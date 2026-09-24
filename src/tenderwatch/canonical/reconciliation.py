from __future__ import annotations

from collections import defaultdict
from dataclasses import fields, is_dataclass
from decimal import Decimal
import hashlib
from typing import Any

from tenderwatch.normalization.models import (
    Classification, Code, Deadline, MappedCode, Money, NormalizedObservation, Scope, TemporalValue,
)
from tenderwatch.serialization import serialize
from .models import (
    Candidate, CanonicalObservation, CurrentState, EvidenceRef, FactScope, Occurrence,
    ProcedureIdentity, ReconciledFact, ReconciliationConflict, ResolutionEvidence,
)
from .resolution import identity_record

SINGLETONS = ('buyer', 'contract_type', 'mixed_contract', 'procurement_method')
OCCURRENCES = ('lots', 'publications', 'outcomes', 'awards', 'execution_actions', 'documents', 'source_references', 'coverage', 'issues')


def _decimal_key(value: Decimal) -> str:
    text = format(value, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def semantic_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return _decimal_key(value) if value else '0'
    if isinstance(value, MappedCode) and value.normalized is not None:
        return {'normalized': value.normalized}
    if isinstance(value, Code):
        return {'system': value.system, 'version': value.version, 'value': value.value}
    if is_dataclass(value):
        omit = {'source_path'}
        if isinstance(value, Money) and value.value_state == 'valid':
            omit.add('raw_value')
        if isinstance(value, TemporalValue) and (value.local_date is not None or value.local_time is not None):
            omit.add('raw')
        return {field.name: semantic_value(getattr(value, field.name)) for field in fields(value) if field.name not in omit}
    if isinstance(value, tuple):
        return tuple(semantic_value(item) for item in value)
    return value


def valid_value(value: Any) -> bool:
    if isinstance(value, Money):
        return value.value_state == 'valid'
    if isinstance(value, MappedCode):
        return value.normalized is not None
    if isinstance(value, Classification):
        return value.code is not None
    if isinstance(value, Deadline):
        return bool(value.notes or value.at and (value.at.local_date is not None or value.at.local_time is not None))
    return True


def fact_scope(observation: NormalizedObservation, scope: Scope) -> FactScope:
    return FactScope(scope.kind, None if scope.kind == 'procedure' else observation.observation_id,
                     scope.lot_keys, scope.source_lot_identifiers)


class _CandidateBuilder:
    def __init__(self, value: Any) -> None:
        self.value = value
        self.serialized = serialize(value)
        self.evidence: set[EvidenceRef] = set()

    def add(self, value: Any, evidence: EvidenceRef) -> None:
        encoded = serialize(value)
        if encoded < self.serialized:
            self.value, self.serialized = value, encoded
        self.evidence.add(evidence)


class _FactBuilder:
    def __init__(self, field: str, slot: Any, scope: FactScope) -> None:
        self.field = field
        self.scope = scope
        self.fact_id = 'fact:v1:' + hashlib.sha256(serialize((field, slot, scope)).encode()).hexdigest()
        self.candidates: dict[str, _CandidateBuilder] = {}

    def add(self, value: Any, evidence: EvidenceRef) -> None:
        comparison = serialize(semantic_value(value))
        candidate = self.candidates.get(comparison)
        if candidate is None:
            candidate = self.candidates[comparison] = _CandidateBuilder(value)
        candidate.add(value, evidence)

    def finish(self) -> tuple[ReconciledFact, ReconciliationConflict | None]:
        candidates = tuple(Candidate('candidate:v1:' + hashlib.sha256(key.encode()).hexdigest(), candidate.value,
                                     tuple(sorted(candidate.evidence))) for key, candidate in sorted(self.candidates.items()))
        valid = [candidate for candidate in candidates if valid_value(candidate.value)]
        selected = valid[0].candidate_id if len(valid) == 1 else None
        if not valid:
            rule = 'reconcile.v1.no_valid_value'
        elif len(valid) > 1:
            rule = 'reconcile.v1.unresolved_conflict'
        else:
            rule = 'reconcile.v1.agreed_value' if len(candidates) == 1 else 'reconcile.v1.sole_valid_value'
        fact = ReconciledFact(self.fact_id, self.scope, candidates, selected, rule)
        conflict = None
        if len(valid) > 1:
            conflict = ReconciliationConflict(self.fact_id, self.field, tuple(c.candidate_id for c in valid),
                tuple(sorted({e.observation_id for c in valid for e in c.evidence})))
        return fact, conflict


class Reconciler:
    def __init__(self, canonical_id: str) -> None:
        self.canonical_id = canonical_id
        self.observations: dict[str, str] = {}
        self.facts: dict[tuple[str, str, str], _FactBuilder] = {}
        self.occurrences: dict[str, list[Occurrence]] = defaultdict(list)
        self.identities: dict[ProcedureIdentity, set[str]] = defaultdict(set)

    def _add(self, field: str, slot: Any, scope: FactScope, value: Any, observation: NormalizedObservation, path: str) -> None:
        fact_key = (field, serialize(slot), serialize(scope))
        fact = self.facts.get(fact_key)
        if fact is None:
            fact = self.facts[fact_key] = _FactBuilder(field, slot, scope)
        fact.add(value, EvidenceRef(observation.observation_id, path))

    def add(self, observation: NormalizedObservation) -> None:
        digest = hashlib.sha256(serialize(observation).encode()).hexdigest()
        previous = self.observations.get(observation.observation_id)
        if previous is not None:
            if previous != digest:
                raise ValueError('Conflicting content for the same observation ID')
            return
        self.observations[observation.observation_id] = digest
        for identity in identity_record(observation).identifiers:
            self.identities[identity].add(observation.observation_id)
        procedure = FactScope()
        for original, field in (('procedure_identifiers', 'identifiers'), ('procedure_numbers', 'procedure_numbers'), ('related_identifiers', 'related_identifiers')):
            for index, value in enumerate(getattr(observation, original)):
                self._add(field, semantic_value(value), procedure, value, observation, f'/{original}/{index}')
        for field in ('titles', 'descriptions'):
            for index, value in enumerate(getattr(observation, field)):
                self._add(field, (value.language, value.source_role), procedure, value, observation, f'/{field}/{index}')
        for field in SINGLETONS:
            value = getattr(observation, field)
            if value is not None:
                self._add(field, field, procedure, value, observation, '/' + field)
        for index, item in enumerate(observation.procurement_attributes):
            self._add('procurement_attributes', item.kind, procedure, item, observation, f'/procurement_attributes/{index}')
        for field in ('classifications', 'financials', 'deadlines', 'statuses', 'execution_locations', 'performance_periods'):
            for index, item in enumerate(getattr(observation, field)):
                value = item if field == 'statuses' else item.value
                if field == 'financials':
                    slot = (value.purpose, value.tax_basis, value.currency, value.vat_rate, value.multiple_vat_rates)
                elif field == 'deadlines':
                    slot = value.kind
                elif field == 'statuses':
                    slot = value.dimension
                else:
                    slot = semantic_value(value)
                self._add(field, slot, fact_scope(observation, item.scope), value, observation, f'/{field}/{index}')
        for field in OCCURRENCES:
            self.occurrences[field].extend(Occurrence(observation.observation_id, f'/{field}/{index}', value)
                                          for index, value in enumerate(getattr(observation, field)))

    def finish(self) -> CanonicalObservation:
        state: dict[str, Any] = {}
        conflicts = []
        fact_fields: dict[str, list[ReconciledFact]] = defaultdict(list)
        for _, builder in sorted(self.facts.items()):
            fact, conflict = builder.finish()
            fact_fields[builder.field].append(fact)
            if conflict:
                conflicts.append(conflict)
        for field, values in fact_fields.items():
            state[field] = values[0] if field in SINGLETONS else tuple(values)
        for field, values in self.occurrences.items():
            state[field] = tuple(sorted(values, key=lambda item: (item.observation_id, int(item.normalized_path.rsplit('/', 1)[1]))))
        provenance = tuple(ResolutionEvidence('er.v1.shared_procedure_identifier', identity, tuple(sorted(ids)))
                           for identity, ids in sorted(self.identities.items()))
        return CanonicalObservation(self.canonical_id, tuple(sorted(self.observations)), CurrentState(**state),
                                    tuple(sorted(conflicts, key=lambda item: item.fact_id)), provenance)
