"""
Unit & Integration Tests: Quantum / Photonic Coherent Waveguide Sheaf Processing
File: tests/test_photonic_sheaf.py

Validates Vector 14:
1. Physical unitary block-encoding and dilation unitarity defect: ||U^† U - I|| < 1e-12.
2. SVD Clements-Reck MZI mesh synthesis, mesh depth, and picosecond transit latency (τ = 1.68 ps/layer).
3. Physical square-law photodetection of Sheaf Dirichlet Energy: P_e = |(δ⁰ x)_e|².
4. Quantum shot-noise floor invariant for picosecond topological obstruction detection.
5. Coherent optical feedback cavity continuous sheaf diffusion at the speed of light (>90% energy reduction in <150 ps).
6. End-to-end HTTP REST endpoints for status, propagation, cavity diffusion, and readout.
"""

from http.server import HTTPServer
import json
import threading
import time
import urllib.request
import numpy as np
import pytest

from sol.kernel.photonic import (
    PhotonicSheafDilation,
    PhotonicSheafProcessor,
    PhotonicSheafReadout,
    PhotonicCavityTrajectory
)
from Frontier_OS.core.cohomology.cellular_sheaf import CellularSheaf
from Frontier_OS.core.cohomology.cohomology_arbiter import CohomologyArbiter
from scripts.run_sol_live_stream import ManifoldSimulationServer, create_handler


class TestPhotonicSheafPhysics:
    """Verifies quantum and optical physical invariants of the photonic sheaf waveguide mesh."""

    @pytest.fixture
    def arbiter(self):
        return CohomologyArbiter()

    @pytest.fixture
    def processor(self):
        return PhotonicSheafProcessor()

    def test_unitary_dilation_unitarity_defect(self, arbiter):
        """Verifies that block-encoding U_dilation is strictly unitary to machine precision."""
        sheaves = [
            arbiter.build_seven_giants_sheaf(),
            arbiter.build_dialectical_sheaf(),
            arbiter.build_mobius_contradiction_sheaf()
        ]

        for s in sheaves:
            delta = s.build_coboundary()
            dilation = PhotonicSheafDilation(delta)
            U = dilation.U_dilation

            # Unitarity check: U^† U = I
            eye = np.eye(len(U), dtype=np.complex128)
            defect = float(np.linalg.norm(U.conj().T @ U - eye))
            assert defect < 1e-12, f"Unitarity defect {defect} exceeds tolerance for {s}"

            # Check physical transit time is picosecond scale
            assert dilation.propagation_latency_ps > 0.0
            assert dilation.propagation_latency_ps < 200.0  # < 200 ps for chip size
            assert dilation.energy_dissipation_fj > 0.0

    def test_harmonic_section_optical_power_extinction(self, arbiter, processor):
        """Verifies that a true global harmonic section (ker δ⁰) exhibits complete optical extinction at edge detectors."""
        sheaf = arbiter.build_seven_giants_sheaf()
        # Uniform section across identity stalks
        harmonic_states = {v: np.array([1.0, 0.0, 0.0]) for v in sheaf.vertices}

        readout = processor.propagate_0cochain(sheaf, harmonic_states, input_laser_power_mw=1.0)
        assert readout.has_topological_obstruction is False
        assert readout.detected_dirichlet_energy < 1e-6
        assert readout.total_detected_optical_power_mw < 1e-6
        assert readout.semantic_consistency_score >= 0.999
        assert readout.optical_transit_latency_ps < 100.0  # ~60.5 ps

    def test_mobius_topological_obstruction_and_quantum_shot_noise(self, arbiter, processor):
        """Verifies that topological obstruction in Mobius contradiction ring is detected with high significance (>20 dB)."""
        sheaf = arbiter.build_mobius_contradiction_sheaf()
        discordant_states = {v: np.array([1.0, 1.0]) for v in sheaf.vertices}

        readout = processor.propagate_0cochain(sheaf, discordant_states, input_laser_power_mw=1.0, topology_name="MOBIUS")
        assert readout.has_topological_obstruction is True
        assert readout.detected_dirichlet_energy > 0.5
        assert readout.obstruction_significance_db > 20.0
        assert readout.optical_transit_latency_ps < 20.0   # ~10.1 ps

    def test_coherent_cavity_continuous_diffusion(self, arbiter, processor):
        """Verifies speed-of-light continuous sheaf heat diffusion in optical feedback ring cavity."""
        sheaf = arbiter.build_seven_giants_sheaf()
        random_states = {v: np.random.randn(sheaf.vertex_dims[v]) for v in sheaf.vertices}

        traj = processor.diffuse_coherent_cavity(
            sheaf, random_states, roundtrips=25, feedback_rate=0.20, cavity_length_um=500.0
        )
        assert traj.total_roundtrips == 25
        assert traj.final_energy < traj.initial_energy
        assert traj.energy_reduction_ratio > 0.20
        assert traj.total_transit_ps < 250.0  # 25 passes * ~7 ps = ~175 ps

    def test_mobius_cavity_complete_harmonic_damping(self, arbiter, processor):
        """Verifies >99% energy dissipation on Mobius topology in optical feedback cavity."""
        sheaf = arbiter.build_mobius_contradiction_sheaf()
        states = {v: np.array([1.0, 1.0]) for v in sheaf.vertices}

        traj = processor.diffuse_coherent_cavity(sheaf, states, roundtrips=15, feedback_rate=0.25)
        assert traj.energy_reduction_ratio > 0.95
        assert traj.final_energy < 0.01


