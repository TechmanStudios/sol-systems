# SOL Cross-Repository Research Synthesis

**Analysis date:** September 5, 2026  
**Scope:** SOL, SOL Lens, Frontier_OS; a focused architectural read of SOL-Edge.  
**Working thesis:** an evidence-carrying, event-driven dynamical runtime.

## Executive assessment

The most defensible next objective is not to declare an entirely new physical law or a completed replacement for conventional computation. It is to establish a programmable dynamical layer whose state transitions are useful, composable, and independently verifiable.

The repositories contain complementary ingredients: dynamical state and primitive experiments in SOL, bounded metacontrol and experiment infrastructure in Frontier, observable trace representation and replay in Lens, and pre-execution authority separation in SOL-Edge. Integration is a proposal, not something established merely by the existence of these components.

This audit produced new analyses of retained evidence, not fresh whole-engine experiments. In particular, all 48 sweep-summary records and all 576 raw pair observations from the September 5 Frontier daily run were reanalyzed. Two information-loss/evaluation counterexamples were executed using arithmetic equivalent to inspected source functions. The complete historical corpus, every repository file, and all test suites were not exhaustively rerun.

## 1. Evidence and reproducibility boundary

Pinned research context:

- SOL main observed at `2c747ed9aa59ff047b040e4cbb77f73536d22535`.
- Frontier_OS main observed at `966639ec8878534166c6c6f1a363b8121d1b9e39`.
- Frontier Actions daily run `33950164824`, original head `cc79b1398d4e984f9376b2c5c21f71dfaf56ab8e`.
- Actions artifact `9965185711`, name `snowball-daily-33950164824`.
- Original ZIP SHA-256: `132c8a211dc021e536715b6c24856b1313cbb99f9c911e144461ec6c347c3aab`.
- SOL Lens scoring source inspected at blob `7f0602e94efb37b088fd10200231cd1754224bcc`.
- Frontier StatisticalPrism source inspected at blob `62fdb08e5c474732226a5324d6407dfe19e3194a`.
- Frontier EntanglerGiant source inspected at blob `6cfd575c8506ddf53f2e5c4deb0a3715590a5ba9`.

The lightweight bundle retains the original sweep summary, selected fields from every raw pair observation, and the source daily report. It does not redistribute the full roughly 848 MB uncompressed Actions artifact. `reanalyze.py --archive <original.zip>` independently reads the original ZIP and verifies its checksum. That route and the retained-input route were both executed and produced matching scientific results.

## 2. Finding A: a controller-boundary regime, not demonstrated nudge benefit

### Recomputed observations

| Measurement | Result |
|---|---:|
| Parameter variants | 48 |
| Raw pair observations | 576 |
| Hint-gate passes | 0 |
| Applied bounded nudges | 0 |
| Rejected nudge attempts | 576, all `gate_blocked` |
| Observations with a nonzero base-controller change | 317 |
| Variants entering Stabilizer | 9 |
| Final aperture | 0.05 in all 48 variants |
| Final damping | 0.99 in all 48 variants |
| Observations simultaneously at those two bounds | 353 |
| Recorded entangler-strength range | 0.2571973902 to 0.4657928478 |

The distinction between the base controller and optional nudges is essential. These simulations were not uncontrolled: the base controller changed state on 317 observations. They do not establish the causal benefit of optional nudges, because no nudge was applied.

### Mechanistic interpretation

`EntanglerGiant` sets aperture bounds to `(0.05, 0.95)` and damping bounds to `(0.5, 0.99)`. Its damping update includes a dedicated reduction term:

`-0.10 * max(0.0, entanglement_strength - 0.70)`

The recorded strength never exceeded 0.466. Therefore this reduction term was zero throughout the audited sweep. Other feedback terms can reduce damping during improvement, so this is not a claim that all negative damping feedback is absent. It identifies one structurally inactive balancing branch, alongside repeatedly active positive terms and observed clipping.

**New working hypothesis:** a substantial part of the apparent operating regime is a controller-induced boundary regime. This is distinguishable from an attractor of the uncontrolled substrate. A frozen-controller, common-input comparison is the appropriate test.

### Seed concentration and horizon mismatch

| Seed | Variants | Variants entering Stabilizer |
|---|---:|---:|
| 29 | 12 | 9 |
| 83 | 12 | 0 |
| 149 | 12 | 0 |
| 167 | 12 | 0 |

All nine entries occurred at shared pair clock 154 or 168, corresponding to late observations in these 12-cycle runs. The current pulse configuration uses six cycles and seed 149; its zero yield is not directly comparable with a 12-cycle, four-seed daily grid. Shared seeds and nearby parameter cases are not independent replication.

