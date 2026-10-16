"""Validation, comparisons, and portable reports. No UI or database dependencies."""

from __future__ import annotations

import difflib
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "1.0"
KINDS = ("measured", "human_rating", "automated_assessment")
OUTCOMES = ("improved", "regressed", "inconclusive", "mixed")
ACTIONS = ("adopt", "reject", "run_another_experiment")
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")


class ValidationError(ValueError):
    def __init__(self, errors: list[str] | str):
        self.errors = [errors] if isinstance(errors, str) else errors
        super().__init__("; ".join(self.errors))


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_json(text: str) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValidationError(f"Duplicate JSON key: {key}.")
            result[key] = value
        return result

    try:
        result = json.loads(text.lstrip("\ufeff"), object_pairs_hook=pairs,
                            parse_constant=lambda value: (_ for _ in ()).throw(
                                ValidationError(f"{value} is not a finite JSON number.")))
    except ValidationError:
        raise
    except (ValueError, RecursionError) as exc:
        raise ValidationError(f"Invalid JSON: {exc}") from exc
    if not isinstance(result, dict):
        raise ValidationError("The JSON document must be an object.")
    def finite(value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValidationError("JSON numbers must be finite; an exponent may be too large.")
        if isinstance(value, dict):
            for child in value.values():
                finite(child)
        elif isinstance(value, list):
            for child in value:
                finite(child)
    try:
        finite(result)
    except RecursionError as exc:
        raise ValidationError("JSON nesting is too deep.") from exc
    return result


class Check:
    def __init__(self):
        self.errors: list[str] = []

    def need(self, condition, message):
        if not condition:
            self.errors.append(message)

    def obj(self, value, path, required=(), optional=()):
        if not isinstance(value, dict):
            self.errors.append(f"{path} must be an object.")
            return {}
        for key in required:
            self.need(key in value, f"{path}.{key} is required.")
        for key in value.keys() - set(required) - set(optional):
            self.errors.append(f"{path}.{key} is not supported in schema {SCHEMA_VERSION}.")
        return value

    def string(self, value, path, optional=False, limit=100_000):
        self.need(isinstance(value, str) and len(value) <= limit and (optional or bool(value.strip())),
                  f"{path} must be {'a string' if optional else 'a non-empty string'} (max {limit} characters).")

    def ident(self, value, path):
        self.need(isinstance(value, str) and bool(ID_PATTERN.fullmatch(value)), f"{path} must be a short ID using letters, numbers, dot, dash, or underscore.")

    def number(self, value, path, nullable=False):
        good = value is None and nullable
        if type(value) in (float, int):
            try:
                good = math.isfinite(value) and abs(value) <= 1e100
            except OverflowError:
                good = False
        self.need(good, f"{path} must be a finite number between -1e100 and 1e100{' or null' if nullable else ''}.")

    def timestamp(self, value, path):
        try:
            if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value):
                raise ValueError("Use an RFC 3339 timestamp")
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            self.need(parsed.utcoffset() is not None, f"{path} needs a timezone, for example 2026-10-15T14:00:00Z.")
        except (ValueError, TypeError, AttributeError):
            self.errors.append(f"{path} must include date, time with seconds, and timezone, for example 2026-10-15T14:00:00Z.")

    def array(self, value, path, limit=200):
        self.need(isinstance(value, list) and len(value) <= limit, f"{path} must be an array with at most {limit} entries.")
        return value if isinstance(value, list) else []

    def finish(self):
        if self.errors:
            raise ValidationError(self.errors)


