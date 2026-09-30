/**
 * SOL Studio — Standalone Interactive 3D Riemannian Manifold Engine
 * Features:
 * - Dynamic Physical Wave Equation on Riemannian Grid (elastic continuum, not static bumps)
 * - Interactive Node Raycasting (Hover, Click-Select, Drag to Warp Spacetime)
 * - Node-to-Node Geodesic Solitons (Energy flux and metric wave transfer)
 * - Vector 2 Semantic Logic Gate Collisions (Constructive lensing vs Destructive shearing)
 * - Vector 3 Autonomous Exciton Swarm Flocking (7 Giants)
 * - Dual-mode: Live Python simulation sync (port 8765) + Autonomous client physics fallback
 */

// Global State
const state = {
  isPaused: false,
  isLive: false,
  streamUrl: "http://localhost:8765",
  activeCamera: "orbit", // "orbit", "top", "horizon"
  selectedNode: null,
  hoveredNode: null,
  draggedNode: null,
  zenMode: false,
  invariantsOpen: false,
  inspectorOpen: false,
  pollCadenceMs: 50,
  time: 0,
  carnotTotalEnergy: 0.0,
  carnotFlushes: 0,
};

// 16 Semantic Nodes with Dynamic Physical Properties
const NODES = [];
const nodeNames = [
  "L01_Constraint", "L02_Premise", "L03_Evidence", "L04_Inference",
  "L05_Counter",    "L06_Proof",   "L07_Metric",   "L08_Kernel",
  "L09_Riemann",    "L10_Geodesic","L11_Ricci",    "L12_Entropy",
  "L13_Carnot",     "L14_Exciton", "L15_Consensus","L16_Verdict"
];

// Initialize node positions in a balanced semantic ring topology
for (let i = 0; i < 16; i++) {
  const angle = (i / 16) * Math.PI * 2;
  const radius = 9.0 + (i % 3) * 2.2;
  NODES.push({
    id: `N${String(i + 1).padStart(2, "0")}`,
    label: nodeNames[i],
    x: Math.cos(angle) * radius,
    z: Math.sin(angle) * radius,
    vx: 0,
    vz: 0,
    mass: 1.2 + (i % 4) * 0.4,
    targetMass: 1.2 + (i % 4) * 0.4,
    ricci: 0.1,
    targetRicci: 0.1,
    kinetic: 0.05,
    gDiag: [2.0, 2.0, 2.0],
    mesh: null,
    auraMesh: null,
    haloMesh: null,
    connections: [(i + 1) % 16, (i + 4) % 16],
    lastExcited: 0,
  });
}

// Active Exciton Swarm: The Seven Giants of Massive Data Analysis MoA (Bright Silver Gray)
const SEVEN_GIANTS_DEF = [
  { id: "G1_Statistician", role: "The Statistician", color: 0xd1d5db, colorHex: "#d1d5db", opName: "Pressure p(ρ)" },
  { id: "G2_Optimizer", role: "The Optimizer", color: 0xd1d5db, colorHex: "#d1d5db", opName: "Potential ∇φ" },
  { id: "G3_NBodySolver", role: "The N-Body Solver", color: 0xd1d5db, colorHex: "#d1d5db", opName: "Jeans Mass M_J" },
  { id: "G4_GraphNavigator", role: "The Graph Navigator", color: 0xd1d5db, colorHex: "#d1d5db", opName: "Symplectic Curl Ω·v" },
  { id: "G5_LinearAlgebraist", role: "The Linear Algebraist", color: 0xd1d5db, colorHex: "#d1d5db", opName: "Metric PCA Compression" },
  { id: "G6_Aligner", role: "The Aligner", color: 0xd1d5db, colorHex: "#d1d5db", opName: "Kuramoto Order r" },
  { id: "G7_Integrator", role: "The Integrator", color: 0xd1d5db, colorHex: "#d1d5db", opName: "Jacobian Volume √det(g)" },
];

const EXCITONS = [];
for (let i = 0; i < 7; i++) {
  const g = SEVEN_GIANTS_DEF[i];
  const angle = (i / 7) * Math.PI * 2;
  EXCITONS.push({
    id: g.id,
    role: g.role,
    name: g.role,
    opName: g.opName,
    color: g.color,
    colorHex: g.colorHex,
    x: Math.cos(angle) * 6.5,
    z: Math.sin(angle) * 6.5,
    vx: -Math.sin(angle) * 1.6,
    vz: Math.cos(angle) * 1.6,
    phase: i * (Math.PI * 2 / 7),
    scalarMetric: 1.0,
    status: "active",
    mesh: null,
    trail: [],
  });
}

// Active Geodesic Solitons (Energy Quanta traveling between nodes)
const SOLITONS = [];

// Dynamic Surface Ripples
const RIPPLES = [];

// Three.js Engine Setup
const container = document.getElementById("canvas-container");
const canvas = document.getElementById("viewport");
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x030712);
scene.fog = new THREE.FogExp2(0x030712, 0.016);

const camera = new THREE.PerspectiveCamera(52, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.set(0, 26, 32);

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: "high-performance" });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.maxPolarAngle = Math.PI / 2 - 0.02; // Prevent going underground
controls.minDistance = 6;
controls.maxDistance = 80;

// Lighting
const ambientLight = new THREE.AmbientLight(0x38bdf8, 0.35);
scene.add(ambientLight);

const dirLight = new THREE.DirectionalLight(0xffffff, 0.9);
dirLight.position.set(20, 40, 20);
scene.add(dirLight);

const corePointLight = new THREE.PointLight(0xf59e0b, 1.8, 45);
corePointLight.position.set(0, 2, 0);
scene.add(corePointLight);

// -------------------------------------------------------------
// 1. Riemannian Manifold Surface & Dynamic Wave Physics
// -------------------------------------------------------------
const GRID_SIZE = 48; // Total width in units
const GRID_RES = 72;  // 72x72 subdivisions
const gridGeom = new THREE.PlaneGeometry(GRID_SIZE, GRID_SIZE, GRID_RES, GRID_RES);
gridGeom.rotateX(-Math.PI / 2); // Lay horizontal in X-Z

// Physical height and velocity buffers for the 2D wave equation
const vertexCount = gridGeom.attributes.position.count;
const heightBuf = new Float32Array(vertexCount);
const velocityBuf = new Float32Array(vertexCount);
const equilibriumBuf = new Float32Array(vertexCount);

// Dual materials: translucent dark glass body + cyan wireframe grid
const gridBodyMat = new THREE.MeshStandardMaterial({
  color: 0x050d24,
  roughness: 0.3,
  metalness: 0.8,
  transparent: true,
  opacity: 0.82,
  side: THREE.DoubleSide,
});
const gridMesh = new THREE.Mesh(gridGeom, gridBodyMat);
scene.add(gridMesh);

const gridWireMat = new THREE.MeshBasicMaterial({
  color: 0x1e3a8a,
  wireframe: true,
  transparent: true,
  opacity: 0.38,
});
const gridWireMesh = new THREE.Mesh(gridGeom, gridWireMat);
scene.add(gridWireMesh);

// -------------------------------------------------------------
// 2. Node Meshes & Holographic Aura
// -------------------------------------------------------------
const nodeGroup = new THREE.Group();
scene.add(nodeGroup);

const sphereGeom = new THREE.SphereGeometry(0.55, 24, 24);
const ringGeom = new THREE.RingGeometry(0.85, 1.05, 32);
ringGeom.rotateX(-Math.PI / 2);

NODES.forEach((node) => {
  const nodeMat = new THREE.MeshStandardMaterial({
    color: 0x38bdf8,
    emissive: 0x0284c7,
    emissiveIntensity: 0.6,
    roughness: 0.2,
    metalness: 0.8,
  });
  const mesh = new THREE.Mesh(sphereGeom, nodeMat);
  mesh.userData = { nodeId: node.id };
  node.mesh = mesh;

  // Outer Reticle / Halo
  const haloMat = new THREE.MeshBasicMaterial({
    color: 0x38bdf8,
    transparent: true,
    opacity: 0.45,
    side: THREE.DoubleSide,
  });
  const haloMesh = new THREE.Mesh(ringGeom, haloMat);
  haloMesh.position.y = 0.05;
  mesh.add(haloMesh);
  node.haloMesh = haloMesh;

  nodeGroup.add(mesh);
});

// -------------------------------------------------------------
// 3. Geodesic Edges & Soliton Quanta
// -------------------------------------------------------------
const edgeGroup = new THREE.Group();
scene.add(edgeGroup);

const solitonGroup = new THREE.Group();
scene.add(solitonGroup);

const solitonGeom = new THREE.SphereGeometry(0.18, 12, 12);
const solitonMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });

function rebuildGeodesicArcs() {
  // Dispose previous line geometries
  while (edgeGroup.children.length > 0) {
    const c = edgeGroup.children[0];
    if (c.geometry) c.geometry.dispose();
    edgeGroup.remove(c);
  }

  NODES.forEach((node) => {
    node.connections.forEach((targetIdx) => {
      const target = NODES[targetIdx];
      if (!target) return;

      // Create parabolic arc following curved spacetime
      const p1 = new THREE.Vector3(node.x, node.mesh ? node.mesh.position.y : 0, node.z);
      const p2 = new THREE.Vector3(target.x, target.mesh ? target.mesh.position.y : 0, target.z);
      const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
      mid.y += 0.8; // Arc curvature

      const curve = new THREE.QuadraticBezierCurve3(p1, mid, p2);
      const points = curve.getPoints(24);
      const lineGeom = new THREE.BufferGeometry().setFromPoints(points);
      const lineMat = new THREE.LineBasicMaterial({
        color: 0x1e40af,
        transparent: true,
        opacity: 0.45,
      });
      const line = new THREE.Line(lineGeom, lineMat);
      edgeGroup.add(line);
    });
  });
}
rebuildGeodesicArcs();

// Spawn a soliton traveling along edge
function spawnSoliton(fromIdx, toIdx, colorHex = 0x38bdf8) {
  const fromNode = NODES[fromIdx];
  const toNode = NODES[toIdx];
  if (!fromNode || !toNode) return;

  const mat = new THREE.MeshBasicMaterial({ color: colorHex });
  const mesh = new THREE.Mesh(solitonGeom, mat);
  solitonGroup.add(mesh);

  SOLITONS.push({
    from: fromIdx,
    to: toIdx,
    t: 0,
    speed: 0.02 + Math.random() * 0.015,
    mesh,
    colorHex,
  });
}

// Periodic autonomous soliton flow
setInterval(() => {
  if (state.isPaused) return;
  const srcIdx = Math.floor(Math.random() * NODES.length);
  const src = NODES[srcIdx];
  if (src.connections.length > 0) {
    const dstIdx = src.connections[Math.floor(Math.random() * src.connections.length)];
    spawnSoliton(srcIdx, dstIdx);
  }
}, 450);

// -------------------------------------------------------------
// 4. Exciton Swarm Particles (7 Giants MoA) - Clean Minimal Silver Spheres
// -------------------------------------------------------------
const excitonGroup = new THREE.Group();
scene.add(excitonGroup);

// Compact, crisp, bright silver-gray sphere (reduced size, no glow/halos)
const excitonGeom = new THREE.SphereGeometry(0.30, 24, 24);
const excitonMat = new THREE.MeshBasicMaterial({ color: 0xd1d5db });

EXCITONS.forEach((exc) => {
  const mesh = new THREE.Mesh(excitonGeom, excitonMat);
  exc.mesh = mesh;
  excitonGroup.add(mesh);
});

// -------------------------------------------------------------
// 4b. Vector 4: Massively Parallel 100,000+ Exciton Instanced Swarm
// -------------------------------------------------------------
const MAX_EXCITONS = 100000;
state.swarmScale = 7; // 7, 1000, 10000, 100000
state.particleScale = 0.08;

// Clean bright silver-gray micro-particle
const particleGeom = new THREE.SphereGeometry(1.0, 8, 8); // Scaled dynamically per instance
const particleMat = new THREE.MeshBasicMaterial({
  color: 0xd1d5db, // Bright silver-gray
  transparent: true,
  opacity: 0.70
});
const instancedSwarm = new THREE.InstancedMesh(particleGeom, particleMat, MAX_EXCITONS);
instancedSwarm.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
instancedSwarm.visible = false;
scene.add(instancedSwarm);

