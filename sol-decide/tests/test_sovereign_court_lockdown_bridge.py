"""
Unit and integration tests for Frontier Z (Vector 29):
Sovereign Court Promotion, Final Gate Registry, System Lockdown & Production Gateway Observatory Bridge.
"""

from __future__ import annotations

from pathlib import Path

from sol_decide.delivery.governance_ledger import GovernanceCourtLedger
from sol_decide.interop.sol_change_producer import (
    export_sovereign_court_lockdown_observatory_bundle,
    run_sovereign_court_lockdown_repeat_trial_suite,
)
from sol_decide.interop.sovereign_court_lockdown_bridge import (
    EXPECTED_DEFAULT_GRAPH_SHA256,
    SolEdgeSovereignLockdownGate,
    SovereignCourtLockdownOrchestrator,
    verify_default_graph_integrity,
)


def test_frontier_z_default_graph_integrity() -> None:
    res = verify_default_graph_integrity()
    assert res["verified"] is True
    assert res["sha256"] == EXPECTED_DEFAULT_GRAPH_SHA256


def test_frontier_z_orchestrator_end_to_end() -> None:
    orchestrator = SovereignCourtLockdownOrchestrator()
    payload = orchestrator.run_sovereign_court_lockdown_evaluation()

    assert payload["frontier"] == "Z"
    assert payload["vector"] == "V29"
    assert payload["allow_production_execution"] is False
    assert payload["authorized_claimed"] is False
    assert payload["decisions"] == []

    promo = payload["court_promotion_docket"]
    assert promo["level"] == 36
    assert promo["evidence_count"] >= 6
    assert promo["promotion_ready"] is True
    assert promo["production_docket_rejected"] is True

    fgr = payload["final_gate_registry"]
    assert fgr["total_gates"] == 11
    assert fgr["passed_count"] == 11
    assert fgr["failed_count"] == 0
    assert fgr["all_passed"] is True
    assert fgr["finalized_immutable"] is True

    gfl = payload["governance_freeze_and_lockdown"]
    assert gfl["governance_frozen"] is True
    assert gfl["governance_invariants_passed"] is True
    assert gfl["governance_tamper_detected"] is True
    assert gfl["system_locked"] is True
    assert gfl["system_lockdown_passed"] is True
    assert gfl["lockdown_tamper_detected"] is True

    fin = payload["finalization_docket"]
    assert fin["evidence_count"] == 10
    assert fin["valid"] is True
    assert fin["court_review_verdict"] == "promote_level50_candidate"

    rt = payload["sovereign_runtime_and_gateway"]
    assert rt["runtime_valid"] is True
    assert rt["allow_production_execution"] is False
    assert rt["shadow_finalization_command_success"] is True
    assert rt["production_command_blocked_and_held"] is True
    assert rt["gateway_policy_default_deny"] is True
    assert rt["gateway_shadow_decision"] == "shadow_only_approved"
    assert rt["gateway_production_mutation_decision"] == "deny"

    rangers = payload["ranger_observations"]
    assert rangers["verified_packet_count"] == 4

    gate = payload["edge_gate"]
    assert gate["policy_gate_passed"] is True
    assert gate["allow_production_execution"] is False
    assert gate["authorized_claimed"] is False


def test_frontier_z_edge_gate_fail_closed_on_violation() -> None:
    gate = SolEdgeSovereignLockdownGate()
    bad_eval = gate.evaluate_sovereign_lockdown_gate(
        final_gate_count=9,
        final_gates_all_passed=False,
        finalization_docket_evidence_count=7,
        finalization_docket_valid=False,
        governance_freeze_verified=False,
        system_lockdown_verified=False,
        production_gateway_default_deny=False,
        production_execution_blocked=False,
        ranger_packets_verified=2,
    )
    assert bad_eval["policy_gate_passed"] is False
    assert bad_eval["allow_production_execution"] is False
    assert bad_eval["authorized_claimed"] is False


def test_frontier_z_sol_change_producer_and_ledger(tmp_path: Path) -> None:
    orchestrator = SovereignCourtLockdownOrchestrator()
    payload = orchestrator.run_sovereign_court_lockdown_evaluation()

    suite = run_sovereign_court_lockdown_repeat_trial_suite(trial_count=3)
    assert suite["trial_group"]["trial_count"] == 3
    assert suite["trial_eval"]["comparability"] == "compatible"
    assert suite["trial_eval"]["outcome"] == "improved"

    handoff = export_sovereign_court_lockdown_observatory_bundle(
        study_name="test_fz_study",
        experiment_id="exp_fz_001",
        experiments_root=tmp_path / "experiments",
        observatory_db_path=tmp_path / "observatory.sqlite3",
        register_in_observatory_db=True,
    )
    assert handoff.comparability == "compatible"
    assert handoff.outcome == "improved"
    assert handoff.review_status == "awaiting_review"

    ledger = GovernanceCourtLedger(db_path=tmp_path / "ledger.sqlite3")
    try:
        entry = ledger.record_sovereign_court_lockdown_observatory_run(payload)
        assert entry["verified"] is True
        integrity = ledger.verify_ledger_integrity()
        assert integrity.is_valid is True
        assert integrity.total_runs_verified == 1

        # Tamper with a sub-pillar metric in proof_packet_json and verify fail-closed detection
        import json
        row = ledger._conn.execute("SELECT run_id, proof_packet_json FROM governance_court_runs LIMIT 1").fetchone()
        tampered_pkt = json.loads(row["proof_packet_json"])
        tampered_pkt["frontier_z_verification"]["final_gate_registry"]["passed_count"] = 10
        ledger._conn.execute(
            "UPDATE governance_court_runs SET proof_packet_json = ? WHERE run_id = ?",
            (json.dumps(tampered_pkt), row["run_id"]),
        )
        ledger._conn.commit()
        tampered_integrity = ledger.verify_ledger_integrity()
        assert tampered_integrity.is_valid is False
    finally:
        ledger.close()
