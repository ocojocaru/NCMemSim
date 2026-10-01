# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Variability-aware DTCO contracts for Phase K ensembles."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any

from ..dtco.metrics import ConstraintOperator, ObjectiveDirection
from ..dtco.spec import ScalarValue
from ..dtco.sweep import SweepPoint
from ..hashing import canonical_hash
from .feasibility import EnsembleFeasibilitySummary


def _label(
    value: str,
    field: str,
) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise ValueError(
            f"{field} must be nonempty text "
            "without outer whitespace"
        )

    return value


class EnsembleScalarKind(str, Enum):
    """Scalar quantities exposed by Phase K5a."""

    MEAN = "mean"
    STANDARD_DEVIATION = "standard_deviation"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    MEDIAN = "median"
    QUANTILE = "quantile"
    COVERAGE_FRACTION = "coverage_fraction"
    SIMULATED_PASS_FRACTION = "simulated_pass_fraction"
    ENSEMBLE_FEASIBILITY_FRACTION = (
        "ensemble_feasibility_fraction"
    )
    FAILURE_FRACTION = "failure_fraction"


_METRIC_SCALAR_KINDS = frozenset(
    {
        EnsembleScalarKind.MEAN,
        EnsembleScalarKind.STANDARD_DEVIATION,
        EnsembleScalarKind.MINIMUM,
        EnsembleScalarKind.MAXIMUM,
        EnsembleScalarKind.MEDIAN,
        EnsembleScalarKind.QUANTILE,
    }
)

_FRACTION_SCALAR_KINDS = frozenset(
    {
        EnsembleScalarKind.COVERAGE_FRACTION,
        EnsembleScalarKind.SIMULATED_PASS_FRACTION,
        EnsembleScalarKind.ENSEMBLE_FEASIBILITY_FRACTION,
        EnsembleScalarKind.FAILURE_FRACTION,
    }
)


@dataclass(frozen=True)
class EnsembleDTCOStudy:
    """Explicit link between one DTCO design point and one K4 result."""

    design_point: SweepPoint
    source: EnsembleFeasibilitySummary

    def __post_init__(self) -> None:
        if not isinstance(
            self.design_point,
            SweepPoint,
        ):
            raise TypeError(
                "design_point must be a SweepPoint"
            )

        if not isinstance(
            self.source,
            EnsembleFeasibilitySummary,
        ):
            raise TypeError(
                "source must be an "
                "EnsembleFeasibilitySummary"
            )

    @property
    def experiment_hash(self) -> str:
        return self.design_point.experiment_hash

    @property
    def point_hash(self) -> str:
        return self.design_point.point_hash

    @property
    def index(self) -> int:
        return self.design_point.index

    @property
    def assignments(
        self,
    ) -> dict[str, ScalarValue]:
        return self.design_point.assignments

    @property
    def source_result_hash(self) -> str:
        return self.source.result_hash

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "ensemble-dtco-study-v1"
            ),
            "design_point": (
                self.design_point.to_dict()
            ),
            "point_hash": self.point_hash,
            "source_result_hash": (
                self.source_result_hash
            ),
        }

    @property
    def study_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


@dataclass(frozen=True)
class EnsembleScalarDefinition:
    """Typed declaration of one scalar exposed from an ensemble study."""

    name: str
    kind: EnsembleScalarKind
    unit: str
    metric_name: str | None = None
    quantile: float | None = None

    def __post_init__(self) -> None:
        _label(
            self.name,
            "scalar name",
        )

        if not isinstance(
            self.kind,
            EnsembleScalarKind,
        ):
            raise TypeError(
                "kind must be an EnsembleScalarKind"
            )

        _label(
            self.unit,
            "scalar unit",
        )

        if self.kind in _METRIC_SCALAR_KINDS:
            if self.metric_name is None:
                raise ValueError(
                    "metric scalar requires metric_name"
                )

            _label(
                self.metric_name,
                "metric_name",
            )

            if (
                self.kind
                is EnsembleScalarKind.QUANTILE
            ):
                if (
                    isinstance(self.quantile, bool)
                    or type(self.quantile)
                    not in (int, float)
                    or not math.isfinite(
                        self.quantile
                    )
                    or not 0.0
                    <= self.quantile
                    <= 1.0
                ):
                    raise ValueError(
                        "quantile scalar requires a "
                        "finite probability in [0, 1]"
                    )

                object.__setattr__(
                    self,
                    "quantile",
                    float(self.quantile),
                )

            elif self.quantile is not None:
                raise ValueError(
                    "quantile probability is only "
                    "valid for QUANTILE"
                )

        elif self.kind in _FRACTION_SCALAR_KINDS:
            if self.metric_name is not None:
                raise ValueError(
                    "fraction scalar cannot declare "
                    "metric_name"
                )

            if self.quantile is not None:
                raise ValueError(
                    "fraction scalar cannot declare "
                    "quantile"
                )

            if self.unit != "1":
                raise ValueError(
                    "fraction scalar requires unit '1'"
                )

        else:
            raise ValueError(
                "unsupported ensemble scalar kind"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "ensemble-scalar-definition-v1"
            ),
            "name": self.name,
            "kind": self.kind.value,
            "metric_name": self.metric_name,
            "unit": self.unit,
            "quantile": self.quantile,
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )

