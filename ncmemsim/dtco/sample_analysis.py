"""Complete-case sample metrics, observed feasibility and explicit statistics."""
from __future__ import annotations
from dataclasses import dataclass, field
import json
import math
import platform
import statistics
from typing import Any
from .._version import __version__
from ..hashing import canonical_hash
from .metrics import MetricAnalysisSpec, ConstraintEvaluation, _label, _numeric
from .propagation import PropagationResult, SamplePointResult
from .sweep import _json_snapshot

@dataclass(frozen=True)
class SampleMetricPointResult:
    source: SamplePointResult
    status: str
    metric_values: tuple[tuple[str, int | float], ...] = ()
    constraints: tuple[ConstraintEvaluation, ...] = ()
    failure_stage: str | None = None
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, SamplePointResult):
            raise TypeError("source must be a SamplePointResult")
        object.__setattr__(self, "metric_values", tuple((n, v) for n, v in self.metric_values))
        object.__setattr__(self, "constraints", tuple(self.constraints))
        if self.status == "failed":
            if self.metric_values or self.constraints:
                raise ValueError("failed analysis points cannot expose partial metrics or constraints")
            expected_stage = "propagation" if self.source.status == "failed" else "extraction"
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
class SampleAnalysisSpec:
    metrics: MetricAnalysisSpec
    quantiles: tuple[float, ...] = (0.05, 0.5, 0.95)

    def __post_init__(self) -> None:
        if not isinstance(self.metrics, MetricAnalysisSpec):
            raise TypeError("metrics must be MetricAnalysisSpec")
        values = tuple(self.quantiles)
        for q in values:
            if type(q) not in (int, float) or not 0 <= q <= 1 or not math.isfinite(q):
                raise ValueError("quantiles must be finite numeric probabilities in [0, 1]")
        values = tuple(float(q) for q in values)
        if len(set(values)) != len(values):
            raise ValueError("duplicate quantiles")
        object.__setattr__(self, "quantiles", values)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": "dtco-sample-analysis-v1", "metrics": self.metrics.to_dict(),
                "quantiles": list(self.quantiles), "quantile_method": "linear-n-minus-one",
                "standard_deviation": "population-ddof-0", "selection": "all-assessed-complete-cases"}

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


def _finite_float(value: int | float) -> float:
    result = float(value)
    if not math.isfinite(result) or (type(value) is int and result != value):
        raise ValueError("metric must be exactly representable as a finite float")
    return result


def _summary(values: list[float], probabilities: tuple[float, ...]) -> dict[str, Any]:
    if not values:
        return {"minimum": None, "maximum": None, "mean": None,
                "standard_deviation": None,
                "quantiles": [{"probability": q, "value": None} for q in probabilities]}
    ordered = sorted(values)
    quantiles = []
    for q in probabilities:
        position = (len(ordered) - 1) * q
        lower = math.floor(position)
        upper = math.ceil(position)
        weight = position - lower
        value = (1.0 - weight) * ordered[lower] + weight * ordered[upper]
        quantiles.append({"probability": q, "value": value})
    result = {"minimum": ordered[0], "maximum": ordered[-1],
              "mean": statistics.mean(values), "standard_deviation": statistics.pstdev(values),
              "quantiles": quantiles}
    _json_snapshot(result)
    return result


