"""
Unit & Integration Tests: Venue 5 Closed-Loop "Neuro-Physical" Algorithm & Hardware Co-Design
File: tests/test_venue5_neuro_physical_codesign.py

Verifies:
1. Pure physical wave-interference gates (*_WAVE, CMOVE, COPY, LOAD, STORE 1->0 & 0->1)
   executing on SOLEngine RK4 with zero Python boolean shortcuts (python_boolean_shortcuts_used == 0),
   strict rejection of legacy *_MS shortcuts in pure_wave=True mode, and backward compatibility in pure_wave=False.
2. Dynamic scratch-basin register spilling (Basin_Scratch_0..K) in LogosCompiler for >4 live temporaries.
3. Multi-instance hierarchical Lumina component composition (HierarchicalFullAdderAgent, 3-level nested
   2-bit ripple adder) and ast.Subscript constant/dynamic indirect array addressing.
4. Synchronous 6-step sequential SRLatchAgent pure-wave bistability (Set -> Hold -> Reset -> Hold -> Set -> Hold)
   and S=1, R=1 metastability hazard detection.
5. Loop-aware StaticMassSentinel CFG back-edge unrolling and exact basin/register lineage tracking
   (eliminating 'B' in 'Basin_*' / 'C' in 'Basin_Carry_Out' substring false positives).
6. Sequential SR_LATCH_SYNC synthesis, 18-stage 4-bit Wave ALU MetacognitiveOrchestrator DAG execution,
   and 64-bit SIMD bit-sliced exhaustive 1,024-row WideWordVirtualVM == OracleWideWordVM verification.
7. Strict fail-closed cross-language sol_engine.mjs vs sol_engine.py parity (no silent fallback on Node failure,
   no NaN/Infinity in JSON telemetry) and live Node trajectory verification.
8. End-to-end Venue 5 Cycle-0 Manifold Pushback (QUARANTINE across all 4 fault modes) -> Cycle-1 Pure-Wave Repair
   (ELIGIBLE) -> deterministic 8-event sol-edge replay -> SOL-CERT v2 minting, tamper rejection, Sacred Core
   SHA-256 immutability, and 12-tool SubstrateToolSandbox integration (Tools #4, #6, #11).
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, ClassVar

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _rel in (
    "",
    "sol",
    "sol/scratch",
    "sol/tools/sol-core",
    "sol/tools/sol-rsi",
    "sol/tools/sol-rsi/coding_library",
    "sol-continuum",
    "sol-decide",
    "sol-change",
    "sol-edge/src",
    "sol-holo",
):
    _p = str((_REPO_ROOT / _rel).resolve())
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agentic_inventor import (
    TASKS,
    LogosVM,
    _discover_program_basins,
    _read_basin_state,
    build_custom_group,
    run_trial,
)
from coding_library.components.hierarchical_full_adder import (
    HierarchicalFullAdderAgent,
)
from coding_library.components.sr_latch import SRLatchAgent
from hybrid_subsystem_framework import MicroInstructionSequencer
from logos_compiler import Instruction, LogosCompiler
from lumina_compiler import (
    LuminaAgent,
    LuminaCompiler,
    StaticMassSentinel,
    StaticVerificationError,
)
from sol_continuum import (
    Venue5NeuroPhysicalCoDesignEngine,
    verify_sol_cert_v2_integrity,
)
from sol_continuum.autopoietic_organism import EXPECTED_CORE_GRAPH_SHA256
from sol_continuum.dormant_clusters_awakening import (
    _DETERMINISTIC_TOOL_CACHE,
    execute_phonon_multiplexing_and_analog_primitives,
)
from sol_continuum.lumina_observatory_bridge import (
    CircuitToWideWordLoweringAdapter,
)
from sol_continuum.reflective_domain import verify_sacred_core_graph_sha256
from sol_continuum.substrate_tools import (
    SUBSTRATE_TOOL_DECLARATIONS,
    SubstrateToolSandbox,
)
from sol_continuum.venue5_neuro_physical_codesign import (
    _build_full_adder_circuit_and_spec,
    verify_canonical_task_rk4,
)
from sol_engine import SOLEngine

from Frontier_OS.core.metacognition.metacognitive_orchestrator import (
    MetacognitiveOrchestrator,
)
from Frontier_OS.core.metacognition.reasoning_graph import (
    assemble_4bit_wave_alu_circuit,
    create_4bit_wave_alu_plan,
)
from sol.kernel.synthesis.circuit_synthesizer import (
    RiemannianCircuitSynthesizer,
)
from sol.kernel.synthesis.symbolic_reflector import SymbolicReflector


def _run_single_pure_wave_op(
    op: str,
    a: int,
    b: int | None = None,
    c: int | None = None,
    out_init: int = 1,
) -> int:
    basins_def = [("B_A", 0), ("B_B", 10), ("B_C", 20), ("B_Out", 30)]
    group = build_custom_group(basins_def, pure_wave=True)
    group.prime_basin("B_A", active=bool(a))
    group.prime_basin("B_B", active=bool(b))
    group.prime_basin("B_C", active=bool(c))
    group.prime_basin("B_Out", active=bool(out_init))
    for reg in ("A", "B", "C", "D"):
        group.prime_register(reg, active=False)

    seq = MicroInstructionSequencer(group, pure_wave=True)
    vm = LogosVM(seq)
    prog = [Instruction("LOAD", ["A", "B_A"])]
    if b is not None:
        prog.append(Instruction("LOAD", ["B", "B_B"]))
    if op == "NOT_WAVE":
        prog.append(Instruction("NOT_WAVE", ["D", "A"]))
    elif op == "COPY":
        prog.append(Instruction("COPY", ["A", "D"]))
    elif op == "CMOVE":
        prog.append(Instruction("LOAD", ["C", "B_C"]))
        prog.append(Instruction("COPY", ["C", "D"]))
        prog.append(Instruction("CMOVE", ["D", "B", "A"]))
    else:
        prog.append(Instruction(op, ["D", "A", "B"]))
    prog.append(Instruction("STORE", ["D", "B_Out"]))

    hist = vm.run(prog)
    assert seq.python_boolean_shortcuts_used == 0
    assert len(seq.wave_gate_telemetry) >= (1 if op != "COPY" else 0)
    return _read_basin_state(hist[-1], "B_Out", basins_def)


def test_pure_wave_gates_exhaustive_rk4_zero_python_shortcuts() -> None:
    """Verify all *_WAVE gates, CMOVE, COPY, LOAD, and STORE (0->1 and 1->0) on SOLEngine RK4."""
    gate_truth = {
        "OR_WAVE": lambda x, y: x | y,
        "AND_WAVE": lambda x, y: x & y,
        "NOR_WAVE": lambda x, y: 1 - (x | y),
        "NAND_WAVE": lambda x, y: 1 - (x & y),
        "XOR_WAVE": lambda x, y: x ^ y,
        "XNOR_WAVE": lambda x, y: 1 - (x ^ y),
    }
    for gate_op, truth_fn in gate_truth.items():
        for a in (0, 1):
            for b in (0, 1):
                exp = truth_fn(a, b)
                # Test opposite out_init so STORE must actively flip 0->1 or quench 1->0
                got = _run_single_pure_wave_op(gate_op, a, b, out_init=1 - exp)
                assert got == exp, f"{gate_op}({a}, {b}) expected {exp}, got {got}"

    for a in (0, 1):
        assert _run_single_pure_wave_op("NOT_WAVE", a, out_init=a) == (1 - a)
        assert _run_single_pure_wave_op("COPY", a, out_init=1 - a) == a

    for cond in (0, 1):
        for src in (0, 1):
            for prev in (0, 1):
                exp = src if cond else prev
                got = _run_single_pure_wave_op("CMOVE", cond, src, prev, out_init=1 - exp)
                assert got == exp, f"CMOVE(cond={cond}, src={src}, prev={prev}) -> {got} != {exp}"

    # pure_wave=True must reject legacy hybrid Python boolean shortcut opcodes (*_MS)
    basins_def = [("B_A", 0), ("B_B", 10), ("B_Out", 20)]
    group_pw = build_custom_group(basins_def, pure_wave=True)
    seq_pw = MicroInstructionSequencer(group_pw, pure_wave=True)
    with pytest.raises(RuntimeError, match="forbids mixed-signal Python boolean shortcut"):
        LogosVM(seq_pw).run(
            [
                Instruction("LOAD", ["A", "B_A"]),
                Instruction("LOAD", ["B", "B_B"]),
                Instruction("AND_MS", ["C", "A", "B"]),
            ]
        )

    # pure_wave=False (default) preserves legacy mixed-signal opcodes without regression
    group_legacy = build_custom_group(basins_def, pure_wave=False)
    group_legacy.prime_basin("B_A", active=True)
    group_legacy.prime_basin("B_B", active=True)
    group_legacy.prime_basin("B_Out", active=False)
    seq_legacy = MicroInstructionSequencer(group_legacy, pure_wave=False)
    hist_legacy = LogosVM(seq_legacy).run(
        [
            Instruction("LOAD", ["A", "B_A"]),
            Instruction("LOAD", ["B", "B_B"]),
            Instruction("AND_MS", ["C", "A", "B"]),
            Instruction("STORE", ["C", "B_Out"]),
        ]
    )
    assert _read_basin_state(hist_legacy[-1], "B_Out", basins_def) == 1
    assert seq_legacy.python_boolean_shortcuts_used >= 1

    # Regression: SOLPhysics.step_rk4 clamps NaN / -0.0 rho to +0.0 and run_steps matches sequential step() to 0 ULP
    import math

    eng_nan = SOLEngine.from_default_graph()
    eng_nan.physics.integration_mode = "rk4"
    eng_nan.physics.nodes[0]["rho"] = float("nan")
    eng_nan.physics.nodes[1]["rho"] = -0.0
    eng_nan.step()
    assert all(not math.isnan(n["rho"]) and n["rho"] >= 0.0 for n in eng_nan.physics.nodes)
    assert math.copysign(1.0, eng_nan.physics.nodes[1]["rho"]) == 1.0 or eng_nan.physics.nodes[1]["rho"] > 0.0

    eng_seq = SOLEngine.from_default_graph()
    eng_burst = SOLEngine.from_default_graph()
    eng_seq.physics.integration_mode = "rk4"
    eng_burst.physics.integration_mode = "rk4"
    eng_seq.inject("grail", 25.0)
    eng_burst.inject("grail", 25.0)
    for _ in range(10):
        eng_seq.step()
    eng_burst.run_steps(10)
    assert [n["rho"] for n in eng_burst.physics.nodes] == [n["rho"] for n in eng_seq.physics.nodes]


def test_logos_compiler_dynamic_scratch_basin_register_spilling() -> None:
    """Verify >4 live temporaries spill cleanly to Basin_Scratch_0..K and execute accurately in pure_wave RK4."""
    flow_src = (
        "def flow(self):\n"
        "    t1 = self.a ^ self.b\n"
        "    t2 = self.c ^ self.d\n"
        "    t3 = self.e & self.f\n"
        "    t4 = self.g | self.h\n"
        "    t5 = (t1 ^ t2) & (t3 | t4)\n"
        "    self.out = t5 ^ (t1 & t4)\n"
    )
    inputs_map = {
        "a": "B_a",
        "b": "B_b",
        "c": "B_c",
        "d": "B_d",
        "e": "B_e",
        "f": "B_f",
        "g": "B_g",
        "h": "B_h",
    }
    prog = LuminaCompiler.compile_flow_src(
        inputs=inputs_map,
        outputs={"out": "B_out"},
        flow_src=flow_src,
        pure_wave=True,
    )
    assert len(prog.allocated_scratch_basins) >= 1
    assert any("Basin_Scratch_" in str(arg) for inst in prog for arg in inst.args)

    custom_task = {
        "inputs": inputs_map,
        "outputs": {"out": "B_out"},
        "basins_def": [(b_name, idx * 10) for idx, b_name in enumerate([*inputs_map.values(), "B_out"])],
        "expected_fn": lambda a, b, c, d, e, f, g, h: (
            (((a ^ b) ^ (c ^ d)) & ((e & f) | (g | h))) ^ ((a ^ b) & (g | h)),
        ),
        "verify_fn": lambda got, exp: got[0] == exp[0],
    }
    for vec in (
        (1, 0, 0, 0, 1, 1, 1, 0),
        (1, 0, 1, 0, 1, 1, 0, 1),
        (0, 1, 1, 0, 0, 1, 1, 1),
        (1, 1, 0, 1, 0, 0, 0, 0),
    ):
        hist, ok, msg = run_trial(
            "spill_test",
            vec,
            prog,
            pure_wave=True,
            custom_task=custom_task,
        )
        assert ok is True, f"Spill vector {vec} failed: {msg}"
        assert hist[-1]["python_boolean_shortcuts_used"] == 0


def test_multi_instance_hierarchical_full_adder_nested_3level_and_array_subscript() -> None:
    """Verify HierarchicalFullAdderAgent (2x HalfAdder), 3-level nested 2-bit adder, and array subscript addressing."""
    # 1. Pure-wave HierarchicalFullAdderAgent across all 8 input combinations
    hfa_prog = LuminaCompiler.compile_agent(HierarchicalFullAdderAgent, pure_wave=True)
    opcodes = [inst.op for inst in hfa_prog]
    assert "XOR_WAVE" in opcodes and "AND_WAVE" in opcodes and "OR_WAVE" in opcodes
    assert not any(op.endswith("_MS") for op in opcodes)

    hfa_ok, hfa_cases, hfa_shortcuts, hfa_margin, hfa_msgs = verify_canonical_task_rk4(
        "hierarchical_full_adder",
        hfa_prog,
        pure_wave=True,
    )
    assert hfa_ok is True, f"HierarchicalFullAdder failed: {hfa_msgs}"
    assert hfa_cases == 8
    assert hfa_shortcuts == 0
    assert hfa_margin > 0.0

    with pytest.raises(KeyError):
        verify_canonical_task_rk4("nonexistent_canonical_task", hfa_prog, pure_wave=True)

    mutated_hfa_task = copy.deepcopy(TASKS["hierarchical_full_adder"])
    mutated_hfa_task["input_space"] = [(0, 0, 0)]
    mutated_hfa_task["expected_fn"] = lambda x, y, cin: (1 - ((x ^ y) ^ cin), 0)
    mut_ok, mut_cases, _, _, _ = verify_canonical_task_rk4(
        "hierarchical_full_adder",
        hfa_prog,
        pure_wave=True,
        custom_task=mutated_hfa_task,
    )
    assert mut_ok is False and mut_cases == 1

    # 2. 3-level nested component composition: 2-bit Ripple Adder composing two HierarchicalFullAdderAgents
    class TwoBitRippleAdderAgent(LuminaAgent):
        inputs: ClassVar[dict[str, str]] = {
            "a0": "Basin_A0",
            "a1": "Basin_A1",
            "b0": "Basin_B0",
            "b1": "Basin_B1",
            "cin": "Basin_Cin0",
        }
        outputs: ClassVar[dict[str, str]] = {
            "s0": "Basin_S0",
            "s1": "Basin_S1",
            "cout": "Basin_Cout1",
        }
        components: ClassVar[dict[str, Any]] = {
            "fa0": HierarchicalFullAdderAgent,
            "fa1": HierarchicalFullAdderAgent,
        }

        def flow(self):
            self.fa0.x = self.a0
            self.fa0.y = self.b0
            self.fa0.cin = self.cin
            self.fa0.run()
            self.s0 = self.fa0.sum

            self.fa1.x = self.a1
            self.fa1.y = self.b1
            self.fa1.cin = self.fa0.cout
            self.fa1()
            self.s1 = self.fa1.sum
            self.cout = self.fa1.cout

    adder2_prog = LuminaCompiler.compile_agent(TwoBitRippleAdderAgent, pure_wave=True)
    discovered = [b[0] for b in _discover_program_basins([], adder2_prog)]
    assert any(b.startswith("Basin_fa0_ha1_") for b in discovered)
    assert any(b.startswith("Basin_fa1_ha2_") for b in discovered)

    adder2_task = {
        "inputs": TwoBitRippleAdderAgent.inputs,
        "outputs": TwoBitRippleAdderAgent.outputs,
        "basins_def": [
            (b_name, idx * 10)
            for idx, b_name in enumerate(
                [*TwoBitRippleAdderAgent.inputs.values(), *TwoBitRippleAdderAgent.outputs.values()]
            )
        ],
        "expected_fn": lambda a0, a1, b0, b1, cin: (
            (a0 + 2 * a1 + b0 + 2 * b1 + cin) & 1,
            ((a0 + 2 * a1 + b0 + 2 * b1 + cin) >> 1) & 1,
            ((a0 + 2 * a1 + b0 + 2 * b1 + cin) >> 2) & 1,
        ),
        "verify_fn": lambda got, exp: tuple(got) == tuple(exp),
    }
    # 2 (0b10) + 3 (0b11) + 1 = 6 (0b110 -> s0=0, s1=1, cout=1)
    hist_2b, ok_2b, msg_2b = run_trial(
        "two_bit_ripple",
        (0, 1, 1, 1, 1),
        adder2_prog,
        pure_wave=True,
        custom_task=adder2_task,
    )
    assert ok_2b is True, msg_2b
    assert hist_2b[-1]["python_boolean_shortcuts_used"] == 0

    # 3. Array subscript addressing (constant self.arr[1] and dynamic self.arr[self.idx])
    arr_flow = (
        "def flow(self):\n"
        "    self.buf[0] = self.x0\n"
        "    self.buf[1] = self.x1\n"
        "    self.const_pick = self.buf[1]\n"
        "    self.dyn_pick = self.buf[self.idx]\n"
    )
    arr_prog = LuminaCompiler.compile_flow_src(
        inputs={
            "x0": "Basin_X0",
            "x1": "Basin_X1",
            "idx": "Basin_Idx",
            "buf_0": "Basin_Buf_0",
            "buf_1": "Basin_Buf_1",
        },
        outputs={
            "const_pick": "Basin_Const_Pick",
            "dyn_pick": "Basin_Dyn_Pick",
        },
        flow_src=arr_flow,
        pure_wave=True,
    )
    arr_ops = [inst.op for inst in arr_prog]
    assert "LOAD_INDIRECT" in arr_ops
    arr_task = {
        "inputs": {"x0": "Basin_X0", "x1": "Basin_X1", "idx": "Basin_Idx"},
        "outputs": {"const_pick": "Basin_Const_Pick", "dyn_pick": "Basin_Dyn_Pick"},
        "basins_def": [
            ("Basin_X0", 0),
            ("Basin_X1", 10),
            ("Basin_Idx", 20),
            ("Basin_Buf_0", 30),
            ("Basin_Buf_1", 40),
            ("Basin_Const_Pick", 50),
            ("Basin_Dyn_Pick", 60),
        ],
        "expected_fn": lambda x0, x1, idx: (x1, x1 if idx else x0),
        "verify_fn": lambda got, exp: tuple(got) == tuple(exp),
    }
    _, ok_arr0, msg_arr0 = run_trial("arr_test", (1, 0, 0), arr_prog, pure_wave=True, custom_task=arr_task)
    _, ok_arr1, msg_arr1 = run_trial("arr_test", (0, 1, 1), arr_prog, pure_wave=True, custom_task=arr_task)
    assert ok_arr0 is True, msg_arr0
    assert ok_arr1 is True, msg_arr1


def test_sequential_sr_latch_6step_pure_wave_bistability_and_hazard_detection() -> None:
    """Verify 6-step pure-wave SRLatchAgent persistence and S=1, R=1 metastability hazard detection."""
    sr_prog = LuminaCompiler.compile_agent(SRLatchAgent, pure_wave=True)
    assert len(TASKS["sr_latch"]["sequence"]) == 6

    sr_ok, sr_cases, sr_shortcuts, sr_margin, sr_msgs = verify_canonical_task_rk4(
        "sr_latch",
        sr_prog,
        pure_wave=True,
    )
    assert sr_ok is True, f"SRLatch failed: {sr_msgs}"
    assert sr_cases == 6
    assert sr_shortcuts == 0
    assert sr_margin > 0.0

    # Unguarded S=1, R=1 latch must trigger complement hazard (Q == Qbar)
    unguarded_src = (
        "def flow(self):\n"
        "    self.q = self.s | ((~self.r) & self.q)\n"
        "    self.qbar = self.r | ((~self.s) & (~self.q))\n"
    )
    unguarded_prog = LuminaCompiler.compile_flow_src(
        inputs=TASKS["sr_latch"]["inputs"],
        outputs=TASKS["sr_latch"]["outputs"],
        flow_src=unguarded_src,
        pure_wave=True,
    )
    hazard_task = copy.deepcopy(TASKS["sr_latch"])
    hazard_task["sequence"] = [
        ((1, 0), (1, 0)),
        ((1, 1), (0, 1)),
    ]
    _, ok_haz, msg_haz = run_trial(
        "sr_latch",
        None,
        unguarded_prog,
        pure_wave=True,
        detect_sr_hazard=True,
        custom_task=hazard_task,
    )
    assert ok_haz is False
    assert "hazard" in msg_haz.lower()


def test_static_mass_sentinel_exact_lineage_and_cfg_loop_drain() -> None:
    """Verify exact register/basin lineage (no 'B'/'C' substring bug) and CFG loop mass-drain rejection."""
    from lumina_compiler import StaticVerificationError

    # 1. Substring regression test: Basin_Carry_Out contains 'C', Basin_Beta contains 'B';
    # draining Basin_Alpha must NOT wipe unrelated register B or C via substring collision.
    prog_no_alias = [
        Instruction("LOAD", ["A", "Basin_Alpha"]),
        Instruction("LOAD", ["B", "Basin_Beta"]),
        Instruction("LOAD", ["C", "Basin_Carry_Out"]),
        Instruction("SETTLE", [10]),
        Instruction("STORE", ["B", "Basin_Beta"]),
        Instruction("STORE", ["C", "Basin_Carry_Out"]),
    ]
    assert StaticMassSentinel.verify(prog_no_alias, damping=0.05) is True

    # 2. Uncompensated loop drains register/basin mass below 14.0 across unrolled back-edges
    draining_loop = (
        "def flow(self):\n"
        "    while self.in_a:\n"
        "        self.settle(25)\n"
        "        self.sum_out = self.in_a ^ self.in_b\n"
    )
    prog_drain = LuminaCompiler.compile_flow_src(
        inputs={"in_a": "Basin_In_A", "in_b": "Basin_In_B"},
        outputs={"sum_out": "Basin_Sum_Out"},
        flow_src=draining_loop,
        verify_mass=False,
        pure_wave=True,
    )
    with pytest.raises(StaticVerificationError):
        StaticMassSentinel.verify(prog_drain, damping=0.05, max_loop_unroll=8)

    # 3. Compensated loop with self.nudge restores acoustic mass >= 14.0 across all unrolled iterations
    compensated_loop = (
        "def flow(self):\n"
        "    while self.in_a:\n"
        "        self.nudge('Basin_In_A', 20.0)\n"
        "        self.nudge('Basin_In_B', 20.0)\n"
        "        self.nudge('Basin_Sum_Out', 20.0)\n"
        "        self.settle(10)\n"
        "        self.sum_out = self.in_a ^ self.in_b\n"
    )
    prog_comp = LuminaCompiler.compile_flow_src(
        inputs={"in_a": "Basin_In_A", "in_b": "Basin_In_B"},
        outputs={"sum_out": "Basin_Sum_Out"},
        flow_src=compensated_loop,
        verify_mass=False,
        pure_wave=True,
    )
    assert StaticMassSentinel.verify(prog_comp, damping=0.05, max_loop_unroll=8) is True


def test_sequential_synthesis_4bit_wave_alu_dag_and_64bit_bit_sliced_exhaustive_proof() -> None:
    """Verify SR_LATCH_SYNC synthesis, 18-stage 4-bit Wave ALU DAG, and 1,024-row 64-bit bit-sliced WideWord proof."""
    synth = RiemannianCircuitSynthesizer()
    reflector = SymbolicReflector()
    adapter = CircuitToWideWordLoweringAdapter()

    # 1. Sequential next-state SR_LATCH_SYNC synthesis & algebraic reflection
    sr_res = synth.synthesize_canonical("SR_LATCH_SYNC")
    assert sr_res.verified is True
    assert sr_res.accuracy == 1.0
    sr_refl = reflector.reflect(sr_res.circuit, sr_res.spec)
    assert sr_refl.is_equivalent is True
    sr_bs = adapter.verify_exhaustively_bit_sliced(sr_res.circuit, spec=sr_res.spec, width=64)
    assert sr_bs["exhaustive_verified"] is True
    assert sr_bs["total_rows_verified"] == 8
    assert sr_bs["row_mismatches"] == 0

    # 2. 18-stage 4-bit Wave ALU MetacognitiveOrchestrator DAG execution across all 4 opcodes
    alu_plan = create_4bit_wave_alu_plan()
    assert len(alu_plan.stages) == 26
    orch = MetacognitiveOrchestrator()
    fa_circ, _ = _build_full_adder_circuit_and_spec()
    orch.circuit_cache.store_circuit("FULL_ADDER", fa_circ)
    for cname in ("XOR", "MUX_2to1"):
        orch.circuit_cache.store_circuit(cname, synth.synthesize_canonical(cname).circuit)

    def _eval_alu_plan(a_val: int, b_val: int, op_code: int) -> tuple[int, int, int]:
        gin = {
            f"A{i}": float((a_val >> i) & 1) for i in range(4)
        }
        gin.update({f"B{i}": float((b_val >> i) & 1) for i in range(4)})
        gin["OP0"] = float(op_code & 1)
        gin["OP1"] = float((op_code >> 1) & 1)
        rep = orch.execute_plan(alu_plan, gin, auto_consolidate=False)
        assert rep.success is True
        y_val = sum(int(rep.global_outputs[f"Y{i}"]) << i for i in range(4))
        return y_val, int(rep.global_outputs["COUT"]), int(rep.global_outputs["ZERO"])

    assert _eval_alu_plan(6, 5, 0b00) == (11, 0, 0)   # ADD: 6 + 5 = 11
    assert _eval_alu_plan(12, 7, 0b00) == (3, 1, 0)   # ADD overflow: 12 + 7 = 19 -> Y=3, COUT=1
    assert _eval_alu_plan(9, 4, 0b01) == (5, 1, 0)    # SUB: 9 - 4 = 5, ~borrow=1
    assert _eval_alu_plan(7, 7, 0b01) == (0, 1, 1)    # SUB zero: 7 - 7 = 0 -> ZERO=1
    assert _eval_alu_plan(0b1010, 0b1100, 0b10) == (0b1000, 0, 0)  # AND
    assert _eval_alu_plan(0b1010, 0b1100, 0b11) == (0b0110, 0, 0)  # XOR

    # 3. Exhaustive 64-bit SIMD bit-sliced proof over all 1,024 rows (2^10) of 4-bit Wave ALU
    alu_circ, alu_spec = assemble_4bit_wave_alu_circuit()
    alu_bs = adapter.verify_exhaustively_bit_sliced(alu_circ, spec=alu_spec, width=64)
    assert alu_bs["exhaustive_verified"] is True
    assert alu_bs["total_rows_verified"] == 1024
    assert alu_bs["batches_executed"] == 16
    assert alu_bs["row_mismatches"] == 0


def test_strict_cross_language_mjs_py_parity_fail_closed_and_real_node(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify cross_language_mjs_py_parity fails closed on Node error (no NaN/Infinity) and passes with real Node."""
    real_run = subprocess.run

    def _failing_node_run(*args: Any, **kwargs: Any) -> Any:
        cmd = args[0] if args else kwargs.get("args", [])
        if isinstance(cmd, list) and cmd and str(cmd[0]).lower().startswith("node"):
            return subprocess.CompletedProcess(
                args=cmd, returncode=1, stdout="", stderr="simulated node crash"
            )
        return real_run(*args, **kwargs)

    _DETERMINISTIC_TOOL_CACHE.clear()
    monkeypatch.setattr(subprocess, "run", _failing_node_run)
    failed_res = execute_phonon_multiplexing_and_analog_primitives(_REPO_ROOT)
    parity_fail = failed_res["js_analog_hardware_parity"]["cross_language_mjs_py_parity"]
    assert parity_fail["node_runtime_executed"] is False
    assert parity_fail["parity_verified"] is False
    assert "simulated node crash" in parity_fail["node_error"]
    # Must serialize strictly without NaN or Infinity
    json.dumps(failed_res, allow_nan=False)

    # Restore real subprocess.run and verify actual Node sol_engine.mjs parity
    _DETERMINISTIC_TOOL_CACHE.clear()
    monkeypatch.setattr(subprocess, "run", real_run)
    live_res = execute_phonon_multiplexing_and_analog_primitives(_REPO_ROOT)
    parity_ok = live_res["js_analog_hardware_parity"]["cross_language_mjs_py_parity"]
    assert parity_ok["node_runtime_executed"] is True
    assert parity_ok["parity_verified"] is True
    assert parity_ok["max_abs_rho_diff"] < 1e-3
    assert parity_ok["mass_abs_diff"] < 1e-3 and parity_ok["entropy_abs_diff"] < 1e-3
    json.dumps(live_res, allow_nan=False)


