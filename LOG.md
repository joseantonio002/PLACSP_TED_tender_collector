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
