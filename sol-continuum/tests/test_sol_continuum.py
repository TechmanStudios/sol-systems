"""
Unit tests for `c:\\sol-systems\\sol-continuum` (`sol_continuum` package) and its
zero-warning integration with the SOL Change Observatory (`c:\\sol-systems\\sol-change`).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

_SOL_CONTINUUM_ROOT = Path(__file__).resolve().parents[1]
_SOL_SYSTEMS_ROOT = _SOL_CONTINUUM_ROOT.parent
_SOL_CHANGE_ROOT = _SOL_SYSTEMS_ROOT / "sol-change"

for _p in (
    _SOL_CONTINUUM_ROOT,
    _SOL_SYSTEMS_ROOT,
    _SOL_CHANGE_ROOT,
    _SOL_SYSTEMS_ROOT / "sol-decide",
    _SOL_SYSTEMS_ROOT / "sol-edge" / "src",
    _SOL_SYSTEMS_ROOT / "conJecture",
):
    _ps = str(_p)
    if _p.exists() and _ps not in sys.path:
        sys.path.insert(0, _ps)

from observatory.domain import compare as observatory_compare, validate_archive, validate_run
from observatory.store import Store as ObservatoryStore

from sol_continuum import (
    COMMAND_PROTOCOL_VERBS,
    SKILL_DIMENSIONS,
    ChangeObservatoryBridge,
    CircuitToWideWordLoweringAdapter,
    ContinuumAgentGuild,
    ContinuumDiscoveryProposalSpec,
    LuminaLibraryObservatoryOrchestrator,
    LuminaRangerObservatoryProposalSpec,
    SolContinuumDiscoveryOrchestrator,
    SolEdgeContinuumDiscoveryGate,
    SolEdgeLuminaSovereignGate,
)
from sol_decide.delivery.governance_ledger import GovernanceCourtLedger


def test_sol_continuum_guild_gate_and_change_observatory_archive() -> None:
    with tempfile.TemporaryDirectory(prefix="sol-continuum-test-") as tmp:
        tmp_path = Path(tmp)
        exp_root = tmp_path / "experiments"
        obs_db = tmp_path / "observatory.sqlite3"
        ledger_db = tmp_path / "governance_ledger.sqlite3"

        bridge = ChangeObservatoryBridge(
            experiments_root=exp_root,
            observatory_db_path=obs_db,
        )
        orchestrator = SolContinuumDiscoveryOrchestrator(
            observatory_bridge=bridge,
        )

        record = orchestrator.run_continuum_discovery_episode(
            study_name="SolContinuum_Autonomous_Guild_Discovery_v1",
            gemini_client=None,
            model="gemini-4-argon",
            register_in_observatory_db=True,
        )

        # 1. Verify 5-agent guild & curriculum evolution
        assert len(record.guild_agents) == 5
        assert len(SKILL_DIMENSIONS) == 5
        assert record.post_mean_guild_competency > record.pre_mean_guild_competency
        assert record.epistemic_gain_bits >= 1.25
        assert record.conjecture_engine_status == "PROVED_THEOREM"
        assert record.wgsl_shader_hash.startswith("sha256:")

        # 1b. Verify Frontier K real theorem proving, circuit synthesis, debate, WGSL, and benchmark artifacts
        assert record.cycle0_proof_certificate["verdict"] == "DISPROVED_COUNTEREXAMPLE"
        assert record.formal_proof_certificate["verdict"] == "PROVED_THEOREM"
        assert record.synthesized_circuit_summary["verified"] is True
        assert record.synthesized_circuit_summary["accuracy"] == 1.0
        assert record.metaplasticity_report["is_healed"] is True
        assert record.metaplasticity_report["repaired_max_cond"] <= 100.0
        assert record.symbolic_reflection_report["is_equivalent"] is True
        assert bool(record.symbolic_reflection_report["algebraic_summary"])
        assert "session_id" in record.dialectical_debate_certificate
        assert record.wgsl_hardware_proof_report["verdict"] == "PROVED_THEOREM"
        assert (
            record.wgsl_hardware_proof_report["states_verified"]
            == record.wgsl_hardware_proof_report["total_states"]
        )
        assert record.wgsl_sheaf_diffusion_report["energy_reduction_ratio"] > 0.5
        assert record.wgsl_shader_validation["is_valid"] is True
        assert record.wgsl_shader_validation["validation_errors"] == []
        assert record.circuit_cache_entry["is_cached"] is True
        assert record.circuit_cache_entry["total_cached_circuits"] >= 1
        assert record.causal_emergence_report["is_emergent"] is True
        assert record.causal_emergence_report["delta_ei"] > 0.0
        assert len(record.benchmark_evaluation_report["aggregate"]) >= 3

        # 2. Verify Cycle 0 QUARANTINE -> Cycle 1 ELIGIBLE zero-trust gate & 4-event sol-edge streams
        assert record.cycle0_audit.is_quarantined is True
        assert record.cycle0_audit.policy_status == "QUARANTINE"
        assert record.cycle0_audit.governance_reason == "UNPROVED_CONJECTURE_OR_CURRICULUM_DRIFT"
        assert len(record.cycle0_audit.events) == 4
        assert record.cycle1_audit.is_quarantined is False
        assert record.cycle1_audit.policy_status == "ELIGIBLE"
        assert record.cycle1_audit.governance_reason == "CONTINUUM_DISCOVERY_PROVED_AND_VERIFIED"
        assert record.cycle1_audit.cohomological_event == "COHOMOLOGICAL_QUARANTINE_CLEARED"
        assert len(record.cycle1_audit.events) == 4

        # 3. Verify SOL Change Observatory integration & zero missing-context warnings
        assert record.observatory_comparability == "compatible"
        assert record.observatory_outcome == "improved"
        assert record.observatory_review_status == "awaiting_review"
        assert record.observatory_warnings == []
        assert record.observatory_db_registered is True

        bundle_dir = Path(record.experiment_bundle_dir)
        assert (bundle_dir / "baseline.json").is_file()
        assert (bundle_dir / "candidate.json").is_file()
        assert (bundle_dir / "experiment.json").is_file()
        assert (bundle_dir / "comparison.md").is_file()
        assert (bundle_dir / "candidate_proof_packet.json").is_file()

        # Validate saved files directly with sol-change domain validators
        base_run = json.loads((bundle_dir / "baseline.json").read_text(encoding="utf-8"))
        cand_run = json.loads((bundle_dir / "candidate.json").read_text(encoding="utf-8"))
        exp_doc = json.loads((bundle_dir / "experiment.json").read_text(encoding="utf-8"))
        validate_run(base_run)
        validate_run(cand_run)
        validate_archive(exp_doc)
        assert exp_doc["review_status"] == "awaiting_review"
        assert exp_doc["decisions"] == []

        comp = observatory_compare(exp_doc)
        assert comp["comparability"] == "compatible"
        assert comp["warnings"] == []
        assert comp["counts"]["improved"] == 6
        assert comp["counts"]["regressed"] == 0

        # Verify experiment was persisted in sol-change SQLite Store
        store = ObservatoryStore(obs_db)
        stored_exp = store.get(record.experiment_id)
        assert stored_exp["id"] == record.experiment_id
        assert stored_exp["review_status"] == "awaiting_review"
        assert stored_exp["decisions"] == []

        # 4. Verify GovernanceCourtLedger hash-chained persistence (Frontier M: 8 events + thought signatures)
        ledger = GovernanceCourtLedger(db_path=str(ledger_db))
        entry = ledger.record_sol_continuum_episode(record)
        assert entry["run_mode"] == "sol_continuum_discovery_observatory"
        assert entry["experiment_id"] == record.experiment_id
        assert entry["edge_event_count"] == 8
        assert entry["thought_signature_count"] >= 1
        integrity = ledger.verify_ledger_integrity()
        assert integrity.is_valid is True
        assert integrity.total_runs_verified == 1
        assert integrity.total_events_verified == 8
        runs_list = ledger.list_runs()
        assert runs_list[0]["edgeEventCount"] == 8
        assert runs_list[0]["thoughtSignatureCount"] >= 1
        assert len(ledger.list_thought_signatures()) >= 1
        ledger.close()


def test_lumina_coding_library_and_ranger_corps_observatory_integration() -> None:
    """
    Frontier J/L/M Unit Test: Verifies that the Lumina Coding Library (`LuminaLibraryAgent`),
    Sovereign Domain (`SovereignDomain`, `PromotionCourt`), and 8-Ranger Lumina Squadron
    (`PhaseRanger`, `MassRanger`, `CourtRanger`, `FinalizationRanger`, `WideWordProgramRanger`,
    `MicroISARanger`, `FaultMatrixRanger`, `EntangledFeedbackRanger`) execute the 8-verb
    Command Protocol, lower synthesized circuits & Micro-ISA v1 ops to 32/64-bit WideWord VMs,
    verify 33-case pipeline/wavefront + 21-case relocation + 14-case calibration fault matrices,
    execute 3-manifold 2PC atomic commit & SovereignRuntime shadow execution, stage candidate
    components with `review_status == "awaiting_review"`, record Rule 7 `level_lessons.json` laws,
    and archive a zero-warning schema-1.0 experiment in the SOL Change Observatory.
    """
    with tempfile.TemporaryDirectory(prefix="sol-lumina-ranger-test-") as tmp:
        tmp_path = Path(tmp)
        exp_root = tmp_path / "experiments"
        obs_db = tmp_path / "observatory.sqlite3"
        ledger_db = tmp_path / "governance_ledger.sqlite3"

        bridge = ChangeObservatoryBridge(
            experiments_root=exp_root,
            observatory_db_path=obs_db,
        )
        orchestrator = LuminaLibraryObservatoryOrchestrator(
            observatory_bridge=bridge,
        )

        # Verify LuminaLibraryAgent SovereignDomain router contract (LuminaRangerCorps.md §11)
        court_route = json.loads(
            orchestrator.library_agent.ask_expert("court", "Query Level 12 gate", {"level": 12})
        )
        assert court_route["domain"] == "sol_sovereign"
        assert court_route["branch"] == "promotion_court"
        ranger_route = json.loads(
            orchestrator.library_agent.ask_expert("ranger_team", "Query Level 12 rangers", {"level": 12})
        )
        assert ranger_route["branch"] == "ranger_corps"
        for expected_ranger in (
            "phase_ranger",
            "mass_ranger",
            "court_ranger",
            "finalization_ranger",
            "wideword_program_ranger",
            "micro_isa_ranger",
            "fault_matrix_ranger",
            "entangled_feedback_ranger",
        ):
            assert expected_ranger in ranger_route["registered_rangers"]

        record = orchestrator.run_lumina_observatory_episode(
            study_name="Lumina_Ranger_Corps_Observatory_Sovereignty_v1",
            gemini_client=None,
            model="gemini-4-argon",
            register_in_observatory_db=True,
            persist_library_staging=False,
        )

        # 1. Verify 8-verb Command Protocol trace & RangerMission bounds
        verbs = tuple(step["verb"] for step in record.command_protocol_trace)
        assert verbs == COMMAND_PROTOCOL_VERBS
        assert "CHANGE_ENGINE_MATH" in record.ranger_mission["forbidden_actions"]
        assert "WRITE_SOURCE" in record.ranger_mission["forbidden_actions"]

        # 2. Verify SovereignPacket field evidence from all 8 Rangers & Frontier L hardware verification
        assert record.cycle0_phase_packet["recommendation"] == "reject"
        assert record.cycle1_phase_packet["recommendation"] == "observe"
        assert record.cycle1_phase_packet["evidence"]["active_delta"] >= 0.20
        assert record.cycle1_phase_packet["evidence"]["cross_talk"] <= 0.05
        assert record.cycle1_phase_packet["evidence"]["min_active_register_mass"] >= 14.0
        assert record.cycle1_court_packet["actor"] == "Court Ranger"
        assert record.cycle1_finalization_packet["actor"] == "Finalization Ranger"
        assert record.cycle1_finalization_packet["evidence"]["promotion_readiness"] is True

        # Frontier L: Verify WideWordProgramRanger, MicroISARanger, FaultMatrixRanger, EntangledFeedbackRanger
        assert record.cycle1_wideword_packet["actor"] == "WideWord Program Ranger"
        assert record.cycle1_wideword_packet["recommendation"] == "observe"
        assert record.cycle1_wideword_packet["evidence"]["oracle_match_status"] is True
        assert record.cycle1_micro_isa_packet["actor"] == "Micro-ISA Ranger"
        assert record.cycle1_micro_isa_packet["recommendation"] in ("observe", "promote")
        assert record.cycle0_fault_matrix_packet["actor"] == "Fault Matrix Ranger"
        assert record.cycle0_fault_matrix_packet["recommendation"] in ("observe", "promote")
        assert record.cycle1_entangled_feedback_packet["actor"] == "Entangled Feedback Ranger"
        assert record.cycle1_entangled_feedback_packet["recommendation"] in ("observe", "promote")

        # Frontier L: Verify 32-bit and 64-bit WideWord fabric, Micro-ISA v1 lowering, and VM oracle parity
        assert record.wideword_fabric_report["32bit"]["topology_valid"] is True
        assert record.wideword_fabric_report["32bit"]["lane_count"] == 4
        assert record.wideword_fabric_report["32bit"]["arithmetic_fabric_valid"] is True
        assert record.wideword_fabric_report["64bit"]["topology_valid"] is True
        assert record.wideword_fabric_report["64bit"]["lane_count"] == 8
        assert record.wideword_fabric_report["64bit"]["arithmetic_fabric_valid"] is True
        assert record.micro_isa_v1_lowering_report["32bit"]["successfully_lowered"] == 6
        assert record.micro_isa_v1_lowering_report["32bit"]["safety_checks_passed"] is True
        assert record.micro_isa_v1_lowering_report["64bit"]["successfully_lowered"] == 6
        assert record.micro_isa_v1_lowering_report["64bit"]["safety_checks_passed"] is True

        fl = record.frontier_l_verification
        assert fl["circuit_to_wideword_lowering"]["vm_executions"]["32bit"]["oracle_match"] is True
        assert fl["circuit_to_wideword_lowering"]["vm_executions"]["32bit"]["mismatch_count"] == 0
        assert fl["circuit_to_wideword_lowering"]["vm_executions"]["64bit"]["oracle_match"] is True
        assert fl["circuit_to_wideword_lowering"]["vm_executions"]["64bit"]["mismatch_count"] == 0
        assert fl["circuit_to_wideword_lowering"]["micro_isa_summary"]["v1_extension_compliant"] is True
        assert fl["circuit_to_wideword_lowering"]["micro_isa_summary"]["v1_opcode_count"] == 29

        # Frontier L: Verify 33-case pipeline/wavefront, 21-case relocation, 14-case calibration fault matrices & rollback
        assert record.fault_matrix_report["pipeline_wavefront_fault_matrix"]["total_cases"] == 33
        assert record.fault_matrix_report["pipeline_wavefront_fault_matrix"]["passed_cases"] == 33
        assert record.fault_matrix_report["state_relocation_fault_matrix"]["total_cases"] == 21
        assert record.fault_matrix_report["state_relocation_fault_matrix"]["passed_cases"] == 21
        assert record.fault_matrix_report["realtime_calibration_fault_matrix"]["total_cases"] == 14
        assert record.fault_matrix_report["realtime_calibration_fault_matrix"]["passed_cases"] == 14
        assert record.fault_matrix_report["rollback_proof"]["passed_proof"] is True
        assert record.fault_matrix_report["rollback_proof"]["all_restored"] is True

        # Frontier L: Verify 3-manifold 2PC atomic commit & SovereignRuntime shadow execution
        assert record.multimanifold_atomic_commit_report["coordination_group"] == ["M1", "M2", "M3"]
        assert record.multimanifold_atomic_commit_report["barrier_satisfied"] is True
        assert record.multimanifold_atomic_commit_report["commit_status"] == "commit"
        assert record.multimanifold_atomic_commit_report["commit_success"] is True
        assert record.multimanifold_atomic_commit_report["feedback_loop_stable"] is True
        assert record.multimanifold_atomic_commit_report["feedback_atomic_ready"] is True
        assert record.sovereign_runtime_report["mode"] == "shadow"
        assert record.sovereign_runtime_report["allow_production_execution"] is False
        assert record.sovereign_runtime_report["command_success"] is True
        assert record.sovereign_runtime_report["quarantined"] is False
        assert "frontier_l_verification" in record.sol_lens_packet

        # 3. Verify Cycle 0 QUARANTINE -> Cycle 1 ELIGIBLE under the 7 Sovereignty Rules
        assert record.cycle0_audit.is_quarantined is True
        assert record.cycle0_audit.policy_status == "QUARANTINE"
        assert record.cycle0_audit.governance_reason == "SOVEREIGN_RANGER_DRIFT_OR_MASS_QUARANTINE"
        assert len(record.cycle0_audit.events) == 4
        assert record.cycle1_audit.is_quarantined is False
        assert record.cycle1_audit.policy_status == "ELIGIBLE"
        assert record.cycle1_audit.governance_reason == "LUMINA_RANGER_SOVEREIGN_COURT_VERIFIED"
        assert record.cycle1_audit.sacred_physics_mutated is False
        assert abs(record.cycle1_audit.bounded_phase_nudge_rad) <= 0.05
        assert abs(record.cycle1_audit.bounded_damping_delta) <= 0.01
        assert len(record.cycle1_audit.events) == 4

        # 4. Verify Lumina Coding Library staging & Rule 7 Lesson Law
        assert len(record.library_verified_components) >= 5
        assert record.staged_component_record["verification_status"] == "AWAITING_OBSERVATORY_REVIEW"
        assert record.staged_component_record["review_status"] == "awaiting_review"
        assert record.staged_component_record["observatory_experiment_id"] == record.experiment_id
        assert record.lesson_law_record["observatory_experiment_id"] == record.experiment_id

        # 5. Verify SOL Change Observatory schema-1.0 archive & zero warnings
        assert record.observatory_comparability == "compatible"
        assert record.observatory_outcome == "improved"
        assert record.observatory_review_status == "awaiting_review"
        assert record.observatory_warnings == []
        assert record.observatory_db_registered is True

        bundle_dir = Path(record.experiment_bundle_dir)
        exp_doc = json.loads((bundle_dir / "experiment.json").read_text(encoding="utf-8"))
        validate_archive(exp_doc)
        assert exp_doc["review_status"] == "awaiting_review"
        assert exp_doc["decisions"] == []

        # 6. Verify GovernanceCourtLedger persistence (Frontier M: 8 events + thought signatures)
        ledger = GovernanceCourtLedger(db_path=str(ledger_db))
        entry = ledger.record_lumina_observatory_episode(record)
        assert entry["run_mode"] == "lumina_ranger_observatory_sovereignty"
        assert entry["experiment_id"] == record.experiment_id
        assert entry["edge_event_count"] == 8
        assert entry["thought_signature_count"] >= 1
        integrity = ledger.verify_ledger_integrity()
        assert integrity.is_valid is True
        assert integrity.total_runs_verified == 1
        assert integrity.total_events_verified == 8
        assert len(ledger.list_thought_signatures()) >= 1
        ledger.close()


def test_frontier_k_false_conjecture_refutation_and_gate_quarantine() -> None:
    """
    Frontier K Edge-Case Verification:
    Verifies that deliberately false conjectures in `AutonomousConjectureEngine` are
    refuted with explicit counterexample witnesses by both `AutomatedProofEngine` and
    `WGSLProofEngine`, and are quarantined by `SolEdgeContinuumDiscoveryGate`.
    """
    from Frontier_OS.core.hardware_accel import WGSLProofEngine, WGSLProofVerdict
    from Frontier_OS.core.theorem_proving import (
        AutomatedProofEngine,
        AutonomousConjectureEngine,
        FormalProofCertificate,
        ProofVerdict,
    )
    from sol_edge.runtime.replay import replay_events
    from sol_edge.runtime.state import RuntimeStatus

    conj_engine = AutonomousConjectureEngine()
    catalog = conj_engine.generate_conjecture_catalog(include_false_conjectures=True)
    false_conj = next(c for c in catalog if c.is_deliberately_false)

    prover = AutomatedProofEngine()
    cert = prover.prove_conjecture(false_conj, max_debate_rounds=5)
    assert isinstance(cert, FormalProofCertificate)
    assert cert.verdict == ProofVerdict.DISPROVED_COUNTEREXAMPLE
    assert cert.counterexample_witness is not None

    wgsl_prover = WGSLProofEngine()
    wgsl_rep = wgsl_prover.prove_conjecture_wgsl(false_conj)
    assert wgsl_rep.verdict == WGSLProofVerdict.DISPROVED_COUNTEREXAMPLE
    assert wgsl_rep.counter_examples_found >= 1
    assert wgsl_rep.witness_bits is not None

    gate = SolEdgeContinuumDiscoveryGate()
    audit = gate.evaluate_discovery_cycle(
        cycle_index=0,
        designation="baseline",
        workflow_version="sol-continuum/guild-v0.1-refuted",
        conjecture_status=cert.verdict.value,
        sheaf_coboundary_defect=0.0,
        epistemic_gain_bits=1.60,
        falsification_survival_rate=0.0,
        observatory_comparability="compatible",
    )
    assert audit.is_quarantined is True
    assert audit.policy_status == "QUARANTINE"
    assert len(audit.events) == 4
    replayed = replay_events(audit.events)
    assert replayed.status == RuntimeStatus.QUARANTINED
    assert replayed.state_digest == audit.state_digest


def test_frontier_m_cross_run_replay_and_tamper_detection() -> None:
    """
    Frontier M Edge-Case Verification:
    Verifies multi-run hash chaining across Continuum + Lumina episodes in
    `GovernanceCourtLedger`, `assess_continuum_observatory` cycle-level drift &
    `sol_edge.runtime.replay` verification, and immediate tamper detection when any
    persisted `sol_edge_runtime_events` row is mutated.
    """
    from observatory.continuum import assess_continuum_observatory

    with tempfile.TemporaryDirectory(prefix="sol-frontier-m-tamper-") as tmp:
        tmp_path = Path(tmp)
        exp_root = tmp_path / "experiments"
        obs_db = tmp_path / "observatory.sqlite3"
        ledger_db = tmp_path / "governance_ledger.sqlite3"

        bridge = ChangeObservatoryBridge(
            experiments_root=exp_root,
            observatory_db_path=obs_db,
        )
        cont_orch = SolContinuumDiscoveryOrchestrator(observatory_bridge=bridge)
        lum_orch = LuminaLibraryObservatoryOrchestrator(observatory_bridge=bridge)

        cont_rec = cont_orch.run_continuum_discovery_episode(
            study_name="SolContinuum_Autonomous_Guild_Discovery_v1",
            gemini_client=None,
            register_in_observatory_db=True,
        )
        lum_rec = lum_orch.run_lumina_observatory_episode(
            study_name="Lumina_Ranger_Corps_Observatory_Sovereignty_v1",
            gemini_client=None,
            register_in_observatory_db=True,
            persist_library_staging=False,
        )

        ledger = GovernanceCourtLedger(db_path=str(ledger_db))
        try:
            r1 = ledger.record_sol_continuum_episode(cont_rec)
            r2 = ledger.record_lumina_observatory_episode(lum_rec)
            assert r2["previous_run_digest"] == r1["ledger_entry_digest"]

            integrity = ledger.verify_ledger_integrity()
            assert integrity.is_valid is True
            assert integrity.total_runs_verified == 2
            assert integrity.total_events_verified == 16

            # Assess Continuum experiment + replay all 16 persisted sol-edge events via sol-change
            assessment = assess_continuum_observatory(
                Path(cont_rec.experiment_bundle_dir),
                ledger_db=ledger_db,
            )
            assert assessment["comparability"] == "compatible"
            assert assessment["outcome"] == "improved"
            assert assessment["cycle_drift_breakdown"]["verdict_transition"] == "QUARANTINE -> PROMOTE"
            assert assessment["cycle_drift_breakdown"]["mean_quality_drift"] > 0.20
            assert assessment["runtime_replay_verification"]["verified"] is True
            assert assessment["runtime_replay_verification"]["total_runs"] == 2
            assert assessment["runtime_replay_verification"]["total_events_replayed"] == 16
            assert assessment["runtime_replay_verification"]["total_thought_signatures"] >= 2

            # Tamper with a single sol_edge_runtime_events payload in SQLite
            with ledger._conn:
                ledger._conn.execute(
                    """
                    UPDATE sol_edge_runtime_events
                    SET payload_json = '{"experiment_plan_digest":"sha256:0000000000000000000000000000000000000000000000000000000000000000","capability_manifest_digest":"sha256:0000000000000000000000000000000000000000000000000000000000000000"}'
                    WHERE run_id = ? AND sequence_number = 1
                    """,
                    (r1["run_id"],),
                )

            tampered_integrity = ledger.verify_ledger_integrity()
            assert tampered_integrity.is_valid is False
            assert r1["run_id"] in tampered_integrity.broken_event_run_ids

            tampered_assessment = assess_continuum_observatory(
                Path(cont_rec.experiment_bundle_dir),
                ledger_db=ledger_db,
            )
            assert tampered_assessment["runtime_replay_verification"]["verified"] is False
        finally:
            ledger.close()


def test_frontier_k_guild_artifacts_metaplasticity_and_mixed_mode_replay() -> None:
    """
    Verifies:
    1. Every guild agent in `ep.guild_agents` carries its role-specific `verification_artifact`.
    2. `MetaplasticityEngine` injects thermal/metric perturbations (`perturbed_max_cond > 100.0`)
       and heals them via Shield 1 & 4 (`repaired_max_cond <= 100.0`).
    3. `symbolic_reflection_report` contains the full `dag` and `mermaid_markdown`.
    4. Live/mock Gemini `thought.signature` and token `usage` extraction works in both
       `SolContinuumDiscoveryOrchestrator` and `LuminaLibraryObservatoryOrchestrator`.
    5. Mixed-mode ledgers (`non_hermitian_skin_pt` + `sol_continuum_discovery_observatory` +
       `lumina_ranger_observatory_sovereignty`) replay cleanly, and deleting a `:cycle0-quarantine`
       stream is immediately detected as a broken event run.
    """
    from types import SimpleNamespace
    from observatory.continuum import replay_persisted_runtime_events
    from sol_decide.interop.non_hermitian_skin_pt import (
        NonHermitianPTSkinOrchestrator,
        NonHermitianPTSurgerySpec,
    )

    with tempfile.TemporaryDirectory(prefix="sol-frontier-km-hardened-") as tmp:
        tmp_path = Path(tmp)
        bridge = ChangeObservatoryBridge(
            experiments_root=tmp_path / "experiments",
            observatory_db_path=tmp_path / "observatory.sqlite3",
        )
        cont_orch = SolContinuumDiscoveryOrchestrator(observatory_bridge=bridge)
        lum_orch = LuminaLibraryObservatoryOrchestrator(observatory_bridge=bridge)

        mock_lumina_client = SimpleNamespace(
            interactions=SimpleNamespace(
                create=lambda **kw: SimpleNamespace(
                    id="int-lumina-custom-sig-777",
                    output_text="",
                    outputs=[
                        SimpleNamespace(
                            type="thought",
                            signature=b"custom-lumina-sig-alpha",
                            summary="Inspected PDM lanes and calibrated phase nudge.",
                        ),
                        SimpleNamespace(
                            type="thought",
                            signature=b"custom-lumina-sig-beta",
                            summary="Verified 25 FinalizationRanger invariants.",
                        ),
                    ],
                    usage=SimpleNamespace(input_tokens=512, thought_tokens=888, output_tokens=404),
                )
            )
        )

        cont_rec = cont_orch.run_continuum_discovery_episode(register_in_observatory_db=False)
        lum_rec = lum_orch.run_lumina_observatory_episode(
            gemini_client=mock_lumina_client,
            register_in_observatory_db=False,
            persist_library_staging=False,
        )

        # 1. Per-agent verification_artifact check
        assert len(cont_rec.guild_agents) == 5
        for agent in cont_rec.guild_agents:
            art = agent["verification_artifact"]
            assert isinstance(art, dict) and "engine" in art and len(art) >= 3

        # 2. Non-trivial metaplasticity perturbation & healing check
        mp = cont_rec.metaplasticity_report
        assert mp["perturbed_max_cond"] > 100.0
        assert mp["repaired_max_cond"] <= 100.0
        assert mp["repaired_max_cond"] < mp["perturbed_max_cond"]
        assert mp["is_healed"] is True

        # 3. Symbolic reflection DAG & packet Frontier K telemetry check
        sym = cont_rec.symbolic_reflection_report
        assert "dag" in sym and isinstance(sym["dag"], dict)
        assert "nodes" in sym["dag"] and "layers" in sym["dag"]
        assert "mermaid_markdown" in sym and "graph" in sym["mermaid_markdown"]
        assert "frontier_k_verification" in cont_rec.sol_lens_packet
        assert "reasoning_telemetry" in cont_rec.sol_lens_packet

        # 4. Lumina custom Gemini thought signature & usage extraction check
        assert lum_rec.reasoning_telemetry.interaction_id == "int-lumina-custom-sig-777"
        assert lum_rec.reasoning_telemetry.total_input_tokens == 512
        assert lum_rec.reasoning_telemetry.total_thought_tokens == 888
        assert lum_rec.reasoning_telemetry.total_output_tokens == 404
        assert len(lum_rec.reasoning_telemetry.thought_signature_digests) == 2
        assert "reasoning_telemetry" in lum_rec.sol_lens_packet

        # 5. Mixed-mode ledger replay & missing cycle0 stream detection
        ledger_db = tmp_path / "mixed_ledger.sqlite3"
        ledger = GovernanceCourtLedger(db_path=str(ledger_db))
        try:
            nh_spec = NonHermitianPTSurgerySpec(
                target_cavity_id="cavity_nhse_pt_core",
                calibrated_skin_gauge_gamma=0.0,
                clamped_pt_gain_loss_g=0.35,
                wormhole_pbc_flux_phase_rad=0.0,
                gbz_gauge_transformation_rationale="GBZ similarity transform eliminates winding.",
                non_hermitian_pt_rationale="Clamping g=0.35 < g_EP=1.0 restores real spectrum.",
            )
            nh_client = SimpleNamespace(
                interactions=SimpleNamespace(
                    create=lambda **kw: SimpleNamespace(
                        id="int-nhse-001",
                        output_text=nh_spec.model_dump_json(),
                        outputs=[SimpleNamespace(type="thought", signature=b"sig-nh", summary="Calibrated PT.")],
                        usage=SimpleNamespace(input_tokens=100, thought_tokens=200, output_tokens=80),
                    )
                )
            )
            nh_rec = NonHermitianPTSkinOrchestrator(client=nh_client).run_non_hermitian_pt_episode()
            ledger.record_non_hermitian_pt_episode(nh_rec)
            r_cont = ledger.record_sol_continuum_episode(cont_rec)
            ledger.record_lumina_observatory_episode(lum_rec)

            assert ledger.verify_ledger_integrity().is_valid is True
            obs_replay = replay_persisted_runtime_events(ledger_db)
            assert obs_replay["verified"] is True
            assert obs_replay["total_runs"] == 3
            assert obs_replay["total_streams"] == 6
            assert obs_replay["total_events_replayed"] == 24

            # Delete only the :cycle0-quarantine stream of the Continuum run and verify tamper detection
            with ledger._conn:
                ledger._conn.execute(
                    "DELETE FROM sol_edge_runtime_events WHERE run_id = ? AND option_id LIKE '%:cycle0-quarantine'",
                    (r_cont["run_id"],),
                )
            assert ledger.verify_ledger_integrity().is_valid is False
            assert r_cont["run_id"] in ledger.verify_ledger_integrity().broken_event_run_ids
            assert replay_persisted_runtime_events(ledger_db)["verified"] is False
        finally:
            ledger.close()


def test_frontier_l_wideword_lowering_fault_containment_and_production_lockdown() -> None:
    """
    Frontier L Edge-Case Verification:
    1. `CircuitToWideWordLoweringAdapter` lowers synthesized circuits across multiple boolean
       inputs `(0, 0, 0)`, `(1, 0, 1)`, `(1, 1, 1)` onto 32-bit and 64-bit `WideWordVirtualVM`
       and `OracleWideWordVM` with zero mismatches, preserving circuit truth-table parity and
       producing distinct packed vector/prefix results (`r6_hex`, `r7_hex`) per input vector.
    2. `CircuitNodeType.INVERTER` circuits (`MUX_2to1` and 10-node `EQUALS_2BIT`), custom >12-node
       simultaneously-live multi-output DAGs (exercising memory spill/reload), and
       `enable_waveguide_channel_state=True` (`WG_CHAN_SEND`, `WG_CHAN_ROUTE`, `WG_CHAN_RECV`,
       `WG_CHAN_FENCE`) lower and execute with 100% truth-table and oracle parity.
    3. Unsafe Micro-ISA v1 candidate instructions (`WG_CHAN_SEND` with channel state disabled,
       `PLOAD_RO` with dynamic register address) are rejected by `validate_v1_candidate_lowering_safety`.
    4. Multi-manifold 2PC atomic commit barrier rejects missing rollback snapshots / failed consensus
       and triggers clean rollback without partial commit.
    5. `SovereignRuntime` rejects `allow_production_execution=True` at build time and rejects
       `mode="production"` commands at execution time.
    """
    import pytest
    from sol.kernel.synthesis.circuit_topology import CircuitNodeType, SelfAssembledCircuit
    from sol_micro_isa_v1_lowering import validate_v1_candidate_lowering_safety
    from sol_multimanifold_atomic_commit import (
        MultiManifoldAtomicCommitDecision,
        build_multimanifold_atomic_commit_intent,
        commit_shadow_multimanifold_atomic,
        evaluate_atomic_commit_barrier,
    )
    from sol_sovereign_runtime import (
        SovereignRuntimeCommand,
        SovereignRuntimePolicy,
        build_sovereign_runtime,
        submit_runtime_command,
    )
    from sol_wideword_computation_validation import WideWordProgramInstruction

    adapter = CircuitToWideWordLoweringAdapter()
    r7_by_bits = {}
    expected_fa = {
        (0, 0, 0): {"SUM": 0, "COUT": 0},
        (1, 0, 1): {"SUM": 0, "COUT": 1},
        (1, 1, 1): {"SUM": 1, "COUT": 1},
    }
    for bits, exp_outs in expected_fa.items():
        bundle = adapter.lower_and_execute_circuit(input_bits=bits)
        assert bundle["vm_executions"]["32bit"]["oracle_match"] is True
        assert bundle["vm_executions"]["32bit"]["mismatch_count"] == 0
        assert bundle["vm_executions"]["32bit"]["circuit_truth_table_match"] is True
        assert bundle["vm_executions"]["32bit"]["circuit_outputs"] == exp_outs
        assert bundle["vm_executions"]["64bit"]["oracle_match"] is True
        assert bundle["vm_executions"]["64bit"]["mismatch_count"] == 0
        assert bundle["vm_executions"]["64bit"]["circuit_truth_table_match"] is True
        assert bundle["vm_executions"]["64bit"]["circuit_outputs"] == exp_outs
        assert bundle["micro_isa_summary"]["program_isa_valid"] is True
        assert bundle["micro_isa_summary"]["program_isa_errors"] == []
        r7_by_bits[bits] = bundle["vm_executions"]["32bit"]["r7_hex"]

    # Ensure circuit outputs genuinely drive the downstream v1 VEC_PACK / PREFIX_ADD registers
    assert len(set(r7_by_bits.values())) == 3
    assert r7_by_bits[(1, 1, 1)] == "0x7D5D7757"

    # Test INVERTER-heavy canonical circuits: MUX_2to1 (7 nodes) and EQUALS_2BIT (10 nodes)
    mux_circuit = adapter.synthesizer.synthesize_canonical("MUX_2to1").circuit
    for mux_bits, exp_y in (((0, 1, 0), 1), ((1, 1, 0), 0), ((1, 0, 1), 1)):
        mux_bundle = adapter.lower_and_execute_circuit(circuit=mux_circuit, input_bits=mux_bits)
        assert mux_bundle["vm_executions"]["32bit"]["circuit_truth_table_match"] is True
        assert mux_bundle["vm_executions"]["32bit"]["circuit_outputs"] == {"Y": exp_y}
        assert mux_bundle["vm_executions"]["64bit"]["circuit_truth_table_match"] is True

    eq_circuit = adapter.synthesizer.synthesize_canonical("EQUALS_2BIT").circuit
    assert len(eq_circuit.nodes) == 10
    for eq_bits, exp_eq in (((1, 0, 0, 0), 0), ((0, 1, 1, 0), 0), ((1, 0, 1, 0), 1), ((0, 0, 0, 0), 1)):
        eq_bundle = adapter.lower_and_execute_circuit(
            circuit=eq_circuit,
            input_bits=eq_bits,
            enable_waveguide_channel_state=True,
        )
        assert eq_bundle["lowering_reports"]["32bit"]["successfully_lowered"] == 9
        assert eq_bundle["lowering_reports"]["32bit"]["safety_checks_passed"] is True
        assert eq_bundle["vm_executions"]["32bit"]["oracle_match"] is True
        assert eq_bundle["vm_executions"]["32bit"]["circuit_truth_table_match"] is True
        assert eq_bundle["vm_executions"]["32bit"]["circuit_outputs"] == {"EQUAL": exp_eq}
        assert eq_bundle["vm_executions"]["64bit"]["oracle_match"] is True
        assert eq_bundle["vm_executions"]["64bit"]["circuit_truth_table_match"] is True

    # Test custom >12 simultaneously-live node multi-output DAG (exercising register spill/reload)
    wide_circuit = SelfAssembledCircuit("wide_14_inputs_3_outputs", "WideSpillCircuit")
    for idx in range(14):
        wide_circuit.add_node(f"IN_{idx}", CircuitNodeType.INPUT, [-4.0, float(idx)])
    wide_circuit.add_node("AND_ALL", CircuitNodeType.LENS_AND, [0.0, 0.0])
    wide_circuit.add_node("XOR_PAIR", CircuitNodeType.INTERFERENCE, [0.0, 2.0])
    wide_circuit.add_node("INV_0", CircuitNodeType.INVERTER, [0.0, 4.0])
    wide_circuit.add_node("OUT_AND", CircuitNodeType.BASIN, [4.0, 0.0])
    wide_circuit.add_node("OUT_XOR", CircuitNodeType.BASIN, [4.0, 2.0])
    wide_circuit.add_node("OUT_INV", CircuitNodeType.BASIN, [4.0, 4.0])
    for idx in range(14):
        wide_circuit.add_edge(f"IN_{idx}", "AND_ALL", 1.0)
    wide_circuit.add_edge("IN_0", "XOR_PAIR", 1.0)
    wide_circuit.add_edge("IN_13", "XOR_PAIR", 1.0)
    wide_circuit.add_edge("IN_0", "INV_0", 1.0)
    wide_circuit.add_edge("AND_ALL", "OUT_AND", 1.0)
    wide_circuit.add_edge("XOR_PAIR", "OUT_XOR", 1.0)
    wide_circuit.add_edge("INV_0", "OUT_INV", 1.0)

    wide_bundle = adapter.lower_and_execute_circuit(
        circuit=wide_circuit,
        input_bits=tuple([0] + [1] * 13),
    )
    assert wide_bundle["vm_executions"]["32bit"]["oracle_match"] is True
    assert wide_bundle["vm_executions"]["32bit"]["circuit_truth_table_match"] is True
    assert wide_bundle["vm_executions"]["32bit"]["circuit_outputs"] == {
        "OUT_AND": 0,
        "OUT_XOR": 1,
        "OUT_INV": 1,
    }
    assert wide_bundle["vm_executions"]["64bit"]["oracle_match"] is True
    assert wide_bundle["vm_executions"]["64bit"]["circuit_truth_table_match"] is True

    # Unsafe v1 candidate opcodes must be rejected by lowering safety checks
    unsafe_wg = WideWordProgramInstruction("WG_CHAN_SEND", 0, "R1")
    ok_wg, reason_wg = validate_v1_candidate_lowering_safety(
        unsafe_wg, enable_waveguide_channel_state=False
    )
    assert ok_wg is False
    assert reason_wg == "unsupported_waveguide_channel_operation"

    unsafe_pload = WideWordProgramInstruction("PLOAD_RO", "R1", "Z", ("R2", 0x10))
    ok_pl, reason_pl = validate_v1_candidate_lowering_safety(
        unsafe_pload, enable_waveguide_channel_state=False
    )
    assert ok_pl is False
    assert reason_pl == "dynamic_address_unknown_alias"

    # Multi-manifold 2PC barrier rejection on missing rollback snapshot
    faulty_intent = build_multimanifold_atomic_commit_intent(
        transaction_intent={"value": 0xCAFEBABE},
        coordination_group=["M1", "M2", "M3"],
        metadata={"missing_rollback_snapshot_for": "M2"},
    )
    faulty_barrier = evaluate_atomic_commit_barrier(faulty_intent, {"status": "approved"})
    assert faulty_barrier.satisfied is False
    assert len(faulty_barrier.errors) >= 1
    abort_decision = MultiManifoldAtomicCommitDecision(
        decision_id="DEC_ABORT_TEST",
        status="abort",
        justification="Missing rollback snapshot on M2.",
    )
    abort_report = commit_shadow_multimanifold_atomic(faulty_intent, abort_decision)
    assert abort_report.result.committed_value is None
    assert abort_report.result.rollback_triggered is True

    # SovereignRuntime production lockdown enforcement
    with pytest.raises(ValueError, match="production execution is strictly prohibited"):
        build_sovereign_runtime(SovereignRuntimePolicy(allow_production_execution=True))

    rt = build_sovereign_runtime(SovereignRuntimePolicy(allow_production_execution=False))
    with pytest.raises(ValueError, match="Production mode execution is blocked"):
        submit_runtime_command(
            rt,
            SovereignRuntimeCommand(
                command_id="CMD_PROD_FORBIDDEN",
                target_level=12,
                operation="quantum_wavefront_calibration",
                mode="production",
            ),
        )
    assert rt.mode == "hold"


def test_frontier_n_autopoietic_organism_unification_and_edge_cases() -> None:
    """
    Frontier N Unit & Edge-Case Verification:
    1. Verifies all 4 pillars of `FrontierNAutopoieticHarmonizer` (`epistemic_gap_intake`,
       `bimodal_dream_consolidation`, `bilateral_entangler_control`, and
       `statistical_evolution_governance`) execute end-to-end and are embedded in both
       `SolContinuumDiscoveryOrchestrator` and `LuminaLibraryObservatoryOrchestrator` packets
       and `assess_continuum_observatory` summaries.
    2. Verifies `verify_core_graph_immutability` detects any byte tampering on a copy of
       `default_graph.json` while keeping the real `default_graph.json` strictly immutable.
    3. Verifies `EntanglerGiant` + `HintGatingPolicy` blocks nudges when Lyapunov exponent
       `lambda_hat > 0` (`nudge_msf_status == "unstable"`, `nudge_rejection_reason == "msf_unstable"`).
    4. Verifies `sol-evolve` `apply_candidate` raises ValueError on `sacred_math_impact == "FORBIDDEN"`,
       and `Judge` + `Gatekeeper` reject regressed candidate runs.
    """
    import pytest
    from observatory.continuum import assess_continuum_observatory
    from sol_continuum import (
        EXPECTED_CORE_GRAPH_SHA256,
        FrontierNAutopoieticHarmonizer,
        verify_core_graph_immutability,
    )
    from sol_continuum.autopoietic_organism import (
        Candidate,
        Gatekeeper,
        Judge,
        RunResult,
        apply_candidate,
    )

    harmonizer = FrontierNAutopoieticHarmonizer()
    report = harmonizer.execute_autopoietic_episode(
        study_name="FrontierN_Autopoietic_Verification_v1",
        episode_mode="continuum_discovery",
        run_id="test-frontier-n-001",
        cycle0_metrics={
            "evidence": 0.42,
            "coherence": 0.44,
            "contradiction": 0.56,
            "continuity": 0.41,
            "authority": 0.45,
            "faithfulness": 0.43,
        },
        cycle1_metrics={
            "evidence": 0.91,
            "coherence": 0.93,
            "contradiction": 0.04,
            "continuity": 0.90,
            "authority": 0.92,
            "faithfulness": 0.94,
        },
    )
    assert report.autopoietic_loop_verified is True
    assert report.summary_digest.startswith("sha256:")

    # Pillar 1: Autonomous Epistemic Intake & Smoke Immutability
    p1 = report.epistemic_gap_intake
    assert p1["core_immutability_verified"] is True
    assert p1["core_graph_sha256"] == EXPECTED_CORE_GRAPH_SHA256
    assert p1["smoke_stage_passed"] is True
    assert p1["total_gaps_detected"] >= 4
    assert p1["stage_contract"]["stage"] == "cortex"

    # Pillar 2: Bimodal Hippocampal Dream Consolidation & Spectral Isomorphism
    p2 = report.bimodal_dream_consolidation
    assert p2["bimodal_synapse_verified"] is True
    assert p2["sol_hippocampus_replay"]["overlay_core_nodes"] == 140
    assert p2["sol_hippocampus_replay"]["overlay_memory_nodes"] >= 2
    assert p2["sol_hippocampus_replay"]["basin_stability"] >= 0.66
    assert p2["riemannian_isometric_sink"]["status"] == "CONSOLIDATED"
    assert p2["riemannian_isometric_sink"]["geodesic_correlation"] >= 0.95
    assert p2["circuit_cache_telemetry"]["total_accesses"] >= 1
    assert p2["circuit_cache_telemetry"]["consolidated_count"] >= 1

    # Pillar 3: Bilateral Topological Control (EntanglerGiant + HintGatingPolicy MSF Guard)
    p3 = report.bilateral_entangler_control
    assert p3["bilateral_lock_verified"] is True
    assert p3["cycle0_control"]["nudge_msf_status"] == "unstable"
    assert p3["cycle0_control"]["nudge_msf_lambda_hat"] > 0.0
    assert p3["cycle0_control"]["nudge_applied"] is False
    assert p3["cycle0_control"]["nudge_rejection_reason"] == "msf_unstable"
    assert p3["transverse_msf_status"] == "stable"
    assert p3["transverse_msf_lambda_hat"] < -0.01
    assert p3["hint_gate_accepted"] is True
    assert p3["bounded_nudge_applied"] is True
    assert len(p3["wormhole_weight_map"]) == 4

    # Pillar 4: Statistical Self-Evolution & Trust Governance
    p4 = report.statistical_evolution_governance
    assert p4["promotion_statistically_governed"] is True
    assert p4["ab_test_summary"]["verdict"] in ("PASS", "IMPROVE", "IMPROVED")
    assert p4["ab_test_summary"]["sacred_math_impact"] == "none"
    assert p4["statistical_significance"]["is_significant_p_lt_0_05"] is True
    assert p4["statistical_significance"]["one_sided_p_value"] < 0.05
    assert p4["statistical_significance"]["cohens_d_effect_size"] >= 1.2
    assert p4["meta_learner_telemetry"]["insight_score"] >= 0.65
    assert p4["self_train_gatekeeper"]["accepted"] is True
    assert p4["trust_governance"]["mean_trust_score"] >= 0.70
    assert p4["trust_governance"]["total_trigger_events"] == 0

    # Verify real default_graph.json is untouched
    real_ok, real_sha = verify_core_graph_immutability()
    assert real_ok is True
    assert real_sha == EXPECTED_CORE_GRAPH_SHA256

    with tempfile.TemporaryDirectory(prefix="sol-frontier-n-edge-") as tmp:
        tmp_path = Path(tmp)
        # Edge case 1: Tampered default_graph.json copy must fail SHA-256 immutability check
        tampered_graph = tmp_path / "tampered_default_graph.json"
        tampered_graph.write_text('{"tampered": true}\n', encoding="utf-8")
        tampered_ok, tampered_sha = verify_core_graph_immutability(tampered_graph)
        assert tampered_ok is False
        assert tampered_sha != EXPECTED_CORE_GRAPH_SHA256

        # Edge case 2: Forbidden sacred math candidate must raise ValueError in apply_candidate
        forbidden_cand = Candidate(
            name="forbidden_sacred_math_mutation",
            description="Attempts to mutate non-tunable sacred Hamiltonian parameter",
            hypothesis="Should be blocked by sacred_math_impact guard",
            change_type="param_tune",
            target="core.sacred_hamiltonian",
            parameters={"core.sacred_hamiltonian": 2.0},
            expected_improvements=[],
            acceptable_regressions=[],
            sacred_math_impact="FORBIDDEN",
        )
        with pytest.raises(ValueError, match="sacred_math_impact=FORBIDDEN"):
            apply_candidate(object(), forbidden_cand)

        # Edge case 3: EntanglerGiant + HintGatingPolicy blocks nudges when both cycles have diverging phase gap
        diverging_ctrl = harmonizer.run_bilateral_entangler_control(
            episode_mode="continuum_discovery",
            cycle0_phase_coherence_history=[0.66, 0.59, 0.51, 0.42],
            cycle1_phase_coherence_history=[0.66, 0.59, 0.51, 0.42],
        )
        assert diverging_ctrl["transverse_msf_status"] == "unstable"
        assert diverging_ctrl["transverse_msf_lambda_hat"] > 0.0
        assert diverging_ctrl["bounded_nudge_applied"] is False
        assert diverging_ctrl["bilateral_lock_verified"] is False

        # Edge case 4: Judge & Gatekeeper reject regressed candidate runs
        judge = Judge(
            weights={
                "stability": 0.35,
                "novelty": 0.20,
                "usefulness": 0.30,
                "reproducibility": 0.20,
                "cost": 0.05,
            }
        )
        base_score = judge.score(
            "baseline",
            [
                RunResult(
                    policy_id="baseline",
                    task_id="t_0",
                    elapsed_sec=0.20,
                    metrics={
                        "stability": 0.90,
                        "novelty": 0.80,
                        "usefulness": 0.88,
                        "reproducibility": 0.95,
                        "cost": 0.10,
                    },
                )
            ],
        )
        regressed_score = judge.score(
            "regressed_candidate",
            [
                RunResult(
                    policy_id="regressed_candidate",
                    task_id="t_0",
                    elapsed_sec=0.35,
                    metrics={
                        "stability": 0.55,
                        "novelty": 0.40,
                        "usefulness": 0.50,
                        "reproducibility": 0.60,
                        "cost": 0.40,
                    },
                )
            ],
        )
        gk = Gatekeeper(min_anchor_delta=0.05, max_full_regression=0.0)
        bad_decision = gk.decide(
            baseline_full=base_score,
            candidate_full=regressed_score,
            baseline_anchor=base_score,
            candidate_anchor=regressed_score,
        )
        assert bad_decision.accepted is False
        assert bad_decision.delta_anchor_score < 0.0

        # Verify Continuum + Lumina episodes embed frontier_n_verification and sol-change surfaces it
        bridge = ChangeObservatoryBridge(
            experiments_root=tmp_path / "experiments",
            observatory_db_path=tmp_path / "observatory.sqlite3",
        )
        cont_rec = SolContinuumDiscoveryOrchestrator(
            observatory_bridge=bridge
        ).run_continuum_discovery_episode(register_in_observatory_db=False)
        assert cont_rec.frontier_n_verification["autopoietic_loop_verified"] is True
        assert cont_rec.frontier_n_verification["epistemic_gap_intake"]["selected_gap"]["gap_id"].startswith("GAP-001")
        assert cont_rec.sol_lens_packet["observatory_context"]["conditions"]["selected_gap_id"].startswith("GAP-001")
        assert "frontier_n_verification" in cont_rec.sol_lens_packet

        cont_assess = assess_continuum_observatory(Path(cont_rec.experiment_bundle_dir))
        f_sum = cont_assess["cycle_drift_breakdown"]["frontier_verification_summary"]
        assert f_sum["frontier_k_verified"] is True
        assert f_sum["frontier_n_verified"] is True
        assert f_sum["frontier_n_core_immutability_verified"] is True
        assert f_sum["frontier_n_bimodal_dream_verified"] is True
        assert f_sum["frontier_n_bilateral_entangler_verified"] is True
        assert f_sum["frontier_n_statistical_governance_verified"] is True

        # Edge case 5: Multi-threaded concurrent execution of FrontierNAutopoieticHarmonizer
        from concurrent.futures import ThreadPoolExecutor

        def _worker(idx: int):
            mode = "continuum_discovery" if idx % 2 == 0 else "lumina_sovereign"
            return harmonizer.execute_autopoietic_episode(
                study_name=f"Concurrent_FrontierN_{idx}",
                episode_mode=mode,
                run_id=f"concurrent-fn-{idx:02d}",
                cycle0_metrics={
                    "evidence": 0.42,
                    "coherence": 0.44,
                    "contradiction": 0.56,
                    "continuity": 0.41,
                    "authority": 0.45,
                    "faithfulness": 0.43,
                },
                cycle1_metrics={
                    "evidence": 0.91,
                    "coherence": 0.93,
                    "contradiction": 0.04,
                    "continuity": 0.90,
                    "authority": 0.92,
                    "faithfulness": 0.94,
                },
            )

        with ThreadPoolExecutor(max_workers=4) as pool:
            concurrent_reports = list(pool.map(_worker, range(4)))
        for idx, rep in enumerate(concurrent_reports):
            assert rep.autopoietic_loop_verified is True
            expected_prefix = "GAP-001" if idx % 2 == 0 else "GAP-002"
            assert rep.epistemic_gap_intake["selected_gap"]["gap_id"].startswith(expected_prefix)
            assert rep.statistical_evolution_governance["meta_learner_telemetry"]["total_outcomes"] == 1

        # Edge case 6: GovernanceCourtLedger preserves Frontier K/L/N metadata and detects proof_packet_json tampering
        import json
        from sol_decide.delivery.governance_ledger import GovernanceCourtLedger

        lum_rec = LuminaLibraryObservatoryOrchestrator(
            observatory_bridge=bridge
        ).run_lumina_observatory_episode(
            register_in_observatory_db=False,
            persist_library_staging=False,
        )
        assert lum_rec.sol_lens_packet["observatory_context"]["conditions"]["selected_gap_id"].startswith("GAP-002")

        ledger_db = tmp_path / "frontier_n_court_ledger.sqlite3"
        ledger = GovernanceCourtLedger(db_path=str(ledger_db))
        c_entry = ledger.record_sol_continuum_episode(cont_rec)
        assert c_entry["frontier_k_verified"] is True
        assert c_entry["frontier_n_verified"] is True
        assert c_entry["frontier_n_summary_digest"].startswith("sha256:")

        l_entry = ledger.record_lumina_observatory_episode(lum_rec)
        assert l_entry["frontier_l_verified"] is True
        assert l_entry["frontier_n_verified"] is True
        assert l_entry["frontier_n_summary_digest"].startswith("sha256:")

        rep_records = ledger.list_repair_records(limit=10)
        assert any(r["postStalk"].get("frontier_l_verified") is True and r["postStalk"].get("frontier_n_verified") is True for r in rep_records)
        assert ledger.verify_ledger_integrity().is_valid is True

        # Tamper with frontier_n_verification inside proof_packet_json and verify ledger catches it
        tampered_pkt = json.loads(json.dumps(lum_rec.sol_lens_packet))
        tampered_pkt["frontier_n_verification"]["epistemic_gap_intake"]["core_immutability_verified"] = False
        with ledger._conn:
            ledger._conn.execute(
                "UPDATE governance_court_runs SET proof_packet_json = ? WHERE run_id = ?",
                (json.dumps(tampered_pkt), l_entry["run_id"]),
            )
        tampered_integrity = ledger.verify_ledger_integrity()
        assert tampered_integrity.is_valid is False
        assert l_entry["run_id"] in tampered_integrity.broken_run_ids
        ledger.close()

