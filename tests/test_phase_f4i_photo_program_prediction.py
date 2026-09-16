from __future__ import annotations

import numpy as np
import pytest

from ncmemsim import (
    DeviceBuilder,
    DeviceState,
    PhysicsModel,
    SimulationConfig,
    Simulator,
    make_gesn,
)
from ncmemsim.optics import LightSource
from ncmemsim.photo import (
    PhotoTransitionConfig,
    PhotoTransitionWeights,
)
from ncmemsim.photo_program_fit import (
    ElectroOpticalProgramTimeFitProtocol,
    ElectroOpticalProgramTimePrediction,
    predict_electro_optical_delta_vfb_vs_programming_time,
)


PROGRAM_VOLTAGE_V = 2.0
READ_VOLTAGE_V = 0.0
INTERNAL_DT_S = 1.0e-5
POWER_DENSITY_W_M2 = 1000.0
WAVELENGTH_NM = 1550.0
PROGRAMMING_TIMES_S = np.asarray(
    [1.0e-4, 3.0e-4, 1.0e-3],
    dtype=float,
)


def _simulator() -> Simulator:
    device = DeviceBuilder.v1(
        n_fgs=1,
        nc_material=[make_gesn(0.08)],
        nc_diameter_nm=[5.0],
        active_fraction=[1.0],
        fg_thickness_nm=[15.0],
    )
    device.floating_gates()[0].grid_points = 7

    return Simulator(
        device,
        PhysicsModel.default(),
        SimulationConfig(
            dwell_time_s=5.0e-3,
            internal_dt_s=INTERNAL_DT_S,
        ),
    )


def _weights(
    *,
    r01: float = 1.0,
    r12: float = 1.0,
    r10: float = 0.0,
    r21: float = 0.0,
) -> PhotoTransitionWeights:
    return PhotoTransitionWeights(
        r01=r01,
        r12=r12,
        r10=r10,
        r21=r21,
    )


def _protocol(
    *,
    wavelength_nm: float = WAVELENGTH_NM,
    power_density_W_m2: float = POWER_DENSITY_W_M2,
    weights: PhotoTransitionWeights | None = None,
    occupancy_integrator: str = "explicit_euler",
    program_voltage_V: float = PROGRAM_VOLTAGE_V,
) -> ElectroOpticalProgramTimeFitProtocol:
    return ElectroOpticalProgramTimeFitProtocol(
        program_voltage_V=program_voltage_V,
        read_voltage_V=READ_VOLTAGE_V,
        program_internal_dt_s=INTERNAL_DT_S,
        light_source=LightSource.laser(
            wavelength_nm=wavelength_nm,
            power_density_W_m2=power_density_W_m2,
        ),
        photo_weights=(
            _weights()
            if weights is None
            else weights
        ),
        occupancy_integrator=occupancy_integrator,
    )


def _photo_config(
    eta: float = 1.0e-7,
) -> PhotoTransitionConfig:
    return PhotoTransitionConfig(
        photo_capture_efficiency=eta,
    )


def _assert_occupation_state_equal(
    left: DeviceState,
    right: DeviceState,
) -> None:
    assert left.time_s == pytest.approx(right.time_s)
    assert len(left.floating_gates) == len(right.floating_gates)

    for left_fg, right_fg in zip(
        left.floating_gates,
        right.floating_gates,
    ):
        assert np.array_equal(left_fg.P0, right_fg.P0)
        assert np.array_equal(left_fg.P1, right_fg.P1)
        assert np.array_equal(left_fg.P2, right_fg.P2)


def test_protocol_hash_is_deterministic():
    assert (
        _protocol().protocol_hash()
        == _protocol().protocol_hash()
    )


@pytest.mark.parametrize(
    "variant",
    [
        _protocol(wavelength_nm=1300.0),
        _protocol(power_density_W_m2=500.0),
        _protocol(weights=_weights(r12=0.5)),
        _protocol(occupancy_integrator="backward_euler"),
        _protocol(program_voltage_V=1.5),
    ],
)
def test_protocol_hash_tracks_experimental_and_numerical_conditions(
    variant,
):
    assert variant.protocol_hash() != _protocol().protocol_hash()


def test_protocol_excludes_photo_capture_efficiency_value():
    payload = _protocol().to_dict()

    assert (
        payload["photo_capture_efficiency_semantics"]
        == "supplied-at-execution-not-part-of-protocol"
    )
    assert "photo_transition_config" not in payload
    assert payload["illumination_semantics"] == "program-pulse-only"
    assert payload["read_illumination"] == "dark"


