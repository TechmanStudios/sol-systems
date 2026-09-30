"""
SOL-Decide: Schema Serialization & Validation
=============================================
Provides JSON-Schema and dictionary export/import for SheafDecisionComplex,
fulfilling Task 1 Schema Deliverable requirements.
"""

import json
from typing import Dict, Any, List, Optional
import numpy as np

from .primitives import (
    PrimitiveType,
    OptimizationDirection,
    ConstraintSeverity,
    Objective,
    Option,
    Constraint,
    Assumption,
    Risk,
    BiasCheck
)
from .sheaf_decision_complex import SheafDecisionComplex, SheafEdge


def export_complex_to_dict(complex_obj: SheafDecisionComplex) -> Dict[str, Any]:
    """Serializes a SheafDecisionComplex into a JSON-compliant dictionary."""
    nodes = []
    for vid in complex_obj.vertex_order:
        p = complex_obj.primitives[vid]
        item = p.to_dict()
        if p.primitive_type == PrimitiveType.OBJECTIVE:
            item["direction"] = getattr(p, "direction", OptimizationDirection.MAXIMIZE).value
            item["weight"] = getattr(p, "weight", 1.0)
            item["target_value"] = getattr(p, "target_value", 1.0)
        elif p.primitive_type == PrimitiveType.OPTION:
            item["trl"] = getattr(p, "trl", 6)
            item["mrl"] = getattr(p, "mrl", 6)
            item["estimated_cost_m"] = getattr(p, "estimated_cost_m", 0.0)
        elif p.primitive_type == PrimitiveType.CONSTRAINT:
            item["severity"] = getattr(p, "severity", ConstraintSeverity.HARD).value
            item["lower_bound"] = float(getattr(p, "lower_bound", -np.inf))
            item["upper_bound"] = float(getattr(p, "upper_bound", np.inf))
            item["tolerance"] = float(getattr(p, "tolerance", 1e-4))
        elif p.primitive_type == PrimitiveType.ASSUMPTION:
            item["baseline_value"] = float(getattr(p, "baseline_value", 1.0))
            item["uncertainty_sigma"] = float(getattr(p, "uncertainty_sigma", 0.05))
            item["decay_rate_per_month"] = float(getattr(p, "decay_rate_per_month", 0.01))
            item["months_elapsed"] = float(getattr(p, "months_elapsed", 0.0))
        elif p.primitive_type == PrimitiveType.RISK:
            item["probability"] = float(getattr(p, "probability", 0.1))
            item["impact"] = float(getattr(p, "impact", 0.5))
            item["mitigated"] = bool(getattr(p, "mitigated", False))
        elif p.primitive_type == PrimitiveType.BIAS_CHECK:
            item["bias_category"] = getattr(p, "bias_category", "confirmation_bias")
            item["is_refuted"] = bool(getattr(p, "is_refuted", False))
        nodes.append(item)

    edges = []
    for eid in complex_obj.edge_order:
        e = complex_obj.edges[eid]
        edges.append({
            "id": e.id,
            "source_id": e.source_id,
            "target_id": e.target_id,
            "dim_edge": e.dim_edge,
            "source_map": e.source_map.tolist(),
            "target_map": e.target_map.tolist(),
            "weight": float(e.weight),
            "description": e.description,
            "edge_type": e.edge_type
        })

    return {
        "name": complex_obj.name,
        "zero_tolerance": complex_obj.zero_tolerance,
        "nodes": nodes,
        "edges": edges
    }


