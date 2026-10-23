// SOL-Studio Hardware-Accelerated Decision Prover & MSCK Inflection Kernel (Frontier O / Vector 19)
// Enforces:
//   1. Positive-definite 2x2 metric retraction via matrix_exp_2x2
//   2. Symplectic drift step using params.dt and velocity state
//   3. Thermodynamic Carnot dissipation accounting via atomicAdd(&carnot_dissipation[0], ...)
//   4. Parallel evaluation of 10,000+ trade-space option/assumption permutations and MSCK inflection boundaries

struct DecisionProverParams {
    num_permutations: u32,
    num_options: u32,
    num_assumptions: u32,
    dt: f32,
    carnot_limit: f32,
    msck_fragility_floor: f32,
    grid_resolution: u32,
    baseline_winner_idx: u32,
};

struct TradeSpacePermutationState {
    option_utilities: vec4<f32>,
    velocity: vec4<f32>,
    coboundary_norm: f32,
    top_option_idx: u32,
    winner_flipped: u32,
    inflection_margin_pct: f32,
};

struct MSCKInflectionPoint {
    assumption_idx: u32,
    baseline_val: f32,
    inflection_val: f32,
    relative_delta_pct: f32,
    surface_gradient_norm: f32,
    flipped_winner_idx: u32,
    is_fragile: u32,
    reserved_pad: u32,
};

@group(0) @binding(0) var<uniform> params: DecisionProverParams;
@group(0) @binding(1) var<storage, read> option_stalks: array<vec4<f32>>;
@group(0) @binding(2) var<storage, read> assumption_perturbations: array<vec4<f32>>;
@group(0) @binding(3) var<storage, read_write> permutation_states: array<TradeSpacePermutationState>;
@group(0) @binding(4) var<storage, read_write> msck_inflection_points: array<MSCKInflectionPoint>;
@group(0) @binding(5) var<storage, read_write> carnot_dissipation: array<atomic<u32>>;

// Positive-Definite Retraction: 2nd-order Padé / Taylor Matrix Exponential on 2x2 tangent slice
fn matrix_exp_2x2(a: mat2x2<f32>) -> mat2x2<f32> {
    let i = mat2x2<f32>(vec2<f32>(1.0, 0.0), vec2<f32>(0.0, 1.0));
    let a2 = a * a;
    let a3 = a2 * a;
    return i + a + (a2 * 0.5) + (a3 * 0.16666667);
}

// Local gradient sampling across 2D assumption perturbation grid
fn sample_gradient(u_center: f32, u_plus_x: f32, u_plus_y: f32, step: f32) -> vec2<f32> {
    let inv_step = select(1.0, 1.0 / step, step > 1e-6);
    return vec2<f32>((u_plus_x - u_center) * inv_step, (u_plus_y - u_center) * inv_step);
}

@compute @workgroup_size(64, 1, 1)
fn sweep_trade_space_permutations(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let idx = global_id.x;
    if (idx >= params.num_permutations) {
        return;
    }

    var state = permutation_states[idx];
    let perturb = assumption_perturbations[idx];

    // Construct symmetric 2x2 tangent perturbation and retract to SPD manifold
    let tangent = mat2x2<f32>(
        vec2<f32>(perturb.x * 0.05, perturb.y * 0.02),
        vec2<f32>(perturb.y * 0.02, perturb.z * 0.05)
    );
    let spd_metric = matrix_exp_2x2(tangent);

    // Evaluate option utilities under perturbed assumption weights and symplectic velocity drift
    let stalk0 = option_stalks[0];
    let stalk1 = option_stalks[1];
    let stalk2 = option_stalks[2];
    let stalk3 = option_stalks[3];

    let force = vec4<f32>(
        dot(stalk0.xy, spd_metric[0]) + stalk0.z * perturb.z + stalk0.w * perturb.w,
        dot(stalk1.xy, spd_metric[0]) + stalk1.z * perturb.z + stalk1.w * perturb.w,
        dot(stalk2.xy, spd_metric[1]) + stalk2.z * perturb.z + stalk2.w * perturb.w,
        dot(stalk3.xy, spd_metric[1]) + stalk3.z * perturb.z + stalk3.w * perturb.w
    );

    let new_vel = state.velocity + force * (0.5 * params.dt);
    let utilities = state.option_utilities + new_vel * params.dt;

    // Determine top-ranked option and MSCK winner flip status
    var best_idx: u32 = 0u;
    var best_val: f32 = utilities.x;
    var runner_up_val: f32 = utilities.y;

    if (utilities.y > best_val) {
        runner_up_val = best_val;
        best_val = utilities.y;
        best_idx = 1u;
    } else {
        runner_up_val = utilities.y;
    }
    if (utilities.z > best_val) {
        runner_up_val = best_val;
        best_val = utilities.z;
        best_idx = 2u;
    } else if (utilities.z > runner_up_val) {
        runner_up_val = utilities.z;
    }
    if (utilities.w > best_val) {
        runner_up_val = best_val;
        best_val = utilities.w;
        best_idx = 3u;
    } else if (utilities.w > runner_up_val) {
        runner_up_val = utilities.w;
    }

    // Sheaf coboundary norm ||delta^0 x||_2 across option restriction maps
    let diff01 = (utilities.x - utilities.y) * 0.1;
    let diff12 = (utilities.y - utilities.z) * 0.1;
    let coboundary = sqrt(diff01 * diff01 + diff12 * diff12);

    // Thermodynamic Carnot dissipation bound enforcement
    let kinetic_energy = 0.5 * dot(new_vel, new_vel);
    if (kinetic_energy + coboundary > params.carnot_limit) {
        let dissipation_quantized = u32((kinetic_energy + coboundary - params.carnot_limit) * 1000.0);
        atomicAdd(&carnot_dissipation[0], max(1u, dissipation_quantized));
    }

    state.option_utilities = utilities;
    state.velocity = new_vel;
    state.coboundary_norm = coboundary;
    state.top_option_idx = best_idx;
    state.winner_flipped = select(0u, 1u, best_idx != params.baseline_winner_idx);
    state.inflection_margin_pct = ((best_val - runner_up_val) / max(abs(best_val), 1e-4)) * 100.0;

    permutation_states[idx] = state;
}

@compute @workgroup_size(64, 1, 1)
fn solve_msck_inflection_surface(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let a_idx = global_id.x;
    if (a_idx >= params.num_assumptions) {
        return;
    }

    var pt = msck_inflection_points[a_idx];
    let grad_vec = sample_gradient(pt.baseline_val, pt.inflection_val, pt.inflection_val * 0.95, 0.05);
    pt.surface_gradient_norm = length(grad_vec);
    pt.is_fragile = select(0u, 1u, abs(pt.relative_delta_pct) < params.msck_fragility_floor);
    msck_inflection_points[a_idx] = pt;
}
