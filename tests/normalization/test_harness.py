from dataclasses import dataclass
from types import ModuleType, SimpleNamespace

import pytest

from . import conftest as harness
from .support import semantic


def test_absence_marker_is_narrow_and_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    marks = []
    item = SimpleNamespace(path=harness.Path(harness.__file__).parent / 'test_core.py', fixturenames=('api',), add_marker=marks.append)
    monkeypatch.setattr(harness, 'find_spec', lambda name: None)
    harness.pytest_collection_modifyitems([item])
    assert len(marks) == 1
    assert marks[0].kwargs['raises'] is harness.MissingNormalizationImplementation
    assert marks[0].kwargs['strict'] is True
    with pytest.raises(harness.MissingNormalizationImplementation):
        harness.api.__wrapped__()
    monkeypatch.setattr(harness, 'find_spec', lambda name: object())
    marks.clear()
    harness.pytest_collection_modifyitems([item])
    assert not marks


def test_existing_broken_api_is_never_marked_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harness, 'find_spec', lambda name: object())
    error = ModuleNotFoundError('dependency failure inside an existing implementation')
    def broken_import(name: str):
        raise error
    monkeypatch.setattr(harness, 'import_module', broken_import)
    with pytest.raises(ModuleNotFoundError) as caught:
        harness.api.__wrapped__()
    assert caught.value is error
    monkeypatch.setattr(harness, 'import_module', lambda name: ModuleType(name))
    with pytest.raises(AssertionError, match='Missing normalization API export'):
        harness.api.__wrapped__()


def test_semantic_comparison_ignores_opaque_keys_not_reference_targets() -> None:
    @dataclass(frozen=True)
    class Item:
        key: str
        source_path: str

    @dataclass(frozen=True)
    class View:
        observation_id: str
        raw_source_record_id: str
        lots: tuple[Item, ...]
        lot_keys: tuple[str, ...]

    first = View('observation-a', 'raw-a', (Item('a', '/lots/0'), Item('b', '/lots/1')), ('a',))
    renamed = View('observation-b', 'raw-b', (Item('c', '/lots/0'), Item('d', '/lots/1')), ('c',))
    wrong = View('observation-b', 'raw-b', renamed.lots, ('d',))
    assert semantic(first) == semantic(renamed)
    assert semantic(first) != semantic(wrong)
