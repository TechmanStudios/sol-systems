"""
Unit & Integration Tests: Hardware-Accelerated WGSL Proof Engine & Micro-Architecture
File: tests/test_wgsl_proof_engine.py

Validates Vector 13:
1. WebGPU WGSL compute shader loading, workgroup bounds, struct alignments, and invariants.
2. Massively parallel state-space exhaustion proving sound mathematical conjectures.
3. Atomic counter-example discovery with exact witness bitmask for flawed conjectures.
4. GPU-accelerated Sheaf Laplacian continuous heat diffusion and Dirichlet energy dissipation.
5. Micro-architecture performance benchmark: speedup factor and high-throughput evaluation.
6. End-to-end HTTP REST endpoints for WGSL status, proving, diffusion, and benchmarking.
"""

from http.server import HTTPServer
import json
import threading
import time
import urllib.request
import numpy as np
import pytest

from sol.kernel.photonic.webgpu_compiler import WebGPUComputeCompiler
from Frontier_OS.core.hardware_accel import (
    WGSLProofEngine,
    HardwareProofReport,
    MicroArchBenchmarkReport,
    WGSLProofVerdict
)
from Frontier_OS.core.theorem_proving.conjecture_engine import (
    AutonomousConjectureEngine,
    MathematicalConjecture
)
from Frontier_OS.core.cohomology.cellular_sheaf import CellularSheaf
from scripts.run_sol_live_stream import ManifoldSimulationServer, create_handler


class TestWGSLProofEngineCore:
    """Tests the standalone WGSL proof acceleration engine and compute shader invariants."""

    @pytest.fixture
    def engine(self):
        return WGSLProofEngine()

    def test_shader_compilation_and_validation(self, engine):
        """Verifies proof_engine.wgsl against WebGPU limits and SOL invariants."""
        status = engine.get_shader_status()
        assert status["is_valid"] is True
        assert status["shader_name"] == "proof_engine.wgsl"
        assert status["workgroup_size"] == (64, 1, 1)
        assert status["bindings_count"] == 6
        assert status["has_positive_definite_retraction"] is True
        assert status["has_symplectic_integration"] is True
        assert status["has_carnot_atomic_dissipation"] is True
        assert "ProofParameters" in status["uniform_structs"]
        assert "proof_result" in status["storage_buffers"]

    def test_sound_conjectures_proving_wgsl(self, engine):
        """Verifies that sound conjectures are proved with 100% soundness and high Hegelian consensus."""
        c_eng = AutonomousConjectureEngine()
        catalog = {c.conjecture_id: c for c in c_eng.generate_conjecture_catalog()}

        sound_ids = [
            "conj_demorgan_nand",
            "conj_majority_self_duality",
            "conj_xor_associativity",
            "conj_adder_carry_majority"
        ]

        for cid in sound_ids:
            conj = catalog[cid]
            rep = engine.prove_conjecture_wgsl(conj, metric_strain_eps=0.05)
            assert rep.verdict == WGSLProofVerdict.PROVED_THEOREM
            assert rep.counter_examples_found == 0
            assert rep.states_verified == rep.total_states
            assert rep.witness_input_state is None
            assert rep.hegelian_consensus >= 0.70
            assert rep.is_crystallized is True
            assert rep.gpu_dispatch_time_us > 0.0

    def test_flawed_conjectures_refutation_with_witness_wgsl(self, engine):
        """Verifies that flawed conjectures are refuted with atomic counter-example witnesses."""
        c_eng = AutonomousConjectureEngine()
        catalog = {c.conjecture_id: c for c in c_eng.generate_conjecture_catalog()}

        flawed_ids = [
            "conj_flawed_xor_linear",
            "conj_flawed_even_majority"
        ]

        for cid in flawed_ids:
            conj = catalog[cid]
            rep = engine.prove_conjecture_wgsl(conj, metric_strain_eps=0.05)
            assert rep.verdict == WGSLProofVerdict.DISPROVED_COUNTEREXAMPLE
            assert rep.counter_examples_found > 0
            assert rep.witness_input_state is not None
            assert rep.witness_bits is not None
            assert "A" in rep.witness_bits
            assert rep.hegelian_consensus < 0.50
            assert rep.is_crystallized is False

    def test_gpu_sheaf_heat_diffusion(self, engine):
        """Verifies parallel Sheaf Laplacian heat diffusion and Dirichlet energy dissipation."""
        sheaf = CellularSheaf()
        sheaf.add_vertex("V1", dim=2)
        sheaf.add_vertex("V2", dim=2)
        sheaf.add_edge("e12", "V1", "V2", dim_edge=2)

        states = {
            "V1": np.array([2.0, -1.0]),
            "V2": np.array([-1.0, 2.0])
        }

        diff_res = engine.diffuse_sheaf_heat_wgsl(sheaf, states, steps=25, dt=0.05, rate=1.0)
        assert diff_res["steps"] == 25
        assert diff_res["stalk_dimension"] == 4
        assert diff_res["final_energy"] < diff_res["initial_energy"]
        assert diff_res["energy_reduction_ratio"] > 0.50
        assert diff_res["carnot_dissipated_energy"] > 0.0
        assert diff_res["gpu_diffusion_time_us"] > 0.0
        assert "V1" in diff_res["final_states"]
        assert "V2" in diff_res["final_states"]

    def test_microarchitecture_speedup_benchmark(self, engine):
        """Verifies high-throughput execution and positive speedup ratio over CPU baseline."""
        c_eng = AutonomousConjectureEngine()
        catalog = list(c_eng.generate_conjecture_catalog()[:3])

        bench = engine.run_microarchitecture_benchmark(conjectures=catalog, runs_per_conjecture=3)
        assert bench.theorems_evaluated == 9
        assert bench.total_gpu_time_us > 0.0
        assert bench.total_cpu_time_ms > 0.0
        assert bench.mean_speedup >= 10.0
        assert bench.gpu_throughput_theorems_per_sec > 1000.0


