# 1. How PLACSP data works

## 1.1 Research scope, evidence and principal conclusions

TenderWatch's current project direction is defined in [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md): its current sources are PLACSP and Generalitat de Catalunya. The models below remain research proposals, not a final production architecture or a commitment to additional sources.

This is an empirical research snapshot acquired on **22 September 2026**, not a production ingestion system. The requested interval is **2025-01-01 through 2026-09-22 inclusive**. It is a change/publication interval, **not a restriction to procedures first opened in 2025**. Consequently, some procedures and notices discussed below originated in 2022–2024.

Evidence labels used throughout:

- **Documented:** stated by an official publisher or the API vendor's technical documentation.
- **Observed:** measured in the local raw acquisitions, with reproducible indexes or samples.
- **Inference:** a plausible interpretation, not an additional fact supplied by the publisher.
- **Unverified:** a claim requiring another experiment or clarification from the publisher.

The central answer is **yes, a traceable canonical representation is feasible, but neither source is a complete event log, and a single identifier plus a single “last updated” timestamp is insufficient**. In particular:

1. A PLACSP Atom entry is an updated representation of a source expediente, not an individual business event.
2. The main Generalitat table mixes ordinary procedure/lot projections and individual contracts within publication batches. It is not one row per notice.
3. A publication UUID can identify a **batch containing different contracts**. Conversely, **313 PSCP URL UUIDs have more than one PLACSP Atom ID** in the aggregation cohort.
4. The same publication can be represented with different timestamp precision and different current organization metadata.
5. Publication, award decision, formalization, execution action, source-table update and retrieval dates must remain separate.
6. “Same source publication” is much easier to establish than “all business fields describe exactly the same state.”

### Local evidence and reproducibility

- Immutable responses: [`data/raw/`](../../data/raw/), including four original national ZIP archives, both Generalitat table extracts, selected rich publication representations and official documentation.
- Acquisition ledger: [`data/raw/download_manifest.jsonl`](../../data/raw/download_manifest.jsonl). Successful files have SHA-256, source/resolved URL, request parameters, HTTP status, important headers, size and UTC retrieval times. Failed requests are retained in the ledger. Seven append-only annotations correct an initial human-readable execution-dataset period label; the preserved requests correctly say `$where=1=1`.
- Main statistics: [`analysis/metrics.json`](../../analysis/metrics.json); overlap-focused statistics: [`analysis/aggregated_metrics.json`](../../analysis/aggregated_metrics.json).
- Further semantic tests: [`analysis/semantic_audit.json`](../../analysis/semantic_audit.json); CSVs: [`monthly.csv`](../../analysis/monthly.csv), [`field_presence.csv`](../../analysis/field_presence.csv), [`matching_candidates.csv`](../../analysis/matching_candidates.csv), [`gencat_publication_dates_monthly.csv`](../../analysis/gencat_publication_dates_monthly.csv).
- Twenty deliberately selected case studies: [`analysis/case_selection.json`](../../analysis/case_selection.json), [`analysis/cases.json`](../../analysis/cases.json), [`analysis/case_findings.json`](../../analysis/case_findings.json), and [`data/samples/`](../../data/samples/).
- Integrity and pagination audit: [`analysis/verification.json`](../../analysis/verification.json), [`analysis/archive_anomalies.json`](../../analysis/archive_anomalies.json).

An extracted XML sample is an **exact byte slice** of its ZIP member. Its namespace declarations may be inherited from the parent feed; `.xml.fragment` files are intentionally not advertised as standalone XML documents. Each sample records the archive, member, entry ordinal, byte range and fragment checksum. Generalitat samples record the original page and row ordinal. Pretty JSON and research SQLite indexes are derived, not replacements for raw files.

**Coverage limits:** these are the data available from the selected official distributions at retrieval time. The final day was still in progress. Daily source publication lags mean this is **not certification that every event through the end of 22 September is present**. Full current table rows and archive bytes were retained; rich publication bodies were fetched for the selected cases, **not for every procedure**. Tender attachment PDFs and other document binaries were not exhaustively downloaded. Historical state completeness cannot be guaranteed by either table/feed. PLACSP minor-contract and own-resource-entrustment feeds, and Generalitat's separate contract register, were identified but are not additional bulk cohorts in this comparison.

### Official references

