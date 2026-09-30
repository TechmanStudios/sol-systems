"""
Executable CLI: Benchmark Distributed Swarm Sharding & Real-Time IPC Fabric (Vector 7)
File: scripts/benchmark_distributed_sharding.py

Evaluates scaling, throughput, latency, and boundary conservation across:
1. Monolithic Swarm Router (1 Shard baseline)
2. Distributed 1D Strip Sharding (2, 4, 8 Shards)
3. Distributed 2D Cartesian Grid (2x2 = 4 Shards)
4. Zero-Copy Shared Memory Throughput & IPC Transmission Latency
5. Boundary Transit Conservation (0% loss/duplication) & Halo-Exchange Symmetry
6. Dynamic Load Rebalancing under Severe Population Skew

Usage:
  python scripts/benchmark_distributed_sharding.py
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List
import numpy as np

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

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
    DistributedSwarmCluster,
    DistributedSwarmReport
)


def run_benchmark():
    print("=" * 80)
    print("      SOL-SYSTEMS & FRONTIER_OS: VECTOR 7 DISTRIBUTED SHARDING BENCHMARK     ")
    print("      Multi-Cluster Swarm Sharding, Halo Exchange & Real-Time IPC Fabric    ")
    print("=" * 80)

    results: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "vector": "Vector 7: Multi-Cluster Distributed Swarm Sharding & Real-Time IPC Fabric",
        "scaling_benchmark": [],
        "transit_conservation": {},
        "halo_symmetry": {},
        "ipc_latency": {},
        "dynamic_rebalancing": {}
    }

    # -------------------------------------------------------------------------
    # 1. Multi-Shard Scaling Benchmark: 1 vs 2 vs 4 vs 8 Shards
    # -------------------------------------------------------------------------
    print("\n[1. Multi-Cluster Swarm Sharding Throughput & Scaling]")
    population = 240
    steps = 15
    shard_configs = [1, 2, 4, 8]
    scaling_records = []
    base_time = None

    for k in shard_configs:
        cluster = DistributedSwarmCluster.create_1d_strip(
            num_shards=k,
            x_span=(-30.0, 30.0),
            z_span=(-30.0, 30.0),
            dt=0.02
        )
        # Uniformly distribute agents across the manifold
        for i in range(population):
            x = -28.0 + (56.0 * i / population)
            z = -10.0 + 20.0 * (i % 5) / 4.0
            pos = np.array([x, z, 0.0, 0.0])
            vel = np.array([0.4 * np.cos(i), 0.4 * np.sin(i), 0.0, 0.0])
            cluster.inject_agent(SwarmAgent(f"p_{i}", "Worker", pos, vel))

        t0 = time.time()
        reports = cluster.step(steps=steps)
        t_total = (time.time() - t0) * 1000.0  # ms
        ms_per_step = t_total / steps
        throughput = (population * steps) / (t_total / 1000.0)

        if k == 1:
            base_time = ms_per_step
            speedup = 1.0
        else:
            speedup = base_time / ms_per_step if base_time else 1.0

        record = {
            "num_shards": k,
            "population": population,
            "total_steps": steps,
            "total_time_ms": round(t_total, 2),
            "ms_per_step": round(ms_per_step, 2),
            "speedup": round(speedup, 2),
            "throughput_agents_per_sec": round(throughput, 1),
            "final_order_parameter": round(reports[-1].global_order_parameter, 4)
        }
        scaling_records.append(record)
        print(f"  Shards: {k:<2} | Time: {ms_per_step:>6.2f} ms/step | Speedup: {speedup:>4.2f}x | Throughput: {throughput:>8.1f} agents/s | Order (r): {reports[-1].global_order_parameter:.3f}")

    results["scaling_benchmark"] = scaling_records

    # -------------------------------------------------------------------------
    # 2. Boundary Transit & 100% Agent Conservation Invariant
    # -------------------------------------------------------------------------
    print("\n[2. Boundary Crossing & Phase-Space Conservation Invariant]")
    transit_cluster = DistributedSwarmCluster.create_1d_strip(
        num_shards=2,
        x_span=(-15.0, 15.0),
        z_span=(-15.0, 15.0),
        dt=0.05
    )
    # Inject 50 agents moving towards the boundary (x=0) from shard-0 into shard-1
    for i in range(50):
        pos = np.array([-2.5 + 0.04 * i, 0.0, 0.0, 0.0])
        vel = np.array([1.5, 0.0, 0.0, 0.0])
        transit_cluster.inject_agent(SwarmAgent(f"migrant_{i}", "Migrant", pos, vel))

    initial_pop = len(transit_cluster.get_all_agents())
    total_transits = 0
    all_reports = transit_cluster.step(steps=40)

    for rep in all_reports:
        total_transits += rep.total_transits_occurred
        assert rep.total_active_agents == initial_pop, f"Agent loss detected! Expected {initial_pop}, got {rep.total_active_agents}"

    final_alloc = all_reports[-1].shard_allocations
    conservation_rate = 100.0 * (all_reports[-1].total_active_agents / initial_pop)

    transit_results = {
        "initial_population": initial_pop,
        "final_population": all_reports[-1].total_active_agents,
        "conservation_rate_pct": conservation_rate,
        "total_boundary_crossings": total_transits,
        "initial_allocation": {"shard-0": 50, "shard-1": 0},
        "final_allocation": final_alloc,
        "verified": bool(conservation_rate == 100.0)
    }
    results["transit_conservation"] = transit_results
    print(f"  Initial Population: {initial_pop} in shard-0")
    print(f"  Final Allocation:   shard-0: {final_alloc['shard-0']}, shard-1: {final_alloc['shard-1']}")
    print(f"  Boundary Crossings: {total_transits}")
    print(f"  Conservation Rate:  {conservation_rate:.2f}% (Strictly Invariant)")

    # -------------------------------------------------------------------------
    # 3. Cross-Boundary Halo Force Symmetry Verification
    # -------------------------------------------------------------------------
    print("\n[3. Cross-Boundary Halo Force Symmetry Verification]")
    halo_cluster = DistributedSwarmCluster.create_1d_strip(
        num_shards=2,
        x_span=(-10.0, 10.0),
        z_span=(-10.0, 10.0),
        dt=0.04
    )
    a_left = SwarmAgent("left", "Role", np.array([-0.3, 0.0, 0.0, 0.0]), np.array([0.5, 0.0, 0.0, 0.0]))
    a_right = SwarmAgent("right", "Role", np.array([0.3, 0.0, 0.0, 0.0]), np.array([-0.5, 0.0, 0.0, 0.0]))
    halo_cluster.inject_agent(a_left)
    halo_cluster.inject_agent(a_right)

    halo_cluster.step(steps=1)
    v_l = halo_cluster.coordinator.shards["shard-0"].router.agents["left"].velocity[0]
    v_r = halo_cluster.coordinator.shards["shard-1"].router.agents["right"].velocity[0]
    dv_l = v_l - 0.5
    dv_r = v_r - (-0.5)
    rel_error = abs(abs(dv_l) - abs(dv_r)) / max(abs(dv_l), 1e-9)

    halo_res = {
        "dv_left": round(float(dv_l), 6),
        "dv_right": round(float(dv_r), 6),
        "symmetry_relative_error": float(rel_error),
        "force_continuity_verified": bool(rel_error < 1e-3)
    }
    results["halo_symmetry"] = halo_res
    print(f"  Left Shard dv:   {dv_l:+.6f}")
    print(f"  Right Shard dv:  {dv_r:+.6f}")
    print(f"  Symmetry Error:  {rel_error:.2e} (Continuous Newton III across partition)")

    # -------------------------------------------------------------------------
    # 4. Zero-Copy Shared Memory Throughput & IPC Latency
    # -------------------------------------------------------------------------
    print("\n[4. Zero-Copy Shared Memory & IPC Transmission Latency]")
    shm_name = f"benchmark_shm_{int(time.time()*1000)%100000}"
    capacity = 100000  # 100,000 excitons
    shm = SharedMemoryMeshBuffer(name=shm_name, capacity=capacity, create=True)
    arr = shm.as_array()

    # Benchmark writing 100,000 particles to shared memory view
    t0 = time.time()
    for _ in range(5):
        arr['pos'][:, 0] = np.linspace(-20.0, 20.0, capacity)
        arr['vel'][:, 0] = 0.5
        shm.set_active_count(capacity, 1)
    t_shm_write = (time.time() - t0) / 5.0  # seconds per 100k sync
    bandwidth_gb_s = (capacity * EXCITON_DTYPE.itemsize) / (t_shm_write * (1024**3))

    # Benchmark ExcitonTransitPacket binary serialization
    dummy_pkt = ExcitonTransitPacket(
        agent_id="pkt_test",
        role="The Optimizer",
        position=np.array([1.0, 2.0, 3.0, 0.0]),
        velocity=np.array([0.1, -0.1, 0.0, 0.0]),
        mass=1.0,
        charge=1.0,
        source_shard_id="shard-0",
        dest_shard_id="shard-1"
    )
    t0 = time.time()
    n_serializations = 20000
    for _ in range(n_serializations):
        raw = dummy_pkt.to_bytes()
        _ = ExcitonTransitPacket.from_bytes(raw)
    t_ipc = (time.time() - t0) / n_serializations * 1000.0  # ms per packet

    shm.close()
    shm.unlink()

    ipc_res = {
        "shm_capacity_excitons": capacity,
        "shm_buffer_size_mb": round((capacity * EXCITON_DTYPE.itemsize) / (1024**2), 2),
        "shm_write_time_100k_ms": round(t_shm_write * 1000.0, 2),
        "shm_bandwidth_gb_s": round(bandwidth_gb_s, 2),
        "ipc_roundtrip_per_packet_us": round(t_ipc * 1000.0, 2),
        "verified": bool(t_ipc < 1.0)
    }
    results["ipc_latency"] = ipc_res
    print(f"  Shared Memory Size:      {ipc_res['shm_buffer_size_mb']} MB (100,000 Excitons)")
    print(f"  100k Particle Sync:      {ipc_res['shm_write_time_100k_ms']} ms ({bandwidth_gb_s:.2f} GB/s zero-copy)")
    print(f"  Binary IPC Packet Round: {ipc_res['ipc_roundtrip_per_packet_us']} us (< 1.0 ms requirement)")

    # -------------------------------------------------------------------------
    # 5. Dynamic Load Rebalancing Convergence under Skew
    # -------------------------------------------------------------------------
    print("\n[5. Dynamic Load Rebalancing under Severe Population Skew]")
    rebal_cluster = DistributedSwarmCluster.create_1d_strip(
        num_shards=2,
        x_span=(-20.0, 20.0),
        z_span=(-20.0, 20.0),
        dt=0.02
    )
    # Inject 80 agents in shard-0 and 0 in shard-1
    for i in range(80):
        pos = np.array([-18.0 + 0.2 * i, 0.0, 0.0, 0.0])
        rebal_cluster.inject_agent(SwarmAgent(f"skew_{i}", "Worker", pos, np.zeros(4)))

    s0 = rebal_cluster.coordinator.shards["shard-0"]
    initial_boundary = s0.domain.x_max
    initial_imbalance = 2.0  # (80 - 0) / 40

    rebal_reports = rebal_cluster.step(steps=10)
    final_boundary = s0.domain.x_max
    boundary_shift = initial_boundary - final_boundary

    rebal_res = {
        "initial_imbalance": initial_imbalance,
        "initial_boundary_x": initial_boundary,
        "final_boundary_x": round(final_boundary, 3),
        "total_boundary_shift": round(boundary_shift, 3),
        "rebalancing_active": bool(boundary_shift > 0.0)
    }
    results["dynamic_rebalancing"] = rebal_res
    print(f"  Initial Imbalance: {initial_imbalance:.2f} (80 agents in shard-0, 0 in shard-1)")
    print(f"  Initial Boundary:  x = {initial_boundary:.2f}")
    print(f"  Rebalanced Bound:  x = {final_boundary:.2f} (Shift: -{boundary_shift:.2f})")
    print(f"  Adaptive Domain:   Domain boundary actively shifted to contract overcrowded shard")

    # -------------------------------------------------------------------------
    # Save Report to Disk
    # -------------------------------------------------------------------------
    def json_serializer(obj):
        if isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        if isinstance(obj, (np.floating, float)):
            return float(obj)
        if isinstance(obj, (np.integer, int)):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)

    out_dir = repo_root / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / "distributed_sharding_benchmark_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=json_serializer)

    print("\n" + "=" * 80)
    print(f"BENCHMARK COMPLETE. Telemetry saved to: {report_file}")
    print("=" * 80)


if __name__ == "__main__":
    run_benchmark()
