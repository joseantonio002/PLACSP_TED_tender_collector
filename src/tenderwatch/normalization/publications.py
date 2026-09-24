from __future__ import annotations

from dataclasses import replace
import re
from typing import Any

from tenderwatch.raw import RawSourceRecord
from .common import BATCH_PATH, BATCH_SCOPE, PROCEDURE, SUBJECT, Builder, key, lexical
from .errors import InvalidNormalizationInput, UnsupportedNormalizationInput
from .models import (
    Award, ContractReference, Coverage, Deadline, DurationPart, ExecutionAction, Location,
    Lot, Money, NormalizedObservation, Party, PerformancePeriod, ProcurementAttribute, PublicationReference, RelatedIdentifier,
    ReportedHash, Scope, Scoped, SourceDocumentReference, Status, SupplierAllocation,
)
CONTRACT_TYPES = {'393': 'services', '394': 'supplies'}
METHODS = {'401': 'open', '1000008': 'open_simplified_abbreviated'}
PHASE_CODES = {'1000037': 'future_notice', '1000040': 'tender_notice', '1000043': 'formalization_notice',
               '1000045': 'execution', '1000046': 'aggregate_contract_report'}
ACTIONS = {'1008296': 'modification'}

BASIC = '/publicacio/dadesBasiquesPublicacio'
DETAIL = '/publicacio/dadesPublicacio'
LOTS = '/publicacio/dadesPublicacioLot'


def object_field(b: Builder, parent: dict[str, Any], field: str, path: str) -> dict[str, Any]:
    value = parent.get(field, {})
    if not isinstance(value, dict):
        b.issue('unsupported_structure', path)
        return {}
    return value


def rich_buyer(b: Builder, body: dict[str, Any]) -> Party | None:
    organ = object_field(b, body, 'organ', '/organ')
    identifiers = tuple(b.identifier(organ[field], 'buyer', scheme) for field, scheme in
                        (('nif', 'NIF'), ('organContractacioId', 'pscp_buyer')) if organ.get(field) is not None)
    names = b.texts(organ.get('nom'), '/organ/nom')
    addresses = ()
    if any(organ.get(field) for field in ('direccioPostal', 'localitat', 'codiPostal', 'nuts')):
        addresses = (Location(address=organ.get('direccioPostal'), locality=organ.get('localitat'),
                              postal_code=organ.get('codiPostal'), nuts_code=organ.get('nuts')),)
    return Party(identifiers=identifiers, names=names, addresses=addresses) if identifiers or names or addresses else None


def rich_money(b: Builder, obj: dict[str, Any], path: str, fields: tuple[tuple[str, str, str], ...]) -> tuple[tuple[str, Money], ...]:
    multiple = obj.get('varisTipusIva')
    if multiple is not None and not isinstance(multiple, bool):
        b.issue('invalid_value', path + '/varisTipusIva')
        multiple = None
    vat = b.decimal(obj['iva'], path + '/iva') if 'iva' in obj and multiple is not True else None
    return tuple((path + '/' + field, b.money(obj[field], path + '/' + field, purpose, tax, vat=vat, multiple=multiple))
                 for field, purpose, tax in fields if field in obj)


def rich_financials(b: Builder, obj: dict[str, Any], path: str, scope: Scope) -> None:
    for source_path, money in rich_money(b, obj, path, (
        ('pressupostLicitacio', 'tender_budget', 'excluded'), ('pressupostBaseLicitacioAmbIva', 'tender_budget', 'included'),
        ('valorEstimatContracte', 'estimated_value', 'excluded'), ('valorEstimat', 'estimated_value', 'excluded'),
        ('vec', 'estimated_value', 'excluded'),
    )):
        b.add('financials', Scoped(source_path, scope, money))


