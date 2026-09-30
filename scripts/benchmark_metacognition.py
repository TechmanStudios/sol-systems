"""
Frontier_OS: Vector 9 Hierarchical Multi-Agent Cognitive Orchestration & Dynamic Metacognition Benchmark
File: scripts/benchmark_metacognition.py

Evaluates:
1. Multi-stage reasoning graph decomposition and topological execution across arithmetic,
   decision arbiters, and counterfactual query DAGs.
2. 7 Giants MoA swarm-guided manifold exploration, Kuramoto phase synchronization (r >= 0.70),
   and metric Lie algebra regularizations (kappa(g) <= 100.0).
3. Quantitative Causal Emergence (Delta EI > 0) and degeneracy quenching across hierarchical pipelines.
4. Hippocampal cognitive circuit caching and Dream Cycle consolidation (r_geo >= 0.95).
5. Dynamic online metaplasticity self-repair under severe thermal and parameter noise.

Outputs: data/metacognition_benchmark_report.json
"""

import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List
import numpy as np

# Ensure root directory is on PYTHONPATH
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from Frontier_OS.core.hippocampal_sink import HippocampalMemorySink
from Frontier_OS.core.metacognition import (
    create_ripple_carry_adder_plan,
    create_hierarchical_arbiter_plan,
    create_counterfactual_equality_plan,
    SwarmGuidedSynthesizer,
    HippocampalCircuitCache,
    MetacognitiveOrchestrator
)
from sol.kernel.synthesis import (
    CANONICAL_SPECS,
    MetaplasticityEngine
)


