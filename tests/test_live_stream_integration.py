"""
End-to-End Live Stream Integration Test
File: tests/test_live_stream_integration.py

Verifies the HTTP simulation server, /api/packet/live, /api/health, and 3D WebGL viewer endpoints.
"""

from http.server import HTTPServer
import json
from pathlib import Path
import subprocess
import threading
import time
import urllib.request
import pytest

from scripts.run_sol_live_stream import ManifoldSimulationServer, create_handler


@pytest.fixture(scope="module")
def live_server():
    """Spins up a local ManifoldSimulationServer on an ephemeral test port."""
    port = 8799
    sim = ManifoldSimulationServer(port=port)
    sim.start()
    httpd = HTTPServer(("127.0.0.1", port), create_handler(sim))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    # Allow simulation to step a few cycles
    time.sleep(0.3)

    yield f"http://127.0.0.1:{port}"

    httpd.shutdown()
    sim.stop()


def test_health_endpoint(live_server):
    req = urllib.request.Request(f"{live_server}/api/health")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "healthy"
        assert data["engine"] == "SOL-Kernel"


def test_live_packet_endpoint_and_schema(live_server):
    req = urllib.request.Request(f"{live_server}/api/packet/live")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"
        data = json.loads(resp.read().decode("utf-8"))

        assert data["schema"] == "techman.sol-lens.proof-packet/v0.2"
        assert "logons" in data
        assert len(data["logons"]) > 0
        assert "edges" in data
        assert "metrics" in data
        assert data["verdict"] in ["PROMOTE", "HOLD", "QUARANTINE"]

        # Verify 3D visual coordinates are attached for WebGL viewport
        for logon in data["logons"]:
            assert "coords" in logon
            assert len(logon["coords"]) == 3


def test_webgl_3d_viewer_html(live_server):
    req = urllib.request.Request(f"{live_server}/")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        assert "text/html" in resp.headers.get("Content-Type")
        html = resp.read().decode("utf-8")
        assert "three.min.js" in html
        assert "OrbitControls.js" in html
        assert "SOL ENGINE: 3D RIEMANNIAN MANIFOLD" in html


def test_packet_schema_normalization_in_sol_lens(live_server):
    """Validates that the live packet passes sol-lens TypeScript normalization."""
    req = urllib.request.Request(f"{live_server}/api/packet/live")
    with urllib.request.urlopen(req) as resp:
        packet_json = resp.read().decode("utf-8")

    node_script = f"""
    import('./lib/packet-schema.ts').then(({{ normalizePacket }}) => {{
        const raw = {packet_json};
        const result = normalizePacket(raw);
        if (!result.ok) {{
            console.error(JSON.stringify(result.errors));
            process.exit(1);
        }}
        console.log('OK: ' + result.packet.packet_id + ' verdict=' + result.packet.evaluation.verdict);
    }});
    """
    sol_lens_dir = Path(__file__).resolve().parents[1] / "sol-lens"
    res = subprocess.run(
        ["node", "--experimental-strip-types", "-e", node_script],
        cwd=sol_lens_dir,
        capture_output=True,
        text=True
    )
    assert res.returncode == 0, f"Node normalization failed: {res.stderr}"
    assert "OK:" in res.stdout


def test_logic_endpoint_xor_and_half_adder(live_server):
    """Validates the live /api/logic endpoint for continuous geometric logic gates."""
    # Test XOR(1, 1) -> 0 via destructive interference
    req_xor = urllib.request.Request(f"{live_server}/api/logic?gate=XOR&a=1.0&b=1.0")
    with urllib.request.urlopen(req_xor) as resp:
        assert resp.status == 200
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"
        data = json.loads(resp.read().decode("utf-8"))
        assert data["gate_type"] == "XOR"
        assert data["binary_outputs"]["Y"] == 0
        assert data["min_eigenvalue"] > 0.0
        assert "exciton_A" in data["trajectories"]

    # Test Half-Adder(1, 1) -> Sum=0, Carry=1
    req_ha = urllib.request.Request(f"{live_server}/api/logic?gate=HALF_ADDER&a=1.0&b=1.0")
    with urllib.request.urlopen(req_ha) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["gate_type"] == "HALF_ADDER"
        assert data["binary_outputs"]["Sum"] == 0
        assert data["binary_outputs"]["Carry"] == 1


