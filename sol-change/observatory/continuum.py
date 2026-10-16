"""Offline artifact bridge for the SOL continuum. Never executes a sibling project."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

from .domain import (Check, ValidationError, canonical, compare, digest, markdown_report,
                     now, parse_json, validate_archive, validate_run)
from .store import ConflictError, Store

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKET_SCHEMA = "techman.sol-lens.proof-packet/v0.2"
ADAPTER_VERSION = "sol-lens-proof-packet/1.0"
MAX_PACKET_BYTES = 1_000_000
METRICS = (("evidence", "Evidence support", "higher"), ("coherence", "Coherence", "higher"),
           ("contradiction", "Contradiction", "lower"), ("continuity", "Continuity", "higher"),
           ("authority", "Authority", "higher"), ("faithfulness", "Faithfulness", "higher"))
COMPONENTS = (
    ("sol", "Research kernel and diagnostics", "Native run JSON; benchmark adapter needs an explicit metric/units contract", "sol/diagnostics/telemetry_emitter.py"),
    ("Frontier_OS", "Agent orchestration and experimental dynamics", "Shared proof packets where emitted; dedicated benchmark adapter remains planned", "Frontier_OS/core/telemetry_hook.py"),
    ("sol-decide", "Trade studies and decision program outputs", "Proof-packet v0.2 intake implemented", "sol-decide/sol_decide/core/serialization.py"),
    ("sol-edge", "Pre-execution eligibility policy and replay", "Policy evidence retained through packets; direct event replay verification remains separate", "sol-edge/README.md"),
    ("sol-lens", "Observable trace and packet review", "Proof-packet v0.2 intake implemented", "sol-lens/lib/packet-schema.ts"),
    ("sol-studio", "Spatial visualization and live server client", "Saved packet handoff implemented; automatic UI navigation/export remains planned", "sol-studio/app.js"),
    ("sol-change", "Version comparison and human review", "Consumer: run/experiment schema 1.0; local port 8770", "sol-change/INTEGRATION.md"),
    ("conJecture", "Formal research notes and theorem corpus", "Evidence references; dedicated certificate adapter remains planned", "conJecture/FORMAL_THEOREMS_CORPUS.md"),
    ("synThesis", "Cross-repository research synthesis", "Evidence references; no numerical adapter inferred", "synThesis/SOL_cross_repo_synthesis_2026-09-05/manifest.json"),
)


def read_artifact(path: Path):
    """Read a named local file once, retaining exact decoded text and byte identity."""
    if not path.is_file():
        raise ValidationError(f"Local artifact not found: {path}")
    if path.stat().st_size > MAX_PACKET_BYTES:
        raise ValidationError("Native packet intake is limited to 1 MB so the portable run can retain the full source.")
    raw = path.read_bytes()
    if len(raw) > MAX_PACKET_BYTES:
        raise ValidationError("Native packet exceeds 1 MB.")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("Native artifacts must be UTF-8 JSON.") from exc
    return text, hashlib.sha256(raw).hexdigest()


def validate_context(context):
    c = Check()
    context = c.obj(context, "observatory_context", ("schema_version",),
                    ("input", "conditions", "evaluator_version", "workflow_version", "executed_at", "data_type"))
    c.need(context.get("schema_version") == "1.0", "observatory_context.schema_version must be 1.0.")
    for field in ("input", "evaluator_version", "workflow_version"):
        if field in context:
            c.string(context[field], f"observatory_context.{field}", limit=100_000 if field == "input" else 500)
    if "conditions" in context:
        c.need(isinstance(context["conditions"], dict), "observatory_context.conditions must be an object.")
    if "executed_at" in context:
        c.timestamp(context["executed_at"], "observatory_context.executed_at")
    if "data_type" in context:
        c.need(context["data_type"] in ("imported", "manual", "synthetic"), "observatory_context.data_type must be imported, manual, or synthetic.")
    c.finish()


def packet_to_run(source_text: str, designation: str, source_label="packet.json", context=None) -> dict:
    """Convert only the packet's primary observation, never its counterfactual baseline."""
    if designation not in ("baseline", "candidate"):
        raise ValidationError("Choose baseline or candidate for this saved packet's primary observation.")
    if not isinstance(source_text, str) or len(source_text.encode("utf-8")) > MAX_PACKET_BYTES:
        raise ValidationError("Native packet must be UTF-8 JSON smaller than 1 MB.")
    if not isinstance(source_label, str) or not source_label.strip() or len(source_label) > 500:
        raise ValidationError("Source label must be a non-empty string of at most 500 characters.")
    packet = parse_json(source_text)
    if packet.get("schema") != PACKET_SCHEMA:
        raise ValidationError(f"Supported native packet schema: {PACKET_SCHEMA}. Use run schema 1.0 for other producers.")
    c = Check()
    for field in ("packet_id",):
        c.string(packet.get(field), f"packet.{field}", limit=5000)
    if "fixture" in packet:
        c.string(packet["fixture"], "packet.fixture", limit=5000)
    c.need(packet.get("observable_trace_only") is True, "packet.observable_trace_only must be true for the supported observable packet contract.")
    c.timestamp(packet.get("generated_at"), "packet.generated_at")
    evaluation = packet.get("evaluation") if isinstance(packet.get("evaluation"), dict) else {}
    normalized = isinstance(evaluation.get("metrics"), dict)
    metrics = evaluation["metrics"] if normalized else packet.get("metrics")
    metric_pointer = "/evaluation/metrics" if normalized else "/metrics"
    c.need(isinstance(metrics, dict), "packet.metrics must be an object. No values are read from baseline_evaluation.")
    logons = packet.get("logons")
    c.need(isinstance(logons, list) and len(logons) <= 1000, "packet.logons must be an array of at most 1000 observations.")
    c.finish()
    for name, _, _ in METRICS:
        value = metrics.get(name)
        c.number(value, f"packet.metrics.{name}", nullable=True)
        if type(value) in (int, float):
            c.need(0 <= value <= 1, f"packet.metrics.{name} must be between 0 and 1; scores are not percentages.")
    for index, logon in enumerate(logons):
        c.need(isinstance(logon, dict), f"packet.logons[{index}] must be an object.")
    c.finish()
    embedded = packet.get("observatory_context")
    if embedded is not None:
        validate_context(embedded)
    if context is not None:
        validate_context(context)
        if embedded is not None and canonical(context) != canonical(embedded):
            raise ValidationError("Sidecar context conflicts with embedded observatory_context. Correct the source explicitly.")
    context = context if context is not None else embedded or {"schema_version": "1.0"}
    warnings = []
    evaluator_version = context.get("evaluator_version") or evaluation.get("scoring_profile")
    if evaluator_version is not None:
        c.string(evaluator_version, "evaluation.scoring_profile", limit=500)
        c.finish()
    if not context.get("input"):
        warnings.append("Original execution input is not recorded; the input field contains only the packet's scenario label.")
    if not context.get("conditions"):
        warnings.append("Dataset, seed, environment, and other controlled execution conditions are not recorded.")
    if not evaluator_version:
        warnings.append("Scoring implementation/version is not recorded. Metrics are producer-reported assessments, not independently re-evaluated results.")
    if normalized and isinstance(packet.get("metrics"), dict) and canonical(packet["metrics"]) != canonical(metrics):
        warnings.append("Top-level claimed scores differ from evaluation.metrics. Only evaluation.metrics is selected; both remain in the original source.")
    if not context.get("executed_at"):
        warnings.append("Execution timestamp is unknown; the displayed timestamp is the packet's generated_at time.")
    if not context.get("data_type"):
        warnings.append("Original data origin is undeclared. Imported is an intake label, not proof that the contents are measured or non-synthetic.")
    source_hash = digest(source_text)
    upstream_verdict = evaluation.get("verdict", packet.get("verdict"))
    provenance = {"adapter": ADAPTER_VERSION, "source_schema": PACKET_SCHEMA, "source_packet_id": packet["packet_id"],
                  "source_label": source_label, "sha256_source_text": source_hash,
                  "sha256_source_utf8_bytes": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
                  "original_source_text": source_text, "context": context,
                  "context_warnings": warnings, "timestamp_basis": "execution" if context.get("executed_at") else "packet_generated_at",
                  "counterfactual_baseline_present": "baseline_evaluation" in packet,
                  "counterfactual_baseline_imported": False,
                  "upstream_verdict": upstream_verdict, "source_verification": "not_performed", "metric_pointer": metric_pointer}
    evidence = [{"id": "packet-source", "title": "Original SOL continuum proof packet", "reference": f"sha256:{source_hash}#",
                 "provenance": f"Local source {source_label}; full original UTF-8 text retained in configuration.sol_continuum.original_source_text. This is a content identity, not a signature or independent verification."}]
    measurements = []
    for name, label, _ in METRICS:
        evidence_id = f"metric-{name}"
        evidence.append({"id": evidence_id, "title": f"Producer-reported {label.lower()} score", "reference": f"sha256:{source_hash}#{metric_pointer}/{name}",
                         "provenance": f"Read directly from {metric_pointer}/{name} in {source_label}. SOL Lens aggregate assessment on a 0–1 scale; not a physical measurement or an external source audit."})
        measurements.append({"criterion_id": f"lens_{name}", "value": metrics.get(name), "unit": "score/1",
                             "method": {"kind": "automated_assessment", "description": f"Producer-reported SOL Lens {metric_pointer}/{name} aggregate; no independent recomputation.", "version": evaluator_version},
                             "evidence_ids": [evidence_id] if metrics.get(name) is not None else []})
    for key, unit, kind in (("execution_time", "s", "measured"), ("cost", "USD", "measured"), ("human_review", "rating/5", "human_rating")):
        measurements.append({"criterion_id": key, "value": None, "unit": unit,
                             "method": {"kind": kind, "description": "Not captured by the supported proof-packet intake contract.", "version": None}, "evidence_ids": []})
    scenario = packet.get("fixture", "Unnamed scenario")
    output = ["IMPORTED SOL CONTINUUM OBSERVATION — UNVERIFIED SOURCE CLAIMS", "", f"Scenario: {scenario}",
              f"Packet: {packet['packet_id']}", f"Upstream verdict (not a human decision or execution authorization): {canonical(upstream_verdict)}", "",
              f"This run contains only the packet's primary {metric_pointer} observation.",
              "The embedded baseline_evaluation, if any, is retained as source material and is not imported as an independently executed baseline.",
              "Time, cost, and independent human review remain unmeasured.", "", *warnings, "", "Observable packet trace:"]
    for index, logon in enumerate(logons):
        output.append(f"[{index}] {logon.get('label', '(unlabeled)')}: {logon.get('detail', '')}")
    models = packet.get("models") if isinstance(packet.get("models"), dict) else {}
    version = context.get("workflow_version") or models.get("candidate")
    if not isinstance(version, str):
        version = None
    run = {"schema_version": "1.0", "kind": "sol-change/run", "id": f"continuum-{designation}-{source_hash[:20]}-{digest(canonical(context))[:8]}",
           "designation": designation,
           "input": context.get("input") or f"Original execution input unknown. Scenario label only: {scenario}",
           "output": "\n".join(output), "configuration": {"sol_continuum": provenance}, "workflow_version": version,
           "executed_at": context.get("executed_at") or packet["generated_at"], "conditions": context.get("conditions", {}),
           "data_type": context.get("data_type", "imported"), "measurements": measurements, "evidence": evidence}
    validate_run(run)
    if len(canonical(run).encode("utf-8")) > 5_000_000:
        raise ValidationError("Converted run exceeds the 5 MB portable run limit.")
    return run


