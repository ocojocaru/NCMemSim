import numpy as np
import pytest

from ncmemsim import DeviceBuilder, DeviceState, PhysicsModel, SimulationConfig, Simulator, make_ge, make_gesn

@pytest.mark.parametrize("n_fgs", [1, 2, 3])
def test_empty_state_tracks_device_geometry(n_fgs):
    device = DeviceBuilder.v1(n_fgs=n_fgs, nc_material=[make_ge()] * n_fgs)
    state = DeviceState.empty_for_device(device)
    state.validate(device)
    assert len(state.floating_gates) == n_fgs
    positions = device.layer_positions_nm()
    for i, (fg, fg_state) in enumerate(zip(device.floating_gates(), state.floating_gates)):
        z0, z1 = positions[fg.name]
        assert fg_state.fg_id == i
        assert fg_state.layer_name == fg.name
        assert fg_state.z_center_nm == pytest.approx(0.5 * (z0 + z1))
        assert fg_state.P0.size == fg.grid_points


def test_state_copy_is_deep_and_preserves_metadata():
    device = DeviceBuilder.v2(n_fgs=2)
    state = DeviceState.empty_for_device(device)
    state.metadata["tag"] = "original"
    state.floating_gates[0].metadata["source"] = "test"
    copied = state.copy()
    copied.floating_gates[0].P0[0] = 0.5
    copied.metadata["tag"] = "copy"
    copied.floating_gates[0].metadata["source"] = "copy"
    assert state.floating_gates[0].P0[0] == 1.0
    assert state.metadata["tag"] == "original"
    assert state.floating_gates[0].metadata["source"] == "test"


def test_two_fgs_evolve_independently_and_expose_per_fg_outputs():
    device = DeviceBuilder.v1(
        n_fgs=2,
        nc_material=[make_ge(), make_gesn(0.10)],
        nc_diameter_nm=[3.0, 6.0],
        active_fraction=[0.22, 0.12],
        fg_thickness_nm=[12.0, 18.0],
    )
    sim = Simulator(
        device,
        PhysicsModel.default(),
        SimulationConfig(dwell_time_s=2e-5, internal_dt_s=1e-5),
    )
    state = DeviceState.empty_for_device(device)
    out = sim.relax_voltage(state, 2.0)
    assert out["qfg_by_fg_C_m2"].shape == (2,)
    assert out["mean_occupation_by_fg"].shape == (2,)
    assert out["field_mean_by_fg_V_m"].shape == (2,)
    assert len(out["rho_by_fg_C_m3"]) == 2
    assert out["qfg_C_m2"] == pytest.approx(np.sum(out["qfg_by_fg_C_m2"]))
    assert out["state"].time_s == pytest.approx(2e-5)
    assert [s.fg_id for s in out["state"].floating_gates] == [0, 1]
    assert [s.layer_name for s in out["state"].floating_gates] == ["FG1", "FG2"]
    assert all(s.z_center_nm is not None for s in out["state"].floating_gates)
    # Different geometry/material parameters must be represented by distinct states.
    assert not np.isclose(
        out["mean_occupation_by_fg"][0],
        out["mean_occupation_by_fg"][1],
        rtol=1e-5,
        atol=0.0,
    )



def test_three_fg_sweep_shapes_and_probability_normalization():
    device = DeviceBuilder.v2(
        n_fgs=3,
        nc_material=[make_ge(), make_gesn(0.02), make_gesn(0.10)],
        nc_diameter_nm=[3.0, 5.0, 7.0],
        active_fraction=[0.22, 0.18, 0.12],
    )
    for fg in device.floating_gates():
        fg.grid_points = 7
    sim = Simulator(
        device,
        config=SimulationConfig(dwell_time_s=1e-5, internal_dt_s=1e-5),
    )
    result = sim.run_sweep([-1.0, 0.0, 1.0])
    assert result.qfg_by_fg_C_m2.shape == (3, 3)
    assert result.mean_occupation_by_fg.shape == (3, 3)
    assert result.field_mean_by_fg_V_m.shape == (3, 3)
    result.final_state.validate(device)
    for fg_state in result.final_state.floating_gates:
        assert np.allclose(fg_state.P0 + fg_state.P1 + fg_state.P2, 1.0)


def test_state_device_count_mismatch_is_rejected():
    one_fg = DeviceBuilder.v1(1)
    two_fg = DeviceBuilder.v1(2)
    state = DeviceState.empty_for_device(one_fg)
    with pytest.raises(ValueError, match="count mismatch"):
        state.validate(two_fg)
