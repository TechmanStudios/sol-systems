"""Emit self-contained Draft 2020-12 contracts. Runtime enforces cross-record invariants too."""
import copy
import json
from pathlib import Path


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def arr(items, maximum=200, minimum=0):
    return {"type": "array", "items": items, "maxItems": maximum, "minItems": minimum}


def enum(*values):
    return {"enum": list(values)}


def text(maximum=100_000, empty=False):
    result = {"type": "string", "maxLength": maximum}
    if not empty:
        result.update(minLength=1, pattern=r"\S")
    return result


ID = {"type": "string", "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$"}
STAMP = {"type": "string", "format": "date-time", "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"}
NUMBER = {"type": "number", "minimum": -1e100, "maximum": 1e100}
NULLABLE = {"anyOf": [NUMBER, {"type": "null"}]}
NULL_ID = {"anyOf": [ID, {"type": "null"}]}
BOOL = {"type": "boolean"}
REVISION = {"type": "integer", "minimum": 1}
FREE_OBJECT = {"type": "object"}
CRITERION = obj({"id": ID, "label": text(200), "unit": text(40), "direction": enum("higher", "lower"),
                 "threshold": NULLABLE, "max_regression_percent": {"anyOf": [{"type": "number", "minimum": 0, "maximum": 1e100}, {"type": "null"}]}, "required": BOOL})
SETUP = obj({**{name: text(200 if name == "title" else 20_000, name in ("constraints", "acceptable_tradeoffs"))
                for name in ("title", "task", "proposed_change", "hypothesis", "intended_improvement", "constraints", "acceptable_tradeoffs")}, "criteria": arr(CRITERION, 30, 1)})
METHOD = obj({"kind": enum("measured", "human_rating", "automated_assessment"), "description": text(5000), "version": {"type": ["string", "null"]}})
MEASUREMENT = obj({"criterion_id": ID, "value": NULLABLE, "unit": text(40), "method": METHOD, "evidence_ids": arr(ID)})
EVIDENCE = obj({"id": ID, "title": text(5000), "reference": text(5000), "provenance": text(5000)})
RUN = obj({"schema_version": {"const": "1.0"}, "kind": {"const": "sol-change/run"}, "id": ID, "designation": enum("baseline", "candidate"),
           "input": text(), "output": text(empty=True), "configuration": FREE_OBJECT, "workflow_version": {"type": ["string", "null"]},
           "executed_at": STAMP, "conditions": FREE_OBJECT, "data_type": enum("imported", "manual", "synthetic"),
           "measurements": arr(MEASUREMENT), "evidence": arr(EVIDENCE)})
BINDINGS = obj({"baseline": NULL_ID, "candidate": NULL_ID})
DECISION_BINDINGS = obj({"baseline": ID, "candidate": ID})
METRIC = obj({"criterion": CRITERION, "baseline": {"anyOf": [MEASUREMENT, {"type": "null"}]}, "candidate": {"anyOf": [MEASUREMENT, {"type": "null"}]},
              "delta": {"type": ["number", "null"], "minimum": -2e100, "maximum": 2e100}, "percent_change": {"type": ["number", "null"]}, "status": enum("improved", "regressed", "unchanged", "unknown", "incompatible"),
              "threshold_status": enum("not_set", "pass", "fail", "unknown"), "guardrail_status": enum("not_set", "pass", "fail", "unknown"),
              "notes": arr(text()), "evidence": obj({"baseline": arr(text()), "candidate": arr(text())})})
COMPARISON = obj({"criteria_revision": REVISION, "run_ids": BINDINGS, "comparability": enum("compatible", "limited", "incomplete", "incompatible"),
                  "warnings": arr(text()), "metrics": arr(METRIC, 30), "limitations": arr(text()),
                  "counts": obj({name: {"type": "integer", "minimum": 0} for name in ("improved", "regressed", "unchanged", "unknown", "incompatible")}), "output_diff": text(400_000, True)})
DECISION = obj({"outcome": enum("improved", "regressed", "inconclusive", "mixed"), "action": enum("adopt", "reject", "run_another_experiment"),
               "reviewer": text(200), "rationale": text(20_000), "supporting_evidence": arr(text()), "unresolved_questions": arr(text(5000)),
               "id": ID, "created_at": STAMP, "criteria_revision": REVISION, "run_ids": DECISION_BINDINGS, "comparison_snapshot": COMPARISON, "setup_snapshot": SETUP})
RECORD = obj({"record_id": ID, "run": RUN, "imported_at": STAMP, "source_filename": text(500), "source_text": text(5_000_000), "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
              "supersedes_record_id": NULL_ID, "correction_reason": text(5000, True)})
EXPERIMENT = obj({"schema_version": {"const": "1.0"}, "kind": {"const": "sol-change/experiment"}, "id": ID,
                  "created_at": STAMP, "updated_at": STAMP, "review_status": enum("draft", "awaiting_review", "reviewed"), "setup": SETUP,
                  "current_revision": REVISION, "criteria_revisions": arr(obj({"revision": REVISION, "created_at": STAMP, "after_results": BOOL, "criteria": arr(CRITERION, 30, 1), "setup_snapshot": SETUP}), 200, 1),
                  "runs": arr(RECORD), "active_runs": BINDINGS, "decisions": arr(DECISION)})

if __name__ == "__main__":
    folder = Path(__file__).resolve().parents[1] / "schemas"
    folder.mkdir(exist_ok=True)
    for name, schema in (("run", RUN), ("experiment", EXPERIMENT)):
        contract = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": f"SOL Change Observatory {name} v1.0",
                    "description": "The runtime additionally validates evidence references, unique IDs, revision continuity, original source hashes, and decision snapshot bindings.", **copy.deepcopy(schema)}
        (folder / f"{name}.schema.json").write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    print("Generated self-contained run and experiment schemas (v1.0).")
