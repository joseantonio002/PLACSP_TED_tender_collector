from collections import Counter
import json
from pathlib import Path

from download import ROOT

cases = json.loads((ROOT / 'analysis/cases.json').read_bytes())
findings = []
for case in cases:
    folder = ROOT / case['folder']
    ps = json.loads((folder / 'placsp-extracted.json').read_bytes())
    gs = json.loads((folder / 'gencat-rows.json').read_bytes())
    phases = []
    for publication, ref in case['phase_json'].items():
        if 'raw_path' not in ref:
            phases.append({'publication_id': publication, 'error': ref.get('error')})
            continue
        if ref.get('format') == 'xml':
            import xml.etree.ElementTree as ET
            root = ET.parse(ROOT / ref['raw_path']).getroot()
            phases.append({'publication_id': publication, 'raw_path': ref['raw_path'], 'format': 'xml', 'root': root.tag, 'codiceVersion': root.findtext('codiceVersion'), 'tenderingSpaceId': root.findtext('tenderingSpaceId'), 'expediente': root.findtext('TenderingProcess/diligenceId'), 'recovered_after_primary_404': True})
            continue
        x = json.loads((ROOT / ref['raw_path']).read_bytes())
        pub = x.get('publicacio', {})
        data = pub.get('dadesPublicacio', {})
        docs = []
        def walk(value):
            if isinstance(value, dict):
                if 'hash' in value and ('titol' in value or 'id' in value):
                    docs.append({k: value.get(k) for k in ('id', 'titol', 'hash', 'mida')})
                for v in value.values():
                    walk(v)
            elif isinstance(value, list):
                for v in value:
                    walk(v)
        walk(pub)
        phases.append({'publication_id': publication, 'raw_path': ref['raw_path'], 'expediente': x.get('codiExpedient'), 'uuid': x.get('idExpedient'), 'schema_version': x.get('versio'), 'publication_at': x.get('dataPublicacioReal'), 'planned_publication_at': x.get('dataPublicacioPlanificada'), 'buyer': x.get('organ', {}).get('nom'), 'buyer_id': x.get('organ', {}).get('organContractacioId'), 'buyer_nif': x.get('organ', {}).get('nif'), 'phase': pub.get('fase', {}).get('ca'), 'budget': data.get('pressupostLicitacio'), 'estimated_value': data.get('valorEstimatContracte'), 'deadline': data.get('dataTerminiPresentacioOSolicitud'), 'correction_type': pub.get('tipusEsmena'), 'correction_reason': pub.get('motiuEsmena'), 'document_count': len(docs), 'documents': docs, 'lot_array_count': len(pub.get('dadesPublicacioLot', []))})
    findings.append({'case_id': case['case_id'], 'tags': case['tags'], 'placsp_timeline': [{k: p.get(k) for k in ('id', 'uuid', 'publication_id', 'expediente', 'updated', 'status', 'buyer_name', 'buyer_ids', 'budget', 'estimated_value', 'deadline_date', 'deadline_time', 'awards')} for p in ps], 'gencat': [{k: r.get(k) for k in ('id_intern', 'codi_expedient', 'codi_organ', 'nom_organ', 'denominacio', 'numero_lot', 'fase_publicacio', 'resultat', 'termini_presentacio_ofertes', 'pressupost_licitacio_sense', 'pressupost_licitacio_sense_1', 'valor_estimat_expedient', 'import_adjudicacio_sense', 'identificacio_adjudicatari', 'data_publicacio_anunci', 'data_publicacio_formalitzacio', 'data_formalitzacio_contracte', ':created_at', ':updated_at')} for r in gs], 'phases': phases})
    print(case['case_id'], 'P observations', len(ps), 'G rows', len(gs), 'phase JSON', len(phases), 'corrections', sum(bool(p.get('correction_type')) for p in phases))
(ROOT / 'analysis/case_findings.json').write_text(json.dumps(findings, ensure_ascii=False, indent=2))
