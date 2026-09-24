from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from tenderwatch.normalization.models import (
    Award, Classification, Coverage, Deadline, ExecutionAction, Identifier, Issue,
    LocalizedText, Location, Lot, MappedCode, Money, Outcome, Party, PerformancePeriod, ProcurementAttribute,
    PublicationReference, RelatedIdentifier, SourceDocumentReference, SourceReference, Status,
)

T = TypeVar('T')


@dataclass(frozen=True, slots=True, order=True)
class ProcedureIdentity:
    scheme: str
    namespace: str
    value: str


@dataclass(frozen=True, slots=True)
class ResolutionEvidence:
    rule: str
    identifier: ProcedureIdentity
    observation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UnresolvedObservation:
    observation_id: str
    reason: str
    identifiers: tuple[ProcedureIdentity, ...]


@dataclass(frozen=True, slots=True, order=True)
class EvidenceRef:
    observation_id: str
    normalized_path: str


@dataclass(frozen=True, slots=True)
class FactScope:
    kind: str = 'procedure'
    observation_id: str | None = None
    lot_keys: tuple[str, ...] = ()
    source_lot_identifiers: tuple[Identifier, ...] = ()


@dataclass(frozen=True, slots=True)
class Candidate(Generic[T]):
    candidate_id: str
    value: T
    evidence: tuple[EvidenceRef, ...]


@dataclass(frozen=True, slots=True)
class ReconciledFact(Generic[T]):
    fact_id: str
    scope: FactScope
    candidates: tuple[Candidate[T], ...]
    selected_candidate_id: str | None
    rule: str

    @property
    def value(self) -> T | None:
        return next((candidate.value for candidate in self.candidates if candidate.candidate_id == self.selected_candidate_id), None)


@dataclass(frozen=True, slots=True)
class Occurrence(Generic[T]):
    observation_id: str
    normalized_path: str
    value: T


@dataclass(frozen=True, slots=True)
class ReconciliationConflict:
    fact_id: str
    field: str
    candidate_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    reason: str = 'competing_values_without_safe_ordering'


@dataclass(frozen=True, slots=True, kw_only=True)
class CurrentState:
    identifiers: tuple[ReconciledFact[Identifier], ...] = ()
    procedure_numbers: tuple[ReconciledFact[Identifier], ...] = ()
    related_identifiers: tuple[ReconciledFact[RelatedIdentifier], ...] = ()
    titles: tuple[ReconciledFact[LocalizedText], ...] = ()
    descriptions: tuple[ReconciledFact[LocalizedText], ...] = ()
    buyer: ReconciledFact[Party] | None = None
    contract_type: ReconciledFact[MappedCode] | None = None
    mixed_contract: ReconciledFact[bool] | None = None
    procurement_method: ReconciledFact[MappedCode] | None = None
    procurement_attributes: tuple[ReconciledFact[ProcurementAttribute], ...] = ()
    classifications: tuple[ReconciledFact[Classification], ...] = ()
    financials: tuple[ReconciledFact[Money], ...] = ()
    deadlines: tuple[ReconciledFact[Deadline], ...] = ()
    statuses: tuple[ReconciledFact[Status], ...] = ()
    execution_locations: tuple[ReconciledFact[Location], ...] = ()
    performance_periods: tuple[ReconciledFact[PerformancePeriod], ...] = ()
    lots: tuple[Occurrence[Lot], ...] = ()
    publications: tuple[Occurrence[PublicationReference], ...] = ()
    outcomes: tuple[Occurrence[Outcome], ...] = ()
    awards: tuple[Occurrence[Award], ...] = ()
    execution_actions: tuple[Occurrence[ExecutionAction], ...] = ()
    documents: tuple[Occurrence[SourceDocumentReference], ...] = ()
    source_references: tuple[Occurrence[SourceReference], ...] = ()
    coverage: tuple[Occurrence[Coverage], ...] = ()
    issues: tuple[Occurrence[Issue], ...] = ()


@dataclass(frozen=True, slots=True)
class CanonicalObservation:
    canonical_id: str
    normalized_observation_ids: tuple[str, ...]
    current_state: CurrentState
    conflicts: tuple[ReconciliationConflict, ...]
    resolution_provenance: tuple[ResolutionEvidence, ...]


@dataclass(frozen=True, slots=True)
class CanonicalizationResult:
    canonical_observations: tuple[CanonicalObservation, ...]
    unresolved_observations: tuple[UnresolvedObservation, ...]
