from __future__ import annotations

from decimal import Decimal
import json
import xml.etree.ElementTree as ET

from tenderwatch.sources.errors import SourceFormatError, UnsupportedFormatError


type JSONValue = None | bool | int | Decimal | str | list[JSONValue] | dict[str, JSONValue]


def _invalid_constant(value: str) -> None:
    raise SourceFormatError(f'Non-JSON numeric constant: {value}')


def parse_json(data: bytes, label: str) -> JSONValue:
    try:
        return json.loads(data, parse_float=Decimal, parse_constant=_invalid_constant)
    except (ValueError, UnicodeError) as exc:
        raise SourceFormatError(f'Malformed JSON: {label}') from exc


class _TreeBuilder(ET.TreeBuilder):
    def doctype(self, name: str, pubid: str | None, system: str | None) -> None:
        raise UnsupportedFormatError('DTD-bearing XML is not a supported retained format')


def parse_xml(data: bytes, label: str) -> ET.Element:
    try:
        return ET.fromstring(data, parser=ET.XMLParser(target=_TreeBuilder(insert_comments=True, insert_pis=True)))
    except ET.ParseError as exc:
        raise SourceFormatError(f'Malformed XML: {label}') from exc