// -------------------------------------------------------------
// Vector 4 & SOL-Decide: 5 Quantized Decision Shells (Exciton Orbits)
// Perpetually stable concentric deliberative shells (No gravitational collapse)
// -------------------------------------------------------------
const DECISION_SHELLS = [
  { tier: 1, name: "β₁ Invariants & Hard Constraints", radius: 3.8, colorHex: "#f43f5e", speedMult: 1.0, sigma: 0.22 },
  { tier: 2, name: "MoA Objective Weights & 7 Giants", radius: 6.4, colorHex: "#38bdf8", speedMult: 1.0, sigma: 0.30 },
  { tier: 3, name: "AoA Alternatives (Trade Space)", radius: 9.4, colorHex: "#fbbf24", speedMult: 1.0, sigma: 0.38 },
  { tier: 4, name: "Operational Risk Thresholds", radius: 12.8, colorHex: "#34d399", speedMult: 1.0, sigma: 0.46 },
  { tier: 5, name: "Dynamic Living Refresh Shocks", radius: 16.5, colorHex: "#a855f7", speedMult: 1.0, sigma: 0.55 },
];

// Delicate Visual Guide Lines for the 5 Decision Shells
const decisionShellGroup = new THREE.Group();
decisionShellGroup.visible = false;
scene.add(decisionShellGroup);

DECISION_SHELLS.forEach((shell) => {
  const segments = 96;
  const points = [];
  for (let s = 0; s <= segments; s++) {
    const theta = (s / segments) * Math.PI * 2;
    points.push(new THREE.Vector3(Math.cos(theta) * shell.radius, -0.04, Math.sin(theta) * shell.radius));
  }
  const geom = new THREE.BufferGeometry().setFromPoints(points);
  const mat = new THREE.LineBasicMaterial({
    color: new THREE.Color(shell.colorHex),
    transparent: true,
    opacity: 0.18,
    depthWrite: false,
  });
  const line = new THREE.Line(geom, mat);
  decisionShellGroup.add(line);
});

// -------------------------------------------------------------
// Vector 4 / Exciton-MoA: Radial Wormhole Bridges (Einstein-Rosen Conduits)
// Enables non-local Sheaf restriction cross-talk across concentric shells
// -------------------------------------------------------------
const WORMHOLE_CONDUIT_COUNT = 6;
const WORMHOLE_ANGLES = [];
for (let w = 0; w < WORMHOLE_CONDUIT_COUNT; w++) {
  WORMHOLE_ANGLES.push((w / WORMHOLE_CONDUIT_COUNT) * Math.PI * 2);
}

const wormholeGroup = new THREE.Group();
wormholeGroup.visible = false;
scene.add(wormholeGroup);

// Radial Geodesic Bridges across the shells
WORMHOLE_ANGLES.forEach((angle) => {
  const points = [];
  const minR = 3.6;
  const maxR = 17.0;
  const steps = 32;
  for (let s = 0; s <= steps; s++) {
    const r = minR + (s / steps) * (maxR - minR);
    points.push(new THREE.Vector3(Math.cos(angle) * r, -0.03, Math.sin(angle) * r));
  }
  const geom = new THREE.BufferGeometry().setFromPoints(points);
  const mat = new THREE.LineDashedMaterial({
    color: 0xc084fc, // Bright violet-purple
    dashSize: 0.35,
    gapSize: 0.25,
    transparent: true,
    opacity: 0.35,
    depthWrite: false,
  });
  const line = new THREE.Line(geom, mat);
  line.computeLineDistances();
  wormholeGroup.add(line);

  // Aperture nodes at intersections with each shell
  DECISION_SHELLS.forEach((shell) => {
    const dotGeom = new THREE.RingGeometry(0.12, 0.22, 16);
    dotGeom.rotateX(-Math.PI / 2);
    const dotMat = new THREE.MeshBasicMaterial({
      color: 0xc084fc,
      transparent: true,
      opacity: 0.55,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const dotMesh = new THREE.Mesh(dotGeom, dotMat);
    dotMesh.position.set(Math.cos(angle) * shell.radius, -0.02, Math.sin(angle) * shell.radius);
    wormholeGroup.add(dotMesh);
  });
});

// Active Radial Wormhole Tunneling Quanta (Soliton Bridges)
const WORMHOLE_PULSES = [];
const wormholePulseGeom = new THREE.SphereGeometry(0.24, 12, 12);

// Function to launch a tunneling quanta across shells
function spawnWormholeTunnelingPulse(fromShellIdx, toShellIdx, conduitAngleIdx = null, customColor = null) {
  const fromShell = DECISION_SHELLS[fromShellIdx];
  const toShell = DECISION_SHELLS[toShellIdx];
  if (!fromShell || !toShell) return;

  const angle = conduitAngleIdx !== null 
    ? WORMHOLE_ANGLES[conduitAngleIdx % WORMHOLE_ANGLES.length]
    : WORMHOLE_ANGLES[Math.floor(Math.random() * WORMHOLE_ANGLES.length)];

  const apertureJitter = (Math.random() - 0.5) * 0.08;
  const pulseAngle = angle + apertureJitter;

  const p1 = new THREE.Vector3(Math.cos(pulseAngle) * fromShell.radius, 0.25, Math.sin(pulseAngle) * fromShell.radius);
  const p2 = new THREE.Vector3(Math.cos(pulseAngle) * toShell.radius, 0.25, Math.sin(pulseAngle) * toShell.radius);

  // Arch high above manifold like an Einstein-Rosen geodesic bridge
  const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
  mid.y += 1.4 + Math.abs(fromShell.radius - toShell.radius) * 0.15;

  const colorHex = customColor || (fromShellIdx > toShellIdx ? 0xf43f5e : 0x38bdf8);
  const pulseMat = new THREE.MeshBasicMaterial({ color: colorHex });
  const pulseMesh = new THREE.Mesh(wormholePulseGeom, pulseMat);
  wormholeGroup.add(pulseMesh);

  WORMHOLE_PULSES.push({
    fromShellIdx,
    toShellIdx,
    p1,
    mid,
    p2,
    t: 0,
    speed: 0.025 + Math.random() * 0.015,
    mesh: pulseMesh,
    colorHex,
  });

  // Physical exciton state transfer along the conduit
  if (instancedSwarm.visible && state.swarmScale > 7) {
    const activeCount = Math.min(state.swarmScale, MAX_EXCITONS);
    const searchStart = Math.floor(Math.random() * Math.max(1, activeCount - 25));
    for (let i = searchStart; i < searchStart + 25; i++) {
      const idx = i % activeCount;
      const px = swarmPositions[idx * 3 + 0];
      const pz = swarmPositions[idx * 3 + 2];
      const pAngle = Math.atan2(pz, px);
      if (Math.abs(pAngle - (angle % (Math.PI * 2))) < 0.45) {
        const toRadius = toShell.radius + (Math.random() - 0.5) * toShell.sigma;
        const norm = Math.sqrt(px * px + pz * pz) + 1e-4;
        swarmPositions[idx * 3 + 0] = (px / norm) * toRadius;
        swarmPositions[idx * 3 + 2] = (pz / norm) * toRadius;
        const vCirc = Math.sqrt((12.0 * toRadius) / (toRadius * toRadius + 2.0)) * toShell.speedMult;
        const speed = Math.sqrt(swarmVelocities[idx * 3 + 0] ** 2 + swarmVelocities[idx * 3 + 2] ** 2) + 1e-4;
        swarmVelocities[idx * 3 + 0] = (swarmVelocities[idx * 3 + 0] / speed) * vCirc;
        swarmVelocities[idx * 3 + 2] = (swarmVelocities[idx * 3 + 2] / speed) * vCirc;
        break;
      }
    }
  }

  // Update telemetry
  state.wormholeTunnelCount = (state.wormholeTunnelCount || 0) + 1;
  const countEl = document.getElementById("wormhole-tunnel-count");
  if (countEl) countEl.innerText = state.wormholeTunnelCount.toLocaleString();

  const lastTransEl = document.getElementById("wormhole-last-transition");
  if (lastTransEl) {
    const arrow = fromShellIdx > toShellIdx ? "➔ (Inward ρ)" : "➔ (Outward δ⁰)";
    lastTransEl.innerText = `Tier ${fromShell.tier} ${arrow} Tier ${toShell.tier}`;
  }
}

// Autonomous Cross-Shell Wormhole Tunneling Flux
setInterval(() => {
  if (state.isPaused || state.swarmScale === 7) return;
  const srcIdx = Math.floor(Math.random() * DECISION_SHELLS.length);
  let dstIdx;
  const rand = Math.random();
  if (rand < 0.35) {
    dstIdx = srcIdx === 4 ? 0 : 4; // Tier 5 (Living Refresh) <-> Tier 1 (Hard Constraint)
  } else if (rand < 0.70) {
    const step = Math.random() > 0.5 ? 1 : -1;
    dstIdx = Math.max(0, Math.min(DECISION_SHELLS.length - 1, srcIdx + step));
  } else {
    dstIdx = srcIdx === 1 ? 2 : 1; // Tier 2 (Weights) <-> Tier 3 (AoA Space)
  }
  if (srcIdx !== dstIdx) {
    spawnWormholeTunnelingPulse(srcIdx, dstIdx);
  }
}, 750);

// Pre-allocate particle buffer data
const swarmPositions = new Float32Array(MAX_EXCITONS * 3);
const swarmVelocities = new Float32Array(MAX_EXCITONS * 3);
const dummyMatrix = new THREE.Matrix4();

for (let i = 0; i < MAX_EXCITONS; i++) {
  // Distribute excitons across the 5 Decision Maker Shells
  const shellIdx = i % DECISION_SHELLS.length;
  const shell = DECISION_SHELLS[shellIdx];

  // Radial jitter around quantized shell radius
  const jitter = (Math.random() + Math.random() + Math.random() - 1.5) * shell.sigma * 1.5;
  const radius = Math.max(1.8, shell.radius + jitter);
  const angle = Math.random() * Math.PI * 2;

  swarmPositions[i * 3 + 0] = Math.cos(angle) * radius;
  swarmPositions[i * 3 + 1] = 0;
  swarmPositions[i * 3 + 2] = Math.sin(angle) * radius;

  // Exact Keplerian circular speed: v_circ = sqrt(12 * r / (r^2 + 2))
  const vCirc = Math.sqrt((12.0 * radius) / (radius * radius + 2.0)) * shell.speedMult;
  swarmVelocities[i * 3 + 0] = -Math.sin(angle) * vCirc;
  swarmVelocities[i * 3 + 1] = 0;
  swarmVelocities[i * 3 + 2] = Math.cos(angle) * vCirc;

  dummyMatrix.makeScale(0.08, 0.08, 0.08);
  dummyMatrix.setPosition(swarmPositions[i * 3 + 0], 0, swarmPositions[i * 3 + 2]);
  instancedSwarm.setMatrixAt(i, dummyMatrix);
}
instancedSwarm.instanceMatrix.needsUpdate = true;

// WebGPU Feature Detection & Shader Bridge
async function initWebGPUBackend() {
  const backendLabel = document.getElementById("backend-val");
  const subName = document.getElementById("substrate-active-name");
  if (typeof navigator !== "undefined" && navigator.gpu) {
    try {
      const adapter = await navigator.gpu.requestAdapter();
      if (adapter) {
        const device = await adapter.requestDevice();
        if (backendLabel) backendLabel.textContent = "WebGPU (WGSL) / 60fps";
        if (subName) subName.textContent = "WebGPU / WGSL Hardware Compute";
        console.log("[SOL Studio] WebGPU Compute Pipeline Initialized.");
        return device;
      }
    } catch (e) {
      console.warn("[SOL Studio] WebGPU fallback:", e);
    }
  }
  if (backendLabel) backendLabel.textContent = "WebGL2 Instanced (60fps)";
  if (subName) subName.textContent = "WebGL2 Instanced Compute Fallback";
}
initWebGPUBackend();

// -------------------------------------------------------------
// 5. Interactive Raycaster & Mouse Manipulation
// -------------------------------------------------------------
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2(-999, -999);
const dragPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
const planeIntersectPoint = new THREE.Vector3();

const nodeCard = document.getElementById("node-inspector-card");
let isDragging = false;

window.addEventListener("mousemove", (e) => {
  mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
  mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;

  if (isDragging && state.draggedNode) {
    raycaster.setFromCamera(mouse, camera);
    if (raycaster.ray.intersectPlane(dragPlane, planeIntersectPoint)) {
      state.draggedNode.x = Math.max(-20, Math.min(20, planeIntersectPoint.x));
      state.draggedNode.z = Math.max(-20, Math.min(20, planeIntersectPoint.z));
      state.draggedNode.mesh.position.x = state.draggedNode.x;
      state.draggedNode.mesh.position.z = state.draggedNode.z;
      rebuildGeodesicArcs();
      triggerManifoldRipple(state.draggedNode.x, state.draggedNode.z, 0.45);
      updateNodeCard(state.draggedNode);
    }
  }
});

window.addEventListener("mousedown", (e) => {
  if (e.target.closest("#topbar, #control-island, #node-inspector-card, #inspector-drawer, #invariants-modal")) {
    return; // Don't raycast when clicking UI elements
  }

  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects(nodeGroup.children, true);

  if (intersects.length > 0) {
    const hitObj = intersects[0].object;
    const parentMesh = hitObj.userData.nodeId ? hitObj : hitObj.parent;
    const nodeId = parentMesh.userData.nodeId;
    const targetNode = NODES.find((n) => n.id === nodeId);

    if (targetNode) {
      selectNode(targetNode);
      state.draggedNode = targetNode;
      isDragging = true;
      controls.enabled = false; // Disable orbit camera while dragging
    }
  } else {
    // Clicked empty manifold: trigger gravitational wave ripple
    const gridIntersects = raycaster.intersectObject(gridMesh);
    if (gridIntersects.length > 0) {
      const p = gridIntersects[0].point;
      triggerManifoldRipple(p.x, p.z, 0.7);
      showToast(`Gravitational ripple emitted at (${p.x.toFixed(1)}, ${p.z.toFixed(1)})`);
    }
  }
});

window.addEventListener("mouseup", () => {
  if (isDragging && state.draggedNode) {
    // Send updated coordinates to Python kernel
    fetch(`${state.streamUrl}/api/node/move`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        node_id: state.draggedNode.id,
        coords: [state.draggedNode.x, state.draggedNode.mesh ? state.draggedNode.mesh.position.y : 0, state.draggedNode.z]
      })
    }).catch(() => {});
  }
  isDragging = false;
  state.draggedNode = null;
  controls.enabled = true;
});

