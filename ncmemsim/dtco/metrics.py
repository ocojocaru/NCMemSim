"""Explicit scalar metrics and feasibility analysis of completed DTCO sweeps."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any

from ..hashing import canonical_hash
from .sweep import SweepPointResult, SweepResult, _json_snapshot


def _label(value: str, field: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field} must be non-empty without outer whitespace")


def _numeric(value: Any, field: str) -> None:
    if type(value) not in (int, float):
        raise TypeError(f"{field} must be a numeric scalar, not a boolean or category")
    if type(value) is float and not math.isfinite(value):
        raise ValueError(f"{field} must be finite")


class ObjectiveDirection(str, Enum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class ConstraintOperator(str, Enum):
    LE = "<="
    GE = ">="


@dataclass(frozen=True)
class MetricDefinition:
    """A scalar JSON output path; integer segments address array elements."""

    name: str
    path: tuple[str | int, ...]
    unit: str
    direction: ObjectiveDirection | None = None

    def __post_init__(self) -> None:
        if isinstance(self.path, (str, bytes)):
            raise TypeError("metric path must be a sequence of segments")
        object.__setattr__(self, "path", tuple(self.path))
        _label(self.name, "metric name")
        _label(self.unit, "metric unit; use '1' for dimensionless metrics")
        if not self.path:
            raise ValueError("metric path cannot be empty")
        for segment in self.path:
            if type(segment) is str:
                _label(segment, "metric path segment")
            elif type(segment) is not int or segment < 0:
                raise ValueError("metric path segments must be strings or nonnegative integers")
        if self.direction is not None and not isinstance(self.direction, ObjectiveDirection):
            raise TypeError("direction must be ObjectiveDirection or None")

    def extract(self, output: dict[str, Any]) -> int | float:
        value: Any = output
        for segment in self.path:
            if type(segment) is str:
                if type(value) is not dict:
                    raise TypeError(f"metric {self.name!r} requires an object at {segment!r}")
                if segment not in value:
                    raise ValueError(f"metric {self.name!r} missing output key {segment!r}")
            else:
                if type(value) is not list:
                    raise TypeError(f"metric {self.name!r} requires an array at index {segment}")
                if segment >= len(value):
                    raise ValueError(f"metric {self.name!r} array index {segment} is out of range")
            value = value[segment]
        _numeric(value, f"metric {self.name!r}")
        return value

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "path": list(self.path), "unit": self.unit,
            "direction": self.direction.value if self.direction is not None else None,
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class MetricConstraint:
    """An inclusive bound in the metric's declared unit, with no conversion."""

    name: str
    metric_name: str
    operator: ConstraintOperator
    threshold: int | float
    unit: str

    def __post_init__(self) -> None:
        _label(self.name, "constraint name")
        _label(self.metric_name, "constraint metric name")
        _label(self.unit, "constraint unit")
        if not isinstance(self.operator, ConstraintOperator):
            raise TypeError("operator must be a ConstraintOperator")
        _numeric(self.threshold, "constraint threshold")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "metric_name": self.metric_name,
            "operator": self.operator.value, "threshold": self.threshold, "unit": self.unit,
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class MetricAnalysisSpec:
    """Ordered metric definitions and named constraints for one analysis."""

    name: str
    metrics: tuple[MetricDefinition, ...]
    constraints: tuple[MetricConstraint, ...] = ()

    def __post_init__(self) -> None:
        _label(self.name, "analysis name")
        object.__setattr__(self, "metrics", tuple(self.metrics))
        object.__setattr__(self, "constraints", tuple(self.constraints))
        if not self.metrics:
            raise ValueError("analysis requires at least one metric")
        if any(not isinstance(m, MetricDefinition) for m in self.metrics):
            raise TypeError("metrics must contain MetricDefinition instances")
        if any(not isinstance(c, MetricConstraint) for c in self.constraints):
            raise TypeError("constraints must contain MetricConstraint instances")
        units = {m.name: m.unit for m in self.metrics}
        if len(units) != len(self.metrics):
            raise ValueError("metric names must be unique")
        if len({c.name for c in self.constraints}) != len(self.constraints):
            raise ValueError("constraint names must be unique")
        for constraint in self.constraints:
            if constraint.metric_name not in units:
                raise ValueError(f"unknown constraint metric: {constraint.metric_name!r}")
            if constraint.unit != units[constraint.metric_name]:
                raise ValueError(f"constraint {constraint.name!r} unit differs from metric unit")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "dtco-metric-analysis-v1", "name": self.name,
            "metrics": [m.to_dict() for m in self.metrics],
            "constraints": [c.to_dict() for c in self.constraints],
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class ConstraintEvaluation:
    constraint: MetricConstraint
    value: int | float

    def __post_init__(self) -> None:
        if not isinstance(self.constraint, MetricConstraint):
            raise TypeError("constraint must be a MetricConstraint")
        _numeric(self.value, "constraint value")

    @property
    def satisfied(self) -> bool:
        if self.constraint.operator is ConstraintOperator.LE:
            return self.value <= self.constraint.threshold
        return self.value >= self.constraint.threshold

    def to_dict(self) -> dict[str, Any]:
        return {**self.constraint.to_dict(), "value": self.value, "satisfied": self.satisfied}


