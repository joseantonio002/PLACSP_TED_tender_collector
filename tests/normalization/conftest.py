from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
import builtins
import io
import os
from pathlib import Path
import socket
import sqlite3
from types import ModuleType
from typing import NoReturn

import pytest

from .support import Cases


MODULE = 'tenderwatch.normalization'


class MissingNormalizationImplementation(RuntimeError):
    pass


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption('--audit-normalization-evidence', action='store_true', help='Compare committed normalization fixtures with the optional local research originals')


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if find_spec(MODULE) is None:
        for item in items:
            if Path(__file__).parent in Path(item.path).parents and 'api' in getattr(item, 'fixturenames', ()):
                item.add_marker(pytest.mark.xfail(
                    raises=MissingNormalizationImplementation, strict=True,
                    reason='Test-first contract: tenderwatch.normalization is not implemented yet',
                ))


@pytest.fixture
def api() -> ModuleType:
    if find_spec(MODULE) is None:
        raise MissingNormalizationImplementation(MODULE)
    module = import_module(MODULE)
    for name in ('normalize', 'validate_observation', 'NormalizedObservation', 'SCHEMA_VERSION', 'MAPPING_VERSION', 'NormalizationError', 'InvalidNormalizationInput', 'UnsupportedNormalizationInput', 'NormalizationInvariantError'):
        assert hasattr(module, name), f'Missing normalization API export: {name}'
    return module


@pytest.fixture
def cases(tmp_path: Path) -> Cases:
    return Cases(tmp_path)


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args, **kwargs) -> NoReturn:
        raise AssertionError('Normalization and its fixtures must not access the network')

    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)
    monkeypatch.setattr(sqlite3, 'connect', forbidden)


@pytest.fixture(autouse=True)
def forbid_research_fallback(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    if request.node.name == 'test_optional_fixture_audit_against_originals':
        return
    research_data = Path(__file__).resolve().parents[2] / 'data'

    def guarded(original):
        def open_file(path, *args, **kwargs):
            if not isinstance(path, int):
                assert not Path(os.fsdecode(path)).resolve().is_relative_to(research_data), 'Normalization tests must use committed fixtures, not research data'
            return original(path, *args, **kwargs)
        return open_file

    monkeypatch.setattr(builtins, 'open', guarded(builtins.open))
    monkeypatch.setattr(io, 'open', guarded(io.open))
