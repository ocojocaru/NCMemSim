"""Deterministic scalar distribution sampling for Phase K."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import platform
import re
from typing import Any

import numpy as np

from .._version import __version__
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

MANIFEST_SCHEMA_VERSION = "ensemble-sample-manifest-v1"
SAMPLE_TABLE_SCHEMA_VERSION = "ensemble-sample-table-v1"

_RUNTIME_KEYS = (
    "python",
    "python_implementation",
    "numpy",
    "ncmemsim",
)


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


def _sample_id_from_identity(
    sampling_spec_hash: str,
    sample_index: int,
) -> str:
    return canonical_hash(
        {
            "schema_version": SAMPLE_ID_SCHEMA_VERSION,
            "sampling_spec_hash": sampling_spec_hash,
            "sample_index": sample_index,
        }
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

    @property
    def sample_id(self) -> str:
        return _sample_id_from_identity(
            self.sampling_spec_hash,
            self.sample_index,
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


class SampleGenerationError(ValueError):
    """Failure while generating one declared ensemble sample value."""

    def __init__(
        self,
        sampling_spec_hash: str,
        sample_index: int,
        variable_name: str,
        cause: SamplingError,
    ) -> None:
        self.sampling_spec_hash = sampling_spec_hash
        self.sample_index = sample_index
        self.variable_name = variable_name
        self.cause = cause
        self.sample_id = _sample_id_from_identity(
            sampling_spec_hash,
            sample_index,
        )

        super().__init__(
            "sample generation failed for "
            f"sample {sample_index} "
            f"({self.sample_id}), "
            f"variable {variable_name!r}: {cause}"
        )


@dataclass(frozen=True)
class SampleManifest:
    """Canonical ordered Phase K sample table and provenance."""

    sampling_spec: SamplingSpec
    samples: tuple[EnsembleSample, ...]
    runtime: tuple[tuple[str, str], ...]
    schema_version: str = MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(
            self.sampling_spec,
            SamplingSpec,
        ):
            raise TypeError(
                "sampling_spec must be SamplingSpec"
            )

        samples = tuple(self.samples)
        runtime = tuple(
            tuple(pair)
            for pair in self.runtime
        )

        if len(samples) != self.sampling_spec.sample_count:
            raise ValueError(
                "manifest sample count does not match "
                "sampling specification"
            )

        for expected_index, sample in enumerate(samples):
            if not isinstance(
                sample,
                EnsembleSample,
            ):
                raise TypeError(
                    "manifest samples must be EnsembleSample instances"
                )

            sample.require_matches_spec(
                self.sampling_spec
            )

            if sample.sample_index != expected_index:
                raise ValueError(
                    "manifest samples must be ordered by "
                    "contiguous sample_index"
                )

            for pair in runtime:
                if len(pair) != 2:
                    raise ValueError(
                        "runtime metadata entries must be key/value pairs"
                    )

            if tuple(
                pair[0]
                for pair in runtime
            ) != _RUNTIME_KEYS:
                raise ValueError(
                    "runtime metadata fields/order mismatch"
                )

            for pair in runtime:
                key, value = pair

            if (
                not isinstance(key, str)
                or not isinstance(value, str)
                or not key
                or not value
                or key != key.strip()
                or value != value.strip()
            ):
                raise ValueError(
                    "runtime metadata must contain "
                    "nonempty normalized text"
                )

        if self.schema_version != MANIFEST_SCHEMA_VERSION:
            raise ValueError(
                "unsupported sample-manifest schema_version"
            )

        object.__setattr__(
            self,
            "samples",
            samples,
        )
        object.__setattr__(
            self,
            "runtime",
            runtime,
        )

    def _sample_table_payload(self) -> dict[str, Any]:
        return {
            "schema_version": SAMPLE_TABLE_SCHEMA_VERSION,
            "sampling_spec_hash": (
                self.sampling_spec.definition_hash
            ),
            "samples": [
                sample.to_dict()
                for sample in self.samples
            ],
        }

    @property
    def sample_table_hash(self) -> str:
        return canonical_hash(
            self._sample_table_payload()
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "sampling_spec": (
                self.sampling_spec.to_dict()
            ),
            "sampling_spec_hash": (
                self.sampling_spec.definition_hash
            ),
            "runtime": dict(self.runtime),
            "sample_table_hash": (
                self.sample_table_hash
            ),
            "samples": [
                sample.to_dict()
                for sample in self.samples
            ],
        }

    @property
    def manifest_hash(self) -> str:
        return canonical_hash(
            self._payload()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "manifest_hash": self.manifest_hash,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "SampleManifest":
        """Restore one manifest without drawing random values again."""

        strict_fields(
            data,
            label="sample-manifest",
            required={
                "schema_version",
                "sampling_spec",
                "sampling_spec_hash",
                "runtime",
                "sample_table_hash",
                "samples",
                "manifest_hash",
            },
        )

        sampling_spec = SamplingSpec.from_dict(
            data["sampling_spec"]
        )

        if (
            data["sampling_spec_hash"]
            != sampling_spec.definition_hash
        ):
            raise ValueError(
                "sampling_spec_hash integrity mismatch"
            )

        if not isinstance(data["runtime"], dict):
            raise TypeError(
                "sample-manifest runtime must be a dict"
            )

        strict_fields(
            data["runtime"],
            label="sample-manifest runtime",
            required=set(_RUNTIME_KEYS),
        )

        runtime = tuple(
            (
                key,
                data["runtime"][key],
            )
            for key in _RUNTIME_KEYS
        )

        if not isinstance(data["samples"], list):
            raise TypeError(
                "sample-manifest samples must be a list"
            )

        samples = tuple(
            EnsembleSample.from_dict(item)
            for item in data["samples"]
        )

        manifest = cls(
            sampling_spec=sampling_spec,
            samples=samples,
            runtime=runtime,
            schema_version=data["schema_version"],
        )

        if (
            data["sample_table_hash"]
            != manifest.sample_table_hash
        ):
            raise ValueError(
                "sample_table_hash integrity mismatch"
            )

        if (
            data["manifest_hash"]
            != manifest.manifest_hash
        ):
            raise ValueError(
                "manifest_hash integrity mismatch"
            )

        return manifest

    def to_json(self) -> str:
        """Return the deterministic JSON representation of this manifest."""

        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    @classmethod
    def from_json(
        cls,
        text: str,
    ) -> "SampleManifest":
        """Restore a manifest from strict JSON without resampling."""

        if not isinstance(text, str):
            raise TypeError(
                "sample-manifest JSON must be text"
            )

        def reject_duplicate_keys(
            pairs: list[tuple[str, Any]],
        ) -> dict[str, Any]:
            result: dict[str, Any] = {}

            for key, value in pairs:
                if key in result:
                    raise ValueError(
                        f"duplicate JSON key {key!r}"
                    )

                result[key] = value

            return result

        def reject_nonfinite(
            value: str,
        ) -> None:
            raise ValueError(
                f"non-finite JSON constant {value!r}"
            )

        raw = json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonfinite,
        )

        if not isinstance(raw, dict):
            raise TypeError(
                "sample-manifest JSON root must be an object"
            )

        return cls.from_dict(raw)


def generate_sample_manifest(
    sampling_spec: SamplingSpec,
) -> SampleManifest:
    """Generate one deterministic ordered independent sample manifest."""

    if not isinstance(
        sampling_spec,
        SamplingSpec,
    ):
        raise TypeError(
            "sampling_spec must be SamplingSpec"
        )

    if not isinstance(
        sampling_spec.dependence,
        IndependentDependence,
    ):
        raise ValueError(
            "current Phase K generation supports "
            "independent dependence only"
        )

    rng = sampling_spec.rng.create_generator()
    samples: list[EnsembleSample] = []

    for sample_index in range(
        sampling_spec.sample_count
    ):
        values: list[float] = []

        for variable in (
            sampling_spec.ensemble_spec.variables
        ):
            try:
                value = sample_distribution(
                    variable.distribution,
                    rng,
                    max_draws_per_value=(
                        sampling_spec.max_draws_per_value
                    ),
                )
            except SamplingError as exc:
                raise SampleGenerationError(
                    sampling_spec.definition_hash,
                    sample_index,
                    variable.name,
                    exc,
                ) from exc

            values.append(value)

        samples.append(
            EnsembleSample.from_values(
                sampling_spec,
                sample_index,
                tuple(values),
            )
        )

    runtime = (
        (
            "python",
            platform.python_version(),
        ),
        (
            "python_implementation",
            platform.python_implementation(),
        ),
        (
            "numpy",
            np.__version__,
        ),
        (
            "ncmemsim",
            __version__,
        ),
    )

    return SampleManifest(
        sampling_spec=sampling_spec,
        samples=tuple(samples),
        runtime=runtime,
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
    "MANIFEST_SCHEMA_VERSION",
    "SAMPLE_TABLE_SCHEMA_VERSION",
    "SampleGenerationError",
    "SampleManifest",
    "generate_sample_manifest",
]
