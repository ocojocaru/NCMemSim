from dataclasses import FrozenInstanceError, replace
import math

import pytest

from ncmemsim.ensemble import (
    ConstantDistribution,
    FiniteDiscreteDistribution,
    LogNormalDistribution,
    NormalDistribution,
    TruncatedNormalDistribution,
    UniformDistribution,
)
from ncmemsim.hashing import canonical_hash


@pytest.mark.parametrize(
    "factory",
    [
        lambda value: ConstantDistribution(value),
        lambda value: NormalDistribution(value, 1.0),
        lambda value: NormalDistribution(0.0, value),
        lambda value: UniformDistribution(value, 2.0),
        lambda value: UniformDistribution(0.0, value),
        lambda value: TruncatedNormalDistribution(value, 1.0, -1.0, 1.0),
        lambda value: LogNormalDistribution(value, 1.2),
    ],
)
@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_nonfinite_values_are_rejected(factory, value):
    with pytest.raises(ValueError):
        factory(value)


@pytest.mark.parametrize("value", [True, "1", None, {}, []])
def test_nonnumeric_values_are_rejected(value):
    with pytest.raises(TypeError):
        ConstantDistribution(value)


@pytest.mark.parametrize("std", [0.0, -1.0, math.nan, math.inf])
def test_normal_standard_deviation_must_be_positive(std):
    with pytest.raises(ValueError):
        NormalDistribution(0.0, std)


@pytest.mark.parametrize("bounds", [(1.0, 1.0), (2.0, 1.0)])
def test_uniform_requires_strictly_ordered_bounds(bounds):
    with pytest.raises(ValueError):
        UniformDistribution(*bounds)


@pytest.mark.parametrize("bounds", [(1.0, 1.0), (2.0, 1.0)])
def test_truncated_normal_requires_strictly_ordered_bounds(bounds):
    with pytest.raises(ValueError):
        TruncatedNormalDistribution(
            mean=0.0,
            standard_deviation=1.0,
            lower=bounds[0],
            upper=bounds[1],
        )


def test_truncated_normal_mean_may_lie_outside_support():
    item = TruncatedNormalDistribution(
        mean=3.0,
        standard_deviation=2.0,
        lower=0.0,
        upper=1.0,
    )

    assert item.mean == 3.0


@pytest.mark.parametrize("median", [0.0, -1.0])
def test_lognormal_requires_positive_median(median):
    with pytest.raises(ValueError):
        LogNormalDistribution(
            median=median,
            geometric_standard_deviation=1.2,
        )


@pytest.mark.parametrize("gsd", [0.0, 0.5, 1.0, -1.0])
def test_lognormal_requires_non_degenerate_geometric_sd(gsd):
    with pytest.raises(ValueError):
        LogNormalDistribution(
            median=5.0,
            geometric_standard_deviation=gsd,
        )


def test_constant_distribution_represents_zero_variation():
    item = ConstantDistribution(5)

    assert item.value == 5.0
    assert item.to_dict() == {
        "family": "constant",
        "value": 5.0,
    }


def test_finite_discrete_contract():
    item = FiniteDiscreteDistribution(
        values=(4, 5, 6),
        probabilities=(0.2, 0.5, 0.3),
    )

    assert item.values == (4.0, 5.0, 6.0)
    assert item.probabilities == (0.2, 0.5, 0.3)
    assert item.to_dict() == {
        "family": "finite_discrete",
        "values": [4.0, 5.0, 6.0],
        "probabilities": [0.2, 0.5, 0.3],
    }


@pytest.mark.parametrize(
    "values, probabilities",
    [
        ((), ()),
        ((1.0,), (0.5, 0.5)),
        ((1.0, 1.0), (0.5, 0.5)),
        ((1.0, 2.0), (0.0, 1.0)),
        ((1.0, 2.0), (-0.1, 1.1)),
        ((1.0, 2.0), (0.4, 0.4)),
    ],
)
def test_invalid_finite_discrete_contract(values, probabilities):
    with pytest.raises(ValueError):
        FiniteDiscreteDistribution(
            values=values,
            probabilities=probabilities,
        )


def test_serialization_and_hashes_are_deterministic():
    first = NormalDistribution(5, 0.5)
    second = NormalDistribution(5.0, 0.5)

    assert first.to_dict() == second.to_dict()
    assert first.definition_hash == second.definition_hash
    assert first.definition_hash == canonical_hash(first.to_dict())

    changed = replace(first, mean=6.0)
    assert changed.definition_hash != first.definition_hash


def test_distribution_objects_are_frozen():
    item = UniformDistribution(1.0, 2.0)

    with pytest.raises(FrozenInstanceError):
        item.lower = 0.0
