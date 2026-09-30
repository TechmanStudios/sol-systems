"""
Tests: Semantic Logic Gates on Riemannian Manifolds
File: tests/test_semantic_logic_manifold.py

Validates constructive/destructive geodesic wave interference for:
- Boolean truth tables (AND, OR, NOT, XOR, NAND)
- 1-bit Riemannian Half-Adder (Sum = A ^ B, Carry = A & B)
- Metric tensor invariants (positive-definiteness, condition number, Ricci curvature)
- Continuous fuzzy interpolation and noise immunity
"""

import numpy as np
import pytest

from sol.kernel.geometry.logic_manifold import (
    LogicGateType,
    LogicGateResult,
    RiemannianLogicManifold
)


class TestSemanticLogicManifold:

    @pytest.fixture
    def manifold(self):
        return RiemannianLogicManifold(dt=0.02, max_steps=120)

    def test_and_gate_truth_table(self, manifold):
        """Verifies AND gate: only 1 & 1 -> 1, otherwise 0."""
        expected = [
            (0.0, 0.0, 0),
            (0.0, 1.0, 0),
            (1.0, 0.0, 0),
            (1.0, 1.0, 1),
        ]
        for a, b, exp in expected:
            res = manifold.evaluate_gate(LogicGateType.AND, a, b)
            assert res.binary_outputs["Y"] == exp, f"AND({a}, {b}) expected {exp}, got {res.binary_outputs['Y']} (P={res.outputs['Y']})"
            assert res.min_eigenvalue > 0.0
            assert res.max_condition_number < 100.0
            assert res.absorbed_energy > 0.0

    def test_or_gate_truth_table(self, manifold):
        """Verifies OR gate: 0 | 0 -> 0, otherwise 1."""
        expected = [
            (0.0, 0.0, 0),
            (0.0, 1.0, 1),
            (1.0, 0.0, 1),
            (1.0, 1.0, 1),
        ]
        for a, b, exp in expected:
            res = manifold.evaluate_gate(LogicGateType.OR, a, b)
            assert res.binary_outputs["Y"] == exp, f"OR({a}, {b}) expected {exp}, got {res.binary_outputs['Y']} (P={res.outputs['Y']})"
            assert res.min_eigenvalue > 0.0

    def test_not_gate_truth_table(self, manifold):
        """Verifies NOT gate: !0 -> 1, !1 -> 0."""
        res_0 = manifold.evaluate_gate(LogicGateType.NOT, 0.0)
        assert res_0.binary_outputs["Y"] == 1, f"NOT(0) expected 1, got {res_0.binary_outputs['Y']}"

        res_1 = manifold.evaluate_gate(LogicGateType.NOT, 1.0)
        assert res_1.binary_outputs["Y"] == 0, f"NOT(1) expected 0, got {res_1.binary_outputs['Y']}"

    def test_xor_gate_destructive_collision(self, manifold):
        """
        Verifies XOR gate via constructive single-ray lensing and destructive
        dual-ray collision scattering:
        0 ^ 0 -> 0
        0 ^ 1 -> 1
        1 ^ 0 -> 1
        1 ^ 1 -> 0 (destructive interference at central hyperbolic saddle)
        """
        expected = [
            (0.0, 0.0, 0),
            (0.0, 1.0, 1),
            (1.0, 0.0, 1),
            (1.0, 1.0, 0),
        ]
        for a, b, exp in expected:
            res = manifold.evaluate_gate(LogicGateType.XOR, a, b)
            assert res.binary_outputs["Y"] == exp, f"XOR({a}, {b}) expected {exp}, got {res.binary_outputs['Y']} (P={res.outputs['Y']})"
            assert res.min_eigenvalue > 0.0
            assert res.max_condition_number < 100.0

    def test_nand_gate_truth_table(self, manifold):
        """Verifies NAND gate: complementary to AND."""
        expected = [
            (0.0, 0.0, 1),
            (0.0, 1.0, 1),
            (1.0, 0.0, 1),
            (1.0, 1.0, 0),
        ]
        for a, b, exp in expected:
            res = manifold.evaluate_gate(LogicGateType.NAND, a, b)
            assert res.binary_outputs["Y"] == exp, f"NAND({a}, {b}) expected {exp}, got {res.binary_outputs['Y']}"

    def test_half_adder_dual_output(self, manifold):
        """
        Verifies 1-bit Riemannian Half-Adder:
        A + B -> Sum (A ^ B), Carry (A & B)
        (0, 0) -> S=0, C=0
        (0, 1) -> S=1, C=0
        (1, 0) -> S=1, C=0
        (1, 1) -> S=0, C=1
        """
        expected = [
            (0.0, 0.0, 0, 0),
            (0.0, 1.0, 1, 0),
            (1.0, 0.0, 1, 0),
            (1.0, 1.0, 0, 1),
        ]
        for a, b, exp_sum, exp_carry in expected:
            res = manifold.evaluate_half_adder(a, b)
            s = res.binary_outputs["Sum"]
            c = res.binary_outputs["Carry"]
            assert (s, c) == (exp_sum, exp_carry), f"Half-Adder({a}, {b}) expected (S={exp_sum}, C={exp_carry}), got (S={s}, C={c})"
            assert res.min_eigenvalue > 0.0
            assert res.absorbed_energy > 0.0

    def test_metric_positive_definiteness_invariants(self, manifold):
        """Scans grid of points and ensures g_ij >> 0, det(g) > 0 across continuous input space."""
        xs = np.linspace(-4.0, 4.0, 9)
        ys = np.linspace(-3.0, 3.0, 7)
        for a, b in [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0)]:
            for px in xs:
                for py in ys:
                    pt = np.array([px, py])
                    g = manifold.evaluate_metric(pt, LogicGateType.XOR, a, b)
                    evals = np.linalg.eigvalsh(g)
                    assert np.all(evals > 0), f"Metric lost positive-definiteness at {pt}: evals={evals}"
                    det = np.linalg.det(g)
                    assert det > 1e-6, f"Metric volume collapsed: det={det}"
                    cond = np.max(evals) / np.min(evals)
                    assert cond < 100.0, f"Condition number blown up: cond={cond}"

    def test_noise_tolerance(self, manifold):
        """Verifies that small noise perturbations (|eps| <= 0.15) do not flip boolean outcomes."""
        rng = np.random.RandomState(42)
        for _ in range(5):
            noise_a = rng.uniform(-0.15, 0.15)
            noise_b = rng.uniform(-0.15, 0.15)

            # AND noise test around (1, 1)
            res_and_11 = manifold.evaluate_gate(LogicGateType.AND, 1.0 + noise_a, 1.0 + noise_b)
            assert res_and_11.binary_outputs["Y"] == 1

            # AND noise test around (0, 1)
            res_and_01 = manifold.evaluate_gate(LogicGateType.AND, max(0.0, 0.0 + noise_a), 1.0 + noise_b)
            assert res_and_01.binary_outputs["Y"] == 0

            # XOR noise test around (1, 1)
            res_xor_11 = manifold.evaluate_gate(LogicGateType.XOR, 1.0 + noise_a, 1.0 + noise_b)
            assert res_xor_11.binary_outputs["Y"] == 0

            # XOR noise test around (1, 0)
            res_xor_10 = manifold.evaluate_gate(LogicGateType.XOR, 1.0 + noise_a, max(0.0, 0.0 + noise_b))
            assert res_xor_10.binary_outputs["Y"] == 1

    def test_continuous_fuzzy_monotonicity(self, manifold):
        """Verifies that varying input a smoothly continuously shifts the output probability."""
        probs = []
        for a in np.linspace(0.0, 1.0, 6):
            res = manifold.evaluate_gate(LogicGateType.OR, a, 0.0)
            probs.append(res.outputs["Y"])

        # P(OR(a, 0)) should be non-decreasing with increasing a
        for i in range(len(probs) - 1):
            assert probs[i+1] >= probs[i] - 0.05, f"Monotonicity violated: {probs}"

    def test_full_adder_truth_table(self, manifold):
        """Verifies 1-bit Full Adder for all 8 input combinations (A, B, Cin) -> (Sum, Cout)."""
        truth_table = [
            (0, 0, 0, 0, 0),
            (0, 0, 1, 1, 0),
            (0, 1, 0, 1, 0),
            (0, 1, 1, 0, 1),
            (1, 0, 0, 1, 0),
            (1, 0, 1, 0, 1),
            (1, 1, 0, 0, 1),
            (1, 1, 1, 1, 1),
        ]
        for a, b, cin, exp_sum, exp_cout in truth_table:
            res = manifold.evaluate_full_adder(float(a), float(b), float(cin))
            act_sum = res.binary_outputs["Sum"]
            act_cout = res.binary_outputs["Cout"]
            assert act_sum == exp_sum, f"FullAdder({a}, {b}, {cin}) Sum expected {exp_sum}, got {act_sum}"
            assert act_cout == exp_cout, f"FullAdder({a}, {b}, {cin}) Cout expected {exp_cout}, got {act_cout}"
            assert res.min_eigenvalue > 0.0, "Positive definiteness violated in full adder"
            assert res.absorbed_energy > 0.0, "Energy dissipation expected"

    def test_ripple_carry_4bit_addition(self, manifold):
        """Verifies 4-bit Ripple-Carry arithmetic circuit on continuous Riemannian manifold."""
        from sol.kernel.geometry.logic_manifold import RippleCarryManifoldCircuit

        circuit = RippleCarryManifoldCircuit(num_bits=4, manifold=manifold)

        test_cases = [
            (3, 5, 8),     # 0011 + 0101 = 1000
            (7, 6, 13),    # 0111 + 0110 = 1101
            (0, 0, 0),     # 0000 + 0000 = 0000
            (9, 4, 13),    # 1001 + 0100 = 1101
            (15, 1, 16),   # 1111 + 0001 = 10000 (overflow carry bit)
        ]

        for a, b, expected_sum in test_cases:
            res = circuit.add(a, b)
            actual_total = res.sum_int + (res.carry_out << 4)
            assert actual_total == expected_sum, f"Adder {a} + {b} expected {expected_sum}, got {actual_total}"
            assert res.verified is True
            assert res.min_eigenvalue > 0.0, "Strict positive-definiteness preserved across all stages"
            assert res.total_absorbed_energy > 0.0
            assert len(res.stages) == 4

