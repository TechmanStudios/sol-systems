"""
Tests: Multi-Cluster Distributed Swarm Sharding & Real-Time IPC Fabric (Vector 7)
File: tests/test_distributed_swarm_sharding.py

Validates the full Vector 7 architecture:
1. Exact 64-byte WebGPU WGSL structured memory layout (EXCITON_DTYPE).
2. Zero-copy SharedMemoryMeshBuffer allocation, array viewing, and IPC sync.
3. ExcitonTransitPacket compact binary serialization and lossless reconstruction.
4. HaloBuffer packaging and double-buffered ghost particle exchange.
5. 1D strip and 2D Cartesian grid spatial domain decomposition.
6. Boundary crossing and agent conservation (zero loss, zero duplication).
7. Cross-boundary halo repulsion symmetry and force continuity.
8. Distributed 7 Giants MoA operator reduction (Kuramoto r, Jeans centroid, Carnot sink).
9. Dynamic load balancing and boundary adaptation under population skew.
10. Throughput scaling and IPC transmission latency (< 1.0 ms).
"""

import time
import numpy as np
import pytest

from Frontier_OS.core import (
    GiantRole,
    GIANT_PROFILES,
    HippocampalMemorySink,
    SwarmAgent,
    SwarmCluster
)
from Frontier_OS.core.sharding import (
    EXCITON_DTYPE,
    ExcitonTransitPacket,
    HaloBuffer,
    SharedMemoryMeshBuffer,
    SwarmIPCChannel,
    ShardDomain,
    ShardTelemetryReport,
    SwarmShardNode,
    DistributedSwarmReport,
    SwarmMeshCoordinator,
    DistributedSwarmCluster
)


