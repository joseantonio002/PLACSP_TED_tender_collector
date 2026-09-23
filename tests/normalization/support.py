from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from copy import deepcopy
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import json
from pathlib import Path
from types import ModuleType
from typing import Any
import xml.etree.ElementTree as ET

from tenderwatch.raw import RawSourceRecord, RecordKind, to_raw
from tenderwatch.sources.artifacts import identify_artifact, load_record, read_document
from tenderwatch.sources.formats import JSONValue, parse_json
from tenderwatch.sources.gencat import read_gencat_execution, read_gencat_main, read_gencat_publication
from tenderwatch.sources.placsp import read_placsp


FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures'
NS = {
    'a': 'http://www.w3.org/2005/Atom',
    'cbc': 'urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2',
    'cac': 'urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2',
    'ext': 'urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2',
    'ebc': 'urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2',
}
ROOT_SELECTION = '$'
BATCH = '/publicacio/dadesPublicacio/contractesAgregada'
MISSING = object()


def json_bytes(value: JSONValue) -> bytes:
    if isinstance(value, Decimal):
        assert value.is_finite()
        return str(value).encode()
    if isinstance(value, list):
        return b'[' + b','.join(json_bytes(item) for item in value) + b']'
    if isinstance(value, dict):
        return b'{' + b','.join(json_bytes(key) + b':' + json_bytes(item) for key, item in value.items()) + b'}'
    return json.dumps(value, ensure_ascii=False, allow_nan=False).encode()


def pointer(value: JSONValue, path: str) -> JSONValue:
    if path in ('', ROOT_SELECTION):
        return value
    assert path.startswith('/'), path
    for component in path[1:].split('/'):
        component = component.replace('~1', '/').replace('~0', '~')
        value = value[int(component)] if isinstance(value, list) else value[component]
    return value


def xml_path(short_path: str) -> str:
    return './' + '/'.join('{' + NS[part.split(':')[0]] + '}' + part.split(':', 1)[1] for part in short_path.split('/'))


CFS = xml_path('ext:ContractFolderStatus')
P_BUDGET = xml_path('ext:ContractFolderStatus/cac:ProcurementProject/cac:BudgetAmount/cbc:TaxExclusiveAmount')
P_ESTIMATE = xml_path('ext:ContractFolderStatus/cac:ProcurementProject/cac:BudgetAmount/cbc:EstimatedOverallContractAmount')


@dataclass(frozen=True)
class Case:
    name: str
    root: Path
    raw: RawSourceRecord
    recipe: tuple[str, ...] = ()

    def payload(self) -> dict[str, JSONValue] | ET.Element:
        return load_record(self.root, self.raw.content)

    def normalize(self, api: ModuleType, *, projection: str | None = None) -> tuple[Any, ...]:
        before = read_document(self.root, self.raw.content)
        envelope = asdict(self.raw)
        calls = []
        views = []

        def resolve(content):
            assert content == self.raw.content, 'Normalizer attempted to resolve another raw occurrence'
            calls.append(content)
            payload = load_record(self.root, content)
            views.append((payload, deepcopy(payload)))
            return payload

        try:
            result = api.normalize(self.raw, resolve=resolve, projection=projection)
        finally:
            assert read_document(self.root, self.raw.content) == before
            assert asdict(self.raw) == envelope
            for payload, snapshot in views:
                if isinstance(payload, ET.Element):
                    assert ET.tostring(payload) == ET.tostring(snapshot)
                else:
                    assert payload == snapshot
        assert isinstance(result, tuple)
        if self.raw.record_kind != RecordKind.PLACSP_TOMBSTONE:
            assert calls, 'Payload assertions must come from the supplied raw occurrence'
        for observation in result:
            assert_contract(observation, self, api)
        return result

    def one(self, api: ModuleType, *, projection: str | None = None) -> Any:
        observation, = self.normalize(api, projection=projection)
        return observation


