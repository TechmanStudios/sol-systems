"""
SOL-Decide: Differential Decision Delta Engine
===============================================
Computes living decision program updates when operational evidence,
environmental parameters, or supply chain realities drift over time.

Mechanism:
----------
1. Ingests baseline signed Decision Package.
2. Applies operational shocks (e.g., prototype battery failure, armor up-armoring, lead time surge).
3. Automatically activates Sheaf Coboundary delta^0 x to isolate strained edges without manual review.
4. Performs surgical re-evaluation of affected subgraphs.
5. Emits an auditable Differential Decision Delta stating whether the optimal alternative flipped.
"""

from dataclasses import dataclass, field
import time
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import scipy.linalg as la

from ..core.sheaf_decision_complex import SheafDecisionComplex, DecisionEvaluationReport
from .decision_package import SignerReadyDecisionPackage


@dataclass
class OperationalShock:
    """Represents an external shock or parameter drift."""
    shock_id: str
    target_primitive_id: str
    parameter_channel: int
    delta_value: float  # Absolute or relative shift
    is_relative_pct: bool
    rationale: str


@dataclass
class DifferentialDecisionDelta:
    """Auditable differential report between baseline and refreshed decision states."""
    delta_id: str
    baseline_package_id: str
    baseline_option_id: str
    refreshed_option_id: str
    did_decision_flip: bool
    applied_shocks: List[OperationalShock]
    activated_coboundary_edges: List[Dict[str, Any]]
    pre_energy: float
    post_energy: float
    pre_betti_1: int
    post_betti_1: int
    audit_summary: str


class DifferentialDeltaEngine:
    """
    Applies shocks and calculates Differential Decision Deltas for living programs.
    """

    def apply_shocks_and_evaluate(
        self,
        complex_obj: SheafDecisionComplex,
        baseline_package: SignerReadyDecisionPackage,
        shocks: List[OperationalShock]
    ) -> Tuple[DifferentialDecisionDelta, DecisionEvaluationReport]:
        """
        Applies a list of shocks, detects coboundary discrepancies, and calculates the delta.
        """
        pre_energy = baseline_package.dirichlet_energy
        pre_betti_1 = baseline_package.betti_1
        base_option = baseline_package.selected_option_id

        # Apply shocks
        for shock in shocks:
            if shock.target_primitive_id in complex_obj.primitives:
                p = complex_obj.primitives[shock.target_primitive_id]
                ch = shock.parameter_channel
                if ch < len(p.state_vector):
                    old_val = p.state_vector[ch]
                    if shock.is_relative_pct:
                        new_val = old_val * (1.0 + shock.delta_value)
                    else:
                        new_val = old_val + shock.delta_value
                    
                    new_vec = p.state_vector.copy()
                    new_vec[ch] = new_val
                    p.set_state(new_vec)

        # Invalidate cache & re-evaluate
        complex_obj._invalidate_cache()
        refreshed_eval = complex_obj.evaluate_decision_package()

        # Audit activated coboundary edges
        strained_edges = complex_obj.audit_obstructions(tolerance=1e-3)

        did_flip = (refreshed_eval.selected_option_id != base_option)
        delta_id = f"DELTA-{int(time.time())}"

        audit_summary = (
            f"Differential Decision Delta [{delta_id}]: "
            f"Baseline Selection '{base_option}' -> Refreshed Selection '{refreshed_eval.selected_option_id}'. "
            f"Decision {'FLIPPED' if did_flip else 'REMAINED STABLE'}. "
            f"Shocks Applied: {len(shocks)}. Strained Edges Detected: {len(strained_edges)}. "
            f"Energy: {pre_energy:.4e} -> {refreshed_eval.dirichlet_energy:.4e}."
        )

        delta = DifferentialDecisionDelta(
            delta_id=delta_id,
            baseline_package_id=baseline_package.package_id,
            baseline_option_id=base_option,
            refreshed_option_id=refreshed_eval.selected_option_id or "NONE",
            did_decision_flip=did_flip,
            applied_shocks=shocks,
            activated_coboundary_edges=strained_edges,
            pre_energy=pre_energy,
            post_energy=refreshed_eval.dirichlet_energy,
            pre_betti_1=pre_betti_1,
            post_betti_1=refreshed_eval.beta_1,
            audit_summary=audit_summary
        )

        return delta, refreshed_eval
