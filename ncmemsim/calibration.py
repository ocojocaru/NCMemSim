from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .fit_diagnostics import FitUncertaintyDiagnostics
from .fitting import (
    DeterministicFitResult,
    ObjectiveEvaluation,
)
from .hashing import canonical_hash


def _required_text(
    value: str,
    *,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string."
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"{field_name} cannot be empty."
        )

    return normalized


@dataclass(frozen=True)
class CalibrationCriteria:
    """
    Explicit qualification thresholds for promotion to calibration.

    Qualification is intentionally separate from fitting. At least one
    quantitative validation-performance threshold must be configured so
    calibration cannot be granted solely because an optimizer converged.

    RMSE and MAE thresholds use the raw observable units carried by the
    validation objective. The R² threshold is dimensionless. The scaled
    condition number refers to the bound-normalized Jacobian used by the
    generic fit diagnostics.
    """

    max_validation_rmse: float | None = None
    max_validation_mae: float | None = None
    min_validation_r2: float | None = None
    max_scaled_condition_number: float | None = None

    require_distinct_validation_dataset: bool = True
    require_local_identifiability: bool = True
    require_covariance: bool = True

    def __post_init__(self) -> None:
        for field_name in (
            "require_distinct_validation_dataset",
            "require_local_identifiability",
            "require_covariance",
        ):
            if not isinstance(
                getattr(self, field_name),
                bool,
            ):
                raise TypeError(
                    f"{field_name} must be a bool."
                )

        for field_name in (
            "max_validation_rmse",
            "max_validation_mae",
        ):
            value = getattr(self, field_name)

            if value is None:
                continue

            numeric = float(value)

            if (
                not math.isfinite(numeric)
                or numeric < 0.0
            ):
                raise ValueError(
                    f"{field_name} must be finite and non-negative."
                )

            object.__setattr__(
                self,
                field_name,
                numeric,
            )

        if self.min_validation_r2 is not None:
            min_r2 = float(self.min_validation_r2)

            if (
                not math.isfinite(min_r2)
                or min_r2 > 1.0
            ):
                raise ValueError(
                    "min_validation_r2 must be finite and <= 1."
                )

            object.__setattr__(
                self,
                "min_validation_r2",
                min_r2,
            )

        if self.max_scaled_condition_number is not None:
            max_condition = float(
                self.max_scaled_condition_number
            )

            if (
                not math.isfinite(max_condition)
                or max_condition < 1.0
            ):
                raise ValueError(
                    "max_scaled_condition_number must be "
                    "finite and >= 1."
                )

            object.__setattr__(
                self,
                "max_scaled_condition_number",
                max_condition,
            )

        if all(
            value is None
            for value in (
                self.max_validation_rmse,
                self.max_validation_mae,
                self.min_validation_r2,
            )
        ):
            raise ValueError(
                "At least one quantitative validation threshold "
                "must be configured."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "max_validation_rmse": self.max_validation_rmse,
            "max_validation_mae": self.max_validation_mae,
            "min_validation_r2": self.min_validation_r2,
            "max_scaled_condition_number": (
                self.max_scaled_condition_number
            ),
            "require_distinct_validation_dataset": (
                self.require_distinct_validation_dataset
            ),
            "require_local_identifiability": (
                self.require_local_identifiability
            ),
            "require_covariance": self.require_covariance,
        }

    def criteria_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


