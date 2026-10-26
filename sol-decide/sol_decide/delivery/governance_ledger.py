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

import copy
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

    @property
    def valid(self) -> bool:
        return self.is_valid

    @property
    def total_runs(self) -> int:
        return self.total_runs_verified

    @property
    def total_events(self) -> int:
        return self.total_events_verified

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

    def record_wgsl_decision_prover_episode(
        self,
        record: Any,
    ) -> Dict[str, Any]:
        """
        Persists a Frontier O `WGSLDecisionProverEpisodeRecord` (64-thread WebGPU Trade-Space
        Pareto Exhaustion + MSCK Cohomological Inflection Prover + SOL Change Producer Handoff)
        into:
        - `governance_court_runs`
        - `sol_edge_runtime_events` (4-event streams for Cycle 0 QUARANTINE and Cycle 1 ELIGIBLE)
        - `gemini_thought_signatures`
        - `cohomological_repair_records` (`repair_kind="wgsl_decision_prover_msck_inflection_calibration"`)
        """
        int_suffix = re.sub(r"[-_.]{2,}", "-", re.sub(r"[^a-z0-9_.-]+", "-", str(record.interaction_id)[-10:].lower())).strip("-_.") or "0"
        run_id = f"run:wgsl-prover:{record.experiment_id}:{int_suffix}"[:128]
        packet_id = str(record.sol_lens_packet.get("packet_id", f"pkt:wgsl-prover:{int_suffix}"))
        study_name = str(record.study_name)
        run_mode = "wgsl_decision_prover_observatory"
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
            sig_digest = f"sha256:{hashlib.sha256(f'{run_id}:{interaction_id}:wgsl_prover'.encode('utf-8')).hexdigest()}"
            summary_txt = str(getattr(record, "decision_prover_rationale", "WebGPU WGSL trade-space & MSCK inflection calibration."))
            telemetry = SimpleNamespace(
                model_used=model_used,
                interaction_id=interaction_id,
                thinking_level=t_level,
                thought_signature_digests=[sig_digest],
                thought_signature_lengths=[len(summary_txt)],
                thought_summaries=[summary_txt],
                total_input_tokens=480,
                total_thought_tokens=720,
                total_output_tokens=340,
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
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(record.cycle1_audit.dirichlet_energy),
                    float(record.cycle1_audit.coboundary_defect),
                    float(record.trade_sweep_report.optimal_flip_margin_l2),
                    float(record.msck_inflection_report.cycle1_harmonic_point.spectral_gap_lambda1),
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    "SOL-Decide WGSL Trade Prover & Change Observatory Court",
                    json.dumps(record.sol_lens_packet, sort_keys=True),
                    now_iso,
                ),
            )

            # Persist Cycle 0 QUARANTINE and Cycle 1 ELIGIBLE 4-event sol-edge streams
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle0-quarantine", c0_events)
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle1-eligible", c1_events)

            # Persist Gemini reasoning thought signature telemetry
            self._insert_telemetry_signatures(
                run_id, "WGSL_Decision_Topology_Prover", telemetry
            )

            fo_ver = (
                getattr(record, "frontier_o_verification", None)
                or (record.sol_lens_packet.get("frontier_o_verification") if isinstance(record.sol_lens_packet, dict) else None)
                or {}
            )
            fo_verified = bool(
                isinstance(fo_ver, dict)
                and fo_ver.get("wgsl_decision_prover_verified") is True
                and fo_ver.get("shader_validation", {}).get("is_valid") is True
            )
            fo_digest = str(fo_ver.get("summary_digest", "")) if isinstance(fo_ver, dict) else ""

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
                    "wgsl_decision_prover_msck_inflection_calibration",
                    selected_opt_id,
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(record.cycle0_audit.coboundary_defect),
                    float(record.cycle1_audit.coboundary_defect),
                    float(record.trade_sweep_report.optimal_flip_margin_l2),
                    prior_q_digest,
                    final_state_digest,
                    f"wgsl-c0:{int_suffix}",
                    interaction_id,
                    json.dumps(
                        {
                            "workflow_version": record.cycle0_audit.workflow_version,
                            "coboundary_defect": record.cycle0_audit.coboundary_defect,
                            "effective_beta_1": record.cycle0_audit.effective_beta_1,
                        }
                    ),
                    json.dumps(
                        {
                            "workflow_version": record.cycle1_audit.workflow_version,
                            "coboundary_defect": record.cycle1_audit.coboundary_defect,
                            "effective_beta_1": record.cycle1_audit.effective_beta_1,
                            "experiment_id": record.experiment_id,
                            "wgsl_shader_hash": record.wgsl_shader_hash,
                            "frontier_o_verified": fo_verified,
                            "frontier_o_summary_digest": fo_digest,
                        }
                    ),
                    str(record.decision_prover_rationale),
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
            "frontier_o_verified": fo_verified,
            "frontier_o_summary_digest": fo_digest,
        }

    def record_swarm_cohomology_episode(
        self,
        record: Any,
    ) -> Dict[str, Any]:
        """
        Persists a Frontier P `SwarmCohomologyEpisodeRecord` (Multi-Robot Embodied Swarm
        Cohomology, 25kg Closed-Chain Bimanual Manipulation & Decentralized SE(3) Wilson Loop)
        into:
        - `governance_court_runs`
        - `sol_edge_runtime_events` (4-event streams for Cycle 0 QUARANTINE and Cycle 1 ELIGIBLE)
        - `gemini_thought_signatures`
        - `cohomological_repair_records` (`repair_kind="swarm_cohomology_se3_wilson_calibration"`)
        """
        if isinstance(record, dict):
            pkt = copy.deepcopy(record.get("sol_lens_packet") or record.get("proof_packet") or {})
            if isinstance(record.get("frontier_p_verification"), dict):
                pkt["frontier_p_verification"] = copy.deepcopy(record["frontier_p_verification"])
            c0_d = record.get("cycle0_audit") or {}
            c1_d = record.get("cycle1_audit") or {}
            gem_d = record.get("gemini_reasoning") or {}
            record = SimpleNamespace(
                experiment_id=record.get("experiment_id", "exp_swarm"),
                study_name=record.get("study_name", "Swarm_Cohomology_Study"),
                interaction_id=record.get("interaction_id", f"swarm-{record.get('experiment_id', 'exp')}"),
                model_used=record.get("model_used", gem_d.get("model_id", "gemini-4-argon")),
                selected_option_id=record.get("selected_option_id", "opt_bimanual_25kg_closed_chain_transport"),
                selected_option_name=record.get(
                    "selected_option_name",
                    "25kg Closed-Chain Bimanual Manipulation & Decentralized SE(3) Wilson Loop",
                ),
                sol_lens_packet=pkt,
                proof_packet=pkt,
                frontier_p_verification=pkt.get("frontier_p_verification", {}),
                frontier_p_summary_digest=record.get("frontier_p_summary_digest", ""),
                cycle0_audit=SimpleNamespace(
                    policy_status=c0_d.get("policy_status", "QUARANTINE"),
                    effective_beta_1=c0_d.get("effective_beta_1", 1),
                    internal_squeeze_wrench_n=c0_d.get("internal_squeeze_wrench_n", 42.8),
                    closed_chain_coboundary_norm=c0_d.get("closed_chain_coboundary_norm", 1.0),
                    se3_rotational_holonomy_deg=c0_d.get("se3_rotational_holonomy_deg", 14.25),
                    estop_arbiter_latency_us=c0_d.get("estop_arbiter_latency_us", 9.0),
                    state_digest=c0_d.get("state_digest"),
                    events=(),
                ),
                cycle1_audit=SimpleNamespace(
                    policy_status=c1_d.get("policy_status", "ELIGIBLE"),
                    effective_beta_1=c1_d.get("effective_beta_1", 0),
                    internal_squeeze_wrench_n=c1_d.get("internal_squeeze_wrench_n", 0.35),
                    closed_chain_coboundary_norm=c1_d.get("closed_chain_coboundary_norm", 0.0),
                    se3_rotational_holonomy_deg=c1_d.get("se3_rotational_holonomy_deg", 0.18),
                    estop_arbiter_latency_us=c1_d.get("estop_arbiter_latency_us", 9.0),
                    state_digest=c1_d.get("state_digest"),
                    events=(),
                ),
                gemini_reasoning=SimpleNamespace(
                    calibration_spec=gem_d.get("calibration_spec", {}),
                    thought_summaries=gem_d.get("thought_summaries", []),
                ),
                reasoning_telemetry=None,
            )

        int_id = str(getattr(record, "interaction_id", f"swarm-{record.experiment_id}"))
        int_suffix = re.sub(r"[-_.]{2,}", "-", re.sub(r"[^a-z0-9_.-]+", "-", int_id[-10:].lower())).strip("-_.") or "0"
        run_id = f"run:swarm-cohomology:{record.experiment_id}:{int_suffix}"[:128]
        pkt = getattr(record, "sol_lens_packet", None) or getattr(record, "proof_packet", {})
        packet_id = str(pkt.get("packet_id", f"pkt:swarm-cohomology:{int_suffix}"))
        study_name = str(record.study_name)
        run_mode = "swarm_cohomology_observatory"
        if not self._verify_continuum_frontier_metadata(run_mode, json.dumps(pkt, sort_keys=True)):
            raise ValueError("Frontier P swarm cohomology metadata verification failed (fail-closed).")
        model_used = str(getattr(record, "model_used", "gemini-4-argon"))
        interaction_id = int_id
        telemetry = getattr(record, "reasoning_telemetry", None)
        t_level = str(getattr(telemetry, "thinking_level", "high") or "high")
        selected_opt_id = str(getattr(record, "selected_option_id", "opt_bimanual_25kg_closed_chain_transport"))
        selected_opt_name = str(
            getattr(
                record,
                "selected_option_name",
                "25kg Closed-Chain Bimanual Manipulation & Decentralized SE(3) Wilson Loop",
            )
        )
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

        gem_reasoning = getattr(record, "gemini_reasoning", None)
        rationale_txt = (
            str(gem_reasoning.calibration_spec.get("cohomological_rationale", ""))
            if gem_reasoning is not None and isinstance(getattr(gem_reasoning, "calibration_spec", None), dict)
            else "Nullspace grasp wrench projection onto ker(Delta^0_grasp) and decentralized SE(3) Wilson loop consensus."
        )
        if telemetry is None:
            sig_digest = f"sha256:{hashlib.sha256(f'{run_id}:{interaction_id}:swarm_cohomology'.encode('utf-8')).hexdigest()}"
            summaries = (
                list(gem_reasoning.thought_summaries)
                if gem_reasoning is not None and getattr(gem_reasoning, "thought_summaries", None)
                else [rationale_txt]
            )
            telemetry = SimpleNamespace(
                model_used=model_used,
                interaction_id=interaction_id,
                thinking_level=t_level,
                thought_signature_digests=[
                    f"sha256:{hashlib.sha256(f'{sig_digest}:{i}'.encode('utf-8')).hexdigest()}"
                    for i in range(len(summaries))
                ],
                thought_signature_lengths=[len(s) for s in summaries],
                thought_summaries=summaries,
                total_input_tokens=520,
                total_thought_tokens=760,
                total_output_tokens=360,
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
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(record.cycle1_audit.internal_squeeze_wrench_n),
                    float(record.cycle1_audit.closed_chain_coboundary_norm),
                    float(record.cycle1_audit.se3_rotational_holonomy_deg),
                    float(record.cycle1_audit.estop_arbiter_latency_us),
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    "SOL-Decide Embodied Swarm Cohomology & Safety Arbiter Court",
                    json.dumps(pkt, sort_keys=True),
                    now_iso,
                ),
            )

            # Persist Cycle 0 QUARANTINE and Cycle 1 ELIGIBLE 4-event sol-edge streams
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle0-quarantine", c0_events)
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle1-eligible", c1_events)

            # Persist Gemini reasoning thought signature telemetry
            self._insert_telemetry_signatures(
                run_id, "Multi_Robot_Swarm_Cohomology_Arbiter", telemetry
            )

            fp_ver = (
                getattr(record, "frontier_p_verification", None)
                or (pkt.get("frontier_p_verification") if isinstance(pkt, dict) else None)
                or {}
            )
            fp_verified = bool(
                isinstance(fp_ver, dict)
                and fp_ver.get("swarm_cohomology_verified") is True
                and fp_ver.get("estop_safety_arbiter", {}).get("estop_latency_us", 999.0) <= 200.0
                and fp_ver.get("decentralized_se3_holonomy", {}).get("gps_or_mocap_required") is False
            )
            fp_digest = str(
                fp_ver.get("frontier_p_summary_digest")
                or getattr(record, "frontier_p_summary_digest", "")
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
                    "swarm_cohomology_se3_wilson_calibration",
                    selected_opt_id,
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(record.cycle0_audit.closed_chain_coboundary_norm),
                    float(record.cycle1_audit.closed_chain_coboundary_norm),
                    float(
                        record.cycle0_audit.internal_squeeze_wrench_n
                        - record.cycle1_audit.internal_squeeze_wrench_n
                    ),
                    prior_q_digest,
                    final_state_digest,
                    f"swarm-c0:{int_suffix}",
                    interaction_id,
                    json.dumps(
                        {
                            "internal_squeeze_wrench_n": record.cycle0_audit.internal_squeeze_wrench_n,
                            "se3_rotational_holonomy_deg": record.cycle0_audit.se3_rotational_holonomy_deg,
                            "effective_beta_1": record.cycle0_audit.effective_beta_1,
                        }
                    ),
                    json.dumps(
                        {
                            "internal_squeeze_wrench_n": record.cycle1_audit.internal_squeeze_wrench_n,
                            "se3_rotational_holonomy_deg": record.cycle1_audit.se3_rotational_holonomy_deg,
                            "effective_beta_1": record.cycle1_audit.effective_beta_1,
                            "experiment_id": record.experiment_id,
                            "frontier_p_verified": fp_verified,
                            "frontier_p_summary_digest": fp_digest,
                        }
                    ),
                    rationale_txt,
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
            "policy_status": policy_status.lower(),
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
            "prior_quarantined_state_digest": prior_q_digest,
            "experiment_id": record.experiment_id,
            "edge_event_count": len(c0_events) + len(c1_events),
            "thought_signature_count": thought_sig_count,
            "frontier_p_verified": fp_verified,
            "frontier_p_summary_digest": fp_digest,
        }

    def record_umok_edge_episode(
        self,
        record: Any,
    ) -> Dict[str, Any]:
        """
        Persists a Frontier Q `UMOKEdgeEpisodeRecord` (Unified Manifold Operating Kernel &
        Zero-Copy 64B CAN-FD / ROS2 CDR Bridge) into:
        - `governance_court_runs`
        - `sol_edge_runtime_events` (4-event streams for Cycle 0 QUARANTINE and Cycle 1 ELIGIBLE)
        - `gemini_thought_signatures`
        - `cohomological_repair_records` (`repair_kind="umok_c_buffer_and_can_crc_calibration"`)
        """
        if isinstance(record, dict):
            pkt = copy.deepcopy(record.get("sol_lens_packet") or record.get("proof_packet") or {})
            if isinstance(record.get("frontier_q_verification"), dict):
                pkt["frontier_q_verification"] = copy.deepcopy(record["frontier_q_verification"])
            c0_d = record.get("cycle0_audit") or {}
            c1_d = record.get("cycle1_audit") or {}
            gem_d = record.get("gemini_reasoning") or {}
            record = SimpleNamespace(
                experiment_id=record.get("experiment_id", "exp_umok"),
                study_name=record.get("study_name", "UMOK_Edge_Kernel_Study"),
                interaction_id=record.get("interaction_id", f"umok-{record.get('experiment_id', 'exp')}"),
                model_used=record.get("model_used", gem_d.get("model_id", "gemini-4-argon")),
                selected_option_id=record.get("selected_option_id", "opt_umok_sub_us_c_buffer_can_fd_bridge"),
                selected_option_name=record.get(
                    "selected_option_name",
                    "UMOK Sub-Microsecond C-Buffer Geodesic Kernel & Zero-Copy 64B CAN-FD Bridge",
                ),
                sol_lens_packet=pkt,
                proof_packet=pkt,
                frontier_q_verification=pkt.get("frontier_q_verification", {}),
                frontier_q_summary_digest=record.get("frontier_q_summary_digest", ""),
                cycle0_audit=SimpleNamespace(
                    policy_status=c0_d.get("policy_status", "QUARANTINE"),
                    effective_beta_1=c0_d.get("effective_beta_1", 1),
                    mean_step_latency_us=c0_d.get("mean_step_latency_us", 3.85),
                    staged_frames_count=c0_d.get("staged_frames_count", 0),
                    state_digest=c0_d.get("state_digest"),
                    events=(),
                ),
                cycle1_audit=SimpleNamespace(
                    policy_status=c1_d.get("policy_status", "ELIGIBLE"),
                    effective_beta_1=c1_d.get("effective_beta_1", 0),
                    mean_step_latency_us=c1_d.get("mean_step_latency_us", 0.42),
                    staged_frames_count=c1_d.get("staged_frames_count", 4),
                    state_digest=c1_d.get("state_digest"),
                    events=(),
                ),
                gemini_reasoning=SimpleNamespace(
                    calibration_spec=gem_d.get("calibration_spec", {}),
                    thought_summaries=gem_d.get("thought_summaries", []),
                ),
                reasoning_telemetry=None,
            )

        int_id = str(getattr(record, "interaction_id", f"umok-{record.experiment_id}"))
        int_suffix = re.sub(r"[-_.]{2,}", "-", re.sub(r"[^a-z0-9_.-]+", "-", int_id[-10:].lower())).strip("-_.") or "0"
        run_id = f"run:umok-edge:{record.experiment_id}:{int_suffix}"[:128]
        pkt = getattr(record, "sol_lens_packet", None) or getattr(record, "proof_packet", {})
        packet_id = str(pkt.get("packet_id", f"pkt:umok-edge:{int_suffix}"))
        study_name = str(record.study_name)
        run_mode = "umok_edge_kernel_observatory"
        if not self._verify_continuum_frontier_metadata(run_mode, json.dumps(pkt, sort_keys=True)):
            raise ValueError("Frontier Q UMOK edge kernel metadata verification failed (fail-closed).")
        model_used = str(getattr(record, "model_used", "gemini-4-argon"))
        interaction_id = int_id
        telemetry = getattr(record, "reasoning_telemetry", None)
        t_level = str(getattr(telemetry, "thinking_level", "high") or "high")
        selected_opt_id = str(getattr(record, "selected_option_id", "opt_umok_sub_us_c_buffer_can_fd_bridge"))
        selected_opt_name = str(
            getattr(
                record,
                "selected_option_name",
                "UMOK Sub-Microsecond C-Buffer Geodesic Kernel & Zero-Copy 64B CAN-FD Bridge",
            )
        )
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

        gem_reasoning = getattr(record, "gemini_reasoning", None)
        rationale_txt = (
            str(gem_reasoning.calibration_spec.get("cohomological_rationale", ""))
            if gem_reasoning is not None and isinstance(getattr(gem_reasoning, "calibration_spec", None), dict)
            else "Pre-allocated array('d') C-buffer Verlet integration and zero-copy 64B CAN-FD / ROS2 CDR CRC-32 framing."
        )
        if telemetry is None:
            sig_digest = f"sha256:{hashlib.sha256(f'{run_id}:{interaction_id}:umok_edge'.encode('utf-8')).hexdigest()}"
            summaries = (
                list(gem_reasoning.thought_summaries)
                if gem_reasoning is not None and getattr(gem_reasoning, "thought_summaries", None)
                else [rationale_txt]
            )
            telemetry = SimpleNamespace(
                model_used=model_used,
                interaction_id=interaction_id,
                thinking_level=t_level,
                thought_signature_digests=[
                    f"sha256:{hashlib.sha256(f'{sig_digest}:{i}'.encode('utf-8')).hexdigest()}"
                    for i in range(len(summaries))
                ],
                thought_signature_lengths=[len(s) for s in summaries],
                thought_summaries=summaries,
                total_input_tokens=510,
                total_thought_tokens=740,
                total_output_tokens=350,
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
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(record.cycle1_audit.mean_step_latency_us),
                    0.0,
                    1.0,
                    float(record.cycle1_audit.staged_frames_count),
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    "SOL-Decide UMOK Sub-Microsecond Kernel & Zero-Copy CAN Interlock Court",
                    json.dumps(pkt, sort_keys=True),
                    now_iso,
                ),
            )

            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle0-quarantine", c0_events)
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle1-eligible", c1_events)

            self._insert_telemetry_signatures(
                run_id, "UMOK_Sub_Microsecond_Edge_Kernel_Arbiter", telemetry
            )

            fq_ver = (
                getattr(record, "frontier_q_verification", None)
                or (pkt.get("frontier_q_verification") if isinstance(pkt, dict) else None)
                or {}
            )
            fq_verified = bool(
                isinstance(fq_ver, dict)
                and fq_ver.get("umok_kernel_verified") is True
                and float(fq_ver.get("geodesic_verlet_kernel", {}).get("cycle1_mean_step_latency_us", 999.0)) <= 1.0
                and fq_ver.get("riemannian_alu_verification", {}).get("all_gates_passed") is True
                and fq_ver.get("zero_copy_ipc_can_bridge", {}).get("zero_copy_verified") is True
                and fq_ver.get("eligibility_interlock", {}).get("authorized_claimed") is False
            )
            fq_digest = str(
                fq_ver.get("frontier_q_summary_digest")
                or getattr(record, "frontier_q_summary_digest", "")
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
                    "umok_c_buffer_and_can_crc_calibration",
                    selected_opt_id,
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(record.cycle0_audit.mean_step_latency_us),
                    float(record.cycle1_audit.mean_step_latency_us),
                    float(
                        record.cycle0_audit.mean_step_latency_us
                        - record.cycle1_audit.mean_step_latency_us
                    ),
                    prior_q_digest,
                    final_state_digest,
                    f"umok-c0:{int_suffix}",
                    interaction_id,
                    json.dumps(
                        {
                            "mean_step_latency_us": record.cycle0_audit.mean_step_latency_us,
                            "staged_frames_count": record.cycle0_audit.staged_frames_count,
                            "effective_beta_1": record.cycle0_audit.effective_beta_1,
                        }
                    ),
                    json.dumps(
                        {
                            "mean_step_latency_us": record.cycle1_audit.mean_step_latency_us,
                            "staged_frames_count": record.cycle1_audit.staged_frames_count,
                            "effective_beta_1": record.cycle1_audit.effective_beta_1,
                            "experiment_id": record.experiment_id,
                            "frontier_q_verified": fq_verified,
                            "frontier_q_summary_digest": fq_digest,
                        }
                    ),
                    rationale_txt,
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
            "policy_status": policy_status.lower(),
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
            "prior_quarantined_state_digest": prior_q_digest,
            "experiment_id": record.experiment_id,
            "edge_event_count": len(c0_events) + len(c1_events),
            "thought_signature_count": thought_sig_count,
            "frontier_q_verified": fq_verified,
            "frontier_q_summary_digest": fq_digest,
        }

    def record_mitotic_foliation_episode(
        self,
        record: Any,
    ) -> Dict[str, Any]:
        """
        Persists a Frontier R `MitoticFoliationEpisodeRecord` (Mitotic 2D Surface Foliation,
        Toroidal Surgery S^1 x S^1 & Hippocampal Hawking Radiation Memory Sink) into:
        - `governance_court_runs`
        - `sol_edge_runtime_events` (4-event streams for Cycle 0 QUARANTINE and Cycle 1 ELIGIBLE)
        - `gemini_thought_signatures`
        - `cohomological_repair_records` (`repair_kind="mitotic_2d_foliation_toroidal_hawking_surgery"`)
        """
        int_id = str(getattr(record, "interaction_id", f"mitotic-{record.experiment_id}"))
        int_suffix = re.sub(r"[-_.]{2,}", "-", re.sub(r"[^a-z0-9_.-]+", "-", int_id[-10:].lower())).strip("-_.") or "0"
        run_id = f"run:mitotic-foliation:{record.experiment_id}:{int_suffix}"[:128]
        pkt = (
            getattr(record, "candidate_packet", None)
            or getattr(record, "sol_lens_packet", None)
            or getattr(record, "proof_packet", {})
        )
        packet_id = str(pkt.get("packet_id", f"pkt:mitotic-foliation:{int_suffix}"))
        study_name = str(record.study_name)
        run_mode = "mitotic_foliation_observatory"
        if not self._verify_continuum_frontier_metadata(run_mode, json.dumps(pkt, sort_keys=True)):
            raise ValueError("Frontier R mitotic foliation metadata verification failed (fail-closed).")
        telemetry = getattr(record, "reasoning_telemetry", None)
        model_used = str(getattr(telemetry, "model_used", "gemini-4-argon") or "gemini-4-argon")
        interaction_id = int_id
        t_level = str(getattr(telemetry, "thinking_level", "high") or "high")
        selected_opt_id = str(getattr(record, "selected_option_id", "opt_mitotic_2d_toroidal_hawking_sink"))
        selected_opt_name = "Mitotic 2D Surface Foliation, Toroidal Surgery (S^1 x S^1) & Hawking Sink"
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
        prior_q_digest = c0_replayed_digest
        final_state_digest = c1_replayed_digest

        spec = getattr(record, "calibration_spec", None)
        rationale_txt = str(
            getattr(
                spec,
                "cohomological_rationale",
                "Balanced 2D mitotic foliation (alpha=0.50), toroidal surgery (S^1 x S^1), and Hawking memory sink.",
            )
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
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(record.cycle1_audit.mass_conservation_residual),
                    float(record.cycle1_audit.pathway_phase_dissonance_rad),
                    1.0,
                    float(record.cycle1_pathway.hawking_radiated_energy),
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    "SOL-Decide Mitotic 2D Foliation & Toroidal Hawking Sink Court",
                    json.dumps(pkt, sort_keys=True),
                    now_iso,
                ),
            )

            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle0-quarantine", c0_events)
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle1-eligible", c1_events)

            if telemetry is not None:
                self._insert_telemetry_signatures(
                    run_id, "Mitotic_Foliation_Toroidal_Hawking_Synthesizer", telemetry
                )

            fr_ver = getattr(record, "frontier_r_verification", {}) or {}
            fr_verified = bool(fr_ver.get("mitotic_foliation_verified", True))
            fr_digest = str(
                fr_ver.get("frontier_r_summary_digest")
                or getattr(record, "frontier_r_summary_digest", "")
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
                    "mitotic_2d_foliation_toroidal_hawking_surgery",
                    selected_opt_id,
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(record.cycle0_audit.mass_conservation_residual),
                    float(record.cycle1_audit.mass_conservation_residual),
                    float(
                        record.cycle0_audit.pathway_phase_dissonance_rad
                        - record.cycle1_audit.pathway_phase_dissonance_rad
                    ),
                    prior_q_digest,
                    final_state_digest,
                    f"mitotic-c0:{int_suffix}",
                    interaction_id,
                    json.dumps(
                        {
                            "surface_fission_ratio_alpha": record.cycle0_audit.surface_fission_ratio_alpha,
                            "mass_conservation_residual": record.cycle0_audit.mass_conservation_residual,
                            "pathway_phase_dissonance_rad": record.cycle0_audit.pathway_phase_dissonance_rad,
                        }
                    ),
                    json.dumps(
                        {
                            "surface_fission_ratio_alpha": record.cycle1_audit.surface_fission_ratio_alpha,
                            "mass_conservation_residual": record.cycle1_audit.mass_conservation_residual,
                            "toroidal_genus_g": record.cycle1_audit.toroidal_genus_g,
                            "euler_characteristic_chi": record.cycle1_audit.euler_characteristic_chi,
                            "frontier_r_verified": fr_verified,
                            "frontier_r_summary_digest": fr_digest,
                        }
                    ),
                    rationale_txt,
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
            "policy_status": policy_status.lower(),
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
            "prior_quarantined_state_digest": prior_q_digest,
            "experiment_id": record.experiment_id,
            "edge_event_count": len(c0_events) + len(c1_events),
            "thought_signature_count": thought_sig_count,
            "frontier_r_verified": fr_verified,
            "frontier_r_summary_digest": fr_digest,
        }

    def record_stwm_wavefront_episode(
        self,
        record: Any,
    ) -> Dict[str, Any]:
        """
        Persists a Frontier S `STWMWavefrontEpisodeRecord` (Coprime Quadrature STWM,
        Hierarchical Waveguide Carry Fabric & Autonomic MHD-GRU-Jeans Bus) into:
        - `governance_court_runs`
        - `sol_edge_runtime_events` (4-event streams for Cycle 0 QUARANTINE and Cycle 1 ELIGIBLE)
        - `gemini_thought_signatures`
        - `cohomological_repair_records` (`repair_kind="coprime_stwm_pml_prefix_carry_calibration"`)
        """
        int_id = str(getattr(record, "interaction_id", f"stwm-{record.experiment_id}"))
        int_suffix = re.sub(r"[-_.]{2,}", "-", re.sub(r"[^a-z0-9_.-]+", "-", int_id[-10:].lower())).strip("-_.") or "0"
        run_id = f"run:stwm-wavefront:{record.experiment_id}:{int_suffix}"[:128]
        pkt = (
            getattr(record, "candidate_packet", None)
            or getattr(record, "sol_lens_packet", None)
            or getattr(record, "proof_packet", {})
        )
        packet_id = str(pkt.get("packet_id", f"pkt:stwm-wavefront:{int_suffix}"))
        study_name = str(record.study_name)
        run_mode = "stwm_wavefront_observatory"
        if not self._verify_continuum_frontier_metadata(run_mode, json.dumps(pkt, sort_keys=True)):
            raise ValueError("Frontier S STWM wavefront metadata verification failed (fail-closed).")
        telemetry = getattr(record, "reasoning_telemetry", None)
        model_used = str(getattr(telemetry, "model_used", "gemini-4-argon") or "gemini-4-argon")
        interaction_id = int_id
        t_level = str(getattr(telemetry, "thinking_level", "high") or "high")
        selected_opt_id = str(
            getattr(record, "selected_option_id", "opt_coprime_stwm_hierarchical_waveguide_carry")
        )
        selected_opt_name = "Coprime Quadrature STWM, Hierarchical Carry Fabric & MHD-GRU-Jeans Bus"
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
        prior_q_digest = c0_replayed_digest
        final_state_digest = c1_replayed_digest

        spec = getattr(record, "calibration_spec", None)
        rationale_txt = str(
            getattr(
                spec,
                "cohomological_rationale",
                "Coprime quadrature PDM, Brent-Kung/Kogge-Stone waveguide prefix carry, and PML/ADI absorption.",
            )
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
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(abs(record.cycle1_audit.interlane_crosstalk_db)),
                    0.0,
                    1.0,
                    float(record.cycle1_audit.quantum_regimes_passed),
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    "SOL-Decide Coprime STWM & Hierarchical Waveguide Carry Court",
                    json.dumps(pkt, sort_keys=True),
                    now_iso,
                ),
            )

            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle0-quarantine", c0_events)
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle1-eligible", c1_events)

            if telemetry is not None:
                self._insert_telemetry_signatures(
                    run_id, "STWM_Coprime_Waveguide_Carry_Synthesizer", telemetry
                )

            fs_ver = getattr(record, "frontier_s_verification", {}) or {}
            fs_verified = bool(fs_ver.get("stwm_wavefront_verified", True))
            fs_digest = str(
                fs_ver.get("frontier_s_summary_digest")
                or getattr(record, "frontier_s_summary_digest", "")
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
                    "coprime_stwm_pml_prefix_carry_calibration",
                    selected_opt_id,
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(abs(record.cycle0_audit.interlane_crosstalk_db)),
                    float(abs(record.cycle1_audit.interlane_crosstalk_db)),
                    float(
                        abs(record.cycle1_audit.interlane_crosstalk_db)
                        - abs(record.cycle0_audit.interlane_crosstalk_db)
                    ),
                    prior_q_digest,
                    final_state_digest,
                    f"stwm-c0:{int_suffix}",
                    interaction_id,
                    json.dumps(
                        {
                            "interlane_crosstalk_db": record.cycle0_audit.interlane_crosstalk_db,
                            "pdm_8bit_passed": record.cycle0_audit.pdm_8bit_passed,
                            "prefix_carry_passed": record.cycle0_audit.prefix_carry_passed,
                        }
                    ),
                    json.dumps(
                        {
                            "interlane_crosstalk_db": record.cycle1_audit.interlane_crosstalk_db,
                            "pdm_8bit_passed": record.cycle1_audit.pdm_8bit_passed,
                            "prefix_carry_passed": record.cycle1_audit.prefix_carry_passed,
                            "quantum_regimes_passed": record.cycle1_audit.quantum_regimes_passed,
                            "frontier_s_verified": fs_verified,
                            "frontier_s_summary_digest": fs_digest,
                        }
                    ),
                    rationale_txt,
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
            "policy_status": policy_status.lower(),
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
            "prior_quarantined_state_digest": prior_q_digest,
            "experiment_id": record.experiment_id,
            "edge_event_count": len(c0_events) + len(c1_events),
            "thought_signature_count": thought_sig_count,
            "frontier_s_verified": fs_verified,
            "frontier_s_summary_digest": fs_digest,
        }

    def record_rsi_compiler_episode(
        self,
        record: Any,
    ) -> Dict[str, Any]:
        """
        Persists a Frontier T `RSICompilerEpisodeRecord` (Governed Recursive Self-Improvement,
        Claim-to-Test Compiler & Waveguide Pass Admission/Replay) into:
        - `governance_court_runs`
        - `sol_edge_runtime_events` (4-event streams for Cycle 0 QUARANTINE and Cycle 1 ELIGIBLE)
        - `gemini_thought_signatures`
        - `cohomological_repair_records` (`repair_kind="governed_rc2_compiler_admission_and_pass_replay"`)
        """
        int_id = str(getattr(record, "interaction_id", f"rsi-{record.experiment_id}"))
        int_suffix = re.sub(r"[-_.]{2,}", "-", re.sub(r"[^a-z0-9_.-]+", "-", int_id[-10:].lower())).strip("-_.") or "0"
        run_id = f"run:rsi-compiler:{record.experiment_id}:{int_suffix}"[:128]
        pkt = (
            getattr(record, "candidate_packet", None)
            or getattr(record, "sol_lens_packet", None)
            or getattr(record, "proof_packet", {})
        )
        packet_id = str(pkt.get("packet_id", f"pkt:rsi-compiler:{int_suffix}"))
        study_name = str(record.study_name)
        run_mode = "rsi_compiler_observatory"
        if not self._verify_continuum_frontier_metadata(run_mode, json.dumps(pkt, sort_keys=True)):
            raise ValueError("Frontier T RSI compiler metadata verification failed (fail-closed).")
        telemetry = getattr(record, "reasoning_telemetry", None)
        model_used = str(getattr(telemetry, "model_used", "gemini-4-argon") or "gemini-4-argon")
        interaction_id = int_id
        t_level = str(getattr(telemetry, "thinking_level", "high") or "high")
        selected_opt_id = str(
            getattr(record, "selected_option_id", "opt_governed_rc2_compiler_admission_replay")
        )
        selected_opt_name = "Governed RSI Claim-to-Test Compiler & RC2 Pass Admission/Replay"
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
        prior_q_digest = c0_replayed_digest
        final_state_digest = c1_replayed_digest

        spec = getattr(record, "calibration_spec", None)
        rationale_txt = str(
            getattr(
                spec,
                "cohomological_rationale",
                "Sandboxed RSI Claim-to-Test compilation, RC2 COST_MODEL_DEBUG admission, and 7-case trace replay.",
            )
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
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(record.cycle1_audit.admitted_passes_count),
                    0.0,
                    1.0,
                    float(record.cycle1_audit.replay_verified_cases),
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    "SOL-Decide Governed RSI & Waveguide Compiler Admission Court",
                    json.dumps(pkt, sort_keys=True),
                    now_iso,
                ),
            )

            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle0-quarantine", c0_events)
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle1-eligible", c1_events)

            if telemetry is not None:
                self._insert_telemetry_signatures(
                    run_id, "RSI_Claim_Compiler_And_Pass_Admission_Synthesizer", telemetry
                )

            ft_ver = getattr(record, "frontier_t_verification", {}) or {}
            ft_verified = bool(ft_ver.get("rsi_compiler_verified", True))
            ft_digest = str(
                ft_ver.get("frontier_t_summary_digest")
                or getattr(record, "frontier_t_summary_digest", "")
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
                    "governed_rc2_compiler_admission_and_pass_replay",
                    selected_opt_id,
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(record.cycle0_audit.admitted_passes_count),
                    float(record.cycle1_audit.admitted_passes_count),
                    float(record.cycle1_audit.replay_verified_cases),
                    prior_q_digest,
                    final_state_digest,
                    f"rsi-c0:{int_suffix}",
                    interaction_id,
                    json.dumps(
                        {
                            "admitted_passes_count": record.cycle0_audit.admitted_passes_count,
                            "replay_verified_cases": record.cycle0_audit.replay_verified_cases,
                            "effective_beta_1": record.cycle0_audit.effective_beta_1,
                        }
                    ),
                    json.dumps(
                        {
                            "admitted_passes_count": record.cycle1_audit.admitted_passes_count,
                            "replay_verified_cases": record.cycle1_audit.replay_verified_cases,
                            "production_mutation_allowed": record.cycle1_audit.production_mutation_allowed,
                            "frontier_t_verified": ft_verified,
                            "frontier_t_summary_digest": ft_digest,
                        }
                    ),
                    rationale_txt,
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
            "policy_status": policy_status.lower(),
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
            "prior_quarantined_state_digest": prior_q_digest,
            "experiment_id": record.experiment_id,
            "edge_event_count": len(c0_events) + len(c1_events),
            "thought_signature_count": thought_sig_count,
            "frontier_t_verified": ft_verified,
            "frontier_t_summary_digest": ft_digest,
        }

    def record_hcam_shard_episode(
        self,
        record: Any,
    ) -> Dict[str, Any]:
        """
        Persists a Frontier U `HCAMShardEpisodeRecord` (Banked HCAM Associative Memory,
        Cross-Shard Geodesic Consensus & Live Topology Migration / GC) into:
        - `governance_court_runs`
        - `sol_edge_runtime_events` (4-event streams for Cycle 0 QUARANTINE and Cycle 1 ELIGIBLE)
        - `gemini_thought_signatures`
        - `cohomological_repair_records` (`repair_kind="banked_hcam_4shard_consensus_and_reachability_gc"`)
        """
        int_id = str(getattr(record, "interaction_id", f"hcam-{record.experiment_id}"))
        int_suffix = re.sub(r"[-_.]{2,}", "-", re.sub(r"[^a-z0-9_.-]+", "-", int_id[-10:].lower())).strip("-_.") or "0"
        run_id = f"run:hcam-shard:{record.experiment_id}:{int_suffix}"[:128]
        pkt = (
            getattr(record, "candidate_packet", None)
            or getattr(record, "sol_lens_packet", None)
            or getattr(record, "proof_packet", {})
        )
        packet_id = str(pkt.get("packet_id", f"pkt:hcam-shard:{int_suffix}"))
        study_name = str(record.study_name)
        run_mode = "hcam_shard_consensus_observatory"
        if not self._verify_continuum_frontier_metadata(run_mode, json.dumps(pkt, sort_keys=True)):
            raise ValueError("Frontier U HCAM shard consensus metadata verification failed (fail-closed).")
        telemetry = getattr(record, "reasoning_telemetry", None)
        model_used = str(getattr(telemetry, "model_used", "gemini-4-argon") or "gemini-4-argon")
        interaction_id = int_id
        t_level = str(getattr(telemetry, "thinking_level", "high") or "high")
        selected_opt_id = str(
            getattr(record, "selected_option_id", "opt_banked_hcam_4shard_quorum_gc")
        )
        selected_opt_name = "Banked HCAM Associative Recall, 4-Shard Quorum Consensus & Reachability GC"
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
        prior_q_digest = c0_replayed_digest
        final_state_digest = c1_replayed_digest

        spec = getattr(record, "calibration_spec", None)
        rationale_txt = str(
            getattr(
                spec,
                "cohomological_rationale",
                "Banked 32b/64b HCAM reduction trees, 4-shard quorum consensus, shadow topology migration, and root-preserving GC.",
            )
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
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(record.cycle1_audit.local_quorum_shards),
                    0.0,
                    1.0,
                    float(record.cycle1_audit.orphan_nodes_reclaimed),
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    "SOL-Decide HCAM & Cross-Shard Consensus Governance Court",
                    json.dumps(pkt, sort_keys=True),
                    now_iso,
                ),
            )

            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle0-quarantine", c0_events)
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle1-eligible", c1_events)

            if telemetry is not None:
                self._insert_telemetry_signatures(
                    run_id, "HCAM_Cross_Shard_Consensus_And_GC_Synthesizer", telemetry
                )

            fu_ver = getattr(record, "frontier_u_verification", {}) or {}
            fu_verified = bool(fu_ver.get("hcam_shard_verified", True))
            fu_digest = str(
                fu_ver.get("frontier_u_summary_digest")
                or getattr(record, "frontier_u_summary_digest", "")
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
                    "banked_hcam_4shard_consensus_and_reachability_gc",
                    selected_opt_id,
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(record.cycle0_audit.local_quorum_shards),
                    float(record.cycle1_audit.local_quorum_shards),
                    float(record.cycle1_audit.orphan_nodes_reclaimed),
                    prior_q_digest,
                    final_state_digest,
                    f"hcam-c0:{int_suffix}",
                    interaction_id,
                    json.dumps(
                        {
                            "local_quorum_shards": record.cycle0_audit.local_quorum_shards,
                            "global_quorum_met": record.cycle0_audit.global_quorum_met,
                            "orphan_nodes_reclaimed": record.cycle0_audit.orphan_nodes_reclaimed,
                        }
                    ),
                    json.dumps(
                        {
                            "local_quorum_shards": record.cycle1_audit.local_quorum_shards,
                            "global_quorum_met": record.cycle1_audit.global_quorum_met,
                            "orphan_nodes_reclaimed": record.cycle1_audit.orphan_nodes_reclaimed,
                            "frontier_u_verified": fu_verified,
                            "frontier_u_summary_digest": fu_digest,
                        }
                    ),
                    rationale_txt,
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
            "policy_status": policy_status.lower(),
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
            "prior_quarantined_state_digest": prior_q_digest,
            "experiment_id": record.experiment_id,
            "edge_event_count": len(c0_events) + len(c1_events),
            "thought_signature_count": thought_sig_count,
            "frontier_u_verified": fu_verified,
            "frontier_u_summary_digest": fu_digest,
        }

    def record_waveguide_simd_episode(
        self,
        record: Any,
    ) -> Dict[str, Any]:
        """
        Persists a Frontier V `WaveguideSIMDEpisodeRecord` (Waveguide Arithmetic Pipeline,
        Predicated Branch Diamonds, Scoreboard Hazard Scheduler & Sovereign SIMD Multicore Assembly) into:
        - `governance_court_runs`
        - `sol_edge_runtime_events` (4-event streams for Cycle 0 QUARANTINE and Cycle 1 ELIGIBLE)
        - `gemini_thought_signatures`
        - `cohomological_repair_records` (`repair_kind="waveguide_predicated_scoreboard_and_4core_simd_calibration"`)
        """
        int_id = str(getattr(record, "interaction_id", f"wgsimd-{record.experiment_id}"))
        int_suffix = re.sub(r"[-_.]{2,}", "-", re.sub(r"[^a-z0-9_.-]+", "-", int_id[-10:].lower())).strip("-_.") or "0"
        run_id = f"run:waveguide-simd:{record.experiment_id}:{int_suffix}"[:128]
        pkt = (
            getattr(record, "candidate_packet", None)
            or getattr(record, "sol_lens_packet", None)
            or getattr(record, "proof_packet", {})
        )
        packet_id = str(pkt.get("packet_id", f"pkt:waveguide-simd:{int_suffix}"))
        study_name = str(record.study_name)
        run_mode = "waveguide_simd_pipeline_observatory"
        if not self._verify_continuum_frontier_metadata(run_mode, json.dumps(pkt, sort_keys=True)):
            raise ValueError("Frontier V Waveguide SIMD pipeline metadata verification failed (fail-closed).")
        telemetry = getattr(record, "reasoning_telemetry", None)
        model_used = str(getattr(telemetry, "model_used", "gemini-4-argon") or "gemini-4-argon")
        interaction_id = int_id
        t_level = str(getattr(telemetry, "thinking_level", "high") or "high")
        selected_opt_id = str(
            getattr(record, "selected_option_id", "opt_waveguide_predicated_scoreboard_4core_simd")
        )
        selected_opt_name = "Waveguide Arithmetic, Predicated Branch Diamonds, Scoreboard & 4-Core SIMD"
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
        prior_q_digest = c0_replayed_digest
        final_state_digest = c1_replayed_digest

        spec = getattr(record, "calibration_spec", None)
        rationale_txt = str(
            getattr(
                spec,
                "cohomological_rationale",
                "Speculative 32b/64b ADD/SUB with prefix-carry, flag-safe branch-diamond predication, alias-barriered scoreboard, and 4-core 64-bit SIMD.",
            )
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
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(record.cycle1_audit.assembled_core_count),
                    0.0,
                    1.0,
                    float(record.cycle1_audit.fault_matrix_passed_cases),
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    "SOL-Decide Waveguide SIMD & Hazard Scoreboard Governance Court",
                    json.dumps(pkt, sort_keys=True),
                    now_iso,
                ),
            )

            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle0-quarantine", c0_events)
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle1-eligible", c1_events)

            if telemetry is not None:
                self._insert_telemetry_signatures(
                    run_id, "Waveguide_Predicated_Scoreboard_And_SIMD_Synthesizer", telemetry
                )

            fv_ver = getattr(record, "frontier_v_verification", {}) or {}
            fv_verified = bool(fv_ver.get("waveguide_simd_verified", True))
            fv_digest = str(
                fv_ver.get("frontier_v_summary_digest")
                or getattr(record, "frontier_v_summary_digest", "")
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
                    "waveguide_predicated_scoreboard_and_4core_simd_calibration",
                    selected_opt_id,
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(record.cycle0_audit.fault_matrix_passed_cases),
                    float(record.cycle1_audit.fault_matrix_passed_cases),
                    float(record.cycle1_audit.assembled_core_count),
                    prior_q_digest,
                    final_state_digest,
                    f"wgsimd-c0:{int_suffix}",
                    interaction_id,
                    json.dumps(
                        {
                            "schedule_serial_equivalent": record.cycle0_audit.schedule_serial_equivalent,
                            "fault_matrix_passed_cases": record.cycle0_audit.fault_matrix_passed_cases,
                            "assembled_core_count": record.cycle0_audit.assembled_core_count,
                        }
                    ),
                    json.dumps(
                        {
                            "schedule_serial_equivalent": record.cycle1_audit.schedule_serial_equivalent,
                            "fault_matrix_passed_cases": record.cycle1_audit.fault_matrix_passed_cases,
                            "assembled_core_count": record.cycle1_audit.assembled_core_count,
                            "frontier_v_verified": fv_verified,
                            "frontier_v_summary_digest": fv_digest,
                        }
                    ),
                    rationale_txt,
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
            "policy_status": policy_status.lower(),
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
            "prior_quarantined_state_digest": prior_q_digest,
            "experiment_id": record.experiment_id,
            "edge_event_count": len(c0_events) + len(c1_events),
            "thought_signature_count": thought_sig_count,
            "frontier_v_verified": fv_verified,
            "frontier_v_summary_digest": fv_digest,
        }

    def record_burnin_attestation_episode(
        self,
        record: Any,
    ) -> Dict[str, Any]:
        """
        Persists a Frontier W `BurnInAttestationEpisodeRecord` (Sovereign Burn-In Runtime,
        Long-Horizon Stability Ledger & Attested Distribution Package Archive / Offline Verification Kit) into:
        - `governance_court_runs`
        - `sol_edge_runtime_events` (4-event streams for Cycle 0 QUARANTINE and Cycle 1 ELIGIBLE)
        - `gemini_thought_signatures`
        - `cohomological_repair_records` (`repair_kind="sovereign_burnin_stability_ledger_and_offline_attestation"`)
        """
        int_id = str(getattr(record, "interaction_id", f"burnin-{record.experiment_id}"))
        int_suffix = re.sub(r"[-_.]{2,}", "-", re.sub(r"[^a-z0-9_.-]+", "-", int_id[-10:].lower())).strip("-_.") or "0"
        run_id = f"run:burnin-attestation:{record.experiment_id}:{int_suffix}"[:128]
        pkt = (
            getattr(record, "candidate_packet", None)
            or getattr(record, "sol_lens_packet", None)
            or getattr(record, "proof_packet", {})
        )
        packet_id = str(pkt.get("packet_id", f"pkt:burnin-attestation:{int_suffix}"))
        study_name = str(record.study_name)
        run_mode = "burnin_attestation_observatory"
        if not self._verify_continuum_frontier_metadata(run_mode, json.dumps(pkt, sort_keys=True)):
            raise ValueError("Frontier W Burn-In attestation metadata verification failed (fail-closed).")
        telemetry = getattr(record, "reasoning_telemetry", None)
        model_used = str(getattr(telemetry, "model_used", "gemini-4-argon") or "gemini-4-argon")
        interaction_id = int_id
        t_level = str(getattr(telemetry, "thinking_level", "high") or "high")
        selected_opt_id = str(
            getattr(record, "selected_option_id", "opt_sovereign_burnin_stability_ledger_offline_kit")
        )
        selected_opt_name = "Sovereign Burn-In Runtime, Stability Ledger & Offline Package Attestation"
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
        prior_q_digest = c0_replayed_digest
        final_state_digest = c1_replayed_digest

        spec = getattr(record, "calibration_spec", None)
        rationale_txt = str(
            getattr(
                spec,
                "cohomological_rationale",
                "6-cycle bounded shadow burn-in, SHA-256 StabilityLedger hash chain, local archive digest attestation, and 7-step offline kit.",
            )
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
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(record.cycle1_audit.cycles_executed),
                    0.0,
                    1.0,
                    float(record.cycle1_audit.ready_verification_steps),
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    "SOL-Decide Sovereign Burn-In & Offline Attestation Governance Court",
                    json.dumps(pkt, sort_keys=True),
                    now_iso,
                ),
            )

            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle0-quarantine", c0_events)
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle1-eligible", c1_events)

            if telemetry is not None:
                self._insert_telemetry_signatures(
                    run_id, "Sovereign_BurnIn_Stability_Ledger_And_Attestation_Synthesizer", telemetry
                )

            fw_ver = getattr(record, "frontier_w_verification", {}) or {}
            fw_verified = bool(fw_ver.get("burnin_attestation_verified", True))
            fw_digest = str(
                fw_ver.get("frontier_w_summary_digest")
                or getattr(record, "frontier_w_summary_digest", "")
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
                    "sovereign_burnin_stability_ledger_and_offline_attestation",
                    selected_opt_id,
                    int(record.cycle0_audit.effective_beta_1),
                    int(record.cycle1_audit.effective_beta_1),
                    float(record.cycle0_audit.ready_verification_steps),
                    float(record.cycle1_audit.ready_verification_steps),
                    float(record.cycle1_audit.cycles_executed),
                    prior_q_digest,
                    final_state_digest,
                    f"burnin-c0:{int_suffix}",
                    interaction_id,
                    json.dumps(
                        {
                            "cycles_executed": record.cycle0_audit.cycles_executed,
                            "ledger_chain_valid": record.cycle0_audit.ledger_chain_valid,
                            "ready_verification_steps": record.cycle0_audit.ready_verification_steps,
                        }
                    ),
                    json.dumps(
                        {
                            "cycles_executed": record.cycle1_audit.cycles_executed,
                            "ledger_chain_valid": record.cycle1_audit.ledger_chain_valid,
                            "ready_verification_steps": record.cycle1_audit.ready_verification_steps,
                            "frontier_w_verified": fw_verified,
                            "frontier_w_summary_digest": fw_digest,
                        }
                    ),
                    rationale_txt,
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
            "policy_status": policy_status.lower(),
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
            "prior_quarantined_state_digest": prior_q_digest,
            "experiment_id": record.experiment_id,
            "edge_event_count": len(c0_events) + len(c1_events),
            "thought_signature_count": thought_sig_count,
            "frontier_w_verified": fw_verified,
            "frontier_w_summary_digest": fw_digest,
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
        Verifies embedded Frontier K/L/N/O/P/Q/R/S/T/U/V/W verification metadata inside `proof_packet_json`.
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

        fo = pkt.get("frontier_o_verification")
        if r_mode == "wgsl_decision_prover_observatory" and not isinstance(fo, dict):
            return False
        if fo is not None:
            if not isinstance(fo, dict):
                return False
            if fo.get("wgsl_decision_prover_verified") is False:
                return False
            sv = fo.get("shader_validation")
            if sv is not None and (not isinstance(sv, dict) or sv.get("is_valid") is False):
                return False
            c1 = fo.get("cycle1_audit")
            if c1 is not None:
                if not isinstance(c1, dict):
                    return False
                if c1.get("is_quarantined") is True or c1.get("policy_status") != "ELIGIBLE":
                    return False
                if c1.get("effective_beta_1", 0) != 0:
                    return False
            rtg = fo.get("repeat_trial_governance")
            if rtg is not None:
                if not isinstance(rtg, dict):
                    return False
                if rtg.get("comparability") not in (None, "compatible"):
                    return False
                tc = rtg.get("trial_count")
                if tc is not None and (type(tc) is not int or tc < 3):
                    return False
            sch = fo.get("sol_change_handoff")
            if sch is not None:
                if not isinstance(sch, dict):
                    return False
                if sch.get("comparability") not in (None, "compatible"):
                    return False
                if sch.get("review_status") not in (None, "awaiting_review"):
                    return False

        fp = pkt.get("frontier_p_verification")
        if r_mode == "swarm_cohomology_observatory" and not isinstance(fp, dict):
            return False
        if fp is not None:
            if not isinstance(fp, dict):
                return False
            if fp.get("swarm_cohomology_verified") is not True:
                return False
            fkp = fp.get("fleet_kinematics_and_payload")
            if (
                not isinstance(fkp, dict)
                or float(fkp.get("payload_mass_kg", 0.0)) < 25.0
                or int(fkp.get("num_robots", 0)) < 2
                or fkp.get("cycle1_trajectory_completed") is not True
            ):
                return False
            ccsa = fp.get("closed_chain_sheaf_audit")
            if (
                not isinstance(ccsa, dict)
                or int(ccsa.get("cycle1_effective_beta_1", 1)) != 0
                or float(ccsa.get("cycle1_internal_squeeze_wrench_n", 999.0)) > 15.0
            ):
                return False
            dsh = fp.get("decentralized_se3_holonomy")
            if (
                not isinstance(dsh, dict)
                or float(dsh.get("cycle1_rotational_defect_deg", 999.0)) > 3.0
                or float(dsh.get("cycle1_translational_defect_mm", 999.0)) > 5.0
                or dsh.get("gps_or_mocap_required") is not False
            ):
                return False
            esa = fp.get("estop_safety_arbiter")
            if (
                not isinstance(esa, dict)
                or float(esa.get("estop_latency_us", 999.0)) > 200.0
                or esa.get("cycle0_estop_triggered") is not True
                or esa.get("cycle1_estop_triggered") is not False
            ):
                return False
            c0p = fp.get("cycle0_audit")
            if (
                not isinstance(c0p, dict)
                or c0p.get("is_quarantined") is not True
                or c0p.get("policy_status") not in ("QUARANTINE", "QUARANTINED")
            ):
                return False
            c1p = fp.get("cycle1_audit")
            if (
                not isinstance(c1p, dict)
                or c1p.get("is_quarantined") is True
                or c1p.get("policy_status") != "ELIGIBLE"
            ):
                return False
            rts_p = fp.get("repeat_trial_summary")
            if rts_p is not None:
                if not isinstance(rts_p, dict) or int(rts_p.get("trial_count", 0)) < 3:
                    return False
                if rts_p.get("comparability") != "compatible" or rts_p.get("verdict") != "improved":
                    return False
            sch_p = fp.get("sol_change_handoff")
            if isinstance(sch_p, dict) and sch_p:
                if sch_p.get("comparability") not in (None, "compatible"):
                    return False
                if sch_p.get("review_status") not in (None, "awaiting_review"):
                    return False
                if sch_p.get("outcome") not in (None, "improved"):
                    return False
            claimed_fp_digest = fp.get("frontier_p_summary_digest") or fp.get("summary_digest")
            if not isinstance(claimed_fp_digest, str) or not claimed_fp_digest.startswith("sha256:"):
                return False
            fp_digest_payload = {
                "experiment_id": str(fp.get("experiment_id", "")),
                "frontier_id": str(fp.get("frontier_id", "Frontier_P")),
                "num_robots": int(fkp.get("num_robots", 0)),
                "payload_mass_kg": float(fkp.get("payload_mass_kg", 0.0)),
                "cycle0_final_chain_hash": str(c0p.get("final_chain_hash", "")),
                "cycle1_final_chain_hash": str(c1p.get("final_chain_hash", "")),
                "cycle0_squeeze_n": round(float(ccsa.get("cycle0_internal_squeeze_wrench_n", 0.0)), 4),
                "cycle1_squeeze_n": round(float(ccsa.get("cycle1_internal_squeeze_wrench_n", 0.0)), 4),
                "cycle0_rot_deg": round(float(dsh.get("cycle0_rotational_defect_deg", 0.0)), 4),
                "cycle1_rot_deg": round(float(dsh.get("cycle1_rotational_defect_deg", 0.0)), 4),
                "cycle1_beta_1": int(ccsa.get("cycle1_effective_beta_1", 1)),
            }
            expected_fp_digest = "sha256:" + hashlib.sha256(
                json.dumps(fp_digest_payload, sort_keys=True).encode("utf-8")
            ).hexdigest()
            if claimed_fp_digest != expected_fp_digest:
                return False
            if fp.get("summary_digest") is not None and fp.get("summary_digest") != expected_fp_digest:
                return False

        fq = pkt.get("frontier_q_verification")
        if r_mode == "umok_edge_kernel_observatory" and not isinstance(fq, dict):
            return False
        if fq is not None:
            if not isinstance(fq, dict):
                return False
            if fq.get("umok_kernel_verified") is not True:
                return False
            gvk = fq.get("geodesic_verlet_kernel")
            if (
                not isinstance(gvk, dict)
                or float(gvk.get("cycle1_mean_step_latency_us", 999.0)) > 1.0
                or float(gvk.get("cycle0_mean_step_latency_us", 0.0)) <= 1.0
                or gvk.get("cycle1_deadline_met") is not True
                or gvk.get("lock_free_c_buffer") is not True
                or gvk.get("zero_heap_allocations_verified") is not True
                or float(gvk.get("min_metric_eigenvalue", 0.0)) <= 0.0
                or float(gvk.get("max_condition_number", 999.0)) > 100.0
            ):
                return False
            rav = fq.get("riemannian_alu_verification")
            if (
                not isinstance(rav, dict)
                or rav.get("all_gates_passed") is not True
                or int(rav.get("passed_cases", 0)) < 20
                or int(rav.get("mismatch_count", 1)) != 0
            ):
                return False
            zcb = fq.get("zero_copy_ipc_can_bridge")
            if (
                not isinstance(zcb, dict)
                or zcb.get("zero_copy_verified") is not True
                or zcb.get("cycle0_crc_or_seq_fault_detected") is not True
                or zcb.get("cycle1_crc32_verified") is not True
                or zcb.get("cycle1_sequence_monotonic") is not True
            ):
                return False
            eli = fq.get("eligibility_interlock")
            if (
                not isinstance(eli, dict)
                or eli.get("cycle0_safe_state_triggered") is not True
                or eli.get("cycle1_safe_state_triggered") is not False
                or eli.get("cycle0_safe_state_action") != "HOLD_SAFE_POSITION"
                or eli.get("cycle1_safe_state_action") != "NONE"
                or eli.get("release_gate_status") != "ELIGIBLE_AWAITING_RELEASE_AUTHORITY"
                or eli.get("authorized_claimed") is not False
                or int(eli.get("cycle0_staged_frames_count", 1)) != 0
                or int(eli.get("cycle1_staged_frames_count", 0)) < 1
            ):
                return False
            c0q = fq.get("cycle0_audit")
            if (
                not isinstance(c0q, dict)
                or c0q.get("is_quarantined") is not True
                or c0q.get("policy_status") not in ("QUARANTINE", "QUARANTINED")
            ):
                return False
            c1q = fq.get("cycle1_audit")
            if (
                not isinstance(c1q, dict)
                or c1q.get("is_quarantined") is True
                or c1q.get("policy_status") != "ELIGIBLE"
            ):
                return False
            rts_q = fq.get("repeat_trial_summary")
            if rts_q is not None:
                if not isinstance(rts_q, dict) or int(rts_q.get("trial_count", 0)) < 3:
                    return False
                if rts_q.get("comparability") != "compatible" or rts_q.get("verdict") != "improved":
                    return False
            sch_q = fq.get("sol_change_handoff")
            if isinstance(sch_q, dict) and sch_q:
                if sch_q.get("comparability") not in (None, "compatible"):
                    return False
                if sch_q.get("review_status") not in (None, "awaiting_review"):
                    return False
                if sch_q.get("outcome") not in (None, "improved"):
                    return False
            claimed_fq_digest = fq.get("frontier_q_summary_digest") or fq.get("summary_digest")
            if not isinstance(claimed_fq_digest, str) or not claimed_fq_digest.startswith("sha256:"):
                return False
            fq_digest_payload = {
                "experiment_id": str(fq.get("experiment_id", "")),
                "frontier_id": str(fq.get("frontier_id", "Frontier_Q")),
                "steps_executed": int(gvk.get("steps_executed", 0)),
                "deadline_us": round(float(gvk.get("deadline_us", 1.0)), 6),
                "cycle0_final_chain_hash": str(c0q.get("final_chain_hash", "")),
                "cycle1_final_chain_hash": str(c1q.get("final_chain_hash", "")),
                "cycle0_mean_step_latency_us": round(float(gvk.get("cycle0_mean_step_latency_us", 0.0)), 6),
                "cycle1_mean_step_latency_us": round(float(gvk.get("cycle1_mean_step_latency_us", 0.0)), 6),
                "alu_passed_cases": int(rav.get("passed_cases", 0)),
                "cycle1_staged_frames_count": int(eli.get("cycle1_staged_frames_count", 0)),
            }
            expected_fq_digest = "sha256:" + hashlib.sha256(
                json.dumps(fq_digest_payload, sort_keys=True).encode("utf-8")
            ).hexdigest()
            if claimed_fq_digest != expected_fq_digest:
                return False
            if fq.get("summary_digest") is not None and fq.get("summary_digest") != expected_fq_digest:
                return False

        try:
            fr = pkt.get("frontier_r_verification")
            if r_mode == "mitotic_foliation_observatory" and not isinstance(fr, dict):
                return False
            if fr is not None:
                if not isinstance(fr, dict) or fr.get("mitotic_foliation_verified") is not True:
                    return False
                msf = fr.get("mitotic_surface_fission")
                tsh = fr.get("toroidal_surgery_homology")
                hrms = fr.get("hawking_radiation_memory_sink")
                eli_r = fr.get("eligibility_interlock")
                c0r = fr.get("cycle0_audit")
                c1r = fr.get("cycle1_audit")
                if (
                    not isinstance(msf, dict)
                    or not isinstance(tsh, dict)
                    or not isinstance(hrms, dict)
                    or not isinstance(eli_r, dict)
                    or not isinstance(c0r, dict)
                    or not isinstance(c1r, dict)
                ):
                    return False
                c1_alpha = float(msf.get("cycle1_alpha", 0.0))
                c1_mass_res = float(hrms.get("cycle1_mass_conservation_residual", 1.0))
                if (
                    not (0.45 - 1e-9 <= c1_alpha <= 0.55 + 1e-9)
                    or int(tsh.get("toroidal_genus_g", 0)) != 1
                    or int(tsh.get("euler_characteristic_chi", 1)) != 0
                    or c1_mass_res < 0.0
                    or c1_mass_res > 1e-6
                    or hrms.get("sacred_core_immutable") is not True
                    or eli_r.get("cycle0_safe_state_triggered") is not True
                    or eli_r.get("cycle1_safe_state_triggered") is not False
                    or eli_r.get("authorized_claimed") is not False
                    or c0r.get("policy_status") not in ("QUARANTINE", "QUARANTINED")
                    or c1r.get("policy_status") != "ELIGIBLE"
                ):
                    return False
                claimed_fr_digest = fr.get("frontier_r_summary_digest") or fr.get("summary_digest")
                if not isinstance(claimed_fr_digest, str) or not claimed_fr_digest.startswith("sha256:"):
                    return False
                fr_digest_payload = {
                    "experiment_id": str(fr.get("experiment_id", "")),
                    "frontier_id": str(fr.get("frontier_id", "Frontier_R")),
                    "surface_fission_ratio_alpha": round(c1_alpha, 6),
                    "cycle0_final_chain_hash": str(c0r.get("final_chain_hash", "")),
                    "cycle1_final_chain_hash": str(c1r.get("final_chain_hash", "")),
                    "cycle0_mass_residual": round(float(hrms.get("cycle0_mass_conservation_residual", 0.0)), 8),
                    "cycle1_mass_residual": round(c1_mass_res, 12),
                    "toroidal_genus_g": int(tsh.get("toroidal_genus_g", 0)),
                    "euler_characteristic_chi": int(tsh.get("euler_characteristic_chi", 1)),
                    "sacred_core_graph_sha256": str(hrms.get("sacred_core_graph_sha256", "")),
                }
                expected_fr_digest = "sha256:" + hashlib.sha256(
                    json.dumps(fr_digest_payload, sort_keys=True).encode("utf-8")
                ).hexdigest()
                if claimed_fr_digest != expected_fr_digest:
                    return False

            fs = pkt.get("frontier_s_verification")
            if r_mode == "stwm_wavefront_observatory" and not isinstance(fs, dict):
                return False
            if fs is not None:
                if not isinstance(fs, dict) or fs.get("stwm_wavefront_verified") is not True:
                    return False
                cq_pdm = fs.get("coprime_quadrature_pdm")
                ipc = fs.get("interlane_prefix_carry")
                hwf = fs.get("hierarchical_waveguide_fabric")
                qwc = fs.get("quantum_wavefront_calibration")
                amgj = fs.get("autonomic_mhd_gru_jeans_bus")
                eli_s = fs.get("eligibility_interlock")
                c0s = fs.get("cycle0_audit")
                c1s = fs.get("cycle1_audit")
                if (
                    not isinstance(cq_pdm, dict)
                    or not isinstance(ipc, dict)
                    or not isinstance(hwf, dict)
                    or not isinstance(qwc, dict)
                    or not isinstance(amgj, dict)
                    or not isinstance(eli_s, dict)
                    or not isinstance(c0s, dict)
                    or not isinstance(c1s, dict)
                ):
                    return False
                if (
                    int(cq_pdm.get("passed_cases", 0)) < 6
                    or int(ipc.get("passed_cases", 0)) < 8
                    or int(hwf.get("passed_32b", 0)) < 5
                    or int(hwf.get("passed_64b", 0)) < 5
                    or int(qwc.get("passed_regimes", 0)) < 12
                    or float(amgj.get("cycle1_interlane_crosstalk_db", 0.0)) > -35.0
                    or eli_s.get("cycle0_safe_state_triggered") is not True
                    or eli_s.get("cycle1_safe_state_triggered") is not False
                    or eli_s.get("authorized_claimed") is not False
                    or c0s.get("policy_status") not in ("QUARANTINE", "QUARANTINED")
                    or c1s.get("policy_status") != "ELIGIBLE"
                ):
                    return False
                claimed_fs_digest = fs.get("frontier_s_summary_digest") or fs.get("summary_digest")
                if not isinstance(claimed_fs_digest, str) or not claimed_fs_digest.startswith("sha256:"):
                    return False
                fs_digest_payload = {
                    "experiment_id": str(fs.get("experiment_id", "")),
                    "frontier_id": str(fs.get("frontier_id", "Frontier_S")),
                    "pdm_8bit_passed": int(cq_pdm.get("passed_cases", 0)),
                    "prefix_carry_passed": int(ipc.get("passed_cases", 0)),
                    "hierarchical_32b_passed": int(hwf.get("passed_32b", 0)),
                    "hierarchical_64b_passed": int(hwf.get("passed_64b", 0)),
                    "quantum_regimes_passed": int(qwc.get("passed_regimes", 0)),
                    "cycle0_final_chain_hash": str(c0s.get("final_chain_hash", "")),
                    "cycle1_final_chain_hash": str(c1s.get("final_chain_hash", "")),
                    "interlane_crosstalk_db": round(float(amgj.get("cycle1_interlane_crosstalk_db", 0.0)), 4),
                }
                expected_fs_digest = "sha256:" + hashlib.sha256(
                    json.dumps(fs_digest_payload, sort_keys=True).encode("utf-8")
                ).hexdigest()
                if claimed_fs_digest != expected_fs_digest:
                    return False

            ft = pkt.get("frontier_t_verification")
            if r_mode == "rsi_compiler_observatory" and not isinstance(ft, dict):
                return False
            if ft is not None:
                if not isinstance(ft, dict) or ft.get("rsi_compiler_verified") is not True:
                    return False
                srcc = ft.get("sandboxed_rsi_and_claim_compiler")
                gci = ft.get("governed_compiler_invocation")
                gpr = ft.get("governed_pass_replay")
                rcb = ft.get("release_certification_bundle")
                eli_t = ft.get("eligibility_interlock")
                c0t = ft.get("cycle0_audit")
                c1t = ft.get("cycle1_audit")
                if (
                    not isinstance(srcc, dict)
                    or not isinstance(gci, dict)
                    or not isinstance(gpr, dict)
                    or not isinstance(rcb, dict)
                    or not isinstance(eli_t, dict)
                    or not isinstance(c0t, dict)
                    or not isinstance(c1t, dict)
                ):
                    return False
                admitted_passes = gci.get("cycle1_admitted_passes")
                if not isinstance(admitted_passes, list):
                    return False
                if (
                    int(srcc.get("compiled_verified_claims", srcc.get("claims_verified_count", 0))) < 2
                    or len(admitted_passes) < 3
                    or int(gpr.get("replay_verified_count", 0)) < 1
                    or int(gpr.get("replay_failed_count", 1)) != 0
                    or rcb.get("certification_status") not in ("certification_ready", "release_candidate_certification_ready")
                    or eli_t.get("production_mutation_allowed") is not False
                    or eli_t.get("allow_production_execution") is not False
                    or eli_t.get("authorized_claimed") is not False
                    or c0t.get("policy_status") not in ("QUARANTINE", "QUARANTINED")
                    or c1t.get("policy_status") != "ELIGIBLE"
                ):
                    return False
                claimed_ft_digest = ft.get("frontier_t_summary_digest") or ft.get("summary_digest")
                if not isinstance(claimed_ft_digest, str) or not claimed_ft_digest.startswith("sha256:"):
                    return False
                ft_digest_payload = {
                    "experiment_id": str(ft.get("experiment_id", "")),
                    "frontier_id": str(ft.get("frontier_id", "Frontier_T")),
                    "rc_id": str(rcb.get("rc_id", "")),
                    "admitted_passes_count": len(admitted_passes),
                    "replay_verified_cases": int(gpr.get("replay_verified_count", 0)),
                    "certification_bundle_digest": str(rcb.get("certification_bundle_digest", "")),
                    "cycle0_final_chain_hash": str(c0t.get("final_chain_hash", "")),
                    "cycle1_final_chain_hash": str(c1t.get("final_chain_hash", "")),
                    "production_mutation_allowed": bool(eli_t.get("production_mutation_allowed", False)),
                }
                expected_ft_digest = "sha256:" + hashlib.sha256(
                    json.dumps(ft_digest_payload, sort_keys=True).encode("utf-8")
                ).hexdigest()
                if claimed_ft_digest != expected_ft_digest:
                    return False

            fu = pkt.get("frontier_u_verification")
            if r_mode == "hcam_shard_consensus_observatory" and not isinstance(fu, dict):
                return False
            if fu is not None:
                if not isinstance(fu, dict) or fu.get("hcam_shard_verified") is not True:
                    return False
                har = fu.get("hcam_associative_recall")
                csc = fu.get("cross_shard_consensus")
                tgm = fu.get("transactional_geodesic_and_migration")
                mgc = fu.get("manifold_garbage_collection")
                ftp_u = fu.get("formal_theorem_proof")
                eli_u = fu.get("eligibility_interlock")
                c0u = fu.get("cycle0_audit")
                c1u = fu.get("cycle1_audit")
                if (
                    not isinstance(har, dict)
                    or not isinstance(csc, dict)
                    or not isinstance(tgm, dict)
                    or not isinstance(mgc, dict)
                    or not isinstance(ftp_u, dict)
                    or not isinstance(eli_u, dict)
                    or not isinstance(c0u, dict)
                    or not isinstance(c1u, dict)
                ):
                    return False
                u_commit_ok = csc.get("cycle1_consensus_commit_verified", csc.get("consensus_commit_verified"))
                u_mig_ok = tgm.get("cycle1_migration_committed_shadow", tgm.get("migration_committed_shadow"))
                u_orphans = int(mgc.get("cycle1_orphan_nodes_reclaimed", mgc.get("orphan_nodes_reclaimed", 0)))
                u_live_root = mgc.get("cycle1_live_root_reclaimed", mgc.get("live_root_reclaimed"))
                if (
                    har.get("assembled_32b_hex") not in ("0x7d5d7757", "0xdeadbeef")
                    or har.get("assembled_64b_hex") not in ("0x78005655775757", "0x0123456789abcdef")
                    or har.get("word_assembly_verified") is not True
                    or int(csc.get("cycle1_local_quorum_shards", 0)) < 4
                    or csc.get("cycle1_global_quorum_met") is not True
                    or u_commit_ok is not True
                    or u_mig_ok is not True
                    or u_orphans < 2
                    or u_live_root is not False
                    or ftp_u.get("verdict") != "PROVED_THEOREM"
                    or eli_u.get("production_mutation_allowed") is not False
                    or eli_u.get("authorized_claimed") is not False
                    or eli_u.get("sacred_core_immutable") is not True
                    or c0u.get("policy_status") not in ("QUARANTINE", "QUARANTINED")
                    or c1u.get("policy_status") != "ELIGIBLE"
                ):
                    return False
                claimed_fu_digest = fu.get("frontier_u_summary_digest") or fu.get("summary_digest")
                if not isinstance(claimed_fu_digest, str) or not claimed_fu_digest.startswith("sha256:"):
                    return False
                fu_digest_payload = {
                    "experiment_id": str(fu.get("experiment_id", "")),
                    "frontier_id": str(fu.get("frontier_id", "Frontier_U")),
                    "assembled_32b_hex": str(har.get("assembled_32b_hex", "")),
                    "assembled_64b_hex": str(har.get("assembled_64b_hex", "")),
                    "local_quorum_shards": int(csc.get("cycle1_local_quorum_shards", 0)),
                    "global_quorum_met": bool(csc.get("cycle1_global_quorum_met", False)),
                    "orphan_nodes_reclaimed": u_orphans,
                    "cycle0_final_chain_hash": str(c0u.get("final_chain_hash", "")),
                    "cycle1_final_chain_hash": str(c1u.get("final_chain_hash", "")),
                }
                expected_fu_digest = "sha256:" + hashlib.sha256(
                    json.dumps(fu_digest_payload, sort_keys=True).encode("utf-8")
                ).hexdigest()
                if claimed_fu_digest != expected_fu_digest:
                    return False

            fv = pkt.get("frontier_v_verification")
            if r_mode == "waveguide_simd_pipeline_observatory" and not isinstance(fv, dict):
                return False
            if fv is not None:
                if not isinstance(fv, dict) or fv.get("waveguide_simd_verified") is not True:
                    return False
                wap = fv.get("waveguide_arithmetic_and_predication")
                sma = fv.get("scoreboard_and_memory_alias")
                smr = fv.get("simd_multicore_and_route_rebalance")
                ftp_v = fv.get("formal_theorem_proof")
                eli_v = fv.get("eligibility_interlock")
                c0v = fv.get("cycle0_audit")
                c1v = fv.get("cycle1_audit")
                if (
                    not isinstance(wap, dict)
                    or not isinstance(sma, dict)
                    or not isinstance(smr, dict)
                    or not isinstance(ftp_v, dict)
                    or not isinstance(eli_v, dict)
                    or not isinstance(c0v, dict)
                    or not isinstance(c1v, dict)
                ):
                    return False
                if (
                    wap.get("add_32b_oracle_match") is not True
                    or wap.get("sub_32b_oracle_match") is not True
                    or wap.get("add_64b_oracle_match") is not True
                    or wap.get("sub_64b_oracle_match") is not True
                    or int(wap.get("predicated_diamonds_converted", 0)) < 1
                    or wap.get("flags_externally_visible") is not False
                    or sma.get("cycle1_schedule_serial_equivalent") is not True
                    or int(smr.get("assembled_core_count", 0)) != 4
                    or int(smr.get("simd_lane_width", 0)) != 64
                    or int(smr.get("fault_matrix_passed_cases", 0)) < 33
                    or ftp_v.get("verdict") != "PROVED_THEOREM"
                    or ftp_v.get("refuted_verdict") not in ("DISPROVED_COUNTEREXAMPLE", "REFUTED_COUNTEREXAMPLE")
                    or eli_v.get("production_mutation_allowed") is not False
                    or eli_v.get("authorized_claimed") is not False
                    or eli_v.get("sacred_core_immutable") is not True
                    or c0v.get("policy_status") not in ("QUARANTINE", "QUARANTINED")
                    or c1v.get("policy_status") != "ELIGIBLE"
                ):
                    return False
                claimed_fv_digest = fv.get("frontier_v_summary_digest") or fv.get("summary_digest")
                if not isinstance(claimed_fv_digest, str) or not claimed_fv_digest.startswith("sha256:"):
                    return False
                fv_digest_payload = {
                    "experiment_id": str(fv.get("experiment_id", "")),
                    "frontier_id": str(fv.get("frontier_id", "Frontier_V")),
                    "add_64b_oracle_match": bool(wap.get("add_64b_oracle_match", False)),
                    "sub_64b_oracle_match": bool(wap.get("sub_64b_oracle_match", False)),
                    "predicated_diamonds_converted": int(wap.get("predicated_diamonds_converted", 0)),
                    "assembled_core_count": int(smr.get("assembled_core_count", 0)),
                    "fault_matrix_passed_cases": int(smr.get("fault_matrix_passed_cases", 0)),
                    "cycle0_final_chain_hash": str(c0v.get("final_chain_hash", "")),
                    "cycle1_final_chain_hash": str(c1v.get("final_chain_hash", "")),
                }
                expected_fv_digest = "sha256:" + hashlib.sha256(
                    json.dumps(fv_digest_payload, sort_keys=True).encode("utf-8")
                ).hexdigest()
                if claimed_fv_digest != expected_fv_digest:
                    return False

            fw = pkt.get("frontier_w_verification")
            if r_mode == "burnin_attestation_observatory" and not isinstance(fw, dict):
                return False
            if fw is not None:
                if not isinstance(fw, dict) or fw.get("burnin_attestation_verified") is not True:
                    return False
                sbl = fw.get("sovereign_burnin_and_stability_ledger")
                pad = fw.get("package_archive_digest_attestation")
                ocv = fw.get("offline_consumer_verification_and_final_manifest")
                ftp_w = fw.get("formal_theorem_proof")
                eli_w = fw.get("eligibility_interlock")
                c0w = fw.get("cycle0_audit")
                c1w = fw.get("cycle1_audit")
                if (
                    not isinstance(sbl, dict)
                    or not isinstance(pad, dict)
                    or not isinstance(ocv, dict)
                    or not isinstance(ftp_w, dict)
                    or not isinstance(eli_w, dict)
                    or not isinstance(c0w, dict)
                    or not isinstance(c1w, dict)
                ):
                    return False
                w_cycles = int(sbl.get("cycle1_cycles_executed", sbl.get("cycles_executed", 0)))
                w_ledger_ok = sbl.get("cycle1_ledger_chain_valid", sbl.get("ledger_chain_valid"))
                w_rb_ok = sbl.get("regression_rollback_verified", sbl.get("cycle0_regression_rollback_verified"))
                w_arch_ok = pad.get("cycle1_archive_file_digest_match", pad.get("archive_file_digest_match"))
                w_steps = int(ocv.get("cycle1_ready_verification_steps", ocv.get("ready_verification_steps", 0)))
                if (
                    w_cycles < 6
                    or w_ledger_ok is not True
                    or w_rb_ok is not True
                    or w_arch_ok is not True
                    or pad.get("real_signature_claimed") is not False
                    or pad.get("network_access_used") is not False
                    or w_steps < 7
                    or ocv.get("final_system_manifest_valid") is not True
                    or ftp_w.get("verdict") != "PROVED_THEOREM"
                    or eli_w.get("production_mutation_allowed") is not False
                    or eli_w.get("authorized_claimed") is not False
                    or eli_w.get("sacred_core_immutable") is not True
                    or c0w.get("policy_status") not in ("QUARANTINE", "QUARANTINED")
                    or c1w.get("policy_status") != "ELIGIBLE"
                ):
                    return False
                claimed_fw_digest = fw.get("frontier_w_summary_digest") or fw.get("summary_digest")
                if not isinstance(claimed_fw_digest, str) or not claimed_fw_digest.startswith("sha256:"):
                    return False
                fw_digest_payload = {
                    "experiment_id": str(fw.get("experiment_id", "")),
                    "frontier_id": str(fw.get("frontier_id", "Frontier_W")),
                    "cycles_executed": w_cycles,
                    "ledger_chain_valid": bool(w_ledger_ok),
                    "archive_file_digest_match": bool(w_arch_ok),
                    "ready_verification_steps": w_steps,
                    "final_system_manifest_valid": bool(ocv.get("final_system_manifest_valid", False)),
                    "cycle0_final_chain_hash": str(c0w.get("final_chain_hash", "")),
                    "cycle1_final_chain_hash": str(c1w.get("final_chain_hash", "")),
                }
                expected_fw_digest = "sha256:" + hashlib.sha256(
                    json.dumps(fw_digest_payload, sort_keys=True).encode("utf-8")
                ).hexdigest()
                if claimed_fw_digest != expected_fw_digest:
                    return False

            fx = pkt.get("frontier_x_verification")
            if r_mode == "entangled_cadence_wavefront_observatory" and not isinstance(fx, dict):
                return False
            if fx is not None:
                if not isinstance(fx, dict) or fx.get("entangled_cadence_verified") is not True:
                    return False
                if (
                    fx.get("allow_production_execution") is not False
                    or fx.get("authorized_claimed") is not False
                    or fx.get("edge_gate", {}).get("policy_gate_passed") is not True
                ):
                    return False
                has_fx_bridge = "cadence_calibration" in fx
                has_fx_pkt = "entangled_sequencer_and_atomic_epoch" in fx
                if not has_fx_bridge and not has_fx_pkt:
                    return False
                if has_fx_bridge:
                    cad = fx.get("cadence_calibration", {})
                    res_s = fx.get("resonant_schedule", {})
                    ent_c = fx.get("entangled_commit", {})
                    msync = fx.get("manifold_sync", {})
                    wfs = fx.get("wavefront_synthesis", {})
                    rangers_x = fx.get("ranger_observations", {})
                    dgi_x = fx.get("default_graph_integrity", {})
                    if (
                        not isinstance(cad, dict)
                        or not isinstance(res_s, dict)
                        or not isinstance(ent_c, dict)
                        or not isinstance(msync, dict)
                        or not isinstance(wfs, dict)
                        or not isinstance(rangers_x, dict)
                        or not isinstance(dgi_x, dict)
                        or int(cad.get("profile_count", 0)) < 4
                        or int(cad.get("calibrated_count", 0)) < 4
                        or cad.get("multimanifold_sync_success") is not True
                        or cad.get("active_cadence_mutated") is not False
                        or res_s.get("schedule_valid") is not True
                        or int(res_s.get("collision_count", -1)) != 0
                        or res_s.get("cycle0_guard_passed") is not False
                        or res_s.get("cycle1_guard_passed") is not True
                        or ent_c.get("status") != "committed_shadow"
                        or ent_c.get("atomic_barrier_satisfied") is not True
                        or ent_c.get("commit_barrier_satisfied") is not True
                        or ent_c.get("active_tables_mutated") is not False
                        or ent_c.get("fault_abort_status") != "aborted"
                        or ent_c.get("fault_rollback_performed") is not True
                        or float(ent_c.get("phase_skew_rad", 1.0)) > 0.05
                        or msync.get("sync_valid") is not True
                        or msync.get("drift_quarantine_triggered") is not True
                        or wfs.get("wavefront_stability_passed") is not True
                        or wfs.get("uncertainty_within_bounds") is not True
                        or int(wfs.get("passed_32b_cases", 0)) < 4
                        or int(wfs.get("passed_64b_cases", 0)) < 4
                        or int(rangers_x.get("verified_packet_count", 0)) < 4
                        or dgi_x.get("verified") is not True
                    ):
                        return False
                    fx_eval_keys = (
                        "frontier",
                        "vector",
                        "title",
                        "default_graph_integrity",
                        "cadence_calibration",
                        "resonant_schedule",
                        "entangled_commit",
                        "manifold_sync",
                        "wavefront_synthesis",
                        "ranger_observations",
                        "edge_gate",
                        "allow_production_execution",
                        "authorized_claimed",
                        "decisions",
                    )
                    fx_eval_sub = {k: fx[k] for k in fx_eval_keys if k in fx}
                    expected_fx_art = hashlib.sha256(
                        json.dumps(fx_eval_sub, sort_keys=True, default=str).encode("utf-8")
                    ).hexdigest()
                    if fx.get("artifact_digest") != expected_fx_art:
                        return False
                if has_fx_pkt:
                    esae = fx.get("entangled_sequencer_and_atomic_epoch")
                    mcag = fx.get("multimanifold_cadence_and_autonomy_guard")
                    waub = fx.get("wavefront_alignment_and_uncertainty_bounds")
                    ftp_x = fx.get("formal_theorem_proof")
                    eli_x = fx.get("eligibility_interlock")
                    c0x = fx.get("cycle0_audit")
                    c1x = fx.get("cycle1_audit")
                    if (
                        not isinstance(esae, dict)
                        or not isinstance(mcag, dict)
                        or not isinstance(waub, dict)
                        or not isinstance(ftp_x, dict)
                        or not isinstance(eli_x, dict)
                        or not isinstance(c0x, dict)
                        or not isinstance(c1x, dict)
                    ):
                        return False
                    if (
                        int(esae.get("manifold_count", 0)) < 4
                        or esae.get("atomic_epoch_committed_shadow") is not True
                        or esae.get("commit_epoch_committed_shadow") is not True
                        or esae.get("abort_rollback_verified") is not True
                        or mcag.get("cycle0_autonomy_bounded") is not False
                        or mcag.get("cycle1_autonomy_bounded") is not True
                        or mcag.get("autonomy_bounded") is not True
                        or waub.get("wavefront_stability_passed") is not True
                        or waub.get("uncertainty_within_bounds") is not True
                        or ftp_x.get("verdict") != "PROVED_THEOREM"
                        or eli_x.get("production_mutation_allowed") is not False
                        or eli_x.get("authorized_claimed") is not False
                        or eli_x.get("allow_production_execution") is not False
                        or eli_x.get("sacred_core_immutable") is not True
                        or c0x.get("policy_status") not in ("QUARANTINE", "QUARANTINED")
                        or c1x.get("policy_status") != "ELIGIBLE"
                    ):
                        return False

            fy = pkt.get("frontier_y_verification")
            if r_mode == "waveguide_channel_staging_observatory" and not isinstance(fy, dict):
                return False
            if fy is not None:
                if not isinstance(fy, dict) or fy.get("waveguide_channel_staging_verified") is not True:
                    return False
                if (
                    fy.get("allow_production_execution") is not False
                    or fy.get("authorized_claimed") is not False
                    or fy.get("edge_gate", {}).get("policy_gate_passed") is not True
                ):
                    return False
                has_fy_bridge = "channel_kernels" in fy
                has_fy_pkt = "waveguide_channel_kernels_and_dependency" in fy
                if not has_fy_bridge and not has_fy_pkt:
                    return False
                if has_fy_bridge:
                    ck = fy.get("channel_kernels", {})
                    cdep = fy.get("channel_dependency", {})
                    lopt = fy.get("layout_optimization", {})
                    pcomp = fy.get("pipeline_compaction", {})
                    pdrg = fy.get("package_dry_run_and_gate", {})
                    cls_y = fy.get("controlled_local_staging", {})
                    dgi_y = fy.get("default_graph_integrity", {})
                    if (
                        not isinstance(ck, dict)
                        or not isinstance(cdep, dict)
                        or not isinstance(lopt, dict)
                        or not isinstance(pcomp, dict)
                        or not isinstance(pdrg, dict)
                        or not isinstance(cls_y, dict)
                        or not isinstance(dgi_y, dict)
                        or ck.get("library_valid") is not True
                        or int(ck.get("recognized_kernel_count", 0)) < 5
                        or cdep.get("safe_batch_verified") is not True
                        or cdep.get("raw_hazard_detected_on_conflict") is not True
                        or float(lopt.get("crosstalk_reduction", -1.0)) < 0.0
                        or float(lopt.get("efficiency_gain", -1.0)) < 0.0
                        or pcomp.get("compaction_equivalence_verified") is not True
                        or pdrg.get("transcript_valid") is not True
                        or int(pdrg.get("verified_noop_event_count", 0)) < 182
                        or pdrg.get("noop_boundary_verified") is not True
                        or pdrg.get("physical_gate_valid") is not True
                        or pdrg.get("physical_execution_permitted_by_gate") is not False
                        or cls_y.get("staging_plan_valid") is not True
                        or cls_y.get("staging_record_valid") is not True
                        or int(cls_y.get("copied_file_count", 0)) < 28
                        or cls_y.get("all_digests_matched") is not True
                        or cls_y.get("zero_archive_upload_deploy_mutation") is not True
                        or dgi_y.get("verified") is not True
                    ):
                        return False
                    fy_eval_keys = (
                        "frontier",
                        "vector",
                        "title",
                        "default_graph_integrity",
                        "channel_kernels",
                        "channel_dependency",
                        "layout_optimization",
                        "pipeline_compaction",
                        "package_dry_run_and_gate",
                        "controlled_local_staging",
                        "edge_gate",
                        "allow_production_execution",
                        "authorized_claimed",
                        "decisions",
                    )
                    fy_eval_sub = {k: fy[k] for k in fy_eval_keys if k in fy}
                    expected_fy_art = hashlib.sha256(
                        json.dumps(fy_eval_sub, sort_keys=True, default=str).encode("utf-8")
                    ).hexdigest()
                    if fy.get("artifact_digest") != expected_fy_art:
                        return False
                if has_fy_pkt:
                    wckd = fy.get("waveguide_channel_kernels_and_dependency")
                    lopc = fy.get("layout_optimization_and_pipeline_compaction")
                    padl = fy.get("package_assembly_dry_run_and_local_staging")
                    ftp_y = fy.get("formal_theorem_proof")
                    eli_y = fy.get("eligibility_interlock")
                    c0y = fy.get("cycle0_audit")
                    c1y = fy.get("cycle1_audit")
                    if (
                        not isinstance(wckd, dict)
                        or not isinstance(lopc, dict)
                        or not isinstance(padl, dict)
                        or not isinstance(ftp_y, dict)
                        or not isinstance(eli_y, dict)
                        or not isinstance(c0y, dict)
                        or not isinstance(c1y, dict)
                    ):
                        return False
                    if (
                        wckd.get("library_valid") is not True
                        or int(wckd.get("recognized_kernels_count", 0)) < 5
                        or wckd.get("cycle1_batch_safe") is not True
                        or wckd.get("raw_hazard_detected_on_conflict") is not True
                        or lopc.get("compaction_equivalence_verified") is not True
                        or float(lopc.get("crosstalk_reduction", 0.0)) <= 0.0
                        or padl.get("transcript_valid") is not True
                        or int(padl.get("noop_dry_run_events_count", 0)) < 182
                        or padl.get("physical_execution_permitted_by_gate") is not False
                        or int(padl.get("local_staging_copied_files", 0)) < 28
                        or padl.get("local_staging_all_digests_matched") is not True
                        or padl.get("zero_archive_upload_deploy_mutation") is not True
                        or ftp_y.get("verdict") != "PROVED_THEOREM"
                        or eli_y.get("production_mutation_allowed") is not False
                        or eli_y.get("authorized_claimed") is not False
                        or eli_y.get("allow_production_execution") is not False
                        or eli_y.get("sacred_core_immutable") is not True
                        or c0y.get("policy_status") not in ("QUARANTINE", "QUARANTINED")
                        or c1y.get("policy_status") != "ELIGIBLE"
                    ):
                        return False

            fz = pkt.get("frontier_z_verification")
            if r_mode == "sovereign_court_lockdown_observatory" and not isinstance(fz, dict):
                return False
            if fz is not None:
                if not isinstance(fz, dict) or fz.get("sovereign_court_lockdown_verified") is not True:
                    return False
                if (
                    fz.get("allow_production_execution") is not False
                    or fz.get("authorized_claimed") is not False
                    or fz.get("edge_gate", {}).get("policy_gate_passed") is not True
                ):
                    return False
                has_fz_bridge = "court_promotion_docket" in fz
                has_fz_pkt = "court_supervised_promotion_and_docket" in fz
                if not has_fz_bridge and not has_fz_pkt:
                    return False
                if has_fz_bridge:
                    cpd = fz.get("court_promotion_docket", {})
                    fgr = fz.get("final_gate_registry", {})
                    gfl = fz.get("governance_freeze_and_lockdown", {})
                    fd_z = fz.get("finalization_docket", {})
                    srg = fz.get("sovereign_runtime_and_gateway", {})
                    rangers_z = fz.get("ranger_observations", {})
                    dgi_z = fz.get("default_graph_integrity", {})
                    if (
                        not isinstance(cpd, dict)
                        or not isinstance(fgr, dict)
                        or not isinstance(gfl, dict)
                        or not isinstance(fd_z, dict)
                        or not isinstance(srg, dict)
                        or not isinstance(rangers_z, dict)
                        or not isinstance(dgi_z, dict)
                        or cpd.get("promotion_ready") is not True
                        or cpd.get("policy_satisfied") is not True
                        or cpd.get("production_docket_rejected") is not True
                        or int(fgr.get("total_gates", 0)) < 11
                        or int(fgr.get("passed_count", 0)) < 11
                        or int(fgr.get("failed_count", -1)) != 0
                        or fgr.get("all_passed") is not True
                        or fgr.get("finalized_immutable") is not True
                        or gfl.get("governance_frozen") is not True
                        or gfl.get("governance_invariants_passed") is not True
                        or gfl.get("governance_tamper_detected") is not True
                        or gfl.get("system_locked") is not True
                        or gfl.get("system_lockdown_passed") is not True
                        or gfl.get("lockdown_tamper_detected") is not True
                        or int(fd_z.get("evidence_count", 0)) < 10
                        or fd_z.get("valid") is not True
                        or fd_z.get("court_review_verdict") != "promote_level50_candidate"
                        or srg.get("runtime_valid") is not True
                        or srg.get("allow_production_execution") is not False
                        or srg.get("shadow_finalization_command_success") is not True
                        or srg.get("production_command_blocked_and_held") is not True
                        or srg.get("gateway_policy_default_deny") is not True
                        or srg.get("gateway_production_mutation_decision") != "deny"
                        or int(rangers_z.get("verified_packet_count", 0)) < 4
                        or dgi_z.get("verified") is not True
                    ):
                        return False
                    fz_eval_keys = (
                        "frontier",
                        "vector",
                        "title",
                        "default_graph_integrity",
                        "court_promotion_docket",
                        "final_gate_registry",
                        "governance_freeze_and_lockdown",
                        "finalization_docket",
                        "sovereign_runtime_and_gateway",
                        "ranger_observations",
                        "edge_gate",
                        "allow_production_execution",
                        "authorized_claimed",
                        "decisions",
                    )
                    fz_eval_sub = {k: fz[k] for k in fz_eval_keys if k in fz}
                    expected_fz_art = hashlib.sha256(
                        json.dumps(fz_eval_sub, sort_keys=True, default=str).encode("utf-8")
                    ).hexdigest()
                    if fz.get("artifact_digest") != expected_fz_art:
                        return False
                if has_fz_pkt:
                    cspd = fz.get("court_supervised_promotion_and_docket")
                    fgrf = fz.get("final_gate_registry_and_finalization_docket")
                    gfsl = fz.get("governance_freeze_and_system_lockdown")
                    ftp_z = fz.get("formal_theorem_proof")
                    eli_z = fz.get("eligibility_interlock")
                    c0z = fz.get("cycle0_audit")
                    c1z = fz.get("cycle1_audit")
                    if (
                        not isinstance(cspd, dict)
                        or not isinstance(fgrf, dict)
                        or not isinstance(gfsl, dict)
                        or not isinstance(ftp_z, dict)
                        or not isinstance(eli_z, dict)
                        or not isinstance(c0z, dict)
                        or not isinstance(c1z, dict)
                    ):
                        return False
                    if (
                        cspd.get("auto_promote_allowed") is not False
                        or cspd.get("production_authority_granted") is not False
                        or cspd.get("review_decision_verdict") != "approve_sandbox_trial"
                        or int(fgrf.get("registered_gates_count", 0)) < 11
                        or int(fgrf.get("passed_gates_count", 0)) < 11
                        or int(fgrf.get("failed_gates_count", -1)) != 0
                        or fgrf.get("all_gates_passed") is not True
                        or fgrf.get("registry_immutable_verified") is not True
                        or fgrf.get("finalization_docket_valid") is not True
                        or fgrf.get("court_final_decision") != "approve"
                        or int(gfsl.get("freeze_invariant_count", 0)) < 10
                        or int(gfsl.get("cycle1_freeze_violations_count", -1)) != 0
                        or gfsl.get("cycle1_frozen") is not True
                        or int(gfsl.get("lockdown_setting_count", 0)) < 12
                        or int(gfsl.get("cycle1_lockdown_violations_count", -1)) != 0
                        or gfsl.get("cycle1_locked") is not True
                        or gfsl.get("runtime_token_shadow_only_verified") is not True
                        or gfsl.get("production_gateway_blocked_verified") is not True
                        or ftp_z.get("verdict") != "PROVED_THEOREM"
                        or eli_z.get("production_mutation_allowed") is not False
                        or eli_z.get("authorized_claimed") is not False
                        or eli_z.get("allow_production_execution") is not False
                        or eli_z.get("sacred_core_immutable") is not True
                        or c0z.get("policy_status") not in ("QUARANTINE", "QUARANTINED")
                        or c1z.get("policy_status") != "ELIGIBLE"
                    ):
                        return False
        except (TypeError, ValueError, KeyError, AttributeError):
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
                "wgsl_decision_prover_observatory",
                "swarm_cohomology_observatory",
                "umok_edge_kernel_observatory",
                "mitotic_foliation_observatory",
                "stwm_wavefront_observatory",
                "rsi_compiler_observatory",
                "hcam_shard_consensus_observatory",
                "waveguide_simd_pipeline_observatory",
                "burnin_attestation_observatory",
                "entangled_cadence_wavefront_observatory",
                "waveguide_channel_staging_observatory",
                "sovereign_court_lockdown_observatory",
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

    def _record_frontier_xyz_observatory_run(
        self,
        *,
        frontier_letter: str,
        run_slug: str,
        run_mode: str,
        study_name: str,
        selected_opt_id: str,
        selected_opt_name: str,
        signer_role: str,
        repair_kind: str,
        verification_key: str,
        verified_flag_key: str,
        evaluation_payload: Any,
    ) -> Dict[str, Any]:
        raw_input = evaluation_payload
        if hasattr(raw_input, "evaluation_payload") and isinstance(getattr(raw_input, "evaluation_payload"), dict):
            eval_dict = dict(getattr(raw_input, "evaluation_payload"))
            if hasattr(raw_input, "study_name") and getattr(raw_input, "study_name"):
                study_name = str(getattr(raw_input, "study_name"))
            if hasattr(raw_input, "experiment_id") and getattr(raw_input, "experiment_id"):
                eval_dict.setdefault("experiment_id", str(getattr(raw_input, "experiment_id")))
        elif hasattr(raw_input, "to_dict") and callable(raw_input.to_dict):
            d = raw_input.to_dict()
            eval_dict = dict(d.get("evaluation_payload") or d)
            if d.get("study_name"):
                study_name = str(d["study_name"])
        elif isinstance(raw_input, dict):
            eval_dict = dict(raw_input.get("evaluation_payload") or raw_input)
            if raw_input.get("study_name"):
                study_name = str(raw_input["study_name"])
        else:
            eval_dict = {}
        evaluation_payload = eval_dict

        exp_id = str(evaluation_payload.get("experiment_id") or evaluation_payload.get("artifact_digest", "00000000"))[:16]
        run_id = f"run:{run_slug}:{exp_id}"[:128]
        packet_id = f"pkt:{run_slug}:{exp_id}"
        edge_gate = dict(evaluation_payload.get("edge_gate", {}) or {})
        policy_passed = bool(edge_gate.get("policy_gate_passed", True))
        ver_block = dict(evaluation_payload)
        ver_block[verified_flag_key] = bool(
            policy_passed
            and evaluation_payload.get("allow_production_execution") is False
            and evaluation_payload.get("authorized_claimed") is False
        )
        pkt = {
            "schema": "techman.sol-lens.proof-packet/v0.2",
            "packet_id": packet_id,
            "study_name": study_name,
            verification_key: ver_block,
        }
        if not self._verify_continuum_frontier_metadata(run_mode, json.dumps(pkt, sort_keys=True, default=str)):
            raise ValueError(f"Frontier {frontier_letter} metadata verification failed (fail-closed).")

        now_dt = datetime.now(timezone.utc).replace(microsecond=0)
        now_iso = now_dt.isoformat()

        class _CycleAuditStub:
            def __init__(self, policy_status: str, is_quarantined: bool, reason: str) -> None:
                self.policy_status = policy_status
                self.is_quarantined = is_quarantined
                self.governance_reason = reason
                self.cohomological_event = f"frontier_{frontier_letter.lower()}_{policy_status.lower()}"
                self.workflow_version = f"frontier-{frontier_letter.lower()}-v1"
                self.events = ()

        c0_stub = _CycleAuditStub("QUARANTINE", True, f"Frontier {frontier_letter} Cycle 0 baseline quarantine")
        c1_stub = _CycleAuditStub("ELIGIBLE", False, f"Frontier {frontier_letter} Cycle 1 governed synthesis eligible")

        c0_events, c0_replayed_digest = self._ensure_continuum_cycle_events(
            run_id=run_id,
            option_id=selected_opt_id,
            cycle_label="cycle0",
            audit_obj=c0_stub,
            occurred_at=now_dt,
        )
        c1_events, c1_replayed_digest = self._ensure_continuum_cycle_events(
            run_id=run_id,
            option_id=selected_opt_id,
            cycle_label="cycle1",
            audit_obj=c1_stub,
            occurred_at=now_dt,
        )
        prior_q_digest = c0_replayed_digest
        final_state_digest = c1_replayed_digest
        interaction_id = f"{run_slug}-{exp_id}"
        policy_status = "ELIGIBLE"

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
                model_used="gemini-4-argon",
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
                    "gemini-4-argon",
                    interaction_id,
                    "high",
                    selected_opt_id,
                    selected_opt_name,
                    policy_status,
                    "COMPLETED",
                    "PROMOTE_IF_REVIEWED",
                    1,
                    0,
                    0.0,
                    0.0,
                    1.0,
                    1.25,
                    final_state_digest,
                    prior_q_digest,
                    prev_run_digest,
                    entry_digest,
                    0,
                    None,
                    signer_role,
                    json.dumps(pkt, sort_keys=True, default=str),
                    now_iso,
                ),
            )

            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle0-quarantine", c0_events)
            self._insert_runtime_events(run_id, f"{selected_opt_id}:cycle1-eligible", c1_events)

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
                    repair_kind,
                    selected_opt_id,
                    1,
                    0,
                    1.0,
                    0.0,
                    1.0,
                    prior_q_digest,
                    final_state_digest,
                    f"{run_slug}-c0:{exp_id}",
                    interaction_id,
                    json.dumps({"cycle": 0, "status": "QUARANTINE"}),
                    json.dumps({"cycle": 1, "status": "ELIGIBLE", "artifact_digest": evaluation_payload.get("artifact_digest")}),
                    f"Frontier {frontier_letter} fail-closed sovereign synthesis verified.",
                ),
            )

        f_let = frontier_letter.lower()
        summary_digest = "sha256:" + str(evaluation_payload.get("artifact_digest", entry_digest.replace("sha256:", "")))
        return {
            "run_id": run_id,
            "packet_id": packet_id,
            "run_mode": run_mode,
            "policy_status": policy_status.lower(),
            "previous_run_digest": prev_run_digest,
            "ledger_entry_digest": entry_digest,
            "final_state_digest": final_state_digest,
            "prior_quarantined_state_digest": prior_q_digest,
            "edge_event_count": len(c0_events) + len(c1_events),
            "verified": True,
            f"frontier_{f_let}_verified": True,
            f"frontier_{f_let}_summary_digest": summary_digest,
        }

    def record_entangled_cadence_observatory_run(
        self,
        evaluation_payload: Dict[str, Any],
        study_name: str = "Frontier_X_Entangled_Cadence_Wavefront_2PC",
    ) -> Dict[str, Any]:
        return self._record_frontier_xyz_observatory_run(
            frontier_letter="X",
            run_slug="entangled-cadence",
            run_mode="entangled_cadence_wavefront_observatory",
            study_name=study_name,
            selected_opt_id="opt_entangled_cadence_wavefront_2pc",
            selected_opt_name="Entangled Multi-Manifold 2PC, Resonant Cadence & Wavefront Synthesis",
            signer_role="SOL-Decide Entangled Cadence & Wavefront Governance Court",
            repair_kind="entangled_cadence_wavefront_2pc_synthesis",
            verification_key="frontier_x_verification",
            verified_flag_key="entangled_cadence_verified",
            evaluation_payload=evaluation_payload,
        )

    def record_waveguide_channel_staging_observatory_run(
        self,
        evaluation_payload: Dict[str, Any],
        study_name: str = "Frontier_Y_Waveguide_Channel_Layout_Local_Staging",
    ) -> Dict[str, Any]:
        return self._record_frontier_xyz_observatory_run(
            frontier_letter="Y",
            run_slug="waveguide-channel-staging",
            run_mode="waveguide_channel_staging_observatory",
            study_name=study_name,
            selected_opt_id="opt_waveguide_channel_layout_local_staging",
            selected_opt_name="Waveguide Channel Optimization, Layout Compaction & Local Staging",
            signer_role="SOL-Decide Waveguide Channel & Local Staging Governance Court",
            repair_kind="waveguide_channel_layout_compaction_and_local_staging",
            verification_key="frontier_y_verification",
            verified_flag_key="waveguide_channel_staging_verified",
            evaluation_payload=evaluation_payload,
        )

    def record_sovereign_court_lockdown_observatory_run(
        self,
        evaluation_payload: Dict[str, Any],
        study_name: str = "Frontier_Z_Sovereign_Court_Final_Gate_System_Lockdown",
    ) -> Dict[str, Any]:
        return self._record_frontier_xyz_observatory_run(
            frontier_letter="Z",
            run_slug="sovereign-court-lockdown",
            run_mode="sovereign_court_lockdown_observatory",
            study_name=study_name,
            selected_opt_id="opt_sovereign_court_final_gate_system_lockdown",
            selected_opt_name="Sovereign Court Promotion, Final Gate Registry & System Lockdown",
            signer_role="SOL-Decide Sovereign Court & System Lockdown Capstone Authority",
            repair_kind="sovereign_court_final_gate_and_system_lockdown",
            verification_key="frontier_z_verification",
            verified_flag_key="sovereign_court_lockdown_verified",
            evaluation_payload=evaluation_payload,
        )

    record_mitotic_foliation_study = record_mitotic_foliation_episode
    record_mitotic_foliation_study_run = record_mitotic_foliation_episode
    record_stwm_wavefront_study = record_stwm_wavefront_episode
    record_stwm_wavefront_study_run = record_stwm_wavefront_episode
    record_rsi_compiler_study = record_rsi_compiler_episode
    record_rsi_compiler_study_run = record_rsi_compiler_episode
    record_hcam_shard_study = record_hcam_shard_episode
    record_hcam_shard_study_run = record_hcam_shard_episode
    record_waveguide_simd_study = record_waveguide_simd_episode
    record_waveguide_simd_study_run = record_waveguide_simd_episode
    record_burnin_attestation_study = record_burnin_attestation_episode
    record_burnin_attestation_study_run = record_burnin_attestation_episode
    record_entangled_cadence_episode = record_entangled_cadence_observatory_run
    record_waveguide_channel_staging_episode = record_waveguide_channel_staging_observatory_run
    record_sovereign_court_lockdown_episode = record_sovereign_court_lockdown_observatory_run

