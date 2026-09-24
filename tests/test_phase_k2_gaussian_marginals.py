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


def test_truncated_normal_transform_fails_closed_for_now():
    distribution = TruncatedNormalDistribution(
        mean=5.0,
        standard_deviation=0.5,
        lower=4.0,
        upper=6.0,
    )

    with pytest.raises(
        SamplingError,
        match="inverse-CDF",
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
