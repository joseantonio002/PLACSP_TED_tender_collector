# Normalization test strategy

## 1. Purpose and scope

This document specifies tests to write **before** implementing source-specific normalization mappers. It is a research/design deliverable, not an implementation, a new schema, or a claim that the proposed model has already been accepted in production.

The boundary is:

```text
one immutable RawSourceRecord + explicit selection + versioned mapping rules
    -> source-attributed NormalizedObservation(s), or a controlled failure
```

Each observation must describe one defensibly selected subject from exactly one raw occurrence. It may be partial, internally heterogeneous, or unresolved. It need not identify a globally unique procedure. A rich batch can yield several observations, but no observation can combine two raw records.

Excluded: daily/incremental change detection, scheduling, persistence, entity resolution, PLACSP-to-Generalitat matching, reconciliation, canonical ProcurementProcess construction, reconstructed history, canonical revisions, notifications, and inference of deletion from source absence. Tests involving two retained representations invoke normalization **independently** and assert isolation, not agreement, matching, event ordering, or reconciliation.

### 1.1 Authority and repository state

Inspected on 23 September 2026 against the retained 22 September research snapshot:

| Reference | Role in this strategy |
|---|---|
| [PROJECT_CONTEXT.md](../../PROJECT_CONTEXT.md), [AGENTS.md](../../AGENTS.md) | Current source scope and repository/testing rules. |
| [NORMALIZED_SCHEMA_DESIGN.md](NORMALIZED_SCHEMA_DESIGN.md), especially §§5–13, 15–16 | Primary normalization contract: fields, cardinality, scopes, Issues and conservative handling. References below abbreviated **N §n**. |
| [REPORT.md](REPORT.md), §§1–3, 6–7 | Source analysis, C01–C20, validation and limitations. Its earlier §4 canonical proposal is **not** the normalization test oracle; N §5.3 explicitly supersedes that boundary. |
| [Main metadata](../../data/raw/gencat/ybgg-dgi6/metadata-before.json), [execution metadata](../../data/raw/gencat/8idu-wkjv/metadata-before.json), [syndication text](../../data/analysis/documentation/syndication-current.txt) | Documented field meanings, including lot/procedure money, action money and dates. |
| [Case selection](../../analysis/case_selection.json), [case findings](../../analysis/case_findings.json), [semantic audit](../../analysis/semantic_audit.json), [metrics](../../analysis/metrics.json) | Locate counterexamples; analysis summaries are not lossless mapper inputs. |
| [Samples](../../data/samples/), their `evidence.json`, and referenced raw acquisitions | Real fixture origins and exact occurrence lineage. |
| [Acquisition](../scripts/download.py), [sample extraction](../scripts/make_samples.py), [PLACSP inspection](../scripts/inspect_placsp.py), [Generalitat inspection](../scripts/inspect_gencat.py) | Existing ingestion/research behavior and provenance mechanics, not production mapper contracts. |
| [Artifact verification](../scripts/verify_artifacts.py), [parser verification](../scripts/verify_parsers.py), [report verification](../scripts/verify_report.py), [semantic audit script](../scripts/audit_semantics.py) | Existing validation and its limits. |
| [pytest/package configuration](../../pyproject.toml), [research tests](../../tests/research/test_research.py), [smoke test](../../tests/test_smoke.py) | Current deterministic pytest suite; retained unittest-style research regressions; no normalization fixture helpers yet. |

**Important implementation gap:** `src/tenderwatch/` currently contains only an empty `__init__.py`. There are no implemented `RawSourceRecord` or `NormalizedObservation` classes, normalization functions, validators, or public normalization exceptions. N §§5.1 and 6.10 describe the raw relationship contract; N §16 describes a language-agnostic proposed observation. Do not invent an existing constructor, signature, error name, or serialization format when writing the next task. The exception names and operational choices below are recommendations needing explicit adoption.

The research code cannot be used uncritically as the expected-output generator:

- `parse_entry` uses namespace wildcards, substitutes an empty element for a missing ContractFolderStatus, takes first matches, pools some descendant fields, and calls negative TenderResults “awards.” Production tests must enforce N's stronger semantics instead.
- Research `amount`/comparison helpers intentionally collapse some invalid values and use lossy matching keys. They do not implement Money states, supplier alignment, or exact identifier preservation.
- `make_samples.py` preserves exact XML slices but reserializes table rows and uses broad download-recovery exception handling. That recovery pattern is not appropriate inside a mapper.
- Research artifact checks validate hashes/locators. Parser verification checks consistency with indexed URL IDs, not complete normalization semantics. The semantic audit performs cross-record analysis that must not migrate into normalizers.
- Raw data and samples are local, Git-ignored evidence. Default tests must not require the multi-gigabyte snapshot. `tests/fixtures/` currently has only `.gitkeep`.

### 1.2 Evidence labels

**Contract** means specified by N, not a publisher guarantee. **Observed** means directly retained in the inspected corpus. **Proposed** means a test/API policy chosen here, not settled by N. **Gate** means a decision or focused mapping review must precede an exact expected assertion. A gate must not be resolved by guessing or by quietly dropping the test.

## 2. Normalization test philosophy

### 2.1 Four outcomes, not “parse or crash”

| Category | Required response | Examples |
|---|---|---|
| Happy path | Produce the expected typed projection; ordinary missing optional values remain absent. | P entry, main lot row, standalone execution row. |
| Real edge | Preserve unusual but supported source semantics, often with no Issue for the edge itself. | Multiple lots, repeated source occurrences, retained award plus renunciation, batch members. |
| Recoverable/degraded | Produce an observation with Issues and/or omit only an unsupported assertion; preserve independent facts and raw recoverability. | Invalid decimal, unknown code, uncertain scope, malformed optional URL. |
| Fatal input/selection failure | No observation for the failed selection; a small public, contextual normalization error. | Unresolvable raw occurrence, undecodable entire body, no defensible batch-member selection. |
| Internal invariant/programming/system failure | Fail loudly; never disguise as bad source data, an Issue, or an empty successful result. | Mapper-created dangling local key, missing mapping version, unexpected KeyError, unavailable storage due to permissions. |

A happy-path fixture can legitimately contain diagnostics. “Happy” describes a supported, ordinary projection, not an assertion that real data is perfect. For example, a normal bare Generalitat row can contain documented lot columns without a lot number. Its procedure-scoped facts still normalize, while the ambiguous facts need `record_subject` scope and `uncertain_scope`.

Apply this decision sequence:

1. Is the raw occurrence valid and resolvable, with the necessary format/namespace context?
2. Is this a recognized input family and can the explicit selection identify a defensible subject?
3. For each assertion, is its lexical value, code meaning, owner and scope supported?
4. If not, can the schema retain a weaker assertion safely? Prefer that over dropping it.
5. If no meaningful nested object remains, omit that object and diagnose the affected value, not the entire observation.
6. Only fail the whole selection when no contract-compliant projection is possible. Optional business identity, amount, title, deadline or buyer is not required normalization metadata.
7. Validate the mapper's output invariants. Failure here is generally a mapper defect, not an excuse to reject ordinary imperfect input.

### 2.2 Assertions should test meaning

For every example test assert:

- cardinality, one raw reference, exact selection and source/mapping/schema metadata;
- typed values, original code/identifier spelling, monetary purpose/tax/currency, temporal role/precision/basis;
- scope and grouping, including nested collection counts and supplier positions;
- source paths and resolvable local references;
- deliberate null/absent values and absence of forbidden inferred facts;
- required diagnostics by **code and affected path**, not exact prose or incidental ordering;
- raw input unchanged and no network/cross-record access.

Use exact Decimal expectations from strings. Do not compare binary floats with tolerances. Do not assert full-object equality between sources. Do not derive expected values with the same parser/crosswalk helper being tested. A test that checks only “returned an observation” does not test this contract.

Collections are not globally complete unless explicitly justified. A source-declared empty lot inventory is different from `lots=[]` because this projection contains no mapped lots. Known no-lots flags do not make empty language maps, unsupported action arrays, or absent winners complete inventories.

### 2.3 Diagnostic baseline policy

Matrix rows name the diagnostic caused by the behavior under test. A real fixture's other diagnostics remain relevant. Before implementing tests, record its baseline issue set under the adopted mapping version. For one-property mutations compare against that baseline, allowing only diagnostics attributable to the changed property and its dependent assertions. Do not demand globally empty `issues` simply because a row is categorized happy/edge.

Proposed defaults used here:

- Missing optional field: no Issue merely for absence.
- Empty unused source containers or intentionally deferred fields: no Issue spam.
- Explicit empty **mapped scalar/token**: `explicit_empty`; no fabricated identifier/party.
- Floating time with unresolved timezone: `ambiguous_time` for a timestamp-bearing assertion; date-only facts use `not_applicable`, not a timezone warning.
- A verified observed precision rule may use `observed_projection`; it is not automatically an error. If precision cannot be defended, emit `uncertain_precision`.
- Unknown optional source attributes outside the v1 mapping are retained raw, not each diagnosed as unsupported. A changed structure at a supported path is different and warrants `unsupported_structure`.

These diagnostic granularity defaults are proposed policy. Freeze them before golden comparisons (§13).

## 3. Input kinds and mapper boundaries

These are conceptual adapter cases, not names of existing Python classes. `record_kind` below is the **normalized** SourceMetadata enum; raw routing tags have not yet been defined.

| Adapter case | Raw occurrence / explicit selection | Observation count | Normalized record kind and scope |
|---|---|---|---|
| P | One Atom entry, with inherited namespace context; native or aggregated feed retained in dataset metadata | 1 | `procedure_snapshot`; normally procedure focus; nested lots/results remain in this observation. Feed aggregation is not a publication batch. |
| G-O | One ordinary `ybgg-dgi6` row | 1 | `procedure_projection`; procedure/planning/unresolved subject as evidenced; `record_subject` for ambiguous row facts. |
| G-L | One ordinary main-table lot row | 1 | `lot_projection`; one local Lot and lot focus; separately reported procedure facts remain procedure-scoped. |
| G-B | One main-table `es_agregada=SÍ` member row | 1 | `batch_member_projection`; `subject_kind=batch_member`, focus `record_subject`; publication is batch-scoped. |
| E | One `8idu-wkjv` row | 1 | `execution_action_projection`; partial action observation, no main-row prerequisite. A missing/zero lot marker does not identify a real lot. |
| J-O | One ordinary modern rich publication body | 1 | `publication_body`; all supported lots/results/actions in that body, no fetching phase links. |
| J-B | One modern rich batch body, members at `/publicacio/dadesPublicacio/contractesAgregada/i` | One per explicit member | `batch_publication_body`; each projection has its own member locator and the same raw ID. Shared applicable buyer/publication context is allowed, sibling facts are not. |
| J-E | One modern execution publication body | 1 | `publication_body`; multiple execution actions plus any independently reported tender/award facts. |
| L | One legacy PSCP XML publication body, regardless of JSON-named URL | 1 if a validated subject mapping exists | `publication_body`; separate legacy adapter, not P's Atom parser or J's JSON paths. Detailed support is gated. |
| T | One recognized Atom tombstone | 0 procurement observations | Retain availability in raw; no invented cancellation. Ordinary P `ANUL` entries still produce observations. |

**Selection versus occurrence:** selecting a row from an acquired page identifies the raw occurrence. Selecting a rich batch member identifies a projection within that occurrence. Tests must distinguish these locators. A caller cannot pass an arbitrary entire table page as though it were one row. A root marker must be explicit, not null.

**Proposed API shape:** a public one-raw normalization entry point may return an immutable sequence of observations; a selected-member mapper can return one. N permits zero or more observations but specifies no callable signature. Zero is legitimate for recognized availability records, not a generic suppression mechanism for failure. No additional subject joins or an entity-resolution context should be accepted.

**Batch failure gate:** N does not define delivery of successful members alongside fatal member failures. Prefer selected-projection failure isolation: each selected member either succeeds or fails with its locator; unaffected members can be normalized independently. If the public API returns only a sequence for an entire raw body, make enumeration atomic on a fatal selection failure rather than silently returning an incomplete successful sequence. Do not introduce a result-envelope schema here. The next task must choose and pin this behavior; an invalid optional member amount is recoverable and does not trigger this gate.

## 4. Happy-path plan and fixture register

### 4.1 Fixture notation and exact provenance

`Cnn/Pxxx` means the exact `placsp-xxx.xml.fragment` in the folder below, plus its original feed namespace context from `evidence.json`. `Cnn/G(selector)` means **one** selected object in that folder's `gencat-rows.json`, identified by `:id` or full `id_intern`, not an inferred row suffix. `C19/E0` and `E1` refer to the separately retained execution rows. `Jnn` means the entire named raw publication body.

| Case | Repository-relative folder; each contains `evidence.json` |
|---|---|
| C01 | `data/samples/01_amb_correction/` |
| C02 | `data/samples/02_deltebre_deadlines_budget/` |
| C03 | `data/samples/03_bsm_budget_jump/` |
| C04 | `data/samples/04_expediente_renamed/` |
| C05 | `data/samples/05_thirteen_lots/` |
| C06 | `data/samples/06_cancelled_olot/` |
| C07 | `data/samples/07_equivalent_projection/` |
| C08 | `data/samples/08_precision_and_lot_result/` |
| C09 | `data/samples/09_withdrawal_retains_award/` |
| C10 | `data/samples/10_two_placsp_ids/` |
| C11 | `data/samples/11_buyer_reassignment/` |
| C12 | `data/samples/12_award_only_placsp/` |
| C13 | `data/samples/13_timestamp_disagreement/` |
| C14 | `data/samples/14_batch_is_not_procedure/` |
| C15 | `data/samples/15_duplicate_lot_number/` |
| C16 | `data/samples/16_parent_and_lots_different_phases/` |
| C17 | `data/samples/17_expediente_collision/` |
| C18 | `data/samples/18_fuzzy_false_friend/` |
| C19 | `data/samples/19_execution_modifications/` |
| C20 | `data/samples/20_multiple_winners_empty_amounts/` |

| Rich alias | Exact retained body |
|---|---|
| J01 | [300885987.json](../../data/raw/gencat/phases/300885987.json), corrected tender |
| J01-original | [300837018.json](../../data/raw/gencat/phases/300837018.json), original tender |
| J14 | [300339416.json](../../data/raw/gencat/phases/300339416.json), six-member batch |
| J19 | [300007312.json](../../data/raw/gencat/phases/300007312.json), two modifications and retained award information |
| J20 | [300641893.json](../../data/raw/gencat/phases/300641893.json), six lots and structured contractors |
| L20-tender | [107376474.bin](../../data/raw/gencat/legacy_probes/107376474.bin), legacy XML |
| L20-award | [115526013.bin](../../data/raw/gencat/legacy_probes/115526013.bin), legacy XML |
| L07 / L09 | [103585423.bin](../../data/raw/gencat/legacy_probes/103585423.bin) / [102238048.bin](../../data/raw/gencat/legacy_probes/102238048.bin) |

Representative acquisition locators, verified from the case evidence:

| Fixture | Original occurrence |
|---|---|
| C01/P000 | Aggregated 2026 ZIP; member `PlataformasAgregadasSinMenores_20260812_030033.atom`; entry ordinal 451; byte range `[5324381,5332091)`; fragment SHA-256 `0673d0533cff55933a52e5161ba9412aab950c3c8ae24be2825991e12cfd00a7`. |
| C01/G | `ybgg-dgi6/pages/001030000.json`, row ordinal 6271, `:id=row-uvc4~ws2c-5q3s`. |
| C05/G lot 1 | `ybgg-dgi6/pages/000580000.json`, row ordinal 3845, `:id=row-iw6d.k33d-dch8`, full `id_intern=f98c30c1-1327-4dfc-b38a-5b707e9adf41_0`. |
| C14/G first member | `ybgg-dgi6/pages/000590000.json`, row ordinal 5420, `:id=row-u5pt_diur_q5ga`, full member suffix `_306344580`. |
| C19/E0, E1 | `8idu-wkjv/pages/000060000.json`, ordinals 6387 / 6388; IDs `row-immc-dqqp_ii59` / `row-5zxx.dwxh_8t7i`. |
| C20/G lot 1 | `ybgg-dgi6/pages/000000000.json`, ordinal 166, `:id=row-bqev_mmy2.eedc`, full `id_intern=0cad6ef8-d560-937e-0dc0-bdf44338687e_1`. |

