"""Tests for Phase K6c design, K3 execution and K4 population analysis."""

import math

import pytest

from examples.phase_k6c_ensemble_dtco_reference import (
    NOMINAL_PROGRAM_VOLTAGE_V,
    NOMINAL_TUNNEL_THICKNESS_NM,
    PROGRAM_VOLTAGE_VALUES_V,
    REFERENCE_SAMPLE_COUNT,
    TUNNEL_THICKNESS_VALUES_NM,
    build_reference_analyses,
    build_reference_design_space,
    build_reference_ensemble_cases,
    build_reference_executions,
)


EXPECTED_POINTS = (
    (6.0, 4.0),
    (6.0, 5.0),
    (6.0, 6.0),
    (8.0, 4.0),
    (8.0, 5.0),
    (8.0, 6.0),
    (10.0, 4.0),
    (10.0, 5.0),
    (10.0, 6.0),
)


def test_k6c_design_space_uses_declared_cartesian_order():
    device, protocol, experiment, points = build_reference_design_space()

    assert experiment.design_point_count == 9
    assert len(points) == 9
    assert tuple(point.index for point in points) == tuple(range(9))
    assert all(
        point.experiment_hash == experiment.experiment_hash
        for point in points
    )

    actual = tuple(
        (
            point.assignments["tunnel_thickness_nm"],
            point.assignments["program_voltage_V"],
        )
        for point in points
    )
    assert actual == EXPECTED_POINTS

    assert experiment.variables[0].values == TUNNEL_THICKNESS_VALUES_NM
    assert experiment.variables[1].values == PROGRAM_VOLTAGE_VALUES_V

    assert device.get_layer("tunnel_sio2").thickness_nm == (
        NOMINAL_TUNNEL_THICKNESS_NM
    )
    assert protocol.program_voltage_V == NOMINAL_PROGRAM_VOLTAGE_V


def test_k6c_nominal_design_anchor_occurs_exactly_once():
    _, _, _, points = build_reference_design_space()

    nominal = tuple(
        point
        for point in points
        if (
            point.assignments["tunnel_thickness_nm"]
            == NOMINAL_TUNNEL_THICKNESS_NM
            and point.assignments["program_voltage_V"]
            == NOMINAL_PROGRAM_VOLTAGE_V
        )
    )

    assert len(nominal) == 1
    assert nominal[0].index == 4


def test_k6c_builds_distinct_per_design_manifests():
    cases = build_reference_ensemble_cases()

    assert len(cases) == 9
    assert tuple(case.point.index for case in cases) == tuple(range(9))

    sampling_hashes = {
        case.manifest.sampling_spec.definition_hash
        for case in cases
    }
    manifest_hashes = {
        case.manifest.manifest_hash
        for case in cases
    }

    assert len(sampling_hashes) == 9
    assert len(manifest_hashes) == 9

    for case in cases:
        assert case.manifest.sampling_spec.sample_count == (
            REFERENCE_SAMPLE_COUNT
        )
        assert len(case.manifest.samples) == REFERENCE_SAMPLE_COUNT
        assert tuple(
            sample.sample_index
            for sample in case.manifest.samples
        ) == tuple(range(REFERENCE_SAMPLE_COUNT))


def test_k6c_common_random_numbers_pair_physical_values_by_sample_index():
    cases = build_reference_ensemble_cases()

    reference_values = tuple(
        sample.values
        for sample in cases[0].manifest.samples
    )
    reference_names = tuple(
        sample.variable_names
        for sample in cases[0].manifest.samples
    )

    for case in cases[1:]:
        assert tuple(
            sample.values
            for sample in case.manifest.samples
        ) == reference_values
        assert tuple(
            sample.variable_names
            for sample in case.manifest.samples
        ) == reference_names

    for sample_index in range(REFERENCE_SAMPLE_COUNT):
        sample_ids = {
            case.manifest.samples[sample_index].sample_id
            for case in cases
        }
        assert len(sample_ids) == 9


