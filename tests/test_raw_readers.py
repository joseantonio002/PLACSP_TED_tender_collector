from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from tenderwatch.raw import RecordKind, RecordLocator, to_raw
from tenderwatch.sources.artifacts import identify_artifact, load_record, read_document
from tenderwatch.sources.errors import ArtifactReadError, IntegrityError, LocatorError, SourceFormatError
from tenderwatch.sources.gencat import read_gencat_execution, read_gencat_main, read_gencat_publication
from tenderwatch.sources.placsp import ATOM, TOMB, read_placsp


FIXTURES = Path(__file__).parent / 'fixtures'


def test_placsp_reader_and_namespace_context():
    artifact = identify_artifact(FIXTURES, 'placsp.atom')
    tombstone, entry = list(read_placsp(FIXTURES, artifact, dataset='aggregated'))
    assert tombstone.record_kind == RecordKind.PLACSP_TOMBSTONE
    assert entry.record_kind == RecordKind.PLACSP_ATOM_ENTRY
    assert entry.content.locator == RecordLocator('xml-child', ordinal=0, xml_tag=ATOM + 'entry')
    assert tombstone.content.locator.xml_tag == TOMB + 'deleted-entry'
    assert entry.source_identifiers[0].value.endswith('/20283724')
    assert entry.source_timestamps[0].value == '2026-09-21T22:00:26.651+02:00'
    assert read_document(FIXTURES, entry.content) == (FIXTURES / 'placsp.atom').read_bytes()
    element = load_record(FIXTURES, entry.content)
    assert element.tag == ATOM + 'entry'
    assert element.find('.//{urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2}ContractFolderID').text == '905451/26'
    assert load_record(FIXTURES, tombstone.content).get('ref').endswith('/7816066')


def test_zip_visits_every_member_and_preserves_duplicate_names(tmp_path):
    data = (FIXTURES / 'placsp.atom').read_bytes()
    path = tmp_path / 'retained.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('head.atom', data)
        archive.writestr('unreachable-2021.atom', data)
        with pytest.warns(UserWarning, match='Duplicate name'):
            archive.writestr('head.atom', data)
    artifact = identify_artifact(tmp_path, path.name)
    records = list(read_placsp(tmp_path, artifact, dataset='native'))
    assert len(records) == 6
    assert [r.content.locator.member_index for r in records] == [0, 0, 1, 1, 2, 2]
    assert len({to_raw(r).raw_record_id for r in records}) == 6
    assert read_document(tmp_path, records[-1].content) == data


def test_execution_reader_preserves_rows_and_no_join():
    artifact = identify_artifact(FIXTURES, 'gencat-execution.json')
    records = list(read_gencat_execution(FIXTURES, artifact))
    rows = json.loads((FIXTURES / artifact.path).read_bytes())
    assert len(records) == 5
    for ordinal, (record, row) in enumerate(zip(records, rows, strict=True)):
        assert record.record_kind == RecordKind.GENCAT_EXECUTION_ROW
        assert record.content.locator == RecordLocator('json-row', ordinal=ordinal)
        assert load_record(FIXTURES, record.content) == row
    assert records[2].source_urls == records[3].source_urls
    assert to_raw(records[2]).raw_record_id != to_raw(records[3]).raw_record_id
    assert load_record(FIXTURES, records[1].content)['import_sense_iva'] == '140030.610000000000000000'


def test_main_reader_and_raw_conversion():
    artifact = identify_artifact(FIXTURES, 'gencat-main.json')
    source, = read_gencat_main(FIXTURES, artifact)
    raw = to_raw(source)
    assert raw.record_kind == RecordKind.GENCAT_MAIN_ROW
    assert raw.dataset == 'ybgg-dgi6'
    row = load_record(FIXTURES, raw.content)
    assert row == json.loads((FIXTURES / artifact.path).read_bytes())[0]
    assert dict((field.path, field.value) for field in raw.source_identifiers)['/id_intern'] == row['id_intern']
    assert dict((field.path, field.value) for field in raw.source_timestamps)['/:updated_at'] == row[':updated_at']
    assert raw.content.locator.ordinal == 0
    assert read_document(FIXTURES, raw.content) == (FIXTURES / artifact.path).read_bytes()


@pytest.mark.parametrize('filename,kind', [
    ('gencat-publication.json', RecordKind.GENCAT_PUBLICATION_JSON),
    ('gencat-batch-excerpt.json', RecordKind.GENCAT_PUBLICATION_JSON),
    ('gencat-legacy-excerpt.xml', RecordKind.GENCAT_PUBLICATION_XML),
])
def test_publication_is_one_whole_occurrence(filename, kind, tmp_path):
    data = (FIXTURES / filename).read_bytes()
    (tmp_path / 'advertised-json.json').write_bytes(data)
    artifact = identify_artifact(tmp_path, 'advertised-json.json')
    source, = read_gencat_publication(tmp_path, artifact)
    raw = to_raw(source)
    assert raw.record_kind == kind
    assert raw.content.locator == RecordLocator('document')
    assert read_document(tmp_path, raw.content) == data
    assert raw.source_identifiers == source.source_identifiers
    assert raw.schema == source.schema
    if filename == 'gencat-batch-excerpt.json':
        members = load_record(tmp_path, raw.content)['publicacio']['dadesPublicacio']['contractesAgregada']
        assert len(members) == 3
        assert members[1]['expedient'] == members[2]['expedient']
        assert members[0]['importAdjudicacioSenseIva'] == Decimal('28957.25')
    elif kind == RecordKind.GENCAT_PUBLICATION_XML:
        assert raw.content.format == 'xml'
        assert raw.schema[0].value == '1.05b'
        assert b'<![CDATA[]]>' in read_document(tmp_path, raw.content)


