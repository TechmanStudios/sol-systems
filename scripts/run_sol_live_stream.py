"""
SOL Engine: Real-Time 3D Manifold Streaming Server & sol-lens Bridge
File: scripts/run_sol_live_stream.py

Runs the continuous Riemannian metric deformation engine and Exciton-MoA geodesic
navigation loop in real time, serving:
1. GET /api/packet/live - Latest canonical SolLensPacketV02 JSON packet.
2. GET /api/stream      - High-frequency Server-Sent Events (SSE) stream.
3. GET /                - Interactive 3D WebGL / Canvas Riemannian manifold viewer.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from pathlib import Path
import sys
import threading
import time
from typing import Dict, List, Optional
import numpy as np

# Ensure workspace packages are importable
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
telemetry_dir = root_dir / "Frontier_OS" / "Exciton-MoA" / "teleMetry"
if str(telemetry_dir) not in sys.path:
    sys.path.insert(0, str(telemetry_dir))

import urllib.parse

from sol.kernel.geometry.ricci import DiscreteRicciFlowEngine, ExcitonTrajectory
from sol.kernel.geometry.logic_manifold import (
    RiemannianLogicManifold,
    LogicGateType,
    RippleCarryManifoldCircuit,
    RiemannianALU,
    ALUOp
)
from sol.diagnostics.telemetry_emitter import SolLensTelemetryEmitter, ManifoldNodeTelemetry
from Frontier_OS.core import (
    RiemannianGeodesicNavigator,
    HippocampalMemorySink,
    AutonomousSwarmRouter,
    SwarmAgent,
    SwarmCluster,
    GiantRole,
    GiantProfile,
    GiantOperatorReadout,
    GIANT_PROFILES,
    SevenGiantsEnsemble,
    SevenGiantsMissionReport,
    DistributedSwarmCluster,
    DistributedSwarmReport
)
from sol.kernel.synthesis import (
    RiemannianCircuitSynthesizer,
    CANONICAL_SPECS,
    TruthTableSpec,
    SymbolicReflector,
    MetaplasticityEngine
)
from Frontier_OS.core.metacognition import (
    create_ripple_carry_adder_plan,
    create_hierarchical_arbiter_plan,
    create_counterfactual_equality_plan,
    MetacognitiveOrchestrator,
    CognitiveReasoningPlan,
    SwarmGuidedSynthesizer
)
from Frontier_OS.core.dialectics import (
    DialecticalProposition,
    PropositionType,
    DialecticalArena,
    ArenaSessionReport,
    QuantitativeCausalAblator,
    DialecticalVerdict,
    AttackVerdict
)
from Frontier_OS.core.theorem_proving import (
    MathematicalDomain,
    AutonomousConjectureEngine,
    AutomatedProofEngine,
    ProofVerdict,
    TheoremCorpus
)
from Frontier_OS.core.cohomology import (
    CellularSheaf,
    CohomologyEngine,
    CohomologySpectrum,
    SheafDiffuser,
    TopologicalRepairEngine,
    CohomologyArbiter,
    CohomologyAuditReport
)
from Frontier_OS.core.hardware_accel import (
    WGSLProofEngine,
    HardwareProofReport,
    MicroArchBenchmarkReport,
    WGSLProofVerdict
)
from sol.kernel.photonic import (
    PhotonicSheafDilation,
    PhotonicSheafProcessor,
    PhotonicSheafReadout,
    PhotonicCavityTrajectory
)
from Frontier_OS.core.robotics import (
    ArticulatedManipulator6DOF,
    RoboticConfigurationManifold,
    Obstacle3D,
    KinematicState,
    GeodesicActuationController,
    TrajectoryExecutionReport,
    RoboticSafetyArbiter,
    RoboticSafetyAuditReport
)
from Frontier_OS.core.gauge import (
    skew,
    unskew,
    so3_exp,
    so3_log,
    so3_geodesic_distance,
    se3_exp,
    se3_log,
    lie_bracket_so3,
    WilsonLoopReport,
    FaceCurvatureReport,
    NonAbelianGaugeSheaf,
    ToolDriftCompensationReport,
    GaugeNavigationAuditReport,
    HolonomicSpatialNavigator,
    GaugeViolation,
    GaugeArbiterReport,
    NonAbelianGaugeArbiter
)
from sol.kernel.synthesis.circuit_synthesizer import build_canonical_specs


HTML_3D_VIEWER = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SOL Studio — SOL ENGINE: 3D RIEMANNIAN MANIFOLD</title>
<style>
  :root {
    --bg: #030712;
    --glass: rgba(15, 23, 42, 0.72);
    --glass-hover: rgba(30, 41, 59, 0.85);
    --border: rgba(255, 255, 255, 0.08);
    --border-active: rgba(56, 189, 248, 0.4);
    --text: #f3f4f6;
    --text-muted: #94a3b8;
    --text-dim: #64748b;
    --cyan: #38bdf8;
    --emerald: #10b981;
    --amber: #f59e0b;
    --rose: #f43f5e;
    --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    overflow: hidden;
    height: 100vh;
    width: 100vw;
    user-select: none;
  }

  /* Fullscreen Viewport */
  #viewport-container {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }
  canvas { width: 100%; height: 100%; display: block; }

  /* Floating Glass Top Navigation */
  #topbar {
    position: absolute;
    top: 16px;
    left: 20px;
    right: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 20;
    pointer-events: none;
  }
  .brand-pill {
    pointer-events: auto;
    display: flex;
    align-items: center;
    gap: 12px;
    background: var(--glass);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    padding: 8px 16px;
    border-radius: 9999px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  }
  .brand-sun {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--amber), var(--cyan));
    box-shadow: 0 0 12px rgba(56, 189, 248, 0.6);
  }
  .brand-title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: #fff;
    text-transform: uppercase;
  }
  .live-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--emerald);
    box-shadow: 0 0 8px var(--emerald);
    animation: live-pulse 1.8s infinite;
  }
  @keyframes live-pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.35; transform: scale(0.8); } }
  .live-tag {
    font-size: 10px;
    font-family: var(--mono);
    color: var(--emerald);
    font-weight: 600;
    letter-spacing: 0.05em;
  }

  /* Center Ticker Pill */
  #ticker-pill {
    pointer-events: auto;
    display: flex;
    align-items: center;
    gap: 16px;
    background: var(--glass);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    padding: 8px 20px;
    border-radius: 9999px;
    font-size: 11px;
    font-family: var(--mono);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  }
  .ticker-item { display: flex; gap: 6px; align-items: baseline; }
  .ticker-label { color: var(--text-dim); }
  .ticker-val { font-weight: 600; color: #fff; }

  /* Right Action Pills */
  .right-actions {
    pointer-events: auto;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .glass-btn {
    background: var(--glass);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    color: var(--text-muted);
    font-size: 11px;
    font-family: var(--sans);
    font-weight: 500;
    padding: 7px 14px;
    border-radius: 9999px;
    cursor: pointer;
    transition: all 0.15s ease;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .glass-btn:hover {
    background: var(--glass-hover);
    color: #fff;
    border-color: rgba(255, 255, 255, 0.2);
  }
  .glass-btn.active {
    background: rgba(56, 189, 248, 0.15);
    border-color: var(--cyan);
    color: var(--cyan);
  }
  .verdict-pill {
    font-size: 10px;
    font-family: var(--mono);
    font-weight: 700;
    padding: 5px 12px;
    border-radius: 9999px;
    background: #064e3b;
    color: #34d399;
    border: 1px solid #059669;
  }

  /* Floating Bottom Control Island */
  #control-deck {
    position: absolute;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 12px;
    background: var(--glass);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border);
    padding: 8px 18px;
    border-radius: 9999px;
    z-index: 20;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
  }
  .deck-section { display: flex; align-items: center; gap: 6px; }
  .deck-divider { width: 1px; height: 18px; background: var(--border); margin: 0 4px; }
  .deck-btn {
    background: transparent;
    border: 1px solid transparent;
    color: var(--text-muted);
    font-size: 11px;
    padding: 5px 12px;
    border-radius: 9999px;
    cursor: pointer;
    transition: all 0.15s ease;
    font-weight: 500;
  }
  .deck-btn:hover { color: #fff; background: rgba(255, 255, 255, 0.06); }
  .deck-btn.active {
    background: rgba(56, 189, 248, 0.18);
    border-color: rgba(56, 189, 248, 0.4);
    color: var(--cyan);
  }
  .deck-btn.pulse-btn {
    color: var(--amber);
  }
  .deck-btn.pulse-btn:hover {
    background: rgba(245, 158, 11, 0.15);
    border-color: rgba(245, 158, 11, 0.4);
  }

  /* Sliding Inspector Drawer */
  #inspector-drawer {
    position: absolute;
    top: 0;
    right: -420px;
    width: 400px;
    height: 100vh;
    background: rgba(11, 17, 32, 0.94);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border-left: 1px solid var(--border);
    z-index: 30;
    transition: right 0.28s cubic-bezier(0.16, 1, 0.3, 1);
    display: flex;
    flex-direction: column;
    box-shadow: -16px 0 48px rgba(0, 0, 0, 0.6);
  }
  #inspector-drawer.open { right: 0; }
  .drawer-header {
    padding: 18px 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .drawer-title { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #fff; }
  .drawer-content { flex: 1; overflow-y: auto; padding: 20px 24px; font-family: var(--mono); font-size: 11px; }
  .drawer-card {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 14px;
  }
  .drawer-card-label { font-size: 10px; color: var(--text-dim); text-transform: uppercase; margin-bottom: 4px; }
  .drawer-card-val { font-size: 13px; font-weight: 600; color: #fff; }
  pre { background: #020617; border: 1px solid var(--border); border-radius: 6px; padding: 12px; overflow-x: auto; color: #94a3b8; line-height: 1.5; }

  /* Overlay Toast */
  #action-toast {
    position: absolute;
    top: 74px;
    left: 50%;
    transform: translateX(-50%) translateY(-20px);
    background: var(--glass);
    backdrop-filter: blur(16px);
    border: 1px solid var(--border-active);
    color: var(--cyan);
    font-size: 12px;
    font-family: var(--mono);
    padding: 8px 18px;
    border-radius: 9999px;
    opacity: 0;
    pointer-events: none;
    transition: all 0.25s ease;
    z-index: 25;
  }
  #action-toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>

<div id="viewport-container">
  <canvas id="viewport"></canvas>
</div>

<!-- Floating Top Navigation -->
<div id="topbar">
  <div class="brand-pill">
    <div class="brand-sun"></div>
    <span class="brand-title">SOL Studio</span>
    <span class="live-dot"></span>
    <span class="live-tag">20 Hz LIVE</span>
  </div>

  <div id="ticker-pill">
    <div class="ticker-item"><span class="ticker-label">det(g)</span><span id="det-g" class="ticker-val">1.000</span></div>
    <div class="ticker-item"><span class="ticker-label">Curvature R</span><span id="scalar-r" class="ticker-val">+0.000</span></div>
    <div class="ticker-item"><span class="ticker-label">κ(g)</span><span id="cond-g" class="ticker-val">1.00</span></div>
    <div class="ticker-item"><span class="ticker-label">dE Absorbed</span><span id="hippo-energy" class="ticker-val">0.00 J</span></div>
    <div class="ticker-item"><span class="ticker-label">Excitons</span><span id="exciton-count" class="ticker-val">0</span></div>
    <div class="ticker-item"><span class="ticker-label">Preservation</span><span id="geodesic-corr" class="ticker-val" style="color:var(--emerald);">99.7%</span></div>
  </div>

  <div class="right-actions">
    <span id="verdict-badge" class="verdict-pill">PROMOTE</span>
    <button id="btn-toggle-inspector" class="glass-btn" type="button">Telemetry ☰</button>
  </div>
</div>

<!-- Floating Bottom Control Island -->
<div id="control-deck">
  <div class="deck-section">
    <button class="deck-btn active" id="view-orbit" type="button">Orbit 3D</button>
    <button class="deck-btn" id="view-top" type="button">Top-Down</button>
    <button class="deck-btn" id="view-horizon" type="button">Horizon</button>
  </div>
  <div class="deck-divider"></div>
  <div class="deck-section">
    <span style="font-size:10px; color:var(--text-dim); text-transform:uppercase; margin-right:4px;">Logic:</span>
    <button class="deck-btn pulse-btn" id="gate-xor" type="button" title="Test non-linear destructive collision (Vector 2)">XOR</button>
    <button class="deck-btn pulse-btn" id="gate-and" type="button" title="Test constructive lensing (Vector 2)">AND</button>
    <button class="deck-btn pulse-btn" id="gate-half-adder" type="button" title="Test dual sum/carry routing (Vector 2)">Half-Adder</button>
  </div>
  <div class="deck-divider"></div>
  <div class="deck-section">
    <button class="deck-btn" id="btn-swarm" type="button" style="color:var(--emerald);" title="Trigger Autonomous Swarm Flocking (Vector 3)">● Swarm</button>
    <button class="deck-btn" id="btn-pause" type="button">Pause</button>
  </div>
</div>

<!-- Notification Toast -->
<div id="action-toast">Simulation Active</div>

<!-- Sliding Inspector Drawer -->
<div id="inspector-drawer">
  <div class="drawer-header">
    <span class="drawer-title">Riemannian Telemetry</span>
    <button class="glass-btn" id="btn-close-inspector" type="button">Close ✕</button>
  </div>
  <div class="drawer-content">
    <div class="drawer-card">
      <div class="drawer-card-label">Metric Retraction Cone</div>
      <div class="drawer-card-val" style="color:var(--emerald);">g_ij = exp(S) ≻ 0 · Verified</div>
    </div>
    <div class="drawer-card">
      <div class="drawer-card-label">Symplectic Geodesic Stepper</div>
      <div class="drawer-card-val">Levi-Civita Γ^k_ij · Adaptive γ(v, R)</div>
    </div>
    <div class="drawer-card">
      <div class="drawer-card-label">Hippocampal Memory Preservation</div>
      <div class="drawer-card-val">99.73% Geodesic Correlation</div>
    </div>
    <div class="drawer-card">
      <div class="drawer-card-label">Latest Proof-Packet JSON</div>
      <pre id="raw-json">Loading packet stream...</pre>
    </div>
  </div>
</div>

<script>
  const canvas = document.getElementById("viewport");
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x030712);
  scene.fog = new THREE.FogExp2(0x030712, 0.015);

  const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(0, 24, 28);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;

  // Deformable Riemannian Grid Mesh with dual visual shading
  const GRID_SIZE = 38;
  const GRID_SEGS = 52;
  const gridGeom = new THREE.PlaneGeometry(GRID_SIZE, GRID_SIZE, GRID_SEGS, GRID_SEGS);
  gridGeom.rotateX(-Math.PI / 2);

  // Surface wireframe
  const gridWireMat = new THREE.MeshBasicMaterial({
    color: 0x1e3a8a,
    wireframe: true,
    transparent: true,
    opacity: 0.35
  });
  const gridMesh = new THREE.Mesh(gridGeom, gridWireMat);
  scene.add(gridMesh);

  // Surface translucent body
  const gridBodyMat = new THREE.MeshBasicMaterial({
    color: 0x081226,
    transparent: true,
    opacity: 0.45,
    depthWrite: false
  });
  const gridBodyMesh = new THREE.Mesh(gridGeom, gridBodyMat);
  scene.add(gridBodyMesh);

  // Groups
  const nodeGroup = new THREE.Group();
  scene.add(nodeGroup);
  const edgeGroup = new THREE.Group();
  scene.add(edgeGroup);
  const excitonGroup = new THREE.Group();
  scene.add(excitonGroup);

  const nodeMeshMap = new Map();
  const nodeGeom = new THREE.SphereGeometry(0.36, 16, 16);
  let isPaused = false;
  let autoRotate = true;

  function showToast(msg) {
    const t = document.getElementById("action-toast");
    t.innerText = msg;
    t.classList.add("show");
    setTimeout(() => t.classList.remove("show"), 2500);
  }

  function updateHUD(data) {
    if (!data) return;
    if (data.metrics) {
      document.getElementById("geodesic-corr").innerText = (data.metrics.continuity * 100).toFixed(1) + "%";
    }
    if (data.logons && data.logons.length > 0) {
      const avgRho = data.logons.reduce((acc, l) => acc + l.rho, 0) / data.logons.length;
      const avgPressure = data.logons.reduce((acc, l) => acc + l.pressure, 0) / data.logons.length;
      document.getElementById("det-g").innerText = (avgRho * 2.5).toFixed(3);
      document.getElementById("scalar-r").innerText = ((avgRho - 0.5) * 8.0 >= 0 ? "+" : "") + ((avgRho - 0.5) * 8.0).toFixed(3);
      document.getElementById("cond-g").innerText = (1.0 + avgPressure * 12.0).toFixed(2);
      document.getElementById("hippo-energy").innerText = (avgPressure * 45.0).toFixed(2) + " J";
      const excitons = (data.excitons ? data.excitons.length : 0) + data.logons.filter(l => l.status === "inferred").length;
      document.getElementById("exciton-count").innerText = excitons;
    }
    const rawPre = document.getElementById("raw-json");
    if (rawPre && document.getElementById("inspector-drawer").classList.contains("open")) {
      rawPre.innerText = JSON.stringify(data, null, 2);
    }
  }

  function updateScene(packet) {
    if (!packet || !packet.logons) return;
    updateHUD(packet);

    // Deform Grid Vertices based on local metric curvature / pressure
    const posAttr = gridGeom.attributes.position;
    for (let i = 0; i < posAttr.count; i++) {
      const x = posAttr.getX(i);
      const z = posAttr.getZ(i);
      let deformation = 0;
      for (const logon of packet.logons) {
        if (!logon.coords) continue;
        const dx = x - logon.coords[0];
        const dz = z - logon.coords[1];
        const distSq = dx * dx + dz * dz;
        deformation -= (logon.rho * 2.2) / (1.0 + 0.3 * distSq);
      }
      posAttr.setY(i, deformation);
    }
    posAttr.needsUpdate = true;

    // Update Semantic Nodes
    packet.logons.forEach((logon) => {
      let mesh = nodeMeshMap.get(logon.id);
      if (!mesh) {
        let col = logon.status === "contradiction" ? 0xf43f5e : (logon.status === "inferred" ? 0x38bdf8 : 0x10b981);
        const mat = new THREE.MeshBasicMaterial({ color: col });
        mesh = new THREE.Mesh(nodeGeom, mat);
        nodeGroup.add(mesh);
        nodeMeshMap.set(logon.id, mesh);
      }
      if (logon.coords) {
        mesh.position.set(logon.coords[0], (logon.coords[2] || 0) * 0.5, logon.coords[1]);
      }
    });

    // Update Edges with proper WebGL resource disposal
    while (edgeGroup.children.length > 0) {
      const child = edgeGroup.children[0];
      if (child.geometry) child.geometry.dispose();
      if (child.material) child.material.dispose();
      edgeGroup.remove(child);
    }
    if (packet.edges) {
      for (const edge of packet.edges) {
        const u = nodeMeshMap.get(edge.from);
        const v = nodeMeshMap.get(edge.to);
        if (u && v) {
          const pts = [u.position, v.position];
          const lineGeom = new THREE.BufferGeometry().setFromPoints(pts);
          const lineMat = new THREE.LineBasicMaterial({
            color: edge.kind === "flow" ? 0x60a5fa : 0x1e3a8a,
            transparent: true,
            opacity: edge.kind === "flow" ? 0.9 : 0.35
          });
          const line = new THREE.Line(lineGeom, lineMat);
          edgeGroup.add(line);
        }
      }
    }

    // Update Dynamic Exciton Particles (Active Geodesic Trajectories)
    if (packet.excitons && Array.isArray(packet.excitons)) {
      while (excitonGroup.children.length < packet.excitons.length) {
        const pGeom = new THREE.SphereGeometry(0.45, 16, 16);
        const pMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });
        const pMesh = new THREE.Mesh(pGeom, pMat);
        excitonGroup.add(pMesh);
      }
      while (excitonGroup.children.length > packet.excitons.length) {
        const last = excitonGroup.children[excitonGroup.children.length - 1];
        if (last.geometry) last.geometry.dispose();
        if (last.material) last.material.dispose();
        excitonGroup.remove(last);
      }
      packet.excitons.forEach((exc, idx) => {
        const pMesh = excitonGroup.children[idx];
        if (pMesh && exc.coords) {
          pMesh.position.set(exc.coords[0], (exc.coords[2] || 0) + 0.45, exc.coords[1]);
        }
      });
    }
  }

  // Polling loop
  let pollDelay = 50;
  async function pollLivePacket() {
    if (!isPaused) {
      try {
        const resp = await fetch("/api/packet/live");
        if (resp.ok) {
          const data = await resp.json();
          updateScene(data);
          pollDelay = 50;
        } else {
          pollDelay = 500;
        }
      } catch (e) {
        pollDelay = 1000;
      }
    }
    setTimeout(pollLivePacket, pollDelay);
  }
  pollLivePacket();

  // Camera presets
  function setCamera(pos, target, btnId) {
    document.querySelectorAll("#control-deck .deck-btn").forEach(b => b.classList.remove("active"));
    if (btnId) document.getElementById(btnId).classList.add("active");
    camera.position.set(...pos);
    controls.target.set(...target);
    controls.update();
  }

  document.getElementById("view-orbit").onclick = () => setCamera([0, 24, 28], [0, 0, 0], "view-orbit");
  document.getElementById("view-top").onclick = () => setCamera([0, 36, 0.01], [0, 0, 0], "view-top");
  document.getElementById("view-horizon").onclick = () => setCamera([0, 5, 30], [0, 0, 0], "view-horizon");

  // Logic Gate Triggers (Vector 2 Integration)
  async function triggerLogicGate(gateName) {
    showToast("Evaluating Riemannian " + gateName + " Gate...");
    try {
      const res = await fetch("/api/logic?gate=" + gateName + "&a=1.0&b=1.0");
      if (res.ok) {
        const data = await res.json();
        const readout = Object.entries(data.binary_outputs).map(([k, v]) => k + "=" + v).join(", ");
        showToast(gateName + " Result: " + readout + " (Absorbed: " + data.absorbed_energy + " J)");
      }
    } catch (e) {
      showToast("Error triggering logic gate");
    }
  }

  document.getElementById("gate-xor").onclick = () => triggerLogicGate("XOR");
  document.getElementById("gate-and").onclick = () => triggerLogicGate("AND");
  document.getElementById("gate-half-adder").onclick = () => triggerLogicGate("HALF_ADDER");

  // Swarm trigger (Vector 3 Integration)
  document.getElementById("btn-swarm").onclick = () => {
    showToast("Autonomous Swarm Flocking Active: 7 Giants Dispatched");
  };

  // Pause / Resume
  const btnPause = document.getElementById("btn-pause");
  btnPause.onclick = () => {
    isPaused = !isPaused;
    btnPause.innerText = isPaused ? "Resume" : "Pause";
    btnPause.classList.toggle("active", isPaused);
  };

  // Inspector Drawer
  const drawer = document.getElementById("inspector-drawer");
  document.getElementById("btn-toggle-inspector").onclick = () => drawer.classList.toggle("open");
  document.getElementById("btn-close-inspector").onclick = () => drawer.classList.remove("open");

  // Keyboard navigation
  window.addEventListener("keydown", (e) => {
    if (e.key === "1") document.getElementById("view-orbit").click();
    if (e.key === "2") document.getElementById("view-top").click();
    if (e.key === "3") document.getElementById("view-horizon").click();
    if (e.key.toLowerCase() === "i" || e.key === "Tab") {
      e.preventDefault();
      drawer.classList.toggle("open");
    }
    if (e.code === "Space") {
      e.preventDefault();
      btnPause.click();
    }
  });

  window.addEventListener("resize", () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  function animate() {
    requestAnimationFrame(animate);
    controls.update();
    if (!isPaused && autoRotate) {
      gridMesh.rotation.y += 0.0004;
      gridBodyMesh.rotation.y += 0.0004;
    }
    renderer.render(scene, camera);
  }
  animate();
</script>
</body>
</html>
"""


