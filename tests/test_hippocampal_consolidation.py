"""
Integration Tests: Closed-Loop Hippocampal Memory Sink & Dream Cycle Consolidation
File: tests/test_hippocampal_consolidation.py
"""

from pathlib import Path
import sys
import numpy as np
import pytest

# Ensure Exciton-MoA teleMetry directory is on sys.path
telemetry_dir = Path(__file__).resolve().parents[1] / "Frontier_OS" / "Exciton-MoA" / "teleMetry"
if str(telemetry_dir) not in sys.path:
    sys.path.insert(0, str(telemetry_dir))

from sol.kernel.geometry.ricci import DiscreteRicciFlowEngine
from Frontier_OS.core import (
    RiemannianGeodesicNavigator,
    HippocampalMemorySink,
    DreamConsolidationReport
)
from hippocampalReplay import HippocampalReplay


class TestHippocampalConsolidation:

    @pytest.fixture
    def setup_sink_and_manifold(self, tmp_path):
        """Sets up a test HippocampalMemorySink and 4D Riemannian manifold."""
        dim = 4
        sink = HippocampalMemorySink(
            ambient_dim=dim,
            compressed_dim=2,
            storage_dir=tmp_path,
            min_preservation_ratio=0.95
        )
        navigator = RiemannianGeodesicNavigator(dim=dim, dt=0.02)
        return dim, sink, navigator, tmp_path

    def test_kinetic_dissipation_absorption_loop(self, setup_sink_and_manifold):
        """
        Validates Invariant 2: Active agent kinetic energy is dissipated into
        the Hippocampal memory sink via gamma(v, R) damping.
        """
        dim, sink, navigator, _ = setup_sink_and_manifold
        rng = np.random.RandomState(42)

        # Base positive-definite metric tensor
        A = rng.randn(dim, dim)
        g_0 = A.T @ A + 2.0 * np.eye(dim)

        total_dissipated = 0.0
        num_excitons = 10
        steps_per_exciton = 15

        for i in range(num_excitons):
            node_id = f"node_{i:02d}"
            pos = rng.randn(dim) * 2.0
            vel = rng.randn(dim) * 1.5

            for step in range(steps_per_exciton):
                # Step exciton with high-curvature singularity proximity at odd nodes
                ricci_val = 15.0 if i % 2 == 1 else 0.5
                step_res = navigator.step_agent(
                    x=pos,
                    v=vel,
                    g_ij=g_0,
                    ricci_scalar=ricci_val
                )

                # Absorb dissipation into Hippocampus
                dE = sink.absorb_step(
                    node_id=node_id,
                    coords=step_res.position,
                    step_result=step_res,
                    g_ij=g_0,
                    dt=navigator.dt
                )
                total_dissipated += dE
                pos = step_res.position
                vel = step_res.velocity

        assert total_dissipated > 0.0
        assert np.isclose(sink.get_lifetime_absorbed_energy(), total_dissipated)
        # Verify node-level energy tracking
        assert len(sink.node_absorbed_energy) == num_excitons

    def test_dream_cycle_geodesic_preservation_invariant(self, setup_sink_and_manifold):
        """
        Executes the Hippocampal Dream Cycle:
        - Compresses short-term memory traces into persistent crystallized manifolds.
        - Asserts that pairwise geodesic distance correlation >= 95%.
        - Asserts that long-term archive records are appended.
        """
        dim, sink, navigator, tmp_path = setup_sink_and_manifold
        rng = np.random.RandomState(1337)

        # Populate sink with 20 distinct active semantic clusters
        A = rng.randn(dim, dim)
        g_0 = A.T @ A + 1.5 * np.eye(dim)

        for i in range(20):
            node_id = f"cluster_{i:02d}"
            pos = rng.randn(dim) * 3.0
            vel = rng.randn(dim) * 1.2
            step_res = navigator.step_agent(x=pos, v=vel, g_ij=g_0, ricci_scalar=2.0)
            sink.absorb_step(node_id, pos, step_res, g_0, dt=0.01)

        # Trigger Dream Cycle Consolidation
        report: DreamConsolidationReport = sink.execute_dream_cycle(pair_id="test-manifold-01")

        assert report.status == "CONSOLIDATED"
        assert report.pre_compression_nodes == 20
        assert report.compressed_dim <= dim
        # STRICT INVARIANT ASSERTION: >= 95% geodesic relationship preservation
        print(f"\n[Hippocampal Dream Cycle Correlation]: {report.geodesic_correlation * 100:.2f}%")
        assert report.geodesic_correlation >= 0.95, (
            f"Consolidation violated geodesic preservation invariant: {report.geodesic_correlation:.4f} < 0.95"
        )
        assert Path(report.long_term_record_path).exists()

    def test_hippocampal_replay_integration(self, setup_sink_and_manifold):
        """
        Verifies that HippocampalReplay correctly reads and analyzes crystallized
        dream cycle memory records from long-term storage.
        """
        dim, sink, navigator, tmp_path = setup_sink_and_manifold
        rng = np.random.RandomState(777)

        # Populate and consolidate memory in tmp_path
        g_0 = np.eye(dim) * 2.0
        for i in range(12):
            node_id = f"mem_node_{i:02d}"
            pos = rng.randn(dim) * 2.0
            vel = rng.randn(dim) * (2.0 if i == 0 else 0.5)  # node 0 absorbs high energy
            step_res = navigator.step_agent(x=pos, v=vel, g_ij=g_0, ricci_scalar=1.0)
            sink.absorb_step(node_id, pos, step_res, g_0, dt=0.02)

        sink.execute_dream_cycle(pair_id="replay-test-01")

        # Initialize HippocampalReplay pointed to the test working_data
        replay = HippocampalReplay(working_dir=tmp_path)

        dream_records = replay.load_dream_consolidation_records()
        assert len(dream_records) == 12

        summary = replay.summarize_dream_crystallization()
        assert summary["crystallized_nodes"] == 12
        assert summary["total_absorbed_dissipation"] > 0.0
        assert summary["mean_consensus_confidence"] >= 0.95
        # The highest energy node should lead the dominant crystal list
        assert summary["dominant_crystal_nodes"][0] == "mem_node_00"
