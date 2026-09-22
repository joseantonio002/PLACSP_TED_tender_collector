import json
import sqlite3

from download import ROOT
from inspect_placsp import url_ids
from inspect_gencat import url

counts, mismatches = {}, []
for name, path, expression in [
    ('placsp', ROOT / 'data/processed/research.sqlite', 'SELECT uuid,publication_id,data FROM p'),
    ('gencat', ROOT / 'data/processed/gencat/ybgg-dgi6.sqlite', 'SELECT uuid,publication_id,data FROM observations'),
]:
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    count = 0
    for uuid, publication, data in db.execute(expression):
        row = json.loads(data)
        original = row.get('url') if name == 'placsp' else url(row.get('enllac_publicacio'))
        parsed = url_ids(original)
        if parsed != (uuid, publication):
            mismatches.append({'source': name, 'url': original, 'indexed': [uuid, publication], 'current_parser': parsed})
        count += 1
    counts[name] = count
    db.close()
result = {'rows_rechecked': counts, 'identifier_parser_mismatches': mismatches}
(ROOT / 'analysis/parser_verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2))
if mismatches:
    raise SystemExit(1)
