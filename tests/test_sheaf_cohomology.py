"""
Unit Tests for Sheaf-Theoretic Knowledge Cohomology & Global Semantic Consistency
=================================================================================
Vector 12 Test Suite verifying Cellular Sheaf operators, Coboundary Delta,
Betti numbers beta_0 and beta_1, harmonic projections, continuous diffusion,
topological self-repair, and the Cohomology Arbiter.
"""

import pytest
import numpy as np
import scipy.linalg as la

from Frontier_OS.core.cohomology.cellular_sheaf import CellularSheaf
from Frontier_OS.core.cohomology.cohomology_engine import CohomologyEngine
from Frontier_OS.core.cohomology.sheaf_diffusion import SheafDiffuser
from Frontier_OS.core.cohomology.topological_repair import TopologicalRepairEngine
from Frontier_OS.core.cohomology.cohomology_arbiter import CohomologyArbiter


class TestCellularSheafBasics:
    """Verifies fundamental cellular sheaf invariants and matrix assemblies."""

    def test_trivial_line_graph(self):
        """Line graph: A -- B -- C with 1D scalar stalks."""
        sheaf = CellularSheaf()
        sheaf.add_vertex("A", dim=1)
        sheaf.add_vertex("B", dim=1)
        sheaf.add_vertex("C", dim=1)

        sheaf.add_edge("e1", "A", "B", dim_edge=1)
        sheaf.add_edge("e2", "B", "C", dim_edge=1)

        assert sheaf.total_vertex_dim == 3
        assert sheaf.total_edge_dim == 2

        delta = sheaf.build_coboundary()
        assert delta.shape == (2, 3)

        # For e1: -x_A + x_B, for e2: -x_B + x_C
        expected_delta = np.array([
            [-1.0, 1.0, 0.0],
            [0.0, -1.0, 1.0]
        ])
        np.testing.assert_allclose(delta, expected_delta)

        laplacian = sheaf.build_laplacian()
        assert laplacian.shape == (3, 3)
        # Standard graph Laplacian for path graph P_3
        expected_L = np.array([
            [1.0, -1.0, 0.0],
            [-1.0, 2.0, -1.0],
            [0.0, -1.0, 1.0]
        ])
        np.testing.assert_allclose(laplacian, expected_L)

        # Positive semi-definiteness
        evals = np.linalg.eigvalsh(laplacian)
        assert np.all(evals >= -1e-10)

    def test_multi_dimensional_stalks(self):
        """Verifies multi-dimensional stalks (d_v = 3) with rotation restriction maps."""
        sheaf = CellularSheaf()
        sheaf.add_vertex("V1", dim=3)
        sheaf.add_vertex("V2", dim=3)

        # 90-degree rotation matrix around Z-axis
        R = np.array([
            [0.0, -1.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0]
        ])
        sheaf.add_edge("e12", "V1", "V2", dim_edge=3, source_map=np.eye(3), target_map=R)

        assert sheaf.total_vertex_dim == 6
        assert sheaf.total_edge_dim == 3

        delta = sheaf.build_coboundary()
        assert delta.shape == (3, 6)

        laplacian = sheaf.build_laplacian()
        assert laplacian.shape == (6, 6)
        # Symmetric check
        np.testing.assert_allclose(laplacian, laplacian.T)


