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
]