def rich_supplier(b: Builder, obj: dict[str, Any], path: str, position: int, *, member: bool = False) -> SupplierAllocation | None:
    id_field, name_field = ('nifAdjudicatari', 'nomAdjudicatari') if member else ('identificador', 'denominacioEmpresaContractista')
    identifiers = ()
    if obj.get(id_field):
        scheme = 'NIF' if member else 'source_unclassified'
        if not member and 'tipusIdentificador' in obj:
            category = obj['tipusIdentificador']
            if isinstance(category, dict) and lexical(category.get('id')) == '542':
                scheme = 'NIF'
            else:
                b.issue('unmapped_code', path + '/tipusIdentificador')
        identifiers = (b.identifier(obj[id_field], 'supplier', scheme),)
    names = b.texts(obj.get(name_field), path + '/' + name_field)
    addresses = (Location(address=obj['adreca']),) if isinstance(obj.get('adreca'), str) and obj['adreca'] else ()
    party = Party(identifiers=identifiers, names=names, addresses=addresses) if identifiers or names or addresses else None
    amounts = tuple(money for _, money in rich_money(b, obj, path, (
        ('importAdjudicacioSenseIva', 'award_amount', 'excluded'), ('importAdjudicacioAmbIva', 'award_amount', 'included'),
    )))
    if party is None and not amounts:
        return None
    return SupplierAllocation(key=key('supplier', path), source_path=path, source_position=position, party=party, amounts=amounts)


def rich_award(b: Builder, obj: dict[str, Any], path: str, scope: Scope, publication_key: str, *, member: bool = False) -> None:
    suppliers = []
    if member:
        allocation = rich_supplier(b, obj, path, 0, member=True)
        if allocation:
            suppliers.append(allocation)
    else:
        rows = obj.get('empresaContractista', [])
        if not isinstance(rows, list):
            b.issue('unsupported_structure', path + '/empresaContractista')
            rows = []
        for index, row in enumerate(rows):
            source_path = path + '/empresaContractista/' + str(index)
            if not isinstance(row, dict):
                b.issue('unsupported_structure', source_path)
                continue
            allocation = rich_supplier(b, row, source_path, index)
            if allocation:
                suppliers.append(allocation)
    if not suppliers and not any(field in obj for field in ('dataAdjudicacio', 'dataFormalitzacio')):
        return
    contracts = ()
    if 'dataFormalitzacio' in obj:
        at = b.temporal(obj['dataFormalitzacio'], path + '/dataFormalitzacio', unresolved=True)
        contracts = (ContractReference(path + '/dataFormalitzacio', formalized_at=at),)
    b.add('awards', Award(key=key('award', path), source_path=path, scope=scope, grouping='source_award_object',
        suppliers=tuple(suppliers), contract_references=contracts, publication_keys=(publication_key,),
        decision_at=b.temporal(obj['dataAdjudicacio'], path + '/dataAdjudicacio', unresolved=True) if 'dataAdjudicacio' in obj else None))


def rich_documents(b: Builder, obj: dict[str, Any], path: str, scope: Scope, publication_key: str) -> None:
    for field, role in (('plecsDeClausulesAdministratives', 'administrative_specification'),
                        ('plecsDePrescripcionsTecniques', 'technical_specification'), ('documentsAddicionals', 'additional_document')):
        if field not in obj:
            continue
        collection = object_field(b, obj, field, path + '/' + field)
        for language, documents in collection.items():
            prefix = path + '/' + field + '/' + language
            if not isinstance(documents, list):
                b.issue('unsupported_structure', prefix)
                continue
            for index, document in enumerate(documents):
                source_path = prefix + '/' + str(index)
                if not isinstance(document, dict):
                    b.issue('unsupported_structure', source_path)
                    continue
                identifiers = (b.identifier(document['id'], 'document', 'pscp_document'),) if document.get('id') is not None else ()
                urls = ()
                if 'url' in document:
                    url = b.url(document['url'], source_path + '/url')
                    urls = (url,) if url else ()
                if not (identifiers or urls or document.get('path') or document.get('titol')):
                    continue
                b.add('documents', SourceDocumentReference(key=key('document', source_path), source_path=source_path, scope=scope,
                    identifiers=identifiers, role=b.mapped(field, source_path, {field: role}),
                    titles=b.texts(document.get('titol'), source_path + '/titol'), language=document.get('idioma', language), urls=urls,
                    source_path_token=document.get('path'), reported_hash=ReportedHash(document['hash']) if document.get('hash') else None,
                    publication_keys=(publication_key,)))


