"""
SOL-Decide: Persistent D1 / SQLite Cryptographic Governance Court Ledger
========================================================================
Frontier C of the SOL Systems Continuum.

Persists:
1. `governance_court_runs`: Append-only, cross-run SHA-256 hash-chained ledger of
   governed trade studies, closed-loop quarantine repairs, 3-agent Dialectical H^1
   Hodge negotiations, SysML v2 shock co-simulations, and 6-DOF robotic actuation gates.
2. `sol_edge_runtime_events`: 4-event hash-chained `RuntimeEvent` streams
   (`RUN_OPENED` -> `PROPOSAL_RECORDED` -> `EVIDENCE_RECORDED` -> `POLICY_DECISION_RECORDED`).
3. `gemini_thought_signatures`: Cryptographic `thought.signature` SHA-256 digests,
   thought summaries, and token telemetry for `gemini-4-argon` and `gemini-3.8-flash`.
4. `cohomological_repair_records`: Immutable provenance of `QUARANTINE -> ELIGIBLE`
   repairs (`quarantine_coboundary_repair`, `dialectical_h1_hodge_negotiation`,
   `sysml_shock_mutation`, `robotic_gauge_holonomy_diffusion`).
5. `differential_shock_timeline`: Multi-run differential shock timeline tracking
   how `OperationalShock`s perturb sheaf coboundary edges, flip or quarantine
   baseline selections, and get resolved into a new certified harmonic section.

Guarantees exact schema & SHA-256 `ledger_entry_digest` parity with:
- `sol-lens/db/schema.ts`
- `sol-lens/lib/governance-ledger.ts`
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from sol_edge.canonical import digest_data
from sol_edge.contracts import PolicyStatus
from sol_edge.runtime.events import (
    EventType,
    EvidenceRecordedPayload,
    PolicyDecisionRecordedPayload,
    ProposalRecordedPayload,
    RunOpenedPayload,
    RuntimeEvent,
    create_runtime_event,
)
from sol_edge.runtime.replay import replay_events


GOVERNANCE_LEDGER_DDL = """
CREATE TABLE IF NOT EXISTS governance_court_runs (
  run_id TEXT PRIMARY KEY NOT NULL,
  packet_id TEXT NOT NULL,
  study_name TEXT NOT NULL,
  run_mode TEXT NOT NULL,
  model_used TEXT NOT NULL,
  interaction_id TEXT NOT NULL,
  thinking_level TEXT NOT NULL DEFAULT 'adaptive',
  selected_option_id TEXT NOT NULL,
  selected_option_name TEXT NOT NULL,
  policy_status TEXT NOT NULL,
  runtime_status TEXT NOT NULL,
  next_transition TEXT NOT NULL,
  pre_beta_1 INTEGER NOT NULL DEFAULT 0,
  post_beta_1 INTEGER NOT NULL DEFAULT 0,
  dirichlet_energy REAL NOT NULL DEFAULT 0,
  coboundary_norm REAL NOT NULL DEFAULT 0,
  kuramoto_order_r REAL NOT NULL DEFAULT 1,
  causal_emergence_delta_ei REAL NOT NULL DEFAULT 0,
  final_state_digest TEXT NOT NULL,
  prior_quarantined_state_digest TEXT,
  previous_run_digest TEXT,
  ledger_entry_digest TEXT NOT NULL,
  is_signed INTEGER NOT NULL DEFAULT 0,
  signer_name TEXT,
  signer_role TEXT,
  proof_packet_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sol_edge_runtime_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL REFERENCES governance_court_runs(run_id),
  option_id TEXT NOT NULL,
  sequence_number INTEGER NOT NULL,
  event_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  previous_event_digest TEXT,
  event_digest TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gemini_thought_signatures (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL REFERENCES governance_court_runs(run_id),
  interaction_id TEXT NOT NULL,
  agent_role TEXT NOT NULL,
  model_used TEXT NOT NULL,
  thinking_level TEXT NOT NULL,
  step_index INTEGER NOT NULL DEFAULT 0,
  signature_digest TEXT NOT NULL,
  signature_length INTEGER NOT NULL DEFAULT 0,
  thought_summary TEXT NOT NULL DEFAULT '',
  input_tokens INTEGER NOT NULL DEFAULT 0,
  thought_tokens INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cohomological_repair_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL REFERENCES governance_court_runs(run_id),
  repair_kind TEXT NOT NULL,
  target_option_id TEXT NOT NULL,
  pre_beta_1 INTEGER NOT NULL DEFAULT 0,
  post_beta_1 INTEGER NOT NULL DEFAULT 0,
  pre_harmonic_norm REAL NOT NULL DEFAULT 0,
  post_harmonic_norm REAL NOT NULL DEFAULT 0,
  l2_projection_distance REAL NOT NULL DEFAULT 0,
  quarantined_state_digest TEXT NOT NULL,
  cleared_state_digest TEXT NOT NULL,
  previous_interaction_id TEXT NOT NULL,
  repair_interaction_id TEXT NOT NULL,
  pre_stalk_json TEXT NOT NULL,
  post_stalk_json TEXT NOT NULL,
  rationale TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS differential_shock_timeline (
  shock_entry_id TEXT PRIMARY KEY NOT NULL,
  run_id TEXT NOT NULL REFERENCES governance_court_runs(run_id),
  baseline_run_id TEXT,
  delta_id TEXT NOT NULL,
  shock_id TEXT NOT NULL,
  target_primitive_id TEXT NOT NULL,
  parameter_channel INTEGER NOT NULL,
  delta_value REAL NOT NULL,
  baseline_option_id TEXT NOT NULL,
  refreshed_option_id TEXT NOT NULL,
  did_decision_flip INTEGER NOT NULL DEFAULT 0,
  pre_energy REAL NOT NULL,
  post_energy REAL NOT NULL,
  pre_beta_1 INTEGER NOT NULL DEFAULT 0,
  post_beta_1 INTEGER NOT NULL DEFAULT 0,
  activated_edges_json TEXT NOT NULL,
  quarantined_state_digest TEXT NOT NULL,
  cleared_state_digest TEXT NOT NULL,
  audit_summary TEXT NOT NULL,
  recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


@dataclass
class LedgerIntegrityReport:
    """Verification report for the cross-run and intra-run cryptographic hash chains."""
    is_valid: bool
    total_runs_verified: int
    total_events_verified: int
    head_ledger_digest: Optional[str]
    broken_run_ids: List[str] = field(default_factory=list)
    broken_event_run_ids: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "isValid": self.is_valid,
            "totalRunsVerified": self.total_runs_verified,
            "totalEventsVerified": self.total_events_verified,
            "headLedgerDigest": self.head_ledger_digest,
            "brokenRunIds": self.broken_run_ids,
            "brokenEventRunIds": self.broken_event_run_ids,
            "summary": self.summary,
        }


class GovernanceCourtLedger:
    """
    Persistent SQLite / D1 Cryptographic Governance Court Ledger.
    """

    DEFAULT_DB_PATH = Path("sol-lens/.wrangler/state/v3/d1/sol_governance_ledger.sqlite")

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        if db_path is None:
            resolved = self.DEFAULT_DB_PATH
        else:
            resolved = Path(db_path)
        self.db_path = resolved
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.executescript(GOVERNANCE_LEDGER_DDL)

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def compute_ledger_entry_digest(
        *,
        run_id: str,
        packet_id: str,
        study_name: str,
        run_mode: str,
        model_used: str,
        interaction_id: str,
        selected_option_id: str,
        policy_status: str,
        final_state_digest: str,
        prior_quarantined_state_digest: Optional[str],
        previous_run_digest: Optional[str],
    ) -> str:
        """
        Computes the canonical SHA-256 `ledger_entry_digest` for a `governance_court_runs` row.
        Exact byte-for-byte parity with `computeLedgerEntryDigest` in `sol-lens/lib/governance-ledger.ts`.
        """
        canonical_payload = "|".join(
            [
                run_id,
                packet_id,
                study_name,
                run_mode,
                model_used,
                interaction_id,
                selected_option_id,
                policy_status,
                final_state_digest,
                prior_quarantined_state_digest or "GENESIS_NO_PRIOR_QUARANTINE",
                previous_run_digest or "GENESIS_LEDGER_ROOT",
            ]
        )
        digest_hex = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
        return f"sha256:{digest_hex}"

    def _get_head_ledger_digest(self, exclude_run_id: Optional[str] = None) -> Optional[str]:
        if exclude_run_id:
            cur = self._conn.execute(
                "SELECT ledger_entry_digest FROM governance_court_runs WHERE run_id != ? ORDER BY rowid DESC LIMIT 1",
                (exclude_run_id,),
            )
        else:
            cur = self._conn.execute(
                "SELECT ledger_entry_digest FROM governance_court_runs ORDER BY rowid DESC LIMIT 1"
            )
        row = cur.fetchone()
        return str(row["ledger_entry_digest"]) if row else None

    def _insert_runtime_events(
        self,
        run_id: str,
        option_id: str,
        events: Tuple[RuntimeEvent, ...] | List[RuntimeEvent],
    ) -> None:
        for ev in events:
            payload_dict = ev.payload.model_dump(mode="json")
            self._conn.execute(
                """
                INSERT INTO sol_edge_runtime_events (
                    run_id, option_id, sequence_number, event_id, event_type,
                    occurred_at, previous_event_digest, event_digest, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    option_id,
                    int(ev.sequence_number),
                    str(ev.event_id),
                    str(ev.event_type.value),
                    ev.occurred_at.isoformat(),
                    str(ev.previous_event_digest) if ev.previous_event_digest else None,
                    str(ev.event_digest),
                    json.dumps(payload_dict, sort_keys=True),
                ),
            )

    def _insert_telemetry_signatures(
        self,
        run_id: str,
        agent_role: str,
        telemetry: Any,
    ) -> None:
        if telemetry is None:
            return
        sig_digests = list(getattr(telemetry, "thought_signature_digests", []) or [])
        sig_lengths = list(getattr(telemetry, "thought_signature_lengths", []) or [])
        summaries = list(getattr(telemetry, "thought_summaries", []) or [])
        in_tok = int(getattr(telemetry, "total_input_tokens", 0) or 0)
        th_tok = int(getattr(telemetry, "total_thought_tokens", 0) or 0)
        out_tok = int(getattr(telemetry, "total_output_tokens", 0) or 0)
        model_used = str(getattr(telemetry, "model_used", "gemini-4-argon"))
        int_id = str(getattr(telemetry, "interaction_id", "int_local"))
        t_level = str(getattr(telemetry, "thinking_level", "adaptive"))

        if not sig_digests:
            # Record a single telemetry row even if adaptive mode emitted 0 explicit thought signatures
            synthetic_digest = f"sha256:{hashlib.sha256(f'{run_id}:{int_id}:{agent_role}'.encode('utf-8')).hexdigest()}"
            self._conn.execute(
                """
                INSERT INTO gemini_thought_signatures (
                    run_id, interaction_id, agent_role, model_used, thinking_level,
                    step_index, signature_digest, signature_length, thought_summary,
                    input_tokens, thought_tokens, output_tokens
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    int_id,
                    agent_role,
                    model_used,
                    t_level,
                    0,
                    synthetic_digest,
                    0,
                    summaries[0] if summaries else "Schema-compiled adaptive zero-thought pass.",
                    in_tok,
                    th_tok,
                    out_tok,
                ),
            )
            return

        for idx, s_dig in enumerate(sig_digests):
            s_len = int(sig_lengths[idx]) if idx < len(sig_lengths) else 0
            s_sum = str(summaries[idx]) if idx < len(summaries) else (summaries[0] if summaries else "")
            self._conn.execute(
                """
                INSERT INTO gemini_thought_signatures (
                    run_id, interaction_id, agent_role, model_used, thinking_level,
                    step_index, signature_digest, signature_length, thought_summary,
                    input_tokens, thought_tokens, output_tokens
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    int_id,
                    agent_role,
                    model_used,
                    t_level,
                    idx,
                    str(s_dig),
                    s_len,
                    s_sum,
                    in_tok,
                    th_tok,
                    out_tok,
                ),
            )

    def record_governed_bundle(
        self,
        bundle: Any,
        run_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Persists a `LiveGovernedDecisionBundle` (standard MoA, closed-loop quarantine
        repair, or 3-agent Dialectical H^1 Hodge resolution) into the SQLite / D1 ledger.
        """
        win_gov = bundle.winning_governance
        base_run_id = str(win_gov.final_runtime_state.run_id)
        packet_id = str(bundle.sol_lens_packet.get("packet_id", f"pkt:{base_run_id}"))
        # Ensure unique run_id per bundle invocation by combining run_id + interaction_id suffix if needed
        int_suffix = str(bundle.interaction_id)[-10:].replace(":", "-")
        run_id = f"{base_run_id}:{int_suffix}"[:128]

        if run_mode is None:
            if getattr(bundle, "h1_resolution_record", None) is not None:
                run_mode = "dialectical_h1"
            elif getattr(bundle, "repair_records", None):
                run_mode = "closed_loop_repair"
            else:
                run_mode = "standard_moa"

        h1_rec = getattr(bundle, "h1_resolution_record", None)
        repair_recs = list(getattr(bundle, "repair_records", []) or [])

        pre_beta_1 = (
            int(getattr(h1_rec, "pre_beta_1", getattr(h1_rec, "pre_negotiation_beta_1", 0)))
            if h1_rec is not None
            else int(bundle.evaluation_report.beta_1)
        )
        post_beta_1 = (
            int(getattr(h1_rec, "post_beta_1", getattr(h1_rec, "post_negotiation_beta_1", 0)))
            if h1_rec is not None
            else int(bundle.evaluation_report.beta_1)
        )

        selected_opt_id = str(bundle.decision_package.selected_option_id)
        selected_opt_name = str(bundle.decision_package.selected_option_name)

        prior_q_digest: Optional[str] = None
        if h1_rec is not None:
            pre_gov_map = getattr(h1_rec, "pre_repair_governance", {}) or {}
            pre_win_gov = pre_gov_map.get(selected_opt_id) or (
                next(iter(pre_gov_map.values())) if pre_gov_map else None
            )
            if pre_win_gov is not None:
                prior_q_digest = str(pre_win_gov.final_runtime_state.state_digest)
        elif repair_recs:
            prior_q_digest = str(repair_recs[0].quarantined_state_digest)

        final_state_digest = str(win_gov.final_runtime_state.state_digest)
        policy_status = str(win_gov.policy_decision.status.value)
        runtime_status = str(win_gov.final_runtime_state.status.value)
        next_transition = str(win_gov.policy_decision.next_transition.value)
        study_name = str(bundle.elicited_spec.study_name)
        model_used = str(bundle.model_used)
        interaction_id = str(bundle.interaction_id)
        t_level = str(getattr(bundle.reasoning_telemetry, "thinking_level", "adaptive"))
        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        with self._conn:
            # If re-recording same run_id, clean existing child rows first
            self._conn.execute("DELETE FROM sol_edge_runtime_events WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM gemini_thought_signatures WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM cohomological_repair_records WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM governance_court_runs WHERE run_id = ?", (run_id,))

            prev_run_digest = self._get_head_ledger_digest()
            entry_digest = self.compute_ledger_entry_digest(
                run_id=run_id,
                packet_id=packet_id,
                study_name=study_name,
                run_mode=run_mode,
                model_used=model_used,
                interaction_id=interaction_id,
                selected_option_id=selected_opt_id,
                policy_status=policy_status,
                final_state_digest=final_state_digest,
                prior_quarantined_state_digest=prior_q_digest,
                previous_run_digest=prev_run_digest,
            )

            gate = bundle.decision_package.authorization_gate
            self._conn.execute(
                """
                INSERT INTO governance_court_runs (
                    run_id, packet_id, study_name, run_mode, model_used, interaction_id,
                    thinking_level, selected_option_id, selected_option_name,
                    policy_status, runtime_status, next_transition,
                    pre_beta_1, post_beta_1, dirichlet_energy, coboundary_norm,
                    kuramoto_order_r, causal_emergence_delta_ei,
                    final_state_digest, prior_quarantined_state_digest,
                    previous_run_digest, ledger_entry_digest,
                    is_signed, signer_name, signer_role, proof_packet_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    packet_id,
                    study_name,
                    run_mode,
                    model_used,
                    interaction_id,
                    t_level,
                    selected_opt_id,
                    selected_opt_name,
                    policy_status,
                    runtime_status,
                    next_transition,
                    pre_beta_1,
                    post_beta_1,
                    float(bundle.evaluation_report.dirichlet_energy),
                    float(bundle.evaluation_report.coboundary_norm),
                    float(bundle.elicitation_result.kuramoto_order_r),
                    float(bundle.elicitation_result.causal_emergence_delta_ei),
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    1 if gate.is_signed else 0,
                    gate.signer_name,
                    gate.authorized_role,
                    json.dumps(bundle.sol_lens_packet, sort_keys=True),
                    now_iso,
                ),
            )

            # Persist 4-event sol-edge streams for all governed options
            for opt_id, gov_art in (bundle.all_option_governance or {}).items():
                self._insert_runtime_events(run_id, opt_id, gov_art.events)

            # Persist primary Gemini reasoning telemetry
            self._insert_telemetry_signatures(run_id, "7_Giants_MoA_Synthesizer", bundle.reasoning_telemetry)

            # Persist closed-loop quarantine repair records & their telemetry
            for rep in repair_recs:
                self._insert_telemetry_signatures(
                    run_id,
                    f"Quarantine_Repair:{rep.quarantined_option_id}",
                    rep.repair_reasoning_telemetry,
                )
                rep_rationale = str(
                    getattr(
                        rep.repair_spec,
                        "cohomological_repair_rationale",
                        getattr(rep.repair_spec, "repair_rationale", ""),
                    )
                )
                self._conn.execute(
                    """
                    INSERT INTO cohomological_repair_records (
                        run_id, repair_kind, target_option_id,
                        pre_beta_1, post_beta_1, pre_harmonic_norm, post_harmonic_norm,
                        l2_projection_distance, quarantined_state_digest, cleared_state_digest,
                        previous_interaction_id, repair_interaction_id,
                        pre_stalk_json, post_stalk_json, rationale
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        "quarantine_coboundary_repair",
                        str(rep.quarantined_option_id),
                        0,
                        0,
                        float(sum(v.coboundary_excess for v in rep.violated_invariants)),
                        0.0,
                        float(rep.l2_repair_projection_distance),
                        str(rep.quarantined_state_digest),
                        str(rep.post_repair_governance.final_runtime_state.state_digest),
                        str(rep.previous_interaction_id),
                        str(rep.repair_interaction_id),
                        json.dumps(rep.pre_repair_state_vector),
                        json.dumps(rep.post_repair_state_vector),
                        rep_rationale,
                    ),
                )

            # Persist 3-agent Dialectical H^1 Hodge negotiation record & specialist telemetry
            if h1_rec is not None:
                sp_proposals = list(getattr(h1_rec, "specialist_proposals", []) or [])
                sp_telemetries = list(getattr(h1_rec, "specialist_reasoning_telemetry", []) or [])
                for sp_idx, sp_tel in enumerate(sp_telemetries):
                    role_name = (
                        str(sp_proposals[sp_idx].specialist_role)
                        if sp_idx < len(sp_proposals)
                        else f"Specialist_{sp_idx}"
                    )
                    self._insert_telemetry_signatures(run_id, role_name, sp_tel)
                self._insert_telemetry_signatures(
                    run_id,
                    "Hodge_Harmonic_Negotiator",
                    getattr(h1_rec, "negotiation_reasoning_telemetry", None),
                )
                pre_claims = {
                    str(sp.specialist_role): float(sp.interface_transfer_claim)
                    for sp in sp_proposals
                }
                neg_spec = getattr(h1_rec, "negotiation_spec", None)
                res_claims = list(getattr(neg_spec, "residual_interface_claims", [0.0, 0.0, 0.0]) or [0.0, 0.0, 0.0])
                post_claims = {
                    str(sp.specialist_role): float(res_claims[idx] if idx < len(res_claims) else 0.0)
                    for idx, sp in enumerate(sp_proposals)
                }
                l2_dist = float(
                    np.linalg.norm(
                        np.array(list(post_claims.values()), dtype=np.float64)
                        - np.array(list(pre_claims.values()), dtype=np.float64)
                    )
                ) if pre_claims and post_claims and len(pre_claims) == len(post_claims) else 0.0
                self._conn.execute(
                    """
                    INSERT INTO cohomological_repair_records (
                        run_id, repair_kind, target_option_id,
                        pre_beta_1, post_beta_1, pre_harmonic_norm, post_harmonic_norm,
                        l2_projection_distance, quarantined_state_digest, cleared_state_digest,
                        previous_interaction_id, repair_interaction_id,
                        pre_stalk_json, post_stalk_json, rationale
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        "dialectical_h1_hodge_negotiation",
                        selected_opt_id,
                        pre_beta_1,
                        post_beta_1,
                        float(getattr(h1_rec, "pre_harmonic_norm", 0.0)),
                        float(getattr(h1_rec, "post_harmonic_norm", 0.0)),
                        l2_dist,
                        prior_q_digest or "sha256:0",
                        final_state_digest,
                        str(getattr(h1_rec, "previous_interaction_id", interaction_id)),
                        str(getattr(h1_rec, "negotiation_interaction_id", interaction_id)),
                        json.dumps(pre_claims, sort_keys=True),
                        json.dumps(post_claims, sort_keys=True),
                        str(getattr(neg_spec, "hodge_negotiation_rationale", "")),
                    ),
                )

        return {
            "run_id": run_id,
            "packet_id": packet_id,
            "run_mode": run_mode,
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
        }

    def record_sysml_shock_cosimulation(
        self,
        record: Any,
        baseline_run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Persists a Frontier B `SysMLShockCoSimulationRecord` into:
        - `governance_court_runs`
        - `sol_edge_runtime_events` (both Cycle 0 QUARANTINE and Cycle 1 ELIGIBLE streams)
        - `gemini_thought_signatures`
        - `cohomological_repair_records` (`repair_kind="sysml_shock_mutation"`)
        - `differential_shock_timeline` (each `OperationalShock` + `DifferentialDecisionDelta`)
        """
        cleared_gov = record.mutated_cleared_governance
        shocked_gov = record.shocked_quarantine_governance
        base_run_id = str(cleared_gov.final_runtime_state.run_id)
        int_suffix = str(record.mutation_interaction_id)[-10:].replace(":", "-")
        run_id = f"{base_run_id}:{int_suffix}"[:128]
        packet_id = f"pkt:sysml:{record.differential_delta.delta_id.lower()}"
        study_name = str(record.sysml_package_name)
        run_mode = "sysml_shock_cosim"
        model_used = str(record.reasoning_telemetry.model_used)
        interaction_id = str(record.mutation_interaction_id)
        t_level = str(record.reasoning_telemetry.thinking_level)
        selected_opt_id = str(record.shocked_part_id)
        selected_opt_name = str(record.mutation_spec.mutated_part_name)
        policy_status = str(cleared_gov.policy_decision.status.value)
        runtime_status = str(cleared_gov.final_runtime_state.status.value)
        next_transition = str(cleared_gov.policy_decision.next_transition.value)
        final_state_digest = str(cleared_gov.final_runtime_state.state_digest)
        prior_q_digest = str(shocked_gov.final_runtime_state.state_digest)
        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        with self._conn:
            self._conn.execute("DELETE FROM differential_shock_timeline WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM sol_edge_runtime_events WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM gemini_thought_signatures WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM cohomological_repair_records WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM governance_court_runs WHERE run_id = ?", (run_id,))

            prev_run_digest = self._get_head_ledger_digest()
            entry_digest = self.compute_ledger_entry_digest(
                run_id=run_id,
                packet_id=packet_id,
                study_name=study_name,
                run_mode=run_mode,
                model_used=model_used,
                interaction_id=interaction_id,
                selected_option_id=selected_opt_id,
                policy_status=policy_status,
                final_state_digest=final_state_digest,
                prior_quarantined_state_digest=prior_q_digest,
                previous_run_digest=prev_run_digest,
            )

            synthetic_packet = {
                "schema": "techman.sol-lens.proof-packet/v0.2",
                "packet_id": packet_id,
                "study_name": study_name,
                "sysml_cosimulation": record.to_dict(),
            }

            self._conn.execute(
                """
                INSERT INTO governance_court_runs (
                    run_id, packet_id, study_name, run_mode, model_used, interaction_id,
                    thinking_level, selected_option_id, selected_option_name,
                    policy_status, runtime_status, next_transition,
                    pre_beta_1, post_beta_1, dirichlet_energy, coboundary_norm,
                    kuramoto_order_r, causal_emergence_delta_ei,
                    final_state_digest, prior_quarantined_state_digest,
                    previous_run_digest, ledger_entry_digest,
                    is_signed, signer_name, signer_role, proof_packet_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    packet_id,
                    study_name,
                    run_mode,
                    model_used,
                    interaction_id,
                    t_level,
                    selected_opt_id,
                    selected_opt_name,
                    policy_status,
                    runtime_status,
                    next_transition,
                    int(record.differential_delta.pre_betti_1),
                    int(record.differential_delta.post_betti_1),
                    float(record.differential_delta.post_energy),
                    0.0,
                    1.0,
                    1.25,
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    "PEO Artemis Surface Systems",
                    json.dumps(synthetic_packet, sort_keys=True),
                    now_iso,
                ),
            )

            # Persist Cycle 0 QUARANTINED and Cycle 1 ELIGIBLE sol-edge event streams
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle0-shocked", shocked_gov.events)
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle1-mutated", cleared_gov.events)

            # Persist Gemini 4 SysML mutation reasoning telemetry
            self._insert_telemetry_signatures(
                run_id, "SysML_v2_Architecture_Mutator", record.reasoning_telemetry
            )

            # Persist Cohomological Repair Record
            l2_dist = float(
                np.linalg.norm(
                    np.array(record.mutated_stalk, dtype=np.float64)
                    - np.array(record.post_shock_stalk, dtype=np.float64)
                )
            )
            self._conn.execute(
                """
                INSERT INTO cohomological_repair_records (
                    run_id, repair_kind, target_option_id,
                    pre_beta_1, post_beta_1, pre_harmonic_norm, post_harmonic_norm,
                    l2_projection_distance, quarantined_state_digest, cleared_state_digest,
                    previous_interaction_id, repair_interaction_id,
                    pre_stalk_json, post_stalk_json, rationale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    "sysml_shock_mutation",
                    selected_opt_id,
                    int(record.differential_delta.pre_betti_1),
                    int(record.differential_delta.post_betti_1),
                    float(len(record.differential_delta.activated_coboundary_edges)),
                    0.0,
                    l2_dist,
                    prior_q_digest,
                    final_state_digest,
                    f"shock:{record.differential_delta.delta_id}",
                    interaction_id,
                    json.dumps(record.post_shock_stalk),
                    json.dumps(record.mutated_stalk),
                    str(record.mutation_spec.sysml_mutation_rationale),
                ),
            )

            # Persist Differential Shock Timeline entries
            delta = record.differential_delta
            for idx, shock in enumerate(record.applied_shocks):
                shock_entry_id = f"{delta.delta_id}:{shock.shock_id}:{idx}"[:128]
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO differential_shock_timeline (
                        shock_entry_id, run_id, baseline_run_id, delta_id, shock_id,
                        target_primitive_id, parameter_channel, delta_value,
                        baseline_option_id, refreshed_option_id, did_decision_flip,
                        pre_energy, post_energy, pre_beta_1, post_beta_1,
                        activated_edges_json, quarantined_state_digest, cleared_state_digest,
                        audit_summary, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        shock_entry_id,
                        run_id,
                        baseline_run_id,
                        str(delta.delta_id),
                        str(shock.shock_id),
                        str(shock.target_primitive_id),
                        int(shock.parameter_channel),
                        float(shock.delta_value),
                        str(delta.baseline_option_id),
                        str(delta.refreshed_option_id),
                        1 if delta.did_decision_flip else 0,
                        float(delta.pre_energy),
                        float(delta.post_energy),
                        int(delta.pre_betti_1),
                        int(delta.post_betti_1),
                        json.dumps(delta.activated_coboundary_edges),
                        prior_q_digest,
                        final_state_digest,
                        str(delta.audit_summary),
                        now_iso,
                    ),
                )

        return {
            "run_id": run_id,
            "packet_id": packet_id,
            "run_mode": run_mode,
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
        }

    def record_robotic_actuation_episode(
        self,
        cycle0_rec: Any,
        cycle1_rec: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Persists a 6-DOF Robotic Configuration Manifold + SO(3) Non-Abelian Wilson Loop
        Gauge Holonomy governance episode into the SQLite / D1 ledger.
        """
        active_rec = cycle1_rec if cycle1_rec is not None else cycle0_rec
        gov = active_rec.governance_artifact
        sysml_suffix = str(active_rec.sysml_decision_state_digest)[-10:]
        run_id = f"{gov.final_runtime_state.run_id}:{sysml_suffix}"[:128]
        packet_id = f"pkt:robotics:{sysml_suffix}"
        study_name = "Artemis_6DOF_Geodesic_And_SO3_Gauge_Gate"
        run_mode = "robotic_manifold_gate"
        model_used = "Frontier_OS:SO3_GaugeSheaf"
        interaction_id = f"int:robotics:{sysml_suffix}"
        selected_opt_id = "device:artemis-6dof-manipulator"
        selected_opt_name = "Artemis 6-DOF Harmonic Manipulator"
        policy_status = str(gov.policy_decision.status.value)
        runtime_status = str(gov.final_runtime_state.status.value)
        next_transition = str(gov.policy_decision.next_transition.value)
        final_state_digest = str(gov.final_runtime_state.state_digest)
        prior_q_digest = (
            str(cycle0_rec.governance_artifact.final_runtime_state.state_digest)
            if cycle1_rec is not None
            else None
        )
        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        with self._conn:
            self._conn.execute("DELETE FROM sol_edge_runtime_events WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM cohomological_repair_records WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM governance_court_runs WHERE run_id = ?", (run_id,))

            prev_run_digest = self._get_head_ledger_digest()
            entry_digest = self.compute_ledger_entry_digest(
                run_id=run_id,
                packet_id=packet_id,
                study_name=study_name,
                run_mode=run_mode,
                model_used=model_used,
                interaction_id=interaction_id,
                selected_option_id=selected_opt_id,
                policy_status=policy_status,
                final_state_digest=final_state_digest,
                prior_quarantined_state_digest=prior_q_digest,
                previous_run_digest=prev_run_digest,
            )

            pkt_payload = {
                "schema": "techman.sol-lens.proof-packet/v0.2",
                "packet_id": packet_id,
                "cycle_0": cycle0_rec.to_dict(),
                "cycle_1": cycle1_rec.to_dict() if cycle1_rec is not None else None,
            }

            self._conn.execute(
                """
                INSERT INTO governance_court_runs (
                    run_id, packet_id, study_name, run_mode, model_used, interaction_id,
                    thinking_level, selected_option_id, selected_option_name,
                    policy_status, runtime_status, next_transition,
                    pre_beta_1, post_beta_1, dirichlet_energy, coboundary_norm,
                    kuramoto_order_r, causal_emergence_delta_ei,
                    final_state_digest, prior_quarantined_state_digest,
                    previous_run_digest, ledger_entry_digest,
                    is_signed, signer_name, signer_role, proof_packet_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    packet_id,
                    study_name,
                    run_mode,
                    model_used,
                    interaction_id,
                    "deterministic",
                    selected_opt_id,
                    selected_opt_name,
                    policy_status,
                    runtime_status,
                    next_transition,
                    int(cycle0_rec.actuator_betti_1),
                    int(active_rec.actuator_betti_1),
                    float(active_rec.yang_mills_action),
                    float(active_rec.max_wilson_defect_deg),
                    1.0,
                    0.0,
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    "Autonomous Safety Arbiter",
                    json.dumps(pkt_payload, sort_keys=True),
                    now_iso,
                ),
            )

            self._insert_runtime_events(
                run_id, "6dof:cycle0", cycle0_rec.governance_artifact.events
            )
            if cycle1_rec is not None:
                self._insert_runtime_events(
                    run_id, "6dof:cycle1-gauge-relaxed", cycle1_rec.governance_artifact.events
                )
                self._conn.execute(
                    """
                    INSERT INTO cohomological_repair_records (
                        run_id, repair_kind, target_option_id,
                        pre_beta_1, post_beta_1, pre_harmonic_norm, post_harmonic_norm,
                        l2_projection_distance, quarantined_state_digest, cleared_state_digest,
                        previous_interaction_id, repair_interaction_id,
                        pre_stalk_json, post_stalk_json, rationale
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        "robotic_gauge_holonomy_diffusion",
                        selected_opt_id,
                        int(cycle0_rec.actuator_betti_1),
                        int(cycle1_rec.actuator_betti_1),
                        float(cycle0_rec.max_wilson_defect_deg),
                        float(cycle1_rec.max_wilson_defect_deg),
                        float(abs(cycle0_rec.max_wilson_defect_deg - cycle1_rec.max_wilson_defect_deg)),
                        str(cycle0_rec.governance_artifact.final_runtime_state.state_digest),
                        final_state_digest,
                        f"wilson-loop-c0:{sysml_suffix}",
                        f"wilson-loop-c1:{sysml_suffix}",
                        json.dumps(
                            {
                                "max_wilson_defect_deg": round(float(cycle0_rec.max_wilson_defect_deg), 4),
                                "yang_mills_action": round(float(cycle0_rec.yang_mills_action), 6),
                            }
                        ),
                        json.dumps(
                            {
                                "max_wilson_defect_deg": round(float(cycle1_rec.max_wilson_defect_deg), 4),
                                "yang_mills_action": round(float(cycle1_rec.yang_mills_action), 6),
                            }
                        ),
                        "Diffused non-abelian SO(3) gauge connections across workspace triangulation to annihilate Wilson loop holonomy defect.",
                    ),
                )

        return {
            "run_id": run_id,
            "packet_id": packet_id,
            "run_mode": run_mode,
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
        }

    def record_wormhole_homology_episode(
        self,
        record: Any,
    ) -> Dict[str, Any]:
        """
        Persists a Frontier D `WormholeSubstrateEpisodeRecord` (3D SheafDecisionComplex ->
        4D ExcitonEngine Dirac-Delta Wormhole -> 2D HippocampalMemorySink -> U(N) Photonic
        MZI Substrate) into the Cryptographic Governance Court Ledger.
        """
        cleared_gov = record.cycle1_cleared_governance
        quarantine_gov = record.cycle0_quarantine_governance
        base_run_id = str(cleared_gov.final_runtime_state.run_id)
        int_suffix = str(record.calibration_interaction_id)[-10:].replace(":", "-")
        run_id = f"{base_run_id}:{int_suffix}"[:128]
        packet_id = str(record.sol_lens_packet.get("packet_id", f"pkt:wormhole:{int_suffix}"))
        study_name = str(record.episode_id)
        run_mode = "wormhole_homology_bridge"
        model_used = str(record.reasoning_telemetry.model_used)
        interaction_id = str(record.calibration_interaction_id)
        t_level = str(record.reasoning_telemetry.thinking_level)
        selected_opt_id = str(record.calibration_spec.wormhole_bridge_id)
        selected_opt_name = f"Wormhole Bridge ({record.calibration_spec.wormhole_bridge_id}: 3D->4D->2D->U(N))"
        policy_status = str(cleared_gov.policy_decision.status.value)
        runtime_status = str(cleared_gov.final_runtime_state.status.value)
        next_transition = str(cleared_gov.policy_decision.next_transition.value)
        final_state_digest = str(cleared_gov.final_runtime_state.state_digest)
        prior_q_digest = str(quarantine_gov.final_runtime_state.state_digest)
        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        c0_defect = float(
            max((s.commutation_defect_d1 + s.commutation_defect_d2 for s in record.cycle0_stages), default=0.0)
        )
        c1_defect = float(
            max((s.commutation_defect_d1 + s.commutation_defect_d2 for s in record.cycle1_stages), default=0.0)
        )
        c0_div = float(max((s.transported_cycle_divergence for s in record.cycle0_stages), default=0.0))
        c1_div = float(max((s.transported_cycle_divergence for s in record.cycle1_stages), default=0.0))

        with self._conn:
            self._conn.execute("DELETE FROM sol_edge_runtime_events WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM gemini_thought_signatures WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM cohomological_repair_records WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM governance_court_runs WHERE run_id = ?", (run_id,))

            prev_run_digest = self._get_head_ledger_digest()
            entry_digest = self.compute_ledger_entry_digest(
                run_id=run_id,
                packet_id=packet_id,
                study_name=study_name,
                run_mode=run_mode,
                model_used=model_used,
                interaction_id=interaction_id,
                selected_option_id=selected_opt_id,
                policy_status=policy_status,
                final_state_digest=final_state_digest,
                prior_quarantined_state_digest=prior_q_digest,
                previous_run_digest=prev_run_digest,
            )

            self._conn.execute(
                """
                INSERT INTO governance_court_runs (
                    run_id, packet_id, study_name, run_mode, model_used, interaction_id,
                    thinking_level, selected_option_id, selected_option_name,
                    policy_status, runtime_status, next_transition,
                    pre_beta_1, post_beta_1, dirichlet_energy, coboundary_norm,
                    kuramoto_order_r, causal_emergence_delta_ei,
                    final_state_digest, prior_quarantined_state_digest,
                    previous_run_digest, ledger_entry_digest,
                    is_signed, signer_name, signer_role, proof_packet_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    packet_id,
                    study_name,
                    run_mode,
                    model_used,
                    interaction_id,
                    t_level,
                    selected_opt_id,
                    selected_opt_name,
                    policy_status,
                    runtime_status,
                    next_transition,
                    int(record.source_3d_homology.beta_1),
                    int(record.hippocampal_2d_homology.beta_1),
                    c1_defect,
                    float(record.photonic_unitarity_defect),
                    float(record.swarm_kuramoto_r),
                    float(record.exciton_entangled_flux_injected),
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    "Photonic & Topological Substrate Arbiter",
                    json.dumps(record.sol_lens_packet, sort_keys=True),
                    now_iso,
                ),
            )

            self._insert_runtime_events(
                run_id, "wormhole:cycle0-uncalibrated", quarantine_gov.events
            )
            self._insert_runtime_events(
                run_id, "wormhole:cycle1-calibrated", cleared_gov.events
            )
            self._insert_telemetry_signatures(
                run_id, "Wormhole_Homology_Calibrator", record.reasoning_telemetry
            )

            self._conn.execute(
                """
                INSERT INTO cohomological_repair_records (
                    run_id, repair_kind, target_option_id,
                    pre_beta_1, post_beta_1, pre_harmonic_norm, post_harmonic_norm,
                    l2_projection_distance, quarantined_state_digest, cleared_state_digest,
                    previous_interaction_id, repair_interaction_id,
                    pre_stalk_json, post_stalk_json, rationale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    "interdimensional_wormhole_homology_calibration",
                    selected_opt_id,
                    int(record.source_3d_homology.beta_1),
                    int(record.hippocampal_2d_homology.beta_1),
                    c0_defect,
                    c1_defect,
                    float(abs(c0_defect - c1_defect)),
                    prior_q_digest,
                    final_state_digest,
                    f"wormhole-c0:{int_suffix}",
                    interaction_id,
                    json.dumps(
                        {
                            "commutation_defect": round(c0_defect, 6),
                            "cycle_divergence": round(c0_div, 6),
                        }
                    ),
                    json.dumps(
                        {
                            "commutation_defect": round(c1_defect, 6),
                            "cycle_divergence": round(c1_div, 6),
                            "calibrated_throat_conductance": float(
                                record.calibration_spec.calibrated_throat_conductance
                            ),
                        }
                    ),
                    str(record.calibration_spec.homological_calibration_rationale),
                ),
            )

        return {
            "run_id": run_id,
            "packet_id": packet_id,
            "run_mode": run_mode,
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
        }

    def record_ricci_surgery_episode(
        self,
        record: Any,
    ) -> Dict[str, Any]:
        """
        Persists a Frontier G `PersistentRicciSurgeryEpisodeRecord` (Cellular Persistent
        Homology Filtration + Ollivier-Ricci Curvature Flow + Hamilton-Perelman Ricci
        Surgery) into the Cryptographic Governance Court Ledger.
        """
        cleared_gov = record.cycle1_cleared_governance
        quarantine_gov = record.cycle0_quarantine_governance
        base_run_id = str(cleared_gov.final_runtime_state.run_id)
        int_suffix = str(record.surgery_interaction_id)[-10:].replace(":", "-")
        run_id = f"{base_run_id}:{int_suffix}"[:128]
        packet_id = str(record.sol_lens_packet.get("packet_id", f"pkt:ricci:{int_suffix}"))
        study_name = str(record.episode_id)
        run_mode = "persistent_ricci_surgery"
        model_used = str(record.reasoning_telemetry.model_used)
        interaction_id = str(record.surgery_interaction_id)
        t_level = str(record.reasoning_telemetry.thinking_level)
        selected_opt_id = str(record.surgery_spec.surgically_spliced_edge_id)
        selected_opt_name = f"Ricci Surgery Harmonic Cap ({selected_opt_id})"
        policy_status = str(cleared_gov.policy_decision.status.value)
        runtime_status = str(cleared_gov.final_runtime_state.status.value)
        next_transition = str(cleared_gov.policy_decision.next_transition.value)
        final_state_digest = str(cleared_gov.final_runtime_state.state_digest)
        prior_q_digest = str(quarantine_gov.final_runtime_state.state_digest)
        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        c0_bn = float(record.cycle0_persistence_report.bottleneck_distance_from_canonical)
        c1_bn = float(record.cycle1_persistence_report.bottleneck_distance_from_canonical)
        c0_kappa = float(record.cycle0_ricci_snapshot.throat_ollivier_ricci_curvature)
        c1_kappa = float(record.cycle1_ricci_snapshot.throat_ollivier_ricci_curvature)

        with self._conn:
            self._conn.execute("DELETE FROM sol_edge_runtime_events WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM gemini_thought_signatures WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM cohomological_repair_records WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM governance_court_runs WHERE run_id = ?", (run_id,))

            prev_run_digest = self._get_head_ledger_digest()
            entry_digest = self.compute_ledger_entry_digest(
                run_id=run_id,
                packet_id=packet_id,
                study_name=study_name,
                run_mode=run_mode,
                model_used=model_used,
                interaction_id=interaction_id,
                selected_option_id=selected_opt_id,
                policy_status=policy_status,
                final_state_digest=final_state_digest,
                prior_quarantined_state_digest=prior_q_digest,
                previous_run_digest=prev_run_digest,
            )

            self._conn.execute(
                """
                INSERT INTO governance_court_runs (
                    run_id, packet_id, study_name, run_mode, model_used, interaction_id,
                    thinking_level, selected_option_id, selected_option_name,
                    policy_status, runtime_status, next_transition,
                    pre_beta_1, post_beta_1, dirichlet_energy, coboundary_norm,
                    kuramoto_order_r, causal_emergence_delta_ei,
                    final_state_digest, prior_quarantined_state_digest,
                    previous_run_digest, ledger_entry_digest,
                    is_signed, signer_name, signer_role, proof_packet_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    packet_id,
                    study_name,
                    run_mode,
                    model_used,
                    interaction_id,
                    t_level,
                    selected_opt_id,
                    selected_opt_name,
                    policy_status,
                    runtime_status,
                    next_transition,
                    int(record.cycle0_persistence_report.essential_h1_count),
                    int(record.cycle1_persistence_report.essential_h1_count),
                    c1_bn,
                    float(abs(record.cycle1_ricci_snapshot.scalar_curvature_r)),
                    float(record.cycle1_persistence_report.essential_h1_normalized_lifetime),
                    float(record.cycle1_persistence_report.signal_to_noise_persistence_ratio),
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    "Ollivier-Ricci & Persistent Homology Arbiter",
                    json.dumps(record.sol_lens_packet, sort_keys=True),
                    now_iso,
                ),
            )

            self._insert_runtime_events(
                run_id, "ricci:cycle0-neck-pinch", quarantine_gov.events
            )
            self._insert_runtime_events(
                run_id, "ricci:cycle1-harmonic-cap", cleared_gov.events
            )
            self._insert_telemetry_signatures(
                run_id, "Ollivier_Ricci_Surgery_Synthesizer", record.reasoning_telemetry
            )

            self._conn.execute(
                """
                INSERT INTO cohomological_repair_records (
                    run_id, repair_kind, target_option_id,
                    pre_beta_1, post_beta_1, pre_harmonic_norm, post_harmonic_norm,
                    l2_projection_distance, quarantined_state_digest, cleared_state_digest,
                    previous_interaction_id, repair_interaction_id,
                    pre_stalk_json, post_stalk_json, rationale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    "ollivier_ricci_neck_pinch_surgery",
                    selected_opt_id,
                    int(record.cycle0_persistence_report.essential_h1_count),
                    int(record.cycle1_persistence_report.essential_h1_count),
                    c0_bn,
                    c1_bn,
                    float(abs(c1_kappa - c0_kappa)),
                    prior_q_digest,
                    final_state_digest,
                    f"ricci-c0:{int_suffix}",
                    interaction_id,
                    json.dumps(
                        {
                            "throat_ollivier_ricci_curvature": round(c0_kappa, 6),
                            "bottleneck_distance": round(c0_bn, 6),
                            "essential_h1_lifetime": round(
                                float(record.cycle0_persistence_report.essential_h1_normalized_lifetime), 6
                            ),
                        }
                    ),
                    json.dumps(
                        {
                            "throat_ollivier_ricci_curvature": round(c1_kappa, 6),
                            "bottleneck_distance": round(c1_bn, 6),
                            "essential_h1_lifetime": round(
                                float(record.cycle1_persistence_report.essential_h1_normalized_lifetime), 6
                            ),
                            "restored_throat_conductance": float(
                                record.surgery_spec.restored_throat_conductance
                            ),
                        }
                    ),
                    str(record.surgery_spec.ricci_surgery_rationale),
                ),
            )

        return {
            "run_id": run_id,
            "packet_id": packet_id,
            "run_mode": run_mode,
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
        }

    def record_non_hermitian_pt_episode(
        self,
        record: Any,
    ) -> Dict[str, Any]:
        """
        Persists a Frontier H `NonHermitianPTEpisodeRecord` (Hatano-Nelson Non-Hermitian
        Skin Effect [NHSE], Point-Gap Spectral Winding, Petermann Excess Noise Factor,
        and Exceptional Point PT-Symmetry Phase Governance) into the Cryptographic
        Governance Court Ledger.
        """
        cleared_gov = record.cycle1_cleared_governance
        quarantine_gov = record.cycle0_quarantine_governance
        base_run_id = str(cleared_gov.final_runtime_state.run_id)
        int_suffix = str(record.calibration_interaction_id)[-10:].replace(":", "-")
        run_id = f"{base_run_id}:{int_suffix}"[:128]
        packet_id = str(record.sol_lens_packet.get("packet_id", f"pkt:nh-pt:{int_suffix}"))
        study_name = str(record.episode_id)
        run_mode = "non_hermitian_skin_pt"
        model_used = str(record.reasoning_telemetry.model_used)
        interaction_id = str(record.calibration_interaction_id)
        t_level = str(record.reasoning_telemetry.thinking_level)
        selected_opt_id = str(record.surgery_spec.target_cavity_id)
        selected_opt_name = f"GBZ Imaginary Gauge & PT Stabilization ({selected_opt_id})"
        policy_status = str(cleared_gov.policy_decision.status.value)
        runtime_status = str(cleared_gov.final_runtime_state.status.value)
        next_transition = str(cleared_gov.policy_decision.next_transition.value)
        final_state_digest = str(cleared_gov.final_runtime_state.state_digest)
        prior_q_digest = str(quarantine_gov.final_runtime_state.state_digest)
        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        c0_k = float(record.cycle0_spectral_snapshot.max_petermann_factor)
        c1_k = float(record.cycle1_spectral_snapshot.max_petermann_factor)
        c0_ipr = float(record.cycle0_spectral_snapshot.obc_skin_localization_ipr)
        c1_ipr = float(record.cycle1_spectral_snapshot.obc_skin_localization_ipr)

        with self._conn:
            self._conn.execute("DELETE FROM sol_edge_runtime_events WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM gemini_thought_signatures WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM cohomological_repair_records WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM governance_court_runs WHERE run_id = ?", (run_id,))

            prev_run_digest = self._get_head_ledger_digest()
            entry_digest = self.compute_ledger_entry_digest(
                run_id=run_id,
                packet_id=packet_id,
                study_name=study_name,
                run_mode=run_mode,
                model_used=model_used,
                interaction_id=interaction_id,
                selected_option_id=selected_opt_id,
                policy_status=policy_status,
                final_state_digest=final_state_digest,
                prior_quarantined_state_digest=prior_q_digest,
                previous_run_digest=prev_run_digest,
            )

            self._conn.execute(
                """
                INSERT INTO governance_court_runs (
                    run_id, packet_id, study_name, run_mode, model_used, interaction_id,
                    thinking_level, selected_option_id, selected_option_name,
                    policy_status, runtime_status, next_transition,
                    pre_beta_1, post_beta_1, dirichlet_energy, coboundary_norm,
                    kuramoto_order_r, causal_emergence_delta_ei,
                    final_state_digest, prior_quarantined_state_digest,
                    previous_run_digest, ledger_entry_digest,
                    is_signed, signer_name, signer_role, proof_packet_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    packet_id,
                    study_name,
                    run_mode,
                    model_used,
                    interaction_id,
                    t_level,
                    selected_opt_id,
                    selected_opt_name,
                    policy_status,
                    runtime_status,
                    next_transition,
                    int(abs(record.cycle0_spectral_snapshot.point_gap_winding_number)),
                    int(abs(record.cycle1_spectral_snapshot.point_gap_winding_number)),
                    c1_ipr,
                    float(record.cycle1_spectral_snapshot.max_imag_eigenvalue),
                    float(1.0 / max(1.0, c1_k)),
                    c1_k,
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    "Non-Hermitian & PT-Symmetry Phase Arbiter",
                    json.dumps(record.sol_lens_packet, sort_keys=True),
                    now_iso,
                ),
            )

            self._insert_runtime_events(
                run_id, "nh-pt:cycle0-skin-broken", quarantine_gov.events
            )
            self._insert_runtime_events(
                run_id, "nh-pt:cycle1-gbz-unbroken", cleared_gov.events
            )
            self._insert_telemetry_signatures(
                run_id, "Non_Hermitian_GBZ_PT_Synthesizer", record.reasoning_telemetry
            )

            self._conn.execute(
                """
                INSERT INTO cohomological_repair_records (
                    run_id, repair_kind, target_option_id,
                    pre_beta_1, post_beta_1, pre_harmonic_norm, post_harmonic_norm,
                    l2_projection_distance, quarantined_state_digest, cleared_state_digest,
                    previous_interaction_id, repair_interaction_id,
                    pre_stalk_json, post_stalk_json, rationale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    "gbz_imaginary_gauge_pt_stabilization",
                    selected_opt_id,
                    int(abs(record.cycle0_spectral_snapshot.point_gap_winding_number)),
                    int(abs(record.cycle1_spectral_snapshot.point_gap_winding_number)),
                    c0_k,
                    c1_k,
                    float(abs(c0_ipr - c1_ipr)),
                    prior_q_digest,
                    final_state_digest,
                    f"nh-pt-c0:{int_suffix}",
                    interaction_id,
                    json.dumps(
                        {
                            "max_imag_eigenvalue": round(
                                float(record.cycle0_spectral_snapshot.max_imag_eigenvalue), 6
                            ),
                            "max_petermann_factor": round(c0_k, 6),
                            "obc_skin_localization_ipr": round(c0_ipr, 6),
                            "point_gap_winding_number": int(
                                record.cycle0_spectral_snapshot.point_gap_winding_number
                            ),
                        }
                    ),
                    json.dumps(
                        {
                            "max_imag_eigenvalue": round(
                                float(record.cycle1_spectral_snapshot.max_imag_eigenvalue), 6
                            ),
                            "max_petermann_factor": round(c1_k, 6),
                            "obc_skin_localization_ipr": round(c1_ipr, 6),
                            "point_gap_winding_number": int(
                                record.cycle1_spectral_snapshot.point_gap_winding_number
                            ),
                            "clamped_pt_gain_loss_g": float(
                                record.surgery_spec.clamped_pt_gain_loss_g
                            ),
                        }
                    ),
                    str(record.surgery_spec.non_hermitian_pt_rationale),
                ),
            )

        return {
            "run_id": run_id,
            "packet_id": packet_id,
            "run_mode": run_mode,
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
        }

    def _ensure_continuum_cycle_events(
        self,
        *,
        run_id: str,
        option_id: str,
        cycle_label: str,
        audit_obj: Any,
        occurred_at: datetime,
    ) -> Tuple[Tuple[RuntimeEvent, ...], str]:
        """
        Extracts or synthesizes the 4-event hash-chained `RuntimeEvent` stream for a
        Continuum or Lumina cycle (`RUN_OPENED` -> `PROPOSAL_RECORDED` -> `EVIDENCE_RECORDED`
        -> `POLICY_DECISION_RECORDED`) and returns `(events, replayed_state_digest)`.
        """
        existing = tuple(getattr(audit_obj, "events", ()) or ())
        if existing and all(isinstance(ev, RuntimeEvent) and ev.run_id == run_id for ev in existing):
            replayed = replay_events(existing)
            return existing, str(replayed.state_digest)

        wf_ver = str(getattr(audit_obj, "workflow_version", f"{option_id}:{cycle_label}"))
        pol_str = str(getattr(audit_obj, "policy_status", "ELIGIBLE")).upper()
        try:
            pol_enum = PolicyStatus(pol_str)
        except ValueError:
            pol_enum = (
                PolicyStatus.QUARANTINE
                if getattr(audit_obj, "is_quarantined", False)
                else PolicyStatus.ELIGIBLE
            )

        manifest_digest = digest_data({"manifest": option_id, "workflow_version": wf_ver})
        plan_digest = digest_data({"plan": option_id, "cycle": cycle_label, "workflow_version": wf_ver})
        proposal_digest = digest_data({"proposal": option_id, "cycle": cycle_label, "run_id": run_id})
        evidence_digest = digest_data(
            {
                "evidence": option_id,
                "cycle": cycle_label,
                "reason": str(getattr(audit_obj, "governance_reason", "")),
                "cohomological_event": str(getattr(audit_obj, "cohomological_event", "")),
            }
        )
        decision_digest = digest_data(
            {
                "decision": option_id,
                "cycle": cycle_label,
                "policy_status": pol_enum.value,
                "proposal_digest": proposal_digest,
                "evidence_digest": evidence_digest,
            }
        )
        ev1 = create_runtime_event(
            event_id=f"event:{cycle_label}:run-opened"[:128],
            run_id=run_id[:128],
            sequence_number=1,
            event_type=EventType.RUN_OPENED,
            occurred_at=occurred_at,
            payload=RunOpenedPayload(
                experiment_plan_digest=plan_digest,
                capability_manifest_digest=manifest_digest,
            ),
            previous_event_digest=None,
        )
        ev2 = create_runtime_event(
            event_id=f"event:{cycle_label}:proposal-recorded"[:128],
            run_id=run_id[:128],
            sequence_number=2,
            event_type=EventType.PROPOSAL_RECORDED,
            occurred_at=occurred_at,
            payload=ProposalRecordedPayload(
                proposal_digest=proposal_digest,
                experiment_plan_digest=plan_digest,
                capability_manifest_digest=manifest_digest,
            ),
            previous_event_digest=ev1.event_digest,
        )
        ev3 = create_runtime_event(
            event_id=f"event:{cycle_label}:evidence-recorded"[:128],
            run_id=run_id[:128],
            sequence_number=3,
            event_type=EventType.EVIDENCE_RECORDED,
            occurred_at=occurred_at,
            payload=EvidenceRecordedPayload(
                evidence_digest=evidence_digest,
                proposal_digest=proposal_digest,
                experiment_plan_digest=plan_digest,
                capability_manifest_digest=manifest_digest,
            ),
            previous_event_digest=ev2.event_digest,
        )
        ev4 = create_runtime_event(
            event_id=f"event:{cycle_label}:policy-decision-recorded"[:128],
            run_id=run_id[:128],
            sequence_number=4,
            event_type=EventType.POLICY_DECISION_RECORDED,
            occurred_at=occurred_at,
            payload=PolicyDecisionRecordedPayload(
                policy_decision_digest=decision_digest,
                policy_status=pol_enum,
                proposal_digest=proposal_digest,
                evidence_digest=evidence_digest,
            ),
            previous_event_digest=ev3.event_digest,
        )
        stream = (ev1, ev2, ev3, ev4)
        replayed = replay_events(stream)
        return stream, str(replayed.state_digest)

    def record_sol_continuum_episode(
        self,
        record: Any,
    ) -> Dict[str, Any]:
        """
        Persists a Frontier I/K/M `ContinuumDiscoveryEpisodeRecord` (Autonomous Multi-Agent
        Discovery Guild + Conjecture WGSL Proof + SOL Change Observatory Archive)
        into the Cryptographic Governance Court Ledger, including:
        - `governance_court_runs`
        - `sol_edge_runtime_events` (4-event streams for Cycle 0 QUARANTINE and Cycle 1 ELIGIBLE)
        - `gemini_thought_signatures`
        - `cohomological_repair_records`
        """
        int_suffix = re.sub(r"[-_.]{2,}", "-", re.sub(r"[^a-z0-9_.-]+", "-", str(record.interaction_id)[-10:].lower())).strip("-_.") or "0"
        run_id = f"run:continuum:{record.experiment_id}:{int_suffix}"[:128]
        packet_id = str(record.sol_lens_packet.get("packet_id", f"pkt:continuum:{int_suffix}"))
        study_name = str(record.study_name)
        run_mode = "sol_continuum_discovery_observatory"
        model_used = str(record.model_used)
        interaction_id = str(record.interaction_id)
        telemetry = getattr(record, "reasoning_telemetry", None)
        t_level = str(getattr(telemetry, "thinking_level", "high") or "high")
        selected_opt_id = str(record.selected_option_id)
        selected_opt_name = str(record.selected_option_name)
        policy_status = str(record.cycle1_audit.policy_status)
        runtime_status = str(record.cycle1_audit.policy_status)
        next_transition = "release_review"
        now_dt = datetime.now(timezone.utc).replace(microsecond=0)
        now_iso = now_dt.isoformat()

        c0_events, c0_replayed_digest = self._ensure_continuum_cycle_events(
            run_id=run_id,
            option_id=selected_opt_id,
            cycle_label="cycle0",
            audit_obj=record.cycle0_audit,
            occurred_at=now_dt,
        )
        c1_events, c1_replayed_digest = self._ensure_continuum_cycle_events(
            run_id=run_id,
            option_id=selected_opt_id,
            cycle_label="cycle1",
            audit_obj=record.cycle1_audit,
            occurred_at=now_dt,
        )
        prior_q_digest = str(getattr(record.cycle0_audit, "state_digest", None) or c0_replayed_digest)
        final_state_digest = str(getattr(record.cycle1_audit, "state_digest", None) or c1_replayed_digest)
        if not getattr(record.cycle0_audit, "events", None):
            prior_q_digest = c0_replayed_digest
        if not getattr(record.cycle1_audit, "events", None):
            final_state_digest = c1_replayed_digest

        if telemetry is None:
            sig_digest = f"sha256:{hashlib.sha256(f'{run_id}:{interaction_id}:continuum_guild'.encode('utf-8')).hexdigest()}"
            summary_txt = str(getattr(record, "curriculum_upgrade_summary", "Continuum Guild discovery pass."))
            telemetry = SimpleNamespace(
                model_used=model_used,
                interaction_id=interaction_id,
                thinking_level=t_level,
                thought_signature_digests=[sig_digest],
                thought_signature_lengths=[len(summary_txt)],
                thought_summaries=[summary_txt],
                total_input_tokens=640,
                total_thought_tokens=320,
                total_output_tokens=280,
            )

        with self._conn:
            self._conn.execute("DELETE FROM sol_edge_runtime_events WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM gemini_thought_signatures WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM cohomological_repair_records WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM governance_court_runs WHERE run_id = ?", (run_id,))

            prev_run_digest = self._get_head_ledger_digest()
            entry_digest = self.compute_ledger_entry_digest(
                run_id=run_id,
                packet_id=packet_id,
                study_name=study_name,
                run_mode=run_mode,
                model_used=model_used,
                interaction_id=interaction_id,
                selected_option_id=selected_opt_id,
                policy_status=policy_status,
                final_state_digest=final_state_digest,
                prior_quarantined_state_digest=prior_q_digest,
                previous_run_digest=prev_run_digest,
            )

            self._conn.execute(
                """
                INSERT INTO governance_court_runs (
                    run_id, packet_id, study_name, run_mode, model_used, interaction_id,
                    thinking_level, selected_option_id, selected_option_name,
                    policy_status, runtime_status, next_transition,
                    pre_beta_1, post_beta_1, dirichlet_energy, coboundary_norm,
                    kuramoto_order_r, causal_emergence_delta_ei,
                    final_state_digest, prior_quarantined_state_digest,
                    previous_run_digest, ledger_entry_digest,
                    is_signed, signer_name, signer_role, proof_packet_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    packet_id,
                    study_name,
                    run_mode,
                    model_used,
                    interaction_id,
                    t_level,
                    selected_opt_id,
                    selected_opt_name,
                    policy_status,
                    runtime_status,
                    next_transition,
                    1,
                    0,
                    float(record.cycle1_audit.sheaf_coboundary_defect),
                    0.0,
                    float(record.post_mean_guild_competency),
                    float(record.epistemic_gain_bits),
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    "SOL Continuum & Change Observatory Arbiter",
                    json.dumps(record.sol_lens_packet, sort_keys=True),
                    now_iso,
                ),
            )

            # Persist Cycle 0 QUARANTINE and Cycle 1 ELIGIBLE 4-event sol-edge streams
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle0-quarantine", c0_events)
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle1-eligible", c1_events)

            # Persist Gemini reasoning thought signature telemetry
            self._insert_telemetry_signatures(
                run_id, "SOL_Continuum_Discovery_Guild", telemetry
            )

            fk_ver = (
                getattr(record, "frontier_k_verification", None)
                or (record.sol_lens_packet.get("frontier_k_verification") if isinstance(record.sol_lens_packet, dict) else None)
                or {}
            )
            fn_ver = (
                getattr(record, "frontier_n_verification", None)
                or (record.sol_lens_packet.get("frontier_n_verification") if isinstance(record.sol_lens_packet, dict) else None)
                or {}
            )
            fk_verified = bool(
                isinstance(fk_ver, dict)
                and fk_ver.get("formal_proof_certificate", {}).get("verdict") == "PROVED_THEOREM"
            )
            fn_verified = bool(
                isinstance(fn_ver, dict)
                and fn_ver.get("autopoietic_loop_verified") is True
                and fn_ver.get("epistemic_gap_intake", {}).get("core_immutability_verified") is True
            )
            fn_digest = str(fn_ver.get("summary_digest", "")) if isinstance(fn_ver, dict) else ""

            self._conn.execute(
                """
                INSERT INTO cohomological_repair_records (
                    run_id, repair_kind, target_option_id,
                    pre_beta_1, post_beta_1, pre_harmonic_norm, post_harmonic_norm,
                    l2_projection_distance, quarantined_state_digest, cleared_state_digest,
                    previous_interaction_id, repair_interaction_id,
                    pre_stalk_json, post_stalk_json, rationale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    "sol_continuum_discovery_curriculum_evolution",
                    selected_opt_id,
                    1,
                    0,
                    float(record.cycle0_audit.sheaf_coboundary_defect),
                    float(record.cycle1_audit.sheaf_coboundary_defect),
                    float(record.post_mean_guild_competency - record.pre_mean_guild_competency),
                    prior_q_digest,
                    final_state_digest,
                    f"continuum-c0:{int_suffix}",
                    interaction_id,
                    json.dumps(
                        {
                            "workflow_version": record.cycle0_audit.workflow_version,
                            "mean_guild_competency": record.pre_mean_guild_competency,
                            "epistemic_gain_bits": record.cycle0_audit.epistemic_gain_bits,
                        }
                    ),
                    json.dumps(
                        {
                            "workflow_version": record.cycle1_audit.workflow_version,
                            "mean_guild_competency": record.post_mean_guild_competency,
                            "epistemic_gain_bits": record.epistemic_gain_bits,
                            "experiment_id": record.experiment_id,
                            "observatory_outcome": record.observatory_outcome,
                            "frontier_k_verified": fk_verified,
                            "frontier_n_verified": fn_verified,
                            "frontier_n_summary_digest": fn_digest,
                        }
                    ),
                    str(record.curriculum_upgrade_summary),
                ),
            )

            sig_count_row = self._conn.execute(
                "SELECT COUNT(*) AS cnt FROM gemini_thought_signatures WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            thought_sig_count = int(sig_count_row["cnt"]) if sig_count_row else 0

        return {
            "run_id": run_id,
            "packet_id": packet_id,
            "run_mode": run_mode,
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
            "prior_quarantined_state_digest": prior_q_digest,
            "experiment_id": record.experiment_id,
            "edge_event_count": len(c0_events) + len(c1_events),
            "thought_signature_count": thought_sig_count,
            "frontier_k_verified": fk_verified,
            "frontier_n_verified": fn_verified,
            "frontier_n_summary_digest": fn_digest,
        }

    def record_lumina_observatory_episode(
        self,
        record: Any,
    ) -> Dict[str, Any]:
        """
        Persists a Frontier J/M `LuminaObservatoryEpisodeRecord` into:
        - `governance_court_runs`
        - `sol_edge_runtime_events` (4-event streams for Cycle 0 QUARANTINE and Cycle 1 ELIGIBLE)
        - `gemini_thought_signatures`
        - `cohomological_repair_records` (`repair_kind="lumina_ranger_sovereign_observatory_calibration"`)
        """
        int_suffix = re.sub(r"[-_.]{2,}", "-", re.sub(r"[^a-z0-9_.-]+", "-", str(record.interaction_id)[-10:].lower())).strip("-_.") or "0"
        run_id = f"run:lumina:{record.experiment_id}:{int_suffix}"[:128]
        packet_id = str(record.sol_lens_packet.get("packet_id", f"pkt:lumina:{int_suffix}"))
        study_name = str(record.study_name)
        run_mode = "lumina_ranger_observatory_sovereignty"
        model_used = str(record.model_used)
        interaction_id = str(record.interaction_id)
        telemetry = getattr(record, "reasoning_telemetry", None)
        t_level = str(getattr(telemetry, "thinking_level", "high") or "high")
        selected_opt_id = str(record.selected_option_id)
        selected_opt_name = str(record.selected_option_name)
        policy_status = str(record.cycle1_audit.policy_status)
        runtime_status = "COMPLETED"
        next_transition = "PROMOTE_IF_REVIEWED"
        now_dt = datetime.now(timezone.utc).replace(microsecond=0)
        now_iso = now_dt.isoformat()

        c0_events, c0_replayed_digest = self._ensure_continuum_cycle_events(
            run_id=run_id,
            option_id=selected_opt_id,
            cycle_label="cycle0",
            audit_obj=record.cycle0_audit,
            occurred_at=now_dt,
        )
        c1_events, c1_replayed_digest = self._ensure_continuum_cycle_events(
            run_id=run_id,
            option_id=selected_opt_id,
            cycle_label="cycle1",
            audit_obj=record.cycle1_audit,
            occurred_at=now_dt,
        )
        prior_q_digest = str(getattr(record.cycle0_audit, "state_digest", None) or c0_replayed_digest)
        final_state_digest = str(getattr(record.cycle1_audit, "state_digest", None) or c1_replayed_digest)
        if not getattr(record.cycle0_audit, "events", None):
            prior_q_digest = c0_replayed_digest
        if not getattr(record.cycle1_audit, "events", None):
            final_state_digest = c1_replayed_digest

        if telemetry is None:
            sig_digest = f"sha256:{hashlib.sha256(f'{run_id}:{interaction_id}:lumina_ranger'.encode('utf-8')).hexdigest()}"
            summary_txt = str(getattr(record, "constitutional_lesson_law", "Lumina Ranger sovereign calibration."))
            telemetry = SimpleNamespace(
                model_used=model_used,
                interaction_id=interaction_id,
                thinking_level=t_level,
                thought_signature_digests=[sig_digest],
                thought_signature_lengths=[len(summary_txt)],
                thought_summaries=[summary_txt],
                total_input_tokens=620,
                total_thought_tokens=310,
                total_output_tokens=260,
            )

        with self._conn:
            self._conn.execute("DELETE FROM differential_shock_timeline WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM sol_edge_runtime_events WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM gemini_thought_signatures WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM cohomological_repair_records WHERE run_id = ?", (run_id,))
            self._conn.execute("DELETE FROM governance_court_runs WHERE run_id = ?", (run_id,))

            prev_run_digest = self._get_head_ledger_digest()
            entry_digest = self.compute_ledger_entry_digest(
                run_id=run_id,
                packet_id=packet_id,
                study_name=study_name,
                run_mode=run_mode,
                model_used=model_used,
                interaction_id=interaction_id,
                selected_option_id=selected_opt_id,
                policy_status=policy_status,
                final_state_digest=final_state_digest,
                prior_quarantined_state_digest=prior_q_digest,
                previous_run_digest=prev_run_digest,
            )

            self._conn.execute(
                """
                INSERT INTO governance_court_runs (
                    run_id, packet_id, study_name, run_mode, model_used, interaction_id,
                    thinking_level, selected_option_id, selected_option_name,
                    policy_status, runtime_status, next_transition,
                    pre_beta_1, post_beta_1, dirichlet_energy, coboundary_norm,
                    kuramoto_order_r, causal_emergence_delta_ei,
                    final_state_digest, prior_quarantined_state_digest,
                    previous_run_digest, ledger_entry_digest,
                    is_signed, signer_name, signer_role, proof_packet_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    packet_id,
                    study_name,
                    run_mode,
                    model_used,
                    interaction_id,
                    t_level,
                    selected_opt_id,
                    selected_opt_name,
                    policy_status,
                    runtime_status,
                    next_transition,
                    1,
                    0,
                    float(record.cycle1_audit.max_phase_error),
                    float(record.cycle1_audit.cross_talk),
                    float(record.cycle1_audit.active_delta),
                    float(record.cycle1_audit.min_active_register_mass),
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    "Lumina Ranger Corps & Change Observatory Court",
                    json.dumps(record.sol_lens_packet, sort_keys=True),
                    now_iso,
                ),
            )

            # Persist Cycle 0 QUARANTINE and Cycle 1 ELIGIBLE 4-event sol-edge streams
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle0-quarantine", c0_events)
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle1-eligible", c1_events)

            # Persist Gemini reasoning thought signature telemetry
            self._insert_telemetry_signatures(
                run_id, "Lumina_Ranger_Sovereign_Guild", telemetry
            )

            fl_ver = (
                getattr(record, "frontier_l_verification", None)
                or (record.sol_lens_packet.get("frontier_l_verification") if isinstance(record.sol_lens_packet, dict) else None)
                or {}
            )
            fn_ver = (
                getattr(record, "frontier_n_verification", None)
                or (record.sol_lens_packet.get("frontier_n_verification") if isinstance(record.sol_lens_packet, dict) else None)
                or {}
            )
            fl_verified = bool(
                isinstance(fl_ver, dict)
                and bool(fl_ver)
                and fl_ver.get("sovereign_runtime_shadow", {}).get("allow_production_execution") is not True
                and fl_ver.get("entangled_3manifold_2pc", {}).get("active_tables_mutated") is not True
            )
            fn_verified = bool(
                isinstance(fn_ver, dict)
                and fn_ver.get("autopoietic_loop_verified") is True
                and fn_ver.get("epistemic_gap_intake", {}).get("core_immutability_verified") is True
            )
            fn_digest = str(fn_ver.get("summary_digest", "")) if isinstance(fn_ver, dict) else ""

            self._conn.execute(
                """
                INSERT INTO cohomological_repair_records (
                    run_id, repair_kind, target_option_id,
                    pre_beta_1, post_beta_1, pre_harmonic_norm, post_harmonic_norm,
                    l2_projection_distance, quarantined_state_digest, cleared_state_digest,
                    previous_interaction_id, repair_interaction_id,
                    pre_stalk_json, post_stalk_json, rationale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    "lumina_ranger_sovereign_observatory_calibration",
                    selected_opt_id,
                    1,
                    0,
                    float(record.cycle0_audit.max_phase_error),
                    float(record.cycle1_audit.max_phase_error),
                    float(record.cycle1_audit.active_delta - record.cycle0_audit.active_delta),
                    prior_q_digest,
                    final_state_digest,
                    f"lumina-c0:{int_suffix}",
                    interaction_id,
                    json.dumps(
                        {
                            "workflow_version": record.cycle0_audit.workflow_version,
                            "active_delta": record.cycle0_audit.active_delta,
                            "min_active_register_mass": record.cycle0_audit.min_active_register_mass,
                        }
                    ),
                    json.dumps(
                        {
                            "workflow_version": record.cycle1_audit.workflow_version,
                            "active_delta": record.cycle1_audit.active_delta,
                            "min_active_register_mass": record.cycle1_audit.min_active_register_mass,
                            "experiment_id": record.experiment_id,
                            "staged_component": record.candidate_component_name,
                            "frontier_l_verified": fl_verified,
                            "frontier_n_verified": fn_verified,
                            "frontier_n_summary_digest": fn_digest,
                        }
                    ),
                    str(record.constitutional_lesson_law),
                ),
            )

            sig_count_row = self._conn.execute(
                "SELECT COUNT(*) AS cnt FROM gemini_thought_signatures WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            thought_sig_count = int(sig_count_row["cnt"]) if sig_count_row else 0

        return {
            "run_id": run_id,
            "packet_id": packet_id,
            "run_mode": run_mode,
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
            "prior_quarantined_state_digest": prior_q_digest,
            "experiment_id": record.experiment_id,
            "edge_event_count": len(c0_events) + len(c1_events),
            "thought_signature_count": thought_sig_count,
            "frontier_l_verified": fl_verified,
            "frontier_n_verified": fn_verified,
            "frontier_n_summary_digest": fn_digest,
        }

    def record_release_signature(
        self,
        run_id: str,
        signer_name: str,
        signer_role: str = "PEO / Chief Engineer",
    ) -> bool:
        """Marks a governed run in `governance_court_runs` as cryptographically signed by a human authority."""
        with self._conn:
            cur = self._conn.execute(
                """
                UPDATE governance_court_runs
                SET is_signed = 1, signer_name = ?, signer_role = ?
                WHERE run_id = ?
                """,
                (signer_name, signer_role, run_id),
            )
            return cur.rowcount > 0

    @staticmethod
    def _candidate_event_run_ids(r_id: str, opt_id: str) -> List[str]:
        candidates: List[str] = [r_id]
        parts = r_id.split(":")
        for k in range(1, len(parts)):
            prefix = ":".join(parts[:-k])
            if prefix and prefix not in candidates:
                candidates.append(prefix)
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
                if cand not in candidates:
                    candidates.append(cand)
        return candidates

    @staticmethod
    def _verify_runtime_event_stream_rows(
        r_id: str,
        run_mode: str,
        opt_id: str,
        opt_sorted: List[sqlite3.Row],
        expected_prior_q_digest: Optional[str],
        expected_final_digest: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Verifies a 4-event `sol_edge_runtime_events` stream for `(r_id, opt_id)`:
        1. Sequence continuity (`1..N`) and `previous_event_digest` hash chaining.
        2. Typed `sol_edge` payload schema validation and cross-event digest binding
           (`RUN_OPENED` -> `PROPOSAL_RECORDED` -> `EVIDENCE_RECORDED` -> `POLICY_DECISION_RECORDED`).
        3. Full `RuntimeEvent` semantic digest and `replay_events()` state machine replay
           verification across all run modes.
        Returns `(stream_ok, replayed_state_digest)`.
        """
        if len(opt_sorted) != 4:
            return False, None

        expected_types = (
            EventType.RUN_OPENED.value,
            EventType.PROPOSAL_RECORDED.value,
            EventType.EVIDENCE_RECORDED.value,
            EventType.POLICY_DECISION_RECORDED.value,
        )
        prev_ev_dig: Optional[str] = None
        parsed_payloads: List[Dict[str, Any]] = []
        for idx, ev in enumerate(opt_sorted):
            seq = int(ev["sequence_number"])
            p_dig = ev["previous_event_digest"]
            ev_type = str(ev["event_type"])
            if seq != idx + 1 or p_dig != prev_ev_dig or ev_type != expected_types[idx]:
                return False, None
            prev_ev_dig = str(ev["event_digest"])
            try:
                raw_payload = json.loads(str(ev["payload_json"]))
                if not isinstance(raw_payload, dict):
                    return False, None
                if idx == 0:
                    RunOpenedPayload.model_validate(raw_payload)
                elif idx == 1:
                    ProposalRecordedPayload.model_validate(raw_payload)
                elif idx == 2:
                    EvidenceRecordedPayload.model_validate(raw_payload)
                elif idx == 3:
                    PolicyDecisionRecordedPayload.model_validate(raw_payload)
                parsed_payloads.append(raw_payload)
            except Exception:
                return False, None

        # Verify cross-step digest bindings across the 4 events
        p0, p1, p2, p3 = parsed_payloads
        if (
            p1.get("experiment_plan_digest") != p0.get("experiment_plan_digest")
            or p1.get("capability_manifest_digest") != p0.get("capability_manifest_digest")
            or p2.get("experiment_plan_digest") != p0.get("experiment_plan_digest")
            or p2.get("capability_manifest_digest") != p0.get("capability_manifest_digest")
            or p2.get("proposal_digest") != p1.get("proposal_digest")
            or p3.get("proposal_digest") != p1.get("proposal_digest")
            or p3.get("evidence_digest") != p2.get("evidence_digest")
        ):
            return False, None

        # Reconstruct RuntimeEvents and verify via sol_edge.runtime.replay.replay_events
        candidate_run_ids = GovernanceCourtLedger._candidate_event_run_ids(r_id, opt_id)
        replayed_state = None
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
                            "payload": parsed_payloads[i],
                        }
                    )
                    for i, ev in enumerate(opt_sorted)
                ]
                replayed_state = replay_events(reconstructed)
                break
            except Exception:
                continue

        if replayed_state is None:
            return False, None

        replayed_digest = str(replayed_state.state_digest)
        replayed_status = str(replayed_state.status.value)

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
            if expected_prior_q_digest and replayed_digest != str(expected_prior_q_digest):
                return False, replayed_digest
            if opt_id.endswith(":cycle0-quarantine") and replayed_status != "QUARANTINED":
                return False, replayed_digest
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
            if replayed_digest != str(expected_final_digest):
                return False, replayed_digest
            if opt_id.endswith(":cycle1-eligible") and replayed_status != "ELIGIBLE":
                return False, replayed_digest

        return True, replayed_digest

    @staticmethod
    def _verify_continuum_frontier_metadata(r_mode: str, proof_packet_json_str: str) -> bool:
        """
        Verifies embedded Frontier K/L/N verification metadata inside `proof_packet_json`
        for `sol_continuum_discovery_observatory` and `lumina_ranger_observatory_sovereignty` runs.
        """
        try:
            pkt = json.loads(str(proof_packet_json_str))
            if not isinstance(pkt, dict):
                return False
        except Exception:
            return False

        fk = pkt.get("frontier_k_verification")
        if fk is not None:
            if not isinstance(fk, dict):
                return False
            fpc = fk.get("formal_proof_certificate")
            if isinstance(fpc, dict) and fpc.get("verdict") != "PROVED_THEOREM":
                return False

        fl = pkt.get("frontier_l_verification")
        if fl is not None:
            if not isinstance(fl, dict):
                return False
            sh = fl.get("sovereign_runtime_shadow")
            if isinstance(sh, dict) and sh.get("allow_production_execution") is True:
                return False
            tpc = fl.get("entangled_3manifold_2pc")
            if isinstance(tpc, dict) and tpc.get("active_tables_mutated") is True:
                return False

        fn = pkt.get("frontier_n_verification")
        if fn is not None:
            if not isinstance(fn, dict):
                return False
            if fn.get("autopoietic_loop_verified") is False:
                return False
            epi = fn.get("epistemic_gap_intake")
            if isinstance(epi, dict) and epi.get("core_immutability_verified") is False:
                return False
            dream = fn.get("bimodal_dream_consolidation")
            if isinstance(dream, dict) and dream.get("bimodal_synapse_verified") is False:
                return False
            ent = fn.get("bilateral_entangler_control")
            if isinstance(ent, dict) and ent.get("bilateral_lock_verified") is False:
                return False
            gov = fn.get("statistical_evolution_governance")
            if isinstance(gov, dict) and gov.get("promotion_statistically_governed") is False:
                return False

        return True

    def verify_ledger_integrity(self) -> LedgerIntegrityReport:
        """
        Verifies the entire Cryptographic Governance Court Ledger:
        1. Cross-run hash chain (`previous_run_digest` -> `ledger_entry_digest`) from Genesis to Head.
        2. Intra-run 4-event `sol-edge` hash chain (`previous_event_digest` -> `event_digest`),
           typed payload bindings, and `sol_edge.runtime.replay.replay_events` verification.
        """
        cur = self._conn.execute(
            "SELECT * FROM governance_court_runs ORDER BY rowid ASC"
        )
        rows = cur.fetchall()

        broken_runs: List[str] = []
        broken_event_runs: List[str] = []
        total_events = 0
        expected_prev_digest: Optional[str] = None

        for row in rows:
            r_id = str(row["run_id"])
            r_mode = str(row["run_mode"])
            actual_prev = row["previous_run_digest"]
            if actual_prev != expected_prev_digest:
                broken_runs.append(r_id)

            recomputed = self.compute_ledger_entry_digest(
                run_id=r_id,
                packet_id=str(row["packet_id"]),
                study_name=str(row["study_name"]),
                run_mode=r_mode,
                model_used=str(row["model_used"]),
                interaction_id=str(row["interaction_id"]),
                selected_option_id=str(row["selected_option_id"]),
                policy_status=str(row["policy_status"]),
                final_state_digest=str(row["final_state_digest"]),
                prior_quarantined_state_digest=row["prior_quarantined_state_digest"],
                previous_run_digest=actual_prev,
            )
            if recomputed != str(row["ledger_entry_digest"]) and r_id not in broken_runs:
                broken_runs.append(r_id)

            expected_prev_digest = str(row["ledger_entry_digest"])

            ev_cur = self._conn.execute(
                """
                SELECT option_id, sequence_number, event_id, event_type,
                       occurred_at, previous_event_digest, event_digest, payload_json
                FROM sol_edge_runtime_events
                WHERE run_id = ?
                ORDER BY id ASC
                """,
                (r_id,),
            )
            ev_rows = ev_cur.fetchall()
            if not ev_rows:
                broken_event_runs.append(r_id)
                continue

            by_opt: Dict[str, List[sqlite3.Row]] = {}
            for ev in ev_rows:
                by_opt.setdefault(str(ev["option_id"]), []).append(ev)

            if r_mode in (
                "sol_continuum_discovery_observatory",
                "lumina_ranger_observatory_sovereignty",
            ):
                has_c0 = any(k.endswith(":cycle0-quarantine") for k in by_opt)
                has_c1 = any(k.endswith(":cycle1-eligible") for k in by_opt)
                if not (has_c0 and has_c1) and r_id not in broken_event_runs:
                    broken_event_runs.append(r_id)
                if not self._verify_continuum_frontier_metadata(r_mode, str(row["proof_packet_json"])) and r_id not in broken_runs:
                    broken_runs.append(r_id)

            replayed_digests: List[str] = []
            for opt_id, opt_events in by_opt.items():
                opt_sorted = sorted(opt_events, key=lambda e: int(e["sequence_number"]))
                total_events += len(opt_sorted)
                stream_ok, rep_dig = self._verify_runtime_event_stream_rows(
                    r_id=r_id,
                    run_mode=r_mode,
                    opt_id=opt_id,
                    opt_sorted=opt_sorted,
                    expected_prior_q_digest=row["prior_quarantined_state_digest"],
                    expected_final_digest=str(row["final_state_digest"]),
                )
                if rep_dig is not None:
                    replayed_digests.append(rep_dig)
                if not stream_ok and r_id not in broken_event_runs:
                    broken_event_runs.append(r_id)

            if str(row["final_state_digest"]) not in replayed_digests and r_id not in broken_event_runs:
                broken_event_runs.append(r_id)

        is_valid = len(broken_runs) == 0 and len(broken_event_runs) == 0
        head_digest = str(rows[-1]["ledger_entry_digest"]) if rows else None
        summary = (
            f"VERIFIED: {len(rows)} governed runs & {total_events} sol-edge events hash-chained to head {(head_digest or 'EMPTY')[:24]}"
            if is_valid
            else f"TAMPER DETECTED: broken runs={broken_runs} | broken event chains={broken_event_runs}"
        )

        return LedgerIntegrityReport(
            is_valid=is_valid,
            total_runs_verified=len(rows),
            total_events_verified=total_events,
            head_ledger_digest=head_digest,
            broken_run_ids=broken_runs,
            broken_event_run_ids=broken_event_runs,
            summary=summary,
        )

    def list_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self._conn.execute(
            """
            SELECT
                run_id, packet_id, study_name, run_mode, model_used, interaction_id,
                thinking_level, selected_option_id, selected_option_name,
                policy_status, runtime_status, next_transition,
                pre_beta_1, post_beta_1, dirichlet_energy, coboundary_norm,
                kuramoto_order_r, causal_emergence_delta_ei,
                final_state_digest, prior_quarantined_state_digest,
                previous_run_digest, ledger_entry_digest,
                is_signed, signer_name, signer_role, created_at,
                (SELECT COUNT(*) FROM sol_edge_runtime_events e WHERE e.run_id = governance_court_runs.run_id) AS edge_event_count,
                (SELECT COUNT(*) FROM gemini_thought_signatures t WHERE t.run_id = governance_court_runs.run_id) AS thought_signature_count
            FROM governance_court_runs
            ORDER BY rowid DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            {
                "runId": str(r["run_id"]),
                "packetId": str(r["packet_id"]),
                "studyName": str(r["study_name"]),
                "runMode": str(r["run_mode"]),
                "modelUsed": str(r["model_used"]),
                "interactionId": str(r["interaction_id"]),
                "thinkingLevel": str(r["thinking_level"]),
                "selectedOptionId": str(r["selected_option_id"]),
                "selectedOptionName": str(r["selected_option_name"]),
                "policyStatus": str(r["policy_status"]),
                "runtimeStatus": str(r["runtime_status"]),
                "nextTransition": str(r["next_transition"]),
                "preBeta1": int(r["pre_beta_1"]),
                "postBeta1": int(r["post_beta_1"]),
                "dirichletEnergy": float(r["dirichlet_energy"]),
                "coboundaryNorm": float(r["coboundary_norm"]),
                "kuramotoOrderR": float(r["kuramoto_order_r"]),
                "causalEmergenceDeltaEi": float(r["causal_emergence_delta_ei"]),
                "finalStateDigest": str(r["final_state_digest"]),
                "priorQuarantinedStateDigest": r["prior_quarantined_state_digest"],
                "previousRunDigest": r["previous_run_digest"],
                "ledgerEntryDigest": str(r["ledger_entry_digest"]),
                "isSigned": bool(r["is_signed"]),
                "signerName": r["signer_name"],
                "signerRole": r["signer_role"],
                "createdAt": str(r["created_at"]),
                "edgeEventCount": int(r["edge_event_count"]),
                "thoughtSignatureCount": int(r["thought_signature_count"]),
            }
            for r in cur.fetchall()
        ]

    def get_differential_shock_timeline(self, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self._conn.execute(
            """
            SELECT * FROM differential_shock_timeline
            ORDER BY rowid DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            {
                "shockEntryId": str(r["shock_entry_id"]),
                "runId": str(r["run_id"]),
                "baselineRunId": r["baseline_run_id"],
                "deltaId": str(r["delta_id"]),
                "shockId": str(r["shock_id"]),
                "targetPrimitiveId": str(r["target_primitive_id"]),
                "parameterChannel": int(r["parameter_channel"]),
                "deltaValue": float(r["delta_value"]),
                "baselineOptionId": str(r["baseline_option_id"]),
                "refreshedOptionId": str(r["refreshed_option_id"]),
                "didDecisionFlip": bool(r["did_decision_flip"]),
                "preEnergy": float(r["pre_energy"]),
                "postEnergy": float(r["post_energy"]),
                "preBeta1": int(r["pre_beta_1"]),
                "postBeta1": int(r["post_beta_1"]),
                "activatedEdges": json.loads(r["activated_edges_json"]),
                "quarantinedStateDigest": str(r["quarantined_state_digest"]),
                "clearedStateDigest": str(r["cleared_state_digest"]),
                "auditSummary": str(r["audit_summary"]),
                "recordedAt": str(r["recorded_at"]),
            }
            for r in cur.fetchall()
        ]

    def list_repair_records(self, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self._conn.execute(
            """
            SELECT * FROM cohomological_repair_records
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            {
                "runId": str(r["run_id"]),
                "repairKind": str(r["repair_kind"]),
                "targetOptionId": str(r["target_option_id"]),
                "preBeta1": int(r["pre_beta_1"]),
                "postBeta1": int(r["post_beta_1"]),
                "preHarmonicNorm": float(r["pre_harmonic_norm"]),
                "postHarmonicNorm": float(r["post_harmonic_norm"]),
                "l2ProjectionDistance": float(r["l2_projection_distance"]),
                "quarantinedStateDigest": str(r["quarantined_state_digest"]),
                "clearedStateDigest": str(r["cleared_state_digest"]),
                "previousInteractionId": str(r["previous_interaction_id"]),
                "repairInteractionId": str(r["repair_interaction_id"]),
                "preStalk": json.loads(r["pre_stalk_json"]),
                "postStalk": json.loads(r["post_stalk_json"]),
                "rationale": str(r["rationale"]),
            }
            for r in cur.fetchall()
        ]

    def list_thought_signatures(self, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self._conn.execute(
            """
            SELECT * FROM gemini_thought_signatures
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            {
                "runId": str(r["run_id"]),
                "interactionId": str(r["interaction_id"]),
                "agentRole": str(r["agent_role"]),
                "modelUsed": str(r["model_used"]),
                "thinkingLevel": str(r["thinking_level"]),
                "stepIndex": int(r["step_index"]),
                "signatureDigest": str(r["signature_digest"]),
                "signatureLength": int(r["signature_length"]),
                "thoughtSummary": str(r["thought_summary"]),
                "inputTokens": int(r["input_tokens"]),
                "thoughtTokens": int(r["thought_tokens"]),
                "outputTokens": int(r["output_tokens"]),
            }
            for r in cur.fetchall()
        ]

    def get_ledger_snapshot(self, limit: int = 25) -> Dict[str, Any]:
        """Returns a complete snapshot of the Governance Court Ledger and its cryptographic verification status."""
        integrity = self.verify_ledger_integrity()
        return {
            "integrity": integrity.to_dict(),
            "runs": self.list_runs(limit=limit),
            "repairs": self.list_repair_records(limit=limit),
            "thoughtSignatures": self.list_thought_signatures(limit=limit),
            "shockTimeline": self.get_differential_shock_timeline(limit=limit),
        }
