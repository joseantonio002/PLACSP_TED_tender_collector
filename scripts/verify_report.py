import json
import re
from urllib.parse import urlparse

from download import ROOT

report = (ROOT / 'REPORT.md').read_text()
expected = [
    '# 1. How PLACSP data works',
    '# 2. How Generalitat de Catalunya data works',
    '# 3. Differences between PLACSP and Generalitat schemas',
    '# 4. Proposed common normalized schema',
    '# 5. Possible reconciliation strategies',
    '# 6. Hypothesis validation',
    '# 7. Open questions / next experiments',
]
headings = [line for line in report.splitlines() if line.startswith('# ')]
assert headings == expected, headings
assert not re.search(r'\{\{FINAL|\bTODO\b|\bTBD\b', report)
links = re.findall(r'\]\(([^)]+)\)', report)
missing = [link for link in links if not urlparse(link).scheme and not (ROOT / link.split('#')[0]).exists()]
assert not missing, missing
m = json.loads((ROOT / 'analysis/metrics.json').read_bytes())
a = json.loads((ROOT / 'analysis/aggregated_metrics.json').read_bytes())
v = json.loads((ROOT / 'analysis/verification.json').read_bytes())
assert sum(m['placsp']['monthly'].values()) == m['placsp']['selected_record_occurrences'] == 218461
assert sum(m['gencat']['ybgg-dgi6']['month_by_latest_available_publication_date'].values()) == 1070969
assert m['placsp']['counts']['all_entries'] == 1624581
assert m['placsp']['unique_atom_ids'] == 65954
assert a['matching']['placsp_ids_any_historical_exact_uuid'] == 56310
assert a['matching']['latest_id_field_comparisons']['same_publication_three_fields_equal'] == 33831
assert sum(a['matching']['latest_id_candidate_tiers'].values()) == a['placsp']['unique_atom_ids']
assert v['case_count'] == 20
assert f"{v['size_bytes']:,}" in report
assert f"{v['successful_raw_files']} successfully acquired raw files" in report
assert not v['bad_raw_hashes'] and not v['missing_raw_files'] and not v['sample_reference_errors']
result = {'main_headings': headings, 'missing_local_links': missing, 'snapshot_metric_assertions': 'passed', 'note': 'Numerical assertions pin the reported research snapshot, not future upstream datasets.'}
(ROOT / 'analysis/report_verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2))
