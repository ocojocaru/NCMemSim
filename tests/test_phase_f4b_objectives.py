from __future__ import annotations

import numpy as np
import pytest

from ncmemsim.experimental import (
    ExperimentalDatasetMetadata,
    OpticalAbsorptionDataset,
)
from ncmemsim.fitting import (
    ObjectiveEvaluation,
    evaluate_least_squares_objective,
    least_squares_residuals,
)


def test_unweighted_residual_sign_is_predicted_minus_observed():
    residuals = least_squares_residuals(
        observed=[10.0, 20.0, 30.0],
        predicted=[12.0, 19.0, 30.0],
    )

    assert residuals.tolist() == [2.0, -1.0, 0.0]


def test_uncertainty_weighted_residuals_are_normalized_pointwise():
    residuals = least_squares_residuals(
        observed=[10.0, 20.0, 30.0],
        predicted=[12.0, 19.0, 33.0],
        uncertainty=[2.0, 0.5, 3.0],
    )

    assert residuals.tolist() == pytest.approx(
        [1.0, -2.0, 1.0]
    )


def test_residual_array_is_read_only():
    residuals = least_squares_residuals(
        observed=[1.0, 2.0],
        predicted=[1.5, 2.5],
    )

    assert not residuals.flags.writeable

    with pytest.raises(ValueError):
        residuals[0] = 0.0


def test_evaluation_reports_raw_metrics():
    result = evaluate_least_squares_objective(
        observed=[1.0, 2.0, 3.0],
        predicted=[2.0, 2.0, 2.0],
    )

    assert isinstance(result, ObjectiveEvaluation)
    assert result.weighted is False
    assert result.n_points == 3
    assert result.residuals.tolist() == [1.0, 0.0, -1.0]
    assert result.objective_residuals.tolist() == [
        1.0,
        0.0,
        -1.0,
    ]
    assert result.residual_sum_squares == pytest.approx(2.0)
    assert result.objective_sum_squares == pytest.approx(2.0)
    assert result.root_mean_square_error == pytest.approx(
        np.sqrt(2.0 / 3.0)
    )
    assert result.mean_absolute_error == pytest.approx(2.0 / 3.0)
    assert result.coefficient_of_determination == pytest.approx(0.0)


def test_weighting_changes_objective_but_not_raw_fit_metrics():
    unweighted = evaluate_least_squares_objective(
        observed=[10.0, 20.0],
        predicted=[12.0, 19.0],
    )
    weighted = evaluate_least_squares_objective(
        observed=[10.0, 20.0],
        predicted=[12.0, 19.0],
        uncertainty=[2.0, 0.5],
    )

    assert weighted.weighted is True

    assert weighted.residuals.tolist() == pytest.approx(
        unweighted.residuals.tolist()
    )
    assert weighted.residual_sum_squares == pytest.approx(
        unweighted.residual_sum_squares
    )
    assert weighted.root_mean_square_error == pytest.approx(
        unweighted.root_mean_square_error
    )
    assert weighted.mean_absolute_error == pytest.approx(
        unweighted.mean_absolute_error
    )
    assert weighted.coefficient_of_determination == pytest.approx(
        unweighted.coefficient_of_determination
    )

    assert weighted.objective_residuals.tolist() == pytest.approx(
        [1.0, -2.0]
    )
    assert weighted.objective_sum_squares == pytest.approx(5.0)
    assert unweighted.objective_sum_squares == pytest.approx(5.0)


def test_perfect_fit_has_zero_errors_and_r_squared_one():
    result = evaluate_least_squares_objective(
        observed=[2.0, 4.0, 8.0],
        predicted=[2.0, 4.0, 8.0],
    )

    assert result.residual_sum_squares == pytest.approx(0.0)
    assert result.objective_sum_squares == pytest.approx(0.0)
    assert result.root_mean_square_error == pytest.approx(0.0)
    assert result.mean_absolute_error == pytest.approx(0.0)
    assert result.coefficient_of_determination == pytest.approx(1.0)


def test_r_squared_can_be_negative_for_poor_predictions():
    result = evaluate_least_squares_objective(
        observed=[1.0, 2.0, 3.0],
        predicted=[10.0, 10.0, 10.0],
    )

    assert result.coefficient_of_determination is not None
    assert result.coefficient_of_determination < 0.0


def test_r_squared_is_none_for_constant_observations():
    result = evaluate_least_squares_objective(
        observed=[5.0, 5.0, 5.0],
        predicted=[5.0, 5.5, 4.5],
    )

    assert result.coefficient_of_determination is None


def test_evaluation_to_dict_is_serializable_and_explicit():
    result = evaluate_least_squares_objective(
        observed=[1.0, 2.0],
        predicted=[1.5, 1.5],
        uncertainty=[0.5, 0.25],
    )

    data = result.to_dict()

    assert data["n_points"] == 2
    assert data["weighted"] is True
    assert data["residuals"] == [0.5, -0.5]
    assert data["objective_residuals"] == [1.0, -2.0]
    assert data["residual_sum_squares"] == pytest.approx(0.5)
    assert data["objective_sum_squares"] == pytest.approx(5.0)


