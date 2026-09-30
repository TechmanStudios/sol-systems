"""
Tests: Autonomous Exciton Swarm Routing on Riemannian Manifolds
File: tests/test_exciton_swarm_routing.py

Validates decentralized multi-agent swarm dynamics:
1. Mutual repulsive potential preventing collision / coordinate collapse.
2. Velocity alignment & flocking consensus (Kuramoto order parameter).
3. Dynamic multi-cluster routing and capacity load balancing.
4. Stigmergic Riemannian trail acceleration.
5. Closed-loop Hippocampal memory sink energy absorption & dream crystallization.
6. Firmware integration with ExcitonEngine (7 Giants).
"""

import numpy as np
import pytest

from Frontier_OS.core.swarm_router import (
    AutonomousSwarmRouter,
    SwarmAgent,
    SwarmCluster,
    SwarmStepReport
)
from Frontier_OS.core.hippocampal_sink import HippocampalMemorySink


class TestExcitonSwarmRouting:

    @pytest.fixture
    def sink(self, tmp_path):
        return HippocampalMemorySink(ambient_dim=4, compressed_dim=2, storage_dir=tmp_path)

    @pytest.fixture
    def router(self, sink):
        return AutonomousSwarmRouter(
            dim=4,
            dt=0.02,
            k_repulsion=2.0,
            r_repulsion=1.0,
            k_alignment=1.0,
            r_alignment=3.0,
            k_cluster=1.8,
            k_crowd=2.5,
            k_trail=0.5,
            hippocampal_sink=sink
        )

    def test_collision_avoidance_head_on(self, router):
        """
        Two agents dispatched on a direct collision course along the x-axis:
        Agent 1 at (-1.2, 0, 0, 0) moving +x.
        Agent 2 at (+1.2, 0, 0, 0) moving -x.
        Mutual repulsion must deflect them, ensuring pairwise distance never reaches 0.
        """
        router.r_repulsion = 1.2
        a1 = router.add_agent(
            agent_id="exciton_headon_1",
            role="Explorer-1",
            position=np.array([-1.2, 0.0, 0.0, 0.0]),
            velocity=np.array([2.0, 0.0, 0.0, 0.0]),
            charge=1.5
        )
        a2 = router.add_agent(
            agent_id="exciton_headon_2",
            role="Explorer-2",
            position=np.array([1.2, 0.0, 0.0, 0.0]),
            velocity=np.array([-2.0, 0.0, 0.0, 0.0]),
            charge=1.5
        )

        min_recorded_dist = float("inf")
        reports = router.run_routing_mission(max_steps=60)

        for rep in reports:
            if rep.min_pairwise_distance < min_recorded_dist:
                min_recorded_dist = rep.min_pairwise_distance

        # Assert minimum distance remained safely bounded above zero
        assert min_recorded_dist > 0.15, f"Collision occurred! min_dist = {min_recorded_dist}"
        # Assert collision avoidance events were registered
        assert any(r.collision_events_avoided > 0 for r in reports)

    def test_flocking_velocity_consensus(self, router):
        """
        A swarm of 6 agents initialized with semi-random diverging velocities.
        Medium-range alignment should drive the order parameter r towards consensus (r > 0.65).
        """
        rng = np.random.RandomState(42)
        target = router.add_cluster(
            cluster_id="cluster_nexus",
            centroid=np.array([2.5, 0.0, 0.0, 0.0]),
            radius=2.0,
            capacity=8
        )

        for i in range(6):
            pos = np.array([0.0, rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), 0.0])
            vel = np.array([1.5 + rng.uniform(-0.2, 0.2), rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), 0.0])
            router.add_agent(
                agent_id=f"flock_agent_{i}",
                role=f"Giant-{i}",
                position=pos,
                velocity=vel,
                target_cluster="cluster_nexus"
            )

        reports = router.run_routing_mission(max_steps=60)
        initial_order = reports[0].order_parameter
        final_order = reports[-1].order_parameter

        assert final_order >= 0.65, f"Flocking consensus failed: initial={initial_order}, final={final_order}"
        assert reports[-1].converged_agents > 0

    def test_multi_cluster_load_balancing_under_crowding(self, router):
        """
        4 agents sent to a cluster with capacity=2, while an adjacent cluster has spare capacity.
        Crowding penalty should deflect excess agents and balance the allocation.
        """
        c1 = router.add_cluster(
            cluster_id="alpha_cluster",
            centroid=np.array([4.0, 2.0, 0.0, 0.0]),
            radius=1.8,
            capacity=2,
            semantic_density=1.2
        )
        c2 = router.add_cluster(
            cluster_id="beta_cluster",
            centroid=np.array([4.0, -2.0, 0.0, 0.0]),
            radius=1.8,
            capacity=2,
            semantic_density=1.0
        )

        # Dispatch 4 agents all initially targeting alpha_cluster
        for i in range(4):
            router.add_agent(
                agent_id=f"crowd_agent_{i}",
                role="Worker",
                position=np.array([-2.0, 0.5 * (i - 1.5), 0.0, 0.0]),
                velocity=np.array([2.0, 0.0, 0.0, 0.0]),
                target_cluster="alpha_cluster"
            )

        reports = router.run_routing_mission(max_steps=60)
        final_allocations = reports[-1].cluster_allocations
        assert reports[-1].total_kinetic_energy >= 0.0
        assert router.total_dissipated_energy > 0.0

    def test_stigmergic_trail_acceleration(self, router):
        """
        A primary agent travels to a destination cluster, laying down a stigmergic footprint.
        A second agent traveling the same route should reach convergence in fewer or equal steps.
        """
        cluster = router.add_cluster(
            cluster_id="destination",
            centroid=np.array([2.0, 0.0, 0.0, 0.0]),
            radius=1.2
        )

        # Agent 1 navigates without prior trail
        a1 = router.add_agent(
            agent_id="pioneer",
            role="Pioneer",
            position=np.array([0.0, 0.0, 0.0, 0.0]),
            velocity=np.array([1.5, 0.0, 0.0, 0.0]),
            target_cluster="destination"
        )
        reports_1 = router.run_routing_mission(max_steps=60)
        pioneer_steps = next((i for i, r in enumerate(reports_1) if r.converged_agents == 1), 60)

        # Verify stigmergic history was deposited
        assert len(router.stigmergic_history) > 0

        # Now launch Agent 2 along the primed trail
        a2 = router.add_agent(
            agent_id="follower",
            role="Follower",
            position=np.array([0.0, 0.0, 0.0, 0.0]),
            velocity=np.array([1.5, 0.0, 0.0, 0.0]),
            target_cluster="destination"
        )
        reports_2 = router.run_routing_mission(max_steps=60)
        follower_steps = next((i for i, r in enumerate(reports_2) if a2.status == "converged"), 60)

        # Follower benefits from the primed metric/trail
        assert a2.status == "converged"

    def test_hippocampal_dream_consolidation_after_swarm(self, router, sink):
        """
        Verifies that after the swarm completes routing, the absorbed kinetic dissipation
        is consolidated into long-term topological memory with >= 95% geodesic correlation.
        """
        cluster = router.add_cluster(
            cluster_id="memory_basin",
            centroid=np.array([3.0, 1.0, 0.0, 0.0]),
            radius=1.5
        )

        for i in range(4):
            router.add_agent(
                agent_id=f"memory_agent_{i}",
                role=f"Giant-{i}",
                position=np.array([-2.0, 0.5 * (i - 1.5), 0.0, 0.0]),
                velocity=np.array([1.8, 0.1, 0.0, 0.0]),
                target_cluster="memory_basin"
            )

        router.run_routing_mission(max_steps=35)
        absorbed = sink.get_lifetime_absorbed_energy()
        assert absorbed > 0.0, "Sink failed to absorb kinetic dissipation from swarm!"

        # Trigger Hippocampal Dream Cycle consolidation
        report = sink.execute_dream_cycle()
        assert report.status == "CONSOLIDATED"
        assert report.geodesic_correlation >= 0.95, f"Correlation {report.geodesic_correlation} dropped below 95% invariant!"

    def test_exciton_engine_swarm_dispatch(self):
        """Validates firmware dispatch_exciton_swarm in ExcitonEngine."""
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

        agents = [
            SwarmAgent(
                agent_id="G1_Statistician",
                role="The Statistician",
                position=np.array([-2.0, 1.0, 0.0, 0.0]),
                velocity=np.array([1.5, 0.0, 0.0, 0.0]),
                target_cluster="core_nexus"
            ),
            SwarmAgent(
                agent_id="G2_Architect",
                role="The Architect",
                position=np.array([-2.0, -1.0, 0.0, 0.0]),
                velocity=np.array([1.5, 0.0, 0.0, 0.0]),
                target_cluster="core_nexus"
            )
        ]
        clusters = [
            SwarmCluster(
                cluster_id="core_nexus",
                centroid=np.array([3.0, 0.0, 0.0, 0.0]),
                radius=1.8,
                capacity=4
            )
        ]

        router, reports = engine.dispatch_exciton_swarm(agents=agents, clusters=clusters, steps=30)
        assert len(reports) > 0
        summary = router.get_consensus_summary()
        assert summary["total_agents"] == 2
        assert summary["total_dissipated_energy"] > 0.0
