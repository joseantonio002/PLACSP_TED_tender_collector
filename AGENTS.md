# Development instructions

Use `.venv/bin/python`; never install Python packages globally. Research dependencies are pinned in `requirements-research.txt`.

Develop incrementally. For each requested change:

1. Inspect the relevant existing code and documentation first.
2. Make the smallest change required for the current task.
3. Do not implement unrelated future functionality.
4. Add or update tests for introduced behavior.
5. Run the relevant tests after changes and do not finish with failing tests.
6. Prefer simple, typed, readable Python over premature abstractions.

Tests should be deterministic and should not depend on live external services unless explicitly marked as live tests. Prefer representative real source data stored as local fixtures.

Raw acquisitions under `data/raw/` are immutable. `data/raw/download_manifest.jsonl` is append-only. Never overwrite a successful acquisition to refresh a source; create a new acquisition instead.

Existing research entry points include:

* `scripts/download.py`
* `scripts/extract_documentation.py`
* `scripts/inspect_placsp.py`
* `scripts/inspect_gencat.py`
* `scripts/compare_sources.py`

Run scripts from the repository root. SQLite files under `data/processed/` are analysis indexes, not production schemas. Preserve existing exploratory scripts and user files unless explicitly asked to remove them.

Important research findings already established:

* PLACSP research dates are filtered using entry `updated`.
* Generalitat main rows use `data_publicacio*` dates; execution actions use different date semantics. Do not conflate these cohorts.
* Current-year PLACSP archives and Socrata tables may change upstream.
* PSCP exports may contain legacy XML even through `/json/` endpoints; inspect actual content rather than trusting URL names.
* `es_agregada=SI` UUIDs identify publication batches, not individual procurement procedures.

Current research verification commands:

```bash
.venv/bin/python -m unittest discover -s scripts -p 'test_*.py' -v
.venv/bin/python -m compileall -q scripts
.venv/bin/python scripts/verify_artifacts.py
.venv/bin/python scripts/verify_parsers.py
.venv/bin/python scripts/verify_report.py
```

`REPORT.md` contains the full research reproduction sequence, findings, and limitations.