def rich_scoped(b: Builder, obj: dict[str, Any], path: str, scope: Scope) -> None:
    rich_financials(b, obj, path, scope)
    for field in ('cpvPrincipal', 'codiCpv'):
        if field in obj:
            category = object_field(b, obj, field, path + '/' + field)
            if 'codi' in category:
                source_path = path + '/' + field + '/codi'
                value = b.classification(category['codi'], source_path)
                b.add('classifications', Scoped(source_path, scope, replace(value, role='main' if field == 'cpvPrincipal' else 'unspecified')))
    if obj.get('llocExecucio'):
        location = obj['llocExecucio']
        source_path = path + '/llocExecucio'
        names = b.texts(location, source_path)
        nuts = location.get('codiNuts') if isinstance(location, dict) else None
        if names or nuts:
            b.add('execution_locations', Scoped(source_path, scope, Location(names=names, nuts_code=nuts)))
    if 'duradaTermini' in obj:
        source_path = path + '/duradaTermini'
        period = object_field(b, obj, 'duradaTermini', source_path)
        parts = []
        for field, unit in (('anys', 'years'), ('mesos', 'months'), ('dies', 'days')):
            if field in period:
                value = b.decimal(period[field], source_path + '/' + field)
                if value is not None:
                    parts.append(DurationPart(value, unit))
        texts = b.texts(period.get('observacions'), source_path + '/observacions')
        if parts or texts:
            b.add('performance_periods', Scoped(source_path, scope, PerformancePeriod(raw_text=texts, duration=tuple(parts))))


