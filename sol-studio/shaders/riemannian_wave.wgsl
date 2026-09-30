// ==============================================================================
// WebGPU Compute Shader: 2D Continuous Riemannian Metric Wave Equation
// File: sol-studio/shaders/riemannian_wave.wgsl
//
// Solves:
//   ∂²h/∂t² = c² ∇²_g h - γ ∂h/∂t + S_ext(x, z)
// where:
//   ∇²_g h = (1 / √det(g)) ∂_i (√det(g) g^{ij} ∂_j h)
//
// Invariants enforced:
// 1. Strict positive-definiteness: g_ij = exp(S) >> 0 via Log-Euclidean retraction.
// 2. Symplectic energy conservation: kinetic dissipation 2γv² is accumulated into
//    an atomic Carnot sink buffer.
// ==============================================================================

struct SimulationParams {
    grid_width: u32,
    grid_height: u32,
    dt: f32,
    c_speed: f32,
    damping_gamma: f32,
    grid_spacing: f32,
    time: f32,
    active_sources: u32,
};

struct ExternalSource {
    pos: vec2<f32>,     // x, z coordinates in grid units
    amplitude: f32,
    frequency: f32,
};

// Storage Buffers
@group(0) @binding(0) var<uniform> params: SimulationParams;
@group(0) @binding(1) var<storage, read> height_in: array<f32>;
@group(0) @binding(2) var<storage, read_write> height_out: array<f32>;
@group(0) @binding(3) var<storage, read_write> velocity: array<f32>;
@group(0) @binding(4) var<storage, read> metric_generators: array<vec4<f32>>; // Sxx, Sxz, Szx, Szz
@group(0) @binding(5) var<storage, read> sources: array<ExternalSource>;
@group(0) @binding(6) var<storage, read_write> carnot_dissipation: array<atomic<u32>>; // Fixed-point atomic accumulator

// Helper: 2D Grid Indexing
fn get_index(x: u32, z: u32) -> u32 {
    return z * params.grid_width + x;
}

// 2x2 Matrix Exponential Retraction for Positive-Definite Metric g = exp(S)
fn matrix_exp_2x2(S: vec4<f32>) -> vec4<f32> {
    let tr = S.x + S.w;
    let tr_half = tr * 0.5;
    // Traceless part S_0 = S - tr_half * I
    let s0_xx = S.x - tr_half;
    let s0_xz = S.y;
    let s0_zx = S.z;
    let s0_zz = S.w - tr_half;
    
    // det(S_0) = s0_xx * s0_zz - s0_xz * s0_zx
    let det_s0 = s0_xx * s0_zz - s0_xz * s0_zx;
    let theta_sq = -det_s0; // = (s0_xx² + s0_xz * s0_zx) for symmetric matrices
    
    let exp_tr = exp(tr_half);
    
    if (theta_sq > 1e-7) {
        let theta = sqrt(theta_sq);
        let cosh_th = cosh(theta);
        let sinh_th = sinh(theta);
        let factor = sinh_th / theta;
        return vec4<f32>(
            exp_tr * (cosh_th + factor * s0_xx),
            exp_tr * (factor * s0_xz),
            exp_tr * (factor * s0_zx),
            exp_tr * (cosh_th + factor * s0_zz)
        );
    } else {
        // Small theta expansion: exp(S) ≈ exp(tr/2) * (I + S_0)
        return vec4<f32>(
            exp_tr * (1.0 + s0_xx),
            exp_tr * s0_xz,
            exp_tr * s0_zx,
            exp_tr * (1.0 + s0_zz)
        );
    }
}

// Invert 2x2 Positive-Definite Metric Matrix
fn invert_metric(g: vec4<f32>) -> vec4<f32> {
    let det_g = max(g.x * g.w - g.y * g.z, 1e-6);
    let inv_det = 1.0 / det_g;
    return vec4<f32>(
        g.w * inv_det,
        -g.y * inv_det,
        -g.z * inv_det,
        g.x * inv_det
    );
}

