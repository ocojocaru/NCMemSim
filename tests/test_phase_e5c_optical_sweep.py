import numpy as np

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


def test_dark_sweep_preserves_existing_behavior():
    _, sim = make_simulator()

    voltages = np.array([0.0, 1.0, 2.0])

    reference = sim.run_sweep(voltages)
    explicit_dark = sim.run_sweep(
        voltages,
        light_source=None,
    )

    assert np.array_equal(
        reference.mean_occupation,
        explicit_dark.mean_occupation,
    )
    assert np.array_equal(
        reference.qfg_C_m2,
        explicit_dark.qfg_C_m2,
    )
    assert np.array_equal(
        reference.capacitance_F_m2,
        explicit_dark.capacitance_F_m2,
    )


def test_illuminated_sweep_increases_programming():
    _, sim = make_simulator()

    voltages = np.array([0.0, 1.0, 2.0])

    dark = sim.run_sweep(voltages)

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    illuminated = sim.run_sweep(
        voltages,
        light_source=source,
        photo_config=PhotoTransitionConfig(
            photo_capture_efficiency=1.0e-7,
        ),
    )

    assert np.all(
        illuminated.mean_occupation
        >= dark.mean_occupation
    )

    assert np.any(
        illuminated.mean_occupation
        > dark.mean_occupation
    )


def test_optical_sweep_diagnostics_have_expected_shapes():
    _, sim = make_simulator()

    voltages = np.array([0.0, 1.0, 2.0, 3.0])

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    out = sim.run_sweep(
        voltages,
        light_source=source,
        photo_config=PhotoTransitionConfig(
            photo_capture_efficiency=1.0e-7,
        ),
    )

    assert out.optical_absorption_fraction.shape == (4,)
    assert out.absorbed_photon_flux_m2_s.shape == (4,)
    assert out.photo_transition_rate_s.shape == (4,)

    assert out.optical_absorption_fraction_by_fg.shape == (4, 1)
    assert out.absorbed_photon_flux_by_fg_m2_s.shape == (4, 1)
    assert out.absorbed_photon_rate_per_nc_by_fg_s.shape == (4, 1)
    assert out.photo_transition_rate_by_fg_s.shape == (4, 1)
    assert out.optical_alpha_nc_by_fg_m_inv.shape == (4, 1)
    assert out.optical_alpha_eff_by_fg_m_inv.shape == (4, 1)


def test_optical_material_diagnostics_are_constant_across_voltage():
    _, sim = make_simulator()

    voltages = np.array([0.0, 1.0, 2.0, 3.0])

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    out = sim.run_sweep(
        voltages,
        light_source=source,
        photo_config=PhotoTransitionConfig(
            photo_capture_efficiency=1.0e-7,
        ),
    )

    assert np.allclose(
        out.optical_absorption_fraction,
        out.optical_absorption_fraction[0],
    )

    assert np.allclose(
        out.absorbed_photon_flux_m2_s,
        out.absorbed_photon_flux_m2_s[0],
    )

    assert np.allclose(
        out.photo_transition_rate_s,
        out.photo_transition_rate_s[0],
    )

    assert np.allclose(
        out.optical_alpha_nc_by_fg_m_inv,
        out.optical_alpha_nc_by_fg_m_inv[0],
    )

    assert np.allclose(
        out.optical_alpha_eff_by_fg_m_inv,
        out.optical_alpha_eff_by_fg_m_inv[0],
    )


def test_multi_fg_optical_sweep_has_voltage_fg_matrices():
    _, sim = make_simulator(n_fgs=2)

    voltages = np.array([0.0, 1.0, 2.0])

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    out = sim.run_sweep(
        voltages,
        light_source=source,
        photo_config=PhotoTransitionConfig(
            photo_capture_efficiency=1.0e-7,
        ),
    )

    assert out.optical_absorption_fraction_by_fg.shape == (3, 2)
    assert out.absorbed_photon_flux_by_fg_m2_s.shape == (3, 2)
    assert out.absorbed_photon_rate_per_nc_by_fg_s.shape == (3, 2)
    assert out.photo_transition_rate_by_fg_s.shape == (3, 2)
    assert out.optical_alpha_nc_by_fg_m_inv.shape == (3, 2)
    assert out.optical_alpha_eff_by_fg_m_inv.shape == (3, 2)