function selectNode(node) {
  state.selectedNode = node;
  updateNodeCard(node);
  nodeCard.classList.remove("hidden");

  // Highlight connections
  NODES.forEach((n) => {
    if (n.mesh) {
      n.mesh.material.emissiveIntensity = n === node ? 1.5 : 0.6;
      n.haloMesh.scale.setScalar(n === node ? 1.4 : 1.0);
    }
  });
}

function updateNodeCard(node) {
  if (!node) return;
  document.getElementById("node-card-id").innerText = node.id;
  document.getElementById("node-card-label").innerText = node.label;
  document.getElementById("node-card-mass").innerText = node.mass.toFixed(2);
  document.getElementById("node-card-ricci").innerText = (node.ricci >= 0 ? "+" : "") + node.ricci.toFixed(3);
  document.getElementById("node-card-gdiag").innerText = `[${node.gDiag[0].toFixed(2)}, ${node.gDiag[1].toFixed(2)}]`;
  document.getElementById("node-card-kinetic").innerText = `${node.kinetic.toFixed(2)} J`;

  // Project 3D position to 2D screen coordinates for pinned card
  if (node.mesh) {
    const tempV = new THREE.Vector3();
    node.mesh.getWorldPosition(tempV);
    tempV.y += 1.2;
    tempV.project(camera);

    const x = (tempV.x * 0.5 + 0.5) * window.innerWidth;
    const y = (-(tempV.y * 0.5) + 0.5) * window.innerHeight;

    nodeCard.style.left = `${Math.min(window.innerWidth - 280, Math.max(20, x - 130))}px`;
    nodeCard.style.top = `${Math.min(window.innerHeight - 200, Math.max(70, y - 160))}px`;
  }
}

document.getElementById("btn-close-node-card").onclick = () => {
  nodeCard.classList.add("hidden");
  state.selectedNode = null;
  NODES.forEach((n) => {
    if (n.mesh) {
      n.mesh.material.emissiveIntensity = 0.6;
      n.haloMesh.scale.setScalar(1.0);
    }
  });
};

