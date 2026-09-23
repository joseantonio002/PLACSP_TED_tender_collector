# 1. Purpose and scope

## Recommendation

Retain **NormalizedObservation** as the working name, defined as:

> A typed, source-attributed projection of what one raw source record says about one procurement subject, including any explicitly scoped lots, publications, results and execution actions, as that record was observed. It may be partial, historical, internally heterogeneous or ambiguous.

“State” means **source representation state**, not a claim that every contained fact was simultaneously effective, newly published, or still current. A procurement subject may be a procedure, a planning object, or an individual contract entry in a publication batch whose procedure identity is unresolved.

This first design supports **PLACSP and Generalitat de Catalunya**, using the research snapshot acquired on 22 September 2026. It is a proposal, not an accepted production architecture. It does not define a canonical tender, legal-procedure identity, canonical revision, database, parser, entity-resolution algorithm, reconciliation policy or notification model. No implementation is included.

The central design decision is **common concepts plus explicit scope and retained source semantics**, not a union of source columns and not a single flattened tender row. In particular:

- Procedure identity, source-row identity and publication identity are different.
- Procedure lifecycle, published phase and result/outcome are different.
- Estimated value, tender budget, award value and modification value are different.
- Technical source updates, publication times and business dates are different.
- One observation need not enumerate all lots, awards, documents or historical notices.
- Absence in an observation never instructs a consumer to delete a previously known fact.
- Normalization does not combine records, even when their identifiers appear to agree.

## Evidence discipline and reading guide

Evidence labels apply to claims about the sources:

- **[D] Documented:** official publisher documentation or API-vendor documentation explicitly supports the claim.
- **[O] Observed:** present in retained source bodies or measured by the existing research. An observed property is not a permanence guarantee.
- **[I] Inference:** interpretation justified by the evidence but not explicitly guaranteed by the publisher.
- **[U] Unresolved:** evidence is insufficient or conflicting.
- **[R] Recommendation:** a design decision in this report, not purported source behavior.

All normative field definitions, cardinalities and taxonomies below are **[R]**, unless another label is attached. Mapping references identify the evidence for their inputs. An empty normalized category never licenses guessing a source meaning.

### Evidence register

Paths are repository-relative; linked paths resolve from this report. The schema analyses and previous normalization/reconciliation proposal are sections of the main report, rather than separate schema documents.

| Ref | Evidence inspected | What it establishes / limitation |
|---|---|---|
| R | [Main research report](REPORT.md), §§1–3, including both schema analyses and comparison; §§4–5, previous proposals; §§6–7, validation and limitations | Synthesis, measured cohorts and counterexamples. Previous proposals are critically reviewed, not adopted as requirements. |
| P | [Syndication specification v1.10, extracted text](../../data/analysis/documentation/syndication-current.txt); [original PDF](../../data/raw/documentation/syndication-current.pdf) | [D] Entry/update semantics, §§3.1–3.4; status §4.1; amounts §4.4; types §§4.7, 4.12; lots §4.11; results §4.35; modifications §4.38; publications §4.39. Examples and prose have occasional inconsistencies; see §15. |
| G | [Main-table metadata](../../data/raw/gencat/ybgg-dgi6/metadata-before.json), `ybgg-dgi6` | [D] Row granularity and column definitions, including easily confused lot/procedure amount fields. Cached category counts describe the whole live table, not just the selected cohort. |
| E | [Execution-table metadata](../../data/raw/gencat/8idu-wkjv/metadata-before.json), `8idu-wkjv` | [D] Action types and action/end/amount column semantics. Detailed action granularity is additionally established empirically. |
| S | [Socrata system-field documentation](../../data/raw/documentation/socrata-system-fields.html) | [D] Technical row clocks, not procurement clocks. |
| A | [Semantic audit](../../analysis/semantic_audit.json), [metrics](../../analysis/metrics.json), [case findings](../../analysis/case_findings.json) | [O] Renamed numbers, duplicate IDs, heterogeneous phases, precision differences and missingness; not an entity-resolved census. |
| C01–C20 | [Case directory](../../data/samples/), indexed in R §3.2 and [case selection](../../analysis/case_selection.json) | [O] Purposively selected edge cases, not a random sample or statistical accuracy estimate. Exact acquisition locators are in each `evidence.json`. |
| J01 | [PSCP publication 300885987](../../data/raw/gencat/phases/300885987.json) | [O] Multilingual text, correction, documents, explicit no-lots flag, nevertheless a `dadesPublicacioLot` array, net/gross budget and VAT fields. |
| J14 | [PSCP batch 300339416](../../data/raw/gencat/phases/300339416.json) | [O] Six contract entries, related framework identifiers and no individual procedure identity derivable from the batch UUID. |
| J19 | [PSCP execution publication 300007312](../../data/raw/gencat/phases/300007312.json) | [O] Two modifications in one publication; distinct dates, local action identifiers and price increments. |
| J20 | [PSCP publication 300641893](../../data/raw/gencat/phases/300641893.json) | [O] Lots, different internal lot IDs and numbers, multiple contractor objects, formalization dates and absent amounts. |

The preceding PLACSP distribution catalogues, OpenPLACSP manual and PSCP presentation are identified in R §1.1. Local source artifacts are intentionally retained outside Git in this repository. A reader without them can use R for the findings, but should not mistake that for independent raw-data verification.

Coverage: both researched PLACSP primary feeds, Generalitat main rows, sampled modern/legacy publication bodies and the researched execution table. RPC, additional PLACSP minor/entrustment feeds and hypothetical foreign sources are not added to the acquisition scope. Their mention in documentation does not imply empirical coverage. No claim of exhaustive historical notices or document binaries is made.

# 2. Conceptual comparison of PLACSP and Generalitat

| Question | PLACSP | Generalitat de Catalunya |
|---|---|---|
| What is the acquired record? | [D] An Atom entry containing a CODICE/PLACSP `ContractFolderStatus`, inside a feed/archive. A tombstone is a different record kind. | [D/O] A Socrata main row, an execution-action projection, or a separately acquired rich publication body. Those representations must not be treated as interchangeable records. |
| What is the procedure? | [D] Source expediente represented by an entry ID and human `ContractFolderID`; [O] several entry IDs can point at one PSCP procedure object. | [O] Ordinary PSCP UUID/`idExpedient` identifies a source procedure object. For aggregated publications the similarly shaped UUID identifies the batch, not each member's procedure. |
| Snapshot, event or publication? | [D/O] Updated procedure representation, often carrying accumulated notices/results. Not one entry per legal event and not a complete event log. | [D/O] Main rows are current projections of procedure/lot/member information across phases. Rich bodies are publication representations, also potentially containing accumulated details. Execution rows project actions, and one body may contain several actions. A mixture. |
| Publications | [D] `ValidNoticeInfo` groups by notice type and medium, with potentially multiple dated references. An entry link can identify an origin notice independently of those groups. | [D/O] Phase dates and phase export links; rich body has actual/planned publication times and a phase. Main page URL can refer to a different notice from the latest corrected phase export. |
| Updates | [D] Entry `updated` means latest relevant publication time; generation corrections can occur without changing it. Feed `updated` is another clock. | [D] Socrata system fields mark row management; phase publication columns mark publications. [O] Old business data has 2026 technical row creation dates. |
| Lots | [D/O] Nested `ProcurementProjectLot`, with separately lot-referenced results; aggregation details can be sparse. | [D/O] Separate table rows plus rich arrays. Parent and lot rows can coexist with different phases. An internal `lotId`, row suffix and displayed `numeroLot` need not agree. A rich “lot” container can describe an unsplit procedure. |
| Lifecycle | [D] Procedure-oriented state; `ADJ` can mean at least one lot awarded; `RES` includes formalization or unsuccessful/withdrawn outcomes across lots. | [D] `fase_publicacio` is latest published phase, not a directly equivalent procedure state. `resultat` supplies another dimension; execution action type is yet another. |
| Awards and winners | [D/O] Repeated `TenderResult` can be positive or negative; repeated winners and awarded-project/contract structures. | [D/O] Scalar and `||`-concatenated columns; rich per-lot contractor arrays. Current projection can retain historical award details after withdrawal. |
| Corrections/modifications | [D/O] Replacement representations and notice/result references; contract modifications separately documented. A content change alone does not establish legal cause. | [O] `tipusEsmena`/`motiuEsmena` describe publication corrections; execution actions describe contract changes. They are not the same concept. |
| History | [D] Older entries may exceptionally disappear. Archives overlap and repeat occurrences. | [D/O] Current rows are not a version history. Some past phase bodies can be retrieved, but complete enumeration and stable-content guarantees are unresolved. |
| Documents | [D/O] Legal/technical/additional references, including references nested within notices/results. | [O] Main export links lead to publication representations; rich bodies expose document IDs, titles, paths, hashes and sizes. JSON-named endpoints can return legacy XML. |
| Stable identity | [D/O] Scoped entry ID is useful across updates, not a global legal-procedure key. Same `(id, updated)` is not guaranteed immutable. | [O/U] Row IDs are unique in the snapshot; longitudinal stability after reload is unproven. Ordinary UUIDs are useful; batch UUIDs and local lot/action identifiers require separate scope. |

## Concrete consequences

1. **C05:** 25 PLACSP observations and 13 current Generalitat rows for the 13-lot `ME. MEC-25L02` are not competing counts of procedures or revisions.
2. **C16:** one planning parent and five tender lot rows coexist. Normalization must not choose the maximum phase and rewrite all six rows.
3. **C14/J14:** six reported contracts share one batch UUID, with two entries sharing `2023/800`. Neither UUID nor buyer-plus-number uniquely identifies the member.
4. **C09:** PLACSP reports `RES`, result `5` and `RENUNCIA`; Generalitat reports `Anul·lació`/`Renúncia` while retaining winner `A58846064` and net award `83,996.64`. Both can be represented without declaring either record wrong or erasing history.
5. **C19/J19:** two actions, dated March and August 2026, occur in a publication actually released on 26 August. Their September row update is neither action date nor publication date.
6. **J01:** `teLots=false` and `divisioEnLots=Sense lots` coexist with one `dadesPublicacioLot` element. This is a source container, not evidence for “lot 0.”

All six are **[O]**. Their schema consequences are **[R]**, not proof of universal source behavior.

# 3. Cross-source field mapping

## Mapping notation

`P` paths below are relative to `ContractFolderStatus` unless prefixed `entry/`. `PP` = `ProcurementProject`; `PL` = `ProcurementProjectLot/ProcurementProject`; `TR` = `TenderResult`; `VN` = `ValidNoticeInfo`. Namespace prefixes are omitted for readability, **not** permission to ignore namespace URIs when implementing.

`G` = main-table fields; `E` = execution-table fields; `J` = modern rich JSON. `JB` = `publicacio.dadesBasiquesPublicacio`; `JP` = `publicacio.dadesPublicacio`; `JL` = `publicacio.dadesPublicacioLot[]`. Legacy XML needs its own source mapping; modern paths must not be applied by guessing from the endpoint name.

The relationship column classifies the **conceptual relationship**, not whether every value is present. `DIRECT MAPPING` still requires lossless type conversion. `MAPPING WITH NORMALIZATION` requires qualified codes, parsing, scope or precision handling. `SEMANTICS DIFFER` forbids an unconditional shared-field assignment. `SOURCE-SPECIFIC` means retain separately or in raw; it need not be discarded. `CURRENTLY UNCLEAR` means do not populate a stronger normalized claim without more evidence.

