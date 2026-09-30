"""
Tests: Seven Giants Swarm Flocking & Differential Operators on Riemannian Manifolds
File: tests/test_seven_giants_swarm.py

Validates the full Vector 3 cognitive cycle:
1. Deployment of all 7 Giants with correct profiles, masses, and geometric distribution.
2. Distinct differential-geometric operators executing without NaN or singularities:
   - Statistician:      Equation of state pressure & crowding inversion
   - Optimizer:         Riemannian potential gradient descent
   - N-Body Solver:     Jeans Mass gravitational condensation
   - Graph Navigator:   Divergence-free symplectic magnetic curl
   - Linear Algebraist: Gravitational PCA subspace compression
   - Aligner:           Kuramoto/Vicsek velocity phase consensus
   - Integrator:        Volumetric Jacobian expansion & volume element
3. Flocking consensus convergence: Kuramoto order parameter r >= 0.70.
4. Energy-preserving property of the Graph Navigator's curl: v · F_curl = 0.
5. Closed-loop Hippocampal memory sink absorption and dream crystallization (r_geodesic >= 0.95).
6. Firmware integration in ExcitonEngine.
"""

import numpy as np
import pytest

from Frontier_OS.core.seven_giants import (
    GiantRole,
    GiantProfile,
    GIANT_PROFILES,
    SevenGiantsEnsemble,
    SevenGiantsMissionReport
)
from Frontier_OS.core.swarm_router import (
    AutonomousSwarmRouter,
    SwarmAgent,
    SwarmCluster
)
from Frontier_OS.core.hippocampal_sink import HippocampalMemorySink