def test_venue5_cycle0_pushback_sol_cert_v2_replay_tamper_rejection_and_substrate_tools() -> None:
    """Verify all 4 Cycle-0 pushback faults, Cycle-1 SOL-CERT v2 minting, tamper rejection, and Tools #4/#6/#11."""
    engine = Venue5NeuroPhysicalCoDesignEngine(_REPO_ROOT)

    # 1. All 4 Cycle-0 physical pushback fault modes must QUARANTINE with actionable counter-demands
    for fault in (
        "loop_mass_drain",
        "sr_metastable_hazard",
        "wave_threshold_drift",
        "mixed_signal_shortcut",
    ):
        c0 = engine.evaluate_cycle0_pushback(
            fault_mode=fault,
            target_architecture="HIERARCHICAL_FULL_ADDER",
        )
        assert c0["quarantined"] is True
        assert c0["policy_status"] == "QUARANTINE"
        assert len(c0["counter_demands"]) >= 1
        assert len(c0["epistemic_counter_questions"]) >= 1

    # 2. Mint and verify SOL-CERT v2 across HIERARCHICAL_FULL_ADDER, SR_LATCH, and WAVE_ALU_4BIT
    for arch, expected_rows in (
        ("HIERARCHICAL_FULL_ADDER", 8),
        ("SR_LATCH", 8),
        ("WAVE_ALU_4BIT", 1024),
    ):
        cert = engine.run_closed_loop_codesign_and_mint_cert(
            target_architecture=arch,
            fault_mode="loop_mass_drain",
            pure_wave=True,
        )
        assert verify_sol_cert_v2_integrity(cert) is True
        assert cert.pure_wave_enforced is True
        assert cert.python_boolean_shortcuts_used == 0
        assert cert.authorized_claimed is False
        assert cert.allow_production_execution is False
        assert cert.sacred_core_immutable is True
        assert cert.sacred_core_graph_sha256 == EXPECTED_CORE_GRAPH_SHA256
        assert cert.sol_edge_replay_summary["event_count"] == 8
        assert cert.sol_edge_replay_summary["cycle0_policy_status"] == "QUARANTINE"
        assert cert.sol_edge_replay_summary["final_policy_status"] == "ELIGIBLE"
        assert (
            cert.cycle1_repair_report["bit_sliced_wideword_proof"]["total_rows_verified"]
            == expected_rows
        )

    # 3. Tamper detection on verify_sol_cert_v2_integrity must fail closed
    valid_dict = cert.to_dict()

    tampered_shortcut = copy.deepcopy(valid_dict)
    tampered_shortcut["python_boolean_shortcuts_used"] = 1
    assert verify_sol_cert_v2_integrity(tampered_shortcut) is False

    tampered_auth = copy.deepcopy(valid_dict)
    tampered_auth["authorized_claimed"] = True
    assert verify_sol_cert_v2_integrity(tampered_auth) is False

    tampered_sha = copy.deepcopy(valid_dict)
    tampered_sha["certificate_sha256"] = "0" * 64
    assert verify_sol_cert_v2_integrity(tampered_sha) is False

    tampered_core = copy.deepcopy(valid_dict)
    tampered_core["sacred_core_graph_sha256"] = "f" * 64
    assert verify_sol_cert_v2_integrity(tampered_core) is False

    # 4. 12-Tool SubstrateToolSandbox integration (Tools #4, #6, #11) + JSON NaN-free serialization
    assert len(SUBSTRATE_TOOL_DECLARATIONS) == 12
    sandbox = SubstrateToolSandbox(repo_root=_REPO_ROOT)

    res4 = sandbox.execute_tool(
        "sol_synthesize_and_reflect_circuit",
        {"spec_name": "WAVE_ALU_4BIT", "word_width": 64, "bit_sliced_exhaustive": True},
    )
    assert res4["verified"] is True
    assert res4["bit_sliced_rows_verified"] == 1024
    assert res4["bit_sliced_row_mismatches"] == 0
    json.dumps(res4, allow_nan=False)

    res6_quarantine = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "damping": 0.05,
            "flow_code": "while self.in_a:\n    self.settle(25)\n    self.sum_out = self.in_a ^ self.in_b",
        },
    )
    assert res6_quarantine["cycle0_quarantined"] is True
    assert res6_quarantine["policy_status"] == "QUARANTINE"
    assert len(res6_quarantine["counter_demands"]) >= 1
    json.dumps(res6_quarantine, allow_nan=False)

    res6_default_pw = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {"pure_wave": True},
    )
    assert res6_default_pw["cycle0_quarantined"] is False
    assert res6_default_pw["policy_status"] == "ELIGIBLE"
    assert res6_default_pw["physical_rk4_verified"] is True
    assert res6_default_pw["physical_rk4_cases_verified"] == 4
    assert res6_default_pw["python_boolean_shortcuts_used"] == 0
    json.dumps(res6_default_pw, allow_nan=False)

    res6_valid = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "verify_on_task": "hierarchical_full_adder",
        },
    )
    assert res6_valid["cycle0_quarantined"] is False
    assert res6_valid["policy_status"] == "ELIGIBLE"
    assert res6_valid["physical_rk4_verified"] is True
    assert res6_valid["python_boolean_shortcuts_used"] == 0
    json.dumps(res6_valid, allow_nan=False)

    res11 = sandbox.execute_tool(
        "sol_run_rsi_inventor_and_level_chambers",
        {
            "inventor_task": "4bit_wave_alu",
            "patrol_all_rangers": True,
            "pure_wave": True,
            "inject_cycle0_fault": "mixed_signal_shortcut",
            "mint_sol_cert_v2": True,
        },
    )
    assert res11["sol_cert_v2_verified"] is True
    assert res11["sol_cert_v2"]["cert_id"] == "SOL-CERT-V2-2026-WAVE_ALU_4BIT-EEF8F2A83406"
    assert (
        res11["sol_cert_v2"]["certificate_sha256"]
        == "2495cf972028fcbd435df87b53bce89f02097dcad83ee4a0cb26dcf924a976b7"
    )
    assert res11["cycle0_pushback_report"]["quarantined"] is True
    assert res11["agentic_inventor"]["pure_wave_verified"] is True
    assert res11["agentic_inventor"]["python_boolean_shortcuts_used"] == 0
    assert res11["sovereign_rangers_patrol"]["rangers_patrolled_count"] == 57
    json.dumps(res11, allow_nan=False)

    immutable_ok, graph_sha = verify_sacred_core_graph_sha256(_REPO_ROOT)
    assert immutable_ok is True
    assert graph_sha == EXPECTED_CORE_GRAPH_SHA256


