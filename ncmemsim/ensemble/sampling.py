"""Deterministic scalar distribution sampling for Phase K."""

from __future__ import annotations

import math

import numpy as np

from .distributions import (
    ConstantDistribution,
    DistributionSpec,
    FiniteDiscreteDistribution,
    LogNormalDistribution,
    NormalDistribution,
    TruncatedNormalDistribution,
    UniformDistribution,
)


SCALAR_SAMPLING_ALGORITHM = (
    "phase-k-pcg64-raw53-box-muller-v1"
)

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


__all__ = [
    "SCALAR_SAMPLING_ALGORITHM",
    "SamplingError",
    "sample_distribution",
]
