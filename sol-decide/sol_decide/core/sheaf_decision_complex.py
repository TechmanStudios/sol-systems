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
    edge_type: str = "allocation"  # allocation, constraint_check, assumption_link, risk_mitigation, subsystem_interface
    edge_offset: Optional[np.ndarray] = None  # Optional bilateral affine transfer claim b_e in F(e)


@dataclass
class SheafFace:
    """2-cell plaquette (oriented cycle of edges) defining the 1-coboundary operator delta^1: C^1 -> C^2."""
    id: str
    edge_ids: List[str]
    orientations: List[float]  # +1.0 or -1.0 per edge in edge_ids
    dim_face: int = 1
    weight: float = 1.0
    description: str = ""


@dataclass
class HodgeDecompositionReport:
    """
    Orthogonal Discrete Hodge Decomposition of a 1-cochain omega in C^1(X; F)
    via the 1-Hodge Laplacian Delta^1 = delta^0 (delta^0)^T + (delta^1)^T delta^1:
        omega = omega_exact (+) omega_coexact (+) omega_harmonic
    where:
      - omega_exact in im(delta^0) (resolvable via local 0-cochain vertex shifts)
      - omega_coexact in im((delta^1)^T) (curl around filled 2-cell plaquettes)
      - omega_harmonic in ker(Delta^1) ~= H^1(X; F) (global topological obstruction)
    """
    beta_0: int
    beta_1: int
    cochain_1: np.ndarray
    exact_component: np.ndarray
    coexact_component: np.ndarray
    harmonic_component: np.ndarray
    total_norm: float
    exact_norm: float
    coexact_norm: float
    harmonic_norm: float
    orthogonality_error: float
    laplacian_1_harmonic_residual: float
    cycle_holonomy_residual: float
    harmonic_basis: np.ndarray  # Shape: (D_E, beta_1)
    edge_harmonic_norms: Dict[str, float]
    edge_exact_norms: Dict[str, float]
    edge_coexact_norms: Dict[str, float]
    frustrated_cycle_edges: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "beta_0": self.beta_0,
            "beta_1": self.beta_1,
            "total_norm": round(self.total_norm, 6),
            "exact_norm": round(self.exact_norm, 6),
            "coexact_norm": round(self.coexact_norm, 6),
            "harmonic_norm": round(self.harmonic_norm, 6),
            "orthogonality_error": float(self.orthogonality_error),
            "laplacian_1_harmonic_residual": float(self.laplacian_1_harmonic_residual),
            "cycle_holonomy_residual": round(self.cycle_holonomy_residual, 6),
            "edge_harmonic_norms": {k: round(v, 6) for k, v in self.edge_harmonic_norms.items()},
            "edge_exact_norms": {k: round(v, 6) for k, v in self.edge_exact_norms.items()},
            "edge_coexact_norms": {k: round(v, 6) for k, v in self.edge_coexact_norms.items()},
            "frustrated_cycle_edges": list(self.frustrated_cycle_edges),
        }


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
        self.baseline_states: Dict[str, np.ndarray] = {}
        self.vertex_order: List[str] = []
        self.vertex_offsets: Dict[str, int] = {}
        
        self.edges: Dict[str, SheafEdge] = {}
        self.edge_order: List[str] = []
        self.edge_offsets: Dict[str, int] = {}

        self.faces: Dict[str, SheafFace] = {}
        self.face_order: List[str] = []
        self.face_offsets: Dict[str, int] = {}
        
        self._total_v_dim: int = 0
        self._total_e_dim: int = 0
        self._total_f_dim: int = 0
        self._coboundary_cache: Optional[np.ndarray] = None
        self._coboundary_1_cache: Optional[np.ndarray] = None
        self._laplacian_cache: Optional[np.ndarray] = None
        self._hodge_laplacian_1_cache: Optional[np.ndarray] = None

    def add_primitive(self, primitive: DecisionPrimitive) -> None:
        """Register a decision primitive vertex into the complex."""
        if primitive.id in self.primitives:
            raise ValueError(f"Primitive {primitive.id} already exists in complex")
        self.primitives[primitive.id] = primitive
        self.baseline_states[primitive.id] = primitive.state_vector.copy()
        self.vertex_order.append(primitive.id)
        self._invalidate_cache()

    def get_effective_option_state(self, option_id: str) -> np.ndarray:
        """
        Computes the effective state vector of an Option by propagating deviations
        from connected Assumption and Risk stalks through their linear restriction maps:
            x_opt_eff = x_opt - sum_{e=(u -> opt)} w_e * F_{opt <= e}^+ * F_{u <= e} * (x_u - x_u^(0))
        At baseline (x_u == x_u^(0)), returns x_opt unchanged.
        """
        opt = self.primitives[option_id]
        eff_state = opt.state_vector.copy()

        for edge in self.edges.values():
            if edge.target_id == option_id and edge.edge_type in ("assumption_link", "risk_mitigation"):
                src = self.primitives[edge.source_id]
                base_src = self.baseline_states.get(
                    src.id,
                    np.array([getattr(src, "baseline_value", float(src.state_vector[0]))], dtype=np.float64)
                )
                delta_src = src.state_vector - base_src
                if float(np.linalg.norm(delta_src)) > 1e-12:
                    # Map source deviation into edge stalk, then pull back to option stalk
                    edge_impulse = edge.source_map @ delta_src
                    opt_shift = la.pinv(edge.target_map) @ edge_impulse
                    eff_state = eff_state - float(edge.weight) * opt_shift

        return eff_state

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
        edge_type: str = "allocation",
        edge_offset: Optional[np.ndarray] = None,
    ) -> SheafEdge:
        """
        Add a directed edge between two primitives with linear restriction maps
        and optional bilateral affine transfer offset b_e in F(e).
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

        parsed_offset: Optional[np.ndarray] = None
        if edge_offset is not None:
            parsed_offset = np.asarray(edge_offset, dtype=np.float64).reshape(-1)
            if parsed_offset.shape != (dim_edge,):
                raise ValueError(f"edge_offset shape {parsed_offset.shape} != ({dim_edge},)")

        edge = SheafEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            dim_edge=dim_edge,
            source_map=source_map,
            target_map=target_map,
            weight=weight,
            description=description,
            edge_type=edge_type,
            edge_offset=parsed_offset,
        )
        self.edges[edge_id] = edge
        self.edge_order.append(edge_id)
        self._invalidate_cache()
        return edge

    def add_face(
        self,
        face_id: str,
        edge_ids: List[str],
        orientations: Optional[List[float]] = None,
        weight: float = 1.0,
        description: str = "",
    ) -> SheafFace:
        """
        Registers a 2-cell plaquette (oriented cycle of edges) into the complex
        for 1-coboundary delta^1: C^1(X; F) -> C^2(X; F) and coexact Hodge analysis.
        """
        if face_id in self.faces:
            raise ValueError(f"Face {face_id} already exists")
        if not edge_ids:
            raise ValueError("Face must reference at least one edge")
        for eid in edge_ids:
            if eid not in self.edges:
                raise KeyError(f"Edge {eid} referenced by face {face_id} not found")

        dims = {self.edges[eid].dim_edge for eid in edge_ids}
        if len(dims) != 1:
            raise ValueError(f"All edges in face {face_id} must share the same stalk dimension")
        dim_face = next(iter(dims))

        if orientations is None:
            orientations = [1.0 for _ in edge_ids]
        elif len(orientations) != len(edge_ids):
            raise ValueError("orientations length must match edge_ids length")

        face = SheafFace(
            id=face_id,
            edge_ids=list(edge_ids),
            orientations=[float(o) for o in orientations],
            dim_face=dim_face,
            weight=float(weight),
            description=description,
        )
        self.faces[face_id] = face
        self.face_order.append(face_id)
        self._invalidate_cache()
        return face

    def _invalidate_cache(self) -> None:
        self._coboundary_cache = None
        self._coboundary_1_cache = None
        self._laplacian_cache = None
        self._hodge_laplacian_1_cache = None

    def _compile_layout(self) -> None:
        """Compute memory layout offsets for vertices, edges, and 2-cell faces."""
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

        self.face_offsets.clear()
        f_offset = 0
        for fid in self.face_order:
            self.face_offsets[fid] = f_offset
            f_offset += self.faces[fid].dim_face
        self._total_f_dim = f_offset

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

    @property
    def total_face_dim(self) -> int:
        if self._coboundary_cache is None:
            self._compile_layout()
        return self._total_f_dim

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

    def build_coboundary_1(self) -> np.ndarray:
        """
        Builds the 1st Coboundary matrix delta^1: C^1(X; F) -> C^2(X; F) of shape (D_F, D_E).
        """
        if self._coboundary_1_cache is not None:
            return self._coboundary_1_cache

        self._compile_layout()
        D_F = self._total_f_dim
        D_E = self._total_e_dim

        if D_F == 0 or D_E == 0:
            self._coboundary_1_cache = np.zeros((D_F, D_E), dtype=np.float64)
            return self._coboundary_1_cache

        delta_1 = np.zeros((D_F, D_E), dtype=np.float64)
        for fid in self.face_order:
            face = self.faces[fid]
            f_idx = self.face_offsets[fid]
            d_f = face.dim_face
            sqrt_wf = np.sqrt(face.weight)
            for eid, orient in zip(face.edge_ids, face.orientations):
                e_idx = self.edge_offsets[eid]
                d_e = self.edges[eid].dim_edge
                delta_1[f_idx : f_idx + d_f, e_idx : e_idx + d_e] += (
                    sqrt_wf * float(orient) * np.eye(d_f, d_e, dtype=np.float64)
                )

        self._coboundary_1_cache = delta_1
        return delta_1

    def build_laplacian(self) -> np.ndarray:
        """
        Builds the 0th Sheaf Laplacian matrix Delta^0 = (delta^0)^T delta^0 of shape (D_V, D_V).
        """
        if self._laplacian_cache is not None:
            return self._laplacian_cache

        delta = self.build_coboundary()
        lap = delta.T @ delta
        # Guarantee strict symmetry
        lap = 0.5 * (lap + lap.T)
        self._laplacian_cache = lap
        return lap

    def build_hodge_laplacian_1(self) -> np.ndarray:
        """
        Builds the 1-Hodge Sheaf Laplacian matrix Delta^1 = delta^0 (delta^0)^T + (delta^1)^T delta^1
        of shape (D_E, D_E) acting on 1-cochains in C^1(X; F).
        """
        if self._hodge_laplacian_1_cache is not None:
            return self._hodge_laplacian_1_cache

        delta_0 = self.build_coboundary()
        delta_1 = self.build_coboundary_1()
        lap_1 = (delta_0 @ delta_0.T) + (delta_1.T @ delta_1)
        lap_1 = 0.5 * (lap_1 + lap_1.T)
        self._hodge_laplacian_1_cache = lap_1
        return lap_1

    def compute_betti_numbers(self) -> Tuple[int, int]:
        """
        Computes (beta_0, beta_1):
        beta_0 = dim ker(delta^0) = D_V - rank(delta^0)
        beta_1 = dim H^1(X; F) = dim(ker(delta^1) / im(delta^0)) = D_E - rank(delta^0) - rank(delta^1_orth)
        """
        delta = self.build_coboundary()
        D_E, D_V = delta.shape
        if D_E == 0 or D_V == 0:
            return D_V, 0

        # Singular value decomposition for robust numerical rank
        U0, s0, _ = la.svd(delta, full_matrices=True)
        rank_delta = int(np.sum(s0 > self.zero_tolerance))

        rank_delta_1 = 0
        delta_1 = self.build_coboundary_1()
        if delta_1.shape[0] > 0:
            U_exact = U0[:, :rank_delta]
            B1_orth = delta_1.T - U_exact @ (U_exact.T @ delta_1.T)
            _, s1, _ = la.svd(B1_orth, full_matrices=False)
            rank_delta_1 = int(np.sum(s1 > self.zero_tolerance))

        beta_0 = max(0, D_V - rank_delta)
        beta_1 = max(0, D_E - rank_delta - rank_delta_1)
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

    def assemble_edge_offsets(self) -> np.ndarray:
        """Assembles weighted bilateral affine edge offsets sqrt(w_e) * b_e in C^1(X; F)."""
        self._compile_layout()
        b = np.zeros(self._total_e_dim, dtype=np.float64)
        for eid in self.edge_order:
            edge = self.edges[eid]
            if edge.edge_offset is not None:
                offset = self.edge_offsets[eid]
                dim = edge.dim_edge
                b[offset : offset + dim] = np.sqrt(edge.weight) * edge.edge_offset
        return b

    def evaluate_coboundary(self, x: Optional[np.ndarray] = None) -> np.ndarray:
        """Computes the coboundary discrepancy 1-cochain omega = delta^0 x - b in C^1(X; F)."""
        if x is None:
            x = self.assemble_cochain()
        delta = self.build_coboundary()
        b = self.assemble_edge_offsets()
        return (delta @ x) - b

    def compute_dirichlet_energy(self, x: Optional[np.ndarray] = None) -> float:
        """Computes total Dirichlet Energy: E(x) = 1/2 ||delta^0 x - b||^2."""
        dx = self.evaluate_coboundary(x)
        return 0.5 * float(np.sum(dx ** 2))

    def hodge_decomposition(
        self,
        cochain_1: Optional[np.ndarray] = None,
        tolerance: float = 1e-4,
    ) -> HodgeDecompositionReport:
        """
        Executes Orthogonal Discrete Hodge Decomposition of a 1-cochain omega in C^1(X; F)
        using the 1-Hodge Laplacian Delta^1 = delta^0 (delta^0)^T + (delta^1)^T delta^1:
            omega = omega_exact (+) omega_coexact (+) omega_harmonic
        Isolates global topological obstructions in ker(Delta^1) ~= H^1(X; F) and
        identifies the exact frustrated interface cycle edges.
        """
        omega = (
            np.asarray(cochain_1, dtype=np.float64).reshape(-1)
            if cochain_1 is not None
            else self.evaluate_coboundary()
        )
        delta_0 = self.build_coboundary()
        delta_1 = self.build_coboundary_1()
        lap_1 = self.build_hodge_laplacian_1()
        D_E, D_V = delta_0.shape

        if D_E == 0:
            empty = np.zeros(0, dtype=np.float64)
            return HodgeDecompositionReport(
                beta_0=D_V,
                beta_1=0,
                cochain_1=empty,
                exact_component=empty,
                coexact_component=empty,
                harmonic_component=empty,
                total_norm=0.0,
                exact_norm=0.0,
                coexact_norm=0.0,
                harmonic_norm=0.0,
                orthogonality_error=0.0,
                laplacian_1_harmonic_residual=0.0,
                cycle_holonomy_residual=0.0,
                harmonic_basis=np.zeros((0, 0), dtype=np.float64),
                edge_harmonic_norms={},
                edge_exact_norms={},
                edge_coexact_norms={},
                frustrated_cycle_edges=[],
            )

        # 1. Exact subspace im(delta^0) via orthonormal SVD basis
        U0, s0, _ = la.svd(delta_0, full_matrices=True)
        r0 = int(np.sum(s0 > self.zero_tolerance))
        U_exact = U0[:, :r0]
        omega_exact = U_exact @ (U_exact.T @ omega) if r0 > 0 else np.zeros_like(omega)

        # 2. Coexact subspace im((delta^1)^T) orthogonalized against im(delta^0)
        r1 = 0
        if delta_1.shape[0] > 0:
            B1_orth = (
                delta_1.T - U_exact @ (U_exact.T @ delta_1.T)
                if r0 > 0
                else delta_1.T.copy()
            )
            U1, s1, _ = la.svd(B1_orth, full_matrices=False)
            r1 = int(np.sum(s1 > self.zero_tolerance))
            U_coexact = U1[:, :r1]
            omega_coexact = (
                U_coexact @ (U_coexact.T @ (omega - omega_exact))
                if r1 > 0
                else np.zeros_like(omega)
            )
        else:
            omega_coexact = np.zeros_like(omega)

        # 3. Harmonic subspace ker(Delta^1) = (im(delta^0) (+) im((delta^1)^T))^perp
        omega_harmonic = omega - omega_exact - omega_coexact

        beta_0 = max(0, D_V - r0)
        beta_1 = max(0, D_E - r0 - r1)

        eigs, eigvecs = la.eigh(lap_1)
        null_mask = np.abs(eigs) <= max(self.zero_tolerance, 1e-6)
        harmonic_basis = eigvecs[:, null_mask]

        # Orthogonality & Laplacian kernel residual checks
        norm_sq = max(1.0, float(la.norm(omega) ** 2))
        dot_eh = abs(float(np.dot(omega_exact, omega_harmonic))) / norm_sq
        dot_ch = abs(float(np.dot(omega_coexact, omega_harmonic))) / norm_sq
        dot_ec = abs(float(np.dot(omega_exact, omega_coexact))) / norm_sq
        orth_err = max(dot_eh, dot_ch, dot_ec)
        lap_res = float(la.norm(lap_1 @ omega_harmonic))


        edge_harm_norms: Dict[str, float] = {}
        edge_exact_norms: Dict[str, float] = {}
        edge_coexact_norms: Dict[str, float] = {}
        frustrated_edges: List[str] = []

        for eid in self.edge_order:
            e_idx = self.edge_offsets[eid]
            d_e = self.edges[eid].dim_edge
            h_norm = float(la.norm(omega_harmonic[e_idx : e_idx + d_e]))
            ex_norm = float(la.norm(omega_exact[e_idx : e_idx + d_e]))
            co_norm = float(la.norm(omega_coexact[e_idx : e_idx + d_e]))
            edge_harm_norms[eid] = h_norm
            edge_exact_norms[eid] = ex_norm
            edge_coexact_norms[eid] = co_norm
            if h_norm > tolerance:
                frustrated_edges.append(eid)

        if harmonic_basis.shape[1] > 0:
            # Signed projection onto primary harmonic cycle mode scaled by sqrt(cycle length)
            n_cycle = max(1, len(frustrated_edges))
            cycle_holonomy = float(np.sqrt(n_cycle) * float(harmonic_basis[:, 0].T @ omega))
        else:
            cycle_holonomy = 0.0

        return HodgeDecompositionReport(
            beta_0=beta_0,
            beta_1=beta_1,
            cochain_1=omega,
            exact_component=omega_exact,
            coexact_component=omega_coexact,
            harmonic_component=omega_harmonic,
            total_norm=float(la.norm(omega)),
            exact_norm=float(la.norm(omega_exact)),
            coexact_norm=float(la.norm(omega_coexact)),
            harmonic_norm=float(la.norm(omega_harmonic)),
            orthogonality_error=orth_err,
            laplacian_1_harmonic_residual=lap_res,
            cycle_holonomy_residual=cycle_holonomy,
            harmonic_basis=harmonic_basis,
            edge_harmonic_norms=edge_harm_norms,
            edge_exact_norms=edge_exact_norms,
            edge_coexact_norms=edge_coexact_norms,
            frustrated_cycle_edges=frustrated_edges,
        )

    def audit_obstructions(
        self,
        x: Optional[np.ndarray] = None,
        target_option_id: Optional[str] = None,
        tolerance: float = 1e-3
    ) -> List[Dict[str, Any]]:
        """
        Isolates individual edges experiencing metric strain / contradiction:
        - For constraint_check edges: tests constraint inequality violation.
        - For allocation/dependency/subsystem_interface edges: tests ||(delta^0 x - b)_e|| > tolerance.
        If target_option_id is specified, only evaluates edges associated with that option,
        global system primitives, or global cross-subsystem interfaces.
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
            # unless the edge is a global cross-subsystem interface edge
            if target_option_id is not None and edge.edge_type != "subsystem_interface":
                if src.primitive_type == PrimitiveType.OPTION and src.id != target_option_id:
                    continue
                if tgt.primitive_type == PrimitiveType.OPTION and tgt.id != target_option_id:
                    continue

            if edge.edge_type in ["objective_coupling", "informational"]:
                continue

            if edge.edge_type == "constraint_check" and tgt.primitive_type == PrimitiveType.CONSTRAINT:
                con = tgt
                src_state = (
                    self.get_effective_option_state(src.id)
                    if src.primitive_type == PrimitiveType.OPTION
                    else src.state_vector
                )
                projected = edge.source_map @ src_state
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
            
            opt_state = self.get_effective_option_state(opt.id)

            # Base utility
            opt_score = 100.0
            
            # Evaluate connected Objectives
            for obj in objectives:
                has_edge = False
                for edge in self.edges.values():
                    if edge.source_id == opt.id and edge.target_id == obj.id:
                        has_edge = True
                        projected = edge.source_map @ opt_state
                        val = float(projected[0])
                        if getattr(obj, "direction", OptimizationDirection.MAXIMIZE) == OptimizationDirection.MAXIMIZE:
                            opt_score += obj.weight * val
                        elif getattr(obj, "direction", OptimizationDirection.MAXIMIZE) == OptimizationDirection.MINIMIZE:
                            opt_score -= obj.weight * val
                        else:
                            opt_score -= obj.weight * abs(val - obj.target_value)

                # Fallback to metadata scores or channel_index if no direct objective edge exists
                if not has_edge and "scores" in opt.metadata:
                    cid = obj.id.replace("obj_", "")
                    if cid in opt.metadata["scores"]:
                        val = float(opt.metadata["scores"][cid])
                        opt_score += obj.weight * val
                elif not has_edge and "raw_channel" in getattr(obj, "metadata", {}):
                    ch_idx = int(obj.metadata["raw_channel"])
                    if 0 <= ch_idx < len(opt_state):
                        val = float(opt_state[ch_idx])
                        direction = getattr(obj, "direction", OptimizationDirection.MAXIMIZE)
                        if direction == OptimizationDirection.MAXIMIZE:
                            opt_score += obj.weight * val
                        elif direction == OptimizationDirection.MINIMIZE:
                            opt_score -= obj.weight * val
                        else:
                            opt_score -= obj.weight * abs(val - obj.target_value)
                elif not has_edge and "channel_index" in getattr(obj, "metadata", {}):
                    ch_idx = int(obj.metadata["channel_index"])
                    if 0 <= ch_idx < len(opt_state):
                        val = float(opt_state[ch_idx])
                        scale = max(1.0, abs(float(obj.target_value)))
                        direction = getattr(obj, "direction", OptimizationDirection.MAXIMIZE)
                        if direction == OptimizationDirection.MAXIMIZE:
                            opt_score += 100.0 * obj.weight * (val / scale)
                        elif direction == OptimizationDirection.MINIMIZE:
                            opt_score -= 100.0 * obj.weight * (val / scale)
                        else:
                            opt_score -= 100.0 * obj.weight * (abs(val - obj.target_value) / scale)

            # Penalize constraint violations
            for con in constraints:
                # Find edges connecting opt -> con
                for edge in self.edges.values():
                    if edge.source_id == opt.id and edge.target_id == con.id:
                        projected = edge.source_map @ opt_state
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
