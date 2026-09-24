from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any
from urllib.parse import urlsplit

from tenderwatch.raw import RawSourceRecord
from .models import (
    Classification, Code, Identifier, Issue, LocalizedText, MappedCode, Money,
    NormalizedObservation, Scope, SourceMetadata, SourceReference, TemporalValue,
)

PROCEDURE = Scope('procedure')
SUBJECT = Scope('record_subject')
BATCH_SCOPE = Scope('publication_batch')
BATCH_PATH = '/publicacio/dadesPublicacio/contractesAgregada'


def lexical(value: Any) -> str:
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


def composite(paths: list[str]) -> str:
    return paths[0] if len(paths) == 1 else 'paths:' + json.dumps(paths, ensure_ascii=False)


def key(kind: str, path: str) -> str:
    return kind + ':' + hashlib.sha256(path.encode()).hexdigest()[:24]


class Builder:
    def __init__(self, raw: RawSourceRecord, kind: str, projection: str = '$') -> None:
        self.raw = raw
        self.projection = projection
        self.issues: list[Issue] = []
        self.data: dict[str, Any] = {
            field.name: [] for field in fields(NormalizedObservation) if field.default == ()
        }
        self.data.update(source=SourceMetadata(raw.source, raw.dataset, kind), subject_kind='procedure', focus=PROCEDURE)

    def add(self, field: str, value: Any) -> None:
        self.data[field].append(value)

    def issue(self, code: str, path: str) -> None:
        diagnostic = Issue(code, 'raw:' + path, code.replace('_', ' ').capitalize())
        if diagnostic not in self.issues:
            self.issues.append(diagnostic)

    def finish(self) -> NormalizedObservation:
        from . import MAPPING_VERSION, SCHEMA_VERSION
        identity = json.dumps([self.raw.raw_record_id, self.projection, SCHEMA_VERSION, MAPPING_VERSION])
        values = {name: tuple(value) if isinstance(value, list) else value for name, value in self.data.items()}
        values['issues'] = tuple(self.issues)
        return NormalizedObservation(
            observation_id='obs:v1:' + hashlib.sha256(identity.encode()).hexdigest(),
            raw_source_record_id=self.raw.raw_record_id, projection_locator=self.projection,
            schema_version=SCHEMA_VERSION, mapping_version=MAPPING_VERSION, **values,
        )

    def identifier(self, value: Any, role: str, scheme: str = 'source_unclassified', namespace: str | None = None) -> Identifier:
        return Identifier(scheme, namespace or f'{self.raw.source}:{self.raw.dataset}:{scheme}', lexical(value), role)

    def texts(self, value: Any, path: str, role: str | None = None) -> tuple[LocalizedText, ...]:
        if value is None or value == '':
            return ()
        if isinstance(value, str):
            return (LocalizedText(value, source_role=role),)
        if not isinstance(value, dict):
            self.issue('unsupported_structure', path)
            return ()
        result = []
        for language in ('ca', 'es', 'en', 'oc'):
            text = value.get(language)
            if text == 'null':
                self.issue('invalid_value', path + '/' + language)
            elif isinstance(text, str) and text:
                result.append(LocalizedText(text, language, role))
        return tuple(result)

    def code(self, value: Any, path: str, system: str | None = None) -> Code:
        if isinstance(value, dict):
            return Code(system or f'{self.raw.source}:{path}', lexical(value.get('id', '')), labels=self.texts(value, path))
        return Code(system or f'{self.raw.source}:{path}', lexical(value))

    def mapped(self, value: Any, path: str, vocabulary: dict[str, str], *, system: str | None = None, broader: tuple[str, ...] = ()) -> MappedCode:
        code = self.code(value, path, system)
        normalized = vocabulary.get(code.value)
        if normalized is None:
            self.issue('unmapped_code', path)
        return MappedCode(code, normalized, 'unmapped' if normalized is None else ('broader' if code.value in broader else 'exact'))

    def decimal(self, value: Any, path: str) -> Decimal | None:
        try:
            result = Decimal(lexical(value)) if isinstance(value, (str, int, Decimal)) and not isinstance(value, bool) else None
        except InvalidOperation:
            result = None
        if result is None or not result.is_finite():
            self.issue('invalid_value', path)
            return None
        return result

    def money(self, value: Any, path: str, purpose: str, tax: str, currency: str | None = None, *, vat: Decimal | None = None, multiple: bool | None = None) -> Money:
        raw = lexical(value)
        if value is None or value == '':
            self.issue('explicit_empty', path)
            amount, state = None, 'explicit_empty'
        else:
            amount = self.decimal(value, path)
            state = 'valid' if amount is not None else 'invalid'
        return Money(purpose, amount, raw, state, currency, tax, vat, multiple)

    def temporal(self, value: Any, path: str, *, calendar: bool = False, unresolved: bool = False) -> TemporalValue:
        raw = lexical(value)
        if unresolved:
            self.issue('ambiguous_time', path)
            return TemporalValue(raw)
        try:
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw):
                return TemporalValue(raw, local_date=date.fromisoformat(raw), zone_basis='not_applicable', precision='day')
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            self.issue('invalid_value', path)
            return TemporalValue(raw)
        if calendar and parsed.time() == time(0) and parsed.tzinfo is None:
            return TemporalValue(raw, local_date=parsed.date(), zone_basis='not_applicable', precision='day', precision_basis='observed_projection')
        if calendar:
            self.issue('uncertain_precision', path)
        offset = parsed.utcoffset()
        if offset is None:
            self.issue('ambiguous_time', path)
        precision = 'fractional_second' if '.' in raw else ('second' if len(raw.split('T')[-1].split(':')) >= 3 else 'minute')
        return TemporalValue(raw, parsed.date(), parsed.time(), parsed.astimezone(timezone.utc) if offset is not None else None,
                             offset, zone_basis='explicit_offset' if offset is not None else 'unknown', precision=precision)

    def classification(self, value: Any, path: str, system: str | None = None) -> Classification:
        raw = lexical(value)
        match = re.fullmatch(r'(\d{8})(?:-(\d))?', raw)
        if match is None:
            self.issue('invalid_value', path)
        return Classification(raw, match[1] if match else None, match[2] if match else None, source_system=system)

    def url(self, value: Any, path: str) -> str | None:
        if not isinstance(value, str):
            self.issue('unsupported_structure', path)
            return None
        try:
            parsed = urlsplit(value)
            valid = parsed.scheme in ('http', 'https') and bool(parsed.hostname) and not any(c.isspace() for c in value)
        except ValueError:
            valid = False
        if not valid:
            self.issue('invalid_value', path)
            return None
        return value

    def url_ids(self, url: str, *, batch: bool = False) -> tuple[Identifier, ...]:
        parsed = urlsplit(url)
        if parsed.hostname != 'contractaciopublica.cat':
            return ()
        result = []
        match = re.fullmatch(r'/[^/]+/detall-publicacio/([0-9a-fA-F-]{36})/(\d+)', parsed.path)
        if match:
            result.append(self.identifier(match[1], 'batch' if batch else 'procedure', 'pscp_uuid', 'gencat:pscp'))
            result.append(self.identifier(match[2], 'publication', 'pscp_publication', 'gencat:pscp'))
        else:
            match = re.match(r'/portal-api/documents-publicacio/(?:json-xifrat|json)/(\d+)(?:/|$)', parsed.path)
            if match:
                result.append(self.identifier(match[1], 'publication', 'pscp_publication', 'gencat:pscp'))
        return tuple(result)

    def reference(self, value: Any, path: str, target: str, publications: tuple[str, ...] = (), *, batch: bool = False) -> SourceReference | None:
        url = self.url(value, path)
        if url is None:
            return None
        reference = SourceReference(key=key('reference', path), source_path=path, url=url, target_kind=target,
                                    identifiers=self.url_ids(url, batch=batch), publication_keys=publications)
        self.add('source_references', reference)
        return reference
