"""Tests for the Phase K6c deterministic DTCO design-space contract."""

from examples.phase_k6c_ensemble_dtco_reference import (
    NOMINAL_PROGRAM_VOLTAGE_V,
    NOMINAL_TUNNEL_THICKNESS_NM,
    PROGRAM_VOLTAGE_VALUES_V,
    TUNNEL_THICKNESS_VALUES_NM,
    build_reference_design_space,
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