def validate_criteria(criteria: Any, check: Check | None = None, path="criteria"):
    c = check or Check()
    rows = c.array(criteria, path, 30)
    c.need(bool(rows), f"{path} needs at least one criterion.")
    seen = set()
    for index, row in enumerate(rows):
        p = f"{path}[{index}]"
        row = c.obj(row, p, ("id", "label", "unit", "direction", "threshold", "max_regression_percent", "required"))
        c.ident(row.get("id"), f"{p}.id")
        key = row.get("id")
        c.need(isinstance(key, str) and key not in seen, f"{p}.id must be unique.")
        if isinstance(key, str):
            seen.add(key)
        c.string(row.get("label"), f"{p}.label", limit=200)
        c.string(row.get("unit"), f"{p}.unit", limit=40)
        c.need(row.get("direction") in ("higher", "lower"), f"{p}.direction must be higher or lower.")
        c.number(row.get("threshold"), f"{p}.threshold", nullable=True)
        c.number(row.get("max_regression_percent"), f"{p}.max_regression_percent", nullable=True)
        if type(row.get("max_regression_percent")) in (float, int):
            c.need(row["max_regression_percent"] >= 0, f"{p}.max_regression_percent cannot be negative.")
        c.need(type(row.get("required")) is bool, f"{p}.required must be true or false.")
    if check is None:
        c.finish()


SETUP_FIELDS = ("title", "task", "proposed_change", "hypothesis", "intended_improvement", "constraints", "acceptable_tradeoffs", "criteria")


def validate_setup(setup: Any):
    c = Check()
    setup = c.obj(setup, "experiment", SETUP_FIELDS)
    for field in SETUP_FIELDS[:-1]:
        c.string(setup.get(field), f"experiment.{field}", optional=field in ("constraints", "acceptable_tradeoffs"), limit=20_000 if field != "title" else 200)
    validate_criteria(setup.get("criteria"), c)
    c.finish()


RUN_FIELDS = ("schema_version", "kind", "id", "designation", "input", "output", "configuration", "workflow_version", "executed_at", "conditions", "data_type", "measurements", "evidence")


def validate_run(run: Any):
    c = Check()
    run = c.obj(run, "run", RUN_FIELDS)
    c.need(run.get("schema_version") == SCHEMA_VERSION, "run.schema_version must be 1.0.")
    c.need(run.get("kind") == "sol-change/run", "run.kind must be sol-change/run.")
    c.ident(run.get("id"), "run.id")
    c.need(run.get("designation") in ("baseline", "candidate"), "run.designation must be baseline or candidate.")
    c.string(run.get("input"), "run.input")
    c.string(run.get("output"), "run.output", optional=True)
    c.need(isinstance(run.get("configuration"), dict), "run.configuration must be an object.")
    c.need(isinstance(run.get("conditions"), dict), "run.conditions must be an object; use {} when conditions are unknown.")
    c.need(run.get("data_type") in ("imported", "manual", "synthetic"), "run.data_type must be imported, manual, or synthetic.")
    c.need(run.get("workflow_version") is None or isinstance(run.get("workflow_version"), str), "run.workflow_version must be a string or null.")
    c.timestamp(run.get("executed_at"), "run.executed_at")
    evidence = c.array(run.get("evidence"), "run.evidence")
    ids = set()
    for index, item in enumerate(evidence):
        p = f"run.evidence[{index}]"
        item = c.obj(item, p, ("id", "title", "reference", "provenance"))
        c.ident(item.get("id"), f"{p}.id")
        key = item.get("id")
        c.need(isinstance(key, str) and key not in ids, f"{p}.id must be unique.")
        if isinstance(key, str):
            ids.add(key)
        for field in ("title", "reference", "provenance"):
            c.string(item.get(field), f"{p}.{field}", limit=5000)
    seen = set()
    for index, item in enumerate(c.array(run.get("measurements"), "run.measurements")):
        p = f"run.measurements[{index}]"
        item = c.obj(item, p, ("criterion_id", "value", "unit", "method", "evidence_ids"))
        key = item.get("criterion_id")
        c.ident(key, f"{p}.criterion_id")
        c.need(isinstance(key, str) and key not in seen, f"{p}.criterion_id must be unique.")
        if isinstance(key, str):
            seen.add(key)
        c.number(item.get("value"), f"{p}.value", nullable=True)
        c.string(item.get("unit"), f"{p}.unit", limit=40)
        method = c.obj(item.get("method"), f"{p}.method", ("kind", "description", "version"))
        c.need(method.get("kind") in KINDS, f"{p}.method.kind must be measured, human_rating, or automated_assessment.")
        c.string(method.get("description"), f"{p}.method.description", limit=5000)
        c.need(method.get("version") is None or isinstance(method.get("version"), str), f"{p}.method.version must be a string or null.")
        for evidence_id in c.array(item.get("evidence_ids"), f"{p}.evidence_ids"):
            c.need(isinstance(evidence_id, str) and evidence_id in ids, f"{p}.evidence_ids contains an unknown evidence ID.")
    c.finish()


