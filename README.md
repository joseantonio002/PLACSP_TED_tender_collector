# TenderWatch

TenderWatch is a public procurement data platform for discovering and exploring tenders from **PLACSP and Generalitat de Catalunya**, initially focused on Catalunya / Barcelona. Its goal is to reconcile source observations into traceable canonical tender states and preserve their history for search and exploration.

[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) is the high-level source of truth for the current project direction. The application now reads retained research acquisitions into independent source records, immutable `RawSourceRecord`s, and source-attributed immutable `NormalizedObservation`s. Reconciliation, canonical representations, and queries are not implemented yet. The research remains preserved, with no new acquisition or external-service infrastructure.

## Repository layout

```text
src/tenderwatch/             Installable TenderWatch application package
tests/                      Offline test suite
  test_smoke.py              Minimal application package-import test
  research/                 Existing research regression tests
  fixtures/                 Small retained-evidence fixtures and explicit excerpts
docs/                       Implemented application contracts and usage
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

### Normalization suite

`tests/normalization/` exercises the implemented `RawSourceRecord -> NormalizedObservation` API using committed retained-evidence fixtures. The original test-first assertions, fixtures, and harness are unchanged. The harness automatically imports the real `tenderwatch.normalization` package; its absent-module expected-failure mechanism is inactive. All mapping tests now run normally, including under `--runxfail`.

```bash
.venv/bin/python -m pytest tests/normalization -q -r fE
.venv/bin/python -m pytest tests/normalization --runxfail -x
.venv/bin/python -m pytest tests/normalization/test_fixtures.py --audit-normalization-evidence -q
```

The third command is an optional audit requiring retained local research data; ordinary normalization tests block research-data fallback, database access, and network calls. Additional implementation-edge tests and workflow tests cover the inspection command and cached artifact resolver.

See [normalization contracts and implementation gates](research/docs/NORMALIZATION_TESTS.md#14-executable-test-contract-test-first-update) for source-path conventions, conservative policies, coverage, and fixture reductions.

## Normalize retained data for inspection

```bash
.venv/bin/python -m tenderwatch.sources --root .
```

This offline single-run command discovers manifest inputs, verifies checksums, creates every raw occurrence, calls `normalize`, and streams every resulting observation into a new **disposable, non-production** `tenderwatch-inspection-*` directory under the system temporary directory. The exact location is printed. It preserves repeated acquisitions and performs no date/geography filtering, joins, downloads, reconciliation, or canonical-state construction.

A full snapshot produces substantial output. For a bounded inspection or a selected family:

```bash
.venv/bin/python -m tenderwatch.sources --root . --limit 100
.venv/bin/python -m tenderwatch.sources --root . --artifact 'data/raw/gencat/phases/*'
.venv/bin/python -m tenderwatch.sources --root . --artifact 'data/raw/placsp/probes/native-head.atom' --limit 100
.venv/bin/python -m tenderwatch.sources --root . --raw-only
```

`--source placsp|gencat` filters sources. Repeat `--artifact` to select multiple retained-path globs. `--output-parent /existing/path` selects the parent of a fresh uniquely named directory; existing outputs are never overwritten. `--raw-only` retains the previous count-only behavior without creating output. `--limit` counts raw occurrences, not observations, and marks the run as limited.

Each inspection directory contains:

- `observations.jsonl`: one complete observation per line, including its raw ID, projection locator, versions, source paths, and Issues. Decimals are exact strings, dates/times are ISO strings, and UTC offsets are readable duration strings. This is a debugging export, not a production storage contract.
- `failures.jsonl`: contextual controlled failures, including unsupported legacy XML. Whole-batch fatal selection failures produce no partial batch output. Other raw occurrences still run.
- `summary.json`: counts by source/kind, diagnostic/failure totals, filters, and completion status (`complete`, `complete_with_unsupported`, `limited`, `failed`, or `interrupted`).

The first three processed raw occurrences are printed with compact normalized summaries (including zero observations for tombstones or an explicit failure). Huge raw payloads and tokenized export URLs are not dumped to stdout. All observations are collected on disk rather than retained together in memory. Known unsupported inputs are counted/reported; invalid inputs cause a nonzero exit after traversal. Unexpected programmer/invariant errors propagate and leave an interrupted summary. The generated directory is safe to delete and is never used as research evidence or production persistence.

### Normalization API and implementation

```python
from functools import partial
from tenderwatch.normalization import normalize, validate_observation
from tenderwatch.sources.artifacts import load_record

observations = normalize(raw_record, resolve=partial(load_record, root))
```

`normalize(raw, *, resolve, projection=None)` returns a tuple of frozen `NormalizedObservation`s. Ordinary inputs produce one, tombstones none, and explicit rich batch members one each. `projection` can select an exact batch-member JSON pointer. No observation combines raw occurrences. The command uses `verified_resolver(root, artifact)` to keep one verified artifact open and cache only the current parsed page/member; this avoids repeated archive hashing for each record. Parsed views are read-only to normalization.

The package `tenderwatch.normalization` contains `models.py` (frozen typed models), `common.py` (source-preserving value parsing), `placsp.py`, `tables.py`, and `publications.py` (adapters), plus `errors.py` and `validation.py`. Public controlled input errors derive from `NormalizationError`; `NormalizationInvariantError` is deliberately separate. Observation identity includes the raw occurrence, projection, schema version, and mapping version.

Supported mappings cover native/aggregated PLACSP Atom entries, Generalitat main and execution rows, and modern ordinary/batch/execution publication JSON. Legacy XML raises `UnsupportedNormalizationInput`. Reviewed code dictionaries are intentionally bounded (including EUR currency recognition); unknown codes produce Issues, not guessed categories. Comprehensive code lists, legacy mappings, additional contract-action families, PLACSP multi-project award grouping/effective dates, publisher-backed rich calendar interpretations, and document-size units remain deferred. Multi-project result groups are diagnosed rather than pooled; rich serialized business dates retain unresolved raw values rather than guessed legal instants. No entity resolution or reconciliation is performed.

See [the raw-source contract and API](docs/RAW_SOURCE_RECORDS.md) for supported acquisition formats, exact artifact locators, acquisition lineage, fixture provenance, and limitations.

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