def comparison_setup(title, change):
    criteria = [{"id": f"lens_{key}", "label": f"{label} (SOL Lens assessment)", "unit": "score/1", "direction": direction,
                 "threshold": None, "max_regression_percent": None, "required": True} for key, label, direction in METRICS]
    criteria += [{"id": key, "label": label, "unit": unit, "direction": direction, "threshold": None,
                  "max_regression_percent": None, "required": True}
                 for key, label, unit, direction in (("execution_time", "Execution time", "s", "lower"), ("cost", "Run cost", "USD", "lower"), ("human_review", "Independent human review", "rating/5", "higher"))]
    return {"title": title, "task": "Review two explicitly selected saved SOL continuum proof-packet observations and their comparison conditions.",
            "proposed_change": change, "hypothesis": "The proposed change can be assessed only where inputs, conditions, and evaluation methods support comparison.",
            "intended_improvement": "Reviewer-defined; no quality target or adoption recommendation is inferred from packet verdicts.",
            "constraints": "Keep source identity, unknown conditions, unmeasured costs, and authority boundaries visible. Do not equate a producer score or ELIGIBLE status with human approval.",
            "acceptable_tradeoffs": "Not set. The reviewer must define acceptable quality, cost, and time tradeoffs.", "criteria": criteria}


def build_comparison(baseline, candidate, title, change):
    validate_run(baseline)
    validate_run(candidate)
    if baseline["designation"] != "baseline" or candidate["designation"] != "candidate":
        raise ValidationError("The selected pair must contain one baseline and one candidate.")
    with tempfile.TemporaryDirectory(prefix="sol-change-bridge-") as folder:
        store = Store(Path(folder) / "package.sqlite3")
        exp = store.create(comparison_setup(title, change))
        for run in (baseline, candidate):
            exp = store.import_run(exp["id"], json.dumps(run, ensure_ascii=False, indent=2), f'{run["id"]}.json')
    exp["id"] = "continuum-" + digest(canonical({"baseline": baseline, "candidate": candidate, "setup": exp["setup"]}))[:24]
    validate_archive(exp)
    return exp


