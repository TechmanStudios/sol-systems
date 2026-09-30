// ==============================================================================
// WebGPU Compute Shader: 100,000+ Exciton Swarm on Riemannian Manifold
// File: sol-studio/shaders/exciton_swarm.wgsl
//
// Simulates 100,000+ autonomous Exciton agents with:
// 1. Christoffel geodesic acceleration along curved Riemannian spacetime.
// 2. 7 Giants Differential Operators:
//    - Statistician: Equation of state crowding pressure
//    - Optimizer: Riemannian potential descent
//    - N-Body: Jeans Mass gravitational collapse
//    - Graph Navigator: Symplectic magnetic curl (zero-work circulation)
//    - Linear Algebraist: PCA dispersion compression
//    - Aligner: Kuramoto velocity & phase synchronization
//    - Integrator: Jacobian volume preservation & AdS boundary confinement
// 3. Thermodynamic Carnot memory dissipation into atomic accumulator.
// ==============================================================================

struct SwarmUniforms {
    total_excitons: u32,
    grid_width: u32,
    grid_height: u32,
    grid_spacing: f32,
    dt: f32,
    time: f32,
    damping: f32,
    curl_vorticity: f32,
    horizon_radius: f32,
    num_clusters: u32,
};

struct SwarmClusterTarget {
    pos: vec4<f32>,     // x, y, z, radius
    meta: vec4<f32>,    // capacity, current_count, attraction_k, padding
};

struct ExcitonParticle {
    pos: vec4<f32>,     // x, y, z, phase
    vel: vec4<f32>,     // vx, vy, vz, mass
    color: vec4<f32>,   // r, g, b, alpha
    extra: vec4<f32>,   // charge, role_id (0..6), target_cluster, status (0=active, 1=converged)
};

@group(0) @binding(0) var<uniform> uniforms: SwarmUniforms;
@group(0) @binding(1) var<storage, read_write> excitons: array<ExcitonParticle>;
@group(0) @binding(2) var<storage, read> height_map: array<f32>;
@group(0) @binding(3) var<storage, read> clusters: array<SwarmClusterTarget>;
@group(0) @binding(4) var<storage, read_write> carnot_dissipation: array<atomic<u32>>;

// Bilinear interpolation of continuous wave height h(x, z)
fn sample_height(world_x: f32, world_z: f32) -> f32 {
    let half_w = f32(uniforms.grid_width) * uniforms.grid_spacing * 0.5;
    let half_h = f32(uniforms.grid_height) * uniforms.grid_spacing * 0.5;

    let gx = (world_x + half_w) / uniforms.grid_spacing;
    let gz = (world_z + half_h) / uniforms.grid_spacing;

    let x0 = clamp(u32(floor(gx)), 0u, uniforms.grid_width - 2u);
    let z0 = clamp(u32(floor(gz)), 0u, uniforms.grid_height - 2u);
    let x1 = x0 + 1u;
    let z1 = z0 + 1u;

    let fx = fract(gx);
    let fz = fract(gz);

    let h00 = height_map[z0 * uniforms.grid_width + x0];
    let h10 = height_map[z0 * uniforms.grid_width + x1];
    let h01 = height_map[z1 * uniforms.grid_width + x0];
    let h11 = height_map[z1 * uniforms.grid_width + x1];

    let h0 = mix(h00, h10, fx);
    let h1 = mix(h01, h11, fx);
    return mix(h0, h1, fz);
}

// Compute surface gradient ∇h = (∂h/∂x, ∂h/∂z) for Christoffel geodesic curvature
fn sample_gradient(world_x: f32, world_z: f32) -> vec2<f32> {
    let eps = uniforms.grid_spacing * 0.5;
    let h_right = sample_height(world_x + eps, world_z);
    let h_left  = sample_height(world_x - eps, world_z);
    let h_up    = sample_height(world_x, world_z + eps);
    let h_down  = sample_height(world_x, world_z - eps);

    let dh_dx = (h_right - h_left) / (2.0 * eps);
    let dh_dz = (h_up - h_down) / (2.0 * eps);
    return vec2<f32>(dh_dx, dh_dz);
}

