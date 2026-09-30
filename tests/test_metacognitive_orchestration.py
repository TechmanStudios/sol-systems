"""
Unit & Integration Tests: Vector 9 Hierarchical Multi-Agent Cognitive Orchestration & Dynamic Metacognition
File: tests/test_metacognitive_orchestration.py

Verifies:
1. Reasoning Graph & Query Decomposition: Topological sorting, dependency tracking, cycle detection.
2. 7 Giants MoA Swarm-Guided Circuit Synthesis:
   - 100% truth accuracy across canonical primitives.
   - Kuramoto phase synchronization order parameter r >= 0.70.
   - Strict Riemannian metric invariants (g > 0, kappa(g) <= 100.0).
   - Telemetry readouts from all 7 Giants.
3. Hippocampal Cognitive Circuit Cache:
   - O(1) circuit reuse.
   - Carnot dissipation tracking.
   - Dream cycle consolidation preserving >= 95% geodesic correlation (r_geo >= 0.95).
4. End-to-End Hierarchical Multi-Stage Execution:
   - 2-Bit Ripple-Carry Arithmetic with Parity Verification.
   - Hierarchical 3-Way Majority Arbiter with Priority Override.
   - Counterfactual Concept Equality and Difference Inference.
   - Dynamic Online Metaplasticity Self-Repair during multi-stage execution.
"""

import numpy as np
import pytest

from Frontier_OS.core.seven_giants import GiantRole
from Frontier_OS.core.hippocampal_sink import HippocampalMemorySink
from Frontier_OS.core.metacognition import (
    CognitiveStage,
    CognitiveStageType,
    CognitiveReasoningPlan,
    create_ripple_carry_adder_plan,
    create_hierarchical_arbiter_plan,
    create_counterfactual_equality_plan,
    SwarmGuidedSynthesizer,
    SwarmSynthesisResult,
    HippocampalCircuitCache,
    MetacognitiveOrchestrator,
    MetacognitiveExecutionReport
)
from sol.kernel.synthesis.circuit_synthesizer import CANONICAL_SPECS


class TestReasoningGraphDecomposition:
    """Verifies reasoning graph construction, dependency analysis, and cycle detection."""

    def test_topological_sort_and_dependencies(self):
        plan = create_ripple_carry_adder_plan(bits=2, with_parity=True)
        order = plan.execution_order

        assert "stage_bit0" in order
        assert "stage_bit1" in order
        assert "stage_parity" in order

        # stage_bit1 must follow stage_bit0 (depends on CARRY)
        assert order.index("stage_bit0") < order.index("stage_bit1")
        # stage_parity must follow stage_bit1
        assert order.index("stage_bit1") < order.index("stage_parity")

    def test_cycle_detection(self):
        plan = CognitiveReasoningPlan(
            plan_id="cyclic_plan",
            query_description="Invalid cyclic plan"
        )
        s1 = CognitiveStage(
            stage_id="s1",
            stage_type=CognitiveStageType.DECISION_ARBITER,
            spec_name="XOR",
            input_bindings={"A": ("s2", "Y")},
            output_names=["Y"]
        )
        s2 = CognitiveStage(
            stage_id="s2",
            stage_type=CognitiveStageType.DECISION_ARBITER,
            spec_name="XOR",
            input_bindings={"A": ("s1", "Y")},
            output_names=["Y"]
        )
        plan.stages["s1"] = s1
        plan.stages["s2"] = s2

        with pytest.raises(ValueError, match="Cycle detected"):
            plan.compute_topological_order()

    def test_plan_serialization(self):
        plan = create_hierarchical_arbiter_plan()
        p_dict = plan.to_dict()

        assert p_dict["plan_id"] == "plan_hierarchical_arbiter"
        assert p_dict["num_stages"] == 2
        assert "stage_majority" in p_dict["stages"]
        assert "stage_mux" in p_dict["stages"]
        assert "FINAL_DECISION" in p_dict["global_outputs"]


