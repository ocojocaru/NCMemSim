"""Tests for the Phase K6c deterministic design and paired manifests."""

from examples.phase_k6c_ensemble_dtco_reference import (
    NOMINAL_PROGRAM_VOLTAGE_V,
    NOMINAL_TUNNEL_THICKNESS_NM,
    PROGRAM_VOLTAGE_VALUES_V,
    REFERENCE_SAMPLE_COUNT,
    TUNNEL_THICKNESS_VALUES_NM,
    build_reference_design_space,
    build_reference_ensemble_cases,
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
