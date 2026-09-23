from datetime import date, datetime, time, timezone
from decimal import Decimal
from types import ModuleType

import pytest

from .support import Cases, P_BUDGET, P_ESTIMATE, financial, ids, issue, semantic


@pytest.mark.parametrize('name,kind,subject', [
    ('C01-P000', 'procedure_snapshot', 'procedure'),
    ('C07-P001', 'procedure_snapshot', 'procedure'),
    ('C01-G', 'procedure_projection', 'procedure'),
    ('C05-G1', 'lot_projection', 'procedure'),
    ('C14-G0', 'batch_member_projection', 'batch_member'),
    ('C19-E0', 'execution_action_projection', 'procedure'),
    ('J01', 'publication_body', 'procedure'),
    ('J19', 'publication_body', 'procedure'),
    ('J16', 'publication_body', 'planning'),
])
def test_H01_H09_source_envelope(api: ModuleType, cases: Cases, name: str, kind: str, subject: str) -> None:
    observation = cases.get(name).one(api)
    assert observation.source.record_kind == kind
    assert observation.subject_kind == subject
    assert observation.projection_locator == '$'


def test_H01_placsp_tender(api: ModuleType, cases: Cases) -> None:
    observation = cases.get('C01-P000').one(api)
    assert ids(observation.procedure_numbers) == ['905451/26']
    atom = 'https://contrataciondelestado.es/sindicacion/PlataformasAgregadasSinMenores/20283724'
    assert atom in ids(observation.source.record_identifiers)
    assert atom in ids(observation.procedure_identifiers)
    assert '4b131001-63ad-4eac-a80a-ab91c3a9f366' in ids(observation.procedure_identifiers)
    assert observation.source.origin_platform.value == '62'
    assert '28027859' in ids(observation.buyer.identifiers)
    assert '62' not in ids(observation.buyer.identifiers)
    assert not any(identifier.scheme == 'NIF' for identifier in observation.buyer.identifiers)
    assert observation.focus.kind == 'procedure'
    assert observation.mixed_contract is False
    lifecycle, = observation.statuses
    assert lifecycle.dimension == 'procurement_lifecycle'
    assert lifecycle.value.source.value == 'PUB'
    assert lifecycle.value.source.system == 'https://contrataciondelestado.es/codice/cl/2.04/SyndicationContractFolderStatusCode-2.04.gc'
    assert lifecycle.value.normalized == 'submission_open_reported'
    financial(observation, P_BUDGET, purpose='tender_budget', amount='949509.1', tax='excluded', scope='procedure', currency='EUR')
    financial(observation, P_ESTIMATE, purpose='estimated_value', amount='2183870.93', tax='excluded', scope='procedure', currency='EUR')
    assert len(observation.financials) == 2
    cpv, = observation.classifications
    assert (cpv.value.raw_code, cpv.value.code, cpv.value.check_digit) == ('90513000', '90513000', None)
    deadline, = observation.deadlines
    assert deadline.value.kind == 'offers'
    assert deadline.value.at.local_date == date(2026, 9, 14)
    assert deadline.value.at.local_time == time(14)
    assert deadline.value.at.utc_instant is None and deadline.value.at.zone_basis == 'unknown'
    marker, = observation.source_markers
    assert marker.kind == 'placsp_entry_publication_updated'
    assert marker.at.raw == '2026-08-11T10:02:29.069+02:00'
    assert marker.at.utc_instant == datetime(2026, 8, 11, 8, 2, 29, 69000, timezone.utc)
    media = [publication for publication in observation.publications if publication.medium in ('Perfil del contratante', 'DOUE')]
    assert len(media) == 2
    assert len({publication.source_path for publication in media}) == 2
    assert all(publication.publication_at.local_date == date(2026, 8, 11) for publication in media)
    assert all(not publication.identifiers for publication in media)
    dispatch, = [publication.sent_at for publication in media if publication.medium == 'DOUE']
    assert dispatch.local_date == date(2026, 7, 29) and dispatch.local_time == time(20, 3, 11)
    assert {document.role.normalized for document in observation.documents} == {'administrative_specification', 'technical_specification'}
    assert all(document.urls for document in observation.documents)
    assert not observation.descriptions
    assert not observation.lots and not observation.awards and not observation.outcomes
    assert not any(item.path == 'lots' and item.state == 'source_declares_empty' for item in observation.coverage)
    assert all(text.language is None for text in observation.titles)
    assert {text.text for text in observation.titles} == {'Servicios de tratamiento de la fracción vegetal municipal procedente de los municipios del AMB'}
    assert [text.text for text in observation.buyer.names] == ['Àrea Metropolitana de Barcelona']


