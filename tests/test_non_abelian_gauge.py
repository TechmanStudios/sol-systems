"""
Tests for Vector 16: Non-Abelian Gauge Sheaves & Holonomy-Based Spatial Intelligence
File: tests/test_non_abelian_gauge.py
"""

import math
import numpy as np
import pytest

from Frontier_OS.core.gauge import (
    skew,
    unskew,
    so3_exp,
    so3_log,
    so3_geodesic_distance,
    se3_exp,
    se3_log,
    lie_bracket_so3,
    adjoint_so3,
    adjoint_matrix_so3,
    adjoint_se3,
    adjoint_matrix_se3,
    so3_left_jacobian,
    so3_left_jacobian_inv,
    so3_right_jacobian,
    so3_slerp,
    se3_interpolate,
    WilsonLoopReport,
    FaceCurvatureReport,
    NonAbelianGaugeSheaf,
    ToolDriftCompensationReport,
    GaugeNavigationAuditReport,
    HolonomicSpatialNavigator,
    GaugeViolation,
    GaugeArbiterReport,
    NonAbelianGaugeArbiter
)


def test_so3_lie_algebra_and_exp_log_roundtrip():
    """Validates Rodrigues formula, hat/vee operators, and SO(3) Riemannian distance."""
    # 1. Hat and Vee operators
    omega = np.array([0.2, -0.4, 0.6], dtype=np.float64)
    W = skew(omega)
    omega_rec = unskew(W)
    np.testing.assert_allclose(omega, omega_rec, atol=1e-12)

    # 2. Exponential and Logarithm roundtrip
    R = so3_exp(omega)
    # Check SO(3) group properties: R^T R = I and det(R) = 1
    np.testing.assert_allclose(R.T @ R, np.eye(3), atol=1e-10)
    assert math.isclose(float(np.linalg.det(R)), 1.0, rel_tol=1e-10)

    omega_extracted = so3_log(R)
    np.testing.assert_allclose(omega, omega_extracted, atol=1e-9)

    # 3. Geodesic distance on SO(3)
    R1 = so3_exp(np.array([0.1, 0.0, 0.0]))
    R2 = so3_exp(np.array([0.4, 0.0, 0.0]))
    dist = so3_geodesic_distance(R1, R2)
    assert math.isclose(dist, 0.3, abs_tol=1e-5)


def test_so3_adjoint_and_jacobians():
    """Validates SO(3) adjoint actions and Left/Right Jacobian matrices."""
    omega = np.array([0.25, -0.15, 0.35], dtype=np.float64)
    R = so3_exp(omega)

    # Adjoint representations
    ad_w = adjoint_so3(omega)
    np.testing.assert_allclose(ad_w, skew(omega), atol=1e-12)

    Ad_R = adjoint_matrix_so3(R)
    v = np.array([0.1, 0.2, -0.3], dtype=np.float64)
    # Ad_R(v^) = R v^ R^T = (R v)^
    lhs = R @ skew(v) @ R.T
    rhs = skew(Ad_R @ v)
    np.testing.assert_allclose(lhs, rhs, atol=1e-10)

    # Left Jacobian and its inverse
    Jl = so3_left_jacobian(omega)
    Jl_inv = so3_left_jacobian_inv(omega)
    np.testing.assert_allclose(Jl @ Jl_inv, np.eye(3), atol=1e-10)

    # Right Jacobian
    Jr = so3_right_jacobian(omega)
    np.testing.assert_allclose(Jr, so3_left_jacobian(-omega), atol=1e-12)


