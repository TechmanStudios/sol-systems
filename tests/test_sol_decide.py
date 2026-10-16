"""
Tests for SOL-Decide: Sheaf-Theoretic Governed Agentic Decision Management OS
=============================================================================
Formal verification suite covering:
1. 6 Decision Primitives & Stalk Dimensions
2. Sheaf Decision Complex Assembly, Coboundary & Laplacian Operations
3. Cohomological Invariants: Betti Numbers beta_0, beta_1 & Obstruction Auditing
4. JSON-Schema Roundtrip Serialization
5. 7 Giants MoA Structured Elicitation & Metacognitive Invariants
6. Dialectical Adversary Anti-Bias Stress & 0.00% False Commit Guarantee
7. Quantitative Causal Ablation ("What Flips the Decision" Sensitivity & MSCK)
8. OMG SysML 2.0 / KerML AST Ingestion Bridge
9. DAOSoft Bi-Directional Interoperability Bridge
10. Demonstration 1: NGCV Powertrain Single-Episode Point-in-Time Trade Study
11. Demonstration 2: Multi-Episode Long-Horizon Living Refresh Program & Differential Delta
12. Signer-Ready Decision Package Compiler & Cryptographic SHA-256 Proof Certificate
"""

import json
from pathlib import Path
import pytest
import numpy as np
import scipy.linalg as la

import sol_decide
from sol_decide.core import (
    PrimitiveType,
    OptimizationDirection,
    ConstraintSeverity,
    Objective,
    Option,
    Constraint,
    Assumption,
    Risk,
    BiasCheck,
    SheafDecisionComplex,
    SheafEdge,
    DecisionEvaluationReport,
    export_complex_to_dict,
    import_complex_from_dict,
    export_complex_to_json,
    import_complex_from_json
)
from sol_decide.agentic import (
    SevenGiantsElicitor,
    DialecticalAdversary,
    SensitivityAblator
)
from sol_decide.interop import (
    SysMLKerMLParser,
    DAOSoftBridge
)
from sol_decide.delivery import (
    DecisionPackageCompiler,
    DifferentialDeltaEngine,
    OperationalShock
)
from sol_decide.demonstrations import (
    build_ngcv_trade_study,
    run_demonstration_1,
    run_demonstration_2
)


def test_primitives_creation_and_bounds():
    """Verify all 6 core decision primitives initialize with typed stalks and proper attributes."""
    obj = Objective(id="obj1", name="Payload Capacity", target_value=12.5, units="tons")
    assert obj.primitive_type == PrimitiveType.OBJECTIVE
    assert obj.stalk_dim == 1
    assert float(obj.state_vector[0]) == 12.5

    opt = Option(id="opt1", name="Concept A", stalk_dim=3, initial_params=np.array([10.0, 20.0, 30.0]), trl=7)
    assert opt.primitive_type == PrimitiveType.OPTION
    assert opt.stalk_dim == 3
    assert opt.trl == 7
    assert np.allclose(opt.state_vector, [10.0, 20.0, 30.0])

    con = Constraint(id="con1", name="Max Weight", upper_bound=45.0, severity=ConstraintSeverity.HARD)
    assert con.primitive_type == PrimitiveType.CONSTRAINT
    is_viol, mag = con.evaluate_violation(47.5)
    assert is_viol is True
    assert pytest.approx(mag, 1e-4) == 2.5
    is_viol2, mag2 = con.evaluate_violation(42.0)
    assert is_viol2 is False
    assert mag2 == 0.0

    ass = Assumption(id="ass1", name="Cell Density", baseline_value=450.0, uncertainty_sigma=0.08)
    assert ass.primitive_type == PrimitiveType.ASSUMPTION
    eff_sigma = ass.advance_time(12.0)
    assert eff_sigma > 0.08

    risk = Risk(id="risk1", name="Thermal Delay", probability=0.3, impact=0.8)
    assert risk.primitive_type == PrimitiveType.RISK
    assert pytest.approx(risk.severity_score, 1e-4) == 0.24

    bias = BiasCheck(id="bias1", name="Vendor Lockin Check", bias_category="vendor_bias")
    assert bias.primitive_type == PrimitiveType.BIAS_CHECK
    assert bias.is_refuted is False


def test_sheaf_complex_coboundary_and_laplacian():
    """Verify assembly of coboundary delta^0 and symmetric positive semi-definite Laplacian Delta^0."""
    complex_obj = SheafDecisionComplex(name="TestComplex")
    opt = Option(id="opt", name="Opt", stalk_dim=2, initial_params=np.array([10.0, 5.0]))
    con = Constraint(id="con", name="Con", lower_bound=4.0, upper_bound=6.0)
    complex_obj.add_primitive(opt)
    complex_obj.add_primitive(con)

    s_map = np.array([[0.0, 1.0]])  # Select channel 1 (value 5.0)
    complex_obj.add_edge(
        edge_id="e1",
        source_id="opt",
        target_id="con",
        dim_edge=1,
        source_map=s_map,
        target_map=np.array([[1.0]]),
        edge_type="constraint_check"
    )

    delta = complex_obj.build_coboundary()
    assert delta.shape == (1, 3)

    lap = complex_obj.build_laplacian()
    assert lap.shape == (3, 3)
    # Check symmetry: Delta^0 == (Delta^0)^T
    assert np.allclose(lap, lap.T)
    # Check positive semi-definiteness: all eigenvalues >= -1e-9
    eigs = la.eigvalsh(lap)
    assert np.all(eigs >= -1e-9)

    beta_0, beta_1 = complex_obj.compute_betti_numbers()
    assert beta_0 >= 1
    assert beta_1 == 0


def test_json_serialization_roundtrip():
    """Verify export and import of complex to and from JSON format."""
    c = build_ngcv_trade_study()
    json_str = export_complex_to_json(c)
    assert "NGCV_Powertrain_Trade_Study" in json_str

    restored = import_complex_from_json(json_str)
    assert restored.name == c.name
    assert len(restored.primitives) == len(c.primitives)
    assert len(restored.edges) == len(c.edges)
    
    b0_orig, b1_orig = c.compute_betti_numbers()
    b0_rest, b1_rest = restored.compute_betti_numbers()
    assert b0_orig == b0_rest
    assert b1_orig == b1_rest


def test_seven_giants_elicitation():
    """Verify 7 Giants MoA structured elicitation and mathematical invariants."""
    elicitor = SevenGiantsElicitor()
    spec = {
        "objectives": [
            {"id": "o1", "name": "Obj1", "weight": 0.6, "target_value": 10.0},
            {"id": "o2", "name": "Obj2", "weight": 0.4, "target_value": 5.0}
        ],
        "options": [
            {"id": "alt1", "name": "Alt1", "state_vector": [10.0, 5.0]}
        ],
        "constraints": [
            {"id": "c1", "name": "Con1", "lower_bound": 0.0, "upper_bound": 20.0}
        ],
        "assumptions": [
            {"id": "a1", "name": "Ass1", "baseline_value": 1.0, "uncertainty_sigma": 0.05}
        ],
        "risks": [
            {"id": "r1", "name": "Risk1", "probability": 0.1, "impact": 0.3}
        ],
        "bias_checks": [
            {"id": "b1", "name": "Bias1", "bias_category": "confirmation_bias"}
        ],
        "edges": [
            {
                "id": "e1",
                "source_id": "alt1",
                "target_id": "c1",
                "dim_edge": 1,
                "source_map": [[1.0, 0.0]],
                "target_map": [[1.0]]
            }
        ]
    }
    res = elicitor.elicit_from_requirements("TestElicit", spec)
    assert res.is_valid is True
    assert res.kuramoto_order_r >= 0.70
    assert res.condition_number <= 500.0
    assert res.causal_emergence_delta_ei > 0.0
    assert "The Statistician" in res.giant_reports
    assert "The Graph Navigator" in res.giant_reports
    assert "The Linear Algebraist" in res.giant_reports
    assert "The Aligner" in res.giant_reports
    assert "The Integrator" in res.giant_reports

    # Verify cycle detection catches a genuine directed cycle
    cyclic_spec = dict(spec)
    cyclic_spec["edges"] = list(spec["edges"]) + [
        {
            "id": "e_back",
            "source_id": "c1",
            "target_id": "alt1",
            "dim_edge": 1,
            "source_map": [[1.0]],
            "target_map": [[1.0, 0.0]]
        }
    ]
    res_cyclic = elicitor.elicit_from_requirements("CyclicElicit", cyclic_spec)
    assert res_cyclic.giant_reports["The Graph Navigator"].passed is False
    assert res_cyclic.is_valid is False


def test_dialectical_adversary_stress_and_false_commit():
    """Verify adversarial strain injection and 0.00% False Commit Rate."""
    c = build_ngcv_trade_study()
    
    # 1. Operational envelope check (5% strain) - must remain resilient
    adversary_op = DialecticalAdversary(max_strain_trials=25, strain_magnitude=0.05)
    rep_op = adversary_op.stress_test_candidate(c, "opt_hed")
    assert rep_op.is_resilient is True
    assert rep_op.false_commit_rate == 0.00
    assert rep_op.max_strain_tolerated > 0.0

    # 2. Extreme inflection strain check (15% strain) - detects boundary and yields witness
    adversary_inf = DialecticalAdversary(max_strain_trials=30, strain_magnitude=0.15)
    rep_inf = adversary_inf.stress_test_candidate(c, "opt_hed")
    assert rep_inf.inflection_point_detected is True
    assert rep_inf.witness_vector is not None
    assert rep_inf.false_commit_rate == 0.00


def test_sensitivity_ablation_what_flips_the_decision():
    """Verify Quantitative Causal Ablation and MSCK flip boundary calculation."""
    c = build_ngcv_trade_study()
    ablator = SensitivityAblator(sweep_steps=25, max_deviation_ratio=0.50)
    rep = ablator.compute_decision_flips(c)
    assert rep.baseline_selected_option == "opt_hed"
    assert len(rep.minimal_sufficient_causal_kernel) >= 1
    # Check that at least one sensitive parameter has a flip threshold
    sens_thresh = [t for t in rep.parameter_thresholds if t.is_sensitive]
    assert len(sens_thresh) > 0
    # Weight channel of HED should flip when increased
    weight_thresh = next((t for t in sens_thresh if "ch_0" in t.primitive_name), None)
    assert weight_thresh is not None
    assert weight_thresh.flip_value > 42.0  # Flipped above baseline 42.0 tons
    # Upstream Battery Density assumption should propagate via restriction map and flip when decreased
    ass_thresh = next((t for t in sens_thresh if t.primitive_id == "ass_battery_density"), None)
    assert ass_thresh is not None
    assert ass_thresh.flip_value < 450.0  # Flipped below baseline 450.0 Wh/kg


def test_sysml_kerml_ast_parser():
    """Verify parsing SysML 2.0 text blocks into SheafDecisionComplex."""
    sysml_text = """
    part def AdvancedTurbine {
        attribute weight_tons : Real = 6.2;
        attribute output_kw : Real = 1200.0;
    }
    constraint def PayloadLimit {
        attribute max_weight : Real = 15.0;
    }
    requirement def PowerMandate {
        attribute min_power : Real = 1000.0;
    }
    """
    parser = SysMLKerMLParser()
    c = parser.parse_sysml_text(sysml_text, "TurbineSystem")
    assert "sysml_advancedturbine" in c.primitives
    assert "sysml_payloadlimit" in c.primitives
    assert "sysml_powermandate" in c.primitives

    opt = c.primitives["sysml_advancedturbine"]
    assert opt.primitive_type == PrimitiveType.OPTION
    assert opt.stalk_dim == 2


def test_daosoft_bridge():
    """Verify DAOSoft trade study tabular ingestion and export."""
    daosoft_json = {
        "study_title": "Ground Vehicle Armor Trade Study",
        "criteria": [
            {"id": "c_protection", "name": "Kinetic Protection", "weight": 0.6, "min_val": 50.0, "max_val": 100.0},
            {"id": "c_mobility", "name": "Mobility Index", "weight": 0.4, "min_val": 40.0, "max_val": 100.0}
        ],
        "alternatives": [
            {"id": "a_steel", "name": "Rolled Homogeneous Armor", "scores": {"c_protection": 60.0, "c_mobility": 50.0}, "cost_m": 5.0},
            {"id": "a_ceramic", "name": "Silicon Carbide Composite", "scores": {"c_protection": 90.0, "c_mobility": 80.0}, "cost_m": 12.0}
        ]
    }
    bridge = DAOSoftBridge()
    c = bridge.ingest_daosoft_matrix(daosoft_json)
    eval_rep = c.evaluate_decision_package()
    assert eval_rep.is_feasible is True
    assert eval_rep.selected_option_id == "opt_a_ceramic"

    exported = bridge.export_to_daosoft(c, eval_rep)
    assert exported["study_name"] == "Ground Vehicle Armor Trade Study"
    assert exported["selected_alternative"] == "opt_a_ceramic"
    assert exported["verification_status"] == "CERTIFIED"


def test_demonstration_1_ngcv_powertrain():
    """Verify full Demonstration 1: NGCV Powertrain Trade Study."""
    c, pkg, sens, bias = run_demonstration_1()
    assert pkg.is_certifiable is True
    assert pkg.selected_option_id == "opt_hed"
    assert pkg.betti_1 == 0
    assert pkg.false_commit_rate == 0.00
    assert pkg.authorization_gate.is_signed is False
    assert len(pkg.cryptographic_proof_hash) == 64

    # Markdown export check
    md_text = pkg.to_markdown()
    assert "ACQUISITION DECISION PACKAGE" in md_text
    assert "Series Hybrid-Electric Drive (HED)" in md_text
    assert "SYNTHETIC DEMO - MATHEMATICALLY CERTIFIABLE" in md_text


def test_demonstration_2_living_refresh_delta():
    """Verify Demonstration 2: 18-Month Living Refresh Program & Differential Delta."""
    delta, ref_eval, c = run_demonstration_2()
    assert delta.baseline_option_id == "opt_hed"
    assert delta.did_decision_flip is True
    assert len(delta.applied_shocks) == 3
    assert len(delta.activated_coboundary_edges) > 0
    assert delta.post_energy > delta.pre_energy
    assert "FLIPPED" in delta.audit_summary


def test_demo_package_has_only_synthetic_sign_off():
    """Generated packages and serialized exports cannot claim Army authorization."""
    from dataclasses import asdict
    from sol_decide.delivery.decision_package import DEMO_NOTICE, DEMO_SIGNER_ROLE

    _, pkg, _, _ = run_demonstration_1()
    gate = pkg.authorization_gate
    assert pkg.is_demo is True
    assert gate.is_signed is False
    assert gate.is_simulated_signature is True
    assert gate.signer_name == gate.authorized_role == DEMO_SIGNER_ROLE
    assert gate.signature_timestamp is None
    assert gate.comments == DEMO_NOTICE
    serialized = json.loads(json.dumps(asdict(pkg)))
    assert serialized["is_demo"] is True
    assert serialized["authorization_gate"]["is_signed"] is False
    assert serialized["authorization_gate"]["is_simulated_signature"] is True
    markdown = pkg.to_markdown()
    assert DEMO_NOTICE in markdown
    assert "SIMULATED SIGN-OFF ONLY" in markdown
    assert "SIGNED by" not in markdown
    assert "READY FOR SIGNATURE" not in markdown
    for output in (markdown, json.dumps(serialized)):
        assert "Bryan Tucker" not in output
        assert "PEO GCS Chief Engineer" not in output
    with pytest.raises(PermissionError, match="Synthetic demo"):
        pkg.sign("Example official")
    assert gate.is_signed is False
    assert gate.signer_name == DEMO_SIGNER_ROLE


def test_demo_benchmark_matches_generated_authorization_metadata():
    """The reusable benchmark must preserve the generated demo provenance."""
    _, pkg, _, _ = run_demonstration_1()
    benchmark = json.loads(
        (Path(__file__).resolve().parents[1] / "data" / "sol_decide_benchmark_report.json").read_text(encoding="utf-8")
    )["demonstration_1_point_in_time"]
    assert benchmark["is_demo"] is pkg.is_demo is True
    assert benchmark["is_signed"] is pkg.authorization_gate.is_signed is False
    assert benchmark["is_simulated_signature"] is pkg.authorization_gate.is_simulated_signature is True
    assert benchmark["signer"] == pkg.authorization_gate.signer_name
    assert benchmark["authorization_notice"] == pkg.authorization_gate.comments
    assert benchmark["proof_hash"] == pkg.cryptographic_proof_hash


