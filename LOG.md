**# TenderWatch Project Log**

**## 2026-09-23: Data source investigation and empirical analysis**

**\*\*What:\*\*** Downloaded and analyzed PLACSP and Generalitat de Catalunya procurement data to understand their structure, update mechanisms, and overlap.

**\*\*Why:\*\*** To establish empirical foundations for the multi-source reconciliation pipeline before implementing application logic. Needed to validate assumptions about data quality, completeness, identifier stability, and cross-source linkage.

**\*\*How:\*\*** 

\- Downloaded PLACSP 2025 and available 2026 Atom feeds from both native-profile and aggregated-platform endpoints.

\- Retrieved all Generalitat main-table rows and execution-action rows with publication dates in the research window.

\- Extracted official PLACSP and PSCP documentation and specifications.

\- Profiled 1.6M PLACSP entries and 1.1M Generalitat rows; identified 20 representative case studies.

\- Compared source schemas, identifier schemes, publication mechanisms, and update patterns.

**\*\*Outputs:\*\***

\- \`research/docs/REPORT.md\`: Full investigation with findings, limitations, and proposed normalized model.

\- \`data/raw/\`: 214 validated raw files (6.24 GB) with acquisition metadata and checksums.

\- \`analysis/metrics.json\`, \`analysis/cases.json\`: Quantitative profiles and case catalogue.

\- \`data/samples/\`: 20 case-study evidence fragments with cross-source linkage examples.

**\*\*Key findings:\*\***

\- 98.25% of selected PLACSP aggregation IDs link explicitly to Generalitat procedure UUIDs.

\- Generalitat publication-batch UUIDs can encompass different contracts; batch UUID ≠ procedure identity.

\- Neither source guarantees complete event history; PLACSP may remove older entries.

\- Many apparent deadline conflicts are precision differences (seconds), not extensions.

\- PSCP endpoints may return legacy XML despite \`/json/\` URLs.

**---**

**## 2026-09-23: Repository reorganization for development**

**\*\*What:\*\*** Restructured the repository to separate application code, tests, research tools, and data artifacts into a conventional Python project layout.

**\*\*Why:\*\*** To establish a clean development baseline that preserves research evidence while enabling incremental application development without mixing exploratory and production code.

**\*\*How:\*\***

\- Created \`src/tender_collector/\` application package (empty, ready for development).

\- Moved existing research tests into \`tests/research/\` and added a smoke test in \`tests/\`.

\- Created \`tests/fixtures/\` for future local test fixtures.

\- Preserved \`research/scripts/\`, \`research/legacy/\`, and \`research/docs/\` for historical material.

\- Kept \`data/raw/\`, \`data/processed/\`, \`data/samples/\`, and \`analysis/\` at existing paths to preserve provenance references.

\- Added \`pyproject.toml\` with editable installation, pytest configuration, and research dependencies.

**\*\*Outputs:\*\***

\- \`pyproject.toml\`: Build configuration, package discovery, pytest settings.

\- \`tests/test_smoke.py\`: Minimal test verifying package import and metadata.

\- Updated \`README.md\` with development instructions.

**\*\*Verification:\*\*** All 10 tests pass; all 214 raw-file checksums verified; report links valid.

**---**

**## 2026-09-23: Project identity cleanup (TED → TenderWatch)**

**\*\*What:\*\*** Removed stale references to the previous project name and TED-based architecture. Updated active documentation and configuration to consistently identify TenderWatch with PLACSP and Generalitat de Catalunya as current sources.

**\*\*Why:\*\*** The project had transitioned from a TED-focused experiment to a multi-source platform, but documentation and metadata still contained old branding and implied TED as an active data source.

**\*\*How:\*\***

\- Renamed application package from \`tender_collector\` to \`tenderwatch\`.

\- Updated \`README.md\`, \`pyproject.toml\`, \`AGENTS.md\`, and \`PROJECT_CONTEXT.md\` to reflect current identity and sources.

\- Rewrote three hypothetical "future TED" examples in \`research/docs/REPORT.md\` as source-neutral language.

\- Created \`research/legacy/README.md\` to document the archived TED experiment and preserve historical API notes.

\- Removed obsolete editable package metadata and reinstalled with correct distribution name.

**\*\*Preserved intentionally:\*\***

\- \`research/legacy/ted.py\`: Archived experiment, explicitly marked as outside current scope.

\- TED identifiers in raw PLACSP XML, PSCP publication links, and official specifications: genuine source content, not claims about current ingestion.

\- Workspace directory and Git history: operational locations, not active branding.

**\*\*Outputs:\*\***

\- Updated \`README.md\`, \`pyproject.toml\`, \`AGENTS.md\`, \`PROJECT_CONTEXT.md\`, \`research/docs/REPORT.md\`.

\- New \`research/legacy/README.md\` with historical context.

\- Renamed \`src/tenderwatch/\` package directory.

**\*\*Verification:\*\*** All 10 tests pass; repository-wide searches confirm no stale active references; \`pip check\` and \`git diff --check\` pass.

**---**

**## 2026-09-23: Project documentation guidelines**

**\*\*What:\*\*** Added a "Project documentation" section to \`AGENTS.md\` establishing clear rules for maintaining \`PROJECT_CONTEXT.md\` and \`AGENTS.md\` as the project evolves.

**\*\*Why:\*\*** To prevent documentation drift and ensure that future changes are recorded consistently and at the appropriate level of abstraction (material architectural changes vs. temporary implementation details).

**\*\*How:\*\***

\- Defined when to update \`PROJECT_CONTEXT.md\` (material scope/architecture changes only).

\- Defined when to update \`AGENTS.md\` (stable repository-wide working rules, not one-off decisions).

\- Required that changes to either file be mentioned in task summaries.

**\*\*Outputs:\*\***

\- Updated \`AGENTS.md\` with new guidelines section.

\- Simplified REPORT.md reference in \`PROJECT_CONTEXT.md\` for clarity.

**\*\*Verification:\*\*** All 10 tests pass; commit successful.



**---**

**## 2026-09-23: Normalized schema design report**

**\*\*What:\*\*** Designed and documented the first version of a common normalized procurement schema that both PLACSP and Generalitat de Catalunya can map into without erasing important semantic differences.

**\*\*Why:\*\*** To establish a source-independent representation layer that preserves source scope, uncertainty, and traceability before implementing reconciliation, entity resolution, or canonical state logic. The normalized model must be implementation-ready but language-agnostic, and must reflect actual observed source semantics rather than hypothetical universal procurement concepts.

**\*\*How:\*\***

\- Reviewed all research evidence: \`REPORT.md\`, source documentation, semantic audit, representative case studies, and raw publication bodies.

\- Analyzed conceptual models of both sources: PLACSP as an Atom update feed with accumulated publication history; Generalitat as mixed-granularity rows (procedures, lots, contracts, batch members) plus separate execution-action records.

\- Identified false equivalences: expediente ≠ stable procedure ID; publication UUID ≠ procedure UUID; source update ≠ business event; RES ≠ awarded; missing value ≠ deletion.

\- Designed \`NormalizedObservation\` as a typed, source-attributed projection of exactly one raw source record about one procurement subject, with explicit scope, no cross-record merging, and retained source codes.

\- Specified all normalized fields with type, cardinality, semantics, source mappings, and edge cases.

\- Separated lifecycle dimensions: publication phase, process status, outcome, execution state, and source availability.

\- Distinguished monetary purposes: estimated value, tender budget, award amount, contract amount, modification delta, execution action amount.

\- Preserved temporal semantics: source update time, publication time, submission deadline, award decision time, formalization time, execution action time, planned publication time.

\- Modeled identifiers as namespaced values retaining scheme, issuer, role, raw value and scope.

\- Deferred canonical identities, reconciliation confidence, entity resolution, and field-level canonical provenance.

**\*\*Outputs:\*\***

\- \`research/docs/NORMALIZED_SCHEMA_DESIGN.md\`

**\*\*Key design decisions:\*\***

\- \`NormalizedObservation\` is a partial, single-input projection—not a canonical tender, reconciled state, or complete procedure snapshot.

\- Procedure, lot, batch-member and publication scope are explicit and preserved.

\- Outcomes are separate from awards; positive award facts require positive evidence.

\- Supplier allocations preserve positional and unresolved alignment; no guessing or equal splitting.

\- Lots are nested only when the source explicitly supports a lot context; no synthetic lot zero.

\- Documents are source references/metadata, not acquired binaries; URLs do not establish download.

\- Provenance preserves raw source record identity, dataset identity, acquisition identity, source record locator, mapping version, exact field/path locators, projection scope, and source record hash.

\- Source-specific raw codes are retained alongside normalized categories; crosswalks are versioned.

\- Unresolved/unknown values are represented explicitly rather than guessed or forced into \`other\`.

**\*\*Verification:\*\*** Report reviewed for all 16 required sections, consistent terminology, no accidental code/SQL, no unsupported source claims, no contradictions between field tables and final schema, valid Markdown formatting, and closed code fences.

**---**

**## 2026-09-23: Normalization test strategy**

**\*\*What:\*\*** Defined the test strategy for the \`RawSourceRecord -> NormalizedObservation\` mapping layer before implementing the normalizers.

**\*\*Why:\*\*** To establish expected behavior for valid, unusual, degraded, and invalid source records, and to distinguish recoverable source-data issues from fatal normalization errors and implementation bugs.

**\*\*How:\*\***

\* Reviewed the normalized schema, retained raw samples, and C01–C20 research cases.

\* Identified happy paths and real edge cases to use as regression fixtures.

\* Analyzed potential normalization failure modes and classified them as recoverable issues or fatal errors.

\* Defined a small public exception model and synthetic-fixture strategy for failure cases not present in the retained data.

\* Identified cross-source normalization invariants to test independently of individual fixtures.

**\*\*Outputs:\*\***

\* \`research/docs/NORMALIZATION_TESTS.md\`: Test plan covering happy paths, edge cases, recoverable failures, fatal failures, invariants, fixtures, and expected exception behavior.

**\*\*Next:\*\*** Implement the normalization test suite from this specification before implementing the source-specific normalization mappers.

---

## 2026-09-23: Implementation plan changed to retained-data MVP

**What:** Changed the near-term implementation plan from building an operational ingestion pipeline to building a single-run MVP over the already downloaded and validated research datasets.

**Why:** The immediate priority is to prove the core data transformations end to end with the available evidence and limited implementation time. Continuous acquisition, change detection, scheduling, and other operational pipeline concerns can be added later if needed.

**New implementation flow:**

```text
Stored Downloaded Data
    -> Read Individual Source Records
    -> RawSourceRecord
    -> NormalizedObservation
    -> Entity Resolution / Reconciliation
    -> Canonical Representations
    -> Query Interface