def test_sol_studio_standalone_assets(live_server):
    """Verifies that the standalone sol-studio web app assets are served with proper content types."""
    # Check index.html
    req_index = urllib.request.Request(f"{live_server}/")
    with urllib.request.urlopen(req_index) as resp:
        assert resp.status == 200
        assert "text/html" in resp.headers.get("Content-Type")
        body = resp.read().decode("utf-8")
        assert "SOL Studio" in body
        assert "SOL ENGINE: 3D RIEMANNIAN MANIFOLD" in body

    # Check style.css
    req_css = urllib.request.Request(f"{live_server}/style.css")
    with urllib.request.urlopen(req_css) as resp:
        assert resp.status == 200
        assert "text/css" in resp.headers.get("Content-Type")
        css_body = resp.read().decode("utf-8")
        assert "--bg: #030712" in css_body

    # Check app.js
    req_js = urllib.request.Request(f"{live_server}/app.js")
    with urllib.request.urlopen(req_js) as resp:
        assert resp.status == 200
        assert "application/javascript" in resp.headers.get("Content-Type")
        js_body = resp.read().decode("utf-8")
        assert "Riemannian" in js_body


def test_interactive_node_and_swarm_endpoints(live_server):
    """Verifies POST endpoints for dynamic node stimulation, coordinate updates, and swarm dispatch."""
    # 1. Stimulate Node
    data_stim = json.dumps({"node_id": "N01", "energy": 3.0}).encode("utf-8")
    req_stim = urllib.request.Request(f"{live_server}/api/node/stimulate", data=data_stim, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req_stim) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        assert res["ok"] is True
        assert res["node_id"] == "N01"

    # 2. Move Node
    data_move = json.dumps({"node_id": "N02", "coords": [4.5, -2.1, 1.0]}).encode("utf-8")
    req_move = urllib.request.Request(f"{live_server}/api/node/move", data=data_move, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req_move) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        assert res["ok"] is True
        assert res["node_id"] == "N02"

    # 3. Dispatch Swarm (7 Giants MoA Ensemble)
    req_swarm = urllib.request.Request(f"{live_server}/api/swarm/dispatch", data=b"{}", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req_swarm) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        assert res["ok"] is True
        assert res["swarm_size"] in [7, 8]

    # 4. Check 7 Giants Telemetry Endpoint
    req_giants = urllib.request.Request(f"{live_server}/api/swarm/giants")
    with urllib.request.urlopen(req_giants) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "7 Giants" in data["swarm_type"]
        assert len(data["giants"]) == 7
        assert "G1_Statistician" in data["giants"]
        assert "G2_Optimizer" in data["giants"]


def test_logic_adder_endpoint(live_server):
    """Verifies that /api/logic/adder performs continuous multi-bit addition."""
    req = urllib.request.Request(f"{live_server}/api/logic/adder?a=5&b=3")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["a_int"] == 5
        assert data["b_int"] == 3
        assert data["total_int"] == 8
        assert data["verified"] is True
        assert data["min_eigenvalue"] > 0.0
        assert data["total_absorbed_energy"] > 0.0


def test_logic_alu_endpoint(live_server):
    """Verifies that /api/logic/alu performs continuous Riemannian ALU operations."""
    # 1. ADD
    req_add = urllib.request.Request(f"{live_server}/api/logic/alu?op=ADD&a=9&b=4")
    with urllib.request.urlopen(req_add) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["op"] == "ADD"
        assert data["result_int"] == 13
        assert data["verified"] is True
        assert data["min_eigenvalue"] > 0.0

    # 2. SUB
    req_sub = urllib.request.Request(f"{live_server}/api/logic/alu?op=SUB&a=12&b=5")
    with urllib.request.urlopen(req_sub) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["op"] == "SUB"
        assert data["result_int"] == 7
        assert data["verified"] is True

    # 3. XOR
    req_xor = urllib.request.Request(f"{live_server}/api/logic/alu?op=XOR&a=10&b=6")
    with urllib.request.urlopen(req_xor) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["op"] == "XOR"
        assert data["result_int"] == 12  # 10 ^ 6 = 12
        assert data["verified"] is True

    # 4. AND
    req_and = urllib.request.Request(f"{live_server}/api/logic/alu?op=AND&a=14&b=11")
    with urllib.request.urlopen(req_and) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["op"] == "AND"
        assert data["result_int"] == 10  # 14 & 11 = 10
        assert data["verified"] is True