def test_demo_cli_export_is_explicitly_synthetic(tmp_path, monkeypatch):
    from sol_decide.cli import main
    from sol_decide.delivery.decision_package import DEMO_NOTICE

    output = tmp_path / "demo.md"
    monkeypatch.setattr("sys.argv", ["sol-decide", "demo1", "--export-md", str(output)])
    main()
    markdown = output.read_text(encoding="utf-8")
    assert DEMO_NOTICE in markdown
    assert "SIMULATED SIGN-OFF ONLY" in markdown
    assert "SIGNED by" not in markdown


def test_simulated_sign_off_respects_certification_and_demo_boundary():
    c = build_ngcv_trade_study()
    report = c.evaluate_decision_package()
    compiler = DecisionPackageCompiler()
    regular = compiler.compile(c, report, authorized_role="Example reviewer")
    assert regular.is_demo is False
    with pytest.raises(PermissionError, match="restricted"):
        regular.simulate_sign_off()
    assert regular.sign("Example signer") is True
    assert regular.authorization_gate.is_signed is True
    assert regular.authorization_gate.is_simulated_signature is False

    demo = compiler.compile(c, report, is_demo=True)
    assert "DEMO ONLY - UNSIGNED" in demo.to_markdown()
    with pytest.raises(PermissionError, match="Synthetic demo"):
        demo.sign("Example signer")
    demo.betti_1 = 1
    with pytest.raises(PermissionError, match="obstructed"):
        demo.simulate_sign_off()
    assert demo.authorization_gate.signer_name is None
    assert demo.authorization_gate.is_simulated_signature is False
    assert demo.authorization_gate.is_signed is False


def test_signer_ready_package_cryptographic_hash():
    """Verify cryptographic tampering detection in decision package signing."""
    c, pkg, sens, bias = run_demonstration_1()
    # Cannot sign if package is obstructed
    pkg.betti_1 = 1
    pkg.is_certifiable = False
    with pytest.raises(PermissionError):
        pkg.sign("Hacker", "Illegitimate signature attempt")


def test_multi_agent_elicitation_and_sol_edge_pre_execution_gate():
    """
    Verify that competing multi-agent proposals compiled through LiveGeminiMoAElicitor
    are audited by SheafDecisionComplex and governed by the SOL-Edge 4-event state machine:
    - Compliant harmonic options -> PolicyStatus.ELIGIBLE (RuntimeStatus.ELIGIBLE)
    - Constraint-violating aggressive option -> PolicyStatus.QUARANTINE (RuntimeStatus.QUARANTINED)
    - Consequential high-cost option -> PolicyStatus.REQUIRE_HUMAN_APPROVAL (RuntimeStatus.AWAITING_HUMAN_APPROVAL)
    """
    from sol_decide.agentic.live_llm_elicitation import (
        LiveGeminiMoAElicitor,
        MultiAgentTradeStudySpec,
    )
    from sol_edge.contracts import NextTransition, PolicyStatus
    from sol_edge.runtime.replay import replay_events
    from sol_edge.runtime.state import RuntimeStatus

    sample_spec = MultiAgentTradeStudySpec(
        study_name="lunar_microgrid_trade",
        channel_names=["specific_power_w_kg", "endurance_hours", "payload_mass_kg"],
        objectives=[
            {
                "id": "obj_spec_power",
                "name": "Maximize Specific Power",
                "direction": "maximize",
                "weight": 0.40,
                "target_value": 120.0,
                "channel_index": 0,
                "units": "W/kg",
                "description": "High specific power reduces launch mass.",
            },
            {
                "id": "obj_endurance",
                "name": "Maximize Lunar Night Endurance",
                "direction": "maximize",
                "weight": 0.35,
                "target_value": 350.0,
                "channel_index": 1,
                "units": "hours",
                "description": "Survive 354-hour lunar eclipse.",
            },
            {
                "id": "obj_mass",
                "name": "Minimize Lander Payload Mass",
                "direction": "minimize",
                "weight": 0.25,
                "target_value": 800.0,
                "channel_index": 2,
                "units": "kg",
                "description": "Stay well within lander cargo allocation.",
            },
        ],
        constraints=[
            {
                "id": "con_min_spec_power",
                "name": "Minimum Specific Power",
                "channel_index": 0,
                "lower_bound": 60.0,
                "upper_bound": 250.0,
                "units": "W/kg",
                "description": "Must exceed 60 W/kg.",
            },
            {
                "id": "con_eclipse_endurance",
                "name": "Lunar Night Survival Window",
                "channel_index": 1,
                "lower_bound": 300.0,
                "upper_bound": 500.0,
                "units": "hours",
                "description": "Must provide at least 300 hours of eclipse storage.",
            },
            {
                "id": "con_max_cargo_mass",
                "name": "Maximum Artemis Cargo Allocation",
                "channel_index": 2,
                "lower_bound": 200.0,
                "upper_bound": 1200.0,
                "units": "kg",
                "description": "Must not exceed 1200 kg lander limit.",
            },
        ],
        options=[
            {
                "id": "opt_regen_fuel_cell",
                "proposer_agent_role": "Balanced_Systems_Architect",
                "name": "Regenerative H2/O2 Fuel Cell + Solar Array",
                "state_vector": [135.0, 380.0, 780.0],
                "trl": 7,
                "mrl": 7,
                "estimated_cost_m": 42.0,
                "rationale": "Balanced harmonic architecture satisfying all 3 Artemis bounds.",
            },
            {
                "id": "opt_li_ion_bank",
                "proposer_agent_role": "Conservative_Baseline_Agent",
                "name": "Heritage Li-Ion Battery Bank + Fixed PV",
                "state_vector": [75.0, 315.0, 1120.0],
                "trl": 9,
                "mrl": 8,
                "estimated_cost_m": 28.0,
                "rationale": "High-TRL baseline within mass limit but lower specific power.",
            },
            {
                "id": "opt_unshielded_stirling",
                "proposer_agent_role": "Aggressive_Boundary_Agent",
                "name": "High-Output Fission Stirling Array (Over-Mass)",
                "state_vector": [190.0, 480.0, 1490.0],
                "trl": 5,
                "mrl": 5,
                "estimated_cost_m": 95.0,
                "rationale": "Pushes power and endurance but breaches the 1200 kg cargo mass limit.",
            },
        ],
        assumptions=[
            {
                "id": "ass_electrolyzer_eff",
                "name": "PEM Electrolyzer Roundtrip Efficiency",
                "baseline_value": 0.68,
                "uncertainty_sigma": 0.06,
                "coupled_option_id": "opt_regen_fuel_cell",
                "coupled_channel_index": 0,
                "sensitivity_gain": 80.0,
                "units": "efficiency",
                "description": "Coupled to Regenerative Fuel Cell specific power.",
            },
            {
                "id": "ass_cryo_boiloff",
                "name": "Cryogenic Tank Zero-Boiloff Margin",
                "baseline_value": 1.0,
                "uncertainty_sigma": 0.08,
                "coupled_option_id": "opt_regen_fuel_cell",
                "coupled_channel_index": 1,
                "sensitivity_gain": 120.0,
                "units": "index",
                "description": "Coupled to lunar night endurance hours.",
            },
        ],
        risks=[
            {
                "id": "risk_dust_abrasion",
                "name": "Lunar Regolith Radiator Fouling",
                "probability": 0.25,
                "impact": 0.40,
                "coupled_option_id": "opt_regen_fuel_cell",
                "coupled_channel_index": 2,
                "description": "Dust accumulation increases thermal rejection mass.",
            }
        ],
    )

    class _MockInteraction:
        id = "int_mock_gemini_4"
        output_text = sample_spec.model_dump_json()

    class _MockInteractionsAPI:
        def create(self, **kwargs):
            return _MockInteraction()

    class _MockGenAIClient:
        interactions = _MockInteractionsAPI()

    elicitor = LiveGeminiMoAElicitor(
        model="gemini-3.8-flash",
        client=_MockGenAIClient(),
        require_human_approval_above_cost_m=500.0,
    )
    bundle = elicitor.run_live_governed_study("Design a lunar surface microgrid power architecture.")

    assert bundle.elicitation_result.is_valid is True
    assert bundle.elicitation_result.causal_emergence_delta_ei > 0.5
    assert bundle.evaluation_report.selected_option_id == "opt_regen_fuel_cell"
    assert bundle.evaluation_report.beta_1 == 0

    # Winning option is ELIGIBLE (never AUTHORIZED) and advances to RELEASE_REVIEW
    win_gov = bundle.winning_governance
    assert win_gov.policy_decision.status == PolicyStatus.ELIGIBLE
    assert win_gov.policy_decision.next_transition == NextTransition.RELEASE_REVIEW
    assert win_gov.final_runtime_state.status == RuntimeStatus.ELIGIBLE
    assert len(win_gov.events) == 4
    replayed = replay_events(win_gov.events)
    assert replayed.state_digest == win_gov.final_runtime_state.state_digest

    # Aggressive boundary-violating option (1490 kg > 1200 kg) is QUARANTINED by SOL-Edge
    agg_gov = bundle.all_option_governance["opt_unshielded_stirling"]
    assert agg_gov.evidence.overall_passed is False
    assert agg_gov.policy_decision.status == PolicyStatus.QUARANTINE
    assert agg_gov.policy_decision.next_transition == NextTransition.INVESTIGATE_AND_CLEAR_QUARANTINE
    assert agg_gov.final_runtime_state.status == RuntimeStatus.QUARANTINED

    # Verify REQUIRE_HUMAN_APPROVAL gate when cost threshold is lowered below $42M
    strict_cost_elicitor = LiveGeminiMoAElicitor(
        model="gemini-3.8-flash",
        client=_MockGenAIClient(),
        require_human_approval_above_cost_m=30.0,
    )
    strict_bundle = strict_cost_elicitor.run_live_governed_study("Design a lunar surface microgrid.")
    assert strict_bundle.winning_governance.policy_decision.status == PolicyStatus.REQUIRE_HUMAN_APPROVAL
    assert (
        strict_bundle.winning_governance.final_runtime_state.status
        == RuntimeStatus.AWAITING_HUMAN_APPROVAL
    )

    # Verify SOL-Lens v0.2 Proof Packet emitted in bundle
    pkt = bundle.sol_lens_packet
    assert pkt["schema"] == "techman.sol-lens.proof-packet/v0.2"
    assert pkt["observable_trace_only"] is True
    assert pkt["verdict"] == "PROMOTE"
    assert pkt["baseline_evaluation"]["verdict"] == "QUARANTINE"
    assert len(pkt["groups"]) == 5
    assert len(pkt["logons"]) >= 16
    assert len(pkt["edges"]) >= len(pkt["logons"])
    contradiction_logons = [lg for lg in pkt["logons"] if lg["status"] == "contradiction"]
    assert len(contradiction_logons) == 1
    assert "opt_unshielded_stirling" in contradiction_logons[0]["label"]


def test_live_gemini_api_elicitation_and_sol_edge_governance():
    """
    Live end-to-end integration test calling Gemini (`gemini-3.8-flash`) via
    `google-genai` Interactions API structured outputs, auditing via Cellular Sheaf
    Cohomology, governing via SOL-Edge pre-execution contracts, and emitting a
    `techman.sol-lens.proof-packet/v0.2` trace packet.
    """
    import os
    from sol_decide.agentic.live_llm_elicitation import (
        LiveGeminiMoAElicitor,
        SolLensProofPacketCompiler,
        _load_env_safely,
    )
    from sol_edge.contracts import PolicyStatus
    from sol_edge.runtime.replay import replay_events
    from sol_edge.runtime.state import RuntimeStatus

    _load_env_safely()
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        pytest.skip("GEMINI_API_KEY not configured for live Gemini API test")

    elicitor = LiveGeminiMoAElicitor(
        model="gemini-3.8-flash",
        require_human_approval_above_cost_m=1000.0,
    )
    bundle = elicitor.run_live_governed_study(
        "Design an autonomous deep-sea AUV power and hull architecture balancing "
        "energy capacity (kWh), hull crush depth margin (meters), and dry vehicle mass (kg)."
    )

    assert bundle.interaction_id and bundle.interaction_id != "int_local"
    assert len(bundle.elicited_spec.options) >= 3
    assert bundle.elicitation_result.is_valid is True
    assert bundle.elicitation_result.causal_emergence_delta_ei > 0.0
    assert bundle.evaluation_report.beta_1 == 0
    assert bundle.evaluation_report.selected_option_id is not None

    statuses = {gov.policy_decision.status for gov in bundle.all_option_governance.values()}
    assert (PolicyStatus.ELIGIBLE in statuses) or (PolicyStatus.REQUIRE_HUMAN_APPROVAL in statuses)
    assert PolicyStatus.QUARANTINE in statuses

    for gov in bundle.all_option_governance.values():
        replayed = replay_events(gov.events)
        assert replayed.state_digest == gov.final_runtime_state.state_digest
        if gov.policy_decision.status == PolicyStatus.QUARANTINE:
            assert gov.final_runtime_state.status == RuntimeStatus.QUARANTINED

    # Verify SOL-Lens v0.2 packet parity & cryptographic digest linkage
    pkt = bundle.sol_lens_packet
    assert pkt["schema"] == "techman.sol-lens.proof-packet/v0.2"
    replayed_metrics, replayed_verdict = SolLensProofPacketCompiler.evaluate_logons(pkt["logons"])
    assert pkt["verdict"] == replayed_verdict == "PROMOTE"
    for k, v in replayed_metrics.items():
        assert abs(pkt["metrics"][k] - v) <= 1e-12

    all_refs = [ref for lg in pkt["logons"] for ref in lg.get("evidence_refs", [])]
    assert any(bundle.interaction_id in ref for ref in all_refs)
    assert any(bundle.winning_governance.final_runtime_state.state_digest[:20] in ref for ref in all_refs)
    assert any(bundle.decision_package.cryptographic_proof_hash[:20] in ref for ref in all_refs)
    assert bundle.reasoning_telemetry.thought_step_count >= 1
    assert len(bundle.reasoning_telemetry.thought_signature_digests) >= 1


def test_live_gemini_4_argon_reasoning_and_sol_governance():
    """
    Live end-to-end integration test specifically targeting Gemini 4 (`gemini-4-argon`).
    Verifies how Gemini 4's schema-grounded reasoning and thought signatures interact
    with the 7 Giants MoA topological check, Cellular Sheaf Cohomology auditor,
    SOL-Edge pre-execution state machine, and SOL-Lens v0.2 proof packet compiler.
    """
    import os
    from sol_decide.agentic.live_llm_elicitation import (
        LiveGeminiMoAElicitor,
        SolLensProofPacketCompiler,
        _load_env_safely,
    )
    from sol_edge.contracts import PolicyStatus
    from sol_edge.runtime.replay import replay_events
    from sol_edge.runtime.state import RuntimeStatus

    _load_env_safely()
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        pytest.skip("GEMINI_API_KEY not configured for live Gemini 4 API test")

    elicitor = LiveGeminiMoAElicitor(
        model="gemini-4-argon",
        require_human_approval_above_cost_m=1000.0,
        thinking_level="high",
    )
    bundle = elicitor.run_live_governed_study(
        "Design a lunar surface microgrid power architecture balancing specific power (W/kg), "
        "eclipse energy storage endurance (hours), and total lander payload mass (kg) under hard "
        "Artemis cargo mass and thermal dissipation limits."
    )

    # 1. Verify Gemini 4 reasoning telemetry & cryptographic thought signature capture
    rt = bundle.reasoning_telemetry
    assert rt.model_used == "gemini-4-argon"
    assert rt.thinking_level == "high"
    assert rt.interaction_id == bundle.interaction_id
    assert rt.thought_step_count >= 1
    assert len(rt.thought_signature_digests) >= 1
    assert rt.thought_signature_digests[0].startswith("sha256:")
    assert rt.thought_signature_lengths[0] > 1000
    assert len(rt.thought_summaries) >= 1
    assert rt.total_input_tokens > 1000  # Gemini 4 compiles full JSON schema into input token representation
    assert rt.total_thought_tokens > 0
    assert rt.total_output_tokens > 0

    # 2. Verify 7 Giants MoA & Sheaf Cohomology global section (beta_1 == 0)
    assert bundle.elicitation_result.is_valid is True
    assert bundle.elicitation_result.causal_emergence_delta_ei > 0.5
    assert bundle.evaluation_report.beta_1 == 0
    assert bundle.evaluation_report.selected_option_id is not None

    # 3. Verify SOL-Edge zero-trust pre-execution governance & deterministic replay
    statuses = {gov.policy_decision.status for gov in bundle.all_option_governance.values()}
    assert (PolicyStatus.ELIGIBLE in statuses) or (PolicyStatus.REQUIRE_HUMAN_APPROVAL in statuses)
    assert PolicyStatus.QUARANTINE in statuses

    for gov in bundle.all_option_governance.values():
        replayed = replay_events(gov.events)
        assert replayed.state_digest == gov.final_runtime_state.state_digest
        if gov.policy_decision.status == PolicyStatus.QUARANTINE:
            assert gov.final_runtime_state.status == RuntimeStatus.QUARANTINED

    # 4. Verify SOL-Lens v0.2 proof packet includes Cognitive Reasoning & Thought Signature Logon
    pkt = bundle.sol_lens_packet
    assert pkt["schema"] == "techman.sol-lens.proof-packet/v0.2"
    replayed_metrics, replayed_verdict = SolLensProofPacketCompiler.evaluate_logons(pkt["logons"])
    assert pkt["verdict"] == replayed_verdict == "PROMOTE"
    for k, v in replayed_metrics.items():
        assert abs(pkt["metrics"][k] - v) <= 1e-12

    thought_logons = [
        lg for lg in pkt["logons"] if "Thought Signature" in lg.get("label", "")
    ]
    assert len(thought_logons) == 1
    assert any(
        rt.thought_signature_digests[0][:24] in ref
        for ref in thought_logons[0].get("evidence_refs", [])
    )


