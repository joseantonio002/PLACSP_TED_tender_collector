from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Generic, TypeVar


@dataclass(frozen=True, slots=True)
class LocalizedText:
    text: str
    language: str | None = None
    source_role: str | None = None


@dataclass(frozen=True, slots=True)
class Identifier:
    scheme: str
    namespace: str
    value: str
    role: str
    usability: str = 'unvalidated'


@dataclass(frozen=True, slots=True)
class RelatedIdentifier:
    identifier: Identifier
    relation: str = 'related_unspecified'


@dataclass(frozen=True, slots=True)
class Code:
    system: str
    value: str
    version: str | None = None
    labels: tuple[LocalizedText, ...] = ()


@dataclass(frozen=True, slots=True)
class MappedCode:
    source: Code
    normalized: str | None
    mapping: str


@dataclass(frozen=True, slots=True)
class Scope:
    kind: str
    lot_keys: tuple[str, ...] = ()
    source_lot_identifiers: tuple[Identifier, ...] = ()


T = TypeVar('T')


@dataclass(frozen=True, slots=True)
class Scoped(Generic[T]):
    source_path: str
    scope: Scope
    value: T


@dataclass(frozen=True, slots=True)
class TemporalValue:
    raw: str
    local_date: date | None = None
    local_time: time | None = None
    utc_instant: datetime | None = None
    offset: timedelta | None = None
    zone: str | None = None
    zone_basis: str = 'unknown'
    precision: str = 'unknown'
    precision_basis: str = 'lexical_only'


@dataclass(frozen=True, slots=True)
class SourceMarker:
    kind: str
    at: TemporalValue


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    system: str
    dataset: str
    record_kind: str
    record_identifiers: tuple[Identifier, ...] = ()
    origin_platform: Code | None = None


@dataclass(frozen=True, slots=True)
class Location:
    names: tuple[LocalizedText, ...] = ()
    nuts_code: str | None = None
    nuts_version: str | None = None
    country_code: str | None = None
    locality: str | None = None
    postal_code: str | None = None
    address: str | None = None


@dataclass(frozen=True, slots=True)
class Party:
    kind: str = 'unknown'
    identifiers: tuple[Identifier, ...] = ()
    names: tuple[LocalizedText, ...] = ()
    addresses: tuple[Location, ...] = ()


@dataclass(frozen=True, slots=True)
class ProcurementAttribute:
    kind: str
    value: Code


@dataclass(frozen=True, slots=True)
class Status:
    source_path: str
    scope: Scope
    dimension: str
    value: MappedCode


@dataclass(frozen=True, slots=True)
class Classification:
    raw_code: str
    code: str | None = None
    check_digit: str | None = None
    system: str = 'CPV'
    source_system: str | None = None
    version: str | None = None
    role: str = 'unspecified'


@dataclass(frozen=True, slots=True)
class Money:
    purpose: str
    value: Decimal | None
    raw_value: str
    value_state: str
    currency: str | None = None
    tax_basis: str = 'unspecified'
    vat_rate: Decimal | None = None
    multiple_vat_rates: bool | None = None


@dataclass(frozen=True, slots=True)
class Deadline:
    kind: str
    at: TemporalValue | None = None
    notes: tuple[LocalizedText, ...] = ()


@dataclass(frozen=True, slots=True)
class DurationPart:
    value: Decimal
    unit: str


