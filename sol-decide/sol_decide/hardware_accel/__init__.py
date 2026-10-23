"""
SOL-Decide Hardware Acceleration Package (`sol_decide.hardware_accel`)
======================================================================
Frontier O (Vector 19): WebGPU WGSL Trade-Space Exhaustion & MSCK Cohomological Inflection Prover.
"""

from .wgsl_decision_prover import (
    MSCKInflectionSurfacePoint,
    SolEdgeWGSLDecisionGate,
    WGSLCycleAuditResult,
    WGSLDecisionProverEpisodeRecord,
    WGSLDecisionProverOrchestrator,
    WGSLMSCKInflectionReport,
    WGSLProverReasoningTelemetry,
    WGSLTradeSpaceCalibrationSpec,
    WGSLTradeSpaceSweepReport,
    build_wgsl_prover_cycle_events,
)

__all__ = [
    "MSCKInflectionSurfacePoint",
    "SolEdgeWGSLDecisionGate",
    "WGSLCycleAuditResult",
    "WGSLDecisionProverEpisodeRecord",
    "WGSLDecisionProverOrchestrator",
    "WGSLMSCKInflectionReport",
    "WGSLProverReasoningTelemetry",
    "WGSLTradeSpaceCalibrationSpec",
    "WGSLTradeSpaceSweepReport",
    "build_wgsl_prover_cycle_events",
]
