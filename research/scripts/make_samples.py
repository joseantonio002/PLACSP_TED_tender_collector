from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlparse
import zipfile

from download import ROOT, fetch
from inspect_gencat import url


def make_samples(download_phases: bool) -> None:
    specs = json.loads((ROOT / 'analysis/case_selection.json').read_bytes())
    db = sqlite3.connect(ROOT / 'data/processed/research.sqlite')
    db.row_factory = sqlite3.Row
    g = sqlite3.connect(ROOT / 'data/processed/gencat/ybgg-dgi6.sqlite')
    g.row_factory = sqlite3.Row
    cases = []
    for spec in specs:
        folder = ROOT / 'data/samples' / spec['case_id']
        folder.mkdir(parents=True, exist_ok=True)
        ps, gs, refs = [], [], []
        pids = spec.get('placsp_ids', []) + ([spec['placsp_id']] if spec.get('placsp_id') else [])
        for pid in pids:
            ps.extend(json.loads(r[0]) for r in db.execute('SELECT data FROM p WHERE id=? ORDER BY julianday(updated)', (pid,)))
        if spec.get('gencat_uuid') and not ps:
            ps = [json.loads(r[0]) for r in db.execute('SELECT data FROM p WHERE uuid=? ORDER BY julianday(updated)', (spec['gencat_uuid'],))]
        uuids = sorted({p['uuid'] for p in ps if p['uuid']} | ({spec['gencat_uuid']} if spec.get('gencat_uuid') else set()))
        for uuid in uuids:
            gs.extend(g.execute('SELECT * FROM observations WHERE uuid=? ORDER BY source_id', (uuid,)))
        if spec.get('gencat_buyer_exp'):
            gs.extend(g.execute('SELECT * FROM observations WHERE buyer=? AND expediente=? ORDER BY source_id', spec['gencat_buyer_exp']))
        gs = {r['id']: r for r in gs}.values()
        for i, p in enumerate(ps):
            with zipfile.ZipFile(ROOT / p['archive']) as z:
                xml = z.read(p['member'])
            entries = list(re.finditer(rb'<entry(?:\s[^>]*)?>.*?</entry>', xml, re.DOTALL))
            match = entries[p['ordinal']]
            fragment = match.group()
            filename = f'placsp-{i:03d}.xml.fragment'
            (folder / filename).write_bytes(fragment)
            refs.append({'source': 'placsp', 'file': filename, 'archive': p['archive'], 'member': p['member'], 'entry_ordinal': p['ordinal'], 'byte_start_in_member': match.start(), 'byte_end_in_member': match.end(), 'fragment_sha256': hashlib.sha256(fragment).hexdigest(), 'note': 'Exact byte slice, namespace bindings inherited from parent feed; original complete XML is in archive member.'})
        (folder / 'placsp-extracted.json').write_text(json.dumps(ps, ensure_ascii=False, indent=2))
        gdata = [json.loads(r['data']) for r in gs]
        (folder / 'gencat-rows.json').write_text(json.dumps(gdata, ensure_ascii=False, indent=2))
        refs.extend({'source': 'gencat', 'page': r['page'], 'row_ordinal': r['ordinal'], 'socrata_id': r['id'], 'id_intern': r['source_id']} for r in gs)
        phases = {}
        for r in gdata:
            for k, value in r.items():
                if k.startswith('url_json') and url(value):
                    u = url(value)
                    match = re.search(r'/json(?:-xifrat)?/(\d+)', u)
                    key = match.group(1) if match else hashlib.sha256(u.encode()).hexdigest()[:16]
                    phases[key] = {'url': u, 'field': k, 'source_row_id': r.get(':id')}
        if spec.get('execution_buyer_exp'):
            execution = sqlite3.connect(ROOT / 'data/processed/gencat/8idu-wkjv.sqlite')
            execution.row_factory = sqlite3.Row
            erows = list(execution.execute('SELECT * FROM observations WHERE buyer=? AND expediente=?', spec['execution_buyer_exp']))
            edata = [json.loads(r['data']) for r in erows]
            (folder / 'gencat-execution-rows.json').write_text(json.dumps(edata, ensure_ascii=False, indent=2))
            refs.extend({'source': 'gencat-execution', 'page': r['page'], 'row_ordinal': r['ordinal'], 'socrata_id': r['id']} for r in erows)
            for r in edata:
                if r.get('url_json'):
                    phases[r['url_json'].rsplit('/', 1)[-1]] = {'url': r['url_json'], 'field': 'execution.url_json'}
            execution.close()
        if spec.get('fetch_historical_notices'):
            for p in ps:
                if p['publication_id']:
                    phases.setdefault(p['publication_id'], {'url': f'https://contractaciopublica.cat/portal-api/documents-publicacio/json/{p["publication_id"]}', 'field': 'historical_placsp_publication_link', 'source_placsp_updated': p['updated']})
        if download_phases:
            for key, phase in phases.items():
                try:
                    path = fetch('gencat', phase['url'], f'phases/{key}.json')
                    phase['raw_path'] = str(path.relative_to(ROOT))
                except Exception as exc:
                    phase['error'] = str(exc)
                    try:
                        import xml.etree.ElementTree as ET
                        fallback_url = f'https://contractaciopublica.cat/portal-api/documents-publicacio/json/{key}'
                        fallback = fetch('gencat', fallback_url, f'legacy_probes/{key}.bin')
                        ET.parse(fallback)
                        phase.update(raw_path=str(fallback.relative_to(ROOT)), format='xml', recovered_by=fallback_url)
                    except Exception as fallback_exc:
                        phase['fallback_error'] = str(fallback_exc)
        case = {**spec, 'placsp_observations': len(ps), 'gencat_rows': len(gdata), 'evidence_references': refs, 'phase_json': phases, 'folder': str(folder.relative_to(ROOT))}
        (folder / 'evidence.json').write_text(json.dumps(case, ensure_ascii=False, indent=2))
        cases.append(case)
        print(spec['case_id'], len(ps), len(gdata), len(phases), flush=True)
    (ROOT / 'analysis/cases.json').write_text(json.dumps(cases, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--download-phases', action='store_true')
    make_samples(p.parse_args().download_phases)