def inventory(root: Path):
    """Bounded discovery of known public project entry points and saved artifacts."""
    root = root.resolve()
    if not root.is_dir():
        raise ValidationError(f"Continuum root not found: {root}")
    components = []
    for name, role, integration, anchor in COMPONENTS:
        components.append({"component": name, "present": (root / name).is_dir(), "role": role,
                           "integration_status": integration, "source_anchor": anchor, "anchor_present": (root / anchor).is_file()})
    artifacts = []
    patterns = ("sol-lens/samples/*.json", "sol-decide/examples/*packet*.json", "data/*benchmark*report.json")
    for pattern in patterns:
        for path in sorted(root.glob(pattern))[:100]:
            resolved = path.resolve()
            if not resolved.is_relative_to(root) or not resolved.is_file() or resolved.stat().st_size > MAX_PACKET_BYTES:
                continue
            try:
                source, source_hash = read_artifact(resolved)
                payload = parse_json(source)
            except (OSError, ValidationError) as exc:
                artifacts.append({"path": path.relative_to(root).as_posix(), "intake_error": str(exc)})
                continue
            supported = payload.get("schema") == PACKET_SCHEMA
            artifacts.append({"path": path.relative_to(root).as_posix(), "sha256_bytes": source_hash,
                              "schema": payload.get("schema"), "adapter": ADAPTER_VERSION if supported else None,
                              "packet_id": payload.get("packet_id"), "scenario": payload.get("fixture"),
                              "counterfactual_baseline_present": "baseline_evaluation" in payload,
                              "interpretation": "Saved producer claims; not freshly executed or independently verified."})
    return {"schema_version": "1.0", "kind": "sol-change/continuum-inventory", "captured_at": now(),
            "root": str(root), "components": components, "artifacts": artifacts,
            "ports": {"sol_live_server_documented": 8765, "sol_change_default": 8770},
            "limits": ["Curated, bounded inventory; not an exhaustive recursive scan or health certification.",
                       "No code execution, API calls, credential access, remote fetching, or sibling-project writes."]}


