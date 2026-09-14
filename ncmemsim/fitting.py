from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np


def _as_1d_finite_float_array(
    values: np.ndarray | list[float] | tuple[float, ...],
    *,
    field_name: str,
) -> np.ndarray:
    array = np.array(values, dtype=float, copy=True)

    if array.ndim != 1:
        raise ValueError(f"{field_name} must be one-dimensional.")

    if array.size == 0:
        raise ValueError(f"{field_name} cannot be empty.")

    if not np.all(np.isfinite(array)):
        raise ValueError(
            f"{field_name} must contain only finite values."
        )

    array.setflags(write=False)
    return array


@dataclass(frozen=True)
class ObjectiveEvaluation:
    """
    Deterministic least-squares objective diagnostics.

    ``residuals`` always contains raw residuals in the convention

        predicted - observed

    and therefore retains the physical units of the observable.

    ``objective_residuals`` contains the residual vector that should be
    supplied to a least-squares optimizer. When experimental uncertainty is
    supplied this vector is normalized point-by-point by that uncertainty.

    ``residual_sum_squares`` and ``root_mean_square_error`` are always based
    on the raw residuals. ``objective_sum_squares`` is based on the optimizer
    residuals and is therefore dimensionless for uncertainty-weighted data.
    """

    residuals: np.ndarray
    objective_residuals: np.ndarray
    weighted: bool
    residual_sum_squares: float
    objective_sum_squares: float
    root_mean_square_error: float
    mean_absolute_error: float
    coefficient_of_determination: float | None

    def __post_init__(self) -> None:
        residuals = _as_1d_finite_float_array(
            self.residuals,
            field_name="residuals",
        )
        objective_residuals = _as_1d_finite_float_array(
            self.objective_residuals,
            field_name="objective_residuals",
        )

        if residuals.shape != objective_residuals.shape:
            raise ValueError(
                "residuals and objective_residuals "
                "must have the same shape."
            )

        for field_name in (
            "residual_sum_squares",
            "objective_sum_squares",
            "root_mean_square_error",
            "mean_absolute_error",
        ):
            value = float(getattr(self, field_name))
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(
                    f"{field_name} must be finite and non-negative."
                )

        if self.coefficient_of_determination is not None:
            if not math.isfinite(self.coefficient_of_determination):
                raise ValueError(
                    "coefficient_of_determination must be finite "
                    "when provided."
                )

        object.__setattr__(self, "residuals", residuals)
        object.__setattr__(
            self,
            "objective_residuals",
            objective_residuals,
        )

    @property
    def n_points(self) -> int:
        return int(self.residuals.size)

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_points": self.n_points,
            "weighted": self.weighted,
            "residual_sum_squares": self.residual_sum_squares,
            "objective_sum_squares": self.objective_sum_squares,
            "root_mean_square_error": self.root_mean_square_error,
            "mean_absolute_error": self.mean_absolute_error,
            "coefficient_of_determination": (
                self.coefficient_of_determination
            ),
            "residuals": self.residuals.tolist(),
            "objective_residuals": self.objective_residuals.tolist(),
        }


def least_squares_residuals(
    observed: np.ndarray | list[float] | tuple[float, ...],
    predicted: np.ndarray | list[float] | tuple[float, ...],
    *,
    uncertainty: (
        np.ndarray | list[float] | tuple[float, ...] | None
    ) = None,
) -> np.ndarray:
    """
    Return deterministic least-squares residuals.

    Residual sign convention is ``predicted - observed``.

    If ``uncertainty`` is supplied, each residual is divided by the
    corresponding strictly positive experimental uncertainty.
    """

    observed_array = _as_1d_finite_float_array(
        observed,
        field_name="observed",
    )
    predicted_array = _as_1d_finite_float_array(
        predicted,
        field_name="predicted",
    )

    if observed_array.shape != predicted_array.shape:
        raise ValueError(
            "observed and predicted must have the same shape."
        )

    residuals = predicted_array - observed_array

    if uncertainty is not None:
        uncertainty_array = _as_1d_finite_float_array(
            uncertainty,
            field_name="uncertainty",
        )

        if uncertainty_array.shape != observed_array.shape:
            raise ValueError(
                "uncertainty must have the same shape as observed."
            )

        if np.any(uncertainty_array <= 0.0):
            raise ValueError(
                "uncertainty values must be strictly positive."
            )

        residuals = residuals / uncertainty_array

    residuals = np.array(residuals, dtype=float, copy=True)
    residuals.setflags(write=False)
    return residuals


def evaluate_least_squares_objective(
    observed: np.ndarray | list[float] | tuple[float, ...],
    predicted: np.ndarray | list[float] | tuple[float, ...],
    *,
    uncertainty: (
        np.ndarray | list[float] | tuple[float, ...] | None
    ) = None,
) -> ObjectiveEvaluation:
    """
    Evaluate raw and optimizer-facing least-squares diagnostics.

    The coefficient of determination is computed from the raw residuals
    and is returned as ``None`` when all observed values are identical,
    because R^2 is undefined in that case.
    """

    observed_array = _as_1d_finite_float_array(
        observed,
        field_name="observed",
    )
    predicted_array = _as_1d_finite_float_array(
        predicted,
        field_name="predicted",
    )

    if observed_array.shape != predicted_array.shape:
        raise ValueError(
            "observed and predicted must have the same shape."
        )

    raw_residuals = predicted_array - observed_array
    raw_residuals = np.array(
        raw_residuals,
        dtype=float,
        copy=True,
    )
    raw_residuals.setflags(write=False)

    objective_residuals = least_squares_residuals(
        observed_array,
        predicted_array,
        uncertainty=uncertainty,
    )

    residual_sum_squares = float(
        np.dot(raw_residuals, raw_residuals)
    )
    objective_sum_squares = float(
        np.dot(objective_residuals, objective_residuals)
    )

    root_mean_square_error = float(
        np.sqrt(residual_sum_squares / raw_residuals.size)
    )
    mean_absolute_error = float(
        np.mean(np.abs(raw_residuals))
    )

    centered_observed = observed_array - np.mean(observed_array)
    total_sum_squares = float(
        np.dot(centered_observed, centered_observed)
    )

    coefficient_of_determination: float | None
    if total_sum_squares == 0.0:
        coefficient_of_determination = None
    else:
        coefficient_of_determination = float(
            1.0 - residual_sum_squares / total_sum_squares
        )

    return ObjectiveEvaluation(
        residuals=raw_residuals,
        objective_residuals=objective_residuals,
        weighted=uncertainty is not None,
        residual_sum_squares=residual_sum_squares,
        objective_sum_squares=objective_sum_squares,
        root_mean_square_error=root_mean_square_error,
        mean_absolute_error=mean_absolute_error,
        coefficient_of_determination=coefficient_of_determination,
    )


__all__ = [
    "ObjectiveEvaluation",
    "evaluate_least_squares_objective",
    "least_squares_residuals",
]