```

**Immediate development sequence:**

- Read the retained PLACSP and Generalitat artifacts directly from disk.
- Iterate the individual source records represented by those artifacts.
- Convert each source occurrence into an immutable `RawSourceRecord` while preserving exact source content/provenance.
- Use the existing normalization test strategy to implement tests for `RawSourceRecord -> NormalizedObservation` before implementing the source-specific normalizers.
- Implement normalization without cross-record joins or canonical-state logic.
- Add reconciliation/canonical construction only after normalized observations are working correctly.
- Add a query interface over canonical representations after reconciliation is available.

**Deferred:**

- downloading the latest source data as part of the application;
- periodic execution/scheduling;
- incremental change detection;
- durable ingestion checkpoints;
- workers/queues;
- continuous update processing;
- production pipeline orchestration.

**Architectural implication:** The code should still keep reading, raw construction, normalization, reconciliation, and querying as separate responsibilities so the same transformation logic can later be reused if the project evolves into a continuous pipeline.

**Documentation updated:**

- `PROJECT_CONTEXT.md`: current scope now explicitly describes the retained-data, single-execution MVP and the implementation sequence through canonical querying.
- `AGENTS.md`: repository-wide development rules now state that the current implementation reads existing local acquisitions and should not introduce pipeline infrastructure unless explicitly requested.
- `LOG.md`: this entry records the change of plans and supersedes the informal pipeline notes previously appended to the log.

---

## 2026-09-23: Retained-data readers and immutable raw source records

**What:** Implemented the first two processing boundaries:

```text
Stored artifact on disk
    -> source-specific reader
    -> individual SourceRecord
    -> to_raw(source_record)
    -> immutable RawSourceRecord
