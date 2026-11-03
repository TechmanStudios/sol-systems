# SOL Companion Session #06: `venue5_track_b_peephole_and_quench`

- **Recorded At (UTC):** `2026-11-02T17:50:10Z`
- **Model:** `gemini-4-argon` (`thinking_level="high"`)
- **Wall-Clock Duration:** `93.47s`
- **Interaction Chain:** `["v1_Chc5c3pvYXR5WEhMNktpTE1QazVtZi1RaxIXOXN6b2F0eVhITDZLaUxNUGs1bWYtUWs", "v1_Chc5c3pvYXR5WEhMNktpTE1QazVtZi1RaxIXQU0zb2FzMmJDN0xCeGRJUC1xNzBpQWs", "v1_Chc5c3pvYXR5WEhMNktpTE1QazVtZi1RaxIXRmMzb2FzZjBPTVBWaUxNUHJaUFY4QWc"]`
- **Token Telemetry:** `input=17846 | thought=3136 | output=4319 | cached=0`
- **Sacred Core Graph SHA-256 (`default_graph.json`):** `d0a80462d2b9389160502b097aca1932bb014941adf6e4b77799997283e4a1bc` (`immutable=True`)
- **Governance Invariants:** `allow_production_execution=False`, `authorized_claimed=False`

## 1. Challenge Prompt

```text
Execute Venue 5 Track B Verification & Discovery: Compiler Peephole Optimization, Scratch-Alias-Aware `NUDGE`/`ASSERT_MASS`, and Pure-Wave Control/Reset Quench.

You must execute this experiment across TWO sequential tool-calling turns (do NOT call both in parallel in Turn 1):

1. **Turn 1 (Scratch-Alias `ASSERT_MASS` Pushback Trap):** Call `sol_compile_lumina_agent_and_claim` with:
   - `basin_name`: `"Basin_A_SUM"`
   - `pure_wave`: `True`
   - `damping`: `0.05`
   - `flow_code`: `"while self.in_a:\n    self.nudge(self.in_b, 15.0)\n    self.nudge(self.sum_out, 15.0)\n    self.nudge(self.carry_out, 15.0)\n    self.settle(25)\n    self.assert_mass(self.in_a, 25.0)\n    self.assert_mass(self.in_b, 25.0)\n    self.in_a = self.in_a ^ self.in_b\n    self.sum_out = self.in_a\n    self.carry_out = self.carry_out | (self.in_a & self.in_b)"`
   Stop and wait for the tool output so you can inspect the resulting `QUARANTINE` telemetry (`allocated_scratch_basins: {"in_a": "Basin_Scratch_0"}`, scratch-alias lowering `ASSERT_MASS('Basin_Scratch_0', 25.0)`, and mass drain failure on `Basin_Scratch_0` / `Basin_In_A`).

2. **Turn 2 (Autonomous Scratch-Alias `NUDGE` Repair & Peephole/Quench Verification):** After inspecting Turn 1's `QUARANTINE` telemetry, autonomously repair `flow_code` by inserting `self.nudge(self.in_a, 15.0)` before `self.settle(25)` (while keeping `self.nudge(self.in_b, 15.0)`, `self.nudge(self.sum_out, 15.0)`, `self.nudge(self.carry_out, 15.0)`, `self.settle(25)`, `self.assert_mass(self.in_a, 25.0)`, `self.assert_mass(self.in_b, 25.0)`, `self.in_a = self.in_a ^ self.in_b`, `self.sum_out = self.in_a`, and `self.carry_out = self.carry_out | (self.in_a & self.in_b)`). Submit the repaired `flow_code` to `sol_compile_lumina_agent_and_claim` (`basin_name="Basin_A_SUM"`, `pure_wave=True`, `damping=0.05`) and verify that it achieves `policy_status == "ELIGIBLE"`, `static_mass_verified == True`, `physical_rk4_verified == True` (`4/4` truth-table cases), `python_boolean_shortcuts_used == 0`, and `pure_wave_quench_ops > 0`.

3. **Turn 3 (Quantitative Track B Comparison vs Session #05 & Track C Synthesis):** Using the exact telemetry from Turn 1 and Turn 2:
   - Quote the exact `static_verification_error`, `counter_demands`, and `instructions` from Turn 1, noting how `self.assert_mass(self.in_a, 25.0)` lowered to `ASSERT_MASS('Basin_Scratch_0', 25.0)`.
   - Compare Turn 2 (`ELIGIBLE`) against Session #05's unoptimized baseline (`instruction_count=37`, `CLEAR` count `10/37 = 27.03%`, `STORE('A', 'Basin_Scratch_0')` count `3`, `STORE('D', 'Basin_Carry_Out')` count `2`, and the 5-op `COPY`/`CMOVE` scalar assignment shuffle): report the exact new `instruction_count`, `CLEAR` count and percentage, `STORE` counts to `Basin_Scratch_0` and `Basin_Carry_Out`, elimination of `COPY`/`CMOVE`, `pure_wave_quench_ops`, and `min_charge_margin_vs_tau`.
   - Formulate concrete physical parameter and threshold co-optimization priorities for Track C (Riemannian Parameter & Threshold Co-Optimization).
```

