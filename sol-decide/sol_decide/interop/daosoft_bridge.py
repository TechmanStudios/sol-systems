"""
SOL-Decide: DAOSoft Interoperability & Bi-Directional Bridge
============================================================
Enables seamless data exchange with legacy DAOSoft COTS decision tools,
allowing SOL-Decide to either export structured packages into DAOSoft
or ingest legacy MAUT spreadsheets into living sheaf decision graphs.
"""

from typing import Any

import numpy as np

from ..core.primitives import (
    Constraint,
    ConstraintSeverity,
    Objective,
    OptimizationDirection,
    Option,
    PrimitiveType,
)
from ..core.sheaf_decision_complex import DecisionEvaluationReport, SheafDecisionComplex


class DAOSoftBridge:
    """
    Bi-directional translator between DAOSoft tabular trade study formats
    and SOL-Decide SheafDecisionComplex graphs.
    """

    @staticmethod
    def _resolve_severity(raw_sev: Any) -> ConstraintSeverity:
        if isinstance(raw_sev, ConstraintSeverity):
            return raw_sev
        if isinstance(raw_sev, str):
            norm = raw_sev.strip().lower()
            for member in ConstraintSeverity:
                if member.value == norm or member.name.lower() == norm:
                    return member
        return ConstraintSeverity.HARD

    def ingest_daosoft_matrix(
        self,
        daosoft_data: dict[str, Any],
        study_name: str = "DAOSoft_Study",
        *,
        compress_quotient: bool | None = None,
    ) -> SheafDecisionComplex:
        """
        Converts a DAOSoft MAUT trade study JSON into a SheafDecisionComplex.
        Supports per-criterion `severity` (hard, soft, threshold, preference, aspirational)
        and exact Quotient Sheaf Compression when `compress_quotient=True` or
        `len(criteria) > 2500`.
        """
        complex_obj = SheafDecisionComplex(name=daosoft_data.get("study_title", study_name))

        raw_criteria = list(daosoft_data.get("criteria", []))
        raw_alternatives = list(daosoft_data.get("alternatives", []))
        explicit_cap = int(daosoft_data.get("quotient_explicit_cap", 256))
        use_quotient = (
            bool(compress_quotient)
            if compress_quotient is not None
            else (bool(daosoft_data.get("compress_quotient", False)) or len(raw_criteria) > 2500)
        )

        alt_meta_copies: list[dict[str, Any]] = [
            {
                **alt,
                "scores": dict(alt.get("scores", {})),
            }
            for alt in raw_alternatives
        ]
        alt_state_overrides: dict[tuple[int, str], float] = {}

        if use_quotient and len(raw_criteria) > explicit_cap:
            head_criteria = list(raw_criteria[:explicit_cap])
            tail_criteria = list(raw_criteria[explicit_cap:])

            # Try exact (has_bounds, min_val, max_val, severity, scores_tuple) equivalence classes first
            exact_groups: dict[Any, list[dict[str, Any]]] = {}
            for crit in tail_criteria:
                cid = crit["id"]
                has_b = ("min_val" in crit) or ("max_val" in crit)
                min_v = float(crit.get("min_val", -np.inf)) if has_b else -np.inf
                max_v = float(crit.get("max_val", np.inf)) if has_b else np.inf
                sev = self._resolve_severity(crit.get("severity", ConstraintSeverity.HARD)).value
                scores_tup = tuple(
                    float(alt.get("scores", {}).get(cid, 50.0)) for alt in raw_alternatives
                )
                key = (has_b, min_v, max_v, sev, scores_tup)
                exact_groups.setdefault(key, []).append(crit)

            synthesized_tail: list[dict[str, Any]] = []
            if len(exact_groups) <= 128:
                for g_idx, ((has_b, min_v, max_v, sev, scores_tup), group) in enumerate(
                    exact_groups.items()
                ):
                    qid = f"quotient_eq_{g_idx}"
                    w_sum = float(sum(float(c.get("weight", 1.0)) for c in group))
                    m_sum = float(sum(float(c.get("quotient_multiplicity", 1.0)) for c in group))
                    q_crit: dict[str, Any] = {
                        "id": qid,
                        "name": f"Quotient Class {g_idx} ({len(group)} compressed)",
                        "weight": w_sum,
                        "quotient_multiplicity": m_sum,
                        "severity": sev,
                    }
                    if has_b:
                        q_crit["min_val"] = min_v
                        q_crit["max_val"] = max_v
                    synthesized_tail.append(q_crit)
                    for a_idx, alt_copy in enumerate(alt_meta_copies):
                        alt_copy["scores"][qid] = float(scores_tup[a_idx])
            else:
                # General heterogeneous quotient compression grouped by (has_bounds, severity, viol_mask)
                het_groups: dict[Any, list[dict[str, Any]]] = {}
                for crit in tail_criteria:
                    cid = crit["id"]
                    has_b = ("min_val" in crit) or ("max_val" in crit)
                    min_v = float(crit.get("min_val", -np.inf)) if has_b else -np.inf
                    max_v = float(crit.get("max_val", np.inf)) if has_b else np.inf
                    sev_enum = self._resolve_severity(crit.get("severity", ConstraintSeverity.HARD))
                    viol_mask = []
                    for alt in raw_alternatives:
                        val = float(alt.get("scores", {}).get(cid, 50.0))
                        if not has_b:
                            viol_mask.append(False)
                        elif not np.isfinite(val):
                            viol_mask.append(True)
                        else:
                            viol_mask.append(bool(val < min_v or val > max_v))
                    key = (has_b, sev_enum.value, tuple(viol_mask))
                    het_groups.setdefault(key, []).append(crit)

                for g_idx, ((has_b, sev, viol_mask), group) in enumerate(het_groups.items()):
                    qid = f"quotient_het_{g_idx}"
                    w_sum = float(sum(float(c.get("weight", 1.0)) for c in group))
                    m_sum = float(sum(float(c.get("quotient_multiplicity", 1.0)) for c in group))
                    q_crit = {
                        "id": qid,
                        "name": f"Heterogeneous Quotient Class {g_idx} ({len(group)} compressed)",
                        "weight": w_sum if abs(w_sum) > 1e-15 else 1.0,
                        "quotient_multiplicity": m_sum,
                        "severity": sev,
                    }
                    if has_b and any(viol_mask):
                        q_crit["min_val"] = 0.0
                        q_crit["max_val"] = np.inf
                    synthesized_tail.append(q_crit)

                    for a_idx, alt_copy in enumerate(alt_meta_copies):
                        weighted_obj_sum = sum(
                            float(c.get("weight", 1.0))
                            * float(raw_alternatives[a_idx].get("scores", {}).get(c["id"], 50.0))
                            for c in group
                        )
                        alt_copy["scores"][qid] = (
                            weighted_obj_sum / w_sum if abs(w_sum) > 1e-15 else weighted_obj_sum
                        )
                        if has_b and any(viol_mask):
                            if viol_mask[a_idx]:
                                total_mag = 0.0
                                for c in group:
                                    c_min = float(c.get("min_val", -np.inf))
                                    c_max = float(c.get("max_val", np.inf))
                                    c_mult = float(c.get("quotient_multiplicity", 1.0))
                                    v_raw = float(
                                        raw_alternatives[a_idx].get("scores", {}).get(c["id"], 50.0)
                                    )
                                    if not np.isfinite(v_raw):
                                        mag_c = 1e6
                                    elif v_raw < c_min:
                                        mag_c = c_min - v_raw
                                    elif v_raw > c_max:
                                        mag_c = v_raw - c_max
                                    else:
                                        mag_c = 0.0
                                    total_mag += c_mult * mag_c
                                alt_state_overrides[(a_idx, qid)] = -total_mag / max(m_sum, 1e-15)
                            else:
                                alt_state_overrides[(a_idx, qid)] = 0.0

            criteria = head_criteria + synthesized_tail
        else:
            criteria = raw_criteria

        # Create Objectives & Constraints for each criterion
        crit_indices = {}
        for idx, crit in enumerate(criteria):
            cid = crit["id"]
            crit_indices[cid] = idx
            
            # Objective
            complex_obj.add_primitive(Objective(
                id=f"obj_{cid}",
                name=f"Maximize {crit['name']}",
                direction=OptimizationDirection.MAXIMIZE,
                weight=float(crit.get("weight", 1.0)),
                target_value=float(crit.get("max_val", 100.0))
            ))

            # Constraint if bounds exist
            if "min_val" in crit or "max_val" in crit:
                sev_enum = self._resolve_severity(crit.get("severity", ConstraintSeverity.HARD))
                q_mult = float(crit.get("quotient_multiplicity", 1.0))
                complex_obj.add_primitive(Constraint(
                    id=f"con_{cid}",
                    name=f"Bound {crit['name']}",
                    lower_bound=float(crit.get("min_val", -np.inf)),
                    upper_bound=float(crit.get("max_val", np.inf)),
                    severity=sev_enum,
                    metadata={"quotient_multiplicity": q_mult} if q_mult != 1.0 else {},
                ))

        # Create Options for alternatives
        for a_idx, alt in enumerate(alt_meta_copies):
            aid = alt["id"]
            scores_vec = []
            for crit in criteria:
                cid = crit["id"]
                if (a_idx, cid) in alt_state_overrides:
                    val = alt_state_overrides[(a_idx, cid)]
                else:
                    val = alt.get("scores", {}).get(cid, 50.0)
                scores_vec.append(float(val))

            complex_obj.add_primitive(Option(
                id=f"opt_{aid}",
                name=alt["name"],
                stalk_dim=len(scores_vec),
                initial_params=np.array(scores_vec, dtype=np.float64),
                estimated_cost_m=alt.get("cost_m", 0.0),
                metadata=alt
            ))

            # Wire edges to constraints
            for crit in criteria:
                cid = crit["id"]
                c_idx = crit_indices[cid]
                source_map = np.zeros((1, len(scores_vec)), dtype=np.float64)
                source_map[0, c_idx] = 1.0

                if f"con_{cid}" in complex_obj.primitives:
                    complex_obj.add_edge(
                        edge_id=f"edge_{aid}_to_con_{cid}",
                        source_id=f"opt_{aid}",
                        target_id=f"con_{cid}",
                        dim_edge=1,
                        source_map=source_map.copy(),
                        target_map=np.array([[1.0]]),
                        weight=float(crit.get("weight", 1.0)),
                        edge_type="constraint_check"
                    )

        return complex_obj

    def export_to_daosoft(self, complex_obj: SheafDecisionComplex, report: DecisionEvaluationReport) -> dict[str, Any]:
        """
        Exports a SheafDecisionComplex and evaluation report back into DAOSoft JSON format.
        """
        criteria = []
        for p in complex_obj.primitives.values():
            if p.primitive_type == PrimitiveType.OBJECTIVE:
                criteria.append({
                    "id": p.id,
                    "name": p.name,
                    "weight": getattr(p, "weight", 1.0),
                    "target_value": getattr(p, "target_value", 1.0)
                })

        alternatives = []
        for p in complex_obj.primitives.values():
            if p.primitive_type == PrimitiveType.OPTION:
                alternatives.append({
                    "id": p.id,
                    "name": p.name,
                    "score": report.option_scores.get(p.id, 0.0),
                    "is_selected": (p.id == report.selected_option_id),
                    "trl": getattr(p, "trl", 6),
                    "mrl": getattr(p, "mrl", 6),
                    "state_vector": p.state_vector.tolist()
                })

        return {
            "platform": "SOL-Decide / DAOSoft Interoperability Engine",
            "study_name": complex_obj.name,
            "betti_0": report.beta_0,
            "betti_1": report.beta_1,
            "dirichlet_energy": report.dirichlet_energy,
            "selected_alternative": report.selected_option_id,
            "criteria": criteria,
            "alternatives": alternatives,
            "verification_status": "CERTIFIED" if report.is_feasible else "OBSTRUCTED"
        }