```

No normalization, reconciliation, canonical representations, query functionality, or new downloading behavior was implemented.

**Implementation:**

- `src/tenderwatch/raw.py`: frozen raw/source models, explicit record kinds, structured artifact/record locators, and deterministic occurrence IDs.
- `src/tenderwatch/sources/`: local artifact access and checksum verification, JSON/XML parsing, PLACSP and Generalitat readers, manifest-based discovery, deliberate error types, and the traversal entry point.
- PLACSP readers visit every retained Atom/XML ZIP member, including members outside the advertised navigation chain. Atom entries and tombstones remain distinct.
- Generalitat main-table and execution-table rows remain independent. Rich JSON and legacy XML publication bodies are supported; a batch body remains one raw occurrence rather than being split or joined with table rows.
- Original content is retained through checksum-bound references to the complete artifact/member and an exact record locator. XML namespace context, original JSON values, unknown fields, acquisition URLs, captured timestamps, and metadata remain recoverable without semantic conversion.

### How to execute

Use the existing virtual environment and run from the repository root:

```bash
cd /home/jose/PLACSP_TED_tender_collector
.venv/bin/python -m tenderwatch.sources --root .
```

For a single source, or to display the available options:

```bash
.venv/bin/python -m tenderwatch.sources --root . --source placsp
.venv/bin/python -m tenderwatch.sources --root . --source gencat
.venv/bin/python -m tenderwatch.sources --help
```

`--root` points to the repository/snapshot root containing `data/raw/`, not to `data/raw/` itself. No network access or additional runtime dependencies are required. The retained acquisitions must already exist locally.

To save the summary and progress separately, choose new output filenames:

```bash
.venv/bin/python -m tenderwatch.sources --root . \
  > raw-record-counts.tsv 2> raw-record-progress.log