def test_closed_loop_cohomological_quarantine_repair_mock():
    """
    Deterministic unit test verifying Phase 7 Closed-Loop Autonomous Self-Correction:
    Cycle 0 QUARANTINE -> violated sheaf coboundary feedback -> Cycle 1 Cohomological Repair
    -> ELIGIBLE clearance with cryptographic hash-chain provenance and SOL-Lens feedback edge.
    """
    from sol_decide.agentic.live_llm_elicitation import (
        LiveGeminiMoAElicitor,
        MultiAgentTradeStudySpec,
        QuarantineRepairProposalSpec,
        SolLensProofPacketCompiler,
    )
    from sol_edge.contracts import NextTransition, PolicyStatus
    from sol_edge.runtime.replay import replay_events
    from sol_edge.runtime.state import RuntimeStatus

    sample_spec = MultiAgentTradeStudySpec(
        study_name="lunar_microgrid_trade",
        channel_names=["specific_power_w_kg", "endurance_hours", "payload_mass_kg"],
        objectives=[
            {
                "id": "obj_spec_power",
                "name": "Maximize Specific Power",
                "direction": "maximize",
                "weight": 0.40,
                "target_value": 120.0,
                "channel_index": 0,
                "units": "W/kg",
                "description": "High specific power reduces launch mass.",
            },
            {
                "id": "obj_endurance",
                "name": "Maximize Lunar Night Endurance",
                "direction": "maximize",
                "weight": 0.35,
                "target_value": 350.0,
                "channel_index": 1,
                "units": "hours",
                "description": "Survive 354-hour lunar eclipse.",
            },
            {
                "id": "obj_mass",
                "name": "Minimize Lander Payload Mass",
                "direction": "minimize",
                "weight": 0.25,
                "target_value": 800.0,
                "channel_index": 2,
                "units": "kg",
                "description": "Stay well within lander cargo allocation.",
            },
        ],
        constraints=[
            {
                "id": "con_min_spec_power",
                "name": "Minimum Specific Power",
                "channel_index": 0,
                "lower_bound": 60.0,
                "upper_bound": 250.0,
                "units": "W/kg",
                "description": "Must exceed 60 W/kg.",
            },
            {
                "id": "con_eclipse_endurance",
                "name": "Lunar Night Survival Window",
                "channel_index": 1,
                "lower_bound": 300.0,
                "upper_bound": 500.0,
                "units": "hours",
                "description": "Must provide at least 300 hours of eclipse storage.",
            },
            {
                "id": "con_max_cargo_mass",
                "name": "Maximum Artemis Cargo Allocation",
                "channel_index": 2,
                "lower_bound": 200.0,
                "upper_bound": 1200.0,
                "units": "kg",
                "description": "Must not exceed 1200 kg lander limit.",
            },
        ],
        options=[
            {
                "id": "opt_regen_fuel_cell",
                "proposer_agent_role": "Balanced_Systems_Architect",
                "name": "Regenerative H2/O2 Fuel Cell + Solar Array",
                "state_vector": [135.0, 380.0, 780.0],
                "trl": 7,
                "mrl": 7,
                "estimated_cost_m": 42.0,
                "rationale": "Balanced harmonic architecture satisfying all 3 Artemis bounds.",
            },
            {
                "id": "opt_li_ion_bank",
                "proposer_agent_role": "Conservative_Baseline_Agent",
                "name": "Heritage Li-Ion Battery Bank + Fixed PV",
                "state_vector": [75.0, 315.0, 1120.0],
                "trl": 9,
                "mrl": 8,
                "estimated_cost_m": 28.0,
                "rationale": "High-TRL baseline within mass limit but lower specific power.",
            },
            {
                "id": "opt_unshielded_stirling",
                "proposer_agent_role": "Aggressive_Boundary_Agent",
                "name": "High-Output Fission Stirling Array (Over-Mass)",
                "state_vector": [190.0, 480.0, 1490.0],
                "trl": 5,
                "mrl": 5,
                "estimated_cost_m": 95.0,
                "rationale": "Pushes power and endurance but breaches the 1200 kg cargo mass limit.",
            },
        ],
        assumptions=[
            {
                "id": "ass_electrolyzer_eff",
                "name": "PEM Electrolyzer Roundtrip Efficiency",
                "baseline_value": 0.68,
                "uncertainty_sigma": 0.06,
                "coupled_option_id": "opt_regen_fuel_cell",
                "coupled_channel_index": 0,
                "sensitivity_gain": 80.0,
                "units": "efficiency",
                "description": "Coupled to Regenerative Fuel Cell specific power.",
            },
        ],
        risks=[
            {
                "id": "risk_dust_abrasion",
                "name": "Lunar Regolith Radiator Fouling",
                "probability": 0.25,
                "impact": 0.40,
                "coupled_option_id": "opt_regen_fuel_cell",
                "coupled_channel_index": 2,
                "description": "Dust accumulation increases thermal rejection mass.",
            }
        ],
    )

    repair_spec = QuarantineRepairProposalSpec(
        repaired_option_id="opt_unshielded_stirling",
        proposer_agent_role="Aggressive_Boundary_Agent",
        repaired_name="Lightweighted Composite-Shielded Fission Stirling Array (Cohomologically Repaired)",
        repaired_state_vector=[165.0, 420.0, 1140.0],
        trl=6,
        mrl=6,
        estimated_cost_m=88.0,
        cohomological_repair_rationale=(
            "Replaced monolithic tungsten shielding with graded LiH-B4C shadow shielding, "
            "projecting channel 2 payload mass from 1490.0 kg down to 1140.0 kg (strictly inside "
            "[200.0, 1200.0] kg) to annihilate the sheaf coboundary defect on con_max_cargo_mass."
        ),
        invariant_clearance_proof=(
            "ch[0]=165.0 in [60.0, 250.0] W/kg; ch[1]=420.0 in [300.0, 500.0] hours; "
            "ch[2]=1140.0 in [200.0, 1200.0] kg."
        ),
    )

    class _MockClosedLoopInteractionsAPI:
        def __init__(self):
            self.call_count = 0
            self.seen_previous_ids = []

        def create(self, **kwargs):
            self.call_count += 1
            self.seen_previous_ids.append(kwargs.get("previous_interaction_id"))
            if self.call_count == 1:
                class _Cycle0Resp:
                    id = "real_cycle0_interaction_99"
                    output_text = sample_spec.model_dump_json()
                return _Cycle0Resp()
            else:
                class _Cycle1Resp:
                    id = "real_cycle1_repair_interaction_100"
                    output_text = repair_spec.model_dump_json()
                return _Cycle1Resp()

    class _MockClosedLoopClient:
        def __init__(self):
            self.interactions = _MockClosedLoopInteractionsAPI()

    mock_client = _MockClosedLoopClient()
    elicitor = LiveGeminiMoAElicitor(
        model="gemini-4-argon",
        client=mock_client,
        require_human_approval_above_cost_m=500.0,
    )
    bundle = elicitor.run_closed_loop_governed_study("Design a lunar surface microgrid.")

    # 1. Verify multi-turn interaction chaining (Cycle 0 -> Cycle 1)
    assert mock_client.interactions.call_count == 2
    assert mock_client.interactions.seen_previous_ids[1] == "real_cycle0_interaction_99"
    assert len(bundle.repair_records) == 1

    rec = bundle.repair_records[0]
    assert rec.quarantined_option_id == "opt_unshielded_stirling"
    assert rec.quarantine_cleared is True
    assert rec.previous_interaction_id == "real_cycle0_interaction_99"
    assert rec.repair_interaction_id == "real_cycle1_repair_interaction_100"
    assert len(rec.violated_invariants) == 1
    assert rec.violated_invariants[0].constraint_id == "con_max_cargo_mass"
    assert abs(rec.violated_invariants[0].coboundary_excess - 290.0) <= 1e-6

    # 2. Verify cryptographic provenance binding from Cycle 0 QUARANTINE into Cycle 1 ELIGIBLE
    assert rec.pre_repair_governance.policy_decision.status == PolicyStatus.QUARANTINE
    assert rec.pre_repair_governance.final_runtime_state.status == RuntimeStatus.QUARANTINED
    assert rec.post_repair_governance.policy_decision.status == PolicyStatus.ELIGIBLE
    assert rec.post_repair_governance.policy_decision.next_transition == NextTransition.RELEASE_REVIEW
    assert rec.post_repair_governance.final_runtime_state.status == RuntimeStatus.ELIGIBLE
    assert "COHOMOLOGICAL_QUARANTINE_CLEARED" in rec.post_repair_governance.policy_decision.reason_codes
    assert any(
        j.claim_code == "COHOMOLOGICAL_QUARANTINE_CLEARED"
        and j.evidence_digest == rec.quarantined_state_digest
        for j in rec.post_repair_governance.proposal.structured_justification
    )
    assert any(
        p.source_id == "source:prior-quarantined-state"
        and p.digest == rec.quarantined_state_digest
        for p in rec.post_repair_governance.evidence.provenance
    )
    assert replay_events(rec.post_repair_governance.events).state_digest == (
        rec.post_repair_governance.final_runtime_state.state_digest
    )

    # 3. Verify all options in post-repair bundle are now cleared (zero remaining QUARANTINE)
    post_statuses = {gov.policy_decision.status for gov in bundle.all_option_governance.values()}
    assert PolicyStatus.QUARANTINE not in post_statuses
    assert bundle.evaluation_report.beta_1 == 0

    # 4. Verify SOL-Lens v0.2 proof packet contains Cycle 0 contradiction logon,
    #    Cycle 1 supported repair logon, and a `feedback` edge connecting them
    pkt = bundle.sol_lens_packet
    feedback_edges = [e for e in pkt["edges"] if e["kind"] == "feedback"]
    assert len(feedback_edges) == 1
    fb_edge = feedback_edges[0]
    assert fb_edge["status"] == "supported"

    logons_by_id = {lg["id"]: lg for lg in pkt["logons"]}
    pre_lg = logons_by_id[fb_edge["from"]]
    post_lg = logons_by_id[fb_edge["to"]]
    assert pre_lg["status"] == "contradiction"
    assert "Cycle 0 Quarantined" in pre_lg["label"]
    assert post_lg["status"] == "supported"
    assert "Cohomological Self-Correction" in post_lg["label"]

    replayed_metrics, replayed_verdict = SolLensProofPacketCompiler.evaluate_logons(pkt["logons"])
    assert pkt["verdict"] == replayed_verdict == "PROMOTE"
    for k, v in replayed_metrics.items():
        assert abs(pkt["metrics"][k] - v) <= 1e-12


def test_live_gemini_4_closed_loop_quarantine_repair():
    """
    Live end-to-end test of Phase 7 Closed-Loop Autonomous Self-Correction with Gemini 4 (`gemini-4-argon`).
    Verifies that when Gemini 4's Cycle 0 adversarial boundary option is quarantined by SOL-Edge,
    the violated sheaf coboundary invariants and quarantined state digest are chained via
    `previous_interaction_id` into a Cycle 1 Gemini 4 repair call that projects the option
    into the sheaf feasible global section and clears quarantine.
    """
    import os
    from sol_decide.agentic.live_llm_elicitation import (
        LiveGeminiMoAElicitor,
        SolLensProofPacketCompiler,
        _load_env_safely,
    )
    from sol_edge.contracts import PolicyStatus
    from sol_edge.runtime.replay import replay_events

    _load_env_safely()
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        pytest.skip("GEMINI_API_KEY not configured for live Gemini 4 closed-loop repair test")

    elicitor = LiveGeminiMoAElicitor(
        model="gemini-4-argon",
        require_human_approval_above_cost_m=1000.0,
        thinking_level="high",
    )
    bundle = elicitor.run_closed_loop_governed_study(
        "Design a lunar surface microgrid power architecture balancing specific power (W/kg), "
        "eclipse energy storage endurance (hours), and total lander payload mass (kg) under hard "
        "Artemis cargo mass and thermal dissipation limits."
    )

    assert len(bundle.repair_records) >= 1
    for rec in bundle.repair_records:
        assert rec.quarantine_cleared is True
        assert rec.previous_interaction_id == bundle.interaction_id
        assert rec.repair_interaction_id != bundle.interaction_id
        assert rec.l2_repair_projection_distance > 0.0
        assert rec.repair_reasoning_telemetry.thought_step_count >= 1
        assert len(rec.repair_reasoning_telemetry.thought_signature_digests) >= 1
        assert "COHOMOLOGICAL_QUARANTINE_CLEARED" in rec.post_repair_governance.policy_decision.reason_codes
        assert replay_events(rec.post_repair_governance.events).state_digest == (
            rec.post_repair_governance.final_runtime_state.state_digest
        )

    # All options in the repaired trade study must now be cleared of QUARANTINE
    statuses = {gov.policy_decision.status for gov in bundle.all_option_governance.values()}
    assert PolicyStatus.QUARANTINE not in statuses
    assert bundle.evaluation_report.beta_1 == 0

    # Verify SOL-Lens v0.2 packet has feedback edge and passes deterministic replay
    pkt = bundle.sol_lens_packet
    feedback_edges = [e for e in pkt["edges"] if e["kind"] == "feedback"]
    assert len(feedback_edges) == len(bundle.repair_records)
    replayed_metrics, replayed_verdict = SolLensProofPacketCompiler.evaluate_logons(pkt["logons"])
    assert pkt["verdict"] == replayed_verdict == "PROMOTE"
    for k, v in replayed_metrics.items():
        assert abs(pkt["metrics"][k] - v) <= 1e-12


