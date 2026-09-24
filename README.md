# TenderWatch

TenderWatch is a public procurement data platform for discovering and exploring tenders from **PLACSP and Generalitat de Catalunya**, initially focused on Catalunya / Barcelona. Its goal is to reconcile source observations into traceable canonical tender states and preserve their history for search and exploration.

[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) is the high-level source of truth for the current project direction. The application reads retained research acquisitions into independent source records and immutable `RawSourceRecord`s, normalizes them, resolves explicit procedure identities, and reconciles the evidence into `CanonicalObservation`s. The Search / Query Interface remains unimplemented. The research remains preserved, with no new acquisition or external-service infrastructure.

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
  NormalizedObservations/   Published normalization output (managed directory link)
  CanonicalObservations/    Published canonical output (managed directory link)
  ProcessingRuns/           Isolated run outputs, diagnostics, and shared current pointer
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

## Run retained data through canonical observations

```bash
.venv/bin/python -m tenderwatch.sources --root .
```

The offline single-execution workflow is:

```text
retained artifacts -> source records -> RawSourceRecord -> NormalizedObservation
    -> explicit procedure identity resolution -> reconciliation -> CanonicalObservation
```

The command verifies artifact checksums and persists all normalized observations before finishing identity resolution. Reconciliation reads those actual materialized observations, restoring the existing typed values. No acquisition, research index, or original fixture is rewritten. No database or network service is used.

Published output paths, relative to `--root`:

```text
data/NormalizedObservations/observations.jsonl
data/CanonicalObservations/canonical.jsonl
```

Each line is a complete object. Decimals are exact strings, dates/times are ISO strings, and UTC offsets use readable duration strings. `tenderwatch.serialization.load_observation(line)` restores normalized dataclasses without changing normalization semantics. Canonical output is ordered deterministically by canonical ID; evidence and alternatives are deterministically ordered. A repeated run over identical inputs/rules produces identical materialized JSONL bytes.

### Run isolation and diagnostics

The two public directories are managed symbolic links through a shared `data/ProcessingRuns/current` pointer. Each execution first writes to a fresh `data/ProcessingRuns/run-<id>/`. Both public stages switch together through one atomic pointer replacement only after successful processing. Old or failed runs stay separate, with no stale rows appended to the current output. Unmanaged directories/links at the public paths are refused, never removed. The private per-run directories are execution snapshots, **not** a canonical business-revision system. A consumer reading several files while another run may finish should resolve `ProcessingRuns/current` once and read both stages from that pinned run path.

`data/CanonicalObservations/` contains only final canonical objects. Diagnostics live separately under `data/ProcessingRuns/current/`:

- `summary.json`: raw, normalized, canonical, unresolved, conflict and artifact counts; filters; rule versions; normalization failures; completion status.
- `unresolved.jsonl`: each unassigned observation ID, explicit reason, and recognized procedure identifiers. Those observations remain in the normalized output.
- `failures.jsonl`: controlled normalization failures, including unsupported legacy XML. These inputs did not produce normalized observations.

Unsupported normalization inputs are reported. Invalid normalization inputs, I/O failures, or unexpected defects do not replace the last successfully published run. Known unsupported inputs can yield `complete_with_unsupported`; a deliberately bounded run is labelled `limited`. A conflicting canonical field is a represented result, not a processing crash. Partial/failed runs are inspectable through the private run path printed to stderr.

This avoids the previous `/tmp` capacity problem. All bulk outputs and temporary partition files use the repository's `data/` filesystem. Previous execution directories are retained and consume disk space; they are not automatically garbage-collected. Do not delete the run currently targeted by `ProcessingRuns/current` while consuming its outputs.

### Bounded runs and console output

A full snapshot produces substantial output. For a bounded run, source selection, or the previous raw-only traversal:

```bash
.venv/bin/python -m tenderwatch.sources --root . --limit 100
.venv/bin/python -m tenderwatch.sources --root . --artifact 'data/raw/gencat/phases/*'
.venv/bin/python -m tenderwatch.sources --root . --artifact 'data/raw/placsp/probes/native-head.atom' --limit 100
.venv/bin/python -m tenderwatch.sources --root . --raw-only
```