@dataclass(frozen=True)
class MetricPointResult:
    source: SweepPointResult
    status: str
    metric_values: tuple[tuple[str, int | float], ...] = ()
    constraints: tuple[ConstraintEvaluation, ...] = ()
    failure_stage: str | None = None
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, SweepPointResult):
            raise TypeError("source must be a SweepPointResult")
        object.__setattr__(self, "metric_values", tuple((n, v) for n, v in self.metric_values))
        object.__setattr__(self, "constraints", tuple(self.constraints))
        if self.status == "failed":
            if self.metric_values or self.constraints:
                raise ValueError("failed analysis points cannot expose partial metrics or constraints")
            expected_stage = "sweep" if self.source.status == "failed" else "extraction"
            if self.failure_stage != expected_stage:
                raise ValueError("invalid analysis failure stage")
            _label(self.error_type, "failure error type")
            if not isinstance(self.error_message, str):
                raise TypeError("failure requires an error message")
        elif self.status in ("feasible", "infeasible"):
            if self.source.status != "success" or not self.metric_values:
                raise ValueError("assessed points require successful output and metrics")
            if any(v is not None for v in (self.failure_stage, self.error_type, self.error_message)):
                raise ValueError("assessed points cannot contain failure details")
            for name, value in self.metric_values:
                _label(name, "metric value name")
                _numeric(value, "metric value")
            if len(dict(self.metric_values)) != len(self.metric_values):
                raise ValueError("metric value names must be unique")
            if any(not isinstance(c, ConstraintEvaluation) for c in self.constraints):
                raise TypeError("constraints must contain ConstraintEvaluation instances")
            expected = "feasible" if all(c.satisfied for c in self.constraints) else "infeasible"
            if self.status != expected:
                raise ValueError("status differs from constraint evaluation")
        else:
            raise ValueError("status must be feasible, infeasible, or failed")

    @property
    def metrics(self) -> dict[str, int | float]:
        return dict(self.metric_values)

    def to_dict(self) -> dict[str, Any]:
        return {
            "point_hash": self.source.point.point_hash, "index": self.source.point.index,
            "status": self.status, "metrics": self.metrics,
            "constraints": [c.to_dict() for c in self.constraints],
            "failure": None if self.status != "failed" else {
                "stage": self.failure_stage, "type": self.error_type, "message": self.error_message,
            },
        }


