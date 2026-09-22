import json

from download import MANIFEST, now, record

entries = [json.loads(line) for line in MANIFEST.read_text().splitlines() if line]
annotated = {r.get('applies_to_filename') for r in entries if r.get('event') == 'metadata_annotation'}
for r in entries:
    name = r.get('filename', '')
    if r.get('validated') and '/8idu-wkjv/pages/' in name and 'any publication date' in (r.get('period') or '') and name not in annotated:
        record({'event': 'metadata_annotation', 'recorded_at': now(), 'applies_to_filename': name, 'field': 'period', 'original_value': r['period'], 'corrected_value': 'all available execution actions; local date profiling', 'reason': 'The actual preserved request used $where=1=1. Initial human-readable period label was inherited from the main publication downloader. No raw bytes or request parameters changed.'})
        print(name)