def test_H02_placsp_award_group_not_supplier_amount(api: ModuleType, cases: Cases) -> None:
    observation = cases.get('C07-P001').one(api)
    award, = observation.awards
    assert award.grouping == 'source_result'
    assert award.decision_at is None
    amount, = award.amounts
    assert (amount.value, amount.currency, amount.tax_basis, amount.purpose) == (Decimal('779542.5'), 'EUR', 'excluded', 'award_amount')
    supplier, = award.suppliers
    assert ids(supplier.party.identifiers) == ['B43672138']
    assert supplier.alignment == 'structured' and not supplier.amounts
    contract, = award.contract_references
    assert contract.formalized_at.local_date == date(2022, 11, 8)
    assert contract.formalized_at.utc_instant is None
    assert observation.statuses[0].value.normalized == 'resolved_unspecified'


def test_H03_main_row_scope_currency_and_phase(api: ModuleType, cases: Cases) -> None:
    observation = cases.get('C01-G').one(api)
    assert set(ids(observation.source.record_identifiers)) == {'row-uvc4~ws2c-5q3s', '4b131001-63ad-4eac-a80a-ab91c3a9f366'}
    assert observation.contract_type.normalized == 'services'
    assert not any(identifier.scheme == 'NIF' for identifier in observation.buyer.identifiers)
    assert observation.procurement_method.normalized == 'open'
    assert observation.procurement_method.source.value == 'Obert'
    assert observation.statuses[0].value.source.value == 'Expedient en avaluació'
    assert observation.mixed_contract is None
    assert [(status.dimension, status.value.normalized, status.scope.kind) for status in observation.statuses] == [('publication_phase', 'evaluation', 'record_subject')]
    financial(observation, '/pressupost_licitacio_sense_1', purpose='tender_budget', amount='949509.1', tax='excluded', scope='procedure')
    financial(observation, '/pressupost_licitacio_amb_1', purpose='tender_budget', amount='1044460.01', tax='included', scope='procedure')
    financial(observation, '/valor_estimat_expedient', purpose='estimated_value', amount='2183870.93', tax='excluded', scope='procedure')
    financial(observation, '/pressupost_licitacio_sense', purpose='tender_budget', amount='949509.1', tax='excluded', scope='record_subject')
    issue(observation, 'uncertain_scope', '/pressupost_licitacio_sense')
    assert len(observation.financials) == 6
    assert all(item.value.currency is None and item.value.vat_rate is None for item in observation.financials)
    assert not observation.lots and not observation.awards and not observation.execution_actions and not observation.documents
    cpv, = observation.classifications
    assert (cpv.value.raw_code, cpv.value.code, cpv.value.check_digit) == ('90513000-6', '90513000', '6')
    assert cpv.scope.kind == 'record_subject'
    markers = {marker.kind: marker.at for marker in observation.source_markers}
    assert set(markers) == {'socrata_row_created', 'socrata_row_updated'}
    assert markers['socrata_row_created'].raw == '2026-08-12T08:00:16.789Z'
    assert markers['socrata_row_created'].utc_instant == datetime(2026, 8, 12, 8, 0, 16, 789000, timezone.utc)
    assert markers['socrata_row_updated'].raw == '2026-09-22T08:00:13.604Z'
    assert markers['socrata_row_updated'].utc_instant == datetime(2026, 9, 22, 8, 0, 13, 604000, timezone.utc)
    for raw_date, publication_id, kind in [('2026-09-17T20:18:00.000', '300885987', 'tender_notice'), ('2026-09-21T19:16:00.000', '300888482', 'evaluation')]:
        publication, = [p for p in observation.publications if p.publication_at and p.publication_at.raw == raw_date]
        assert ids(publication.identifiers) == [publication_id]
        assert publication.type.normalized == kind
        assert publication.publication_at.utc_instant is None
    assert all(reference.target_kind != 'document' for reference in observation.source_references)