class TestCohomologyEngine:
    """Verifies Betti number calculations and harmonic projections."""

    def test_betti_numbers_trivial_sheaf(self):
        """Connected graph with trivial connection must have beta_0 = dim(stalk) = 1."""
        sheaf = CellularSheaf()
        for v in ["V1", "V2", "V3", "V4"]:
            sheaf.add_vertex(v, dim=1)

        sheaf.add_edge("e1", "V1", "V2")
        sheaf.add_edge("e2", "V2", "V3")
        sheaf.add_edge("e3", "V3", "V4")
        sheaf.add_edge("e4", "V4", "V1")  # Cycle graph C_4

        engine = CohomologyEngine(sheaf)
        spec = engine.compute_spectrum()

        # beta_0 = 1 (one global consensus state: all equal)
        assert spec.beta_0 == 1
        # beta_1 = D_E - D_V + beta_0 = 4 - 4 + 1 = 1 (one independent cycle)
        assert spec.beta_1 == 1
        assert spec.algebraic_connectivity > 0.0

    def test_harmonic_decomposition(self):
        """Verifies that harmonic component has zero Dirichlet energy and is orthogonal."""
        sheaf = CellularSheaf()
        sheaf.add_vertex("A", dim=2)
        sheaf.add_vertex("B", dim=2)
        sheaf.add_edge("e", "A", "B", dim_edge=2)

        engine = CohomologyEngine(sheaf)
        spec = engine.compute_spectrum()

        # Input cochain with discordance
        x = np.array([1.0, 2.0, 3.0, 4.0])
        decomp = engine.decompose_cochain(x, spec)

        # Harmonic energy must be identically zero
        assert decomp.harmonic_energy < 1e-10
        # Discrepancy energy matches original energy
        assert np.isclose(decomp.discrepancy_energy, decomp.original_energy)
        # Harmonic and discrepancy cochains must be orthogonal
        ortho_dot = np.dot(decomp.harmonic_cochain, decomp.discrepancy_cochain)
        assert abs(ortho_dot) < 1e-10

        # Coboundary of harmonic component is zero
        cob_harm = sheaf.compute_coboundary_of(decomp.harmonic_cochain)
        assert np.linalg.norm(cob_harm) < 1e-10

    def test_mobius_contradiction_holonomy(self):
        """Verifies Mobius loop with reflection restriction map creates non-trivial obstruction."""
        arbiter = CohomologyArbiter()
        mobius_sheaf = arbiter.build_mobius_contradiction_sheaf()
        engine = CohomologyEngine(mobius_sheaf)
        spec = engine.compute_spectrum()

        # With reflection map in the 3-cycle, global consensus in that coordinate is obstructed!
        # beta_0 decreases, beta_1 increases
        assert spec.beta_1 >= 1

        cycle_spec = [
            ("edge_ab", "NODE_A", True),
            ("edge_bc", "NODE_B", True),
            ("edge_ca_twist", "NODE_C", True)
        ]
        holonomy = engine.compute_holonomy(cycle_spec)
        det_hol = float(np.linalg.det(holonomy))
        # Odd parity reflection gives negative determinant
        assert np.isclose(det_hol, -1.0)


class TestSheafDiffusion:
    """Verifies continuous heat diffusion dynamics and convergence."""

    def test_monotonic_energy_dissipation(self):
        """Verifies dE/dt <= 0 under semi-implicit integration."""
        sheaf = CellularSheaf()
        for i in range(5):
            sheaf.add_vertex(f"N{i}", dim=1)
        for i in range(4):
            sheaf.add_edge(f"e{i}", f"N{i}", f"N{i+1}")

        diffuser = SheafDiffuser(sheaf, diffusion_rate=1.0, dt=0.05)
        x_init = np.array([10.0, 2.0, 8.0, 1.0, 5.0])

        traj = diffuser.run_diffusion(x_init, max_steps=40, energy_tolerance=1e-5)

        assert traj.final_energy < traj.initial_energy
        assert traj.energy_reduction_ratio > 0.90
        assert traj.final_semantic_consistency > 0.95

        # Check monotonic decrease at each step
        energies = [s.dirichlet_energy for s in traj.steps]
        for k in range(len(energies) - 1):
            assert energies[k+1] <= energies[k] + 1e-12

    def test_analytical_vs_semi_implicit(self):
        """Verifies that semi-implicit stepping approximates matrix exponential solution."""
        sheaf = CellularSheaf()
        sheaf.add_vertex("A", dim=1)
        sheaf.add_vertex("B", dim=1)
        sheaf.add_edge("e", "A", "B")

        diffuser = SheafDiffuser(sheaf, diffusion_rate=0.5, dt=0.01)
        x_init = np.array([4.0, 0.0])

        x_analytical = diffuser.analytical_solution(x_init, t=0.5)

        # 50 steps of 0.01 = 0.5s
        x_num = x_init.copy()
        for _ in range(50):
            x_num = diffuser.step_semi_implicit(x_num, dt=0.01)

        np.testing.assert_allclose(x_num, x_analytical, rtol=1e-2, atol=1e-2)


