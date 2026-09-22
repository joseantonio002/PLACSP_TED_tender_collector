from pathlib import Path
from pypdf import PdfReader

root = Path(__file__).resolve().parents[1]
out = root / 'data/analysis/documentation'
out.mkdir(parents=True, exist_ok=True)
for path in (root / 'data/raw/documentation').glob('*.pdf'):
    reader = PdfReader(path)
    text = '\n\n'.join(f'PAGE {i + 1}\n{page.extract_text()}' for i, page in enumerate(reader.pages))
    (out / f'{path.stem}.txt').write_text(text)
