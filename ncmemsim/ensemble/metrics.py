"""Per-realization metric assessment for Phase K ensembles."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from ..dtco.metrics import (
    ConstraintEvaluation,
    MetricAnalysisSpec,
)
from ..hashing import canonical_hash
from .execution import (
    EnsembleExecutionResult,
    RealizationExecutionPoint,
)


_METRIC_FAILURE_STAGE = "metric-extraction"
_METRIC_FAILURE_CATEGORY = "metric-extraction"


def _label(value: str, field: str) -> str:
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


def _finite_float(
    value: int | float,
    field: str,
) -> float:
    if (
        isinstance(value, bool)
        or type(value) not in (int, float)
    ):
        raise TypeError(
            f"{field} must be a numeric scalar"
        )

    result = float(value)

    if (
        not math.isfinite(result)
        or (
            type(value) is int
            and result != value
        )
    ):
        raise ValueError(
            f"{field} must be exactly representable "
            "as a finite float"
        )

    return result


@dataclass(frozen=True)
class EnsembleMetricPointResult:
    """Metric assessment for one exact K3 realization result."""

    source: RealizationExecutionPoint
    status: str
    metric_values: tuple[
        tuple[str, float],
        ...
    ] = ()
    constraints: tuple[
        ConstraintEvaluation,
        ...
    ] = ()
    failure_stage: str | None = None
    failure_category: str | None = None
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            RealizationExecutionPoint,
        ):
            raise TypeError(
                "source must be "
                "RealizationExecutionPoint"
            )

        metric_values = tuple(
            self.metric_values
        )

        constraints = tuple(
            self.constraints
        )

        object.__setattr__(
            self,
            "metric_values",
            metric_values,
        )

        object.__setattr__(
            self,
            "constraints",
            constraints,
        )

        if self.status == "failed":
            if metric_values or constraints:
                raise ValueError(
                    "failed metric points cannot "
                    "expose partial metrics or constraints"
                )

            if self.source.status == "failed":
                if (
                    self.failure_stage
                    != self.source.failure_stage
                    or self.failure_category
                    != self.source.failure_category
                    or self.error_type
                    != self.source.error_type
                    or self.error_message
                    != self.source.error_message
                ):
                    raise ValueError(
                        "propagated execution failure "
                        "must preserve K3 failure details"
                    )

            else:
                if (
                    self.failure_stage
                    != _METRIC_FAILURE_STAGE
                    or self.failure_category
                    != _METRIC_FAILURE_CATEGORY
                ):
                    raise ValueError(
                        "metric extraction failure "
                        "requires metric-extraction stage "
                        "and category"
                    )

                _label(
                    self.error_type,
                    "failure error type",
                )

                if not isinstance(
                    self.error_message,
                    str,
                ):
                    raise TypeError(
                        "failure requires string "
                        "error_message"
                    )

        elif self.status in {
            "feasible",
            "infeasible",
        }:
            if self.source.status != "success":
                raise ValueError(
                    "assessed metric point requires "
                    "successful K3 execution"
                )

            if not metric_values:
                raise ValueError(
                    "assessed metric point requires metrics"
                )

            if any(
                value is not None
                for value in (
                    self.failure_stage,
                    self.failure_category,
                    self.error_type,
                    self.error_message,
                )
            ):
                raise ValueError(
                    "assessed metric point cannot "
                    "contain failure details"
                )

            names = []

            for name, value in metric_values:
                _label(
                    name,
                    "metric value name",
                )

                if type(value) is not float:
                    raise TypeError(
                        "ensemble metric values must "
                        "be exact Python floats"
                    )

                if not math.isfinite(value):
                    raise ValueError(
                        "ensemble metric values must "
                        "be finite"
                    )

                names.append(name)

            if len(set(names)) != len(names):
                raise ValueError(
                    "metric value names must be unique"
                )

            if any(
                not isinstance(
                    item,
                    ConstraintEvaluation,
                )
                for item in constraints
            ):
                raise TypeError(
                    "constraints must contain "
                    "ConstraintEvaluation instances"
                )

            if any(
                type(item.value) is not float
                or not math.isfinite(item.value)
                for item in constraints
            ):
                raise ValueError(
                    "ensemble constraint values must "
                    "be finite Python floats"
                )

            expected_status = (
                "feasible"
                if all(
                    item.satisfied
                    for item in constraints
                )
                else "infeasible"
            )

            if self.status != expected_status:
                raise ValueError(
                    "status differs from "
                    "constraint evaluation"
                )

        else:
            raise ValueError(
                "status must be feasible, "
                "infeasible, or failed"
            )

    @property
    def metrics(self) -> dict[str, float]:
        return dict(
            self.metric_values
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "realization_id": (
                self.source.identity.realization_id
            ),
            "sample_id": (
                self.source.identity.sample_id
            ),
            "sample_index": (
                self.source.identity.sample_index
            ),
            "source_result_hash": (
                self.source.result_hash
            ),
            "status": self.status,
            "metrics": self.metrics,
            "constraints": [
                item.to_dict()
                for item in self.constraints
            ],
            "failure": (
                None
                if self.status != "failed"
                else {
                    "stage": self.failure_stage,
                    "category": (
                        self.failure_category
                    ),
                    "type": self.error_type,
                    "message": (
                        self.error_message
                    ),
                }
            ),
        }

    @property
    def result_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


@dataclass(frozen=True)
class EnsembleMetricAnalysisResult:
    """Ordered K4a assessment of one K3 execution result."""

    spec: MetricAnalysisSpec
    source: EnsembleExecutionResult
    points: tuple[
        EnsembleMetricPointResult,
        ...
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.spec,
            MetricAnalysisSpec,
        ):
            raise TypeError(
                "spec must be MetricAnalysisSpec"
            )

        if not isinstance(
            self.source,
            EnsembleExecutionResult,
        ):
            raise TypeError(
                "source must be EnsembleExecutionResult"
            )

        points = tuple(
            self.points
        )

        if len(points) != len(
            self.source.points
        ):
            raise ValueError(
                "analysis requires every "
                "source realization"
            )

        metric_names = tuple(
            metric.name
            for metric in self.spec.metrics
        )

        for point, source_point in zip(
            points,
            self.source.points,
            strict=True,
        ):
            if not isinstance(
                point,
                EnsembleMetricPointResult,
            ):
                raise TypeError(
                    "points must contain "
                    "EnsembleMetricPointResult instances"
                )

            if point.source != source_point:
                raise ValueError(
                    "analysis point order or "
                    "source differs"
                )

            if point.status == "failed":
                continue

            if tuple(
                name
                for name, _ in point.metric_values
            ) != metric_names:
                raise ValueError(
                    "metric order differs from "
                    "analysis specification"
                )

            if tuple(
                item.constraint
                for item in point.constraints
            ) != self.spec.constraints:
                raise ValueError(
                    "constraint definitions differ "
                    "from analysis specification"
                )

            if any(
                item.value
                != point.metrics[
                    item.constraint.metric_name
                ]
                for item in point.constraints
            ):
                raise ValueError(
                    "constraint value differs "
                    "from extracted metric"
                )

        object.__setattr__(
            self,
            "points",
            points,
        )

    @property
    def analysis_hash(self) -> str:
        return canonical_hash(
            {
                "schema_version": (
                    "ensemble-metric-analysis-run-v1"
                ),
                "spec": self.spec.to_dict(),
                "source_result_hash": (
                    self.source.result_hash
                ),
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "ensemble-metric-analysis-result-v1"
            ),
            "analysis_hash": (
                self.analysis_hash
            ),
            "definition_hash": (
                self.spec.definition_hash
            ),
            "source_result_hash": (
                self.source.result_hash
            ),
            "points": [
                point.to_dict()
                for point in self.points
            ],
        }

    @property
    def result_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


__all__ = [
    "EnsembleMetricAnalysisResult",
    "EnsembleMetricPointResult",
]