## 2. Live Model Thought Summaries

### Thought Step 1
**Executing the First Tool Call**

Okay, I understand. The user is laying out a specific, two-turn interaction protocol for me. My immediate task, in this *first* turn, is to adhere *precisely* to the instructions. No deviation. I must now call the `sol_compile_lumina_agent_and_claim` tool. The arguments are fixed and, given the user is an expert, I'm sure there's a good reason for the specific values: Basin name is `"Basin_A_SUM"`, `pure_wave` is `True`, `damping` is `0.05`, and crucially, the `flow_code` is critical: `"while self.in_a:\n    self.nudge(self.in_b, 15.0)\n    self.nudge(self.sum_out, 15.0)\n    self.nudge(self.carry_out, 15.0)\n    self.settle(25)\n    self.assert_mass(self.in_a, 25.0)\n    self.assert_mass(self.in_b, 25.0)\n    self.in_a = self.in_a ^ self.in_b\n    self.sum_out = self.in_a\n    self.carry_out = self.carry_out | (self.in_a & self.in_b)"`. I will *only* call the tool with *these* parameters. I will now invoke `sol_compile_lumina_agent_and_claim` and patiently wait for the result before proceeding to the second turn.

### Thought Step 2
**Analyzing and Addressing a Flow Control Static Verification Failure**

Okay, so I've been looking at the telemetry from Turn 1 regarding the `QUARANTINE` phase. It seems I've allocated a scratch basin, `Basin_Scratch_0`, and I've got a mass assertion expecting 25.0 units in the input basin, `Basin_Scratch_0`. I've noted the assertion at index 11 was lowered. Crucially, I've hit a static verification error: specifically, the `SETTLE 25` instruction at index 10 is draining mass from `Basin_In_A`, across a loop back-edge, to a value of 13.75, which is less than the expected 14.0. The error suggests that I should either place a `self.nudge(<basin>, >=15.0)` instruction *before* `self.settle` or bound `self.settle(steps <= 20)` with pre-settle nudges to resolve the issue.

Now, let's fix this in Turn 2. I'll autonomously repair the `flow_code` by introducing a `self.nudge(self.in_a, 15.0)` *before* the existing `self.settle(25)` instruction. I'm going to keep all the other instructions in place: `self.nudge(self.in_b, 15.0)`, `self.nudge(self.sum_out, 15.0)`, `self.nudge(self.carry_out, 15.0)`, `self.settle(25)`, `self.assert_mass(self.in_a, 25.0)`, `self.assert_mass(self.in_b, 25.0)`, `self.in_a = self.in_a ^ self.in_b`, `self.sum_out = self.in_a`, and `self.carry_out = self.carry_out | (self.in_a & self.in_b)`. This should restore the flow to the desired mass. Finally, I'll call `sol_compile_lumina_agent_and_claim` with this repaired code.

