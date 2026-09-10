import numpy as np
import pytest
import warnings

from ncmemsim import (
    DeviceBuilder,
    DeviceState,
    PhysicsModel,
    SimulationConfig,
    Simulator,
    make_gesn,
)
from ncmemsim.optics import LightSource
from ncmemsim.photo import PhotoTransitionConfig


def make_simulator(n_fgs=1):
    device = DeviceBuilder.v1(
        n_fgs=n_fgs,
        nc_material=[make_gesn(0.08)] * n_fgs,
        nc_diameter_nm=[5.0] * n_fgs,
        active_fraction=[1.0] * n_fgs,
        fg_thickness_nm=[15.0] * n_fgs,
    )

    for fg in device.floating_gates():
        fg.grid_points = 7

    sim = Simulator(
        device,
        PhysicsModel.default(),
        SimulationConfig(
            dwell_time_s=1.0e-3,
            internal_dt_s=1.0e-5,
        ),
    )

    return device, sim
    
    
def test_illuminated_simulation_exposes_optical_diagnostics():
    device, sim = make_simulator()

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    out = sim.relax_voltage(
        DeviceState.empty_for_device(device),
        gate_voltage_V=2.0,
        light_source=source,
        photo_config=PhotoTransitionConfig(
            photo_capture_efficiency=1.0e-7,
        ),
    )

    assert out["optical_absorption_fraction"] > 0.0
    assert out["absorbed_photon_flux_m2_s"] > 0.0
    assert out["photo_transition_rate_s"] > 0.0

    assert out["optical_alpha_nc_by_fg_m_inv"][0] > 0.0
    assert out["optical_alpha_eff_by_fg_m_inv"][0] > 0.0
    
    
def test_photo_rate_diagnostic_matches_efficiency_relation():
    device, sim = make_simulator()

    eta = 1.0e-7

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    out = sim.relax_voltage(
        DeviceState.empty_for_device(device),
        gate_voltage_V=2.0,
        light_source=source,
        photo_config=PhotoTransitionConfig(
            photo_capture_efficiency=eta,
        ),
    )

    rate_per_nc = (
        out["absorbed_photon_rate_per_nc_by_fg_s"][0]
    )

    photo_rate = (
        out["photo_transition_rate_by_fg_s"][0]
    )

    assert photo_rate == pytest.approx(
        eta * rate_per_nc
    )
    
    
def test_effective_alpha_diagnostic_matches_volume_fraction():
    device, sim = make_simulator()

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    out = sim.relax_voltage(
        DeviceState.empty_for_device(device),
        gate_voltage_V=2.0,
        light_source=source,
    )

    fg = device.floating_gates()[0]

    assert (
        out["optical_alpha_eff_by_fg_m_inv"][0]
        == pytest.approx(
            fg.nc_volume_fraction
            * out["optical_alpha_nc_by_fg_m_inv"][0]
        )
    )
    
    
def test_dark_simulation_has_zero_photo_flux_and_rate():
    device, sim = make_simulator()

    out = sim.relax_voltage(
        DeviceState.empty_for_device(device),
        gate_voltage_V=2.0,
    )

    assert out["absorbed_photon_flux_m2_s"] == 0.0
    assert out["photo_transition_rate_s"] == 0.0

    assert np.isnan(
        out["optical_absorption_fraction_by_fg"][0]
    )

    assert np.isnan(
        out["optical_alpha_nc_by_fg_m_inv"][0]
    )
    
    
def test_disabled_source_keeps_material_optics_but_zero_photo_rate():
    device, sim = make_simulator()

    source = LightSource(
        name="disabled",
        source_type="laser",
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
        enabled=False,
    )

    out = sim.relax_voltage(
        DeviceState.empty_for_device(device),
        gate_voltage_V=2.0,
        light_source=source,
    )

    assert out["optical_alpha_nc_by_fg_m_inv"][0] > 0.0
    assert out["optical_absorption_fraction_by_fg"][0] > 0.0

    assert out["absorbed_photon_flux_by_fg_m2_s"][0] == 0.0
    assert out["photo_transition_rate_by_fg_s"][0] == 0.0
    
    
def test_multi_fg_optical_diagnostics_have_per_fg_shape():
    device, sim = make_simulator(n_fgs=2)

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    out = sim.relax_voltage(
        DeviceState.empty_for_device(device),
        gate_voltage_V=2.0,
        light_source=source,
        photo_config=PhotoTransitionConfig(
            photo_capture_efficiency=1.0e-7,
        ),
    )

    assert out["optical_absorption_fraction_by_fg"].shape == (2,)
    assert out["absorbed_photon_flux_by_fg_m2_s"].shape == (2,)
    assert out["absorbed_photon_rate_per_nc_by_fg_s"].shape == (2,)
    assert out["photo_transition_rate_by_fg_s"].shape == (2,)
    assert out["optical_alpha_nc_by_fg_m_inv"].shape == (2,)
    assert out["optical_alpha_eff_by_fg_m_inv"].shape == (2,)
    
    
def test_multi_fg_dark_optical_diagnostics_do_not_warn():
    device, sim = make_simulator(n_fgs=2)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        out = sim.relax_voltage(
            DeviceState.empty_for_device(device),
            gate_voltage_V=2.0,
        )

    assert caught == []
    assert np.isnan(out["optical_absorption_fraction"])
    
