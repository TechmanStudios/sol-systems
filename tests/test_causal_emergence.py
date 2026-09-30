"""
Unit & Integration Tests: Vector 6 Quantitative Causal Emergence (EI) Metrics
File: tests/test_causal_emergence.py

Verifies:
1. Information-theoretic bounds for Shannon entropy, Determinism, Degeneracy, and Effective Information (EI).
2. Exact numerical reproduction of Erik Hoel's foundational PNAS 2013 benchmarks (Fig 4 and Fig 2).
3. Continuous Riemannian Logic circuits exhibiting causal emergence (Delta EI > 0).
4. Hardening Shield analog restoration preserving macro EI under analog jitter.
5. 7 Giants MoA Cognitive Pipeline exhibiting causal emergence and emergence phase boundary.
"""

import pytest
import numpy as np

from sol.kernel.causal.effective_information import (
    CausalMetrics,
    CausalEmergenceReport,
    compute_entropy,
    compute_tpm_determinism,
    compute_tpm_degeneracy,
    compute_effective_information,
    compute_causal_metrics,
    coarse_grain_tpm,
    compute_causal_emergence,
    generate_hoel_canonical_network
)
from sol.kernel.causal.manifold_causal_analyzer import RiemannianCausalAnalyzer
from sol.kernel.causal.swarm_causal_analyzer import SwarmCausalAnalyzer
from sol.kernel.geometry.logic_manifold import RiemannianLogicManifold, LogicGateType


class TestInformationTheoreticBounds:
    """Tests fundamental information-theoretic mathematical invariants."""

    def test_shannon_entropy_properties(self):
        # 1. Non-negativity
        assert compute_entropy(np.array([1.0, 0.0, 0.0])) == 0.0

        # 2. Maximum entropy on uniform distribution
        for n in (2, 4, 8, 16):
            p_uniform = np.ones(n) / n
            expected_h = np.log2(n)
            assert np.isclose(compute_entropy(p_uniform), expected_h, atol=1e-12)

        # 3. 0 * log(0) convention
        p_sparse = np.array([0.5, 0.5, 0.0, 0.0])
        assert np.isclose(compute_entropy(p_sparse), 1.0, atol=1e-12)

    def test_identity_and_permutation_tpm(self):
        # Permutation / Identity matrix has maximal determinism, zero degeneracy, EI = log2(N)
        for n in (2, 4, 8):
            W_eye = np.eye(n)
            metrics = compute_causal_metrics(W_eye)
            assert np.isclose(metrics.determinism, np.log2(n), atol=1e-12)
            assert np.isclose(metrics.degeneracy, 0.0, atol=1e-12)
            assert np.isclose(metrics.effective_information, np.log2(n), atol=1e-12)
            assert np.isclose(metrics.effectiveness, 1.0, atol=1e-12)

    def test_completely_noisy_tpm(self):
        # Completely noisy TPM: each row is uniform -> zero determinism, zero EI
        for n in (2, 4, 8):
            W_noisy = np.ones((n, n)) / n
            metrics = compute_causal_metrics(W_noisy)
            assert np.isclose(metrics.determinism, 0.0, atol=1e-12)
            assert np.isclose(metrics.effective_information, 0.0, atol=1e-12)
            assert np.isclose(metrics.effectiveness, 0.0, atol=1e-12)

    def test_effective_information_non_negative_bound(self):
        # EI must always be >= 0
        np.random.seed(42)
        for _ in range(20):
            dim = np.random.randint(2, 10)
            W_rand = np.random.dirichlet(np.ones(dim), size=dim)
            metrics = compute_causal_metrics(W_rand)
            assert metrics.effective_information >= -1e-12
            assert metrics.effective_information <= metrics.max_possible_ei + 1e-12


