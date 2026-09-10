import numpy as np
import pytest

from ncmemsim.kinetics import OccupancyEngine, RateArrays
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


def zero_electrical_rates(grid_points):
    zeros = np.zeros(grid_points)

    return RateArrays(
        r01=zeros.copy(),
        r12=zeros.copy(),
        r21=zeros.copy(),
        r10=zeros.copy(),
        tprog=zeros.copy(),
        terase=zeros.copy(),
        field_V_m=zeros.copy(),
    )
    
    
def test_light_changes_empty_floating_gate_state():
    layer = make_test_fg()

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

    electrical = zero_electrical_rates(
        layer.grid_points
    )

    total = OccupancyEngine.combine_rates(
        electrical,
        photo,
    )

    state = FloatingGateState.empty(
        layer.grid_points,
        layer_name=layer.name,
    )

    updated = OccupancyEngine.step(
        state,
        total,
        dt_s=1.0e-3,
    )

    assert np.all(updated.P0 < state.P0)
    assert np.all(updated.P1 > state.P1)
    assert updated.mean_normalized_occupation > 0.0
    
    
def test_zero_photo_efficiency_leaves_state_unchanged():
    layer = make_test_fg()

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
        config=PhotoTransitionConfig(
            photo_capture_efficiency=0.0
        ),
    )

    total = OccupancyEngine.combine_rates(
        zero_electrical_rates(layer.grid_points),
        photo,
    )

    state = FloatingGateState.empty(
        layer.grid_points
    )

    updated = OccupancyEngine.step(
        state,
        total,
        dt_s=1.0e-3,
    )

    assert np.allclose(updated.P0, state.P0)
    assert np.allclose(updated.P1, state.P1)
    assert np.allclose(updated.P2, state.P2)
    
    
def test_higher_optical_power_increases_photo_programming():
    layer = make_test_fg()

    low_source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=100.0,
    )

    high_source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    low_optical = evaluate_floating_gate_optical_absorption(
        low_source,
        layer,
    )

    high_optical = evaluate_floating_gate_optical_absorption(
        high_source,
        layer,
    )

    low_photo = photo_transition_rates_from_optical_result(
        low_optical,
        layer,
    )

    high_photo = photo_transition_rates_from_optical_result(
        high_optical,
        layer,
    )

    electrical = zero_electrical_rates(
        layer.grid_points
    )

    initial = FloatingGateState.empty(
        layer.grid_points
    )

    low_state = OccupancyEngine.step(
        initial,
        OccupancyEngine.combine_rates(
            electrical,
            low_photo,
        ),
        dt_s=1.0e-3,
    )

    high_state = OccupancyEngine.step(
        initial,
        OccupancyEngine.combine_rates(
            electrical,
            high_photo,
        ),
        dt_s=1.0e-3,
    )

    assert (
        high_state.mean_normalized_occupation
        > low_state.mean_normalized_occupation
    )
    
    
def test_photo_programming_preserves_probability_normalization():
    layer = make_test_fg()

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

    total = OccupancyEngine.combine_rates(
        zero_electrical_rates(layer.grid_points),
        photo,
    )

    state = FloatingGateState.empty(
        layer.grid_points
    )

    updated = OccupancyEngine.step(
        state,
        total,
        dt_s=1.0e-3,
    )

    assert np.allclose(
        updated.P0 + updated.P1 + updated.P2,
        1.0,
    )

    updated.validate()
    
    
def test_end_to_end_photo_rates_match_fg_grid():
    layer = make_test_fg()

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

    assert photo.r01.shape == (layer.grid_points,)
    assert photo.r12.shape == (layer.grid_points,)
    assert photo.r10.shape == (layer.grid_points,)
    assert photo.r21.shape == (layer.grid_points,)
    
    
def test_disabled_light_source_gives_zero_photo_programming():
    layer = make_test_fg()

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

    assert np.all(photo.r01 == 0.0)
    assert np.all(photo.r12 == 0.0)
    assert np.all(photo.r10 == 0.0)
    assert np.all(photo.r21 == 0.0)