All page paths above are under `data/raw/gencat/`. Other exact archive/page locators and hashes are in the respective case evidence; do not substitute source URLs for immutable acquisition identity.

### 4.2 H-P: ordinary PLACSP tender — C01/P000

Representative of the compact Catalan aggregation entry, not a statistically representative native PLACSP entry.

- One `procedure_snapshot`, source dataset aggregated, origin platform `62`; procedure focus. Atom ID ending `20283724` is separately qualified as record and procedure identity. Origin link supplies ordinary PSCP UUID `4b131001-63ad-4eac-a80a-ab91c3a9f366` and publication `300837018`; those roles are not interchangeable.
- `ContractFolderID=905451/26` remains an exact buyer-scoped procedure number. Buyer `ID_OC_PLAT=28027859`; AgentParty `62` is not the buyer or winner. No buyer NIF is present in this raw entry.
- `PUB` becomes lifecycle `submission_open_reported`; this is a source assertion, never recomputed using today's date. `MixContractIndicator=false` is an explicit false, unlike missing flags.
- Project budget `949509.1` becomes Decimal tender budget, excluded tax, EUR, procedure scope. Estimate `2183870.93` remains a separate financial purpose. No gross budget, VAT rate or inferred total.
- CPV `90513000`, source list URI retained, check digit absent. NUTS `ES511` and its NUTS-2021 source context stay execution geography, not a Barcelona municipality.
- Deadline has local date `2026-09-14`, local time `14:00:00`; its components carry no offset. Entry updated `2026-08-11T10:02:29.069+02:00` is an independently offset-qualified source marker, not the deadline's timezone.
- Two explicit specification document references retain exact URLs and administrative/technical roles. VN contains two media occurrences dated `2026-08-11` (profile and DOUE); preserve each source path, with no fabricated notice IDs. DOUE dispatch components (`2026-07-29+02:00`, `20:03:11`) are dispatch, not publication. The origin link's notice ID must not be assigned indiscriminately to both VN occurrences.
- No lots, awards or outcomes; absence of lots alone is not a no-lots declaration. No synthetic long description from Atom summary. Text language remains unknown unless explicitly evidenced for that text; code `languageID=es` does not label every string.
- Contract/method numeric crosswalk assertions require the verified list/version rule bundle (N Q3); otherwise retain exact Code plus `unmapped_code`. The retained labels and documentation support services/open conceptually, but a bare numeric code is not a sufficient key.

### 4.3 H-P-award: PLACSP formalization — C07/P001

A compact one-result success complements the tender-only fixture:

- Procedure number `C 06/2022 Exp Actio núm 8100810007-2022-0000245`, buyer `10248462`, Atom ID ending `10051590`, publication link `300701712`.
- Budget Decimal `815892.1`, estimate `1631784.2`, EUR and procedure scope. Lifecycle `RES -> resolved_unspecified`, not performance completed.
- One result code `9` under the retained TenderResultCode-2.09 vocabulary, one formalized Outcome and one `source_result` Award when that mapping is verified. Supplier `B43672138` is a structured allocation.
- Decimal `779542.5` is an **Award.amounts group total**, not duplicated into supplier allocation money. Contract reference has its explicitly supplied ID and day `2022-11-08`; this fixture has no AwardDate, so award decision date stays null. Do not borrow the 2022-09-27 date from the G row.
- No lot object, no inherited rich information, no gross award fallback. Tender, award and formalization publication occurrences retain their own paths/dates and may lack notice IDs.

### 4.4 H-G-O: ordinary main row — C01/G

Use `row-uvc4~ws2c-5q3s`. This is a realistic ordinary row even though some scope is necessarily weaker than in J01.

- One `procedure_projection`; retain both source row IDs, ordinary UUID, exact procedure number and buyer platform ID/DIR3. Buyer NIF remains absent.
- Services and open map from documented literal labels; row status is `publication_phase=evaluation`, scope `record_subject`, not lifecycle `awaiting_award`.
- Procedure money: estimate `2183870.93`, net tender `949509.1`, gross tender `1044460.01`, from the explicit procedure columns. Currency null throughout.
- Documented lot money columns also exist with the same numeric values, but no lot number/no-lots declaration occurs in this row. Keep these separately source-located with `record_subject` scope and `uncertain_scope`; do not invent a lot or silently coalesce them into procedure totals. Equality does not settle scope.
- `codi_cpv=90513000-6` preserves raw spelling, normalized code and explicit check digit; ambiguous row applicability does not become a fabricated lot. Location and duration preserve reported scope/meaning without importing J01's no-lots flag.
- Tender phase date `2026-09-17T20:18:00.000` pairs with export `300885987`; evaluation date `2026-09-21T19:16:00.000` with `300888482`. The main page is `300888482`, not the owner of all dates.
- Deadline `2026-09-14T14:00:00.000` remains floating by default. Technical created/updated timestamps become Socrata markers. No procedure-created date, current-open boolean, correction flag inferred solely from lateness, or rich document objects.
- `lots`, `awards`, `outcomes` and `execution_actions` empty; export links are source references, not specifications. No network request to the export URLs.

### 4.5 H-G-L: main-table lot row — C05 lot 1

Use `row-iw6d.k33d-dch8` (array index 0 in retained row extract).

- One observation, one local Lot numbered string `1`, lot focus. Full row ID ending `_0` remains record identity, not lot number.
- Procedure financials: estimate `83579468.07`, net budget `41129079.80`, gross budget `49766186.56`.
- Lot financials: estimate `4500965.74`, net budget `2292542.12`, gross budget `2773975.96`; CPV `50700000-2`, description “Edificis judicials Barcelona,” and result/award scoped to this local lot. Currency null; no computed VAT.
- Supplier `B60650801`, name as transmitted, net award `2011802.23`, gross `2434280.70` as supplier allocation amounts; do not also manufacture an award-group total.
- `Formalització` phase is row-subject status and result `Formalització` is a separately lot-scoped Outcome. One row award group with source-supported contract formalization date; award date `2025-10-15T17:00:00.000` must not be reduced unconditionally to a day. See R06.
- The row is not a thirteen-lot inventory. Coverage of procedure lots is partial. It cannot load the other twelve rows or copy their values. No multiplication or distribution of procedure budgets.

### 4.6 H-G-B: aggregate-publication member row — C14 first member

Use `row-u5pt_diur_q5ga`, full `id_intern=fff0ffe1-d07b-42af-ade9-dc8eb403a8b6_306344580`.

- One `batch_member_projection`, subject `batch_member`, focus `record_subject`. UUID `fff0ffe1-d07b-42af-ade9-dc8eb403a8b6` appears in `batch_identifiers`, never procedure identifiers. Full `id_intern` can also appear with member role; its suffix is not parsed into a legal contract or lot ID.
- Member number `2023/585`, title/description from this row; buyer `2988807`. DIR3 `A9999999` retained with placeholder usability/Issue, not used as reliable identity.
- Member-scoped estimate `132628.56`, tender budget `28957.25`, award allocation net/gross `28957.25` to `A28119220`, names preserved; currency unknown and no inferred VAT exemption because net equals gross.
- Aggregate publication `300339416`, date `2025-01-01T09:00:00.000`, scope `publication_batch`. Award business date `2024-11-29` is separate.
- No procedure UUID, fake lot, artificial deadline, or execution action parsed from the descriptive word “pròrroga.” Rationalization `Contracte basat en acord marc` is its own attribute; absent method remains absent.
- This raw row has no verified supplier scheme merely because the identifier looks like a NIF; retain an unclassified/unvalidated identifier rather than importing J14's field semantics.

### 4.7 H-J-B: rich batch — J14

- Enumerate exactly six member selections, pointers `/publicacio/dadesPublicacio/contractesAgregada/0` through `/5`; each observation references the same immutable body and has a distinct projection identity.
- Shared batch UUID and publication `300339416`, actual instant `2025-01-01T08:00:05.758Z`, planned instant `2025-01-01T08:00:00.000Z`, and buyer `2988807`/NIF `P1700053J` remain applicable context. Publication scope is `publication_batch` in each projection.
- Member 0 has number `2023/585`, description, CPV `66511000-5` (role unspecified, not automatically main), `nifAdjudicatari=A28119220`, award net/gross `28957.25`, budget `28957.25`, `vec=132628.56`; all member economics use `record_subject`. Calendar-serialized business dates use the approved temporal policy, not the UTC calendar day blindly.
- Members 1 and 2 both have number `2023/800`, but retain separate locators and suppliers/amounts (`W0072130H`, `7096.06`; `G08171407`, `3149.79`). No deduplication.
- Root number `2024004-AM` and title “Contractes basats en AM, 4t trimestre de 2024” are batch header material, not each member's procedure number/title. A member description does not automatically become a title. No synthesized member source ID from index, and no table `id_intern` imported.
- Member 0's `expedientIdReferencia=1efe0fb1-e5e6-4e3a-8cb6-fcc33215dad1` and `codiExpedientReferencia=2022.06` are related framework identifiers, not current procedure identity. Same rule for each other member's own references.
- `nombreInformats=6` agrees with the array; it is not a guarantee of complete procedure/award history. No source guarantees of stable member order or globally stable IDs.

### 4.8 H-E: standalone execution row — C19/E0

- One partial `execution_action_projection`; source `8idu-wkjv`, record ID `row-immc-dqqp_ii59`, buyer `9598270`, procedure number `4317110007-2021-0001388`.
- One action: `Modificació (Objectiva)` retains the literal source category and maps to modification under an approved label rule; title is action title. Date `2026-03-30T00:00:00.000` is action calendar date, not publication. Net Decimal `341124.070000000000000000` has purpose `action_amount` and null currency.
- `numero_lot=0` creates no lot. Conservative focus/action scope is `record_subject`, with `uncertain_scope` rather than a invented lot/procedure-wide applicability claim.
- Export identifies publication `300007312`; publication time is absent. Row created `2026-08-27T01:10:55.486Z` and updated `2026-09-22T01:11:51.826Z` are separate markers.
- No UUID, action identifier 1, publication date, winner, award or tender budget borrowed from J19. No missing main-row failure. `data_fi`, participants, contract ID and action amount currency stay absent if not supplied.

### 4.9 H-J-O: rich ordinary correction — J01

- One `publication_body`, ordinary UUID and number `905451/26`, buyer NIF `P0800258F` and platform ID `28027859`; named Catalan/Spanish title and description variants remain separate localized values.
- `teLots=false` and `divisioEnLots.ca=Sense lots` establish no lots despite one `dadesPublicacioLot` container. `lots=[]` with source-declared empty lot coverage; supported facts in the unsplit container can be procedure-scoped. Do not manufacture lot `0`.
- Procedure financials retain budget net `949509.1`, gross `1044460.01`, estimate `2183870.93`, explicitly reported VAT `10` and `varisTipusIva=false` in applicable amount contexts. Currency stays null: these numbers have no explicit currency field. Repeated header/container assertions need a documented structural rule or separate source-located facts, never sums.
- Actual publication `2026-09-17T18:18:05.642Z` and planned `2026-09-17T18:17:26.471Z` remain distinct. Tender phase plus `is_correction=true`, exact opening-date correction type/reason. No guessed `corrects` relation target if absent.
- Submission time `2026-09-14T12:00:00.000Z` remains unchanged; opening `2026-09-21T09:00:00.000Z` must not replace it. Combined offers/requests deadline kind is `submission_unspecified` unless the adopted structural context establishes offers.
- Four typed JP document objects have IDs `302601952`, `302601953`, `302601951`, `302601950`, titles, language and opaque delivery paths. No synthesized download URL; hash algorithm unknown. Size population depends on confirmed byte-unit semantics. Other supplied reference contexts should not be silently discarded merely to force a total count of four.
- `llocExecucio.oc="null"` is not an Aranese translation: omit that text, `invalid_value`, keep other languages/location components. Duration retains years and conditional-start prose, not a computed effective date.

### 4.10 H-J-E: rich execution — J19

- One ordinary publication-body observation, UUID `cdd2280f-bc0d-b291-4214-69ded8c1182d`, no lots under explicit `teLots=false`.
- Exactly two modification actions at `/publicacio/dadesPublicacioLot/0/modificacions/0` and `/1`, identifiers `1` and `2` qualified by source subject/type/publication context. Each explicitly references the same local publication.
- `incrementPreu` values `341124.07` / `317101.25` have purpose `modification_delta`, not generic action amount, award amount or revised total. Their dates serialize as `2026-03-29T22:00:00.000Z` / `2026-08-09T22:00:00.000Z`; interpreting them as business days March 30 / August 10 requires the transparent field-specific calendar policy (§13), not a join to E0/E1.
- Actual publication `2026-08-26T10:44:10.472Z`; planned time separately retained. No Socrata markers imported.
- Preserve independent header tender budget `3981218.08` and contractor award allocation to URBASER `A79524054`: net `3961311.99`, gross `4357443.19`, explicit VAT `10`. Retained award/formalization information is not overwritten by action amounts. The scalar `importAdjudicacio` has no automatic net/gross/group-total interpretation beyond a validated rule.
- Action `contractistes=[]` means no mapped action participants; do not copy the historical contractor into each action's parties. No sum calculating current contract value. This is stronger than an actions-only fixture.

### 4.11 H-J-lots: structured formalization — J20

- One body, six local lots **in source order** `4,1,2,3,6,5`; internal `lotId` values `0,1,2,3,4,5` are separately qualified identifiers. Internal zero is valid for an explicitly real lot 4, not a displayed synthetic lot 0.
- Lot 1 has two structured contractor allocations (`B41956970`, `A08338683`); lot 5 also has two. Preserve explicit source grouping rather than infer joint legal awards. In absent amount fields, do not create empty Money just to mirror table C20's tokens.
- Formalization business dates are not the December 2025 publication time. Phase formalization is not lifecycle completion. Procedure budget `211249.74`, estimate `422499.47` remain procedure financials, not divided among six lots.
- Method `Obert` is open; `Acord Marc` remains contracting-system attribute, not framework call-off. Supplier `tipusIdentificador.id=542` is explicitly labelled NIF in this body; that does not decode all numeric scheme codes.
- Preserve main CPV role from `cpvPrincipal`, party addresses separately from execution geography, and flag literal `"null"` language values only in supported mapped fields. Rich absent awards amounts stay absent even though C20/P000 explicitly reports zero amounts.

### 4.12 Coverage gaps, not invented happy fixtures

**Native P:** both native annual ZIPs are retained under `data/raw/placsp/native/`, but C01–C20's extracted P fragments are from the aggregated feed. Native source presence statistics and documented structures do not identify a reviewed per-entry normalization oracle. Before claiming both-feed coverage, select and review one native entry with buyer NIF, explicit net/gross budget and nested notices/documents from the read-only native analysis index; pin archive/member/ordinal/checksum and retain the source entry. This is a fixture-selection gate, not permission to synthesize a native entry by changing an aggregated entry's dataset tag.

**Legacy PSCP:** L20-tender is well-formed `<Notice>` XML with `codiceVersion=1.05b`, `TenderingProcess/diligenceId=9884AM`, notice `107376474`, title/description CDATA and a structured calendar. Content dispatch and a limited identity/text projection are supported by inspection; a complete legacy financial/lot/date mapper is not established by N Q12. §11 specifies gated expectations rather than pretending modern JSON mappings apply unchanged.

### 4.13 Shared field coverage beyond the headline cases

The examples above are not permission to implement only the most common publication columns. Parameterize N §7.1's complete main-table phase-date contract:

