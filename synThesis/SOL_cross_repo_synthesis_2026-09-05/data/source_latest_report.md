# Snowball daily report — 2026-09-05T07:19:08Z

- run_dir: `/home/runner/work/Frontier_OS/Frontier_OS/Exciton-MoA/working_data/snowball/runs/daily/20260905T063418Z`
- started_utc: 2026-09-05T06:34:18Z
- engine_returncode: 0
- regime: explore -> explore
- size: medium
- rationale: low_variance_candidate streak=763 >=3 -> explore; msf_ab: treatment (--enable-msf-guard); posture_ab: treatment (coupling_posture_profiles: weak,permissive)

## Outcome
- variants: 48
- natural Stabilizer entries: 9
- gate passes (sum): 0
- bounded nudges applied (sum): 0
- positive forward windows (sum): 0
- consensus diagnosis: low_variance_candidate
- consensus synchrony basis: boundary_led
- consensus coupling posture: strained
- consensus basin fragility: broad
- paper trigger: basin_fragility

## Counts
- diagnosis: entered_stabilizer=9, low_variance_candidate=39
- synchrony: boundary_led=45, structure_led=3
- coupling: strained=48
- basin: broad=28, narrow=20

## State after
- diagnosis_streak: low_variance_candidate x 764
- weak_synchrony_streak: 0
- observe_only_streak: 0
- recent_yields_pulse: [0, 0, 0, 0, 0, 0, 0, 0]
- recent_yields_daily: [9, 9, 9, 9, 9, 9, 9, 9]

## Engine argv
```
--sweep --sweep-root-dir /home/runner/work/Frontier_OS/Frontier_OS/Exciton-MoA/working_data/snowball/runs/daily/20260905T063418Z --clean-run-reset --enable-hint-gate --enable-bounded-nudges --persist-summaries --runtime-preset best-pocket --embedding-scale 0.08 --hint-confidence-threshold 0.55 --hint-reliability-threshold 0.6 --enable-msf-guard --coupling-posture-profile weak:0.45,0.55,none --coupling-posture-profile permissive:none,none,0.05 --cycles 12 --sweep-cycle-counts 12 --sweep-embedding-a-locs 0.49 0.5 0.51 --sweep-embedding-b-locs 0.57 0.58 --sweep-embedding-drifts 0.06 0.08 --sweep-seeds 149 83 29 167
```

## Handoff excerpt
```
# UNCERTAINTY TO PAPER RECOMMENDATION

Selected variant: variant_043_a0p510_b0p580_d0p060_c12_s29
Working dir: /home/runner/work/Frontier_OS/Frontier_OS/Exciton-MoA/working_data/snowball/runs/daily/20260905T063418Z/variant_043_a0p510_b0p580_d0p060_c12_s29
Sweep trigger coverage: 48/48 variants
Selection basis: representative triggered variant chosen from a sweep-wide consensus, favoring stronger near-pass maturity (near-passes=4, confidence-gap=0.17, reliability-gap=0.22)
Consensus pattern: dominant triggered pattern: intervention=control policy (48/48), sync=borderline (45/48), basin=broad (28/48), diagnosis=low_variance_candidate (39/48)

## Uncertainty summary
- current bottleneck: The pair shows unresolved synchrony uncertainty: local evidence is not cleanly separating weak hints from structural difficulty in reaching or sustaining phase alignment.
- why current repo knowledge is still insufficient: Current sweep evidence leaves unfavorable synchrony posture and narrow basin posture only partially explained by local diagnostics.
- why this is stable uncertainty rather than a one-off failure: The trigger persists across gate blocks=12, near-passes=4, contradictions=2, and diagnosis=entered_stabilizer.
```