The committed state contains eight daily yields of 9, eight pulse yields of 0, and long explore/diagnosis streaks. These facts establish repetition of reported counts, not continuing discovery or broad robustness. Fresh, separated random streams for topology, input, and perturbation would identify the source of seed sensitivity.

### Telemetry integrity issues

All 48 summary rows contain nonfinite `msf_lambda_hat_mean` values. The raw history includes an initial insufficient-history period. Reduction should distinguish missing estimates from finite estimates, retain finite sample counts, and export standards-compliant missing values rather than NaN.

The `coupling_posture_profile_used` field is absent from all 48 summaries. The snowball consumer reads this field and defaults to `none`; the current state consequently cannot establish actual profile exposure. The inspected raw pair export also omits the field. Do not interpret the accumulated `none` count as proof that a profile was never selected. Export configured, selected, eligible, applied, and outcome states separately.

## 3. Finding B: SOL completion times may be more stable than the reported halt rate

The retained cognition report runs every configuration for at most 500 steps. Changing `dt` changes the simulated-time budget.

| Pressure | dt 0.08 | dt 0.12 | Relative time difference |
|---|---:|---:|---:|
| 2 | 383 steps = 30.64 time units | 255 steps = 30.60 time units | about 0.13% |
| 3 | 307 steps = 24.56 time units | 205 steps = 24.60 time units | about 0.16% |

At `dt=0.04`, the 500-step horizon is only 20 time units. It ends before either of these completion times. Thus the reported non-halting cases at that timestep are censored observations, not evidence that these systems would never halt.

**New positive hypothesis:** the engine may support a useful, nearly timestep-consistent completion event in these parameter regions. A matched-time rerun predicts a halt around steps 765-766 for pressure 2 and 614-615 for pressure 3 at `dt=0.04`; these are predictions, not results obtained in this audit.

A good rerun holds simulated duration and readout duration fixed, includes smaller timesteps, and checks memory postconditions. Low flux alone can mean successful completion, loss of signal, or a blocked network. A trustworthy completion condition requires both a persistent low-residual condition and the correct task state.

The experiment also explicitly sets context gates, disables belief diffusion, and externally selects readout. This is evidence about engineered primitives, not spontaneous general cognition. That distinction does not diminish their possible value as computing components.

The 66.7% routing statistic additionally combines lane selectivity with an active-loop loading threshold. These should be separate measurements. Table entries of `0.00` on inactive lanes are rounded observations, not a proof of exact zero leakage.

## 4. Finding C: semantic information is lost before Frontier dynamics see it

The inspected StatisticalPrism input map is:

`f(e) = (5 * mean(e), 10 * variance(e), 2 * skewness(e))`.

For any coordinate permutation P, `f(e) = f(Pe)`. Two distinct inputs can therefore induce exactly the same injection field from the same initial state through this channel.

The bundled counterexample uses two orthogonal, normalized 1,536-dimensional vectors with the same multiset of entries. Their cosine similarity is zero; both fingerprints are `[0, 0.006510416666666667, 0]` to numerical precision. Unlike a sparse-unit-vector example, these fingerprints remain near the intended coordinate region.

This is an exact information-loss counterexample, not a claim that these synthetic vectors are natural-language embeddings. It demonstrates that the input channel cannot generally preserve semantic direction. Subsequent dynamics cannot reconstruct the discarded distinction unless it arrives through another channel.

**Proposed repair:** separate identity-bearing input from operating-condition input. Use a task-validated projection, semantic anchors, or multiple low-dimensional charts for identity. Keep moments as intensity, spread, and uncertainty controls. Evaluate neighborhood preservation and held-out task performance; do not assume any chosen projection dimension is sufficient.

The exchanged wormhole signature also averages density and absolute-valued potential/flux summaries. Whether those summaries are sufficient for a given task is an empirical question; sign-sensitive tasks require a sign-preserving representation.

## 5. Finding D: Lens's current court is not a dependency proof

`scoreLogons` takes node fields, not edges. Its current verdict therefore cannot respond to an edge-only change while node fields remain fixed. This is a property of the scoring function, not a claim that all other packet validation layers are absent.

The current contradiction metric is:

`contradiction_count / (node_count + 4)`.

In the bundled formula-level example, two supported nodes and one unresolved contradiction receive HOLD. Adding three redundant high-scoring supported nodes, with distinct identifiers and without resolving the contradiction, changes the score to PROMOTE: the contradiction fraction falls from `1/7` to `1/10`.

The README already labels the court as a demonstration scoring profile and separates it from manifold replay. That separation is sound. A production verifier needs mandatory per-claim obligations, dependency reachability, source identity/deduplication, and non-dilutable critical constraints. Aggregate coherence can remain a diagnostic; it should not override a violated obligation.

**Cross-repository synthesis:** Frontier's input map and Lens's output score both collapse distinctions that the intended application may need. Improving the underlying dynamics cannot fix a distinction erased by the input encoder or ignored by the output verifier.

