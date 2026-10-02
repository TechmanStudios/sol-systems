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
