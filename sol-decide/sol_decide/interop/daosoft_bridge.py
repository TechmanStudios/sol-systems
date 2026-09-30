"""
SOL-Decide: DAOSoft Interoperability & Bi-Directional Bridge
============================================================
Enables seamless data exchange with legacy DAOSoft COTS decision tools,
allowing SOL-Decide to either export structured packages into DAOSoft
or ingest legacy MAUT spreadsheets into living sheaf decision graphs.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import numpy as np

from ..core.primitives import (
    PrimitiveType,
    OptimizationDirection,
    ConstraintSeverity,
    Objective,
    Option,
    Constraint
)
from ..core.sheaf_decision_complex import SheafDecisionComplex, DecisionEvaluationReport


class DAOSoftBridge:
    """
    Bi-directional translator between DAOSoft tabular trade study formats
    and SOL-Decide SheafDecisionComplex graphs.
    """

    def ingest_daosoft_matrix(self, daosoft_data: Dict[str, Any], study_name: str = "DAOSoft_Study") -> SheafDecisionComplex:
        """
        Converts a DAOSoft MAUT trade study JSON into a SheafDecisionComplex.
        
        DAOSoft schema format:
        {
            "study_title": "...",
            "criteria": [
                {"id": "c1", "name": "Armor Protection", "weight": 0.35, "min_val": 40.0, "max_val": 100.0},
                ...
            ],
            "alternatives": [
                {"id": "a1", "name": "Diesel-Mechanical", "scores": {"c1": 75.0, ...}, "cost_m": 12.5},
                ...
            ]
        }
        """
        complex_obj = SheafDecisionComplex(name=daosoft_data.get("study_title", study_name))

        criteria = daosoft_data.get("criteria", [])
        alternatives = daosoft_data.get("alternatives", [])

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
                weight=crit.get("weight", 1.0),
                target_value=crit.get("max_val", 100.0)
            ))

            # Constraint if bounds exist
            if "min_val" in crit or "max_val" in crit:
                complex_obj.add_primitive(Constraint(
                    id=f"con_{cid}",
                    name=f"Bound {crit['name']}",
                    lower_bound=crit.get("min_val", -np.inf),
                    upper_bound=crit.get("max_val", np.inf),
                    severity=ConstraintSeverity.HARD
                ))

        # Create Options for alternatives
        for alt in alternatives:
            aid = alt["id"]
            scores_vec = []
            for crit in criteria:
                cid = crit["id"]
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
                        weight=crit.get("weight", 1.0),
                        edge_type="constraint_check"
                    )

        return complex_obj

    def export_to_daosoft(self, complex_obj: SheafDecisionComplex, report: DecisionEvaluationReport) -> Dict[str, Any]:
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
