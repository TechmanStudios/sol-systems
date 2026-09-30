"""
SOL Engine & Frontier_OS: Vector 10 Dialectical Reasoning & Arena Test Suite
File: tests/test_dialectical_reasoning.py

Tests the multi-agent dialectical reasoning architecture:
1. Proposition formulation and affirmative Thesis manifold synthesis.
2. Adversarial counter-example discovery and Lie-algebraic metric strain injection.
3. Quantitative causal ablation, node classification, and Minimal Causal Kernel extraction.
4. Hegelian-Kuramoto phase coupling (consensus vs. antiphase bifurcation).
5. Supreme Synthesis Arbiter verdicts and Dialectical Causal Emergence gain (Delta EI_dialectic > 0).
6. Closed-loop Hippocampal consolidation of verified theorems.
"""

import pytest
import numpy as np

from sol.kernel.synthesis.circuit_synthesizer import (
    TruthTableSpec,
    CANONICAL_SPECS,
    build_canonical_specs
)
from Frontier_OS.core.dialectics import (
    DialecticalProposition,
    PropositionType,
    EvidentiaryProofBundle,
    ProponentCluster,
    AdversaryChallengeReport,
    AttackVerdict,
    AdversaryCluster,
    NodeCausalClassification,
    AblationTelemetry,
    MinimalCausalKernel,
    QuantitativeCausalAblator,
    DialecticalVerdict,
    DialecticalTheoremReport,
    SynthesisArbiter,
    DialecticalArena,
    ArenaSessionReport
)


class TestDialecticalPropositions:
    """Verifies proposition formulation, specification mapping, and serialization."""

    def test_proposition_instantiation_and_serialization(self):
        canonical = build_canonical_specs()
        spec = canonical["MAJORITY_3"]

        prop = DialecticalProposition(
            prop_id="prop_majority_sound",
            prop_type=PropositionType.CANONICAL_SPEC,
            title="MAJORITY_3",
            claim_statement="The 3-input majority voter preserves continuous monotonicity and 100% truth table compliance.",
            target_spec=spec,
            expected_behavior={"monotonic": True}
        )

        d = prop.to_dict()
        assert d["prop_id"] == "prop_majority_sound"
        assert d["prop_type"] == "CANONICAL_SPEC"
        assert d["target_spec"]["num_cases"] == 8
        assert d["is_deliberately_flawed"] is False

    def test_deliberately_flawed_proposition_generation(self):
        canonical = build_canonical_specs()
        spec = canonical["XOR"]

        flawed_prop = DialecticalProposition(
            prop_id="prop_xor_flawed",
            prop_type=PropositionType.HYPOTHETICAL_PROPERTY,
            title="XOR",
            claim_statement="XOR can be computed without destructive soliton interference.",
            target_spec=spec,
            is_deliberately_flawed=True
        )

        proponent = ProponentCluster()
        bundle = proponent.synthesize_thesis_manifold(flawed_prop, max_swarm_steps=5)
        # Because it's deliberately flawed, truth table verification must fail
        assert bundle.is_verified is False
        assert bundle.accuracy < 1.0


class TestProponentThesisSynthesis:
    """Verifies Thesis Proponent Cluster synthesis and affirmative proof bundle generation."""

    def test_proponent_sound_thesis_synthesis(self):
        canonical = build_canonical_specs()
        spec = canonical["EQUALS_2BIT"]

        prop = DialecticalProposition(
            prop_id="prop_equals_2bit",
            prop_type=PropositionType.CANONICAL_SPEC,
            title="EQUALS_2BIT",
            claim_statement="Two 2-bit words are equivalent iff all corresponding bits coincide.",
            target_spec=spec
        )

        proponent = ProponentCluster()
        bundle = proponent.synthesize_thesis_manifold(prop, max_swarm_steps=10)

        assert bundle.is_verified is True
        assert bundle.accuracy == 1.0
        assert bundle.delta_ei > 0.0
        assert bundle.max_condition_number <= 100.0
        assert bundle.kuramoto_order >= 0.70
        assert len(bundle.witness_evaluations) == len(spec.table)


