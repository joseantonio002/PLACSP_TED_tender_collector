from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
import re
import sqlite3
import unicodedata

from download import ROOT

OUT = ROOT / 'analysis'


def norm(value: str | None) -> str:
    return re.sub(r'[^A-Z0-9]', '', unicodedata.normalize('NFKD', value or '').upper())


def amount(value: str | None) -> Decimal | None:
    try:
        return Decimal(value) if value not in (None, '') else None
    except InvalidOperation:
        return None


def scalar(db: sqlite3.Connection, sql: str) -> int:
    return db.execute(sql).fetchone()[0]


def connect(aggregated_only: bool = False) -> sqlite3.Connection:
    path = ROOT / 'data/processed/research.sqlite'
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS loaded (name TEXT PRIMARY KEY)')
    archives = sorted((ROOT / 'data/processed/placsp').glob('*.sqlite'))
    for path in archives:
        if db.execute('SELECT 1 FROM loaded WHERE name=?', (path.name,)).fetchone():
            continue
        db.execute('ATTACH DATABASE ? AS incoming', (str(path),))
        db.execute('CREATE TABLE IF NOT EXISTS p AS SELECT * FROM incoming.observations WHERE 0')
        db.execute('CREATE TABLE IF NOT EXISTS tombstones AS SELECT * FROM incoming.tombstones WHERE 0')
        db.execute('INSERT INTO p SELECT * FROM incoming.observations')
        db.execute('INSERT INTO tombstones SELECT * FROM incoming.tombstones')
        db.execute('INSERT INTO loaded VALUES (?)', (path.name,))
        db.commit()
        db.execute('DETACH DATABASE incoming')
    db.executescript('CREATE INDEX IF NOT EXISTS p_id ON p(id); CREATE INDEX IF NOT EXISTS p_uuid ON p(uuid); CREATE INDEX IF NOT EXISTS p_buyer_exp ON p(buyer,expediente);')
    db.execute('ATTACH DATABASE ? AS gdb', (str(ROOT / 'data/processed/gencat/ybgg-dgi6.sqlite'),))
    db.execute('CREATE TEMP VIEW g AS SELECT * FROM gdb.observations')
    if aggregated_only:
        db.execute("CREATE TEMP VIEW p AS SELECT * FROM main.p WHERE id LIKE '%/PlataformasAgregadasSinMenores/%'")
        db.execute("CREATE TEMP VIEW tombstones AS SELECT * FROM main.tombstones WHERE id LIKE '%/PlataformasAgregadasSinMenores/%'")
    db.execute('CREATE TEMP TABLE latest AS SELECT * FROM (SELECT *,ROW_NUMBER() OVER(PARTITION BY id ORDER BY julianday(updated) DESC,hash) AS rn FROM p) WHERE rn=1')
    db.execute('CREATE INDEX latest_uuid ON latest(uuid)')
    return db


