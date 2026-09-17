from dataclasses import FrozenInstanceError
import csv
from io import StringIO
import json
import math

import pytest

from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (
    BindingScope, ConstraintOperator, DesignVariable, DesignVariableRole,
    DTCOReport, ExperimentSpec, MetricAnalysisSpec, MetricConstraint,
    MetricDefinition, ObjectiveDirection, ParameterBinding, analyze_pareto,
    analyze_sensitivity, analyze_sweep, build_dtco_report, run_cartesian_sweep,
    write_dtco_report,
)
from ncmemsim.hashing import canonical_hash
from examples.phase_g6_dtco_reference import build_reference_report


def analysis(offset=0):
    device = DeviceBuilder.v2(n_fgs=1)
    variable = DesignVariable("x", ParameterBinding(BindingScope.DEVICE, ("temperature_K",)),
                              (300, 325, 350, 375), DesignVariableRole.MODEL, "K")
    experiment = ExperimentSpec.from_device(name="report-source", device=device, variables=(variable,))
    def evaluate(d, p, point):
        if point.index == 3:
            raise RuntimeError('failed | point\nwith "quotes"')
        return {"value": point.assignments["x"] + offset}
    sweep = run_cartesian_sweep(experiment, device, evaluate, evaluation_id="g6-test-v1")
    return analyze_sweep(sweep, MetricAnalysisSpec("report-metrics", (
        MetricDefinition("response", ("value",), "V", ObjectiveDirection.MAXIMIZE),
    ), (MetricConstraint("upper", "response", ConstraintOperator.LE, 325, "V"),)))


def bundle():
    source = analysis()
    return build_dtco_report(source, pareto=analyze_pareto(source),
                             sensitivity=analyze_sensitivity(source), metadata={"purpose": "test"})


def reseal(manifest):
    manifest = dict(manifest)
    manifest.pop("report_hash", None)
    manifest["report_hash"] = canonical_hash(manifest)
    return json.dumps(manifest)


def test_report_roundtrip_hashes_and_compact_component_reconstruction():
    report = bundle()
    reconstructed = DTCOReport.from_json(report.to_json())
    assert reconstructed.to_json() == report.to_json()
    assert reconstructed.report_hash == report.report_hash
    manifest = report.to_dict()
    assert "source_analysis" not in manifest["pareto"]["data"]
    assert "source_analysis" not in manifest["sensitivity"]["data"]
    metrics = manifest["metric_analysis"]["data"]
    for name in ("pareto", "sensitivity"):
        restored = {**manifest[name]["data"], "source_analysis": metrics}
        assert canonical_hash(restored) == manifest[name]["result_hash"]


@pytest.mark.parametrize("components", ["none", "pareto", "sensitivity", "both"])
def test_optional_components(components):
    source = analysis()
    report = build_dtco_report(
        source, pareto=analyze_pareto(source) if components in ("pareto", "both") else None,
        sensitivity=analyze_sensitivity(source) if components in ("sensitivity", "both") else None,
    )
    assert DTCOReport.from_json(report.to_json()).report_hash == report.report_hash
    assert len(list(csv.DictReader(StringIO(report.points_csv())))) == 4
    if components in ("none", "pareto"):
        assert list(csv.DictReader(StringIO(report.sensitivity_csv()))) == []


@pytest.mark.parametrize("component", ["pareto", "sensitivity"])
def test_mismatched_component_sources_rejected(component):
    original, other = analysis(), analysis(offset=1)
    value = analyze_pareto(other) if component == "pareto" else analyze_sensitivity(other)
    with pytest.raises(ValueError, match="source analysis differs"):
        build_dtco_report(original, **{component: value})


def test_csv_retains_all_statuses_exact_payloads_failures_and_ranks():
    report = bundle()
    rows = list(csv.DictReader(StringIO(report.points_csv())))
    assert [row["status"] for row in rows] == ["feasible", "feasible", "infeasible", "failed"]
    assert [row["pareto_rank"] for row in rows] == ["1", "0", "", ""]
    assert json.loads(rows[0]["assignments_json"]) == [{"name": "x", "value": 300}]
    assert json.loads(rows[2]["metrics_json"]) == {"response": 350}
    assert json.loads(rows[3]["failure_json"])["message"] == 'failed | point\nwith "quotes"'
    assert json.loads(rows[3]["metrics_json"]) == {}
    edges = list(csv.DictReader(StringIO(report.sensitivity_csv())))
    assert len(edges) == 3
    assert edges[-1]["status"] == "excluded" and edges[-1]["slope"] == ""
    assert edges[0]["slope_unit"] == "(V)/(K)"


def test_csv_json_payload_preserves_large_integer_precision():
    source = analysis(offset=2**60)
    report = build_dtco_report(source)
    row = next(csv.DictReader(StringIO(report.points_csv())))
    assert json.loads(row["metrics_json"])["response"] == 2**60 + 300


def test_markdown_contains_definitions_classifications_fronts_and_coverage():
    text = bundle().to_markdown()
    assert "## Metric definitions" in text and "maximize" in text
    assert "## Constraints" in text and "&lt;=" in text
    assert "Feasible: 2; infeasible: 1; failed: 1." in text
    assert "## Pareto fronts" in text
    assert "## Grid sensitivity" in text and "Coverage" in text
    assert "failed" in text and "\\|" in text
    assert "Complete assignments" in text