def pack_placsp_reduction(spec: dict[str, Any]) -> bytes:
    def put(parent: ET.Element, path: str, value: str, **attributes: str) -> ET.Element:
        for part in path.split('/'):
            prefix, local = part.split(':')
            tag = '{' + NS[prefix] + '}' + local
            child = parent.find(tag)
            if child is None:
                child = ET.SubElement(parent, tag)
            parent = child
        parent.text = value
        parent.attrib.update(attributes)
        return parent

    feed = ET.Element('{' + NS['a'] + '}feed')
    entry = ET.SubElement(feed, '{' + NS['a'] + '}entry')
    put(entry, 'a:id', spec['id'])
    put(entry, 'a:updated', spec['updated'])
    cfs = ET.SubElement(entry, '{' + NS['ext'] + '}ContractFolderStatus')
    for key, value in spec.items():
        if ':' in key:
            attributes = {}
            if key.endswith('TaxExclusiveAmount'):
                attributes['currencyID'] = 'EUR'
            elif key == 'ebc:ContractFolderStatusCode':
                attributes = {'languageID': 'es', 'listURI': 'https://contrataciondelestado.es/codice/cl/2.04/SyndicationContractFolderStatusCode-2.04.gc'}
            put(cfs, key, value, **attributes)
        elif key == 'buyer_ID_OC_PLAT':
            put(cfs, 'ext:LocatedContractingParty/cac:Party/cac:PartyIdentification/cbc:ID', value, schemeName='ID_OC_PLAT')
    for number in spec.get('lots', []):
        lot = ET.SubElement(cfs, '{' + NS['cac'] + '}ProcurementProjectLot')
        put(lot, 'cbc:ID', number, schemeName='ID_LOTE')
    for row in spec.get('results', []):
        result = ET.SubElement(cfs, '{' + NS['cac'] + '}TenderResult')
        put(result, 'cbc:ResultCode', row['code'], listURI='http://contrataciondelestado.es/codice/cl/2.09/TenderResultCode-2.09.gc')
        if 'lot' in row:
            put(result, 'cac:AwardedTenderedProject/cbc:ProcurementProjectLotID', row['lot'])
        if 'amount' in row:
            put(result, 'cac:AwardedTenderedProject/cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount', row['amount'], currencyID='EUR')
    return ET.tostring(feed, encoding='utf-8')


class Cases:
    def __init__(self, root: Path):
        self.root = root
        self.counter = 0

    def from_bytes(self, name: str, data: bytes, kind: str, *, ordinal: int = 0, recipe: tuple[str, ...] = (), dataset: str = 'aggregated') -> Case:
        self.counter += 1
        suffix = '.atom' if kind == 'placsp' else '.json'
        relative = f'{self.counter:03d}-{name}{suffix}'
        (self.root / relative).write_bytes(data)
        artifact = identify_artifact(self.root, relative)
        readers = {'main': read_gencat_main, 'execution': read_gencat_execution, 'publication': read_gencat_publication}
        records = list(read_placsp(self.root, artifact, dataset=dataset)) if kind == 'placsp' else list(readers[kind](self.root, artifact))
        return Case(name, self.root, to_raw(records[ordinal]), recipe)

    def get(self, name: str) -> Case:
        existing = {
            'C01-G': ('gencat-main.json', 'main', 0),
            'C01-P002': ('placsp.atom', 'placsp', 1),
            'T01': ('placsp.atom', 'placsp', 0),
            'C19-E0': ('gencat-execution.json', 'execution', 2),
            'C19-E1': ('gencat-execution.json', 'execution', 3),
            'J16': ('gencat-publication.json', 'publication', 0),
            'L07': ('gencat-legacy-excerpt.xml', 'publication', 0),
        }
        if name in existing:
            filename, kind, ordinal = existing[name]
            return self.from_bytes(name, (FIXTURES / filename).read_bytes(), kind, ordinal=ordinal)
        if name in ('C01-P000', 'C07-P001', 'P-native'):
            entry = (FIXTURES / 'normalization' / f'{name}.xml.fragment').read_bytes()
            header = (FIXTURES / 'placsp.atom').read_bytes().split(b'    <author>')[0]
            return self.from_bytes(name, header + entry + b'\n</feed>', 'placsp', dataset='native' if name == 'P-native' else 'aggregated')
        for filename in ('main-cases.json', 'main-regressions.json'):
            catalog = parse_json((FIXTURES / 'normalization' / filename).read_bytes(), filename)
            if name in catalog:
                return self.from_bytes(name, json_bytes([catalog[name]['row']]), 'main')
        catalog = parse_json((FIXTURES / 'normalization/placsp-regressions.json').read_bytes(), 'PLACSP fixture catalogue')['cases']
        if name in catalog:
            return self.from_bytes(name, pack_placsp_reduction(catalog[name]), 'placsp')
        return self.from_bytes(name, (FIXTURES / 'normalization' / f'{name}.json').read_bytes(), 'publication')

    def mutate_json(self, base: Case, path: str, value: JSONValue | object = MISSING) -> Case:
        payload = deepcopy(base.payload())
        assert isinstance(payload, dict)
        parent_path, key = path.rsplit('/', 1)
        parent = pointer(payload, parent_path)
        key = int(key) if isinstance(parent, list) else key.replace('~1', '/').replace('~0', '~')
        if value is MISSING:
            del parent[key]
        else:
            parent[key] = value
        kind = {RecordKind.GENCAT_MAIN_ROW: 'main', RecordKind.GENCAT_EXECUTION_ROW: 'execution', RecordKind.GENCAT_PUBLICATION_JSON: 'publication'}[base.raw.record_kind]
        body = payload if kind == 'publication' else [payload]
        recipe = (base.raw.content.document_sha256, path, 'delete' if value is MISSING else 'replace')
        return self.from_bytes(base.name + '-synthetic', json_bytes(body), kind, recipe=recipe)

    def mutate_xml(self, base: Case, path: str, change: Callable[[ET.Element, ET.Element], None]) -> Case:
        entry = deepcopy(base.payload())
        node = entry.find(path)
        assert node is not None, path
        change(entry, node)
        feed = ET.Element('{' + NS['a'] + '}feed')
        feed.append(entry)
        return self.from_bytes(base.name + '-synthetic', ET.tostring(feed, encoding='utf-8'), 'placsp', dataset=base.raw.dataset, recipe=(base.raw.content.document_sha256, path, 'XML mutation'))


