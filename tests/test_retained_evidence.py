import hashlib
import json
from pathlib import Path

import pytest

from tenderwatch.raw import RecordKind, to_raw
from tenderwatch.sources.artifacts import identify_artifact, load_record, read_document
from tenderwatch.sources.gencat import read_gencat_publication


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures'


def test_placsp_fixture_contains_exact_retained_entry():
    data = (FIXTURES / 'placsp.atom').read_bytes()
    entry = data[data.index(b'<entry>'):data.index(b'</entry>') + len(b'</entry>')]
    assert hashlib.sha256(entry).hexdigest() == 'e66979d1ec776c98d0a3db22c88fd56526f2c8ae065cfd4bc7566e77b7ad255c'


@pytest.mark.parametrize('fixture,original', [
    ('gencat-execution.json', 'data/raw/gencat/8idu-wkjv/probe.json'),
    ('gencat-main.json', 'data/samples/01_amb_correction/gencat-rows.json'),
    ('gencat-publication.json', 'data/raw/gencat/phases/300831068.json'),
])
def test_fixture_matches_retained_evidence_when_available(fixture, original):
    path = ROOT / original
    if not path.exists():
        pytest.skip('Optional local evidence not installed; fixture-only tests remain offline')
    assert (FIXTURES / fixture).read_bytes().rstrip(b'\n') == path.read_bytes().rstrip(b'\n')


def test_batch_excerpt_matches_retained_fields_when_available():
    path = ROOT / 'data/raw/gencat/phases/300339416.json'
    if not path.exists():
        pytest.skip('Optional local batch evidence not installed')
    excerpt = json.loads((FIXTURES / 'gencat-batch-excerpt.json').read_bytes())
    original = json.loads(path.read_bytes())
    members = excerpt['publicacio']['dadesPublicacio']['contractesAgregada']
    for index, member in enumerate(members):
        for key, value in member.items():
            assert original['publicacio']['dadesPublicacio']['contractesAgregada'][index][key] == value
    for key in ('idExpedient', 'codiExpedient', 'versio', 'dataPublicacioReal', 'dataPublicacioPlanificada'):
        assert original[key] == excerpt[key]
    raw, = (to_raw(record) for record in read_gencat_publication(ROOT, identify_artifact(ROOT, path.relative_to(ROOT).as_posix())))
    assert len(load_record(ROOT, raw.content)['publicacio']['dadesPublicacio']['contractesAgregada']) == 6


@pytest.mark.parametrize('name', ['102238048', '103585423', '107376474', '115526013'])
def test_complete_legacy_body_when_available(name):
    relative = f'data/raw/gencat/legacy_probes/{name}.bin'
    path = ROOT / relative
    if not path.exists():
        pytest.skip('Optional local legacy body not installed')
    source, = read_gencat_publication(ROOT, identify_artifact(ROOT, relative))
    raw = to_raw(source)
    assert raw.record_kind == RecordKind.GENCAT_PUBLICATION_XML
    assert read_document(ROOT, raw.content) == path.read_bytes()
    assert load_record(ROOT, raw.content).tag == 'Notice'
    if name == '103585423':
        excerpt = (FIXTURES / 'gencat-legacy-excerpt.xml').read_bytes()
        prefix = excerpt.split(b'</com.capgemini.gencat.economia.pscp.entity.PscpContractNotice>')[0]
        assert path.read_bytes().startswith(prefix)
