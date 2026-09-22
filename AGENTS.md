# Procurement research environment

Use `.venv/bin/python`; do not install Python packages globally. Research dependencies are pinned in `requirements-research.txt`; requests was already installed, and pypdf 6.17.0 was added for local official-PDF text extraction.

Raw acquisitions are immutable under `data/raw/`, with an append-only `data/raw/download_manifest.jsonl`. Never replace a successful raw acquisition to refresh a source: use a new filename/run directory. The downloader resumes at validated-file/page boundaries, not HTTP byte boundaries. Current-year PLACSP archives and Socrata tables are mutable upstream.

Research entry points are `scripts/download.py`, `scripts/extract_documentation.py`, `scripts/inspect_placsp.py`, `scripts/inspect_gencat.py`, and `scripts/compare_sources.py`. Run from repository root. SQLite files under `data/processed/` are analysis indexes, not production schemas. PLACSP dates are filtered using entry/updated; Generalitat main rows are selected by any data_publicacio* date; execution actions have a different date definition. Do not conflate these cohorts.

Preserve existing exploratory root scripts and user files. The investigation does not use subagents or create production infrastructure.

Verification: `.venv/bin/python -m unittest discover -s scripts -p 'test_*.py' -v`, `.venv/bin/python -m compileall -q scripts`, `.venv/bin/python scripts/verify_artifacts.py`, `.venv/bin/python scripts/verify_parsers.py`, and `.venv/bin/python scripts/verify_report.py`. `REPORT.md` has the complete reproduction sequence and limitations. Validated downloads resume without network refresh. Rich PSCP exports may be legacy XML even through a `/json/` endpoint; do not rely on URL names for content type. `es_agregada=SI` (accented in source as SÍ) UUIDs identify publication batches, not individual procurement procedures.
