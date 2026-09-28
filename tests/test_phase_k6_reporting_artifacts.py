from __future__ import annotations

import csv
import importlib.util
from io import StringIO
import json
from pathlib import Path

import pytest

from ncmemsim.ensemble.reporting import (
    EnsembleReport,
    build_ensemble_report,
    write_ensemble_report,
)


def _load_snapshot_helpers():
    path = (
        Path(__file__).resolve().parent
        / "test_phase_k6_reporting_snapshot.py"
    )
    spec = importlib.util.spec_from_file_location(
        "phase_k6_reporting_snapshot_helpers",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Phase K6a-2 test helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_K6A2 = _load_snapshot_helpers()


def report(*, with_pareto=False):
    source = _K6A2.studies()
    return build_ensemble_report(
        source,
        name="K6a artifact test",
        pareto=_K6A2.pareto_for(source) if with_pareto else None,
        metadata={"purpose": "artifact-test"},
    )


def rows(text):
    return list(csv.DictReader(StringIO(text)))


def test_samples_csv_retains_every_attempted_realization():
    result = report()
    data = rows(result.samples_csv())

    assert len(data) == 6
    assert [row["study_index"] for row in data] == [
        "0", "0", "0", "1", "1", "1"
    ]
    assert [row["sample_index"] for row in data] == [
        "0", "1", "2", "0", "1", "2"
    ]
    assert all(row["execution_status"] == "success" for row in data)
    assert [row["metric_status"] for row in data[:3]] == [
        "feasible", "infeasible", "infeasible"
    ]
    assert all(json.loads(row["assignments_json"]) for row in data)
    assert all(json.loads(row["output_json"]) is not None for row in data)
    assert all(json.loads(row["metrics_json"]) for row in data)


def test_statistics_csv_preserves_units_denominators_and_membership():
    data = rows(report().statistics_csv())

    assert len(data) == 4
    assert {row["unit"] for row in data} == {"V", "1"}
    assert all(row["denominator"] == "3" for row in data)
    assert all(
        json.loads(row["sample_indices_json"]) == [0, 1, 2]
        for row in data
    )
    assert all(
        len(json.loads(row["realization_ids_json"])) == 3
        for row in data
    )
    assert all(row["mean"] != "null" for row in data)
    assert all(row["median"] != "null" for row in data)


def test_feasibility_csv_preserves_explicit_fraction_denominators():
    data = rows(report().feasibility_csv())

    assert len(data) == 2
    for row in data:
        assert row["attempted"] == "3"
        assert row["assessed"] == "3"
        assert row["feasible"] == "1"
        assert row["infeasible"] == "2"
        assert row["failed"] == "0"

        simulated = json.loads(row["simulated_pass_fraction_json"])
        conditional = json.loads(
            row["ensemble_feasibility_fraction_json"]
        )
        failure = json.loads(row["failure_fraction_json"])

        assert simulated == {
            "denominator": 3,
            "numerator": 1,
            "value": 1 / 3,
        }
        assert conditional == {
            "denominator": 3,
            "numerator": 1,
            "value": 1 / 3,
        }
        assert failure == {
            "denominator": 3,
            "numerator": 0,
            "value": 0.0,
        }
        assert len(json.loads(row["nominal_references_json"])) == 2
        assert len(json.loads(row["nominal_comparisons_json"])) == 2


def test_eligibility_csv_keeps_design_identity_assignments_and_status():
    data = rows(report().eligibility_csv())

    assert len(data) == 2
    assert [row["design_point_index"] for row in data] == ["0", "1"]
    assert all(len(row["design_point_hash"]) == 64 for row in data)
    assert all(len(row["study_hash"]) == 64 for row in data)
    assert all(row["eligibility_status"] == "eligible" for row in data)
    assert [
        json.loads(row["assignments_json"])
        for row in data
    ] == [
        [{"name": "x", "value": 1.0}],
        [{"name": "x", "value": 2.0}],
    ]
    assert all(
        json.loads(row["constraint_evaluations_json"]) == []
        for row in data
    )


def test_pareto_csv_is_header_only_when_section_is_absent():
    text = report().pareto_csv()

    assert rows(text) == []
    assert text.startswith(
        "study_index,design_point_index,study_hash,"
        "design_point_hash,eligibility_status,pareto_rank,"
        "objectives_json,exclusion_reason\n"
    )


def test_pareto_csv_retains_every_study_rank_objectives_and_exclusions():
    data = rows(report(with_pareto=True).pareto_csv())

    assert len(data) == 2
    assert [row["design_point_index"] for row in data] == ["0", "1"]
    assert all(row["eligibility_status"] == "eligible" for row in data)
    assert all(row["pareto_rank"] == "0" for row in data)
    assert all(
        json.loads(row["objectives_json"])["mean_response"] == 2.0
        for row in data
    )
    assert all(row["exclusion_reason"] == "" for row in data)


def test_markdown_contains_identity_counts_and_interpretation_limits():
    result = report(with_pareto=True)
    text = result.to_markdown()

    assert f"Report hash: {result.report_hash}" in text
    assert "## Study summary" in text
    assert "## Pareto analysis" in text
    assert "## Interpretation limits" in text
    assert "not manufacturing yield" in text
    assert "Failed realizations remain explicit" in text
    assert "Derived plot files" in text
    assert "manifest.json" in text


def test_writer_emits_exact_seven_file_bundle_and_roundtrips(tmp_path):
    result = report(with_pareto=True)
    paths = write_ensemble_report(
        result,
        tmp_path / "bundle",
    )

    assert tuple(path.name for path in paths) == (
        "manifest.json",
        "samples.csv",
        "statistics.csv",
        "feasibility.csv",
        "eligibility.csv",
        "pareto.csv",
        "report.md",
    )
    assert all(path.is_absolute() for path in paths)

    expected = (
        result.to_json() + "\n",
        result.samples_csv(),
        result.statistics_csv(),
        result.feasibility_csv(),
        result.eligibility_csv(),
        result.pareto_csv(),
        result.to_markdown(),
    )
    assert [
        path.read_text(encoding="utf-8")
        for path in paths
    ] == list(expected)

    restored = EnsembleReport.from_json(
        paths[0].read_text(encoding="utf-8")
    )
    assert restored.report_hash == result.report_hash


@pytest.mark.parametrize(
    "existing",
    (
        "manifest.json",
        "samples.csv",
        "statistics.csv",
        "feasibility.csv",
        "eligibility.csv",
        "pareto.csv",
        "report.md",
    ),
)
def test_writer_refuses_any_existing_target_before_writing(
    tmp_path,
    existing,
):
    target = tmp_path / "bundle"
    target.mkdir()
    (target / existing).write_text(
        "keep",
        encoding="utf-8",
    )

    with pytest.raises(FileExistsError):
        write_ensemble_report(
            report(),
            target,
        )

    assert sorted(
        path.name
        for path in target.iterdir()
    ) == [existing]
    assert (target / existing).read_text(
        encoding="utf-8"
    ) == "keep"


def test_writer_preserves_unrelated_files(tmp_path):
    target = tmp_path / "bundle"
    target.mkdir()
    unrelated = target / "notes.txt"
    unrelated.write_text(
        "keep",
        encoding="utf-8",
    )

    paths = write_ensemble_report(
        report(),
        target,
    )

    assert unrelated.read_text(encoding="utf-8") == "keep"
    assert len(paths) == 7


def test_writer_rejects_wrong_report_type(tmp_path):
    with pytest.raises(TypeError, match="EnsembleReport"):
        write_ensemble_report(
            object(),
            tmp_path,
        )
