# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Complete-case analysis of stored MODEL execution, preserving Phase K rules."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from ..dtco.metrics import (
    ConstraintEvaluation, ConstraintOperator, MetricAnalysisSpec, MetricConstraint,
    MetricDefinition, ObjectiveDirection,
)
from ..hashing import canonical_hash
from ._serialization import strict_fields
from .execution import _runtime, _error_type
from .feasibility import NominalMetricReference
from .metrics import _finite_float
from .model_execution import ModelExecutionResult
from .model_sampling import _snapshot, _strict_json
from .statistics import EnsembleStatisticsSpec, _metric_population_summary


def _metric_spec_from_dict(data: dict[str, Any]) -> MetricAnalysisSpec:
    strict_fields(data, label="MODEL metric spec", required={"schema_version", "name", "metrics", "constraints"})
    if data["schema_version"] != "dtco-metric-analysis-v1":
        raise ValueError("unsupported metric spec schema")
    if type(data["metrics"]) is not list or type(data["constraints"]) is not list:
        raise TypeError("metric and constraint definitions must be lists")
    metrics, constraints = [], []
    for item in data["metrics"]:
        strict_fields(item, label="metric", required={"name", "path", "unit", "direction"})
        if type(item["path"]) is not list:
            raise TypeError("metric path must be a list")
        metrics.append(MetricDefinition(item["name"], tuple(item["path"]), item["unit"],
                       None if item["direction"] is None else ObjectiveDirection(item["direction"])))
    for item in data["constraints"]:
        strict_fields(item, label="constraint", required={"name", "metric_name", "operator", "threshold", "unit"})
        constraints.append(MetricConstraint(item["name"], item["metric_name"], ConstraintOperator(item["operator"]),
                                            item["threshold"], item["unit"]))
    return MetricAnalysisSpec(data["name"], tuple(metrics), tuple(constraints))


def _assess(source: ModelExecutionResult, spec: MetricAnalysisSpec) -> list[dict[str, Any]]:
    points = []
    for point in source.points:
        original = point.to_dict()
        record = {"realization_id": original["realization_id"], "sample_index": original["sample_index"],
                  "sample_id": original["sample_id"], "sample_hash": original["sample_hash"],
                  "status": "failed", "metric_values": [], "constraints": [],
                  "failure_stage": None, "failure_category": None, "error_type": None, "error_message": None}
        if original["status"] == "failed":
            for name in ("failure_stage", "failure_category", "error_type", "error_message"):
                record[name] = original[name]
        else:
            try:
                values = {m.name: _finite_float(m.extract(original["output"]), m.name) for m in spec.metrics}
                constraints = [ConstraintEvaluation(c, values[c.metric_name]) for c in spec.constraints]
                record["metric_values"] = [[m.name, values[m.name]] for m in spec.metrics]
                record["constraints"] = [c.to_dict() for c in constraints]
                record["status"] = "feasible" if all(c.satisfied for c in constraints) else "infeasible"
            except (TypeError, ValueError, OverflowError) as exc:
                record.update(failure_stage="metric-extraction", failure_category="metric-extraction",
                              error_type=_error_type(exc), error_message=str(exc) or type(exc).__name__)
        points.append(record)
    return points


