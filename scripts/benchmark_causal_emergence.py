"""
SOL-Systems & Frontier_OS: Vector 6 Quantitative Causal Emergence (EI) Benchmark CLI
File: scripts/benchmark_causal_emergence.py

Executes formal causal emergence benchmarks:
1. Canonical Erik Hoel PNAS 2013 Models (Fig 4 Degenerate Cycle & Fig 2 Noisy AND).
2. Continuous Riemannian Geodesic Circuits (Shielded vs Unshielded under analog jitter).
3. 7 Giants MoA Cognitive Pipeline Swarm Architecture (Noise sweep & Emergence transition).

Saves benchmark telemetry to data/causal_emergence_benchmark_report.json.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import numpy as np

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sol.kernel.causal.effective_information import (
    CausalMetrics,
    CausalEmergenceReport,
    compute_causal_emergence,
    generate_hoel_canonical_network
)
from sol.kernel.causal.manifold_causal_analyzer import (
    RiemannianCausalAnalyzer,
    ManifoldCausalSweepResult
)
from sol.kernel.causal.swarm_causal_analyzer import (
    SwarmCausalAnalyzer,
    SwarmScaleEmergenceResult
)
from sol.kernel.geometry.logic_manifold import LogicGateType


def format_report_row(name: str, n_micro: int, n_macro: int, micro_ei: float, macro_ei: float, delta_ei: float, emergence: bool) -> str:
    status = "EMERGENT (+)" if emergence else "REDUCED (-)"
    return f"| {name:<35} | {n_micro:>7} | {n_macro:>7} | {micro_ei:>9.3f} | {macro_ei:>9.3f} | {delta_ei:>+9.3f} | {status:<12} |"


def main():
    parser = argparse.ArgumentParser(description="Run SOL Quantitative Causal Emergence (EI) Benchmarks.")
    parser.add_argument("--output", type=str, default="data/causal_emergence_benchmark_report.json",
                        help="Path to save output JSON benchmark telemetry.")
    args = parser.parse_args()

    print("=" * 105)
    print("      SOL-SYSTEMS & FRONTIER_OS: QUANTITATIVE CAUSAL EMERGENCE (EI) BENCHMARK SUITE")
    print(f"      Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Theoretical Standard: Erik Hoel (PNAS 2013)")
    print("=" * 105)

    results_data = {
        "timestamp": datetime.now().isoformat(),
        "canonical_hoel_benchmarks": {},
        "riemannian_circuit_benchmarks": {},
        "swarm_moa_benchmarks": {}
    }

    # ---------------------------------------------------------
    # 1. CANONICAL HOEL BENCHMARKS
    # ---------------------------------------------------------
    print("\n[SECTION 1: CANONICAL ERIK HOEL PNAS 2013 BENCHMARKS]")
    print("-" * 105)
    print(f"| {'Benchmark Architecture':<35} | {'N_micro':>7} | {'N_macro':>7} | {'Micro EI':>9} | {'Macro EI':>9} | {'Delta EI':>9} | {'Status':<12} |")
    print("-" * 105)

    # Fig 4: Degenerate AND cycle
    W4, map4 = generate_hoel_canonical_network("fig4_degenerate_cycle")
    rep4 = compute_causal_emergence(W4, map4)
    print(format_report_row("Hoel Fig 4 (Degenerate Cycle)", 64, 8, rep4.micro_metrics.effective_information, rep4.macro_metrics.effective_information, rep4.delta_ei, rep4.has_causal_emergence))

    # Fig 2: Noisy AND network (eps=0.01)
    W2, map2 = generate_hoel_canonical_network("fig2_noisy_and", noise_eps=0.01)
    rep2 = compute_causal_emergence(W2, map2)
    print(format_report_row("Hoel Fig 2 (Noisy AND, eps=0.01)", 16, 4, rep2.micro_metrics.effective_information, rep2.macro_metrics.effective_information, rep2.delta_ei, rep2.has_causal_emergence))
    print("-" * 105)

    results_data["canonical_hoel_benchmarks"]["fig4_degenerate_cycle"] = {
        "n_micro": 64, "n_macro": 8,
        "micro_ei": rep4.micro_metrics.effective_information,
        "macro_ei": rep4.macro_metrics.effective_information,
        "delta_ei": rep4.delta_ei,
        "determinism_gain": rep4.determinism_gain,
        "degeneracy_reduction": rep4.degeneracy_reduction,
        "has_causal_emergence": rep4.has_causal_emergence
    }
    results_data["canonical_hoel_benchmarks"]["fig2_noisy_and"] = {
        "n_micro": 16, "n_macro": 4,
        "micro_ei": rep2.micro_metrics.effective_information,
        "macro_ei": rep2.macro_metrics.effective_information,
        "delta_ei": rep2.delta_ei,
        "determinism_gain": rep2.determinism_gain,
        "degeneracy_reduction": rep2.degeneracy_reduction,
        "has_causal_emergence": rep2.has_causal_emergence
    }

    # ---------------------------------------------------------
    # 2. CONTINUOUS RIEMANNIAN LOGIC CIRCUIT BENCHMARKS
    # ---------------------------------------------------------
    print("\n[SECTION 2: CONTINUOUS RIEMANNIAN LOGIC CIRCUITS & 5 HARDENING SHIELDS]")
    print("-" * 105)
    print(f"| {'Circuit Substrate':<35} | {'N_micro':>7} | {'N_macro':>7} | {'Micro EI':>9} | {'Macro EI':>9} | {'Delta EI':>9} | {'Status':<12} |")
    print("-" * 105)

    manifold_analyzer = RiemannianCausalAnalyzer()
    
    # Coupled AND circuit (Shielded vs Unshielded)
    rep_shielded = manifold_analyzer.evaluate_coupled_network_emergence(LogicGateType.AND, noise_sigma=0.05, use_shields=True, n_samples=3)
    print(format_report_row("Riemannian Circuit (Shielded, s=0.05)", 16, 4, rep_shielded.micro_metrics.effective_information, rep_shielded.macro_metrics.effective_information, rep_shielded.delta_ei, rep_shielded.has_causal_emergence))

    rep_unshielded = manifold_analyzer.evaluate_coupled_network_emergence(LogicGateType.AND, noise_sigma=0.05, use_shields=False, n_samples=3)
    print(format_report_row("Riemannian Circuit (Unshielded, s=0.05)", 16, 4, rep_unshielded.micro_metrics.effective_information, rep_unshielded.macro_metrics.effective_information, rep_unshielded.delta_ei, rep_unshielded.has_causal_emergence))

    # Half Adder
    ha_rep = manifold_analyzer.evaluate_half_adder_causal_emergence(noise_sigma=0.05, use_shields=True)
    print(format_report_row("Riemannian Half-Adder (Sum/Carry)", 16, 4, ha_rep.micro_metrics.effective_information, ha_rep.macro_metrics.effective_information, ha_rep.delta_ei, ha_rep.has_causal_emergence))
    print("-" * 105)

    results_data["riemannian_circuit_benchmarks"]["coupled_and_shielded"] = {
        "n_micro": 16, "n_macro": 4,
        "micro_ei": rep_shielded.micro_metrics.effective_information,
        "macro_ei": rep_shielded.macro_metrics.effective_information,
        "delta_ei": rep_shielded.delta_ei,
        "degeneracy_reduction": rep_shielded.degeneracy_reduction,
        "has_causal_emergence": rep_shielded.has_causal_emergence
    }
    results_data["riemannian_circuit_benchmarks"]["coupled_and_unshielded"] = {
        "n_micro": 16, "n_macro": 4,
        "micro_ei": rep_unshielded.micro_metrics.effective_information,
        "macro_ei": rep_unshielded.macro_metrics.effective_information,
        "delta_ei": rep_unshielded.delta_ei,
        "has_causal_emergence": rep_unshielded.has_causal_emergence
    }

    # ---------------------------------------------------------
    # 3. 7 GIANTS MOA COGNITIVE PIPELINE BENCHMARKS
    # ---------------------------------------------------------
    print("\n[SECTION 3: 7 GIANTS MOA COGNITIVE PIPELINE SWARM]")
    print("-" * 105)
    print(f"| {'Swarm Cognitive Architecture':<35} | {'N_micro':>7} | {'N_macro':>7} | {'Micro EI':>9} | {'Macro EI':>9} | {'Delta EI':>9} | {'Status':<12} |")
    print("-" * 105)

    swarm_analyzer = SwarmCausalAnalyzer()
    sweep_res = swarm_analyzer.evaluate_swarm_noise_sweep([0.0, 0.02, 0.05, 0.08, 0.10])

    for i, eps in enumerate(sweep_res.noise_levels):
        name = f"7 Giants Pipeline (eps={eps:.2f}, r={sweep_res.kuramoto_order_r[i]:.2f})"
        print(format_report_row(name, 64, 8, sweep_res.micro_ei[i], sweep_res.macro_ei[i], sweep_res.delta_ei[i], sweep_res.has_emergence[i]))
    print("-" * 105)

    results_data["swarm_moa_benchmarks"]["noise_sweep"] = {
        "noise_levels": sweep_res.noise_levels,
        "kuramoto_order_r": sweep_res.kuramoto_order_r,
        "micro_ei": sweep_res.micro_ei,
        "macro_ei": sweep_res.macro_ei,
        "delta_ei": sweep_res.delta_ei,
        "has_causal_emergence": sweep_res.has_emergence,
        "determinism_gains": sweep_res.determinism_gains,
        "degeneracy_reductions": sweep_res.degeneracy_reductions
    }

    # Save artifact
    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2)

    print(f"\n[OK] Benchmark telemetry successfully saved to: {output_path}")
    print("=" * 105)


if __name__ == "__main__":
    main()