@dataclass(frozen=True)
class EnsembleScalarEvaluation:
    """One typed scalar projection from an immutable Phase K study."""

    study: EnsembleDTCOStudy
    definition: EnsembleScalarDefinition
    status: str
    value: float | None

    def __post_init__(self) -> None:
        if not isinstance(
            self.study,
            EnsembleDTCOStudy,
        ):
            raise TypeError(
                "study must be an EnsembleDTCOStudy"
            )

        if not isinstance(
            self.definition,
            EnsembleScalarDefinition,
        ):
            raise TypeError(
                "definition must be an "
                "EnsembleScalarDefinition"
            )

        if self.status not in (
            "defined",
            "undefined",
        ):
            raise ValueError(
                "status must be defined or undefined"
            )

        if self.status == "defined":
            if (
                type(self.value) is not float
                or not math.isfinite(self.value)
            ):
                raise ValueError(
                    "defined scalar requires a "
                    "finite Python float"
                )
        elif self.value is not None:
            raise ValueError(
                "undefined scalar requires value=None"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "ensemble-scalar-evaluation-v1"
            ),
            "study_hash": self.study.study_hash,
            "definition": (
                self.definition.to_dict()
            ),
            "definition_hash": (
                self.definition.definition_hash
            ),
            "status": self.status,
            "value": self.value,
        }

    @property
    def evaluation_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


def _metric_summary(
    study: EnsembleDTCOStudy,
    definition: EnsembleScalarDefinition,
):
    summaries = tuple(
        summary
        for summary
        in study.source.source.metric_statistics
        if (
            summary.metric_name
            == definition.metric_name
        )
    )

    if not summaries:
        raise ValueError(
            f"metric {definition.metric_name!r} "
            "is absent from source statistics"
        )

    if len(summaries) != 1:
        raise ValueError(
            f"metric {definition.metric_name!r} "
            "is not unique in source statistics"
        )

    summary = summaries[0]

    if summary.unit != definition.unit:
        raise ValueError(
            f"metric {definition.metric_name!r} "
            f"uses unit {summary.unit!r}, "
            f"not declared unit {definition.unit!r}"
        )

    return summary


def _metric_scalar_value(
    study: EnsembleDTCOStudy,
    definition: EnsembleScalarDefinition,
) -> float | None:
    summary = _metric_summary(
        study,
        definition,
    )

    fields = {
        EnsembleScalarKind.MEAN: "mean",
        EnsembleScalarKind.STANDARD_DEVIATION: (
            "standard_deviation"
        ),
        EnsembleScalarKind.MINIMUM: "minimum",
        EnsembleScalarKind.MAXIMUM: "maximum",
        EnsembleScalarKind.MEDIAN: "median",
    }

    if definition.kind in fields:
        return getattr(
            summary,
            fields[definition.kind],
        )

    if (
        definition.kind
        is EnsembleScalarKind.QUANTILE
    ):
        for probability, value in summary.quantiles:
            if (
                probability
                == definition.quantile
            ):
                return value

        raise ValueError(
            f"quantile {definition.quantile!r} "
            f"for metric {definition.metric_name!r} "
            "was not declared in source statistics"
        )

    raise ValueError(
        "definition is not a metric scalar"
    )


