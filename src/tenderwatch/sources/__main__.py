from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

from tenderwatch.raw import to_raw
from tenderwatch.sources.errors import RawSourceError
from tenderwatch.sources.retained import discover_inputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Read retained source occurrences and count immutable raw records; no downloads or normalization.')
    parser.add_argument('--root', type=Path, default=Path.cwd(), help='Repository/snapshot root containing data/raw')
    parser.add_argument('--source', choices=('all', 'placsp', 'gencat'), default='all')
    args = parser.parse_args(argv)
    counts: Counter[tuple[str, str, str]] = Counter()
    artifacts = 0
    try:
        for retained in discover_inputs(args.root):
            source = 'placsp' if retained.reader == 'placsp' else 'gencat'
            if args.source != 'all' and source != args.source:
                continue
            print(f'Reading {retained.artifact.path}', file=sys.stderr, flush=True)
            for source_record in retained.read(args.root):
                raw = to_raw(source_record)
                counts[(raw.source, raw.dataset, raw.record_kind)] += 1
            artifacts += 1
        if not artifacts:
            raise RawSourceError('No supported retained artifacts found for the requested source')
    except RawSourceError as exc:
        print(f'Raw traversal failed (counts incomplete): {exc}', file=sys.stderr)
        return 1
    print('source\tdataset\trecord_kind\tcount')
    for (source, dataset, kind), count in sorted(counts.items()):
        print(f'{source}\t{dataset}\t{kind}\t{count}')
    print(f'Total: {sum(counts.values())} raw occurrences in {artifacts} artifacts (checksums verified)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