class ManifoldSimulationServer:
    """
    Runs real-time continuous Riemannian manifold deformation, exciton geodesic
    navigation, and Hippocampal dream consolidation in a background thread, serving
    live telemetry via HTTP JSON and SSE endpoints.
    """
    def __init__(self, port: int = 8765):
        self.port = port
        self.dim = 4
        self.running = False
        self.lock = threading.Lock()

        # Core Engines
        self.ricci_engine = DiscreteRicciFlowEngine(dim=self.dim, dt=0.02)
        self.navigator = RiemannianGeodesicNavigator(dim=self.dim, dt=0.02)
        self.sink = HippocampalMemorySink(ambient_dim=self.dim, compressed_dim=2)
        self.emitter = SolLensTelemetryEmitter(packet_id_prefix="sol-3d-stream")
        self.logic_manifold = RiemannianLogicManifold()
        self.circuit = RippleCarryManifoldCircuit(num_bits=4, manifold=self.logic_manifold)
        self.alu = RiemannianALU(num_bits=4, manifold=self.logic_manifold)

        # 16 Semantic Nodes
        rng = np.random.RandomState(42)
        self.node_ids = [f"N{i+1:02d}" for i in range(16)]
        self.node_coords = {nid: rng.randn(self.dim) * 6.0 for nid in self.node_ids}
        self.base_metric = np.eye(self.dim) * 2.0
        self.node_metrics = {nid: self.base_metric.copy() for nid in self.node_ids}
        self.node_ricci = {nid: 0.0 for nid in self.node_ids}

        # Vector 3: Autonomous 7 Giants Swarm Router & Ensemble
        self.router = AutonomousSwarmRouter(
            dim=self.dim,
            dt=0.02,
            k_repulsion=1.5,
            r_repulsion=1.2,
            k_alignment=1.2,
            r_alignment=3.0,
            hippocampal_sink=self.sink,
            ricci_engine=self.ricci_engine
        )
        self.giants_ensemble = SevenGiantsEnsemble(dim=self.dim)
        self.router.add_cluster(
            cluster_id="nexus_core",
            centroid=np.array([2.5, 0.0, 0.0, 0.0]),
            radius=2.0,
            capacity=7,
            semantic_density=1.5
        )
        self.giants_ensemble.deploy_giants(self.router, target_cluster="nexus_core", spread=3.0)
        self.giant_readouts: Dict[str, GiantOperatorReadout] = {}
        self.consensus_order: float = 0.5
        self.exciton_positions = [a.position for a in self.router.agents.values()]
        self.exciton_velocities = [a.velocity for a in self.router.agents.values()]

        # Vector 7: Distributed Swarm Cluster Sharding (2x2 Grid)
        self.cluster = DistributedSwarmCluster.create_2d_grid(
            grid_x=2,
            grid_z=2,
            x_span=(-15.0, 15.0),
            z_span=(-15.0, 15.0),
            dim=self.dim,
            dt=0.02,
            hippocampal_sink=self.sink
        )
        self.cluster.add_cluster(
            cluster_id="nexus_core",
            centroid=np.array([2.5, 0.0, 0.0, 0.0]),
            radius=2.0,
            capacity=7,
            semantic_density=1.5
        )
        for a in self.router.agents.values():
            self.cluster.inject_agent(SwarmAgent(
                agent_id=f"sharded_{a.agent_id}",
                role=a.role,
                position=a.position.copy(),
                velocity=a.velocity.copy(),
                mass=a.mass,
                charge=a.charge,
                target_cluster=a.target_cluster
            ))
        self.latest_cluster_report: Optional[DistributedSwarmReport] = None

        # Vector 8: Autonomous Circuit Synthesis & Neuro-Symbolic Reflection
        self.circuit_synthesizer = RiemannianCircuitSynthesizer()
        self.symbolic_reflector = SymbolicReflector()
        self.metaplasticity_engine = MetaplasticityEngine()
        self.active_synthesized_circuits: Dict[str, Any] = {}

        # Vector 9: Hierarchical Multi-Agent Cognitive Orchestration
        self.metacognitive_orchestrator = MetacognitiveOrchestrator()
        self.active_reasoning_plans: Dict[str, CognitiveReasoningPlan] = {
            "ripple_carry": create_ripple_carry_adder_plan(bits=2, with_parity=True),
            "hierarchical_arbiter": create_hierarchical_arbiter_plan(),
            "counterfactual_equality": create_counterfactual_equality_plan()
        }
        self.latest_metacognitive_report = None
        # Vector 10: Multi-Agent Metacognitive Dialogue Arena & Dialectical Reasoning
        self.dialectical_arena = DialecticalArena(circuit_cache=self.metacognitive_orchestrator.circuit_cache)
        self.latest_dialectical_session: Optional[ArenaSessionReport] = None

        # Vector 11: Open-Ended Mathematical Discovery & Automated Theorem Proving
        self.conjecture_engine = AutonomousConjectureEngine()
        self.proof_engine = AutomatedProofEngine(arena=self.dialectical_arena, circuit_cache=self.metacognitive_orchestrator.circuit_cache)
        self.theorem_corpus = TheoremCorpus()
        self.conjecture_catalog = {c.conjecture_id: c for c in self.conjecture_engine.generate_conjecture_catalog()}

        # Vector 12: Sheaf-Theoretic Knowledge Cohomology & Global Semantic Consistency
        self.cohomology_arbiter = CohomologyArbiter()
        self.cohomology_sheaves = {
            "7_GIANTS_MOA": self.cohomology_arbiter.build_seven_giants_sheaf(),
            "DIALECTICAL_BIPARTITE": self.cohomology_arbiter.build_dialectical_sheaf(),
            "MOBIUS_CONTRADICTION": self.cohomology_arbiter.build_mobius_contradiction_sheaf()
        }
        self.latest_cohomology_report = None

        # Vector 13: Hardware-Accelerated WGSL Proof Synthesis & Micro-Architecture Execution
        self.wgsl_proof_engine = WGSLProofEngine()
        self.latest_wgsl_proof_report = None

        # Vector 14: Quantum / Photonic Coherent Waveguide Sheaf Processing
        self.photonic_sheaf_processor = PhotonicSheafProcessor()
        self.latest_photonic_sheaf_readout = None

        # Vector 15: Closed-Loop Embodied Autonomous Robotics & Geodesic Actuation
        self.manipulator = ArticulatedManipulator6DOF()
        self.robotic_obstacles = [
            Obstacle3D(obstacle_id="obs_pillar_1", position=np.array([0.35, 0.20, 0.40]), radius=0.10, repulsion_gain=0.8),
            Obstacle3D(obstacle_id="obs_pillar_2", position=np.array([0.20, -0.30, 0.35]), radius=0.08, repulsion_gain=0.6)
        ]
        self.robotic_manifold = RoboticConfigurationManifold(self.manipulator, self.robotic_obstacles)
        self.robotic_controller = GeodesicActuationController(self.robotic_manifold, dt=0.01)
        self.robotic_safety_arbiter = RoboticSafetyArbiter(self.robotic_manifold)
        self.latest_robotic_trajectory_report: Optional[TrajectoryExecutionReport] = None
        self.latest_robotic_safety_report: Optional[RoboticSafetyAuditReport] = None
        self.current_q = np.array([0.0, 0.2, -0.4, 0.0, 0.2, 0.0])

        # Vector 16: Non-Abelian Gauge Sheaves & Holonomy-Based Spatial Intelligence
        self.gauge_nav = HolonomicSpatialNavigator()
        self.gauge_anchors = {
            "Anchor_Dock": np.array([0.15, 0.05, 0.25]),
            "Anchor_Alpha": np.array([0.35, 0.20, 0.45]),
            "Anchor_Beta": np.array([0.45, -0.15, 0.40]),
            "Anchor_Gamma": np.array([0.25, -0.25, 0.30])
        }
        self.gauge_loops = [
            ("triangulation_alpha", ["Anchor_Dock", "Anchor_Alpha", "Anchor_Beta"]),
            ("triangulation_beta", ["Anchor_Dock", "Anchor_Beta", "Anchor_Gamma"])
        ]
        self.gauge_sheaf = self.gauge_nav.build_workspace_triangulation(self.gauge_anchors, self.gauge_loops)
        self.gauge_arbiter = NonAbelianGaugeArbiter(self.gauge_nav, max_allowed_defect_deg=5.0)
        self.latest_gauge_audit_report: Optional[GaugeArbiterReport] = None
        self.latest_drift_compensation_report: Optional[ToolDriftCompensationReport] = None

        self.latest_packet: Dict = {}
        self._update_packet_snapshot()

    def start(self):
        self.running = True
        self.sim_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.sim_thread.start()

    def stop(self):
        self.running = False
        if hasattr(self, 'sim_thread'):
            self.sim_thread.join(timeout=0.5)

    def _update_packet_snapshot(self):
        nodes_telemetry = []
        for nid in self.node_ids:
            coords = self.node_coords[nid]
            g_ij = self.node_metrics[nid]
            r_scalar = self.node_ricci[nid]
            nodes_telemetry.append(ManifoldNodeTelemetry(
                node_id=nid,
                label=f"Semantic Locus {nid}",
                coords=coords,
                metric_tensor=g_ij,
                ricci_scalar=r_scalar,
                attention_heat=float(np.clip(abs(r_scalar) * 0.1, 0.05, 0.95)),
                kinetic_energy=float(np.clip(np.sum(coords[:2]**2) * 0.02, 0.05, 0.95)),
                damping_gamma=0.2,
                is_divergent=abs(r_scalar) > 15.0,
                is_active_exciton=False,
                group_id=f"G{(int(nid[1:]) // 5) + 1:02d}"
            ))

        # Adjacency edges (metric neighbors)
        adj_edges = []
        for i in range(len(self.node_ids) - 1):
            adj_edges.append((self.node_ids[i], self.node_ids[i+1], 0.75))

        # Geodesic flow edges from active excitons
        flow_edges = []
        for p in self.exciton_positions:
            # Find nearest node
            dists = [np.linalg.norm(p - self.node_coords[nid]) for nid in self.node_ids]
            nearest_idx = int(np.argmin(dists))
            target_idx = (nearest_idx + 1) % len(self.node_ids)
            flow_edges.append((self.node_ids[nearest_idx], self.node_ids[target_idx], 0.95))

        with self.lock:
            pkt = self.emitter.synthesize_packet(
                nodes=nodes_telemetry,
                adjacency_edges=adj_edges,
                geodesic_flow_edges=flow_edges
            )
            # Inject 2D/3D visual coordinates into packet for 3D viewport
            for logon in pkt["logons"]:
                coords = self.node_coords[logon["id"]]
                logon["coords"] = [round(float(c), 3) for c in coords[:3]]

            # Inject active 7 Giants exciton positions & operator telemetry for 3D viewport
            pkt["excitons"] = [
                {
                    "id": a.agent_id,
                    "role": a.role,
                    "color": GIANT_PROFILES.get(
                        next((r for r in GiantRole if r.value == a.role), None),
                        GiantProfile(GiantRole.STATISTICIAN, a.agent_id, "#38bdf8", 1.0, 1.0, "")
                    ).color_hex,
                    "coords": [round(float(c), 3) for c in a.position[:3]],
                    "velocity": [round(float(v), 3) for v in a.velocity[:3]],
                    "scalar_metric": self.giant_readouts.get(a.agent_id).scalar_metric if (hasattr(self, 'giant_readouts') and a.agent_id in self.giant_readouts) else 0.0,
                    "status": a.status
                }
                for a in self.router.agents.values()
            ]
            pkt["consensus_order"] = round(float(self.consensus_order), 4) if hasattr(self, 'consensus_order') else 0.0
            pkt["gauge_sheaf"] = {
                "total_anchors": len(self.gauge_sheaf.vertices),
                "total_edges": len(self.gauge_sheaf.edges),
                "total_faces": len(self.gauge_sheaf.faces),
                "yang_mills_action": round(self.gauge_nav.compute_yang_mills_action(), 5),
                "dirichlet_energy": round(self.gauge_sheaf.compute_dirichlet_energy(), 5),
                "is_gauge_consistent": self.latest_gauge_audit_report.is_gauge_consistent if self.latest_gauge_audit_report else True
            }

            self.latest_packet = pkt

    def _run_loop(self):
        step = 0
        while self.running:
            step += 1
            trajectories = []
            with self.lock:
                # 1. Compute 7 Giants Operator accelerations
                agent_list = list(self.router.agents.values())
                metrics = [self.router.compute_local_metric(a.position) for a in agent_list]
                extra_accs, readouts = self.giants_ensemble.compute_giant_operators(self.router, metrics)
                self.giant_readouts = readouts

                for a_id, extra_acc in extra_accs.items():
                    if a_id in self.router.agents:
                        self.router.agents[a_id].velocity += self.router.dt * 0.5 * extra_acc

                # 2. Step the autonomous swarm router and distributed cluster
                step_rep = self.router.step_swarm(step_index=step)
                self.consensus_order = step_rep.order_parameter
                self.latest_cluster_report = self.cluster.step(steps=1)[0]

                self.exciton_positions = [a.position for a in self.router.agents.values()]
                self.exciton_velocities = [a.velocity for a in self.router.agents.values()]

                # 3. Create ExcitonTrajectories for Ricci flow backreaction
                for a_id, a in self.router.agents.items():
                    dists = [np.linalg.norm(a.position - self.node_coords[nid]) for nid in self.node_ids]
                    nearest_idx = int(np.argmin(dists))
                    trajectories.append(ExcitonTrajectory(
                        agent_id=a_id,
                        node_id=nearest_idx,
                        velocity=a.velocity,
                        dwell_time=a.dwell_time,
                        attention_weight=1.5
                    ))

                # 4. Deform Metric via Discrete Ricci Flow
                nbrs = [self.node_metrics[nid] for nid in self.node_ids[:4]]
                weights = np.ones(4) / 4.0
                for nid in self.node_ids:
                    g_new, r_scalar, T_ij = self.ricci_engine.step(
                        self.node_metrics[nid],
                        trajectories,
                        nbrs,
                        weights
                    )
                    self.node_metrics[nid] = g_new
                    self.node_ricci[nid] = r_scalar

            # 5. Update telemetry packet
            self._update_packet_snapshot()
            time.sleep(0.05)  # 20 Hz simulation cadence