## 6. Finding E: the historical 83.33 boundary is already explained by its update law

The proof ledger calls damping near 83.33 a topology-invariant mathematical constant/phase boundary. The detailed domain notes also record:

`rho_next = rho * (1 - 0.1 * damping * dt)`.

At `dt=0.12`, the multiplier reaches zero at `damping = 1/(0.1*0.12) = 83.333...`. Negative updates combined with a nonnegative clamp explain the abrupt extinction. Other retained run notes already acknowledge this mechanism; this synthesis exposes an inconsistency in claim status, not a previously unknown formula.

The associated predictions are 166.666... at `dt=0.06` and 41.666... at `dt=0.24`. A matched-time comparison against exact exponential damping or a positivity-preserving method would separate a discrete-update boundary from a continuum dynamical transition. Changing the solver must remain an explicitly versioned experiment, not a silent rewrite of the model.

The discrete map can still be an interesting computational system. It should not be described as an independently discovered universal physical constant on this evidence.

## 7. Positive computational foundations worth preserving

The non-destructive-readout report shows two successful read pulses while the binary state remains 1. Host mass nevertheless declines. The defensible abstraction is a state-preserving, resource-consuming read over the tested horizon, not indefinitely non-depleting storage. Treat it as a register with a read-disturb margin and refresh budget.

The LogosVM branching report contains a two-case conditional-branch truth table driven by register state. That is a concrete bridge from dynamical state to ordinary program control. More composition, noise, reset, fan-out, and read-disturb tests are needed before a general computing claim.

The adaptive handshake report retains precedence across the tested damping values by triggering a host-side nudge after observed arbitration. This supports investigating event-triggered control; it is not by itself proof of an autonomous physical clock.

## 8. Architectural proposal: evidence-carrying dynamical execution

The proposed layer would compile a task contract into an input encoding, graph/dynamical configuration, permitted intervention policy, readout map, resource budget, and completion condition. A result would be committed only after an independent verifier checks the observed outcome.

Roles:

- **SOL:** implements and characterizes stateful dynamical operators.
- **Frontier:** selects or adapts operating regions, subject to explicit limits and identifiable experimental exposure.
- **Lens:** renders actual observable traces and checks claim/dependency obligations independently of the dynamics.
- **SOL-Edge:** binds proposals and evidence to capabilities and release review. Its current ELIGIBLE outcome is explicitly not physical authorization.

Do not equate identically named fields across repositories. A pressure-like physical state, a trace risk score, a phase angle, and a constraint-alignment score are different quantities unless a versioned mapping establishes their relationship.

A common evidence envelope should carry code/graph/input hashes, RNG streams, solver and timestep, physical and wall-clock timing, controller policy, actual intervention exposure, raw-versus-derived labels, fixture-versus-live provenance, readout mapping, semantic ground truth, and resource measurements.

### The key research hypothesis: useful causal abstraction

Let x be the full state and z = Phi(x) a proposed macrostate such as register state, route selection, or an evidence-bound result. Two microstates mapped to the same macrostate should respond similarly at the macro level to the same legal intervention, within a specified tolerance and horizon.

Test this by constructing matched microstate pairs, applying identical inputs/interventions, and comparing next-macrostate distributions under noise. If hidden phase, timing, or mass reserve changes the result, those variables must be included in the abstraction or the primitive's operating contract. A compression is not a reliable instruction interface simply because its labels are stable.

If robust macro-transitions compose, the layer can expose instructions such as store, recall, route, compare, and commit while allowing different implementations beneath them. This is a testable route toward a computing abstraction rather than a claim that novelty follows from a visual pattern.

## 9. Recommended flagship experiment

Build one small end-to-end contextual delayed-recall and conflict-routing task. The system receives a context, a payload, a distracting interval, and a retrieval cue; some trials contain conflicting or disconnected evidence. Ground truth is generated independently of the dynamics and the court.

Use an identity-preserving encoder. SOL performs storage/routing/readout; Frontier is evaluated in frozen and adaptive modes; Lens emits a real observable packet with graph-aware obligations; SOL-Edge evaluates eligibility without performing a consequential action.

Compare against an explicit finite-state/DAG implementation, a linear graph-diffusion baseline, and a conventional reservoir with the same encoder/readout budget. Include controller-only and substrate-ablated conditions. Test held-out seeds, durations, noise, reordered inputs, and graph perturbations. Separate topology randomness from input randomness.

Measure correct recall/routing, false commit rate, retention/read-disturb margin, recovery time, wall-clock latency, memory, and total controller/verification overhead. Simulated time is not wall-clock speed; simulated mass is not measured electrical energy. A hardware energy claim requires actual measurement.

