"""
SOL-Decide Demonstrations Package
"""

from .demo1_ngcv_powertrain import (
    build_ngcv_trade_study,
    run_demonstration_1
)
from .demo2_living_refresh import (
    run_demonstration_2
)

__all__ = [
    "build_ngcv_trade_study",
    "run_demonstration_1",
    "run_demonstration_2"
]
