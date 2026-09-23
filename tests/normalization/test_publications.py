from datetime import datetime, timezone
from decimal import Decimal
from types import ModuleType

import pytest

from .support import BATCH, Cases, assert_stable, financial, ids, issue, semantic


def test_H07_E22_E25_correction_no_lots_and_document_metadata(api: ModuleType, cases: Cases) -> None:
    case = cases.get('J01')
    observation = case.one(api)
    assert 'P0800258F' in ids(observation.buyer.identifiers)
    assert '28027859' in ids(observation.buyer.identifiers)
    assert observation.buyer.addresses[0].postal_code == '08040'
    assert {text.language for text in observation.titles} == {'ca', 'es'}
    assert observation.lots == ()
    assert any(item.path == 'lots' and item.state == 'source_declares_empty' for item in observation.coverage)
    assert len(observation.financials) == 6
    for path in ('/publicacio/dadesPublicacio/pressupostLicitacio', '/publicacio/dadesPublicacioLot/0/pressupostLicitacio'):
        amount = financial(observation, path, purpose='tender_budget', amount='949509.1', tax='excluded', scope='procedure').value
        assert amount.vat_rate == Decimal('10') and amount.multiple_vat_rates is False
    publication, = [p for p in observation.publications if p.publication_at and p.publication_at.raw == '2026-09-17T18:18:05.642Z']
    assert publication.publication_at.utc_instant == datetime(2026, 9, 17, 18, 18, 5, 642000, timezone.utc)
    assert publication.planned_publication_at.raw == '2026-09-17T18:17:26.471Z'
    assert publication.type.normalized == 'tender_notice' and publication.is_correction is True
    assert not publication.relations
    assert 'Modificació de dades d\'obertura' in [text.text for text in publication.correction_reason]
    deadline, = observation.deadlines
    assert deadline.value.kind == 'submission_unspecified'
    assert deadline.value.at.raw == '2026-09-14T12:00:00.000Z'
    assert deadline.value.at.utc_instant == datetime(2026, 9, 14, 12, tzinfo=timezone.utc)
    assert len(observation.documents) == 2
    assert {identifier.value for document in observation.documents for identifier in document.identifiers} == {'302601952', '302601953'}
    for document in observation.documents:
        assert not document.urls and document.source_path_token
        assert document.reported_hash.value and document.reported_hash.algorithm is None
        assert document.reported_size_bytes is None
        assert document.language == 'ca'
    assert {document.role.normalized for document in observation.documents} == {'administrative_specification', 'technical_specification'}
    assert not any(text.text == 'null' for location in observation.execution_locations for text in location.value.names)
    issue(observation, 'invalid_value', '/publicacio/dadesPublicacioLot/0/llocExecucio/oc')
    period, = observation.performance_periods
    assert period.value.start_at is None and period.value.end_at is None
    assert any(part.value == Decimal('2') and part.unit == 'years' for part in period.value.duration)
    assert any('formalització' in text.text for text in period.value.raw_text)