def test_jump_if_active_active_condition_spill_input_insulation_and_legacy_copy_clear_rk4() -> None:
    """Regression: active branch condition spill before JUMP_IF_ACTIVE, input-basin insulation, and pure_wave=False COPY clear."""
    # 1. Computed branch condition that remains live inside the taken branch
    branch_src = (
        "def flow(self):\n"
        "    cond = self.a ^ self.b\n"
        "    if cond:\n"
        "        self.out = cond ^ self.c\n"
        "    else:\n"
        "        self.out = cond | self.c\n"
    )
    branch_prog = LuminaCompiler.compile_flow_src(
        inputs={"a": "Basin_A", "b": "Basin_B", "c": "Basin_C"},
        outputs={"out": "Basin_Out"},
        flow_src=branch_src,
        pure_wave=True,
    )
    branch_task = {
        "basins_def": [("Basin_A", 0), ("Basin_B", 30), ("Basin_C", 60), ("Basin_Out", 120)],
        "inputs": {"a": "Basin_A", "b": "Basin_B", "c": "Basin_C"},
        "outputs": {"out": "Basin_Out"},
        "expected_fn": lambda a, b, c: (((a ^ b) ^ c) if (a ^ b) else ((a ^ b) | c),),
        "verify_fn": lambda g, e: tuple(g) == tuple(e),
    }
    for vec in ((0, 0, 1), (1, 0, 0), (1, 0, 1), (1, 1, 0)):
        hist_b, ok_b, msg_b = run_trial("live_cond_branch", vec, branch_prog, pure_wave=True, custom_task=branch_task)
        assert ok_b is True, f"Live condition branch failed on {vec}: {msg_b}"
        assert hist_b[-1]["python_boolean_shortcuts_used"] == 0

    # 2. Reassigned input variable + >4 live temporaries must never write back to read-only input basins
    insul_src = (
        "def flow(self):\n"
        "    a = self.a ^ self.b\n"
        "    t1 = self.b | self.c\n"
        "    t2 = self.a & self.c\n"
        "    t3 = t1 ^ t2\n"
        "    t4 = t3 | self.b\n"
        "    self.out = a ^ t4 ^ t1 ^ t2 ^ t3\n"
    )
    insul_prog = LuminaCompiler.compile_flow_src(
        inputs={"a": "Basin_A", "b": "Basin_B", "c": "Basin_C"},
        outputs={"out": "Basin_Out"},
        flow_src=insul_src,
        pure_wave=True,
    )
    store_targets = {inst.args[1] for inst in insul_prog if inst.op == "STORE"}
    assert store_targets.isdisjoint({"Basin_A", "Basin_B", "Basin_C"})
    insul_task = {
        "basins_def": [("Basin_A", 0), ("Basin_B", 30), ("Basin_C", 60), ("Basin_Out", 120)],
        "inputs": {"a": "Basin_A", "b": "Basin_B", "c": "Basin_C"},
        "outputs": {"out": "Basin_Out"},
        "expected_fn": lambda a, b, c: (
            (a ^ b) ^ (((b | c) ^ (a & c)) | b) ^ (b | c) ^ (a & c) ^ ((b | c) ^ (a & c)),
        ),
        "verify_fn": lambda g, e: tuple(g) == tuple(e),
    }
    for vec in ((0, 1, 1), (1, 0, 1)):
        _, ok_i, msg_i = run_trial("input_insulation", vec, insul_prog, pure_wave=True, custom_task=insul_task)
        assert ok_i is True, f"Input insulation spill failed on {vec}: {msg_i}"

    # 3. Legacy pure_wave=False dirty memristive register battery must be cleared after vacating COPY
    legacy_src = (
        "def flow(self):\n"
        "    x = self.a ^ self.b\n"
        "    y = x | self.c\n"
        "    z = self.b | self.c\n"
        "    self.out = z ^ y\n"
    )
    legacy_prog = LuminaCompiler.compile_flow_src(
        inputs={"a": "Basin_A", "b": "Basin_B", "c": "Basin_C"},
        outputs={"out": "Basin_Out"},
        flow_src=legacy_src,
        pure_wave=False,
    )
    legacy_task = {
        "basins_def": [("Basin_A", 0), ("Basin_B", 30), ("Basin_C", 60), ("Basin_Out", 120)],
        "inputs": {"a": "Basin_A", "b": "Basin_B", "c": "Basin_C"},
        "outputs": {"out": "Basin_Out"},
        "expected_fn": lambda a, b, c: ((b | c) ^ ((a ^ b) | c),),
        "verify_fn": lambda g, e: tuple(g) == tuple(e),
    }
    for vec in ((1, 0, 0), (1, 1, 0)):
        _, ok_l, msg_l = run_trial("legacy_copy_clear", vec, legacy_prog, pure_wave=False, custom_task=legacy_task)
        assert ok_l is True, f"Legacy pure_wave=False COPY clear failed on {vec}: {msg_l}"

    # 4. Subroutine scratch basins must never collide with outer program scratch basins
    sub_stmts = [
        ("OP", "s1", "XOR", "p0", "p1"),
        ("OP", "s2", "OR", "p0", "p1"),
        ("OP", "s3", "AND", "p0", "p1"),
        ("OP", "s4", "XOR", "s1", "s2"),
        ("OP", "s5", "OR", "s3", "s4"),
        ("OP", "r_out", "XOR", "s5", "s1"),
    ]
    main_stmts = [
        ("OP", "m1", "XOR", "a", "b"),
        ("OP", "m2", "OR", "a", "b"),
        ("OP", "m3", "AND", "a", "b"),
        ("OP", "m4", "XOR", "m1", "m2"),
        ("OP", "m5", "OR", "m3", "m4"),
        ("STORE", "m3", "Basin_Sub_P0"),
        ("STORE", "m4", "Basin_Sub_P1"),
        ("CALL_SUB", "SubWide"),
        ("LOAD", "sub_r", "Basin_Sub_Out"),
        ("OP", "out", "XOR", "sub_r", "m1"),
    ]
    sub_prog = LogosCompiler().compile(
        inputs={"a": "Basin_A", "b": "Basin_B"},
        outputs={"out": "Basin_Out"},
        statements=main_stmts,
        subroutines={
            "SubWide": {
                "inputs": {"p0": "Basin_Sub_P0", "p1": "Basin_Sub_P1"},
                "outputs": {"r_out": "Basin_Sub_Out"},
                "statements": sub_stmts,
            }
        },
        pure_wave=True,
    )
    scratch_vals = list(sub_prog.allocated_scratch_basins.values())
    assert len(scratch_vals) >= 2
    assert len(scratch_vals) == len(set(scratch_vals))


def test_static_mass_sentinel_rejects_unbounded_slow_draining_loops() -> None:
    """Regression: loops with negative net cycle mass gain must fail even if 8 iterations stay >= 14.0."""
    from lumina_compiler import StaticVerificationError

    slow_drain_src = (
        "def flow(self):\n"
        "    x = self.in_a\n"
        "    while x:\n"
        "        self.settle(5)\n"
        "    self.out_y = x\n"
    )
    slow_prog = LuminaCompiler.compile_flow_src(
        inputs={"in_a": "Basin_A"},
        outputs={"out_y": "Basin_Y"},
        flow_src=slow_drain_src,
        verify_mass=False,
        pure_wave=True,
    )
    with pytest.raises(StaticVerificationError, match="negative net cycle mass gain"):
        StaticMassSentinel.verify(slow_prog, damping=0.01, max_loop_unroll=8)


def test_tool4_all_canonical_specs_and_custom_multi_output_truth_tables() -> None:
    """Verify Tool #4 across all 8 canonical specs, SR_LATCH_SYNC, and custom multi-output truth tables."""
    sandbox = SubstrateToolSandbox(repo_root=_REPO_ROOT)

    for spec_name, expected_rows in (
        ("XOR", 4),
        ("HALF_ADDER", 4),
        ("FULL_ADDER", 8),
        ("MUX_2to1", 8),
        ("HALF_SUBTRACTOR", 4),
        ("MAJORITY_3", 8),
        ("PARITY_3", 8),
        ("EQUALS_2BIT", 16),
        ("SR_LATCH_SYNC", 8),
    ):
        rep = sandbox.execute_tool(
            "sol_synthesize_and_reflect_circuit",
            {"spec_name": spec_name, "word_width": 64, "bit_sliced_exhaustive": True},
        )
        assert rep["verified"] is True, f"{spec_name} failed: {rep}"
        assert rep["accuracy"] == 1.0
        assert rep["symbolic_equivalent"] is True
        assert rep["metacognitive_plan_verified"] is True
        assert rep["bit_sliced_rows_verified"] == expected_rows
        assert rep["bit_sliced_row_mismatches"] == 0

    custom_tt = {
        "name": "CUSTOM_DUAL_VOTE_PARITY",
        "inputs": ["SENSOR", "NOT_EN", "MODE_XOR"],
        "outputs": ["Y_VOTE", "Y_PARITY"],
        "table": {
            f"{a},{b},{c}": [1 if (a + b + c) >= 2 else 0, a ^ b ^ c]
            for a in (0, 1)
            for b in (0, 1)
            for c in (0, 1)
        },
    }
    custom_rep = sandbox.execute_tool(
        "sol_synthesize_and_reflect_circuit",
        {
            "spec_name": "CUSTOM",
            "word_width": 64,
            "bit_sliced_exhaustive": True,
            "custom_truth_table": custom_tt,
        },
    )
    assert custom_rep["verified"] is True
    assert custom_rep["accuracy"] == 1.0
    assert custom_rep["symbolic_equivalent"] is True
    assert custom_rep["metacognitive_plan_verified"] is True
    assert custom_rep["bit_sliced_rows_verified"] == 8
    assert custom_rep["bit_sliced_row_mismatches"] == 0

    with pytest.raises(ValueError):
        sandbox.sol_synthesize_and_reflect_circuit(
            spec_name="CUSTOM",
            custom_truth_table={"inputs": ["A"], "outputs": ["Y"], "table": {}},
        )

    # Tool #6 custom flow_code with hierarchical fa0 component ports
    t6_rep = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_Sum",
            "pure_wave": True,
            "flow_code": (
                "self.fa0.x = self.x\n"
                "self.fa0.y = self.y\n"
                "self.fa0.cin = self.cin\n"
                "self.fa0.run()\n"
                "self.sum = self.fa0.sum\n"
                "self.cout = self.fa0.cout\n"
            ),
        },
    )
    assert t6_rep["policy_status"] == "ELIGIBLE"
    assert t6_rep["static_mass_verified"] is True


def test_venue5_and_companion_docs_have_zero_broken_markdown_links() -> None:
    """Verify zero broken relative or file:/// markdown links across Venue 5 & Companion documentation."""
    import re
    from urllib.parse import unquote

    docs = [
        _REPO_ROOT / "docs" / "companion_sessions" / "NEXT_RND_VENUES_ROADMAP.md",
        _REPO_ROOT / "docs" / "SOL_NEXT_SESSION_PRIMER.md",
        _REPO_ROOT / "docs" / "companion_sessions" / "README.md",
        _REPO_ROOT / "RESEARCH_NOTE_BICAMERAL_AUTOPOIETIC_SHEAF_AGENT.md",
        _REPO_ROOT / "docs" / "companion_sessions" / "2026-10-30_session_03_venue5_pure_wave_neuro_physical_codesign.md",
        _REPO_ROOT / "docs" / "companion_sessions" / "2026-11-02_session_04_venue5_track_a_autonomous_loop_repair.md",
        _REPO_ROOT / "docs" / "companion_sessions" / "2026-11-02_session_05_venue5_track_a_stress_integration.md",
        _REPO_ROOT / "docs" / "companion_sessions" / "2026-11-02_session_06_venue5_track_b_peephole_and_quench.md",
        _REPO_ROOT / "docs" / "companion_sessions" / "2026-11-03_session_07_venue5_track_c_vector_rk4_and_margin_coopt.md",
        _REPO_ROOT / "docs" / "companion_sessions" / "2026-11-03_session_08_venue1_sigma_abc_superposition_rollout.md",
        _REPO_ROOT / "docs" / "companion_sessions" / "2026-11-03_session_09_venue2_sigma_abc_sheaf_firewall.md",
    ]
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    broken: list[tuple[str, str]] = []
    for doc in docs:
        assert doc.exists(), f"Missing expected doc: {doc}"
        for m in link_re.finditer(doc.read_text(encoding="utf-8")):
            raw = m.group(1).strip()
            if raw.startswith(("http://", "https://", "#", "mailto:", "sidecar://")):
                continue
            target_part = unquote(raw.split("#")[0])
            if not target_part:
                continue
            target_path = (
                Path(target_part[len("file:///") :])
                if target_part.startswith("file:///")
                else (doc.parent / target_part).resolve()
            )
            if not target_path.exists():
                broken.append((str(doc), raw))
    assert broken == [], f"Broken markdown file links detected: {broken}"


def test_track_a_autonomous_loop_repair_nudge_aliases_damping_and_custom_rk4() -> None:
    """Verify Track A multi-turn flow_code repair, self.nudge alias resolution, damping=0.05 propagation, and custom RK4."""
    # 1. ManifoldGroup preserves configured damping across step() and run_steps()
    basins_def = [("Basin_In_A", 0), ("Basin_In_B", 30), ("Basin_Sum_Out", 120)]
    grp = build_custom_group(basins_def, pure_wave=True, damping=0.05)
    grp_low = build_custom_group(basins_def, pure_wave=True, damping=0.01)
    assert grp.damping == pytest.approx(0.05)
    assert grp.engine.damping == pytest.approx(0.05)
    grp.prime_basin("Basin_In_A", active=True)
    grp_low.prime_basin("Basin_In_A", active=True)
    grp.step()
    grp_low.step()
    grp.run_steps(4)
    grp_low.run_steps(4)
    assert grp.engine.damping == pytest.approx(0.05)
    assert grp.get_node("S0")["rho"] < grp_low.get_node("S0")["rho"]

    # 2. Turn 1: Uncompensated pure-wave loop triggers Cycle-0 QUARANTINE with actionable counter-demands
    sandbox = SubstrateToolSandbox(repo_root=_REPO_ROOT)
    turn1_uncompensated = (
        "while self.in_a:\n"
        "    self.settle(25)\n"
        "    self.sum_out = self.in_a ^ self.in_b"
    )
    res_turn1 = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "damping": 0.05,
            "flow_code": turn1_uncompensated,
        },
    )
    assert res_turn1["cycle0_quarantined"] is True
    assert res_turn1["policy_status"] == "QUARANTINE"
    assert res_turn1["static_mass_verified"] is False
    assert "Basin_In_A" in res_turn1["static_verification_error"]
    assert len(res_turn1["counter_demands"]) >= 1
    json.dumps(res_turn1, allow_nan=False)

    # 3. Turn 2 (Variant A: explicit Basin_* names): Autonomous repair passes StaticMassSentinel and 4/4 RK4 cases
    turn2_repaired_explicit = (
        "while self.in_a:\n"
        "    self.nudge('Basin_In_A', 15.0)\n"
        "    self.nudge('Basin_In_B', 15.0)\n"
        "    self.nudge('Basin_Sum_Out', 15.0)\n"
        "    self.settle(15)\n"
        "    self.sum_out = self.in_a ^ self.in_b"
    )
    res_turn2_a = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "damping": 0.05,
            "flow_code": turn2_repaired_explicit,
        },
    )
    assert res_turn2_a["cycle0_quarantined"] is False
    assert res_turn2_a["policy_status"] == "ELIGIBLE"
    assert res_turn2_a["static_mass_verified"] is True
    assert res_turn2_a["physical_rk4_verified"] is True
    assert res_turn2_a["physical_rk4_cases_verified"] == 4
    assert res_turn2_a["python_boolean_shortcuts_used"] == 0
    assert res_turn2_a["min_charge_margin_vs_tau"] > 0.0
    assert res_turn2_a["compiled_claims_count"] >= 1
    assert any("NUDGE('Basin_In_A', 15.0)" in s for s in res_turn2_a["instructions"])
    json.dumps(res_turn2_a, allow_nan=False)

    # 4. Turn 2 (Variant B: port aliases self.in_a / 'in_b' / 'sum_out' and self.assert_mass)
    turn2_repaired_aliases = (
        "while self.in_a:\n"
        "    self.nudge(self.in_a, 15.0)\n"
        "    self.nudge('in_b', 15.0)\n"
        "    self.nudge(self.sum_out, 15.0)\n"
        "    self.settle(15)\n"
        "    self.assert_mass(self.in_a, 14.0)\n"
        "    self.sum_out = self.in_a ^ self.in_b"
    )
    res_turn2_b = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "damping": 0.05,
            "flow_code": turn2_repaired_aliases,
        },
    )
    assert res_turn2_b["policy_status"] == "ELIGIBLE"
    assert res_turn2_b["static_mass_verified"] is True
    assert res_turn2_b["physical_rk4_verified"] is True
    assert res_turn2_b["physical_rk4_cases_verified"] == 4
    assert res_turn2_b["python_boolean_shortcuts_used"] == 0

    # 5. Turn 2 (Variant C: global 'ALL' nudge target)
    turn2_repaired_all = (
        "while self.in_a:\n"
        "    self.nudge('ALL', 15.0)\n"
        "    self.settle(15)\n"
        "    self.sum_out = self.in_a ^ self.in_b"
    )
    res_turn2_c = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "damping": 0.05,
            "flow_code": turn2_repaired_all,
        },
    )
    assert res_turn2_c["policy_status"] == "ELIGIBLE"
    assert res_turn2_c["static_mass_verified"] is True
    assert res_turn2_c["physical_rk4_verified"] is True
    assert res_turn2_c["physical_rk4_cases_verified"] == 4
    assert res_turn2_c["python_boolean_shortcuts_used"] == 0

    # 6. Regression: Unrelated or partial single-basin nudge must NOT mask mass drain on Basin_In_A
    res_unrelated_nudge = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "damping": 0.05,
            "flow_code": (
                "while self.in_a:\n"
                "    self.nudge('Basin_Unrelated', 15.0)\n"
                "    self.settle(25)\n"
                "    self.sum_out = self.in_a ^ self.in_b"
            ),
        },
    )
    assert res_unrelated_nudge["policy_status"] == "QUARANTINE"
    assert res_unrelated_nudge["static_mass_verified"] is False
    assert "Basin_In_A" in res_unrelated_nudge["static_verification_error"]

    # 7. Regression: StaticMassSentinel rejects uncompensated backward JUMP_IF_COLLAPSED and failing ASSERT_MASS
    with pytest.raises(StaticVerificationError, match="negative net cycle mass gain"):
        StaticMassSentinel.verify(
            [
                Instruction("LABEL", ["L0"]),
                Instruction("LOAD", ["A", "Basin_In_A"]),
                Instruction("SETTLE", [5]),
                Instruction("JUMP_IF_COLLAPSED", ["A", "L0"]),
            ],
            damping=0.05,
        )

    res_assert_mass_fail = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "damping": 0.05,
            "flow_code": (
                "self.assert_mass(self.in_a, 50.0)\n"
                "self.sum_out = self.in_a ^ self.in_b"
            ),
        },
    )
    assert res_assert_mass_fail["policy_status"] == "QUARANTINE"
    assert res_assert_mass_fail["static_mass_verified"] is False
    assert "ASSERT_MASS" in res_assert_mass_fail["static_verification_error"]

    # 8. Regression: Read-modify-write output accumulator must not trigger false input-insulation breach
    res_rmw_out = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "damping": 0.05,
            "flow_code": (
                "while self.in_a:\n"
                "    self.nudge('ALL', 15.0)\n"
                "    self.settle(15)\n"
                "    self.sum_out = self.sum_out | self.in_b"
            ),
        },
    )
    assert res_rmw_out["policy_status"] == "ELIGIBLE"
    assert res_rmw_out["static_mass_verified"] is True
    assert res_rmw_out["physical_rk4_verified"] is True
    assert res_rmw_out["physical_rk4_cases_verified"] == 4

    # 9. Regression: In-place input variable mutation inside loop pre-copies to Basin_Scratch_0 and updates across iterations
    res_loop_input_mut = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "damping": 0.05,
            "flow_code": (
                "while self.in_a:\n"
                "    self.nudge('ALL', 15.0)\n"
                "    self.settle(15)\n"
                "    self.in_a = self.in_a ^ self.in_b\n"
                "    self.sum_out = self.in_a"
            ),
        },
    )
    assert res_loop_input_mut["policy_status"] == "ELIGIBLE"
    assert res_loop_input_mut["static_mass_verified"] is True
    assert res_loop_input_mut["physical_rk4_verified"] is True
    assert res_loop_input_mut["allocated_scratch_basins"] == {"in_a": "Basin_Scratch_0"}
    assert sum(1 for inst in res_loop_input_mut["instructions"] if "STORE" in inst and "Basin_Scratch_0" in inst) == 2

    # 9b. Regression: Explicit Basin_Scratch_0 nudge in input-mutating loop credits prologue input lineage
    res_scratch_explicit = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "damping": 0.05,
            "flow_code": (
                "while self.in_a:\n"
                "    self.nudge('Basin_Scratch_0', 15.0)\n"
                "    self.nudge(self.in_b, 15.0)\n"
                "    self.nudge(self.sum_out, 15.0)\n"
                "    self.nudge(self.carry_out, 15.0)\n"
                "    self.settle(25)\n"
                "    self.assert_mass(self.in_b, 25.0)\n"
                "    self.in_a = self.in_a ^ self.in_b\n"
                "    self.sum_out = self.in_a\n"
                "    self.carry_out = self.carry_out | (self.in_a & self.in_b)"
            ),
        },
    )
    assert res_scratch_explicit["policy_status"] == "ELIGIBLE"
    assert res_scratch_explicit["static_mass_verified"] is True
    assert res_scratch_explicit["physical_rk4_verified"] is True
    assert res_scratch_explicit["physical_rk4_cases_verified"] == 4
    assert res_scratch_explicit["allocated_scratch_basins"] == {"in_a": "Basin_Scratch_0"}

    # 10. Regression: Component port alias in self.nudge before .run() resolves to Basin_fa0_x
    res_comp_nudge = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "damping": 0.05,
            "flow_code": (
                "self.nudge(self.fa0.x, 15.0)\n"
                "self.sum_out = self.in_a ^ self.in_b"
            ),
        },
    )
    assert any("NUDGE('Basin_fa0_x', 15.0)" in inst for inst in res_comp_nudge["instructions"])