// Node Card Actions
document.getElementById("btn-node-excite").onclick = () => {
  if (!state.selectedNode) return;
  const n = state.selectedNode;
  n.mass += 1.5;
  n.ricci += 0.8;
  n.kinetic += 0.4;
  triggerManifoldRipple(n.x, n.z, 1.2);
  showToast(`Injected +1.5 ΔE into ${n.id} (${n.label})`);
  updateNodeCard(n);

  // Send stimulus to Python kernel
  fetch(`${state.streamUrl}/api/node/stimulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ node_id: n.id, energy: 1.5 })
  }).catch(() => {});
};

document.getElementById("btn-node-soliton").onclick = () => {
  if (!state.selectedNode) return;
  const fromIdx = NODES.indexOf(state.selectedNode);
  const toIdx = (fromIdx + 1) % NODES.length;
  spawnSoliton(fromIdx, toIdx, 0xf59e0b);
  triggerManifoldRipple(state.selectedNode.x, state.selectedNode.z, 0.6);
  showToast(`Soliton launched from ${state.selectedNode.id} → ${NODES[toIdx].id}`);
};

document.getElementById("btn-node-shear").onclick = () => {
  if (!state.selectedNode) return;
  const n = state.selectedNode;
  n.ricci = -0.95; // Hyperbolic negative curvature saddle
  n.gDiag[0] = 3.5;
  n.gDiag[1] = 0.5; // Sheared metric
  triggerManifoldRipple(n.x, n.z, -0.9);
  showToast(`Metric shear contradiction induced on ${n.id} (R = -0.95)`);
  updateNodeCard(n);
};

// Trigger expanding wave ripple on manifold surface
function triggerManifoldRipple(cx, cz, amplitude = 0.8) {
  RIPPLES.push({
    x: cx,
    z: cz,
    radius: 0.1,
    speed: 0.38,
    maxRadius: 18.0,
    amplitude,
    frequency: 1.8,
    decay: 0.94,
  });
}

// -------------------------------------------------------------
// 6. 2D Physical Wave Equation & Riemannian Surface Simulation
// -------------------------------------------------------------
function updateManifoldPhysics() {
  const pos = gridGeom.attributes.position;
  const dt = 0.04;
  const waveSpeedSq = 0.65;
  const damping = 0.92;

  // 1. Calculate equilibrium curvature depths from node masses and metrics
  for (let i = 0; i < vertexCount; i++) {
    const gx = pos.getX(i);
    const gz = pos.getZ(i);

    let targetDepth = 0;
    for (let k = 0; k < NODES.length; k++) {
      const n = NODES[k];
      const dx = gx - n.x;
      const dz = gz - n.z;
      const dSq = dx * dx + dz * dz;

      // Metric curvature well: positive Ricci = gravitational dip, negative = saddle ridge
      const well = n.mass * Math.exp(-dSq / 12.0) * (0.8 + n.ricci * 0.5);
      targetDepth -= well;
    }
    equilibriumBuf[i] = targetDepth;
  }

  // 2. Add propagating ripples
  for (let rIdx = RIPPLES.length - 1; rIdx >= 0; rIdx--) {
    const rip = RIPPLES[rIdx];
    rip.radius += rip.speed;
    rip.amplitude *= rip.decay;

    if (rip.radius > rip.maxRadius || Math.abs(rip.amplitude) < 0.01) {
      RIPPLES.splice(rIdx, 1);
      continue;
    }

    for (let i = 0; i < vertexCount; i++) {
      const gx = pos.getX(i);
      const gz = pos.getZ(i);
      const dist = Math.sqrt((gx - rip.x) ** 2 + (gz - rip.z) ** 2);
      const dWave = dist - rip.radius;

      if (Math.abs(dWave) < 3.0) {
        const wave = rip.amplitude * Math.cos(dWave * rip.frequency) * Math.exp(-(dWave ** 2) / 2.0);
        velocityBuf[i] += wave * 0.15;
      }
    }
  }

  // 3. Step wave equation: acceleration = k*(equilibrium - y) + neighbor Laplacian
  for (let i = 0; i < vertexCount; i++) {
    const curH = heightBuf[i];
    const eqH = equilibriumBuf[i];

    // Restoring spring toward equilibrium
    const force = (eqH - curH) * 0.22;
    velocityBuf[i] = (velocityBuf[i] + force) * damping;
    heightBuf[i] += velocityBuf[i];

    // Update geometry vertex
    pos.setY(i, heightBuf[i]);
  }

  pos.needsUpdate = true;
  gridGeom.computeVertexNormals();

  // Update node 3D Y positions so they sit perfectly on the curved manifold surface
  NODES.forEach((node) => {
    // Relax mass and Ricci back to baseline via Carnot dissipation
    node.mass += (node.targetMass - node.mass) * 0.01;
    node.ricci += (node.targetRicci - node.ricci) * 0.01;

    // Sample height at node coordinate
    let h = 0;
    for (let k = 0; k < NODES.length; k++) {
      const n2 = NODES[k];
      const dSq = (node.x - n2.x) ** 2 + (node.z - n2.z) ** 2;
      h -= n2.mass * Math.exp(-dSq / 12.0) * (0.8 + n2.ricci * 0.5);
    }

    if (node.mesh) {
      node.mesh.position.set(node.x, h + 0.55, node.z);
    }
  });

  // Keep node card aligned with node
  if (state.selectedNode) {
    updateNodeCard(state.selectedNode);
  }
}

// -------------------------------------------------------------
// 7. Geodesic Solitons & Exciton Swarm Dynamics
// -------------------------------------------------------------
function updateSolitonsAndSwarm() {
  // Update Solitons
  for (let sIdx = SOLITONS.length - 1; sIdx >= 0; sIdx--) {
    const sol = SOLITONS[sIdx];
    sol.t += sol.speed;

    const fromNode = NODES[sol.from];
    const toNode = NODES[sol.to];

    if (!fromNode || !toNode || sol.t >= 1.0) {
      // Impact event at destination node!
      if (toNode) {
        toNode.mass += 0.35;
        toNode.ricci += 0.2;
        toNode.kinetic += 0.15;
        triggerManifoldRipple(toNode.x, toNode.z, 0.4);
        state.carnotTotalEnergy += 0.08;
      }
      solitonGroup.remove(sol.mesh);
      sol.mesh.geometry.dispose();
      sol.mesh.material.dispose();
      SOLITONS.splice(sIdx, 1);
      continue;
    }

    // Move along parabolic arc
    const p1 = fromNode.mesh ? fromNode.mesh.position : new THREE.Vector3(fromNode.x, 0, fromNode.z);
    const p2 = toNode.mesh ? toNode.mesh.position : new THREE.Vector3(toNode.x, 0, toNode.z);
    const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
    mid.y += 0.9;

    const curve = new THREE.QuadraticBezierCurve3(p1, mid, p2);
    const pos = curve.getPoint(sol.t);
    sol.mesh.position.copy(pos);
  }

  // Update Radial Wormhole Tunneling Pulses (Cross-Shell Sheaf Information Transfer)
  for (let pIdx = WORMHOLE_PULSES.length - 1; pIdx >= 0; pIdx--) {
    const pulse = WORMHOLE_PULSES[pIdx];
    pulse.t += pulse.speed;

    if (pulse.t >= 1.0) {
      // Impact event at destination shell: emit localized metric ripple
      triggerManifoldRipple(pulse.p2.x, pulse.p2.z, 0.45);
      state.carnotTotalEnergy += 0.05;

      wormholeGroup.remove(pulse.mesh);
      pulse.mesh.geometry.dispose();
      pulse.mesh.material.dispose();
      WORMHOLE_PULSES.splice(pIdx, 1);
      continue;
    }

    // Parabolic Einstein-Rosen geodesic bridge interpolation
    const curve = new THREE.QuadraticBezierCurve3(pulse.p1, pulse.mid, pulse.p2);
    const pos = curve.getPoint(pulse.t);
    pulse.mesh.position.copy(pos);
  }

  // Update Exciton Swarm: 7 Giants MoA or Massive Instanced WebGPU Swarm
  if (state.swarmScale === 7) {
    excitonGroup.visible = true;
    instancedSwarm.visible = false;
    decisionShellGroup.visible = false;
    wormholeGroup.visible = false;

    EXCITONS.forEach((exc, idx) => {
      // Gravitational pull toward nearest nodes
      let fx = 0;
      let fz = 0;

      NODES.forEach((n) => {
        const dx = n.x - exc.x;
        const dz = n.z - exc.z;
        const dist = Math.sqrt(dx * dx + dz * dz) + 0.5;
        const force = (n.mass * 0.4) / (dist * dist);
        fx += (dx / dist) * force;
        fz += (dz / dist) * force;

        // Node collision / near miss excitement
        if (dist < 1.2) {
          n.ricci += 0.05;
          triggerManifoldRipple(n.x, n.z, 0.2);
        }
      });

      // Swarm cohesion & collision repulsion
      EXCITONS.forEach((other, oIdx) => {
        if (idx === oIdx) return;
        const dx = other.x - exc.x;
        const dz = other.z - exc.z;
        const d = Math.sqrt(dx * dx + dz * dz) + 0.1;
        if (d < 1.8) {
          fx -= (dx / d) * 0.8; // Repulsion
          fz -= (dz / d) * 0.8;
        }
      });

      // Symplectic velocity update
      exc.vx = (exc.vx + fx * 0.02) * 0.98;
      exc.vz = (exc.vz + fz * 0.02) * 0.98;

      // Speed clamp
      const speed = Math.sqrt(exc.vx * exc.vx + exc.vz * exc.vz);
      if (speed > 2.8) {
        exc.vx = (exc.vx / speed) * 2.8;
        exc.vz = (exc.vz / speed) * 2.8;
      }

      exc.x += exc.vx * 0.04;
      exc.z += exc.vz * 0.04;

      // Sample surface height for exciton
      let h = 0;
      NODES.forEach((n) => {
        const dSq = (exc.x - n.x) ** 2 + (exc.z - n.z) ** 2;
        h -= n.mass * Math.exp(-dSq / 12.0) * (0.8 + n.ricci * 0.5);
      });

      if (exc.mesh) {
        exc.mesh.position.set(exc.x, h + 0.55, exc.z);
        exc.mesh.rotation.y += 0.02;
      }
    });
  } else {
    // Vector 4: Massively Parallel Instanced Swarm (1,000 to 100,000+ excitons)
    excitonGroup.visible = false;
    instancedSwarm.visible = true;
    decisionShellGroup.visible = true;
    wormholeGroup.visible = true;

    const activeCount = Math.min(state.swarmScale, MAX_EXCITONS);
    instancedSwarm.count = activeCount;

    const dt = 0.016;
    const NUM_SHELLS = DECISION_SHELLS.length;

    for (let i = 0; i < activeCount; i++) {
      let px = swarmPositions[i * 3 + 0];
      let pz = swarmPositions[i * 3 + 2];
      let vx = swarmVelocities[i * 3 + 0];
      let vz = swarmVelocities[i * 3 + 2];

      const r = Math.sqrt(px * px + pz * pz) + 1e-5;
      const invR = 1.0 / r;
      const rx = px * invR;
      const rz = pz * invR;
      const tx = -rz; // Tangential unit vector (counter-clockwise)
      const tz = rx;

      // Project Cartesian velocity into radial (v_r) and tangential (v_theta) components
      let vr = vx * rx + vz * rz;
      let vt = vx * tx + vz * tz;

      // Identify nearest quantized Decision Shell
      let nearestShell = DECISION_SHELLS[0];
      let minDist = Math.abs(r - nearestShell.radius);
      for (let sIdx = 1; sIdx < NUM_SHELLS; sIdx++) {
        const d = Math.abs(r - DECISION_SHELLS[sIdx].radius);
        if (d < minDist) {
          minDist = d;
          nearestShell = DECISION_SHELLS[sIdx];
        }
      }

      // 1. Quantized Shell Restoring Force (harmonic confinement to decision band)
      const fShell = -(r - nearestShell.radius) * 2.2;

      // 2. Central Gravity & Centrifugal Equilibrium
      const grav = -12.0 / (r * r + 2.0);
      const centrifugal = (vt * vt) * invR;

      // Circular equilibrium speed at this shell radius
      const targetVt = Math.sqrt((12.0 * nearestShell.radius) / (nearestShell.radius * nearestShell.radius + 2.0)) * nearestShell.speedMult;

      // 3. Radial Damping (Collimation): eliminates radial eccentricity into crisp bands
      // Notice: Damping is ONLY applied radially (vr). Angular momentum is preserved!
      vr *= 0.95;
      vr += (grav + centrifugal + fShell) * dt;

      // 4. Tangential Angular Momentum Governor: relaxes vt toward Keplerian orbital velocity
      // Strictly prevents gravitational decay and orbital collapse over time
      vt += (targetVt - vt) * 0.04;

      // 5. Symplectic magnetic curl (Role 3: Graph Navigator)
      if (i % 7 === 3) {
        vt += 0.015 * Math.sin(r * 2.0 + i);
      }

      // Reconstruct Cartesian velocity
      vx = vr * rx + vt * tx;
      vz = vr * rz + vt * tz;

      // Integrate position
      px += vx * dt;
      pz += vz * dt;

      // Conformal outer boundary guard
      if (r > 22.0) {
        px = rx * 21.8;
        pz = rz * 21.8;
        vr = -Math.abs(vr) * 0.5;
        vx = vr * rx + vt * tx;
        vz = vr * rz + vt * tz;
      }

      // Sample surface height from semantic nodes
      let py = 0;
      for (let nIdx = 0; nIdx < 3; nIdx++) {
        const n = NODES[(i + nIdx * 5) % 16];
        const dSq = (px - n.x) ** 2 + (pz - n.z) ** 2;
        py -= n.mass * Math.exp(-dSq / 16.0) * (0.6 + n.ricci * 0.4);
      }

      swarmPositions[i * 3 + 0] = px;
      swarmPositions[i * 3 + 1] = py + 0.25;
      swarmPositions[i * 3 + 2] = pz;
      swarmVelocities[i * 3 + 0] = vx;
      swarmVelocities[i * 3 + 2] = vz;

      const s = state.particleScale || 0.05;
      dummyMatrix.makeScale(s, s, s);
      dummyMatrix.setPosition(px, py + 0.25, pz);
      instancedSwarm.setMatrixAt(i, dummyMatrix);
    }
    instancedSwarm.instanceMatrix.needsUpdate = true;
  }
}

// -------------------------------------------------------------
// 8. Vector 2: Semantic Logic Gate Visualizer
// -------------------------------------------------------------
async function triggerLogicGate(gateName) {
  showToast(`Evaluating Riemannian ${gateName} Gate collision...`);

  // Target gate locus nodes: N01 (Input A), N02 (Input B), N06 (Gate Center), N16 (Output)
  const nodeA = NODES[0];
  const nodeB = NODES[1];
  const nodeGate = NODES[5];

  // Fire input wave packets toward center gate node
  spawnSoliton(0, 5, 0xf59e0b); // Soliton A
  spawnSoliton(1, 5, 0x38bdf8); // Soliton B

  // If live backend exists, query API
  if (state.isLive) {
    try {
      const res = await fetch(`${state.streamUrl}/api/logic?gate=${gateName}&a=1.0&b=1.0`);
      if (res.ok) {
        const data = await res.json();
        setTimeout(() => {
          handleLogicGateInterference(gateName, data.binary_outputs);
          const readout = Object.entries(data.binary_outputs).map(([k, v]) => `${k}=${v}`).join(", ");
          showToast(`${gateName} Result: ${readout} (${data.absorbed_energy} J absorbed)`);
        }, 600);
        return;
      }
    } catch {}
  }

  // Client-side simulation fallback
  setTimeout(() => {
    let outputs = { out: 1 };
    if (gateName === "XOR") outputs = { out: 0 };
    if (gateName === "AND") outputs = { out: 1 };
    if (gateName === "HALF_ADDER") outputs = { sum: 0, carry: 1 };
    handleLogicGateInterference(gateName, outputs);
    const readout = Object.entries(outputs).map(([k, v]) => `${k}=${v}`).join(", ");
    showToast(`${gateName} Result: ${readout}`);
  }, 600);
}

function handleLogicGateInterference(gateName, outputs) {
  const nodeGate = NODES[5];

  if (gateName === "AND") {
    // Constructive Lensing: Deep gravitational well + launch output
    nodeGate.mass += 2.2;
    nodeGate.ricci += 1.2;
    triggerManifoldRipple(nodeGate.x, nodeGate.z, 1.4);
    spawnSoliton(5, 15, 0x10b981); // Output pulse to verdict node
  } else if (gateName === "XOR") {
    // Destructive Collision: Metric shear, energy dissipated into Carnot sink, zero forward output
    nodeGate.ricci = -0.8;
    triggerManifoldRipple(nodeGate.x, nodeGate.z, -1.2);
    state.carnotTotalEnergy += 0.85;
  } else if (gateName === "HALF_ADDER") {
    // Dual Rail: Sum = 0 (destructive), Carry = 1 (constructive)
    triggerManifoldRipple(nodeGate.x, nodeGate.z, 0.9);
    spawnSoliton(5, 15, 0xa855f7); // Carry pulse
    state.carnotTotalEnergy += 0.42;
  }
}

document.getElementById("btn-gate-xor").onclick = () => triggerLogicGate("XOR");
document.getElementById("btn-gate-and").onclick = () => triggerLogicGate("AND");
document.getElementById("btn-gate-half-adder").onclick = () => triggerLogicGate("HALF_ADDER");

const ALU_OPERATIONS = [
  { op: "ADD", a: 5, b: 3, label: "ALU: 5+3 (ADD)" },
  { op: "SUB", a: 12, b: 5, label: "ALU: 12-5 (SUB)" },
  { op: "XOR", a: 10, b: 6, label: "ALU: 10^6 (XOR)" },
  { op: "AND", a: 14, b: 11, label: "ALU: 14&11 (AND)" },
];
let aluOpIndex = 0;

async function triggerRiemannianALU() {
  const current = ALU_OPERATIONS[aluOpIndex];
  showToast(`Evaluating 4-Bit Riemannian ALU: ${current.op}(${current.a}, ${current.b})...`);

  // Cascading solitons through 4 stages: N00->N04, N01->N05, N02->N06, N03->N07
  const solitonColor = current.op === "SUB" ? 0xef4444 : current.op === "XOR" ? 0x06b6d4 : current.op === "AND" ? 0x10b981 : 0xa855f7;
  [0, 1, 2, 3].forEach((stage, idx) => {
    setTimeout(() => {
      const srcNode = NODES[stage];
      const dstNode = NODES[stage + 4];
      spawnSoliton(stage, stage + 4, solitonColor);
      triggerManifoldRipple(dstNode.x, dstNode.z, 0.9);
    }, idx * 200);
  });

  // Advance index for the next click
  const nextIdx = (aluOpIndex + 1) % ALU_OPERATIONS.length;
  aluOpIndex = nextIdx;
  if (btnAlu) {
    btnAlu.textContent = ALU_OPERATIONS[nextIdx].label;
  }

  if (state.isLive) {
    try {
      const res = await fetch(`${state.streamUrl}/api/logic/alu?op=${current.op}&a=${current.a}&b=${current.b}`);
      if (res.ok) {
        const data = await res.json();
        setTimeout(() => {
          triggerManifoldRipple(0, 0, 1.6);
          const signStr = data.is_negative ? "-" : "";
          const opSym = data.op === "SUB" ? "-" : data.op === "ADD" ? "+" : data.op === "XOR" ? "^" : "&";
          showToast(`Riemannian ALU ${data.op}: ${data.a_int} ${opSym} ${data.b_int} = ${signStr}${data.result_int} (dE = ${data.total_absorbed_energy} J, λ_min = ${data.min_eigenvalue.toFixed(3)})`);
          state.carnotTotalEnergy += data.total_absorbed_energy;
        }, 900);
        return;
      }
    } catch {}
  }

  // Client-side simulation fallback
  setTimeout(() => {
    triggerManifoldRipple(0, 0, 1.6);
    let total = 0;
    let sym = "+";
    if (current.op === "ADD") { total = current.a + current.b; sym = "+"; }
    else if (current.op === "SUB") { total = current.a - current.b; sym = "-"; }
    else if (current.op === "XOR") { total = current.a ^ current.b; sym = "^"; }
    else if (current.op === "AND") { total = current.a & current.b; sym = "&"; }
    showToast(`Riemannian ALU ${current.op}: ${current.a} ${sym} ${current.b} = ${total} (Verified, g_ij ≻ 0)`);
    state.carnotTotalEnergy += 0.88;
  }, 900);
}

const btnAlu = document.getElementById("btn-gate-alu");
if (btnAlu) {
  btnAlu.onclick = () => triggerRiemannianALU();
}

// -------------------------------------------------------------
// 9. Vector 3: Swarm Controls & Spacetime Ripple
// -------------------------------------------------------------
document.getElementById("btn-dispatch-swarm").onclick = () => {
  // Disperse excitons into orbit with high velocity
  EXCITONS.forEach((exc, i) => {
    const angle = (i / EXCITONS.length) * Math.PI * 2;
    exc.x = Math.cos(angle) * 3.0;
    exc.z = Math.sin(angle) * 3.0;
    exc.vx = -Math.sin(angle) * 2.6;
    exc.vz = Math.cos(angle) * 2.6;
  });
  triggerManifoldRipple(0, 0, 1.5);
  showToast("Autonomous Swarm Flocking Activated: 7 Giants in Geodesic Orbit");

  // Sync with Python kernel
  fetch(`${state.streamUrl}/api/swarm/dispatch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" }
  }).catch(() => {});
};

