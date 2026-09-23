from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
from typing import Iterator
import xml.etree.ElementTree as ET

from tenderwatch.raw import Artifact, ContentReference, RecordKind, RecordLocator, SourceField, SourceRecord
from tenderwatch.sources.artifacts import open_artifact, open_zip, read_member
from tenderwatch.sources.errors import UnsupportedFormatError
from tenderwatch.sources.formats import parse_xml


ATOM = '{http://www.w3.org/2005/Atom}'
TOMB = '{http://purl.org/atompub/tombstones/1.0}'


def _text_fields(element: ET.Element, names: tuple[str, ...]) -> tuple[SourceField, ...]:
    return tuple(
        SourceField(name, child.text or '')
        for name in names for child in element.findall(name)
    )


def _feed_records(
    data: bytes, artifact: Artifact, dataset: str,
    member_name: str | None = None, member_index: int | None = None,
) -> Iterator[SourceRecord]:
    root = parse_xml(data, f'{artifact.path}:{member_name}')
    if root.tag != ATOM + 'feed':
        raise UnsupportedFormatError(f'Expected an Atom feed: {artifact.path}:{member_name}')
    document_sha256 = hashlib.sha256(data).hexdigest()
    ordinals: Counter[str] = Counter()
    for element in root:
        if element.tag not in (ATOM + 'entry', TOMB + 'deleted-entry'):
            continue
        locator = RecordLocator('xml-child', ordinals[element.tag], element.tag, member_name, member_index)
        ordinals[element.tag] += 1
        tombstone = element.tag == TOMB + 'deleted-entry'
        if tombstone:
            identifiers = (SourceField('@ref', element.attrib['ref']),) if 'ref' in element.attrib else ()
            timestamps = (SourceField('@when', element.attrib['when']),) if 'when' in element.attrib else ()
        else:
            identifiers = _text_fields(element, (ATOM + 'id',))
            timestamps = _text_fields(element, (ATOM + 'updated', ATOM + 'published'))
        yield SourceRecord(
            source='placsp', dataset=dataset,
            record_kind=RecordKind.PLACSP_TOMBSTONE if tombstone else RecordKind.PLACSP_ATOM_ENTRY,
            content=ContentReference(artifact, locator, 'xml', document_sha256),
            source_identifiers=identifiers, source_timestamps=timestamps,
            source_urls=tuple(SourceField(ATOM + 'link/@href', node.attrib['href']) for node in element.findall(ATOM + 'link') if 'href' in node.attrib),
            schema=(SourceField('root_tag', root.tag),),
        )


def read_placsp(root: Path, artifact: Artifact, *, dataset: str) -> Iterator[SourceRecord]:
    with open_artifact(root, artifact) as stream:
        if Path(artifact.path).suffix.lower() == '.zip':
            with open_zip(stream, artifact.path) as archive:
                found = False
                for index, member in enumerate(archive.infolist()):
                    if not member.is_dir() and Path(member.filename).suffix.lower() in ('.atom', '.xml'):
                        found = True
                        yield from _feed_records(read_member(archive, member), artifact, dataset, member.filename, index)
                if not found:
                    raise UnsupportedFormatError(f'ZIP contains no Atom/XML members: {artifact.path}')
        else:
            yield from _feed_records(stream.read(), artifact, dataset)