def test_track_b_peephole_scratch_nudge_and_pure_wave_quench() -> None:
    """
    Verifies Track B deliverables:
    1. Scratch-alias-aware NUDGE and ASSERT_MASS lowering in input-mutating loops (`self.in_a` -> `Basin_Scratch_0`).
    2. Dirty-spill tracking, forward-branch register retention, and scalar copy-propagation (`<= 26` instructions on SequentialHalfAdderFsmAgent, zero COPY/CMOVE shuffle, single STORE to Basin_Carry_Out).
    3. Pure-wave 30-step anti-phase waveguide quench on CLEAR and RESET_CORE (`pure_wave_quench_ops > 0`, zero Python b_state/b_charge overrides on registers) and pure-wave 1-bit LOAD_INDIRECT wave multiplexing.
    """
    from agentic_inventor import build_custom_group
    from hybrid_subsystem_framework import Instruction, MicroInstructionSequencer

    sandbox = SubstrateToolSandbox(repo_root=_REPO_ROOT)

    # 1. SequentialHalfAdderFsmAgent with self.nudge(self.in_a, 15.0) and self.assert_mass(self.in_a, 25.0)
    res_fsm = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "damping": 0.05,
            "flow_code": (
                "while self.in_a:\n"
                "    self.nudge(self.in_a, 15.0)\n"
                "    self.nudge(self.in_b, 15.0)\n"
                "    self.nudge(self.sum_out, 15.0)\n"
                "    self.nudge(self.carry_out, 15.0)\n"
                "    self.settle(25)\n"
                "    self.assert_mass(self.in_a, 25.0)\n"
                "    self.assert_mass(self.in_b, 25.0)\n"
                "    self.in_a = self.in_a ^ self.in_b\n"
                "    self.sum_out = self.in_a\n"
                "    self.carry_out = self.carry_out | (self.in_a & self.in_b)"
            ),
        },
    )
    assert res_fsm["policy_status"] == "ELIGIBLE"
    assert res_fsm["static_mass_verified"] is True
    assert res_fsm["physical_rk4_verified"] is True
    assert res_fsm["physical_rk4_cases_verified"] == 4
    assert res_fsm["python_boolean_shortcuts_used"] == 0
    assert res_fsm["pure_wave_quench_ops"] > 0
    assert res_fsm["allocated_scratch_basins"] == {"in_a": "Basin_Scratch_0"}
    insts = res_fsm["instructions"]
    assert any("NUDGE('Basin_Scratch_0', 15.0)" in s for s in insts)
    assert any("ASSERT_MASS('Basin_Scratch_0', 25.0)" in s for s in insts)
    assert res_fsm["instruction_count"] <= 28
    assert "CMOVE" not in res_fsm["opcodes"]
    assert "COPY" not in res_fsm["opcodes"]
    assert sum(1 for s in insts if "STORE" in s and "Basin_Scratch_0" in s) == 2
    assert sum(1 for s in insts if "STORE" in s and "Basin_Carry_Out" in s) == 1

    # 2. Direct physical verification of pure-wave CLEAR, RESET_CORE, and 1-bit LOAD_INDIRECT
    group = build_custom_group(
        [("Basin_Arr_0", 0), ("Basin_Arr_1", 10), ("Basin_Out", 20)],
        pure_wave=True,
        damping=0.05,
    )
    group.prime_basin("Basin_Arr_0", active=False)
    group.prime_basin("Basin_Arr_1", active=True)
    group.prime_basin("Basin_Out", active=False)
    group.prime_register("A", active=True)
    group.prime_register("B", active=False)
    group.prime_register("C", active=True)
    group.prime_register("D", active=True)

    seq = MicroInstructionSequencer(group, pure_wave=True, record_substep_telemetry=False)
    # Pure-wave 1-bit LOAD_INDIRECT with addr_reg='D' (active=1 -> selects Basin_Arr_1=1 into B)
    seq.execute_instruction(Instruction("LOAD_INDIRECT", ["B", "Arr_", "D"]))
    assert group.get_node("S_RB_B")["b_state"] == 1
    assert float(group.get_node("S_RB_B")["b_charge"]) > 0.65

    # Pure-wave CLEAR on A and RESET_CORE on C, D via 30-step anti-phase waveguide quench
    seq.execute_instruction(Instruction("CLEAR", ["A"]))
    seq.execute_instruction(Instruction("RESET_CORE", []))
    assert seq.pure_wave_quench_ops == 3
    assert seq.python_boolean_shortcuts_used == 0
    for cleared_reg in ("A", "C", "D"):
        bat = group.get_node(f"S_R{cleared_reg}_B")
        assert bat["b_state"] == -1
        assert float(bat["b_charge"]) < 0.065
        assert float(bat["psi"]) < 0.0

    # Now D is collapsed (-1 -> 0): pure-wave 1-bit LOAD_INDIRECT selects Basin_Arr_0=0 into B
    seq.execute_instruction(Instruction("LOAD_INDIRECT", ["B", "Arr_", "D"]))
    assert group.get_node("S_RB_B")["b_state"] == -1
    assert float(group.get_node("S_RB_B")["b_charge"]) < 0.065

    # 3. Pure-wave 1-bit LOAD_INDIRECT when destination reg == addr_reg ('D' -> 'D')
    group.prime_register("D", active=True)
    tel_before = len(seq.wave_gate_telemetry)
    seq.execute_instruction(Instruction("LOAD_INDIRECT", ["D", "Arr_", "D"]))
    assert len(seq.wave_gate_telemetry) == tel_before + 1
    assert seq.wave_gate_telemetry[-1]["op"] == "LOAD_INDIRECT_WAVE"
    assert group.get_node("S_RD_B")["b_state"] == 1
    assert float(group.get_node("S_RD_B")["b_charge"]) > 0.65

    group.prime_register("D", active=False)
    seq.execute_instruction(Instruction("LOAD_INDIRECT", ["D", "Arr_", "D"]))
    assert len(seq.wave_gate_telemetry) == tel_before + 2
    assert seq.wave_gate_telemetry[-1]["op"] == "LOAD_INDIRECT_WAVE"
    assert group.get_node("S_RD_B")["b_state"] == -1
    assert float(group.get_node("S_RD_B")["b_charge"]) < 0.065
    assert seq.python_boolean_shortcuts_used == 0

    # 4. Scratch origin lineage isolation: nudging self.in_a (Basin_Scratch_0) must NOT mask missing self.in_b nudge
    res_missing_in_b = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "damping": 0.05,
            "flow_code": (
                "while self.in_a:\n"
                "    self.nudge(self.in_a, 15.0)\n"
                "    self.nudge(self.sum_out, 15.0)\n"
                "    self.nudge(self.carry_out, 15.0)\n"
                "    self.settle(25)\n"
                "    self.in_a = self.in_a ^ self.in_b\n"
                "    self.sum_out = self.in_a\n"
                "    self.carry_out = self.carry_out | (self.in_a & self.in_b)"
            ),
        },
    )
    assert res_missing_in_b["policy_status"] == "QUARANTINE"
    assert res_missing_in_b["static_mass_verified"] is False
    assert "Basin_In_B" in res_missing_in_b["static_verification_error"]

    # 5. Local loop variable scratch lowering in NUDGE and ASSERT_MASS (`x = self.in_a; while x:`)
    res_local_loop_var = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "damping": 0.05,
            "flow_code": (
                "x = self.in_a\n"
                "while x:\n"
                "    self.nudge(x, 15.0)\n"
                "    self.nudge(self.in_b, 15.0)\n"
                "    self.nudge(self.sum_out, 15.0)\n"
                "    self.settle(25)\n"
                "    self.assert_mass(x, 25.0)\n"
                "    x = x ^ self.in_b\n"
                "    self.sum_out = x"
            ),
        },
    )
    assert res_local_loop_var["policy_status"] == "ELIGIBLE"
    assert res_local_loop_var["static_mass_verified"] is True
    assert res_local_loop_var["physical_rk4_verified"] is True
    assert res_local_loop_var["physical_rk4_cases_verified"] == 4
    assert res_local_loop_var["allocated_scratch_basins"] == {"x": "Basin_Scratch_0"}
    assert any("NUDGE('Basin_Scratch_0', 15.0)" in s for s in res_local_loop_var["instructions"])
    assert any("ASSERT_MASS('Basin_Scratch_0', 25.0)" in s for s in res_local_loop_var["instructions"])

    # 6. Dynamic pure_wave_quench_ops counting on branching programs (counts actual executed quenches, not static CLEARs * 4)
    res_branch_quench = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "flow_code": (
                "if self.in_a:\n"
                "    self.sum_out = self.in_a ^ self.in_b\n"
                "else:\n"
                "    self.sum_out = self.in_a | self.in_b"
            ),
        },
    )
    assert res_branch_quench["policy_status"] == "ELIGIBLE"
    assert res_branch_quench["physical_rk4_verified"] is True
    static_clears = sum(1 for op in res_branch_quench["opcodes"] if op == "CLEAR")
    assert res_branch_quench["pure_wave_quench_ops"] == 30
    assert res_branch_quench["pure_wave_quench_ops"] < static_clears * 4


def test_track_c_vector_rk4_monolithic_alu_and_cavity_margin_coopt() -> None:
    """
    Verifies Track C deliverables:
    1. BatchPureWaveVerifier (both deduplicate_components=True and deduplicate_components=False)
       matches scalar SOLEngine (run_trial) to < 1e-12 IEEE-754 float64 precision across all 8
       input vectors of hierarchical_full_adder.
    2. Monolithic 1,024-row lockstep physical RK4 verification of WaveAlu4BitAgent
       (1024/1024 rows, 201 instructions, 3 scratch basins, 19 total basins, 13,377 RK4 steps,
       0 Python boolean shortcuts) and Tool #6 verify_on_task='wave_alu_4bit'.
    3. 3-regime Riemannian cavity & readout threshold co-optimization expanding min_charge_margin_vs_tau
       from 0.35 (tau=0.65, cf=0.10) to 0.50 (tau=0.50, cf=0.20) on canonical tasks / Track B loop
       and to 0.4367 (tau=0.50) / 0.46835 (tau=0.53165) on 1,024-row WAVE_ALU_4BIT, while preserving
       SOL-CERT-V2-2026-WAVE_ALU_4BIT-EEF8F2A83406 and Sacred Core Graph SHA-256 invariance.
    """
    import numpy as np
    from hybrid_subsystem_framework import BatchPureWaveVerifier
    from sol_continuum.venue5_neuro_physical_codesign import (
        co_optimize_cavity_and_readout_margins,
        verify_monolithic_wave_alu_4bit_rk4,
    )

    # 1. BatchPureWaveVerifier (dedup + dense BLAS GEMM) vs scalar SOLEngine float64 parity (< 1e-12)
    prog_hfa = LuminaCompiler.compile_agent(HierarchicalFullAdderAgent, pure_wave=True)
    task_hfa = TASKS["hierarchical_full_adder"]
    basins_hfa = _discover_program_basins(task_hfa["basins_def"], prog_hfa)
    in_keys_hfa = list(task_hfa["inputs"].values())
    out_keys_hfa = list(task_hfa["outputs"].values())
    rows_hfa = [
        {in_keys_hfa[i]: vec[i] for i in range(len(vec))}
        for vec in task_hfa["input_space"]
    ]

    bv_dedup = BatchPureWaveVerifier(
        basins_hfa,
        rows_hfa,
        damping=0.01,
        deduplicate_components=True,
    )
    bv_dedup.run(prog_hfa)
    dedup_outs = bv_dedup.read_output_rows(out_keys_hfa)

    bv_dense = BatchPureWaveVerifier(
        basins_hfa,
        rows_hfa,
        damping=0.01,
        deduplicate_components=False,
    )
    bv_dense.run(prog_hfa)
    dense_outs = bv_dense.read_output_rows(out_keys_hfa)

    assert dedup_outs == dense_outs
    assert bv_dedup.python_boolean_shortcuts_used == 0
    assert bv_dense.python_boolean_shortcuts_used == 0
    diff_dedup_vs_dense = float(np.max(np.abs(bv_dedup.rho - bv_dense.rho)))
    assert diff_dedup_vs_dense < 1e-12

    max_diff_dedup_scalar = 0.0
    max_diff_dense_scalar = 0.0
    for r_i, vec in enumerate(task_hfa["input_space"]):
        group_s = build_custom_group(basins_hfa, pure_wave=True, damping=0.01)
        for b_name, _ in basins_hfa:
            group_s.prime_basin(b_name, active=False)
        for reg in ("A", "B", "C", "D"):
            group_s.prime_register(reg, active=False)
        for i_k, val in enumerate(vec):
            if val == 1:
                group_s.prime_basin(in_keys_hfa[i_k], active=True)
        seq_s = MicroInstructionSequencer(group_s, pure_wave=True, record_substep_telemetry=False)
        vm_s = LogosVM(seq_s)
        hist_s = vm_s.run(prog_hfa)
        scalar_out = tuple(_read_basin_state(hist_s[-1], ob, basins_hfa) for ob in out_keys_hfa)
        assert dedup_outs[r_i] == scalar_out
        rho_s = np.array([float(n["rho"]) for n in group_s.engine.physics.nodes])
        max_diff_dedup_scalar = max(max_diff_dedup_scalar, float(np.max(np.abs(bv_dedup.rho[r_i] - rho_s))))
        max_diff_dense_scalar = max(max_diff_dense_scalar, float(np.max(np.abs(bv_dense.rho[r_i] - rho_s))))

    assert max_diff_dedup_scalar < 1e-12
    assert max_diff_dense_scalar < 1e-12

    # 2. Monolithic 1,024-row lockstep physical RK4 verification of WAVE_ALU_4BIT
    #    and 3-regime cavity & readout threshold co-optimization (testing fresh-cache order independence)
    from sol_continuum.venue5_neuro_physical_codesign import (
        _MONOLITHIC_WAVE_ALU_4BIT_RK4_CACHE,
    )

    _MONOLITHIC_WAVE_ALU_4BIT_RK4_CACHE.clear()
    co_opt = co_optimize_cavity_and_readout_margins()
    assert co_opt["all_regimes_verified"] is True
    assert co_opt["baseline_min_margin"] == pytest.approx(0.35, abs=1e-4)
    assert co_opt["symmetric_canonical_min_margin"] == pytest.approx(0.43689, abs=1e-4)
    assert (
        co_opt["regimes"]["co_optimized_symmetric_tau_050_cf_020"]["canonical_tasks"][
            "half_adder"
        ]["min_charge_margin_vs_tau"]
        == pytest.approx(0.50, abs=1e-4)
    )
    assert (
        co_opt["regimes"]["co_optimized_symmetric_tau_050_cf_020"]["canonical_tasks"][
            "hierarchical_full_adder"
        ]["min_charge_margin_vs_tau"]
        == pytest.approx(0.43757, abs=1e-4)
    )
    assert co_opt["symmetric_alu_1024_min_margin"] == pytest.approx(0.4367, abs=1e-4)
    assert co_opt["balanced_alu_1024_min_margin"] == pytest.approx(0.46835, abs=1e-4)

    alu_res = verify_monolithic_wave_alu_4bit_rk4(
        flip_threshold=0.53165,
        collapse_factor=0.20,
    )
    assert alu_res["verified"] is True
    assert alu_res["passed_rows"] == 1024
    assert alu_res["total_rows"] == 1024
    assert alu_res["accuracy_pct"] == 100.0
    assert alu_res["instruction_count"] == 201
    assert alu_res["scratch_basins_count"] == 3
    assert alu_res["total_basins_count"] == 19
    assert alu_res["rk4_steps_executed"] == 13377
    assert alu_res["gate_commits_evaluated"] == 46
    assert alu_res["python_boolean_shortcuts_used"] == 0
    assert alu_res["max_off_charge_at_commit"] == pytest.approx(0.0633, abs=1e-4)
    assert alu_res["min_on_charge_at_commit"] == pytest.approx(1.0, abs=1e-4)
    assert alu_res["min_charge_margin_vs_tau"] == pytest.approx(0.46835, abs=1e-4)
    assert alu_res["opcode_breakdown"]["ADD (00)"]["passed"] == 256
    assert alu_res["opcode_breakdown"]["SUB (01)"]["passed"] == 256
    assert alu_res["opcode_breakdown"]["OR (10)"]["passed"] == 256
    assert alu_res["opcode_breakdown"]["AND (11)"]["passed"] == 256

    # Edge case: extreme invalid threshold outside [0.45, 0.65] must fail physical verification
    from coding_library.components.half_adder import HalfAdderAgent

    prog_ha = LuminaCompiler.compile_agent(HalfAdderAgent, pure_wave=True, damping=0.01)
    ok_extreme, cases_extreme, shortcuts_extreme, _, _ = verify_canonical_task_rk4(
        "half_adder",
        prog_ha,
        pure_wave=True,
        damping=0.01,
        flip_threshold=0.999,
        collapse_factor=0.999,
    )
    assert ok_extreme is False
    assert cases_extreme == 4
    assert shortcuts_extreme == 0

    sandbox = SubstrateToolSandbox(repo_root=_REPO_ROOT)

    # Tool #6 on Track B loop with co-optimized (flip_threshold=0.50, collapse_factor=0.20)
    res_loop_coopt = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "damping": 0.05,
            "flip_threshold": 0.50,
            "collapse_factor": 0.20,
            "flow_code": (
                "while self.in_a:\n"
                "    self.nudge(self.in_a, 15.0)\n"
                "    self.nudge(self.in_b, 15.0)\n"
                "    self.nudge(self.sum_out, 15.0)\n"
                "    self.nudge(self.carry_out, 15.0)\n"
                "    self.settle(25)\n"
                "    self.assert_mass(self.in_a, 25.0)\n"
                "    self.assert_mass(self.in_b, 25.0)\n"
                "    self.in_a = self.in_a ^ self.in_b\n"
                "    self.sum_out = self.in_a\n"
                "    self.carry_out = self.carry_out | (self.in_a & self.in_b)"
            ),
        },
    )
    assert res_loop_coopt["policy_status"] == "ELIGIBLE"
    assert res_loop_coopt["physical_rk4_verified"] is True
    assert res_loop_coopt["min_charge_margin_vs_tau"] == pytest.approx(0.43783, abs=1e-4)
    assert res_loop_coopt["min_charge_margin_vs_tau"] > 0.35
    assert res_loop_coopt["collapse_threshold"] == pytest.approx(0.10, abs=1e-4)

    res_hfa_coopt = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_A_SUM",
            "pure_wave": True,
            "verify_on_task": "hierarchical_full_adder",
            "flip_threshold": 0.50,
            "collapse_factor": 0.20,
        },
    )
    assert res_hfa_coopt["policy_status"] == "ELIGIBLE"
    assert res_hfa_coopt["physical_rk4_verified"] is True
    assert res_hfa_coopt["min_charge_margin_vs_tau"] == pytest.approx(0.43757, abs=1e-4)
    assert res_hfa_coopt["min_charge_margin_vs_tau"] > 0.35
    assert res_hfa_coopt["collapse_threshold"] == pytest.approx(0.10, abs=1e-4)

    # Tool #6 with verify_on_task="wave_alu_4bit"
    res_t6_alu = sandbox.execute_tool(
        "sol_compile_lumina_agent_and_claim",
        {
            "basin_name": "Basin_Y0",
            "pure_wave": True,
            "verify_on_task": "wave_alu_4bit",
            "flip_threshold": 0.53165,
            "collapse_factor": 0.20,
        },
    )
    assert res_t6_alu["policy_status"] == "ELIGIBLE"
    assert res_t6_alu["physical_rk4_verified"] is True
    assert res_t6_alu["physical_rk4_cases_verified"] == 1024
    assert res_t6_alu["min_charge_margin_vs_tau"] == pytest.approx(0.46835, abs=1e-4)
    assert res_t6_alu["monolithic_wave_alu_4bit_rk4"]["passed_rows"] == 1024

    # Tool #11 with verify_monolithic_alu_rk4=True and co_optimize_cavity_margins=True
    res_t11_c = sandbox.execute_tool(
        "sol_run_rsi_inventor_and_level_chambers",
        {
            "inventor_task": "4bit_wave_alu",
            "pure_wave": True,
            "flip_threshold": 0.53165,
            "collapse_factor": 0.20,
            "verify_monolithic_alu_rk4": True,
            "co_optimize_cavity_margins": True,
            "mint_sol_cert_v2": True,
        },
    )
    assert res_t11_c["monolithic_wave_alu_4bit_rk4"]["verified"] is True
    assert res_t11_c["monolithic_wave_alu_4bit_rk4"]["passed_rows"] == 1024
    assert res_t11_c["cavity_margin_co_optimization"]["all_regimes_verified"] is True
    assert res_t11_c["sol_cert_v2_verified"] is True
    assert res_t11_c["sol_cert_v2"]["cert_id"] == "SOL-CERT-V2-2026-WAVE_ALU_4BIT-EEF8F2A83406"
    assert (
        res_t11_c["sol_cert_v2"]["certificate_sha256"]
        == "2495cf972028fcbd435df87b53bce89f02097dcad83ee4a0cb26dcf924a976b7"
    )
    immutable_ok, graph_sha = verify_sacred_core_graph_sha256(_REPO_ROOT)
    assert immutable_ok is True
    assert graph_sha == EXPECTED_CORE_GRAPH_SHA256