`--source placsp|gencat` filters sources; repeat `--artifact` to select several retained-path globs. `--limit` counts raw occurrences, not observations; a successful limited run becomes the newly published subset rather than mixing with a previous full run. `--raw-only` neither creates nor changes materialized outputs. The legacy `--output-parent` option now creates optional inspection aliases to that execution's normalized file and diagnostics; it does not relocate or duplicate the materialized dataset.

The command prints raw/normalized previews, up to three canonical examples, and counts and output paths for every stage. It does not dump whole datasets or tokenized export links. A compact identity index and temporary hash partitions avoid holding the full normalized corpus in memory; memory still depends on the largest reconciliation partition/group. This is a local batch algorithm, not distributed processing or incremental ingestion infrastructure.

### Normalization API and implementation

```python
from functools import partial
from tenderwatch.normalization import normalize, validate_observation
from tenderwatch.sources.artifacts import load_record

observations = normalize(raw_record, resolve=partial(load_record, root))
```

`normalize(raw, *, resolve, projection=None)` returns a tuple of frozen `NormalizedObservation`s. Ordinary inputs produce one, tombstones none, and explicit rich batch members one each. `projection` can select an exact batch-member JSON pointer. No observation combines raw occurrences. The command uses `verified_resolver(root, artifact)` to keep one verified artifact open and cache only the current parsed page/member; this avoids repeated archive hashing for each record. Parsed views are read-only to normalization.

The package `tenderwatch.normalization` contains `models.py` (frozen typed models), `common.py` (source-preserving value parsing), `placsp.py`, `tables.py`, and `publications.py` (adapters), plus `errors.py` and `validation.py`. Public controlled input errors derive from `NormalizationError`; `NormalizationInvariantError` is deliberately separate. Observation identity includes the raw occurrence, projection, schema version, and mapping version.

Supported mappings cover native/aggregated PLACSP Atom entries, Generalitat main and execution rows, and modern ordinary/batch/execution publication JSON. Legacy XML raises `UnsupportedNormalizationInput`. Reviewed code dictionaries are intentionally bounded (including EUR currency recognition); unknown codes produce Issues, not guessed categories. Comprehensive code lists, legacy mappings, additional contract-action families, PLACSP multi-project award grouping/effective dates, publisher-backed rich calendar interpretations, and document-size units remain deferred. Multi-project result groups are diagnosed rather than pooled; rich serialized business dates retain unresolved raw values rather than guessed legal instants. No entity resolution or reconciliation is performed inside normalization; those are separate downstream stages.

### Canonical model and deterministic MVP rules

`tenderwatch.canonical.canonicalize(observations)` is the small in-memory API. The command uses the same `ResolutionIndex` and `Reconciler` against disk-partitioned materialized observations for the bulk run. `canonical/models.py`, `canonical/resolution.py`, and `canonical/reconciliation.py` separate representation, identity, and fact reconciliation. `materialization.py` owns output publication and disk partitioning; `serialization.py` preserves typed normalized values on reload.

The canonical root is deliberately small:

```text
CanonicalObservation
  canonical_id
  normalized_observation_ids[]
  current_state
  conflicts[]
  resolution_provenance[]
```

`normalized_observation_ids` is the complete associated evidence set for this run, not a reconstructed legal-state timeline. Whole normalized observations are not embedded in the canonical root. `canonical_id` is a versioned digest of the component's qualified PSCP procedure UUID, or its deterministic PLACSP Atom-ID anchor when there is no UUID. It is deterministic for the same identity evidence; future changed merge/split evidence can change the grouping. It is not a permanent legal identifier or an incremental registry.

**Identity rules (`er.v1`):**

