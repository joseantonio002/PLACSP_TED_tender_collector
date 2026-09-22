from __future__ import annotations

import argparse
import hashlib
import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/raw'
MANIFEST = RAW / 'download_manifest.jsonl'
DOMAIN = 'https://analisi.transparenciacatalunya.cat'
FEEDS = {'aggregated': ('1044', 'PlataformasAgregadasSinMenores'), 'native': ('643', 'licitacionesPerfilesContratanteCompleto3')}
START, END = '2025-01-01T00:00:00', '2026-09-23T00:00:00'


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str:
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def record(item: dict[str, Any]) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open('a') as f:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')


def fetch(source: str, url: str, filename: str, params: dict | None = None, period: str | None = None) -> Path:
    path = RAW / source / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and MANIFEST.exists():
        matches = [json.loads(s) for s in MANIFEST.read_text().splitlines() if s]
        matches = [m for m in matches if m.get('filename') == str(path.relative_to(ROOT)) and m.get('validated')]
        if matches and matches[-1]['sha256'] == digest(path):
            return path
        raise RuntimeError(f'Refusing to overwrite unverified existing raw file: {path}')
    partial = path.with_suffix(path.suffix + '.partial')
    for attempt in range(5):
        began = now()
        try:
            with requests.get(url, params=params, stream=True, timeout=(30, 180), headers={'User-Agent': 'ProcurementSchemaResearch/0.1', 'Accept-Encoding': 'identity'}) as r:
                meta = {'source': source, 'download_started_at': began, 'downloaded_at': now(), 'source_url': url, 'resolved_url': r.url, 'request_parameters': params or {}, 'request_headers': {'Accept-Encoding': 'identity', 'User-Agent': 'ProcurementSchemaResearch/0.1'}, 'period': period, 'filename': str(path.relative_to(ROOT)), 'http_status': r.status_code, 'response_headers': {k: v for k, v in r.headers.items() if k.lower() not in ('set-cookie', 'authorization', 'proxy-authorization')}, 'original_filename': r.headers.get('Content-Disposition'), 'attempt': attempt + 1}
                if not r.ok:
                    record({**meta, 'validated': False, 'error': r.text[:1000]})
                    r.raise_for_status()
                with partial.open('wb') as f:
                    for chunk in r.iter_content(1024 * 1024):
                        f.write(chunk)
                if path.suffix == '.zip':
                    with zipfile.ZipFile(partial) as z:
                        bad = z.testzip()
                        if bad:
                            raise ValueError(f'ZIP CRC failure: {bad}')
                elif path.suffix == '.json':
                    json.loads(partial.read_bytes())
                elif path.suffix in ('.atom', '.xml'):
                    ET.parse(partial)
                elif path.suffix == '.pdf' and not partial.read_bytes().startswith(b'%PDF'):
                    raise ValueError('Not a PDF')
                meta.update(downloaded_at=now(), sha256=digest(partial), size_bytes=partial.stat().st_size, validated=True)
                partial.rename(path)
                record(meta)
                print(f'{source}/{filename}: {meta["size_bytes"]:,} bytes', flush=True)
                return path
        except (requests.RequestException, ValueError, zipfile.BadZipFile, ET.ParseError) as exc:
            record({'source': source, 'source_url': url, 'request_parameters': params or {}, 'period': period, 'downloaded_at': now(), 'attempt': attempt + 1, 'validated': False, 'error': str(exc)})
            permanent_http = isinstance(exc, requests.HTTPError) and exc.response is not None and 400 <= exc.response.status_code < 500 and exc.response.status_code not in (408, 429)
            if attempt == 4 or permanent_http:
                raise
            time.sleep(min(2 ** attempt * 2, 30))
    raise RuntimeError('Unreachable')


def discovery() -> None:
    docs = {
        'aggregation.html': 'https://www.hacienda.gob.es/es-es/gobiernoabierto/datos%20abiertos/paginas/licitacionesagregacion.aspx',
        'native.html': 'https://www.hacienda.gob.es/es-es/gobiernoabierto/datos%20abiertos/paginas/licitacionescontratante.aspx',
        'syndication-1.3.pdf': 'https://www.hacienda.gob.es/Documentacion/Publico/D.G.%20PATRIMONIO/Plataforma_Contratacion/especificacion-sindicacion-1-3.pdf',
        'openplacsp-2.1.pdf': 'https://contrataciondelestado.es/datosabiertos/DGPE_PLACSP_OpenPLACSP_v.2.1.pdf',
    }
    for filename, url in docs.items():
        try:
            fetch('documentation', url, filename)
        except requests.RequestException as exc:
            print(f'Document unavailable: {exc}', flush=True)
    for dataset in ('ybgg-dgi6', '8idu-wkjv'):
        fetch('gencat', f'{DOMAIN}/api/views/{dataset}.json', f'{dataset}/metadata-before.json')
        fetch('gencat', f'{DOMAIN}/resource/{dataset}.json', f'{dataset}/probe.json', {'$limit': 5, '$select': '*,:id,:created_at,:updated_at'})


def placsp(feed: str, periods: list[str]) -> None:
    code, name = FEEDS[feed]
    for period in periods:
        url = f'https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_{code}/{name}_{period}.zip'
        fetch('placsp', url, f'{feed}/{name}_{period}.zip', period=period)


def gencat(dataset: str) -> None:
    meta_path = fetch('gencat', f'{DOMAIN}/api/views/{dataset}.json', f'{dataset}/metadata-before.json')
    meta = json.loads(meta_path.read_bytes())
    dates = [c['fieldName'] for c in meta['columns'] if c['fieldName'].startswith('data_publicacio')]
    where = ' OR '.join(f"({f} >= '{START}' AND {f} < '{END}')" for f in dates)
    if not where:
        if dataset != '8idu-wkjv':
            raise ValueError('No publication date fields found')
        where = '1=1'
    endpoint = f'{DOMAIN}/resource/{dataset}.json'
    countpath = fetch('gencat', endpoint, f'{dataset}/count-before.json', {'$select': 'count(*)', '$where': where})
    count = int(json.loads(countpath.read_bytes())[0]['count'])
    print(f'{dataset}: {count:,} rows, date fields {dates}', flush=True)
    offset, fetched = 0, 0
    while offset < count:
        p = fetch('gencat', endpoint, f'{dataset}/pages/{offset:09d}.json', {'$select': '*,:id,:created_at,:updated_at', '$where': where, '$order': ':id', '$limit': 10000, '$offset': offset}, period=('all available execution actions; local date profiling' if dataset == '8idu-wkjv' else f'{START}/{END} exclusive-end; any publication date'))
        rows = json.loads(p.read_bytes())
        if not rows:
            raise RuntimeError(f'Unexpected empty page at {offset}')
        fetched += len(rows)
        offset += len(rows)
    fetch('gencat', f'{DOMAIN}/api/views/{dataset}.json', f'{dataset}/metadata-after.json')
    fetch('gencat', endpoint, f'{dataset}/count-after.json', {'$select': 'count(*)', '$where': where})
    if fetched != count:
        raise RuntimeError(f'Row count mismatch: {fetched} != {count}')


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=['discovery', 'placsp', 'gencat'])
    p.add_argument('--feed', choices=FEEDS, default='aggregated')
    p.add_argument('--periods', nargs='+', default=['2025', '2026'])
    p.add_argument('--dataset', default='ybgg-dgi6')
    a = p.parse_args()
    if a.mode == 'discovery':
        discovery()
    elif a.mode == 'placsp':
        placsp(a.feed, a.periods)
    else:
        gencat(a.dataset)


if __name__ == '__main__':
    main()
