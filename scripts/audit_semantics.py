from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from difflib import SequenceMatcher
import json
import statistics
from zoneinfo import ZoneInfo

from compare_sources import connect, norm, scalar, OUT, amount
from inspect_placsp import stable_hash


def main() -> None:
    db = connect()
    result = {}
    db.execute('ATTACH DATABASE ? AS execution', (str(OUT.parent / 'data/processed/gencat/8idu-wkjv.sqlite'),))
    result['execution_action_date_scope'] = dict(db.execute("SELECT count(*) records,count(DISTINCT buyer) buyers,count(DISTINCT buyer||'|'||expediente) buyer_exp_pairs FROM execution.observations WHERE json_extract(data,'$.data')>='2025-01-01' AND json_extract(data,'$.data')<'2026-09-23'").fetchone())
    sqls = {
        'ordinary_lot_zero_rows': "SELECT count(*) FROM g WHERE json_extract(data,'$.es_agregada')='NO' AND lot='0'",
        'ordinary_missing_lot_rows': "SELECT count(*) FROM g WHERE json_extract(data,'$.es_agregada')='NO' AND lot IS NULL",
        'ordinary_positive_named_lot_rows': "SELECT count(*) FROM g WHERE json_extract(data,'$.es_agregada')='NO' AND lot IS NOT NULL AND lot!='0'",
        'ordinary_procedures_multiple_phases_across_rows': "SELECT count(*) FROM (SELECT uuid FROM g WHERE json_extract(data,'$.es_agregada')='NO' GROUP BY uuid HAVING count(DISTINCT status)>1)",
        'ordinary_identical_titles_multiple_uuid_groups': "SELECT count(*) FROM (SELECT json_extract(data,'$.denominacio') FROM g WHERE json_extract(data,'$.es_agregada')='NO' GROUP BY 1 HAVING count(DISTINCT uuid)>1)",
        'ordinary_buyer_names_per_code_multiple': "SELECT count(*) FROM (SELECT buyer FROM g WHERE json_extract(data,'$.es_agregada')='NO' GROUP BY buyer HAVING count(DISTINCT json_extract(data,'$.nom_organ'))>1)",
        'publication_date_anunci_after_deadline_rows': "SELECT count(*) FROM g WHERE json_extract(data,'$.data_publicacio_anunci')>json_extract(data,'$.termini_presentacio_ofertes')",
        'ordinary_buyer_dir3_placeholder_rows': "SELECT count(*) FROM g WHERE json_extract(data,'$.es_agregada')='NO' AND json_extract(data,'$.codi_dir3')='A9999999'",
        'same_uuid_same_publication_multiple_g_rows_groups': "SELECT count(*) FROM (SELECT uuid,publication_id FROM g GROUP BY uuid,publication_id HAVING count(*)>1)",
    }
    result['counts'] = {k: scalar(db, sql) for k, sql in sqls.items()}
    example_sql = {
        'ordinary_buyer_expediente_collision': "SELECT buyer,expediente,count(DISTINCT uuid) n,group_concat(DISTINCT uuid) uuids FROM g WHERE json_extract(data,'$.es_agregada')='NO' AND expediente IS NOT NULL AND expediente!='' GROUP BY buyer,expediente HAVING n>1 ORDER BY n DESC LIMIT 10",
        'missing_expediente_multiple_uuid_buckets': "SELECT buyer,count(DISTINCT uuid) n FROM g WHERE expediente IS NULL GROUP BY buyer HAVING n>1 ORDER BY n DESC LIMIT 10",
        'ordinary_duplicate_uuid_lot': "SELECT uuid,lot,count(*) n,group_concat(DISTINCT status) statuses FROM g WHERE json_extract(data,'$.es_agregada')='NO' GROUP BY uuid,lot HAVING n>1 ORDER BY n DESC LIMIT 10",
        'different_lot_phases': "SELECT uuid,count(DISTINCT status) n,group_concat(DISTINCT status) statuses FROM g WHERE json_extract(data,'$.es_agregada')='NO' GROUP BY uuid HAVING n>1 LIMIT 10",
        'same_title_distinct_procedures': "SELECT json_extract(data,'$.denominacio') title,count(DISTINCT uuid) n,group_concat(DISTINCT uuid) uuids FROM g WHERE json_extract(data,'$.es_agregada')='NO' GROUP BY 1 HAVING n>1 ORDER BY n DESC LIMIT 5",
        'same_codice_different_ids': "SELECT content_hash,count(DISTINCT id) n,group_concat(DISTINCT id) ids FROM p GROUP BY content_hash HAVING n>1 LIMIT 10",
        'same_id_time_different_hash': "SELECT id,updated,count(DISTINCT hash) n FROM p GROUP BY id,updated HAVING n>1 LIMIT 10",
        'placsp_exp_multiple_buyers': "SELECT expediente,count(DISTINCT buyer) n,group_concat(DISTINCT id) ids FROM latest WHERE buyer IS NOT NULL GROUP BY expediente HAVING n>1 ORDER BY n DESC LIMIT 10",
    }
    result['examples'] = {k: [dict(r) for r in db.execute(sql)] for k, sql in example_sql.items()}
    presence, geo, buyers = Counter(), Counter(), set()
    for r in db.execute('SELECT data FROM p'):
        a = json.loads(r[0])
        buyers.add((a['agent'], tuple(tuple(v) for v in a['buyer_ids'])))
        if any(n == 'ES511' for n in a['execution_nuts']):
            geo['execution_barcelona_ES511'] += 1
        if a['buyer_postal'] and a['buyer_postal'].startswith('08'):
            geo['buyer_postcode_08'] += 1
        if a['agent'] == '62' and not any(n.startswith('ES51') for n in a['execution_nuts']):
            geo['catalan_origin_without_ES51_execution'] += 1
    result['placsp_unique_buyer_identifier_bundles'] = len(buyers)
    result['placsp_geography'] = dict(geo)
    exact_hashes, formatted_hashes, duplicate_examples = {}, set(), []
    presence_by_kind, kind_counts = defaultdict(Counter), Counter()
    def tidy(value):
        if isinstance(value, str):
            return ' '.join(value.split())
        if isinstance(value, dict):
            return {k: tidy(v) for k, v in value.items()}
        if isinstance(value, list):
            return [tidy(v) for v in value]
        return value
    for r in db.execute('SELECT data FROM g'):
        a = json.loads(r[0])
        payload = {k: v for k, v in a.items() if not k.startswith(':') and k != 'id_intern'}
        key = stable_hash(payload)
        if key in exact_hashes and len(duplicate_examples) < 10:
            duplicate_examples.append([exact_hashes[key], a['id_intern']])
        exact_hashes[key] = a['id_intern']
        formatted_hashes.add(stable_hash(tidy(payload)))
        tests = {'expediente': a.get('codi_expedient'), 'buyer_identifier': a.get('codi_organ') or a.get('codi_dir3'), 'buyer_nif': False, 'supplier_identifier': a.get('identificacio_adjudicatari'), 'cpv': a.get('codi_cpv'), 'budget_any_scope': a.get('pressupost_licitacio_sense') or a.get('pressupost_licitacio_sense_1'), 'budget_procedure': a.get('pressupost_licitacio_sense_1'), 'estimated_value_any_scope': a.get('valor_estimat_contracte') or a.get('valor_estimat_expedient'), 'estimated_value_procedure': a.get('valor_estimat_expedient'), 'deadline': a.get('termini_presentacio_ofertes'), 'execution_location': a.get('lloc_execucio') or a.get('codi_nuts'), 'status': a.get('fase_publicacio'), 'source_link': a.get('enllac_publicacio'), 'phase_json_link': any(v for k, v in a.items() if k.startswith('url_json')), 'award_information': a.get('data_adjudicacio_contracte') or a.get('identificacio_adjudicatari') or a.get('import_adjudicacio_sense'), 'winner': a.get('identificacio_adjudicatari') or a.get('denominacio_adjudicatari')}
        presence.update(k for k, v in tests.items() if v)
        kind = a.get('es_agregada', '(missing)')
        kind_counts[kind] += 1
        presence_by_kind[kind].update(k for k, v in tests.items() if v)
    result['gencat_presence_by_aggregation'] = {kind: {'rows': kind_counts[kind], 'fields': {k: {'count': counts[k], 'percent': round(counts[k] / kind_counts[kind] * 100, 4)} for k in tests}} for kind, counts in presence_by_kind.items()}
    n = scalar(db, 'SELECT count(*) FROM g')
    result['gencat_identity_excluded_duplication'] = {'extra_exact_content_rows': n - len(exact_hashes), 'extra_whitespace_normalized_rows': n - len(formatted_hashes), 'example_source_id_pairs': duplicate_examples, 'excluded_fields': ['id_intern', ':id', ':created_at', ':updated_at'], 'warning': 'Equal content does not prove duplicate contracts; aggregate batches can contain legitimately indistinguishable business payloads.'}
    result['gencat_comparable_presence'] = {k: {'count': presence[k], 'percent': round(presence[k] / n * 100, 4)} for k in tests}
    delays, delay_examples, field_disagreements = [], [], []
    samepubrows = db.execute("SELECT l.id,l.updated,l.publication_id,l.data pdata,g.data gdata FROM latest l JOIN g ON g.uuid=l.uuid AND g.publication_id=l.publication_id WHERE json_extract(g.data,'$.es_agregada')='NO' GROUP BY l.id")
    for r in samepubrows:
        a, b = json.loads(r['pdata']), json.loads(r['gdata'])
        times = [v for k, v in b.items() if k.startswith('data_publicacio') and v]
        if not times:
            continue
        gt = datetime.fromisoformat(max(times)).replace(tzinfo=ZoneInfo('Europe/Madrid'))
        delta = (datetime.fromisoformat(r['updated']) - gt).total_seconds()
        delays.append(delta)
        if delta < 0 and len(delay_examples) < 15:
            delay_examples.append({'placsp_id': r['id'], 'updated': r['updated'], 'gencat_latest_publication_time': max(times), 'publication_id': r['publication_id'], 'seconds': delta})
    result['same_publication_timestamp_difference_proxy'] = {'pairs': len(delays), 'negative': sum(d < 0 for d in delays), 'median_seconds': statistics.median(delays) if delays else None, 'min_seconds': min(delays, default=None), 'max_seconds': max(delays, default=None), 'negative_examples': delay_examples, 'warning': 'Not measured network arrival latency. Uses latest non-null publication column per representative Gencat row; floating times interpreted as Europe/Madrid, which is supported by phase samples but not a universal guarantee.'}
    g_by_exp = defaultdict(list)
    for r in db.execute("SELECT uuid,expediente,data FROM g WHERE json_extract(data,'$.es_agregada')='NO' GROUP BY uuid"):
        b = json.loads(r['data'])
        g_by_exp[norm(r['expediente'])].append((r['uuid'], b.get('nom_organ', ''), b.get('denominacio', ''), b.get('pressupost_licitacio_sense_1')))
    fuzzy = []
    for r in db.execute('SELECT * FROM latest WHERE NOT EXISTS (SELECT 1 FROM g WHERE g.uuid=latest.uuid)'):
        a = json.loads(r['data'])
        for uuid, buyer, title, budget in g_by_exp[norm(a['expediente'])]:
            buyer_score = SequenceMatcher(None, norm(a['buyer_name']), norm(buyer)).ratio()
            title_score = SequenceMatcher(None, norm(a['title']), norm(title)).ratio()
            money_equal = amount(a['budget']) is not None and amount(a['budget']) == amount(budget)
            if buyer_score >= 0.8 or title_score >= 0.8:
                fuzzy.append({'placsp_id': r['id'], 'gencat_uuid': uuid, 'expediente': a['expediente'], 'buyer_similarity': round(buyer_score, 4), 'title_similarity': round(title_score, 4), 'procedure_budget_equal': money_equal, 'automatic_merge': False})
    result['fuzzy_candidate_experiment'] = {'blocking': 'exact punctuation-stripped expediente, previously unmatched latest PLACSP UUID; buyer or title SequenceMatcher >= .8', 'candidate_pairs': len(fuzzy), 'placsp_ids': len({x['placsp_id'] for x in fuzzy}), 'examples': fuzzy[:30], 'warning': 'Exploratory uncalibrated thresholds, not estimated precision or proof of identity.'}
    (OUT / 'fuzzy_candidates.json').write_text(json.dumps(fuzzy, ensure_ascii=False, indent=2))
    (OUT / 'semantic_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != 'examples'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
