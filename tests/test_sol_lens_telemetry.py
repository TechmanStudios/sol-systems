"""
Integration Tests: sol-lens Telemetry Emitter & Schema Validation
File: tests/test_sol_lens_telemetry.py
"""

import json
from pathlib import Path
import subprocess
import numpy as np
import pytest

from sol.kernel.geometry.ricci import DiscreteRicciFlowEngine, ExcitonTrajectory
from sol.diagnostics.telemetry_emitter import (
    SolLensTelemetryEmitter,
    ManifoldNodeTelemetry,
    PACKET_SCHEMA_V02
)
from Frontier_OS.core import RiemannianGeodesicNavigator


class TestSolLensTelemetry:

    @pytest.fixture
    def manifold_nodes(self):
        """Generates a cluster of 12 Riemannian semantic nodes."""
        rng = np.random.RandomState(42)
        dim = 4
        engine = DiscreteRicciFlowEngine(dim=dim)
        nodes = []

        base_A = rng.randn(dim, dim)
        g_0 = base_A.T @ base_A + 2.0 * np.eye(dim)

        for i in range(12):
            node_id = f"L{i+1:02d}"
            label = f"Semantic Cluster {i+1}"
            coords = rng.randn(dim)

            # Local metric perturbation
            M = rng.randn(dim, dim) * 0.1
            g_i = g_0 + (M.T @ M)

            # Neighbor metrics for Ricci calculation
            nbrs = [g_0 + (rng.randn(dim, dim) * 0.05).T @ (rng.randn(dim, dim) * 0.05) for _ in range(4)]
            weights = np.ones(4) / 4.0

            # Exciton trajectory at node
            traj = [ExcitonTrajectory(
                agent_id=f"exciton_{i}",
                node_id=i,
                velocity=rng.randn(dim) * 0.5,
                dwell_time=0.1 + rng.rand() * 0.1,
                attention_weight=0.5 + rng.rand() * 0.5
            )]

            g_updated, ricci_scalar, T_ij = engine.step(g_i, traj, nbrs, weights)

            nodes.append(ManifoldNodeTelemetry(
                node_id=node_id,
                label=label,
                coords=coords,
                metric_tensor=g_updated,
                ricci_scalar=ricci_scalar,
                attention_heat=float(np.trace(T_ij) * 0.1),
                kinetic_energy=0.5 * float(np.sum(coords**2)),
                damping_gamma=0.2,
                is_divergent=False,
                is_active_exciton=(i % 3 == 0),
                group_id=f"G{(i // 4) + 1:02d}"
            ))

        return nodes

    def test_telemetry_packet_generation_and_schema_constraints(self, manifold_nodes, tmp_path):
        """
        Validates that generated packets comply with PACKET_SCHEMA_V02:
        - All required fields present
        - Bounded measures within [0, 1]
        - Edge references valid
        - Serializes to valid JSON under 5MB
        """
        emitter = SolLensTelemetryEmitter(packet_id_prefix="test-sol-manifold")

        # Create adjacency connections between consecutive nodes
        adj_edges = [
            (manifold_nodes[i].node_id, manifold_nodes[i+1].node_id, 0.8)
            for i in range(len(manifold_nodes) - 1)
        ]
        # Create geodesic flow line
        flow_edges = [
            ("L01", "L04", 0.95),
            ("L04", "L07", 0.90)
        ]

        packet = emitter.synthesize_packet(
            nodes=manifold_nodes,
            adjacency_edges=adj_edges,
            geodesic_flow_edges=flow_edges
        )

        # 1. Structural assertions
        assert packet["schema"] == PACKET_SCHEMA_V02
        assert packet["observable_trace_only"] is True
        assert len(packet["logons"]) == 12
        assert len(packet["edges"]) == len(adj_edges) + len(flow_edges)
        assert packet["verdict"] in ["PROMOTE", "HOLD", "QUARANTINE"]

        # 2. Measures range assertions
        logon_ids = set()
        for logon in packet["logons"]:
            logon_ids.add(logon["id"])
            assert 0.0 <= logon["evidence"] <= 1.0
            assert 0.0 <= logon["rho"] <= 1.0
            assert 0.0 <= logon["psi"] <= 1.0
            assert 0.0 <= logon["pressure"] <= 1.0
            assert logon["status"] in ["supported", "inferred", "contradiction"]
            assert len(logon["detail"]) > 0

        # 3. Edge integrity
        for edge in packet["edges"]:
            assert edge["from"] in logon_ids
            assert edge["to"] in logon_ids
            assert edge["kind"] in ["dependency", "evidence", "constraint", "flow", "feedback"]

        # 4. JSON serialization & size limit (< 5 MB)
        packet_path = tmp_path / "telemetry_packet.json"
        emitter.save_packet(packet, packet_path)
        file_bytes = packet_path.stat().st_size
        assert file_bytes < 5 * 1024 * 1024
        assert file_bytes > 0

    def test_sol_lens_typescript_validator_acceptance(self, manifold_nodes, tmp_path):
        """
        Cross-Language Verification:
        Feeds the generated JSON packet directly into sol-lens's TypeScript
        normalizePacket() validator using Node.js to prove 100% interoperability.
        """
        emitter = SolLensTelemetryEmitter(packet_id_prefix="ts-validation-manifold")
        adj_edges = [(manifold_nodes[i].node_id, manifold_nodes[i+1].node_id, 0.75) for i in range(len(manifold_nodes) - 1)]

        packet = emitter.synthesize_packet(nodes=manifold_nodes, adjacency_edges=adj_edges)
        packet_json_path = tmp_path / "packet_for_ts.json"
        emitter.save_packet(packet, packet_json_path)

        # Run Node.js with --experimental-strip-types to evaluate normalizePacket directly
        repo_root = Path(__file__).resolve().parents[1]
        schema_ts_uri = (repo_root / "sol-lens" / "lib" / "packet-schema.ts").as_uri()
        json_posix = packet_json_path.as_posix()

        js_eval_code = f"""
        import fs from 'node:fs';
        import {{ normalizePacket }} from '{schema_ts_uri}';

        const raw = JSON.parse(fs.readFileSync('{json_posix}', 'utf8'));
        const result = normalizePacket(raw);

        if (!result.ok) {{
            console.error('Validation errors:', result.errors.join('; '));
            process.exit(1);
        }} else {{
            console.log('VALIDATION_SUCCESS: Normalized packet id:', result.packet.packet_id);
            console.log('Evaluation verdict:', result.packet.evaluation.verdict);
            process.exit(0);
        }}
        """

        proc = subprocess.run(
            ["node", "--experimental-strip-types", "-e", js_eval_code],
            capture_output=True,
            text=True,
            cwd=str(repo_root)
        )

        print("\n[sol-lens Node Validator Output]:", proc.stdout)
        if proc.returncode != 0:
            print("[sol-lens Node Validator STDERR]:", proc.stderr)

        assert proc.returncode == 0, f"sol-lens normalizePacket rejected generated packet: {proc.stderr}"
        assert "VALIDATION_SUCCESS" in proc.stdout
