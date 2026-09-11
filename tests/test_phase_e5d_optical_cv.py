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


def test_dark_cv_preserves_existing_behavior():
    _, sim = make_simulator()

    reference = sim.simulate_cv(
        vmin_V=-2.0,
        vmax_V=2.0,
        points=21,
    )

    explicit_dark = sim.simulate_cv(
        vmin_V=-2.0,
        vmax_V=2.0,
        points=21,
        light_source=None,
    )

    assert np.array_equal(
        reference.forward.mean_occupation,
        explicit_dark.forward.mean_occupation,
    )

    assert np.array_equal(
        reference.backward.mean_occupation,
        explicit_dark.backward.mean_occupation,
    )

    assert reference.memory_window_V == explicit_dark.memory_window_V
    
def test_illuminated_cv_contains_optical_diagnostics():
    _, sim = make_simulator()

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    out = sim.simulate_cv(
        vmin_V=-2.0,
        vmax_V=2.0,
        points=21,
        light_source=source,
        photo_config=PhotoTransitionConfig(
            photo_capture_efficiency=1.0e-7,
        ),
    )

    assert np.all(
        out.forward.absorbed_photon_flux_m2_s > 0.0
    )

    assert np.all(
        out.backward.absorbed_photon_flux_m2_s > 0.0
    )

    assert np.all(
        out.forward.photo_transition_rate_s > 0.0
    )

    assert np.all(
        out.backward.photo_transition_rate_s > 0.0
    )
    
    
def test_illumination_changes_cv_occupancy():
    _, sim = make_simulator()

    dark = sim.simulate_cv(
        vmin_V=-2.0,
        vmax_V=2.0,
        points=21,
    )

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    illuminated = sim.simulate_cv(
        vmin_V=-2.0,
        vmax_V=2.0,
        points=21,
        light_source=source,
        photo_config=PhotoTransitionConfig(
            photo_capture_efficiency=1.0e-7,
        ),
    )

    assert np.any(
        illuminated.forward.mean_occupation
        != dark.forward.mean_occupation
    )

    assert np.any(
        illuminated.backward.mean_occupation
        != dark.backward.mean_occupation
    )
    
    
def test_cv_optical_sweep_shapes_are_consistent():
    _, sim = make_simulator()

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    points = 17

    out = sim.simulate_cv(
        vmin_V=-2.0,
        vmax_V=2.0,
        points=points,
        light_source=source,
        photo_config=PhotoTransitionConfig(
            photo_capture_efficiency=1.0e-7,
        ),
    )

    assert out.forward.voltages_V.shape == (points,)
    assert out.backward.voltages_V.shape == (points,)

    assert out.forward.photo_transition_rate_s.shape == (points,)
    assert out.backward.photo_transition_rate_s.shape == (points,)