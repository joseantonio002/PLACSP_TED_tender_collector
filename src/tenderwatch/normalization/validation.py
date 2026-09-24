from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from .errors import NormalizationInvariantError
from .models import Identifier, Money, NormalizedObservation, Scope, TemporalValue


def validate_observation(observation: NormalizedObservation) -> None:
    def require(condition: bool, detail: str) -> None:
        if not condition:
            raise NormalizationInvariantError(detail)

    require(isinstance(observation, NormalizedObservation), 'Expected NormalizedObservation')
    for name in ('observation_id', 'raw_source_record_id', 'projection_locator', 'schema_version', 'mapping_version'):
        require(isinstance(getattr(observation, name), str) and bool(getattr(observation, name)), 'Missing ' + name)
    require(bool(observation.source.system and observation.source.dataset and observation.source.record_kind), 'Missing source metadata')
    targets = {
        'lot_keys': {item.key for item in observation.lots},
        'publication_keys': {item.key for item in observation.publications},
        'outcome_keys': {item.key for item in observation.outcomes},
    }
    keys = set()

    def visit(value: Any) -> None:
        if is_dataclass(value):
            require(value.__dataclass_params__.frozen, 'Mutable output dataclass')
            if hasattr(value, 'key'):
                require(bool(value.key) and value.key not in keys, 'Empty or duplicate local key')
                keys.add(value.key)
            if hasattr(value, 'source_path'):
                require(isinstance(value.source_path, str) and bool(value.source_path), 'Missing source path')
            for name, available in targets.items():
                if hasattr(value, name):
                    require(set(getattr(value, name)) <= available, 'Dangling ' + name)
            if isinstance(value, Identifier):
                require(bool(value.value and value.scheme and value.namespace and value.role), 'Empty identifier')
            if isinstance(value, Scope):
                require(value.kind in ('procedure', 'lots', 'record_subject', 'publication_batch', 'unknown'), 'Invalid scope')
                require(bool(value.lot_keys or value.source_lot_identifiers) == (value.kind == 'lots'), 'Invalid lot scope')
            if isinstance(value, Money):
                require(value.value_state in ('valid', 'explicit_empty', 'invalid'), 'Unknown money state')
                require((value.value is not None) == (value.value_state == 'valid'), 'Money value/state mismatch')
                require(value.value is None or isinstance(value.value, Decimal) and value.value.is_finite(), 'Money must be finite Decimal')
                require(isinstance(value.raw_value, str), 'Missing raw monetary token')
            if isinstance(value, TemporalValue):
                require(value.local_date is None or type(value.local_date) is date, 'Invalid calendar date')
                require(value.local_time is None or type(value.local_time) is time, 'Invalid clock time')
                require(value.utc_instant is None or isinstance(value.utc_instant, datetime) and value.utc_instant.utcoffset() == timedelta(0), 'Instant must be UTC aware')
                if value.precision == 'day':
                    require(value.local_time is None and value.utc_instant is None, 'Date-only value has time')
                if value.zone_basis == 'unknown':
                    require(value.utc_instant is None, 'Unknown zone cannot imply an instant')
            for field in fields(value):
                visit(getattr(value, field.name))
        elif isinstance(value, tuple):
            for item in value:
                visit(item)
        else:
            require(isinstance(value, (type(None), str, int, Decimal, date, time, timedelta)), 'Mutable or unsupported output value')
            if isinstance(value, Decimal):
                require(value.is_finite(), 'Nonfinite decimal')
    visit(observation)
    for field, role in (('procedure_identifiers', 'procedure'), ('procedure_numbers', 'procedure_number'), ('batch_identifiers', 'batch'), ('member_identifiers', 'member')):
        require(all(i.role == role for i in getattr(observation, field)), 'Incorrect identifier role')
    require(all(i.role == 'record' for i in observation.source.record_identifiers), 'Incorrect record identifier role')
    require(all(issue.code and issue.path.startswith('raw:') and issue.detail for issue in observation.issues), 'Invalid issue')
