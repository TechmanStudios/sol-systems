"""
Unit and integration tests for Frontier X (Vector 27):
Entangled Multi-Manifold 2PC, Resonant Cadence Scheduling & Wavefront Synthesis Observatory Bridge.
"""

from __future__ import annotations

from pathlib import Path

from sol_decide.delivery.governance_ledger import GovernanceCourtLedger
from sol_decide.interop.entangled_cadence_wavefront_bridge import (
    EXPECTED_DEFAULT_GRAPH_SHA256,
    EntangledCadenceWavefrontOrchestrator,
    SolEdgeEntangledCadenceGate,
    verify_default_graph_integrity,
)
from sol_decide.interop.sol_change_producer import (
    export_entangled_cadence_observatory_bundle,
    run_entangled_cadence_repeat_trial_suite,
)


def test_frontier_x_default_graph_integrity() -> None:
    res = verify_default_graph_integrity()
    assert res["verified"] is True
    assert res["sha256"] == EXPECTED_DEFAULT_GRAPH_SHA256


def test_frontier_x_orchestrator_end_to_end() -> None:
    orchestrator = EntangledCadenceWavefrontOrchestrator()
    payload = orchestrator.run_entangled_cadence_evaluation()

    assert payload["frontier"] == "X"
    assert payload["vector"] == "V27"
    assert payload["allow_production_execution"] is False
    assert payload["authorized_claimed"] is False
    assert payload["decisions"] == []

    cad = payload["cadence_calibration"]
    assert cad["profile_count"] == 4
    assert cad["calibrated_count"] == 4
    assert cad["active_cadence_mutated"] is False

    res_sched = payload["resonant_schedule"]
    assert res_sched["schedule_valid"] is True
    assert res_sched["collision_count"] == 0
    assert res_sched["total_throughput_gain"] > 0.0

    ent = payload["entangled_commit"]
    assert ent["status"] == "committed_shadow"
    assert ent["phase_skew_rad"] < 0.05
    assert ent["active_tables_mutated"] is False
    assert ent["fault_abort_status"] == "aborted"
    assert ent["fault_rollback_performed"] is True

    msync = payload["manifold_sync"]
    assert msync["sync_valid"] is True
    assert msync["synced_manifolds"] == 3
    assert msync["drift_quarantine_triggered"] is True

    wf = payload["wavefront_synthesis"]
    assert wf["passed_32b_cases"] == 4
    assert wf["passed_64b_cases"] == 4
    assert wf["total_cases"] == 8

    rangers = payload["ranger_observations"]
    assert rangers["verified_packet_count"] == 4

    gate = payload["edge_gate"]
    assert gate["policy_gate_passed"] is True
    assert gate["allow_production_execution"] is False
    assert gate["authorized_claimed"] is False


def test_frontier_x_edge_gate_fail_closed_on_anomaly() -> None:
    gate = SolEdgeEntangledCadenceGate()
    bad_eval = gate.evaluate_entangled_cadence_gate(
        cadence_profiles_calibrated=2,  # < 4
        resonant_collision_count=3,     # > 0
        entangled_commit_status="aborted",
        phase_skew_rad=0.45,
        active_tables_mutated=True,
        manifold_sync_valid=False,
        wavefront_synthesis_passed=6,
        ranger_packets_verified=3,
    )
    assert bad_eval["policy_gate_passed"] is False
    assert bad_eval["allow_production_execution"] is False
    assert bad_eval["authorized_claimed"] is False


def test_frontier_x_sol_change_producer_and_ledger(tmp_path: Path) -> None:
    orchestrator = EntangledCadenceWavefrontOrchestrator()
    payload = orchestrator.run_entangled_cadence_evaluation()

    suite = run_entangled_cadence_repeat_trial_suite(trial_count=3)
    assert suite["trial_group"]["trial_count"] == 3
    assert suite["trial_eval"]["comparability"] == "compatible"
    assert suite["trial_eval"]["outcome"] == "improved"

    handoff = export_entangled_cadence_observatory_bundle(
        study_name="test_fx_study",
        experiment_id="exp_fx_001",
        experiments_root=tmp_path / "experiments",
        observatory_db_path=tmp_path / "observatory.sqlite3",
        register_in_observatory_db=True,
    )
    assert handoff.comparability == "compatible"
    assert handoff.outcome == "improved"
    assert handoff.review_status == "awaiting_review"

    ledger = GovernanceCourtLedger(db_path=tmp_path / "ledger.sqlite3")
    try:
        entry = ledger.record_entangled_cadence_observatory_run(payload)
        assert entry["verified"] is True
        integrity = ledger.verify_ledger_integrity()
        assert integrity.is_valid is True
        assert integrity.total_runs_verified == 1

        # Tamper with a sub-pillar metric in proof_packet_json and verify fail-closed detection
        import json
        row = ledger._conn.execute("SELECT run_id, proof_packet_json FROM governance_court_runs LIMIT 1").fetchone()
        tampered_pkt = json.loads(row["proof_packet_json"])
        tampered_pkt["frontier_x_verification"]["entangled_commit"]["phase_skew_rad"] = 0.25
        ledger._conn.execute(
            "UPDATE governance_court_runs SET proof_packet_json = ? WHERE run_id = ?",
            (json.dumps(tampered_pkt), row["run_id"]),
        )
        ledger._conn.commit()
        tampered_integrity = ledger.verify_ledger_integrity()
        assert tampered_integrity.is_valid is False
    finally:
        ledger.close()
