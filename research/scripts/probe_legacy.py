import json
import requests

from download import fetch

for publication in ('107376474', '115526013', '102238048', '103585423'):
    try:
        path = fetch('gencat', f'https://contractaciopublica.cat/portal-api/documents-publicacio/json/{publication}', f'legacy_probes/{publication}.bin')
        try:
            obj = json.loads(path.read_bytes())
            print(publication, 'JSON', type(obj).__name__)
        except ValueError:
            print(publication, 'Non-JSON response preserved', path.read_bytes()[:120])
    except requests.HTTPError as exc:
        print(publication, exc.response.status_code)
