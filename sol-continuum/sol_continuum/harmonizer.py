"""
Full A–Z Capstone Harmonizer (`sol_continuum.harmonizer`)
=========================================================

Unifies `FrontierNAutopoieticHarmonizer` with the Phase III Capstone engines:
- Frontier X (Vector 27): `EntangledCadenceWavefrontEngine`
- Frontier Y (Vector 28): `WaveguideChannelStagingEngine`
- Frontier Z (Vector 29): `SovereignCourtLockdownEngine`
while strictly verifying sacred `default_graph.json` SHA-256 immutability and
fail-closed governance (`allow_production_execution == False`, `authorized_claimed == False`).
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from .autopoietic_organism import (
    EXPECTED_CORE_GRAPH_SHA256,
    FrontierNAutopoieticHarmonizer,
    FrontierNAutopoieticReport,
    verify_core_graph_immutability,
)
from .entangled_cadence import EntangledCadenceReport, EntangledCadenceWavefrontEngine
from .sovereign_lockdown import SovereignCourtLockdownEngine, SovereignCourtLockdownReport
from .waveguide_channels import WaveguideChannelStagingEngine, WaveguideChannelStagingReport


@dataclass(frozen=True)
class FrontierXYZCapstoneReport:
    """Combined verification report for Frontiers X, Y, and Z in `sol_continuum`."""

    frontier_x: EntangledCadenceReport
    frontier_y: WaveguideChannelStagingReport
    frontier_z: SovereignCourtLockdownReport
    core_immutability_verified: bool
    core_graph_sha256: str
    allow_production_execution: bool
    authorized_claimed: bool
    all_verified: bool
    capstone_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "frontier_x": self.frontier_x.to_dict(),
            "frontier_y": self.frontier_y.to_dict(),
            "frontier_z": self.frontier_z.to_dict(),
            "core_immutability_verified": self.core_immutability_verified,
            "core_graph_sha256": self.core_graph_sha256,
            "allow_production_execution": self.allow_production_execution,
            "authorized_claimed": self.authorized_claimed,
            "all_verified": self.all_verified,
            "capstone_digest": self.capstone_digest,
        }


class FrontierXYZCapstoneHarmonizer:
    """
    Coordinates Frontiers X, Y, and Z inside `sol_continuum` alongside
    `FrontierNAutopoieticHarmonizer`.
    """

    def __init__(self) -> None:
        self.autopoietic_harmonizer = FrontierNAutopoieticHarmonizer()
        self.frontier_x_engine = EntangledCadenceWavefrontEngine()
        self.frontier_y_engine = WaveguideChannelStagingEngine()
        self.frontier_z_engine = SovereignCourtLockdownEngine()

    def evaluate_capstone_xyz(self) -> FrontierXYZCapstoneReport:
        fx = self.frontier_x_engine.evaluate()
        fy = self.frontier_y_engine.evaluate()
        fz = self.frontier_z_engine.evaluate()
        core_ok, core_sha = verify_core_graph_immutability()

        allow_prod = bool(
            fx.allow_production_execution
            or fy.allow_production_execution
            or fz.allow_production_execution
        )
        auth_claimed = bool(
            fx.authorized_claimed
            or fy.authorized_claimed
            or fz.authorized_claimed
        )
        all_ok = bool(
            fx.entangled_cadence_verified
            and fy.waveguide_channel_staging_verified
            and fz.sovereign_court_lockdown_verified
            and core_ok
            and core_sha == EXPECTED_CORE_GRAPH_SHA256
            and not allow_prod
            and not auth_claimed
        )
        canonical = json.dumps(
            {
                "fx": fx.summary_digest,
                "fy": fy.summary_digest,
                "fz": fz.summary_digest,
                "core_sha256": core_sha,
                "all_ok": all_ok,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return FrontierXYZCapstoneReport(
            frontier_x=fx,
            frontier_y=fy,
            frontier_z=fz,
            core_immutability_verified=core_ok,
            core_graph_sha256=core_sha,
            allow_production_execution=allow_prod,
            authorized_claimed=auth_claimed,
            all_verified=all_ok,
            capstone_digest=digest,
        )


__all__ = [
    "EXPECTED_CORE_GRAPH_SHA256",
    "FrontierNAutopoieticHarmonizer",
    "FrontierNAutopoieticReport",
    "FrontierXYZCapstoneHarmonizer",
    "FrontierXYZCapstoneReport",
    "verify_core_graph_immutability",
]