def test_unusual_values_unknown_fields_and_duplicate_occurrences(tmp_path):
    body = b'[{"id_intern":" 001_0 ","procediment":"unknown","money":"||","empty":"","nil":null,"extra":{"number":1.2300}}, {"id_intern":" 001_0 ","procediment":"unknown"}]'
    (tmp_path / 'page.json').write_bytes(body)
    artifact = identify_artifact(tmp_path, 'page.json')
    first, second = list(read_gencat_main(tmp_path, artifact))
    raw = to_raw(first)
    row = load_record(tmp_path, raw.content)
    assert row['id_intern'] == ' 001_0 '
    assert row['empty'] == '' and row['nil'] is None
    assert row['extra']['number'] == Decimal('1.2300')
    assert row['money'] == '||'
    assert read_document(tmp_path, raw.content) == body
    assert raw.raw_record_id != to_raw(second).raw_record_id
    (tmp_path / 'page.json').unlink()
    assert to_raw(first) == raw


def test_xml_prefixes_nested_entries_and_whitespace(tmp_path):
    body = b'<a:feed xmlns:a="http://www.w3.org/2005/Atom" xmlns:x="urn:unknown" xml:lang="ca"><x:entry/><a:entry><a:id> id </a:id><x:unknown value=" 0 "><a:entry/></x:unknown></a:entry><a:entry><a:id> id </a:id></a:entry></a:feed>'
    (tmp_path / 'page.atom').write_bytes(body)
    artifact = identify_artifact(tmp_path, 'page.atom')
    records = list(read_placsp(tmp_path, artifact, dataset='native'))
    assert len(records) == 2
    assert [r.content.locator.ordinal for r in records] == [0, 1]
    assert records[0].source_identifiers[0].value == ' id '
    assert read_document(tmp_path, records[0].content) == body
    assert load_record(tmp_path, records[0].content).find('{urn:unknown}unknown').attrib['value'] == ' 0 '


def test_xml_and_zip_invalid_locators(tmp_path):
    with zipfile.ZipFile(tmp_path / 'test.zip', 'w') as archive:
        archive.writestr('feed.atom', (FIXTURES / 'placsp.atom').read_bytes())
    source = next(read_placsp(tmp_path, identify_artifact(tmp_path, 'test.zip'), dataset='native'))
    for locator in (
        replace(source.content.locator, member_index=99),
        replace(source.content.locator, member_name='missing.atom'),
        replace(source.content.locator, ordinal=99),
        replace(source.content.locator, xml_tag='{urn:wrong}entry'),
    ):
        with pytest.raises(LocatorError):
            load_record(tmp_path, replace(source.content, locator=locator))
    with pytest.raises(IntegrityError):
        read_document(tmp_path, replace(source.content, document_sha256='0' * 64))


def test_raw_factory_is_pure_deterministic_and_immutable():
    artifact = identify_artifact(FIXTURES, 'gencat-execution.json')
    source = next(read_gencat_execution(FIXTURES, artifact))
    raw = to_raw(source)
    assert raw == to_raw(source)
    assert raw.source == 'gencat'
    assert raw.dataset == '8idu-wkjv'
    assert raw.content is source.content
    assert raw.source_identifiers == source.source_identifiers
    assert raw.source_timestamps == source.source_timestamps
    assert raw.observed_at is None
    assert raw.content.artifact.sha256 == hashlib.sha256((FIXTURES / artifact.path).read_bytes()).hexdigest()
    assert not hasattr(raw, 'canonical_procedure_id')
    assert not hasattr(raw, 'status')
    with pytest.raises(FrozenInstanceError):
        raw.dataset = 'other'
    with pytest.raises(FrozenInstanceError):
        raw.content.artifact.path = 'other'
    value = load_record(FIXTURES, raw.content)
    value[':id'] = 'changed'
    assert load_record(FIXTURES, raw.content)[':id'] == 'row-f8sk.dbiy.7gg6'


@pytest.mark.parametrize('name,body,reader', [
    ('bad.zip', b'not a zip', read_placsp),
    ('bad.atom', b'<feed>', read_placsp),
    ('bad.json', b'[', read_gencat_main),
    ('bad.json', b'{"rows": []}', read_gencat_main),
    ('bad.json', b'[1]', read_gencat_execution),
    ('bad.bin', b'<html/>', read_gencat_publication),
    ('bad.json', b'{', read_gencat_publication),
    ('bad.json', b'{"publicacio":[]}', read_gencat_publication),
    ('bad.atom', b'<!DOCTYPE feed [<!ENTITY x "expanded">]><feed/>', read_placsp),
    ('bad.json', b'[{"value":NaN}]', read_gencat_main),
])
def test_format_failures(tmp_path, name, body, reader):
    (tmp_path / name).write_bytes(body)
    artifact = identify_artifact(tmp_path, name)
    kwargs = {'dataset': 'aggregated'} if reader is read_placsp else {}
    with pytest.raises(SourceFormatError):
        list(reader(tmp_path, artifact, **kwargs))


def test_missing_changed_artifact_and_invalid_locator(tmp_path):
    with pytest.raises(ArtifactReadError):
        identify_artifact(tmp_path, 'missing.json')
    path = tmp_path / 'page.json'
    path.write_bytes((FIXTURES / 'gencat-execution.json').read_bytes())
    artifact = identify_artifact(tmp_path, path.name)
    source = next(read_gencat_execution(tmp_path, artifact))
    with pytest.raises(LocatorError):
        load_record(tmp_path, replace(source.content, locator=RecordLocator('json-row', ordinal=999)))
    with pytest.raises(LocatorError):
        RecordLocator('json-row', ordinal=-1)
    path.write_bytes(b'[]')
    with pytest.raises(IntegrityError):
        load_record(tmp_path, source.content)
