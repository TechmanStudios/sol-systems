"""
SOL-Decide Demonstration 2: Long-Horizon Living Decision Program
================================================================
Demonstrates automated 18-month lifecycle refresh, coboundary defect isolation,
and auditable Differential Decision Delta generation under three realistic shocks:
1. Battery technology shortfall (-15% Wh/kg -> weight penalty)
2. Threat evolution / applique armor increase (+1,800 lbs / 0.9 tons)
3. Geopolitical supply chain disruption (inverter lead time +26 weeks)
"""

from typing import Tuple, List, Dict, Any
import numpy as np

from ..core.sheaf_decision_complex import SheafDecisionComplex, DecisionEvaluationReport
from ..delivery.decision_package import SignerReadyDecisionPackage
from ..delivery.differential_delta import (
    DifferentialDeltaEngine,
    DifferentialDecisionDelta,
    OperationalShock
)
from .demo1_ngcv_powertrain import build_ngcv_trade_study, run_demonstration_1


def run_demonstration_2() -> Tuple[DifferentialDecisionDelta, DecisionEvaluationReport, SheafDecisionComplex]:
    """
    Executes complete end-to-end pipeline for Demonstration 2.
    """
    # 1. Establish Demonstration 1 baseline
    complex_obj, base_package, _, _ = run_demonstration_1()

    # 2. Formulate 18-Month Operational Shocks
    shocks = [
        # Shock 1: Battery density shortfall - adds 3.2 tons to HED battery weight (Channel 0)
        OperationalShock(
            shock_id="SHOCK-BATTERY-DENSITY",
            target_primitive_id="opt_hed",
            parameter_channel=0,  # Weight channel
            delta_value=3.2,
            is_relative_pct=False,
            rationale="15% shortfall in prototype Li-Ion energy density forces larger cell pack to meet 8hr silent watch"
        ),
        # Shock 2: Threat evolution - applique armor adds 0.9 tons to HED chassis (Channel 0)
        OperationalShock(
            shock_id="SHOCK-ARMOR-INCREASE",
            target_primitive_id="opt_hed",
            parameter_channel=0,  # Weight channel
            delta_value=0.9,
            is_relative_pct=False,
            rationale="DEVCOM blast survivability mandate mandates 1,800 lbs titanium applique package"
        ),
        # Shock 3: Supply chain lead time surge - SiC inverters jump by 26 weeks (Channel 3)
        OperationalShock(
            shock_id="SHOCK-SUPPLY-CHAIN",
            target_primitive_id="opt_hed",
            parameter_channel=3,  # Lead time channel
            delta_value=26.0,
            is_relative_pct=False,
            rationale="Geopolitical disruption in high-purity silicon carbide wafers surges procurement lead time"
        )
    ]

    # 3. Execute Living Refresh Engine
    engine = DifferentialDeltaEngine()
    delta, refreshed_eval = engine.apply_shocks_and_evaluate(
        complex_obj=complex_obj,
        baseline_package=base_package,
        shocks=shocks
    )

    return delta, refreshed_eval, complex_obj