def test_report_and_metadata_are_snapshots_and_identity_sensitive():
    source = analysis()
    original = source.to_json()
    metadata = {"nested": [1]}
    a = build_dtco_report(source, metadata=metadata)
    b = build_dtco_report(source, metadata=metadata)
    assert a.to_json() == b.to_json()
    metadata["nested"].append(2)
    exported = a.to_dict()
    exported["metadata"]["nested"].append(3)
    assert a.to_dict()["metadata"] == {"nested": [1]}
    assert source.to_json() == original
    assert build_dtco_report(source, name="renamed").report_hash != a.report_hash
    with pytest.raises(FrozenInstanceError):
        a.payload_json = "{}"


@pytest.mark.parametrize("field", ["metadata", "metric_analysis", "pareto", "sensitivity"])
def test_stale_outer_hash_rejects_tampering(field):
    manifest = bundle().to_dict()
    manifest[field] = {}
    with pytest.raises(ValueError, match="report hash differs"):
        DTCOReport.from_json(json.dumps(manifest))


@pytest.mark.parametrize("component", ["metric_analysis", "pareto", "sensitivity"])
def test_recomputed_outer_hash_does_not_hide_stale_component_hash(component):
    manifest = bundle().to_dict()
    records = "edges" if component == "sensitivity" else "points"
    manifest[component]["data"][records][0]["status"] = "tampered"
    with pytest.raises(ValueError, match="hash differs"):
        DTCOReport.from_json(reseal(manifest))


def test_recomputed_component_and_outer_hash_cannot_hide_cross_source_reference():
    manifest = bundle().to_dict()
    manifest["sensitivity"]["data"]["source_result_hash"] = "a"*64
    restored = {**manifest["sensitivity"]["data"],
                "source_analysis": manifest["metric_analysis"]["data"]}
    manifest["sensitivity"]["result_hash"] = canonical_hash(restored)
    with pytest.raises(ValueError, match="source analysis differs"):
        DTCOReport.from_json(reseal(manifest))


def test_duplicate_keys_and_unknown_schema_are_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        DTCOReport.from_json('{"schema_version":"one","schema_version":"two"}')
    manifest = bundle().to_dict()
    manifest["schema_version"] = "unknown"
    with pytest.raises(ValueError, match="schema"):
        DTCOReport.from_json(reseal(manifest))
    with pytest.raises(ValueError):
        DTCOReport.from_json("[]")


@pytest.mark.parametrize("kwargs", [
    {"name": ""}, {"name": " spaced"}, {"metadata": []}, {"metadata": {"value": math.nan}},
    {"metadata": {1: "bad"}}, {"pareto": "bad"}, {"sensitivity": "bad"},
])
def test_invalid_report_inputs(kwargs):
    with pytest.raises((ValueError, TypeError)):
        build_dtco_report(analysis(), **kwargs)
    with pytest.raises(TypeError):
        build_dtco_report(None)


def test_export_writes_exact_utf8_contents_and_roundtrip(tmp_path):
    report = bundle()
    paths = write_dtco_report(report, tmp_path / "bundle")
    assert tuple(p.name for p in paths) == ("manifest.json", "points.csv", "sensitivity.csv", "report.md")
    assert all(p.is_absolute() for p in paths)
    expected = (report.to_json() + "\n", report.points_csv(), report.sensitivity_csv(), report.to_markdown())
    assert [p.read_text(encoding="utf-8") for p in paths] == list(expected)
    assert DTCOReport.from_json(paths[0].read_text(encoding="utf-8")).report_hash == report.report_hash


@pytest.mark.parametrize("existing", ["manifest.json", "points.csv", "sensitivity.csv", "report.md"])
def test_existing_target_refused_before_any_export_write(tmp_path, existing):
    (tmp_path / existing).write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_dtco_report(bundle(), tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == [existing]
    assert (tmp_path / existing).read_text() == "keep"


def test_existing_unrelated_files_are_preserved(tmp_path):
    (tmp_path / "unrelated.txt").write_text("keep", encoding="utf-8")
    write_dtco_report(bundle(), tmp_path)
    assert (tmp_path / "unrelated.txt").read_text() == "keep"
    with pytest.raises(TypeError):
        write_dtco_report("bad", tmp_path)


@pytest.mark.parametrize("invalid", [False, True])
def test_reference_workflow_is_repeatable_and_exports_real_solver_results(tmp_path, invalid):
    a = build_reference_report(include_invalid_point=invalid)
    b = build_reference_report(include_invalid_point=invalid)
    assert a.report_hash == b.report_hash
    manifest = a.to_dict()
    data = manifest["metric_analysis"]["data"]
    assert data["feasible_count"] == 4
    assert data["failure_count"] == (2 if invalid else 0)
    assert manifest["pareto"] is not None and manifest["sensitivity"] is not None
    parameters = data["source_sweep"]["evaluation"]["parameters"]
    assert parameters["initial_state"] == "empty_for_candidate"
    assert "simulation_config" in parameters and "numpy_version" in parameters
    write_dtco_report(a, tmp_path / "reference")
    if invalid:
        assert any(s["coverage_fraction"] < 1 for s in manifest["sensitivity"]["data"]["summaries"])


@pytest.mark.parametrize("field", ["source_sweep_hash", "analysis_hash", "experiment_hash", "point_hash"])
def test_resealed_report_rejects_inconsistent_nested_identities(field):
    manifest = build_dtco_report(analysis()).to_dict()
    data = manifest["metric_analysis"]["data"]
    if field in ("source_sweep_hash", "analysis_hash"):
        data[field] = "a"*64
    elif field == "experiment_hash":
        data["source_sweep"]["experiment_hash"] = "a"*64
    else:
        data["source_sweep"]["points"][0]["point_hash"] = "a"*64
    data["source_result_hash"] = canonical_hash(data["source_sweep"])
    manifest["metric_analysis"]["result_hash"] = canonical_hash(data)
    with pytest.raises(ValueError):
        DTCOReport.from_json(reseal(manifest))