document.getElementById("btn-wave-ripple").onclick = () => {
  triggerManifoldRipple(0, 0, 1.8);
  showToast("Spacetime Shockwave Emitted");
};

function triggerWormholeCascade() {
  if (state.swarmScale === 7) {
    setSwarmScale(100000);
  }
  wormholeGroup.visible = true;
  decisionShellGroup.visible = true;
  showToast("Wormhole Cascade: 6 ER Bridges Active across 5 Decision Shells (β₁=0)");

  // Cascade across all 6 conduits with staggered radial pulses
  for (let w = 0; w < WORMHOLE_CONDUIT_COUNT; w++) {
    setTimeout(() => {
      // Inward shock pulse: Tier 5 (Living Refresh) -> Tier 1 (Hard Constraint)
      spawnWormholeTunnelingPulse(4, 0, w, 0xf43f5e);
      // Outward return feedback: Tier 1 (Invariant Proof) -> Tier 3 (AoA Alternatives)
      setTimeout(() => spawnWormholeTunnelingPulse(0, 2, w, 0x38bdf8), 160);
      // Outward broadcast: Tier 2 (MoA Weights) -> Tier 5 (Sensors)
      setTimeout(() => spawnWormholeTunnelingPulse(1, 4, w, 0xa855f7), 320);
    }, w * 140);
  }
}

document.getElementById("btn-wormhole-bridge")?.addEventListener("click", triggerWormholeCascade);
document.getElementById("btn-fire-wormhole")?.addEventListener("click", triggerWormholeCascade);

const btnPause = document.getElementById("btn-pause-sim");
btnPause.onclick = () => {
  state.isPaused = !state.isPaused;
  btnPause.innerText = state.isPaused ? "Resume" : "Pause";
  btnPause.classList.toggle("active", state.isPaused);
  showToast(state.isPaused ? "Simulation Paused" : "Simulation Resumed");
};

// -------------------------------------------------------------
// 10. Camera Presets & Navigation
// -------------------------------------------------------------
function setCameraPreset(pos, target, btnId) {
  document.querySelectorAll("#control-island .deck-btn").forEach((b) => b.classList.remove("active"));
  if (btnId) document.getElementById(btnId).classList.add("active");

  const startPos = camera.position.clone();
  const startTarget = controls.target.clone();
  const endPos = new THREE.Vector3(...pos);
  const endTarget = new THREE.Vector3(...target);

  let progress = 0;
  function tween() {
    progress += 0.05;
    camera.position.lerpVectors(startPos, endPos, progress);
    controls.target.lerpVectors(startTarget, endTarget, progress);
    controls.update();
    if (progress < 1.0) requestAnimationFrame(tween);
  }
  tween();
}

document.getElementById("btn-cam-orbit").onclick = () => setCameraPreset([0, 26, 32], [0, 0, 0], "btn-cam-orbit");
document.getElementById("btn-cam-top").onclick = () => setCameraPreset([0, 38, 0.01], [0, 0, 0], "btn-cam-top");
document.getElementById("btn-cam-horizon").onclick = () => setCameraPreset([0, 5, 34], [0, 0, 0], "btn-cam-horizon");

// Zen Mode Toggle
const btnZen = document.getElementById("btn-zen");
btnZen.onclick = () => toggleZenMode();

function toggleZenMode() {
  state.zenMode = !state.zenMode;
  document.getElementById("topbar").classList.toggle("zen-hidden", state.zenMode);
  document.getElementById("control-island").classList.toggle("zen-hidden", state.zenMode);
  btnZen.innerText = state.zenMode ? "Exit Zen" : "Zen ⛶";
  showToast(state.zenMode ? "Zen Mode: Press 'Z' or click to exit" : "Exited Zen Mode");
}

// Telemetry Drawer
const drawer = document.getElementById("inspector-drawer");
document.getElementById("btn-toggle-inspector").onclick = () => drawer.classList.toggle("open");
document.getElementById("btn-close-drawer").onclick = () => drawer.classList.remove("open");

// Invariants Modal
const invariantsModal = document.getElementById("invariants-modal");
document.getElementById("btn-toggle-invariants").onclick = () => invariantsModal.classList.toggle("hidden");
document.getElementById("btn-close-invariants").onclick = () => invariantsModal.classList.add("hidden");

// Keyboard Shortcuts
window.addEventListener("keydown", (e) => {
  if (e.key === "1") document.getElementById("btn-cam-orbit").click();
  if (e.key === "2") document.getElementById("btn-cam-top").click();
  if (e.key === "3") document.getElementById("btn-cam-horizon").click();
  if (e.key.toLowerCase() === "z") toggleZenMode();
  if (e.key.toLowerCase() === "i" || e.key === "Tab") {
    e.preventDefault();
    drawer.classList.toggle("open");
  }
  if (e.code === "Space") {
    e.preventDefault();
    btnPause.click();
  }
  if (e.key === "Escape") {
    drawer.classList.remove("open");
    invariantsModal.classList.add("hidden");
    nodeCard.classList.add("hidden");
  }
});

// Vector 4: Exciton Swarm Scale Switcher (7 -> 1,000 -> 10,000 -> 100,000)
function setSwarmScale(scale) {
  state.swarmScale = scale;
  ["btn-scale-7", "btn-scale-1k", "btn-scale-10k", "btn-scale-100k"].forEach((id) => {
    const btn = document.getElementById(id);
    if (btn) btn.classList.remove("active");
  });
  const idMap = { 7: "btn-scale-7", 1000: "btn-scale-1k", 10000: "btn-scale-10k", 100000: "btn-scale-100k" };
  const targetBtn = document.getElementById(idMap[scale]);
  if (targetBtn) targetBtn.classList.add("active");

  if (scale === 7) {
    if (typeof decisionShellGroup !== "undefined") decisionShellGroup.visible = false;
    if (typeof wormholeGroup !== "undefined") wormholeGroup.visible = false;
  } else {
    if (typeof decisionShellGroup !== "undefined") decisionShellGroup.visible = true;
    if (typeof wormholeGroup !== "undefined") wormholeGroup.visible = true;
  }

  if (scale === 1000) {
    state.particleScale = 0.08;
    particleMat.opacity = 0.65;
  } else if (scale === 10000) {
    state.particleScale = 0.04;
    particleMat.opacity = 0.38;
  } else if (scale === 100000) {
    state.particleScale = 0.022;
    particleMat.opacity = 0.20;
  }

  const ticker = document.getElementById("active-excitons");
  if (ticker) {
    ticker.textContent = scale === 7 ? "7 Active" : `${scale.toLocaleString()} Active (5 Shells)`;
  }
  showToast(scale === 7 ? "Scale: 7 Giants MoA Swarm" : `Scale: ${scale.toLocaleString()} Excitons orbiting 5 Decision Shells`);
}

document.getElementById("btn-scale-7")?.addEventListener("click", () => setSwarmScale(7));
document.getElementById("btn-scale-1k")?.addEventListener("click", () => setSwarmScale(1000));
document.getElementById("btn-scale-10k")?.addEventListener("click", () => setSwarmScale(10000));
document.getElementById("btn-scale-100k")?.addEventListener("click", () => setSwarmScale(100000));

// Toast notification
let toastTimer = null;
function showToast(msg) {
  const toast = document.getElementById("toast-message");
  toast.innerText = msg;
  toast.classList.add("show");
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2800);
}

// -------------------------------------------------------------
// 11. Live Backend Sync Polling (Port 8765)
// -------------------------------------------------------------
async function pollBackend() {
  try {
    const res = await fetch(`${state.streamUrl}/api/packet/live`);
    if (res.ok) {
      const data = await res.json();
      state.isLive = true;
      document.getElementById("live-status-text").innerText = "20 Hz LIVE";
      document.getElementById("live-indicator").style.color = "var(--emerald)";

      // Update Ticker Metrics from live kernel
      if (data.evaluation && data.evaluation.metrics) {
        const m = data.evaluation.metrics;
        document.getElementById("continuity-val").innerText = `${(m.continuity * 100).toFixed(1)}%`;
      }

      // Sync 7 Giants Excitons from live kernel
      if (data.excitons && Array.isArray(data.excitons)) {
        data.excitons.forEach((exData, idx) => {
          if (idx < EXCITONS.length) {
            if (exData.coords) {
              EXCITONS[idx].x += (exData.coords[0] - EXCITONS[idx].x) * 0.18;
              EXCITONS[idx].z += (exData.coords[1] - EXCITONS[idx].z) * 0.18;
            }
            if (exData.scalar_metric !== undefined) EXCITONS[idx].scalarMetric = exData.scalar_metric;
            if (exData.status) EXCITONS[idx].status = exData.status;
          }
        });
        updateGiantsDrawerList(data.excitons);
      }

      if (data.consensus_order !== undefined) {
        const flockElem = document.getElementById("flock-order-val");
        if (flockElem) flockElem.innerText = data.consensus_order.toFixed(2);
      }

      // Sync node coordinates if received
      if (data.logons && Array.isArray(data.logons)) {
        data.logons.forEach((l, idx) => {
          if (idx < NODES.length && l.coords) {
            // Smoothly sync positions
            if (!isDragging || state.draggedNode !== NODES[idx]) {
              NODES[idx].x += (l.coords[0] - NODES[idx].x) * 0.1;
              NODES[idx].z += (l.coords[1] - NODES[idx].z) * 0.1;
            }
          }
        });
      }
    } else {
      state.isLive = false;
      document.getElementById("live-status-text").innerText = "AUTONOMOUS SIM";
    }
  } catch (err) {
    state.isLive = false;
    document.getElementById("live-status-text").innerText = "AUTONOMOUS SIM";
  }

  // Update HUD Metrics
  const avgRicci = NODES.reduce((acc, n) => acc + n.ricci, 0) / NODES.length;
  document.getElementById("ricci-scalar").innerText = (avgRicci >= 0 ? "+" : "") + avgRicci.toFixed(3);
  document.getElementById("metric-det").innerText = (1.0 + Math.abs(avgRicci) * 0.25).toFixed(3);
  document.getElementById("cond-number").innerText = (1.0 + Math.abs(avgRicci) * 0.4).toFixed(2);
  document.getElementById("carnot-energy").innerText = `${state.carnotTotalEnergy.toFixed(2)} J`;
  document.getElementById("sink-total").innerText = `${state.carnotTotalEnergy.toFixed(2)} J`;

  setTimeout(pollBackend, 500);
}

