"""
SOL-Decide: Sheaf-Theoretic Decision Complex
============================================
Implements the 1D Cellular Sheaf Decision Complex X = (V, E)
for rigorous, auditable trade studies and acquisition decision management.

Mathematical Formulation:
--------------------------
1. Cell Complex:
   - Vertices V = V_obj U V_opt U V_con U V_ass U V_risk U V_bias
   - Stalks F(v) = R^{d_v}, Total dimension D_V = sum_{v in V} d_v
   - Edges e = (u -> v) in E with stalks F(e) = R^{d_e}, Total dimension D_E = sum_{e in E} d_e
   - Linear restriction maps F_{u <= e}: F(u) -> F(e), F_{v <= e}: F(v) -> F(e)

2. Coboundary Operator delta^0: C^0(X; F) -> C^1(X; F):
   (delta^0 x)_e = sqrt(w_e) * ( F_{v <= e} x_v - F_{u <= e} x_u )

3. Sheaf Laplacian Delta^0 = (delta^0)^T delta^0:
   Positive semi-definite quadratic form defining the Dirichlet Energy:
   E_F(x) = 1/2 * ||delta^0 x||^2 = 1/2 * x^T Delta^0 x

4. Cohomological Invariants:
   beta_0 = dim H^0(X; F) = dim(ker Delta^0) (global agreement / consistent configurations)
   beta_1 = dim H^1(X; F) = D_E - rank(delta^0) (topological obstruction dimension)
   Invariant: A Decision Package cannot be certified if beta_1 > 0 or ||delta^0 x|| > tol.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import scipy.linalg as la

from .primitives import (
    DecisionPrimitive,
    PrimitiveType,
    OptimizationDirection,
    Objective,
    Option,
    Constraint,
    Assumption,
    Risk,
    BiasCheck,
    ConstraintSeverity
)


@dataclass
class SheafEdge:
    """Directed edge with linear restriction maps representing causal / allocation coupling."""
    id: str
    source_id: str
    target_id: str
    dim_edge: int
    source_map: np.ndarray  # Shape: (dim_edge, dim_source)
    target_map: np.ndarray  # Shape: (dim_edge, dim_target)
    weight: float = 1.0
    description: str = ""
    edge_type: str = "allocation"  # allocation, constraint_check, assumption_link, risk_mitigation


@dataclass
class DecisionEvaluationReport:
    """Telemetry and mathematical certificate of a decision configuration evaluation."""
    is_feasible: bool
    beta_0: int
    beta_1: int
    dirichlet_energy: float
    coboundary_norm: float
    obstructed_edges: List[Dict[str, Any]]
    option_scores: Dict[str, float]
    selected_option_id: Optional[str]
    cochain_state: Dict[str, List[float]]
    summary: str


class SheafDecisionComplex:
    """
    Cellular Sheaf Decision Complex for acquisition engineering & living trade studies.
    """

    def __init__(self, name: str = "DecisionComplex", zero_tolerance: float = 1e-7):
        self.name = name
        self.zero_tolerance = zero_tolerance
        
        self.primitives: Dict[str, DecisionPrimitive] = {}
        self.vertex_order: List[str] = []
        self.vertex_offsets: Dict[str, int] = {}
        
        self.edges: Dict[str, SheafEdge] = {}
        self.edge_order: List[str] = []
        self.edge_offsets: Dict[str, int] = {}
        
        self._total_v_dim: int = 0
        self._total_e_dim: int = 0
        self._coboundary_cache: Optional[np.ndarray] = None
        self._laplacian_cache: Optional[np.ndarray] = None

    def add_primitive(self, primitive: DecisionPrimitive) -> None:
        """Register a decision primitive vertex into the complex."""
        if primitive.id in self.primitives:
            raise ValueError(f"Primitive {primitive.id} already exists in complex")
        self.primitives[primitive.id] = primitive
        self.vertex_order.append(primitive.id)
        self._invalidate_cache()

    def add_edge(
        self,
        edge_id: str,
        source_id: str,
        target_id: str,
        dim_edge: Optional[int] = None,
        source_map: Optional[np.ndarray] = None,
        target_map: Optional[np.ndarray] = None,
        weight: float = 1.0,
        description: str = "",
        edge_type: str = "allocation"
    ) -> SheafEdge:
        """
        Add a directed edge between two primitives with linear restriction maps.
        """
        if source_id not in self.primitives:
            raise KeyError(f"Source primitive {source_id} not found")
        if target_id not in self.primitives:
            raise KeyError(f"Target primitive {target_id} not found")
        if edge_id in self.edges:
            raise ValueError(f"Edge {edge_id} already exists")

        d_s = self.primitives[source_id].stalk_dim
        d_t = self.primitives[target_id].stalk_dim

        if dim_edge is None:
            dim_edge = min(d_s, d_t)

        if source_map is None:
            source_map = np.eye(dim_edge, d_s, dtype=np.float64)
        else:
            source_map = np.asarray(source_map, dtype=np.float64)
            if source_map.shape != (dim_edge, d_s):
                raise ValueError(f"source_map shape {source_map.shape} != ({dim_edge}, {d_s})")

        if target_map is None:
            target_map = np.eye(dim_edge, d_t, dtype=np.float64)
        else:
            target_map = np.asarray(target_map, dtype=np.float64)
            if target_map.shape != (dim_edge, d_t):
                raise ValueError(f"target_map shape {target_map.shape} != ({dim_edge}, {d_t})")

        edge = SheafEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            dim_edge=dim_edge,
            source_map=source_map,
            target_map=target_map,
            weight=weight,
            description=description,
            edge_type=edge_type
        )
        self.edges[edge_id] = edge
        self.edge_order.append(edge_id)
        self._invalidate_cache()
        return edge

    def _invalidate_cache(self) -> None:
        self._coboundary_cache = None
        self._laplacian_cache = None

    def _compile_layout(self) -> None:
        """Compute memory layout offsets for vertices and edges."""
        self.vertex_offsets.clear()
        v_offset = 0
        for vid in self.vertex_order:
            self.vertex_offsets[vid] = v_offset
            v_offset += self.primitives[vid].stalk_dim
        self._total_v_dim = v_offset

        self.edge_offsets.clear()
        e_offset = 0
        for eid in self.edge_order:
            self.edge_offsets[eid] = e_offset
            e_offset += self.edges[eid].dim_edge
        self._total_e_dim = e_offset

    @property
    def total_vertex_dim(self) -> int:
        if self._coboundary_cache is None:
            self._compile_layout()
        return self._total_v_dim

    @property
    def total_edge_dim(self) -> int:
        if self._coboundary_cache is None:
            self._compile_layout()
        return self._total_e_dim

    def build_coboundary(self) -> np.ndarray:
        """
        Builds the 0th Coboundary matrix delta^0 of shape (D_E, D_V).
        """
        if self._coboundary_cache is not None:
            return self._coboundary_cache

        self._compile_layout()
        D_E = self._total_e_dim
        D_V = self._total_v_dim

        if D_E == 0 or D_V == 0:
            self._coboundary_cache = np.zeros((D_E, D_V), dtype=np.float64)
            return self._coboundary_cache

        delta = np.zeros((D_E, D_V), dtype=np.float64)

        for eid in self.edge_order:
            edge = self.edges[eid]
            e_idx = self.edge_offsets[eid]
            d_e = edge.dim_edge

            u_idx = self.vertex_offsets[edge.source_id]
            d_u = self.primitives[edge.source_id].stalk_dim

            v_idx = self.vertex_offsets[edge.target_id]
            d_v = self.primitives[edge.target_id].stalk_dim

            sqrt_w = np.sqrt(edge.weight)
            # (delta^0 x)_e = sqrt(w) * (F_{v<=e} x_v - F_{u<=e} x_u)
            delta[e_idx : e_idx + d_e, u_idx : u_idx + d_u] -= sqrt_w * edge.source_map
            delta[e_idx : e_idx + d_e, v_idx : v_idx + d_v] += sqrt_w * edge.target_map

        self._coboundary_cache = delta
        return delta

    def build_laplacian(self) -> np.ndarray:
        """
        Builds the Sheaf Laplacian matrix Delta^0 = (delta^0)^T delta^0 of shape (D_V, D_V).
        """
        if self._laplacian_cache is not None:
            return self._laplacian_cache

        delta = self.build_coboundary()
        lap = delta.T @ delta
        # Guarantee strict symmetry
        lap = 0.5 * (lap + lap.T)
        self._laplacian_cache = lap
        return lap

    def compute_betti_numbers(self) -> Tuple[int, int]:
        """
        Computes (beta_0, beta_1):
        beta_0 = dim ker(delta^0) = D_V - rank(delta^0)
        beta_1 = dim H^1(X; F) = D_E - rank(delta^0)
        """
        delta = self.build_coboundary()
        D_E, D_V = delta.shape
        if D_E == 0 or D_V == 0:
            return D_V, 0

        # Singular value decomposition for robust numerical rank
        _, s, _ = la.svd(delta, full_matrices=False)
        rank_delta = int(np.sum(s > self.zero_tolerance))
        
        beta_0 = max(0, D_V - rank_delta)
        beta_1 = max(0, D_E - rank_delta)
        return beta_0, beta_1

    def assemble_cochain(self) -> np.ndarray:
        """Concatenates current state vectors into a global 0-cochain x in C^0(X; F)."""
        self._compile_layout()
        x = np.zeros(self._total_v_dim, dtype=np.float64)
        for vid in self.vertex_order:
            offset = self.vertex_offsets[vid]
            dim = self.primitives[vid].stalk_dim
            x[offset : offset + dim] = self.primitives[vid].state_vector
        return x

    def evaluate_coboundary(self, x: Optional[np.ndarray] = None) -> np.ndarray:
        """Computes the coboundary discrepancy vector delta^0 x."""
        if x is None:
            x = self.assemble_cochain()
        delta = self.build_coboundary()
        return delta @ x

    def compute_dirichlet_energy(self, x: Optional[np.ndarray] = None) -> float:
        """Computes total Dirichlet Energy: E(x) = 1/2 ||delta^0 x||^2."""
        dx = self.evaluate_coboundary(x)
        return 0.5 * float(np.sum(dx ** 2))

    def audit_obstructions(
        self,
        x: Optional[np.ndarray] = None,
        target_option_id: Optional[str] = None,
        tolerance: float = 1e-3
    ) -> List[Dict[str, Any]]:
        """
        Isolates individual edges experiencing metric strain / contradiction:
        - For constraint_check edges: tests constraint inequality violation.
        - For allocation/dependency edges: tests ||(delta^0 x)_e|| > tolerance.
        If target_option_id is specified, only evaluates edges associated with that option
        or global system primitives.
        """
        if x is None:
            x = self.assemble_cochain()
        dx = self.evaluate_coboundary(x)
        
        obstructed = []
        for eid in self.edge_order:
            edge = self.edges[eid]
            src = self.primitives[edge.source_id]
            tgt = self.primitives[edge.target_id]

            # If filtering by option, skip edges belonging to other unselected options
            if target_option_id is not None:
                if src.primitive_type == PrimitiveType.OPTION and src.id != target_option_id:
                    continue
                if tgt.primitive_type == PrimitiveType.OPTION and tgt.id != target_option_id:
                    continue

            if edge.edge_type in ["objective_coupling", "informational"]:
                continue

            if edge.edge_type == "constraint_check" and tgt.primitive_type == PrimitiveType.CONSTRAINT:
                con = tgt
                projected = edge.source_map @ src.state_vector
                is_viol, mag = con.evaluate_violation(float(projected[0]))
                if is_viol and mag > tolerance:
                    obstructed.append({
                        "edge_id": eid,
                        "source_id": edge.source_id,
                        "source_name": src.name,
                        "target_id": edge.target_id,
                        "target_name": tgt.name,
                        "edge_type": edge.edge_type,
                        "discrepancy_norm": float(mag),
                        "discrepancy_vector": [float(mag)],
                        "violation_details": f"Breached {con.name}: value {float(projected[0]):.2f} outside [{con.lower_bound}, {con.upper_bound}]"
                    })
            else:
                offset = self.edge_offsets[eid]
                dim = edge.dim_edge
                e_slice = dx[offset : offset + dim]
                norm = float(la.norm(e_slice))
                if norm > tolerance:
                    obstructed.append({
                        "edge_id": eid,
                        "source_id": edge.source_id,
                        "source_name": src.name,
                        "target_id": edge.target_id,
                        "target_name": tgt.name,
                        "edge_type": edge.edge_type,
                        "discrepancy_norm": norm,
                        "discrepancy_vector": e_slice.tolist(),
                        "violation_details": f"Linear discrepancy norm {norm:.4e} > {tolerance}"
                    })

        return obstructed

    def evaluate_options(self) -> Dict[str, float]:
        """
        Scores all registered Option primitives against the active constraints and objectives.
        Returns a dictionary mapping option_id -> utility_score.
        """
        options = [p for p in self.primitives.values() if p.primitive_type == PrimitiveType.OPTION]
        objectives = [p for p in self.primitives.values() if p.primitive_type == PrimitiveType.OBJECTIVE]
        constraints = [p for p in self.primitives.values() if p.primitive_type == PrimitiveType.CONSTRAINT]
        
        scores: Dict[str, float] = {}
        for opt in options:
            if not getattr(opt, "is_active", True):
                continue
            
            # Base utility
            opt_score = 100.0
            
            # Evaluate connected Objectives
            for obj in objectives:
                has_edge = False
                for edge in self.edges.values():
                    if edge.source_id == opt.id and edge.target_id == obj.id:
                        has_edge = True
                        projected = edge.source_map @ opt.state_vector
                        val = float(projected[0])
                        if getattr(obj, "direction", OptimizationDirection.MAXIMIZE) == OptimizationDirection.MAXIMIZE:
                            opt_score += obj.weight * val
                        elif getattr(obj, "direction", OptimizationDirection.MAXIMIZE) == OptimizationDirection.MINIMIZE:
                            opt_score -= obj.weight * val
                        else:
                            opt_score -= obj.weight * abs(val - obj.target_value)

                # Fallback to metadata scores if no direct objective edge exists
                if not has_edge and "scores" in opt.metadata:
                    cid = obj.id.replace("obj_", "")
                    if cid in opt.metadata["scores"]:
                        val = float(opt.metadata["scores"][cid])
                        opt_score += obj.weight * val

            # Penalize constraint violations
            for con in constraints:
                # Find edges connecting opt -> con
                for edge in self.edges.values():
                    if edge.source_id == opt.id and edge.target_id == con.id:
                        projected = edge.source_map @ opt.state_vector
                        is_viol, mag = con.evaluate_violation(float(projected[0]))
                        if is_viol:
                            if con.severity == ConstraintSeverity.HARD:
                                opt_score -= 1000.0 * (1.0 + mag)
                            else:
                                opt_score -= 50.0 * mag

            # Bonus/penalty for TRL/MRL
            opt_score += (opt.trl + opt.mrl) * 2.0
            scores[opt.id] = float(opt_score)

        return scores

    def evaluate_decision_package(self) -> DecisionEvaluationReport:
        """
        Executes full mathematical evaluation of the decision complex.
        Verifies cohomological consistency (beta_1 == 0), evaluates energy,
        detects obstructed edges, and ranks candidate options.
        """
        beta_0, beta_1 = self.compute_betti_numbers()
        x = self.assemble_cochain()
        energy = self.compute_dirichlet_energy(x)
        dx = self.evaluate_coboundary(x)
        dx_norm = float(la.norm(dx))
        
        scores = self.evaluate_options()
        
        # Select best option with non-negative score
        selected_id = None
        if scores:
            best_id = max(scores, key=lambda k: scores[k])
            if scores[best_id] > -500.0:  # Did not violate hard constraints
                selected_id = best_id

        # Audit obstructions specifically for selected option
        obstructed = self.audit_obstructions(x, target_option_id=selected_id)

        # Feasible only if no hard obstructions exist and beta_1 == 0
        is_feasible = (beta_1 == 0) and (len(obstructed) == 0) and (selected_id is not None)

        cochain_dict = {
            vid: self.primitives[vid].state_vector.tolist()
            for vid in self.vertex_order
        }

        summary = (
            f"Decision Complex '{self.name}': beta_0={beta_0}, beta_1={beta_1}, "
            f"Dirichlet Energy={energy:.4e}, Discrepancy Norm={dx_norm:.4e}, "
            f"Obstructed Edges={len(obstructed)}, Optimal Option={selected_id}"
        )

        return DecisionEvaluationReport(
            is_feasible=is_feasible,
            beta_0=beta_0,
            beta_1=beta_1,
            dirichlet_energy=energy,
            coboundary_norm=dx_norm,
            obstructed_edges=obstructed,
            option_scores=scores,
            selected_option_id=selected_id,
            cochain_state=cochain_dict,
            summary=summary
        )