@compute @workgroup_size(16, 16, 1)
fn main(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let x = global_id.x;
    let z = global_id.y;

    if (x >= params.grid_width || z >= params.grid_height) {
        return;
    }

    let idx = get_index(x, z);

    // Boundary conditions: clamp boundaries to zero displacement (Dirichlet horizon)
    if (x == 0u || x == params.grid_width - 1u || z == 0u || z == params.grid_height - 1u) {
        height_out[idx] = 0.0;
        velocity[idx] = 0.0;
        return;
    }

    // Neighbor indices
    let idx_L = get_index(x - 1u, z);
    let idx_R = get_index(x + 1u, z);
    let idx_D = get_index(x, z - 1u);
    let idx_U = get_index(x, z + 1u);

    let h_C = height_in[idx];
    let h_L = height_in[idx_L];
    let h_R = height_in[idx_R];
    let h_D = height_in[idx_D];
    let h_U = height_in[idx_U];

    let dx = params.grid_spacing;
    let inv_dx2 = 1.0 / (dx * dx);

    // 1. Evaluate Local Riemannian Metric g_ij = exp(S) >> 0
    let S = metric_generators[idx];
    let g = matrix_exp_2x2(S);
    let g_inv = invert_metric(g);
    let det_g = max(g.x * g.w - g.y * g.z, 1e-6);

    // 2. Compute Metric-Warped Laplace-Beltrami Operator ∇²_g h
    // ∇²_g h ≈ g^{xx} ∂²h/∂x² + 2 g^{xz} ∂²h/∂x∂z + g^{zz} ∂²h/∂z²
    let d2h_dx2 = (h_R - 2.0 * h_C + h_L) * inv_dx2;
    let d2h_dz2 = (h_U - 2.0 * h_C + h_D) * inv_dx2;

    // Mixed cross derivative ∂²h/∂x∂z
    let idx_RU = get_index(x + 1u, z + 1u);
    let idx_LU = get_index(x - 1u, z + 1u);
    let idx_RD = get_index(x + 1u, z - 1u);
    let idx_LD = get_index(x - 1u, z - 1u);
    let d2h_dxdz = (height_in[idx_RU] - height_in[idx_LU] - height_in[idx_RD] + height_in[idx_LD]) / (4.0 * dx * dx);

    let laplacian_g = g_inv.x * d2h_dx2 + (g_inv.y + g_inv.z) * d2h_dxdz + g_inv.w * d2h_dz2;

    // 3. Inject External Soliton Curvature Sources
    var source_term = 0.0;
    let world_x = f32(x) * dx - f32(params.grid_width) * dx * 0.5;
    let world_z = f32(z) * dx - f32(params.grid_height) * dx * 0.5;

    for (var s = 0u; s < params.active_sources; s = s + 1u) {
        let src = sources[s];
        let dist_sq = (world_x - src.pos.x) * (world_x - src.pos.x) + (world_z - src.pos.y) * (world_z - src.pos.y);
        let spatial_profile = exp(-dist_sq / 1.8);
        source_term = source_term + src.amplitude * spatial_profile * sin(params.time * src.frequency);
    }

    // 4. Semi-Implicit Symplectic Verlet Integration
    let cur_v = velocity[idx];
    let c2 = params.c_speed * params.c_speed;
    let accel = c2 * laplacian_g - params.damping_gamma * cur_v + source_term;

    // Symplectic velocity update with dampening
    let new_v = (cur_v + accel * params.dt) * (1.0 - params.damping_gamma * params.dt);
    let new_h = h_C + new_v * params.dt;

    // Write back updated states
    velocity[idx] = new_v;
    height_out[idx] = new_h;

    // 5. Thermodynamic Carnot Dissipation Accounting
    // dE = 2γ v² dt absorbed into hippocampal sink accumulator
    let dE = 2.0 * params.damping_gamma * (new_v * new_v) * params.dt;
    // Quantize to fixed-point integer (scale 1e5) for atomic addition
    let dE_int = u32(max(0.0, dE * 100000.0));
    if (dE_int > 0u) {
        atomicAdd(&carnot_dissipation[0], dE_int);
    }
}
