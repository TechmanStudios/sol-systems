"""
SOL-Decide Demonstration 1: NGCV Powertrain Trade Study
========================================================
Point-in-Time Single-Episode Trade Study for Next-Generation Combat Vehicle (NGCV)
comparing three candidate powertrain architectures:
1. Advanced Diesel-Mechanical
2. Series Hybrid-Electric Drive (HED)
3. Hydrogen Fuel Cell Hybrid (FCH)
"""

from typing import Tuple
import numpy as np

from ..core.primitives import (
    OptimizationDirection,
    ConstraintSeverity,
    Objective,
    Option,
    Constraint,
    Assumption,
    Risk,
    BiasCheck
)
from ..core.sheaf_decision_complex import SheafDecisionComplex, DecisionEvaluationReport
from ..agentic.elicitation_moa import SevenGiantsElicitor, ElicitationResult
from ..agentic.dialectical_bias import DialecticalAdversary, DialecticalBiasReport
from ..agentic.sensitivity_ablation import SensitivityAblator, SensitivityReport
from ..delivery.decision_package import DecisionPackageCompiler, SignerReadyDecisionPackage


def build_ngcv_trade_study() -> SheafDecisionComplex:
    """
    Constructs the formal Sheaf Decision Complex for the NGCV Powertrain Study.
    
    State vector channels for Options:
    [0]: Gross Vehicle Weight (tons)
    [1]: Silent Watch Duration (hours)
    [2]: Dash Speed (mph)
    [3]: Supply Chain Lead Time (weeks)
    """
    complex_obj = SheafDecisionComplex(name="NGCV_Powertrain_Trade_Study")

    # 1. Objectives
    complex_obj.add_primitive(Objective(
        id="obj_silent_watch",
        name="Maximize Silent Watch Duration",
        direction=OptimizationDirection.MAXIMIZE,
        weight=0.40,
        target_value=8.0,
        units="hours"
    ))
    complex_obj.add_primitive(Objective(
        id="obj_dash_speed",
        name="Maximize Dash Speed",
        direction=OptimizationDirection.MAXIMIZE,
        weight=0.30,
        target_value=50.0,
        units="mph"
    ))
    complex_obj.add_primitive(Objective(
        id="obj_trl",
        name="Maximize Technology Readiness",
        direction=OptimizationDirection.MAXIMIZE,
        weight=0.30,
        target_value=8.0,
        units="TRL_scale"
    ))

    # 2. Hard Constraints
    complex_obj.add_primitive(Constraint(
        id="con_gvwr",
        name="Gross Vehicle Weight Rating Ceiling",
        lower_bound=-np.inf,
        upper_bound=45.0,
        severity=ConstraintSeverity.HARD,
        units="tons",
        description="Air transportability and bridge classification limit"
    ))
    complex_obj.add_primitive(Constraint(
        id="con_silent_watch",
        name="Minimum Silent Watch Mandate",
        lower_bound=6.0,
        upper_bound=np.inf,
        severity=ConstraintSeverity.HARD,
        units="hours",
        description="Acoustic & thermal stealth mission duration"
    ))
    complex_obj.add_primitive(Constraint(
        id="con_dash_speed",
        name="Minimum Dash Speed Threshold",
        lower_bound=45.0,
        upper_bound=np.inf,
        severity=ConstraintSeverity.HARD,
        units="mph",
        description="Combat sprint survivability requirement"
    ))
    complex_obj.add_primitive(Constraint(
        id="con_lead_time",
        name="Supply Chain Lead Time Ceiling",
        lower_bound=-np.inf,
        upper_bound=40.0,
        severity=ConstraintSeverity.HARD,
        units="weeks",
        description="Procurement schedule delivery window"
    ))

    # 3. Assumptions
    complex_obj.add_primitive(Assumption(
        id="ass_battery_density",
        name="Li-Ion Specific Energy Density",
        baseline_value=450.0,
        uncertainty_sigma=0.08,
        units="Wh/kg",
        source_reference="DEVCOM GVSC Cell Roadmap 2026",
        description="Baseline cell-level energy density for hybrid battery pack"
    ))
    complex_obj.add_primitive(Assumption(
        id="ass_fuel_cost",
        name="Logistics Fuel Burden Cost",
        baseline_value=35.0,
        uncertainty_sigma=0.10,
        units="USD/gal",
        source_reference="Army Petroleum Center 2026",
        description="Fully burdened cost of fuel in theater"
    ))

    # 4. Program Risks
    complex_obj.add_primitive(Risk(
        id="risk_inverter_thermal",
        name="SiC Inverter Thermal Runaway Risk",
        probability=0.20,
        impact=0.70,
        description="High-voltage power electronics cooling under extreme ambient conditions"
    ))

    # 5. Bias Check
    complex_obj.add_primitive(BiasCheck(
        id="bias_vendor_lockin",
        name="Incumbent Diesel Bias Refutation",
        bias_category="confirmation_bias",
        description="Adversarial check against legacy diesel fleet status-quo bias"
    ))

    # 6. Candidate Options
    # [Weight (tons), Silent Watch (hrs), Dash Speed (mph), Lead Time (wks)]
    opt_diesel = Option(
        id="opt_diesel",
        name="Advanced Diesel-Mechanical",
        stalk_dim=4,
        initial_params=np.array([43.5, 2.0, 48.0, 24.0]),
        trl=8,
        mrl=8,
        estimated_cost_m=11.2,
        description="Modernized turbocharged high-density diesel engine"
    )
    opt_hed = Option(
        id="opt_hed",
        name="Series Hybrid-Electric Drive (HED)",
        stalk_dim=4,
        initial_params=np.array([42.0, 8.0, 52.0, 32.0]),
        trl=6,
        mrl=6,
        estimated_cost_m=13.8,
        description="Series hybrid with SiC power electronics and Li-Ion energy storage"
    )
    opt_fch = Option(
        id="opt_fch",
        name="Hydrogen Fuel Cell Hybrid",
        stalk_dim=4,
        initial_params=np.array([46.5, 10.0, 44.0, 52.0]),
        trl=4,
        mrl=3,
        estimated_cost_m=18.5,
        description="Proton exchange membrane fuel cell with pressurized hydrogen tanks"
    )

    complex_obj.add_primitive(opt_diesel)
    complex_obj.add_primitive(opt_hed)
    complex_obj.add_primitive(opt_fch)

    # 7. Edges & Linear Restriction Maps
    # Channels: 0: Weight, 1: Silent Watch, 2: Dash, 3: Lead Time
    options = [opt_diesel, opt_hed, opt_fch]
    for opt in options:
        # Edge to Weight Constraint (channel 0)
        s_map_w = np.zeros((1, 4))
        s_map_w[0, 0] = 1.0
        complex_obj.add_edge(
            edge_id=f"e_{opt.id}_gvwr",
            source_id=opt.id,
            target_id="con_gvwr",
            dim_edge=1,
            source_map=s_map_w,
            target_map=np.array([[1.0]]),
            weight=1.0,
            edge_type="constraint_check"
        )

        # Edge to Silent Watch Constraint (channel 1)
        s_map_sw = np.zeros((1, 4))
        s_map_sw[0, 1] = 1.0
        complex_obj.add_edge(
            edge_id=f"e_{opt.id}_silent_watch",
            source_id=opt.id,
            target_id="con_silent_watch",
            dim_edge=1,
            source_map=s_map_sw,
            target_map=np.array([[1.0]]),
            weight=1.0,
            edge_type="constraint_check"
        )

        # Edge to Dash Speed Constraint (channel 2)
        s_map_ds = np.zeros((1, 4))
        s_map_ds[0, 2] = 1.0
        complex_obj.add_edge(
            edge_id=f"e_{opt.id}_dash_speed",
            source_id=opt.id,
            target_id="con_dash_speed",
            dim_edge=1,
            source_map=s_map_ds,
            target_map=np.array([[1.0]]),
            weight=1.0,
            edge_type="constraint_check"
        )

        # Edge to Lead Time Constraint (channel 3)
        s_map_lt = np.zeros((1, 4))
        s_map_lt[0, 3] = 1.0
        complex_obj.add_edge(
            edge_id=f"e_{opt.id}_lead_time",
            source_id=opt.id,
            target_id="con_lead_time",
            dim_edge=1,
            source_map=s_map_lt,
            target_map=np.array([[1.0]]),
            weight=1.0,
            edge_type="constraint_check"
        )

    return complex_obj


