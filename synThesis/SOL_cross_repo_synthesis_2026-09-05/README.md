# Reproducible SOL cross-repository audit

Start with `RESEARCH_SYNTHESIS.md` for findings, caveats, sources, and architecture.

Run `python reanalyze.py` with Python 3.10 or newer. No third-party packages, network calls, or repository changes are needed. The script reads retained evidence, tests two formula-level counterexamples, and writes `audit_results.json`.

The optional `--archive /path/to/frontier-daily-2026-09-05.zip` route reanalyzes the original GitHub Actions artifact after verifying its SHA-256. The full original ZIP is not included in this lightweight bundle. `audit_from_original_archive.json` records the independently executed original-archive route. Both routes were run during this analysis and returned matching findings.

## Contents

- `RESEARCH_SYNTHESIS.md`: technical synthesis and source references.
- `reanalyze.py`: executable, standard-library-only reanalysis and counterexamples.
- `audit_results.json`: strict JSON results from retained data.
- `audit_from_original_archive.json`: results obtained directly from the original Actions ZIP.
- `experiment_plan.json`: proposed experiments, outcomes, and interpretation guards.
- `data/frontier_sweep_summary.jsonl`: unmodified 48-row source summary. WARNING: the source contains nonstandard JSON NaN values; Python's JSON parser accepts them, but strict parsers may not.
- `data/frontier_pair_metrics.jsonl`: selected source fields from all 576 pair telemetry observations, plus source-variant identifiers. This selected-field export is strict JSON.
- `data/source_latest_report.md`: original daily report from the Actions artifact.
- `manifest.json`: provenance and checksums.

## Interpretation limits

These files do not claim a new full-engine simulation, execution of every repository test, exhaustive review of every historical experiment, or established global novelty. The Prism and Lens tests are equivalent-arithmetic counterexamples, not a full application integration test. Control-boundary results describe one complete 48-variant sweep, not every configuration Frontier can run.

The artifact includes analysis of private/user-owned research. Review before publishing it outside the project.
