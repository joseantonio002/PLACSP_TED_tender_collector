from copy import deepcopy
from datetime import date, time
from decimal import Decimal
from types import ModuleType
import xml.etree.ElementTree as ET

import pytest

from .support import BATCH, Cases, P_BUDGET, assert_stable, financial, issue, semantic, xml_path


@pytest.mark.parametrize('name,path,selection', [
    ('C01-G', '/pressupost_licitacio_sense_1', None),
    ('C05-G1', '/pressupost_licitacio_sense', None),
    ('C14-G0', '/pressupost_licitacio_sense', None),
    ('C19-E0', '/import_sense_iva', None),
    ('J01', '/publicacio/dadesPublicacio/pressupostLicitacio', None),
    ('J14', BATCH + '/0/pressupostLicitacio', BATCH + '/0'),
    ('J19', '/publicacio/dadesPublicacioLot/0/modificacions/0/incrementPreu', None),
])
def test_D01_bad_money_keeps_qualified_value_and_unrelated_facts(api: ModuleType, cases: Cases, name: str, path: str, selection: str | None) -> None:
    base = cases.get(name)
    before = base.one(api, projection=selection)
    changed = cases.mutate_json(base, path, 'not-a-decimal')
    after = changed.one(api, projection=selection)
    assert_stable(before, after, ('buyer', 'publications', 'titles'))
    issue(after, 'invalid_value', path)
    if name == 'C19-E0':
        money = after.execution_actions[0].amounts[0]
    elif name == 'J19':
        money = after.execution_actions[0].amounts[0]
        assert semantic(after)['execution_actions'][1] == semantic(before)['execution_actions'][1]
    else:
        money, = [item.value for item in after.financials if item.source_path == path]
    assert (money.value, money.raw_value, money.value_state) == (None, 'not-a-decimal', 'invalid')
    assert changed.recipe[0] == base.raw.content.document_sha256


@pytest.mark.parametrize('token,state,amount', [('', 'explicit_empty', None), ('0', 'valid', '0'), ('-12.50', 'valid', '-12.50'), ('123456789012345678901234567890.123456789', 'valid', '123456789012345678901234567890.123456789'), ('NaN', 'invalid', None), ('Infinity', 'invalid', None), ('bad', 'invalid', None)])
def test_I06_exact_decimal_and_states_in_placsp(api: ModuleType, cases: Cases, token: str, state: str, amount: str | None) -> None:
    base = cases.get('C01-P000')
    changed = cases.mutate_xml(base, P_BUDGET, lambda entry, node: setattr(node, 'text', token))
    observation = changed.one(api)
    result = financial(observation, P_BUDGET, purpose='tender_budget', amount=amount, tax='excluded', scope='procedure', currency='EUR', state=state)
    assert result.value.raw_value == token
    assert len(observation.financials) == 2
    if state != 'valid':
        issue(observation, 'explicit_empty' if state == 'explicit_empty' else 'invalid_value', P_BUDGET)


@pytest.mark.parametrize('value,state,raw', [('', 'explicit_empty', ''), ('0', 'valid', '0'), (None, 'explicit_empty', 'null')])
def test_D02_empty_zero_null_in_supplier_money(api: ModuleType, cases: Cases, value, state: str, raw: str) -> None:
    observation = cases.mutate_json(cases.get('C05-G1'), '/import_adjudicacio_sense', value).one(api)
    money, = [amount for amount in observation.awards[0].suppliers[0].amounts if amount.tax_basis == 'excluded']
    assert money.raw_value == raw and money.value_state == state
    assert money.value == (Decimal('0') if state == 'valid' else None)
    if state != 'valid':
        issue(observation, 'explicit_empty', '/import_adjudicacio_sense')


@pytest.mark.parametrize('name,path', [('C01-G', '/objecte_contracte'), ('C05-G1', '/import_adjudicacio_sense'), ('C19-E0', '/data'), ('J01', '/versio')])
def test_D15_missing_optional_fields_are_not_errors(api: ModuleType, cases: Cases, name: str, path: str) -> None:
    base = cases.get(name)
    before = base.one(api)
    after = cases.mutate_json(base, path).one(api)
    assert {(item.code, item.path) for item in after.issues} <= {(item.code, item.path) for item in before.issues}
    assert after.buyer == before.buyer
    if name == 'C01-G':
        assert not after.descriptions and after.titles == before.titles
    elif name == 'C05-G1':
        assert {amount.tax_basis for amount in after.awards[0].suppliers[0].amounts} == {'included'}
    elif name == 'C19-E0':
        assert after.execution_actions[0].action_at is None


