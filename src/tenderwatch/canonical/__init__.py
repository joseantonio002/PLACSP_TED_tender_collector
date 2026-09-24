from __future__ import annotations

from collections.abc import Iterable

from tenderwatch.normalization.models import NormalizedObservation
from .models import CanonicalObservation, CanonicalizationResult, UnresolvedObservation
from .reconciliation import Reconciler
from .resolution import ResolutionIndex, identity_record

SCHEMA_VERSION = 'tenderwatch.canonical.v1'
RESOLUTION_VERSION = 'er.v1'
RECONCILIATION_VERSION = 'reconcile.v1'


def canonicalize(observations: Iterable[NormalizedObservation]) -> CanonicalizationResult:
    retained: dict[str, NormalizedObservation] = {}
    index = ResolutionIndex()
    for observation in observations:
        existing = retained.get(observation.observation_id)
        if existing is not None:
            if existing != observation:
                raise ValueError('Conflicting content for the same observation ID')
            continue
        retained[observation.observation_id] = observation
        index.add(identity_record(observation))
    index.finalize()
    groups: dict[str, Reconciler] = {}
    unresolved = []
    for observation_id in sorted(retained):
        observation = retained[observation_id]
        decision = index.resolve(identity_record(observation))
        if isinstance(decision, UnresolvedObservation):
            unresolved.append(decision)
        else:
            group = groups.setdefault(decision, Reconciler(decision))
            group.add(observation)
    return CanonicalizationResult(tuple(groups[key].finish() for key in sorted(groups)), tuple(unresolved))
