# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Population-statistics contracts for Phase K ensembles."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import platform
import statistics
from typing import Any

from .._version import __version__
from ..hashing import canonical_hash
from .metrics import EnsembleMetricAnalysisResult


_STATISTICS_ALGORITHM = (
    "phase-k-population-statistics-v1"
)


def _json_snapshot(
    value: dict[str, Any],
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


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


def _finite_float_or_none(
    value: float | None,
    field: str,
) -> float | None:
    if value is None:
        return None

    if type(value) is not float:
        raise TypeError(
            f"{field} must be a Python float or None"
        )

    if not math.isfinite(value):
        raise ValueError(
            f"{field} must be finite"
        )

    return value


@dataclass(frozen=True)
class EnsembleStatisticsSpec:
    """Fixed Phase K4b population-statistics conventions."""

    quantiles: tuple[float, ...] = (
        0.05,
        0.5,
        0.95,
    )

    def __post_init__(self) -> None:
        if isinstance(
            self.quantiles,
            (str, bytes),
        ):
            raise TypeError(
                "quantiles must be a sequence "
                "of probabilities"
            )

        values = tuple(
            self.quantiles
        )

        normalized = []

        for value in values:
            if (
                isinstance(value, bool)
                or type(value)
                not in (int, float)
                or not math.isfinite(value)
                or not 0.0 <= value <= 1.0
            ):
                raise ValueError(
                    "quantiles must be finite numeric "
                    "probabilities in [0, 1]"
                )

            normalized.append(
                float(value)
            )

        normalized_tuple = tuple(
            normalized
        )

        if (
            len(set(normalized_tuple))
            != len(normalized_tuple)
        ):
            raise ValueError(
                "duplicate quantiles"
            )

        object.__setattr__(
            self,
            "quantiles",
            normalized_tuple,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "ensemble-statistics-spec-v1"
            ),
            "quantiles": list(
                self.quantiles
            ),
            "quantile_method": (
                "linear-n-minus-one"
            ),
            "standard_deviation": (
                "population-ddof-0"
            ),
            "variance": (
                "population-ddof-0"
            ),
            "selection": (
                "all-assessed-complete-cases"
            ),
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


@dataclass(frozen=True)
class MetricPopulationSummary:
    """Population summary for one declared K4a metric."""

    metric_name: str
    unit: str
    denominator: int
    sample_indices: tuple[int, ...]
    realization_ids: tuple[str, ...]
    minimum: float | None
    maximum: float | None
    mean: float | None
    variance: float | None
    standard_deviation: float | None
    median: float | None
    quantiles: tuple[
        tuple[float, float | None],
        ...
    ]

    def __post_init__(self) -> None:
        _label(
            self.metric_name,
            "metric_name",
        )

        _label(
            self.unit,
            "unit",
        )

        if (
            type(self.denominator) is not int
            or self.denominator < 0
        ):
            raise ValueError(
                "denominator must be a "
                "nonnegative integer"
            )

        sample_indices = tuple(
            self.sample_indices
        )

        realization_ids = tuple(
            self.realization_ids
        )

        quantiles = tuple(
            self.quantiles
        )

        if any(
            type(index) is not int
            or index < 0
            for index in sample_indices
        ):
            raise ValueError(
                "sample_indices must contain "
                "nonnegative integers"
            )

        if (
            len(set(sample_indices))
            != len(sample_indices)
        ):
            raise ValueError(
                "sample_indices must be unique"
            )

        for realization_id in realization_ids:
            _label(
                realization_id,
                "realization_id",
            )

        if (
            len(set(realization_ids))
            != len(realization_ids)
        ):
            raise ValueError(
                "realization_ids must be unique"
            )

        if (
            len(sample_indices)
            != self.denominator
            or len(realization_ids)
            != self.denominator
        ):
            raise ValueError(
                "summary membership must match "
                "denominator"
            )

        scalar_fields = (
            "minimum",
            "maximum",
            "mean",
            "variance",
            "standard_deviation",
            "median",
        )

        scalar_values = tuple(
            _finite_float_or_none(
                getattr(
                    self,
                    field,
                ),
                field,
            )
            for field in scalar_fields
        )

        normalized_quantiles = []

        seen_probabilities = set()

        for item in quantiles:
            if (
                not isinstance(
                    item,
                    tuple,
                )
                or len(item) != 2
            ):
                raise TypeError(
                    "quantiles must contain "
                    "(probability, value) tuples"
                )

            probability, value = item

            if (
                type(probability)
                is not float
                or not math.isfinite(
                    probability
                )
                or not 0.0
                <= probability
                <= 1.0
            ):
                raise ValueError(
                    "quantile probability must be "
                    "a finite Python float in [0, 1]"
                )

            if (
                probability
                in seen_probabilities
            ):
                raise ValueError(
                    "duplicate quantile probability"
                )

            seen_probabilities.add(
                probability
            )

            normalized_quantiles.append(
                (
                    probability,
                    _finite_float_or_none(
                        value,
                        "quantile value",
                    ),
                )
            )

        if self.denominator == 0:
            if any(
                value is not None
                for value in scalar_values
            ):
                raise ValueError(
                    "empty summary requires "
                    "None scalar values"
                )

            if any(
                value is not None
                for _, value
                in normalized_quantiles
            ):
                raise ValueError(
                    "empty summary requires "
                    "None quantile values"
                )

        else:
            if any(
                value is None
                for value in scalar_values
            ):
                raise ValueError(
                    "nonempty summary requires "
                    "all scalar statistics"
                )

            if any(
                value is None
                for _, value
                in normalized_quantiles
            ):
                raise ValueError(
                    "nonempty summary requires "
                    "all quantile values"
                )

            if (
                self.minimum
                > self.maximum
            ):
                raise ValueError(
                    "minimum cannot exceed maximum"
                )

            if (
                self.variance < 0.0
                or self.standard_deviation < 0.0
            ):
                raise ValueError(
                    "variance and standard deviation "
                    "must be nonnegative"
                )

            if not (
                self.minimum
                <= self.mean
                <= self.maximum
            ):
                raise ValueError(
                    "mean must lie within "
                    "minimum and maximum"
                )

            if not (
                self.minimum
                <= self.median
                <= self.maximum
            ):
                raise ValueError(
                    "median must lie within "
                    "minimum and maximum"
                )

            if any(
                not (
                    self.minimum
                    <= value
                    <= self.maximum
                )
                for _, value
                in normalized_quantiles
            ):
                raise ValueError(
                    "quantile values must lie within "
                    "minimum and maximum"
                )

            if not math.isclose(
                self.standard_deviation ** 2,
                self.variance,
                rel_tol=1e-12,
                abs_tol=1e-15,
            ):
                raise ValueError(
                    "variance and standard deviation "
                    "are inconsistent"
                )

        object.__setattr__(
            self,
            "sample_indices",
            sample_indices,
        )

        object.__setattr__(
            self,
            "realization_ids",
            realization_ids,
        )

        object.__setattr__(
            self,
            "quantiles",
            tuple(
                normalized_quantiles
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "unit": self.unit,
            "denominator": self.denominator,
            "sample_indices": list(
                self.sample_indices
            ),
            "realization_ids": list(
                self.realization_ids
            ),
            "minimum": self.minimum,
            "maximum": self.maximum,
            "mean": self.mean,
            "variance": self.variance,
            "standard_deviation": (
                self.standard_deviation
            ),
            "median": self.median,
            "quantiles": [
                {
                    "probability": probability,
                    "value": value,
                }
                for probability, value
                in self.quantiles
            ],
        }

    @property
    def summary_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


@dataclass(frozen=True)
class EnsemblePopulationStatistics:
    """K4b population statistics over one immutable K4a result."""

    spec: EnsembleStatisticsSpec
    source: EnsembleMetricAnalysisResult
    metric_statistics: tuple[
        MetricPopulationSummary,
        ...
    ]
    runtime_json: str = field(
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.spec,
            EnsembleStatisticsSpec,
        ):
            raise TypeError(
                "spec must be EnsembleStatisticsSpec"
            )

        if not isinstance(
            self.source,
            EnsembleMetricAnalysisResult,
        ):
            raise TypeError(
                "source must be "
                "EnsembleMetricAnalysisResult"
            )

        metric_statistics = tuple(
            self.metric_statistics
        )

        if any(
            not isinstance(
                summary,
                MetricPopulationSummary,
            )
            for summary
            in metric_statistics
        ):
            raise TypeError(
                "metric_statistics must contain "
                "MetricPopulationSummary instances"
            )

        expected_metrics = tuple(
            (
                metric.name,
                metric.unit,
            )
            for metric
            in self.source.spec.metrics
        )

        actual_metrics = tuple(
            (
                summary.metric_name,
                summary.unit,
            )
            for summary
            in metric_statistics
        )

        if (
            actual_metrics
            != expected_metrics
        ):
            raise ValueError(
                "metric statistics differ from "
                "source metric specification"
            )

        assessed = tuple(
            point
            for point in self.source.points
            if point.status != "failed"
        )

        expected_indices = tuple(
            point.source.identity.sample_index
            for point in assessed
        )

        expected_realization_ids = tuple(
            point.source.identity.realization_id
            for point in assessed
        )

        expected_probabilities = (
            self.spec.quantiles
        )

        for summary in metric_statistics:
            if (
                summary.denominator
                != len(assessed)
            ):
                raise ValueError(
                    "metric denominator differs "
                    "from assessed count"
                )

            if (
                summary.sample_indices
                != expected_indices
            ):
                raise ValueError(
                    "metric sample membership "
                    "differs from assessed points"
                )

            if (
                summary.realization_ids
                != expected_realization_ids
            ):
                raise ValueError(
                    "metric realization membership "
                    "differs from assessed points"
                )

            if tuple(
                probability
                for probability, _
                in summary.quantiles
            ) != expected_probabilities:
                raise ValueError(
                    "metric quantiles differ from "
                    "statistics specification"
                )

        object.__setattr__(
            self,
            "metric_statistics",
            metric_statistics,
        )

        runtime = {
            "python": (
                platform.python_version()
            ),
            "python_implementation": (
                platform.python_implementation()
            ),
            "ncmemsim": __version__,
            "algorithm": (
                _STATISTICS_ALGORITHM
            ),
        }

        object.__setattr__(
            self,
            "runtime_json",
            _json_snapshot(runtime),
        )


    @property
    def runtime(self) -> dict[str, str]:
        return json.loads(
            self.runtime_json
        )


    @property
    def attempted_count(self) -> int:
        return len(
            self.source.points
        )

    @property
    def assessed_count(self) -> int:
        return (
            self.feasible_count
            + self.infeasible_count
        )

    @property
    def feasible_count(self) -> int:
        return sum(
            point.status == "feasible"
            for point in self.source.points
        )

    @property
    def infeasible_count(self) -> int:
        return sum(
            point.status == "infeasible"
            for point in self.source.points
        )

    @property
    def failed_count(self) -> int:
        return sum(
            point.status == "failed"
            for point in self.source.points
        )

    @property
    def coverage_fraction(self) -> float:
        return (
            self.assessed_count
            / self.attempted_count
        )

    @property
    def analysis_hash(self) -> str:
        return canonical_hash(
            {
                "schema_version": (
                    "ensemble-population-statistics-run-v1"
                ),
                "spec": self.spec.to_dict(),
                "source_result_hash": (
                    self.source.result_hash
                ),
                "runtime": self.runtime,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "ensemble-population-statistics-result-v1"
            ),
            "analysis_hash": (
                self.analysis_hash
            ),
            "definition_hash": (
                self.spec.definition_hash
            ),
            "runtime": self.runtime,
            "source_result_hash": (
                self.source.result_hash
            ),
            "counts": {
                "attempted": (
                    self.attempted_count
                ),
                "assessed": (
                    self.assessed_count
                ),
                "feasible": (
                    self.feasible_count
                ),
                "infeasible": (
                    self.infeasible_count
                ),
                "failed": (
                    self.failed_count
                ),
            },
            "coverage_fraction": {
                "value": (
                    self.coverage_fraction
                ),
                "numerator": (
                    self.assessed_count
                ),
                "denominator": (
                    self.attempted_count
                ),
            },
            "metric_statistics": [
                summary.to_dict()
                for summary
                in self.metric_statistics
            ],
        }

    @property
    def result_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


def _linear_quantile(
    ordered: list[float],
    probability: float,
) -> float:
    position = (
        (len(ordered) - 1)
        * probability
    )

    lower = math.floor(
        position
    )

    upper = math.ceil(
        position
    )

    weight = (
        position - lower
    )

    # Equal interpolation endpoints must retain their exact constant value.
    # Weighted arithmetic can otherwise round outside a constant population.
    if ordered[lower] == ordered[upper]:
        return float(ordered[lower])

    return float(
        (1.0 - weight)
        * ordered[lower]
        + weight
        * ordered[upper]
    )


def _metric_population_summary(
    *,
    metric_name: str,
    unit: str,
    values: list[float],
    sample_indices: tuple[int, ...],
    realization_ids: tuple[str, ...],
    probabilities: tuple[float, ...],
) -> MetricPopulationSummary:
    if not values:
        return MetricPopulationSummary(
            metric_name=metric_name,
            unit=unit,
            denominator=0,
            sample_indices=(),
            realization_ids=(),
            minimum=None,
            maximum=None,
            mean=None,
            variance=None,
            standard_deviation=None,
            median=None,
            quantiles=tuple(
                (
                    probability,
                    None,
                )
                for probability
                in probabilities
            ),
        )

    ordered = sorted(
        values
    )

    mean = float(
        statistics.mean(values)
    )

    variance = float(
        statistics.pvariance(
            values,
            mu=mean,
        )
    )

    standard_deviation = float(
        math.sqrt(
            variance
        )
    )

    middle = (
        len(ordered) // 2
    )

    if len(ordered) % 2:
        median = float(
            ordered[middle]
        )
    else:
        median = float(
            ordered[middle - 1] / 2.0
            + ordered[middle] / 2.0
        )

    quantiles = tuple(
        (
            probability,
            _linear_quantile(
                ordered,
                probability,
            ),
        )
        for probability
        in probabilities
    )

    return MetricPopulationSummary(
        metric_name=metric_name,
        unit=unit,
        denominator=len(values),
        sample_indices=sample_indices,
        realization_ids=realization_ids,
        minimum=float(
            ordered[0]
        ),
        maximum=float(
            ordered[-1]
        ),
        mean=mean,
        variance=variance,
        standard_deviation=(
            standard_deviation
        ),
        median=median,
        quantiles=quantiles,
    )


def summarize_ensemble_metrics(
    source: EnsembleMetricAnalysisResult,
    spec: EnsembleStatisticsSpec,
) -> EnsemblePopulationStatistics:
    """Compute K4b population statistics without rerunning physics."""

    if not isinstance(
        source,
        EnsembleMetricAnalysisResult,
    ):
        raise TypeError(
            "source must be "
            "EnsembleMetricAnalysisResult"
        )

    if not isinstance(
        spec,
        EnsembleStatisticsSpec,
    ):
        raise TypeError(
            "spec must be EnsembleStatisticsSpec"
        )

    assessed = tuple(
        point
        for point in source.points
        if point.status != "failed"
    )

    sample_indices = tuple(
        point.source.identity.sample_index
        for point in assessed
    )

    realization_ids = tuple(
        point.source.identity.realization_id
        for point in assessed
    )

    summaries = tuple(
        _metric_population_summary(
            metric_name=metric.name,
            unit=metric.unit,
            values=[
                point.metrics[
                    metric.name
                ]
                for point in assessed
            ],
            sample_indices=(
                sample_indices
            ),
            realization_ids=(
                realization_ids
            ),
            probabilities=(
                spec.quantiles
            ),
        )
        for metric
        in source.spec.metrics
    )

    return EnsemblePopulationStatistics(
        spec=spec,
        source=source,
        metric_statistics=summaries,
    )


__all__ = [
    "EnsemblePopulationStatistics",
    "EnsembleStatisticsSpec",
    "MetricPopulationSummary",
]