| Date field | Same-phase export field | Publication type |
|---|---|---|
| `data_publicacio_futura` | `url_json_futura` | future_notice |
| `data_publicacio_consulta` | `url_json_cpm` | market_consultation |
| `data_publicacio_previ` | `url_json_previ` | prior_information |
| `data_publicacio_anunci` | `url_json_licitacio` | tender_notice |
| `data_publicacio_avaluacio` | `url_json_avaluacio` | evaluation |
| `data_publicacio_adjudicacio` | `url_json_adjudicacio` | award_notice |
| `data_publicacio_formalitzacio` | `url_json_formalitzacio` | formalization_notice |
| `data_publicacio_anul` | `url_json_anulacio` | annulment_notice |
| `data_publicacio_contracte` | `url_json_agregada` | aggregate_contract_report, publication_batch scope |
| `data_publicacio_encarrec` | None established | own_resource_entrustment_notice, date-only reference allowed |

Use the real C01/C05/C09/C14/C16 rows for supplied pairings. For columns not represented by a reviewed small fixture, add just that date field to a valid ordinary row with a clearly labelled synthetic value. This tests the field's meaning, not whether the source has actually published that synthetic phase combination. For the aggregate date use C14's already valid batch context. Date without export and export without date must both yield meaningful partial publication references; removing either must not remove the independently supplied other component. Never invent `data_publicacio_execucio` from E `data` or the main phase label Execució. Do not bind all ten dates to the main page URL.

Also parameterize these bounded value-type behaviors, using one-property mutations and the validated dictionaries rather than a new general source simulator:

- Contract type, award method, urgency and contracting system remain separate dimensions. Real J20 proves open plus framework establishment; C16 proves `Obert simplificat abreujat`. For literal `Contracte de serveis especials (annex IV)`, expect broader services plus source qualifier, not an invented primary type. `Altra legislació sectorial` stays unmapped. Missing mixed-contract flag is null, explicit false remains false.
- Every mapped deadline kind is owned by its source field. Removing P EndTime yields day precision with no inserted midnight/end-of-day; removing EndDate leaves only the supported time component, never borrows the publication day. Offers and participation requests are different periods. The rich combined field cannot become offers solely from its name.
- J01's duration is two years with conditional-start prose; no arithmetic end/effective date. C16's `1 mes 15 dies` may yield separate month/day components only through an approved unambiguous text rule, otherwise retain raw text. Do not convert months to a fixed day count.
- `Location` needs a reported component; NUTS is execution territory only where its owner says so. Buyer postcode `08040` retains its zero; supplier addresses stay supplier-owned. Unknown numeric country ID is not directly ISO. No INE10-to-execution municipality inference.
- Positive award information can exist without suppliers/amount/date, provided a positive result or other grounding remains. An award phase alone is not grounding for a detail-free Award. Removing a supplier ID must not erase a name-only Party; deleting all Party evidence should omit it rather than construct an empty Party.

## 5. Real edge-case regression plan

Every C01–C20 finding is converted below into a one-input assertion. “Pair” always means two separate calls; no pair is passed into a mapper.

| Regression | Exact fixture(s) | Required result / forbidden inference |
|---|---|---|
| C01 corrections and media | C01/P000, P002; C01/G; J01-original and J01 | Preserve source's August VN dates, September corrected phase dates, separate publication IDs and opening correction. Do not diagnose a cross-record inconsistency, infer reopening, or rewrite deadline. Rich no-lots and document rules in H-J-O. |
| C02 evolving assertions | C02/P000–P009, independently; especially P000 and P005 | P000 budget `162565.2`, deadline 2025-01-24; P005 budget `177465.2`, deadline 2025-05-20. Each retains its own status/publication. No diff, previous value, legal modification or revision generation. |
| C03 budget jump | C03/P000 and P005 | Net budget `2000` versus `53000`, each valid in its own raw input. No automatic `invalid_value` due to magnitude/change, no inferred correction cause/action delta. |
| C04 renamed number | C04/P000 and P001 | Respectively `24001098` / `006_24001098`, including leading zeroes/punctuation; two lots in each supported input. Do not normalize both to a shared alias list or mutate the earlier projection. |
| C05 many lots and suffix mismatch | C05/P024; G lot 1; G full ID ending `_6` (lot 7) | P024 yields one observation with 13 lot occurrences and 13 source result groups, not 13 observations. Local references attach to the correct lot, preserve source order `1,10,11,12,13,2,...`. G `_6` reports lot `7`. No invented lot budgets in sparse P structures; no summed repeated procedure figures. |
| C06 annulment | C06/P000, G row; rich `300344003.json` separately from `300343988.json` | P `ANUL -> annulled_reported`; G annulment phase is not automatically the same lifecycle. Distinct origin annulment/corrected-tender notices; only explicit result reason becomes Outcome. No tombstone conversion. |
| C07 ordinary award detail | C07/P001 and G `row-4qjs_4vm9~67tr` | Keep the P group amount versus G per-supplier amounts; P missing award date stays missing while G supplies 2022-09-27. No cross-source equality requirement; currencies differ in availability. |
| C08 lot negative outcome | C08/P000; G lot 5 `row-am4c_5egi~vbnm` | Five P lots; G lot 5 has `resultat=Desert`, outcome deserted, while row phase remains evaluation. No positive Award from negative result alone; no propagation to other lots/procedure. Preserve P deadline seconds `23:59:59` versus G transmitted `23:59:00.000`. |
| C09 retained old award | C09/P000; G `row-r3sv~uwv9~sc39` | P lifecycle resolved-unspecified and negative result `5`/renounced, no winner imported. G retains renounced Outcome plus row Award supplier `A58846064`, net `83996.64`, old award date 2022-07-11. Negative outcome decision date does not inherit it; no active/rescinded status or automatic award-to-withdrawal link. This coexistence is not itself `inconsistent_source_values`. |
| C10 multiple P IDs | C10/P000, P001, P002 | Each observation contains only its own Atom ID (16638290 or 16638580) plus explicitly supplied ordinary origin UUID. No canonical merge/alias completion. Formalization 2024-12-13 is distinct from February 2025 publication. Named UTE remains one supplied party, not two winners split on its name. |
| C11 different buyers | C11/P000; G `row-zmki.rk8n~atvm`; rich `300286770.json` when testing that adapter | Preserve Presidència/202037 where supplied, Justícia/202266 in G row. No cause of reassignment, “current buyer” field, overwrite or cross-record inconsistency Issue. |
| C12 partial inventories | C12/P000; each of six G rows independently | P contains 25 lot structures and both positive and negative results. G only maps its selected lot (e.g. 11/Desert); no import of P winners, inferred deletion, or assertion that all source awards were enumerated. Cardinality of selected research cohort is not normalized coverage. |
| C13 notice and precision mismatch | C13/P000, three G lot rows, rich `300869210.json` and `300885950.json` | Old main URL notice 300869210 and corrected export 300885950 remain distinct. G deadline local 2026-09-16 23:59:00; P seconds 23:59:59; rich UTC 21:59:59. No cross-record second repair, maximum-clock selection, latency or history test. Precision rules gated below. |
| C14 batch identities | All six C14/G rows; J14 | One G member per call; six J member selections. The two `2023/800` occurrences stay separate; batch UUID excluded from procedure IDs, related framework UUID not promoted. Header descriptions/numbers never become member assertions. |
| C15 duplicate displayed lot | G `row-nrbp-795a.r8hs` and `row-sngf-ckt7_xibr` | Both number `3`, different raw rows/publications and award values `4070.00` / `4839.00`. Each has one lot. Neither mapper needs a cross-record duplicate Issue. Main phase `Execució` alone must not create an ExecutionAction. Same-body ambiguous duplicate-number resolution requires a synthetic test (S12). |
| C16 parent versus lot phases | G parent `row-qb3i_5px5-saz3` and five lot rows | Parent is planning/future notice and has **no procedure number**, despite title beginning `2026/7731`. Lot row `row-kddq~eark~n8nw` has number 2026/7731 and tender phase, one lot. Do not borrow number/phase/lots from another row or parse the title as an identifier. |
| C17 expediente collision | C17/P000, P001 and corresponding G rows | `1/2025` remains buyer-qualified in each observation; Ars and INTERHOSPITALIA identifiers/text remain independently source reported. No normalization of a global procedure key. Not an entity-resolution test. |
| C18 fuzzy false friend | C18/P000 and G `row-z93q_cgx2_7ssf` | Preserve each `288/2024`, buyer, title, amounts and source IDs without fuzzy cleanup or cross-record fallback. No similarity scores/matching assertions in expected output. |
| C19 multiple actions | E0 and E1 separately; J19 | Each E row yields one action, generic action amount and no publication date. J19 yields two actions/deltas and its own older award facts. No join or current-contract-total calculation. |
| C20 winners, empty tokens, legacy | C20/G `row-bqev_mmy2.eedc`, C20/P000, J20, L20-tender/award | G two suppliers, two empty net tokens **and two empty gross tokens**, with positions preserved. P has eight positive result occurrences over six lots and explicit zeros; keep valid zero amounts, not table empties. J structured missing amounts stay absent. Legacy XML selected by content, not URL suffix. |

Further real structures worth asserting explicitly: C01's separate DOUE dispatch date; J01's literal `"null"` text and conditional duration; J20's internal lot zero and supplier addresses; J19's absent action parties despite retained original contractor. They exercise contract dimensions that headline case summaries alone can miss.

## 6. Recoverable/degraded-case analysis

The following are **successful normalization** cases. Raw means the immutable occurrence plus selection and original paths, not only a diagnostic message. Paths shown are conceptual; exact locator syntax must be frozen with mapping_version. An Issue may point to an omitted normalized slot or an explicitly prefixed `raw:` locator (N §6.10).

| ID / Issue | Trigger, real evidence or minimal mutation | Preserve / omit / unresolved | Conceptual Issue.path and recoverability |
|---|---|---|---|
| R01 `invalid_value` | Replace C01/P000 net amount token `949509.1` with `not-a-decimal`; no reviewed real malformed decimal fixture. Also parameterize G money, J numeric token replaced by a JSON string, E amount. | Keep Money owner, purpose, tax basis, explicit currency, `raw_value`, `value_state=invalid`, `value=null`. Keep all other financials and observation. Do not omit Money where the contract explicitly supports invalid lexical states. | `financials/<item>/value/value` (or award/action amount); exact source token/path remain raw. Narrow Decimal conversion failure becomes Issue. |
| R02 `explicit_empty` | Real C20/G lot 1 has `\|\|` for **each** net/gross amount vector. Scalar empty-string mutation tests same contract separately. | Two positional supplier allocations, two empty Money values per tax-basis vector, `value_state=explicit_empty`, raw token `""`, value null. Do not filter tokens, insert zero or declare alignment failure merely because values are empty. | `awards/<group>/suppliers/<position>/amounts/<item>`; original complete vectors and separator spelling raw. Continue. |
| R03 `placeholder_identifier` | C09/C14 DIR3 `A9999999`; C20 `A99999999`. | Retain value and scheme, mark `usability=placeholder` under explicit reviewed sentinel policy. Other buyer IDs/names survive. Never discard entire buyer or treat placeholder as usable global identity. | `buyer/identifiers/<item>`; original token retained. Do not generalize every similar token to a sentinel without policy. |
| R04 `unmapped_code` | Unknown P status/result/list version; unknown G literal method/action category; N explicitly leaves `Altra legislació sectorial` / `Tramitacio amb mesures de gestió eficient` unmapped. Specific raw row for these labels not selected here. | Keep MappedCode.source with system/version/value/labels; `normalized=null`, `mapping=unmapped`. Keep Outcome/Status/Action when its source structure is meaningful. Unknown does not become `other`, open, closed or awarded. | `statuses/<item>/value`, `procurement_method`, `execution_actions/<item>/type`, etc. Raw code-list attributes preserved. Continue. |
| R05 `uncertain_scope` | Real C01/G documented lot money with no lot marker; C19 E `numero_lot=0`; synthetic P multi-lot result without a lot reference. | Keep supported amount/result at `record_subject` or `unknown` as established; no fabricated lot/procedure claim. P explicit reference to a nonembedded lot may instead use `Scope(kind=lots, source_lot_identifiers=...)`, no dangling local key. | Affected fact's `/scope`; conflicting/missing scope evidence and paths remain raw. Observation continues. |
| R06 `ambiguous_time` / `uncertain_precision` | G floating timestamps; C05 award time 17:00 despite a business-date-like field; C13 observed minute projection; J19/J20 midnight-converted calendar fields. | Preserve raw string and defensible components. Floating defaults to no UTC instant, zone basis unknown. Preserve nonmidnight C05 time; do not strip it. If a date-serialization rule is unapproved, do not assert the next local business day as certain. | Specific `.../at`, `.../decision_at`, `.../action_at`. Original offset/lexical timestamp recoverable. Continue; do not synthesize a zone from another record. |
| R07 `supplier_alignment` | Mutate only C20/G `import_adjudicacio_sense` to a three-token vector while suppliers still have two positions; real aggregate counts show unequal populations but do not prove this exact per-row mismatch. | Independently supported supplier/amount positions remain unresolved allocations; each gets its originating vector path and original ordinal. No zip truncation, broadcast, Cartesian product or nearest-neighbor assignment. Compatible name/ID association may remain if independently justified. | Award `/suppliers` plus relevant raw vector paths; unresolved amounts have `party=null`. Preserve all tokens; no blind reuse of parties for mismatched amounts. Continue. |
| R08 `inconsistent_source_values` | Mutate J01 `publicacio.teLots` to true, leaving explicit `Sense lots` declaration; or duplicate P's single mixed-contract flag with conflicting value. No reviewed real contradictory singleton fixture; documentation monetary typos are not a real acquisition. | Conflicting singleton remains null where nullable; repeated facts may remain separately scoped. For lot-declaration conflict, retain procedure facts, no false complete-empty inventory or fabricated Lot; ambiguous dependent facts weaker/omitted. No arbitrary last-wins rule. | Normalized singleton or `raw:` ordered conflicting paths; detail identifies paths without dumping payload. Continue if one subject is still defensible. |
| R09 `unsupported_structure` | Replace J01's administrative document `ca` list with an unexpected scalar at that supported path; optional array element with unrecognized shape. Legacy optional unsupported detail after validated envelope mapping is another example. | Skip only unsupported subtree/member assertion, keep independent documents, header and financials. Do not advertise complete collection coverage. Unknown future keys outside v1 are simply raw, not necessarily Issues. | `documents` or `raw:/publicacio/dadesPublicacio/plecsDeClausulesAdministratives/ca`; raw subtree retained. Continue. |
| R10 `invalid_value` (optional URL) | Replace C01/G one phase export `.url` with a malformed URI string; no selected real malformed supported reference. J19 buyer `web=www.vila-seca.cat` is not by itself evidence of a malformed field required in v1. | Omit unusable SourceReference (URL required); retain same-phase date-only PublicationReference. If document URL invalid but ID/title/path survives, retain document with no invalid URL. No repair/fetch or invented ID. | Omitted source-reference slot or `raw:/url_json_licitacio/url`. Preserve exact lexical source. Continue. |
| R11 `unmapped_code` (identifier scheme) | Replace C05/G `tipus_identificacio=542` with an unsupported token, leaving identifier/name. G-B first row has no scheme at all (missing is distinct). | Keep Identifier with `scheme=source_unclassified`, source-qualified namespace and `usability=unvalidated`. Unknown source scheme stays recoverable from raw; do not guess NIF from spelling. Missing scheme need not be called an unmapped **code** if no code was supplied. | Supplier identifier scheme or explicitly labelled raw type path; separate namespace for source classification. Continue. |
| R12 no Issue for ordinary absence | Real C16 parent lacks number; E missing end date; J20 absent amount; synthetic removal of one optional field. | No Identifier/Money/empty Party invented. Missing flag stays null, not false. `ingested_at` is optional at this research boundary. | No diagnostic merely for optional absence; raw shows field absence. Subject may be planning/unresolved without being fatal. |
| R13 `invalid_value` (date) | Replace one C01/G deadline with an impossible calendar date. | Keep TemporalValue.raw, unknown precision/zone, null parsed components as N §6.6 specifies. Other dates remain intact. An invalid business timestamp is not missing normalization metadata. | `deadlines/<item>/value/at`; preserve exact value and source path. Continue. |
| R14 `invalid_value` (CPV/text/boolean) | Invalid CPV token mutation; real J01/J19/J20 localized `oc="null"`; mixed-contract lexical mutation to an unsupported token. | CPV retains raw_code but code null; valid explicit check digit handling depends on validation rule. Omit literal-null translation only, preserve other languages. Invalid nullable boolean remains null, not Python truthiness of nonempty string. | Classification value, omitted localized item/raw path, or `mixed_contract`. Continue. |
| R15 `unmapped_code` / `invalid_value` (currency/unit) | Delete currencyID (absence); replace with unsupported currency token; unknown duration unit. | No currency default. For invalid/unknown currency retain amount, currency null; token raw and diagnostic for supplied invalid/unmapped token. Unknown duration unit uses `unspecified` with issue; preserve measure. Missing currency alone is normal. | Money `/currency` or period duration `/unit`. Never copy currency from sibling unrelated amount or another record. |
| R16 `uncertain_scope` (local association) | Same-body duplicate lot number makes a result reference nonunique, or explicit lot reference not embedded. | Keep source lot identifier; local keys empty unless unambiguous. No failure merely because the external lot is absent. Duplicate occurrences keep distinct keys and paths. | Outcome/Award `/scope`; source reference and candidate paths retained. If the mapper nevertheless emits a dangling key, that is B01, not R16. |
| R17 `inconsistent_source_values` (repeated subject identity) | Change only J01 `/publicacio/expedientId` to a different UUID, leaving root `/idExpedient` and other repeated subject fields unchanged. The retained phase export URLs contain numeric notice IDs, not procedure UUIDs: do not invent a UUID-bearing export route as a fixture. | The ordinary body still supplies one explicit record-subject projection. Preserve competing source identifier assertions with an Issue and exact raw paths; do not choose a canonical UUID, merge subjects, or infer that two procedures are legally identical. Omit any stronger association that requires choosing between contradictory fields unless an adopted structural rule resolves their roles. | `procedure_identifiers` plus all conflicting raw paths. Independent titles, money and dates survive. This same-body contradiction is not C13's legitimate old-page/new-export distinction. |
| R18 `unsupported_structure` / `invalid_value` (nested required field) | In J19 replace first action's type object with an unsupported structure; leave second action valid. | An ExecutionAction requires a MappedCode type. Use a validated typed-container rule (modificacions) only if explicitly adopted; otherwise omit only that action, retain raw/path and diagnostic, second action and rest of observation. Never fail a whole body merely because a nested object cannot satisfy its required field. | `execution_actions` or exact raw action/type path. Gate the structural fallback rule; no empty invented Code. |