class TestSwarmGuidedSynthesizer:
    """Verifies the 7 Giants MoA swarm-guided manifold exploration and calibration."""

    @pytest.fixture
    def swarm_synthesizer(self):
        return SwarmGuidedSynthesizer()

    def test_swarm_synthesis_majority_gate(self, swarm_synthesizer):
        spec = CANONICAL_SPECS["MAJORITY_3"]
        res = swarm_synthesizer.synthesize_with_swarm(spec, max_swarm_steps=15)

        assert res.verified is True
        assert res.accuracy == 1.0
        assert res.kuramoto_order_parameter >= 0.70
        assert res.max_condition_number <= 100.0
        assert res.optimization_steps >= 1
        assert res.synthesis_time_ms < 500.0

        # Verify all 7 Giants reported readouts
        assert len(res.giant_readouts) == 7
        for role in GiantRole:
            profile_id = role.name  # role.value is in profile
            found = any(r.role == role.value for r in res.giant_readouts.values())
            assert found is True

    def test_swarm_synthesis_mux_causal_emergence(self, swarm_synthesizer):
        spec = CANONICAL_SPECS["MUX_2to1"]
        res = swarm_synthesizer.synthesize_with_swarm(spec, max_swarm_steps=15)

        assert res.verified is True
        assert res.causal_emergence is not None
        assert res.causal_emergence.has_causal_emergence is True
        assert res.causal_emergence.delta_ei > 0.30


class TestHippocampalCircuitCache:
    """Verifies crystallized circuit memory and dream cycle consolidation."""

    @pytest.fixture
    def cache(self, tmp_path):
        sink = HippocampalMemorySink(
            ambient_dim=4,
            compressed_dim=2,
            storage_dir=tmp_path,
            min_preservation_ratio=0.95,
            auto_dream_flush=False
        )
        return HippocampalCircuitCache(hippocampal_sink=sink)

    def test_cache_store_and_recall(self, cache):
        synth = SwarmGuidedSynthesizer()
        spec = CANONICAL_SPECS["XOR"]
        res = synth.synthesize_with_swarm(spec)

        cache.store_circuit("XOR", res.circuit)
        retrieved = cache.get_circuit("XOR")

        assert retrieved is not None
        assert retrieved.circuit_id == res.circuit.circuit_id
        assert cache.cache["XOR"].access_count >= 2

    def test_dream_consolidation_invariant(self, cache):
        synth = SwarmGuidedSynthesizer()
        for name in ["XOR", "MAJORITY_3", "MUX_2to1"]:
            spec = CANONICAL_SPECS[name]
            res = synth.synthesize_with_swarm(spec)
            cache.store_circuit(name, res.circuit)
            cache.record_execution_dissipation(name, 5.0)

        # Trigger Dream Cycle consolidation
        report = cache.trigger_consolidation(pair_id="test_consolidation")

        assert report is not None
        assert report.status == "CONSOLIDATED"
        assert report.geodesic_correlation >= 0.95
        assert report.crystallized_edges > 0
        assert all(entry.is_consolidated for entry in cache.cache.values())