DECISION_FIELDS = ("outcome", "action", "reviewer", "rationale", "supporting_evidence", "unresolved_questions")


def validate_decision(data, evidence_keys):
    c = Check()
    data = c.obj(data, "decision", DECISION_FIELDS)
    c.need(data.get("outcome") in OUTCOMES, "decision.outcome must be improved, regressed, inconclusive, or mixed.")
    c.need(data.get("action") in ACTIONS, "decision.action must be adopt, reject, or run_another_experiment.")
    c.string(data.get("reviewer"), "decision.reviewer", limit=200)
    c.string(data.get("rationale"), "decision.rationale", limit=20_000)
    for key in c.array(data.get("supporting_evidence"), "decision.supporting_evidence"):
        c.need(isinstance(key, str) and key in evidence_keys, "decision.supporting_evidence must reference evidence from the selected runs.")
    for question in c.array(data.get("unresolved_questions"), "decision.unresolved_questions"):
        c.string(question, "decision.unresolved_questions[]", limit=5000)
    c.finish()


def active_record(exp, role):
    return next((r for r in exp["runs"] if r["record_id"] == exp["active_runs"].get(role)), None)


def evidence_keys(exp, run_ids=None):
    selected = set(run_ids or exp["active_runs"].values())
    return {f'{r["record_id"]}:{e["id"]}' for r in exp["runs"] if r["record_id"] in selected for e in r["run"]["evidence"]}


