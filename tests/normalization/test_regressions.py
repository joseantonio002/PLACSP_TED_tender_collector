from copy import deepcopy
from datetime import date, time
from decimal import Decimal
from types import ModuleType
import xml.etree.ElementTree as ET

import pytest

from .support import Cases, NS, P_BUDGET, financial, ids, semantic, xml_path


def test_E01_correction_does_not_reopen_or_rewrite_deadline(api: ModuleType, cases: Cases) -> None:
    original = cases.get('C01-P000').one(api)
    corrected = cases.get('C01-P002').one(api)
    assert original.deadlines[0].value.at.local_date == corrected.deadlines[0].value.at.local_date == date(2026, 9, 14)
    assert original.deadlines[0].value.at.local_time == corrected.deadlines[0].value.at.local_time == time(14)
    assert original.statuses[0].value.normalized == 'submission_open_reported'
    assert corrected.statuses[0].value.normalized == 'awaiting_award'
    assert original.raw_source_record_id != corrected.raw_source_record_id
    assert not any(publication.relations for observation in (original, corrected) for publication in observation.publications)


@pytest.mark.parametrize('first,second,before,after', [('C02-P000', 'C02-P005', '162565.2', '177465.2'), ('C03-P000', 'C03-P005', '2000', '53000')])
def test_E02_E03_changed_budget_is_not_a_revision_or_action(api: ModuleType, cases: Cases, first: str, second: str, before: str, after: str) -> None:
    earlier = cases.get(first).one(api)
    later = cases.get(second).one(api)
    financial(earlier, P_BUDGET, purpose='tender_budget', amount=before, tax='excluded', scope='procedure', currency='EUR')
    financial(later, P_BUDGET, purpose='tender_budget', amount=after, tax='excluded', scope='procedure', currency='EUR')
    assert not earlier.execution_actions and not later.execution_actions
    if first.startswith('C02'):
        assert earlier.deadlines[0].value.at.local_date == date(2025, 1, 24)
        assert later.deadlines[0].value.at.local_date == date(2025, 5, 20)


def test_E04_renamed_numbers_remain_exact_independent_assertions(api: ModuleType, cases: Cases) -> None:
    earlier = cases.get('C04-P000').one(api)
    later = cases.get('C04-P001').one(api)
    assert ids(earlier.procedure_numbers) == ['24001098']
    assert ids(later.procedure_numbers) == ['006_24001098']
    assert earlier.raw_source_record_id != later.raw_source_record_id


def test_E05_thirteen_lots_and_results_stay_in_one_observation(api: ModuleType, cases: Cases) -> None:
    observation = cases.get('C05-P024').one(api)
    assert [lot.number for lot in observation.lots] == ['1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9']
    assert len(observation.awards) == len(observation.outcomes) == 13
    lot1 = observation.lots[0]
    award, = [award for award in observation.awards if award.scope.lot_keys == (lot1.key,)]
    assert award.amounts[0].value == Decimal('2011802.23')
    assert all(financial.scope.kind == 'procedure' for financial in observation.financials)
    assert len({award.source_path for award in observation.awards}) == 13


def test_E06_row_suffix_is_not_the_lot_number(api: ModuleType, cases: Cases) -> None:
    observation = cases.get('C05-G7').one(api)
    assert observation.lots[0].number == '7'
    assert 'f98c30c1-1327-4dfc-b38a-5b707e9adf41_6' in ids(observation.source.record_identifiers)
    assert 'f98c30c1-1327-4dfc-b38a-5b707e9adf41_6' not in ids(observation.lots[0].identifiers)
    assert len(observation.lots) == 1


def test_E07_ordinary_annulled_entry_is_not_a_tombstone(api: ModuleType, cases: Cases) -> None:
    observation = cases.get('C06-P000').one(api)
    assert observation.source.record_kind == 'procedure_snapshot'
    assert observation.statuses[0].value.normalized == 'annulled_reported'
    assert not observation.outcomes and not observation.awards


def test_E08_deserted_lot_does_not_roll_up_to_global_lifecycle(api: ModuleType, cases: Cases) -> None:
    observation = cases.get('C08-G5').one(api)
    lot, = observation.lots
    outcome, = observation.outcomes
    assert lot.number == '5' and outcome.scope.lot_keys == (lot.key,)
    assert outcome.result.normalized == 'deserted'
    assert not observation.awards
    assert [(status.dimension, status.value.normalized) for status in observation.statuses] == [('publication_phase', 'evaluation')]
    assert all(text.language is None for text in observation.titles)


def test_E09_negative_placsp_does_not_borrow_table_winner(api: ModuleType, cases: Cases) -> None:
    case = cases.get('C09-P000')
    before = case.one(api)
    cases.get('C09-G').one(api)
    after = case.one(api)
    assert semantic(after) == semantic(before)
    assert after.outcomes[0].result.normalized == 'renounced'
    assert not after.awards


