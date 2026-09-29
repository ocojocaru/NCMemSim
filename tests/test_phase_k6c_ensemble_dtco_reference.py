"""Tests for Phase K6c design, paired manifests and real K3 execution."""

import math

import pytest

from examples.phase_k6c_ensemble_dtco_reference import (
    NOMINAL_PROGRAM_VOLTAGE_V,
    NOMINAL_TUNNEL_THICKNESS_NM,
    PROGRAM_VOLTAGE_VALUES_V,
    REFERENCE_SAMPLE_COUNT,
    TUNNEL_THICKNESS_VALUES_NM,
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



def test_k6c_main_runs_complete_k3_reference(monkeypatch, capsys):
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
    assert "success: 54" in output
    assert "failed: 0" in output