class TestAntithesisAdversaryInterrogation:
    """Verifies Adversary counter-example search, boundary fuzzing, and metric strain injection."""

    def test_adversary_catches_flawed_proposition(self):
        canonical = build_canonical_specs()
        spec = canonical["MAJORITY_3"]

        flawed_prop = DialecticalProposition(
            prop_id="prop_majority_corrupted",
            prop_type=PropositionType.HYPOTHETICAL_PROPERTY,
            title="MAJORITY_3",
            claim_statement="All-ones majority produces zero (deliberate falsehood).",
            target_spec=spec,
            is_deliberately_flawed=True
        )

        proponent = ProponentCluster()
        bundle = proponent.synthesize_thesis_manifold(flawed_prop, max_swarm_steps=5)

        adversary = AdversaryCluster()
        challenge_rep = adversary.challenge_thesis(flawed_prop, bundle)

        assert challenge_rep.verdict == AttackVerdict.REFUTED
        assert len(challenge_rep.counter_examples) > 0
        witness = challenge_rep.counter_examples[0]
        assert witness.attack_type == "DISCRETE_WITNESS"
        assert witness.expected_output != witness.observed_output

    def test_adversary_stress_tests_sound_thesis(self):
        canonical = build_canonical_specs()
        spec = canonical["XOR"]

        sound_prop = DialecticalProposition(
            prop_id="prop_xor_sound",
            prop_type=PropositionType.CANONICAL_SPEC,
            title="XOR",
            claim_statement="XOR destructive collision invariant holds across all inputs.",
            target_spec=spec
        )

        proponent = ProponentCluster()
        bundle = proponent.synthesize_thesis_manifold(sound_prop, max_swarm_steps=10)

        adversary = AdversaryCluster()
        challenge_rep = adversary.challenge_thesis(sound_prop, bundle, max_strain=0.20)

        # A sound thesis should have 0 discrete counter-examples
        assert len(challenge_rep.counter_examples) == 0
        assert challenge_rep.verdict in (AttackVerdict.SURVIVED, AttackVerdict.STRAIN_VULNERABLE)
        assert isinstance(challenge_rep.counter_delta_ei, float)
        assert bundle.delta_ei >= challenge_rep.counter_delta_ei


class TestQuantitativeCausalAblation:
    """Verifies node-by-node causal ablation, classification, and minimal kernel distillation."""

    def test_causal_ablation_extracts_minimal_kernel(self):
        canonical = build_canonical_specs()
        spec = canonical["MAJORITY_3"]

        proponent = ProponentCluster()
        prop = DialecticalProposition(
            prop_id="prop_ablation_maj",
            prop_type=PropositionType.CANONICAL_SPEC,
            title="MAJORITY_3",
            claim_statement="Majority 3 causal emergence and minimal kernel.",
            target_spec=spec
        )
        bundle = proponent.synthesize_thesis_manifold(prop, max_swarm_steps=10)

        ablator = QuantitativeCausalAblator()
        telemetry = ablator.ablate_circuit(bundle.circuit, spec, prop_id="MAJORITY_3")

        assert telemetry.original_accuracy == 1.0
        assert telemetry.original_delta_ei > 0.0
        assert len(telemetry.node_records) > 0

        # Check minimal kernel
        kernel = telemetry.minimal_kernel
        assert kernel.kernel_accuracy == 1.0
        assert len(kernel.core_node_ids) > 0
        assert kernel.kernel_node_count <= kernel.original_node_count
        assert kernel.kernel_delta_ei > 0.0
        # Occam Emergence: kernel delta EI is positive and non-negative gain
        assert kernel.occam_emergence_gain >= -0.05