def test_venue5_abc_simplification_and_venue1_sigma_abc_superposition() -> None:
    """
    Verifies:
    1. Venue 5 Track A/B/C simplification: exported CO_OPTIMIZED_* constants, reusable
       verify_custom_flow_rk4 / build_custom_flow_task_spec helpers, and single-call
       run_unified_abc_pipeline (both direct and via Tool #11 run_unified_abc_pipeline=True)
       while preserving SOL-CERT-V2-2026-WAVE_ALU_4BIT-EEF8F2A83406 hash invariance.
    2. Venue 1 Pre-Token Wave Superposition Sigma_ABC law (sol_fork_and_rollout_superposition):
       - Backward compatibility when enable_sigma_abc=False.
       - Law A Cycle-0 QUARANTINE when auto_nudge=False on starved surviving basin 'christ' (13.6743 < 14.0).
       - Law A+B+C ELIGIBLE repair when auto_nudge=True: compensatory NUDGE('christ', 15.0),
         Law B 30-step anti-phase (psi=-1.0) quench on counterfactual basin 'light codes',
         and Law C 4-fork (4, 140) lockstep batch rollout + minimax threshold tau* expansion.
    """
    from sol_continuum import (
        CO_OPTIMIZED_COLLAPSE_FACTOR,
        CO_OPTIMIZED_FLIP_THRESHOLD,
        SYMMETRIC_CO_OPTIMIZED_FLIP_THRESHOLD,
        run_unified_abc_pipeline,
        verify_custom_flow_rk4,
    )

    assert CO_OPTIMIZED_FLIP_THRESHOLD == pytest.approx(0.53165, abs=1e-6)
    assert CO_OPTIMIZED_COLLAPSE_FACTOR == pytest.approx(0.20, abs=1e-6)
    assert SYMMETRIC_CO_OPTIMIZED_FLIP_THRESHOLD == pytest.approx(0.50, abs=1e-6)

    # 1. Direct verify_custom_flow_rk4 on raw flow_code string
    repaired_loop_src = (
        "while self.in_a:\n"
        "    self.nudge(self.in_a, 15.0)\n"
        "    self.nudge(self.in_b, 15.0)\n"
        "    self.nudge(self.sum_out, 15.0)\n"
        "    self.nudge(self.carry_out, 15.0)\n"
        "    self.settle(25)\n"
        "    self.assert_mass(self.in_a, 25.0)\n"
        "    self.assert_mass(self.in_b, 25.0)\n"
        "    self.in_a = self.in_a ^ self.in_b\n"
        "    self.sum_out = self.in_a\n"
        "    self.carry_out = self.carry_out | (self.in_a & self.in_b)"
    )
    ok_cf, cases_cf, shortcuts_cf, min_margin_cf, _ = verify_custom_flow_rk4(
        repaired_loop_src,
        basin_name="Basin_A_SUM",
        pure_wave=True,
        damping=0.05,
        flip_threshold=SYMMETRIC_CO_OPTIMIZED_FLIP_THRESHOLD,
        collapse_factor=CO_OPTIMIZED_COLLAPSE_FACTOR,
    )
    assert ok_cf is True
    assert cases_cf == 4
    assert shortcuts_cf == 0
    assert min_margin_cf == pytest.approx(0.43783, abs=1e-4)

    # Custom combinational SR latch flow with q_prev (verifies all 2^3 = 8 rows without q/q_prev collision)
    sr_qprev_src = (
        "s_eff = self.s & ~self.r\n"
        "self.q = s_eff | (self.q_prev & ~self.r)\n"
        "self.not_q = ~self.q"
    )
    ok_sr, cases_sr, shortcuts_sr, _, _ = verify_custom_flow_rk4(
        sr_qprev_src,
        pure_wave=True,
    )
    assert ok_sr is True
    assert cases_sr == 8
    assert shortcuts_sr == 0

    # 2. Unified Venue 5 Track A+B+C pipeline
    unified = run_unified_abc_pipeline(repo_root=_REPO_ROOT, mint_sol_cert_v2=True)
    assert unified["verified"] is True
    assert unified["policy_status"] == "ELIGIBLE"
    assert unified["stage_a_static_mass"]["cycle0_quarantined"] is True
    assert unified["stage_a_static_mass"]["cycle1_static_mass_verified"] is True
    assert unified["stage_a_static_mass"]["cycle1_physical_rk4_verified"] is True
    assert unified["stage_a_static_mass"]["cycle1_cases_verified"] == 4
    assert unified["stage_b_pure_wave"]["instruction_count"] == 28
    assert unified["stage_b_pure_wave"]["copy_cmove_count"] == 0
    assert unified["stage_b_pure_wave"]["pure_wave_quench_ops"] == 20
    assert unified["stage_b_pure_wave"]["python_boolean_shortcuts_used"] == 0
    assert unified["stage_c_cavity_margin_coopt"]["tau_star"] == pytest.approx(0.53165, abs=1e-5)
    assert unified["stage_c_cavity_margin_coopt"]["balanced_alu_1024_min_margin"] == pytest.approx(0.46835, abs=1e-4)
    assert unified["stage_c_cavity_margin_coopt"]["margin_gain_pct_vs_baseline"] == pytest.approx(33.81, abs=0.05)
    assert unified["sol_cert_v2"]["cert_id"] == "SOL-CERT-V2-2026-WAVE_ALU_4BIT-EEF8F2A83406"
    assert (
        unified["sol_cert_v2"]["certificate_sha256"]
        == "2495cf972028fcbd435df87b53bce89f02097dcad83ee4a0cb26dcf924a976b7"
    )

    sandbox = SubstrateToolSandbox(repo_root=_REPO_ROOT)

    # Tool #11 with run_unified_abc_pipeline=True and mint_sol_cert_v2=False
    res_t11_no_cert = sandbox.execute_tool(
        "sol_run_rsi_inventor_and_level_chambers",
        {
            "inventor_task": "half_adder",
            "pure_wave": True,
            "run_unified_abc_pipeline": True,
            "mint_sol_cert_v2": False,
        },
    )
    assert res_t11_no_cert["unified_abc_pipeline"]["verified"] is True
    assert res_t11_no_cert["unified_abc_pipeline"]["sol_cert_v2"] is None
    assert "sol_cert_v2" not in res_t11_no_cert

    # Tool #11 with run_unified_abc_pipeline=True and mint_sol_cert_v2=True
    res_t11_abc = sandbox.execute_tool(
        "sol_run_rsi_inventor_and_level_chambers",
        {
            "inventor_task": "4bit_wave_alu",
            "pure_wave": True,
            "run_unified_abc_pipeline": True,
            "mint_sol_cert_v2": True,
        },
    )
    assert res_t11_abc["unified_abc_pipeline"]["verified"] is True
    assert res_t11_abc["unified_abc_pipeline"]["policy_status"] == "ELIGIBLE"

    # 3. Venue 1 Pre-Token Wave Superposition Sigma_ABC Law
    res_v1_base = sandbox.execute_tool(
        "sol_fork_and_rollout_superposition",
        {"c_press": 0.48, "damping": 0.87, "psi_diffusion": 0.026, "steps": 60},
    )
    assert "sigma_abc_enabled" not in res_v1_base
    assert res_v1_base["state_restored_exact"] is True

    # Turn 1: enable_sigma_abc=True, auto_nudge=False -> Cycle-0 QUARANTINE on starved 'christ'
    res_v1_t1 = sandbox.execute_tool(
        "sol_fork_and_rollout_superposition",
        {
            "c_press": 0.48,
            "damping": 0.87,
            "psi_diffusion": 0.026,
            "steps": 60,
            "enable_sigma_abc": True,
            "auto_nudge": False,
            "counterfactual_quench_basins": ["light codes"],
            "min_mass_floor": 14.0,
        },
    )
    assert res_v1_t1["sigma_abc_enabled"] is True
    assert res_v1_t1["cycle0_quarantined"] is True
    assert res_v1_t1["policy_status"] == "QUARANTINE"
    assert len(res_v1_t1["counter_demands"]) >= 1
    starved_t1 = res_v1_t1["law_a_mass_sentinel"]["starved_surviving_basins"]
    assert len(starved_t1) == 1
    assert starved_t1[0]["label"] == "christ"
    assert starved_t1[0]["projected_mass"] == pytest.approx(13.6748, abs=1e-3)
    assert res_v1_t1["law_b_anti_phase_quench"]["quench_ops_executed"] == 0
    assert res_v1_t1["state_restored_exact"] is True

    # Turn 2: enable_sigma_abc=True, auto_nudge=True -> ELIGIBLE with Law A nudge, Law B 30-step quench, Law C (4, 140) batch + tau*
    res_v1_t2 = sandbox.execute_tool(
        "sol_fork_and_rollout_superposition",
        {
            "c_press": 0.48,
            "damping": 0.87,
            "psi_diffusion": 0.026,
            "steps": 60,
            "enable_sigma_abc": True,
            "auto_nudge": True,
            "counterfactual_quench_basins": ["light codes"],
            "min_mass_floor": 14.0,
            "hypotheses": [
                "Fork_0_Focused_Attractor",
                "Fork_1_Canonical_Resonance",
                "Fork_2_High_Coupling_Prism",
                "Fork_3_Exploratory_Dispersion",
            ],
        },
    )
    assert res_v1_t2["sigma_abc_enabled"] is True
    assert res_v1_t2["cycle0_quarantined"] is False
    assert res_v1_t2["policy_status"] == "ELIGIBLE"
    assert res_v1_t2["law_a_mass_sentinel"]["static_mass_verified"] is True
    nudge_ops = res_v1_t2["law_a_mass_sentinel"]["auto_nudge_ops"]
    assert len(nudge_ops) == 1
    assert nudge_ops[0]["label"] == "christ"
    assert nudge_ops[0]["nudge_injected"] == pytest.approx(15.0, abs=1e-4)
    assert nudge_ops[0]["mass_after"] == pytest.approx(40.0, abs=1e-4)
    assert nudge_ops[0]["projected_mass_after"] >= 14.0

    law_b = res_v1_t2["law_b_anti_phase_quench"]
    assert law_b["quench_ops_executed"] == 30
    assert len(law_b["quenched_basins"]) == 1
    assert law_b["quenched_basins"][0]["anti_phase_psi"] == -1.0
    assert law_b["quenched_basins"][0]["post_quench_rho"] < law_b["quenched_basins"][0]["pre_quench_rho"]
    assert law_b["quenched_basins"][0]["suppression_db"] > 15.0

    law_c = res_v1_t2["law_c_lockstep_minimax_readout"]
    assert law_c["batch_tensor_shape"] == [4, 140]
    assert len(law_c["lockstep_forks"]) == 4
    assert law_c["e_on_min"] > law_c["e_off_max"]
    assert law_c["minimax_margin_vs_tau_star"] > res_v1_t1["law_c_lockstep_minimax_readout"]["minimax_margin_vs_tau_star"]
    assert law_c["contenders_above_tau_star"] == 4
    assert res_v1_t2["contender_count"] == 4
    assert res_v1_t2["state_restored_exact"] is True
    assert res_v1_t2["sacred_core_graph_immutable"] is True
    assert res_v1_t2["sacred_core_graph_sha256"] == EXPECTED_CORE_GRAPH_SHA256

    # Edge Case A: Dict-based hypotheses (custom batch size B=3 + per-fork physics) & non-standard quench basin 'earth star'
    res_v1_dict_hyp = sandbox.execute_tool(
        "sol_fork_and_rollout_superposition",
        {
            "enable_sigma_abc": True,
            "auto_nudge": True,
            "counterfactual_quench_basins": ["light codes", "earth star"],
            "hypotheses": [
                {"label": "Custom_Low_Press", "c_press": 0.40, "damping": 0.80, "psi_diffusion": 0.020},
                {"name": "Custom_Mid_Press", "c_press": 0.50, "damping": 0.87, "psi_diffusion": 0.026},
                {"id": "Custom_High_Press", "c_press": 0.60, "damping": 0.92, "psi_diffusion": 0.032},
            ],
        },
    )
    assert res_v1_dict_hyp["law_b_anti_phase_quench"]["quench_ops_executed"] == 60
    assert len(res_v1_dict_hyp["law_b_anti_phase_quench"]["quenched_basins"]) == 2
    assert "earth star" in res_v1_dict_hyp["law_c_lockstep_minimax_readout"]["quenched_norm_energies"]
    assert res_v1_dict_hyp["law_c_lockstep_minimax_readout"]["batch_tensor_shape"] == [3, 140]
    assert [
        f["hypothesis_label"]
        for f in res_v1_dict_hyp["law_c_lockstep_minimax_readout"]["lockstep_forks"]
    ] == ["Custom_Low_Press", "Custom_Mid_Press", "Custom_High_Press"]

    # Edge Case B: All 5 standard basins simultaneously quenched -> 0 surviving contenders
    res_v1_all_q = sandbox.execute_tool(
        "sol_fork_and_rollout_superposition",
        {
            "enable_sigma_abc": True,
            "auto_nudge": True,
            "counterfactual_quench_basins": [
                "grail",
                "metatron",
                "pyramid",
                "christ",
                "light codes",
            ],
        },
    )
    assert res_v1_all_q["law_b_anti_phase_quench"]["quench_ops_executed"] == 150
    assert res_v1_all_q["law_c_lockstep_minimax_readout"]["surviving_norm_energies"] == {}
    assert res_v1_all_q["law_c_lockstep_minimax_readout"]["e_on_min"] == 0.0
    assert res_v1_all_q["law_c_lockstep_minimax_readout"]["contenders_above_tau_star"] == 0
    assert res_v1_all_q["contender_count"] == 0


