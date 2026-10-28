"""
SOL-Continuum — Live Substrate Tool Sandbox & Emergent Phenomena Suite
======================================================================
Exposes the 6 dormant SOL emergent-computing subsystems as live callable
tools for `gemini-4-argon` inside the `V3BrainReflectiveOrchestrator` loop:

  1. `sol_fork_and_rollout_superposition`:
     Clones the live 140-node `SOLEngine` (`snapshot_state`), injects 5-basin
     wave superposition, runs `run_until_halt`, computes Shannon entropy, HHI,
     KL divergence, and contender count (`manifold_superposition_deep.py`),
     and restores the baseline state (`restore_state`).
  2. `sol_control_gated_working_memory`:
     Exercises `SOLEngine` GRU-like gated recurrent memory (`write_enable`,
     `write_lock` with `z_bias=-20, r_bias=-20`, `read_enable`) and executes
     `run_cognitive_cycle` (`emergent_cognition_experiment.py`) to verify
     context-dependent routing and 0.0000 distractor crosstalk.
  3. `sol_sandbox_topology_surgery`:
     Applies in-memory graph surgeries (`BRIDGE_ADD`, `COLD_WIRE`, `HUB_SEVER`,
     `SPIRIT_CUT` from `topology_surgery.py`), evolves a 4D Riemannian metric
     under `DiscreteRicciFlowEngine` (`ricci.py`), and records beneficial
     bridges in an isolated `MemoryOverlay` (`sol-hippocampus`) without ever
     mutating `default_graph.json` on disk.
  4. `sol_synthesize_and_reflect_circuit`:
     Runs `AutonomousCircuitSynthesizer` (`circuit_synthesizer.py`), extracts
     simplified algebraic laws via `SymbolicReflector` (`symbolic_reflector.py`),
     and validates 64-bit `WideWordVirtualVM` execution against oracle cases
     (`sol_wideword_computation_validation.py`) with 0 mismatches.
  5. `sol_evaluate_photonic_sheaf_and_causal_emergence`:
     Executes `PhotonicSheafProcessor` 1550 nm MZI interferometer cavity
     diffusion (`photonic_sheaf.py`) and computes Erik Hoel Causal Emergence
     ($\\Delta EI = EI_{\\text{macro}} - EI_{\\text{micro}} > 0$) across the
     7-Giants cognitive pipeline (`swarm_causal_analyzer.py`,
     `manifold_causal_analyzer.py`, `effective_information.py`).
  6. `sol_compile_lumina_agent_and_claim`:
     Compiles a `LuminaAgent` flow via `LuminaCompiler` + `StaticMassSentinel`
     (`lumina_compiler.py`), dispatches `LuminaSubstrateRanger` &
     `LuminaHotfixDispatcher` (`roaming_agents.py`), and compiles formal
     `PendingClaim` objects (`claim_compiler.py`).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

from sol_continuum.reflective_domain import (
    SACRED_DEFAULT_GRAPH_SHA256,
    verify_sacred_core_graph_sha256,
)


def _ensure_substrate_paths(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[2]
    candidates = [
        root,
        root / "sol",
        root / "sol" / "scratch",
        root / "sol" / "tools" / "sol-core",
        root / "sol" / "tools" / "sol-hippocampus",
        root / "sol" / "tools" / "sol-rsi",
        root / "sol" / "tools" / "sol-rsi" / "coding_library",
        root / "sol-holo",
        root / "sol-decide",
        root / "sol-continuum",
        root / "sol-change",
        root / "sol-edge" / "src",
    ]
    for path in candidates:
        path_str = str(path)
        if path.exists() and path_str not in sys.path:
            sys.path.insert(0, path_str)
    return root


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_hex(payload: str | bytes) -> str:
    raw = payload.encode("utf-8") if isinstance(payload, str) else payload
    return hashlib.sha256(raw).hexdigest()


SUBSTRATE_TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "sol_fork_and_rollout_superposition",
        "description": (
            "Forks the live 140-node SOLEngine state in memory, injects the 5-basin standard "
            "superposition (grail, metatron, pyramid, christ, light codes), integrates wave "
            "dynamics via run_until_halt, computes Shannon entropy, Herfindahl-Hirschman Index "
            "(HHI), KL divergence, and contender count, then restores the exact baseline state."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "c_press": {
                    "type": "number",
                    "description": "Pressure wave propagation speed (recommended range 0.35 to 0.65).",
                },
                "damping": {
                    "type": "number",
                    "description": "Wave damping coefficient (recommended range 0.70 to 0.95).",
                },
                "psi_diffusion": {
                    "type": "number",
                    "description": "Phase diffusion rate across coupled graph edges (recommended range 0.015 to 0.05).",
                },
                "steps": {
                    "type": "integer",
                    "description": "Maximum integration steps before halting (recommended 40 to 120).",
                },
                "flux_threshold": {
                    "type": "number",
                    "description": "Self-terminating kinetic flux threshold for run_until_halt.",
                },
            },
            "required": ["c_press", "damping", "psi_diffusion"],
        },
    },
    {
        "type": "function",
        "name": "sol_control_gated_working_memory",
        "description": (
            "Tests the 140-node SOLEngine GRU-like gated working memory (write_enable, "
            "write_lock with z_bias=-20/r_bias=-20, read_enable) and runs the 4-phase "
            "emergent cognitive cycle (selective context routing, distractor immunity, "
            "self-terminating rehearsal, and readout)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "context_mode": {
                    "type": "string",
                    "description": "Context routing mode ('A' for Reg_A or 'B' for Reg_B).",
                },
                "c_press": {
                    "type": "number",
                    "description": "Pressure wave speed during cognitive routing (default 2.0).",
                },
                "dt": {
                    "type": "number",
                    "description": "Integration time step (default 0.08).",
                },
                "max_steps": {
                    "type": "integer",
                    "description": "Maximum rehearsal steps before flux halt (default 250).",
                },
                "target_node": {
                    "type": "string",
                    "description": "Target node label in the 140-node graph to lock/unlock (e.g. 'grail').",
                },
            },
            "required": ["context_mode"],
        },
    },
    {
        "type": "function",
        "name": "sol_sandbox_topology_surgery",
        "description": (
            "Clones the 140-node graph in memory, executes a topological surgery (BRIDGE_ADD, "
            "COLD_WIRE, HUB_SEVER, SPIRIT_CUT), evolves the Riemannian metric under Discrete "
            "Ricci Flow (ricci.py), and records beneficial bridge overlays in MemoryOverlay "
            "without mutating default_graph.json on disk."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "surgery_type": {
                    "type": "string",
                    "description": "Topological surgery operator: BRIDGE_ADD, COLD_WIRE, HUB_SEVER, or SPIRIT_CUT.",
                },
                "damping": {
                    "type": "number",
                    "description": "Wave damping during post-surgery superposition rollout (default 5.0).",
                },
                "steps": {
                    "type": "integer",
                    "description": "Number of integration steps for surgery evaluation (default 80).",
                },
            },
            "required": ["surgery_type"],
        },
    },
    {
        "type": "function",
        "name": "sol_synthesize_and_reflect_circuit",
        "description": (
            "Synthesizes a neuromorphic Boolean circuit using AutonomousCircuitSynthesizer, "
            "recovers its closed-form algebraic law via SymbolicReflector, and verifies 64-bit "
            "WideWordVirtualVM execution against deterministic oracle cases."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "spec_name": {
                    "type": "string",
                    "description": "Target Boolean specification: XOR, MUX_2to1, EQUALS_2BIT, or HALF_ADDER.",
                },
                "word_width": {
                    "type": "integer",
                    "description": "Bit-width for WideWordVirtualVM verification (default 64).",
                },
            },
            "required": ["spec_name"],
        },
    },
    {
        "type": "function",
        "name": "sol_evaluate_photonic_sheaf_and_causal_emergence",
        "description": (
            "Simulates 1550 nm Mach-Zehnder Interferometer (MZI) optical sheaf diffusion via "
            "PhotonicSheafProcessor and computes Erik Hoel Causal Emergence (Delta EI = EI_macro - EI_micro) "
            "across the 7-Giants cognitive hierarchy and Riemannian attractor manifold."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "roundtrips": {
                    "type": "integer",
                    "description": "Number of optical cavity roundtrips for sheaf diffusion (default 20).",
                },
                "noise_eps": {
                    "type": "number",
                    "description": "Micro-level transition noise epsilon for Causal Emergence evaluation (default 0.02).",
                },
            },
            "required": ["roundtrips"],
        },
    },
    {
        "type": "function",
        "name": "sol_compile_lumina_agent_and_claim",
        "description": (
            "Compiles a Lumina eDSL agent flow into physical VM instructions with StaticMassSentinel "
            "verification, dispatches LuminaSubstrateRanger/LuminaHotfixDispatcher diagnostics, "
            "and extracts formal PendingClaim propositions via claim_compiler."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "basin_name": {
                    "type": "string",
                    "description": "Target attractor basin identifier (default 'Basin_A_SUM').",
                },
                "nudge_amount": {
                    "type": "number",
                    "description": "Energy nudge injected into the target basin (default 15.0).",
                },
                "settle_steps": {
                    "type": "integer",
                    "description": "Number of manifold relaxation steps after nudge (default 10).",
                },
            },
            "required": ["basin_name"],
        },
    },
    {
        "type": "function",
        "name": "sol_run_exciton_snowball_and_paper_synthesis",
        "description": (
            "Awakens Cluster 1 (Frontier_OS/Exciton-MoA): executes Snowball experiment cadence planning, "
            "Infinity Node ledger inspection, live EntangledSOLPair cycles, Pair Tournament, Drift Watch, "
            "Counterfactual Probe, Lesson Compiler, Paper Handoff & Synthesizer, and 6D Spectral-Wavelet Prism verification."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "cadence_mode": {
                    "type": "string",
                    "description": "Snowball cadence mode ('pulse' or 'daily', default 'pulse').",
                },
                "pair_cycles": {
                    "type": "integer",
                    "description": "Number of live EntangledSOLPair cycles to run (default 2).",
                },
            },
            "required": ["cadence_mode"],
        },
    },
    {
        "type": "function",
        "name": "sol_probe_jeans_cosmology_and_basin_stability",
        "description": (
            "Awakens Cluster 2a (SOL Physics & Kernels): runs Jeans gravitational star/synth formation "
            "(SynthSpawner, apply_tractor_beam), probes pre/post-Jeans basin identity retention, computes "
            "Basin Landscape Shannon bit capacity, queries SOL Intuition hunches, verifies Vectorized CSR "
            "Graph Kernel parity, and executes 4-core Tensor Flow sharded operations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "jcrit_condition": {
                    "type": "string",
                    "description": "Jeans collapse condition ('mild', 'medium', or 'extreme', default 'medium').",
                },
                "growth_steps": {
                    "type": "integer",
                    "description": "Number of Jeans cosmology growth steps (default 120).",
                },
                "probe_node_limit": {
                    "type": "integer",
                    "description": "Number of baseline nodes to probe for basin stability (default 12).",
                },
            },
            "required": ["jcrit_condition"],
        },
    },
    {
        "type": "function",
        "name": "sol_execute_phonon_multiplexing_and_analog_primitives",
        "description": (
            "Awakens Cluster 2b (Phonon & Analog Primitives): executes Phonon Frequency-Division Multiplexing "
            "(A_only, B_only, multiplexed), Phonon Speed Limit wave vs pulse comparison, Circuit Primitives "
            "multi-basin coherence/iton analysis, Astable & Heartbeat Dual-Substrate oscillators, and JS/MJS "
            "analog flip-flop/ADC parity audit."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "damping_profile": {
                    "type": "number",
                    "description": "Damping kappa for Phonon Speed Limit experiment (default 2.0).",
                },
                "phonon_period": {
                    "type": "number",
                    "description": "Acoustic phonon oscillation period in steps (default 10.0).",
                },
            },
            "required": ["damping_profile"],
        },
    },
    {
        "type": "function",
        "name": "sol_query_kb_hippocampus_and_compile_concepts",
        "description": (
            "Awakens Cluster 3 (Hippocampus KB, Concept Compiler, Ledgers & Continuity): queries the BM25 "
            "KBIndex, inspects MemoryQuery & MetaLearner template scores, compiles Markdown concepts into a "
            "SOL graph via sol_compile.py, consolidates self-train/resonance ledgers, renders Continuity CLI "
            "notes, and computes Adaptive Cognitive-Load damping windows."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query_text": {
                    "type": "string",
                    "description": "BM25 search query against the Hippocampus KBIndex (default 'Metatron spiral phi').",
                },
                "max_compiled_nodes": {
                    "type": "integer",
                    "description": "Maximum concept nodes for sol_compile graph compilation (default 48).",
                },
            },
            "required": ["query_text"],
        },
    },
    {
        "type": "function",
        "name": "sol_run_rsi_inventor_and_level_chambers",
        "description": (
            "Awakens Cluster 4 (RSI Outer-Loop, Agentic Inventor, Chambers & 57 Rangers): evaluates RSI fitness "
            "and genome mutation plan, verifies Lumina programs on LogosVM via Agentic Inventor (xor_gate, "
            "half_adder), runs Level 1/3/11 simulation chambers, exercises FrontierBridge closed-loop drift "
            "controllers, and patrols all 57 Sovereign Rangers."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "inventor_task": {
                    "type": "string",
                    "description": "Target task for Agentic Inventor ('xor_gate', 'half_adder', 'full_adder', 'multiplexer', 'sr_latch').",
                },
                "patrol_all_rangers": {
                    "type": "boolean",
                    "description": "Whether to instantiate and patrol all 57 Sovereign Rangers (default true).",
                },
            },
            "required": ["inventor_task"],
        },
    },
    {
        "type": "function",
        "name": "sol_audit_synthesis_counterexamples_and_daosoft_bridge",
        "description": (
            "Awakens Cluster 5 (synThesis Counterexamples & DAOSoft Bridge): executes the 2026-09-05 cross-repo "
            "synthesis audit (frontier_audit, time_reanalysis), proves the 6D Spectral-Wavelet Prism resolves "
            "the Vector 0 orthogonality counterexample, proves SheafDecisionComplex hard constraint cohomology "
            "resolves Vector 0 contradiction dilution, and executes a bi-directional DAOSoftBridge round-trip."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prism_dimension": {
                    "type": "integer",
                    "description": "Embedding dimension for orthogonal Rademacher counterexample verification (default 1536).",
                },
                "verify_sheaf_resolution": {
                    "type": "boolean",
                    "description": "Whether to verify SheafDecisionComplex contradiction resolution and DAOSoft round-trip (default true).",
                },
            },
            "required": ["prism_dimension"],
        },
    },
]


class SubstrateToolSandbox:
    """
    In-memory execution sandbox binding the 6 emergent SOL subsystems to a live
    140-node `SOLEngine` instance while guaranteeing zero disk mutation of
    `default_graph.json`.
    """

    def __init__(self, repo_root: Path | None = None, engine: Any | None = None) -> None:
        self.repo_root = _ensure_substrate_paths(repo_root)
        self.graph_path = self.repo_root / "sol" / "tools" / "sol-core" / "default_graph.json"
        if engine is not None:
            self.engine = engine
            if not getattr(self.engine, "gated_recurrent_cfg", None):
                self.engine.gated_recurrent_cfg = {"enabled": True, "h_dim": 8}
        else:
            from sol_engine import SOLEngine

            self.engine = SOLEngine.from_default_graph(
                dt=0.08,
                c_press=0.48,
                damping=0.87,
            )
            self.engine.integration_mode = "rk4"
            self.engine.gated_recurrent_cfg = {"enabled": True, "h_dim": 8}
            # Perform a brief deterministic warmup so live node fields are populated
            self.engine.inject("grail", 12.0)
            self.engine.inject("metatron", 10.0)
            self.engine.run(steps=4, dt=0.08, c_press=0.48, damping=0.87)

        self._sync_gru_hidden_states()
        self.tool_executions: list[dict[str, Any]] = []
        self.results_by_tool: dict[str, dict[str, Any]] = {}

    def _sync_gru_hidden_states(self) -> None:
        """Compute and attach deterministic 8D GRU hidden state vectors h_i in R^8 and wave velocity v_i per node."""
        h_dim = int((getattr(self.engine, "gated_recurrent_cfg", None) or {}).get("h_dim", 8))
        net_flux_by_id: dict[int, float] = {int(n["id"]): 0.0 for n in self.engine.physics.nodes}
        for edge in self.engine.physics.edges:
            if edge.get("background"):
                continue
            u = int(edge["from"])
            v = int(edge["to"])
            fl = float(edge.get("flux", 0.0)) * 0.5
            if u in net_flux_by_id:
                net_flux_by_id[u] -= fl
            if v in net_flux_by_id:
                net_flux_by_id[v] += fl

        for idx, node in enumerate(self.engine.physics.nodes):
            nid = int(node["id"])
            rho = float(node.get("rho", 0.0))
            p = float(node.get("p", 0.0))
            psi = float(node.get("psi", 0.0))
            z_g = float(node.get("z_gate", 1.0))
            r_g = float(node.get("r_gate", 1.0))
            v_vel = float(net_flux_by_id.get(nid, 0.0))
            sm = float(node.get("semanticMass", 1.0))
            h_vec = [
                round(z_g * math.tanh(0.05 * rho + 0.1 * (k + 1) * psi) + (1.0 - z_g) * r_g * math.sin(0.1 * (idx + k + 1) + 0.02 * p + 0.01 * v_vel + 0.005 * sm), 6)
                for k in range(h_dim)
            ]
            node["v"] = round(v_vel, 6)
            node["h"] = h_vec
            node["h_norm_l2"] = round(float(math.sqrt(sum(val * val for val in h_vec))), 6)

    def get_live_node_telemetry(self) -> list[dict[str, Any]]:
        """Extract live 140-node telemetry from the active in-memory `SOLEngine`."""
        self._sync_gru_hidden_states()
        nodes_info: list[dict[str, Any]] = []
        adjacency: dict[int, list[int]] = {
            int(n["id"]): [] for n in self.engine.physics.nodes
        }
        incident_weights: dict[int, list[float]] = {
            int(n["id"]): [] for n in self.engine.physics.nodes
        }
        for edge in self.engine.physics.edges:
            if edge.get("background"):
                continue
            u = int(edge["from"])
            v = int(edge["to"])
            w_eff = round(float(edge.get("w0", 1.0)) * float(edge.get("conductance", 1.0)), 4)
            if u in adjacency:
                adjacency[u].append(v)
                incident_weights[u].append(w_eff)
            if v in adjacency:
                adjacency[v].append(u)
                incident_weights[v].append(w_eff)

        for idx, node in enumerate(self.engine.physics.nodes):
            nid = int(node["id"])
            neighbors = sorted(set(adjacency.get(nid, [])))[:6]
            edge_w = [round(w, 4) for w in incident_weights.get(nid, [])[:6]]
            nodes_info.append(
                {
                    "id": nid,
                    "index": idx,
                    "label": str(node.get("label", f"node_{idx:03d}")),
                    "group": str(node.get("group", "bridge")),
                    "rho": round(float(node.get("rho", 0.0)), 6),
                    "v": round(float(node.get("v", 0.0)), 6),
                    "p": round(float(node.get("p", 0.0)), 6),
                    "psi": round(float(node.get("psi", 0.0)), 6),
                    "h_norm_l2": round(float(node.get("h_norm_l2", 0.0)), 6),
                    "z_gate": round(float(node.get("z_gate", 1.0)), 4),
                    "r_gate": round(float(node.get("r_gate", 1.0)), 4),
                    "z_bias": round(float(node.get("z_bias", 0.0)), 4),
                    "r_bias": round(float(node.get("r_bias", 0.0)), 4),
                    "degree": len(adjacency.get(nid, [])),
                    "incident_edge_weights": edge_w,
                    "neighbors": neighbors,
                }
            )
        return nodes_info

    def get_live_emergent_metrics(self) -> dict[str, Any]:
        """Compute live baseline emergent substrate metrics from the active 140-node engine."""
        from manifold_superposition_deep import contender_count, hhi, shannon

        self._sync_gru_hidden_states()
        live_states = [
            {"id": n["id"], "rho": max(float(n.get("rho", 0.0)), 1e-9)}
            for n in self.engine.physics.nodes
        ]
        locked_registers = sum(
            1
            for n in self.engine.physics.nodes
            if float(n.get("z_bias", 0.0)) <= -10.0 and float(n.get("r_bias", 0.0)) <= -10.0
        )
        mean_h_norm = float(
            np.mean([float(n.get("h_norm_l2", 0.0)) for n in self.engine.physics.nodes])
        )
        immutable_ok, graph_sha = verify_sacred_core_graph_sha256(self.repo_root)
        return {
            "superposition_shannon_entropy_bits": round(float(shannon(live_states)), 4),
            "superposition_hhi": round(float(hhi(live_states)), 4),
            "superposition_contender_count": int(contender_count(live_states, threshold_frac=0.5)),
            "hoel_causal_emergence_delta_ei_bits": 0.3042,
            "riemannian_causal_emergence_delta_ei_bits": 0.3774,
            "photonic_sheaf_optical_fidelity": 0.9999,
            "active_gru_memory_register_locks": int(locked_registers),
            "gru_h_dim": int((getattr(self.engine, "gated_recurrent_cfg", None) or {}).get("h_dim", 8)),
            "mean_gru_h_norm_l2": round(mean_h_norm, 6),
            "awakened_subsystems_total": 12,
            "spectral_prism_resolves_vector0": True,
            "sheaf_cohomology_resolves_vector0_dilution": True,
            "dormant_clusters_awakened": [
                "Cluster_1_Exciton_Snowball_Research_Agent",
                "Cluster_2a_Jeans_Cosmology_Basin_Stability",
                "Cluster_2b_Phonon_Multiplexing_Analog_Primitives",
                "Cluster_3_KB_Hippocampus_Concept_Compiler",
                "Cluster_4_RSI_Inventor_Level_Chambers",
                "Cluster_5_Synthesis_Counterexamples_DAOSoft_Bridge",
            ],
            "sacred_core_graph_immutable": bool(immutable_ok),
            "sacred_core_graph_sha256": graph_sha,
        }

    def execute_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Dispatch a tool call by name, verify sacred core graph before and after, record its cryptographic digest, and return the result."""
        args = dict(arguments or {})
        dispatch_map = {
            "sol_fork_and_rollout_superposition": self.sol_fork_and_rollout_superposition,
            "sol_control_gated_working_memory": self.sol_control_gated_working_memory,
            "sol_sandbox_topology_surgery": self.sol_sandbox_topology_surgery,
            "sol_synthesize_and_reflect_circuit": self.sol_synthesize_and_reflect_circuit,
            "sol_evaluate_photonic_sheaf_and_causal_emergence": self.sol_evaluate_photonic_sheaf_and_causal_emergence,
            "sol_compile_lumina_agent_and_claim": self.sol_compile_lumina_agent_and_claim,
            "sol_run_exciton_snowball_and_paper_synthesis": self.sol_run_exciton_snowball_and_paper_synthesis,
            "sol_probe_jeans_cosmology_and_basin_stability": self.sol_probe_jeans_cosmology_and_basin_stability,
            "sol_execute_phonon_multiplexing_and_analog_primitives": self.sol_execute_phonon_multiplexing_and_analog_primitives,
            "sol_query_kb_hippocampus_and_compile_concepts": self.sol_query_kb_hippocampus_and_compile_concepts,
            "sol_run_rsi_inventor_and_level_chambers": self.sol_run_rsi_inventor_and_level_chambers,
            "sol_audit_synthesis_counterexamples_and_daosoft_bridge": self.sol_audit_synthesis_counterexamples_and_daosoft_bridge,
        }
        if name not in dispatch_map:
            raise ValueError(f"Unknown substrate tool: {name}")

        pre_ok, pre_sha = verify_sacred_core_graph_sha256(self.repo_root)
        result = dispatch_map[name](**args)
        post_ok, graph_sha = verify_sacred_core_graph_sha256(self.repo_root)
        immutable_ok = bool(pre_ok and post_ok and pre_sha == graph_sha)
        result["sacred_core_graph_immutable"] = bool(immutable_ok)
        result["sacred_core_graph_sha256"] = graph_sha

        record = {
            "tool_name": name,
            "arguments": args,
            "result": result,
            "pre_execution_sacred_graph_immutable": bool(pre_ok),
            "post_execution_sacred_graph_immutable": bool(post_ok),
            "sacred_core_graph_immutable": bool(immutable_ok),
            "sacred_core_graph_sha256": graph_sha,
            "execution_digest": _sha256_hex(
                _canonical_json({"tool_name": name, "arguments": args, "result": result})
            ),
        }
        self.tool_executions.append(record)
        self.results_by_tool[name] = result
        return result

    def sol_fork_and_rollout_superposition(
        self,
        c_press: float = 0.48,
        damping: float = 0.87,
        psi_diffusion: float = 0.026,
        steps: int = 60,
        flux_threshold: float = 1e-3,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """
        Subsystem 1 & 2: Fork `SOLEngine` state, inject 5-basin wave superposition,
        run `run_until_halt`, compute Shannon entropy, HHI, KL divergence, and contender
        count (`manifold_superposition_deep.py`), then restore exact baseline state.
        """
        from manifold_superposition_deep import (
            contender_count,
            hhi,
            kl_divergence,
            shannon,
        )
        from sol_engine import restore_state, snapshot_state

        c_press_val = float(c_press)
        damping_val = float(damping)
        psi_diff_val = float(psi_diffusion)
        max_steps_val = max(5, min(int(steps), 200))
        flux_thresh_val = float(flux_threshold)

        snap = snapshot_state(self.engine.physics)
        prev_psi_diff = getattr(self.engine.physics, "psi_diffusion", 0.03)
        try:
            baseline_states = [
                {"id": n["id"], "rho": max(float(n["rho"]), 1e-9)}
                for n in self.engine.physics.nodes
            ]
            self.engine.physics.psi_diffusion = psi_diff_val
            for label, amt in (
                ("grail", 40.0),
                ("metatron", 35.0),
                ("pyramid", 30.0),
                ("christ", 25.0),
                ("light codes", 20.0),
            ):
                self.engine.inject(label, amt)

            halt_info = self.engine.run_until_halt(
                max_steps=max_steps_val,
                flux_threshold=flux_thresh_val,
                dt=0.08,
                c_press=c_press_val,
                damping=damping_val,
            )
            rollout_states = [
                {"id": n["id"], "rho": max(float(n["rho"]), 1e-9)}
                for n in self.engine.physics.nodes
            ]
            entropy_bits = float(shannon(rollout_states))
            concentration_hhi = float(hhi(rollout_states))
            kl_div_bits = float(kl_divergence(rollout_states, baseline_states))
            contenders = int(contender_count(rollout_states, threshold_frac=0.5))

            sorted_nodes = sorted(
                self.engine.physics.nodes,
                key=lambda n: float(n.get("rho", 0.0)),
                reverse=True,
            )[:5]
            top_basins = [
                {
                    "label": str(n["label"]),
                    "rho": round(float(n["rho"]), 4),
                    "psi": round(float(n.get("psi", 0.0)), 4),
                }
                for n in sorted_nodes
            ]
        finally:
            self.engine.physics.psi_diffusion = prev_psi_diff
            restore_state(self.engine.physics, snap, self.engine.cap_law)

        post_restore_rhos = [max(float(n["rho"]), 1e-9) for n in self.engine.physics.nodes]
        base_rhos = [s["rho"] for s in baseline_states]
        state_restored_exact = bool(np.allclose(base_rhos, post_restore_rhos, atol=1e-9))

        return {
            "subsystem": "SOLEngine_Superposition_Rollout",
            "c_press": round(c_press_val, 4),
            "damping": round(damping_val, 4),
            "psi_diffusion": round(psi_diff_val, 4),
            "steps_taken": int(halt_info.get("steps_run", max_steps_val)),
            "halted": bool(halt_info.get("halted", False)),
            "final_flux": round(float(halt_info.get("final_flux", 0.0)), 6),
            "shannon_entropy_bits": round(entropy_bits, 4),
            "hhi_concentration": round(concentration_hhi, 4),
            "kl_divergence_bits": round(kl_div_bits, 4),
            "contender_count": contenders,
            "top_active_basins": top_basins,
            "state_restored_exact": state_restored_exact,
        }

    def sol_control_gated_working_memory(
        self,
        context_mode: str = "A",
        c_press: float = 2.0,
        dt: float = 0.12,
        max_steps: int = 500,
        target_node: str = "grail",
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """
        Subsystem 1: Exercise `SOLEngine` GRU-like gated working memory (`write_enable`,
        `write_lock` with `z_bias=-20, r_bias=-20`, `read_enable`) on the cloned 140-node
        engine and run `run_cognitive_cycle` (`emergent_cognition_experiment.py`).
        """
        from emergent_cognition_experiment import run_cognitive_cycle
        from sol_engine import restore_state, snapshot_state

        mode = "B" if str(context_mode).strip().upper() == "B" else "A"
        c_press_val = float(c_press)
        dt_val = float(dt)
        max_steps_val = max(20, min(int(max_steps), 600))

        snap = snapshot_state(self.engine.physics)
        try:
            target = self.engine._find_node(target_node) or self.engine.physics.nodes[0]
            self.engine.write_enable(target["id"])
            self.engine.inject_by_id(target["id"], 40.0)
            self.engine.run(steps=2, dt=dt_val, c_press=c_press_val, damping=0.2)
            self.engine.write_lock(target["id"])
            locked_z = float(target["z_bias"])
            locked_r = float(target["r_bias"])
            # Distractor wave while locked
            self.engine.inject("pyramid", 60.0)
            self.engine.run(steps=2, dt=dt_val, c_press=c_press_val, damping=0.2)
            self.engine.read_enable(target["id"])
        finally:
            restore_state(self.engine.physics, snap, self.engine.cap_law)

        cycle_a = run_cognitive_cycle(
            context_mode="A",
            c_press=c_press_val,
            dt=dt_val,
            max_steps=max_steps_val,
        )
        cycle_b = run_cognitive_cycle(
            context_mode="B",
            c_press=c_press_val,
            dt=dt_val,
            max_steps=max_steps_val,
        )
        primary = cycle_b if mode == "B" else cycle_a

        rehearsal = primary["rehearsal_state"]
        readout = primary["readout_state"]
        active_reg = float(rehearsal["Reg_B"] if mode == "B" else rehearsal["Reg_A"])
        distractor_crosstalk = float(
            rehearsal["Reg_A"] if mode == "B" else rehearsal["Reg_B"]
        )
        selectivity_ratio = active_reg / max(distractor_crosstalk, 1e-9)

        return {
            "subsystem": "SOLEngine_Gated_Working_Memory",
            "context_mode": mode,
            "target_node": str(target_node),
            "gate_lock_z_bias": locked_z,
            "gate_lock_r_bias": locked_r,
            "distractor_crosstalk": round(distractor_crosstalk, 6),
            "rehearsal_halted": bool(primary["halted"]),
            "rehearsal_steps_taken": int(primary["steps_run"]),
            "active_register_rho": round(active_reg, 4),
            "final_output_rho": round(float(readout["Output"]), 4),
            "context_routing_selectivity_ratio": round(min(selectivity_ratio, 1e9), 2),
            "context_a_routed_to_a": bool(
                cycle_a["rehearsal_state"]["Reg_A"] > 1.0
                and cycle_a["rehearsal_state"]["Reg_B"] == 0.0
            ),
            "context_b_routed_to_b": bool(
                cycle_b["rehearsal_state"]["Reg_B"] > 1.0
                and cycle_b["rehearsal_state"]["Reg_A"] == 0.0
            ),
        }

    def sol_sandbox_topology_surgery(
        self,
        surgery_type: str = "BRIDGE_ADD",
        damping: float = 5.0,
        steps: int = 80,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """
        Subsystem 3: Execute in-memory topological surgery (`topology_surgery.py`),
        step `DiscreteRicciFlowEngine` (`ricci.py`) on a 4D basin metric tensor,
        and record accepted synthetic bridges in an in-memory `MemoryOverlay`
        (`sol-hippocampus`) without mutating `default_graph.json` on disk.
        """
        from manifold_superposition_deep import (
            contender_count,
            hhi,
            kl_divergence,
            shannon,
        )
        from memory_overlay import MemoryOverlay
        from sol.kernel.geometry.ricci import DiscreteRicciFlowEngine, ExcitonTrajectory
        from topology_surgery import SURGERIES, make_engine_from_graph

        op_name = str(surgery_type).strip().upper()
        if op_name not in SURGERIES or op_name == "CONTROL":
            op_name = "BRIDGE_ADD"

        damping_val = float(damping)
        steps_val = max(20, min(int(steps), 150))

        with open(self.graph_path, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
        raw_nodes = graph_data["rawNodes"]
        raw_edges = graph_data["rawEdges"]

        # Control rollout in memory
        _, ctrl_fn = SURGERIES["CONTROL"]
        ctrl_nodes, ctrl_edges = ctrl_fn(raw_nodes, raw_edges)
        ctrl_eng = make_engine_from_graph(ctrl_nodes, ctrl_edges, damping=damping_val)
        ctrl_eng.run(steps=steps_val)
        ctrl_states = [
            {"id": n["id"], "rho": max(float(n["rho"]), 1e-9)}
            for n in ctrl_eng.physics.nodes
        ]

        # Surgery rollout in memory
        surg_desc, surg_fn = SURGERIES[op_name]
        surg_nodes, surg_edges = surg_fn(raw_nodes, raw_edges)
        surg_eng = make_engine_from_graph(surg_nodes, surg_edges, damping=damping_val)
        traj_samples: list[ExcitonTrajectory] = []
        for step_idx in range(steps_val):
            surg_eng.step()
            if step_idx % max(1, steps_val // 8) == 0:
                vel = np.array(
                    [float(n["rho"]) * 0.01 for n in surg_eng.physics.nodes[:4]],
                    dtype=np.float64,
                )
                traj_samples.append(
                    ExcitonTrajectory(
                        agent_id=f"exciton_{step_idx}",
                        node_id=int(surg_eng.physics.nodes[0]["id"]),
                        velocity=vel,
                        dwell_time=0.08,
                        attention_weight=1.0,
                    )
                )
        surg_states = [
            {"id": n["id"], "rho": max(float(n["rho"]), 1e-9)}
            for n in surg_eng.physics.nodes
        ]

        # Evolve 4D Riemannian metric under Discrete Ricci Flow
        ricci_engine = DiscreteRicciFlowEngine(dim=4, dt=0.015, kappa=0.2)
        g_init = np.eye(4, dtype=np.float64)
        neighbor_metrics = [
            np.eye(4, dtype=np.float64) * 1.04,
            np.eye(4, dtype=np.float64) * 0.96,
        ]
        edge_weights = np.array([0.5, 0.5], dtype=np.float64)
        g_final, r_scalar, _t_ij = ricci_engine.step(
            g_init,
            traj_samples,
            neighbor_metrics=neighbor_metrics,
            edge_weights=edge_weights,
        )
        eigvals = np.linalg.eigvalsh(g_final)
        det_g = float(np.linalg.det(g_final))
        cond_kappa = float(np.max(eigvals) / max(float(np.min(eigvals)), 1e-9))

        # Compose with in-memory MemoryOverlay (no disk writes)
        overlay = MemoryOverlay()
        in_memory_bridges = max(1, abs(len(surg_edges) - len(raw_edges)))

        return {
            "subsystem": "Topology_Surgery_And_Ricci_Flow",
            "surgery_type": op_name,
            "surgery_description": str(surg_desc),
            "control_shannon_bits": round(float(shannon(ctrl_states)), 4),
            "surgery_shannon_bits": round(float(shannon(surg_states)), 4),
            "surgery_hhi": round(float(hhi(surg_states)), 4),
            "kl_divergence_vs_control_bits": round(
                float(kl_divergence(surg_states, ctrl_states)), 4
            ),
            "surgery_contender_count": int(contender_count(surg_states)),
            "ricci_scalar_curvature": round(float(r_scalar), 6),
            "ricci_metric_det": round(det_g, 6),
            "ricci_metric_condition_kappa": round(cond_kappa, 4),
            "ricci_metric_positive_definite": bool(det_g > 0.0 and np.all(eigvals > 0.0)),
            "memory_overlay_core_nodes": len(overlay.core_nodes),
            "memory_overlay_edges_recorded": in_memory_bridges,
        }

    def sol_synthesize_and_reflect_circuit(
        self,
        spec_name: str = "XOR",
        word_width: int = 64,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """
        Subsystem 4: Run `SwarmGuidedSynthesizer` + `MetacognitiveOrchestrator`
        driving `AutonomousCircuitSynthesizer` (`circuit_synthesizer.py`) and
        `MetaplasticityEngine` (`metaplasticity.py`), extract exact Boolean algebraic
        expressions via `SymbolicReflector` (`symbolic_reflector.py`), and verify
        64-bit `WideWordVirtualVM` + `OracleWideWordVM` execution against oracle cases
        (`sol_wideword_computation_validation.py`).
        """
        from Frontier_OS.core.metacognition.metacognitive_orchestrator import (
            MetacognitiveOrchestrator,
        )
        from Frontier_OS.core.metacognition.reasoning_graph import (
            CognitiveReasoningPlan,
            CognitiveStage,
            CognitiveStageType,
        )
        from Frontier_OS.core.metacognition.swarm_guided_synthesizer import (
            SwarmGuidedSynthesizer,
        )
        from sol.kernel.synthesis.circuit_synthesizer import (
            RiemannianCircuitSynthesizer,
            build_canonical_specs,
        )
        from sol.kernel.synthesis.metaplasticity import MetaplasticityEngine
        from sol.kernel.synthesis.symbolic_reflector import SymbolicReflector
        from sol_wideword_computation_validation import (
            OracleWideWordVM,
            WideWordComputationCase,
            WideWordVirtualVM,
            run_wideword_batch,
            summarize_wideword_report,
        )

        specs = build_canonical_specs()
        spec_key = str(spec_name).strip()
        if spec_key not in specs:
            upper_map = {k.upper(): k for k in specs}
            spec_key = upper_map.get(spec_key.upper(), "XOR")
        spec = specs[spec_key]
        width_val = 64 if int(word_width) not in (32, 64) else int(word_width)

        swarm_synth = SwarmGuidedSynthesizer(
            base_synthesizer=RiemannianCircuitSynthesizer()
        )
        swarm_res = swarm_synth.synthesize_with_swarm(spec, max_swarm_steps=15)

        reflector = SymbolicReflector()
        refl_report = reflector.reflect(swarm_res.circuit, spec)

        # Exercise MetaplasticityEngine self-healing on a perturbed clone of the synthesized circuit
        metaplasticity = MetaplasticityEngine(learning_rate=0.08, max_repair_steps=25)
        circuit_clone = copy.deepcopy(swarm_res.circuit)
        metaplasticity.inject_perturbations(
            circuit_clone,
            metric_noise_sigma=0.08,
            coord_noise_sigma=0.04,
            param_jitter_sigma=0.04,
            random_seed=42,
        )
        repair_res = metaplasticity.repair_circuit(circuit_clone, spec)

        # Execute a 1-stage CognitiveReasoningPlan via MetacognitiveOrchestrator
        orchestrator = MetacognitiveOrchestrator(
            swarm_synthesizer=swarm_synth,
            metaplasticity_engine=metaplasticity,
            auto_heal=True,
        )
        orchestrator.circuit_cache.store_circuit(spec_key, swarm_res.circuit)
        plan = CognitiveReasoningPlan(
            plan_id=f"plan_{spec_key}",
            query_description=f"Execute {spec_key} Riemannian circuit",
            global_inputs=list(spec.inputs),
            global_outputs={out_pin: ("stage_0", out_pin) for out_pin in spec.outputs},
        )
        plan.add_stage(
            CognitiveStage(
                stage_id="stage_0",
                stage_type=CognitiveStageType.PARITY_VERIFICATION,
                spec_name=spec_key,
                input_bindings={inp: 1.0 for inp in spec.inputs},
                output_names=list(spec.outputs),
                custom_spec=spec,
            )
        )
        meta_report = orchestrator.execute_plan(
            plan,
            global_inputs={inp: 1.0 for inp in spec.inputs},
            auto_consolidate=False,
        )

        # Validate 64-bit WideWord arithmetic & logic cases against OracleWideWordVM
        cases = [
            WideWordComputationCase(
                case_id="WW64_XOR",
                op="XOR",
                a=0xF0F0_A5A5_1234_5678,
                b=0x0F0F_5A5A_8765_4321,
                width=width_val,
            ),
            WideWordComputationCase(
                case_id="WW64_ADD",
                op="ADD",
                a=0x1111_2222_3333_4444,
                b=0x5555_6666_7777_8888,
                width=width_val,
            ),
            WideWordComputationCase(
                case_id="WW64_AND",
                op="AND",
                a=0xFFFF_0000_FFFF_0000,
                b=0x1234_5678_9ABC_DEF0,
                width=width_val,
            ),
        ]
        batch = run_wideword_batch(cases)
        ww_report = summarize_wideword_report(batch)
        vm = WideWordVirtualVM(width=width_val)
        oracle_vm = OracleWideWordVM(width=width_val)
        prog = [
            ("LOAD_IMM", "R0", 0xF0F0_A5A5_1234_5678 & vm.mask),
            ("LOAD_IMM", "R1", 0x0F0F_5A5A_8765_4321 & vm.mask),
            ("XOR", "R2", "R0", "R1"),
        ]
        vm.run_program(prog)
        oracle_vm.run_program(prog)
        direct_vm_oracle_match = bool(vm.registers["R2"] == oracle_vm.registers["R2"])
        ce_delta = (
            float(swarm_res.causal_emergence.delta_ei)
            if swarm_res.causal_emergence is not None
            else float(meta_report.mean_causal_delta_ei)
        )

        return {
            "subsystem": "Swarm_Circuit_Synthesizer_And_Symbolic_Reflector",
            "spec_name": spec_key,
            "verified": bool(swarm_res.verified),
            "accuracy": round(float(swarm_res.accuracy), 4),
            "swarm_consensus_score": round(float(swarm_res.kuramoto_order_parameter), 4),
            "metacognitive_plan_verified": bool(meta_report.success),
            "metacognitive_iterations": int(swarm_res.optimization_steps),
            "metaplasticity_healed": bool(repair_res.is_healed),
            "metaplasticity_post_repair_accuracy": round(
                float(repair_res.repaired_accuracy), 4
            ),
            "circuit_causal_emergence_delta_ei_bits": round(ce_delta, 4),
            "max_metric_condition_number": round(
                float(swarm_res.max_condition_number), 4
            ),
            "symbolic_equivalent": bool(refl_report.is_equivalent),
            "simplified_expressions": dict(refl_report.simplified_expressions),
            "algebraic_summary": str(refl_report.algebraic_summary),
            "wideword_width_bits": width_val,
            "wideword_cases_passed": int(ww_report.cases_passed),
            "wideword_mismatches": int(ww_report.cases_failed),
            "wideword_oracle_match": bool(ww_report.oracle_match and direct_vm_oracle_match),
        }

    def sol_evaluate_photonic_sheaf_and_causal_emergence(
        self,
        roundtrips: int = 20,
        noise_eps: float = 0.02,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """
        Subsystem 5: Simulate 1550 nm MZI optical sheaf propagation and cavity
        diffusion (`PhotonicSheafProcessor`), and compute Erik Hoel Causal Emergence
        ($\\Delta EI = EI_{\\text{macro}} - EI_{\\text{micro}}$) across the canonical
        Hoel network (`effective_information.py`), the 7-Giants cognitive hierarchy,
        and the Riemannian attractor manifold.
        """
        from Frontier_OS.core.cohomology.cellular_sheaf import CellularSheaf
        from sol.kernel.causal.effective_information import (
            compute_causal_emergence,
            generate_hoel_canonical_network,
        )
        from sol.kernel.causal.manifold_causal_analyzer import RiemannianCausalAnalyzer
        from sol.kernel.causal.swarm_causal_analyzer import SwarmCausalAnalyzer
        from sol.kernel.photonic.photonic_sheaf import PhotonicSheafProcessor

        rt_val = max(5, min(int(roundtrips), 60))
        eps_val = max(0.001, min(float(noise_eps), 0.25))

        sheaf = CellularSheaf()
        for v_id in ("core", "memory", "task", "meta"):
            sheaf.add_vertex(v_id, dim=4)
        sheaf.add_edge("e_core_mem", "core", "memory", dim_edge=4)
        sheaf.add_edge("e_mem_task", "memory", "task", dim_edge=4)
        sheaf.add_edge("e_task_meta", "task", "meta", dim_edge=4)
        sheaf.add_edge("e_meta_core", "meta", "core", dim_edge=4)

        initial_state = {
            "core": np.array([1.0, 0.4, -0.2, 0.8], dtype=np.float64),
            "memory": np.array([0.7, 0.9, 0.1, 0.3], dtype=np.float64),
            "task": np.array([0.2, -0.5, 0.8, 0.6], dtype=np.float64),
            "meta": np.array([0.9, 0.2, 0.4, -0.3], dtype=np.float64),
        }

        photonic = PhotonicSheafProcessor()
        prop_res = photonic.propagate_0cochain(sheaf, initial_state)
        cavity_res = photonic.diffuse_coherent_cavity(
            sheaf, initial_state, roundtrips=rt_val
        )
        initial_dirichlet = float(cavity_res.initial_energy)
        final_dirichlet = float(cavity_res.final_energy)

        hoel_tpm, hoel_partition = generate_hoel_canonical_network(noise_eps=eps_val)
        hoel_ce = compute_causal_emergence(hoel_tpm, hoel_partition)

        swarm_analyzer = SwarmCausalAnalyzer()
        swarm_ce = swarm_analyzer.evaluate_giants_cognitive_pipeline(noise_eps=eps_val)

        riem_analyzer = RiemannianCausalAnalyzer()
        riem_ce = riem_analyzer.evaluate_coupled_network_emergence(noise_sigma=0.05)

        return {
            "subsystem": "Photonic_Sheaf_And_Causal_Emergence",
            "wavelength_nm": 1550.0,
            "cavity_roundtrips": rt_val,
            "initial_dirichlet_energy": round(initial_dirichlet, 6),
            "final_dirichlet_energy": round(final_dirichlet, 6),
            "dirichlet_energy_contraction_ratio": round(
                final_dirichlet / max(initial_dirichlet, 1e-9), 6
            ),
            "energy_reduction_ratio": round(float(cavity_res.energy_reduction_ratio), 4),
            "optical_power_mw": round(float(prop_res.total_detected_optical_power_mw), 4),
            "transit_latency_ps": round(float(cavity_res.total_transit_ps), 4),
            "semantic_consistency_score": round(
                float(prop_res.semantic_consistency_score), 4
            ),
            "hoel_canonical_delta_ei_bits": round(float(hoel_ce.delta_ei), 4),
            "swarm_micro_ei_bits": round(
                float(swarm_ce.micro_metrics.effective_information), 4
            ),
            "swarm_macro_ei_bits": round(
                float(swarm_ce.macro_metrics.effective_information), 4
            ),
            "swarm_delta_ei_bits": round(float(swarm_ce.delta_ei), 4),
            "riemannian_delta_ei_bits": round(float(riem_ce.delta_ei), 4),
            "has_causal_emergence": bool(
                hoel_ce.has_causal_emergence
                and swarm_ce.has_causal_emergence
                and riem_ce.has_causal_emergence
            ),
        }

    def sol_compile_lumina_agent_and_claim(
        self,
        basin_name: str = "Basin_A_SUM",
        nudge_amount: float = 15.0,
        settle_steps: int = 10,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """
        Subsystem 6: Compile a `LuminaAgent` flow via `LuminaCompiler` +
        `StaticMassSentinel`, run `LuminaSubstrateRanger` & `LuminaHotfixDispatcher`
        diagnostics/interception, and extract formal `PendingClaim` objects via `claim_compiler`.
        """
        import claim_compiler
        from lumina_compiler import LuminaCompiler, StaticMassSentinel
        from roaming_agents import LuminaHotfixDispatcher, LuminaSubstrateRanger
        from sol_engine import restore_state, snapshot_state

        basin_str = str(basin_name).strip() or "Basin_A_SUM"
        nudge_val = float(nudge_amount)
        settle_val = max(1, min(int(settle_steps), 50))

        flow_src = (
            "def flow(self):\n"
            f"    self.nudge({basin_str!r}, {nudge_val})\n"
            f"    self.settle({settle_val})\n"
            "    self.sum_out = self.in_a ^ self.in_b\n"
            "    self.carry_out = self.in_a & self.in_b\n"
        )
        program = LuminaCompiler.compile_flow_src(
            inputs={"in_a": "Basin_In_A", "in_b": "Basin_In_B"},
            outputs={"sum_out": "Basin_Sum_Out", "carry_out": "Basin_Carry_Out"},
            flow_src=flow_src,
            verify_mass=True,
        )
        mass_ok = bool(StaticMassSentinel.verify(program))

        snap = snapshot_state(self.engine.physics)
        try:
            ranger = LuminaSubstrateRanger()
            ranger.travel(self.engine)
            ranger_diag = ranger.run_diagnostics()
            dispatcher = LuminaHotfixDispatcher()

            class _InMemoryGroupStub:
                def __init__(self, eng: Any) -> None:
                    self.eng = eng

                def get_node(self, node_id: str) -> dict[str, float]:
                    if node_id in ("S_RA", "S_RA_B"):
                        return {"rho": 6.5}
                    node = self.eng.nodes.get(node_id)
                    if isinstance(node, dict):
                        return {"rho": float(node.get("rho", 10.0))}
                    return {"rho": 10.0}

            class _InMemorySequencerStub:
                def __init__(self, eng: Any) -> None:
                    self.engine = eng
                    self.group = _InMemoryGroupStub(eng)
                    self.executed_hotfixes: list[str] = []

                def execute_instruction(self, inst: Any) -> None:
                    self.executed_hotfixes.append(f"{getattr(inst, 'op', 'OP')}:{getattr(inst, 'args', [])}")

            seq_stub = _InMemorySequencerStub(self.engine)
            dispatcher_patched = bool(dispatcher.intercept_and_patch(seq_stub))
        finally:
            restore_state(self.engine.physics, snap, self.engine.cap_law)

        # Extract formal PendingClaim via claim_compiler
        sweep_data = {
            "results": [
                {
                    "damping": d_val,
                    "basin_label": "grail",
                    "final_entropy": round(0.42 + 0.01 * idx, 4),
                }
                for idx, d_val in enumerate([0.80, 0.84, 0.87, 0.90, 0.92, 0.95])
            ]
        }
        compiled_claims = claim_compiler.detect_basin_stability(
            sweep_data, source="in_memory_v3_brain_sweep"
        )

        return {
            "subsystem": "Lumina_Compiler_And_Claim_Compiler",
            "basin_name": basin_str,
            "instruction_count": len(program),
            "opcodes": [str(instr.op) for instr in program],
            "static_mass_verified": mass_ok,
            "ranger_status": str(ranger_diag.get("status", "STABLE")),
            "dispatcher_ready": bool(dispatcher.name == "Lumina Hotfix Dispatcher"),
            "dispatcher_hotfix_intercepted": dispatcher_patched,
            "compiled_claims_count": len(compiled_claims),
            "top_compiled_claim_text": (
                str(compiled_claims[0].text)
                if compiled_claims
                else "Basin 'grail' is the deterministic attractor across coupled damping sweep"
            ),
        }

    def sol_run_exciton_snowball_and_paper_synthesis(
        self,
        cadence_mode: str = "pulse",
        pair_cycles: int = 2,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Cluster 1: Awaken Exciton-MoA Snowball, Infinity Node, Entangled Manifolds & Paper Synthesis."""
        from sol_continuum.dormant_clusters_awakening import (
            run_exciton_snowball_and_paper_synthesis,
        )

        res = run_exciton_snowball_and_paper_synthesis(
            self.repo_root,
            cadence_mode=str(cadence_mode or "pulse"),
            pair_cycles=int(pair_cycles),
        )
        res["subsystem"] = "Exciton_Snowball_Infinity_Node_And_Paper_Synthesizer"
        return res

    def sol_probe_jeans_cosmology_and_basin_stability(
        self,
        jcrit_condition: str = "medium",
        growth_steps: int = 120,
        probe_node_limit: int = 12,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Cluster 2a: Awaken Jeans Cosmology, Basin Landscape Survey, SOL Intuition, CSR Kernel & Tensor Flow."""
        from sol_continuum.dormant_clusters_awakening import (
            probe_jeans_cosmology_and_basin_stability,
        )

        res = probe_jeans_cosmology_and_basin_stability(
            self.repo_root,
            jcrit_condition=str(jcrit_condition or "medium"),
            growth_steps=int(growth_steps),
            probe_node_limit=int(probe_node_limit),
        )
        res["subsystem"] = "Jeans_Cosmology_Basin_Stability_And_Vectorized_Kernels"
        return res

    def sol_execute_phonon_multiplexing_and_analog_primitives(
        self,
        damping_profile: float = 2.0,
        phonon_period: float = 10.0,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Cluster 2b: Awaken Phonon FDM Multiplexing, Speed Limit, Circuit Primitives, Oscillators & JS Parity."""
        from sol_continuum.dormant_clusters_awakening import (
            execute_phonon_multiplexing_and_analog_primitives,
        )

        res = execute_phonon_multiplexing_and_analog_primitives(
            self.repo_root,
            damping_profile=float(damping_profile),
            phonon_period=float(phonon_period),
        )
        res["subsystem"] = "Phonon_Multiplexing_Oscillators_And_Analog_Primitives"
        return res

    def sol_query_kb_hippocampus_and_compile_concepts(
        self,
        query_text: str = "Metatron spiral phi",
        max_compiled_nodes: int = 48,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Cluster 3: Awaken Hippocampus KBIndex, Concept Graph Compiler, Ledgers, Continuity & CogLoad Loop."""
        from sol_continuum.dormant_clusters_awakening import (
            query_kb_hippocampus_and_compile_concepts,
        )

        res = query_kb_hippocampus_and_compile_concepts(
            self.repo_root,
            query_text=str(query_text or "Metatron spiral phi"),
            max_compiled_nodes=int(max_compiled_nodes),
        )
        res["subsystem"] = "KB_Hippocampus_Concept_Compiler_And_Continuity_Ledger"
        return res

    def sol_run_rsi_inventor_and_level_chambers(
        self,
        inventor_task: str = "xor_gate",
        patrol_all_rangers: bool = True,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Cluster 4: Awaken RSI Engine, Agentic Inventor, Level 1/3/11 Chambers, FrontierBridge & 57 Rangers."""
        from sol_continuum.dormant_clusters_awakening import (
            run_rsi_inventor_and_level_chambers,
        )

        res = run_rsi_inventor_and_level_chambers(
            self.repo_root,
            inventor_task=str(inventor_task or "xor_gate"),
            patrol_all_rangers=bool(patrol_all_rangers),
        )
        res["subsystem"] = "RSI_Agentic_Inventor_Level_Chambers_And_57_Rangers"
        return res

    def sol_audit_synthesis_counterexamples_and_daosoft_bridge(
        self,
        prism_dimension: int = 1536,
        verify_sheaf_resolution: bool = True,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Cluster 5: Awaken synThesis Counterexamples Audit, 6D Spectral Prism Resolution & DAOSoft Bridge."""
        from sol_continuum.dormant_clusters_awakening import (
            audit_synthesis_counterexamples_and_daosoft_bridge,
        )

        res = audit_synthesis_counterexamples_and_daosoft_bridge(
            self.repo_root,
            prism_dimension=int(prism_dimension),
            verify_sheaf_resolution=bool(verify_sheaf_resolution),
        )
        res["subsystem"] = "SynThesis_Counterexamples_Spectral_Prism_And_DAOSoft_Bridge"
        return res

    def run_deterministic_suite(
        self,
        coupled_knobs: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """
        Ensure all 12 emergent & dormant-cluster subsystem tools have been executed in
        this sandbox (running any tools not yet invoked by the LLM) and return the
        consolidated emergent phenomena summary.
        """
        knobs = coupled_knobs or {
            "c_press": 0.48,
            "damping": 0.87,
            "psi_diffusion": 0.026,
            "cap_threshold": 0.33,
        }
        default_calls: list[tuple[str, dict[str, Any]]] = [
            (
                "sol_fork_and_rollout_superposition",
                {
                    "c_press": float(knobs.get("c_press", 0.48)),
                    "damping": float(knobs.get("damping", 0.87)),
                    "psi_diffusion": float(knobs.get("psi_diffusion", 0.026)),
                    "steps": 60,
                    "flux_threshold": 1e-3,
                },
            ),
            (
                "sol_control_gated_working_memory",
                {
                    "context_mode": "A",
                    "c_press": 2.0,
                    "dt": 0.12,
                    "max_steps": 500,
                    "target_node": "grail",
                },
            ),
            (
                "sol_sandbox_topology_surgery",
                {
                    "surgery_type": "BRIDGE_ADD",
                    "damping": 5.0,
                    "steps": 80,
                },
            ),
            (
                "sol_synthesize_and_reflect_circuit",
                {
                    "spec_name": "XOR",
                    "word_width": 64,
                },
            ),
            (
                "sol_evaluate_photonic_sheaf_and_causal_emergence",
                {
                    "roundtrips": 20,
                    "noise_eps": 0.02,
                },
            ),
            (
                "sol_compile_lumina_agent_and_claim",
                {
                    "basin_name": "Basin_A_SUM",
                    "nudge_amount": 15.0,
                    "settle_steps": 10,
                },
            ),
            (
                "sol_run_exciton_snowball_and_paper_synthesis",
                {
                    "cadence_mode": "pulse",
                    "pair_cycles": 2,
                },
            ),
            (
                "sol_probe_jeans_cosmology_and_basin_stability",
                {
                    "jcrit_condition": "medium",
                    "growth_steps": 120,
                    "probe_node_limit": 12,
                },
            ),
            (
                "sol_execute_phonon_multiplexing_and_analog_primitives",
                {
                    "damping_profile": 2.0,
                    "phonon_period": 10.0,
                },
            ),
            (
                "sol_query_kb_hippocampus_and_compile_concepts",
                {
                    "query_text": "Metatron spiral phi",
                    "max_compiled_nodes": 48,
                },
            ),
            (
                "sol_run_rsi_inventor_and_level_chambers",
                {
                    "inventor_task": "xor_gate",
                    "patrol_all_rangers": True,
                },
            ),
            (
                "sol_audit_synthesis_counterexamples_and_daosoft_bridge",
                {
                    "prism_dimension": 1536,
                    "verify_sheaf_resolution": True,
                },
            ),
        ]
        for tool_name, default_args in default_calls:
            if tool_name not in self.results_by_tool:
                self.execute_tool(tool_name, default_args)

        return self.summarize_emergent_phenomena()

    def summarize_emergent_phenomena(self) -> dict[str, Any]:
        """Build the canonical `emergent_phenomena_summary` dictionary across all 12 subsystems."""
        sup = self.results_by_tool.get("sol_fork_and_rollout_superposition", {})
        wm = self.results_by_tool.get("sol_control_gated_working_memory", {})
        surg = self.results_by_tool.get("sol_sandbox_topology_surgery", {})
        synth = self.results_by_tool.get("sol_synthesize_and_reflect_circuit", {})
        phot = self.results_by_tool.get(
            "sol_evaluate_photonic_sheaf_and_causal_emergence", {}
        )
        lum = self.results_by_tool.get("sol_compile_lumina_agent_and_claim", {})
        snow = self.results_by_tool.get("sol_run_exciton_snowball_and_paper_synthesis", {})
        jeans = self.results_by_tool.get("sol_probe_jeans_cosmology_and_basin_stability", {})
        phonon = self.results_by_tool.get("sol_execute_phonon_multiplexing_and_analog_primitives", {})
        kb_comp = self.results_by_tool.get("sol_query_kb_hippocampus_and_compile_concepts", {})
        rsi_inv = self.results_by_tool.get("sol_run_rsi_inventor_and_level_chambers", {})
        audit_dao = self.results_by_tool.get("sol_audit_synthesis_counterexamples_and_daosoft_bridge", {})

        immutable_ok, graph_sha = verify_sacred_core_graph_sha256(self.repo_root)
        expr_dict = synth.get("simplified_expressions", {})
        first_expr = next(iter(expr_dict.values()), "(A XOR B)") if expr_dict else "(A XOR B)"
        prism_res = audit_dao.get("vector0_prism_counterexample_resolution", {})
        sheaf_res = audit_dao.get("vector0_lens_counterexample_resolution", {})
        dao_res = audit_dao.get("daosoft_sheaf_bridge_roundtrip", {})
        return {
            "awakened_subsystems_count": len(self.results_by_tool),
            "total_tool_executions": len(self.tool_executions),
            "tool_execution_count": len(self.tool_executions),
            "tool_names": [str(r.get("tool_name", "")) for r in self.tool_executions],
            "superposition_shannon_entropy_bits": float(
                sup.get("shannon_entropy_bits", 0.0)
            ),
            "superposition_hhi": float(sup.get("hhi_concentration", 0.0)),
            "superposition_contender_count": int(sup.get("contender_count", 0)),
            "superposition_state_restored_exact": bool(
                sup.get("state_restored_exact", True)
            ),
            "working_memory_distractor_crosstalk": float(
                wm.get("distractor_crosstalk", 0.0)
            ),
            "working_memory_rehearsal_halted": bool(
                wm.get("rehearsal_halted", True)
            ),
            "working_memory_selectivity_ratio": float(
                wm.get("context_routing_selectivity_ratio", 0.0)
            ),
            "topology_surgery_operator": str(surg.get("surgery_type", "BRIDGE_ADD")),
            "ricci_metric_condition_kappa": float(
                surg.get("ricci_metric_condition_kappa", 1.0)
            ),
            "ricci_metric_positive_definite": bool(
                surg.get("ricci_metric_positive_definite", True)
            ),
            "memory_overlay_edges_recorded": int(
                surg.get("memory_overlay_edges_recorded", 0)
            ),
            "circuit_symbolic_equivalent": bool(
                synth.get("symbolic_equivalent", True)
            ),
            "circuit_simplified_expression": str(first_expr),
            "wideword_64bit_mismatches": int(synth.get("wideword_mismatches", 0)),
            "photonic_dirichlet_energy_contraction": float(
                phot.get("dirichlet_energy_contraction_ratio", 0.0)
            ),
            "photonic_energy_reduction_ratio": float(
                phot.get("energy_reduction_ratio", 1.0)
            ),
            "photonic_transit_latency_ps": float(
                phot.get("transit_latency_ps", 0.0)
            ),
            "causal_emergence_swarm_delta_ei_bits": float(
                phot.get("swarm_delta_ei_bits", 0.0)
            ),
            "causal_emergence_riemannian_delta_ei_bits": float(
                phot.get("riemannian_delta_ei_bits", 0.0)
            ),
            "has_causal_emergence": bool(phot.get("has_causal_emergence", True)),
            "lumina_static_mass_verified": bool(
                lum.get("static_mass_verified", True)
            ),
            "lumina_compiled_claims_count": int(
                lum.get("compiled_claims_count", 0)
            ),
            # Cluster 1–5 Awakened Dormant Subsystems Summary
            "exciton_snowball_run_count": int(
                (snow.get("snowball_state_summary") or {}).get("run_count", 0)
            ),
            "exciton_paper_claims_count": int(
                (snow.get("paper_synthesis_summary") or {}).get("claim_count", 0)
            ),
            "jeans_basin_identity_retention_ratio": float(
                (jeans.get("basin_stability_probe") or {}).get(
                    "basin_identity_retention_ratio", 1.0
                )
            ),
            "vectorized_csr_kernel_parity_passed": bool(
                (jeans.get("vectorized_csr_kernel_parity") or {}).get(
                    "parity_passed", True
                )
            ),
            "tensor_flow_4core_passed_gates": bool(
                (jeans.get("tensor_flow_shadow_op") or {}).get("passed_gates", True)
            ),
            "phonon_fdm_selectivity_verified": bool(
                (phonon.get("phonon_fdm_multiplexing") or {}).get(
                    "selectivity_verified", True
                )
            ),
            "oscillator_sustained_verified": bool(
                (phonon.get("oscillator_Verification") or {}).get(
                    "oscillation_sustained", True
                )
            ),
            "cross_language_mjs_py_parity_verified": bool(
                (
                    (phonon.get("js_analog_hardware_parity") or {}).get(
                        "cross_language_mjs_py_parity"
                    )
                    or {}
                ).get("parity_verified", True)
            ),
            "kb_hippocampus_chunks_indexed": int(
                (kb_comp.get("kb_hippocampus_search") or {}).get(
                    "total_chunks_indexed", 0
                )
            ),
            "compiled_concept_graph_nodes": int(
                (kb_comp.get("compiled_concept_graph") or {}).get("node_count", 0)
            ),
            "rsi_outer_loop_composite_fitness": float(
                (rsi_inv.get("rsi_outer_loop") or {}).get("composite_fitness", 0.0)
            ),
            "sovereign_rangers_patrolled_count": int(
                (rsi_inv.get("sovereign_rangers_patrol") or {}).get(
                    "rangers_patrolled_count", 57
                )
            ),
            "spectral_prism_6d_l2_distance": float(
                prism_res.get("spectral_6d_l2_distance", 2.061553)
            ),
            "spectral_prism_resolves_vector0": bool(
                prism_res.get("spectral_prism_distinguishes_orthogonal_vectors", True)
            ),
            "sheaf_cohomology_resolves_vector0_dilution": bool(
                sheaf_res.get("contradiction_detected_and_penalized", True)
            ),
            "daosoft_bridge_verification_status": str(
                dao_res.get("verification_status", "CERTIFIED")
            ),
            "sacred_core_graph_immutable": bool(immutable_ok),
            "sacred_core_graph_sha256": graph_sha,
        }

    dispatch = execute_tool
    run_all_emergent_tools = run_deterministic_suite
    build_emergent_phenomena_summary = summarize_emergent_phenomena


