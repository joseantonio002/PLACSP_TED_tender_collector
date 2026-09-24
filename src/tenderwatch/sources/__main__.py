from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack, closing, nullcontext
from fnmatch import fnmatchcase
from pathlib import Path
import sys

from tenderwatch.inspection import create_output, failure_summary, preview, serialize
from tenderwatch.normalization import NormalizationError, UnsupportedNormalizationInput, normalize
from tenderwatch.raw import to_raw
from tenderwatch.sources.artifacts import verified_resolver
from tenderwatch.sources.errors import RawSourceError
from tenderwatch.sources.retained import discover_inputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Read retained occurrences and normalize them into disposable inspection JSONL; no downloads or reconciliation.')
    parser.add_argument('--root', type=Path, default=Path.cwd(), help='Repository/snapshot root containing data/raw')
    parser.add_argument('--source', choices=('all', 'placsp', 'gencat'), default='all')
    parser.add_argument('--artifact', action='append', default=[], help='Optional retained artifact path glob; repeat to select several patterns')
    parser.add_argument('--limit', type=int, help='Stop after this many raw occurrences; the output is explicitly marked as limited')
    parser.add_argument('--output-parent', type=Path, help='Existing parent for a new unique tenderwatch-inspection-* directory (default: system temporary directory)')
    parser.add_argument('--raw-only', action='store_true', help='Only traverse/count raw records; do not create inspection output')
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be positive')
    if args.output_parent is not None and not args.output_parent.is_dir():
        parser.error('--output-parent must be an existing directory')
    counts: Counter[tuple[str, str, str]] = Counter()
    diagnostics: Counter[str] = Counter()
    failures: Counter[str] = Counter()
    artifacts = processed = normalized = invalid = 0
    limited = False
    output = None
    status = 'running'
    try:
        with ExitStack() as stack:
            if not args.raw_only:
                output = create_output(args.output_parent)
                print(f'Disposable inspection output: {output}', file=sys.stderr, flush=True)
                observations_file = stack.enter_context((output / 'observations.jsonl').open('x', encoding='utf-8'))
                failures_file = stack.enter_context((output / 'failures.jsonl').open('x', encoding='utf-8'))
                (output / 'summary.json').write_text(serialize({'status': status, 'production': False}) + '\n', encoding='utf-8')
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
                        if not args.raw_only:
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
                                diagnostics.update(issue.code for issue in observation.issues)
                            normalized += len(observations)
                            if processed <= 3:
                                preview(raw, observations, sys.stdout, error)
                        if args.limit is not None and processed >= args.limit:
                            limited = True
                            break
                if limited:
                    break
            if not artifacts:
                raise RawSourceError('No supported retained artifacts found for the requested source')
            status = 'failed' if invalid else ('limited' if limited else ('complete_with_unsupported' if failures else 'complete'))
    except (RawSourceError, OSError) as exc:
        status = 'failed'
        print(f'Raw/normalized traversal failed (counts incomplete): {exc}', file=sys.stderr)
        return 1
    finally:
        if output is not None:
            summary = {
                'production': False, 'status': 'interrupted' if status == 'running' else status, 'limited': limited,
                'root': str(args.root.resolve()), 'source_filter': args.source, 'artifact_filters': args.artifact,
                'raw_occurrences': processed, 'observations': normalized, 'artifacts': artifacts,
                'normalization_failures': dict(failures), 'issues': dict(diagnostics),
                'raw_counts': [{'source': source, 'dataset': dataset, 'record_kind': kind, 'count': count}
                               for (source, dataset, kind), count in sorted(counts.items())],
            }
            (output / 'summary.json').write_text(serialize(summary) + '\n', encoding='utf-8')
    print('source\tdataset\trecord_kind\tcount')
    for (source, dataset, kind), count in sorted(counts.items()):
        print(f'{source}\t{dataset}\t{kind}\t{count}')
    print(f'Total: {processed} raw occurrences in {artifacts} artifacts (checksums verified){"; limited inspection" if limited else ""}')
    if output is not None:
        print(f'Normalized: {normalized} observations; {sum(failures.values())} controlled failures; output: {output}')
        if failures:
            print('Unsupported/invalid selections: ' + serialize(dict(failures)))
    return 1 if invalid else 0


if __name__ == '__main__':
    raise SystemExit(main())