### 6.1 Additional recovery rules

- **Explicit null is not deletion.** N defines empty/invalid Money states but does not fully define JSON null versus absent/empty-string across all scalar types. Proposed: treat a present null mapped scalar as explicitly empty with an Issue; do not create an empty Identifier or Party. Pin a field-specific Money raw token convention (`null` versus empty string) before testing it. Do not silently stringify JSON null into a valid text translation.
- **Non-finite money:** Decimal accepts some NaN/Infinity spellings, but they are not defensible procurement amounts. Proposed `invalid_value`, value null, raw preserved. JSON nonstandard NaN tokens at the byte decoder boundary may instead be invalid payload syntax; test valid JSON string mutations separately from decoder rejection.
- **Conflicting money occurrences:** financials are a scoped collection, not one root budget scalar. Repeated same-purpose values can be retained with separate paths and `inconsistent_source_values`; do not turn both into one null “budget” or arbitrarily choose the last. Only a documented structural rule may identify one as the intended value.
- **Contradiction is not always source error:** no Issue just because award information coexists with renunciation, a correction occurs after a deadline, two independent rows have different buyers, or phases differ across parent/lot rows. These are supported meanings, not incoherent singletons.
- **Optional invalid item versus fatal root:** unsupported document shape is recoverable; an unsupported whole body without a usable subject projection is not. The threshold depends on the contract's subject boundary, not how inconvenient a parser is to write.
- **Partial collection:** preserving five valid members of an optional six-item document/action collection must not assert completeness. No sibling member's facts are copied into a failed item. Batch subjects have the separate selection-level policy in §3.

## 7. Fatal failure-mode analysis

No retained successful acquisition has been established here as a genuinely fatal normalization input. Legacy XML is a format surprise, not inherently invalid. Failed HTTP requests and `.partial` bodies are not accepted raw records. Most fatal fixtures therefore must be controlled, labelled mutations of valid envelopes or bodies.

Use the public exceptions proposed in §8. `InvalidNormalizationInput` and `UnsupportedNormalizationInput` are expected failures; `NormalizationInvariantError` is a defect signal, not routine bad-data handling.

| ID / candidate | Why fatal rather than Issue; smallest realistic fixture | Detecting layer / expected result |
|---|---|---|
| F01 unsupported source/kind | Valid C01 raw envelope with routing kind changed to a future unimplemented family (not a code inside its payload). No adapter can interpret that family. | Dispatcher: `UnsupportedNormalizationInput(reason=unsupported_kind)`. A type-invalid enum/argument rejected by a raw constructor remains that layer's validation; an unexpected Python object is API misuse, not ordinary source data. |
| F02 no payload representation | Valid raw envelope with its sole payload/immutable artifact reference absent. There is no occurrence to inspect or recover from an Issue. | Raw construction should reject first. If reachable at public normalization boundary, `InvalidNormalizationInput(reason=missing_payload)` before mapping. Do not manufacture impossible typed objects just to bypass constructor validation. |
| F03 raw locator does not resolve | C01 entry ordinal or G page row index changed to one past end; or immutable resolver reports that the referenced record does not exist. | Raw accessor validates occurrence. If normalization owns that access, translate its specific not-found/locator-domain error to `InvalidNormalizationInput(reason=unresolvable_occurrence)`. Do not catch arbitrary FileNotFoundError over the whole mapper. |
| F04 locator resolves to wrong occurrence / integrity mismatch | Change only declared occurrence identity or checksum so selected bytes no longer match the raw envelope; never edit retained raw files. A projection would falsely claim provenance. | Primarily raw integrity/accessor tests. Public integration guard may translate a specific integrity mismatch into `InvalidNormalizationInput(reason=raw_integrity_mismatch)`. Full archive rehash/ZIP CRC tests do not belong in mapper tests. |
| F05 entire payload undecodable | One-character JSON syntax break in J01, or truncate P closing syntax while preserving valid external namespace context. No reliable source tree exists. | Prefer raw decoding validation; if raw accepts bytes and decoder is inside normalization, narrow JSONDecodeError/XML ParseError/UnicodeDecodeError translation to `InvalidNormalizationInput(reason=unparseable_payload)`. Test once at owning boundary, not every field helper. |
| F06 missing mandatory structural root | P entry with its single ContractFolderStatus subtree removed; J body with the required `publicacio` object removed; a main-row selection yields an array/scalar instead of an object. Recognizable adapter contract cannot locate the procurement representation. | Adapter input validation: `InvalidNormalizationInput(reason=missing_root_or_wrong_shape)` **if** that root is declared required for this adapter. Missing optional PP fields/`versio`/buyer/UUID are not this case. Unknown but coherent alternate schema is F09 instead. |
| F07 explicit projection locator absent | J14 locator `/publicacio/dadesPublicacio/contractesAgregada/6` on six-member body (0–5 valid). Falling back to root/first member would describe the wrong subject. | Selection validation: `InvalidNormalizationInput(reason=unresolvable_projection)`, includes raw ID and requested locator. Distinct from an unembedded source lot reference, which is recoverable. |
| F08 member cannot be selected defensibly | Requested J14 member selected only by nonunique number `2023/800`, or select an entry replaced by a scalar. Array position is valid occurrence localization; number matching is not a unique selector. | Prefer API that requires explicit pointer and never exposes ambiguous business-key selectors. If supported, ambiguous selector fails `InvalidNormalizationInput(reason=ambiguous_projection)`; structurally scalar member fails invalid selection shape. Never default to first matching member or entire batch-as-procedure. |
| F09 unsupported entire format/structure | Replace valid rich body with a well-formed unrecognized object family, or declare an unsupported content family/version that changes the structural root and permits no validated partial projection. | Dispatcher/adapter: `UnsupportedNormalizationInput(reason=unsupported_structure_or_format)`. Known XML through `/json/` is not invalid JSON input if actual format metadata is XML. Unknown optional child/version marker alone is not fatal. |
| F10 no defensible subject partition | In J14 replace the member collection with an opaque scalar, retaining batch header. Header describes the batch, not one member; emitting a procedure/member requires guessing. | `UnsupportedNormalizationInput(reason=unprojectable_subject)` for whole-body expansion; an explicit member pointer may fail earlier as F07. N §5.1 says retain raw and report mapping failure; an in-observation Issue alone cannot represent a case producing no observation. Do not call ordinary missing procedure identity fatal. |
| F11 required raw metadata unavailable | Remove immutable raw identity or required source/dataset context while leaving payload. Cannot truthfully populate mandatory raw reference/source attribution. | Raw envelope constructor first; defensive normalization boundary `InvalidNormalizationInput(reason=missing_provenance)` if reachable. Missing source business ID, optional ingested_at or a precise research receipt instant does not qualify. |
| B01 mapper-generated dangling references | Inject a mapper/validator seam that produces a local key with no target, duplicate keys, lots-scope with neither local nor source lot reference, or a reference to another observation. Raw remains valid. | Final invariant validator: `NormalizationInvariantError`. This is **not** a realistic bad-source fixture and not expected NormalizationError handling. Test validator/mapper integrity, no input rejection workaround. |
| B02 mandatory generated metadata/schema violation | Mapping version/schema version missing due to programming/configuration; mapper emits Money valid with null value, invalid with a number, an empty ungrounded Party, or malformed required source envelope. | Configuration/startup validation where possible; explicit postcondition guard `NormalizationInvariantError`. Do not relabel all model ValidationErrors as invalid source data. A malformed optional source value should have been handled per §6. |
| B03 unexpected program/system failure | Deliberately raised sentinel KeyError/IndexError/TypeError in a known internal seam; permission/I/O failure resolving storage. | Propagate with traceback/cause; no broad conversion to an Issue, NormalizationError, or empty list. System failures are not assertions about source quality. |

### 7.1 Conditions not fatal at this layer

Missing buyer, title, human number, procedure UUID, source-row ID, currency, deadline, amount, winner, award date, formalization date or optional representation version does not make the raw occurrence unidentifiable: the immutable raw ID/locator is separate. N permits `subject_kind=unresolved`, record-subject/unknown focus, source-only lot references and many empty collections. A sparse but defensibly selected record is not F10.

A valid known tombstone intentionally yields no procurement observation; test that dispatch rule, not a cancellation and not unsupported input. New unknown tombstone type can remain raw without guessing legal meaning. A plain empty selected object with no procurement evidence needs an explicitly adopted minimal-root/subject rule; N does not license turning every empty object into a successful phantom procedure.

### 7.2 Failures owned outside normalization

Do not reproduce acquisition tests for network timeouts, authentication, HTTP 404, retries, redirects, wrong response media type before acquisition, incomplete downloads, ZIP CRC, manifest append-only behavior, pagination drift/duplicate rows, date-cohort selection, or archive link chains. The report's four 404 legacy exports demonstrate retrieval recovery, not mapper failure. A `.partial` file is never the recommended happy raw fixture.

A bad XML fragment with omitted inherited namespaces can be a **fixture/raw reconstruction defect**, not source corruption. Tests must retain real namespace context and separately distinguish wrong namespaces in source from broken fixture packaging. Availability of an immutable artifact is an accessor responsibility; transient disk/permission failures must not be converted to “bad procurement data.”

If a future raw model guarantees parsed, validated envelopes, move F02–F06/F11 to raw-boundary tests and retain only reachable normalization integration guards. Do not test imaginary public states just to satisfy an error list.

## 8. Proposed small public exception contract

Names are proposals, not existing imports. Use two recoverable-call failure subclasses and one **separate** defect exception:

```text
Exception
  NormalizationError                 expected inability to normalize a selection
    InvalidNormalizationInput        invalid raw/projection contract
    UnsupportedNormalizationInput    coherent but unsupported/unprojectable input

RuntimeError
  NormalizationInvariantError         mapper-generated invalid output/configuration
```

The invariant exception deliberately does **not** inherit from NormalizationError. A caller catching expected bad-input failures must not silently quarantine mapper defects as source errors. Four names including the base are sufficient; no per-field DecimalError, URLNormalizationError, etc.

| Exception | Means / examples | Does NOT mean | Translation policy |
|---|---|---|---|
| `NormalizationError` | Base for a failed raw/selection call; caller may retain raw and report diagnostic context. | Not a generic catch-all and not an Issue container for every imperfect field. | Only explicitly raised semantic subclasses below. No blanket wrapping of arbitrary exceptions. |
| `InvalidNormalizationInput` | Raw provenance/selection requirements violated; missing payload, stale locator, whole-body syntax error if decoding is owned here. | Unknown business code, invalid optional money/date/URL, missing buyer/UUID, ambiguous field scope. | Specific raw accessor domain exceptions; narrow decoder exceptions at the whole-payload boundary. Validate structural membership/types explicitly rather than relying on accidental KeyError/IndexError. |
| `UnsupportedNormalizationInput` | A well-defined family/structure is not supported, or no safe subject partition exists under this mapping. | Extra unknown key, unfamiliar optional enum, valid legacy XML merely because URL says JSON, or unsupported optional nested material with an otherwise valid projection. | Usually explicit dispatch/shape checks. Do not translate every ValueError into it. Legacy adapter unsupported status is an implementation capability decision, not a source syntax diagnosis. |
| `NormalizationInvariantError` | An intentional postcondition/configuration check finds that the mapper cannot satisfy its own output contract. | Expected upstream missingness or invalid decimal text. | Raise at explicit invariant check; wrap a known final model validation failure only when it demonstrably describes mapper-generated output. Retain cause for developers. Unexpected bugs otherwise propagate unchanged. |

Proposed stable context: machine-readable `reason`, raw record ID when available, source/input kind, projection locator and safe source path. Human message is concise; do not copy entire raw bodies, supplier contact details, tokenized export URLs or exception payload dumps. No filesystem layout or decoder message must become a stable test string.

Narrow exception handling examples, described rather than implemented:

- Decimal conversion around **one money token**: understood InvalidOperation becomes R01; the normalizer continues. Failure while allocating local keys is outside that block.
- Date conversion around **one timestamp**: understood format/calendar ValueError becomes R13; keep TemporalValue.raw. It is not a whole-record InvalidNormalizationInput.
- JSON/XML decoding around **the whole selected representation**: understood syntax/encoding failure becomes F05 if this layer owns decoding. URI parsing errors are not caught there.
- Missing local source lot target: do not raise because lookup has no match; emit source-qualified unresolved reference. Missing **mapper local key** after construction is B01.
- URI validation: explicit invalid optional reference becomes R10. Do not catch every AttributeError caused by passing unexpected internal values to a URL helper.
- Unexpected KeyError, IndexError, AssertionError, TypeError or RuntimeError: deliberately propagate unless an extremely narrow, documented boundary establishes a different meaning. Never `except Exception: return []` or `except Exception: issues.append(...)`.

Tests should verify exact exception class/reason and input identity/selection, preservation of cause where translated, no partial successful observation for a failed selection, and no mutation. Message prose/traceback line numbers are not API contracts.

## 9. Synthetic-fixture plan

**No synthetic fixtures are created by this document.** Future mutations operate on independent copies of real fixtures, never files under `data/raw/`. Label them synthetic and record base checksum, exact changed property, mutation recipe and represented upstream change. Unchanged surrounding structure remains valid. Each parameterized variant is a separate mutation, not one fixture accumulating faults.