```

The summary contains a tab-separated header and count rows followed by a human-readable total line; it is not a raw-record export or a strict TSV-only file. Shell redirection overwrites existing output files with those names.

### Inputs

Discovery reads `data/raw/download_manifest.jsonl` and processes supported successful acquisitions:

- **PLACSP:** the four original 2025/2026 ZIP archives under `data/raw/placsp/aggregated/` and `data/raw/placsp/native/`, plus standalone Atom probes under `data/raw/placsp/probes/`.
- **Generalitat main table:** JSON row arrays under `data/raw/gencat/ybgg-dgi6/pages/`, the dataset probe, and separately acquired main-table probes under `data/raw/gencat/probes/`.
- **Generalitat execution table:** JSON row arrays under `data/raw/gencat/8idu-wkjv/pages/` and its dataset probe.
- **Rich Generalitat publications:** retained bodies under `data/raw/gencat/phases/`, `phase_probes/`, and `legacy_probes/`. Actual body content determines JSON versus XML; JSON-named endpoints can contain XML.
- **Context:** manifest acquisition lines and annotations, plus retained table metadata-before/after and count-before/after artifacts. These are provenance/context inputs, not additional procurement rows.

Failed requests, unfinished `.partial` files, aggregate audit queries, documentation, research SQLite indexes, and derived sample/analysis copies are not emitted as source records. Separately acquired probes are included as independent occurrences. No date/geography filtering, deduplication, or source-record joins are performed.

### Outputs

**Command output:**

- Progress messages identifying each input artifact go to **stderr**.
- Counts by `source`, `dataset`, and `record_kind`, followed by the total number of raw occurrences and artifacts, go to **stdout**.
- Checksums are verified during traversal. Missing/changed files, malformed supported inputs, and invalid locators produce controlled errors; traversal failures exit nonzero and do not present incomplete counts as success.
- The command constructs raw objects incrementally but does **not** persist them, export normalized data, create a database, or modify input acquisitions. Output files are only created if the caller explicitly redirects stdout/stderr.

**Programmatic output:** reader iterators yield individual `SourceRecord` objects; `to_raw()` returns an immutable `RawSourceRecord` for each occurrence:

```python
from pathlib import Path

from tenderwatch.raw import to_raw
from tenderwatch.sources.retained import discover_inputs

root = Path('.')
for retained in discover_inputs(root):
    for source_record in retained.read(root):
        raw_record = to_raw(source_record)
