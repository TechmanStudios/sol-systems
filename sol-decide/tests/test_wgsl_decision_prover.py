"""
Tests for Frontier O (Vector 19): WGSL GPU Trade-Space & MSCK Inflection Prover
+ Producer-Side SOL Change Telemetry (`sol-decide` x `sol-change` x `sol-lens`).
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

_SOL_SYSTEMS_ROOT = Path(__file__).resolve().parents[2]
for _p in (
    _SOL_SYSTEMS_ROOT,
    _SOL_SYSTEMS_ROOT / "sol-decide",
    _SOL_SYSTEMS_ROOT / "sol-change",
    _SOL_SYSTEMS_ROOT / "sol-edge" / "src",
):
    _ps = str(_p)
    if _p.exists() and _ps not in sys.path:
        sys.path.insert(0, _ps)

from sol_edge.contracts import PolicyStatus
from sol_edge.runtime.replay import replay_events
from observatory.continuum import (
    assess_continuum_observatory,
    evaluate_repeat_trial_group,
    main as continuum_cli_main,
    packet_to_run,
    validate_repeat_trial_group,
)
from observatory.domain import ValidationError, validate_archive, validate_run

from sol_decide.cli import main as sol_decide_cli_main
from sol_decide.delivery.governance_ledger import GovernanceCourtLedger
from sol_decide.hardware_accel import (
    SolEdgeWGSLDecisionGate,
    WGSLDecisionProverOrchestrator,
)
from sol_decide.interop.sol_change_producer import (
    build_measured_sol_change_run,
    build_observatory_context_sidecar,
    run_wgsl_prover_repeat_trial_suite,
)


class TestWGSLDecisionProverAndSolChangeProducer(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temp_dir.name)
        self.experiments_root = self.root / "experiments"
        self.obs_db = self.root / "observatory.sqlite3"
        self.ledger_db = self.root / "governance_ledger.sqlite3"
        self.orchestrator = WGSLDecisionProverOrchestrator(
            experiments_root=self.experiments_root,
            observatory_db_path=self.obs_db,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_decision_prover_wgsl_shader_compiler_validation(self) -> None:
        status = self.orchestrator.get_shader_status()
        self.assertTrue(status["is_valid"], f"Shader errors: {status['validation_errors']}")
        self.assertEqual(status["shader_name"], "decision_prover.wgsl")
        self.assertEqual(status["workgroup_size"], [64, 1, 1])
        self.assertGreaterEqual(status["bindings_count"], 5)
        self.assertTrue(status["has_positive_definite_retraction"])
        self.assertTrue(status["has_symplectic_integration"])
        self.assertTrue(status["has_carnot_atomic_dissipation"])
        self.assertTrue(status["wgsl_shader_hash"].startswith("sha256:"))

    def test_wgsl_trade_space_sweep_and_msck_inflection_surface(self) -> None:
        sweep = self.orchestrator.run_wgsl_trade_space_sweep(grid_size=4096)
        self.assertEqual(sweep.total_grid_cells, 4096)
        self.assertEqual(sweep.workgroup_size, (64, 1, 1))
        self.assertEqual(sweep.workgroups_dispatched, 64)
        self.assertGreater(sweep.feasible_cells_count, 3000)
        self.assertGreaterEqual(sweep.pareto_frontier_count, 64)
        self.assertGreater(sweep.optimal_flip_margin_l2, 0.0)
        self.assertGreater(sweep.speedup_ratio, 10.0)
        self.assertGreater(sweep.carnot_dissipation_energy, 0.0)
        self.assertTrue(len(sweep.flip_boundary_samples) > 0)

        msck = self.orchestrator.run_wgsl_msck_inflection_sweep(
            grid_dim=64,
            cycle0_alpha=0.72,
            cycle0_beta_flux=0.88,
            calibrated_alpha=1.0,
            calibrated_beta_flux=0.0,
        )
        self.assertEqual(msck.grid_resolution, (64, 64))
        self.assertEqual(msck.total_surface_points, 4096)
        self.assertEqual(msck.cycle0_frustrated_point.effective_beta_1, 1)
        self.assertGreater(
            msck.cycle0_frustrated_point.holonomy_residual,
            msck.critical_holonomy_threshold,
        )
        self.assertEqual(msck.cycle1_harmonic_point.effective_beta_1, 0)
        self.assertAlmostEqual(msck.cycle1_harmonic_point.holonomy_residual, 0.0, places=6)
        self.assertAlmostEqual(msck.cycle1_harmonic_point.coboundary_energy, 0.0, places=6)
        self.assertGreater(
            msck.cycle1_harmonic_point.spectral_gap_lambda1,
            msck.cycle0_frustrated_point.spectral_gap_lambda1,
        )
        self.assertGreaterEqual(msck.inflection_boundary_locus_count, 12)

    def test_sol_edge_wgsl_decision_gate_cycle0_quarantine_and_cycle1_eligible(self) -> None:
        gate = SolEdgeWGSLDecisionGate()
        c0 = gate.evaluate_prover_cycle(
            cycle_index=0,
            designation="baseline",
            workflow_version="v1.0-uncalibrated",
            shader_valid=True,
            effective_beta_1=1,
            dirichlet_energy=0.35,
            coboundary_defect=0.81,
            pareto_dominance_verified=False,
            observatory_comparability="compatible",
            run_id="run:test-wgsl-gate",
        )
        self.assertTrue(c0.is_quarantined)
        self.assertEqual(c0.policy_status, "QUARANTINE")
        self.assertEqual(len(c0.events), 4)
        replayed_c0 = replay_events(c0.events)
        self.assertEqual(replayed_c0.status.value, "QUARANTINED")
        self.assertEqual(replayed_c0.state_digest, c0.state_digest)

        c1 = gate.evaluate_prover_cycle(
            cycle_index=1,
            designation="candidate",
            workflow_version="v2.0-calibrated",
            shader_valid=True,
            effective_beta_1=0,
            dirichlet_energy=0.0,
            coboundary_defect=0.0,
            pareto_dominance_verified=True,
            observatory_comparability="compatible",
            run_id="run:test-wgsl-gate",
        )
        self.assertFalse(c1.is_quarantined)
        self.assertEqual(c1.policy_status, "ELIGIBLE")
        self.assertEqual(len(c1.events), 4)
        replayed_c1 = replay_events(c1.events)
        self.assertEqual(replayed_c1.status.value, "ELIGIBLE")
        self.assertEqual(replayed_c1.state_digest, c1.state_digest)

    def test_repeat_trial_suite_statistical_governance_and_edge_cases(self) -> None:
        out_path = self.root / "repeat_trials.json"
        suite = run_wgsl_prover_repeat_trial_suite(
            study_name="NGCV_WGSL_Test",
            shared_input="NGCV 4096-cell trade sweep benchmark",
            trial_count=5,
            base_seed=100,
            output_path=out_path,
        )
        self.assertTrue(out_path.is_file())
        eval_report = suite["evaluation"]
        self.assertEqual(eval_report["trial_count"], 5)
        self.assertEqual(eval_report["comparability"], "compatible")
        self.assertEqual(eval_report["outcome"], "improved")
        self.assertEqual(eval_report["review_status"], "awaiting_review")
        self.assertEqual(eval_report["human_decisions_created"], 0)

        ev_stats = eval_report["metrics"]["lens_evidence"]
        self.assertGreater(ev_stats["mean_delta"], 0.25)
        self.assertGreater(ev_stats["cohens_d"], 10.0)
        self.assertLess(ev_stats["p_value_two_sided"], 0.001)
        self.assertTrue(ev_stats["statistically_significant_95"])

        time_stats = eval_report["metrics"]["execution_time"]
        self.assertEqual(time_stats["status"], "improved")
        self.assertLess(time_stats["mean_delta"], 0.0)

        # Edge case: < 3 trials rejected
        with self.assertRaises(ValueError):
            run_wgsl_prover_repeat_trial_suite(
                study_name="NGCV_WGSL_Test",
                shared_input="NGCV 4096-cell trade sweep benchmark",
                trial_count=2,
            )

        # Edge case: mismatched shared_input across trials rejected by validate_repeat_trial_group
        tampered = json.loads(out_path.read_text(encoding="utf-8"))
        tampered["trials"][1]["candidate_run"]["input"] = "Tampered different input"
        with self.assertRaises(ValidationError):
            validate_repeat_trial_group(tampered)

        # Edge case: negative measured_execution_time_s rejected by packet_to_run
        ctx = build_observatory_context_sidecar(
            input_text="Test input",
            study_name="NGCV_WGSL_Test",
            workflow_version="v1.0",
            executed_at="2026-10-22T12:00:00Z",
        )
        sample_pkt = suite["repeat_trial_group"]["trials"][0]["candidate_run"]["configuration"][
            "sol_continuum"
        ]["original_source_text"]
        with self.assertRaises(ValidationError):
            packet_to_run(sample_pkt, "candidate", "pkt.json", ctx, measured_execution_time_s=-0.5)

    def test_end_to_end_episode_governance_ledger_and_observatory_replay(self) -> None:
        sample_dir = self.root / "samples"
        episode = self.orchestrator.run_wgsl_decision_prover_episode(
            study_name="Artemis_WGSL_MSCK_Inflection_Prover_Test",
            repeat_trial_count=5,
            register_in_observatory_db=True,
            export_sample_packet_dir=sample_dir,
        )
        self.assertEqual(episode.cycle0_audit.policy_status, "QUARANTINE")
        self.assertEqual(episode.cycle1_audit.policy_status, "ELIGIBLE")
        self.assertEqual(episode.observatory_comparability, "compatible")
        self.assertEqual(episode.observatory_outcome, "improved")
        self.assertEqual(episode.observatory_review_status, "awaiting_review")
        self.assertEqual(episode.observatory_warnings, [])
        self.assertTrue(episode.frontier_o_verification["wgsl_decision_prover_verified"])

        # Check exported bundle artifacts on disk
        bundle_dir = Path(episode.experiment_bundle_dir)
        for fname in (
            "baseline_packet.json",
            "baseline_packet.context.json",
            "candidate_packet.json",
            "candidate_packet.context.json",
            "baseline.json",
            "candidate.json",
            "experiment.json",
            "comparison.md",
            "repeat_trials.json",
            "repeat_trials_evaluation.json",
        ):
            self.assertTrue((bundle_dir / fname).is_file(), f"Missing {fname}")

        validate_run(json.loads((bundle_dir / "baseline.json").read_text(encoding="utf-8")))
        validate_run(json.loads((bundle_dir / "candidate.json").read_text(encoding="utf-8")))
        exp_doc = json.loads((bundle_dir / "experiment.json").read_text(encoding="utf-8"))
        validate_archive(exp_doc)
        self.assertEqual(exp_doc["review_status"], "awaiting_review")
        self.assertEqual(exp_doc["decisions"], [])

        # Verify to_lens_packet(), handoff_manifest.cli_commands, and on-disk sha256_source_text parity
        lens_pkt = episode.to_lens_packet()
        self.assertEqual(lens_pkt["packet_id"], episode.sol_lens_packet["packet_id"])
        self.assertIn("import_continuum", episode.handoff_manifest.cli_commands)
        self.assertIn("compare", episode.handoff_manifest.cli_commands)
        self.assertIn("evaluate_trials", episode.handoff_manifest.cli_commands)
        self.assertGreater(episode.handoff_manifest.measured_execution_time_s, 0.0)
        self.assertIsNone(episode.handoff_manifest.measured_cost_usd)
        self.assertEqual(episode.trade_sweep_report.num_permutations, 10000)
        self.assertGreater(episode.trade_sweep_report.speedup_factor, 10.0)
        self.assertGreater(episode.msck_inflection_report.min_inflection_delta_pct, 90.0)

        from observatory.domain import digest as obs_digest

        base_run_doc = json.loads((bundle_dir / "baseline.json").read_text(encoding="utf-8"))
        base_pkt_disk_text = (bundle_dir / "baseline_packet.json").read_text(encoding="utf-8")
        self.assertEqual(
            obs_digest(base_pkt_disk_text),
            base_run_doc["configuration"]["sol_continuum"]["sha256_source_text"],
        )
        cand_run_doc = json.loads((bundle_dir / "candidate.json").read_text(encoding="utf-8"))
        cand_pkt_disk_text = (bundle_dir / "candidate_packet.json").read_text(encoding="utf-8")
        self.assertEqual(
            obs_digest(cand_pkt_disk_text),
            cand_run_doc["configuration"]["sol_continuum"]["sha256_source_text"],
        )

        # Record in GovernanceCourtLedger and verify cryptographic hash chain + Frontier O metadata
        ledger = GovernanceCourtLedger(db_path=self.ledger_db)
        self.addCleanup(ledger.close)
        entry = ledger.record_wgsl_decision_prover_episode(episode)
        self.assertEqual(entry["run_mode"], "wgsl_decision_prover_observatory")
        self.assertTrue(entry["frontier_o_verified"])
        self.assertEqual(entry["edge_event_count"], 8)

        integrity = ledger.verify_ledger_integrity()
        self.assertTrue(integrity.is_valid, f"Ledger integrity failed: {integrity.to_dict()}")
        self.assertEqual(integrity.total_runs_verified, 1)
        self.assertEqual(integrity.total_events_verified, 8)

        # Verify tamper detection on nested frontier_o_verification fields
        tampered_pkt = json.loads(json.dumps(episode.sol_lens_packet))
        tampered_pkt["frontier_o_verification"]["cycle1_audit"]["policy_status"] = "QUARANTINE"
        self.assertFalse(
            ledger._verify_continuum_frontier_metadata(
                "wgsl_decision_prover_observatory", json.dumps(tampered_pkt)
            )
        )
        tampered_rtg = json.loads(json.dumps(episode.sol_lens_packet))
        tampered_rtg["frontier_o_verification"]["repeat_trial_governance"]["trial_count"] = 2
        self.assertFalse(
            ledger._verify_continuum_frontier_metadata(
                "wgsl_decision_prover_observatory", json.dumps(tampered_rtg)
            )
        )
        tampered_handoff = json.loads(json.dumps(episode.sol_lens_packet))
        tampered_handoff["frontier_o_verification"]["sol_change_handoff"]["review_status"] = "approved"
        self.assertFalse(
            ledger._verify_continuum_frontier_metadata(
                "wgsl_decision_prover_observatory", json.dumps(tampered_handoff)
            )
        )
        ledger.close()

        # Assess via sol-change continuum bridge + replay persisted sol-edge runtime events from ledger
        assessment = assess_continuum_observatory(
            bundle_dir,
            ledger_db=self.ledger_db,
            run_id=entry["run_id"],
        )
        self.assertEqual(assessment["comparability"], "compatible")
        self.assertEqual(assessment["outcome"], "improved")
        f_sum = assessment["cycle_drift_breakdown"]["frontier_verification_summary"]
        self.assertTrue(f_sum["frontier_o_verified"])
        self.assertEqual(
            f_sum["frontier_o_summary_digest"],
            episode.frontier_o_verification["summary_digest"],
        )
        replay_ver = assessment["runtime_replay_verification"]
        self.assertIsNotNone(replay_ver)
        self.assertTrue(replay_ver["verified"])
        self.assertEqual(replay_ver["total_runs"], 1)
        self.assertEqual(replay_ver["total_streams"], 2)
        self.assertEqual(replay_ver["total_events_replayed"], 8)

    def test_sol_decide_wgsl_sweep_cli_and_continuum_evaluate_trials_cli(self) -> None:
        out_json = self.root / "wgsl_cli_out.json"
        out_pkt = self.root / "exported_wgsl.packet.json"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = sol_decide_cli_main(
                [
                    "wgsl-sweep",
                    "--study-name",
                    "CLI_WGSL_Study",
                    "--permutations",
                    "10000",
                    "--trials",
                    "3",
                    "--export-packet",
                    str(out_pkt),
                    "--export-observatory-dir",
                    str(self.experiments_root),
                    "--ledger-db",
                    str(self.ledger_db),
                    "--output-json",
                    str(out_json),
                ]
            )
        self.assertEqual(rc, 0)
        self.assertTrue(out_json.is_file())
        self.assertTrue(out_pkt.is_file())
        self.assertTrue(out_pkt.with_suffix(".context.json").is_file())
        cli_payload = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertTrue(cli_payload["ok"])
        self.assertTrue(cli_payload["ledger_integrity"]["is_valid"])

        rt_path = Path(cli_payload["episode"]["handoff_manifest"]["repeat_trial_bundle_path"])
        self.assertTrue(rt_path.is_file())
        eval_out = self.root / "cli_repeat_eval.json"
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            rc2 = continuum_cli_main(
                [
                    "evaluate-trials",
                    "--group",
                    str(rt_path),
                    "--format",
                    "json",
                    "--output",
                    str(eval_out),
                ]
            )
        self.assertEqual(rc2, 0)
        self.assertTrue(eval_out.is_file())
        eval_doc = json.loads(eval_out.read_text(encoding="utf-8"))
        self.assertEqual(eval_doc["trial_count"], 3)
        self.assertEqual(eval_doc["outcome"], "improved")

    def test_export_bundle_manifest_consistency_when_regressed_or_warned(self) -> None:
        """
        Verifies that export_decision_prover_observatory_bundle embeds the actual computed
        comparability, outcome, and warnings into baseline_packet.json and candidate_packet.json
        before computing run SHA-256 hashes, even when the candidate regresses or triggers warnings.
        """
        from observatory.domain import digest as obs_digest
        from sol_decide.interop.sol_change_producer import (
            build_observatory_context_sidecar,
            export_decision_prover_observatory_bundle,
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base_ctx = build_observatory_context_sidecar(
                study_name="Regressed_Bundle_Test",
                input_text="shared-input-A",
                workflow_version="v1.0-base",
                executed_at="2026-10-22T00:00:00Z",
            )
            # Different input_text triggers incompatibility warning
            cand_ctx = build_observatory_context_sidecar(
                study_name="Regressed_Bundle_Test",
                input_text="shared-input-B-mismatched",
                workflow_version="v2.0-cand",
                executed_at="2026-10-22T00:00:01Z",
            )
            base_pkt = {
                "schema": "techman.sol-lens.proof-packet/v0.2",
                "packet_id": "pkt:reg-test-base",
                "run_id": "reg-test-base",
                "generated_at": "2026-10-22T00:00:00Z",
                "observable_trace_only": True,
                "logons": [
                    {
                        "id": "logon_0",
                        "kind": "claim",
                        "summary": "Baseline claim",
                        "confidence": 0.92,
                    }
                ],
                "edges": [],
                "metrics": {
                    "evidence": 0.92,
                    "coherence": 0.91,
                    "contradiction": 0.04,
                    "continuity": 0.90,
                    "authority": 0.91,
                    "faithfulness": 0.93,
                },
                "verdict": "PROMOTE",
                "frontier_o_verification": {},
            }
            cand_pkt = {
                "schema": "techman.sol-lens.proof-packet/v0.2",
                "packet_id": "pkt:reg-test-cand",
                "run_id": "reg-test-cand",
                "generated_at": "2026-10-22T00:00:01Z",
                "observable_trace_only": True,
                "logons": [
                    {
                        "id": "logon_0",
                        "kind": "claim",
                        "summary": "Regressed candidate claim",
                        "confidence": 0.41,
                    }
                ],
                "edges": [],
                "metrics": {
                    "evidence": 0.41,
                    "coherence": 0.43,
                    "contradiction": 0.52,
                    "continuity": 0.40,
                    "authority": 0.42,
                    "faithfulness": 0.44,
                },
                "verdict": "HOLD",
                "frontier_o_verification": {},
            }
            manifest, details = export_decision_prover_observatory_bundle(
                experiment_id="exp-regressed-manifest-check",
                study_name="Regressed_Bundle_Test",
                title="Regressed & Incompatible Manifest Consistency Check",
                hypothesis="Candidate regresses and has mismatched shared_input.",
                baseline_packet=base_pkt,
                baseline_context=base_ctx,
                candidate_packet=cand_pkt,
                candidate_context=cand_ctx,
                measured_baseline_time_s=0.10,
                measured_candidate_time_s=0.25,
                experiments_root=tmp_path / "experiments",
                observatory_db_path=tmp_path / "obs.sqlite3",
                register_in_observatory_db=False,
            )
            self.assertEqual(manifest.outcome, "inconclusive")
            self.assertEqual(manifest.comparability, "incompatible")
            self.assertGreater(len(manifest.warnings), 0)

            disk_cand_text = Path(manifest.candidate_packet_path).read_text(encoding="utf-8")
            disk_cand_pkt = json.loads(disk_cand_text)
            self.assertEqual(
                disk_cand_pkt["frontier_o_verification"]["sol_change_handoff"],
                manifest.to_dict(),
            )
            self.assertEqual(
                details["candidate_packet"]["frontier_o_verification"]["sol_change_handoff"],
                manifest.to_dict(),
            )
            self.assertEqual(
                details["candidate_run"]["configuration"]["sol_continuum"]["sha256_source_text"],
                obs_digest(disk_cand_text),
            )

            # Also verify compatible context with regressed metrics produces outcome == "regressed"
            cand_ctx_compat = build_observatory_context_sidecar(
                study_name="Regressed_Bundle_Test",
                input_text="shared-input-A",
                workflow_version="v2.0-cand",
                executed_at="2026-10-22T00:00:01Z",
            )
            reg_manifest, reg_details = export_decision_prover_observatory_bundle(
                experiment_id="exp-compatible-regressed-check",
                study_name="Regressed_Bundle_Test",
                title="Compatible Regressed Manifest Consistency Check",
                hypothesis="Candidate regresses under identical context.",
                baseline_packet=base_pkt,
                baseline_context=base_ctx,
                candidate_packet=cand_pkt,
                candidate_context=cand_ctx_compat,
                measured_baseline_time_s=0.10,
                measured_candidate_time_s=0.25,
                experiments_root=tmp_path / "experiments",
                observatory_db_path=tmp_path / "obs.sqlite3",
                register_in_observatory_db=False,
            )
            self.assertEqual(reg_manifest.comparability, "compatible")
            self.assertEqual(reg_manifest.outcome, "regressed")
            reg_disk_text = Path(reg_manifest.candidate_packet_path).read_text(encoding="utf-8")
            reg_disk_pkt = json.loads(reg_disk_text)
            self.assertEqual(
                reg_disk_pkt["frontier_o_verification"]["sol_change_handoff"],
                reg_manifest.to_dict(),
            )
            self.assertEqual(
                reg_details["candidate_run"]["configuration"]["sol_continuum"]["sha256_source_text"],
                obs_digest(reg_disk_text),
            )

    def test_gemini_client_interactions_api_fenced_and_malformed_fallback(self) -> None:
        class _FakeContentItem:
            def __init__(self, item_type: str, text: str = "", signature: str = "", summary: object = None) -> None:
                self.type = item_type
                self.text = text
                self.signature = signature
                self.summary = summary

        class _FakeUsage:
            total_input_tokens = 612
            total_thought_tokens = 944
            total_output_tokens = 288

        fenced_payload = (
            "```json\n"
            + json.dumps(
                {
                    "selected_option_id": "OPT-ALPHA-SOVEREIGN-MESH",
                    "selected_option_name": "Sovereign Hybrid Photonic-Electronic Mesh",
                    "calibrated_weight_vector": [3.8, 3.4, 2.8],
                    "calibrated_holonomy_flux_compensation": -0.88,
                    "calibrated_alpha_coupling": 1.0,
                    "decision_prover_theorem_title": "Mock Live WGSL Simplex Theorem",
                    "decision_prover_rationale": "Fenced JSON live Gemini 4 Argon calibration rationale.",
                    "observatory_hypothesis": "Fenced JSON live Gemini 4 Argon observatory hypothesis.",
                }
            )
            + "\n```"
        )

        class _FakeInteractionFenced:
            id = "v1_mock_wgsl_prover_interaction_fenced01"
            usage = _FakeUsage()
            outputs = [
                _FakeContentItem(
                    item_type="thought",
                    signature="mock_cryptographic_thought_signature_bytes_frontier_o",
                    summary=["Synthesizing 64-thread WGSL simplex Pareto exhaustion and MSCK holonomy compensation."],
                ),
                _FakeContentItem(item_type="text", text=fenced_payload),
            ]

        captured_kwargs: dict = {}

        class _FakeInteractionsAPIFenced:
            def create(self, **kwargs: object) -> _FakeInteractionFenced:
                captured_kwargs.update(kwargs)
                return _FakeInteractionFenced()

        class _FakeGeminiClientFenced:
            interactions = _FakeInteractionsAPIFenced()

        ep = self.orchestrator.run_wgsl_decision_prover_episode(
            study_name="Frontier_O_Mock_Live_Fenced_Test",
            gemini_client=_FakeGeminiClientFenced(),
            repeat_trial_count=3,
            register_in_observatory_db=False,
        )
        self.assertEqual(captured_kwargs.get("model"), "gemini-4-argon")
        self.assertEqual(
            captured_kwargs.get("generation_config"),
            {"thinking_level": "high", "thinking_summaries": "auto"},
        )
        self.assertEqual(ep.interaction_id, "v1_mock_wgsl_prover_interaction_fenced01")
        self.assertEqual(
            ep.sol_lens_packet["reasoning_telemetry"]["interaction_id"],
            "v1_mock_wgsl_prover_interaction_fenced01",
        )
        self.assertEqual(len(ep.sol_lens_packet["reasoning_telemetry"]["thought_signature_digests"]), 1)
        self.assertAlmostEqual(
            sum(ep.frontier_o_verification["calibration_spec"]["calibrated_weight_vector"]),
            1.0,
            places=4,
        )
        self.assertEqual(
            ep.decision_prover_theorem_title,
            "Mock Live WGSL Simplex Theorem",
        )

        # Also test truncated/malformed JSON output from interactions.create:
        # must fall back cleanly to deterministic calibration while preserving live interaction_id and ledger sync
        class _FakeInteractionTruncated:
            id = "v1_mock_wgsl_prover_interaction_trunc99"
            usage = _FakeUsage()
            outputs = [
                _FakeContentItem(
                    item_type="thought",
                    signature="mock_sig_truncated_frontier_o",
                    summary=["Partial thought summary before output truncation."],
                ),
                _FakeContentItem(item_type="text", text='{"selected_option_id": "OPT-ALPHA-SOVEREIGN-MESH", "calibr'),
            ]

        class _FakeGeminiClientTruncated:
            class interactions:
                @staticmethod
                def create(**kwargs: object) -> _FakeInteractionTruncated:
                    return _FakeInteractionTruncated()

        ep_trunc = self.orchestrator.run_wgsl_decision_prover_episode(
            study_name="Frontier_O_Mock_Live_Truncated_Test",
            gemini_client=_FakeGeminiClientTruncated(),
            repeat_trial_count=3,
            register_in_observatory_db=False,
        )
        self.assertEqual(ep_trunc.interaction_id, "v1_mock_wgsl_prover_interaction_trunc99")
        self.assertEqual(len(ep_trunc.sol_lens_packet["reasoning_telemetry"]["thought_signature_digests"]), 1)
        ledger = GovernanceCourtLedger(db_path=str(self.root / "wgsl_mock_live_ledger.sqlite3"))
        try:
            receipt = ledger.record_wgsl_decision_prover_episode(ep_trunc)
            self.assertTrue(receipt["run_id"].endswith(":on_trunc99"))
            assessment = assess_continuum_observatory(
                Path(ep_trunc.experiment_bundle_dir),
                ledger_db=self.root / "wgsl_mock_live_ledger.sqlite3",
            )
            self.assertTrue(assessment["runtime_replay_verification"]["verified"])
        finally:
            ledger.close()


if __name__ == "__main__":
    unittest.main()