def run_demonstration_1() -> Tuple[SheafDecisionComplex, SignerReadyDecisionPackage, SensitivityReport, DialecticalBiasReport]:
    """
    Executes complete end-to-end pipeline for Demonstration 1.
    """
    complex_obj = build_ngcv_trade_study()

    # 1. 7 Giants Elicitation Pass
    elicitor = SevenGiantsElicitor()
    # Complex is already constructed, but run verification
    eval_rep = complex_obj.evaluate_decision_package()

    # 2. Dialectical Adversary Stress Test on selected alternative
    adversary = DialecticalAdversary(max_strain_trials=40, strain_magnitude=0.12)
    bias_rep = adversary.stress_test_candidate(complex_obj, eval_rep.selected_option_id or "opt_hed")

    # 3. Sensitivity Ablation ("What Flips the Decision")
    ablator = SensitivityAblator(sweep_steps=30, max_deviation_ratio=0.40)
    sens_rep = ablator.compute_decision_flips(complex_obj)

    # 4. Compile and Sign Decision Package
    compiler = DecisionPackageCompiler()
    package = compiler.compile(
        complex_obj=complex_obj,
        eval_report=eval_rep,
        sensitivity_report=sens_rep,
        bias_report=bias_rep,
        authorized_role="PEO Ground Combat Systems"
    )

    # 5. Sign Authorization Gate
    package.sign(signer_name="Col. Bryan Tucker, PEO GCS Chief Engineer", comments="Certified. beta_1=0; HED selected.")

    return complex_obj, package, sens_rep, bias_rep