```

Source-specific interfaces are `read_placsp`, `read_gencat_main`, `read_gencat_execution`, and `read_gencat_publication`. Recovery helpers include `read_document` for exact containing-document bytes, `load_record` for a fresh parsed record view, and `read_manifest_line` for verified acquisition metadata. Raw records reference retained content rather than embedding a cleaned procurement object, so the referenced files must remain available and unchanged.

### Verified results

The complete local traversal succeeded with **2,850,341 raw occurrences across 195 input artifacts**, with checksums verified:

| Record kind | Count |
|---|---:|
| `placsp_atom_entry` (both collections) | 1,625,075 |
| `placsp_tombstone` (both collections) | 86,253 |
| `gencat_main_row` | 1,070,978 |
| `gencat_execution_row` | 67,965 |
| `gencat_publication_json` | 66 |
| `gencat_publication_xml` | 4 |

Counts include independent probe acquisitions and all archived occurrences, so they are not equivalent to the research's filtered cohorts or bulk-only row totals.

**Tests and verification:**

```bash
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src tests research/scripts
.venv/bin/python research/scripts/verify_artifacts.py
.venv/bin/python research/scripts/verify_parsers.py
.venv/bin/python research/scripts/verify_report.py
```

- All **52 tests passed**, including existing research regressions and optional local-evidence checks. The suite without the optional retained-evidence test module passed all **43 tests** and requires no research snapshot.
- Compilation and existing research verification scripts passed.
- Research artifact verification checked all **214 acquired files** and found no missing files, checksum mismatches, or sample-reference errors. This broader acquisition total includes documentation and metadata that are not among the 195 source-record input artifacts.
- Added three test modules and six small retained-evidence fixtures/excerpts. Raw acquisitions and research scripts were not changed.

**Documentation:** Added `docs/RAW_SOURCE_RECORDS.md` with the full module/API contract, locator rules, supported formats, fixture provenance, and limitations. Updated `README.md` and the implementation status in `PROJECT_CONTEXT.md`; no implementation-task changes were made to `AGENTS.md`.

**Next:** Implement and test `RawSourceRecord -> NormalizedObservation` separately. Preserve the existing meaning of `observed_at` as captured download completion, not an invented precise receipt timestamp. Bulk normalization should reuse verified page/member parsing rather than repeatedly reopen and hash large containing artifacts. Identifier roles, batch projections, legacy XML semantic mappings, and all procurement normalization decisions remain deferred.

---

## 2026-09-24: Source-specific normalization and disposable inspection output

**What:** Implemented the next processing boundary and connected it to the existing single-run workflow:

```text
Stored artifact on disk
    -> individual SourceRecord
    -> immutable RawSourceRecord
    -> normalize(raw, resolve=..., projection=...)
    -> tuple of immutable NormalizedObservation objects
    -> disposable inspection JSONL
