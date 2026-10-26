"""
Frontier X (Vector 27): Entangled Multi-Manifold 2PC, Resonant Cadence & Wavefront Synthesis Engine
====================================================================================================

Provides `EntangledCadenceWavefrontEngine` and `EntangledCadenceReport` inside `sol_continuum`,
orchestrating:
1. 4-manifold entangled Kuramoto phase-lock & shadow 2-Phase Commit (`sol_entangled_sequencer.py`,
   `sol_entangled_atomic_epoch.py`, `sol_entangled_commit_epoch.py`).
2. Resonant temporal cadence skew alignment & bounded autonomy guard (`sol_temporal_cadence.py`,
   `sol_multimanifold_cadence_sync.py`, `sol_autonomous_cadence_sync.py`, `sol_cadence_autonomy_guard.py`).
3. Wavefront interference alignment, uncertainty calibration & 4-Ranger squadron audit
   (`sol_wavefront_alignment_coordinator.py`, `sol_wavefront_alignment_stabilizer.py`,
   `sol_wavefront_uncertainty_window.py`, `CadenceRanger`, `ResonantCadenceRanger`,
   `EntangledCommitRanger`, `ManifoldSyncRanger`).
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
from sol_decide.interop.entangled_cadence_wavefront_bridge import (
    EntangledCadenceWavefrontOrchestrator,
    SolEdgeEntangledCadenceGate,
)


@dataclass(frozen=True)
class EntangledCadenceReport:
    """Structured `sol_continuum` report for Frontier X (Vector 27)."""

    evaluation: dict[str, Any]
    core_immutability_verified: bool
    core_graph_sha256: str

    @property
    def entangled_cadence_verified(self) -> bool:
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
        payload["entangled_cadence_verified"] = self.entangled_cadence_verified
        payload["core_immutability_verified"] = self.core_immutability_verified
        payload["core_graph_sha256"] = self.core_graph_sha256
        return payload


class EntangledCadenceWavefrontEngine:
    """
    `sol_continuum` engine for Frontier X (Vector 27):
    Entangled Multi-Manifold 2PC, Resonant Cadence & Wavefront Synthesis.
    """

    def __init__(self, *, orchestrator: EntangledCadenceWavefrontOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or EntangledCadenceWavefrontOrchestrator()
        self.gate = SolEdgeEntangledCadenceGate()

    def evaluate(
        self,
        *,
        manifold_count: int = 4,
        steps: int = 180,
        inject_cycle0_fault: bool = False,
    ) -> EntangledCadenceReport:
        if manifold_count < 2:
            raise ValueError(f"manifold_count must be >= 2, got {manifold_count}")
        if steps < 10:
            raise ValueError(f"steps must be >= 10, got {steps}")

        eval_payload = self.orchestrator.run_entangled_cadence_evaluation()
        if inject_cycle0_fault:
            ent_commit = eval_payload.get("entangled_commit", {})
            res_sched = eval_payload.get("resonant_schedule", {})
            if (
                ent_commit.get("fault_abort_status") != "aborted"
                or not ent_commit.get("fault_rollback_performed", False)
                or res_sched.get("cycle0_guard_passed", True) is not False
            ):
                raise RuntimeError("Cycle 0 fault injection failed to trigger abort/rollback/guard rejection")
        core_ok, core_sha = verify_core_graph_immutability()
        return EntangledCadenceReport(
            evaluation=eval_payload,
            core_immutability_verified=core_ok,
            core_graph_sha256=core_sha,
        )

    def run_episode(
        self,
        *,
        study_name: str = "Frontier_X_Entangled_Cadence_Wavefront_2PC",
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
    "EntangledCadenceReport",
    "EntangledCadenceWavefrontEngine",
    "EntangledCadenceWavefrontOrchestrator",
    "SolEdgeEntangledCadenceGate",
]