def test_synthesis_specs_and_circuit_endpoints(live_server):
    """Verifies that /api/synthesis/specs and /api/synthesis/circuit serve Vector 8 synthesis."""
    # 1. Specs list
    req_specs = urllib.request.Request(f"{live_server}/api/synthesis/specs")
    with urllib.request.urlopen(req_specs) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "available_specs" in data
        assert "XOR" in data["available_specs"]
        assert "MAJORITY_3" in data["available_specs"]

    # 2. Circuit synthesis
    req_circ = urllib.request.Request(f"{live_server}/api/synthesis/circuit?spec=MAJORITY_3")
    with urllib.request.urlopen(req_circ) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["spec_name"] == "MAJORITY_3"
        assert data["verified"] is True
        assert data["accuracy"] == 1.0
        assert "mermaid_markdown" in data
        assert "expressions" in data
        assert data["causal_emergence"]["has_causal_emergence"] is True
        assert data["causal_emergence"]["delta_ei"] > 0.0


def test_metacognition_endpoints(live_server):
    """Verifies Vector 9 metacognitive orchestration endpoints: plans, execute, telemetry."""
    # 1. GET /api/metacognition/plans
    req_plans = urllib.request.Request(f"{live_server}/api/metacognition/plans")
    with urllib.request.urlopen(req_plans) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        assert "available_plans" in data
        assert "ripple_carry" in data["available_plans"]
        assert "hierarchical_arbiter" in data["available_plans"]
        assert "counterfactual_equality" in data["available_plans"]

    # 2. POST /api/metacognition/execute (Hierarchical Arbiter: Majority=1, Override=0)
    body = json.dumps({
        "plan": "hierarchical_arbiter",
        "inputs": {"V1": 1.0, "V2": 1.0, "V3": 0.0, "OVERRIDE": 0.0, "PRIORITY_VOTE": 0.0}
    }).encode("utf-8")
    req_exec = urllib.request.Request(
        f"{live_server}/api/metacognition/execute",
        data=body,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_exec) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        report = data["report"]
        assert report["success"] is True
        assert report["global_outputs"]["FINAL_DECISION"] == 1
        assert report["global_outputs"]["MAJORITY_RAW"] == 1
        assert report["mean_causal_delta_ei"] > 0.30

    # 3. GET /api/metacognition/telemetry
    req_telem = urllib.request.Request(f"{live_server}/api/metacognition/telemetry")
    with urllib.request.urlopen(req_telem) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        assert data["latest_report"] is not None
        assert data["latest_report"]["plan_id"] == "plan_hierarchical_arbiter"
        assert len(data["cached_circuits"]) > 0


def test_dialectics_endpoints(live_server):
    """Verifies Vector 10 dialectical discourse endpoints: arena, debate, ablation, theorems."""
    # 1. GET /api/dialectics/arena (initial status)
    req_arena = urllib.request.Request(f"{live_server}/api/dialectics/arena")
    with urllib.request.urlopen(req_arena) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        assert data["arena_status"] == "operational"

    # 2. POST /api/dialectics/debate (MAJORITY_3 debate session)
    body = json.dumps({
        "title": "MAJORITY_3",
        "prop_id": "prop_maj3_test",
        "claim": "Majority 3 preserves positive causal emergence under adversarial challenge",
        "is_deliberately_flawed": False,
        "rounds": 6
    }).encode("utf-8")
    req_debate = urllib.request.Request(
        f"{live_server}/api/dialectics/debate",
        data=body,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_debate) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        session = data["session"]
        assert session["session_id"].startswith("arena_prop_maj3_test_")
        assert session["proof_bundle"]["accuracy"] == 1.0
        assert session["theorem_report"]["verdict"] in ("SYNTHESIS_PROVED", "EMPIRICAL_COMPROMISE")
        assert session["final_consensus_order"] > 0.40

    # 3. POST /api/dialectics/ablation (standalone ablation of XOR)
    body_abl = json.dumps({"spec": "XOR"}).encode("utf-8")
    req_abl = urllib.request.Request(
        f"{live_server}/api/dialectics/ablation",
        data=body_abl,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_abl) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        abl = data["ablation"]
        assert abl["prop_id"] == "XOR"
        assert abl["minimal_kernel"]["kernel_accuracy"] == 1.0

    # 4. GET /api/dialectics/theorems
    req_theo = urllib.request.Request(f"{live_server}/api/dialectics/theorems")
    with urllib.request.urlopen(req_theo) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["latest_session"]["session_id"].startswith("arena_prop_maj3_test_")