- **D1:** [PLACSP syndication specification, version 1.10, 17/09/2024](https://contrataciondelsectorpublico.gob.es/datosabiertos/especificacion-sindicacion.pdf), locally `data/raw/documentation/syndication-current.pdf`; extracted, page-marked text under `data/analysis/documentation/`. Especially §§3.1–3.4, 4.1, 4.35, 4.38 and 4.39. The older version 1.3 was also retained; conclusions use 1.10 where it supersedes it.
- **D2:** [Official aggregation distribution catalogue](https://www.hacienda.gob.es/es-es/gobiernoabierto/datos%20abiertos/paginas/licitacionesagregacion.aspx), locally `aggregation.html`.
- **D3:** [Official native-profile distribution catalogue](https://www.hacienda.gob.es/es-es/gobiernoabierto/datos%20abiertos/paginas/licitacionescontratante.aspx), locally `native.html`.
- **D4:** [OpenPLACSP manual 2.1](https://contrataciondelestado.es/datosabiertos/DGPE_PLACSP_OpenPLACSP_v.2.1.pdf), locally `openplacsp-2.1.pdf`.
- **D5:** [Official PSCP main-table metadata](https://analisi.transparenciacatalunya.cat/api/views/ybgg-dgi6.json), locally `data/raw/gencat/ybgg-dgi6/metadata-before.json` and `metadata-after.json`.
- **D6:** [Official execution-table metadata](https://analisi.transparenciacatalunya.cat/api/views/8idu-wkjv.json), equivalent local files under `8idu-wkjv/`.
- **D7:** [PSCP/eLicita presentation hosted by Localret](https://www.localret.cat/wp-content/uploads/2023/04/Contractacio-Publica-i-AOC.pdf), locally `pscp-aoc-2023.pdf`. Its data-set and lot-management descriptions supplement, rather than override, the current official metadata.
- **D8:** [Socrata system fields](https://dev.socrata.com/docs/system-fields.html) and [pagination](https://dev.socrata.com/docs/queries/offset), both preserved locally.

## 1.2 Distributions, acquisition and geography

**Documented, D2–D3:** the two primary feeds are:

| Feed | Contents | Historical mechanism |
|---|---|---|
| `sindicacion_643/licitacionesPerfilesContratanteCompleto3` | Procedures from buyers with their profiles hosted on PLACSP, excluding minor contracts | Annual archives from 2012; monthly/current-year incremental archives |
| `sindicacion_1044/PlataformasAgregadasSinMenores` | Procedures transmitted from other platforms, excluding minor contracts | Annual archives from 2016; monthly/current-year incremental archives |

Also relevant are `sindicacion_1143/contratosMenoresPerfilesContratantes` for native minor contracts, `sindicacion_1383/EMP_SectorPublico` for own-resource entrustments, and the buyer-profile distribution. They serve different procurement populations. Generalitat's own “aggregated publication” flag is **not** the same concept as PLACSP's aggregated-platform feed.

The research downloaded the **2025 and 2026 annual ZIPs of both primary feeds**. Using one annual series avoids deliberately mixing overlapping monthly and annual distributions. Every Atom member was inspected, including members not reachable through the head's link chain. Selection uses actual entry timestamps, never the date in a ZIP/member filename.

| Archive | ZIP bytes | Atom members | All entry occurrences | Selected in-range Catalunya-oriented occurrences |
|---|---:|---:|---:|---:|
| Aggregated 2025 | 139,302,233 | 630 | 250,652 | 110,686 |
| Aggregated 2026 incremental | 107,444,835 | 403 | 187,103 | 76,587 |
| Native 2025 | 2,172,595,976 | 1,398 | 693,088 | 17,777 |
| Native 2026 incremental | 1,571,316,789 | 991 | 493,738 | 13,411 |
| **Total** | **3,990,659,833** | **3,422** | **1,624,581** | **218,461** |

Of all archived entries, **1,620,626** have an in-range `updated` date and **3,955** do not. After geographic selection, the full cohort has **65,954 distinct Atom IDs**: **57,311 aggregated** and **8,643 native**. The native subset contributes **31,188 observation occurrences** and no explicit PSCP UUID links in its entry URLs. This is expected for a different profile-hosting population, not a measured missing-link rate for the aggregation feed. The annual archives have boundary overlaps: figures above count stored occurrences, not deduplicated events.

The full selected cohort has **1,885 distinct source buyer-identifier bundles** (origin platform plus Party identification tuples), **36,009 distinct `(Atom ID, named lot ID)` pairs across history**, and **165,848 nested lot occurrences**. These are operational identifiers/occurrences, not an entity-resolved census of legal buyers or current lots. The aggregation-only lot-pair count is **30,115**. In Generalitat's ordinary cohort there are **29,460 nonzero named-lot rows**, corresponding to **29,459 distinct `(procedure UUID, lot number)` pairs**; one pair repeats. These counts should not be equated across differing identity/history populations.

Monthly distributions are preserved in `analysis/monthly.csv`. PLACSP is grouped by **entry updated month**; Gencat is grouped by the **latest available publication-date column per selected row**, not by download or source-update month. For example January 2025 has 8,541 aggregation observations, 1,347 native observations and 53,884 Gencat rows on that different basis; September 2026 has 5,847, 899 and 18,357 respectively. The ten separate Gencat publication-date monthly distributions are also exported, so this convenient row histogram does not collapse their underlying semantics.

The completed aggregation archives contain **437,755 Atom entry occurrences** before date/geography selection. Of these, **187,273** enter the Catalunya-oriented research cohort, representing **57,311 Atom IDs** and **56,933 non-null PSCP procedure UUIDs**. Counts of source IDs are not counts of already-resolved legal procedures.

Geographic selection is the union of four **separately recorded** predicates:

1. Origin platform `AgentParty/PartyIdentification/ID = 62` (Generalitat de Catalunya).
2. Entry link hosted on `contractaciopublica.cat` or its legacy `contractaciopublica.gencat.cat` hostname.
3. Procedure or lot execution NUTS starting with `ES51`.
4. Buyer postal code in the Catalan province prefixes `08`, `17`, `25`, `43`.

The aggregation cohort includes **187,250 origin-platform-62 occurrences** and **23 additional occurrences** selected through other geography signals. **1,176 Catalan-origin occurrences do not have an ES51 execution code**. This can mean missing geography or execution elsewhere; it does not make the Catalan origin false. The aggregation cohort has **104,233 occurrences with execution NUTS exactly `ES511`**.

There is no single defensible definition of a “Barcelona tender”:

- `ES511` describes the **province-level execution area**, not Barcelona municipality.
- Buyer postcode prefix `08` describes a buyer address in Barcelona province, not necessarily where work takes place.
- A Barcelona-city buyer is a separate identity/address/municipality criterion.
- A national buyer can procure work in Barcelona; a Barcelona buyer can procure work elsewhere.
- A procedure can have lots in several execution areas.

For the future product, expose buyer jurisdiction and execution geography as separate facets; allow an explicit union/intersection chosen by the product, not an undocumented ingestion assumption.

## 1.3 Atom, CODICE and the logical unit

**Documented, D1:** Atom provides the distribution envelope. Its entry contains a `cac-place-ext:ContractFolderStatus` tree using CODICE components and PLACSP extensions. CODICE uses UBL-related concepts, but these are the actual `urn:dgpe:...` namespaces, not an arbitrary UBL invoice schema. Namespace URIs and code-list attributes must be preserved.

Important distinctions:

| Element | Meaning |
|---|---|
| Feed `id`, `updated`, `link rel=self/first/next/...` | Identity, generation/update and navigation of a feed page |
| Entry `id` | Source expediente identity within a syndication collection, not a publication ID |
| Entry `updated` | D1 describes the time of the latest relevant publication; not our retrieval time |
| Entry `title`, `summary`, `link` | Display material and source page; the link may identify a specific origin publication |
| `ContractFolderID` | Buyer's human expediente number; mutable and not globally unique |
| `ContractFolderStatus` | Updated structured representation, including accumulated notices/results and other available information |

Simplified real observation, case 01:

```xml
<id>https://contrataciondelestado.es/sindicacion/PlataformasAgregadasSinMenores/20283724</id>
<link href="https://contractaciopublica.cat/ca/detall-publicacio/4b131001-63ad-4eac-a80a-ab91c3a9f366/300888482"/>
<updated>2026-09-21T22:00:26.651+02:00</updated>
<cbc:ContractFolderID>905451/26</cbc:ContractFolderID>
<cbc-place-ext:ContractFolderStatusCode>EV</cbc-place-ext:ContractFolderStatusCode>
```

The buyer is Àrea Metropolitana de Barcelona, `ID_OC_PLAT=28027859`; the origin platform is `62`. This gives an explicit PSCP procedure UUID, a PSCP notice ID and a shared source-specific buyer identifier. Its Spanish Atom title and Catalan table title differ; rich PSCP JSON supplies both language variants. Title inequality is not an identity conflict here.

## 1.4 Evolution, publications and history

**Documented, D1 §§3.3.1–3.3.2:** repeated entries with the same Atom ID are expected. The newest representation contains updated expediente information. However:

> The purpose of the syndication is not to provide the history of every state; older entries may exceptionally be removed.

The specification also explicitly permits correction of Atom-generation errors **without changing the entry's `updated` timestamp**. Consequently, neither `(id, updated)` nor a high-water timestamp alone is a sufficient immutable observation identity or complete correction detector.

**Observed in the aggregation cohort:**

| Test | Result |
|---|---:|
| Atom IDs with more than one observation occurrence | 39,810 |
| IDs with more than one distinct `updated` value | 39,784 |
| Extra occurrences sharing the whitespace-insensitive XML-tree hash | 307 |
| Distinct whole-entry tree hashes | 186,966 |
| Distinct CODICE-subtree hashes | 160,757 |
| Same ID + timestamp, different tree hash | 0 in this frozen cohort |
| Atom IDs whose expediente number changes | 159 |
| PSCP URL UUIDs associated with multiple Atom IDs | 313 |

The hashes above are **research tree hashes**, using expanded XML names, attributes and stripped node text; they are not hashes of original XML bytes and are not a complete semantic hash. Original archive hashes and exact sample byte hashes are stored separately. Zero equal-timestamp conflicts here does not refute the documented possibility of later in-place corrections: that requires repeated retrieval of the same upstream resource over time.

`ValidNoticeInfo` is itself not always “one notice object.” D1 §4.39 permits multiple publication media and multiple dated document references for the same type/media grouping. In the Catalan aggregation examples it often contains notice type and **date only**, without a notice identifier. The Atom link's numeric PSCP publication ID therefore provides an important additional signal.

Case 02, Deltebre expediente `4390180001-2024-0010219`, demonstrates material evolution:

| PLACSP `updated` date | Status | Net budget | Submission date |
|---|---|---:|---|
| 2025-01-09 | PUB | 162,565.20 | 2025-01-24 |
| 2025-01-24 | PUB | 162,565.20 | 2025-02-10 |
| 2025-02-11 | PUB | 162,565.20 | 2025-02-26 |
| 2025-03-21 | PUB | 162,565.20 | 2025-04-07 |
| 2025-05-05 | PUB | 177,465.20 | 2025-05-20 |
| 2025-05-06 | PUB | 177,465.20 | 2025-05-21 |
| 2025-05-22 | EV | 177,465.20 | 2025-05-21 |
| 2025-07-24 | ADJ | 177,465.20 | 2025-05-21 |
| 2025-08-18 | RES | 177,465.20 | 2025-05-21 |

Ten observations are preserved; the table omits one intermediate February update for readability. All ten corresponding rich PSCP publication bodies were recovered. This is evidence for multiple states, not proof that ten observations equal ten material revisions.

Across the aggregation cohort, successive extracted representations differ in deadline date for **3,952 IDs**, budget for **545**, estimated value for **418**, document-reference collections for **12,196**, lot representations for **2,439**, and status for **37,167**. These are representation differences: some can be corrections, increased completeness, formatting or reordering rather than business changes.

## 1.5 Buyers, lots, awards, documents and status

- **Buyer:** `LocatedContractingParty/Party` has scoped identifications, name and sometimes address. `AgentParty` identifies an origin platform in the aggregation feed; it is not the winning supplier. Parent-party structures describe organization hierarchy. Native Catalan-selected 2025 records all contain an explicitly NIF-labelled buyer identifier; the Catalan aggregation projection does not.
- **Lots:** repeated `ProcurementProjectLot` children. Case 05, `ME. MEC-25L02`, has 13 lots and **25 PLACSP observations across both years**, but 13 current Generalitat rows. Lot fields may be sparse in aggregation: do not distribute the procedure budget over lots or fabricate lot budgets.
- **Results/awards:** repeated `TenderResult`, result codes, `WinningParty`, awarded-project amounts, lot references and contract information. A `TenderResult` can describe an unsuccessful or withdrawn process; its presence is not proof of a positive award. Several suppliers/results/lots are possible.
- **Status:** `PUB`, `EV`, `ADJ`, `RES`, `PRE`, `ANUL` are observed. D1 describes `RES` as resolution that can include formalization, unsuccessful tendering, withdrawal or abandonment. It is not a synonym for “awarded successfully.”
- **CPV:** `RequiredCommodityClassification/ItemClassificationCode`, with code-list URI. PLACSP examples use eight-digit CPV values; the Catalan table commonly includes a check digit, e.g. `90513000` versus `90513000-6`.
- **Money:** procedure `BudgetAmount` separates estimated overall amount, tax-exclusive budget and gross amount where present. Award money appears under awarded-project monetary totals. Currency belongs to each amount, not implicitly to every numeric value in the record.
- **Dates:** deadline date and time are separate components; notice issue dates can have only day precision; contract-signing/award dates are different facts. Do not attach `entry/updated` to every nested object as its business date.
- **Documents:** legal, technical and additional document references can contain IDs/names and external URIs. Other document references appear inside notices/results. The simple field-presence metric for document links counts direct document-reference children only; full raw XML preserves nested references too. A URL list is not the binary content of the specifications.

## 1.6 Deletion, cancellation and archive anomalies

**Documented, D1 §3.1.2:** Atom tombstones use `ref` and `when`. Since July 2022, `at:comment/@type` distinguishes `ANULADA` (invalidated expediente) from `CERRADA` (closed/archived, no longer accessible). **A closed-source record is not automatically a cancelled contract.** Preserve a source-availability event independently of business outcome.

The aggregation archives contain **78,898 tombstone occurrences**, all `CERRADA`; **446 are dated 2024-12-31**, outside the requested interval despite being inside the 2025 archive. The in-range aggregation tombstone count is therefore **78,452**. These are national-feed counts: tombstones lack buyer/geography payload, and only **282 selected Atom IDs** can be linked to one from the available selected observations. Do not label all 78,452 as Catalan cancellations.

The native 2025 archive additionally contains `ANULADA`, `CERRADA` and tombstones without a type. There are also ordinary `ANUL` state observations. These mechanisms must not be collapsed.

**Observed contradictions/peculiarities:**

- D2/D3 advertise at most 500 entries per page. **Ten pages** in the 2025 aggregation archive exceed 500, with **518–520 entries**. For example `PlataformasAgregadasSinMenores_20250128_040028_3.atom` contains 520 distinct entry IDs with updates from 24–27 January 2025. Do not hard-code rejection at 500. Exact members and dates are in `analysis/archive_anomalies.json`.
- The native 2025 and 2026 ZIPs each contain **three Atom members outside the head's reachable chain**. These are the same September 2021 members, containing 1,430 entry occurrences per archive and no in-scope entries. The parser inspected them rather than silently assuming all ZIP members belong to the advertised year.
- The 2025 aggregation archive extends into **2026-01-01** for some entries; the 2026 archive begins with some **2025-12-30** entries. ZIP labels are not exact semantic date boundaries.
- Atom ID stability is useful but not a one-to-one legal-procedure guarantee: case 10 associates IDs `16638290` and `16638580` with the same PSCP UUID and expediente `SCS-2025-122`.

# 2. How Generalitat de Catalunya data works

## 2.1 Datasets and collection method

The primary official SODA resource is `ybgg-dgi6`, “Contractació pública a Catalunya: publicacions a la Plataforma de serveis de contractació pública.” The metadata exposes **67 application columns**, supplemented here by `:id`, `:created_at` and `:updated_at`.

The complete live table contained **1,978,216 rows** in the saved aggregate audit. Its earliest tender-notice date was **2011-02-03T11:30:00.000**; the latest was **2026-09-21T20:44:00.000**. Thus table creation dates do not mark the beginning of business history.

Collection selects rows satisfying an OR across **all ten `data_publicacio*` fields**, with `>= 2025-01-01T00:00:00` and `< 2026-09-23T00:00:00`. It uses pages of 10,000 rows ordered by `:id`, preserving all application/system fields. Before/after metadata `rowsUpdatedAt`, server counts, acquired count and distinct row IDs agree. This is evidence of a consistent extraction, not an API-guaranteed transaction snapshot.

The result is **1,070,969 rows**. Every row has a unique Socrata ID and `id_intern` within this snapshot. The API's publication-date selection does not recover prior versions of those rows.

Two other datasets matter:

- **`8idu-wkjv`: execution actions.** All **67,960** currently available rows were downloaded because there is no publication-date column equivalent to the main table's dates. `data` means action date, not API update time. **35,098 actions** have an action date inside the research interval, spanning **19,283 buyer/expediente pairs** and **767 buyers**; **8,054 rows have no action date**, and **24,808** have an out-of-range action date. They remain in raw storage and are not silently discarded.
- **`hb6v-jcbf`: public contract register (RPC).** Official metadata was retained in `data/raw/gencat/rpc-metadata.json`. This is a contract-registration population, including post-award information, not a substitute for opportunity/publication ingestion. It was identified, not bulk-ingested in this PSCP-focused comparison.

**Documented warning, D5:** the publisher reports missing expedientes in historical dataset versions from **15–19 June 2026**. This is a concrete reason not to equate absence in a table snapshot with legal cancellation.

## 2.2 What one row represents—and where that model breaks

**Documented, D5/D7:** rows can represent an expediente, a lot, or an individual expediente within an aggregated publication. `fase_publicacio` is described as the latest published phase. Rich information is linked separately for each phase.

**Observed:**

| Population | Rows | Identity interpretation |
|---|---:|---|
| `es_agregada = NO` | 88,077 | Ordinary procedure/lot projections, including some planning records and minor contracts |
| Ordinary distinct URL UUIDs | 66,491 | Practical official procedure-object count, not a count of rows or notices |
| `es_agregada = SÍ` | 982,892 | Individual contracts/entries within aggregate publications |
| Aggregate distinct URL UUIDs | 12,317 | **Publication batches**, not 12,317 individual contracts |
| Aggregate distinct `id_intern` values | 982,892 | Distinct current source-row identities, not proven globally unique legal contracts |
| Buyers (`codi_organ`) across the selected main table | 1,802 | Source-specific contracting organizations |

There is **no trustworthy single “unique tenders” total** obtained by counting either all row IDs or all URL UUIDs. The main table also has **6,632 ordinary rows with `procediment=Contracte menor`**. “Ordinary publication” is not synonymous with “non-minor tender,” which matters when comparing with PLACSP's explicitly non-minor feeds.

Important empirical exceptions to an overly simple latest-state model:

1. **Parent and lot rows can retain different phases.** Case 16, UUID `0a859be5-1ee8-4c70-97f5-5ac6b6677700`, retains a parent `Alerta futura` row without `codi_expedient`, alongside five `Anunci de licitació` lot rows for `2026/7731`. There are **20 ordinary UUIDs with multiple phase labels across rows**. These are not automatically 20 temporal event histories or 20 errors.
2. **Lot number is not a guaranteed row key.** Case 15, `URB/2022/164`, has two different `id_intern` values with `numero_lot=3`, linked to different publication IDs. This is the one ordinary `(UUID, lot)` group with duplicate rows in this extraction.
3. **The suffix of `id_intern` is not the official lot number.** In case 05, suffix `_6` corresponds to lot `7`. Preserve both. Never derive lot identity by splitting this string and assuming its suffix is `numero_lot`.
4. The main table still contains rows whose phase label is `Execució`, even though detailed execution **actions** live in the separate dataset. A phase label and an action table have different granularity.

### Aggregate-publication counterexample

Case 14 uses publication **300339416**, UUID `fff0ffe1-d07b-42af-ade9-dc8eb403a8b6`, buyer XALOC (`2988807`). It contains six separate contract rows. Examples:

| `id_intern` suffix | Expediente | Description / awardee | Award amount, net |
|---|---|---|---:|
| `_306344580` | 2023/585 | Life insurance / Seguros Catalana Occidente | 28,957.25 |
| `_306344581` | 2023/800 | Collective accident insurance / Zurich | 7,096.06 |
| `_306344582` | 2023/800 | Vehicle insurance / FIATC | 3,149.79 |

All share the same publication URL. Some also share a buyer and expediente string while describing separate published contract entries. An unconditional UUID merge or buyer-plus-expediente merge across this population would lose distinctions.

## 2.3 Rich publications, corrections and legacy formats

The table's `url_json_licitacio`, `url_json_adjudicacio`, `url_json_formalitzacio`, `url_json_anulacio`, etc. are essential enrichment links. Modern downloaded bodies contain, among others:

- `idExpedient` and `codiExpedient`;
- `dataPublicacioPlanificada` and `dataPublicacioReal`;
- `organ`, including a buyer NIF in some bodies even though the table lacks a buyer-NIF column;
- `publicacio.fase`, multilingual basic data, procedure-wide and lot-specific data;
- `tipusEsmena` and `motiuEsmena` for corrections;
- document IDs, titles, source-reported hashes, paths and sizes;
- execution-action arrays in execution publications.

The sampled `versio="1.0.0"` is a **representation/schema version**, not evidence of the first business revision. One sampled body omitted it. Do not number canonical tender revisions from this field.

Case 01 illustrates a real correction:

```json
{
  "idExpedient": "4b131001-63ad-4eac-a80a-ab91c3a9f366",
  "codiExpedient": "905451/26",
  "dataPublicacioReal": "2026-09-17T18:18:05.642Z",
  "publicacio": {
    "tipusEsmena": {"ca": "Data obertura de sobres"},
    "motiuEsmena": {"ca": "Modificació de dades d'obertura"}
  }
}
```

This is publication **300885987**. The original tender notice **300837018**, also downloaded, has `dataPublicacioReal=2026-08-11T07:02:05.662Z`. Both retain a submission deadline of `2026-09-14T12:00:00.000Z`. The correction is **not a new initial opportunity or a deadline extension**. The current table's `data_publicacio_anunci=2026-09-17T20:18:00.000` identifies the later corrected tender-phase publication, while PLACSP `ValidNoticeInfo/DOC_CN/IssueDate` retains **2026-08-11**.

**Observed legacy-format surprise:** four advertised encrypted JSON links returned 404. Fetching their publication IDs through the official unencrypted `/portal-api/documents-publicacio/json/{id}` endpoint recovered all four as **XML**, not JSON. One begins:

```xml
<Notice>
  <codiceVersion>1.05b</codiceVersion>
  <tenderingSpaceId>107376459</tenderingSpaceId>
  <TenderingProcess><diligenceId>9884AM</diligenceId></TenderingProcess>
  <com.capgemini.gencat.economia.pscp.entity.PscpContractNotice>
    <contractNoticeId>107376474</contractNoticeId>
```

Raw legacy bodies are under `data/raw/gencat/legacy_probes/`. They contain CDATA, Java-entity-style element names and structured calendar values. This is not the modern PSCP JSON schema, nor the same Atom/CODICE envelope as PLACSP. The endpoint name and table column name are not reliable content-format validators.

## 2.4 Dates and temporal precision

| Timestamp | Documented or observed meaning | Do not confuse with |
|---|---|---|
| Main-table `data_publicacio_*` | Publication of a named phase; empirical examples include its later correction | First-ever publication, source-row update |
| `data_adjudicacio_contracte` | Award decision date | Award notice publication |
| `data_formalitzacio_contracte` | Contract formalization date | Formalization notice publication |
| `termini_presentacio_ofertes` | Submission deadline | Publication date |
| Rich `dataPublicacioPlanificada` | Planned publication timestamp | Actual publication |
| Rich `dataPublicacioReal` | Actual publication timestamp in sampled official representation | API retrieval |
| Execution `data`, `data_fi` | Action/start and end dates | Publication or row update |
| Socrata `:created_at`, `:updated_at` | Record creation/update in Socrata, D8 | Procedure creation or a business lifecycle event |
| View metadata `createdAt`, `publicationDate`, `rowsUpdatedAt` | Dataset/view-level management metadata | Dates of individual notices |

The selected main table contains historical publications, but the saved audit's **minimum Socrata row-created time is 2026-07-13T13:26:08.273Z**. Many old procedures share that technical timestamp. D8 explicitly warns that full replacements can update all rows. A reload/migration is a plausible explanation; its precise administrative cause is unverified.

The SODA application dates are floating timestamps, with no explicit offset. Modern rich JSON uses `Z`; sampled conversions agree with **Europe/Madrid**, including daylight saving. Preserve the original local value and record the timezone interpretation rather than silently interpreting floating values as UTC.

Precision is substantive. In case 13 the rich JSON deadline is **2026-09-16T21:59:59.000Z**; PLACSP reports local **23:59:59**; the table reports **23:59:00.000**. This supports a minute-level projection, not a real 59-second deadline change. At the same time, precision truncation must not be assumed for every arbitrary mismatch.

A timestamp-difference audit over 50,115 shared-publication pairs found a median PLACSP-updated minus latest table publication-column difference of **5,269.895 seconds**, with **27 negative differences**. This is **not measured delivery latency**: a table row's source URL and its latest phase-date column can refer to different notices, as case 13 demonstrates. The signed differences show why subtracting superficially comparable timestamps, or globally sorting on them, is not a reliable lifecycle or arrival-order model.

## 2.5 Execution, awards, suppliers, amounts and documents

**Execution case 19:** Vila-seca expediente `4317110007-2021-0001388` has two rows pointing to the same publication **300007312**:

| Action date | Net action amount | Row creation | Row update |
|---|---:|---|---|
| 2026-03-30 | 341,124.07 | 2026-08-27T01:10:55.486Z | 2026-09-22T01:11:51.826Z |
| 2026-08-10 | 317,101.25 | 2026-08-27T01:10:55.486Z | 2026-09-22T01:11:51.826Z |

The downloaded publication body was actually published **2026-08-26T10:44:10.472Z** and contains two modification objects with local `identificador` values **1 and 2**. Its UUID is `cdd2280f-bc0d-b291-4214-69ded8c1182d`. Thus **one publication contains multiple actions with earlier action dates**. No matching main-table row falls into the selected publication-date cohort for this procedure. A main-table-only ingestion would miss these execution actions.

**Awards:** D5 documents `||`-concatenated amounts for multiple winners. The extraction has **1,807 rows with multiple supplier identifiers** but only **1,712 with `||` in the net-award amount field**. The representation is not a clean nested award array. In case 20, `9884AM`, supplier IDs are `B41956970||A08338683` while the net-amount field is literally `||`. Empty tokens must not become zero amounts or be dropped before alignment. UTE/consortium identifiers are not interchangeable with each constituent company.

**Money scope:** `valor_estimat_contracte` is documented as the **lot** estimate; `valor_estimat_expedient` is the **procedure** estimate. Similarly, `pressupost_licitacio_sense` is lot-level and `pressupost_licitacio_sense_1` is procedure-level. Human display names and API field names differ. Summing the repeated procedure amount across lot rows would multiply the budget. Numeric equality checks in this research compare declared net numeric values; the Gencat table does not independently supply a currency column for a fully qualified money equality proof.

**Source-specific detail:** Gencat exposes descriptions, richer multilingual text, origin buyer NIF in rich publications, correction reasons and structured execution actions. PLACSP's compact Catalan projection often supplies procedure state and references but lacks these details. Gencat's current table can retain a previous winner when its latest phase is withdrawal; PLACSP may instead expose only the latest withdrawal result. Keep both historical award facts and later outcome facts.

## 2.6 Completeness and internal duplication

Presence means non-empty data in the examined representation, **not validation or truth**. A number encoded as `0` is present; `||` can be present but unusable. Document-link counts differ by representation.

| Concept | PLACSP aggregation cohort | Gencat full selected main table |
|---|---:|---:|
| Expediente | 100% | 99.9848% |
| Buyer identifier | 100% | 100% |
| Buyer NIF explicitly provided in this bulk projection | 0% | 0% |
| CPV | 99.9957% | 83.0568% |
| Net budget, any available applicable scope | 100% procedure | 85.8397% lot/procedure |
| Estimated value | 99.9877% procedure | 89.0230% lot/procedure |
| Submission deadline | 94.9235% | 7.3299% |
| Execution location | 99.4169% | 84.0104% |
| Status / phase label | 100% | 100% |
| Source page link | 100% | 100% |
| Direct legal/technical/additional document URL / phase export URL | 94.7836% direct documents | 100% phase export links, not direct document binaries |
| Result structure / award-related field | 44.8191% `TenderResult` | 98.0842% award-related fields |

Exact numerator/denominator CSVs and ordinary-versus-aggregate Gencat breakdowns are supplied; these populations must not be compared as if they contained the same mix of records. In particular the Gencat deadline percentage is dominated by batch contract reports, not missing deadlines in ordinary open tenders. Buyer NIF in the bulk tables is distinct from supplier NIF; enrichment changes its availability.

Other observations:

- **32,776 expediente-string buckets span multiple buyers** in the selected Gencat table. Never use expediente alone as a global key.
- For **ordinary records with a non-null/non-empty expediente**, no same-buyer/exact-expediente pair mapped to multiple UUIDs in this snapshot. An earlier null-inclusive grouping produces 33 groups—all missing-number buckets, not real collisions. This strengthens that composite as a candidate signal, not as an eternal uniqueness guarantee.
- There are **1,478 exact-title groups spanning multiple ordinary UUIDs**. A repeated Microsoft-licensing title alone spans 39 UUIDs.
- **34 buyer codes have multiple buyer-name strings**. Source identifiers should precede name similarity.
- **1,720 ordinary rows use DIR3 `A9999999`**. It is a shared placeholder, not a safe organization identity.
- **10,183 rows have a tender-phase publication timestamp after their submission deadline**. The reviewed correction cases explain why this need not mean late initial advertising; the entire set has not been adjudicated.
- One ordinary duplicate `(UUID, lot-number)` group is preserved without deduplication. Counting all batch UUID/lot pairs would confuse batch membership with lots.

Excluding `id_intern` and Socrata system metadata, there are **367 extra rows with exactly equal remaining JSON content**. Collapsing whitespace raises that to **368**. Examples include source IDs `03534917-ccb3-47dd-8a86-4ac31bff4224_309543577` and `_309543578`. These are candidate content duplicates, not proof that two reported contracts are the same legal contract. The raw rows remain distinct. The separate metric that includes `id_intern` naturally finds zero identical business rows; its identity-inclusive definition must not be mistaken for a successful duplicate-contract audit.

For the **ordinary Gencat rows alone**, deadline presence is **89.1277%**, CPV **98.9657%**, procedure budget **97.6770%**, estimate **99.6583%**, and execution location **99.5799%**. This is a much more relevant completeness baseline for opportunities than the batch-dominated full-table percentages.

For **all 218,461 selected PLACSP observations** including native profiles, explicit buyer-NIF presence is **14.2762%**, CPV **99.9396%**, estimated value **99.9826%**, deadline **94.6526%**, execution location **99.5001%**, direct document links **94.0951%**, and `TenderResult` presence **45.9203%**. Expediente, buyer identification, budget, status and source link are present in 100%. Full-cohort counts are kept separate from the overlap-focused aggregation figures above.

# 3. Differences between PLACSP and Generalitat schemas

## 3.1 Concept-by-concept comparison

| Concept | PLACSP | Generalitat | Semantic differences | Normalization implications |
|---|---|---|---|---|
| Procedure identifier | Atom entry ID within collection | Ordinary publication URL UUID / rich `idExpedient` | Several PLACSP IDs can share one UUID; aggregate UUID is a batch | Namespaced external identifiers and typed subject identities |
| Expediente | `ContractFolderID` | `codi_expedient`, rich `codiExpedient` | Mutable, missing for planning, non-global; aggregate collisions | Versioned aliases scoped to buyer/process; never primary key |
| Publication identifier | Often in origin URL; not Atom ID; notice groups may lack IDs | Numeric publication IDs in URLs and phase links | Main source link may lag a corrected phase link or differ across lots | Separate Notice and NoticeSubject relations |
| Buyer identifier | Party ID plus scheme; origin platform supplies scope | `codi_organ`, `codi_dir3`, rich NIF | DIR3 placeholder; originating organization can differ from current table organization | Scheme/issuer/country/role and temporal identity mappings |
| Buyer name | PartyName, hierarchy | `nom_organ`, organizational hierarchy | Renaming, translation, administrative reassignment | Names are attributed labels, not keys |
| Title | Atom title / project Name | `denominacio`, multilingual rich JSON | Spanish versus Catalan is common | Language-tagged values; do not treat translation as contradiction |
| Description | Compact project text; additional native detail possible | `objecte_contracte`, rich `descripcio` | Different completeness and scope | Distinct title and description assertions |
| Lifecycle/status | Procedure-oriented code (`RES` broad) | Phase label plus lot `resultat`; action types separately | Withdrawal can be PLACSP RES and Gencat Anul·lació | Status vector and typed events, not one lossy enum |
| Publication timestamp | Notice date(s); `updated` has documented latest-publication semantics | Per-phase table dates; rich actual/planned timestamps | Original notice date versus correction date; precision differences | Keep notice identity, media, time role and precision |
| Update timestamp | Entry `updated`; feed `updated` is separate | Socrata system update; dataset-level update | Business/source change versus technical table management | Separate source_updated_at by record kind, never global last-write-wins |
| Submission deadline | EndDate + EndTime, sometimes second precision | Floating table datetime; rich UTC timestamp | Empirical second truncation in the table | Preserve raw precision; prefer detailed authoritative notice when justified |
| Award | TenderResult and awarded-project structures | Current award columns / rich lot publications | Latest result can suppress former winner; Gencat can retain it | Historical Award plus outcome/withdrawal relations |
| Winner | Repeated WinningParty | IDs/names, sometimes `||` strings | UTE vs companies; parallel arrays can be incomplete | SupplierParty and AwardParty associations; preserve alignment errors |
| Budget | Procedure/lot BudgetAmount, net/gross | Separate lot and procedure fields | Repeated procedure values on lot rows | Money has purpose, tax basis and subject scope |
| Estimated value | EstimatedOverallContractAmount | `valor_estimat_contracte` versus `valor_estimat_expedient` | Despite its name, the former is documented lot-level | Never compare lot estimate to procedure estimate |
| Award amount | Awarded-project monetary total | Net/gross text, possibly multiple/empty tokens | Not always a scalar or a complete amount | Zero, null, missing and invalid tokens remain distinct |
| CPV | Classification codes with list URI | Often check-digit form; lot-oriented | Eight versus nine digits and scope | Standardized code + preserved original/check digit/scope |
| Lots | Nested structures and result references | Rows, plus rich lot arrays | Row suffix not lot number; duplicate numbers observed | Local lot entities with source aliases and unresolved-identity flags |
| Execution location | Procedure/lot RealizedLocation | NUTS + `lloc_execucio`; rich address | Not buyer geography or publication platform territory | Typed locations by role and subject |
| Documents | Reference trees and URIs | Rich JSON document metadata/paths; bulk phase links | Bulk table does not itself contain all document metadata | Document versions separate from notice links; hashes with known algorithm only |
| Source URLs | Entry link and references | Publication, phase JSON and legacy export URLs | URL can point to batch, older notice or XML through a JSON-named route | Preserve exact URL and parsed target type separately |
| Cancellation/deletion | ANUL state; result/notice types; typed tombstones | Anul·lació + result/reason; source row absence | Archive closure not cancellation; absent row not a business fact | SourceAvailabilityEvent separate from business outcome |
| History | Updated representations, repeated entries, incomplete retention guarantee | Current table projections plus retrievable phase publications; separate actions | Neither is a guaranteed complete event log | Immutable observations and explicitly incomplete history coverage |

## 3.2 Twenty reviewed cases

All identifiers below have local raw references and extracted representations. This is a **purposive edge-case sample**, not a random validation set and not a precision estimate.

| Case / local folder | Procedure or identifier | Finding and reconciliation consequence |
|---|---|---|
| [01](../../data/samples/01_amb_correction/) | AMB `905451/26`, PLACSP 20283724 | August notice, September opening-information corrections, Spanish/Catalan titles, later evaluation. Different phase dates do not necessarily conflict. |
| [02](../../data/samples/02_deltebre_deadlines_budget/) | Deltebre `4390180001-2024-0010219` | Ten observations; repeated deadline changes and budget 162,565.20 → 177,465.20, then award/formalization. Same procedure, different states. |
| [03](../../data/samples/03_bsm_budget_jump/) | BSM `2024PT0235AC` | Budget representation 2,000 → 53,000; deadline extensions; rich corrected tender notice exists in addition to PLACSP's sampled states. Treat as a material assertion change; do not infer its legal cause from amount alone. |
| [04](../../data/samples/04_expediente_renamed/) | Institut de Cultura de Barcelona `24001098` → `006_24001098` | Same Atom ID 15581446 and procedure UUID; both representations resolved, two lots. Preserve identifier aliases. |
| [05](../../data/samples/05_thirteen_lots/) | `ME. MEC-25L02`, UUID `f98c30c1-1327-4dfc-b38a-5b707e9adf41` | 13 lots, 25 observations, 13 Gencat rows. Row suffixes differ from official lot numbers. Repeated procedure budgets cannot be summed. |
| [06](../../data/samples/06_cancelled_olot/) | Olot `CCS12024000095`, PLACSP 16219472 | ANUL observation and dedicated origin annulment publication 300344003. Keep cancellation notice separate from preceding corrected tender notice 300343988. |
| [07](../../data/samples/07_equivalent_projection/) | `C 06/2022 Exp Actio núm 8100810007-2022-0000245`, PLACSP 10051590 | Same current publication 300701712; net budget 815,892.10, estimate 1,631,784.20, deadline 2022-06-10 12:00 and winner B43672138 align. Strong same-publication, same-comparable-fields example, not proof of complete bytewise state equivalence. |
| [08](../../data/samples/08_precision_and_lot_result/) | Aran `1262-0001/2023`, PLACSP 12253314 | 23:59:59 versus 23:59:00; five lots; lot 5 has Desert and its own publication while procedure phase remains evaluation. Separate precision and lot outcome. |
| [09](../../data/samples/09_withdrawal_retains_award/) | TMB `13794496`, PLACSP 10275923 | Same publication 300694438: PLACSP RES/result 5/RENUNCIA, Gencat Anul·lació/Renúncia retaining winner A58846064 and old award 83,996.64. Do not erase historical award or translate RES to successful completion. |
| [10](../../data/samples/10_two_placsp_ids/) | CatSalut `SCS-2025-122`, UUID `00c79486-0c0d-41f8-8ed6-2097f449a999` | Atom IDs 16638290 and 16638580 point to the same procedure. Formalization date 2024-12-13 precedes February 2025 publications. One-to-one Atom-ID assumptions fail. |
| [11](../../data/samples/11_buyer_reassignment/) | `PR-2025-7`, PLACSP 15314304 | PLACSP and historical rich notice name Presidència/202037; current Gencat row names Justícia/202266 for the same UUID. Reassignment is plausible, its cause not proven. Distinguish historical issuer from current administration. |
| [12](../../data/samples/12_award_only_placsp/) | `AG-2023-29`, PLACSP 13416259 | The selected Gencat cohort contains six lot rows, while the retained PLACSP representation contains award information not present in those selected rows. This is complementary selected-cohort evidence, not proof the entire Gencat source lacks those awards. |
| [13](../../data/samples/13_timestamp_disagreement/) | Puigverd d'Agramunt `11741_2026_32`, PLACSP 20350694 | PLACSP still links 300869210 with August updated time; table phase date and JSON link identify September correction 300885950. Same table source URL does not imply every column belongs to that old publication. |
| [14](../../data/samples/14_batch_is_not_procedure/) | XALOC batch 300339416 | Six contract rows under one UUID/URL; multiple contracts share `2023/800`. Reject a batch-UUID-as-procedure key. |
| [15](../../data/samples/15_duplicate_lot_number/) | Sabadell `URB/2022/164` | Two source-row IDs claim lot 3, different publications. Do not deduplicate on `(UUID, lot number)` without inspecting rich source identity/history. |
| [16](../../data/samples/16_parent_and_lots_different_phases/) | Diputació de Girona `2026/7731` | Parent future-alert row has no expediente; five child lot rows have tender phase and expediente. A source procedure can have simultaneous heterogeneous projections. |
| [17](../../data/samples/17_expediente_collision/) | Both `1/2025`: Ars and INTERHOSPITALIA 2 | Different buyers, UUIDs and works/waste-service objects. Clear different-procedure pair despite exact expediente equality. |
| [18](../../data/samples/18_fuzzy_false_friend/) | `288/2024`, PLACSP 15632941 versus UUID `5d96c294-93f0-4d38-8047-20f01b34d846` | Buyer-name similarity 0.8302 but title similarity 0.0132 and unequal budgets. Reject automatic matching; a weak fuzzy threshold yields a false friend. |
| [19](../../data/samples/19_execution_modifications/) | Vila-seca `4317110007-2021-0001388` | Two 2026 modifications in a single publication, much later source-row timestamps, no selected main-table row. Need execution ingestion and distinct business/knowledge times. |
| [20](../../data/samples/20_multiple_winners_empty_amounts/) | Aigües de Manresa `9884AM` | Multiple suppliers, empty `||` amount tokens, six lot rows and legacy XML recovered through a JSON-named endpoint. Keep cardinality, missingness and format distinctions. |

# 4. Proposed common normalized schema

## 4.1 Domain boundaries

This proposal follows the observations above. It is **not a union of source columns** and is not an implemented production database.

Use a stable **ProcurementProcess** for an identified procurement activity, with `kind` distinguishing competitive procedure, direct award, framework call-off, planning activity, market consultation and unresolved process type. A legal contract is a separate entity. A planning object can later relate to a procedure without pretending that every planning row was already a tender. Publication batches are also separate subjects.

```text
Acquisition -> RawArtifact -> SourceObservation -> FieldAssertion
                                      |                  |
                                      v                  v
                          SourceIdentityLink      ReconciliationDecision
                                      |                  |
                                      v                  v
ProcurementProcess -- Lots -- Awards -- Contracts -- ExecutionActions
         |               \          /
         +-------- NoticeSubject --- Notice -- DocumentVersion
         |
         +--- CanonicalRevision --- RevisionEvidence

PublicationBatch -- BatchMember --> Contract / unresolved procurement object
Organization -- role assignments --> process, award, contract, notice
```

Notice-to-subject is a relation, not a single compulsory tender foreign key: a batch notice concerns multiple contract entries; a notice can concern several lots; one execution publication can report several actions. A notice from another procurement platform can reuse the same domain entities without being forced into the Atom entry shape; this is a general modeling consideration, not a commitment to an additional TenderWatch source.

## 4.2 Shared types and missingness

| Type | Concrete representation / semantics |
|---|---|
| `ID` | Locally generated UUID; never a source expediente string |
| `ExternalIdentifier` | `{scheme, issuer, value_raw, value_normalized?, entity_kind, scope?, valid_period?, evidence}`; value/issuer/scheme/entity kind required |
| `Code` | `{system_uri, version?, code, label?, raw}`; keep unknown codes instead of silently mapping them to a default |
| `LocalizedText` | `{language?, text}`; preserve original language and text; use a separate comparison key |
| `TypedLocation` | `{role, granularity, codes: Code[], name?, address?, coordinates?, raw_text?}`; role/granularity required, including explicit unknown; buyer address, jurisdiction and execution location remain distinct |
| `IdentifierAssertion` | ExternalIdentifier plus observation/evidence reference and optional asserted validity interval; supports renamed expediente aliases without rewriting source identity |
| `Money` | `{amount: decimal-string, currency: ISO4217?, purpose, tax_basis, subject_scope}`; amount/purpose/tax basis/scope required when an amount assertion exists; never binary float |
| `TemporalValue` | `{raw, local_date?, local_time?, utc_instant?, offset?, zone_assumption?, precision, role}`; raw/precision/role required; date-only is not midnight; timezone assumptions are explicit |
| `ValueState<T>` | `{availability: value/not_provided/explicitly_empty/not_applicable/redacted/invalid, value?: T}`; null is not deletion and an omitted array is not necessarily an empty complete set |
| `EvidenceRef` | Observation ID plus exact JSON Pointer/XML path/array position or raw byte locator, extraction version and optional source notice ID |

For Gencat, currency may be unknown in a bare table row. EUR can be asserted from an authoritative notice or documented dataset convention; it must not become a universal parser default for future countries. CPV normalization may separate its check digit, but must retain the original and validation outcome. NUTS needs its version and geographic role. Zero-valued monetary amounts remain zero until evidence shows a source sentinel or correction.

## 4.3 Concrete entities and fields

`1` means required singleton; `0..1` nullable singleton; `0..N` optional collection; `1..N` required nonempty collection. Mutable business values are projections of assertions, not destructive updates to the only copy of a fact. Every mapped business field carries assertion/evidence links described in §4.5.

### A. Stable identity and relationships

| Entity.field | Type / cardinality | Semantics and source mapping / normalization |
|---|---|---|
| Process.id | ID / 1 | Internal stable identity assigned after entity-resolution decision |
| Process.kind | Code / 1 | Procedure/direct-award/planning/etc.; unknown allowed, not default “open tender” |
| Process.external_identifiers | ExternalIdentifier / 0..N | Scoped PLACSP Atom IDs, ordinary PSCP UUIDs and other namespaced official process IDs supplied by the sources; batch UUID excluded from procedure identities |
| Process.procedure_numbers | IdentifierAssertion / 0..N | `ContractFolderID`, `codi_expedient`; retain aliases, issuer and observed validity rather than overwriting renamed numbers |
| Process.relationships | `{other_process_id, kind, evidence}` / 0..N | Framework call-off, successor/republication, joint procurement, planning-to-procedure; do not merge solely because related |
| SourceIdentityLink | `{source_identifier, canonical_subject_id, subject_kind, decision_id}` / 0..N | Explicit mapping of typed source objects to a canonical identity; retains multiple aliases and unresolved candidates |
| EntityResolutionDecision | `{id, candidate_subjects, outcome, method, rule_version, evidence_ids, decided_at, confidence?, supersedes?}` / 1 per decision | Required ID, candidate subjects, match/non-match/unresolved outcome, method, rule version, evidence and UTC decision time; confidence and superseded decision nullable. Independent from field/state reconciliation and reversible after new evidence. |
| Lot.id | ID / 1 | Internal identity; not forced to source number |
| Lot.process_id | ID / 1 | Exactly one owning process |
| Lot.external_identifiers | ExternalIdentifier / 0..N | Source lot IDs, `numero_lot`, rich publication lot IDs; `id_intern` suffix kept only as a row alias |
| Lot.number | string / 0..1 | Display number; need not be unique until source anomalies resolved; do not invent a lot for absent/zero markers |
| Party.id / Party.kind | ID / 1; enum / 1 | Base actor identity: organization, individual, consortium or unknown. Organization below is its organizational subtype; do not infer legal form merely from a NIF-like string. |
| Organization.id | ID / 1 | Organizational Party identity used for public buyers and organizational suppliers |
| Organization.identifiers | ExternalIdentifier / 0..N | NIF/CIF, DIR3, PSCP `codi_organ`, source `ID_OC_PLAT`; namespace by issuer/platform; flag placeholders |
| Organization.names | LocalizedText / 0..N | Current and historical names, aliases, language and evidence |
| Organization.addresses | TypedLocation / 0..N | Registered/contact address; separate from execution place |
| OrganizationMembership | `{group_id, member_id, role?, period?, evidence}` / 0..N | UTE/consortium membership when known; do not split a group ID into invented companies |
| PartyRoleAssignment | `{organization_id, subject_id, role, valid_period?, evidence}` / 0..N | Buyer, current administrator, historical issuer, winner, joint bidder; handles case 11 |
| PublicationBatch.id | ID / 1 | Identity of an aggregate publication grouping |
| PublicationBatch.external_identifiers | ExternalIdentifier / 1..N | Aggregate UUID/numeric notice identity, explicitly typed as batch |
| BatchMember | `{batch_id, source_member_id?, ordinal?, contract_id?, process_id?, evidence}` / 1..N per batch | Individual aggregate entry; unresolved linkage is allowed instead of forcibly merging repeated expedientes |

### B. Mutable business assertions

| Subject.field | Type / cardinality | Semantics and source mappings |
|---|---|---|
| Process/Lot.title | LocalizedText / 0..N | Atom/project name, `denominacio`, rich language variants; whitespace comparison does not delete originals |
| Process/Lot.description | LocalizedText / 0..N | `objecte_contracte`, rich descriptions and applicable CODICE text |
| Process.procedure_type | Code / 0..1 | TenderingProcess/ProcedureCode or `procediment`, preserving source code and mapping version |
| Process.contract_type | Code / 0..1 | Works/services/supplies/etc.; keep mixed-contract indicators separately |
| Process/Lot.classifications | `{Code, role}` / 0..N | CPV and future classifications; scope/main/additional status preserved |
| Process/Lot.amounts | Money assertions / 0..N | Budget net/gross, estimated value; source procedure and lot paths mapped explicitly, never summed indiscriminately |
| Process/Lot.submission_deadlines | `{kind, TemporalValue}` / 0..N | Offers, participation requests and lot-specific deadlines; select the relevant active deadline in a search projection |
| Process/Lot.execution_locations | TypedLocation / 0..N | NUTS, country, municipality, address or free text with role=execution; retain granularity and unknowns |
| Process/Lot.performance_period | `{start?, end?, duration?, raw}` / 0..1 | Date interval or duration; don't manufacture dates from duration alone |
| Process/Lot.status_assertions | `{dimension, code, notice_id?, time?, evidence}` / 0..N | Dimensions include publication phase, submission availability, competition outcome and execution state |
| Process/Lot.requirements | `{category, structured_value?, text?, document_ref?, evidence}` / 0..N | Eligibility/award criteria/technical requirements where mapped; unknown detail remains recoverable in raw artifacts |
| Process/Lot.document_relations | `{document_version_id, purpose, notice_id?, status}` / 0..N | Specifications, addenda, minutes, corrections; source disappearance alone does not retract a document |

A convenience `TenderView.status` can be derived for search, but it must not replace the multidimensional process/lot assertions. A procedure can have one lot deserted and others under evaluation or awarded.

### C. Publications, awards, contracts and execution

| Entity.field | Type / cardinality | Semantics and source mappings |
|---|---|---|
| Notice.id | ID / 1 | Internal notice/publication identity |
| Notice.external_identifiers | ExternalIdentifier / 0..N | Numeric PSCP publication ID, native official notice ID and other official notice identifiers supplied by the sources; date/type without ID is a weaker reconstructed reference |
| Notice.type | Code / 0..1 | Tender notice, award, formalization, correction, annulment, etc.; preserve source-specific type |
| Notice.publication_at | TemporalValue / 0..1 | Actual public release; media-specific dates may require child publication occurrences |
| Notice.planned_publication_at | TemporalValue / 0..1 | Rich `dataPublicacioPlanificada`, never substituted for actual date |
| Notice.media_occurrences | `{medium, identifier?, publication_at?, sent_at?, evidence}` / 0..N | Repeated CODICE publication media/references, not a unique `(medium,date)` assumption |
| Notice.relations | `{related_notice_id, kind, evidence}` / 0..N | Corrects/replaces/withdraws/supplements; use explicit relation if available, otherwise mark inference |
| Notice.correction_reason | LocalizedText / 0..N | `tipusEsmena`/`motiuEsmena`; not a new procedure |
| NoticeSubject | `{notice_id, subject_id, subject_kind, relation_role}` / 1..N per resolved notice | Procedure, lot, award, contract, batch or execution action |
| Award.id / process_id | ID / 1 each | Award fact or decision, not its notice |
| Award.lot_ids | ID / 0..N | Empty/unknown scope distinguished; do not fabricate a lot zero |
| Award.decision_at | TemporalValue / 0..1 | `data_adjudicacio_contracte` or explicit CODICE award date |
| Award.outcome / status | Code / 0..1 each | Positive award, unsuccessful, withdrawn, superseded, disputed; historical awards survive later outcomes |
| Award.amounts | Money / 0..N | Award totals or per-winner shares only when scope is explicit |
| AwardParty | `{award_id, party_id?, role, share?, source_position?, evidence}` / 0..N | Multiple winners and incomplete parallel arrays; party may be organization, individual or consortium. Unknown identity allowed with preserved raw party assertion; identifiers and names use the same evidence-bearing types as organizations. |
| Contract.id / process_id | ID / 1 each | Legal contract distinct from procurement process and award notice |
| Contract.award_ids / lot_ids | ID / 0..N each | Relationships may be unresolved in coarse table rows |
| Contract.external_identifiers | ExternalIdentifier / 0..N | Contract number/member identifier where supplied |
| Contract.formalized_at | TemporalValue / 0..1 | Signing/formalization fact, separate from Notice.publication_at |
| Contract.amounts / performance_period | Money / 0..N; period / 0..1 | Original and modified assertions distinguished by action and valid time |
| ExecutionAction.id | ID / 1 | Action identity independent of publication |
| ExecutionAction.contract_id / process_id / lot_ids | ID / 0..1; ID / 1; ID / 0..N | Contract link optional until resolved |
| ExecutionAction.external_identifiers | ExternalIdentifier / 0..N | Rich `identificador` scoped to its owning subject/type, not globally unique |
| ExecutionAction.type / action_at / end_at | Code / 1; TemporalValue / 0..1 each | Modification, extension, termination, suspension, etc.; execution-table `data` is action time |
| ExecutionAction.amounts / details | Money / 0..N; typed assertions / 0..N | Action amount is not automatically replacement total budget |
| DocumentVersion.id | ID / 1 | Immutable document representation identity |
| DocumentVersion.source_ids / urls | ExternalIdentifier / 0..N; URI / 0..N | Original URI retained, normalized target identity separate |
| DocumentVersion.title / language / media_type | string / 0..1 each | Names, language and actual/declared format |
| DocumentVersion.reported_hash / content_sha256 | `{algorithm?, value}` / 0..1; hex / 0..1 | Source hash is not a locally verified SHA-256. Content SHA only when bytes acquired |
| DocumentVersion.raw_artifact_id / size_bytes | ID / 0..1; integer / 0..1 | Allows known metadata without claiming binary acquisition |
| SourceAvailabilityEvent | `{source_object_id, kind, source_time?, observation_id}` / 0..N | ANULADA/CERRADA/tombstone/access failure, separately interpreted from legal lifecycle |

### D. Source and observation metadata

| Entity.field | Type / cardinality | Semantics |
|---|---|---|
| Source.id / dataset_id / origin_source_id | string / 1; string / 0..1; string / 0..1 | Transport dataset and originating authority/platform distinguished; aggregation is not independent corroboration |
| Acquisition.id / source_id | ID / 1; string / 1 | One retrieval attempt, with status and request parameters |
| Acquisition.request_url / resolved_url / parameters / headers | URI / 1; URI / 0..1; object / 1; object / 0..1 | HTTP lineage; avoid retaining authentication headers in a production ledger |
| Acquisition.started_at / observed_at | UTC instant / 1 each for completed retrieval | Request start and completed response receipt; optionally first-byte time separately |
| RawArtifact.id / sha256 / storage_uri / byte_length / media_type | ID / 1; hex / 1; URI / 1; integer / 1; string / 0..1 | Immutable bytes; many acquisitions may retrieve the same artifact |
| SourceObservation.id / acquisition_id / raw_artifact_id | ID / 1 each | Extracted record occurrence; independent from stable source-object ID |
| SourceObservation.locator | structured locator / 1 | ZIP member + ordinal/byte range, or JSON page + array index; makes any extraction reproducible |
| SourceObservation.source_object_id | ExternalIdentifier / 0..1 | Atom ID, table row ID or notice ID according to record kind |
| SourceObservation.record_kind | Code / 1 | Procedure snapshot, lot projection, batch member, notice body, execution-action projection, tombstone |
| SourceObservation.source_created_at / source_updated_at | TemporalValue / 0..1 each | Source-record technical/change times, with source-specific semantics; absent is permitted |
| SourceObservation.ingested_at / extraction_version | UTC instant / 1; string / 1 | When our parser accepted it and which parser/mapping produced assertions |
| SourceObservation.content_hashes | `{purpose, algorithm, version, value}` / 0..N | Raw-byte, XML-tree, normalized-projection hashes are not interchangeable |
| SourceObservation.completeness / validation_issues | scoped coverage claims / 0..N; issues / 0..N | Which collections/fields were actually supplied or known complete; preserve invalid values |

## 4.4 Temporal model

Keep **knowledge time** and **business time** separate:

- `observed_at`: when this system actually received the source representation, from acquisition metadata.
- `ingested_at`: when this system parsed/accepted that observation; can be later than receipt.
- `source_created_at`: creation of the source record object, if exposed. Socrata row creation is not process creation.
- `source_updated_at`: source's update marker, qualified by record kind. PLACSP entry updated and Socrata row updated are not one universal clock.
- `publication_at`: actual release of a particular notice; a single observation may reference many such dates.
- `planned_publication_at`: explicitly planned release, never promoted to actual release without evidence.
- `effective_at` / valid interval: when a particular decision or contract action legally/business-wise applies, **only when the source states it**. Do not infer it from whichever timestamp is newest.
- `action_at`, `award_decided_at`, `contract_formalized_at`, `deadline_at`: typed business roles rather than generic event dates.
- `reconciled_at`: when our system produced a canonical revision.

Field assertions may carry both an asserted business-valid interval and a knowledge interval beginning at observation/ingestion. Unknown valid-time bounds remain unknown. A late correction can change our present understanding of an earlier state without making an old notice the current business state. Reported date-only values and minute-level values retain precision, not fabricated seconds. DST-ambiguous floating times require an uncertainty flag or supporting offset-bearing publication.

## 4.5 Field provenance and canonical revisions

Store **FieldAssertion** records with required `assertion_id`, `subject_id`, `field_path`, `value_state`, `observation_id`, `source_locator`, `extraction_version`; optional `notice_id`, `business_valid_from/to`, `confidence` and `normalization_notes`. A multi-source corroboration links several assertions to one chosen canonical value; it must not overwrite the original assertions.

**ReconciliationDecision** requires subject/field, candidate assertion IDs, selected assertion ID(s) or unresolved status, rule version, reason and decision time. Conflicting rejected candidates remain queryable.

**CanonicalRevision** requires `revision_id`, `process_id`, `reconciled_at`, predecessor revision ID except for the first, canonical projection, semantic-hash algorithm/version and hash, reconciliation-policy version and evidence/decision links. Optional fields include effective-time bounds, completeness warnings, conflict flags and a categorized material diff. Source revisions, parser revisions and canonical business revisions are distinct.

A deadline example would retain:

```yaml
subject: process:4b131001-63ad-4eac-a80a-ab91c3a9f366
field: submission_deadlines.offers
value: 2026-09-14T12:00:00Z
precision: second
selected_evidence:
  source: gencat_publication
  publication_id: '300885987'
  raw_file: data/raw/gencat/phases/300885987.json
  pointer: /publicacio/dadesPublicacio/dataTerminiPresentacioOSolicitud
corroboration:
  placsp_local_value: 2026-09-14T14:00:00
  table_local_value: 2026-09-14T14:00:00.000
timezone_interpretation: Europe/Madrid
```

This is an illustrative canonical assertion backed by the sample, not a claim that all records have already been normalized into that model.

# 5. Possible reconciliation strategies

## 5.1 Problem A: entity resolution

### Observed overlap and denominators

The primary comparison is the **187,273 selected aggregation observations / 57,311 Atom IDs**, against the **88,077 ordinary Gencat rows / 66,491 ordinary procedure UUIDs**. Aggregate Gencat batch UUIDs are excluded from procedure-UUID matching.

| Matching measure | Observed value |
|---|---:|
| PLACSP Atom IDs with an explicit ordinary PSCP UUID match | 56,310 |
| PLACSP observation occurrences with such a match | 186,109 |
| Distinct matched Gencat ordinary UUIDs | 55,997 |
| Share of selected aggregation Atom IDs explicitly linked | **98.2534%** |
| Share of Gencat ordinary procedure UUIDs linked to the aggregation cohort | **84.2174%** |
| Additional unique buyer + exact expediente candidate | 1 |
| Additional unique buyer + punctuation-normalized expediente candidates | 3 |
| No candidate from those exact/composite tiers | 997 |

The extra four are **candidates, not confirmed additional procedures**. Native-feed results are reported separately in the full metrics. The 84.22% denominator includes Gencat minor contracts/planning and different source/time coverage. It is not a statement that PLACSP lost the other 15.78%.

**What cannot be estimated here:** the percentage of *all truly overlapping legal procedures* reconciled correctly. The true overlapping population was not independently labelled. The percentages above measure explicit linkage coverage in specified cohorts, not recall or precision. The twenty case studies establish concrete behavior and counterexamples, not statistical accuracy.

### Tier 1: explicit source identity, with type and scope guards

1. Match an explicit ordinary PSCP procedure UUID in the PLACSP source URL to rich `idExpedient` / the ordinary table UUID.
2. Match an explicit notice ID to its authoritative parent procedure where that parent relation is known.
3. Use an official cross-source identifier/cross-reference that is semantically a procedure identifier, not a batch, lot, buyer or notice.
4. Consolidate multiple PLACSP IDs pointing to that same ordinary procedure, retaining all source aliases and evidence.

This establishes identity of the same official **source object** with high confidence. It does not make corrupt source data impossible or settle every legal successor/continuation question. A conflicting buyer ID warrants inspection, but case 11 demonstrates why it does not automatically disprove identity when the official procedure UUID agrees.

**Never apply this tier to aggregate UUIDs without resolving batch members.** Never use a URL's numeric publication ID as the procedure ID. Never assume a source identifier is globally unique without its dataset/platform namespace.

### Tier 2: exact/normalized composites

Use `(origin platform, buyer official ID, exact expediente)` as a strong candidate key when all components are meaningful, nonempty, scoped correctly and one-to-one. Check year/context, title, amounts, notice chronology, lot structure and any contradicting explicit UUIDs.

The current ordinary Gencat snapshot has no non-null exact-composite collision, but the larger domain contains aggregate collisions and **159 observed expediente renamings**. Therefore promote a composite to deterministic linkage only under a documented scoped uniqueness policy with collision monitoring and no stronger contradictory identifier. Do not normalize away leading zeroes, year components or meaningful suffixes. Punctuation-stripped values should be secondary candidate keys, not replacements for original identifiers.

A shared NIF can be valuable after enrichment, but a tax entity can contain several contracting units. DIR3 placeholder `A9999999` and similarly invalid IDs must be excluded. Numeric `ID_OC_PLAT` only matches `codi_organ` within the relevant origin platform's namespace.

### Tier 3: fuzzy candidates, not automatic merges

An exploratory blocker uses punctuation-normalized expediente and retains unmatched pairs when buyer-name or title `SequenceMatcher` similarity is at least 0.8. Across both selected PLACSP feeds it produced **12 candidate pairs involving 11 Atom IDs**, including one native-feed candidate. Its candidate list and scores are preserved in `analysis/fuzzy_candidates.json`. This is deliberately an **uncalibrated recall-oriented experiment**; no pair is automatically merged.

Case 18 demonstrates why 0.8 buyer similarity is unsafe by itself. Conversely, Spanish/Catalan translations can have low lexical similarity for a true match. For a future matcher, require combinations of buyer identity/name, number aliases, multilingual title, scoped amount, CPV, time and geography, and calibrate thresholds on an independently labelled set of positive and hard-negative pairs. Amount equality and a common CPV are not enough. Location is weak identity evidence. Embeddings might help cross-language candidate retrieval, but there is no demonstrated need for them to resolve the overwhelming explicit-UUID overlap here.

Explicit different buyers and incompatible objects, aggregate-member ambiguity, contradictory strong identifiers, missing discriminating fields and tied candidates must block automatic merges. Keep unresolved links and reversible merge/split decisions.

## 5.2 Problem B: duplicate observation, equivalent state or evolution

Once identity is established, classify **observations and assertions**, not only whole records:

| Classification | Evidence needed | Action |
|---|---|---|
| Duplicate acquisition/observation | Same byte artifact and locator, or validated identical source representation | Record retrieval lineage; no business revision |
| Equivalent normalized projection | Same identified publication/subject, compatible precision and equal compared fields | Add corroborating provenance; do not claim unseen fields equal |
| Newer business state | Explicit successor/correction/action relation or compatible publication/business chronology with material changes | Reconcile affected fields; create material revision if resulting state changes |
| Older/historical observation | Earlier identified notice/state arriving later | Enrich historical knowledge without reverting current fields |
| Complementary data | Same subject with non-conflicting fields previously unreported | Add assertions; distinguish business enrichment from material change |
| Conflict | Competing values for same subject, fact role, scope and relevant time | Retain alternatives; resolve by documented policy or mark unresolved |
| Source availability change | Tombstone, archive closure, transient missing row | Update source availability; do not infer cancellation without the right semantics |

In the aggregation cohort, **50,115 latest Atom-ID projections share their latest publication ID with at least one ordinary Gencat row**; **6,195 have different latest publication IDs**. Comparing a matching-publication row where possible:

- Net procedure budget: **49,605 equal**, **510 not comparable because missing**, **0 different** among the same-publication group.
- Procedure estimate: **50,113 equal**, **2 missing**, **0 different**.
- Deadline: **34,167 exactly equal**, **6,099 missing**, **9,849 different strings**. Of the differences, **9,846 are seconds-only** and **3 extend beyond seconds**.
- **33,831** share that publication and have all three compared fields present and exactly equal.

This is useful evidence for H2 but **not 33,831 proven equivalent complete tender states**. The comparison is a declared three-field projection, uses numeric money values without a Gencat currency column, and does not compare every lot, document, requirement or winner. The representative Gencat row is selected reproducibly, preferring the matching publication ID; other rows can carry different phases or lot outcomes. A correct future reconciliation must inspect all applicable subjects, not just this research projection.

For different latest publications, there are eight net-budget differences and eight estimated-value differences in the representative comparison. Some are genuinely older/newer assertions; others can result from retaining a planning parent alongside later lot rows. Do not turn this count into a confirmed data-error rate.

## 5.3 Field-level conflict policy

Do **not** implement global `latest timestamp wins`. Use this order of reasoning:

1. **Align identity, scope and fact role.** Procedure budget is not lot budget; historical issuer is not current administrator; award decision date is not notice publication.
2. **Establish the relevant notice/action and its relationship.** A correction can supersede only certain fields, while an award or execution action does not necessarily replace tender requirements.
3. **Prefer the originating authoritative publication for what it actually states.** For a PSCP procedure, rich official PSCP publication data can justify a deadline or correction reason over a lossy table/aggregation projection. For a native PLACSP procedure, the native official publication is the corresponding origin. There is no source-wide “Gencat always wins” rule.
4. **Use source technical update time only for source representation freshness**, not as evidence of later business effect. Preserve same-timestamp hash changes and late older notices.
5. **Account for precision and completeness.** Rich `23:59:59` versus minute-level `23:59:00` is not automatically a change. A missing value is not an instruction to erase a more complete historical fact.
6. **Retain unresolved contradictions.** A rule should record candidate values, selected value or unresolved status, evidence and policy version. Do not silently choose because one value is non-null or one platform is generally considered better.

Examples:

- **Deadline X vs Y:** find the latest applicable tender/deadline correction for the relevant procedure/lot; compare its explicit deadline, timezone and precision. If source notice ordering is unknown, surface conflict rather than guessing. A phase published after the deadline may correct opening information only.
- **Budget:** compare matching scope/tax basis/currency. Preserve a zero assertion rather than treating zero as missing. Do not replace a procedure total with one lot or an execution modification delta.
- **Buyer:** retain the buyer that issued the historical notice. A current table reclassification may justify a separate current-administrator assertion, not a rewrite of the old notice.
- **Winner after withdrawal:** retain the historical award and mark its subsequent outcome. Case 09 makes neither “remove all award history” nor “winner means still awarded” valid.
- **Document changes:** compare stable source document IDs and reported hashes, then binary content hashes if downloaded. An encrypted delivery path changing alone does not prove a new specification. New requirements inside an unchanged URL require content-aware monitoring; that was not measured exhaustively here.

PLACSP's Catalan aggregation is downstream of PSCP, so agreement is generally **not two independent authorities voting for the same value**. Track origin lineage to avoid double-counting corroboration.

## 5.4 Canonical revision creation and semantic hashing

Use at least three separate fingerprints:

1. **Raw hash:** SHA-256 of actual bytes; acquisition integrity and exact duplicate detection.
2. **Normalized observation/projection hash:** parser-versioned comparison of one source representation; useful for formatting noise, not proof of business identity.
3. **Canonical semantic hash:** policy-versioned material projection of the selected business state, **after** entity resolution and field reconciliation.

Candidate material fields include relevant deadline and precision, scoped budget/estimate, meaningful status/outcome, lot structure, awards and their status, applicable requirements, and official document versions. Generate a new canonical business revision when that projection changes. Store a structured diff and assertion provenance for every changed field.

Normally exclude retrieval times, HTTP headers, Socrata technical timestamps, insignificant whitespace, known unordered-set order, encrypted URL transport tokens and equivalent decimal spelling. Do not indiscriminately lowercase legal identifiers/text or sort arrays whose positions align winners and amounts. Excluding a document's content from a hash risks missing requirement changes; including unstable URLs risks false positives. Hash policy must be versioned and tested on the real cases.

A new official notice can deserve its own notice-history entry even if it causes **no material canonical state change**. Conversely, an in-place correction can change a canonical value without a new notice ID or source timestamp. Preserve audit/provenance updates even when the business hash remains unchanged. Do not manufacture a business revision just because a new source starts reporting an already-known value.

Late historical data can trigger a new **knowledge/reconciliation revision** or improved reconstructed past state without regressing the latest business state. Model canonical revisions as immutable system decisions with business-time annotations, rather than equating their ordinal with official lifecycle order. Retain merge/split and mapping-policy provenance so incorrect consolidation can be reversed.

## 5.5 Requirements for a future reliable ingestion system

The research supports these requirements, not a production implementation:

- Separate connectors for native PLACSP, origin-platform aggregation, PSCP main rows, rich modern/legacy notices and execution actions.
- Immutable acquisition artifacts; HTTP validators; retries/backoff; durable pagination checkpoints; checksum validation; source snapshot/version consistency checks.
- Namespace-aware XML and content-aware format detection; dynamic code lists and explicit unknown-code handling.
- Different incremental strategies by source. Atom change cursors need overlap/revalidation to catch same-timestamp corrections. Socrata `:updated_at` needs reload detection and must not be used as lifecycle order.
- Periodic reconciliation/backfill, including old notices referenced by newly changed procedures, rather than only “new tenders since yesterday.” When a procedure or lot changes, fetch its companion rows/lots even if their own publication dates fall outside the incremental window. Otherwise the date filter itself creates incomplete procedure states, as the selected-cohort limitation in case 12 illustrates.
- Explicit source availability/history coverage and retention gaps; source deletion never physically erases all evidence.
- Scoped identity indexes and reversible entity-resolution decisions, including batches, lots, organizations and notices.
- Field-level provenance, origin authority rules, precision-aware temporal values, decimal amounts, current/historical projections and conflict reporting.
- Independent tests for entity resolution, notice equivalence and material-revision generation. A notification system should consume reviewed material diffs later; it is not part of this investigation.

# 6. Hypothesis validation

| Hypothesis | Result | Evidence | Confidence |
|---|---|---|---|
| H1 — Cross-source overlap | Confirmed | 56,310 selected aggregation Atom IDs explicitly link to 55,997 ordinary Gencat UUIDs; numerous manually inspected cases | High for this cohort; not a complete legal-procedure census |
| H2 — Equivalent state across sources | Partially confirmed | 50,115 latest ID projections share a publication ID; 33,831 also match all three tested fields; case 07 adds aligned winner/outcome evidence | High for shared publication and compared facts; moderate/unknown for complete-state equality |
| H3 — Tender lifecycle creates multiple changes | Confirmed | Deltebre's ten observations and recovered notices, BSM changes, 13-lot history; widespread measured changes | High that evolution exists; number of actual material events not equal to row count |
| H4 — Incomplete or complementary histories | Confirmed, with scope qualification | PLACSP's documented non-exhaustive retention; Gencat correction JSON not represented by some latest PLACSP entries; execution-only selected case; retained historical winner versus latest withdrawal result | High for complementary representations; source-wide absence requires wider historical queries |
| H5 — Deterministic entity resolution possible in some cases | Confirmed | Explicit ordinary PSCP UUID and notice-parent links; same UUID corroborated by buyer/expediente and rich bodies | High for official-object linkage; exact composite keys are conditional, not universally safe |
| H6 — Same state vs different state distinguishable | Partially confirmed | A: case 07 comparable-state match; B: case 02 deadline/budget evolution; C: case 17 different buyers/procedures despite same expediente; seconds-only and lot-scope ambiguities remain | High for reviewed classifications, incomplete for a general fully automatic classifier |
| H7 — Arrival order may differ from semantic order | Partially confirmed | Historical notices retrieved after newer ones; execution actions dated March/August published together later; 2026 technical row dates for much older business facts; source-clock disagreements | High that timestamps/order are non-equivalent; spontaneous live cross-source arrival disorder was not measured longitudinally |

Specific simplistic assumptions rejected by the evidence:

- `one publication = one version` and `one source row = one event`;
- one universal UUID or one expediente string as a procedure key;
- one PLACSP Atom ID per origin procedure without duplicates/aliases;
- a latest phase label uniformly describing all rows/lots;
- every `url_json_*` returning JSON;
- every Atom page respecting the advertised 500-entry maximum;
- timestamp equality implying content immutability;
- `RES = successful contract completion`, `Anul·lació = only PLACSP ANUL`, or `CERRADA = cancellation`;
- source-table creation/update time as the business lifecycle clock;
- exact deadline-string inequality always representing a material change;
- absence of a main-table selected row as absence of a procedure or execution activity;
- a source record's extra information justifying a blind overwrite of a more authoritative, differently scoped fact.

# 7. Open questions / next experiments

## 7.1 Highest-value unresolved questions

1. **Longitudinal corrections and natural arrival order.** Poll frozen IDs and overlapping Atom pages across several source releases; compare bytes, IDs, timestamps and notice bodies. Measure genuine first-seen delays rather than treating source-clock subtraction as network latency. No same-ID/same-timestamp correction was demonstrated by repeated snapshots in this run.
2. **Batch-member and lot identity stability.** Revisit selected `id_intern` suffixes and rich lot/action identifiers after corrections and reordering. Determine which survive source regeneration. Investigate Sabadell's duplicate lot 3 before choosing any uniqueness constraint.
3. **Publisher clarification on dates.** Confirm systematic minute truncation, floating-time timezone policy, whether rich publication bodies can change under stable notice IDs, and why table source URLs can lag phase JSON links.
4. **PL aggregation gaps and duplicated identities.** Explain the CatSalut multiple-Atom-ID groups, quantify source/platform-specific transmission behavior, and investigate why selected corrections are absent from the retained aggregation timeline. Do not assume every absent record is a transport failure.
5. **Independent matching evaluation.** Label a stratified random set and hard negatives, including unmatched ordinary minor contracts, buyer reassignment, renamed expediente numbers, batches, repeated annual numbers and multi-lot procedures. Only then estimate precision/recall and calibrate fuzzy thresholds.
6. **Full history reconstruction.** Explore officially supported notice-history enumeration and snapshot archives; distinguish the latest per-phase links from all historic corrections. Compare monthly versus annual PLACSP archives to test whether monthly snapshots preserve additional historical representations; their equivalence was not established here. The direct numeric-ID endpoint recovered known historical notices, but this does not prove an exhaustive enumeration mechanism.
7. **Requirements/document revisions.** Acquire a bounded repeated sample of document binaries, preserving verified SHA-256 and language; test same URL/new bytes and token-only URL changes. Current findings concern document metadata/references, not exhaustive document-content changes.
8. **Contract-register reconciliation.** Add RPC as a separate later experiment, with contract-registration dates and legal-contract identity rather than treating it as another notice feed. Likewise decide explicitly whether PLACSP minors/entrustments belong in the future product scope.
9. **Geography validation.** Audit buyer-versus-execution filters, NUTS versions, municipality codes and missing locations. Do not market ES511 filtering as Barcelona-city coverage.
10. **Source-authority policies.** Validate who is authoritative for current administration versus historical notice issuer, and for procedure-level versus lot-level attributes. Some conflicts in this report are legitimate changes in representation or scope, not incorrect source values.

## 7.2 Reproducing this research

The research findings and snapshot are preserved. The paths and commands below reflect the subsequent repository reorganization; run them from the repository root. Research tools now live in `research/scripts/`, original experiments in `research/legacy/`, and regression tests in `tests/research/`. The development extra adds pytest; the dependency history below describes the original research acquisition.

Use the existing local Python environment. Only **pypdf 6.17.0** was added; requests was already installed. Exact research dependencies are in `research/requirements.txt`. No global Python installation, application stack or orchestration infrastructure is required.

```bash
.venv/bin/python -m pip install -e ".[dev]" -r research/requirements.txt
.venv/bin/python research/scripts/download.py discovery
.venv/bin/python research/scripts/download_extra.py
.venv/bin/python research/scripts/download.py placsp --feed aggregated --periods 2025 2026
.venv/bin/python research/scripts/download.py placsp --feed native --periods 2025 2026
.venv/bin/python research/scripts/download.py gencat --dataset ybgg-dgi6
.venv/bin/python research/scripts/download.py gencat --dataset 8idu-wkjv
.venv/bin/python research/scripts/extract_documentation.py
.venv/bin/python research/scripts/inspect_placsp.py data/raw/placsp/aggregated/*.zip data/raw/placsp/native/*.zip
.venv/bin/python research/scripts/inspect_gencat.py --dataset ybgg-dgi6
.venv/bin/python research/scripts/inspect_gencat.py --dataset 8idu-wkjv
.venv/bin/python research/scripts/compare_sources.py
.venv/bin/python research/scripts/compare_sources.py --aggregated-only
.venv/bin/python research/scripts/audit_semantics.py
.venv/bin/python research/scripts/make_samples.py --download-phases
.venv/bin/python research/scripts/analyze_cases.py
.venv/bin/python research/scripts/inspect_phase_json.py
.venv/bin/python research/scripts/export_tables.py
.venv/bin/python research/scripts/verify_artifacts.py
.venv/bin/python research/scripts/audit_archives.py
.venv/bin/python research/scripts/verify_parsers.py
.venv/bin/python research/scripts/verify_report.py
.venv/bin/python -m pytest tests/research -v
```

Download resumption is at **validated file/page boundaries**, not HTTP byte ranges. A partial file is not accepted as a complete acquisition. Existing successful raw files are checksum-checked and reused; the scripts do not silently refresh/overwrite them. Future fresh acquisitions need a new run directory or clean research copy because upstream current-year archives/tables are mutable. Metadata drift or duplicate pagination IDs causes validation to fail rather than certifying a mixed snapshot. Existing derived indexes are reused; a parser change requires a new derived-output run/version, not pretending the old index reflects the new code.

The manifest itself also reproduces every supplementary probe's URL and parameters. Saved raw snapshots, rather than the assumption that a future live API response will be identical, make the reported analysis reproducible. Full source bodies remain local and are excluded from Git by `.gitignore`; the original exploratory root scripts and user files were not rewritten.

### Verification outcome

- **214 successfully acquired raw files**, totalling **6,237,708,795 bytes** (about 6.24 GB decimal), were rehashed: **zero missing files and zero checksum mismatches**.
- All **3,422 Atom members** were parsed. Link-chain auditing identified the ten oversized aggregation pages and the three out-of-period orphan members repeated in each native annual ZIP; they were reported rather than suppressed.
- The twenty case folders contain **64 exact PLACSP entry fragments**, **62 main-table row references** and **2 execution-row references**. Every saved fragment/reference was checked against its original acquisition: **zero mismatches**.
- All four failing encrypted legacy phase links were recovered as XML through an alternate official endpoint; **zero selected phase references remain unrecovered**. The failed requests and recovered bodies are both retained.
- Rechecking the identifier parser against **218,461 PLACSP observations and 1,070,969 Gencat rows** found **zero differences from the indexed identifiers**. A synthetic UUID-only URL regression was caught and fixed without affecting this corpus.
- **Nine unit tests pass**, Python compilation succeeds, and `git diff --check` passes. Tests cover URL identity parsing, source-host guards, decimal amounts, lossy matching normalization, whitespace-sensitive/insensitive hash distinctions, and separation of buyer/supplier identities.

These checks establish artifact integrity, extraction consistency and the tested parser behavior—not universal source completeness, a complete canonical history or production-ready matching accuracy.
