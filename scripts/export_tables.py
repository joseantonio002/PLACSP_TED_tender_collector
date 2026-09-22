from collections import Counter
import csv
import json

from download import ROOT

out = ROOT / 'analysis'
metrics = json.loads((out / 'metrics.json').read_bytes())
agg = json.loads((out / 'aggregated_metrics.json').read_bytes())
audit = json.loads((out / 'semantic_audit.json').read_bytes())
g = metrics['gencat']['ybgg-dgi6']
native_months = Counter()
for profile in metrics['placsp']['archive_profiles']:
    if '/native/' in profile['archive']:
        native_months.update(profile['selected_months'])
months = sorted(set(metrics['placsp']['monthly']) | set(g['month_by_latest_available_publication_date']))
with (out / 'monthly.csv').open('w') as f:
    w = csv.writer(f)
    w.writerow(['month', 'placsp_aggregated_entry_updated', 'placsp_native_entry_updated', 'gencat_rows_latest_publication_column'])
    for m in months:
        w.writerow([m, agg['placsp']['monthly'].get(m, 0), native_months[m], g['month_by_latest_available_publication_date'].get(m, 0)])
with (out / 'gencat_publication_dates_monthly.csv').open('w') as f:
    w = csv.writer(f)
    w.writerow(['source_field', 'month', 'row_count'])
    for field, periods in g['date_fields_monthly'].items():
        for month, n in sorted(periods.items()):
            w.writerow([field, month, n])
with (out / 'field_presence.csv').open('w') as f:
    w = csv.writer(f)
    w.writerow(['cohort', 'field_concept', 'count', 'denominator', 'percent'])
    for label, data in [('placsp_all_selected', metrics['placsp']), ('placsp_aggregated_selected', agg['placsp'])]:
        n = data['selected_record_occurrences']
        for field, count in data['selected_field_presence'].items():
            w.writerow([label, field, count, n, round(count / n * 100, 4)])
    for kind, data in audit['gencat_presence_by_aggregation'].items():
        for field, values in data['fields'].items():
            w.writerow([f'gencat_es_agregada_{kind}', field, values['count'], data['rows'], values['percent']])
    for field, values in audit['gencat_comparable_presence'].items():
        w.writerow(['gencat_all', field, values['count'], g['counts']['rows'], values['percent']])
summary = {'placsp': {k: v for k, v in metrics['placsp'].items() if k not in ('archive_profiles', 'monthly')}, 'gencat_counts': g['counts'], 'gencat_semantics': metrics['gencat']['main_semantic_counts'], 'matching': {k: v for k, v in metrics['matching'].items() if k != 'examples'}, 'audit_counts': audit['counts'], 'gencat_duplication': audit['gencat_identity_excluded_duplication'], 'geography': audit['placsp_geography'], 'unique_buyer_bundles': audit['placsp_unique_buyer_identifier_bundles'], 'time_difference_proxy': {k: v for k, v in audit['same_publication_timestamp_difference_proxy'].items() if k != 'negative_examples'}, 'fuzzy_counts': {k: v for k, v in audit['fuzzy_candidate_experiment'].items() if k != 'examples'}}
(out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
print(json.dumps(summary, ensure_ascii=False, indent=2))