def compare(exp: dict, revision: int | None = None, run_ids: dict | None = None) -> dict:
    target_revision = exp["current_revision"] if revision is None else revision
    rev = next((r for r in exp["criteria_revisions"] if r["revision"] == target_revision), None)
    if rev is None:
        raise ValidationError("Unknown criteria revision.")
    selected = run_ids if run_ids is not None else exp["active_runs"]
    records = {role: next((r for r in exp["runs"] if r["record_id"] == selected.get(role)), None) for role in ("baseline", "candidate")}
    baseline, candidate = (records[role]["run"] if records[role] else None for role in ("baseline", "candidate"))
    warnings, blockers = [], []
    if not baseline or not candidate:
        warnings.append("Import both a baseline and a candidate to compare this experiment.")
    if baseline and candidate:
        if baseline["input"] != candidate["input"]:
            blockers.append("Inputs differ. The runs do not answer the same exact input.")
        if canonical(baseline["conditions"]) != canonical(candidate["conditions"]):
            blockers.append("Comparison conditions differ (dataset, environment, seed, or other declared conditions).")
        elif not baseline["conditions"]:
            warnings.append("Comparison conditions are unknown. Differences are observational; comparability is limited.")
        if (baseline["data_type"] == "synthetic") != (candidate["data_type"] == "synthetic"):
            blockers.append("Synthetic and non-synthetic run data are mixed.")
        if not baseline["workflow_version"] or not candidate["workflow_version"]:
            warnings.append("At least one workflow version is unknown.")
        if not baseline["configuration"] or not candidate["configuration"]:
            warnings.append("At least one run has no configuration recorded.")
    context_messages = {}
    for role, run in (("baseline", baseline), ("candidate", candidate)):
        metadata = (run or {}).get("configuration", {}).get("sol_continuum")
        if not isinstance(metadata, dict) or metadata.get("adapter") != "sol-lens-proof-packet/1.0":
            continue
        messages = metadata.get("context_warnings", [])
        if isinstance(messages, list):
            for message in messages:
                if isinstance(message, str):
                    context_messages.setdefault(message, []).append(role)
    for message, roles in context_messages.items():
        warnings.append(f'{"Both runs" if len(roles) == 2 else roles[0].capitalize()}: {message}')
    metrics = []
    for criterion in rev["criteria"]:
        left = next((m for m in (baseline or {}).get("measurements", []) if m["criterion_id"] == criterion["id"]), None)
        right = next((m for m in (candidate or {}).get("measurements", []) if m["criterion_id"] == criterion["id"]), None)
        row = {"criterion": criterion, "baseline": left, "candidate": right, "delta": None, "percent_change": None,
               "status": "unknown", "threshold_status": "not_set", "guardrail_status": "not_set", "notes": [], "evidence": {}}
        for role, measure in (("baseline", left), ("candidate", right)):
            row["evidence"][role] = [f'{records[role]["record_id"]}:{key}' for key in measure["evidence_ids"]] if measure and records[role] else []
            if measure and measure["value"] is not None and not measure["evidence_ids"]:
                row["notes"].append(f"{role.capitalize()} measurement has no linked evidence; its value is self-reported.")
        missing = [role for role, measure in (("baseline", left), ("candidate", right)) if not measure or measure["value"] is None]
        reasons = list(blockers)
        if missing:
            row["notes"].append(f"Missing measurement: {', '.join(missing)}. Unknown, never zero.")
        if any(m and m["unit"] != criterion["unit"] for m in (left, right)):
            reasons.append("Units are incompatible with each other or the criterion. No implicit conversion is applied.")
        if left and right:
            if left["method"] != right["method"]:
                reasons.append("Evaluation methods differ in kind, description, or version.")
        if reasons:
            row["status"] = "incompatible"
            row["notes"].extend(reasons)
        elif not missing:
            delta = right["value"] - left["value"]
            oriented = delta * (1 if criterion["direction"] == "higher" else -1)
            row.update(delta=delta, status="improved" if oriented > 0 else "regressed" if oriented < 0 else "unchanged")
            if left["value"] == 0:
                row["notes"].append("Zero baseline: percentage change is undefined. Use the absolute difference.")
            else:
                relative = delta / abs(left["value"]) * 100
                if math.isfinite(relative):
                    row["percent_change"] = relative
                else:
                    row["notes"].append("Relative change exceeds the finite numeric range. Use the absolute difference.")
            if criterion["max_regression_percent"] is not None:
                if oriented >= 0:
                    row["guardrail_status"] = "pass"
                elif left["value"] == 0:
                    row["guardrail_status"] = "fail" if criterion["max_regression_percent"] == 0 else "unknown"
                else:
                    row["guardrail_status"] = "pass" if -oriented / abs(left["value"]) * 100 <= criterion["max_regression_percent"] + 1e-10 else "fail"
        if criterion["threshold"] is not None:
            if row["status"] == "incompatible" or not right or right["value"] is None or right["unit"] != criterion["unit"]:
                row["threshold_status"] = "unknown"
            else:
                passed = right["value"] >= criterion["threshold"] if criterion["direction"] == "higher" else right["value"] <= criterion["threshold"]
                row["threshold_status"] = "pass" if passed else "fail"
        if criterion["max_regression_percent"] is not None and row["guardrail_status"] == "not_set":
            row["guardrail_status"] = "unknown"
        metrics.append(row)
    if any(row["status"] == "incompatible" for row in metrics) and not blockers:
        warnings.append("Some criteria have incompatible units or evaluation methods; their differences are withheld.")
    limitations = ["One pair of runs is descriptive evidence only. No statistical significance or repeatability is established.",
                   "Evidence references and provenance are supplied by the importer; source contents have not been fetched or verified.",
                   "The reviewer makes the adoption decision. Criterion checks are not an overall score."]
    if any(r and r["run"]["data_type"] == "synthetic" for r in records.values()):
        limitations.insert(0, "SYNTHETIC DEMONSTRATION: these records are invented examples, not measured results from a real agent.")
    if rev["after_results"]:
        limitations.append("This criteria revision was recorded after runs were imported. Earlier criteria are retained.")
    return {"criteria_revision": rev["revision"], "run_ids": dict(selected), "comparability": "incompatible" if blockers else "incomplete" if not baseline or not candidate else "limited" if warnings else "compatible",
            "warnings": blockers + warnings, "metrics": metrics, "limitations": limitations,
            "counts": {s: sum(row["status"] == s for row in metrics) for s in ("improved", "regressed", "unchanged", "unknown", "incompatible")},
            "output_diff": "\n".join(difflib.unified_diff(baseline["output"].splitlines(), candidate["output"].splitlines(), fromfile="baseline", tofile="candidate", lineterm="")) if baseline and candidate else ""}