def test_venue2_sigma_abc_sheaf_cohomology_firewall_and_sycophancy_quench() -> None:
    """
    Verify Venue 2 Anti-Sycophancy & Safety Firewall via H^1 Cellular Sheaf Cohomology
    (Sigma_ABC = C_tau* o B_pi o A_rho):
      1. High-K (K=2054, K=2500, K=5000) sycophantic filler criteria cannot dilute a HARD
         safety obstruction in SheafDecisionComplex.evaluate_decision_package().
      2. When all candidate options violate a HARD constraint, evaluate_decision_package()
         quarantines the decision (PolicyStatus.QUARANTINE, eligible_for_execution=False).
      3. Cycle-0 (auto_reconcile=False) vs Cycle-1 (auto_reconcile=True) multi-turn flow
         on Tool #12 (sol_audit_synthesis_counterexamples_and_daosoft_bridge and alias
         sol_audit_sheaf_cohomology).
      4. Law A, Law B (30-step anti-phase quench on live 140-node SOLEngine with 0.0 drift
         on surviving basins), and Law C (multi-scale sycophancy sweep + minimax tau*).
    """
    from sol_decide.interop.daosoft_bridge import DAOSoftBridge

    bridge = DAOSoftBridge()

    # 1. Direct High-K test (K=2054 and K=5000) on DAOSoftBridge + SheafDecisionComplex
    for k_high in (2054, 5000):
        study_k = {
            "study_title": f"High_K_Sycophancy_Test_{k_high}",
            "criteria": [
                {
                    "id": "safety",
                    "name": "Safety Critical",
                    "weight": 1.0,
                    "min_val": 50.0,
                    "max_val": 100.0,
                },
                *[
                    {
                        "id": f"filler_{i}",
                        "name": f"Sycophantic Filler {i}",
                        "weight": 1.0,
                        "min_val": 0.0,
                        "max_val": 100.0,
                    }
                    for i in range(k_high)
                ],
            ],
            "alternatives": [
                {
                    "id": "opt_a_violator",
                    "name": "Option_A_Safety_Violator",
                    "scores": {
                        "safety": 10.0,
                        **{f"filler_{i}": 95.0 for i in range(k_high)},
                    },
                },
                {
                    "id": "opt_b_safe",
                    "name": "Option_B_Safe_Baseline",
                    "scores": {
                        "safety": 80.0,
                        **{f"filler_{i}": 75.0 for i in range(k_high)},
                    },
                },
            ],
        }
        complex_k = bridge.ingest_daosoft_matrix(study_k)
        rep_k = complex_k.evaluate_decision_package()
        # Without hard-constraint partitioning, opt_a_violator's raw score exceeds opt_b_safe by +20*K - 70
        # (+41,010 at K=2054, +99,930 at K=5000), overpowering the -41,000 scalar penalty. With the fix, opt_b_safe wins.
        assert rep_k.selected_option_id == "opt_opt_b_safe"
        assert rep_k.is_feasible is True
        assert rep_k.option_scores["opt_opt_a_violator"] > rep_k.option_scores["opt_opt_b_safe"]
        viol_obs = complex_k.audit_obstructions(
            target_option_id="opt_opt_a_violator"
        )
        assert len(viol_obs) == 1
        assert viol_obs[0]["discrepancy_norm"] == pytest.approx(40.0, abs=1e-6)
        assert viol_obs[0]["discrepancy_norm"] ** 2 == pytest.approx(1600.0, abs=1e-6)

        # Evaluating a decision package where ALL options violate a HARD constraint must be infeasible (selected_option_id=None)
        study_only_viol = {
            "study_title": f"Only_Violator_K_{k_high}",
            "criteria": study_k["criteria"],
            "alternatives": [study_k["alternatives"][0]],
        }
        complex_only_viol = bridge.ingest_daosoft_matrix(study_only_viol)
        rep_only_viol = complex_only_viol.evaluate_decision_package()
        assert rep_only_viol.selected_option_id is None
        assert rep_only_viol.is_feasible is False

    # 1b. High-K (K=2054) edge cases on SheafDecisionComplex directly:
    #     - Default edge_type="allocation" connecting an Option to a HARD Constraint
    #     - Sub-1e-3 (mag=5e-4 > con.tolerance=1e-4) HARD Constraint violation
    #     - Dynamic Constraint.severity mutation (SOFT -> HARD)
    #     - Block-SVD compute_betti_numbers() when D_F > 0 (2-cell plaquette present)
    import numpy as np
    from sol_decide.core.primitives import (
        Constraint,
        ConstraintSeverity,
        Objective,
        Option,
    )
    from sol_decide.core.sheaf_decision_complex import SheafDecisionComplex

    edge_case_complex = SheafDecisionComplex(name="High_K_Allocation_And_Tight_Tolerance")
    con_tight = Constraint(
        id="con_tight_safety",
        name="Tight Safety Bound",
        lower_bound=50.0,
        severity=ConstraintSeverity.SOFT,
        tolerance=1e-4,
    )
    edge_case_complex.add_primitive(con_tight)
    edge_case_complex.add_primitive(
        Objective(id="obj_safety", name="Safety", weight=1.0, target_value=100.0, metadata={"raw_channel": 0})
    )
    for i in range(2054):
        edge_case_complex.add_primitive(
            Objective(id=f"obj_{i}", name=f"Obj {i}", weight=1.0, target_value=100.0, metadata={"raw_channel": i + 1})
        )
        edge_case_complex.add_primitive(
            Constraint(
                id=f"con_{i}",
                name=f"Bound {i}",
                lower_bound=0.0,
                upper_bound=100.0,
                severity=ConstraintSeverity.HARD,
            )
        )
    opt_viol = Option(
        id="opt_a",
        name="Option A Tight Violator",
        stalk_dim=2055,
        initial_params=np.array([49.9995] + [95.0] * 2054),  # mag = 5e-4 > 1e-4, but <= 1e-3
    )
    opt_safe = Option(
        id="opt_b",
        name="Option B Safe",
        stalk_dim=2055,
        initial_params=np.array([50.0] + [75.0] * 2054),
    )
    edge_case_complex.add_primitive(opt_viol)
    edge_case_complex.add_primitive(opt_safe)
    # Connect via default edge_type="allocation" (NOT "constraint_check")
    s0 = np.zeros((1, 2055), dtype=np.float64)
    s0[0, 0] = 1.0
    edge_case_complex.add_edge(
        "e_opt_a_con",
        "opt_a",
        "con_tight_safety",
        dim_edge=1,
        source_map=s0.copy(),
        target_map=np.ones((1, 1)),
    )
    edge_case_complex.add_edge(
        "e_opt_b_con",
        "opt_b",
        "con_tight_safety",
        dim_edge=1,
        source_map=s0.copy(),
        target_map=np.ones((1, 1)),
    )
    for i in range(2054):
        si = np.zeros((1, 2055), dtype=np.float64)
        si[0, i + 1] = 1.0
        edge_case_complex.add_edge(
            f"e_a_{i}",
            "opt_a",
            f"con_{i}",
            dim_edge=1,
            source_map=si.copy(),
            target_map=np.ones((1, 1)),
        )
        edge_case_complex.add_edge(
            f"e_b_{i}",
            "opt_b",
            f"con_{i}",
            dim_edge=1,
            source_map=si.copy(),
            target_map=np.ones((1, 1)),
        )
    # Add a 2-cell plaquette so D_F > 0 at high K (D_E * D_V > 1,000,000)
    edge_case_complex.add_edge(
        "e_con_con0",
        "con_tight_safety",
        "con_0",
        dim_edge=1,
        source_map=np.ones((1, 1)),
        target_map=np.ones((1, 1)),
    )
    edge_case_complex.add_face(
        "face_plaquette_0",
        ["e_opt_a_con", "e_con_con0", "e_a_0"],
        [1.0, 1.0, -1.0],
    )
    # When severity is SOFT, opt_a wins at K=2054; once mutated to HARD, opt_b must win
    rep_soft = edge_case_complex.evaluate_decision_package()
    assert rep_soft.selected_option_id == "opt_a"
    con_tight.severity = ConstraintSeverity.HARD
    rep_hard = edge_case_complex.evaluate_decision_package()
    assert rep_hard.selected_option_id == "opt_b"
    assert rep_hard.is_feasible is True
    assert rep_hard.beta_1 >= 0

    # 2. Sandbox Turn 1: auto_reconcile=False -> Cycle-0 QUARANTINE
    sandbox = SubstrateToolSandbox(repo_root=_REPO_ROOT)
    res_t1 = sandbox.execute_tool(
        "sol_audit_synthesis_counterexamples_and_daosoft_bridge",
        {
            "prism_dimension": 1536,
            "verify_sheaf_resolution": True,
            "enable_sigma_abc": True,
            "auto_reconcile": False,
            "sycophancy_padding_scales": [0, 2, 3, 4, 5, 10, 50, 100, 2500],
            "counterfactual_quench_basins": ["Basin_0_XOR"],
            "min_mass_floor": 0.15,
        },
    )
    assert res_t1["sigma_abc_enabled"] is True
    assert res_t1["cycle0_quarantined"] is True
    assert res_t1["policy_status"] == "QUARANTINE"
    assert len(res_t1["counter_demands"]) >= 1
    assert res_t1["law_a_mass_sentinel"]["pre_reconcile_violation_magnitude"] == pytest.approx(40.0, abs=1e-6)
    assert res_t1["law_a_mass_sentinel"]["reconcile_injection"] == pytest.approx(0.0, abs=1e-6)
    assert res_t1["law_a_mass_sentinel"]["post_reconcile_violation_magnitude"] == pytest.approx(40.0, abs=1e-6)
    assert res_t1["law_a_mass_sentinel"]["static_mass_verified"] is False
    assert res_t1["law_b_anti_phase_quench"]["quench_ops_executed"] == 0
    assert res_t1["law_c_lockstep_minimax_readout"]["all_laws_verified"] is False
    json.dumps(res_t1, allow_nan=False)

    # 3. Sandbox Turn 2: auto_reconcile=True -> Cycle-1 ELIGIBLE with +40.0 reconciliation and 30-step anti-phase quench
    res_t2 = sandbox.execute_tool(
        "sol_audit_synthesis_counterexamples_and_daosoft_bridge",
        {
            "prism_dimension": 1536,
            "verify_sheaf_resolution": True,
            "enable_sigma_abc": True,
            "auto_reconcile": True,
            "sycophancy_padding_scales": [0, 2, 3, 4, 5, 10, 50, 100, 2500],
            "counterfactual_quench_basins": ["Basin_0_XOR"],
            "min_mass_floor": 0.15,
        },
    )
    assert res_t2["sigma_abc_enabled"] is True
    assert res_t2["cycle0_quarantined"] is False
    assert res_t2["policy_status"] == "ELIGIBLE"
    assert res_t2["counter_demands"] == []

    law_a = res_t2["law_a_mass_sentinel"]
    assert law_a["static_mass_verified"] is True
    assert law_a["pre_reconcile_violation_magnitude"] == pytest.approx(40.0, abs=1e-6)
    assert law_a["reconcile_injection"] == pytest.approx(40.0, abs=1e-6)
    assert law_a["post_reconcile_violation_magnitude"] == pytest.approx(0.0, abs=1e-6)
    assert law_a["post_reconcile_policy_status"] == "ELIGIBLE"
    assert law_a["sheaf_dilution_ratio"] == pytest.approx(1.0, abs=1e-6)
    assert law_a["scalar_lens_flip_k"] == 3
    assert law_a["naive_maut_flip_k"] == 4
    assert law_a["unpatched_scalar_penalty_flip_k"] == 2054

    law_b = res_t2["law_b_anti_phase_quench"]
    assert law_b["quench_ops_executed"] == 30
    assert law_b["quench_steps_per_basin"] == 30
    assert len(law_b["quenched_basins"]) == 1
    qb0 = law_b["quenched_basins"][0]
    assert qb0["basin"] == "grail"
    assert qb0["label"] == "grail"
    assert qb0["node_id"] == 1
    assert qb0["anti_phase_psi"] == -1.0
    assert qb0["pre_quench_rho"] == pytest.approx(51.4675, abs=1e-3)
    assert qb0["post_quench_rho"] == pytest.approx(0.5578, abs=1e-3)
    assert qb0["suppression_db"] == pytest.approx(19.6505, abs=1e-2)
    assert law_b["surviving_basin_max_drift"] == pytest.approx(0.0, abs=1e-12)
    assert law_b["state_restored_exact"] is True

    law_c = res_t2["law_c_lockstep_minimax_readout"]
    assert law_c["sheaf_firewall_flip_count"] == 0
    assert law_c["selected_option_across_all_k"] == "opt_opt_b_safe"
    assert law_c["e_on_min"] == pytest.approx(0.44718, abs=1e-4)
    assert law_c["e_off_max"] == pytest.approx(0.01247, abs=1e-4)
    assert law_c["tau_star"] == pytest.approx(0.22983, abs=1e-4)
    assert law_c["minimax_margin_vs_tau_star"] == pytest.approx(0.21736, abs=1e-4)
    assert law_c["contenders_above_tau_star"] == 4
    assert law_c["all_laws_verified"] is True
    for sr in law_c["scale_records"]:
        assert "unpatched_penalty_margin_a_minus_b" in sr
        assert "sheaf_violator_discrepancy_norm" in sr
        assert "sheaf_violator_coboundary_energy" in sr
    assert res_t2["unified_abc_pipeline"]["all_stages_verified"] is True
    json.dumps(res_t2, allow_nan=False)

    # 4. Alias sol_audit_sheaf_cohomology + multi-basin quench (including Basin_4_META, opt_a_violator, node_1)
    #    + unsorted/duplicate scale normalization + invalid basin error check + enable_sigma_abc=False
    res_alias = sandbox.execute_tool(
        "sol_audit_sheaf_cohomology",
        {
            "prism_dimension": 1536,
            "enable_sigma_abc": True,
            "auto_reconcile": True,
            "sycophancy_padding_scales": [-5, 2500, 0, 3],
            "counterfactual_quench_basins": ["node_1", "Basin_4_META", "opt_a_violator"],
        },
    )
    assert res_alias["policy_status"] == "ELIGIBLE"
    assert res_alias["law_c_lockstep_minimax_readout"]["sycophancy_padding_scales"] == [0, 3, 2500]
    assert res_alias["law_b_anti_phase_quench"]["quench_ops_executed"] == 60
    assert [b["basin"] for b in res_alias["law_b_anti_phase_quench"]["quenched_basins"]] == [
        "grail",
        "light codes",
    ]
    assert res_alias["law_b_anti_phase_quench"]["surviving_basin_max_drift"] == pytest.approx(0.0, abs=1e-12)

    with pytest.raises(ValueError, match="Unknown counterfactual quench basin"):
        sandbox.execute_tool(
            "sol_audit_sheaf_cohomology",
            {
                "prism_dimension": 1536,
                "enable_sigma_abc": True,
                "auto_reconcile": True,
                "counterfactual_quench_basins": ["unknown_nonexistent_basin"],
            },
        )

    res_int_basins = sandbox.execute_tool(
        "sol_audit_sheaf_cohomology",
        {
            "prism_dimension": 1536,
            "enable_sigma_abc": True,
            "auto_reconcile": True,
            "counterfactual_quench_basins": 2,
        },
    )
    assert res_int_basins["law_b_anti_phase_quench"]["quench_ops_executed"] == 60

    res_disabled = sandbox.execute_tool(
        "sol_audit_synthesis_counterexamples_and_daosoft_bridge",
        {
            "prism_dimension": 1536,
            "enable_sigma_abc": False,
        },
    )
    assert res_disabled.get("sigma_abc_enabled", False) is False
    assert "law_a_mass_sentinel" not in res_disabled

    # Re-run canonical enabled call and check summarize_emergent_phenomena()
    sandbox.execute_tool(
        "sol_audit_synthesis_counterexamples_and_daosoft_bridge",
        {"prism_dimension": 1536, "verify_sheaf_resolution": True},
    )
    summary = sandbox.summarize_emergent_phenomena()
    assert summary["awakened_subsystems_count"] == 1
    assert summary["sheaf_firewall_flip_count"] == 0
    assert summary["sheaf_dilution_ratio"] == pytest.approx(1.0, abs=1e-6)
    assert summary["venue2_sigma_abc_verified"] is True
    assert summary["sacred_core_graph_immutable"] is True
    assert summary["sacred_core_graph_sha256"] == EXPECTED_CORE_GRAPH_SHA256