def _fraction_scalar_value(
    study: EnsembleDTCOStudy,
    definition: EnsembleScalarDefinition,
) -> float | None:
    if (
        definition.kind
        is EnsembleScalarKind.COVERAGE_FRACTION
    ):
        return (
            study.source.source.coverage_fraction
        )

    if (
        definition.kind
        is EnsembleScalarKind.SIMULATED_PASS_FRACTION
    ):
        return (
            study.source.simulated_pass_fraction
        )

    if (
        definition.kind
        is EnsembleScalarKind.ENSEMBLE_FEASIBILITY_FRACTION
    ):
        return (
            study.source.ensemble_feasibility_fraction
        )

    if (
        definition.kind
        is EnsembleScalarKind.FAILURE_FRACTION
    ):
        return study.source.failure_fraction

    raise ValueError(
        "definition is not a fraction scalar"
    )


def evaluate_ensemble_scalar(
    study: EnsembleDTCOStudy,
    definition: EnsembleScalarDefinition,
) -> EnsembleScalarEvaluation:
    """Project one declared K5 scalar without recomputing Phase K4."""

    if not isinstance(
        study,
        EnsembleDTCOStudy,
    ):
        raise TypeError(
            "study must be an EnsembleDTCOStudy"
        )

    if not isinstance(
        definition,
        EnsembleScalarDefinition,
    ):
        raise TypeError(
            "definition must be an "
            "EnsembleScalarDefinition"
        )

    if definition.kind in _METRIC_SCALAR_KINDS:
        value = _metric_scalar_value(
            study,
            definition,
        )
    elif definition.kind in _FRACTION_SCALAR_KINDS:
        value = _fraction_scalar_value(
            study,
            definition,
        )
    else:
        raise ValueError(
            "unsupported ensemble scalar kind"
        )

    return EnsembleScalarEvaluation(
        study=study,
        definition=definition,
        status=(
            "undefined"
            if value is None
            else "defined"
        ),
        value=value,
    )

@dataclass(frozen=True)
class EnsembleConstraint:
    """One inclusive K5b bound over a declared ensemble scalar."""

    name: str
    scalar: EnsembleScalarDefinition
    operator: ConstraintOperator
    threshold: int | float
    unit: str

    def __post_init__(self) -> None:
        _label(
            self.name,
            "constraint name",
        )

        if not isinstance(
            self.scalar,
            EnsembleScalarDefinition,
        ):
            raise TypeError(
                "scalar must be an "
                "EnsembleScalarDefinition"
            )

        if not isinstance(
            self.operator,
            ConstraintOperator,
        ):
            raise TypeError(
                "operator must be a ConstraintOperator"
            )

        if type(self.threshold) not in (
            int,
            float,
        ):
            raise TypeError(
                "constraint threshold must be a "
                "numeric scalar, not a boolean"
            )

        if (
            type(self.threshold) is float
            and not math.isfinite(
                self.threshold
            )
        ):
            raise ValueError(
                "constraint threshold must be finite"
            )

        _label(
            self.unit,
            "constraint unit",
        )

        if self.unit != self.scalar.unit:
            raise ValueError(
                "constraint unit differs from "
                "selected scalar unit"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "ensemble-constraint-v1"
            ),
            "name": self.name,
            "scalar": self.scalar.to_dict(),
            "scalar_definition_hash": (
                self.scalar.definition_hash
            ),
            "operator": self.operator.value,
            "threshold": self.threshold,
            "unit": self.unit,
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