def test_discovery_endpoints(live_server):
    """Verifies Vector 11 discovery endpoints: conjectures, prove, theorems, and markdown corpus."""
    # 1. GET /api/discovery/conjectures
    req_conjs = urllib.request.Request(f"{live_server}/api/discovery/conjectures")
    with urllib.request.urlopen(req_conjs) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        assert len(data["conjectures"]) >= 5

    # 2. POST /api/discovery/prove (De Morgan NAND Duality)
    body = json.dumps({
        "conjecture_id": "conj_demorgan_nand",
        "rounds": 6
    }).encode("utf-8")
    req_prove = urllib.request.Request(
        f"{live_server}/api/discovery/prove",
        data=body,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_prove) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        cert = data["certificate"]
        assert cert["verdict"] == "PROVED_THEOREM"
        assert cert["hegelian_consensus_order"] > 0.40
        assert cert["is_crystallized"] is True

    # 3. GET /api/discovery/theorems
    req_thms = urllib.request.Request(f"{live_server}/api/discovery/theorems")
    with urllib.request.urlopen(req_thms) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        assert data["theorems_count"] >= 1
        assert "mermaid_dag" in data
        assert "flowchart TD" in data["mermaid_dag"]

    # 4. GET /api/discovery/corpus/markdown
    req_md = urllib.request.Request(f"{live_server}/api/discovery/corpus/markdown")
    with urllib.request.urlopen(req_md) as resp:
        assert resp.status == 200
        md_content = resp.read().decode("utf-8")
        assert "# Formal Corpus of Proven Mathematical Theorems" in md_content
        assert "De Morgan" in md_content


def test_cohomology_endpoints(live_server):
    """Verifies Vector 12 Sheaf Cohomology REST endpoints."""
    # 1. GET /api/cohomology/topologies
    req_topos = urllib.request.Request(f"{live_server}/api/cohomology/topologies")
    with urllib.request.urlopen(req_topos) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        assert "7_GIANTS_MOA" in data["topologies"]
        assert "MOBIUS_CONTRADICTION" in data["topologies"]
        assert data["topologies"]["7_GIANTS_MOA"]["vertex_count"] == 7

    # 2. GET /api/cohomology/audit (Live 7 Giants state)
    req_audit = urllib.request.Request(f"{live_server}/api/cohomology/audit")
    with urllib.request.urlopen(req_audit) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        audit = data["audit"]
        assert audit["topology_name"] == "7_GIANTS_MOA"
        assert audit["vertex_count"] == 7
        assert audit["beta_0"] >= 1
        assert "semantic_consistency_score" in audit

    # 3. POST /api/cohomology/audit with auto_repair on Mobius contradiction
    body = json.dumps({
        "topology": "MOBIUS_CONTRADICTION",
        "states": {
            "NODE_A": [1.0, 1.0],
            "NODE_B": [1.0, 1.0],
            "NODE_C": [1.0, 1.0]
        },
        "auto_repair": True
    }).encode("utf-8")
    req_post_audit = urllib.request.Request(
        f"{live_server}/api/cohomology/audit",
        data=body,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_post_audit) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        audit = data["audit"]
        assert audit["topology_name"] == "MOBIUS_CONTRADICTION"
        assert audit["repair"] is not None
        assert audit["repair"]["energy_dissipated"] >= 0.0
        assert audit["semantic_consistency_score"] >= audit["repair"]["initial_consistency"]

    # 4. POST /api/cohomology/diffuse
    body_diff = json.dumps({
        "topology": "7_GIANTS_MOA",
        "steps": 25,
        "dt": 0.04,
        "rate": 1.2
    }).encode("utf-8")
    req_diff = urllib.request.Request(
        f"{live_server}/api/cohomology/diffuse",
        data=body_diff,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_diff) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        assert data["total_steps"] > 0
        assert data["energy_reduction_ratio"] > 0.0


