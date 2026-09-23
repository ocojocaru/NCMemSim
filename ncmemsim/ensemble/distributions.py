"""Immutable stochastic distribution contracts for Phase K."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from ..hashing import canonical_hash


def _number(value: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be numeric, excluding bool")

    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{label} must be finite") from exc

    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")

    return result


def _positive(value: float, label: str) -> float:
    result = _number(value, label)
    if result <= 0.0:
        raise ValueError(f"{label} must be strictly positive")
    return result


def _ordered_bounds(instance: Any) -> None:
    lower = _number(instance.lower, "lower")
    upper = _number(instance.upper, "upper")

    if lower >= upper:
        raise ValueError("lower must be strictly less than upper")

    object.__setattr__(instance, "lower", lower)
    object.__setattr__(instance, "upper", upper)


@dataclass(frozen=True)
class ConstantDistribution:
    """Degenerate distribution used for explicit zero variation."""

    value: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _number(self.value, "value"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": "constant",
            "value": self.value,
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class NormalDistribution:
    """Arithmetic normal distribution."""

    mean: float
    standard_deviation: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "mean", _number(self.mean, "mean"))
        object.__setattr__(
            self,
            "standard_deviation",
            _positive(self.standard_deviation, "standard_deviation"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": "normal",
            "mean": self.mean,
            "standard_deviation": self.standard_deviation,
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class TruncatedNormalDistribution:
    """Underlying arithmetic normal truncated to [lower, upper]."""

    mean: float
    standard_deviation: float
    lower: float
    upper: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "mean", _number(self.mean, "mean"))
        object.__setattr__(
            self,
            "standard_deviation",
            _positive(self.standard_deviation, "standard_deviation"),
        )
        _ordered_bounds(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": "truncated_normal",
            "mean": self.mean,
            "standard_deviation": self.standard_deviation,
            "lower": self.lower,
            "upper": self.upper,
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class UniformDistribution:
    """Continuous uniform distribution on [lower, upper]."""

    lower: float
    upper: float

    def __post_init__(self) -> None:
        _ordered_bounds(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": "uniform",
            "lower": self.lower,
            "upper": self.upper,
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class LogNormalDistribution:
    """Log-normal distribution parameterized by median and geometric SD."""

    median: float
    geometric_standard_deviation: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "median", _positive(self.median, "median"))

        geometric_sd = _number(
            self.geometric_standard_deviation,
            "geometric_standard_deviation",
        )
        if geometric_sd <= 1.0:
            raise ValueError(
                "geometric_standard_deviation must be strictly greater than 1; "
                "use ConstantDistribution for zero variation"
            )

        object.__setattr__(
            self,
            "geometric_standard_deviation",
            geometric_sd,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": "log_normal",
            "median": self.median,
            "geometric_standard_deviation": self.geometric_standard_deviation,
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class FiniteDiscreteDistribution:
    """Finite numeric support with explicit probabilities."""

    values: tuple[float, ...]
    probabilities: tuple[float, ...]

    def __post_init__(self) -> None:
        values = tuple(
            _number(value, f"values[{index}]")
            for index, value in enumerate(self.values)
        )
        probabilities = tuple(
            _number(probability, f"probabilities[{index}]")
            for index, probability in enumerate(self.probabilities)
        )

        if not values:
            raise ValueError("values cannot be empty")

        if len(values) != len(probabilities):
            raise ValueError(
                "values and probabilities must have the same length"
            )

        if len(set(values)) != len(values):
            raise ValueError("finite-discrete values must be unique")

        if any(probability <= 0.0 for probability in probabilities):
            raise ValueError(
                "finite-discrete probabilities must be strictly positive"
            )

        total = math.fsum(probabilities)
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(
                "finite-discrete probabilities must sum to 1"
            )

        object.__setattr__(self, "values", values)
        object.__setattr__(self, "probabilities", probabilities)

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": "finite_discrete",
            "values": list(self.values),
            "probabilities": list(self.probabilities),
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())

def _strict_fields(
    data: dict[str, Any],
    required: set[str],
) -> None:
    actual = set(data)

    missing = required - actual
    if missing:
        raise ValueError(
            "missing distribution fields: "
            + ", ".join(sorted(missing))
        )

    unknown = actual - required
    if unknown:
        raise ValueError(
            "unknown distribution fields: "
            + ", ".join(sorted(unknown))
        )


def distribution_from_dict(
    data: dict[str, Any],
) -> "DistributionSpec":
    """Restore one distribution from its exact serialized representation."""

    if not isinstance(data, dict):
        raise TypeError("distribution data must be a dict")

    if "family" not in data:
        raise ValueError("missing distribution fields: family")

    family = data["family"]
    if not isinstance(family, str):
        raise TypeError("distribution family must be text")

    if family == "constant":
        _strict_fields(
            data,
            {"family", "value"},
        )
        return ConstantDistribution(
            value=data["value"],
        )

    if family == "normal":
        _strict_fields(
            data,
            {
                "family",
                "mean",
                "standard_deviation",
            },
        )
        return NormalDistribution(
            mean=data["mean"],
            standard_deviation=data["standard_deviation"],
        )

    if family == "truncated_normal":
        _strict_fields(
            data,
            {
                "family",
                "mean",
                "standard_deviation",
                "lower",
                "upper",
            },
        )
        return TruncatedNormalDistribution(
            mean=data["mean"],
            standard_deviation=data["standard_deviation"],
            lower=data["lower"],
            upper=data["upper"],
        )

    if family == "uniform":
        _strict_fields(
            data,
            {
                "family",
                "lower",
                "upper",
            },
        )
        return UniformDistribution(
            lower=data["lower"],
            upper=data["upper"],
        )

    if family == "log_normal":
        _strict_fields(
            data,
            {
                "family",
                "median",
                "geometric_standard_deviation",
            },
        )
        return LogNormalDistribution(
            median=data["median"],
            geometric_standard_deviation=(
                data["geometric_standard_deviation"]
            ),
        )

    if family == "finite_discrete":
        _strict_fields(
            data,
            {
                "family",
                "values",
                "probabilities",
            },
        )

        if not isinstance(data["values"], list):
            raise TypeError(
                "finite-discrete values must be a list"
            )

        if not isinstance(data["probabilities"], list):
            raise TypeError(
                "finite-discrete probabilities must be a list"
            )

        return FiniteDiscreteDistribution(
            values=tuple(data["values"]),
            probabilities=tuple(data["probabilities"]),
        )

    raise ValueError(
        f"unsupported distribution family {family!r}"
    )

DistributionSpec = (
    ConstantDistribution
    | NormalDistribution
    | TruncatedNormalDistribution
    | UniformDistribution
    | LogNormalDistribution
    | FiniteDiscreteDistribution
)


__all__ = [
    "ConstantDistribution",
    "DistributionSpec",
    "FiniteDiscreteDistribution",
    "LogNormalDistribution",
    "NormalDistribution",
    "TruncatedNormalDistribution",
    "UniformDistribution",
    "distribution_from_dict",
]