@dataclass(frozen=True)
class MetricAnalysisResult:
    spec: MetricAnalysisSpec
    source_sweep: SweepResult
    points: tuple[MetricPointResult, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.spec, MetricAnalysisSpec) or not isinstance(self.source_sweep, SweepResult):
            raise TypeError("analysis requires MetricAnalysisSpec and SweepResult")
        object.__setattr__(self, "points", tuple(self.points))
        if len(self.points) != len(self.source_sweep.points):
            raise ValueError("analysis requires every source point")
        names = tuple(m.name for m in self.spec.metrics)
        for point, source in zip(self.points, self.source_sweep.points):
            if not isinstance(point, MetricPointResult):
                raise TypeError("points must contain MetricPointResult instances")
            if point.source != source:
                raise ValueError("analysis point order or source differs")
            if point.status == "failed":
                continue
            if tuple(n for n, v in point.metric_values) != names:
                raise ValueError("point metrics differ from analysis specification")
            if tuple(c.constraint for c in point.constraints) != self.spec.constraints:
                raise ValueError("point constraints differ from analysis specification")
            if any(c.value != point.metrics[c.constraint.metric_name] for c in point.constraints):
                raise ValueError("constraint value differs from extracted metric")

    @property
    def feasible_count(self) -> int:
        return sum(p.status == "feasible" for p in self.points)

    @property
    def infeasible_count(self) -> int:
        return sum(p.status == "infeasible" for p in self.points)

    @property
    def failure_count(self) -> int:
        return sum(p.status == "failed" for p in self.points)

    @property
    def analysis_hash(self) -> str:
        return canonical_hash({
            "schema_version": "dtco-metric-analysis-run-v1",
            "spec": self.spec.to_dict(), "source_result_hash": self.source_sweep.result_hash,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "dtco-metric-analysis-result-v1",
            "analysis_hash": self.analysis_hash, "definition_hash": self.spec.definition_hash,
            "spec": self.spec.to_dict(), "source_sweep_hash": self.source_sweep.sweep_hash,
            "source_result_hash": self.source_sweep.result_hash,
            "source_sweep": self.source_sweep.to_dict(),
            "points": [p.to_dict() for p in self.points],
            "feasible_count": self.feasible_count, "infeasible_count": self.infeasible_count,
            "failure_count": self.failure_count,
        }

    def to_json(self) -> str:
        return _json_snapshot(self.to_dict())

    @property
    def result_hash(self) -> str:
        return canonical_hash(self.to_dict())


def analyze_sweep(sweep: SweepResult, spec: MetricAnalysisSpec) -> MetricAnalysisResult:
    """Analyze every point without rerunning or modifying the source sweep."""
    if not isinstance(sweep, SweepResult) or not isinstance(spec, MetricAnalysisSpec):
        raise TypeError("analysis requires SweepResult and MetricAnalysisSpec")
    points = []
    for source in sweep.points:
        if source.status == "failed":
            points.append(MetricPointResult(
                source, "failed", failure_stage="sweep",
                error_type=source.error_type, error_message=source.error_message,
            ))
            continue
        try:
            output = source.output
            values = tuple((m.name, m.extract(output)) for m in spec.metrics)
        except (TypeError, ValueError, OverflowError) as exc:
            points.append(MetricPointResult(
                source, "failed", failure_stage="extraction",
                error_type=f"{type(exc).__module__}.{type(exc).__qualname__}", error_message=str(exc),
            ))
            continue
        metrics = dict(values)
        constraints = tuple(ConstraintEvaluation(c, metrics[c.metric_name]) for c in spec.constraints)
        status = "feasible" if all(c.satisfied for c in constraints) else "infeasible"
        points.append(MetricPointResult(source, status, values, constraints))
    return MetricAnalysisResult(spec, sweep, tuple(points))


__all__ = [
    "ObjectiveDirection", "ConstraintOperator", "MetricDefinition", "MetricConstraint",
    "MetricAnalysisSpec", "ConstraintEvaluation", "MetricPointResult",
    "MetricAnalysisResult", "analyze_sweep",
]
