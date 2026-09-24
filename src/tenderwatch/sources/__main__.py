from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack, closing, nullcontext
from fnmatch import fnmatchcase
from pathlib import Path
import sys

from tenderwatch.canonical import RECONCILIATION_VERSION, RESOLUTION_VERSION, SCHEMA_VERSION
from tenderwatch.canonical.resolution import ResolutionIndex, identity_record
from tenderwatch.inspection import failure_summary, preview
from tenderwatch.materialization import MaterializedRun, reconcile_materialized
from tenderwatch.normalization import NormalizationError, UnsupportedNormalizationInput, normalize
from tenderwatch.raw import to_raw
from tenderwatch.serialization import serialize
from tenderwatch.sources.artifacts import verified_resolver
from tenderwatch.sources.errors import RawSourceError
from tenderwatch.sources.retained import discover_inputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Normalize retained data, conservatively resolve procedure identity, and materialize reconciled canonical observations.')
    parser.add_argument('--root', type=Path, default=Path.cwd(), help='Repository/snapshot root containing data/raw')
    parser.add_argument('--source', choices=('all', 'placsp', 'gencat'), default='all')
    parser.add_argument('--artifact', action='append', default=[], help='Optional retained artifact path glob; repeat to select several patterns')
    parser.add_argument('--limit', type=int, help='Stop after this many raw occurrences; publish an explicitly limited run')
    parser.add_argument('--output-parent', type=Path, help='Optional existing parent for legacy inspection aliases; materialized outputs always remain under root/data')
    parser.add_argument('--raw-only', action='store_true', help='Only traverse/count raw records; do not create materialized output')
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be positive')
    if args.output_parent is not None and not args.output_parent.is_dir():
        parser.error('--output-parent must be an existing directory')
    counts: Counter[tuple[str, str, str]] = Counter()
    diagnostics: Counter[str] = Counter()
    failures: Counter[str] = Counter()
    artifacts = processed = normalized = invalid = 0
    limited = summary_failed = False
    run = canonical_result = None
    status = 'running'
    index = ResolutionIndex()

    def summary() -> dict:
        return {
            'production': False, 'status': 'interrupted' if status == 'running' else status, 'limited': limited,
            'root': str(args.root.resolve()), 'source_filter': args.source, 'artifact_filters': args.artifact,
            'raw_occurrences': processed, 'observations': normalized, 'normalized_observations': normalized, 'artifacts': artifacts,
            'canonical_observations': canonical_result.canonical_observations if canonical_result else 0,
            'unresolved_observations': canonical_result.unresolved_observations if canonical_result else 0,
            'unresolved_identity_groups': canonical_result.unresolved_identity_groups if canonical_result else 0,
            'reconciliation_conflicts': canonical_result.reconciliation_conflicts if canonical_result else 0,
            'unresolved_reasons': dict(canonical_result.unresolved_reasons) if canonical_result else {},
            'canonical_schema_version': SCHEMA_VERSION, 'resolution_version': RESOLUTION_VERSION,
            'reconciliation_version': RECONCILIATION_VERSION,
            'normalization_failures': dict(failures), 'issues': dict(diagnostics),
            'raw_counts': [{'source': source, 'dataset': dataset, 'record_kind': kind, 'count': count}
                           for (source, dataset, kind), count in sorted(counts.items())],
        }

    try:
        with ExitStack() as stack:
            if not args.raw_only:
                run = MaterializedRun(args.root, args.output_parent)
                print(f'Materializing isolated run: {run.path}', file=sys.stderr, flush=True)
                observations_file = stack.enter_context(run.normalized.open('x', encoding='utf-8'))
                failures_file = stack.enter_context((run.path / 'failures.jsonl').open('x', encoding='utf-8'))
                run.summary({'status': 'running', 'stage': 'normalization', 'production': False})
            for retained in discover_inputs(args.root):
                source = 'placsp' if retained.reader == 'placsp' else 'gencat'
                if args.source != 'all' and source != args.source:
                    continue
                if args.artifact and not any(fnmatchcase(retained.artifact.path, pattern) for pattern in args.artifact):
                    continue
                print(f'Reading {retained.artifact.path}', file=sys.stderr, flush=True)
                artifacts += 1
                resolver_context = nullcontext(None) if args.raw_only else verified_resolver(args.root, retained.artifact)
                with resolver_context as resolve, closing(retained.read(args.root)) as records:
                    for source_record in records:
                        raw = to_raw(source_record)
                        counts[(raw.source, raw.dataset, raw.record_kind)] += 1
                        processed += 1
                        if run is not None:
                            error = None
                            observations = ()
                            try:
                                observations = normalize(raw, resolve=resolve)
                            except NormalizationError as exc:
                                error = exc
                                failures[exc.reason] += 1
                                invalid += not isinstance(exc, UnsupportedNormalizationInput)
                                failures_file.write(serialize(failure_summary(raw, exc)) + '\n')
                            for observation in observations:
                                observations_file.write(serialize(observation) + '\n')
                                index.add(identity_record(observation))
                                diagnostics.update(issue.code for issue in observation.issues)
                            normalized += len(observations)
                            if processed <= 3:
                                preview(raw, observations, sys.stdout, error)
                        if processed % 10000 == 0:
                            print(f'Processed {processed} raw records; {normalized} normalized observations', file=sys.stderr, flush=True)
                        if args.limit is not None and processed >= args.limit:
                            limited = True
                            break
                if limited:
                    break
            if not artifacts:
                raise RawSourceError('No supported retained artifacts found for the requested source')
        if run is not None and not invalid:
            run.summary({**summary(), 'status': 'running', 'stage': 'entity_resolution_and_reconciliation'})
            print('Resolving identity and reconciling materialized observations', file=sys.stderr, flush=True)
            canonical_result = reconcile_materialized(run, index)
        status = 'failed' if invalid else ('limited' if limited else ('complete_with_unsupported' if failures else 'complete'))
    except (RawSourceError, OSError) as exc:
        status = 'failed'
        print(f'Processing failed (counts incomplete; previous published output unchanged): {exc}', file=sys.stderr)
        return 1
    finally:
        if run is not None:
            try:
                run.summary(summary())
            except OSError as exc:
                summary_failed = True
                print(f'Could not write run summary: {exc}', file=sys.stderr)
    if summary_failed:
        return 1
    if run is not None and not invalid:
        try:
            run.publish()
        except OSError as exc:
            print(f'Could not publish completed run: {exc}', file=sys.stderr)
            return 1
    print('source\tdataset\trecord_kind\tcount')
    for (source, dataset, kind), count in sorted(counts.items()):
        print(f'{source}\t{dataset}\t{kind}\t{count}')
    print(f'Total: {processed} raw occurrences in {artifacts} artifacts (checksums verified){"; limited run" if limited else ""}')
    if run is not None:
        print(f'Normalized observations: {normalized}; location: {args.root / "data/NormalizedObservations"}')
        if canonical_result:
            print(f'Canonical observations: {canonical_result.canonical_observations}; location: {args.root / "data/CanonicalObservations"}')
            print(f'Unresolved observations: {canonical_result.unresolved_observations}; contradictory identity groups: {canonical_result.unresolved_identity_groups}')
            print(f'Reconciliation conflicts: {canonical_result.reconciliation_conflicts}')
            for example in canonical_result.examples:
                print('Normalized Observations: ' + ', '.join(example['normalized_observation_ids']))
                print('    ↓ Entity Resolution: strong procedure identifier match')
                print('CanonicalObservation ' + serialize(example))
        if failures:
            print('Unsupported/invalid selections: ' + serialize(dict(failures)))
        print(f'Run diagnostics: {run.path}')
        if invalid:
            print('Run failed; incomplete outputs were not published', file=sys.stderr)
    return 1 if invalid else 0


if __name__ == '__main__':
    raise SystemExit(main())
