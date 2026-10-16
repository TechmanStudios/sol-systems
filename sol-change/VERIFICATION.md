# Verification — SOL Change Observatory v0.1.0

Verified locally on Windows on October 15, 2026. All application files are rooted in `C:\sol-systems\sol-change`; sibling SOL projects were not changed by this build.

## Automated checks

**81 tests passed; 0 failures, 0 errors.** The final run took 8.501 seconds on this machine. The full local log is `test-results/unittest.txt` (ignored by Git).

```text
python -m unittest discover -s tests -v
node --check static/app.js
```

The JavaScript syntax check also passed. The app itself has no Node runtime requirement.

| Area | Verified behavior |
| --- | --- |
| Metric rules | Higher/lower direction, equality, inclusive targets, inclusive regression guardrails, distinct target/guardrail results. |
| Unknowns | Null and omitted measurements remain unknown; missing baseline does not become zero; candidate absolute targets can still be checked independently. |
| Numeric boundaries | Zero baselines, negative baselines, tiny baselines that would overflow relative change, undefined relative guardrails. |
| Comparability | Input changes, declared-condition changes, boolean/integer condition distinctions, incompatible units, method versions and assessment kinds, synthetic/non-synthetic mixtures. |
| Imports | Malformed JSON, duplicate keys, unsupported schemas/fields, non-finite values, malformed nested shapes, duplicate run/evidence/measurement IDs, broken evidence references, timestamps without timezone. |
| Original records | Original decoded text including CRLF/BOM when supplied through the Python API, source-text hashes, correction links/reasons, duplicate-ID conflicts without overwrite. |
| History | Setup revisions after results, old criterion checks, preserved decision snapshots and evidence bindings, changes returning an experiment to review. |
| Persistence | Reopening SQLite, transactional concurrent imports, demo seeding once, and two actual fresh server process launches reading the same saved decision. |
| Round trips | Complete JSON export/import into a separate database, preserving revisions, original imports, and human decision records. |
| Reports | Contiguous Markdown tables, measurement methods and actual units, evidence/provenance, decision history, unknowns, limitations, escaped imported image syntax. |
| HTTP | Complete create/import/compare/decide/export journey, JSON errors, downloadable examples/schemas, local-only hosts and write origins, restricted static paths and content security policy. |

## Actual browser walkthrough

Used the Codex in-app browser against the running local application, with an isolated QA database at `test-results/browser/observatory.sqlite3` on port 8766. QA records are explicitly labeled **Codex QA test — not a human approval**. The primary database retains two synthetic demos awaiting the owner’s review and has no seeded human decisions.

Completed these actions through the actual interface:

1. Created an experiment, including task, change, hypothesis, intended improvement, constraints, tradeoffs, and four criteria.
2. Submitted an invalid run and observed field-specific validation errors.
3. Selected and imported the baseline and candidate JSON files through the file chooser.
4. Inspected citation support `68% → 92%`, duration `78 s → 112 s`, cost `$0.24 → $0.38`, and the unmeasured candidate usefulness rating.
5. Confirmed the cost absolute target passes while its maximum percentage regression fails.
6. Followed a metric’s evidence button to the corresponding source reference and provenance.
7. Recorded a mixed QA outcome, action to run another experiment, rationale, two supporting references, and two unresolved questions.
8. Downloaded the actual Markdown report and JSON archive through the browser. Inspected the downloaded Markdown content locally.
9. Stopped and restarted the QA application, reloaded the page, and confirmed the saved reviewer/rationale and decision history remained visible.
10. Revised the cost target after results; observed criteria revision 2, then selected revision 1 and confirmed the original target/result remained inspectable. The earlier decision was preserved and flagged as applying to an earlier comparison.
11. Opened the incompatible fixture and confirmed the input/condition warnings and withheld numerical differences.
12. Checked layouts at desktop `1440 × 1000` and mobile `390 × 844`. The document did not overflow horizontally; the measurement table scrolls within its own container on mobile. Confirmed the mobile import guide remains available.
13. Activated the keyboard skip link and verified focus moved to `main` without changing the experiment route. Checked browser console output: no reported warnings or errors in the inspected session.

The PowerShell launcher was also used to start the primary app successfully. Temporary viewport overrides were reset after inspection. QA servers are stopped at handoff; launch with `launch.cmd` or `launch.ps1` to resume.

Screenshots: [desktop comparison](docs/comparison-desktop.jpg), [mobile comparison](docs/comparison-mobile.jpg).

## Evidence boundaries and remaining limits

- Both delivered demos are invented fixtures, not measurements from real agent runs. QA decisions establish application behavior only; they are not a human adoption decision or source verification.
- V1 compares a single selected pair and makes no statistical-significance or repeatability claim.
- Evidence references and provenance are retained as supplied. Their contents are never automatically fetched or verified. Reviewer names are self-reported.
- Numeric targets and regression guardrails are checked. Prose constraints and acceptable tradeoffs require human interpretation.
- Exact unit matching is supported; conversion is deliberately absent. The tool also cannot detect undeclared confounders.
- The JSON Schema files document the v1.0 contracts; the runtime performs additional semantic validation. No third-party JSON Schema validator is required by the app or test suite.
- Browser checks covered the local in-app Chromium interface and two viewport sizes. This is not a cross-browser or complete assistive-technology certification.
- Experiments support at most 30 criteria, 200 setup revisions, 200 imports, and 200 decisions. Run files are capped at 5 MB and HTTP bodies at 10 MB. SQLite is a local store, not a multi-user synchronization service.
- Authentication, network/cloud deployment, live agent execution, provider integrations, and repeated-trial analysis are outside v0.1.0.
