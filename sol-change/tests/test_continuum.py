import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from observatory import DEFAULT_PORT
from observatory.continuum import (PACKET_SCHEMA, build_comparison, inventory, main,
                                   packet_to_run, read_artifact, validate_context)
from observatory.domain import ValidationError, compare, digest, validate_archive, validate_run
from observatory.store import Store


def sample_packet():
    return {"schema": PACKET_SCHEMA, "packet_id": "synthetic-bridge-test", "generated_at": "2026-10-15T18:00:00Z",
            "observable_trace_only": True, "fixture": "Synthetic integration task", "models": {"baseline": "Counterfactual", "candidate": "Test producer v1"},
            "metrics": {"evidence": 0.8, "coherence": 0.85, "contradiction": 0.1, "continuity": 0.8, "authority": 0.82, "faithfulness": 0.81},
            "baseline_evaluation": {"source": "Invented counterfactual", "metrics": {"evidence": 0.2}, "verdict": "QUARANTINE"},
            "logons": [{"id": "L1", "label": "Synthetic observation", "detail": "Test data only", "evidence_refs": ["javascript:never-executed()"]}],
            "edges": [], "groups": [], "verdict": "PROMOTE"}


def complete_context():
    return {"schema_version": "1.0", "input": "Exact synthetic test input", "conditions": {"dataset": "synthetic/1", "seed": 7},
            "evaluator_version": "test-scoring/1", "workflow_version": "test-workflow/1", "executed_at": "2026-10-15T17:59:00Z", "data_type": "synthetic"}