| Normalized concept | PLACSP | Generalitat | Relationship | Semantic notes | Normalization implications |
|---|---|---|---|---|---|
| Source record identifiers | `entry/id` | `:id`, `id_intern`; rich publication ID from explicit URL/context | SEMANTICS DIFFER | P entry identifies source expediente, G IDs identify projection rows [D/O]. | Typed, namespaced `source.record_identifiers`; immutable occurrence ID is separate. |
| Source procedure identifiers | Entry ID; ordinary PSCP UUID explicitly in origin URL | Ordinary UUID/`idExpedient` | MAPPING WITH NORMALIZATION | Several P IDs per UUID; batch exception [O]. | `procedure_identifiers`; do not resolve them to a canonical ID. |
| Procedure number | `ContractFolderID` | `codi_expedient`, `codiExpedient`, batch member `expedient` | MAPPING WITH NORMALIZATION | Mutable, buyer-scoped, sometimes absent [O]. | Preserve strings and issuer context; never parse title as a number fallback. |
| Publication/notice identifiers | Origin URL ID; explicit VN document IDs where truly notice IDs | Page/phase URL numeric ID; body references | MAPPING WITH NORMALIZATION | Atom ID is not a notice ID; IDs often absent from VN [D/O]. | Embedded publication references may have no identifier. |
| Publication batch identity | Aggregated-platform feed is not a publication batch | `es_agregada`, batch UUID and notice ID | SOURCE-SPECIFIC | Feed aggregation and multi-contract publication are unrelated [D/O]. | `batch_identifiers`, `subject_kind=batch_member`; never put batch UUID in procedure identifiers. |
| Lot identity | `ProcurementProjectLot/ID`; awarded-project lot reference | `numero_lot`; `JL.numeroLot`, `JL.lotId` | MAPPING WITH NORMALIZATION | Row suffix is not number; duplicate number observed [O]. | Observation-local lot keys plus scoped source identifiers, no unique-number constraint. |
| Buyer identity | Located party IDs with `schemeName`; origin `AgentParty` | `codi_organ`, `codi_dir3`; J `organ.organContractacioId`, `organ.nif` | MAPPING WITH NORMALIZATION | Platform ID is not tax ID; placeholders exist [O]. | Party identifier schemes and namespaces; buyer NIF is not supplier NIF. |
| Supplier identity | `TR/WinningParty/PartyIdentification/ID` | `identificacio_adjudicatari`, `tipus_identificacio`; J contractor objects | MAPPING WITH NORMALIZATION | Concatenated values, numeric type codes, UTE identity [D/O]. | Preserve positions and unresolved schemes; no legal-entity matching. |
| Title | `PP/Name`; Atom title as labelled fallback | `denominacio`; `JB.denominacio`; batch member description only if explicitly a title | MAPPING WITH NORMALIZATION | Multiple languages and display variations [O]. | Localized texts; no translation or title-to-ID inference. |
| Description | Explicit project description if provided, not synthesized Atom summary | `objecte_contracte`; `JB.descripcio`; batch `descripcio` | MAPPING WITH NORMALIZATION | P project `Name` is often contract object, not independent long description [D/O]. | Separate description; do not duplicate title merely to fill it. |
| Buyer name/address | Located party and postal address | `nom_organ`; J `organ.nom`/address | MAPPING WITH NORMALIZATION | Historical publication buyer can differ from current table buyer [O]. | Source-reported buyer, not inferred current administrator. |
| Contract type | `PP/TypeCode`, `SubTypeCode`, `MixContractIndicator` | `tipus_contracte`; `JB.tipusContracte`, `contracteMixt` | MAPPING WITH NORMALIZATION | Legacy legal types and Annex IV qualifiers [D/O]. | Contract taxonomy plus original category/subtype and mixed flag. |
| Award procedure | `TenderingProcess/ProcedureCode` | `procediment`; `JB.procedimentAdjudicacio` | MAPPING WITH NORMALIZATION | Simplified and abbreviated variants; source categories are not one clean legal dimension [D/O]. | §10 taxonomy; retain unmapped labels rather than force `open`. |
| Contracting system / urgency | `ContractingSystemCode`, `UrgencyCode` | `racionalitzacio_contractacio`, `tipus_tramitacio` | MAPPING WITH NORMALIZATION | Framework establishment is not a call-off method; urgency is not method. | Separate optional source-coded attributes. |
| Lifecycle | `ContractFolderStatusCode` | No exact equivalent; `fase_publicacio` is phase | SEMANTICS DIFFER | `PUB` and tender-phase publication do not both prove accepting offers now. | Separate status dimensions, scoped to what was reported. |
| Published phase/type | `VN/NoticeTypeCode` | `fase_publicacio`, J `publicacio.fase`, phase-specific columns | MAPPING WITH NORMALIZATION | A correction can retain tender phase. | Publication type plus correction qualifier; current row phase is separately retained. |
| Result | `TR/ResultCode` | `resultat`; rich annulment/result detail | MAPPING WITH NORMALIZATION | Deserted, renounced, discontinued, awarded, formalized [D/O]. | `outcomes`, not unconditional `awards`. |
| CPV | Project/lot `RequiredCommodityClassification/ItemClassificationCode` | `codi_cpv`; rich CPV objects | MAPPING WITH NORMALIZATION | Eight digits vs check-digit form; row/lot scope [O]. | Preserve original, normalized eight-digit code, check digit, list/version and scope. |
| Procedure estimate | `PP/BudgetAmount/EstimatedOverallContractAmount` | `valor_estimat_expedient`; `JP.valorEstimatContracte` | MAPPING WITH NORMALIZATION | Not the tender budget; may include future options/framework value [D]. | `financials`: purpose `estimated_value`, scope procedure. |
| Lot estimate | Explicit estimate under PL if supplied | `valor_estimat_contracte`; `JL.valorEstimat` | MAPPING WITH NORMALIZATION | G name misleading: documented lot estimate [D]. | Lot scope only when real lot identified; otherwise preserve record-subject/uncertain scope. |
| Net procedure tender budget | `PP/BudgetAmount/TaxExclusiveAmount` | `pressupost_licitacio_sense_1`; `JP.pressupostLicitacio` | MAPPING WITH NORMALIZATION | Repeated across lot rows [D/O]. | Purpose `tender_budget`, tax excluded, procedure scope; never sum repetitions. |
| Gross procedure budget | `PP/BudgetAmount/TotalAmount` | `pressupost_licitacio_amb_1`; `JP.pressupostBaseLicitacioAmbIva` | MAPPING WITH NORMALIZATION | Not interchangeable with net. | Preserve separately with tax included. |
| Lot budgets | PL `BudgetAmount/TaxExclusiveAmount`, `TotalAmount` | `pressupost_licitacio_sense`, `pressupost_licitacio_amb`; JL budget fields | MAPPING WITH NORMALIZATION | Sparse P aggregation; lotless rich container [O]. | No invented lots or distributed procedure budget; see documentary inconsistency §15. |
| VAT rate/treatment | Net/gross paths; explicit tax data if present | Net/gross columns; J `iva`, `varisTipusIva` | MAPPING WITH NORMALIZATION | A single rate cannot describe mixed rates; net=gross does not prove exemption. | Preserve tax basis and explicitly reported rate/multiple-rate flag; do not infer from division. |
| Currency | Amount `currencyID` | No independent table currency column; sampled rich amount numbers often also lack one | SEMANTICS DIFFER | P documentation specifies EUR; G numeric equality alone lacks currency qualification. | Nullable currency. No blanket EUR default or borrowing from another record. |
| Award amount | `TR/AwardedTenderedProject/LegalMonetaryTotal/TaxExclusiveAmount`, `PayableAmount` | `import_adjudicacio_sense`, `import_adjudicacio_amb_iva`; rich explicit award fields | MAPPING WITH NORMALIZATION | Multiple winner values and empty tokens [D/O]. | Award/group totals and supplier-specific amounts separately; no sum if partition semantics unknown. |
| Action / modified-contract amount | `ContractModificationLegalMonetaryTotal`; `FinalLegalMonetaryTotal` | E `import_sense_iva`; J action `incrementPreu` | SEMANTICS DIFFER | Action amount, price delta and resulting total differ [D/O]. | Purpose `action_amount`, `modification_delta`, or `contract_total_after_modification`. |
| Publication date | VN PLACSP `NoticeIssueDate`; media document `IssueDate` | Ten `data_publicacio*` fields; J `dataPublicacioReal` | SEMANTICS DIFFER | Original notice date versus later correction; medium and notice may differ [O]. | Publication occurrences with role, phase and precision; no top-level singular date. |
| Planned publication | No shared field established in reviewed projection | J `dataPublicacioPlanificada` | SOURCE-SPECIFIC | Planned is not actual. | Optional publication field; never fallback for actual. |
| Source creation | No verified procedure-creation field in entry | Socrata `:created_at` | SEMANTICS DIFFER | G row creation is technical [D]. | Raw source clock only; no `procedure_created_at`. |
| Source update | `entry/updated` | Socrata `:updated_at` | SEMANTICS DIFFER | Latest relevant publication marker versus technical row update [D]. | Typed `source_markers`; never a comparable generic `updated_at`. |
| Feed/dataset update | Feed `updated` | View `rowsUpdatedAt`/`publicationDate` | SOURCE-SPECIFIC | Container metadata, not per-procedure facts. | Raw/acquisition metadata only. |
| Observation/ingestion | Collector times, not source fields | Collector times, not source fields | DIRECT MAPPING | Same system events independent of source. | Raw provenance, distinct receipt and acceptance clocks. |
| Offer deadline | `TenderSubmissionDeadlinePeriod/EndDate`, `EndTime` | `termini_presentacio_ofertes`; J `dataTerminiPresentacioOSolicitud` | MAPPING WITH NORMALIZATION | J combined offers/requests name needs contextual interpretation; precision/zone differ. | Typed deadline; unknown submission subtype permitted, no forced UTC. |
| Participation-request deadline | `ParticipationRequestReceptionPeriod` when supplied | Rich combined submission field if explicitly requests | MAPPING WITH NORMALIZATION | Not always the same deadline as offers. | `participation_requests` separate from `offers`/`submission_unspecified`. |
| Result decision / award date | `TR/AwardDate` | `data_adjudicacio_contracte`; `JL.dataAdjudicacio` | SEMANTICS DIFFER | P calls it “Fecha del acuerdo,” also usable on negative results [D]. | Outcome decision date; award decision date only with positive award evidence. |
| Formalization | `TR/Contract/IssueDate` | `data_formalitzacio_contracte`; `JL.dataFormalitzacio` | MAPPING WITH NORMALIZATION | Business date, not formalization notice date. | Contract reference under award details; multiple references possible. |
| Contract entry into force | `TR/StartDate` | No unambiguous general table counterpart | SOURCE-SPECIFIC | Contract effective date is not planned performance start. | Optional contract-reference `effective_at` only with supported attachment. |
| Action dates | Explicit action date if a supported P structure supplies it | E `data`, `data_fi`; J `dataModificacio` and typed action dates | MAPPING WITH NORMALIZATION | Not generic publication/event timestamps. | `action_at`/`end_at`; absence stays absent. |
| Performance period | `PlannedPeriod` dates/duration | `durada_contracte`; J `duradaTermini`, batch execution start/end | MAPPING WITH NORMALIZATION | Planned periods, reported execution intervals, durations and conditional starts differ. | Preserve period kind and raw text; no calculated end dates. |
| Lots | Nested P project lots | Rows and JL objects | SEMANTICS DIFFER | Container/row identity does not establish complete lot inventory. | Embedded lot occurrences plus partial coverage, not globally identified lot entities. |
| Awards/winners | TR and repeated winning parties | Flattened columns and rich arrays | MAPPING WITH NORMALIZATION | Grouping, winner cardinality and persistence differ. | Repeated award-information groups with supplier allocations and uncertain alignment preserved. |
| Documents | Direct and nested document references | Rich document objects; main phase links are exports | SEMANTICS DIFFER | Export URL is not technical specifications. | `documents` for actual document references; `source_references` for pages/exports. |
| Execution geography | Project/lot `RealizedLocation` | `codi_nuts`, `lloc_execucio`; J `llocExecucio` | MAPPING WITH NORMALIZATION | NUTS area and free-text municipality labels need not share granularity. | Scoped locations; no city inference from ES511. |
| Buyer geography | Party postal address | Buyer organization J address; organizational/INE columns | SEMANTICS DIFFER | Not execution territory; metadata only calls `codi_ine10` “Codi INE10.” | Buyer location separately; defer uncertain INE interpretation. |
| Source page and exports | Entry link, profile URI, notice references | `enllac_publicacio`, `url_json_*`, E `url_json` | MAPPING WITH NORMALIZATION | Exact URL and typed target differ; old/current notice mismatch possible. | Preserve exact links and independently extracted identifiers; no synthesis of unverified download URLs. |
| Source-specific classifications | Subtype, funding, legislation, hierarchy, submission tooling | Funding, administrative hierarchy, electronic tools, SME and other labels | SOURCE-SPECIFIC | Not all are procurement taxonomies. | Small named attributes where specified; remainder raw, not an unbounded metadata bag. |
| Unknown code meaning | Unrecognized list/version/code | Numeric G category with no verified dictionary, e.g. supplier type outside inspected examples | CURRENTLY UNCLEAR | A number or translated label is not its own semantic dictionary. | Retain Code with null normalized value; issue, not guessed mapping. |
| Source deletion | Tombstones `ANULADA`, `CERRADA`, unknown type | Row absence, access failures | SEMANTICS DIFFER | Source availability is not legal outcome [D/O]. | Preserve raw availability records; do not manufacture procurement cancellation observations. |

# 4. Important semantic differences and false equivalences

| Looks equivalent because… | Why it is not identical | Information lost by collapsing | Required representation / evidence |
|---|---|---|---|
| Both sources have “updated.” | P entry marker is publication-related; Socrata row update is technical; feed/view update is container-level. | Business chronology, reload detection, later corrections with unchanged P timestamp. | Typed source markers, raw container clocks and separately identified publications. [D P/S; O R §2.4] |
| Both expose a tender-looking UUID/ID. | Atom ID is source expediente ID; numeric PSCP ID is publication; batch UUID is not a member procedure. | Many-to-one entry identities and multiple contracts per batch. | Separate record/procedure/publication/batch/member identifiers. [O C10/C14] |
| Expediente strings match. | Numbers are buyer-scoped, mutable and can repeat even inside a batch for distinct entries. | Distinct buyers/contracts and number history. | Exact numbers with buyer context, not normalized global keys. [O C04/C14/C17] |
| Both expose estimated contract value and budget. | Estimated overall commitment and advertised base budget are separate legal/economic concepts. | Options/extensions/framework ceiling versus current tender budget. | Distinct money purpose; never fallback between them. [D P §4.4/G] |
| G `valor_estimat_contracte` sounds procedure-wide. | Metadata calls it lot-level; `valor_estimat_expedient` is procedure-wide. | Lot economics and inflated repeated totals. | Explicit financial scope; no summation of repeated procedure figures. [D G; O C05] |
| Net and gross amounts happen to be equal. | Equality does not state exemption or a zero VAT rate. | Unknown tax treatment; potentially mixed or absent data. | Preserve included/excluded tax basis and source-reported VAT only. [O C14/J14; I tax caution] |
| Numeric amounts match across sources. | G table does not supply currency; action delta is not contract total; supplier value is not group total. | Currency, purpose and monetary attribution. | Decimal + currency + tax basis + purpose + scope/group placement. [D/O R §§2.5,5.2] |
| `PUB` resembles `Anunci de licitació`. | P state says within submission period as represented; G label says a tender phase was published. | Whether an opportunity is currently accepting submissions. | Lifecycle state separate from publication phase; no clock-based rewriting during normalization. [D P §4.1/G] |
| `RES` resembles completed/awarded. | It covers formalization, deserted tendering, renunciation and discontinuation. Formalization is not completion of performance. | Unsuccessful lots and failed procedures. | `resolved_unspecified` lifecycle with separate result(s). [D P §4.1; O C09] |
| `Anul·lació` resembles only P `ANUL`. | G annulment publication covers deserted/renounced/discontinued/error/tribunal cases; P may report `RES` with specific result. | Reason for ending and difference between invalid publication and failed competition. | Annulment publication family plus original detail/outcome; no universal cancellation enum. [D G; O C06/C09] |
| `AwardDate` resembles `data_adjudicacio_contracte`. | P documents a result agreement date, including negative results; G award date explicitly concerns adjudication. | A negative decision incorrectly becomes an award. | Outcome `decision_at`; award `decision_at` only when positive facts justify it. [D P §4.35.5, including negative-result example; G] |
| Publication date resembles first opening date. | Tender phase date can be a correction after deadline; VN may retain original notice date. | Original versus corrected publication and real deadline changes. | Multiple publication occurrences, correction metadata, typed deadline. [O C01/C02/C13] |
| Formalization date resembles formalization publication. | Contract can be signed months before a later publication/correction. | Actual contracting chronology. | Separate contract-reference date and publication occurrence. [O C10/C20] |
| Rich UTC midnight-related timestamp resembles an exact event instant. | A date-only business field may be serialized as local midnight converted to UTC. Table precision may also truncate seconds. | Calendar-day meaning and measurement uncertainty. | Semantic precision and timezone basis; preserve original serialization. [O C13/J19/J20; U systematic policy] |
| Buyer Barcelona address resembles execution in Barcelona. | Buyer address is organizational; ES511 is a province-level execution area, not municipality. | Work elsewhere, national buyers working locally, multi-location lots. | Buyer addresses separate from scoped execution locations. [D/O R §1.2] |
| Row suffix/internal lot ID resembles lot number. | C05 suffix `_6` means displayed lot 7; J20 `lotId=0` means lot 4. | Wrong lot/result/amount associations. | Separate local occurrence key, original number and source IDs. [O C05/J20] |
| Rich lot array means lots exist. | J01 contains that array with an explicit no-lots flag. Missing/zero G lot marker is also not sufficient evidence of a real lot. | Fabricated lots and wrong procedure totals. | Check semantic flags/context; use procedure or record-subject scope, not fake lot 0. [O J01/A] |
| Winner present means currently awarded. | G retains an old winner after renunciation; P latest result may omit it. | Historical award and later negative outcome. | Award information and outcome as separate collections, no inferred rescission link. [O C09] |
| A publication body or `ValidNoticeInfo` is one event. | A body can contain two execution actions; VN can have several dates per medium. | Action cardinality, media-specific publication dates. | Action array; publication occurrence references, not unique event objects. [D P §4.39; O J19] |
| Document hash/URL represents an immutable document version. | Source hash algorithm can be unstated; URL tokens can change; binaries were not exhaustively acquired. | Difference between reported metadata and verified content. | SourceDocumentReference, not DocumentVersion; exact links plus reported hash. [O J01; U content stability] |
| Missing row or `CERRADA` means cancelled. | Publisher has documented missing historical rows; closure concerns source accessibility. | Legal state and retained history. | Raw availability information, no cancellation inference. [D P/G] |
| PLACSP and Gencat agreement means two independent witnesses. | Catalan aggregation is downstream of PSCP. | Origin lineage and misleading corroboration confidence. | Transport source separate from originating platform. [D/O R §5.3] |
| `versio=1.0.0` means first business revision. | It is a representation/schema version in sampled PSCP bodies. | Publication/revision chronology. | Raw representation metadata, not normalized revision number. [O R §2.3] |

# 5. Proposed normalized model

## 5.1 Boundary with RawSourceRecord

**RawSourceRecord** is the immutable source-specific occurrence, not a cleaned business object. It owns:

- Exact source bytes or a lossless reference into an immutable acquired artifact. A parsed JSON object alone is not a replacement for the original bytes.
- Acquisition identity, original/resolved request URL, request parameters, relevant safe response metadata, response receipt time and verified artifact checksum.
- Record locator: archive/member/entry ordinal and byte range where available, or JSON page/index; required XML namespace context; rich-body or batch-member selection paths.
- Source format/schema markers, source IDs, technical row fields, feed/view metadata, unrecognized values and source-specific structures.
- `observed_at` (collector receipt) and, if tracked, `ingested_at` (acceptance into the raw-record layer). It must not fabricate ingestion time from file mtime.
- Source clocks exactly as transmitted, including their field names; availability/tombstone information.

**NormalizedObservation** owns the typed procurement projection, source-qualified identifiers, scoped monetary/classification/deadline facts, embedded lots, publication references, outcomes, award details, action details and document references. It includes normalization version, input selection and issues. It does **not** own the original payload, perform joins, select authoritative values from other records, or declare stable real-world entities.

**Cardinality:** one raw record produces zero or more observations. Each observation references **exactly one raw record** and one explicit selection within it:

- One P entry → one observation, regardless of its lot count.
- One ordinary G main row → one observation; a lot row includes a single lot occurrence and any separately reported procedure facts.
- One rich ordinary publication → one observation, including all its explicitly described lots/actions.
- One G batch row → one batch-member observation. One rich batch body → one observation per explicitly listed member, all pointing to the same raw body with different `projection_locator` values; shared batch publication metadata remains batch metadata.
- One E row → one partial action observation, even if no main row is available.
- A tombstone is **not** a procurement-state observation in v1. Retain it as a raw availability record for a later availability projection. An actual P `ANUL` entry remains a procurement observation.

Joining a table row with a separately acquired rich body would violate the one-input boundary. Emit separate observations instead. Copying common header facts into each member projection of the **same** raw batch body is allowed only when the source makes them applicable to that member; copying member A's facts into member B is not. A batch title is not each member's title, and batch totals are not member budgets. Keep batch-only descriptive/financial header material raw; the normalized batch identity and publication scope preserve its context.

If a record cannot be safely assigned a member/procedure scope, keep it raw and report a mapping issue rather than produce a false procedure. Identifiers can be absent: no canonical ID is needed to emit a correctly scoped partial observation.

## 5.2 Shape and justified abstractions

The observation has a source envelope, subject identity, descriptive fields, scoped facts, and embedded collections. **Scope** is a small shared value, not an entity graph:

- `procedure`: explicitly procedure-wide information.
- `lots`: one or more identified source lot references, which may or may not resolve to an embedded lot occurrence.
- `record_subject`: information about this row/member's subject without claiming procedure-wide or lot-wide applicability. Necessary for batch members and ambiguous lotless table projections.
- `publication_batch`: only for facts such as the batch publication, not member finances/awards.
- `unknown`: source gives insufficient scope.

This prevents hidden inheritance. A procedure deadline is not copied onto all lots; a lot result is not promoted to procedure lifecycle. A consumer may later use procedure terms as applicable defaults, but normalization does not manufacture duplicate facts.

| Concept | Include? | Justification |
|---|---|---|
| Buyer / Supplier | Yes, as uses of a shared embedded `Party` value | Both have names and scoped identifiers. No organization registry, canonical party ID or inferred role history. |
| Money | Yes | Exact decimal, currency, tax basis and purpose are essential. Scope is provided by a containing scoped fact, award/allocation or action. |
| Lot | Yes, embedded occurrence | Real repeated lot structures and flattened rows require association, but not stable cross-observation lot identities. |
| PublicationReference | Yes, embedded occurrence | Both expose publications, sometimes without IDs or with grouped dates. It is deliberately weaker than a globally identified Notice entity. |
| Outcome and Award | Yes, separated | Negative results are not awards; an observation can simultaneously report an old award and later renunciation. Award means a group of source-reported award information, not proof of one legally individuated decision. |
| ContractReference | Yes, inside award information | Preserve reported contract numbers, formalization and effective dates without building a legal Contract entity or assuming one contract per procedure. |
| ExecutionAction | Yes, narrowly | Already researched, not hypothetical. J19 cannot be expressed correctly as a single status or award amount. No contract-state calculation. |
| SourceDocumentReference | Yes | Supports original links and metadata without claiming acquisition, immutability or canonicality. |
| Location, LocalizedText, Code, TemporalValue | Yes, value types | Real geographic-role, language, code-list and temporal precision differences warrant them. |
| Stable ProcurementProcess, Organization, Notice, DocumentVersion, Contract | No, deferred | These would require identity/lifecycle decisions outside normalization. |
| Generic FieldAssertion/ValueState on every field | No | Not required for canonical provenance here. Nullable values, original raw data, item locators and explicit issues suffice for v1. |
| Arbitrary `extra_metadata` dictionary | No | It would recreate the union of both schemas. Unmapped details remain raw; small explicitly named coded attributes are specified below. |

## 5.3 Explicit changes to the earlier proposal

The earlier R §4 proposal includes resolution decisions, stable Process/Lot/Party IDs, canonical revisions, field assertions and document versions. These are useful future topics, **not** components of this layer.

This design:

1. Replaces stable `Process.id` with observation-local identity plus typed **source** identifiers; no resolution decision is smuggled into normalization.
2. Replaces canonical lot IDs with local occurrence keys; lot numbers are not uniqueness constraints.
3. Replaces broad `source_updated_at` with individually typed source markers.
4. Replaces one Notice object per VN with publication **occurrences**; an occurrence can lack ID or refer to a batch.
5. Separates negative outcomes from award information and limits `award.decision_at` to award evidence.
6. Replaces DocumentVersion with SourceDocumentReference; source hashes are not verified local hashes.
7. Preserves unresolved row/member scope rather than forcing all data into a stable procedure or legal contract.
8. Retains narrowly defined execution action facts because they are observed, but defers full Contracts, party-role histories and valid-time intervals.
9. Does not require field-level provenance/assertion entities. One immutable raw input plus exact selection, mapping version and repeated-item source paths is the minimum contract.
10. Adds an explicit guard against PSCP's **lot-shaped no-lots container**, a detail not resolved by merely saying “rich lot arrays.”

# 6. Field-by-field specification

## 6.1 Conventions and global invariants

The tables in this section and the complete expansion in §16 specify the proposed v1 fields. Reused types are defined once; their field rules apply at every occurrence.

- `1` = required, non-null singleton; `0..1` = optional/nullable singleton; `0..N` = required collection, permitted empty; `1..N` = required nonempty collection. Collection elements are non-null. These are conceptual cardinalities, not a storage format.
- `String` preserves source identifier spelling; `Decimal` is exact, never binary floating point; `Key` is an observation-local opaque string, **not** a stable domain ID; `ID` is an internal observation/raw identity, not a canonical procurement ID.
- `Text[]` means `LocalizedText[0..N]`. Unknown language is null; do not label all G text Catalan (Aranese content is present). HTML/source text is retained as source text; safe rendering is a later concern.
- Missing scalar means not asserted here, not false, zero, legally inapplicable or deleted. Empty collection means no mapped members in this projection, not a complete empty set.
- `issues` records distinctions such as explicit empty, invalid, unmapped, scope uncertainty, ambiguous timezone and alignment failure. The exact original value remains raw. Numeric source tokens additionally remain in `Money.raw_value`; empty award tokens remain positional.
- Do not create an empty Party, Money, Outcome or Publication merely to satisfy a shape. A reference with only an ID, URL, phase or date can be meaningful; a completely ungrounded object cannot.
- No normalization fallback may cross raw records. No inferred budget totals, currency, winners, procedure numbers, active status or legal transitions.
- Every local reference must resolve within the observation, or remain an explicit **source** identifier rather than a dangling local key. Local keys are unique across the observation. They can be deterministically based on source path; they do not survive source reordering by guarantee.
- Preserve repetition and order where they carry source grouping/positional meaning. Equal content does not prove duplicate legal objects.
- For conflicting singleton assertions within the same raw input, apply a documented structural rule only when it establishes the field's source meaning; otherwise leave the singleton null and emit inconsistent_source_values referencing all original paths. Do not choose whichever value appears last. Repeated/scoped collections can retain competing occurrences.
- Source paths use exact JSON pointers, qualified XML occurrence paths, or an ordered list of such locators encoded as a string for multi-field values. The locator convention belongs to mapping_version. This is sufficient to revisit grouping without a field-assertion storage model.

### Source mapping abbreviations

The P/G/J abbreviations from §3 apply. `collector` means generated from acquisition/raw identity, not a source business claim. `mapping` means a versioned deterministic interpretation of the same raw record. `—` means no mapping established; it does not imply the source can never supply it. `Qn` points to an implementation/open question in §15. For fields with no unresolved issue, “none specific” does not imply exhaustive source validation.

## 6.2 Observation and source envelope

| Field | Type; cardinality / nullable | Meaning | PLACSP mapping | Generalitat mapping | Normalization, edge cases and unresolved questions |
|---|---|---|---|---|---|
| `observation_id` | ID; 1 / no | Immutable identity of this projection/version | collector | collector | Not `(source ID, timestamp)` and not procurement identity. Reprocessing under a new mapping yields a separately identifiable projection. |
| `raw_source_record_id` | ID; 1 / no | Exactly one immutable input | raw entry occurrence | raw row/body occurrence | Must remain resolvable; never a mutable “latest raw record” pointer. |
| `projection_locator` | String; 1 / no | Selected subject within raw record | root selection | row root, body root, or batch member path | Explicit root marker permitted. Rich batch common headers remain accessible through the raw record. |
| `schema_version` | String; 1 / no | This normalized structural contract | mapping | mapping | Not PSCP `versio`. v1 is a design label, not implementation acceptance. |
| `mapping_version` | String; 1 / no | Reproducible mapping rules and code-list interpretation | mapping | mapping | Must identify exact rule bundle; not wall-clock or canonical revision. |
| `source` | SourceMetadata; 1 / no | Transport and origin context | feed metadata + entry | dataset/body metadata | Fields below; assertions remain attributed to transport source even when origin is PSCP. |
| `source_markers` | SourceMarker[]; 0..N / no | Non-interchangeable record clocks | entry `updated` | Socrata row clocks | Publication release dates go in publications, not here; no maximum-clock calculation. |
| `subject_kind` | enum; 1 / no | `procedure`, `planning`, `batch_member`, `unresolved` | explicit object/phase evidence | ordinary/planning/batch context | `planning` covers pre-procedure information, not an inferred future legal procedure. No default competitive tender. |
| `focus` | Scope; 1 / no | Principal projection scope | normally procedure | lot row, member or procedure; E action's scope | May be `record_subject`/`unknown`; does not override individual fact scopes. |
| `procedure_identifiers` | Identifier[]; 0..N / no | Explicit source procedure object IDs | Atom ID; ordinary origin UUID | ordinary UUID/`idExpedient` | Batch UUID excluded. Framework reference UUID is a related identifier, not identity of this procedure. Q1. |
| `procedure_numbers` | Identifier[]; 0..N / no | Buyer-issued expediente strings | `ContractFolderID` | `codi_expedient`, body/member number | Scheme `procedure_number`; namespace identifies source/buyer context. No aliases imported from older records. |
| `batch_identifiers` | Identifier[]; 0..N / no | Containing publication-batch IDs | — | batch UUID | Numeric notice ID belongs in publication identifiers; do not label it a member ID. |
| `member_identifiers` | Identifier[]; 0..N / no | Explicit batch-entry identity | — | complete `id_intern` with member role; explicit rich member ID if supplied | Do not infer ID from array position or number suffix. J14 members have no verified stable ID in the inspected body. |
| `related_identifiers` | RelatedIdentifier[]; 0..N / no | Explicit external links that do not establish same-subject identity | explicit references only | J14 `expedientIdReferencia` and companion fields | No entity resolution; relation may remain `related_unspecified`. |
| `titles` | Text[]; 0..N / no | Procedure/member-level title assertions | PP `Name`; distinct Atom display title as labelled variant, or fallback if PP Name absent | `denominacio`, JB title | Lot title stays in Lot. Preserve differing explicit title variants with source roles, not one silently selected translation. |
| `descriptions` | Text[]; 0..N / no | Procedure/member description | explicit description | `objecte_contracte`, JB/member description | No title duplication fallback; batch description need not create a title. |
| `buyer` | Party; 0..1 / yes | Buyer exactly as identified by this record | LocatedContractingParty/Party | row buyer; J `organ` | Not “current buyer” across time. Parent hierarchy remains raw unless named attribute below. Q7. |
| `contract_type` | MappedCode; 0..1 / yes | Reported contract nature, §10 | PP `TypeCode` | `tipus_contracte`, JB/member type | Coarse normalized category plus exact source Code; not inferred from CPV. |
| `mixed_contract` | Boolean; 0..1 / yes | Explicit mixed-contract declaration | `MixContractIndicator` | `JB.contracteMixt` | Missing is not false. No separate synthetic “mixed” primary contract type. |
| `procurement_method` | MappedCode; 0..1 / yes | Reported method, §10 | `TenderingProcess/ProcedureCode` | `procediment`, JB method | Unknown source category remains unmapped. |
| `procurement_attributes` | ProcurementAttribute[]; 0..N / no | Limited ancillary dimensions | subtype, urgency, contracting system | type-specific qualifier, urgency, rationalization | Not an arbitrary metadata dictionary. Exact permitted kinds below. |
| `statuses` | Status[]; 0..N / no | Source lifecycle/phase assertions | status code | `fase_publicacio`; body phase | Distinct dimensions; outcomes below. No inferred current-open boolean. |
| `classifications` | Scoped<Classification>[]; 0..N / no | CPVs and their scope | project/lot classification | row CPV; rich typed CPV objects | Only CPV normalized in v1. Unknown source classifications stay raw. |
| `financials` | Scoped<Money>[]; 0..N / no | Estimates and tender budgets | project/lot BudgetAmount | documented procedure/lot fields; rich equivalents | Allowed purposes here: `estimated_value`, `tender_budget`; award/action money has separate owners. |
| `deadlines` | Scoped<Deadline>[]; 0..N / no | Offer/request/document deadlines | named TenderingProcess periods | offer column; rich combined field | Lot-specific only if explicitly scoped; no guessed applicability. |
| `execution_locations` | Scoped<Location>[]; 0..N / no | Places of performance | RealizedLocation at correct level | row execution fields; rich location | Buyer and supplier addresses cannot populate this field. |
| `performance_periods` | Scoped<PerformancePeriod>[]; 0..N / no | Reported planned/contract execution intervals or durations | PlannedPeriod | `durada_contracte`; rich period fields | Keep relative duration and conditional text; never generate actual effective dates. |
| `lots` | Lot[]; 0..N / no | Source lot occurrences within this input | ProcurementProjectLot | one main lot row; real JL lots | Absence is not no-lots; no-lots containers do not generate Lot. Q1. |
| `publications` | PublicationReference[]; 0..N / no | Publication occurrences/phase references | VN and explicit link notice | phase dates/links; rich body | Can represent multiple dates/media without unique notice IDs. |
| `outcomes` | Outcome[]; 0..N / no | Positive/negative result assertions | TR result | `resultat`, explicit rich result | An unsuccessful result need not create an Award. |
| `awards` | Award[]; 0..N / no | Reported award-information groups | positive TR or explicit award facts | award columns, rich contractor/award grouping | Group is not necessarily one legal award decision; retained historical award permitted. |
| `execution_actions` | ExecutionAction[]; 0..N / no | Already reported contract actions | ContractModification | E row; J action arrays | Do not compute a revised contract state. |
| `documents` | SourceDocumentReference[]; 0..N / no | Source document links/metadata | all applicable reference trees | rich document objects, supported legacy equivalents | Not phase export links and not locally verified binaries. |
| `source_references` | SourceReference[]; 0..N / no | Original pages, profile links and export representations | Atom link/profile/notice URLs | page/export URLs | Exact URL preserved; export format is not inferred from path. |
| `coverage` | Coverage[]; 0..N / no | Explicit collection coverage information | source structure/mapping limit | row projection/body scope | Default unknown; complete means only the explicitly stated source scope, not complete history. |
| `issues` | Issue[]; 0..N / no | Mapping/missingness/ambiguity diagnostics | mapping | mapping | No confidence score or reconciliation conflict resolution. |

| SourceMetadata field | Type; cardinality / nullable | Meaning and mapping | Edge cases / questions |
|---|---|---|---|
| `system` | enum `placsp`/`gencat`; 1 / no | Acquired source, not subject nationality | Future values require versioned extension. |
| `dataset` | String; 1 / no | Feed collection, `ybgg-dgi6`, `8idu-wkjv`, or named PSCP publication representation family | Preserve native vs aggregated P and table vs rich G. |
| `record_kind` | enum; 1 / no | `procedure_snapshot`, `procedure_projection`, `lot_projection`, `batch_member_projection`, `publication_body`, `batch_publication_body`, `execution_action_projection` | Source shape, not lifecycle; rich legacy vs modern format remains raw metadata. |
| `record_identifiers` | Identifier[]; 0..N / no | Entry ID, both G row IDs, or explicit body notice ID | IDs may be absent without invalidating immutable raw occurrence identity. |
| `origin_platform` | Code; 0..1 / yes | P AgentParty origin or G's own PSCP context | `62` is an origin platform, never buyer/supplier. No independent-source voting. |

