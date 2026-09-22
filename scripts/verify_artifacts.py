from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse
import zipfile

from download import ROOT, MANIFEST, digest


def main() -> None:
    entries = [json.loads(line) for line in MANIFEST.read_text().splitlines() if line]
    successful = {r['filename']: r for r in entries if r.get('validated')}
    missing, bad_hash = [], []
    total_bytes = 0
    by_source = Counter()
    for filename, record in successful.items():
        path = ROOT / filename
        if not path.exists():
            missing.append(filename)
        elif digest(path) != record['sha256']:
            bad_hash.append(filename)
        total_bytes += record['size_bytes']
        by_source[record['source']] += 1
    chains = []
    for path in sorted((ROOT / 'data/processed/placsp').glob('*.json')):
        profile = json.loads(path.read_bytes())
        pages = profile['pages']
        by_name = {Path(p['member']).name: p for p in pages}
        base = next((n for n in by_name if re.search(r'_(?:20\d{2})', n) is None), None)
        current, visited, end = base, [], None
        while current in by_name and current not in visited:
            visited.append(current)
            links = by_name[current]['links']
            nxt = next((x['href'] for x in links if x.get('rel') == 'next'), None)
            if nxt is None:
                end = 'no next'
                break
            current = Path(urlparse(nxt).path).name
        if end is None:
            end = 'cycle' if current in visited else current
        chains.append({'archive': profile['archive'], 'pages': len(pages), 'reachable_from_base': len(visited), 'unreachable_pages': sorted(set(by_name) - set(visited)), 'chain_end': end, 'max_entries': max(p['entries'] for p in pages), 'max_entries_plus_tombstones': max(p['entries'] + p['tombstones'] for p in pages)})
    cases = json.loads((ROOT / 'analysis/cases.json').read_bytes())
    fragment_errors, sample_counts = [], Counter()
    for case in cases:
        for ref in case['evidence_references']:
            sample_counts[ref['source']] += 1
            if ref['source'] == 'placsp':
                fragment = (ROOT / case['folder'] / ref['file']).read_bytes()
                with zipfile.ZipFile(ROOT / ref['archive']) as z:
                    original = z.read(ref['member'])[ref['byte_start_in_member']:ref['byte_end_in_member']]
                if fragment != original or hashlib.sha256(fragment).hexdigest() != ref['fragment_sha256']:
                    fragment_errors.append([case['case_id'], ref['file']])
            else:
                rows = json.loads((ROOT / ref['page']).read_bytes())
                if rows[ref['row_ordinal']].get(':id') != ref['socrata_id']:
                    fragment_errors.append([case['case_id'], ref['socrata_id']])
    result = {'successful_raw_files': len(successful), 'files_by_source': dict(by_source), 'size_bytes': total_bytes, 'missing_raw_files': missing, 'bad_raw_hashes': bad_hash, 'sample_reference_errors': fragment_errors, 'sample_counts': dict(sample_counts), 'case_count': len(cases), 'primary_phase_reference_failures': sum('error' in p for c in cases for p in c['phase_json'].values()), 'recovered_as_legacy_xml': sum(p.get('format') == 'xml' for c in cases for p in c['phase_json'].values()), 'unrecovered_phase_references': sum('raw_path' not in p for c in cases for p in c['phase_json'].values()), 'zip_chains': chains, 'request_failures_by_http_status': dict(Counter(str(r['http_status']) for r in entries if not r.get('validated') and 'http_status' in r))}
    (ROOT / 'analysis/verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if missing or bad_hash or fragment_errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