| Synthetic ID | Base and sole relevant change | Represents / proves |
|---|---|---|
| S01 | C01/P000 net money text to `not-a-decimal`; analogous one money path in G/J/E separately | Corrupt amount; R01 survives with invalid Money, unrelated values unchanged. |
| S02 | C05/G lot 1 net award to empty string, `0`, or valid JSON null in separate variants | Empty/zero/null distinction; pin null policy first. C20 already covers real vector empties. |
| S03 | C01/P000 one lifecycle/method/result code or its code-list version changed, one variant each | Vocabulary drift; retain exact source code, never guess enum. Result variant uses C07/P001. |
| S04 | C05/G one supplier-type code replaced with unknown token | Unknown identifier scheme is not a missing supplier or NIF guess. |
| S05 | C01/G one deadline replaced by impossible date or a floating DST gap/overlap time | Invalid syntax versus valid ambiguous local time. Use 2026-03-29 02:30 and 2026-10-25 02:30 only under an explicitly selected Europe/Madrid assumption policy; no unique UTC guess. |
| S06 | C20/G lot 1 net amount vector replaced by `10\|\|20\|\|30` (actual field uses `\|\|`, escaping here is Markdown only) | Mismatched amount vector with all other vectors untouched; independently preserve positions. Additional variant changes only supplier-name length. |
| S07 | C01/P000 add a conflicting repeated `MixContractIndicator` | Duplicate source singleton must not use first/last-wins. Retain null normalized flag plus all conflict paths. |
| S08 | J01 change administrative-specification language list to a scalar | Optional supported container drift; lose only that reference collection, not observation. |
| S09 | C01/G mutate one export URI; separate J01 variant changes only `/publicacio/expedientId` to a different UUID | Malformed optional URL (R10) versus conflicting repeated same-body source identity (R17); no invented export URI structure. |
| S10 | C01/P000 remove currencyID on one amount; separate variant replaces it with unknown token | No EUR default or borrowing from adjacent financial item. |
| S11 | C05/P024 remove one result's explicit lot reference | Unknown result scope, not automatic procedure scope or fatal failure. |
| S12 | C05/P024 change only second embedded lot ID `10` to `1` | Two local occurrences now have number 1; references to 1 are ambiguous and to 10 may remain source-only. Distinct local keys, no arbitrary match/dangling key. This is synthetic same-body evidence, unlike C15's distinct rows. |
| S13 | J01 flip only `teLots` to true | Contradictory lot declarations; retain procedure projection with uncertainty, no fake lot inventory. |
| S14 | C01/P000 one CPV token malformed; separate variant invalid mixed-contract boolean or unknown duration unit | R14/R15 preserve raw and other facts; no prefix slicing/truthiness guesses. |
| S15 | C01/G remove one optional field (e.g. objecte_contracte); E0 remove data in a separate variant | Absence itself is not error/zero/deletion; action still justified by its type/title/amount. |
| S16 | J19 first action type object replaced with scalar | Nested required-field handling, structural fallback policy gate R18; other action/award survives. |
| S17 | J14 change `nombreInformats` from 6 to 7 | Count disagreement does not fabricate seventh member; proposed `inconsistent_source_values`, no complete coverage claim. Six explicit selections remain valid. |
| S18 | C09/P000 add one award monetary subtree containing only a zero placeholder to the negative result | A negative result plus zero money alone must not create Award. This targeted structure insertion is labelled synthetic, not claimed as a retained negative-zero example. |
| S19 | J01 change only document size to a negative value; separate variant declares multiple VAT rates true in its applicable money context | Invalid supported size omitted with Issue; multi-rate flag prevents a misleading single applied VAT rate. Requires adopted field/unit rules. |
| S20 | C01/P000 add a second dated reference in one existing VN media group | Supported repeated publication occurrences at one type/media; no collapse to first/last date or fabricated unique notice. Documented structure, not observed multiplicity in this particular base. |
| S21 | C07/P001 add a second WinningParty within the same positive TR | Multiple structured suppliers share the same group total; no allocation broadcasting. Real C20/P000 exercises separate TRs, not this exact shape. |
| S22 | C01/P000 remap XML prefixes consistently without changing namespace URIs; separate wrong-URI variant | Prefix-insensitive, URI-sensitive supported structures. Wrong required namespace must not be accepted by wildcard matching. |
| S23 | J14 mutate one selected member's amount only | Invalid Money remains local to that member; all other member projections unchanged, common header unaffected. No fatal batch failure. |
| S24 | Valid real envelope with one invalid routing tag, locator, raw ID or payload reference, variants F01–F04/F07/F11 | Invalid normalization input/provenance rather than imperfect procurement data; source bytes unchanged. |
| S25 | J01 remove one closing JSON delimiter; P000 truncate closing syntax in separate variant | Whole-body parse failure F05 with otherwise valid context. Test only at decoder owner boundary. |
| S26 | P000 remove ContractFolderStatus; J01 remove publicacio; row selection replaced with scalar, separate variants | Missing adapter structural root F06, not missing optional field. |
| S27 | J14 member array replaced by opaque scalar; separate member-selection target replaced with scalar | Whole-body subject partition unsupported vs selected member shape invalid. Never manufacture a procedure from batch header. |
| S28 | Valid J01 envelope points to a well-formed unsupported root family | F09 coherent but unsupported whole representation; no arbitrary JSON parser error. |
| S29 | P fixture copied with same source ID/timestamp but one changed budget token, new immutable occurrence envelope | Two independent normalizations preserve each value and raw pointer. Tests identity isolation only, not change detection or hashing policy. |
| S30 | Add one documented phase-date field to C16 parent for a missing date-family example; separately remove one date or export from a real paired C01/C05/C14 row | All ten mappings in §4.13, independently meaningful date-only/export-only references. No invented execution date column. |
| S31 | C01/P000 remove only EndTime or only EndDate, separate variants | Partial TemporalValue without midnight, end-of-day or another field's date fallback. |
| S32 | C05/G replace only contract-type label with documented Annex IV services or intentionally unmapped sectoral legislation, separate variants | Broader versus unmapped crosswalk; no contract-type/method/system conflation. |
| S33 | C07/P001 remove its WinningParty subtree; separate variant removes only supplier ID | Positive formalization/contract evidence still grounds Award with zero suppliers; name-only Party remains valid in second variant. Missing optional supplier is not fatal. |

Bug tests B01–B03 are **not** synthetic bad-source fixtures. Use an explicit validator seam or small controlled internal stub to demonstrate propagation/postconditions; label it fault injection. Do not corrupt source data to manufacture a dangling reference that a correct mapper could represent safely.

For fatal byte mutations, generate an internally consistent synthetic raw envelope/checksum so integrity rejection does not mask the intended parser test. For integrity tests, deliberately mismatch only that metadata. For optional-field mutations preserve source format and numeric lexical evidence (JSON decimal precision must not be damaged by a float round trip).

## 10. Invariant/property-test plan

Use deterministic parametrized assertions first; pytest is available, Hypothesis is not a current dependency. Bounded exhaustive token examples and metamorphic mutations provide property coverage without adding a library. A future property-testing dependency is a separate choice, not required by this document.

| ID | Invariant and effective test style |
|---|---|
| I01 one immutable input | Shared assertion over every successful fixture: one raw ID, matching explicit locator, schema/mapping version and transport source; repeated item paths stay within that occurrence. J14 members share raw ID but distinct member locators. |
| I02 no joins/fallback | Fixed C09/C11/C12/C19 and isolated-call tests: access only this raw artifact, no sibling row/body lookup. Run before/after normalizing another record; output semantic content unchanged. Do not create a reconciliation test harness. |
| I03 identities remain typed | Parameterize C01/C14/J14/J19/J20: record, procedure, number, publication, batch, member, lot, supplier and action roles/namespaces distinct. Batch UUID is absent from procedure identifiers; related framework IDs excluded too. |
| I04 lot occurrence semantics | Fixed C05/C15/J01/J20 plus S12: no invented displayed lot 0; an explicit internal lotId 0 remains valid; suffix never interpreted as official number; duplicate displayed numbers permitted; local keys unique. |
| I05 financial scope | C05 all 13 G rows normalized independently: each procedure amount remains procedure-scoped once per source assertion, never multiplied/recast as lot money. P sparse lot budgets remain missing. No computed totals/distribution. |
| I06 money states and precision | Parameterized missing/empty/invalid/zero/negative/large-precision decimal tokens: `value` non-null iff state valid, exact Decimal and raw spelling preserved; absent field produces no Money. Negative modification deltas allowed. Proposed nonfinite rejection as R01. |
| I07 currency/tax | Bare G fixtures currency null; P explicit EUR retained only on applicable amounts; S10 unknown stays null. No derived VAT from equal/divergent net/gross; explicit multiple-rate flag does not imply one rate. |
| I08 missing is not a claim | S15 plus C16/J20: absence never becomes zero/false/empty identifier/deletion/no-lots; explicit false and valid zero survive. Empty normalized collection alone carries no complete-empty meaning. |
| I09 no guessed enum | S03/S04/S14: known source vocabulary mappings include system/version; unknown maps to null/unmapped, not Other. Changing list version cannot silently reuse a bare-code dictionary without an approved compatibility rule. |
| I10 separate status dimensions | All G fixtures have source publication phase, not fabricated P lifecycle; C08 lot outcome not global roll-up; P RES not performance-completed. No current-clock-based status rewrite. |
| I11 negative results and historical awards | C09 and S18: negative alone creates no Award; retained positive facts remain separate; old award date not copied into negative Outcome; no inferred legal rescission link. |
| I12 action ownership | E0/J19: action amounts/dates in actions only; original tender/award finances unchanged; generic E amount is not rich delta; no current-contract-total arithmetic. |
| I13 temporal separation | C01/C05/C13/C19/J20: deadline, dispatch, publication, planned publication, decision, formalization, action and source-marker clocks retain roles. Raw receipt/acceptance not substituted. Date-only UTC instant null; floating UTC null by default; explicit offset preserved. |
| I14 local referential integrity | Walk every collection and nested supplier allocation: unique keys across observation; every lot/publication/outcome local key resolves in the correct collection of this observation. Source identifiers need not resolve locally and are not dangling keys. B01 validates guard. |
| I15 uncertainty not guessed | R05/R07/R16: weak scope/alignment survives; no first candidate, scalar broadcast or Cartesian pairing. Unsupported singleton assertions omitted/null while independent supported facts stay. |
| I16 positional order | C20/J20/S06/S20/S21: preserve supplier tokens including leading/trailing/interior empties, source positions and structured order. Same numeric ordinal may appear in different unresolved vectors, disambiguated by path; never sort parties before alignment. |
| I17 text/identifier fidelity | C04/C10/C16/C17/J01: punctuation/leading zeros/case retained; unknown language null; named translations preserve text; source literal `null` not a translation; no title-derived number or consortium-name splitting. |
| I18 no hidden completeness | Every fixture's empty/partial collections examined; G-L lots partial, J01 only source-declared no-lots complete-empty. Full JSON array mapped does not prove all historical publications/awards. Unsupported children cannot strengthen coverage. |
| I19 no document claims beyond input | J01/L20/P references: exact URLs/delivery tokens retained without synthesis; export not specification; reported hash not locally verified and algorithm not guessed from length. No binary fetching. |
| I20 deterministic interpretation / immutable input | Repeated mapping with fixed versions/context yields same semantic fields, order, scopes, paths and diagnostics; payload bytes/parsed view unchanged. Do not require identical observation ID until its generation policy is adopted, or a canonical semantic hash. No clock/network dependency. |
| I21 namespace/format correctness | S22 and legacy fixtures: same URI/different prefix same semantics; wrong required URI not wildcard-matched; `/json/` path does not dictate decoder. |
| I22 batch isolation | J14/S23: changing member i never changes business facts of member j; applicable shared header may be copied with batch scope; array index is a locator not a source member ID. No assertions of stable identity after reorder. |
| I23 recoverable locality | Each single-field mutation changes only dependent assertions/issues/coverage. Unrelated buyer, publication, titles, valid money and sibling collection members remain unchanged. No swallowed exception producing mostly empty observation. |
| I24 programmer errors remain visible | B01–B03: expected NormalizationError catch does not catch invariant exception; unexpected sentinel bug propagates, not Issue/empty success. |
| I25 no canonical artifacts | Shared field/schema assertion: no canonical procedure/party IDs, match decisions, revision numbers, resolved history, inferred relations or source priority. Source ID equality in C10/C17/C18 does not trigger any lookup or content merge. |

Property tests should generate only inputs relevant to a claimed supported contract. Arbitrary dictionaries with every field broken are not a substitute for realistic one-property mutations. Do not write permissive “never raises for any input” properties: that would hide programmer bugs and contradict fatal input handling.

## 11. Detailed test matrix

This matrix is the implementation index. Detailed assertions and source paths in §§4–10 are part of each row, not optional background. `Real` means a retained source occurrence, even when later extracted into a small fixture. `Synthetic Sxx` means the one-property mutation in §9; `Fault` means an internal defect injection. `Base` in the diagnostics column means the adopted baseline described in §2.3, not arbitrary extra Issues. `—` in exception column means success (possibly partial/diagnosed), never “exception unspecified.”

### 11.1 Happy and real regression matrix