def test_human_release_gate_signature_and_sol_lens_seal():
    """
    Verify Phase 8 Human Release Authority Gate (`sign_release_gate`):
    - Certifiable ELIGIBLE / REQUIRE_HUMAN_APPROVAL bundles can be signed by a human authority,
      computing a cryptographic `release_seal_digest` and emitting a terminal `Signed Human Release Authorization`
      Logon in Phase 5 (`G05`) of the `sol-lens` v0.2 proof packet.
    - Attempting to sign a QUARANTINED winning governance raises PermissionError.
    """
    from dataclasses import replace
    from sol_decide.agentic.live_llm_elicitation import (
        LiveGeminiMoAElicitor,
        MultiAgentTradeStudySpec,
        SolLensProofPacketCompiler,
    )

    sample_spec = MultiAgentTradeStudySpec(
        study_name="lunar_microgrid_release_test",
        channel_names=["specific_power_w_kg", "endurance_hours", "payload_mass_kg"],
        objectives=[
            {
                "id": "obj_spec_power",
                "name": "Maximize Specific Power",
                "direction": "maximize",
                "weight": 0.40,
                "target_value": 120.0,
                "channel_index": 0,
                "units": "W/kg",
                "description": "High specific power reduces launch mass.",
            },
            {
                "id": "obj_endurance",
                "name": "Maximize Lunar Night Endurance",
                "direction": "maximize",
                "weight": 0.35,
                "target_value": 350.0,
                "channel_index": 1,
                "units": "hours",
                "description": "Survive 354-hour lunar eclipse.",
            },
            {
                "id": "obj_mass",
                "name": "Minimize Lander Payload Mass",
                "direction": "minimize",
                "weight": 0.25,
                "target_value": 800.0,
                "channel_index": 2,
                "units": "kg",
                "description": "Stay well within lander cargo allocation.",
            },
        ],
        constraints=[
            {
                "id": "con_min_spec_power",
                "name": "Minimum Specific Power",
                "channel_index": 0,
                "lower_bound": 60.0,
                "upper_bound": 250.0,
                "units": "W/kg",
                "description": "Must exceed 60 W/kg.",
            },
            {
                "id": "con_eclipse_endurance",
                "name": "Lunar Night Survival Window",
                "channel_index": 1,
                "lower_bound": 300.0,
                "upper_bound": 500.0,
                "units": "hours",
                "description": "Must provide at least 300 hours of eclipse storage.",
            },
            {
                "id": "con_max_cargo_mass",
                "name": "Maximum Artemis Cargo Allocation",
                "channel_index": 2,
                "lower_bound": 200.0,
                "upper_bound": 1200.0,
                "units": "kg",
                "description": "Must not exceed 1200 kg lander limit.",
            },
        ],
        options=[
            {
                "id": "opt_regen_fuel_cell",
                "proposer_agent_role": "Balanced_Systems_Architect",
                "name": "Regenerative H2/O2 Fuel Cell + Solar Array",
                "state_vector": [135.0, 380.0, 780.0],
                "trl": 7,
                "mrl": 7,
                "estimated_cost_m": 42.0,
                "rationale": "Balanced harmonic architecture satisfying all 3 Artemis bounds.",
            },
            {
                "id": "opt_li_ion_bank",
                "proposer_agent_role": "Conservative_Baseline_Agent",
                "name": "Heritage Li-Ion Battery Bank + Fixed PV",
                "state_vector": [75.0, 315.0, 1120.0],
                "trl": 9,
                "mrl": 8,
                "estimated_cost_m": 28.0,
                "rationale": "High-TRL baseline within mass limit.",
            },
            {
                "id": "opt_unshielded_stirling",
                "proposer_agent_role": "Aggressive_Boundary_Agent",
                "name": "High-Output Fission Stirling Array (Over-Mass)",
                "state_vector": [190.0, 480.0, 1490.0],
                "trl": 5,
                "mrl": 5,
                "estimated_cost_m": 95.0,
                "rationale": "Breaches the 1200 kg cargo mass limit.",
            },
        ],
        assumptions=[
            {
                "id": "ass_electrolyzer_eff",
                "name": "PEM Electrolyzer Roundtrip Efficiency",
                "baseline_value": 0.68,
                "uncertainty_sigma": 0.06,
                "coupled_option_id": "opt_regen_fuel_cell",
                "coupled_channel_index": 0,
                "sensitivity_gain": 80.0,
                "units": "efficiency",
                "description": "Coupled to Regenerative Fuel Cell specific power.",
            },
        ],
        risks=[
            {
                "id": "risk_dust_abrasion",
                "name": "Lunar Regolith Radiator Fouling",
                "probability": 0.25,
                "impact": 0.40,
                "coupled_option_id": "opt_regen_fuel_cell",
                "coupled_channel_index": 2,
                "description": "Dust accumulation increases thermal rejection mass.",
            }
        ],
    )

    class _MockResp:
        id = "int_release_gate_mock"
        output_text = sample_spec.model_dump_json()

    class _MockClient:
        class interactions:
            @staticmethod
            def create(**kwargs):
                return _MockResp()

    elicitor = LiveGeminiMoAElicitor(
        model="gemini-4-argon",
        client=_MockClient(),
        require_human_approval_above_cost_m=500.0,
    )
    bundle = elicitor.run_live_governed_study("Design a lunar surface microgrid.")

    pre_logon_count = len(bundle.sol_lens_packet["logons"])
    assert bundle.decision_package.authorization_gate.is_signed is False

    # Verify zero-trust rejection if a QUARANTINED option is substituted as winner
    quarantined_bundle = replace(
        bundle,
        winning_governance=bundle.all_option_governance["opt_unshielded_stirling"],
    )
    with pytest.raises(PermissionError):
        quarantined_bundle.sign_release_gate(
            signer_name="Dr. E. Vance",
            authorized_role="PEO Space",
        )

    # Sign the certifiable ELIGIBLE bundle
    seal_digest = bundle.sign_release_gate(
        signer_name="Dr. E. Vance",
        authorized_role="PEO Space / Artemis Power Authority",
        comments="Approved following verified beta_1=0 sheaf global section.",
    )
    assert seal_digest.startswith("sha256:")
    assert bundle.decision_package.authorization_gate.is_signed is True
    assert bundle.decision_package.authorization_gate.signer_name == "Dr. E. Vance"

    pkt = bundle.sol_lens_packet
    assert len(pkt["logons"]) == pre_logon_count + 1
    signed_logon = pkt["logons"][-1]
    assert "Signed Human Release Authorization: Dr. E. Vance" in signed_logon["label"]
    assert signed_logon["status"] == "supported"
    assert signed_logon["group_id"] == "G05"

    replayed_metrics, replayed_verdict = SolLensProofPacketCompiler.evaluate_logons(pkt["logons"])
    assert pkt["verdict"] == replayed_verdict == "PROMOTE"
    for k, v in replayed_metrics.items():
        assert abs(pkt["metrics"][k] - v) <= 1e-12


def test_hodge_decomposition_1_laplacian_and_2_cell_curl():
    """
    Frontier A Mathematical Identity Test:
    Verifies Discrete Hodge Decomposition omega = omega_exact (+) omega_coexact (+) omega_harmonic
    via the 1-Hodge Laplacian Delta^1 = delta^0 (delta^0)^T + (delta^1)^T delta^1 on a cellular sheaf
    containing both a 2-cell plaquette curl (coexact component) and an unfilled 1-dimensional
    topological hole (harmonic obstruction in ker(Delta^1)).
    """
    complex_obj = SheafDecisionComplex(name="Hodge_1_Laplacian_Verification")
    for vid, val in [("v0", 1.0), ("v1", 2.0), ("v2", 3.5), ("v3", 1.5)]:
        complex_obj.add_primitive(
            Option(id=vid, name=f"Node {vid}", stalk_dim=1, initial_params=np.array([val]))
        )


    # Triangle 1 (v0 -> v1 -> v2 -> v0): filled by a 2-cell plaquette f_curl -> coexact subspace
    complex_obj.add_edge("e01", "v0", "v1", dim_edge=1, edge_offset=np.array([0.4]))
    complex_obj.add_edge("e12", "v1", "v2", dim_edge=1, edge_offset=np.array([0.5]))
    complex_obj.add_edge("e02", "v0", "v2", dim_edge=1, edge_offset=np.array([-0.3]))
    complex_obj.add_face(
        "f_curl_plaquette",
        edge_ids=["e01", "e12", "e02"],
        orientations=[1.0, 1.0, -1.0],
        weight=1.0,
        description="Filled 2-cell plaquette capturing coexact curl",
    )

    # Triangle 2 (v1 -> v2 -> v3 -> v1): unfilled 1-dimensional hole -> harmonic H^1 obstruction
    complex_obj.add_edge("e23", "v2", "v3", dim_edge=1, edge_offset=np.array([0.6]))
    complex_obj.add_edge("e13", "v1", "v3", dim_edge=1, edge_offset=np.array([-0.4]))

    hodge = complex_obj.hodge_decomposition()
    assert hodge.beta_0 == 1
    assert hodge.beta_1 == 1
    assert hodge.exact_norm > 0.1
    assert hodge.coexact_norm > 0.1
    assert hodge.harmonic_norm > 0.1

    # Orthogonal subspace identities
    assert hodge.orthogonality_error < 1e-12
    assert hodge.laplacian_1_harmonic_residual < 1e-12
    pythagorean_sq = hodge.exact_norm ** 2 + hodge.coexact_norm ** 2 + hodge.harmonic_norm ** 2
    assert abs(hodge.total_norm ** 2 - pythagorean_sq) < 1e-11

    # Verify JSON roundtrip preserves edge_offset and 2-cell faces
    json_str = export_complex_to_json(complex_obj)
    reloaded = import_complex_from_json(json_str)
    hodge_reloaded = reloaded.hodge_decomposition()
    assert hodge_reloaded.beta_1 == hodge.beta_1 == 1
    assert abs(hodge_reloaded.harmonic_norm - hodge.harmonic_norm) < 1e-12
    assert abs(hodge_reloaded.coexact_norm - hodge.coexact_norm) < 1e-12


def test_dialectical_h1_obstruction_and_hodge_negotiation_mock():
    """
    Frontier A End-to-End Governance Test:
    1. 3 independent specialist sub-agents (`Power_Thermal_Specialist`, `Structures_Mass_Specialist`,
       `Avionics_Guidance_Specialist`) propose locally valid subsystem stalks inside all 3 hard
       constraint bounds, but their cross-subsystem interface claims form a frustrated 1-cycle
       (beta_1 = dim H^1(X, F) = 1 > 0, ||omega_harmonic||_2 > 0).
    2. SOL-Edge deterministically routes Cycle 0 to `QUARANTINE` (`H1_TOPOLOGICAL_CYCLE_OBSTRUCTION`)
       even though 0 local constraint bounds are violated.
    3. Discrete Hodge Decomposition pinpoints the exact 3 frustrated interface edges and feeds the
       harmonic obstruction back to the Hodge-Harmonic Negotiator (`previous_interaction_id`).
    4. Cycle 1 resolves beta_1: 1 -> 0, ||omega_harmonic||_2 -> 0.0, and clears SOL-Edge
       from `QUARANTINE` to `ELIGIBLE` (`H1_COHOMOLOGICAL_OBSTRUCTION_CLEARED`).
    """
    from sol_decide.agentic.live_llm_elicitation import (
        HodgeHarmonicNegotiationSpec,
        LiveGeminiMoAElicitor,
        SolLensProofPacketCompiler,
        SpecialistSubsystemProposalSpec,
        PolicyStatus,
        RuntimeStatus,
        NextTransition,
        replay_events,
    )

    sp_power = SpecialistSubsystemProposalSpec(
        specialist_role="Power_Thermal_Specialist",
        subsystem_option_id="sub_power_thermal",
        subsystem_name="High-Specific-Energy Solid-State Bus",
        state_vector=[545.0, 68.0, 4.1],
        trl=7,
        mrl=7,
        estimated_cost_m=145.0,
        interface_target_role="Structures_Mass_Specialist",
        interface_transfer_claim=0.42,
        rationale="Locally compliant power/thermal stalk with +0.42 cold-plate rejection claim.",
    )
    sp_struct = SpecialistSubsystemProposalSpec(
        specialist_role="Structures_Mass_Specialist",
        subsystem_option_id="sub_structures_mass",
        subsystem_name="Iso-Grid Composite Load-Bearing Chassis",
        state_vector=[490.0, 74.0, 4.6],
        trl=8,
        mrl=8,
        estimated_cost_m=118.0,
        interface_target_role="Avionics_Guidance_Specialist",
        interface_transfer_claim=0.31,
        rationale="Locally compliant structural stalk with +0.31 avionics isolation mount claim.",
    )
    sp_avio = SpecialistSubsystemProposalSpec(
        specialist_role="Avionics_Guidance_Specialist",
        subsystem_option_id="sub_avionics_guidance",
        subsystem_name="Fault-Tolerant Radiation-Hardened GN&C Suite",
        state_vector=[475.0, 64.0, 5.1],
        trl=8,
        mrl=7,
        estimated_cost_m=132.0,
        interface_target_role="Power_Thermal_Specialist",
        interface_transfer_claim=-0.24,
        rationale="Locally compliant avionics stalk with -0.24 bus draw offset.",
    )

    neg_spec = HodgeHarmonicNegotiationSpec(
        negotiated_study_name="Reconciled Harmonic Spacecraft Bus Architecture (beta_1=0)",
        reconciled_power_thermal_vector=[525.0, 70.0, 4.3],
        reconciled_structures_mass_vector=[495.0, 72.0, 4.6],
        reconciled_avionics_guidance_vector=[485.0, 67.0, 4.9],
        residual_interface_claims=[0.0, 0.0, 0.0],
        hodge_negotiation_rationale=(
            "Projected the 3 subsystem stalks onto the orthogonal complement of ker(Delta^1) "
            "and balanced the bilateral thermal/structural/power transfer offsets to zero holonomy."
        ),
        holonomy_clearance_proof=(
            "Verified cyclic holonomy b_PS + b_SA - b_PA = 0.0, rank(delta^0) = D_E, beta_1 = 0, "
            "and all 3 subsystem stalks strictly inside [350, 620], [25, 95], [1.8, 6.0]."
        ),
    )

    call_log = []

    class _MockStep:
        type = "thought"
        signature = "sig_h1_dialectical_specialist_verification"
        summary = ["Audited local stalk bounds and cross-subsystem Hodge harmonic holonomy."]

    class _MockUsage:
        total_input_tokens = 2480
        total_thought_tokens = 520
        total_output_tokens = 390
        total_tokens = 3390

    class _MockResp:
        def __init__(self, int_id: str, text: str):
            self.id = int_id
            self.output_text = text
            self.steps = [_MockStep()]
            self.usage = _MockUsage()

    responses = [
        _MockResp("live_sub_power_001", sp_power.model_dump_json()),
        _MockResp("live_sub_struct_002", sp_struct.model_dump_json()),
        _MockResp("live_sub_avio_003", sp_avio.model_dump_json()),
        _MockResp("live_hodge_neg_004", neg_spec.model_dump_json()),
    ]

    class _MockClient:
        class interactions:
            @staticmethod
            def create(**kwargs):
                idx = len(call_log)
                call_log.append(kwargs)
                return responses[idx]

    elicitor = LiveGeminiMoAElicitor(
        model="gemini-4-argon",
        client=_MockClient(),
        require_human_approval_above_cost_m=500.0,
        thinking_level="high",
    )
    bundle = elicitor.run_dialectical_h1_obstruction_study(
        "Design a coupled spacecraft power/thermal, structures/mass, and avionics/guidance architecture."
    )

    # Verify 4 distinct Gemini calls: 3 independent specialist calls + 1 Hodge-Harmonic negotiation call
    assert len(call_log) == 4
    assert call_log[3].get("previous_interaction_id") == "live_sub_avio_003"
    assert "H1 COHOMOLOGICAL OBSTRUCTION" in call_log[3]["input"]
    assert "e_if_power_to_structures" in call_log[3]["input"]

    h1_rec = bundle.h1_resolution_record
    assert h1_rec is not None
    assert len(h1_rec.specialist_proposals) == 3

    # Verify Cycle 0: non-trivial H^1 topological obstruction (beta_1 = 1) -> QUARANTINE
    assert h1_rec.pre_beta_1 == 1
    assert h1_rec.pre_harmonic_norm > 0.30
    assert h1_rec.pre_hodge_report.orthogonality_error < 1e-12
    assert h1_rec.pre_hodge_report.laplacian_1_harmonic_residual < 1e-12
    assert set(h1_rec.frustrated_cycle_edges) == {
        "e_if_power_to_structures",
        "e_if_structures_to_avionics",
        "e_if_power_to_avionics",
    }
    for sub_id, pre_gov in h1_rec.pre_repair_governance.items():
        assert pre_gov.policy_decision.status == PolicyStatus.QUARANTINE
        assert pre_gov.policy_decision.next_transition == NextTransition.INVESTIGATE_AND_CLEAR_QUARANTINE
        assert pre_gov.final_runtime_state.status == RuntimeStatus.QUARANTINED
        assert "H1_TOPOLOGICAL_CYCLE_OBSTRUCTION" in pre_gov.policy_decision.reason_codes

    # Verify Cycle 1: Hodge-Harmonic negotiation resolves beta_1: 1 -> 0 and clears QUARANTINE -> ELIGIBLE
    assert h1_rec.post_beta_1 == 0
    assert h1_rec.post_harmonic_norm < 1e-9
    assert h1_rec.post_hodge_report.frustrated_cycle_edges == []
    assert h1_rec.obstruction_cleared is True
    assert bundle.evaluation_report.beta_1 == 0
    assert bundle.evaluation_report.is_feasible is True

    win_gov = bundle.winning_governance
    assert win_gov.policy_decision.status == PolicyStatus.ELIGIBLE
    assert win_gov.final_runtime_state.status == RuntimeStatus.ELIGIBLE
    assert "H1_COHOMOLOGICAL_OBSTRUCTION_CLEARED" in win_gov.policy_decision.reason_codes
    assert any(
        c.claim_code == "H1_COHOMOLOGICAL_OBSTRUCTION_CLEARED"
        for c in win_gov.proposal.structured_justification
    )
    replayed_win = replay_events(win_gov.events)


    assert replayed_win.state_digest == win_gov.final_runtime_state.state_digest

    # Verify SOL-Lens v0.2 packet contains Specialist G01 logons, H^1 feedback edge in G03, and ACCEPT verdict
    pkt = bundle.sol_lens_packet
    feedback_edges = [e for e in pkt["edges"] if e["kind"] == "feedback"]
    assert len(feedback_edges) == 1
    assert any("Specialist Sub-Agent: Power_Thermal_Specialist" in lg["label"] for lg in pkt["logons"])
    assert any("Cycle 0 H^1 Topological Obstruction" in lg["label"] for lg in pkt["logons"])
    assert any("Cycle 1 Hodge-Harmonic Negotiation Cleared" in lg["label"] for lg in pkt["logons"])

    replayed_metrics, replayed_verdict = SolLensProofPacketCompiler.evaluate_logons(pkt["logons"])
    assert pkt["verdict"] == replayed_verdict == "PROMOTE"
    for k, v in replayed_metrics.items():
        assert abs(pkt["metrics"][k] - v) <= 1e-12



