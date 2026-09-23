from copy import deepcopy
from decimal import Decimal
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from tenderwatch.sources.artifacts import read_document
from tenderwatch.sources.formats import parse_json

from .support import BATCH, CFS, FIXTURES, NS, Cases, P_BUDGET, json_bytes, pack_placsp_reduction, source_at


MAIN_REGRESSIONS = parse_json((FIXTURES / 'normalization/main-regressions.json').read_bytes(), 'main regressions')
PLACSP_REGRESSIONS = parse_json((FIXTURES / 'normalization/placsp-regressions.json').read_bytes(), 'PLACSP regressions')['cases']
ALL_CASES = ('C01-P000', 'C01-P002', 'C07-P001', 'C01-G', 'C05-G1', 'C14-G0', 'C20-G1', 'C09-G', 'C16-parent', 'C19-E0', 'C19-E1', 'J01', 'J14', 'J19', 'J20', 'J16', 'L07', 'T01', 'P-native') + tuple(MAIN_REGRESSIONS) + tuple(PLACSP_REGRESSIONS)


@pytest.mark.parametrize('name', ALL_CASES)
def test_committed_fixture_builds_resolvable_raw_without_normalizer(cases: Cases, name: str) -> None:
    case = cases.get(name)
    payload = case.payload()
    assert isinstance(payload, (dict, ET.Element))
    assert case.raw.raw_record_id.startswith('raw:v1:')
    assert case.raw.observed_at is None
    assert hashlib.sha256(read_document(case.root, case.raw.content)).hexdigest() == case.raw.content.document_sha256
    assert case.raw.content.artifact.path.startswith('001-')


@pytest.mark.parametrize('name,expected', [('C01-P000', '0673d0533cff55933a52e5161ba9412aab950c3c8ae24be2825991e12cfd00a7'), ('C07-P001', 'a0c58be1d89b471312005733343443b5e386d230c58efc68876aab4f53cd5e9a')])
def test_exact_placsp_entry_hashes(name: str, expected: str) -> None:
    assert hashlib.sha256((FIXTURES / 'normalization' / f'{name}.xml.fragment').read_bytes()).hexdigest() == expected


def test_json_mutation_is_single_property_and_decimal_lossless(cases: Cases) -> None:
    base = cases.get('J14')
    before = base.payload()
    path = BATCH + '/0/importAdjudicacioSenseIva'
    changed = cases.mutate_json(base, path, 'not-a-decimal')
    expected = deepcopy(before)
    expected['publicacio']['dadesPublicacio']['contractesAgregada'][0]['importAdjudicacioSenseIva'] = 'not-a-decimal'
    assert changed.payload() == expected
    assert base.payload() == before
    assert changed.recipe == (base.raw.content.document_sha256, path, 'replace')
    precise = {'amount': Decimal('123456789012345678901234567890.1234567890')}
    assert json_bytes(precise) == b'{"amount":123456789012345678901234567890.1234567890}'
    assert parse_json(json_bytes(precise), 'precision') == precise


@pytest.mark.parametrize('name,original', [('C01-P000', '949509.1'), ('P-native', '87184.24')])
def test_xml_mutation_retains_expanded_names_and_unrelated_fields(cases: Cases, name: str, original: str) -> None:
    base = cases.get(name)
    before = base.payload()
    changed = cases.mutate_xml(base, P_BUDGET, lambda entry, node: setattr(node, 'text', 'bad'))
    assert changed.raw.dataset == base.raw.dataset
    assert before.find(P_BUDGET).text == original
    assert changed.payload().find(P_BUDGET).text == 'bad'
    assert changed.payload().find(CFS).tag == before.find(CFS).tag
    assert changed.raw.raw_record_id != base.raw.raw_record_id


def test_fixture_catalogue_documents_every_reduction() -> None:
    catalog = parse_json((FIXTURES / 'normalization/main-cases.json').read_bytes(), 'fixture catalogue')
    for entry in catalog.values():
        assert entry['origin'].startswith('data/samples/')
        assert entry['selection'] == entry['row'][':id']
        assert entry['reduction']


def assert_subset(expected, original, path: str = '') -> None:
    if isinstance(expected, dict):
        assert isinstance(original, dict), path
        for key, value in expected.items():
            assert key in original, path + '/' + key
            assert_subset(value, original[key], path + '/' + key)
    elif isinstance(expected, list):
        assert len(expected) == len(original), path
        for index, value in enumerate(expected):
            assert_subset(value, original[index], path + '/' + str(index))
    else:
        assert expected == original, path


def assert_xml_subset(expected: ET.Element, original: ET.Element) -> None:
    assert expected.tag == original.tag
    assert expected.attrib.items() <= original.attrib.items()
    if not len(expected):
        assert expected.text == original.text
    for tag in dict.fromkeys(child.tag for child in expected):
        children, originals = expected.findall(tag), original.findall(tag)
        assert len(children) <= len(originals)
        for child, source in zip(children, originals):
            assert_xml_subset(child, source)


def test_source_path_helpers_resolve_real_positions(cases: Cases) -> None:
    assert source_at(cases.get('C20-G1').payload(), '/import_adjudicacio_sense#token=1') == ''
    assert source_at(cases.get('C01-P000').payload(), P_BUDGET).text == '949509.1'
    assert source_at(cases.get('C01-G').payload(), 'paths:["/:id","/id_intern"]') == ['row-uvc4~ws2c-5q3s', '4b131001-63ad-4eac-a80a-ab91c3a9f366']


def test_optional_fixture_audit_against_originals(request: pytest.FixtureRequest, cases: Cases) -> None:
    if not request.config.getoption('--audit-normalization-evidence', default=False):
        pytest.skip('Use --audit-normalization-evidence for the optional local research evidence audit')
    root = Path(__file__).resolve().parents[2]
    catalog = {**parse_json((FIXTURES / 'normalization/main-cases.json').read_bytes(), 'fixture catalogue'), **MAIN_REGRESSIONS}
    header = (FIXTURES / 'placsp.atom').read_bytes().split(b'    <author>')[0]
    for spec in PLACSP_REGRESSIONS.values():
        original = ET.fromstring(header + (root / spec['origin']).read_bytes() + b'</feed>')[0]
        reduced = ET.fromstring(pack_placsp_reduction(spec))[0]
        assert_xml_subset(reduced, original)
    native = ET.parse(root / 'data/raw/placsp/probes/native-head.atom').getroot().findall('{' + NS['a'] + '}entry')[1]
    assert_xml_subset(cases.get('P-native').payload(), native)
    for entry in catalog.values():
        source = parse_json((root / entry['origin']).read_bytes(), entry['origin'])
        row, = [row for row in source if row[':id'] == entry['selection']]
        assert_subset(entry['row'], row)
    for alias, publication in [('J01', '300885987'), ('J14', '300339416'), ('J19', '300007312'), ('J20', '300641893')]:
        original = parse_json((root / f'data/raw/gencat/phases/{publication}.json').read_bytes(), publication)
        fixture = parse_json((FIXTURES / 'normalization' / f'{alias}.json').read_bytes(), alias)
        assert_subset(fixture, original)
    for name, folder, fragment in [('C01-P000', '01_amb_correction', 'placsp-000.xml.fragment'), ('C07-P001', '07_equivalent_projection', 'placsp-001.xml.fragment')]:
        assert (FIXTURES / 'normalization' / f'{name}.xml.fragment').read_bytes() == (root / 'data/samples' / folder / fragment).read_bytes()
