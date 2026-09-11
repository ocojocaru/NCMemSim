import numpy as np
import pytest

from ncmemsim.kinetics import OccupancyEngine
from ncmemsim.layers import FloatingGateLayer
from ncmemsim.materials import HFO2, make_gesn
from ncmemsim.optics import (
    LightSource,
    evaluate_floating_gate_optical_absorption,
)
from ncmemsim.photo import (
    PhotoTransitionConfig,
    photo_transition_rates_from_optical_result,
)
from ncmemsim.state import FloatingGateState
from ncmemsim.tunneling import TunnelingEngine



def make_test_fg():
    return FloatingGateLayer(
        name="FG",
        matrix_material=HFO2,
        thickness_nm=15.0,
        nc_material=make_gesn(0.08),
        nc_diameter_nm=5.0,
        nc_volume_fraction=0.60,
        electrically_active_fraction=1.0,
        grid_points=7,
    )


def occupation_after_programming(
    voltage_V,
    *,
    illuminated,
    power_density_W_m2=1000.0,
    dwell_time_s=1.0e-3,
    photo_capture_efficiency=1.0e-7,
):
    layer = make_test_fg()
    tunneling = TunnelingEngine()
    occupancy = OccupancyEngine(tunneling)

    x_m, _ = occupancy.grid(layer)

    electrical = occupancy.rates(
        fg=layer,
        x_m=x_m,
        veff_V=voltage_V,
        tunnel_base_distance_m=10.0e-9,
        temperature_K=300.0,
    )

    rates = electrical

    if illuminated:
        source = LightSource.laser(
            wavelength_nm=1550.0,
            power_density_W_m2=power_density_W_m2,
        )

        optical = evaluate_floating_gate_optical_absorption(
            source,
            layer,
        )

        photo = photo_transition_rates_from_optical_result(
            optical,
            layer,
        )
        
        photo = photo_transition_rates_from_optical_result(
            optical,
            layer,
            config=PhotoTransitionConfig(
                photo_capture_efficiency=photo_capture_efficiency,
            ),
        )

        rates = occupancy.combine_rates(
            electrical,
            photo,
        )

    state = FloatingGateState.empty(
        layer.grid_points
    )

    updated = occupancy.step(
        state,
        rates,
        dt_s=dwell_time_s,
    )

    return updated.mean_normalized_occupation


def voltage_for_target(
    voltages,
    occupations,
    target,
):
    voltages = np.asarray(voltages, dtype=float)
    occupations = np.asarray(occupations, dtype=float)

    if target < occupations.min() or target > occupations.max():
        return float("nan")

    order = np.argsort(occupations)

    return float(
        np.interp(
            target,
            occupations[order],
            voltages[order],
        )
    )
    
    
def test_illumination_increases_occupation_across_voltage_sweep():
    voltages = np.linspace(0.0, 4.0, 17)

    dark = np.array([
        occupation_after_programming(
            v,
            illuminated=False,
        )
        for v in voltages
    ])

    light = np.array([
        occupation_after_programming(
            v,
            illuminated=True,
        )
        for v in voltages
    ])

    assert np.all(light > dark)
    
    
def test_programming_increases_with_voltage():
    voltages = np.linspace(0.0, 4.0, 17)

    dark = np.array([
        occupation_after_programming(
            v,
            illuminated=False,
        )
        for v in voltages
    ])

    light = np.array([
        occupation_after_programming(
            v,
            illuminated=True,
        )
        for v in voltages
    ])

    assert np.all(np.diff(dark) >= 0.0)
    assert np.all(np.diff(light) >= 0.0)
    
    
def test_illumination_reduces_voltage_for_same_target_occupation():
    voltages = np.linspace(0.0, 4.0, 81)

    dark = np.array([
        occupation_after_programming(
            v,
            illuminated=False,
        )
        for v in voltages
    ])

    light = np.array([
        occupation_after_programming(
            v,
            illuminated=True,
        )
        for v in voltages
    ])

    common_min = max(
        dark.min(),
        light.min(),
    )

    common_max = min(
        dark.max(),
        light.max(),
    )

    assert common_max > common_min

    target = common_min + 0.5 * (
        common_max - common_min
    )

    v_dark = voltage_for_target(
        voltages,
        dark,
        target,
    )

    v_light = voltage_for_target(
        voltages,
        light,
        target,
    )

    assert np.isfinite(v_dark)
    assert np.isfinite(v_light)

    assert v_light < v_dark
    
    
def test_higher_optical_power_requires_lower_voltage():
    voltages = np.linspace(0.0, 4.0, 81)

    low = np.array([
        occupation_after_programming(
            v,
            illuminated=True,
            power_density_W_m2=100.0,
        )
        for v in voltages
    ])

    high = np.array([
        occupation_after_programming(
            v,
            illuminated=True,
            power_density_W_m2=500.0,
        )
        for v in voltages
    ])

    common_min = max(
        low.min(),
        high.min(),
    )

    common_max = min(
        low.max(),
        high.max(),
    )

    assert common_max > common_min

    target = common_min + 0.5 * (
        common_max - common_min
    )

    v_low = voltage_for_target(
        voltages,
        low,
        target,
    )

    v_high = voltage_for_target(
        voltages,
        high,
        target,
    )

    assert v_high < v_low
    
    
def test_voltage_for_target_interpolates():
    voltages = np.array([
        0.0,
        1.0,
        2.0,
    ])

    occupations = np.array([
        0.0,
        0.1,
        0.2,
    ])

    result = voltage_for_target(
        voltages,
        occupations,
        target=0.15,
    )

    assert result == pytest.approx(1.5)