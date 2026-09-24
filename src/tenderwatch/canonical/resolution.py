from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any

from tenderwatch.normalization.models import NormalizedObservation
from tenderwatch.serialization import serialize
from .models import ProcedureIdentity, UnresolvedObservation


@dataclass(frozen=True, slots=True)
class ObservationIdentity:
    observation_id: str
    procedure_subject: bool
    identifiers: tuple[ProcedureIdentity, ...]


def _identities(system: str, dataset: str, identifiers: list[dict[str, str]]) -> tuple[ProcedureIdentity, ...]:
    result = set()
    for item in identifiers:
        if item['role'] != 'procedure' or item['usability'] in ('placeholder', 'invalid'):
            continue
        scheme, namespace, value = item['scheme'], item['namespace'], item['value']
        if scheme == 'pscp_uuid' and namespace == 'gencat:pscp':
            if not re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', value) or value == '00000000-0000-0000-0000-000000000000':
                continue
        elif scheme == 'atom_id' and system == 'placsp' and namespace == f'placsp:{dataset}:atom_id':
            collection = {'aggregated': 'PlataformasAgregadasSinMenores', 'native': 'licitacionesPerfilContratante'}.get(dataset)
            if collection is None or not re.fullmatch(r'https?://contrataciondelestado\.es/sindicacion/' + collection + r'/\d+', value):
                continue
        else:
            continue
        result.add(ProcedureIdentity(scheme, namespace, value))
    return tuple(sorted(result))


def identity_record(observation: NormalizedObservation) -> ObservationIdentity:
    ids = [{'scheme': i.scheme, 'namespace': i.namespace, 'value': i.value, 'role': i.role, 'usability': i.usability}
           for i in observation.procedure_identifiers]
    subject = observation.subject_kind == 'procedure' and not observation.batch_identifiers and not observation.member_identifiers
    return ObservationIdentity(observation.observation_id, subject, _identities(observation.source.system, observation.source.dataset, ids))


def identity_from_dict(observation: dict[str, Any]) -> ObservationIdentity:
    subject = observation['subject_kind'] == 'procedure' and not observation['batch_identifiers'] and not observation['member_identifiers']
    return ObservationIdentity(observation['observation_id'], subject,
        _identities(observation['source']['system'], observation['source']['dataset'], observation['procedure_identifiers']))


class ResolutionIndex:
    def __init__(self) -> None:
        self.parent: dict[ProcedureIdentity, ProcedureIdentity] = {}
        self.sizes: dict[ProcedureIdentity, int] = {}
        self.decisions: dict[ProcedureIdentity, str | None] | None = None

    def _root(self, identity: ProcedureIdentity) -> ProcedureIdentity:
        root = identity
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[identity] != identity:
            parent = self.parent[identity]
            self.parent[identity] = root
            identity = parent
        return root

    def add(self, record: ObservationIdentity) -> None:
        if self.decisions is not None:
            raise ValueError('Resolution index is already finalized')
        if not record.procedure_subject:
            return
        for identity in record.identifiers:
            if identity not in self.parent:
                self.parent[identity] = identity
                self.sizes[identity] = 1
        for identity in record.identifiers[1:]:
            first, second = self._root(record.identifiers[0]), self._root(identity)
            if first != second:
                if self.sizes[first] < self.sizes[second]:
                    first, second = second, first
                self.parent[second] = first
                self.sizes[first] += self.sizes.pop(second)

    def finalize(self) -> None:
        anchors: dict[ProcedureIdentity, ProcedureIdentity] = {}
        uuids: dict[ProcedureIdentity, set[ProcedureIdentity]] = {}
        for identity in self.parent:
            root = self._root(identity)
            anchors[root] = min(anchors.get(root, identity), identity)
            if identity.scheme == 'pscp_uuid':
                uuids.setdefault(root, set()).add(identity)
        self.decisions = {}
        for root, fallback in anchors.items():
            candidates = uuids.get(root, set())
            anchor = next(iter(candidates)) if len(candidates) == 1 else fallback
            self.decisions[root] = None if len(candidates) > 1 else 'canonical:v1:' + hashlib.sha256(serialize(anchor).encode()).hexdigest()
        self.sizes.clear()

    def resolve(self, record: ObservationIdentity) -> str | UnresolvedObservation:
        if self.decisions is None:
            raise ValueError('Finalize the complete identity index before resolving')
        reason = None
        if not record.procedure_subject:
            reason = 'not_a_procedure_subject'
        elif not record.identifiers:
            reason = 'no_strong_procedure_identifier'
        else:
            result = self.decisions[self._root(record.identifiers[0])]
            if result is not None:
                return result
            reason = 'contradictory_procedure_identifiers'
        return UnresolvedObservation(record.observation_id, reason, record.identifiers)
