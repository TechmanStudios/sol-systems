"""
SOL Engine & Frontier_OS: Vector 11 Automated Theorem Proving Test Suite
File: tests/test_automated_theorem_proving.py

Tests the autonomous mathematical discovery and theorem proving architecture:
1. Axiom system formulation across boolean, geometric, and causal domains.
2. Non-trivial conjecture generation and Shannon entropy evaluation.
3. Automated dialectical proof trajectories for De Morgan, Majority, and XOR invariants.
4. Counter-example refutation of false conjectures with witness certificates.
5. Theorem Corpus registration, Mermaid dependency DAGs, and formal Markdown monographs.
"""

import pytest
import numpy as np

from Frontier_OS.core.theorem_proving import (
    MathematicalDomain,
    AxiomDefinition,
    build_axiom_library,
    ConjectureType,
    MathematicalConjecture,
    AutonomousConjectureEngine,
    ProofVerdict,
    ProofStep,
    TheoremProofCertificate,
    AutomatedProofEngine,
    TheoremRecord,
    TheoremCorpus
)


class TestAxiomLibrary:
    """Verifies axiomatic foundations across all mathematical domains."""

    def test_axiom_library_completeness(self):
        axioms = build_axiom_library()
        assert len(axioms) >= 6
        assert "AXIOM_DEMORGAN_AND" in axioms
        assert "AXIOM_XOR_INVOLUTION" in axioms
        assert "AXIOM_MAJORITY_SELF_DUAL" in axioms
        assert "AXIOM_RICCI_POSITIVE_DEFINITE" in axioms
        assert "AXIOM_OCCAM_CAUSAL_EMERGENCE" in axioms

        demorgan = axioms["AXIOM_DEMORGAN_AND"]
        assert demorgan.domain == MathematicalDomain.BOOLEAN_ALGEBRA
        assert r"\neg" in demorgan.formula_latex

        d = demorgan.to_dict()
        assert d["axiom_id"] == "AXIOM_DEMORGAN_AND"
        assert d["domain"] == "BOOLEAN_ALGEBRA"


class TestConjectureEngine:
    """Verifies autonomous conjecture generation, non-triviality entropy, and catalog structure."""

    def test_conjecture_generation_and_entropy(self):
        engine = AutonomousConjectureEngine()
        catalog = engine.generate_conjecture_catalog()

        assert len(catalog) >= 5
        for conj in catalog:
            assert conj.conjecture_id != ""
            assert conj.entropy_score > 0.0  # Guarantees non-triviality (not constant function)
            assert len(conj.target_spec.table) > 0
            d = conj.to_dict()
            assert "conjecture_id" in d
            assert "latex_formula" in d

        # Check sound vs flawed conjectures
        sound_conjs = [c for c in catalog if not c.is_deliberately_false]
        flawed_conjs = [c for c in catalog if c.is_deliberately_false]
        assert len(sound_conjs) >= 4
        assert len(flawed_conjs) >= 2


class TestAutomatedProofEngine:
    """Verifies dialectical proof trajectories, sound verification, and counter-example refutation."""

    def test_prove_demorgan_nand_duality(self):
        engine = AutonomousConjectureEngine()
        prover = AutomatedProofEngine()

        catalog = engine.generate_conjecture_catalog()
        conj = next(c for c in catalog if c.conjecture_id == "conj_demorgan_nand")

        cert = prover.prove_conjecture(conj, max_debate_rounds=6)

        assert cert.verdict == ProofVerdict.PROVED_THEOREM
        assert cert.hegelian_consensus_order > 0.50
        assert cert.causal_emergence_gain >= 0.05
        assert cert.is_crystallized is True
        assert cert.counter_example_witness is None
        assert len(cert.proof_steps) == 5
        assert all(step.passed for step in cert.proof_steps)

    def test_prove_majority_self_duality(self):
        engine = AutonomousConjectureEngine()
        prover = AutomatedProofEngine()

        catalog = engine.generate_conjecture_catalog()
        conj = next(c for c in catalog if c.conjecture_id == "conj_majority_self_duality")

        cert = prover.prove_conjecture(conj, max_debate_rounds=6)

        assert cert.verdict == ProofVerdict.PROVED_THEOREM
        assert cert.is_crystallized is True
        assert cert.minimal_causal_kernel_nodes > 0

    def test_refute_flawed_xor_linear(self):
        engine = AutonomousConjectureEngine()
        prover = AutomatedProofEngine()

        catalog = engine.generate_conjecture_catalog()
        flawed_conj = next(c for c in catalog if c.conjecture_id == "conj_flawed_xor_linear")

        cert = prover.prove_conjecture(flawed_conj, max_debate_rounds=6)

        assert cert.verdict == ProofVerdict.DISPROVED_COUNTEREXAMPLE
        assert cert.is_crystallized is False
        assert cert.counter_example_witness is not None
        # Observed must not equal expected
        wit = cert.counter_example_witness
        assert wit["expected_output"] != wit["observed_output"]

    def test_refute_flawed_even_majority(self):
        engine = AutonomousConjectureEngine()
        prover = AutomatedProofEngine()

        catalog = engine.generate_conjecture_catalog()
        flawed_conj = next(c for c in catalog if c.conjecture_id == "conj_flawed_even_majority")

        cert = prover.prove_conjecture(flawed_conj, max_debate_rounds=6)

        assert cert.verdict == ProofVerdict.DISPROVED_COUNTEREXAMPLE
        assert cert.counter_example_witness is not None


class TestTheoremCorpusAndDAG:
    """Verifies theorem registration, Mermaid DAG generation, and monograph export."""

    def test_corpus_registration_and_export(self, tmp_path):
        corpus = TheoremCorpus()
        engine = AutonomousConjectureEngine()
        prover = AutomatedProofEngine()

        catalog = engine.generate_conjecture_catalog()
        conj_sound = next(c for c in catalog if c.conjecture_id == "conj_xor_associativity")
        conj_flawed = next(c for c in catalog if c.conjecture_id == "conj_flawed_xor_linear")

        # Prove sound conjecture
        cert_sound = prover.prove_conjecture(conj_sound, max_debate_rounds=5)
        thm_rec = corpus.add_proved_theorem(conj_sound, cert_sound)

        assert thm_rec.theorem_id == "THM_CONJ_XOR_ASSOCIATIVITY"
        assert thm_rec.proof_certificate.verdict == ProofVerdict.PROVED_THEOREM

        # Refute flawed conjecture
        cert_flawed = prover.prove_conjecture(conj_flawed, max_debate_rounds=5)
        corpus.add_refutation(conj_flawed, cert_flawed)

        assert len(corpus.theorems) == 1
        assert len(corpus.refutations) == 1

        # Check Mermaid DAG
        dag_mermaid = corpus.generate_mermaid_dag()
        assert "flowchart TD" in dag_mermaid
        assert "THM_CONJ_XOR_ASSOCIATIVITY" in dag_mermaid
        assert "AXIOM_XOR_INVOLUTION" in dag_mermaid

        # Check Markdown export
        export_file = tmp_path / "test_corpus.md"
        md_text = corpus.export_corpus_markdown(filepath=str(export_file))
        assert "# Formal Corpus of Proven Mathematical Theorems" in md_text
        assert "XOR Group Associativity" in md_text
        assert "Disproved Conjectures & Witness Certificates" in md_text
        assert export_file.exists()
