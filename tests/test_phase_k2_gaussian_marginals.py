# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

import math

import pytest

from ncmemsim.ensemble import (
    ConstantDistribution,
    LogNormalDistribution,
    NormalDistribution,
    TruncatedNormalDistribution,
    UniformDistribution,
)
from ncmemsim.ensemble.sampling import (
    SamplingError,
    _correlated_marginal_value,
    _standard_normal_cdf_open,
    _inverse_standard_normal_cdf_open,
)


def test_standard_normal_cdf_zero_is_half():
    assert _standard_normal_cdf_open(
        0.0
    ) == pytest.approx(
        0.5,
        abs=0.0,
    )


def test_standard_normal_cdf_is_symmetric():
    positive = _standard_normal_cdf_open(
        1.25
    )

    negative = _standard_normal_cdf_open(
        -1.25
    )

    assert negative == pytest.approx(
        1.0 - positive,
        abs=1.0e-15,
    )


def test_standard_normal_cdf_remains_open_for_extreme_latents():
    lower = _standard_normal_cdf_open(
        -100.0
    )

    upper = _standard_normal_cdf_open(
        100.0
    )

    assert 0.0 < lower < 1.0
    assert 0.0 < upper < 1.0


@pytest.mark.parametrize(
    ("z", "expected"),
    [
        (0.0, 5.0),
        (1.0, 5.5),
        (-1.0, 4.5),
    ],
)
def test_normal_marginal_uses_latent_standard_normal_directly(
    z,
    expected,
):
    distribution = NormalDistribution(
        mean=5.0,
        standard_deviation=0.5,
    )

    assert _correlated_marginal_value(
        distribution,
        z,
    ) == pytest.approx(
        expected,
        abs=1.0e-15,
    )


def test_uniform_latent_zero_maps_to_midpoint():
    distribution = UniformDistribution(
        lower=2.0,
        upper=6.0,
    )

    value = _correlated_marginal_value(
        distribution,
        0.0,
    )

    assert value == pytest.approx(
        4.0,
        abs=0.0,
    )


def test_uniform_extreme_latents_remain_within_support():
    distribution = UniformDistribution(
        lower=0.0,
        upper=1.0,
    )

    lower = _correlated_marginal_value(
        distribution,
        -100.0,
    )

    upper = _correlated_marginal_value(
        distribution,
        100.0,
    )

    assert 0.0 < lower < 1.0
    assert 0.0 < upper < 1.0


def test_lognormal_latent_zero_maps_to_median():
    distribution = LogNormalDistribution(
        median=15.0,
        geometric_standard_deviation=1.05,
    )

    value = _correlated_marginal_value(
        distribution,
        0.0,
    )

    assert value == pytest.approx(
        15.0,
        abs=0.0,
    )


def test_lognormal_transform_matches_declared_formula():
    distribution = LogNormalDistribution(
        median=15.0,
        geometric_standard_deviation=1.05,
    )

    z = 1.25

    expected = (
        15.0
        * math.exp(
            math.log(1.05)
            * z
        )
    )

    assert _correlated_marginal_value(
        distribution,
        z,
    ) == pytest.approx(
        expected,
        abs=1.0e-15,
    )


@pytest.mark.parametrize(
    ("probability", "expected"),
    [
        (
            0.5,
            0.0,
        ),
        (
            0.025,
            -1.959963984540054,
        ),
        (
            0.975,
            1.959963984540054,
        ),
    ],
)
def test_inverse_standard_normal_known_quantiles(
    probability,
    expected,
):
    assert _inverse_standard_normal_cdf_open(
        probability
    ) == pytest.approx(
        expected,
        abs=5.0e-12,
    )


@pytest.mark.parametrize(
    "probability",
    [
        1.0e-9,
        1.0e-6,
        1.0e-3,
        0.1,
        0.5,
        0.9,
        0.999,
        1.0 - 1.0e-6,
        1.0 - 1.0e-9,
    ],
)
def test_inverse_standard_normal_round_trip(
    probability,
):
    z = _inverse_standard_normal_cdf_open(
        probability
    )

    restored = _standard_normal_cdf_open(
        z
    )

    assert restored == pytest.approx(
        probability,
        abs=1.0e-14,
    )


@pytest.mark.parametrize(
    "probability",
    [
        0.0,
        1.0,
        math.nan,
        math.inf,
        -math.inf,
    ],
)
def test_inverse_standard_normal_rejects_invalid_probability(
    probability,
):
    with pytest.raises(SamplingError):
        _inverse_standard_normal_cdf_open(
            probability
        )


def test_truncated_normal_latent_zero_maps_to_symmetric_center():
    distribution = TruncatedNormalDistribution(
        mean=5.0,
        standard_deviation=0.5,
        lower=4.0,
        upper=6.0,
    )

    value = _correlated_marginal_value(
        distribution,
        0.0,
    )

    assert value == pytest.approx(
        5.0,
        abs=1.0e-14,
    )


def test_truncated_normal_extreme_latents_remain_in_support():
    distribution = TruncatedNormalDistribution(
        mean=5.0,
        standard_deviation=0.5,
        lower=4.0,
        upper=6.0,
    )

    lower_value = _correlated_marginal_value(
        distribution,
        -100.0,
    )

    upper_value = _correlated_marginal_value(
        distribution,
        100.0,
    )

    assert (
        distribution.lower
        <= lower_value
        <= distribution.upper
    )

    assert (
        distribution.lower
        <= upper_value
        <= distribution.upper
    )


def test_truncated_normal_mapping_is_monotonic():
    distribution = TruncatedNormalDistribution(
        mean=5.0,
        standard_deviation=0.5,
        lower=4.0,
        upper=6.0,
    )

    values = tuple(
        _correlated_marginal_value(
            distribution,
            z,
        )
        for z in (
            -2.0,
            -1.0,
            0.0,
            1.0,
            2.0,
        )
    )

    assert values == tuple(
        sorted(values)
    )

    assert len(set(values)) == len(values)


def test_unrepresentable_truncation_probability_interval_fails_closed():
    distribution = TruncatedNormalDistribution(
        mean=0.0,
        standard_deviation=1.0,
        lower=20.0,
        upper=21.0,
    )

    with pytest.raises(
        SamplingError,
        match="not representable",
    ):
        _correlated_marginal_value(
            distribution,
            0.0,
        )


def test_unsupported_marginal_is_rejected():
    distribution = ConstantDistribution(
        5.0
    )

    with pytest.raises(TypeError):
        _correlated_marginal_value(
            distribution,
            0.0,
        )


@pytest.mark.parametrize(
    "value",
    [
        math.nan,
        math.inf,
        -math.inf,
    ],
)
def test_nonfinite_latent_is_rejected(
    value,
):
    distribution = NormalDistribution(
        mean=5.0,
        standard_deviation=0.5,
    )

    with pytest.raises(SamplingError):
        _correlated_marginal_value(
            distribution,
            value,
        )


def test_truncated_normal_asymmetric_reference_quantile():
    distribution = TruncatedNormalDistribution(
        mean=0.0,
        standard_deviation=1.0,
        lower=0.0,
        upper=2.0,
    )

    value = _correlated_marginal_value(
        distribution,
        0.0,
    )

    assert value == pytest.approx(
        0.6391119108712726,
        abs=5.0e-12,
    )
