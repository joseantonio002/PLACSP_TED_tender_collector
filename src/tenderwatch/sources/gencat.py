from __future__ import annotations

from pathlib import Path
from typing import Iterator

from tenderwatch.raw import Artifact, ContentReference, RecordKind, RecordLocator, SourceField, SourceRecord
from tenderwatch.sources.artifacts import open_artifact
from tenderwatch.sources.errors import SourceFormatError, UnsupportedFormatError
from tenderwatch.sources.formats import JSONValue, parse_json, parse_xml


def _fields(row: dict[str, JSONValue], names: tuple[str, ...]) -> tuple[SourceField, ...]:
    return tuple(SourceField('/' + name, row[name]) for name in names if isinstance(row.get(name), str))


def _urls(row: dict[str, JSONValue]) -> tuple[SourceField, ...]:
    found = []
    for key, value in row.items():
        if key == 'enllac_publicacio' or key.startswith('url_json'):
            if isinstance(value, str):
                found.append(SourceField('/' + key, value))
            elif isinstance(value, dict) and isinstance(value.get('url'), str):
                found.append(SourceField('/' + key + '/url', value['url']))
    return tuple(found)


def _read_table(
    root: Path, artifact: Artifact, dataset: str, record_kind: RecordKind,
    context_artifacts: tuple[Artifact, ...],
) -> Iterator[SourceRecord]:
    with open_artifact(root, artifact) as stream:
        rows = parse_json(stream.read(), artifact.path)
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise SourceFormatError(f'Expected a Socrata array of row objects: {artifact.path}')
    for ordinal, row in enumerate(rows):
        yield SourceRecord(
            source='gencat', dataset=dataset, record_kind=record_kind,
            content=ContentReference(artifact, RecordLocator('json-row', ordinal), 'json', artifact.sha256),
            source_identifiers=_fields(row, (':id', 'id_intern', 'codi_expedient')),
            source_timestamps=_fields(row, (':created_at', ':updated_at')),
            source_urls=_urls(row), context_artifacts=context_artifacts,
        )


def read_gencat_main(
    root: Path, artifact: Artifact, *, context_artifacts: tuple[Artifact, ...] = (),
) -> Iterator[SourceRecord]:
    yield from _read_table(root, artifact, 'ybgg-dgi6', RecordKind.GENCAT_MAIN_ROW, context_artifacts)


def read_gencat_execution(
    root: Path, artifact: Artifact, *, context_artifacts: tuple[Artifact, ...] = (),
) -> Iterator[SourceRecord]:
    yield from _read_table(root, artifact, '8idu-wkjv', RecordKind.GENCAT_EXECUTION_ROW, context_artifacts)


def read_gencat_publication(root: Path, artifact: Artifact) -> Iterator[SourceRecord]:
    with open_artifact(root, artifact) as stream:
        data = stream.read()
    prefix = data.removeprefix(b'\xef\xbb\xbf').lstrip()
    if prefix.startswith(b'<'):
        element = parse_xml(data, artifact.path)
        if element.tag != 'Notice':
            raise UnsupportedFormatError(f'Expected a legacy PSCP Notice: {artifact.path}')
        identifiers = tuple(
            SourceField(path, node.text or '')
            for path in ('tenderingSpaceId', 'com.capgemini.gencat.economia.pscp.entity.PscpContractNotice/contractNoticeId')
            for node in element.findall(path)
        )
        schema = tuple(SourceField('codiceVersion', node.text or '') for node in element.findall('codiceVersion'))
        kind, format_name = RecordKind.GENCAT_PUBLICATION_XML, 'xml'
    elif prefix.startswith(b'{'):
        value = parse_json(data, artifact.path)
        if not isinstance(value, dict) or not isinstance(value.get('publicacio'), dict):
            raise UnsupportedFormatError(f'Expected a modern PSCP publication object: {artifact.path}')
        identifiers = _fields(value, ('idExpedient', 'codiExpedient'))
        schema = _fields(value, ('versio',))
        kind, format_name = RecordKind.GENCAT_PUBLICATION_JSON, 'json'
    else:
        raise UnsupportedFormatError(f'Unrecognized retained PSCP body format: {artifact.path}')
    yield SourceRecord(
        source='gencat', dataset='pscp-publications', record_kind=kind,
        content=ContentReference(artifact, RecordLocator('document'), format_name, artifact.sha256),
        source_identifiers=identifiers, schema=schema,
    )