def write_new(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = document if isinstance(document, str) else json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="") as stream:
            stream.write(text)
    except FileExistsError as exc:
        raise ConflictError(f"Output already exists; choose a new destination: {path}") from exc


def _load_sol_edge_replay():
    sol_edge_src = PROJECT_ROOT.parent / "sol-edge" / "src"
    if sol_edge_src.is_dir() and str(sol_edge_src) not in sys.path:
        sys.path.insert(0, str(sol_edge_src))
    from sol_edge.runtime.events import RuntimeEvent
    from sol_edge.runtime.replay import replay_events
    return RuntimeEvent, replay_events


def replay_persisted_runtime_events(ledger_db: Path, run_id: str | None = None) -> dict:
    """
    Reconstructs and replays persisted 4-event `sol_edge_runtime_events` streams from a
    SQLite GovernanceCourtLedger database via `sol_edge.runtime.replay.replay_events`.
    """
    import sqlite3

    ledger_path = Path(ledger_db)
    if not ledger_path.is_file():
        raise ValidationError(f"Governance ledger database not found: {ledger_path}")

    RuntimeEvent, replay_events = _load_sol_edge_replay()

    conn = sqlite3.connect(str(ledger_path))
    conn.row_factory = sqlite3.Row
    try:
        if run_id:
            run_rows = conn.execute(
                "SELECT * FROM governance_court_runs WHERE run_id = ? ORDER BY rowid ASC",
                (run_id,),
            ).fetchall()
        else:
            run_rows = conn.execute(
                "SELECT * FROM governance_court_runs ORDER BY rowid ASC"
            ).fetchall()

        if not run_rows:
            raise ValidationError(
                f"No governed runs found in ledger {ledger_path}"
                + (f" for run_id={run_id}" if run_id else "")
            )

        run_reports = []
        total_streams = 0
        total_events_replayed = 0
        total_thought_signatures = 0
        all_streams_valid = True

        for r_row in run_rows:
            r_id = str(r_row["run_id"])
            ev_rows = conn.execute(
                """
                SELECT option_id, sequence_number, event_id, event_type,
                       occurred_at, previous_event_digest, event_digest, payload_json
                FROM sol_edge_runtime_events
                WHERE run_id = ?
                ORDER BY id ASC
                """,
                (r_id,),
            ).fetchall()

            sig_rows = conn.execute(
                """
                SELECT interaction_id, agent_role, model_used, thinking_level,
                       step_index, signature_digest, signature_length, thought_summary
                FROM gemini_thought_signatures
                WHERE run_id = ?
                ORDER BY step_index ASC, id ASC
                """,
                (r_id,),
            ).fetchall()
            total_thought_signatures += len(sig_rows)

            if not ev_rows:
                all_streams_valid = False
                run_reports.append(
                    {
                        "run_id": r_id,
                        "run_mode": str(r_row["run_mode"]),
                        "verified": False,
                        "error": "No sol_edge_runtime_events recorded for run.",
                        "streams": [],
                        "thought_signature_count": len(sig_rows),
                    }
                )
                continue

            by_opt: dict[str, list] = {}
            for ev in ev_rows:
                by_opt.setdefault(str(ev["option_id"]), []).append(ev)

            r_mode = str(r_row["run_mode"])
            stream_reports = []
            run_valid = True
            if r_mode in (
                "sol_continuum_discovery_observatory",
                "lumina_ranger_observatory_sovereignty",
            ):
                has_c0 = any(k.endswith(":cycle0-quarantine") for k in by_opt)
                has_c1 = any(k.endswith(":cycle1-eligible") for k in by_opt)
                if not (has_c0 and has_c1):
                    run_valid = False
                    all_streams_valid = False

            replayed_digests: list[str] = []
            for opt_id, opt_events in by_opt.items():
                total_streams += 1
                opt_sorted = sorted(opt_events, key=lambda e: int(e["sequence_number"]))
                total_events_replayed += len(opt_sorted)

                candidate_run_ids = [r_id]
                parts = r_id.split(":")
                for k in range(1, len(parts)):
                    prefix = ":".join(parts[:-k])
                    if prefix and prefix not in candidate_run_ids:
                        candidate_run_ids.append(prefix)
                if r_id.startswith("run:") and len(parts) >= 2:
                    study_slug = parts[1]
                    opt_base = opt_id.split(":")[0]
                    cleaned = re.sub(r"[^a-z0-9-_.:]+", "-", opt_base.strip().lower())
                    cleaned = re.sub(r"[-_.:]{2,}", "-", cleaned).strip("-_.:")
                    if not cleaned or not cleaned[0].isalpha():
                        cleaned = f"opt:{cleaned}" if cleaned else "opt:default"
                    if len(cleaned) < 3:
                        cleaned = f"opt:{cleaned}"
                    opt_slug = cleaned[:128].rstrip("-_.:")
                    for suffix in ("", ":repair-1", ":repair-2"):
                        cand = f"run:{study_slug}:{opt_slug}{suffix}"[:128]
                        if cand not in candidate_run_ids:
                            candidate_run_ids.append(cand)

                replayed_state = None
                last_err = None
                for cand_run_id in candidate_run_ids:
                    try:
                        reconstructed = [
                            RuntimeEvent.model_validate(
                                {
                                    "schema_name": "runtime_event",
                                    "schema_version": "0.2.0",
                                    "event_id": str(ev["event_id"]),
                                    "run_id": cand_run_id,
                                    "sequence_number": int(ev["sequence_number"]),
                                    "event_type": str(ev["event_type"]),
                                    "occurred_at": str(ev["occurred_at"]),
                                    "previous_event_digest": ev["previous_event_digest"],
                                    "event_digest": str(ev["event_digest"]),
                                    "payload": json.loads(str(ev["payload_json"])),
                                }
                            )
                            for ev in opt_sorted
                        ]
                        replayed_state = replay_events(reconstructed)
                        break
                    except Exception as exc:
                        last_err = str(exc)

                if replayed_state is None:
                    run_valid = False
                    all_streams_valid = False
                    stream_reports.append(
                        {
                            "option_id": opt_id,
                            "event_count": len(opt_sorted),
                            "verified": False,
                            "error": last_err or "Replay validation failed.",
                        }
                    )
                    continue

                replayed_digests.append(str(replayed_state.state_digest))
                expected_digest = None
                if any(
                    opt_id.endswith(sfx)
                    for sfx in (
                        ":cycle0-quarantine",
                        ":cycle0-shocked",
                        ":cycle0-pinched",
                        ":cycle0-skin-broken",
                        ":cycle0",
                    )
                ):
                    expected_digest = r_row["prior_quarantined_state_digest"]
                elif any(
                    opt_id.endswith(sfx)
                    for sfx in (
                        ":cycle1-eligible",
                        ":cycle1-mutated",
                        ":cycle1-bridged",
                        ":cycle1-healed",
                        ":cycle1-pt-restored",
                        ":cycle1",
                    )
                ):
                    expected_digest = r_row["final_state_digest"]

                digest_matches = (
                    True
                    if not expected_digest
                    else str(replayed_state.state_digest) == str(expected_digest)
                )
                stream_ok = len(opt_sorted) == 4 and digest_matches
                if not stream_ok:
                    run_valid = False
                    all_streams_valid = False

                stream_reports.append(
                    {
                        "option_id": opt_id,
                        "event_count": len(opt_sorted),
                        "verified": stream_ok,
                        "replayed_status": str(replayed_state.status.value),
                        "replayed_policy_status": str(replayed_state.status.value),
                        "replayed_state_digest": str(replayed_state.state_digest),
                        "expected_state_digest": str(expected_digest) if expected_digest else None,
                        "digest_matches": digest_matches,
                        "last_event_digest": str(replayed_state.last_accepted_event_digest),
                    }
                )

            if str(r_row["final_state_digest"]) not in replayed_digests:
                run_valid = False
                all_streams_valid = False

            run_reports.append(
                {
                    "run_id": r_id,
                    "run_mode": str(r_row["run_mode"]),
                    "study_name": str(r_row["study_name"]),
                    "policy_status": str(r_row["policy_status"]),
                    "final_state_digest": str(r_row["final_state_digest"]),
                    "prior_quarantined_state_digest": r_row["prior_quarantined_state_digest"],
                    "verified": run_valid,
                    "streams": stream_reports,
                    "thought_signature_count": len(sig_rows),
                    "thought_signatures": [
                        {
                            "interaction_id": str(s["interaction_id"]),
                            "agent_role": str(s["agent_role"]),
                            "model_used": str(s["model_used"]),
                            "thinking_level": str(s["thinking_level"]),
                            "step_index": int(s["step_index"]),
                            "signature_digest": str(s["signature_digest"]),
                            "signature_length": int(s["signature_length"]),
                        }
                        for s in sig_rows
                    ],
                }
            )

        return {
            "schema_version": "1.0",
            "kind": "sol-change/runtime-replay-verification",
            "verified": all_streams_valid and len(run_reports) > 0,
            "total_runs": len(run_reports),
            "total_streams": total_streams,
            "total_events_replayed": total_events_replayed,
            "total_thought_signatures": total_thought_signatures,
            "runs": run_reports,
        }
    finally:
        conn.close()