def custom_serializer(obj: Any) -> Any:
    """Safely converts numpy types to standard Python primitives for JSON serialization."""
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def run_metacognition_benchmark() -> Dict[str, Any]:
    print("=" * 80)
    print("FRONTIER_OS: VECTOR 9 HIERARCHICAL COGNITIVE ORCHESTRATION BENCHMARK")
    print("=" * 80)

    storage_dir = root_dir / "data" / "hippocampal_bench"
    storage_dir.mkdir(parents=True, exist_ok=True)
    sink = HippocampalMemorySink(
        ambient_dim=4,
        compressed_dim=2,
        storage_dir=storage_dir,
        min_preservation_ratio=0.95,
        auto_dream_flush=False
    )
    cache = HippocampalCircuitCache(hippocampal_sink=sink)
    swarm_synth = SwarmGuidedSynthesizer()
    metaplasticity = MetaplasticityEngine()
    orchestrator = MetacognitiveOrchestrator(
        circuit_cache=cache,
        swarm_synthesizer=swarm_synth,
        metaplasticity_engine=metaplasticity,
        auto_heal=True
    )

    results: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "version": "v9.0.0",
        "vector": "Vector 9: Hierarchical Multi-Agent Cognitive Orchestration & Dynamic Metacognition",
        "plans_evaluated": {},
        "swarm_synthesis_metrics": {},
        "causal_emergence_summary": {},
        "hippocampal_consolidation": {},
        "metaplasticity_healing": {}
    }

    # =========================================================================
    # Task 1: 2-Bit Ripple-Carry Arithmetic with Parity Integrity Verification
    # =========================================================================
    print("\n[Task 1/4] Benchmarking 2-Bit Ripple-Carry Arithmetic & Parity Verification...")
    rc_plan = create_ripple_carry_adder_plan(bits=2, with_parity=True)

    rc_cases_evaluated = 0
    rc_correct = 0
    rc_total_dissipation = 0.0
    rc_latencies = []

    for a_val in range(4):
        for b_val in range(4):
            a0 = float(a_val & 1)
            a1 = float((a_val >> 1) & 1)
            b0 = float(b_val & 1)
            b1 = float((b_val >> 1) & 1)

            expected_sum = a_val + b_val
            exp_s0 = expected_sum & 1
            exp_s1 = (expected_sum >> 1) & 1
            exp_cout = (expected_sum >> 2) & 1
            exp_parity = exp_s0 ^ exp_s1 ^ exp_cout

            inputs = {"A0": a0, "B0": b0, "A1": a1, "B1": b1}
            rep = orchestrator.execute_plan(rc_plan, inputs, auto_consolidate=False)

            rc_cases_evaluated += 1
            rc_total_dissipation += rep.total_energy_dissipated
            rc_latencies.append(rep.total_latency_ms)

            is_correct = (
                rep.success
                and rep.global_outputs.get("S0") == exp_s0
                and rep.global_outputs.get("S1") == exp_s1
                and rep.global_outputs.get("COUT") == exp_cout
                and rep.global_outputs.get("PARITY") == exp_parity
            )
            if is_correct:
                rc_correct += 1

    rc_accuracy = rc_correct / max(rc_cases_evaluated, 1)
    print(f"  -> Accuracy: {rc_accuracy * 100:.1f}% ({rc_correct}/{rc_cases_evaluated} cases)")
    print(f"  -> Mean Latency: {np.mean(rc_latencies):.2f} ms")
    print(f"  -> Total Carnot Dissipation: {rc_total_dissipation:.6f} a.u.")

    results["plans_evaluated"]["ripple_carry_adder_2bit"] = {
        "num_cases": rc_cases_evaluated,
        "correct": rc_correct,
        "accuracy": rc_accuracy,
        "mean_latency_ms": float(np.mean(rc_latencies)),
        "total_carnot_dissipation": float(rc_total_dissipation)
    }

    # =========================================================================
    # Task 2: Hierarchical 3-Way Majority Arbiter with Priority Override
    # =========================================================================
    print("\n[Task 2/4] Benchmarking Hierarchical Majority Arbiter & Causal Emergence...")
    arb_plan = create_hierarchical_arbiter_plan()

    arb_cases = 0
    arb_correct = 0
    arb_delta_eis = []
    arb_latencies = []

    # Sweep all 2^5 = 32 input combinations
    for v1 in (0, 1):
        for v2 in (0, 1):
            for v3 in (0, 1):
                for ov in (0, 1):
                    for pv in (0, 1):
                        maj_raw = 1 if (v1 + v2 + v3) >= 2 else 0
                        final_dec = pv if ov == 1 else maj_raw

                        inputs = {
                            "V1": float(v1), "V2": float(v2), "V3": float(v3),
                            "OVERRIDE": float(ov), "PRIORITY_VOTE": float(pv)
                        }
                        rep = orchestrator.execute_plan(arb_plan, inputs, auto_consolidate=False)

                        arb_cases += 1
                        arb_latencies.append(rep.total_latency_ms)
                        arb_delta_eis.append(rep.mean_causal_delta_ei)

                        is_match = (
                            rep.success
                            and rep.global_outputs.get("MAJORITY_RAW") == maj_raw
                            and rep.global_outputs.get("FINAL_DECISION") == final_dec
                        )
                        if is_match:
                            arb_correct += 1

    arb_accuracy = arb_correct / max(arb_cases, 1)
    mean_delta_ei = float(np.mean(arb_delta_eis))
    print(f"  -> Accuracy: {arb_accuracy * 100:.1f}% ({arb_correct}/{arb_cases} cases)")
    print(f"  -> Mean Causal Emergence (Delta EI): +{mean_delta_ei:.4f} bits")
    print(f"  -> Mean Latency: {np.mean(arb_latencies):.2f} ms")

    results["plans_evaluated"]["hierarchical_decision_arbiter"] = {
        "num_cases": arb_cases,
        "correct": arb_correct,
        "accuracy": arb_accuracy,
        "mean_causal_delta_ei": mean_delta_ei,
        "mean_latency_ms": float(np.mean(arb_latencies))
    }

    # =========================================================================
    # Task 3: Counterfactual Concept Equality and Difference Inference
    # =========================================================================
    print("\n[Task 3/4] Benchmarking Counterfactual Concept Equality & Difference...")
    cf_plan = create_counterfactual_equality_plan()

    cf_cases = 0
    cf_correct = 0
    cf_latencies = []

    for a1 in (0, 1):
        for a0 in (0, 1):
            for b1 in (0, 1):
                for b0 in (0, 1):
                    eq_exp = 1 if (a1 == b1 and a0 == b0) else 0
                    diff_exp = 0 if eq_exp == 1 else (a0 ^ b0)

                    inputs = {"A1": float(a1), "A0": float(a0), "B1": float(b1), "B0": float(b0)}
                    rep = orchestrator.execute_plan(cf_plan, inputs, auto_consolidate=False)

                    cf_cases += 1
                    cf_latencies.append(rep.total_latency_ms)

                    is_match = (
                        rep.success
                        and rep.global_outputs.get("EQUAL") == eq_exp
                        and rep.global_outputs.get("RESIDUAL_DIFF") == diff_exp
                    )
                    if is_match:
                        cf_correct += 1

    cf_accuracy = cf_correct / max(cf_cases, 1)
    print(f"  -> Accuracy: {cf_accuracy * 100:.1f}% ({cf_correct}/{cf_cases} cases)")
    print(f"  -> Mean Latency: {np.mean(cf_latencies):.2f} ms")

    results["plans_evaluated"]["counterfactual_equality"] = {
        "num_cases": cf_cases,
        "correct": cf_correct,
        "accuracy": cf_accuracy,
        "mean_latency_ms": float(np.mean(cf_latencies))
    }

    # =========================================================================
    # Task 4: 7 Giants MoA Swarm Synthesis & Metaplasticity Resilience
    # =========================================================================
    print("\n[Task 4/4] Benchmarking 7 Giants MoA Swarm Synthesis & Online Self-Healing...")

    # Swarm Guided Synthesis Benchmark
    swarm_res = swarm_synth.synthesize_with_swarm(CANONICAL_SPECS["MAJORITY_3"])
    print(f"  -> Swarm Kuramoto Order Parameter (r): {swarm_res.kuramoto_order_parameter:.4f} (Invariant: r >= 0.70)")
    print(f"  -> Metric Condition Number kappa(g): {swarm_res.max_condition_number:.2f} (Invariant: kappa <= 100.0)")
    print(f"  -> 7 Giants Convergence Steps: {swarm_res.optimization_steps} steps")

    results["swarm_synthesis_metrics"] = {
        "spec_name": "MAJORITY_3",
        "accuracy": swarm_res.accuracy,
        "kuramoto_order": swarm_res.kuramoto_order_parameter,
        "max_condition_number": swarm_res.max_condition_number,
        "steps_used": swarm_res.optimization_steps,
        "synthesis_time_ms": swarm_res.synthesis_time_ms,
        "giants_readouts": {gid: r.status for gid, r in swarm_res.giant_readouts.items()}
    }

    # Metaplasticity Online Self-Healing Benchmark
    test_circ, _ = orchestrator.get_or_synthesize_circuit(arb_plan.stages["stage_majority"])
    for nid, node in test_circ.nodes.items():
        node.metric_bias += np.random.normal(0, 0.40, (2, 2))
        node.gain += np.random.normal(0, 0.30)

    t_heal_start = time.time()
    heal_rep = metaplasticity.repair_circuit(test_circ, CANONICAL_SPECS["MAJORITY_3"])
    t_heal_elapsed = (time.time() - t_heal_start) * 1000.0

    print(f"  -> Metaplasticity Pre-Repair Accuracy: {heal_rep.perturbed_accuracy * 100:.1f}%")
    print(f"  -> Metaplasticity Post-Repair Accuracy: {heal_rep.repaired_accuracy * 100:.1f}%")
    print(f"  -> Healing Steps Taken: {heal_rep.steps_taken} steps in {t_heal_elapsed:.2f} ms")

    results["metaplasticity_healing"] = {
        "initial_accuracy": heal_rep.initial_accuracy,
        "perturbed_accuracy": heal_rep.perturbed_accuracy,
        "repaired_accuracy": heal_rep.repaired_accuracy,
        "steps_taken": heal_rep.steps_taken,
        "is_healed": heal_rep.is_healed,
        "repair_time_ms": t_heal_elapsed
    }

    # Dream Cycle Consolidation Benchmark
    print("\nExecuting Hippocampal Memory Dream Cycle Consolidation...")
    dream_report = cache.trigger_consolidation(pair_id="metacognition-benchmark-dream")
    if dream_report:
        print(f"  -> Geodesic Correlation (r_geo): {dream_report.geodesic_correlation:.4f} (Invariant: r_geo >= 0.95)")
        print(f"  -> Crystallized Nodes: {dream_report.pre_compression_nodes} nodes compressed to {dream_report.compressed_dim}D")
        print(f"  -> Status: {dream_report.status}")

        results["hippocampal_consolidation"] = {
            "geodesic_correlation": dream_report.geodesic_correlation,
            "pre_compression_nodes": dream_report.pre_compression_nodes,
            "compressed_dim": dream_report.compressed_dim,
            "crystallized_edges": dream_report.crystallized_edges,
            "status": dream_report.status
        }

    # Save to data directory
    out_path = root_dir / "data" / "metacognition_benchmark_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=custom_serializer)

    print(f"\n[OK] Benchmark Report written to: {out_path}")
    print("=" * 80)
    return results


if __name__ == "__main__":
    run_metacognition_benchmark()
