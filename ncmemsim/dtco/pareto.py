"""Exact, deterministic non-dominated sorting of feasible DTCO points."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..hashing import canonical_hash
from .metrics import MetricAnalysisResult, MetricPointResult, ObjectiveDirection
from .sweep import _json_snapshot


@dataclass(frozen=True)
class ParetoAnalysisSpec:
    """An explicit ordered subset of directed metrics; no weights or tolerances."""

    name: str
    objective_names: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name or self.name != self.name.strip():
            raise ValueError("Pareto analysis name must be non-empty without outer whitespace")
        if isinstance(self.objective_names, (str, bytes)):
            raise TypeError("objective_names must be a sequence of names")
        object.__setattr__(self, "objective_names", tuple(self.objective_names))
        if not self.objective_names:
            raise ValueError("Pareto analysis requires at least one objective")
        for name in self.objective_names:
            if not isinstance(name, str) or not name or name != name.strip():
                raise ValueError("objective names must be non-empty without outer whitespace")
        if len(set(self.objective_names)) != len(self.objective_names):
            raise ValueError("objective names must be unique")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "dtco-pareto-analysis-v1",
            "name": self.name, "objective_names": list(self.objective_names),
            "dominance": "exact-no-worse-all-strictly-better-one",
            "eligibility": "feasible-only", "ties": "retain-all",
            "ordering": "source-point-order", "rank_base": 0,
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class ParetoPointResult:
    source: MetricPointResult
    rank: int | None
    objective_values: tuple[tuple[str, int | float], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.source, MetricPointResult):
            raise TypeError("source must be a MetricPointResult")
        object.__setattr__(self, "objective_values", tuple((n, v) for n, v in self.objective_values))
        if self.source.status == "feasible":
            if type(self.rank) is not int or self.rank < 0:
                raise ValueError("feasible points require a nonnegative integer rank")
            if not self.objective_values or len(dict(self.objective_values)) != len(self.objective_values):
                raise ValueError("ranked points require unique objective values")
            for name, value in self.objective_values:
                if name not in self.source.metrics or type(value) not in (int, float):
                    raise ValueError("objective differs from source metrics")
                if value != self.source.metrics[name]:
                    raise ValueError("objective differs from source metrics")
        elif self.rank is not None or self.objective_values:
            raise ValueError("excluded points cannot have rank or objectives")

    @property
    def exclusion_reason(self) -> str | None:
        return None if self.source.status == "feasible" else self.source.status

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.source.source.point.index,
            "point_hash": self.source.source.point.point_hash,
            "source_status": self.source.status, "rank": self.rank,
            "objectives": dict(self.objective_values),
            "exclusion_reason": self.exclusion_reason,
        }


@dataclass(frozen=True)
class ParetoAnalysisResult:
    spec: ParetoAnalysisSpec
    source_analysis: MetricAnalysisResult
    points: tuple[ParetoPointResult, ...]
    fronts: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.spec, ParetoAnalysisSpec) or not isinstance(self.source_analysis, MetricAnalysisResult):
            raise TypeError("Pareto result requires spec and source metric analysis")
        object.__setattr__(self, "points", tuple(self.points))
        object.__setattr__(self, "fronts", tuple(tuple(front) for front in self.fronts))
        _objectives(self.source_analysis, self.spec)
        if len(self.points) != len(self.source_analysis.points):
            raise ValueError("Pareto result must retain every source point")
        ranked = set()
        for index, (point, source) in enumerate(zip(self.points, self.source_analysis.points)):
            if not isinstance(point, ParetoPointResult):
                raise TypeError("points must contain ParetoPointResult instances")
            if point.source != source:
                raise ValueError("Pareto point order or source differs")
            if source.status == "feasible":
                if tuple(n for n, v in point.objective_values) != self.spec.objective_names:
                    raise ValueError("point objectives differ from specification")
                ranked.add(index)
        seen = set()
        for rank, front in enumerate(self.fronts):
            if not front or any(type(i) is not int for i in front) or tuple(sorted(front)) != front:
                raise ValueError("fronts must be non-empty and in source order")
            for index in front:
                if index not in ranked or index in seen or self.points[index].rank != rank:
                    raise ValueError("front membership or point rank differs")
                seen.add(index)
        if seen != ranked:
            raise ValueError("fronts must partition all feasible points")

    @property
    def pareto_indices(self) -> tuple[int, ...]:
        return self.fronts[0] if self.fronts else ()

    @property
    def ranked_count(self) -> int:
        return self.source_analysis.feasible_count

    @property
    def excluded_count(self) -> int:
        return len(self.points) - self.ranked_count

    @property
    def analysis_hash(self) -> str:
        return canonical_hash({
            "schema_version": "dtco-pareto-run-v1",
            "spec": self.spec.to_dict(), "source_result_hash": self.source_analysis.result_hash,
        })

    def to_dict(self) -> dict[str, Any]:
        definitions = _objectives(self.source_analysis, self.spec)
        return {
            "schema_version": "dtco-pareto-result-v1", "analysis_hash": self.analysis_hash,
            "definition_hash": self.spec.definition_hash, "spec": self.spec.to_dict(),
            "objectives": [m.to_dict() for m in definitions],
            "source_result_hash": self.source_analysis.result_hash,
            "source_analysis": self.source_analysis.to_dict(),
            "points": [p.to_dict() for p in self.points],
            "fronts": [list(front) for front in self.fronts],
            "pareto_indices": list(self.pareto_indices),
            "ranked_count": self.ranked_count, "excluded_count": self.excluded_count,
        }

    def to_json(self) -> str:
        return _json_snapshot(self.to_dict())

    @property
    def result_hash(self) -> str:
        return canonical_hash(self.to_dict())


def _objectives(analysis: MetricAnalysisResult, spec: ParetoAnalysisSpec):
    definitions = {m.name: m for m in analysis.spec.metrics}
    objectives = []
    for name in spec.objective_names:
        if name not in definitions:
            raise ValueError(f"unknown Pareto objective: {name!r}")
        definition = definitions[name]
        if definition.direction is None:
            raise ValueError(f"metric {name!r} has no objective direction")
        objectives.append(definition)
    return tuple(objectives)


def analyze_pareto(
    analysis: MetricAnalysisResult, spec: ParetoAnalysisSpec | None = None,
) -> ParetoAnalysisResult:
    """Sort feasible points into all fronts, retaining every source point.

    Exact comparisons preserve sign and integer precision. Equal vectors do not
    dominate one another. Complexity is O(N² M) time and O(N²) worst-case memory,
    for N feasible points and M selected objectives.
    """
    if not isinstance(analysis, MetricAnalysisResult):
        raise TypeError("analysis must be a MetricAnalysisResult")
    if spec is None:
        spec = ParetoAnalysisSpec("pareto", tuple(
            m.name for m in analysis.spec.metrics if m.direction is not None
        ))
    if not isinstance(spec, ParetoAnalysisSpec):
        raise TypeError("spec must be ParetoAnalysisSpec or None")
    definitions = _objectives(analysis, spec)
    eligible = [i for i, p in enumerate(analysis.points) if p.status == "feasible"]
    values = {i: analysis.points[i].metrics for i in eligible}

    def dominates(left, right):
        better = False
        for metric in definitions:
            a, b = values[left][metric.name], values[right][metric.name]
            if metric.direction is ObjectiveDirection.MINIMIZE:
                if a > b:
                    return False
                better = better or a < b
            else:
                if a < b:
                    return False
                better = better or a > b
        return better

    successors = {i: [] for i in eligible}
    incoming = {i: 0 for i in eligible}
    for position, left in enumerate(eligible):
        for right in eligible[position + 1:]:
            if dominates(left, right):
                successors[left].append(right)
                incoming[right] += 1
            elif dominates(right, left):
                successors[right].append(left)
                incoming[left] += 1
    current = [i for i in eligible if incoming[i] == 0]
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
    points = tuple(ParetoPointResult(
        point, ranks.get(index),
        tuple((m.name, values[index][m.name]) for m in definitions)
        if index in ranks else (),
    ) for index, point in enumerate(analysis.points))
    return ParetoAnalysisResult(spec, analysis, points, tuple(fronts))


__all__ = [
    "ParetoAnalysisSpec", "ParetoPointResult", "ParetoAnalysisResult", "analyze_pareto",
]