def assess_continuum_observatory(
    experiment: Path | dict,
    ledger_db: Path | str | None = None,
    run_id: str | None = None,
) -> dict:
    """
    Produces a cycle-level before/after drift breakdown (`cycle0_baseline` vs `cycle1_candidate`)
    for a SOL Continuum or Lumina experiment and optionally verifies persisted `sol-edge`
    runtime event streams from a GovernanceCourtLedger SQLite database via `replay_events`.
    """
    if isinstance(experiment, dict):
        exp = experiment
    else:
        exp_path = Path(experiment)
        if exp_path.is_dir():
            exp_path = exp_path / "experiment.json"
        source_text, _ = read_artifact(exp_path)
        exp = parse_json(source_text)

    validate_archive(exp)
    comp = compare(exp)

    active_runs = exp.get("active_runs", {})
    runs_by_rec_id = {
        r["record_id"]: r["run"]
        for r in exp.get("runs", [])
        if isinstance(r, dict) and "record_id" in r and isinstance(r.get("run"), dict)
    }
    baseline_run = runs_by_rec_id.get(active_runs.get("baseline"))
    candidate_run = runs_by_rec_id.get(active_runs.get("candidate"))
    if not baseline_run or not candidate_run:
        raise ValidationError("Experiment archive must contain both a baseline and a candidate run.")

    base_sc = baseline_run.get("configuration", {}).get("sol_continuum", {})
    cand_sc = candidate_run.get("configuration", {}).get("sol_continuum", {})
    base_metrics = {m["criterion_id"]: m.get("value") for m in baseline_run.get("measurements", [])}
    cand_metrics = {m["criterion_id"]: m.get("value") for m in candidate_run.get("measurements", [])}

    criterion_deltas = []
    quality_improvements = []
    for row in comp["metrics"]:
        crit = row["criterion"]
        cid = crit["id"]
        b_val = row["baseline"].get("value") if isinstance(row.get("baseline"), dict) else row.get("baseline")
        c_val = row["candidate"].get("value") if isinstance(row.get("candidate"), dict) else row.get("candidate")
        delta = row["delta"]
        direction = crit["direction"]
        criterion_deltas.append(
            {
                "criterion_id": cid,
                "label": crit["label"],
                "direction": direction,
                "cycle0_value": b_val,
                "cycle1_value": c_val,
                "delta": delta,
                "status": row["status"],
            }
        )
        if cid.startswith("lens_") and isinstance(delta, (int, float)):
            signed_gain = -float(delta) if direction == "lower" else float(delta)
            quality_improvements.append(signed_gain)

    counts = comp.get("counts", {})
    if comp.get("comparability") != "compatible" or counts.get("incompatible", 0) > 0:
        outcome = "inconclusive"
    elif counts.get("improved", 0) > 0 and counts.get("regressed", 0) == 0:
        outcome = "improved"
    elif counts.get("regressed", 0) > 0 and counts.get("improved", 0) == 0:
        outcome = "regressed"
    elif counts.get("improved", 0) > 0 and counts.get("regressed", 0) > 0:
        outcome = "mixed"
    else:
        outcome = "inconclusive"

    c0_verdict = base_sc.get("upstream_verdict", "UNKNOWN")
    c1_verdict = cand_sc.get("upstream_verdict", "UNKNOWN")
    cand_source_pkt: dict = {}
    raw_cand_source = cand_sc.get("original_source_text")
    if isinstance(raw_cand_source, str) and raw_cand_source.strip():
        try:
            parsed_cand = parse_json(raw_cand_source)
            if isinstance(parsed_cand, dict):
                cand_source_pkt = parsed_cand
        except Exception:
            cand_source_pkt = {}

    fk = cand_source_pkt.get("frontier_k_verification")
    fl = cand_source_pkt.get("frontier_l_verification")
    fn = cand_source_pkt.get("frontier_n_verification")
    cand_cond = candidate_run.get("conditions", {}) if isinstance(candidate_run.get("conditions"), dict) else {}

    frontier_verification_summary = {
        "frontier_k_verified": (
            bool(
                fk.get("all_six_capabilities_verified", False)
                or (
                    isinstance(fk.get("formal_proof_certificate"), dict)
                    and fk["formal_proof_certificate"].get("verdict") == "PROVED_THEOREM"
                )
            )
            if isinstance(fk, dict)
            else bool(cand_cond.get("frontier_k_verified", False))
        ),
        "frontier_k_summary_digest": (
            fk.get("summary_digest")
            if isinstance(fk, dict)
            else cand_cond.get("frontier_k_summary_digest")
        ),
        "frontier_l_verified": (
            bool(
                fl.get("all_five_capabilities_verified", False)
                or bool(fl.get("wideword_fabric_report"))
                or bool(fl.get("sovereign_runtime_report"))
            )
            if isinstance(fl, dict)
            else bool(cand_cond.get("frontier_l_verified", False))
        ),
        "frontier_l_summary_digest": (
            fl.get("summary_digest")
            if isinstance(fl, dict)
            else cand_cond.get("frontier_l_summary_digest")
        ),
        "frontier_n_verified": (
            bool(fn.get("autopoietic_loop_verified", False))
            if isinstance(fn, dict)
            else bool(cand_cond.get("frontier_n_verified", False))
        ),
        "frontier_n_summary_digest": (
            fn.get("summary_digest")
            if isinstance(fn, dict)
            else cand_cond.get("frontier_n_summary_digest")
        ),
        "frontier_n_core_immutability_verified": (
            bool(fn.get("epistemic_gap_intake", {}).get("core_immutability_verified", False))
            if isinstance(fn, dict) and isinstance(fn.get("epistemic_gap_intake"), dict)
            else False
        ),
        "frontier_n_bimodal_dream_verified": (
            bool(fn.get("bimodal_dream_consolidation", {}).get("bimodal_synapse_verified", False))
            if isinstance(fn, dict) and isinstance(fn.get("bimodal_dream_consolidation"), dict)
            else False
        ),
        "frontier_n_bilateral_entangler_verified": (
            bool(fn.get("bilateral_entangler_control", {}).get("bilateral_lock_verified", False))
            if isinstance(fn, dict) and isinstance(fn.get("bilateral_entangler_control"), dict)
            else False
        ),
        "frontier_n_statistical_governance_verified": (
            bool(fn.get("statistical_evolution_governance", {}).get("promotion_statistically_governed", False))
            if isinstance(fn, dict) and isinstance(fn.get("statistical_evolution_governance"), dict)
            else False
        ),
        "frontier_n_msf_cycle0_blocked": (
            bool(
                fn.get("bilateral_entangler_control", {})
                .get("cycle0_control", {})
                .get("nudge_rejection_reason")
                == "msf_unstable"
                or fn.get("topological_entanglement_control", {}).get("cycle0_nudge_blocked", False)
            )
            if isinstance(fn, dict)
            else False
        ),
        "frontier_n_gatekeeper_promoted": (
            bool(
                fn.get("statistical_evolution_governance", {})
                .get("self_train_gatekeeper", {})
                .get("accepted", False)
                or fn.get("statistical_self_evolution", {}).get("gatekeeper_promoted", False)
            )
            if isinstance(fn, dict)
            else False
        ),
    }

    drift_breakdown = {
        "cycle0_baseline": {
            "run_id": baseline_run["id"],
            "workflow_version": baseline_run.get("workflow_version"),
            "upstream_verdict": c0_verdict,
            "source_packet_id": base_sc.get("source_packet_id"),
            "sha256_source_text": base_sc.get("sha256_source_text"),
            "conditions": baseline_run.get("conditions", {}),
            "metrics": base_metrics,
        },
        "cycle1_candidate": {
            "run_id": candidate_run["id"],
            "workflow_version": candidate_run.get("workflow_version"),
            "upstream_verdict": c1_verdict,
            "source_packet_id": cand_sc.get("source_packet_id"),
            "sha256_source_text": cand_sc.get("sha256_source_text"),
            "conditions": candidate_run.get("conditions", {}),
            "metrics": cand_metrics,
        },
        "verdict_transition": f"{c0_verdict} -> {c1_verdict}",
        "mean_quality_drift": (
            round(sum(quality_improvements) / len(quality_improvements), 6)
            if quality_improvements
            else 0.0
        ),
        "criterion_deltas": criterion_deltas,
        "frontier_verification_summary": frontier_verification_summary,
    }

    replay_report = None
    if ledger_db is not None:
        replay_report = replay_persisted_runtime_events(Path(ledger_db), run_id=run_id)

    return {
        "schema_version": "1.0",
        "kind": "sol-change/continuum-assessment",
        "experiment_id": exp["id"],
        "review_status": exp["review_status"],
        "comparability": comp["comparability"],
        "outcome": outcome,
        "warnings": comp["warnings"],
        "counts": counts,
        "cycle_drift_breakdown": drift_breakdown,
        "runtime_replay_verification": replay_report,
        "authority_boundary": (
            "Producer verdicts and ELIGIBLE runtime states never substitute for an "
            "independent human review decision in sol-change."
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="SOL continuum → Change Observatory: offline, source-preserving artifact intake")
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("inventory", help="List known components and supported saved artifacts without executing them")
    scan.add_argument("--root", type=Path, default=PROJECT_ROOT.parent)
    scan.add_argument("--output", type=Path)
    convert = commands.add_parser("convert", help="Convert one packet's primary observation to run schema 1.0")
    convert.add_argument("packet", type=Path)
    convert.add_argument("--designation", required=True, choices=("baseline", "candidate"))
    convert.add_argument("--context", type=Path, help="Optional schema-1.0 context sidecar")
    convert.add_argument("--output", type=Path, required=True)
    pair = commands.add_parser("compare", help="Prepare a reviewable experiment from two saved packet observations")
    pair.add_argument("--baseline", type=Path, required=True)
    pair.add_argument("--candidate", type=Path, required=True)
    pair.add_argument("--baseline-context", type=Path)
    pair.add_argument("--candidate-context", type=Path)
    pair.add_argument("--title", required=True)
    pair.add_argument("--change", required=True)
    pair.add_argument("--output-dir", type=Path, required=True)
    pair.add_argument("--register", action="store_true", help="Also import the prepared archive into a local Observatory database")
    pair.add_argument("--db", type=Path, default=PROJECT_ROOT / "data" / "observatory.sqlite3")
    assess_cmd = commands.add_parser("assess", help="Assess cycle-level before/after drift and optionally replay persisted sol-edge runtime events")
    assess_cmd.add_argument("--experiment", type=Path, required=True, help="Path to experiment.json or experiment bundle directory")
    assess_cmd.add_argument("--ledger-db", type=Path, help="Optional path to SQLite GovernanceCourtLedger database")
    assess_cmd.add_argument("--run-id", help="Optional specific run_id in the governance ledger")
    assess_cmd.add_argument("--output", type=Path, help="Optional path to write JSON assessment report")
    args = parser.parse_args(argv)
    try:
        if args.command == "inventory":
            result = inventory(args.root)
            if args.output:
                write_new(args.output, result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "assess":
            result = assess_continuum_observatory(args.experiment, ledger_db=args.ledger_db, run_id=args.run_id)
            if args.output:
                write_new(args.output, result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if result.get("runtime_replay_verification") and not result["runtime_replay_verification"]["verified"]:
                return 2
            return 0
        def convert_file(path, designation, context_path=None):
            source, _ = read_artifact(path)
            context = parse_json(read_artifact(context_path)[0]) if context_path else None
            return packet_to_run(source, designation, path.as_posix(), context)
        if args.command == "convert":
            run = convert_file(args.packet, args.designation, args.context)
            write_new(args.output, run)
            print(f"Prepared {args.output}. Source preserved; no experiment or decision was created.")
            return 0
        baseline = convert_file(args.baseline, "baseline", args.baseline_context)
        candidate = convert_file(args.candidate, "candidate", args.candidate_context)
        exp = build_comparison(baseline, candidate, args.title, args.change)
        if args.output_dir.exists():
            raise ConflictError("Output directory already exists. Choose a new directory; prior exports are never overwritten.")
        args.output_dir.mkdir(parents=True)
        for name, document in (("baseline.json", baseline), ("candidate.json", candidate), ("experiment.json", exp), ("comparison.md", markdown_report(exp))):
            write_new(args.output_dir / name, document)
        registered = False
        registered_state = exp
        if args.register:
            store = Store(args.db)
            try:
                store.import_archive(json.dumps(exp, ensure_ascii=False))
                registered = True
            except ConflictError:
                registered_state = store.get(exp["id"])
                print("This comparison is already registered. Its existing criteria and decisions were preserved.")
        result = compare(exp)
        print(json.dumps({"experiment_id": exp["id"], "output_dir": str(args.output_dir.resolve()),
                          "comparability": result["comparability"], "warnings": result["warnings"], "registered_new": registered,
                          "review_status": registered_state["review_status"], "human_decisions_created": 0}, ensure_ascii=False, indent=2))
        return 0
    except (ValidationError, ConflictError, OSError) as exc:
        print(f"Intake failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