### Thought Step 3
**Turn 3 Synthesis: A Deep Dive into Optimization and Verification**

Okay, let's break this down. My primary goal here is to craft a rigorous Turn 3 synthesis, building upon the meticulous analysis of Turns 1 and 2. I need to be exact, so let's start with a recall of the crucial telemetry.

From Turn 1, I see the initial "QUARANTINE" policy status, indicating a static verification failure. The error message is crystal clear: *"Static verification failure: instruction 'SETTLE 25' at index 10 drains Basin Basin_In_A mass across CFG execution/loop back-edge to 13.75 (< 14.0). [active_loop_basins=Basin_Carry_Out, Basin_In_A, Basin_In_B, Basin_Sum_Out; depleted=Basin_In_A=13.75, Basin_Scratch_0=13.75; place self.nudge(<basin>, >=15.0) BEFORE self.settle or bound self.settle(steps <= 20) with pre-settle nudges]"* This translates directly to the need for a compensatory nudge, before the settle, as per the counter demands: `["Inject compensatory self.nudge('<basin>', >=15.0) or bound loop SETTLE iterations so acoustic mass rho >= 14.0 under damping=0.05 across 8 unrolled loop cycles (Static verification failure: instruction 'SETTLE 25' at index 10 drains Basin Basin_In_A mass across CFG execution/loop back-edge to 13.75 (< 14.0). [active_loop_basins=Basin_Carry_Out, Basin_In_A, Basin_In_B, Basin_Sum_Out; depleted=Basin_In_A=13.75, Basin_Scratch_0=13.75; place self.nudge(<basin>, >=15.0) BEFORE self.settle or bound self.settle(steps <= 20) with pre-settle nudges])."]`. I must verify this requirement, and note that `self.assert_mass(self.in_a, 25.0)` was lowered to `ASSERT_MASS('Basin_Scratch_0', 25.0)` through allocation.

Now, let's shift to Turn 2's "ELIGIBLE" status and the critical comparison against Session #05. The insertion of `self.nudge(self.in_a, 15.0)` at index 7, successfully corrected the violation. The key is in the instruction count – a dramatic reduction from Session #05's 37 instructions to just 28, a reduction even with two added `ASSERT_MASS` statements. Removing the `ASSERT_MASS` statements and there's a reduction to 26 instructions, even more significant reduction percentage. The `CLEAR` instruction count shows an equally compelling optimization with a 50% reduction. It's the loop body that's the real star, specifically those streamlined wave-interference operations. The complete elimination of 0 `COPY` and 0 `CMOVE` operations are the key here, and I must not lose this optimization by making changes in Turn 3. 20 `pure_wave_quench_ops` confirms the wave mechanics are core, and a `0.35` minimum charge margin proves sustained physical operation.

Therefore, the focus of Turn 3 is clear: Optimize. That means, concrete physical parameter and threshold co-optimization priorities for Track C (Riemannian Parameter & Threshold Co-Optimization).

## 3. Live Substrate Tool Calls Executed

