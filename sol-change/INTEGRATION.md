# Integration boundary

`sol-change/` is the Change Observatory’s application root inside `sol-systems/`. Keep its source, schemas, examples, tests, launchers, and default database under this directory. V1 has no dependency on sibling projects or experimental SOL algorithms.

The v0.2.0 bridge consumes saved `techman.sol-lens.proof-packet/v0.2` artifacts from existing continuum workflows. Use the app’s **SOL packets** action or `python -m observatory.continuum`. See [the continuum integration map](docs/CONTINUUM_INTEGRATION.md) for implemented paths, commands, and planned adapters. Other producers can emit schema-1.0 run files directly. Execution stays separate from review and declared provenance is preserved.

## HTTP API

Default base: `http://127.0.0.1:8770`. Write requests use `Content-Type: application/json`. No CORS access is enabled; browser writes must originate from this loopback app. Direct local API clients can omit `Origin`. This API is intentionally unauthenticated and is not intended for network exposure.

| Method | Path | Body / result |
| --- | --- | --- |
| GET | `/api/health` | App and schema version. |
| POST | `/api/continuum/experiments` | `title`, `proposed_change`, `baseline_source_text`, `candidate_source_text`; optional source labels/context objects. Converts two saved primary packet observations and atomically creates a review-pending experiment. |
| GET | `/api/experiments` | Experiment aggregates in latest-update order. |
| POST | `/api/experiments` | Setup object, as in `examples/experiment-setup.json`; creates an experiment. |
| GET | `/api/experiments/{id}` | `{ "experiment": ..., "comparison": ... }`. |
| PATCH | `/api/experiments/{id}` | Full setup object; appends a revision if anything changed. |
| POST | `/api/experiments/{id}/runs` | `{ "source_text": "original JSON text", "source_filename": "run.json", "supersedes_record_id": null, "correction_reason": "" }`. |
| POST | `/api/experiments/{id}/selections` | `{ "baseline": "record ID or null", "candidate": "record ID or null" }`. Actual null is JSON `null`. |
| GET | `/api/experiments/{id}/comparison?revision=1` | Evaluate selected runs against a retained revision. Omit revision for current. |
| POST | `/api/experiments/{id}/decisions` | Decision fields below. Appends a record and freezes the current comparison context. |
| GET | `/api/experiments/{id}/export.json` | Complete portable archive with attachment disposition. |
| GET | `/api/experiments/{id}/report.md` | Human-readable Markdown report. |
| POST | `/api/import-experiment` | `{ "source_text": "complete exported experiment JSON text" }`; validates and creates, never overwrites. |

Successful creations return HTTP 201; reads/updates return 200. Validation returns 422 with `{ "errors": ["field-specific explanation"] }`. Duplicate IDs return 409; unknown records return 404. Nonlocal hosts/cross-origin writes return 403, wrong write content types 415, and oversized bodies 413.

Decision input:

```json
{
  "outcome": "mixed",
  "action": "run_another_experiment",
  "reviewer": "Reviewer name",
  "rationale": "Explain the quality gain, the costs, and remaining uncertainty.",
  "supporting_evidence": ["run-record-id:evidence-id"],
  "unresolved_questions": ["Does the candidate preserve reader usefulness?"]
}
```

Reviewer identity is self-reported. An agent using the API must not impersonate human approval. Automated QA records must be explicitly labeled as tests.

## Python boundary

With `sol-change` on the Python module path:

```python
from observatory.domain import compare, markdown_report, validate_run
from observatory.store import Store

store = Store("path/to/observatory.sqlite3")
experiment = store.get("experiment-id")
comparison = compare(experiment)
report = markdown_report(experiment)
```

The domain layer returns descriptive per-criterion results and limitations. It does not infer a reviewer’s outcome or action. Use `Store` operations rather than editing the database document to preserve run records, revision history, and decision bindings.

## Contract evolution

Schemas are versioned separately from app release `0.2.0` and internal SQLite storage schema `1`. Unsupported import schema versions fail visibly. There is no silent migration. Changes to persisted comparison rules or snapshot shape require an explicit contract/migration strategy so historical decisions stay interpretable. A future integration should include producer version, evaluation version, stable input/conditions, and provenance; it should not equate transport success with verified evidence or human approval.
