"""
Frontier Z (Vector 29): Sovereign Court Promotion Docket, Final Gate Registry & System Lockdown Engine
======================================================================================================

Provides `SovereignCourtLockdownEngine` and `SovereignCourtLockdownReport` inside `sol_continuum`,
orchestrating:
1. Sovereign Court Promotion Docket (`sol_promotion_docket.py`, `sol_court_supervised_promotion.py`).
2. Final Gate Registry (`11/11` L50 final gates + `12/12` SovereignRuntime gates) & Finalization Docket
   (`sol_final_gate_registry.py`, `sol_finalization_docket.py`).
3. Governance Freeze (`10/10` invariants), System Lockdown (`12/12` settings, `20/20` frozen components),
   and fail-closed production gateway (`allow_production_execution == False`, `authorized_claimed == False`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

_THIS_FILE = Path(__file__).resolve()
_SOL_CONTINUUM_ROOT = _THIS_FILE.parents[1]
_SOL_SYSTEMS_ROOT = _SOL_CONTINUUM_ROOT.parent

for _p in (
    _SOL_SYSTEMS_ROOT,
    _SOL_SYSTEMS_ROOT / "sol-decide",
    _SOL_SYSTEMS_ROOT / "sol-edge" / "src",
    _SOL_SYSTEMS_ROOT / "sol-change",
    _SOL_SYSTEMS_ROOT / "Frontier_OS",
):
    _ps = str(_p)
    if _p.exists() and _ps not in sys.path:
        sys.path.insert(0, _ps)

from .autopoietic_organism import EXPECTED_CORE_GRAPH_SHA256, verify_core_graph_immutability
from sol_decide.interop.sovereign_court_lockdown_bridge import (
    SolEdgeSovereignLockdownGate,
    SovereignCourtLockdownOrchestrator,
)


@dataclass(frozen=True)
class SovereignCourtLockdownReport:
    """Structured `sol_continuum` report for Frontier Z (Vector 29)."""

    evaluation: dict[str, Any]
    core_immutability_verified: bool
    core_graph_sha256: str

    @property
    def sovereign_court_lockdown_verified(self) -> bool:
        edge_gate = self.evaluation.get("edge_gate", {})
        return bool(
            edge_gate.get("policy_gate_passed") is True
            and self.evaluation.get("allow_production_execution") is False
            and self.evaluation.get("authorized_claimed") is False
            and self.core_immutability_verified
            and self.core_graph_sha256 == EXPECTED_CORE_GRAPH_SHA256
        )

    @property
    def allow_production_execution(self) -> bool:
        return bool(self.evaluation.get("allow_production_execution", False))

    @property
    def authorized_claimed(self) -> bool:
        return bool(self.evaluation.get("authorized_claimed", False))

    @property
    def summary_digest(self) -> str:
        return str(self.evaluation.get("artifact_digest", ""))

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.evaluation)
        payload["sovereign_court_lockdown_verified"] = self.sovereign_court_lockdown_verified
        payload["core_immutability_verified"] = self.core_immutability_verified
        payload["core_graph_sha256"] = self.core_graph_sha256
        return payload


class SovereignCourtLockdownEngine:
    """
    `sol_continuum` engine for Frontier Z (Vector 29):
    Sovereign Court Promotion Docket, Final Gate Registry & System Lockdown Closure.
    """

    def __init__(self, *, orchestrator: SovereignCourtLockdownOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or SovereignCourtLockdownOrchestrator()
        self.gate = SolEdgeSovereignLockdownGate()

    def evaluate(
        self,
        *,
        attempt_production_execution: bool = False,
    ) -> SovereignCourtLockdownReport:
        eval_payload = self.orchestrator.run_sovereign_court_lockdown_evaluation()
        if attempt_production_execution:
            if eval_payload.get("allow_production_execution") or eval_payload.get("authorized_claimed"):
                raise RuntimeError("Production execution or self-authorization must remain fail-closed")
            rt_gw = eval_payload.get("sovereign_runtime_and_gateway", {})
            if (
                not rt_gw.get("production_command_blocked_and_held", False)
                or rt_gw.get("gateway_production_mutation_decision") != "deny"
            ):
                raise RuntimeError("Production gateway block check failed")
        core_ok, core_sha = verify_core_graph_immutability()
        return SovereignCourtLockdownReport(
            evaluation=eval_payload,
            core_immutability_verified=core_ok,
            core_graph_sha256=core_sha,
        )

    def run_episode(
        self,
        *,
        study_name: str = "Frontier_Z_Sovereign_Court_Final_Gate_System_Lockdown",
        trial_count: int = 5,
        experiments_root: str | Path | None = None,
        observatory_db_path: str | Path | None = None,
        register_in_observatory_db: bool = True,
        export_packet_path: str | Path | None = None,
    ) -> Any:
        return self.orchestrator.run_episode(
            study_name=study_name,
            trial_count=trial_count,
            experiments_root=Path(experiments_root) if experiments_root is not None else None,
            observatory_db_path=Path(observatory_db_path) if observatory_db_path is not None else None,
            register_in_observatory_db=register_in_observatory_db,
            export_packet_path=Path(export_packet_path) if export_packet_path is not None else None,
        )


__all__ = [
    "SolEdgeSovereignLockdownGate",
    "SovereignCourtLockdownEngine",
    "SovereignCourtLockdownOrchestrator",
    "SovereignCourtLockdownReport",
]