def test_H04_lot_row_scope_and_nonmidnight_award(api: ModuleType, cases: Cases) -> None:
    observation = cases.get('C05-G1').one(api)
    lot, = observation.lots
    assert lot.number == '1' and observation.focus.lot_keys == (lot.key,)
    assert 'f98c30c1-1327-4dfc-b38a-5b707e9adf41_0' in ids(observation.source.record_identifiers)
    financial(observation, '/pressupost_licitacio_sense_1', purpose='tender_budget', amount='41129079.80', tax='excluded', scope='procedure')
    financial(observation, '/pressupost_licitacio_amb_1', purpose='tender_budget', amount='49766186.56', tax='included', scope='procedure')
    financial(observation, '/valor_estimat_expedient', purpose='estimated_value', amount='83579468.07', tax='excluded', scope='procedure')
    money = financial(observation, '/pressupost_licitacio_sense', purpose='tender_budget', amount='2292542.12', tax='excluded', scope='lots')
    assert money.scope.lot_keys == (lot.key,)
    financial(observation, '/pressupost_licitacio_amb', purpose='tender_budget', amount='2773975.96', tax='included', scope='lots')
    financial(observation, '/valor_estimat_contracte', purpose='estimated_value', amount='4500965.74', tax='excluded', scope='lots')
    award, = observation.awards
    assert award.scope.lot_keys == (lot.key,)
    assert award.grouping == 'source_row_group' and not award.amounts
    supplier, = award.suppliers
    assert ids(supplier.party.identifiers) == ['B60650801']
    assert {(amount.tax_basis, amount.value) for amount in supplier.amounts} == {('excluded', Decimal('2011802.23')), ('included', Decimal('2434280.70'))}
    assert all(amount.currency is None and amount.vat_rate is None for amount in supplier.amounts)
    assert award.decision_at.local_time == time(17)
    assert award.decision_at.utc_instant is None
    issue(observation, 'uncertain_precision', '/data_adjudicacio_contracte')
    assert any(item.path == 'lots' and item.state == 'partial' for item in observation.coverage)
    outcome, = observation.outcomes
    assert outcome.result.normalized == 'formalized' and outcome.scope.lot_keys == (lot.key,)


def test_H05_batch_row_is_not_a_procedure(api: ModuleType, cases: Cases) -> None:
    observation = cases.get('C14-G0').one(api)
    assert not observation.procedure_identifiers
    assert ids(observation.batch_identifiers) == ['fff0ffe1-d07b-42af-ade9-dc8eb403a8b6']
    assert ids(observation.member_identifiers) == ['fff0ffe1-d07b-42af-ade9-dc8eb403a8b6_306344580']
    assert ids(observation.procedure_numbers) == ['2023/585']
    assert observation.focus.kind == 'record_subject'
    assert all(item.scope.kind == 'record_subject' for item in observation.financials)
    assert not observation.lots and not observation.execution_actions and not observation.deadlines
    assert observation.procurement_method is None
    assert any(attribute.kind == 'contracting_system' and attribute.value.value == 'Contracte basat en acord marc' for attribute in observation.procurement_attributes)
    supplier, = observation.awards[0].suppliers
    assert ids(supplier.party.identifiers) == ['A28119220']
    assert supplier.party.identifiers[0].scheme == 'source_unclassified'
    assert supplier.party.identifiers[0].usability == 'unvalidated'
    assert all(amount.currency is None and amount.vat_rate is None for amount in supplier.amounts)
    assert any(publication.scope.kind == 'publication_batch' and publication.type.normalized == 'aggregate_contract_report' for publication in observation.publications)
    issue(observation, 'placeholder_identifier', '/codi_dir3')


