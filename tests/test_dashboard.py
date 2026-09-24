from pathlib import Path
import shutil
import subprocess

import pytest


def test_dashboard_regressions() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Dashboard JavaScript tests require Node.js with node:test support")
    result = subprocess.run(
        [node, "--test", str(Path(__file__).with_name("dashboard.test.cjs"))],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_filter_explanation_is_after_all_controls() -> None:
    from tenderwatch.web import STATIC_DIR

    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    sidebar = html.split('<aside class="filters"', 1)[1].split("</aside>", 1)[0]
    explanation = sidebar.index("Filters use selected values only.")
    assert explanation > sidebar.rindex("</label>")
    assert sidebar.count("Filters use selected values only.") == 1
