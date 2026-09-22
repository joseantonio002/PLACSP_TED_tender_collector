import json
from pathlib import Path

from download import ROOT

out = ROOT / 'data/analysis/phase_details'
out.mkdir(parents=True, exist_ok=True)
for folder in ('phase_probes', 'phases'):
    for path in (ROOT / 'data/raw/gencat' / folder).glob('*.json'):
        obj = json.loads(path.read_bytes())
        (out / path.name).write_text(json.dumps(obj, ensure_ascii=False, indent=2))
        print(path.name, type(obj).__name__, list(obj)[:50] if isinstance(obj, dict) else len(obj))