def test_so3_and_se3_geodesic_interpolations():
    """Validates SLERP and SE(3) screw motion interpolations."""
    # 1. SO(3) SLERP
    R1 = so3_exp(np.array([0.0, 0.0, 0.0]))
    R2 = so3_exp(np.array([0.0, 0.0, math.radians(60.0)]))

    R_mid = so3_slerp(R1, R2, 0.5)
    np.testing.assert_allclose(R_mid.T @ R_mid, np.eye(3), atol=1e-10)
    dist_1_mid = so3_geodesic_distance(R1, R_mid)
    dist_mid_2 = so3_geodesic_distance(R_mid, R2)
    assert math.isclose(dist_1_mid, math.radians(30.0), abs_tol=1e-4)
    assert math.isclose(dist_mid_2, math.radians(30.0), abs_tol=1e-4)

    # 2. SE(3) Screw interpolation
    twist = np.array([1.0, 0.0, 0.0, 0.0, 0.0, math.radians(90.0)], dtype=np.float64)
    T1 = np.eye(4, dtype=np.float64)
    T2 = se3_exp(twist)
    T_mid = se3_interpolate(T1, T2, 0.5)

    twist_mid = se3_log(T_mid)
    np.testing.assert_allclose(twist_mid, 0.5 * twist, atol=1e-6)
    assert math.isclose(so3_geodesic_distance(T1[:3, :3], T_mid[:3, :3]), math.radians(45.0), abs_tol=1e-4)


def test_se3_twists_and_adjoint():
    """Validates SE(3) exponential, logarithm, and adjoint action."""
    twist = np.array([0.5, -0.2, 0.8, 0.1, 0.3, -0.2], dtype=np.float64)
    T = se3_exp(twist)

    assert T.shape == (4, 4)
    np.testing.assert_allclose(T[3, :], np.array([0, 0, 0, 1]), atol=1e-12)

    # Roundtrip log
    twist_rec = se3_log(T)
    np.testing.assert_allclose(twist, twist_rec, atol=1e-6)

    # Adjoint representations
    ad_xi = adjoint_se3(twist)
    assert ad_xi.shape == (6, 6)
    Ad_T = adjoint_matrix_se3(T)
    assert Ad_T.shape == (6, 6)


def test_wilson_loop_flat_and_defective_holonomy():
    """Validates Wilson loop holonomies and topological dislocation detection."""
    sheaf = NonAbelianGaugeSheaf()
    for node in ["A", "B", "C"]:
        sheaf.add_vertex(node)

    # Pure gauge (flat): identity connections
    sheaf.add_edge("e_AB", "A", "B", connection=np.eye(3))
    sheaf.add_edge("e_BC", "B", "C", connection=np.eye(3))
    sheaf.add_edge("e_CA", "C", "A", connection=np.eye(3))

    flat_loop = sheaf.compute_wilson_loop("triangle_flat", ["A", "B", "C"])
    assert flat_loop.is_flat is True
    assert math.isclose(flat_loop.defect_angle_deg, 0.0, abs_tol=1e-4)
    assert math.isclose(flat_loop.trace, 3.0, abs_tol=1e-4)

    # Introduce a 45-degree rotation dislocation around Z on edge BC
    sheaf_twisted = NonAbelianGaugeSheaf()
    for node in ["A", "B", "C"]:
        sheaf_twisted.add_vertex(node)

    R_twist = so3_exp(np.array([0.0, 0.0, math.radians(45.0)]))
    sheaf_twisted.add_edge("e_AB", "A", "B", connection=np.eye(3))
    sheaf_twisted.add_edge("e_BC", "B", "C", connection=R_twist)
    sheaf_twisted.add_edge("e_CA", "C", "A", connection=np.eye(3))

    twisted_loop = sheaf_twisted.compute_wilson_loop("triangle_twisted", ["A", "B", "C"])
    assert twisted_loop.is_flat is False
    assert math.isclose(twisted_loop.defect_angle_deg, 45.0, abs_tol=1e-2)
    assert math.isclose(float(np.linalg.norm(twisted_loop.curvature_vector)), math.radians(45.0), abs_tol=1e-3)


