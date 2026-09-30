"""
SOL-Decide: Sheaf-Theoretic Governed Agentic Decision Operating System
======================================================================
Vector 17 of the SOL Systems Continuum.

Provides schema-driven decision management for auditable trade studies
and acquisition decisions, powered by cellular sheaf cohomology,
7 Giants MoA structured elicitation, and dialectical adversarial verification.
"""

from .core import (
    PrimitiveType,
    OptimizationDirection,
    ConstraintSeverity,
    DecisionPrimitive,
    Objective,
    Option,
    Constraint,
    Assumption,
    Risk,
    BiasCheck,
    SheafDecisionComplex,
    SheafEdge,
    DecisionEvaluationReport,
    export_complex_to_dict,
    import_complex_from_dict,
    export_complex_to_json,
    import_complex_from_json
)
from .agentic import (
    SevenGiantsElicitor,
    ElicitationResult,
    ElicitationGiantReport,
    DialecticalAdversary,
    DialecticalBiasReport,
    SensitivityAblator,
    SensitivityReport,
    ParameterFlipThreshold
)
from .interop import (
    SysMLKerMLParser,
    SysMLBlockAST,
    DAOSoftBridge
)
from .delivery import (
    SignerReadyDecisionPackage,
    DecisionPackageCompiler,
    EvidenceEntry,
    SignerAuthorizationGate,
    DifferentialDeltaEngine,
    DifferentialDecisionDelta,
    OperationalShock
)
from .demonstrations import (
    build_ngcv_trade_study,
    run_demonstration_1,
    run_demonstration_2
)

__version__ = "1.0.0"

__all__ = [
    "PrimitiveType",
    "OptimizationDirection",
    "ConstraintSeverity",
    "DecisionPrimitive",
    "Objective",
    "Option",
    "Constraint",
    "Assumption",
    "Risk",
    "BiasCheck",
    "SheafDecisionComplex",
    "SheafEdge",
    "DecisionEvaluationReport",
    "export_complex_to_dict",
    "import_complex_from_dict",
    "export_complex_to_json",
    "import_complex_from_json",
    "SevenGiantsElicitor",
    "ElicitationResult",
    "ElicitationGiantReport",
    "DialecticalAdversary",
    "DialecticalBiasReport",
    "SensitivityAblator",
    "SensitivityReport",
    "ParameterFlipThreshold",
    "SysMLKerMLParser",
    "SysMLBlockAST",
    "DAOSoftBridge",
    "SignerReadyDecisionPackage",
    "DecisionPackageCompiler",
    "EvidenceEntry",
    "SignerAuthorizationGate",
    "DifferentialDeltaEngine",
    "DifferentialDecisionDelta",
    "OperationalShock",
    "build_ngcv_trade_study",
    "run_demonstration_1",
    "run_demonstration_2"
]