@dataclass(frozen=True)
class EnsembleConstraintEvaluation:
    """K5b constraint outcome with explicit unevaluable state."""

    constraint: EnsembleConstraint
    scalar_evaluation: EnsembleScalarEvaluation
    status: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.constraint,
            EnsembleConstraint,
        ):
            raise TypeError(
                "constraint must be an EnsembleConstraint"
            )

        if not isinstance(
            self.scalar_evaluation,
            EnsembleScalarEvaluation,
        ):
            raise TypeError(
                "scalar_evaluation must be an "
                "EnsembleScalarEvaluation"
            )

        if (
            self.scalar_evaluation.definition
            != self.constraint.scalar
        ):
            raise ValueError(
                "scalar evaluation definition differs "
                "from constraint scalar"
            )

        if self.status not in (
            "satisfied",
            "violated",
            "unevaluable",
        ):
            raise ValueError(
                "status must be satisfied, violated, "
                "or unevaluable"
            )

        if (
            self.scalar_evaluation.status
            == "undefined"
        ):
            expected = "unevaluable"
        elif (
            self.constraint.operator
            is ConstraintOperator.LE
        ):
            expected = (
                "satisfied"
                if self.scalar_evaluation.value
                <= self.constraint.threshold
                else "violated"
            )
        else:
            expected = (
                "satisfied"
                if self.scalar_evaluation.value
                >= self.constraint.threshold
                else "violated"
            )

        if self.status != expected:
            raise ValueError(
                "constraint status differs from "
                "scalar evaluation"
            )

    @property
    def study(self) -> EnsembleDTCOStudy:
        return self.scalar_evaluation.study

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "ensemble-constraint-evaluation-v1"
            ),
            "study_hash": self.study.study_hash,
            "constraint": self.constraint.to_dict(),
            "constraint_hash": (
                self.constraint.definition_hash
            ),
            "scalar_evaluation_hash": (
                self.scalar_evaluation.evaluation_hash
            ),
            "status": self.status,
            "value": self.scalar_evaluation.value,
        }

    @property
    def evaluation_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


def evaluate_ensemble_constraint(
    study: EnsembleDTCOStudy,
    constraint: EnsembleConstraint,
) -> EnsembleConstraintEvaluation:
    """Evaluate one K5b constraint without recomputing upstream data."""

    if not isinstance(
        study,
        EnsembleDTCOStudy,
    ):
        raise TypeError(
            "study must be an EnsembleDTCOStudy"
        )

    if not isinstance(
        constraint,
        EnsembleConstraint,
    ):
        raise TypeError(
            "constraint must be an EnsembleConstraint"
        )

    scalar_evaluation = evaluate_ensemble_scalar(
        study,
        constraint.scalar,
    )

    if scalar_evaluation.status == "undefined":
        status = "unevaluable"
    elif (
        constraint.operator
        is ConstraintOperator.LE
    ):
        status = (
            "satisfied"
            if scalar_evaluation.value
            <= constraint.threshold
            else "violated"
        )
    else:
        status = (
            "satisfied"
            if scalar_evaluation.value
            >= constraint.threshold
            else "violated"
        )

    return EnsembleConstraintEvaluation(
        constraint=constraint,
        scalar_evaluation=scalar_evaluation,
        status=status,
    )


@dataclass(frozen=True)
class EnsembleEligibilityResult:
    """Aggregate K5b eligibility for one variability-aware DTCO study."""

    study: EnsembleDTCOStudy
    evaluations: tuple[
        EnsembleConstraintEvaluation,
        ...
    ]
    status: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.study,
            EnsembleDTCOStudy,
        ):
            raise TypeError(
                "study must be an EnsembleDTCOStudy"
            )

        evaluations = tuple(
            self.evaluations
        )

        if any(
            not isinstance(
                evaluation,
                EnsembleConstraintEvaluation,
            )
            for evaluation in evaluations
        ):
            raise TypeError(
                "evaluations must contain "
                "EnsembleConstraintEvaluation instances"
            )

        names = tuple(
            evaluation.constraint.name
            for evaluation in evaluations
        )
        if len(set(names)) != len(names):
            raise ValueError(
                "constraint names must be unique"
            )

        if any(
            evaluation.study.study_hash
            != self.study.study_hash
            for evaluation in evaluations
        ):
            raise ValueError(
                "constraint evaluations must belong "
                "to the eligibility study"
            )

        if self.status not in (
            "eligible",
            "ineligible",
            "unevaluable",
        ):
            raise ValueError(
                "status must be eligible, ineligible, "
                "or unevaluable"
            )

        if any(
            evaluation.status == "unevaluable"
            for evaluation in evaluations
        ):
            expected = "unevaluable"
        elif any(
            evaluation.status == "violated"
            for evaluation in evaluations
       ):
            expected = "ineligible"
        else:
            expected = "eligible"

        if self.status != expected:
            raise ValueError(
                "eligibility status differs from "
                "constraint evaluations"
            )

        object.__setattr__(
            self,
            "evaluations",
            evaluations,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "ensemble-eligibility-result-v1"
            ),
            "study_hash": self.study.study_hash,
            "evaluations": [
                evaluation.to_dict()
                for evaluation in self.evaluations
            ],
            "status": self.status,
        }

    @property
    def result_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


