"""
Tests for Frontier R (Vector 21): Mitotic 2D Surface Foliation, Toroidal Surgery &
Hawking Radiation Memory Sink (`sol-decide` x `sol-edge` x `sol-change` x `sol-lens`).
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
from sol_decide.interop.mitotic_foliation_bridge import (
    MitoticFoliationOrchestrator,
    MitoticPathwayReport,
    SolEdgeMitoticFoliationGate,
    run_frontier_r_mitotic_foliation_study,
)


class TestMitoticFoliationBridgeFrontierR(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temp_dir.name)
        self.experiments_root = self.root / "experiments"
        self.obs_db = self.root / "observatory.sqlite3"
        self.ledger_db = self.root / "governance_ledger.sqlite3"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_gate_cycle0_quarantine_and_cycle1_eligible(self) -> None:
        gate = SolEdgeMitoticFoliationGate()
        c0_rep = MitoticPathwayReport(
            cycle_index=0,
            designation="baseline",
            input_density_trace=1.0,
            surface_fission_ratio_alpha=0.88,
            pathway_a_density_trace=0.88,
            pathway_b_density_trace=-0.022,
            hawking_radiated_energy=0.0,
            mass_conservation_residual=0.142,
            pathway_phase_dissonance_rad=0.624,
            toroidal_genus_g=0,
            euler_characteristic_chi=2,
            betti_numbers=(1, 0, 0),
            overlay_plasticity_retention=0.54,
            overlay_weights_persisted=5,
            sacred_core_graph_sha256="d0a80462d2b9389160502b097aca1932bb014941adf6e4b77799997283e4a1bc",
            sacred_core_immutable=True,
        )
        audit_c0 = gate.evaluate_cycle(
            run_id="run:test-mitotic-gate",
            cycle_index=0,
            designation="baseline",
            option_id="opt_mitotic_test",
            pathway_report=c0_rep,
            effective_beta_1=1,
            theorem_proved=True,
        )
        self.assertTrue(audit_c0.is_quarantined)
        self.assertEqual(audit_c0.policy_status, "QUARANTINE")
        self.assertEqual(len(audit_c0.events), 4)
        self.assertFalse(audit_c0.authorized_claimed)

        c1_rep = MitoticPathwayReport(
            cycle_index=1,
            designation="candidate",
            input_density_trace=1.0,
            surface_fission_ratio_alpha=0.50,
            pathway_a_density_trace=0.46,
            pathway_b_density_trace=0.46,
            hawking_radiated_energy=0.08,
            mass_conservation_residual=0.0,
            pathway_phase_dissonance_rad=0.0068,
            toroidal_genus_g=1,
            euler_characteristic_chi=0,
            betti_numbers=(1, 2, 1),
            overlay_plasticity_retention=0.92,
            overlay_weights_persisted=5,
            sacred_core_graph_sha256="d0a80462d2b9389160502b097aca1932bb014941adf6e4b77799997283e4a1bc",
            sacred_core_immutable=True,
        )
        audit_c1 = gate.evaluate_cycle(
            run_id="run:test-mitotic-gate",
            cycle_index=1,
            designation="candidate",
            option_id="opt_mitotic_test",
            pathway_report=c1_rep,
            effective_beta_1=0,
            theorem_proved=True,
        )
        self.assertFalse(audit_c1.is_quarantined)
        self.assertEqual(audit_c1.policy_status, "ELIGIBLE")
        self.assertEqual(len(audit_c1.events), 4)
        self.assertFalse(audit_c1.authorized_claimed)

    def test_end_to_end_orchestrator_ledger_and_observatory_assessment(self) -> None:
        orch = MitoticFoliationOrchestrator()
        sample_pkt = self.root / "sample_mitotic_packet.json"
        ep = orch.run_episode(
            study_name="Frontier_R_Mitotic_Foliation_Test",
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
        self.assertTrue(ep.frontier_r_verification["mitotic_foliation_verified"])

        exp_dir = Path(ep.handoff_manifest.experiment_dir)
        validate_run(json.loads((exp_dir / "baseline.json").read_text(encoding="utf-8")))
        validate_run(json.loads((exp_dir / "candidate.json").read_text(encoding="utf-8")))
        validate_archive(json.loads((exp_dir / "experiment.json").read_text(encoding="utf-8")))

        ledger = GovernanceCourtLedger(db_path=str(self.ledger_db))
        try:
            rec = ledger.record_mitotic_foliation_episode(ep)
            self.assertEqual(rec["policy_status"], "eligible")
            self.assertTrue(rec["frontier_r_verified"])
            integrity = ledger.verify_ledger_integrity()
            self.assertTrue(integrity.is_valid)
            self.assertEqual(integrity.total_runs_verified, 1)
            self.assertEqual(integrity.total_events_verified, 8)

            assessment = assess_continuum_observatory(exp_dir, ledger_db=self.ledger_db)
            self.assertEqual(assessment["comparability"], "compatible")
            self.assertEqual(assessment["outcome"], "improved")
            self.assertTrue(assessment["runtime_replay_verification"]["verified"])
            fr_sum = assessment["cycle_drift_breakdown"]["frontier_verification_summary"][
                "frontier_r"
            ]
            self.assertTrue(fr_sum["verified"])
            self.assertEqual(fr_sum["toroidal_genus_g"], 1)
            self.assertEqual(fr_sum["euler_characteristic_chi"], 0)

            # Post-persistence SQLite tamper check: frontier_r_summary_digest mismatch
            bad_digest_pkt = json.loads(json.dumps(ep.proof_packet))
            bad_digest_pkt["frontier_r_verification"]["frontier_r_summary_digest"] = (
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

    def test_cli_mitotic_foliation_subcommand_and_convenience(self) -> None:
        pkt_out = self.root / "cli_mitotic_pkt.json"
        json_out = self.root / "cli_mitotic_summary.json"
        rc = sol_decide_cli_main(
            [
                "mitotic-foliation",
                "--study-name",
                "CLI_Mitotic_Foliation_Test",
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
        self.assertTrue(summary["frontier_r_verified"])
        self.assertEqual(summary["comparability"], "compatible")
        self.assertEqual(summary["outcome"], "improved")

        ep = run_frontier_r_mitotic_foliation_study(
            study_name="Convenience_Frontier_R_Study",
            trial_count=3,
            use_live_api=False,
            experiments_root=self.experiments_root / "conv_runs",
            observatory_db_path=self.root / "conv_observatory.sqlite3",
            register_in_observatory_db=True,
        )
        self.assertEqual(ep.cycle0_audit.policy_status, "QUARANTINE")
        self.assertEqual(ep.cycle1_audit.policy_status, "ELIGIBLE")
        self.assertTrue(ep.frontier_r_verification["mitotic_foliation_verified"])


if __name__ == "__main__":
    unittest.main()
