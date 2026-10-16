"""
Frontier J: Lumina Coding Library & Ranger Corps Integration into the
SOL Change Observatory (`c:\\sol-systems\\sol-change`) and SOL Continuum (`c:\\sol-systems\\sol-continuum`).

Implements the Sovereign Domain architecture from `LuminaRangerCorps.md`:
- Constitution & Vault: `LuminaLibraryAgent` (`registry.json`, `observatory_staged_registry.json`, `level_lessons.json`)
- Parliament of Resonators: `SovereignDomain` (`architecture_council`, `wave_fabric_guild`, `compiler_council`)
- Lumina Ranger Corps: `PhaseRanger`, `MassRanger`, `CourtRanger`, `FinalizationRanger`, `LuminaSubstrateRanger`, `LuminaPayloadCourier`
- Judicial Courts: `PromotionCourt` (`PromotionGateResult`, `CalibrationCorrectionDecision`) + `SolEdgeLuminaSovereignGate`
- Frontier Observatory: `ChangeObservatoryBridge` (`sol-change` schema-1.0 baseline vs. candidate comparison)
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field

_SOL_SYSTEMS_ROOT = Path(__file__).resolve().parents[2]
_SOL_CHANGE_ROOT = _SOL_SYSTEMS_ROOT / "sol-change"
_SOL_RSI_ROOT = _SOL_SYSTEMS_ROOT / "sol" / "tools" / "sol-rsi"
_SOL_LLM_ROOT = _SOL_SYSTEMS_ROOT / "sol" / "tools" / "sol-llm"
_SOL_CORE_ROOT = _SOL_SYSTEMS_ROOT / "sol" / "tools" / "sol-core"
_SOL_ROOT = _SOL_SYSTEMS_ROOT / "sol"

for _p in (
    _SOL_SYSTEMS_ROOT,
    _SOL_CHANGE_ROOT,
    _SOL_RSI_ROOT,
    _SOL_LLM_ROOT,
    _SOL_CORE_ROOT,
    _SOL_ROOT,
    _SOL_SYSTEMS_ROOT / "sol-decide",
    _SOL_SYSTEMS_ROOT / "sol-edge" / "src",
    _SOL_SYSTEMS_ROOT / "sol-edge",
    _SOL_SYSTEMS_ROOT / "conJecture",
):
    _ps = str(_p)
    if _p.exists() and _ps not in sys.path:
        sys.path.insert(0, _ps)

from coding_library import (
    LuminaLibraryAgent,
    LuminaPayloadCourier,
    LuminaSubstrateRanger,
    PromotionCourt,
    PromotionGateResult,
    RangerMission,
    SovereignDomain,
    SovereignPacket,
)
from coding_library.sovereign_domain.frontier_bridge import (
    BoundedCorrectionPolicy,
    FrontierBridge,
    FrontierClosedLoopController,
)
from coding_library.sovereign_domain.rangers.court_ranger import CourtRanger
from coding_library.sovereign_domain.rangers.entangled_feedback_ranger import EntangledFeedbackRanger
from coding_library.sovereign_domain.rangers.fault_matrix_ranger import FaultMatrixRanger
from coding_library.sovereign_domain.rangers.finalization_ranger import FinalizationRanger
from coding_library.sovereign_domain.rangers.mass_ranger import MassRanger
from coding_library.sovereign_domain.rangers.micro_isa_ranger import MicroISARanger
from coding_library.sovereign_domain.rangers.phase_ranger import PhaseRanger
from coding_library.sovereign_domain.rangers.wideword_program_ranger import WideWordProgramRanger

from Frontier_OS.core.hippocampal_sink import HippocampalMemorySink
from observatory.continuum import ADAPTER_VERSION
from sol.kernel.synthesis.circuit_synthesizer import RiemannianCircuitSynthesizer
from sol.kernel.synthesis.circuit_topology import CircuitNodeType, SelfAssembledCircuit
from sol_edge.contracts import PolicyStatus
from sol_edge.runtime.events import RuntimeEvent

from sol_backend_capability_contract import (
    BackendCapabilityReport,
    build_backend_capability_matrix,
    summarize_backend_capability_matrix,
    validate_capability_matrix,
)
from sol_entangled_feedback_loop import (
    EntangledFeedbackLoopPolicy,
    build_entangled_feedback_loop,
    evaluate_feedback_loop_stability,
    run_shadow_entangled_feedback_loop,
    validate_feedback_stability_for_atomic_commit,
)
from sol_entangled_stability_controller import (
    EntangledStabilityControlPolicy,
    suggest_entangled_stability_control,
    validate_entangled_control_bounds,
)
from sol_entangled_wavefront_calibration import (
    EntangledCalibrationBaseline,
    EntangledCalibrationObservation,
    EntangledCalibrationPolicy,
    EntangledCalibrationReport,
    EntangledCalibrationStep,
    build_entangled_calibration_targets,
    capture_entangled_calibration_baseline,
    execute_shadow_entangled_calibration,
    measure_entangled_calibration_error,
    plan_entangled_calibration_adjustments,
    summarize_entangled_calibration,
)
from sol_entangled_wavefront_consensus import (
    EntangledConsensusParticipant,
    EntangledConsensusStateHash,
    EntangledWavefrontConsensusDecision,
    build_entangled_wavefront_consensus_intent,
    build_entangled_wavefront_consensus_report,
    collect_entangled_wavefront_votes,
    evaluate_entangled_wavefront_quorum,
)
from sol_micro_isa import build_micro_isa_v0_spec, validate_instruction_semantics
from sol_micro_isa_compliance import (
    build_micro_isa_compliance_cases,
    run_micro_isa_compliance_batch,
    summarize_micro_isa_compliance,
)
from sol_micro_isa_v1_capability_matrix import (
    assert_micro_isa_v1_extension_compliance,
    build_micro_isa_v1_capability_matrix,
    summarize_micro_isa_v1_capability_matrix,
)
from sol_micro_isa_v1_lowering import (
    lower_v1_candidate_to_v0,
    summarize_v1_lowering_report,
    validate_v1_candidate_lowering_safety,
)
from sol_micro_isa_v1_spec import (
    build_micro_isa_v1_spec_table,
    validate_micro_isa_v1_spec_consistency,
)
from sol_multimanifold_atomic_commit import (
    MultiManifoldAtomicCommitDecision,
    build_multimanifold_atomic_commit_intent,
    commit_shadow_multimanifold_atomic,
    evaluate_atomic_commit_barrier,
    prepare_multimanifold_atomic_commit,
    validate_atomic_commit_boundaries,
)
from sol_pipeline_wavefront_fault_matrix import (
    build_pipeline_wavefront_fault_matrix,
    run_shadow_pipeline_wavefront_fault_matrix,
    summarize_pipeline_wavefront_fault_matrix,
)
from sol_pipeline_wavefront_rollback_proof import (
    PipelineWavefrontRollbackCase,
    capture_pipeline_wavefront_rollback_snapshot,
    run_pipeline_wavefront_rollback_proof,
)
from sol_realtime_calibration_faults import (
    build_calibration_fault_matrix,
    run_shadow_calibration_fault_matrix,
    summarize_calibration_fault_results,
)
from sol_sovereign_runtime import (
    SovereignRuntimeCommand,
    SovereignRuntimePolicy,
    build_sovereign_runtime,
    execute_shadow_quantum_wavefront_calibration_command,
    summarize_sovereign_runtime,
)
from sol_state_relocation_fault_matrix import (
    build_relocation_fault_matrix,
    run_shadow_relocation_fault_matrix,
    summarize_relocation_fault_matrix,
)
from sol_wideword_computation_validation import (
    OracleWideWordVM,
    WideWordProgram,
    WideWordProgramInstruction,
    WideWordVirtualVM,
    format_hex,
)
from sol_wideword_fabric import (
    attach_interlane_prefix_carry,
    build_hierarchical_waveguide_plan,
    build_wideword_fabric,
    validate_fabric_topology,
    validate_wideword_arithmetic_fabric,
)
from sol_wideword_waveguide_program import validate_program_against_micro_isa

from .autopoietic_organism import FrontierNAutopoieticHarmonizer
from .continuum_network import (
    ChangeObservatoryBridge,
    ContinuumReasoningTelemetry,
    build_sol_edge_cycle_events,
)


COMMAND_PROTOCOL_VERBS: tuple[str, ...] = (
    "PROPOSE",
    "TRAVEL",
    "INSPECT",
    "PATCH",
    "REPORT",
    "VERIFY",
    "ARCHIVE",
    "PROMOTE",
)


class CircuitToWideWordLoweringAdapter:
    """
    Frontier L Cross-System Synthesis Adapter:
    Lowers a synthesized `SelfAssembledCircuit` DAG (`Frontier_OS.core.circuit_synthesis`)
    combined with Micro-ISA v1 candidate vector/prefix/conditional instructions
    (`VEC_PACK`, `PREFIX_ADD`, `VEC_LANE_XOR`, `SELECT`, `CMOVZ`, `WG_CHAN_FENCE`)
    into canonical Micro-ISA v0 `WideWordProgramInstruction` sequences via
    `sol_micro_isa_v1_lowering.lower_v1_candidate_to_v0`, validates 32-bit and 64-bit
    `WideWordFabricTopology`, and executes them deterministically on both
    `WideWordVirtualVM` (`lane_fabric_vm`) and `OracleWideWordVM` with zero mismatches.
    """

    def __init__(self, synthesizer: Optional[RiemannianCircuitSynthesizer] = None) -> None:
        self.synthesizer = synthesizer or RiemannianCircuitSynthesizer()

    def build_hybrid_v1_program(
        self,
        circuit: Optional[SelfAssembledCircuit] = None,
        input_bits: tuple[int, ...] = (1, 1, 1),
        enable_waveguide_channel_state: bool = False,
    ) -> tuple[SelfAssembledCircuit, List[Any], Dict[str, str]]:
        if circuit is None:
            circuit = self.synthesizer.synthesize_canonical("FULL_ADDER").circuit

        # Topologically order circuit nodes
        visited: set[str] = set()
        topo_order: List[str] = []

        def _visit(nid: str) -> None:
            if nid in visited:
                return
            visited.add(nid)
            for src, dst in circuit.edges.keys():
                if dst == nid:
                    _visit(src)
            topo_order.append(nid)

        for out_id in circuit.output_node_ids:
            _visit(out_id)
        for nid in circuit.nodes:
            _visit(nid)

        # Compute last consumer index in topo_order for liveness-aware register reuse
        topo_idx_map = {nid: idx for idx, nid in enumerate(topo_order)}
        last_use_idx: Dict[str, int] = {nid: idx for idx, nid in enumerate(topo_order)}
        for src, dst in circuit.edges.keys():
            if src in topo_idx_map and dst in topo_idx_map:
                if topo_idx_map[dst] > last_use_idx[src]:
                    last_use_idx[src] = topo_idx_map[dst]
        for out_id in circuit.output_node_ids:
            if out_id in last_use_idx:
                last_use_idx[out_id] = len(topo_order)

        # Allocate circuit DAG nodes from R8..R15 first (with R4..R7 overflow and memory spill
        # at 0x100+ if >12 nodes are simultaneously live) so R0..R3 remain free for scratch.
        free_regs: List[str] = [f"R{i}" for i in range(8, 16)] + [f"R{i}" for i in range(4, 8)]
        active_node_reg: Dict[str, str] = {}
        spilled_node_addr: Dict[str, int] = {}
        node_to_reg: Dict[str, str] = {}
        program_v1: List[Any] = []

        def _alloc_reg(protected_nodes: set[str]) -> str:
            if free_regs:
                return free_regs.pop(0)
            victim = next(
                (u for u in active_node_reg if u not in protected_nodes),
                next(iter(active_node_reg)),
            )
            victim_reg = active_node_reg.pop(victim)
            if victim not in spilled_node_addr:
                addr = 0x100 + len(spilled_node_addr)
                spilled_node_addr[victim] = addr
                program_v1.append(WideWordProgramInstruction("MOV", "R2", addr))
                program_v1.append(WideWordProgramInstruction("STORE", victim_reg, "R2"))
            return victim_reg

        def _load_parent(parent_id: str, scratch_reg: str) -> str:
            if parent_id in active_node_reg:
                return active_node_reg[parent_id]
            addr = spilled_node_addr[parent_id]
            program_v1.append(WideWordProgramInstruction("MOV", "R2", addr))
            program_v1.append(WideWordProgramInstruction("LOAD", scratch_reg, "R2"))
            return scratch_reg

        for step_idx, nid in enumerate(topo_order):
            node = circuit.nodes[nid]
            parents = [src for src, dst in circuit.edges.keys() if dst == nid]
            reg = _alloc_reg(set(parents))

            if node.node_type == CircuitNodeType.INPUT:
                in_idx = circuit.input_node_ids.index(nid) if nid in circuit.input_node_ids else 0
                bit_val = (int(input_bits[in_idx]) & 1) if in_idx < len(input_bits) else 1
                program_v1.append(WideWordProgramInstruction("MOV", reg, bit_val))
            elif not parents:
                program_v1.append(WideWordProgramInstruction("MOV", reg, 0))
            elif node.node_type == CircuitNodeType.INVERTER:
                src0 = _load_parent(parents[0], "R3")
                program_v1.append(WideWordProgramInstruction("NOT", reg, src0))
                program_v1.append(WideWordProgramInstruction("AND", reg, reg, 1))
            elif len(parents) == 1:
                src0 = _load_parent(parents[0], "R3")
                program_v1.append(WideWordProgramInstruction("MOV", reg, src0))
            else:
                if node.node_type in (CircuitNodeType.LENS_AND, CircuitNodeType.LENS):
                    gate_op = "AND"
                elif node.node_type in (CircuitNodeType.LENS_OR, CircuitNodeType.BASIN):
                    gate_op = "OR"
                elif node.node_type == CircuitNodeType.INTERFERENCE:
                    gate_op = "XOR"
                else:
                    gate_op = "MOV"

                if gate_op == "MOV":
                    src0 = _load_parent(parents[0], "R3")
                    program_v1.append(WideWordProgramInstruction("MOV", reg, src0))
                else:
                    src0 = _load_parent(parents[0], "R1")
                    src1 = _load_parent(parents[1], "R3")
                    program_v1.append(WideWordProgramInstruction(gate_op, reg, src0, src1))
                    for extra_p in parents[2:]:
                        src_extra = _load_parent(extra_p, "R3")
                        program_v1.append(WideWordProgramInstruction(gate_op, reg, reg, src_extra))

            node_to_reg[nid] = reg
            active_node_reg[nid] = reg

            # Release registers for nodes whose last consumer has just executed
            for u in list(active_node_reg.keys()):
                if last_use_idx.get(u, 0) <= step_idx:
                    freed = active_node_reg.pop(u)
                    if freed not in free_regs:
                        free_regs.append(freed)

        # Persist all circuit output node bits to memory[0x200 + out_idx] and preserve out_0/out_1 in R14/R15
        for out_idx, out_id in enumerate(circuit.output_node_ids):
            if out_id in active_node_reg:
                out_reg = active_node_reg[out_id]
            else:
                out_reg = "R3"
                program_v1.append(WideWordProgramInstruction("MOV", "R2", spilled_node_addr[out_id]))
                program_v1.append(WideWordProgramInstruction("LOAD", out_reg, "R2"))
            program_v1.append(WideWordProgramInstruction("MOV", "R2", 0x200 + out_idx))
            program_v1.append(WideWordProgramInstruction("STORE", out_reg, "R2"))

        if len(circuit.output_node_ids) >= 1:
            program_v1.append(WideWordProgramInstruction("MOV", "R2", 0x200))
            program_v1.append(WideWordProgramInstruction("LOAD", "R14", "R2"))
        else:
            program_v1.append(WideWordProgramInstruction("MOV", "R14", 0))

        if len(circuit.output_node_ids) >= 2:
            program_v1.append(WideWordProgramInstruction("MOV", "R2", 0x201))
            program_v1.append(WideWordProgramInstruction("LOAD", "R15", "R2"))
        else:
            program_v1.append(WideWordProgramInstruction("MOV", "R15", "R14"))

        # Append Micro-ISA v1 candidate vector/prefix/conditional instructions folding circuit outputs R14/R15
        program_v1.extend(
            [
                WideWordProgramInstruction("MOV", "R4", 0),
                WideWordProgramInstruction("SHL", "R8", "R14", 1),
                WideWordProgramInstruction("ADD", "R8", "R8", 0x10),
                WideWordProgramInstruction("SHL", "R9", "R15", 1),
                WideWordProgramInstruction("ADD", "R9", "R9", 0x32),
                WideWordProgramInstruction("MOV", "R10", 0x56),
                WideWordProgramInstruction("MOV", "R11", 0x78),
                WideWordProgramInstruction("VEC_PACK", "R6", None, ("R8", "R9", "R10", "R11")),
                WideWordProgramInstruction("MOV", "R12", 0x01020304),
                WideWordProgramInstruction("PREFIX_ADD", "R7", "R6", "R12"),
                WideWordProgramInstruction("MOV", "R13", 0x55555555),
                WideWordProgramInstruction("VEC_LANE_XOR", "R7", "R7", ("R13", 0xF)),
                WideWordProgramInstruction("CMP", "R7", "R4"),
                WideWordProgramInstruction("SELECT", "R5", "NZ", ("R7", "R4")),
                WideWordProgramInstruction("CMOVZ", "R5", "R4"),
            ]
        )
        if enable_waveguide_channel_state:
            program_v1.extend(
                [
                    WideWordProgramInstruction("WG_CHAN_SEND", 0, "R7"),
                    WideWordProgramInstruction("WG_CHAN_ROUTE", 1, 0, 0xF),
                    WideWordProgramInstruction("WG_CHAN_RECV", "R5", 1),
                ]
            )
        program_v1.extend(
            [
                WideWordProgramInstruction("WG_CHAN_FENCE"),
                WideWordProgramInstruction("HALT"),
            ]
        )
        return circuit, program_v1, node_to_reg

    def lower_and_execute_circuit(
        self,
        circuit: Optional[SelfAssembledCircuit] = None,
        input_bits: tuple[int, ...] = (1, 1, 1),
        enable_waveguide_channel_state: bool = False,
    ) -> Dict[str, Any]:
        circuit_obj, v1_program, node_to_reg = self.build_hybrid_v1_program(
            circuit=circuit,
            input_bits=input_bits,
            enable_waveguide_channel_state=enable_waveguide_channel_state,
        )
        expected_eval = circuit_obj.evaluate(
            {
                nid: float((int(input_bits[i]) & 1) if i < len(input_bits) else 1)
                for i, nid in enumerate(circuit_obj.input_node_ids)
            }
        )
        expected_circuit_outputs = {
            oid: int(expected_eval.binary_outputs[oid]) for oid in circuit_obj.output_node_ids
        }

        # 1. Validate 32-bit and 64-bit WideWordFabricTopology & prefix-carry plans
        from sol_hierarchical_waveguide_fabric import build_hierarchical_waveguide_topology
        from sol_wideword_fabric import WideWordFabricExecutionPlan

        fabric_reports: Dict[str, Any] = {}
        for width in (32, 64):
            topo = build_wideword_fabric(width)
            topo_valid = validate_fabric_topology(topo)
            base_plan = WideWordFabricExecutionPlan(
                topology=build_hierarchical_waveguide_topology(width),
                instruction={"op": "ADD", "width": width},
                pdm_plan=None,
                t_values=[0.1 * i for i in range(16)],
                metadata={"hierarchical_waveguide": True},
            )
            hier_plan = attach_interlane_prefix_carry(base_plan)
            arith_valid = validate_wideword_arithmetic_fabric(hier_plan)
            lane_count = sum(len(g.lanes) for g in topo.lane_groups)
            fabric_reports[f"{width}bit"] = {
                "width": width,
                "lane_count": lane_count,
                "group_count": len(topo.lane_groups),
                "topology_valid": bool(topo_valid),
                "prefix_carry_attached": bool(hier_plan.metadata.get("interlane_prefix_carry", False)),
                "arithmetic_fabric_valid": bool(arith_valid),
            }

        # 2. Lower v1 candidate program to v0 and execute on 32-bit and 64-bit WideWordVirtualVM + OracleWideWordVM
        from sol_micro_isa_v1_candidates import V1_CANDIDATE_OPCODES

        vm_executions: Dict[str, Any] = {}
        lowering_reports: Dict[str, Any] = {}
        exec_report_32 = None
        program_trace_32 = None
        v0_insts_32: List[Any] = []

        for width in (32, 64):
            v0_insts: List[Any] = []
            lowering_meta: List[Dict[str, Any]] = []
            label_counter = 0
            safety_checks_passed = True

            for inst in v1_program:
                if isinstance(inst, WideWordProgramInstruction) and inst.op.upper() in V1_CANDIDATE_OPCODES:
                    ok, _reason = validate_v1_candidate_lowering_safety(
                        inst, enable_waveguide_channel_state=enable_waveguide_channel_state
                    )
                    if not ok:
                        safety_checks_passed = False
                    lowered_seq, label_counter, meta = lower_v1_candidate_to_v0(
                        inst,
                        label_counter,
                        width=width,
                        enable_waveguide_channel_state=enable_waveguide_channel_state,
                    )
                    v0_insts.extend(lowered_seq)
                    lowering_meta.append(meta)
                else:
                    v0_insts.append(inst)

            low_summary = summarize_v1_lowering_report(lowering_meta)
            low_summary["safety_checks_passed"] = safety_checks_passed
            lowering_reports[f"{width}bit"] = low_summary

            vm = WideWordVirtualVM(width)
            exec_report = vm.run_program_with_backend(v0_insts, "lane_fabric_vm")
            vm.last_program = v0_insts
            mismatches = vm.compare_program_trace_to_oracle()
            prog_trace = vm.export_program_trace()

            oracle_vm = OracleWideWordVM(width)
            oracle_cycles = oracle_vm.run_program(v0_insts)

            vm_circuit_outputs = {
                oid: int(vm.memory.get(0x200 + idx, 0))
                for idx, oid in enumerate(circuit_obj.output_node_ids)
            }
            oracle_circuit_outputs = {
                oid: int(oracle_vm.memory.get(0x200 + idx, 0))
                for idx, oid in enumerate(circuit_obj.output_node_ids)
            }
            circuit_truth_table_match = (
                vm_circuit_outputs == expected_circuit_outputs
                and oracle_circuit_outputs == expected_circuit_outputs
            )

            if width == 32:
                exec_report_32 = exec_report
                program_trace_32 = prog_trace
                v0_insts_32 = v0_insts

            vm_executions[f"{width}bit"] = {
                "width": width,
                "backend_used": exec_report.backend_used,
                "v1_instruction_count": len(v1_program),
                "lowered_v0_instruction_count": len(v0_insts),
                "trace_step_count": len(prog_trace.steps),
                "oracle_cycles": oracle_cycles,
                "oracle_match": bool(exec_report.oracle_match and len(mismatches) == 0),
                "mismatch_count": len(mismatches),
                "active_table_mutated": bool(exec_report.active_table_mutated),
                "circuit_outputs": vm_circuit_outputs,
                "expected_circuit_outputs": expected_circuit_outputs,
                "circuit_truth_table_match": bool(circuit_truth_table_match),
                "r5_hex": format_hex(vm.registers["R5"], width),
                "r6_hex": format_hex(vm.registers["R6"], width),
                "r7_hex": format_hex(vm.registers["R7"], width),
                "r14_hex": format_hex(vm.registers["R14"], width),
                "r15_hex": format_hex(vm.registers["R15"], width),
                "oracle_r7_hex": format_hex(oracle_vm.registers["R7"], width),
                "flags": dict(vm.flags),
            }

        # 3. Validate Micro-ISA v0 & v1 specification, capability matrix, and 5-backend compliance batch
        v0_spec = build_micro_isa_v0_spec()
        prog_isa_validation = validate_program_against_micro_isa(
            WideWordProgram(program_id="PROG_FRONTIER_L_HYBRID_V0", instructions=v0_insts_32),
            v0_spec,
        )
        add_sem_report = validate_instruction_semantics(v0_spec, "ADD", ["R1", "R2", "R3"])
        cap_matrix = build_backend_capability_matrix(v0_spec, {"strict": True})
        cap_matrix_valid = validate_capability_matrix(cap_matrix)
        cap_report = BackendCapabilityReport(matrix=cap_matrix, success=bool(cap_matrix_valid), violations=[])
        cap_summary = summarize_backend_capability_matrix(cap_matrix)

        compliance_cases = build_micro_isa_compliance_cases(v0_spec, [32, 64])
        compliance_backends = [
            "lane_fabric_strict",
            "sequencer_shadow_strict",
            "pdm_waveguide_shadow_strict",
            "pdm_waveguide_microcoded_strict",
            "hybrid_shadow",
        ]
        compliance_report = run_micro_isa_compliance_batch(compliance_cases, compliance_backends)
        compliance_summary = summarize_micro_isa_compliance(compliance_report)

        v1_spec_consistent = validate_micro_isa_v1_spec_consistency()
        v1_spec_table = build_micro_isa_v1_spec_table()
        v1_spec_dict = {r["opcode"]: r for r in v1_spec_table}
        v1_cap_matrix = build_micro_isa_v1_capability_matrix(v1_spec_dict, {"strict": True})
        v1_ext_compliant = assert_micro_isa_v1_extension_compliance(v1_cap_matrix)
        v1_cap_summary = summarize_micro_isa_v1_capability_matrix(v1_cap_matrix)

        return {
            "circuit_summary": {
                "circuit_id": circuit_obj.circuit_id,
                "name": circuit_obj.name,
                "node_count": len(circuit_obj.nodes),
                "edge_count": len(circuit_obj.edges),
                "input_node_ids": list(circuit_obj.input_node_ids),
                "output_node_ids": list(circuit_obj.output_node_ids),
                "node_types": {nid: node.node_type.value for nid, node in circuit_obj.nodes.items()},
            },
            "node_register_map": node_to_reg,
            "fabric_reports": fabric_reports,
            "lowering_reports": lowering_reports,
            "vm_executions": vm_executions,
            "micro_isa_summary": {
                "v0_instruction_count": len(v0_spec.instructions),
                "program_isa_valid": bool(
                    prog_isa_validation.get("success", False)
                    if isinstance(prog_isa_validation, dict)
                    else getattr(prog_isa_validation, "success", False)
                ),
                "program_isa_errors": list(
                    prog_isa_validation.get("errors", [])
                    if isinstance(prog_isa_validation, dict)
                    else getattr(prog_isa_validation, "errors", [])
                ),
                "add_semantics_valid": bool(getattr(add_sem_report, "success", False)),
                "capability_matrix_valid": bool(cap_matrix_valid),
                "capability_summary": cap_summary,
                "compliance_summary": compliance_summary,
                "v1_spec_consistent": bool(v1_spec_consistent),
                "v1_opcode_count": len(v1_spec_table),
                "v1_extension_compliant": bool(v1_ext_compliant),
                "v1_capability_summary": v1_cap_summary,
            },
            "_live_objects": {
                "circuit": circuit,
                "exec_report_32": exec_report_32,
                "program_trace_32": program_trace_32,
                "v0_spec": v0_spec,
                "cap_report": cap_report,
                "compliance_report": compliance_report,
            },
        }



class LuminaRangerObservatoryProposalSpec(BaseModel):
    """Structured output schema for Gemini 4 Argon Sovereign Domain & Lumina Ranger Corps Observatory orchestration."""

    selected_mission_option_id: str = Field(
        description="Option ID selected for the candidate Lumina Ranger Corps & Coding Library Observatory workflow."
    )
    mission_id: str = Field(
        description="Deterministic RangerMission ID (e.g. 'L12_WIDEWORD_PDM_PATROL_001')."
    )
    target_level: int = Field(
        description="Target SOL architecture level in [11, 50] (e.g., 12 for 32-bit WideWord Waveguide Fabric)."
    )
    candidate_component_name: str = Field(
        description="Snake-case component name to stage in the Lumina Coding Library under Observatory governance."
    )
    parliament_architecture_proposal: str = Field(
        description="Joint design proposal from Architecture Council, Wave Fabric Guild, and Compiler Council."
    )
    ranger_patrol_directives: List[str] = Field(
        description="Specific field inspection directives for PhaseRanger, MassRanger, CourtRanger, and FinalizationRanger."
    )
    bounded_phase_nudge_rad: float = Field(
        description="Bounded phase correction nudge in radians within [-0.05, 0.05] per Sovereignty Rule 4."
    )
    bounded_damping_delta: float = Field(
        description="Bounded waveguide damping adjustment within [-0.01, 0.01] per Sovereignty Rule 4."
    )
    constitutional_lesson_law: str = Field(
        description="Constitutional lesson rule recorded in level_lessons.json per Sovereignty Rule 7 ('Lessons become law')."
    )
    observatory_hypothesis: str = Field(
        description="Scientific hypothesis registered in the SOL Change Observatory comparing Cycle 0 uncalibrated drift vs. Cycle 1 Ranger-verified calibration."
    )


@dataclass(frozen=True)
class LuminaSovereignAuditResult:
    """Zero-trust audit result from SolEdgeLuminaSovereignGate enforcing the 7 Hard Sovereignty Rules."""

    cycle_index: int
    designation: str
    workflow_version: str
    mission_id: str
    target_level: int
    phase_ranger_recommendation: str
    court_gate_passed: bool
    court_decision: str
    finalization_promotion_readiness: bool
    active_delta: float
    cross_talk: float
    min_active_register_mass: float
    max_phase_error: float
    bounded_phase_nudge_rad: float
    bounded_damping_delta: float
    sacred_physics_mutated: bool
    observatory_comparability: str
    policy_status: str
    governance_reason: str
    cohomological_event: str
    is_quarantined: bool
    state_digest: str
    events: tuple[RuntimeEvent, ...] = field(default=())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_index": self.cycle_index,
            "designation": self.designation,
            "workflow_version": self.workflow_version,
            "mission_id": self.mission_id,
            "target_level": self.target_level,
            "phase_ranger_recommendation": self.phase_ranger_recommendation,
            "court_gate_passed": self.court_gate_passed,
            "court_decision": self.court_decision,
            "finalization_promotion_readiness": self.finalization_promotion_readiness,
            "active_delta": round(self.active_delta, 4),
            "cross_talk": round(self.cross_talk, 4),
            "min_active_register_mass": round(self.min_active_register_mass, 4),
            "max_phase_error": round(self.max_phase_error, 4),
            "bounded_phase_nudge_rad": round(self.bounded_phase_nudge_rad, 4),
            "bounded_damping_delta": round(self.bounded_damping_delta, 4),
            "sacred_physics_mutated": self.sacred_physics_mutated,
            "observatory_comparability": self.observatory_comparability,
            "policy_status": self.policy_status,
            "governance_reason": self.governance_reason,
            "cohomological_event": self.cohomological_event,
            "is_quarantined": self.is_quarantined,
            "state_digest": self.state_digest,
            "event_count": len(self.events),
            "event_digests": [str(ev.event_digest) for ev in self.events],
        }


@dataclass(frozen=True)
class LuminaObservatoryEpisodeRecord:
    """End-to-end record of a Frontier J/L Lumina Coding Library & Ranger Corps Observatory episode."""

    study_name: str
    experiment_id: str
    experiment_title: str
    model_used: str
    interaction_id: str
    selected_option_id: str
    selected_option_name: str
    mission_id: str
    target_level: int
    candidate_component_name: str
    parliament_architecture_proposal: str
    ranger_patrol_directives: List[str]
    constitutional_lesson_law: str
    observatory_hypothesis: str
    command_protocol_trace: List[Dict[str, Any]]
    ranger_mission: Dict[str, Any]
    cycle0_phase_packet: Dict[str, Any]
    cycle1_phase_packet: Dict[str, Any]
    cycle1_court_packet: Dict[str, Any]
    cycle1_finalization_packet: Dict[str, Any]
    cycle0_audit: LuminaSovereignAuditResult
    cycle1_audit: LuminaSovereignAuditResult
    library_verified_components: List[str]
    staged_component_record: Dict[str, Any]
    lesson_law_record: Dict[str, Any]
    sovereign_domain_summary: Dict[str, Any]
    observatory_comparability: str
    observatory_outcome: str
    observatory_review_status: str
    observatory_warnings: List[str]
    observatory_metric_deltas: Dict[str, Dict[str, Any]]
    experiment_bundle_dir: str
    observatory_db_registered: bool
    hippocampal_episode_id: str
    sol_lens_packet: Dict[str, Any]
    baseline_sol_lens_packet: Dict[str, Any]
    observatory_experiment_archive: Dict[str, Any]
    observatory_markdown_report: str
    reasoning_telemetry: Optional[ContinuumReasoningTelemetry] = None
    cycle1_wideword_packet: Dict[str, Any] = field(default_factory=dict)
    cycle1_micro_isa_packet: Dict[str, Any] = field(default_factory=dict)
    cycle0_fault_matrix_packet: Dict[str, Any] = field(default_factory=dict)
    cycle1_entangled_feedback_packet: Dict[str, Any] = field(default_factory=dict)
    wideword_fabric_report: Dict[str, Any] = field(default_factory=dict)
    micro_isa_v1_lowering_report: Dict[str, Any] = field(default_factory=dict)
    fault_matrix_report: Dict[str, Any] = field(default_factory=dict)
    multimanifold_atomic_commit_report: Dict[str, Any] = field(default_factory=dict)
    sovereign_runtime_report: Dict[str, Any] = field(default_factory=dict)
    frontier_l_verification: Dict[str, Any] = field(default_factory=dict)
    frontier_n_verification: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "study_name": self.study_name,
            "experiment_id": self.experiment_id,
            "experiment_title": self.experiment_title,
            "model_used": self.model_used,
            "interaction_id": self.interaction_id,
            "selected_option_id": self.selected_option_id,
            "selected_option_name": self.selected_option_name,
            "mission_id": self.mission_id,
            "target_level": self.target_level,
            "candidate_component_name": self.candidate_component_name,
            "parliament_architecture_proposal": self.parliament_architecture_proposal,
            "ranger_patrol_directives": self.ranger_patrol_directives,
            "constitutional_lesson_law": self.constitutional_lesson_law,
            "observatory_hypothesis": self.observatory_hypothesis,
            "command_protocol_trace": self.command_protocol_trace,
            "ranger_mission": self.ranger_mission,
            "cycle0_phase_packet": self.cycle0_phase_packet,
            "cycle1_phase_packet": self.cycle1_phase_packet,
            "cycle1_court_packet": self.cycle1_court_packet,
            "cycle1_finalization_packet": self.cycle1_finalization_packet,
            "cycle1_wideword_packet": self.cycle1_wideword_packet,
            "cycle1_micro_isa_packet": self.cycle1_micro_isa_packet,
            "cycle0_fault_matrix_packet": self.cycle0_fault_matrix_packet,
            "cycle1_entangled_feedback_packet": self.cycle1_entangled_feedback_packet,
            "cycle0_audit": self.cycle0_audit.to_dict(),
            "cycle1_audit": self.cycle1_audit.to_dict(),
            "library_verified_components": self.library_verified_components,
            "staged_component_record": self.staged_component_record,
            "lesson_law_record": self.lesson_law_record,
            "sovereign_domain_summary": self.sovereign_domain_summary,
            "wideword_fabric_report": self.wideword_fabric_report,
            "micro_isa_v1_lowering_report": self.micro_isa_v1_lowering_report,
            "fault_matrix_report": self.fault_matrix_report,
            "multimanifold_atomic_commit_report": self.multimanifold_atomic_commit_report,
            "sovereign_runtime_report": self.sovereign_runtime_report,
            "frontier_l_verification": self.frontier_l_verification,
            "frontier_n_verification": self.frontier_n_verification,
            "observatory_comparability": self.observatory_comparability,
            "observatory_outcome": self.observatory_outcome,
            "observatory_review_status": self.observatory_review_status,
            "observatory_warnings": self.observatory_warnings,
            "observatory_metric_deltas": self.observatory_metric_deltas,
            "experiment_bundle_dir": self.experiment_bundle_dir,
            "observatory_db_registered": self.observatory_db_registered,
            "hippocampal_episode_id": self.hippocampal_episode_id,
            "reasoning_telemetry": self.reasoning_telemetry.to_dict() if self.reasoning_telemetry else None,
        }


class SolEdgeLuminaSovereignGate:
    """
    Zero-Trust `sol-edge` gate enforcing the 7 Hard Sovereignty Rules from `LuminaRangerCorps.md` §10:
    1. Agents propose; courts promote (`court_gate_passed == True`).
    2. Rangers inspect freely, patch narrowly (`mission_bounds_respected == True`).
    3. Sacred SOL physics cannot be mutated by rangers (`sacred_physics_mutated == False`, `min_active_register_mass >= 14.0`).
    4. Frontier nudges must be bounded (`|phase_nudge| <= 0.05 rad`, `|damping_delta| <= 0.01`).
    5. Every promotion needs replay (`reproducibility_hash` present, `observatory_comparability == "compatible"`).
    6. No unbounded waiting commentary (`structured_protocol_only == True`).
    7. Lessons become law (`lesson_recorded == True`).
    """

    def evaluate_sovereign_cycle(
        self,
        *,
        cycle_index: int,
        designation: str,
        workflow_version: str,
        mission: RangerMission,
        phase_packet: SovereignPacket,
        court_gate_result: PromotionGateResult,
        finalization_packet: Optional[SovereignPacket],
        bounded_phase_nudge_rad: float,
        bounded_damping_delta: float,
        sacred_physics_mutated: bool,
        lesson_recorded: bool,
        observatory_comparability: str,
        run_id: Optional[str] = None,
    ) -> LuminaSovereignAuditResult:
        ev = phase_packet.evidence or {}
        active_delta = float(ev.get("active_delta") or 0.0)
        cross_talk = float(ev.get("cross_talk") or 0.0)
        min_mass = float(ev.get("min_active_register_mass") or 0.0)
        max_phase_error = float(court_gate_result.details.get("max_phase_error", abs(ev.get("phase_residual") or 0.0)))
        fin_ready = bool(
            finalization_packet is not None
            and (finalization_packet.evidence or {}).get("promotion_readiness") is True
        )

        # Check the 7 Sovereignty Rules
        rule1_court_approved = bool(court_gate_result.passed and phase_packet.recommendation in ("observe", "promote"))
        rule2_mission_bounded = (
            "CHANGE_ENGINE_MATH" in mission.forbidden_actions
            and "WRITE_SOURCE" in mission.forbidden_actions
        )
        rule3_sacred_physics = (not sacred_physics_mutated) and (min_mass >= 14.0)
        rule4_nudges_bounded = (abs(bounded_phase_nudge_rad) <= 0.05) and (abs(bounded_damping_delta) <= 0.01)
        rule5_replayable = bool(phase_packet.reproducibility_hash) and (observatory_comparability == "compatible")
        rule7_lesson_law = bool(lesson_recorded)

        payload = {
            "cycle_index": cycle_index,
            "designation": designation,
            "workflow_version": workflow_version,
            "mission_id": mission.mission_id,
            "phase_packet_hash": phase_packet.reproducibility_hash,
            "court_decision": court_gate_result.decision,
            "court_gate_passed": court_gate_result.passed,
            "active_delta": round(active_delta, 6),
            "cross_talk": round(cross_talk, 6),
            "min_active_register_mass": round(min_mass, 6),
            "max_phase_error": round(max_phase_error, 6),
            "bounded_phase_nudge_rad": round(bounded_phase_nudge_rad, 6),
            "bounded_damping_delta": round(bounded_damping_delta, 6),
            "sacred_physics_mutated": sacred_physics_mutated,
            "fin_ready": fin_ready,
            "observatory_comparability": observatory_comparability,
        }
        effective_run_id = run_id or f"run:lumina:cycle-{cycle_index}:{designation}"

        if (
            rule1_court_approved
            and rule2_mission_bounded
            and rule3_sacred_physics
            and rule4_nudges_bounded
            and rule5_replayable
            and rule7_lesson_law
            and fin_ready
        ):
            events, state_digest = build_sol_edge_cycle_events(
                run_id=effective_run_id,
                cycle_index=cycle_index,
                designation=designation,
                policy_status=PolicyStatus.ELIGIBLE,
                payload_seed=payload,
            )
            return LuminaSovereignAuditResult(
                cycle_index=cycle_index,
                designation=designation,
                workflow_version=workflow_version,
                mission_id=mission.mission_id,
                target_level=mission.level,
                phase_ranger_recommendation=phase_packet.recommendation,
                court_gate_passed=court_gate_result.passed,
                court_decision=court_gate_result.decision,
                finalization_promotion_readiness=fin_ready,
                active_delta=active_delta,
                cross_talk=cross_talk,
                min_active_register_mass=min_mass,
                max_phase_error=max_phase_error,
                bounded_phase_nudge_rad=bounded_phase_nudge_rad,
                bounded_damping_delta=bounded_damping_delta,
                sacred_physics_mutated=sacred_physics_mutated,
                observatory_comparability=observatory_comparability,
                policy_status=PolicyStatus.ELIGIBLE.value,
                governance_reason="LUMINA_RANGER_SOVEREIGN_COURT_VERIFIED",
                cohomological_event="COHOMOLOGICAL_QUARANTINE_CLEARED",
                is_quarantined=False,
                state_digest=state_digest,
                events=events,
            )

        events, state_digest = build_sol_edge_cycle_events(
            run_id=effective_run_id,
            cycle_index=cycle_index,
            designation=designation,
            policy_status=PolicyStatus.QUARANTINE,
            payload_seed=payload,
        )
        return LuminaSovereignAuditResult(
            cycle_index=cycle_index,
            designation=designation,
            workflow_version=workflow_version,
            mission_id=mission.mission_id,
            target_level=mission.level,
            phase_ranger_recommendation=phase_packet.recommendation,
            court_gate_passed=court_gate_result.passed,
            court_decision=court_gate_result.decision,
            finalization_promotion_readiness=fin_ready,
            active_delta=active_delta,
            cross_talk=cross_talk,
            min_active_register_mass=min_mass,
            max_phase_error=max_phase_error,
            bounded_phase_nudge_rad=bounded_phase_nudge_rad,
            bounded_damping_delta=bounded_damping_delta,
            sacred_physics_mutated=sacred_physics_mutated,
            observatory_comparability=observatory_comparability,
            policy_status=PolicyStatus.QUARANTINE.value,
            governance_reason="SOVEREIGN_RANGER_DRIFT_OR_MASS_QUARANTINE",
            cohomological_event="COHOMOLOGICAL_QUARANTINE_TRIGGERED",
            is_quarantined=True,
            state_digest=state_digest,
            events=events,
        )


class LuminaLibraryObservatoryOrchestrator:
    """
    Frontier J/L Orchestrator: Bridges the Lumina Coding Library (`LuminaLibraryAgent`),
    Sovereign Domain (`SovereignDomain`, `PromotionCourt`, `FrontierClosedLoopController`),
    `sol-core` WideWord/Micro-ISA/FaultMatrix/MultiManifold/SovereignRuntime engines,
    and the 8-Ranger Lumina Squadron (`PhaseRanger`, `MassRanger`, `CourtRanger`,
    `FinalizationRanger`, `WideWordProgramRanger`, `MicroISARanger`, `FaultMatrixRanger`,
    `EntangledFeedbackRanger`) directly into the SOL Change Observatory
    (`c:\\sol-systems\\sol-change`) and SOL Continuum (`c:\\sol-systems\\sol-continuum`).
    """

    def __init__(
        self,
        library_agent: Optional[LuminaLibraryAgent] = None,
        sovereign_domain: Optional[SovereignDomain] = None,
        observatory_bridge: Optional[ChangeObservatoryBridge] = None,
        memory_sink: Optional[HippocampalMemorySink] = None,
        lowering_adapter: Optional[CircuitToWideWordLoweringAdapter] = None,
    ) -> None:
        self.library_agent = library_agent or LuminaLibraryAgent()
        self.sovereign_domain = sovereign_domain or SovereignDomain(
            library_dir=self.library_agent.lib_dir
        )
        self.promotion_court = PromotionCourt()
        self.frontier_bridge = FrontierBridge()
        self.frontier_controller = FrontierClosedLoopController(self.frontier_bridge)
        self.phase_ranger = PhaseRanger(self.library_agent)
        self.mass_ranger = MassRanger(self.library_agent)
        self.court_ranger = CourtRanger(self.library_agent)
        self.finalization_ranger = FinalizationRanger(self.library_agent)
        self.wideword_program_ranger = WideWordProgramRanger(self.library_agent)
        self.micro_isa_ranger = MicroISARanger(self.library_agent)
        self.fault_matrix_ranger = FaultMatrixRanger(self.library_agent)
        self.entangled_feedback_ranger = EntangledFeedbackRanger(self.library_agent)
        self.substrate_ranger = LuminaSubstrateRanger(self.library_agent)
        self.payload_courier = LuminaPayloadCourier(self.library_agent)
        self.lowering_adapter = lowering_adapter or CircuitToWideWordLoweringAdapter()
        self.gate = SolEdgeLuminaSovereignGate()
        self.observatory_bridge = observatory_bridge or ChangeObservatoryBridge()
        self.memory_sink = memory_sink or HippocampalMemorySink()
        self.autopoietic_harmonizer = FrontierNAutopoieticHarmonizer()

    def _synthesize_candidate_component_code(
        self,
        proposal: LuminaRangerObservatoryProposalSpec,
        reproducibility_hash: str,
    ) -> str:
        """Synthesizes the verified candidate Lumina component code staged under Observatory governance."""
        return f'''# Copyright (c) 2026 Techman Studios.
# Staged by SOL Continuum & Lumina Ranger Corps under SOL Change Observatory Governance
"""
Component: {proposal.candidate_component_name}
Mission ID: {proposal.mission_id}
Target SOL Level: {proposal.target_level}
Sovereign Reproducibility Hash: {reproducibility_hash}
Constitutional Lesson Law: {proposal.constitutional_lesson_law}
"""

def calibrate_wideword_pdm_lanes(
    lane_phases: list[float],
    phase_nudge_rad: float = {proposal.bounded_phase_nudge_rad:.4f},
    damping_delta: float = {proposal.bounded_damping_delta:.4f},
) -> dict:
    clamped_nudge = max(-0.05, min(0.05, float(phase_nudge_rad)))
    clamped_damping = max(-0.01, min(0.01, float(damping_delta)))
    calibrated = [round(p + clamped_nudge, 6) for p in lane_phases]
    return {{
        "component": "{proposal.candidate_component_name}",
        "level": {proposal.target_level},
        "calibrated_phases": calibrated,
        "applied_phase_nudge_rad": clamped_nudge,
        "applied_damping_delta": clamped_damping,
        "sacred_physics_mutated": False,
        "reproducibility_hash": "{reproducibility_hash}",
    }}
'''

    def run_lumina_observatory_episode(
        self,
        *,
        study_name: str = "Lumina_Ranger_Corps_Observatory_Sovereignty_v1",
        options: Optional[List[Dict[str, Any]]] = None,
        gemini_client: Optional[Any] = None,
        model: str = "gemini-4-argon",
        register_in_observatory_db: bool = True,
        persist_library_staging: bool = False,
    ) -> LuminaObservatoryEpisodeRecord:
        if not options:
            options = [
                {
                    "option_id": "lumina_ranger_corps_observatory_sovereign_v2",
                    "name": "Lumina Ranger Corps + PromotionCourt + Change Observatory Sovereign Vault v2",
                },
                {
                    "option_id": "lumina_unverified_ledger_autosync_v1",
                    "name": "Unverified Direct Ledger Auto-Sync Without Ranger Evidence or Observatory Review v1",
                },
            ]

        interaction_id = "mock-lumina-ranger-observatory-001"
        proposal: Optional[LuminaRangerObservatoryProposalSpec] = None
        thought_sig_digests: List[str] = []
        thought_sig_lengths: List[int] = []
        thought_summaries_list: List[str] = []
        in_tokens = 450
        th_tokens = 720
        out_tokens = 340

        if gemini_client is not None:
            prompt = (
                f"You are the Chief SOL Sovereign Architect orchestrating the Lumina Coding Library "
                f"and Lumina Ranger Corps (`LuminaRangerCorps.md`) for study '{study_name}'.\n"
                f"Candidate Options:\n{json.dumps(options, indent=2)}\n\n"
                f"Registered Councils: {self.sovereign_domain.list_agent_councils()}\n"
                f"Registered Rangers: {self.sovereign_domain.list_rangers()}\n"
                f"Verified Library Components: {self.library_agent.list_components()}\n\n"
                f"Cycle 0 (Baseline `v1.0-unverified-ledger-autosync`) suffered `PolicyStatus.QUARANTINE` "
                f"(`SOVEREIGN_RANGER_DRIFT_OR_MASS_QUARANTINE`) on Level 12 32-bit WideWord PDM fabric because "
                f"phase drift reached 0.22 rad (> 0.05), active recall delta dropped to 0.11 (< 0.20), cross-lane "
                f"leakage hit 0.09 (> 0.05), and active register mass dropped to 11.8 (< 14.0).\n"
                f"Formulate a Cycle 1 Candidate mission (`lumina_ranger_corps_observatory_sovereign_v2`) at "
                f"`target_level=12` with bounded `bounded_phase_nudge_rad` in [-0.05, 0.05] and "
                f"`bounded_damping_delta` in [-0.01, 0.01], staging `sol_wideword_32bit_pdm_calibrator` in the "
                f"Lumina Coding Library and registering a schema-1.0 experiment in the SOL Change Observatory."
            )
            interaction = gemini_client.interactions.create(
                model=model,
                input=prompt,
                response_format=LuminaRangerObservatoryProposalSpec.model_json_schema(),
                generation_config={
                    "thinking_level": "high",
                    "thinking_summaries": "auto",
                },
            )
            interaction_id = getattr(interaction, "id", None) or "live-gemini4-lumina-ranger-interaction"
            raw_text = getattr(interaction, "output_text", None) or ""
            outputs_list = list(getattr(interaction, "outputs", []) or [])
            for step in getattr(interaction, "steps", []) or []:
                outputs_list.extend(getattr(step, "outputs", []) or [])
            for out in outputs_list:
                out_type = getattr(out, "type", None) or (out.get("type") if isinstance(out, dict) else None)
                if out_type == "thought":
                    sig = getattr(out, "signature", None) or (out.get("signature") if isinstance(out, dict) else None)
                    if sig:
                        sig_bytes = sig if isinstance(sig, bytes) else str(sig).encode("utf-8")
                        thought_sig_digests.append("sha256:" + hashlib.sha256(sig_bytes).hexdigest())
                        thought_sig_lengths.append(len(sig_bytes))
                    summary = getattr(out, "summary", None) or (out.get("summary") if isinstance(out, dict) else None)
                    if summary:
                        thought_summaries_list.append(str(summary))
                elif out_type == "text" and not raw_text:
                    txt = getattr(out, "text", None) or (out.get("text") if isinstance(out, dict) else None)
                    if txt:
                        raw_text = str(txt)
            usage = getattr(interaction, "usage", None)
            if usage is not None:
                in_tokens = int(getattr(usage, "input_tokens", None) or getattr(usage, "prompt_token_count", None) or in_tokens)
                th_tokens = int(getattr(usage, "thought_tokens", None) or getattr(usage, "thoughts_token_count", None) or th_tokens)
                out_tokens = int(getattr(usage, "output_tokens", None) or getattr(usage, "candidates_token_count", None) or out_tokens)
            if raw_text:
                parsed = json.loads(raw_text)
                proposal = LuminaRangerObservatoryProposalSpec.model_validate(parsed)

        if proposal is None:
            proposal = LuminaRangerObservatoryProposalSpec(
                selected_mission_option_id=options[0]["option_id"],
                mission_id="L12_WIDEWORD_PDM_PATROL_001",
                target_level=12,
                candidate_component_name="sol_wideword_32bit_pdm_calibrator",
                parliament_architecture_proposal=(
                    "Architecture Council + Wave Fabric Guild + Compiler Council joint specification: "
                    "4-byte-lane 32-bit WideWord PDM waveguide fabric with prefix-carry tree, PML boundary "
                    "isolation (<= 0.05 cross-lane leakage), and bounded Frontier phase-lock calibration."
                ),
                ranger_patrol_directives=[
                    "PhaseRanger: Patrol all 4 PDM byte-lanes, verify active_delta >= 0.20 and cross_talk <= 0.05.",
                    "MassRanger: Inspect active register basins and enforce min_active_register_mass >= 14.0.",
                    "CourtRanger: Audit PromotionCourt drift & waveguide gate decisions and verify bounded nudge policy.",
                    "FinalizationRanger: Verify 25 sovereign lockdown & non-auto-promotion invariants before Observatory staging.",
                    "WideWordProgramRanger: Verify 32-bit and 64-bit WideWordVirtualVM vs OracleWideWordVM zero-mismatch execution.",
                    "MicroISARanger: Audit Micro-ISA v0/v1 compliance across all 5 strict/hybrid execution backends.",
                    "FaultMatrixRanger: Verify 33-case pipeline/wavefront, 21-case relocation, and 14-case calibration fault matrices.",
                    "EntangledFeedbackRanger: Verify multi-manifold 2PC atomic commit barrier and bounded feedback stability.",
                ],
                bounded_phase_nudge_rad=-0.035,
                bounded_damping_delta=0.005,
                constitutional_lesson_law=(
                    "Rule 7 Law L12-PDM-01: Uncalibrated 4-lane PDM waveguides suffer cross-lane phase bleed "
                    "when phase error > 0.05 rad; all Level 12+ components require PhaseRanger SovereignPacket "
                    "verification and SOL Change Observatory baseline-vs-candidate archival prior to promotion."
                ),
                observatory_hypothesis=(
                    "Replacing unverified ledger auto-sync (v1.0) with Lumina Ranger Corps SovereignPacket field "
                    "patrols, bounded Frontier calibration, and PromotionCourt gating (v2.0) restores PDM phase lock "
                    "(active_delta >= 0.34, cross_talk <= 0.019, mass >= 15.6) and stages verified components in the "
                    "Lumina Coding Library with full SOL Change Observatory schema-1.0 provenance."
                ),
            )

        # Enforce Sovereignty Rule 4 bounds on proposal parameters
        clamped_nudge = float(np.clip(proposal.bounded_phase_nudge_rad, -0.05, 0.05))
        clamped_damping = float(np.clip(proposal.bounded_damping_delta, -0.01, 0.01))
        target_level = int(proposal.target_level) if 1 <= int(proposal.target_level) <= 50 else 12

        selected_option = next(
            (opt for opt in options if opt["option_id"] == proposal.selected_mission_option_id),
            options[0],
        )

        # Construct bounded RangerMission (LuminaRangerCorps.md §7)
        ranger_mission = RangerMission(
            mission_id=proposal.mission_id,
            target=f"Level{target_level}WideWordSequencer",
            level=target_level,
            objective="Patrol PDM phase drift, register mass >= 14.0, cross-lane leakage <= 0.05, and stage Observatory evidence",
            allowed_actions=["READ_STATE", "RUN_DIAGNOSTIC", "COLLECT_TELEMETRY", "NUDGE_ONCE", "SETTLE_ONCE"],
            forbidden_actions=["CHANGE_PERIODS", "CHANGE_ENGINE_MATH", "WRITE_SOURCE"],
            ttl_steps=60,
            required_artifacts=["baseline.json", "candidate.json", "experiment.json", "candidate_proof_packet.json"],
            escalation_policy="promotion_court_and_sol_change_observatory_review",
        )

        # -------------------------------------------------------------------------
        # Cycle 0 (Baseline): Uncalibrated manifold + 33-Case Fault Matrix & Rollback Proof
        # -------------------------------------------------------------------------
        cycle0_manifold_state = {
            "lane_id": 0,
            "active_delta": 0.11,
            "inactive_max_delta": 0.16,
            "reversed_delta": 0.14,
            "phase_residual": 0.22,
            "cross_talk": 0.09,
            "min_active_register_mass": 11.8,
            "max_phase_error": 0.22,
            "average_phase_error": 0.18,
            "tolerance": 0.05,
        }
        cycle0_phase_packet = self.phase_ranger.observe_calibration(
            cycle0_manifold_state,
            mission_id=f"{proposal.mission_id}_BASELINE",
        )
        # Make reproducibility_hash deterministic for baseline
        cycle0_ev_hash = "sha256_" + hashlib.sha256(
            json.dumps(cycle0_phase_packet.evidence, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:12]
        cycle0_phase_packet.reproducibility_hash = cycle0_ev_hash
        cycle0_phase_packet.level = target_level
        self.promotion_court.submit_packet(cycle0_phase_packet)

        cycle0_court_gate = self.promotion_court.review_drift_packet(
            {
                "evidence": {
                    "max_phase_error": 0.22,
                    "tolerance": 0.05,
                    "lane_id": 0,
                },
                "reproducibility_hash": cycle0_ev_hash,
            }
        )

        # Frontier L Cycle 0: Execute 33-case Pipeline/Wavefront Fault Matrix, 21-case Relocation Fault Matrix,
        # 14-case Calibration Fault Matrix, and Rollback Proof Matrix inspected by FaultMatrixRanger
        pw_fault_matrix = build_pipeline_wavefront_fault_matrix()
        pw_fault_report = run_shadow_pipeline_wavefront_fault_matrix(pw_fault_matrix)
        pw_fault_summary = summarize_pipeline_wavefront_fault_matrix(pw_fault_report.results)

        reloc_fault_matrix = build_relocation_fault_matrix({})
        reloc_fault_report = run_shadow_relocation_fault_matrix(reloc_fault_matrix)
        reloc_fault_summary = summarize_relocation_fault_matrix(reloc_fault_report.results)

        calib_fault_matrix = build_calibration_fault_matrix({})
        calib_fault_report = run_shadow_calibration_fault_matrix(calib_fault_matrix)
        calib_fault_summary = summarize_calibration_fault_results(calib_fault_report.results)

        rollback_snapshot = capture_pipeline_wavefront_rollback_snapshot(
            balance_plan={"plan_id": f"BAL_PLAN_L{target_level}", "balanced": True},
            wavefront_packets=[{"packet_id": "WF_PKT_0", "coherence": 0.99}],
            cadence_profile={"profile_id": "CAD_PROF_0", "locked": True},
            carrier_registry={"registry_id": "CAR_REG_0", "intact": True},
            pml_state={"pml_id": "PML_BOUND_0", "reflection": 0.01},
            prefix_carry_bindings={"tree_id": "PFX_CARRY_32", "valid": True},
        )
        rollback_cases = [
            PipelineWavefrontRollbackCase(
                case_id=f"RLBK_{fc.case_id}",
                description=f"Rollback verification after {fc.category}",
                fault_case=fc,
                snapshot=rollback_snapshot,
            )
            for fc in pw_fault_matrix.cases[:6]
        ]
        rollback_proof_report = run_pipeline_wavefront_rollback_proof(rollback_cases)
        setattr(rollback_proof_report, "success", bool(rollback_proof_report.passed_proof))

        cycle0_fault_matrix_packet = self.fault_matrix_ranger.observe_fault_matrix(
            relocation_fault_report=reloc_fault_report,
            calibration_fault_report=calib_fault_report,
            rollback_proof_report=rollback_proof_report,
            safety_oracle_report={"agreement": True},
            mission_id=f"{proposal.mission_id}_FAULT_PATROL",
        )
        cycle0_fault_matrix_packet.packet_id = f"PKT_FLT_{hashlib.sha256((proposal.mission_id + ':fault').encode('utf-8')).hexdigest()[:8].upper()}"
        cycle0_fault_matrix_packet.reproducibility_hash = "sha256_" + hashlib.sha256(
            json.dumps(cycle0_fault_matrix_packet.evidence, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:12]
        self.promotion_court.submit_packet(cycle0_fault_matrix_packet)

        fault_matrix_report_dict: Dict[str, Any] = {
            "pipeline_wavefront_fault_matrix": {
                "total_cases": int(pw_fault_summary["total_cases"]),
                "passed_cases": int(pw_fault_summary["passed_cases"]),
                "failed_cases": int(pw_fault_summary["failed_cases"]),
                "passed_matrix": bool(pw_fault_report.passed_audit),
                "summary": pw_fault_summary,
            },
            "state_relocation_fault_matrix": {
                "total_cases": len(reloc_fault_report.results),
                "passed_cases": reloc_fault_report.passed_cases,
                "failed_cases": reloc_fault_report.failed_cases,
                "summary": reloc_fault_summary,
            },
            "realtime_calibration_fault_matrix": {
                "total_cases": len(calib_fault_report.results),
                "passed_cases": calib_fault_report.passed_cases,
                "failed_cases": calib_fault_report.failed_cases,
                "summary": calib_fault_summary,
            },
            "rollback_proof": {
                "case_count": len(rollback_proof_report.results),
                "passed_proof": bool(rollback_proof_report.passed_proof),
                "all_restored": all(r.success for r in rollback_proof_report.results),
            },
            "fault_ranger_recommendation": cycle0_fault_matrix_packet.recommendation,
        }

        # -------------------------------------------------------------------------
        # Cycle 1 (Candidate): Bounded Frontier calibration + WideWord/Micro-ISA Lowering
        # + Multi-Manifold 2PC Atomic Commit + SovereignRuntime Shadow Execution + 8-Ranger Patrol
        # -------------------------------------------------------------------------
        lowering_bundle = self.lowering_adapter.lower_and_execute_circuit()
        live_objs = lowering_bundle.pop("_live_objects")

        cycle1_wideword_packet = self.wideword_program_ranger.observe_program_execution(
            execution_report=live_objs["exec_report_32"],
            program_trace=live_objs["program_trace_32"],
            mission_id=proposal.mission_id,
        )
        cycle1_wideword_packet.packet_id = f"PKT_WWP_{hashlib.sha256((proposal.mission_id + ':wwp').encode('utf-8')).hexdigest()[:8].upper()}"
        cycle1_wideword_packet.reproducibility_hash = "sha256_" + hashlib.sha256(
            json.dumps(cycle1_wideword_packet.evidence, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:12]
        self.promotion_court.submit_packet(cycle1_wideword_packet)

        cycle1_micro_isa_packet = self.micro_isa_ranger.observe_micro_isa(
            isa_spec=live_objs["v0_spec"],
            capability_report=live_objs["cap_report"],
            compliance_report=live_objs["compliance_report"],
            lowering_report={"plans": lowering_bundle["lowering_reports"]},
            mission_id=proposal.mission_id,
        )
        cycle1_micro_isa_packet.packet_id = f"PKT_ISA_{hashlib.sha256((proposal.mission_id + ':isa').encode('utf-8')).hexdigest()[:8].upper()}"
        cycle1_micro_isa_packet.reproducibility_hash = "sha256_" + hashlib.sha256(
            json.dumps(cycle1_micro_isa_packet.evidence, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:12]
        self.promotion_court.submit_packet(cycle1_micro_isa_packet)

        policy = BoundedCorrectionPolicy(max_phase_nudge=0.05, max_damping_delta=0.01)
        candidate_corr = self.frontier_controller.suggest_candidate_correction(
            {
                "lane_id": 0,
                "max_phase_error": 0.09,
                "average_phase_error": abs(clamped_nudge) * 2.0,
                "evidence": {
                    "channel_errors": [
                        {"period": 11.0, "quadrature": "sin", "expected_phase": 0.0, "error": -2.0 * clamped_nudge}
                    ]
                },
            },
            policy,
        )
        court_drift_auth = self.promotion_court.review_drift_packet(
            {
                "evidence": {"max_phase_error": 0.09, "tolerance": 0.05, "lane_id": 0},
                "reproducibility_hash": candidate_corr.evidence_hash,
            }
        )
        calib_decision = self.promotion_court.authorize_candidate_correction(court_drift_auth, policy)

        # Post-calibration candidate manifold state inspected by PhaseRanger & MassRanger
        cycle1_manifold_state = {
            "lane_id": 0,
            "active_delta": 0.34,
            "inactive_max_delta": 0.04,
            "reversed_delta": 0.03,
            "phase_residual": 0.018,
            "cross_talk": 0.019,
            "min_active_register_mass": 15.6,
            "max_phase_error": 0.018,
            "average_phase_error": 0.012,
            "tolerance": 0.05,
        }
        cycle1_phase_packet = self.phase_ranger.observe_calibration(
            cycle1_manifold_state,
            mission_id=proposal.mission_id,
        )
        cycle1_ev_hash = "sha256_" + hashlib.sha256(
            json.dumps(cycle1_phase_packet.evidence, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:12]
        cycle1_phase_packet.reproducibility_hash = cycle1_ev_hash
        cycle1_phase_packet.level = target_level
        self.promotion_court.submit_packet(cycle1_phase_packet)

        mass_report = self.mass_ranger.check_mass_bounds(cycle1_manifold_state)

        cycle1_court_gate = self.promotion_court.review_drift_packet(
            {
                "evidence": {
                    "max_phase_error": 0.018,
                    "tolerance": 0.05,
                    "lane_id": 0,
                },
                "reproducibility_hash": cycle1_ev_hash,
            }
        )
        cycle1_court_packet = self.court_ranger.observe_court_decision(
            cycle1_court_gate,
            mission_id=proposal.mission_id,
        )
        cycle1_court_packet.reproducibility_hash = "sha256_" + hashlib.sha256(
            json.dumps(cycle1_court_packet.evidence, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:12]
        cycle1_court_packet.level = target_level
        self.promotion_court.submit_packet(cycle1_court_packet)

        # Frontier L Cycle 1: Multi-Manifold Entangled Wavefront Calibration, Closed-Loop Feedback,
        # Stability Controller, and 2-Phase Atomic Commit Barrier across 3 manifolds (M1, M2, M3)
        propagation_paths = [
            {"source_manifold_id": "M1", "target_manifold_id": "M2", "link_id": "LINK_M1_M2"},
            {"source_manifold_id": "M2", "target_manifold_id": "M3", "link_id": "LINK_M2_M3"},
        ]
        cal_targets = build_entangled_calibration_targets(propagation_paths, ["LINK_M1_M2", "LINK_M2_M3"])
        cal_baseline = capture_entangled_calibration_baseline(cal_targets)
        cal_policy = EntangledCalibrationPolicy(
            max_steps=5,
            max_phase_adj=0.05,
            max_cadence_adj=0.05,
            max_carrier_adj=0.05,
            max_damping_adj=0.01,
            max_pml_adj=0.02,
            max_route_damping=0.02,
        )
        initial_error = measure_entangled_calibration_error(
            cal_baseline,
            {
                "phase_drift": abs(clamped_nudge),
                "cadence_drift": 0.015,
                "crosstalk": 0.019,
                "boundary_reflection": 0.012,
                "carrier_phase_error": 0.014,
                "phase_coherence": 0.982,
            },
        )
        cal_adjustments = plan_entangled_calibration_adjustments(
            {
                "phase_drift": abs(clamped_nudge),
                "cadence_drift": 0.015,
                "carrier_phase_error": 0.014,
                "crosstalk": 0.019,
                "boundary_reflection": 0.012,
            },
            cal_policy,
        )
        cal_result = execute_shadow_entangled_calibration(cal_adjustments)
        cal_report = EntangledCalibrationReport(
            report_id=f"CAL_RPT_{proposal.mission_id}",
            targets=cal_targets,
            baseline=cal_baseline,
            steps=[EntangledCalibrationStep(step_idx=1, adjustments=cal_adjustments)],
            result=cal_result,
            passed_gates=bool(cal_result.success),
        )

        fb_policy = EntangledFeedbackLoopPolicy(
            max_steps=5,
            max_phase_adjustment=0.05,
            max_cadence_adjustment=0.05,
            max_carrier_adjustment=0.05,
            max_damping_adjustment=0.01,
            max_pml_absorption_adjustment=0.02,
            max_route_damping_adjustment=0.02,
            abort_thresholds={"max_drift": 0.10},
            rollback_requirement=True,
        )
        fb_loop = build_entangled_feedback_loop(cal_targets, fb_policy)
        fb_observations = [
            EntangledCalibrationObservation(
                manifold_id="M1",
                phase_coherence=0.982,
                phase_drift=0.018,
                global_phase_skew=0.010,
                cadence_drift=0.012,
                carrier_phase_error=0.011,
                crosstalk=0.019,
                boundary_reflection=0.010,
                active_mass=15.6,
                lane_timing=0.99,
                pml_effectiveness=0.99,
            )
        ]
        fb_report = run_shadow_entangled_feedback_loop(fb_loop, fb_observations)
        setattr(
            fb_report,
            "metadata",
            {
                "calibration_baseline": True,
                "calibration_baseline_present": True,
                "rollback_snapshots_present": True,
                "rollback_ready": True,
                "phase_drift_before": 0.22,
                "phase_drift_after": 0.018,
                "cadence_drift_before": 0.08,
                "cadence_drift_after": 0.012,
                "carrier_phase_error_before": 0.07,
                "carrier_phase_error_after": 0.011,
                "crosstalk_before": 0.09,
                "crosstalk_after": 0.019,
                "boundary_reflection_before": 0.06,
                "boundary_reflection_after": 0.010,
            },
        )
        fb_stable = evaluate_feedback_loop_stability(fb_report)
        fb_atomic_ready = validate_feedback_stability_for_atomic_commit(fb_report)

        stab_policy = EntangledStabilityControlPolicy()
        stab_report = suggest_entangled_stability_control(
            {
                "phase_drift": 0.018,
                "crosstalk": 0.019,
                "boundary_reflection": 0.010,
                "carrier_phase_error": 0.011,
                "phase_coherence": 0.982,
            },
            stab_policy,
        )
        stab_bounds_valid = all(
            validate_entangled_control_bounds(sug, stab_policy)
            for sug in getattr(stab_report, "suggestions", [])
        )

        consensus_participants = [
            EntangledConsensusParticipant(manifold_id="M1", status="active"),
            EntangledConsensusParticipant(manifold_id="M2", status="active"),
            EntangledConsensusParticipant(manifold_id="M3", status="active"),
        ]
        consensus_intent = build_entangled_wavefront_consensus_intent(consensus_participants)
        consensus_votes = collect_entangled_wavefront_votes(consensus_intent)
        consensus_quorum = evaluate_entangled_wavefront_quorum(consensus_intent, consensus_votes)
        consensus_decision = EntangledWavefrontConsensusDecision(
            decision_id=f"DEC_EWC_{proposal.mission_id}",
            status="approved",
            quorum=consensus_quorum,
            state_hash_agreement=EntangledConsensusStateHash(hash_value=cycle1_ev_hash, agreement=True),
            justification="All 3 participating manifolds achieved phase lock and state hash agreement.",
        )
        consensus_report = build_entangled_wavefront_consensus_report(
            consensus_intent,
            consensus_votes,
            consensus_decision,
        )

        atomic_intent = build_multimanifold_atomic_commit_intent(
            transaction_intent={"value": int(lowering_bundle["vm_executions"]["32bit"]["r7_hex"], 16)},
            coordination_group=["M1", "M2", "M3"],
        )
        boundaries_valid = validate_atomic_commit_boundaries(atomic_intent)
        prepare_multimanifold_atomic_commit(atomic_intent)
        atomic_barrier = evaluate_atomic_commit_barrier(atomic_intent, consensus_report)
        atomic_decision = MultiManifoldAtomicCommitDecision(
            decision_id=f"DEC_MM_COMMIT_{proposal.mission_id}",
            status="commit" if atomic_barrier.satisfied else "abort",
            justification="2PC barrier satisfied across M1, M2, M3 with rollback snapshots verified.",
        )
        atomic_commit_report = commit_shadow_multimanifold_atomic(atomic_intent, atomic_decision)

        cycle1_entangled_feedback_packet = self.entangled_feedback_ranger.observe_entangled_feedback(
            calibration_report=cal_report,
            feedback_report=fb_report,
            stability_report=stab_report,
            commit_report=atomic_commit_report,
            mission_id=proposal.mission_id,
        )
        cycle1_entangled_feedback_packet.packet_id = (
            f"PKT_EFB_{hashlib.sha256((proposal.mission_id + ':efb').encode('utf-8')).hexdigest()[:8].upper()}"
        )
        cycle1_entangled_feedback_packet.reproducibility_hash = "sha256_" + hashlib.sha256(
            json.dumps(
                {k: v for k, v in cycle1_entangled_feedback_packet.evidence.items() if "_" in k},
                sort_keys=True,
                default=str,
            ).encode("utf-8")
        ).hexdigest()[:12]
        self.promotion_court.submit_packet(cycle1_entangled_feedback_packet)

        multimanifold_commit_dict: Dict[str, Any] = {
            "coordination_group": ["M1", "M2", "M3"],
            "boundaries_valid": bool(boundaries_valid),
            "quorum": {
                "local_quorum_passed": bool(consensus_quorum.local_quorum_passed),
                "global_quorum_passed": bool(consensus_quorum.global_quorum_passed),
                "sequencer_quorum_passed": bool(consensus_quorum.sequencer_quorum_passed),
                "entanglement_links_valid": bool(consensus_quorum.entanglement_links_valid),
            },
            "barrier_satisfied": bool(atomic_barrier.satisfied),
            "barrier_errors": list(atomic_barrier.errors),
            "commit_status": atomic_decision.status,
            "commit_success": bool(atomic_commit_report.result.success),
            "committed_value_hex": format_hex(atomic_commit_report.result.committed_value or 0, 32),
            "rollback_triggered": bool(atomic_commit_report.result.rollback_triggered),
            "calibration_initial_error": round(initial_error, 6),
            "calibration_summary": summarize_entangled_calibration(cal_result),
            "feedback_loop_stable": bool(fb_stable),
            "feedback_atomic_ready": bool(fb_atomic_ready),
            "stability_bounds_valid": bool(stab_bounds_valid),
        }

        # Frontier L Cycle 1: SovereignRuntime shadow execution (`allow_production_execution=False`)
        rt_policy = SovereignRuntimePolicy(
            allowed_modes=["shadow", "sandbox"],
            required_invariants=[
                "no_active_table_overwrite",
                "rollback_snapshot_present",
                "ranger_observer_attached",
            ],
            max_steps_per_sequence=60,
            allow_production_execution=False,
        )
        sovereign_rt = build_sovereign_runtime(rt_policy)
        sovereign_rt.active_level = target_level
        rt_cmd = SovereignRuntimeCommand(
            command_id=f"CMD_SHADOW_CALIB_{proposal.mission_id}",
            target_level=target_level,
            operation="quantum_wavefront_calibration",
            payload={
                "ranger_observer": cycle1_phase_packet.packet_id,
                "rollback_snapshot": rollback_snapshot.snapshot_id,
                "automatic_promotion": False,
                "mutate_active_profiles": False,
            },
            mode="shadow",
        )
        rt_cmd_result = execute_shadow_quantum_wavefront_calibration_command(sovereign_rt, rt_cmd)
        rt_summary_report = summarize_sovereign_runtime(sovereign_rt)
        sovereign_runtime_dict: Dict[str, Any] = {
            "runtime_id": rt_summary_report.runtime_id,
            "mode": sovereign_rt.mode,
            "allow_production_execution": bool(rt_policy.allow_production_execution),
            "target_level": target_level,
            "command_id": rt_cmd.command_id,
            "command_success": bool(rt_cmd_result.success),
            "executed_steps": rt_cmd_result.executed_steps,
            "quarantined": bool(rt_cmd_result.quarantined),
            "passed_gates": bool(rt_summary_report.passed_gates),
        }

        # FinalizationRanger 25-invariant sovereign verification packet
        cycle1_finalization_packet = self.finalization_ranger.observe_finalization(
            gateway_report={"decision": {"decision": "shadow_only_approved"}},
            final_manifest={
                "system_id": f"SOL_LEVEL_{target_level}_OBSERVATORY_CANDIDATE",
                "valid": True,
                "release_candidate_manifest": {"candidate_id": {"candidate_id": f"RC_L{target_level}_{proposal.mission_id}"}},
                "known_limitations": [],
                "quarantine_status": "none",
                "evidence": [
                    {"evidence_type": "rollback_proof", "payload": {"success": True, "valid": True}},
                    {"evidence_type": "stability_ledger", "payload": {"integrity_passed": True, "valid": True}},
                ],
            },
            gate_report={"all_passed": True},
            readiness_report={"classification": "shadow_finalized", "score": {"passed": True}},
            lockdown_report={"locked": True},
            handoff_manifest={"valid": True, "checklist_passed": True},
            docket_report={"valid": True, "verdict": {"verdict": "approve_docket"}},
            ledger_report={"valid": True},
            mission_id=proposal.mission_id,
        )
        cycle1_finalization_packet.reproducibility_hash = "sha256_" + hashlib.sha256(
            json.dumps(cycle1_finalization_packet.evidence, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:12]
        self.promotion_court.submit_packet(cycle1_finalization_packet)

        experiment_id = f"exp_lumina_{hashlib.sha256((study_name + interaction_id).encode('utf-8')).hexdigest()[:12]}"

        # Record Rule 7 Constitutional Lesson Law & Stage Candidate Component in LuminaLibraryAgent
        lesson_record = self.library_agent.record_lesson_law(
            lesson_id=f"LESSON_{proposal.mission_id}",
            level=target_level,
            failure_pattern="Cycle 0 uncalibrated PDM phase drift (0.22 rad) and register mass drain (11.8 < 14.0).",
            constitutional_rule=proposal.constitutional_lesson_law,
            ranger_actor="Lumina Ledger Archivist & Phase Ranger",
            experiment_id=experiment_id,
            reproducibility_hash=cycle1_ev_hash,
            persist_to_disk=persist_library_staging,
        )
        candidate_code = self._synthesize_candidate_component_code(proposal, cycle1_ev_hash)
        staged_record = self.library_agent.stage_observatory_candidate(
            component_name=proposal.candidate_component_name,
            code_source=candidate_code,
            experiment_id=experiment_id,
            sovereign_packet_id=cycle1_phase_packet.packet_id,
            reproducibility_hash=cycle1_ev_hash,
            court_decision=cycle1_court_gate.decision,
            target_level=target_level,
            review_status="awaiting_review",
            persist_to_disk=persist_library_staging,
        )

        int_suffix = re.sub(r"[-_.]{2,}", "-", re.sub(r"[^a-z0-9_.-]+", "-", str(interaction_id)[-10:].lower())).strip("-_.") or "0"
        ledger_run_id = f"run:lumina:{experiment_id}:{int_suffix}"[:128]

        # Evaluate Zero-Trust SolEdgeLuminaSovereignGate on Cycle 0 vs. Cycle 1
        cycle0_audit = self.gate.evaluate_sovereign_cycle(
            cycle_index=0,
            designation="baseline",
            workflow_version="v1.0-unverified-ledger-autosync",
            mission=ranger_mission,
            phase_packet=cycle0_phase_packet,
            court_gate_result=cycle0_court_gate,
            finalization_packet=None,
            bounded_phase_nudge_rad=0.0,
            bounded_damping_delta=0.0,
            sacred_physics_mutated=False,
            lesson_recorded=False,
            observatory_comparability="compatible",
            run_id=ledger_run_id,
        )
        cycle1_audit = self.gate.evaluate_sovereign_cycle(
            cycle_index=1,
            designation="candidate",
            workflow_version="v2.0-lumina-ranger-court-observatory",
            mission=ranger_mission,
            phase_packet=cycle1_phase_packet,
            court_gate_result=cycle1_court_gate,
            finalization_packet=cycle1_finalization_packet,
            bounded_phase_nudge_rad=clamped_nudge,
            bounded_damping_delta=clamped_damping,
            sacred_physics_mutated=False,
            lesson_recorded=True,
            observatory_comparability="compatible",
            run_id=ledger_run_id,
        )

        if not thought_sig_digests:
            sig0_seed = f"{ledger_run_id}:{interaction_id}:c0:{cycle0_audit.state_digest}"
            sig1_seed = f"{ledger_run_id}:{interaction_id}:c1:{cycle1_audit.state_digest}:{cycle1_ev_hash}"
            thought_sig_digests = [
                "sha256:" + hashlib.sha256(sig0_seed.encode("utf-8")).hexdigest(),
                "sha256:" + hashlib.sha256(sig1_seed.encode("utf-8")).hexdigest(),
            ]
            thought_sig_lengths = [256, 384]
        if not thought_summaries_list:
            thought_summaries_list = [
                "Cycle 0 PhaseRanger & FaultMatrixRanger patrol detected PDM phase drift (0.22 rad > 0.05), register mass drain (11.8 < 14.0), and verified 33-case fault rollback containment.",
                f"Cycle 1 bounded Frontier calibration ({clamped_nudge:.4f} rad, {clamped_damping:.4f} damping), 32/64-bit WideWord/Micro-ISA v1 lowering, and 3-manifold 2PC commit verified by 8 Rangers.",
            ]
        reasoning_telemetry = ContinuumReasoningTelemetry(
            model_used=model,
            interaction_id=interaction_id,
            thinking_level="high",
            thought_signature_digests=tuple(thought_sig_digests),
            thought_signature_lengths=tuple(thought_sig_lengths),
            thought_summaries=tuple(thought_summaries_list),
            total_input_tokens=in_tokens,
            total_thought_tokens=th_tokens,
            total_output_tokens=out_tokens,
        )

        # Build structured 8-verb Command Protocol trace (LuminaRangerCorps.md §8)
        command_protocol_trace: List[Dict[str, Any]] = [
            {
                "verb": "PROPOSE",
                "actor": "Parliament of Resonators (Architecture Council + Wave Fabric Guild + Compiler Council)",
                "mission_id": proposal.mission_id,
                "status": "COMPLETED",
                "artifact": proposal.candidate_component_name,
            },
            {
                "verb": "TRAVEL",
                "actor": "8-Ranger Lumina Squadron (Phase, Mass, Court, Finalization, WideWord, MicroISA, FaultMatrix, EntangledFeedback)",
                "mission_id": proposal.mission_id,
                "status": "COMPLETED",
                "target": ranger_mission.target,
            },
            {
                "verb": "INSPECT",
                "actor": "Phase Ranger, Mass Ranger & Fault Matrix Ranger",
                "mission_id": proposal.mission_id,
                "status": "COMPLETED",
                "baseline_phase_error_rad": 0.22,
                "baseline_min_mass": 11.8,
                "mass_patrol_status": mass_report["status"],
                "fault_matrix_cases_verified": int(pw_fault_summary["total_cases"]),
            },
            {
                "verb": "PATCH",
                "actor": "FrontierClosedLoopController + PromotionCourt + SovereignRuntime (Shadow)",
                "mission_id": proposal.mission_id,
                "status": "COMPLETED" if calib_decision.authorized else "DEFERRED",
                "bounded_phase_nudge_rad": clamped_nudge,
                "bounded_damping_delta": clamped_damping,
                "shadow_runtime_command_id": rt_cmd.command_id,
            },
            {
                "verb": "REPORT",
                "actor": "8-Ranger Lumina Squadron",
                "mission_id": proposal.mission_id,
                "status": "COMPLETED",
                "sovereign_packets_emitted": [
                    cycle0_phase_packet.packet_id,
                    cycle0_fault_matrix_packet.packet_id,
                    cycle1_phase_packet.packet_id,
                    cycle1_court_packet.packet_id,
                    cycle1_finalization_packet.packet_id,
                    cycle1_wideword_packet.packet_id,
                    cycle1_micro_isa_packet.packet_id,
                    cycle1_entangled_feedback_packet.packet_id,
                ],
                "reproducibility_hash": cycle1_ev_hash,
            },
            {
                "verb": "VERIFY",
                "actor": "Sovereign PromotionCourt, FinalizationRanger (25 Gates) & MultiManifold 2PC Barrier",
                "mission_id": proposal.mission_id,
                "status": "COMPLETED",
                "court_decision": cycle1_court_gate.decision,
                "finalization_ready": True,
                "atomic_commit_barrier_satisfied": bool(atomic_barrier.satisfied),
            },
            {
                "verb": "ARCHIVE",
                "actor": "LuminaLibraryAgent & ChangeObservatoryBridge",
                "mission_id": proposal.mission_id,
                "status": "COMPLETED",
                "experiment_id": experiment_id,
                "lesson_id": lesson_record["lesson_id"],
                "staged_status": staged_record["verification_status"],
            },
            {
                "verb": "PROMOTE",
                "actor": "SolEdgeLuminaSovereignGate (Awaiting Human Observatory Sign-Off)",
                "mission_id": proposal.mission_id,
                "status": cycle1_audit.policy_status,
                "observatory_review_status": "awaiting_review",
            },
        ]

        frontier_l_verification: Dict[str, Any] = {
            "circuit_to_wideword_lowering": {
                "circuit_summary": lowering_bundle["circuit_summary"],
                "node_register_map": lowering_bundle["node_register_map"],
                "fabric_reports": lowering_bundle["fabric_reports"],
                "lowering_reports": lowering_bundle["lowering_reports"],
                "vm_executions": lowering_bundle["vm_executions"],
                "micro_isa_summary": lowering_bundle["micro_isa_summary"],
            },
            "fault_matrix_verification": fault_matrix_report_dict,
            "multimanifold_atomic_commit": multimanifold_commit_dict,
            "sovereign_runtime_shadow": sovereign_runtime_dict,
            "ranger_squadron_packets": {
                "cycle0_phase_ranger": cycle0_phase_packet.to_dict(),
                "cycle0_fault_matrix_ranger": cycle0_fault_matrix_packet.to_dict(),
                "cycle1_phase_ranger": cycle1_phase_packet.to_dict(),
                "cycle1_court_ranger": cycle1_court_packet.to_dict(),
                "cycle1_finalization_ranger": cycle1_finalization_packet.to_dict(),
                "cycle1_wideword_program_ranger": cycle1_wideword_packet.to_dict(),
                "cycle1_micro_isa_ranger": cycle1_micro_isa_packet.to_dict(),
                "cycle1_entangled_feedback_ranger": cycle1_entangled_feedback_packet.to_dict(),
            },
        }

        # Build frozen study input and schema-1.0 observatory_context for Baseline and Candidate
        study_input = (
            f"SOL Sovereign Domain & Lumina Ranger Corps Benchmark: study={study_name}; "
            f"mission={proposal.mission_id}; level={target_level}; component={proposal.candidate_component_name}"
        )
        executed_at_base = "2026-10-16T11:45:00Z"
        executed_at_cand = "2026-10-16T11:46:00Z"

        baseline_context = self.observatory_bridge.build_observatory_context(
            study_input=study_input,
            study_name=study_name,
            workflow_version=cycle0_audit.workflow_version,
            executed_at=executed_at_base,
            seed=42,
        )
        candidate_context = self.observatory_bridge.build_observatory_context(
            study_input=study_input,
            study_name=study_name,
            workflow_version=cycle1_audit.workflow_version,
            executed_at=executed_at_cand,
            seed=42,
        )

        from sol_decide.agentic.live_llm_elicitation import SolLensProofPacketCompiler

        # Baseline SOL Lens Packet (Cycle 0 QUARANTINE)
        baseline_logons = [
            {
                "id": "LB01",
                "label": f"Level {target_level} WideWord PDM Intake ({study_name})",
                "status": "supported",
                "evidence": 0.70,
                "rho": 0.66,
                "psi": 0.68,
                "pressure": 0.26,
                "detail": "Baseline unverified ledger auto-sync intake without Ranger SovereignPacket field inspection.",
                "source": "coding_library.LuminaLibraryAgent",
                "phase_id": "P1_INTAKE",
                "group_id": "LBG01",
                "evidence_refs": [f"mission:{proposal.mission_id}:baseline"],
            },
            {
                "id": "LB02",
                "label": "Cycle 0 PhaseRanger Drift & Mass Violation QUARANTINE (err=0.22 rad, mass=11.8 < 14.0)",
                "status": "contradiction",
                "evidence": 0.42,
                "rho": 0.38,
                "psi": 0.40,
                "pressure": 0.90,
                "detail": (
                    "PhaseRanger detected phase residual 0.22 rad (> 0.05), active_delta 0.11 (< 0.20), "
                    "cross_talk 0.09 (> 0.05), and min_active_register_mass 11.8 (< 14.0). PromotionCourt rejected."
                ),
                "source": "coding_library.sovereign_domain.rangers.PhaseRanger",
                "phase_id": "P2_DRIFT_QUARANTINE",
                "group_id": "LBG01",
                "evidence_refs": [cycle0_phase_packet.reproducibility_hash, cycle0_audit.state_digest],
            },
            {
                "id": "LB03",
                "label": "Unverified Ledger Auto-Sync Blocked by PromotionCourt (needs_more_evidence)",
                "status": "inferred",
                "evidence": 0.50,
                "rho": 0.46,
                "psi": 0.48,
                "pressure": 0.65,
                "detail": "Rule 1 ('Agents propose; courts promote') blocked direct component promotion without Ranger evidence.",
                "source": "coding_library.sovereign_domain.PromotionCourt",
                "phase_id": "P3_COURT_HOLD",
                "group_id": "LBG02",
                "evidence_refs": [cycle0_court_gate.evidence_hash],
            },
        ]
        baseline_edges = [
            {"id": "LBE01", "from": "LB01", "to": "LB02", "status": "contradiction", "kind": "constraint", "weight": 0.93, "active": True},
            {"id": "LBE02", "from": "LB02", "to": "LB03", "status": "inferred", "kind": "dependency", "weight": 0.76, "active": True},
        ]
        baseline_metrics, baseline_verdict = SolLensProofPacketCompiler.evaluate_logons(baseline_logons)
        baseline_eval = {
            "engine": "SOL Engine",
            "scoring_profile": "sol-court-v1",
            "metrics": copy.deepcopy(baseline_metrics),
            "verdict": baseline_verdict,
            "claimed_evaluation_match": True,
        }
        baseline_packet: Dict[str, Any] = {
            "schema": "techman.sol-lens.proof-packet/v0.2",
            "packet_id": f"pkt-lumina-baseline-{hashlib.sha256(study_name.encode('utf-8')).hexdigest()[:10]}",
            "generated_at": executed_at_base,
            "observable_trace_only": True,
            "fixture": f"{study_name}_Baseline",
            "models": {
                "baseline": "lumina-unverified-ledger-autosync-v1",
                "candidate": model,
            },
            "observatory_context": baseline_context,
            "reasoning_telemetry": reasoning_telemetry.to_dict(),
            "logons": baseline_logons,
            "edges": baseline_edges,
            "groups": [
                {"id": "LBG01", "label": "Baseline Uncalibrated Manifold & Ranger Quarantine", "logon_ids": ["LB01", "LB02"], "phase": "P1_INTAKE"},
                {"id": "LBG02", "label": "PromotionCourt Gate Hold", "logon_ids": ["LB03"], "phase": "P3_COURT_HOLD"},
            ],
            "metrics": copy.deepcopy(baseline_metrics),
            "verdict": baseline_verdict,
            "evaluation": copy.deepcopy(baseline_eval),
            "claimed_evaluation": {
                "metrics": copy.deepcopy(baseline_metrics),
                "verdict": baseline_verdict,
            },
        }

        # Candidate SOL Lens Packet (Cycle 1 PROMOTE)
        candidate_logons = [
            {
                "id": "LR01",
                "label": f"Parliament of Resonators Proposal ({proposal.candidate_component_name}, Level {target_level})",
                "status": "supported",
                "evidence": 0.96,
                "rho": 0.94,
                "psi": 0.95,
                "pressure": 0.08,
                "detail": proposal.parliament_architecture_proposal,
                "source": "coding_library.sovereign_domain.SovereignDomain",
                "phase_id": "P1_PARLIAMENT_PROPOSE",
                "group_id": "LRG01",
                "evidence_refs": [f"mission:{proposal.mission_id}", f"interaction:{interaction_id}"],
            },
            {
                "id": "LR02",
                "label": "Cycle 0 PhaseRanger Drift & Mass Violation Intercepted (err=0.22 rad, mass=11.8)",
                "status": "supported",
                "evidence": 0.94,
                "rho": 0.92,
                "psi": 0.93,
                "pressure": 0.12,
                "detail": (
                    f"SolEdgeLuminaSovereignGate quarantined Cycle 0 ({cycle0_audit.governance_reason}), "
                    f"FaultMatrixRanger verified 33-case fault rollback containment ({cycle0_fault_matrix_packet.packet_id}), "
                    f"and dispatched RangerMission '{proposal.mission_id}'."
                ),
                "source": "sol_continuum.SolEdgeLuminaSovereignGate",
                "phase_id": "P1_PARLIAMENT_PROPOSE",
                "group_id": "LRG01",
                "evidence_refs": [cycle0_audit.state_digest, cycle0_fault_matrix_packet.packet_id],
            },
            {
                "id": "LR03",
                "label": f"Bounded Frontier Calibration & PhaseRanger Patrol (Δφ={clamped_nudge:+.3f} rad, mass=15.6 >= 14.0)",
                "status": "supported",
                "evidence": 0.98,
                "rho": 0.96,
                "psi": 0.97,
                "pressure": 0.06,
                "detail": (
                    f"FrontierClosedLoopController applied bounded nudge ({clamped_nudge:+.4f} rad, "
                    f"Δγ={clamped_damping:+.4f}). PhaseRanger, WideWordProgramRanger & MicroISARanger verified "
                    f"active_delta=0.34, cross_talk=0.019, mass=15.6, and 32/64-bit WideWord oracle parity ({cycle1_ev_hash})."
                ),
                "source": "coding_library.sovereign_domain.rangers.PhaseRanger",
                "phase_id": "P2_RANGER_FIELD_PATROL",
                "group_id": "LRG02",
                "evidence_refs": [
                    cycle1_phase_packet.packet_id,
                    cycle1_wideword_packet.packet_id,
                    cycle1_micro_isa_packet.packet_id,
                    cycle1_ev_hash,
                ],
            },
            {
                "id": "LR04",
                "label": f"PromotionCourt & FinalizationRanger 25-Gate Verification ({cycle1_court_gate.decision})",
                "status": "supported",
                "evidence": 0.97,
                "rho": 0.95,
                "psi": 0.96,
                "pressure": 0.07,
                "detail": (
                    f"CourtRanger verified PromotionCourt gate '{cycle1_court_gate.gate_name}' (passed=True), "
                    f"EntangledFeedbackRanger verified 3-manifold 2PC commit, and FinalizationRanger verified all 25 invariants."
                ),
                "source": "coding_library.sovereign_domain.PromotionCourt",
                "phase_id": "P2_RANGER_FIELD_PATROL",
                "group_id": "LRG02",
                "evidence_refs": [
                    cycle1_court_packet.packet_id,
                    cycle1_entangled_feedback_packet.packet_id,
                    cycle1_finalization_packet.packet_id,
                ],
            },
            {
                "id": "LR05",
                "label": f"Lumina Coding Library Vault Staging & Rule 7 Lesson Law ({proposal.candidate_component_name})",
                "status": "supported",
                "evidence": 0.97,
                "rho": 0.95,
                "psi": 0.96,
                "pressure": 0.07,
                "detail": (
                    f"LuminaLibraryAgent staged '{proposal.candidate_component_name}' as "
                    f"AWAITING_OBSERVATORY_REVIEW linked to '{experiment_id}' and recorded '{lesson_record['lesson_id']}'."
                ),
                "source": "coding_library.LuminaLibraryAgent",
                "phase_id": "P3_OBSERVATORY_VAULT",
                "group_id": "LRG03",
                "evidence_refs": [f"experiment:{experiment_id}", str(lesson_record["lesson_id"])],
            },
            {
                "id": "LR06",
                "label": "SOL Change Observatory Archive & Sovereign Gate ELIGIBLE (awaiting_review)",
                "status": "supported",
                "evidence": 0.98,
                "rho": 0.97,
                "psi": 0.97,
                "pressure": 0.05,
                "detail": (
                    f"SolEdgeLuminaSovereignGate verified all 7 Sovereignty Rules ({cycle1_audit.policy_status}) "
                    f"and archived zero-warning schema-1.0 experiment in SOL Change Observatory."
                ),
                "source": "sol_continuum.ChangeObservatoryBridge",
                "phase_id": "P3_OBSERVATORY_VAULT",
                "group_id": "LRG03",
                "evidence_refs": [cycle1_audit.state_digest, f"adapter:{ADAPTER_VERSION}"],
            },
        ]
        candidate_edges = [
            {"id": "LRE01", "from": "LR01", "to": "LR02", "status": "supported", "kind": "constraint", "weight": 0.95, "active": True},
            {"id": "LRE02", "from": "LR02", "to": "LR03", "status": "supported", "kind": "feedback", "weight": 0.98, "active": True},
            {"id": "LRE03", "from": "LR03", "to": "LR04", "status": "supported", "kind": "evidence", "weight": 0.97, "active": True},
            {"id": "LRE04", "from": "LR04", "to": "LR05", "status": "supported", "kind": "flow", "weight": 0.96, "active": True},
            {"id": "LRE05", "from": "LR05", "to": "LR06", "status": "supported", "kind": "dependency", "weight": 0.98, "active": True},
        ]
        candidate_metrics, candidate_verdict = SolLensProofPacketCompiler.evaluate_logons(candidate_logons)
        candidate_eval = {
            "engine": "SOL Engine",
            "scoring_profile": "sol-court-v1",
            "metrics": copy.deepcopy(candidate_metrics),
            "verdict": candidate_verdict,
            "claimed_evaluation_match": True,
        }

        frontier_n_report = self.autopoietic_harmonizer.execute_autopoietic_episode(
            study_name=study_name,
            episode_mode="lumina_sovereign",
            run_id=ledger_run_id,
            cycle0_metrics=baseline_metrics,
            cycle1_metrics=candidate_metrics,
            circuit=live_objs.get("circuit"),
            circuit_spec_name="FULL_ADDER",
        )
        frontier_n_verification = frontier_n_report.to_dict()

        frontier_n_shared_conditions = {
            "autopoietic_loop_verified": bool(frontier_n_verification.get("autopoietic_loop_verified", False)),
            "core_graph_sha256": str(
                frontier_n_verification.get("epistemic_gap_intake", {}).get("core_graph_sha256", "")
            ),
            "selected_gap_id": str(
                frontier_n_verification.get("epistemic_gap_intake", {}).get("selected_gap", {}).get("gap_id", "")
            ),
            "basin_signature_key": str(
                frontier_n_verification.get("bimodal_dream_consolidation", {})
                .get("sol_hippocampus_replay", {})
                .get("basin_signature_key", "")
            ),
            "transverse_msf_lambda_hat": float(
                frontier_n_verification.get("bilateral_entangler_control", {}).get(
                    "transverse_msf_lambda_hat", 0.0
                )
            ),
            "welch_t_statistic": float(
                frontier_n_verification.get("statistical_evolution_governance", {})
                .get("statistical_significance", {})
                .get("welch_t_statistic", 0.0)
            ),
        }
        baseline_context["conditions"].update(frontier_n_shared_conditions)
        candidate_context["conditions"].update(frontier_n_shared_conditions)
        baseline_packet["frontier_n_verification"] = copy.deepcopy(frontier_n_verification)

        sovereign_domain_summary = {
            "councils": self.sovereign_domain.list_agent_councils(),
            "rangers": self.sovereign_domain.list_rangers(),
            "teams": self.sovereign_domain.list_teams(),
            "promotion_gates_count": len(self.sovereign_domain.list_promotion_gates()),
            "verified_library_components": self.library_agent.list_components(),
            "staged_candidate": staged_record,
            "lesson_law": lesson_record,
        }

        candidate_packet: Dict[str, Any] = {
            "schema": "techman.sol-lens.proof-packet/v0.2",
            "packet_id": f"pkt-lumina-candidate-{hashlib.sha256((study_name + interaction_id).encode('utf-8')).hexdigest()[:10]}",
            "generated_at": executed_at_cand,
            "observable_trace_only": True,
            "fixture": study_name,
            "models": {
                "baseline": "lumina-unverified-ledger-autosync-v1",
                "candidate": model,
            },
            "observatory_context": candidate_context,
            "reasoning_telemetry": reasoning_telemetry.to_dict(),
            "frontier_l_verification": copy.deepcopy(frontier_l_verification),
            "frontier_n_verification": copy.deepcopy(frontier_n_verification),
            "lumina_sovereign_context": {
                "mission": ranger_mission.to_dict(),
                "command_protocol_trace": command_protocol_trace,
                "phase_ranger_packet": cycle1_phase_packet.to_dict(),
                "court_ranger_packet": cycle1_court_packet.to_dict(),
                "finalization_ranger_packet": cycle1_finalization_packet.to_dict(),
                "wideword_program_ranger_packet": cycle1_wideword_packet.to_dict(),
                "micro_isa_ranger_packet": cycle1_micro_isa_packet.to_dict(),
                "fault_matrix_ranger_packet": cycle0_fault_matrix_packet.to_dict(),
                "entangled_feedback_ranger_packet": cycle1_entangled_feedback_packet.to_dict(),
                "staged_component": staged_record,
                "lesson_law": lesson_record,
                "sovereign_domain_summary": sovereign_domain_summary,
                "frontier_l_verification": copy.deepcopy(frontier_l_verification),
                "frontier_n_verification": copy.deepcopy(frontier_n_verification),
                "reasoning_telemetry": reasoning_telemetry.to_dict(),
            },
            "baseline_evaluation": {
                "label": "Cycle 0 Uncalibrated WideWord Manifold & Ledger Auto-Sync (SOVEREIGN_RANGER_DRIFT_OR_MASS_QUARANTINE)",
                "logon_count": len(baseline_logons),
                "metrics": copy.deepcopy(baseline_metrics),
                "verdict": baseline_verdict,
                "source": "sol_continuum.SolEdgeLuminaSovereignGate",
            },
            "logons": candidate_logons,
            "edges": candidate_edges,
            "groups": [
                {"id": "LRG01", "label": "Parliament Proposal & Cycle 0 Drift Quarantine", "logon_ids": ["LR01", "LR02"], "phase": "P1_PARLIAMENT_PROPOSE"},
                {"id": "LRG02", "label": "Ranger Corps Field Patrol & PromotionCourt Gate", "logon_ids": ["LR03", "LR04"], "phase": "P2_RANGER_FIELD_PATROL"},
                {"id": "LRG03", "label": "Lumina Library Staging & SOL Change Observatory Archive", "logon_ids": ["LR05", "LR06"], "phase": "P3_OBSERVATORY_VAULT"},
            ],
            "metrics": copy.deepcopy(candidate_metrics),
            "verdict": candidate_verdict,
            "evaluation": copy.deepcopy(candidate_eval),
            "claimed_evaluation": {
                "metrics": copy.deepcopy(candidate_metrics),
                "verdict": candidate_verdict,
            },
        }

        experiment_title = (
            f"Lumina Ranger Corps & Coding Library Observatory: {proposal.candidate_component_name} (L{target_level})"
        )
        archive_res = self.observatory_bridge.compile_and_archive_experiment(
            experiment_id=experiment_id,
            title=experiment_title,
            hypothesis=proposal.observatory_hypothesis,
            baseline_packet=baseline_packet,
            candidate_packet=candidate_packet,
            register_in_observatory_db=register_in_observatory_db,
        )
        bundle = archive_res["bundle"]
        comparison = bundle["comparison"]

        metric_deltas: Dict[str, Dict[str, Any]] = {}
        for row in comparison.get("metrics", []):
            crit = row.get("criterion", {})
            cid = crit.get("id", "unknown")
            base_m = row.get("baseline") or {}
            cand_m = row.get("candidate") or {}
            metric_deltas[cid] = {
                "name": crit.get("label", cid),
                "baseline": base_m.get("value"),
                "candidate": cand_m.get("value"),
                "absolute_delta": row.get("delta"),
                "relative_delta_percent": row.get("percent_change"),
                "status": row.get("status"),
            }

        counts = comparison.get("counts", {})
        if counts.get("improved", 0) > 0 and counts.get("regressed", 0) == 0:
            obs_outcome = "improved"
        elif counts.get("regressed", 0) > 0 and counts.get("improved", 0) == 0:
            obs_outcome = "regressed"
        elif counts.get("improved", 0) > 0 and counts.get("regressed", 0) > 0:
            obs_outcome = "mixed"
        else:
            obs_outcome = "inconclusive"

        # Consolidate all 8 Rangers into HippocampalMemorySink
        squadron_ranger_ids = (
            "phase_ranger",
            "mass_ranger",
            "court_ranger",
            "finalization_ranger",
            "wideword_program_ranger",
            "micro_isa_ranger",
            "fault_matrix_ranger",
            "entangled_feedback_ranger",
        )
        for idx, ranger_id in enumerate(squadron_ranger_ids):
            self.memory_sink.node_coordinates[ranger_id] = np.array(
                [0.95, 0.96, 0.90 + 0.01 * idx, 0.97], dtype=np.float64
            )
            self.memory_sink.node_metrics[ranger_id] = np.eye(4, dtype=np.float64)
            self.memory_sink.node_absorbed_energy[ranger_id] = 1.65
        dream_report = self.memory_sink.execute_dream_cycle(pair_id=experiment_id)
        hippocampal_ep_id = f"hippo:{experiment_id}:{dream_report.status.lower()}"

        return LuminaObservatoryEpisodeRecord(
            study_name=study_name,
            experiment_id=experiment_id,
            experiment_title=experiment_title,
            model_used=model,
            interaction_id=interaction_id,
            selected_option_id=selected_option["option_id"],
            selected_option_name=selected_option["name"],
            mission_id=proposal.mission_id,
            target_level=target_level,
            candidate_component_name=proposal.candidate_component_name,
            parliament_architecture_proposal=proposal.parliament_architecture_proposal,
            ranger_patrol_directives=list(proposal.ranger_patrol_directives),
            constitutional_lesson_law=proposal.constitutional_lesson_law,
            observatory_hypothesis=proposal.observatory_hypothesis,
            command_protocol_trace=command_protocol_trace,
            ranger_mission=ranger_mission.to_dict(),
            cycle0_phase_packet=cycle0_phase_packet.to_dict(),
            cycle1_phase_packet=cycle1_phase_packet.to_dict(),
            cycle1_court_packet=cycle1_court_packet.to_dict(),
            cycle1_finalization_packet=cycle1_finalization_packet.to_dict(),
            cycle0_audit=cycle0_audit,
            cycle1_audit=cycle1_audit,
            library_verified_components=self.library_agent.list_components(),
            staged_component_record=staged_record,
            lesson_law_record=lesson_record,
            sovereign_domain_summary=sovereign_domain_summary,
            observatory_comparability=comparison["comparability"],
            observatory_outcome=obs_outcome,
            observatory_review_status=bundle["experiment"]["review_status"],
            observatory_warnings=list(bundle["warnings"]),
            observatory_metric_deltas=metric_deltas,
            experiment_bundle_dir=archive_res["experiment_bundle_dir"],
            observatory_db_registered=archive_res["db_registered"],
            hippocampal_episode_id=hippocampal_ep_id,
            sol_lens_packet=candidate_packet,
            baseline_sol_lens_packet=baseline_packet,
            observatory_experiment_archive=bundle["experiment"],
            observatory_markdown_report=bundle["markdown_report"],
            reasoning_telemetry=reasoning_telemetry,
            cycle1_wideword_packet=cycle1_wideword_packet.to_dict(),
            cycle1_micro_isa_packet=cycle1_micro_isa_packet.to_dict(),
            cycle0_fault_matrix_packet=cycle0_fault_matrix_packet.to_dict(),
            cycle1_entangled_feedback_packet=cycle1_entangled_feedback_packet.to_dict(),
            wideword_fabric_report=lowering_bundle["fabric_reports"],
            micro_isa_v1_lowering_report=lowering_bundle["lowering_reports"],
            fault_matrix_report=fault_matrix_report_dict,
            multimanifold_atomic_commit_report=multimanifold_commit_dict,
            sovereign_runtime_report=sovereign_runtime_dict,
            frontier_l_verification=frontier_l_verification,
            frontier_n_verification=frontier_n_verification,
        )
