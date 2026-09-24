from __future__ import annotations

from dataclasses import replace
from typing import Any

from tenderwatch.raw import RawSourceRecord
from .common import BATCH_SCOPE, PROCEDURE, SUBJECT, Builder, composite, key, lexical
from .errors import UnsupportedNormalizationInput
from .models import (
    Award, ContractReference, Coverage, Deadline, ExecutionAction, Location,
    Lot, NormalizedObservation, Outcome, Party, PerformancePeriod, ProcurementAttribute, PublicationReference,
    Scope, Scoped, SourceMarker, Status, SupplierAllocation,
)

CONTRACT_TYPES = {'Serveis': 'services', 'Subministraments': 'supplies', 'Subministraments ': 'supplies', 'Obres': 'works',
                  'Contracte de serveis especials (annex IV)': 'services'}
METHODS = {'Obert': 'open', 'Obert simplificat': 'open_simplified', 'Obert simplificat abreujat': 'open_simplified_abbreviated',
           'Restringit': 'restricted'}
PHASE_CODES = {
    'Alerta futura': 'future_notice', 'Consulta preliminar del mercat': 'market_consultation',
    'Anunci previ': 'prior_information', 'Anunci de licitació': 'tender_notice',
    'Expedient en avaluació': 'evaluation', 'Adjudicació': 'award_notice', 'Formalització': 'formalization_notice',
    'Anul·lació': 'annulment_notice', 'Publicació agregada de contractes': 'aggregate_contract_report',
    'Execució': 'execution',
}
RESULTS = {'Formalització': 'formalized', 'Adjudicació': 'awarded', 'Desert': 'deserted', 'Deserta': 'deserted',
           'Renúncia': 'renounced', 'Desistiment': 'discontinued'}
ACTIONS = {'Modificació (Objectiva)': 'modification', 'Modificació': 'modification',
           'Pròrroga': 'extension', 'Extinció': 'termination'}
PHASES = (
    ('data_publicacio_futura', 'url_json_futura', 'future_notice'),
    ('data_publicacio_consulta', 'url_json_cpm', 'market_consultation'),
    ('data_publicacio_previ', 'url_json_previ', 'prior_information'),
    ('data_publicacio_anunci', 'url_json_licitacio', 'tender_notice'),
    ('data_publicacio_avaluacio', 'url_json_avaluacio', 'evaluation'),
    ('data_publicacio_adjudicacio', 'url_json_adjudicacio', 'award_notice'),
    ('data_publicacio_formalitzacio', 'url_json_formalitzacio', 'formalization_notice'),
    ('data_publicacio_anul', 'url_json_anulacio', 'annulment_notice'),
    ('data_publicacio_contracte', 'url_json_agregada', 'aggregate_contract_report'),
    ('data_publicacio_encarrec', None, 'own_resource_entrustment_notice'),
)


def table_buyer(b: Builder, row: dict[str, Any]) -> Party | None:
    identifiers = []
    for field, scheme in (('codi_organ', 'pscp_buyer'), ('codi_dir3', 'DIR3')):
        value = row.get(field)
        if value:
            identifier = b.identifier(value, 'buyer', scheme)
            if scheme == 'DIR3' and value in ('A9999999', 'A99999999'):
                identifier = replace(identifier, usability='placeholder')
                b.issue('placeholder_identifier', '/' + field)
            identifiers.append(identifier)
    names = b.texts(row.get('nom_organ'), '/nom_organ')
    return Party(identifiers=tuple(identifiers), names=names) if identifiers or names else None


def table_envelope(b: Builder, row: dict[str, Any]) -> None:
    b.data['source'] = replace(b.data['source'], record_identifiers=tuple(
        b.identifier(row[field], 'record', 'socrata_row' if field == ':id' else 'pscp_row')
        for field in (':id', 'id_intern') if row.get(field)
    ))
    for field, kind in ((':created_at', 'socrata_row_created'), (':updated_at', 'socrata_row_updated')):
        if field in row:
            b.add('source_markers', SourceMarker(kind, b.temporal(row[field], '/' + field)))
    b.data['buyer'] = table_buyer(b, row)
    if row.get('codi_expedient'):
        b.add('procedure_numbers', b.identifier(row['codi_expedient'], 'procedure_number', 'procedure_number',
              'gencat:buyer:' + lexical(row.get('codi_organ', b.raw.raw_record_id))))


