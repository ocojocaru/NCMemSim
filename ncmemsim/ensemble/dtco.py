"""Variability-aware DTCO contracts for Phase K ensembles."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any

from ..dtco.metrics import ConstraintOperator
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


__all__ = [
    "EnsembleConstraint",
    "EnsembleConstraintEvaluation",
    "EnsembleDTCOStudy",
    "EnsembleEligibilityResult",
    "EnsembleScalarDefinition",
    "EnsembleScalarEvaluation",
    "EnsembleScalarKind",
    "evaluate_ensemble_constraint",
    "evaluate_ensemble_eligibility",
    "evaluate_ensemble_scalar",
]
