from __future__ import annotations

from collections import Counter
from dataclasses import replace
from datetime import date, time
import re
import xml.etree.ElementTree as ET

from tenderwatch.raw import RawSourceRecord
from .common import PROCEDURE, Builder, composite, key
from .errors import InvalidNormalizationInput
from .models import (
    Award, ContractReference, Coverage, Deadline, DurationPart, LocalizedText, Location,
    Lot, MappedCode, Money, NormalizedObservation, Outcome, Party, PerformancePeriod, ProcurementAttribute, PublicationReference,
    ReportedHash, Scope, Scoped, SourceDocumentReference, SourceMarker, Status,
    SupplierAllocation, TemporalValue,
)

NS = {
    'a': 'http://www.w3.org/2005/Atom',
    'cbc': 'urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2',
    'cac': 'urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2',
    'ext': 'urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2',
    'ebc': 'urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2',
}
LIFECYCLE = {'PRE': 'prior_information', 'PUB': 'submission_open_reported', 'EV': 'awaiting_award', 'ADJ': 'award_reported',
             'RES': 'resolved_unspecified', 'ANUL': 'annulled_reported'}
RESULTS = {'3': 'deserted', '5': 'renounced', '8': 'awarded', '9': 'formalized'}
NOTICES = {'DOC_CN': 'tender_notice', 'DOC_CAN_ADJ': 'award_notice', 'DOC_FORM': 'formalization_notice',
           'DOC_PIN': 'prior_information', 'RENUNCIA': 'annulment_notice'}


def text(node: ET.Element, path: str) -> str | None:
    found = node.find(path, NS)
    return found.text if found is not None else None


def paths_for(root: ET.Element) -> dict[ET.Element, str]:
    paths = {root: '.'}
    def visit(parent: ET.Element) -> None:
        counts = Counter(child.tag for child in parent)
        positions: Counter[str] = Counter()
        for child in parent:
            if not isinstance(child.tag, str):
                continue
            positions[child.tag] += 1
            suffix = f'[{positions[child.tag]}]' if counts[child.tag] > 1 else ''
            paths[child] = paths[parent] + '/' + child.tag + suffix
            visit(child)
    visit(root)
    return paths