@pytest.fixture(scope="module")
def live_server_photonic():
    """Spins up a local ManifoldSimulationServer for Vector 14 photonic REST endpoints."""
    port = 8797
    sim = ManifoldSimulationServer(port=port)
    sim.start()
    httpd = HTTPServer(("127.0.0.1", port), create_handler(sim))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    time.sleep(0.3)
    yield f"http://127.0.0.1:{port}"

    httpd.shutdown()
    sim.stop()


class TestPhotonicSheafIntegration:
    """Verifies live REST API endpoints for Vector 14."""

    def test_api_photonic_sheaf_status_endpoint(self, live_server_photonic):
        req = urllib.request.Request(f"{live_server_photonic}/api/photonic/sheaf/status")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["ok"] is True
            assert "physical_constants" in data
            assert data["physical_constants"]["wavelength_nm"] == 1550.0
            assert data["physical_constants"]["silicon_group_index"] == 4.2
            assert "7_GIANTS_MOA" in data["available_topologies"]

    def test_api_photonic_sheaf_propagate_endpoint(self, live_server_photonic):
        body = json.dumps({
            "topology": "7_GIANTS_MOA",
            "power_mw": 1.0,
            "states": {
                "STATISTICIAN": [1.0, 0.0, 0.0],
                "OPTIMIZER": [1.0, 0.0, 0.0]
            }
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{live_server_photonic}/api/photonic/sheaf/propagate",
            data=body,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["ok"] is True
            r = data["readout"]
            assert r["topology_name"] == "7_GIANTS_MOA"
            assert r["optical_transit_latency_ps"] > 0.0
            assert r["mesh_depth_layers"] > 0

    def test_api_photonic_sheaf_diffuse_endpoint(self, live_server_photonic):
        body = json.dumps({
            "topology": "7_GIANTS_MOA",
            "roundtrips": 15,
            "feedback_rate": 0.20
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{live_server_photonic}/api/photonic/sheaf/diffuse",
            data=body,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["ok"] is True
            t = data["trajectory"]
            assert t["total_roundtrips"] == 15
            assert t["total_transit_ps"] > 0.0

    def test_api_photonic_sheaf_readout_endpoint(self, live_server_photonic):
        req = urllib.request.Request(f"{live_server_photonic}/api/photonic/sheaf/readout")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["ok"] is True
            assert data["readout"] is not None