def test_discrete_faces_and_yang_mills_action():
    """Validates discrete 2-cell curvature 2-forms and Yang-Mills action."""
    sheaf = NonAbelianGaugeSheaf()
    for node in ["P1", "P2", "P3", "P4"]:
        sheaf.add_vertex(node)

    sheaf.add_edge("e1", "P1", "P2", connection=np.eye(3))
    sheaf.add_edge("e2", "P2", "P3", connection=np.eye(3))
    sheaf.add_edge("e3", "P3", "P1", connection=np.eye(3))
    sheaf.add_edge("e4", "P2", "P4", connection=np.eye(3))
    sheaf.add_edge("e5", "P4", "P3", connection=np.eye(3))

    sheaf.add_face("face_1", ["P1", "P2", "P3"])
    sheaf.add_face("face_2", ["P2", "P4", "P3"])

    # Flat state action should be 0.0
    action_flat = sheaf.compute_yang_mills_action()
    assert math.isclose(action_flat, 0.0, abs_tol=1e-8)

    # Introduce a 30-degree rotation on e2
    R_pert = so3_exp(np.array([math.radians(30.0), 0.0, 0.0]))
    sheaf.gauge_connections["e2"] = R_pert

    action_pert = sheaf.compute_yang_mills_action()
    assert action_pert > 0.0
    curv_1 = sheaf.compute_face_curvature("face_1")
    assert curv_1.is_flat is False
    assert math.isclose(curv_1.defect_angle_deg, 30.0, abs_tol=1e-2)


def test_local_gauge_transformation_invariance():
    """Validates that Wilson loop traces and Yang-Mills action are strictly gauge invariant."""
    sheaf = NonAbelianGaugeSheaf()
    for node in ["V1", "V2", "V3"]:
        sheaf.add_vertex(node)

    # Connections with inherent curvature
    r12 = so3_exp(np.array([0.1, -0.2, 0.15]))
    r23 = so3_exp(np.array([-0.05, 0.3, -0.1]))
    r31 = so3_exp(np.array([0.2, 0.1, -0.25]))

    sheaf.add_edge("e_12", "V1", "V2", connection=r12)
    sheaf.add_edge("e_23", "V2", "V3", connection=r23)
    sheaf.add_edge("e_31", "V3", "V1", connection=r31)
    sheaf.add_face("f_123", ["V1", "V2", "V3"])

    # Generate random local gauge transformation elements g_v in SO(3)
    gauge_elements = {
        "V1": so3_exp(np.array([0.45, -0.22, 0.61])),
        "V2": so3_exp(np.array([-0.31, 0.55, -0.19])),
        "V3": so3_exp(np.array([0.18, 0.29, -0.42]))
    }

    inv_rep = sheaf.verify_gauge_invariance(gauge_elements)
    assert inv_rep["is_strictly_gauge_invariant"] is True
    assert inv_rep["sym_invariance_error"] < 1e-10
    assert inv_rep["max_wilson_trace_error"] < 1e-10


def test_discrete_non_abelian_bianchi_identity():
    """Validates discrete non-abelian Bianchi identity D F = 0 on a tetrahedron."""
    sheaf = NonAbelianGaugeSheaf()
    nodes = ["T0", "T1", "T2", "T3"]
    for n in nodes:
        sheaf.add_vertex(n)

    # Add edges between all pairs of nodes with arbitrary SO(3) connections
    edges = [
        ("T0", "T1", [0.1, 0.2, -0.1]),
        ("T1", "T2", [-0.2, 0.1, 0.3]),
        ("T2", "T0", [0.15, -0.25, 0.05]),
        ("T0", "T3", [0.3, -0.1, 0.2]),
        ("T2", "T3", [-0.1, 0.2, -0.15]),
        ("T3", "T1", [0.05, -0.3, 0.1])
    ]
    for u, v, w in edges:
        sheaf.add_edge(f"e_{u}_{v}", u, v, connection=so3_exp(np.array(w)))

    bianchi_rep = sheaf.verify_non_abelian_bianchi(nodes)
    assert bianchi_rep["is_bianchi_satisfied"] is True
    assert bianchi_rep["bianchi_defect_norm"] < 1e-10


def test_dirichlet_energy_and_riemannian_gradient_diffusion():
    """Validates non-abelian Dirichlet energy relaxation on SO(3)."""
    sheaf = NonAbelianGaugeSheaf()
    sheaf.add_vertex("A", frame=np.eye(3))
    # Perturbed frame at B
    R_b_init = so3_exp(np.array([0.3, 0.2, -0.4]))
    sheaf.add_vertex("B", frame=R_b_init)
    sheaf.add_edge("e_AB", "A", "B", connection=np.eye(3))

    e_init = sheaf.compute_dirichlet_energy()
    assert e_init > 0.05

    e_start, e_final, history = sheaf.diffuse_gauge_frames(steps=20, lr=0.25)
    assert e_final < e_start
    assert e_final < 0.01  # Relaxed to consensus alignment
    assert history[-1] <= history[0]