def test_E10_two_atom_ids_not_coalesced(api: ModuleType, cases: Cases) -> None:
    first = cases.get('C10-P000').one(api)
    second = cases.get('C10-P001').one(api)
    assert ids(first.source.record_identifiers)[0].endswith('/16638290')
    assert ids(second.source.record_identifiers)[0].endswith('/16638580')
    assert set(ids(first.source.record_identifiers)).isdisjoint(ids(second.source.record_identifiers))
    assert first.raw_source_record_id != second.raw_source_record_id


def test_E11_source_reported_buyer_not_current_buyer(api: ModuleType, cases: Cases) -> None:
    original = cases.get('C11-P000')
    placsp = original.one(api)
    gencat = cases.get('C11-G').one(api)
    assert semantic(original.one(api)) == semantic(placsp)
    assert '202037' in ids(placsp.buyer.identifiers) and '202266' not in ids(placsp.buyer.identifiers)
    assert '202266' in ids(gencat.buyer.identifiers) and '202037' not in ids(gencat.buyer.identifiers)
    assert ids(placsp.procedure_numbers) == ids(gencat.procedure_numbers) == ['PR-2025-7']


def test_E12_independent_partial_lot_inventories(api: ModuleType, cases: Cases) -> None:
    placsp = cases.get('C12-P000').one(api)
    table = cases.get('C12-G11').one(api)
    assert len(placsp.lots) == 25
    assert [lot.number for lot in table.lots] == ['11']
    assert table.outcomes[0].result.normalized == 'deserted' and not table.awards
    assert not any(item.path == 'lots' and item.state == 'source_declares_complete' for item in table.coverage)


def test_E13_timestamp_seconds_and_notice_targets_are_not_repaired(api: ModuleType, cases: Cases) -> None:
    placsp = cases.get('C13-P000').one(api)
    table = cases.get('C13-G1').one(api)
    assert placsp.deadlines[0].value.at.local_time == time(23, 59, 59)
    assert table.deadlines[0].value.at.local_time == time(23, 59)
    assert table.deadlines[0].value.at.utc_instant is None
    phase, = [publication for publication in table.publications if publication.publication_at and publication.publication_at.raw == '2026-09-17T17:16:00.000']
    assert ids(phase.identifiers) == ['300885950']
    assert any(reference.url.endswith('/300869210') for reference in table.source_references)


def test_E15_duplicate_display_lot_rows_stay_independent(api: ModuleType, cases: Cases) -> None:
    first = cases.get('C15-G0').one(api)
    second = cases.get('C15-G2').one(api)
    for observation, expected in [(first, '4070.00'), (second, '4839.00')]:
        assert [lot.number for lot in observation.lots] == ['3']
        assert not observation.execution_actions
        award, = observation.awards
        assert not award.amounts
        assert [amount.value for allocation in award.suppliers for amount in allocation.amounts if amount.tax_basis == 'excluded'] == [Decimal(expected)]
    assert first.raw_source_record_id != second.raw_source_record_id


def test_E16_parent_and_lot_do_not_share_number_or_phase(api: ModuleType, cases: Cases) -> None:
    parent = cases.get('C16-parent').one(api)
    lot = cases.get('C16-lot1').one(api)
    assert not parent.procedure_numbers and not parent.lots
    assert ids(lot.procedure_numbers) == ['2026/7731']
    assert parent.statuses[0].value.normalized == 'future_notice'
    assert lot.statuses[0].value.normalized == 'tender_notice'


def test_E17_same_number_is_buyer_scoped(api: ModuleType, cases: Cases) -> None:
    first = cases.get('C17-P000').one(api)
    second = cases.get('C17-P001').one(api)
    assert ids(first.procedure_numbers) == ids(second.procedure_numbers) == ['1/2025']
    assert first.procedure_numbers[0].namespace != second.procedure_numbers[0].namespace
    assert '100000012' in ids(first.buyer.identifiers)
    assert '100000081' in ids(second.buyer.identifiers)


def test_E18_no_fuzzy_enrichment(api: ModuleType, cases: Cases) -> None:
    placsp = cases.get('C18-P000').one(api)
    table = cases.get('C18-G').one(api)
    assert ids(placsp.procedure_numbers) == ids(table.procedure_numbers) == ['288/2024']
    assert '8766912' in ids(placsp.buyer.identifiers)
    assert '2867949' in ids(table.buyer.identifiers)
    financial(placsp, P_BUDGET, purpose='tender_budget', amount='14521.86', tax='excluded', scope='procedure', currency='EUR')
    financial(table, '/pressupost_licitacio_sense_1', purpose='tender_budget', amount='13223.14', tax='excluded', scope='procedure')


def test_E21_explicit_zero_results_are_not_table_empty_tokens(api: ModuleType, cases: Cases) -> None:
    observation = cases.get('C20-P000').one(api)
    assert len(observation.lots) == 6 and len(observation.awards) == 8
    for award in observation.awards:
        money, = award.amounts
        assert (money.value, money.raw_value, money.value_state) == (Decimal('0'), '0', 'valid')
    lot1 = observation.lots[0]
    assert sum(award.scope.lot_keys == (lot1.key,) for award in observation.awards) == 2