```

Each observation describes exactly one raw occurrence/selection. Normalization does not join records, fetch links, consult research indexes, resolve entities, reconcile observations, construct canonical state, or provide queries.

**Important command change:** `python -m tenderwatch.sources` now normalizes by default and writes inspection output. The preceding entry's count-only behavior is still available with `--raw-only`; its historical statement that the default command creates no output files no longer applies.

### Implementation and public interfaces

- Added `src/tenderwatch/normalization/`: `models.py` defines frozen typed observations and nested values; `common.py` contains shared value parsing; `placsp.py`, `tables.py`, and `publications.py` implement the source-specific adapters; `errors.py` and `validation.py` define controlled failures and output invariant checks.
- Public interface: `normalize(raw, *, resolve, projection=None) -> tuple[NormalizedObservation, ...]`, plus `validate_observation`, `NormalizedObservation`, `SCHEMA_VERSION`, `MAPPING_VERSION`, and the normalization exception classes.
- Normalized identity is deterministic for the raw occurrence, projection locator, and schema/mapping versions. Local keys and references remain observation-local, not canonical IDs.
- Money uses exact `Decimal` values and distinguishes missing, explicit empty/null, invalid, and valid zero values. Source spelling, positional supplier tokens, financial scope, tax basis, and temporal roles remain distinct. No currency, timezone, missing amount, or legal state is guessed.
- Recoverable source problems become path-qualified `Issue`s. Fatal input/selection failures use `InvalidNormalizationInput` or `UnsupportedNormalizationInput`, both derived from `NormalizationError`. Generated-output defects raise the separate `NormalizationInvariantError`; unexpected programming/system errors are not converted into successful empty results.
- Extended `src/tenderwatch/sources/artifacts.py` with `verified_resolver(root, artifact)`: a context-managed resolver restricted to one verified artifact, caching the current parsed page/member and checking each locator/document checksum. This avoids reopening and hashing an archive for every entry. Parsed views are not mutated by normalization.
- Added `src/tenderwatch/inspection.py` for serialization and compact previews, keeping file output and stdout behavior outside the normalization functions. Extended `src/tenderwatch/sources/__main__.py` to call normalization for every processed raw occurrence and stream all resulting observations to disk.

### Supported raw kinds

| Raw record kind | Normalization behavior |
|---|---|
| `placsp_atom_entry` | One observation for a native or aggregated entry, with supported nested lots, publications, outcomes, awards, and documents. |
| `placsp_tombstone` | Empty tuple; no invented procurement cancellation. |
| `gencat_main_row` | One independent procedure, lot, planning, or batch-member projection according to the row evidence. |
| `gencat_execution_row` | One independent execution-action projection, without a main-table join. |
| `gencat_publication_json` | Ordinary/execution body projection, or one observation per explicitly selected batch member. |
| `gencat_publication_xml` | Raw-readable but normalization explicitly raises `UnsupportedNormalizationInput(reason='unsupported_structure_or_format')`. |

Ordinary observations use projection locator `$`. Rich batch members use `/publicacio/dadesPublicacio/contractesAgregada/{index}`. Whole-batch enumeration is atomic on fatal member-selection/shape failures; a valid sibling can still be normalized separately by its explicit pointer.

### How to execute

From the repository root, using the existing virtual environment:

```bash
cd /home/jose/PLACSP_TED_tender_collector
.venv/bin/python -m tenderwatch.sources --root .
```

The command above processes all discovered inputs and can produce substantial output. For bounded inspection, source selection, or the previous raw-only traversal:

```bash
.venv/bin/python -m tenderwatch.sources --root . --limit 100
.venv/bin/python -m tenderwatch.sources --root . --source gencat --limit 100
.venv/bin/python -m tenderwatch.sources --root . --artifact 'data/raw/gencat/phases/*'
.venv/bin/python -m tenderwatch.sources --root . --artifact 'data/raw/placsp/probes/native-head.atom' --limit 100
.venv/bin/python -m tenderwatch.sources --root . --raw-only
.venv/bin/python -m tenderwatch.sources --help
```

- `--root` is the repository/snapshot root containing `data/raw/`.
- `--limit` counts raw occurrences, not observations, and explicitly marks the output as limited.
- `--source placsp|gencat` filters sources; repeat `--artifact` to select multiple retained-path globs.
- `--output-parent /existing/path` places a new uniquely named inspection directory under that existing parent. Existing outputs are never overwritten.
- No new runtime dependency or network access is required.

### Inputs and outputs

**Inputs:** the existing successful acquisitions in `data/raw/download_manifest.jsonl`, including both PLACSP collections and their probes, Generalitat main/execution table pages and probes, modern rich publication JSON, and retained legacy XML. Artifact checksums and record locators remain the raw-access boundary. No acquisition, fixture, research index, or sample was rewritten to make normalization work.

**Outputs:** each normalizing run creates a fresh `tenderwatch-inspection-*` directory under the system temporary directory unless `--output-parent` is supplied. Its exact location is printed. The directory is explicitly non-production and safe to delete:

- `observations.jsonl`: one complete normalized observation per line, including raw identity, projection, versions, source paths, scoped assertions, and Issues. Decimal values are serialized as exact strings; dates/times use ISO strings and offsets use readable duration strings. This is a debugging representation, not an adopted production storage schema.
- `failures.jsonl`: controlled normalization failures with raw occurrence context, exception type, reason, and projection locator. Unsupported legacy XML is recorded here rather than silently discarded. Other raw occurrences continue processing.
- `summary.json`: raw/observation/artifact counts, source-kind counts, diagnostic/failure totals, filters, and completion status: `complete`, `complete_with_unsupported`, `limited`, `failed`, or `interrupted`.

Progress and output-directory announcements go to stderr. Stdout shows the first three processed raw occurrences with compact normalized summaries, then final counts. Tombstones show zero observations; unsupported examples show their failure reason. Huge raw payloads and tokenized export URLs are not dumped to stdout. Observations are streamed to disk rather than accumulated for the entire snapshot in memory.

Known unsupported inputs are counted and reported. Invalid normalization inputs cause a nonzero exit after traversal; unexpected programmer/invariant errors propagate and leave an interrupted summary. `--raw-only` creates no inspection directory.

### Retained-data inspection performed

The combined selected-evidence run used:

```bash
.venv/bin/python -m tenderwatch.sources --root . \
  --artifact 'data/raw/gencat/*/probe.json' \
  --artifact 'data/raw/gencat/phases/*' \
  --artifact 'data/raw/gencat/phase_probes/*' \
  --artifact 'data/raw/gencat/legacy_probes/*' \
  --artifact 'data/raw/placsp/probes/*.atom'
