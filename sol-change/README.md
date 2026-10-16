# SOL Change Observatory

A local workspace for comparing two agent workflow runs, following the evidence, and recording a human decision. The application root is **`C:\sol-systems\sol-change`**. It is self-contained for later integration with the rest of `sol-systems`.

SOL is the project name. This application does not implement experimental SOL algorithms, execute agents, or call model providers.

**SOL continuum integration (v0.2.0):** use **SOL packets** to import two saved SOL Lens v0.2 observations, retaining original sources and missing-context warnings. The default port is now **8770**, so the existing SOL live server can keep **8765**. See [the integration map](docs/CONTINUUM_INTEGRATION.md), [Gemini handoff](docs/GEMINI_HANDOFF.md), and [integration verification](docs/CONTINUUM_VERIFICATION.md).

## Launch

On Windows, double-click **`launch.cmd`**, or run from PowerShell:

```powershell
cd C:\sol-systems\sol-change
.\launch.ps1
```

Open **http://127.0.0.1:8770**. The launcher opens the browser automatically; `-NoBrowser` disables that. Stop the server with Ctrl+C. Restarting with the same database preserves experiments, run imports, criteria revisions, and decisions.

Python **3.11 or later** is the only requirement. There are no third-party runtime packages, install step, build step, external accounts, paid API calls, CDN assets, or remote fonts. The Windows launcher uses `python` when available, otherwise the local Codex bundled Python runtime. You can set `SOL_CHANGE_PYTHON` to an explicit Python executable.

Other platforms, or an explicit interpreter:

```text
python app.py --open
```

If port 8770 is occupied:

```powershell
.\launch.ps1 -Port 8767
```

For a clean, isolated workspace without demo seeding:

```text
python app.py --no-demo --db data/my-experiments.sqlite3 --port 8767
```

## Try the complete journey

1. Open **A better sourced research agent**, the populated synthetic example. Citation support rises from 68% to 92%; time rises from 78 to 112 seconds; cost rises from $0.24 to $0.38; candidate reader usefulness is unmeasured. Cost meets the absolute $0.50 target but exceeds the allowed 50% regression. Every number and reference in this example is invented.
2. Inspect the metric methods, side-by-side outputs, text diff, and linked evidence references. The second example, **When the comparison breaks**, deliberately changes inputs, source packets, and evaluation methods to demonstrate the warning.
3. Choose **Record decision**. Select an outcome and an action separately, identify the reviewer, explain the judgment, select supporting references, and record remaining questions. No verdict or action is selected for you.
4. Export **Report** for a readable Markdown record, and **JSON** for the complete archive. Restart the server and reopen the decision to verify it remains saved.
5. To create your own experiment, choose **New experiment**, enter a task and hypothesis, define criteria, and import baseline and candidate files. The downloadable examples are also in `examples/`.

Review status (`draft`, `awaiting_review`, `reviewed`) is separate from the reviewer’s outcome (`improved`, `regressed`, `inconclusive`, `mixed`). The action is `adopt`, `reject`, or `run_another_experiment`.

## Import format

Run files use `kind: "sol-change/run"` and `schema_version: "1.0"`. See [the baseline example](examples/baseline.json), [candidate example](examples/candidate.json), [incompatible candidate](examples/incompatible-candidate.json), and [run schema](schemas/run.schema.json).

Required run fields:

| Field | Meaning |
| --- | --- |
| `id`, `designation` | Unique run ID; `baseline` or `candidate`. |
| `input`, `output` | Original text. An empty output is valid; missing input is not. |
| `configuration` | Relevant workflow settings. Differences here are allowed: they can describe the proposed change. |
| `workflow_version` | Model or workflow version string, or `null` when unknown. |
| `executed_at` | Timestamp with date, seconds, and timezone, such as `2026-10-15T14:00:00Z`. |
| `conditions` | Dataset, source packet, environment, seed, and other comparison controls. Use `{}` when unknown; the app warns. |
| `data_type` | `imported`, `manual`, or `synthetic`. This is the origin declared by the author; the import timestamp separately records intake. |
| `measurements` | Array of criterion IDs, numeric values or `null`, exact units, methods, and evidence IDs. An absent measurement is unknown. |
| `evidence` | Array of IDs, titles, references, and provenance descriptions. References remain text. |

One measurement:

```json
{
  "criterion_id": "citation_support",
  "value": 92,
  "unit": "%",
  "method": {
    "kind": "automated_assessment",
    "description": "Supported factual claims divided by 50 claims using a frozen source packet and rubric.",
    "version": "claim-audit/1"
  },
  "evidence_ids": ["citation-audit"]
}
```

Methods distinguish `measured`, `human_rating`, and `automated_assessment`. Method descriptions and versions must match between runs for that criterion’s differences to be shown. Referenced evidence IDs must exist in the same run. No measurement is assumed to be independent source verification.

The import dialog accepts a UTF-8 file or pasted JSON. It rejects malformed JSON, duplicate keys, non-finite numbers, unsupported fields and schema versions, duplicate run IDs, broken evidence references, and invalid timestamps. Unsupported fields are rejected rather than silently discarded. Run files are limited to 5 MB; HTTP request bodies to 10 MB.

Original decoded source text, source filename, import timestamp, and SHA-256 of the UTF-8 source text are retained. The hash identifies that text; it is not a digital signature or proof of source authenticity. Browser text decoding can normalize a UTF-8 BOM, so the hash is explicitly a **source-text** hash rather than a byte-for-byte file checksum.