@compute @workgroup_size(64, 1, 1)
fn main(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let idx = global_id.x;
    if (idx >= uniforms.total_excitons) {
        return;
    }

    var agent = excitons[idx];

    var pos = agent.pos.xyz;
    var phase = agent.pos.w;
    var vel = agent.vel.xyz;
    let mass = max(agent.vel.w, 0.1);
    let charge = agent.extra.x;
    let role_id = u32(agent.extra.y);
    let cluster_idx = u32(agent.extra.z);

    // 1. Sample Riemannian Manifold Surface & Gradient
    let grad_h = sample_gradient(pos.x, pos.z);
    let surf_y = sample_height(pos.x, pos.z);

    // 2. Christoffel Geodesic Acceleration on Monge Patch (z = h(x, y))
    // The induced metric is g_ij = δ_ij + ∂_i h ∂_j h.
    // Geodesic equation accelerates down curvature: a_geo = - (∇h / (1 + ||∇h||²)) * (g_ij v^i v^j)
    let grad_norm_sq = dot(grad_h, grad_h);
    let v_metric_sq = (vel.x * vel.x + vel.z * vel.z) + (grad_h.x * vel.x + grad_h.y * vel.z) * (grad_h.x * vel.x + grad_h.y * vel.z);
    let geo_factor = v_metric_sq / (1.0 + grad_norm_sq + 1e-4);
    var a_total = vec3<f32>(-grad_h.x * geo_factor * 0.4, 0.0, -grad_h.y * geo_factor * 0.4);

    // 3. 7 Giants Specialized Differential Operators
    // Giant 1: The Statistician (role 0) -> Crowding pressure repulsion
    if (role_id == 0u) {
        let r_center = length(pos.xz);
        let p_factor = 2.0 / (1.0 + r_center * 0.1);
        a_total += vec3<f32>(pos.x * p_factor * 0.08, 0.0, pos.z * p_factor * 0.08);
    }
    // Giant 2: The Optimizer (role 1) -> Geodesic potential steepest descent
    else if (role_id == 1u) {
        a_total += vec3<f32>(-grad_h.x * 2.5, 0.0, -grad_h.y * 2.5);
    }
    // Giant 3: The N-Body Solver (role 2) -> Gravitational Jeans collapse
    else if (role_id == 2u) {
        if (cluster_idx < uniforms.num_clusters) {
            let cl = clusters[cluster_idx];
            let delta = cl.pos.xyz - pos;
            let dist = max(length(delta), 0.5);
            let f_grav = (cl.meta.z * mass) / (dist * dist * dist);
            a_total += delta * f_grav * 1.5;
        }
    }
    // Giant 4: The Graph Navigator (role 3) -> Symplectic magnetic curl (Ω · v)
    // Invariant: v · a_curl ≡ 0 (conserves kinetic energy, zero mechanical work!)
    else if (role_id == 3u) {
        let omega = uniforms.curl_vorticity;
        let curl_ax = -omega * vel.z;
        let curl_az =  omega * vel.x;
        a_total += vec3<f32>(curl_ax, 0.0, curl_az);
    }
    // Giant 5: The Linear Algebraist (role 4) -> PCA compression
    else if (role_id == 4u) {
        // Compress along minor dispersion axis (z)
        a_total.z -= vel.z * 0.4;
    }
    // Giant 6: The Aligner (role 5) -> Kuramoto phase consensus
    else if (role_id == 5u) {
        // Kuramoto coupling: synchronizes phase w.r.t orbital frequency
        phase = phase + 1.2 * uniforms.dt;
        let target_vx = -pos.z * 0.2;
        let target_vz =  pos.x * 0.2;
        a_total += vec3<f32>((target_vx - vel.x) * 1.2, 0.0, (target_vz - vel.z) * 1.2);
    }
    // Giant 7: The Integrator (role 6) -> Conformal AdS horizon boundary barrier
    else if (role_id == 6u) {
        let r = length(pos.xz);
        if (r > uniforms.horizon_radius * 0.7) {
            let barrier_k = pow((r - uniforms.horizon_radius * 0.7), 2.0) * 0.8;
            a_total += vec3<f32>(-pos.x / r * barrier_k, 0.0, -pos.z / r * barrier_k);
        }
    }

    // Cluster guidance for all agents assigned to a target cluster
    if (cluster_idx < uniforms.num_clusters) {
        let cl = clusters[cluster_idx];
        let to_cluster = cl.pos.xyz - pos;
        let dist_to_target = length(to_cluster);
        if (dist_to_target > cl.pos.w) {
            let k_pull = cl.meta.z;
            a_total += normalize(to_cluster) * k_pull;
        } else {
            // Arrived at cluster basin: damp and register converged
            a_total -= vel * 2.0;
            agent.extra.w = 1.0; // Converged
        }
    }

    // 4. Conformal Boundary Confinement (Infinite Void Escape Prevention)
    let current_radius = length(pos.xz);
    if (current_radius > uniforms.horizon_radius) {
        let normal = -normalize(pos.xz);
        vel.x = normal.x * abs(vel.x) * 0.8;
        vel.z = normal.y * abs(vel.z) * 0.8;
        pos.x = -normal.x * uniforms.horizon_radius * 0.99;
        pos.z = -normal.y * uniforms.horizon_radius * 0.99;
    }

    // 5. Semi-Implicit Symplectic Verlet Integration
    let damping_factor = max(1.0 - uniforms.damping * uniforms.dt, 0.0);
    vel = (vel + a_total * uniforms.dt) * damping_factor;
    pos = pos + vel * uniforms.dt;
    pos.y = surf_y + 0.35; // Sit on manifold surface with hover offset

    // Update phase
    phase = (phase + length(vel) * uniforms.dt) % 6.2831853;

    // 6. Write Back Particle State
    agent.pos = vec4<f32>(pos, phase);
    agent.vel = vec4<f32>(vel, mass);
    excitons[idx] = agent;

    // 7. Accumulate Carnot Kinetic Dissipation
    let v_sq = dot(vel, vel);
    let dE = 2.0 * uniforms.damping * (0.5 * mass * v_sq) * uniforms.dt;
    let dE_int = u32(max(0.0, dE * 100000.0));
    if (dE_int > 0u) {
        atomicAdd(&carnot_dissipation[0], dE_int);
    }
}