@pytest.mark.parametrize('name,amount,day', [('C19-E0', '341124.070000000000000000', date(2026, 3, 30)), ('C19-E1', '317101.250000000000000000', date(2026, 8, 10))])
def test_H06_E19_execution_is_independent(api: ModuleType, cases: Cases, name: str, amount: str, day: date) -> None:
    observation = cases.get(name).one(api)
    action, = observation.execution_actions
    assert action.type.normalized == 'modification'
    assert action.type.source.value == 'Modificació (Objectiva)'
    assert action.scope.kind == 'record_subject'
    assert ids(observation.procedure_numbers) == ['4317110007-2021-0001388']
    assert not observation.procedure_identifiers and not action.identifiers
    assert not action.parties and action.end_at is None
    money, = action.amounts
    assert (money.value, money.raw_value, money.purpose, money.tax_basis, money.currency) == (Decimal(amount), amount, 'action_amount', 'excluded', None)
    assert action.action_at.local_date == day and action.action_at.precision == 'day'
    assert action.action_at.local_time is None and action.action_at.utc_instant is None
    assert not observation.awards and not observation.financials and not observation.lots
    assert all(publication.publication_at is None for publication in observation.publications)
    assert any('300007312' in ids(publication.identifiers) for publication in observation.publications)
    issue(observation, 'uncertain_scope', '/numero_lot')


def test_E09_retained_award_is_not_erased_or_rescinded(api: ModuleType, cases: Cases) -> None:
    observation = cases.get('C09-G').one(api)
    outcome, = observation.outcomes
    assert outcome.result.normalized == 'renounced' and outcome.decision_at is None
    award, = observation.awards
    assert not award.outcome_keys
    assert 'A58846064' in ids(award.suppliers[0].party.identifiers)
    assert any(amount.value == Decimal('83996.64') for amount in award.suppliers[0].amounts)
    assert award.decision_at.local_date == date(2022, 7, 11)
    assert not any(item.code == 'inconsistent_source_values' for item in observation.issues)


def test_E16_planning_does_not_extract_number_from_title(api: ModuleType, cases: Cases) -> None:
    observation = cases.get('C16-parent').one(api)
    assert observation.subject_kind == 'planning'
    assert not observation.procedure_numbers and not observation.lots
    assert observation.procurement_method.normalized == 'open_simplified_abbreviated'
    assert any(text.text.startswith('2026/7731') for text in observation.titles)
    assert [(status.dimension, status.value.normalized) for status in observation.statuses] == [('publication_phase', 'future_notice')]


def test_E20_empty_winner_vectors_preserve_positions(api: ModuleType, cases: Cases) -> None:
    observation = cases.get('C20-G1').one(api)
    award, = observation.awards
    assert not award.amounts
    assert [supplier.source_position for supplier in award.suppliers] == [0, 1]
    assert [ids(supplier.party.identifiers) for supplier in award.suppliers] == [['B41956970'], ['A08338683']]
    for supplier in award.suppliers:
        assert supplier.alignment == 'positional'
        assert {amount.tax_basis for amount in supplier.amounts} == {'excluded', 'included'}
        assert all(amount.value is None and amount.raw_value == '' and amount.value_state == 'explicit_empty' for amount in supplier.amounts)
    for field in ('import_adjudicacio_sense', 'import_adjudicacio_amb_iva'):
        for index in (0, 1):
            issue(observation, 'explicit_empty', f'/{field}#token={index}')
    assert not any(item.code == 'supplier_alignment' for item in observation.issues)
    issue(observation, 'placeholder_identifier', '/codi_dir3')


@pytest.mark.parametrize('name', ['C01-P000', 'C01-G', 'C05-G1', 'C14-G0', 'C19-E0', 'J01', 'J19'])
def test_I20_I26_repeated_mapping_and_interleaving(api: ModuleType, cases: Cases, name: str) -> None:
    case = cases.get(name)
    first = case.one(api)
    cases.get('C09-G').one(api)
    again = case.one(api)
    assert semantic(first) == semantic(again)
    assert first.observation_id == again.observation_id
    assert all(identifier.namespace for identifier in first.source.record_identifiers)
