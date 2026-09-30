"""
SOL-Decide: SysML 2.0 / KerML AST Parser & Ingestion Bridge
============================================================
Translates OMG Systems Modeling Language (SysML 2.0) and Kernel Modeling
Language (KerML) models into SheafDecisionComplex topologies.

Mapping Formulation:
-------------------
1. SysML 'part def' / 'part usage'       --> Option primitive with state vector stalk F(v)
2. SysML 'constraint def' / 'usage'      --> Constraint primitive with [lower_bound, upper_bound]
3. SysML 'requirement def' / 'usage'     --> Objective / Constraint primitive
4. SysML 'attribute def'                 --> Stalk channel coordinate
5. SysML 'allocate' / 'connection' / 'satisfy' --> Directed SheafEdge with linear restriction map
"""

from dataclasses import dataclass, field
import re
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from ..core.primitives import (
    PrimitiveType,
    OptimizationDirection,
    ConstraintSeverity,
    Objective,
    Option,
    Constraint,
    Assumption
)
from ..core.sheaf_decision_complex import SheafDecisionComplex


@dataclass
class SysMLBlockAST:
    """Represents a parsed SysML 2.0 element."""
    element_type: str  # part, constraint, requirement, attribute, connection
    name: str
    id: str
    attributes: Dict[str, float] = field(default_factory=dict)
    connections: List[Tuple[str, str]] = field(default_factory=list)
    docstring: str = ""


class SysMLKerMLParser:
    """
    Parses textual SysML 2.0 / KerML blocks or structured JSON metamodels
    into a mathematically validated SheafDecisionComplex.
    """

    def parse_sysml_text(self, sysml_code: str, model_name: str = "SysML_Model") -> SheafDecisionComplex:
        """
        Parses textual SysML 2.0 declarations.
        
        Example syntax supported:
        part def DieselEngine {
            attribute weight_tons : Real = 8.5;
            attribute power_hp : Real = 1500.0;
        }
        constraint def WeightLimit {
            attribute max_weight : Real = 45.0;
        }
        requirement def SilentWatchReq {
            attribute min_hours : Real = 6.0;
        }
        """
        complex_obj = SheafDecisionComplex(name=model_name)
        lines = sysml_code.splitlines()
        
        current_block: Optional[Dict[str, Any]] = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("//"):
                continue

            # Detect block start: part def, constraint def, requirement def
            part_match = re.match(r"(part|constraint|requirement)\s+def\s+(\w+)\s*\{?", line)
            if part_match:
                b_type, b_name = part_match.groups()
                current_block = {
                    "type": b_type,
                    "name": b_name,
                    "id": f"sysml_{b_name.lower()}",
                    "attrs": {}
                }
                continue

            # Detect attribute declaration
            attr_match = re.match(r"attribute\s+(\w+)\s*:\s*\w+\s*=\s*([0-9\.\-]+)\s*;", line)
            if attr_match and current_block is not None:
                attr_name, attr_val = attr_match.groups()
                current_block["attrs"][attr_name] = float(attr_val)
                continue

            # Detect block closing
            if "}" in line and current_block is not None:
                b_type = current_block["type"]
                b_id = current_block["id"]
                b_name = current_block["name"]
                attrs = current_block["attrs"]

                if b_type == "part":
                    vals = list(attrs.values()) if attrs else [1.0]
                    complex_obj.add_primitive(Option(
                        id=b_id,
                        name=b_name,
                        stalk_dim=len(vals),
                        initial_params=np.array(vals, dtype=np.float64),
                        metadata={"attributes": attrs, "sysml_type": "part"}
                    ))
                elif b_type == "constraint":
                    upper = attrs.get("max_weight", attrs.get("upper", np.inf))
                    lower = attrs.get("min_val", attrs.get("lower", -np.inf))
                    complex_obj.add_primitive(Constraint(
                        id=b_id,
                        name=b_name,
                        lower_bound=lower,
                        upper_bound=upper,
                        severity=ConstraintSeverity.HARD,
                        metadata={"attributes": attrs, "sysml_type": "constraint"}
                    ))
                elif b_type == "requirement":
                    min_val = attrs.get("min_hours", attrs.get("target", 1.0))
                    complex_obj.add_primitive(Objective(
                        id=b_id,
                        name=b_name,
                        direction=OptimizationDirection.MAXIMIZE,
                        target_value=min_val,
                        metadata={"attributes": attrs, "sysml_type": "requirement"}
                    ))

                current_block = None

        return complex_obj

    def parse_kerml_json(self, kerml_dict: Dict[str, Any], model_name: str = "KerML_Model") -> SheafDecisionComplex:
        """
        Ingests OMG KerML structured JSON AST models.
        """
        complex_obj = SheafDecisionComplex(name=model_name)

        # Ingest elements
        for elem in kerml_dict.get("elements", []):
            e_type = elem.get("kerml_type", "Part")
            e_id = elem["id"]
            e_name = elem.get("name", e_id)
            attrs = elem.get("attributes", {})

            if e_type in ["Part", "Item"]:
                vals = list(attrs.values()) if attrs else [1.0]
                complex_obj.add_primitive(Option(
                    id=e_id,
                    name=e_name,
                    stalk_dim=len(vals),
                    initial_params=np.array(vals, dtype=np.float64),
                    trl=elem.get("trl", 6),
                    mrl=elem.get("mrl", 6),
                    metadata=elem
                ))
            elif e_type in ["Constraint", "ConstraintBlock"]:
                complex_obj.add_primitive(Constraint(
                    id=e_id,
                    name=e_name,
                    lower_bound=elem.get("lower_bound", -np.inf),
                    upper_bound=elem.get("upper_bound", np.inf),
                    severity=ConstraintSeverity(elem.get("severity", "hard")),
                    metadata=elem
                ))
            elif e_type in ["Requirement", "Objective"]:
                complex_obj.add_primitive(Objective(
                    id=e_id,
                    name=e_name,
                    direction=OptimizationDirection(elem.get("direction", "maximize")),
                    target_value=elem.get("target_value", 1.0),
                    weight=elem.get("weight", 1.0),
                    metadata=elem
                ))
            elif e_type in ["Assumption"]:
                complex_obj.add_primitive(Assumption(
                    id=e_id,
                    name=e_name,
                    baseline_value=elem.get("baseline_value", 1.0),
                    uncertainty_sigma=elem.get("uncertainty_sigma", 0.05),
                    metadata=elem
                ))

        # Ingest relationships / allocations
        for rel in kerml_dict.get("relationships", []):
            src_id = rel["source_id"]
            tgt_id = rel["target_id"]
            if src_id in complex_obj.primitives and tgt_id in complex_obj.primitives:
                s_map = np.array(rel["source_map"]) if "source_map" in rel else None
                t_map = np.array(rel["target_map"]) if "target_map" in rel else None
                complex_obj.add_edge(
                    edge_id=rel["id"],
                    source_id=src_id,
                    target_id=tgt_id,
                    dim_edge=rel.get("dim_edge"),
                    source_map=s_map,
                    target_map=t_map,
                    weight=rel.get("weight", 1.0),
                    edge_type=rel.get("type", "allocation"),
                    description=rel.get("description", "")
                )

        return complex_obj