@dataclass(frozen=True, slots=True)
class PerformancePeriod:
    kind: str = 'planned'
    raw_text: tuple[LocalizedText, ...] = ()
    start_at: TemporalValue | None = None
    end_at: TemporalValue | None = None
    duration: tuple[DurationPart, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class Item:
    key: str
    source_path: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Lot(Item):
    identifiers: tuple[Identifier, ...] = ()
    number: str | None = None
    titles: tuple[LocalizedText, ...] = ()
    descriptions: tuple[LocalizedText, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceRelation:
    kind: str
    target_identifiers: tuple[Identifier, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicationReference(Item):
    scope: Scope
    identifiers: tuple[Identifier, ...] = ()
    type: MappedCode | None = None
    medium: str | None = None
    publication_at: TemporalValue | None = None
    planned_publication_at: TemporalValue | None = None
    sent_at: TemporalValue | None = None
    is_correction: bool | None = None
    correction_type: tuple[LocalizedText, ...] = ()
    correction_reason: tuple[LocalizedText, ...] = ()
    relations: tuple[SourceRelation, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class Outcome(Item):
    scope: Scope
    result: MappedCode
    decision_at: TemporalValue | None = None
    reasons: tuple[LocalizedText, ...] = ()
    publication_keys: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class SupplierAllocation(Item):
    source_position: int | None = None
    party: Party | None = None
    amounts: tuple[Money, ...] = ()
    alignment: str = 'structured'


@dataclass(frozen=True, slots=True)
class ContractReference:
    source_path: str
    identifiers: tuple[Identifier, ...] = ()
    formalized_at: TemporalValue | None = None
    effective_at: TemporalValue | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Award(Item):
    scope: Scope
    grouping: str
    identifiers: tuple[Identifier, ...] = ()
    decision_at: TemporalValue | None = None
    amounts: tuple[Money, ...] = ()
    suppliers: tuple[SupplierAllocation, ...] = ()
    contract_references: tuple[ContractReference, ...] = ()
    outcome_keys: tuple[str, ...] = ()
    publication_keys: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionAction(Item):
    scope: Scope
    type: MappedCode
    identifiers: tuple[Identifier, ...] = ()
    contract_identifiers: tuple[Identifier, ...] = ()
    titles: tuple[LocalizedText, ...] = ()
    action_at: TemporalValue | None = None
    end_at: TemporalValue | None = None
    amounts: tuple[Money, ...] = ()
    parties: tuple[Party, ...] = ()
    details: tuple[LocalizedText, ...] = ()
    publication_keys: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReportedHash:
    value: str
    algorithm: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceDocumentReference(Item):
    scope: Scope
    identifiers: tuple[Identifier, ...] = ()
    role: MappedCode | None = None
    titles: tuple[LocalizedText, ...] = ()
    language: str | None = None
    urls: tuple[str, ...] = ()
    source_path_token: str | None = None
    reported_hash: ReportedHash | None = None
    reported_size_bytes: int | None = None
    declared_media_type: str | None = None
    publication_keys: tuple[str, ...] = ()
    relations: tuple[SourceRelation, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceReference(Item):
    url: str
    target_kind: str
    identifiers: tuple[Identifier, ...] = ()
    publication_keys: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Coverage:
    path: str
    scope: Scope
    state: str
    basis: str


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    path: str
    detail: str


@dataclass(frozen=True, slots=True, kw_only=True)
class NormalizedObservation:
    observation_id: str
    raw_source_record_id: str
    projection_locator: str
    schema_version: str
    mapping_version: str
    source: SourceMetadata
    subject_kind: str
    focus: Scope
    source_markers: tuple[SourceMarker, ...] = ()
    procedure_identifiers: tuple[Identifier, ...] = ()
    procedure_numbers: tuple[Identifier, ...] = ()
    batch_identifiers: tuple[Identifier, ...] = ()
    member_identifiers: tuple[Identifier, ...] = ()
    related_identifiers: tuple[RelatedIdentifier, ...] = ()
    titles: tuple[LocalizedText, ...] = ()
    descriptions: tuple[LocalizedText, ...] = ()
    buyer: Party | None = None
    contract_type: MappedCode | None = None
    mixed_contract: bool | None = None
    procurement_method: MappedCode | None = None
    procurement_attributes: tuple[ProcurementAttribute, ...] = ()
    statuses: tuple[Status, ...] = ()
    classifications: tuple[Scoped[Classification], ...] = ()
    financials: tuple[Scoped[Money], ...] = ()
    deadlines: tuple[Scoped[Deadline], ...] = ()
    execution_locations: tuple[Scoped[Location], ...] = ()
    performance_periods: tuple[Scoped[PerformancePeriod], ...] = ()
    lots: tuple[Lot, ...] = ()
    publications: tuple[PublicationReference, ...] = ()
    outcomes: tuple[Outcome, ...] = ()
    awards: tuple[Award, ...] = ()
    execution_actions: tuple[ExecutionAction, ...] = ()
    documents: tuple[SourceDocumentReference, ...] = ()
    source_references: tuple[SourceReference, ...] = ()
    coverage: tuple[Coverage, ...] = ()
    issues: tuple[Issue, ...] = ()
