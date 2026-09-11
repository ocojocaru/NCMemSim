import numpy as np
import pytest

from ncmemsim import (
    DeviceBuilder,
    DeviceState,
    PhysicsModel,
    Simulator,
    SimulationConfig,
    make_gesn,
)

from ncmemsim.optics import LightSource
from ncmemsim.photo import PhotoTransitionConfig


POWER_DENSITY_W_M2 = 1000.0
PHOTO_CAPTURE_EFFICIENCY = 1.0e-7

WAVELENGTHS_NM = (
    1300.0,
    1550.0,
    1700.0,
)

GATE_VOLTAGE_V = 2.0
OPTICAL_ONLY_GATE_VOLTAGE_V = 0.0

DWELL_TIME_S = 1.0e-3
INTERNAL_DT_S = 1.0e-5


def make_simulator():
    device = DeviceBuilder.v1(
        n_fgs=1,
        nc_material=[make_gesn(0.08)],
        nc_diameter_nm=[5.0],
        active_fraction=[1.0],
        fg_thickness_nm=[15.0],
    )

    fg = device.floating_gates()[0]
    fg.grid_points = 7

    physics = PhysicsModel.default()

    sim = Simulator(
        device,
        physics,
        SimulationConfig(
            dwell_time_s=DWELL_TIME_S,
            internal_dt_s=INTERNAL_DT_S,
        ),
    )

    return device, sim


def make_light(wavelength_nm):
    return LightSource.laser(
        wavelength_nm=wavelength_nm,
        power_density_W_m2=POWER_DENSITY_W_M2,
    )


def make_photo_config():
    return PhotoTransitionConfig(
        photo_capture_efficiency=PHOTO_CAPTURE_EFFICIENCY,
    )


def run_benchmark(
    wavelength_nm=None,
    gate_voltage_V=GATE_VOLTAGE_V,
):
    device, sim = make_simulator()

    state = DeviceState.empty_for_device(device)

    light_source = (
        None
        if wavelength_nm is None
        else make_light(wavelength_nm)
    )

    out = sim.relax_voltage(
        state,
        gate_voltage_V=gate_voltage_V,
        light_source=light_source,
        photo_config=make_photo_config(),
    )

    return device, out


def test_dark_benchmark_has_zero_photo_contribution():
    _, out = run_benchmark(
        wavelength_nm=None,
        gate_voltage_V=GATE_VOLTAGE_V,
    )

    assert out["absorbed_photon_flux_m2_s"] == pytest.approx(0.0)
    assert out["photo_transition_rate_s"] == pytest.approx(0.0)

    assert np.all(
        out["absorbed_photon_flux_by_fg_m2_s"] == 0.0
    )

    assert np.all(
        out["photo_transition_rate_by_fg_s"] == 0.0
    )


def test_swir_light_produces_measurable_photo_programming():
    _, dark = run_benchmark(
        wavelength_nm=None,
        gate_voltage_V=GATE_VOLTAGE_V,
    )

    _, light = run_benchmark(
        wavelength_nm=1550.0,
        gate_voltage_V=GATE_VOLTAGE_V,
    )

    assert light["absorbed_photon_flux_m2_s"] > 0.0
    assert light["photo_transition_rate_s"] > 0.0

    assert (
        light["mean_occupation"]
        >
        dark["mean_occupation"]
    )


def test_electro_optical_programming_exceeds_electrical_only():
    _, electrical = run_benchmark(
        wavelength_nm=None,
        gate_voltage_V=GATE_VOLTAGE_V,
    )

    _, electro_optical = run_benchmark(
        wavelength_nm=1550.0,
        gate_voltage_V=GATE_VOLTAGE_V,
    )

    assert (
        electro_optical["mean_occupation"]
        >
        electrical["mean_occupation"]
    )

    assert (
        electro_optical["qfg_C_m2"]
        != pytest.approx(
            electrical["qfg_C_m2"],
            rel=0.0,
            abs=1.0e-30,
        )
    )


def test_swir_programming_follows_spectral_photo_rate():
    results = []

    for wavelength_nm in WAVELENGTHS_NM:
        _, out = run_benchmark(
            wavelength_nm=wavelength_nm,
            gate_voltage_V=GATE_VOLTAGE_V,
        )

        results.append(
            (
                wavelength_nm,
                out["photo_transition_rate_s"],
                out["mean_occupation"],
            )
        )

    photo_rates = np.asarray(
        [item[1] for item in results]
    )

    occupations = np.asarray(
        [item[2] for item in results]
    )

    assert np.ptp(photo_rates) > 0.0
    assert np.ptp(occupations) > 0.0

    rate_order = np.argsort(photo_rates)
    occupation_order = np.argsort(occupations)

    assert np.array_equal(
        rate_order,
        occupation_order,
    )


def test_optical_only_programming_changes_empty_state():
    _, dark = run_benchmark(
        wavelength_nm=None,
        gate_voltage_V=OPTICAL_ONLY_GATE_VOLTAGE_V,
    )

    _, light = run_benchmark(
        wavelength_nm=1550.0,
        gate_voltage_V=OPTICAL_ONLY_GATE_VOLTAGE_V,
    )

    assert light["photo_transition_rate_s"] > 0.0

    assert (
        light["mean_occupation"]
        >
        dark["mean_occupation"]
    )


def test_swir_programming_preserves_probability_normalization():
    device, out = run_benchmark(
        wavelength_nm=1550.0,
        gate_voltage_V=GATE_VOLTAGE_V,
    )

    state = out["state"]

    state.validate(device)

    fg_state = state.floating_gates[0]

    total_probability = (
        fg_state.P0
        + fg_state.P1
        + fg_state.P2
    )

    assert np.all(np.isfinite(total_probability))

    assert np.allclose(
        total_probability,
        1.0,
        rtol=0.0,
        atol=1.0e-12,
    )

    assert np.all(fg_state.P0 >= 0.0)
    assert np.all(fg_state.P1 >= 0.0)
    assert np.all(fg_state.P2 >= 0.0)