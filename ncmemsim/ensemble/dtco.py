"""Variability-aware DTCO contracts for Phase K ensembles."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any

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


__all__ = [
    "EnsembleDTCOStudy",
    "EnsembleScalarDefinition",
    "EnsembleScalarEvaluation",
    "EnsembleScalarKind",
    "evaluate_ensemble_scalar",
]
