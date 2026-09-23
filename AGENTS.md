# TenderWatch development instructions

`PROJECT_CONTEXT.md` is the high-level source of truth for TenderWatch. The current procurement data sources are PLACSP and Generalitat de Catalunya, with an initial Catalunya / Barcelona focus. Historical research and archived experiments do not expand the current source scope or define a final production architecture.

Use `.venv/bin/python`; never install Python packages globally. Install the development environment with `.venv/bin/python -m pip install -e ".[dev]" -r research/requirements.txt`. Application packaging and pytest configuration are in `pyproject.toml`; the existing research dependencies remain pinned separately.

Develop incrementally. For each requested change:

1. Inspect the relevant existing code and documentation first.
2. Make the smallest change required for the current task.
3. Do not implement unrelated future functionality.
4. Add or update tests for introduced behavior.
5. Run the relevant tests after changes and do not finish with failing tests.
6. Prefer simple, typed, readable Python over premature abstractions.

Existing research entry points include:

- `research/scripts/download.py`
- `research/scripts/extract_documentation.py`
- `research/scripts/inspect_placsp.py`
- `research/scripts/inspect_gencat.py`
- `research/scripts/compare_sources.py`

Run scripts from the repository root. SQLite files under `data/processed/` are analysis indexes, not production schemas. Preserve existing exploratory scripts and user files unless explicitly asked to remove them.

Application code belongs in `src/tenderwatch/`; tests belong in `tests/`, with small local fixtures in `tests/fixtures/`. Research code is not application code. Existing research regression tests are retained in `tests/research/` and run as part of the complete pytest suite. The test-only `pythonpath` configuration preserves their existing flat imports. Do not import the live-request experiments in `research/legacy/` into tests.

Verification commands:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src tests research/scripts
.venv/bin/python research/scripts/verify_artifacts.py
.venv/bin/python research/scripts/verify_parsers.py
.venv/bin/python research/scripts/verify_report.py
```

The default pytest suite needs no bulk data or external services; future `live` tests are opt-in with `-m live`. The research verification scripts require the local snapshot and can refresh derived verification outputs, but never raw acquisitions.

## Project documentation

Keep project documentation consistent with the repository as it evolves.

- Update `PROJECT_CONTEXT.md` when an implemented and accepted change materially affects the project scope, core concepts, or high-level architecture.
- Do not update it for temporary implementation details, experiments, or unconfirmed ideas.
- Update `AGENTS.md` only when a new stable repository-wide working rule is necessary. Do not turn one-off implementation decisions into permanent instructions.
- Never remove or rewrite existing `AGENTS.md` rules unless the change is clearly required by the task.
- Mention any changes to `AGENTS.md` or `PROJECT_CONTEXT.md` in the task summary.
