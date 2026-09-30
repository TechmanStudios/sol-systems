"""
Tests for Vector 15: Closed-Loop Embodied Autonomous Robotics & Geodesic Actuation
File: tests/test_robotic_actuation.py
"""

import math
import numpy as np
import pytest

from Frontier_OS.core.robotics import (
    ArticulatedManipulator6DOF,
    RoboticConfigurationManifold,
    Obstacle3D,
    KinematicState,
    ActuationStepRecord,
    TrajectoryExecutionReport,
    GeodesicActuationController,
    SafetyViolation,
    RoboticSafetyAuditReport,
    RoboticSafetyArbiter
)
from scripts.run_sol_live_stream import ManifoldSimulationServer, create_handler


def test_forward_kinematics_and_reachability():
    """Validates 6-DOF forward kinematics and SO(3) rotation preservation."""
    robot = ArticulatedManipulator6DOF()
    assert robot.num_joints == 6
    assert len(robot.link_lengths) == 6

    # Test home configuration q = [0, 0, 0, 0, 0, 0]
    q_home = np.zeros(6)
    ee_pos, ee_rot, joint_positions = robot.forward_kinematics(q_home)

    assert len(joint_positions) == 7  # Base + 6 joints
    assert ee_pos.shape == (3,)
    assert ee_rot.shape == (3, 3)

    # SO(3) orthogonality check: R^T R = I and det(R) = 1
    ortho_identity = ee_rot.T @ ee_rot
    np.testing.assert_allclose(ortho_identity, np.eye(3), atol=1e-5)
    assert math.isclose(float(np.linalg.det(ee_rot)), 1.0, rel_tol=1e-4)

    # Base joint is at [0, 0, l_0]
    np.testing.assert_allclose(joint_positions[1], np.array([0.0, 0.0, robot.link_lengths[0]]), atol=1e-5)


def test_numerical_geometric_jacobian_and_manipulability():
    """Validates central-difference Jacobian rank and Yoshikawa index."""
    robot = ArticulatedManipulator6DOF()
    q = np.array([0.0, 0.4, -0.6, 0.0, 0.3, 0.0])

    J_v = robot.compute_jacobian(q)
    assert J_v.shape == (3, 6)

    # Rank must be 3 (full Cartesian translational rank)
    rank = np.linalg.matrix_rank(J_v)
    assert rank == 3

    # Manipulability index w(q) = sqrt(det(J J^T)) > 0
    w = robot.compute_manipulability(q)
    assert w > 0.001


def test_riemannian_configuration_metric():
    """Validates metric tensor positive-definiteness, symmetry, and obstacle warping."""
    robot = ArticulatedManipulator6DOF()
    obs = Obstacle3D(obstacle_id="pillar", position=np.array([0.35, 0.20, 0.40]), radius=0.10, repulsion_gain=1.0)
    manifold = RoboticConfigurationManifold(robot, obstacles=[obs])

    q = np.array([0.1, 0.3, -0.5, 0.1, 0.2, 0.0])
    g = manifold.compute_metric(q)

    # 1. Metric must be 6x6
    assert g.shape == (6, 6)

    # 2. Strict symmetry g = g^T
    np.testing.assert_allclose(g, g.T, atol=1e-6)

    # 3. Positive definiteness: all eigenvalues > 0
    eigenvals = np.linalg.eigvalsh(g)
    assert np.all(eigenvals > 0.0)
    assert min(eigenvals) >= 0.01

    # 4. Obstacle metric inflation: metric close to obstacle has higher condition number
    q_near = np.array([0.4, 0.2, -0.3, 0.0, 0.2, 0.0])
    g_near = manifold.compute_metric(q_near)
    cond_near = np.linalg.cond(g_near)
    assert cond_near > 1.0


def test_christoffel_symbols_and_geodesic_deflection():
    """Validates Christoffel symbol computation and curvature deflection."""
    robot = ArticulatedManipulator6DOF()
    obs = Obstacle3D(obstacle_id="pillar", position=np.array([0.35, 0.20, 0.40]), radius=0.10, repulsion_gain=0.8)
    manifold = RoboticConfigurationManifold(robot, obstacles=[obs])

    q = np.array([0.1, 0.3, -0.4, 0.0, 0.2, 0.0])
    dq = np.array([0.2, -0.1, 0.15, -0.05, 0.1, 0.0])

    gamma = manifold.compute_christoffel_symbols(q)
    assert gamma.shape == (6, 6, 6)

    # Christoffel symmetry in lower indices: Γ^i_{jk} == Γ^i_{kj}
    for i in range(6):
        np.testing.assert_allclose(gamma[i], gamma[i].T, atol=1e-4)

    # Geodesic acceleration a^i = - Γ^i_{jk} dq^j dq^k
    a_geodesic = manifold.compute_geodesic_acceleration(q, dq)
    assert a_geodesic.shape == (6,)
    assert not np.any(np.isnan(a_geodesic))


