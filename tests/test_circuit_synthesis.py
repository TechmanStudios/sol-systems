"""
Unit & Integration Tests: Vector 8 Autonomous Self-Assembling Riemannian Semantic Circuits
File: tests/test_circuit_synthesis.py

Verifies:
1. Exact Boolean accuracy (100.0%, L_truth = 0.0) across all canonical specifications:
   XOR, MUX_2to1, MAJORITY_3, PARITY_3, EQUALS_2BIT, HALF_SUBTRACTOR, FULL_ADDER.
2. Generic Disjunctive Normal Form (DNF) manifold decomposition for arbitrary truth tables.
3. Strict positive-definiteness (g > 0, lambda_min >= 1e-4) and condition number (kappa <= 100).
4. Quantitative Causal Emergence (Delta EI > 0) via topological noise quenching and degeneracy reduction.
5. Neuro-Symbolic Reflection: DAG extraction, critical path analysis, propositional formula recovery,
   formal semantic equivalence verification, and Mermaid flowchart export.
6. Dynamic Online Metaplasticity: Self-healing convergence under thermal metric jitter and parameter drift.
"""

import numpy as np
import pytest
import scipy.linalg as la

from sol.kernel.synthesis.circuit_topology import (
    CircuitNode,
    CircuitNodeType,
    SelfAssembledCircuit
)
from sol.kernel.synthesis.circuit_synthesizer import (
    CANONICAL_SPECS,
    TruthTableSpec,
    RiemannianCircuitSynthesizer,
    build_canonical_specs
)
from sol.kernel.synthesis.symbolic_reflector import (
    CircuitDAG,
    SymbolicReflector
)
from sol.kernel.synthesis.metaplasticity import (
    MetaplasticityEngine,
    MetaplasticityReport
)


class TestCanonicalCircuitSynthesis:
    """Verifies autonomous synthesis and 100% accuracy of canonical specifications."""

    @pytest.fixture
    def synthesizer(self):
        return RiemannianCircuitSynthesizer()

    @pytest.mark.parametrize("spec_name", [
        "XOR",
        "MUX_2to1",
        "MAJORITY_3",
        "PARITY_3",
        "EQUALS_2BIT",
        "HALF_SUBTRACTOR",
        "FULL_ADDER"
    ])
    def test_canonical_specs_exact_accuracy(self, synthesizer, spec_name):
        """Verifies that all 7 canonical circuits achieve 100% accuracy and pass verification."""
        res = synthesizer.synthesize_canonical(spec_name)

        assert res.verified is True
        assert res.accuracy == 1.0
        assert res.iterations_used >= 1
        assert res.synthesis_time_ms < 500.0
        assert res.max_condition_number <= 100.0

        # Verify all case reports match expected outputs
        for case in res.case_reports:
            assert case["correct"] is True
            assert case["actual"] == case["expected"]

    def test_positive_definite_metric_invariants(self, synthesizer):
        """Shields 1 & 4: Verifies that every locus metric tensor satisfies g > 0 and kappa <= 100."""
        for spec_name in CANONICAL_SPECS:
            res = synthesizer.synthesize_canonical(spec_name)
            circuit = res.circuit

            for nid, node in circuit.nodes.items():
                g = node.compute_local_metric()
                evals = la.eigvalsh(g)
                min_eval = float(np.min(evals))
                max_eval = float(np.max(evals))
                cond = max_eval / max(min_eval, 1e-12)

                assert min_eval >= 1e-4, f"Node {nid} in {spec_name} has min eval {min_eval} < 1e-4"
                assert cond <= 100.0, f"Node {nid} in {spec_name} has cond {cond} > 100.0"
                # Check symmetry: g == g.T
                assert np.allclose(g, g.T, atol=1e-10)

    def test_generic_dnf_synthesis(self, synthesizer):
        """Verifies generic Disjunctive Normal Form (minterm) assembly for arbitrary truth tables."""
        # 3-input custom boolean function: Y = (A and not B) or (B and C)
        custom_table = {}
        for a in (0, 1):
            for b in (0, 1):
                for c in (0, 1):
                    y = 1 if ((a == 1 and b == 0) or (b == 1 and c == 1)) else 0
                    custom_table[(a, b, c)] = (y,)

        spec = TruthTableSpec(
            name="CUSTOM_DNF_FUNC",
            inputs=["A", "B", "C"],
            outputs=["Y"],
            table=custom_table,
            description="Custom 3-variable DNF expression"
        )

        res = synthesizer.synthesize(spec)
        assert res.verified is True
        assert res.accuracy == 1.0


