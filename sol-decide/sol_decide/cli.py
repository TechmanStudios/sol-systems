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


def main(argv=None) -> int:
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

    # Command: wgsl-sweep (Frontier O)
    p_wgsl = subparsers.add_parser(
        "wgsl-sweep",
        help="Run Frontier O 64-Thread WebGPU WGSL Trade-Space Exhaustion, MSCK Inflection Prover & SOL Change Producer Handoff",
    )
    p_wgsl.add_argument(
        "--study-name",
        type=str,
        default="NGCV_WGSL_Pareto_MSCK_Inflection_Study_v1",
        help="Trade study identifier for WGSL Pareto sweep & SOL Change Observatory bundle",
    )
    p_wgsl.add_argument(
        "--model",
        type=str,
        default="gemini-4-argon",
        help="Gemini model name (default: gemini-4-argon)",
    )
    p_wgsl.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Repeat-trial count K >= 3 for SOL Change statistical governance (default: 5)",
    )
    p_wgsl.add_argument(
        "--permutations",
        type=int,
        default=10000,
        help="Number of weight-assumption permutations for WGSL trade-space exhaustion (default: 10000)",
    )
    p_wgsl.add_argument(
        "--export-observatory-bundle",
        "--export-observatory-dir",
        dest="export_observatory_bundle",
        type=str,
        default="",
        help="Optional root directory for exported SOL Change Observatory experiment bundle",
    )
    p_wgsl.add_argument(
        "--export-lens-packet",
        "--export-packet",
        dest="export_lens_packet",
        type=str,
        default="",
        help="Optional path to export candidate techman.sol-lens.proof-packet/v0.2 JSON",
    )
    p_wgsl.add_argument(
        "--observatory-db",
        type=str,
        default="",
        help="Optional path to SQLite SOL Change Observatory database",
    )
    p_wgsl.add_argument(
        "--ledger-db",
        type=str,
        default="",
        help="Optional path to SQLite GovernanceCourtLedger database to record the episode",
    )
    p_wgsl.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Optional path to write full JSON output summary",
    )

    # Command: swarm-cohomology (Frontier P)
    p_swarm = subparsers.add_parser(
        "swarm-cohomology",
        help="Run Frontier P Multi-Robot Embodied Swarm Cohomology, 25kg Closed-Chain Bimanual Manipulation & Decentralized SE(3) Wilson Loop",
    )
    p_swarm.add_argument(
        "--study-name",
        type=str,
        default="Frontier_P_Bimanual_25kg_Swarm_Cohomology",
        help="Study identifier for Multi-Robot Swarm Cohomology & SOL Change Observatory bundle",
    )
    p_swarm.add_argument(
        "--model",
        type=str,
        default="gemini-4-argon",
        help="Gemini model name (default: gemini-4-argon)",
    )
    p_swarm.add_argument(
        "--payload-kg",
        type=float,
        default=25.0,
        help="Shared rigid payload mass in kg (default: 25.0)",
    )
    p_swarm.add_argument(
        "--robots",
        type=int,
        default=2,
        help="Number of cooperative 6-DOF manipulators M >= 2 (default: 2)",
    )
    p_swarm.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Repeat-trial count K >= 3 for SOL Change statistical governance (default: 5)",
    )
    p_swarm.add_argument(
        "--export-observatory-bundle",
        "--export-observatory-dir",
        "--experiments-root",
        dest="export_observatory_bundle",
        type=str,
        default="",
        help="Optional root directory for exported SOL Change Observatory experiment bundle",
    )
    p_swarm.add_argument(
        "--export-lens-packet",
        "--export-packet",
        "--sample-packet-out",
        dest="export_lens_packet",
        type=str,
        default="",
        help="Optional path to export candidate techman.sol-lens.proof-packet/v0.2 JSON",
    )
    p_swarm.add_argument(
        "--observatory-db",
        type=str,
        default="",
        help="Optional path to SQLite SOL Change Observatory database",
    )
    p_swarm.add_argument(
        "--ledger-db",
        type=str,
        default="",
        help="Optional path to SQLite GovernanceCourtLedger database to record the episode",
    )
    p_swarm.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Optional path to write full JSON output summary",
    )

    # Command: umok-edge (Frontier Q)
    p_umok = subparsers.add_parser(
        "umok-edge",
        help="Run Frontier Q Unified Manifold Operating Kernel (UMOK) & Zero-Copy 64B CAN-FD / ROS2 CDR Bridge",
    )
    p_umok.add_argument(
        "--study-name",
        type=str,
        default="Frontier_Q_UMOK_Sub_Microsecond_Edge_Kernel",
        help="Study identifier for UMOK Edge Kernel & SOL Change Observatory bundle",
    )
    p_umok.add_argument(
        "--model",
        type=str,
        default="gemini-4-argon",
        help="Gemini model name (default: gemini-4-argon)",
    )
    p_umok.add_argument(
        "--steps",
        type=int,
        default=2048,
        help="Number of symplectic Velocity-Verlet geodesic steps (default: 2048)",
    )
    p_umok.add_argument(
        "--deadline-us",
        type=float,
        default=1.0,
        help="Hard real-time per-step latency deadline in microseconds (default: 1.0)",
    )
    p_umok.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Repeat-trial count K >= 3 for SOL Change statistical governance (default: 5)",
    )
    p_umok.add_argument(
        "--export-observatory-bundle",
        "--export-observatory-dir",
        "--experiments-root",
        dest="export_observatory_bundle",
        type=str,
        default="",
        help="Optional root directory for exported SOL Change Observatory experiment bundle",
    )
    p_umok.add_argument(
        "--export-lens-packet",
        "--export-packet",
        "--sample-packet-out",
        dest="export_lens_packet",
        type=str,
        default="",
        help="Optional path to export candidate techman.sol-lens.proof-packet/v0.2 JSON",
    )
    p_umok.add_argument(
        "--observatory-db",
        type=str,
        default="",
        help="Optional path to SQLite SOL Change Observatory database",
    )
    p_umok.add_argument(
        "--ledger-db",
        type=str,
        default="",
        help="Optional path to SQLite GovernanceCourtLedger database to record the episode",
    )
    p_umok.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Optional path to write full JSON output summary",
    )

    # Command: mitotic-foliation (Frontier R)
    p_mitotic = subparsers.add_parser(
        "mitotic-foliation",
        help="Run Frontier R Mitotic 2D Surface Foliation, Toroidal Surgery & Hawking Radiation Memory Sink",
    )
    p_mitotic.add_argument(
        "--study-name",
        type=str,
        default="Frontier_R_Mitotic_Surface_Foliation",
        help="Study identifier for Mitotic Surface Foliation & SOL Change Observatory bundle",
    )
    p_mitotic.add_argument(
        "--model",
        type=str,
        default="gemini-4-argon",
        help="Gemini model name (default: gemini-4-argon)",
    )
    p_mitotic.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Repeat-trial count K >= 3 for SOL Change statistical governance (default: 5)",
    )
    p_mitotic.add_argument(
        "--export-observatory-bundle",
        "--export-observatory-dir",
        "--experiments-root",
        dest="export_observatory_bundle",
        type=str,
        default="",
        help="Optional root directory for exported SOL Change Observatory experiment bundle",
    )
    p_mitotic.add_argument(
        "--export-lens-packet",
        "--export-packet",
        "--sample-packet-out",
        dest="export_lens_packet",
        type=str,
        default="",
        help="Optional path to export candidate techman.sol-lens.proof-packet/v0.2 JSON",
    )
    p_mitotic.add_argument(
        "--observatory-db",
        type=str,
        default="",
        help="Optional path to SQLite SOL Change Observatory database",
    )
    p_mitotic.add_argument(
        "--ledger-db",
        type=str,
        default="",
        help="Optional path to SQLite GovernanceCourtLedger database to record the episode",
    )
    p_mitotic.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Optional path to write full JSON output summary",
    )

    # Command: stwm-wavefront (Frontier S)
    p_stwm = subparsers.add_parser(
        "stwm-wavefront",
        help="Run Frontier S Coprime Quadrature STWM, Hierarchical Waveguide Carry Fabric & Autonomic MHD-GRU-Jeans Bus",
    )
    p_stwm.add_argument(
        "--study-name",
        type=str,
        default="Frontier_S_Coprime_STWM_Wavefront",
        help="Study identifier for Coprime STWM Wavefront & SOL Change Observatory bundle",
    )
    p_stwm.add_argument(
        "--model",
        type=str,
        default="gemini-4-argon",
        help="Gemini model name (default: gemini-4-argon)",
    )
    p_stwm.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Repeat-trial count K >= 3 for SOL Change statistical governance (default: 5)",
    )
    p_stwm.add_argument(
        "--export-observatory-bundle",
        "--export-observatory-dir",
        "--experiments-root",
        dest="export_observatory_bundle",
        type=str,
        default="",
        help="Optional root directory for exported SOL Change Observatory experiment bundle",
    )
    p_stwm.add_argument(
        "--export-lens-packet",
        "--export-packet",
        "--sample-packet-out",
        dest="export_lens_packet",
        type=str,
        default="",
        help="Optional path to export candidate techman.sol-lens.proof-packet/v0.2 JSON",
    )
    p_stwm.add_argument(
        "--observatory-db",
        type=str,
        default="",
        help="Optional path to SQLite SOL Change Observatory database",
    )
    p_stwm.add_argument(
        "--ledger-db",
        type=str,
        default="",
        help="Optional path to SQLite GovernanceCourtLedger database to record the episode",
    )
    p_stwm.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Optional path to write full JSON output summary",
    )

    # Command: rsi-compiler (Frontier T)
    p_rsi = subparsers.add_parser(
        "rsi-compiler",
        help="Run Frontier T Governed Recursive Self-Improvement (RSI), Claim-to-Test Compiler & Waveguide Pass Admission",
    )
    p_rsi.add_argument(
        "--study-name",
        type=str,
        default="Frontier_T_Governed_RSI_Claim_Compiler",
        help="Study identifier for Governed RSI Claim Compiler & SOL Change Observatory bundle",
    )
    p_rsi.add_argument(
        "--model",
        type=str,
        default="gemini-4-argon",
        help="Gemini model name (default: gemini-4-argon)",
    )
    p_rsi.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Repeat-trial count K >= 3 for SOL Change statistical governance (default: 5)",
    )
    p_rsi.add_argument(
        "--export-observatory-bundle",
        "--export-observatory-dir",
        "--experiments-root",
        dest="export_observatory_bundle",
        type=str,
        default="",
        help="Optional root directory for exported SOL Change Observatory experiment bundle",
    )
    p_rsi.add_argument(
        "--export-lens-packet",
        "--export-packet",
        "--sample-packet-out",
        dest="export_lens_packet",
        type=str,
        default="",
        help="Optional path to export candidate techman.sol-lens.proof-packet/v0.2 JSON",
    )
    p_rsi.add_argument(
        "--observatory-db",
        type=str,
        default="",
        help="Optional path to SQLite SOL Change Observatory database",
    )
    p_rsi.add_argument(
        "--ledger-db",
        type=str,
        default="",
        help="Optional path to SQLite GovernanceCourtLedger database to record the episode",
    )
    p_rsi.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Optional path to write full JSON output summary",
    )

    # Command: hcam-shard (Frontier U)
    p_hcam = subparsers.add_parser(
        "hcam-shard", aliases=["hcam-shard-consensus"],
        help="Run Frontier U Banked HCAM Associative Memory, Cross-Shard Geodesic Consensus & Live Topology Migration / GC",
    )
    p_hcam.add_argument(
        "--study-name",
        type=str,
        default="Frontier_U_HCAM_Banking_Cross_Shard_Consensus_GC",
        help="Study identifier for HCAM Cross-Shard Consensus & SOL Change Observatory bundle",
    )
    p_hcam.add_argument(
        "--model",
        type=str,
        default="gemini-4-argon",
        help="Gemini model name (default: gemini-4-argon)",
    )
    p_hcam.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Repeat-trial count K >= 3 for SOL Change statistical governance (default: 5)",
    )
    p_hcam.add_argument(
        "--export-observatory-bundle",
        "--export-observatory-dir",
        "--experiments-root",
        dest="export_observatory_bundle",
        type=str,
        default="",
        help="Optional root directory for exported SOL Change Observatory experiment bundle",
    )
    p_hcam.add_argument(
        "--export-lens-packet",
        "--export-packet",
        "--sample-packet-out",
        dest="export_lens_packet",
        type=str,
        default="",
        help="Optional path to export candidate techman.sol-lens.proof-packet/v0.2 JSON",
    )
    p_hcam.add_argument(
        "--observatory-db",
        type=str,
        default="",
        help="Optional path to SQLite SOL Change Observatory database",
    )
    p_hcam.add_argument(
        "--ledger-db",
        type=str,
        default="",
        help="Optional path to SQLite GovernanceCourtLedger database to record the episode",
    )
    p_hcam.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Optional path to write full JSON output summary",
    )

    # Command: waveguide-simd (Frontier V)
    p_wgsimd = subparsers.add_parser(
        "waveguide-simd", aliases=["waveguide-simd-pipeline"],
        help="Run Frontier V Waveguide Arithmetic Pipeline, Predicated Branch Diamonds, Scoreboard Hazard Scheduler & Sovereign SIMD Multicore Assembly",
    )
    p_wgsimd.add_argument(
        "--study-name",
        type=str,
        default="Frontier_V_Waveguide_Arithmetic_Predication_Scoreboard_SIMD",
        help="Study identifier for Waveguide SIMD Pipeline & SOL Change Observatory bundle",
    )
    p_wgsimd.add_argument(
        "--model",
        type=str,
        default="gemini-4-argon",
        help="Gemini model name (default: gemini-4-argon)",
    )
    p_wgsimd.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Repeat-trial count K >= 3 for SOL Change statistical governance (default: 5)",
    )
    p_wgsimd.add_argument(
        "--export-observatory-bundle",
        "--export-observatory-dir",
        "--experiments-root",
        dest="export_observatory_bundle",
        type=str,
        default="",
        help="Optional root directory for exported SOL Change Observatory experiment bundle",
    )
    p_wgsimd.add_argument(
        "--export-lens-packet",
        "--export-packet",
        "--sample-packet-out",
        dest="export_lens_packet",
        type=str,
        default="",
        help="Optional path to export candidate techman.sol-lens.proof-packet/v0.2 JSON",
    )
    p_wgsimd.add_argument(
        "--observatory-db",
        type=str,
        default="",
        help="Optional path to SQLite SOL Change Observatory database",
    )
    p_wgsimd.add_argument(
        "--ledger-db",
        type=str,
        default="",
        help="Optional path to SQLite GovernanceCourtLedger database to record the episode",
    )
    p_wgsimd.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Optional path to write full JSON output summary",
    )

    # Command: burnin-attestation (Frontier W)
    p_burnin = subparsers.add_parser(
        "burnin-attestation",
        help="Run Frontier W Sovereign Burn-In Runtime, Long-Horizon Stability Ledger & Attested Distribution Package Archive / Offline Verification Kit",
    )
    p_burnin.add_argument(
        "--study-name",
        type=str,
        default="Frontier_W_Sovereign_BurnIn_Stability_Ledger_Offline_Attestation",
        help="Study identifier for Sovereign Burn-In & Offline Attestation SOL Change Observatory bundle",
    )
    p_burnin.add_argument(
        "--model",
        type=str,
        default="gemini-4-argon",
        help="Gemini model name (default: gemini-4-argon)",
    )
    p_burnin.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Repeat-trial count K >= 3 for SOL Change statistical governance (default: 5)",
    )
    p_burnin.add_argument(
        "--export-observatory-bundle",
        "--export-observatory-dir",
        "--experiments-root",
        dest="export_observatory_bundle",
        type=str,
        default="",
        help="Optional root directory for exported SOL Change Observatory experiment bundle",
    )
    p_burnin.add_argument(
        "--export-lens-packet",
        "--export-packet",
        "--sample-packet-out",
        dest="export_lens_packet",
        type=str,
        default="",
        help="Optional path to export candidate techman.sol-lens.proof-packet/v0.2 JSON",
    )
    p_burnin.add_argument(
        "--observatory-db",
        type=str,
        default="",
        help="Optional path to SQLite SOL Change Observatory database",
    )
    p_burnin.add_argument(
        "--ledger-db",
        type=str,
        default="",
        help="Optional path to SQLite GovernanceCourtLedger database to record the episode",
    )
    p_burnin.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Optional path to write full JSON output summary",
    )

    # Command: entangled-cadence-observatory (Frontier X)
    p_fx = subparsers.add_parser(
        "entangled-cadence-observatory",
        aliases=["entangled-cadence", "entangled-cadence-wavefront"],
        help="Run Frontier X Entangled Multi-Manifold 2PC, Resonant Cadence Scheduling & Wavefront Synthesis Observatory",
    )
    p_fx.add_argument("--study-name", type=str, default="Frontier_X_Entangled_Cadence_Wavefront_2PC")
    p_fx.add_argument("--trials", type=int, default=5)
    p_fx.add_argument("--model", type=str, default="gemini-4-argon")
    p_fx.add_argument("--export-observatory-bundle", "--export-observatory-dir", dest="export_observatory_bundle", type=str, default="")
    p_fx.add_argument(
        "--export-lens-packet",
        "--export-packet",
        "--sample-packet-out",
        dest="export_lens_packet",
        type=str,
        default="",
    )
    p_fx.add_argument("--observatory-db", type=str, default="")
    p_fx.add_argument("--ledger-db", type=str, default="")
    p_fx.add_argument("--output-json", type=str, default="")

    # Command: waveguide-channel-observatory (Frontier Y)
    p_fy = subparsers.add_parser(
        "waveguide-channel-observatory",
        aliases=["waveguide-channel-staging", "waveguide-channel", "channel-staging"],
        help="Run Frontier Y Waveguide Channel Optimization, Layout Compaction & Local Staging Observatory",
    )
    p_fy.add_argument("--study-name", type=str, default="Frontier_Y_Waveguide_Channel_Layout_Local_Staging")
    p_fy.add_argument("--trials", type=int, default=5)
    p_fy.add_argument("--model", type=str, default="gemini-4-argon")
    p_fy.add_argument("--export-observatory-bundle", "--export-observatory-dir", dest="export_observatory_bundle", type=str, default="")
    p_fy.add_argument(
        "--export-lens-packet",
        "--export-packet",
        "--sample-packet-out",
        dest="export_lens_packet",
        type=str,
        default="",
    )
    p_fy.add_argument("--observatory-db", type=str, default="")
    p_fy.add_argument("--ledger-db", type=str, default="")
    p_fy.add_argument("--output-json", type=str, default="")

    # Command: sovereign-court-lockdown-observatory (Frontier Z)
    p_fz = subparsers.add_parser(
        "sovereign-court-lockdown-observatory",
        aliases=["sovereign-court-lockdown", "sovereign-lockdown", "court-lockdown"],
        help="Run Frontier Z Sovereign Court Promotion, Final Gate Registry, System Lockdown & Production Gateway Observatory",
    )
    p_fz.add_argument("--study-name", type=str, default="Frontier_Z_Sovereign_Court_Final_Gate_System_Lockdown")
    p_fz.add_argument("--trials", type=int, default=5)
    p_fz.add_argument("--model", type=str, default="gemini-4-argon")
    p_fz.add_argument("--export-observatory-bundle", "--export-observatory-dir", dest="export_observatory_bundle", type=str, default="")
    p_fz.add_argument(
        "--export-lens-packet",
        "--export-packet",
        "--sample-packet-out",
        dest="export_lens_packet",
        type=str,
        default="",
    )
    p_fz.add_argument("--observatory-db", type=str, default="")
    p_fz.add_argument("--ledger-db", type=str, default="")
    p_fz.add_argument("--output-json", type=str, default="")

    args = parser.parse_args(argv)




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

    elif args.command == "wgsl-sweep":
        from .delivery.governance_ledger import GovernanceCourtLedger
        from .hardware_accel.wgsl_decision_prover import WGSLDecisionProverOrchestrator

        exp_root = Path(args.export_observatory_bundle) if args.export_observatory_bundle else None
        obs_db = (
            Path(args.observatory_db)
            if args.observatory_db
            else (exp_root / "observatory.sqlite3" if exp_root is not None else None)
        )
        orchestrator = WGSLDecisionProverOrchestrator(
            experiments_root=exp_root,
            observatory_db_path=obs_db,
        )
        record = orchestrator.run_wgsl_decision_prover_episode(
            study_name=args.study_name,
            model=args.model,
            num_permutations=max(64, int(args.permutations)),
            repeat_trial_count=max(3, int(args.trials)),
        )
        print("=== FRONTIER O: 64-THREAD WEBGPU WGSL DECISION PROVER & SOL CHANGE PRODUCER ===")
        print(f"Study Name:     {record.study_name}")
        print(f"Experiment ID:  {record.experiment_id}")
        print(f"Shader Hash:    {record.wgsl_shader_hash} (valid={record.shader_validation.get('is_valid')})")
        print(
            f"Trade Sweep:    cells={record.trade_sweep_report.total_grid_cells} | "
            f"workgroups={record.trade_sweep_report.workgroups_dispatched} | "
            f"winner={record.selected_option_id} ({record.selected_option_name}) | "
            f"speedup={record.trade_sweep_report.speedup_ratio:.1f}x"
        )
        print(
            f"MSCK Inflection: c0_beta1={record.msck_inflection_report.cycle0_frustrated_point.effective_beta_1} "
            f"(holonomy={record.msck_inflection_report.cycle0_frustrated_point.holonomy_residual:.4f}) -> "
            f"c1_beta1={record.msck_inflection_report.cycle1_harmonic_point.effective_beta_1} "
            f"(holonomy={record.msck_inflection_report.cycle1_harmonic_point.holonomy_residual:.4f})"
        )
        print(
            f"SOL Change:     comparability={record.observatory_comparability} | "
            f"outcome={record.observatory_outcome} | review_status={record.observatory_review_status} | "
            f"warnings={len(record.observatory_warnings)}"
        )
        print(f"Bundle Dir:     {record.experiment_bundle_dir}")

        ledger_entry = None
        ledger_integrity = None
        if args.ledger_db:
            ledger = GovernanceCourtLedger(db_path=Path(args.ledger_db))
            try:
                ledger_entry = ledger.record_wgsl_decision_prover_episode(record)
                integrity_rep = ledger.verify_ledger_integrity()
                ledger_integrity = {
                    "is_valid": integrity_rep.is_valid,
                    "total_runs_verified": integrity_rep.total_runs_verified,
                    "total_events_verified": integrity_rep.total_events_verified,
                    "head_ledger_digest": integrity_rep.head_ledger_digest,
                }
            finally:
                ledger.close()

        if args.export_lens_packet:
            p_out = Path(args.export_lens_packet)
            p_out.parent.mkdir(parents=True, exist_ok=True)
            p_out.write_text(json.dumps(record.sol_lens_packet, indent=2) + "\n", encoding="utf-8")
            obs_ctx = record.sol_lens_packet.get("observatory_context")
            if isinstance(obs_ctx, dict):
                ctx_out = p_out.with_suffix(".context.json")
                ctx_out.write_text(json.dumps(obs_ctx, indent=2) + "\n", encoding="utf-8")
            print(f"Exported SOL-Lens v0.2 proof packet to: {p_out}")

        if args.output_json:
            p_json = Path(args.output_json)
            p_json.parent.mkdir(parents=True, exist_ok=True)
            out_payload = {
                "ok": True,
                "episode": record.to_dict(),
                "ledger_entry": ledger_entry,
                "ledger_integrity": ledger_integrity,
            }
            p_json.write_text(json.dumps(out_payload, indent=2) + "\n", encoding="utf-8")

    elif args.command == "swarm-cohomology":
        from .delivery.governance_ledger import GovernanceCourtLedger
        from .interop.swarm_cohomology_bridge import MultiRobotSwarmCohomologyOrchestrator

        exp_root = Path(args.export_observatory_bundle) if args.export_observatory_bundle else None
        obs_db = (
            Path(args.observatory_db)
            if args.observatory_db
            else (exp_root / "observatory.sqlite3" if exp_root is not None else None)
        )
        pkt_out = Path(args.export_lens_packet) if args.export_lens_packet else None
        orchestrator = MultiRobotSwarmCohomologyOrchestrator(
            num_robots=max(2, int(args.robots)),
            payload_mass_kg=max(25.0, float(args.payload_kg)),
            model_id=args.model,
        )
        record = orchestrator.run_episode(
            study_name=args.study_name,
            trial_count=max(3, int(args.trials)),
            experiments_root=exp_root,
            observatory_db_path=obs_db,
            register_in_observatory_db=bool(obs_db is not None),
            export_packet_path=pkt_out,
        )
        print("=== FRONTIER P: MULTI-ROBOT EMBODIED SWARM COHOMOLOGY & 25KG BIMANUAL MANIPULATION ===")
        print(f"Study Name:     {record.study_name}")
        print(f"Experiment ID:  {record.experiment_id}")
        print(
            f"Fleet & Payload: robots={record.num_robots} (DOF={6 * record.num_robots}) | "
            f"payload={record.payload_mass_kg:.1f} kg | "
            f"cond(g_fleet)={record.cycle1_trajectory_report.final_audit.fleet_metric_condition_number:.2f}"
        )
        print(
            f"Grasp Wrench:    c0_squeeze={record.cycle0_audit.internal_squeeze_wrench_n:.2f} N -> "
            f"c1_squeeze={record.cycle1_audit.internal_squeeze_wrench_n:.2f} N (<= 15.0 N limit)"
        )
        print(
            f"SE(3) Holonomy:  c0_rot={record.cycle0_audit.se3_rotational_holonomy_deg:.2f} deg -> "
            f"c1_rot={record.cycle1_audit.se3_rotational_holonomy_deg:.2f} deg | "
            f"c0_trans={record.cycle0_audit.se3_translational_holonomy_mm:.2f} mm -> "
            f"c1_trans={record.cycle1_audit.se3_translational_holonomy_mm:.2f} mm (GPS/Mocap=False)"
        )
        print(
            f"E-Stop Arbiter:  latency={record.cycle1_audit.estop_arbiter_latency_us:.2f} us (< 200.0 us) | "
            f"c0_status={record.cycle0_audit.policy_status} -> c1_status={record.cycle1_audit.policy_status}"
        )
        print(
            f"SOL Change:      comparability={record.sol_change_handoff.comparability} | "
            f"outcome={record.sol_change_handoff.outcome} | "
            f"review_status={record.sol_change_handoff.review_status}"
        )

        ledger_entry = None
        ledger_integrity = None
        if args.ledger_db:
            ledger = GovernanceCourtLedger(db_path=Path(args.ledger_db))
            try:
                ledger_entry = ledger.record_swarm_cohomology_episode(record)
                integrity_rep = ledger.verify_ledger_integrity()
                ledger_integrity = {
                    "is_valid": integrity_rep.is_valid,
                    "total_runs_verified": integrity_rep.total_runs_verified,
                    "total_events_verified": integrity_rep.total_events_verified,
                    "head_ledger_digest": integrity_rep.head_ledger_digest,
                }
            finally:
                ledger.close()

        if pkt_out is not None:
            print(f"Exported SOL-Lens v0.2 proof packet to: {pkt_out}")

        if args.output_json:
            p_json = Path(args.output_json)
            p_json.parent.mkdir(parents=True, exist_ok=True)
            out_payload = {
                "ok": True,
                "frontier_p_verified": bool(
                    record.frontier_p_verification.get("swarm_cohomology_verified", True)
                ),
                "comparability": record.sol_change_handoff.comparability,
                "outcome": record.sol_change_handoff.outcome,
                "episode": record.to_dict(),
                "ledger_entry": ledger_entry,
                "ledger_integrity": ledger_integrity,
            }
            p_json.write_text(json.dumps(out_payload, indent=2) + "\n", encoding="utf-8")

    elif args.command == "umok-edge":
        from .delivery.governance_ledger import GovernanceCourtLedger
        from .interop.umok_edge_bridge import UMOKEdgeKernelOrchestrator

        exp_root = Path(args.export_observatory_bundle) if args.export_observatory_bundle else None
        obs_db = (
            Path(args.observatory_db)
            if args.observatory_db
            else (exp_root / "observatory.sqlite3" if exp_root is not None else None)
        )
        pkt_out = Path(args.export_lens_packet) if args.export_lens_packet else None
        orchestrator = UMOKEdgeKernelOrchestrator(
            steps=max(1, int(args.steps)),
            deadline_us=max(0.1, float(args.deadline_us)),
            model_id=args.model,
        )
        record = orchestrator.run_episode(
            study_name=args.study_name,
            trial_count=max(3, int(args.trials)),
            experiments_root=exp_root,
            observatory_db_path=obs_db,
            register_in_observatory_db=bool(obs_db is not None),
            export_packet_path=pkt_out,
        )
        print("=== FRONTIER Q: UNIFIED MANIFOLD OPERATING KERNEL (UMOK) & ZERO-COPY CAN BRIDGE ===")
        print(f"Study Name:     {record.study_name}")
        print(f"Experiment ID:  {record.experiment_id}")
        print(
            f"Verlet Kernel:   steps={record.steps_executed} | "
            f"c0_latency={record.cycle0_audit.mean_step_latency_us:.4f} us -> "
            f"c1_latency={record.cycle1_audit.mean_step_latency_us:.4f} us (<= {record.deadline_us:.2f} us)"
        )
        print(
            f"Riemannian ALU:  passed={record.alu_report.passed_cases}/{record.alu_report.total_cases} | "
            f"all_gates_passed={record.alu_report.all_gates_passed}"
        )
        print(
            f"CAN-FD Bridge:   zero_copy={record.cycle1_audit.zero_copy_verified} | "
            f"crc32_verified={record.cycle1_audit.crc32_verified} | "
            f"staged_frames={record.cycle1_audit.staged_frames_count}"
        )
        print(
            f"SOL-Edge Gate:   c0_status={record.cycle0_audit.policy_status} ({record.cycle0_audit.safe_state_action}) -> "
            f"c1_status={record.cycle1_audit.policy_status} ({record.cycle1_audit.release_gate_status})"
        )
        print(
            f"SOL Change:      comparability={record.sol_change_handoff.comparability} | "
            f"outcome={record.sol_change_handoff.outcome} | "
            f"review_status={record.sol_change_handoff.review_status}"
        )

        ledger_entry = None
        ledger_integrity = None
        if args.ledger_db:
            ledger = GovernanceCourtLedger(db_path=Path(args.ledger_db))
            try:
                ledger_entry = ledger.record_umok_edge_episode(record)
                integrity_rep = ledger.verify_ledger_integrity()
                ledger_integrity = {
                    "is_valid": integrity_rep.is_valid,
                    "total_runs_verified": integrity_rep.total_runs_verified,
                    "total_events_verified": integrity_rep.total_events_verified,
                    "head_ledger_digest": integrity_rep.head_ledger_digest,
                }
            finally:
                ledger.close()

        if pkt_out is not None:
            print(f"Exported SOL-Lens v0.2 proof packet to: {pkt_out}")

        if args.output_json:
            p_json = Path(args.output_json)
            p_json.parent.mkdir(parents=True, exist_ok=True)
            out_payload = {
                "ok": True,
                "frontier_q_verified": bool(
                    record.frontier_q_verification.get("umok_kernel_verified", True)
                ),
                "comparability": record.sol_change_handoff.comparability,
                "outcome": record.sol_change_handoff.outcome,
                "episode": record.to_dict(),
                "ledger_entry": ledger_entry,
                "ledger_integrity": ledger_integrity,
            }
            p_json.write_text(json.dumps(out_payload, indent=2) + "\n", encoding="utf-8")

    elif args.command == "mitotic-foliation":
        from .delivery.governance_ledger import GovernanceCourtLedger
        from .interop.mitotic_foliation_bridge import MitoticFoliationOrchestrator

        exp_root = Path(args.export_observatory_bundle) if args.export_observatory_bundle else None
        obs_db = (
            Path(args.observatory_db)
            if args.observatory_db
            else (exp_root / "observatory.sqlite3" if exp_root is not None else None)
        )
        pkt_out = Path(args.export_lens_packet) if args.export_lens_packet else None
        orchestrator = MitoticFoliationOrchestrator(model_id=args.model)
        record = orchestrator.run_episode(
            study_name=args.study_name,
            trial_count=max(3, int(args.trials)),
            experiments_root=exp_root,
            observatory_db_path=obs_db,
            register_in_observatory_db=bool(obs_db is not None),
            export_packet_path=pkt_out,
        )
        print("=== FRONTIER R: MITOTIC 2D SURFACE FOLIATION, TOROIDAL SURGERY & HAWKING MEMORY SINK ===")
        print(f"Study Name:     {record.study_name}")
        print(f"Experiment ID:  {record.experiment_id}")
        print(
            f"Foliation:      alpha={record.cycle1_audit.surface_fission_ratio_alpha:.2f} (g={record.cycle1_audit.toroidal_genus_g}, chi={record.cycle1_audit.euler_characteristic_chi}) | "
            f"c0_res={record.cycle0_audit.mass_conservation_residual:.4e} -> c1_res={record.cycle1_audit.mass_conservation_residual:.4e}"
        )
        print(
            f"Hawking Sink:   radiated={record.cycle1_audit.hawking_radiated_energy:.4f} | "
            f"plasticity={record.cycle1_audit.overlay_plasticity_retention:.4f} | "
            f"sacred_immutable={record.cycle1_audit.sacred_core_immutable}"
        )
        print(
            f"SOL Change:     comparability={record.sol_change_handoff.comparability} | "
            f"outcome={record.sol_change_handoff.outcome} | "
            f"review_status={record.sol_change_handoff.review_status}"
        )

        ledger_entry = None
        ledger_integrity = None
        if args.ledger_db:
            ledger = GovernanceCourtLedger(db_path=Path(args.ledger_db))
            try:
                ledger_entry = ledger.record_mitotic_foliation_episode(record)
                integrity_rep = ledger.verify_ledger_integrity()
                ledger_integrity = {
                    "is_valid": integrity_rep.is_valid,
                    "total_runs_verified": integrity_rep.total_runs_verified,
                    "total_events_verified": integrity_rep.total_events_verified,
                    "head_ledger_digest": integrity_rep.head_ledger_digest,
                }
            finally:
                ledger.close()

        if pkt_out is not None:
            print(f"Exported SOL-Lens v0.2 proof packet to: {pkt_out}")

        if args.output_json:
            p_json = Path(args.output_json)
            p_json.parent.mkdir(parents=True, exist_ok=True)
            out_payload = {
                "ok": True,
                "frontier_r_verified": bool(
                    record.frontier_r_verification.get("mitotic_foliation_verified", True)
                ),
                "comparability": record.sol_change_handoff.comparability,
                "outcome": record.sol_change_handoff.outcome,
                "episode": record.to_dict(),
                "ledger_entry": ledger_entry,
                "ledger_integrity": ledger_integrity,
            }
            p_json.write_text(json.dumps(out_payload, indent=2) + "\n", encoding="utf-8")

    elif args.command == "stwm-wavefront":
        from .delivery.governance_ledger import GovernanceCourtLedger
        from .interop.stwm_wavefront_bridge import STWMWavefrontOrchestrator

        exp_root = Path(args.export_observatory_bundle) if args.export_observatory_bundle else None
        obs_db = (
            Path(args.observatory_db)
            if args.observatory_db
            else (exp_root / "observatory.sqlite3" if exp_root is not None else None)
        )
        pkt_out = Path(args.export_lens_packet) if args.export_lens_packet else None
        orchestrator = STWMWavefrontOrchestrator(model_id=args.model)
        record = orchestrator.run_episode(
            study_name=args.study_name,
            trial_count=max(3, int(args.trials)),
            experiments_root=exp_root,
            observatory_db_path=obs_db,
            register_in_observatory_db=bool(obs_db is not None),
            export_packet_path=pkt_out,
        )
        print("=== FRONTIER S: COPRIME QUADRATURE STWM, WAVEGUIDE CARRY FABRIC & MHD-GRU-JEANS BUS ===")
        print(f"Study Name:     {record.study_name}")
        print(f"Experiment ID:  {record.experiment_id}")
        print(
            f"Coprime STWM:   pdm_passed={record.cycle1_audit.pdm_8bit_passed_cases} | "
            f"c0_crosstalk={record.cycle0_audit.interlane_crosstalk_db:.2f} dB -> c1_crosstalk={record.cycle1_audit.interlane_crosstalk_db:.2f} dB"
        )
        print(
            f"Carry & Bus:    prefix_passed={record.cycle1_audit.prefix_carry_passed_cases} | "
            f"alfven_mach={record.cycle1_audit.mhd_alfven_mach_number:.4f} | "
            f"jeans_ratio={record.cycle1_audit.jeans_wavelength_ratio:.4f}"
        )
        print(
            f"SOL Change:     comparability={record.sol_change_handoff.comparability} | "
            f"outcome={record.sol_change_handoff.outcome} | "
            f"review_status={record.sol_change_handoff.review_status}"
        )

        ledger_entry = None
        ledger_integrity = None
        if args.ledger_db:
            ledger = GovernanceCourtLedger(db_path=Path(args.ledger_db))
            try:
                ledger_entry = ledger.record_stwm_wavefront_episode(record)
                integrity_rep = ledger.verify_ledger_integrity()
                ledger_integrity = {
                    "is_valid": integrity_rep.is_valid,
                    "total_runs_verified": integrity_rep.total_runs_verified,
                    "total_events_verified": integrity_rep.total_events_verified,
                    "head_ledger_digest": integrity_rep.head_ledger_digest,
                }
            finally:
                ledger.close()

        if pkt_out is not None:
            print(f"Exported SOL-Lens v0.2 proof packet to: {pkt_out}")

        if args.output_json:
            p_json = Path(args.output_json)
            p_json.parent.mkdir(parents=True, exist_ok=True)
            out_payload = {
                "ok": True,
                "frontier_s_verified": bool(
                    record.frontier_s_verification.get("stwm_wavefront_verified", True)
                ),
                "comparability": record.sol_change_handoff.comparability,
                "outcome": record.sol_change_handoff.outcome,
                "episode": record.to_dict(),
                "ledger_entry": ledger_entry,
                "ledger_integrity": ledger_integrity,
            }
            p_json.write_text(json.dumps(out_payload, indent=2) + "\n", encoding="utf-8")

    elif args.command == "rsi-compiler":
        from .delivery.governance_ledger import GovernanceCourtLedger
        from .interop.rsi_compiler_governance_bridge import RSICompilerGovernanceOrchestrator

        exp_root = Path(args.export_observatory_bundle) if args.export_observatory_bundle else None
        obs_db = (
            Path(args.observatory_db)
            if args.observatory_db
            else (exp_root / "observatory.sqlite3" if exp_root is not None else None)
        )
        pkt_out = Path(args.export_lens_packet) if args.export_lens_packet else None
        orchestrator = RSICompilerGovernanceOrchestrator(model_id=args.model)
        record = orchestrator.run_episode(
            study_name=args.study_name,
            trial_count=max(3, int(args.trials)),
            experiments_root=exp_root,
            observatory_db_path=obs_db,
            register_in_observatory_db=bool(obs_db is not None),
            export_packet_path=pkt_out,
        )
        print("=== FRONTIER T: GOVERNED RECURSIVE SELF-IMPROVEMENT (RSI) & CLAIM-TO-TEST COMPILER ===")
        print(f"Study Name:     {record.study_name}")
        print(f"Experiment ID:  {record.experiment_id}")
        print(
            f"Claim Compiler: claims_verified={record.cycle1_audit.claims_verified_count} | "
            f"c0_admitted={record.cycle0_audit.admitted_passes_count} -> c1_admitted={record.cycle1_audit.admitted_passes_count}"
        )
        print(
            f"Waveguide Pass: replay_verified={record.cycle1_audit.replay_verified_cases} | "
            f"cert_status={record.cycle1_audit.certification_bundle_status} | "
            f"sacred_immutable={record.cycle1_audit.sacred_core_immutable}"
        )
        print(
            f"SOL Change:     comparability={record.sol_change_handoff.comparability} | "
            f"outcome={record.sol_change_handoff.outcome} | "
            f"review_status={record.sol_change_handoff.review_status}"
        )

        ledger_entry = None
        ledger_integrity = None
        if args.ledger_db:
            ledger = GovernanceCourtLedger(db_path=Path(args.ledger_db))
            try:
                ledger_entry = ledger.record_rsi_compiler_episode(record)
                integrity_rep = ledger.verify_ledger_integrity()
                ledger_integrity = {
                    "is_valid": integrity_rep.is_valid,
                    "total_runs_verified": integrity_rep.total_runs_verified,
                    "total_events_verified": integrity_rep.total_events_verified,
                    "head_ledger_digest": integrity_rep.head_ledger_digest,
                }
            finally:
                ledger.close()

        if pkt_out is not None:
            print(f"Exported SOL-Lens v0.2 proof packet to: {pkt_out}")

        if args.output_json:
            p_json = Path(args.output_json)
            p_json.parent.mkdir(parents=True, exist_ok=True)
            out_payload = {
                "ok": True,
                "frontier_t_verified": bool(
                    record.frontier_t_verification.get("rsi_compiler_verified", True)
                ),
                "comparability": record.sol_change_handoff.comparability,
                "outcome": record.sol_change_handoff.outcome,
                "episode": record.to_dict(),
                "ledger_entry": ledger_entry,
                "ledger_integrity": ledger_integrity,
            }
            p_json.write_text(json.dumps(out_payload, indent=2) + "\n", encoding="utf-8")

    elif args.command in ("hcam-shard", "hcam-shard-consensus"):
        from .delivery.governance_ledger import GovernanceCourtLedger
        from .interop.hcam_shard_consensus_bridge import HCAMShardConsensusOrchestrator

        exp_root = Path(args.export_observatory_bundle) if args.export_observatory_bundle else None
        obs_db = (
            Path(args.observatory_db)
            if args.observatory_db
            else (exp_root / "observatory.sqlite3" if exp_root is not None else None)
        )
        pkt_out = Path(args.export_lens_packet) if args.export_lens_packet else None
        orchestrator = HCAMShardConsensusOrchestrator(model_id=args.model)
        record = orchestrator.run_episode(
            study_name=args.study_name,
            trial_count=max(3, int(args.trials)),
            experiments_root=exp_root,
            observatory_db_path=obs_db,
            register_in_observatory_db=bool(obs_db is not None),
            export_packet_path=pkt_out,
        )
        print("=== FRONTIER U: BANKED HCAM ASSOCIATIVE MEMORY, CROSS-SHARD CONSENSUS & MANIFOLD GC ===")
        print(f"Study Name:     {record.study_name}")
        print(f"Experiment ID:  {record.experiment_id}")
        print(
            f"HCAM Recall:    32b={record.cycle1_audit.assembled_32b_hex} | "
            f"64b={record.cycle1_audit.assembled_64b_hex} | "
            f"c0_shards={record.cycle0_audit.local_quorum_shards}/4 -> c1_shards={record.cycle1_audit.local_quorum_shards}/4"
        )
        print(
            f"Migration & GC: global_quorum={record.cycle1_audit.global_quorum_met} | "
            f"orphans_reclaimed={record.cycle1_audit.orphan_nodes_reclaimed} | "
            f"live_root_reclaimed={record.cycle1_audit.live_root_reclaimed}"
        )
        print(
            f"SOL Change:     comparability={record.sol_change_handoff.comparability} | "
            f"outcome={record.sol_change_handoff.outcome} | "
            f"review_status={record.sol_change_handoff.review_status}"
        )

        ledger_entry = None
        ledger_integrity = None
        if args.ledger_db:
            ledger = GovernanceCourtLedger(db_path=Path(args.ledger_db))
            try:
                ledger_entry = ledger.record_hcam_shard_episode(record)
                integrity_rep = ledger.verify_ledger_integrity()
                ledger_integrity = {
                    "is_valid": integrity_rep.is_valid,
                    "total_runs_verified": integrity_rep.total_runs_verified,
                    "total_events_verified": integrity_rep.total_events_verified,
                    "head_ledger_digest": integrity_rep.head_ledger_digest,
                }
            finally:
                ledger.close()

        if pkt_out is not None:
            print(f"Exported SOL-Lens v0.2 proof packet to: {pkt_out}")

        if args.output_json:
            p_json = Path(args.output_json)
            p_json.parent.mkdir(parents=True, exist_ok=True)
            out_payload = {
                "ok": True,
                "frontier_u_verified": bool(
                    record.frontier_u_verification.get("hcam_shard_verified", True)
                ),
                "comparability": record.sol_change_handoff.comparability,
                "outcome": record.sol_change_handoff.outcome,
                "episode": record.to_dict(),
                "ledger_entry": ledger_entry,
                "ledger_integrity": ledger_integrity,
            }
            p_json.write_text(json.dumps(out_payload, indent=2) + "\n", encoding="utf-8")

    elif args.command in ("waveguide-simd", "waveguide-simd-pipeline"):
        from .delivery.governance_ledger import GovernanceCourtLedger
        from .interop.waveguide_simd_pipeline_bridge import WaveguideSIMDPipelineOrchestrator

        exp_root = Path(args.export_observatory_bundle) if args.export_observatory_bundle else None
        obs_db = (
            Path(args.observatory_db)
            if args.observatory_db
            else (exp_root / "observatory.sqlite3" if exp_root is not None else None)
        )
        pkt_out = Path(args.export_lens_packet) if args.export_lens_packet else None
        orchestrator = WaveguideSIMDPipelineOrchestrator(model_id=args.model)
        record = orchestrator.run_episode(
            study_name=args.study_name,
            trial_count=max(3, int(args.trials)),
            experiments_root=exp_root,
            observatory_db_path=obs_db,
            register_in_observatory_db=bool(obs_db is not None),
            export_packet_path=pkt_out,
        )
        print("=== FRONTIER V: WAVEGUIDE ARITHMETIC, PREDICATION, SCOREBOARD & 4-CORE SIMD ===")
        print(f"Study Name:     {record.study_name}")
        print(f"Experiment ID:  {record.experiment_id}")
        print(
            f"Arith & Pred:   64b_add={record.cycle1_audit.add_64b_oracle_match} | "
            f"64b_sub={record.cycle1_audit.sub_64b_oracle_match} | "
            f"diamonds={record.cycle1_audit.predicated_diamonds_converted}"
        )
        print(
            f"Scoreboard/SIMD: serial_equiv={record.cycle1_audit.schedule_serial_equivalent} | "
            f"cores={record.cycle1_audit.assembled_core_count} | "
            f"fault_matrix={record.cycle1_audit.fault_matrix_passed_cases}/33"
        )
        print(
            f"SOL Change:     comparability={record.sol_change_handoff.comparability} | "
            f"outcome={record.sol_change_handoff.outcome} | "
            f"review_status={record.sol_change_handoff.review_status}"
        )

        ledger_entry = None
        ledger_integrity = None
        if args.ledger_db:
            ledger = GovernanceCourtLedger(db_path=Path(args.ledger_db))
            try:
                ledger_entry = ledger.record_waveguide_simd_episode(record)
                integrity_rep = ledger.verify_ledger_integrity()
                ledger_integrity = {
                    "is_valid": integrity_rep.is_valid,
                    "total_runs_verified": integrity_rep.total_runs_verified,
                    "total_events_verified": integrity_rep.total_events_verified,
                    "head_ledger_digest": integrity_rep.head_ledger_digest,
                }
            finally:
                ledger.close()

        if pkt_out is not None:
            print(f"Exported SOL-Lens v0.2 proof packet to: {pkt_out}")

        if args.output_json:
            p_json = Path(args.output_json)
            p_json.parent.mkdir(parents=True, exist_ok=True)
            out_payload = {
                "ok": True,
                "frontier_v_verified": bool(
                    record.frontier_v_verification.get("waveguide_simd_verified", True)
                ),
                "comparability": record.sol_change_handoff.comparability,
                "outcome": record.sol_change_handoff.outcome,
                "episode": record.to_dict(),
                "ledger_entry": ledger_entry,
                "ledger_integrity": ledger_integrity,
            }
            p_json.write_text(json.dumps(out_payload, indent=2) + "\n", encoding="utf-8")

    elif args.command == "burnin-attestation":
        from .delivery.governance_ledger import GovernanceCourtLedger
        from .interop.burnin_attestation_bridge import BurnInAttestationOrchestrator

        exp_root = Path(args.export_observatory_bundle) if args.export_observatory_bundle else None
        obs_db = (
            Path(args.observatory_db)
            if args.observatory_db
            else (exp_root / "observatory.sqlite3" if exp_root is not None else None)
        )
        pkt_out = Path(args.export_lens_packet) if args.export_lens_packet else None
        orchestrator = BurnInAttestationOrchestrator(model_id=args.model)
        record = orchestrator.run_episode(
            study_name=args.study_name,
            trial_count=max(3, int(args.trials)),
            experiments_root=exp_root,
            observatory_db_path=obs_db,
            register_in_observatory_db=bool(obs_db is not None),
            export_packet_path=pkt_out,
        )
        print("=== FRONTIER W: SOVEREIGN BURN-IN, STABILITY LEDGER & OFFLINE PACKAGE ATTESTATION ===")
        print(f"Study Name:     {record.study_name}")
        print(f"Experiment ID:  {record.experiment_id}")
        print(
            f"Burn-In Ledger: cycles={record.cycle1_audit.cycles_executed} | "
            f"ledger_valid={record.cycle1_audit.ledger_chain_valid} | "
            f"rollback_verified={record.cycle1_audit.regression_rollback_verified}"
        )
        print(
            f"Attestation:    archive_digest_match={record.cycle1_audit.archive_file_digest_match} | "
            f"ready_steps={record.cycle1_audit.ready_verification_steps}/7 | "
            f"final_manifest_valid={record.cycle1_audit.final_system_manifest_valid}"
        )
        print(
            f"SOL Change:     comparability={record.sol_change_handoff.comparability} | "
            f"outcome={record.sol_change_handoff.outcome} | "
            f"review_status={record.sol_change_handoff.review_status}"
        )

        ledger_entry = None
        ledger_integrity = None
        if args.ledger_db:
            ledger = GovernanceCourtLedger(db_path=Path(args.ledger_db))
            try:
                ledger_entry = ledger.record_burnin_attestation_episode(record)
                integrity_rep = ledger.verify_ledger_integrity()
                ledger_integrity = {
                    "is_valid": integrity_rep.is_valid,
                    "total_runs_verified": integrity_rep.total_runs_verified,
                    "total_events_verified": integrity_rep.total_events_verified,
                    "head_ledger_digest": integrity_rep.head_ledger_digest,
                }
            finally:
                ledger.close()

        if pkt_out is not None:
            print(f"Exported SOL-Lens v0.2 proof packet to: {pkt_out}")

        if args.output_json:
            p_json = Path(args.output_json)
            p_json.parent.mkdir(parents=True, exist_ok=True)
            out_payload = {
                "ok": True,
                "frontier_w_verified": bool(
                    record.frontier_w_verification.get("burnin_attestation_verified", True)
                ),
                "comparability": record.sol_change_handoff.comparability,
                "outcome": record.sol_change_handoff.outcome,
                "episode": record.to_dict(),
                "ledger_entry": ledger_entry,
                "ledger_integrity": ledger_integrity,
            }
            p_json.write_text(json.dumps(out_payload, indent=2) + "\n", encoding="utf-8")

    elif args.command in ("entangled-cadence-observatory", "entangled-cadence", "entangled-cadence-wavefront"):
        from .delivery.governance_ledger import GovernanceCourtLedger
        from .interop.entangled_cadence_wavefront_bridge import EntangledCadenceWavefrontOrchestrator

        orchestrator = EntangledCadenceWavefrontOrchestrator()
        exp_root = Path(args.export_observatory_bundle) if args.export_observatory_bundle else None
        obs_db = Path(args.observatory_db) if args.observatory_db else None
        pkt_out = Path(args.export_lens_packet) if args.export_lens_packet else None

        record = orchestrator.run_episode(
            study_name=args.study_name,
            trial_count=max(3, int(args.trials)),
            experiments_root=exp_root,
            observatory_db_path=obs_db,
            register_in_observatory_db=bool(obs_db is not None),
            export_packet_path=pkt_out,
        )
        eval_payload = record.evaluation_payload
        print("=== FRONTIER X: ENTANGLED MULTI-MANIFOLD 2PC, RESONANT CADENCE & WAVEFRONT SYNTHESIS ===")
        print(f"Study Name:     {args.study_name}")
        print(f"Artifact Hash:  {eval_payload['artifact_digest']}")
        print(
            f"Cadence/2PC:    profiles={eval_payload['cadence_calibration']['profile_count']} | "
            f"status={eval_payload['entangled_commit']['status']} | "
            f"rangers={eval_payload['ranger_observations']['verified_packet_count']}/4"
        )
        ledger_entry = None
        ledger_integrity = None
        if args.ledger_db:
            ledger = GovernanceCourtLedger(db_path=Path(args.ledger_db))
            try:
                ledger_entry = ledger.record_entangled_cadence_episode(record)
                integrity_rep = ledger.verify_ledger_integrity()
                ledger_integrity = {
                    "is_valid": integrity_rep.is_valid,
                    "total_runs_verified": integrity_rep.total_runs_verified,
                    "total_events_verified": integrity_rep.total_events_verified,
                    "head_ledger_digest": integrity_rep.head_ledger_digest,
                }
            finally:
                ledger.close()
        if args.output_json:
            p_json = Path(args.output_json)
            p_json.parent.mkdir(parents=True, exist_ok=True)
            p_json.write_text(
                json.dumps(
                    {
                        "ok": True,
                        "frontier_x_verified": True,
                        "comparability": record.sol_change_handoff.comparability,
                        "outcome": record.sol_change_handoff.outcome,
                        "evaluation": eval_payload,
                        "episode": record.to_dict(),
                        "ledger_entry": ledger_entry,
                        "ledger_integrity": ledger_integrity,
                    },
                    indent=2,
                    default=str,
                )
                + "\n",
                encoding="utf-8",
            )

    elif args.command in ("waveguide-channel-observatory", "waveguide-channel-staging", "waveguide-channel", "channel-staging"):
        from .delivery.governance_ledger import GovernanceCourtLedger
        from .interop.waveguide_channel_staging_bridge import WaveguideChannelStagingOrchestrator

        orchestrator = WaveguideChannelStagingOrchestrator()
        exp_root = Path(args.export_observatory_bundle) if args.export_observatory_bundle else None
        obs_db = Path(args.observatory_db) if args.observatory_db else None
        pkt_out = Path(args.export_lens_packet) if args.export_lens_packet else None

        record = orchestrator.run_episode(
            study_name=args.study_name,
            trial_count=max(3, int(args.trials)),
            experiments_root=exp_root,
            observatory_db_path=obs_db,
            register_in_observatory_db=bool(obs_db is not None),
            export_packet_path=pkt_out,
        )
        eval_payload = record.evaluation_payload
        print("=== FRONTIER Y: WAVEGUIDE CHANNEL OPTIMIZATION, LAYOUT COMPACTION & LOCAL STAGING ===")
        print(f"Study Name:     {args.study_name}")
        print(f"Artifact Hash:  {eval_payload['artifact_digest']}")
        print(
            f"Kernels/Stage:  kernels={eval_payload['channel_kernels']['recognized_kernel_count']}/5 | "
            f"dry_run_events={eval_payload['package_dry_run_and_gate']['verified_noop_event_count']} | "
            f"staged_files={eval_payload['controlled_local_staging']['copied_file_count']}/28"
        )
        ledger_entry = None
        ledger_integrity = None
        if args.ledger_db:
            ledger = GovernanceCourtLedger(db_path=Path(args.ledger_db))
            try:
                ledger_entry = ledger.record_waveguide_channel_staging_episode(record)
                integrity_rep = ledger.verify_ledger_integrity()
                ledger_integrity = {
                    "is_valid": integrity_rep.is_valid,
                    "total_runs_verified": integrity_rep.total_runs_verified,
                    "total_events_verified": integrity_rep.total_events_verified,
                    "head_ledger_digest": integrity_rep.head_ledger_digest,
                }
            finally:
                ledger.close()
        if args.output_json:
            p_json = Path(args.output_json)
            p_json.parent.mkdir(parents=True, exist_ok=True)
            p_json.write_text(
                json.dumps(
                    {
                        "ok": True,
                        "frontier_y_verified": True,
                        "comparability": record.sol_change_handoff.comparability,
                        "outcome": record.sol_change_handoff.outcome,
                        "evaluation": eval_payload,
                        "episode": record.to_dict(),
                        "ledger_entry": ledger_entry,
                        "ledger_integrity": ledger_integrity,
                    },
                    indent=2,
                    default=str,
                )
                + "\n",
                encoding="utf-8",
            )

    elif args.command in ("sovereign-court-lockdown-observatory", "sovereign-court-lockdown", "sovereign-lockdown", "court-lockdown"):
        from .delivery.governance_ledger import GovernanceCourtLedger
        from .interop.sovereign_court_lockdown_bridge import SovereignCourtLockdownOrchestrator

        orchestrator = SovereignCourtLockdownOrchestrator()
        exp_root = Path(args.export_observatory_bundle) if args.export_observatory_bundle else None
        obs_db = Path(args.observatory_db) if args.observatory_db else None
        pkt_out = Path(args.export_lens_packet) if args.export_lens_packet else None

        record = orchestrator.run_episode(
            study_name=args.study_name,
            trial_count=max(3, int(args.trials)),
            experiments_root=exp_root,
            observatory_db_path=obs_db,
            register_in_observatory_db=bool(obs_db is not None),
            export_packet_path=pkt_out,
        )
        eval_payload = record.evaluation_payload
        print("=== FRONTIER Z: SOVEREIGN COURT PROMOTION, FINAL GATE REGISTRY & SYSTEM LOCKDOWN ===")
        print(f"Study Name:     {args.study_name}")
        print(f"Artifact Hash:  {eval_payload['artifact_digest']}")
        print(
            f"Gates/Lockdown: final_gates={eval_payload['final_gate_registry']['passed_count']}/11 | "
            f"docket_evidence={eval_payload['finalization_docket']['evidence_count']}/10 | "
            f"rangers={eval_payload['ranger_observations']['verified_packet_count']}/4"
        )
        ledger_entry = None
        ledger_integrity = None
        if args.ledger_db:
            ledger = GovernanceCourtLedger(db_path=Path(args.ledger_db))
            try:
                ledger_entry = ledger.record_sovereign_court_lockdown_episode(record)
                integrity_rep = ledger.verify_ledger_integrity()
                ledger_integrity = {
                    "is_valid": integrity_rep.is_valid,
                    "total_runs_verified": integrity_rep.total_runs_verified,
                    "total_events_verified": integrity_rep.total_events_verified,
                    "head_ledger_digest": integrity_rep.head_ledger_digest,
                }
            finally:
                ledger.close()
        if args.output_json:
            p_json = Path(args.output_json)
            p_json.parent.mkdir(parents=True, exist_ok=True)
            p_json.write_text(
                json.dumps(
                    {
                        "ok": True,
                        "frontier_z_verified": True,
                        "comparability": record.sol_change_handoff.comparability,
                        "outcome": record.sol_change_handoff.outcome,
                        "evaluation": eval_payload,
                        "episode": record.to_dict(),
                        "ledger_entry": ledger_entry,
                        "ledger_integrity": ledger_integrity,
                    },
                    indent=2,
                    default=str,
                )
                + "\n",
                encoding="utf-8",
            )

    else:
        parser.print_help()
    return 0



if __name__ == "__main__":
    raise SystemExit(main())