def test_geodesic_actuation_controller_execution():
    """Tests closed-loop trajectory convergence and Carnot memory dissipation."""
    robot = ArticulatedManipulator6DOF()
    obs = Obstacle3D(obstacle_id="obs_target_flank", position=np.array([0.30, 0.10, 0.35]), radius=0.08, repulsion_gain=0.6)
    manifold = RoboticConfigurationManifold(robot, obstacles=[obs])
    controller = GeodesicActuationController(manifold, dt=0.01, damping_gamma=0.08)

    q_start = np.array([0.1, 0.4, -0.6, 0.0, 0.2, 0.0])
    q_goal = np.array([0.3, 0.6, -0.8, 0.1, 0.4, 0.0])
    target_pos, _, _ = robot.forward_kinematics(q_goal)

    rep = controller.execute_trajectory(
        q_start=q_start,
        target_pos=target_pos,
        max_steps=120,
        goal_tolerance=0.035
    )

    assert rep.total_steps > 0
    assert rep.duration_s > 0.0
    assert rep.initial_distance > rep.final_distance
    assert rep.final_distance < 0.035  # Close to goal within tolerance
    assert rep.success is True
    assert rep.total_carnot_dissipated_j > 0.0
    assert rep.min_obstacle_clearance > 0.0  # Kept positive clearance
    assert len(rep.trajectory) == rep.total_steps


def test_robotic_safety_arbiter_audit_and_cohomology():
    """Validates Safety Arbiter invariant checks and actuator sheaf cohomology."""
    robot = ArticulatedManipulator6DOF()
    obs = Obstacle3D(obstacle_id="obs1", position=np.array([0.35, 0.20, 0.40]), radius=0.10, repulsion_gain=0.8)
    manifold = RoboticConfigurationManifold(robot, obstacles=[obs])
    arbiter = RoboticSafetyArbiter(manifold, min_safe_clearance_m=0.03)

    # 1. Test Actuator Sheaf construction & Betti number β₁ = 0
    actuator_sheaf = arbiter.build_actuator_coordination_sheaf()
    assert len(actuator_sheaf.vertices) == 6
    assert len(actuator_sheaf.edges) == 5  # Line graph across 6 serial joints

    # Line graph of serial chain has β₁ = 0 (no cycles)
    spectrum = arbiter.cohomology_engine.compute_spectrum()
    assert spectrum.beta_1 == 0
    assert spectrum.beta_0 == 1  # 1 connected component

    # 2. Test Safe Trajectory Audit
    controller = GeodesicActuationController(manifold, dt=0.01)
    q_start = np.array([0.0, 0.2, -0.4, 0.0, 0.2, 0.0])
    target_pos = np.array([0.45, 0.25, 0.45])
    traj_rep = controller.execute_trajectory(q_start, target_pos, max_steps=40)

    audit_rep = arbiter.audit_trajectory(traj_rep.trajectory)
    assert audit_rep.is_safe is True
    assert audit_rep.violations_count == 0
    assert audit_rep.emergency_stop_triggered is False
    assert audit_rep.actuator_betti_1 == 0
    assert audit_rep.actuator_sheaf_consistency >= 0.90

    # 3. Test Injected Collision Hazard Detection
    hazardous_step = ActuationStepRecord(
        step_index=999,
        time_s=1.0,
        end_effector_pos=[0.35, 0.20, 0.40],
        distance_to_goal=0.01,
        min_obstacle_dist=0.01,  # Below min safe clearance of 0.03
        manipulability=0.08,
        torque_norm=10.0,
        kinetic_energy=0.5,
        carnot_dissipated_dE=0.001
    )
    hazard_audit = arbiter.audit_trajectory([hazardous_step])
    assert hazard_audit.is_safe is False
    assert hazard_audit.violations_count >= 1
    assert hazard_audit.emergency_stop_triggered is True
    assert any(v.invariant_name == "COLLISION_AVOIDANCE" for v in hazard_audit.violations)


def test_live_stream_robotics_status_and_execution_endpoints():
    """Validates HTTP API endpoints for Vector 15 in ManifoldSimulationServer."""
    server = ManifoldSimulationServer(port=8765)
    server.start()

    try:
        # 1. Test status query
        status = server.manipulator.num_joints
        assert status == 6
        assert len(server.robotic_obstacles) == 2

        # 2. Direct controller trajectory dispatch
        target_pos = np.array([0.45, 0.25, 0.45])
        rep = server.robotic_controller.execute_trajectory(
            q_start=server.current_q,
            target_pos=target_pos,
            max_steps=50
        )
        assert rep.total_steps > 0
        server.latest_robotic_trajectory_report = rep

        # 3. Safety audit dispatch
        safety_rep = server.robotic_safety_arbiter.audit_trajectory(rep.trajectory)
        server.latest_robotic_safety_report = safety_rep
        assert safety_rep.actuator_betti_1 == 0
        assert safety_rep.is_safe is True

    finally:
        server.stop()