| # | Substrate Tool | Arguments | Key Telemetry Summary |
| :---: | :--- | :--- | :--- |
| 1 | `sol_compile_lumina_agent_and_claim` | `{"pure_wave": true, "damping": 0.05, "flow_code": "while self.in_a:\n    self.nudge(self.in_b, 15.0)\n    self.nudge(self.sum_out, 15.0)\n    self.nudge(self.carry_out, 15.0)\n    self.settle(25)\n    self.assert_mass(self.in_a, 25.0)\n    self.assert_mass(self.in_b, 25.0)\n    self.in_a = self.in_a ^ self.in_b\n    self.sum_out = self.in_a\n    self.carry_out = self.carry_out \| (self.in_a & self.in_b)", "basin_name": "Basin_A_SUM"}` | `{"subsystem": "Lumina_Compiler_And_Claim_Compiler", "basin_name": "Basin_A_SUM", "pure_wave_mode": true, "damping": 0.05, "instruction_count": 27, "static_mass_verified": false, "cycle0_quarantined": true, "policy_status": "QUARANTINE", "physical_rk4_cases_verified": 0, "python_boolean_shortcuts_used": 0}` |
| 2 | `sol_compile_lumina_agent_and_claim` | `{"flow_code": "while self.in_a:\n    self.nudge(self.in_a, 15.0)\n    self.nudge(self.in_b, 15.0)\n    self.nudge(self.sum_out, 15.0)\n    self.nudge(self.carry_out, 15.0)\n    self.settle(25)\n    self.assert_mass(self.in_a, 25.0)\n    self.assert_mass(self.in_b, 25.0)\n    self.in_a = self.in_a ^ self.in_b\n    self.sum_out = self.in_a\n    self.carry_out = self.carry_out \| (self.in_a & self.in_b)", "basin_name": "Basin_A_SUM", "pure_wave": true, "damping": 0.05}` | `{"subsystem": "Lumina_Compiler_And_Claim_Compiler", "basin_name": "Basin_A_SUM", "pure_wave_mode": true, "damping": 0.05, "instruction_count": 28, "static_mass_verified": true, "cycle0_quarantined": false, "policy_status": "ELIGIBLE", "physical_rk4_verified": true, "physical_rk4_cases_verified": 4}` |

## 4. Final Substrate-Grounded Synthesis

### Venue 5 Track B Verification & Discovery Report: Compiler Peephole Optimization, Scratch-Alias-Aware `NUDGE`/`ASSERT_MASS`, and Pure-Wave Control/Reset Quench

---

### 1. Turn 1 Telemetry Inspection: Scratch-Alias `ASSERT_MASS` Lowering & Cycle-0 `QUARANTINE` Pushback

In **Turn 1**, `sol_compile_lumina_agent_and_claim` was invoked on `"Basin_A_SUM"` (`pure_wave=True`, `damping=0.05`) with `self.assert_mass(self.in_a, 25.0)` and `self.assert_mass(self.in_b, 25.0)` inside the loop, omitting `self.nudge(self.in_a, 15.0)`.

#### Scratch-Alias Lowering of `ASSERT_MASS`
Because `self.in_a` is mutated inside the `while self.in_a:` loop body (`self.in_a = self.in_a ^ self.in_b`), the compiler allocated scratch alias `allocated_scratch_basins: {"in_a": "Basin_Scratch_0"}`. The compiler's scratch-alias resolution lowered `self.assert_mass(self.in_a, 25.0)` directly to **`ASSERT_MASS('Basin_Scratch_0', 25.0)`** at instruction index `11`, while `StaticMassSentinel` simultaneously tracked both the physical input basin (`Basin_In_A`) and its active loop scratch alias (`Basin_Scratch_0`) across the 8 unrolled CFG loop back-edges.

#### Exact Turn 1 `static_verification_error`
```text
"Static verification failure: instruction 'SETTLE 25' at index 10 drains Basin Basin_In_A mass across CFG execution/loop back-edge to 13.75 (< 14.0). [active_loop_basins=Basin_Carry_Out, Basin_In_A, Basin_In_B, Basin_Sum_Out; depleted=Basin_In_A=13.75, Basin_Scratch_0=13.75; place self.nudge(<basin>, >=15.0) BEFORE self.settle or bound self.settle(steps <= 20) with pre-settle nudges]"
```

#### Exact Turn 1 `counter_demands`
```json
[
  "Inject compensatory self.nudge('<basin>', >=15.0) or bound loop SETTLE iterations so acoustic mass rho >= 14.0 under damping=0.05 across 8 unrolled loop cycles (Static verification failure: instruction 'SETTLE 25' at index 10 drains Basin Basin_In_A mass across CFG execution/loop back-edge to 13.75 (< 14.0). [active_loop_basins=Basin_Carry_Out, Basin_In_A, Basin_In_B, Basin_Sum_Out; depleted=Basin_In_A=13.75, Basin_Scratch_0=13.75; place self.nudge(<basin>, >=15.0) BEFORE self.settle or bound self.settle(steps <= 20) with pre-settle nudges])."
]
```

