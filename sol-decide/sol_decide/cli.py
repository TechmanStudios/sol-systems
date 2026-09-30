"""
SOL-Decide Command-Line Interface (CLI)
=======================================
Executable entrypoint for running trade studies, evaluating sheaf decision complexes,
executing adversarial bias checks, sensitivity ablation, and generating signer-ready packages.
"""

import argparse
import json
import sys
from pathlib import Path

from .core.sheaf_decision_complex import SheafDecisionComplex
from .core.serialization import export_complex_to_json, import_complex_from_json
from .agentic.sensitivity_ablation import SensitivityAblator
from .agentic.dialectical_bias import DialecticalAdversary
from .demonstrations.demo1_ngcv_powertrain import run_demonstration_1, build_ngcv_trade_study
from .demonstrations.demo2_living_refresh import run_demonstration_2


def main():
    parser = argparse.ArgumentParser(
        prog="sol-decide",
        description="SOL-Decide: Sheaf-Theoretic Governed Agentic Decision Management OS"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: demo1
    p_demo1 = subparsers.add_parser("demo1", help="Run Demonstration 1: NGCV Powertrain Trade Study")
    p_demo1.add_argument("--export-md", type=str, default="", help="Export executive Markdown report path")

    # Command: demo2
    p_demo2 = subparsers.add_parser("demo2", help="Run Demonstration 2: 18-Month Living Refresh Program")

    # Command: evaluate
    p_eval = subparsers.add_parser("evaluate", help="Evaluate a Sheaf Decision Complex JSON file")
    p_eval.add_argument("file", type=str, help="Path to decision complex JSON")

    # Command: sensitivity
    p_sens = subparsers.add_parser("sensitivity", help="Run 'What Flips the Decision' sensitivity ablation")
    p_sens.add_argument("--steps", type=int, default=30, help="Sweep steps")

    args = parser.parse_args()

    if args.command == "demo1":
        print("=== RUNNING SOL-DECIDE DEMONSTRATION 1 (NGCV POWERTRAIN TRADE STUDY) ===")
        complex_obj, package, sens, bias = run_demonstration_1()
        print(package.summary if hasattr(package, "summary") else package.executive_summary)
        print(f"Selected Option: {package.selected_option_name} ({package.selected_option_id})")
        print(f"Betti Numbers: beta_0 = {package.betti_0}, beta_1 = {package.betti_1}")
        print(f"Energy: {package.dirichlet_energy:.4e}, Coboundary: {package.coboundary_norm:.4e}")
        print(f"False Commit Rate: {package.false_commit_rate:.2%}")
        print(f"Proof Hash: {package.cryptographic_proof_hash}")
        if args.export_md:
            Path(args.export_md).write_text(package.to_markdown(), encoding="utf-8")
            print(f"Exported executive report to: {args.export_md}")

    elif args.command == "demo2":
        print("=== RUNNING SOL-DECIDE DEMONSTRATION 2 (18-MONTH LIVING REFRESH PROGRAM) ===")
        delta, refreshed_eval, _ = run_demonstration_2()
        print(delta.audit_summary)
        print(f"Baseline Option: {delta.baseline_option_id} -> Refreshed Option: {delta.refreshed_option_id}")
        print(f"Decision Flipped: {delta.did_decision_flip}")
        print(f"Strained Edges Isolated: {len(delta.activated_coboundary_edges)}")

    elif args.command == "evaluate":
        p = Path(args.file)
        if not p.exists():
            print(f"Error: File {args.file} does not exist.")
            sys.exit(1)
        complex_obj = import_complex_from_json(p.read_text(encoding="utf-8"))
        rep = complex_obj.evaluate_decision_package()
        print(rep.summary)

    elif args.command == "sensitivity":
        complex_obj = build_ngcv_trade_study()
        ablator = SensitivityAblator(sweep_steps=args.steps)
        rep = ablator.compute_decision_flips(complex_obj)
        print(rep.summary)
        for t in rep.parameter_thresholds:
            if t.is_sensitive:
                print(f"  * {t.description}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
