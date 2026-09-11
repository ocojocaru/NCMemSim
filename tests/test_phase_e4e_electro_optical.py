import numpy as np

from ncmemsim.kinetics import OccupancyEngine
from ncmemsim.layers import FloatingGateLayer
from ncmemsim.materials import HFO2, make_gesn
from ncmemsim.optics import (
    LightSource,
    evaluate_floating_gate_optical_absorption,
)
from ncmemsim.photo import (
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


def make_engines():
    tunneling = TunnelingEngine()
    occupancy = OccupancyEngine(tunneling)
    return tunneling, occupancy
    
    
def test_electro_optical_rates_exceed_electrical_programming_rates():
    layer = make_test_fg()
    tunneling, occupancy = make_engines()

    x_m, _ = occupancy.grid(layer)

    electrical = occupancy.rates(
        fg=layer,
        x_m=x_m,
        veff_V=2.0,
        tunnel_base_distance_m=10.0e-9,
        temperature_K=300.0,
    )

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    optical = evaluate_floating_gate_optical_absorption(
        source,
        layer,
    )

    photo = photo_transition_rates_from_optical_result(
        optical,
        layer,
    )

    total = occupancy.combine_rates(
        electrical,
        photo,
    )

    assert np.all(total.r01 > electrical.r01)
    assert np.all(total.r12 > electrical.r12)

    assert np.allclose(total.r10, electrical.r10)
    assert np.allclose(total.r21, electrical.r21)
    
    
def test_electro_optical_programming_exceeds_electrical_only():
    layer = make_test_fg()
    tunneling, occupancy = make_engines()

    x_m, _ = occupancy.grid(layer)

    electrical = occupancy.rates(
        fg=layer,
        x_m=x_m,
        veff_V=2.0,
        tunnel_base_distance_m=10.0e-9,
        temperature_K=300.0,
    )

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    optical = evaluate_floating_gate_optical_absorption(
        source,
        layer,
    )

    photo = photo_transition_rates_from_optical_result(
        optical,
        layer,
    )

    electro_optical = occupancy.combine_rates(
        electrical,
        photo,
    )

    initial = FloatingGateState.empty(
        layer.grid_points
    )

    electrical_state = occupancy.step(
        initial,
        electrical,
        dt_s=1.0e-5,
    )

    electro_optical_state = occupancy.step(
        initial,
        electro_optical,
        dt_s=1.0e-5,
    )

    assert (
        electro_optical_state.mean_normalized_occupation
        > electrical_state.mean_normalized_occupation
    )
    
    
def test_disabled_light_recovers_electrical_only_result():
    layer = make_test_fg()
    tunneling, occupancy = make_engines()

    x_m, _ = occupancy.grid(layer)

    electrical = occupancy.rates(
        fg=layer,
        x_m=x_m,
        veff_V=2.0,
        tunnel_base_distance_m=10.0e-9,
        temperature_K=300.0,
    )

    source = LightSource(
        name="Disabled laser",
        source_type="laser",
        power_density_W_m2=1000.0,
        wavelength_nm=1550.0,
        enabled=False,
    )

    optical = evaluate_floating_gate_optical_absorption(
        source,
        layer,
    )

    photo = photo_transition_rates_from_optical_result(
        optical,
        layer,
    )

    total = occupancy.combine_rates(
        electrical,
        photo,
    )

    initial = FloatingGateState.empty(
        layer.grid_points
    )

    dark_state = occupancy.step(
        initial,
        electrical,
        dt_s=1.0e-5,
    )

    disabled_state = occupancy.step(
        initial,
        total,
        dt_s=1.0e-5,
    )

    assert np.allclose(disabled_state.P0, dark_state.P0)
    assert np.allclose(disabled_state.P1, dark_state.P1)
    assert np.allclose(disabled_state.P2, dark_state.P2)
    
    
def test_more_optical_power_increases_electro_optical_programming():
    layer = make_test_fg()
    tunneling, occupancy = make_engines()

    x_m, _ = occupancy.grid(layer)

    electrical = occupancy.rates(
        fg=layer,
        x_m=x_m,
        veff_V=2.0,
        tunnel_base_distance_m=10.0e-9,
        temperature_K=300.0,
    )

    low_source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=100.0,
    )

    high_source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    low_photo = photo_transition_rates_from_optical_result(
        evaluate_floating_gate_optical_absorption(
            low_source,
            layer,
        ),
        layer,
    )

    high_photo = photo_transition_rates_from_optical_result(
        evaluate_floating_gate_optical_absorption(
            high_source,
            layer,
        ),
        layer,
    )

    initial = FloatingGateState.empty(
        layer.grid_points
    )

    low_state = occupancy.step(
        initial,
        occupancy.combine_rates(
            electrical,
            low_photo,
        ),
        dt_s=1.0e-5,
    )

    high_state = occupancy.step(
        initial,
        occupancy.combine_rates(
            electrical,
            high_photo,
        ),
        dt_s=1.0e-5,
    )

    assert (
        high_state.mean_normalized_occupation
        > low_state.mean_normalized_occupation
    )
    
    
def test_electro_optical_step_preserves_probability_normalization():
    layer = make_test_fg()
    tunneling, occupancy = make_engines()

    x_m, _ = occupancy.grid(layer)

    electrical = occupancy.rates(
        fg=layer,
        x_m=x_m,
        veff_V=2.0,
        tunnel_base_distance_m=10.0e-9,
        temperature_K=300.0,
    )

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    photo = photo_transition_rates_from_optical_result(
        evaluate_floating_gate_optical_absorption(
            source,
            layer,
        ),
        layer,
    )

    total = occupancy.combine_rates(
        electrical,
        photo,
    )

    initial = FloatingGateState.empty(
        layer.grid_points
    )

    updated = occupancy.step(
        initial,
        total,
        dt_s=1.0e-5,
    )

    assert np.allclose(
        updated.P0 + updated.P1 + updated.P2,
        1.0,
    )

    updated.validate()