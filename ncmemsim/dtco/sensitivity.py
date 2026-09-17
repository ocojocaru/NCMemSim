"""Local secants and coverage-aware global summaries of Cartesian grid edges."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import product
import json
import math
from typing import Any

from ..hashing import canonical_hash
from .metrics import MetricAnalysisResult, _label, _numeric
from .sweep import _json_snapshot


class SensitivityEligibility(str, Enum):
    ASSESSED = "assessed"
    FEASIBLE_ONLY = "feasible_only"


@dataclass(frozen=True)
class SensitivityAnalysisSpec:
    name: str
    axis_names: tuple[str, ...]
    metric_names: tuple[str, ...]
    eligibility: SensitivityEligibility = SensitivityEligibility.ASSESSED

    def __post_init__(self) -> None:
        _label(self.name, "sensitivity analysis name")
        for field in ("axis_names", "metric_names"):
            names = getattr(self, field)
            if isinstance(names, (str, bytes)):
                raise TypeError(f"{field} must be a sequence")
            names = tuple(names)
            object.__setattr__(self, field, names)
            if not names:
                raise ValueError(f"{field} requires at least one name")
            for name in names:
                _label(name, field)
            if len(set(names)) != len(names):
                raise ValueError(f"{field} must be unique")
        if not isinstance(self.eligibility, SensitivityEligibility):
            raise TypeError("eligibility must be SensitivityEligibility")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "dtco-sensitivity-spec-v1", "name": self.name,
            "axis_names": list(self.axis_names), "metric_names": list(self.metric_names),
            "eligibility": self.eligibility.value,
            "method": "adjacent-numeric-secants-fixed-other-axes",
            "axis_order": "numeric-ascending",
            "missing_neighbors": "exclude-without-bridging",
            "summary_weighting": "equal-valid-grid-edge",
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


def _definitions(analysis, spec):
    variables = json.loads(analysis.source_sweep.experiment_json)["variables"]
    axes = {v["name"]: v for v in variables}
    metrics = {m.name: m for m in analysis.spec.metrics}
    for name in spec.axis_names:
        if name not in axes:
            raise ValueError(f"unknown sensitivity axis: {name!r}")
        for value in axes[name]["values"]:
            _numeric(value, f"axis {name!r}")
    for name in spec.metric_names:
        if name not in metrics:
            raise ValueError(f"unknown sensitivity metric: {name!r}")
    return variables, axes, metrics


def _layout(analysis, spec):
    variables, axes, metrics = _definitions(analysis, spec)
    sizes = [len(v["values"]) for v in variables]
    strides = [math.prod(sizes[i + 1:]) for i in range(len(sizes))]
    positions = {v["name"]: i for i, v in enumerate(variables)}
    for name in spec.axis_names:
        axis = axes[name]
        position = positions[name]
        other = [i for i in range(len(sizes)) if i != position]
        neighbors = sorted(range(sizes[position]), key=lambda i: axis["values"][i])
        for metric_name in spec.metric_names:
            for context in product(*(range(sizes[i]) for i in other)):
                offset = sum(i * strides[p] for p, i in zip(other, context))
                for left, right in zip(neighbors, neighbors[1:]):
                    yield (
                        name, metric_name, offset + left * strides[position],
                        offset + right * strides[position],
                        axis["values"][left], axis["values"][right],
                    )


def _excluded(analysis, spec, left, right):
    reasons = []
    for label, index in (("left", left), ("right", right)):
        status = analysis.points[index].status
        if status == "failed" or (
            status == "infeasible" and spec.eligibility is SensitivityEligibility.FEASIBLE_ONLY
        ):
            reasons.append(f"{label}:{status}")
    return ",".join(reasons) or None


@dataclass(frozen=True)
class SensitivityEdge:
    axis_name: str
    metric_name: str
    left_index: int
    right_index: int
    left_value: int | float
    right_value: int | float
    status: str
    slope: float | None = None
    reason: str | None = None
    error_type: str | None = None

    def __post_init__(self) -> None:
        _label(self.axis_name, "edge axis")
        _label(self.metric_name, "edge metric")
        for index in (self.left_index, self.right_index):
            if type(index) is not int or index < 0:
                raise ValueError("edge indices must be nonnegative integers")
        _numeric(self.left_value, "left axis value")
        _numeric(self.right_value, "right axis value")
        if self.left_value >= self.right_value:
            raise ValueError("edges must run in ascending numeric axis order")
        if self.status == "estimated":
            _numeric(self.slope, "slope")
            if self.reason is not None or self.error_type is not None:
                raise ValueError("estimated edges cannot contain failure details")
        elif self.status in ("excluded", "failed"):
            if self.slope is not None:
                raise ValueError("unestimated edges cannot contain a slope")
            _label(self.reason, "unestimated edge reason")
            if self.status == "failed":
                _label(self.error_type, "arithmetic error type")
            elif self.error_type is not None:
                raise ValueError("excluded edges cannot contain arithmetic errors")
        else:
            raise ValueError("edge status must be estimated, excluded, or failed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "axis_name": self.axis_name, "metric_name": self.metric_name,
            "left_index": self.left_index, "right_index": self.right_index,
            "left_value": self.left_value, "right_value": self.right_value,
            "status": self.status, "slope": self.slope,
            "reason": self.reason, "error_type": self.error_type,
        }


@dataclass(frozen=True)
class SensitivityAnalysisResult:
    spec: SensitivityAnalysisSpec
    source_analysis: MetricAnalysisResult
    edges: tuple[SensitivityEdge, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.spec, SensitivityAnalysisSpec) or not isinstance(
            self.source_analysis, MetricAnalysisResult
        ):
            raise TypeError("sensitivity result requires spec and metric analysis")
        object.__setattr__(self, "edges", tuple(self.edges))
        layout = iter(_layout(self.source_analysis, self.spec))
        for edge in self.edges:
            if not isinstance(edge, SensitivityEdge):
                raise TypeError("edges must contain SensitivityEdge instances")
            actual = (edge.axis_name, edge.metric_name, edge.left_index,
                      edge.right_index, edge.left_value, edge.right_value)
            if actual != next(layout, None):
                raise ValueError("edge geometry or ordering differs from Cartesian grid")
            reason = _excluded(self.source_analysis, self.spec, edge.left_index, edge.right_index)
            if (reason is not None) != (edge.status == "excluded"):
                raise ValueError("edge eligibility differs from source")
            if reason is not None and edge.reason != reason:
                raise ValueError("edge exclusion reason differs from source")
        if next(layout, None) is not None:
            raise ValueError("result must retain every adjacent grid edge")

    @property
    def summaries(self) -> tuple[dict[str, Any], ...]:
        _, axes, metrics = _definitions(self.source_analysis, self.spec)
        groups = {(a, m): [] for a in self.spec.axis_names for m in self.spec.metric_names}
        for edge in self.edges:
            groups[edge.axis_name, edge.metric_name].append(edge)
        summaries = []
        for (axis, metric), edges in groups.items():
            slopes = [e.slope for e in edges if e.status == "estimated"]
            count = len(slopes)
            excluded = sum(e.status == "excluded" for e in edges)
            failed = sum(e.status == "failed" for e in edges)
            summaries.append({
                "axis_name": axis, "metric_name": metric,
                "axis_unit": axes[axis]["unit"], "metric_unit": metrics[metric].unit,
                "slope_unit": f"({metrics[metric].unit})/({axes[axis]['unit']})",
                "attempted_count": len(edges), "estimated_count": count,
                "excluded_count": excluded, "failure_count": failed,
                "complete": bool(edges) and not excluded and not failed,
                "coverage_fraction": count / len(edges) if edges else None,
                "mean_slope": math.fsum(s / count for s in slopes) if count else None,
                "mean_absolute_slope": math.fsum(abs(s) / count for s in slopes) if count else None,
                "max_absolute_slope": max(map(abs, slopes)) if count else None,
            })
        return tuple(summaries)

    @property
    def analysis_hash(self) -> str:
        return canonical_hash({
            "schema_version": "dtco-sensitivity-run-v1",
            "spec": self.spec.to_dict(), "source_result_hash": self.source_analysis.result_hash,
        })

    def to_dict(self) -> dict[str, Any]:
        _, axes, metrics = _definitions(self.source_analysis, self.spec)
        return {
            "schema_version": "dtco-sensitivity-result-v1",
            "definition_hash": self.spec.definition_hash, "analysis_hash": self.analysis_hash,
            "spec": self.spec.to_dict(),
            "axes": [axes[n] for n in self.spec.axis_names],
            "metrics": [metrics[n].to_dict() for n in self.spec.metric_names],
            "source_result_hash": self.source_analysis.result_hash,
            "source_analysis": self.source_analysis.to_dict(),
            "edges": [e.to_dict() for e in self.edges],
            "summaries": list(self.summaries),
        }

    def to_json(self) -> str:
        return _json_snapshot(self.to_dict())

    @property
    def result_hash(self) -> str:
        return canonical_hash(self.to_dict())


def analyze_sensitivity(
    analysis: MetricAnalysisResult, spec: SensitivityAnalysisSpec | None = None,
) -> SensitivityAnalysisResult:
    """Analyze adjacent grid secants; never bridge excluded neighbors.

    Summaries describe sampled grid edges, not Sobol indices or a probability
    distribution. They retain physical units and do not rank unlike quantities.
    """
    if not isinstance(analysis, MetricAnalysisResult):
        raise TypeError("analysis must be a MetricAnalysisResult")
    if spec is None:
        variables = json.loads(analysis.source_sweep.experiment_json)["variables"]
        spec = SensitivityAnalysisSpec(
            "sensitivity",
            tuple(v["name"] for v in variables if all(
                type(value) in (int, float) for value in v["values"]
            )),
            tuple(m.name for m in analysis.spec.metrics),
        )
    if not isinstance(spec, SensitivityAnalysisSpec):
        raise TypeError("spec must be SensitivityAnalysisSpec or None")
    _definitions(analysis, spec)
    edges = []
    for axis, metric, left, right, x1, x2 in _layout(analysis, spec):
        reason = _excluded(analysis, spec, left, right)
        if reason is not None:
            edges.append(SensitivityEdge(axis, metric, left, right, x1, x2, "excluded", reason=reason))
            continue
        try:
            y1 = analysis.points[left].metrics[metric]
            y2 = analysis.points[right].metrics[metric]
            dx, dy = x2 - x1, y2 - y1
            _numeric(dx, "axis difference")
            _numeric(dy, "metric difference")
            slope = dy / dx
            _numeric(slope, "slope")
        except (TypeError, ValueError, ArithmeticError) as exc:
            edges.append(SensitivityEdge(
                axis, metric, left, right, x1, x2, "failed",
                reason=str(exc) or type(exc).__name__,
                error_type=f"{type(exc).__module__}.{type(exc).__qualname__}",
            ))
            continue
        edges.append(SensitivityEdge(axis, metric, left, right, x1, x2, "estimated", slope))
    return SensitivityAnalysisResult(spec, analysis, tuple(edges))


__all__ = [
    "SensitivityEligibility", "SensitivityAnalysisSpec", "SensitivityEdge",
    "SensitivityAnalysisResult", "analyze_sensitivity",
]
