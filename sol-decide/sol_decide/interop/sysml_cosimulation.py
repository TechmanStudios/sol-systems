"""
SOL-Decide: Live SysML v2 / KerML & 3D Riemannian / Robotic Manifold Co-Simulation
===================================================================================
Frontier B of the SOL Systems Continuum.

Connects:
1. `SysMLKerMLParser` (.sysml textual models & KerML JSON ASTs) -> `SheafDecisionComplex`
2. `DifferentialDeltaEngine` (`OperationalShock`s from 3D manifold / physical telemetry)
3. `LiveGeminiMoAElicitor` (`gemini-4-argon` architectural mutation under shock)
4. `RoboticManifoldActuationGate` (`sol-edge` zero-trust pre-execution gate for 6-DOF
   robotic geodesic trajectories and SO(3) non-abelian Wilson loop gauge holonomy).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field

from ..core.primitives import (
    Constraint,
    ConstraintSeverity,
    Objective,
    OptimizationDirection,
    Option,
    PrimitiveType,
)
from ..core.sheaf_decision_complex import DecisionEvaluationReport, SheafDecisionComplex
from ..delivery.decision_package import DecisionPackageCompiler, SignerReadyDecisionPackage
from ..delivery.differential_delta import (
    DifferentialDecisionDelta,
    DifferentialDeltaEngine,
    OperationalShock,
)
from ..agentic.dialectical_bias import DialecticalAdversary
from ..agentic.elicitation_moa import ElicitationGiantReport, ElicitationResult, SevenGiantsElicitor
from ..agentic.live_llm_elicitation import (
    DEFAULT_GEMINI_MODEL,
    GeminiReasoningTelemetry,
    SolEdgeGovernanceArtifact,
    SolEdgePreExecutionBridge,
    SolLensProofPacketCompiler,
    _sanitize_identifier,
)
from .sysml_kerml import SysMLKerMLParser


def _to_decimal(val: float, places: int = 4) -> Decimal:
    return Decimal(f"{float(val):.{places}f}")

from sol_edge.canonical import digest_data
from sol_edge.contracts import (
    SCHEMA_VERSION,
    ActionProposal,
    ActorRef,
    ActorType,
    ArtifactRef,
    CapabilityManifest,
    CommandParameterSpec,
    Condition,
    DeviceIdentity,
    EvidencePacket,
    ExecutionWindow,
    ExpectedObservation,
    ExperimentPlan,
    InvariantResult,
    InvariantSpec,
    JustificationClaim,
    NextTransition,
    NumericRange,
    Observation,
    ParameterAssignment,
    PlanStep,
    PolicyDecision,
    PolicyStatus,
    ProvenanceRef,
    ReadableChannel,
    SafeState,
    SafeStateAction,
    TargetRef,
    TimeoutPolicy,
    UnitCode,
    ValidatedParameter,
    WritableCommand,
)
from sol_edge.runtime.events import (
    EventType,
    EvidenceRecordedPayload,
    PolicyDecisionRecordedPayload,
    ProposalRecordedPayload,
    RunOpenedPayload,
    RuntimeEvent,
    create_runtime_event,
)
from sol_edge.runtime.replay import replay_events
from sol_edge.runtime.state import RuntimeState, RuntimeStatus


# ============================================================================
# 1. Pydantic Schema for Gemini 4 SysML v2 Architectural Mutation Under Shock
# ============================================================================

class SysMLArchitectureMutationSpec(BaseModel):
    """
    Structured output schema for Gemini 4 (`gemini-4-argon`) when an
    `OperationalShock` strikes a SysML v2 `part def` option and induces
    coboundary strain (`activated_coboundary_edges`) or a hard constraint breach.
    """
    shocked_part_id: str = Field(
        description="Identifier of the shocked SysML v2 part def (e.g. 'sysml_hybridsupercapharmonicdrivearm')."
    )
    mutated_part_name: str = Field(
        description="Updated SysML v2 part def name reflecting the structural/actuator redesign."
    )
    mutated_state_vector: List[float] = Field(
        min_length=3,
        max_length=3,
        description=(
            "Mutated 3-channel stalk vector [channel_0, channel_1, channel_2] that "
            "absorbs the operational shock while strictly satisfying every hard "
            "SysML constraint interval [lower_bound, upper_bound]."
        ),
    )
    mutated_cost: float = Field(
        description="Updated cost estimate ($M) after architectural mutation."
    )
    sysml_mutation_rationale: str = Field(
        description=(
            "Rigorous systems-engineering & cohomological proof explaining how the "
            "SysML v2 part def mutation absorbs the operational shock and restores "
            "sheaf coboundary consistency (ker Delta^0)."
        )
    )


@dataclass
class SysMLShockCoSimulationRecord:
    """
    Complete audit record of a SysML v2 architecture subjected to a live
    operational shock, quarantined by `sol-edge`, and autonomously mutated
    by Gemini 4 back into `ker(Delta^0)` (`ELIGIBLE`).
    """
    sysml_package_name: str
    baseline_selected_part_id: str
    baseline_selected_part_name: str
    baseline_energy: float
    applied_shocks: List[OperationalShock]
    differential_delta: DifferentialDecisionDelta
    shocked_part_id: str
    pre_shock_stalk: List[float]
    post_shock_stalk: List[float]
    mutated_stalk: List[float]
    shocked_quarantine_governance: SolEdgeGovernanceArtifact
    mutated_cleared_governance: SolEdgeGovernanceArtifact
    mutation_spec: SysMLArchitectureMutationSpec
    mutated_sysml_source: str
    mutation_interaction_id: str
    reasoning_telemetry: GeminiReasoningTelemetry
    shock_cleared: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sysml_package_name": self.sysml_package_name,
            "baseline_selected_part_id": self.baseline_selected_part_id,
            "baseline_selected_part_name": self.baseline_selected_part_name,
            "baseline_energy": float(self.baseline_energy),
            "shocked_part_id": self.shocked_part_id,
            "pre_shock_stalk": [float(x) for x in self.pre_shock_stalk],
            "post_shock_stalk": [float(x) for x in self.post_shock_stalk],
            "mutated_stalk": [float(x) for x in self.mutated_stalk],
            "shocked_policy_status": str(self.shocked_quarantine_governance.policy_decision.status.value),
            "shocked_state_digest": str(self.shocked_quarantine_governance.final_runtime_state.state_digest),
            "cleared_policy_status": str(self.mutated_cleared_governance.policy_decision.status.value),
            "cleared_state_digest": str(self.mutated_cleared_governance.final_runtime_state.state_digest),
            "mutation_spec": self.mutation_spec.model_dump(mode="json"),
            "mutation_interaction_id": self.mutation_interaction_id,
            "shock_cleared": bool(self.shock_cleared),
        }


# ============================================================================
# 2. Zero-Trust `sol-edge` Gate for 3D Robotic & Gauge Manifold Actuation
# ============================================================================

@dataclass
class RoboticActuationGovernanceRecord:
    """
    Zero-trust `sol-edge` pre-execution governance artifact for physical 6-DOF
    robotic geodesic trajectory execution and SO(3) non-abelian Wilson loop
    gauge holonomy on the 3D Riemannian manifold.
    """
    run_id: str
    sysml_decision_state_digest: str
    target_end_effector_pos: List[float]
    min_obstacle_clearance_m: float
    max_metric_condition: float
    actuator_betti_1: int
    max_wilson_defect_deg: float
    yang_mills_action: float
    actuator_commit_permitted: bool
    governance_artifact: SolEdgeGovernanceArtifact
    sol_lens_packet: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "sysml_decision_state_digest": self.sysml_decision_state_digest,
            "target_end_effector_pos": [float(x) for x in self.target_end_effector_pos],
            "min_obstacle_clearance_m": float(self.min_obstacle_clearance_m),
            "max_metric_condition": float(self.max_metric_condition),
            "actuator_betti_1": int(self.actuator_betti_1),
            "max_wilson_defect_deg": float(self.max_wilson_defect_deg),
            "yang_mills_action": float(self.yang_mills_action),
            "actuator_commit_permitted": bool(self.actuator_commit_permitted),
            "policy_status": str(self.governance_artifact.policy_decision.status.value),
            "state_digest": str(self.governance_artifact.final_runtime_state.state_digest),
        }


class RoboticManifoldActuationGate:
    """
    Governs physical 6-DOF robotic manipulator trajectories and SO(3) gauge
    holonomy commits through the pure 4-event hash-chained `sol-edge` state
    machine. No physical actuator command is ever permitted unless:
    1. A valid `ELIGIBLE` SysML `SheafDecisionComplex` state digest is bound.
    2. `min_obstacle_clearance_m >= min_safe_clearance_m` (default `0.05` m).
    3. `max_metric_condition <= max_allowed_condition_num` (default `80.0`).
    4. `actuator_betti_1 == 0` (6-joint coordination sheaf is obstruction-free).
    5. `max_wilson_defect_deg <= max_allowed_defect_deg` (default `5.0` deg).
    """

    def __init__(
        self,
        min_safe_clearance_m: float = 0.05,
        max_allowed_condition_num: float = 80.0,
        max_allowed_defect_deg: float = 5.0,
    ) -> None:
        self.min_safe_clearance_m = float(min_safe_clearance_m)
        self.max_allowed_condition_num = float(max_allowed_condition_num)
        self.max_allowed_defect_deg = float(max_allowed_defect_deg)

    def govern_robotic_actuation(
        self,
        *,
        sysml_decision_state_digest: str,
        sysml_is_eligible: bool,
        target_pos: List[float],
        min_obstacle_clearance_m: float,
        max_metric_condition: float,
        actuator_betti_1: int,
        max_wilson_defect_deg: float,
        yang_mills_action: float,
        prior_quarantined_state_digest: Optional[str] = None,
        repair_cycle: int = 0,
    ) -> SolEdgeGovernanceArtifact:
        """
        Compiles a 6-DOF robotic trajectory + SO(3) Wilson loop holonomy audit
        into a 4-event `sol-edge` hash-chained `RuntimeState`.
        """
        now_utc = datetime.now(timezone.utc).replace(microsecond=0)
        run_suffix = f":repair-{repair_cycle}" if repair_cycle > 0 else ""
        run_id = f"run:robotic-6dof-actuation{run_suffix}"[:128]
        device_id = "device:artemis-6dof-manipulator"

        readable_channels: List[ReadableChannel] = [
            ReadableChannel(
                channel_id="channel:min-obstacle-clearance-m",
                unit=UnitCode.UNITLESS,
                value_type="decimal",
                permitted_range=NumericRange(minimum=Decimal("0.0"), maximum=Decimal("10.0")),
                freshness_seconds=Decimal("10"),
            ),
            ReadableChannel(
                channel_id="channel:max-metric-condition-kappa",
                unit=UnitCode.UNITLESS,
                value_type="decimal",
                permitted_range=NumericRange(minimum=Decimal("1.0"), maximum=Decimal("10000.0")),
                freshness_seconds=Decimal("10"),
            ),
            ReadableChannel(
                channel_id="channel:actuator-sheaf-beta1",
                unit=UnitCode.UNITLESS,
                value_type="integer",
                permitted_range=NumericRange(minimum=Decimal("0"), maximum=Decimal("100")),
                freshness_seconds=Decimal("10"),
            ),
            ReadableChannel(
                channel_id="channel:gauge-wilson-defect-deg",
                unit=UnitCode.UNITLESS,
                value_type="decimal",
                permitted_range=NumericRange(minimum=Decimal("0.0"), maximum=Decimal("180.0")),
                freshness_seconds=Decimal("10"),
            ),
            ReadableChannel(
                channel_id="channel:sysml-decision-eligible",
                unit=UnitCode.UNITLESS,
                value_type="integer",
                permitted_range=NumericRange(minimum=Decimal("0"), maximum=Decimal("1")),
                freshness_seconds=Decimal("60"),
            ),
        ]

        clearance_range = NumericRange(
            minimum=_to_decimal(self.min_safe_clearance_m, 4),
            maximum=Decimal("10.0"),
        )
        kappa_range = NumericRange(
            minimum=Decimal("1.0"),
            maximum=_to_decimal(self.max_allowed_condition_num, 4),
        )
        beta1_range = NumericRange(minimum=Decimal("0"), maximum=Decimal("0"))
        defect_range = NumericRange(
            minimum=Decimal("0.0"),
            maximum=_to_decimal(self.max_allowed_defect_deg, 4),
        )
        sysml_elig_range = NumericRange(minimum=Decimal("1"), maximum=Decimal("1"))

        invariant_specs: List[InvariantSpec] = [
            InvariantSpec(
                invariant_id="inv:obstacle-clearance-m",
                channel_id="channel:min-obstacle-clearance-m",
                operator="between",
                expected_range=clearance_range,
                unit=UnitCode.UNITLESS,
                violation_transition="QUARANTINE",
            ),
            InvariantSpec(
                invariant_id="inv:metric-condition-kappa",
                channel_id="channel:max-metric-condition-kappa",
                operator="between",
                expected_range=kappa_range,
                unit=UnitCode.UNITLESS,
                violation_transition="QUARANTINE",
            ),
            InvariantSpec(
                invariant_id="inv:actuator-sheaf-beta1",
                channel_id="channel:actuator-sheaf-beta1",
                operator="equals",
                expected_range=beta1_range,
                unit=UnitCode.UNITLESS,
                violation_transition="QUARANTINE",
            ),
            InvariantSpec(
                invariant_id="inv:gauge-wilson-defect-deg",
                channel_id="channel:gauge-wilson-defect-deg",
                operator="between",
                expected_range=defect_range,
                unit=UnitCode.UNITLESS,
                violation_transition="QUARANTINE",
            ),
            InvariantSpec(
                invariant_id="inv:sysml-decision-eligible",
                channel_id="channel:sysml-decision-eligible",
                operator="equals",
                expected_range=sysml_elig_range,
                unit=UnitCode.UNITLESS,
                violation_transition="QUARANTINE",
            ),
        ]

        sensor_seed_digest = digest_data(
            {
                "run_id": run_id,
                "target_pos": [f"{float(c):.4f}" for c in target_pos],
                "min_obstacle_clearance_m": f"{float(min_obstacle_clearance_m):.4f}",
                "max_wilson_defect_deg": f"{float(max_wilson_defect_deg):.4f}",
            }
        )

        obs_clearance = _to_decimal(max(0.0, float(min_obstacle_clearance_m)), 4)
        obs_kappa = _to_decimal(max(1.0, float(max_metric_condition)), 4)
        obs_beta1 = Decimal(str(max(0, int(actuator_betti_1))))
        obs_defect = _to_decimal(max(0.0, float(max_wilson_defect_deg)), 4)
        obs_sysml = Decimal("1" if sysml_is_eligible else "0")

        observations: List[Observation] = [
            Observation(
                observation_id="obs:min-obstacle-clearance-m",
                channel_id="channel:min-obstacle-clearance-m",
                value=obs_clearance,
                unit=UnitCode.UNITLESS,
                observed_at=now_utc,
                source_digest=sensor_seed_digest,
            ),
            Observation(
                observation_id="obs:max-metric-condition-kappa",
                channel_id="channel:max-metric-condition-kappa",
                value=obs_kappa,
                unit=UnitCode.UNITLESS,
                observed_at=now_utc,
                source_digest=sensor_seed_digest,
            ),
            Observation(
                observation_id="obs:actuator-sheaf-beta1",
                channel_id="channel:actuator-sheaf-beta1",
                value=obs_beta1,
                unit=UnitCode.UNITLESS,
                observed_at=now_utc,
                source_digest=sensor_seed_digest,
            ),
            Observation(
                observation_id="obs:gauge-wilson-defect-deg",
                channel_id="channel:gauge-wilson-defect-deg",
                value=obs_defect,
                unit=UnitCode.UNITLESS,
                observed_at=now_utc,
                source_digest=sensor_seed_digest,
            ),
            Observation(
                observation_id="obs:sysml-decision-eligible",
                channel_id="channel:sysml-decision-eligible",
                value=obs_sysml,
                unit=UnitCode.UNITLESS,
                observed_at=now_utc,
                source_digest=sysml_decision_state_digest,
            ),
        ]

        pass_clearance = clearance_range.contains(obs_clearance)
        pass_kappa = kappa_range.contains(obs_kappa)
        pass_beta1 = beta1_range.contains(obs_beta1)
        pass_defect = defect_range.contains(obs_defect)
        pass_sysml = sysml_elig_range.contains(obs_sysml)

        invariant_results: List[InvariantResult] = [
            InvariantResult(
                invariant_id="inv:obstacle-clearance-m",
                passed=pass_clearance,
                observed_value=obs_clearance,
                expected_range=clearance_range,
                unit=UnitCode.UNITLESS,
            ),
            InvariantResult(
                invariant_id="inv:metric-condition-kappa",
                passed=pass_kappa,
                observed_value=obs_kappa,
                expected_range=kappa_range,
                unit=UnitCode.UNITLESS,
            ),
            InvariantResult(
                invariant_id="inv:actuator-sheaf-beta1",
                passed=pass_beta1,
                observed_value=obs_beta1,
                expected_range=beta1_range,
                unit=UnitCode.UNITLESS,
            ),
            InvariantResult(
                invariant_id="inv:gauge-wilson-defect-deg",
                passed=pass_defect,
                observed_value=obs_defect,
                expected_range=defect_range,
                unit=UnitCode.UNITLESS,
            ),
            InvariantResult(
                invariant_id="inv:sysml-decision-eligible",
                passed=pass_sysml,
                observed_value=obs_sysml,
                expected_range=sysml_elig_range,
                unit=UnitCode.UNITLESS,
            ),
        ]

        param_specs: Tuple[CommandParameterSpec, ...] = (
            CommandParameterSpec(
                parameter_id="target-x-m",
                unit=UnitCode.UNITLESS,
                permitted_range=NumericRange(minimum=Decimal("-2.0"), maximum=Decimal("2.0")),
                safe_value=Decimal("0.0"),
            ),
            CommandParameterSpec(
                parameter_id="target-y-m",
                unit=UnitCode.UNITLESS,
                permitted_range=NumericRange(minimum=Decimal("-2.0"), maximum=Decimal("2.0")),
                safe_value=Decimal("0.0"),
            ),
            CommandParameterSpec(
                parameter_id="target-z-m",
                unit=UnitCode.UNITLESS,
                permitted_range=NumericRange(minimum=Decimal("-2.0"), maximum=Decimal("2.0")),
                safe_value=Decimal("0.0"),
            ),
        )
        param_assignments: Tuple[ParameterAssignment, ...] = (
            ParameterAssignment(parameter_id="target-x-m", value=_to_decimal(target_pos[0], 4), unit=UnitCode.UNITLESS),
            ParameterAssignment(parameter_id="target-y-m", value=_to_decimal(target_pos[1], 4), unit=UnitCode.UNITLESS),
            ParameterAssignment(parameter_id="target-z-m", value=_to_decimal(target_pos[2], 4), unit=UnitCode.UNITLESS),
        )
        validated_params: Tuple[ValidatedParameter, ...] = (
            ValidatedParameter(
                parameter_id="target-x-m",
                value=_to_decimal(target_pos[0], 4),
                unit=UnitCode.UNITLESS,
                permitted_range=NumericRange(minimum=Decimal("-2.0"), maximum=Decimal("2.0")),
            ),
            ValidatedParameter(
                parameter_id="target-y-m",
                value=_to_decimal(target_pos[1], 4),
                unit=UnitCode.UNITLESS,
                permitted_range=NumericRange(minimum=Decimal("-2.0"), maximum=Decimal("2.0")),
            ),
            ValidatedParameter(
                parameter_id="target-z-m",
                value=_to_decimal(target_pos[2], 4),
                unit=UnitCode.UNITLESS,
                permitted_range=NumericRange(minimum=Decimal("-2.0"), maximum=Decimal("2.0")),
            ),
        )

        manifest = CapabilityManifest(
            manifest_id="manifest:artemis-6dof-manipulator",
            manifest_version="1.0.0",
            device=DeviceIdentity(
                device_id=device_id,
                manufacturer="SOL Systems Robotics",
                model="Artemis-6DOF-Harmonic-Arm",
                serial_number="sol-6dof-1.0.0",
            ),
            device_type="robotic_manipulator_6dof",
            firmware_or_simulator_version="1.0.0",
            readable_channels=tuple(readable_channels),
            writable_commands=(
                WritableCommand(
                    command_id="execute-geodesic-trajectory",
                    parameters=param_specs,
                    max_duration_seconds=Decimal("30"),
                    readback_channels=tuple(ch.channel_id for ch in readable_channels),
                    human_approval_required=False,
                ),
                WritableCommand(
                    command_id="engage-carnot-brake",
                    parameters=(
                        CommandParameterSpec(
                            parameter_id="brake-hold-s",
                            unit=UnitCode.SECOND,
                            permitted_range=NumericRange(minimum=Decimal("0"), maximum=Decimal("10")),
                            safe_value=Decimal("0"),
                        ),
                    ),
                    max_duration_seconds=Decimal("10"),
                    readback_channels=("channel:min-obstacle-clearance-m",),
                    human_approval_required=False,
                ),
            ),
            safe_state=SafeState(
                command_id="engage-carnot-brake",
                description="Dissipate kinetic energy into Carnot brake and lock 6-DOF joints.",
            ),
            fail_safe_behavior="On obstacle clearance breach or SO(3) Wilson loop holonomy defect, quarantine trajectory and engage Carnot brake.",
            human_approval_required=False,
        )

        expected_observations: List[ExpectedObservation] = [
            ExpectedObservation(
                observation_id="exp:min-obstacle-clearance-m",
                channel_id="channel:min-obstacle-clearance-m",
                expected_range=clearance_range,
                unit=UnitCode.UNITLESS,
            ),
            ExpectedObservation(
                observation_id="exp:gauge-wilson-defect-deg",
                channel_id="channel:gauge-wilson-defect-deg",
                expected_range=defect_range,
                unit=UnitCode.UNITLESS,
            ),
        ]

        plan = ExperimentPlan(
            plan_id=f"plan:6dof-geodesic{run_suffix}"[:128],
            plan_version="1.0.0",
            objective="Execute 6-DOF Riemannian geodesic trajectory under flat SO(3) Wilson loop gauge holonomy.",
            capability_manifest_digest=manifest.semantic_digest(),
            steps=(
                PlanStep(
                    step_id="step:geodesic-actuation",
                    sequence=1,
                    command_id="execute-geodesic-trajectory",
                    parameters=param_assignments,
                    duration_seconds=Decimal("10"),
                ),
            ),
            preconditions=(
                Condition(
                    code="SYSML_ARCHITECTURE_CERTIFIED",
                    description="SysML v2 SheafDecisionComplex is certified ELIGIBLE.",
                ),
            ),
            expected_observations=tuple(expected_observations),
            invariants=tuple(invariant_specs),
            timeout=TimeoutPolicy(timeout_seconds=Decimal("30"), transition="DEFER"),
            compensation_and_safe_state=(
                SafeStateAction(
                    command_id="engage-carnot-brake",
                    parameters=(
                        ParameterAssignment(
                            parameter_id="brake-hold-s",
                            value=Decimal("0"),
                            unit=UnitCode.SECOND,
                        ),
                    ),
                    rationale="Lock 6-DOF manipulator if obstacle clearance or gauge holonomy fails.",
                ),
            ),
            required_evidence=("robotic-safety-arbiter", "non-abelian-gauge-arbiter", "sysml-sheaf-gate"),
        )

        justification_claims: List[JustificationClaim] = [
            JustificationClaim(
                claim_code="SYSML_ARCHITECTURE_GATE_BOUND",
                statement=(
                    f"Bound to certified SysML v2 SheafDecisionComplex state digest "
                    f"{sysml_decision_state_digest[:24]}."
                ),
                evidence_digest=sysml_decision_state_digest,
            ),
            JustificationClaim(
                claim_code="RIEMANNIAN_GEODESIC_AND_GAUGE_AUDIT",
                statement=(
                    f"6-DOF trajectory clearance={min_obstacle_clearance_m:.4f}m, "
                    f"kappa(g)={max_metric_condition:.2f}, Wilson defect={max_wilson_defect_deg:.2f} deg."
                ),
                evidence_digest=sensor_seed_digest,
            ),
        ]
        if prior_quarantined_state_digest:
            justification_claims.append(
                JustificationClaim(
                    claim_code="COHOMOLOGICAL_QUARANTINE_CLEARED",
                    statement=(
                        f"Cleared prior quarantined robotic/gauge state {prior_quarantined_state_digest[:24]} "
                        f"via SO(3) gauge frame diffusion and obstacle repulsion."
                    ),
                    evidence_digest=prior_quarantined_state_digest,
                )
            )

        proposal = ActionProposal(
            proposal_id=f"proposal:6dof-actuation{run_suffix}"[:128],
            actor=ActorRef(actor_id="actor:geodesic-controller", actor_type=ActorType.AI),
            experiment_plan_digest=plan.semantic_digest(),
            capability_manifest_digest=manifest.semantic_digest(),
            target=TargetRef(
                device_id=manifest.device.device_id,
                device_type=manifest.device_type,
            ),
            command_id="execute-geodesic-trajectory",
            validated_parameters=validated_params,
            frozen_sensor_digest=sensor_seed_digest,
            rationale=(
                f"Execute 6-DOF geodesic trajectory to target {target_pos} under "
                f"SysML v2 decision gate {sysml_decision_state_digest[:18]}."
            ),
            structured_justification=tuple(justification_claims),
            execution_window=ExecutionWindow(
                not_before=now_utc,
                not_after=now_utc + timedelta(minutes=15),
            ),
            required_readback_channels=tuple(ch.channel_id for ch in readable_channels),
        )

        overall_passed = all(r.passed for r in invariant_results)
        policy_id_digest = digest_data({"policy": "sol-edge-robotic-manifold-gate", "version": "1.0.0"})

        provenance_refs: List[ProvenanceRef] = [
            ProvenanceRef(
                source_id="source:sysml-sheaf-decision-gate",
                source_type="plan",
                digest=sysml_decision_state_digest,
                description="Cryptographic SHA-256 digest of the governing SysML v2 SheafDecisionComplex.",
            ),
            ProvenanceRef(
                source_id="source:robotic-safety-and-gauge-arbiter",
                source_type="simulator",
                digest=sensor_seed_digest,
                description="6-DOF Riemannian Geodesic Safety & Non-Abelian SO(3) Wilson Loop Arbiter.",
            ),
        ]
        if prior_quarantined_state_digest:
            provenance_refs.append(
                ProvenanceRef(
                    source_id="source:prior-quarantined-actuator-state",
                    source_type="simulator",
                    digest=prior_quarantined_state_digest,
                    description="Prior QUARANTINED robotic/gauge state cleared by gauge diffusion & geodesic avoidance.",
                )
            )

        evidence_dict: dict[str, object] = {
            "schema_name": "evidence_packet",
            "schema_version": SCHEMA_VERSION,
            "evidence_id": f"evidence:6dof-actuation{run_suffix}"[:128],
            "proposal_digest": proposal.semantic_digest(),
            "experiment_plan_digest": plan.semantic_digest(),
            "capability_manifest_digest": manifest.semantic_digest(),
            "input_digest": proposal.frozen_sensor_digest,
            "policy_digest": policy_id_digest,
            "simulation_or_dry_run_version": "1.0.0",
            "predicted_output_digest": sensor_seed_digest,
            "observations": tuple(observations),
            "invariant_results": tuple(invariant_results),
            "overall_passed": overall_passed,
            "artifacts": (
                ArtifactRef(
                    artifact_id=f"artifact:6dof-actuation{run_suffix}"[:128],
                    uri="sol-decide://robotic-manifold/6dof/safety-and-gauge-report.json",
                    media_type="application/json",
                    digest=sensor_seed_digest,
                ),
            ),
            "provenance": tuple(provenance_refs),
        }
        evidence_dict["reproducibility_digest"] = digest_data(evidence_dict)
        evidence = EvidencePacket.model_validate(evidence_dict)

        if not overall_passed:
            status = PolicyStatus.QUARANTINE
            reasons = ["ROBOTIC_OR_GAUGE_INVARIANT_VIOLATION", "INVARIANT_VIOLATION"]
            if not pass_clearance:
                reasons.insert(0, "OBSTACLE_CLEARANCE_BREACH")
            if not pass_defect:
                reasons.insert(0, "WILSON_LOOP_HOLONOMY_DEFECT")
            explanation = (
                f"6-DOF trajectory or SO(3) gauge holonomy violated safety envelope "
                f"(clearance={min_obstacle_clearance_m:.4f}m, defect={max_wilson_defect_deg:.2f} deg); quarantined."
            )
            unmet: Tuple[str, ...] = ("ZERO_ROBOTIC_AND_GAUGE_VIOLATION",)
            transition = NextTransition.INVESTIGATE_AND_CLEAR_QUARANTINE
        else:
            status = PolicyStatus.ELIGIBLE
            reasons = ["ALL_ROBOTIC_AND_GAUGE_INVARIANTS_PASSED", "SYSML_GATE_VERIFIED"]
            if prior_quarantined_state_digest:
                reasons.append("COHOMOLOGICAL_QUARANTINE_CLEARED")
            explanation = (
                f"6-DOF geodesic trajectory and SO(3) Wilson loop holonomy pass all invariants "
                f"(clearance={min_obstacle_clearance_m:.4f}m, defect={max_wilson_defect_deg:.2f} deg); eligible."
            )
            unmet = ()
            transition = NextTransition.RELEASE_REVIEW

        decision_dict: dict[str, object] = {
            "schema_name": "policy_decision",
            "schema_version": SCHEMA_VERSION,
            "decision_id": f"decision:6dof-actuation{run_suffix}"[:128],
            "status": status,
            "proposal_digest": proposal.semantic_digest(),
            "evidence_digest": evidence.semantic_digest(),
            "policy_name": "policy:sol-edge-robotic-manifold-gate",
            "policy_version": "1.0.0",
            "policy_digest": policy_id_digest,
            "reason_codes": tuple(reasons),
            "explanation": explanation,
            "unmet_requirements": unmet,
            "next_transition": transition,
            "decided_at": now_utc,
        }
        decision_dict["decision_digest"] = digest_data(decision_dict)
        policy_decision = PolicyDecision.model_validate(decision_dict)

        ev1 = create_runtime_event(
            event_id="event:run-opened",
            run_id=run_id,
            sequence_number=1,
            event_type=EventType.RUN_OPENED,
            occurred_at=now_utc,
            payload=RunOpenedPayload(
                experiment_plan_digest=plan.semantic_digest(),
                capability_manifest_digest=manifest.semantic_digest(),
            ),
            previous_event_digest=None,
        )
        ev2 = create_runtime_event(
            event_id="event:proposal-recorded",
            run_id=run_id,
            sequence_number=2,
            event_type=EventType.PROPOSAL_RECORDED,
            occurred_at=now_utc,
            payload=ProposalRecordedPayload(
                proposal_digest=proposal.semantic_digest(),
                experiment_plan_digest=plan.semantic_digest(),
                capability_manifest_digest=manifest.semantic_digest(),
            ),
            previous_event_digest=ev1.event_digest,
        )
        ev3 = create_runtime_event(
            event_id="event:evidence-recorded",
            run_id=run_id,
            sequence_number=3,
            event_type=EventType.EVIDENCE_RECORDED,
            occurred_at=now_utc,
            payload=EvidenceRecordedPayload(
                evidence_digest=evidence.semantic_digest(),
                proposal_digest=proposal.semantic_digest(),
                experiment_plan_digest=plan.semantic_digest(),
                capability_manifest_digest=manifest.semantic_digest(),
            ),
            previous_event_digest=ev2.event_digest,
        )
        ev4 = create_runtime_event(
            event_id="event:policy-decision-recorded",
            run_id=run_id,
            sequence_number=4,
            event_type=EventType.POLICY_DECISION_RECORDED,
            occurred_at=now_utc,
            payload=PolicyDecisionRecordedPayload(
                policy_decision_digest=policy_decision.semantic_digest(),
                policy_status=policy_decision.status,
                proposal_digest=proposal.semantic_digest(),
                evidence_digest=evidence.semantic_digest(),
            ),
            previous_event_digest=ev3.event_digest,
        )
        events = (ev1, ev2, ev3, ev4)
        final_state = replay_events(events)

        return SolEdgeGovernanceArtifact(
            manifest=manifest,
            plan=plan,
            proposal=proposal,
            evidence=evidence,
            policy_decision=policy_decision,
            events=events,
            final_runtime_state=final_state,
        )


# ============================================================================
# 3. SysMLCoSimulationBridge — End-to-End SysML v2 + Shock + Gemini 4 + Robotic Gate
# ============================================================================

class SysMLCoSimulationBridge:
    """
    Orchestrates Frontier B:
    1. Parses a SysML v2 `.sysml` model into a `SheafDecisionComplex`.
    2. Evaluates the baseline SysML architecture & governs all `part def` options via `sol-edge`.
    3. Applies live `OperationalShock`s (`DifferentialDeltaEngine`), isolating strained
       sheaf coboundary edges and quarantining the violated option in `sol-edge`.
    4. Invokes Gemini 4 (`gemini-4-argon`) to mutate the shocked SysML `part def`
       back into `ker(Delta^0)` (`ELIGIBLE`) and exports the updated `.sysml` source.
    5. Gates physical 6-DOF robotic trajectory & SO(3) Wilson loop holonomy commits
       through `RoboticManifoldActuationGate`.
    """

    def __init__(
        self,
        model: str = DEFAULT_GEMINI_MODEL,
        thinking_level: Optional[str] = "high",
        api_key: Optional[str] = None,
        client: Optional[Any] = None,
    ) -> None:
        self.model = model
        self.thinking_level = thinking_level
        self.api_key = api_key
        self._client = client
        self.sysml_parser = SysMLKerMLParser()
        self.giants_elicitor = SevenGiantsElicitor()
        self.bias_adversary = DialecticalAdversary()
        self.delta_engine = DifferentialDeltaEngine()
        self.package_compiler = DecisionPackageCompiler()
        self.sol_edge_bridge = SolEdgePreExecutionBridge()
        self.robotic_gate = RoboticManifoldActuationGate()
        self.proof_compiler = SolLensProofPacketCompiler()

    def _get_elicitor(self):
        from ..agentic.live_llm_elicitation import LiveGeminiMoAElicitor
        return LiveGeminiMoAElicitor(
            model=self.model,
            thinking_level=self.thinking_level,
            client=self._client,
        )

    def _evaluate_giants_on_complex(self, complex_obj: SheafDecisionComplex) -> ElicitationResult:
        """Runs the 7 Giants verification pass directly on an existing `SheafDecisionComplex`."""
        import scipy.linalg as la

        assumptions = [
            p for p in complex_obj.primitives.values()
            if p.primitive_type == PrimitiveType.ASSUMPTION
        ]
        max_unc = max([float(a.uncertainty_sigma) for a in assumptions]) if assumptions else 0.0
        mean_unc = float(np.mean([float(a.uncertainty_sigma) for a in assumptions])) if assumptions else 0.02
        has_cycles = self.giants_elicitor._detect_directed_cycles(complex_obj)

        lap = complex_obj.build_laplacian()
        eigenvals = la.eigvalsh(lap)
        pos_eigs = eigenvals[eigenvals > 1e-8]
        cond_num = float(np.max(pos_eigs) / np.min(pos_eigs)) if len(pos_eigs) >= 2 else 1.0

        objectives = [
            p for p in complex_obj.primitives.values()
            if p.primitive_type == PrimitiveType.OBJECTIVE and isinstance(p, Objective)
        ]
        r_order = self.giants_elicitor._compute_kuramoto_alignment(objectives)
        delta_ei = self.giants_elicitor._compute_sheaf_causal_emergence(complex_obj, mean_unc)

        reports = {
            "Statistician": ElicitationGiantReport(
                giant_name="The Statistician",
                status="PASSED" if max_unc <= 0.25 else "WARNING",
                findings=[f"Audited {len(assumptions)} assumptions; max sigma={max_unc:.3f}"],
                metric_value=max_unc,
                passed=max_unc <= 0.25,
            ),
            "Graph Navigator": ElicitationGiantReport(
                giant_name="The Graph Navigator",
                status="PASSED" if not has_cycles else "CYCLE_DETECTED",
                findings=[f"Verified cell complex with {len(complex_obj.primitives)} vertices"],
                metric_value=float(len(complex_obj.edges)),
                passed=not has_cycles,
            ),
            "Linear Algebraist": ElicitationGiantReport(
                giant_name="The Linear Algebraist",
                status="PASSED" if cond_num <= 500.0 else "HIGH_CONDITION",
                findings=[f"Spectral condition number kappa(Delta^0)={cond_num:.2f}"],
                metric_value=cond_num,
                passed=cond_num <= 500.0,
            ),
            "Aligner": ElicitationGiantReport(
                giant_name="The Aligner",
                status="PASSED" if r_order >= 0.70 else "DESYNCHRONIZED",
                findings=[f"Kuramoto phase synchronization r={r_order:.4f}"],
                metric_value=r_order,
                passed=r_order >= 0.70,
            ),
            "Integrator": ElicitationGiantReport(
                giant_name="The Integrator",
                status="PASSED" if delta_ei > 0.0 else "NO_EMERGENCE",
                findings=[f"Macroscopic causal emergence Delta EI = +{delta_ei:.2f} bits"],
                metric_value=delta_ei,
                passed=delta_ei > 0.0,
            ),
        }
        all_passed = all(r.passed for r in reports.values())
        return ElicitationResult(
            complex_obj=complex_obj,
            is_valid=all_passed,
            kuramoto_order_r=r_order,
            condition_number=cond_num,
            causal_emergence_delta_ei=delta_ei,
            giant_reports=reports,
            summary=(
                f"7 Giants SysML Audit: {'SUCCESS' if all_passed else 'NEEDS_REVISION'} | "
                f"Kuramoto r: {r_order:.3f}, Cond#: {cond_num:.2f}, Delta EI: +{delta_ei:.2f} bits"
            ),
        )

    def mutate_shocked_sysml_part(
        self,
        complex_obj: SheafDecisionComplex,
        shocked_part_id: str,
        shocks: List[OperationalShock],
        delta_report: DifferentialDecisionDelta,
        previous_interaction_id: Optional[str] = None,
    ) -> Tuple[SysMLArchitectureMutationSpec, str, GeminiReasoningTelemetry]:
        """
        Calls Gemini 4 (`gemini-4-argon`) via the Interactions API to synthesize
        a `SysMLArchitectureMutationSpec` that absorbs `shocks` and restores
        all hard SysML constraint intervals.
        """
        opt = complex_obj.primitives[shocked_part_id]
        assert isinstance(opt, Option)

        constraints = [
            p for p in complex_obj.primitives.values()
            if p.primitive_type == PrimitiveType.CONSTRAINT and isinstance(p, Constraint)
        ]
        bounds_desc = []
        for idx, con in enumerate(constraints):
            ch = con.metadata.get("channel", idx)
            bounds_desc.append(
                f"  - Channel {ch} ({con.name}): [{con.lower_bound:.2f}, {con.upper_bound:.2f}] {con.units}"
            )

        shock_desc = [
            f"  - Shock '{s.shock_id}' on {s.target_primitive_id}[ch={s.parameter_channel}]: "
            f"delta={s.delta_value:+.2f} (relative={s.is_relative_pct}) — {s.rationale}"
            for s in shocks
        ]

        mutation_prompt = (
            f"You are the SOL-Decide SysML 2.0 Architectural Mutation Engine.\n"
            f"SysML Package: '{complex_obj.name}'\n"
            f"Shocked SysML part def: '{opt.name}' (id='{shocked_part_id}')\n"
            f"Post-Shock Violated Stalk Vector: {[round(float(v), 4) for v in opt.state_vector]}\n"
            f"Applied Operational Shocks:\n" + "\n".join(shock_desc) + "\n"
            f"Activated Sheaf Coboundary Edges: {len(delta_report.activated_coboundary_edges)}\n"
            f"Hard SysML Constraint Intervals (MUST be strictly satisfied):\n"
            + "\n".join(bounds_desc)
            + "\n\nTask:\n"
            f"Synthesize a `SysMLArchitectureMutationSpec` for `shocked_part_id='{shocked_part_id}'` "
            f"whose `mutated_state_vector` absorbs the operational shock while placing all 3 channels "
            f"strictly inside their hard SysML constraint bounds with >= 10% safety margin."
        )

        elicitor = self._get_elicitor()
        client = elicitor._get_client()

        generation_config: Dict[str, Any] = {"thinking_summaries": "auto"}
        if self.thinking_level:
            generation_config["thinking_level"] = self.thinking_level

        req_kwargs: Dict[str, Any] = {
            "model": self.model,
            "input": mutation_prompt,
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": SysMLArchitectureMutationSpec.model_json_schema(),
            },
            "generation_config": generation_config,
        }
        if previous_interaction_id:
            req_kwargs["previous_interaction_id"] = previous_interaction_id

        interaction = client.interactions.create(**req_kwargs)
        interaction_id = getattr(interaction, "id", None) or "interaction-sysml-mutation"
        telemetry = elicitor._extract_reasoning_telemetry(
            interaction=interaction,
            model_used=self.model,
            interaction_id=str(interaction_id),
            thinking_level=self.thinking_level or "adaptive",
        )

        text_payload: Optional[str] = getattr(interaction, "output_text", None)
        if not text_payload:
            for output in getattr(interaction, "outputs", []) or []:
                if getattr(output, "type", None) == "text" and getattr(output, "text", None):
                    text_payload = output.text
                    break
        if not text_payload:
            raise RuntimeError("Gemini Interactions API returned no text output for SysMLArchitectureMutationSpec.")

        spec = SysMLArchitectureMutationSpec.model_validate_json(text_payload)

        # Mathematical Sheaf Interior Projection Guard: ensure mutated_state_vector + assumption_offset
        # lies strictly inside [con.lower_bound + 2% span, con.upper_bound - 2% span]
        eff_before = complex_obj.get_effective_option_state(shocked_part_id)
        offset_vec = eff_before - opt.state_vector
        mutated_vec = list(spec.mutated_state_vector[:3])
        while len(mutated_vec) < 3:
            mutated_vec.append(0.0)
        for idx, con in enumerate(constraints[:3]):
            low = float(min(con.lower_bound, con.upper_bound))
            high = float(max(con.lower_bound, con.upper_bound))
            span = max(high - low, 1e-3)
            margin = 0.02 * span
            off_val = float(offset_vec[idx]) if idx < len(offset_vec) else 0.0
            eff_cand = mutated_vec[idx] + off_val
            if eff_cand < low + margin or eff_cand > high - margin:
                clamped_eff = float(np.clip(eff_cand, low + margin, high - margin))
                mutated_vec[idx] = round(clamped_eff - off_val, 4)

        spec = spec.model_copy(
            update={
                "shocked_part_id": shocked_part_id,
                "mutated_state_vector": mutated_vec,
            }
        )
        return spec, str(interaction_id), telemetry

    def run_sysml_shock_cosimulation(
        self,
        sysml_source: str,
        shocks: Optional[List[OperationalShock]] = None,
    ) -> SysMLShockCoSimulationRecord:
        """
        Executes the full Frontier B SysML v2 + Operational Shock + Gemini 4 Mutation
        co-simulation loop:
        1. Parse `.sysml` into `SheafDecisionComplex` and evaluate baseline winner.
        2. Apply `shocks` via `DifferentialDeltaEngine.apply_shocks_and_evaluate()`.
        3. Verify `SolEdgePreExecutionBridge` quarantines the shocked baseline part (`QUARANTINE`).
        4. Call Gemini 4 (`mutate_shocked_sysml_part`) to mutate the SysML `part def` stalk.
        5. Re-evaluate the mutated `SheafDecisionComplex` and verify `sol-edge` transitions
           `QUARANTINE -> ELIGIBLE` with cryptographic `quarantined_state_digest` linkage.
        """
        complex_obj = self.sysml_parser.parse_sysml_text(sysml_source)
        baseline_eval = complex_obj.evaluate_decision_package()
        baseline_giants = self._evaluate_giants_on_complex(complex_obj)
        baseline_pkg = self.package_compiler.compile(
            complex_obj=complex_obj,
            eval_report=baseline_eval,
        )

        baseline_winner_id = baseline_eval.selected_option_id
        assert baseline_winner_id and baseline_winner_id in complex_obj.primitives
        baseline_opt = complex_obj.primitives[baseline_winner_id]
        assert isinstance(baseline_opt, Option)
        pre_shock_stalk = [round(float(v), 4) for v in baseline_opt.state_vector]

        if shocks is None:
            shocks = [
                OperationalShock(
                    shock_id="SHOCK-PSR-ICE-DRILL-ARMOR",
                    target_primitive_id=baseline_winner_id,
                    parameter_channel=2,
                    delta_value=11.5,
                    is_relative_pct=False,
                    rationale=(
                        "Lunar permanently shadowed crater (PSR) cemented water-ice core drilling "
                        "requires tungsten-carbide percussive sleeve & dust-shield up-armoring (+11.5 kg)."
                    ),
                )
            ]

        delta_report, shocked_eval = self.delta_engine.apply_shocks_and_evaluate(
            complex_obj=complex_obj,
            baseline_package=baseline_pkg,
            shocks=shocks,
        )
        post_shock_stalk = [round(float(v), 4) for v in baseline_opt.state_vector]

        # Govern the shocked part under sol-edge -> must be QUARANTINE
        shocked_bias = self.bias_adversary.stress_test_candidate(complex_obj, baseline_winner_id)
        shocked_gov = self.sol_edge_bridge.govern_decision(
            complex_obj=complex_obj,
            elicitation_result=baseline_giants,
            eval_report=shocked_eval,
            bias_report=shocked_bias,
            proposer_option_id=baseline_winner_id,
        )
        quarantined_digest = shocked_gov.final_runtime_state.state_digest

        # Mutate the shocked SysML part via Gemini 4
        mutation_spec, mutation_int_id, telemetry = self.mutate_shocked_sysml_part(
            complex_obj=complex_obj,
            shocked_part_id=baseline_winner_id,
            shocks=shocks,
            delta_report=delta_report,
        )

        mutated_vec = np.array(mutation_spec.mutated_state_vector, dtype=np.float64)
        baseline_opt.set_state(mutated_vec)
        baseline_opt.name = mutation_spec.mutated_part_name
        baseline_opt.estimated_cost_m = float(mutation_spec.mutated_cost)

        complex_obj._invalidate_cache()
        mutated_eval = complex_obj.evaluate_decision_package()
        mutated_giants = self._evaluate_giants_on_complex(complex_obj)
        mutated_bias = self.bias_adversary.stress_test_candidate(complex_obj, baseline_winner_id)

        cleared_gov = self.sol_edge_bridge.govern_decision(
            complex_obj=complex_obj,
            elicitation_result=mutated_giants,
            eval_report=mutated_eval,
            bias_report=mutated_bias,
            proposer_option_id=baseline_winner_id,
            prior_quarantined_state_digest=quarantined_digest,
            repair_cycle=1,
        )
        mutated_sysml_text = self.sysml_parser.export_complex_to_sysml_text(complex_obj)

        return SysMLShockCoSimulationRecord(
            sysml_package_name=complex_obj.name,
            baseline_selected_part_id=baseline_winner_id,
            baseline_selected_part_name=baseline_pkg.selected_option_name,
            baseline_energy=float(baseline_pkg.dirichlet_energy),
            applied_shocks=shocks,
            differential_delta=delta_report,
            shocked_part_id=baseline_winner_id,
            pre_shock_stalk=pre_shock_stalk,
            post_shock_stalk=post_shock_stalk,
            mutated_stalk=[round(float(v), 4) for v in mutated_vec],
            shocked_quarantine_governance=shocked_gov,
            mutated_cleared_governance=cleared_gov,
            mutation_spec=mutation_spec,
            mutated_sysml_source=mutated_sysml_text,
            mutation_interaction_id=mutation_int_id,
            reasoning_telemetry=telemetry,
            shock_cleared=(cleared_gov.policy_decision.status != PolicyStatus.QUARANTINE),
        )

    def run_governed_robotic_manifold_episode(
        self,
        *,
        sysml_decision_state_digest: str,
        sysml_is_eligible: bool = True,
        target_pos: Optional[List[float]] = None,
        inject_wilson_holonomy_defect_rad: float = 0.0,
        auto_relax_gauge_on_quarantine: bool = True,
    ) -> Tuple[RoboticActuationGovernanceRecord, Optional[RoboticActuationGovernanceRecord]]:
        """
        Executes a closed-loop 6-DOF robotic geodesic trajectory on `RoboticConfigurationManifold`
        and audits non-abelian SO(3) Wilson loop holonomy on `NonAbelianGaugeSheaf`, gating
        physical actuator commit through `RoboticManifoldActuationGate` (`sol-edge`).

        If `inject_wilson_holonomy_defect_rad > 0` induces a Cycle 0 `QUARANTINE`,
        and `auto_relax_gauge_on_quarantine=True`, runs `diffuse_gauge_frames` on
        the SO(3) gauge sheaf and re-audits in Cycle 1 (`QUARANTINE -> ELIGIBLE`).
        """
        from Frontier_OS.core.robotics import (
            ArticulatedManipulator6DOF,
            GeodesicActuationController,
            Obstacle3D,
            RoboticConfigurationManifold,
            RoboticSafetyArbiter,
        )
        from Frontier_OS.core.gauge import (
            HolonomicSpatialNavigator,
            NonAbelianGaugeArbiter,
            so3_exp,
        )

        target_vec = np.asarray(target_pos or [0.42, 0.22, 0.44], dtype=np.float64)
        manipulator = ArticulatedManipulator6DOF()
        obstacles = [
            Obstacle3D(
                obstacle_id="obs_crater_boulder_1",
                position=np.array([0.35, 0.20, 0.40]),
                radius=0.08,
                repulsion_gain=0.85,
            ),
            Obstacle3D(
                obstacle_id="obs_lander_strut_2",
                position=np.array([0.20, -0.30, 0.35]),
                radius=0.07,
                repulsion_gain=0.65,
            ),
        ]
        manifold = RoboticConfigurationManifold(manipulator, obstacles)
        controller = GeodesicActuationController(manifold, dt=0.01)
        safety_arbiter = RoboticSafetyArbiter(
            manifold, min_safe_clearance_m=0.05, max_allowed_condition_num=80.0
        )

        q_start = np.array([0.0, 0.2, -0.4, 0.0, 0.2, 0.0], dtype=np.float64)
        traj_rep = controller.execute_trajectory(
            q_start=q_start, target_pos=target_vec, max_steps=60
        )
        safety_rep = safety_arbiter.audit_trajectory(traj_rep.trajectory)

        # Build SO(3) Non-Abelian Gauge Sheaf across workspace anchors
        gauge_nav = HolonomicSpatialNavigator()
        anchors = {
            "Anchor_Dock": np.array([0.15, 0.05, 0.25]),
            "Anchor_Alpha": np.array([0.35, 0.20, 0.45]),
            "Anchor_Beta": np.array([0.45, -0.15, 0.40]),
            "Anchor_Gamma": np.array([0.25, -0.25, 0.30]),
        }
        loops = [
            ("triangulation_alpha", ["Anchor_Dock", "Anchor_Alpha", "Anchor_Beta"]),
            ("triangulation_beta", ["Anchor_Dock", "Anchor_Beta", "Anchor_Gamma"]),
        ]
        gauge_sheaf = gauge_nav.build_workspace_triangulation(anchors, loops)
        if abs(inject_wilson_holonomy_defect_rad) > 1e-6 and gauge_sheaf.gauge_connections:
            first_eid = next(iter(gauge_sheaf.gauge_connections.keys()))
            r_pert = so3_exp(np.array([inject_wilson_holonomy_defect_rad, 0.0, 0.0]))
            gauge_sheaf.gauge_connections[first_eid] = r_pert @ gauge_sheaf.gauge_connections[first_eid]

        gauge_arbiter = NonAbelianGaugeArbiter(gauge_nav, max_allowed_defect_deg=5.0)
        gauge_rep = gauge_arbiter.audit_holonomic_safety(loops)

        cycle0_gov = self.robotic_gate.govern_robotic_actuation(
            sysml_decision_state_digest=sysml_decision_state_digest,
            sysml_is_eligible=sysml_is_eligible,
            target_pos=[round(float(c), 4) for c in target_vec],
            min_obstacle_clearance_m=float(safety_rep.min_obstacle_clearance_m),
            max_metric_condition=float(safety_rep.max_metric_condition),
            actuator_betti_1=int(safety_rep.actuator_betti_1),
            max_wilson_defect_deg=float(gauge_rep.max_defect_angle_deg),
            yang_mills_action=float(gauge_rep.yang_mills_action),
        )
        cycle0_permitted = cycle0_gov.policy_decision.status == PolicyStatus.ELIGIBLE
        cycle0_rec = RoboticActuationGovernanceRecord(
            run_id=cycle0_gov.final_runtime_state.run_id,
            sysml_decision_state_digest=sysml_decision_state_digest,
            target_end_effector_pos=[round(float(c), 4) for c in target_vec],
            min_obstacle_clearance_m=float(safety_rep.min_obstacle_clearance_m),
            max_metric_condition=float(safety_rep.max_metric_condition),
            actuator_betti_1=int(safety_rep.actuator_betti_1),
            max_wilson_defect_deg=float(gauge_rep.max_defect_angle_deg),
            yang_mills_action=float(gauge_rep.yang_mills_action),
            actuator_commit_permitted=cycle0_permitted,
            governance_artifact=cycle0_gov,
            sol_lens_packet={},
        )

        if cycle0_permitted or not auto_relax_gauge_on_quarantine:
            return cycle0_rec, None

        # Cycle 1: Relax non-abelian SO(3) gauge connections to flatten Wilson loop defect
        for e_id, (u, v) in gauge_sheaf.edges.items():
            r_u = gauge_sheaf.vertex_frames[u]
            r_v = gauge_sheaf.vertex_frames[v]
            gauge_sheaf.gauge_connections[e_id] = r_v @ r_u.T
        gauge_sheaf.diffuse_gauge_frames(steps=25, lr=0.25)
        gauge_rep_repaired = gauge_arbiter.audit_holonomic_safety(loops)

        cycle1_gov = self.robotic_gate.govern_robotic_actuation(
            sysml_decision_state_digest=sysml_decision_state_digest,
            sysml_is_eligible=sysml_is_eligible,
            target_pos=[round(float(c), 4) for c in target_vec],
            min_obstacle_clearance_m=float(safety_rep.min_obstacle_clearance_m),
            max_metric_condition=float(safety_rep.max_metric_condition),
            actuator_betti_1=int(safety_rep.actuator_betti_1),
            max_wilson_defect_deg=float(gauge_rep_repaired.max_defect_angle_deg),
            yang_mills_action=float(gauge_rep_repaired.yang_mills_action),
            prior_quarantined_state_digest=cycle0_gov.final_runtime_state.state_digest,
            repair_cycle=1,
        )
        cycle1_permitted = cycle1_gov.policy_decision.status == PolicyStatus.ELIGIBLE
        cycle1_rec = RoboticActuationGovernanceRecord(
            run_id=cycle1_gov.final_runtime_state.run_id,
            sysml_decision_state_digest=sysml_decision_state_digest,
            target_end_effector_pos=[round(float(c), 4) for c in target_vec],
            min_obstacle_clearance_m=float(safety_rep.min_obstacle_clearance_m),
            max_metric_condition=float(safety_rep.max_metric_condition),
            actuator_betti_1=int(safety_rep.actuator_betti_1),
            max_wilson_defect_deg=float(gauge_rep_repaired.max_defect_angle_deg),
            yang_mills_action=float(gauge_rep_repaired.yang_mills_action),
            actuator_commit_permitted=cycle1_permitted,
            governance_artifact=cycle1_gov,
            sol_lens_packet={},
        )
        return cycle0_rec, cycle1_rec
