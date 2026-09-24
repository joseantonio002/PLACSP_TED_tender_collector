from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Any
import uuid

from tenderwatch.canonical.models import CanonicalObservation, UnresolvedObservation
from tenderwatch.canonical.reconciliation import Reconciler
from tenderwatch.canonical.resolution import ResolutionIndex, identity_from_dict
from tenderwatch.inspection import create_output
from tenderwatch.serialization import load_observation, serialize

OUTPUTS = ('NormalizedObservations', 'CanonicalObservations')


class MaterializedRun:
    def __init__(self, root: Path, inspection_parent: Path | None = None) -> None:
        self.data = root.resolve() / 'data'
        self.runs = self.data / 'ProcessingRuns'
        for name in OUTPUTS:
            path = self.data / name
            expected = f'ProcessingRuns/current/{name}'
            if path.is_symlink():
                if os.readlink(path) != expected:
                    raise FileExistsError(f'Refusing to replace unmanaged output link: {path}')
            elif path.exists():
                raise FileExistsError(f'Refusing to replace unmanaged output directory: {path}')
        current = self.runs / 'current'
        if current.is_symlink():
            target = Path(os.readlink(current))
            if target.is_absolute() or len(target.parts) != 1 or not target.name.startswith('run-'):
                raise FileExistsError(f'Refusing to replace unmanaged run pointer: {current}')
        elif current.exists():
            raise FileExistsError(f'Refusing to replace unmanaged run pointer: {current}')
        self.path = self.runs / ('run-' + uuid.uuid4().hex)
        for name in OUTPUTS:
            (self.path / name).mkdir(parents=True)
        self.normalized = self.path / 'NormalizedObservations/observations.jsonl'
        self.canonical = self.path / 'CanonicalObservations/canonical.jsonl'
        self.inspection = None
        if inspection_parent is not None:
            self.inspection = create_output(inspection_parent)
            for name, target in (('observations.jsonl', self.normalized), ('failures.jsonl', self.path / 'failures.jsonl'), ('summary.json', self.path / 'summary.json')):
                (self.inspection / name).symlink_to(target)

    def summary(self, values: dict[str, Any]) -> None:
        (self.path / 'summary.json').write_text(serialize(values) + '\n', encoding='utf-8')

    def publish(self) -> None:
        if not self.normalized.is_file() or not self.canonical.is_file():
            raise ValueError('Both materialized stages must exist before publication')
        for name in OUTPUTS:
            path = self.data / name
            if not path.is_symlink():
                path.symlink_to(f'ProcessingRuns/current/{name}', target_is_directory=True)
            elif os.readlink(path) != f'ProcessingRuns/current/{name}':
                raise FileExistsError(f'Output link changed during processing: {path}')
        pointer = self.runs / ('pending-' + self.path.name)
        pointer.symlink_to(self.path.name, target_is_directory=True)
        pointer.replace(self.runs / 'current')


@dataclass(frozen=True, slots=True)
class CanonicalRunResult:
    canonical_observations: int
    unresolved_observations: int
    unresolved_identity_groups: int
    reconciliation_conflicts: int
    unresolved_reasons: tuple[tuple[str, int], ...]
    examples: tuple[dict[str, Any], ...]


def canonical_preview(canonical: CanonicalObservation) -> dict[str, Any]:
    state = canonical.current_state
    return {
        'canonical_id': canonical.canonical_id,
        'normalized_observation_ids': canonical.normalized_observation_ids[:3],
        'total_evidence_observations': len(canonical.normalized_observation_ids),
        'rules': sorted({decision.rule for decision in canonical.resolution_provenance}),
        'current_state': {
            'procedure_numbers': [fact.value.value for fact in state.procedure_numbers if fact.value is not None][:3],
            'titles': [fact.value.text[:180] for fact in state.titles if fact.value is not None][:2],
            'financials': [{'purpose': fact.value.purpose, 'amount': fact.value.value, 'scope': fact.scope.kind,
                           'currency': fact.value.currency, 'tax_basis': fact.value.tax_basis}
                          for fact in state.financials if fact.value is not None][:4],
            'lots': len(state.lots), 'awards': len(state.awards), 'execution_actions': len(state.execution_actions),
        },
        'unresolved_conflicts': len(canonical.conflicts),
    }


def reconcile_materialized(run: MaterializedRun, index: ResolutionIndex) -> CanonicalRunResult:
    index.finalize()
    reasons: Counter[str] = Counter()
    count = conflicts = 0
    examples = []
    unresolved_groups = sum(value is None for value in index.decisions.values())
    with tempfile.TemporaryDirectory(prefix='work-', dir=run.path) as work, ExitStack() as stack:
        buckets = {}
        unresolved = stack.enter_context((run.path / 'unresolved.jsonl').open('x', encoding='utf-8'))
        with run.normalized.open(encoding='utf-8') as stream:
            for line in stream:
                identity = identity_from_dict(json.loads(line))
                decision = index.resolve(identity)
                if isinstance(decision, UnresolvedObservation):
                    unresolved.write(serialize(decision) + '\n')
                    reasons[decision.reason] += 1
                    continue
                bucket = decision.removeprefix('canonical:v1:')[:2]
                if bucket not in buckets:
                    buckets[bucket] = stack.enter_context((Path(work) / (bucket + '.jsonl')).open('x', encoding='utf-8'))
                buckets[bucket].write(decision + '\t' + line)
        for stream in buckets.values():
            stream.close()
        with run.canonical.open('x', encoding='utf-8') as output:
            for bucket in sorted(buckets):
                groups: dict[str, Reconciler] = {}
                with (Path(work) / (bucket + '.jsonl')).open(encoding='utf-8') as stream:
                    for line in stream:
                        canonical_id, observation_json = line.split('\t', 1)
                        if canonical_id not in groups:
                            groups[canonical_id] = Reconciler(canonical_id)
                        groups[canonical_id].add(load_observation(observation_json))
                for canonical_id in sorted(groups):
                    canonical = groups[canonical_id].finish()
                    output.write(serialize(canonical) + '\n')
                    count += 1
                    conflicts += len(canonical.conflicts)
                    if len(examples) < 3:
                        examples.append(canonical_preview(canonical))
    return CanonicalRunResult(count, sum(reasons.values()), unresolved_groups, conflicts, tuple(sorted(reasons.items())), tuple(examples))