def test_H08_E14_rich_batch_six_distinct_subjects(api: ModuleType, cases: Cases) -> None:
    case = cases.get('J14')
    observations = case.normalize(api)
    assert len(observations) == 6
    assert [observation.projection_locator for observation in observations] == [f'{BATCH}/{index}' for index in range(6)]
    assert len({observation.observation_id for observation in observations}) == 6
    assert {observation.raw_source_record_id for observation in observations} == {case.raw.raw_record_id}
    expected = [('2023/585', 'A28119220', '28957.25'), ('2023/800', 'W0072130H', '7096.06'), ('2023/800', 'G08171407', '3149.79'), ('2024/757', 'A28119220', '3997.57'), ('2024/639', 'B58265240', '0'), ('2024/363', 'A61893871', '5044.16')]
    for index, (observation, (number, supplier_id, net)) in enumerate(zip(observations, expected, strict=True)):
        assert observation.source.record_kind == 'batch_publication_body'
        assert observation.subject_kind == 'batch_member'
        assert observation.focus.kind == 'record_subject'
        assert ids(observation.procedure_numbers) == [number]
        assert not observation.procedure_identifiers and not observation.member_identifiers
        assert ids(observation.batch_identifiers) == ['fff0ffe1-d07b-42af-ade9-dc8eb403a8b6']
        assert not observation.titles
        assert 'P1700053J' in ids(observation.buyer.identifiers)
        assert all(money.scope.kind == 'record_subject' for money in observation.financials)
        estimate = ('132628.56', '34061.08', '13369.64', '15990.28', '0', '18158.97')[index]
        assert len(observation.financials) == 2
        assert {(item.value.purpose, item.value.value) for item in observation.financials} == {('estimated_value', Decimal(estimate)), ('tender_budget', Decimal(net))}
        award, = observation.awards
        supplier, = award.suppliers
        assert ids(supplier.party.identifiers) == [supplier_id]
        assert any(amount.value == Decimal(net) and amount.tax_basis == 'excluded' for amount in supplier.amounts)
        assert all(amount.currency is None and amount.vat_rate is None for amount in supplier.amounts)
        assert any(publication.scope.kind == 'publication_batch' and publication.publication_at.raw == '2025-01-01T08:00:05.758Z' for publication in observation.publications if publication.publication_at)
        selected = case.one(api, projection=f'{BATCH}/{index}')
        assert semantic(selected) == semantic(observation)
    assert '1efe0fb1-e5e6-4e3a-8cb6-fcc33215dad1' in [item.identifier.value for item in observations[0].related_identifiers]
    assert all(item.identifier.role == 'related' for item in observations[0].related_identifiers)


def test_H09_rich_actions_are_deltas_not_original_award(api: ModuleType, cases: Cases) -> None:
    observation = cases.get('J19').one(api)
    assert not observation.lots and not observation.source_markers
    assert ids(observation.procedure_identifiers) == ['cdd2280f-bc0d-b291-4214-69ded8c1182d']
    assert len(observation.execution_actions) == 2
    for index, (action, amount, original_time) in enumerate(zip(observation.execution_actions, ('341124.07', '317101.25'), ('2026-03-29T22:00:00.000Z', '2026-08-09T22:00:00.000Z'), strict=True)):
        assert ids(action.identifiers) == [str(index + 1)]
        assert action.type.normalized == 'modification'
        assert action.source_path == f'/publicacio/dadesPublicacioLot/0/modificacions/{index}'
        assert action.amounts[0].value == Decimal(amount)
        assert action.amounts[0].purpose == 'modification_delta'
        assert not action.parties
        assert action.action_at.raw == original_time
        assert action.action_at.utc_instant is None and action.action_at.local_date is None
        issue(observation, 'ambiguous_time', action.source_path + '/dataModificacio')
    assert observation.execution_actions[0].publication_keys == observation.execution_actions[1].publication_keys
    assert len(observation.execution_actions[0].publication_keys) == 1
    assert any(item.value.value == Decimal('3981218.08') and item.value.purpose == 'tender_budget' for item in observation.financials)
    supplier, = observation.awards[0].suppliers
    assert ids(supplier.party.identifiers) == ['A79524054']
    assert {(amount.tax_basis, amount.value) for amount in supplier.amounts} == {('excluded', Decimal('3961311.99')), ('included', Decimal('4357443.19'))}
    assert all(amount.vat_rate == Decimal('10') for amount in supplier.amounts)


