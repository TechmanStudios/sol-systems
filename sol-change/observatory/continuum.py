"""Offline artifact bridge for the SOL continuum. Never executes a sibling project."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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
REPEAT_TRIAL_GROUP_KIND = "sol-change/repeat-trial-group"
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


def packet_to_run(
    source_text: str,
    designation: str,
    source_label="packet.json",
    context=None,
    *,
    measured_execution_time_s: float | None = None,
    measured_cost_usd: float | None = None,
) -> dict:
    """Convert only the packet's primary observation, never its counterfactual baseline."""
    if designation not in ("baseline", "candidate"):
        raise ValidationError("Choose baseline or candidate for this saved packet's primary observation.")
    if not isinstance(source_text, str) or len(source_text.encode("utf-8")) > MAX_PACKET_BYTES:
        raise ValidationError("Native packet must be UTF-8 JSON smaller than 1 MB.")
    if not isinstance(source_label, str) or not source_label.strip() or len(source_label) > 500:
        raise ValidationError("Source label must be a non-empty string of at most 500 characters.")
    if measured_execution_time_s is not None:
        if type(measured_execution_time_s) not in (int, float) or not math.isfinite(float(measured_execution_time_s)) or float(measured_execution_time_s) < 0.0:
            raise ValidationError("measured_execution_time_s must be a non-negative finite number.")
    if measured_cost_usd is not None:
        if type(measured_cost_usd) not in (int, float) or not math.isfinite(float(measured_cost_usd)) or float(measured_cost_usd) < 0.0:
            raise ValidationError("measured_cost_usd must be a non-negative finite number.")
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

    if measured_execution_time_s is not None:
        evidence.append({
            "id": "timing-telemetry",
            "title": "Producer-measured wall-clock execution time",
            "reference": f"sha256:{source_hash}#/timing_telemetry",
            "provenance": (
                f"Wall-clock time.perf_counter duration ({float(measured_execution_time_s):.6f} s) "
                f"measured directly during producer execution of {source_label}."
            ),
        })
        measurements.append({
            "criterion_id": "execution_time",
            "value": round(float(measured_execution_time_s), 9),
            "unit": "s",
            "method": {
                "kind": "measured",
                "description": "Wall-clock execution time measured via time.perf_counter.",
                "version": "wall_clock_perf_counter/1.0",
            },
            "evidence_ids": ["timing-telemetry"],
        })
    else:
        measurements.append({
            "criterion_id": "execution_time",
            "value": None,
            "unit": "s",
            "method": {
                "kind": "measured",
                "description": "Not captured by the supported proof-packet intake contract.",
                "version": None,
            },
            "evidence_ids": [],
        })

    if measured_cost_usd is not None:
        evidence.append({
            "id": "cost-telemetry",
            "title": "Producer-measured API token cost",
            "reference": f"sha256:{source_hash}#/cost_telemetry",
            "provenance": f"Measured API token billing cost (${float(measured_cost_usd):.6f} USD) for {source_label}.",
        })
        measurements.append({
            "criterion_id": "cost",
            "value": round(float(measured_cost_usd), 9),
            "unit": "USD",
            "method": {
                "kind": "measured",
                "description": "Measured API token usage cost.",
                "version": "token_ledger/1.0",
            },
            "evidence_ids": ["cost-telemetry"],
        })
    else:
        measurements.append({
            "criterion_id": "cost",
            "value": None,
            "unit": "USD",
            "method": {
                "kind": "measured",
                "description": "Not captured by the supported proof-packet intake contract.",
                "version": None,
            },
            "evidence_ids": [],
        })

    measurements.append({
        "criterion_id": "human_review",
        "value": None,
        "unit": "rating/5",
        "method": {
            "kind": "human_rating",
            "description": "Not captured by the supported proof-packet intake contract.",
            "version": None,
        },
        "evidence_ids": [],
    })
    scenario = packet.get("fixture", "Unnamed scenario")
    output = ["IMPORTED SOL CONTINUUM OBSERVATION — UNVERIFIED SOURCE CLAIMS", "", f"Scenario: {scenario}",
              f"Packet: {packet['packet_id']}", f"Upstream verdict (not a human decision or execution authorization): {canonical(upstream_verdict)}", "",
              f"This run contains only the packet's primary {metric_pointer} observation.",
              "The embedded baseline_evaluation, if any, is retained as source material and is not imported as an independently executed baseline.",
              "Time, cost, and independent human review remain unmeasured." if (measured_execution_time_s is None and measured_cost_usd is None) else "Independent human review remains unmeasured.",
              "", *warnings, "", "Observable packet trace:"]
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
                "wgsl_decision_prover_observatory",
                "swarm_cohomology_observatory",
                "umok_edge_kernel_observatory",
                "mitotic_foliation_observatory",
                "stwm_wavefront_observatory",
                "rsi_compiler_observatory",
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
    fo = cand_source_pkt.get("frontier_o_verification")
    fp = cand_source_pkt.get("frontier_p_verification")
    fq = cand_source_pkt.get("frontier_q_verification")
    fr = cand_source_pkt.get("frontier_r_verification")
    fs = cand_source_pkt.get("frontier_s_verification")
    ft = cand_source_pkt.get("frontier_t_verification")
    cand_cond = candidate_run.get("conditions", {}) if isinstance(candidate_run.get("conditions"), dict) else {}

    def _d(val: object) -> dict:
        return val if isinstance(val, dict) else {}

    def _f(val: object, default: float) -> float:
        if type(val) in (int, float) and math.isfinite(float(val)):
            return float(val)
        return default

    def _i(val: object, default: int) -> int:
        if type(val) is int:
            return val
        if type(val) is float and val.is_integer():
            return int(val)
        return default

    def _l(val: object) -> list:
        return val if isinstance(val, list) else []

    fp_verified_bool = (
        bool(
            fp.get("swarm_cohomology_verified") is True
            and isinstance(fp.get("fleet_kinematics_and_payload"), dict)
            and isinstance(fp.get("closed_chain_sheaf_audit"), dict)
            and isinstance(fp.get("decentralized_se3_holonomy"), dict)
            and isinstance(fp.get("estop_safety_arbiter"), dict)
            and isinstance(fp.get("cycle1_audit"), dict)
            and _f(_d(fp.get("fleet_kinematics_and_payload")).get("payload_mass_kg"), 0.0) >= 25.0
            and _i(_d(fp.get("fleet_kinematics_and_payload")).get("num_robots"), 0) >= 2
            and _i(_d(fp.get("closed_chain_sheaf_audit")).get("cycle1_effective_beta_1"), 1) == 0
            and _f(_d(fp.get("closed_chain_sheaf_audit")).get("cycle1_internal_squeeze_wrench_n"), 999.0) <= 15.0
            and _f(_d(fp.get("decentralized_se3_holonomy")).get("cycle1_rotational_defect_deg"), 999.0) <= 3.0
            and _f(_d(fp.get("decentralized_se3_holonomy")).get("cycle1_translational_defect_mm"), 999.0) <= 5.0
            and _d(fp.get("decentralized_se3_holonomy")).get("gps_or_mocap_required") is False
            and _f(_d(fp.get("estop_safety_arbiter")).get("estop_latency_us"), 999.0) <= 200.0
            and _d(fp.get("estop_safety_arbiter")).get("cycle0_estop_triggered") is True
            and _d(fp.get("estop_safety_arbiter")).get("cycle1_estop_triggered") is False
            and _d(fp.get("cycle1_audit")).get("policy_status") == "ELIGIBLE"
        )
        if isinstance(fp, dict)
        else bool(cand_cond.get("frontier_p_verified", False))
    )

    fq_verified_bool = (
        bool(
            fq.get("umok_kernel_verified") is True
            and isinstance(fq.get("geodesic_verlet_kernel"), dict)
            and isinstance(fq.get("riemannian_alu_verification"), dict)
            and isinstance(fq.get("zero_copy_ipc_can_bridge"), dict)
            and isinstance(fq.get("eligibility_interlock"), dict)
            and isinstance(fq.get("cycle1_audit"), dict)
            and _f(_d(fq.get("geodesic_verlet_kernel")).get("cycle1_mean_step_latency_us"), 999.0) <= 1.0
            and _f(_d(fq.get("geodesic_verlet_kernel")).get("cycle0_mean_step_latency_us"), 0.0) > 1.0
            and _d(fq.get("riemannian_alu_verification")).get("all_gates_passed") is True
            and _i(_d(fq.get("riemannian_alu_verification")).get("passed_cases"), 0) >= 20
            and _d(fq.get("zero_copy_ipc_can_bridge")).get("zero_copy_verified") is True
            and _d(fq.get("zero_copy_ipc_can_bridge")).get("cycle0_crc_or_seq_fault_detected") is True
            and _d(fq.get("zero_copy_ipc_can_bridge")).get("cycle1_crc32_verified") is True
            and _d(fq.get("eligibility_interlock")).get("cycle0_safe_state_triggered") is True
            and _d(fq.get("eligibility_interlock")).get("cycle1_safe_state_triggered") is False
            and _d(fq.get("eligibility_interlock")).get("authorized_claimed") is False
            and _d(fq.get("cycle1_audit")).get("policy_status") == "ELIGIBLE"
        )
        if isinstance(fq, dict)
        else bool(cand_cond.get("frontier_q_verified", False))
    )

    fr_verified_bool = (
        bool(
            fr.get("mitotic_foliation_verified") is True
            and isinstance(fr.get("mitotic_surface_fission"), dict)
            and isinstance(fr.get("toroidal_surgery_homology"), dict)
            and isinstance(fr.get("hawking_radiation_memory_sink"), dict)
            and isinstance(fr.get("eligibility_interlock"), dict)
            and isinstance(fr.get("cycle1_audit"), dict)
            and 0.45 - 1e-9 <= _f(_d(fr.get("mitotic_surface_fission")).get("cycle1_alpha"), 0.0) <= 0.55 + 1e-9
            and _i(_d(fr.get("toroidal_surgery_homology")).get("toroidal_genus_g"), 0) == 1
            and _i(_d(fr.get("toroidal_surgery_homology")).get("euler_characteristic_chi"), 1) == 0
            and 0.0 <= _f(_d(fr.get("hawking_radiation_memory_sink")).get("cycle1_mass_conservation_residual"), 1.0) <= 1e-6
            and _d(fr.get("hawking_radiation_memory_sink")).get("sacred_core_immutable") is True
            and _d(fr.get("eligibility_interlock")).get("cycle0_safe_state_triggered") is True
            and _d(fr.get("eligibility_interlock")).get("cycle1_safe_state_triggered") is False
            and _d(fr.get("eligibility_interlock")).get("authorized_claimed") is False
            and _d(fr.get("cycle1_audit")).get("policy_status") == "ELIGIBLE"
        )
        if isinstance(fr, dict)
        else bool(cand_cond.get("frontier_r_verified", False))
    )

    fs_verified_bool = (
        bool(
            fs.get("stwm_wavefront_verified") is True
            and isinstance(fs.get("coprime_quadrature_pdm"), dict)
            and isinstance(fs.get("interlane_prefix_carry"), dict)
            and isinstance(fs.get("hierarchical_waveguide_fabric"), dict)
            and isinstance(fs.get("quantum_wavefront_calibration"), dict)
            and isinstance(fs.get("autonomic_mhd_gru_jeans_bus"), dict)
            and isinstance(fs.get("eligibility_interlock"), dict)
            and isinstance(fs.get("cycle1_audit"), dict)
            and _i(_d(fs.get("coprime_quadrature_pdm")).get("passed_cases"), 0) >= 6
            and _i(_d(fs.get("interlane_prefix_carry")).get("passed_cases"), 0) >= 8
            and _i(_d(fs.get("hierarchical_waveguide_fabric")).get("passed_32b"), 0) >= 5
            and _i(_d(fs.get("hierarchical_waveguide_fabric")).get("passed_64b"), 0) >= 5
            and _i(_d(fs.get("quantum_wavefront_calibration")).get("passed_regimes"), 0) >= 12
            and _f(_d(fs.get("autonomic_mhd_gru_jeans_bus")).get("cycle1_interlane_crosstalk_db"), 0.0) <= -35.0
            and _d(fs.get("eligibility_interlock")).get("cycle0_safe_state_triggered") is True
            and _d(fs.get("eligibility_interlock")).get("cycle1_safe_state_triggered") is False
            and _d(fs.get("eligibility_interlock")).get("authorized_claimed") is False
            and _d(fs.get("cycle1_audit")).get("policy_status") == "ELIGIBLE"
        )
        if isinstance(fs, dict)
        else bool(cand_cond.get("frontier_s_verified", False))
    )

    ft_verified_bool = (
        bool(
            ft.get("rsi_compiler_verified") is True
            and isinstance(ft.get("sandboxed_rsi_and_claim_compiler"), dict)
            and isinstance(ft.get("governed_compiler_invocation"), dict)
            and isinstance(ft.get("governed_pass_replay"), dict)
            and isinstance(ft.get("release_certification_bundle"), dict)
            and isinstance(ft.get("eligibility_interlock"), dict)
            and isinstance(ft.get("cycle1_audit"), dict)
            and _i(
                _d(ft.get("sandboxed_rsi_and_claim_compiler")).get(
                    "compiled_verified_claims",
                    _d(ft.get("sandboxed_rsi_and_claim_compiler")).get("claims_verified_count", 0),
                ),
                0,
            )
            >= 2
            and len(_l(_d(ft.get("governed_compiler_invocation")).get("cycle1_admitted_passes"))) >= 3
            and _i(_d(ft.get("governed_pass_replay")).get("replay_verified_count"), 0) >= 1
            and _i(_d(ft.get("governed_pass_replay")).get("replay_failed_count"), 1) == 0
            and _d(ft.get("release_certification_bundle")).get("certification_status")
            in ("certification_ready", "release_candidate_certification_ready")
            and _d(ft.get("eligibility_interlock")).get("production_mutation_allowed") is False
            and _d(ft.get("eligibility_interlock")).get("allow_production_execution") is False
            and _d(ft.get("eligibility_interlock")).get("authorized_claimed") is False
            and _d(ft.get("cycle1_audit")).get("policy_status") == "ELIGIBLE"
        )
        if isinstance(ft, dict)
        else bool(cand_cond.get("frontier_t_verified", False))
    )

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
            bool(_d(fn.get("epistemic_gap_intake")).get("core_immutability_verified", False))
            if isinstance(fn, dict)
            else False
        ),
        "frontier_n_bimodal_dream_verified": (
            bool(_d(fn.get("bimodal_dream_consolidation")).get("bimodal_synapse_verified", False))
            if isinstance(fn, dict)
            else False
        ),
        "frontier_n_bilateral_entangler_verified": (
            bool(_d(fn.get("bilateral_entangler_control")).get("bilateral_lock_verified", False))
            if isinstance(fn, dict)
            else False
        ),
        "frontier_n_statistical_governance_verified": (
            bool(_d(fn.get("statistical_evolution_governance")).get("promotion_statistically_governed", False))
            if isinstance(fn, dict)
            else False
        ),
        "frontier_n_msf_cycle0_blocked": (
            bool(
                _d(_d(fn.get("bilateral_entangler_control")).get("cycle0_control")).get("nudge_rejection_reason")
                == "msf_unstable"
                or _d(fn.get("topological_entanglement_control")).get("cycle0_nudge_blocked", False)
            )
            if isinstance(fn, dict)
            else False
        ),
        "frontier_n_gatekeeper_promoted": (
            bool(
                _d(_d(fn.get("statistical_evolution_governance")).get("self_train_gatekeeper")).get("accepted", False)
                or _d(fn.get("statistical_self_evolution")).get("gatekeeper_promoted", False)
            )
            if isinstance(fn, dict)
            else False
        ),
        "frontier_o_verified": (
            bool(
                (
                    fo.get("wgsl_decision_prover_verified", False)
                    and (
                        not isinstance(fo.get("shader_validation"), dict)
                        or fo["shader_validation"].get("is_valid", True)
                    )
                )
                or (
                    fo.get("wgsl_prover_verified", False)
                    and fo.get("shader_valid", False)
                )
            )
            if isinstance(fo, dict)
            else bool(cand_cond.get("frontier_o_verified", False))
        ),
        "frontier_o_summary_digest": (
            fo.get("summary_digest")
            if isinstance(fo, dict)
            else cand_cond.get("frontier_o_summary_digest")
        ),
        "frontier_p_verified": fp_verified_bool,
        "frontier_p_summary_digest": (
            fp.get("frontier_p_summary_digest") or fp.get("summary_digest")
            if isinstance(fp, dict)
            else cand_cond.get("frontier_p_summary_digest")
        ),
        "frontier_p": (
            {
                "verified": fp_verified_bool,
                "payload_mass_kg": _f(
                    _d(fp.get("fleet_kinematics_and_payload")).get("payload_mass_kg"), 0.0
                ),
                "cycle1_effective_beta_1": _i(
                    _d(fp.get("closed_chain_sheaf_audit")).get("cycle1_effective_beta_1"), 1
                ),
                "cycle1_internal_squeeze_wrench_n": _f(
                    _d(fp.get("closed_chain_sheaf_audit")).get("cycle1_internal_squeeze_wrench_n"), 999.0
                ),
                "cycle1_rotational_defect_deg": _f(
                    _d(fp.get("decentralized_se3_holonomy")).get("cycle1_rotational_defect_deg"), 999.0
                ),
                "cycle1_translational_defect_mm": _f(
                    _d(fp.get("decentralized_se3_holonomy")).get("cycle1_translational_defect_mm"), 999.0
                ),
                "estop_latency_us": _f(
                    _d(fp.get("estop_safety_arbiter")).get("estop_latency_us"), 999.0
                ),
                "gps_or_mocap_required": bool(
                    _d(fp.get("decentralized_se3_holonomy")).get("gps_or_mocap_required", True)
                ),
                "summary_digest": fp.get("frontier_p_summary_digest") or fp.get("summary_digest"),
            }
            if isinstance(fp, dict)
            else {
                "verified": bool(cand_cond.get("frontier_p_verified", False)),
                "gps_or_mocap_required": False,
                "summary_digest": cand_cond.get("frontier_p_summary_digest"),
            }
        ),
        "frontier_q_verified": fq_verified_bool,
        "frontier_q_summary_digest": (
            fq.get("frontier_q_summary_digest") or fq.get("summary_digest")
            if isinstance(fq, dict)
            else cand_cond.get("frontier_q_summary_digest")
        ),
        "frontier_q": (
            {
                "verified": fq_verified_bool,
                "cycle0_mean_step_latency_us": _f(
                    _d(fq.get("geodesic_verlet_kernel")).get("cycle0_mean_step_latency_us"), 999.0
                ),
                "cycle1_mean_step_latency_us": _f(
                    _d(fq.get("geodesic_verlet_kernel")).get("cycle1_mean_step_latency_us"), 999.0
                ),
                "alu_all_gates_passed": bool(
                    _d(fq.get("riemannian_alu_verification")).get("all_gates_passed", False)
                ),
                "alu_passed_cases": _i(
                    _d(fq.get("riemannian_alu_verification")).get("passed_cases"), 0
                ),
                "zero_copy_verified": bool(
                    _d(fq.get("zero_copy_ipc_can_bridge")).get("zero_copy_verified", False)
                ),
                "cycle1_crc32_verified": bool(
                    _d(fq.get("zero_copy_ipc_can_bridge")).get("cycle1_crc32_verified", False)
                ),
                "cycle1_staged_frames_count": _i(
                    _d(fq.get("eligibility_interlock")).get("cycle1_staged_frames_count"), 0
                ),
                "authorized_claimed": bool(
                    _d(fq.get("eligibility_interlock")).get("authorized_claimed", True)
                ),
                "summary_digest": fq.get("frontier_q_summary_digest") or fq.get("summary_digest"),
            }
            if isinstance(fq, dict)
            else {
                "verified": bool(cand_cond.get("frontier_q_verified", False)),
                "zero_copy_verified": bool(cand_cond.get("frontier_q_verified", False)),
                "authorized_claimed": False,
                "summary_digest": cand_cond.get("frontier_q_summary_digest"),
            }
        ),
        "frontier_r_verified": fr_verified_bool,
        "frontier_r_summary_digest": (
            fr.get("frontier_r_summary_digest") or fr.get("summary_digest")
            if isinstance(fr, dict)
            else cand_cond.get("frontier_r_summary_digest")
        ),
        "frontier_r": (
            {
                "verified": fr_verified_bool,
                "cycle0_alpha": _f(
                    _d(fr.get("mitotic_surface_fission")).get("cycle0_alpha"), 0.0
                ),
                "cycle1_alpha": _f(
                    _d(fr.get("mitotic_surface_fission")).get("cycle1_alpha"), 0.0
                ),
                "toroidal_genus_g": _i(
                    _d(fr.get("toroidal_surgery_homology")).get("toroidal_genus_g"), 0
                ),
                "euler_characteristic_chi": _i(
                    _d(fr.get("toroidal_surgery_homology")).get("euler_characteristic_chi"), 1
                ),
                "cycle1_mass_conservation_residual": _f(
                    _d(fr.get("hawking_radiation_memory_sink")).get("cycle1_mass_conservation_residual"), 1.0
                ),
                "sacred_core_immutable": bool(
                    _d(fr.get("hawking_radiation_memory_sink")).get("sacred_core_immutable", False)
                ),
                "authorized_claimed": bool(
                    _d(fr.get("eligibility_interlock")).get("authorized_claimed", True)
                ),
                "summary_digest": fr.get("frontier_r_summary_digest") or fr.get("summary_digest"),
            }
            if isinstance(fr, dict)
            else {
                "verified": bool(cand_cond.get("frontier_r_verified", False)),
                "sacred_core_immutable": True,
                "authorized_claimed": False,
                "summary_digest": cand_cond.get("frontier_r_summary_digest"),
            }
        ),
        "frontier_s_verified": fs_verified_bool,
        "frontier_s_summary_digest": (
            fs.get("frontier_s_summary_digest") or fs.get("summary_digest")
            if isinstance(fs, dict)
            else cand_cond.get("frontier_s_summary_digest")
        ),
        "frontier_s": (
            {
                "verified": fs_verified_bool,
                "pdm_8bit_passed": _i(
                    _d(fs.get("coprime_quadrature_pdm")).get("passed_cases"), 0
                ),
                "pdm_8bit_passed_cases": _i(
                    _d(fs.get("coprime_quadrature_pdm")).get("passed_cases"), 0
                ),
                "prefix_carry_passed": _i(
                    _d(fs.get("interlane_prefix_carry")).get("passed_cases"), 0
                ),
                "prefix_carry_passed_cases": _i(
                    _d(fs.get("interlane_prefix_carry")).get("passed_cases"), 0
                ),
                "hierarchical_32b_passed": _i(
                    _d(fs.get("hierarchical_waveguide_fabric")).get("passed_32b"), 0
                ),
                "hierarchical_64b_passed": _i(
                    _d(fs.get("hierarchical_waveguide_fabric")).get("passed_64b"), 0
                ),
                "quantum_regimes_passed": _i(
                    _d(fs.get("quantum_wavefront_calibration")).get("passed_regimes"), 0
                ),
                "cycle1_interlane_crosstalk_db": _f(
                    _d(fs.get("autonomic_mhd_gru_jeans_bus")).get("cycle1_interlane_crosstalk_db"), 0.0
                ),
                "authorized_claimed": bool(
                    _d(fs.get("eligibility_interlock")).get("authorized_claimed", True)
                ),
                "summary_digest": fs.get("frontier_s_summary_digest") or fs.get("summary_digest"),
            }
            if isinstance(fs, dict)
            else {
                "verified": bool(cand_cond.get("frontier_s_verified", False)),
                "authorized_claimed": False,
                "summary_digest": cand_cond.get("frontier_s_summary_digest"),
            }
        ),
        "frontier_t_verified": ft_verified_bool,
        "frontier_t_summary_digest": (
            ft.get("frontier_t_summary_digest") or ft.get("summary_digest")
            if isinstance(ft, dict)
            else cand_cond.get("frontier_t_summary_digest")
        ),
        "frontier_t": (
            {
                "verified": ft_verified_bool,
                "compiled_verified_claims": _i(
                    _d(ft.get("sandboxed_rsi_and_claim_compiler")).get(
                        "compiled_verified_claims",
                        _d(ft.get("sandboxed_rsi_and_claim_compiler")).get("claims_verified_count", 0),
                    ),
                    0,
                ),
                "admitted_passes_count": len(
                    _l(_d(ft.get("governed_compiler_invocation")).get("cycle1_admitted_passes"))
                ),
                "replay_verified_count": _i(
                    _d(ft.get("governed_pass_replay")).get("replay_verified_count"), 0
                ),
                "replay_failed_count": _i(
                    _d(ft.get("governed_pass_replay")).get("replay_failed_count"), 1
                ),
                "certification_status": str(
                    _d(ft.get("release_certification_bundle")).get("certification_status") or ""
                ),
                "production_mutation_allowed": bool(
                    _d(ft.get("eligibility_interlock")).get("production_mutation_allowed", True)
                ),
                "authorized_claimed": bool(
                    _d(ft.get("eligibility_interlock")).get("authorized_claimed", True)
                ),
                "summary_digest": ft.get("frontier_t_summary_digest") or ft.get("summary_digest"),
            }
            if isinstance(ft, dict)
            else {
                "verified": bool(cand_cond.get("frontier_t_verified", False)),
                "production_mutation_allowed": False,
                "authorized_claimed": False,
                "summary_digest": cand_cond.get("frontier_t_summary_digest"),
            }
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


_T_CRIT_95 = {
    1: 12.706205,
    2: 4.302653,
    3: 3.182446,
    4: 2.776445,
    5: 2.570582,
    6: 2.446912,
    7: 2.364624,
    8: 2.306004,
    9: 2.262157,
    10: 2.228139,
    11: 2.200985,
    12: 2.178813,
    13: 2.160369,
    14: 2.144787,
    15: 2.131450,
    16: 2.119905,
    17: 2.109816,
    18: 2.100922,
    19: 2.093024,
    20: 2.085963,
    25: 2.059539,
    30: 2.042272,
}


def _t_critical_95(df: float) -> float:
    df_int = max(1, int(round(df)))
    if df_int in _T_CRIT_95:
        return _T_CRIT_95[df_int]
    if df_int < 30:
        return 1.959964 + 2.372 / float(df_int) + 2.82 / float(df_int * df_int)
    return 1.959964 + 2.372 / max(float(df), 1.0)


def _student_t_two_sided_pvalue(t_abs: float, df: float) -> float:
    """Two-sided p-value for Student's t-distribution using exact/Hill normal transformation."""
    if not math.isfinite(t_abs) or t_abs <= 0.0:
        return 1.0
    if df <= 0.0:
        return 1.0
    if df >= 1e6:
        return float(math.erfc(t_abs / math.sqrt(2.0)))
    # Peizer-Pratt / Wallace normal approximation for Student's t -> standard normal z
    # Accurate across all df >= 1 and monotonic in |t|
    a = df - 0.5
    b = 48.0 * a * a
    z2 = a * math.log1p((t_abs * t_abs) / df)
    z = math.sqrt(z2) * (
        1.0
        - (z2 + 3.0) / b
        + (4.0 * z2 * z2 + 33.0 * z2 + 24.0) / (10.0 * b * b)
    )
    p = float(math.erfc(max(0.0, z) / math.sqrt(2.0)))
    return max(0.0, min(1.0, p))


def validate_repeat_trial_group(group: dict) -> dict:
    """
    Validates a `sol-change/repeat-trial-group` v1.0 artifact:
    - Enforces schema_version == "1.0" and kind == "sol-change/repeat-trial-group"
    - Enforces K >= 3 trials (`trial_count >= 3` and `len(trials) == trial_count`)
    - Validates every trial's `baseline_run` and `candidate_run` via `validate_run`
    - Verifies every trial shares identical `input` / `shared_input.digest` and `evaluator_version`
    """
    c = Check()
    group = c.obj(
        group,
        "repeat_trial_group",
        ("schema_version", "kind", "group_id", "created_at", "shared_input", "evaluator_version", "trial_count", "trials"),
        ("study_name", "baseline_workflow_version", "candidate_workflow_version", "statistical_summary"),
    )
    c.need(group.get("schema_version") == "1.0", "repeat_trial_group.schema_version must be 1.0.")
    c.need(
        group.get("kind") == REPEAT_TRIAL_GROUP_KIND,
        f"repeat_trial_group.kind must be {REPEAT_TRIAL_GROUP_KIND}.",
    )
    c.ident(group.get("group_id"), "repeat_trial_group.group_id")
    c.timestamp(group.get("created_at"), "repeat_trial_group.created_at")
    c.string(group.get("evaluator_version"), "repeat_trial_group.evaluator_version", limit=500)
    if "study_name" in group:
        c.string(group.get("study_name"), "repeat_trial_group.study_name", limit=500)
    if "baseline_workflow_version" in group and group.get("baseline_workflow_version") is not None:
        c.string(group.get("baseline_workflow_version"), "repeat_trial_group.baseline_workflow_version", limit=200)
    if "candidate_workflow_version" in group and group.get("candidate_workflow_version") is not None:
        c.string(group.get("candidate_workflow_version"), "repeat_trial_group.candidate_workflow_version", limit=200)

    shared_input = c.obj(
        group.get("shared_input"),
        "repeat_trial_group.shared_input",
        ("id", "digest"),
        ("dataset_version", "description"),
    )
    c.string(shared_input.get("id"), "repeat_trial_group.shared_input.id", limit=500)
    c.string(shared_input.get("digest"), "repeat_trial_group.shared_input.digest", limit=200)
    if "dataset_version" in shared_input:
        c.string(shared_input.get("dataset_version"), "repeat_trial_group.shared_input.dataset_version", limit=200)
    if "description" in shared_input:
        c.string(shared_input.get("description"), "repeat_trial_group.shared_input.description", limit=10_000)

    trial_count = group.get("trial_count")
    c.need(
        type(trial_count) is int and trial_count >= 3,
        "repeat_trial_group.trial_count must be an integer >= 3 (minimum 3 trials required for statistical evaluation).",
    )
    trials = c.array(group.get("trials"), "repeat_trial_group.trials", limit=1000)
    c.need(
        len(trials) >= 3,
        "repeat_trial_group.trials must contain at least 3 paired trials (K >= 3).",
    )
    if type(trial_count) is int:
        c.need(
            len(trials) == trial_count,
            f"repeat_trial_group.trials length ({len(trials)}) must match trial_count ({trial_count}).",
        )
    c.finish()

    expected_eval_ver = group["evaluator_version"]
    expected_input_id = shared_input["id"]
    expected_input_digest = shared_input["digest"]
    reference_run_input: str | None = None
    seen_trial_indices: set[int] = set()
    reference_base_wf_ver = group.get("baseline_workflow_version")
    reference_cand_wf_ver = group.get("candidate_workflow_version")

    for idx, trial in enumerate(trials):
        tp = f"repeat_trial_group.trials[{idx}]"
        trial_obj = c.obj(
            trial,
            tp,
            ("trial_index", "seed", "baseline_run", "candidate_run"),
            (
                "wgsl_metrics",
                "swarm_metrics",
                "umok_metrics",
                "mitotic_metrics",
                "stwm_metrics",
                "rsi_compiler_metrics",
            ),
        )
        c.need(type(trial_obj.get("trial_index")) is int and trial_obj["trial_index"] >= 0, f"{tp}.trial_index must be a non-negative integer.")
        c.need(type(trial_obj.get("seed")) is int, f"{tp}.seed must be an integer.")
        for _opt_m in (
            "wgsl_metrics",
            "swarm_metrics",
            "umok_metrics",
            "mitotic_metrics",
            "stwm_metrics",
            "rsi_compiler_metrics",
        ):
            if _opt_m in trial_obj:
                c.need(isinstance(trial_obj[_opt_m], dict), f"{tp}.{_opt_m} must be an object.")
        c.finish()

        t_index = int(trial_obj["trial_index"])
        if t_index in seen_trial_indices:
            raise ValidationError(f"{tp}.trial_index ({t_index}) is duplicated across trials.")
        seen_trial_indices.add(t_index)

        for opt_metric_field in (
            "wgsl_metrics",
            "swarm_metrics",
            "umok_metrics",
            "mitotic_metrics",
            "stwm_metrics",
            "rsi_compiler_metrics",
        ):
            if opt_metric_field in trial_obj:
                for wm_key, wm_val in trial_obj[opt_metric_field].items():
                    if not isinstance(wm_key, str) or not wm_key.strip() or len(wm_key) > 128:
                        raise ValidationError(f"{tp}.{opt_metric_field} keys must be non-empty strings (<= 128 chars).")
                    if type(wm_val) not in (int, float) or not math.isfinite(float(wm_val)):
                        raise ValidationError(f"{tp}.{opt_metric_field}.{wm_key} must be a finite number.")


        base_run = trial_obj["baseline_run"]
        cand_run = trial_obj["candidate_run"]
        validate_run(base_run)
        validate_run(cand_run)
        if base_run.get("designation") != "baseline":
            raise ValidationError(f"{tp}.baseline_run.designation must be 'baseline'.")
        if cand_run.get("designation") != "candidate":
            raise ValidationError(f"{tp}.candidate_run.designation must be 'candidate'.")

        base_wf = base_run.get("workflow_version")
        cand_wf = cand_run.get("workflow_version")
        if reference_base_wf_ver is None:
            reference_base_wf_ver = base_wf
        elif base_wf != reference_base_wf_ver:
            raise ValidationError(
                f"{tp}.baseline_run.workflow_version ({base_wf}) does not match group baseline workflow_version ({reference_base_wf_ver})."
            )
        if reference_cand_wf_ver is None:
            reference_cand_wf_ver = cand_wf
        elif cand_wf != reference_cand_wf_ver:
            raise ValidationError(
                f"{tp}.candidate_run.workflow_version ({cand_wf}) does not match group candidate workflow_version ({reference_cand_wf_ver})."
            )

        if base_run.get("input") != cand_run.get("input"):
            raise ValidationError(f"{tp} baseline_run and candidate_run have mismatched input strings.")
        if reference_run_input is None:
            reference_run_input = str(base_run.get("input"))
        elif str(base_run.get("input")) != reference_run_input:
            raise ValidationError(f"{tp} input does not match prior trials' shared input.")

        for role_label, run_doc in (("baseline_run", base_run), ("candidate_run", cand_run)):
            cond = run_doc.get("conditions", {}) if isinstance(run_doc.get("conditions"), dict) else {}
            if "input_id" in cond and cond["input_id"] != expected_input_id:
                raise ValidationError(
                    f"{tp}.{role_label}.conditions.input_id ({cond['input_id']}) does not match shared_input.id ({expected_input_id})."
                )
            if "input_digest" in cond and cond["input_digest"] != expected_input_digest:
                raise ValidationError(
                    f"{tp}.{role_label}.conditions.input_digest ({cond['input_digest']}) does not match shared_input.digest ({expected_input_digest})."
                )
            sc_ctx = (
                run_doc.get("configuration", {})
                .get("sol_continuum", {})
                .get("context", {})
            )
            if isinstance(sc_ctx, dict) and sc_ctx.get("evaluator_version"):
                if sc_ctx["evaluator_version"] != expected_eval_ver:
                    raise ValidationError(
                        f"{tp}.{role_label} context evaluator_version ({sc_ctx['evaluator_version']}) "
                        f"does not match group evaluator_version ({expected_eval_ver})."
                    )
            for m in run_doc.get("measurements", []):
                cid = str(m.get("criterion_id", ""))
                if cid.startswith("lens_"):
                    m_ver = m.get("method", {}).get("version")
                    if m_ver is not None and m_ver != expected_eval_ver:
                        raise ValidationError(
                            f"{tp}.{role_label} measurement '{cid}' method.version ({m_ver}) "
                            f"does not match group evaluator_version ({expected_eval_ver})."
                        )

    return group


def _compute_paired_metric_stats(
    criterion_id: str,
    unit: str,
    direction: str,
    base_vals: list[float],
    cand_vals: list[float],
) -> dict:
    n = len(base_vals)
    if n < 3 or len(cand_vals) != n:
        return {
            "criterion_id": criterion_id,
            "unit": unit,
            "direction": direction,
            "trial_count": n,
            "status": "unknown",
        }

    mean_b = sum(base_vals) / n
    mean_c = sum(cand_vals) / n
    deltas = [c - b for b, c in zip(base_vals, cand_vals)]
    mean_d = sum(deltas) / n

    var_b = sum((x - mean_b) ** 2 for x in base_vals) / (n - 1)
    var_c = sum((x - mean_c) ** 2 for x in cand_vals) / (n - 1)
    var_d = sum((d - mean_d) ** 2 for d in deltas) / (n - 1)

    std_b = math.sqrt(max(0.0, var_b))
    std_c = math.sqrt(max(0.0, var_c))
    std_d = math.sqrt(max(0.0, var_d))

    se_d = std_d / math.sqrt(n)
    t_crit = _t_critical_95(n - 1)
    ci95_lower = mean_d - t_crit * se_d
    ci95_upper = mean_d + t_crit * se_d

    # Welch's two-sample t-statistic & degrees of freedom
    se_welch_sq = (var_b / n) + (var_c / n)
    if se_welch_sq > 1e-18:
        welch_t = (mean_c - mean_b) / math.sqrt(se_welch_sq)
        num = se_welch_sq * se_welch_sq
        den = ((var_b / n) ** 2) / (n - 1) + ((var_c / n) ** 2) / (n - 1)
        welch_df = num / den if den > 1e-24 else float(2 * n - 2)
        p_val = _student_t_two_sided_pvalue(abs(welch_t), welch_df)
    elif abs(mean_d) > 1e-12:
        # Zero sample variance across replicates with non-zero shift
        welch_t = math.copysign(999.0, mean_d)
        welch_df = float(2 * n - 2)
        p_val = 0.0
    else:
        welch_t = 0.0
        welch_df = float(2 * n - 2)
        p_val = 1.0

    if se_d > 1e-18:
        paired_t = mean_d / se_d
    elif abs(mean_d) > 1e-12:
        paired_t = math.copysign(999.0, mean_d)
    else:
        paired_t = 0.0

    pooled_var = 0.5 * (var_b + var_c)
    if pooled_var > 1e-18:
        cohens_d = (mean_c - mean_b) / math.sqrt(pooled_var)
    elif std_d > 1e-18:
        cohens_d = mean_d / std_d
    elif abs(mean_d) > 1e-12:
        cohens_d = math.copysign(99.0, mean_d)
    else:
        cohens_d = 0.0

    oriented_delta = -mean_d if direction == "lower" else mean_d
    if abs(mean_d) <= 1e-12:
        status = "unchanged"
    elif oriented_delta > 0:
        status = "improved"
    else:
        status = "regressed"

    return {
        "criterion_id": criterion_id,
        "unit": unit,
        "direction": direction,
        "trial_count": n,
        "baseline_mean": round(mean_b, 6),
        "baseline_std": round(std_b, 6),
        "candidate_mean": round(mean_c, 6),
        "candidate_std": round(std_c, 6),
        "mean_delta": round(mean_d, 6),
        "std_delta": round(std_d, 6),
        "ci95_lower": round(ci95_lower, 6),
        "ci95_upper": round(ci95_upper, 6),
        "welch_t_stat": round(welch_t, 6),
        "welch_df": round(welch_df, 4),
        "paired_t_stat": round(paired_t, 6),
        "p_value_two_sided": round(p_val, 8),
        "cohens_d": round(cohens_d, 6),
        "statistically_significant_95": bool(p_val < 0.05),
        "status": status,
    }


def evaluate_repeat_trial_group(group: dict | Path) -> dict:
    """
    Validates a `sol-change/repeat-trial-group` v1.0 artifact and computes sample mean,
    sample standard deviation, 95% confidence interval, Welch's t-statistic, two-sided
    p-value, and Cohen's d effect size across the K >= 3 paired runs.
    """
    if isinstance(group, Path) or isinstance(group, str):
        raw_text, _ = read_artifact(Path(group))
        group_doc = parse_json(raw_text)
    else:
        group_doc = group

    validate_repeat_trial_group(group_doc)
    trials = group_doc["trials"]
    k = len(trials)

    direction_map = {f"lens_{name}": direction for name, _, direction in METRICS}
    direction_map.update({
        "execution_time": "lower",
        "cost": "lower",
        "human_review": "higher",
    })
    unit_map = {f"lens_{name}": "score/1" for name, _, _ in METRICS}
    unit_map.update({
        "execution_time": "s",
        "cost": "USD",
        "human_review": "rating/5",
    })

    criterion_order = [f"lens_{name}" for name, _, _ in METRICS] + [
        "execution_time",
        "cost",
        "human_review",
    ]
    metric_summaries: dict[str, dict] = {}
    improved_count = 0
    regressed_count = 0
    unknown_count = 0

    for cid in criterion_order:
        b_vals: list[float] = []
        c_vals: list[float] = []
        for t in trials:
            b_m = next((m for m in t["baseline_run"].get("measurements", []) if m["criterion_id"] == cid), None)
            c_m = next((m for m in t["candidate_run"].get("measurements", []) if m["criterion_id"] == cid), None)
            if (
                b_m is not None
                and c_m is not None
                and type(b_m.get("value")) in (int, float)
                and type(c_m.get("value")) in (int, float)
            ):
                b_vals.append(float(b_m["value"]))
                c_vals.append(float(c_m["value"]))

        if len(b_vals) == k:
            stats = _compute_paired_metric_stats(
                criterion_id=cid,
                unit=unit_map[cid],
                direction=direction_map[cid],
                base_vals=b_vals,
                cand_vals=c_vals,
            )
            metric_summaries[cid] = stats
            if stats["status"] == "improved":
                improved_count += 1
            elif stats["status"] == "regressed":
                regressed_count += 1
        else:
            unknown_count += 1
            metric_summaries[cid] = {
                "criterion_id": cid,
                "unit": unit_map[cid],
                "direction": direction_map[cid],
                "trial_count": len(b_vals),
                "status": "unknown",
            }

    def _summarize_domain_pairs(
        field_name: str,
        pairs: tuple[tuple[str, str, str, str, str], ...],
    ) -> dict[str, dict]:
        summary: dict[str, dict] = {}
        for metric_key, b_key, c_key, unit, direction in pairs:
            b_vals = []
            c_vals = []
            for t in trials:
                dm = t.get(field_name)
                if isinstance(dm, dict) and type(dm.get(b_key)) in (int, float) and type(dm.get(c_key)) in (int, float):
                    b_vals.append(float(dm[b_key]))
                    c_vals.append(float(dm[c_key]))
            if len(b_vals) == k:
                summary[metric_key] = _compute_paired_metric_stats(
                    criterion_id=metric_key,
                    unit=unit,
                    direction=direction,
                    base_vals=b_vals,
                    cand_vals=c_vals,
                )
        return summary

    # Optional domain metrics across trials (Frontiers O, P, Q, R, S, T)
    wgsl_summary = _summarize_domain_pairs(
        "wgsl_metrics",
        (
            ("min_inflection_delta_pct", "baseline_min_inflection_delta_pct", "candidate_min_inflection_delta_pct", "%", "higher"),
            ("winner_stability_fraction", "baseline_winner_stability", "candidate_winner_stability", "fraction", "higher"),
            ("prover_latency_ms", "serial_cpu_latency_ms", "wgsl_simd_latency_ms", "ms", "lower"),
        ),
    )
    swarm_summary = _summarize_domain_pairs(
        "swarm_metrics",
        (
            ("internal_squeeze_wrench_n", "baseline_internal_squeeze_wrench_n", "candidate_internal_squeeze_wrench_n", "N", "lower"),
            ("se3_rotational_holonomy_deg", "baseline_se3_rotational_holonomy_deg", "candidate_se3_rotational_holonomy_deg", "deg", "lower"),
        ),
    )
    umok_summary = _summarize_domain_pairs(
        "umok_metrics",
        (
            ("mean_step_latency_us", "baseline_mean_step_latency_us", "candidate_mean_step_latency_us", "us", "lower"),
        ),
    )
    mitotic_summary = _summarize_domain_pairs(
        "mitotic_metrics",
        (
            ("mass_conservation_residual", "baseline_mass_conservation_residual", "candidate_mass_conservation_residual", "residual", "lower"),
            ("phase_dissonance_rad", "baseline_phase_dissonance_rad", "candidate_phase_dissonance_rad", "rad", "lower"),
        ),
    )
    stwm_summary = _summarize_domain_pairs(
        "stwm_metrics",
        (
            ("interlane_crosstalk_db", "baseline_interlane_crosstalk_db", "candidate_interlane_crosstalk_db", "dB", "lower"),
        ),
    )
    rsi_compiler_summary = _summarize_domain_pairs(
        "rsi_compiler_metrics",
        (
            ("admitted_passes_count", "baseline_admitted_passes_count", "candidate_admitted_passes_count", "count", "higher"),
        ),
    )

    if improved_count > 0 and regressed_count == 0:
        overall_outcome = "improved"
    elif regressed_count > 0 and improved_count == 0:
        overall_outcome = "regressed"
    elif improved_count > 0 and regressed_count > 0:
        overall_outcome = "mixed"
    else:
        overall_outcome = "inconclusive"

    return {
        "schema_version": "1.0",
        "kind": "sol-change/repeat-trial-evaluation",
        "group_id": group_doc["group_id"],
        "study_name": group_doc.get("study_name", group_doc["group_id"]),
        "evaluated_at": now(),
        "trial_count": k,
        "shared_input": group_doc["shared_input"],
        "evaluator_version": group_doc["evaluator_version"],
        "comparability": "compatible",
        "outcome": overall_outcome,
        "counts": {
            "improved": improved_count,
            "regressed": regressed_count,
            "unknown": unknown_count,
        },
        "metrics": metric_summaries,
        "wgsl_trial_summary": wgsl_summary,
        "swarm_trial_summary": swarm_summary,
        "umok_trial_summary": umok_summary,
        "mitotic_trial_summary": mitotic_summary,
        "stwm_trial_summary": stwm_summary,
        "rsi_compiler_trial_summary": rsi_compiler_summary,
        "review_status": "awaiting_review",
        "human_decisions_created": 0,
        "authority_boundary": (
            "Repeat-trial confidence intervals, Welch's t-statistics, and Cohen's d effect sizes "
            "provide statistical evidence for human review and never auto-approve release."
        ),
    }


def format_repeat_trial_evaluation_text(report: dict) -> str:
    lines = [
        f"SOL Change Repeat-Trial Statistical Evaluation — {report.get('group_id')}",
        f"Study: {report.get('study_name')} | Trials (K): {report.get('trial_count')} | Outcome: {report.get('outcome')}",
        f"Shared Input: {report.get('shared_input', {}).get('id')} ({report.get('shared_input', {}).get('digest')})",
        f"Evaluator Version: {report.get('evaluator_version')} | Review Status: {report.get('review_status')}",
        "",
        "Criterion Statistical Summary (Mean Delta, 95% CI, Welch t, p-value, Cohen's d):",
    ]
    for cid, stats in report.get("metrics", {}).items():
        if stats.get("status") == "unknown":
            lines.append(f"  - {cid}: unknown (unmeasured in one or more trials)")
        else:
            lines.append(
                f"  - {cid} ({stats['unit']}): {stats['baseline_mean']:.4f} -> {stats['candidate_mean']:.4f} "
                f"| delta={stats['mean_delta']:+.4f} "
                f"95% CI [{stats['ci95_lower']:+.4f}, {stats['ci95_upper']:+.4f}] "
                f"| t={stats['welch_t_stat']:+.3f} (p={stats['p_value_two_sided']:.4g}) "
                f"| d={stats['cohens_d']:+.3f} [{stats['status']}]"
            )
    if report.get("wgsl_trial_summary"):
        lines.append("")
        lines.append("WGSL Prover Domain Metrics:")
        for mk, stats in report["wgsl_trial_summary"].items():
            lines.append(
                f"  - {mk} ({stats['unit']}): {stats['baseline_mean']:.4f} -> {stats['candidate_mean']:.4f} "
                f"| delta={stats['mean_delta']:+.4f} "
                f"95% CI [{stats['ci95_lower']:+.4f}, {stats['ci95_upper']:+.4f}] "
                f"| t={stats['welch_t_stat']:+.3f} | d={stats['cohens_d']:+.3f}"
            )
    lines.append("")
    lines.append(report.get("authority_boundary", ""))
    return "\n".join(lines)


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
    convert.add_argument("--measured-time-s", type=float, default=None, help="Optional measured wall-clock execution time in seconds")
    convert.add_argument("--measured-cost-usd", type=float, default=None, help="Optional measured API token cost in USD")
    convert.add_argument("--output", type=Path, required=True)
    for cmd_name in ("compare", "import-continuum"):
        pair = commands.add_parser(cmd_name, help="Prepare a reviewable experiment from two saved packet observations")
        pair.add_argument("--baseline", type=Path, required=True)
        pair.add_argument("--candidate", type=Path, required=True)
        pair.add_argument("--baseline-context", type=Path)
        pair.add_argument("--candidate-context", type=Path)
        pair.add_argument("--baseline-measured-time-s", type=float, default=None)
        pair.add_argument("--candidate-measured-time-s", type=float, default=None)
        pair.add_argument("--baseline-measured-cost-usd", type=float, default=None)
        pair.add_argument("--candidate-measured-cost-usd", type=float, default=None)
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
    trials_cmd = commands.add_parser("evaluate-trials", help="Validate and statistically evaluate a repeat-trial-group (K >= 3) bundle")
    trials_cmd.add_argument("--group", type=Path, required=True, help="Path to repeat-trial-group JSON file")
    trials_cmd.add_argument("--format", choices=("json", "text"), default="json", help="Output format (json or text)")
    trials_cmd.add_argument("--output", type=Path, help="Optional path to write evaluation JSON report")
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
        if args.command == "evaluate-trials":
            result = evaluate_repeat_trial_group(args.group)
            if args.output:
                write_new(args.output, result)
            if args.format == "text":
                print(format_repeat_trial_evaluation_text(result))
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        def convert_file(path, designation, context_path=None, measured_time_s=None, measured_cost_usd=None):
            source, _ = read_artifact(path)
            context = parse_json(read_artifact(context_path)[0]) if context_path else None
            return packet_to_run(
                source,
                designation,
                path.as_posix(),
                context,
                measured_execution_time_s=measured_time_s,
                measured_cost_usd=measured_cost_usd,
            )
        if args.command == "convert":
            run = convert_file(
                args.packet,
                args.designation,
                args.context,
                measured_time_s=args.measured_time_s,
                measured_cost_usd=args.measured_cost_usd,
            )
            write_new(args.output, run)
            print(f"Prepared {args.output}. Source preserved; no experiment or decision was created.")
            return 0
        baseline = convert_file(
            args.baseline,
            "baseline",
            args.baseline_context,
            measured_time_s=args.baseline_measured_time_s,
            measured_cost_usd=args.baseline_measured_cost_usd,
        )
        candidate = convert_file(
            args.candidate,
            "candidate",
            args.candidate_context,
            measured_time_s=args.candidate_measured_time_s,
            measured_cost_usd=args.candidate_measured_cost_usd,
        )
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

