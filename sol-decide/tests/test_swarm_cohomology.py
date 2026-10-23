"""
Tests for Frontier P (Vector 18): Multi-Robot Embodied Swarm Cohomology,
25kg Closed-Chain Bimanual Manipulation & Decentralized SE(3) Wilson Loop Calibration
(`Frontier_OS` x `sol-decide` x `sol-change` x `sol-edge` x `sol-lens`).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

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

from Frontier_OS.core.robotics import (
    BimanualCooperativeController,
    ClosedKinematicChainSheaf,
    MultiRobotFleetManifold,
    SharedPayloadSpec,
    SwarmCohomologySafetyArbiter,
)
from observatory.continuum import assess_continuum_observatory
from observatory.domain import validate_archive, validate_run

from sol_decide.cli import main as sol_decide_cli_main
from sol_decide.delivery.governance_ledger import GovernanceCourtLedger
from sol_decide.interop.swarm_cohomology_bridge import (
    MultiRobotSwarmCohomologyOrchestrator,
    SolEdgeSwarmCohomologyGate,
)


class TestMultiRobotSwarmCohomologyFrontierP(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temp_dir.name)
        self.experiments_root = self.root / "experiments"
        self.obs_db = self.root / "observatory.sqlite3"
        self.ledger_db = self.root / "governance_ledger.sqlite3"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_fleet_manifold_12dof_riemannian_metric_and_25kg_payload(self) -> None:
        fleet = MultiRobotFleetManifold(num_robots=2)
        self.assertEqual(fleet.num_robots, 2)
        self.assertEqual(fleet.total_dof, 12)
        self.assertGreaterEqual(fleet.payload_spec.mass_kg, 25.0)

        q0 = np.array(
            [0.15, -0.55, 0.75, 0.0, 0.45, 0.0, -0.15, -0.55, 0.75, 0.0, 0.45, 0.0],
            dtype=float,
        )
        G = fleet.compute_fleet_metric(q0)
        self.assertEqual(G.shape, (12, 12))
        np.testing.assert_allclose(G, G.T, atol=1e-10)
        eigvals = np.linalg.eigvalsh(G)
        self.assertTrue(np.all(eigvals > 0.0))

        cond = float(np.linalg.cond(G))
        self.assertTrue(np.isfinite(cond) and cond > 1.0)
        _, min_inter = fleet.compute_inter_arm_repulsion_potential(q0)
        _, min_obs = fleet.compute_obstacle_clearance(q0)
        self.assertGreater(min_inter, 0.15)
        self.assertGreater(min_obs, 0.10)

        # Edge case: invalid payload mass rejected
        with self.assertRaises(ValueError):
            SharedPayloadSpec(payload_id="bad", mass_kg=0.0)
        with self.assertRaises(ValueError):
            SharedPayloadSpec(payload_id="bad_neg", mass_kg=-5.0)

    def test_closed_kinematic_chain_sheaf_hodge_wrench_and_se3_wilson_consensus(self) -> None:
        fleet = MultiRobotFleetManifold(num_robots=2)
        sheaf = ClosedKinematicChainSheaf(fleet)
        q0 = np.array(
            [0.15, -0.55, 0.75, 0.0, 0.45, 0.0, -0.15, -0.55, 0.75, 0.0, 0.45, 0.0],
            dtype=float,
        )

        # Cycle 0 uncalibrated wrench with internal squeeze shear > 15 N
        w_c0 = sheaf.compute_gravity_compensation_wrench(q0, parasitic_internal_squeeze_n=42.8)
        drift_c0 = np.array(
            [np.radians(14.25), 0.0, 0.0, 0.0184, 0.0, 0.0],
            dtype=float,
        )
        decomp_c0 = sheaf.decompose_grasp_wrench(w_c0, q_fleet=q0)
        self.assertGreater(decomp_c0["internal_squeeze_wrench_n"], 15.0)
        self.assertLess(decomp_c0["orthogonality_residual"], 1e-7)

        _, coboundary_c0, beta1_c0 = sheaf.compute_closed_chain_coboundary(
            q0, w_c0, relative_base_drift_se3=drift_c0
        )
        self.assertEqual(beta1_c0, 1)
        self.assertGreater(coboundary_c0, 1.0)

        # Decentralized SE(3) Wilson loop consensus (GPS/MoCap-free)
        cal_res = sheaf.calibrate_decentralized_se3_holonomy(
            q_fleet=q0,
            w_applied=w_c0,
            relative_base_drift_se3=drift_c0,
            consensus_steps=12,
            step_size=0.38,
        )
        self.assertFalse(cal_res["wilson_after"]["gps_or_mocap_required"])
        self.assertEqual(cal_res["effective_beta_1_after"], 0)
        self.assertLessEqual(cal_res["wilson_after"]["se3_rotational_holonomy_deg"], 3.0)
        self.assertLessEqual(cal_res["wilson_after"]["se3_translational_holonomy_mm"], 5.0)
        self.assertLessEqual(cal_res["wrench_after"]["internal_squeeze_wrench_n"], 15.0)
        self.assertEqual(len(cal_res["holonomy_trace_deg"]), 12)
        self.assertLess(cal_res["holonomy_trace_deg"][-1], cal_res["holonomy_trace_deg"][0])

        # Edge case 1: Zero drift & zero internal squeeze remain exact 0.0 (never amplified to sensor floor)
        w_zero_squeeze = sheaf.compute_gravity_compensation_wrench(
            q0, parasitic_internal_squeeze_n=0.0
        )
        cal_zero = sheaf.calibrate_decentralized_se3_holonomy(
            q_fleet=q0,
            w_applied=w_zero_squeeze,
            relative_base_drift_se3=np.zeros(6, dtype=float),
            consensus_steps=12,
            step_size=0.38,
        )
        self.assertAlmostEqual(
            cal_zero["wilson_after"]["se3_rotational_holonomy_deg"], 0.0, places=9
        )
        self.assertAlmostEqual(
            cal_zero["wilson_after"]["se3_translational_holonomy_mm"], 0.0, places=9
        )
        self.assertAlmostEqual(
            cal_zero["wrench_after"]["internal_squeeze_wrench_n"], 0.0, places=9
        )
        self.assertEqual(cal_zero["effective_beta_1_after"], 0)

        # Edge case 2: Small initial drift (< sensor floor) strictly contracts and never increases
        w_tiny = sheaf.compute_gravity_compensation_wrench(q0, parasitic_internal_squeeze_n=0.10)
        drift_tiny = np.array([np.radians(0.05), 0.0, 0.0, 0.0001, 0.0, 0.0], dtype=float)
        cal_tiny = sheaf.calibrate_decentralized_se3_holonomy(
            q_fleet=q0,
            w_applied=w_tiny,
            relative_base_drift_se3=drift_tiny,
            consensus_steps=4,
            step_size=0.25,
        )
        self.assertLess(cal_tiny["wilson_after"]["se3_rotational_holonomy_deg"], 0.05)
        self.assertLess(cal_tiny["wilson_after"]["se3_translational_holonomy_mm"], 0.10)
        self.assertLess(cal_tiny["wrench_after"]["internal_squeeze_wrench_n"], 0.10)

        # Edge case 3: Insufficient consensus steps (1 step with small step_size) fails safety gate
        cal_weak = sheaf.calibrate_decentralized_se3_holonomy(
            q_fleet=q0,
            w_applied=w_c0,
            relative_base_drift_se3=drift_c0,
            consensus_steps=1,
            step_size=0.10,
            damping_gain=0.10,
        )
        self.assertGreater(cal_weak["wilson_after"]["se3_rotational_holonomy_deg"], 3.0)
        self.assertGreater(cal_weak["wrench_after"]["internal_squeeze_wrench_n"], 15.0)
        self.assertEqual(cal_weak["effective_beta_1_after"], 1)

    def test_multi_arm_3_and_4_robot_fleet_scaling(self) -> None:
        for m_arms in (3, 4):
            fleet_m = MultiRobotFleetManifold(
                num_robots=m_arms,
                payload_spec=SharedPayloadSpec(payload_id=f"payload_{m_arms}arm", mass_kg=30.0),
            )
            self.assertEqual(fleet_m.total_dof, 6 * m_arms)
            q_m = np.zeros(6 * m_arms, dtype=float)
            g_m = fleet_m.compute_fleet_metric(q_m)
            self.assertEqual(g_m.shape, (6 * m_arms, 6 * m_arms))
            self.assertTrue(np.all(np.linalg.eigvalsh(g_m) > 0.0))

            sheaf_m = ClosedKinematicChainSheaf(fleet_m)
            G_grasp = sheaf_m.compute_grasp_matrix(q_m)
            self.assertEqual(G_grasp.shape, (6, 6 * m_arms))
            wilson_m = sheaf_m.evaluate_se3_wilson_loop(
                q_m, relative_base_drift_se3=np.array([0.0, 0.0, np.radians(2.0), 0.002, 0.0, 0.0])
            )
            self.assertEqual(wilson_m["loop_count"], m_arms - 1)
            self.assertAlmostEqual(wilson_m["se3_rotational_holonomy_deg"], 2.0, places=4)
            self.assertAlmostEqual(wilson_m["se3_translational_holonomy_mm"], 2.0, places=4)

        orch3 = MultiRobotSwarmCohomologyOrchestrator(num_robots=3, payload_mass_kg=30.0)
        ep3 = orch3.run_episode(
            study_name="Frontier_P_TriArm_30kg_Test",
            experiment_id="exp_20261022_triarm_30kg",
            trial_count=3,
        )
        self.assertEqual(ep3.num_robots, 3)
        self.assertEqual(ep3.payload_mass_kg, 30.0)
        self.assertEqual(ep3.cycle0_audit.policy_status, "QUARANTINE")
        self.assertEqual(ep3.cycle1_audit.policy_status, "ELIGIBLE")
        self.assertEqual(
            ep3.frontier_p_verification["fleet_kinematics_and_payload"]["total_dof"], 18
        )

    def test_estop_safety_arbiter_sub_200us_and_bimanual_controller(self) -> None:
        fleet = MultiRobotFleetManifold(num_robots=2)
        sheaf = ClosedKinematicChainSheaf(fleet)
        arbiter = SwarmCohomologySafetyArbiter(sheaf)
        controller = BimanualCooperativeController(fleet=fleet, sheaf=sheaf, arbiter=arbiter)
        q_start = np.array(
            [0.15, -0.55, 0.75, 0.0, 0.45, 0.0, -0.15, -0.55, 0.75, 0.0, 0.45, 0.0],
            dtype=float,
        )
        q_goal = np.array(
            [0.32, -0.42, 0.68, 0.05, 0.38, -0.05, -0.32, -0.42, 0.68, -0.05, 0.38, 0.05],
            dtype=float,
        )

        w_c0 = sheaf.compute_gravity_compensation_wrench(q_start, parasitic_internal_squeeze_n=42.8)
        drift_c0 = np.array([np.radians(14.25), 0.0, 0.0, 0.0184, 0.0, 0.0], dtype=float)

        # Cycle 0 uncalibrated trajectory triggers E-Stop
        traj_c0 = controller.execute_cooperative_trajectory(
            q_start=q_start,
            q_goal=q_goal,
            w_applied=w_c0,
            relative_base_drift_se3=drift_c0,
        )
        self.assertFalse(traj_c0.trajectory_completed)
        self.assertTrue(traj_c0.final_audit.emergency_stop_triggered)
        self.assertEqual(traj_c0.final_audit.effective_beta_1, 1)
        self.assertLessEqual(traj_c0.mean_estop_arbiter_latency_us, 200.0)

        # Cycle 1 calibrated trajectory completes without E-Stop
        cal = sheaf.calibrate_decentralized_se3_holonomy(
            q_fleet=q_start,
            w_applied=w_c0,
            relative_base_drift_se3=drift_c0,
        )
        traj_c1 = controller.execute_cooperative_trajectory(
            q_start=q_start,
            q_goal=q_goal,
            w_applied=cal["calibrated_wrench"],
            relative_base_drift_se3=cal["calibrated_drift_se3"],
        )
        self.assertTrue(traj_c1.trajectory_completed)
        self.assertFalse(traj_c1.final_audit.emergency_stop_triggered)
        self.assertEqual(traj_c1.final_audit.effective_beta_1, 0)
        self.assertLessEqual(traj_c1.final_audit.internal_squeeze_wrench_n, 15.0)
        self.assertLessEqual(traj_c1.final_audit.se3_rotational_holonomy_deg, 3.0)
        self.assertLessEqual(traj_c1.mean_estop_arbiter_latency_us, 200.0)

        # Edge case: clearance breach triggers immediate E-Stop
        collision_audit = arbiter.audit_closed_chain_step(
            q_fleet=q_start,
            w_applied=cal["calibrated_wrench"],
            relative_base_drift_se3=cal["calibrated_drift_se3"],
            precomputed_clearances=(0.01, 0.4),
            precomputed_metric_cond=12.0,
        )
        self.assertTrue(collision_audit.emergency_stop_triggered)
        self.assertFalse(collision_audit.is_safe)

    def test_sol_edge_swarm_cohomology_gate_replay_parity(self) -> None:
        fleet = MultiRobotFleetManifold(num_robots=2)
        sheaf = ClosedKinematicChainSheaf(fleet)
        arbiter = SwarmCohomologySafetyArbiter(sheaf)
        controller = BimanualCooperativeController(fleet=fleet, sheaf=sheaf, arbiter=arbiter)
        q_start = np.array(
            [0.15, -0.55, 0.75, 0.0, 0.45, 0.0, -0.15, -0.55, 0.75, 0.0, 0.45, 0.0],
            dtype=float,
        )
        q_goal = np.array(
            [0.32, -0.42, 0.68, 0.05, 0.38, -0.05, -0.32, -0.42, 0.68, -0.05, 0.38, 0.05],
            dtype=float,
        )
        w_c0 = sheaf.compute_gravity_compensation_wrench(q_start, parasitic_internal_squeeze_n=42.8)
        drift_c0 = np.array([np.radians(14.25), 0.0, 0.0, 0.0184, 0.0, 0.0], dtype=float)
        cal = sheaf.calibrate_decentralized_se3_holonomy(
            q_fleet=q_start,
            w_applied=w_c0,
            relative_base_drift_se3=drift_c0,
        )

        traj_c0 = controller.execute_cooperative_trajectory(
            q_start, q_goal, w_c0, drift_c0
        )
        traj_c1 = controller.execute_cooperative_trajectory(
            q_start, q_goal, cal["calibrated_wrench"], cal["calibrated_drift_se3"]
        )

        gate = SolEdgeSwarmCohomologyGate()
        audit_c0 = gate.evaluate_swarm_cycle(
            cycle_index=0,
            run_id="run:test-swarm-gate",
            option_id="opt_bimanual:c0",
            trajectory_report=traj_c0,
            occurred_at="2026-10-22T15:00:00+00:00",
        )
        self.assertTrue(audit_c0.is_quarantined)
        self.assertEqual(audit_c0.policy_status, "QUARANTINE")
        self.assertTrue(audit_c0.chain_verified)
        self.assertEqual(len(audit_c0.runtime_events), 4)

        audit_c1 = gate.evaluate_swarm_cycle(
            cycle_index=1,
            run_id="run:test-swarm-gate",
            option_id="opt_bimanual:c1",
            trajectory_report=traj_c1,
            occurred_at="2026-10-22T15:00:05+00:00",
        )
        self.assertFalse(audit_c1.is_quarantined)
        self.assertEqual(audit_c1.policy_status, "ELIGIBLE")
        self.assertTrue(audit_c1.chain_verified)
        self.assertEqual(len(audit_c1.runtime_events), 4)

    def test_end_to_end_orchestrator_governance_ledger_and_observatory_assessment(self) -> None:
        orch = MultiRobotSwarmCohomologyOrchestrator()
        sample_pkt = self.root / "sample_swarm_packet.json"
        ep = orch.run_swarm_cohomology_episode(
            study_name="Frontier_P_Bimanual_25kg_Test",
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
        self.assertTrue(ep.frontier_p_verification["swarm_cohomology_verified"])

        exp_dir = Path(ep.handoff_manifest.experiment_dir)
        validate_run(json.loads((exp_dir / "baseline.json").read_text(encoding="utf-8")))
        validate_run(json.loads((exp_dir / "candidate.json").read_text(encoding="utf-8")))
        validate_archive(json.loads((exp_dir / "experiment.json").read_text(encoding="utf-8")))

        ledger = GovernanceCourtLedger(db_path=str(self.ledger_db))
        try:
            rec = ledger.record_swarm_cohomology_episode(ep)
            self.assertEqual(rec["policy_status"], "eligible")
            self.assertTrue(rec["frontier_p_verified"])
            integrity = ledger.verify_ledger_integrity()
            self.assertTrue(integrity.is_valid)
            self.assertEqual(integrity.total_runs_verified, 1)
            self.assertEqual(integrity.total_events_verified, 8)

            assessment = assess_continuum_observatory(exp_dir, ledger_db=self.ledger_db)
            self.assertEqual(assessment["comparability"], "compatible")
            self.assertEqual(assessment["outcome"], "improved")
            self.assertTrue(assessment["runtime_replay_verification"]["verified"])
            fp_sum = assessment["cycle_drift_breakdown"]["frontier_verification_summary"][
                "frontier_p"
            ]
            self.assertTrue(fp_sum["verified"])
            self.assertFalse(fp_sum["gps_or_mocap_required"])

            # Post-persistence SQLite tamper check 1: gps_or_mocap_required = True
            bad_pkt = json.loads(json.dumps(ep.proof_packet))
            bad_pkt["frontier_p_verification"]["decentralized_se3_holonomy"][
                "gps_or_mocap_required"
            ] = True
            ledger._conn.execute(
                "UPDATE governance_court_runs SET proof_packet_json = ? WHERE run_id = ?",
                (json.dumps(bad_pkt), rec["run_id"]),
            )
            ledger._conn.commit()
            tampered_integrity = ledger.verify_ledger_integrity()
            self.assertFalse(tampered_integrity.is_valid)
            self.assertIn(rec["run_id"], tampered_integrity.broken_run_ids)

            # Post-persistence SQLite tamper check 2: frontier_p_summary_digest mismatch
            bad_digest_pkt = json.loads(json.dumps(ep.proof_packet))
            bad_digest_pkt["frontier_p_verification"]["frontier_p_summary_digest"] = (
                "sha256:0000000000000000000000000000000000000000000000000000000000000000"
            )
            ledger._conn.execute(
                "UPDATE governance_court_runs SET proof_packet_json = ? WHERE run_id = ?",
                (json.dumps(bad_digest_pkt), rec["run_id"]),
            )
            ledger._conn.commit()
            self.assertFalse(ledger.verify_ledger_integrity().is_valid)

            # Post-persistence SQLite tamper check 3: cycle0_estop_triggered = False
            bad_c0_estop_pkt = json.loads(json.dumps(ep.proof_packet))
            bad_c0_estop_pkt["frontier_p_verification"]["estop_safety_arbiter"][
                "cycle0_estop_triggered"
            ] = False
            ledger._conn.execute(
                "UPDATE governance_court_runs SET proof_packet_json = ? WHERE run_id = ?",
                (json.dumps(bad_c0_estop_pkt), rec["run_id"]),
            )
            ledger._conn.commit()
            self.assertFalse(ledger.verify_ledger_integrity().is_valid)
        finally:
            ledger.close()

        # Boundary checks on MultiRobotSwarmCohomologyOrchestrator
        with self.assertRaises(ValueError):
            MultiRobotSwarmCohomologyOrchestrator(num_robots=1)
        with self.assertRaises(ValueError):
            MultiRobotSwarmCohomologyOrchestrator(payload_mass_kg=20.0)

        # Fail-closed tamper check on GovernanceCourtLedger.record_swarm_cohomology_episode
        tampered_ep = json.loads(json.dumps(ep.to_dict()))
        tampered_ep["frontier_p_verification"]["estop_safety_arbiter"]["estop_latency_us"] = 250.0
        ledger2 = GovernanceCourtLedger(db_path=str(self.root / "tampered.sqlite3"))
        try:
            with self.assertRaises(ValueError):
                ledger2.record_swarm_cohomology_episode(tampered_ep)
        finally:
            ledger2.close()

    def test_cli_swarm_cohomology_subcommand(self) -> None:
        pkt_out = self.root / "cli_swarm_pkt.json"
        json_out = self.root / "cli_swarm_summary.json"
        rc = sol_decide_cli_main(
            [
                "swarm-cohomology",
                "--study-name",
                "CLI_Swarm_Cohomology_Test",
                "--experiments-root",
                str(self.experiments_root / "cli_runs"),
                "--sample-packet-out",
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
        self.assertTrue(summary["frontier_p_verified"])
        self.assertEqual(summary["comparability"], "compatible")
        self.assertEqual(summary["outcome"], "improved")

    def test_gemini_client_interactions_api_and_ledger_sync(self) -> None:
        class _FakeContentItem:
            def __init__(self, item_type: str, text: str = "", signature: str = "", summary: object = None) -> None:
                self.type = item_type
                self.text = text
                self.signature = signature
                self.summary = summary

        class _FakeUsage:
            total_input_tokens = 811
            total_thought_tokens = 1120
            total_output_tokens = 255

        class _FakeInteraction:
            id = "v1_mock_swarm_cohomology_interaction_01"
            usage = _FakeUsage()
            outputs = [
                _FakeContentItem(
                    item_type="thought",
                    signature="mock_cryptographic_thought_signature_bytes_frontier_p",
                    summary=["Synthesizing decentralized SE(3) Wilson loop consensus and nullspace wrench calibration."],
                ),
                _FakeContentItem(
                    item_type="text",
                    text="```json\n"
                    + json.dumps(
                        {
                            "calibration_id": "MOCK-FRONTIER-P-CAL-01",
                            "se3_consensus_iterations": 12,
                            "se3_consensus_step_size": 0.36,
                            "grasp_nullspace_damping_gain": 0.991,
                            "inter_arm_repulsion_gain": 1.35,
                            "cohomological_rationale": "Decentralized SE(3) Lie algebra consensus damps rotational holonomy and nullspace squeeze.",
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

        orch = MultiRobotSwarmCohomologyOrchestrator(gemini_client=_FakeGeminiClient())
        ep = orch.run_swarm_cohomology_episode(
            study_name="Frontier_P_Mock_Live_Interactions_Test",
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
            "v1_mock_swarm_cohomology_interaction_01",
        )
        self.assertEqual(len(ep.reasoning_telemetry.thought_signature_digests), 1)
        self.assertTrue(
            ep.reasoning_telemetry.thought_signature_digests[0].startswith("sha256:")
        )
        self.assertEqual(ep.reasoning_telemetry.total_input_tokens, 811)
        self.assertEqual(ep.reasoning_telemetry.total_thought_tokens, 1120)
        self.assertEqual(ep.reasoning_telemetry.total_output_tokens, 255)
        self.assertEqual(
            ep.reasoning_telemetry.calibration_spec["calibration_id"],
            "MOCK-FRONTIER-P-CAL-01",
        )
        self.assertAlmostEqual(
            ep.reasoning_telemetry.calibration_spec["se3_consensus_step_size"],
            0.36,
            places=4,
        )
        self.assertAlmostEqual(
            ep.reasoning_telemetry.calibration_spec["grasp_nullspace_damping_gain"],
            0.991,
            places=4,
        )
        self.assertAlmostEqual(
            ep.reasoning_telemetry.calibration_spec["inter_arm_repulsion_gain"],
            1.35,
            places=4,
        )

        # Verify ledger_run_id matches interaction_id across Cycle 0/1 RuntimeEvents & GovernanceCourtLedger
        ledger_live = GovernanceCourtLedger(db_path=str(self.root / "mock_live_ledger.sqlite3"))
        try:
            rec = ledger_live.record_swarm_cohomology_episode(ep)
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
            id = "v1_mock_swarm_cohomology_trunc_99"
            usage = _FakeUsage()
            outputs = [
                _FakeContentItem(
                    item_type="thought",
                    signature="mock_sig_swarm_trunc_99",
                    summary=["Partial thought summary."],
                ),
                _FakeContentItem(item_type="text", text='{"calibration_id": "TRUNC'),
            ]

        class _FakeTruncatedClient:
            class interactions:
                @staticmethod
                def create(**kwargs: object) -> _FakeTruncatedInteraction:
                    return _FakeTruncatedInteraction()

        orch_trunc = MultiRobotSwarmCohomologyOrchestrator(gemini_client=_FakeTruncatedClient())
        ep_trunc = orch_trunc.run_swarm_cohomology_episode(
            study_name="Frontier_P_Mock_Truncated_Test",
            experiments_root=self.experiments_root / "mock_trunc",
            observatory_db_path=self.root / "mock_trunc_obs.sqlite3",
            register_in_observatory_db=False,
        )
        self.assertEqual(ep_trunc.interaction_id, "v1_mock_swarm_cohomology_trunc_99")
        self.assertEqual(len(ep_trunc.reasoning_telemetry.thought_signature_digests), 1)


if __name__ == "__main__":
    unittest.main()
