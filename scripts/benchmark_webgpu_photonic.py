"""
Executable CLI: Benchmark WebGPU WGSL Compute Shaders & Photonic Substrate Mapping
File: scripts/benchmark_webgpu_photonic.py

Evaluates scaling, throughput, latency, and energy dissipation across:
- Classical Single-Core CPU
- WebGPU WGSL Compute Shaders (100,000+ excitons)
- Photonic Integrated Circuits (Mach-Zehnder Interferometers)
- Neuromorphic Memristive Lattices

Usage:
  python scripts/benchmark_webgpu_photonic.py
"""

from pathlib import Path
import sys
import time
import numpy as np

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from sol.kernel.photonic.webgpu_compiler import WebGPUComputeCompiler
from sol.kernel.photonic.substrate_mapping import (
    PhotonicMZIMesh,
    PhotonicLogicGateMapping,
    NeuromorphicMemristorCrossbar,
    PhysicalSubstrateComparison
)


def main():
    print("=" * 80)
    print("       SOL-SYSTEMS & FRONTIER_OS: VECTOR 4 HARDWARE SUBSTRATE BENCHMARK     ")
    print("       WebGPU WGSL Shaders (100k Excitons) & Photonic MZI Substrates        ")
    print("=" * 80)

    compiler = WebGPUComputeCompiler()

    # 1. Compile & Validate WGSL Shaders
    print("\n[1. WebGPU WGSL Compute Shader Compilation & Verification]")
    shaders = ["riemannian_wave.wgsl", "exciton_swarm.wgsl"]
    for s_name in shaders:
        spec = compiler.load_shader(s_name)
        val = compiler.validate_shader(spec)
        status = "PASSED" if val.is_valid else "FAILED"
        print(f"  Shader: {s_name:<24} | Workgroup: {str(val.workgroup_size):<12} | Status: {status}")
        print(f"    - Positive-Definite Retraction: {val.has_positive_definite_retraction}")
        print(f"    - Symplectic Verlet Stepper:    {val.has_symplectic_integration}")
        print(f"    - Atomic Carnot Dissipation:    {val.has_carnot_atomic_dissipation}")

    # 2. Exciton Swarm Scaling Benchmark
    print("\n[2. Exciton Swarm Scaling Benchmark (Symplectic + Curl Invariant)]")
    scales = [7, 100, 1000, 10000, 50000]
    rng = np.random.RandomState(42)

    for n in scales:
        positions = rng.randn(n, 3).astype(np.float32) * 5.0
        velocities = rng.randn(n, 3).astype(np.float32) * 2.0

        t0 = time.perf_counter()
        pos_out, vel_out, dE = compiler.emulate_swarm_step(
            num_particles=n,
            positions=positions,
            velocities=velocities,
            dt=0.02,
            damping=0.05,
            curl_vorticity=0.75
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        rate = n / (elapsed_ms / 1000.0)
        print(f"  Scale: {n:>6} Excitons | Latency: {elapsed_ms:>8.3f} ms | Throughput: {rate:>12.0f} agents/s | Carnot dE: {dE:.4f} J")

    # 3. Optical Mach-Zehnder Interferometer (PIC) Evaluation
    print("\n[3. Photonic Integrated Circuit (MZI) Logic Gate Benchmark]")
    mzi = PhotonicMZIMesh(arm_length_um=120.0)
    gate_mapper = PhotonicLogicGateMapping(mzi=mzi)

    for gate in ["XOR", "AND", "OR"]:
        print(f"  Evaluating Photonic {gate} Gate (1550nm coherent lightwave):")
        for a, b in [(0.0, 0.0), (0.0, 1.0), (1.0, 0.0), (1.0, 1.0)]:
            res = gate_mapper.evaluate_photonic_gate(gate, a, b)
            print(f"    Inputs: ({int(a)}, {int(b)}) -> Readout Bit: {res.binary_readout} | Port 0: {res.output_port_0:.4f} mW | Latency: {res.propagation_latency_ps:.2f} ps | Energy: {res.energy_per_op_femtojoules:.2f} fJ")

    # 4. Neuromorphic Memristor Crossbar Metric Mapping
    print("\n[4. Neuromorphic Memristive Lattice Metric Tensor Evaluation]")
    crossbar = NeuromorphicMemristorCrossbar(dim=4, g_base_microsiemens=50.0)
    S = rng.randn(4, 4) * 0.1
    S = 0.5 * (S + S.T)
    conductances = crossbar.program_metric(S)
    V_in = np.array([1.0, 0.5, 0.0, 0.8])
    currents, energy_pj = crossbar.analog_inner_product(conductances, V_in)
    print(f"  Programmed 4x4 Metric Tensor Conductance Matrix (Positive Definite G >> 0):")
    for r in range(4):
        print(f"    [{', '.join(f'{conductances[r, c]:>6.2f} uS' for c in range(4))}]")
    print(f"  Analog Inner Product Vector: [{', '.join(f'{c:>6.2f} uA' for c in currents)}]")
    print(f"  Energy Consumption: {energy_pj:.3f} picojoules (O(1) physical clock execution)\n")

    # 5. Multi-Substrate Comparison Table
    print("[5. Substrate Comparison & Thermodynamic Efficiency]")
    table = PhysicalSubstrateComparison.get_comparison_table()
    header = (
        f"| {'Substrate Architecture':<34} | {'Step Latency':<12} | {'Energy / Op':<14} | {'Max Capacity':<14} | {'Efficiency / Landauer':<20} |\n"
        f"| :--- | :---: | :---: | :---: | :---: |"
    )
    print(header)
    for s in table:
        lat_str = f"{s.latency_per_step_ns * 1e3:.1f} ps" if s.latency_per_step_ns < 1.0 else f"{s.latency_per_step_ns:.1f} ns"
        en_str = f"{s.energy_per_op_joules * 1e15:.1f} fJ" if s.energy_per_op_joules < 1e-12 else (f"{s.energy_per_op_joules * 1e12:.1f} pJ" if s.energy_per_op_joules < 1e-9 else f"{s.energy_per_op_joules * 1e9:.1f} nJ")
        cap_str = f"{s.max_exciton_capacity:>9,}"
        eff_str = f"{s.thermodynamic_efficiency:.2e}"
        print(f"| **{s.substrate_type}** | {lat_str} | {en_str} | {cap_str} | {eff_str} |")
    print()


if __name__ == "__main__":
    main()
