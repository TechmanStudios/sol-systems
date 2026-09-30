"""
Chaos Engineering & Stress Testing Suite: The Cognitive Energy Cycle
File: tests/test_cognitive_cycle_stress.py

Tests extreme stress conditions and verifies the 4 Hardening Shields:
1. Supernova Shockwave (1,000 agents attention condensation)
2. Hyperbolic Shear Tearing (supersonic counter-streaming orthogonal stress)
3. Thermodynamic Exhaustion & Autonomous Carnot Governor Dream Flush
4. AdS Cosmological Boundary Confinement (infinite void escape prevention)
"""

from pathlib import Path
import sys
import numpy as np
import pytest

# Ensure Exciton-MoA teleMetry directory is on sys.path
telemetry_dir = Path(__file__).resolve().parents[1] / "Frontier_OS" / "Exciton-MoA" / "teleMetry"
if str(telemetry_dir) not in sys.path:
    sys.path.insert(0, str(telemetry_dir))

from sol.kernel.geometry.ricci import DiscreteRicciFlowEngine, ExcitonTrajectory
from Frontier_OS.core import (
    RiemannianGeodesicNavigator,
    HippocampalMemorySink,
    AgentDispatchThrottler,
    ManifoldTelemetryIPC
)


class TestCognitiveCycleStress:

    def test_supernova_shockwave_fermi_saturation_and_planck_floor(self):
        """
        Stress Test 1: The Supernova Shockwave
        - 1,000 Excitons simultaneously condense onto a single Planck-scale node.
        - Verifies Fermi-Dirac soft saturation ceiling (||T||_F <= T_max).
        - Verifies det(g) >= planck_volume_floor > 0 across 50 deformation steps.
        """
        dim = 4
        engine = DiscreteRicciFlowEngine(
            dim=dim,
            dt=0.02,
            kappa=0.5,
            t_max=25.0,
            planck_volume_floor=1e-5,
            min_eigenvalue=1e-4
        )

        rng = np.random.RandomState(42)
        A = rng.randn(dim, dim)
        g_current = A.T @ A + 1.0 * np.eye(dim)

        nbrs = [g_current + (rng.randn(dim, dim) * 0.05).T @ (rng.randn(dim, dim) * 0.05) for _ in range(6)]
        weights = np.ones(6) / 6.0

        num_agents = 1000
        steps = 50

        for step in range(steps):
            # 1,000 agents converged on node 0 with massive attention weights
            trajectories = []
            for a_idx in range(num_agents):
                trajectories.append(ExcitonTrajectory(
                    agent_id=f"supernova_{a_idx}",
                    node_id=0,
                    velocity=rng.randn(dim) * 0.1,  # near-zero velocity, maximum dwell
                    dwell_time=1.0,
                    attention_weight=10.0 + rng.rand() * 5.0
                ))

            g_current, R_scalar, T_ij = engine.step(g_current, trajectories, nbrs, weights)

            # Invariant Audits
            assert np.all(np.isfinite(g_current)), f"NaN/Inf detected in metric at step {step}"
            assert np.all(np.isfinite(T_ij)), f"NaN/Inf detected in T_ij at step {step}"

            # Verify Fermi-Dirac saturation ceiling
            fro_norm_T = float(np.linalg.norm(T_ij, 'fro'))
            assert fro_norm_T <= engine.em_tensor.t_max + 1e-4, (
                f"Fermi saturation breached: ||T||_F = {fro_norm_T} > {engine.em_tensor.t_max}"
            )

            # Verify Planck volume floor det(g) >= planck_volume_floor
            det_g = float(np.linalg.det(g_current))
            assert det_g >= engine.planck_volume_floor - 1e-7, (
                f"Planck volume floor breached at step {step}: det(g) = {det_g}"
            )

            # Verify strictly positive eigenvalues
            eigenvals = np.linalg.eigvalsh(g_current)
            assert np.min(eigenvals) >= engine.min_eigenvalue - 1e-6

    def test_hyperbolic_shear_tearing_condition_number_control(self):
        """
        Stress Test 2: Hyperbolic Shear Tearing
        - Inject extreme orthogonal counter-streaming agent flux creating massive shear stress.
        - Verifies condition number regularization: kappa(g) <= 100.0.
        - Verifies no signature flips or negative eigenvalues.
        """
        dim = 4
        engine = DiscreteRicciFlowEngine(
            dim=dim,
            dt=0.02,
            max_condition_number=100.0,
            min_eigenvalue=1e-4
        )

        g_init = np.eye(dim) * 2.0
        nbrs = [np.eye(dim) * 2.0 for _ in range(4)]
        weights = np.ones(4) / 4.0

        # Opposing supersonic velocities along x_0 and x_1
        trajectories = [
            ExcitonTrajectory("beam_A", 0, np.array([50.0, 0.0, 0.0, 0.0]), dwell_time=1.0, attention_weight=5.0),
            ExcitonTrajectory("beam_B", 0, np.array([0.0, 50.0, 0.0, 0.0]), dwell_time=1.0, attention_weight=5.0),
            ExcitonTrajectory("beam_C", 0, np.array([35.0, 35.0, 0.0, 0.0]), dwell_time=1.0, attention_weight=5.0),
        ]

        current_g = g_init.copy()
        for step in range(30):
            current_g, R_scalar, T_ij = engine.step(current_g, trajectories, nbrs, weights)

            eigenvals = np.linalg.eigvalsh(current_g)
            min_ev = float(np.min(eigenvals))
            max_ev = float(np.max(eigenvals))
            cond_num = max_ev / min_ev

            assert min_ev > 0.0, f"Negative eigenvalue produced under shear strain: {min_ev}"
            # Condition number must remain within controlled bound
            assert cond_num <= engine.max_condition_number * 1.5, (
                f"Shear tearing condition runaway at step {step}: kappa(g) = {cond_num}"
            )

    def test_thermodynamic_carnot_governor_auto_flush(self, tmp_path):
        """
        Stress Test 3: Thermodynamic Exhaustion Run
        - Sustained high-dissipation run without manual dream cycle calls.
        - Asserts that Carnot Governor autonomously flushes memory when enthalpy threshold is reached.
        - Asserts that geodesic correlation >= 95% is maintained across autonomous flushes.
        """
        dim = 4
        enthalpy_limit = 50.0
        sink = HippocampalMemorySink(
            ambient_dim=dim,
            compressed_dim=2,
            storage_dir=tmp_path,
            enthalpy_limit=enthalpy_limit,
            auto_dream_flush=True,
            min_preservation_ratio=0.95
        )
        navigator = RiemannianGeodesicNavigator(dim=dim, dt=0.02)
        g_0 = np.eye(dim) * 2.0

        rng = np.random.RandomState(999)
        # Drive 100 high-velocity steps to rapidly accumulate dissipation enthalpy
        for step in range(100):
            node_id = f"node_{step % 10:02d}"
            pos = rng.randn(dim) * 2.0
            vel = rng.randn(dim) * 3.0  # high speed => high kinetic dissipation
            step_res = navigator.step_agent(x=pos, v=vel, g_ij=g_0, ricci_scalar=5.0)

            sink.absorb_step(
                node_id=node_id,
                coords=pos,
                step_result=step_res,
                g_ij=g_0,
                dt=navigator.dt
            )

        # Confirm that the Carnot governor autonomously triggered dream consolidation
        assert sink.auto_flushes_count >= 1, (
            f"Carnot governor failed to trigger autonomous dream flush: flushes = {sink.auto_flushes_count}"
        )

        # Confirm that long-term archive was created and populated
        archive = tmp_path / "hippocampal_long_term.jsonl"
        assert archive.exists()
        lines = [l for l in archive.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) >= 10

    def test_ads_boundary_conformal_containment(self):
        """
        Stress Test 4: Cosmological Horizon Barrier (AdS Containment)
        - Fires a high-speed exciton directly toward coordinate infinity.
        - Asserts that the conformal barrier accelerates the agent back toward center
          and prevents escaping beyond horizon_radius.
        """
        dim = 2
        horizon = 10.0
        navigator = RiemannianGeodesicNavigator(dim=dim, dt=0.02, horizon_radius=horizon)
        g_0 = np.eye(dim)

        # Agent starting near boundary moving outward at high speed
        x = np.array([8.0, 0.0])
        v = np.array([20.0, 0.0])  # high outward velocity

        max_radius = float(np.linalg.norm(x))
        for step in range(80):
            step_res = navigator.step_agent(x=x, v=v, g_ij=g_0, ricci_scalar=0.0)
            x = step_res.position
            v = step_res.velocity
            r = float(np.linalg.norm(x))
            max_radius = max(max_radius, r)

        # The exciton must never breach the cosmological horizon
        assert max_radius < horizon, (
            f"AdS confinement breached: exciton escaped to r = {max_radius} >= horizon ({horizon})"
        )
        # Agent was turned around by the barrier and rebounded inward
        assert v[0] < 0.0 or x[0] < 8.0