| Test ID / category | Source / kind | Fixture origin / realness / case | Purpose and important expected assertions | Issues | Exception / why it matters |
|---|---|---|---|---|---|
| H01 p_tender / happy | P / procedure_snapshot | C01/P000, Real C01 | H-P: one procedure projection; EUR estimate/budget, correct buyer/origin, CPV, two VN media, dispatch, two specs; no awards/gross/borrowed NIF. | Base; ambiguous_time on unzoned deadline under default policy; unmapped_code only for unsupported verified-rule coverage | —; ordinary compact entry contract. |
| H02 p_award / happy | P / procedure_snapshot | C07/P001, Real C07 | H-P-award: one source-result award, group total 779542.5, supplier B43672138, contract date 2022-11-08; award date null. | Base | —; positive results are not flattened supplier totals. |
| H03 g_ordinary / happy | G-O / procedure_projection | C01/G row-uvc4~ws2c-5q3s, Real C01 | H-G-O: procedure money plus unresolved lot-column scope, no Lot; phase not lifecycle; two named phase associations. | uncertain_scope, ambiguous_time; Base | —; normal imperfect row still useful. |
| H04 g_lot / happy | G-L / lot_projection | C05/G row-iw6d.k33d-dch8, Real C05 | H-G-L exact procedure/lot finances; one lot; supplier money; row phase versus lot outcome; partial lots. | ambiguous_time, uncertain_precision for nonmidnight business-date policy; Base | —; prevents scope inflation. |
| H05 g_batch_member / happy | G-B / batch_member_projection | C14/G row-u5pt_diur_q5ga, Real C14 | H-G-B member identity/number/economics; batch publication; unknown currency/supplier scheme; no UUID procedure identity. | placeholder_identifier, ambiguous_time; Base | —; dominant source population must not collapse to batches. |
| H06 execution_row / happy | E / execution_action_projection | C19/E0, Real C19 | H-E one action_amount, action day, no main row/UUID/publication instant/action ID borrowed. | uncertain_scope; Base | —; standalone partial execution supported. |
| H07 rich_ordinary / happy | J-O / publication_body | J01, Real C01 | H-J-O exact rich correction, scoped no-lots facts, multilingual title, document paths, explicit VAT. | invalid_value for literal-null mapped text; Base | —; rich source support without inventing download URLs. |
| H08 rich_batch / happy | J-B / batch_publication_body | J14 all 6 selections, Real C14 | H-J-B six distinct locators, own member values; common batch publication; no header title/number copied. | Temporal policy Base; optional unmapped source categories as reviewed | —; one raw can safely fan out. |
| H09 rich_execution / happy | J-E / publication_body | J19, Real C19 | H-J-E two deltas, one publication, retained original award/budget, no contractor copied to empty action parties. | invalid_value for mapped literal-null text; temporal Base | —; independent financial/time roles in one body. |
| H10 rich_lots / happy | J-O / publication_body | J20, Real C20 | H-J-lots six source-ordered lots, internal IDs distinct, multiple structured winners, absent amount stays absent. | invalid_value for mapped literal-null text; temporal Base | —; rich grouping differs from flat vectors. |
| H11 native_entry / happy, gated | P / procedure_snapshot | Retained native 2025/2026 ZIP; Real, no reviewed entry selected | Select/pin native fixture per §4.12; buyer NIF versus winner; net/gross; nested publication/document paths. Do not assert exact fields before fixture review. | To pin from fixture/rules | — once supported; avoids claiming aggregated samples cover native structures. |
| E01 corrected_deadline_not_reopened / edge | P, G-O, J-O / respective kinds | C01/P002, G; J01 and original, Real C01 | Independent calls preserve original/corrected notices; deadline unchanged; no inferred reopening/relations. | Base, no inconsistency merely for date ordering | —; correction semantics. |
| E02 evolving_budget_deadline / edge | P / procedure_snapshot | C02/P000, P005 (expand all 10), Real C02 | 162565.2/2025-01-24 versus 177465.2/2025-05-20 per input; no history/delta creation. | Base | —; no historical-state reconstruction. |
| E03 large_budget_change / edge | P / procedure_snapshot | C03/P000 and P005, Real C03 | 2000 versus 53000 remain reported budgets; no magnitude rejection/legal-cause inference. | Base | —; unusual value not automatically invalid. |
| E04 exact_renamed_number / edge | P / procedure_snapshot | C04/P000 and P001, Real C04 | Exact 24001098 / 006_24001098 in independent observations, no merged aliases. | Base | —; identifier fidelity. |
| E05 thirteen_lots / edge | P / procedure_snapshot | C05/P024, Real C05 | One observation, 13 lots and source result groups; lot 1 award 2011802.23; all explicit lot references resolve; no lot budgets imported. | Base | —; nested cardinality and references. |
| E06 row_suffix_not_number / edge | G-L / lot_projection | C05/G full id_intern ending _6, Real C05 | Lot number 7, full id_intern record role, not number 6; one lot only. | Base | —; concrete suffix counterexample. |
| E07 annulled_entry / edge | P/G-O/J-O | C06/P000, G, rich 300344003 independently, Real C06 | P ANUL normal observation, separate annulment publication from 300343988; only explicit result becomes Outcome. | Base | —; no availability/cancellation conflation. |
| E08 deserted_lot / edge | P/G-L | C08/P000; G lot 5, Real C08 | G Desert outcome scoped lot, evaluation phase retained, no positive award from Desert alone. P000 has no TenderResult: its outcomes stay empty, not enriched from G. | Base | —; no phase/lifecycle/result roll-up. |
| E09 award_and_renunciation / edge | P/G-O | C09/P000 and G row-r3sv~uwv9~sc39, Real C09 | G both old award and negative outcome; P no imported winner; no inferred rescission or old date on outcome. | G placeholder_identifier, uncertain_scope/time Base; no inconsistency for coexistence | —; prevents historical fact erasure. |
| E10 two_atom_ids / edge | P / procedure_snapshot | C10/P000–P002, Real C10 | Each own Atom ID, explicit UUID only; old formalization date not publication; no UTE name decomposition. | Base | —; identity roles without resolution. |
| E11 buyer_as_reported / edge | P/G-O/J-O | C11/P000, G, 300286770, Real C11 | Preserve each buyer; no current-buyer selection or reassignment explanation. | Base, no cross-record conflict Issue | —; no reconciliation. |
| E12 partial_lots_awards / edge | P/G-L | C12/P000 and six G rows independently, Real C12 | P 25 lots, source results; G one lot; no missing award fallback or completeness/deletion claim. | Base | —; cohort absence is not source completeness. |
| E13 timestamp_precision / edge | P/G-L/J-O | C13/P000/G; rich 300869210 and 300885950, Real C13 | Separate old page/new export; preserve 23:59:00 versus 23:59:59; no per-record join to repair precision/UTC. | ambiguous_time/uncertain_precision where rule unresolved; Base | —; freeze temporal policy before exact precision golden. |
| E14 colliding_batch_numbers / edge | G-B/J-B | C14/G members _306344581 and _306344582; J14 /1,/2, Real C14 | Both 2023/800, distinct projections and values 7096.06/3149.79; batch and related IDs not procedure IDs. | Base | —; no member coalescing. |
| E15 duplicate_lot_rows / edge | G-L / lot_projection | C15/G row-nrbp-795a.r8hs / row-sngf-ckt7_xibr, Real C15 | Each lot 3 with own source publication/award; phase Execució creates no action. | Base; no cross-record duplicate Issue | —; no global lot-number uniqueness. |
| E16 planning_parent / edge | G-O/G-L | C16 parent + five rows independently, Real C16 | Parent planning/no number/no lots; lot row tender/number supplied. No title-number extraction or maximum phase. | Base; optional absence no error | —; sparse planning is valid. |
| E17 buyer_scoped_number / edge | P/G-O | C17 both records, Real C17 | Number 1/2025 retained in each buyer context; no canonical key/matching call. | Base | —; no resolution functionality. |
| E18 no_fuzzy_fallback / edge | P/G-O | C18/P000/G row-z93q_cgx2_7ssf, Real C18 | Exact own 288/2024/title/buyer/amount; no similar-record enrichment. | Base | —; no lossy matching in mapping. |
| E19 multiple_actions / edge | E/J-E | C19/E0,E1; J19 separately, Real C19 | One action per row versus two per body; purpose/date ownership exactly H-E/H-J-E. | Base | —; publication is not action cardinality. |
| E20 multiple_winners_empty / recoverable | G-L / lot_projection | C20/G row-bqev_mmy2.eedc, Real C20 | Two suppliers; 2 net + 2 gross explicit-empty Money tokens; no group total or zero. | explicit_empty at each affected amount (grouped issue policy may encode multiple paths), placeholder_identifier; Base; no supplier_alignment merely for empties | —; positional loss prevention. |
| E21 explicit_zero_not_empty / edge | P / procedure_snapshot | C20/P000, Real C20 | Eight positive result groups, six lots, explicit zero group amounts valid; two results for lot 1 remain separate. | Base | —; no repair from G empty/rich missing values. |
| E22 no_lots_container / edge | J-O/J-E | J01/J19, Real C01/C19 | Empty lots with explicit no-lots coverage; container facts mapped conservatively to unsplit procedure; no lot 0. | Base | —; source structure is not always entity. |
| E23 internal_zero_real_lot / edge | J-O / publication_body | J20 /dadesPublicacioLot/0, Real C20 | Lot.number=4, internal ID=0, no mistaken rejection. Body input still one observation with all lots. | Base | —; local source ID is not displayed number. |
| E24 legacy_content_dispatch / edge, gated | L / publication_body | L20-tender, Real C20 | XML recognition through json route; validated minimal notice/number/text projection, unsupported optional detail diagnosed; no JSONDecodeError. See §13 legacy gate. | unsupported_structure only for unsupported mapped optional paths | — with approved minimal adapter; otherwise explicit UnsupportedNormalizationInput capability failure, not invalid source. |
| E25 document_metadata / edge | J-O/P | J01; C01/P000, Real C01 | Opaque rich paths versus explicit P URLs; hash algorithm null, no binary claims; media notices vs attachments distinct. | Base; size-unit gate | —; exact reference semantics. |

### 11.2 Recoverable and synthetic matrix

Each row expects a successful observation; unaffected baseline fields must remain equal by I23. The R/S references supply the exact source change, retained/omitted values and Issue paths.

| Test ID / category | Source / raw adapter kind | Fixture / realness | Purpose / expected behavior and key assertions | Expected Issues | Exception / why |
|---|---|---|---|---|---|
| D01 invalid_decimal / recoverable | P,G-O,G-L,G-B,E,J-O,J-B,J-E money paths | S01, Synthetic from respective H fixtures | R01 invalid Money retained, null value, exact lexical token; surrounding observation survives. | invalid_value | —; token parse error not record failure. |
| D02 empty_zero_missing / recoverable | G-L, J-O; E for absence | S02/S15; J20, Real and Synthetic | Separate variants for absent/empty/zero/null; explicit empty not zero, absent not Money; gate null spelling. | explicit_empty only for adopted explicit-null/empty cases | —; missingness contract. |
| D03 unknown_codes / recoverable | P,G-O,G-L,G-B,E,J-O,J-B,J-E | S03 and equivalent one code changes, Synthetic | R04 exact source Code with null normalized; retain status/outcome/action owner. Parameterize list version independently. | unmapped_code | —; vocabulary drift. |
| D04 unknown_identifier_scheme / recoverable | G-L/J-O/P party identifiers | S04 (C05); analogous single scheme mutation | R11 source_unclassified, unvalidated, name/value preserved; no NIF guess. | unmapped_code when source supplies unsupported code | —; unknown scheme not unknown party. |
| D05 placeholders / recoverable | G-B/G-O/G-L | C14/C09/C20, Real | R03 both DIR3 sentinel spellings; preserve buyer platform ID/name. | placeholder_identifier | —; known sentinel not fatal. |
| D06 invalid_or_floating_time / recoverable | G-O/E/J-E/P time-bearing paths | S05, Synthetic; C05/C13/J19 Real | R06/R13 raw retained; invalid components null; floating no UTC; DST not unique; preserve C05 17:00. | invalid_value or ambiguous_time/uncertain_precision by variant | —; time uncertainty is representable. |
| D07 vector_length_mismatch / recoverable | G-L / lot_projection | S06, Synthetic C20 | R07 no zip/broadcast, all amounts/party positions recoverable, unresolved association; independent gross vector not discarded. | supplier_alignment | —; alignment ambiguity not truncation. |
| D08 conflicting_singleton / recoverable | P/J-O | S07/S13, separate Synthetic fixtures | R08 nullable flag unresolved/all paths; contradictory lots do not create false inventory. | inconsistent_source_values; uncertain_scope on affected facts | —; do not choose by order. |
| D09 unsupported_optional_subtree / recoverable | J-O/J-E/L when supported | S08/S16; legacy optional paths after gate | R09/R18 only unsupported assertion omitted; other documents/action and header survive, no complete coverage. | unsupported_structure (or invalid_value for established scalar lexical failure) | —; local structural change. |
| D10 optional_bad_url / recoverable | G-O/P/J-O | S09 malformed variant | R10 omit invalid reference only; preserve date-only publication or ID-bearing document; no fetch/repair. | invalid_value | —; URL optional to subject. |
| D11 missing_unknown_currency / recoverable | P/J-O money | S10, Synthetic | R15 absent currency null with no inferred EUR; unsupported token null plus issue; valid amount unchanged. | none for missing; unmapped_code/invalid_value for supplied unsupported token per rule | —; qualification not fabricated. |
| D12 unknown_result_scope / recoverable | P / procedure_snapshot | S11, Synthetic C05 | Keep outcome/award at unknown scope; do not attach all lots or procedure. | uncertain_scope | —; safe weak scope exists. |
| D13 ambiguous_local_lot / recoverable | P / procedure_snapshot | S12, Synthetic C05 inspired by C15 | Two lot 1 occurrences distinct; source-only references to 1/10 where ambiguous/unembedded; no dangling local refs. | uncertain_scope for ambiguity | —; not an output invariant failure. |
| D14 invalid_cpv_boolean_unit / recoverable | P/G/J supported paths | S14, Synthetic | R14 malformed CPV raw preserved/code null; boolean null; unknown duration unit unspecified. | invalid_value or unmapped_code by variant | —; no coercion guesses. |
| D15 missing_optional_fields / happy | All ordinary adapter families | S15 and per-family removal; C16 parent Real | R12 keep defensible partial subject; no field fallback or missing-optional exception. | No new Issue solely for absence | —; no overstrict schema. |
| D16 count_mismatch / recoverable | J-B / batch_publication_body | S17, Synthetic J14 | Six explicit member projections, no seventh; disagreeing count diagnostic, no complete inventory inference. | inconsistent_source_values (proposed) | —; header count not invented member. |
| D17 negative_zero_not_award / edge | P / procedure_snapshot | S18, Synthetic C09 | Negative Outcome survives, no Award justified by added zero-only money subtree. | Only justified source-anomaly diagnostic if policy adopts one; no automatic invalid decimal | —; positive evidence guard. |
| D18 bad_size_multi_vat / recoverable | J-O / publication_body | S19, independent Synthetic J01 variants | Negative size omitted (if size mapped); multiple-rate flag retained and no unqualified single applied rate. | invalid_value for size; inconsistent_source_values only if actual applicable rates contradict | —; explicit tax/metadata meaning. |
| D19 repeated_media_dates / edge | P / procedure_snapshot | S20, Synthetic C01 | One more publication occurrence at new source path; existing media/date occurrences intact. | Base | —; VN group not single notice. |
| D20 repeated_winning_parties / edge | P / procedure_snapshot | S21, Synthetic C07 | Two structured suppliers in one source-result group; original group amount not duplicated to allocations. | Base | —; preserves group ownership. |
| D21 namespace_equivalence / invariant | P / procedure_snapshot | S22 equivalent-prefix variant, Synthetic | Semantics unchanged under consistent prefix rename; exact locator representation may differ under approved syntax. | Same semantic diagnostics | —; use namespace URIs. |
| D22 one_bad_batch_amount / recoverable | J-B / batch_publication_body | S23, Synthetic J14 | Selected member invalid Money; five siblings' fields unchanged; six observations remain possible. | invalid_value only at selected member amount plus Base | —; not atomic fatal batch failure. |
| D23 contradictory_subject_ids / recoverable | J-O / publication_body | S09 nested-UUID variant, Synthetic J01 | R17 preserve competing reported identifiers/paths without choosing canonical identity; independent facts survive, unsupported associations remain unresolved. | inconsistent_source_values | —; same-input structural conflict, not cross-record comparison. |
| D24 literal_null_text / recoverable | J-O/J-E | J01/J19/J20, Real | Omit only mapped literal-null translation, preserve other languages and geography roles. | invalid_value | —; real imperfect multilingual content. |
| D25 phase_date_families / edge | G-O/G-L/G-B | C01/C05/C09/C14/C16 Real; S30 Synthetic for uncovered variants | Exact ten field/type/export pairings in §4.13, correct batch scope, no main-page binding shortcut; independent date-only and link-only references remain meaningful. | ambiguous_time on floating timestamp assertions; Base | —; systematic publication mapping, not only common phases. |
| D26 partial_deadline_components / recoverable | P / procedure_snapshot | S31, Synthetic C01 | EndDate-only is day/no UTC or invented time; EndTime-only retains supported partial clock without date fallback. | No invalid_value merely for missing component; ambiguous_time when applicable | —; partial timestamp not whole-record failure. |
| D27 taxonomy_dimensions / edge | G-L/J-O | C16/J20 Real; S32 Synthetic C05 | Open simplified abbreviated distinct from open; open + framework system not call-off; Annex IV broader services with qualifier; sectoral law unmapped. | unmapped_code only for intentionally unsupported category; Base | —; no overbroad taxonomy defaults. |
| D28 incomplete_award_parties / edge | P / procedure_snapshot | S33, Synthetic C07 | Award remains grounded by positive/contract facts with no suppliers; separate ID-removal case keeps exact supplier name and no fabricated identifier. | No new Issue solely for optional absence | —; meaningful objects rather than completeness constraints. |

### 11.3 Fatal, defect and boundary matrix

“Conditional owner” means first decide whether the future raw model allows this input to reach normalization (§7.2). The test must then be placed at the actual owning boundary, not weakened to accept arbitrary Python exceptions.