def validate_archive(exp: Any):
    """Validate the whole history, including original imports and decision bindings."""
    c = Check()
    exp = c.obj(exp, "archive", ("schema_version", "kind", "id", "created_at", "updated_at", "review_status", "setup", "current_revision", "criteria_revisions", "runs", "active_runs", "decisions"))
    c.need(exp.get("schema_version") == SCHEMA_VERSION and exp.get("kind") == "sol-change/experiment", "Archive must use kind sol-change/experiment and schema_version 1.0.")
    c.ident(exp.get("id"), "archive.id")
    c.timestamp(exp.get("created_at"), "archive.created_at")
    c.timestamp(exp.get("updated_at"), "archive.updated_at")
    c.need(exp.get("review_status") in ("draft", "awaiting_review", "reviewed"), "archive.review_status is invalid.")
    c.finish()
    validate_setup(exp["setup"])
    revisions = c.array(exp["criteria_revisions"], "archive.criteria_revisions")
    numbers = []
    for rev in revisions:
        rev = c.obj(rev, "revision", ("revision", "created_at", "after_results", "criteria", "setup_snapshot"))
        number = rev.get("revision")
        c.need(type(number) is int and number > 0, "revision.revision must be a positive integer.")
        numbers.append(number)
        c.timestamp(rev.get("created_at"), "revision.created_at")
        c.need(type(rev.get("after_results")) is bool, "revision.after_results must be boolean.")
        validate_criteria(rev.get("criteria"), c)
        c.finish()
        validate_setup(rev["setup_snapshot"])
        c.need(rev["criteria"] == rev["setup_snapshot"]["criteria"], "Revision criteria must match its setup snapshot.")
    c.need(numbers == list(range(1, len(numbers) + 1)) and bool(numbers), "Criteria revisions must be consecutive from 1.")
    c.need(type(exp["current_revision"]) is int and exp["current_revision"] == len(numbers), "current_revision must identify the latest criteria revision.")
    if revisions:
        c.need(exp["setup"] == revisions[-1]["setup_snapshot"], "Current setup must match the latest revision snapshot.")
    c.finish()
    records, payload_ids = {}, set()
    for record in c.array(exp["runs"], "archive.runs"):
        record = c.obj(record, "record", ("record_id", "run", "imported_at", "source_filename", "source_text", "sha256", "supersedes_record_id", "correction_reason"))
        c.ident(record.get("record_id"), "record.record_id")
        c.finish()
        c.need(record.get("record_id") not in records, "Duplicate run record ID.")
        c.timestamp(record.get("imported_at"), "record.imported_at")
        c.string(record.get("source_filename"), "record.source_filename", limit=500)
        c.string(record.get("source_text"), "record.source_text", limit=5_000_000)
        c.need(isinstance(record.get("sha256"), str), "record.sha256 must be a string.")
        c.need(record.get("supersedes_record_id") is None or (isinstance(record.get("supersedes_record_id"), str) and record.get("supersedes_record_id") in records), "A correction must reference an earlier run record.")
        c.string(record.get("correction_reason"), "record.correction_reason", optional=not record.get("supersedes_record_id"), limit=5000)
        c.finish()
        validate_run(record["run"])
        original = parse_json(record["source_text"])
        c.need(canonical(original) == canonical(record["run"]) and digest(record["source_text"]) == record["sha256"], "Original run source or its SHA-256 does not match the run record.")
        c.need(record["run"]["id"] not in payload_ids, "Duplicate imported run ID.")
        if record["supersedes_record_id"]:
            c.need(records[record["supersedes_record_id"]]["run"]["designation"] == record["run"]["designation"], "Corrections must retain the original designation.")
        records[record["record_id"]] = record
        payload_ids.add(record["run"]["id"])
    active = c.obj(exp["active_runs"], "active_runs", ("baseline", "candidate"))
    for role, key in active.items():
        c.need(key is None or (isinstance(key, str) and key in records and records[key]["run"]["designation"] == role), f"active_runs.{role} must reference a run with that designation.")
    c.finish()
    decision_ids = set()
    for decision in c.array(exp["decisions"], "archive.decisions"):
        decision = c.obj(decision, "decision record", (*DECISION_FIELDS, "id", "created_at", "criteria_revision", "run_ids", "comparison_snapshot", "setup_snapshot"))
        c.ident(decision.get("id"), "decision.id")
        c.finish()
        c.need(decision.get("id") not in decision_ids, "Duplicate decision ID.")
        decision_ids.add(decision.get("id"))
        c.timestamp(decision.get("created_at"), "decision.created_at")
        c.need(decision.get("criteria_revision") in numbers, "Decision references an unknown criteria revision.")
        bindings = c.obj(decision.get("run_ids"), "decision.run_ids", ("baseline", "candidate"))
        for role, key in bindings.items():
            c.need(isinstance(key, str) and key in records and records[key]["run"]["designation"] == role, "Decision must reference a valid baseline and candidate.")
        c.finish()
        validate_decision({k: decision[k] for k in DECISION_FIELDS}, evidence_keys(exp, bindings.values()))
        snapshot = next(r for r in revisions if r["revision"] == decision["criteria_revision"])
        c.need(decision["setup_snapshot"] == snapshot["setup_snapshot"], "Decision setup must match its criteria revision.")
        c.need(decision["comparison_snapshot"] == compare(exp, decision["criteria_revision"], bindings), "Decision comparison snapshot does not match its bound runs and criteria.")
    if exp["review_status"] == "reviewed":
        c.need(bool(exp["decisions"]), "A reviewed experiment needs a decision.")
        if exp["decisions"]:
            latest = exp["decisions"][-1]
            c.need(latest["criteria_revision"] == exp["current_revision"] and latest["run_ids"] == active, "Reviewed status must refer to the current criteria and selected runs.")
    c.finish()


