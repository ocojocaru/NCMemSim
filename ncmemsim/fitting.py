from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Sequence

import numpy as np

from .reproducibility import canonical_hash


def _as_1d_finite_float_array(
    values: np.ndarray | Sequence[float],
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


def _normalize_required_text(
    value: str,
    *,
    field_name: str,
) -> str:
    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field_name} cannot be empty.")

    return normalized


def _normalize_optional_text(
    value: str | None,
    *,
    field_name: str,
) -> str | None:
    if value is None:
        return None

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field_name} cannot be empty.")

    return normalized


@dataclass(frozen=True)
class FitParameter:
    """
    Ordered scalar fit-parameter specification.

    Bounds are finite and strictly ordered. The initial value may lie on
    either bound, but it must not lie outside the interval.
    """

    name: str
    initial_value: float
    lower_bound: float
    upper_bound: float
    unit: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        name = _normalize_required_text(
            self.name,
            field_name="name",
        )
        unit = _normalize_optional_text(
            self.unit,
            field_name="unit",
        )
        description = _normalize_optional_text(
            self.description,
            field_name="description",
        )

        initial_value = float(self.initial_value)
        lower_bound = float(self.lower_bound)
        upper_bound = float(self.upper_bound)

        for field_name, value in {
            "initial_value": initial_value,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
        }.items():
            if not math.isfinite(value):
                raise ValueError(
                    f"{field_name} must be finite."
                )

        if lower_bound >= upper_bound:
            raise ValueError(
                "lower_bound must be strictly less than upper_bound."
            )

        if not lower_bound <= initial_value <= upper_bound:
            raise ValueError(
                "initial_value must lie within "
                "[lower_bound, upper_bound]."
            )

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "initial_value", initial_value)
        object.__setattr__(self, "lower_bound", lower_bound)
        object.__setattr__(self, "upper_bound", upper_bound)

    def contains(self, value: float) -> bool:
        candidate = float(value)

        return (
            math.isfinite(candidate)
            and self.lower_bound <= candidate <= self.upper_bound
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "initial_value": self.initial_value,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "unit": self.unit,
            "description": self.description,
        }


@dataclass(frozen=True)
class FitParameterSet:
    """
    Ordered collection of optimizer-facing fit parameters.

    Parameter order is part of the specification because numerical
    optimizers exchange ordered vectors rather than name-value mappings.
    """

    parameters: tuple[FitParameter, ...]

    def __post_init__(self) -> None:
        parameters = tuple(self.parameters)

        if not parameters:
            raise ValueError(
                "FitParameterSet requires at least one parameter."
            )

        if not all(
            isinstance(parameter, FitParameter)
            for parameter in parameters
        ):
            raise TypeError(
                "parameters must contain only FitParameter instances."
            )

        names = [parameter.name for parameter in parameters]

        if len(names) != len(set(names)):
            raise ValueError(
                "FitParameter names must be unique within a parameter set."
            )

        object.__setattr__(self, "parameters", parameters)

    @property
    def n_parameters(self) -> int:
        return len(self.parameters)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(
            parameter.name
            for parameter in self.parameters
        )

    def _vector(self, attribute: str) -> np.ndarray:
        vector = np.array(
            [
                getattr(parameter, attribute)
                for parameter in self.parameters
            ],
            dtype=float,
        )
        vector.setflags(write=False)
        return vector

    @property
    def initial_values(self) -> np.ndarray:
        return self._vector("initial_value")

    @property
    def lower_bounds(self) -> np.ndarray:
        return self._vector("lower_bound")

    @property
    def upper_bounds(self) -> np.ndarray:
        return self._vector("upper_bound")

    def validate_values(
        self,
        values: np.ndarray | Sequence[float],
    ) -> np.ndarray:
        vector = _as_1d_finite_float_array(
            values,
            field_name="values",
        )

        if vector.size != self.n_parameters:
            raise ValueError(
                "values must contain exactly "
                f"{self.n_parameters} entries."
            )

        lower_bounds = self.lower_bounds
        upper_bounds = self.upper_bounds

        if np.any(vector < lower_bounds) or np.any(vector > upper_bounds):
            raise ValueError(
                "values must lie within the configured parameter bounds."
            )

        return vector

    def values_to_dict(
        self,
        values: np.ndarray | Sequence[float],
    ) -> dict[str, float]:
        vector = self.validate_values(values)

        return {
            name: float(value)
            for name, value in zip(self.names, vector)
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "parameters": [
                parameter.to_dict()
                for parameter in self.parameters
            ],
        }

    def specification_hash(self) -> str:
        """Return a deterministic SHA-256 hash of the parameter specification."""

        return canonical_hash(self.to_dict())


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
    observed: np.ndarray | Sequence[float],
    predicted: np.ndarray | Sequence[float],
    *,
    uncertainty: (
        np.ndarray | Sequence[float] | None
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
    observed: np.ndarray | Sequence[float],
    predicted: np.ndarray | Sequence[float],
    *,
    uncertainty: (
        np.ndarray | Sequence[float] | None
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
    "FitParameter",
    "FitParameterSet",
    "ObjectiveEvaluation",
    "evaluate_least_squares_objective",
    "least_squares_residuals",
]