@pytest.mark.parametrize('name,path', [('C01-G', '/procediment'), ('C14-G0', '/tipus_contracte'), ('C19-E0', '/tipus_actuacio_execucio')])
def test_D03_unknown_code_is_not_other(api: ModuleType, cases: Cases, name: str, path: str) -> None:
    observation = cases.mutate_json(cases.get(name), path, 'UNREVIEWED-CODE').one(api)
    mapped = observation.procurement_method if path == '/procediment' else (observation.contract_type if path == '/tipus_contracte' else observation.execution_actions[0].type)
    assert mapped.source.value == 'UNREVIEWED-CODE'
    assert mapped.normalized is None and mapped.mapping == 'unmapped'
    issue(observation, 'unmapped_code', path)


@pytest.mark.parametrize('version_only', [False, True])
def test_D03_placsp_code_and_list_version_are_both_required(api: ModuleType, cases: Cases, version_only: bool) -> None:
    path = xml_path('ext:ContractFolderStatus/ebc:ContractFolderStatusCode')
    def change(entry: ET.Element, node: ET.Element) -> None:
        if version_only:
            node.set('listURI', node.get('listURI').replace('2.04', '99.99'))
        else:
            node.text = 'UNKNOWN'
    observation = cases.mutate_xml(cases.get('C01-P000'), path, change).one(api)
    status, = observation.statuses
    assert status.value.normalized is None and status.value.mapping == 'unmapped'
    assert status.value.source.value == ('PUB' if version_only else 'UNKNOWN')
    if version_only:
        assert '99.99' in status.value.source.system
    issue(observation, 'unmapped_code', path)


def test_D04_unknown_supplier_scheme_keeps_party(api: ModuleType, cases: Cases) -> None:
    observation = cases.mutate_json(cases.get('C05-G1'), '/tipus_identificacio', 'unknown').one(api)
    identifier, = observation.awards[0].suppliers[0].party.identifiers
    assert (identifier.value, identifier.scheme, identifier.usability) == ('B60650801', 'source_unclassified', 'unvalidated')
    issue(observation, 'unmapped_code', '/tipus_identificacio')


@pytest.mark.parametrize('token', ['2026-02-30T12:00:00.000', 'not-a-date'])
def test_D06_invalid_business_date_is_recoverable(api: ModuleType, cases: Cases, token: str) -> None:
    observation = cases.mutate_json(cases.get('C01-G'), '/termini_presentacio_ofertes', token).one(api)
    at = observation.deadlines[0].value.at
    assert at.raw == token
    assert at.local_date is None and at.local_time is None and at.utc_instant is None
    assert at.precision == 'unknown' and at.zone_basis == 'unknown'
    issue(observation, 'invalid_value', '/termini_presentacio_ofertes')
    assert observation.financials and observation.buyer


@pytest.mark.parametrize('token', ['2026-03-29T02:30:00.000', '2026-10-25T02:30:00.000'])
def test_D06_floating_dst_times_never_guess_unique_utc(api: ModuleType, cases: Cases, token: str) -> None:
    observation = cases.mutate_json(cases.get('C01-G'), '/termini_presentacio_ofertes', token).one(api)
    at = observation.deadlines[0].value.at
    assert at.raw == token and at.local_time == time(2, 30)
    assert at.utc_instant is None and at.zone is None and at.offset is None
    assert at.zone_basis == 'unknown'
    issue(observation, 'ambiguous_time', '/termini_presentacio_ofertes')


def test_D07_supplier_amount_mismatch_preserves_every_token(api: ModuleType, cases: Cases) -> None:
    observation = cases.mutate_json(cases.get('C20-G1'), '/import_adjudicacio_sense', '10||20||30').one(api)
    award, = observation.awards
    assert not award.amounts
    net_allocations = [supplier for supplier in award.suppliers if any(amount.tax_basis == 'excluded' for amount in supplier.amounts)]
    assert [supplier.source_position for supplier in net_allocations] == [0, 1, 2]
    assert all(supplier.party is None and supplier.alignment == 'unresolved' for supplier in net_allocations)
    assert [amount.value for supplier in net_allocations for amount in supplier.amounts if amount.tax_basis == 'excluded'] == [Decimal('10'), Decimal('20'), Decimal('30')]
    parties = [supplier for supplier in award.suppliers if supplier.party is not None]
    assert {identifier.value for supplier in parties for identifier in supplier.party.identifiers} == {'B41956970', 'A08338683'}
    assert sum(amount.tax_basis == 'included' for supplier in award.suppliers for amount in supplier.amounts) == 2
    issue(observation, 'supplier_alignment', '/import_adjudicacio_sense')