def test_wgsl_acceleration_endpoints(live_server):
    """Verifies Vector 13 hardware acceleration REST endpoints."""
    # 1. GET /api/wgsl/status
    req_status = urllib.request.Request(f"{live_server}/api/wgsl/status")
    with urllib.request.urlopen(req_status) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        assert data["status"]["is_valid"] is True
        assert data["status"]["shader_name"] == "proof_engine.wgsl"

    # 2. GET /api/wgsl/benchmarks
    req_bench = urllib.request.Request(f"{live_server}/api/wgsl/benchmarks")
    with urllib.request.urlopen(req_bench) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        assert data["benchmarks"]["theorems_evaluated"] > 0
        assert data["benchmarks"]["mean_speedup"] >= 10.0

    # 3. POST /api/wgsl/prove
    body_prove = json.dumps({
        "conjecture_id": "conj_demorgan_nand",
        "metric_strain": 0.05
    }).encode("utf-8")
    req_prove = urllib.request.Request(
        f"{live_server}/api/wgsl/prove",
        data=body_prove,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_prove) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        rep = data["report"]
        assert rep["verdict"] == "PROVED_THEOREM"
        assert rep["counter_examples_found"] == 0

    # 4. POST /api/wgsl/diffuse
    body_diff = json.dumps({
        "topology": "7_GIANTS_MOA",
        "steps": 20,
        "dt": 0.05,
        "rate": 1.0
    }).encode("utf-8")
    req_diff = urllib.request.Request(
        f"{live_server}/api/wgsl/diffuse",
        data=body_diff,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_diff) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        diff = data["diffusion"]
        assert diff["steps"] == 20
        assert diff["energy_reduction_ratio"] > 0.0


def test_gauge_sheaf_live_endpoints(live_server):
    """Validates Vector 16 Non-Abelian Gauge Sheaf HTTP endpoints."""
    # 1. GET /api/gauge/status
    req_status = urllib.request.Request(f"{live_server}/api/gauge/status")
    with urllib.request.urlopen(req_status) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        assert len(data["vertices"]) >= 3
        assert len(data["edges"]) >= 3
        assert "yang_mills_action" in data
        assert "dirichlet_energy" in data

    # 2. POST /api/gauge/wilson_audit
    req_audit = urllib.request.Request(
        f"{live_server}/api/gauge/wilson_audit",
        data=b"{}",
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_audit) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        assert data["audit"]["is_gauge_consistent"] is True
        assert data["audit"]["total_loops_checked"] >= 2

    # 3. POST /api/gauge/relax
    body_relax = json.dumps({"steps": 15, "lr": 0.2}).encode("utf-8")
    req_relax = urllib.request.Request(
        f"{live_server}/api/gauge/relax",
        data=body_relax,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_relax) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        assert data["steps"] == 15
        assert data["final_energy"] <= data["initial_energy"]

    # 4. POST /api/gauge/compensate
    body_comp = json.dumps({
        "cycle_nodes": ["Anchor_Dock", "Anchor_Alpha", "Anchor_Beta", "Anchor_Dock"]
    }).encode("utf-8")
    req_comp = urllib.request.Request(
        f"{live_server}/api/gauge/compensate",
        data=body_comp,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_comp) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        assert data["compensation"]["is_drift_eliminated"] is True

    # 5. POST /api/gauge/transform
    req_trans = urllib.request.Request(
        f"{live_server}/api/gauge/transform",
        data=b"{}",
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_trans) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["ok"] is True
        assert data["gauge_invariance"]["is_strictly_gauge_invariant"] is True

    # 6. Verify live packet contains gauge_sheaf telemetry
    req_pkt = urllib.request.Request(f"{live_server}/api/packet/live")
    with urllib.request.urlopen(req_pkt) as resp:
        assert resp.status == 200
        pkt = json.loads(resp.read().decode("utf-8"))
        assert "gauge_sheaf" in pkt
        assert pkt["gauge_sheaf"]["total_anchors"] >= 3
        assert "yang_mills_action" in pkt["gauge_sheaf"]










