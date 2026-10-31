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
from lumina_compiler import LuminaAgent, LuminaCompiler, StaticMassSentinel
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

