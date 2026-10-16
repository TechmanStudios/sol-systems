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

    # Command: elicit-live
    p_live = subparsers.add_parser(
        "elicit-live",
        help="Run Live Multi-Agent Gemini Elicitation + Sheaf Cohomology Audit + SOL-Edge Gate",
    )
    p_live.add_argument(
        "--prompt",
        type=str,
        default=(
            "Design a lunar surface microgrid power architecture balancing specific power (kW/kg), "
            "eclipse energy storage endurance (hours), and total lander payload mass (kg) under hard "
            "Artemis cargo mass and thermal dissipation limits."
        ),
        help="Engineering mission or trade study problem description",
    )
    p_live.add_argument(
        "--model",
        type=str,
        default="gemini-3.8-flash",
        help="Gemini model name (default: gemini-3.8-flash; e.g., gemini-4-argon)",
    )
    p_live.add_argument(
        "--thinking-level",
        type=str,
        default="",
        help="Optional thinking level ('minimal', 'low', 'medium', 'high')",
    )
    p_live.add_argument(
        "--export-md",
        type=str,
        default="",
        help="Optional path to export Signer-Ready Decision Package markdown",
    )
    p_live.add_argument(
        "--export-lens-packet",
        type=str,
        default="",
        help="Optional path to export techman.sol-lens.proof-packet/v0.2 JSON trace packet",
    )
    p_live.add_argument(
        "--closed-loop-repair",
        action="store_true",
        help="Run Cycle 1 autonomous cohomological self-correction on any QUARANTINED agent option",
    )
    p_live.add_argument(
        "--dialectical-h1",
        action="store_true",
        help="Run 3-agent specialist dialectical H^1 cohomological obstruction (beta_1=1) and Hodge-harmonic negotiation (beta_1 -> 0)",
    )

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

    elif args.command == "elicit-live":
        from .agentic.live_llm_elicitation import LiveGeminiMoAElicitor

        print(f"=== RUNNING LIVE MULTI-AGENT GEMINI ELICITATION ({args.model}) ===")
        live_elicitor = LiveGeminiMoAElicitor(
            model=args.model,
            thinking_level=args.thinking_level or None,
        )
        if args.dialectical_h1:
            bundle = live_elicitor.run_dialectical_h1_obstruction_study(args.prompt)
        elif args.closed_loop_repair:
            bundle = live_elicitor.run_closed_loop_governed_study(args.prompt)
        else:
            bundle = live_elicitor.run_live_governed_study(args.prompt)
        print(f"Interaction ID: {bundle.interaction_id}")
        print(f"Study Name:     {bundle.elicited_spec.study_name}")
        rt = bundle.reasoning_telemetry
        print(
            f"Reasoning:      level={rt.thinking_level} | thought_steps={rt.thought_step_count} | "
            f"in_tok={rt.total_input_tokens} | thought_tok={rt.total_thought_tokens} | "
            f"out_tok={rt.total_output_tokens} | ratio={rt.thought_to_output_ratio:.4f}"
        )
        if rt.thought_signature_digests:
            print(
                f"Thought Sig:    {rt.thought_signature_digests[0][:36]}... "
                f"(len={rt.thought_signature_lengths[0]}B)"
            )
        print(bundle.elicitation_result.summary)
        print(f"Winning Option: {bundle.decision_package.selected_option_name} ({bundle.decision_package.selected_option_id})")
        print(
            f"Betti Numbers:  beta_0 = {bundle.decision_package.betti_0}, "
            f"beta_1 = {bundle.decision_package.betti_1} | "
            f"Dirichlet Energy = {bundle.decision_package.dirichlet_energy:.4e}"
        )
        if bundle.h1_resolution_record is not None:
            h1 = bundle.h1_resolution_record
            print("--- Multi-Agent Dialectical H^1 Obstruction & Hodge-Harmonic Negotiation ---")
            print(
                f"  * Specialist Sub-Agents: {', '.join(h1.specialist_roles)} "
                f"(interactions={', '.join(h1.specialist_interaction_ids)})"
            )
            print(
                f"  * Cycle 0 H^1 Obstruction: beta_1={h1.pre_negotiation_beta_1} | "
                f"frustrated_cycle={h1.frustrated_cycle_edges} | "
                f"||omega_exact||_2={h1.pre_hodge_report.exact_norm:.4f} | "
                f"||omega_coexact||_2={h1.pre_hodge_report.coexact_norm:.4f} | "
                f"||omega_harmonic||_2={h1.pre_hodge_report.harmonic_norm:.4f} "
                f"(holonomy={h1.pre_hodge_report.cycle_holonomy_residual:+.4f})"
            )
            print(
                f"  * Cycle 1 Hodge Cleared:   beta_1={h1.post_negotiation_beta_1} | "
                f"||omega_harmonic||_2={h1.post_hodge_report.harmonic_norm:.4f} | "
                f"Cleared={h1.obstruction_cleared} | NegotiationInt={h1.negotiation_interaction_id}"
            )
        if bundle.repair_records:
            print("--- Closed-Loop Cohomological Quarantine Self-Correction (Cycle 0 -> Cycle 1) ---")
            for rec in bundle.repair_records:
                print(
                    f"  * [{rec.quarantined_option_id}] {rec.pre_repair_state_vector} -> {rec.post_repair_state_vector} | "
                    f"||Delta x||_2={rec.l2_repair_projection_distance:.3f} | "
                    f"Cleared={rec.quarantine_cleared} ({rec.post_repair_governance.policy_decision.status.value}) | "
                    f"RepairInt={rec.repair_interaction_id}"
                )
        print("--- SOL-Edge Pre-Execution Governance Per Competing Agent Option ---")
        for opt_id, gov in bundle.all_option_governance.items():
            print(
                f"  * [{opt_id}] PolicyStatus={gov.policy_decision.status.value} | "
                f"RuntimeStatus={gov.final_runtime_state.status.value} | "
                f"NextTransition={gov.policy_decision.next_transition.value} | "
                f"StateDigest={gov.final_runtime_state.state_digest[:24]}..."
            )
        pkt = bundle.sol_lens_packet
        pkt_metrics = pkt.get("metrics", {})
        print("--- SOL-Lens Trace Court Proof Packet (v0.2) ---")
        print(
            f"  * Packet ID:  {pkt.get('packet_id')} | Logons: {len(pkt.get('logons', []))} | "
            f"Edges: {len(pkt.get('edges', []))} | Groups: {len(pkt.get('groups', []))}"
        )
        print(
            f"  * Verdict:    {pkt.get('verdict')} (Baseline: {pkt.get('baseline_evaluation', {}).get('verdict')}) | "
            f"Evidence={pkt_metrics.get('evidence', 0.0):.4f} | "
            f"Coherence={pkt_metrics.get('coherence', 0.0):.4f} | "
            f"Contradiction={pkt_metrics.get('contradiction', 0.0):.4f}"
        )
        if args.export_md:
            Path(args.export_md).write_text(bundle.decision_package.to_markdown(), encoding="utf-8")
            print(f"Exported executive report to: {args.export_md}")
        if args.export_lens_packet:
            out_path = live_elicitor.lens_compiler.save_packet(pkt, args.export_lens_packet)
            print(f"Exported SOL-Lens v0.2 proof packet to: {out_path}")


    else:
        parser.print_help()


if __name__ == "__main__":
    main()
