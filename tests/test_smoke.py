from importlib.metadata import metadata

import tenderwatch


def test_package_import() -> None:
    assert tenderwatch.__name__ == "tenderwatch"
    assert metadata("tenderwatch")["Name"] == "TenderWatch"
