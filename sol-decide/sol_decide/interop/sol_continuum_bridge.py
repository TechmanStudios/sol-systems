"""
Frontier I Interop Bridge: Connects `sol-decide` with the `sol-continuum` workspace
(`c:\\sol-systems\\sol-continuum`) and the SOL Change Observatory (`c:\\sol-systems\\sol-change`).
"""

from __future__ import annotations

import sys
from pathlib import Path

_SOL_SYSTEMS_ROOT = Path(__file__).resolve().parents[3]
_SOL_CONTINUUM_ROOT = _SOL_SYSTEMS_ROOT / "sol-continuum"
_SOL_CHANGE_ROOT = _SOL_SYSTEMS_ROOT / "sol-change"

for _p in (_SOL_CONTINUUM_ROOT, _SOL_CHANGE_ROOT):
    _ps = str(_p)
    if _p.exists() and _ps not in sys.path:
        sys.path.insert(0, _ps)

from sol_continuum import (
    COMMAND_PROTOCOL_VERBS,
    SKILL_DIMENSIONS,
    ChangeObservatoryBridge,
    ContinuumAgentGuild,
    ContinuumAgentNode,
    ContinuumDiscoveryAuditResult,
    ContinuumDiscoveryEpisodeRecord,
    ContinuumDiscoveryProposalSpec,
    LuminaLibraryObservatoryOrchestrator,
    LuminaObservatoryEpisodeRecord,
    LuminaRangerObservatoryProposalSpec,
    LuminaSovereignAuditResult,
    SolContinuumDiscoveryOrchestrator,
    SolEdgeContinuumDiscoveryGate,
    SolEdgeLuminaSovereignGate,
)

__all__ = [
    "COMMAND_PROTOCOL_VERBS",
    "SKILL_DIMENSIONS",
    "ChangeObservatoryBridge",
    "ContinuumAgentGuild",
    "ContinuumAgentNode",
    "ContinuumDiscoveryAuditResult",
    "ContinuumDiscoveryEpisodeRecord",
    "ContinuumDiscoveryProposalSpec",
    "LuminaLibraryObservatoryOrchestrator",
    "LuminaObservatoryEpisodeRecord",
    "LuminaRangerObservatoryProposalSpec",
    "LuminaSovereignAuditResult",
    "SolContinuumDiscoveryOrchestrator",
    "SolEdgeContinuumDiscoveryGate",
    "SolEdgeLuminaSovereignGate",
]

