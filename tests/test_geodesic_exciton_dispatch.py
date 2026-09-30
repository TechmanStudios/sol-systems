"""
Integration Tests: Frontier_OS Exciton-MoA Riemannian Geodesic Navigation
File: tests/test_geodesic_exciton_dispatch.py
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock
import numpy as np
import pytest
import scipy.linalg as la

# Ensure ExcitonEngine directory is on sys.path
exciton_engine_dir = Path(__file__).resolve().parents[1] / "Frontier_OS" / "Exciton-MoA" / "firmWare" / "ExcitonEngine"
if str(exciton_engine_dir) not in sys.path:
    sys.path.insert(0, str(exciton_engine_dir))

from sol.kernel.geometry.ricci import DiscreteRicciFlowEngine
from sol.diagnostics.damping_spectrogram import AdaptiveDampingStabilizer
from Frontier_OS.core import (
    AgentDispatchThrottler,
    CurvatureTelemetryPacket,
    ManifoldTelemetryIPC,
    RiemannianGeodesicNavigator,
    ChristoffelCalculator,
    GeodesicStepResult
)
from excitons import ExcitonEngine


class TestGeodesicExcitonDispatch:

    def test_christoffel_symbols_conformal_metric(self):
        """
        Validates Christoffel symbols for a conformal metric field:
            g_ij(x) = exp(Phi(x)) * delta_ij
        Analytically, for g_ij = e^(2 psi) delta_ij:
            Gamma^k_ij = delta_ki d_j psi + delta_kj d_i psi - delta_ij d_k psi
        """
        dim = 2
        calc = ChristoffelCalculator(dim=dim, eps=1e-5)

        # Potential well at origin: Phi(x) = -0.5 * (x_0^2 + x_1^2)
        def metric_at(x):
            psi = -0.5 * np.sum(x**2)
            factor = np.exp(2.0 * psi)
            return factor * np.eye(dim)

        x_eval = np.array([0.5, 0.5])
        g_at_x = metric_at(x_eval)

        Gamma = calc.compute_symbols(g_at_x, metric_evaluator=metric_at, x=x_eval)

        assert Gamma.shape == (2, 2, 2)
        # Analytical check: d psi / dx = -x => d_0 psi = -0.5, d_1 psi = -0.5
        # Gamma^0_00 = d_0 psi = -0.5
        assert np.isclose(Gamma[0, 0, 0], -0.5, atol=1e-3)
        # Gamma^1_11 = d_1 psi = -0.5
        assert np.isclose(Gamma[1, 1, 1], -0.5, atol=1e-3)
        # Symmetry: Gamma^k_ij = Gamma^k_ji
        assert np.isclose(Gamma[0, 0, 1], Gamma[0, 1, 0], atol=1e-5)

    def test_geodesic_curvature_lensing_deflection(self):
        """
        Verifies that an exciton moving past a semantic mass well is deflected
        along the curved geodesic towards the mass center (geodesic lensing).
        """
        dim = 2
        navigator = RiemannianGeodesicNavigator(dim=dim, dt=0.02)

        # Attractive semantic well at [0.0, 1.0]: g_ij has strong local gradient
        def metric_at(x):
            center = np.array([0.0, 1.0])
            r_sq = np.sum((x - center)**2)
            # Higher metric density near center
            scale = 1.0 + 3.0 / (1.0 + r_sq)
            return scale * np.eye(dim)

        # Agent moving horizontally from left to right along y = 0
        x_init = np.array([-2.0, 0.0])
        v_init = np.array([2.0, 0.0])  # purely horizontal initial velocity

        x = x_init.copy()
        v = v_init.copy()

        y_positions = [x[1]]
        for step in range(60):
            g_curr = metric_at(x)
            step_res = navigator.step_agent(
                x=x,
                v=v,
                g_ij=g_curr,
                metric_evaluator=metric_at,
                potential_coupling=0.0  # pure geodesic motion, no explicit target potential
            )
            x = step_res.position
            v = step_res.velocity
            y_positions.append(x[1])

        # Assert that the exciton was deflected in y towards the well at y = 1.0
        max_y_deflection = max(y_positions)
        assert max_y_deflection > 0.05, (
            f"Exciton failed to lens along curved geodesic: max_y = {max_y_deflection}"
        )

    def test_adaptive_damping_quenching_under_curvature_strain(self):
        """
        Verifies that high-curvature regions increase dynamic damping gamma(v, R),
        quenching kinetic energy before caustic collapse.
        """
        dim = 4
        navigator = RiemannianGeodesicNavigator(dim=dim, dt=0.01)
        g_ij = np.eye(dim)

        v_in = np.array([5.0, 5.0, 5.0, 5.0])
        x_in = np.zeros(dim)

        # Baseline flat void (R = 0.0)
        res_flat = navigator.step_agent(x=x_in, v=v_in, g_ij=g_ij, ricci_scalar=0.0)

        # High curvature singularity proximity (R = 25.0)
        res_curved = navigator.step_agent(x=x_in, v=v_in, g_ij=g_ij, ricci_scalar=25.0)

        # Damping must be substantially higher in curved space
        assert res_curved.damping_gamma > res_flat.damping_gamma * 5.0
        # Final speed must be quenched more aggressively in curved space
        speed_flat = np.linalg.norm(res_flat.velocity)
        speed_curved = np.linalg.norm(res_curved.velocity)
        assert speed_curved < speed_flat

    def test_end_to_end_exciton_engine_dispatch(self):
        """
        Verifies full integration through ExcitonEngine firmware.
        """
        mock_core = MagicMock()
        mock_core.graph = MagicMock()
        mock_core.graph.nodes = MagicMock(return_value=[])
        mock_core.config.dimensionality = 4
        mock_core.config.base_jeans_mass = 1.0

        engine = ExcitonEngine(manifold_core=mock_core)

        start = np.array([0.0, 0.0, 0.0, 0.0])
        vel = np.array([1.0, 0.5, 0.0, 0.0])
        target = np.array([2.0, 2.0, 1.0, 1.0])

        trajectory = engine.dispatch_geodesic_exciton(
            start_coords=start,
            initial_velocity=vel,
            target_coords=target,
            steps=25,
            g_ij=np.eye(4) * 1.5
        )

        assert len(trajectory) == 25
        final_pos = trajectory[-1].position

        # Agent should have moved towards the target
        dist_start_target = np.linalg.norm(start - target)
        dist_final_target = np.linalg.norm(final_pos - target)
        assert dist_final_target < dist_start_target
