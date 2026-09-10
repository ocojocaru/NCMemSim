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


def make_simulator():
    device = DeviceBuilder.v1(
        n_fgs=1,
        nc_material=[make_gesn(0.08)],
        nc_diameter_nm=[5.0],
        active_fraction=[1.0],
        fg_thickness_nm=[15.0],
    )

    device.floating_gates()[0].grid_points = 7

    sim = Simulator(
        device,
        PhysicsModel.default(),
        SimulationConfig(
            dwell_time_s=1.0e-3,
            internal_dt_s=1.0e-5,
        ),
    )

    return device, sim
    
    
def test_no_light_source_preserves_existing_behavior():
    device, sim = make_simulator()

    initial = DeviceState.empty_for_device(device)

    reference = sim.relax_voltage(
        initial,
        gate_voltage_V=2.0,
    )

    explicit_dark = sim.relax_voltage(
        initial,
        gate_voltage_V=2.0,
        light_source=None,
    )

    assert np.array_equal(
        reference["state"].floating_gates[0].P0,
        explicit_dark["state"].floating_gates[0].P0,
    )
    assert np.array_equal(
        reference["state"].floating_gates[0].P1,
        explicit_dark["state"].floating_gates[0].P1,
    )
    assert np.array_equal(
        reference["state"].floating_gates[0].P2,
        explicit_dark["state"].floating_gates[0].P2,
    )

    assert reference["qfg_C_m2"] == explicit_dark["qfg_C_m2"]
    assert reference["mean_occupation"] == explicit_dark["mean_occupation"]
    assert reference["veff_V"] == explicit_dark["veff_V"]
    
    
def test_light_increases_simulator_programming():
    device, sim = make_simulator()

    initial = DeviceState.empty_for_device(device)

    dark = sim.relax_voltage(
        initial,
        gate_voltage_V=2.0,
    )

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    illuminated = sim.relax_voltage(
        initial,
        gate_voltage_V=2.0,
        light_source=source,
        photo_config=PhotoTransitionConfig(
            photo_capture_efficiency=1.0e-7,
        ),
    )

    assert (
        illuminated["mean_occupation"]
        > dark["mean_occupation"]
    )

    assert (
        illuminated["qfg_C_m2"]
        > dark["qfg_C_m2"]
    )
    
    
def test_disabled_light_source_recovers_dark_simulation():
    device, sim = make_simulator()

    initial = DeviceState.empty_for_device(device)

    dark = sim.relax_voltage(
        initial,
        gate_voltage_V=2.0,
    )

    source = LightSource(
        name="disabled",
        source_type="laser",
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
        enabled=False,
    )

    illuminated = sim.relax_voltage(
        initial,
        gate_voltage_V=2.0,
        light_source=source,
    )

    assert np.allclose(
        illuminated["state"].floating_gates[0].P0,
        dark["state"].floating_gates[0].P0,
    )
    assert np.allclose(
        illuminated["state"].floating_gates[0].P1,
        dark["state"].floating_gates[0].P1,
    )
    assert np.allclose(
        illuminated["state"].floating_gates[0].P2,
        dark["state"].floating_gates[0].P2,
    )
    
    
def test_optical_programming_updates_electrostatic_state():
    device, sim = make_simulator()

    initial = DeviceState.empty_for_device(device)

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    out = sim.relax_voltage(
        initial,
        gate_voltage_V=2.0,
        light_source=source,
        photo_config=PhotoTransitionConfig(
            photo_capture_efficiency=1.0e-7,
        ),
    )

    fg_state = out["state"].floating_gates[0]

    assert fg_state.mean_normalized_occupation > 0.0
    assert out["qfg_C_m2"] > 0.0

    assert fg_state.local_field_V_m is not None
    assert fg_state.local_potential_V is not None

    out["state"].validate(device)
    
    
def test_optical_relaxation_advances_requested_time():
    device, sim = make_simulator()

    initial = DeviceState.empty_for_device(device)

    source = LightSource.laser(
        wavelength_nm=1550.0,
        power_density_W_m2=1000.0,
    )

    out = sim.relax_voltage(
        initial,
        gate_voltage_V=2.0,
        dwell_time_s=2.0e-4,
        internal_dt_s=1.0e-5,
        light_source=source,
        photo_config=PhotoTransitionConfig(
            photo_capture_efficiency=1.0e-7,
        ),
    )

    assert out["state"].time_s == 2.0e-4