class TestCausalEmergenceInSynthesizedCircuits:
    """Verifies Erik Hoel's quantitative Causal Emergence in synthesized Riemannian circuits."""

    @pytest.fixture
    def synthesizer(self):
        return RiemannianCircuitSynthesizer()

    def test_majority_voter_causal_emergence(self, synthesizer):
        """Verifies positive causal emergence (Delta EI > 0) on 3-input Majority Voter."""
        res = synthesizer.synthesize_canonical("MAJORITY_3")
        report = res.causal_emergence

        assert report is not None
        assert report.has_causal_emergence is True
        assert report.delta_ei > 0.30
        assert np.isclose(report.macro_metrics.effective_information, 2.000, atol=0.05)
        assert report.degeneracy_reduction > 2.0

    def test_multiplexer_causal_emergence(self, synthesizer):
        """Verifies positive causal emergence on 2-to-1 Multiplexer."""
        res = synthesizer.synthesize_canonical("MUX_2to1")
        report = res.causal_emergence

        assert report is not None
        assert report.has_causal_emergence is True
        assert report.delta_ei > 0.30
        assert report.macro_metrics.effective_information > report.micro_metrics.effective_information

    def test_equality_comparator_causal_emergence(self, synthesizer):
        """Verifies positive causal emergence on 2-bit Equality Comparator."""
        res = synthesizer.synthesize_canonical("EQUALS_2BIT")
        report = res.causal_emergence

        assert report is not None
        assert report.has_causal_emergence is True
        assert report.delta_ei > 0.30


class TestNeuroSymbolicReflection:
    """Verifies DAG extraction, boolean formula recovery, and formal equivalence."""

    @pytest.fixture
    def synthesizer(self):
        return RiemannianCircuitSynthesizer()

    @pytest.fixture
    def reflector(self):
        return SymbolicReflector()

    @pytest.mark.parametrize("spec_name", list(CANONICAL_SPECS.keys()))
    def test_semantic_equivalence_all_specs(self, synthesizer, reflector, spec_name):
        """Verifies 100% formal semantic equivalence of recovered symbolic expressions."""
        res = synthesizer.synthesize_canonical(spec_name)
        report = reflector.reflect(res.circuit, res.spec)

        assert report.is_equivalent is True
        assert len(report.simplified_expressions) == len(res.spec.outputs)
        assert report.dag.max_depth >= 1
        assert report.dag.critical_path_length >= 2
        assert report.dag.total_edges > 0

    def test_dag_structure_and_mermaid_generation(self, synthesizer, reflector):
        """Verifies DAG topological metrics and Mermaid diagram export."""
        res = synthesizer.synthesize_canonical("FULL_ADDER")
        report = reflector.reflect(res.circuit, res.spec)

        # Full Adder should have depth >= 3
        assert report.dag.max_depth >= 3
        assert report.dag.critical_path_length >= 4
        assert "SUM" in report.simplified_expressions
        assert "COUT" in report.simplified_expressions

        # Mermaid output checks
        mermaid = report.mermaid_markdown
        assert "```mermaid" in mermaid
        assert "flowchart LR" in mermaid
        assert "subgraph Inputs" in mermaid
        assert "subgraph Basins" in mermaid
        assert "SUM" in mermaid
        assert "COUT" in mermaid


class TestMetaplasticitySelfRepair:
    """Verifies online metaplasticity self-repair under metric distortion and thermal jitter."""

    @pytest.fixture
    def synthesizer(self):
        return RiemannianCircuitSynthesizer()

    @pytest.fixture
    def engine(self):
        return MetaplasticityEngine()

    def test_metric_regularization_guarantee(self, synthesizer, engine):
        """Verifies that metric regularization strictly bounds eigenvalues and condition numbers."""
        res = synthesizer.synthesize_canonical("MAJORITY_3")
        c = res.circuit

        # Inject extreme metric distortion
        engine.inject_perturbations(c, metric_noise_sigma=0.60, coord_noise_sigma=0.40, param_jitter_sigma=0.30)
        # Apply regularizer
        engine.regularize_metric_tensors(c)

        for node in c.nodes.values():
            g = node.compute_local_metric()
            cond = float(np.linalg.cond(g))
            min_ev = float(np.min(la.eigvalsh(g)))
            assert cond <= 100.0
            assert min_ev >= 1e-4

    def test_online_self_healing_convergence(self, synthesizer, engine):
        """Verifies that the metaplasticity engine restores accuracy and stability in < 15 steps."""
        for spec_name in ["XOR", "MUX_2to1", "MAJORITY_3", "HALF_SUBTRACTOR"]:
            res = synthesizer.synthesize_canonical(spec_name)
            c = res.circuit
            spec = res.spec

            # Inject moderate thermal noise
            engine.inject_perturbations(c, metric_noise_sigma=0.25, coord_noise_sigma=0.15, param_jitter_sigma=0.15)

            # Self-repair
            rep = engine.repair_circuit(c, spec)

            assert rep.is_healed is True
            assert rep.repaired_accuracy == 1.0
            assert rep.repaired_max_cond <= 100.0
            assert rep.steps_taken <= 15
            assert rep.repair_time_ms < 200.0