@pytest.fixture(scope="module")
def live_server_wgsl():
    """Spins up a local ManifoldSimulationServer for live Vector 13 endpoint tests."""
    port = 8798
    sim = ManifoldSimulationServer(port=port)
    sim.start()
    httpd = HTTPServer(("127.0.0.1", port), create_handler(sim))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    time.sleep(0.3)
    yield f"http://127.0.0.1:{port}"

    httpd.shutdown()
    sim.stop()


class TestWGSLProofEngineIntegration:
    """Verifies live REST API endpoints for Vector 13."""

    def test_api_wgsl_status_endpoint(self, live_server_wgsl):
        req = urllib.request.Request(f"{live_server_wgsl}/api/wgsl/status")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["ok"] is True
            assert data["status"]["is_valid"] is True
            assert data["status"]["shader_name"] == "proof_engine.wgsl"

    def test_api_wgsl_benchmarks_endpoint(self, live_server_wgsl):
        req = urllib.request.Request(f"{live_server_wgsl}/api/wgsl/benchmarks")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["ok"] is True
            bench = data["benchmarks"]
            assert bench["theorems_evaluated"] > 0
            assert bench["mean_speedup"] >= 10.0
            assert bench["gpu_throughput_theorems_per_sec"] > 0.0

    def test_api_wgsl_prove_sound_endpoint(self, live_server_wgsl):
        body = json.dumps({
            "conjecture_id": "conj_demorgan_nand",
            "metric_strain": 0.05
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{live_server_wgsl}/api/wgsl/prove",
            data=body,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["ok"] is True
            rep = data["report"]
            assert rep["conjecture_id"] == "conj_demorgan_nand"
            assert rep["verdict"] == "PROVED_THEOREM"
            assert rep["counter_examples_found"] == 0
            assert rep["hegelian_consensus"] >= 0.70

    def test_api_wgsl_prove_flawed_endpoint(self, live_server_wgsl):
        body = json.dumps({
            "conjecture_id": "conj_flawed_xor_linear",
            "metric_strain": 0.05
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{live_server_wgsl}/api/wgsl/prove",
            data=body,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["ok"] is True
            rep = data["report"]
            assert rep["conjecture_id"] == "conj_flawed_xor_linear"
            assert rep["verdict"] == "DISPROVED_COUNTEREXAMPLE"
            assert rep["counter_examples_found"] > 0
            assert rep["witness_input_state"] is not None

    def test_api_wgsl_diffuse_endpoint(self, live_server_wgsl):
        body = json.dumps({
            "topology": "7_GIANTS_MOA",
            "steps": 20,
            "dt": 0.05,
            "rate": 1.0
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{live_server_wgsl}/api/wgsl/diffuse",
            data=body,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["ok"] is True
            diff = data["diffusion"]
            assert diff["steps"] == 20
            assert diff["energy_reduction_ratio"] > 0.0
            assert diff["gpu_diffusion_time_us"] > 0.0