def number(value):
    return "unknown" if value is None else f"{value:,.4g}"


def md_text(value):
    result = str(value).replace("\\", "\\\\").replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;").replace("\r", "")
    result = re.sub(r"([`*_{}\[\]()#!])", r"\\\1", result)
    return result.replace("\n", "<br>")


def measurement_text(measurement):
    if not measurement or measurement["value"] is None:
        return "unknown"
    return f'{number(measurement["value"])} {md_text(measurement["unit"])}'


def report_configuration(configuration):
    native = configuration.get("sol_continuum")
    if isinstance(native, dict) and "original_source_text" in native:
        metadata = {key: value for key, value in native.items() if key != "original_source_text"}
        metadata["original_source_text"] = "Preserved in the complete JSON export and source-packet download; omitted from this readable configuration summary."
        return {**configuration, "sol_continuum": metadata}
    return configuration


def markdown_report(exp: dict) -> str:
    result = compare(exp)
    setup = exp["setup"]
    lines = [f'# SOL Change Observatory — {md_text(setup["title"])}', "", f'Exported: {now()}',
             f'Experiment: {exp["id"]} · Schema {SCHEMA_VERSION}', f'Review status: {exp["review_status"]} · Criteria revision: {exp["current_revision"]}', "",
             "## Proposed change", "", md_text(setup["proposed_change"]), "", f'**Task:** {md_text(setup["task"])}', "",
             f'**Hypothesis:** {md_text(setup["hypothesis"])}', f'**Intended improvement:** {md_text(setup["intended_improvement"])}',
             f'**Constraints:** {md_text(setup["constraints"]) or "None recorded"}', f'**Acceptable tradeoffs:** {md_text(setup["acceptable_tradeoffs"]) or "None recorded"}', "",
             "## Comparison", "", f'Comparability: **{result["comparability"]}**. No overall score or automatic adoption recommendation.', ""]
    lines += [f'- {md_text(w)}' for w in result["warnings"]]
    lines += ["", "| Criterion | Direction / unit | Baseline | Candidate | Absolute delta | Relative delta | Change | Target check | Regression guardrail | Required |",
              "|---|---|---:|---:|---:|---:|---|---|---|---|"]
    metric_notes = []
    for row in result["metrics"]:
        crit = row["criterion"]
        pct = "undefined (zero baseline)" if row["baseline"] and row["baseline"]["value"] == 0 and row["delta"] is not None else "unknown" if row["percent_change"] is None else number(row["percent_change"]) + "%"
        lines.append(f'| {md_text(crit["label"])} | {crit["direction"]} / {md_text(crit["unit"])} | {measurement_text(row["baseline"])} | {measurement_text(row["candidate"])} | {number(row["delta"])} | {pct} | {row["status"]} | {number(crit["threshold"])}: {row["threshold_status"]} | {number(crit["max_regression_percent"])}%: {row["guardrail_status"]} | {crit["required"]} |')
        for role in ("baseline", "candidate"):
            method = (row[role] or {}).get("method")
            if method:
                metric_notes.append(f'{md_text(crit["label"])} / {role}: {md_text(method["kind"])} — {md_text(method["description"])} (version {md_text(method["version"] or "unknown")}); evidence: {md_text(", ".join(row["evidence"][role])) or "none"}.')
        for note in row["notes"]:
            metric_notes.append(f'{md_text(crit["label"])}: {md_text(note)}')
    lines += ["", "### Measurement methods and notes", ""]
    for note in metric_notes:
        lines += [note, ""]
    lines += ["", "## Run records and evidence", ""]
    for record in exp["runs"]:
        run = record["run"]
        active = record["record_id"] in exp["active_runs"].values()
        lines += [f'### {run["designation"].capitalize()}: {md_text(run["id"])} {"(selected)" if active else "(history)"}', "",
                  f'Data origin: **{run["data_type"]}** · Workflow: {md_text(run["workflow_version"] or "unknown")} · Executed: {run["executed_at"]}',
                  f'Imported: {record["imported_at"]} · File: {md_text(record["source_filename"])}', f'Record: {record["record_id"]} · SHA-256 (source text): `{record["sha256"]}`',
                  f'Correction of: {record["supersedes_record_id"] or "none"} · Reason: {md_text(record["correction_reason"]) or "none"}', "",
                  "Input:", "", md_text(run["input"]), "", "Output:", "", md_text(run["output"]), "",
                  f'Configuration: {md_text(canonical(report_configuration(run["configuration"])))}', f'Conditions: {md_text(canonical(run["conditions"]))}', ""]
        for item in run["evidence"]:
            lines.append(f'- **{record["record_id"]}:{item["id"]}** — {md_text(item["title"])}; reference: {md_text(item["reference"])}; provenance: {md_text(item["provenance"])}')
    lines += ["", "## Criteria revision history", ""]
    for rev in exp["criteria_revisions"]:
        lines.append(f'- Revision {rev["revision"]} · {rev["created_at"]} · After results imported: {rev["after_results"]}')
        for crit in rev["criteria"]:
            lines.append(f'  - {md_text(crit["label"])} ({crit["id"]}): {crit["direction"]} {md_text(crit["unit"])}, target {number(crit["threshold"])}, max regression {number(crit["max_regression_percent"])}%, required {crit["required"]}')
    lines += ["", "## Human decision history", ""]
    if not exp["decisions"]:
        lines.append("Awaiting human review. No decision has been recorded.")
    for decision in exp["decisions"]:
        current = decision["criteria_revision"] == exp["current_revision"] and decision["run_ids"] == exp["active_runs"]
        lines += [f'### {decision["outcome"].capitalize()} → {decision["action"].replace("_", " ")}', "",
                  f'Reviewer (self-reported): {md_text(decision["reviewer"])} · {decision["created_at"]}',
                  f'Criteria revision: {decision["criteria_revision"]} · Applies to current comparison: {current}',
                  f'Baseline record: {decision["run_ids"]["baseline"]} · Candidate record: {decision["run_ids"]["candidate"]}', "",
                  md_text(decision["rationale"]), "", f'Supporting evidence: {md_text(", ".join(decision["supporting_evidence"])) or "None selected"}', "",
                  "Remaining questions:"]
        lines.extend(f'- {md_text(q)}' for q in decision["unresolved_questions"])
        if not decision["unresolved_questions"]:
            lines.append("None recorded.")
    lines += ["", "## Limitations", "", *[f'- {md_text(item)}' for item in result["limitations"]], "",
              "The JSON export preserves original run source text, every revision, and each decision's complete comparison and setup snapshots.", ""]
    return "\n".join(lines)