def test_H10_E23_rich_lot_order_zero_id_and_missing_award_amounts(api: ModuleType, cases: Cases) -> None:
    observation = cases.get('J20').one(api)
    assert [lot.number for lot in observation.lots] == ['4', '1', '2', '3', '6', '5']
    assert '0' in ids(observation.lots[0].identifiers)
    assert len(observation.awards) == 6
    for number, suppliers in [('1', {'B41956970', 'A08338683'}), ('5', {'B41956970', 'A08338683'})]:
        lot, = [lot for lot in observation.lots if lot.number == number]
        award, = [award for award in observation.awards if award.scope.lot_keys == (lot.key,)]
        assert {identifier.value for allocation in award.suppliers for identifier in allocation.party.identifiers} == suppliers
        assert not award.amounts
        assert all(not allocation.amounts and allocation.alignment == 'structured' for allocation in award.suppliers)
    assert observation.procurement_method.normalized == 'open'
    assert any(attribute.kind == 'contracting_system' and attribute.value.value == '472' for attribute in observation.procurement_attributes)
    assert all(item.scope.kind == 'procedure' for item in observation.financials)
    assert {item.value.value for item in observation.financials} == {Decimal('211249.74'), Decimal('422499.47')}
    assert not observation.execution_locations


def test_D22_invalid_batch_amount_does_not_change_siblings(api: ModuleType, cases: Cases) -> None:
    case = cases.get('J14')
    original = case.normalize(api)
    changed = cases.mutate_json(case, BATCH + '/1/importAdjudicacioSenseIva', 'not-a-decimal').normalize(api)
    assert len(changed) == 6
    for index in (0, 2, 3, 4, 5):
        assert semantic(changed[index]) == semantic(original[index])
    money, = [amount for amount in changed[1].awards[0].suppliers[0].amounts if amount.tax_basis == 'excluded']
    assert money.value is None and money.value_state == 'invalid' and money.raw_value == 'not-a-decimal'
    issue(changed[1], 'invalid_value', BATCH + '/1/importAdjudicacioSenseIva')


def test_D16_count_mismatch_does_not_invent_member(api: ModuleType, cases: Cases) -> None:
    changed = cases.mutate_json(cases.get('J14'), '/publicacio/dadesPublicacio/nombreInformats', 7)
    observations = changed.normalize(api)
    assert len(observations) == 6
    for observation in observations:
        issue(observation, 'inconsistent_source_values', '/publicacio/dadesPublicacio/nombreInformats')


@pytest.mark.parametrize('name,path', [('J01', '/publicacio/dadesPublicacio/plecsDeClausulesAdministratives/ca'), ('J19', '/publicacio/dadesPublicacioLot/0/modificacions/0/tipusActuacioExecucio')])
def test_D09_unsupported_optional_subtree_is_local(api: ModuleType, cases: Cases, name: str, path: str) -> None:
    base = cases.get(name)
    before = base.one(api)
    after = cases.mutate_json(base, path, 'unsupported scalar').one(api)
    assert_stable(before, after, ('buyer', 'titles', 'financials'))
    issue(after, 'unsupported_structure', path)
    if name == 'J01':
        assert len(after.documents) == 1
        assert after.documents[0].role.normalized == 'technical_specification'
    else:
        assert len(after.execution_actions) == 1
        assert ids(after.execution_actions[0].identifiers) == ['2']
        assert_stable(before, after, ('awards',))


def test_D08_conflicting_no_lots_declarations(api: ModuleType, cases: Cases) -> None:
    observation = cases.mutate_json(cases.get('J01'), '/publicacio/teLots', True).one(api)
    assert not observation.lots
    assert not any(coverage.path == 'lots' and coverage.state == 'source_declares_empty' for coverage in observation.coverage)
    issue(observation, 'inconsistent_source_values', '/publicacio/teLots')
    assert any(item.source_path == '/publicacio/dadesPublicacio/pressupostLicitacio' and item.scope.kind == 'procedure' for item in observation.financials)


def test_D23_conflicting_body_ids_remain_competing_source_assertions(api: ModuleType, cases: Cases) -> None:
    other = '00000000-0000-4000-8000-000000000001'
    observation = cases.mutate_json(cases.get('J01'), '/publicacio/expedientId', other).one(api)
    assert set(ids(observation.procedure_identifiers)) == {'4b131001-63ad-4eac-a80a-ab91c3a9f366', other}
    issue(observation, 'inconsistent_source_values', '/publicacio/expedientId')
    assert observation.financials and observation.titles