def evaluate_ensemble_eligibility(
    study: EnsembleDTCOStudy,
    constraints,
) -> EnsembleEligibilityResult:
    """Evaluate ordered K5b constraints with explicit unevaluable precedence."""

    if not isinstance(
        study,
        EnsembleDTCOStudy,
    ):
        raise TypeError(
            "study must be an EnsembleDTCOStudy"
        )

    if isinstance(
        constraints,
        (str, bytes),
    ):
        raise TypeError(
            "constraints must be a sequence of "
            "EnsembleConstraint instances"
        )

    constraints = tuple(
        constraints
    )

    if any(
        not isinstance(
            constraint,
            EnsembleConstraint,
        )
        for constraint in constraints
    ):
        raise TypeError(
            "constraints must contain "
            "EnsembleConstraint instances"
        )

    names = tuple(
        constraint.name
        for constraint in constraints
    )
    if len(set(names)) != len(names):
        raise ValueError(
            "constraint names must be unique"
        )

    evaluations = tuple(
        evaluate_ensemble_constraint(
            study,
            constraint,
        )
        for constraint in constraints
    )

    if any(
        evaluation.status == "unevaluable"
        for evaluation in evaluations
    ):
        status = "unevaluable"
    elif any(
        evaluation.status == "violated"
        for evaluation in evaluations
    ):
        status = "ineligible"
    else:
        status = "eligible"

    return EnsembleEligibilityResult(
        study=study,
        evaluations=evaluations,
        status=status,
    )

@dataclass(frozen=True)
class EnsembleObjective:
    """One explicit K5c objective over an ensemble-derived scalar."""

    name: str
    scalar: EnsembleScalarDefinition
    direction: ObjectiveDirection

    def __post_init__(self) -> None:
        _label(self.name, "objective name")
        if not isinstance(self.scalar, EnsembleScalarDefinition):
            raise TypeError(
                "scalar must be an EnsembleScalarDefinition"
            )
        if not isinstance(self.direction, ObjectiveDirection):
            raise TypeError(
                "direction must be an ObjectiveDirection"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "ensemble-objective-v1",
            "name": self.name,
            "scalar": self.scalar.to_dict(),
            "scalar_definition_hash": self.scalar.definition_hash,
            "direction": self.direction.value,
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class EnsembleParetoPointResult:
    """One retained K5c source study, ranked or explicitly excluded."""

    source: EnsembleEligibilityResult
    rank: int | None
    objective_values: tuple[tuple[str, float], ...] = ()
    exclusion_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, EnsembleEligibilityResult):
            raise TypeError(
                "source must be an EnsembleEligibilityResult"
            )

        values = tuple(self.objective_values)
        if len(dict(values)) != len(values):
            raise ValueError(
                "objective value names must be unique"
            )
        for name, value in values:
            _label(name, "objective value name")
            if type(value) is not float or not math.isfinite(value):
                raise ValueError(
                    "objective values must be finite Python floats"
                )

        allowed_reasons = (
            None,
            "constraint-ineligible",
            "constraint-unevaluable",
            "objective-unevaluable",
        )
        if self.exclusion_reason not in allowed_reasons:
            raise ValueError(
                "invalid Pareto exclusion reason"
            )

        if self.source.status == "ineligible":
            expected_reason = "constraint-ineligible"
        elif self.source.status == "unevaluable":
            expected_reason = "constraint-unevaluable"
        elif self.exclusion_reason is None:
            expected_reason = None
        else:
            expected_reason = "objective-unevaluable"

        if self.exclusion_reason != expected_reason:
            raise ValueError(
                "exclusion reason differs from source "
                "eligibility or objective evaluability"
            )

        if self.exclusion_reason is None:
            if self.source.status != "eligible":
                raise ValueError(
                    "ranked Pareto points require eligible K5b source"
                )
            if type(self.rank) is not int or self.rank < 0:
                raise ValueError(
                    "ranked Pareto points require a "
                    "nonnegative integer rank"
                )
            if not values:
                raise ValueError(
                    "ranked Pareto points require objective values"
                )
        elif self.rank is not None or values:
            raise ValueError(
                "excluded Pareto points cannot expose "
                "rank or objective values"
            )

        object.__setattr__(self, "objective_values", values)

    @property
    def study(self) -> EnsembleDTCOStudy:
        return self.source.study

    @property
    def objectives(self) -> dict[str, float]:
        return dict(self.objective_values)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "ensemble-pareto-point-result-v1",
            "study_hash": self.study.study_hash,
            "source_eligibility_result_hash": self.source.result_hash,
            "point_hash": self.study.point_hash,
            "index": self.study.index,
            "source_status": self.source.status,
            "rank": self.rank,
            "objectives": self.objectives,
            "exclusion_reason": self.exclusion_reason,
        }