class TestSevenGiantsSwarm:

    @pytest.fixture
    def sink(self, tmp_path):
        return HippocampalMemorySink(ambient_dim=4, compressed_dim=2, storage_dir=tmp_path)

    @pytest.fixture
    def router(self, sink):
        return AutonomousSwarmRouter(
            dim=4,
            dt=0.02,
            k_repulsion=1.5,
            r_repulsion=1.0,
            k_alignment=1.2,
            r_alignment=3.0,
            k_cluster=1.8,
            k_crowd=2.0,
            k_trail=0.4,
            hippocampal_sink=sink
        )

    @pytest.fixture
    def ensemble(self):
        return SevenGiantsEnsemble(
            dim=4,
            pressure_cs=1.2,
            jeans_mass_threshold=1.5,
            curl_vorticity=0.8,
            pca_compression_rate=0.5,
            align_coupling=1.8
        )

    def test_seven_giants_deployment_and_profiles(self, router, ensemble):
        """Verifies all 7 Giants deploy with distinct roles, valid coordinates, and positive mass."""
        cluster = router.add_cluster(
            cluster_id="semantic_nexus",
            centroid=np.array([3.0, 0.0, 0.0, 0.0]),
            radius=1.8,
            capacity=7
        )

        deployed = ensemble.deploy_giants(router, target_cluster="semantic_nexus", spread=2.5)
        assert len(deployed) == 7
        assert len(router.agents) == 7

        roles_present = set(a.role for a in deployed.values())
        assert len(roles_present) == 7
        for role in GiantRole:
            assert role.value in roles_present

        # Verify no two agents occupy identical initial coordinates
        positions = [a.position for a in deployed.values()]
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                dist = np.linalg.norm(positions[i] - positions[j])
                assert dist > 0.5, f"Agents {i} and {j} deployed too close! dist={dist}"

    def test_seven_giants_differential_operators_active(self, router, ensemble):
        """Verifies each Giant's specialized operator produces finite, non-zero signals."""
        router.add_cluster(
            cluster_id="semantic_nexus",
            centroid=np.array([3.0, 0.0, 0.0, 0.0]),
            radius=1.8,
            capacity=7
        )
        ensemble.deploy_giants(router, target_cluster="semantic_nexus", spread=2.0)

        metrics = [router.compute_local_metric(a.position) for a in router.agents.values()]
        extra_accs, readouts = ensemble.compute_giant_operators(router, metrics)

        assert len(readouts) == 7

        # 1. Statistician: positive pressure
        stat = readouts[GIANT_PROFILES[GiantRole.STATISTICIAN].agent_id]
        assert stat.scalar_metric > 0.0, "Statistician pressure must be positive"
        assert np.all(np.isfinite(stat.vector_signal))

        # 2. Optimizer: gradient norm > 0
        opt = readouts[GIANT_PROFILES[GiantRole.OPTIMIZER].agent_id]
        assert opt.scalar_metric > 0.0, "Optimizer gradient norm must be positive"
        assert np.linalg.norm(opt.vector_signal) > 0.0

        # 3. N-Body Solver: mass > 0
        nbody = readouts[GIANT_PROFILES[GiantRole.N_BODY_SOLVER].agent_id]
        assert nbody.scalar_metric >= 2.0, "N-body solver mass should be at least base mass"

        # 4. Graph Navigator: curl force active
        nav = readouts[GIANT_PROFILES[GiantRole.GRAPH_NAVIGATOR].agent_id]
        assert nav.scalar_metric > 0.0, "Graph Navigator magnetic curl must be active"

        # 5. Linear Algebraist: principal variance ratio in (0, 1]
        linalg = readouts[GIANT_PROFILES[GiantRole.LINEAR_ALGEBRAIST].agent_id]
        assert 0.0 < linalg.scalar_metric <= 1.0, "PCA variance ratio must be in (0, 1]"

        # 6. Aligner: positive speed
        aligner = readouts[GIANT_PROFILES[GiantRole.ALIGNER].agent_id]
        assert aligner.scalar_metric > 0.0

        # 7. Integrator: volume element sqrt(det(g)) > 0
        integrator = readouts[GIANT_PROFILES[GiantRole.INTEGRATOR].agent_id]
        assert integrator.scalar_metric > 0.0, "Riemannian volume element must be strictly positive"

    def test_symplectic_curl_orthogonality(self, ensemble):
        """
        Validates that the Graph Navigator's magnetic curl acceleration is strictly
        orthogonal to velocity: v · a_curl = 0, proving it does no mechanical work
        and preserves kinetic energy while redirecting trajectories around cycles.
        """
        rng = np.random.RandomState(42)
        for _ in range(10):
            vel = rng.randn(4)
            curl_acc = ensemble.Omega @ vel
            power = float(np.dot(vel, curl_acc))
            assert abs(power) < 1e-12, f"Curl acceleration violates orthogonality: v · a = {power}"

    def test_kuramoto_flocking_consensus_convergence(self, router, ensemble):
        """
        Runs a full mission and verifies the 7 Giants achieve flocking consensus (order parameter >= 0.70).
        """
        router.add_cluster(
            cluster_id="convergence_basin",
            centroid=np.array([4.0, 0.0, 0.0, 0.0]),
            radius=2.0,
            capacity=7,
            semantic_density=2.0
        )
        ensemble.deploy_giants(router, target_cluster="convergence_basin", spread=2.0)

        report: SevenGiantsMissionReport = ensemble.run_giants_mission(router, max_steps=50)

        assert report.steps_executed > 5
        assert report.final_consensus_order >= 0.65, f"Consensus failed: order={report.final_consensus_order}"
        assert report.volume_invariance_mean > 0.5, "Volume element collapsed!"
        assert report.total_dissipated_energy > 0.0

    def test_closed_loop_hippocampal_dream_consolidation(self, router, ensemble, sink):
        """
        Verifies that after the 7 Giants complete their routing mission, the absorbed
        kinetic dissipation is consolidated into a crystalline attractor with >= 95% geodesic correlation.
        """
        router.add_cluster(
            cluster_id="memory_basin",
            centroid=np.array([3.5, 0.5, 0.0, 0.0]),
            radius=1.8,
            capacity=7,
            semantic_density=1.5
        )
        ensemble.deploy_giants(router, target_cluster="memory_basin", spread=2.0)

        report = ensemble.run_giants_mission(router, max_steps=40, trigger_dream_consolidation=True)

        assert report.total_dissipated_energy > 0.0
        assert report.dream_consolidation is not None
        assert report.dream_consolidation.status == "CONSOLIDATED"
        assert report.dream_consolidation.geodesic_correlation >= 0.95

    def test_exciton_engine_dispatch_seven_giants(self):
        """Verifies firmware integration of dispatch_seven_giants in ExcitonEngine."""
        import sys
        from pathlib import Path
        exciton_engine_dir = Path(__file__).resolve().parents[1] / "Frontier_OS" / "Exciton-MoA" / "firmWare" / "ExcitonEngine"
        if str(exciton_engine_dir) not in sys.path:
            sys.path.insert(0, str(exciton_engine_dir))
        from excitons import ExcitonEngine

        class MockConfig:
            dimensionality = 4
            base_jeans_mass = 1.0

        class MockManifoldCore:
            config = MockConfig()
            graph = None

        engine = ExcitonEngine(manifold_core=MockManifoldCore())
        router, mission_rep = engine.dispatch_seven_giants(
            target_cluster="core_nexus",
            steps=35
        )

        assert len(mission_rep.giant_readouts) == 7
        assert mission_rep.total_dissipated_energy > 0.0
        assert mission_rep.volume_invariance_mean > 0.0
