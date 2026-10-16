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

    def parse_sysml_text(
        self,
        sysml_code: str,
        model_name: str = "SysML_Model",
        auto_wire_sheaf_edges: bool = True,
    ) -> SheafDecisionComplex:
        """
        Parses textual SysML 2.0 declarations (`part def`, `constraint def`,
        `requirement def`, `assumption def`) into a `SheafDecisionComplex`.
        When `auto_wire_sheaf_edges=True` and no explicit edges are present,
        automatically synthesizes calibrated `sheaf_consensus` and
        `constraint_check` restriction morphisms across matching stalk channels.
        """
        complex_obj = SheafDecisionComplex(name=model_name)
        lines = sysml_code.splitlines()

        current_block: Optional[Dict[str, Any]] = None
        parsed_parts: List[Option] = []
        parsed_constraints: List[Tuple[Constraint, int]] = []
        parsed_objectives: List[Tuple[Objective, int]] = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith("//"):
                continue

            # Detect package name header if present
            pkg_match = re.match(r"package\s+([\w_]+)\s*\{?", line)
            if pkg_match and current_block is None and model_name == "SysML_Model":
                complex_obj.name = pkg_match.group(1)
                continue

            # Detect block start: part def, constraint def, requirement def, assumption def
            part_match = re.match(r"(part|constraint|requirement|assumption)\s+def\s+(\w+)\s*\{?", line)
            if part_match:
                b_type, b_name = part_match.groups()
                current_block = {
                    "type": b_type,
                    "name": b_name,
                    "id": f"sysml_{b_name.lower()}",
                    "attrs": {},
                    "str_attrs": {},
                }
                continue

            # Detect numeric attribute declaration
            attr_match = re.match(r"attribute\s+(\w+)\s*:\s*\w+\s*=\s*([0-9\.\-]+)\s*;", line)
            if attr_match and current_block is not None:
                attr_name, attr_val = attr_match.groups()
                current_block["attrs"][attr_name] = float(attr_val)
                continue

            # Detect string attribute declaration
            str_attr_match = re.match(r'attribute\s+(\w+)\s*:\s*\w+\s*=\s*"([^"]+)"\s*;', line)
            if str_attr_match and current_block is not None:
                attr_name, attr_val = str_attr_match.groups()
                current_block["str_attrs"][attr_name] = attr_val
                continue

            # Detect block closing
            if "}" in line and current_block is not None:
                b_type = current_block["type"]
                b_id = current_block["id"]
                b_name = current_block["name"]
                attrs = current_block["attrs"]
                str_attrs = current_block["str_attrs"]

                if b_type == "part":
                    meta_keys = {"cost", "trl", "mrl"}
                    stalk_attrs = {k: v for k, v in attrs.items() if k not in meta_keys}
                    vals = list(stalk_attrs.values()) if stalk_attrs else [1.0]
                    opt = Option(
                        id=b_id,
                        name=b_name,
                        stalk_dim=len(vals),
                        initial_params=np.array(vals, dtype=np.float64),
                        estimated_cost_m=float(attrs.get("cost", 25.0)),
                        trl=int(attrs.get("trl", 7)),
                        mrl=int(attrs.get("mrl", 7)),
                        description=str_attrs.get("doc", f"SysML 2.0 part def {b_name}"),
                        metadata={"attributes": stalk_attrs, "sysml_type": "part"},
                    )
                    complex_obj.add_primitive(opt)
                    parsed_parts.append(opt)
                elif b_type == "constraint":
                    upper = attrs.get("max_weight", attrs.get("upper", attrs.get("max_val", np.inf)))
                    lower = attrs.get("min_val", attrs.get("lower", -np.inf))
                    ch_idx = int(attrs.get("channel", len(parsed_constraints)))
                    sev_str = str_attrs.get("severity", "hard").lower()
                    sev = ConstraintSeverity.HARD if sev_str == "hard" else ConstraintSeverity.SOFT
                    con = Constraint(
                        id=b_id,
                        name=b_name,
                        lower_bound=lower,
                        upper_bound=upper,
                        severity=sev,
                        units=str_attrs.get("units", "units"),
                        description=str_attrs.get("doc", f"SysML 2.0 constraint def {b_name}"),
                        metadata={"attributes": attrs, "sysml_type": "constraint", "channel": ch_idx},
                    )
                    complex_obj.add_primitive(con)
                    parsed_constraints.append((con, ch_idx))
                elif b_type == "requirement":
                    target_val = attrs.get("min_hours", attrs.get("target", attrs.get("target_value", 1.0)))
                    weight_val = float(attrs.get("weight", 1.0))
                    ch_idx = int(attrs.get("channel", len(parsed_objectives)))
                    dir_str = str_attrs.get("direction", "maximize").lower()
                    direction = (
                        OptimizationDirection.MINIMIZE
                        if dir_str == "minimize"
                        else OptimizationDirection.MAXIMIZE
                    )
                    obj = Objective(
                        id=b_id,
                        name=b_name,
                        direction=direction,
                        target_value=target_val,
                        weight=weight_val,
                        units=str_attrs.get("units", "units"),
                        description=str_attrs.get("doc", f"SysML 2.0 requirement def {b_name}"),
                        metadata={
                            "attributes": attrs,
                            "sysml_type": "requirement",
                            "channel": ch_idx,
                            "raw_channel": ch_idx,
                        },
                    )
                    complex_obj.add_primitive(obj)
                    parsed_objectives.append((obj, ch_idx))
                elif b_type == "assumption":
                    ass = Assumption(
                        id=b_id,
                        name=b_name,
                        baseline_value=float(attrs.get("baseline_value", 1.0)),
                        uncertainty_sigma=float(attrs.get("uncertainty_sigma", 0.05)),
                        decay_rate_per_month=float(attrs.get("decay_rate", 0.01)),
                        units=str_attrs.get("units", "units"),
                        description=str_attrs.get("doc", f"SysML 2.0 assumption def {b_name}"),
                        metadata={"attributes": attrs, "sysml_type": "assumption"},
                    )
                    complex_obj.add_primitive(ass)

                current_block = None

        # Auto-wire calibrated sheaf restriction maps if multi-channel parts + constraints/objectives exist
        if auto_wire_sheaf_edges and parsed_parts and (parsed_constraints or parsed_objectives):
            stalk_dim = parsed_parts[0].stalk_dim
            if stalk_dim >= 1 and all(p.stalk_dim == stalk_dim for p in parsed_parts):
                if parsed_constraints:
                    for con, ch_idx in parsed_constraints:
                        c = ch_idx % stalk_dim
                        proj = np.zeros((1, stalk_dim), dtype=np.float64)
                        proj[0, c] = 1.0
                        for opt in parsed_parts:
                            complex_obj.add_edge(
                                edge_id=f"e_sysml_{opt.id}_to_{con.id}",
                                source_id=opt.id,
                                target_id=con.id,
                                dim_edge=1,
                                source_map=proj,
                                target_map=np.array([[1.0]], dtype=np.float64),
                                weight=1.0,
                                edge_type="constraint_check",
                                description=f"SysML v2 constraint allocation {opt.id}[{c}] -> {con.id}",
                            )
                else:
                    for obj, ch_idx in parsed_objectives:
                        c = ch_idx % stalk_dim
                        proj = np.zeros((1, stalk_dim), dtype=np.float64)
                        proj[0, c] = 1.0
                        for opt in parsed_parts:
                            complex_obj.add_edge(
                                edge_id=f"e_sysml_{opt.id}_to_{obj.id}",
                                source_id=opt.id,
                                target_id=obj.id,
                                dim_edge=1,
                                source_map=proj,
                                target_map=np.array([[1.0]], dtype=np.float64),
                                weight=1.0,
                                edge_type="objective_coupling",
                                description=f"SysML v2 requirement satisfaction {opt.id}[{c}] -> {obj.id}",
                            )

        return complex_obj

    def export_complex_to_sysml_text(self, complex_obj: SheafDecisionComplex) -> str:
        """
        Exports a `SheafDecisionComplex` (including post-shock mutated option stalks)
        back into canonical SysML 2.0 textual syntax.
        """
        lines = [
            f"// Auto-generated by SOL-Decide SysML 2.0 / KerML Interop Bridge",
            f"package {re.sub(r'[^a-zA-Z0-9_]', '_', complex_obj.name)} {{",
            "",
        ]
        for p in complex_obj.primitives.values():
            clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", p.name)
            if p.primitive_type == PrimitiveType.OPTION and isinstance(p, Option):
                lines.append(f"    part def {clean_name} {{")
                attr_names = list(p.metadata.get("attributes", {}).keys())
                for idx, val in enumerate(p.state_vector):
                    aname = attr_names[idx] if idx < len(attr_names) else f"channel_{idx}"
                    lines.append(f"        attribute {aname} : Real = {float(val):.4f};")
                lines.append(f"        attribute cost : Real = {float(p.estimated_cost_m):.2f};")
                lines.append(f"        attribute trl : Real = {int(p.trl)};")
                lines.append(f"        attribute mrl : Real = {int(p.mrl)};")
                lines.append("    }")
            elif p.primitive_type == PrimitiveType.CONSTRAINT and isinstance(p, Constraint):
                lines.append(f"    constraint def {clean_name} {{")
                if np.isfinite(p.lower_bound):
                    lines.append(f"        attribute lower : Real = {float(p.lower_bound):.4f};")
                if np.isfinite(p.upper_bound):
                    lines.append(f"        attribute upper : Real = {float(p.upper_bound):.4f};")
                ch = p.metadata.get("channel", 0)
                lines.append(f"        attribute channel : Real = {int(ch)};")
                lines.append("    }")
            elif p.primitive_type == PrimitiveType.OBJECTIVE and isinstance(p, Objective):
                lines.append(f"    requirement def {clean_name} {{")
                lines.append(f"        attribute target : Real = {float(p.target_value):.4f};")
                lines.append(f"        attribute weight : Real = {float(p.weight):.4f};")
                lines.append(f'        attribute direction : String = "{p.direction.value}";')
                ch = p.metadata.get("channel", 0)
                lines.append(f"        attribute channel : Real = {int(ch)};")
                lines.append("    }")
            elif p.primitive_type == PrimitiveType.ASSUMPTION and isinstance(p, Assumption):
                lines.append(f"    assumption def {clean_name} {{")
                lines.append(f"        attribute baseline_value : Real = {float(p.baseline_value):.4f};")
                lines.append(f"        attribute uncertainty_sigma : Real = {float(p.uncertainty_sigma):.4f};")
                lines.append("    }")
            lines.append("")
        lines.append("}")
        return "\n".join(lines)

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
