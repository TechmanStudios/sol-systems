"""
Pytest configuration for sol-systems test suite.
Ensures sol-decide, sol-edge, sol-continuum, sol-change, sol-holo, and all
workspace modules are directly importable and registers custom pytest markers.
"""
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent

for rel_dir in (
    root_dir / "sol-decide",
    root_dir / "sol-edge" / "src",
    root_dir / "sol-continuum",
    root_dir / "sol-change",
    root_dir / "sol-holo",
    root_dir,
):
    path_str = str(rel_dir)
    if rel_dir.exists() and path_str not in sys.path:
        sys.path.insert(0, path_str)

# Prevent pytest conftest package-name collision with submodule `sol/tests/conftest.py`
sys.modules.pop("tests.conftest", None)
sys.modules.pop("tests", None)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live_gemini: live Gemini API verification test (deselect with -k 'not live')",
    )
