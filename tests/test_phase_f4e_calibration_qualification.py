from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from ncmemsim.calibration import (
    CalibrationCriteria,
    CalibrationCriterionResult,
    CalibrationQualification,
    qualify_calibration,
)
from ncmemsim.fit_diagnostics import (
    FitUncertaintyDiagnostics,
    analyze_fit_uncertainty,
)
from ncmemsim.fitting import (
    DeterministicFitResult,
    FitParameter,
    FitParameterSet,
    evaluate_least_squares_objective,
    run_least_squares_fit,
)


def _linear_fit() -> tuple[
    DeterministicFitResult,
    FitUncertaintyDiagnostics,
]:
    x = np.array(
        [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    )
    observed = np.array(
        [1.10, 2.95, 5.05, 6.95, 9.10, 10.90]
    )

    parameter_set = FitParameterSet(
        parameters=(
            FitParameter(
                name="slope",
                initial_value=1.5,
                lower_bound=0.0,
                upper_bound=4.0,
            ),
            FitParameter(
                name="intercept",
                initial_value=0.5,
                lower_bound=-2.0,
                upper_bound=3.0,
            ),
        )
    )

    def residuals(values: np.ndarray) -> np.ndarray:
        slope, intercept = values
        return (
            slope * x
            + intercept
            - observed
        )

    fit = run_least_squares_fit(
        parameter_set,
        residuals,
    )
    diagnostics = analyze_fit_uncertainty(
        fit
    )

    return fit, diagnostics


def _validation_objective(
    *,
    offset: float = 0.02,
):
    observed = np.array(
        [13.0, 15.0, 17.0, 19.0]
    )
    predicted = observed + np.array(
        [offset, -offset, offset, -offset]
    )

    return evaluate_least_squares_objective(
        observed,
        predicted,
    )


def _passing_criteria() -> CalibrationCriteria:
    return CalibrationCriteria(
        max_validation_rmse=0.05,
        max_validation_mae=0.05,
        min_validation_r2=0.99,
        max_scaled_condition_number=100.0,
    )


def test_criteria_require_quantitative_validation_threshold():
    with pytest.raises(
        ValueError,
        match="At least one quantitative",
    ):
        CalibrationCriteria()


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("max_validation_rmse", -1.0),
        ("max_validation_rmse", float("nan")),
        ("max_validation_mae", -1.0),
        ("max_validation_mae", float("inf")),
        ("min_validation_r2", 1.01),
        ("min_validation_r2", float("nan")),
        ("max_scaled_condition_number", 0.9),
        ("max_scaled_condition_number", float("inf")),
    ],
)
def test_criteria_reject_invalid_thresholds(
    field_name: str,
    value: float,
):
    kwargs = {
        "max_validation_rmse": 1.0,
        field_name: value,
    }

    with pytest.raises(ValueError):
        CalibrationCriteria(**kwargs)


@pytest.mark.parametrize(
    "field_name",
    [
        "require_distinct_validation_dataset",
        "require_local_identifiability",
        "require_covariance",
    ],
)
def test_criteria_require_boolean_switches(
    field_name: str,
):
    kwargs = {
        "max_validation_rmse": 1.0,
        field_name: 1,
    }

    with pytest.raises(TypeError):
        CalibrationCriteria(**kwargs)


def test_criteria_hash_is_deterministic_and_sensitive():
    first = CalibrationCriteria(
        max_validation_rmse=0.5,
        min_validation_r2=0.90,
    )
    same = CalibrationCriteria(
        max_validation_rmse=0.5,
        min_validation_r2=0.90,
    )
    changed = CalibrationCriteria(
        max_validation_rmse=0.6,
        min_validation_r2=0.90,
    )

    assert first.criteria_hash() == same.criteria_hash()
    assert first.criteria_hash() != changed.criteria_hash()


def test_qualification_passes_with_independent_validation_data():
    fit, diagnostics = _linear_fit()

    qualification = qualify_calibration(
        fit,
        diagnostics,
        fit_dataset_hash="fit-dataset-hash",
        validation_dataset_hash="validation-dataset-hash",
        validation_objective=_validation_objective(),
        criteria=_passing_criteria(),
    )

    assert qualification.eligible_for_calibration is True
    assert qualification.failed_criteria == ()
    assert all(
        result.passed
        for result in qualification.criterion_results
    )


def test_same_fit_and_validation_dataset_fails_by_default():
    fit, diagnostics = _linear_fit()

    qualification = qualify_calibration(
        fit,
        diagnostics,
        fit_dataset_hash="same-dataset-hash",
        validation_dataset_hash="same-dataset-hash",
        validation_objective=_validation_objective(),
        criteria=_passing_criteria(),
    )

    assert qualification.eligible_for_calibration is False
    assert "distinct_validation_dataset" in (
        qualification.failed_criteria
    )