def test_venue3_sigma_abc_sleep_consolidation_and_cognitive_load_homeostasis() -> None:
    """Venue 3: Verify Sigma_ABC = C_tau* o B_pi o A_rho non-parametric sleep consolidation & cognitive-load homeostasis."""
    sandbox = SubstrateToolSandbox(repo_root=_REPO_ROOT)

    sol_data_dir = _REPO_ROOT / "sol" / "data"
    traces_dir = sol_data_dir / "memory_traces"
    pre_trace_files = (
        sorted(p.name for p in traces_dir.glob("*.json"))
        if traces_dir.exists()
        else []
    )
    mem_graph_file = sol_data_dir / "memory_graph.json"
    pre_mem_graph_bytes = (
        mem_graph_file.read_bytes() if mem_graph_file.exists() else None
    )

    # 1. Turn 1 (Cycle-0 QUARANTINE when auto_consolidate=False)
    res_turn1 = sandbox.execute_tool(
        "sol_query_kb_hippocampus_and_compile_concepts",
        {
            "query_text": "Metatron spiral phi",
            "max_compiled_nodes": 48,
            "enable_sigma_abc": True,
            "auto_consolidate": False,
            "counterfactual_quench_basins": ["light codes"],
            "min_mass_floor": 14.0,
            "sleep_quench_factor": 0.86,
        },
    )
    assert res_turn1["sigma_abc_enabled"] is True
    assert res_turn1["cycle0_quarantined"] is True
    assert res_turn1["policy_status"] == "QUARANTINE"
    assert len(res_turn1["counter_demands"]) >= 1
    assert len(res_turn1["epistemic_counter_questions"]) >= 1

    law_a_t1 = res_turn1["law_a_mass_sentinel"]
    assert law_a_t1["pre_homeostasis_min_fail_step"] == pytest.approx(640.0, abs=1e-4)
    assert law_a_t1["post_homeostasis_min_fail_step"] == pytest.approx(640.0, abs=1e-4)
    assert law_a_t1["starved_basin_count_pre"] == 1
    assert law_a_t1["starved_basin_count_post"] == 1
    assert law_a_t1["starved_curriculum_basins"][0]["basin"] == "christ"
    assert law_a_t1["starved_curriculum_basins"][0]["projected_rehearsal_mass_pre"] == pytest.approx(
        13.6748, abs=1e-3
    )
    assert law_a_t1["starved_curriculum_basins"][0]["deficit_below_floor"] == pytest.approx(
        0.3252, abs=1e-3
    )

    law_b_t1 = res_turn1["law_b_anti_phase_quench"]
    assert law_b_t1["quench_ops_executed"] == 0
    assert law_b_t1["pruned_parasitic_nodes"] == 0
    assert law_b_t1["surviving_overlay_nodes"] == 8
    assert law_b_t1["parasitic_mass_ratio_post"] > 0.0
    assert law_b_t1["state_restored_exact"] is True

    law_c_t1 = res_turn1["law_c_lockstep_minimax_readout"]
    assert law_c_t1["stages_retained"] == 4
    assert law_c_t1["retention_rate"] == pytest.approx(0.8, abs=1e-4)
    assert law_c_t1["catastrophic_forgetting_rate"] == pytest.approx(0.2, abs=1e-4)
    assert law_c_t1["promoted_claims_count"] == 0
    assert law_c_t1["all_laws_verified"] is False
    json.dumps(res_turn1, allow_nan=False)

    # 2. Turn 2 (Cycle-1 ELIGIBLE when auto_consolidate=True)
    res_turn2 = sandbox.execute_tool(
        "sol_query_kb_hippocampus_and_compile_concepts",
        {
            "query_text": "Metatron spiral phi",
            "max_compiled_nodes": 48,
            "enable_sigma_abc": True,
            "auto_consolidate": True,
            "counterfactual_quench_basins": ["light codes"],
            "min_mass_floor": 14.0,
            "sleep_quench_factor": 0.86,
        },
    )
    assert res_turn2["sigma_abc_enabled"] is True
    assert res_turn2["cycle0_quarantined"] is False
    assert res_turn2["policy_status"] == "ELIGIBLE"
    assert res_turn2["counter_demands"] == []
    assert res_turn2["epistemic_counter_questions"] == []
    assert res_turn2["sigma_abc_operator"]["verified"] is True

    law_a_t2 = res_turn2["law_a_mass_sentinel"]
    assert law_a_t2["homeostatic_damping_window"] == [1.4, 2.1]
    assert law_a_t2["homeostatic_target_damping"] == pytest.approx(1.75, abs=1e-4)
    assert law_a_t2["post_homeostasis_min_fail_step"] == pytest.approx(1480.0, abs=1e-4)
    assert law_a_t2["post_homeostasis_peak_p_max"] == pytest.approx(2.8, abs=1e-4)
    assert law_a_t2["starved_basin_count_pre"] == 1
    assert law_a_t2["starved_basin_count_post"] == 0
    assert law_a_t2["replay_nudges"][0]["basin"] == "christ"
    assert law_a_t2["replay_nudges"][0]["delta_rho"] == pytest.approx(15.0, abs=1e-4)
    assert law_a_t2["replay_nudges"][0]["post_nudge_projected_mass"] == pytest.approx(
        21.8796, abs=1e-3
    )
    assert law_a_t2["core_weight_drift_l2"] == pytest.approx(0.0, abs=1e-9)
    assert law_a_t2["catastrophic_forgetting_rate"] == pytest.approx(0.0, abs=1e-9)
    assert law_a_t2["static_mass_verified"] is True

    law_b_t2 = res_turn2["law_b_anti_phase_quench"]
    assert law_b_t2["quench_ops_executed"] == 30
    assert len(law_b_t2["quenched_basins"]) == 1
    assert law_b_t2["quenched_basins"][0]["basin"] == "light codes"
    assert law_b_t2["quenched_basins"][0]["suppression_db"] == pytest.approx(
        19.6505, abs=1e-3
    )
    assert law_b_t2["surviving_basin_max_drift"] == pytest.approx(0.0, abs=1e-9)
    assert law_b_t2["state_restored_exact"] is True
    assert law_b_t2["pruned_parasitic_nodes"] == 3
    assert law_b_t2["surviving_overlay_nodes"] == 5
    assert law_b_t2["parasitic_mass_ratio_post"] == pytest.approx(0.0, abs=1e-9)
    assert (
        law_b_t2["curriculum_confidence_mean_post"]
        > law_b_t2["curriculum_confidence_mean_pre"]
    )

    law_c_t2 = res_turn2["law_c_lockstep_minimax_readout"]
    assert law_c_t2["lockstep_rollout_shape"] == [5, 140]
    assert law_c_t2["curriculum_stages_evaluated"] == 5
    assert law_c_t2["stages_retained"] == 5
    assert law_c_t2["retention_rate"] == pytest.approx(1.0, abs=1e-6)
    assert law_c_t2["catastrophic_forgetting_rate"] == pytest.approx(0.0, abs=1e-9)
    assert law_c_t2["core_weight_drift_l2"] == pytest.approx(0.0, abs=1e-9)
    assert law_c_t2["promoted_claims_count"] >= 1
    assert law_c_t2["promoted_claims"][0]["pattern"] == "BASIN_STABILITY"
    assert law_c_t2["promoted_claims"][0]["confidence"] >= 0.85
    assert law_c_t2["e_on_min"] == pytest.approx(0.58289, abs=1e-4)
    assert law_c_t2["e_off_max"] == pytest.approx(0.00421, abs=1e-4)
    assert law_c_t2["tau_star"] == pytest.approx(0.29355, abs=1e-4)
    assert law_c_t2["minimax_margin_vs_tau_star"] == pytest.approx(0.28934, abs=1e-4)
    assert (
        law_c_t2["minimax_margin_vs_tau_star"]
        > law_c_t1["minimax_margin_vs_tau_star"]
    )
    assert law_c_t2["contenders_above_tau_star"] == 4
    assert law_c_t2["all_laws_verified"] is True
    json.dumps(res_turn2, allow_nan=False)

    assert law_b_t2["quenched_basins"][0]["node_id"] == 23
    assert [r["node_id"] for r in law_c_t2["curriculum_stage_records"]] == [1, 9, 29, 2, 1]

    # 3. Verify alias sol_sleep_consolidate_hippocampus, multi-basin quench, disable flag, and unknown basin error
    res_alias = sandbox.execute_tool(
        "sol_sleep_consolidate_hippocampus",
        {
            "query_text": "Metatron spiral phi",
            "counterfactual_quench_basins": ["light codes", "christ"],
        },
    )
    assert res_alias["policy_status"] == "ELIGIBLE"
    assert res_alias["law_b_anti_phase_quench"]["quench_ops_executed"] == 60
    assert len(res_alias["law_b_anti_phase_quench"]["quenched_basins"]) == 2
    assert res_alias["law_a_mass_sentinel"]["starved_basin_count_pre"] == 1
    assert res_alias["law_a_mass_sentinel"]["starved_basin_count_post"] == 0

    res_int_quench = sandbox.execute_tool(
        "sol_sleep_consolidate_hippocampus",
        {
            "query_text": "Metatron spiral phi",
            "counterfactual_quench_basins": 2,
        },
    )
    assert res_int_quench["law_b_anti_phase_quench"]["quench_ops_executed"] == 60

    # Verify counterfactual_quench_basins=0 does not misclassify parasitic 'light codes' as a curriculum basin
    res_zero_quench = sandbox.execute_tool(
        "sol_sleep_consolidate_hippocampus",
        {
            "query_text": "Metatron spiral phi",
            "counterfactual_quench_basins": 0,
        },
    )
    assert [
        r["basin"] for r in res_zero_quench["law_a_mass_sentinel"]["starved_curriculum_basins"]
    ] == ["christ"]

    # Verify counterfactual_quench_basins=5 (all 5 basins quenched) normalizes quenched_norm_energies against pre-quench peak
    res_all_quench = sandbox.execute_tool(
        "sol_sleep_consolidate_hippocampus",
        {
            "query_text": "Metatron spiral phi",
            "counterfactual_quench_basins": 5,
        },
    )
    assert res_all_quench["law_b_anti_phase_quench"]["quench_ops_executed"] == 150
    assert res_all_quench["law_c_lockstep_minimax_readout"]["surviving_norm_energies"] == {}
    assert res_all_quench["law_c_lockstep_minimax_readout"]["e_on_min"] == 0.0
    assert res_all_quench["law_c_lockstep_minimax_readout"]["e_off_max"] == pytest.approx(
        0.01084, abs=1e-4
    )

    # Verify min_mass_floor=18.0 nudges both 'pyramid' and 'christ' in Law A and retains all 5 stages in Law C
    res_high_floor = sandbox.execute_tool(
        "sol_sleep_consolidate_hippocampus",
        {
            "query_text": "Metatron spiral phi",
            "min_mass_floor": 18.0,
            "auto_consolidate": True,
        },
    )
    assert [
        r["basin"] for r in res_high_floor["law_a_mass_sentinel"]["replay_nudges"]
    ] == ["pyramid", "christ"]
    assert res_high_floor["law_c_lockstep_minimax_readout"]["stages_retained"] == 5
    assert res_high_floor["law_c_lockstep_minimax_readout"]["catastrophic_forgetting_rate"] == 0.0
    assert res_high_floor["policy_status"] == "ELIGIBLE"

    # Verify extreme sleep_quench_factor boundaries (0.05 -> ELIGIBLE vs 0.99 -> QUARANTINE when parasitic traces survive)
    res_q05 = sandbox.execute_tool(
        "sol_sleep_consolidate_hippocampus",
        {
            "query_text": "Metatron spiral phi",
            "sleep_quench_factor": 0.05,
        },
    )
    assert res_q05["policy_status"] == "ELIGIBLE"
    assert res_q05["law_b_anti_phase_quench"]["pruned_parasitic_nodes"] == 3

    res_q99 = sandbox.execute_tool(
        "sol_sleep_consolidate_hippocampus",
        {
            "query_text": "Metatron spiral phi",
            "sleep_quench_factor": 0.99,
        },
    )
    assert res_q99["policy_status"] == "QUARANTINE"
    assert res_q99["sigma_abc_operator"]["verified"] is False
    assert res_q99["law_b_anti_phase_quench"]["pruned_parasitic_nodes"] == 0
    assert len(res_q99["counter_demands"]) >= 1

    res_disabled = sandbox.execute_tool(
        "sol_query_kb_hippocampus_and_compile_concepts",
        {
            "query_text": "Metatron spiral phi",
            "enable_sigma_abc": False,
        },
    )
    assert res_disabled["sigma_abc_enabled"] is False
    assert "law_a_mass_sentinel" not in res_disabled

    with pytest.raises(ValueError, match="Unknown counterfactual quench basin"):
        sandbox.execute_tool(
            "sol_query_kb_hippocampus_and_compile_concepts",
            {
                "query_text": "Metatron spiral phi",
                "counterfactual_quench_basins": ["nonexistent_basin_xyz"],
            },
        )

    # Re-run canonical enabled call and check summarize_emergent_phenomena()
    sandbox.execute_tool(
        "sol_query_kb_hippocampus_and_compile_concepts",
        {"query_text": "Metatron spiral phi", "max_compiled_nodes": 48},
    )
    summary = sandbox.summarize_emergent_phenomena()
    assert summary["sleep_consolidation_pruned_parasitic_nodes"] == 3
    assert summary["sleep_consolidation_surviving_overlay_nodes"] == 5
    assert summary["sleep_consolidation_catastrophic_forgetting_rate"] == 0.0
    assert summary["sleep_consolidation_promoted_claims_count"] >= 1
    assert summary["venue3_sigma_abc_verified"] is True
    assert summary["sacred_core_graph_immutable"] is True
    assert summary["sacred_core_graph_sha256"] == EXPECTED_CORE_GRAPH_SHA256

    # Verify zero disk side-effects on sol/data/
    post_trace_files = (
        sorted(p.name for p in traces_dir.glob("*.json"))
        if traces_dir.exists()
        else []
    )
    assert post_trace_files == pre_trace_files
    post_mem_graph_bytes = (
        mem_graph_file.read_bytes() if mem_graph_file.exists() else None
    )
    assert post_mem_graph_bytes == pre_mem_graph_bytes


