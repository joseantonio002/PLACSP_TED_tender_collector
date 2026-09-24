from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from functools import cache
import json
import re
from types import UnionType
from typing import Any, Callable, TypeVar, get_args, get_origin, get_type_hints

from tenderwatch.normalization.models import NormalizedObservation


@cache
def _field_names(cls: type) -> tuple[str, ...]:
    return tuple(field.name for field in fields(cls))


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return {name: getattr(value, name) for name in _field_names(type(value))}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return str(value)
    raise TypeError(f'Unsupported serialized value: {type(value).__name__}')


def serialize(value: Any) -> str:
    return json.dumps(value, default=_json_default, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def _duration(value: str) -> timedelta:
    match = re.fullmatch(r'(?:(-?\d+) days?, )?(\d+):(\d{2}):(\d{2})(?:\.(\d{1,6}))?', value)
    if match is None:
        raise ValueError('Invalid serialized offset')
    days, hours, minutes, seconds, fraction = match.groups()
    return timedelta(days=int(days or 0), hours=int(hours), minutes=int(minutes), seconds=int(seconds), microseconds=int((fraction or '').ljust(6, '0')))


@cache
def _decoder(annotation: Any) -> Callable[[Any], Any]:
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is UnionType and type(None) in args and len(args) == 2:
        decode = _decoder(next(arg for arg in args if arg is not type(None)))
        return lambda value: None if value is None else decode(value)
    if origin is tuple:
        decode = _decoder(args[0])
        def sequence(value):
            if not isinstance(value, list):
                raise ValueError('Expected serialized array')
            return tuple(decode(item) for item in value)
        return sequence
    cls = origin or annotation
    if is_dataclass(cls):
        bindings = dict(zip(getattr(cls, '__parameters__', ()), args))
        hints = get_type_hints(cls)
        decoders = {name: _decoder(bindings.get(hint, hint) if isinstance(hint, TypeVar) else hint) for name, hint in hints.items()}
        def model(value):
            if not isinstance(value, dict) or value.keys() != decoders.keys():
                raise ValueError(f'Invalid serialized {cls.__name__} fields')
            return cls(**{name: decode(value[name]) for name, decode in decoders.items()})
        return model
    if annotation is Decimal:
        def decimal(value):
            if not isinstance(value, str):
                raise ValueError('Serialized decimals must be strings')
            result = Decimal(value)
            if not result.is_finite():
                raise ValueError('Nonfinite decimal')
            return result
        return decimal
    if annotation in (datetime, date, time):
        return annotation.fromisoformat
    if annotation is timedelta:
        return _duration
    if annotation in (str, bool, int):
        def scalar(value):
            if type(value) is not annotation:
                raise ValueError(f'Expected serialized {annotation.__name__}')
            return value
        return scalar
    raise TypeError(f'Unsupported model annotation: {annotation}')


def observation_from_dict(value: dict[str, Any]) -> NormalizedObservation:
    return _decoder(NormalizedObservation)(value)


def load_observation(line: str) -> NormalizedObservation:
    return observation_from_dict(json.loads(line))