class ContinuumTests(unittest.TestCase):
    def setUp(self):
        self.packet = sample_packet()
        self.source = json.dumps(self.packet, indent=2)

    def run_for(self, role="candidate", packet=None, context=None):
        return packet_to_run(json.dumps(packet or self.packet, indent=2), role, "test-packet.json", context)

    def test_primary_observation_converts_to_valid_run(self):
        run = self.run_for()
        validate_run(run)
        self.assertEqual(run["measurements"][0]["value"], 0.8)
        self.assertEqual(run["measurements"][0]["method"]["kind"], "automated_assessment")
        self.assertEqual(run["measurements"][0]["unit"], "score/1")

    def test_baseline_designation_never_selects_counterfactual(self):
        run = self.run_for("baseline")
        self.assertEqual(run["measurements"][0]["value"], 0.8)
        self.assertEqual(run["workflow_version"], "Test producer v1")
        self.assertFalse(run["configuration"]["sol_continuum"]["counterfactual_baseline_imported"])

    def test_original_text_and_sha_survive_conversion(self):
        source = "\ufeff" + self.source.replace("\n", "\r\n") + "\r\n"
        run = packet_to_run(source, "candidate")
        metadata = run["configuration"]["sol_continuum"]
        self.assertEqual(metadata["original_source_text"], source)
        self.assertEqual(metadata["sha256_source_text"], digest(source))
        self.assertIn(digest(source), run["evidence"][1]["reference"])

    def test_time_cost_and_human_review_are_unknown(self):
        run = self.run_for()
        for measurement in run["measurements"][-3:]:
            self.assertIsNone(measurement["value"])
            self.assertEqual(measurement["evidence_ids"], [])

    def test_missing_context_is_visible_in_comparison(self):
        exp = build_comparison(self.run_for("baseline"), self.run_for("candidate"), "Test intake", "Test metadata visibility")
        result = compare(exp)
        self.assertEqual(result["comparability"], "limited")
        self.assertIn("Original execution input", " ".join(result["warnings"]))
        self.assertIn("Scoring implementation/version", " ".join(result["warnings"]))
        self.assertIn("data origin", " ".join(result["warnings"]))

    def test_different_scenarios_are_incompatible(self):
        candidate = copy.deepcopy(self.packet)
        candidate["fixture"] = "Different engineering task"
        exp = build_comparison(self.run_for("baseline"), self.run_for("candidate", candidate), "Different tasks", "Interoperability check")
        result = compare(exp)
        self.assertEqual(result["comparability"], "incompatible")
        self.assertTrue(all(row["delta"] is None for row in result["metrics"]))

    def test_complete_context_allows_descriptive_pair(self):
        context = complete_context()
        exp = build_comparison(self.run_for("baseline", context=context), self.run_for("candidate", context=context), "Same task", "Synthetic test")
        result = compare(exp)
        self.assertEqual(result["comparability"], "compatible")
        self.assertEqual(result["counts"]["unknown"], 3)
        self.assertIn("SYNTHETIC", result["limitations"][0])

    def test_changed_evaluator_version_withholds_metric_deltas(self):
        left = complete_context()
        right = {**left, "evaluator_version": "test-scoring/2"}
        exp = build_comparison(self.run_for("baseline", context=left), self.run_for("candidate", context=right), "Scoring changed", "Test")
        self.assertEqual(compare(exp)["metrics"][0]["status"], "incompatible")

    def test_changed_execution_conditions_are_incompatible(self):
        left = complete_context()
        right = {**left, "conditions": {"dataset": "synthetic/2", "seed": 7}}
        exp = build_comparison(self.run_for("baseline", context=left), self.run_for("candidate", context=right), "Dataset changed", "Test")
        self.assertEqual(compare(exp)["comparability"], "incompatible")

    def test_timestamp_basis_is_explicit(self):
        without_context = self.run_for()
        self.assertEqual(without_context["configuration"]["sol_continuum"]["timestamp_basis"], "packet_generated_at")
        with_context = self.run_for(context=complete_context())
        self.assertEqual(with_context["executed_at"], complete_context()["executed_at"])
        self.assertEqual(with_context["configuration"]["sol_continuum"]["timestamp_basis"], "execution")

    def test_normalized_evaluation_is_selected(self):
        self.packet["evaluation"] = {"engine": "SOL Engine", "scoring_profile": "observable-trace/1", "metrics": {**self.packet["metrics"], "evidence": 0.9}}
        run = self.run_for()
        self.assertEqual(run["measurements"][0]["value"], 0.9)
        self.assertEqual(run["measurements"][0]["method"]["version"], "observable-trace/1")
        self.assertIn("#/evaluation/metrics/evidence", run["evidence"][1]["reference"])
        self.assertIn("Top-level claimed scores differ", " ".join(run["configuration"]["sol_continuum"]["context_warnings"]))

    def test_normalized_packet_without_top_level_metrics_supported(self):
        self.packet["evaluation"] = {"scoring_profile": "observable-trace/1", "metrics": self.packet.pop("metrics")}
        validate_run(self.run_for())

    def test_normalized_verdict_is_retained_as_a_source_claim(self):
        self.packet["evaluation"] = {"scoring_profile": "observable-trace/1", "metrics": self.packet["metrics"], "verdict": "HOLD"}
        run = self.run_for()
        self.assertEqual(run["configuration"]["sol_continuum"]["upstream_verdict"], "HOLD")
        self.assertIn('authorization): "HOLD"', run["output"])

    def test_embedded_context_is_supported(self):
        self.packet["observatory_context"] = complete_context()
        run = self.run_for()
        self.assertEqual(run["input"], "Exact synthetic test input")
        self.assertEqual(run["data_type"], "synthetic")

    def test_context_conflict_is_not_silently_overridden(self):
        self.packet["observatory_context"] = complete_context()
        with self.assertRaisesRegex(ValidationError, "conflicts"):
            self.run_for(context={**complete_context(), "input": "Different input"})

    def test_unsupported_schema_fails(self):
        self.packet["schema"] = "techman.sol-lens.proof-packet/v0.1"
        with self.assertRaisesRegex(ValidationError, "Supported native packet schema"):
            self.run_for()

    def test_out_of_range_score_is_not_a_percentage(self):
        self.packet["metrics"]["evidence"] = 92
        with self.assertRaisesRegex(ValidationError, "not percentages"):
            self.run_for()

    def test_missing_metric_stays_unknown(self):
        del self.packet["metrics"]["evidence"]
        self.assertIsNone(self.run_for()["measurements"][0]["value"])

    def test_malformed_packet_fields_fail_clearly(self):
        for field in ("packet_id", "generated_at", "observable_trace_only", "logons", "metrics"):
            broken = copy.deepcopy(self.packet)
            broken[field] = {} if field == "logons" else []
            with self.subTest(field=field), self.assertRaises(ValidationError):
                self.run_for(packet=broken)

    def test_malformed_context_fails_clearly(self):
        for field in complete_context():
            context = complete_context()
            context[field] = []
            with self.subTest(field=field), self.assertRaises(ValidationError):
                validate_context(context)

    def test_oversized_packet_rejected(self):
        with self.assertRaisesRegex(ValidationError, "1 MB"):
            packet_to_run(" " * 1_000_001, "candidate")

    def test_conversion_never_fetches_references(self):
        self.packet["logons"][0]["evidence_refs"] = ["https://example.invalid/do-not-fetch"]
        with patch("urllib.request.urlopen", side_effect=AssertionError("Network must not be called")):
            self.assertIn("https://example.invalid", self.run_for()["configuration"]["sol_continuum"]["original_source_text"])

    def test_upstream_promote_creates_no_human_decision(self):
        exp = build_comparison(self.run_for("baseline"), self.run_for("candidate"), "Intake", "Test")
        self.assertEqual(exp["decisions"], [])
        self.assertEqual(exp["review_status"], "awaiting_review")

    def test_complete_archive_roundtrip_preserves_sources_and_review(self):
        exp = build_comparison(self.run_for("baseline"), self.run_for("candidate"), "Intake", "Test")
        validate_archive(exp)
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "test.db")
            restored = store.import_archive(json.dumps(exp))
            decided = store.decide(restored["id"], {"outcome": "inconclusive", "action": "run_another_experiment", "reviewer": "Synthetic integration QA", "rationale": "Missing execution conditions.", "supporting_evidence": [], "unresolved_questions": []})
            target = Store(Path(folder) / "restored.db")
            self.assertEqual(target.import_archive(json.dumps(decided)), decided)

    def test_default_port_does_not_collide_with_sol_server(self):
        self.assertEqual(DEFAULT_PORT, 8770)


class ContinuumCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.packet_file = self.root / "source.json"
        self.packet_file.write_text(json.dumps(sample_packet()), encoding="utf-8")

    def invoke(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = main(args)
        return code, output.getvalue()

    def test_convert_writes_valid_source_preserving_run(self):
        output = self.root / "run.json"
        self.assertEqual(self.invoke(["convert", str(self.packet_file), "--designation", "candidate", "--output", str(output)])[0], 0)
        validate_run(json.loads(output.read_text(encoding="utf-8")))

    def test_convert_refuses_overwrite(self):
        output = self.root / "run.json"
        output.write_text("keep this", encoding="utf-8")
        code, text = self.invoke(["convert", str(self.packet_file), "--designation", "candidate", "--output", str(output)])
        self.assertEqual(code, 2)
        self.assertIn("already exists", text)
        self.assertEqual(output.read_text(encoding="utf-8"), "keep this")

    def test_pair_registers_and_preserves_existing_review_on_retry(self):
        db = self.root / "observatory.db"
        args = ["compare", "--baseline", str(self.packet_file), "--candidate", str(self.packet_file), "--title", "CLI integration QA", "--change", "Synthetic test", "--register", "--db", str(db)]
        self.assertEqual(self.invoke(args + ["--output-dir", str(self.root / "first")])[0], 0)
        store = Store(db)
        exp = store.list()[0]
        decision = {"outcome": "inconclusive", "action": "run_another_experiment", "reviewer": "Synthetic CLI QA", "rationale": "Test only", "supporting_evidence": [], "unresolved_questions": []}
        expected = store.decide(exp["id"], decision)
        code, output = self.invoke(args + ["--output-dir", str(self.root / "retry")])
        self.assertEqual(code, 0)
        self.assertIn('"review_status": "reviewed"', output)
        self.assertEqual(store.get(exp["id"]), expected)
        for name in ("baseline.json", "candidate.json", "experiment.json", "comparison.md"):
            self.assertTrue((self.root / "first" / name).is_file())

    def test_inventory_is_bounded_and_does_not_import_sibling_code(self):
        samples = self.root / "sol-lens" / "samples"
        samples.mkdir(parents=True)
        (samples / "test.json").write_bytes(self.packet_file.read_bytes())
        sentinel = self.root / "sol-lens" / "__init__.py"
        sentinel.write_text("raise RuntimeError('Do not execute sibling code')", encoding="utf-8")
        result = inventory(self.root)
        self.assertEqual(len(result["components"]), 9)
        self.assertEqual(len(result["artifacts"]), 1)
        self.assertEqual(result["artifacts"][0]["adapter"], "sol-lens-proof-packet/1.0")

    def test_byte_identity_preserves_crlf_and_bom(self):
        raw = b"\xef\xbb\xbf" + self.packet_file.read_bytes().replace(b",", b",\r\n")
        self.packet_file.write_bytes(raw)
        text, checksum = read_artifact(self.packet_file)
        self.assertEqual(text.encode("utf-8"), raw)
        self.assertEqual(checksum, digest(text))

    def test_missing_packet_returns_error_without_outputs(self):
        output = self.root / "missing-output.json"
        code, _ = self.invoke(["convert", str(self.root / "missing.json"), "--designation", "candidate", "--output", str(output)])
        self.assertEqual(code, 2)
        self.assertFalse(output.exists())

    def test_assess_continuum_observatory_drift_and_cli_replay(self):
        from observatory.continuum import assess_continuum_observatory

        base_pkt = copy.deepcopy(sample_packet())
        base_pkt["packet_id"] = "pkt-c0"
        base_pkt["verdict"] = "QUARANTINE"
        base_pkt["metrics"] = {"evidence": 0.45, "coherence": 0.50, "contradiction": 0.40,
                               "continuity": 0.48, "authority": 0.52, "faithfulness": 0.46}
        base_pkt["observatory_context"] = complete_context()

        cand_pkt = copy.deepcopy(sample_packet())
        cand_pkt["packet_id"] = "pkt-c1"
        cand_pkt["verdict"] = "PROMOTE"
        cand_pkt["metrics"] = {"evidence": 0.92, "coherence": 0.94, "contradiction": 0.04,
                               "continuity": 0.91, "authority": 0.95, "faithfulness": 0.93}
        cand_pkt["observatory_context"] = complete_context()
        cand_pkt["frontier_k_verification"] = {
            "all_six_capabilities_verified": True,
            "summary_digest": "sha256:fk-test-digest",
        }
        cand_pkt["frontier_l_verification"] = {
            "all_five_capabilities_verified": True,
            "summary_digest": "sha256:fl-test-digest",
        }
        cand_pkt["frontier_n_verification"] = {
            "autopoietic_loop_verified": True,
            "summary_digest": "sha256:fn-test-digest",
            "epistemic_gap_intake": {"core_immutability_verified": True, "selected_gap": {"gap_id": "GAP-001"}},
            "bimodal_dream_consolidation": {"bimodal_synapse_verified": True},
            "bilateral_entangler_control": {
                "bilateral_lock_verified": True,
                "transverse_msf_lambda_hat": -0.417588,
                "cycle0_control": {"nudge_rejection_reason": "msf_unstable"},
            },
            "statistical_evolution_governance": {
                "promotion_statistically_governed": True,
                "self_train_gatekeeper": {"accepted": True},
            },
        }

        base_file = self.root / "base_pkt.json"
        cand_file = self.root / "cand_pkt.json"
        base_file.write_text(json.dumps(base_pkt), encoding="utf-8")
        cand_file.write_text(json.dumps(cand_pkt), encoding="utf-8")

        exp_dir = self.root / "exp_bundle"
        code, _ = self.invoke([
            "compare",
            "--baseline", str(base_file),
            "--candidate", str(cand_file),
            "--title", "Cycle 0 vs Cycle 1 Drift",
            "--change", "Riemannian circuit synthesis + WGSL verification",
            "--output-dir", str(exp_dir),
        ])
        self.assertEqual(code, 0)

        report = assess_continuum_observatory(exp_dir)
        self.assertEqual(report["comparability"], "compatible")
        self.assertEqual(report["outcome"], "improved")
        self.assertEqual(report["cycle_drift_breakdown"]["verdict_transition"], "QUARANTINE -> PROMOTE")
        self.assertGreater(report["cycle_drift_breakdown"]["mean_quality_drift"], 0.40)
        f_summary = report["cycle_drift_breakdown"]["frontier_verification_summary"]
        self.assertTrue(f_summary["frontier_k_verified"])
        self.assertTrue(f_summary["frontier_l_verified"])
        self.assertTrue(f_summary["frontier_n_verified"])
        self.assertTrue(f_summary["frontier_n_core_immutability_verified"])
        self.assertTrue(f_summary["frontier_n_bimodal_dream_verified"])
        self.assertTrue(f_summary["frontier_n_bilateral_entangler_verified"])
        self.assertTrue(f_summary["frontier_n_statistical_governance_verified"])
        self.assertTrue(f_summary["frontier_n_msf_cycle0_blocked"])
        self.assertTrue(f_summary["frontier_n_gatekeeper_promoted"])

        assess_out = self.root / "assessment.json"
        code, text = self.invoke([
            "assess",
            "--experiment", str(exp_dir),
            "--output", str(assess_out),
        ])
        self.assertEqual(code, 0)
        self.assertTrue(assess_out.is_file())
        parsed = json.loads(text)
        self.assertEqual(parsed["cycle_drift_breakdown"]["verdict_transition"], "QUARANTINE -> PROMOTE")


if __name__ == "__main__":
    unittest.main()