| SourceMarker field | Type; cardinality / nullable | Meaning and mapping | Edge cases / questions |
|---|---|---|---|
| `kind` | enum; 1 / no | `placsp_entry_publication_updated`, `socrata_row_created`, `socrata_row_updated` | Exact semantics, no common freshness ordering. |
| `at` | TemporalValue; 1 / no | P entry `updated`; G `:created_at`/`:updated_at` | Source values also remain raw; no duplicate feed/view clocks here. |

## 6.3 Shared identity, code, scope and text types

| Field | Type; cardinality / nullable | Semantics | P mapping | G mapping | Normalization / edge / uncertainty |
|---|---|---|---|---|---|
| `Identifier.scheme` | String; 1 / no | Source identifier scheme | schemeName/known Atom or notice namespace | named row/UUID/number scheme; supplier type if verified | Use explicit `source_unclassified` scheme if unknown, not guessed NIF. |
| `Identifier.namespace` | String; 1 / no | Issuer/dataset/owning-subject scope | feed, origin platform, buyer or procedure context | dataset, PSCP, buyer, procedure/batch context | Locally qualified namespace allowed when source scope unknown; never implies global uniqueness. |
| `Identifier.value` | String; 1 / no | Exact identifier token | original text | original text/numeric lexical value | Preserve zeros/case/punctuation; URI UUID case normalization is not needed here. Empty token cannot become Identifier. |
| `Identifier.role` | enum; 1 / no | `record`, `procedure`, `procedure_number`, `publication`, `batch`, `member`, `lot`, `buyer`, `supplier`, `award`, `contract`, `action`, `document`, `related` | structural context | structural context | Same token may occur in different roles; never merge by value alone. |
| `Identifier.usability` | enum; 1 / no | `unvalidated`, `usable`, `placeholder`, `invalid` for identifier syntax/known sentinels, not entity-resolution confidence | verified scheme checks | e.g. placeholder DIR3 patterns evidenced locally | Unknown stays unvalidated; `usable` does not prove uniqueness/stability. Q1/Q9. |
| `RelatedIdentifier.identifier` | Identifier; 1 / no | Referenced source identity | explicit source reference | J14 reference UUID/number | Identifier role `related`; do not add to procedure identity set. |
| `RelatedIdentifier.relation` | enum; 1 / no | `framework_reference`, `related_unspecified` | explicit source relation | J14 explicit framework context | Only normalize framework relation when context establishes it; no title-based inference. |
| `Code.system` | String; 1 / no | Source vocabulary identity | full list URI, or source field namespace | API field/category namespace | Do not invent a code-list URI. |
| `Code.version` | String; 0..1 / yes | Explicit source list/schema version | list/version attribute or unequivocal URI version | only explicitly supplied | Not normalized schema version; Q3. |
| `Code.value` | String; 1 / no | Raw code, or literal label for label-only source | code text | numeric ID or original table label | No coercion of unrelated numeric IDs to the same code. |
| `Code.labels` | Text[]; 0..N / no | Explicit source labels | source label attributes where present | rich language labels | No unsourced translation. |
| `MappedCode.source` | Code; 1 / no | Original source category | source code | source code/label | Even when mapping succeeds, keep original. |
| `MappedCode.normalized` | String; 0..1 / yes | Defined normalized vocabulary value | validated dictionary | validated label/category mapping | Null for unmapped or unsupported; source “Other” is an explicit value, not fallback for unknown. |
| `MappedCode.mapping` | enum; 1 / no | `exact`, `broader`, `unmapped` | mapping rules | mapping rules | `broader` e.g. Annex IV services → services; not reconciliation confidence. |
| `LocalizedText.text` | String; 1 / no | Source text | project/party/etc. text | row string/language value | Preserve meaning/format; a literal `null` string in a language map is flagged, not accepted as a translation. |
| `LocalizedText.language` | language tag; 0..1 / yes | Only known language | XML language attribute if it actually describes this text | rich map key; otherwise unknown | Code-list `languageID=es` does not prove Atom title language. |
| `LocalizedText.source_role` | String; 0..1 / yes | Distinguishes variants such as project title versus Atom display title | `project_name`, `atom_title`, etc. | field role when needed | Not a preferred-language decision. |
| `Scope.kind` | enum; 1 / no | `procedure`, `lots`, `record_subject`, `publication_batch`, `unknown` | source containment/explicit references | documented fields and row/body context | No heuristic promotions between levels. |
| `Scope.lot_keys` | Key[]; 0..N / no | Explicitly resolved embedded lot occurrence(s) | direct unambiguous lot reference | same row/object lot | Only with `kind=lots`; no match if number points at multiple occurrences. |
| `Scope.source_lot_identifiers` | Identifier[]; 0..N / no | Original lot references, including unresolved ones | awarded-project lot ID | explicit lot number/internal ID | `kind=lots` requires a local key or source lot identifier. Other scope kinds have empty lot lists. |
| `Scoped<T>.source_path` | String; 1 / no | Path(s) within this raw input for the scoped item | qualified XML path with occurrence position | JSON pointer/column selection | A joined-field item may use an unambiguous composite path notation documented by mapping version. |
| `Scoped<T>.scope` | Scope; 1 / no | Applicability of T | source structure | row/field semantics | `record_subject` is deliberately weaker than procedure. |
| `Scoped<T>.value` | T; 1 / no | Value of the scoped item | defined per T | defined per T | No implicit inheritance. |

For repeated source-derived objects below, `key: Key (1)` and `source_path: String (1)` are called **Item fields**. Every occurrence of `Lot`, `PublicationReference`, `Outcome`, `Award`, `ExecutionAction`, `SourceDocumentReference` and `SourceReference` includes them. They are generated respectively from local identity needs and the exact input locator in both sources. They identify occurrences only; they introduce no globally persistent entity ID. `SupplierAllocation` additionally uses these fields to retain positions within an award group.

## 6.4 Parties, classifications and ancillary categories

| Field | Type; cardinality / nullable | Meaning / P mapping | G mapping | Normalization / edges / unresolved questions |
|---|---|---|---|---|
| `Party.kind` | enum; 1 / no | `organization`, `person`, `consortium`, `unknown`; explicit party/UTE evidence only | explicit rich consortium data or type | Do not infer legal form from company-name punctuation or a tax-number prefix. |
| `Party.identifiers` | Identifier[]; 0..N / no | PartyIdentification IDs | buyer `codi_organ`/DIR3/J NIF; supplier ID/type | AgentParty is not a buyer ID. P aggregation lacking NIF does not justify filling it from another record. |
| `Party.names` | Text[]; 0..N / no | PartyName | `nom_organ`, `denominacio_adjudicatari`, rich names | Name-only supplier is valid. No legal-name cleanup that changes content. |
| `Party.addresses` | Location[]; 0..N / no | Party postal addresses | J buyer/contractor addresses | Main execution location never used as party address. Contacts and hierarchy stay raw. |
| `ProcurementAttribute.kind` | enum; 1 / no | `contract_subtype`, `contract_qualifier`, `urgency`, `contracting_system` | corresponding G subtype/Annex IV qualifier/tramitació/rationalization | Closed list in v1; no universal taxonomy for these attributes. |
| `ProcurementAttribute.value` | Code; 1 / no | Original category code/label | original source category | Preserve legacy legal distinctions; no attempt to equate every source system. |
| `Classification.system` | literal `CPV`; 1 / no | CPV scheme | CPV scheme | Other classifications remain raw until deliberately added. |
| `Classification.code` | String; 0..1 / yes | Normalized eight digits | parse G check-digit form | Null if invalid; never take an arbitrary eight-character prefix. |
| `Classification.check_digit` | String; 0..1 / yes | Explicit check digit if source supplies it | split verified `NNNNNNNN-N` form | Do not invent missing check digit; validation issue if inconsistent. |
| `Classification.raw_code` | String; 1 / no | Exact ItemClassificationCode | exact codi_cpv/token | Code list URI and version separately retained. |
| `Classification.source_system` | String; 0..1 / yes | `listURI` | explicit rich code-list identity if present | CPV system known does not establish a particular code-list release. |
| `Classification.version` | String; 0..1 / yes | explicit list version | explicit only | Q3; do not infer from acquisition year. |
| `Classification.role` | enum; 1 / no | `main`, `additional`, `unspecified` as source establishes | JL `cpvPrincipal.codi` establishes main (J01/J20); J14 member `codiCpv.codi` and table `codi_cpv` do not independently establish a main/additional distinction | First item in an array is not automatically the main CPV. |

Party has no standalone supplier registry ID, temporal aliases or consortium membership graph. Raw consortium member details remain available; `kind=consortium` and its reported identifiers/names preserve the currently essential distinction without inventing constituent winners.

## 6.5 Money, deadlines, locations and performance periods

| Field | Type; cardinality / nullable | Meaning | P mapping | G mapping | Normalization / edge cases / questions |
|---|---|---|---|---|---|
| `Money.purpose` | enum; 1 / no | `estimated_value`, `tender_budget`, `award_amount`, `action_amount`, `modification_delta`, `contract_total_after_modification` | exact monetary subtree | documented column/action meaning | Never generic amount. Parent supplies scope/attribution. |
| `Money.value` | Decimal; 0..1 / yes | Parsed exact amount | text decimal | number/string/token | Nullable only for explicit empty/invalid token; zero remains zero, negative modification is permitted. |
| `Money.raw_value` | String; 1 / no | Original scalar/token lexical representation | amount text | numeric lexical value or exact split token | Needed for empty versus zero and reproducibility; preserve original JSON number precision through raw artifact. |
| `Money.value_state` | enum; 1 / no | `valid`, `explicit_empty`, `invalid` | parse assessment | parse/token assessment | `value` non-null iff valid. Missing field produces no Money, not zero or empty Money. |
| `Money.currency` | ISO currency code; 0..1 / yes | Explicitly established currency | `currencyID` | explicit source currency only | G table absent → null. Q4; no inferred EUR from geography or matching P record. |
| `Money.tax_basis` | enum; 1 / no | `excluded`, `included`, `unspecified` | TaxExclusive vs Total/Payable; estimate per supported meaning | sense/amb IVA, documented estimate | Tax basis reflects source definition, not guessed effective tax rate. |
| `Money.vat_rate` | Decimal percent; 0..1 / yes | Explicit single VAT rate applicable to this amount context | explicit tax data only | rich `iva` with clear context | Do not calculate from net/gross. If multiple rates true, leave single rate null unless explicitly applicable to a component. |
| `Money.multiple_vat_rates` | Boolean; 0..1 / yes | Source declares multiple VAT rates | explicit only | rich `varisTipusIva` | Null in main table; false is not no VAT. |
| `Deadline.kind` | enum; 1 / no | `offers`, `participation_requests`, `submission_unspecified`, `document_access` | named period: TenderSubmissionDeadlinePeriod, ParticipationRequestReceptionPeriod, document-access period | offer column; rich combined deadline requires context | No forced “offers” for ambiguous combined rich field. |
| `Deadline.at` | TemporalValue; 0..1 / yes | Deadline date/time | EndDate + EndTime | floating table/rich timestamp | Can be null for text-only period; date-only never becomes end-of-day. |
| `Deadline.notes` | Text[]; 0..N / no | Explicit textual deadline conditions | period description | explicit rich/text conditions | At least time or notes required; no semantic NLP extraction in v1. |
| `Location.names` | Text[]; 0..N / no | Source location labels | CountrySubentity/city labels | lloc_execucio/rich names | Labels do not by themselves establish municipality codes. |
| `Location.nuts_code` | String; 0..1 / yes | Explicit NUTS code | CountrySubentityCode | codi_nuts/rich code | Preserve source code, validate separately; ES511 not Barcelona city. |
| `Location.nuts_version` | String; 0..1 / yes | Explicit NUTS release | list URI e.g. NUTS-2021 | explicit only | No current-year assumption. |
| `Location.country_code` | String; 0..1 / yes | Explicit country code with known scheme | PostalAddress/Country code | rich country only after verified mapping | Numeric PSCP country ID is not ISO; unknown remains in raw/issues. |
| `Location.locality` | String; 0..1 / yes | Reported town/locality text | CityName | rich localitat/municipi label | Can be composite text, e.g. province + town; no geocoding. |
| `Location.postal_code` | String; 0..1 / yes | Reported postcode | PostalZone | codiPostal | Preserve leading zeroes; geography role comes from owner. |
| `Location.address` | String; 0..1 / yes | Reported street/address text | address components joined losslessly | direccioPostal/adreca | Original components still raw; no address entity resolution. |
| `PerformancePeriod.kind` | enum; 1 / no | `planned`, `reported_execution`, `unspecified` | PlannedPeriod → planned | explicit batch execution interval → reported_execution; bare duration column → unspecified | Distinguish kind instead of equating all periods with effective contract dates. |
| `PerformancePeriod.raw_text` | Text[]; 0..N / no | Original duration/conditional-period text | period description | durada_contracte/observacions | Structured-only period may have none. |
| `PerformancePeriod.start_at` | TemporalValue; 0..1 / yes | Explicit period start | StartDate | explicit interval/date fields | No default start at award or publication. |
| `PerformancePeriod.end_at` | TemporalValue; 0..1 / yes | Explicit period end | EndDate | explicit interval/date fields | Do not add duration to an unknown/conditional start. |
| `PerformancePeriod.duration` | DurationPart[]; 0..N / no | Explicit duration components | DurationMeasure + unitCode | duradaTermini anys/mesos/dies; unambiguous parsed text | Months/years retained, not converted to days. Ambiguous text remains text. |
| `DurationPart.value` | Decimal; 1 / no | Reported numeric duration | measure | component | No rounding. |
| `DurationPart.unit` | enum; 1 / no | `years`, `months`, `days`, `hours`, `unspecified` | verified unitCode | documented component/unit | Unrecognized unit → unspecified and issue; original is raw. |

A location must have at least one reported component; a period must have text, a boundary or a duration. These are meaningful-value constraints, not completeness guarantees.

## 6.6 TemporalValue

This value type is shared by all time-bearing fields; **the containing field supplies its event role**. It avoids a misleading generic business `date` or `updated_at`.

| Field | Type; cardinality / nullable | Meaning / mapping in both sources | Normalization / edge cases / questions |
|---|---|---|---|
| `raw` | String; 1 / no | Original timestamp, date, or explicitly joined P date/time components | Joining must retain both exact components through source path/raw artifact. |
| `local_date` | calendar date; 0..1 / yes | Parsed calendar date in source representation | Not derived UTC date for date-only business facts. |
| `local_time` | clock time; 0..1 / yes | Reported clock component when semantically meaningful | No midnight insertion for date-only values. |
| `utc_instant` | UTC instant; 0..1 / yes | Instant only when precision and timezone interpretation support it | Must be null for a date-only fact; do not turn assumed date serialization into an exact legal instant. |
| `offset` | UTC offset; 0..1 / yes | Explicit source offset, including Z | P and modern J often supply; G floating application fields do not. |
| `zone` | IANA zone; 0..1 / yes | Explicit or transparently interpreted zone, e.g. Europe/Madrid | An offset alone does not establish an IANA zone. |
| `zone_basis` | enum; 1 / no | `explicit_offset`, `documented_zone`, `assumed_zone`, `unknown`, `not_applicable` | G floating → unknown by default; assumption only explicit and issue-recorded. Date-only → not_applicable. Q2. |
| `precision` | enum; 1 / no | `day`, `minute`, `second`, `fractional_second`, `unknown` semantic precision | Do not infer precision solely from `.000`; supported minute truncation or calendar-date role can be coarser than lexical encoding. |
| `precision_basis` | enum; 1 / no | `documented`, `observed_projection`, `lexical_only`, `unknown` | Distinguishes measured projection behavior from publisher guarantee. Do not generalize C13 to every arbitrary timestamp. |