class TestTopologicalRepair:
    """Verifies sheaf connection learning and surgical edge excision."""

    def test_sheaf_learning_adaptation(self):
        """Adapts edge restriction maps to accommodate persistent discordant beliefs."""
        sheaf = CellularSheaf()
        sheaf.add_vertex("A", dim=2)
        sheaf.add_vertex("B", dim=2)
        sheaf.add_edge("e", "A", "B", dim_edge=2)

        # Stubborn discordant beliefs
        x = np.array([1.0, 0.0, 0.0, 1.0])
        init_energy = sheaf.dirichlet_energy(x)
        assert init_energy > 0.1

        repairer = TopologicalRepairEngine(sheaf)
        report = repairer.repair_sheaf(x, allow_resection=False, iterations=60, learning_rate=0.2)

        assert report.final_energy < report.initial_energy * 0.01
        assert report.final_consistency > 0.99
        assert len(report.actions) > 0

    def test_surgical_edge_excision(self):
        """Excises an irreconcilable contradiction edge."""
        sheaf = CellularSheaf()
        sheaf.add_vertex("A", dim=1)
        sheaf.add_vertex("B", dim=1)
        sheaf.add_vertex("C", dim=1)

        sheaf.add_edge("e_good", "A", "B")
        sheaf.add_edge("e_bad", "B", "C")

        # States: A=5, B=5 (e_good is consistent), C=100 (e_bad is huge contradiction)
        x = np.array([5.0, 5.0, 100.0])
        repairer = TopologicalRepairEngine(sheaf)
        report = repairer.repair_sheaf(x, allow_resection=True, resection_threshold=10.0)

        # The bad edge should have been excised
        assert "e_bad" not in sheaf.edges
        assert "e_good" in sheaf.edges
        assert report.final_energy < 1e-10


class TestCohomologyArbiter:
    """Verifies high-level multi-agent topology auditing."""

    def test_seven_giants_audit(self):
        arbiter = CohomologyArbiter()
        sheaf = arbiter.build_seven_giants_sheaf()

        # All 7 giants in identical state (complete alignment)
        state_dict = {
            g: np.array([1.0, 2.0, 0.5])
            for g in ["STATISTICIAN", "OPTIMIZER", "N_BODY", "GRAPH_NAVIGATOR", "LINEAR_ALGEBRAIST", "ALIGNER", "INTEGRATOR"]
        }

        report = arbiter.audit_semantic_consistency(sheaf, state_dict, "7_GIANTS_MOA")
        assert report.is_globally_consistent is True
        assert report.semantic_consistency_score > 0.99
        assert report.dirichlet_energy < 1e-10
        assert report.has_topological_obstruction is False

    def test_dialectical_sheaf_audit(self):
        arbiter = CohomologyArbiter()
        sheaf = arbiter.build_dialectical_sheaf()

        # Proponent and adversary in compliant orthogonal state
        R = np.eye(4, dtype=np.float64)
        theta = np.pi / 4.0
        c, s = np.cos(theta), np.sin(theta)
        R[0:2, 0:2] = [[c, -s], [s, c]]

        v_prop = np.array([1.0, 0.0, 1.0, 1.0])
        # Adversary rotated by R
        v_adv = R @ v_prop

        state_dict = {
            "PROP_ALPHA": v_prop,
            "PROP_BETA": v_prop,
            "PROP_GAMMA": v_prop,
            "ADV_DELTA": v_adv,
            "ADV_EPSILON": v_adv,
            "ADV_ZETA": v_adv,
        }

        report = arbiter.audit_semantic_consistency(sheaf, state_dict, "DIALECTICAL_BIPARTITE")
        assert report.is_globally_consistent is True
        assert report.semantic_consistency_score > 0.99
        assert report.dirichlet_energy < 1e-10
