from __future__ import annotations

import numpy as np
import pytest

from ncmemsim.fitting import (
    FitParameter,
    FitParameterSet,
)
from ncmemsim.materials.optics import (
    TRAN_2016_NEAR_EDGE_PARAMETERS,
)


def _direct_parameter() -> FitParameter:
    return FitParameter(
        name="direct_prefactor_A",
        initial_value=3.68e6,
        lower_bound=1.0e6,
        upper_bound=1.0e7,
        unit="m^-1 eV^(1/2)",
        description="Direct near-edge absorption prefactor.",
    )


def _urbach_parameter() -> FitParameter:
    return FitParameter(
        name="urbach_energy_eV",
        initial_value=0.01058,
        lower_bound=0.001,
        upper_bound=0.100,
        unit="eV",
        description="Urbach energy.",
    )


def _parameter_set() -> FitParameterSet:
    return FitParameterSet(
        parameters=(
            _direct_parameter(),
            _urbach_parameter(),
        )
    )


def test_fit_parameter_normalizes_text_and_numeric_values():
    parameter = FitParameter(
        name="  parameter_a  ",
        initial_value=2,
        lower_bound=1,
        upper_bound=3,
        unit="  eV  ",
        description="  Example parameter.  ",
    )

    assert parameter.name == "parameter_a"
    assert parameter.initial_value == pytest.approx(2.0)
    assert parameter.lower_bound == pytest.approx(1.0)
    assert parameter.upper_bound == pytest.approx(3.0)
    assert parameter.unit == "eV"
    assert parameter.description == "Example parameter."


def test_fit_parameter_allows_initial_value_on_bounds():
    lower = FitParameter(
        name="lower",
        initial_value=1.0,
        lower_bound=1.0,
        upper_bound=2.0,
    )
    upper = FitParameter(
        name="upper",
        initial_value=2.0,
        lower_bound=1.0,
        upper_bound=2.0,
    )

    assert lower.initial_value == pytest.approx(lower.lower_bound)
    assert upper.initial_value == pytest.approx(upper.upper_bound)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("initial_value", float("nan")),
        ("initial_value", float("inf")),
        ("lower_bound", float("-inf")),
        ("lower_bound", float("nan")),
        ("upper_bound", float("inf")),
        ("upper_bound", float("nan")),
    ],
)
def test_fit_parameter_rejects_nonfinite_numeric_fields(
    field_name: str,
    value: float,
):
    kwargs = {
        "name": "parameter",
        "initial_value": 2.0,
        "lower_bound": 1.0,
        "upper_bound": 3.0,
    }
    kwargs[field_name] = value

    with pytest.raises(ValueError):
        FitParameter(**kwargs)


@pytest.mark.parametrize(
    ("lower_bound", "upper_bound"),
    [
        (1.0, 1.0),
        (2.0, 1.0),
    ],
)
def test_fit_parameter_requires_strictly_ordered_bounds(
    lower_bound: float,
    upper_bound: float,
):
    with pytest.raises(
        ValueError,
        match="strictly less",
    ):
        FitParameter(
            name="parameter",
            initial_value=1.0,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )


@pytest.mark.parametrize(
    "initial_value",
    [0.999, 3.001],
)
def test_fit_parameter_rejects_initial_value_outside_bounds(
    initial_value: float,
):
    with pytest.raises(
        ValueError,
        match="initial_value",
    ):
        FitParameter(
            name="parameter",
            initial_value=initial_value,
            lower_bound=1.0,
            upper_bound=3.0,
        )


@pytest.mark.parametrize("name", ["", "   "])
def test_fit_parameter_requires_nonempty_name(name: str):
    with pytest.raises(ValueError, match="name"):
        FitParameter(
            name=name,
            initial_value=2.0,
            lower_bound=1.0,
            upper_bound=3.0,
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("unit", ""),
        ("unit", "   "),
        ("description", ""),
        ("description", "   "),
    ],
)
def test_fit_parameter_rejects_empty_optional_text(
    field_name: str,
    value: str,
):
    kwargs = {
        "name": "parameter",
        "initial_value": 2.0,
        "lower_bound": 1.0,
        "upper_bound": 3.0,
        field_name: value,
    }

    with pytest.raises(ValueError, match=field_name):
        FitParameter(**kwargs)


def test_fit_parameter_contains_is_inclusive_and_rejects_nonfinite():
    parameter = FitParameter(
        name="parameter",
        initial_value=2.0,
        lower_bound=1.0,
        upper_bound=3.0,
    )

    assert parameter.contains(1.0)
    assert parameter.contains(2.0)
    assert parameter.contains(3.0)
    assert not parameter.contains(0.9)
    assert not parameter.contains(3.1)
    assert not parameter.contains(float("nan"))
    assert not parameter.contains(float("inf"))


def test_fit_parameter_to_dict_is_explicit():
    parameter = _direct_parameter()

    assert parameter.to_dict() == {
        "name": "direct_prefactor_A",
        "initial_value": 3.68e6,
        "lower_bound": 1.0e6,
        "upper_bound": 1.0e7,
        "unit": "m^-1 eV^(1/2)",
        "description": "Direct near-edge absorption prefactor.",
    }


def test_parameter_set_accepts_sequence_and_preserves_order():
    parameter_set = FitParameterSet(
        parameters=[
            _direct_parameter(),
            _urbach_parameter(),
        ]
    )

    assert isinstance(parameter_set.parameters, tuple)
    assert parameter_set.n_parameters == 2
    assert parameter_set.names == (
        "direct_prefactor_A",
        "urbach_energy_eV",
    )