def test_k6c_manifest_baselines_match_each_applied_design_point():
    cases = build_reference_ensemble_cases()

    for case in cases:
        point = case.point
        applied = case.applied
        ensemble = case.manifest.sampling_spec.ensemble_spec

        assert applied.device.get_layer("tunnel_sio2").thickness_nm == (
            point.assignments["tunnel_thickness_nm"]
        )
        assert applied.operating_protocol.program_voltage_V == (
            point.assignments["program_voltage_V"]
        )

        assert ensemble.matches_device(applied.device)
        assert ensemble.matches_operating(applied.operating_protocol)



@pytest.fixture(scope="module")
def execution_cases():
    return build_reference_executions()


def test_k6c_executes_all_54_realizations_with_real_solver(execution_cases):
    assert len(execution_cases) == 9
    assert sum(
        len(item.execution.points)
        for item in execution_cases
    ) == 9 * REFERENCE_SAMPLE_COUNT
    assert sum(
        item.execution.success_count
        for item in execution_cases
    ) == 9 * REFERENCE_SAMPLE_COUNT
    assert sum(
        item.execution.failure_count
        for item in execution_cases
    ) == 0

    for item in execution_cases:
        case = item.ensemble_case
        execution = item.execution

        assert execution.manifest.manifest_hash == (
            case.manifest.manifest_hash
        )
        assert len(execution.points) == REFERENCE_SAMPLE_COUNT
        assert all(
            point.status == "success"
            for point in execution.points
        )


def test_k6c_real_solver_outputs_preserve_samples_and_design(execution_cases):
    required_fields = {
        "shift_magnitude_V",
        "mean_occupation",
        "nc_diameter_nm",
        "electrically_active_fraction",
        "program_voltage_V",
        "tunnel_thickness_nm",
    }

    for item in execution_cases:
        case = item.ensemble_case
        point = case.point

        for sample, result in zip(
            case.manifest.samples,
            item.execution.points,
            strict=True,
        ):
            output = result.output
            assert output is not None
            assert required_fields <= set(output)

            assert output["nc_diameter_nm"] == sample.values[0]
            assert output["electrically_active_fraction"] == (
                sample.values[1]
            )
            assert output["program_voltage_V"] == (
                point.assignments["program_voltage_V"]
            )
            assert output["tunnel_thickness_nm"] == (
                point.assignments["tunnel_thickness_nm"]
            )

            shift = float(output["shift_magnitude_V"])
            occupation = float(output["mean_occupation"])
            assert math.isfinite(shift)
            assert shift >= 0.0
            assert math.isfinite(occupation)
            assert 0.0 <= occupation <= 1.0


def test_k6c_k3_execution_metadata_identifies_each_design_point(
    execution_cases,
):
    for item in execution_cases:
        case = item.ensemble_case
        execution_definition = __import__("json").loads(
            item.execution.execution_json
        )
        evaluator = execution_definition["evaluator"]

        assert evaluator["id"] == (
            "phase-k6c-ensemble-dtco-program-read-reference-v1"
        )
        parameters = evaluator["parameters"]
        assert parameters["design_point_index"] == case.point.index
        assert parameters["sample_count"] == REFERENCE_SAMPLE_COUNT
        assert parameters["rng_seed"] == 2028
        assert parameters["stochastic_dependence"] == "independent"
        assert parameters["tunnel_thickness_nm"] == (
            case.point.assignments["tunnel_thickness_nm"]
        )
        assert parameters["program_voltage_V"] == (
            case.point.assignments["program_voltage_V"]
        )



@pytest.fixture(scope="module")
def analysis_cases():
    return build_reference_analyses()


