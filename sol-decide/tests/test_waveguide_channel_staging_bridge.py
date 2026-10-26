"""
Unit and integration tests for Frontier Y (Vector 28):
Waveguide Channel Optimization, Layout Compaction & Local Staging Observatory Bridge.
"""

from __future__ import annotations

from pathlib import Path

from sol_decide.delivery.governance_ledger import GovernanceCourtLedger
from sol_decide.interop.sol_change_producer import (
    export_waveguide_channel_staging_observatory_bundle,
    run_waveguide_channel_staging_repeat_trial_suite,
)
from sol_decide.interop.waveguide_channel_staging_bridge import (
    EXPECTED_DEFAULT_GRAPH_SHA256,
    SolEdgeWaveguideChannelGate,
    WaveguideChannelStagingOrchestrator,
    verify_default_graph_integrity,
)


def test_frontier_y_default_graph_integrity() -> None:
    res = verify_default_graph_integrity()
    assert res["verified"] is True
    assert res["sha256"] == EXPECTED_DEFAULT_GRAPH_SHA256


def test_frontier_y_orchestrator_end_to_end() -> None:
    orchestrator = WaveguideChannelStagingOrchestrator()
    payload = orchestrator.run_waveguide_channel_staging_evaluation()

    assert payload["frontier"] == "Y"
    assert payload["vector"] == "V28"
    assert payload["allow_production_execution"] is False
    assert payload["authorized_claimed"] is False
    assert payload["decisions"] == []

    ck = payload["channel_kernels"]
    assert ck["library_size"] == 5
    assert ck["library_valid"] is True
    assert ck["recognized_kernel_count"] == 5
    assert set(ck["recognized_kernel_names"]) == {
        "channel_parallel_load",
        "channel_fanout",
        "channel_fence_order",
        "channel_gather",
        "channel_route_chain",
    }

    dep = payload["channel_dependency"]
    assert dep["safe_batch_verified"] is True
    assert dep["raw_hazard_detected_on_conflict"] is True

    layout = payload["layout_optimization"]
    assert layout["crosstalk_reduction"] >= 0.0
    assert layout["efficiency_gain"] >= 0.0
    assert layout["crossings_reduced"] >= 0

    comp = payload["pipeline_compaction"]
    assert comp["compaction_equivalence_verified"] is True

    pkg = payload["package_dry_run_and_gate"]
    assert pkg["transcript_valid"] is True
    assert pkg["verified_noop_event_count"] == 182
    assert pkg["noop_boundary_verified"] is True
    assert pkg["physical_gate_valid"] is True
    assert pkg["physical_execution_permitted_by_gate"] is False

    staging = payload["controlled_local_staging"]
    assert staging["staging_plan_valid"] is True
    assert staging["blocked_unapproved_status"] == "package_local_staging_run_blocked"
    assert staging["staging_run_status"] == "package_local_staging_run_completed"
    assert staging["staging_record_valid"] is True
    assert staging["copied_file_count"] == 28
    assert staging["all_digests_matched"] is True
    assert staging["zero_archive_upload_deploy_mutation"] is True

    gate = payload["edge_gate"]
    assert gate["policy_gate_passed"] is True
    assert gate["allow_production_execution"] is False
    assert gate["authorized_claimed"] is False


def test_frontier_y_edge_gate_fail_closed_on_violation() -> None:
    gate = SolEdgeWaveguideChannelGate()
    bad_eval = gate.evaluate_waveguide_channel_gate(
        channel_kernels_recognized=3,
        channel_batch_safety_verified=False,
        crosstalk_reduction=-0.1,
        layout_efficiency_gain=-0.05,
        compaction_equivalence_verified=False,
        noop_dry_run_verified_events=100,
        physical_execution_permitted_by_gate=True,  # forbidden!
        local_staging_copied_files=12,
        local_staging_all_digests_matched=False,
        zero_archive_upload_deploy_mutation=False,
    )
    assert bad_eval["policy_gate_passed"] is False
    assert bad_eval["allow_production_execution"] is False
    assert bad_eval["authorized_claimed"] is False


def test_frontier_y_sol_change_producer_and_ledger(tmp_path: Path) -> None:
    orchestrator = WaveguideChannelStagingOrchestrator()
    payload = orchestrator.run_waveguide_channel_staging_evaluation()

    suite = run_waveguide_channel_staging_repeat_trial_suite(trial_count=3)
    assert suite["trial_group"]["trial_count"] == 3
    assert suite["trial_eval"]["comparability"] == "compatible"
    assert suite["trial_eval"]["outcome"] == "improved"

    handoff = export_waveguide_channel_staging_observatory_bundle(
        study_name="test_fy_study",
        experiment_id="exp_fy_001",
        experiments_root=tmp_path / "experiments",
        observatory_db_path=tmp_path / "observatory.sqlite3",
        register_in_observatory_db=True,
    )
    assert handoff.comparability == "compatible"
    assert handoff.outcome == "improved"
    assert handoff.review_status == "awaiting_review"

    ledger = GovernanceCourtLedger(db_path=tmp_path / "ledger.sqlite3")
    try:
        entry = ledger.record_waveguide_channel_staging_observatory_run(payload)
        assert entry["verified"] is True
        integrity = ledger.verify_ledger_integrity()
        assert integrity.is_valid is True
        assert integrity.total_runs_verified == 1

        # Tamper with a sub-pillar metric in proof_packet_json and verify fail-closed detection
        import json
        row = ledger._conn.execute("SELECT run_id, proof_packet_json FROM governance_court_runs LIMIT 1").fetchone()
        tampered_pkt = json.loads(row["proof_packet_json"])
        tampered_pkt["frontier_y_verification"]["package_dry_run_and_gate"]["physical_execution_permitted_by_gate"] = True
        ledger._conn.execute(
            "UPDATE governance_court_runs SET proof_packet_json = ? WHERE run_id = ?",
            (json.dumps(tampered_pkt), row["run_id"]),
        )
        ledger._conn.commit()
        tampered_integrity = ledger.verify_ledger_integrity()
        assert tampered_integrity.is_valid is False
    finally:
        ledger.close()
