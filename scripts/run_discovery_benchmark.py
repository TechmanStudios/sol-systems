"""
SOL Engine & Frontier_OS: Vector 11 Mathematical Discovery & Theorem Proving Benchmark
File: scripts/run_discovery_benchmark.py

Executes the quantitative benchmark suite for Vector 11:
1. Generates the canonical conjecture catalog across boolean algebra, differential geometry,
   causal information theory, and arithmetic.
2. Directs the AutomatedProofEngine through multi-agent dialectical proof trajectories.
3. Formally proves sound algebraic dualities, topological symmetries, and causal emergence bounds.
4. Conclusively refutes falsifiable hypotheses with reproducible witness vector certificates.
5. Builds the Lemma Dependency DAG (Mermaid) and exports the formal corpus monograph to:
   - conJecture/FORMAL_THEOREMS_CORPUS.md
   - data/discovery_benchmark_report.json
"""

import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List
import numpy as np

# Ensure repository root is on sys.path
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from Frontier_OS.core.theorem_proving import (
    MathematicalDomain,
    ConjectureType,
    MathematicalConjecture,
    AutonomousConjectureEngine,
    ProofVerdict,
    TheoremProofCertificate,
    AutomatedProofEngine,
    TheoremRecord,
    TheoremCorpus
)


def run_discovery_benchmark_suite() -> Dict[str, Any]:
    print("=" * 80)
    print("SOL-SYSTEMS & FRONTIER_OS: VECTOR 11 MATHEMATICAL DISCOVERY BENCHMARK")
    print("=" * 80)

    t0_suite = time.time()
    engine = AutonomousConjectureEngine()
    corpus = TheoremCorpus()
    prover = AutomatedProofEngine()

    catalog = engine.generate_conjecture_catalog()
    print(f"\nGenerated {len(catalog)} non-trivial candidate conjectures across {len(MathematicalDomain)} domains.")

    certificates: List[Dict[str, Any]] = []
    proved_count = 0
    refuted_count = 0
    false_positive_count = 0
    false_negative_count = 0
    causal_gains: List[float] = []
    consensus_orders: List[float] = []
    kernel_sizes: List[int] = []

    for idx, conj in enumerate(catalog, start=1):
        print(f"\n[{idx}/{len(catalog)}] Interrogating Conjecture: {conj.conjecture_id}")
        print(f"   Title:     {conj.title}")
        print(f"   Domain:    {conj.domain.value}")
        print(f"   Formula:   {conj.latex_formula}")
        print(f"   Entropy:   H = {conj.entropy_score:.4f} bits (Non-Triviality Verified)")
        print(f"   Expected:  {'FALSE (Falsifiable)' if conj.is_deliberately_false else 'TRUE (Sound)'}")

        t_start_conj = time.time()
        cert = prover.prove_conjecture(conj, max_debate_rounds=8)
        t_conj_ms = (time.time() - t_start_conj) * 1000.0

        certificates.append(cert.to_dict())

        print(f"   -> Verdict: {cert.verdict.value} (Latency: {t_conj_ms:.2f} ms)")
        print(f"   -> Hegelian Consensus r: {cert.hegelian_consensus_order:.4f}")

        if not conj.is_deliberately_false:
            if cert.verdict == ProofVerdict.PROVED_THEOREM:
                proved_count += 1
                corpus.add_proved_theorem(conj, cert)
                causal_gains.append(cert.causal_emergence_gain)
                consensus_orders.append(cert.hegelian_consensus_order)
                kernel_sizes.append(cert.minimal_causal_kernel_nodes)
                print(f"   -> Dialectical Causal Gain: +{cert.causal_emergence_gain:.4f} bits")
                print(f"   -> Minimal Causal Kernel:   {cert.minimal_causal_kernel_nodes} nodes")
                print(f"   -> Crystallized in Cache:   {cert.is_crystallized}")
            else:
                false_negative_count += 1
                print("   -> ERROR: Sound conjecture was not proved!")
        else:
            if cert.verdict == ProofVerdict.DISPROVED_COUNTEREXAMPLE:
                refuted_count += 1
                corpus.add_refutation(conj, cert)
                wit = cert.counter_example_witness
                print(f"   -> Counter-Example Verified: In={wit.get('input_vector')} Obs={wit.get('observed_output')} Exp={wit.get('expected_output')}")
            else:
                false_positive_count += 1
                print("   -> ERROR: False conjecture was not refuted!")

    total_time_s = time.time() - t0_suite

    # Export formal monograph
    conjecture_dir = root_dir / "conJecture"
    conjecture_dir.mkdir(parents=True, exist_ok=True)
    monograph_path = conjecture_dir / "FORMAL_THEOREMS_CORPUS.md"
    corpus.export_corpus_markdown(filepath=str(monograph_path))
    print(f"\n[FORMAL MONOGRAPH EXPORTED] -> {monograph_path}")

    # Summary Statistics
    total_sound = len([c for c in catalog if not c.is_deliberately_false])
    total_flawed = len([c for c in catalog if c.is_deliberately_false])
    mean_causal_gain = float(np.mean(causal_gains)) if causal_gains else 0.0
    mean_consensus = float(np.mean(consensus_orders)) if consensus_orders else 0.0
    mean_kernel_nodes = float(np.mean(kernel_sizes)) if kernel_sizes else 0.0

    print("\n" + "=" * 80)
    print("MATHEMATICAL DISCOVERY & THEOREM PROVING BENCHMARK RESULTS")
    print("=" * 80)
    print(f"Total Conjectures Interrogated:   {len(catalog)}")
    print(f"Sound Conjectures Proved:        {proved_count} / {total_sound} ({proved_count/max(1, total_sound)*100:.1f}%)")
    print(f"False Conjectures Refuted:       {refuted_count} / {total_flawed} ({refuted_count/max(1, total_flawed)*100:.1f}%)")
    print(f"False Positive Proof Rate:       {false_positive_count/len(catalog)*100:.2f}% (Target: 0.0%)")
    print(f"False Negative Proof Rate:       {false_negative_count/len(catalog)*100:.2f}% (Target: 0.0%)")
    print(f"Mean Hegelian Consensus (Proved): r = {mean_consensus:.4f} (Target: r >= 0.70)")
    print(f"Mean Dialectical Causal Gain:     +{mean_causal_gain:.4f} bits (Target: Delta EI > 0)")
    print(f"Mean Minimal Kernel Size:        {mean_kernel_nodes:.1f} nodes")
    print(f"Theorems Registered in Corpus:   {len(corpus.theorems)}")
    print(f"Total Suite Runtime:             {total_time_s:.2f} s")
    print("=" * 80)

    report = {
        "benchmark_name": "VECTOR_11_AUTOMATED_THEOREM_PROVING_BENCHMARK",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_conjectures": len(catalog),
        "theorems_proved": proved_count,
        "conjectures_refuted": refuted_count,
        "false_positive_rate": false_positive_count / len(catalog),
        "false_negative_rate": false_negative_count / len(catalog),
        "mean_hegelian_consensus_proved": round(mean_consensus, 4),
        "mean_dialectical_causal_gain_bits": round(mean_causal_gain, 4),
        "mean_kernel_nodes": round(mean_kernel_nodes, 1),
        "corpus_theorems_count": len(corpus.theorems),
        "monograph_path": str(monograph_path),
        "total_runtime_seconds": round(total_time_s, 2),
        "certificates": certificates
    }

    report_path = root_dir / "data" / "discovery_benchmark_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"[BENCHMARK REPORT SAVED] -> {report_path}")
    return report


if __name__ == "__main__":
    run_discovery_benchmark_suite()
