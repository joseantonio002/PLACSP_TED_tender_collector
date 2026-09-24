# Retained source records and raw occurrences

This document describes the raw ingestion boundaries:

```text
retained artifact -> source-specific reader -> SourceRecord -> to_raw -> RawSourceRecord
```

These modules do not perform normalization or semantic selection. Separate `tenderwatch.normalization` and `tenderwatch.canonical` packages implement the downstream normalization, entity-resolution, and reconciliation boundaries; see the [single-run workflow](../README.md#run-retained-data-through-canonical-observations). Database persistence, new acquisition infrastructure, and querying remain unimplemented. The readers do not select a date range or geography, join rows, or discard occurrences with repeated source IDs. This follows the raw relationship contract in [the normalization design](../research/docs/NORMALIZED_SCHEMA_DESIGN.md), §§5.1 and 6.10, without adopting its proposed semantic mappings.

## Modules and public interfaces

| Module | Responsibility |
|---|---|
| `tenderwatch.raw` | Frozen, slotted value types: `Artifact`, `Acquisition`, `ManifestLine`, `RecordLocator`, `ContentReference`, `SourceField`, `SourceRecord`, `RawSourceRecord`, `RecordKind`; pure `to_raw(record)` factory. |
| `tenderwatch.sources.artifacts` | Local file access, SHA-256 verification, ZIP access, `identify_artifact`, `read_document`, `load_record`, `read_manifest_line`. |
| `tenderwatch.sources.formats` | JSON and XML parsing, without procurement field conversion. |
| `tenderwatch.sources.placsp` | `read_placsp(root, artifact, *, dataset)` yields individual source records from every retained Atom/XML ZIP member or a standalone Atom feed. |
| `tenderwatch.sources.gencat` | `read_gencat_main(root, artifact)`, `read_gencat_execution(root, artifact)`, and `read_gencat_publication(root, artifact)` yield source records. Table readers optionally accept `context_artifacts`. |
| `tenderwatch.sources.retained` | `discover_inputs(root)` reads the acquisition ledger and yields `RetainedInput` descriptors. `RetainedInput.read(root)` verifies contextual artifacts and dispatches to a reader. |
| `tenderwatch.sources.errors` | Raw-layer I/O, integrity, format, and locator exceptions. |
| `tenderwatch.sources.__main__` | Local traversal/counting command. |

`root` is a `pathlib.Path` identifying the repository/snapshot root, not `data/raw` itself. Artifact paths are relative to that root. Standalone callers can instead choose a smaller root and supply paths relative to it. Paths escaping the root are rejected; archive members are read in place, never extracted onto disk.

```python
from pathlib import Path

from tenderwatch.raw import to_raw
from tenderwatch.sources.retained import discover_inputs

root = Path('.')
for retained in discover_inputs(root):
    for source_record in retained.read(root):
        raw_record = to_raw(source_record)
```

For a single artifact without acquisition metadata:

```python
from tenderwatch.sources.artifacts import identify_artifact, load_record, read_document
from tenderwatch.sources.gencat import read_gencat_execution

artifact = identify_artifact(root, 'data/raw/gencat/8idu-wkjv/pages/000000000.json')
for source_record in read_gencat_execution(root, artifact):
    raw_record = to_raw(source_record)
```

Prefer manifest discovery for real snapshot processing: `identify_artifact` computes and optionally checks a digest, but does not invent or automatically locate acquisition lineage. Its optional `expected_sha256`, `expected_size`, and `acquisition` arguments support explicit callers. Reading verifies the artifact again before yielding its records.

## Supported inputs and kinds

| `record_kind` | `source` / `dataset` | Unit |
|---|---|---|
| `placsp_atom_entry` | `placsp` / `aggregated` or `native` | One immediate Atom `entry` child of a feed. |
| `placsp_tombstone` | Same | One immediate Atom-tombstones `deleted-entry` child; independent of procurement state. |
| `gencat_main_row` | `gencat` / `ybgg-dgi6` | One object in a retained SODA JSON array. |
| `gencat_execution_row` | `gencat` / `8idu-wkjv` | One execution row; no dependency on the main table. |
| `gencat_publication_json` | `gencat` / `pscp-publications` | One complete modern JSON object with a `publicacio` object. |
| `gencat_publication_xml` | Same | One complete legacy XML `Notice` document. |

Modern ordinary, execution, and batch publication bodies share the JSON-body kind. A body containing `contractesAgregada` stays **one** raw occurrence. Its future member selections are normalization projections, not additional raw records. Table rows are not classified as procedure/lot/batch-member here. XML versus JSON is an actual representation distinction needed by later parsers, not a distinction based on storage directory.

Publication format detection examines the retained content (UTF-8 BOM allowed), not the extension, endpoint name, or HTTP content type. The four retained legacy `.bin` bodies are XML despite their JSON-named endpoints and reported JSON content type.

### Discovery scope

Discovery uses successful (`validated: true`) entries in `data/raw/download_manifest.jsonl`, in deterministic path/manifest-line order. It recognizes the two retained PLACSP collections from their recorded source URLs, full-row SODA requests to the two researched datasets, and the retained `phases`, `phase_probes`, and `legacy_probes` publication directories.

- Every `.atom`/`.xml` member of each PLACSP ZIP is visited in central-directory order, independently of feed navigation. No 500-entry cap, archive-year cutoff, or regional filter is applied. Repeated content in another member/archive stays another occurrence.
- Main and execution bulk pages, dataset probes, separately acquired main-table probes, standalone Atom probes, and publication probes are included. A probe is another captured occurrence, not a reason to deduplicate. Counts therefore exceed bulk-only research totals.
- Metadata-before/after and count-before/after acquisitions are linked as `context_artifacts`, not emitted as rows. These retain schema, view technical clocks, and extraction evidence; the reader does not assert a transactional snapshot.
- Append-only metadata annotations are referenced separately. The original manifest line is never replaced by its annotation, and the execution-table period-label correction does not become a date filter.
- Failed retrievals, unfinished `.partial` files, aggregate count/audit responses, documentation, RPC metadata without a row cohort, research SQLite indexes, pretty analysis JSON, and sample copies are not additional source-record inputs.
- Discovery does not silently glob around a missing recorded input. Consuming its descriptor fails if the file or referenced contextual artifact is absent or has a different checksum. Discovery alone does not verify the bytes.

There is no new downloader or network access. Independently calling a reader on an unmanifested local artifact is supported, but its acquisition metadata remains unknown.

## Raw contract

All raw-record fields and nested model objects are immutable value types. Payloads are **lossless references**, not parsed mutable trees or dictionaries embedded in the raw record. The retained files and acquisition ledger must remain available and unchanged.

`RawSourceRecord` extends the source-record envelope with `raw_record_id`. `to_raw` only wraps a reader-produced occurrence and computes its identity; it performs no I/O or semantic conversion.

- **Identity:** `raw:v1:` plus SHA-256 of a versioned, deterministic JSON identity tuple containing source, dataset, kind, root-relative artifact path, artifact SHA-256, acquisition manifest-line reference when present, and the complete record locator. It is an internal occurrence ID, never a procedure/publication identity. Identical source IDs or bytes in different positions/acquisitions do not collapse. Moving the snapshot root preserves IDs; renaming relative artifacts, rewriting/reordering ledger lines, or adopting a different identity version does not. Appending ledger lines does not change earlier acquisition IDs.
- **Artifact:** relative path, SHA-256, size, optional acquisition. A reader verifies the artifact before yielding its records. `ContentReference.document_sha256` separately binds the uncompressed member/document.
- **Acquisition:** exact manifest path, one-based line number and SHA-256 of the line **including its line ending**, original/resolved URL, original download timestamps, and annotation references. `read_manifest_line` verifies and returns the original metadata, including request parameters, status, headers, period labels, and unknown fields. Metadata is not reconstructed from filenames. Callers should not log whole historical manifest entries: early research entries may contain response cookies; this implementation neither copies those into raw fields nor prints them.
- **`observed_at`:** the captured `downloaded_at` string, or `None`. In the research downloader this is successful download completion, not a newly measured precise response-receipt instant. Preserve that definition and precision. No mtime/current-clock fallback, timestamp parsing, or invented `ingested_at` is used.
- **Source facts:** path-qualified textual convenience fields retain Atom IDs/updated/published, tombstone ref/when, Socrata `:id`/`id_intern`/`codi_expedient` and `:created_at`/`:updated_at`, selected rich-body IDs, source links, and actual `versio`/`codiceVersion` markers. Values are not stripped, lowercased, split, or assigned canonical roles. Absent or nontextual convenience fields remain accessible in the original payload, not rejected as procurement errors. These indexes are intentionally not an exhaustive semantic extraction.
- **Remaining context:** feed-level IDs, clocks, links, namespace bindings, code-list attributes, schema details, business dates, rich-body publication clocks, structured legacy calendars, all Socrata system/application fields, unknown fields, and source-specific structures remain recoverable from the document and contextual artifact references.

### Locators and recovery

`RecordLocator` has an explicit `kind`:

- `json-row`: zero-based `ordinal` in the original page array (equivalent to the JSON pointer `/{ordinal}`). The page offset/order/request is available through acquisition metadata. No page offset is inferred from its filename.
- `xml-child`: exact expanded XML tag (`{namespace-uri}local-name`) plus zero-based ordinal **among immediate children with that tag**. Entry ordinals therefore match research entry ordinals even when tombstones occur before them. Tombstone ordinals form their own sequence.
- `document`: explicit whole-document selection; no ordinal. For JSON this corresponds to the empty root JSON pointer, not `/`.

For a ZIP member, `member_name` and its zero-based central-directory `member_index` are both recorded, so duplicate member names remain distinguishable. Standalone documents have neither. No byte offsets are fabricated: these readers select structurally from the exact, checksum-bound containing document. Research sample byte ranges remain separate evidence.

`read_document(root, raw.content)` returns the **exact complete original page/member/body bytes** after checksum verification. It does not return a reserialized single-record fragment. For XML this preserves ancestor namespaces, `xml:base`/`xml:lang`, QName-valued text/attributes, comments, CDATA, and lexical whitespace in their original context.

`load_record(root, raw.content)` is a convenience view: it verifies the same bytes, parses the complete document, validates the locator, and returns the selected object or XML element. Each call returns a fresh mutable view that cannot mutate the raw record. JSON numeric tokens use `Decimal` for nonintegers; strings stay strings. The bytes, not this parsed view, remain authoritative for lexical fidelity (including duplicate JSON keys, XML prefixes, CDATA and XML parser whitespace rules). Consumers needing inherited XML context must use the original document, not serialize the selected element as a replacement artifact.

`load_record` deliberately reopens and verifies the containing artifact on each call. Bulk normalization uses the context manager `verified_resolver(root, artifact)`, which opens and verifies one artifact, caches the current parsed document/member and its checksum, and checks every requested locator and document checksum. Its callable cannot resolve a different artifact. XML child ordinals remain tag-specific. Cached parsed views must not be mutated by callers; normalization never mutates them. Cache lifetime is the context, with memory proportional to the largest current page/member, not the full snapshot. Retained artifacts must remain immutable throughout the run.

## Errors and iteration

`RawSourceError` is the common base:

- `ArtifactReadError`: missing/unreadable files or manifest;
- `IntegrityError`: changed artifact/member/manifest-line checksum or size;
- `SourceFormatError`: malformed XML/JSON/ZIP or wrong table envelope;
- `UnsupportedFormatError` (a `SourceFormatError`): unsupported source representation, encrypted/unsupported-compression ZIP members, or DTD-bearing XML;
- `LocatorError`: invalid selection, out-of-range row/member/XML child, or path escaping the root.

No broad exception recovery skips records. Unknown procurement codes, amounts, identifiers, timestamps, and statuses are not raw-layer errors. ZIP traversal is incremental by member and tables by page; a later member/page can fail after earlier records have been yielded. A completed count requires exhausting the iterator successfully. XML members and JSON pages are parsed before their records are yielded. This does not claim bounded memory independent of the largest member/page.

## Run against retained data

From the repository root:

```bash
.venv/bin/python -m tenderwatch.sources --root . --raw-only
.venv/bin/python -m tenderwatch.sources --root . --source placsp --raw-only
.venv/bin/python -m tenderwatch.sources --root . --source gencat --raw-only
```

With `--raw-only`, the command verifies checksums, creates each raw object, and reports counts by source/dataset/kind without retaining all objects in memory or writing output artifacts. Without this flag, it also materializes normalized observations, resolves procedure identities, reconciles evidence, and publishes canonical observations in the two `data/NormalizedObservations/` and `data/CanonicalObservations/` directories described in README. Progress goes to stderr, final counts to stdout. Failures exit nonzero and do not present partial counts as a successful traversal. This is a local validation entry point, not a production CLI framework.

## Tests and evidence

```bash
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src tests research/scripts
```

The fixture-only tests cover both boundaries, exact document recovery, namespace-safe extraction, separate tombstones, unreachable/duplicate ZIP members, independent repeated rows, immutability, deterministic occurrence IDs, acquisition/context/annotation lineage, unknown-value preservation, and controlled failure cases. No network or bulk snapshot is required.

Small fixtures under `tests/fixtures` have these origins:

- `placsp.atom`: retained aggregated-head feed envelope and first tombstone, plus the complete case-01 `placsp-002.xml.fragment` entry. This is a **constructed small feed**, not a full original page. The entry's exact bytes are checked against research SHA-256 `e66979d1ec776c98d0a3db22c88fd56526f2c8ae065cfd4bc7566e77b7ad255c`.
- `gencat-main.json`: case-01 `gencat-rows.json`, a derived pretty sample of original `ybgg-dgi6/pages/001030000.json`, ordinal 6271. It is not labelled as original page bytes.
- `gencat-execution.json`: the complete five-row retained `8idu-wkjv/probe.json`.
- `gencat-publication.json`: the complete modern `phases/300831068.json` body.
- `gencat-batch-excerpt.json`: explicitly pruned fields from the first three members of `phases/300339416.json`; not the full six-member acquisition.
- `gencat-legacy-excerpt.xml`: the first 51 lines of `legacy_probes/103585423.bin`, closed with the two enclosing end tags; not the full legacy acquisition.

Fixture copies may add a final newline. `test_retained_evidence.py` additionally compares copies/excerpts with the original small evidence when installed, exercises the complete six-member batch as one raw occurrence, and reads all four complete legacy bodies. These optional local-evidence tests skip when the research snapshot is absent. Synthetic cases are limited to parser/locator/integrity/identity invariants and deliberately unusual values; they do not assert normalization behavior.

## Deferred/unsupported and next-boundary questions

- No CSV, Socrata `rows.json` export envelope, JSONL table export, other PLACSP collections, RPC rows, or detached XML fragments without their original feed context. Publication detection currently covers the retained UTF-8 JSON/XML representations, not arbitrary encodings or unresearched publication envelopes. DTDs and external entities are intentionally unsupported.
- No claims of complete historical state, geographic coverage, API transactionality, or acquisition receipt precision beyond the retained evidence.
- No semantic mappings or canonical IDs in the raw layer. Member projections, scopes, timestamps, codes, and monetary semantics are handled only by the separate normalization package; legacy XML normalization remains explicitly unsupported.
- IDs are versioned occurrence identities tied to this retained snapshot layout and append-only ledger. A future relocation/import mechanism must preserve or explicitly migrate those references rather than pretending source IDs are unique raw identities.
- The raw files are protected by checksum verification, not an operating-system immutability guarantee. Do not mutate them concurrently while reading. Long-term artifact storage and recovery caching remain separate implementation decisions.
