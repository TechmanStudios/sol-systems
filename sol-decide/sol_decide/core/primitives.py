"""
SOL-Decide Core Decision Primitives
===================================
Formalizes the six fundamental primitives of acquisition decision-making
as first-class topological objects in a cellular sheaf complex:
    V = V_objectives U V_options U V_constraints U V_assumptions U V_risks U V_bias_checks

Mathematical Invariant:
-----------------------
Each primitive v in V is assigned a typed stalk vector space F(v) = R^{d_v},
equipped with physical units, lower/upper bounds, uncertainty distributions,
and evidence provenance.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import numpy as np


class PrimitiveType(str, Enum):
    """The six core decision primitives."""
    OBJECTIVE = "objective"
    OPTION = "option"
    CONSTRAINT = "constraint"
    ASSUMPTION = "assumption"
    RISK = "risk"
    BIAS_CHECK = "bias_check"


class OptimizationDirection(str, Enum):
    """Optimization objective direction."""
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    TARGET = "target"


class ConstraintSeverity(str, Enum):
    """Severity level of constraint violations."""
    HARD = "hard"          # Cannot be violated; produces topological obstruction (beta_1 > 0)
    SOFT = "soft"          # Penalized in objective Dirichlet energy
    THRESHOLD = "threshold"# Go/no-go gate threshold


@dataclass
class DecisionPrimitive:
    """Base class for all decision complex vertices."""
    id: str
    name: str
    primitive_type: PrimitiveType
    description: str = ""
    stalk_dim: int = 1
    state_vector: np.ndarray = field(default_factory=lambda: np.zeros(1, dtype=np.float64))
    units: str = "dimensionless"
    source_reference: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if len(self.state_vector) != self.stalk_dim:
            self.state_vector = np.resize(self.state_vector, self.stalk_dim).astype(np.float64)

    def set_state(self, val: np.ndarray) -> None:
        """Update stalk state vector."""
        arr = np.asarray(val, dtype=np.float64)
        if arr.shape != (self.stalk_dim,):
            arr = np.resize(arr, self.stalk_dim)
        self.state_vector = arr

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "primitive_type": self.primitive_type.value,
            "description": self.description,
            "stalk_dim": self.stalk_dim,
            "state_vector": self.state_vector.tolist(),
            "units": self.units,
            "source_reference": self.source_reference,
            "metadata": self.metadata
        }


@dataclass
class Objective(DecisionPrimitive):
    """Operational or strategic objective."""
    direction: OptimizationDirection = OptimizationDirection.MAXIMIZE
    weight: float = 1.0
    target_value: float = 1.0

    def __init__(
        self,
        id: str,
        name: str,
        direction: OptimizationDirection = OptimizationDirection.MAXIMIZE,
        weight: float = 1.0,
        target_value: float = 1.0,
        units: str = "utility",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            id=id,
            name=name,
            primitive_type=PrimitiveType.OBJECTIVE,
            description=description,
            stalk_dim=1,
            state_vector=np.array([target_value], dtype=np.float64),
            units=units,
            metadata=metadata or {}
        )
        self.direction = direction
        self.weight = weight
        self.target_value = target_value


@dataclass
class Option(DecisionPrimitive):
    """Candidate alternative under trade study consideration."""
    trl: int = 6  # Technology Readiness Level (1-9)
    mrl: int = 6  # Manufacturing Readiness Level (1-9)
    estimated_cost_m: float = 0.0
    is_active: bool = True

    def __init__(
        self,
        id: str,
        name: str,
        stalk_dim: int = 4,
        initial_params: Optional[np.ndarray] = None,
        trl: int = 6,
        mrl: int = 6,
        estimated_cost_m: float = 0.0,
        units: str = "metric_vector",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        init_vec = initial_params if initial_params is not None else np.zeros(stalk_dim)
        super().__init__(
            id=id,
            name=name,
            primitive_type=PrimitiveType.OPTION,
            description=description,
            stalk_dim=stalk_dim,
            state_vector=np.asarray(init_vec, dtype=np.float64),
            units=units,
            metadata=metadata or {}
        )
        self.trl = trl
        self.mrl = mrl
        self.estimated_cost_m = estimated_cost_m
        self.is_active = True


@dataclass
class Constraint(DecisionPrimitive):
    """Physical, operational, or budgetary boundary constraint."""
    severity: ConstraintSeverity = ConstraintSeverity.HARD
    lower_bound: float = -np.inf
    upper_bound: float = np.inf
    tolerance: float = 1e-4

    def __init__(
        self,
        id: str,
        name: str,
        lower_bound: float = -np.inf,
        upper_bound: float = np.inf,
        severity: ConstraintSeverity = ConstraintSeverity.HARD,
        tolerance: float = 1e-4,
        units: str = "units",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            id=id,
            name=name,
            primitive_type=PrimitiveType.CONSTRAINT,
            description=description,
            stalk_dim=1,
            state_vector=np.array([upper_bound if upper_bound < np.inf else lower_bound], dtype=np.float64),
            units=units,
            metadata=metadata or {}
        )
        self.severity = severity
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.tolerance = tolerance

    def evaluate_violation(self, candidate_val: float) -> Tuple[bool, float]:
        """Returns (is_violated, violation_magnitude)."""
        if candidate_val < self.lower_bound - self.tolerance:
            return True, self.lower_bound - candidate_val
        if candidate_val > self.upper_bound + self.tolerance:
            return True, candidate_val - self.upper_bound
        return False, 0.0


@dataclass
class Assumption(DecisionPrimitive):
    """Operational, environmental, or supply chain baseline premise."""
    baseline_value: float = 0.0
    uncertainty_sigma: float = 0.05
    decay_rate_per_month: float = 0.01  # Rate of assumption staleness
    months_elapsed: float = 0.0

    def __init__(
        self,
        id: str,
        name: str,
        baseline_value: float = 1.0,
        uncertainty_sigma: float = 0.05,
        decay_rate_per_month: float = 0.01,
        units: str = "units",
        description: str = "",
        source_reference: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            id=id,
            name=name,
            primitive_type=PrimitiveType.ASSUMPTION,
            description=description,
            stalk_dim=1,
            state_vector=np.array([baseline_value], dtype=np.float64),
            units=units,
            source_reference=source_reference,
            metadata=metadata or {}
        )
        self.baseline_value = baseline_value
        self.uncertainty_sigma = uncertainty_sigma
        self.decay_rate_per_month = decay_rate_per_month
        self.months_elapsed = 0.0

    def advance_time(self, months: float) -> float:
        """Simulates assumption staleness and drift over program horizon."""
        self.months_elapsed += months
        effective_sigma = self.uncertainty_sigma * (1.0 + self.decay_rate_per_month * self.months_elapsed)
        return effective_sigma


@dataclass
class Risk(DecisionPrimitive):
    """Programmatic, technical, or lifecycle risk item."""
    probability: float = 0.1  # 0.0 to 1.0
    impact: float = 0.5       # 0.0 to 1.0
    mitigated: bool = False

    def __init__(
        self,
        id: str,
        name: str,
        probability: float = 0.1,
        impact: float = 0.5,
        units: str = "risk_score",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        score = float(np.clip(probability * impact, 0.0, 1.0))
        super().__init__(
            id=id,
            name=name,
            primitive_type=PrimitiveType.RISK,
            description=description,
            stalk_dim=1,
            state_vector=np.array([score], dtype=np.float64),
            units=units,
            metadata=metadata or {}
        )
        self.probability = probability
        self.impact = impact
        self.mitigated = False

    @property
    def severity_score(self) -> float:
        return self.probability * self.impact if not self.mitigated else (self.probability * self.impact * 0.2)


@dataclass
class BiasCheck(DecisionPrimitive):
    """Adversarial anti-bias verification probe."""
    bias_category: str = "confirmation_bias"  # e.g. vendor_lockin, optimism_bias, sunk_cost
    adversarial_strain_injected: float = 0.0
    is_refuted: bool = False
    witness_vector: Optional[np.ndarray] = None

    def __init__(
        self,
        id: str,
        name: str,
        bias_category: str = "confirmation_bias",
        units: str = "strain_norm",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            id=id,
            name=name,
            primitive_type=PrimitiveType.BIAS_CHECK,
            description=description,
            stalk_dim=1,
            state_vector=np.zeros(1, dtype=np.float64),
            units=units,
            metadata=metadata or {}
        )
        self.bias_category = bias_category
        self.adversarial_strain_injected = 0.0
        self.is_refuted = False
        self.witness_vector = None