class PlacspMapper:
    def __init__(self, raw: RawSourceRecord, entry: ET.Element) -> None:
        self.b = Builder(raw, 'procedure_snapshot')
        self.entry = entry
        self.paths = paths_for(entry)

    def mapped(self, node: ET.Element, vocabulary: dict[str, str], reviewed: str) -> MappedCode:
        uri = node.get('listURI')
        version = reviewed.rsplit('-', 1)[-1].removesuffix('.gc')
        valid = uri in tuple(f'{scheme}://contrataciondelestado.es/codice/cl/{version}/{reviewed}' for scheme in ('http', 'https'))
        mapped = self.b.mapped(node.text or '', self.paths[node], vocabulary if valid else {}, system=uri, broader=('RENUNCIA',))
        return replace(mapped, source=replace(mapped.source, version=version)) if valid else mapped

    def party(self, node: ET.Element, role: str) -> Party | None:
        identifiers = tuple(self.b.identifier(item.text, role, item.get('schemeName', 'source_unclassified'))
                            for item in node.findall('cac:PartyIdentification/cbc:ID', NS) if item.text)
        names = tuple(LocalizedText(item.text, item.get('{http://www.w3.org/XML/1998/namespace}lang'))
                      for item in node.findall('cac:PartyName/cbc:Name', NS) if item.text)
        addresses = tuple(self.location(item) for item in node.findall('cac:PostalAddress', NS))
        return Party(identifiers=identifiers, names=names, addresses=addresses) if identifiers or names or addresses else None

    def location(self, node: ET.Element) -> Location:
        nuts = node.find('cbc:CountrySubentityCode', NS)
        return Location(names=self.b.texts(text(node, 'cbc:CountrySubentity'), self.paths[node]),
            nuts_code=nuts.text if nuts is not None else None,
            nuts_version=nuts.get('listURI') if nuts is not None else None,
            country_code=text(node, 'cac:Country/cbc:IdentificationCode'), locality=text(node, 'cbc:CityName'),
            postal_code=text(node, 'cbc:PostalZone'), address=text(node, 'cac:AddressLine/cbc:Line'))

    def money(self, node: ET.Element, purpose: str, tax: str) -> Money:
        currency = node.get('currencyID')
        if currency not in (None, 'EUR'):
            self.b.issue('unmapped_code', self.paths[node] + '/@currencyID')
            currency = None
        return self.b.money(node.text or '', self.paths[node], purpose, tax, currency)

    def period_time(self, node: ET.Element, date_name: str, time_name: str) -> TemporalValue | None:
        day = node.find(date_name, NS)
        clock = node.find(time_name, NS)
        if day is None and clock is None:
            return None
        raw_day = day.text or '' if day is not None else ''
        raw_time = clock.text or '' if clock is not None else ''
        path = composite([self.paths[item] for item in (day, clock) if item is not None])
        if day is not None and clock is not None:
            offset = raw_day[10:] if len(raw_day) > 10 else ''
            return self.b.temporal(raw_day[:10] + 'T' + raw_time + offset, path)
        if day is not None:
            try:
                return TemporalValue(raw_day, local_date=date.fromisoformat(raw_day[:10]), zone_basis='not_applicable', precision='day')
            except ValueError:
                self.b.issue('invalid_value', path)
                return TemporalValue(raw_day)
        try:
            value = time.fromisoformat(raw_time)
            self.b.issue('ambiguous_time', path)
            return TemporalValue(raw_time, local_time=value.replace(tzinfo=None), precision='second')
        except ValueError:
            self.b.issue('invalid_value', path)
            return TemporalValue(raw_time)

    def project(self, project: ET.Element, scope: Scope) -> None:
        b = self.b
        for tag, purpose, tax in (('EstimatedOverallContractAmount', 'estimated_value', 'excluded'),
                                  ('TaxExclusiveAmount', 'tender_budget', 'excluded'), ('TotalAmount', 'tender_budget', 'included')):
            for node in project.findall('cac:BudgetAmount/cbc:' + tag, NS):
                b.add('financials', Scoped(self.paths[node], scope, self.money(node, purpose, tax)))
        for node in project.findall('cac:RequiredCommodityClassification/cbc:ItemClassificationCode', NS):
            b.add('classifications', Scoped(self.paths[node], scope, b.classification(node.text or '', self.paths[node], node.get('listURI'))))
        for node in project.findall('cac:RealizedLocation', NS):
            b.add('execution_locations', Scoped(self.paths[node], scope, self.location(node)))
        for node in project.findall('cac:PlannedPeriod', NS):
            parts = []
            for duration in node.findall('cbc:DurationMeasure', NS):
                value = b.decimal(duration.text or '', self.paths[duration])
                unit = {'ANN': 'years', 'MON': 'months', 'DAY': 'days', 'HUR': 'hours'}.get(duration.get('unitCode'), 'unspecified')
                if unit == 'unspecified':
                    b.issue('unmapped_code', self.paths[duration] + '/@unitCode' if 'unitCode' in duration.attrib else self.paths[duration])
                if value is not None:
                    parts.append(DurationPart(value, unit))
            b.add('performance_periods', Scoped(self.paths[node], scope, PerformancePeriod(duration=tuple(parts),
                start_at=b.temporal(text(node, 'cbc:StartDate'), self.paths[node]) if text(node, 'cbc:StartDate') else None,
                end_at=b.temporal(text(node, 'cbc:EndDate'), self.paths[node]) if text(node, 'cbc:EndDate') else None)))

    def result(self, result: ET.Element) -> None:
        b = self.b
        path = self.paths[result]
        multiple_projects = len(result.findall('cac:AwardedTenderedProject', NS)) > 1
        lot_ref = result.find('cac:AwardedTenderedProject/cbc:ProcurementProjectLotID', NS)
        if multiple_projects:
            scope = Scope('unknown')
            b.issue('unsupported_structure', path)
        elif lot_ref is not None and lot_ref.text:
            matches = [lot.key for lot in b.data['lots'] if lot.number == lot_ref.text]
            scope = Scope('lots', tuple(matches) if len(matches) == 1 else (),
                          (b.identifier(lot_ref.text, 'lot', 'lot_number', b.raw.raw_record_id),))
            if len(matches) != 1:
                b.issue('uncertain_scope', self.paths[lot_ref])
        elif b.data['lots']:
            scope = Scope('unknown')
            b.issue('uncertain_scope', path)
        else:
            scope = PROCEDURE
        code = result.find('cbc:ResultCode', NS)
        outcome = None
        decision = result.find('cbc:AwardDate', NS)
        decision_at = b.temporal(decision.text or '', self.paths[decision]) if decision is not None else None
        if code is not None:
            outcome = Outcome(key=key('outcome', path), source_path=path, scope=scope,
                              result=self.mapped(code, RESULTS, 'TenderResultCode-2.09.gc'), decision_at=decision_at,
                              reasons=b.texts(text(result, 'cbc:Description'), path))
            b.add('outcomes', outcome)
        if multiple_projects or outcome is None or outcome.result.normalized not in ('awarded', 'formalized'):
            return
        amounts = []
        for tag, tax in (('TaxExclusiveAmount', 'excluded'), ('PayableAmount', 'included')):
            for node in result.findall('cac:AwardedTenderedProject/cac:LegalMonetaryTotal/cbc:' + tag, NS):
                amounts.append(self.money(node, 'award_amount', tax))
        suppliers = []
        for i, node in enumerate(result.findall('cac:WinningParty', NS)):
            party = self.party(node, 'supplier')
            if party:
                suppliers.append(SupplierAllocation(key=key('supplier', self.paths[node]), source_path=self.paths[node], source_position=i, party=party))
        contracts = []
        for node in result.findall('cac:Contract', NS):
            identifier = text(node, 'cbc:ID')
            day = node.find('cbc:IssueDate', NS)
            contracts.append(ContractReference(self.paths[node],
                identifiers=(b.identifier(identifier, 'contract', 'contract_number', b.raw.raw_record_id),) if identifier else (),
                formalized_at=b.temporal(day.text or '', self.paths[day]) if day is not None else None))
        b.add('awards', Award(key=key('award', path), source_path=path, scope=scope, grouping='source_result',
            amounts=tuple(amounts), suppliers=tuple(suppliers), contract_references=tuple(contracts), outcome_keys=(outcome.key,),
            decision_at=decision_at))

    def publications(self, cfs: ET.Element) -> None:
        b = self.b
        for notice in cfs.findall('ext:ValidNoticeInfo', NS):
            code = notice.find('ebc:NoticeTypeCode', NS)
            mapped = self.mapped(code, NOTICES, 'TenderingNoticeTypeCode-2.11.gc') if code is not None else None
            for medium in notice.findall('ext:AdditionalPublicationStatus', NS):
                request = medium.find('ext:AdditionalPublicationRequest', NS)
                dispatch = self.period_time(request, 'ebc:SendDate', 'ebc:SendTime') if request is not None else None
                for reference in medium.findall('ext:AdditionalPublicationDocumentReference', NS):
                    day = reference.find('cbc:IssueDate', NS)
                    path = self.paths[reference]
                    b.add('publications', PublicationReference(key=key('publication', path), source_path=path, scope=PROCEDURE,
                        type=mapped, medium=text(medium, 'ebc:PublicationMediaName'),
                        publication_at=b.temporal(day.text or '', self.paths[day]) if day is not None else None, sent_at=dispatch))

    def documents(self, cfs: ET.Element) -> None:
        b = self.b
        roles = {'LegalDocumentReference': 'administrative_specification', 'TechnicalDocumentReference': 'technical_specification',
                 'AdditionalDocumentReference': 'additional_document'}
        for node in cfs.iter():
            role = next((role for tag, role in roles.items() if node.tag == '{' + NS['cac'] + '}' + tag), None)
            if role is None:
                continue
            path = self.paths[node]
            owners = [(lot.source_path, Scope('lots', (lot.key,))) for lot in b.data['lots']]
            owners.extend((item.source_path, item.scope) for field in ('outcomes', 'awards') for item in b.data[field])
            applicable = [(owner, scope) for owner, scope in owners if path.startswith(owner + '/')]
            scope = max(applicable, key=lambda pair: len(pair[0]))[1] if applicable else PROCEDURE
            urls = []
            for uri in node.findall('cac:Attachment/cac:ExternalReference/cbc:URI', NS):
                value = b.url(uri.text or '', self.paths[uri])
                if value:
                    urls.append(value)
            digest = text(node, 'cac:Attachment/cac:ExternalReference/cbc:DocumentHash')
            identifier = text(node, 'cbc:ID')
            if not (urls or digest or identifier):
                continue
            b.add('documents', SourceDocumentReference(key=key('document', path), source_path=path, scope=scope,
                identifiers=(b.identifier(identifier, 'document', 'source_document', b.raw.raw_record_id),) if identifier else (),
                role=b.mapped(node.tag, path, {node.tag: role}), urls=tuple(urls), reported_hash=ReportedHash(digest) if digest else None))

    def run(self) -> NormalizedObservation:
        b, entry = self.b, self.entry
        cfs = entry.find('ext:ContractFolderStatus', NS)
        if cfs is None:
            raise InvalidNormalizationInput('missing_root_or_wrong_shape', b.raw.raw_record_id)
        atom_id = text(entry, 'a:id')
        if atom_id:
            record_id = b.identifier(atom_id, 'record', 'atom_id')
            b.data['source'] = replace(b.data['source'], record_identifiers=(record_id,))
            b.add('procedure_identifiers', replace(record_id, role='procedure'))
        updated = entry.find('a:updated', NS)
        if updated is not None:
            b.add('source_markers', SourceMarker('placsp_entry_publication_updated', b.temporal(updated.text or '', self.paths[updated])))
        buyer = cfs.find('ext:LocatedContractingParty/cac:Party', NS)
        if buyer is not None:
            b.data['buyer'] = self.party(buyer, 'buyer')
            platform = buyer.find('cac:AgentParty/cac:PartyIdentification/cbc:ID', NS)
            if platform is not None:
                b.data['source'] = replace(b.data['source'], origin_platform=b.code(platform.text or '', self.paths[platform]))
        number = text(cfs, 'cbc:ContractFolderID')
        if number:
            party = b.data.get('buyer')
            owner = '|'.join(identifier.value for identifier in party.identifiers) if party and party.identifiers else b.raw.raw_record_id
            b.add('procedure_numbers', b.identifier(number, 'procedure_number', 'procedure_number', 'placsp:buyer:' + owner))
        status = cfs.find('ebc:ContractFolderStatusCode', NS)
        if status is not None:
            b.add('statuses', Status(self.paths[status], PROCEDURE, 'procurement_lifecycle', self.mapped(status, LIFECYCLE, 'SyndicationContractFolderStatusCode-2.04.gc')))
        project = cfs.find('cac:ProcurementProject', NS)
        if project is not None:
            name = project.find('cbc:Name', NS)
            if name is not None and name.text:
                b.data['titles'] = b.texts(name.text, self.paths[name], 'project_name')
            contract_type = project.find('cbc:TypeCode', NS)
            if contract_type is not None:
                b.data['contract_type'] = self.mapped(contract_type, {'1': 'supplies', '2': 'services', '3': 'works'}, 'ContractCode-2.08.gc')
            flags = project.findall('cbc:MixContractIndicator', NS)
            if flags:
                path = re.sub(r'\[\d+\]$', '', self.paths[flags[0]])
                values = {node.text for node in flags}
                if len(values) > 1:
                    b.issue('inconsistent_source_values', path)
                elif flags[0].text not in ('true', 'false', '1', '0'):
                    b.issue('invalid_value', path)
                else:
                    b.data['mixed_contract'] = flags[0].text in ('true', '1')
            self.project(project, PROCEDURE)
        display_title = text(entry, 'a:title')
        if display_title and not any(title.text == display_title for title in b.data['titles']):
            b.data['titles'] = tuple(b.data['titles']) + b.texts(display_title, self.paths[entry.find('a:title', NS)], 'atom_title')
        for node in cfs.findall('cac:ProcurementProjectLot', NS):
            number = text(node, 'cbc:ID')
            path = self.paths[node]
            lot = Lot(key=key('lot', path), source_path=path, number=number,
                      identifiers=(b.identifier(number, 'lot', 'lot_number', b.raw.raw_record_id),) if number else (),
                      titles=b.texts(text(node, 'cac:ProcurementProject/cbc:Name'), path))
            b.add('lots', lot)
            nested = node.find('cac:ProcurementProject', NS)
            if nested is not None:
                self.project(nested, Scope('lots', (lot.key,)))
        if b.data['lots']:
            b.add('coverage', Coverage('lots', PROCEDURE, 'partial', 'Embedded source occurrences'))
        process = cfs.find('cac:TenderingProcess', NS)
        if process is not None:
            method = process.find('cbc:ProcedureCode', NS)
            if method is not None:
                b.data['procurement_method'] = self.mapped(method, {'1': 'open', '9': 'open_simplified'}, 'SyndicationTenderingProcessCode-2.07.gc')
            for tag, kind in (('UrgencyCode', 'urgency'), ('ContractingSystemCode', 'contracting_system')):
                node = process.find('cbc:' + tag, NS)
                if node is not None:
                    b.add('procurement_attributes', ProcurementAttribute(kind, b.code(node.text or '', self.paths[node], node.get('listURI'))))
            for tag, kind in (('TenderSubmissionDeadlinePeriod', 'offers'), ('DocumentAvailabilityPeriod', 'document_access'), ('ParticipationRequestReceptionPeriod', 'participation_requests')):
                for node in process.findall('cac:' + tag, NS):
                    at = self.period_time(node, 'cbc:EndDate', 'cbc:EndTime')
                    if at is not None:
                        b.add('deadlines', Scoped(self.paths[node], PROCEDURE, Deadline(kind, at)))
        for node in cfs.findall('cac:TenderResult', NS):
            self.result(node)
        self.publications(cfs)
        self.documents(cfs)
        for link in entry.findall('a:link', NS):
            if 'href' in link.attrib:
                reference = b.reference(link.attrib['href'], self.paths[link] + '/@href', 'publication_page')
                if reference:
                    for identifier in reference.identifiers:
                        if identifier.role == 'procedure':
                            b.add('procedure_identifiers', identifier)
        return b.finish()


def normalize_placsp(raw: RawSourceRecord, entry: ET.Element) -> NormalizedObservation:
    return PlacspMapper(raw, entry).run()
