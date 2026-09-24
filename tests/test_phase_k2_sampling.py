import math

import numpy as np
import pytest

from ncmemsim.ensemble import (
    ConstantDistribution,
    FiniteDiscreteDistribution,
    LogNormalDistribution,
    NormalDistribution,
    RNGSpec,
    SamplingError,
    TruncatedNormalDistribution,
    UniformDistribution,
    sample_distribution,
)


SEED = 12345


def rng():
    return RNGSpec(
        seed=SEED
    ).create_generator()


def test_constant_distribution_consumes_no_rng_state():
    first = rng()
    second = rng()

    value = sample_distribution(
        ConstantDistribution(5.0),
        first,
    )

    assert value == 5.0

    assert (
        first.bit_generator.random_raw()
        == second.bit_generator.random_raw()
    )


def test_uniform_reference_value():
    value = sample_distribution(
        UniformDistribution(
            lower=3.0,
            upper=7.0,
        ),
        rng(),
    )

    assert value == 3.9093440898686787


def test_normal_reference_value():
    value = sample_distribution(
        NormalDistribution(
            mean=0.0,
            standard_deviation=1.0,
        ),
        rng(),
    )

    assert math.isclose(
        value,
        -0.7009952098424472,
        rel_tol=0.0,
        abs_tol=1e-15,
    )


def test_lognormal_reference_value():
    value = sample_distribution(
        LogNormalDistribution(
            median=5.0,
            geometric_standard_deviation=1.2,
        ),
        rng(),
    )

    assert math.isclose(
        value,
        4.400118069187843,
        rel_tol=0.0,
        abs_tol=1e-14,
    )


def test_truncated_normal_rejects_until_inside_distribution_support():
    value = sample_distribution(
        TruncatedNormalDistribution(
            mean=0.0,
            standard_deviation=1.0,
            lower=-0.5,
            upper=0.5,
        ),
        rng(),
    )

    assert math.isclose(
        value,
        -0.3007841096593652,
        rel_tol=0.0,
        abs_tol=1e-15,
    )


def test_truncated_normal_exhaustion_is_explicit():
    with pytest.raises(SamplingError) as caught:
        sample_distribution(
            TruncatedNormalDistribution(
                mean=100.0,
                standard_deviation=1.0,
                lower=-1.0,
                upper=1.0,
            ),
            rng(),
            max_draws_per_value=3,
        )

    assert caught.value.family == "truncated_normal"
    assert caught.value.attempts == 3


def test_finite_discrete_reference_selection():
    value = sample_distribution(
        FiniteDiscreteDistribution(
            values=(4.0, 5.0, 6.0),
            probabilities=(0.2, 0.5, 0.3),
        ),
        rng(),
    )

    assert value == 5.0


@pytest.mark.parametrize(
    "distribution",
    [
        UniformDistribution(1.0, 2.0),
        NormalDistribution(5.0, 0.5),
        TruncatedNormalDistribution(
            mean=5.0,
            standard_deviation=0.5,
            lower=4.0,
            upper=6.0,
        ),
        LogNormalDistribution(
            median=5.0,
            geometric_standard_deviation=1.2,
        ),
        FiniteDiscreteDistribution(
            values=(4.0, 5.0, 6.0),
            probabilities=(0.2, 0.5, 0.3),
        ),
    ],
)
def test_same_seed_produces_same_scalar_draw(distribution):
    first = sample_distribution(
        distribution,
        rng(),
    )

    second = sample_distribution(
        distribution,
        rng(),
    )

    assert first == second


def test_normal_sampling_does_not_enforce_physical_domain():
    value = sample_distribution(
        NormalDistribution(
            mean=-5.0,
            standard_deviation=0.01,
        ),
        rng(),
    )

    assert value < 0.0


@pytest.mark.parametrize(
    "budget",
    [
        0,
        -1,
    ],
)
def test_draw_budget_must_be_positive(budget):
    with pytest.raises(ValueError):
        sample_distribution(
            NormalDistribution(0.0, 1.0),
            rng(),
            max_draws_per_value=budget,
        )


@pytest.mark.parametrize(
    "budget",
    [
        True,
        1.0,
        "1",
        None,
    ],
)
def test_draw_budget_requires_integer(budget):
    with pytest.raises(TypeError):
        sample_distribution(
            NormalDistribution(0.0, 1.0),
            rng(),
            max_draws_per_value=budget,
        )


def test_sampling_requires_generator():
    with pytest.raises(TypeError):
        sample_distribution(
            NormalDistribution(0.0, 1.0),
            object(),
        )


def test_sampling_rejects_non_pcg64_generator():
    other_rng = np.random.Generator(
        np.random.MT19937(SEED)
    )

    with pytest.raises(ValueError):
        sample_distribution(
            NormalDistribution(0.0, 1.0),
            other_rng,
        )


def test_distribution_draws_are_scalar_python_floats():
    distributions = (
        ConstantDistribution(5.0),
        UniformDistribution(1.0, 2.0),
        NormalDistribution(5.0, 0.5),
        TruncatedNormalDistribution(
            mean=5.0,
            standard_deviation=0.5,
            lower=4.0,
            upper=6.0,
        ),
        LogNormalDistribution(
            median=5.0,
            geometric_standard_deviation=1.2,
        ),
        FiniteDiscreteDistribution(
            values=(4.0, 5.0),
            probabilities=(0.5, 0.5),
        ),
    )

    for distribution in distributions:
        value = sample_distribution(
            distribution,
            rng(),
        )

        assert type(value) is float
        assert math.isfinite(value)