#### Exact Turn 1 `instructions` (`instruction_count = 27`)
```json
[
  "LOAD('A', 'Basin_In_A')",
  "STORE('A', 'Basin_Scratch_0')",
  "CLEAR('A')",
  "LABEL('L_LOOP_START_1')",
  "LOAD('A', 'Basin_Scratch_0')",
  "NOT_WAVE('C', 'A')",
  "JUMP_IF_ACTIVE('C', 'L_LOOP_END_2')",
  "NUDGE('Basin_In_B', 15.0)",
  "NUDGE('Basin_Sum_Out', 15.0)",
  "NUDGE('Basin_Carry_Out', 15.0)",
  "SETTLE(25)",
  "ASSERT_MASS('Basin_Scratch_0', 25.0)",
  "ASSERT_MASS('Basin_In_B', 25.0)",
  "LOAD('B', 'Basin_In_B')",
  "XOR_WAVE('A')",
  "STORE('A', 'Basin_Sum_Out')",
  "AND_WAVE('B')",
  "STORE('A', 'Basin_Scratch_0')",
  "LOAD('A', 'Basin_Carry_Out')",
  "OR_WAVE('A')",
  "STORE('A', 'Basin_Carry_Out')",
  "JUMP('L_LOOP_START_1')",
  "LABEL('L_LOOP_END_2')",
  "CLEAR('A')",
  "CLEAR('B')",
  "CLEAR('C')",
  "CLEAR('D')"
]
```

---

### 2. Turn 2 Autonomous Repair & Quantitative Track B Comparison vs. Session #05 Baseline

In **Turn 2**, inserting `self.nudge(self.in_a, 15.0)` before `self.settle(25)` triggered scratch-alias-aware lowering of `self.nudge(self.in_a, 15.0)` to **`NUDGE('Basin_Scratch_0', 15.0)`** at instruction index `7` (paired with **`ASSERT_MASS('Basin_Scratch_0', 25.0)`** at index `12`). This resolved both the static mass drain (`depleted=Basin_In_A=13.75, Basin_Scratch_0=13.75`) and the `ASSERT_MASS` threshold check (`>= 25.0`), transitioning the program from `QUARANTINE` to **`ELIGIBLE`**.

#### Turn 2 Verification Summary
* **`policy_status`**: `"ELIGIBLE"` (`cycle0_quarantined: false`)
* **`static_mass_verified`**: `true` (`static_verification_error: null`, `counter_demands: []`)
* **`physical_rk4_verified`**: `true` (**`4/4`** truth-table cases verified)
* **`python_boolean_shortcuts_used`**: `0`
* **`pure_wave_quench_ops`**: `20`
* **`min_charge_margin_vs_tau`**: `0.35`

#### Quantitative Comparison: Session #05 Unoptimized Baseline vs. Track B Peephole-Optimized Code

