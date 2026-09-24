from __future__ import annotations

from contextlib import ExitStack, contextmanager
import hashlib
from pathlib import Path
from typing import BinaryIO, Callable, Iterator
import xml.etree.ElementTree as ET
import zipfile
import zlib

from tenderwatch.raw import Acquisition, Artifact, ContentReference, ManifestLine
from tenderwatch.sources.errors import ArtifactReadError, IntegrityError, LocatorError, SourceFormatError, UnsupportedFormatError
from tenderwatch.sources.formats import JSONValue, parse_json, parse_xml


def artifact_path(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise LocatorError(f'Artifact path must be relative to the data root: {relative}')
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise LocatorError(f'Artifact path escapes the data root: {relative}')
    return resolved


def identify_artifact(
    root: Path, relative: str, *, expected_sha256: str | None = None,
    expected_size: int | None = None, acquisition: Acquisition | None = None,
) -> Artifact:
    path = artifact_path(root, relative)
    try:
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            size = stream.seek(0, 2)
    except OSError as exc:
        raise ArtifactReadError(f'Cannot read artifact: {relative}') from exc
    if expected_sha256 is not None and digest != expected_sha256:
        raise IntegrityError(f'Artifact checksum mismatch: {relative}')
    if expected_size is not None and size != expected_size:
        raise IntegrityError(f'Artifact size mismatch: {relative}')
    return Artifact(relative, digest, size, acquisition)


@contextmanager
def open_artifact(root: Path, artifact: Artifact) -> Iterator[BinaryIO]:
    path = artifact_path(root, artifact.path)
    try:
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if digest != artifact.sha256 or stream.seek(0, 2) != artifact.size_bytes:
                raise IntegrityError(f'Artifact changed: {artifact.path}')
            stream.seek(0)
            yield stream
    except OSError as exc:
        raise ArtifactReadError(f'Cannot read artifact: {artifact.path}') from exc


@contextmanager
def open_zip(stream: BinaryIO, label: str) -> Iterator[zipfile.ZipFile]:
    try:
        with zipfile.ZipFile(stream) as archive:
            yield archive
    except (zipfile.BadZipFile, EOFError, zlib.error) as exc:
        raise SourceFormatError(f'Corrupt ZIP: {label}') from exc


def read_member(archive: zipfile.ZipFile, member: zipfile.ZipInfo) -> bytes:
    if member.flag_bits & 1:
        raise UnsupportedFormatError(f'Encrypted ZIP member: {member.filename}')
    try:
        return archive.read(member)
    except NotImplementedError as exc:
        raise UnsupportedFormatError(f'Unsupported ZIP compression: {member.filename}') from exc


def read_document(root: Path, content: ContentReference) -> bytes:
    locator = content.locator
    with open_artifact(root, content.artifact) as stream:
        if locator.member_index is None:
            data = stream.read()
        else:
            with open_zip(stream, content.artifact.path) as archive:
                members = archive.infolist()
                if locator.member_index >= len(members):
                    raise LocatorError('ZIP member index is out of range')
                member = members[locator.member_index]
                if member.filename != locator.member_name or member.is_dir():
                    raise LocatorError('ZIP member does not match the locator')
                data = read_member(archive, member)
    if hashlib.sha256(data).hexdigest() != content.document_sha256:
        raise IntegrityError('Containing document checksum mismatch')
    return data


def load_record(root: Path, content: ContentReference) -> dict[str, JSONValue] | ET.Element:
    data = read_document(root, content)
    locator = content.locator
    if content.format == 'json':
        value = parse_json(data, content.artifact.path)
        if locator.kind == 'json-row':
            if not isinstance(value, list) or locator.ordinal >= len(value):
                raise LocatorError('JSON row locator is out of range or not an array')
            value = value[locator.ordinal]
        elif locator.kind != 'document':
            raise LocatorError('XML locator cannot select a JSON record')
        if not isinstance(value, dict):
            raise LocatorError('JSON record locator does not select an object')
        return value
    if content.format != 'xml':
        raise UnsupportedFormatError(f'Unsupported content format: {content.format}')
    element = parse_xml(data, content.artifact.path)
    if locator.kind == 'document':
        return element
    if locator.kind != 'xml-child':
        raise LocatorError('JSON locator cannot select an XML record')
    matches = [child for child in element if child.tag == locator.xml_tag]
    if locator.ordinal >= len(matches):
        raise LocatorError('XML child locator is out of range')
    return matches[locator.ordinal]


@contextmanager
def verified_resolver(root: Path, artifact: Artifact) -> Iterator[Callable[[ContentReference], dict[str, JSONValue] | ET.Element]]:
    with ExitStack() as stack:
        stream = stack.enter_context(open_artifact(root, artifact))
        archive = None
        cached_key = None
        document: JSONValue | ET.Element = None
        digest = None
        children: dict[str, list[ET.Element]] = {}

        def resolve(content: ContentReference) -> dict[str, JSONValue] | ET.Element:
            nonlocal archive, cached_key, document, digest, children
            if content.artifact != artifact:
                raise LocatorError('Resolver is restricted to one verified artifact')
            locator = content.locator
            cache_key = (locator.member_index, locator.member_name, content.format)
            if cached_key != cache_key:
                cached_key = None
                if locator.member_index is None:
                    stream.seek(0)
                    data = stream.read()
                else:
                    if archive is None:
                        archive = stack.enter_context(open_zip(stream, artifact.path))
                    members = archive.infolist()
                    if locator.member_index >= len(members):
                        raise LocatorError('ZIP member index is out of range')
                    member = members[locator.member_index]
                    if member.filename != locator.member_name or member.is_dir():
                        raise LocatorError('ZIP member does not match the locator')
                    data = read_member(archive, member)
                digest = hashlib.sha256(data).hexdigest()
                if digest != content.document_sha256:
                    raise IntegrityError('Containing document checksum mismatch')
                if content.format == 'json':
                    document = parse_json(data, artifact.path)
                elif content.format == 'xml':
                    document = parse_xml(data, artifact.path)
                else:
                    raise UnsupportedFormatError(f'Unsupported content format: {content.format}')
                children = {}
                if isinstance(document, ET.Element):
                    for child in document:
                        children.setdefault(child.tag, []).append(child)
                cached_key = cache_key
            if digest != content.document_sha256:
                raise IntegrityError('Containing document checksum mismatch')
            selected = document
            if locator.kind == 'json-row':
                if content.format != 'json' or not isinstance(document, list) or locator.ordinal >= len(document):
                    raise LocatorError('JSON row locator is out of range or not an array')
                selected = document[locator.ordinal]
            elif locator.kind == 'xml-child':
                matches = children.get(locator.xml_tag, ())
                if content.format != 'xml' or locator.ordinal >= len(matches):
                    raise LocatorError('XML child locator is out of range')
                selected = matches[locator.ordinal]
            if not isinstance(selected, (dict, ET.Element)):
                raise LocatorError('Record locator does not select an object or XML element')
            return selected

        yield resolve


def read_manifest_line(root: Path, reference: ManifestLine) -> dict[str, JSONValue]:
    if reference.line_number < 1:
        raise LocatorError('Manifest line numbers are one-based')
    path = artifact_path(root, reference.path)
    try:
        with path.open('rb') as stream:
            for number, line in enumerate(stream, 1):
                if number == reference.line_number:
                    if hashlib.sha256(line).hexdigest() != reference.sha256:
                        raise IntegrityError('Manifest line checksum mismatch')
                    value = parse_json(line, f'{reference.path}:{number}')
                    if not isinstance(value, dict):
                        raise SourceFormatError('Manifest entry must be an object')
                    return value
    except OSError as exc:
        raise ArtifactReadError(f'Cannot read manifest: {reference.path}') from exc
    raise LocatorError('Manifest line is out of range')
