# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Integrity-checked MODEL population/DTCO reports and deterministic bundles."""
from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
from typing import Any

from ..hashing import canonical_hash
from ._serialization import strict_fields
from .model_analysis import ModelPopulationAnalysis
from .model_dtco import ModelDTCOStudy, ModelEligibilityResult, ModelParetoAnalysis
from .model_sampling import _snapshot, _strict_json


def _label(value: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError("report labels must be nonempty text without outer whitespace")
    return value


def _match(data: Any, expected: Any) -> None:
    if _snapshot(data) != _snapshot(expected):
        raise ValueError("MODEL report content or identity mismatch")


@dataclass(frozen=True)
class ModelReportStudy:
    """One named population, optionally with its declared DTCO eligibility."""
    name: str
    population: ModelPopulationAnalysis
    dtco: ModelEligibilityResult | None = None

    def __post_init__(self) -> None:
        _label(self.name)
        if not isinstance(self.population, ModelPopulationAnalysis):
            raise TypeError("population must be ModelPopulationAnalysis")
        if self.dtco is not None:
            if not isinstance(self.dtco, ModelEligibilityResult):
                raise TypeError("dtco must be ModelEligibilityResult or None")
            if self.population.analysis_hash != self.dtco.study.source.analysis_hash:
                raise ValueError("report population/DTCO source mismatch")

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": "model-report-study-v1", "name": self.name,
                "population": self.population.to_dict(),
                "dtco": None if self.dtco is None else {"study": self.dtco.study.to_dict(), "eligibility": self.dtco.to_dict()}}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelReportStudy:
        strict_fields(data, label="MODEL report study", required={"schema_version", "name", "population", "dtco"})
        dtco = None
        if data["dtco"] is not None:
            strict_fields(data["dtco"], label="report DTCO", required={"study", "eligibility"})
            study = ModelDTCOStudy.from_dict(data["dtco"]["study"])
            dtco = ModelEligibilityResult.from_dict(data["dtco"]["eligibility"], study=study)
        result = cls(data["name"], ModelPopulationAnalysis.from_dict(data["population"]), dtco)
        _match(data, result.to_dict())
        return result


@dataclass(frozen=True)
class ModelReport:
    """Authoritative stored evidence; all summaries rebuild without simulation."""
    name: str
    studies: tuple[ModelReportStudy, ...]
    pareto: ModelParetoAnalysis | None = None
    limitations: tuple[str, ...] = ()
    evidence_json: str = "{}"

    def __post_init__(self) -> None:
        _label(self.name)
        evidence = _strict_json(self.evidence_json)
        if type(evidence) is not dict:
            raise TypeError("report evidence must be a JSON object")
        object.__setattr__(self, "studies", tuple(self.studies))
        object.__setattr__(self, "limitations", tuple(self.limitations))
        if not self.studies or any(not isinstance(s, ModelReportStudy) for s in self.studies):
            raise ValueError("report requires a nonempty ModelReportStudy sequence")
        if len({s.name for s in self.studies}) != len(self.studies):
            raise ValueError("duplicate report study names")
        for limitation in self.limitations:
            _label(limitation)
        if self.pareto is not None:
            if not isinstance(self.pareto, ModelParetoAnalysis):
                raise TypeError("pareto must be ModelParetoAnalysis or None")
            expected = [s.dtco.to_dict() for s in self.studies if s.dtco is not None]
            actual = [s.to_dict() for s in self.pareto.sources]
            _match(actual, expected)
            # Include full source identity in the linkage, not only eligibility hashes.
            _match([s.study.to_dict() for s in self.pareto.sources],
                   [s.dtco.study.to_dict() for s in self.studies if s.dtco is not None])

    def to_dict(self) -> dict[str, Any]:
        payload = {"schema_version": "model-report-v1", "name": self.name,
                   "studies": [s.to_dict() for s in self.studies],
                   "pareto": None if self.pareto is None else self.pareto.to_dict(),
                   "limitations": list(self.limitations), "evidence": _strict_json(self.evidence_json)}
        return {**payload, "report_hash": canonical_hash(payload)}

    @property
    def report_hash(self) -> str:
        return self.to_dict()["report_hash"]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelReport:
        strict_fields(data, label="MODEL report", required={"schema_version", "name", "studies", "pareto", "limitations", "evidence", "report_hash"})
        if type(data["studies"]) is not list or type(data["limitations"]) is not list:
            raise TypeError("report studies/limitations must be lists")
        result = cls(data["name"], tuple(ModelReportStudy.from_dict(s) for s in data["studies"]),
                     None if data["pareto"] is None else ModelParetoAnalysis.from_dict(data["pareto"]), tuple(data["limitations"]), _snapshot(data["evidence"]))
        _match(data, result.to_dict())
        return result

    def to_json(self) -> str:
        return _snapshot(self.to_dict())

    @classmethod
    def from_json(cls, text: str) -> ModelReport:
        return cls.from_dict(_strict_json(text))


def build_model_report(name: str, studies, *, pareto: ModelParetoAnalysis | None = None, limitations=(), evidence=None) -> ModelReport:
    """Build from completed stored populations; never resample or rerun physics."""
    return ModelReport(name, tuple(studies), pareto, tuple(limitations), _snapshot({} if evidence is None else evidence))