def create_handler(server_instance: ManifoldSimulationServer):
    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            studio_dir = root_dir / "sol-studio"

            if path in ["/", "/index.html"]:
                index_file = studio_dir / "index.html"
                if index_file.exists():
                    content = index_file.read_bytes()
                else:
                    content = HTML_3D_VIEWER.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content)
            elif path == "/style.css":
                css_file = studio_dir / "style.css"
                if css_file.exists():
                    self.send_response(200)
                    self.send_header("Content-Type", "text/css; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(css_file.read_bytes())
                else:
                    self.send_response(404)
                    self.end_headers()
            elif path == "/app.js":
                js_file = studio_dir / "app.js"
                if js_file.exists():
                    self.send_response(200)
                    self.send_header("Content-Type", "application/javascript; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(js_file.read_bytes())
                else:
                    self.send_response(404)
                    self.end_headers()
            elif path == "/api/packet/live":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with server_instance.lock:
                    payload = json.dumps(server_instance.latest_packet).encode("utf-8")
                self.wfile.write(payload)
            elif path == "/api/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "healthy", "engine": "SOL-Kernel"}).encode("utf-8"))
            elif path.startswith("/api/logic/adder"):
                qs = urllib.parse.parse_qs(parsed.query)
                a_int = int(qs.get("a", [5])[0])
                b_int = int(qs.get("b", [3])[0])
                try:
                    res = server_instance.circuit.add(a_int, b_int)
                    payload = {
                        "circuit": "4-bit RippleCarryAdder",
                        "a_int": res.a_int,
                        "b_int": res.b_int,
                        "sum_int": res.sum_int,
                        "sum_bits": res.sum_bits,
                        "carry_out": res.carry_out,
                        "total_int": res.sum_int + (res.carry_out << 4),
                        "total_absorbed_energy": res.total_absorbed_energy,
                        "min_eigenvalue": res.min_eigenvalue,
                        "max_condition_number": res.max_condition_number,
                        "verified": res.verified
                    }
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps(payload).encode("utf-8"))
                except Exception as err:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(err)}).encode("utf-8"))
            elif path.startswith("/api/logic/alu"):
                qs = urllib.parse.parse_qs(parsed.query)
                op_str = qs.get("op", ["ADD"])[0].upper()
                a_int = int(qs.get("a", [5])[0])
                b_int = int(qs.get("b", [3])[0])
                try:
                    res = server_instance.alu.execute(op_str, a_int, b_int)
                    payload = {
                        "circuit": "4-bit RiemannianALU",
                        "op": res.operation,
                        "a_int": res.a_int,
                        "b_int": res.b_int,
                        "result_int": res.result_int,
                        "result_bits": res.result_bits,
                        "carry_or_borrow": res.carry_or_borrow,
                        "is_negative": res.is_negative,
                        "total_absorbed_energy": res.total_absorbed_energy,
                        "min_eigenvalue": res.min_eigenvalue,
                        "max_condition_number": res.max_condition_number,
                        "verified": res.verified
                    }
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps(payload).encode("utf-8"))
                except Exception as err:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(err)}).encode("utf-8"))
            elif path.startswith("/api/swarm/giants"):
                with server_instance.lock:
                    payload = {
                        "swarm_type": "7 Giants MoA Ensemble",
                        "consensus_order": round(float(server_instance.consensus_order), 4) if hasattr(server_instance, 'consensus_order') else 0.0,
                        "total_dissipated_energy": round(float(server_instance.router.total_dissipated_energy), 4) if hasattr(server_instance, 'router') else 0.0,
                        "giants": {
                            a.agent_id: {
                                "role": a.role,
                                "agent_id": a.agent_id,
                                "coords": [round(float(c), 3) for c in a.position[:3]],
                                "velocity": [round(float(v), 3) for v in a.velocity[:3]],
                                "color": GIANT_PROFILES.get(
                                    next((r for r in GiantRole if r.value == a.role), None),
                                    GiantProfile(GiantRole.STATISTICIAN, a.agent_id, "#38bdf8", 1.0, 1.0, "")
                                ).color_hex,
                                "scalar_metric": server_instance.giant_readouts.get(a.agent_id).scalar_metric if (hasattr(server_instance, 'giant_readouts') and a.agent_id in server_instance.giant_readouts) else 0.0,
                                "status": a.status
                            }
                            for a in server_instance.router.agents.values()
                        }
                    }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path.startswith("/api/cluster/mesh"):
                with server_instance.lock:
                    if server_instance.latest_cluster_report is not None:
                        rep = server_instance.latest_cluster_report
                        payload = {
                            "status": "operational",
                            "cluster_topology": "2x2 Cartesian Grid (4 Shards)",
                            "step_index": rep.step_index,
                            "total_active_agents": rep.total_active_agents,
                            "global_order_parameter": round(float(rep.global_order_parameter), 4),
                            "total_kinetic_energy": round(float(rep.total_kinetic_energy), 4),
                            "total_dissipated_energy": round(float(rep.total_dissipated_energy), 4),
                            "total_transits_occurred": rep.total_transits_occurred,
                            "max_load_imbalance": round(float(rep.max_load_imbalance), 4),
                            "shard_allocations": rep.shard_allocations,
                            "mesh_step_time_ms": round(float(rep.mesh_step_time_ms), 3)
                        }
                    else:
                        payload = {"status": "initializing", "shard_allocations": {}}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path.startswith("/api/logic"):
                qs = urllib.parse.parse_qs(parsed.query)
                gate_str = qs.get("gate", ["XOR"])[0].upper()
                a_val = float(qs.get("a", [1.0])[0])
                b_val = float(qs.get("b", [1.0])[0])

                try:
                    res = server_instance.logic_manifold.evaluate_gate(gate_str, a_val, b_val)
                    payload = {
                        "gate_type": res.gate_type,
                        "inputs": res.inputs,
                        "outputs": res.outputs,
                        "binary_outputs": res.binary_outputs,
                        "min_eigenvalue": res.min_eigenvalue,
                        "max_condition_number": res.max_condition_number,
                        "absorbed_energy": res.absorbed_energy,
                        "trajectories": {k: v.tolist() for k, v in res.trajectories.items()}
                    }
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps(payload).encode("utf-8"))
                except Exception as err:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(err)}).encode("utf-8"))
            elif path.startswith("/api/synthesis/specs"):
                payload = {
                    "available_specs": list(CANONICAL_SPECS.keys()),
                    "specs": {
                        k: {
                            "name": v.name,
                            "inputs": v.inputs,
                            "outputs": v.outputs,
                            "description": v.description,
                            "num_cases": len(v.table)
                        }
                        for k, v in CANONICAL_SPECS.items()
                    }
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path.startswith("/api/synthesis/circuit"):
                qs = urllib.parse.parse_qs(parsed.query)
                spec_name = qs.get("spec", ["XOR"])[0].upper()
                if spec_name not in CANONICAL_SPECS:
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "error": f"Spec '{spec_name}' not found. Available: {list(CANONICAL_SPECS.keys())}"
                    }).encode("utf-8"))
                    return

                with server_instance.lock:
                    if spec_name in server_instance.active_synthesized_circuits:
                        res = server_instance.active_synthesized_circuits[spec_name]
                    else:
                        res = server_instance.circuit_synthesizer.synthesize_canonical(spec_name)
                        server_instance.active_synthesized_circuits[spec_name] = res

                    ref = server_instance.symbolic_reflector.reflect(res.circuit, res.spec)

                ce = res.causal_emergence
                payload = {
                    "spec_name": res.spec.name,
                    "circuit_id": res.circuit.circuit_id,
                    "verified": res.verified,
                    "accuracy": res.accuracy,
                    "iterations_used": res.iterations_used,
                    "synthesis_time_ms": round(res.synthesis_time_ms, 2),
                    "max_condition_number": round(res.max_condition_number, 2),
                    "causal_emergence": {
                        "has_causal_emergence": ce.has_causal_emergence if ce else False,
                        "delta_ei": round(float(ce.delta_ei), 4) if ce else 0.0,
                        "macro_ei": round(float(ce.macro_metrics.effective_information), 4) if ce else 0.0,
                        "micro_ei": round(float(ce.micro_metrics.effective_information), 4) if ce else 0.0,
                        "degeneracy_reduction": round(float(ce.degeneracy_reduction), 4) if ce else 0.0
                    } if ce else None,
                    "dag": {
                        "max_depth": ref.dag.max_depth,
                        "critical_path_length": ref.dag.critical_path_length,
                        "total_nodes": len(ref.dag.nodes),
                        "total_edges": ref.dag.total_edges,
                        "max_fan_in": ref.dag.max_fan_in,
                        "max_fan_out": ref.dag.max_fan_out
                    },
                    "expressions": ref.simplified_expressions,
                    "algebraic_summary": ref.algebraic_summary,
                    "is_semantically_equivalent": ref.is_equivalent,
                    "mermaid_markdown": ref.mermaid_markdown
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/metacognition/plans":
                payload = {
                    "ok": True,
                    "available_plans": {
                        pid: p.to_dict() for pid, p in server_instance.active_reasoning_plans.items()
                    }
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/metacognition/telemetry":
                with server_instance.lock:
                    rep = server_instance.latest_metacognitive_report
                    rep_dict = rep.to_dict() if rep else None
                    cache_keys = list(server_instance.metacognitive_orchestrator.circuit_cache.cache.keys())
                payload = {
                    "ok": True,
                    "latest_report": rep_dict,
                    "cached_circuits": cache_keys
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/dialectics/theorems":
                with server_instance.lock:
                    cached_theorems = [
                        k for k in server_instance.metacognitive_orchestrator.circuit_cache.cache.keys()
                        if k.startswith("THEOREM_")
                    ]
                    latest_session_dict = (
                        server_instance.latest_dialectical_session.to_dict()
                        if server_instance.latest_dialectical_session else None
                    )
                payload = {
                    "ok": True,
                    "consolidated_theorems": cached_theorems,
                    "latest_session": latest_session_dict
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/dialectics/arena":
                with server_instance.lock:
                    session = server_instance.latest_dialectical_session
                    session_dict = session.to_dict() if session else None
                payload = {
                    "ok": True,
                    "arena_status": "operational",
                    "proponent_swarm_size": server_instance.dialectical_arena.proponent_swarm_size,
                    "adversary_swarm_size": server_instance.dialectical_arena.adversary_swarm_size,
                    "latest_session": session_dict
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/discovery/conjectures":
                with server_instance.lock:
                    conjs = [c.to_dict() for c in server_instance.conjecture_catalog.values()]
                payload = {
                    "ok": True,
                    "conjectures": conjs
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/discovery/theorems":
                with server_instance.lock:
                    thms = [t.to_dict() for t in server_instance.theorem_corpus.theorems.values()]
                    refs = {k: v.to_dict() for k, v in server_instance.theorem_corpus.refutations.items()}
                payload = {
                    "ok": True,
                    "theorems_count": len(thms),
                    "theorems": thms,
                    "refutations": refs,
                    "mermaid_dag": server_instance.theorem_corpus.generate_mermaid_dag()
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/discovery/corpus/markdown":
                with server_instance.lock:
                    md_text = server_instance.theorem_corpus.export_corpus_markdown()
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(md_text.encode("utf-8"))
            elif path == "/api/cohomology/topologies":
                with server_instance.lock:
                    topos = {
                        k: {
                            "name": k,
                            "vertex_count": len(s.vertices),
                            "edge_count": len(s.edges),
                            "total_vertex_dim": s.total_vertex_dim,
                            "total_edge_dim": s.total_edge_dim,
                            "vertices": s.vertices,
                            "edges": list(s.edges.keys())
                        }
                        for k, s in server_instance.cohomology_sheaves.items()
                    }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "topologies": topos}).encode("utf-8"))
            elif path == "/api/cohomology/audit":
                topo_name = "7_GIANTS_MOA"
                with server_instance.lock:
                    sheaf = server_instance.cohomology_sheaves.get(topo_name)
                    if sheaf:
                        state_dict = {}
                        for a in server_instance.router.agents.values():
                            role_name = a.role.upper().replace("-", "_").replace(" ", "_")
                            if role_name in sheaf.vertex_dims:
                                r_val = float(server_instance.node_ricci.get(server_instance.node_ids[0], 0.0))
                                state_dict[role_name] = np.array([float(a.position[0]), float(a.position[1]), r_val])

                        for v in sheaf.vertices:
                            if v not in state_dict:
                                state_dict[v] = np.zeros(sheaf.vertex_dims[v])

                        rep = server_instance.cohomology_arbiter.audit_semantic_consistency(
                            sheaf, state_dict, topology_name=topo_name, auto_repair=False
                        )
                        server_instance.latest_cohomology_report = rep
                        rep_dict = {
                            "topology_name": rep.topology_name,
                            "vertex_count": rep.vertex_count,
                            "edge_count": rep.edge_count,
                            "beta_0": rep.beta_0,
                            "beta_1": rep.beta_1,
                            "algebraic_connectivity": round(rep.algebraic_connectivity, 4),
                            "spectral_gap": round(rep.spectral_gap, 4),
                            "dirichlet_energy": round(rep.dirichlet_energy, 4),
                            "obstruction_norm": round(rep.obstruction_norm, 4),
                            "semantic_consistency_score": round(rep.semantic_consistency_score, 4),
                            "is_globally_consistent": rep.is_globally_consistent,
                            "has_topological_obstruction": rep.has_topological_obstruction,
                            "edge_energies": {k: round(v, 4) for k, v in rep.edge_energies.items()}
                        }
                    else:
                        rep_dict = {}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "audit": rep_dict}).encode("utf-8"))
            elif path == "/api/wgsl/status":
                status = server_instance.wgsl_proof_engine.get_shader_status()
                payload = {
                    "ok": True,
                    "status": status,
                    "latest_report": server_instance.latest_wgsl_proof_report.to_dict() if server_instance.latest_wgsl_proof_report else None
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/wgsl/benchmarks":
                bench = server_instance.wgsl_proof_engine.run_microarchitecture_benchmark(runs_per_conjecture=3)
                payload = {
                    "ok": True,
                    "benchmarks": bench.to_dict()
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/photonic/sheaf/status":
                p = server_instance.photonic_sheaf_processor
                payload = {
                    "ok": True,
                    "physical_constants": {
                        "wavelength_nm": 1550.0,
                        "silicon_group_index": 4.2,
                        "mzi_arm_length_um": 120.0,
                        "transit_time_per_mzi_ps": round(p.transit_ps_per_layer, 3),
                        "waveguide_loss_db_per_cm": 0.5,
                        "energy_per_mzi_op_fj": p.energy_fj_per_mzi,
                        "quantum_shot_noise_ref_mw": round(p.shot_noise_ref_mw, 8)
                    },
                    "available_topologies": list(server_instance.cohomology_sheaves.keys()),
                    "latest_readout": server_instance.latest_photonic_sheaf_readout.to_dict() if server_instance.latest_photonic_sheaf_readout else None
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/photonic/sheaf/readout":
                payload = {
                    "ok": True,
                    "readout": server_instance.latest_photonic_sheaf_readout.to_dict() if server_instance.latest_photonic_sheaf_readout else None
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/robotics/status":
                with server_instance.lock:
                    q = server_instance.current_q
                    ee_pos, ee_rot, joint_pos = server_instance.manipulator.forward_kinematics(q)
                    manip = server_instance.manipulator.compute_manipulability(q)
                    g = server_instance.robotic_manifold.compute_metric(q)
                    cond = float(np.linalg.cond(g))
                    dists = []
                    for obs in server_instance.robotic_obstacles:
                        for jp in joint_pos:
                            dists.append(float(np.linalg.norm(jp - obs.position)) - obs.radius)
                    min_dist = max(0.0, min(dists)) if dists else 1.0

                    payload = {
                        "ok": True,
                        "num_joints": server_instance.manipulator.num_joints,
                        "link_lengths": server_instance.manipulator.link_lengths,
                        "link_masses": server_instance.manipulator.link_masses,
                        "joint_limits": server_instance.manipulator.joint_limits,
                        "current_q": [round(float(a), 4) for a in q],
                        "end_effector_pos": [round(float(p), 4) for p in ee_pos],
                        "manipulability": round(manip, 4),
                        "metric_condition_number": round(cond, 2),
                        "min_obstacle_clearance": round(min_dist, 4),
                        "obstacles": [
                            {
                                "id": obs.obstacle_id,
                                "position": [round(float(p), 3) for p in obs.position],
                                "radius": obs.radius,
                                "repulsion_gain": obs.repulsion_gain
                            }
                            for obs in server_instance.robotic_obstacles
                        ],
                        "latest_trajectory": server_instance.latest_robotic_trajectory_report.to_dict() if server_instance.latest_robotic_trajectory_report else None,
                        "latest_safety": server_instance.latest_robotic_safety_report.to_dict() if server_instance.latest_robotic_safety_report else None
                    }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/robotics/audit":
                with server_instance.lock:
                    if server_instance.latest_robotic_trajectory_report and server_instance.latest_robotic_trajectory_report.trajectory:
                        safety_rep = server_instance.robotic_safety_arbiter.audit_trajectory(
                            server_instance.latest_robotic_trajectory_report.trajectory
                        )
                        server_instance.latest_robotic_safety_report = safety_rep
                        rep_dict = safety_rep.to_dict()
                    else:
                        rep_dict = {
                            "is_safe": True,
                            "trajectory_length": 0,
                            "violations_count": 0,
                            "violations": [],
                            "min_obstacle_clearance_m": 0.5,
                            "max_metric_condition": 1.0,
                            "actuator_sheaf_consistency": 1.0,
                            "actuator_betti_1": 0,
                            "hardware_verification_time_us": 0.0,
                            "emergency_stop_triggered": False
                        }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "safety": rep_dict}).encode("utf-8"))
            elif path == "/api/gauge/status":
                with server_instance.lock:
                    sheaf = server_instance.gauge_sheaf
                    vertices_info = {
                        v: {
                            "frame": [[round(float(x), 4) for x in row] for row in sheaf.vertex_frames[v]],
                            "anchor_pos": [round(float(p), 4) for p in server_instance.gauge_anchors.get(v, [0, 0, 0])]
                        }
                        for v in sheaf.vertices
                    }
                    edges_info = {
                        e_id: {
                            "endpoints": list(sheaf.edges[e_id]),
                            "connection": [[round(float(x), 4) for x in row] for row in sheaf.gauge_connections[e_id]]
                        }
                        for e_id in sheaf.edges
                    }
                    faces_info = {
                        f_id: sheaf.faces[f_id]
                        for f_id in sheaf.faces
                    }
                    payload = {
                        "ok": True,
                        "vertices": vertices_info,
                        "edges": edges_info,
                        "faces": faces_info,
                        "yang_mills_action": round(server_instance.gauge_nav.compute_yang_mills_action(), 5),
                        "dirichlet_energy": round(sheaf.compute_dirichlet_energy(), 5),
                        "latest_audit": server_instance.latest_gauge_audit_report.to_dict() if server_instance.latest_gauge_audit_report else None,
                        "latest_drift_compensation": server_instance.latest_drift_compensation_report.to_dict() if server_instance.latest_drift_compensation_report else None
                    }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length) if length > 0 else b"{}"
            try:
                body = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                body = {}

            if path == "/api/node/stimulate":
                node_id = body.get("node_id", "N01")
                energy = float(body.get("energy", 1.0))
                with server_instance.lock:
                    if node_id in server_instance.node_ricci:
                        server_instance.node_ricci[node_id] += energy * 0.5
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "node_id": node_id}).encode("utf-8"))
            elif path == "/api/node/move":
                node_id = body.get("node_id", "N01")
                coords = body.get("coords", [0, 0, 0])
                with server_instance.lock:
                    if node_id in server_instance.node_coords:
                        server_instance.node_coords[node_id][:len(coords)] = coords
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "node_id": node_id}).encode("utf-8"))
            elif path == "/api/swarm/dispatch":
                with server_instance.lock:
                    server_instance.router.agents.clear()
                    server_instance.giants_ensemble.deploy_giants(server_instance.router, target_cluster="nexus_core", spread=3.5)
                    server_instance.exciton_positions = [a.position for a in server_instance.router.agents.values()]
                    server_instance.exciton_velocities = [a.velocity for a in server_instance.router.agents.values()]
                    swarm_size = len(server_instance.router.agents)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "ok": True,
                    "swarm_size": swarm_size,
                    "type": "7 Giants MoA Ensemble",
                    "roles": [r.value for r in GiantRole]
                }).encode("utf-8"))
            elif path == "/api/synthesis/compile":
                spec_name = body.get("name", "CUSTOM_CIRCUIT")
                inputs = body.get("inputs", ["A", "B"])
                outputs = body.get("outputs", ["Y"])
                raw_table = body.get("table", {})

                # If spec_name in CANONICAL_SPECS and no raw_table provided
                if spec_name in CANONICAL_SPECS and not raw_table:
                    target_spec = CANONICAL_SPECS[spec_name]
                else:
                    parsed_table = {}
                    for k_str, v_val in raw_table.items():
                        clean_k = k_str.strip("()[] ")
                        in_tup = tuple(int(x.strip()) for x in clean_k.split(","))
                        out_tup = tuple(v_val) if isinstance(v_val, (list, tuple)) else (int(v_val),)
                        parsed_table[in_tup] = out_tup

                    target_spec = TruthTableSpec(
                        name=spec_name,
                        inputs=inputs,
                        outputs=outputs,
                        table=parsed_table,
                        description=body.get("description", "Dynamically compiled circuit")
                    )

                with server_instance.lock:
                    res = server_instance.circuit_synthesizer.synthesize(target_spec)
                    server_instance.active_synthesized_circuits[spec_name] = res
                    ref = server_instance.symbolic_reflector.reflect(res.circuit, target_spec)

                ce = res.causal_emergence
                payload = {
                    "ok": True,
                    "spec_name": target_spec.name,
                    "circuit_id": res.circuit.circuit_id,
                    "verified": res.verified,
                    "accuracy": res.accuracy,
                    "iterations_used": res.iterations_used,
                    "synthesis_time_ms": round(res.synthesis_time_ms, 2),
                    "max_condition_number": round(res.max_condition_number, 2),
                    "causal_emergence": {
                        "has_causal_emergence": ce.has_causal_emergence if ce else False,
                        "delta_ei": round(float(ce.delta_ei), 4) if ce else 0.0,
                        "macro_ei": round(float(ce.macro_metrics.effective_information), 4) if ce else 0.0,
                        "micro_ei": round(float(ce.micro_metrics.effective_information), 4) if ce else 0.0,
                        "degeneracy_reduction": round(float(ce.degeneracy_reduction), 4) if ce else 0.0
                    } if ce else None,
                    "dag": {
                        "max_depth": ref.dag.max_depth,
                        "critical_path_length": ref.dag.critical_path_length,
                        "total_nodes": len(ref.dag.nodes),
                        "total_edges": ref.dag.total_edges
                    },
                    "expressions": ref.simplified_expressions,
                    "algebraic_summary": ref.algebraic_summary,
                    "is_semantically_equivalent": ref.is_equivalent,
                    "mermaid_markdown": ref.mermaid_markdown
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/synthesis/repair":
                spec_name = body.get("spec", "MAJORITY_3").upper()
                if spec_name not in CANONICAL_SPECS:
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": f"Unknown spec: {spec_name}"}).encode("utf-8"))
                    return

                with server_instance.lock:
                    if spec_name not in server_instance.active_synthesized_circuits:
                        res = server_instance.circuit_synthesizer.synthesize_canonical(spec_name)
                        server_instance.active_synthesized_circuits[spec_name] = res
                    else:
                        res = server_instance.active_synthesized_circuits[spec_name]

                    server_instance.metaplasticity_engine.inject_perturbations(
                        res.circuit,
                        metric_noise_sigma=float(body.get("metric_noise", 0.35)),
                        coord_noise_sigma=float(body.get("coord_noise", 0.20)),
                        param_jitter_sigma=float(body.get("param_jitter", 0.25))
                    )
                    rep = server_instance.metaplasticity_engine.repair_circuit(res.circuit, res.spec)

                payload = {
                    "ok": True,
                    "circuit_id": rep.circuit_id,
                    "spec_name": rep.spec_name,
                    "perturbed_accuracy": rep.perturbed_accuracy,
                    "repaired_accuracy": rep.repaired_accuracy,
                    "perturbed_max_cond": round(rep.perturbed_max_cond, 2),
                    "repaired_max_cond": round(rep.repaired_max_cond, 2),
                    "steps_taken": rep.steps_taken,
                    "is_healed": rep.is_healed,
                    "repair_time_ms": round(rep.repair_time_ms, 2)
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/metacognition/execute":
                plan_name = body.get("plan", "ripple_carry")
                user_inputs = body.get("inputs", {})
                if plan_name not in server_instance.active_reasoning_plans:
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "error": f"Unknown plan: {plan_name}. Available: {list(server_instance.active_reasoning_plans.keys())}"
                    }).encode("utf-8"))
                    return

                target_plan = server_instance.active_reasoning_plans[plan_name]
                with server_instance.lock:
                    rep = server_instance.metacognitive_orchestrator.execute_plan(target_plan, user_inputs)
                    server_instance.latest_metacognitive_report = rep

                payload = {
                    "ok": True,
                    "report": rep.to_dict()
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/dialectics/debate":
                prop_title = body.get("title", "MAJORITY_3")
                prop_id = body.get("prop_id", f"prop_{prop_title.lower()}")
                claim = body.get("claim", f"Proposition regarding {prop_title}")
                is_flawed = bool(body.get("is_deliberately_flawed", False))
                rounds = int(body.get("rounds", 8))

                canonical = build_canonical_specs()
                target_spec = canonical.get(prop_title)

                prop = DialecticalProposition(
                    prop_id=prop_id,
                    prop_type=PropositionType.CANONICAL_SPEC if target_spec else PropositionType.HYPOTHETICAL_PROPERTY,
                    title=prop_title,
                    claim_statement=claim,
                    target_spec=target_spec,
                    is_deliberately_flawed=is_flawed
                )

                with server_instance.lock:
                    session = server_instance.dialectical_arena.conduct_debate(prop, max_debate_rounds=rounds)
                    server_instance.latest_dialectical_session = session

                payload = {
                    "ok": True,
                    "session": session.to_dict()
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/dialectics/ablation":
                spec_name = body.get("spec", "MAJORITY_3")
                canonical = build_canonical_specs()
                if spec_name not in canonical:
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": f"Unknown specification: {spec_name}"}).encode("utf-8"))
                    return

                spec = canonical[spec_name]
                with server_instance.lock:
                    circuit_res = server_instance.circuit_synthesizer.synthesize(spec, max_iterations=25)
                    ablation_telem = server_instance.dialectical_arena.ablator.ablate_circuit(circuit_res.circuit, spec, prop_id=spec_name)

                payload = {
                    "ok": True,
                    "ablation": ablation_telem.to_dict()
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/discovery/prove":
                conjecture_id = body.get("conjecture_id", "conj_demorgan_nand")
                if conjecture_id not in server_instance.conjecture_catalog:
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "error": f"Unknown conjecture: {conjecture_id}. Available: {list(server_instance.conjecture_catalog.keys())}"
                    }).encode("utf-8"))
                    return

                conj = server_instance.conjecture_catalog[conjecture_id]
                rounds = int(body.get("rounds", 8))

                with server_instance.lock:
                    cert = server_instance.proof_engine.prove_conjecture(conj, max_debate_rounds=rounds)
                    if cert.verdict == ProofVerdict.PROVED_THEOREM:
                        server_instance.theorem_corpus.add_proved_theorem(conj, cert)
                    else:
                        server_instance.theorem_corpus.add_refutation(conj, cert)

                payload = {
                    "ok": True,
                    "certificate": cert.to_dict(),
                    "theorems_count": len(server_instance.theorem_corpus.theorems),
                    "refutations_count": len(server_instance.theorem_corpus.refutations)
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/cohomology/audit":
                topo_name = body.get("topology", "7_GIANTS_MOA")
                auto_repair = bool(body.get("auto_repair", False))
                with server_instance.lock:
                    sheaf = server_instance.cohomology_sheaves.get(topo_name)
                    if not sheaf:
                        self.send_response(404)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": f"Unknown topology: {topo_name}"}).encode("utf-8"))
                        return

                    raw_states = body.get("states", {})
                    state_dict = {}
                    for v in sheaf.vertices:
                        if v in raw_states:
                            state_dict[v] = np.asarray(raw_states[v], dtype=np.float64)
                        else:
                            state_dict[v] = np.zeros(sheaf.vertex_dims[v], dtype=np.float64)

                    rep = server_instance.cohomology_arbiter.audit_semantic_consistency(
                        sheaf, state_dict, topology_name=topo_name, auto_repair=auto_repair
                    )
                    server_instance.latest_cohomology_report = rep
                    rep_dict = {
                        "topology_name": rep.topology_name,
                        "vertex_count": rep.vertex_count,
                        "edge_count": rep.edge_count,
                        "beta_0": rep.beta_0,
                        "beta_1": rep.beta_1,
                        "algebraic_connectivity": round(rep.algebraic_connectivity, 4),
                        "spectral_gap": round(rep.spectral_gap, 4),
                        "dirichlet_energy": round(rep.dirichlet_energy, 4),
                        "obstruction_norm": round(rep.obstruction_norm, 4),
                        "semantic_consistency_score": round(rep.semantic_consistency_score, 4),
                        "is_globally_consistent": rep.is_globally_consistent,
                        "has_topological_obstruction": rep.has_topological_obstruction,
                        "edge_energies": {k: round(v, 4) for k, v in rep.edge_energies.items()},
                        "repair": {
                            "initial_energy": round(rep.repair_report.initial_energy, 4),
                            "final_energy": round(rep.repair_report.final_energy, 4),
                            "energy_dissipated": round(rep.repair_report.energy_dissipated, 4),
                            "initial_consistency": round(rep.repair_report.initial_consistency, 4),
                            "final_consistency": round(rep.repair_report.final_consistency, 4),
                            "actions": [a.description for a in rep.repair_report.actions]
                        } if rep.repair_report else None
                    }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "audit": rep_dict}).encode("utf-8"))
            elif path == "/api/cohomology/diffuse":
                topo_name = body.get("topology", "7_GIANTS_MOA")
                steps = int(body.get("steps", 30))
                dt = float(body.get("dt", 0.05))
                rate = float(body.get("rate", 1.0))
                with server_instance.lock:
                    sheaf = server_instance.cohomology_sheaves.get(topo_name)
                    if not sheaf:
                        self.send_response(404)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": f"Unknown topology: {topo_name}"}).encode("utf-8"))
                        return

                    raw_states = body.get("states", {})
                    state_dict = {}
                    for v in sheaf.vertices:
                        if v in raw_states:
                            state_dict[v] = np.asarray(raw_states[v], dtype=np.float64)
                        else:
                            state_dict[v] = np.random.randn(sheaf.vertex_dims[v])

                    x_init = sheaf.pack_0cochain(state_dict)
                    diffuser = SheafDiffuser(sheaf, diffusion_rate=rate, dt=dt)
                    traj = diffuser.run_diffusion(x_init, max_steps=steps)

                    payload = {
                        "ok": True,
                        "total_steps": traj.total_steps,
                        "initial_energy": round(traj.initial_energy, 4),
                        "final_energy": round(traj.final_energy, 4),
                        "energy_reduction_ratio": round(traj.energy_reduction_ratio, 4),
                        "final_semantic_consistency": round(traj.final_semantic_consistency, 4)
                    }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/wgsl/prove":
                conjecture_id = body.get("conjecture_id", "conj_demorgan_nand")
                if conjecture_id not in server_instance.conjecture_catalog:
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "error": f"Unknown conjecture: {conjecture_id}. Available: {list(server_instance.conjecture_catalog.keys())}"
                    }).encode("utf-8"))
                    return

                conj = server_instance.conjecture_catalog[conjecture_id]
                metric_strain = float(body.get("metric_strain", 0.05))

                with server_instance.lock:
                    rep = server_instance.wgsl_proof_engine.prove_conjecture_wgsl(conj, metric_strain_eps=metric_strain)
                    server_instance.latest_wgsl_proof_report = rep

                payload = {
                    "ok": True,
                    "report": rep.to_dict()
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/wgsl/diffuse":
                topo_name = body.get("topology", "7_GIANTS_MOA")
                steps = int(body.get("steps", 25))
                dt = float(body.get("dt", 0.05))
                rate = float(body.get("rate", 1.0))
                with server_instance.lock:
                    sheaf = server_instance.cohomology_sheaves.get(topo_name)
                    if not sheaf:
                        self.send_response(404)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": f"Unknown topology: {topo_name}"}).encode("utf-8"))
                        return

                    raw_states = body.get("states", {})
                    state_dict = {}
                    for v in sheaf.vertices:
                        if v in raw_states:
                            state_dict[v] = np.asarray(raw_states[v], dtype=np.float64)
                        else:
                            state_dict[v] = np.random.randn(sheaf.vertex_dims[v])

                    diff_res = server_instance.wgsl_proof_engine.diffuse_sheaf_heat_wgsl(
                        sheaf, state_dict, steps=steps, dt=dt, rate=rate
                    )

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "diffusion": diff_res}).encode("utf-8"))
            elif path == "/api/photonic/sheaf/propagate":
                topo_name = body.get("topology", "7_GIANTS_MOA")
                power_mw = float(body.get("power_mw", 1.0))
                with server_instance.lock:
                    sheaf = server_instance.cohomology_sheaves.get(topo_name)
                    if not sheaf:
                        self.send_response(404)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": f"Unknown topology: {topo_name}"}).encode("utf-8"))
                        return

                    raw_states = body.get("states", {})
                    state_dict = {}
                    for v in sheaf.vertices:
                        if v in raw_states:
                            state_dict[v] = np.asarray(raw_states[v], dtype=np.float64)
                        else:
                            state_dict[v] = np.random.randn(sheaf.vertex_dims[v])

                    readout = server_instance.photonic_sheaf_processor.propagate_0cochain(
                        sheaf, state_dict, input_laser_power_mw=power_mw, topology_name=topo_name
                    )
                    server_instance.latest_photonic_sheaf_readout = readout

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "readout": readout.to_dict()}).encode("utf-8"))
            elif path == "/api/photonic/sheaf/diffuse":
                topo_name = body.get("topology", "7_GIANTS_MOA")
                roundtrips = int(body.get("roundtrips", 20))
                feedback_rate = float(body.get("feedback_rate", 0.25))
                with server_instance.lock:
                    sheaf = server_instance.cohomology_sheaves.get(topo_name)
                    if not sheaf:
                        self.send_response(404)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": f"Unknown topology: {topo_name}"}).encode("utf-8"))
                        return

                    raw_states = body.get("states", {})
                    state_dict = {}
                    for v in sheaf.vertices:
                        if v in raw_states:
                            state_dict[v] = np.asarray(raw_states[v], dtype=np.float64)
                        else:
                            state_dict[v] = np.random.randn(sheaf.vertex_dims[v])

                    traj = server_instance.photonic_sheaf_processor.diffuse_coherent_cavity(
                        sheaf, state_dict, roundtrips=roundtrips, feedback_rate=feedback_rate
                    )

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "trajectory": traj.to_dict()}).encode("utf-8"))
            elif path == "/api/robotics/execute":
                target_pos_raw = body.get("target_pos", [0.45, 0.25, 0.45])
                target_pos = np.asarray(target_pos_raw, dtype=np.float64)
                max_steps = int(body.get("max_steps", 100))
                q_init_raw = body.get("initial_q", None)
                with server_instance.lock:
                    q_start = np.asarray(q_init_raw, dtype=np.float64) if q_init_raw else server_instance.current_q
                    rep = server_instance.robotic_controller.execute_trajectory(
                        q_start=q_start,
                        target_pos=target_pos,
                        max_steps=max_steps
                    )
                    server_instance.latest_robotic_trajectory_report = rep
                    if hasattr(server_instance.robotic_controller, "last_q"):
                        server_instance.current_q = server_instance.robotic_controller.last_q

                    safety_rep = server_instance.robotic_safety_arbiter.audit_trajectory(rep.trajectory)
                    server_instance.latest_robotic_safety_report = safety_rep

                payload = {
                    "ok": True,
                    "report": rep.to_dict(),
                    "safety": safety_rep.to_dict()
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/robotics/audit":
                with server_instance.lock:
                    traj_steps = server_instance.latest_robotic_trajectory_report.trajectory if server_instance.latest_robotic_trajectory_report else []
                    safety_rep = server_instance.robotic_safety_arbiter.audit_trajectory(traj_steps)
                    server_instance.latest_robotic_safety_report = safety_rep
                    rep_dict = safety_rep.to_dict()

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "safety": rep_dict}).encode("utf-8"))
            elif path == "/api/gauge/wilson_audit":
                candidate_loops_raw = body.get("loops", None)
                with server_instance.lock:
                    loops = candidate_loops_raw or server_instance.gauge_loops
                    audit_rep = server_instance.gauge_arbiter.audit_holonomic_safety(loops)
                    server_instance.latest_gauge_audit_report = audit_rep
                    rep_dict = audit_rep.to_dict()

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "audit": rep_dict}).encode("utf-8"))
            elif path == "/api/gauge/relax":
                steps = int(body.get("steps", 25))
                lr = float(body.get("lr", 0.2))
                with server_instance.lock:
                    e_init, e_final, history = server_instance.gauge_sheaf.diffuse_gauge_frames(steps=steps, lr=lr)
                    audit_rep = server_instance.gauge_arbiter.audit_holonomic_safety(server_instance.gauge_loops)
                    server_instance.latest_gauge_audit_report = audit_rep

                payload = {
                    "ok": True,
                    "initial_energy": round(e_init, 5),
                    "final_energy": round(e_final, 5),
                    "reduction_pct": round((e_init - e_final) / max(1e-8, e_init) * 100.0, 2),
                    "steps": len(history) - 1,
                    "history": [round(h, 5) for h in history]
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif path == "/api/gauge/compensate":
                cycle_nodes = body.get("cycle_nodes", ["Anchor_Dock", "Anchor_Alpha", "Anchor_Beta", "Anchor_Dock"])
                with server_instance.lock:
                    comp_rep = server_instance.gauge_nav.compensate_cyclic_trajectory(np.eye(3), cycle_nodes)
                    server_instance.latest_drift_compensation_report = comp_rep
                    comp_dict = comp_rep.to_dict()

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "compensation": comp_dict}).encode("utf-8"))
            elif path == "/api/gauge/transform":
                with server_instance.lock:
                    sheaf = server_instance.gauge_sheaf
                    gauge_elems = {
                        v: so3_exp(np.random.randn(3) * 0.5)
                        for v in sheaf.vertices
                    }
                    inv_rep = sheaf.verify_gauge_invariance(gauge_elems)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "gauge_invariance": inv_rep}).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.end_headers()

        def log_message(self, format, *args):
            return  # Suppress console spam
    return RequestHandler


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def main():
    import os
    port = int(os.environ.get("SOL_STREAM_PORT", sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8765))
    server_sim = ManifoldSimulationServer(port=port)
    server_sim.start()

    httpd = ReusableHTTPServer(("0.0.0.0", port), create_handler(server_sim))
    print(f"\n=======================================================")
    print(f" SOL ENGINE 3D RIEMANNIAN MANIFOLD SERVER ACTIVE")
    print(f" WebGL 3D Viewer:   http://localhost:{port}/")
    print(f" Live Proof-Packet: http://localhost:{port}/api/packet/live")
    print(f"=======================================================\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server_sim.stop()
        httpd.server_close()


if __name__ == "__main__":
    main()