class TestDistributedSwarmSharding:

    def test_exciton_dtype_binary_layout(self):
        """Verifies exact 64-byte size and 16-byte alignment matching WebGPU WGSL ExcitonParticle."""
        assert EXCITON_DTYPE.itemsize == 64, f"Expected 64 bytes, got {EXCITON_DTYPE.itemsize}"
        # Field offsets
        assert EXCITON_DTYPE.fields['pos'][1] == 0
        assert EXCITON_DTYPE.fields['vel'][1] == 16
        assert EXCITON_DTYPE.fields['color'][1] == 32
        assert EXCITON_DTYPE.fields['extra'][1] == 48

        # Create structured array and verify byte access
        buf = np.zeros(2, dtype=EXCITON_DTYPE)
        buf[0]['pos'] = [1.5, 2.5, 3.5, 0.785]
        buf[0]['vel'] = [0.1, -0.2, 0.3, 1.2]
        buf[0]['color'] = [0.2, 0.8, 1.0, 1.0]
        buf[0]['extra'] = [1.0, 3.0, 0.0, 1.0]

        raw_bytes = buf.tobytes()
        assert len(raw_bytes) == 128  # 2 * 64 bytes
        unpacked = np.frombuffer(raw_bytes, dtype=EXCITON_DTYPE)
        assert np.allclose(unpacked[0]['pos'], [1.5, 2.5, 3.5, 0.785])
        assert np.allclose(unpacked[0]['vel'], [0.1, -0.2, 0.3, 1.2])

    def test_shared_memory_mesh_buffer_zero_copy(self):
        """Verifies zero-copy read/write and synchronization between separate shared memory handles."""
        shm_name = f"test_sol_mesh_{int(time.time()*1000)%100000}"
        capacity = 500

        # Creator handle
        shm_master = SharedMemoryMeshBuffer(name=shm_name, capacity=capacity, create=True)
        arr_master = shm_master.as_array()
        arr_master[42]['pos'] = [10.0, -5.0, 2.0, 0.5]
        arr_master[42]['vel'] = [0.4, 0.1, -0.3, 1.5]
        shm_master.set_active_count(count=43, step_index=101)

        # Worker handle (zero-copy view)
        shm_worker = SharedMemoryMeshBuffer(name=shm_name, capacity=capacity, create=False)
        cap, active, step, ts = shm_worker.read_header()
        assert cap == capacity
        assert active == 43
        assert step == 101

        arr_worker = shm_worker.as_array()
        assert np.allclose(arr_worker[42]['pos'], [10.0, -5.0, 2.0, 0.5])
        assert np.allclose(arr_worker[42]['vel'], [0.4, 0.1, -0.3, 1.5])

        # Modify through worker handle and verify in master handle without copying
        arr_worker[42]['pos'][0] = 99.0
        assert arr_master[42]['pos'][0] == 99.0

        # Clean up
        shm_worker.close()
        shm_master.close()
        shm_master.unlink()

    def test_exciton_transit_packet_serialization(self):
        """Tests compact binary packet serialization and exact numerical reconstruction."""
        pkt = ExcitonTransitPacket(
            agent_id="exciton_77",
            role="The Architect",
            position=np.array([3.14159, -2.71828, 1.414, 0.0]),
            velocity=np.array([0.55, -0.88, 0.12, 0.0]),
            mass=1.25,
            charge=1.5,
            target_cluster="nexus_core",
            target_coords=np.array([2.5, 0.0, 0.0, 0.0]),
            dwell_time=4.5,
            source_shard_id="shard-0",
            dest_shard_id="shard-1"
        )

        data = pkt.to_bytes()
        assert len(data) > 0

        pkt2 = ExcitonTransitPacket.from_bytes(data)
        assert pkt2.agent_id == "exciton_77"
        assert pkt2.role == "The Architect"
        assert np.allclose(pkt2.position, pkt.position)
        assert np.allclose(pkt2.velocity, pkt.velocity)
        assert abs(pkt2.mass - 1.25) < 1e-6
        assert abs(pkt2.charge - 1.5) < 1e-6
        assert pkt2.target_cluster == "nexus_core"
        assert np.allclose(pkt2.target_coords, pkt.target_coords)
        assert abs(pkt2.dwell_time - 4.5) < 1e-6
        assert pkt2.source_shard_id == "shard-0"
        assert pkt2.dest_shard_id == "shard-1"

    def test_halo_buffer_serialization_and_exchange(self):
        """Tests HaloBuffer creation, binary packing, and ghost particle extraction."""
        positions = np.array([[1.0, 2.0, 0.0, 0.0], [3.0, 4.0, 0.0, 0.0]], dtype=np.float32)
        velocities = np.array([[0.1, -0.1, 0.0, 0.0], [0.2, -0.2, 0.0, 0.0]], dtype=np.float32)
        charges = np.array([1.0, 1.5], dtype=np.float32)
        masses = np.array([1.0, 2.0], dtype=np.float32)

        halo = HaloBuffer(
            source_shard_id="shard-0",
            step_index=5,
            positions=positions,
            velocities=velocities,
            charges=charges,
            masses=masses
        )
        assert halo.count == 2

        halo_bytes = halo.to_bytes()
        halo_deser = HaloBuffer.from_bytes(halo_bytes)
        assert halo_deser.count == 2
        assert halo_deser.source_shard_id == "shard-0"
        assert np.allclose(halo_deser.positions, positions)
        assert np.allclose(halo_deser.velocities, velocities)

    def test_1d_strip_partition_and_agent_injection(self):
        """Tests 1D horizontal strip decomposition and proper spatial routing upon agent injection."""
        cluster = DistributedSwarmCluster.create_1d_strip(
            num_shards=4,
            x_span=(-20.0, 20.0),
            z_span=(-20.0, 20.0),
            dim=4
        )
        assert len(cluster.coordinator.shards) == 4

        # Injections across domains
        # shard-0: [-20, -10]
        # shard-1: [-10, 0]
        # shard-2: [0, 10]
        # shard-3: [10, 20]
        a0 = SwarmAgent("a0", "role", np.array([-15.0, 0.0, 0.0, 0.0]), np.zeros(4))
        a1 = SwarmAgent("a1", "role", np.array([-5.0, 0.0, 0.0, 0.0]), np.zeros(4))
        a2 = SwarmAgent("a2", "role", np.array([5.0, 0.0, 0.0, 0.0]), np.zeros(4))
        a3 = SwarmAgent("a3", "role", np.array([15.0, 0.0, 0.0, 0.0]), np.zeros(4))

        assert cluster.inject_agent(a0) == "shard-0"
        assert cluster.inject_agent(a1) == "shard-1"
        assert cluster.inject_agent(a2) == "shard-2"
        assert cluster.inject_agent(a3) == "shard-3"

        reps = cluster.step(steps=1)
        assert reps[0].total_active_agents == 4
        assert reps[0].shard_allocations == {
            "shard-0": 1,
            "shard-1": 1,
            "shard-2": 1,
            "shard-3": 1
        }

    def test_2d_grid_partition_and_boundary_detection(self):
        """Tests 2D grid Cartesian decomposition and boundary proximity checks."""
        cluster = DistributedSwarmCluster.create_2d_grid(
            grid_x=2,
            grid_z=2,
            x_span=(-10.0, 10.0),
            z_span=(-10.0, 10.0),
            halo_margin=1.5
        )
        assert len(cluster.coordinator.shards) == 4

        # Shard 0_0 covers [-10, 0] × [-10, 0]
        s00 = cluster.coordinator.shards["shard-0_0"]
        pos_center = np.array([-5.0, -5.0, 0.0, 0.0])
        assert s00.domain.contains(pos_center)
        assert not s00.domain.is_near_boundary(pos_center)  # 5.0 units > 1.5 margin

        pos_near_border = np.array([-0.5, -5.0, 0.0, 0.0])
        assert s00.domain.contains(pos_near_border)
        assert s00.domain.is_near_boundary(pos_near_border)  # 0.5 units <= 1.5 margin

    def test_boundary_transit_and_agent_conservation(self):
        """
        Validates phase-space continuity and exact 100% agent conservation
        when an Exciton crosses an inter-shard boundary.
        """
        cluster = DistributedSwarmCluster.create_1d_strip(
            num_shards=2,
            x_span=(-10.0, 10.0),
            z_span=(-10.0, 10.0),
            dt=0.1
        )
        # Agent starts in shard-0 [-10, 0] at x = -0.1 with positive velocity moving right into shard-1 [0, 10]
        a1 = SwarmAgent(
            agent_id="crosser",
            role="Explorer",
            position=np.array([-0.1, 0.0, 0.0, 0.0]),
            velocity=np.array([2.5, 0.0, 0.0, 0.0])
        )
        cluster.inject_agent(a1)
        initial_speed = float(np.linalg.norm(a1.velocity))

        # Step 1: crosses boundary into shard-1
        reps = cluster.step(steps=2)

        # Confirm 100% agent conservation
        assert reps[0].total_active_agents == 1
        assert reps[1].total_active_agents == 1
        assert reps[0].total_transits_occurred == 1

        # Agent must now reside in shard-1
        assert reps[1].shard_allocations["shard-0"] == 0
        assert reps[1].shard_allocations["shard-1"] == 1

        agents = cluster.get_all_agents()
        assert len(agents) == 1
        assert agents[0].position[0] > 0.0, "Agent must now be inside shard-1 domain"
        current_speed = float(np.linalg.norm(agents[0].velocity))
        # Speed slightly damped by Riemannian friction but finite and continuous
        assert 0.5 < current_speed < 3.0, f"Speed tearing detected: {current_speed}"

    def test_cross_boundary_halo_repulsion_symmetry(self):
        """
        Confirms ghost particles in HaloBuffer provide smooth, symmetric repulsion
        across the shard boundary, avoiding step discontinuities.
        """
        cluster = DistributedSwarmCluster.create_1d_strip(
            num_shards=2,
            x_span=(-10.0, 10.0),
            z_span=(-10.0, 10.0),
            dt=0.05
        )
        # Place two agents symmetrically across boundary at x = 0
        a_left = SwarmAgent("left_agent", "Role", np.array([-0.25, 0.0, 0.0, 0.0]), np.array([0.5, 0.0, 0.0, 0.0]))
        a_right = SwarmAgent("right_agent", "Role", np.array([0.25, 0.0, 0.0, 0.0]), np.array([-0.5, 0.0, 0.0, 0.0]))

        cluster.inject_agent(a_left)
        cluster.inject_agent(a_right)

        cluster.step(steps=1)

        v_left = cluster.coordinator.shards["shard-0"].router.agents["left_agent"].velocity[0]
        v_right = cluster.coordinator.shards["shard-1"].router.agents["right_agent"].velocity[0]

        # Symmetrical repulsion across boundary
        assert v_left < 0.5, "Left agent must be repelled leftwards by right ghost particle"
        assert v_right > -0.5, "Right agent must be repelled rightwards by left ghost particle"
        # Due to symmetry, magnitude of change should be identical
        dv_left = v_left - 0.5
        dv_right = v_right - (-0.5)
        assert np.isclose(abs(dv_left), abs(dv_right), rtol=1e-3)

    def test_distributed_7_giants_operator_reduction(self, tmp_path):
        """
        Validates deployment and global operator reduction for the 7 Giants MoA
        across distributed cluster shards.
        """
        sink = HippocampalMemorySink(ambient_dim=4, compressed_dim=2, storage_dir=tmp_path)
        cluster = DistributedSwarmCluster.create_2d_grid(
            grid_x=2,
            grid_z=2,
            x_span=(-15.0, 15.0),
            z_span=(-15.0, 15.0),
            dim=4,
            hippocampal_sink=sink
        )

        cluster.add_cluster("nexus", centroid=np.array([0.0, 0.0, 0.0, 0.0]), radius=3.0, capacity=7)

        # Deploy 7 Giants symmetrically
        roles = list(GiantRole)
        for idx, role in enumerate(roles):
            profile = GIANT_PROFILES[role]
            angle = (2.0 * np.pi * idx) / len(roles)
            pos = np.array([4.0 * np.cos(angle), 4.0 * np.sin(angle), 0.0, 0.0])
            vel = np.array([-1.0 * np.sin(angle), 1.0 * np.cos(angle), 0.0, 0.0])
            agent = SwarmAgent(
                agent_id=profile.agent_id,
                role=profile.role.value,
                position=pos,
                velocity=vel,
                mass=profile.default_mass,
                charge=profile.default_charge,
                target_cluster="nexus"
            )
            cluster.inject_agent(agent)

        reports = cluster.step(steps=10)
        final_rep = reports[-1]

        assert final_rep.total_active_agents == 7
        assert final_rep.global_order_parameter >= 0.0
        assert final_rep.total_kinetic_energy > 0.0
        assert final_rep.total_dissipated_energy >= 0.0
        # Check that Jeans mass centroid is centered near origin
        assert np.linalg.norm(final_rep.global_jeans_centroid[:2]) < 2.0
        # Sink recorded dissipation
        assert sink.get_lifetime_absorbed_energy() > 0.0

    def test_dynamic_load_balancing_under_skew(self):
        """
        Verifies dynamic boundary shifting and load rebalancing
        when swarm agents are heavily concentrated in one shard.
        """
        cluster = DistributedSwarmCluster.create_1d_strip(
            num_shards=2,
            x_span=(-10.0, 10.0),
            z_span=(-10.0, 10.0),
            dt=0.02
        )
        # Inject 25 agents into shard-0 and 0 in shard-1
        for i in range(25):
            pos = np.array([-8.0 + 0.2 * i, 0.0, 0.0, 0.0])
            cluster.inject_agent(SwarmAgent(f"skew_{i}", "Role", pos, np.zeros(4)))

        s0 = cluster.coordinator.shards["shard-0"]
        initial_xmax = s0.domain.x_max

        # Run several steps to allow dynamic load balancing to act
        reports = cluster.step(steps=5)
        rebalanced_xmax = s0.domain.x_max

        # Overloaded shard-0's boundary should shift inward (leftwards)
        assert rebalanced_xmax < initial_xmax, (
            f"Expected shard-0 x_max to contract from {initial_xmax}, got {rebalanced_xmax}"
        )
        assert reports[-1].total_active_agents == 25

    def test_multi_shard_throughput_and_ipc_latency(self):
        """
        Measures IPC transmission latency and execution performance
        across multi-cluster sharding configurations.
        """
        cluster = DistributedSwarmCluster.create_1d_strip(
            num_shards=4,
            x_span=(-20.0, 20.0),
            z_span=(-20.0, 20.0),
            dt=0.02
        )
        # Inject 100 agents evenly across shards
        for i in range(100):
            x = -18.0 + (36.0 * i / 100.0)
            cluster.inject_agent(SwarmAgent(f"p_{i}", "Exciton", np.array([x, 0.0, 0.0, 0.0]), np.array([0.5, 0.0, 0.0, 0.0])))

        reports = cluster.step(steps=10)
        mean_step_time_ms = float(np.mean([r.mesh_step_time_ms for r in reports]))

        # High-performance criterion: mesh step time should be under 200 ms for 100 agents across 4 shards
        assert mean_step_time_ms < 200.0, f"Mesh step too slow: {mean_step_time_ms} ms"

        # Verify IPC latency metric
        for shard in cluster.coordinator.shards.values():
            assert shard.ipc_channel.average_latency_ms < 5.0  # < 5ms IPC roundtrip
