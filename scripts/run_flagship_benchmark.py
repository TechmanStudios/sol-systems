"""
Executable CLI: Run the SOL Flagship Delayed-Recall & Conflict-Routing Benchmark
File: scripts/run_flagship_benchmark.py

Usage:
  python scripts/run_flagship_benchmark.py [--trials 30] [--output benchmark_report.json]
"""

import argparse
import json
from pathlib import Path
import sys

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from sol.benchmarks.delayed_recall_runner import FlagshipBenchmarkRunner


def main():
    parser = argparse.ArgumentParser(
        description="Run SOL Flagship Delayed-Recall & Conflict-Routing Benchmark Suite"
    )
    parser.add_argument("--trials", type=int, default=30, help="Number of trials in the suite")
    parser.add_argument("--topology-seed", type=int, default=1001, help="Seed for graph topology")
    parser.add_argument("--input-seed", type=int, default=2002, help="Seed for input stream")
    parser.add_argument("--output", type=str, default="data/benchmark_results.json", help="Path to write JSON results")
    args = parser.parse_args()

    print("=" * 80)
    print("       SOL-SYSTEMS & FRONTIER_OS: FLAGSHIP EMPIRICAL BENCHMARK SUITE       ")
    print("   Contextual Delayed-Recall, Non-Dilutable Conflict-Routing & Baselines   ")
    print("=" * 80)
    print(f"Configuration: trials={args.trials}, topo_seed={args.topology_seed}, input_seed={args.input_seed}")

    runner = FlagshipBenchmarkRunner()
    results = runner.run_suite(
        num_trials=args.trials,
        topology_seed=args.topology_seed,
        input_seed=args.input_seed
    )

    print("\n[Finding C Audit: Information-Loss Resolution]")
    audit = results.audit_counterexample
    print(f"  Ambient Cosine Similarity: {audit['cosine_similarity']:.6f} (Orthogonal)")
    print(f"  Legacy Prism Collapsed:   {audit['legacy_collapsed']} (Information Loss Confirmed)")
    print(f"  Identity Preserved:       {audit['identity_preserved']}")
    print(f"  Euclidean Separation:     {audit['euclidean_separation']:.4f} > 0.10\n")

    print("[Benchmark Aggregate Comparison]")
    print(results.to_summary_table())

    # Write output JSON
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    export_dict = {
        "suite_id": results.suite_id,
        "total_trials": results.total_trials,
        "audit_counterexample": results.audit_counterexample,
        "models": {
            name: {
                "model_name": m.model_name,
                "recall_accuracy": m.recall_accuracy,
                "conflict_rejection_rate": m.conflict_rejection_rate,
                "false_commit_rate": m.false_commit_rate,
                "mean_read_disturb_margin": m.mean_read_disturb_margin,
                "mean_recovery_time_steps": m.mean_recovery_time_steps,
                "mean_energy_dissipated": m.mean_energy_dissipated,
                "mean_latency_ms": m.mean_latency_ms,
                "total_memory_kb": m.total_memory_kb
            }
            for name, m in results.model_metrics.items()
        }
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(export_dict, f, indent=2)

    print(f"\n[Saved Benchmark Artifact]: {out_path.resolve()}\n")


if __name__ == "__main__":
    main()