class TestCanonicalHoelBenchmarks:
    """Tests exact numerical alignment with Erik Hoel's PNAS 2013 paper."""

    def test_hoel_fig4_degenerate_cycle_exact_match(self):
        """
        PNAS 2013 Fig 4:
        6 binary AND gates in a ring mapped to 3 macro COPY gates.
        N_micro = 64 -> N_macro = 8.
        Paper results:
            EI(Sm) = 2.43 bits
            EI(SM) = 3.00 bits
            Delta EI (CE) = +0.57 bits (0.566 bits exact)
            Determinism coef = 1.0, Degeneracy reduction = 3.566 bits
        """
        W_micro, mapping = generate_hoel_canonical_network("fig4_degenerate_cycle")
        report = compute_causal_emergence(W_micro, mapping)

        assert report.micro_metrics.state_dimension == 64
        assert report.macro_metrics.state_dimension == 8
        assert np.isclose(report.macro_metrics.effective_information, 3.000, atol=1e-3)
        assert np.isclose(report.micro_metrics.effective_information, 2.434, atol=1e-3)
        assert np.isclose(report.delta_ei, 0.566, atol=1e-3)
        assert report.has_causal_emergence is True
        assert np.isclose(report.degeneracy_reduction, 3.566, atol=1e-3)

    def test_hoel_fig2_noisy_and_emergence(self):
        """
        PNAS 2013 Fig 2:
        4 binary AND gates with noise eps mapped to 2 macro gates (N=16 -> N=4).
        Demonstrates emergence (Delta EI > 0) when noise eps <= 0.05.
        """
        W_micro, mapping = generate_hoel_canonical_network("fig2_noisy_and", noise_eps=0.01)
        report = compute_causal_emergence(W_micro, mapping)

        assert report.micro_metrics.state_dimension == 16
        assert report.macro_metrics.state_dimension == 4
        assert report.has_causal_emergence is True
        assert report.delta_ei > 0.20


class TestRiemannianLogicCircuitEmergence:
    """Tests causal emergence in continuous Riemannian geodesic circuits."""

    def test_coupled_riemannian_and_circuit(self):
        """
        Verifies that coupled continuous Riemannian AND circuits exhibit positive
        causal emergence (Delta EI > 0) via topological noise quenching.
        """
        analyzer = RiemannianCausalAnalyzer()
        report = analyzer.evaluate_coupled_network_emergence(
            gate_type=LogicGateType.AND,
            noise_sigma=0.05,
            use_shields=True,
            n_samples=3
        )

        assert report.micro_metrics.state_dimension == 16
        assert report.macro_metrics.state_dimension == 4
        assert report.has_causal_emergence is True
        assert report.delta_ei > 0.30
        assert np.isclose(report.macro_metrics.effective_information, 2.000, atol=0.05)
        assert report.degeneracy_reduction > 2.0

    def test_hardening_shield_noise_protection(self):
        """
        Verifies that under analog noise (sigma = 0.08), the 5 Hardening Shields
        (analog restoration sigmoid attractor) preserve or improve macro effective information.
        """
        analyzer = RiemannianCausalAnalyzer()
        rep_shielded = analyzer.evaluate_coupled_network_emergence(
            gate_type=LogicGateType.AND,
            noise_sigma=0.08,
            use_shields=True,
            n_samples=3
        )
        rep_unshielded = analyzer.evaluate_coupled_network_emergence(
            gate_type=LogicGateType.AND,
            noise_sigma=0.08,
            use_shields=False,
            n_samples=3
        )

        assert rep_shielded.macro_metrics.effective_information >= rep_unshielded.macro_metrics.effective_information - 1e-6
        assert rep_shielded.has_causal_emergence is True


class TestSwarmMoACausalEmergence:
    """Tests causal emergence in the 7 Giants MoA swarm architecture."""

    def test_giants_cognitive_pipeline_emergence(self):
        """
        Verifies that the 6 Giants / 3-Module Cognitive Pipeline (Perception -> Action -> Consensus)
        demonstrates positive causal emergence (Delta EI = +0.566 bits).
        """
        analyzer = SwarmCausalAnalyzer()
        report = analyzer.evaluate_giants_cognitive_pipeline(noise_eps=0.0)

        assert report.micro_metrics.state_dimension == 64
        assert report.macro_metrics.state_dimension == 8
        assert np.isclose(report.macro_metrics.effective_information, 3.000, atol=1e-3)
        assert np.isclose(report.micro_metrics.effective_information, 2.434, atol=1e-3)
        assert np.isclose(report.delta_ei, 0.566, atol=1e-3)
        assert report.has_causal_emergence is True

    def test_swarm_emergence_phase_transition(self):
        """
        Verifies that causal emergence is maintained across noise levels up to eps = 0.08,
        and transitions at the critical boundary eps* ~ 0.083.
        """
        analyzer = SwarmCausalAnalyzer()
        res = analyzer.evaluate_swarm_noise_sweep([0.0, 0.02, 0.05, 0.08, 0.10])

        # eps = 0.0, 0.02, 0.05, 0.08 should be emergent
        for i in range(4):
            assert res.has_emergence[i] is True
            assert res.delta_ei[i] > 0.0

        # eps = 0.10 transitions to reduction
        assert res.has_emergence[4] is False
        assert res.delta_ei[4] < 0.0
