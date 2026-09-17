"""Deterministic, integrity-checked DTCO report bundles."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
import json
from pathlib import Path
from typing import Any

from .._version import __version__
from ..hashing import canonical_hash
from .metrics import MetricAnalysisResult, _label
from .pareto import ParetoAnalysisResult
from .sensitivity import SensitivityAnalysisResult
from .sweep import _json_snapshot


def _check_payload(payload):
    if type(payload) is not dict or payload.get("schema_version") != "dtco-report-v1":
        raise ValueError("unsupported DTCO report schema")
    expected_keys = {
        "schema_version", "name", "ncmemsim_version", "metadata",
        "metric_analysis", "pareto", "sensitivity",
    }
    if set(payload) != expected_keys:
        raise ValueError("incomplete or unknown report fields")
    _label(payload.get("name"), "report name")
    _label(payload.get("ncmemsim_version"), "NCMemSim version")
    if type(payload.get("metadata")) is not dict:
        raise ValueError("report metadata must be a JSON object")
    try:
        metrics = payload["metric_analysis"]
        data = metrics["data"]
        if canonical_hash(data) != metrics["result_hash"]:
            raise ValueError("metric analysis hash differs")
        if canonical_hash(data["source_sweep"]) != data["source_result_hash"]:
            raise ValueError("source sweep result hash differs")
        if canonical_hash(data["spec"]) != data["definition_hash"]:
            raise ValueError("metric definition hash differs")
        sweep = data["source_sweep"]
        if data["source_sweep_hash"] != sweep["sweep_hash"]:
            raise ValueError("source sweep identity differs")
        if sweep["experiment_hash"] != canonical_hash(sweep["experiment"]):
            raise ValueError("source experiment hash differs")
        definition = {
            "schema_version": "dtco-sweep-v1", "experiment": sweep["experiment"],
            "evaluation": sweep["evaluation"], "ordering": "declared-last-axis-fastest",
            "execution": "serial-isolated",
        }
        if sweep["sweep_hash"] != canonical_hash(definition):
            raise ValueError("source sweep definition hash differs")
        if data["analysis_hash"] != canonical_hash({
            "schema_version": "dtco-metric-analysis-run-v1",
            "spec": data["spec"], "source_result_hash": data["source_result_hash"],
        }):
            raise ValueError("metric analysis identity differs")
        if len(data["points"]) != len(sweep["points"]):
            raise ValueError("metric analysis must retain every source point")
        for index, (point, source) in enumerate(zip(data["points"], sweep["points"])):
            if (
                source["point_hash"] != canonical_hash(source["point"])
                or source["point"]["experiment_hash"] != sweep["experiment_hash"]
                or source["point"]["index"] != index
                or point["index"] != index or point["point_hash"] != source["point_hash"]
            ):
                raise ValueError("source point identity or order differs")

        for key in ("pareto", "sensitivity"):
            section = payload[key]
            if section is None:
                continue
            compact = section["data"]
            if compact["source_result_hash"] != metrics["result_hash"]:
                raise ValueError(f"{key} source analysis differs")
            if canonical_hash(compact["spec"]) != compact["definition_hash"]:
                raise ValueError(f"{key} definition hash differs")
            schema = "dtco-pareto-run-v1" if key == "pareto" else "dtco-sensitivity-run-v1"
            if compact["analysis_hash"] != canonical_hash({
                "schema_version": schema, "spec": compact["spec"],
                "source_result_hash": metrics["result_hash"],
            }):
                raise ValueError(f"{key} analysis identity differs")
            restored = {**compact, "source_analysis": data}
            if canonical_hash(restored) != section["result_hash"]:
                raise ValueError(f"{key} result hash differs")
    except (KeyError, TypeError) as exc:
        raise ValueError("incomplete DTCO report manifest") from exc


@dataclass(frozen=True)
class DTCOReport:
    """Canonical snapshot; the manifest hash excludes its own hash field."""

    payload_json: str

    def __post_init__(self) -> None:
        payload = json.loads(self.payload_json)
        _check_payload(payload)
        object.__setattr__(self, "payload_json", _json_snapshot(payload))

    @property
    def report_hash(self) -> str:
        return canonical_hash(json.loads(self.payload_json))

    def to_dict(self) -> dict[str, Any]:
        return {**json.loads(self.payload_json), "report_hash": self.report_hash}

    def to_json(self) -> str:
        return _json_snapshot(self.to_dict())

    @classmethod
    def from_json(cls, value: str) -> DTCOReport:
        def unique_keys(pairs):
            result = {}
            for key, item in pairs:
                if key in result:
                    raise ValueError(f"duplicate JSON key: {key!r}")
                result[key] = item
            return result
        manifest = json.loads(value, object_pairs_hook=unique_keys)
        if type(manifest) is not dict:
            raise ValueError("report manifest must be an object")
        expected = manifest.pop("report_hash", None)
        if expected != canonical_hash(manifest):
            raise ValueError("report hash differs")
        return cls(_json_snapshot(manifest))

    def points_csv(self) -> str:
        payload = json.loads(self.payload_json)
        analysis = payload["metric_analysis"]["data"]
        ranks = {} if payload["pareto"] is None else {
            p["index"]: p["rank"] for p in payload["pareto"]["data"]["points"]
        }
        rows = []
        for point, source in zip(analysis["points"], analysis["source_sweep"]["points"]):
            rows.append((
                point["index"], point["point_hash"], point["status"],
                ranks.get(point["index"]),
                _json_snapshot(source["point"]["assignments"]),
                _json_snapshot(point["metrics"]), _json_snapshot(point["constraints"]),
                _json_snapshot(point["failure"]),
            ))
        return _csv((
            "point_index", "point_hash", "status", "pareto_rank",
            "assignments_json", "metrics_json", "constraints_json", "failure_json",
        ), rows)

    def sensitivity_csv(self) -> str:
        payload = json.loads(self.payload_json)
        section = payload["sensitivity"]
        rows = []
        if section is not None:
            data = section["data"]
            units = {(s["axis_name"], s["metric_name"]): s["slope_unit"] for s in data["summaries"]}
            for edge in data["edges"]:
                rows.append((
                    edge["axis_name"], edge["metric_name"], edge["left_index"],
                    edge["right_index"], edge["left_value"], edge["right_value"],
                    edge["status"], edge["slope"], units[edge["axis_name"], edge["metric_name"]],
                    edge["reason"], edge["error_type"],
                ))
        return _csv((
            "axis_name", "metric_name", "left_index", "right_index", "left_value",
            "right_value", "status", "slope", "slope_unit", "reason", "error_type",
        ), rows)

    def to_markdown(self) -> str:
        payload = json.loads(self.payload_json)
        analysis = payload["metric_analysis"]["data"]
        sweep = analysis["source_sweep"]
        lines = [
            f"# {_text(payload['name'])}", "",
            f"Report hash: {self.report_hash}", "",
            f"NCMemSim version: {_text(payload['ncmemsim_version'])}", "",
            f"Experiment hash: {sweep['experiment_hash']}", "",
            f"Sweep result hash: {analysis['source_result_hash']}", "",
            f"Metric analysis hash: {payload['metric_analysis']['result_hash']}", "",
            f"Feasible: {analysis['feasible_count']}; infeasible: "
            f"{analysis['infeasible_count']}; failed: {analysis['failure_count']}.", "",
            "## Metric definitions", "",
        ]
        lines += _table(("Metric", "Path", "Unit", "Direction"), (
            (m["name"], _json_snapshot(m["path"]), m["unit"], m["direction"] or "reporting")
            for m in analysis["spec"]["metrics"]
        ))
        lines += ["", "## Constraints", ""]
        lines += _table(("Constraint", "Metric", "Operator", "Threshold", "Unit"), (
            (c["name"], c["metric_name"], c["operator"], c["threshold"], c["unit"])
            for c in analysis["spec"]["constraints"]
        ))
        ranks = {}
        if payload["pareto"] is not None:
            pareto = payload["pareto"]["data"]
            ranks = {p["index"]: p["rank"] for p in pareto["points"]}
            lines += ["", "## Pareto fronts", "",
                      f"Selected objectives: {_text(_json_snapshot(pareto['spec']['objective_names']))}.", ""]
            lines += _table(("Rank", "Source point indices"), (
                (rank, _json_snapshot(front)) for rank, front in enumerate(pareto["fronts"])
            ))
            lines += ["", "Excluded points retain their source classification. "
                      "Order within a front expresses no preference.", ""]
        lines += ["", "## All points", ""]
        lines += _table(("Index", "Status", "Pareto rank", "Metrics", "Failure"), (
            (p["index"], p["status"], ranks.get(p["index"]), _json_snapshot(p["metrics"]),
             _json_snapshot(p["failure"])) for p in analysis["points"]
        ))
        if payload["sensitivity"] is not None:
            sensitivity = payload["sensitivity"]["data"]
            lines += ["", "## Grid sensitivity", "",
                      f"Eligibility: {_text(sensitivity['spec']['eligibility'])}. "
                      "Equal weights over valid adjacent grid edges; missing neighbors are not bridged.", ""]
            lines += _table((
                "Axis", "Metric", "Slope unit", "Attempted", "Estimated", "Excluded", "Failed",
                "Coverage", "Complete", "Mean signed", "Mean absolute", "Max absolute",
            ), (
                (s["axis_name"], s["metric_name"], s["slope_unit"], s["attempted_count"],
                 s["estimated_count"], s["excluded_count"], s["failure_count"],
                 s["coverage_fraction"], s["complete"], s["mean_slope"],
                 s["mean_absolute_slope"], s["max_absolute_slope"])
                for s in sensitivity["summaries"]
            ))
            lines += ["", "These are sampled secant summaries, not Sobol indices or "
                      "a ranking across differently dimensioned axes.", ""]
        lines += ["", "## Metadata", "", _text(_json_snapshot(payload["metadata"])), "",
                  "Complete assignments, source outputs, units, constraints and failure provenance "
                  "are preserved in manifest.json. CSV numeric payloads retain JSON precision.", ""]
        return "\n".join(lines)


def _text(value):
    if value is None:
        return "—"
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace(
        "<", "&lt;"
    ).replace(">", "&gt;").replace("\r", "").replace("\n", "<br>")



def _table(headers, rows):
    return [
        "| " + " | ".join(_text(v) for v in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(_text(v) for v in row) + " |" for row in rows),
    ]


def _csv(headers, rows):
    stream = StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue()


def build_dtco_report(
    analysis: MetricAnalysisResult, *, name: str = "DTCO report",
    pareto: ParetoAnalysisResult | None = None,
    sensitivity: SensitivityAnalysisResult | None = None,
    metadata: dict[str, Any] | None = None,
) -> DTCOReport:
    if not isinstance(analysis, MetricAnalysisResult):
        raise TypeError("analysis must be a MetricAnalysisResult")
    _label(name, "report name")
    if metadata is not None and type(metadata) is not dict:
        raise TypeError("metadata must be a JSON object")
    sections = {}
    source_hash = analysis.result_hash
    for key, result, expected in (
        ("pareto", pareto, ParetoAnalysisResult),
        ("sensitivity", sensitivity, SensitivityAnalysisResult),
    ):
        if result is None:
            sections[key] = None
            continue
        if not isinstance(result, expected):
            raise TypeError(f"{key} result has the wrong type")
        if result.source_analysis.result_hash != source_hash:
            raise ValueError(f"{key} source analysis differs")
        data = result.to_dict()
        data.pop("source_analysis")
        sections[key] = {"result_hash": result.result_hash, "data": data}
    return DTCOReport(_json_snapshot({
        "schema_version": "dtco-report-v1", "name": name,
        "ncmemsim_version": __version__, "metadata": {} if metadata is None else metadata,
        "metric_analysis": {"result_hash": source_hash, "data": analysis.to_dict()},
        **sections,
    }))


def write_dtco_report(report: DTCOReport, output_dir: str | Path) -> tuple[Path, ...]:
    """Write four UTF-8 artifacts; refuse existing target files before writing."""
    if not isinstance(report, DTCOReport):
        raise TypeError("report must be a DTCOReport")
    contents = (
        ("manifest.json", report.to_json() + "\n"),
        ("points.csv", report.points_csv()),
        ("sensitivity.csv", report.sensitivity_csv()),
        ("report.md", report.to_markdown()),
    )
    directory = Path(output_dir).resolve()
    targets = tuple(directory / name for name, text in contents)
    for target in targets:
        if target.exists():
            raise FileExistsError(f"report target already exists: {target}")
    directory.mkdir(parents=True, exist_ok=True)
    for target, (_, text) in zip(targets, contents):
        with target.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    return targets


__all__ = ["DTCOReport", "build_dtco_report", "write_dtco_report"]