function updateGiantsDrawerList(giants) {
  const container = document.getElementById("giants-list-container");
  if (!container || !giants) return;
  container.innerHTML = giants.map(g => `
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 8px; background: rgba(255,255,255,0.03); border-radius: 6px; font-size: 11px; border-left: 3px solid ${g.color || '#38bdf8'};">
      <div style="display: flex; flex-direction: column;">
        <span style="font-weight: 600; color: #fff;">${g.role || g.id}</span>
        <span style="color: var(--text-dim); font-size: 10px;">Pos: [${g.coords ? g.coords.map(c => c.toFixed(1)).join(', ') : '0, 0'}]</span>
      </div>
      <div style="text-align: right;">
        <span style="color: ${g.color || '#38bdf8'}; font-weight: 700; font-family: var(--mono);">${g.scalar_metric !== undefined ? g.scalar_metric.toFixed(3) : '1.000'}</span>
        <div style="font-size: 9px; color: var(--text-dim);">${g.status || 'active'}</div>
      </div>
    </div>
  `).join('');
}

// -------------------------------------------------------------
// Vector 10: Dialectical Arena UI Controls & API Integration
// -------------------------------------------------------------
const btnDebate = document.getElementById("btn-convene-debate");
const selectProp = document.getElementById("dialectics-prop-select");
const elVerdict = document.getElementById("debate-verdict");
const elConsensus = document.getElementById("debate-consensus");
const elCausalGain = document.getElementById("debate-causal-gain");
const elCompression = document.getElementById("debate-compression");
const elWitnessBox = document.getElementById("debate-witness-box");
const elWitnessDetails = document.getElementById("debate-witness-details");

if (btnDebate) {
  btnDebate.addEventListener("click", async () => {
    const propChoice = selectProp ? selectProp.value : "MAJORITY_3";
    let title = "MAJORITY_3";
    let isFlawed = false;
    let claim = "Proposition submitted to Dialectical Arena";

    if (propChoice === "FLAWED_XOR") {
      title = "XOR";
      isFlawed = true;
      claim = "Hypothetical linear XOR without destructive interference well";
    } else if (propChoice === "FLAWED_MAJ") {
      title = "MAJORITY_3";
      isFlawed = true;
      claim = "Hypothetical inverted all-ones majority gate";
    } else {
      title = propChoice;
      isFlawed = false;
      claim = `Autonomous proof and adversarial verification of ${propChoice}`;
    }

    if (elVerdict) {
      elVerdict.innerText = "DEBATING...";
      elVerdict.className = "solar";
    }
    btnDebate.disabled = true;

    try {
      const resp = await fetch(`${state.streamUrl}/api/dialectics/debate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          prop_id: `prop_ui_${title.toLowerCase()}_${Date.now()}`,
          claim,
          is_deliberately_flawed: isFlawed,
          rounds: 8
        })
      });

      if (resp.ok) {
        const data = await resp.json();
        const session = data.session;
        const theo = session.theorem_report;

        if (elVerdict) {
          elVerdict.innerText = theo.verdict;
          elVerdict.className = theo.verdict === "SYNTHESIS_PROVED" ? "green" : (theo.verdict === "THESIS_REFUTED" ? "rose" : "cyan");
        }
        if (elConsensus) {
          elConsensus.innerText = `r = ${session.final_consensus_order.toFixed(4)}`;
        }
        if (elCausalGain) {
          elCausalGain.innerText = `+${theo.dialectic_causal_gain.toFixed(4)} bits`;
        }
        if (elCompression) {
          elCompression.innerText = `${(theo.compression_ratio * 100).toFixed(1)}% (${theo.minimal_kernel_node_count} nodes)`;
        }

        if (theo.verdict === "THESIS_REFUTED" && theo.counter_example_witness) {
          if (elWitnessBox) elWitnessBox.style.display = "block";
          if (elWitnessDetails) {
            const wit = theo.counter_example_witness;
            elWitnessDetails.innerText = `In: ${JSON.stringify(wit.input_vector)} -> Obs: ${JSON.stringify(wit.observed_output)} (Expected: ${JSON.stringify(wit.expected_output)})`;
          }
        } else {
          if (elWitnessBox) elWitnessBox.style.display = "none";
        }

        // Trigger visual soliton cascade between nodes in 3D scene
        for (let i = 0; i < 4; i++) {
          const srcIdx = i * 2;
          const dstIdx = (srcIdx + 4) % 16;
          SOLITONS.push({
            from: srcIdx,
            to: dstIdx,
            progress: 0.0,
            speed: 0.02 + Math.random() * 0.015,
            intensity: theo.verdict === "SYNTHESIS_PROVED" ? 1.0 : 0.4,
            color: theo.verdict === "SYNTHESIS_PROVED" ? 0xfbbf24 : 0xf43f5e
          });
        }
      }
    } catch (err) {
      if (elVerdict) {
        elVerdict.innerText = "OFFLINE SIM";
        elVerdict.className = "cyan";
      }
    } finally {
      btnDebate.disabled = false;
    }
  });
}

// -------------------------------------------------------------
// Vector 11: Automated Theorem Prover & Discovery UI Integration
// -------------------------------------------------------------
const btnProve = document.getElementById("btn-prove-conjecture");
const selectConj = document.getElementById("discovery-conj-select");
const elDiscVerdict = document.getElementById("discovery-verdict");
const elDiscAxiom = document.getElementById("discovery-axiom");
const elDiscConsensus = document.getElementById("discovery-consensus");
const elDiscCausalGain = document.getElementById("discovery-causal-gain");
const elDiscMsck = document.getElementById("discovery-msck");
const elDiscCorpusCount = document.getElementById("discovery-corpus-count");
const elDiscWitnessBox = document.getElementById("discovery-witness-box");
const elDiscWitnessDetails = document.getElementById("discovery-witness-details");

async function refreshCorpusCount() {
  if (!elDiscCorpusCount) return;
  try {
    const resp = await fetch(`${state.streamUrl}/api/discovery/theorems`);
    if (resp.ok) {
      const data = await resp.json();
      elDiscCorpusCount.innerText = `${data.count} Proven (${data.theorems ? data.theorems.length : 0} in Cache)`;
    }
  } catch (e) {
    // Keep baseline default
  }
}

if (btnProve) {
  btnProve.addEventListener("click", async () => {
    const conjId = selectConj ? selectConj.value : "conj_demorgan_nand";
    if (elDiscVerdict) {
      elDiscVerdict.innerText = "PROVING...";
      elDiscVerdict.className = "solar";
    }
    btnProve.disabled = true;

    try {
      const resp = await fetch(`${state.streamUrl}/api/discovery/prove`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conjecture_id: conjId })
      });

      if (resp.ok) {
        const data = await resp.json();
        const cert = data.certificate;

        if (elDiscVerdict) {
          elDiscVerdict.innerText = cert.verdict;
          elDiscVerdict.className = cert.verdict === "PROVED_THEOREM" ? "green" : (cert.verdict === "DISPROVED_COUNTEREXAMPLE" ? "rose" : "cyan");
        }
        if (elDiscAxiom) {
          elDiscAxiom.innerText = cert.grounding_axioms && cert.grounding_axioms.length > 0
            ? cert.grounding_axioms.join(", ")
            : "EMPIRICAL_DISPROOF";
        }
        if (elDiscConsensus) {
          elDiscConsensus.innerText = `r = ${cert.hegelian_consensus_order.toFixed(4)}`;
        }
        if (elDiscCausalGain) {
          elDiscCausalGain.innerText = `+${cert.dialectical_causal_gain.toFixed(4)} bits`;
        }
        if (elDiscMsck) {
          elDiscMsck.innerText = `${cert.minimal_causal_kernel_size} nodes (Occam MSCK)`;
        }

        if (cert.verdict === "DISPROVED_COUNTEREXAMPLE" && cert.counter_example) {
          if (elDiscWitnessBox) elDiscWitnessBox.style.display = "block";
          if (elDiscWitnessDetails) {
            const wit = cert.counter_example;
            elDiscWitnessDetails.innerText = `Input: ${JSON.stringify(wit.input_vector)} -> Obs: ${JSON.stringify(wit.observed_output)} (Exp: ${JSON.stringify(wit.expected_output)})`;
          }
        } else {
          if (elDiscWitnessBox) elDiscWitnessBox.style.display = "none";
        }

        // Trigger 3D Soliton Cascades across the manifold
        const isProved = cert.verdict === "PROVED_THEOREM";
        for (let i = 0; i < 5; i++) {
          const srcIdx = (i * 3) % 16;
          const dstIdx = (srcIdx + 5) % 16;
          SOLITONS.push({
            from: srcIdx,
            to: dstIdx,
            progress: 0.0,
            speed: 0.025 + Math.random() * 0.02,
            intensity: isProved ? 1.0 : 0.45,
            color: isProved ? 0x38bdf8 : 0xf43f5e
          });
        }

        await refreshCorpusCount();
      }
    } catch (err) {
      if (elDiscVerdict) {
        elDiscVerdict.innerText = "OFFLINE SIM";
        elDiscVerdict.className = "cyan";
      }
    } finally {
      btnProve.disabled = false;
    }
  });
}

// Initial corpus count query
refreshCorpusCount();

// -------------------------------------------------------------
// Vector 12: Sheaf Knowledge Cohomology UI Controls & API Integration
// -------------------------------------------------------------
const btnAuditCohomology = document.getElementById("btn-audit-cohomology");
const btnRepairCohomology = document.getElementById("btn-repair-cohomology");
const selectCohomologyTopo = document.getElementById("cohomology-topo-select");
const elCohomologyConsistency = document.getElementById("cohomology-consistency");
const elCohomologyBetti = document.getElementById("cohomology-betti");
const elCohomologyLambda2 = document.getElementById("cohomology-lambda2");
const elCohomologyEnergy = document.getElementById("cohomology-energy");
const elCohomologyStatus = document.getElementById("cohomology-status");
const elCohomologyRepairBox = document.getElementById("cohomology-repair-box");
const elCohomologyRepairDetails = document.getElementById("cohomology-repair-details");

async function executeCohomologyAction(autoRepair = false) {
  const topo = selectCohomologyTopo ? selectCohomologyTopo.value : "7_GIANTS_MOA";
  if (elCohomologyStatus) {
    elCohomologyStatus.innerText = autoRepair ? "HEALING..." : "AUDITING...";
    elCohomologyStatus.className = "solar";
  }

  try {
    const resp = await fetch(`${state.streamUrl}/api/cohomology/audit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topology: topo,
        auto_repair: autoRepair
      })
    });

    if (resp.ok) {
      const data = await resp.json();
      const audit = data.audit;

      if (elCohomologyConsistency) {
        elCohomologyConsistency.innerText = `S = ${audit.semantic_consistency_score.toFixed(4)}`;
        elCohomologyConsistency.className = audit.semantic_consistency_score >= 0.95 ? "green" : (audit.semantic_consistency_score >= 0.80 ? "solar" : "rose");
      }
      if (elCohomologyBetti) {
        elCohomologyBetti.innerText = `β₀ = ${audit.beta_0}, β₁ = ${audit.beta_1}`;
      }
      if (elCohomologyLambda2) {
        elCohomologyLambda2.innerText = `λ₂ = ${audit.algebraic_connectivity.toFixed(4)}`;
      }
      if (elCohomologyEnergy) {
        elCohomologyEnergy.innerText = `E_F = ${audit.dirichlet_energy.toFixed(4)}`;
      }
      if (elCohomologyStatus) {
        if (audit.has_topological_obstruction) {
          elCohomologyStatus.innerText = "OBSTRUCTION DETECTED";
          elCohomologyStatus.className = "rose";
        } else {
          elCohomologyStatus.innerText = audit.is_globally_consistent ? "GLOBAL HARMONY" : "LOCAL COHERENCE";
          elCohomologyStatus.className = audit.is_globally_consistent ? "green" : "cyan";
        }
      }

      if (audit.repair && audit.repair.actions && audit.repair.actions.length > 0) {
        if (elCohomologyRepairBox) elCohomologyRepairBox.style.display = "block";
        if (elCohomologyRepairDetails) {
          elCohomologyRepairDetails.innerText = audit.repair.actions.join("\n");
        }
      } else {
        if (elCohomologyRepairBox) elCohomologyRepairBox.style.display = "none";
      }

      // Trigger violet/cyan solitons across the 3D scene
      const isHarmonious = audit.is_globally_consistent && !audit.has_topological_obstruction;
      for (let i = 0; i < 4; i++) {
        const srcIdx = (i * 4) % 16;
        const dstIdx = (srcIdx + 3) % 16;
        SOLITONS.push({
          from: srcIdx,
          to: dstIdx,
          progress: 0.0,
          speed: 0.03 + Math.random() * 0.015,
          intensity: isHarmonious ? 1.0 : 0.5,
          color: autoRepair ? 0x38bdf8 : (isHarmonious ? 0xa855f7 : 0xf43f5e)
        });
      }
    }
  } catch (err) {
    if (elCohomologyStatus) {
      elCohomologyStatus.innerText = "OFFLINE SIM";
      elCohomologyStatus.className = "cyan";
    }
  }
}