| Metric / Compiler Artifact | Session #05 Baseline (Unoptimized) | Track B Turn 2 (`ELIGIBLE`, with 2 `ASSERT_MASS` ops) | Track B Core (excluding 2 `ASSERT_MASS` ops) | Quantitative Improvement & Physical Mechanism |
| :--- | :---: | :---: | :---: | :--- |
| **`instruction_count`** | `37` | **`28`** | **`26`** | **`-24.32%`** total (`-29.73%` core instruction reduction) |
| **`CLEAR` Count & Share** | `10 / 37` (**`27.03%`**) | **`5 / 28`** (**`17.86%`**) | **`5 / 26`** (**`19.23%`**) | **`-50.0%` fewer `CLEAR` ops**; all `5` mid-loop `CLEAR` ops eliminated (`1` prologue `CLEAR('A')` + `4` epilogue `CLEAR('A'..'D')`) |
| **`STORE('A', 'Basin_Scratch_0')`** | `3` | **`2`** | **`2`** | **`-33.3%`** (`1` loop-prologue initialization + `1` fused loop-body update; redundant pre-`sum_out` scratch store removed) |
| **`STORE` to `Basin_Carry_Out`** | `2` (`STORE('D', 'Basin_Carry_Out')`) | **`1`** (`STORE('A', 'Basin_Carry_Out')`) | **`1`** | **`-50.0%`**; dead intermediate store to `Basin_Carry_Out` before `OR_WAVE` eliminated |
| **`COPY` / `CMOVE` Shuffle Ops** | `5`-op sequence (`LOAD` $\rightarrow$ `CLEAR` $\rightarrow$ `COPY` $\rightarrow$ `CMOVE` $\rightarrow$ `STORE`) | **`0`** (`0` `COPY`, `0` `CMOVE`) | **`0`** | **`-100%` eliminated**; register forwarding (`XOR_WAVE('A')` $\rightarrow$ `STORE('A', 'Basin_Sum_Out')`) directly emits `sum_out` without reload or conditional move |
| **Loop Arithmetic/Move Ops** | `17` instructions | **`8` instructions** | **`8` instructions** | **`-52.94%`** reduction in loop-body wave-gate & data-movement instructions (`LOAD('B', 'Basin_In_B')` through `STORE('A', 'Basin_Carry_Out')`) |
| **`pure_wave_quench_ops`** | `0` (tracked as instantaneous scalar resets) | **`20`** | **`20`** | Full physical phase-destructive quench accounting across `CLEAR` and basin overwrite operations across the `4/4` RK4 rollouts |
| **`min_charge_margin_vs_tau`** | `0.35` | **`0.35`** | **`0.35`** | Exact parity in worst-case attractor charge margin above $\tau$ while executing `24.3%` fewer instructions |

#### Exact How-It-Works Breakdown of the Peephole Fusion (Indices 14–21 in Turn 2)
In Session #05, computing `self.in_a = self.in_a ^ self.in_b`, `self.sum_out = self.in_a`, and `self.carry_out = self.carry_out | (self.in_a & self.in_b)` required `17` instructions including redundant `LOAD`/`STORE`/`CLEAR` pairs and a 5-instruction `COPY`/`CMOVE` shuffle. In Track B Turn 2, the compiler fuses the entire arithmetic block into **8 instructions**:
1. `LOAD('B', 'Basin_In_B')` *(with `Basin_Scratch_0` already live in register `A` from the loop header at index 4)*
2. `XOR_WAVE('A')` *(computes `in_a ^ in_b` into `A` while preserving the pre-XOR `in_a` state needed for the carry `AND`)*
3. `STORE('A', 'Basin_Sum_Out')` *(directly writes `sum_out = in_a` without a `COPY`/`CMOVE` shuffle)*
4. `AND_WAVE('B')` *(computes `in_a & in_b` directly into register `B`)*
5. `STORE('A', 'Basin_Scratch_0')` *(commits the updated `in_a` scratch state)*
6. `LOAD('A', 'Basin_Carry_Out')` *(loads existing `carry_out` into `A`)*
7. `OR_WAVE('A')` *(interferes `A` (`carry_out`) with `B` (`in_a & in_b`) into `A`)*
8. `STORE('A', 'Basin_Carry_Out')` *(single final write to `Basin_Carry_Out`)*

---

### 3. Concrete Priorities for Track C: Riemannian Parameter & Threshold Co-Optimization

With Track B eliminating compiler-induced instruction bloat (`37 -> 28` instructions, `0` `COPY`/`CMOVE`, `50%` fewer `CLEAR` ops) and enforcing physical quench accounting (`pure_wave_quench_ops = 20`), the remaining bottleneck exposed by Turn 2 telemetry is **`min_charge_margin_vs_tau = 0.35`**. Because `min_charge_margin_vs_tau` stayed at `0.35` despite the `52.9%` reduction in loop-body wave instructions, the charge margin is governed by **continuous-time RK4 manifold physics and threshold geometry** rather than instruction-count overhead.

Track C (**Riemannian Parameter & Threshold Co-Optimization**) should prioritize the following four co-design targets:

1. **Co-Optimize Readout Decision Threshold ($\tau$) and `SETTLE` Horizon vs. Damping ($\gamma = 0.05$):**
   * *Telemetry Diagnosis:* Under `damping = 0.05` and `SETTLE(25)`, an un-nudged basin drains from `20.0` to `13.75` (`< 14.0` floor), while a nudged basin (`+15.0`) reaches `28.75` (satisfying `ASSERT_MASS(..., 25.0)`), yet the post-interference RK4 readout margin (`min_charge_margin_vs_tau`) is `0.35`.
   * *Track C Action:* Jointly sweep the readout activation threshold $\tau$, `SETTLE` duration ($T_{\text{settle}} \in [15, 25]$), and pre-settle `NUDGE` amplitude ($A_{\text{nudge}} \in [15.0, 18.0]$) so that constructive wave interference (`XOR_WAVE`, `AND_WAVE`, `OR_WAVE`) maximizes $\Delta Q = |Q_{\text{active}} - \tau|$ from `0.35` toward $\ge 0.75$ without triggering HIGH-side saturation on Logic-0 rows.

2. **Phase-Destructive Quench Coupling ($\kappa_{\text{quench}}$) for the 20 `pure_wave_quench_ops`:**
   * *Telemetry Diagnosis:* Turn 2 executed exactly `20` `pure_wave_quench_ops` across the 4 truth-table cases (`5` per truth-table case). Residual acoustic energy left in registers `A..D` or `Basin_Scratch_0` after a quench directly narrows `min_charge_margin_vs_tau` during subsequent `NOT_WAVE` and `AND_WAVE` evaluations.
   * *Track C Action:* Tune the anti-phase quench damping rate $\kappa_{\text{quench}}$ and quench sub-step duration so residual wave energy in quenched registers decays below $< 10^{-3} \tau$ before the next `LOAD` or `*_WAVE` gate, eliminating cross-cycle phase leakage in sequential loops.

3. **Riemannian Edge-Metric Weighting (Discrete Ricci Flow Overlay) on Scratch-to-Output Pathways:**
   * *Telemetry Diagnosis:* Because mutable loop variables route through `Basin_Scratch_0` (`LOAD('A', 'Basin_Scratch_0')` $\rightarrow$ `XOR_WAVE('A')` $\rightarrow$ `STORE('A', 'Basin_Sum_Out')` $\rightarrow$ `AND_WAVE('B')` $\rightarrow$ `STORE('A', 'Basin_Scratch_0')`), phase dispersion along the geodesic connecting `Basin_Scratch_0`, `Basin_In_B`, and `Basin_Sum_Out` attenuates destructive/constructive interference contrast.
   * *Track C Action:* Use Discrete Ricci Flow (`BRIDGE_ADD` / metric conductivity scaling $\psi_{\text{diffusion}}$ and $c_{\text{press}}$) on the active submanifold spanning `Basin_Scratch_0`, `Basin_In_B`, `Basin_Sum_Out`, and `Basin_Carry_Out` to equalize phase arrival times at the `XOR_WAVE` and `AND_WAVE` combiner nodes.

4. **Gate-Specific Wave Interference Gain Calibration (`XOR_WAVE` vs. `AND_WAVE` Asymmetry):**
   * *Telemetry Diagnosis:* In the peephole-fused sequence (`XOR_WAVE('A')` followed immediately by `AND_WAVE('B')`), `XOR_WAVE` relies on phase-cancellation for the `(1, 1) -> 0` case, whereas `AND_WAVE` relies on constructive threshold crossing only when both inputs are `1`. This creates opposing tension on $\tau$ (`(1, 1)` in `XOR_WAVE` pushes charge down toward $\tau - 0.35$, while `(1, 1)` in `AND_WAVE` pushes charge up above $\tau + 0.35$).
   * *Track C Action:* Introduce gate-specific Riemannian coupling gains $(\alpha_{\text{XOR}}, \alpha_{\text{AND}}, \alpha_{\text{OR}})$ or asymmetric Schmitt-trigger readout bands $(\tau_{\text{low}}, \tau_{\text{high}})$ to widen the worst-case truth-table separation margin across all `4/4` RK4 input combinations.