def _ensemble_objective_compatibility_signature(
    source: EnsembleEligibilityResult,
    objective: EnsembleObjective,
):
    scalar = objective.scalar

    if scalar.kind in (
        EnsembleScalarKind.COVERAGE_FRACTION,
        EnsembleScalarKind.SIMULATED_PASS_FRACTION,
        EnsembleScalarKind.ENSEMBLE_FEASIBILITY_FRACTION,
        EnsembleScalarKind.FAILURE_FRACTION,
    ):
        return (
            "fraction",
            scalar.kind.value,
            scalar.unit,
        )

    statistics = source.study.source.source
    metric_analysis = statistics.source

    metric = next(
        (
            item
            for item in metric_analysis.spec.metrics
            if item.name == scalar.metric_name
        ),
        None,
    )
    if metric is None:
        raise ValueError(
            f"Pareto objective {objective.name!r} metric "
            f"{scalar.metric_name!r} is absent from source analysis"
        )
    if metric.unit != scalar.unit:
        raise ValueError(
            f"Pareto objective {objective.name!r} unit differs "
            "from source metric unit"
        )

    statistics_contract = statistics.spec.to_dict()
    population_signature = {
        "selection": statistics_contract["selection"],
    }

    if scalar.kind is EnsembleScalarKind.STANDARD_DEVIATION:
        population_signature["standard_deviation"] = (
            statistics_contract["standard_deviation"]
        )
    elif scalar.kind is EnsembleScalarKind.QUANTILE:
        if scalar.quantile not in statistics.spec.quantiles:
            raise ValueError(
                f"Pareto objective {objective.name!r} quantile "
                "was not computed by source population statistics"
            )
        population_signature["quantile_method"] = (
            statistics_contract["quantile_method"]
        )
        population_signature["quantile"] = scalar.quantile

    return (
        "metric",
        metric.definition_hash,
        scalar.kind.value,
        canonical_hash(population_signature),
    )


def _validate_ensemble_objective_compatibility(
    source_results: tuple[EnsembleEligibilityResult, ...],
    objectives: tuple[EnsembleObjective, ...],
) -> None:
    comparable = tuple(
        source
        for source in source_results
        if source.status == "eligible"
    )

    if len(comparable) < 2:
        return

    for objective in objectives:
        reference = _ensemble_objective_compatibility_signature(
            comparable[0],
            objective,
        )
        for source in comparable[1:]:
            candidate = _ensemble_objective_compatibility_signature(
                source,
                objective,
            )
            if candidate != reference:
                raise ValueError(
                    f"incompatible source definitions for "
                    f"Pareto objective {objective.name!r}"
                )


def _ensemble_objective_projection(
    source: EnsembleEligibilityResult,
    objectives: tuple[EnsembleObjective, ...],
) -> tuple[tuple[tuple[str, float], ...], str | None]:
    if source.status == "ineligible":
        return (), "constraint-ineligible"
    if source.status == "unevaluable":
        return (), "constraint-unevaluable"

    evaluations = tuple(
        evaluate_ensemble_scalar(source.study, objective.scalar)
        for objective in objectives
    )
    if any(
        evaluation.status == "undefined"
        for evaluation in evaluations
    ):
        return (), "objective-unevaluable"

    return (
        tuple(
            (objective.name, evaluation.value)
            for objective, evaluation in zip(objectives, evaluations)
        ),
        None,
    )


