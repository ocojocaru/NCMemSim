from dataclasses import FrozenInstanceError, replace

import pytest

from ncmemsim.ensemble import MatrixCorrelation
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def provenance():
    return ParameterProvenance(
        source="Phase K correlation contract test",
        status=ParameterStatus.ASSUMED,
        notes="Synthetic modelling assumption",
    )


def correlation():
    return MatrixCorrelation(
        variable_names=(
            "diameter",
            "volume_fraction",
            "trap_density",
        ),
        matrix=(
            (1.0, 0.5, 0.2),
            (0.5, 1.0, -0.1),
            (0.2, -0.1, 1.0),
        ),
        provenance=provenance(),
        applicability=(
            "Synthetic latent Gaussian correlation "
            "for contract validation"
        ),
    )


def test_matrix_correlation_identity():
    item = correlation()

    assert item.kind == "gaussian_copula"
    assert (
        item.representation
        == "latent_gaussian_pearson"
    )
    assert item.schema_version == "ensemble-dependence-v1"
    assert item.numerical_tolerance == 1.0e-12


def test_matrix_correlation_hash_is_canonical():
    item = correlation()

    assert item.definition_hash == canonical_hash(
        item.to_dict()
    )


def test_matrix_correlation_round_trip():
    original = correlation()

    restored = MatrixCorrelation.from_dict(
        original.to_dict()
    )

    assert restored == original
    assert restored.to_dict() == original.to_dict()
    assert restored.definition_hash == original.definition_hash


def test_numeric_matrix_entries_are_normalized_to_float():
    item = MatrixCorrelation(
        variable_names=("a", "b"),
        matrix=(
            (1, 0),
            (0, 1),
        ),
        provenance=provenance(),
        applicability="Identity correlation",
    )

    assert item.matrix == (
        (1.0, 0.0),
        (0.0, 1.0),
    )

    assert all(
        type(value) is float
        for row in item.matrix
        for value in row
    )


def test_requires_at_least_two_variables():
    with pytest.raises(ValueError):
        MatrixCorrelation(
            variable_names=("a",),
            matrix=((1.0,),),
            provenance=provenance(),
            applicability="Invalid one-variable correlation",
        )


def test_duplicate_variable_names_are_rejected():
    with pytest.raises(ValueError):
        MatrixCorrelation(
            variable_names=("a", "a"),
            matrix=(
                (1.0, 0.0),
                (0.0, 1.0),
            ),
            provenance=provenance(),
            applicability="Duplicate names",
        )


def test_matrix_dimension_must_match_variable_names():
    with pytest.raises(ValueError):
        MatrixCorrelation(
            variable_names=("a", "b", "c"),
            matrix=(
                (1.0, 0.0),
                (0.0, 1.0),
            ),
            provenance=provenance(),
            applicability="Wrong dimension",
        )


def test_matrix_must_be_square():
    with pytest.raises(ValueError):
        MatrixCorrelation(
            variable_names=("a", "b"),
            matrix=(
                (1.0, 0.0),
                (0.0,),
            ),
            provenance=provenance(),
            applicability="Nonsquare matrix",
        )


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        -float("inf"),
    ],
)
def test_nonfinite_matrix_entries_are_rejected(value):
    with pytest.raises(ValueError):
        MatrixCorrelation(
            variable_names=("a", "b"),
            matrix=(
                (1.0, value),
                (value, 1.0),
            ),
            provenance=provenance(),
            applicability="Nonfinite matrix",
        )


@pytest.mark.parametrize(
    "value",
    [
        -1.0001,
        1.0001,
    ],
)
def test_matrix_entries_must_lie_in_correlation_range(value):
    with pytest.raises(ValueError):
        MatrixCorrelation(
            variable_names=("a", "b"),
            matrix=(
                (1.0, value),
                (value, 1.0),
            ),
            provenance=provenance(),
            applicability="Out-of-range correlation",
        )