def test_distinct_dataset_requirement_can_be_explicitly_disabled():
    fit, diagnostics = _linear_fit()

    criteria = CalibrationCriteria(
        max_validation_rmse=0.05,
        require_distinct_validation_dataset=False,
    )

    qualification = qualify_calibration(
        fit,
        diagnostics,
        fit_dataset_hash="same-dataset-hash",
        validation_dataset_hash="same-dataset-hash",
        validation_objective=_validation_objective(),
        criteria=criteria,
    )

    assert qualification.eligible_for_calibration is True
    assert all(
        result.name != "distinct_validation_dataset"
        for result in qualification.criterion_results
    )


def test_validation_rmse_failure_blocks_qualification():
    fit, diagnostics = _linear_fit()

    criteria = CalibrationCriteria(
        max_validation_rmse=0.01,
    )

    qualification = qualify_calibration(
        fit,
        diagnostics,
        fit_dataset_hash="fit",
        validation_dataset_hash="validation",
        validation_objective=_validation_objective(
            offset=0.02
        ),
        criteria=criteria,
    )

    assert qualification.eligible_for_calibration is False
    assert "validation_rmse" in qualification.failed_criteria


def test_validation_mae_failure_blocks_qualification():
    fit, diagnostics = _linear_fit()

    criteria = CalibrationCriteria(
        max_validation_mae=0.01,
    )

    qualification = qualify_calibration(
        fit,
        diagnostics,
        fit_dataset_hash="fit",
        validation_dataset_hash="validation",
        validation_objective=_validation_objective(
            offset=0.02
        ),
        criteria=criteria,
    )

    assert qualification.eligible_for_calibration is False
    assert "validation_mae" in qualification.failed_criteria


def test_validation_r2_failure_blocks_qualification():
    fit, diagnostics = _linear_fit()

    objective = evaluate_least_squares_objective(
        observed=np.array(
            [0.0, 1.0, 2.0, 3.0]
        ),
        predicted=np.array(
            [0.0, 1.0, 2.0, 4.0]
        ),
    )

    criteria = CalibrationCriteria(
        min_validation_r2=0.95,
    )

    qualification = qualify_calibration(
        fit,
        diagnostics,
        fit_dataset_hash="fit",
        validation_dataset_hash="validation",
        validation_objective=objective,
        criteria=criteria,
    )

    assert qualification.eligible_for_calibration is False
    assert "validation_r2" in qualification.failed_criteria


def test_constant_validation_data_fail_explicit_r2_criterion():
    fit, diagnostics = _linear_fit()

    objective = evaluate_least_squares_objective(
        observed=np.array(
            [3.0, 3.0, 3.0]
        ),
        predicted=np.array(
            [3.0, 3.0, 3.0]
        ),
    )

    criteria = CalibrationCriteria(
        min_validation_r2=0.0,
    )

    qualification = qualify_calibration(
        fit,
        diagnostics,
        fit_dataset_hash="fit",
        validation_dataset_hash="validation",
        validation_objective=objective,
        criteria=criteria,
    )

    r2_result = next(
        result
        for result in qualification.criterion_results
        if result.name == "validation_r2"
    )

    assert r2_result.observed_value is None
    assert r2_result.passed is False
    assert qualification.eligible_for_calibration is False


def test_condition_number_failure_blocks_qualification():
    fit, diagnostics = _linear_fit()

    assert diagnostics.scaled_condition_number >= 1.0

    criteria = CalibrationCriteria(
        max_validation_rmse=0.05,
        max_scaled_condition_number=1.0,
    )

    qualification = qualify_calibration(
        fit,
        diagnostics,
        fit_dataset_hash="fit",
        validation_dataset_hash="validation",
        validation_objective=_validation_objective(),
        criteria=criteria,
    )

    assert qualification.eligible_for_calibration is False
    assert "scaled_condition_number" in (
        qualification.failed_criteria
    )


def test_rank_deficient_fit_fails_identifiability_and_covariance():
    x = np.array(
        [0.0, 1.0, 2.0, 3.0, 4.0]
    )
    observed = 3.0 * x

    parameter_set = FitParameterSet(
        parameters=(
            FitParameter(
                name="a",
                initial_value=1.0,
                lower_bound=-5.0,
                upper_bound=5.0,
            ),
            FitParameter(
                name="b",
                initial_value=1.0,
                lower_bound=-5.0,
                upper_bound=5.0,
            ),
        )
    )

    def residuals(values: np.ndarray) -> np.ndarray:
        a, b = values
        return (a + b) * x - observed

    fit = run_least_squares_fit(
        parameter_set,
        residuals,
    )
    diagnostics = analyze_fit_uncertainty(
        fit
    )

    assert diagnostics.locally_identifiable is False
    assert diagnostics.covariance_available is False

    qualification = qualify_calibration(
        fit,
        diagnostics,
        fit_dataset_hash="fit",
        validation_dataset_hash="validation",
        validation_objective=_validation_objective(),
        criteria=CalibrationCriteria(
            max_validation_rmse=0.05,
        ),
    )

    assert qualification.eligible_for_calibration is False
    assert "local_identifiability" in (
        qualification.failed_criteria
    )
    assert "covariance_available" in (
        qualification.failed_criteria
    )


