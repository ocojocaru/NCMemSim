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
from ncmemsim.electro_optical_program_protocol import (
    ElectroOpticalProgramPulseReadProtocol,
    ElectroOpticalProgramPulseReadResult,
    run_electro_optical_program_pulse_read,
)
from ncmemsim.optics import LightSource
from ncmemsim.photo import (
    PhotoTransitionConfig,
    PhotoTransitionWeights,
)
from ncmemsim.program_protocol import (
    ProgramPulseReadProtocol,
    run_program_pulse_read,
)


PROGRAM_VOLTAGE_V = 2.0
PROGRAMMING_TIME_S = 1.0e-3
READ_VOLTAGE_V = 0.0
INTERNAL_DT_S = 1.0e-5
POWER_DENSITY_W_M2 = 1000.0
WAVELENGTH_NM = 1550.0


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
            dwell_time_s=PROGRAMMING_TIME_S,
            internal_dt_s=INTERNAL_DT_S,
        ),
    )


def _electrical_protocol() -> ProgramPulseReadProtocol:
    return ProgramPulseReadProtocol(
        program_voltage_V=PROGRAM_VOLTAGE_V,
        programming_time_s=PROGRAMMING_TIME_S,
        read_voltage_V=READ_VOLTAGE_V,
        program_internal_dt_s=INTERNAL_DT_S,
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
) -> ElectroOpticalProgramPulseReadProtocol:
    return ElectroOpticalProgramPulseReadProtocol(
        electrical_protocol=_electrical_protocol(),
        light_source=LightSource.laser(
            wavelength_nm=wavelength_nm,
            power_density_W_m2=power_density_W_m2,
        ),
        photo_weights=_weights() if weights is None else weights,
        occupancy_integrator=occupancy_integrator,
    )


def _photo_config(eta: float = 1.0e-7) -> PhotoTransitionConfig:
    return PhotoTransitionConfig(
        photo_capture_efficiency=eta,
    )


def _assert_same_state(a: DeviceState, b: DeviceState) -> None:
    assert a.time_s == pytest.approx(b.time_s)
    assert len(a.floating_gates) == len(b.floating_gates)

    for left, right in zip(
        a.floating_gates,
        b.floating_gates,
    ):
        assert np.array_equal(left.P0, right.P0)
        assert np.array_equal(left.P1, right.P1)
        assert np.array_equal(left.P2, right.P2)


def test_protocol_hash_is_deterministic():
    assert _protocol().protocol_hash() == _protocol().protocol_hash()


@pytest.mark.parametrize(
    "variant",
    [
        _protocol(wavelength_nm=1300.0),
        _protocol(power_density_W_m2=500.0),
        _protocol(weights=_weights(r12=0.5)),
        _protocol(occupancy_integrator="backward_euler"),
    ],
)
def test_protocol_hash_tracks_optical_and_numerical_conditions(variant):
    assert variant.protocol_hash() != _protocol().protocol_hash()


def test_protocol_serialization_excludes_photo_capture_efficiency_value():
    payload = _protocol().to_dict()

    assert (
        payload["photo_capture_efficiency_semantics"]
        == "supplied-at-execution-not-part-of-protocol"
    )
    assert "photo_transition_config" not in payload
    assert payload["read_illumination"] == "dark"
    assert payload["illumination_semantics"] == "program-pulse-only"


def test_protocol_rejects_disabled_or_zero_power_source():
    with pytest.raises(ValueError, match="enabled light source"):
        ElectroOpticalProgramPulseReadProtocol(
            electrical_protocol=_electrical_protocol(),
            light_source=LightSource(
                name="disabled",
                source_type="laser",
                power_density_W_m2=1000.0,
                wavelength_nm=WAVELENGTH_NM,
                enabled=False,
            ),
            photo_weights=_weights(),
        )

    with pytest.raises(ValueError, match="strictly positive"):
        ElectroOpticalProgramPulseReadProtocol(
            electrical_protocol=_electrical_protocol(),
            light_source=LightSource.laser(
                wavelength_nm=WAVELENGTH_NM,
                power_density_W_m2=0.0,
            ),
            photo_weights=_weights(),
        )


def test_protocol_rejects_zero_or_nonfinite_photo_weights():
    with pytest.raises(ValueError, match="At least one"):
        _protocol(
            weights=_weights(
                r01=0.0,
                r12=0.0,
                r10=0.0,
                r21=0.0,
            )
        )

    nan_weights = PhotoTransitionWeights(
        r01=float("nan"),
        r12=1.0,
        r10=0.0,
        r21=0.0,
    )
    with pytest.raises(ValueError, match="finite"):
        _protocol(weights=nan_weights)