If parsing fails, retain a TemporalValue with `raw`, unknown precision/zone and null parsed components, plus an issue. Syntactic calendar values and semantic precision are distinct. A floating local time during a DST overlap/gap must not silently become a unique UTC instant. §7 specifies the event roles and defaults.

## 6.7 Status and lots

| Field | Type; cardinality / nullable | Meaning / P mapping | G mapping | Normalization / edges / questions |
|---|---|---|---|---|
| `Status.source_path` | String; 1 / no | Path of source status assertion | phase column/body field | Retains which status dimension was actually reported. |
| `Status.scope` | Scope; 1 / no | Procedure for P global status; explicit lot only if supplied | Main row phase uses record_subject, not a claim for every lot; body phase uses publication's subject scope | Do not promote phase across companion rows. |
| `Status.dimension` | enum; 1 / no | `procurement_lifecycle` or `publication_phase` | Normally publication_phase | Result/outcome is a separate structure. |
| `Status.value` | MappedCode; 1 / no | Source status code and §9 mapping | source phase and §9 mapping | Unknown code retained, no default closed. |
| `Lot.key`, `Lot.source_path` | Item fields; 1 each / no | Embedded occurrence and exact source position | one lot row or real rich lot object | Observation-local, not globally stable lot entity. |
| `Lot.identifiers` | Identifier[]; 0..N / no | Explicit lot IDs | numero_lot/numeroLot and distinct lotId if provided | Number can also be a scoped identifier; `id_intern` remains record ID, not assumed lot ID. |
| `Lot.number` | String; 0..1 / yes | Display lot number | displayed source number | Preserve text; no unique-number constraint or ordinal replacement. |
| `Lot.titles` | Text[]; 0..N / no | Project lot Name | explicit lot title if supplied | Do not relabel a source description as title without a source-specific rule. |
| `Lot.descriptions` | Text[]; 0..N / no | Explicit lot description | descripcio_lot/JL.descripcio | Lot-scoped CPV, money, deadlines, locations and results are in their respective scoped collections, not duplicated here. |

## 6.8 Publications, outcomes, awards and suppliers

A `PublicationReference` is one source-supported publication occurrence or phase reference, **not a unique notice entity**. One official notice may have several occurrences/media; one occurrence may have no ID. Source groups are not equated by type and date alone.

| Field | Type; cardinality / nullable | Meaning / P mapping | G mapping | Normalization / edges / questions |
|---|---|---|---|---|
| `PublicationReference.key`, `.source_path` | Item fields; 1 each / no | Exact source publication occurrence/reference | phase column/link or body | For VN preserve group/media/document occurrence paths. |
| `.scope` | Scope; 1 / no | What publication reference concerns | procedure/lot/member/batch according to evidence | Batch dates are publication_batch, never each member's independent release. |
| `.identifiers` | Identifier[]; 0..N / no | Explicit notice identifiers, not arbitrary attachment IDs | numeric PSCP notice IDs | Date/type alone does not generate a fake source notice ID. |
| `.type` | MappedCode; 0..1 / yes | VN NoticeTypeCode normalized to §9 phase family | phase or phase-specific field | URL-only unknown notice can have null type. Correction is a qualifier, not necessarily replacement type. |
| `.medium` | String; 0..1 / yes | VN PublicationMediaName; PLACSP for explicitly PLACSP release date | PSCP when documented by field/body context | Free text, not a fixed publication-media enum. |
| `.publication_at` | TemporalValue; 0..1 / yes | VN NoticeIssueDate or individual media IssueDate, separately scoped | phase date or dataPublicacioReal | Never entry updated as fallback. Conflicting dates from the same record remain distinct occurrences with issue. |
| `.planned_publication_at` | TemporalValue; 0..1 / yes | — | dataPublicacioPlanificada | Only on relevant rich-body occurrence. |
| `.sent_at` | TemporalValue; 0..1 / yes | VN AdditionalPublicationRequest/sendDate + sendTime | explicit dispatch date only if separately established | No copy of publication date. |
| `.is_correction` | Boolean; 0..1 / yes | explicit correction type/relation only | meaningful nonempty tipusEsmena/motiuEsmena or explicit correction flag | Empty objects/labels are not evidence of correction. Null when unknown, not false by absence. |
| `.correction_type` | Text[]; 0..N / no | explicit correction detail | tipusEsmena labels | Correction can concern opening details, not deadline. |
| `.correction_reason` | Text[]; 0..N / no | explicit reason | motiuEsmena | No inferred legal cause from changed amount. |
| `.relations` | SourceRelation[]; 0..N / no | Explicit source publication relationship | explicit source relationship if provided | Never infer supersedes merely from later date. |
| `SourceRelation.kind` | enum; 1 / no | `corrects`, `replaces`, `withdraws`, `supplements`, `related_unspecified` | same | Only supported relations; exact ambiguous detail stays raw. |
| `SourceRelation.target_identifiers` | Identifier[]; 1..N / no | Explicit related publication/document IDs, with correct role | same | No canonical entity link; if target absent retain correction metadata without fake relation. |
| `Outcome.key`, `.source_path` | Item fields; 1 each / no | Source result occurrence | row result or rich result object | Do not merge separate result occurrences. |
| `.scope` | Scope; 1 / no | TR awarded-project lot references, else supported scope | row lot/member or explicit body scope | P missing lot reference in multi-lot record can be unknown, not automatically procedure. |
| `.result` | MappedCode; 1 / no | TR ResultCode | resultat/explicit rich reason-result | §9 outcome taxonomy; annulment phase alone is not a result reason. |
| `.decision_at` | TemporalValue; 0..1 / yes | TR AwardDate is date of this result decision | explicit result-decision date, not retained old award date | Do not attach G award date to Renúncia outcome. |
| `.reasons` | Text[]; 0..N / no | TR Description | explicit result reason | No inferred rescission reasoning. |
| `.publication_keys` | Key[]; 0..N / no | Explicitly associated publication occurrences | explicitly related publication | Do not associate all results with Atom link or row page by default. |
| `Award.key`, `.source_path` | Item fields; 1 each / no | Source award-information grouping | award columns as row group or rich group | Not a stable legal decision ID. |
| `.scope` | Scope; 1 / no | AwardedTenderedProject lot references or documented scope | row lot/member or explicit rich scope | Multiple lots allowed; unknown remains explicit. |
| `.identifiers` | Identifier[]; 0..N / no | Explicit award ID if actually supplied | explicit award ID if supplied | Do not manufacture award ID from notice or contract ID. |
| `.grouping` | enum; 1 / no | `source_result`, `source_row_group`, `source_award_object` | row group / explicit rich grouping | Describes evidence grouping, not number of legal decisions. |
| `.decision_at` | TemporalValue; 0..1 / yes | Positive award's TR AwardDate | data_adjudicacio_contracte/JL.dataAdjudicacio | Award information retained after negative outcome is allowed; validity is not inferred. |
| `.amounts` | Money[]; 0..N / no | Explicit award-group totals | scalar/group total only if semantics establish it | Purpose award_amount. If G amount clearly belongs to one winner, put it under that allocation, not also here. |
| `.suppliers` | SupplierAllocation[]; 0..N / no | WinningParty occurrences | aligned tokens or rich empresaContractista objects | Not exactly one; empty winner list can still be award evidence. |
| `.contract_references` | ContractReference[]; 0..N / no | TR Contract info | formalization date/explicit contract info | Preserve formalization separately; do not force one legal contract per group. |
| `.outcome_keys` | Key[]; 0..N / no | Result in same explicit P grouping | same explicit award/result grouping | Do not automatically link retained award to later withdrawal as “rescinded.” |
| `.publication_keys` | Key[]; 0..N / no | Source-established associated notice | explicit award publication/body association | Main page URL alone is insufficient to attach all old award facts. |
| `SupplierAllocation.key`, `.source_path` | Item fields; 1 each / no | One supplier-position/group occurrence | token/object locator | Local identity only; retain empty positions when relevant. |
| `.source_position` | nonnegative integer; 0..1 / yes | Original supplier ordinal | token or array ordinal, zero-based in normalized representation | Zero-based normalization does not change source lot numbers. |
| `.party` | Party; 0..1 / yes | WinningParty | supplier fields or contractor object | Null for amount-only/unresolved positional token; never create empty Party. |
| `.amounts` | Money[]; 0..N / no | Explicitly supplier-attributed amounts, not TR totals copied to each party | aligned per-winner amounts per G metadata | Grouping ambiguity preserved; do not split a group amount evenly. |
| `.alignment` | enum; 1 / no | `structured`, `positional`, `unresolved` | structured body / compatible table tokens / ambiguous vectors | Cardinality mismatch means no guessed zip, no Cartesian product; §11. |
| `ContractReference.source_path` | String; 1 / no | Exact contract/date source position: TR Contract or StartDate context | row/body contract date fields | A date-only contract reference is valid; not a stable Contract entity. |
| `.identifiers` | Identifier[]; 0..N / no | Explicit contract numbers/IDs: TR Contract/ID | explicit contract IDs only | A procedure number or publication ID is not a contract ID. |
| `.formalized_at` | TemporalValue; 0..1 / yes | Contract formalization: TR Contract/IssueDate | data_formalitzacio_contracte/JL.dataFormalitzacio | Separate from publication date; multiple references allowed. |
| `.effective_at` | TemporalValue; 0..1 / yes | Contract entry into force: TR StartDate when linkage is explicit or unambiguous | explicit contract entry-into-force field only | Do not copy onto all contracts if relation is ambiguous; use separate unidentified contract reference and issue. |

A ContractReference needs an ID or a date. An Award needs positive award/result evidence, an explicitly reported award date/amount, a reported awardee, or contract formalization information in an award context. A negative TR with zero monetary placeholders alone does **not** justify a positive Award: retain its monetary/source peculiarities raw and flag if necessary. Mere publication phase `Adjudicació` can support a phase reference without inventing an award decision object with no details.

## 6.9 Execution actions and original material

| Field | Type; cardinality / nullable | Meaning / P mapping | G mapping | Normalization / edges / questions |
|---|---|---|---|---|
| `ExecutionAction.key`, `.source_path` | Item fields; 1 each / no | ContractModification occurrence | E row or typed J action object | No stable action entity inferred. |
| `.scope` | Scope; 1 / no | Explicit procedure/lot reference | numero_lot or rich containing subject | Action may exist without identified procedure UUID/main row. |
| `.identifiers` | Identifier[]; 0..N / no | ContractModification/ID | rich identificador; E row IDs stay source-record IDs | Scope action ID by source subject, action type and publication context until stability verified. |
| `.contract_identifiers` | Identifier[]; 0..N / no | ContractModification/ContractID | explicit contract ID if present | Do not resolve to a Contract entity. |
| `.type` | MappedCode; 1 / no | modification structure | tipus_actuacio_execucio / tipusActuacioExecucio | §9 action taxonomy; unfamiliar type retained unmapped. |
| `.titles` | Text[]; 0..N / no | explicit action name | denominacio_actuacio/denominacioModificacio | Not procedure title. |
| `.action_at` | TemporalValue; 0..1 / yes | only explicitly provided action date | E data; typed rich date such as dataModificacio | No use of publication date as fallback. |
| `.end_at` | TemporalValue; 0..1 / yes | explicit action end | E data_fi/typed rich end | Not procedure completion or notice expiry. |
| `.amounts` | Money[]; 0..N / no | modification delta and post-modification total in distinct paths | E generic action amount; J incrementPreu | E amount does not become a delta just because a separate rich body suggests it. |
| `.parties` | Party[]; 0..N / no | explicit action parties | E identificacio/denominacio; J contractistes | Do not label them original winning suppliers; role is action participant. |
| `.details` | Text[]; 0..N / no | modification observations | E observacions/rich explicit action details | Not an interpreted legal effect. |
| `.publication_keys` | Key[]; 0..N / no | explicit linked publication | E url_json/body publication | J19: two action keys can reference same publication key. |
| `SourceDocumentReference.key`, `.source_path` | Item fields; 1 each / no | reference occurrence, including nested references | rich language/document occurrence | Preserve duplicates across contexts rather than canonicalize. |
| `.scope` | Scope; 1 / no | source parent/explicit lot scope | source parent/explicit scope | Unknown scope permitted. |
| `.identifiers` | Identifier[]; 0..N / no | DocumentReference/ID when it is an ID | rich id | P ID may be filename-like: scoped source document identifier, not global binary ID. |
| `.role` | MappedCode; 0..1 / yes | legal, technical, additional, notice/result context | plecsDeClausulesAdministratives, plecsDePrescripcionsTecniques, other typed containers | Roles: administrative_specification, technical_specification, notice, award_document, correction_document, supporting_document, other; unknown stays null/unmapped. |
| `.titles` | Text[]; 0..N / no | ID/name/document title | titol | Do not use filename as guaranteed MIME type. |
| `.language` | language tag; 0..1 / yes | explicit document language | idioma/container language | No language inference from URL alone. |
| `.urls` | URI string[]; 0..N / no | exact ExternalReference/URI | actual explicit download URLs when supplied/verified in same record | IDs/path tokens alone are not usable URLs; link back through source page otherwise. |
| `.source_path_token` | String; 0..1 / yes | source delivery token/path, not extraction locator | rich path | Preserve opaque value without guessing endpoint; Q8. |
| `.reported_hash` | ReportedHash; 0..1 / yes | explicit hash metadata | rich hash | Reported, not locally verified; no algorithm inference from string length. |
| `.reported_size_bytes` | nonnegative integer; 0..1 / yes | explicit size | mida where defined as bytes by supported mapping | Unit must be established; otherwise retain raw and issue. |
| `.declared_media_type` | String; 0..1 / yes | explicit MIME metadata | explicit MIME metadata if present | Not response Content-Type of an unrelated publication export. |
| `.publication_keys` | Key[]; 0..N / no | explicit notice containment | body publication association | An entry-level document need not be assigned to every VN. |
| `.relations` | SourceRelation[]; 0..N / no | explicitly corrects/replaces/etc. | explicitly provided relation | No canonical/latest-document selection. |
| `ReportedHash.value` | String; 1 / no | Source checksum/digest spelling | source hash | Preserve original case. |
| `ReportedHash.algorithm` | String; 0..1 / yes | Explicitly identified algorithm only | explicit only | An apparent 32-hex value is not automatically verified MD5. |
| `SourceReference.key`, `.source_path` | Item fields; 1 each / no | source URL occurrence | original field/URL occurrence | Transport acquisition URL remains raw; this is business/source navigation. |
| `.url` | URI string; 1 / no | Exact original reference | enllac_publicacio.url, url_json_*.url, execution export | Keep original host/path/query, including legacy route. |
| `.target_kind` | enum; 1 / no | `procedure_page`, `publication_page`, `buyer_profile`, `publication_export`, `other`, `unknown` | field/URL meaning | Do not call a phase export a tender attachment. |
| `.identifiers` | Identifier[]; 0..N / no | Explicit/verified parsed target IDs | same | Guard hostname and route; batch UUID retains batch role. |
| `.publication_keys` | Key[]; 0..N / no | Explicitly referenced publication occurrence(s) | phase export association if supported | Main link and corrected phase export can reference different publications. |

## 6.10 Coverage, issues and raw provenance contract

| Field | Type; cardinality / nullable | Meaning / both-source mapping | Edges / unresolved questions |
|---|---|---|---|
| `Coverage.path` | String; 1 / no | Normalized collection path, e.g. lots or awards/suppliers | Can identify nested local item path. |
| `Coverage.scope` | Scope; 1 / no | Scope within which coverage is asserted | Never “all source history” unless explicitly evidenced; not claimed here. |
| `Coverage.state` | enum; 1 / no | `unknown`, `partial`, `source_declares_complete`, `source_declares_empty` | Main lot row inventory partial. Source no-lots declaration can support source_declares_empty. Empty JSON list alone does not prove global emptiness. |
| `Coverage.basis` | String; 1 / no | Source path or explicit projection-limitation explanation | A “complete” claim requires source-backed basis; otherwise unknown/partial. |
| `Issue.code` | String; 1 / no | Stable diagnostic category | Initial categories: invalid_value, explicit_empty, placeholder_identifier, unmapped_code, uncertain_scope, ambiguous_time, uncertain_precision, supplier_alignment, inconsistent_source_values, unsupported_structure. |
| `Issue.path` | String; 1 / no | Affected normalized or explicitly labelled raw path | Can target omitted/unmapped values; no need to invent a normalized field. |
| `Issue.detail` | String; 1 / no | Concise factual explanation, not reconciliation decision | No secrets or unnecessary personal contact data copied into diagnostics. |