@dataclass(frozen=True)
class SampleAnalysisResult:
    spec: SampleAnalysisSpec
    source: PropagationResult
    points: tuple[SampleMetricPointResult, ...]
    runtime_json: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.spec, SampleAnalysisSpec) or not isinstance(self.source, PropagationResult):
            raise TypeError("analysis requires SampleAnalysisSpec and PropagationResult")
        points = tuple(self.points)
        if len(points) != len(self.source.points):
            raise ValueError("analysis requires every source sample")
        names = tuple(m.name for m in self.spec.metrics.metrics)
        for point, source in zip(points, self.source.points):
            if not isinstance(point, SampleMetricPointResult) or point.source != source:
                raise ValueError("analysis sample order or source mismatch")
            if point.status == "failed":
                continue
            if tuple(n for n, _ in point.metric_values) != names:
                raise ValueError("metric order mismatch")
            if tuple(c.constraint for c in point.constraints) != self.spec.metrics.constraints:
                raise ValueError("constraint definitions mismatch")
            if any(c.value != point.metrics[c.constraint.metric_name] for c in point.constraints):
                raise ValueError("constraint value mismatch")
            if any(type(v) is not float or not math.isfinite(v) for _, v in point.metric_values):
                raise ValueError("sample metrics require finite representable floats")
        object.__setattr__(self, "points", points)
        object.__setattr__(self, "runtime_json", _json_snapshot({"python": platform.python_version(),
            "python_implementation": platform.python_implementation(), "ncmemsim": __version__, "algorithm": "python-statistics-linear-v1"}))

    @property
    def total_count(self) -> int:
        return len(self.points)

    @property
    def assessed_count(self) -> int:
        return self.feasible_count + self.infeasible_count

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
    def observed_feasible_fraction_all_attempted(self) -> float:
        return self.feasible_count / self.total_count

    @property
    def conditional_feasible_fraction_assessed(self) -> float | None:
        return None if self.assessed_count == 0 else self.feasible_count / self.assessed_count

    @property
    def failure_fraction_all_attempted(self) -> float:
        return self.failure_count / self.total_count

    @property
    def metric_statistics(self) -> tuple[dict[str, Any], ...]:
        assessed = [p for p in self.points if p.status != "failed"]
        indices = [p.source.point.index for p in assessed]
        return tuple({"metric_name": metric.name, "unit": metric.unit,
                      "denominator": len(assessed), "sample_indices": list(indices),
                      **_summary([p.metrics[metric.name] for p in assessed], self.spec.quantiles)}
                     for metric in self.spec.metrics.metrics)

    @property
    def analysis_hash(self) -> str:
        return canonical_hash({"schema_version": "dtco-sample-analysis-run-v1",
            "spec": self.spec.to_dict(), "source_result_hash": self.source.result_hash,
            "runtime": json.loads(self.runtime_json)})

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": "dtco-sample-analysis-result-v1", "spec": self.spec.to_dict(),
                "analysis_hash": self.analysis_hash, "runtime": json.loads(self.runtime_json),
                "source_result_hash": self.source.result_hash,
                "source": self.source.to_dict(), "points": [p.to_dict() for p in self.points],
                "counts": {"total": self.total_count, "assessed": self.assessed_count,
                    "feasible": self.feasible_count, "infeasible": self.infeasible_count,
                    "failed": self.failure_count,
                    "propagation_failed": sum(p.failure_stage == "propagation" for p in self.points),
                    "extraction_failed": sum(p.failure_stage == "extraction" for p in self.points)},
                "fractions": {
                    "observed_feasible_fraction_all_attempted": {"value": self.observed_feasible_fraction_all_attempted,
                        "numerator": self.feasible_count, "denominator": self.total_count},
                    "conditional_feasible_fraction_assessed": {"value": self.conditional_feasible_fraction_assessed,
                        "numerator": self.feasible_count, "denominator": self.assessed_count},
                    "failure_fraction_all_attempted": {"value": self.failure_fraction_all_attempted,
                        "numerator": self.failure_count, "denominator": self.total_count}},
                "metric_statistics": list(self.metric_statistics)}

    def to_json(self) -> str:
        return _json_snapshot(self.to_dict())

    @property
    def result_hash(self) -> str:
        return canonical_hash(self.to_dict())


def analyze_samples(source: PropagationResult, spec: SampleAnalysisSpec) -> SampleAnalysisResult:
    """Analyze all samples without rerunning physics; reject incomplete metric cases."""
    if not isinstance(source, PropagationResult) or not isinstance(spec, SampleAnalysisSpec):
        raise TypeError("analysis requires PropagationResult and SampleAnalysisSpec")
    points = []
    for point in source.points:
        if point.status == "failed":
            points.append(SampleMetricPointResult(point, "failed", failure_stage="propagation",
                error_type=point.error_type, error_message=point.error_message))
            continue
        try:
            output = point.output
            values = tuple((metric.name, _finite_float(metric.extract(output))) for metric in spec.metrics.metrics)
            if not all(math.isfinite(v) for _, v in values):
                raise ValueError("metrics must fit finite float representation")
        except (ValueError, TypeError, OverflowError) as exc:
            points.append(SampleMetricPointResult(point, "failed", failure_stage="extraction",
                error_type=f"{type(exc).__module__}.{type(exc).__qualname__}", error_message=str(exc)))
            continue
        metrics = dict(values)
        constraints = tuple(ConstraintEvaluation(c, metrics[c.metric_name]) for c in spec.metrics.constraints)
        status = "feasible" if all(c.satisfied for c in constraints) else "infeasible"
        points.append(SampleMetricPointResult(point, status, values, constraints))
    return SampleAnalysisResult(spec, source, tuple(points))


__all__ = ["SampleAnalysisSpec", "SampleMetricPointResult", "SampleAnalysisResult", "analyze_samples"]