def test_pulse_protocol_injects_requested_programming_time():
    pulse = _protocol().pulse_protocol(3.0e-4)

    assert (
        pulse.electrical_protocol.programming_time_s
        == pytest.approx(3.0e-4)
    )
    assert (
        pulse.electrical_protocol.program_voltage_V
        == pytest.approx(PROGRAM_VOLTAGE_V)
    )
    assert pulse.light_source is _protocol().light_source or (
        pulse.light_source.to_dict()
        == _protocol().light_source.to_dict()
    )


def test_prediction_uses_one_result_per_time_point():
    prediction = (
        predict_electro_optical_delta_vfb_vs_programming_time(
            _simulator(),
            PROGRAMMING_TIMES_S,
            _protocol(),
            photo_config=_photo_config(),
        )
    )

    assert isinstance(
        prediction,
        ElectroOpticalProgramTimePrediction,
    )
    assert (
        prediction.programming_times_s.shape
        == PROGRAMMING_TIMES_S.shape
    )
    assert (
        prediction.predicted_delta_vfb_V.shape
        == PROGRAMMING_TIMES_S.shape
    )
    assert (
        len(prediction.pulse_results)
        == PROGRAMMING_TIMES_S.size
    )


def test_prediction_time_points_are_independent():
    simulator = _simulator()
    initial = DeviceState.empty_for_device(
        simulator.device
    )

    prediction = (
        predict_electro_optical_delta_vfb_vs_programming_time(
            simulator,
            PROGRAMMING_TIMES_S,
            _protocol(),
            photo_config=_photo_config(),
            initial_state=initial,
        )
    )

    for time_s, pulse_result in zip(
        PROGRAMMING_TIMES_S,
        prediction.pulse_results,
    ):
        assert pulse_result.initial_state.time_s == pytest.approx(0.0)
        assert pulse_result.programmed_state.time_s == pytest.approx(
            time_s
        )

    assert initial.time_s == pytest.approx(0.0)


def test_prediction_preserves_requested_time_order():
    times = np.asarray(
        [1.0e-3, 1.0e-4, 3.0e-4],
        dtype=float,
    )

    prediction = (
        predict_electro_optical_delta_vfb_vs_programming_time(
            _simulator(),
            times,
            _protocol(),
            photo_config=_photo_config(),
        )
    )

    assert np.array_equal(
        prediction.programming_times_s,
        times,
    )


def test_prediction_propagates_photo_capture_efficiency():
    low = predict_electro_optical_delta_vfb_vs_programming_time(
        _simulator(),
        PROGRAMMING_TIMES_S,
        _protocol(),
        photo_config=_photo_config(1.0e-8),
    )
    high = predict_electro_optical_delta_vfb_vs_programming_time(
        _simulator(),
        PROGRAMMING_TIMES_S,
        _protocol(),
        photo_config=_photo_config(1.0e-7),
    )

    assert (
        high.pulse_results[-1].photo_transition_rate_s
        > low.pulse_results[-1].photo_transition_rate_s
    )
    assert (
        high.pulse_results[-1].mean_occupation
        > low.pulse_results[-1].mean_occupation
    )


def test_prediction_does_not_mutate_supplied_initial_state():
    simulator = _simulator()
    initial = DeviceState.empty_for_device(
        simulator.device
    )
    snapshot = initial.copy()

    predict_electro_optical_delta_vfb_vs_programming_time(
        simulator,
        PROGRAMMING_TIMES_S,
        _protocol(),
        photo_config=_photo_config(),
        initial_state=initial,
    )

    _assert_occupation_state_equal(
        initial,
        snapshot,
    )


@pytest.mark.parametrize(
    "times",
    [
        [],
        [0.0, 1.0e-3],
        [-1.0e-4, 1.0e-3],
        [float("nan"), 1.0e-3],
    ],
)
def test_prediction_rejects_invalid_times(times):
    with pytest.raises(ValueError):
        predict_electro_optical_delta_vfb_vs_programming_time(
            _simulator(),
            times,
            _protocol(),
            photo_config=_photo_config(),
        )


def test_prediction_requires_explicit_photo_config():
    with pytest.raises(
        TypeError,
        match="PhotoTransitionConfig",
    ):
        predict_electro_optical_delta_vfb_vs_programming_time(
            _simulator(),
            PROGRAMMING_TIMES_S,
            _protocol(),
            photo_config="not-a-photo-config",
        )
