import numpy as np
import pytest

from ncmemsim import (
    CompactCouplingModel,
    DeviceBuilder,
    DeviceState,
    ElectrostaticsEngine,
    SimulationConfig,
    Simulator,
)


def test_single_fg_coupling_preserves_legacy_flatband_relation():
    device = DeviceBuilder.v1(1)
    engine = ElectrostaticsEngine()
    q = 2.5e-4
    cox = engine.equivalent_capacitance(device)
    vfb0 = engine.flatband_zero(device)
    result = engine.evaluate(device, 1.0, q)
    assert result.coupling.sensitivity_factors == pytest.approx([1.0])
    assert result.delta_vfb_V == pytest.approx(-q / cox, rel=1e-14)
    assert result.vfb_V == pytest.approx(vfb0 - q / cox, rel=1e-14)


def test_multifg_sensitivity_increases_towards_substrate():
    device = DeviceBuilder.v1(3)
    beta = CompactCouplingModel().sensitivity_factors(device)
    assert beta.shape == (3,)
    assert np.all(beta > 0.0)
    assert np.all(beta < 1.0)
    assert np.all(np.diff(beta) > 0.0)


def test_delta_vfb_is_sum_of_per_fg_contributions():
    device = DeviceBuilder.v2(3)
    engine = ElectrostaticsEngine()
    q = np.asarray([1.0e-4, 2.0e-4, 3.0e-4])
    out = engine.evaluate(device, 0.5, q)
    assert out.delta_vfb_V == pytest.approx(np.sum(out.delta_vfb_by_fg_V))
    expected = -out.coupling.coefficients_m2_F * q
    assert out.delta_vfb_by_fg_V == pytest.approx(expected)
    assert out.coupling.matrix_m2_F.shape == (3, 3)
    assert np.allclose(out.coupling.matrix_m2_F, np.diag(np.diag(out.coupling.matrix_m2_F)))


def test_local_field_solver_recovers_series_dielectric_field_without_charge():
    device = DeviceBuilder.v1(2)
    engine = ElectrostaticsEngine()
    fields = engine.local_fields_at_fgs_V_m(device, 2.0, np.zeros(2))
    # Both FGs use HfO2 matrices, so in the charge-free series stack their
    # local fields must be identical.
    assert fields[0] == pytest.approx(fields[1], rel=1e-14)
    assert np.all(fields > 0.0)


def test_sheet_charge_changes_fields_on_opposite_sides():
    device = DeviceBuilder.v2(2)
    engine = ElectrostaticsEngine()
    neutral = engine.local_fields_at_fgs_V_m(device, 1.0, np.zeros(2))
    charged = engine.local_fields_at_fgs_V_m(device, 1.0, np.asarray([2e-4, 0.0]))
    assert not np.allclose(neutral, charged, rtol=1e-8, atol=0.0)
    assert charged[0] != pytest.approx(charged[1])


def test_simulator_exposes_d2_outputs_and_sweep_shapes():
    device = DeviceBuilder.v1(3)
    for fg in device.floating_gates():
        fg.grid_points = 5
    sim = Simulator(device, config=SimulationConfig(dwell_time_s=1e-5, internal_dt_s=1e-5))
    out = sim.relax_voltage(DeviceState.empty_for_device(device), 1.5)
    assert out["delta_vfb_by_fg_V"].shape == (3,)
    assert out["coupling_sensitivity_factors"].shape == (3,)
    assert out["coupling_matrix_m2_F"].shape == (3, 3)
    assert out["electrostatic_local_field_by_fg_V_m"].shape == (3,)
    assert out["delta_vfb_V"] == pytest.approx(np.sum(out["delta_vfb_by_fg_V"]))

    sweep = sim.run_sweep([-1.0, 0.0, 1.0])
    assert sweep.delta_vfb_V.shape == (3,)
    assert sweep.delta_vfb_by_fg_V.shape == (3, 3)
    assert sweep.electrostatic_local_field_by_fg_V_m.shape == (3, 3)
    assert sweep.coupling_sensitivity_factors.shape == (3,)
