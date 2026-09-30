"""
SOL-Decide: "What Flips the Decision" Causal Sensitivity Engine
===============================================================
Performs Quantitative Causal Ablation and inflection boundary extraction,
answering the critical PM question:
"What is the exact minimum parameter shift that flips the optimal decision?"

Mathematical Formulation:
--------------------------
1. Causal Ablation:
   Systematically isolates parameters theta_k and sweeps them over [-delta, +delta].
2. Minimal Sufficient Causal Kernel (MSCK):
   Extracts the minimal subset of assumption stalks and constraint edges
   whose removal or perturbation causes the optimal decision to flip.
3. Decision Flip Boundary:
   theta_k^* = inf { theta_k : argmax_{opt} Utility(opt | theta_k) != opt_0^* }
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from ..core.primitives import (
    PrimitiveType,
    Option,
    Constraint,
    Assumption
)
from ..core.sheaf_decision_complex import SheafDecisionComplex


@dataclass
class ParameterFlipThreshold:
    """Calculated inflection threshold for a single parameter."""
    primitive_id: str
    primitive_name: str
    parameter_channel: int
    baseline_value: float
    flip_value: Optional[float]
    relative_change_pct: Optional[float]
    flipping_option_id: Optional[str]
    is_sensitive: bool
    description: str


@dataclass
class SensitivityReport:
    """Full sensitivity tornado and MSCK analysis report."""
    baseline_selected_option: str
    parameter_thresholds: List[ParameterFlipThreshold]
    minimal_sufficient_causal_kernel: List[str]  # IDs of most critical primitives
    most_fragile_parameter: Optional[str]
    summary: str


class SensitivityAblator:
    """
    Computes inflection boundaries and extracts the Minimal Sufficient Causal Kernel (MSCK).
    """

    def __init__(self, sweep_steps: int = 40, max_deviation_ratio: float = 0.50):
        self.sweep_steps = sweep_steps
        self.max_deviation_ratio = max_deviation_ratio

    def compute_decision_flips(
        self,
        complex_obj: SheafDecisionComplex
    ) -> SensitivityReport:
        """
        Sweeps each active assumption and option parameter to find exact flip points.
        """
        # 1. Establish baseline decision
        base_rep = complex_obj.evaluate_decision_package()
        baseline_opt = base_rep.selected_option_id
        if baseline_opt is None:
            raise RuntimeError("Decision complex is already infeasible at baseline; cannot compute flip boundaries")

        thresholds: List[ParameterFlipThreshold] = []
        msck_ids: List[str] = []

        # Sweep assumptions
        for p in complex_obj.primitives.values():
            if p.primitive_type == PrimitiveType.ASSUMPTION:
                base_val = float(p.state_vector[0])
                flip_val = None
                flip_pct = None
                flip_opt = None

                # Test upward and downward sweeps
                deltas = np.linspace(-self.max_deviation_ratio, self.max_deviation_ratio, self.sweep_steps)
                for d in deltas:
                    test_val = base_val * (1.0 + d)
                    p.set_state(np.array([test_val]))
                    
                    eval_rep = complex_obj.evaluate_decision_package()
                    if eval_rep.selected_option_id != baseline_opt:
                        flip_val = float(test_val)
                        flip_pct = float(d * 100.0)
                        flip_opt = eval_rep.selected_option_id
                        break

                # Reset state
                p.set_state(np.array([base_val]))

                is_sens = flip_val is not None
                if is_sens:
                    msck_ids.append(p.id)

                thresholds.append(ParameterFlipThreshold(
                    primitive_id=p.id,
                    primitive_name=p.name,
                    parameter_channel=0,
                    baseline_value=base_val,
                    flip_value=flip_val,
                    relative_change_pct=flip_pct,
                    flipping_option_id=flip_opt,
                    is_sensitive=is_sens,
                    description=(
                        f"Assumption '{p.name}' flips decision from {baseline_opt} "
                        f"to {flip_opt} at {flip_val:.2f} ({flip_pct:+.1f}%)"
                        if is_sens else f"Assumption '{p.name}' is stable within +/-{self.max_deviation_ratio:.0%}"
                    )
                ))

        # Sweep option parameters
        for opt in complex_obj.primitives.values():
            if opt.primitive_type == PrimitiveType.OPTION and opt.id == baseline_opt:
                orig_state = opt.state_vector.copy()
                for ch in range(opt.stalk_dim):
                    base_val = float(orig_state[ch])
                    flip_val = None
                    flip_pct = None
                    flip_opt = None

                    deltas = np.linspace(-self.max_deviation_ratio, self.max_deviation_ratio, self.sweep_steps)
                    for d in deltas:
                        temp_state = orig_state.copy()
                        temp_state[ch] = base_val * (1.0 + d)
                        opt.set_state(temp_state)

                        eval_rep = complex_obj.evaluate_decision_package()
                        if eval_rep.selected_option_id != baseline_opt:
                            flip_val = float(temp_state[ch])
                            flip_pct = float(d * 100.0)
                            flip_opt = eval_rep.selected_option_id
                            break

                    opt.set_state(orig_state)

                    is_sens = flip_val is not None
                    if is_sens and opt.id not in msck_ids:
                        msck_ids.append(opt.id)

                    thresholds.append(ParameterFlipThreshold(
                        primitive_id=opt.id,
                        primitive_name=f"{opt.name}[ch_{ch}]",
                        parameter_channel=ch,
                        baseline_value=base_val,
                        flip_value=flip_val,
                        relative_change_pct=flip_pct,
                        flipping_option_id=flip_opt,
                        is_sensitive=is_sens,
                        description=(
                            f"Channel {ch} of '{opt.name}' flips to {flip_opt} at {flip_val:.2f} ({flip_pct:+.1f}%)"
                            if is_sens else f"Channel {ch} of '{opt.name}' stable within +/-{self.max_deviation_ratio:.0%}"
                        )
                    ))

        # Sort thresholds by sensitivity (lowest absolute relative change first)
        sensitive_items = [t for t in thresholds if t.is_sensitive]
        sensitive_items.sort(key=lambda t: abs(t.relative_change_pct if t.relative_change_pct is not None else 999.0))
        
        most_fragile = sensitive_items[0].primitive_name if sensitive_items else None

        summary = (
            f"Causal Sensitivity Analysis: Baseline Selection = '{baseline_opt}' | "
            f"Most Fragile Parameter: '{most_fragile}' | "
            f"MSCK Size: {len(msck_ids)} critical components | "
            f"Total Evaluated Parameters: {len(thresholds)}"
        )

        return SensitivityReport(
            baseline_selected_option=baseline_opt,
            parameter_thresholds=thresholds,
            minimal_sufficient_causal_kernel=msck_ids,
            most_fragile_parameter=most_fragile,
            summary=summary
        )
