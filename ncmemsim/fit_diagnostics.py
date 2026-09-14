from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np

from .fitting import DeterministicFitResult


@dataclass(frozen=True)
class FitUncertaintyDiagnostics:
    """
    Linearized local uncertainty and identifiability diagnostics.

    Singular values and condition number are evaluated for the Jacobian in
    the optimizer's normalized bound coordinates. Covariance and standard
    errors are returned in the original physical parameter units.

    The covariance estimate uses the conventional local least-squares
    approximation

        s^2 (J^T J)^-1,

    with ``s^2 = objective_sum_squares / degrees_of_freedom``. These are
    model-based fit uncertainty estimates conditional on the objective,
    dataset, parameterization, bounds, and local linearization. They are not
    experimental reported uncertainties and do not imply calibration.
    """

    parameter_names: tuple[str, ...]
    n_observations: int
    n_parameters: int
    degrees_of_freedom: int
    jacobian_rank: int
    active_bound_count: int
    scaled_singular_values: np.ndarray
    scaled_condition_number: float
    residual_variance: float | None
    covariance_matrix: np.ndarray | None
    standard_errors: np.ndarray | None
    correlation_matrix: np.ndarray | None

    def __post_init__(self) -> None:
        names = tuple(name.strip() for name in self.parameter_names)

        if not names or any(not name for name in names):
            raise ValueError(
                "parameter_names must contain non-empty names."
            )

        if len(names) != len(set(names)):
            raise ValueError(
                "parameter_names must be unique."
            )

        integer_fields = {
            "n_observations": self.n_observations,
            "n_parameters": self.n_parameters,
            "degrees_of_freedom": self.degrees_of_freedom,
            "jacobian_rank": self.jacobian_rank,
            "active_bound_count": self.active_bound_count,
        }

        normalized_integers: dict[str, int] = {}
        for field_name, value in integer_fields.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, np.integer))
            ):
                raise TypeError(
                    f"{field_name} must be an integer."
                )
            normalized_integers[field_name] = int(value)

        n_observations = normalized_integers["n_observations"]
        n_parameters = normalized_integers["n_parameters"]
        degrees_of_freedom = normalized_integers[
            "degrees_of_freedom"
        ]
        jacobian_rank = normalized_integers["jacobian_rank"]
        active_bound_count = normalized_integers[
            "active_bound_count"
        ]

        if n_observations <= 0:
            raise ValueError(
                "n_observations must be strictly positive."
            )

        if n_parameters <= 0:
            raise ValueError(
                "n_parameters must be strictly positive."
            )

        if len(names) != n_parameters:
            raise ValueError(
                "parameter_names must contain one name per parameter."
            )

        if not 0 <= jacobian_rank <= min(
            n_observations,
            n_parameters,
        ):
            raise ValueError(
                "jacobian_rank is inconsistent with matrix dimensions."
            )

        expected_dof = n_observations - jacobian_rank
        if degrees_of_freedom != expected_dof:
            raise ValueError(
                "degrees_of_freedom must equal "
                "n_observations - jacobian_rank."
            )

        if not 0 <= active_bound_count <= n_parameters:
            raise ValueError(
                "active_bound_count must be between 0 and n_parameters."
            )

        singular_values = np.array(
            self.scaled_singular_values,
            dtype=float,
            copy=True,
        )

        if singular_values.ndim != 1:
            raise ValueError(
                "scaled_singular_values must be one-dimensional."
            )

        expected_singular_count = min(
            n_observations,
            n_parameters,
        )
        if singular_values.size != expected_singular_count:
            raise ValueError(
                "scaled_singular_values has an unexpected length."
            )

        if not np.all(np.isfinite(singular_values)):
            raise ValueError(
                "scaled_singular_values must be finite."
            )

        if np.any(singular_values < 0.0):
            raise ValueError(
                "scaled_singular_values must be non-negative."
            )

        if singular_values.size > 1 and np.any(
            singular_values[1:] > singular_values[:-1]
        ):
            raise ValueError(
                "scaled_singular_values must be in non-increasing order."
            )

        singular_values.setflags(write=False)

        condition_number = float(self.scaled_condition_number)
        if math.isnan(condition_number) or condition_number < 1.0:
            raise ValueError(
                "scaled_condition_number must be >= 1 or infinity."
            )

        residual_variance: float | None
        if self.residual_variance is None:
            residual_variance = None
        else:
            residual_variance = float(self.residual_variance)
            if (
                not math.isfinite(residual_variance)
                or residual_variance < 0.0
            ):
                raise ValueError(
                    "residual_variance must be finite and non-negative."
                )

        covariance = self._validated_optional_matrix(
            self.covariance_matrix,
            field_name="covariance_matrix",
            n_parameters=n_parameters,
        )
        standard_errors = self._validated_optional_vector(
            self.standard_errors,
            field_name="standard_errors",
            n_parameters=n_parameters,
        )
        correlation = self._validated_optional_matrix(
            self.correlation_matrix,
            field_name="correlation_matrix",
            n_parameters=n_parameters,
        )

        optional_values = (
            covariance,
            standard_errors,
            correlation,
        )
        if any(value is None for value in optional_values) and not all(
            value is None for value in optional_values
        ):
            raise ValueError(
                "covariance_matrix, standard_errors, and "
                "correlation_matrix must either all be provided or all "
                "be None."
            )

        if covariance is not None:
            if residual_variance is None:
                raise ValueError(
                    "covariance estimates require residual_variance."
                )

            if not np.allclose(
                covariance,
                covariance.T,
                rtol=1.0e-10,
                atol=1.0e-12,
            ):
                raise ValueError(
                    "covariance_matrix must be symmetric."
                )

            if np.any(standard_errors < 0.0):
                raise ValueError(
                    "standard_errors must be non-negative."
                )

            if not np.allclose(
                correlation,
                correlation.T,
                rtol=1.0e-10,
                atol=1.0e-12,
            ):
                raise ValueError(
                    "correlation_matrix must be symmetric."
                )

            if np.any(np.abs(correlation) > 1.0 + 1.0e-10):
                raise ValueError(
                    "correlation_matrix entries must lie in [-1, 1]."
                )

            if not np.allclose(
                np.diag(correlation),
                np.ones(n_parameters),
                rtol=1.0e-10,
                atol=1.0e-10,
            ):
                raise ValueError(
                    "correlation_matrix diagonal must equal one."
                )

        object.__setattr__(self, "parameter_names", names)
        object.__setattr__(self, "n_observations", n_observations)
        object.__setattr__(self, "n_parameters", n_parameters)
        object.__setattr__(
            self,
            "degrees_of_freedom",
            degrees_of_freedom,
        )
        object.__setattr__(self, "jacobian_rank", jacobian_rank)
        object.__setattr__(
            self,
            "active_bound_count",
            active_bound_count,
        )
        object.__setattr__(
            self,
            "scaled_singular_values",
            singular_values,
        )
        object.__setattr__(
            self,
            "scaled_condition_number",
            condition_number,
        )
        object.__setattr__(
            self,
            "residual_variance",
            residual_variance,
        )
        object.__setattr__(
            self,
            "covariance_matrix",
            covariance,
        )
        object.__setattr__(
            self,
            "standard_errors",
            standard_errors,
        )
        object.__setattr__(
            self,
            "correlation_matrix",
            correlation,
        )

    @staticmethod
    def _validated_optional_vector(
        value: np.ndarray | None,
        *,
        field_name: str,
        n_parameters: int,
    ) -> np.ndarray | None:
        if value is None:
            return None

        array = np.array(value, dtype=float, copy=True)
        if array.shape != (n_parameters,):
            raise ValueError(
                f"{field_name} must have shape ({n_parameters},)."
            )
        if not np.all(np.isfinite(array)):
            raise ValueError(
                f"{field_name} must contain only finite values."
            )
        array.setflags(write=False)
        return array

    @staticmethod
    def _validated_optional_matrix(
        value: np.ndarray | None,
        *,
        field_name: str,
        n_parameters: int,
    ) -> np.ndarray | None:
        if value is None:
            return None

        array = np.array(value, dtype=float, copy=True)
        expected_shape = (n_parameters, n_parameters)
        if array.shape != expected_shape:
            raise ValueError(
                f"{field_name} must have shape {expected_shape}."
            )
        if not np.all(np.isfinite(array)):
            raise ValueError(
                f"{field_name} must contain only finite values."
            )
        array.setflags(write=False)
        return array

    @property
    def jacobian_full_rank(self) -> bool:
        return self.jacobian_rank == self.n_parameters

    @property
    def locally_identifiable(self) -> bool:
        """
        Whether the bound-scaled local Jacobian has full column rank.

        This is a local linearized rank diagnostic, not a proof of global
        parameter identifiability.
        """

        return self.jacobian_full_rank

    @property
    def bound_constrained(self) -> bool:
        return self.active_bound_count > 0

    @property
    def covariance_available(self) -> bool:
        return self.covariance_matrix is not None

    @property
    def parameter_standard_errors(self) -> dict[str, float] | None:
        if self.standard_errors is None:
            return None

        return {
            name: float(value)
            for name, value in zip(
                self.parameter_names,
                self.standard_errors,
            )
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "method": "linearized-local-least-squares",
            "jacobian_scaling": "fit-parameter-bounds-[0,1]",
            "covariance_parameterization": "physical-parameter-values",
            "variance_scaling": "objective-sse/degrees-of-freedom",
            "parameter_names": list(self.parameter_names),
            "n_observations": self.n_observations,
            "n_parameters": self.n_parameters,
            "degrees_of_freedom": self.degrees_of_freedom,
            "jacobian_rank": self.jacobian_rank,
            "jacobian_full_rank": self.jacobian_full_rank,
            "locally_identifiable": self.locally_identifiable,
            "active_bound_count": self.active_bound_count,
            "bound_constrained": self.bound_constrained,
            "scaled_singular_values": (
                self.scaled_singular_values.tolist()
            ),
            "scaled_condition_number": self.scaled_condition_number,
            "residual_variance": self.residual_variance,
            "covariance_available": self.covariance_available,
            "covariance_matrix": (
                None
                if self.covariance_matrix is None
                else self.covariance_matrix.tolist()
            ),
            "standard_errors": (
                None
                if self.standard_errors is None
                else self.standard_errors.tolist()
            ),
            "parameter_standard_errors": self.parameter_standard_errors,
            "correlation_matrix": (
                None
                if self.correlation_matrix is None
                else self.correlation_matrix.tolist()
            ),
        }