def test_holonomic_spatial_navigator_and_parallel_transport():
    """Validates spatial triangulation and orientation frame parallel transport."""
    nav = HolonomicSpatialNavigator()
    anchors = {
        "Base": np.array([0.0, 0.0, 0.0]),
        "Elbow": np.array([0.3, 0.0, 0.4]),
        "Wrist": np.array([0.5, 0.2, 0.6])
    }
    loops = [("loop_arm", ["Base", "Elbow", "Wrist"])]

    sheaf = nav.build_workspace_triangulation(anchors, loops)
    assert len(sheaf.vertices) == 3
    assert len(sheaf.faces) == 1

    # Parallel transport orientation frame
    R_0 = np.eye(3)
    R_transported = nav.parallel_transport_frame(R_0, ["Base", "Elbow", "Wrist"])
    # Must remain an orthogonal SO(3) matrix
    np.testing.assert_allclose(R_transported.T @ R_transported, np.eye(3), atol=1e-8)

    # Audit holonomy
    audit = nav.audit_workspace_holonomy(loops)
    assert audit.total_loops_audited == 1
    assert audit.gauge_consistency_score > 0.90


def test_holonomic_tool_drift_compensation():
    """Validates Lie-algebraic rotational counter-twist for cyclic task paths."""
    nav = HolonomicSpatialNavigator()
    anchors = {
        "Pick": np.array([0.2, 0.1, 0.3]),
        "Lift": np.array([0.2, 0.1, 0.5]),
        "Place": np.array([0.4, 0.3, 0.3])
    }
    cycle = [("pick_and_place", ["Pick", "Lift", "Place"])]
    nav.build_workspace_triangulation(anchors, cycle)

    # Introduce a 25-degree orientational dislocation into the loop
    nav.sheaf.gauge_connections["edge_Lift_Place"] = so3_exp(np.array([0.0, math.radians(25.0), 0.0]))

    R_tool_init = np.eye(3)
    comp_rep = nav.compensate_cyclic_trajectory(R_tool_init, ["Pick", "Lift", "Place"])

    # Uncompensated drift should match the dislocation (~25 degrees)
    assert comp_rep.uncompensated_drift_deg > 20.0
    # Compensated drift should be eliminated
    assert comp_rep.is_drift_eliminated is True
    assert comp_rep.residual_drift_deg < 0.2
    np.testing.assert_allclose(
        comp_rep.compensated_final_frame.T @ comp_rep.compensated_final_frame,
        np.eye(3),
        atol=1e-10
    )


def test_gauge_safety_arbiter_audit_and_containment():
    """Validates Non-Abelian Gauge Arbiter safety thresholds and emergency containment."""
    nav = HolonomicSpatialNavigator()
    anchors = {
        "N1": np.array([0.0, 0.0, 0.0]),
        "N2": np.array([0.2, 0.0, 0.0]),
        "N3": np.array([0.2, 0.2, 0.0])
    }
    loops = [("safe_loop", ["N1", "N2", "N3"])]
    nav.build_workspace_triangulation(anchors, loops)

    arbiter = NonAbelianGaugeArbiter(nav, max_allowed_defect_deg=3.5)

    # 1. Safe audit
    safe_rep = arbiter.audit_holonomic_safety(loops)
    assert safe_rep.is_gauge_consistent is True
    assert safe_rep.violations_count == 0
    assert safe_rep.emergency_stop_triggered is False
    assert safe_rep.audit_time_us > 0.0
    assert safe_rep.yang_mills_action >= 0.0

    # 2. Inject intentional severe dislocation (60 degrees)
    nav.sheaf.gauge_connections["edge_N1_N2"] = so3_exp(np.array([0.0, 0.0, math.radians(60.0)]))
    hazard_rep = arbiter.audit_holonomic_safety(loops)
    assert hazard_rep.is_gauge_consistent is False
    assert hazard_rep.violations_count >= 1
    assert hazard_rep.emergency_stop_triggered is True
    assert hazard_rep.violations[0].severity == "CRITICAL"
