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
PHOTO_CAPTURE_EFFICIENCY = 1.0e-10

WAVELENGTHS_NM = (
    1300.0,
    1550.0,
    1700.0,
)

VOLTAGES_V = np.linspace(
    0.0,
    4.0,
    17,
)

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


def occupation_curve(
    sim,
    device,
    wavelength_nm=None,
):
    occupations = []
    photo_rates = []

    light_source = (
        None
        if wavelength_nm is None
        else make_light(wavelength_nm)
    )

    for voltage_V in VOLTAGES_V:
        state = DeviceState.empty_for_device(device)

        out = sim.relax_voltage(
            state,
            gate_voltage_V=float(voltage_V),
            light_source=light_source,
            photo_config=make_photo_config(),
        )

        occupations.append(
            out["mean_occupation"]
        )

        photo_rates.append(
            out["photo_transition_rate_s"]
        )

    return (
        np.asarray(occupations, dtype=float),
        np.asarray(photo_rates, dtype=float),
    )


def common_target_occupation(
    dark_occupation,
    *light_occupations,
):
    curves = (
        dark_occupation,
        *light_occupations,
    )

    lower = max(
        np.min(curve)
        for curve in curves
    )

    upper = min(
        np.max(curve)
        for curve in curves
    )

    if upper <= lower:
        raise ValueError(
            "Dark and illuminated occupation curves "
            "do not share a common overlap range."
        )

    return 0.5 * (lower + upper)


def required_voltage_for_occupation(
    occupations,
    target_occupation,
):
    order = np.argsort(occupations)

    occupation_sorted = occupations[order]
    voltage_sorted = VOLTAGES_V[order]

    return float(
        np.interp(
            target_occupation,
            occupation_sorted,
            voltage_sorted,
        )
    )


@pytest.fixture(scope="module")
def benchmark():
    device, sim = make_simulator()

    dark_occupation, dark_photo_rate = occupation_curve(
        sim,
        device,
        wavelength_nm=None,
    )

    illuminated = {}

    for wavelength_nm in WAVELENGTHS_NM:
        occupation, photo_rate = occupation_curve(
            sim,
            device,
            wavelength_nm=wavelength_nm,
        )

        illuminated[wavelength_nm] = {
            "occupation": occupation,
            "photo_rate": photo_rate,
        }

    light_curves = [
        illuminated[wavelength_nm]["occupation"]
        for wavelength_nm in WAVELENGTHS_NM
    ]

    target_occupation = common_target_occupation(
        dark_occupation,
        *light_curves,
    )
    
    return {
        "dark_occupation": dark_occupation,
        "dark_photo_rate": dark_photo_rate,
        "illuminated": illuminated,
        "target_occupation": target_occupation,
    }


def test_dark_programming_increases_with_positive_gate_voltage(
    benchmark,
):
    dark = benchmark["dark_occupation"]

    assert np.all(np.isfinite(dark))

    assert dark[-1] > dark[0]

    assert np.all(
        np.diff(dark) >= -1.0e-15
    )


def test_swir_illumination_increases_occupation_at_same_voltage(
    benchmark,
):
    dark = benchmark["dark_occupation"]

    for wavelength_nm in WAVELENGTHS_NM:
        light = benchmark["illuminated"][
            wavelength_nm
        ]["occupation"]

        assert np.all(light >= dark)

        assert np.any(
            light > dark
        )


def test_dark_and_swir_curves_have_common_occupation_range(
    benchmark,
):
    dark = benchmark["dark_occupation"]
    target = benchmark["target_occupation"]
    
    assert np.min(dark) < target < np.max(dark)

    for wavelength_nm in WAVELENGTHS_NM:
        light = benchmark["illuminated"][
            wavelength_nm
        ]["occupation"]

        assert np.min(light) < target < np.max(light)


def test_swir_reduces_required_programming_voltage(
    benchmark,
):
    dark = benchmark["dark_occupation"]
    target = benchmark["target_occupation"]

    for wavelength_nm in WAVELENGTHS_NM:
        light = benchmark["illuminated"][
            wavelength_nm
        ]["occupation"]

        v_dark = required_voltage_for_occupation(
            dark,
            target,
        )

        v_light = required_voltage_for_occupation(
            light,
            target,
        )

        delta_v = v_dark - v_light

        assert delta_v > 0.0

        assert 0.0 <= v_light <= 4.0
        assert 0.0 <= v_dark <= 4.0


def test_voltage_reduction_tracks_spectral_photo_rate(
    benchmark,
):
    dark = benchmark["dark_occupation"]
    target = benchmark["target_occupation"]

    photo_rates = []
    voltage_reductions = []

    for wavelength_nm in WAVELENGTHS_NM:
        data = benchmark["illuminated"][
            wavelength_nm
        ]

        light = data["occupation"]

        v_dark = required_voltage_for_occupation(
            dark,
            target,
        )

        v_light = required_voltage_for_occupation(
            light,
            target,
        )

        photo_rates.append(
            np.mean(data["photo_rate"])
        )

        voltage_reductions.append(
            v_dark - v_light
        )

    photo_rates = np.asarray(photo_rates)
    voltage_reductions = np.asarray(
        voltage_reductions
    )

    assert np.all(photo_rates > 0.0)
    assert np.all(voltage_reductions > 0.0)

    assert np.array_equal(
        np.argsort(photo_rates),
        np.argsort(voltage_reductions),
    )


def test_dark_photo_rate_is_zero_and_light_rate_is_voltage_independent(
    benchmark,
):
    assert np.all(
        benchmark["dark_photo_rate"] == 0.0
    )

    for wavelength_nm in WAVELENGTHS_NM:
        rates = benchmark["illuminated"][
            wavelength_nm
        ]["photo_rate"]

        assert np.all(rates > 0.0)

        assert np.allclose(
            rates,
            rates[0],
            rtol=1.0e-12,
            atol=0.0,
        )