def ids(identifiers: Iterable[Any]) -> list[str]:
    return [identifier.value for identifier in identifiers]


def issue(observation: Any, code: str, path: str) -> None:
    assert any(item.code == code and item.path == 'raw:' + path for item in observation.issues), (code, path)


def financial(observation: Any, path: str, *, purpose: str, amount: str | None, tax: str, scope: str, currency: str | None = None, state: str = 'valid') -> Any:
    item, = [item for item in observation.financials if item.source_path == path]
    assert item.scope.kind == scope
    money = item.value
    assert (money.purpose, money.tax_basis, money.currency, money.value_state) == (purpose, tax, currency, state)
    assert money.value == (Decimal(amount) if amount is not None else None)
    return item


def walk(value: Any) -> Iterable[Any]:
    yield value
    if is_dataclass(value):
        for field in fields(value):
            yield from walk(getattr(value, field.name))
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from walk(item)


def semantic(observation: Any) -> dict[str, Any]:
    occurrences: Counter[str] = Counter()
    keys = {}
    for item in walk(observation):
        if is_dataclass(item) and hasattr(item, 'key'):
            label = type(item).__name__ + ':' + item.source_path
            keys[item.key] = f'{label}#{occurrences[label]}'
            occurrences[label] += 1

    def comparable(value: Any, field: str = '') -> Any:
        if is_dataclass(value):
            return {item.name: comparable(getattr(value, item.name), item.name) for item in fields(value) if item.name not in ('observation_id', 'raw_source_record_id')}
        if isinstance(value, tuple):
            return tuple(comparable(item, field) for item in value)
        if field in ('key', 'lot_keys', 'publication_keys', 'outcome_keys') and isinstance(value, str):
            return keys[value]
        if field == 'namespace' and isinstance(value, str):
            return value.replace(observation.raw_source_record_id, '$raw')
        return value

    return comparable(observation)


def source_at(payload: dict[str, JSONValue] | ET.Element, path: str) -> Any:
    if path == ROOT_SELECTION:
        return payload
    if path.startswith('paths:'):
        return [source_at(payload, part) for part in json.loads(path[6:])]
    if '#token=' in path:
        base, position = path.rsplit('#token=', 1)
        return source_at(payload, base).split('||')[int(position)]
    if isinstance(payload, dict):
        return pointer(payload, path)
    if '/@' in path:
        base, attribute = path.rsplit('/@', 1)
        element = payload.find(base)
        assert element is not None, path
        return element.attrib[attribute]
    element = payload.find(path)
    assert element is not None, path
    return element


def assert_stable(before: Any, after: Any, names: tuple[str, ...]) -> None:
    first, second = semantic(before), semantic(after)
    for name in names:
        assert first[name] == second[name], name


