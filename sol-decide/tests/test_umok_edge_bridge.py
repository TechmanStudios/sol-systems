"""
Tests for Frontier Q (Vector 20): Unified Manifold Operating Kernel (UMOK),
Zero-Copy ROS2/CAN Bridge & 17-Frontier Unification
(`sol-edge` x `sol-decide` x `sol-change` x `sol-lens`).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

_SOL_SYSTEMS_ROOT = Path(__file__).resolve().parents[2]
for _p in (
    _SOL_SYSTEMS_ROOT,
    _SOL_SYSTEMS_ROOT / "Frontier_OS",
    _SOL_SYSTEMS_ROOT / "sol-decide",
    _SOL_SYSTEMS_ROOT / "sol-change",
    _SOL_SYSTEMS_ROOT / "sol-edge" / "src",
):
    _ps = str(_p)
    if _p.exists() and _ps not in sys.path:
        sys.path.insert(0, _ps)

from observatory.continuum import assess_continuum_observatory
from observatory.domain import validate_archive, validate_run
from sol_edge.umok import (
    SafeStateAction,
    UMOKEdgeEligibilityInterlock,
    UMOKNativeGeodesicKernel,
    ZeroCopyIPCRingBuffer,
)

from sol_decide.cli import main as sol_decide_cli_main
from sol_decide.delivery.governance_ledger import GovernanceCourtLedger
from sol_decide.interop.umok_edge_bridge import (
    SolEdgeUMOKKernelGate,
    UMOKEdgeKernelOrchestrator,
    run_frontier_q_umok_edge_study,
)


class TestUMOKEdgeBridgeFrontierQ(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temp_dir.name)
        self.experiments_root = self.root / "experiments"
        self.obs_db = self.root / "observatory.sqlite3"
        self.ledger_db = self.root / "governance_ledger.sqlite3"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_sol_edge_umok_kernel_gate_cycle0_quarantine_and_cycle1_eligible(self) -> None:
        kernel = UMOKNativeGeodesicKernel(kernel_id="test-umok-kernel", deadline_us=1.0)
        alu_report = kernel.verify_riemannian_alu_truth_tables()
        self.assertTrue(alu_report.all_gates_passed)
        self.assertEqual(alu_report.passed_cases, 20)

        batch_c0 = kernel.step_geodesic_verlet_batch(
            steps=2048,
            dt=0.0005,
            damping_gamma=0.15,
            coupling_a=0.32,
            coupling_b=0.24,
            simulate_unbuffered_fault=True,
        )
        ring_c0 = ZeroCopyIPCRingBuffer(capacity_slots=8)
        ring_c0.write_frame_zero_copy(
            can_id=0x1A0,
            sequence_number=1,
            status_flags=0x0001,
            joint_targets_rad=(0.12, -0.18, 0.24, -0.15, 0.30, -0.22),
            step_latency_ns=int(float(batch_c0.mean_step_latency_us) * 1000),
            inject_crc_fault=True,
        )
        gate = SolEdgeUMOKKernelGate(deadline_us=1.0)

        audit_c0, interlock_c0 = gate.evaluate_cycle(
            cycle_index=0,
            run_id="run:test-umok-gate",
            option_id="opt_umok:c0",
            geodesic_batch=batch_c0,
            alu_report=alu_report,
            ring_buffer=ring_c0,
            timestamp_base="2026-10-22T16:00:00Z",
        )
        self.assertTrue(audit_c0.is_quarantined)
        self.assertEqual(audit_c0.policy_status, "QUARANTINE")
        self.assertTrue(audit_c0.chain_verified)
        self.assertEqual(len(audit_c0.runtime_events), 4)
        self.assertEqual(
            interlock_c0.safe_state_action,
            SafeStateAction.HOLD_SAFE_POSITION,
        )
        self.assertEqual(interlock_c0.staged_frames_count, 0)
        self.assertFalse(interlock_c0.authorized_claimed)

        batch_c1 = kernel.step_geodesic_verlet_batch(
            steps=2048,
            dt=0.0005,
            damping_gamma=0.15,
            coupling_a=0.32,
            coupling_b=0.24,
            simulate_unbuffered_fault=False,
        )
        ring_c1 = ZeroCopyIPCRingBuffer(capacity_slots=8)
        for seq_idx in range(1, 5):
            ring_c1.write_frame_zero_copy(
                can_id=0x1A0,
                sequence_number=seq_idx,
                status_flags=0x0001,
                joint_targets_rad=(0.12 * seq_idx, -0.18, 0.24, -0.15, 0.30, -0.22),
                step_latency_ns=max(1, int(float(batch_c1.mean_step_latency_us) * 1000)),
            )

        audit_c1, interlock_c1 = gate.evaluate_cycle(
            cycle_index=1,
            run_id="run:test-umok-gate",
            option_id="opt_umok:c1",
            geodesic_batch=batch_c1,
            alu_report=alu_report,
            ring_buffer=ring_c1,
            timestamp_base="2026-10-22T16:00:05Z",
        )
        self.assertFalse(audit_c1.is_quarantined)
        self.assertEqual(audit_c1.policy_status, "ELIGIBLE")
        self.assertTrue(audit_c1.chain_verified)
        self.assertEqual(len(audit_c1.runtime_events), 4)
        self.assertEqual(
            interlock_c1.safe_state_action,
            SafeStateAction.NONE,
        )
        self.assertEqual(interlock_c1.staged_frames_count, 4)
        self.assertFalse(interlock_c1.authorized_claimed)
        self.assertEqual(
            interlock_c1.release_gate_status,
            "ELIGIBLE_AWAITING_RELEASE_AUTHORITY",
        )

    def test_end_to_end_orchestrator_governance_ledger_and_observatory_assessment(self) -> None:
        orch = UMOKEdgeKernelOrchestrator()
        sample_pkt = self.root / "sample_umok_packet.json"
        ep = orch.run_umok_edge_episode(
            study_name="Frontier_Q_UMOK_Sub_Microsecond_Test",
            experiments_root=self.experiments_root,
            observatory_db_path=self.obs_db,
            register_in_observatory_db=True,
            sample_packet_out=sample_pkt,
        )
        self.assertTrue(sample_pkt.is_file())
        self.assertTrue(sample_pkt.with_suffix(".context.json").is_file())
        self.assertEqual(ep.cycle0_audit.policy_status, "QUARANTINE")
        self.assertEqual(ep.cycle1_audit.policy_status, "ELIGIBLE")
        self.assertEqual(ep.handoff_manifest.comparability, "compatible")
        self.assertEqual(ep.handoff_manifest.outcome, "improved")
        self.assertEqual(ep.handoff_manifest.review_status, "awaiting_review")
        self.assertTrue(ep.frontier_q_verification["umok_kernel_verified"])

        exp_dir = Path(ep.handoff_manifest.experiment_dir)
        validate_run(json.loads((exp_dir / "baseline.json").read_text(encoding="utf-8")))
        validate_run(json.loads((exp_dir / "candidate.json").read_text(encoding="utf-8")))
        validate_archive(json.loads((exp_dir / "experiment.json").read_text(encoding="utf-8")))

        ledger = GovernanceCourtLedger(db_path=str(self.ledger_db))
        try:
            rec = ledger.record_umok_edge_episode(ep)
            self.assertEqual(rec["policy_status"], "eligible")
            self.assertTrue(rec["frontier_q_verified"])
            integrity = ledger.verify_ledger_integrity()
            self.assertTrue(integrity.is_valid)
            self.assertEqual(integrity.total_runs_verified, 1)
            self.assertEqual(integrity.total_events_verified, 8)

            assessment = assess_continuum_observatory(exp_dir, ledger_db=self.ledger_db)
            self.assertEqual(assessment["comparability"], "compatible")
            self.assertEqual(assessment["outcome"], "improved")
            self.assertTrue(assessment["runtime_replay_verification"]["verified"])
            fq_sum = assessment["cycle_drift_breakdown"]["frontier_verification_summary"][
                "frontier_q"
            ]
            self.assertTrue(fq_sum["verified"])
            self.assertFalse(fq_sum["authorized_claimed"])
            self.assertEqual(fq_sum["cycle1_staged_frames_count"], 4)

            # Post-persistence SQLite tamper check 1: authorized_claimed = True
            bad_auth_pkt = json.loads(json.dumps(ep.proof_packet))
            bad_auth_pkt["frontier_q_verification"]["eligibility_interlock"][
                "authorized_claimed"
            ] = True
            ledger._conn.execute(
                "UPDATE governance_court_runs SET proof_packet_json = ? WHERE run_id = ?",
                (json.dumps(bad_auth_pkt), rec["run_id"]),
            )
            ledger._conn.commit()
            tampered_integrity = ledger.verify_ledger_integrity()
            self.assertFalse(tampered_integrity.is_valid)
            self.assertIn(rec["run_id"], tampered_integrity.broken_run_ids)

            # Post-persistence SQLite tamper check 2: frontier_q_summary_digest mismatch
            bad_digest_pkt = json.loads(json.dumps(ep.proof_packet))
            bad_digest_pkt["frontier_q_verification"]["frontier_q_summary_digest"] = (
                "sha256:0000000000000000000000000000000000000000000000000000000000000000"
            )
            ledger._conn.execute(
                "UPDATE governance_court_runs SET proof_packet_json = ? WHERE run_id = ?",
                (json.dumps(bad_digest_pkt), rec["run_id"]),
            )
            ledger._conn.commit()
            self.assertFalse(ledger.verify_ledger_integrity().is_valid)

            # Post-persistence SQLite tamper check 3: cycle0_safe_state_action tampered
            bad_c0_action_pkt = json.loads(json.dumps(ep.proof_packet))
            bad_c0_action_pkt["frontier_q_verification"]["eligibility_interlock"][
                "cycle0_safe_state_action"
            ] = "STAGE_ELIGIBLE_FRAMES"
            ledger._conn.execute(
                "UPDATE governance_court_runs SET proof_packet_json = ? WHERE run_id = ?",
                (json.dumps(bad_c0_action_pkt), rec["run_id"]),
            )
            ledger._conn.commit()
            self.assertFalse(ledger.verify_ledger_integrity().is_valid)
        finally:
            ledger.close()

        # Boundary checks on UMOKEdgeKernelOrchestrator
        with self.assertRaises(ValueError):
            UMOKEdgeKernelOrchestrator(steps=0)
        with self.assertRaises(ValueError):
            UMOKEdgeKernelOrchestrator(deadline_us=1.5)
        with self.assertRaises(ValueError):
            UMOKEdgeKernelOrchestrator(deadline_us=0.0)

        # Fail-closed tamper check on GovernanceCourtLedger.record_umok_edge_episode
        tampered_ep = json.loads(json.dumps(ep.to_dict()))
        tampered_ep["frontier_q_verification"]["geodesic_verlet_kernel"][
            "cycle1_mean_step_latency_us"
        ] = 1.45
        ledger2 = GovernanceCourtLedger(db_path=str(self.root / "tampered.sqlite3"))
        try:
            with self.assertRaises(ValueError):
                ledger2.record_umok_edge_episode(tampered_ep)
        finally:
            ledger2.close()

    def test_cli_umok_edge_subcommand(self) -> None:
        pkt_out = self.root / "cli_umok_pkt.json"
        json_out = self.root / "cli_umok_summary.json"
        rc = sol_decide_cli_main(
            [
                "umok-edge",
                "--study-name",
                "CLI_UMOK_Edge_Test",
                "--experiments-root",
                str(self.experiments_root / "cli_runs"),
                "--export-packet",
                str(pkt_out),
                "--ledger-db",
                str(self.root / "cli_ledger.sqlite3"),
                "--output-json",
                str(json_out),
            ]
        )
        self.assertEqual(rc, 0)
        self.assertTrue(pkt_out.is_file())
        self.assertTrue(json_out.is_file())
        summary = json.loads(json_out.read_text(encoding="utf-8"))
        self.assertTrue(summary["frontier_q_verified"])
        self.assertEqual(summary["comparability"], "compatible")
        self.assertEqual(summary["outcome"], "improved")

    def test_run_frontier_q_umok_edge_study_convenience_entrypoint(self) -> None:
        pkt_out = self.root / "convenience_umok_pkt.json"
        ep = run_frontier_q_umok_edge_study(
            study_name="Convenience_Frontier_Q_Study",
            steps=512,
            deadline_us=1.0,
            trial_count=3,
            seed=42,
            use_live_api=False,
            experiments_root=self.experiments_root / "conv_runs",
            observatory_db_path=self.root / "conv_observatory.sqlite3",
            register_in_observatory_db=True,
            export_packet_path=pkt_out,
        )
        self.assertEqual(ep.study_name, "Convenience_Frontier_Q_Study")
        self.assertEqual(ep.steps_executed, 512)
        self.assertTrue(pkt_out.is_file())
        self.assertTrue(pkt_out.with_suffix(".context.json").is_file())
        self.assertEqual(ep.cycle0_audit.policy_status, "QUARANTINE")
        self.assertEqual(ep.cycle1_audit.policy_status, "ELIGIBLE")
        self.assertEqual(ep.handoff_manifest.comparability, "compatible")
        self.assertEqual(ep.handoff_manifest.outcome, "improved")
        self.assertTrue(ep.frontier_q_verification["umok_kernel_verified"])

    def test_gemini_client_interactions_api_and_ledger_sync(self) -> None:
        class _FakeContentItem:
            def __init__(self, item_type: str, text: str = "", signature: str = "", summary: object = None) -> None:
                self.type = item_type
                self.text = text
                self.signature = signature
                self.summary = summary

        class _FakeUsage:
            total_input_tokens = 856
            total_thought_tokens = 343
            total_output_tokens = 236

        class _FakeInteraction:
            id = "v1_mock_umok_edge_interaction_01"
            usage = _FakeUsage()
            outputs = [
                _FakeContentItem(
                    item_type="thought",
                    signature="mock_cryptographic_thought_signature_bytes_frontier_q",
                    summary=["Synthesizing C-buffered Geodesic Verlet and zero-copy CAN-FD CRC32 repair spec."],
                ),
                _FakeContentItem(
                    item_type="text",
                    text="```json\n"
                    + json.dumps(
                        {
                            "calibration_id": "MOCK-FRONTIER-Q-CAL-01",
                            "lock_free_c_buffer_enabled": True,
                            "zero_copy_memoryview_enabled": True,
                            "can_fd_crc32_hardware_sync": True,
                            "damping_gamma": 0.15,
                            "coupling_a": 0.32,
                            "coupling_b": 0.24,
                            "can_fd_frames_per_batch": 4,
                            "cohomological_rationale": "Contiguous C-buffered Verlet integration and IEEE 802.3 CRC32 verification restore sub-microsecond determinism.",
                        }
                    )
                    + "\n```",
                ),
            ]

        captured_kwargs: dict = {}

        class _FakeInteractionsAPI:
            def create(self, **kwargs: object) -> _FakeInteraction:
                captured_kwargs.update(kwargs)
                return _FakeInteraction()

        class _FakeGeminiClient:
            interactions = _FakeInteractionsAPI()

        orch = UMOKEdgeKernelOrchestrator(gemini_client=_FakeGeminiClient())
        ep = orch.run_umok_edge_episode(
            study_name="Frontier_Q_Mock_Live_Interactions_Test",
            experiments_root=self.experiments_root / "mock_live",
            observatory_db_path=self.root / "mock_live_obs.sqlite3",
            register_in_observatory_db=False,
        )
        self.assertEqual(captured_kwargs.get("model"), "gemini-4-argon")
        self.assertEqual(
            captured_kwargs.get("generation_config"),
            {"thinking_level": "high", "thinking_summaries": "auto"},
        )
        self.assertTrue(ep.reasoning_telemetry.live_api_used)
        self.assertEqual(
            ep.reasoning_telemetry.interaction_id,
            "v1_mock_umok_edge_interaction_01",
        )
        self.assertEqual(len(ep.reasoning_telemetry.thought_signature_digests), 1)
        self.assertTrue(
            ep.reasoning_telemetry.thought_signature_digests[0].startswith("sha256:")
        )
        self.assertEqual(ep.reasoning_telemetry.total_input_tokens, 856)
        self.assertEqual(ep.reasoning_telemetry.total_thought_tokens, 343)
        self.assertEqual(ep.reasoning_telemetry.total_output_tokens, 236)
        self.assertEqual(
            ep.reasoning_telemetry.calibration_spec["calibration_id"],
            "MOCK-FRONTIER-Q-CAL-01",
        )
        self.assertAlmostEqual(
            ep.reasoning_telemetry.calibration_spec["damping_gamma"],
            0.15,
            places=4,
        )
        self.assertAlmostEqual(
            ep.reasoning_telemetry.calibration_spec["coupling_a"],
            0.32,
            places=4,
        )
        self.assertAlmostEqual(
            ep.reasoning_telemetry.calibration_spec["coupling_b"],
            0.24,
            places=4,
        )

        # Verify ledger_run_id matches interaction_id across Cycle 0/1 RuntimeEvents & GovernanceCourtLedger
        ledger_live = GovernanceCourtLedger(db_path=str(self.root / "mock_live_ledger.sqlite3"))
        try:
            rec = ledger_live.record_umok_edge_episode(ep)
            self.assertEqual(rec["run_id"], ep.ledger_run_id)
            self.assertTrue(rec["run_id"].endswith(":raction_01"))
            self.assertTrue(ledger_live.verify_ledger_integrity().is_valid)
            assessment = assess_continuum_observatory(
                Path(ep.handoff_manifest.experiment_dir),
                ledger_db=self.root / "mock_live_ledger.sqlite3",
            )
            self.assertTrue(assessment["runtime_replay_verification"]["verified"])
        finally:
            ledger_live.close()

        # Verify truncated JSON output still preserves live interaction_id and thought signatures
        class _FakeTruncatedInteraction:
            id = "v1_mock_umok_edge_trunc_99"
            usage = _FakeUsage()
            outputs = [
                _FakeContentItem(
                    item_type="thought",
                    signature="mock_sig_umok_trunc_99",
                    summary=["Partial thought summary."],
                ),
                _FakeContentItem(item_type="text", text='{"calibration_id": "TRUNC'),
            ]

        class _FakeTruncatedClient:
            class interactions:
                @staticmethod
                def create(**kwargs: object) -> _FakeTruncatedInteraction:
                    return _FakeTruncatedInteraction()

        orch_trunc = UMOKEdgeKernelOrchestrator(gemini_client=_FakeTruncatedClient())
        ep_trunc = orch_trunc.run_umok_edge_episode(
            study_name="Frontier_Q_Mock_Truncated_Test",
            experiments_root=self.experiments_root / "mock_trunc",
            observatory_db_path=self.root / "mock_trunc_obs.sqlite3",
            register_in_observatory_db=False,
        )
        self.assertEqual(ep_trunc.interaction_id, "v1_mock_umok_edge_trunc_99")
        self.assertEqual(len(ep_trunc.reasoning_telemetry.thought_signature_digests), 1)


if __name__ == "__main__":
    unittest.main()

