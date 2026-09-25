"""Feasibility and nominal-comparison contracts for Phase K ensembles."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import platform
from typing import Any

from .._version import __version__
from ..hashing import canonical_hash
from .statistics import (
    EnsemblePopulationStatistics,
)


_FEASIBILITY_ALGORITHM = (
    "phase-k-feasibility-nominal-comparison-v1"
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


def _finite_float(
    value: int | float,
    field: str,
) -> float:
    if (
        isinstance(value, bool)
        or type(value) not in (int, float)
    ):
        raise TypeError(
            f"{field} must be a finite numeric value"
        )

    result = float(value)

    if not math.isfinite(result):
        raise ValueError(
            f"{field} must be finite"
        )

    if (
        type(value) is int
        and result != value
    ):
        raise ValueError(
            f"{field} must be exactly representable "
            "as a Python float"
        )

    return result


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


def _json_snapshot(
    value: dict[str, Any],
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


@dataclass(frozen=True)
class NominalMetricReference:
    """Explicit nominal reference for one declared metric."""

    metric_name: str
    unit: str
    nominal_value: float

    def __post_init__(self) -> None:
        _label(
            self.metric_name,
            "metric_name",
        )

        _label(
            self.unit,
            "unit",
        )

        object.__setattr__(
            self,
            "nominal_value",
            _finite_float(
                self.nominal_value,
                "nominal_value",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "ensemble-nominal-metric-reference-v1"
            ),
            "metric_name": self.metric_name,
            "unit": self.unit,
            "nominal_value": (
                self.nominal_value
            ),
        }

    @property
    def reference_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


@dataclass(frozen=True)
class NominalMetricComparison:
    """Population mean/median comparison with one nominal reference."""

    reference: NominalMetricReference
    denominator: int
    population_mean: float | None
    population_median: float | None
    mean_delta: float | None
    median_delta: float | None

    def __post_init__(self) -> None:
        if not isinstance(
            self.reference,
            NominalMetricReference,
        ):
            raise TypeError(
                "reference must be "
                "NominalMetricReference"
            )

        if (
            type(self.denominator) is not int
            or self.denominator < 0
        ):
            raise ValueError(
                "denominator must be a "
                "nonnegative integer"
            )

        population_mean = (
            _finite_float_or_none(
                self.population_mean,
                "population_mean",
            )
        )

        population_median = (
            _finite_float_or_none(
                self.population_median,
                "population_median",
            )
        )

        mean_delta = (
            _finite_float_or_none(
                self.mean_delta,
                "mean_delta",
            )
        )

        median_delta = (
            _finite_float_or_none(
                self.median_delta,
                "median_delta",
            )
        )

        values = (
            population_mean,
            population_median,
            mean_delta,
            median_delta,
        )

        if self.denominator == 0:
            if any(
                value is not None
                for value in values
            ):
                raise ValueError(
                    "zero-denominator nominal comparison "
                    "requires None values"
                )

        else:
            if any(
                value is None
                for value in values
            ):
                raise ValueError(
                    "nonzero-denominator nominal comparison "
                    "requires complete values"
                )

            expected_mean_delta = (
                population_mean
                - self.reference.nominal_value
            )

            expected_median_delta = (
                population_median
                - self.reference.nominal_value
            )

            if not math.isfinite(
                expected_mean_delta
            ):
                raise ValueError(
                    "mean_delta is not finitely "
                    "representable"
                )

            if not math.isfinite(
                expected_median_delta
            ):
                raise ValueError(
                    "median_delta is not finitely "
                    "representable"
                )

            if (
                mean_delta
                != expected_mean_delta
            ):
                raise ValueError(
                    "mean_delta differs from "
                    "population mean minus nominal"
                )

            if (
                median_delta
                != expected_median_delta
            ):
                raise ValueError(
                    "median_delta differs from "
                    "population median minus nominal"
                )

        object.__setattr__(
            self,
            "population_mean",
            population_mean,
        )

        object.__setattr__(
            self,
            "population_median",
            population_median,
        )

        object.__setattr__(
            self,
            "mean_delta",
            mean_delta,
        )

        object.__setattr__(
            self,
            "median_delta",
            median_delta,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference": (
                self.reference.to_dict()
            ),
            "denominator": (
                self.denominator
            ),
            "population_mean": (
                self.population_mean
            ),
            "population_median": (
                self.population_median
            ),
            "mean_delta": (
                self.mean_delta
            ),
            "median_delta": (
                self.median_delta
            ),
        }

    @property
    def comparison_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


@dataclass(frozen=True)
class EnsembleFeasibilitySummary:
    """K4c feasibility fractions and explicit nominal comparisons."""

    source: EnsemblePopulationStatistics
    nominal_references: tuple[
        NominalMetricReference,
        ...
    ]
    comparisons: tuple[
        NominalMetricComparison,
        ...
    ]
    runtime_json: str = field(
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            EnsemblePopulationStatistics,
        ):
            raise TypeError(
                "source must be "
                "EnsemblePopulationStatistics"
            )

        nominal_references = tuple(
            self.nominal_references
        )

        comparisons = tuple(
            self.comparisons
        )

        if any(
            not isinstance(
                reference,
                NominalMetricReference,
            )
            for reference
            in nominal_references
        ):
            raise TypeError(
                "nominal_references must contain "
                "NominalMetricReference instances"
            )

        if any(
            not isinstance(
                comparison,
                NominalMetricComparison,
            )
            for comparison
            in comparisons
        ):
            raise TypeError(
                "comparisons must contain "
                "NominalMetricComparison instances"
            )

        reference_names = tuple(
            reference.metric_name
            for reference
            in nominal_references
        )

        if (
            len(set(reference_names))
            != len(reference_names)
        ):
            raise ValueError(
                "nominal metric references "
                "must be unique"
            )

        if (
            len(comparisons)
            != len(nominal_references)
        ):
            raise ValueError(
                "comparisons must match declared "
                "nominal references"
            )

        source_summaries = {
            summary.metric_name: summary
            for summary
            in self.source.metric_statistics
        }

        for reference, comparison in zip(
            nominal_references,
            comparisons,
        ):
            if (
                comparison.reference
                != reference
            ):
                raise ValueError(
                    "comparison reference order "
                    "does not match declared references"
                )

            if (
                reference.metric_name
                not in source_summaries
            ):
                raise ValueError(
                    "nominal reference metric is absent "
                    "from source statistics"
                )

            source_summary = (
                source_summaries[
                    reference.metric_name
                ]
            )

            if (
                reference.unit
                != source_summary.unit
            ):
                raise ValueError(
                    "nominal reference unit differs "
                    "from source metric unit"
                )

            if (
                comparison.denominator
                != source_summary.denominator
            ):
                raise ValueError(
                    "nominal comparison denominator "
                    "differs from source metric"
                )

            if (
                comparison.population_mean
                != source_summary.mean
            ):
                raise ValueError(
                    "nominal comparison population mean "
                    "differs from source metric"
                )

            if (
                comparison.population_median
                != source_summary.median
            ):
                raise ValueError(
                    "nominal comparison population median "
                    "differs from source metric"
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
                _FEASIBILITY_ALGORITHM
            ),
        }

        object.__setattr__(
            self,
            "nominal_references",
            nominal_references,
        )

        object.__setattr__(
            self,
            "comparisons",
            comparisons,
        )

        object.__setattr__(
            self,
            "runtime_json",
            _json_snapshot(runtime),
        )

    @property
    def attempted_count(self) -> int:
        return (
            self.source.attempted_count
        )

    @property
    def assessed_count(self) -> int:
        return (
            self.source.assessed_count
        )

    @property
    def feasible_count(self) -> int:
        return (
            self.source.feasible_count
        )

    @property
    def infeasible_count(self) -> int:
        return (
            self.source.infeasible_count
        )

    @property
    def failed_count(self) -> int:
        return (
            self.source.failed_count
        )

    @property
    def simulated_pass_fraction(self) -> float:
        return (
            self.feasible_count
            / self.attempted_count
        )

    @property
    def ensemble_feasibility_fraction(
        self,
    ) -> float | None:
        if self.assessed_count == 0:
            return None

        return (
            self.feasible_count
            / self.assessed_count
        )

    @property
    def failure_fraction(self) -> float:
        return (
            self.failed_count
            / self.attempted_count
        )

    @property
    def runtime(self) -> dict[str, str]:
        return json.loads(
            self.runtime_json
        )

    @property
    def analysis_hash(self) -> str:
        return canonical_hash(
            {
                "schema_version": (
                    "ensemble-feasibility-analysis-run-v1"
                ),
                "source_result_hash": (
                    self.source.result_hash
                ),
                "nominal_references": [
                    reference.to_dict()
                    for reference
                    in self.nominal_references
                ],
                "runtime": self.runtime,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "ensemble-feasibility-summary-v1"
            ),
            "analysis_hash": (
                self.analysis_hash
            ),
            "source_result_hash": (
                self.source.result_hash
            ),
            "runtime": self.runtime,
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
            "simulated_pass_fraction": {
                "value": (
                    self.simulated_pass_fraction
                ),
                "numerator": (
                    self.feasible_count
                ),
                "denominator": (
                    self.attempted_count
                ),
            },
            "ensemble_feasibility_fraction": {
                "value": (
                    self.ensemble_feasibility_fraction
                ),
                "numerator": (
                    self.feasible_count
                ),
                "denominator": (
                    self.assessed_count
                ),
            },
            "failure_fraction": {
                "value": (
                    self.failure_fraction
                ),
                "numerator": (
                    self.failed_count
                ),
                "denominator": (
                    self.attempted_count
                ),
            },
            "nominal_references": [
                reference.to_dict()
                for reference
                in self.nominal_references
            ],
            "comparisons": [
                comparison.to_dict()
                for comparison
                in self.comparisons
            ],
        }

    @property
    def result_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


__all__ = [
    "EnsembleFeasibilitySummary",
    "NominalMetricComparison",
    "NominalMetricReference",
]
