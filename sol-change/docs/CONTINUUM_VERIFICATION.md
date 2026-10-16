# SOL continuum integration verification — v0.2.0

Verified locally on Windows on October 15, 2026. This record covers the saved-artifact bridge and SOL Change application. It does not certify the upstream continuum’s research claims or execution system.

## Automated checks

**115 tests passed**, comprising the original 81 application checks plus 34 bridge/API checks. JavaScript syntax validation also passed.

```text
python -m unittest discover -s tests -v
node --check static/app.js
```

The detailed log is `sol-change/test-results/continuum-unittest.txt`, ignored by Git. The CLI retry path was additionally checked to confirm its reported review status matches the preserved, already-reviewed experiment.

New coverage includes:

- Conversion into valid run schema 1.0, exact retained decoded source text and digest, CRLF/BOM identity through the Python/CLI path, and JSON-pointer evidence references.
- Primary-observation selection regardless of assigned comparison role; counterfactual `baseline_evaluation` is never selected as an independently executed run.
- Raw primary metrics and normalized `evaluation.metrics`, scoring profile, retained normalized verdicts, and visible conflicting top-level claims.
- Unknown execution time, USD cost, and human review; missing execution input/conditions/evaluator/data origin; explicit packet-generation timestamp semantics.
- Different scenarios, controlled conditions, and evaluator versions; synthetic-origin labeling when explicitly declared.
- Embedded/sidecar context handling and conflicts; malformed fields, unsupported packet schemas, oversized input, invalid score ranges, and missing values.
- No fetching of evidence URLs; bounded inventory without executing sibling source; output conflict handling without overwrite.
- Complete archive round trips with native sources and reviewer decisions; duplicate registration preserving the existing review and revision history.
- Native intake API atomicity, duplicate conflicts, review-pending status with zero decisions, and cross-origin write rejection.
- Default port 8770, separate from the existing SOL live server’s documented 8765.

## Existing continuum artifacts

The dated inventory at `data/continuum/inventory-2026-10-15.json` contains 9 component entries and 18 artifact entries. Six files identify as the supported v0.2 packet format:

1. `sol-lens/samples/live_gemini4_closed_loop_repaired_packet.json`
2. `sol-lens/samples/live_gemini4_dialectical_h1_packet.json`
3. `sol-lens/samples/live_gemini4_non_hermitian_pt_packet.json`
4. `sol-lens/samples/live_gemini4_ricci_surgery_packet.json`
5. `sol-lens/samples/live_gemini4_wormhole_homology_packet.json`
6. `sol-decide/examples/live_gemini_4_argon_dialectical_h1_packet.json`

All six were read locally, converted successfully, validated against SOL Change’s runtime run rules, and checked for retained original source text/digest and unknown execution-time values. Their byte digests matched the earlier inventory snapshot. The two dialectical files were byte-identical copies; these are six artifact files, not six independently verified trials.

Machine-readable observations and digests are saved in `data/continuum/native-artifact-verification-2026-10-15.json`. No upstream algorithms or provider calls were executed to produce this verification.

## Actual browser observations

An isolated QA app was launched on port 8771 with `test-results/continuum-browser/observatory.sqlite3`. Through the actual Codex in-app browser:

1. Opened **SOL packets**, entered a comparison title/change, and selected the saved wormhole and Ricci-surgery JSON files through file choosers.
2. Created the comparison and observed the incompatibility warning for the different scenarios.
3. Inspected the displayed primary evidence scores `0.974` and `0.978` as automated assessments on `score/1`, with differences withheld.
4. Confirmed execution time remained unmeasured on both sides; no numerical value was inferred from packet timestamps or narrative latency claims.
5. Opened run provenance and confirmed the separate **Source packet JSON** control, packet-generation timestamp label, source hashes, and context warnings were present. The original source payload itself was verified through the conversion/round-trip checks above; this browser check did not assert independent source authenticity.
6. Reloaded after the static changes, opened the continuum integration guide, and opened/canceled its native import dialog successfully.
7. Inspected console logs; no warnings or errors were reported in the inspected browser session.

The primary application launched successfully using `launch.ps1 -NoBrowser` at **8770**, health endpoint reported app **0.2.0** / schema **1.0**, and the prepared **SOL continuum: packet interoperability check** was inspected there. Both run panels were present, and the document did not overflow horizontally at the inspected desktop width. The import flow was also exercised in the browser’s narrow default viewport. Temporary viewport overrides were reset.

Screenshot: [continuum comparison](continuum-comparison.jpg).

The primary database retains both original synthetic demos and one native-artifact interoperability check. All three archives passed runtime validation; each has two imported records and zero human decisions. The original demos were not replaced. The QA servers are stopped at handoff; start the app with `launch.cmd` or `launch.ps1`.

## Scope and limitations

- This is a saved-artifact connection, not a live provider integration, live agent runner, direct SOL Edge verifier, or automatic execution/approval path.
- Native intake checks the supported fields needed for conversion. It does not run the full upstream Lens normalizer or independently recompute its scores.
- The existing saved files do not establish exact original inputs, controlled environments, scoring implementation versions, execution timestamps, or explicit data origins. Those facts remain unknown; source labels such as “live” are not verification.
- The interoperability pair contains different engineering scenarios and cannot support a controlled quality-improvement claim. No adoption decision was created.
- Evidence references, mathematical statements, signatures, ledger entries, and physical-performance claims remain upstream source material. The bridge does not verify those claims, issue credentials, or grant actuation authority.
- Source text is retained after decoding. CLI UTF-8 byte identity was checked; browser text decoding may remove a UTF-8 BOM, so browser hashes identify the retained decoded source text.
- A native packet is limited to 1 MB; a converted run remains subject to the existing 5 MB limit. No new archive schema or SQLite migration is required.
- Dedicated benchmark/certificate adapters, producer-side context writers, Lens/Studio handoff controls, and repeat-trial analysis remain proposals in the integration map.
- Existing producer code and live server were not changed or launched. No paid tests, model calls, or cloud actions were performed. Broader sibling test suites were not rerun as a substitute for these focused bridge checks.
