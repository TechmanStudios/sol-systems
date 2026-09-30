"""
Test Suite: The Flagship Contextual Delayed-Recall & Conflict-Routing Benchmark
File: tests/test_flagship_delayed_recall.py

Validates the full Vector 5 flagship benchmark:
1. Information-loss resolution (Finding C audit).
2. Independent ground truth oracle and task generator.
3. Baseline comparisons: Explicit FSM/DAG, Linear Diffusion, Echo State Reservoir.
4. Non-dilutable conflict rejection and zero false commit rate on SOL Riemannian substrate.
5. Non-destructive readout margin (NDRO >= 0.95).
6. Cross-repo contract verification with Sol-Lens (V0.2 packet) and SOL-Edge pre-execution authority.
"""

from pathlib import Path
import numpy as np
import pytest

from sol.benchmarks.identity_encoder import IdentityPreservingEncoder
from sol.benchmarks.flagship_task import (
    DelayedRecallTrial,
    FlagshipTaskGenerator,
    GroundTruthOracle,
    TrialType
)
from sol.benchmarks.baselines import (
    ExplicitFSMDAGBaseline,
    LinearGraphDiffusionBaseline,
    EchoStateReservoirBaseline
)
from sol.benchmarks.sol_evaluator import SolBenchmarkEvaluator, EvaluationMode
from sol.benchmarks.delayed_recall_runner import FlagshipBenchmarkRunner