class TestSynthesisArbiterAndVerdicts:
    """Verifies supreme dialectical verdicts, causal gains, and Hippocampal consolidation."""

    def test_arbiter_refutation_verdict(self):
        canonical = build_canonical_specs()
        spec = canonical["XOR"]

        flawed_prop = DialecticalProposition(
            prop_id="prop_arbiter_flawed",
            prop_type=PropositionType.HYPOTHETICAL_PROPERTY,
            title="XOR",
            claim_statement="XOR with corrupted cases",
            target_spec=spec,
            is_deliberately_flawed=True
        )

        proponent = ProponentCluster()
        bundle = proponent.synthesize_thesis_manifold(flawed_prop, max_swarm_steps=5)

        adversary = AdversaryCluster()
        challenge_rep = adversary.challenge_thesis(flawed_prop, bundle)

        ablator = QuantitativeCausalAblator()
        ablation_telem = ablator.ablate_circuit(bundle.circuit, spec, prop_id="XOR")

        arbiter = SynthesisArbiter()
        theorem = arbiter.resolve_debate(flawed_prop, bundle, challenge_rep, ablation_telem)

        assert theorem.verdict == DialecticalVerdict.THESIS_REFUTED
        assert theorem.counter_example_witness is not None
        assert theorem.consolidated_in_hippocampus is False

    def test_arbiter_synthesis_proved_with_causal_gain(self):
        canonical = build_canonical_specs()
        spec = canonical["MAJORITY_3"]

        sound_prop = DialecticalProposition(
            prop_id="prop_arbiter_sound",
            prop_type=PropositionType.CANONICAL_SPEC,
            title="MAJORITY_3",
            claim_statement="Majority 3 is universally monotonic.",
            target_spec=spec
        )

        proponent = ProponentCluster()
        bundle = proponent.synthesize_thesis_manifold(sound_prop, max_swarm_steps=10)

        adversary = AdversaryCluster()
        challenge_rep = adversary.challenge_thesis(sound_prop, bundle)

        ablator = QuantitativeCausalAblator()
        ablation_telem = ablator.ablate_circuit(bundle.circuit, spec, prop_id="MAJORITY_3")

        arbiter = SynthesisArbiter()
        theorem = arbiter.resolve_debate(sound_prop, bundle, challenge_rep, ablation_telem)

        assert theorem.verdict in (DialecticalVerdict.SYNTHESIS_PROVED, DialecticalVerdict.EMPIRICAL_COMPROMISE)
        assert theorem.invariant_accuracy == 1.0
        assert theorem.dialectic_causal_gain >= 0.05
        assert theorem.synthesis_delta_ei > 0.0
        if theorem.verdict == DialecticalVerdict.SYNTHESIS_PROVED:
            assert theorem.consolidated_in_hippocampus is True


class TestDialecticalArenaEndToEnd:
    """Verifies end-to-end multi-agent dialectical discourse arena session."""

    def test_arena_debate_successful_synthesis(self):
        canonical = build_canonical_specs()
        spec = canonical["EQUALS_2BIT"]

        prop = DialecticalProposition(
            prop_id="prop_arena_equals",
            prop_type=PropositionType.CANONICAL_SPEC,
            title="EQUALS_2BIT",
            claim_statement="2-bit equivalence holds with positive causal emergence.",
            target_spec=spec
        )

        arena = DialecticalArena(proponent_swarm_size=8, adversary_swarm_size=8)
        session = arena.conduct_debate(prop, max_debate_rounds=8)

        assert session.session_id.startswith("arena_prop_arena_equals_")
        assert session.proof_bundle.is_verified is True
        assert len(session.kuramoto_trajectory) == 8
        assert session.final_consensus_order > 0.50
        assert session.theorem_report.verdict in (DialecticalVerdict.SYNTHESIS_PROVED, DialecticalVerdict.EMPIRICAL_COMPROMISE)
        assert session.session_latency_ms > 0.0

        # Check serialization
        d = session.to_dict()
        assert "proposition" in d
        assert "proof_bundle" in d
        assert "adversary_report" in d
        assert "theorem_report" in d
        assert len(d["kuramoto_trajectory"]) == 8

    def test_arena_debate_refutation_trajectory(self):
        canonical = build_canonical_specs()
        spec = canonical["XOR"]

        flawed_prop = DialecticalProposition(
            prop_id="prop_arena_refuted",
            prop_type=PropositionType.HYPOTHETICAL_PROPERTY,
            title="XOR",
            claim_statement="Flawed XOR specification",
            target_spec=spec,
            is_deliberately_flawed=True
        )

        arena = DialecticalArena(proponent_swarm_size=8, adversary_swarm_size=8)
        session = arena.conduct_debate(flawed_prop, max_debate_rounds=8)

        assert session.theorem_report.verdict == DialecticalVerdict.THESIS_REFUTED
        assert session.adversary_report.verdict == AttackVerdict.REFUTED
        assert session.adversary_report.counter_examples is not None
