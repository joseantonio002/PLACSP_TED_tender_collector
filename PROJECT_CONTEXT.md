# TenderWatch

TenderWatch is a public procurement data platform for discovering and exploring tenders from multiple public sources.

## Problem

Public procurement opportunities are distributed across different platforms, with different schemas, identifiers, update mechanisms, and representations of the same underlying procurement procedure.

This makes it difficult for companies to:

* search procurement opportunities consistently;
* understand the current state of a tender;
* combine information coming from multiple public sources;
* inspect how a tender has evolved over time.

## Product

TenderWatch periodically collects tender data from multiple public procurement sources and reconciles it into a canonical representation.

The initial data sources are:

* PLACSP — Plataforma de Contratación del Sector Público
* Generalitat de Catalunya public procurement data

Users will be able to search the current canonical state of tenders using filters such as:

* free-text search over title and content;
* CPV codes;
* procurement procedure type;
* relevant dates;
* other procurement attributes as the product evolves.

When a tender is selected, TenderWatch should expose its canonical information while preserving traceability to the original source data and documents.

## Core data problem

The central engineering problem is not simply downloading tender data.

Different sources may:

* represent the same procurement procedure differently;
* publish overlapping information;
* update information at different times;
* use different identifiers and schemas;
* contain complementary or conflicting information.

TenderWatch therefore needs to transform source-specific data into a common representation and reconcile observations from different sources into a trustworthy canonical state.

At a high level:

```text
Public Sources
      │
      ▼
   Extract
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
Canonical Tender State
      │
      ▼
Search / Exploration
```

The system should preserve the historical canonical states of a procurement procedure rather than only keeping its latest state.

## Current scope

The initial project focuses on procurement data relevant to Catalunya / Barcelona using PLACSP and Generalitat de Catalunya as sources.

The priority is to build a reliable multi-source data pipeline and canonical tender model before expanding product functionality or adding more procurement sources.

## Current status

The project is currently transitioning from research to implementation.

Research has already been conducted on:

* how PLACSP data is distributed and structured;
* how Generalitat de Catalunya procurement data is distributed and structured;
* differences between both sources;
* potential normalization strategies;
* potential entity-resolution and reconciliation strategies.

`REPORT.md` and the supporting research artifacts contain the detailed findings.

No production architecture should be considered final solely because it appears in the research material. Implementation decisions should be introduced incrementally and validated with tests and real source data.