A useful outcome is a reproducible advantage on at least one named task under a fixed budget, without relaxing correctness. A null result is also informative: it can show whether the valuable part is the control/verification layer rather than the simulated substrate.

## 10. Research positioning

Dynamical and physical reservoir computation already provide relevant prior art. Dambre et al. (2012) give information-processing capacity diagnostics and bounds for their observable-state/linear-readout framework; these are not a blanket limit on all computation. OpenPRC (2026) offers a schema-driven simulation/measurement-to-task workflow and useful comparison methodology. Hoel's Causal Emergence 2.0 provides one formal approach to comparing causal contribution across scales; it is not a universal certificate of emergence.

The proposed differentiation is a tested combination of programmable dynamical macro-operators, semantic input/output contracts, identifiable adaptation, and evidence-bearing execution. Global novelty remains unestablished and would need a focused prior-art review after the technical claim is narrowed.

## Priority order

1. Repair telemetry ambiguity and expose controller saturation/intervention coverage.
2. Preserve semantic identity and enforce non-dilutable, graph-aware verification.
3. Rerun primitive experiments with matched time, held-out randomness, postconditions, and resource budgets.
4. Execute the single end-to-end benchmark and causal-abstraction test before adding more conceptual layers.

## Sources inspected or used

Repository source links are pinned where a commit was established. Blob hashes above identify the inspected Lens and Frontier functions.

- [SOL master chronicle](https://github.com/TechmanStudios/sol/blob/2c747ed9aa59ff047b040e4cbb77f73536d22535/SOL_Master_Chronicle.md)
- [SOL cognition report](https://github.com/TechmanStudios/sol/blob/2c747ed9aa59ff047b040e4cbb77f73536d22535/data/emergent_cognition/report.md)
- [SOL cognition experiment](https://github.com/TechmanStudios/sol/blob/2c747ed9aa59ff047b040e4cbb77f73536d22535/emergent_cognition_experiment.py)
- [SOL proof ledger](https://github.com/TechmanStudios/sol/blob/2c747ed9aa59ff047b040e4cbb77f73536d22535/solKnowledge/proof_packets/LEDGER.md)
- [SOL phonon domain notes](https://github.com/TechmanStudios/sol/blob/2c747ed9aa59ff047b040e4cbb77f73536d22535/solKnowledge/proof_packets/domains/phonon_faraday.md)
- [SOL frozen/flicker analysis](https://github.com/TechmanStudios/sol/blob/2c747ed9aa59ff047b040e4cbb77f73536d22535/data/flicker_frozen/flicker_frozen_run_bundle.md)
- [SOL NDRO register report](https://github.com/TechmanStudios/sol/blob/2c747ed9aa59ff047b040e4cbb77f73536d22535/solResearch/nextBestTest/ndro_register_report.md)
- [SOL LogosVM report](https://github.com/TechmanStudios/sol/blob/2c747ed9aa59ff047b040e4cbb77f73536d22535/solResearch/nextBestTest/logos_vm_report.md)
- [SOL adaptive handshake report](https://github.com/TechmanStudios/sol/blob/2c747ed9aa59ff047b040e4cbb77f73536d22535/data/adaptive_handshake/report.md)
- [Frontier StatisticalPrism](https://github.com/TechmanStudios/Frontier_OS/blob/966639ec8878534166c6c6f1a363b8121d1b9e39/Exciton-MoA/transDucer/statisticalPrism.py)
- [Frontier EntanglerGiant](https://github.com/TechmanStudios/Frontier_OS/blob/966639ec8878534166c6c6f1a363b8121d1b9e39/Exciton-MoA/teleMetry/entanglerGiant.py)
- [Frontier snowball state](https://github.com/TechmanStudios/Frontier_OS/blob/966639ec8878534166c6c6f1a363b8121d1b9e39/Exciton-MoA/working_data/snowball/state.json)
- [Frontier snowball consumer](https://github.com/TechmanStudios/Frontier_OS/blob/966639ec8878534166c6c6f1a363b8121d1b9e39/Exciton-MoA/scripts/snowball_experiment.py)
- [Frontier source Actions run](https://github.com/TechmanStudios/Frontier_OS/actions/runs/33950164824)
- [SOL Lens scoring](https://github.com/TechmanStudios/sol-lens/blob/main/lib/sol-engine.ts)
- [SOL Lens README](https://github.com/TechmanStudios/sol-lens/blob/main/README.md)
- [SOL-Edge README](https://github.com/TechmanStudios/sol-edge/blob/main/README.md)
- [Dambre et al., Information Processing Capacity of Dynamical Systems](https://www.nature.com/articles/srep00514)
- [OpenPRC, 2026](https://arxiv.org/html/2604.07423)
- [Causal Emergence 2.0](https://arxiv.org/html/2503.13395v3)