def main(aggregated_only: bool = False) -> None:
    OUT.mkdir(exist_ok=True)
    db = connect(aggregated_only)
    prefix = 'aggregated_' if aggregated_only else ''
    metrics = {'scope': {'start_inclusive': '2025-01-01', 'end_inclusive': '2026-09-22', 'placsp_date': 'entry/updated date in supplied peninsular offset', 'gencat_date': 'any data_publicacio* value in range', 'execution_date': 'all downloaded; data used separately for in-scope actions'}, 'loaded_placsp_archives': [r[0] for r in db.execute('SELECT name FROM loaded')], 'placsp': {}, 'gencat': {}, 'matching': {}, 'changes': {}}
    p = metrics['placsp']
    queries = {
        'selected_record_occurrences': 'SELECT count(*) FROM p',
        'unique_atom_ids': 'SELECT count(DISTINCT id) FROM p',
        'unique_pscp_uuids': 'SELECT count(DISTINCT uuid) FROM p',
        'unique_tree_hashes': 'SELECT count(DISTINCT hash) FROM p',
        'unique_codice_hashes': 'SELECT count(DISTINCT content_hash) FROM p',
        'ids_with_multiple_observations': 'SELECT count(*) FROM (SELECT id FROM p GROUP BY id HAVING count(*)>1)',
        'ids_with_multiple_updated_times': 'SELECT count(*) FROM (SELECT id FROM p GROUP BY id HAVING count(DISTINCT updated)>1)',
        'same_id_timestamp_different_tree_hash_groups': 'SELECT count(*) FROM (SELECT id,updated FROM p GROUP BY id,updated HAVING count(DISTINCT hash)>1)',
        'ids_with_changed_expediente': 'SELECT count(*) FROM (SELECT id FROM p GROUP BY id HAVING count(DISTINCT expediente)>1)',
        'ids_with_multiple_pscp_uuids': 'SELECT count(*) FROM (SELECT id FROM p GROUP BY id HAVING count(DISTINCT uuid)>1)',
        'uuid_multiple_atom_ids': 'SELECT count(*) FROM (SELECT uuid FROM p WHERE uuid IS NOT NULL GROUP BY uuid HAVING count(DISTINCT id)>1)',
        'buyer_exp_multiple_atom_ids': "SELECT count(*) FROM (SELECT buyer,expediente FROM p WHERE buyer IS NOT NULL AND expediente IS NOT NULL AND expediente!='' GROUP BY buyer,expediente HAVING count(DISTINCT id)>1)",
        'expediente_multiple_buyers': 'SELECT count(*) FROM (SELECT expediente FROM p GROUP BY expediente HAVING count(DISTINCT buyer)>1)',
        'unique_named_lots_by_atom_id': "SELECT count(*) FROM (SELECT DISTINCT p.id,json_extract(j.value,'$.id') lot FROM p,json_each(p.data,'$.lots') j WHERE json_extract(j.value,'$.id') IS NOT NULL)",
        'tombstone_occurrences_all_geographies': 'SELECT count(*) FROM tombstones',
        'selected_ids_with_tombstone': 'SELECT count(DISTINCT p.id) FROM p JOIN tombstones t ON t.id=p.id',
    }
    for k, sql in queries.items():
        p[k] = scalar(db, sql)
    p['buyer_composite_counter_scope'] = 'Non-null ID_OC_PLAT research buyer column, primarily aggregation; native Party identifiers remain in data and are not substituted into this namespace.'
    p['repeated_tree_hash_extra_occurrences'] = p['selected_record_occurrences'] - p['unique_tree_hashes']
    p['monthly'] = dict(db.execute('SELECT substr(updated,1,7),count(*) FROM p GROUP BY 1'))
    p['statuses'] = dict(db.execute('SELECT status,count(*) FROM p GROUP BY status'))
    profiles = [json.loads(f.read_bytes()) for f in (ROOT / 'data/processed/placsp').glob('*.json') if not aggregated_only or f.name.startswith('PlataformasAgregadasSinMenores')]
    metrics['scope']['placsp_feed_filter'] = 'aggregated' if aggregated_only else 'all_downloaded'
    for name in ('counts', 'selected_field_presence', 'selected_geography'):
        total = Counter()
        for profile in profiles:
            total.update(profile[name])
        p[name] = dict(total)
    p['presence_percent'] = {k: round(v / p['selected_record_occurrences'] * 100, 4) for k, v in p['selected_field_presence'].items()}
    p['archive_profiles'] = [{k: v for k, v in x.items() if k not in ('pages', 'selected_xml_path_entry_counts')} for x in profiles]
    for dataset in ('ybgg-dgi6', '8idu-wkjv'):
        metrics['gencat'][dataset] = json.loads((ROOT / f'data/processed/gencat/{dataset}.json').read_bytes())
    metrics['gencat']['main_semantic_counts'] = {
        'ordinary_rows': scalar(db, "SELECT count(*) FROM g WHERE json_extract(data,'$.es_agregada')='NO'"),
        'ordinary_unique_procedure_uuids': scalar(db, "SELECT count(DISTINCT uuid) FROM g WHERE json_extract(data,'$.es_agregada')='NO'"),
        'aggregate_rows': scalar(db, "SELECT count(*) FROM g WHERE json_extract(data,'$.es_agregada')='SÍ'"),
        'aggregate_distinct_batch_uuids': scalar(db, "SELECT count(DISTINCT uuid) FROM g WHERE json_extract(data,'$.es_agregada')='SÍ'"),
        'aggregate_distinct_source_row_ids': scalar(db, "SELECT count(DISTINCT source_id) FROM g WHERE json_extract(data,'$.es_agregada')='SÍ'"),
        'ordinary_buyer_exp_multiple_uuids': scalar(db, "SELECT count(*) FROM (SELECT buyer,expediente FROM g WHERE json_extract(data,'$.es_agregada')='NO' AND expediente IS NOT NULL AND expediente!='' GROUP BY buyer,expediente HAVING count(DISTINCT uuid)>1)"),
        'ordinary_duplicate_uuid_lot_groups': scalar(db, "SELECT count(*) FROM (SELECT uuid,lot FROM g WHERE json_extract(data,'$.es_agregada')='NO' GROUP BY uuid,lot HAVING count(*)>1)"),
    }
    m = metrics['matching']
    m['placsp_ids_any_historical_exact_uuid'] = scalar(db, "SELECT count(DISTINCT p.id) FROM p WHERE EXISTS (SELECT 1 FROM g WHERE g.uuid=p.uuid AND json_extract(g.data,'$.es_agregada')='NO')")
    m['placsp_occurrences_any_exact_uuid'] = scalar(db, "SELECT count(*) FROM p WHERE EXISTS (SELECT 1 FROM g WHERE g.uuid=p.uuid AND json_extract(g.data,'$.es_agregada')='NO')")
    m['gencat_ordinary_uuids_with_placsp_uuid'] = scalar(db, "SELECT count(DISTINCT g.uuid) FROM g WHERE json_extract(g.data,'$.es_agregada')='NO' AND EXISTS (SELECT 1 FROM p WHERE p.uuid=g.uuid)")
    changes = Counter()
    examples = defaultdict(list)
    for row in db.execute('SELECT id FROM p GROUP BY id HAVING count(DISTINCT hash)>1'):
        observations = [json.loads(r[0]) for r in db.execute('SELECT data FROM p WHERE id=? ORDER BY julianday(updated),hash', (row[0],))]
        flags = set()
        for a, b in zip(observations, observations[1:]):
            for field in ('expediente', 'status', 'budget', 'estimated_value', 'deadline_date', 'deadline_time', 'documents', 'lots', 'awards', 'notices', 'title'):
                if a[field] != b[field]:
                    flags.add(field)
            if a['updated'] == b['updated'] and any(a[k] != b[k] for k in a if k not in ('archive', 'member', 'ordinal')):
                flags.add('same_timestamp')
        for flag in flags:
            changes[flag] += 1
            if len(examples[flag]) < 15:
                examples[flag].append(row[0])
    metrics['changes'] = {'ids_with_changes_in_extracted_field': dict(changes), 'examples': dict(examples), 'interpretation': 'Differences between observed representations, not verified business events; includes formatting, completeness and identity corrections.'}
    stats, comparisons = Counter(), Counter()
    rows_for_csv = []
    norm_index = defaultdict(set)
    for r in db.execute("SELECT DISTINCT buyer,expediente,uuid FROM g WHERE json_extract(data,'$.es_agregada')='NO'"):
        norm_index[(r['buyer'], norm(r['expediente']))].add(r['uuid'])
    status_map = {'Anunci de licitació': 'PUB', 'Expedient en avaluació': 'EV', 'Adjudicació': 'ADJ', 'Formalització': 'RES', 'Anul·lació': 'ANUL', 'Anunci previ': 'PRE'}
    for i, row in enumerate(db.execute('SELECT * FROM latest')):
        a = json.loads(row['data'])
        gs = list(db.execute("SELECT data,uuid,publication_id FROM g WHERE uuid=? AND json_extract(data,'$.es_agregada')='NO'", (row['uuid'],))) if row['uuid'] else []
        tier, candidates = 'none', set()
        if gs:
            tier, candidates = 'explicit_uuid', {row['uuid']}
        elif a['agent'] == '62' and row['buyer']:
            candidates = {r[0] for r in db.execute("SELECT DISTINCT uuid FROM g WHERE buyer=? AND expediente=? AND json_extract(data,'$.es_agregada')='NO'", (row['buyer'], row['expediente']))}
            if candidates:
                tier = 'buyer_exact_exp_unique_candidate' if len(candidates) == 1 else 'buyer_exact_exp_ambiguous'
            else:
                candidates = norm_index.get((row['buyer'], norm(row['expediente'])), set())
                if candidates:
                    tier = 'buyer_normalized_exp_unique_candidate' if len(candidates) == 1 else 'buyer_normalized_exp_ambiguous'
        stats[tier] += 1
        rows_for_csv.append({'placsp_id': row['id'], 'uuid': row['uuid'], 'buyer': row['buyer'], 'expediente': row['expediente'], 'tier': tier, 'candidates': '|'.join(sorted(c for c in candidates if c))})
        if gs:
            samepub = any(r['publication_id'] == row['publication_id'] for r in gs)
            group = 'same_latest_publication' if samepub else 'different_latest_publication'
            comparisons[group] += 1
            if len(examples[group]) < 15:
                examples[group].append(row['id'])
            agreement, conflicts, missing = [], [], []
            gs.sort(key=lambda r: (r['publication_id'] != row['publication_id'], json.loads(r['data']).get('id_intern', '')))
            b = json.loads(gs[0]['data'])
            for name, x, y in [('procedure_budget_net', amount(a['budget']), amount(b.get('pressupost_licitacio_sense_1'))), ('procedure_estimated_value', amount(a['estimated_value']), amount(b.get('valor_estimat_expedient'))), ('deadline_wall_time', ((a['deadline_date'] or '')[:10] + 'T' + (a['deadline_time'] or '')[:8]) if a['deadline_date'] else None, b.get('termini_presentacio_ofertes', '')[:19] or None)]:
                if x is None or y is None:
                    missing.append(name)
                elif x == y:
                    agreement.append(name)
                else:
                    conflicts.append(name)
                comparisons[f'{group}:{name}:' + ('missing' if x is None or y is None else 'equal' if x == y else 'different')] += 1
                if x is not None and y is not None and x != y:
                    if name == 'deadline_wall_time':
                        comparisons[f'{group}:deadline_difference:' + ('seconds_only' if x[:16] == y[:16] else 'beyond_seconds')] += 1
                    key = name + '_different'
                    if len(examples[key]) < 15:
                        examples[key].append(row['id'])
            if samepub and not conflicts and not missing:
                comparisons['same_publication_three_fields_equal'] += 1
                if len(examples['equivalent_projection']) < 15:
                    examples['equivalent_projection'].append(row['id'])
            if conflicts:
                if len(examples['field_conflict']) < 15:
                    examples['field_conflict'].append(row['id'])
                if samepub and len(examples['same_pub_field_conflict']) < 15:
                    examples['same_pub_field_conflict'].append(row['id'])
            if row['buyer'] and b.get('codi_organ') != row['buyer']:
                comparisons['uuid_match_buyer_id_disagreement'] += 1
                if len(examples['buyer_conflict']) < 15:
                    examples['buyer_conflict'].append(row['id'])
            g_award = any(json.loads(r['data']).get('identificacio_adjudicatari') for r in gs)
            p_award = any(x['supplier_ids'] for x in a['awards'])
            if g_award != p_award:
                name = 'award_only_gencat' if g_award else 'award_only_placsp'
                comparisons[name] += 1
                if len(examples[name]) < 15:
                    examples[name].append(row['id'])
        if i % 10000 == 0:
            print(f'Matched {i:,} latest PLACSP IDs', flush=True)
    m['latest_id_candidate_tiers'] = dict(stats)
    m['latest_id_field_comparisons'] = dict(comparisons)
    m['explicit_uuid_share_of_selected_placsp_ids_percent'] = round(m['placsp_ids_any_historical_exact_uuid'] / p['unique_atom_ids'] * 100, 4)
    m['explicit_uuid_share_of_ordinary_gencat_procedure_uuids_percent'] = round(m['gencat_ordinary_uuids_with_placsp_uuid'] / metrics['gencat']['main_semantic_counts']['ordinary_unique_procedure_uuids'] * 100, 4)
    m['examples'] = dict(examples)
    with (OUT / f'{prefix}matching_candidates.csv').open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(rows_for_csv[0]))
        w.writeheader()
        w.writerows(rows_for_csv)
    (OUT / f'{prefix}metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(json.dumps({'placsp': {k: v for k, v in p.items() if not isinstance(v, (dict, list))}, 'gencat_semantics': metrics['gencat']['main_semantic_counts'], 'matching': {k: v for k, v in m.items() if k != 'examples'}, 'changes': dict(changes)}, ensure_ascii=False, indent=2))
    db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--aggregated-only', action='store_true')
    main(parser.parse_args().aggregated_only)