def test_H11_native_buyer_nif_gross_budget_and_nested_references(api: ModuleType, cases: Cases) -> None:
    observation = cases.get('P-native').one(api)
    assert observation.source.dataset == 'native'
    assert observation.source.origin_platform is None
    assert 'P2802400H' in ids(observation.buyer.identifiers)
    assert not observation.awards
    financial(observation, P_BUDGET, purpose='tender_budget', amount='87184.24', tax='excluded', scope='procedure', currency='EUR')
    financial(observation, xml_path('ext:ContractFolderStatus/cac:ProcurementProject/cac:BudgetAmount/cbc:TotalAmount'), purpose='tender_budget', amount='105492.93', tax='included', scope='procedure', currency='EUR')
    assert {item.value.kind for item in observation.deadlines} == {'offers', 'document_access'}
    assert len(observation.documents) == 1
    assert observation.documents[0].urls
    assert observation.documents[0].reported_hash.algorithm is None
    media = [publication for publication in observation.publications if publication.medium == 'Perfil del contratante']
    assert len(media) == 2 and len({publication.source_path for publication in media}) == 2


@pytest.mark.parametrize('mutation', ['remove_reference', 'ambiguous_lot'])
def test_D12_D13_source_only_lot_references_not_dangling_keys(api: ModuleType, cases: Cases, mutation: str) -> None:
    base = cases.get('C05-P024')
    if mutation == 'remove_reference':
        path = xml_path('ext:ContractFolderStatus/cac:TenderResult[1]/cac:AwardedTenderedProject/cbc:ProcurementProjectLotID')
        parent = xml_path('ext:ContractFolderStatus/cac:TenderResult[1]/cac:AwardedTenderedProject')
        changed = cases.mutate_xml(base, path, lambda entry, node: entry.find(parent).remove(node))
    else:
        path = xml_path('ext:ContractFolderStatus/cac:ProcurementProjectLot[2]/cbc:ID')
        changed = cases.mutate_xml(base, path, lambda entry, node: setattr(node, 'text', '1'))
    observation = changed.one(api)
    assert len(observation.lots) == 13
    first = observation.awards[0]
    assert not first.scope.lot_keys
    if mutation == 'remove_reference':
        assert first.scope.kind == 'unknown'
    else:
        assert first.scope.kind == 'lots' and ids(first.scope.source_lot_identifiers) == ['1']
    assert any(item.code == 'uncertain_scope' and item.path.startswith('raw:') for item in observation.issues)


def test_D17_zero_money_on_negative_result_is_not_award(api: ModuleType, cases: Cases) -> None:
    path = xml_path('ext:ContractFolderStatus/cac:TenderResult')
    def add_zero(entry: ET.Element, result: ET.Element) -> None:
        project = ET.SubElement(result, '{' + NS['cac'] + '}AwardedTenderedProject')
        total = ET.SubElement(project, '{' + NS['cac'] + '}LegalMonetaryTotal')
        ET.SubElement(total, '{' + NS['cbc'] + '}TaxExclusiveAmount', currencyID='EUR').text = '0'
    observation = cases.mutate_xml(cases.get('C09-P000'), path, add_zero).one(api)
    assert not observation.awards
    assert observation.outcomes[0].result.normalized == 'renounced'


def test_D20_repeated_winning_parties_do_not_duplicate_group_total(api: ModuleType, cases: Cases) -> None:
    parent = xml_path('ext:ContractFolderStatus/cac:TenderResult')
    path = parent + '/' + xml_path('cac:WinningParty')[2:]
    observation = cases.mutate_xml(cases.get('C07-P001'), path, lambda entry, node: entry.find(parent).append(deepcopy(node))).one(api)
    award, = observation.awards
    assert len(award.suppliers) == 2 and all(not supplier.amounts for supplier in award.suppliers)
    assert len(award.amounts) == 1 and award.amounts[0].value == Decimal('779542.5')


@pytest.mark.parametrize('remove', ['party', 'identifier'])
def test_D28_missing_supplier_evidence_not_missing_award(api: ModuleType, cases: Cases, remove: str) -> None:
    parent = xml_path('ext:ContractFolderStatus/cac:TenderResult')
    party_path = parent + '/' + xml_path('cac:WinningParty')[2:]
    if remove == 'party':
        changed = cases.mutate_xml(cases.get('C07-P001'), party_path, lambda entry, node: entry.find(parent).remove(node))
    else:
        path = party_path + '/' + xml_path('cac:PartyIdentification')[2:]
        changed = cases.mutate_xml(cases.get('C07-P001'), path, lambda entry, node: entry.find(party_path).remove(node))
    award, = changed.one(api).awards
    if remove == 'party':
        assert not award.suppliers
    else:
        assert not award.suppliers[0].party.identifiers
        assert award.suppliers[0].party.names[0].text == 'SAD ASSITENCIAL COMARQUES MERIDIONALS S.L'
