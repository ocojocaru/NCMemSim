"""Integrity-linked Phase K ensemble reporting contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..hashing import canonical_hash
from .dtco import EnsembleDTCOStudy, EnsembleEligibilityResult
from .execution import EnsembleExecutionResult
from .feasibility import EnsembleFeasibilitySummary
from .metrics import EnsembleMetricAnalysisResult
from .statistics import EnsemblePopulationStatistics


@dataclass(frozen=True)
class EnsembleReportStudy:
    """One complete ordered K3-K5b study retained by a K6a report."""

    execution: EnsembleExecutionResult
    metric_analysis: EnsembleMetricAnalysisResult
    population_statistics: EnsemblePopulationStatistics
    feasibility: EnsembleFeasibilitySummary
    study: EnsembleDTCOStudy
    eligibility: EnsembleEligibilityResult

    def __post_init__(self) -> None:
        expected_types = (
            ("execution", self.execution, EnsembleExecutionResult),
            ("metric_analysis", self.metric_analysis, EnsembleMetricAnalysisResult),
            (
                "population_statistics",
                self.population_statistics,
                EnsemblePopulationStatistics,
            ),
            ("feasibility", self.feasibility, EnsembleFeasibilitySummary),
            ("study", self.study, EnsembleDTCOStudy),
            ("eligibility", self.eligibility, EnsembleEligibilityResult),
        )
        for name, value, expected in expected_types:
            if not isinstance(value, expected):
                raise TypeError(f"{name} must be {expected.__name__}")

        if self.metric_analysis.source.result_hash != self.execution.result_hash:
            raise ValueError("K4a source differs from retained K3 result")

        if (
            self.population_statistics.source.result_hash
            != self.metric_analysis.result_hash
        ):
            raise ValueError("K4b source differs from retained K4a result")

        if (
            self.feasibility.source.result_hash
            != self.population_statistics.result_hash
        ):
            raise ValueError("K4c source differs from retained K4b result")

        if self.study.source_result_hash != self.feasibility.result_hash:
            raise ValueError("K5 study source differs from retained K4c result")

        if self.eligibility.study.study_hash != self.study.study_hash:
            raise ValueError("K5b source study differs from retained K5 study")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "ensemble-report-study-v1",
            "execution": {
                "result_hash": self.execution.result_hash,
                "data": self.execution.to_dict(),
            },
            "metric_analysis": {
                "result_hash": self.metric_analysis.result_hash,
                "spec": self.metric_analysis.spec.to_dict(),
                "data": self.metric_analysis.to_dict(),
            },
            "population_statistics": {
                "result_hash": self.population_statistics.result_hash,
                "spec": self.population_statistics.spec.to_dict(),
                "data": self.population_statistics.to_dict(),
            },
            "feasibility": {
                "result_hash": self.feasibility.result_hash,
                "data": self.feasibility.to_dict(),
            },
            "study": {
                "study_hash": self.study.study_hash,
                "data": self.study.to_dict(),
            },
            "eligibility": {
                "result_hash": self.eligibility.result_hash,
                "data": self.eligibility.to_dict(),
            },
        }

    @property
    def result_hash(self) -> str:
        return canonical_hash(self.to_dict())


__all__ = ["EnsembleReportStudy"]
