# TenderWatch Project Log

## 2026-09-23: Data source investigation and empirical analysis

**What:** Downloaded and analyzed PLACSP and Generalitat de Catalunya procurement data to understand their structure, update mechanisms, and overlap.

**Why:** To establish empirical foundations for the multi-source reconciliation pipeline before implementing application logic. Needed to validate assumptions about data quality, completeness, identifier stability, and cross-source linkage.

**How:** 
- Downloaded PLACSP 2025 and available 2026 Atom feeds from both native-profile and aggregated-platform endpoints.
- Retrieved all Generalitat main-table rows and execution-action rows with publication dates in the research window.
- Extracted official PLACSP and PSCP documentation and specifications.
- Profiled 1.6M PLACSP entries and 1.1M Generalitat rows; identified 20 representative case studies.
- Compared source schemas, identifier schemes, publication mechanisms, and update patterns.

**Outputs:**
- `research/docs/REPORT.md`: Full investigation with findings, limitations, and proposed normalized model.
- `data/raw/`: 214 validated raw files (6.24 GB) with acquisition metadata and checksums.
- `analysis/metrics.json`, `analysis/cases.json`: Quantitative profiles and case catalogue.
- `data/samples/`: 20 case-study evidence fragments with cross-source linkage examples.

**Key findings:**
- 98.25% of selected PLACSP aggregation IDs link explicitly to Generalitat procedure UUIDs.
- Generalitat publication-batch UUIDs can encompass different contracts; batch UUID ≠ procedure identity.
- Neither source guarantees complete event history; PLACSP may remove older entries.
- Many apparent deadline conflicts are precision differences (seconds), not extensions.
- PSCP endpoints may return legacy XML despite `/json/` URLs.

---

## 2026-09-23: Repository reorganization for development

**What:** Restructured the repository to separate application code, tests, research tools, and data artifacts into a conventional Python project layout.

**Why:** To establish a clean development baseline that preserves research evidence while enabling incremental application development without mixing exploratory and production code.

**How:**
- Created `src/tender_collector/` application package (empty, ready for development).
- Moved existing research tests into `tests/research/` and added a smoke test in `tests/`.
- Created `tests/fixtures/` for future local test fixtures.
- Preserved `research/scripts/`, `research/legacy/`, and `research/docs/` for historical material.
- Kept `data/raw/`, `data/processed/`, `data/samples/`, and `analysis/` at existing paths to preserve provenance references.
- Added `pyproject.toml` with editable installation, pytest configuration, and research dependencies.

**Outputs:**
- `pyproject.toml`: Build configuration, package discovery, pytest settings.
- `tests/test_smoke.py`: Minimal test verifying package import and metadata.
- Updated `README.md` with development instructions.

**Verification:** All 10 tests pass; all 214 raw-file checksums verified; report links valid.

---

## 2026-09-23: Project identity cleanup (TED → TenderWatch)

**What:** Removed stale references to the previous project name and TED-based architecture. Updated active documentation and configuration to consistently identify TenderWatch with PLACSP and Generalitat de Catalunya as current sources.

**Why:** The project had transitioned from a TED-focused experiment to a multi-source platform, but documentation and metadata still contained old branding and implied TED as an active data source.

**How:**
- Renamed application package from `tender_collector` to `tenderwatch`.
- Updated `README.md`, `pyproject.toml`, `AGENTS.md`, and `PROJECT_CONTEXT.md` to reflect current identity and sources.
- Rewrote three hypothetical "future TED" examples in `research/docs/REPORT.md` as source-neutral language.
- Created `research/legacy/README.md` to document the archived TED experiment and preserve historical API notes.
- Removed obsolete editable package metadata and reinstalled with correct distribution name.

**Preserved intentionally:**
- `research/legacy/ted.py`: Archived experiment, explicitly marked as outside current scope.
- TED identifiers in raw PLACSP XML, PSCP publication links, and official specifications: genuine source content, not claims about current ingestion.
- Workspace directory and Git history: operational locations, not active branding.

**Outputs:**
- Updated `README.md`, `pyproject.toml`, `AGENTS.md`, `PROJECT_CONTEXT.md`, `research/docs/REPORT.md`.
- New `research/legacy/README.md` with historical context.
- Renamed `src/tenderwatch/` package directory.

**Verification:** All 10 tests pass; repository-wide searches confirm no stale active references; `pip check` and `git diff --check` pass.

---

## 2026-09-23: Project documentation guidelines

**What:** Added a "Project documentation" section to `AGENTS.md` establishing clear rules for maintaining `PROJECT_CONTEXT.md` and `AGENTS.md` as the project evolves.

**Why:** To prevent documentation drift and ensure that future changes are recorded consistently and at the appropriate level of abstraction (material architectural changes vs. temporary implementation details).

**How:**
- Defined when to update `PROJECT_CONTEXT.md` (material scope/architecture changes only).
- Defined when to update `AGENTS.md` (stable repository-wide working rules, not one-off decisions).
- Required that changes to either file be mentioned in task summaries.

**Outputs:**
- Updated `AGENTS.md` with new guidelines section.
- Simplified REPORT.md reference in `PROJECT_CONTEXT.md` for clarity.

**Verification:** All 10 tests pass; commit successful.