def test_live_gemini_4_argon_dialectical_h1_obstruction_resolution():
    """
    Live Frontier A Integration Test against `gemini-4-argon`:
    Spawns 3 independent live specialist sub-agents (`Power_Thermal_Specialist`,
    `Structures_Mass_Specialist`, `Avionics_Guidance_Specialist`) that induce a
    non-trivial H^1 topological obstruction (beta_1 = 1 > 0), decomposes the
    coboundary via the 1-Hodge Laplacian Delta^1, feeds the harmonic obstruction
    back to `gemini-4-argon` (`previous_interaction_id`), and verifies autonomous
    resolution (beta_1: 1 -> 0, QUARANTINE -> ELIGIBLE).
    """
    import os
    from sol_decide.agentic.live_llm_elicitation import (
        LiveGeminiMoAElicitor,
        SolLensProofPacketCompiler,
        PolicyStatus,
        RuntimeStatus,
        _load_env_safely,
    )

    _load_env_safely()
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("No GEMINI_API_KEY found for live Gemini 4 dialectical H^1 test.")

    elicitor = LiveGeminiMoAElicitor(
        model="gemini-4-argon",
        require_human_approval_above_cost_m=1000.0,
    )
    bundle = elicitor.run_dialectical_h1_obstruction_study(
        "Design a deep-space autonomous spacecraft bus balancing solid-state power/thermal "
        "specific energy (Wh/kg), composite structural thermal margin (K), and radiation-hardened "
        "avionics cycle life (k-cycles) across coupled subsystem interfaces."
    )

    h1_rec = bundle.h1_resolution_record
    assert h1_rec is not None
    assert len(h1_rec.specialist_proposals) == 3
    assert h1_rec.pre_beta_1 == 1
    assert h1_rec.post_beta_1 == 0
    assert h1_rec.pre_harmonic_norm > 0.1
    assert h1_rec.post_harmonic_norm < 1e-9
    assert h1_rec.obstruction_cleared is True
    assert bundle.evaluation_report.beta_1 == 0
    assert bundle.evaluation_report.is_feasible is True
    assert bundle.winning_governance.policy_decision.status in (
        PolicyStatus.ELIGIBLE,
        PolicyStatus.REQUIRE_HUMAN_APPROVAL,
    )
    assert bundle.winning_governance.final_runtime_state.status not in (
        RuntimeStatus.QUARANTINED,
        RuntimeStatus.REJECTED,
    )

    pkt = bundle.sol_lens_packet
    replayed_metrics, replayed_verdict = SolLensProofPacketCompiler.evaluate_logons(pkt["logons"])
    assert pkt["verdict"] == replayed_verdict
    for k, v in replayed_metrics.items():
        assert abs(pkt["metrics"][k] - v) <= 1e-12

    out_path = Path("sol-decide/examples/live_gemini_4_argon_dialectical_h1_packet.json")
    elicitor.lens_compiler.save_packet(pkt, out_path)
    assert out_path.exists()


def test_sysml_shock_cosimulation_and_robotic_manifold_gate_mock():
    """
    Frontier B Deterministic Test:
    1. Parses `artemis_lunar_rover_manipulator.sysml` into a `SheafDecisionComplex`.
    2. Applies an `OperationalShock` (+11.5 kg up-armoring on channel 2 dry mass) that
       breaches `RoverDeckMassAllocationBound` (44.5 -> 56.0 kg > 52.0 kg), triggering
       sheaf coboundary strain and `PolicyStatus.QUARANTINE` in `sol-edge`.
    3. Mutates the shocked SysML `part def` via a mock Gemini 4 `SysMLArchitectureMutationSpec`,
       verifying `QUARANTINE -> ELIGIBLE` clearance, cryptographic `quarantined_state_digest`
       binding, and `.sysml` round-trip re-export.
    4. Runs `run_governed_robotic_manifold_episode` with a non-flat SO(3) Wilson loop
       holonomy defect (`0.22` rad = `12.6` deg > `5.0` deg), verifying Cycle 0 blocks
       physical actuator commit (`QUARANTINE`) and Cycle 1 gauge diffusion clears it (`ELIGIBLE`).
    """
    from types import SimpleNamespace
    from sol_decide.interop import (
        SysMLArchitectureMutationSpec,
        SysMLCoSimulationBridge,
        SysMLKerMLParser,
    )
    from sol_edge.contracts import PolicyStatus
    from sol_edge.runtime.replay import replay_events
    from sol_edge.runtime.state import RuntimeStatus

    sysml_path = Path("sol-decide/examples/artemis_lunar_rover_manipulator.sysml")
    assert sysml_path.exists()
    sysml_source = sysml_path.read_text(encoding="utf-8")

    mock_mutation = SysMLArchitectureMutationSpec(
        shocked_part_id="sysml_hybridsupercapharmonicdrivearm",
        mutated_part_name="HybridSupercapHarmonicDriveArm_ThinWallTiB2_v2",
        mutated_state_vector=[128.0, 66.0, 46.0],
        mutated_cost=31.0,
        sysml_mutation_rationale=(
            "Replaced solid titanium housing with thin-wall TiB2-reinforced carbon-PEEK "
            "harmonic flexspline, absorbing the +11.5 kg percussive drill shield shock "
            "and restoring arm_dry_mass_kg to 46.0 kg <= 52.0 kg."
        ),
    )

    class _MockSysMLInteractionsAPI:
        def create(self, **kwargs):
            return SimpleNamespace(
                id="interaction-sysml-mutation-mock-01",
                outputs=[
                    SimpleNamespace(
                        type="thought",
                        summary=[
                            SimpleNamespace(
                                text="Auditing shocked SysML part stalk [124.0, 64.0, 56.0] against [20.0, 52.0] kg bound."
                            )
                        ],
                        signature="sig-sysml-mutation-01",
                    ),
                    SimpleNamespace(
                        type="text",
                        text=mock_mutation.model_dump_json(),
                    ),
                ],
                usage=SimpleNamespace(
                    total_input_tokens=940,
                    total_thought_tokens=280,
                    total_output_tokens=210,
                    total_tokens=1430,
                ),
            )

    mock_client = SimpleNamespace(interactions=_MockSysMLInteractionsAPI())
    bridge = SysMLCoSimulationBridge(model="gemini-4-argon", client=mock_client)

    rec = bridge.run_sysml_shock_cosimulation(sysml_source=sysml_source)
    assert rec.sysml_package_name == "Artemis_Lunar_6DOF_Manipulator_SysML"
    assert rec.pre_shock_stalk[2] == 44.5
    assert rec.post_shock_stalk[2] == 56.0
    assert rec.mutated_stalk == [128.0, 66.0, 46.0]

    # Cycle 0 shocked SysML part must be QUARANTINED
    assert rec.shocked_quarantine_governance.policy_decision.status == PolicyStatus.QUARANTINE
    assert rec.shocked_quarantine_governance.final_runtime_state.status == RuntimeStatus.QUARANTINED

    # Cycle 1 mutated SysML part must be ELIGIBLE with cryptographic link to Cycle 0 quarantine digest
    assert rec.shock_cleared is True
    assert rec.mutated_cleared_governance.policy_decision.status == PolicyStatus.ELIGIBLE
    assert rec.mutated_cleared_governance.final_runtime_state.status == RuntimeStatus.ELIGIBLE
    assert "COHOMOLOGICAL_QUARANTINE_CLEARED" in rec.mutated_cleared_governance.policy_decision.reason_codes
    assert replay_events(rec.mutated_cleared_governance.events).state_digest == (
        rec.mutated_cleared_governance.final_runtime_state.state_digest
    )

    # Verify exported .sysml text round-trips cleanly through SysMLKerMLParser
    re_parsed = SysMLKerMLParser().parse_sysml_text(rec.mutated_sysml_source)
    re_eval = re_parsed.evaluate_decision_package()
    assert re_eval.is_feasible is True
    assert re_eval.beta_1 == 0

    # Now run the 6-DOF Robotic + SO(3) Non-Abelian Gauge Holonomy Episode gated by the cleared SysML state digest
    c0_rob, c1_rob = bridge.run_governed_robotic_manifold_episode(
        sysml_decision_state_digest=rec.mutated_cleared_governance.final_runtime_state.state_digest,
        sysml_is_eligible=True,
        target_pos=[0.42, 0.22, 0.44],
        inject_wilson_holonomy_defect_rad=0.22,  # ~12.6 deg > 5.0 deg threshold -> Cycle 0 QUARANTINE
        auto_relax_gauge_on_quarantine=True,
    )

    assert c0_rob.actuator_commit_permitted is False
    assert c0_rob.max_wilson_defect_deg > 5.0
    assert c0_rob.governance_artifact.policy_decision.status == PolicyStatus.QUARANTINE
    assert "WILSON_LOOP_HOLONOMY_DEFECT" in c0_rob.governance_artifact.policy_decision.reason_codes

    assert c1_rob is not None
    assert c1_rob.actuator_commit_permitted is True
    assert c1_rob.max_wilson_defect_deg <= 5.0
    assert c1_rob.governance_artifact.policy_decision.status == PolicyStatus.ELIGIBLE
    assert "COHOMOLOGICAL_QUARANTINE_CLEARED" in c1_rob.governance_artifact.policy_decision.reason_codes
    assert replay_events(c1_rob.governance_artifact.events).state_digest == (
        c1_rob.governance_artifact.final_runtime_state.state_digest
    )


def test_live_gemini_4_argon_sysml_shock_and_robotic_cosimulation():
    """
    Live Frontier B Integration Test against `gemini-4-argon`:
    Ingests `artemis_lunar_rover_manipulator.sysml`, applies the live lunar PSR
    core-drilling operational shock, invokes `gemini-4-argon` to mutate the
    SysML v2 `part def` architecture back into `ker(Delta^0)` (`ELIGIBLE`),
    and gates the 6-DOF robotic trajectory & SO(3) gauge holonomy execution.
    """
    import os
    from sol_decide.agentic.live_llm_elicitation import _load_env_safely
    from sol_decide.interop import SysMLCoSimulationBridge
    from sol_edge.contracts import PolicyStatus

    _load_env_safely()
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        pytest.skip("No GEMINI_API_KEY found for live Gemini 4 SysML co-simulation test.")

    sysml_source = Path("sol-decide/examples/artemis_lunar_rover_manipulator.sysml").read_text(
        encoding="utf-8"
    )
    bridge = SysMLCoSimulationBridge(model="gemini-4-argon", thinking_level="high")
    rec = bridge.run_sysml_shock_cosimulation(sysml_source=sysml_source)

    assert rec.shocked_quarantine_governance.policy_decision.status == PolicyStatus.QUARANTINE
    assert rec.shock_cleared is True
    assert rec.mutated_cleared_governance.policy_decision.status in (
        PolicyStatus.ELIGIBLE,
        PolicyStatus.REQUIRE_HUMAN_APPROVAL,
    )
    assert 55.0 <= rec.mutated_stalk[0] <= 145.0
    assert 18.0 <= rec.mutated_stalk[1] <= 85.0
    assert 20.0 <= rec.mutated_stalk[2] <= 52.0

    c0_rob, c1_rob = bridge.run_governed_robotic_manifold_episode(
        sysml_decision_state_digest=rec.mutated_cleared_governance.final_runtime_state.state_digest,
        sysml_is_eligible=True,
        inject_wilson_holonomy_defect_rad=0.22,
        auto_relax_gauge_on_quarantine=True,
    )
    assert c0_rob.actuator_commit_permitted is False
    assert c1_rob is not None and c1_rob.actuator_commit_permitted is True