The **raw relationship contract**, not a full RawSourceRecord implementation design, requires these accessible facts:

| Raw-accessible fact | Type / requirement | Semantics |
|---|---|---|
| Raw record identity | ID / required | Target of raw_source_record_id. |
| Acquisition and immutable artifact reference | ID/reference / required | Resolves original bytes, verified checksum and request/response lineage. |
| Record locator and namespace/format context | structured locator / required | Reconstructs exact source occurrence, not merely a pretty extracted JSON file. |
| `observed_at` | UTC instant / required for new acquisitions | Response receipt; existing research retrieval metadata retains its original definition if not exactly receipt. No invented greater precision. |
| `ingested_at` | UTC instant / optional at this design boundary | When raw-record layer accepted occurrence, if tracked. Not a procurement date. |
| Source times and source IDs | original fields / preserved if supplied | Technical row fields, entry/feed clocks, source representation version. |
| Retrieval outcome / availability | original metadata / required as applicable | Failed retrieval is not a procurement cancellation. |

These do not introduce an application class, persistence schema or new acquisition implementation. They state what the normalized provenance pointer must be able to recover.

# 7. Temporal model

## 7.1 Event roles and ownership

| Proposed or considered time | Real-world/system event | PLACSP supplies? | Generalitat supplies? | Comparable? | Ownership / decision |
|---|---|---|---|---|---|
| `observed_at` | Collector receives representation | Collector, not feed | Collector, not table | Yes as collection event, not source business time | Raw; accessible through reference, not duplicated at every nested object. |
| `ingested_at` | Raw occurrence accepted by pipeline | Collector | Collector | Yes if consistently defined | Raw operational metadata; not required to normalize legacy research samples. |
| `source_created_at` | Source record creation | No established entry equivalent | Socrata :created_at, technical row creation | No procedure-creation equivalence | Preserve raw; normalized marker socrata_row_created. Reject procedure_created_at. |
| `source_updated_at` | Ambiguous without source semantics | Entry updated: latest relevant publication marker | Socrata :updated_at: technical row update | No | Do not provide this generic normalized field; typed source_markers instead. |
| Feed/view updated | Feed page/view management | Feed updated | rowsUpdatedAt etc. | Container clocks only | Raw acquisition/container metadata. |
| `publication_at` | Public release in specified medium/phase | VN NoticeIssueDate and media IssueDate | phase columns; rich dataPublicacioReal | Only after aligning occurrence, medium, correction and precision | PublicationReference, repeated; never a root scalar. |
| `planned_publication_at` | Intended publication schedule | No mapped shared field | dataPublicacioPlanificada | Not actual publication | Optional PublicationReference field. |
| `sent_at` | Dispatch to publication medium | VN request sendDate/sendTime | Not established in bulk table | Only explicit dispatch dates | Optional PublicationReference; no invented G mapping. |
| `submission_deadline` | Last submission date/time, with kind | offer and participation-request periods | offer column; rich combined offers/requests field | Qualified by kind/scope/precision | Scoped Deadline.at; no singular unqualified root deadline. |
| Document-access deadline | Last date to obtain tender documents | DocumentAvailabilityPeriod when provided by supported source mapping | No established main-table field | Not offer deadline | Deadline kind document_access; optional. |
| `decision_at` (outcome) | Decision recorded for result | TR AwardDate, even negative outcome | explicit outcome decision only | Only matching decision type | Outcome, not all awards. |
| `decision_at` (award) / proposed `award_at` | Positive award decision | Positive award TR AwardDate | data_adjudicacio_contracte/JL.dataAdjudicacio | Usually same concept, varying precision/scope | Award.decision_at; reject ambiguous root award_at. |
| `formalized_at` | Contract signing/formalization | TR Contract/IssueDate | contract formalization date fields | Same concept, not same publication | ContractReference; may be multiple. |
| `effective_at` | Contract enters into force | TR StartDate, documented | No shared main-table field established | Only when explicit | ContractReference only with supported context. No observation-level effective_at. |
| `action_at`, `end_at` | Reported contract action and its end | Only explicit action fields | E data/data_fi; J typed action date | Must align action type, not phase | ExecutionAction. |
| Period start/end/duration | Planned/reported performance interval | PlannedPeriod | durada_contracte / rich structured period | Only with period kind | Scoped PerformancePeriod, not legal effectiveness inferred from schedule. |
| Opening timestamps | Envelope opening, not submission deadline | Documented/source-specific opening structures | J ultimaObertura/oberturaSobres | Not automatically one comparable event | Deferred structured opening model; preserve raw and correction reasons. |
| `normalized_at` | Mapping run completion | Our system | Our system | Operational only | Optional later job metadata, not business schema requirement. |
| `reconciled_at`, canonical valid times | Later decision / reconstructed legal state | Not source facts | Not source facts | Not applicable yet | Later model, excluded. |

### Main-table phase-date mapping

G metadata [D] defines ten separate date columns. The default mapping pairs a date with its same-phase export field when both are present and consistent; it does **not** attach all dates to `enllac_publicacio`. Missing date or missing export is allowed independently. These pairings identify source-declared phase context, not proof that every other row column belongs to that notice. Q5 covers contradictory pairings.

| Date column | Same-phase export column | Normalized publication type |
|---|---|---|
| `data_publicacio_futura` | `url_json_futura` | future_notice |
| `data_publicacio_consulta` | `url_json_cpm` | market_consultation |
| `data_publicacio_previ` | `url_json_previ` | prior_information |
| `data_publicacio_anunci` | `url_json_licitacio` | tender_notice |
| `data_publicacio_avaluacio` | `url_json_avaluacio` | evaluation |
| `data_publicacio_adjudicacio` | `url_json_adjudicacio` | award_notice |
| `data_publicacio_formalitzacio` | `url_json_formalitzacio` | formalization_notice |
| `data_publicacio_anul` | `url_json_anulacio` | annulment_notice |
| `data_publicacio_contracte` | `url_json_agregada` | aggregate_contract_report; publication_batch scope |
| `data_publicacio_encarrec` | No corresponding export column in inspected G metadata | own_resource_entrustment_notice; preserve a date-only reference |

The entrustment date is a documented field of the already researched main table, not a proposal to acquire a new entrustment feed or design its separate legal model. Its type may be represented even if no such row occurs in a selected cohort. E has no equivalent publication-date column: its `data` must never enter this table. Main rows labelled Execució likewise do not justify inventing `data_publicacio_execucio`.

## 7.2 Precision and timezone rules

1. Preserve the original timestamp and meaningful components. A date is a calendar day, not midnight or 23:59:59 by default.
2. Offset-bearing publication timestamps can be interpreted as instants with their reported precision. A business field whose semantics are date-only may still arrive as midnight-shaped UTC; retain that serialization without asserting legal sub-day precision.
3. G floating application dates remain floating by default. **[O]** Sampled rich UTC/table pairs agree with Europe/Madrid including DST; **[I]** it is a useful interpretation; **[U]** a dataset-wide publisher guarantee was not established. A later approved assumption can set zone_basis=assumed_zone with an issue; never silently treat them as UTC.
4. Precision is not the count of printed zeros. For the empirically validated minute-projection cases use precision=minute, basis=observed_projection. For unverified timestamps use lexical_only/unknown as appropriate, not a universal “seconds are always truncated” rule.
5. G contract/action calendar-date fields can use precision=day when the source context establishes date semantics. If a non-midnight time is meaningfully supplied (C05 award date is a counterexample to blindly stripping all times), retain it and flag uncertainty rather than force date-only conversion.
6. Preserve P EndDate and EndTime independently in raw if one is absent. Incomplete date/time can produce a partial TemporalValue; do not borrow date from another field.
7. No global event ordering, “latest timestamp wins,” source latency calculation or effective interval is part of normalization.

**Worked temporal counterexample [O]:** C01 has original tender publication 300837018 on 11 August 2026, a correction 300885987 on 17 September, and a submission deadline on 14 September unchanged by that correction. G's tender-phase date refers to the correction; P's DOC_CN IssueDate retains 11 August. Preserve both source observations and distinct publication occurrences. Do not manufacture a reopened tender, negative advertising period, or new procedure.

**Execution [O]:** J19 `dataModificacio` serializes March 30 local midnight as `2026-03-29T22:00:00.000Z`. The business calendar date is not the UTC calendar date March 29. Its August publication and September Socrata update are separate facts.

# 8. Identifier model

No identifier below is a canonical procurement ID. Internal observation/local keys express evidence occurrence only. Uniqueness in a frozen snapshot must not become a perpetual database constraint on source identity.

| Identifier | Scope / global uniqueness | Stability evidence | Possible future resolution use | Normalized placement |
|---|---|---|---|---|
| Internal raw record ID | Collector-wide raw occurrence identity | Immutable by system contract | Traceability, not legal entity match | raw_source_record_id |
| Internal observation ID | Projection identity including mapping version | Immutable by system contract | Distinguishes normalizations | observation_id |
| P full Atom ID | Syndication collection/source expediente; full URI distinguishes collections | [D/O] Repeats across updates; multiple IDs can refer to same PSCP object | Strong source alias, not one-to-one legal identity | source record identifiers and procedure identifiers with different roles |
| G Socrata :id | Dataset row identity | [O] Unique in snapshot; [U] replacement/reload persistence | Row lineage only, weak for long-term procedure identity | source record identifiers |
| G id_intern | Dataset application row/member identifier | [O] Unique in snapshot; suffix differs from official lot number; [U] longitudinal stability | Row/member candidate, not parsed lot key | source record identifiers; member identifiers only for batch member role |
| Ordinary PSCP UUID / idExpedient | Official ordinary procedure object in PSCP | [O] Persists across sampled states; [U] legal successor semantics | Strong explicit cross-source reference when ordinary-subject context is verified | procedure_identifiers |
| Aggregate PSCP UUID | Publication batch | [O] Multiple different contracts per UUID | Batch linkage only | batch_identifiers, not procedure_identifiers |
| Numeric PSCP publication ID | PSCP publication object; namespace required | [O] Retrievable across representations; [U] immutability of body under same ID | Same source-publication association, not proof of identical all-field state | publications/source references |
| P VN reference identifier | Source-specific notice/document scope | [U] Depends on actual reference type | Only after determining whether notice or attached document | Publication or document identifiers accordingly |
| Expediente/procedure number | Buyer/administrative source context | [O] 159 P IDs change number; missing planning numbers; cross-buyer and batch collisions | Candidate evidence with buyer/context, never unique key | procedure_numbers |
| ID_OC_PLAT / codi_organ | Origin platform's contracting-organization namespace | [O] Shared scoped IDs; names can vary | Useful buyer linkage; platform must agree | buyer.identifiers |
| Buyer NIF / DIR3 | Scheme/issuer scope; tax entity differs from contracting unit | [O] Native P/rich G may give NIF; placeholders occur in DIR3 | Useful but not interchangeable legal/unit identity | buyer.identifiers with usability |
| Supplier ID | NIF/UTE/DUNS/VIES/source scheme | [O] Multiple tokens; [U] unsupported numeric scheme codes | Candidate party linkage, not automatic consortium decomposition | SupplierAllocation.party.identifiers |
| Displayed lot number / P lot ID | Procedure-local/source-local | [O] Duplicate G number for distinct rows/publications | Candidate association only with procedure and publication context | Lot.number and identifiers; unresolved Scope source identifiers |
| Rich lotId | Rich source object/publication/procedure context | [O] J20 differs from displayed number, includes zero for a genuine lot; [U] stable across edits? | Source alias with context only | Lot.identifiers; never substitute for number |
| Award identifier | Explicit award-object namespace only | No common stable award ID established in researched bulk representations | Later association if supplied | Award.identifiers optional; no synthesized source ID |
| Contract number | Owning source/procedure contract namespace | [D] P permits multiple contracts; [U] longevity/uniqueness | Contract association later | ContractReference / action contract identifiers |
| Action identificador / modification ID | Source subject + action type/context | [O] J19 1 and 2 are local; [U] correction/reordering stability | Action candidate, not global key | execution_actions.identifiers |
| Framework/related UUID | Related source object, not current procedure | [O] J14 reference to a framework | Relationship evidence, not sameness | related_identifiers |
| Source document ID | Platform/document-reference scope | [O] IDs and paths supplied; [U] version/content stability | Later document correspondence, not verified content identity | documents.identifiers |

**Identifier guardrails:** preserve raw spelling; do not strip meaningful punctuation/years/zeros; keep schemes even when values look alike; flag known placeholders. C14 has DIR3 `A9999999`, while C20 has `A99999999`: do not copy a single hard-coded placeholder spelling from the old report and assume all other variants are real organization IDs. A defensible validator needs the actual scheme policy; unvalidated is safer than asserting usable.

No temporal alias registry is introduced. C04's two numbers stay in their respective observations; constructing a history of aliases across observations belongs later.

# 9. Status and lifecycle model

A single `OPEN / CLOSED / AWARDED` enum is insufficient. It would erase planning, partial lot awards, formalization versus execution completion, distinct unsuccessful outcomes, publication corrections, and differences between a tender-phase notice and a currently open submission window.

Use the smallest useful separation:

1. **Status.dimension=procurement_lifecycle:** only an actual source lifecycle assertion.
2. **Status.dimension=publication_phase:** the row/body's reported publication phase.
3. **PublicationReference.type:** the type of that individual publication reference; historical types can coexist.
4. **Outcome.result:** procedure/lot/member result. Awards retain award information independently.
5. **ExecutionAction.type:** reported post-award action, not a replacement for all the above.

## Lifecycle and phase mappings

| Source value | Normalized dimension/value | Strength and caution |
|---|---|---|
| P PRE | lifecycle `prior_information` | [D/O] Prior notice state, not accepting offers. |
| P PUB | lifecycle `submission_open_reported` | [D] Open according to this source state; not a live availability guarantee at query time. |
| P EV | lifecycle `awaiting_award` | [D] Submission period finished/pending award; do not claim actual evaluation has started. |
| P ADJ | lifecycle `award_reported` | [D] At least one lot can suffice; not all lots awarded. |
| P RES | lifecycle `resolved_unspecified` | [D] All lots resolved by allowed mixed outcomes; not completed performance or necessarily positive award. |
| P ANUL | lifecycle `annulled_reported` | [D] Source procedure annulment; distinct from tombstone. |
| G Alerta futura | phase `future_notice` | [D/O] Planning publication, not an open tender. |
| G Consulta preliminar del mercat | phase `market_consultation` | Not a competitive award procedure merely because a future method is mentioned. |
| G Anunci previ | phase `prior_information` | Phase reference, not P lifecycle assertion. |
| G Anunci de licitació | phase `tender_notice` | No assertion of current submission availability. |
| G Expedient en avaluació | phase `evaluation` | Preserve row scope; not a rewrite of parent/other lot rows. |
| G Adjudicació | phase `award_notice` | Notice phase, not enough to invent a detailed award. |
| G Formalització | phase `formalization_notice` | Not performance completion. |
| G Anul·lació | phase `annulment_notice` | Broad family including several outcomes/errors; outcome detail remains separate. |
| G Execució | phase `execution` | Not one action and not necessarily a guarantee of current active execution. |
| G Publicació agregada de contractes | phase `aggregate_contract_report` | Not awarded state for one single procedure. |

Publication types reuse the phase values where appropriate, with `own_resource_entrustment_notice` additionally supported for the documented main-table date in §7.1. P DOC_CN → tender_notice; DOC_CAN_ADJ → award_notice; verified formalization/prior/annulment types map to those families. P RENUNCIA maps to annulment_notice as a **broader** family while retaining exact source type; outcome remains `renounced` when an actual result supplies it. Other P notice codes require a verified list/version mapping; unknowns stay unmapped. Do not construct a numeric/code crosswalk from unsourced memory.