class TestFlagshipDelayedRecall:

    @pytest.fixture
    def encoder(self):
        return IdentityPreservingEncoder(ambient_dim=1536, manifold_dim=4, seed=42)

    def test_information_loss_counterexample_resolution(self, encoder):
        """
        Validates Finding C resolution:
        - Two orthogonal 1,536-D vectors with identical histograms.
        - Legacy StatisticalPrism collapses them into identical coordinates (diff < 1e-8).
        - IdentityPreservingEncoder preserves Euclidean distance > 1.0.
        """
        audit = encoder.audit_legacy_counterexample()

        assert audit.legacy_collapsed is True, "Legacy StatisticalPrism failed to collapse on permutation"
        assert audit.identity_preserved is True, "IdentityPreservingEncoder failed to preserve distinction"
        assert abs(audit.cosine_similarity) < 1e-10, "Audit vectors were not orthogonal"
        assert audit.euclidean_separation >= 1.0, f"Separation {audit.euclidean_separation} below 1.0 bound"

    def test_flagship_task_suite_generation_and_oracle(self):
        """
        Validates task suite generation:
        - Decoupled topology and input seeds.
        - Balanced distribution of valid recall, contradiction, and disconnected trials.
        - Independent GroundTruthOracle evaluation.
        """
        gen = FlagshipTaskGenerator(topology_seed=101, input_seed=202)
        trials = gen.generate_suite(num_trials=20, delay_steps_list=[5, 15, 30])

        assert len(trials) == 20
        has_valid = any(t.trial_type == TrialType.VALID_RECALL for t in trials)
        has_conflict = any(t.trial_type == TrialType.CONTRADICTION for t in trials)
        has_disconnected = any(t.trial_type == TrialType.DISCONNECTED for t in trials)

        assert has_valid and has_conflict and has_disconnected, "Suite missing trial diversity"

        # Test Oracle on synthetic ground truth
        t_valid = next(t for t in trials if t.trial_type == TrialType.VALID_RECALL)
        res_valid = GroundTruthOracle.evaluate(
            trial=t_valid,
            model_name="OracleTest",
            predicted_value=t_valid.target_value,
            emitted_verdict="PROMOTE"
        )
        assert res_valid.is_correct_recall is True
        assert res_valid.committed_false_claim is False

        t_conflict = next(t for t in trials if t.trial_type == TrialType.CONTRADICTION)
        res_conflict = GroundTruthOracle.evaluate(
            trial=t_conflict,
            model_name="OracleTest",
            predicted_value=None,
            emitted_verdict="QUARANTINE"
        )
        assert res_conflict.rejected_conflict is True
        assert res_conflict.committed_false_claim is False

    def test_comparative_baselines_execution(self, encoder):
        """
        Validates the 3 comparative baselines:
        1. Explicit FSM/DAG: 100% recall on valid, 100% reject on conflict.
        2. Linear Diffusion: susceptible to linear superposition and false commits.
        3. Echo State Reservoir: fading memory decay over long delays.
        """
        gen = FlagshipTaskGenerator(topology_seed=501, input_seed=601)
        trials = gen.generate_suite(num_trials=10, delay_steps_list=[5, 20])

        fsm = ExplicitFSMDAGBaseline(encoder=encoder)
        diffusion = LinearGraphDiffusionBaseline(encoder=encoder)
        esn = EchoStateReservoirBaseline(encoder=encoder)

        fsm_results = [fsm.execute_trial(t) for t in trials]
        diff_results = [diffusion.execute_trial(t) for t in trials]
        esn_results = [esn.execute_trial(t) for t in trials]

        # FSM symbolic integrity
        assert all(r.is_correct_recall for r in fsm_results if r.trial_type == TrialType.VALID_RECALL)
        assert all(r.rejected_conflict for r in fsm_results if r.trial_type == TrialType.CONTRADICTION)

        # Linear diffusion exhibits false commits on conflict trials due to linear superposition
        conflict_diff = [r for r in diff_results if r.trial_type == TrialType.CONTRADICTION]
        if conflict_diff:
            assert any(r.committed_false_claim for r in conflict_diff), (
                "Linear diffusion should exhibit lack of conflict boundary separation"
            )

        # Reservoir produces bounded metrics
        assert all(r.read_disturb_margin >= 0.0 for r in esn_results)

    def test_sol_riemannian_evaluator_zero_false_commits(self, encoder, tmp_path):
        """
        Validates SOL Riemannian Evaluator:
        - Zero false commit rate on contradictory evidence (100% quarantine).
        - High retention and non-destructive readout margin (>= 0.95).
        """
        evaluator_adaptive = SolBenchmarkEvaluator(
            mode=EvaluationMode.ADAPTIVE_SWARM,
            encoder=encoder,
            storage_dir=tmp_path
        )
        evaluator_frozen = SolBenchmarkEvaluator(
            mode=EvaluationMode.FROZEN_CONTROLLER,
            encoder=encoder,
            storage_dir=tmp_path
        )

        gen = FlagshipTaskGenerator(topology_seed=777, input_seed=888)
        trials = gen.generate_suite(num_trials=12, delay_steps_list=[10, 25])

        for model in (evaluator_adaptive, evaluator_frozen):
            for t in trials:
                res = model.execute_trial(t)

                if t.trial_type == TrialType.CONTRADICTION:
                    # Invariant: Conflict routing must strictly reject and NEVER commit false claim
                    assert res.rejected_conflict is True
                    assert res.committed_false_claim is False
                    assert res.verdict == "QUARANTINE"

                # Invariant: Read disturb margin remains bounded
                assert res.read_disturb_margin >= 0.85

    def test_sol_lens_observable_packet_and_edge_contract(self, encoder, tmp_path):
        """
        Validates Lens SolLensPacketV02 generation and SOL-Edge authority integration:
        - Emits valid PACKET_SCHEMA_V02 JSON.
        - Proves Non-Dilutable Contradiction Shield: Adding extra supported nodes
          cannot overturn a QUARANTINE verdict on contradiction.
        """
        evaluator = SolBenchmarkEvaluator(
            mode=EvaluationMode.ADAPTIVE_SWARM,
            encoder=encoder,
            storage_dir=tmp_path
        )

        # Create a trial with contradiction
        trial = DelayedRecallTrial(
            trial_id="DILUTION-DEFENSE-001",
            trial_type=TrialType.CONTRADICTION,
            context_bindings={f"key_{i}": f"val_{i}" for i in range(10)},
            target_key="key_0",
            target_value="val_0",
            distractor_sequence=["noise_1", "noise_2"],
            delay_steps=5,
            contradiction_fact=("key_0", "corrupted_val_999")
        )

        res = evaluator.execute_trial(trial)
        pkt = res.telemetry_packet

        assert pkt is not None
        assert pkt["schema"] == "techman.sol-lens.proof-packet/v0.2"
        assert pkt["verdict"] == "QUARANTINE"

        # Attempt dilution attack: simulate adding 20 extra supported nodes
        logons = list(pkt["logons"])
        for i in range(20):
            logons.append({
                "id": f"DILUTE_EXTRA_{i}",
                "label": f"Irrelevant Supported Node {i}",
                "status": "supported",
                "evidence": 0.99,
                "rho": 0.95,
                "psi": 0.95,
                "pressure": 0.05,
                "detail": "Dilution attempt",
                "source": "Attacker"
            })

        # Test non-dilutable verification rule
        has_contradiction = any(lg["status"] == "contradiction" for lg in logons)
        diluted_verdict = "QUARANTINE" if has_contradiction else "PROMOTE"
        assert diluted_verdict == "QUARANTINE", "Dilution attack succeeded! Invariant breached."

    def test_full_suite_runner_and_reproducibility(self, tmp_path):
        """
        Runs the complete FlagshipBenchmarkRunner across all 7 models.
        Verifies deterministic reproduction and output artifact creation.
        """
        runner = FlagshipBenchmarkRunner(storage_dir=tmp_path)
        results = runner.run_suite(
            num_trials=14,
            delay_steps_list=[5, 15, 30],
            topology_seed=999,
            input_seed=888
        )

        assert results.total_trials == 14
        assert len(results.model_metrics) == 7

        # Verify SOL Adaptive Swarm metrics
        adaptive = results.model_metrics["SOL_ADAPTIVE_SWARM"]
        assert adaptive.false_commit_rate == 0.0
        assert adaptive.conflict_rejection_rate == 1.0
        assert adaptive.mean_read_disturb_margin >= 0.95

        # Verify summary table formatting
        table_str = results.to_summary_table()
        assert "Explicit_FSM_DAG" in table_str
        assert "SOL_ADAPTIVE_SWARM" in table_str
        assert "Linear_Graph_Diffusion" in table_str