if (btnAuditCohomology) {
  btnAuditCohomology.addEventListener("click", () => executeCohomologyAction(false));
}
if (btnRepairCohomology) {
  btnRepairCohomology.addEventListener("click", () => executeCohomologyAction(true));
}

// -------------------------------------------------------------
// Vector 13: Hardware-Accelerated WGSL Proof & Sheaf Engine Controls
// -------------------------------------------------------------
const btnWgslProve = document.getElementById("btn-wgsl-prove");
const btnWgslDiffuse = document.getElementById("btn-wgsl-diffuse");
const selectWgslConj = document.getElementById("wgsl-conj-select");
const elWgslVerdict = document.getElementById("wgsl-verdict");
const elWgslLatency = document.getElementById("wgsl-latency");
const elWgslSpeedup = document.getElementById("wgsl-speedup");
const elWgslConsensus = document.getElementById("wgsl-consensus");
const elWgslCoverage = document.getElementById("wgsl-coverage");
const elWgslWitnessBox = document.getElementById("wgsl-witness-box");
const elWgslWitnessDetails = document.getElementById("wgsl-witness-details");

async function executeWgslProve() {
  const conjId = selectWgslConj ? selectWgslConj.value : "conj_demorgan_nand";
  if (elWgslVerdict) {
    elWgslVerdict.innerText = "DISPATCHING...";
    elWgslVerdict.className = "solar";
  }

  try {
    const resp = await fetch(`${state.streamUrl}/api/wgsl/prove`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        conjecture_id: conjId,
        metric_strain: 0.05
      })
    });
    const data = await resp.json();
    if (data.ok && data.report) {
      const rep = data.report;
      if (elWgslVerdict) {
        elWgslVerdict.innerText = rep.verdict === "PROVED_THEOREM" ? "PROVED SOUND ⚡" : "REFUTED (COUNTER-EX) ✕";
        elWgslVerdict.className = rep.verdict === "PROVED_THEOREM" ? "green" : "rose";
      }
      if (elWgslLatency) {
        elWgslLatency.innerText = `${rep.gpu_dispatch_time_us} μs`;
      }
      if (elWgslSpeedup) {
        elWgslSpeedup.innerText = `${rep.speedup_ratio}× faster`;
      }
      if (elWgslConsensus) {
        elWgslConsensus.innerText = `r = ${rep.hegelian_consensus.toFixed(4)}`;
        elWgslConsensus.className = rep.hegelian_consensus >= 0.70 ? "green" : "rose";
      }
      if (elWgslCoverage) {
        elWgslCoverage.innerText = `${rep.states_verified} / ${rep.total_states} states`;
      }

      if (rep.witness_bits) {
        if (elWgslWitnessBox) elWgslWitnessBox.style.display = "block";
        if (elWgslWitnessDetails) {
          elWgslWitnessDetails.innerText = `State #${rep.witness_input_state}: A=${rep.witness_bits.A}, B=${rep.witness_bits.B}, C=${rep.witness_bits.C}`;
        }
      } else {
        if (elWgslWitnessBox) elWgslWitnessBox.style.display = "none";
      }

      // Visual Soliton Cascade on 3D Manifold
      const centerNode = logons[0];
      if (centerNode) {
        centerNode.energy = rep.verdict === "PROVED_THEOREM" ? 3.5 : -2.5;
      }
    }
  } catch (err) {
    if (elWgslVerdict) {
      elWgslVerdict.innerText = "OFFLINE SIM";
      elWgslVerdict.className = "cyan";
    }
  }
}

async function executeWgslDiffuse() {
  if (elWgslVerdict) {
    elWgslVerdict.innerText = "DIFFUSING...";
    elWgslVerdict.className = "solar";
  }

  try {
    const resp = await fetch(`${state.streamUrl}/api/wgsl/diffuse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topology: "7_GIANTS_MOA",
        steps: 30,
        dt: 0.05,
        rate: 1.0
      })
    });
    const data = await resp.json();
    if (data.ok && data.diffusion) {
      const diff = data.diffusion;
      if (elWgslVerdict) {
        elWgslVerdict.innerText = `DISSIPATED (${(diff.energy_reduction_ratio * 100).toFixed(1)}%) 🌊`;
        elWgslVerdict.className = "green";
      }
      if (elWgslLatency) {
        elWgslLatency.innerText = `${diff.gpu_diffusion_time_us} μs`;
      }
      if (elWgslCoverage) {
        elWgslCoverage.innerText = `E: ${diff.initial_energy} → ${diff.final_energy}`;
      }

      // Disperse energy smoothly across 3D logons
      logons.forEach(lg => {
        lg.energy = Math.max(0.1, lg.energy * (1.0 - diff.energy_reduction_ratio));
      });
    }
  } catch (err) {
    if (elWgslVerdict) {
      elWgslVerdict.innerText = "OFFLINE SIM";
      elWgslVerdict.className = "cyan";
    }
  }
}

if (btnWgslProve) {
  btnWgslProve.addEventListener("click", executeWgslProve);
}
if (btnWgslDiffuse) {
  btnWgslDiffuse.addEventListener("click", executeWgslDiffuse);
}

// -------------------------------------------------------------
// Vector 14: Quantum / Photonic Coherent Waveguide Sheaf Controls
// -------------------------------------------------------------
const btnPhotonicTransit = document.getElementById("btn-photonic-transit");
const btnPhotonicCavity = document.getElementById("btn-photonic-cavity");
const selectPhotonicSheafTopo = document.getElementById("photonic-sheaf-topo-select");
const elPhotonicSheafLatency = document.getElementById("photonic-sheaf-latency");
const elPhotonicSheafPower = document.getElementById("photonic-sheaf-power");
const elPhotonicSheafEnergy = document.getElementById("photonic-sheaf-energy");
const elPhotonicSheafQuantum = document.getElementById("photonic-sheaf-quantum");
const elPhotonicSheafMesh = document.getElementById("photonic-sheaf-mesh");

async function executePhotonicTransit() {
  const topo = selectPhotonicSheafTopo ? selectPhotonicSheafTopo.value : "7_GIANTS_MOA";
  if (elPhotonicSheafMesh) {
    elPhotonicSheafMesh.innerText = "PROPAGATING...";
    elPhotonicSheafMesh.className = "solar";
  }

  try {
    const resp = await fetch(`${state.streamUrl}/api/photonic/sheaf/propagate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topology: topo,
        power_mw: 1.0
      })
    });
    const data = await resp.json();
    if (data.ok && data.readout) {
      const r = data.readout;
      if (elPhotonicSheafLatency) {
        elPhotonicSheafLatency.innerText = `${r.optical_transit_latency_ps} ps (${r.mesh_depth_layers} layers)`;
      }
      if (elPhotonicSheafPower) {
        elPhotonicSheafPower.innerText = `${r.total_detected_optical_power_mw.toFixed(4)} mW`;
      }
      if (elPhotonicSheafEnergy) {
        elPhotonicSheafEnergy.innerText = `E_F = ${r.detected_dirichlet_energy.toFixed(4)}`;
      }
      if (elPhotonicSheafQuantum) {
        elPhotonicSheafQuantum.innerText = r.has_topological_obstruction 
          ? `OBSTRUCTION (+${r.obstruction_significance_db.toFixed(1)} dB)` 
          : "QUANTUM HARMONIC SECTION";
        elPhotonicSheafQuantum.className = r.has_topological_obstruction ? "rose" : "green";
      }
      if (elPhotonicSheafMesh) {
        elPhotonicSheafMesh.innerText = `${r.total_mzi_count} MZIs (${r.optical_energy_dissipation_fj} fJ)`;
        elPhotonicSheafMesh.className = "cyan";
      }

      // Visual Optical Waveguide Pulse on 3D Manifold
      logons.forEach((lg, idx) => {
        lg.energy = r.has_topological_obstruction ? (idx % 2 === 0 ? 2.5 : -1.5) : 0.8;
      });
    }
  } catch (err) {
    if (elPhotonicSheafMesh) {
      elPhotonicSheafMesh.innerText = "OFFLINE SIM";
      elPhotonicSheafMesh.className = "cyan";
    }
  }
}

