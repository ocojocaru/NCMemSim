# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

import numpy as np
import pytest
import math

from ncmemsim.ensemble import MatrixCorrelation
from ncmemsim.ensemble.sampling import (
    _sample_correlated_standard_normals,
    _sequential_psd_cholesky,
    _standard_normal,
)
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def provenance():
    return ParameterProvenance(
        source="Phase K latent Gaussian test",
        status=ParameterStatus.ASSUMED,
        notes="Synthetic correlation test",
    )


def correlation(
    matrix,
    *,
    tolerance=1.0e-12,
):
    size = len(matrix)

    return MatrixCorrelation(
        variable_names=tuple(
            f"x{index}"
            for index in range(size)
        ),
        matrix=tuple(
            tuple(row)
            for row in matrix
        ),
        provenance=provenance(),
        applicability="Latent Gaussian numerical test",
        numerical_tolerance=tolerance,
    )


def reconstruct(factor):
    size = len(factor)

    return tuple(
        tuple(
            sum(
                factor[row][index]
                * factor[column][index]
                for index in range(size)
            )
            for column in range(size)
        )
        for row in range(size)
    )


def test_two_variable_factor_has_expected_values():
    spec = correlation(
        (
            (1.0, 0.6),
            (0.6, 1.0),
        )
    )

    factor = _sequential_psd_cholesky(spec)

    assert factor[0] == pytest.approx(
        (1.0, 0.0)
    )
    assert factor[1] == pytest.approx(
        (0.6, 0.8)
    )


def test_perfect_positive_correlation_is_supported():
    spec = correlation(
        (
            (1.0, 1.0),
            (1.0, 1.0),
        )
    )

    factor = _sequential_psd_cholesky(spec)

    assert factor[0] == pytest.approx(
        (1.0, 0.0)
    )
    assert factor[1] == pytest.approx(
        (1.0, 0.0)
    )


def test_perfect_negative_correlation_is_supported():
    spec = correlation(
        (
            (1.0, -1.0),
            (-1.0, 1.0),
        )
    )

    factor = _sequential_psd_cholesky(spec)

    assert factor[0] == pytest.approx(
        (1.0, 0.0)
    )
    assert factor[1] == pytest.approx(
        (-1.0, 0.0)
    )


def test_factor_reconstructs_positive_semidefinite_matrix():
    spec = correlation(
        (
            (1.0, 0.5, 0.5),
            (0.5, 1.0, 0.5),
            (0.5, 0.5, 1.0),
        )
    )

    factor = _sequential_psd_cholesky(spec)
    restored = reconstruct(factor)

    for restored_row, expected_row in zip(
        restored,
        spec.matrix,
        strict=True,
    ):
        assert restored_row == pytest.approx(
            expected_row,
            abs=1.0e-14,
        )


def test_factorization_uses_symmetric_validation_matrix():
    tolerance = 1.0e-12

    spec = correlation(
        (
            (1.0, 0.25 + 4.0e-13),
            (0.25 - 4.0e-13, 1.0),
        ),
        tolerance=tolerance,
    )

    factor = _sequential_psd_cholesky(spec)

    assert factor[1][0] == pytest.approx(
        0.25,
        abs=1.0e-15,
    )

    assert spec.matrix[0][1] != spec.matrix[1][0]


def test_latent_sampling_uses_existing_standard_normal_stream():
    factor = (
        (1.0, 0.0),
        (0.6, 0.8),
    )

    generated_rng = np.random.Generator(
        np.random.PCG64(12345)
    )

    reference_rng = np.random.Generator(
        np.random.PCG64(12345)
    )

    actual = _sample_correlated_standard_normals(
        generated_rng,
        factor,
    )

    z0 = _standard_normal(reference_rng)
    z1 = _standard_normal(reference_rng)

    expected = (
        z0,
        0.6 * z0 + 0.8 * z1,
    )

    assert actual == pytest.approx(
        expected,
        abs=1.0e-15,
    )

    assert (
        generated_rng.bit_generator.random_raw()
        == reference_rng.bit_generator.random_raw()
    )


def test_singular_positive_correlation_produces_identical_latents():
    spec = correlation(
        (
            (1.0, 1.0),
            (1.0, 1.0),
        )
    )

    factor = _sequential_psd_cholesky(spec)

    rng = np.random.Generator(
        np.random.PCG64(54321)
    )

    values = _sample_correlated_standard_normals(
        rng,
        factor,
    )

    assert values[0] == values[1]


def test_factorization_requires_matrix_correlation():
    with pytest.raises(TypeError):
        _sequential_psd_cholesky(
            object()
        )


def test_small_positive_psd_pivot_is_not_collapsed_to_zero():
    small_diagonal = 5.0e-7

    first_correlation = math.sqrt(
        1.0 - small_diagonal**2
    )

    cross_correlation = (
        small_diagonal * 0.5
    )

    spec = correlation(
        (
            (
                1.0,
                first_correlation,
                0.0,
            ),
            (
                first_correlation,
                1.0,
                cross_correlation,
            ),
            (
                0.0,
                cross_correlation,
                1.0,
            ),
        )
    )

    factor = _sequential_psd_cholesky(spec)

    assert factor[1][1] > 0.0

    restored = reconstruct(factor)

    for restored_row, expected_row in zip(
        restored,
        spec.matrix,
        strict=True,
    ):
        assert restored_row == pytest.approx(
            expected_row,
            abs=1.0e-12,
        )
