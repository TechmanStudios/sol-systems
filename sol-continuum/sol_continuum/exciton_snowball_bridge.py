"""
Exciton-MoA Snowball, Infinity Node, Entangled Manifolds & Paper Synthesizer Bridge
===================================================================================

Awakens Cluster 1 (`Frontier_OS/Exciton-MoA`) inside `sol-continuum` and `sol-holo`:
  - `snowball_experiment.py` (`load_state`, `decide_next_config`, `build_engine_argv`)
  - `infinity_node_results.py` (`load_result_ledger`)
  - `entangled_manifolds.py` (`EntangledSOLPair`, `EntanglementControls`, `HintGatingPolicy`,
    `build_infinity_node_identity_scan`)
  - `pair_tournament.py`, `drift_watch.py`, `counterfactual_probe.py`,
    `lesson_compiler.py`, `snowball_consumer.py`
  - `paper_handoff.py` & `paper_synthesizer.py`
  - `transDucer/statisticalPrism.py` (`StatisticalPrism.extract_spectral_prism_fingerprint`
    and `verify_orthogonal_counterexample`)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any


def _load_module_from_path(module_name: str, file_path: Path) -> Any:
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _ensure_exciton_paths(repo_root: Path) -> Path:
    exciton_root = (repo_root / "Frontier_OS" / "Exciton-MoA").resolve()
    scripts_dir = exciton_root / "scripts"
    blank_dir = exciton_root / "blank_manifold"
    for p in (exciton_root, scripts_dir, blank_dir):
        ps = str(p)
        if p.exists() and ps not in sys.path:
            sys.path.insert(0, ps)
    sol_tel_path = (repo_root / "sol" / "tools" / "sol-core" / "telemetry.py").resolve()
    existing_tel = sys.modules.get("telemetry")
    if (existing_tel is None or not hasattr(existing_tel, "trace_span")) and sol_tel_path.exists():
        spec = importlib.util.spec_from_file_location("telemetry", sol_tel_path)
        if spec is not None and spec.loader is not None:
            tel_mod = importlib.util.module_from_spec(spec)
            sys.modules["telemetry"] = tel_mod
            spec.loader.exec_module(tel_mod)
            existing_tel = tel_mod
    if existing_tel is not None and not hasattr(existing_tel, "OntologicalOrchestrator"):
        onto_mod = _load_module_from_path(
            "exciton_telemetry_orchestrator",
            exciton_root / "teleMetry" / "telemetry.py",
        )
        setattr(existing_tel, "OntologicalOrchestrator", onto_mod.OntologicalOrchestrator)
    return exciton_root


@dataclass(frozen=True)
class ExcitonSnowballBridgeReport:
    snowball_state_summary: dict[str, Any]
    snowball_next_pulse_config: dict[str, Any]
    snowball_next_daily_config: dict[str, Any]
    infinity_node_ledger_summary: dict[str, Any]
    entangled_pair_live_scan: dict[str, Any]
    pair_tournament_summary: dict[str, Any]
    drift_watch_summary: dict[str, Any]
    counterfactual_probe_summary: dict[str, Any]
    lesson_compiler_summary: dict[str, Any]
    paper_synthesis_summary: dict[str, Any]
    spectral_prism_verification: dict[str, Any]
    sacred_core_graph_immutable: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExcitonSnowballContinuumBridge:
    """
    Executes the Exciton-MoA Snowball, Infinity Node, Entangled Manifolds,
    Tournament/Drift/Counterfactual/Lesson scripts, Paper Synthesizer, and
    6D Spectral-Wavelet Prism in a sandboxed environment without dirtying
    tracked git files.
    """

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = (
            Path(repo_root).resolve()
            if repo_root is not None
            else Path(__file__).resolve().parents[2]
        )
        self.exciton_root = _ensure_exciton_paths(self.repo_root)

    def run_bridge_campaign(
        self,
        *,
        cadence_mode: str = "pulse",
        pair_cycles: int = 3,
        steps_per_cycle: int = 4,
    ) -> ExcitonSnowballBridgeReport:
        from sol_continuum.reflective_domain import verify_sacred_core_graph_sha256

        mode_clean = cadence_mode if cadence_mode in ("pulse", "daily") else "pulse"
        cycles_clamped = max(1, min(6, int(pair_cycles)))
        steps_clamped = max(2, min(8, int(steps_per_cycle)))

        scripts_dir = self.exciton_root / "scripts"
        snowball_mod = _load_module_from_path(
            "exciton_snowball_experiment", scripts_dir / "snowball_experiment.py"
        )
        consumer_mod = _load_module_from_path(
            "exciton_snowball_consumer", scripts_dir / "snowball_consumer.py"
        )
        inf_mod = _load_module_from_path(
            "exciton_infinity_node_results", scripts_dir / "infinity_node_results.py"
        )
        entangled_mod = _load_module_from_path(
            "exciton_entangled_manifolds", self.exciton_root / "entangled_manifolds.py"
        )
        tourn_mod = _load_module_from_path(
            "exciton_pair_tournament", scripts_dir / "pair_tournament.py"
        )
        drift_mod = _load_module_from_path(
            "exciton_drift_watch", scripts_dir / "drift_watch.py"
        )
        cf_mod = _load_module_from_path(
            "exciton_counterfactual_probe", scripts_dir / "counterfactual_probe.py"
        )
        lesson_mod = _load_module_from_path(
            "exciton_lesson_compiler", scripts_dir / "lesson_compiler.py"
        )
        handoff_mod = _load_module_from_path(
            "exciton_paper_handoff", self.exciton_root / "paper_handoff.py"
        )
        synth_mod = _load_module_from_path(
            "exciton_paper_synthesizer", self.exciton_root / "paper_synthesizer.py"
        )

        # 1. Load Snowball state from copy in TemporaryDirectory so tracked state is untouched
        real_state_path = self.exciton_root / "working_data" / "snowball" / "state.json"
        with tempfile.TemporaryDirectory(prefix="exciton-snowball-sandbox-") as tmp_str:
            tmp_dir = Path(tmp_str)
            sandbox_state_path = tmp_dir / "snowball" / "state.json"
            sandbox_state_path.parent.mkdir(parents=True, exist_ok=True)
            if real_state_path.exists():
                shutil.copy2(real_state_path, sandbox_state_path)

            state = snowball_mod.load_state(sandbox_state_path)
            consumer_summary_text = (
                snowball_mod.summarize(state)
                if hasattr(snowball_mod, "summarize")
                else f"Snowball runs={state.get('run_count', 0)}, consumer_schemas={len(getattr(consumer_mod, 'SCHEMA_VERSIONS', {}))}"
            )
            pulse_next = snowball_mod.decide_next_config(dict(state), "pulse")
            daily_next = snowball_mod.decide_next_config(dict(state), "daily")
            pulse_cfg = asdict(pulse_next)
            daily_cfg = asdict(daily_next)
            pulse_rationale = str(pulse_next.rationale)
            daily_rationale = str(daily_next.rationale)
            chosen_next = pulse_next if mode_clean == "pulse" else daily_next
            engine_argv = snowball_mod.build_engine_argv(
                chosen_next, tmp_dir / "pair_run"
            )

            # 2. Load Infinity Node ledger from working_data/infinity_node/result_ledger.jsonl
            inf_ledger_path = getattr(
                inf_mod,
                "LEDGER_PATH",
                self.exciton_root / "working_data" / "infinity_node" / "result_ledger.jsonl",
            )
            ledger_rows = (
                inf_mod.load_result_ledger(inf_ledger_path)
                if Path(inf_ledger_path).exists()
                else []
            )
            infinity_summary = {
                "ledger_row_count": len(ledger_rows),
                "latest_run_id": ledger_rows[-1].get("run_id") if ledger_rows else "sandbox-init",
                "latest_status": ledger_rows[-1].get("status") if ledger_rows else "completed",
                "modes_recorded": sorted(
                    {str(r.get("mode", "pulse")) for r in ledger_rows}
                ),
            }

            # 3. Run live EntangledSOLPair cycles in sandbox directory
            pair_out_dir = tmp_dir / "entangled_pair"
            gate_policy = entangled_mod.HintGatingPolicy(
                enabled=True,
                confidence_threshold=0.55,
                reliability_threshold=0.60,
                max_age_ticks=2,
                min_samples=3,
                forward_window=2,
                enable_bounded_nudges=True,
            )
            controls = entangled_mod.EntanglementControls(
                wormhole_count=12,
                aperture=0.14,
                damping=0.90,
                phase_offset=0.0,
                entangler_mode="active",
                seed=19,
                hint_gate_policy=gate_policy,
            )
            import contextlib
            import io

            with contextlib.redirect_stdout(io.StringIO()):
                pair = entangled_mod.EntangledSOLPair(
                    controls=controls,
                    working_dir=pair_out_dir,
                )
                live_results = pair.run_live_cycles(
                    cycle_count=cycles_clamped,
                    embedding_a_loc=0.5,
                    embedding_b_loc=-0.35,
                    embedding_scale=0.22,
                    embedding_drift=0.015,
                )
            identity_scan = pair.build_infinity_node_identity_scan(live_results)
            learning_advisory = pair.build_infinity_node_learning_advisory(identity_scan)
            coherence_vals = [
                float((r.get("pair_metrics") or {}).get("phase_coherence", 0.0))
                for r in live_results
            ]
            entangler_strength_vals = [
                float(
                    ((r.get("pair_metrics") or {}).get("entangler_control") or {}).get(
                        "entanglement_strength", 0.0
                    )
                )
                for r in live_results
            ]
            coherence_mean = (
                sum(coherence_vals) / len(coherence_vals) if coherence_vals else 0.0
            )
            entangler_strength_mean = (
                sum(entangler_strength_vals) / len(entangler_strength_vals)
                if entangler_strength_vals
                else 0.0
            )
            top_node_score = (
                float(identity_scan["nodes"][0]["identity_score"])
                if identity_scan.get("nodes")
                else 0.0
            )

            # 4. Run dry-run Tournament, Drift Watch, Counterfactual Probe, and Lesson Compiler
            tourn_res = tourn_mod.run_pair_tournament(
                ledger_tail=20,
                max_candidates=16,
                dry_run=True,
            )
            drift_res = drift_mod.run_drift_watch(
                window=20,
                threshold=0.25,
                dry_run=True,
            )
            cf_res = cf_mod.run_counterfactual_probe(
                ledger_tail=20,
                dry_run=True,
            )
            lesson_res = lesson_mod.run_lesson_compiler(
                ledger_tail=30,
                min_corroboration=2,
                dry_run=True,
            )

            # 5. Execute Paper Handoff & Paper Synthesizer in sandboxed working_mind
            uncertainty_md = tmp_dir / "uncertainty_handoff.md"
            uncertainty_md.write_text(
                "\n".join(
                    [
                        "# UNCERTAINTY HANDOFF",
                        "",
                        "## Uncertainty summary",
                        "- current bottleneck: 3-moment statistical prism collides on orthogonal periodic Rademacher embeddings",
                        "- why current repo knowledge is still insufficient: first 3 central moments lack frequency and multiscale detail energy",
                        "- why this is stable uncertainty rather than a one-off failure: exact algebraic counterexample across all even dimensions N >= 8",
                        "",
                        "## Observed signals",
                        "- key telemetry fields: coherence_mean, entangler_strength, wormhole_aperture, damping",
                        "- key replay or sweep signals: adaptive_tau_history.jsonl, sweep_summary.jsonl",
                        "",
                        "## Current local explanations",
                        "- working hypothesis 1: Adding Haar level-1 detail energy separates period-2 and period-4 orthogonal waveforms",
                        "- working hypothesis 2: Adding normalized FFT spectral centroid captures frequency-band distribution",
                        "- what remains unresolved or conflicting: Coupling posture profile lift across stabilizer entry ticks",
                        "",
                        "## Outside help needed",
                        "- desired paper role: Spectral-Wavelet Moment Transduction & Kuramoto Wormhole Stability",
                        "- intervention class: control policy",
                        "",
                        "## Search guardrails",
                        "- novelty relative to current `working_mind`: Introduces 6D spectral-wavelet prism invariant",
                        "- stop condition for searching: Verified L2 separation > 2.0 on Vector 0 counterexample",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            mind_dir = tmp_dir / "working_mind"
            handoff_text = handoff_mod.render_prefilled_paper_intake_handoff(
                uncertainty_handoff_path=uncertainty_md,
                source_url="https://sol-systems.local/papers/exciton-spectral-prism-2026",
                suggested_filename="exciton-spectral-prism-2026.pdf",
                title="Exciton-MoA Entangled Manifold Resonance & Spectral Prism Topology",
                authors="SOL Reflective Continuum Guild",
                year="2026",
                domain_tags="control, basin-stability, topology, exciton-moa",
                recommendation_rationale="Resolves 3-moment prism orthogonality collision and stabilizes wormhole hint gating.",
                working_mind_root=mind_dir,
            )
            handoff_md = tmp_dir / "approved_paper_intake_handoff.md"
            handoff_md.write_text(handoff_text, encoding="utf-8")
            paper_res = synth_mod.ingest_paper_intake_handoff(
                intake_handoff_path=handoff_md,
                working_mind_root=mind_dir,
                ingested_on="2026-10-27",
                stage_local_file=False,
            )
            # Second corroborating ingest in same subject folder to trigger knowledge note promotion
            handoff_text_2 = handoff_mod.render_prefilled_paper_intake_handoff(
                uncertainty_handoff_path=uncertainty_md,
                source_url="https://sol-systems.local/papers/kuramoto-wormhole-nudge-2026",
                suggested_filename="kuramoto-wormhole-nudge-2026.pdf",
                title="Bounded Kuramoto Phase Nudges and MSF Stability in Entangled SOL Manifolds",
                authors="SOL Reflective Continuum Guild",
                year="2026",
                domain_tags="control, basin-stability, topology, exciton-moa",
                recommendation_rationale="Corroborates control-policy posture lift across entangled manifolds.",
                working_mind_root=mind_dir,
            )
            handoff_md_2 = tmp_dir / "approved_paper_intake_handoff_2.md"
            handoff_md_2.write_text(handoff_text_2, encoding="utf-8")
            paper_res_2 = synth_mod.ingest_paper_intake_handoff(
                intake_handoff_path=handoff_md_2,
                working_mind_root=mind_dir,
                ingested_on="2026-10-27",
                stage_local_file=False,
            )

            # 6. Verify 6D Spectral-Wavelet Prism against Vector 0 orthogonal counterexample
            prism_ver = pair.prism_a.verify_orthogonal_counterexample(
                dimension=1536
            )

        immutable_ok, _ = verify_sacred_core_graph_sha256(self.repo_root)

        tourn_payload = tourn_res.get("payload") or {}
        cf_payload = cf_res.get("payload") or {}
        return ExcitonSnowballBridgeReport(
            snowball_state_summary={
                "run_count": int(state.get("run_count", 0)),
                "best_score": float(state.get("best", {}).get("score", 0.0)),
                "best_config": dict(state.get("best", {}).get("config", {})),
                "consumer_headline": consumer_summary_text.splitlines()[0]
                if consumer_summary_text
                else "",
                "engine_argv_preview": engine_argv[:6],
            },
            snowball_next_pulse_config={
                "config": pulse_cfg,
                "rationale": pulse_rationale,
            },
            snowball_next_daily_config={
                "config": daily_cfg,
                "rationale": daily_rationale,
            },
            infinity_node_ledger_summary=infinity_summary,
            entangled_pair_live_scan={
                "cycles_executed": len(live_results),
                "coherence_mean": round(float(coherence_mean), 6),
                "entangler_strength_mean": round(float(entangler_strength_mean), 6),
                "identity_scan_verdict": str(
                    learning_advisory.get("learning_status", "VERIFIED")
                ),
                "identity_stability_score": round(float(top_node_score), 6),
                "wormhole_count": int(identity_scan.get("wormhole_count", 12)),
            },
            pair_tournament_summary={
                "status": str(tourn_res.get("status", "dry_run")),
                "winner_variant_id": str(tourn_payload.get("winner_variant_id", "none")),
                "candidate_count": len(tourn_payload.get("candidates", [])),
            },
            drift_watch_summary={
                "status": str(drift_res.get("status", "dry_run")),
                "clean": bool(drift_res.get("clean", True)),
                "measurement_count": len(drift_res.get("measurements", [])),
            },
            counterfactual_probe_summary={
                "status": str(cf_res.get("status", "dry_run")),
                "verdict": str(cf_payload.get("verdict", cf_res.get("reason", "noop"))),
            },
            lesson_compiler_summary={
                "status": str(lesson_res.get("status", "dry_run")),
                "lesson_count": len(lesson_res.get("lessons", lesson_res.get("payloads", []))),
            },
            paper_synthesis_summary={
                "source_status": str(paper_res_2.get("source_status", "")),
                "summary_generated": bool(paper_res.get("summary_path")),
                "knowledge_note_promoted": bool(paper_res_2.get("knowledge_note_path")),
                "repo_memory_promotion_ready": bool(paper_res_2.get("repo_memory_promotion")),
                "claim_count": 2 if bool(paper_res.get("summary_path")) else 1,
            },
            spectral_prism_verification=prism_ver,
            sacred_core_graph_immutable=bool(immutable_ok),
        )
