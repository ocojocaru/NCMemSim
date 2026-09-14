from __future__ import annotations

from dataclasses import replace
import math

import numpy as np
import pytest

from ncmemsim.fit_diagnostics import (
    FitUncertaintyDiagnostics,
    analyze_fit_uncertainty,
)
from ncmemsim.fitting import (
    FitParameter,
    FitParameterSet,
    LeastSquaresConfig,
    run_least_squares_fit,
)


def _linear_parameter_set() -> FitParameterSet:
    return FitParameterSet(
        parameters=(
            FitParameter(
                name="intercept",
                initial_value=0.0,
                lower_bound=-10.0,
                upper_bound=10.0,
            ),
            FitParameter(
                name="slope",
                initial_value=0.0,
                lower_bound=-10.0,
                upper_bound=10.0,
            ),
        )
    )


def _linear_fit():
    x = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    true_intercept = 2.0
    true_slope = 0.5
    residual_at_truth = np.array([1.0, -2.0, 2.0, -2.0, 1.0])
    observed = (
        true_intercept
        + true_slope * x
        - residual_at_truth
    )

    def residuals(values: np.ndarray) -> np.ndarray:
        intercept, slope = values
        return intercept + slope * x - observed

    return run_least_squares_fit(
        _linear_parameter_set(),
        residuals,
    )


def test_runner_stores_physical_parameter_jacobian():
    parameter_set = FitParameterSet(
        parameters=(
            FitParameter(
                name="x",
                initial_value=3.0,
                lower_bound=1.0,
                upper_bound=9.0,
            ),
        )
    )

    result = run_least_squares_fit(
        parameter_set,
        lambda values: np.array(
            [
                2.0 * values[0] - 8.0,
                3.0 * values[0] - 12.0,
            ]
        ),
    )

    assert result.jacobian is not None
    assert result.jacobian.shape == (2, 1)
    assert result.jacobian[:, 0].tolist() == pytest.approx(
        [2.0, 3.0],
        rel=1.0e-6,
        abs=1.0e-8,
    )
    assert not result.jacobian.flags.writeable


def test_result_to_dict_labels_jacobian_parameterization():
    result = _linear_fit()
    data = result.to_dict()

    assert data["jacobian_parameterization"] == (
        "physical-parameter-values"
    )
    assert data["jacobian"] is not None
    assert len(data["jacobian"]) == 5
    assert len(data["jacobian"][0]) == 2


def test_linear_fit_has_expected_rank_and_degrees_of_freedom():
    diagnostics = analyze_fit_uncertainty(
        _linear_fit()
    )

    assert isinstance(
        diagnostics,
        FitUncertaintyDiagnostics,
    )
    assert diagnostics.parameter_names == (
        "intercept",
        "slope",
    )
    assert diagnostics.n_observations == 5
    assert diagnostics.n_parameters == 2
    assert diagnostics.jacobian_rank == 2
    assert diagnostics.jacobian_full_rank is True
    assert diagnostics.locally_identifiable is True
    assert diagnostics.degrees_of_freedom == 3
    assert diagnostics.active_bound_count == 0
    assert diagnostics.bound_constrained is False


def test_linear_fit_condition_number_uses_bound_scaled_jacobian():
    diagnostics = analyze_fit_uncertainty(
        _linear_fit()
    )

    assert diagnostics.scaled_singular_values.tolist() == pytest.approx(
        [20.0 * math.sqrt(10.0), 20.0 * math.sqrt(5.0)],
        rel=1.0e-6,
    )
    assert diagnostics.scaled_condition_number == pytest.approx(
        math.sqrt(2.0),
        rel=1.0e-6,
    )


def test_linear_fit_covariance_matches_analytical_solution():
    diagnostics = analyze_fit_uncertainty(
        _linear_fit()
    )

    assert diagnostics.residual_variance == pytest.approx(
        14.0 / 3.0,
        rel=1.0e-6,
    )
    assert diagnostics.covariance_available is True
    assert diagnostics.covariance_matrix is not None
    assert diagnostics.standard_errors is not None
    assert diagnostics.correlation_matrix is not None

    expected_covariance = np.array(
        [
            [14.0 / 15.0, 0.0],
            [0.0, 14.0 / 30.0],
        ]
    )

    assert diagnostics.covariance_matrix == pytest.approx(
        expected_covariance,
        rel=1.0e-5,
        abs=1.0e-8,
    )
    assert diagnostics.standard_errors.tolist() == pytest.approx(
        [
            math.sqrt(14.0 / 15.0),
            math.sqrt(14.0 / 30.0),
        ],
        rel=1.0e-5,
    )
    assert diagnostics.correlation_matrix == pytest.approx(
        np.eye(2),
        abs=1.0e-7,
    )


def test_parameter_standard_errors_preserve_parameter_names():
    diagnostics = analyze_fit_uncertainty(
        _linear_fit()
    )

    standard_errors = diagnostics.parameter_standard_errors
    assert standard_errors is not None
    assert list(standard_errors) == [
        "intercept",
        "slope",
    ]
    assert standard_errors["intercept"] == pytest.approx(
        math.sqrt(14.0 / 15.0),
        rel=1.0e-5,
    )


def test_diagnostic_arrays_are_read_only():
    diagnostics = analyze_fit_uncertainty(
        _linear_fit()
    )

    arrays = [
        diagnostics.scaled_singular_values,
        diagnostics.covariance_matrix,
        diagnostics.standard_errors,
        diagnostics.correlation_matrix,
    ]

    for array in arrays:
        assert array is not None
        assert not array.flags.writeable

    with pytest.raises(ValueError):
        diagnostics.scaled_singular_values[0] = 0.0


