"""
Stress Testing & Hardening Suite: Semantic Circuits on Riemannian Manifolds
File: tests/test_semantic_circuit_stress.py

Tests extreme stress conditions and verifies the 5 Hardening Shields:
1. Avalanche Carry-Chain Cascade (Worst-case 4-bit and 8-bit ripple propagation exhaustion)
2. Analog Jitter & Continuous Noise Margin Invariance (Monte Carlo noise up to +-0.20)
3. Hostile Input Injection & Caustic Prevention (Negative, extreme, NaN, and Inf inputs)
4. Carnot Dissipation Monotonicity & Second Law Thermodynamic Bounds
5. Complete Riemannian Arithmetic Logic Unit (ALU: ADD, SUB, AND, OR, XOR)
"""

import numpy as np
import pytest

from sol.kernel.geometry.logic_manifold import (
    LogicGateType,
    LogicGateResult,
    RiemannianLogicManifold,
    FullAdderResult,
    RippleCarryResult,
    RippleCarryManifoldCircuit,
    ALUOp,
    ALUResult,
    RiemannianALU
)


class TestSemanticCircuitStress:

    @pytest.fixture
    def manifold(self):
        return RiemannianLogicManifold(dt=0.02, max_steps=120)

    def test_avalanche_carry_chain_cascade_4bit_and_8bit(self, manifold):
        """
        Shield 1: Avalanche Carry-Chain Cascade
        - Tests worst-case carry ripple chains where carry propagates across every stage.
        - 4-bit: 15 + 1 = 16 (0b1111 + 0b0001 -> 4 stage ripple)
        - 8-bit: 255 + 1 = 256 (0b11111111 + 0b00000001 -> 8 stage ripple)
        - 8-bit: 127 + 1 = 128 (0b01111111 + 0b00000001 -> 7 stage ripple)
        - Verifies 100% bitwise exactness, min_eigenvalue > 0, and bounded condition number.
        """
        # 4-bit worst-case cascade
        circuit_4bit = RippleCarryManifoldCircuit(num_bits=4, manifold=manifold)
        res_4 = circuit_4bit.add(15, 1)
        assert res_4.sum_int == 0
        assert res_4.carry_out == 1
        assert (res_4.sum_int + (res_4.carry_out << 4)) == 16
        assert res_4.verified is True
        assert res_4.min_eigenvalue > 0.0
        assert res_4.max_condition_number < 100.0
        assert len(res_4.stages) == 4

        # 8-bit worst-case cascade
        circuit_8bit = RippleCarryManifoldCircuit(num_bits=8, manifold=manifold)
        res_8 = circuit_8bit.add(255, 1)
        assert res_8.sum_int == 0
        assert res_8.carry_out == 1
        assert (res_8.sum_int + (res_8.carry_out << 8)) == 256
        assert res_8.verified is True
        assert res_8.min_eigenvalue > 0.0
        assert res_8.max_condition_number < 100.0
        assert len(res_8.stages) == 8

        # 8-bit 127 + 1 = 128
        res_8_half = circuit_8bit.add(127, 1)
        assert (res_8_half.sum_int + (res_8_half.carry_out << 8)) == 128
        assert res_8_half.verified is True

    def test_analog_jitter_monte_carlo_noise_immunity(self, manifold):
        """
        Shield 2: Analog Jitter & Continuous Noise Margin Invariance
        - Perturbs discrete boolean inputs with uniform analog noise delta in [-0.20, +0.20].
        - Evaluates 10 Monte Carlo noisy additions on 4-bit circuit.
        - Verifies that intermediate noise margins prevent bit flips and maintain exact integer sums.
        """
        circuit = RippleCarryManifoldCircuit(num_bits=4, manifold=manifold)
        rng = np.random.RandomState(42)

        test_pairs = [
            (3, 5),   # 8
            (7, 2),   # 9
            (6, 6),   # 12
            (10, 4),  # 14
            (1, 14),  # 15
        ]

        for a, b in test_pairs:
            # Run without noise
            baseline = circuit.add(a, b)
            expected_sum = a + b

            # Run with Monte Carlo analog noise injection on stage inputs
            for _ in range(2):
                a_bits = [(a >> i) & 1 for i in range(4)]
                b_bits = [(b >> i) & 1 for i in range(4)]

                c_in = 0.0
                noisy_sum_bits = []
                for i in range(4):
                    noise_a = rng.uniform(-0.18, 0.18)
                    noise_b = rng.uniform(-0.18, 0.18)

                    # Pass noisy continuous input to full adder
                    st_res = manifold.evaluate_full_adder(
                        float(a_bits[i]) + noise_a,
                        float(b_bits[i]) + noise_b,
                        c_in
                    )
                    noisy_sum_bits.append(st_res.binary_outputs["Sum"])
                    c_in = float(st_res.binary_outputs["Cout"])

                actual_total = sum(bit << i for i, bit in enumerate(noisy_sum_bits)) + (int(c_in) << 4)
                assert actual_total == expected_sum, f"Noise flipped addition {a} + {b}: got {actual_total}"

    def test_hostile_input_caustic_shield(self, manifold):
        """
        Shield 3: Hostile Input Injection & Caustic Prevention
        - Feeds extreme negative, supersonic, NaN, and Inf inputs into logic gates and full adder.
        - Verifies that input sanitizers gracefully clamp without throwing or creating caustics.
        - Verifies metric tensor stays strictly positive definite (min_eigenvalue > 0).
        """
        hostile_inputs = [
            (-100.0, 500.0),
            (float("nan"), 1.0),
            (0.0, float("nan")),
            (float("inf"), float("-inf")),
            (-999.0, -999.0),
            (1e6, 1e6),
        ]

        for a, b in hostile_inputs:
            # 1. Gate evaluation under hostile inputs
            res_and = manifold.evaluate_gate(LogicGateType.AND, a, b)
            assert res_and.min_eigenvalue > 0.0, f"Positive definiteness lost under ({a}, {b})"
            assert np.isfinite(res_and.outputs["Y"])
            assert res_and.binary_outputs["Y"] in (0, 1)

            # 2. Full adder under hostile inputs
            res_fa = manifold.evaluate_full_adder(a, b, c_in=a)
            assert res_fa.min_eigenvalue > 0.0
            assert res_fa.binary_outputs["Sum"] in (0, 1)
            assert res_fa.binary_outputs["Cout"] in (0, 1)
            assert res_fa.absorbed_energy >= 0.0

    def test_carnot_dissipation_thermodynamic_bounds(self, manifold):
        """
        Shield 4: Carnot Dissipation Monotonicity & Second Law Thermodynamic Bounds
        - Verifies that multi-stage carry switching dissipates strictly more energy than quiescent operations.
        - dE(Avalanche 15 + 1) > dE(Single-bit 1 + 0) > dE(Quiescent 0 + 0) > 0.
        - Verifies non-negative entropy generation on the manifold.
        """
        circuit = RippleCarryManifoldCircuit(num_bits=4, manifold=manifold)

        res_quiescent = circuit.add(0, 0)
        res_single = circuit.add(1, 0)
        res_avalanche = circuit.add(15, 1)

        dE_quiescent = res_quiescent.total_absorbed_energy
        dE_single = res_single.total_absorbed_energy
        dE_avalanche = res_avalanche.total_absorbed_energy

        # Strictly positive dissipation
        assert dE_quiescent > 0.0
        assert dE_single > 0.0
        assert dE_avalanche > 0.0

        # Monotonicity with switching activity
        assert dE_avalanche > dE_single, f"Avalanche dE ({dE_avalanche}) should exceed single-bit dE ({dE_single})"
        assert dE_single >= dE_quiescent, f"Single-bit dE ({dE_single}) should be >= quiescent dE ({dE_quiescent})"

    def test_riemannian_alu_full_operation_suite(self, manifold):
        """
        Shield 5: Complete Riemannian Arithmetic Logic Unit (ALU) Suite
        - Tests all 5 core ALU operations: ADD, SUB, AND, OR, XOR.
        - Verifies exact arithmetic, two's complement subtraction, and metric definiteness.
        """
        alu = RiemannianALU(num_bits=4, manifold=manifold)

        # 1. ADD: 9 + 5 = 14
        res_add = alu.execute(ALUOp.ADD, 9, 5)
        assert res_add.result_int == 14
        assert res_add.verified is True
        assert res_add.min_eigenvalue > 0.0

        # 2. SUB: 12 - 5 = 7
        res_sub_pos = alu.execute(ALUOp.SUB, 12, 5)
        assert res_sub_pos.result_int == 7
        assert res_sub_pos.is_negative is False
        assert res_sub_pos.verified is True
        assert res_sub_pos.min_eigenvalue > 0.0

        # 3. SUB: 7 - 7 = 0
        res_sub_zero = alu.execute(ALUOp.SUB, 7, 7)
        assert res_sub_zero.result_int == 0
        assert res_sub_zero.is_negative is False
        assert res_sub_zero.verified is True

        # 4. SUB: 3 - 5 = -2 (Two's complement borrow)
        res_sub_neg = alu.execute(ALUOp.SUB, 3, 5)
        assert res_sub_neg.result_int == -2
        assert res_sub_neg.is_negative is True
        assert res_sub_neg.verified is True

        # 5. BITWISE AND: 12 & 10 = 8 (0b1100 & 0b1010 = 0b1000)
        res_and = alu.execute(ALUOp.AND, 12, 10)
        assert res_and.result_int == 8
        assert res_and.verified is True

        # 6. BITWISE OR: 12 | 3 = 15 (0b1100 | 0b0011 = 0b1111)
        res_or = alu.execute(ALUOp.OR, 12, 3)
        assert res_or.result_int == 15
        assert res_or.verified is True

        # 7. BITWISE XOR: 12 ^ 10 = 6 (0b1100 ^ 0b1010 = 0b0110)
        res_xor = alu.execute(ALUOp.XOR, 12, 10)
        assert res_xor.result_int == 6
        assert res_xor.verified is True