def map_body(raw: RawSourceRecord, body: dict[str, Any], projection: str, member: dict[str, Any] | None) -> NormalizedObservation:
    batch = member is not None
    b = Builder(raw, 'batch_publication_body' if batch else 'publication_body', projection)
    publication = body['publicacio']
    basic = object_field(b, publication, 'dadesBasiquesPublicacio', BASIC)
    detail = object_field(b, publication, 'dadesPublicacio', DETAIL)
    scope = SUBJECT if batch else PROCEDURE
    b.data.update(focus=scope, buyer=rich_buyer(b, body), subject_kind='batch_member' if batch else 'procedure')
    for value, path in ((body.get('idExpedient'), '/idExpedient'), (publication.get('expedientId'), '/publicacio/expedientId')):
        if value:
            field = 'batch_identifiers' if batch else 'procedure_identifiers'
            if not any(i.value == lexical(value) for i in b.data[field]):
                b.add(field, b.identifier(value, 'batch' if batch else 'procedure', 'pscp_uuid', 'gencat:pscp'))
    if body.get('idExpedient') and publication.get('expedientId') and body['idExpedient'] != publication['expedientId']:
        b.issue('inconsistent_source_values', '/publicacio/expedientId')
    selected, selected_path = (member, projection) if batch else (basic, BASIC)
    number = selected.get('expedient') if batch else basic.get('codiExpedient', body.get('codiExpedient'))
    if number:
        organ = body.get('organ') if isinstance(body.get('organ'), dict) else {}
        b.add('procedure_numbers', b.identifier(number, 'procedure_number', 'procedure_number', 'gencat:buyer:' + lexical(organ.get('organContractacioId', raw.raw_record_id))))
    if not batch:
        b.data['titles'] = b.texts(basic.get('denominacio'), BASIC + '/denominacio')
    b.data['descriptions'] = b.texts(selected.get('descripcio'), selected_path + '/descripcio')
    if 'tipusContracte' in selected:
        b.data['contract_type'] = b.mapped(selected['tipusContracte'], selected_path + '/tipusContracte', CONTRACT_TYPES)
    if not batch and 'procedimentAdjudicacio' in basic:
        b.data['procurement_method'] = b.mapped(basic['procedimentAdjudicacio'], BASIC + '/procedimentAdjudicacio', METHODS)
    if 'contracteMixt' in selected:
        if isinstance(selected['contracteMixt'], bool):
            b.data['mixed_contract'] = selected['contracteMixt']
        else:
            b.issue('invalid_value', selected_path + '/contracteMixt')
    for field, kind in (('racionalitzacioContractacio', 'contracting_system'), ('tipusTramitacio', 'urgency')):
        if field in basic:
            b.add('procurement_attributes', ProcurementAttribute(kind, b.code(basic[field], BASIC + '/' + field)))
    phase = b.mapped(publication['fase'], '/publicacio/fase', PHASE_CODES) if 'fase' in publication else None
    if phase:
        b.add('statuses', Status('/publicacio/fase', BATCH_SCOPE if batch else scope, 'publication_phase', phase))
        if phase.normalized == 'future_notice' and not batch:
            b.data['subject_kind'] = 'planning'
    correction_type = b.texts(publication.get('tipusEsmena'), '/publicacio/tipusEsmena')
    correction_reason = b.texts(publication.get('motiuEsmena'), '/publicacio/motiuEsmena')
    publication_key = key('publication', '/publicacio')
    b.add('publications', PublicationReference(key=publication_key, source_path='/publicacio', scope=BATCH_SCOPE if batch else scope,
        type=phase, medium='PSCP',
        publication_at=b.temporal(body['dataPublicacioReal'], '/dataPublicacioReal') if 'dataPublicacioReal' in body else None,
        planned_publication_at=b.temporal(body['dataPublicacioPlanificada'], '/dataPublicacioPlanificada') if 'dataPublicacioPlanificada' in body else None,
        is_correction=True if correction_type or correction_reason else None, correction_type=correction_type, correction_reason=correction_reason))
    if batch:
        if detail.get('nombreInformats') is not None and detail['nombreInformats'] != len(detail['contractesAgregada']):
            b.issue('inconsistent_source_values', DETAIL + '/nombreInformats')
        rich_scoped(b, member, projection, scope)
        rich_award(b, member, projection, scope, publication_key, member=True)
        for field in ('expedientIdReferencia', 'codiExpedientReferencia'):
            if member.get(field):
                b.add('related_identifiers', RelatedIdentifier(b.identifier(member[field], 'related', field), 'framework_reference'))
        return b.finish()
    rich_scoped(b, detail, DETAIL, PROCEDURE)
    if 'dataTerminiPresentacioOSolicitud' in detail:
        path = DETAIL + '/dataTerminiPresentacioOSolicitud'
        b.add('deadlines', Scoped(path, PROCEDURE, Deadline('submission_unspecified', b.temporal(detail['dataTerminiPresentacioOSolicitud'], path))))
    rich_documents(b, detail, DETAIL, PROCEDURE, publication_key)
    division = detail.get('divisioEnLots')
    explicit_no_lots = isinstance(division, dict) and division.get('ca') == 'Sense lots'
    conflict = publication.get('teLots') is True and explicit_no_lots
    if conflict:
        b.issue('inconsistent_source_values', '/publicacio/teLots')
    no_lots = publication.get('teLots') is False or explicit_no_lots
    if no_lots and not conflict:
        b.add('coverage', Coverage('lots', PROCEDURE, 'source_declares_empty', 'Explicit no-lots declaration'))
    rows = publication.get('dadesPublicacioLot', [])
    if not isinstance(rows, list):
        b.issue('unsupported_structure', LOTS)
        rows = []
    for index, row in enumerate(rows):
        path = LOTS + '/' + str(index)
        if not isinstance(row, dict):
            b.issue('unsupported_structure', path)
            continue
        scope = PROCEDURE if no_lots and not conflict else SUBJECT
        if not no_lots and row.get('numeroLot') is not None:
            lot = Lot(key=key('lot', path), source_path=path, number=lexical(row['numeroLot']),
                identifiers=tuple(b.identifier(row[field], 'lot', field, raw.raw_record_id) for field in ('lotId', 'numeroLot') if row.get(field) is not None),
                descriptions=b.texts(row.get('descripcio'), path + '/descripcio'))
            b.add('lots', lot)
            scope = Scope('lots', (lot.key,))
        rich_scoped(b, row, path, scope)
        rich_award(b, row, path, scope, publication_key)
        rich_documents(b, row, path, scope, publication_key)
        actions = row.get('modificacions', [])
        if not isinstance(actions, list):
            b.issue('unsupported_structure', path + '/modificacions')
            continue
        for position, action in enumerate(actions):
            action_path = path + '/modificacions/' + str(position)
            if not isinstance(action, dict):
                b.issue('unsupported_structure', action_path)
                continue
            action_type = action.get('tipusActuacioExecucio')
            if not isinstance(action_type, dict):
                b.issue('unsupported_structure', action_path + '/tipusActuacioExecucio')
                continue
            b.add('execution_actions', ExecutionAction(key=key('action', action_path), source_path=action_path, scope=scope,
                identifiers=(b.identifier(action['identificador'], 'action', 'pscp_action', raw.raw_record_id),) if action.get('identificador') is not None else (),
                type=b.mapped(action_type, action_path + '/tipusActuacioExecucio', ACTIONS),
                titles=b.texts(action.get('denominacioModificacio'), action_path + '/denominacioModificacio'),
                action_at=b.temporal(action['dataModificacio'], action_path + '/dataModificacio', unresolved=True) if 'dataModificacio' in action else None,
                amounts=(b.money(action['incrementPreu'], action_path + '/incrementPreu', 'modification_delta', 'unspecified'),) if 'incrementPreu' in action else (),
                publication_keys=(publication_key,)))
    if b.data['lots']:
        b.add('coverage', Coverage('lots', PROCEDURE, 'partial', 'Embedded source lot occurrences'))
    return b.finish()