def table_publications(b: Builder, row: dict[str, Any], batch: bool) -> None:
    for date_field, export_field, phase in PHASES:
        if date_field not in row and export_field not in row:
            continue
        path = '/' + date_field if date_field in row else '/' + export_field
        publication_key = key('publication', path)
        reference = None
        if export_field in row:
            value = row[export_field]
            if isinstance(value, dict) and 'url' in value:
                reference = b.reference(value['url'], '/' + export_field + '/url', 'publication_export', (publication_key,))
            else:
                b.issue('unsupported_structure', '/' + export_field)
        b.add('publications', PublicationReference(
            key=publication_key, source_path=path, scope=BATCH_SCOPE if phase == 'aggregate_contract_report' else SUBJECT,
            type=b.mapped(date_field, path, {date_field: phase}),
            publication_at=b.temporal(row[date_field], '/' + date_field) if date_field in row else None,
            identifiers=tuple(i for i in reference.identifiers if i.role == 'publication') if reference else (),
        ))
    page = row.get('enllac_publicacio')
    if isinstance(page, dict) and 'url' in page:
        reference = b.reference(page['url'], '/enllac_publicacio/url', 'publication_page', batch=batch)
        if reference:
            for identifier in reference.identifiers:
                if identifier.role in ('procedure', 'batch'):
                    b.add('batch_identifiers' if batch else 'procedure_identifiers', identifier)


def tokens(row: dict[str, Any], field: str) -> list[tuple[Any, str]]:
    if field not in row:
        return []
    value = row[field]
    if isinstance(value, str) and '||' in value:
        return [(token, '/' + field + '#token=' + str(i)) for i, token in enumerate(value.split('||'))]
    return [(value, '/' + field)]


def table_award(b: Builder, row: dict[str, Any], scope: Scope, outcome: Outcome | None) -> None:
    ids = tokens(row, 'identificacio_adjudicatari')
    names = tokens(row, 'denominacio_adjudicatari')
    schemes = tokens(row, 'tipus_identificacio')
    net = tokens(row, 'import_adjudicacio_sense')
    gross = tokens(row, 'import_adjudicacio_amb_iva')
    positive = outcome is not None and outcome.result.normalized in ('awarded', 'formalized')
    if not (ids or names or net or gross or positive):
        return
    count = max(len(ids), len(names))
    allocations = []
    compatible = not ids or not names or len(ids) == len(names)
    for i in range(count):
        identifiers = ()
        texts = ()
        paths = []
        if i < len(ids):
            value, path = ids[i]
            paths.append(path)
            if value:
                scheme = schemes[i][0] if len(schemes) == count else None
                if scheme is not None and scheme != '542':
                    b.issue('unmapped_code', schemes[i][1])
                identifiers = (b.identifier(value, 'supplier', 'NIF' if scheme == '542' else 'source_unclassified'),)
            else:
                b.issue('explicit_empty', path)
        if i < len(names) and (compatible or not ids):
            value, path = names[i]
            paths.append(path)
            texts = b.texts(value, path)
        if not paths:
            continue
        amounts = []
        for vector, tax in ((net, 'excluded'), (gross, 'included')):
            if len(vector) == count and compatible:
                value, path = vector[i]
                amounts.append(b.money(value, path, 'award_amount', tax))
        path = composite(paths)
        allocations.append(SupplierAllocation(key=key('supplier', path), source_path=path, source_position=i,
            party=Party(identifiers=identifiers, names=texts) if identifiers or texts else None,
            amounts=tuple(amounts), alignment='positional' if compatible else 'unresolved'))
    if not compatible:
        b.issue('supplier_alignment', '/denominacio_adjudicatari')
        for i, (value, path) in enumerate(names):
            if value:
                allocations.append(SupplierAllocation(key=key('supplier-name', path), source_path=path, source_position=i,
                    party=Party(names=b.texts(value, path)), alignment='unresolved'))
    for vector, tax, field in ((net, 'excluded', 'import_adjudicacio_sense'), (gross, 'included', 'import_adjudicacio_amb_iva')):
        if vector and (len(vector) != count or not compatible):
            b.issue('supplier_alignment', '/' + field)
            for i, (value, path) in enumerate(vector):
                allocations.append(SupplierAllocation(key=key('unresolved-money', path), source_path=path, source_position=i,
                    amounts=(b.money(value, path, 'award_amount', tax),), alignment='unresolved'))
    contracts = ()
    if 'data_formalitzacio_contracte' in row:
        path = '/data_formalitzacio_contracte'
        contracts = (ContractReference(path, formalized_at=b.temporal(row['data_formalitzacio_contracte'], path, calendar=True)),)
    b.add('awards', Award(key=key('award', '$'), source_path='$', scope=scope, grouping='source_row_group',
        suppliers=tuple(allocations), contract_references=contracts,
        decision_at=b.temporal(row['data_adjudicacio_contracte'], '/data_adjudicacio_contracte', calendar=True) if 'data_adjudicacio_contracte' in row else None,
        outcome_keys=(outcome.key,) if positive else ()))


