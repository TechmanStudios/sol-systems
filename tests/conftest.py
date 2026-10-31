"""
Pytest configuration for sol-systems test suite.
Ensures sol-decide, sol-edge, sol-continuum, sol-change, sol-holo, and all
workspace modules are directly importable and registers custom pytest markers.
"""
import importlib
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent

for rel_dir in (
    root_dir / "sol-decide",
    root_dir / "sol-edge" / "src",
    root_dir / "sol-continuum",
    root_dir / "sol-change",
    root_dir / "sol-holo",
):
    path_str = str(rel_dir)
    if rel_dir.exists() and path_str not in sys.path:
        sys.path.insert(0, path_str)

root_str = str(root_dir)
if root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

for extra_dir in (
    root_dir / "Frontier_OS" / "Exciton-MoA",
    root_dir / "sol" / "tools" / "sol-core",
    root_dir / "sol" / "tools" / "sol-hippocampus",
    root_dir / "sol" / "tools" / "sol-rsi",
    root_dir / "sol" / "tools" / "sol-llm",
    root_dir / "sol" / "solCompiler",
):
    extra_str = str(extra_dir)
    if extra_dir.exists() and extra_str not in sys.path:
        sys.path.append(extra_str)

# Bridge root `scripts/` (namespace dir) with `Frontier_OS/Exciton-MoA/scripts/__init__.py`
# so `import scripts.run_sol_live_stream` and `import scripts.<exciton_module>` both resolve.
_scripts_mod = importlib.import_module("scripts")
for _scripts_dir in (
    root_dir / "scripts",
    root_dir / "Frontier_OS" / "Exciton-MoA" / "scripts",
):
    _s_str = str(_scripts_dir)
    if _scripts_dir.is_dir() and _s_str not in _scripts_mod.__path__:
        _scripts_mod.__path__.insert(0, _s_str)


def pytest_configure(config):
    # Prevent conftest package-name collision with submodule `sol/tests/conftest.py`
    # after pytest finishes `import_path` / `insert_missing_modules` under importlib mode.
    sys.modules.pop("tests.conftest", None)
    sys.modules.pop("tests", None)
    config.addinivalue_line(
        "markers",
        "live_gemini: live Gemini API verification test (deselect with -k 'not live')",
    )
