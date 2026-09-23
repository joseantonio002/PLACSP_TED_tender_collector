from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Iterator, Literal
from urllib.parse import urlsplit

from tenderwatch.raw import Acquisition, Artifact, ManifestLine, SourceRecord
from tenderwatch.sources.artifacts import artifact_path, open_artifact
from tenderwatch.sources.errors import ArtifactReadError, SourceFormatError, UnsupportedFormatError
from tenderwatch.sources.formats import JSONValue, parse_json
from tenderwatch.sources.gencat import read_gencat_execution, read_gencat_main, read_gencat_publication
from tenderwatch.sources.placsp import read_placsp


MANIFEST = 'data/raw/download_manifest.jsonl'


def _optional_text(value: dict[str, JSONValue], key: str) -> str | None:
    result = value.get(key)
    if result is not None and not isinstance(result, str):
        raise SourceFormatError(f'Manifest field must be text or null: {key}')
    return result


@dataclass(frozen=True, slots=True)
class RetainedInput:
    artifact: Artifact
    reader: Literal['placsp', 'gencat-main', 'gencat-execution', 'gencat-publication']
    dataset: str
    context_artifacts: tuple[Artifact, ...] = ()

    def read(self, root: Path) -> Iterator[SourceRecord]:
        for context in self.context_artifacts:
            with open_artifact(root, context):
                pass
        if self.reader == 'placsp':
            yield from read_placsp(root, self.artifact, dataset=self.dataset)
        elif self.reader == 'gencat-main':
            yield from read_gencat_main(root, self.artifact, context_artifacts=self.context_artifacts)
        elif self.reader == 'gencat-execution':
            yield from read_gencat_execution(root, self.artifact, context_artifacts=self.context_artifacts)
        elif self.reader == 'gencat-publication':
            yield from read_gencat_publication(root, self.artifact)
        else:
            raise UnsupportedFormatError(f'Unknown retained reader: {self.reader}')


def _classify(artifact: Artifact, entry: dict[str, JSONValue]) -> RetainedInput | None:
    path = Path(artifact.path)
    source = entry.get('source')
    url = urlsplit(artifact.acquisition.source_url or '').path
    if source == 'placsp' and path.suffix in ('.zip', '.atom', '.xml'):
        for name, dataset in (
            ('PlataformasAgregadasSinMenores', 'aggregated'),
            ('licitacionesPerfilesContratanteCompleto3', 'native'),
        ):
            if name in url:
                return RetainedInput(artifact, 'placsp', dataset)
        raise UnsupportedFormatError(f'Unknown retained PLACSP collection: {artifact.path}')
    if source != 'gencat':
        return None
    if path.parent.as_posix() in (
        'data/raw/gencat/phases', 'data/raw/gencat/phase_probes', 'data/raw/gencat/legacy_probes',
    ) and path.suffix != '.partial':
        return RetainedInput(artifact, 'gencat-publication', 'pscp-publications')
    params = entry.get('request_parameters', {})
    if not isinstance(params, dict):
        raise SourceFormatError('Manifest request_parameters must be an object')
    select = params.get('$select', '*')
    if not isinstance(select, str) or '*' not in select.split(','):
        return None
    for dataset, reader in (('ybgg-dgi6', 'gencat-main'), ('8idu-wkjv', 'gencat-execution')):
        if url == f'/resource/{dataset}.json':
            return RetainedInput(artifact, reader, dataset)
    return None


def discover_inputs(root: Path, *, manifest: str = MANIFEST) -> Iterator[RetainedInput]:
    path = artifact_path(root, manifest)
    successes = []
    annotations: dict[str, list[ManifestLine]] = defaultdict(list)
    try:
        with path.open('rb') as stream:
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                entry = parse_json(line, f'{manifest}:{number}')
                if not isinstance(entry, dict):
                    raise SourceFormatError(f'Manifest entry must be an object: line {number}')
                reference = ManifestLine(manifest, number, hashlib.sha256(line).hexdigest())
                if entry.get('event') == 'metadata_annotation':
                    filename = _optional_text(entry, 'applies_to_filename')
                    if filename is not None:
                        annotations[filename].append(reference)
                elif entry.get('validated') is True:
                    successes.append((entry, reference))
    except OSError as exc:
        raise ArtifactReadError(f'Cannot read manifest: {manifest}') from exc
    artifacts = []
    by_path: dict[str, list[Artifact]] = defaultdict(list)
    for entry, reference in successes:
        filename = _optional_text(entry, 'filename')
        checksum = _optional_text(entry, 'sha256')
        size = entry.get('size_bytes')
        if not filename or not checksum or len(checksum) != 64 or any(c not in '0123456789abcdef' for c in checksum) or type(size) is not int or size < 0:
            raise SourceFormatError(f'Invalid successful artifact metadata at line {reference.line_number}')
        artifact_path(root, filename)
        acquisition = Acquisition(
            reference, _optional_text(entry, 'source_url'), _optional_text(entry, 'resolved_url'),
            _optional_text(entry, 'downloaded_at'), _optional_text(entry, 'download_started_at'),
            tuple(annotations[filename]),
        )
        artifact = Artifact(filename, checksum, size, acquisition)
        artifacts.append((artifact, entry))
        by_path[filename].append(artifact)
    for artifact, entry in sorted(artifacts, key=lambda pair: (pair[0].path, pair[0].acquisition.manifest_line.line_number)):
        selected = _classify(artifact, entry)
        if selected is not None:
            contexts = tuple(
                context
                for name in ('metadata-before.json', 'metadata-after.json', 'count-before.json', 'count-after.json')
                for context in by_path.get(f'data/raw/gencat/{selected.dataset}/{name}', ())
            )
            yield RetainedInput(artifact, selected.reader, selected.dataset, contexts)
