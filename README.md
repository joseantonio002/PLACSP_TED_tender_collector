# TenderWatch

TenderWatch is a public procurement data platform for discovering and exploring tenders from **PLACSP and Generalitat de Catalunya**, initially focused on Catalunya / Barcelona. Its goal is to reconcile source observations into traceable canonical tender states and preserve their history for search and exploration.

[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) is the high-level source of truth for the current project direction. The repository is transitioning from research to implementation: the research is preserved, and the application package remains intentionally empty, with no procurement business logic or external-service infrastructure yet.

## Repository layout

```text
src/tenderwatch/             Installable TenderWatch application package
tests/                      Offline test suite
  test_smoke.py              Minimal application package-import test
  research/                 Existing research regression tests
  fixtures/                 Small test fixtures only; currently reserved
research/
  scripts/                  Research acquisition, profiling and verification tools
  legacy/                   Archived experiments and historical source notes
  docs/                     Research report and existing local notes
  requirements.txt          Pinned research-only dependencies
analysis/                   Research metrics, CSVs and case-selection metadata
data/
  raw/                      Immutable acquisitions and append-only manifest
  processed/                Generated research indexes, including SQLite
  analysis/                 Extracted documentation and rendered phase data
  samples/                  Preserved research case-study evidence
pyproject.toml              src-layout packaging, dev dependency and pytest settings
```

`analysis/` and all `data/` paths deliberately retain their original locations: manifests, SQLite records and case references embed these paths. Existing raw downloads, outputs and samples have not been moved or rewritten. Research samples are evidence, not automatically application test fixtures; add only small, relevant fixtures when a feature needs them. The existing `guia.md` notes are now in `research/docs/` and remain Git-ignored as before.

The full report is [research/docs/REPORT.md](research/docs/REPORT.md). Its findings are unchanged; links and reproduction commands use the new layout.

## Install dependencies

Use Python 3.12 or newer and the existing local `.venv`. Do not install packages globally. From the repository root:

```bash
.venv/bin/python -m pip install -e ".[dev]" -r research/requirements.txt
```

The application has no runtime dependencies yet. The `dev` extra installs pytest 8.4.2. The separate research requirements retain requests 2.34.2 and pypdf 6.17.0; requests is also needed by the preserved research regression tests. The build backend is pinned to setuptools 80.9.0.

## Run tests

Run the complete default suite, including all existing research regression tests:

```bash
.venv/bin/python -m pytest
```

Run only the smallest smoke test:

```bash
.venv/bin/python -m pytest tests/test_smoke.py
```

Run only the preserved research tests:

```bash
.venv/bin/python -m pytest tests/research
```

These tests use no live APIs, databases or bulk downloads. `testpaths` limits collection to `tests/`; research tools with import-time side effects are not collected. The test-only `pythonpath` setting exposes the legacy flat research modules without changing their imports or adding them to the application package. Future live-service tests must use `@pytest.mark.live`; they are excluded by default and can be selected explicitly with `-m live`. No live tests exist yet.

## Research tools and data integrity

Run research scripts from the repository root, for example:

```bash
.venv/bin/python research/scripts/download.py --help
.venv/bin/python research/scripts/verify_artifacts.py
.venv/bin/python research/scripts/verify_report.py
```

The integrity tools require the local research snapshot and may refresh their generated verification JSON under `analysis/`; they are not part of the ordinary pytest suite. They do not modify raw acquisitions. `verify_artifacts.py` checks checksums and case references; `verify_report.py` checks the historical report and its pinned snapshot metrics. The report contains the complete research reproduction sequence. Do not run downloader commands merely to test the application.

The original experiments are preserved unchanged in `research/legacy/`. They make live requests when executed or imported, so do not import them into application code or tests. Generated data, virtual environments, package build artifacts and test caches are excluded from Git where appropriate.

## Current sources

- **PLACSP — Plataforma de Contratación del Sector Público:** [official native-profile distribution catalogue](https://www.hacienda.gob.es/es-es/gobiernoabierto/datos%20abiertos/paginas/licitacionescontratante.aspx) and [aggregated-platform distribution catalogue](https://www.hacienda.gob.es/es-es/gobiernoabierto/datos%20abiertos/paginas/licitacionesagregacion.aspx).
- **Generalitat de Catalunya:** [official PSCP publications dataset metadata](https://analisi.transparenciacatalunya.cat/api/views/ybgg-dgi6.json) and [execution-actions dataset metadata](https://analisi.transparenciacatalunya.cat/api/views/8idu-wkjv.json).

References for superseded source experiments are preserved separately in [research/legacy/README.md](research/legacy/README.md). External identifiers or publication links appearing inside acquired data do not make their publishing platforms additional TenderWatch ingestion sources.

