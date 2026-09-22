from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sqlite3

from download import ROOT
from inspect_placsp import stable_hash, url_ids


def url(value: object) -> str | None:
    if isinstance(value, dict):
        return value.get('url')
    return value if isinstance(value, str) else None


def inspect(dataset: str) -> None:
    raw = ROOT / 'data/raw/gencat' / dataset
    out = ROOT / 'data/processed/gencat'
    out.mkdir(parents=True, exist_ok=True)
    target = out / f'{dataset}.sqlite'
    if target.exists():
        print(f'Already processed {target}')
        return
    before = json.loads((raw / 'metadata-before.json').read_bytes())
    after = json.loads((raw / 'metadata-after.json').read_bytes())
    expected = int(json.loads((raw / 'count-before.json').read_bytes())[0]['count'])
    expected_after = int(json.loads((raw / 'count-after.json').read_bytes())[0]['count'])
    if before['rowsUpdatedAt'] != after['rowsUpdatedAt'] or expected != expected_after:
        raise ValueError('Dataset changed during pagination: do not claim snapshot consistency')
    db = sqlite3.connect(target.with_suffix('.working'))
    db.execute('CREATE TABLE observations (id TEXT, source_id TEXT, uuid TEXT, publication_id TEXT, expediente TEXT, buyer TEXT, lot TEXT, status TEXT, updated TEXT, hash TEXT, content_hash TEXT, page TEXT, ordinal INTEGER, data TEXT)')
    counts, fields, phases, results, procedures, months, identity_shapes = (Counter() for _ in range(7))
    date_months, values = defaultdict(Counter), defaultdict(Counter)
    for page in sorted((raw / 'pages').glob('*.json')):
        rows = json.loads(page.read_bytes())
        for ordinal, r in enumerate(rows):
            counts['rows'] += 1
            fields.update(k for k, v in r.items() if v not in (None, '', []))
            uuid, pub = url_ids(url(r.get('enllac_publicacio')))
            pubdates = {k: v for k, v in r.items() if k.startswith('data_publicacio') and v}
            if pubdates:
                months[max(pubdates.values())[:7]] += 1
            for k, v in pubdates.items():
                date_months[k][v[:7]] += 1
            for k in ('fase_publicacio', 'procediment', 'es_agregada', 'resultat', 'tipus_contracte', 'numero_lot', 'tipus_actuacio_execucio', 'codi_nuts'):
                values[k][r.get(k, '(missing)')] += 1
            sid = r.get('id_intern')
            if sid:
                identity_shapes['equals_url_uuid' if sid == uuid else 'differs_from_url_uuid'] += 1
            for k in ('identificacio_adjudicatari', 'denominacio_adjudicatari', 'import_adjudicacio_sense'):
                if '||' in str(r.get(k, '')):
                    counts[f'multi_value_{k}'] += 1
            if dataset == '8idu-wkjv':
                d = r.get('data')
                counts['execution_date_in_scope' if d and '2025-01-01' <= d[:10] <= '2026-09-22' else ('execution_date_missing' if not d else 'execution_date_out_of_scope')] += 1
                if d:
                    date_months['data'][d[:7]] += 1
            business = {k: v for k, v in r.items() if not k.startswith(':')}
            db.execute('INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (r.get(':id'), sid, uuid, pub, r.get('codi_expedient'), r.get('codi_organ'), r.get('numero_lot'), r.get('fase_publicacio') or r.get('tipus_actuacio_execucio'), r.get(':updated_at'), stable_hash(r), stable_hash(business), str(page.relative_to(ROOT)), ordinal, json.dumps(r, ensure_ascii=False)))
        db.commit()
        print(f'{dataset}: {counts["rows"]:,}/{expected:,}', flush=True)
    if counts['rows'] != expected:
        raise ValueError(f'Incomplete pages: {counts["rows"]} != {expected}')
    db.executescript('CREATE INDEX obs_uuid ON observations(uuid); CREATE INDEX obs_source ON observations(source_id); CREATE INDEX obs_id ON observations(id); CREATE INDEX obs_buyer_exp ON observations(buyer,expediente); CREATE INDEX obs_pub ON observations(publication_id);')
    counts['unique_socrata_ids'] = db.execute('SELECT COUNT(DISTINCT id) FROM observations').fetchone()[0]
    if counts['unique_socrata_ids'] != counts['rows']:
        raise ValueError('Pagination repeated row IDs')
    counts['unique_source_ids'] = db.execute('SELECT COUNT(DISTINCT source_id) FROM observations').fetchone()[0]
    counts['unique_url_uuids'] = db.execute('SELECT COUNT(DISTINCT uuid) FROM observations').fetchone()[0]
    counts['unique_publication_ids'] = db.execute('SELECT COUNT(DISTINCT publication_id) FROM observations').fetchone()[0]
    counts['unique_buyer_expediente_pairs'] = db.execute('SELECT COUNT(*) FROM (SELECT DISTINCT buyer,expediente FROM observations)').fetchone()[0]
    counts['unique_buyers'] = db.execute('SELECT COUNT(DISTINCT buyer) FROM observations').fetchone()[0]
    counts['unique_nonzero_lots_by_uuid'] = db.execute("SELECT COUNT(*) FROM (SELECT DISTINCT uuid,lot FROM observations WHERE uuid IS NOT NULL AND lot IS NOT NULL AND lot != '0')").fetchone()[0]
    counts['repeated_source_id_groups'] = db.execute('SELECT COUNT(*) FROM (SELECT source_id FROM observations WHERE source_id IS NOT NULL GROUP BY source_id HAVING COUNT(*)>1)').fetchone()[0]
    counts['buyer_expediente_multiple_uuid_groups'] = db.execute('SELECT COUNT(*) FROM (SELECT buyer,expediente FROM observations GROUP BY buyer,expediente HAVING COUNT(DISTINCT uuid)>1)').fetchone()[0]
    counts['expediente_multiple_buyer_groups'] = db.execute('SELECT COUNT(*) FROM (SELECT expediente FROM observations GROUP BY expediente HAVING COUNT(DISTINCT buyer)>1)').fetchone()[0]
    counts['identical_business_rows_extra'] = counts['rows'] - db.execute('SELECT COUNT(DISTINCT content_hash) FROM observations').fetchone()[0]
    counts['duplicate_uuid_lot_groups'] = db.execute('SELECT COUNT(*) FROM (SELECT uuid,lot FROM observations WHERE uuid IS NOT NULL GROUP BY uuid,lot HAVING COUNT(*)>1)').fetchone()[0]
    result = {'dataset': dataset, 'counts': counts, 'field_presence': {k: {'count': v, 'percent': round(v / counts['rows'] * 100, 4)} for k, v in fields.items()}, 'categorical_values': dict(values), 'month_by_latest_available_publication_date': months, 'date_fields_monthly': dict(date_months), 'identity_shapes': identity_shapes, 'snapshot_validation': {'before_rows_updated_at': before['rowsUpdatedAt'], 'after_rows_updated_at': after['rowsUpdatedAt'], 'count_before': expected, 'count_after': expected_after, 'row_ids_unique': True}}
    (out / f'{dataset}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    db.close()
    target.with_suffix('.working').rename(target)
    print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', default='ybgg-dgi6')
    inspect(p.parse_args().dataset)