- Recognize only procedure-role `pscp_uuid` identifiers in `gencat:pscp` and correctly qualified PLACSP `atom_id` identifiers with the reviewed native/aggregated URI shapes. Placeholder/invalid identifiers and malformed UUIDs are excluded.
- Exact shared identifiers group observations. Explicit co-occurrence of qualified procedure identifiers connects aliases, including PLACSP-to-PSCP links and multiple PLACSP IDs for the same UUID.
- Finalize identity over the complete run before assigning groups. If a connected component contains more than one distinct PSCP procedure UUID, quarantine the whole component as `contradictory_procedure_identifiers`; processing order never selects a winner.
- An identified singleton still produces a canonical observation. Observations without a strong procedure identifier remain unresolved. Planning/batch-member subjects and observations carrying batch/member identity are not forced into procurement-procedure groups.
- No buyer-plus-number matching, row-suffix parsing, publication-parent inference, fuzzy matching, or matching by titles/amounts/dates/CPVs is implemented. Thus many execution rows intentionally remain unresolved even when a plausible buyer/number candidate exists elsewhere.
- Every accepted identity is recorded with its qualified value, rule name, and contributing observation IDs. This is evidence grouping, not independent-authority voting.

**Reconciliation rules (`reconcile.v1`):**

- Consolidate equivalent values and their evidence. Exact Decimal spellings such as `1.0` and `1.00` compare equally without rounding; recognized mapped categories can agree across source vocabularies. Original source variants stay available through normalized evidence.
- Select a sole valid value (`agreed_value` or `sole_valid_value`). Missing values contribute no deletion. Invalid/unmapped values remain candidates but do not override supported values; a fact with no usable candidate uses `no_valid_value`.
- Competing usable values in the same fact slot use `unresolved_conflict`, with no selected candidate. No timestamp, source preference, majority count, or input order breaks ties. This deliberately leaves some historical-versus-current alternatives unresolved rather than inferring legal chronology.
- Financial slots preserve scope, purpose, tax basis, currency and explicit VAT qualifiers. Unknown currency/VAT does not establish equivalence to a known qualifier. Deadlines are separated by role; statuses by dimension. Multi-valued identifiers, procedure numbers, classifications, locations and periods retain distinct supported assertions rather than treating every difference as an exclusive conflict.
- `record_subject`, unknown and lot scopes remain observation-qualified. They are not silently promoted to procedure scope or equated across observations.
- Lots, publications, outcomes, awards, actions, documents and source references remain separate `Occurrence(observation_id, normalized_path, value)` objects. Equal displayed numbers/amounts do not merge them. Nested normalized keys resolve only within their owning observation. No legal contract or global party registry is manufactured. These collections are evidence-backed occurrences, not a deduplicated present-day inventory; coverage claims remain attached to their source observations.

`current_state` reuses normalized value types. Reconciled fields contain small `ReconciledFact` wrappers: a fact ID and scope, candidate values with `EvidenceRef(observation_id, normalized_path)` links, a `selected_candidate_id` (null when unresolved), and the rule. In Python, `.value` returns the selected candidate's value; JSON represents the selection by its candidate ID to avoid duplicating it. These IDs are interpreted within their canonical object/fact. Conflicts reference these candidates; alternative values are not discarded. An equivalent candidate's stored source-shaped value is a deterministic representative, not a new source-priority decision.

Scope qualifiers and evidence links make uncertainty inspectable without introducing a generic assertion database. Buyer assertions are compared conservatively as reported Parties; partial or changed buyer descriptions may remain alternatives rather than being assembled into a guessed legal entity.

**Deferred:** Search / Query Interface, APIs/UI, fuzzy/ML matching, confidence scoring, exhaustive party/nested-entity deduplication, legal-contract and historical reconstruction, canonical revisions, temporal supersession inference, universal lifecycle derivation, database persistence, distributed execution, scheduling, and incremental ingestion. Existing normalization capability limits remain unchanged.

Run the focused new tests with:

```bash
.venv/bin/python -m pytest tests/test_canonical.py tests/test_canonical_workflow.py -q
```

They cover strong identity and alias bridges, contradictory components, non-matches, batches/planning, independent lot occurrences, equivalent/conflicting facts, missing/invalid values, evidence preservation, deterministic ordering, typed serialization, rerun isolation, and failure-safe publication. Existing normalization expectations and fixtures were not changed.

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

