import numpy as np
import pytest

from ncmemsim import DeviceBuilder, DeviceState, ElectrostaticsEngine, FieldSolver1D, SimulationConfig, Simulator, make_ge


def test_uncharged_profile_integrates_to_applied_voltage():
    device = DeviceBuilder.v1(n_fgs=3, nc_material=make_ge())
    profile = FieldSolver1D().solve(device, 2.75)
    assert profile.total_voltage_V == pytest.approx(2.75, rel=1e-13, abs=1e-13)
    assert profile.z_nm[0] == 0.0
    assert profile.z_nm[-1] == pytest.approx(device.total_thickness_nm())


def test_profile_contains_one_local_value_per_fg():
    device = DeviceBuilder.v1(n_fgs=3, nc_material=make_ge())
    profile = FieldSolver1D().solve(device, 1.0)
    assert profile.local_fields_by_fg_V_m.shape == (3,)
    assert profile.local_potentials_by_fg_V.shape == (3,)
    assert np.all(np.diff(profile.local_potentials_by_fg_V) > 0.0)


def test_zero_charge_matches_legacy_layer_fields():
    device = DeviceBuilder.v2(n_fgs=2, nc_material=make_ge())
    engine = ElectrostaticsEngine()
    profile = engine.field_profile(device, 1.25, np.zeros(2))
    legacy = engine.local_fields_V_m(device, 1.25)
    for field, layer_name in zip(profile.electric_field_V_m, profile.segment_layer_names):
        assert field == pytest.approx(legacy[layer_name], rel=1e-13)


def test_sheet_charge_changes_displacement_across_fg():
    device = DeviceBuilder.v1(n_fgs=2, nc_material=make_ge())
    q = np.array([-2.0e-4, 0.0])
    profile = FieldSolver1D().solve(device, 0.0, q)
    fg1_segments = [i for i, name in enumerate(profile.segment_layer_names) if name == "FG1"]
    assert len(fg1_segments) == 2
    assert profile.electric_field_V_m[fg1_segments[1]] != pytest.approx(
        profile.electric_field_V_m[fg1_segments[0]]
    )


def test_interpolation_helpers_return_profile_values():
    device = DeviceBuilder.v1(n_fgs=1, nc_material=make_ge())
    profile = FieldSolver1D().solve(device, 2.0)
    z = profile.z_nm[len(profile.z_nm) // 2]
    assert profile.potential_at_nm(z) == pytest.approx(
        profile.potential_V[len(profile.z_nm) // 2]
    )
    with pytest.raises(ValueError):
        profile.field_at_nm(-1.0)


def test_simulator_exposes_profile_and_updates_fg_state():
    device = DeviceBuilder.v1(n_fgs=3, nc_material=make_ge())
    simulator = Simulator(device, config=SimulationConfig(dwell_time_s=1e-5, internal_dt_s=1e-5))
    out = simulator.relax_voltage(DeviceState.empty_for_device(device), 1.5)
    profile = out["field_profile"]
    assert profile.total_voltage_V == pytest.approx(out["veff_V"])
    assert np.allclose(
        out["electrostatic_local_potential_by_fg_V"],
        profile.local_potentials_by_fg_V,
    )
    for index, fg_state in enumerate(out["state"].floating_gates):
        assert fg_state.local_field_V_m == pytest.approx(profile.local_fields_by_fg_V_m[index])
        assert fg_state.local_potential_V == pytest.approx(profile.local_potentials_by_fg_V[index])


def test_single_fg_regression_uses_same_kinetic_path():
    device = DeviceBuilder.v1(n_fgs=1, nc_material=make_ge())
    simulator = Simulator(device, config=SimulationConfig(dwell_time_s=1e-5, internal_dt_s=1e-5))
    out = simulator.relax_voltage(DeviceState.empty_for_device(device), 2.0)
    assert out["field_mean_by_fg_V_m"].shape == (1,)
    assert out["electrostatic_local_field_by_fg_V_m"].shape == (1,)
