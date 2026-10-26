"""
Frontier Y (Vector 28): Waveguide Channel Library, Layout Crosstalk Compaction & Local Staging Engine
=====================================================================================================

Provides `WaveguideChannelStagingEngine` and `WaveguideChannelStagingReport` inside `sol_continuum`,
orchestrating:
1. Canonical waveguide channel kernel recognition & `CHANNEL_RAW` hazard rejection (`sol_waveguide_channel_kernel_library.py`,
   `sol_waveguide_channel_kernel_recognizer.py`, `sol_waveguide_channel_dependency.py`).
2. Waveguide layout optimizer & pipeline compaction equivalence (`sol_waveguide_layout_optimizer.py`,
   `sol_waveguide_pipeline_compaction.py`).
3. No-op dry-run package runner (`182` events) & controlled local staging (`28` files) with
   zero archive/upload/deploy/source-mutation (`sol_waveguide_package_runner_noop_dry_run_transcript.py`,
   `sol_waveguide_package_assembly_physical_execution_gate.py`,
   `sol_waveguide_package_controlled_local_staging_plan.py`,
   `sol_waveguide_package_controlled_local_staging_runner.py`).
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
from sol_decide.interop.waveguide_channel_staging_bridge import (
    SolEdgeWaveguideChannelGate,
    WaveguideChannelStagingOrchestrator,
)


@dataclass(frozen=True)
class WaveguideChannelStagingReport:
    """Structured `sol_continuum` report for Frontier Y (Vector 28)."""

    evaluation: dict[str, Any]
    core_immutability_verified: bool
    core_graph_sha256: str

    @property
    def waveguide_channel_staging_verified(self) -> bool:
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
        payload["waveguide_channel_staging_verified"] = self.waveguide_channel_staging_verified
        payload["core_immutability_verified"] = self.core_immutability_verified
        payload["core_graph_sha256"] = self.core_graph_sha256
        return payload


class WaveguideChannelStagingEngine:
    """
    `sol_continuum` engine for Frontier Y (Vector 28):
    Waveguide Channel Library, Layout Crosstalk Compaction & Controlled Local Staging.
    """

    def __init__(self, *, orchestrator: WaveguideChannelStagingOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or WaveguideChannelStagingOrchestrator()
        self.gate = SolEdgeWaveguideChannelGate()

    def evaluate(
        self,
        *,
        inject_cycle0_raw_hazard: bool = False,
    ) -> WaveguideChannelStagingReport:
        eval_payload = self.orchestrator.run_waveguide_channel_staging_evaluation()
        if inject_cycle0_raw_hazard:
            chan_dep = eval_payload.get("channel_dependency", {})
            staging = eval_payload.get("controlled_local_staging", {})
            if (
                not chan_dep.get("raw_hazard_detected_on_conflict", False)
                or staging.get("blocked_unapproved_status") != "package_local_staging_run_blocked"
            ):
                raise RuntimeError("Cycle 0 RAW hazard / unapproved staging injection failed to trigger quarantine/block")
        core_ok, core_sha = verify_core_graph_immutability()
        return WaveguideChannelStagingReport(
            evaluation=eval_payload,
            core_immutability_verified=core_ok,
            core_graph_sha256=core_sha,
        )

    def run_episode(
        self,
        *,
        study_name: str = "Frontier_Y_Waveguide_Channel_Layout_Local_Staging",
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
    "SolEdgeWaveguideChannelGate",
    "WaveguideChannelStagingEngine",
    "WaveguideChannelStagingOrchestrator",
    "WaveguideChannelStagingReport",
]