def test_rank_and_covariance_requirements_can_be_disabled_explicitly():
    x = np.array(
        [0.0, 1.0, 2.0, 3.0, 4.0]
    )
    observed = 3.0 * x

    parameter_set = FitParameterSet(
        parameters=(
            FitParameter(
                name="a",
                initial_value=1.0,
                lower_bound=-5.0,
                upper_bound=5.0,
            ),
            FitParameter(
                name="b",
                initial_value=1.0,
                lower_bound=-5.0,
                upper_bound=5.0,
            ),
        )
    )

    def residuals(values: np.ndarray) -> np.ndarray:
        a, b = values
        return (a + b) * x - observed

    fit = run_least_squares_fit(
        parameter_set,
        residuals,
    )
    diagnostics = analyze_fit_uncertainty(
        fit
    )

    criteria = CalibrationCriteria(
        max_validation_rmse=0.05,
        require_local_identifiability=False,
        require_covariance=False,
    )

    qualification = qualify_calibration(
        fit,
        diagnostics,
        fit_dataset_hash="fit",
        validation_dataset_hash="validation",
        validation_objective=_validation_objective(),
        criteria=criteria,
    )

    assert qualification.eligible_for_calibration is True


def test_qualification_serialization_is_auditable():
    fit, diagnostics = _linear_fit()

    qualification = qualify_calibration(
        fit,
        diagnostics,
        fit_dataset_hash="fit-hash",
        validation_dataset_hash="validation-hash",
        validation_objective=_validation_objective(),
        criteria=_passing_criteria(),
    )

    data = qualification.to_dict()

    assert data["schema_version"] == 1
    assert (
        data["qualification_type"]
        == "fit-validation-calibration-qualification"
    )
    assert data["eligible_for_calibration"] is True
    assert data["failed_criteria"] == []
    assert data["fit_dataset_hash"] == "fit-hash"
    assert (
        data["validation_dataset_hash"]
        == "validation-hash"
    )
    assert (
        data["criteria_hash"]
        == qualification.criteria.criteria_hash()
    )
    assert (
        data["validation_objective"]["n_points"]
        == 4
    )
    assert (
        data["uncertainty_diagnostics"][
            "locally_identifiable"
        ]
        is True
    )


def test_qualification_hash_is_deterministic():
    fit, diagnostics = _linear_fit()

    first = qualify_calibration(
        fit,
        diagnostics,
        fit_dataset_hash="fit-hash",
        validation_dataset_hash="validation-hash",
        validation_objective=_validation_objective(),
        criteria=_passing_criteria(),
    )
    second = qualify_calibration(
        fit,
        diagnostics,
        fit_dataset_hash="fit-hash",
        validation_dataset_hash="validation-hash",
        validation_objective=_validation_objective(),
        criteria=_passing_criteria(),
    )

    assert (
        first.qualification_hash()
        == second.qualification_hash()
    )


def test_qualification_rejects_mismatched_diagnostics():
    fit, diagnostics = _linear_fit()

    mismatched = replace(
        diagnostics,
        parameter_names=(
            "intercept",
            "slope",
        ),
    )

    with pytest.raises(
        ValueError,
        match="parameter names",
    ):
        qualify_calibration(
            fit,
            mismatched,
            fit_dataset_hash="fit",
            validation_dataset_hash="validation",
            validation_objective=_validation_objective(),
            criteria=_passing_criteria(),
        )


def test_qualification_requires_nonempty_dataset_hashes():
    fit, diagnostics = _linear_fit()

    with pytest.raises(
        ValueError,
        match="fit_dataset_hash",
    ):
        qualify_calibration(
            fit,
            diagnostics,
            fit_dataset_hash=" ",
            validation_dataset_hash="validation",
            validation_objective=_validation_objective(),
            criteria=_passing_criteria(),
        )


def test_criterion_result_normalizes_text():
    result = CalibrationCriterionResult(
        name="  validation_rmse  ",
        passed=True,
        observed_value=0.1,
        comparison="  <=  ",
        threshold=0.2,
        notes="  example  ",
    )

    assert result.name == "validation_rmse"
    assert result.comparison == "<="
    assert result.notes == "example"


def test_qualification_object_rejects_duplicate_criterion_names():
    fit, diagnostics = _linear_fit()
    objective = _validation_objective()
    criteria = _passing_criteria()

    result = CalibrationCriterionResult(
        name="duplicate",
        passed=True,
        observed_value=True,
        comparison="is_true",
        threshold=True,
    )

    with pytest.raises(
        ValueError,
        match="names must be unique",
    ):
        CalibrationQualification(
            fit_dataset_hash="fit",
            validation_dataset_hash="validation",
            criteria=criteria,
            validation_objective=objective,
            uncertainty_diagnostics=diagnostics,
            criterion_results=(
                result,
                result,
            ),
        )
