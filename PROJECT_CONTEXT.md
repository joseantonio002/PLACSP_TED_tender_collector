# TenderWatch

TenderWatch is a public procurement data platform for discovering and exploring tenders from multiple public sources.

## Problem

Public procurement opportunities are distributed across different platforms, with different schemas, identifiers, update mechanisms, and representations of the same underlying procurement procedure.

This makes it difficult for companies to:

- search procurement opportunities consistently;
- understand the current state of a tender;
- combine information coming from multiple public sources;
- inspect how a tender has evolved over time.

## Product

TenderWatch transforms procurement data from multiple public sources into a reconciled canonical representation that can be searched and explored consistently.

The initial data sources are:

- PLACSP — Plataforma de Contratación del Sector Público
- Generalitat de Catalunya public procurement data

Users should be able to search the current canonical state of tenders using filters such as:

- free-text search over title and content;
- CPV codes;
- procurement procedure type;
- relevant dates;
- other procurement attributes as the product evolves.

When a tender is selected, TenderWatch should expose its canonical information while preserving traceability to the original source data and documents.

## Core data problem

The central engineering problem is not simply reading procurement data.

Different sources may:

- represent the same procurement procedure differently;
- publish overlapping information;
- update information at different times;
- use different identifiers and schemas;
- contain complementary or conflicting information.

TenderWatch therefore needs to transform source-specific data into a common representation and reconcile observations from different sources into a trustworthy canonical state.

The current implementation path is:

```text
Stored Downloaded Data
        │
        ▼
Read Source Records
        │
        ▼
Raw Source Records
        │
        ▼
Normalize
        │
        ▼
Normalized Observations
        │
        ▼
Entity Resolution
        │
        ▼
Reconciliation
        │
        ▼
Canonical Representations
        │
        ▼
Search / Query Interface
```

The system should preserve historical canonical states of a procurement procedure rather than only keeping its latest state, where the available source evidence supports doing so.

## Current scope

The initial project focuses on procurement data relevant to Catalunya / Barcelona using PLACSP and Generalitat de Catalunya as sources.

The current implementation is an MVP that processes the already downloaded and validated research datasets from disk in a single execution. The immediate priority is to prove the complete transformation path from retained source data to raw records, normalized observations, reconciled canonical representations, and a usable query interface.

Continuous acquisition, incremental change detection, scheduling, and production pipeline infrastructure are intentionally deferred until the core transformations are working correctly on the retained data.

## Current status

Retained PLACSP and Generalitat artifacts are read into independent source records and immutable `RawSourceRecord`s. Original content remains recoverable through checksum-bound artifact references and exact record locators, with captured acquisition lineage where available.

The next boundary, `RawSourceRecord -> NormalizedObservation`, is implemented with a common dispatcher, immutable typed models, source-specific adapters, explicit scopes, Issues, and controlled input failures. Each observation derives from one raw occurrence/selection; no records are joined. Supported mappings cover PLACSP Atom entries, Generalitat main/execution rows, and modern rich JSON publications, including batch-member projections. Tombstones produce no procurement observations. Legacy XML remains raw-readable but explicitly unsupported for normalization. Reviewed mapping coverage is bounded as documented in README and the normalization test contract.

The single-run command now streams normalized observations into disposable inspection JSONL and prints three compact examples; this is not production persistence. `--raw-only` retains the raw count-only workflow. Reconciliation, canonical representations, and queries remain unimplemented.

The raw contract is documented in `docs/RAW_SOURCE_RECORDS.md`; README describes the normalization API, inspection output, and execution commands.

Research has already been conducted on:

- how PLACSP data is distributed and structured;
- how Generalitat de Catalunya procurement data is distributed and structured;
- differences between both sources;
- the common `NormalizedObservation` model;
- potential entity-resolution and reconciliation strategies;
- normalization test strategy, including happy paths, edge cases, degraded inputs, fatal failures, and invariants.

`research/docs/REPORT.md`, `research/docs/NORMALIZED_SCHEMA_DESIGN.md`, `research/docs/NORMALIZATION_TESTS.md`, and the supporting research artifacts contain the detailed findings.

The next implementation stages are:

1. extend normalization coverage only after reviewing the documented remaining mapping gates;
2. implement entity resolution and reconciliation;
3. construct canonical representations;
4. expose a query/search interface over those canonical representations.

No production architecture should be considered final solely because it appears in the research material. Implementation decisions should be introduced incrementally and validated with tests and real retained source data.
