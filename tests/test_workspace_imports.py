"""Validate the public Exciton exports in the integrated checkout."""

import subprocess
import sys
from pathlib import Path


def test_integrated_navigator_exports():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
from pathlib import Path
sys.path.insert(0, str(Path("Frontier_OS/Exciton-MoA").resolve()))
from firmWare.ExcitonEngine import (
    ExcitonEngine, RiemannianGeodesicNavigator, ChristoffelCalculator, GeodesicStepResult,
)
import firmWare.ExcitonEngine as package
assert package.RiemannianGeodesicNavigator is RiemannianGeodesicNavigator
assert RiemannianGeodesicNavigator(dim=2).dim == 2
assert ChristoffelCalculator(dim=2).dim == 2
""",
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
