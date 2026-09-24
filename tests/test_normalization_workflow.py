from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import pytest

from tenderwatch.inspection import serialize
from tenderwatch.normalization import NormalizationInvariantError
from tenderwatch.sources.__main__ import main
from tenderwatch.sources.artifacts import identify_artifact, load_record, verified_resolver
from tenderwatch.sources.errors import IntegrityError, LocatorError
from tenderwatch.sources.gencat import read_gencat_main
from tenderwatch.sources.placsp import read_placsp


FIXTURES = Path(__file__).parent / 'fixtures'


def snapshot(tmp_path, files):
    manifest = tmp_path / 'data/raw/download_manifest.jsonl'
    manifest.parent.mkdir(parents=True)
    entries = []
    for relative, fixture in files:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        data = (FIXTURES / fixture).read_bytes()
        path.write_bytes(data)
        entries.append({'source': 'gencat', 'filename': relative, 'validated': True,
                        'source_url': 'https://contractaciopublica.cat/portal-api/documents-publicacio/json/300339416',
                        'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data)})
    manifest.write_text(''.join(json.dumps(entry) + '\n' for entry in entries))


def test_command_collects_batch_members_and_reports_unsupported(tmp_path, capsys):
    snapshot(tmp_path, [('data/raw/gencat/phases/batch.json', 'normalization/J14.json'),
                        ('data/raw/gencat/phases/legacy.bin', 'gencat-legacy-excerpt.xml')])
    assert main(['--root', str(tmp_path), '--output-parent', str(tmp_path)]) == 0
    output, = tmp_path.glob('tenderwatch-inspection-*')
    observations = [json.loads(line) for line in (output / 'observations.jsonl').read_text().splitlines()]
    assert len(observations) == 6
    assert len({item['raw_source_record_id'] for item in observations}) == 1
    assert len({item['observation_id'] for item in observations}) == 6
    assert observations[0]['financials'][0]['value']['value'] == '28957.25'
    failures = [json.loads(line) for line in (output / 'failures.jsonl').read_text().splitlines()]
    assert failures[0]['reason'] == 'unsupported_structure_or_format'
    summary = json.loads((output / 'summary.json').read_text())
    assert summary['raw_occurrences'] == 2 and summary['observations'] == 6
    assert summary['production'] is False
    printed = capsys.readouterr()
    assert printed.out.count('RawSourceRecord ') == 2
    assert 'NormalizedObservation(s): 6' in printed.out
    assert 'Normalization failure' in printed.out


def test_command_limit_preview_and_new_output_each_time(tmp_path, capsys):
    snapshot(tmp_path, [(f'data/raw/gencat/phases/{i}.json', 'normalization/J01.json') for i in range(5)])
    args = ['--root', str(tmp_path), '--output-parent', str(tmp_path), '--limit', '4']
    assert main(args) == 0
    output, = tmp_path.glob('tenderwatch-inspection-*')
    assert len((output / 'observations.jsonl').read_text().splitlines()) == 4
    assert json.loads((output / 'summary.json').read_text())['status'] == 'limited'
    printed = capsys.readouterr()
    assert printed.out.count('RawSourceRecord ') == 3
    assert 'source_path_token' not in printed.out
    assert main(args) == 0
    assert len(list(tmp_path.glob('tenderwatch-inspection-*'))) == 2


def test_raw_only_does_not_create_output(tmp_path, capsys):
    snapshot(tmp_path, [('data/raw/gencat/phases/body.json', 'normalization/J01.json')])
    assert main(['--root', str(tmp_path), '--raw-only', '--output-parent', str(tmp_path)]) == 0
    assert not list(tmp_path.glob('tenderwatch-inspection-*'))
    assert 'NormalizedObservation' not in capsys.readouterr().out


def test_unexpected_mapper_errors_are_not_controlled_failures(tmp_path, monkeypatch):
    snapshot(tmp_path, [('data/raw/gencat/phases/body.json', 'normalization/J01.json')])
    def broken(*args, **kwargs):
        raise NormalizationInvariantError('fault injection')
    monkeypatch.setattr('tenderwatch.sources.__main__.normalize', broken)
    with pytest.raises(NormalizationInvariantError):
        main(['--root', str(tmp_path), '--output-parent', str(tmp_path)])
    output, = tmp_path.glob('tenderwatch-inspection-*')
    assert json.loads((output / 'summary.json').read_text())['status'] != 'complete'


def test_inspection_decimal_is_lossless():
    assert json.loads(serialize({'value': Decimal('12345678901234567890.1234567890')}))['value'] == '12345678901234567890.1234567890'


def test_cached_resolver_preserves_row_selection_and_integrity(tmp_path, monkeypatch):
    (tmp_path / 'rows.json').write_bytes((FIXTURES / 'gencat-main.json').read_bytes())
    artifact = identify_artifact(tmp_path, 'rows.json')
    source, = read_gencat_main(tmp_path, artifact)
    import tenderwatch.sources.artifacts as access
    original = access.parse_json
    calls = []
    def counted(*args):
        calls.append(args[1])
        return original(*args)
    monkeypatch.setattr(access, 'parse_json', counted)
    with verified_resolver(tmp_path, artifact) as resolve:
        first = resolve(source.content)
        assert resolve(source.content) is first
        assert len(calls) == 1
        with pytest.raises(IntegrityError):
            resolve(replace(source.content, document_sha256='0' * 64))
        with pytest.raises(LocatorError):
            resolve(replace(source.content, locator=replace(source.content.locator, ordinal=99)))
        with pytest.raises(LocatorError):
            resolve(replace(source.content, artifact=replace(artifact, path='elsewhere.json')))


def test_cached_resolver_zip_members_and_tombstone_ordinals(tmp_path):
    data = (FIXTURES / 'placsp.atom').read_bytes()
    with zipfile.ZipFile(tmp_path / 'source.zip', 'w') as archive:
        archive.writestr('first.atom', data)
        archive.writestr('second.atom', data)
    artifact = identify_artifact(tmp_path, 'source.zip')
    records = list(read_placsp(tmp_path, artifact, dataset='aggregated'))
    with verified_resolver(tmp_path, artifact) as resolve:
        for record in records:
            assert ET.tostring(resolve(record.content)) == ET.tostring(load_record(tmp_path, record.content))
        bad = replace(records[0].content.locator, member_name='missing.atom')
        with pytest.raises(LocatorError):
            resolve(replace(records[0].content, locator=bad))