def test_exact_fit_can_have_zero_covariance_but_defined_correlation():
    x = np.array([-1.0, 0.0, 1.0, 2.0])
    observed = 2.0 + 0.5 * x

    result = run_least_squares_fit(
        _linear_parameter_set(),
        lambda values: (
            values[0] + values[1] * x - observed
        ),
    )

    diagnostics = analyze_fit_uncertainty(result)

    assert diagnostics.residual_variance == pytest.approx(
        0.0,
        abs=1.0e-18,
    )
    assert diagnostics.covariance_matrix is not None
    assert diagnostics.standard_errors is not None
    assert diagnostics.correlation_matrix is not None
    assert diagnostics.standard_errors.tolist() == pytest.approx(
        [0.0, 0.0],
        abs=1.0e-9,
    )
    assert np.allclose(
        np.diag(diagnostics.correlation_matrix),
        1.0,
    )


def test_rank_deficient_fit_is_not_locally_identifiable():
    parameter_set = _linear_parameter_set()

    result = run_least_squares_fit(
        parameter_set,
        lambda values: np.array(
            [
                values[0] + values[1] - 1.0,
                2.0 * (values[0] + values[1] - 1.0),
                3.0 * (values[0] + values[1] - 1.0),
            ]
        ),
    )

    diagnostics = analyze_fit_uncertainty(result)

    assert diagnostics.jacobian_rank == 1
    assert diagnostics.jacobian_full_rank is False
    assert diagnostics.locally_identifiable is False
    assert math.isinf(
        diagnostics.scaled_condition_number
    )
    assert diagnostics.covariance_available is False
    assert diagnostics.covariance_matrix is None
    assert diagnostics.standard_errors is None
    assert diagnostics.correlation_matrix is None


def test_zero_residual_degrees_of_freedom_withholds_covariance():
    result = run_least_squares_fit(
        _linear_parameter_set(),
        lambda values: np.array(
            [
                values[0] + values[1] - 3.0,
                2.0 * values[0] - values[1] - 1.0,
            ]
        ),
    )

    diagnostics = analyze_fit_uncertainty(result)

    assert diagnostics.jacobian_rank == 2
    assert diagnostics.degrees_of_freedom == 0
    assert diagnostics.residual_variance is None
    assert diagnostics.covariance_available is False


def test_active_bound_withholds_unconstrained_covariance():
    parameter_set = FitParameterSet(
        parameters=(
            FitParameter(
                name="x",
                initial_value=0.0,
                lower_bound=-1.0,
                upper_bound=1.0,
            ),
        )
    )

    result = run_least_squares_fit(
        parameter_set,
        lambda values: np.array(
            [
                values[0] - 3.0,
                values[0] - 3.5,
                values[0] - 4.0,
            ]
        ),
    )

    diagnostics = analyze_fit_uncertainty(result)

    assert diagnostics.jacobian_rank == 1
    assert diagnostics.locally_identifiable is True
    assert diagnostics.active_bound_count == 1
    assert diagnostics.bound_constrained is True
    assert diagnostics.degrees_of_freedom == 2
    assert diagnostics.residual_variance is not None
    assert diagnostics.covariance_available is False


def test_diagnostics_to_dict_is_explicit_about_scope_and_scaling():
    diagnostics = analyze_fit_uncertainty(
        _linear_fit()
    )

    data = diagnostics.to_dict()

    assert data["schema_version"] == 1
    assert data["method"] == (
        "linearized-local-least-squares"
    )
    assert data["jacobian_scaling"] == (
        "fit-parameter-bounds-[0,1]"
    )
    assert data["covariance_parameterization"] == (
        "physical-parameter-values"
    )
    assert data["variance_scaling"] == (
        "objective-sse/degrees-of-freedom"
    )
    assert data["locally_identifiable"] is True
    assert data["covariance_available"] is True
    assert data["parameter_standard_errors"] is not None


def test_diagnostics_require_successful_fit():
    parameter_set = FitParameterSet(
        parameters=(
            FitParameter(
                name="x",
                initial_value=0.0,
                lower_bound=-10.0,
                upper_bound=10.0,
            ),
        )
    )

    failed = run_least_squares_fit(
        parameter_set,
        lambda values: np.array(
            [np.exp(values[0]) - 1000.0]
        ),
        config=LeastSquaresConfig(max_nfev=1),
    )

    assert failed.success is False

    with pytest.raises(ValueError, match="successful fit"):
        analyze_fit_uncertainty(failed)


def test_diagnostics_require_stored_jacobian():
    result = _linear_fit()
    without_jacobian = replace(
        result,
        jacobian=None,
    )

    with pytest.raises(ValueError, match="stored fit Jacobian"):
        analyze_fit_uncertainty(without_jacobian)


def test_diagnostics_require_fit_result_instance():
    with pytest.raises(
        TypeError,
        match="DeterministicFitResult",
    ):
        analyze_fit_uncertainty({})  # type: ignore[arg-type]


def test_fit_result_rejects_wrong_jacobian_shape():
    result = _linear_fit()

    with pytest.raises(ValueError, match="jacobian must have shape"):
        replace(
            result,
            jacobian=np.zeros((1, 2)),
        )


def test_fit_result_rejects_nonfinite_jacobian():
    result = _linear_fit()
    bad = np.array(result.jacobian, copy=True)
    bad[0, 0] = np.nan

    with pytest.raises(ValueError, match="finite"):
        replace(
            result,
            jacobian=bad,
        )
