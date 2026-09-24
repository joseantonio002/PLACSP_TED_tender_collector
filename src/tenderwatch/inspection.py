from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any, TextIO

from tenderwatch.normalization import NormalizationError, NormalizedObservation
from tenderwatch.raw import RawSourceRecord
from tenderwatch.serialization import serialize


def create_output(parent: Path | None = None) -> Path:
    return Path(tempfile.mkdtemp(prefix='tenderwatch-inspection-', dir=parent))


def raw_summary(raw: RawSourceRecord) -> dict[str, Any]:
    return {
        'raw_record_id': raw.raw_record_id, 'source': raw.source, 'dataset': raw.dataset,
        'record_kind': raw.record_kind, 'artifact': raw.content.artifact.path,
        'locator': raw.content.locator, 'source_identifiers': raw.source_identifiers,
    }


def failure_summary(raw: RawSourceRecord, error: NormalizationError) -> dict[str, Any]:
    return {'raw': raw_summary(raw), 'error': type(error).__name__, 'reason': error.reason,
            'projection_locator': error.projection_locator}


def preview(raw: RawSourceRecord, observations: tuple[NormalizedObservation, ...], stream: TextIO, error: NormalizationError | None = None) -> None:
    print('RawSourceRecord ' + serialize(raw_summary(raw)), file=stream)
    print('    ↓', file=stream)
    if error is not None:
        print('Normalization failure ' + serialize({'type': type(error).__name__, 'reason': error.reason}), file=stream)
        return
    print(f'NormalizedObservation(s): {len(observations)}', file=stream)
    for observation in observations:
        print(serialize({
            'observation_id': observation.observation_id, 'projection_locator': observation.projection_locator,
            'subject_kind': observation.subject_kind, 'focus': observation.focus,
            'procedure_numbers': observation.procedure_numbers,
            'titles': tuple(text.text[:180] for text in observation.titles[:2]),
            'financials': tuple({'purpose': item.value.purpose, 'scope': item.scope.kind,
                                 'value': item.value.value, 'currency': item.value.currency, 'tax_basis': item.value.tax_basis}
                                for item in observation.financials[:6]),
            'execution_actions': tuple({'type': action.type, 'action_at': action.action_at, 'amounts': action.amounts}
                                       for action in observation.execution_actions[:2]),
            'counts': {name: len(getattr(observation, name)) for name in ('lots', 'publications', 'awards', 'execution_actions', 'documents', 'issues')},
            'issue_codes': sorted({issue.code for issue in observation.issues}),
        }), file=stream)