def normalize_main(raw: RawSourceRecord, row: dict[str, Any]) -> NormalizedObservation:
    if not row:
        raise UnsupportedNormalizationInput('unprojectable_subject', raw.raw_record_id)
    batch = row.get('es_agregada') == 'SÍ'
    number = row.get('numero_lot')
    has_lot = number is not None and lexical(number) not in ('', '0') and not batch
    kind = 'batch_member_projection' if batch else ('lot_projection' if has_lot else 'procedure_projection')
    b = Builder(raw, kind)
    table_envelope(b, row)
    if batch:
        b.data.update(subject_kind='batch_member', focus=SUBJECT)
        if row.get('id_intern'):
            b.add('member_identifiers', b.identifier(row['id_intern'], 'member', 'pscp_member'))
    elif row.get('fase_publicacio') == 'Alerta futura':
        b.data['subject_kind'] = 'planning'
    scope = SUBJECT
    if has_lot:
        lot = Lot(key=key('lot', '/numero_lot'), source_path='/numero_lot', number=lexical(number),
                  identifiers=(b.identifier(number, 'lot', 'lot_number', raw.raw_record_id),),
                  descriptions=b.texts(row.get('descripcio_lot'), '/descripcio_lot'))
        b.add('lots', lot)
        scope = Scope('lots', (lot.key,))
        b.data['focus'] = scope
        b.add('coverage', Coverage('lots', scope, 'partial', 'One source row'))
    table_publications(b, row, batch)
    b.data['titles'] = b.texts(row.get('denominacio'), '/denominacio')
    b.data['descriptions'] = b.texts(row.get('objecte_contracte'), '/objecte_contracte')
    for field, target, vocabulary in (('tipus_contracte', 'contract_type', CONTRACT_TYPES), ('procediment', 'procurement_method', METHODS)):
        if field in row:
            b.data[target] = b.mapped(row[field], '/' + field, vocabulary, broader=('Contracte de serveis especials (annex IV)',))
    for field, kind in (('racionalitzacio_contractacio', 'contracting_system'), ('tipus_tramitacio', 'urgency')):
        if field in row:
            b.add('procurement_attributes', ProcurementAttribute(kind, b.code(row[field], '/' + field)))
    if 'fase_publicacio' in row:
        b.add('statuses', Status('/fase_publicacio', SUBJECT, 'publication_phase', b.mapped(row['fase_publicacio'], '/fase_publicacio', PHASE_CODES)))
    for field, purpose, tax, procedure in (
        ('pressupost_licitacio_sense_1', 'tender_budget', 'excluded', True),
        ('pressupost_licitacio_amb_1', 'tender_budget', 'included', True),
        ('valor_estimat_expedient', 'estimated_value', 'excluded', True),
        ('pressupost_licitacio_sense', 'tender_budget', 'excluded', False),
        ('pressupost_licitacio_amb', 'tender_budget', 'included', False),
        ('valor_estimat_contracte', 'estimated_value', 'excluded', False),
    ):
        if field in row:
            path = '/' + field
            fact_scope = PROCEDURE if procedure and not batch else scope
            b.add('financials', Scoped(path, fact_scope, b.money(row[field], path, purpose, tax)))
            if not procedure and not has_lot and not batch:
                b.issue('uncertain_scope', path)
    if 'codi_cpv' in row:
        b.add('classifications', Scoped('/codi_cpv', scope, b.classification(row['codi_cpv'], '/codi_cpv')))
    if 'termini_presentacio_ofertes' in row:
        path = '/termini_presentacio_ofertes'
        b.add('deadlines', Scoped(path, scope, Deadline('offers', b.temporal(row[path[1:]], path))))
    if row.get('lloc_execucio') or row.get('codi_nuts'):
        paths = ['/' + field for field in ('lloc_execucio', 'codi_nuts') if row.get(field)]
        b.add('execution_locations', Scoped(composite(paths), scope, Location(names=b.texts(row.get('lloc_execucio'), '/lloc_execucio'), nuts_code=row.get('codi_nuts'))))
    if row.get('durada_contracte'):
        b.add('performance_periods', Scoped('/durada_contracte', scope, PerformancePeriod(raw_text=b.texts(row['durada_contracte'], '/durada_contracte'))))
    outcome = None
    if row.get('resultat'):
        outcome = Outcome(key=key('outcome', '/resultat'), source_path='/resultat', scope=scope, result=b.mapped(row['resultat'], '/resultat', RESULTS))
        b.add('outcomes', outcome)
    table_award(b, row, scope, outcome)
    return b.finish()