Outcome taxonomy: `awarded`, `formalized`, `deserted`, `renounced`, `discontinued`, `annulled`, `other`. P/G specifically documented meanings map by verified source code or literal label. Preserve `Renúncia` versus `Desistiment` as different outcomes. `other` requires a known source “other” category; unrecognized codes have null normalized value. Broad source lifecycle `RES` does not produce an outcome without a result. A publication-for-error reason should not be translated to legal contract termination.

No inferred Award.status such as current/superseded/rescinded is included: those require historical association and legal interpretation. An explicit source outcome is enough for this layer. A later query model can derive user-facing filters using these facets, observation times and authoritative deadline rules without overwriting them.

Action type vocabulary is deliberately modest: `modification`, `extension`, `performance_deadline_extension`, `assignment`, `succession`, `subcontracting`, `suspension`, `penalty`, `compensation`, `termination`, `other`. These are grounded in E's documented actions; only modification is deeply exercised by J19 here. Exact per-source code mapping for less-studied actions remains Q6; retain source categories until verified. Publication correction is not `modification` in this vocabulary.

# 10. Contract type and procurement procedure taxonomy

## 10.1 Contract type: what is procured

Use a coarse normalized contract nature plus the exact source code. This is not a classification by procurement method or a translation of CPV.

| Normalized value | PLACSP documented category | G documented/observed category | Treatment |
|---|---|---|---|
| `works` | Obras | Obres | Direct semantic category after code/label normalization. |
| `services` | Servicios | Serveis; Contracte de serveis especials (annex IV) | Annex IV mapping is broader; retain qualifier/source category. |
| `supplies` | Suministros | Subministraments | Trim only comparison keys; preserve original source label. |
| `works_concession` | Concesión de obras; legacy Concesión de obras públicas | Concessió d'obres | Legacy legal category remains source code; mapping to same broad family does not erase legal-regime distinction. |
| `services_concession` | Concesión de servicios | Concessió de serveis; Concessió de serveis especials (annex IV) | Preserve Annex IV qualifier. Do not automatically map legacy Gestión de servicios públicos here. |
| `special_administrative` | Administrativo especial | Administratiu especial | Spanish legal category retained explicitly. |
| `private_contract` | Privado | Privat d'Administració Pública | Broad family, original legal detail retained. |
| `public_private_collaboration` | Colaboración entre sector público y privado | Col·laboració Públic-Privat | Legacy/source-legal category, not modern concession inferred by analogy. |
| `patrimonial` | Patrimonial | No clean G counterpart established | Source-specific legal family; no invented G equivalence. |
| `other` | Explicit Otros | Only an explicitly verified corresponding other category | Not fallback for missing/unknown. |

`Gestión de servicios públicos` and `Altra legislació sectorial` remain **unmapped** in v1 rather than forced into services/services_concession/other. They describe legal categories that do not determine the same “what is procured” family without context. Preserve contract subtype separately. `mixed_contract` is a nullable flag; do not override an explicitly reported principal type or invent component proportions.

**Evidence:** P §4.7 documents its categories; G metadata cached categories empirically include the Catalan labels above, but those cached totals are not the research-selected population. The exact numeric P crosswalk must use the actual list URI/version. Examples in the specification and raw files use different list versions/names; bare code `3` is not a sufficient dictionary key. Q3 is an implementation gate, not a reason to guess.

## 10.2 Procurement method: how it is awarded

Keep this independent of contract type. The first taxonomy preserves observed meaningful variants without attempting a universal European legal taxonomy.

| Normalized value | Source concepts mapping here | Qualification |
|---|---|---|
| `open` | Abierto / Obert | Not a current-open status. |
| `restricted` | Restringido / Restringit | Participation request deadline can differ from offers. |
| `negotiated_with_publication` | Negociado con publicidad / Negociat amb publicitat | Do not automatically merge with the distinct competitive-negotiation category. |
| `negotiated_without_publication` | Negociado sin publicidad / Negociat sense publicitat | Publication of result is still possible; “without publication” is method meaning. |
| `competitive_negotiation` | Licitación con negociación / Licitació amb negociació | Separate verified source category. |
| `competitive_dialogue` | Diálogo competitivo / Diàleg competitiu | Separate from negotiated. |
| `open_simplified` | Abierto simplificado / Obert simplificat | Do not collapse into ordinary open. |
| `open_simplified_abbreviated` | G Obert simplificat abreujat | P generic simplified code does not prove this subtype. |
| `design_contest` | Concurso de proyectos / Concurs de projectes | Not contract nature “services” inferred automatically. |
| `innovation_partnership` | Asociación para la innovación / Associació per a la innovació | Distinct from derived contract below. |
| `innovation_partnership_derived` | P Derivado de asociación para la innovación | Documented P category; no forced G counterpart. |
| `framework_call_off` | P Derivado de acuerdo marco | G rationalization may report Contracte basat en acord marc in a different dimension; preserve there rather than fill absent method automatically. |
| `dynamic_system_specific` | P Basado en un sistema dinámico de adquisición; G Específic de Sistema Dinàmic d'adquisició | Specific contract under system, not establishment of system. |
| `minor_contract` | G Contracte menor | Spanish regime, not necessarily one universal direct-award method. P researched feeds explicitly exclude minors; no implied coverage. |
| `direct_award_non_minor` | G Adjudicacions directes no menors | Do not collapse with minor contract or negotiated without publication. |
| `internal_rules` | P Normas internas; G Altres procediments segons instruccions internes | Broad procedural basis, not one detailed award mechanism. |
| `other` | Explicit source Otros/verified other | Unknown remains unmapped. |

G `Tramitacio amb mesures de gestió eficient` stays unmapped: it sounds like a processing regime and cannot safely be equated with abbreviated open merely from its wording. `tipus_tramitacio`/UrgencyCode and rationalization/ContractingSystemCode remain distinct attributes. C20 is an **open** procedure with **Acord Marc** rationalization; framework establishment and framework call-off are not identical.

Taxonomies are intentionally versioned with the mapping. Missing values remain null; unknown values retain a Code. More detailed legal categories can later be added without rewriting original observations or pretending v1 already established equivalence.

# 11. Lots, awards and suppliers

## 11.1 Embedded lots, not resolved entities

A Lot is a source occurrence within an observation. Store number, source IDs and descriptive text; all variable facts use explicit Scope. This avoids duplicating many field definitions on both procedure and lot and supports results referring to a lot absent from the current source payload.

**C05 example [O]:** first G lot row for `ME. MEC-25L02` contains:

- Procedure estimate `83,579,468.07`; procedure net budget `41,129,079.80`.
- Lot 1 estimate `4,500,965.74`; lot net budget `2,292,542.12`; gross `2,773,975.96`.
- Lot description “Edificis judicials Barcelona,” CPV `50700000-2`, and supplier-specific award `2,011,802.23` net.

**[R] Projection:** one observation, one embedded lot, procedure-scoped and lot-scoped financial items, lot-scoped CPV and award. Currency remains null for the bare G row. Do not multiply the procedure budget by 13; do not fetch and combine the other rows in normalization. Record inventory is partial, even if its procedure identifiers match other observations.

**C15 [O]:** two separate rows claim lot 3 and different publications. They stay separate observations. If a single body presents competing occurrences with the same number, retain distinct local keys. A reference only saying “3” stays unresolved when there is more than one candidate; no arbitrary first-match rule.

**J01 [O]:** no-lots flags override the temptation to create a lot from `dadesPublicacioLot`. Values there can be procedure-scoped when that source context establishes an unsplit procedure. For a bare table row without a usable lot number, missing/zero lot does **not** prove no lots: use record_subject or unknown scope and issue, rather than manufacturing a lot or silently treating documented lot columns as procedure totals.

**[R] Other lot rules:** no synthetic “lot 0”; no budget allocation by division; no CPV union promoted to procedure; no inherited deadline duplicated to each lot; no lifecycle roll-up. Source result references can use `source_lot_identifiers` without creating an otherwise unsupported lot object. Positive internal `lotId` is not proof of a matching displayed number, and internal zero can be a valid identifier for an explicitly real lot (J20).

## 11.2 Award groups versus decisions

P TR is the initial grouping only when it contains positive award information; nonpositive results become Outcomes. P §4.35.8 documents separate TR occurrences for lot results; preserve those boundaries. If a supported representation supplies distinct awarded-project/lot subgroups within a result, retain separate scoped Award groups at those paths rather than pooling their amounts across a union of lots. A genuinely shared multi-lot total can retain multi-lot scope, but cannot be distributed among those lots. Shared supplier/contract context is attached only where its applicability is explicit or unambiguous; otherwise retain it as unresolved information with an issue.

G main-row award columns form a `source_row_group`, preserving the fact that the flat representation does not fully distinguish joint winners from multiple awards/contracts. Rich arrays preserve explicit grouping but do not automatically establish legal joint-award semantics.

An award can have:

- Zero known suppliers (positive decision with incomplete identity).
- One supplier.
- Several supplier allocations, potentially representing separate reported contractor entries.
- A consortium party as one supplier; constituent companies are not automatically separate winners.
- A date but no amount, amounts but no date, or multiple contract references.

An award's scoped result can be formalized while another lot is deserted. Do not impose one winner or one award per procedure, one unique lot number, or one formalization date at observation root.

**C09 [O/R]:** G emits a Renúncia Outcome and an Award group retaining the reported historical winner/amount/date. Do not attach the old award date to the new negative outcome. Do not assert that the Award is still active, legally revoked, or identical to any P award object. P emits its reported negative result without importing G's retained winner.

## 11.3 Positional supplier parsing contract

This is a semantic contract for a future mapper, not normalization code:

1. Preserve the original parallel strings and delimiters in raw; retain every positional token, including empty tokens.
2. For compatible vectors with clearly documented positional alignment, create positional SupplierAllocations. Missing token is not zero; unavailable party identity is not an invented name.
3. If lengths or association semantics are inconsistent, create unresolved allocations for the independently supported party/amount positions, each with its originating source path; do not associate amount with party merely by nearest position. Multiple unresolved entries may share the same numeric ordinal across different source vectors.
4. Do not broadcast a scalar amount over multiple winners or sum values into a procedure/award total unless the source explicitly defines such a total.
5. Group totals from P LegalMonetaryTotal remain Award.amounts; they are not copied to every WinningParty. G documented per-winner values remain allocation amounts. Rich structured party money follows its actual owner.
6. Numeric supplier-type code `542` is supported as NIF by J20's labelled rich objects; that observation does not decode every other numeric scheme. Unknown type remains source-qualified/unvalidated.

**C20 [O/R]:** lot 1 has `B41956970||A08338683`, two supplier names and amount `||`. Preserve two known supplier allocations and two explicit-empty amount tokens, not no suppliers, two zero awards, a parsing exception that discards the row, or a guessed combined award. Raw and item paths preserve the exact vector spelling. J20 is a separate observation, not an automatic repair of the table row.

## 11.4 Execution actions are not replacement award values

J19 yields two embedded modification actions with local identifiers 1 and 2, action dates and `modification_delta` amounts `341,124.07` and `317,101.25`, tied to the same publication. An E row alone supplies `action_amount` because its documented column is generic action amount. P's final modified-contract total, when supplied, has another purpose. No action amount overwrites tender budget or original award amount; no aggregation calculates current contract value in this layer.

# 12. Documents and source references

Keep two deliberately different collections:

- **SourceReference:** a page/profile/publication-export URL and its target identity/role. Enables navigation even when attachments are unavailable.
- **SourceDocumentReference:** an actual referenced document with source ID, role, title/language, exact URL or unresolved delivery token, optional reported hash/size and context.

A procurement notice PDF belongs in documents with role notice if actually referenced; its source page belongs in source_references. Administrative specifications and technical specifications have distinct roles. Generic tender supporting documents remain supporting_document/other rather than being classified by title speculation. Award documents and corrections use their source context; replacements need explicit source relationships, not “newer filename wins.”

**[O] J01** has language-indexed specification objects with ID, titol, opaque path, hash, idioma and mida. It does not turn every path token into an independently verified download URL. Preserve the token and link users through the explicit original publication page/export when a direct URL cannot be established. A future source connector can resolve a documented delivery route; this design does not invent one.

**[D/O] P** has references both directly under status and nested under notices/results. The exploratory direct-child document metric is not the schema coverage definition. A mapper must consider supported nested contexts without treating every VN document-reference ID as an attachment ID or every attachment ID as a notice ID.

**[O] Legacy PSCP** JSON-named endpoints returned XML for selected historical notices. Content format belongs to raw acquisition/extraction metadata; `publication_export` does not mean JSON. Legacy CDATA/calendar structures require source-specific interpretation before producing the same normalized concepts.

No canonical document, “latest specification,” binary-content hash, download-success claim, OCR text, document diff or immutable DocumentVersion is proposed. Reported hashes are separate from any future locally verified content digest. Source disappearance or changed URL tokens alone do not retract or replace a document.

# 13. Provenance requirements

The minimum relation is:

```text
NormalizedObservation
  -- exactly one raw_source_record_id --> immutable RawSourceRecord
  -- projection_locator --> selected subject within that raw record
  -- mapping_version + schema_version --> reproducible interpretation
```

Repeated source-derived items retain `source_path` so that source grouping is recoverable. This is **input localization**, not field-level canonical provenance or a FieldAssertion database. It does not require a provenance link on every scalar, a reconciliation confidence score, or an entity-resolution decision.

Preserve now so later granular provenance remains possible:

1. Immutable original bytes, checksums, acquisition references and exact record locators, including inherited XML namespaces.
2. All original fields/attributes, source code-list URIs/versions, language keys, numeric lexical values, null/empty tokens, ordered arrays and their grouping.
3. Both source-row IDs and publication/procedure/batch identifiers with their original URLs. Do not retain only lossy extracted convenience IDs.
4. Which input subject was selected from a rich batch, and the shared header context used.
5. Distinct source clock roles and original precision/timezone encoding.
6. Mapping rules/version, local item locators, and reasons values were omitted, left unmapped or assigned uncertain scope.
7. Origin-platform lineage, so a PSCP fact transported by P is not later counted as independent corroboration.

No field is overwritten by another source during normalization. To change a mapping, make a separately identifiable projection of the same immutable raw occurrence rather than altering historical source evidence. Later reconciliation can derive field assertions by revisiting this input with a versioned mapping and exact locators.

The raw reference must resolve to **the exact occurrence**, not just an external source URL that may return different content tomorrow. The existing sample `evidence.json` format demonstrates the necessary archive/member/byte-range and page/row lineage, but is research evidence, not a required production storage implementation.

# 14. Fields intentionally excluded or deferred

| Excluded/deferred concept | Reason / what is preserved instead |
|---|---|
| Canonical procurement, buyer, supplier, lot, award, contract or document ID | Requires entity resolution. Keep source IDs and observation-local keys. |
| Canonical revision number, current canonical state, semantic change fingerprint | Requires reconciliation/materiality policy. Mapping/schema versions are not business revisions. |
| Match confidence, source priority, resolved conflicting values | Decisions across observations belong later. Mapping exact/broader/unmapped is a different concept. |
| Unified “current open/closed/awarded” status | Would erase dimensions and depend on time, scope and authoritative deadlines. Keep reported facets. |
| Generic `date`, `updated_at`, `amount`, `tender_id` | Meanings differ across sources; qualified concepts replace them. |
| One first publication or last business change timestamp | Not reliably supplied by these mixed projections. Preserve occurrence dates. |
| Source availability merged into procurement cancellation | Raw tombstones/absence/access failures are not legal outcomes. Later availability projection can use them. |
| Legal Contract entity and current contract value | Existing contract references/actions do not establish complete identity or modification history. |
| Full party-role history / administrative reassignment | C11 demonstrates differences, not a verified reassignment cause. Keep each record's buyer. |
| Full consortium membership and legal-entity registry | Party kind/identifier preserves current distinction; detailed membership stays raw. |
| Inferred totals, converted currencies, computed VAT, evenly allocated lot budgets | Would create new business assertions rather than normalize supplied ones. |
| Complete notice-history reconstruction / successor graph inferred by chronology | Neither source guarantees full event history. Explicit source relations only. |
| Document canonicality, binary hashes, text extraction and version diffs | Only references/metadata were researched thoroughly enough; binaries not exhaustively acquired. |
| Detailed eligibility/award criteria, bid counts, guarantees, funding, legal regime, options, review bodies, electronic-submission tooling | Present in sources but not necessary for the first common discovery representation. Retain raw and document links. Add deliberate typed concepts later, not a generic metadata union. |
| Opening-event schedule model | C01 proves opening correction matters, but its detailed event taxonomy is not needed for v1. Preserve correction text and raw opening structures. |
| Parsed legal effect from free text | Requires semantic interpretation beyond this evidence. Keep exact text. |
| Derived coordinates, buyer/execution municipality reconciliation | No geocoding or entity resolution; preserve explicit locations. |
| Subscription state, user annotations, alerts, notification payloads | Product/user layer, unrelated to what a source asserts. |
| RPC contract-register model, other feed populations, hypothetical European extensions | Outside investigated current acquisition scope. |

