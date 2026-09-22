from collections import Counter
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

from download import ROOT
from inspect_placsp import ATOM, text

verification = json.loads((ROOT / 'analysis/verification.json').read_bytes())
results = []
for info in verification['zip_chains']:
    archive = ROOT / info['archive']
    profile = json.loads((ROOT / 'data/processed/placsp' / f'{archive.stem}.json').read_bytes())
    by_name = {Path(p['member']).name: p for p in profile['pages']}
    selected = set(info['unreachable_pages']) | {Path(p['member']).name for p in profile['pages'] if p['entries'] > 500}
    with zipfile.ZipFile(archive) as z:
        for name in sorted(selected):
            member = by_name[name]['member']
            root = ET.fromstring(z.read(member))
            entries = root.findall(ATOM + 'entry')
            dates = [text(e, ATOM + 'updated') for e in entries]
            ids = [text(e, ATOM + 'id') for e in entries]
            results.append({'archive': info['archive'], 'member': member, 'entry_count': len(entries), 'unique_ids': len(set(ids)), 'updated_min': min(dates), 'updated_max': max(dates), 'in_scope_entries': sum('2025-01-01' <= d[:10] <= '2026-09-22' for d in dates), 'first_ids': ids[:3], 'reachable_from_base': name not in info['unreachable_pages']})
(ROOT / 'analysis/archive_anomalies.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
print(json.dumps(results, ensure_ascii=False, indent=2))