@dataclass(frozen=True)
class ModelPopulationAnalysis:
    """Immutable source-linked assessment, statistics and feasibility envelope.

    All derived data are recomputed from the stored source. No simulator or
    random generator is called. MODEL archives are not converted to Phase K.
    """

    source: ModelExecutionResult
    metric_spec: MetricAnalysisSpec
    statistics_spec: EnsembleStatisticsSpec = field(default_factory=EnsembleStatisticsSpec)
    nominal_references: tuple[NominalMetricReference, ...] = ()
    runtime: tuple[tuple[str, str], ...] = field(default_factory=lambda: tuple(sorted(_runtime().items())))

    def __post_init__(self) -> None:
        if not isinstance(self.source, ModelExecutionResult):
            raise TypeError("source must be ModelExecutionResult")
        if not isinstance(self.metric_spec, MetricAnalysisSpec) or not isinstance(self.statistics_spec, EnsembleStatisticsSpec):
            raise TypeError("metric/statistics specs have incorrect types")
        object.__setattr__(self, "nominal_references", tuple(self.nominal_references))
        object.__setattr__(self, "runtime", tuple(tuple(item) for item in self.runtime))
        runtime = dict(self.runtime)
        if len(runtime) != len(self.runtime) or set(runtime) != set(_runtime()) or any(
                type(v) is not str or not v for v in runtime.values()):
            raise ValueError("invalid MODEL analysis runtime")
        units = {m.name: m.unit for m in self.metric_spec.metrics}
        names = []
        for ref in self.nominal_references:
            if not isinstance(ref, NominalMetricReference):
                raise TypeError("nominal_references must contain NominalMetricReference")
            if ref.metric_name not in units or ref.unit != units[ref.metric_name]:
                raise ValueError("nominal reference metric/unit mismatch")
            names.append(ref.metric_name)
        if len(names) != len(set(names)):
            raise ValueError("duplicate nominal references")
        # Validate aggregate ranges eagerly; overflow must not produce an archive.
        self._derived()

    def _derived(self) -> dict[str, Any]:
        points = _assess(self.source, self.metric_spec)
        assessed = [p for p in points if p["status"] in {"feasible", "infeasible"}]
        attempted = len(points)
        feasible = sum(p["status"] == "feasible" for p in points)
        failed = attempted - len(assessed)
        stages = {}
        for point in points:
            if point["status"] == "failed":
                stage = point["failure_stage"]
                stages[stage] = stages.get(stage, 0) + 1
        indices = tuple(p["sample_index"] for p in assessed)
        identities = tuple(p["realization_id"] for p in assessed)
        summaries = []
        try:
            for metric in self.metric_spec.metrics:
                summaries.append(_metric_population_summary(metric_name=metric.name, unit=metric.unit,
                    values=[dict(p["metric_values"])[metric.name] for p in assessed],
                    sample_indices=indices, realization_ids=identities, probabilities=self.statistics_spec.quantiles).to_dict())
        except (OverflowError, ArithmeticError) as exc:
            raise ValueError("derived MODEL statistics must be finite") from exc
        by_name = {s["metric_name"]: s for s in summaries}
        comparisons = []
        for ref in self.nominal_references:
            summary = by_name[ref.metric_name]
            mean_delta = None if not assessed else summary["mean"] - ref.nominal_value
            median_delta = None if not assessed else summary["median"] - ref.nominal_value
            if any(value is not None and not math.isfinite(value) for value in (mean_delta, median_delta)):
                raise ValueError("nominal comparison delta must be finite")
            comparisons.append({"metric_name": ref.metric_name, "unit": ref.unit, "nominal_value": ref.nominal_value,
                "denominator": len(assessed), "mean_delta": mean_delta, "median_delta": median_delta})
        def fraction(numerator, denominator):
            return {"numerator": numerator, "denominator": denominator,
                    "value": numerator / denominator if denominator else None}
        return {"points": points,
                "counts": {"attempted_count": attempted, "assessed_count": len(assessed), "feasible_count": feasible,
                           "infeasible_count": len(assessed) - feasible, "failed_count": failed,
                           "execution_failure_count": self.source.failure_count,
                           "metric_failure_count": failed - self.source.failure_count},
                "failure_stage_counts": dict(sorted(stages.items())), "statistics": summaries,
                "fractions": {"coverage_fraction": fraction(len(assessed), attempted),
                              "simulated_pass_fraction": fraction(feasible, attempted),
                              "ensemble_feasibility_fraction": fraction(feasible, len(assessed)),
                              "failure_fraction": fraction(failed, attempted)},
                "nominal_comparisons": comparisons}

    @property
    def counts(self) -> dict[str, int]:
        return self._derived()["counts"]

    @property
    def fractions(self) -> dict[str, dict[str, int | float | None]]:
        return self._derived()["fractions"]

    def _payload(self) -> dict[str, Any]:
        return {"schema_version": "model-population-analysis-v1", "algorithm": "phase-l-complete-case-analysis-v1",
                "source": self.source.to_dict(), "source_hash": self.source.result_hash,
                "metric_spec": self.metric_spec.to_dict(), "metric_spec_hash": self.metric_spec.definition_hash,
                "statistics_spec": self.statistics_spec.to_dict(), "statistics_spec_hash": self.statistics_spec.definition_hash,
                "nominal_references": [r.to_dict() for r in self.nominal_references], "runtime": dict(self.runtime),
                **self._derived()}

    @property
    def analysis_hash(self) -> str:
        return canonical_hash(self._payload())

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "analysis_hash": canonical_hash(payload)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelPopulationAnalysis:
        strict_fields(data, label="MODEL population analysis", required={"schema_version", "algorithm", "source", "source_hash",
            "metric_spec", "metric_spec_hash", "statistics_spec", "statistics_spec_hash", "nominal_references", "runtime",
            "points", "counts", "failure_stage_counts", "statistics", "fractions", "nominal_comparisons", "analysis_hash"})
        if type(data["nominal_references"]) is not list or type(data["runtime"]) is not dict:
            raise TypeError("invalid nominal references/runtime")
        stats = data["statistics_spec"]
        strict_fields(stats, label="statistics spec", required={"schema_version", "quantiles", "quantile_method",
                                                                "standard_deviation", "variance", "selection"})
        if type(stats["quantiles"]) is not list:
            raise TypeError("quantiles must be a list")
        references = []
        for item in data["nominal_references"]:
            strict_fields(item, label="nominal reference", required={"schema_version", "metric_name", "unit", "nominal_value"})
            if item["schema_version"] != "ensemble-nominal-metric-reference-v1":
                raise ValueError("unsupported nominal reference schema")
            references.append(NominalMetricReference(item["metric_name"], item["unit"], item["nominal_value"]))
        result = cls(ModelExecutionResult.from_dict(data["source"]), _metric_spec_from_dict(data["metric_spec"]),
                     EnsembleStatisticsSpec(tuple(stats["quantiles"])), tuple(references), tuple(sorted(data["runtime"].items())))
        # Compare canonical JSON, not Python equality (which conflates bool/int).
        if _snapshot(data) != _snapshot(result.to_dict()):
            raise ValueError("MODEL analysis derived content or identity mismatch")
        return result

    def to_json(self) -> str:
        return _snapshot(self.to_dict())

    @classmethod
    def from_json(cls, text: str) -> ModelPopulationAnalysis:
        return cls.from_dict(_strict_json(text))


def analyze_model_execution(source: ModelExecutionResult, metric_spec: MetricAnalysisSpec, *,
                            statistics_spec: EnsembleStatisticsSpec | None = None,
                            nominal_references: tuple[NominalMetricReference, ...] = ()) -> ModelPopulationAnalysis:
    """Assess all attempts and summarize assessed complete cases without physics."""
    return ModelPopulationAnalysis(source, metric_spec,
        EnsembleStatisticsSpec() if statistics_spec is None else statistics_spec, nominal_references)


__all__ = ["ModelPopulationAnalysis", "analyze_model_execution"]
