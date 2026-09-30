"""
Pytest configuration for sol-systems test suite.
Ensures sol-decide and all workspace modules are directly importable.
"""
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sol_decide_dir = root_dir / "sol-decide"

if str(sol_decide_dir) not in sys.path:
    sys.path.insert(0, str(sol_decide_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