def assert_contract(observation: Any, case: Case, api: ModuleType) -> None:
    assert isinstance(observation, api.NormalizedObservation)
    assert is_dataclass(observation) and observation.__dataclass_params__.frozen
    assert observation.raw_source_record_id == case.raw.raw_record_id
    assert observation.source.system == case.raw.source
    assert observation.source.dataset == case.raw.dataset
    assert observation.schema_version == api.SCHEMA_VERSION and observation.schema_version
    assert observation.mapping_version == api.MAPPING_VERSION and observation.mapping_version
    assert isinstance(observation.observation_id, str) and observation.observation_id
    assert observation.projection_locator == ROOT_SELECTION or observation.projection_locator.startswith(BATCH + '/')
    expected_fields = {
        'observation_id', 'raw_source_record_id', 'projection_locator', 'schema_version', 'mapping_version',
        'source', 'source_markers', 'subject_kind', 'focus', 'procedure_identifiers', 'procedure_numbers',
        'batch_identifiers', 'member_identifiers', 'related_identifiers', 'titles', 'descriptions', 'buyer',
        'contract_type', 'mixed_contract', 'procurement_method', 'procurement_attributes', 'statuses',
        'classifications', 'financials', 'deadlines', 'execution_locations', 'performance_periods', 'lots',
        'publications', 'outcomes', 'awards', 'execution_actions', 'documents', 'source_references', 'coverage', 'issues',
    }
    assert {field.name for field in fields(observation)} == expected_fields
    items = [value for value in walk(observation) if is_dataclass(value)]
    keys = [value.key for value in items if hasattr(value, 'key')]
    assert len(keys) == len(set(keys)) and all(keys)
    targets = {'lot_keys': {lot.key for lot in observation.lots}, 'publication_keys': {pub.key for pub in observation.publications}, 'outcome_keys': {outcome.key for outcome in observation.outcomes}}
    payload = case.payload()
    for item in items:
        assert item.__dataclass_params__.frozen
        for field, available in targets.items():
            if hasattr(item, field):
                assert set(getattr(item, field)) <= available
        if hasattr(item, 'source_path'):
            assert isinstance(item.source_path, str) and item.source_path
            source_at(payload, item.source_path)
            paths = json.loads(item.source_path[6:]) if item.source_path.startswith('paths:') else [item.source_path]
            for path in paths:
                if path.startswith(BATCH + '/'):
                    selected = observation.projection_locator
                    assert selected.startswith(BATCH + '/')
                    assert path == selected or path.startswith(selected + '/'), 'Sibling batch facts leaked into this projection'
        if hasattr(item, 'value_state'):
            assert (item.value is not None) == (item.value_state == 'valid')
            if item.value is not None:
                assert isinstance(item.value, Decimal) and item.value.is_finite()
            assert isinstance(item.raw_value, str)
        if hasattr(item, 'lot_keys'):
            if item.kind == 'lots':
                assert item.lot_keys or item.source_lot_identifiers
            else:
                assert not item.lot_keys and not item.source_lot_identifiers
        if hasattr(item, 'zone_basis'):
            assert item.local_date is None or type(item.local_date) is date
            assert item.local_time is None or type(item.local_time) is time
            assert item.offset is None or isinstance(item.offset, timedelta)
            if item.utc_instant is not None:
                assert isinstance(item.utc_instant, datetime) and item.utc_instant.utcoffset() == timedelta(0)
            if item.precision == 'day' or item.zone_basis == 'unknown':
                assert item.utc_instant is None
            if item.precision == 'day':
                assert item.local_time is None
    assert all(isinstance(value, str) and value for value in ids(observation.procedure_identifiers))
    assert all(identifier.role == 'procedure' for identifier in observation.procedure_identifiers)
    assert all(identifier.role == 'record' for identifier in observation.source.record_identifiers)
    assert all(identifier.role == 'procedure_number' for identifier in observation.procedure_numbers)
    assert all(identifier.role == 'batch' for identifier in observation.batch_identifiers)
    assert all(identifier.role == 'member' for identifier in observation.member_identifiers)
    for value in walk(observation):
        assert not isinstance(value, (float, dict, list)), 'Normalized output must be typed and deeply immutable'
        assert is_dataclass(value) or isinstance(value, (type(None), str, int, Decimal, date, time, timedelta, tuple)), type(value)
    for diagnostic in observation.issues:
        assert diagnostic.code and diagnostic.path.startswith('raw:') and diagnostic.detail
        assert all(field.value not in diagnostic.detail for field in case.raw.source_urls if '/json-xifrat/' in field.value)
    api.validate_observation(observation)
