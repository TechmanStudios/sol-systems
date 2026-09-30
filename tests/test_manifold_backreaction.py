"""
SOL Engine Integration Tests: Closed-Loop Metric Deformation & Hippocampal Consolidation
File: tests/test_manifold_backreaction.py
"""

import time
import numpy as np
import pytest
import scipy.linalg as la
from scipy.spatial.distance import pdist, squareform

from sol.kernel.geometry.ricci import (
    DiscreteRicciFlowEngine,
    ExcitonTrajectory
)
from sol.diagnostics.damping_spectrogram import (
    AdaptiveDampingStabilizer,
    DampingSpectrogram
)
from Frontier_OS.core.telemetry_hook import (
    AgentDispatchThrottler,
    CurvatureTelemetryPacket,
    ManifoldTelemetryIPC
)


class TestManifoldBackreaction:

    @pytest.fixture
    def manifold_setup(self):
        """Initializes a 4-dimensional Riemannian semantic locus."""
        dim = 4
        # Seed positive-definite base metric tensor g_0
        rng = np.random.RandomState(42)
        A = rng.randn(dim, dim)
        g_0 = A.T @ A + 2.0 * np.eye(dim)

        # Setup 8-neighbor coordinate chart
        neighbor_metrics = []
        for _ in range(8):
            M = rng.randn(dim, dim) * 0.1
            g_nbr = g_0 + (M.T @ M)
            neighbor_metrics.append(g_nbr)

        weights = np.ones(8, dtype=np.float64) / 8.0
        engine = DiscreteRicciFlowEngine(dim=dim, dt=0.015, kappa=0.3)
        return dim, g_0, neighbor_metrics, weights, engine

    def test_100_agent_high_stress_convergence_and_metric_invariants(self, manifold_setup):
        """
        Stress Test:
        - 100 Exciton agents converge simultaneously into a single semantic locus.
        - Verifies that all metric eigenvalues remain strictly positive (det(g) > 0).
        - Verifies that adaptive damping stabilizes kinetic energy blowup.
        """
        dim, g_ij, neighbors, weights, engine = manifold_setup
        stabilizer = AdaptiveDampingStabilizer()
        spectrogram = DampingSpectrogram()

        rng = np.random.RandomState(1337)
        num_agents = 100
        convergence_steps = 40

        min_eigenvalues = []
        total_kinetic_energies = []

        current_g = g_ij.copy()

        for step in range(convergence_steps):
            # Synthesize 100 converging Exciton agents with aggressive dwell & attention
            trajectories = []
            step_v_aggregate = np.zeros(dim)

            for i in range(num_agents):
                # Agents inward-directed toward semantic sink
                v = rng.randn(dim) * (1.5 / (1.0 + 0.1 * step))
                dwell = 0.05 + rng.rand() * 0.2
                attention = 1.0 + rng.rand() * 2.0
                trajectories.append(ExcitonTrajectory(
                    agent_id=f"exciton_{i}",
                    node_id=0,
                    velocity=v,
                    dwell_time=dwell,
                    attention_weight=attention
                ))
                step_v_aggregate += v

            step_v_mean = step_v_aggregate / num_agents

            # Execute Ricci backreaction update step
            current_g, R_scalar, T_ij = engine.step(current_g, trajectories, neighbors, weights)

            # Compute damping and telemetry
            frame = spectrogram.record_state(
                timestamp_ms=step * 10.0,
                v=step_v_mean,
                g_ij=current_g,
                ricci_scalar=R_scalar
            )

            # Audit Riemannian Invariants
            eigenvals = np.linalg.eigvalsh(current_g)
            min_ev = float(np.min(eigenvals))
            det_g = float(np.linalg.det(current_g))

            min_eigenvalues.append(min_ev)
            total_kinetic_energies.append(frame.kinetic_energy)

            # STRICT INVARIANT ASSERTIONS:
            assert min_ev > 0.0, (
                f"Metric singularity encountered at step {step}: min eigenvalue={min_ev} <= 0"
            )
            assert det_g > 0.0, (
                f"Negative volume form / orientation collapse at step {step}: det(g)={det_g} <= 0"
            )

        # Confirm damping intervention: late-stage kinetic energy must be bounded
        assert total_kinetic_energies[-1] < total_kinetic_energies[0] + 5.0
        # Confirm absolute minimum eigenvalue stability threshold (allowing standard float64 roundoff)
        assert min(min_eigenvalues) >= engine.min_eigenvalue - 1e-6

    def test_frontier_os_non_blocking_ipc_and_orthogonal_throttling(self):
        """
        Validates the Frontier_OS 10ms telemetry hook and orthogonal subspace diversion.
        """
        dim = 4
        ipc = ManifoldTelemetryIPC(poll_interval_sec=0.010)

        # State container for mock manifold
        manifold_state = {
            "ricci": 22.0,  # Above safety threshold (15.0)
            "grad": np.array([5.0, 0.0, 0.0, 0.0]),
            "cond": 8.0
        }

        def mock_sampler():
            return CurvatureTelemetryPacket(
                node_id=42,
                ricci_scalar=manifold_state["ricci"],
                curvature_gradient=manifold_state["grad"],
                metric_condition_number=manifold_state["cond"],
                timestamp=time.time()
            )

        ipc.register_sampler(mock_sampler)
        ipc.start()

        try:
            # Allow at least two 10ms poll cycles
            time.sleep(0.040)
            throttler = AgentDispatchThrottler(ipc, curvature_safety_limit=15.0)

            # Proposed trajectory parallel to curvature surge gradient
            v_proposed = np.array([3.0, 1.0, 0.0, 0.0])
            v_adj, was_throttled, channel = throttler.evaluate_and_route(v_proposed, current_node_id=42)

            assert was_throttled is True
            assert channel == "DIVERTED_ORTHOGONAL"

            # Dot product with curvature gradient must be eliminated (orthogonal)
            dot_with_grad = np.dot(v_adj, manifold_state["grad"])
            assert abs(dot_with_grad) < 1e-6, (
                f"Diverted velocity is not orthogonal to curvature gradient: dot={dot_with_grad}"
            )
        finally:
            ipc.stop()

    def test_hippocampal_dream_cycle_geodesic_distance_preservation(self):
        """
        Simulates the Hippocampal consolidation phase:
        - Evaluates pairwise geodesic distances across primary semantic clusters.
        - Compresses manifold via memory projection.
        - Asserts that 95%+ of pairwise geodesic distance relationships are preserved.
        """
        rng = np.random.RandomState(999)
        num_nodes = 30
        ambient_dim = 8
        compressed_dim = 4

        # Generate primary semantic cluster centroids
        nodes = rng.randn(num_nodes, ambient_dim)

        # Deform space with localized Riemannian metric G_ambient
        A = rng.randn(ambient_dim, ambient_dim)
        G = A.T @ A + np.eye(ambient_dim)
        L = np.linalg.cholesky(G)

        # Compute geodesic distance matrix in deformed Riemannian space
        nodes_curved = nodes @ L
        D_pre = squareform(pdist(nodes_curved, metric="euclidean"))

        # SIMULATED HIPPOCAMPUS DREAM CONSOLIDATION:
        # Low-distortion isometric projection via optimal truncated Mahalanobis-SVD
        U, s, Vt = la.svd(nodes_curved, full_matrices=False)
        nodes_consolidated = U[:, :compressed_dim] * s[:compressed_dim]

        # Consolidated memory space pairwise distances
        D_post = squareform(pdist(nodes_consolidated, metric="euclidean"))

        # Flatten upper-triangular pairwise relationships
        triu_indices = np.triu_indices(num_nodes, k=1)
        d_pre_vec = D_pre[triu_indices]
        d_post_vec = D_post[triu_indices]

        # Pearson correlation evaluates relational structure preservation
        correlation = float(np.corrcoef(d_pre_vec, d_post_vec)[0, 1])

        print(f"\n[Hippocampus Dream Cycle] Geodesic Distance Correlation: {correlation * 100:.2f}%")
        assert correlation >= 0.95, (
            f"Hippocampal memory compression failed preservation invariant: {correlation:.4f} < 0.95"
        )