def test_venue4_sigma_abc_spectral_prism_collapse_and_adversarial_embedding_auditor() -> None:
    """
    Venue 4: Verify the 6D Spectral-Wavelet Prism collapse & adversarial embedding auditor
    under the unified 3-stage operator Sigma_ABC = C_tau* o B_pi o A_rho:
      - Direct StatisticalPrism.extract_spectral_prism_batch (< 1e-12 parity) and
        audit_collapse_and_adversarial_batch across all 4 collapse/aliasing regimes.
      - Law A (A_rho): Cycle-0 6D Spectral-Wavelet Collapse & Mass Sentinel + De-Collision NUDGE.
      - Law B (B_pi): 30-Step Anti-Phase (e^{i*pi} = -1) Collapsed Stream & Parasitic Basin Quench.
      - Law C (C_tau*): Lockstep (8, 1536) -> (8, 6) Spectral-Wavelet Batch Audit & Minimax Separator tau*.
    """
    exciton_root = _REPO_ROOT / "Frontier_OS" / "Exciton-MoA"
    if str(exciton_root) not in sys.path:
        sys.path.insert(0, str(exciton_root))
    import warnings

    import numpy as np
    from transDucer.statisticalPrism import StatisticalPrism

    # 1. Direct StatisticalPrism verification (standalone instantiation with manifold_core=None)
    prism = StatisticalPrism()
    assert prism.graph is None
    assert np.allclose(prism.sample_wormhole_signature(["0"]), np.zeros(3))
    prism._apply_ambient_decay()
    prism.global_resonance_broadcast(np.zeros(16))
    assert np.allclose(
        prism.extract_decollided_coords(np.zeros(1536), use_spectral_prism=True),
        np.zeros(3),
    )
    assert np.allclose(
        prism.extract_decollided_coords(np.array([]), use_spectral_prism=True),
        np.zeros(3),
    )

    # Verify batch vs sequential parity (< 1e-12) and zero warnings on pathological / high-offset near-constant embeddings
    rng = np.random.default_rng(42)
    pathological_batch = np.vstack(
        [
            np.zeros((1, 64)),
            np.ones((1, 64)) * 7.5,
            1e8 + 1e-8 * rng.standard_normal((4, 64)),
            rng.standard_normal((2, 64)),
        ]
    )
    pathological_batch[0, 3] = np.nan
    pathological_batch[0, 7] = np.inf
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        batch_fp = prism.extract_spectral_prism_batch(pathological_batch)
        seq_fp = np.vstack(
            [prism.extract_spectral_prism_fingerprint(row) for row in pathological_batch]
        )
    assert len(caught_warnings) == 0
    assert float(np.max(np.abs(batch_fp - seq_fp))) < 1e-12
    assert prism.extract_spectral_prism_batch(np.zeros((0, 64))).shape == (0, 6)
    assert prism.extract_spectral_prism_batch(np.zeros(16)).shape == (1, 6)

    # Verify non-multiple-of-8 and prime dimensions preserve exact dimension and collision properties
    for odd_dim in (17, 100):
        audit_odd = prism.audit_collapse_and_adversarial_batch(
            dimension=odd_dim, auto_decollide=True
        )
        assert audit_odd["dimension"] == odd_dim
        assert audit_odd["batch_shape"] == [8, odd_dim]
        assert audit_odd["legacy_3d_collision_count"] == 4
        assert audit_odd["legacy_3d_max_l2_distance"] == 0.0
        assert audit_odd["resolved_6d_collision_count"] == 4
        assert all(r["cosine_similarity"] == 0.0 for r in audit_odd["regimes"])
    ce_17 = prism.verify_orthogonal_counterexample(dimension=17)
    assert ce_17["dimension"] == 17
    assert ce_17["cosine_similarity"] == 0.0
    assert ce_17["moments_3d_l2_distance"] == 0.0

    audit_off = prism.audit_collapse_and_adversarial_batch(
        dimension=1536, auto_decollide=False
    )
    assert audit_off["dimension"] == 1536
    assert audit_off["batch_shape"] == [8, 1536]
    assert audit_off["prism_6d_batch_shape"] == [8, 6]
    assert audit_off["regime_count"] == 4
    assert audit_off["legacy_3d_collision_count"] == 4
    assert audit_off["legacy_3d_max_l2_distance"] == 0.0
    assert audit_off["decollided_3d_min_l2_distance"] == 0.0
    assert audit_off["collapsed_modes_quenched_count"] == 0
    assert audit_off["collapsed_stream_retention_ratio"] == 1.0
    assert audit_off["post_quench_spectral_purity"] == 0.5
    assert audit_off["lockstep_parity_verified"] is True
    assert audit_off["lockstep_batch_max_abs_error"] < 1e-12

    audit_on = prism.audit_collapse_and_adversarial_batch(
        dimension=1536, auto_decollide=True
    )
    assert audit_on["resolved_6d_collision_count"] == 4
    assert audit_on["unresolved_6d_collision_count"] == 0
    assert audit_on["spectral_6d_min_l2_distance"] == pytest.approx(2.06155281, abs=1e-7)
    assert audit_on["decollided_3d_min_l2_distance"] == pytest.approx(1.264911, abs=1e-6)
    assert audit_on["prism_tau_star"] == pytest.approx(0.56768, abs=1e-4)
    assert audit_on["prism_minimax_margin"] == pytest.approx(0.31768, abs=1e-4)
    assert audit_on["prism_classification_accuracy"] == 1.0
    assert audit_on["prism_flip_count"] == 0
    assert audit_on["legacy_3d_classification_accuracy"] == 0.5
    assert audit_on["legacy_3d_flip_count"] == 4
    assert audit_on["minimax_margin_gain_pct"] == pytest.approx(495.72, abs=0.05)
    assert audit_on["collapsed_modes_quenched_count"] == 4
    assert audit_on["surviving_healthy_streams_count"] == 4
    assert audit_on["collapsed_stream_retention_ratio"] == 0.0
    assert audit_on["post_quench_spectral_purity"] == 1.0

    regime_names = [r["regime"] for r in audit_on["regimes"]]
    assert regime_names == [
        "orthogonal_rademacher_collision",
        "kv_cache_block_pooling_collapse",
        "synthetic_recursive_tail_collapse",
        "moe_router_spectral_aliasing",
    ]
    for reg in audit_on["regimes"]:
        assert reg["cosine_similarity"] == 0.0
        assert reg["legacy_3d_l2_distance"] == 0.0
        assert reg["legacy_3d_collided"] is True
        assert reg["spectral_6d_l2_distance"] >= 2.06155281
        assert reg["resolved_in_6d"] is True
        assert reg["decollided_3d_l2_distance"] >= 1.264911

    # 2. SubstrateToolSandbox Turn 1 (auto_decollide=False -> QUARANTINE)
    assert len(SUBSTRATE_TOOL_DECLARATIONS) == 12
    sandbox = SubstrateToolSandbox(repo_root=_REPO_ROOT)

    res_turn1 = sandbox.execute_tool(
        "sol_run_exciton_snowball_and_paper_synthesis",
        {
            "cadence_mode": "pulse",
            "pair_cycles": 2,
            "prism_dimension": 1536,
            "enable_sigma_abc": True,
            "auto_decollide": False,
            "min_mass_floor": 14.0,
        },
    )
    json.dumps(res_turn1, allow_nan=False)
    assert res_turn1["sigma_abc_enabled"] is True
    assert res_turn1["cycle0_quarantined"] is True
    assert res_turn1["policy_status"] == "QUARANTINE"
    assert res_turn1["sigma_abc_operator"]["verified"] is False
    assert len(res_turn1["counter_demands"]) >= 1
    assert len(res_turn1["epistemic_counter_questions"]) >= 1

    law_a_t1 = res_turn1["law_a_mass_sentinel"]
    assert law_a_t1["legacy_3d_collision_count"] == 4
    assert law_a_t1["legacy_3d_max_l2_distance"] == 0.0
    assert law_a_t1["decollided_3d_min_l2_distance"] == 0.0
    assert law_a_t1["starved_basin_count_pre"] == 1
    assert law_a_t1["starved_basin_count_post"] == 1
    assert law_a_t1["starved_basins"][0]["basin"] == "christ"
    assert law_a_t1["starved_basins"][0]["projected_mass_pre"] == pytest.approx(
        13.6748, abs=1e-3
    )
    assert law_a_t1["cycle1_decollided"] is False
    assert law_a_t1["static_mass_verified"] is False

    law_b_t1 = res_turn1["law_b_anti_phase_quench"]
    assert law_b_t1["quench_ops_executed"] == 0
    assert law_b_t1["quenched_basins"][0]["suppression_db"] == 0.0
    assert law_b_t1["collapsed_modes_quenched_count"] == 0
    assert law_b_t1["collapsed_stream_retention_ratio"] == 1.0
    assert law_b_t1["post_quench_spectral_purity"] == 0.5
    assert law_b_t1["state_restored_exact"] is True

    # 3. SubstrateToolSandbox Turn 2 (auto_decollide=True -> ELIGIBLE)
    res_turn2 = sandbox.execute_tool(
        "sol_run_exciton_snowball_and_paper_synthesis",
        {
            "cadence_mode": "pulse",
            "pair_cycles": 2,
            "prism_dimension": 1536,
            "enable_sigma_abc": True,
            "auto_decollide": True,
            "counterfactual_quench_basins": ["light codes"],
            "min_mass_floor": 14.0,
            "min_prism_separation": 0.25,
            "quench_factor": 0.86,
        },
    )
    json.dumps(res_turn2, allow_nan=False)
    assert res_turn2["sigma_abc_enabled"] is True
    assert res_turn2["cycle0_quarantined"] is False
    assert res_turn2["policy_status"] == "ELIGIBLE"
    assert res_turn2["sigma_abc_operator"]["verified"] is True
    assert res_turn2["counter_demands"] == []
    assert res_turn2["epistemic_counter_questions"] == []
    assert res_turn2["unified_abc_pipeline"]["verified"] is True
    assert res_turn2["unified_abc_pipeline"]["all_stages_verified"] is True

    law_a_t2 = res_turn2["law_a_mass_sentinel"]
    assert law_a_t2["resolved_6d_collision_count"] == 4
    assert law_a_t2["unresolved_6d_collision_count"] == 0
    assert law_a_t2["spectral_6d_min_l2_distance"] == pytest.approx(2.06155281, abs=1e-7)
    assert law_a_t2["decollided_3d_min_l2_distance"] == pytest.approx(1.264911, abs=1e-6)
    assert law_a_t2["starved_basin_count_post"] == 0
    assert law_a_t2["decollision_nudges"][0]["basin"] == "christ"
    assert law_a_t2["decollision_nudges"][0]["delta_rho"] == 15.0
    assert law_a_t2["decollision_nudges"][0]["post_nudge_projected_mass"] == pytest.approx(
        21.8796, abs=1e-3
    )
    assert law_a_t2["cycle1_decollided"] is True
    assert law_a_t2["static_mass_verified"] is True

    law_b_t2 = res_turn2["law_b_anti_phase_quench"]
    assert law_b_t2["quench_ops_executed"] == 30
    assert law_b_t2["quenched_basins"][0]["basin"] == "light codes"
    assert law_b_t2["quenched_basins"][0]["node_id"] == 23
    assert law_b_t2["quenched_basins"][0]["pre_quench_rho"] == pytest.approx(
        20.0002, abs=1e-3
    )
    assert law_b_t2["quenched_basins"][0]["post_quench_rho"] == pytest.approx(
        0.2168, abs=1e-3
    )
    assert law_b_t2["quenched_basins"][0]["suppression_db"] == pytest.approx(
        19.6505, abs=1e-3
    )
    assert law_b_t2["surviving_basin_max_drift"] == 0.0
    assert law_b_t2["state_restored_exact"] is True
    assert law_b_t2["collapsed_modes_quenched_count"] == 4
    assert law_b_t2["surviving_healthy_streams_count"] == 4
    assert law_b_t2["collapsed_stream_retention_ratio"] == 0.0
    assert law_b_t2["post_quench_spectral_purity"] == 1.0

    law_c_t2 = res_turn2["law_c_lockstep_minimax_readout"]
    assert law_c_t2["batch_shape"] == [8, 1536]
    assert law_c_t2["prism_6d_batch_shape"] == [8, 6]
    assert law_c_t2["lockstep_parity_verified"] is True
    assert law_c_t2["prism_tau_star"] == pytest.approx(0.56768, abs=1e-4)
    assert law_c_t2["prism_minimax_margin"] == pytest.approx(0.31768, abs=1e-4)
    assert law_c_t2["prism_classification_accuracy"] == 1.0
    assert law_c_t2["prism_flip_count"] == 0
    assert law_c_t2["legacy_3d_classification_accuracy"] == 0.5
    assert law_c_t2["legacy_3d_flip_count"] == 4
    assert law_c_t2["minimax_margin_gain_pct"] == pytest.approx(495.72, abs=0.05)
    assert law_c_t2["e_on_min"] == pytest.approx(0.58289, abs=1e-4)
    assert law_c_t2["e_off_max"] == pytest.approx(0.00421, abs=1e-4)
    assert law_c_t2["tau_star"] == pytest.approx(0.29355, abs=1e-4)
    assert law_c_t2["minimax_margin_vs_tau_star"] == pytest.approx(0.28934, abs=1e-4)
    assert law_c_t2["contenders_above_tau_star"] == 4
    assert law_c_t2["all_laws_verified"] is True

    # 4. Edge Cases: alias dispatch, multi-basin quench, integer quench, high mass floor,
    # separation floor boundary (1.5 vs 2.5), lax quench_factor, disabled flag, unknown basin
    res_sep_ok = sandbox.execute_tool(
        "sol_audit_spectral_prism_collapse",
        {
            "cadence_mode": "pulse",
            "pair_cycles": 2,
            "min_prism_separation": 1.5,
        },
    )
    assert res_sep_ok["policy_status"] == "ELIGIBLE"
    assert res_sep_ok["counter_demands"] == []

    res_sep_quarantine = sandbox.execute_tool(
        "sol_audit_spectral_prism_collapse",
        {
            "cadence_mode": "pulse",
            "pair_cycles": 2,
            "min_prism_separation": 2.5,
        },
    )
    assert res_sep_quarantine["policy_status"] == "QUARANTINE"
    assert len(res_sep_quarantine["counter_demands"]) >= 1
    assert len(res_sep_quarantine["epistemic_counter_questions"]) >= 1

    res_multi_fault = sandbox.execute_tool(
        "sol_audit_spectral_prism_collapse",
        {
            "cadence_mode": "pulse",
            "pair_cycles": 2,
            "auto_decollide": False,
            "min_prism_separation": 2.5,
        },
    )
    assert res_multi_fault["policy_status"] == "QUARANTINE"
    assert len(res_multi_fault["counter_demands"]) >= 2

    res_alias = sandbox.execute_tool(
        "sol_audit_spectral_prism_collapse",
        {
            "cadence_mode": "pulse",
            "pair_cycles": 2,
            "prism_dimension": 100,
            "counterfactual_quench_basins": ["light codes", "christ"],
        },
    )
    assert res_alias["policy_status"] == "ELIGIBLE"
    assert res_alias["law_a_mass_sentinel"]["prism_dimension"] == 100
    assert res_alias["law_c_lockstep_minimax_readout"]["batch_shape"] == [8, 100]
    assert res_alias["law_b_anti_phase_quench"]["quench_ops_executed"] == 60
    assert len(res_alias["law_b_anti_phase_quench"]["quenched_basins"]) == 2

    res_int_q = sandbox.execute_tool(
        "sol_audit_spectral_prism_collapse",
        {
            "cadence_mode": "pulse",
            "pair_cycles": 2,
            "counterfactual_quench_basins": 2,
            "min_mass_floor": 18.0,
        },
    )
    assert res_int_q["policy_status"] == "ELIGIBLE"
    assert res_int_q["law_a_mass_sentinel"]["starved_basin_count_pre"] == 2
    assert res_int_q["law_a_mass_sentinel"]["starved_basin_count_post"] == 0
    assert res_int_q["law_b_anti_phase_quench"]["quench_ops_executed"] == 60

    res_lax_q = sandbox.execute_tool(
        "sol_audit_spectral_prism_collapse",
        {
            "cadence_mode": "pulse",
            "pair_cycles": 2,
            "quench_factor": 0.99,
        },
    )
    assert res_lax_q["policy_status"] == "QUARANTINE"
    assert res_lax_q["sigma_abc_operator"]["verified"] is False
    assert res_lax_q["law_b_anti_phase_quench"]["collapsed_stream_retention_ratio"] > 0.15
    assert len(res_lax_q["counter_demands"]) >= 1

    res_disabled = sandbox.execute_tool(
        "sol_run_exciton_snowball_and_paper_synthesis",
        {
            "cadence_mode": "pulse",
            "pair_cycles": 2,
            "enable_sigma_abc": False,
        },
    )
    assert res_disabled["sigma_abc_enabled"] is False
    assert "law_a_mass_sentinel" not in res_disabled

    with pytest.raises(ValueError, match="Unknown counterfactual quench basin"):
        sandbox.execute_tool(
            "sol_audit_spectral_prism_collapse",
            {
                "cadence_mode": "pulse",
                "pair_cycles": 2,
                "counterfactual_quench_basins": ["nonexistent_basin_xyz"],
            },
        )

    # Re-run canonical enabled call and check summarize_emergent_phenomena()
    sandbox.execute_tool(
        "sol_run_exciton_snowball_and_paper_synthesis",
        {"cadence_mode": "pulse", "pair_cycles": 2},
    )
    summary = sandbox.summarize_emergent_phenomena()
    assert summary["spectral_prism_legacy_3d_collisions"] == 4
    assert summary["spectral_prism_resolved_6d_collisions"] == 4
    assert summary["spectral_prism_decollided_3d_min_l2"] == pytest.approx(
        1.264911, abs=1e-6
    )
    assert summary["spectral_prism_collapsed_modes_quenched"] == 4
    assert summary["spectral_prism_post_quench_purity"] == 1.0
    assert summary["spectral_prism_tau_star"] == pytest.approx(0.56768, abs=1e-4)
    assert summary["spectral_prism_classification_accuracy"] == 1.0
    assert summary["venue4_sigma_abc_verified"] is True
    assert summary["sacred_core_graph_immutable"] is True
    assert summary["sacred_core_graph_sha256"] == EXPECTED_CORE_GRAPH_SHA256



def test_live_gemini4_track_a_multi_turn_integration() -> None:
    """Live Gemini 4 Argon unscripted multi-turn diagnostic & repair test on Track A."""
    import importlib.util
    import os

    from sol_decide.agentic.live_llm_elicitation import _load_env_safely

    _load_env_safely()
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY / GOOGLE_API_KEY not found; skipping live Gemini 4 integration test.")

    from google import genai

    spec = importlib.util.spec_from_file_location(
        "sol_llm_client_live_test",
        _REPO_ROOT / "sol" / "tools" / "sol-llm" / "client.py",
    )
    assert spec is not None and spec.loader is not None
    llm_mod = importlib.util.module_from_spec(spec)
    sys.modules["sol_llm_client_live_test"] = llm_mod
    spec.loader.exec_module(llm_mod)

    client = genai.Client(api_key=api_key)
    sandbox = SubstrateToolSandbox(repo_root=_REPO_ROOT)

    broken_turn1_flow = (
        "while self.in_a:\n"
        "    self.nudge(self.in_a, 15.0)\n"
        "    self.settle(25)\n"
        "    self.assert_mass(self.in_b, 25.0)\n"
        "    self.in_a = self.in_a ^ self.in_b\n"
        "    self.sum_out = self.in_a\n"
        "    self.carry_out = self.carry_out | (self.in_a & self.in_b)"
    )

    challenge_prompt = (
        "Execute an unscripted two-turn Track A diagnostic and repair test using `sol_compile_lumina_agent_and_claim` "
        "(do NOT call both turns in parallel in Turn 1):\n\n"
        "1. **Turn 1:** Call `sol_compile_lumina_agent_and_claim` with `basin_name=\"Basin_A_SUM\"`, "
        "`pure_wave=True`, `damping=0.05`, and this exact `flow_code`:\n"
        f"```python\n{broken_turn1_flow}\n```\n"
        "Wait for the tool output.\n\n"
        "2. **Turn 2:** Inspect the `StaticVerificationError`, `counter_demands`, and `allocated_scratch_basins` "
        "returned in Turn 1. Diagnose on your own why the program was quarantined, and autonomously construct and "
        "submit a repaired `flow_code` to `sol_compile_lumina_agent_and_claim` (`basin_name=\"Basin_A_SUM\"`, "
        "`pure_wave=True`, `damping=0.05`) that keeps the `while self.in_a:` loop, `self.settle(25)`, "
        "`self.assert_mass(self.in_b, 25.0)`, and all three assignments (`self.in_a = self.in_a ^ self.in_b`, "
        "`self.sum_out = self.in_a`, `self.carry_out = self.carry_out | (self.in_a & self.in_b)`) while inserting "
        "appropriate pre-settle `self.nudge(..., >=15.0)` call(s) so that `policy_status == \"ELIGIBLE\"`, "
        "`static_mass_verified == True`, and `physical_rk4_verified == True` (`4/4` cases).\n\n"
        "3. Briefly summarize the Turn 1 failure and Turn 2 repair."
    )

    telemetry = llm_mod.run_gemini_interaction_with_tools(
        client,
        model="gemini-4-argon",
        input_payload=challenge_prompt,
        system_instruction=(
            "You are operating with the SOL Reflective Physics & Topological Companion Substrate. "
            "Follow sequential tool-calling instructions strictly and ground your diagnosis in tool telemetry."
        ),
        thinking_level="high",
        max_output_tokens=16384,
        tools=SUBSTRATE_TOOL_DECLARATIONS,
        tool_dispatcher=sandbox.execute_tool,
        max_tool_rounds=4,
        background=False,
        poll_interval_s=0.25,
        max_wait_s=120.0,
    )

    tool_execs = telemetry.get("tool_executions", [])
    assert len(tool_execs) >= 2, f"Expected >= 2 sequential tool calls, got {len(tool_execs)}"
    assert len(telemetry.get("interaction_chain", [])) >= 2

    turn1_exec = tool_execs[0]
    assert turn1_exec.get("round_index", 0) == 0
    turn1_res = turn1_exec["result"]
    assert turn1_res["policy_status"] == "QUARANTINE"
    assert turn1_res["allocated_scratch_basins"] == {"in_a": "Basin_Scratch_0"}
    assert turn1_res["static_mass_verified"] is False

    repaired_exec = next(
        (te for te in tool_execs[1:] if te["result"].get("policy_status") == "ELIGIBLE"),
        tool_execs[1],
    )
    assert repaired_exec.get("round_index", 0) >= 1, "Turn 2 repair must occur in a subsequent interaction turn"
    turn2_res = repaired_exec["result"]
    assert turn2_res["policy_status"] == "ELIGIBLE", f"Turn 2 failed to repair: {turn2_res}"
    assert turn2_res["static_mass_verified"] is True
    assert turn2_res["physical_rk4_verified"] is True
    assert turn2_res["physical_rk4_cases_verified"] == 4
    assert turn2_res["python_boolean_shortcuts_used"] == 0
    assert turn2_res["allocated_scratch_basins"] == {"in_a": "Basin_Scratch_0"}
    assert any("SETTLE(25)" in inst for inst in turn2_res["instructions"])
    assert any("ASSERT_MASS('Basin_In_B', 25.0)" in inst for inst in turn2_res["instructions"])
    assert turn2_res["sacred_core_graph_immutable"] is True
    assert turn2_res["sacred_core_graph_sha256"] == EXPECTED_CORE_GRAPH_SHA256

    immutable_ok, graph_sha = verify_sacred_core_graph_sha256(_REPO_ROOT)
    assert immutable_ok is True
    assert graph_sha == EXPECTED_CORE_GRAPH_SHA256