def analyze_fit_uncertainty(
    result: DeterministicFitResult,
) -> FitUncertaintyDiagnostics:
    """
    Compute linearized local fit uncertainty and identifiability diagnostics.

    The SVD is performed in the same normalized bound coordinates used by
    the optimizer. This removes arbitrary differences in physical parameter
    magnitudes from the numerical rank and condition-number diagnostics.

    Covariance is returned in physical parameter units. It is intentionally
    withheld when the local Jacobian is rank deficient, no residual degrees
    of freedom remain, or one or more fitted parameters are active on a
    bound, because the ordinary unconstrained covariance approximation is
    then not appropriate.
    """

    if not isinstance(result, DeterministicFitResult):
        raise TypeError(
            "result must be a DeterministicFitResult instance."
        )

    if not result.success:
        raise ValueError(
            "Uncertainty diagnostics require a successful fit."
        )

    if result.jacobian is None:
        raise ValueError(
            "Uncertainty diagnostics require a stored fit Jacobian."
        )

    physical_jacobian = np.asarray(
        result.jacobian,
        dtype=float,
    )

    spans = (
        result.parameter_set.upper_bounds
        - result.parameter_set.lower_bounds
    )

    scaled_jacobian = (
        physical_jacobian * spans[np.newaxis, :]
    )

    _, singular_values, vh = np.linalg.svd(
        scaled_jacobian,
        full_matrices=False,
    )

    n_observations, n_parameters = physical_jacobian.shape

    if singular_values.size == 0:
        tolerance = 0.0
    else:
        tolerance = (
            np.finfo(float).eps
            * max(n_observations, n_parameters)
            * singular_values[0]
        )

    jacobian_rank = int(
        np.sum(singular_values > tolerance)
    )

    degrees_of_freedom = (
        n_observations - jacobian_rank
    )

    full_column_rank = (
        jacobian_rank == n_parameters
    )

    if full_column_rank:
        smallest = singular_values[n_parameters - 1]
        if smallest > 0.0:
            condition_number = float(
                singular_values[0] / smallest
            )
        else:
            condition_number = math.inf
    else:
        condition_number = math.inf

    active_bound_count = int(
        np.count_nonzero(result.active_mask)
    )

    residual_variance: float | None
    if degrees_of_freedom > 0:
        residual_variance = (
            result.objective_sum_squares
            / degrees_of_freedom
        )
    else:
        residual_variance = None

    covariance_matrix: np.ndarray | None = None
    standard_errors: np.ndarray | None = None
    correlation_matrix: np.ndarray | None = None

    covariance_is_valid = (
        full_column_rank
        and degrees_of_freedom > 0
        and active_bound_count == 0
    )

    if covariance_is_valid:
        inverse_singular_squared = (
            1.0
            / np.square(
                singular_values[:n_parameters]
            )
        )

        normalized_information_inverse = (
            vh.T
            @ np.diag(inverse_singular_squared)
            @ vh
        )

        span_matrix = np.diag(spans)
        physical_information_inverse = (
            span_matrix
            @ normalized_information_inverse
            @ span_matrix
        )

        covariance_matrix = (
            residual_variance
            * physical_information_inverse
        )

        covariance_matrix = 0.5 * (
            covariance_matrix
            + covariance_matrix.T
        )

        covariance_diagonal = np.maximum(
            np.diag(covariance_matrix),
            0.0,
        )
        standard_errors = np.sqrt(
            covariance_diagonal
        )

        base_diagonal = np.maximum(
            np.diag(physical_information_inverse),
            0.0,
        )
        base_standard_errors = np.sqrt(
            base_diagonal
        )

        correlation_denominator = np.outer(
            base_standard_errors,
            base_standard_errors,
        )

        correlation_matrix = np.divide(
            physical_information_inverse,
            correlation_denominator,
            out=np.zeros_like(
                physical_information_inverse
            ),
            where=correlation_denominator > 0.0,
        )

        correlation_matrix = np.clip(
            correlation_matrix,
            -1.0,
            1.0,
        )
        np.fill_diagonal(correlation_matrix, 1.0)

    return FitUncertaintyDiagnostics(
        parameter_names=result.parameter_set.names,
        n_observations=n_observations,
        n_parameters=n_parameters,
        degrees_of_freedom=degrees_of_freedom,
        jacobian_rank=jacobian_rank,
        active_bound_count=active_bound_count,
        scaled_singular_values=singular_values,
        scaled_condition_number=condition_number,
        residual_variance=residual_variance,
        covariance_matrix=covariance_matrix,
        standard_errors=standard_errors,
        correlation_matrix=correlation_matrix,
    )


__all__ = [
    "FitUncertaintyDiagnostics",
    "analyze_fit_uncertainty",
]
