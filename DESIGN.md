# TenderWatch Canonical Explorer

## Purpose

Build a small, read-only web interface for exploring the published canonical observations in `data/CanonicalObservations/canonical.jsonl`.

The first version follows the editorial, search-first feel of [Cato](https://www.get-cato.com/en): dark navy navigation, warm light surfaces, oversized typography, restrained coral accents, and clear tender cards. It borrows the interaction pattern, not Cato's branding or copy.

## MVP Scope

- Search procedure titles and descriptions.
- Filter by deadline, publication date, status, contract type, procurement method, buyer, CPV, budget, and conflicts.
- Sort and paginate filtered results.
- Open a canonical observation on a dedicated detail view.
- Show selected values, alternatives, conflicts, source evidence, publications, lots, awards, actions, and documents.
- Keep the interface read-only. No mutation, reconciliation, or AI decisions are performed in the browser.

## Data Boundary

The current published JSONL is the source of truth. The web layer loads it into an in-memory search catalog at startup. The catalog uses a flattened search projection for cards and filters while retaining the complete canonical object for detail views.

```text
data/CanonicalObservations/canonical.jsonl
        -> web catalog
        -> filtered, sorted, paginated cards
        -> canonical detail view
```

The application must resolve `data/ProcessingRuns/current` once before loading both canonical data and run metadata. It must never combine files from different processing runs.

## Information Architecture

### Explorer

The root page is the primary product surface:

1. Compact navigation header with TenderWatch identity and a small data-status indicator.
2. Editorial hero with the value proposition and a prominent search field.
3. Filter panel below the hero. On mobile, filters collapse into a drawer.
4. Result count and active-filter summary.
5. Responsive grid of compact canonical cards.
6. Pagination after filtering and sorting.

Filtering always happens before pagination. Query state is represented in the URL so searches can be bookmarked and the browser back button restores the previous result page.

### Detail

Each card links to a dedicated canonical detail view using its `canonical_id`. The detail view is not a large modal because canonical objects can contain many evidence-backed sections.

The detail page contains:

- Back link preserving the explorer query.
- Title, buyer, status, budget, deadline, and source summary.
- Overview and classifications.
- Lots, publications, outcomes, awards, execution actions, and documents.
- Reconciliation and evidence section.
- Conflicts and alternative candidates shown explicitly rather than hidden.

## Card Content

Cards show only information useful for deciding whether to open a tender:

- Title and short description.
- Buyer.
- Primary procedure number or source identifier.
- Contract type and procurement method.
- Budget or estimated value.
- Submission deadline.
- Publication date.
- Lot count.
- Source badges.
- Conflict or unresolved-value badge when applicable.

Cards should never imply that a missing value means zero, no lots, cancellation, or legal closure.

## Reconciliation Presentation

The UI must distinguish:

- **Selected value:** displayed as the current reconciled value.
- **Alternative candidates:** displayed behind an expandable evidence control.
- **Unresolved conflict:** displayed with a warning treatment and all competing candidates.
- **Occurrence data:** lots, publications, awards, actions, and documents remain source-qualified occurrences and are not presented as silently deduplicated facts.

Every candidate and conflict should be traceable to an observation ID and normalized path. The UI should expose the reconciliation rule but should not invent confidence scores or chronology that are not present in the canonical output.

## Visual Direction

- Palette: deep navy shell, warm ivory page background, near-black text, coral/orange action accent, muted blue-green secondary accent.
- Typography: expressive large display headings paired with a highly readable sans-serif body.
- Layout: generous whitespace, rounded cards, thin borders, subtle shadows, strong section rhythm.
- Interaction: clear primary actions, quiet secondary controls, visible hover and focus states.
- Tone: confident, useful, and calm rather than dashboard-heavy.
- Responsive behavior: single-column cards and a filter drawer on narrow screens; multi-column cards and persistent filters on wide screens.

Do not reproduce Cato's logos, illustrations, proprietary wording, or exact page layout.

## Query Behavior

The MVP query state uses URL parameters:

```text
q
page
page_size
sort
deadline_from
deadline_to
publication_from
publication_to
buyer
status
contract_type
procurement_method
cpv
min_budget
max_budget
has_conflicts
```

Changing a filter resets `page` to `1`. Pagination preserves every active filter. The default page size is small enough for scanning and can be changed later without changing the data contract.

## Empty and Error States

- Empty dataset: explain that no canonical publication is available.
- No matches: show the active filters and a clear reset action.
- Missing field: display an em dash and a semantic label such as “Not reported,” not a guessed value.
- Conflicts: keep the tender visible and make the conflict inspectable.
- Invalid or unavailable current run: show a non-destructive data-unavailable state rather than serving mixed or stale files.

## Accessibility

- Semantic headings and landmarks.
- Labels for every filter.
- Keyboard-accessible cards, pagination, disclosure controls, and filter drawer.
- Visible focus rings.
- Color is never the only conflict or status signal.
- Respect reduced-motion preferences.
- Dates and amounts use text alternatives where formatting alone may be ambiguous.

## Implementation Phases

### Phase 1: Read-only explorer

- Standard-library server and static browser assets.
- In-memory catalog from the current canonical JSONL.
- Search, filters, sort, pagination, and detail route.
- No database and no new runtime dependency.

### Phase 2: Evidence refinement

- Better field-specific formatting.
- More explicit candidate and conflict inspection.
- Source links and normalized observation drill-down.

### Deferred

- Authentication and saved searches.
- Notifications.
- Database persistence or FTS indexing.
- Canonical mutation or manual reconciliation.
- Fuzzy matching or model-generated decisions.
- Historical canonical revisions and legal-state reconstruction.
