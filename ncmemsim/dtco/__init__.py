"""Design-space exploration and DTCO specifications."""

from .binding import (
    BindingApplicationError,
    apply_device_binding,
    apply_device_bindings,
    apply_experiment_design_point,
)
from .operating import (
    AppliedExperimentPoint,
    OperatingBindingError,
    OperatingProtocol,
    apply_experiment_point,
    apply_operating_binding,
    apply_operating_bindings,
)
from .spec import (
    BindingScope,
    DesignVariable,
    DesignVariableRole,
    ExperimentSpec,
    ParameterBinding,
    ScalarValue,
)

from .sweep import (
    SweepPoint,
    SweepPointResult,
    SweepResult,
    iter_cartesian_points,
    run_cartesian_sweep,
)

from .metrics import (
    ConstraintEvaluation,
    ConstraintOperator,
    MetricAnalysisResult,
    MetricAnalysisSpec,
    MetricConstraint,
    MetricDefinition,
    MetricPointResult,
    ObjectiveDirection,
    analyze_sweep,
)

from .pareto import (
    ParetoAnalysisResult,
    ParetoAnalysisSpec,
    ParetoPointResult,
    analyze_pareto,
)

from .sensitivity import (
    SensitivityEligibility,
    SensitivityAnalysisSpec,
    SensitivityEdge,
    SensitivityAnalysisResult,
    analyze_sensitivity,
)

from .reporting import DTCOReport, build_dtco_report, write_dtco_report

__all__ = [
    "DTCOReport",
    "build_dtco_report",
    "write_dtco_report",
    "SensitivityEligibility",
    "SensitivityAnalysisSpec",
    "SensitivityEdge",
    "SensitivityAnalysisResult",
    "analyze_sensitivity",

    "ParetoAnalysisResult",
    "ParetoAnalysisSpec",
    "ParetoPointResult",
    "analyze_pareto",
    "ConstraintEvaluation",
    "ConstraintOperator",
    "MetricAnalysisResult",
    "MetricAnalysisSpec",
    "MetricConstraint",
    "MetricDefinition",
    "MetricPointResult",
    "ObjectiveDirection",
    "analyze_sweep",

    "SweepPoint", "SweepPointResult", "SweepResult",
    "iter_cartesian_points", "run_cartesian_sweep",
    "AppliedExperimentPoint",
    "BindingApplicationError",
    "BindingScope",
    "DesignVariable",
    "DesignVariableRole",
    "ExperimentSpec",
    "OperatingBindingError",
    "OperatingProtocol",
    "ParameterBinding",
    "ScalarValue",
    "apply_device_binding",
    "apply_device_bindings",
    "apply_experiment_design_point",
    "apply_experiment_point",
    "apply_operating_binding",
    "apply_operating_bindings",
]

from .variation import (VariationKind, VariationProvenance, UniformVariation,
                        TruncatedNormalVariation, VariationDefinition)

__all__ += ["VariationKind", "VariationProvenance", "UniformVariation",
            "TruncatedNormalVariation", "VariationDefinition"]

from .sampling import SamplingSpec, SampleManifest, SamplingError, sample_variations

__all__ += ["SamplingSpec", "SampleManifest", "SamplingError", "sample_variations"]

from .propagation import SamplePoint, SamplePointResult, PropagationResult, propagate_samples

__all__ += ["SamplePoint", "SamplePointResult", "PropagationResult", "propagate_samples"]

from .sample_analysis import SampleAnalysisSpec, SampleMetricPointResult, SampleAnalysisResult, analyze_samples

__all__ += ["SampleAnalysisSpec", "SampleMetricPointResult", "SampleAnalysisResult", "analyze_samples"]