def test_D08_duplicate_conflicting_boolean_does_not_use_last_value(api: ModuleType, cases: Cases) -> None:
    path = xml_path('ext:ContractFolderStatus/cac:ProcurementProject/cbc:MixContractIndicator')
    def conflict(entry: ET.Element, node: ET.Element) -> None:
        duplicate = deepcopy(node)
        duplicate.text = 'true'
        entry.find(xml_path('ext:ContractFolderStatus/cac:ProcurementProject')).append(duplicate)
    observation = cases.mutate_xml(cases.get('C01-P000'), path, conflict).one(api)
    assert observation.mixed_contract is None
    issue(observation, 'inconsistent_source_values', path)
    assert observation.financials


def test_D10_invalid_phase_url_does_not_drop_date(api: ModuleType, cases: Cases) -> None:
    observation = cases.mutate_json(cases.get('C01-G'), '/url_json_licitacio/url', 'not a URI').one(api)
    publication, = [p for p in observation.publications if p.publication_at and p.publication_at.raw == '2026-09-17T20:18:00.000']
    assert publication.type.normalized == 'tender_notice' and not publication.identifiers
    assert all(reference.url != 'not a URI' for reference in observation.source_references)
    issue(observation, 'invalid_value', '/url_json_licitacio/url')


@pytest.mark.parametrize('currency', [None, 'UNSUPPORTED-CURRENCY'])
def test_D11_currency_not_borrowed(api: ModuleType, cases: Cases, currency: str | None) -> None:
    def change(entry: ET.Element, node: ET.Element) -> None:
        if currency is None:
            del node.attrib['currencyID']
        else:
            node.set('currencyID', currency)
    observation = cases.mutate_xml(cases.get('C01-P000'), P_BUDGET, change).one(api)
    financial(observation, P_BUDGET, purpose='tender_budget', amount='949509.1', tax='excluded', scope='procedure')
    if currency is not None:
        issue(observation, 'unmapped_code', P_BUDGET + '/@currencyID')


@pytest.mark.parametrize('path,token,code', [
    ('ext:ContractFolderStatus/cac:ProcurementProject/cbc:MixContractIndicator', 'not-bool', 'invalid_value'),
    ('ext:ContractFolderStatus/cac:ProcurementProject/cac:RequiredCommodityClassification/cbc:ItemClassificationCode', 'not-cpv', 'invalid_value'),
])
def test_D14_invalid_boolean_and_cpv(api: ModuleType, cases: Cases, path: str, token: str, code: str) -> None:
    path = xml_path(path)
    observation = cases.mutate_xml(cases.get('C01-P000'), path, lambda entry, node: setattr(node, 'text', token)).one(api)
    if token == 'not-bool':
        assert observation.mixed_contract is None
    else:
        assert observation.classifications[0].value.raw_code == token and observation.classifications[0].value.code is None
    issue(observation, code, path)


@pytest.mark.parametrize('component', ['EndDate', 'EndTime'])
def test_D26_partial_deadline_components(api: ModuleType, cases: Cases, component: str) -> None:
    parent = xml_path('ext:ContractFolderStatus/cac:TenderingProcess/cac:TenderSubmissionDeadlinePeriod')
    path = parent + '/' + xml_path('cbc:' + component)[2:]
    observation = cases.mutate_xml(cases.get('C01-P000'), path, lambda entry, node: entry.find(parent).remove(node)).one(api)
    at = observation.deadlines[0].value.at
    assert at.utc_instant is None
    if component == 'EndDate':
        assert at.local_date is None and at.local_time == time(14)
    else:
        assert at.local_date == date(2026, 9, 14) and at.local_time is None and at.precision == 'day'


@pytest.mark.parametrize('label,normalized,mapping', [('Contracte de serveis especials (annex IV)', 'services', 'broader'), ('Altra legislació sectorial', None, 'unmapped')])
def test_D27_taxonomy_is_not_guessed(api: ModuleType, cases: Cases, label: str, normalized: str | None, mapping: str) -> None:
    observation = cases.mutate_json(cases.get('C05-G1'), '/tipus_contracte', label).one(api)
    assert observation.contract_type.source.value == label
    assert (observation.contract_type.normalized, observation.contract_type.mapping) == (normalized, mapping)
    assert observation.procurement_method.normalized == 'open'
    if normalized is None:
        issue(observation, 'unmapped_code', '/tipus_contracte')


def test_unknown_future_keys_remain_raw_without_issue_spam(api: ModuleType, cases: Cases) -> None:
    base = cases.get('C01-G')
    before = base.one(api)
    after = cases.mutate_json(base, '/unmapped_future_column', {'nested': 'retained'}).one(api)
    assert semantic(after) == semantic(before)