def import_complex_from_dict(data: Dict[str, Any]) -> SheafDecisionComplex:
    """Reconstructs a SheafDecisionComplex from a serialized dictionary."""
    complex_obj = SheafDecisionComplex(
        name=data.get("name", "RestoredComplex"),
        zero_tolerance=data.get("zero_tolerance", 1e-7)
    )

    for item in data.get("nodes", []):
        ptype = PrimitiveType(item["primitive_type"])
        state_vec = np.array(item.get("state_vector", [0.0]), dtype=np.float64)
        
        if ptype == PrimitiveType.OBJECTIVE:
            direction = OptimizationDirection(item.get("direction", "maximize"))
            prim = Objective(
                id=item["id"],
                name=item["name"],
                direction=direction,
                weight=item.get("weight", 1.0),
                target_value=item.get("target_value", 1.0),
                units=item.get("units", "utility"),
                description=item.get("description", ""),
                metadata=item.get("metadata")
            )
        elif ptype == PrimitiveType.OPTION:
            prim = Option(
                id=item["id"],
                name=item["name"],
                stalk_dim=item.get("stalk_dim", len(state_vec)),
                initial_params=state_vec,
                trl=item.get("trl", 6),
                mrl=item.get("mrl", 6),
                estimated_cost_m=item.get("estimated_cost_m", 0.0),
                units=item.get("units", "metric_vector"),
                description=item.get("description", ""),
                metadata=item.get("metadata")
            )
        elif ptype == PrimitiveType.CONSTRAINT:
            severity = ConstraintSeverity(item.get("severity", "hard"))
            prim = Constraint(
                id=item["id"],
                name=item["name"],
                lower_bound=item.get("lower_bound", -np.inf),
                upper_bound=item.get("upper_bound", np.inf),
                severity=severity,
                tolerance=item.get("tolerance", 1e-4),
                units=item.get("units", "units"),
                description=item.get("description", ""),
                metadata=item.get("metadata")
            )
        elif ptype == PrimitiveType.ASSUMPTION:
            prim = Assumption(
                id=item["id"],
                name=item["name"],
                baseline_value=item.get("baseline_value", 1.0),
                uncertainty_sigma=item.get("uncertainty_sigma", 0.05),
                decay_rate_per_month=item.get("decay_rate_per_month", 0.01),
                units=item.get("units", "units"),
                description=item.get("description", ""),
                source_reference=item.get("source_reference", ""),
                metadata=item.get("metadata")
            )
            prim.months_elapsed = item.get("months_elapsed", 0.0)
        elif ptype == PrimitiveType.RISK:
            prim = Risk(
                id=item["id"],
                name=item["name"],
                probability=item.get("probability", 0.1),
                impact=item.get("impact", 0.5),
                units=item.get("units", "risk_score"),
                description=item.get("description", ""),
                metadata=item.get("metadata")
            )
            prim.mitigated = item.get("mitigated", False)
        elif ptype == PrimitiveType.BIAS_CHECK:
            prim = BiasCheck(
                id=item["id"],
                name=item["name"],
                bias_category=item.get("bias_category", "confirmation_bias"),
                units=item.get("units", "strain_norm"),
                description=item.get("description", ""),
                metadata=item.get("metadata")
            )
            prim.is_refuted = item.get("is_refuted", False)
        else:
            continue
            
        prim.set_state(state_vec)
        complex_obj.add_primitive(prim)

    for edge in data.get("edges", []):
        complex_obj.add_edge(
            edge_id=edge["id"],
            source_id=edge["source_id"],
            target_id=edge["target_id"],
            dim_edge=edge.get("dim_edge"),
            source_map=np.array(edge["source_map"], dtype=np.float64),
            target_map=np.array(edge["target_map"], dtype=np.float64),
            weight=edge.get("weight", 1.0),
            description=edge.get("description", ""),
            edge_type=edge.get("edge_type", "allocation")
        )

    return complex_obj


def export_complex_to_json(complex_obj: SheafDecisionComplex, indent: int = 2) -> str:
    """Exports complex to formatted JSON string."""
    return json.dumps(export_complex_to_dict(complex_obj), indent=indent)


def import_complex_from_json(json_str: str) -> SheafDecisionComplex:
    """Imports complex from JSON string."""
    return import_complex_from_dict(json.loads(json_str))