| Test ID / category | Source / kind | Fixture origin / realness | Purpose and important assertions | Issues | Expected exception/result and reason |
|---|---|---|---|---|---|
| F01 unsupported_dispatch / fatal | All dispatch kinds | S24, Synthetic valid envelope + future kind | No mapper invoked, no output/raw mutation. | Not an observation Issue | UnsupportedNormalizationInput / unsupported_kind. |
| F02 missing_payload / fatal, conditional owner | All | S24, Synthetic envelope | No valid occurrence; raw constructor or public preflight rejection. | None | InvalidNormalizationInput / missing_payload if public boundary reachable. |
| F03 unresolved_occurrence / fatal, conditional owner | P and G row | S24, Synthetic out-of-range ordinal | Cannot silently select previous/first record or resolve live URL. | None | InvalidNormalizationInput / unresolvable_occurrence. |
| F04 wrong_occurrence_integrity / fatal, conditional owner | P/G/J | S24 checksum or identity variant | Selected bytes inconsistent with immutable pointer; no falsely attributed projection. | None | InvalidNormalizationInput / raw_integrity_mismatch from specific accessor failure. |
| F05 invalid_payload_syntax / fatal, conditional owner | P/J/L decoder families | S25; malformed L variant from L20 after adapter support | Narrow syntax exception translated at owning decoder boundary, cause retained. | None | InvalidNormalizationInput / unparseable_payload, not exposed library error. |
| F06 missing_structural_root / fatal | P/J/G per declared adapter contract | S26; S22 wrong required namespace variant | Missing CFS/publicacio or wrong selected row shape; no fabricated empty procedure. | None | InvalidNormalizationInput / missing_root_or_wrong_shape; unknown coherent schema uses F09. |
| F07 missing_projection / fatal | J-B / selected batch member | S24 pointer /6 on J14 | No root/first-member fallback; include exact requested locator. | None | InvalidNormalizationInput / unresolvable_projection. |
| F08 ambiguous_member_selection / fatal | J-B selector boundary | Real J14 with Synthetic selector 2023/800; S27 selected scalar variant | Reject nonunique business selector if API permits it; scalar is not member object. | None | InvalidNormalizationInput / ambiguous_projection or invalid selection shape; prefer pointer-only API. |
| F09 unsupported_body / fatal | J/L/P dispatch as applicable | S28, Synthetic; unsupported L20 capability separately | Coherent unsupported structure cannot yield validated projection; no false syntax classification. | None | UnsupportedNormalizationInput / unsupported_structure_or_format. |
| F10 unprojectable_batch / fatal | J-B / whole batch | S27 opaque member collection, Synthetic J14 | Batch header cannot become one procedure/member; retain raw for later support. | None in an observation that cannot exist | UnsupportedNormalizationInput / unprojectable_subject. |
| F11 missing_provenance / fatal, conditional owner | All | S24 missing raw ID/source metadata | Cannot construct truthful required normalized envelope; business identifiers irrelevant. | None | InvalidNormalizationInput / missing_provenance if boundary reachable. |
| B01 local_reference_invariant / invariant, defect | All normalized outputs | Fault injection, valid raw H04/H09 | Final validator rejects dangling/mistyped/duplicate keys and invalid Scope; no Issue recovery. | None | NormalizationInvariantError, not caught by expected NormalizationError handler. |
| B02 generated_metadata_invariant / invariant, defect | All | Fault injection, valid raw H01 | Missing mapping version, invalid Money state/object grounding caught; do not blame source. | None | NormalizationInvariantError or configuration failure before mapping, per ownership. |
| B03 unexpected_bug_propagates / invariant, defect | All | Internal sentinel fault, not corrupted raw | KeyError/IndexError/TypeError deliberately propagate; no empty result or source Issue. | None | Original sentinel exception, not translated. |
| B04 storage_error_propagates / invariant, system | Raw-access boundary | Specific accessor stub raises PermissionError | Not confused with domain not-found; no retry/live fetch inside mapper. | None | Original system/accessor infrastructure error. |
| T01 tombstone_no_procurement / edge boundary | P / availability raw kind | Small namespace-correct tombstone, Synthetic documented shape; retained real types in report | ANULADA/CERRADA/unknown type yield no procurement-state observation under approved dispatch; no legal outcome. Compare separate ordinary C06 P ANUL success. | Raw availability diagnostic only if needed | Empty procurement result, not fatal source error; no deletion-detection tests. |
| I00 successful_output_contract / invariant | All supported kinds | All real H/E fixtures and recovered D variants | Apply I01–I25 where relevant; exact raw attribution, meaningful objects, key resolution, no inferred facts. | As baseline/mutation | —; catches violations not visible in single scalar assertions. |
| I26 repeated_mapping_isolation / invariant | P/G/J-B | C04/C09/C19/J14; S29, Real + Synthetic | Normalize independently/repeatedly, no previous-record state, same-version semantic determinism and unchanged raw. | Deterministic by policy | —; not incremental detection/revision logic. |

**Per-adapter coverage obligation:** P, G-O, G-L, G-B, E, J-O, J-B and J-E each need their real happy/edge example, one malformed optional value recovery case, one shape/selection guard reachable through the adopted raw contract, and the common output invariants. Do not limit all degraded/fatal tests to one convenient parser. L support must be explicitly declared minimal/full/unsupported; gated tests are not silently counted as passing coverage. Native P's fixture-selection gate remains visible until closed.

## 12. Fixture and expected-output storage strategy

### 12.1 Recommendation

In the implementation task, add **small, reviewed, committed fixtures under `tests/fixtures/normalization/`**, grouped by PLACSP, Generalitat main/execution, modern publications and legacy publications. This is a proposed location, not a directory created here. Keep C01–C20 case IDs and source occurrence identifiers in fixture names/provenance, not a copy of the entire research corpus.

Use a small provenance record per fixture (or one manifest) containing:

- real versus synthetic label and motivating case/test IDs;
- original repository-relative artifact, acquisition/manifest reference and SHA-256;
- original archive/member/entry ordinal/byte range or page/row ordinal and source ID;
- exact extraction/selection, inherited XML namespace bindings and actual format;
- hash of the committed fixture bytes, separate from original artifact/fragment hash;
- any reduction/reserialization/redaction and why; synthetic base checksum plus one-property mutation recipe;
- approved mapping-version rules needed for expected interpretations (time, codes, URI roles).

Do not invent a historical `observed_at` from mtime or claim the research downloader's ambiguous timing is precise response receipt. A fixture raw wrapper may use a clearly labelled fixed synthetic acquisition context for model tests; that is distinct from a claim about original retrieval time. Source markers remain the real source values. Preserve original research manifest semantics.

### 12.2 Raw realism versus fixture size

| Approach | Benefits | Risks / recommendation |
|---|---|---|
| Direct research snapshot references | Maximum original lineage; useful manual/bulk audit. | Missing in clean checkout; huge ZIP/page dependencies and slow tests. Not default pytest fixtures. Optional local corpus audit may use them later; no new live dependency. |
| Exact XML entry slice + namespace context | Small, real input and original attributes/order/lexical money; existing P samples already available. | Fragments are not standalone XML. Store required inherited namespace context explicitly or use a clearly labelled minimal wrapper copied from the original feed. A wrapper changes fixture hash, not original fragment hash. Do not copy the research unit test's fake `urn:codice` namespace as real evidence. |
| One complete JSON row | Small, realistic main/action mapping with all columns and URL objects. | `gencat-rows.json` is a reserialization, not exact original byte slice. Retain page/ordinal/hash provenance and label derivation. Avoid reducing away procedure money, empty tokens or technical clocks that distinguish semantics. |
| Complete rich body | Correct shared context, grouping, multilingual maps and format; J14 six members is small enough semantically. | Contains unrelated text/contact data and more noise. Prefer full relevant header plus complete relevant nested collections, with documented reduction; at least one unpruned representative per supported structure where practical. Do not remove no-lots/batch flags to make a test easier. |
| Minimal selected rich subtree | Good unit fixture for a narrow helper. | Cannot by itself prove full raw-to-observation boundary or header applicability. Pair with full-body integration fixture; never pretend a selected member subtree is the original complete acquisition. |
| Synthetic in-memory mutation | Small reviewable diff, no proliferation of near-identical huge files. | Must deep-copy; serialization must preserve decimals and realistic types. Use byte/token mutation for lexical-decimal/decoder tests, not float parsing. Manifest/parameter IDs identify synthetic cases. |

Retain enough unrelated valid facts in degraded fixtures to prove recovery locality. A fixture containing only the corrupted field cannot prove that buyer/publication/valid finances survive. A no-lots fixture without the contradictory-looking container cannot test the real trap.

No mock should replace a real body already available. Small test doubles are appropriate only at a raw accessor failure boundary, forbidden cross-record/network access seam, identity generator if needed, or deliberate bug/invariant injection. They should not stub out the actual mapper's conversion/grouping logic.

Contact names/emails and signed-looking export tokens require deliberate fixture review before committing. Prefer no unrelated personal/contact data in newly extracted fixtures. If any values are redacted, record the alteration and distinguish the derived test fixture from byte-exact evidence; keep immutable research originals untouched. Never copy such values into diagnostic goldens merely to prove errors preserve context.

### 12.3 Expected objects

Prefer explicit expected typed fragments/assertions constructed in tests for the contract under examination: Decimal strings, exact identifier tuples, scoped money tuples, publication roles, supplier positions, nulls and issue paths. For the initial representative H fixtures, a small complete expected observation can be useful **after** constructors/serialization/ID rules are adopted.

Do not auto-bless mapper output as golden truth. Golden JSON files for every case would freeze incidental key generation, formatting and unresolved choices, and could conceal scope errors in large diffs. If small reviewed goldens are used:

- serialize Decimal losslessly, represent times/bases explicitly;
- use injected/fixed observation identity or compare it separately until ID policy is settled;
- preserve order for positional/occurrence collections; do not sort away the property being tested;
- compare Issue codes/paths and necessary context, not unstable prose;
- manually justify each field from one raw occurrence and the mapping rule bundle;
- never regenerate expected output from a research extractor or normalize another source to repair the expected object.

### 12.4 Future verification sequence

Follow repository conventions: typed tests in `tests/`, imports from application code under `src/tenderwatch/`, `.venv/bin/python -m pytest` and targeted subsets for iteration. Retain the existing research suite unchanged. It is deterministic and requires no bulk data/services; future live tests remain opt-in. Compile verification uses the existing command in AGENTS, not a new toolchain.

Before fixture commit: verify small fixture provenance/extraction against original evidence where available, then run default tests on only the committed fixtures without access to bulk data. This proves reproducibility in a clean checkout. Research verification scripts are useful optional source audits but **write derived verification outputs**; they are not necessary for a documentation-only change and should not be run here under the one-file-only instruction.

A test-first implementation order is: adopt API/raw/error gates; provenance and primitive/scoped contract checks; real happy examples per enabled adapter; C01–C20 regressions; single-property recovery and fatal guards; common invariants. Do not implement unrelated canonical layers to make normalization tests pass.

## 13. Open decisions and implementation gates

These are explicit limits of the existing evidence, not invitations to invent stronger source guarantees.

| Gate | Decision required before exact tests | Conservative expectation until resolved |
|---|---|---|
| G1 actual raw/model API | Typed models, raw resolver responsibilities, required input metadata, source kind tags, immutable data access, normalization callable/cardinality. No classes exist today. | Test conceptual contract, then place invalid-envelope/decoder cases at the owning layer; no speculative constructor imports. |
| G2 exceptions and zero/multiple outputs | Adopt names/reasons in §8 or a comparably small intentional contract; choose tombstone dispatch and batch atomicity/selected-member failure API. | No silent suppression, no false batch-as-procedure. Invariant bugs not swallowed by expected input failure handling. |
| G3 identifiers and locators | Scheme/namespace strings, exact root marker, qualified XML occurrence paths, composite field/token locators, observation-ID generation. | Preserve original spelling/roles; local keys opaque but unique/resolvable. Do not assert arbitrary key strings or cross-run stable keys before adoption. |
| G4 issue granularity | Path grammar, explicit null/empty handling, one issue per token versus one diagnostic listing paths, unknown scheme/category policy, baseline floating-time diagnostics. | All affected values recoverable; no duplicate noise from unused empty maps; deterministic codes/paths; no exact prose contract. |
| G5 field-specific temporal rules (N Q2) | Whether/how to adopt observed minute projection, Europe/Madrid assumptions, rich UTC calendar serialization and DST handling. C05 nonmidnight award time disproves universal day truncation. | Floating no UTC; ambiguous precision explicitly uncertain. Do not hard-code source IDs to choose precision or consult other records at runtime. A versioned source-field rule needs a documented applicability limit. |
| G6 J19/J20/J14 business-day interpretation | N identifies March 30 rather than UTC March 29 for J19. To assert local_date=March 30, mapper needs adopted field-specific calendar zone rule using only this input plus static rules. | If adopted: day precision, no legal UTC instant, original Z serialization retained, assumed zone explicitly recorded/diagnosed when not documented. Without it: preserve raw, uncertainty, do not assert UTC date as the legal day. Tests must choose one policy, not accept either silently. |
| G7 verified code dictionaries (N Q3/Q6) | Exact PLACSP code-list URI/version compatibility, G numeric code labels, action subtypes beyond modification, source Other semantics and country/unit dictionaries. | Unsupported categories remain source Codes/unmapped. Documented literal labels can map; no bare-number lookup or translation from memory. Tests must distinguish mapping coverage gaps from source invalidity. |
| G8 scope and repeated rich fields (N Q10/Q11) | Bare lotless table facts, no-lots duplicate header/container amounts, association of deadlines/publications to lots versus record subject, supported repeated awarded-project subgroups. | Explicit procedure columns stay procedure; ambiguous lot-column facts record_subject/unknown with issue; repeated monetary facts not summed; root unknowns need no fatal default. |
| G9 supplier alignment and placeholders (N Q9) | Validate positional vector contract and independent grouping on mismatches; exact sentinel policy; unknown identifier scheme representation. | Preserve tokens and paths, unresolved association rather than guessed zip; explicitly observed sentinels flagged, unfamiliar values unvalidated. No UTE constituent splitting. |
| G10 phase-link binding (N Q5) | Exact same-phase pairing rule, distinction between main page and export, guarded target URI recognition, behavior on explicit contradiction. | Preserve independent references and time roles; no attach-all-dates-to-main-link shortcut, no live fetch. |
| G11 documents (N Q8) | Supported role/container mapping, byte-size evidence, opaque delivery route and hash algorithm interpretation. | Exact path/token and reported hash retained; no synthesized download URL/algorithm. Size null if unit unverified, diagnostic only where a supported assertion was attempted. |
| G12 legacy adapter scope (N Q12) | Choose validated minimal legacy projection or explicitly unsupported adapter for the first mapper increment; inspect calendar, lots and monetary owner paths before stronger mappings. | L20 minimal candidate: notice ID at `Notice/com.capgemini.gencat.economia.pscp.entity.PscpContractNotice/contractNoticeId`, number at `Notice/TenderingProcess/diligenceId`, explicit title/description CDATA. `tenderingSpaceId` is source-qualified, not a guessed modern UUID. Do not call valid XML malformed JSON. Full legacy happy-path assertions remain gated, not silently omitted. |
| G13 native P fixture | Select/review a real native occurrence and code/namespace evidence; current case fragments are aggregated only. | H11 remains visible pending fixture review; no claim of comprehensive native normalization from aggregate samples. |
| G14 meaningful projection threshold | Required structural root versus permissible sparse/unresolved subject; selected empty member/body; optional malformed nested objects. | Optional IDs/title/buyer not mandatory; preserve weak defensible subjects. A batch-only header without selectable members cannot stand in for a member. Decide minimal valid selected-object rule before F06/F10 goldens. |
| G15 supported additions beyond examples | Nested P documents, multi-media dates, multiple winning parties in one TR, P modifications, multiple contracts/effective date association, other E action kinds. | Use documented structures and minimal clearly labelled fixtures; retain unknown portions raw/issues. Additional real native/action samples needed before claiming exhaustive mapping coverage. No unsupported full-path mappings invented from local-name resemblance. |

For G15, the initial matrix already covers repeated media and parties synthetically (D19/D20) and real G modifications (H06/H09). Before implementing additional P modification or multi-contract fields, pin the documented qualified paths and a reviewed raw or documentation-derived fixture: modification delta versus final modified total, separate contract IDs/dates, and unlinked StartDate retained as a separate unidentified contract reference with uncertainty rather than copied to every contract. These are bounded normalization extensions already mentioned by N, not permission to construct contract state or history.

### Acceptance checklist for the subsequent test-writing task

- Every enabled input kind has a real reviewed fixture and explicit typed/scoped/null assertions; no mapper is credited with native/legacy support based only on a dispatcher label.
- Every C01–C20 regression is represented as independent raw projection, not a matching/history test.
- All ten initial Issue categories have concrete trigger, path, recovery and raw retention assertions; missing optional fields are tested as non-errors.
- Fatal tests reject only unreachable/unsupported/unprojectable inputs at their actual owning boundary; source ambiguity is not automatically fatal.
- Expected input errors are small and intentional; invariant/program/system failures remain visible.
- Synthetic cases change one relevant property of a known fixture and identify their origin; immutable raw acquisitions remain untouched.
- Shared invariants verify source isolation, no entity resolution, exact values, scope, grouping, local references and no fabricated completeness.
- Default pytest requires neither live services nor bulk research data. No tests/mappers/schemas/fixtures are implemented by this document.

