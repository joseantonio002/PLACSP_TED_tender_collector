import hashlib
import json
from pathlib import Path

import pytest

from tenderwatch.raw import to_raw
from tenderwatch.sources.__main__ import main
from tenderwatch.sources.artifacts import read_manifest_line
from tenderwatch.sources.errors import ArtifactReadError, IntegrityError, LocatorError, SourceFormatError
from tenderwatch.sources.retained import discover_inputs


FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.fixture
def snapshot(tmp_path):
    relative = 'data/raw/gencat/8idu-wkjv/pages/000000000.json'
    page = tmp_path / relative
    page.parent.mkdir(parents=True)
    data = (FIXTURES / 'gencat-execution.json').read_bytes()
    page.write_bytes(data)
    metadata = page.parent.parent / 'metadata-before.json'
    metadata.write_bytes(b'{"id":"8idu-wkjv","rowsUpdatedAt":123}')
    acquisition = {
        'source': 'gencat', 'filename': relative, 'validated': True,
        'source_url': 'https://analisi.transparenciacatalunya.cat/resource/8idu-wkjv.json',
        'resolved_url': 'https://analisi.transparenciacatalunya.cat/resource/8idu-wkjv.json?%24offset=0',
        'downloaded_at': '2026-09-22T16:01:00+00:00',
        'download_started_at': '2026-09-22T16:00:00+00:00',
        'request_parameters': {'$offset': 0, '$select': '*,:id,:created_at,:updated_at', '$where': '1=1'},
        'response_headers': {'Content-Type': 'application/json'},
        'period': 'initial period label',
        'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data),
    }
    meta_acquisition = {
        **acquisition, 'filename': metadata.relative_to(tmp_path).as_posix(),
        'source_url': 'https://analisi.transparenciacatalunya.cat/api/views/8idu-wkjv.json',
        'sha256': hashlib.sha256(metadata.read_bytes()).hexdigest(), 'size_bytes': metadata.stat().st_size,
    }
    annotation = {
        'event': 'metadata_annotation', 'applies_to_filename': relative,
        'field': 'period', 'corrected_value': 'all available execution actions; local date profiling',
    }
    entries = [acquisition, {**acquisition, 'validated': False, 'filename': 'missing.json'}, meta_acquisition, annotation]
    manifest = tmp_path / 'data/raw/download_manifest.jsonl'
    manifest.write_text(''.join(json.dumps(entry) + '\n' for entry in entries))
    return tmp_path, acquisition, manifest


def test_discovery_and_raw_acquisition_lineage(snapshot):
    root, acquisition, manifest = snapshot
    retained, = discover_inputs(root)
    records = list(retained.read(root))
    assert len(records) == 5
    raw = to_raw(records[0])
    artifact = raw.content.artifact
    assert artifact.path == acquisition['filename']
    assert artifact.sha256 == acquisition['sha256']
    assert raw.observed_at == acquisition['downloaded_at']
    assert artifact.acquisition.source_url == acquisition['source_url']
    assert artifact.acquisition.resolved_url == acquisition['resolved_url']
    assert artifact.acquisition.manifest_line.line_number == 1
    assert read_manifest_line(root, artifact.acquisition.manifest_line) == acquisition
    assert read_manifest_line(root, artifact.acquisition.annotations[0])['field'] == 'period'
    assert len(raw.context_artifacts) == 1
    assert raw.context_artifacts[0].path.endswith('/metadata-before.json')
    original_id = raw.raw_record_id
    with manifest.open('a') as stream:
        stream.write(json.dumps({'validated': False}) + '\n')
    assert to_raw(next(next(discover_inputs(root)).read(root))).raw_record_id == original_id
    with manifest.open('a') as stream:
        stream.write(json.dumps(acquisition) + '\n')
    again = list(discover_inputs(root))
    assert len(again) == 2
    assert to_raw(next(again[1].read(root))).raw_record_id != original_id


def test_missing_manifest_artifact_does_not_silently_disappear(snapshot):
    root, acquisition, manifest = snapshot
    acquisition['filename'] = 'data/raw/gencat/8idu-wkjv/pages/missing.json'
    manifest.write_text(json.dumps(acquisition) + '\n')
    retained, = discover_inputs(root)
    with pytest.raises(ArtifactReadError):
        list(retained.read(root))


def test_missing_referenced_context_fails(snapshot):
    root, _, manifest = snapshot
    entries = [json.loads(line) for line in manifest.read_text().splitlines()]
    entries[2]['filename'] = 'data/raw/gencat/8idu-wkjv/metadata-after.json'
    manifest.write_text(''.join(json.dumps(entry) + '\n' for entry in entries))
    retained, = discover_inputs(root)
    with pytest.raises(ArtifactReadError):
        list(retained.read(root))


def test_manifest_checksum_mismatch(snapshot):
    root, acquisition, manifest = snapshot
    acquisition['sha256'] = '0' * 64
    manifest.write_text(json.dumps(acquisition) + '\n')
    with pytest.raises(IntegrityError):
        list(next(discover_inputs(root)).read(root))


def test_manifest_reference_detects_edits(snapshot):
    root, acquisition, manifest = snapshot
    retained, = discover_inputs(root)
    acquisition['period'] = 'changed'
    manifest.write_text(json.dumps(acquisition) + '\n')
    with pytest.raises(IntegrityError):
        read_manifest_line(root, retained.artifact.acquisition.manifest_line)


def test_manifest_path_cannot_escape_root(snapshot):
    root, acquisition, manifest = snapshot
    acquisition['filename'] = '../outside.json'
    manifest.write_text(json.dumps(acquisition) + '\n')
    with pytest.raises(LocatorError):
        list(discover_inputs(root))


@pytest.mark.parametrize('data', ['{', '[]', '{"validated":true}', '{"validated":true,"filename":42}'])
def test_malformed_manifest(tmp_path, data):
    (tmp_path / 'manifest.jsonl').write_text(data)
    with pytest.raises(SourceFormatError):
        list(discover_inputs(tmp_path, manifest='manifest.jsonl'))


def test_traversal_command(snapshot, capsys):
    root, _, _ = snapshot
    assert main(['--root', str(root)]) == 0
    result = capsys.readouterr()
    assert 'gencat\t8idu-wkjv\tgencat_execution_row\t5' in result.out
    assert 'checksums verified' in result.out
    assert 'Reading data/raw/' in result.err
    assert main(['--root', str(root), '--source', 'placsp']) == 1
    assert 'counts incomplete' in capsys.readouterr().err