@dataclass(frozen=True)
class CalibrationCriterionResult:
    """Result of one explicit calibration-qualification criterion."""

    name: str
    passed: bool
    observed_value: float | bool | str | None
    comparison: str
    threshold: float | bool | str | None
    notes: str | None = None

    def __post_init__(self) -> None:
        name = _required_text(
            self.name,
            field_name="name",
        )
        comparison = _required_text(
            self.comparison,
            field_name="comparison",
        )

        if not isinstance(self.passed, bool):
            raise TypeError(
                "passed must be a bool."
            )

        notes = self.notes
        if notes is not None:
            if not isinstance(notes, str):
                raise TypeError(
                    "notes must be None or a string."
                )
            notes = notes.strip() or None

        object.__setattr__(
            self,
            "name",
            name,
        )
        object.__setattr__(
            self,
            "comparison",
            comparison,
        )
        object.__setattr__(
            self,
            "notes",
            notes,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "observed_value": self.observed_value,
            "comparison": self.comparison,
            "threshold": self.threshold,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class CalibrationQualification:
    """
    Auditable calibration-qualification result.

    ``eligible_for_calibration`` means that all configured qualification
    criteria passed. This object does not mutate parameter provenance and
    does not itself assign ``ParameterStatus.CALIBRATED``.
    """

    fit_dataset_hash: str
    validation_dataset_hash: str
    criteria: CalibrationCriteria
    validation_objective: ObjectiveEvaluation
    uncertainty_diagnostics: FitUncertaintyDiagnostics
    criterion_results: tuple[CalibrationCriterionResult, ...]

    def __post_init__(self) -> None:
        fit_dataset_hash = _required_text(
            self.fit_dataset_hash,
            field_name="fit_dataset_hash",
        )
        validation_dataset_hash = _required_text(
            self.validation_dataset_hash,
            field_name="validation_dataset_hash",
        )

        if not isinstance(
            self.criteria,
            CalibrationCriteria,
        ):
            raise TypeError(
                "criteria must be a CalibrationCriteria instance."
            )

        if not isinstance(
            self.validation_objective,
            ObjectiveEvaluation,
        ):
            raise TypeError(
                "validation_objective must be an ObjectiveEvaluation "
                "instance."
            )

        if not isinstance(
            self.uncertainty_diagnostics,
            FitUncertaintyDiagnostics,
        ):
            raise TypeError(
                "uncertainty_diagnostics must be a "
                "FitUncertaintyDiagnostics instance."
            )

        criterion_results = tuple(
            self.criterion_results
        )

        if not criterion_results:
            raise ValueError(
                "criterion_results cannot be empty."
            )

        if not all(
            isinstance(
                result,
                CalibrationCriterionResult,
            )
            for result in criterion_results
        ):
            raise TypeError(
                "criterion_results must contain only "
                "CalibrationCriterionResult instances."
            )

        names = [
            result.name
            for result in criterion_results
        ]

        if len(names) != len(set(names)):
            raise ValueError(
                "criterion_results names must be unique."
            )

        object.__setattr__(
            self,
            "fit_dataset_hash",
            fit_dataset_hash,
        )
        object.__setattr__(
            self,
            "validation_dataset_hash",
            validation_dataset_hash,
        )
        object.__setattr__(
            self,
            "criterion_results",
            criterion_results,
        )

    @property
    def eligible_for_calibration(self) -> bool:
        return all(
            result.passed
            for result in self.criterion_results
        )

    @property
    def failed_criteria(self) -> tuple[str, ...]:
        return tuple(
            result.name
            for result in self.criterion_results
            if not result.passed
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "qualification_type": (
                "fit-validation-calibration-qualification"
            ),
            "eligible_for_calibration": (
                self.eligible_for_calibration
            ),
            "failed_criteria": list(
                self.failed_criteria
            ),
            "fit_dataset_hash": self.fit_dataset_hash,
            "validation_dataset_hash": (
                self.validation_dataset_hash
            ),
            "criteria": self.criteria.to_dict(),
            "criteria_hash": self.criteria.criteria_hash(),
            "validation_objective": (
                self.validation_objective.to_dict()
            ),
            "uncertainty_diagnostics": (
                self.uncertainty_diagnostics.to_dict()
            ),
            "criterion_results": [
                result.to_dict()
                for result in self.criterion_results
            ],
        }

    def qualification_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


def qualify_calibration(
    fit_result: DeterministicFitResult,
    uncertainty_diagnostics: FitUncertaintyDiagnostics,
    *,
    fit_dataset_hash: str,
    validation_dataset_hash: str,
    validation_objective: ObjectiveEvaluation,
    criteria: CalibrationCriteria,
) -> CalibrationQualification:
    """
    Evaluate explicit post-fit calibration qualification criteria.

    The fitted dataset and validation dataset are identified by deterministic
    hashes. By default they must differ. Validation quality is evaluated from
    a separately supplied objective, not from the optimizer's training
    objective.

    This generic function only decides whether the configured criteria pass.
    It never changes parameter provenance and never assigns CALIBRATED status.
    """

    if not isinstance(
        fit_result,
        DeterministicFitResult,
    ):
        raise TypeError(
            "fit_result must be a DeterministicFitResult instance."
        )

    if not fit_result.success:
        raise ValueError(
            "Calibration qualification requires a successful fit."
        )

    if not isinstance(
        uncertainty_diagnostics,
        FitUncertaintyDiagnostics,
    ):
        raise TypeError(
            "uncertainty_diagnostics must be a "
            "FitUncertaintyDiagnostics instance."
        )

    if not isinstance(
        validation_objective,
        ObjectiveEvaluation,
    ):
        raise TypeError(
            "validation_objective must be an ObjectiveEvaluation "
            "instance."
        )

    if not isinstance(
        criteria,
        CalibrationCriteria,
    ):
        raise TypeError(
            "criteria must be a CalibrationCriteria instance."
        )

    fit_dataset_hash = _required_text(
        fit_dataset_hash,
        field_name="fit_dataset_hash",
    )
    validation_dataset_hash = _required_text(
        validation_dataset_hash,
        field_name="validation_dataset_hash",
    )

    if (
        uncertainty_diagnostics.parameter_names
        != fit_result.parameter_set.names
    ):
        raise ValueError(
            "uncertainty_diagnostics parameter names must match "
            "the fit parameter order."
        )

    if (
        uncertainty_diagnostics.n_parameters
        != fit_result.parameter_set.n_parameters
    ):
        raise ValueError(
            "uncertainty_diagnostics parameter count must match "
            "the fit result."
        )

    if (
        uncertainty_diagnostics.n_observations
        != fit_result.objective_residuals.size
    ):
        raise ValueError(
            "uncertainty_diagnostics observation count must match "
            "the fit residual count."
        )

    results: list[CalibrationCriterionResult] = []

    if criteria.require_distinct_validation_dataset:
        distinct = (
            fit_dataset_hash
            != validation_dataset_hash
        )

        results.append(
            CalibrationCriterionResult(
                name="distinct_validation_dataset",
                passed=distinct,
                observed_value=distinct,
                comparison="is_true",
                threshold=True,
                notes=(
                    "Validation data must be distinct from the data "
                    "used to fit the parameters."
                ),
            )
        )

    if criteria.require_local_identifiability:
        locally_identifiable = (
            uncertainty_diagnostics.locally_identifiable
        )

        results.append(
            CalibrationCriterionResult(
                name="local_identifiability",
                passed=locally_identifiable,
                observed_value=locally_identifiable,
                comparison="is_true",
                threshold=True,
                notes=(
                    "Local identifiability means full column rank of "
                    "the bound-scaled Jacobian; it is not a claim of "
                    "global identifiability."
                ),
            )
        )

    if criteria.require_covariance:
        covariance_available = (
            uncertainty_diagnostics.covariance_available
        )

        results.append(
            CalibrationCriterionResult(
                name="covariance_available",
                passed=covariance_available,
                observed_value=covariance_available,
                comparison="is_true",
                threshold=True,
                notes=(
                    "The ordinary local covariance estimate must be "
                    "available; bound-active or rank-deficient fits "
                    "therefore fail this criterion."
                ),
            )
        )

    if (
        criteria.max_scaled_condition_number
        is not None
    ):
        observed_condition = (
            uncertainty_diagnostics.scaled_condition_number
        )

        results.append(
            CalibrationCriterionResult(
                name="scaled_condition_number",
                passed=(
                    observed_condition
                    <= criteria.max_scaled_condition_number
                ),
                observed_value=observed_condition,
                comparison="<=",
                threshold=(
                    criteria.max_scaled_condition_number
                ),
                notes=(
                    "Condition number is evaluated in the same "
                    "bound-normalized parameter coordinates used for "
                    "generic identifiability diagnostics."
                ),
            )
        )

    if criteria.max_validation_rmse is not None:
        observed_rmse = (
            validation_objective.root_mean_square_error
        )

        results.append(
            CalibrationCriterionResult(
                name="validation_rmse",
                passed=(
                    observed_rmse
                    <= criteria.max_validation_rmse
                ),
                observed_value=observed_rmse,
                comparison="<=",
                threshold=criteria.max_validation_rmse,
                notes=(
                    "RMSE is evaluated on raw validation residuals "
                    "in observable units."
                ),
            )
        )

    if criteria.max_validation_mae is not None:
        observed_mae = (
            validation_objective.mean_absolute_error
        )

        results.append(
            CalibrationCriterionResult(
                name="validation_mae",
                passed=(
                    observed_mae
                    <= criteria.max_validation_mae
                ),
                observed_value=observed_mae,
                comparison="<=",
                threshold=criteria.max_validation_mae,
                notes=(
                    "MAE is evaluated on raw validation residuals "
                    "in observable units."
                ),
            )
        )

    if criteria.min_validation_r2 is not None:
        observed_r2 = (
            validation_objective.coefficient_of_determination
        )

        r2_passed = (
            observed_r2 is not None
            and observed_r2
            >= criteria.min_validation_r2
        )

        results.append(
            CalibrationCriterionResult(
                name="validation_r2",
                passed=r2_passed,
                observed_value=observed_r2,
                comparison=">=",
                threshold=criteria.min_validation_r2,
                notes=(
                    "R² is unavailable for constant validation "
                    "observations; such a dataset fails an explicit "
                    "R² criterion."
                ),
            )
        )

    return CalibrationQualification(
        fit_dataset_hash=fit_dataset_hash,
        validation_dataset_hash=validation_dataset_hash,
        criteria=criteria,
        validation_objective=validation_objective,
        uncertainty_diagnostics=uncertainty_diagnostics,
        criterion_results=tuple(results),
    )


__all__ = [
    "CalibrationCriteria",
    "CalibrationCriterionResult",
    "CalibrationQualification",
    "qualify_calibration",
]