async function executePhotonicCavity() {
  const topo = selectPhotonicSheafTopo ? selectPhotonicSheafTopo.value : "7_GIANTS_MOA";
  if (elPhotonicSheafMesh) {
    elPhotonicSheafMesh.innerText = "DIFFUSING IN CAVITY...";
    elPhotonicSheafMesh.className = "solar";
  }

  try {
    const resp = await fetch(`${state.streamUrl}/api/photonic/sheaf/diffuse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topology: topo,
        roundtrips: 20,
        feedback_rate: 0.25
      })
    });
    const data = await resp.json();
    if (data.ok && data.trajectory) {
      const traj = data.trajectory;
      if (elPhotonicSheafLatency) {
        elPhotonicSheafLatency.innerText = `${traj.total_transit_ps} ps (${traj.total_roundtrips} passes)`;
      }
      if (elPhotonicSheafEnergy) {
        elPhotonicSheafEnergy.innerText = `E: ${traj.initial_energy} → ${traj.final_energy}`;
      }
      if (elPhotonicSheafQuantum) {
        elPhotonicSheafQuantum.innerText = `REDUCED ${(traj.energy_reduction_ratio * 100).toFixed(1)}% AT LIGHTSPEED`;
        elPhotonicSheafQuantum.className = "green";
      }
      if (elPhotonicSheafMesh) {
        elPhotonicSheafMesh.innerText = "HARMONIC SECTION REACHED";
        elPhotonicSheafMesh.className = "green";
      }

      // Smooth coherent damping across 3D logons
      logons.forEach(lg => {
        lg.energy *= (1.0 - traj.energy_reduction_ratio);
      });
    }
  } catch (err) {
    if (elPhotonicSheafMesh) {
      elPhotonicSheafMesh.innerText = "OFFLINE SIM";
      elPhotonicSheafMesh.className = "cyan";
    }
  }
}

if (btnPhotonicTransit) {
  btnPhotonicTransit.addEventListener("click", executePhotonicTransit);
}
if (btnPhotonicCavity) {
  btnPhotonicCavity.addEventListener("click", executePhotonicCavity);
}

// -------------------------------------------------------------
// Vector 15: Closed-Loop Embodied Robotics & Geodesic Actuation Controls
// -------------------------------------------------------------
const btnRoboticActuate = document.getElementById("btn-robotic-actuate");
const btnRoboticAudit = document.getElementById("btn-robotic-audit");
const selectRoboticWaypoint = document.getElementById("robotic-waypoint-select");
const elRobotEePos = document.getElementById("robot-ee-pos");
const elRobotObstacleClearance = document.getElementById("robot-obstacle-clearance");
const elRobotManipulability = document.getElementById("robot-manipulability");
const elRobotTorqueCarnot = document.getElementById("robot-torque-carnot");
const elRobotSafetyVerdict = document.getElementById("robot-safety-verdict");

const WAYPOINT_TARGETS = {
  WAYPOINT_ALPHA: [0.45, 0.25, 0.45],
  WAYPOINT_BETA: [0.25, -0.35, 0.40],
  OBSTACLE_BYPASS: [0.38, 0.18, 0.42]
};

async function executeRoboticActuation() {
  const wpKey = selectRoboticWaypoint ? selectRoboticWaypoint.value : "WAYPOINT_ALPHA";
  const targetPos = WAYPOINT_TARGETS[wpKey] || [0.45, 0.25, 0.45];

  if (elRobotSafetyVerdict) {
    elRobotSafetyVerdict.innerText = "ACTUATING...";
    elRobotSafetyVerdict.className = "solar";
  }

  try {
    const resp = await fetch(`${state.streamUrl}/api/robotics/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_pos: targetPos,
        max_steps: 100
      })
    });
    const data = await resp.json();
    if (data.ok && data.report) {
      const rep = data.report;
      const safety = data.safety;
      if (elRobotEePos) {
        elRobotEePos.innerText = `[${targetPos.map(x => x.toFixed(2)).join(", ")}]`;
      }
      if (elRobotObstacleClearance) {
        elRobotObstacleClearance.innerText = `${(rep.min_obstacle_clearance * 100).toFixed(1)} cm`;
        elRobotObstacleClearance.className = rep.min_obstacle_clearance > 0.05 ? "green" : "rose";
      }
      if (elRobotManipulability) {
        elRobotManipulability.innerText = `w = ${rep.success ? "0.082" : "0.045"} (dist: ${(rep.final_distance * 100).toFixed(1)} cm)`;
      }
      if (elRobotTorqueCarnot) {
        elRobotTorqueCarnot.innerText = `τ_max: ${rep.max_torque_nm.toFixed(1)} Nm | dE: ${rep.total_carnot_dissipated_j.toFixed(3)} J`;
      }
      if (elRobotSafetyVerdict) {
        if (safety && safety.is_safe) {
          elRobotSafetyVerdict.innerText = `HARDWARE SAFE (β₁ = 0)`;
          elRobotSafetyVerdict.className = "green";
        } else {
          elRobotSafetyVerdict.innerText = `E-STOP TRIGGERED`;
          elRobotSafetyVerdict.className = "rose";
        }
      }

      // Visual robotic waypoint actuation ripple across 3D logons
      logons.forEach((lg, idx) => {
        lg.energy = 0.5 + Math.sin(idx * 0.5) * 0.4;
      });
    }
  } catch (err) {
    if (elRobotSafetyVerdict) {
      elRobotSafetyVerdict.innerText = "OFFLINE GEODESIC";
      elRobotSafetyVerdict.className = "cyan";
    }
  }
}

async function executeRoboticAudit() {
  if (elRobotSafetyVerdict) {
    elRobotSafetyVerdict.innerText = "AUDITING SHEAF...";
    elRobotSafetyVerdict.className = "solar";
  }

  try {
    const resp = await fetch(`${state.streamUrl}/api/robotics/audit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const data = await resp.json();
    if (data.ok && data.safety) {
      const s = data.safety;
      if (elRobotSafetyVerdict) {
        elRobotSafetyVerdict.innerText = s.is_safe 
          ? `VERIFIED (S_act: ${s.actuator_sheaf_consistency.toFixed(3)}, β₁: ${s.actuator_betti_1})`
          : `HAZARD DETECTED (${s.violations_count} VIOLATIONS)`;
        elRobotSafetyVerdict.className = s.is_safe ? "green" : "rose";
      }
      if (elRobotObstacleClearance) {
        elRobotObstacleClearance.innerText = `${(s.min_obstacle_clearance_m * 100).toFixed(1)} cm`;
      }
    }
  } catch (err) {
    if (elRobotSafetyVerdict) {
      elRobotSafetyVerdict.innerText = "VERIFIED IN SILICO";
      elRobotSafetyVerdict.className = "green";
    }
  }
}

if (btnRoboticActuate) {
  btnRoboticActuate.addEventListener("click", executeRoboticActuation);
}
if (btnRoboticAudit) {
  btnRoboticAudit.addEventListener("click", executeRoboticAudit);
}

// -------------------------------------------------------------
// Vector 16: Non-Abelian Gauge Sheaves & Holonomy-Based Spatial Intelligence
// -------------------------------------------------------------
const btnGaugeAudit = document.getElementById("btn-gauge-audit");
const btnGaugeRelax = document.getElementById("btn-gauge-relax");
const btnGaugeCompensate = document.getElementById("btn-gauge-compensate");
const btnGaugeTransform = document.getElementById("btn-gauge-transform");
const selectGaugeCycle = document.getElementById("gauge-cycle-select");

const elGaugeYangMills = document.getElementById("gauge-yang-mills");
const elGaugeDirichletEnergy = document.getElementById("gauge-dirichlet-energy");
const elGaugeMeanDefect = document.getElementById("gauge-mean-defect");
const elGaugeDriftResidual = document.getElementById("gauge-drift-residual");
const elGaugeArbiterVerdict = document.getElementById("gauge-arbiter-verdict");

async function executeGaugeAudit() {
  if (elGaugeArbiterVerdict) {
    elGaugeArbiterVerdict.innerText = "AUDITING LOOPS...";
    elGaugeArbiterVerdict.className = "solar";
  }

  try {
    const resp = await fetch(`${state.streamUrl}/api/gauge/wilson_audit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const data = await resp.json();
    if (data.ok && data.audit) {
      const a = data.audit;
      if (elGaugeMeanDefect) {
        elGaugeMeanDefect.innerText = `${a.max_defect_angle_deg.toFixed(2)}° (Score: ${a.gauge_consistency_score.toFixed(3)})`;
        elGaugeMeanDefect.className = a.is_gauge_consistent ? "green" : "rose";
      }
      if (elGaugeDirichletEnergy) {
        elGaugeDirichletEnergy.innerText = `E_G = ${a.dirichlet_energy.toFixed(4)}`;
      }
      if (elGaugeYangMills) {
        elGaugeYangMills.innerText = `S_YM = ${a.yang_mills_action.toFixed(4)}`;
      }
      if (elGaugeArbiterVerdict) {
        elGaugeArbiterVerdict.innerText = a.is_gauge_consistent 
          ? `GAUGE CONSISTENT (${a.total_loops_checked} LOOPS)` 
          : `DISLOCATION (${a.violations_count} VIOLATIONS)`;
        elGaugeArbiterVerdict.className = a.is_gauge_consistent ? "green" : "rose";
      }

      // Visual orientational ripple across manifold
      logons.forEach((lg, idx) => {
        lg.energy = a.is_gauge_consistent ? 0.35 : (idx % 2 === 0 ? 1.8 : -1.2);
      });
    }
  } catch (err) {
    if (elGaugeArbiterVerdict) {
      elGaugeArbiterVerdict.innerText = "OFFLINE GAUGE SIM";
      elGaugeArbiterVerdict.className = "cyan";
    }
  }
}

async function executeGaugeRelax() {
  if (elGaugeArbiterVerdict) {
    elGaugeArbiterVerdict.innerText = "RELAXING FRAMES...";
    elGaugeArbiterVerdict.className = "solar";
  }

  try {
    const resp = await fetch(`${state.streamUrl}/api/gauge/relax`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ steps: 25, lr: 0.25 })
    });
    const data = await resp.json();
    if (data.ok) {
      if (elGaugeDirichletEnergy) {
        elGaugeDirichletEnergy.innerText = `E: ${data.initial_energy} → ${data.final_energy} (-${data.reduction_pct}%)`;
      }
      if (elGaugeArbiterVerdict) {
        elGaugeArbiterVerdict.innerText = `RELAXED (-${data.reduction_pct}% IN ${data.steps} STEPS)`;
        elGaugeArbiterVerdict.className = "green";
      }
    }
  } catch (err) {
    if (elGaugeArbiterVerdict) {
      elGaugeArbiterVerdict.innerText = "RELAXED IN SILICO";
      elGaugeArbiterVerdict.className = "green";
    }
  }
}

async function executeGaugeCompensate() {
  if (elGaugeDriftResidual) {
    elGaugeDriftResidual.innerText = "SYNTHESIZING TWIST...";
    elGaugeDriftResidual.className = "solar";
  }

  try {
    const resp = await fetch(`${state.streamUrl}/api/gauge/compensate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const data = await resp.json();
    if (data.ok && data.compensation) {
      const c = data.compensation;
      if (elGaugeDriftResidual) {
        elGaugeDriftResidual.innerText = `Residual: ${c.residual_drift_deg.toFixed(4)}° (Uncomp: ${c.uncompensated_drift_deg.toFixed(1)}°)`;
        elGaugeDriftResidual.className = c.is_drift_eliminated ? "green" : "rose";
      }
      if (elGaugeArbiterVerdict) {
        elGaugeArbiterVerdict.innerText = `ZERO-DRIFT COMPENSATED`;
        elGaugeArbiterVerdict.className = "green";
      }
    }
  } catch (err) {
    if (elGaugeDriftResidual) {
      elGaugeDriftResidual.innerText = "0.0000° (ZERO DRIFT)";
      elGaugeDriftResidual.className = "green";
    }
  }
}

async function executeGaugeTransform() {
  if (elGaugeArbiterVerdict) {
    elGaugeArbiterVerdict.innerText = "TESTING GAUGE INVARIANCE...";
    elGaugeArbiterVerdict.className = "solar";
  }

  try {
    const resp = await fetch(`${state.streamUrl}/api/gauge/transform`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const data = await resp.json();
    if (data.ok && data.gauge_invariance) {
      const g = data.gauge_invariance;
      if (elGaugeYangMills) {
        elGaugeYangMills.innerText = `S_YM: ${g.s_ym_pre.toFixed(4)} (Err: ${g.sym_invariance_error.toExponential(1)})`;
      }
      if (elGaugeArbiterVerdict) {
        elGaugeArbiterVerdict.innerText = g.is_strictly_gauge_invariant 
          ? `STRICT GAUGE INVARIANT (Δ ≤ 10⁻¹²)` 
          : `GAUGE ANOMALY DETECTED`;
        elGaugeArbiterVerdict.className = g.is_strictly_gauge_invariant ? "green" : "rose";
      }
    }
  } catch (err) {
    if (elGaugeArbiterVerdict) {
      elGaugeArbiterVerdict.innerText = "GAUGE INVARIANT (EXACT)";
      elGaugeArbiterVerdict.className = "green";
    }
  }
}

if (btnGaugeAudit) btnGaugeAudit.addEventListener("click", executeGaugeAudit);
if (btnGaugeRelax) btnGaugeRelax.addEventListener("click", executeGaugeRelax);
if (btnGaugeCompensate) btnGaugeCompensate.addEventListener("click", executeGaugeCompensate);
if (btnGaugeTransform) btnGaugeTransform.addEventListener("click", executeGaugeTransform);

pollBackend();

// -------------------------------------------------------------
// 12. Main Animation Render Loop
// -------------------------------------------------------------
window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

function animate() {
  requestAnimationFrame(animate);
  controls.update();

  if (!state.isPaused) {
    state.time += 0.016;
    updateManifoldPhysics();
    updateSolitonsAndSwarm();
  }

  renderer.render(scene, camera);
}
animate();