def test_runner_requires_explicit_photo_config_type():
    with pytest.raises(TypeError, match="PhotoTransitionConfig"):
        run_electro_optical_program_pulse_read(
            _simulator(),
            _protocol(),
            photo_config="not-a-photo-config",
        )


def test_illuminated_program_produces_positive_optical_diagnostics():
    result = run_electro_optical_program_pulse_read(
        _simulator(),
        _protocol(),
        photo_config=_photo_config(),
    )

    assert isinstance(
        result,
        ElectroOpticalProgramPulseReadResult,
    )
    assert result.absorbed_photon_flux_m2_s > 0.0
    assert result.photo_transition_rate_s > 0.0
    assert np.all(
        result.absorbed_photon_flux_by_fg_m2_s > 0.0
    )
    assert np.all(
        result.photo_transition_rate_by_fg_s > 0.0
    )


def test_read_is_dark_zero_dwell_and_does_not_change_programmed_state():
    result = run_electro_optical_program_pulse_read(
        _simulator(),
        _protocol(),
        photo_config=_photo_config(),
    )

    # Simulator.relax_voltage() still performs one zero-dt occupancy
    # projection for dwell_time_s=0.0. OccupancyEngine.step() normalizes
    # P0/P1/P2, so last-bit roundoff is allowed even though there is no
    # physical kinetic evolution during the read.
    assert result.read_state.time_s == pytest.approx(
        result.programmed_state.time_s
    )
    assert len(result.read_state.floating_gates) == len(
        result.programmed_state.floating_gates
    )

    for programmed, read in zip(
        result.programmed_state.floating_gates,
        result.read_state.floating_gates,
    ):
        assert np.allclose(
            programmed.P0,
            read.P0,
            rtol=0.0,
            atol=1.0e-15,
        )
        assert np.allclose(
            programmed.P1,
            read.P1,
            rtol=0.0,
            atol=1.0e-15,
        )
        assert np.allclose(
            programmed.P2,
            read.P2,
            rtol=0.0,
            atol=1.0e-15,
        )


def test_zero_photo_efficiency_matches_electrical_programming():
    simulator = _simulator()

    illuminated_zero = run_electro_optical_program_pulse_read(
        simulator,
        _protocol(),
        photo_config=_photo_config(0.0),
    )
    electrical = run_program_pulse_read(
        simulator,
        _electrical_protocol(),
    )

    assert illuminated_zero.absorbed_photon_flux_m2_s > 0.0
    assert illuminated_zero.photo_transition_rate_s == pytest.approx(0.0)
    assert illuminated_zero.delta_vfb_V == pytest.approx(
        electrical.delta_vfb_V,
        rel=0.0,
        abs=1.0e-15,
    )
    assert illuminated_zero.mean_occupation == pytest.approx(
        electrical.mean_occupation,
        rel=0.0,
        abs=1.0e-15,
    )


def test_higher_photo_capture_efficiency_increases_programmed_occupation():
    low = run_electro_optical_program_pulse_read(
        _simulator(),
        _protocol(),
        photo_config=_photo_config(1.0e-8),
    )
    high = run_electro_optical_program_pulse_read(
        _simulator(),
        _protocol(),
        photo_config=_photo_config(1.0e-7),
    )

    assert high.photo_transition_rate_s > low.photo_transition_rate_s
    assert high.mean_occupation > low.mean_occupation


def test_runner_does_not_mutate_supplied_initial_state():
    simulator = _simulator()
    initial = DeviceState.empty_for_device(
        simulator.device
    )
    snapshot = initial.copy()

    run_electro_optical_program_pulse_read(
        simulator,
        _protocol(),
        photo_config=_photo_config(),
        initial_state=initial,
    )

    _assert_same_state(initial, snapshot)


def test_result_serializes_protocol_and_applied_photo_parameter():
    protocol = _protocol()
    result = run_electro_optical_program_pulse_read(
        _simulator(),
        protocol,
        photo_config=_photo_config(2.0e-7),
    )

    payload = result.to_dict()

    assert payload["protocol_hash"] == protocol.protocol_hash()
    assert (
        payload["photo_transition_config"][
            "photo_capture_efficiency"
        ]
        == pytest.approx(2.0e-7)
    )
    assert payload["protocol"]["read_illumination"] == "dark"
