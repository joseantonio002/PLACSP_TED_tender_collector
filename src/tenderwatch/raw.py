from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from enum import StrEnum
import hashlib
import json
from typing import Literal

from tenderwatch.sources.errors import LocatorError


class RecordKind(StrEnum):
    PLACSP_ATOM_ENTRY = 'placsp_atom_entry'
    PLACSP_TOMBSTONE = 'placsp_tombstone'
    GENCAT_MAIN_ROW = 'gencat_main_row'
    GENCAT_EXECUTION_ROW = 'gencat_execution_row'
    GENCAT_PUBLICATION_JSON = 'gencat_publication_json'
    GENCAT_PUBLICATION_XML = 'gencat_publication_xml'


@dataclass(frozen=True, slots=True)
class ManifestLine:
    path: str
    line_number: int
    sha256: str


@dataclass(frozen=True, slots=True)
class Acquisition:
    manifest_line: ManifestLine
    source_url: str | None
    resolved_url: str | None
    downloaded_at: str | None
    download_started_at: str | None
    annotations: tuple[ManifestLine, ...] = ()


@dataclass(frozen=True, slots=True)
class Artifact:
    path: str
    sha256: str
    size_bytes: int
    acquisition: Acquisition | None = None


@dataclass(frozen=True, slots=True)
class RecordLocator:
    kind: Literal['document', 'json-row', 'xml-child']
    ordinal: int | None = None
    xml_tag: str | None = None
    member_name: str | None = None
    member_index: int | None = None

    def __post_init__(self) -> None:
        if self.kind not in ('document', 'json-row', 'xml-child'):
            raise LocatorError(f'Unknown locator kind: {self.kind}')
        if self.kind == 'document':
            if self.ordinal is not None or self.xml_tag is not None:
                raise LocatorError('Document locators cannot select a child')
        elif type(self.ordinal) is not int or self.ordinal < 0:
            raise LocatorError('Record ordinal must be a nonnegative integer')
        if (self.kind == 'xml-child') != (self.xml_tag is not None):
            raise LocatorError('Only XML child locators require an expanded XML tag')
        if (self.member_name is None) != (self.member_index is None):
            raise LocatorError('ZIP member name and central-directory index are both required')
        if self.member_index is not None and (type(self.member_index) is not int or self.member_index < 0):
            raise LocatorError('ZIP member index must be a nonnegative integer')


@dataclass(frozen=True, slots=True)
class ContentReference:
    artifact: Artifact
    locator: RecordLocator
    format: Literal['json', 'xml']
    document_sha256: str


@dataclass(frozen=True, slots=True)
class SourceField:
    path: str
    value: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceRecord:
    source: Literal['placsp', 'gencat']
    dataset: str
    record_kind: RecordKind
    content: ContentReference
    source_identifiers: tuple[SourceField, ...] = ()
    source_timestamps: tuple[SourceField, ...] = ()
    source_urls: tuple[SourceField, ...] = ()
    schema: tuple[SourceField, ...] = ()
    context_artifacts: tuple[Artifact, ...] = ()

    @property
    def observed_at(self) -> str | None:
        acquisition = self.content.artifact.acquisition
        return acquisition.downloaded_at if acquisition else None


@dataclass(frozen=True, slots=True, kw_only=True)
class RawSourceRecord(SourceRecord):
    raw_record_id: str


def to_raw(record: SourceRecord) -> RawSourceRecord:
    artifact = record.content.artifact
    acquisition = artifact.acquisition
    identity = [
        'tenderwatch.raw.v1', record.source, record.dataset, record.record_kind,
        artifact.path, artifact.sha256,
        asdict(acquisition.manifest_line) if acquisition else None,
        asdict(record.content.locator),
    ]
    digest = hashlib.sha256(json.dumps(identity, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    return RawSourceRecord(
        raw_record_id='raw:v1:' + digest,
        **{field.name: getattr(record, field.name) for field in fields(SourceRecord)},
    )