def normalize_publication(raw: RawSourceRecord, body: dict[str, Any], projection: str | None) -> tuple[NormalizedObservation, ...]:
    publication = body.get('publicacio')
    if not isinstance(publication, dict):
        raise InvalidNormalizationInput('missing_root_or_wrong_shape', raw.raw_record_id, projection or '$')
    basic, detail = publication.get('dadesBasiquesPublicacio', {}), publication.get('dadesPublicacio', {})
    batch = isinstance(basic, dict) and basic.get('publicacioAgregada') is True
    if isinstance(detail, dict) and 'contractesAgregada' in detail:
        batch = True
    if not batch:
        if projection not in (None, '$'):
            raise InvalidNormalizationInput('unresolvable_projection', raw.raw_record_id, projection)
        return (map_body(raw, body, '$', None),)
    members = detail.get('contractesAgregada') if isinstance(detail, dict) else None
    if not isinstance(members, list) or not members:
        raise UnsupportedNormalizationInput('unprojectable_subject', raw.raw_record_id, projection or '$')
    indices = range(len(members))
    if projection is not None:
        match = re.fullmatch(re.escape(BATCH_PATH) + r'/(0|[1-9]\d*)', projection)
        if match is None or int(match[1]) >= len(members):
            raise InvalidNormalizationInput('unresolvable_projection', raw.raw_record_id, projection)
        indices = (int(match[1]),)
    observations = []
    for index in indices:
        path = BATCH_PATH + '/' + str(index)
        member = members[index]
        if not isinstance(member, dict):
            raise InvalidNormalizationInput('missing_root_or_wrong_shape', raw.raw_record_id, path)
        if not member:
            raise UnsupportedNormalizationInput('unprojectable_subject', raw.raw_record_id, path)
        observations.append(map_body(raw, body, path, member))
    return tuple(observations)