def normalize_execution(raw: RawSourceRecord, row: dict[str, Any]) -> NormalizedObservation:
    if not row:
        raise UnsupportedNormalizationInput('unprojectable_subject', raw.raw_record_id)
    b = Builder(raw, 'execution_action_projection')
    table_envelope(b, row)
    scope = SUBJECT
    number = row.get('numero_lot')
    if number is not None and lexical(number) not in ('', '0'):
        scope = Scope('lots', source_lot_identifiers=(b.identifier(number, 'lot', 'lot_number', raw.raw_record_id),))
    elif 'numero_lot' in row:
        b.issue('uncertain_scope', '/numero_lot')
    b.data['focus'] = scope
    publications = ()
    if 'url_json' in row:
        reference = b.reference(row['url_json'], '/url_json', 'publication_export', (key('publication', '/url_json'),))
        if reference:
            publication = PublicationReference(key=key('publication', '/url_json'), source_path='/url_json', scope=SUBJECT,
                                               identifiers=reference.identifiers)
            b.add('publications', publication)
            publications = (publication.key,)
    if 'tipus_actuacio_execucio' in row:
        b.add('execution_actions', ExecutionAction(key=key('action', '$'), source_path='$', scope=scope,
            type=b.mapped(row['tipus_actuacio_execucio'], '/tipus_actuacio_execucio', ACTIONS),
            titles=b.texts(row.get('denominacio_actuacio'), '/denominacio_actuacio'),
            details=b.texts(row.get('observacions'), '/observacions'),
            action_at=b.temporal(row['data'], '/data', calendar=True) if 'data' in row else None,
            end_at=b.temporal(row['data_fi'], '/data_fi', calendar=True) if 'data_fi' in row else None,
            amounts=(b.money(row['import_sense_iva'], '/import_sense_iva', 'action_amount', 'excluded'),) if 'import_sense_iva' in row else (),
            publication_keys=publications))
    return b.finish()
