"""Deterministic scalar distribution sampling for Phase K."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import Any

import numpy as np

from ..hashing import canonical_hash
from ._serialization import strict_fields
from .distributions import (
    ConstantDistribution,
    DistributionSpec,
    FiniteDiscreteDistribution,
    LogNormalDistribution,
    NormalDistribution,
    TruncatedNormalDistribution,
    UniformDistribution,
)
from .correlation import (
    DependenceSpec,
    IndependentDependence,
    dependence_from_dict,
)
from .rng import RNGSpec
from .specification import EnsembleSpec


SCALAR_SAMPLING_ALGORITHM = (
    "phase-k-pcg64-raw53-box-muller-v1"
)

SAMPLING_SCHEMA_VERSION = "ensemble-sampling-spec-v1"
SAMPLE_SCHEMA_VERSION = "ensemble-sample-v1"
SAMPLE_ID_SCHEMA_VERSION = "ensemble-sample-id-v1"

SAMPLING_ORDER = "sample-major,declared-variable-order"
SAMPLING_PRECISION = "float64-derived-python-float"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_TWO_POW_53 = float(2**53)


class SamplingError(ValueError):
    """Explicit numerical or bounded-distribution sampling failure."""

    def __init__(
        self,
        family: str,
        reason: str,
        *,
        attempts: int | None = None,
    ) -> None:
        self.family = family
        self.reason = reason
        self.attempts = attempts

        suffix = (
            ""
            if attempts is None
            else f" after {attempts} attempts"
        )

        super().__init__(
            f"{family} sampling failed: {reason}{suffix}"
        )


def _validate_rng(
    rng: np.random.Generator,
) -> None:
    if not isinstance(rng, np.random.Generator):
        raise TypeError(
            "rng must be numpy.random.Generator"
        )

    if not isinstance(
        rng.bit_generator,
        np.random.PCG64,
    ):
        raise ValueError(
            "Phase K sampling requires the PCG64 bit generator"
        )


def _validate_draw_budget(
    max_draws_per_value: int,
) -> None:
    if (
        isinstance(max_draws_per_value, bool)
        or not isinstance(max_draws_per_value, int)
    ):
        raise TypeError(
            "max_draws_per_value must be an integer excluding bool"
        )

    if max_draws_per_value < 1:
        raise ValueError(
            "max_draws_per_value must be >= 1"
        )


def _raw_uint64(
    rng: np.random.Generator,
) -> int:
    return int(
        rng.bit_generator.random_raw()
    )


def _unit_interval(
    rng: np.random.Generator,
) -> float:
    """Return one deterministic float on [0, 1) from 53 raw bits."""

    raw = _raw_uint64(rng)
    mantissa = raw >> 11

    return mantissa / _TWO_POW_53


def _open_unit_interval(
    rng: np.random.Generator,
) -> float:
    """Return one deterministic float strictly inside (0, 1)."""

    raw = _raw_uint64(rng)
    mantissa = raw >> 11

    return (mantissa + 0.5) / _TWO_POW_53


def _standard_normal(
    rng: np.random.Generator,
) -> float:
    """Return one Box-Muller standard-normal draw."""

    u1 = _open_unit_interval(rng)
    u2 = _unit_interval(rng)

    radius = math.sqrt(
        -2.0 * math.log(u1)
    )
    angle = math.tau * u2

    return radius * math.cos(angle)


def _normal_value(
    distribution: NormalDistribution
    | TruncatedNormalDistribution,
    rng: np.random.Generator,
) -> float:
    z = _standard_normal(rng)

    value = (
        distribution.mean
        + distribution.standard_deviation * z
    )

    return float(value)


def sample_distribution(
    distribution: DistributionSpec,
    rng: np.random.Generator,
    *,
    max_draws_per_value: int = 10000,
) -> float:
    """Draw one scalar according to the frozen Phase K sampling contract."""

    _validate_rng(rng)
    _validate_draw_budget(max_draws_per_value)

    if isinstance(
        distribution,
        ConstantDistribution,
    ):
        return float(distribution.value)

    if isinstance(
        distribution,
        UniformDistribution,
    ):
        u = _unit_interval(rng)

        value = (
            (1.0 - u) * distribution.lower
            + u * distribution.upper
        )

        if not math.isfinite(value):
            raise SamplingError(
                "uniform",
                "non-finite numerical result",
            )

        return float(value)

    if isinstance(
        distribution,
        NormalDistribution,
    ):
        value = _normal_value(
            distribution,
            rng,
        )

        if not math.isfinite(value):
            raise SamplingError(
                "normal",
                "non-finite numerical result",
            )

        return value

    if isinstance(
        distribution,
        TruncatedNormalDistribution,
    ):
        for attempt in range(
            1,
            max_draws_per_value + 1,
        ):
            value = _normal_value(
                distribution,
                rng,
            )

            if (
                math.isfinite(value)
                and distribution.lower
                <= value
                <= distribution.upper
            ):
                return value

        raise SamplingError(
            "truncated_normal",
            "rejection budget exhausted",
            attempts=max_draws_per_value,
        )

    if isinstance(
        distribution,
        LogNormalDistribution,
    ):
        z = _standard_normal(rng)

        try:
            value = (
                distribution.median
                * math.exp(
                    math.log(
                        distribution.geometric_standard_deviation
                    )
                    * z
                )
            )
        except OverflowError as exc:
            raise SamplingError(
                "log_normal",
                "floating-point overflow",
            ) from exc

        if (
            not math.isfinite(value)
            or value <= 0.0
        ):
            raise SamplingError(
                "log_normal",
                "non-representable positive finite result",
            )

        return float(value)

    if isinstance(
        distribution,
        FiniteDiscreteDistribution,
    ):
        u = _unit_interval(rng)
        total = math.fsum(
            distribution.probabilities
        )
        threshold = u * total

        cumulative = 0.0

        for value, probability in zip(
            distribution.values[:-1],
            distribution.probabilities[:-1],
        ):
            cumulative += probability

            if threshold < cumulative:
                return float(value)

        return float(
            distribution.values[-1]
        )

    raise TypeError(
        "distribution must be a supported DistributionSpec"
    )


def _integer(
    value: int,
    label: str,
    minimum: int,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(
            f"{label} must be an integer excluding bool"
        )

    if value < minimum:
        raise ValueError(
            f"{label} must be >= {minimum}"
        )


@dataclass(frozen=True)
class SamplingSpec:
    """Immutable identity of one Phase K sampling operation."""

    ensemble_spec: EnsembleSpec
    rng: RNGSpec
    sample_count: int
    dependence: DependenceSpec = field(
        default_factory=IndependentDependence
    )
    max_draws_per_value: int = 10000
    scalar_sampling_algorithm: str = SCALAR_SAMPLING_ALGORITHM
    order: str = SAMPLING_ORDER
    precision: str = SAMPLING_PRECISION
    schema_version: str = SAMPLING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(
            self.ensemble_spec,
            EnsembleSpec,
        ):
            raise TypeError(
                "ensemble_spec must be EnsembleSpec"
            )

        if not isinstance(self.rng, RNGSpec):
            raise TypeError(
                "rng must be RNGSpec"
            )

        if not isinstance(
            self.dependence,
            IndependentDependence,
        ):
            raise TypeError(
                "dependence must be a supported DependenceSpec"
            )

        _integer(
            self.sample_count,
            "sample_count",
            1,
        )
        _integer(
            self.max_draws_per_value,
            "max_draws_per_value",
            1,
        )

        if (
            self.scalar_sampling_algorithm
            != SCALAR_SAMPLING_ALGORITHM
        ):
            raise ValueError(
                "unsupported scalar sampling algorithm"
            )

        if self.order != SAMPLING_ORDER:
            raise ValueError(
                "unsupported sampling order"
            )

        if self.precision != SAMPLING_PRECISION:
            raise ValueError(
                "unsupported sampling precision"
            )

        if self.schema_version != SAMPLING_SCHEMA_VERSION:
            raise ValueError(
                "unsupported sampling schema_version"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "ensemble_spec": self.ensemble_spec.to_dict(),
            "ensemble_spec_hash": (
                self.ensemble_spec.definition_hash
            ),
            "rng": self.rng.to_dict(),
            "sample_count": self.sample_count,
            "dependence": self.dependence.to_dict(),
            "max_draws_per_value": self.max_draws_per_value,
            "scalar_sampling_algorithm": (
                self.scalar_sampling_algorithm
            ),
            "order": self.order,
            "precision": self.precision,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "SamplingSpec":
        strict_fields(
            data,
            label="sampling-specification",
            required={
                "schema_version",
                "ensemble_spec",
                "ensemble_spec_hash",
                "rng",
                "sample_count",
                "dependence",
                "max_draws_per_value",
                "scalar_sampling_algorithm",
                "order",
                "precision",
            },
        )

        ensemble_spec = EnsembleSpec.from_dict(
            data["ensemble_spec"]
        )

        if (
            data["ensemble_spec_hash"]
            != ensemble_spec.definition_hash
        ):
            raise ValueError(
                "ensemble_spec_hash integrity mismatch"
            )

        return cls(
            ensemble_spec=ensemble_spec,
            rng=RNGSpec.from_dict(
                data["rng"]
            ),
            sample_count=data["sample_count"],
            dependence=dependence_from_dict(
                data["dependence"]
            ),
            max_draws_per_value=(
                data["max_draws_per_value"]
            ),
            scalar_sampling_algorithm=(
                data["scalar_sampling_algorithm"]
            ),
            order=data["order"],
            precision=data["precision"],
            schema_version=data["schema_version"],
        )

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class EnsembleSample:
    """One ordered generated parameter sample."""

    sampling_spec_hash: str
    sample_index: int
    variable_names: tuple[str, ...]
    values: tuple[float, ...]
    schema_version: str = SAMPLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "variable_names",
            tuple(self.variable_names),
        )
        object.__setattr__(
            self,
            "values",
            tuple(self.values),
        )

        if (
            not isinstance(self.sampling_spec_hash, str)
            or not _SHA256_RE.fullmatch(
                self.sampling_spec_hash
            )
        ):
            raise ValueError(
                "sampling_spec_hash must be a lowercase "
                "SHA-256 hex digest"
            )

        _integer(
            self.sample_index,
            "sample_index",
            0,
        )

        if not self.variable_names:
            raise ValueError(
                "variable_names cannot be empty"
            )

        for name in self.variable_names:
            if (
                not isinstance(name, str)
                or not name
                or name != name.strip()
            ):
                raise ValueError(
                    "variable names must be nonempty text "
                    "without outer whitespace"
                )

        if (
            len(set(self.variable_names))
            != len(self.variable_names)
        ):
            raise ValueError(
                "variable_names must be unique"
            )

        if len(self.values) != len(self.variable_names):
            raise ValueError(
                "sample values must match variable_names width"
            )

        for value in self.values:
            if (
                type(value) is not float
                or not math.isfinite(value)
            ):
                raise ValueError(
                    "sample values must be finite Python floats"
                )

        if self.schema_version != SAMPLE_SCHEMA_VERSION:
            raise ValueError(
                "unsupported ensemble-sample schema_version"
            )

    @classmethod
    def from_values(
        cls,
        sampling_spec: SamplingSpec,
        sample_index: int,
        values: tuple[float, ...] | list[float],
    ) -> "EnsembleSample":
        if not isinstance(
            sampling_spec,
            SamplingSpec,
        ):
            raise TypeError(
                "sampling_spec must be SamplingSpec"
            )

        _integer(
            sample_index,
            "sample_index",
            0,
        )

        if sample_index >= sampling_spec.sample_count:
            raise ValueError(
                "sample_index must be smaller than sample_count"
            )

        return cls(
            sampling_spec_hash=(
                sampling_spec.definition_hash
            ),
            sample_index=sample_index,
            variable_names=(
                sampling_spec.ensemble_spec.variable_names
            ),
            values=tuple(values),
        )

    def _id_payload(self) -> dict[str, Any]:
        return {
            "schema_version": SAMPLE_ID_SCHEMA_VERSION,
            "sampling_spec_hash": self.sampling_spec_hash,
            "sample_index": self.sample_index,
        }

    @property
    def sample_id(self) -> str:
        return canonical_hash(
            self._id_payload()
        )

    def _content_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "sampling_spec_hash": self.sampling_spec_hash,
            "sample_index": self.sample_index,
            "sample_id": self.sample_id,
            "variable_names": list(
                self.variable_names
            ),
            "values": list(self.values),
        }

    @property
    def sample_hash(self) -> str:
        return canonical_hash(
            self._content_payload()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._content_payload(),
            "sample_hash": self.sample_hash,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "EnsembleSample":
        strict_fields(
            data,
            label="ensemble-sample",
            required={
                "schema_version",
                "sampling_spec_hash",
                "sample_index",
                "sample_id",
                "variable_names",
                "values",
                "sample_hash",
            },
        )

        if not isinstance(
            data["variable_names"],
            list,
        ):
            raise TypeError(
                "ensemble-sample variable_names must be a list"
            )

        if not isinstance(data["values"], list):
            raise TypeError(
                "ensemble-sample values must be a list"
            )

        sample = cls(
            sampling_spec_hash=(
                data["sampling_spec_hash"]
            ),
            sample_index=data["sample_index"],
            variable_names=tuple(
                data["variable_names"]
            ),
            values=tuple(data["values"]),
            schema_version=data["schema_version"],
        )

        if data["sample_id"] != sample.sample_id:
            raise ValueError(
                "sample_id integrity mismatch"
            )

        if data["sample_hash"] != sample.sample_hash:
            raise ValueError(
                "sample_hash integrity mismatch"
            )

        return sample

    def require_matches_spec(
        self,
        sampling_spec: SamplingSpec,
    ) -> None:
        if not isinstance(
            sampling_spec,
            SamplingSpec,
        ):
            raise TypeError(
                "sampling_spec must be SamplingSpec"
            )

        if (
            self.sampling_spec_hash
            != sampling_spec.definition_hash
        ):
            raise ValueError(
                "sample does not match sampling specification"
            )

        if (
            self.variable_names
            != sampling_spec.ensemble_spec.variable_names
        ):
            raise ValueError(
                "sample variable order does not match "
                "sampling specification"
            )

        if self.sample_index >= sampling_spec.sample_count:
            raise ValueError(
                "sample index is outside sampling specification"
            )

__all__ = [
    "EnsembleSample",
    "SAMPLING_ORDER",
    "SAMPLING_PRECISION",
    "SAMPLING_SCHEMA_VERSION",
    "SAMPLE_ID_SCHEMA_VERSION",
    "SAMPLE_SCHEMA_VERSION",
    "SCALAR_SAMPLING_ALGORITHM",
    "SamplingError",
    "SamplingSpec",
    "sample_distribution",
]
