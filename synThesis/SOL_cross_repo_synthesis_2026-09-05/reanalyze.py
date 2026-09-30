#!/usr/bin/env python3
"""Reanalyze retained Frontier evidence and test two algebraic counterexamples.

Python 3.10+, standard library only. No network access or repository mutation.
These are data reanalyses and formula-level checks, NOT a rerun of SOL/Frontier.

Usage:
  python reanalyze.py
  python reanalyze.py --archive /path/to/frontier-daily-2026-09-05.zip
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import statistics
import zipfile
from typing import Any

ROOT = Path(__file__).resolve().parent
EXPECTED_ARCHIVE_SHA256 = '132c8a211dc021e536715b6c24856b1313cbb99f9c911e144461ec6c347c3aab'
RUN_PREFIX = 'runs/daily/20260905T063418Z/'

def read_jsonl(text: str) -> list[dict[str, Any]]:
    # Python accepts the source artifact's nonstandard NaN values. Audit output
    # explicitly reports these and never serializes nonfinite JSON numbers.
    return [json.loads(line) for line in text.splitlines() if line.strip()]

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def load_inputs(archive: Path | None) -> tuple[list[dict], list[dict], dict]:
    if archive is not None:
        digest = sha256_file(archive)
        if digest != EXPECTED_ARCHIVE_SHA256:
            raise ValueError(f'Unexpected source archive SHA-256: {digest}')
        with zipfile.ZipFile(archive) as z:
            summaries = read_jsonl(z.read(RUN_PREFIX + 'sweep_summary.jsonl').decode())
            telemetry: list[dict] = []
            for name in sorted(z.namelist()):
                if name.startswith(RUN_PREFIX) and name.endswith('/adaptive_tau_history.jsonl'):
                    variant = name.split('/')[-2]
                    for row in read_jsonl(z.read(name).decode()):
                        if row.get('record_type') == 'pair':
                            telemetry.append({'variant_id': variant, **row})
        return summaries, telemetry, {'archive_sha256': digest, 'mode': 'original_archive'}
    summary_path = ROOT / 'data' / 'frontier_sweep_summary.jsonl'
    pair_path = ROOT / 'data' / 'frontier_pair_metrics.jsonl'
    return (
        read_jsonl(summary_path.read_text()), read_jsonl(pair_path.read_text()),
        {'mode': 'retained_summary_and_selected_raw_fields',
         'summary_sha256': sha256_file(summary_path),
         'selected_pair_fields_sha256': sha256_file(pair_path)},
    )

def counter(values: list[Any]) -> dict[str, int]:
    return {str(k): v for k, v in sorted(collections.Counter(values).items(), key=lambda x: str(x[0]))}

def frontier_audit(summaries: list[dict], telemetry: list[dict]) -> dict:
    if len(summaries) != 48 or len(telemetry) != 576:
        raise ValueError('This audit expects the pinned 48-variant, 576-observation experiment.')
    by_variant: dict[str, list[dict]] = collections.defaultdict(list)
    for row in telemetry:
        by_variant[row['variant_id']].append(row)
    final = [sorted(rs, key=lambda r: r['shared_pair_clock'])[-1] for rs in by_variant.values()]
    seed_results = {}
    for seed in sorted({r['seed'] for r in summaries}):
        sr = [r for r in summaries if r['seed'] == seed]
        seed_results[str(seed)] = {
            'variants': len(sr),
            'variants_entering_stabilizer': sum(r['first_stabilizer_tick'] is not None for r in sr),
            'mean_recorded_coherence': statistics.fmean(r['coherence_mean'] for r in sr),
        }
    nonzero_base_steps = sum(
        any(abs(r[f'entangler_{k}_after'] - r[f'entangler_{k}_before']) > 1e-12
            for k in ('aperture', 'damping', 'phase')) for r in telemetry
    )
    present_nan = sum(isinstance(r.get('msf_lambda_hat_mean'), float)
                      and not math.isfinite(r['msf_lambda_hat_mean']) for r in summaries)
    mode_cells = []
    for r in summaries:
        if r['seed'] == 29:
            mode_cells.append({k: r[k] for k in (
                'embedding_a_loc', 'embedding_b_loc', 'embedding_drift', 'first_stabilizer_tick', 'final_mode')})
    result = {
        'variants': len(summaries), 'pair_observations': len(telemetry),
        'gate_passes_raw': sum(bool(r['entangler_hint_gate_passed']) for r in telemetry),
        'nudges_applied_raw': sum(bool(r['entangler_nudge_applied']) for r in telemetry),
        'nudge_rejections': counter([r['entangler_nudge_rejection_reason'] for r in telemetry]),
        'gate_reasons': dict(sum((collections.Counter(r['hint_gate_reason_counts']) for r in summaries), collections.Counter())),
        'base_controller_nonzero_change_steps': nonzero_base_steps,
        'variants_entering_stabilizer': sum(r['first_stabilizer_tick'] is not None for r in summaries),
        'first_stabilizer_shared_clock_counts': counter([r['first_stabilizer_tick'] for r in summaries if r['first_stabilizer_tick'] is not None]),
        'by_seed': seed_results,
        'seed_29_factor_cells': mode_cells,
        'final_aperture_values': sorted({r['wormhole_aperture'] for r in final}),
        'final_damping_values': sorted({r['damping'] for r in final}),
        'observations_at_both_control_bounds': sum(abs(r['wormhole_aperture'] - .05) < 1e-12 and abs(r['damping'] - .99) < 1e-12 for r in telemetry),
        'recorded_entangler_strength_range': [min(r['entangler_strength'] for r in telemetry), max(r['entangler_strength'] for r in telemetry)],
        'main_damping_reduction_branch_eligible_observations': sum(r['entangler_strength'] > .70 for r in telemetry),
        'bilateral_burst_count_distribution': counter([r['bilateral_burst_count'] for r in telemetry]),
        'msf_status_counts_raw': counter([r['entangler_nudge_msf_status'] for r in telemetry]),
        'nonfinite_msf_lambda_mean_summary_rows': present_nan,
        'summary_rows_missing_profile_used_field': sum('coupling_posture_profile_used' not in r for r in summaries),
        'raw_pair_rows_missing_profile_used_field': sum('coupling_posture_profile_used' not in r and 'entangler_coupling_posture_profile_used' not in r for r in telemetry),
    }
    assert result['gate_passes_raw'] == result['nudges_applied_raw'] == 0
    assert result['base_controller_nonzero_change_steps'] == 317
    assert result['final_aperture_values'] == [.05] and result['final_damping_values'] == [.99]
    assert result['by_seed']['29']['variants_entering_stabilizer'] == 9
    return result

def prism_moments(x: list[float]) -> list[float]:
    """Formula-level equivalent of StatisticalPrism.extract_moments (nonconstant x)."""
    mean = statistics.fmean(x)
    m2 = statistics.fmean((v - mean) ** 2 for v in x)
    if m2 <= 0:
        raise ValueError('Counterexample excludes constant vectors; skewness is undefined there.')
    m3 = statistics.fmean((v - mean) ** 3 for v in x)
    return [5 * mean, 10 * m2, 2 * m3 / m2 ** 1.5]

def prism_counterexample() -> dict:
    n = 1536
    scale = 1 / math.sqrt(n)
    x = [v * scale for v in ([1, 1, -1, -1] * (n // 4))]
    y = [v * scale for v in ([1, -1, 1, -1] * (n // 4))]
    cosine = math.fsum(a * b for a, b in zip(x, y)) / math.sqrt(math.fsum(a*a for a in x) * math.fsum(b*b for b in y))
    fx, fy = prism_moments(x), prism_moments(y)
    assert abs(cosine) < 1e-12 and fx == fy
    return {'dimension': n, 'cosine_similarity': cosine, 'fingerprint_x': fx, 'fingerprint_y': fy,
            'fingerprints_identical': fx == fy,
            'scope': 'Synthetic exact information-loss counterexample for this input channel; not a semantic task benchmark.'}

def lens_metrics(logons: list[dict]) -> dict:
    """Equivalent arithmetic for the currently inspected static scoring function."""
    average = lambda values: math.fsum(values) / max(len(values), 1)
    clamp = lambda value: max(0.0, min(1.0, value))
    evidence = average([r['evidence'] for r in logons if r['status'] != 'contradiction'])
    alignment = average([r['psi'] for r in logons])
    pressure = average([r['pressure'] for r in logons])
    contradiction = sum(r['status'] == 'contradiction' for r in logons) / max(len(logons) + 4, 1)
    coherence = clamp(.45 * evidence + .42 * alignment + .13 * (1 - pressure))
    verdict = 'QUARANTINE' if contradiction > .2 or coherence < .72 else ('HOLD' if contradiction > .1 or evidence < .82 else 'PROMOTE')
    return {'evidence': clamp(evidence), 'coherence': coherence, 'contradiction': contradiction, 'verdict': verdict}

def lens_counterexample() -> dict:
    supported = lambda i: dict(id=f's{i}', status='supported', evidence=.9, rho=.8, psi=.95, pressure=.05)
    contradiction = dict(id='c', status='contradiction', evidence=.1, rho=.8, psi=.95, pressure=.05)
    base = [supported(0), supported(1), contradiction]
    padded = base + [supported(i) for i in (2, 3, 4)]
    before, after = lens_metrics(base), lens_metrics(padded)
    assert before['verdict'] == 'HOLD' and after['verdict'] == 'PROMOTE'
    return {'before': before, 'after_three_redundant_supported_nodes': after,
            'same_unresolved_contradiction': True,
            'graph_edges_not_an_argument_to_scorer': True,
            'scope': 'Static scoreLogons/courtVerdict formulas only; not a complete application or packet-validator test.'}

def time_reanalysis() -> list[dict]:
    result = []
    for cp, n08, n12 in [(2, 383, 255), (3, 307, 205)]:
        t08, t12 = n08 * .08, n12 * .12
        result.append({'c_press': cp, 'halt_time_dt_008': t08, 'halt_time_dt_012': t12,
                       'relative_difference_percent': abs(t08 - t12) / ((t08 + t12) / 2) * 100,
                       'dt_004_observation_horizon': 500 * .04,
                       'predicted_dt_004_halt_step_range_not_observed': [min(t08, t12) / .04, max(t08, t12) / .04]})
    return result

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Optional original GitHub Actions ZIP; checksum enforced.')
    parser.add_argument('--output', type=Path, default=ROOT / 'audit_results.json')
    args = parser.parse_args()
    summaries, telemetry, provenance = load_inputs(args.archive)
    results = {
        'analysis_date': '2026-09-05', 'analysis_kind': 'existing_data_reanalysis_and_formula_counterexamples',
        'original_actions_run_id': 33950164824, 'original_artifact_id': 9965185711,
        'provenance': provenance, 'frontier': frontier_audit(summaries, telemetry),
        'prism': prism_counterexample(), 'lens': lens_counterexample(),
        'sol_physical_time': time_reanalysis(),
        'historical_damping_zero': [{'dt': dt, 'zero_damping_parameter': 1/(.1*dt)} for dt in [.06,.12,.24]],
        'limitations': [
            'No fresh SOL or Frontier simulation and no repository-wide test-suite rerun.',
            'Formula counterexamples are deliberately scoped and do not test all integration/validation layers.',
            'One complete retained Frontier sweep was reanalyzed; daily history comparisons use the committed state summary.',
            'Parameter variants sharing seeds are not statistically independent robustness trials.',
            'An absent summary field is not evidence that its runtime value was none.',
        ],
    }
    args.output.write_text(json.dumps(results, indent=2, allow_nan=False) + '\n')
    print(f'All consistency assertions passed. Audit written to {args.output}')
    print(json.dumps({k: results['frontier'][k] for k in ('variants','pair_observations','gate_passes_raw','nudges_applied_raw','base_controller_nonzero_change_steps','variants_entering_stabilizer','final_aperture_values','final_damping_values')}, indent=2))

if __name__ == '__main__':
    main()
