"""
Tests for Frontier W (Vector 26): Sovereign Burn-In Runtime, Long-Horizon Stability Ledger &
Attested Distribution Package Archive / Offline Verification Kit (`sol-decide` x `sol-edge` x `sol-change` x `sol-lens`).
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

from sol_decide.cli import main as sol_decide_cli_main
from sol_decide.delivery.governance_ledger import GovernanceCourtLedger
from sol_decide.interop.burnin_attestation_bridge import (
    BurnInAttestationAuditReport,
    BurnInAttestationOrchestrator,
    SolEdgeBurnInAttestationGate,
    run_frontier_w_burnin_attestation_study,
)


class TestBurnInAttestationBridgeFrontierW(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temp_dir.name)
        self.experiments_root = self.root / "experiments"
        self.obs_db = self.root / "observatory.sqlite3"
        self.ledger_db = self.root / "governance_ledger.sqlite3"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_gate_cycle0_quarantine_and_cycle1_eligible(self) -> None:
        gate = SolEdgeBurnInAttestationGate()
        c0_rep = BurnInAttestationAuditReport(
            cycle_index=0,
            designation="baseline",
            cycles_executed=4,
            ledger_chain_valid=False,
            regression_rollback_verified=True,
            archive_file_digest_match=False,
            real_signature_claimed=False,
            network_access_used=False,
            ready_verification_steps=5,
            final_system_manifest_valid=False,
            promotion_readiness_passed=False,
            production_mutation_allowed=False,
            sacred_core_immutable=True,
        )
        audit_c0 = gate.evaluate_cycle(
            run_id="run:test-burnin-gate",
            cycle_index=0,
            designation="baseline",
            option_id="opt_burnin_test",
            audit_report=c0_rep,
            effective_beta_1=1,
            theorem_proved=True,
        )
        self.assertTrue(audit_c0.is_quarantined)
        self.assertEqual(audit_c0.policy_status, "QUARANTINE")
        self.assertEqual(len(audit_c0.events), 4)
        self.assertFalse(audit_c0.authorized_claimed)

        c1_rep = BurnInAttestationAuditReport(
            cycle_index=1,
            designation="candidate",
            cycles_executed=6,
            ledger_chain_valid=True,
            regression_rollback_verified=True,
            archive_file_digest_match=True,
            real_signature_claimed=False,
            network_access_used=False,
            ready_verification_steps=7,
            final_system_manifest_valid=True,
            promotion_readiness_passed=True,
            production_mutation_allowed=False,
            sacred_core_immutable=True,
        )
        audit_c1 = gate.evaluate_cycle(
            run_id="run:test-burnin-gate",
            cycle_index=1,
            designation="candidate",
            option_id="opt_burnin_test",
            audit_report=c1_rep,
            effective_beta_1=0,
            theorem_proved=True,
        )
        self.assertFalse(audit_c1.is_quarantined)
        self.assertEqual(audit_c1.policy_status, "ELIGIBLE")
        self.assertEqual(len(audit_c1.events), 4)
        self.assertFalse(audit_c1.authorized_claimed)

    def test_end_to_end_orchestrator_ledger_and_observatory_assessment(self) -> None:
        orch = BurnInAttestationOrchestrator()
        sample_pkt = self.root / "sample_burnin_packet.json"
        ep = orch.run_episode(
            study_name="Frontier_W_BurnIn_Attestation_Test",
            trial_count=3,
            experiments_root=self.experiments_root,
            observatory_db_path=self.obs_db,
            register_in_observatory_db=True,
            export_packet_path=sample_pkt,
        )
        self.assertTrue(sample_pkt.is_file())
        self.assertTrue(sample_pkt.with_suffix(".context.json").is_file())
        self.assertEqual(ep.cycle0_audit.policy_status, "QUARANTINE")
        self.assertEqual(ep.cycle1_audit.policy_status, "ELIGIBLE")
        self.assertEqual(ep.handoff_manifest.comparability, "compatible")
        self.assertEqual(ep.handoff_manifest.outcome, "improved")
        self.assertEqual(ep.handoff_manifest.review_status, "awaiting_review")
        self.assertTrue(ep.frontier_w_verification["burnin_attestation_verified"])

        exp_dir = Path(ep.handoff_manifest.experiment_dir)
        validate_run(json.loads((exp_dir / "baseline.json").read_text(encoding="utf-8")))
        validate_run(json.loads((exp_dir / "candidate.json").read_text(encoding="utf-8")))
        validate_archive(json.loads((exp_dir / "experiment.json").read_text(encoding="utf-8")))

        ledger = GovernanceCourtLedger(db_path=str(self.ledger_db))
        try:
            rec = ledger.record_burnin_attestation_episode(ep)
            self.assertEqual(rec["policy_status"], "eligible")
            self.assertTrue(rec["frontier_w_verified"])
            integrity = ledger.verify_ledger_integrity()
            self.assertTrue(integrity.is_valid)
            self.assertEqual(integrity.total_runs_verified, 1)
            self.assertEqual(integrity.total_events_verified, 8)

            assessment = assess_continuum_observatory(exp_dir, ledger_db=self.ledger_db)
            self.assertEqual(assessment["comparability"], "compatible")
            self.assertEqual(assessment["outcome"], "improved")
            self.assertTrue(assessment["runtime_replay_verification"]["verified"])
            fw_sum = assessment["cycle_drift_breakdown"]["frontier_verification_summary"][
                "frontier_w"
            ]
            self.assertTrue(fw_sum["verified"])
            self.assertEqual(fw_sum["cycles_executed"], 6)
            self.assertEqual(fw_sum["ready_verification_steps"], 7)

            # Post-persistence SQLite tamper check: frontier_w_summary_digest mismatch
            bad_digest_pkt = json.loads(json.dumps(ep.proof_packet))
            bad_digest_pkt["frontier_w_verification"]["frontier_w_summary_digest"] = (
                "sha256:0000000000000000000000000000000000000000000000000000000000000000"
            )
            ledger._conn.execute(
                "UPDATE governance_court_runs SET proof_packet_json = ? WHERE run_id = ?",
                (json.dumps(bad_digest_pkt), rec["run_id"]),
            )
            ledger._conn.commit()
            self.assertFalse(ledger.verify_ledger_integrity().is_valid)
        finally:
            ledger.close()

    def test_cli_burnin_attestation_subcommand_and_convenience(self) -> None:
        pkt_out = self.root / "cli_burnin_pkt.json"
        json_out = self.root / "cli_burnin_summary.json"
        rc = sol_decide_cli_main(
            [
                "burnin-attestation",
                "--study-name",
                "CLI_BurnIn_Attestation_Test",
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
        self.assertTrue(summary["frontier_w_verified"])
        self.assertEqual(summary["comparability"], "compatible")
        self.assertEqual(summary["outcome"], "improved")

        ep = run_frontier_w_burnin_attestation_study(
            study_name="Convenience_Frontier_W_Study",
            trial_count=3,
            use_live_api=False,
            experiments_root=self.experiments_root / "conv_runs",
            observatory_db_path=self.root / "conv_observatory.sqlite3",
            register_in_observatory_db=True,
        )
        self.assertEqual(ep.cycle0_audit.policy_status, "QUARANTINE")
        self.assertEqual(ep.cycle1_audit.policy_status, "ELIGIBLE")
        self.assertTrue(ep.frontier_w_verification["burnin_attestation_verified"])


if __name__ == "__main__":
    unittest.main()