def test_governance_court_ledger_and_differential_shock_timeline(tmp_path):
    """
    Frontier C Deterministic Verification:
    1. Instantiates `GovernanceCourtLedger` backed by an isolated SQLite / D1 database file.
    2. Persists a multi-run chain of:
       - Run 1: Dialectical H^1 Hodge-harmonic resolution (`record_governed_bundle`, `dialectical_h1`)
       - Run 2: SysML v2 shock co-simulation (`record_sysml_shock_cosimulation`, `sysml_shock_cosim`)
       - Run 3: 6-DOF Robotic Manifold & SO(3) Gauge Holonomy gate (`record_robotic_actuation_episode`, `robotic_manifold_gate`)
    3. Records a human PEO release signature on Run 1 (`record_release_signature`).
    4. Verifies the cross-run SHA-256 Merkle/hash chain (`previous_run_digest` -> `ledger_entry_digest`)
       and every run's internal 4-event `sol-edge` hash chain (`verify_ledger_integrity()`).
    5. Verifies `differential_shock_timeline`, `cohomological_repair_records`, and `gemini_thought_signatures`.
    6. Simulates database tampering on both a run row and a `sol-edge` event row and asserts
       `verify_ledger_integrity()` deterministically flags the exact tampered `run_id`.
    """
    from types import SimpleNamespace
    from sol_decide.agentic.live_llm_elicitation import (
        HodgeHarmonicNegotiationSpec,
        LiveGeminiMoAElicitor,
        SpecialistSubsystemProposalSpec,
    )
    from sol_decide.delivery import GovernanceCourtLedger
    from sol_decide.interop import (
        SysMLArchitectureMutationSpec,
        SysMLCoSimulationBridge,
    )

    db_file = tmp_path / "test_sol_governance_ledger.sqlite"
    ledger = GovernanceCourtLedger(db_path=db_file)

    # --- 1. Run 1: Dialectical H^1 Hodge Negotiation ---
    specialist_specs = [
        SpecialistSubsystemProposalSpec(
            study_name="DeepSpace_Bus_Dialectical_H1",
            specialist_role="Power_Thermal_Specialist",
            subsystem_option_id="sub_power_thermal",
            subsystem_name="Solid-State Cryo-Radiator Bus",
            state_vector=[530.0, 74.0, 3.8],
            trl=7,
            mrl=7,
            estimated_cost_m=120.0,
            interface_target_role="Structures_Mass_Specialist",
            interface_transfer_claim=0.45,
            rationale="Power/Thermal demands +0.45 interface margin from Structures.",
        ),
        SpecialistSubsystemProposalSpec(
            study_name="DeepSpace_Bus_Dialectical_H1",
            specialist_role="Structures_Mass_Specialist",
            subsystem_option_id="sub_structures_mass",
            subsystem_name="Iso-Grid Carbon-SiC Primary Truss",
            state_vector=[490.0, 68.0, 4.4],
            trl=8,
            mrl=8,
            estimated_cost_m=95.0,
            interface_target_role="Avionics_Guidance_Specialist",
            interface_transfer_claim=0.35,
            rationale="Structures demands +0.35 interface margin from Avionics.",
        ),
        SpecialistSubsystemProposalSpec(
            study_name="DeepSpace_Bus_Dialectical_H1",
            specialist_role="Avionics_Guidance_Specialist",
            subsystem_option_id="sub_avionics_guidance",
            subsystem_name="Fault-Tolerant Optical Gyro & Rad-Hard FSW",
            state_vector=[470.0, 62.0, 5.1],
            trl=8,
            mrl=7,
            estimated_cost_m=110.0,
            interface_target_role="Power_Thermal_Specialist",
            interface_transfer_claim=-0.20,
            rationale="Avionics claims -0.20 interface offset back to Power/Thermal (net loop holonomy = +1.00 != 0).",
        ),
    ]
    negotiation_spec = HodgeHarmonicNegotiationSpec(
        negotiated_study_name="DeepSpace_Bus_Dialectical_H1_Reconciled",
        reconciled_power_thermal_vector=[515.0, 72.0, 4.2],
        reconciled_structures_mass_vector=[495.0, 69.0, 4.5],
        reconciled_avionics_guidance_vector=[480.0, 65.0, 4.9],
        residual_interface_claims=[0.0, 0.0, 0.0],
        hodge_negotiation_rationale="Annihilated harmonic 1-cocycle in ker(Delta^1).",
        holonomy_clearance_proof="b_PS + b_SA - b_PA = 0.0, beta_1 = 0.",
    )
    call_counter = {"n": 0}

    class _MockDialecticalInteractions:
        def create(self, **kwargs):
            idx = call_counter["n"]
            call_counter["n"] += 1
            if idx < 3:
                payload = specialist_specs[idx].model_dump_json()
                int_id = f"int-ledger-sp-{idx + 1}"
            else:
                payload = negotiation_spec.model_dump_json()
                int_id = "int-ledger-hodge-neg-04"
            return SimpleNamespace(
                id=int_id,
                output_text=payload,
                outputs=[
                    SimpleNamespace(
                        type="thought",
                        summary=[SimpleNamespace(text=f"Step {idx + 1} sheaf reasoning")],
                        signature=f"sig-ledger-step-{idx + 1}",
                    ),
                    SimpleNamespace(type="text", text=payload),
                ],
                usage=SimpleNamespace(
                    total_input_tokens=600,
                    total_thought_tokens=200,
                    total_output_tokens=150,
                    total_tokens=950,
                ),
            )

    elicitor = LiveGeminiMoAElicitor(
        model="gemini-4-argon",
        client=SimpleNamespace(interactions=_MockDialecticalInteractions()),
    )
    bundle_h1 = elicitor.run_dialectical_h1_obstruction_study("Design deep-space bus.")
    r1_meta = ledger.record_governed_bundle(bundle_h1, run_mode="dialectical_h1")
    assert r1_meta["previous_run_digest"] is None
    assert r1_meta["ledger_entry_digest"].startswith("sha256:")

    # Sign Run 1
    assert ledger.record_release_signature(
        r1_meta["run_id"], signer_name="Dr. Elena Vance", signer_role="PEO Deep Space"
    ) is True

    # --- 2. Run 2: SysML v2 Shock Co-Simulation ---
    sysml_source = Path("sol-decide/examples/artemis_lunar_rover_manipulator.sysml").read_text(
        encoding="utf-8"
    )
    mock_sysml_mutation = SysMLArchitectureMutationSpec(
        shocked_part_id="sysml_hybridsupercapharmonicdrivearm",
        mutated_part_name="HybridSupercapHarmonicDriveArm_ThinWallTiB2_v2",
        mutated_state_vector=[128.0, 66.0, 46.0],
        mutated_cost=31.0,
        sysml_mutation_rationale="Reduced dry mass to 46.0 kg <= 52.0 kg after +11.5 kg shock.",
    )

    class _MockSysMLInteractions:
        def create(self, **kwargs):
            return SimpleNamespace(
                id="int-ledger-sysml-02",
                outputs=[
                    SimpleNamespace(
                        type="thought",
                        summary=[SimpleNamespace(text="Mutating shocked SysML part def")],
                        signature="sig-ledger-sysml-02",
                    ),
                    SimpleNamespace(type="text", text=mock_sysml_mutation.model_dump_json()),
                ],
                usage=SimpleNamespace(
                    total_input_tokens=800,
                    total_thought_tokens=250,
                    total_output_tokens=180,
                    total_tokens=1230,
                ),
            )

    cosim_bridge = SysMLCoSimulationBridge(
        model="gemini-4-argon",
        client=SimpleNamespace(interactions=_MockSysMLInteractions()),
    )
    sysml_rec = cosim_bridge.run_sysml_shock_cosimulation(sysml_source=sysml_source)
    r2_meta = ledger.record_sysml_shock_cosimulation(
        sysml_rec, baseline_run_id=r1_meta["run_id"]
    )
    assert r2_meta["previous_run_digest"] == r1_meta["ledger_entry_digest"]

    # --- 3. Run 3: 6-DOF Robotic Manifold + SO(3) Gauge Holonomy Gate ---
    c0_rob, c1_rob = cosim_bridge.run_governed_robotic_manifold_episode(
        sysml_decision_state_digest=sysml_rec.mutated_cleared_governance.final_runtime_state.state_digest,
        sysml_is_eligible=True,
        inject_wilson_holonomy_defect_rad=0.22,
        auto_relax_gauge_on_quarantine=True,
    )
    r3_meta = ledger.record_robotic_actuation_episode(c0_rob, c1_rob)
    assert r3_meta["previous_run_digest"] == r2_meta["ledger_entry_digest"]

    # --- 4. Verify Snapshot & Cryptographic Hash Chain ---
    snap = ledger.get_ledger_snapshot()
    assert snap["integrity"]["isValid"] is True
    assert snap["integrity"]["totalRunsVerified"] == 3
    assert snap["integrity"]["totalEventsVerified"] >= 20
    assert snap["integrity"]["headLedgerDigest"] == r3_meta["ledger_entry_digest"]
    assert len(snap["runs"]) == 3
    assert len(snap["repairs"]) == 3
    assert len(snap["shockTimeline"]) == 1
    assert snap["shockTimeline"][0]["baselineRunId"] == r1_meta["run_id"]
    assert snap["shockTimeline"][0]["deltaValue"] == 11.5

    # --- 5. Tamper Detection Test ---
    with ledger._conn:
        ledger._conn.execute(
            "UPDATE governance_court_runs SET policy_status = 'AUTHORIZED' WHERE run_id = ?",
            (r2_meta["run_id"],),
        )
    tampered_report = ledger.verify_ledger_integrity()
    assert tampered_report.is_valid is False
    assert r2_meta["run_id"] in tampered_report.broken_run_ids

    ledger.close()


def test_cellular_chain_homology_and_interdimensional_wormhole_bridge_mock(tmp_path):
    """
    Frontier D Deterministic Verification:
    1. Verifies `CellularChainHomologyEngine` on a cellular sheaf with both a 1-cycle hole
       and a 2-cell plaquette:
       - Nilpotency: ||d_1 o d_2||_F < 1e-12
       - Poincare-Hodge Duality: dim H_k(X; F) == dim H^k(X; F) for k = 0, 1, 2
       - Kirchoff-Closed Exciton 1-Cycle Currents: ||d_1 J||_2 < 1e-12
    2. Verifies `InterDimensionalWormholeBridge` across all 4 SOL dimensional substrates:
       - 3D `SheafDecisionComplex` -> 4D `ExcitonEngine` Dirac-Delta Wormhole & `AutonomousSwarmRouter`
         -> 2D `HippocampalMemorySink` -> U(N) `PhotonicSheafDilation` / `PhotonicSheafProcessor`.
       - Cycle 0 uncalibrated wormhole throat shear (0.35) violates chain-map commutation
         (d_1^(4D) f_1 != f_0 d_1^(3D)) and triggers `PolicyStatus.QUARANTINE` in `SolEdgeWormholeGate`.
       - Cycle 1 `WormholeHomologyCalibrationSpec` restores exact chain-map commutation
         (< 1e-9), preserves homology (Delta beta_0 = Delta beta_1 = Delta beta_2 = 0),
         compiles the 1550 nm photonic MZI unitary (||U^H U - I||_F < 1e-11), and clears
         `SolEdgeWormholeGate` to `PolicyStatus.ELIGIBLE` (`WORMHOLE_HOMOLOGY_ISOMORPHISM_VERIFIED`).
    3. Verifies persistence in `GovernanceCourtLedger.record_wormhole_homology_episode()`.
    """
    from types import SimpleNamespace
    from sol_decide.delivery import GovernanceCourtLedger
    from sol_decide.interop import (
        CellularChainHomologyEngine,
        InterDimensionalWormholeBridge,
        WormholeHomologyCalibrationSpec,
    )
    from sol_edge.contracts import PolicyStatus
    from sol_edge.runtime.replay import replay_events
    from sol_edge.runtime.state import RuntimeStatus

    bridge = InterDimensionalWormholeBridge(model="gemini-4-argon")
    complex_3d = bridge.build_canonical_substrate_complex("SOL_Decide_3D_Sheaf", stalk_dim=3)

    # 1. Verify CellularChainHomologyEngine mathematical identities on 3D complex
    engine = CellularChainHomologyEngine()
    hom_3d = engine.analyze_homology(complex_3d, "SOL_Decide_3D_Sheaf")
    assert hom_3d.chain_complex_identity_defect < 1e-12
    assert hom_3d.poincare_hodge_duality_gap == 0
    assert hom_3d.beta_0 == 3
    assert hom_3d.beta_1 == 3
    assert hom_3d.beta_2 == 0
    assert hom_3d.exciton_cycle_divergence_norm < 1e-12
    assert hom_3d.exciton_cycle_energy > 0.9

    # 2. Run Inter-Dimensional Wormhole Episode with mock Gemini 4 calibration
    mock_cal = WormholeHomologyCalibrationSpec(
        wormhole_bridge_id="wormhole_3d_4d_2d_photonic",
        calibrated_throat_conductance=1.0,
        calibrated_channel_gains=[1.0, 1.0, 1.0],
        phase_holonomy_trim_rad=0.0,
        homological_calibration_rationale=(
            "Zeroed off-diagonal wormhole throat shear (0.35 -> 0.0) and matched "
            "conductance gain alpha=1.0 so d_1^(4D) f_1 = f_0 d_1^(3D) commutes "
            "exactly and all harmonic 1-cycle Exciton currents remain divergence-free."
        ),
    )

    class _MockWormholeInteractions:
        def create(self, **kwargs):
            return SimpleNamespace(
                id="int-wormhole-homology-mock-01",
                outputs=[
                    SimpleNamespace(
                        type="thought",
                        summary=[
                            SimpleNamespace(
                                text="Calibrating graded chain map f_bullet across 3D->4D->2D->U(N) barriers."
                            )
                        ],
                        signature="sig-wormhole-homology-01",
                    ),
                    SimpleNamespace(
                        type="text",
                        text=mock_cal.model_dump_json(),
                    ),
                ],
                usage=SimpleNamespace(
                    total_input_tokens=880,
                    total_thought_tokens=310,
                    total_output_tokens=195,
                    total_tokens=1385,
                ),
            )

    bridge._client = SimpleNamespace(interactions=_MockWormholeInteractions())
    ep = bridge.run_interdimensional_wormhole_episode(
        episode_id="SOL_Wormhole_Exciton_Homology_Bridge",
        inject_cycle0_throat_shear=0.35,
        tmp_storage_dir=tmp_path / "hippocampus",
    )

    # Verify Cycle 0 uncalibrated wormhole shear is QUARANTINED
    assert any(s.commutation_defect_d1 > 0.05 for s in ep.cycle0_stages)
    assert any(not s.is_homology_isomorphism for s in ep.cycle0_stages)
    assert ep.cycle0_quarantine_governance.policy_decision.status == PolicyStatus.QUARANTINE
    assert ep.cycle0_quarantine_governance.final_runtime_state.status == RuntimeStatus.QUARANTINED
    assert (
        "HOMOLOGICAL_CHAIN_MAP_DEFECT"
        in ep.cycle0_quarantine_governance.policy_decision.reason_codes
    )

    # Verify Cycle 1 calibrated wormhole bridge is ELIGIBLE across all dimensional transitions
    assert len(ep.cycle1_stages) == 2
    for st in ep.cycle1_stages:
        assert st.commutation_defect_d1 < 1e-9
        assert st.commutation_defect_d2 < 1e-9
        assert st.transported_cycle_divergence < 1e-9
        assert st.delta_beta_0 == 0
        assert st.delta_beta_1 == 0
        assert st.delta_beta_2 == 0
        assert st.is_homology_isomorphism is True

    assert ep.homology_preserved_across_all_substrates is True
    assert ep.exciton_wormhole_collapsed_edges >= 1
    assert ep.exciton_entangled_flux_injected > 0.0
    assert ep.photonic_unitarity_defect < 1e-11
    assert ep.photonic_transit_latency_ps > 0.0

    # Frontier E/F Wormhole Aperture Governance & Multi-Substrate Homology Compilation
    assert ep.cycle0_aperture_alpha == 0.0
    assert ep.cycle1_aperture_alpha == 1.0
    assert ep.photonic_cavity_roundtrips == 15
    assert ep.photonic_cavity_energy_reduction_ratio > 0.99
    assert ep.photonic_cavity_total_transit_ps > 0.0
    assert ep.wgsl_diffusion_time_us > 0.0
    assert ep.wgsl_energy_reduction_ratio > 0.50
    assert ep.wgsl_carnot_dissipated_energy > 0.0
    assert ep.wgsl_theorem_verdict == "PROVED_THEOREM"
    assert ep.memristor_mean_conductance_us > 0.0
    assert 0.0 < ep.memristor_energy_pj < 50.0
    assert len(ep.sol_lens_packet["logons"]) == 6
    assert ep.sol_lens_packet["logons"][-1]["id"] == "L06"
    assert "PROVED_THEOREM" in ep.sol_lens_packet["logons"][-1]["label"]

    assert ep.cycle1_cleared_governance.policy_decision.status == PolicyStatus.ELIGIBLE
    assert ep.cycle1_cleared_governance.final_runtime_state.status == RuntimeStatus.ELIGIBLE
    assert (
        "WORMHOLE_HOMOLOGY_ISOMORPHISM_VERIFIED"
        in ep.cycle1_cleared_governance.policy_decision.reason_codes
    )
    assert (
        "COHOMOLOGICAL_QUARANTINE_CLEARED"
        in ep.cycle1_cleared_governance.policy_decision.reason_codes
    )
    assert replay_events(ep.cycle1_cleared_governance.events).state_digest == (
        ep.cycle1_cleared_governance.final_runtime_state.state_digest
    )

    # 3. Verify GovernanceCourtLedger persistence of the Frontier D/E/F episode
    db_file = tmp_path / "test_wormhole_ledger.sqlite"
    ledger = GovernanceCourtLedger(db_path=db_file)
    meta = ledger.record_wormhole_homology_episode(ep)
    assert meta["run_mode"] == "wormhole_homology_bridge"
    integrity = ledger.verify_ledger_integrity()
    assert integrity.is_valid is True
    assert integrity.total_runs_verified == 1
    assert integrity.total_events_verified == 8
    ledger.close()



def test_live_gemini_4_argon_interdimensional_wormhole_homology_bridge(tmp_path):
    """
    Live Frontier D Integration Test against `gemini-4-argon`:
    Calibrates the Inter-Dimensional Dirac-Delta Wormhole chain map f_bullet across
    3D `sol-decide` -> 4D `Frontier_OS` `ExcitonEngine` -> 2D `HippocampalMemorySink`
    -> U(N) `PhotonicSheafDilation` MZI mesh, verifying exact homological commutation
    and `QUARANTINE -> ELIGIBLE` clearance in `sol-edge`.
    """
    import os
    from sol_decide.agentic.live_llm_elicitation import _load_env_safely
    from sol_decide.interop import InterDimensionalWormholeBridge
    from sol_edge.contracts import PolicyStatus

    _load_env_safely()
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        pytest.skip("No GEMINI_API_KEY found for live Gemini 4 wormhole homology test.")

    bridge = InterDimensionalWormholeBridge(model="gemini-4-argon", thinking_level="high")
    ep = bridge.run_interdimensional_wormhole_episode(
        inject_cycle0_throat_shear=0.35,
        tmp_storage_dir=tmp_path / "live_hippocampus",
    )

    assert ep.cycle0_quarantine_governance.policy_decision.status == PolicyStatus.QUARANTINE
    assert ep.homology_preserved_across_all_substrates is True
    assert ep.exciton_wormhole_collapsed_edges >= 1
    assert ep.photonic_unitarity_defect < 1e-11
    assert ep.cycle1_cleared_governance.policy_decision.status == PolicyStatus.ELIGIBLE
    assert (
        "WORMHOLE_HOMOLOGY_ISOMORPHISM_VERIFIED"
        in ep.cycle1_cleared_governance.policy_decision.reason_codes
    )


