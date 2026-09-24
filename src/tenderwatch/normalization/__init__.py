from __future__ import annotations

from collections.abc import Callable
import xml.etree.ElementTree as ET

from tenderwatch.raw import ContentReference, RawSourceRecord, RecordKind
from tenderwatch.sources.errors import IntegrityError, LocatorError, SourceFormatError, UnsupportedFormatError
from tenderwatch.sources.formats import JSONValue

from .errors import InvalidNormalizationInput, NormalizationError, NormalizationInvariantError, UnsupportedNormalizationInput
from .models import NormalizedObservation
from .placsp import normalize_placsp
from .publications import normalize_publication
from .tables import normalize_execution, normalize_main
from .validation import validate_observation

SCHEMA_VERSION = 'tenderwatch.observation.v1'
MAPPING_VERSION = 'tenderwatch.normalization.v1'


def normalize(
    raw: RawSourceRecord, *,
    resolve: Callable[[ContentReference], dict[str, JSONValue] | ET.Element],
    projection: str | None = None,
) -> tuple[NormalizedObservation, ...]:
    selection = projection if projection is not None else '$'
    if not raw.raw_record_id or not raw.dataset or not raw.source:
        raise InvalidNormalizationInput('missing_provenance', raw.raw_record_id, selection)
    if raw.record_kind == RecordKind.GENCAT_PUBLICATION_XML:
        raise UnsupportedNormalizationInput('unsupported_structure_or_format', raw.raw_record_id, selection)
    if raw.record_kind not in set(RecordKind):
        raise UnsupportedNormalizationInput('unsupported_record_kind', raw.raw_record_id, selection)
    if raw.record_kind != RecordKind.GENCAT_PUBLICATION_JSON and selection != '$':
        raise InvalidNormalizationInput('unresolvable_projection', raw.raw_record_id, selection)
    if raw.record_kind == RecordKind.PLACSP_TOMBSTONE:
        return ()
    try:
        payload = resolve(raw.content)
    except LocatorError as exc:
        raise InvalidNormalizationInput('unresolvable_occurrence', raw.raw_record_id, selection) from exc
    except IntegrityError as exc:
        raise InvalidNormalizationInput('raw_integrity_mismatch', raw.raw_record_id, selection) from exc
    except UnsupportedFormatError as exc:
        raise UnsupportedNormalizationInput('unsupported_structure_or_format', raw.raw_record_id, selection) from exc
    except SourceFormatError as exc:
        raise InvalidNormalizationInput('unparseable_payload', raw.raw_record_id, selection) from exc
    if raw.record_kind == RecordKind.PLACSP_ATOM_ENTRY:
        if not isinstance(payload, ET.Element):
            raise InvalidNormalizationInput('missing_root_or_wrong_shape', raw.raw_record_id, selection)
        observations = (normalize_placsp(raw, payload),)
    else:
        if not isinstance(payload, dict):
            raise InvalidNormalizationInput('missing_root_or_wrong_shape', raw.raw_record_id, selection)
        if raw.record_kind == RecordKind.GENCAT_PUBLICATION_JSON:
            observations = normalize_publication(raw, payload, projection)
        elif raw.record_kind == RecordKind.GENCAT_MAIN_ROW:
            observations = (normalize_main(raw, payload),)
        else:
            observations = (normalize_execution(raw, payload),)
    for observation in observations:
        validate_observation(observation)
    return observations
