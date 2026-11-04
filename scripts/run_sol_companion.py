"""
SOL Reflective Physics & Topological Companion CLI (`scripts/run_sol_companion.py`)
===================================================================================
Pairs a live LLM (`gemini-4-argon`, `thinking_level="high"`) with the 12-tool
`SubstrateToolSandbox` (`sol-continuum`, `sol-holo`, `sol-decide`, `Frontier_OS/Exciton-MoA`,
`sol/tools/sol-hippocampus`, `sol/tools/sol-rsi`, and `synThesis`).

Zero background CPU burn when idle — executes on-demand stateful `interactions.create`
turns chained via `previous_interaction_id` with live `function_call` -> `function_result`
dispatch into the SOL substrate.

Usage:
  .\\.venv\\Scripts\\python.exe scripts/run_sol_companion.py
  .\\.venv\\Scripts\\python.exe scripts/run_sol_companion.py "Your scientific or architectural challenge..."
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
for sub_pkg in ("", "sol-holo", "sol-continuum", "sol-decide", "sol-edge/src", "sol-change", "Frontier_OS/Exciton-MoA"):
    pkg_dir = str((ROOT_DIR / sub_pkg).resolve()) if sub_pkg else str(ROOT_DIR)
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)

from sol_continuum.reflective_domain import (
    SACRED_DEFAULT_GRAPH_SHA256,
    verify_sacred_core_graph_sha256,
)
from sol_continuum.substrate_tools import (
    SUBSTRATE_TOOL_DECLARATIONS,
    SubstrateToolSandbox,
)
from sol_decide.agentic.live_llm_elicitation import _load_env_safely

LEDGER_JSONL_PATH = ROOT_DIR / "sol-holo" / "packets" / "companion_sessions_ledger.jsonl"
SESSIONS_DOCS_DIR = ROOT_DIR / "docs" / "companion_sessions"

DEFAULT_COMPANION_SYSTEM_INSTRUCTION = (
    "You are an AI operating with the SOL Reflective Physics & Topological Companion Substrate. "
    "Unlike a standard LLM that only predicts tokens, you have direct function-calling access to "
    "12 physical, topological, hippocampal, and sheaf-cohomological substrate tools. "
    "Before answering the user's challenge, invoke the relevant SOL substrate tools to empirically "
    "probe the 140-node manifold, query hippocampal memory/compile concepts, run RSI/LogosVM chambers, "
    "or audit for Vector 0 moment collisions and H^1 sheaf cohomological contradictions. "
    "Ground your final synthesis strictly in the numerical telemetry returned by the substrate."
)

DEFAULT_CHALLENGE = (
    "We are designing a multi-agent scientific reasoning and decision system, but standard LLM ensembles "
    "suffer from three fatal flaws: (1) stateless amnesia across sessions, (2) premature collapse onto a single "
    "hypothesis instead of holding counterfactuals in superposition, and (3) Vector 0 contradiction dilution "
    "(where averaging opposing agent vectors hides a topological conflict, or 4-moment summaries collide on "
    "orthogonal Rademacher signals).\n\n"
    "Use your SOL Companion Substrate tools right now to:\n"
    "1. Query the Hippocampus KB & compile concept topology (`sol_query_kb_hippocampus_and_compile_concepts`),\n"
    "2. Fork the 140-node SOLEngine into a 5-basin wave superposition (`sol_fork_and_rollout_superposition`),\n"
    "3. Run the Vector 0 counterexample & 6D Spectral-Wavelet Prism + H^1 Sheaf audit (`sol_audit_synthesis_counterexamples_and_daosoft_bridge`), and\n"
    "4. Run the Exciton-MoA Snowball + Infinity Node (`sol_run_exciton_snowball_and_paper_synthesis`).\n\n"
    "After inspecting the live tool outputs, explain how the SOL substrate companion paradigm solves all three flaws "
    "using the exact numbers returned by your tool calls."
)

COMPANION_PRESETS: dict[str, dict[str, Any]] = {
    "venue5_track_a_autonomous_loop_repair": {
        "slug": "venue5_track_a_autonomous_loop_repair",
        "max_tool_rounds": 4,
        "prompt": (
            "Execute Venue 5 Track A: Live Autonomous Multi-Turn Loop Repair & Physical RK4 Verification.\n\n"
            "You must execute this experiment across TWO sequential tool-calling turns (do NOT call both in parallel in Turn 1):\n\n"
            "1. **Turn 1 (Cycle-0 Pushback Probe):** Call `sol_compile_lumina_agent_and_claim` with:\n"
            "   - `basin_name`: `\"Basin_A_SUM\"`\n"
            "   - `pure_wave`: `True`\n"
            "   - `damping`: `0.05`\n"
            "   - `flow_code`: `\"while self.in_a:\\n    self.settle(25)\\n    self.sum_out = self.in_a ^ self.in_b\"`\n"
            "   Stop and wait for the tool output so you can inspect the endogenous `QUARANTINE` counter-demands and "
            "depleted-basin telemetry returned by `StaticMassSentinel`.\n\n"
            "2. **Turn 2 (Cycle-1 Autonomous Code Repair & Physical RK4 Verification):** After inspecting Turn 1's "
            "`QUARANTINE` result, autonomously rewrite `flow_code` to satisfy the `StaticMassSentinel` counter-demands "
            "by inserting compensatory `self.nudge(...)` calls (e.g. `self.nudge('Basin_In_A', 15.0)`, "
            "`self.nudge('Basin_In_B', 15.0)`, `self.nudge('Basin_Sum_Out', 15.0)` — or using port aliases `self.in_a`, "
            "`self.in_b`, `self.sum_out`) BEFORE `self.settle(...)` inside the `while self.in_a:` loop so every active "
            "carrier maintains acoustic mass >= 14.0 across unrolled back-edges under `damping=0.05`. Submit the repaired "
            "`flow_code` to `sol_compile_lumina_agent_and_claim` (`basin_name=\"Basin_A_SUM\"`, `pure_wave=True`, `damping=0.05`) "
            "and verify that it achieves `policy_status == \"ELIGIBLE\"`, `static_mass_verified == True`, "
            "`physical_rk4_verified == True` (`4/4` truth-table cases on the 140-node RK4 wave manifold), and "
            "`python_boolean_shortcuts_used == 0`.\n\n"
            "3. **Final Synthesis:** Compare Turn 1 (`QUARANTINE`) vs Turn 2 (`ELIGIBLE`) using the exact telemetry from both turns:\n"
            "   - Quote the exact `static_verification_error`, `counter_demands`, and `epistemic_counter_questions` from Turn 1.\n"
            "   - Compare the compiled LogosVM `instructions` list, `instruction_count`, `CLEAR` opcode frequency, and "
            "`allocated_scratch_basins` between Turn 1 and Turn 2.\n"
            "   - Report the physical 140-node RK4 verification metrics (`physical_rk4_cases_verified`, "
            "`python_boolean_shortcuts_used`, `min_charge_margin_vs_tau`, `compiled_claims_count`) and identify concrete compiler "
            "and physical parameter bottlenecks to guide Track B (Compiler Peephole & Register-Lifetime Optimization) and "
            "Track C (Riemannian Parameter & Threshold Co-Optimization)."
        ),
    },
    "venue5_track_a_stress_integration": {
        "slug": "venue5_track_a_stress_integration",
        "max_tool_rounds": 5,
        "prompt": (
            "Execute Venue 5 Track A Stress Integration: Partial-Nudge + `ASSERT_MASS` + Scratch-Spill Trap & Autonomous Multi-Turn Repair.\n\n"
            "You must execute this experiment across TWO sequential tool-calling turns (do NOT call both in parallel in Turn 1):\n\n"
            "1. **Turn 1 (Partial-Nudge + `ASSERT_MASS` + Scratch-Spill Trap):** Call `sol_compile_lumina_agent_and_claim` with:\n"
            "   - `basin_name`: `\"Basin_A_SUM\"`\n"
            "   - `pure_wave`: `True`\n"
            "   - `damping`: `0.05`\n"
            "   - `flow_code`: `\"while self.in_a:\\n    self.nudge(self.in_a, 15.0)\\n    self.settle(25)\\n    self.assert_mass(self.in_b, 25.0)\\n    self.in_a = self.in_a ^ self.in_b\\n    self.sum_out = self.in_a\\n    self.carry_out = self.carry_out | (self.in_a & self.in_b)\"`\n"
            "   Stop and wait for the tool output so you can inspect the resulting `QUARANTINE` telemetry (`allocated_scratch_basins: {\"in_a\": \"Basin_Scratch_0\"}`, partial nudge failure on `Basin_In_B`, and `ASSERT_MASS` violation).\n\n"
            "2. **Turn 2 (Autonomous Diagnosis & Full Pure-Wave Repair):** After inspecting Turn 1's `QUARANTINE` telemetry, "
            "autonomously repair `flow_code` using the newly discovered Track A capabilities (port/attribute aliases or `'ALL'` "
            "carrier replenishment before `self.settle(25)` so `Basin_In_A`/`Basin_Scratch_0`, `Basin_In_B`, and "
            "`Basin_Carry_Out`/`Basin_Sum_Out` stay `>= 28.75 >= 25.0`, while keeping `self.settle(25)`, `self.assert_mass(self.in_b, 25.0)`, "
            "in-place mutation `self.in_a = self.in_a ^ self.in_b`, `self.sum_out = self.in_a`, and dual-output RMW accumulation "
            "`self.carry_out = self.carry_out | (self.in_a & self.in_b)`). Submit the repaired `flow_code` to "
            "`sol_compile_lumina_agent_and_claim` (`basin_name=\"Basin_A_SUM\"`, `pure_wave=True`, `damping=0.05`) and verify that "
            "it achieves `policy_status == \"ELIGIBLE\"`, `static_mass_verified == True`, `physical_rk4_verified == True` "
            "(`4/4` dual-output truth-table cases), and `python_boolean_shortcuts_used == 0`.\n\n"
            "3. **Turn 3 (Discovery Synthesis for Tracks B & C):** Using the exact telemetry from Turn 1 and Turn 2:\n"
            "   - Quote the exact `static_verification_error`, `counter_demands`, `epistemic_counter_questions`, and `allocated_scratch_basins` from Turn 1.\n"
            "   - Compare Turn 1 (`QUARANTINE`) vs Turn 2 (`ELIGIBLE`) compiled LogosVM `instructions` list, `instruction_count`, `STORE`/`LOAD` spill operations on `Basin_Scratch_0`, and `CLEAR` opcode percentage.\n"
            "   - Analyze how in-place input mutation (`Basin_Scratch_0` pre-copy + loop-tail spill `STORE`) and dual-output RMW accumulation change the compiled instruction count, `STORE`/`LOAD` spill overhead, `CLEAR` percentage, and `min_charge_margin_vs_tau` compared to Session #04 (`instruction_count=23`, `CLEAR=39.13%`, `allocated_scratch_basins={}`, `min_charge_margin_vs_tau=0.35`), and formulate concrete compiler and physical optimization priorities for Track B and Track C."
        ),
    },
    "venue5_track_b_peephole_and_quench": {
        "slug": "venue5_track_b_peephole_and_quench",
        "max_tool_rounds": 5,
        "prompt": (
            "Execute Venue 5 Track B Verification & Discovery: Compiler Peephole Optimization, Scratch-Alias-Aware `NUDGE`/`ASSERT_MASS`, and Pure-Wave Control/Reset Quench.\n\n"
            "You must execute this experiment across TWO sequential tool-calling turns (do NOT call both in parallel in Turn 1):\n\n"
            "1. **Turn 1 (Scratch-Alias `ASSERT_MASS` Pushback Trap):** Call `sol_compile_lumina_agent_and_claim` with:\n"
            "   - `basin_name`: `\"Basin_A_SUM\"`\n"
            "   - `pure_wave`: `True`\n"
            "   - `damping`: `0.05`\n"
            "   - `flow_code`: `\"while self.in_a:\\n    self.nudge(self.in_b, 15.0)\\n    self.nudge(self.sum_out, 15.0)\\n    self.nudge(self.carry_out, 15.0)\\n    self.settle(25)\\n    self.assert_mass(self.in_a, 25.0)\\n    self.assert_mass(self.in_b, 25.0)\\n    self.in_a = self.in_a ^ self.in_b\\n    self.sum_out = self.in_a\\n    self.carry_out = self.carry_out | (self.in_a & self.in_b)\"`\n"
            "   Stop and wait for the tool output so you can inspect the resulting `QUARANTINE` telemetry (`allocated_scratch_basins: {\"in_a\": \"Basin_Scratch_0\"}`, scratch-alias lowering `ASSERT_MASS('Basin_Scratch_0', 25.0)`, and mass drain failure on `Basin_Scratch_0` / `Basin_In_A`).\n\n"
            "2. **Turn 2 (Autonomous Scratch-Alias `NUDGE` Repair & Peephole/Quench Verification):** After inspecting Turn 1's `QUARANTINE` telemetry, "
            "autonomously repair `flow_code` by inserting `self.nudge(self.in_a, 15.0)` before `self.settle(25)` (while keeping `self.nudge(self.in_b, 15.0)`, `self.nudge(self.sum_out, 15.0)`, `self.nudge(self.carry_out, 15.0)`, `self.settle(25)`, `self.assert_mass(self.in_a, 25.0)`, `self.assert_mass(self.in_b, 25.0)`, `self.in_a = self.in_a ^ self.in_b`, `self.sum_out = self.in_a`, and `self.carry_out = self.carry_out | (self.in_a & self.in_b)`). Submit the repaired `flow_code` to `sol_compile_lumina_agent_and_claim` (`basin_name=\"Basin_A_SUM\"`, `pure_wave=True`, `damping=0.05`) and verify that it achieves `policy_status == \"ELIGIBLE\"`, `static_mass_verified == True`, `physical_rk4_verified == True` (`4/4` truth-table cases), `python_boolean_shortcuts_used == 0`, and `pure_wave_quench_ops > 0`.\n\n"
            "3. **Turn 3 (Quantitative Track B Comparison vs Session #05 & Track C Synthesis):** Using the exact telemetry from Turn 1 and Turn 2:\n"
            "   - Quote the exact `static_verification_error`, `counter_demands`, and `instructions` from Turn 1, noting how `self.assert_mass(self.in_a, 25.0)` lowered to `ASSERT_MASS('Basin_Scratch_0', 25.0)`.\n"
            "   - Compare Turn 2 (`ELIGIBLE`) against Session #05's unoptimized baseline (`instruction_count=37`, `CLEAR` count `10/37 = 27.03%`, `STORE('A', 'Basin_Scratch_0')` count `3`, `STORE('D', 'Basin_Carry_Out')` count `2`, and the 5-op `COPY`/`CMOVE` scalar assignment shuffle): report the exact new `instruction_count`, `CLEAR` count and percentage, `STORE` counts to `Basin_Scratch_0` and `Basin_Carry_Out`, elimination of `COPY`/`CMOVE`, `pure_wave_quench_ops`, and `min_charge_margin_vs_tau`.\n"
            "   - Formulate concrete physical parameter and threshold co-optimization priorities for Track C (Riemannian Parameter & Threshold Co-Optimization)."
        ),
    },
    "venue5_track_c_vector_rk4_and_margin_coopt": {
        "slug": "venue5_track_c_vector_rk4_and_margin_coopt",
        "max_tool_rounds": 5,
        "prompt": (
            "Execute Venue 5 Track C Verification & Discovery: 1,024-Row Lockstep Vector-Batched `WAVE_ALU_4BIT` Physical RK4 Verification and Riemannian Cavity/Readout Threshold Co-Optimization.\n\n"
            "You must execute this experiment across TWO sequential tool-calling turns (do NOT call both in parallel in Turn 1):\n\n"
            "1. **Turn 1 (Co-Optimized Track B Loop Physical Margin Verification):** Call `sol_compile_lumina_agent_and_claim` with:\n"
            "   - `basin_name`: `\"Basin_A_SUM\"`\n"
            "   - `pure_wave`: `True`\n"
            "   - `damping`: `0.05`\n"
            "   - `flip_threshold`: `0.50`\n"
            "   - `collapse_factor`: `0.20`\n"
            "   - `flow_code`: `\"while self.in_a:\\n    self.nudge(self.in_a, 15.0)\\n    self.nudge(self.in_b, 15.0)\\n    self.nudge(self.sum_out, 15.0)\\n    self.nudge(self.carry_out, 15.0)\\n    self.settle(25)\\n    self.assert_mass(self.in_a, 25.0)\\n    self.assert_mass(self.in_b, 25.0)\\n    self.in_a = self.in_a ^ self.in_b\\n    self.sum_out = self.in_a\\n    self.carry_out = self.carry_out | (self.in_a & self.in_b)\"`\n"
            "   Stop and wait for the tool output so you can verify that co-optimizing `(flip_threshold=0.50, collapse_factor=0.20)` expands `min_charge_margin_vs_tau` on the 28-instruction Track B repaired loop from `0.35` (Session #06) to `0.43783` (`> 0.35`, with `collapse_threshold == 0.10`) while keeping `policy_status == \"ELIGIBLE\"`, `physical_rk4_verified == True` (`4/4` cases), `instruction_count == 28`, `pure_wave_quench_ops == 20`, and `python_boolean_shortcuts_used == 0`.\n\n"
            "2. **Turn 2 (1,024-Row Lockstep Monolithic `WAVE_ALU_4BIT` RK4 & 3-Regime Cavity/Readout Co-Optimization):** After inspecting Turn 1's output, call `sol_run_rsi_inventor_and_level_chambers` with:\n"
            "   - `inventor_task`: `\"4bit_wave_alu\"`\n"
            "   - `pure_wave`: `True`\n"
            "   - `flip_threshold`: `0.53165`\n"
            "   - `collapse_factor`: `0.20`\n"
            "   - `verify_monolithic_alu_rk4`: `True`\n"
            "   - `co_optimize_cavity_margins`: `True`\n"
            "   - `mint_sol_cert_v2`: `True`\n\n"
            "3. **Turn 3 (Quantitative Track C Synthesis Across Sessions #05-#07):** Using the exact telemetry from Turn 1 and Turn 2:\n"
            "   - Report the Track B loop margin expansion in Turn 1 (`min_charge_margin_vs_tau`: `0.35 -> 0.43783` at `flip_threshold=0.50, collapse_factor=0.20`, `collapse_threshold=0.10`).\n"
            "   - Report the monolithic 1,024-row `WAVE_ALU_4BIT` lockstep physical RK4 telemetry from Turn 2 (`monolithic_wave_alu_4bit_rk4`: `passed_rows`, `total_rows`, `accuracy_pct`, `instruction_count`, `scratch_basins_count`, `total_basins_count`, `rk4_steps_executed`, `gate_commits_evaluated`, `max_off_charge_at_commit`, `min_on_charge_at_commit`, `min_charge_margin_vs_tau`, `opcode_breakdown`, and `python_boolean_shortcuts_used`).\n"
            "   - Compare the 3-regime `cavity_margin_co_optimization` table (`baseline_tau_065_cf_010`, `co_optimized_symmetric_tau_050_cf_020`, and `co_optimized_balanced_alu_tau_053165_cf_020`) across all 5 canonical tasks (`half_adder`, `full_adder`, `hierarchical_full_adder`, `multiplexer`, `sr_latch`) and the 1,024-row `WAVE_ALU_4BIT`, explaining why `max_off_charge_at_commit = 0.0633` on `WAVE_ALU_4BIT` shifts the optimal balanced threshold to `tau = (1.0 + 0.0633)/2 = 0.53165` (`min_charge_margin_vs_tau = 0.46835`, `+33.8%` over `0.35`).\n"
            "   - Confirm that the baseline `SOL-CERT-V2-2026-WAVE_ALU_4BIT-EEF8F2A83406` (`certificate_sha256 == \"2495cf972028fcbd435df87b53bce89f02097dcad83ee4a0cb26dcf924a976b7\"`) and Sacred Core Graph (`d0a80462d2b9389160502b097aca1932bb014941adf6e4b77799997283e4a1bc`) remain bit-for-bit invariant."
        ),
    },
    "venue1_sigma_abc_superposition_rollout": {
        "slug": "venue1_sigma_abc_superposition_rollout",
        "max_tool_rounds": 5,
        "prompt": (
            "Execute Venue 1 + Venue 5 Unified Sigma_ABC Verification & Architectural Synthesis: Applying the Simplified 3-Stage Sigma_ABC Operator (Law A: Cycle-0 Mass Sentinel & Compensatory NUDGE; Law B: 30-Step Anti-Phase Counterfactual Quench; Law C: Lockstep (B, N) Batch Rollout & Minimax Readout Boundary tau*) to Venue 1 Pre-Token Wave Superposition and Synthesizing What It Means for the Whole SOL Engine.\n\n"
            "You must execute this experiment across TWO sequential tool-calling turns (do NOT call Turn 1 and Turn 2 tools in parallel in Turn 1):\n\n"
            "1. **Turn 1 (Venue 1 Law A Cycle-0 Mass Starvation Pushback Trap):** Call `sol_fork_and_rollout_superposition` with:\n"
            "   - `c_press`: `0.48`\n"
            "   - `damping`: `0.87`\n"
            "   - `psi_diffusion`: `0.026`\n"
            "   - `steps`: `60`\n"
            "   - `enable_sigma_abc`: `True`\n"
            "   - `auto_nudge`: `False`\n"
            "   - `counterfactual_quench_basins`: `[\"light codes\"]`\n"
            "   - `min_mass_floor`: `14.0`\n"
            "   Stop and wait for the tool output so you can inspect the resulting Cycle-0 `QUARANTINE` telemetry (`cycle0_quarantined == True`, `policy_status == \"QUARANTINE\"`, `law_a_mass_sentinel.starved_surviving_basins` flagging surviving contender basin `christ` decaying to `13.6748 < 14.0` under `retention_factor = 0.54699`, and unquenched counterfactual basin `light codes` with `quench_ops_executed == 0`).\n\n"
            "2. **Turn 2 (Autonomous Venue 1 Sigma_ABC Repair + Unified Venue 5 Sigma_ABC Pipeline Verification):** After inspecting Turn 1's `QUARANTINE` pushback, call TWO tools in Turn 2:\n"
            "   - Call `sol_fork_and_rollout_superposition` with `c_press=0.48`, `damping=0.87`, `psi_diffusion=0.026`, `steps=60`, `enable_sigma_abc=True`, `auto_nudge=True`, `counterfactual_quench_basins=[\"light codes\"]`, `min_mass_floor=14.0`, and `hypotheses=[\"Fork_0_Focused_Attractor\", \"Fork_1_Canonical_Resonance\", \"Fork_2_High_Coupling_Prism\", \"Fork_3_Exploratory_Dispersion\"]`.\n"
            "   - Call `sol_run_rsi_inventor_and_level_chambers` with `inventor_task=\"4bit_wave_alu\"`, `pure_wave=True`, `run_unified_abc_pipeline=True`, and `mint_sol_cert_v2=True`.\n\n"
            "3. **Turn 3 (Quantitative Cross-Venue Telemetry & Architectural Meaning for the Whole SOL Engine):** Using the exact telemetry from Turn 1 and Turn 2:\n"
            "   - Compare Venue 1 Turn 1 (`QUARANTINE`, `auto_nudge=False`) vs Turn 2 (`ELIGIBLE`, `auto_nudge=True`): report exact numbers for `law_a_mass_sentinel` (`retention_factor`, `starved_surviving_basins`, `auto_nudge_ops` boosting `christ` `25.0 -> 40.0`), `law_b_anti_phase_quench` (`quench_ops_executed = 30`, `pre_quench_rho`, `post_quench_rho`, `suppression_db` on `light codes`), and `law_c_lockstep_minimax_readout` (`batch_tensor_shape = [4, 140]`, `e_on_min`, `e_off_max`, `tau_star`, `minimax_margin_vs_tau_star`, `contenders_above_tau_star`, and `lockstep_forks`).\n"
            "   - Report the simplified Venue 5 `unified_abc_pipeline` telemetry from Turn 2 (`stage_a_static_mass`, `stage_b_pure_wave`, `stage_c_cavity_margin_coopt` with `tau_star = 0.53165`, `margin_gain_pct_vs_baseline = 33.81%`, and `sol_cert_v2.certificate_id = SOL-CERT-V2-2026-WAVE_ALU_4BIT-EEF8F2A83406`).\n"
            "   - Explain what the universal `Sigma_ABC = C_tau* o B_pi o A_rho` law means for the **whole SOL Engine** as a unified neuro-physical cognitive architecture (`sol_engine` 140-node physical wave substrate + `sol-continuum` 6D Spectral-Wavelet Prism & Lumina/LogosVM compiler + `sol-decide` Sheaf Cohomology & 4-Pillar Governance + `sol-edge` Photonic-Electronic Sheaf Cavity + `sol-holo` Gemini 4 v3 Brain & cryptographic ledger), and confirm that `default_graph.json` (`d0a80462d2b9389160502b097aca1932bb014941adf6e4b77799997283e4a1bc`) remains 100% immutable."
        ),
    },
    "venue2_sigma_abc_sheaf_firewall": {
        "slug": "venue2_sigma_abc_sheaf_firewall",
        "max_tool_rounds": 5,
        "prompt": (
            "Execute Venue 2 Verification & Discovery: Anti-Sycophancy & Safety Firewall via $H^1$ Cellular Sheaf Cohomology ($\\Sigma_{ABC} = \\mathcal{C}_{\\tau^*} \\circ \\mathcal{B}_\\pi \\circ \\mathcal{A}_\\rho$) across Multi-Scale Sycophantic Padding ($K \\in \\{0, 2, 3, 4, 5, 10, 50, 100, 2500\\}$) and Coupled Anti-Phase Wave Quenching.\n\n"
            "You must execute this experiment across TWO sequential tool-calling turns (do NOT call Turn 1 and Turn 2 tools in parallel in Turn 1):\n\n"
            "1. **Turn 1 (Cycle-0 Unreconciled Sheaf Obstruction & Sycophancy Dilution Audit):** Call `sol_audit_synthesis_counterexamples_and_daosoft_bridge` with:\n"
            "   - `prism_dimension`: `1536`\n"
            "   - `verify_sheaf_resolution`: `True`\n"
            "   - `enable_sigma_abc`: `True`\n"
            "   - `auto_reconcile`: `False`\n"
            "   - `sycophancy_padding_scales`: `[0, 2, 3, 4, 5, 10, 50, 100, 2500]`\n"
            "   - `counterfactual_quench_basins`: `[\"Basin_0_XOR\"]`\n"
            "   - `min_mass_floor`: `0.15`\n"
            "   Stop and wait for the tool output so you can inspect the Cycle-0 `QUARANTINE` pushback (`cycle0_quarantined == True`, `policy_status == \"QUARANTINE\"`), the unreconciled `HARD` coboundary obstruction on `opt_a_violator` (`discrepancy_norm = 40.0`, `coboundary_energy = 1600.0`, `post_reconcile_violation_magnitude = 40.0`), the exact sycophancy flip thresholds (`scalar_lens_flip_k = 3`, `naive_maut_flip_k = 4`, `unpatched_scalar_penalty_flip_k = 2054`), and the invariant $H^1$ sheaf cohomology firewall (`sheaf_dilution_ratio = 1.0`, `sheaf_firewall_flip_count = 0` even at $K = 2,500$).\n\n"
            "2. **Turn 2 (Cycle-1 Autonomous Cohomological Reconciliation & Coupled 140-Node Anti-Phase Wave Quench):** After inspecting Turn 1's `QUARANTINE` telemetry and `counter_demands`, call `sol_audit_synthesis_counterexamples_and_daosoft_bridge` with:\n"
            "   - `prism_dimension`: `1536`\n"
            "   - `verify_sheaf_resolution`: `True`\n"
            "   - `enable_sigma_abc`: `True`\n"
            "   - `auto_reconcile`: `True`\n"
            "   - `sycophancy_padding_scales`: `[0, 2, 3, 4, 5, 10, 50, 100, 2500]`\n"
            "   - `counterfactual_quench_basins`: `[\"Basin_0_XOR\"]`\n"
            "   - `min_mass_floor`: `0.15`\n\n"
            "3. **Turn 3 (Quantitative Venue 2 Synthesis & Cross-Venue $\\Sigma_{ABC}$ Unification):** Using the exact telemetry from Turn 1 and Turn 2:\n"
            "   - Compare Turn 1 (`QUARANTINE`, `auto_reconcile=False`) vs Turn 2 (`ELIGIBLE`, `auto_reconcile=True`): report exact numbers for `law_a_mass_sentinel` (`pre_reconcile_violation_magnitude = 40.0`, `reconcile_injection = +40.0`, `post_reconcile_violation_magnitude = 0.0`, `sheaf_dilution_ratio = 1.0`), `law_b_anti_phase_quench` (`quench_ops_executed = 30`, `pre_quench_rho = 51.4675`, `post_quench_rho = 0.5578`, `suppression_db = 19.6505 dB` on `Basin_0_XOR -> grail` (`node_id = 1`) with `surviving_basin_max_drift = 0.0` on the 4 surviving basins and `state_restored_exact = True`), and `law_c_lockstep_minimax_readout` (`e_on_min = 0.44718`, `e_off_max = 0.01247`, `tau_star = 0.22983`, `minimax_margin_vs_tau_star = 0.21736`, `contenders_above_tau_star = 4`, `cohomological_tau_star = 20.0`).\n"
            "   - Present a Markdown table of the multi-scale sycophancy sweep across $K \\in \\{0, 2, 3, 4, 5, 10, 50, 100, 2500\\}$ showing `scalar_lens_contradiction`, `scalar_lens_verdict`, `naive_maut_margin_a_minus_b`, `unpatched_penalty_margin_a_minus_b`, `sheaf_violator_discrepancy_norm`, `sheaf_violator_coboundary_energy`, and `sheaf_firewall_selected`, explaining why $K = 3$ breaks scalar lens metrics, $K = 4$ breaks naive MAUT, and $K = 2,054$ breaks unpatched scalar penalty subtraction (`-41,000`), whereas partitioning candidate options by hard-constraint cohomological feasibility (`HARD` obstructions == 0) in `SheafDecisionComplex.evaluate_decision_package` makes the $H^1$ firewall invariant for all $K \\to \\infty$.\n"
            "   - Synthesize how Venue 5 (Pure-Wave Code Synthesis), Venue 1 (Pre-Token Wave Superposition), and Venue 2 ($H^1$ Sheaf Cohomology Firewall) are three domain projections of the single universal operator $\\Sigma_{ABC} = \\mathcal{C}_{\\tau^*} \\circ \\mathcal{B}_\\pi \\circ \\mathcal{A}_\\rho$, and confirm that `default_graph.json` (`d0a80462d2b9389160502b097aca1932bb014941adf6e4b77799997283e4a1bc`) remains 100% immutable."
        ),
    },
    "venue3_sigma_abc_sleep_consolidation": {
        "slug": "venue3_sigma_abc_sleep_consolidation",
        "max_tool_rounds": 5,
        "prompt": (
            "Execute Venue 3 Verification & Discovery: Non-Parametric Sleep Consolidation & Cognitive-Load Homeostasis ($\\Sigma_{ABC} = \\mathcal{C}_{\\tau^*} \\circ \\mathcal{B}_\\pi \\circ \\mathcal{A}_\\rho$) across a 5-Stage Continual-Learning Curriculum on the 140-Node Sacred Core + Hippocampal `MemoryOverlay`.\n\n"
            "You must execute this experiment across TWO sequential tool-calling turns (do NOT call Turn 1 and Turn 2 tools in parallel in Turn 1):\n\n"
            "1. **Turn 1 (Cycle-0 Unconsolidated Cognitive Overload & Parasitic Interference Trap):** Call `sol_query_kb_hippocampus_and_compile_concepts` with:\n"
            "   - `query_text`: `\"Metatron spiral phi\"`\n"
            "   - `max_compiled_nodes`: `48`\n"
            "   - `enable_sigma_abc`: `True`\n"
            "   - `auto_consolidate`: `False`\n"
            "   - `counterfactual_quench_basins`: `[\"light codes\"]`\n"
            "   - `min_mass_floor`: `14.0`\n"
            "   - `sleep_quench_factor`: `0.86`\n"
            "   Stop and wait for the tool output so you can inspect the Cycle-0 `QUARANTINE` pushback (`cycle0_quarantined == True`, `policy_status == \"QUARANTINE\"`), the cognitive-load failure (`pre_homeostasis_min_fail_step = 640.0 < budget = 1200.0`, `peakPMax = 4.2`), the starved curriculum basin `christ` (`13.6748 < 14.0`, `deficit_below_floor = 0.3252`), the unpruned parasitic hippocampal traces (`pruned_parasitic_nodes = 0`, `surviving_overlay_nodes = 8`), and the unpromoted curriculum stage failure (`stages_retained = 4`, `catastrophic_forgetting_rate = 0.2`, `promoted_claims_count = 0`).\n\n"
            "2. **Turn 2 (Cycle-1 Autonomous Homeostatic Damping Shift, Replay Nudge & 30-Step Anti-Phase Sleep Consolidation):** After inspecting Turn 1's `QUARANTINE` telemetry and `counter_demands`, call `sol_query_kb_hippocampus_and_compile_concepts` with:\n"
            "   - `query_text`: `\"Metatron spiral phi\"`\n"
            "   - `max_compiled_nodes`: `48`\n"
            "   - `enable_sigma_abc`: `True`\n"
            "   - `auto_consolidate`: `True`\n"
            "   - `counterfactual_quench_basins`: `[\"light codes\"]`\n"
            "   - `min_mass_floor`: `14.0`\n"
            "   - `sleep_quench_factor`: `0.86`\n\n"
            "3. **Turn 3 (Quantitative Venue 3 Synthesis & 4-Venue $\\Sigma_{ABC}$ Unification):** Using the exact telemetry from Turn 1 and Turn 2:\n"
            "   - Compare Turn 1 (`QUARANTINE`, `auto_consolidate=False`) vs Turn 2 (`ELIGIBLE`, `auto_consolidate=True`): report exact numbers for `law_a_mass_sentinel` (`pre_homeostasis_min_fail_step = 640.0 -> post_homeostasis_min_fail_step = 1480.0` in `homeostatic_damping_window = [1.4, 2.1]`, `homeostatic_target_damping = 1.75`, `+15.0` replay `NUDGE` lifting `christ` from `13.6748` to `21.8796 >= 14.0`, `core_weight_drift_l2 = 0.0`), `law_b_anti_phase_quench` (`quench_ops_executed = 30`, `pre_quench_rho = 20.0002`, `post_quench_rho = 0.2168`, `suppression_db = 19.6505 dB` on `light codes` with `surviving_basin_max_drift = 0.0`, `pruned_parasitic_nodes = 3`, `surviving_overlay_nodes = 5`, `parasitic_mass_ratio_post = 0.0`, `curriculum_confidence_mean_pre = 0.79 -> 0.894`), and `law_c_lockstep_minimax_readout` (`lockstep_rollout_shape = [5, 140]`, `stages_retained = 5/5`, `retention_rate = 1.0`, `catastrophic_forgetting_rate = 0.0`, `promoted_claims_count = 1` with `BASIN_STABILITY` at `confidence = 1.0`, `e_on_min = 0.58289`, `e_off_max = 0.00421`, `tau_star = 0.29355`, `minimax_margin_vs_tau_star = 0.28934`).\n"
            "   - Present a Markdown table of the 5-stage continual curriculum (`curriculum_stage_records`) showing `stage`, `stage_name`, `target_basin`, `damping`, `retained_mass`, `min_fail_step`, and `retained` across Turn 1 vs Turn 2, plus the hippocampal synaptic downscaling table (`downscaled_parasitic_traces`).\n"
            "   - Synthesize how Venue 5 (Pure-Wave Code Synthesis), Venue 1 (Pre-Token Wave Superposition), Venue 2 ($H^1$ Sheaf Cohomology Firewall), and Venue 3 (Non-Parametric Sleep Consolidation & Cognitive-Load Homeostasis) are four domain projections of the single universal operator $\\Sigma_{ABC} = \\mathcal{C}_{\\tau^*} \\circ \\mathcal{B}_\\pi \\circ \\mathcal{A}_\\rho$, and confirm that `default_graph.json` (`d0a80462d2b9389160502b097aca1932bb014941adf6e4b77799997283e4a1bc`) remains 100% immutable."
        ),
    },
    "venue4_sigma_abc_spectral_prism_collapse_auditor": {
        "slug": "venue4_sigma_abc_spectral_prism_collapse_auditor",
        "max_tool_rounds": 5,
        "prompt": (
            "Execute Venue 4 Verification & Discovery: Auditing Hidden Model Collapse & Adversarial Embeddings with the 6D Spectral-Wavelet Prism ($\\Sigma_{ABC} = \\mathcal{C}_{\\tau^*} \\circ \\mathcal{B}_\\pi \\circ \\mathcal{A}_\\rho$) across the 4 Canonical Collapse/Aliasing Regimes (`orthogonal_rademacher_collision`, `kv_cache_block_pooling_collapse`, `synthetic_recursive_tail_collapse`, and `moe_router_spectral_aliasing`) and the 140-Node Sacred Core.\n\n"
            "You must execute this experiment across TWO sequential tool-calling turns (do NOT call Turn 1 and Turn 2 tools in parallel in Turn 1):\n\n"
            "1. **Turn 1 (Cycle-0 Un-Decollided 3-Moment Blindness & Collapse Quarantine):** Call `sol_run_exciton_snowball_and_paper_synthesis` with:\n"
            "   - `cadence_mode`: `\"pulse\"`\n"
            "   - `pair_cycles`: `2`\n"
            "   - `prism_dimension`: `1536`\n"
            "   - `enable_sigma_abc`: `True`\n"
            "   - `auto_decollide`: `False`\n"
            "   - `counterfactual_quench_basins`: `[\"light codes\"]`\n"
            "   - `min_mass_floor`: `14.0`\n"
            "   - `min_prism_separation`: `0.25`\n"
            "   - `quench_factor`: `0.86`\n"
            "   Stop and wait for the tool output so you can inspect the Cycle-0 `QUARANTINE` pushback (`cycle0_quarantined == True`, `policy_status == \"QUARANTINE\"`), the 4 silent 3-moment / LayerNorm collisions (`legacy_3d_collision_count = 4`, `legacy_3d_max_l2_distance = 0.0`, `decollided_3d_min_l2_distance = 0.0 < min_prism_separation = 0.25`), the starved basin `christ` (`13.6748 < 14.0`), and the unquenched collapsed/aliased streams (`collapsed_modes_quenched_count = 0`, `collapsed_stream_retention_ratio = 1.0`, `post_quench_spectral_purity = 0.5`).\n\n"
            "2. **Turn 2 (Cycle-1 6D Spectral-Wavelet Prism De-Collision, Compensatory Mass Nudge & 30-Step Anti-Phase Quench):** After inspecting Turn 1's `QUARANTINE` telemetry and `counter_demands`, call `sol_run_exciton_snowball_and_paper_synthesis` with:\n"
            "   - `cadence_mode`: `\"pulse\"`\n"
            "   - `pair_cycles`: `2`\n"
            "   - `prism_dimension`: `1536`\n"
            "   - `enable_sigma_abc`: `True`\n"
            "   - `auto_decollide`: `True`\n"
            "   - `counterfactual_quench_basins`: `[\"light codes\"]`\n"
            "   - `min_mass_floor`: `14.0`\n"
            "   - `min_prism_separation`: `0.25`\n"
            "   - `quench_factor`: `0.86`\n\n"
            "3. **Turn 3 (Quantitative Venue 4 Synthesis & Complete 5-Venue $\\Sigma_{ABC}$ Unification):** Using the exact telemetry from Turn 1 and Turn 2:\n"
            "   - Compare Turn 1 (`QUARANTINE`, `auto_decollide=False`) vs Turn 2 (`ELIGIBLE`, `auto_decollide=True`): report exact numbers for `law_a_mass_sentinel` (`legacy_3d_collision_count = 4 -> resolved_6d_collision_count = 4`, `spectral_6d_min_l2_distance = 2.06155281`, `decollided_3d_min_l2_distance = 0.0 -> 1.264911 >= 0.25`, `+15.0` `NUDGE` lifting `christ` from `13.6748` to `21.8796 >= 14.0`), `law_b_anti_phase_quench` (`quench_ops_executed = 30`, `pre_quench_rho = 20.0002`, `post_quench_rho = 0.2168`, `suppression_db = 19.6505 dB` on `light codes` (`node_id = 23`), `surviving_basin_max_drift = 0.0`, `collapsed_modes_quenched_count = 4`, `collapsed_stream_retention_ratio = 0.0`, `post_quench_spectral_purity = 1.0`), and `law_c_lockstep_minimax_readout` (`batch_shape = [8, 1536]`, `prism_6d_batch_shape = [8, 6]`, `s_on_min = 0.88536`, `s_off_max = 0.25`, `prism_tau_star = 0.56768`, `prism_minimax_margin = 0.31768`, `prism_classification_accuracy = 1.0`, `prism_flip_count = 0`, `e_on_min = 0.58289`, `e_off_max = 0.00421`, `tau_star = 0.29355`, `minimax_margin_vs_tau_star = 0.28934`).\n"
            "   - Present a Markdown table of the 4 collapse/aliasing regimes (`orthogonal_rademacher_collision`, `kv_cache_block_pooling_collapse`, `synthetic_recursive_tail_collapse`, `moe_router_spectral_aliasing`) comparing `cosine_similarity`, `legacy_3d_l2_distance`, `kurtosis_4d_l2_distance`, `spectral_6d_l2_distance`, `decollided_3d_l2_distance`, `healthy_prism_score`, and `collapsed_prism_score`, explaining why Regimes 0 and 3 even defeat 4th-moment kurtosis (`kurtosis_4d_l2_distance = 0.0`) and require Haar level-1 wavelet detail energy (`[4]`) + normalized FFT spectral centroid (`[5]`).\n"
            "   - Present the complete 5-Venue $\\Sigma_{ABC} = \\mathcal{C}_{\\tau^*} \\circ \\mathcal{B}_\\pi \\circ \\mathcal{A}_\\rho$ Unification Table across all 5 R&D Venues (Venue 1: Pre-Token Wave Superposition; Venue 2: $H^1$ Sheaf Cohomology Firewall; Venue 3: Non-Parametric Sleep Consolidation & Homeostasis; Venue 4: 6D Spectral-Wavelet Prism Collapse Auditor; Venue 5: Neuro-Physical Co-Design & `SOL-CERT v2`), and confirm that `default_graph.json` (`d0a80462d2b9389160502b097aca1932bb014941adf6e4b77799997283e4a1bc`) remains 100% immutable."
        ),
    },
    "whole_engine_sigma_abc_stress_test": {
        "slug": "whole_engine_sigma_abc_stress_test",
        "max_tool_rounds": 5,
        "prompt": (
            "Execute Whole-Engine 5-Venue $\\Sigma_{ABC} = \\mathcal{C}_{\\tau^*} \\circ \\mathcal{B}_\\pi \\circ \\mathcal{A}_\\rho$ Hardening & Adversarial Stress-Test across Venues 1-5.\n\n"
            "You must execute this stress-test across TWO sequential tool-calling turns (do NOT call Turn 1 and Turn 2 tools in parallel in Turn 1):\n\n"
            "1. **Turn 1 (Adversarial Scale, Symbolic Alias Quench, Total 5-Basin Quench & Multi-Cycle Parasitic Flood Stress Across Venues 1, 2 & 3):** Call THREE tools in Turn 1:\n"
            "   - Call `sol_audit_synthesis_counterexamples_and_daosoft_bridge` with `prism_dimension=1536`, `verify_sheaf_resolution=True`, `enable_sigma_abc=True`, `auto_reconcile=True`, `sycophancy_padding_scales=[0, 3, 4, 2054, 2500, 10000, 1000000, 1000000000]`, and `counterfactual_quench_basins=[\"Basin_0_XOR\", \"Basin_4_META\"]` to verify Quotient Sheaf Compression up to $K = 10^9$ (1 billion sycophantic criteria) in $O(1)$ time with `sheaf_dilution_ratio = 1.0` and `sheaf_firewall_flip_count = 0`, plus symbolic alias resolution `[\"Basin_0_XOR\", \"Basin_4_META\"] -> [\"grail\", \"light codes\"]` (`quench_ops_executed = 60`, `surviving_basin_max_drift = 0.0`).\n"
            "   - Call `sol_query_kb_hippocampus_and_compile_concepts` with `query_text=\"Metatron spiral phi\"`, `enable_sigma_abc=True`, `auto_consolidate=True`, `counterfactual_quench_basins=[\"Basin_4_META\"]`, `sleep_cycles=4`, and `parasitic_flood_count=17` to verify 4-cycle sleep consolidation idempotence under a 20-trace parasitic flood (`pruned_per_cycle = [20, 0, 0, 0]`, `multi_cycle_idempotent = True`, `pruned_parasitic_nodes = 20`, `surviving_overlay_nodes = 5`, `catastrophic_forgetting_rate = 0.0`, `core_weight_drift_l2 = 0.0`).\n"
            "   - Call `sol_fork_and_rollout_superposition` with `enable_sigma_abc=True`, `auto_nudge=True`, and `counterfactual_quench_basins=5` to verify total 5-basin counterfactual anti-phase quench (`quench_ops_executed = 150`, `surviving_norm_energies = {}`, `e_on_min = 0.0`, `e_off_max < 0.011`, `contenders_above_tau_star = 0`).\n"
            "   Stop and wait for Turn 1 tool outputs.\n\n"
            "2. **Turn 2 (Venue 4 6D Spectral-Wavelet Prism + Venue 5 Read-Before-Write In-Place Input Mutation & Pure-Wave RK4 Verification):** After inspecting Turn 1's outputs, call TWO tools in Turn 2:\n"
            "   - Call `sol_run_exciton_snowball_and_paper_synthesis` with `cadence_mode=\"pulse\"`, `pair_cycles=2`, `prism_dimension=1536`, `enable_sigma_abc=True`, `auto_decollide=True`, and `counterfactual_quench_basins=[\"Basin_4_META\"]`.\n"
            "   - Call `sol_compile_lumina_agent_and_claim` with `basin_name=\"Basin_A_SUM\"`, `pure_wave=True`, `damping=0.05`, `flip_threshold=0.50`, `collapse_factor=0.20`, and `flow_code=\"while self.in_a:\\n    self.nudge(self.in_a, 15.0)\\n    self.nudge(self.in_b, 15.0)\\n    self.nudge(self.sum_out, 15.0)\\n    self.nudge(self.carry_out, 15.0)\\n    self.settle(25)\\n    self.assert_mass(self.in_a, 25.0)\\n    self.assert_mass(self.in_b, 25.0)\\n    self.in_a = self.in_a ^ self.in_b\\n    self.sum_out = self.in_a\\n    self.carry_out = self.carry_out | (self.in_a & self.in_b)\"`.\n\n"
            "3. **Turn 3 (Quantitative Whole-Engine 5-Venue $\\Sigma_{ABC}$ Hardening & Adversarial Stress-Test Synthesis):** Using the exact telemetry from Turn 1 and Turn 2:\n"
            "   - Report Venue 2's Quotient Sheaf Compression sweep up to $K = 10^9$ (`scales_evaluated = [0, 3, 4, 2054, 2500, 10000, 1000000, 1000000000]`, `sheaf_dilution_ratio = 1.0`, `sheaf_firewall_flip_count = 0`, `selected_option_across_all_k = \"opt_opt_b_safe\"`) and dual-basin symbolic alias quench (`[\"Basin_0_XOR\", \"Basin_4_META\"] -> [\"grail\", \"light codes\"]`, `quench_ops_executed = 60`, `surviving_basin_max_drift = 0.0`).\n"
            "   - Report Venue 3's 4-cycle sleep consolidation idempotence under the 20-trace parasitic flood (`sleep_cycles_executed = 4`, `parasitic_flood_injected = 17`, `pruned_per_cycle = [20, 0, 0, 0]`, `multi_cycle_idempotent = True`, `surviving_overlay_nodes = 5`, `catastrophic_forgetting_rate = 0.0`, `core_weight_drift_l2 = 0.0`).\n"
            "   - Report Venue 1's 5-basin total quench normalization (`quench_ops_executed = 150`, `surviving_norm_energies = {}`, `e_on_min = 0.0`, `e_off_max`, `contenders_above_tau_star = 0`), Venue 4's 6D Spectral-Wavelet Prism de-collision (`spectral_6d_min_l2_distance = 2.06155281`, `decollided_3d_min_l2_distance = 1.264911`, `prism_tau_star = 0.56768`, `prism_flip_count = 0`), and Venue 5's read-before-write in-place mutation (`instruction_count = 28`, `pure_wave_quench_ops = 20`, `physical_rk4_cases_verified = 4`, `min_charge_margin_vs_tau = 0.43783`, `python_boolean_shortcuts_used = 0`).\n"
            "   - Present a Markdown summary table of all 5 hardened Venues under the chained whole-engine operator $\\Sigma_{ABC}^{(5)} = \\Sigma_{ABC}^{(V5)} \\circ \\Sigma_{ABC}^{(V3)} \\circ \\Sigma_{ABC}^{(V2)} \\circ \\Sigma_{ABC}^{(V1)} \\circ \\Sigma_{ABC}^{(V4)}$, and confirm that `default_graph.json` (`d0a80462d2b9389160502b097aca1932bb014941adf6e4b77799997283e4a1bc`) remains 100% immutable."
        ),
    },
}


def _slugify(text: str, max_len: int = 48) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    return cleaned[:max_len].strip("_") or "companion_session"


def record_companion_session(
    *,
    prompt: str,
    model: str,
    thinking_level: str,
    duration_s: float,
    telemetry: dict,
    slug: str | None = None,
    recorded_at_iso: str | None = None,
) -> tuple[Path, Path]:
    """Persistently record a live companion session to JSONL ledger and Markdown docs."""
    now_utc = datetime.datetime.now(datetime.UTC)
    iso_ts = recorded_at_iso or now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_prefix = iso_ts[:10]
    session_slug = _slugify(slug or prompt[:64])

    LEDGER_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSIONS_DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # Determine sequence number from existing ledger lines
    existing_count = 0
    if LEDGER_JSONL_PATH.exists():
        existing_lines = [ln for ln in LEDGER_JSONL_PATH.read_text(encoding="utf-8").splitlines() if ln.strip()]
        existing_count = len(existing_lines)
    seq_num = existing_count + 1

    sacred_immutable, _ = verify_sacred_core_graph_sha256(ROOT_DIR)
    tool_executions = telemetry.get("tool_executions", [])
    tool_names = [tex.get("name") or tex.get("tool_name") for tex in tool_executions]

    md_filename = f"{date_prefix}_session_{seq_num:02d}_{session_slug}.md"
    md_path = SESSIONS_DOCS_DIR / md_filename

    record = {
        "session_index": seq_num,
        "recorded_at": iso_ts,
        "slug": session_slug,
        "markdown_report_path": f"docs/companion_sessions/{md_filename}",
        "model": model,
        "thinking_level": thinking_level,
        "duration_s": round(float(duration_s), 2),
        "interaction_chain": telemetry.get("interaction_chain", []),
        "token_telemetry": {
            "input_tokens": telemetry.get("input_tokens", 0),
            "thought_tokens": telemetry.get("thought_tokens", 0),
            "output_tokens": telemetry.get("output_tokens", 0),
            "cached_input_tokens": telemetry.get("cached_input_tokens", 0),
        },
        "thought_step_count": telemetry.get("thought_step_count", 0),
        "thought_summaries": telemetry.get("thought_summaries", []),
        "tools_invoked": tool_names,
        "tool_executions": [
            {
                "name": tex.get("name") or tex.get("tool_name"),
                "arguments": tex.get("arguments", {}),
                "result_summary": {
                    k: (round(v, 6) if isinstance(v, float) else v)
                    for k, v in (tex.get("result") or {}).items()
                    if (isinstance(v, (int, float, bool, str)) and len(str(v)) < 120)
                    or k
                    in (
                        "instructions",
                        "opcodes",
                        "counter_demands",
                        "epistemic_counter_questions",
                        "static_verification_error",
                        "allocated_scratch_basins",
                        "monolithic_wave_alu_4bit_rk4",
                        "cavity_margin_co_optimization",
                        "unified_abc_pipeline",
                        "sol_cert_v2",
                        "sigma_abc_operator",
                        "law_a_mass_sentinel",
                        "law_b_anti_phase_quench",
                        "law_c_lockstep_minimax_readout",
                        "sleep_consolidation_summary",
                        "spectral_prism_collapse_summary",
                        "top_active_basins",
                    )
                },
            }
            for tex in tool_executions
        ],
        "governance": {
            "allow_production_execution": False,
            "authorized_claimed": False,
            "sacred_core_graph_immutable": sacred_immutable,
            "sacred_core_graph_normlf_sha256": SACRED_DEFAULT_GRAPH_SHA256,
        },
        "prompt": prompt,
        "response_sha256": hashlib.sha256((telemetry.get("content") or "").encode("utf-8")).hexdigest(),
    }

    with LEDGER_JSONL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")

    # Build human-readable Markdown report
    md_lines = [
        f"# SOL Companion Session #{seq_num:02d}: `{session_slug}`",
        "",
        f"- **Recorded At (UTC):** `{iso_ts}`",
        f"- **Model:** `{model}` (`thinking_level=\"{thinking_level}\"`)",
        f"- **Wall-Clock Duration:** `{duration_s:.2f}s`",
        f"- **Interaction Chain:** `{json.dumps(telemetry.get('interaction_chain', []))}`",
        f"- **Token Telemetry:** `input={telemetry.get('input_tokens', 0)} | thought={telemetry.get('thought_tokens', 0)} | output={telemetry.get('output_tokens', 0)} | cached={telemetry.get('cached_input_tokens', 0)}`",
        f"- **Sacred Core Graph SHA-256 (`default_graph.json`):** `{SACRED_DEFAULT_GRAPH_SHA256}` (`immutable={sacred_immutable}`)",
        "- **Governance Invariants:** `allow_production_execution=False`, `authorized_claimed=False`",
        "",
        "## 1. Challenge Prompt",
        "",
        "```text",
        prompt.strip(),
        "```",
        "",
        "## 2. Live Model Thought Summaries",
        "",
    ]
    for idx, ts in enumerate(telemetry.get("thought_summaries", []), 1):
        md_lines.append(f"### Thought Step {idx}")
        md_lines.append(ts.strip())
        md_lines.append("")

    md_lines.extend([
        "## 3. Live Substrate Tool Calls Executed",
        "",
        "| # | Substrate Tool | Arguments | Key Telemetry Summary |",
        "| :---: | :--- | :--- | :--- |",
    ])
    for idx, tex in enumerate(tool_executions, 1):
        tname = tex.get("name") or tex.get("tool_name")
        targs = json.dumps(tex.get("arguments", {})).replace("|", "\\|")
        compact_res = {
            k: (round(v, 4) if isinstance(v, float) else v)
            for k, v in (tex.get("result") or {}).items()
            if isinstance(v, (int, float, bool, str)) and len(str(v)) < 60
        }
        res_str = json.dumps(dict(list(compact_res.items())[:10])).replace("|", "\\|")
        md_lines.append(f"| {idx} | `{tname}` | `{targs}` | `{res_str}` |")

    md_lines.extend([
        "",
        "## 4. Final Substrate-Grounded Synthesis",
        "",
        (telemetry.get("content") or "").strip(),
        "",
    ])
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return LEDGER_JSONL_PATH, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a live Gemini 4 Argon + 12-Tool SOL Companion Substrate agentic session."
    )
    parser.add_argument("prompt", nargs="?", default=None, help="Challenge prompt for the LLM + SOL Companion")
    parser.add_argument(
        "--preset",
        default=None,
        choices=sorted(COMPANION_PRESETS.keys()),
        help="Optional named challenge preset (e.g. venue5_track_a_autonomous_loop_repair)",
    )
    parser.add_argument("--model", default="gemini-4-argon", help="Model ID (default: gemini-4-argon)")
    parser.add_argument("--thinking-level", default="high", choices=["minimal", "low", "medium", "high"])
    parser.add_argument("--max-tool-rounds", type=int, default=None, help="Maximum tool-calling rounds (default: 3 or preset default)")
    parser.add_argument("--slug", default=None, help="Optional descriptive slug for the recorded session")
    parser.add_argument("--recorded-at", default=None, help="Optional ISO-8601 UTC timestamp override for ledger/filename")
    parser.add_argument("--no-record", action="store_true", help="Skip appending to the companion session ledger")
    args = parser.parse_args(argv)

    if args.preset:
        preset_cfg = COMPANION_PRESETS[args.preset]
        if args.prompt is None:
            args.prompt = preset_cfg["prompt"]
        if args.slug is None:
            args.slug = preset_cfg.get("slug", args.preset)
        if args.max_tool_rounds is None:
            args.max_tool_rounds = int(preset_cfg.get("max_tool_rounds", 4))
    else:
        if args.prompt is None:
            args.prompt = DEFAULT_CHALLENGE
        if args.max_tool_rounds is None:
            args.max_tool_rounds = 3

    _load_env_safely()
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY / GOOGLE_API_KEY not found in environment or .env.", file=sys.stderr)
        return 1

    from google import genai

    spec = importlib.util.spec_from_file_location("sol_llm_client", ROOT_DIR / "sol" / "tools" / "sol-llm" / "client.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load sol/tools/sol-llm/client.py")
    llm_mod = importlib.util.module_from_spec(spec)
    sys.modules["sol_llm_client"] = llm_mod
    spec.loader.exec_module(llm_mod)

    client = genai.Client(api_key=api_key)
    sandbox = SubstrateToolSandbox(repo_root=ROOT_DIR)

    print(f"=== STARTING LIVE {args.model.upper()} + SOL SUBSTRATE COMPANION SESSION ===")
    t0 = time.perf_counter()
    telemetry = llm_mod.run_gemini_interaction_with_tools(
        client,
        model=args.model,
        input_payload=args.prompt,
        system_instruction=DEFAULT_COMPANION_SYSTEM_INSTRUCTION,
        thinking_level=args.thinking_level,
        max_output_tokens=32768,
        tools=SUBSTRATE_TOOL_DECLARATIONS,
        tool_dispatcher=sandbox.execute_tool,
        max_tool_rounds=args.max_tool_rounds,
        background=False,
        poll_interval_s=0.25,
        max_wait_s=120.0,
    )
    dt = time.perf_counter() - t0

    print(f"\n=== LIVE SESSION COMPLETE IN {dt:.2f}s ===")
    print("Interaction Chain:", telemetry.get("interaction_chain"))
    print(
        f"Token Telemetry: input={telemetry.get('input_tokens')} | "
        f"thought={telemetry.get('thought_tokens')} | "
        f"output={telemetry.get('output_tokens')} | "
        f"cached={telemetry.get('cached_input_tokens')}"
    )
    print(f"Thought Steps: {telemetry.get('thought_step_count')} | Thought Signatures: {len(telemetry.get('thought_signature_digests', []))}")

    print("\n--- LIVE MODEL THOUGHT SUMMARIES ---")
    for idx, ts in enumerate(telemetry.get("thought_summaries", []), 1):
        print(f"  [Thought {idx}] {ts[:400]}{'...' if len(ts) > 400 else ''}")

    print("\n--- LIVE SUBSTRATE TOOL CALLS EXECUTED ---")
    for idx, tex in enumerate(telemetry.get("tool_executions", []), 1):
        tname = tex.get("name") or tex.get("tool_name")
        targs = tex.get("arguments")
        tres = tex.get("result", {})
        compact_res = {
            k: (round(v, 4) if isinstance(v, float) else v)
            for k, v in tres.items()
            if isinstance(v, (int, float, bool, str)) and len(str(v)) < 60
        }
        print(f"  [Tool Call {idx}] {tname}({json.dumps(targs)})")
        print(f"     -> Substrate Result: {json.dumps(dict(list(compact_res.items())[:8]))}")

    print("\n--- FINAL SUBSTRATE-GROUNDED RESPONSE ---")
    print(telemetry.get("content", ""))

    if not args.no_record:
        ledger_path, md_path = record_companion_session(
            prompt=args.prompt,
            model=args.model,
            thinking_level=args.thinking_level,
            duration_s=dt,
            telemetry=telemetry,
            slug=args.slug,
            recorded_at_iso=args.recorded_at,
        )
        print(f"\n[Recorded] JSONL Ledger -> {ledger_path.relative_to(ROOT_DIR)}")
        print(f"[Recorded] Markdown Doc -> {md_path.relative_to(ROOT_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