def test_parameter_set_requires_at_least_one_parameter():
    with pytest.raises(ValueError, match="at least one"):
        FitParameterSet(parameters=())


def test_parameter_set_rejects_non_parameter_members():
    with pytest.raises(TypeError, match="FitParameter"):
        FitParameterSet(
            parameters=(
                _direct_parameter(),
                "not-a-parameter",  # type: ignore[arg-type]
            )
        )


def test_parameter_set_requires_unique_names():
    with pytest.raises(ValueError, match="unique"):
        FitParameterSet(
            parameters=(
                _direct_parameter(),
                FitParameter(
                    name="direct_prefactor_A",
                    initial_value=4.0e6,
                    lower_bound=1.0e6,
                    upper_bound=1.0e7,
                ),
            )
        )


def test_parameter_vectors_are_ordered_and_read_only():
    parameter_set = _parameter_set()

    initial_values = parameter_set.initial_values
    lower_bounds = parameter_set.lower_bounds
    upper_bounds = parameter_set.upper_bounds

    assert initial_values.tolist() == pytest.approx(
        [3.68e6, 0.01058]
    )
    assert lower_bounds.tolist() == pytest.approx(
        [1.0e6, 0.001]
    )
    assert upper_bounds.tolist() == pytest.approx(
        [1.0e7, 0.100]
    )

    assert not initial_values.flags.writeable
    assert not lower_bounds.flags.writeable
    assert not upper_bounds.flags.writeable

    with pytest.raises(ValueError):
        initial_values[0] = 1.0


def test_validate_values_returns_read_only_normalized_vector():
    parameter_set = _parameter_set()

    vector = parameter_set.validate_values(
        [4.0e6, 0.012]
    )

    assert vector.dtype.kind == "f"
    assert vector.tolist() == pytest.approx(
        [4.0e6, 0.012]
    )
    assert not vector.flags.writeable


def test_validate_values_accepts_exact_bounds():
    parameter_set = _parameter_set()

    lower = parameter_set.validate_values(
        parameter_set.lower_bounds
    )
    upper = parameter_set.validate_values(
        parameter_set.upper_bounds
    )

    assert lower.tolist() == pytest.approx(
        parameter_set.lower_bounds.tolist()
    )
    assert upper.tolist() == pytest.approx(
        parameter_set.upper_bounds.tolist()
    )


@pytest.mark.parametrize(
    "values",
    [
        [3.68e6],
        [3.68e6, 0.01058, 1.0],
        [[3.68e6, 0.01058]],
        [float("nan"), 0.01058],
        [float("inf"), 0.01058],
        [0.9e6, 0.01058],
        [10.1e6, 0.01058],
        [3.68e6, 0.0009],
        [3.68e6, 0.101],
    ],
)
def test_validate_values_rejects_invalid_candidate_vectors(values):
    with pytest.raises(ValueError):
        _parameter_set().validate_values(values)


def test_values_to_dict_preserves_parameter_order_and_names():
    parameter_set = _parameter_set()

    values = parameter_set.values_to_dict(
        [4.2e6, 0.0125]
    )

    assert list(values) == [
        "direct_prefactor_A",
        "urbach_energy_eV",
    ]
    assert values == {
        "direct_prefactor_A": pytest.approx(4.2e6),
        "urbach_energy_eV": pytest.approx(0.0125),
    }


def test_parameter_set_to_dict_has_explicit_schema():
    data = _parameter_set().to_dict()

    assert data["schema_version"] == 1
    assert len(data["parameters"]) == 2
    assert (
        data["parameters"][0]["name"]
        == "direct_prefactor_A"
    )
    assert (
        data["parameters"][1]["name"]
        == "urbach_energy_eV"
    )


def test_parameter_set_hash_is_deterministic():
    first = _parameter_set()
    second = _parameter_set()

    assert (
        first.specification_hash()
        == second.specification_hash()
    )
    assert len(first.specification_hash()) == 64


def test_parameter_set_hash_changes_when_bounds_change():
    baseline = _parameter_set()

    changed = FitParameterSet(
        parameters=(
            FitParameter(
                name="direct_prefactor_A",
                initial_value=3.68e6,
                lower_bound=2.0e6,
                upper_bound=1.0e7,
                unit="m^-1 eV^(1/2)",
                description=(
                    "Direct near-edge absorption prefactor."
                ),
            ),
            _urbach_parameter(),
        )
    )

    assert (
        baseline.specification_hash()
        != changed.specification_hash()
    )


def test_parameter_set_can_represent_tran_near_edge_fit_candidates():
    reference = TRAN_2016_NEAR_EDGE_PARAMETERS

    parameter_set = FitParameterSet(
        parameters=(
            FitParameter(
                name="direct_prefactor_A",
                initial_value=reference.direct_prefactor_A,
                lower_bound=1.0e6,
                upper_bound=1.0e7,
                unit="m^-1 eV^(1/2)",
            ),
            FitParameter(
                name="urbach_energy_eV",
                initial_value=reference.urbach_energy_eV,
                lower_bound=0.001,
                upper_bound=0.100,
                unit="eV",
            ),
        )
    )

    assert parameter_set.initial_values.tolist() == pytest.approx(
        [
            reference.direct_prefactor_A,
            reference.urbach_energy_eV,
        ]
    )