def test_objective_accepts_optical_dataset_arrays_directly():
    metadata = ExperimentalDatasetMetadata(
        dataset_id="objective-optical-test",
        source="synthetic test",
    )

    dataset = OpticalAbsorptionDataset(
        wavelength_nm=np.array([1500.0, 1750.0, 2000.0]),
        absorption_coefficient_m_inv=np.array(
            [8.0e5, 6.0e5, 4.0e5],
        ),
        absorption_uncertainty_m_inv=np.array(
            [2.0e4, 2.0e4, 4.0e4],
        ),
        sn_fraction=0.05,
        metadata=metadata,
    )

    predicted = np.array([8.2e5, 5.8e5, 4.4e5])

    result = evaluate_least_squares_objective(
        observed=dataset.absorption_coefficient_m_inv,
        predicted=predicted,
        uncertainty=dataset.absorption_uncertainty_m_inv,
    )

    assert result.weighted is True
    assert result.residuals.tolist() == pytest.approx(
        [2.0e4, -2.0e4, 4.0e4]
    )
    assert result.objective_residuals.tolist() == pytest.approx(
        [1.0, -1.0, 1.0]
    )
    assert result.objective_sum_squares == pytest.approx(3.0)


@pytest.mark.parametrize(
    ("observed", "predicted"),
    [
        ([], []),
        ([1.0, 2.0], [1.0]),
        ([[1.0, 2.0]], [1.0, 2.0]),
        ([1.0, 2.0], [[1.0, 2.0]]),
        ([1.0, float("nan")], [1.0, 2.0]),
        ([1.0, float("inf")], [1.0, 2.0]),
        ([1.0, 2.0], [1.0, float("nan")]),
        ([1.0, 2.0], [1.0, float("inf")]),
    ],
)
def test_residuals_reject_invalid_primary_arrays(
    observed,
    predicted,
):
    with pytest.raises(ValueError):
        least_squares_residuals(
            observed=observed,
            predicted=predicted,
        )


@pytest.mark.parametrize(
    "uncertainty",
    [
        [1.0],
        [0.0, 1.0],
        [-1.0, 1.0],
        [float("nan"), 1.0],
        [float("inf"), 1.0],
        [[1.0, 1.0]],
    ],
)
def test_residuals_reject_invalid_uncertainty(uncertainty):
    with pytest.raises(ValueError):
        least_squares_residuals(
            observed=[1.0, 2.0],
            predicted=[1.0, 2.0],
            uncertainty=uncertainty,
        )


def test_evaluation_rejects_shape_mismatch():
    with pytest.raises(ValueError):
        evaluate_least_squares_objective(
            observed=[1.0, 2.0],
            predicted=[1.0],
        )


def test_objective_evaluation_copies_input_arrays():
    residuals = np.array([1.0, -1.0])
    objective_residuals = np.array([2.0, -2.0])

    result = ObjectiveEvaluation(
        residuals=residuals,
        objective_residuals=objective_residuals,
        weighted=True,
        residual_sum_squares=2.0,
        objective_sum_squares=8.0,
        root_mean_square_error=1.0,
        mean_absolute_error=1.0,
        coefficient_of_determination=0.5,
    )

    residuals[0] = 999.0
    objective_residuals[0] = 999.0

    assert result.residuals.tolist() == [1.0, -1.0]
    assert result.objective_residuals.tolist() == [2.0, -2.0]
    assert not result.residuals.flags.writeable
    assert not result.objective_residuals.flags.writeable


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("residual_sum_squares", -1.0),
        ("residual_sum_squares", float("nan")),
        ("objective_sum_squares", -1.0),
        ("root_mean_square_error", -1.0),
        ("mean_absolute_error", float("inf")),
    ],
)
def test_objective_evaluation_rejects_invalid_metrics(
    field_name: str,
    value: float,
):
    kwargs = {
        "residuals": np.array([0.0, 1.0]),
        "objective_residuals": np.array([0.0, 1.0]),
        "weighted": False,
        "residual_sum_squares": 1.0,
        "objective_sum_squares": 1.0,
        "root_mean_square_error": np.sqrt(0.5),
        "mean_absolute_error": 0.5,
        "coefficient_of_determination": 0.5,
    }
    kwargs[field_name] = value

    with pytest.raises(ValueError):
        ObjectiveEvaluation(**kwargs)


def test_objective_evaluation_rejects_nonfinite_r_squared():
    with pytest.raises(ValueError):
        ObjectiveEvaluation(
            residuals=np.array([0.0, 1.0]),
            objective_residuals=np.array([0.0, 1.0]),
            weighted=False,
            residual_sum_squares=1.0,
            objective_sum_squares=1.0,
            root_mean_square_error=np.sqrt(0.5),
            mean_absolute_error=0.5,
            coefficient_of_determination=float("nan"),
        )


def test_objective_evaluation_requires_matching_residual_shapes():
    with pytest.raises(ValueError):
        ObjectiveEvaluation(
            residuals=np.array([0.0, 1.0]),
            objective_residuals=np.array([0.0]),
            weighted=False,
            residual_sum_squares=1.0,
            objective_sum_squares=1.0,
            root_mean_square_error=np.sqrt(0.5),
            mean_absolute_error=0.5,
            coefficient_of_determination=0.5,
        )