def test_k6c_k4_metric_contract_is_complete_and_ordered(analysis_cases):
    assert len(analysis_cases) == 9

    expected_metrics = (
        ("shift_magnitude", "V"),
        ("occupation", "1"),
        ("nc_diameter", "nm"),
        ("active_fraction", "1"),
        ("program_voltage", "V"),
        ("tunnel_thickness", "nm"),
    )
    expected_constraints = (
        "occupation_min",
        "occupation_max",
        "active_fraction_min",
        "active_fraction_max",
    )

    for item in analysis_cases:
        spec = item.metric_analysis.spec
        assert tuple(
            (metric.name, metric.unit)
            for metric in spec.metrics
        ) == expected_metrics
        assert tuple(
            constraint.name
            for constraint in spec.constraints
        ) == expected_constraints


def test_k6c_k4_population_counts_and_feasibility_are_complete(
    analysis_cases,
):
    for item in analysis_cases:
        statistics = item.population_statistics
        feasibility = item.feasibility

        assert statistics.attempted_count == REFERENCE_SAMPLE_COUNT
        assert statistics.assessed_count == REFERENCE_SAMPLE_COUNT
        assert statistics.feasible_count == REFERENCE_SAMPLE_COUNT
        assert statistics.infeasible_count == 0
        assert statistics.failed_count == 0
        assert statistics.coverage_fraction == 1.0

        assert feasibility.attempted_count == REFERENCE_SAMPLE_COUNT
        assert feasibility.assessed_count == REFERENCE_SAMPLE_COUNT
        assert feasibility.feasible_count == REFERENCE_SAMPLE_COUNT
        assert feasibility.infeasible_count == 0
        assert feasibility.failed_count == 0
        assert feasibility.simulated_pass_fraction == 1.0
        assert feasibility.ensemble_feasibility_fraction == 1.0
        assert feasibility.failure_fraction == 0.0


def test_k6c_k4_statistics_include_q05_and_constant_design_metrics(
    analysis_cases,
):
    for item in analysis_cases:
        point = item.execution_case.ensemble_case.point
        summaries = {
            summary.metric_name: summary
            for summary in item.population_statistics.metric_statistics
        }

        assert tuple(summaries) == (
            "shift_magnitude",
            "occupation",
            "nc_diameter",
            "active_fraction",
            "program_voltage",
            "tunnel_thickness",
        )

        shift = summaries["shift_magnitude"]
        assert shift.denominator == REFERENCE_SAMPLE_COUNT
        q05 = dict(shift.quantiles)[0.05]
        assert math.isfinite(q05)
        assert q05 >= 0.0

        assert summaries["program_voltage"].mean == (
            point.assignments["program_voltage_V"]
        )
        assert summaries["tunnel_thickness"].mean == (
            point.assignments["tunnel_thickness_nm"]
        )


def test_k6c_k4_nominal_references_are_point_specific_and_complete(
    analysis_cases,
):
    for item in analysis_cases:
        point = item.execution_case.ensemble_case.point
        refs = {
            reference.metric_name: reference
            for reference in item.feasibility.nominal_references
        }

        assert tuple(refs) == (
            "shift_magnitude",
            "occupation",
            "nc_diameter",
            "active_fraction",
            "program_voltage",
            "tunnel_thickness",
        )
        assert refs["nc_diameter"].nominal_value == 5.0
        assert refs["active_fraction"].nominal_value == 0.22
        assert refs["program_voltage"].nominal_value == (
            point.assignments["program_voltage_V"]
        )
        assert refs["tunnel_thickness"].nominal_value == (
            point.assignments["tunnel_thickness_nm"]
        )


def test_k6c_main_runs_complete_k4_reference(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        ["phase_k6c_ensemble_dtco_reference"],
    )

    from examples.phase_k6c_ensemble_dtco_reference import main

    main()
    output = capsys.readouterr().out

    assert "design_point_count: 9" in output
    assert "sample_count: 6" in output
    assert "seed: 2028" in output
    assert "attempted: 54" in output
    assert "assessed: 54" in output
    assert "feasible: 54" in output
    assert "infeasible: 0" in output
    assert "failed: 0" in output