def _csv(headers, rows) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _cell(value) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _render(report: ModelReport) -> dict[str, bytes]:
    data = report.to_dict()
    attempts, summaries, designs = [], [], []
    markdown = ["# " + _cell(report.name), "", "Report hash: `" + data["report_hash"] + "`", "",
        "Descriptive simulation evidence. Fractions are not measured manufacturing yield.", "",
        "| Study | Attempted | Assessed | Feasible | Infeasible | Failed |", "| --- | --- | --- | --- | --- | --- |"]
    for study in report.studies:
        population = study.population.to_dict()
        counts = population["counts"]
        markdown.append("| " + " | ".join([_cell(study.name)] + [str(counts[k]) for k in
            ("attempted_count", "assessed_count", "feasible_count", "infeasible_count", "failed_count")]) + " |")
        original = study.population.source.points
        for point, execution in zip(population["points"], original, strict=True):
            raw = execution.to_dict()
            attempts.append([study.name, population["analysis_hash"], point["sample_index"], point["sample_id"],
                point["sample_hash"], point["realization_id"], point["status"], raw["context_hash"],
                _snapshot(raw["assignments"]), _snapshot(point["metric_values"]), _snapshot(point["constraints"]),
                point["failure_stage"], point["failure_category"], point["error_type"], point["error_message"]])
        for summary in population["statistics"]:
            summaries.append([study.name, population["analysis_hash"], summary["metric_name"], summary["unit"],
                summary["denominator"], summary["mean"], summary["standard_deviation"], summary["variance"], summary["median"],
                summary["minimum"], summary["maximum"], _snapshot(summary["quantiles"]),
                _snapshot(summary["sample_indices"]), _snapshot(summary["realization_ids"]),
                _snapshot(population["fractions"]), _snapshot(population["failure_stage_counts"]),
                _snapshot(population["nominal_comparisons"])])
    if report.pareto is not None:
        markdown += ["", "## DTCO designs", "", "| Index | Eligibility | Exclusion | Rank |", "| --- | --- | --- | --- |"]
        for point in report.pareto.to_dict()["points"]:
            index = point["source_index"]
            source = report.pareto.sources[index]
            designs.append([index, point["point_hash"], point["study_hash"], source.study.design_point.experiment_hash,
                source.study.design_point.index, _snapshot(source.study.design_point.to_dict()["assignments"]),
                point["eligibility"]["status"], point["exclusion_reason"], point["rank"], _snapshot(point["objective_values"])])
            markdown.append("| " + " | ".join(_cell("" if x is None else x) for x in
                (index, point["eligibility"]["status"], point["exclusion_reason"], point["rank"])) + " |")
    markdown += ["", "## Interpretation limits", ""] + ["- " + _cell(item) for item in report.limitations]
    markdown += ["", "The JSON is authoritative and retains manifests, contexts, definitions, runtime, failures and all source identities.",
        "CSV tables and this summary are deterministic projections of that JSON.", ""]
    return {"report.json": (json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+"\n").encode("utf-8"),
        "report.md": "\n".join(markdown).encode("utf-8"),
        "attempts.csv": _csv(["study", "analysis_hash", "sample_index", "sample_id", "sample_hash", "realization_id", "status",
            "context_hash", "assignments_json", "metrics_json", "constraints_json", "failure_stage", "failure_category", "error_type", "error_message"], attempts),
        "statistics.csv": _csv(["study", "analysis_hash", "metric", "unit", "denominator", "mean", "standard_deviation", "variance",
            "median", "minimum", "maximum", "quantiles_json", "sample_indices_json", "realization_ids_json", "fractions_json",
            "failure_stage_counts_json", "nominal_comparisons_json"], summaries),
        "designs.csv": _csv(["source_index", "point_hash", "study_hash", "experiment_hash", "design_index", "assignments_json",
            "eligibility", "exclusion_reason", "rank", "objectives_json"], designs)}


def _bundle_manifest(report: ModelReport, files: dict[str, bytes]) -> dict[str, Any]:
    return {"schema_version": "model-report-bundle-v1", "report_hash": report.report_hash,
            "files": {name: hashlib.sha256(content).hexdigest() for name, content in sorted(files.items())}}


def write_model_report(report: ModelReport, destination: str | Path) -> Path:
    """Export six deterministic files; refuse any existing destination."""
    if not isinstance(report, ModelReport):
        raise TypeError("report must be ModelReport")
    # Validate nested source evidence before creating a destination.
    report = ModelReport.from_dict(report.to_dict())
    files = _render(report)
    files["bundle.json"] = (json.dumps(_bundle_manifest(report, files), indent=2, sort_keys=True)+"\n").encode("utf-8")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    created = []
    try:
        for name, content in files.items():
            path = destination/name
            # Exclusive creation also protects against competing writers.
            with path.open("xb") as handle:
                created.append(path)
                handle.write(content)
    except BaseException:
        for path in created:
            path.unlink()
        destination.rmdir()
        raise
    return destination


def load_model_report_bundle(destination: str | Path) -> ModelReport:
    """Verify every byte and rebuild every projection from authoritative JSON."""
    destination = Path(destination)
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError("bundle must be an ordinary directory")
    expected = {"report.json", "report.md", "attempts.csv", "statistics.csv", "designs.csv", "bundle.json"}
    entries = list(destination.iterdir())
    if {p.name for p in entries} != expected or any(p.is_symlink() or not p.is_file() for p in entries):
        raise ValueError("unexpected, missing or nonregular bundle file")
    manifest = _strict_json((destination/"bundle.json").read_text(encoding="utf-8"))
    strict_fields(manifest, label="MODEL bundle", required={"schema_version", "report_hash", "files"})
    report = ModelReport.from_json((destination/"report.json").read_text(encoding="utf-8"))
    rebuilt = _render(report)
    _match(manifest, _bundle_manifest(report, rebuilt))
    for name, content in rebuilt.items():
        if (destination/name).read_bytes() != content:
            raise ValueError("bundle projection/content mismatch: " + name)
    return report


__all__ = ["ModelReportStudy", "ModelReport", "build_model_report", "write_model_report", "load_model_report_bundle"]