To correct a record, import a file with a new run ID, select **Correction of…**, and explain the correction. The old record stays in history. Use the run selectors to revisit earlier records. Each import becomes the selected run for its designation.

## Comparison rules

- Missing or null values remain **unknown**, with no delta. A known candidate can still be checked against an absolute target when baseline is missing.
- Units must match the criterion exactly. There is no implicit conversion between seconds and milliseconds, percentages and fractions, or currencies.
- Higher/lower direction determines improvement. Targets are inclusive. `max_regression_percent` bounds deterioration relative to the magnitude of baseline; zero forbids deterioration. A blank setting means unset.
- Percentage change is `(candidate - baseline) / abs(baseline) * 100`. A zero baseline produces an absolute delta and no percentage. An unrepresentably large relative change also remains undefined. `%` metric deltas are labeled percentage points in the UI.
- If a zero baseline regresses, a zero-tolerance guardrail fails; a positive percentage allowance is unknown because its relative basis is undefined.
- Different inputs, declared conditions, or a mixture of synthetic and non-synthetic data block direct comparison. Different measurement methods or units block the affected criteria. Unknown conditions and missing metadata produce warnings.
- Individual regressions can still fit a user-defined tradeoff. Target and guardrail checks stay separate. There is no weighted aggregate score, statistical-significance claim, or automatic adoption recommendation.

## History, persistence, and exports

SQLite data defaults to **`sol-change/data/observatory.sqlite3`** and is ignored by Git. All writes use transactions. Run records and decisions are append-only through the app; setup edits append a new criteria revision with a complete setup snapshot. Revisions made after any imports are explicitly flagged. Editing setup or changing selected runs returns the experiment to review without erasing earlier decisions.

Every decision stores its criteria revision, exact selected run record IDs, supporting evidence IDs, complete comparison snapshot, and setup snapshot. Reviewer names and provenance are self-reported; the app has no identity verification.

JSON exports use `kind: "sol-change/experiment"` and schema version `1.0`. They preserve the complete aggregate, including original run source text. [The experiment schema](schemas/experiment.schema.json) is self-contained. Runtime validation additionally checks cross-record references, source hashes, revision continuity, and decision snapshot consistency. Import an archive into a fresh database to restore it; an existing experiment ID causes a clear conflict and is never overwritten.

Markdown reports include task, hypothesis, constraints, tradeoffs, criterion checks, metric methods, every run and its evidence/provenance, revision history, decision history, unresolved questions, and limitations. Imported Markdown/image syntax is escaped. References are never fetched, embedded as remote images, or executed.

To back up the whole workspace, stop the server before copying `data/`. Alternatively, export individual experiments as JSON while the server runs. SQLite uses WAL mode; copying only the main database during a write may omit recent changes.

## Architecture and integration

| Path | Responsibility |
| --- | --- |
| `observatory/domain.py` | Pure validation, comparison rules, and Markdown reporting. No UI or database dependencies. |
| `observatory/store.py` | SQLite persistence, append-only history, atomic mutations, archive intake. |
| `observatory/fixtures.py` | Explicitly invented demonstration data. |
| `app.py` | Local HTTP API and static file serving, bound only to `127.0.0.1`. |
| `static/` | Buildless browser interface: experiment list, setup, comparison, decision. |
| `schemas/`, `examples/` | Versioned contracts and portable fixtures. |
| `tests/` | Domain, import/export, persistence, concurrency, and HTTP tests. |

Python’s standard library plus SQLite keeps the initial local tool easy to run and integrate. Vanilla JavaScript modules avoid a second runtime/build pipeline. All assets ship locally. The pure domain functions, documented JSON format, and HTTP API are the integration boundaries; sibling SOL projects are not imported or modified. See [INTEGRATION.md](INTEGRATION.md) for endpoint details.

The server checks loopback hosts and write origins, serves only explicitly allowed static directories, requires JSON for writes, and applies a restrictive content security policy. It is a local development application, not an authenticated or multi-user network service. Other local processes with filesystem access can read or change its database.

## Verify

From the project root:

```text
python -m unittest discover -s tests -v
node --check static/app.js
```

Node is optional and used only for this JavaScript syntax check. The app itself needs only Python and a modern browser. Tests use temporary databases and no external accounts, API calls, or network services beyond loopback.

Regenerate the committed fixtures or schemas when intentionally changing their source:

```text
python scripts/generate_examples.py
python scripts/generate_schemas.py
```

See [VERIFICATION.md](VERIFICATION.md) for the completed browser walkthrough and observed limits.

The initial verification record documents v0.1.0 at its former port. Current v0.2.0 integration checks are recorded separately in [CONTINUUM_VERIFICATION.md](docs/CONTINUUM_VERIFICATION.md).

## V1 boundaries

One selected baseline/candidate pair is evaluated at a time. Evidence contents are not collected or verified. Constraints written in prose require human interpretation; numeric criterion thresholds and guardrails are the checks the app can apply. Experiments support up to 30 criteria, 200 setup revisions, 200 run records, and 200 decisions. Large archive imports remain subject to the HTTP size limit.

Authentication, cloud deployment, provider integrations, live execution, automated experiment recommendations, and statistical analysis of repeated trials are deferred. Repeated trials are the next natural step after this local review loop.