## Extensibility assessment

| Part | Reusability / coupling | Deliberate extension point |
|---|---|---|
| Observation-to-raw boundary, partial coverage, scoped facts, decimal money, temporal precision | Broadly reusable across sources | New mapping versions and record kinds without canonical identity assumptions. |
| Procedure/buyer/supplier/source identifiers | Reusable structure; actual schemes source/country-specific | Namespaced scheme strings, not a fixed global identifier format. |
| CPV and NUTS | European classifications actually present here | Explicit code-list identity/version; no automatic assumption all future sources use them. |
| NIF, DIR3, expediente numbers; minor/simplified/legacy contract categories | Strong Spanish/Catalan coupling | Source codes retained; normalized taxonomy can be extended deliberately. |
| Source markers, es_agregada interpretation, PSCP numeric category IDs, opaque document paths | Explicitly source-specific | Source metadata and raw retention; no claim of generic equivalents. |
| Lots, outcomes, award groups, publication occurrences, action facts | Meaningful reusable procurement concepts grounded in these two sources | New supported type/category values, not speculative future entities. |
| Currency and timezone | Deliberately not Spain-wide defaults | Explicit qualified values/assumptions; nullable when unsupported. |

This is reasonable extensibility, not a universal European schema. A future source may justify new concepts; it should not force reinterpretation of old observation identities or erase original code meanings.

# 15. Open questions

The representation can be implemented without resolving every uncertainty by using the conservative rules specified above. The following questions are nevertheless explicit implementation gates for stronger mappings. No live probing or new ingestion is part of this report.

| Question | Evidence / uncertainty | Conservative v1 behavior | What would justify a stronger mapping? |
|---|---|---|---|
| Q1: Are G row/member/lot/action IDs stable across correction, reload and reordering? | [O] Distinct row/lot identifiers, duplicate lot 3, batch collisions; [U] longitudinal guarantees | Occurrence keys only; qualified source IDs, unresolved references; no uniqueness constraint on lot number | Publisher statement plus repeated acquisitions of selected IDs. |
| Q2: Exact timezone and semantic precision policy for each G date field? | [O] Madrid-compatible sampled conversions and seconds truncation; calendar date serialization; non-midnight award example | Floating by default, precision_basis explicit; no forced UTC or automatic midnight stripping | Field-specific documentation and broader paired table/body validation, including DST ambiguity. |
| Q3: Complete verified code-list mappings by version? | [D] P points to code lists; [O] versions differ; rich G numeric IDs have labels only in examples | Exact raw Code; null normalized for unsupported code/version; common documented labels map conservatively | Retained authoritative dictionaries/code lists and version-specific crosswalk review. |
| Q4: Is there an official G currency guarantee? | [O] Main table lacks independent currency; sampled rich amounts may too | Currency null unless explicit within same input; no external enrichment during normalization | Documented dataset convention adopted as a versioned rule, or explicit source field. |
| Q5: Can G phase dates always bind to corresponding phase export IDs? Can bodies change under stable IDs? | [O] Main URL can lag correction; [U] per-phase pairing/stable-body guarantees | Pair named phase date/link only when their association is unambiguous; otherwise separate references and issue; retain raw occurrence identity | Publisher clarification and longitudinal body comparisons. |
| Q6: Exact action type, amount and date semantics outside reviewed modification case? | [D] E generic action amount; [O] J19 incrementPreu is delta; other action populations less inspected | Action amount remains generic typed action_amount; unsupported subtype unmapped, no contract-state update | Per-action samples/dictionaries, including whether amount is delta, penalty or revised total. |
| Q7: Does current table buyer represent administrative reassignment? | [O] C11 old issuer/current organization differ; [I] reassignment; [U] cause and validity | Each observation's source-reported buyer only, no historical/current role assertion | Official historical organization relationship evidence. |
| Q8: Document paths, hash algorithms, size units and replacement semantics? | [O] Rich metadata and usable P links; [U] full delivery/immutability guarantees | Preserve opaque path, reported hash with unknown algorithm, explicit verified units only; source-page fallback | Source API/documentation plus bounded binary retrieval verification in a later task. |
| Q9: Supplier vector alignment and identifier placeholder policy beyond inspected examples? | [D] Multiple award amounts concatenated; [O] vectors differ/empty tokens, numeric schemes and DIR3 variants | Preserve positions, unresolved allocations on mismatch, scheme unvalidated, no global party match | Publisher vector contract, scheme dictionaries and further representative cases. |
| Q10: Bare G lotless row scope for documented lot fields? | [D] Lot-level column descriptions; [O] absent/zero lot markers and rich no-lots container | record_subject/unknown, no fake lot or procedure-total inference | Publisher rule and paired examples proving unsplit subject semantics. |
| Q11: Documentation inconsistencies in monetary examples/path labels? | [D] P §4.11 prose labels pair “con impuestos” with TaxExclusiveAmount and “sin impuestos” with TotalAmount, while its numeric example and §4.4 show the expected inverse. §4.35.3 sample repeats TaxExclusiveAmount for two values. | Use supported element semantics and actual structures, preserve tax basis, flag anomalous repeated/conflicting values; never copy apparent documentation typos into a mapper | Authoritative schema/code definitions and representative native/lot/award source validation. |
| Q12: Supported legacy publication mappings and completeness? | [O] Legacy XML returned through JSON endpoints; Java-style names/calendar structures | Detect actual format in raw; only normalize validated paths; keep unsupported details raw with issues | Focused legacy field review before implementing that adapter. |
| Q13: Meaning of G organizational INE10 codes and source “complete” lists? | [D] Brief metadata description does not prove execution municipality or historical completeness | Do not map INE10 into execution geography; coverage unknown/partial unless explicit | Publisher-specific field and coverage definitions. |

**Critical implementation boundary:** none of these questions justifies guessed canonical IDs, coalescing batch members, treating unknown currency as EUR, claiming complete collections, or translating every closing publication into a cancelled contract. An unresolved mapping can be represented without losing the original input.

## Design review against concrete cases

| Evidence | Required outcome of any future implementation |
|---|---|
| C01/J01 correction and no-lots body | No invented lot; original/corrected publication distinguished; unchanged submission deadline not treated as reopening. |
| C02/C03 evolving budgets/deadlines | Separate observations, not mutations of one normalized tender or inferred legal modification. |
| C04 renamed expediente | Both observations retain their source number; no destructive alias rewrite. |
| C05 thirteen lots | Correct scoped amounts/CPVs/awards; no multiplied procedure total or suffix-derived lot numbers. |
| C06/C08/C09 cancellation/desert/renunciation | Distinct phase, lifecycle and outcomes; old award preserved where supplied. |
| C10/C11 multiple Atom IDs/buyer disagreement | Multiple qualified source IDs and separately reported buyers; no automatic resolution. |
| C12 selected-cohort complementarity | Absence not deletion; no claim of complete source history. |
| C13 timestamps | Distinct notice targets and precision, no global latest-clock ordering. |
| C14/J14 batch | Six separate member projections from body; batch UUID never procedure ID; framework reference is related identity. |
| C15/C16 duplicate lots/mixed phases | Preserve distinct records and scopes; no unique lot-number key or maximum-phase roll-up. |
| C17/C18 identifier/fuzzy false friends | No joining by number or title similarity in normalization. |
| C19/J19 execution | Two action objects, one publication; action amounts/dates separate from publication/row timestamps. |
| C20/J20 multiple winners/empty amounts | Preserve suppliers and empty positions; no zero money, manufactured award grouping or modern-JSON assumption for legacy exports. |

These are design acceptance examples, not tests or implemented normalization.

# 16. Final recommended schema

The following is language-agnostic. It expands the complete recommended shape; it is not Python, SQL, a database migration or an implementation. All source categories/normalizations follow §§6, 9 and 10.

Notation: `!` required non-null singleton; `?` optional/nullable; `[]` required possibly empty collection; `[+]` nonempty collection. `Item` means the two required fields `key: Key!` and `source_path: String!`. `Text` is LocalizedText. Keys refer only within this observation.

```text
NormalizedObservation
├── observation_id: ID!
├── raw_source_record_id: ID!
├── projection_locator: String!
├── schema_version: String!
├── mapping_version: String!
├── source: SourceMetadata!
├── source_markers: SourceMarker[]
├── subject_kind: procedure | planning | batch_member | unresolved !
├── focus: Scope!
├── procedure_identifiers: Identifier[]
├── procedure_numbers: Identifier[]
├── batch_identifiers: Identifier[]
├── member_identifiers: Identifier[]
├── related_identifiers: RelatedIdentifier[]
├── titles: Text[]
├── descriptions: Text[]
├── buyer: Party?
├── contract_type: MappedCode?
├── mixed_contract: Boolean?
├── procurement_method: MappedCode?
├── procurement_attributes: ProcurementAttribute[]
├── statuses: Status[]
├── classifications: Scoped<Classification>[]
├── financials: Scoped<Money>[]
├── deadlines: Scoped<Deadline>[]
├── execution_locations: Scoped<Location>[]
├── performance_periods: Scoped<PerformancePeriod>[]
├── lots: Lot[]
├── publications: PublicationReference[]
├── outcomes: Outcome[]
├── awards: Award[]
├── execution_actions: ExecutionAction[]
├── documents: SourceDocumentReference[]
├── source_references: SourceReference[]
├── coverage: Coverage[]
└── issues: Issue[]

SourceMetadata
  system: placsp | gencat !
  dataset: String!
  record_kind: procedure_snapshot | procedure_projection | lot_projection |
               batch_member_projection | publication_body |
               batch_publication_body | execution_action_projection !
  record_identifiers: Identifier[]
  origin_platform: Code?

SourceMarker
  kind: placsp_entry_publication_updated | socrata_row_created | socrata_row_updated !
  at: TemporalValue!

Identifier
  scheme: String!
  namespace: String!
  value: String!
  role: record | procedure | procedure_number | publication | batch | member |
        lot | buyer | supplier | award | contract | action | document | related !
  usability: unvalidated | usable | placeholder | invalid !

RelatedIdentifier
  identifier: Identifier!
  relation: framework_reference | related_unspecified !

Code
  system: String!
  version: String?
  value: String!
  labels: Text[]

MappedCode
  source: Code!
  normalized: String?
  mapping: exact | broader | unmapped !

LocalizedText
  text: String!
  language: LanguageTag?
  source_role: String?

Scope
  kind: procedure | lots | record_subject | publication_batch | unknown !
  lot_keys: Key[]
  source_lot_identifiers: Identifier[]

Scoped<T>
  source_path: String!
  scope: Scope!
  value: T!

Party
  kind: organization | person | consortium | unknown !
  identifiers: Identifier[]
  names: Text[]
  addresses: Location[]

ProcurementAttribute
  kind: contract_subtype | contract_qualifier | urgency | contracting_system !
  value: Code!

Status
  source_path: String!
  scope: Scope!
  dimension: procurement_lifecycle | publication_phase !
  value: MappedCode!

Classification
  system: CPV!
  code: String?
  check_digit: String?
  raw_code: String!
  source_system: String?
  version: String?
  role: main | additional | unspecified !

Money
  purpose: estimated_value | tender_budget | award_amount | action_amount |
           modification_delta | contract_total_after_modification !
  value: Decimal?
  raw_value: String!
  value_state: valid | explicit_empty | invalid !
  currency: CurrencyCode?
  tax_basis: excluded | included | unspecified !
  vat_rate: Decimal?
  multiple_vat_rates: Boolean?

TemporalValue
  raw: String!
  local_date: CalendarDate?
  local_time: ClockTime?
  utc_instant: UTCInstant?
  offset: UTCOffset?
  zone: IANAZone?
  zone_basis: explicit_offset | documented_zone | assumed_zone | unknown | not_applicable !
  precision: day | minute | second | fractional_second | unknown !
  precision_basis: documented | observed_projection | lexical_only | unknown !

Deadline
  kind: offers | participation_requests | submission_unspecified | document_access !
  at: TemporalValue?
  notes: Text[]

Location
  names: Text[]
  nuts_code: String?
  nuts_version: String?
  country_code: String?
  locality: String?
  postal_code: String?
  address: String?

PerformancePeriod
  kind: planned | reported_execution | unspecified !
  raw_text: Text[]
  start_at: TemporalValue?
  end_at: TemporalValue?
  duration: DurationPart[]

DurationPart
  value: Decimal!
  unit: years | months | days | hours | unspecified !

Lot [Item]
  identifiers: Identifier[]
  number: String?
  titles: Text[]
  descriptions: Text[]

PublicationReference [Item]
  scope: Scope!
  identifiers: Identifier[]
  type: MappedCode?
  medium: String?
  publication_at: TemporalValue?
  planned_publication_at: TemporalValue?
  sent_at: TemporalValue?
  is_correction: Boolean?
  correction_type: Text[]
  correction_reason: Text[]
  relations: SourceRelation[]

SourceRelation
  kind: corrects | replaces | withdraws | supplements | related_unspecified !
  target_identifiers: Identifier[+]

Outcome [Item]
  scope: Scope!
  result: MappedCode!
  decision_at: TemporalValue?
  reasons: Text[]
  publication_keys: Key[]

Award [Item]
  scope: Scope!
  identifiers: Identifier[]
  grouping: source_result | source_row_group | source_award_object !
  decision_at: TemporalValue?
  amounts: Money[]
  suppliers: SupplierAllocation[]
  contract_references: ContractReference[]
  outcome_keys: Key[]
  publication_keys: Key[]

SupplierAllocation [Item]
  source_position: NonnegativeInteger?
  party: Party?
  amounts: Money[]
  alignment: structured | positional | unresolved !

ContractReference
  source_path: String!
  identifiers: Identifier[]
  formalized_at: TemporalValue?
  effective_at: TemporalValue?

ExecutionAction [Item]
  scope: Scope!
  identifiers: Identifier[]
  contract_identifiers: Identifier[]
  type: MappedCode!
  titles: Text[]
  action_at: TemporalValue?
  end_at: TemporalValue?
  amounts: Money[]
  parties: Party[]
  details: Text[]
  publication_keys: Key[]

SourceDocumentReference [Item]
  scope: Scope!
  identifiers: Identifier[]
  role: MappedCode?
  titles: Text[]
  language: LanguageTag?
  urls: URIString[]
  source_path_token: String?
  reported_hash: ReportedHash?
  reported_size_bytes: NonnegativeInteger?
  declared_media_type: String?
  publication_keys: Key[]
  relations: SourceRelation[]

ReportedHash
  value: String!
  algorithm: String?

SourceReference [Item]
  url: URIString!
  target_kind: procedure_page | publication_page | buyer_profile |
               publication_export | other | unknown !
  identifiers: Identifier[]
  publication_keys: Key[]

Coverage
  path: String!
  scope: Scope!
  state: unknown | partial | source_declares_complete | source_declares_empty !
  basis: String!

Issue
  code: String!
  path: String!
  detail: String!
```

**Final recommendation:** implement this eventually as a conservative, immutable projection of a single raw input, not a small canonical tender disguised as normalization. Preserve uncertainty and source scope now; leave stable identity, consolidated state and historical interpretation to the explicitly later layers.