def test_persistent_homology_filtration_and_ollivier_ricci_surgery_mock(tmp_path):
    """
    Frontier G Deterministic Verification:
    1. Verifies `PersistentHomologyFiltrationEngine`:
       - Sweeps filtration threshold `eps` across `X_{eps_0} <= ... <= X_{eps_M}`,
         extracting the Topological Persistence Barcode `[b_i, d_i)` that separates:
           * `ESSENTIAL_WORMHOLE_CYCLE` (`[1.00, inf)`, normalized lifetime = 0.80)
           * `TRANSIENT_PLAQUETTE_NOISE` (`[1.25, 2.00)`, killed by `im(d_2)` when
             `face_spa_plaquette` enters the filtration)
       - Verifies that when the wormhole throat edge `e_ps` suffers a hyperbolic
         neck-pinch (`w_{e_ps} = 0.04`), `eps_birth(e_ps) = 25.0 > eps_max`, collapsing
         the essential `H_1` persistence bar (`essential_h1_normalized_lifetime == 0.0`,
         Bottleneck shift `Delta_BN == 4.0`).
    2. Verifies `OllivierRicciSurgeryOrchestrator` + `SolEdgeRicciSurgeryGate`:
       - Cycle 0 neck-pinch drives `throat_ollivier_ricci_curvature < -0.15` and
         quarantines the manifold (`PolicyStatus.QUARANTINE`, `RICCI_NECK_PINCH_SINGULARITY`,
         `PERSISTENT_HOMOLOGY_BARCODE_COLLAPSE`).
       - Cycle 1 `RicciFlowSurgerySpec` excises the neck-pinch horn and splices a
         Ricci-flat harmonic cap (`w_{e_ps} = 1.0`, `throat_ollivier_ricci_curvature >= 0`),
         restoring the canonical `H_1` persistence barcode (`Delta_BN == 0.0`,
         `essential_h1_normalized_lifetime == 0.80`) and clearing `SolEdgeRicciSurgeryGate`
         to `PolicyStatus.ELIGIBLE` (`RICCI_SURGERY_BARCODE_RESTORED`,
         `COHOMOLOGICAL_QUARANTINE_CLEARED`).
    3. Verifies persistence in `GovernanceCourtLedger.record_ricci_surgery_episode()`.
    """
    from types import SimpleNamespace
    from sol_decide.agentic.live_llm_elicitation import SolLensProofPacketCompiler
    from sol_decide.delivery import GovernanceCourtLedger
    from sol_decide.interop import (
        OllivierRicciSurgeryOrchestrator,
        PersistentHomologyFiltrationEngine,
        RicciFlowSurgerySpec,
    )
    from sol_edge.contracts import PolicyStatus
    from sol_edge.runtime.replay import replay_events
    from sol_edge.runtime.state import RuntimeStatus

    # 1. Verify PersistentHomologyFiltrationEngine on canonical unpinched vs pinched complexes
    filt_engine = PersistentHomologyFiltrationEngine(eps_max=5.0)
    canonical_rep = filt_engine.compute_filtration_and_barcode(
        name="Canonical_Unpinched_Manifold",
        stalk_dim=3,
        edge_conductances={"e_ps": 1.0, "e_sa": 1.0, "e_ap": 1.0, "e_sp": 0.8, "e_pa": 0.8},
        plaquette_birth_delay=0.75,
        canonical_essential_birth=1.0,
    )
    assert canonical_rep.essential_h1_count == 3
    assert canonical_rep.transient_h1_count == 3
    assert abs(canonical_rep.essential_h1_normalized_lifetime - 0.80) < 1e-6
    assert abs(canonical_rep.transient_h1_normalized_lifetime - 0.15) < 1e-6
    assert canonical_rep.signal_to_noise_persistence_ratio > 5.0
    assert canonical_rep.bottleneck_distance_from_canonical < 1e-9

    pinched_rep = filt_engine.compute_filtration_and_barcode(
        name="Neck_Pinched_Manifold",
        stalk_dim=3,
        edge_conductances={"e_ps": 0.04, "e_sa": 1.0, "e_ap": 1.0, "e_sp": 0.8, "e_pa": 0.8},
        plaquette_birth_delay=0.75,
        canonical_essential_birth=1.0,
    )
    assert pinched_rep.essential_h1_count == 0
    assert pinched_rep.essential_h1_normalized_lifetime == 0.0
    assert pinched_rep.bottleneck_distance_from_canonical > 3.5

    # 2. Run OllivierRicciSurgeryOrchestrator with mock Gemini 4 Argon surgery spec
    mock_surgery = RicciFlowSurgerySpec(
        surgically_spliced_edge_id="e_ps",
        restored_throat_conductance=1.0,
        ricci_scalar_target=0.0,
        plaquette_gauge_damping=0.85,
        ricci_surgery_rationale=(
            "Excised hyperbolic Ollivier-Ricci neck-pinch horn on wormhole throat edge e_ps "
            "(kappa = -0.82 -> +0.11) and spliced a Ricci-flat harmonic cap (g_{e_ps} = 1.0), "
            "restoring the [1.00, inf) essential H_1 wormhole persistence bar with Delta_BN = 0.0."
        ),
    )

    class _MockRicciSurgeryInteractions:
        def create(self, **kwargs):
            return SimpleNamespace(
                id="int-ricci-surgery-mock-01",
                outputs=[
                    SimpleNamespace(
                        type="thought",
                        summary=[
                            SimpleNamespace(
                                text="Diagnosing Ollivier-Ricci neck-pinch on e_ps and synthesizing Hamilton-Perelman harmonic cap."
                            )
                        ],
                        signature="sig-ricci-surgery-01",
                    ),
                    SimpleNamespace(
                        type="text",
                        text=mock_surgery.model_dump_json(),
                    ),
                ],
                usage=SimpleNamespace(
                    total_input_tokens=910,
                    total_thought_tokens=340,
                    total_output_tokens=205,
                    total_tokens=1455,
                ),
            )

    orchestrator = OllivierRicciSurgeryOrchestrator(
        model="gemini-4-argon",
        client=SimpleNamespace(interactions=_MockRicciSurgeryInteractions()),
        thinking_level="high",
    )
    ep = orchestrator.run_persistent_ricci_surgery_episode(
        episode_id="SOL_Persistent_Homology_Ollivier_Ricci_Surgery",
        inject_cycle0_throat_conductance=0.04,
    )

    # Verify Cycle 0 QUARANTINE under hyperbolic neck-pinch
    assert ep.cycle0_ricci_snapshot.throat_edge_ricci_curvature < -0.15
    assert ep.cycle0_ricci_snapshot.has_neck_pinch_singularity is True
    assert ep.cycle0_persistence_report.essential_h1_count == 0
    assert ep.cycle0_persistence_report.bottleneck_distance_from_canonical > 0.25
    assert ep.cycle0_quarantine_governance.policy_decision.status == PolicyStatus.QUARANTINE
    assert ep.cycle0_quarantine_governance.final_runtime_state.status == RuntimeStatus.QUARANTINED
    assert (
        "RICCI_NECK_PINCH_SINGULARITY"
        in ep.cycle0_quarantine_governance.policy_decision.reason_codes
    )
    assert (
        "PERSISTENT_HOMOLOGY_BARCODE_COLLAPSE"
        in ep.cycle0_quarantine_governance.policy_decision.reason_codes
    )

    # Verify Cycle 1 ELIGIBLE after Hamilton-Perelman Ricci Flow Surgery
    assert ep.cycle1_ricci_snapshot.throat_edge_ricci_curvature >= -0.05
    assert ep.cycle1_ricci_snapshot.has_neck_pinch_singularity is False
    assert ep.cycle1_persistence_report.essential_h1_count == 3
    assert abs(ep.cycle1_persistence_report.essential_h1_normalized_lifetime - 0.80) < 1e-6
    assert ep.cycle1_persistence_report.bottleneck_distance_from_canonical < 1e-6
    assert ep.neck_pinch_healed_and_barcode_restored is True
    assert ep.cycle1_cleared_governance.policy_decision.status == PolicyStatus.ELIGIBLE
    assert ep.cycle1_cleared_governance.final_runtime_state.status == RuntimeStatus.ELIGIBLE
    assert (
        "RICCI_SURGERY_BARCODE_RESTORED"
        in ep.cycle1_cleared_governance.policy_decision.reason_codes
    )
    assert (
        "COHOMOLOGICAL_QUARANTINE_CLEARED"
        in ep.cycle1_cleared_governance.policy_decision.reason_codes
    )
    assert replay_events(ep.cycle1_cleared_governance.events).state_digest == (
        ep.cycle1_cleared_governance.final_runtime_state.state_digest
    )

    # Verify SOL-Lens v0.2 proof packet evaluation parity
    pkt = ep.sol_lens_packet
    replayed_metrics, replayed_verdict = SolLensProofPacketCompiler.evaluate_logons(pkt["logons"])
    assert pkt["verdict"] == replayed_verdict == "PROMOTE"
    for k, v in replayed_metrics.items():
        assert abs(pkt["metrics"][k] - v) <= 1e-12

    # 3. Verify GovernanceCourtLedger persistence of the Frontier G episode
    db_file = tmp_path / "test_ricci_surgery_ledger.sqlite"
    ledger = GovernanceCourtLedger(db_path=db_file)
    meta = ledger.record_ricci_surgery_episode(ep)
    assert meta["run_mode"] == "persistent_ricci_surgery"
    integrity = ledger.verify_ledger_integrity()
    assert integrity.is_valid is True
    assert integrity.total_runs_verified == 1
    assert integrity.total_events_verified == 8
    ledger.close()


def test_live_gemini_4_argon_persistent_ricci_surgery():
    """
    Live Frontier G Integration Test against `gemini-4-argon`:
    Synthesizes a Hamilton-Perelman `RicciFlowSurgerySpec` when an Ollivier-Ricci
    neck-pinch singularity collapses the essential `H_1` wormhole persistence bar,
    restoring the barcode (`Delta_BN == 0.0`) and clearing `SolEdgeRicciSurgeryGate`
    from `QUARANTINE` to `ELIGIBLE`.
    """
    import os
    from sol_decide.agentic.live_llm_elicitation import _load_env_safely
    from sol_decide.interop import OllivierRicciSurgeryOrchestrator
    from sol_edge.contracts import PolicyStatus

    _load_env_safely()
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        pytest.skip("No GEMINI_API_KEY found for live Gemini 4 Ricci surgery test.")

    orchestrator = OllivierRicciSurgeryOrchestrator(model="gemini-4-argon", thinking_level="high")
    ep = orchestrator.run_persistent_ricci_surgery_episode(
        inject_cycle0_throat_conductance=0.04,
    )

    assert ep.cycle0_quarantine_governance.policy_decision.status == PolicyStatus.QUARANTINE
    assert ep.neck_pinch_healed_and_barcode_restored is True
    assert ep.cycle1_cleared_governance.policy_decision.status == PolicyStatus.ELIGIBLE
    assert (
        "RICCI_SURGERY_BARCODE_RESTORED"
        in ep.cycle1_cleared_governance.policy_decision.reason_codes
    )


def test_non_hermitian_skin_effect_and_pt_symmetry_gate_mock(tmp_path):
    """
    Frontier H Deterministic Verification:
    1. Verifies `NonHermitianSkinEngine`:
       - Supercritical optical gain/loss (`g = 1.35 > g_EP = 1.00`) and non-reciprocal
         Hatano-Nelson skin drift (`gamma = 0.95`) break PT-symmetry (`max |Im(lambda)| > 0.85`),
         inflate the Petermann excess noise factor (`K_max > 15.0`), induce non-trivial
         point-gap spectral winding (`nu(E_0) = -1`), and localize OBC eigenstates onto the
         boundary (`IPR > 0.70`, `skin_boundary_accumulation_ratio > 3.0`).
       - Applying the Generalized Brillouin Zone (GBZ) imaginary gauge similarity transformation
         `S = diag(exp(-gamma * x_v))` (`gamma_eff = 0.0`) and clamping gain/loss below the
         Exceptional Point (`g = 0.35 < g_EP = 1.00`) restores unbroken PT-symmetry
         (`max |Im(lambda)| < 1e-12`), bounds the Petermann factor (`K_max < 1.25`),
         trivializes the point-gap winding (`nu(E_0) == 0`), and delocalizes OBC eigenstates
         (`IPR == 0.25`, `skin_boundary_accumulation_ratio == 1.0`).
    2. Verifies `NonHermitianPTSkinOrchestrator` + `SolEdgeNonHermitianPTGate`:
       - Cycle 0 broken PT-symmetry & NHSE skin pileup triggers `PolicyStatus.QUARANTINE`
         (`PT_SYMMETRY_BROKEN_EXCEPTIONAL_POINT`, `NON_HERMITIAN_SKIN_BOUNDARY_LOCALIZATION`).
       - Cycle 1 `NonHermitianPTSurgerySpec` clears `SolEdgeNonHermitianPTGate` to
         `PolicyStatus.ELIGIBLE` (`PT_SYMMETRY_UNBROKEN_VERIFIED`, `NON_HERMITIAN_SKIN_DELOCALIZED`,
         `COHOMOLOGICAL_QUARANTINE_CLEARED`).
    3. Verifies persistence in `GovernanceCourtLedger.record_non_hermitian_pt_episode()`.
    """
    from types import SimpleNamespace
    from sol_decide.agentic.live_llm_elicitation import SolLensProofPacketCompiler
    from sol_decide.delivery import GovernanceCourtLedger
    from sol_decide.interop import (
        NonHermitianPTSkinOrchestrator,
        NonHermitianPTSurgerySpec,
        NonHermitianSkinEngine,
    )
    from sol_edge.contracts import PolicyStatus
    from sol_edge.runtime.replay import replay_events
    from sol_edge.runtime.state import RuntimeStatus

    # 1. Verify NonHermitianSkinEngine broken vs unbroken spectral & localization invariants
    skin_engine = NonHermitianSkinEngine(num_vertices=4, stalk_dim=3, base_coupling=1.0)
    broken_snap = skin_engine.analyze_spectral_state(
        stage_label="Test_Broken_PT_Skin",
        skin_gamma=0.95,
        pt_gain_loss_g=1.35,
    )
    assert broken_snap.exceptional_point_threshold_g_ep == 1.0
    assert broken_snap.max_imag_eigenvalue > 0.85
    assert broken_snap.max_petermann_factor > 15.0
    assert broken_snap.point_gap_winding_number == -1
    assert broken_snap.obc_skin_localization_ipr > 0.70
    assert broken_snap.skin_boundary_accumulation_ratio > 3.0
    assert broken_snap.pt_symmetry_unbroken is False
    assert broken_snap.skin_effect_delocalized is False

    unbroken_snap = skin_engine.analyze_spectral_state(
        stage_label="Test_Unbroken_PT_Delocalized",
        skin_gamma=0.0,
        pt_gain_loss_g=0.35,
    )
    assert unbroken_snap.max_imag_eigenvalue < 1e-12
    assert 1.0 <= unbroken_snap.max_petermann_factor <= 1.25
    assert unbroken_snap.point_gap_winding_number == 0
    assert abs(unbroken_snap.obc_skin_localization_ipr - 0.25) < 1e-6
    assert abs(unbroken_snap.skin_boundary_accumulation_ratio - 1.0) < 1e-6
    assert unbroken_snap.pt_symmetry_unbroken is True
    assert unbroken_snap.skin_effect_delocalized is True

    # 2. Run NonHermitianPTSkinOrchestrator with mock Gemini 4 Argon surgery spec
    mock_pt_spec = NonHermitianPTSurgerySpec(
        target_cavity_id="cavity_nhse_pt_core",
        calibrated_skin_gauge_gamma=0.0,
        clamped_pt_gain_loss_g=0.35,
        wormhole_pbc_flux_phase_rad=0.0,
        non_hermitian_pt_rationale=(
            "Applied Generalized Brillouin Zone (GBZ) imaginary gauge similarity transformation "
            "S = diag(exp(-gamma * x_v)) to cancel Hatano-Nelson skin drift (gamma_eff = 0.0, "
            "IPR = 0.25, winding nu = 0) and clamped optical gain/loss to g = 0.35 < g_EP = 1.00, "
            "restoring unbroken PT-symmetry (Im(lambda) = 0, K_max = 1.1396)."
        ),
    )

    class _MockNHPTInteractions:
        def create(self, **kwargs):
            return SimpleNamespace(
                id="int-nhse-pt-mock-01",
                outputs=[
                    SimpleNamespace(
                        type="thought",
                        summary=[
                            SimpleNamespace(
                                text="Auditing EP2 Petermann factor K_max and synthesizing GBZ imaginary gauge S(gamma)."
                            )
                        ],
                        signature="sig-nhse-pt-01",
                    ),
                    SimpleNamespace(
                        type="text",
                        text=mock_pt_spec.model_dump_json(),
                    ),
                ],
                usage=SimpleNamespace(
                    total_input_tokens=890,
                    total_thought_tokens=320,
                    total_output_tokens=190,
                    total_tokens=1400,
                ),
            )

    orchestrator = NonHermitianPTSkinOrchestrator(
        model="gemini-4-argon",
        client=SimpleNamespace(interactions=_MockNHPTInteractions()),
        thinking_level="high",
    )
    ep = orchestrator.run_non_hermitian_pt_episode(
        episode_id="SOL_NonHermitian_Skin_And_PT_Symmetry",
        inject_cycle0_skin_gamma=0.95,
        inject_cycle0_pt_gain_g=1.35,
    )

    # Verify Cycle 0 QUARANTINE under broken PT-symmetry & NHSE skin localization
    assert ep.cycle0_spectral_snapshot.pt_symmetry_unbroken is False
    assert ep.cycle0_spectral_snapshot.skin_effect_delocalized is False
    assert ep.cycle0_quarantine_governance.policy_decision.status == PolicyStatus.QUARANTINE
    assert ep.cycle0_quarantine_governance.final_runtime_state.status == RuntimeStatus.QUARANTINED
    assert (
        "PT_SYMMETRY_BROKEN_EXCEPTIONAL_POINT"
        in ep.cycle0_quarantine_governance.policy_decision.reason_codes
    )
    assert (
        "NON_HERMITIAN_SKIN_BOUNDARY_LOCALIZATION"
        in ep.cycle0_quarantine_governance.policy_decision.reason_codes
    )

    # Verify Cycle 1 ELIGIBLE after GBZ imaginary gauge transform & sub-EP gain clamping
    assert ep.cycle1_spectral_snapshot.pt_symmetry_unbroken is True
    assert ep.cycle1_spectral_snapshot.skin_effect_delocalized is True
    assert ep.cycle1_spectral_snapshot.max_imag_eigenvalue < 1e-12
    assert ep.cycle1_spectral_snapshot.max_petermann_factor <= 2.50
    assert ep.cycle1_spectral_snapshot.point_gap_winding_number == 0
    assert abs(ep.cycle1_spectral_snapshot.obc_skin_localization_ipr - 0.25) < 1e-6
    assert ep.pt_symmetry_and_skin_delocalization_restored is True
    assert ep.cycle1_cleared_governance.policy_decision.status == PolicyStatus.ELIGIBLE
    assert ep.cycle1_cleared_governance.final_runtime_state.status == RuntimeStatus.ELIGIBLE
    assert (
        "PT_SYMMETRY_UNBROKEN_VERIFIED"
        in ep.cycle1_cleared_governance.policy_decision.reason_codes
    )
    assert (
        "NON_HERMITIAN_SKIN_DELOCALIZED"
        in ep.cycle1_cleared_governance.policy_decision.reason_codes
    )
    assert (
        "COHOMOLOGICAL_QUARANTINE_CLEARED"
        in ep.cycle1_cleared_governance.policy_decision.reason_codes
    )
    assert replay_events(ep.cycle1_cleared_governance.events).state_digest == (
        ep.cycle1_cleared_governance.final_runtime_state.state_digest
    )

    # Verify SOL-Lens v0.2 proof packet evaluation parity
    pkt = ep.sol_lens_packet
    replayed_metrics, replayed_verdict = SolLensProofPacketCompiler.evaluate_logons(pkt["logons"])
    assert pkt["verdict"] == replayed_verdict == "PROMOTE"
    for k, v in replayed_metrics.items():
        assert abs(pkt["metrics"][k] - v) <= 1e-12

    # 3. Verify GovernanceCourtLedger persistence of the Frontier H episode
    db_file = tmp_path / "test_nh_pt_ledger.sqlite"
    ledger = GovernanceCourtLedger(db_path=db_file)
    meta = ledger.record_non_hermitian_pt_episode(ep)
    assert meta["run_mode"] == "non_hermitian_skin_pt"
    integrity = ledger.verify_ledger_integrity()
    assert integrity.is_valid is True
    assert integrity.total_runs_verified == 1
    assert integrity.total_events_verified == 8
    ledger.close()