def test_diagonal_must_be_one_within_tolerance():
    with pytest.raises(ValueError):
        MatrixCorrelation(
            variable_names=("a", "b"),
            matrix=(
                (0.99, 0.0),
                (0.0, 1.0),
            ),
            provenance=provenance(),
            applicability="Invalid diagonal",
        )


def test_small_diagonal_roundoff_within_tolerance_is_allowed():
    item = MatrixCorrelation(
        variable_names=("a", "b"),
        matrix=(
            (1.0 - 5.0e-13, 0.2),
            (0.2, 1.0),
        ),
        provenance=provenance(),
        applicability="Roundoff-tolerant diagonal",
    )

    assert item.matrix[0][0] == 1.0 - 5.0e-13


def test_asymmetry_beyond_tolerance_is_rejected():
    with pytest.raises(ValueError):
        MatrixCorrelation(
            variable_names=("a", "b"),
            matrix=(
                (1.0, 0.2),
                (0.2001, 1.0),
            ),
            provenance=provenance(),
            applicability="Asymmetric matrix",
        )


def test_asymmetry_within_tolerance_is_allowed_without_repair():
    upper = 0.2
    lower = 0.2 + 5.0e-13

    item = MatrixCorrelation(
        variable_names=("a", "b"),
        matrix=(
            (1.0, upper),
            (lower, 1.0),
        ),
        provenance=provenance(),
        applicability="Roundoff asymmetry",
    )

    assert item.matrix[0][1] == upper
    assert item.matrix[1][0] == lower


def test_non_positive_semidefinite_matrix_is_rejected():
    with pytest.raises(ValueError):
        MatrixCorrelation(
            variable_names=("a", "b", "c"),
            matrix=(
                (1.0, 0.9, 0.9),
                (0.9, 1.0, -0.9),
                (0.9, -0.9, 1.0),
            ),
            provenance=provenance(),
            applicability="Intentionally non-PSD matrix",
        )


@pytest.mark.parametrize(
    "tolerance",
    [
        0.0,
        -1.0e-12,
        float("nan"),
        float("inf"),
    ],
)
def test_tolerance_must_be_positive_and_finite(tolerance):
    with pytest.raises(ValueError):
        replace(
            correlation(),
            numerical_tolerance=tolerance,
        )


@pytest.mark.parametrize(
    "tolerance",
    [
        True,
        "1e-12",
        None,
    ],
)
def test_tolerance_must_be_real_number(tolerance):
    with pytest.raises(TypeError):
        replace(
            correlation(),
            numerical_tolerance=tolerance,
        )


@pytest.mark.parametrize(
    "field, value",
    [
        ("kind", "pearson"),
        ("representation", "physical_pearson"),
        ("schema_version", "ensemble-dependence-v2"),
    ],
)
def test_correlation_identity_fields_are_fixed(field, value):
    with pytest.raises(ValueError):
        replace(
            correlation(),
            **{field: value},
        )


def test_unknown_serialized_field_is_rejected():
    data = correlation().to_dict()
    data["extra"] = 1

    with pytest.raises(ValueError):
        MatrixCorrelation.from_dict(data)


def test_missing_serialized_field_is_rejected():
    data = correlation().to_dict()
    del data["representation"]

    with pytest.raises(ValueError):
        MatrixCorrelation.from_dict(data)


def test_serialized_variable_names_must_be_list():
    data = correlation().to_dict()
    data["variable_names"] = tuple(
        data["variable_names"]
    )

    with pytest.raises(TypeError):
        MatrixCorrelation.from_dict(data)


def test_serialized_matrix_rows_must_be_lists():
    data = correlation().to_dict()
    data["matrix"][0] = tuple(
        data["matrix"][0]
    )

    with pytest.raises(TypeError):
        MatrixCorrelation.from_dict(data)


def test_matrix_correlation_is_frozen():
    item = correlation()

    with pytest.raises(FrozenInstanceError):
        item.matrix = (
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        )