```

It verified and processed **623 raw occurrences across 74 artifacts**, yielding **575 normalized observations**. There were **four controlled unsupported-input failures**, all retained legacy XML bodies, and no other controlled input failures. The run status was `complete_with_unsupported`.

| Selected raw input | Count |
|---|---:|
| Generalitat execution probe rows | 5 |
| Generalitat main probe rows | 5 |
| Modern rich publication JSON bodies | 66 |
| Legacy publication XML bodies | 4 |
| Aggregated PLACSP Atom entries | 359 |
| Aggregated PLACSP tombstones | 49 |
| Native PLACSP Atom entries | 135 |

The six-member batch accounts for five additional observations; tombstones and unsupported legacy bodies produce none. The modern rich bodies alone produced **71 observations**.

The combined output was written to **`/tmp/tenderwatch-inspection-7ehvit4k/`** (approximately 12 MB of observations), with all three files described above. This temporary path may be removed by system cleanup; rerunning the command creates a new directory. Separate bounded runs also exercised 100 rows from each Generalitat table and both PLACSP feed families.

**Scope of this verification:** this was a selected-evidence normalization run, not a new full traversal/normalization of all 2,850,341 raw occurrences reported in the previous entry. The unfiltered command is available, but a complete multi-million-record normalized export was not generated in this task.

### Tests and verification

The original test-first assertions, expected outputs, fixtures, and harness were left unchanged. No placeholder test wiring needed replacement: the existing API fixture automatically imports the real module, so absent-implementation xfails are inactive. Added `tests/normalization/test_implementation_edges.py` and `tests/test_normalization_workflow.py` for implementation-edge cases, resolver caching/integrity, lossless inspection serialization, CLI output, limits, and failure propagation.

```bash
.venv/bin/python -m pytest -q -r fE
.venv/bin/python -m pytest tests/normalization --runxfail -q -r fE
.venv/bin/python -m pytest tests/normalization/test_fixtures.py --audit-normalization-evidence -q
.venv/bin/python -m compileall -q src tests research/scripts
git diff --check
```

Verified implementation results:

- Complete suite: **298 passed, 1 skipped**, no xfails or failing tests.
- Normalization suite with `--runxfail`: **239 passed, 1 skipped**.
- Explicit retained-evidence fixture audit: **54 passed**.
- The ordinary skipped normalization test is the opt-in retained-evidence audit.
- Compilation and diff checks passed. The existing original normalization tests/fixtures had no diff.

### Remaining limitations and documentation

Legacy XML mappings, comprehensive source code dictionaries, additional action families, PLACSP multi-project award grouping/effective dates, publisher-backed rich business-date timezone rules, and document-size units remain deferred. Code and currency recognition is deliberately bounded; unreviewed values remain unmapped with Issues rather than being guessed. Unreviewed multi-project result groups are diagnosed rather than pooled into a misleading award total. Rich serialized business dates remain raw/unresolved where their legal calendar interpretation is not established.

Updated `README.md`, `docs/RAW_SOURCE_RECORDS.md`, the implementation-status note in `research/docs/NORMALIZATION_TESTS.md`, and `PROJECT_CONTEXT.md` to describe the implemented boundary and workflow. `AGENTS.md`, original contract tests/fixtures, raw acquisitions, and research scripts were unchanged. This entry records the completed normalization increment; reconciliation, canonical representations, and querying remain separate future work.
