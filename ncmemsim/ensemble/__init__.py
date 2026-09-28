"""Stochastic ensemble contracts and execution tools."""

from .distributions import (
    ConstantDistribution,
    DistributionSpec,
    FiniteDiscreteDistribution,
    LogNormalDistribution,
    NormalDistribution,
    TruncatedNormalDistribution,
    UniformDistribution,
    distribution_from_dict,
)

from .spec import PhysicalDomain, StochasticVariable
from .specification import EnsembleSpec
from .rng import RNGSpec
from .sampling import (
    EnsembleSample,
    SamplingError,
    SamplingSpec,
    sample_distribution,
    SampleGenerationError,
    SampleManifest,
    generate_sample_manifest,
)
from .correlation import (
    IndependentDependence,
    MatrixCorrelation,
)
from .realization import (
    RealizationIdentity,
    SampleDomainValidationError,
    validate_sample_domain,
    AppliedRealization,
    RealizationAssignment,
    apply_sample_to_context,
)
from .execution import (
    EnsembleExecutionResult,
    RealizationExecutionPoint,
    execute_sample_manifest,
)
from .metrics import (
    EnsembleMetricAnalysisResult,
    EnsembleMetricPointResult,
    analyze_ensemble_execution,
)
from .statistics import (
    EnsemblePopulationStatistics,
    EnsembleStatisticsSpec,
    MetricPopulationSummary,
    summarize_ensemble_metrics,
)
from .feasibility import (
    EnsembleFeasibilitySummary,
    NominalMetricComparison,
    NominalMetricReference,
    summarize_ensemble_feasibility,
)
from .dtco import (
    EnsembleDTCOStudy,
    EnsembleScalarDefinition,
    EnsembleScalarEvaluation,
    EnsembleScalarKind,
    evaluate_ensemble_scalar,
)

__all__ = [
    "ConstantDistribution",
    "DistributionSpec",
    "FiniteDiscreteDistribution",
    "LogNormalDistribution",
    "NormalDistribution",
    "TruncatedNormalDistribution",
    "UniformDistribution",
    "PhysicalDomain",
    "StochasticVariable",
    "EnsembleSpec",
    "distribution_from_dict",
    "RNGSpec",
    "SamplingError",
    "sample_distribution",
    "EnsembleSample",
    "IndependentDependence",
    "SamplingSpec",
    "SampleGenerationError",
    "SampleManifest",
    "generate_sample_manifest",
    "MatrixCorrelation",
    "RealizationIdentity",
    "SampleDomainValidationError",
    "validate_sample_domain",
    "AppliedRealization",
    "RealizationAssignment",
    "apply_sample_to_context",
    "EnsembleExecutionResult",
    "RealizationExecutionPoint",
    "execute_sample_manifest",
    "EnsembleMetricAnalysisResult",
    "EnsembleMetricPointResult",
    "analyze_ensemble_execution",
    "EnsemblePopulationStatistics",
    "EnsembleStatisticsSpec",
    "MetricPopulationSummary",
    "summarize_ensemble_metrics",
    "EnsembleFeasibilitySummary",
    "NominalMetricComparison",
    "NominalMetricReference",
    "summarize_ensemble_feasibility",
    "EnsembleDTCOStudy",
    "EnsembleScalarDefinition",
    "EnsembleScalarEvaluation",
    "EnsembleScalarKind",
    "evaluate_ensemble_scalar",
]