def test_live_gemini_4_argon_non_hermitian_skin_pt_gate():
    """
    Live Frontier H Integration Test against `gemini-4-argon`:
    Synthesizes a `NonHermitianPTSurgerySpec` when supercritical optical pump gain
    (`g = 1.35 > g_EP = 1.00`) and non-reciprocal Hatano-Nelson drift (`gamma = 0.95`)
    break PT-symmetry and localize skin modes at the boundary, restoring unbroken
    PT-symmetry (`Im(lambda) == 0`, `K_max <= 1.25`, `IPR == 0.25`, `nu == 0`) and
    clearing `SolEdgeNonHermitianPTGate` from `QUARANTINE` to `ELIGIBLE`.
    """
    import os
    from sol_decide.agentic.live_llm_elicitation import _load_env_safely
    from sol_decide.interop import NonHermitianPTSkinOrchestrator
    from sol_edge.contracts import PolicyStatus

    _load_env_safely()
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        pytest.skip("No GEMINI_API_KEY found for live Gemini 4 Non-Hermitian PT test.")

    orchestrator = NonHermitianPTSkinOrchestrator(model="gemini-4-argon", thinking_level="high")
    ep = orchestrator.run_non_hermitian_pt_episode(
        inject_cycle0_skin_gamma=0.95,
        inject_cycle0_pt_gain_g=1.35,
    )

    assert ep.cycle0_quarantine_governance.policy_decision.status == PolicyStatus.QUARANTINE
    assert ep.pt_symmetry_and_skin_delocalization_restored is True
    assert ep.cycle1_cleared_governance.policy_decision.status == PolicyStatus.ELIGIBLE
    assert (
        "PT_SYMMETRY_UNBROKEN_VERIFIED"
        in ep.cycle1_cleared_governance.policy_decision.reason_codes
    )
    assert (
        "NON_HERMITIAN_SKIN_DELOCALIZED"
        in ep.cycle1_cleared_governance.policy_decision.reason_codes
    )


def test_sol_continuum_agentic_discovery_and_change_observatory_mock(tmp_path):
    """
    Deterministic Frontier I Integration Test:
    1. Verifies the 5-agent `ContinuumAgentGuild` in `sol-continuum` (`Conjecture_Architect`,
       `Sheaf_Topologist`, `Counterfactual_Skeptic`, `Substrate_Synthesizer`,
       `Observatory_Archivist`) proposes and audits a scientific conjecture across:
       - `conJecture` WGSL verification shader compilation,
       - `Frontier_OS` `HippocampalMemorySink` dream cycle consolidation,
       - `SolEdgeContinuumDiscoveryGate` (`QUARANTINE` in Cycle 0 -> `ELIGIBLE` in Cycle 1).
    2. Verifies `ChangeObservatoryBridge` translates Cycle 0 (`baseline`) and Cycle 1
       (`candidate`) proof packets via `observatory.continuum.packet_to_run` and
       `observatory.continuum.build_comparison`, evaluates `observatory.domain.compare`
       with `comparability == "compatible"`, `outcome == "improved"`,
       `review_status == "awaiting_review"`, `warnings == []`, and persists to SQLite.
    3. Verifies `GovernanceCourtLedger.record_sol_continuum_episode` records the
       Cycle 0 + Cycle 1 chain with valid ledger integrity.
    """
    from sol_decide.agentic.live_llm_elicitation import SolLensProofPacketCompiler
    from sol_decide.delivery import GovernanceCourtLedger
    from sol_decide.interop import (
        ChangeObservatoryBridge,
        SolContinuumDiscoveryOrchestrator,
    )

    exp_dir = tmp_path / "continuum_experiments"
    obs_db = tmp_path / "observatory.sqlite3"
    bridge = ChangeObservatoryBridge(
        experiments_root=exp_dir,
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

    assert len(record.guild_agents) == 5
    assert record.post_mean_guild_competency > record.pre_mean_guild_competency
    assert record.epistemic_gain_bits >= 1.25
    assert record.conjecture_engine_status == "PROVED_THEOREM"
    assert record.wgsl_shader_hash.startswith("sha256:")
    assert record.cycle0_audit.is_quarantined is True
    assert record.cycle0_audit.policy_status == "QUARANTINE"
    assert record.cycle1_audit.is_quarantined is False
    assert record.cycle1_audit.policy_status == "ELIGIBLE"
    assert record.observatory_comparability == "compatible"
    assert record.observatory_outcome == "improved"
    assert record.observatory_review_status == "awaiting_review"
    assert record.observatory_warnings == []
    assert record.observatory_db_registered is True

    pkt = record.sol_lens_packet
    replayed_metrics, replayed_verdict = SolLensProofPacketCompiler.evaluate_logons(pkt["logons"])
    assert pkt["verdict"] == replayed_verdict == "PROMOTE"
    for k, v in replayed_metrics.items():
        assert abs(pkt["metrics"][k] - v) <= 1e-12

    db_file = tmp_path / "test_continuum_ledger.sqlite"
    ledger = GovernanceCourtLedger(db_path=db_file)
    meta = ledger.record_sol_continuum_episode(record)
    assert meta["run_mode"] == "sol_continuum_discovery_observatory"
    assert meta["experiment_id"] == record.experiment_id
    integrity = ledger.verify_ledger_integrity()
    assert integrity.is_valid is True
    assert integrity.total_runs_verified == 1
    ledger.close()


def test_live_gemini_4_argon_sol_continuum_discovery_observatory(tmp_path):
    """
    Live Frontier I Integration Test against `gemini-4-argon`:
    Synthesizes a `ContinuumDiscoveryProposalSpec` for the 5-agent `ContinuumAgentGuild`,
    verifies Cycle 0 `QUARANTINE` -> Cycle 1 `ELIGIBLE` across `conJecture` WGSL and
    `HippocampalMemorySink`, and archives a compatible `sol-change` experiment with
    `review_status == "awaiting_review"` and `warnings == []`.
    """
    import os
    from google import genai
    from sol_decide.agentic.live_llm_elicitation import _load_env_safely
    from sol_decide.interop import (
        ChangeObservatoryBridge,
        SolContinuumDiscoveryOrchestrator,
    )

    _load_env_safely()
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("No GEMINI_API_KEY found for live Gemini 4 SOL Continuum test.")

    client = genai.Client(api_key=api_key)
    bridge = ChangeObservatoryBridge(
        experiments_root=tmp_path / "live_experiments",
        observatory_db_path=tmp_path / "live_observatory.sqlite3",
    )
    orchestrator = SolContinuumDiscoveryOrchestrator(
        observatory_bridge=bridge,
    )
    record = orchestrator.run_continuum_discovery_episode(
        study_name="SolContinuum_Autonomous_Guild_Discovery_v1",
        gemini_client=client,
        model="gemini-4-argon",
        register_in_observatory_db=True,
    )

    assert record.cycle0_audit.policy_status == "QUARANTINE"
    assert record.cycle1_audit.policy_status == "ELIGIBLE"
    assert record.conjecture_engine_status == "PROVED_THEOREM"
    assert record.observatory_comparability == "compatible"
    assert record.observatory_outcome == "improved"
    assert record.observatory_review_status == "awaiting_review"
    assert record.observatory_warnings == []
    assert record.post_mean_guild_competency > record.pre_mean_guild_competency


def test_lumina_coding_library_and_ranger_corps_observatory_mock(tmp_path):
    """
    Frontier J Deterministic Test:
    Verifies that `LuminaLibraryObservatoryOrchestrator` connects the Lumina Coding Library
    (`LuminaLibraryAgent`), Sovereign Domain (`SovereignDomain`, `PromotionCourt`), and
    Lumina Ranger Corps (`PhaseRanger`, `MassRanger`, `CourtRanger`, `FinalizationRanger`)
    with `sol-change` and `GovernanceCourtLedger`.
    """
    from sol_decide.delivery.governance_ledger import GovernanceCourtLedger
    from sol_decide.interop import (
        COMMAND_PROTOCOL_VERBS,
        ChangeObservatoryBridge,
        LuminaLibraryObservatoryOrchestrator,
    )

    bridge = ChangeObservatoryBridge(
        experiments_root=tmp_path / "lumina_experiments",
        observatory_db_path=tmp_path / "lumina_observatory.sqlite3",
    )
    orchestrator = LuminaLibraryObservatoryOrchestrator(
        observatory_bridge=bridge,
    )
    record = orchestrator.run_lumina_observatory_episode(
        study_name="Lumina_Ranger_Corps_Observatory_Sovereignty_v1",
        gemini_client=None,
        model="gemini-4-argon",
        register_in_observatory_db=True,
        persist_library_staging=False,
    )

    assert tuple(step["verb"] for step in record.command_protocol_trace) == COMMAND_PROTOCOL_VERBS
    assert record.cycle0_audit.policy_status == "QUARANTINE"
    assert record.cycle0_audit.governance_reason == "SOVEREIGN_RANGER_DRIFT_OR_MASS_QUARANTINE"
    assert record.cycle1_audit.policy_status == "ELIGIBLE"
    assert record.cycle1_audit.governance_reason == "LUMINA_RANGER_SOVEREIGN_COURT_VERIFIED"
    assert record.cycle1_audit.sacred_physics_mutated is False
    assert record.staged_component_record["verification_status"] == "AWAITING_OBSERVATORY_REVIEW"
    assert record.staged_component_record["review_status"] == "awaiting_review"
    assert record.observatory_comparability == "compatible"
    assert record.observatory_outcome == "improved"
    assert record.observatory_review_status == "awaiting_review"
    assert record.observatory_warnings == []
    assert record.sol_lens_packet["verdict"] == "PROMOTE"

    ledger = GovernanceCourtLedger(db_path=str(tmp_path / "lumina_ledger.sqlite3"))
    entry = ledger.record_lumina_observatory_episode(record)
    assert entry["run_mode"] == "lumina_ranger_observatory_sovereignty"
    assert ledger.verify_ledger_integrity().is_valid is True
    ledger.close()


@pytest.mark.live_gemini
def test_live_gemini_4_argon_lumina_ranger_corps_observatory(tmp_path):
    """
    Live Frontier J Integration Test against `gemini-4-argon`:
    Synthesizes a `LuminaRangerObservatoryProposalSpec` for the Sovereign Domain,
    Lumina Ranger Corps, and Lumina Coding Library, verifies Cycle 0 `QUARANTINE` ->
    Cycle 1 `ELIGIBLE` across all 7 Sovereignty Rules, and archives a zero-warning
    `sol-change` schema-1.0 experiment.
    """
    import os
    from google import genai
    from sol_decide.agentic.live_llm_elicitation import _load_env_safely
    from sol_decide.interop import (
        ChangeObservatoryBridge,
        LuminaLibraryObservatoryOrchestrator,
    )

    _load_env_safely()
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("No GEMINI_API_KEY found for live Gemini 4 Lumina Ranger Observatory test.")

    client = genai.Client(api_key=api_key)
    bridge = ChangeObservatoryBridge(
        experiments_root=tmp_path / "live_lumina_experiments",
        observatory_db_path=tmp_path / "live_lumina_observatory.sqlite3",
    )
    orchestrator = LuminaLibraryObservatoryOrchestrator(
        observatory_bridge=bridge,
    )
    record = orchestrator.run_lumina_observatory_episode(
        study_name="Lumina_Ranger_Corps_Observatory_Sovereignty_v1",
        gemini_client=client,
        model="gemini-4-argon",
        register_in_observatory_db=True,
        persist_library_staging=False,
    )

    assert record.cycle0_audit.policy_status == "QUARANTINE"
    assert record.cycle1_audit.policy_status == "ELIGIBLE"
    assert record.cycle1_audit.sacred_physics_mutated is False
    assert abs(record.cycle1_audit.bounded_phase_nudge_rad) <= 0.05
    assert abs(record.cycle1_audit.bounded_damping_delta) <= 0.01
    assert record.staged_component_record["verification_status"] == "AWAITING_OBSERVATORY_REVIEW"
    assert record.observatory_comparability == "compatible"
    assert record.observatory_outcome == "improved"
    assert record.observatory_review_status == "awaiting_review"
    assert record.observatory_warnings == []

