from copy import deepcopy
from datetime import date
from decimal import Decimal
from types import ModuleType
import xml.etree.ElementTree as ET

import pytest

from tenderwatch.sources.artifacts import read_document

from .support import CFS, Cases, NS, P_BUDGET, ids, issue, semantic, xml_path


def test_D21_prefix_equivalence_but_not_namespace_equivalence(api: ModuleType, cases: Cases) -> None:
    base = cases.get('C01-P000')
    before = base.one(api)
    renamed = read_document(base.root, base.raw.content).replace(b'cac-place-ext', b'extension')
    after = cases.from_bytes('prefix-only-synthetic', renamed, 'placsp').one(api)
    assert semantic(before) == semantic(after)
    wrong = cases.mutate_xml(base, CFS, lambda entry, node: setattr(node, 'tag', '{urn:wrong-namespace}ContractFolderStatus'))
    with pytest.raises(api.InvalidNormalizationInput) as caught:
        wrong.normalize(api)
    assert caught.value.reason == 'missing_root_or_wrong_shape'


def test_D19_repeated_media_dates_preserve_occurrences(api: ModuleType, cases: Cases) -> None:
    parent = xml_path('ext:ContractFolderStatus/ext:ValidNoticeInfo/ext:AdditionalPublicationStatus[1]')
    path = parent + '/' + xml_path('ext:AdditionalPublicationDocumentReference')[2:]
    def add_reference(entry: ET.Element, node: ET.Element) -> None:
        copied = deepcopy(node)
        copied.find('{' + NS['cbc'] + '}IssueDate').text = '2026-08-12'
        entry.find(parent).append(copied)
    observation = cases.mutate_xml(cases.get('C01-P000'), path, add_reference).one(api)
    media = [p for p in observation.publications if p.medium == 'Perfil del contratante']
    assert len(media) == 2
    assert {p.publication_at.local_date for p in media} == {date(2026, 8, 11), date(2026, 8, 12)}
    assert len({p.source_path for p in media}) == 2
    assert all(not p.identifiers for p in media)


def test_D14_duration_unknown_unit_is_not_converted(api: ModuleType, cases: Cases) -> None:
    path = xml_path('ext:ContractFolderStatus/cac:ProcurementProject/cac:PlannedPeriod/cbc:DurationMeasure')
    observation = cases.mutate_xml(cases.get('C01-P000'), path, lambda entry, node: node.set('unitCode', 'unknown')).one(api)
    duration, = observation.performance_periods[0].value.duration
    assert duration.value == Decimal('2') and duration.unit == 'unspecified'
    issue(observation, 'unmapped_code', path + '/@unitCode')


def test_D18_multiple_rates_do_not_assert_single_vat_rate(api: ModuleType, cases: Cases) -> None:
    path = '/publicacio/dadesPublicacio/varisTipusIva'
    observation = cases.mutate_json(cases.get('J01'), path, True).one(api)
    amount, = [item.value for item in observation.financials if item.source_path == '/publicacio/dadesPublicacio/pressupostLicitacio']
    assert amount.multiple_vat_rates is True and amount.vat_rate is None
    assert amount.value == Decimal('949509.1')


@pytest.mark.parametrize('token', ['00/2025', '006_24001098', '  Ab-01 / 2025 '])
def test_I17_identifier_spelling_is_not_a_matching_key(api: ModuleType, cases: Cases, token: str) -> None:
    observation = cases.mutate_json(cases.get('C01-G'), '/codi_expedient', token).one(api)
    assert ids(observation.procedure_numbers) == [token]


@pytest.mark.parametrize('name', ['C01-G', 'C19-E0'])
def test_G14_empty_table_object_has_no_procurement_subject(api: ModuleType, cases: Cases, name: str) -> None:
    kind = 'main' if name == 'C01-G' else 'execution'
    case = cases.from_bytes('empty-object-synthetic', b'[{}]', kind)
    with pytest.raises(api.UnsupportedNormalizationInput) as caught:
        case.normalize(api)
    assert caught.value.reason == 'unprojectable_subject'


@pytest.mark.parametrize('name', ['J01', 'J19', 'J20'])
def test_F07_ordinary_body_does_not_accept_arbitrary_subject_pointer(api: ModuleType, cases: Cases, name: str) -> None:
    case = cases.get(name)
    with pytest.raises(api.InvalidNormalizationInput) as caught:
        case.normalize(api, projection='/not-a-supported-subject')
    assert caught.value.reason == 'unresolvable_projection'


def test_S29_same_source_id_and_clock_do_not_collapse_raw_occurrences(api: ModuleType, cases: Cases) -> None:
    base = cases.get('C01-P000')
    changed = cases.mutate_xml(base, P_BUDGET, lambda entry, node: setattr(node, 'text', '949510'))
    first, second = base.one(api), changed.one(api)
    assert ids(first.source.record_identifiers) == ids(second.source.record_identifiers)
    assert first.source_markers == second.source_markers
    assert first.raw_source_record_id != second.raw_source_record_id
    assert first.observation_id != second.observation_id
    assert next(item.value.value for item in first.financials if item.source_path == P_BUDGET) == Decimal('949509.1')
    assert next(item.value.value for item in second.financials if item.source_path == P_BUDGET) == Decimal('949510')


def test_D15_absent_buyer_is_not_missing_provenance(api: ModuleType, cases: Cases) -> None:
    path = xml_path('ext:ContractFolderStatus/ext:LocatedContractingParty')
    case = cases.mutate_xml(cases.get('C01-P000'), path, lambda entry, node: entry.find(CFS).remove(node))
    observation = case.one(api)
    assert observation.buyer is None
    assert observation.financials and observation.titles
    assert ids(observation.procedure_numbers) == ['905451/26']
    assert not any(item.path == 'raw:' + path for item in observation.issues)


def test_unknown_host_cannot_supply_pscp_identifiers(api: ModuleType, cases: Cases) -> None:
    base = cases.get('C01-G')
    original_url = base.payload()['enllac_publicacio']['url']
    changed_url = original_url.replace('contractaciopublica.cat', 'example.invalid')
    observation = cases.mutate_json(base, '/enllac_publicacio/url', changed_url).one(api)
    reference, = [reference for reference in observation.source_references if reference.url == changed_url]
    assert not reference.identifiers