## 14. Executable test contract (test-first update)

**Current implementation status:** `tenderwatch.normalization` now implements the public API below. The original contract tests, fixtures, assertions, and harness are unchanged; the existing harness imports the real package and no longer applies absent-module expected failures. `--runxfail` now runs successfully against the implementation. Additional implementation-edge and inspection-workflow tests cover reviewed lifecycle labels, XML annotations, distinct display titles, explicit result decision dates, conservative unsupported multi-project result grouping, cached resolution, serialization, and CLI behavior. The remaining mapping gates in §14.3 remain bounded limitations, not claims of exhaustive source coverage. README documents the disposable normalized-output command. The following test-first status paragraphs are retained as historical context, not the current implementation status.

**Implementation update, 23 September 2026:** the historical repository-state descriptions above predate the raw-reader implementation. `RawSourceRecord` and retained-data readers now exist. The executable tests are under `tests/normalization/`; normalization functions and the production `NormalizedObservation` model still do **not** exist. This section records the contract selected for the next implementation, not a claim that normalization has passed.

The user explicitly selected **expected failures while the API is absent**, rather than leaving the repository's default suite red. The collection hook only marks tests that request the normalization API fixture, only when `tenderwatch.normalization` is absent, and only for a dedicated `MissingNormalizationImplementation` exception (`strict=True`). Once a module exists, missing exports, internal import failures, assertion failures, and mapper errors fail normally. There are no fake normalizers, unconditional xfails, or replacement observation models. Executable fixture and harness checks run even before the API exists.

### 14.1 Public API selected by the tests

The future module `tenderwatch.normalization` is expected to export:

```text
normalize(raw: RawSourceRecord, *, resolve, projection: str | None = None)
    -> tuple[NormalizedObservation, ...]

validate_observation(observation: NormalizedObservation) -> None

NormalizedObservation
SCHEMA_VERSION
MAPPING_VERSION
NormalizationError
InvalidNormalizationInput
UnsupportedNormalizationInput
NormalizationInvariantError
```

`resolve` is a small callable taking the raw `ContentReference` and returning the selected JSON object or XML element. For local artifacts, callers can supply `functools.partial(tenderwatch.sources.artifacts.load_record, root)`. It is an explicit raw-access boundary, not a service container or acquisition interface. Tests exercise the real readers, `to_raw`, and resolver; doubles are confined to resolver failures and test-harness checks. The normalizer must not resolve another occurrence, fetch links, open research indexes, or look up companion rows/bodies. Both raw artifact/envelope and resolver-returned parsed views must remain unchanged, including when normalization raises.

The public dispatcher keeps callers independent of internal adapter names. The three core routes are PLACSP Atom entries, Generalitat `ybgg-dgi6` main rows, and Generalitat `8idu-wkjv` execution rows. Modern rich bodies need a separate adapter; tombstones and unsupported legacy bodies have explicit dispatch contracts. Internal function/module organization is not dictated by the tests.

- Ordinary selected records return a one-element tuple; tombstones return `()`.
- `projection=None` automatically selects an ordinary root or enumerates all explicit rich batch members in source order.
- The observation's root marker is `$`. Batch projections use exact `/publicacio/dadesPublicacio/contractesAgregada/{index}` pointers. Arbitrary body subtrees and noncanonical/negative/out-of-range array indices are not subject selectors.
- Whole-batch enumeration is atomic on a fatal member-shape/selection failure. Explicit selection of a valid sibling remains supported. A recoverable bad monetary token does not abort batch enumeration.
- Empty main/execution objects have no defensible procurement subject and raise `UnsupportedNormalizationInput(reason='unprojectable_subject')`; this does not make ordinary missing optional fields fatal.
- Observation models are frozen dataclasses with the fields in N §16 and immutable tuple collections. Decimal, `datetime.date`, `datetime.time`, UTC-aware `datetime.datetime`, and `datetime.timedelta` represent the corresponding typed values. No binary-float money, mutable nested payloads, or canonical/query fields.
- Schema/mapping versions are nonempty module constants, independent of source `versio`. Observation IDs are deterministic for the same raw/projection/version and distinguish different raw occurrences even when source ID and source clock are equal. The digest algorithm and opaque local-key spelling are deliberately not pinned. Identifier namespaces remain source/context qualified; a record-local qualifier can include the full raw-record ID. Semantic mutation comparisons replace that literal qualifier with a placeholder, without changing source identifier values.
- `validate_observation` owns generated-output invariant checks. Its defect exception is separate from expected normalization failures. Ordinary upstream field errors remain Issues, not validator failures.

### 14.2 Paths, diagnostics, and conservative mapping decisions

| Decision | Executable expectation |
|---|---|
| JSON source paths | RFC 6901 pointers relative to the selected row or complete rich body. `$` denotes the selected raw root, not a whole acquired table page. |
| XML source paths | ElementTree-compatible paths relative to the entry, e.g. `./{URI}ContractFolderStatus/{URI}ProcurementProject/...`; repeated occurrences use one-based `[n]`. Namespace URIs, not prefixes, identify elements. |
| Composite paths | `paths:` followed by a JSON array of source paths, preserving field order. |
| Supplier token paths | Append `#token={zero_based_index}` to an original vector-field pointer. Scalar fields use their ordinary pointer; explicit `\|\|` vectors retain empty positions. |
| Issue paths | `raw:` plus the affected path/token/composite locator. Assertions pin codes and paths, not human message prose. Tokenized export URLs must not be copied into diagnostic details. |
| Baselines | Happy fixtures may contain the documented scope/time/placeholder/unmapped diagnostics. Tests assert required diagnostics and forbidden ones where specified, not globally empty issues. One-property recovery tests compare unaffected fields with the independently normalized base and require the new field-specific diagnostic. Exhaustive full-observation issue goldens remain deferred; no mapper output has been auto-blessed as an oracle. |
| Missing/empty/null money | Missing means no Money. Empty string or explicit JSON null means `explicit_empty`; raw null token is the string `null`, not Python `None`. Valid zero stays Decimal zero. Nonfinite strings are invalid Money, not valid numeric values. |
| Estimate tax basis | Generalitat metadata explicitly defines both `valor_estimat_*` columns as excluding IVA; procedure versus lot/member scope remains separate. PLACSP's retained syndication §4.4 defines EstimatedOverallContractAmount by Directive 2004/18/EC Article 9, whose net-of-VAT definition supports excluded tax basis. No VAT rate is calculated from amounts. |
| Floating times | Preserve local components, no UTC instant, no inferred Madrid zone. C05's nonmidnight award time is retained with uncertainty. No universal observed-minute rule is imposed from C13. |
| Rich calendar serialization | The J19 action-date test deliberately adopts the conservative **raw-only unresolved business day** policy: original serialized value retained, no local business day or legal UTC instant asserted, `ambiguous_time`. A future reviewed calendar-zone rule requires an explicit contract/version update, not accepting either answer silently. Publication and submission timestamps with explicit offsets remain instants. |
| Scope | Main-row lot columns without lot evidence stay `record_subject` with `uncertain_scope`; explicit procedure columns remain procedure-scoped. No-lots rich header/container money is retained as separate source-located assertions, never summed. Missing multi-lot result references use unknown scope; ambiguous/unembedded explicit lot references remain source-only. |
| Vocabulary coverage | Pin the researched PLACSP lifecycle and reviewed result subset (including TenderResultCode-2.09 `5`/`9`) and documented Generalitat labels. Unknown source values/list versions remain unmapped. Complete numeric contract/method/action dictionaries are not implied by this suite. |
| Supplier schemes/placeholders | Missing scheme does not become NIF from spelling. Unknown supplied scheme produces an unmapped-code diagnostic. Both observed DIR3 sentinel spellings are placeholders. Misaligned amount vectors retain all positions with unresolved, party-free amount allocations; an independently compatible vector survives. |
| Phase association | All ten date fields are tested. Bind only to the named same-phase export; missing export does not cause fallback to the main page URL. Date-only and export-only references remain meaningful. |
| Documents | Preserve actual URLs or opaque paths as supplied, with unknown hash algorithm unless explicit. Rich `mida` remains raw and `reported_size_bytes=None` pending a reviewed unit rule. No size-based golden or negative-size mapping test claims that unresolved unit gate is closed. |
| Legacy | First-increment capability is explicitly unsupported: valid legacy XML raises `UnsupportedNormalizationInput(reason='unsupported_structure_or_format')`, not a JSON syntax error. Positive legacy financial/lot/calendar tests remain gated on the focused field review in G12. |
| Optional action shape | No typed-container fallback is adopted for a structurally unusable J19 action type: omit that action with `unsupported_structure`, preserving its valid sibling and independent award/tender facts. |

The estimate definition used above is available in the retained `data/analysis/documentation/syndication-current.txt` (§4.4) and [Directive 2004/18/EC, Article 9(1)](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX%3A32004L0018). Tests make no live request for these definitions.

### 14.3 Executable coverage and fixture provenance

| Test file | Coverage |
|---|---|
| `test_core.py` | P/G-O/G-L/G-B/E envelopes and happy projections; typed money/scopes, phase versus lifecycle, clocks, lots, supplier tokens, absence and determinism. |
| `test_publications.py` | Modern ordinary, six-member batch, execution and six-lot bodies; corrections, no-lots containers, source document metadata, sibling isolation, conflicts and optional-subtree recovery. |
| `test_regressions.py` | Independent C01–C20 regression projections in conjunction with core/publication tests: evolving assertions, renamed numbers, many lots, annulment, negative results/retained awards, multiple IDs/buyers, partial inventories, precision/notice targets, collisions and explicit zeros. Includes reviewed native evidence. |
| `test_recovery.py` | Bad/empty/null/zero/nonfinite/exact decimals, unknown codes/schemes/currency, invalid/floating times, supplier alignment, conflicting booleans, invalid URLs/CPVs, partial deadlines, taxonomy and optional absence. |
| `test_publication_dates.py` | All ten named phase-date families, nine same-phase export pairings, and independent missing date/export cases. Unrepresented phase combinations are explicitly synthetic. |
| `test_failures.py` | Reachable locator/integrity/decoder integration failures, missing P root, batch selection/atomicity, missing provenance, legacy capability, invariant validation and visible system/program errors; tombstone dispatch. |
| `test_additional_invariants.py` | Namespace URI/prefix distinction, repeated media dates, duration units, multiple VAT, exact identifier spelling, projection guards, guarded URL identity extraction, same-ID/same-clock raw isolation. |
| `test_fixtures.py`, `test_harness.py` | Active checks of every committed fixture, exact fragment hashes, decimal-safe one-property mutations, source-path helpers, optional original-evidence audit, and narrow xfail behavior. |

`support.py` is test-only: it creates actual raw records through the existing readers, makes independent temporary mutation artifacts, checks shared output invariants, and compares semantics while treating local keys as opaque. It contains no normalization implementation or expected-output generator based on research mappers. Catalog-to-XML packing only reconstructs the explicitly reviewed input paths/attributes; its output is audited against original XML, never used to calculate normalized expectations.

Small source-derived fixtures are under `tests/fixtures/normalization/`, with existing raw-layer fixtures reused where suitable:

- **Exact P entries:** `C01-P000.xml.fragment` and `C07-P001.xml.fragment`, copied unchanged with SHA-256 checks. C01 originates in aggregated 2026 member `PlataformasAgregadasSinMenores_20260812_030033.atom`, ordinal 451, bytes `[5324381,5332091)`. C07 originates in `PlataformasAgregadasSinMenores_20260224_040120.atom`, ordinal 453, bytes `[4896231,4906084)`. The fixture packer adds the retained Atom namespace wrapper; it does not claim the wrapper is an original feed page.
- **Other P regressions:** `placsp-regressions.json` records each original fragment path and retained raw field paths, values, lot order and result order. The generated XML is a deliberately reduced/reformatted input, not byte-exact evidence. Unlisted titles, documents, suppliers, money and other subtrees are omitted; tests do not claim full-field coverage of those original entries. The 13/25-lot and eight-result occurrence counts remain intact where tested. Each original fragment's acquisition/member/ordinal/byte range is available through its neighboring `evidence.json` and the retained acquisition ledger.
- **Native P:** `P-native.xml.fragment` is a reviewed reduction of entry ordinal 1 of the retained `data/raw/placsp/probes/native-head.atom`, Atom ID ending `20479849`. It preserves buyer NIF, explicit net/gross/estimated money, separate CPVs/deadline roles, one nested document reference and both notice occurrences. Contact/hierarchy/qualification material and other attachments are omitted. This is real native evidence, not an aggregated fixture with its dataset tag changed; it is bounded native coverage, not an exhaustive native oracle.
- **Main rows:** `main-cases.json` and `main-regressions.json` record original sample paths, exact Socrata selectors, retained row objects and explicit reduction notes. Their original page/row locators are in the neighboring case evidence. They are reserialized selected-field excerpts, not exact acquired page bytes. Supplier amounts, positions and relevant scope flags are retained in the cases that assert them. Supplier personal identity is omitted from the C15 amount/duplicate-lot excerpts.
- **Modern rich reductions:** J01 from `phases/300885987.json`, J14 from `phases/300339416.json`, J19 from `phases/300007312.json`, J20 from `phases/300641893.json`. Body envelope, shared applicable header and source paths remain in place. J14 retains all six members; J19 both modifications plus independent award facts; J20 all six ordered lots and all eight contractor occurrences. Contact information and unrelated detail are omitted. J01 retains the administrative/technical document collections only, so its expected document count is two, not a claim that the original contains only two. Other omitted scalar fields and subtrees are visible by comparison with the originals.
- **Unpruned/previous fixtures:** C01 main row, the execution probe including C19 E0/E1, C01 P002/tombstone, and the full J16 body reuse existing committed fixtures with provenance in `docs/RAW_SOURCE_RECORDS.md`. L07 reuses the explicitly labelled legacy XML excerpt for the unsupported-capability contract only.

Each temporary raw artifact has its own computed SHA-256, record locator and raw identity. XML mutation recipes retain the base document hash and target path; JSON recipes additionally record replacement/deletion. Fixture acquisition time remains unknown rather than inventing historical receipt metadata. Original acquisition hashes remain in `data/raw/download_manifest.jsonl`; reduced copies are never presented as having those original hashes. The optional audit compares every retained JSON field and ordered array, XML field/attribute/repetition, and exact P fragment against the named originals. No research acquisition or analysis index is rewritten.

**Remaining bounded gates:** F01's future routing family cannot be constructed as a valid member of today's closed `RecordKind` enum, and F02's absent content violates the typed raw contract; the suite does not forge such objects to manufacture coverage. Wrong JSON row envelopes and modern bodies without `publicacio` are already rejected by the readers, so their decoder/root ownership stays there rather than duplicating imaginary mapper states. Full legacy support, comprehensive source dictionaries, additional PLACSP modification/multi-contract/effective-date mappings, publisher-backed rich calendar rules, and verified document size units still require the focused reviews described above. The suite covers the central regression of each C01–C20 case, not every field and every occurrence in the full research corpus.

### 14.4 Running this test-first stage

From the repository root:

```bash
.venv/bin/python -m pytest -q -r fE
.venv/bin/python -m pytest tests/normalization -q -r fE
.venv/bin/python -m pytest tests/normalization --runxfail -x
.venv/bin/python -m pytest tests/normalization/test_fixtures.py --audit-normalization-evidence -q
.venv/bin/python -m compileall -q src tests research/scripts
```

The `--runxfail` command intentionally exposes the missing API as a failure for TDD. Do not interpret pending xfails as successful mapping tests. The audit command is optional and requires local retained originals; specify the test path as shown so pytest loads its scoped option. Default tests use only committed fixtures and temporary artifacts, with research-file reads, SQLite connections and network calls forbidden inside the normalization suite (except the explicitly selected provenance audit). The normalizer remains a separate implementation task.
