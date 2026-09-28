"""Integrity-linked Phase K ensemble reporting contracts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Iterable

from .._version import __version__
from ..dtco.sweep import _json_snapshot
from ..hashing import canonical_hash
from .dtco import (
    EnsembleDTCOStudy,
    EnsembleEligibilityResult,
    EnsembleParetoAnalysisResult,
)
from .execution import EnsembleExecutionResult
from .feasibility import EnsembleFeasibilitySummary
from .metrics import EnsembleMetricAnalysisResult
from .sampling import SampleManifest
from .statistics import EnsemblePopulationStatistics


def _label(value: str, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise ValueError(
            f"{field} must be nonempty text without outer whitespace"
        )
    return value


def _fraction_payload(
    value: dict[str, Any],
    *,
    numerator: int,
    denominator: int,
    allow_none: bool,
    field: str,
) -> None:
    if type(value) is not dict or set(value) != {
        "value",
        "numerator",
        "denominator",
    }:
        raise ValueError(f"{field} fraction structure differs")

    if (
        value["numerator"] != numerator
        or value["denominator"] != denominator
    ):
        raise ValueError(f"{field} fraction denominator/value mismatch")

    expected = None
    if denominator != 0:
        expected = numerator / denominator
    elif not allow_none:
        raise ValueError(f"{field} denominator cannot be zero")

    if value["value"] != expected:
        raise ValueError(f"{field} fraction denominator/value mismatch")


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


def _wrapped_section(
    value: Any,
    field: str,
    *,
    hash_key: str = "result_hash",
) -> tuple[dict[str, Any], str]:
    if (
        type(value) is not dict
        or set(value) != {hash_key, "data"}
        or type(value.get("data")) is not dict
    ):
        raise ValueError(f"{field} report section structure differs")

    data = value["data"]
    expected = canonical_hash(data)
    if value[hash_key] != expected:
        raise ValueError(f"{field} hash differs")
    return data, expected


def _check_report_study_payload(payload: Any) -> str:
    if (
        type(payload) is not dict
        or set(payload)
        != {
            "schema_version",
            "execution",
            "metric_analysis",
            "population_statistics",
            "feasibility",
            "study",
            "eligibility",
        }
        or payload.get("schema_version") != "ensemble-report-study-v1"
    ):
        raise ValueError("unsupported or incomplete ensemble report study")

    execution, execution_hash = _wrapped_section(
        payload["execution"],
        "execution",
    )
    if execution.get("schema_version") != "ensemble-execution-result-v1":
        raise ValueError("unsupported execution result schema")
    if execution.get("execution_hash") != canonical_hash(
        execution.get("execution")
    ):
        raise ValueError("execution definition hash differs")
    if execution.get("nominal_hash") != canonical_hash(
        execution.get("execution", {}).get("nominal")
    ):
        raise ValueError("execution nominal hash differs")

    try:
        manifest = SampleManifest.from_dict(execution["manifest"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("embedded sample manifest integrity differs") from exc

    if manifest.manifest_hash != execution["manifest"]["manifest_hash"]:
        raise ValueError("embedded sample manifest hash differs")

    points = execution.get("points")
    if type(points) is not list or len(points) != manifest.sampling_spec.sample_count:
        raise ValueError("execution must retain every manifest sample")

    success_count = sum(
        type(point) is dict and point.get("status") == "success"
        for point in points
    )
    if (
        execution.get("success_count") != success_count
        or execution.get("failure_count") != len(points) - success_count
    ):
        raise ValueError("execution counts differ from retained points")

    metric_wrapper = payload["metric_analysis"]
    if (
        type(metric_wrapper) is not dict
        or set(metric_wrapper) != {"result_hash", "spec", "data"}
        or type(metric_wrapper.get("spec")) is not dict
        or type(metric_wrapper.get("data")) is not dict
    ):
        raise ValueError("metric analysis report section structure differs")
    metric = metric_wrapper["data"]
    metric_hash = canonical_hash(metric)
    if metric_wrapper["result_hash"] != metric_hash:
        raise ValueError("metric analysis hash differs")
    if metric.get("schema_version") != "ensemble-metric-analysis-result-v1":
        raise ValueError("unsupported metric analysis schema")
    if metric.get("definition_hash") != canonical_hash(metric_wrapper["spec"]):
        raise ValueError("metric definition hash differs")
    if metric.get("source_result_hash") != execution_hash:
        raise ValueError("K4a source differs from retained K3 result")
    if metric.get("analysis_hash") != canonical_hash(
        {
            "schema_version": "ensemble-metric-analysis-run-v1",
            "spec": metric_wrapper["spec"],
            "source_result_hash": execution_hash,
        }
    ):
        raise ValueError("metric analysis identity differs")
    if (
        type(metric.get("points")) is not list
        or len(metric["points"]) != len(points)
    ):
        raise ValueError("metric analysis must retain every execution point")

    stats_wrapper = payload["population_statistics"]
    if (
        type(stats_wrapper) is not dict
        or set(stats_wrapper) != {"result_hash", "spec", "data"}
        or type(stats_wrapper.get("spec")) is not dict
        or type(stats_wrapper.get("data")) is not dict
    ):
        raise ValueError("population statistics report section structure differs")
    statistics = stats_wrapper["data"]
    statistics_hash = canonical_hash(statistics)
    if stats_wrapper["result_hash"] != statistics_hash:
        raise ValueError("population statistics hash differs")
    if (
        statistics.get("schema_version")
        != "ensemble-population-statistics-result-v1"
    ):
        raise ValueError("unsupported population statistics schema")
    if statistics.get("definition_hash") != canonical_hash(stats_wrapper["spec"]):
        raise ValueError("population statistics definition hash differs")
    if statistics.get("source_result_hash") != metric_hash:
        raise ValueError("K4b source differs from retained K4a result")
    if statistics.get("analysis_hash") != canonical_hash(
        {
            "schema_version": "ensemble-population-statistics-run-v1",
            "spec": stats_wrapper["spec"],
            "source_result_hash": metric_hash,
            "runtime": statistics.get("runtime"),
        }
    ):
        raise ValueError("population statistics identity differs")

    counts = statistics.get("counts")
    if type(counts) is not dict or set(counts) != {
        "attempted",
        "assessed",
        "feasible",
        "infeasible",
        "failed",
    }:
        raise ValueError("population counts structure differs")
    if (
        counts["attempted"] != len(metric["points"])
        or counts["assessed"] != counts["feasible"] + counts["infeasible"]
        or counts["attempted"] != counts["assessed"] + counts["failed"]
    ):
        raise ValueError("population counts differ")
    _fraction_payload(
        statistics.get("coverage_fraction"),
        numerator=counts["assessed"],
        denominator=counts["attempted"],
        allow_none=False,
        field="coverage",
    )

    metric_statistics = statistics.get("metric_statistics")
    if type(metric_statistics) is not list:
        raise ValueError("metric statistics must be a list")
    for summary in metric_statistics:
        if type(summary) is not dict:
            raise ValueError("metric statistic entry must be an object")
        if summary.get("denominator") != counts["assessed"]:
            raise ValueError("metric statistic denominator differs")
        if len(summary.get("sample_indices", [])) != counts["assessed"]:
            raise ValueError("metric statistic sample membership differs")
        if len(summary.get("realization_ids", [])) != counts["assessed"]:
            raise ValueError("metric statistic realization membership differs")

    feasibility, feasibility_hash = _wrapped_section(
        payload["feasibility"],
        "feasibility",
    )
    if feasibility.get("schema_version") != "ensemble-feasibility-summary-v1":
        raise ValueError("unsupported feasibility schema")
    if feasibility.get("source_result_hash") != statistics_hash:
        raise ValueError("K4c source differs from retained K4b result")
    if feasibility.get("analysis_hash") != canonical_hash(
        {
            "schema_version": "ensemble-feasibility-analysis-run-v1",
            "source_result_hash": statistics_hash,
            "nominal_references": feasibility.get("nominal_references"),
            "runtime": feasibility.get("runtime"),
        }
    ):
        raise ValueError("feasibility analysis identity differs")
    if feasibility.get("counts") != counts:
        raise ValueError("feasibility counts differ from population statistics")

    _fraction_payload(
        feasibility.get("simulated_pass_fraction"),
        numerator=counts["feasible"],
        denominator=counts["attempted"],
        allow_none=False,
        field="simulated pass",
    )
    _fraction_payload(
        feasibility.get("ensemble_feasibility_fraction"),
        numerator=counts["feasible"],
        denominator=counts["assessed"],
        allow_none=True,
        field="ensemble feasibility",
    )
    _fraction_payload(
        feasibility.get("failure_fraction"),
        numerator=counts["failed"],
        denominator=counts["attempted"],
        allow_none=False,
        field="failure",
    )

    references = feasibility.get("nominal_references")
    comparisons = feasibility.get("comparisons")
    if (
        type(references) is not list
        or type(comparisons) is not list
        or len(references) != len(comparisons)
    ):
        raise ValueError("nominal comparison count/order differs")

    study, study_hash = _wrapped_section(
        payload["study"],
        "study",
        hash_key="study_hash",
    )
    if study.get("schema_version") != "ensemble-dtco-study-v1":
        raise ValueError("unsupported ensemble DTCO study schema")
    if study.get("source_result_hash") != feasibility_hash:
        raise ValueError("K5 study source differs from retained K4c result")
    if study.get("point_hash") != canonical_hash(study.get("design_point")):
        raise ValueError("K5 design-point identity differs")

    eligibility, eligibility_hash = _wrapped_section(
        payload["eligibility"],
        "eligibility",
    )
    if eligibility.get("schema_version") != "ensemble-eligibility-result-v1":
        raise ValueError("unsupported ensemble eligibility schema")
    if eligibility.get("study_hash") != study_hash:
        raise ValueError("K5b source study differs from retained K5 study")

    evaluations = eligibility.get("evaluations")
    if type(evaluations) is not list:
        raise ValueError("eligibility evaluations must be a list")
    statuses = []
    for evaluation in evaluations:
        if type(evaluation) is not dict:
            raise ValueError("eligibility evaluation must be an object")
        status = evaluation.get("status")
        if status not in ("satisfied", "violated", "unevaluable"):
            raise ValueError("invalid eligibility constraint status")
        statuses.append(status)

    if "unevaluable" in statuses:
        expected_status = "unevaluable"
    elif "violated" in statuses:
        expected_status = "ineligible"
    else:
        expected_status = "eligible"
    if eligibility.get("status") != expected_status:
        raise ValueError("eligibility status differs from evaluations")

    return canonical_hash(payload)


def _check_pareto_payload(
    wrapped: Any,
    eligibility_hashes: tuple[str, ...],
    study_hashes: tuple[str, ...],
    point_indices: tuple[int, ...],
) -> None:
    if wrapped is None:
        return

    pareto, pareto_hash = _wrapped_section(
        wrapped,
        "Pareto",
    )
    if pareto.get("schema_version") != "ensemble-pareto-result-v1":
        raise ValueError("unsupported ensemble Pareto schema")
    if tuple(pareto.get("source_result_hashes", ())) != eligibility_hashes:
        raise ValueError("Pareto source eligibility order differs")

    source_results = pareto.get("source_results")
    points = pareto.get("points")
    fronts = pareto.get("fronts")
    if (
        type(source_results) is not list
        or len(source_results) != len(eligibility_hashes)
        or type(points) is not list
        or len(points) != len(eligibility_hashes)
        or type(fronts) is not list
    ):
        raise ValueError("Pareto retained source structure differs")

    for position, (
        source,
        expected_hash,
        expected_study_hash,
        expected_point_index,
        point,
    ) in enumerate(
        zip(
            source_results,
            eligibility_hashes,
            study_hashes,
            point_indices,
            points,
        )
    ):
        if canonical_hash(source) != expected_hash:
            raise ValueError("Pareto retained eligibility result hash differs")
        if (
            type(point) is not dict
            or point.get("source_eligibility_result_hash") != expected_hash
            or point.get("study_hash") != expected_study_hash
            or point.get("index") != expected_point_index
        ):
            raise ValueError(
                f"Pareto point source/order differs at position {position}"
            )

    definition = {
        "schema_version": "ensemble-pareto-analysis-v1",
        "name": pareto.get("name"),
        "objectives": pareto.get("objectives"),
        "dominance": "exact-no-worse-all-strictly-better-one",
        "eligibility": "k5b-eligible-and-all-objectives-defined",
        "ties": "retain-all",
        "ordering": "source-study-order",
        "rank_base": 0,
    }
    if pareto.get("definition_hash") != canonical_hash(definition):
        raise ValueError("Pareto definition identity differs")
    if pareto.get("analysis_hash") != canonical_hash(
        {
            "schema_version": "ensemble-pareto-run-v1",
            "definition_hash": pareto.get("definition_hash"),
            "source_result_hashes": list(eligibility_hashes),
        }
    ):
        raise ValueError("Pareto analysis identity differs")

    ranked = {
        index
        for index, point in enumerate(points)
        if point.get("rank") is not None
    }
    seen: set[int] = set()
    for rank, front in enumerate(fronts):
        if (
            type(front) is not list
            or not front
            or front != sorted(front)
        ):
            raise ValueError("Pareto fronts must be nonempty and source ordered")
        for index in front:
            if (
                type(index) is not int
                or index not in ranked
                or index in seen
                or points[index].get("rank") != rank
            ):
                raise ValueError("Pareto front membership/rank differs")
            seen.add(index)

    if seen != ranked:
        raise ValueError("Pareto fronts do not partition ranked studies")

    expected_indices = fronts[0] if fronts else []
    if pareto.get("pareto_indices") != expected_indices:
        raise ValueError("Pareto index summary differs")
    if pareto.get("ranked_count") != len(ranked):
        raise ValueError("Pareto ranked count differs")
    if pareto.get("excluded_count") != len(points) - len(ranked):
        raise ValueError("Pareto excluded count differs")
    if wrapped["result_hash"] != pareto_hash:
        raise ValueError("Pareto result hash differs")


def _check_report_payload(payload: Any) -> None:
    if (
        type(payload) is not dict
        or set(payload)
        != {
            "schema_version",
            "name",
            "ncmemsim_version",
            "metadata",
            "studies",
            "pareto",
        }
        or payload.get("schema_version") != "ensemble-report-v1"
    ):
        raise ValueError("unsupported or incomplete ensemble report schema")

    _label(payload.get("name"), "report name")
    _label(payload.get("ncmemsim_version"), "NCMemSim version")
    if type(payload.get("metadata")) is not dict:
        raise ValueError("report metadata must be a JSON object")

    studies = payload.get("studies")
    if type(studies) is not list or not studies:
        raise ValueError("ensemble report requires at least one study")

    eligibility_hashes = []
    study_hashes = []
    point_indices = []
    for wrapped in studies:
        if (
            type(wrapped) is not dict
            or set(wrapped) != {"result_hash", "data"}
            or type(wrapped.get("data")) is not dict
        ):
            raise ValueError("report study wrapper structure differs")
        expected_hash = _check_report_study_payload(wrapped["data"])
        if wrapped["result_hash"] != expected_hash:
            raise ValueError("report study result hash differs")
        eligibility_hashes.append(
            wrapped["data"]["eligibility"]["result_hash"]
        )
        study_hashes.append(
            wrapped["data"]["study"]["study_hash"]
        )
        point_indices.append(
            wrapped["data"]["study"]["data"]["design_point"]["index"]
        )

    _check_pareto_payload(
        payload["pareto"],
        tuple(eligibility_hashes),
        tuple(study_hashes),
        tuple(point_indices),
    )


@dataclass(frozen=True)
class EnsembleReport:
    """Canonical immutable K6a report snapshot."""

    payload_json: str

    def __post_init__(self) -> None:
        payload = json.loads(self.payload_json)
        _check_report_payload(payload)
        object.__setattr__(
            self,
            "payload_json",
            _json_snapshot(payload),
        )

    @property
    def report_hash(self) -> str:
        return canonical_hash(
            json.loads(self.payload_json)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **json.loads(self.payload_json),
            "report_hash": self.report_hash,
        }

    def to_json(self) -> str:
        return _json_snapshot(self.to_dict())

    @classmethod
    def from_json(cls, value: str) -> "EnsembleReport":
        def unique_keys(pairs):
            result = {}
            for key, item in pairs:
                if key in result:
                    raise ValueError(
                        f"duplicate JSON key: {key!r}"
                    )
                result[key] = item
            return result

        manifest = json.loads(
            value,
            object_pairs_hook=unique_keys,
        )
        if type(manifest) is not dict:
            raise ValueError("ensemble report manifest must be an object")

        expected = manifest.pop("report_hash", None)
        if expected != canonical_hash(manifest):
            raise ValueError("report hash differs")

        return cls(_json_snapshot(manifest))


def build_ensemble_report(
    studies: Iterable[EnsembleReportStudy],
    *,
    name: str = "Phase K ensemble report",
    pareto: EnsembleParetoAnalysisResult | None = None,
    metadata: dict[str, Any] | None = None,
) -> EnsembleReport:
    """Build an immutable integrity-linked K6a report snapshot."""

    _label(name, "report name")
    if isinstance(studies, (str, bytes)):
        raise TypeError(
            "studies must be a sequence of EnsembleReportStudy instances"
        )
    studies = tuple(studies)
    if not studies:
        raise ValueError("ensemble report requires at least one study")
    if any(
        not isinstance(study, EnsembleReportStudy)
        for study in studies
    ):
        raise TypeError(
            "studies must contain EnsembleReportStudy instances"
        )

    if metadata is not None and type(metadata) is not dict:
        raise TypeError("metadata must be a JSON object")

    eligibility_hashes = tuple(
        study.eligibility.result_hash
        for study in studies
    )

    pareto_section = None
    if pareto is not None:
        if not isinstance(pareto, EnsembleParetoAnalysisResult):
            raise TypeError(
                "pareto must be an EnsembleParetoAnalysisResult"
            )
        if tuple(
            source.result_hash
            for source in pareto.source_results
        ) != eligibility_hashes:
            raise ValueError(
                "Pareto source eligibility order differs from report studies"
            )
        pareto_section = {
            "result_hash": pareto.result_hash,
            "data": pareto.to_dict(),
        }

    payload = {
        "schema_version": "ensemble-report-v1",
        "name": name,
        "ncmemsim_version": __version__,
        "metadata": {} if metadata is None else metadata,
        "studies": [
            {
                "result_hash": study.result_hash,
                "data": study.to_dict(),
            }
            for study in studies
        ],
        "pareto": pareto_section,
    }

    return EnsembleReport(_json_snapshot(payload))


__all__ = [
    "EnsembleReport",
    "EnsembleReportStudy",
    "build_ensemble_report",
]
