from __future__ import annotations

import csv
from io import StringIO
import json

import pytest

from examples.phase_k6b_active_fraction_variability import (
    ACTIVE_FRACTION_STANDARD_DEVIATION,
    NOMINAL_ACTIVE_FRACTION,
    REFERENCE_SAMPLE_COUNT,
    REFERENCE_SEED,
    build_reference_report,
)
from ncmemsim.ensemble import (
    EnsembleReport,
    write_ensemble_report,
)


@pytest.fixture(scope="module")
def report():
    return build_reference_report()


def test_reference_is_repeatable_and_uses_real_solver(report):
    repeated = build_reference_report()

    assert report.to_json() == repeated.to_json()
    assert report.report_hash == repeated.report_hash

    payload = report.to_dict()
    assert len(payload["studies"]) == 1

    study = payload["studies"][0]["data"]
    execution = study["execution"]["data"]
    assert execution["success_count"] == REFERENCE_SAMPLE_COUNT
    assert execution["failure_count"] == 0

    outputs = [
        point["output"]
        for point in execution["points"]
    ]
    assert all(
        output["observable"]["name"] == "delta_vfb"
        and output["observable"]["unit"] == "V"
        and isinstance(output["observable"]["value"], float)
        and "mean_occupation" in output
        and "shift_magnitude_V" in output
        and "electrically_active_fraction" in output
        and output["shift_magnitude_V"] == abs(output["observable"]["value"])
        for output in outputs
    )


def test_reference_manifest_is_fixed_and_within_physical_domain(report):
    payload = report.to_dict()
    study = payload["studies"][0]["data"]
    manifest = study["execution"]["data"]["manifest"]

    assert (
        manifest["sampling_spec"]["rng"]["seed"]
        == REFERENCE_SEED
    )
    assert len(manifest["samples"]) == REFERENCE_SAMPLE_COUNT

    values = [
        sample["values"][0]
        for sample in manifest["samples"]
    ]
    assert all(0.0 <= value <= 1.0 for value in values)
    assert len(set(values)) == len(values)


def test_reference_statistics_feasibility_and_nominal_comparison(report):
    payload = report.to_dict()
    study = payload["studies"][0]["data"]

    statistics = study["population_statistics"]["data"]
    assert statistics["counts"] == {
        "attempted": REFERENCE_SAMPLE_COUNT,
        "assessed": REFERENCE_SAMPLE_COUNT,
        "feasible": REFERENCE_SAMPLE_COUNT,
        "infeasible": 0,
        "failed": 0,
    }
    assert (
        statistics["coverage_fraction"]["value"]
        == 1.0
    )

    feasibility = study["feasibility"]["data"]
    assert (
        feasibility["simulated_pass_fraction"]["value"]
        == 1.0
    )
    assert (
        feasibility["ensemble_feasibility_fraction"]["value"]
        == 1.0
    )
    assert (
        feasibility["failure_fraction"]["value"]
        == 0.0
    )

    refs = {
        item["metric_name"]: item
        for item in feasibility["nominal_references"]
    }
    assert (
        refs["active_fraction"]["nominal_value"]
        == NOMINAL_ACTIVE_FRACTION
    )
    assert refs["shift_magnitude"]["unit"] == "V"
    assert refs["occupation"]["unit"] == "1"


def test_reference_metadata_states_interpretation_limits(report):
    metadata = report.to_dict()["metadata"]

    assert metadata["seed"] == REFERENCE_SEED
    assert metadata["sample_count"] == REFERENCE_SAMPLE_COUNT
    assert metadata["nominal_value"] == NOMINAL_ACTIVE_FRACTION
    assert (
        metadata["distribution"]["standard_deviation"]
        == ACTIVE_FRACTION_STANDARD_DEVIATION
    )
    assert metadata["physical_domain"] == {
        "lower": 0.0,
        "upper": 1.0,
        "lower_inclusive": True,
        "upper_inclusive": True,
    }
    assert "not TAT trap density" in metadata["interpretation"]
    assert "not manufacturing yield" in metadata["interpretation"]
    assert "MODEL" in metadata["tat_limitation"]


def test_reference_csvs_retain_samples_statistics_and_identity(report):
    samples = list(
        csv.DictReader(
            StringIO(report.samples_csv())
        )
    )
    assert len(samples) == REFERENCE_SAMPLE_COUNT
    assert all(
        row["execution_status"] == "success"
        for row in samples
    )
    assert all(
        row["metric_status"] == "feasible"
        for row in samples
    )

    metrics = [
        json.loads(row["metrics_json"])
        for row in samples
    ]
    assert all(
        "active_fraction" in item
        and "shift_magnitude" in item
        and "occupation" in item
        for item in metrics
    )

    eligibility = list(
        csv.DictReader(
            StringIO(report.eligibility_csv())
        )
    )
    assert len(eligibility) == 1
    assert eligibility[0]["eligibility_status"] == "eligible"


def test_reference_report_roundtrips_and_exports(report, tmp_path):
    restored = EnsembleReport.from_json(
        report.to_json()
    )
    assert restored.report_hash == report.report_hash

    paths = write_ensemble_report(
        report,
        tmp_path / "k6b-active-fraction",
    )
    assert {path.name for path in paths} == {
        "manifest.json",
        "samples.csv",
        "statistics.csv",
        "feasibility.csv",
        "eligibility.csv",
        "pareto.csv",
        "report.md",
    }


@pytest.mark.parametrize(
    "kwargs",
    (
        {"sample_count": 0},
        {"sample_count": True},
        {"seed": -1},
        {"seed": True},
    ),
)
def test_reference_rejects_invalid_sampling_inputs(kwargs):
    with pytest.raises(ValueError):
        build_reference_report(**kwargs)
