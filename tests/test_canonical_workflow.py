from importlib import import_module
import json
from pathlib import Path

import pytest

import tenderwatch.normalization as normalization
from tenderwatch.inspection import serialize
from tenderwatch.sources.__main__ import main
from normalization.support import Cases
from test_normalization_workflow import snapshot as initial_snapshot


def snapshot(root, files):
    if not (root / 'data/raw/download_manifest.jsonl').exists():
        initial_snapshot(root, files)
        return
    import hashlib
    entries = []
    for relative, fixture in files:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        data = (Path(__file__).parent / 'fixtures' / fixture).read_bytes()
        path.write_bytes(data)
        entries.append({'source': 'gencat', 'filename': relative, 'validated': True,
                        'source_url': 'https://contractaciopublica.cat/portal-api/documents-publicacio/json/300339416',
                        'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data)})
    (root / 'data/raw/download_manifest.jsonl').write_text(''.join(json.dumps(entry) + '\n' for entry in entries))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


@pytest.mark.parametrize('case_name', ['C01-P000', 'C01-G', 'C05-G1', 'C19-E0', 'J01', 'J19', 'J20'])
def test_materialized_normalized_round_trip_preserves_types(tmp_path, case_name):
    codec = import_module('tenderwatch.serialization')
    original = Cases(tmp_path).get(case_name).one(normalization)
    restored = codec.load_observation(serialize(original))
    assert restored == original
    normalization.validate_observation(restored)
    assert serialize(restored) == serialize(original)


def test_workflow_materializes_both_stages_and_traceable_canonical(tmp_path, capsys):
    snapshot(tmp_path, [('data/raw/gencat/phases/a.json', 'normalization/J01.json'),
                        ('data/raw/gencat/phases/b.json', 'normalization/J01.json')])
    assert main(['--root', str(tmp_path)]) == 0
    normalized_path = tmp_path / 'data/NormalizedObservations/observations.jsonl'
    canonical_path = tmp_path / 'data/CanonicalObservations/canonical.jsonl'
    normalized = read_jsonl(normalized_path)
    canonical, = read_jsonl(canonical_path)
    assert len(normalized) == 2
    assert set(canonical['normalized_observation_ids']) == {o['observation_id'] for o in normalized}
    assert canonical['resolution_provenance']
    assert 'current_state' in canonical and 'conflicts' in canonical
    assert not list(tmp_path.glob('tenderwatch-inspection-*'))
    assert {p.name for p in canonical_path.parent.iterdir()} == {'canonical.jsonl'}
    summary = json.loads((tmp_path / 'data/ProcessingRuns/current/summary.json').read_text())
    assert summary['normalized_observations'] == 2
    assert summary['canonical_observations'] == 1
    assert summary['unresolved_observations'] == 0
    printed = capsys.readouterr().out
    assert 'Entity Resolution:' in printed and 'CanonicalObservation' in printed
    assert 'NormalizedObservations' in printed and 'CanonicalObservations' in printed


def test_rerun_is_byte_deterministic_and_does_not_mix_previous_output(tmp_path):
    snapshot(tmp_path, [('data/raw/gencat/phases/body.json', 'normalization/J01.json')])
    args = ['--root', str(tmp_path)]
    assert main(args) == 0
    old_current = (tmp_path / 'data/ProcessingRuns/current').resolve()
    canonical_path = tmp_path / 'data/CanonicalObservations/canonical.jsonl'
    first = canonical_path.read_bytes()
    assert main(args) == 0
    assert canonical_path.read_bytes() == first
    assert (tmp_path / 'data/ProcessingRuns/current').resolve() != old_current
    assert (old_current / 'CanonicalObservations/canonical.jsonl').read_bytes() == first
    snapshot(tmp_path, [('data/raw/gencat/phases/batch.json', 'normalization/J14.json')])
    assert main(args) == 0
    assert read_jsonl(canonical_path) == []
    normalized = read_jsonl(tmp_path / 'data/NormalizedObservations/observations.jsonl')
    assert len(normalized) == 6
    unresolved = read_jsonl(tmp_path / 'data/ProcessingRuns/current/unresolved.jsonl')
    assert {u['observation_id'] for u in unresolved} == {o['observation_id'] for o in normalized}


def test_failed_rerun_does_not_publish_partial_or_mismatched_stages(tmp_path, monkeypatch):
    snapshot(tmp_path, [('data/raw/gencat/phases/body.json', 'normalization/J01.json')])
    args = ['--root', str(tmp_path)]
    assert main(args) == 0
    previous = (tmp_path / 'data/ProcessingRuns/current').resolve()
    def fail(*args, **kwargs):
        raise RuntimeError('injected mapper defect')
    monkeypatch.setattr('tenderwatch.sources.__main__.normalize', fail)
    with pytest.raises(RuntimeError, match='injected'):
        main(args)
    assert (tmp_path / 'data/ProcessingRuns/current').resolve() == previous
    assert (tmp_path / 'data/NormalizedObservations').resolve().parent == previous
    assert (tmp_path / 'data/CanonicalObservations').resolve().parent == previous


def test_does_not_overwrite_an_unmanaged_output_directory(tmp_path):
    snapshot(tmp_path, [('data/raw/gencat/phases/body.json', 'normalization/J01.json')])
    output = tmp_path / 'data/NormalizedObservations'
    output.mkdir()
    marker = output / 'user-file.json'
    marker.write_text('preserve me')
    assert main(['--root', str(tmp_path)]) == 1
    assert marker.read_text() == 'preserve me'


@pytest.mark.parametrize('failure', ['canonical_write', 'final_summary', 'publish'])
def test_io_failure_never_replaces_previous_completed_output(tmp_path, monkeypatch, failure):
    from tenderwatch.materialization import MaterializedRun
    snapshot(tmp_path, [('data/raw/gencat/phases/body.json', 'normalization/J01.json')])
    args = ['--root', str(tmp_path)]
    assert main(args) == 0
    previous = (tmp_path / 'data/ProcessingRuns/current').resolve()
    original_summary = MaterializedRun.summary
    original_open = Path.open
    if failure == 'final_summary':
        def write_summary(self, values):
            if values['status'] in ('complete', 'complete_with_unsupported', 'limited'):
                raise OSError('simulated disk full')
            return original_summary(self, values)
        monkeypatch.setattr(MaterializedRun, 'summary', write_summary)
    elif failure == 'publish':
        def publish(self):
            raise OSError('simulated publication failure')
        monkeypatch.setattr(MaterializedRun, 'publish', publish)
    else:
        def open_file(self, mode='r', *args, **kwargs):
            if self.name == 'canonical.jsonl' and mode == 'x':
                raise OSError('simulated disk full')
            return original_open(self, mode, *args, **kwargs)
        monkeypatch.setattr(Path, 'open', open_file)
    assert main(args) == 1
    assert (tmp_path / 'data/ProcessingRuns/current').resolve() == previous


def test_materialized_data_is_input_to_canonical_stage(tmp_path):
    snapshot(tmp_path, [('data/raw/gencat/phases/body.json', 'normalization/J19.json')])
    assert main(['--root', str(tmp_path)]) == 0
    codec = import_module('tenderwatch.serialization')
    api = import_module('tenderwatch.canonical')
    lines = (tmp_path / 'data/NormalizedObservations/observations.jsonl').read_text().splitlines()
    observations = [codec.load_observation(line) for line in lines]
    expected = api.canonicalize(observations).canonical_observations
    actual = read_jsonl(tmp_path / 'data/CanonicalObservations/canonical.jsonl')
    assert actual == [json.loads(serialize(c)) for c in expected]