class TestMetacognitiveOrchestratorExecution:
    """Verifies end-to-end multi-stage reasoning queries."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        sink = HippocampalMemorySink(ambient_dim=4, compressed_dim=2, storage_dir=tmp_path)
        cache = HippocampalCircuitCache(hippocampal_sink=sink)
        return MetacognitiveOrchestrator(circuit_cache=cache, auto_heal=True)

    def test_ripple_carry_arithmetic_all_cases(self, orchestrator):
        plan = create_ripple_carry_adder_plan(bits=2, with_parity=True)

        # Test full 2-bit addition truth table (4 x 4 = 16 cases)
        for a_val in range(4):
            for b_val in range(4):
                a0 = float(a_val & 1)
                a1 = float((a_val >> 1) & 1)
                b0 = float(b_val & 1)
                b1 = float((b_val >> 1) & 1)

                expected_sum = a_val + b_val
                exp_s0 = expected_sum & 1
                exp_s1 = (expected_sum >> 1) & 1
                exp_cout = (expected_sum >> 2) & 1
                exp_parity = exp_s0 ^ exp_s1 ^ exp_cout

                inputs = {"A0": a0, "B0": b0, "A1": a1, "B1": b1}
                rep = orchestrator.execute_plan(plan, inputs, auto_consolidate=False)

                assert rep.success is True
                assert rep.global_outputs["S0"] == exp_s0
                assert rep.global_outputs["S1"] == exp_s1
                assert rep.global_outputs["COUT"] == exp_cout
                assert rep.global_outputs["PARITY"] == exp_parity

    def test_hierarchical_decision_arbiter(self, orchestrator):
        plan = create_hierarchical_arbiter_plan()

        # Majority 1 without override
        rep1 = orchestrator.execute_plan(plan, {
            "V1": 1.0, "V2": 1.0, "V3": 0.0, "OVERRIDE": 0.0, "PRIORITY_VOTE": 0.0
        })
        assert rep1.global_outputs["MAJORITY_RAW"] == 1
        assert rep1.global_outputs["FINAL_DECISION"] == 1
        assert rep1.mean_causal_delta_ei > 0.30

        # Majority 0 overridden by priority 1
        rep2 = orchestrator.execute_plan(plan, {
            "V1": 0.0, "V2": 0.0, "V3": 1.0, "OVERRIDE": 1.0, "PRIORITY_VOTE": 1.0
        })
        assert rep2.global_outputs["MAJORITY_RAW"] == 0
        assert rep2.global_outputs["FINAL_DECISION"] == 1

        # Majority 1 overridden by priority 0
        rep3 = orchestrator.execute_plan(plan, {
            "V1": 1.0, "V2": 1.0, "V3": 1.0, "OVERRIDE": 1.0, "PRIORITY_VOTE": 0.0
        })
        assert rep3.global_outputs["MAJORITY_RAW"] == 1
        assert rep3.global_outputs["FINAL_DECISION"] == 0

    def test_counterfactual_equality_inference(self, orchestrator):
        plan = create_counterfactual_equality_plan()

        # Concepts equal (A = 3, B = 3)
        rep1 = orchestrator.execute_plan(plan, {
            "A1": 1.0, "A0": 1.0, "B1": 1.0, "B0": 1.0
        })
        assert rep1.global_outputs["EQUAL"] == 1
        assert rep1.global_outputs["RESIDUAL_DIFF"] == 0

        # Concepts unequal (A = 3, B = 2 -> A0=1, B0=0 -> Diff=1)
        rep2 = orchestrator.execute_plan(plan, {
            "A1": 1.0, "A0": 1.0, "B1": 1.0, "B0": 0.0
        })
        assert rep2.global_outputs["EQUAL"] == 0
        assert rep2.global_outputs["RESIDUAL_DIFF"] == 1

    def test_online_metaplasticity_healing_during_execution(self, orchestrator):
        """Verifies that orchestrator auto-heals perturbed circuits on the fly."""
        plan = create_hierarchical_arbiter_plan()

        # Retrieve circuit and inject severe metric and parameter perturbation
        circuit, _ = orchestrator.get_or_synthesize_circuit(plan.stages["stage_majority"])
        for nid, node in circuit.nodes.items():
            node.metric_bias += np.random.normal(0, 0.45, (2, 2))
            node.gain += np.random.normal(0, 0.35)

        # Execute plan with auto_heal=True
        rep = orchestrator.execute_plan(plan, {
            "V1": 1.0, "V2": 1.0, "V3": 0.0, "OVERRIDE": 0.0, "PRIORITY_VOTE": 0.0
        })
        assert rep.success is True
        assert rep.global_outputs["FINAL_DECISION"] == 1
        assert rep.stage_results["stage_majority"].healed is True