@dataclass(frozen=True)
class EnsembleParetoAnalysisResult:
    """Exact K5c non-dominated sorting over eligible ensemble studies."""

    name: str
    objectives: tuple[EnsembleObjective, ...]
    source_results: tuple[EnsembleEligibilityResult, ...]
    points: tuple[EnsembleParetoPointResult, ...]
    fronts: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        _label(self.name, "Pareto analysis name")

        objectives = tuple(self.objectives)
        source_results = tuple(self.source_results)
        points = tuple(self.points)
        fronts = tuple(tuple(front) for front in self.fronts)

        if not objectives:
            raise ValueError(
                "Pareto analysis requires at least one objective"
            )
        if any(
            not isinstance(objective, EnsembleObjective)
            for objective in objectives
        ):
            raise TypeError(
                "objectives must contain EnsembleObjective instances"
            )

        objective_names = tuple(
            objective.name for objective in objectives
        )
        if len(set(objective_names)) != len(objective_names):
            raise ValueError(
                "objective names must be unique"
            )

        if any(
            not isinstance(source, EnsembleEligibilityResult)
            for source in source_results
        ):
            raise TypeError(
                "source_results must contain "
                "EnsembleEligibilityResult instances"
            )

        _validate_ensemble_objective_compatibility(
            source_results,
            objectives,
        )
        if any(
            not isinstance(point, EnsembleParetoPointResult)
            for point in points
        ):
            raise TypeError(
                "points must contain "
                "EnsembleParetoPointResult instances"
            )
        if len(points) != len(source_results):
            raise ValueError(
                "Pareto result must retain every "
                "source eligibility result"
            )

        ranked = set()
        for index, (point, source) in enumerate(
            zip(points, source_results)
        ):
            if point.source.result_hash != source.result_hash:
                raise ValueError(
                    "Pareto point order or source differs"
                )

            expected_values, expected_reason = (
                _ensemble_objective_projection(
                    source,
                    objectives,
                )
            )
            if point.exclusion_reason != expected_reason:
                raise ValueError(
                    "Pareto point exclusion reason differs "
                    "from source analysis"
                )

            if expected_reason is None:
                if point.objective_values != expected_values:
                    raise ValueError(
                        "point objectives differ from "
                        "source scalar evaluations"
                    )
                if tuple(
                    name for name, _ in point.objective_values
                ) != objective_names:
                    raise ValueError(
                        "point objectives differ from "
                        "analysis objectives"
                    )
                ranked.add(index)

        seen = set()
        for rank, front in enumerate(fronts):
            if (
                not front
                or any(type(index) is not int for index in front)
                or tuple(sorted(front)) != front
            ):
                raise ValueError(
                    "fronts must be non-empty and in source order"
                )
            for index in front:
                if (
                    index not in ranked
                    or index in seen
                    or points[index].rank != rank
                ):
                    raise ValueError(
                        "front membership or point rank differs"
                    )
                seen.add(index)

        if seen != ranked:
            raise ValueError(
                "fronts must partition all ranked studies"
            )

        object.__setattr__(self, "objectives", objectives)
        object.__setattr__(self, "source_results", source_results)
        object.__setattr__(self, "points", points)
        object.__setattr__(self, "fronts", fronts)

    @property
    def pareto_indices(self) -> tuple[int, ...]:
        return self.fronts[0] if self.fronts else ()

    @property
    def ranked_count(self) -> int:
        return sum(point.rank is not None for point in self.points)

    @property
    def excluded_count(self) -> int:
        return len(self.points) - self.ranked_count

    @property
    def definition_hash(self) -> str:
        return canonical_hash(
            {
                "schema_version": "ensemble-pareto-analysis-v1",
                "name": self.name,
                "objectives": [
                    objective.to_dict()
                    for objective in self.objectives
                ],
                "dominance": (
                    "exact-no-worse-all-strictly-better-one"
                ),
                "eligibility": (
                    "k5b-eligible-and-all-objectives-defined"
                ),
                "ties": "retain-all",
                "ordering": "source-study-order",
                "rank_base": 0,
            }
        )

    @property
    def analysis_hash(self) -> str:
        return canonical_hash(
            {
                "schema_version": "ensemble-pareto-run-v1",
                "definition_hash": self.definition_hash,
                "source_result_hashes": [
                    source.result_hash
                    for source in self.source_results
                ],
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "ensemble-pareto-result-v1",
            "analysis_hash": self.analysis_hash,
            "definition_hash": self.definition_hash,
            "name": self.name,
            "objectives": [
                objective.to_dict()
                for objective in self.objectives
            ],
            "source_result_hashes": [
                source.result_hash
                for source in self.source_results
            ],
            "source_results": [
                source.to_dict()
                for source in self.source_results
            ],
            "points": [
                point.to_dict()
                for point in self.points
            ],
            "fronts": [
                list(front)
                for front in self.fronts
            ],
            "pareto_indices": list(self.pareto_indices),
            "ranked_count": self.ranked_count,
            "excluded_count": self.excluded_count,
        }

    @property
    def result_hash(self) -> str:
        return canonical_hash(self.to_dict())


def analyze_ensemble_pareto(
    source_results,
    objectives,
    *,
    name: str = "pareto",
) -> EnsembleParetoAnalysisResult:
    """Sort eligible K5 studies into exact Pareto fronts."""

    _label(name, "Pareto analysis name")

    if isinstance(source_results, (str, bytes)):
        raise TypeError(
            "source_results must be a sequence of "
            "EnsembleEligibilityResult instances"
        )
    source_results = tuple(source_results)
    if any(
        not isinstance(source, EnsembleEligibilityResult)
        for source in source_results
    ):
        raise TypeError(
            "source_results must contain "
            "EnsembleEligibilityResult instances"
        )

    if isinstance(objectives, (str, bytes)):
        raise TypeError(
            "objectives must be a sequence of "
            "EnsembleObjective instances"
        )
    objectives = tuple(objectives)
    if not objectives:
        raise ValueError(
            "Pareto analysis requires at least one objective"
        )
    if any(
        not isinstance(objective, EnsembleObjective)
        for objective in objectives
    ):
        raise TypeError(
            "objectives must contain EnsembleObjective instances"
        )

    objective_names = tuple(
        objective.name for objective in objectives
    )
    if len(set(objective_names)) != len(objective_names):
        raise ValueError(
            "objective names must be unique"
        )

    _validate_ensemble_objective_compatibility(
        source_results,
        objectives,
    )

    values: dict[int, tuple[tuple[str, float], ...]] = {}
    exclusion_reasons: dict[int, str] = {}

    for index, source in enumerate(source_results):
        projected, reason = _ensemble_objective_projection(
            source,
            objectives,
        )
        if reason is None:
            values[index] = projected
        else:
            exclusion_reasons[index] = reason

    eligible = tuple(
        index
        for index in range(len(source_results))
        if index in values
    )

    def dominates(left: int, right: int) -> bool:
        left_values = dict(values[left])
        right_values = dict(values[right])
        better = False

        for objective in objectives:
            a = left_values[objective.name]
            b = right_values[objective.name]

            if objective.direction is ObjectiveDirection.MINIMIZE:
                if a > b:
                    return False
                better = better or a < b
            else:
                if a < b:
                    return False
                better = better or a > b

        return better

    successors = {index: [] for index in eligible}
    incoming = {index: 0 for index in eligible}

    for position, left in enumerate(eligible):
        for right in eligible[position + 1:]:
            if dominates(left, right):
                successors[left].append(right)
                incoming[right] += 1
            elif dominates(right, left):
                successors[right].append(left)
                incoming[left] += 1

    current = [
        index for index in eligible
        if incoming[index] == 0
    ]
    fronts = []
    ranks = {}

    while current:
        front = tuple(sorted(current))
        fronts.append(front)
        following = []

        for index in front:
            ranks[index] = len(fronts) - 1
            for target in successors[index]:
                incoming[target] -= 1
                if incoming[target] == 0:
                    following.append(target)

        current = following

    points = tuple(
        EnsembleParetoPointResult(
            source=source,
            rank=ranks.get(index),
            objective_values=(
                values[index]
                if index in ranks
                else ()
            ),
            exclusion_reason=(
                None
                if index in ranks
                else exclusion_reasons[index]
            ),
        )
        for index, source in enumerate(source_results)
    )

    return EnsembleParetoAnalysisResult(
        name=name,
        objectives=objectives,
        source_results=source_results,
        points=points,
        fronts=tuple(fronts),
    )


__all__ = [
    "EnsembleConstraint",
    "EnsembleConstraintEvaluation",
    "EnsembleDTCOStudy",
    "EnsembleEligibilityResult",
    "EnsembleObjective",
    "EnsembleParetoAnalysisResult",
    "EnsembleParetoPointResult",
    "EnsembleScalarDefinition",
    "EnsembleScalarEvaluation",
    "EnsembleScalarKind",
    "analyze_ensemble_pareto",
    "evaluate_ensemble_constraint",
    "evaluate_ensemble_eligibility",
    "evaluate_ensemble_scalar",
]
