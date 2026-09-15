from __future__ import annotations

import numpy as np
import pytest

from ncmemsim import DeviceState, RetentionConfig, Simulator, make_v53_reference_device
from ncmemsim.kinetics import OccupancyEngine, RateArrays
from ncmemsim.state import FloatingGateState


def _rates(n: int) -> RateArrays:
    zeros = np.zeros(n, dtype=float)
    return RateArrays(
        r01=np.full(n, 2.0e6),
        r12=np.full(n, 8.0e5),
        r21=np.full(n, 3.0e5),
        r10=np.full(n, 5.0e5),
        tprog=zeros.copy(),
        terase=zeros.copy(),
        field_V_m=zeros.copy(),
    )


def _local_state() -> FloatingGateState:
    state = FloatingGateState.empty(3)
    state.P0[:] = [0.2, 0.0, 0.7]
    state.P1[:] = [0.5, 1.0, 0.2]
    state.P2[:] = [0.3, 0.0, 0.1]
    return state


def _charged_state(device, kind: str) -> DeviceState:
    state = DeviceState.empty_for_device(device)
    for fg_state in state.floating_gates:
        if kind == "P1":
            fg_state.P0[:] = 0.0
            fg_state.P1[:] = 1.0
            fg_state.P2[:] = 0.0
        elif kind == "P2":
            fg_state.P0[:] = 0.0
            fg_state.P1[:] = 0.0
            fg_state.P2[:] = 1.0
        else:
            raise ValueError(kind)
    state.validate(device)
    return state


def test_backward_euler_large_step_preserves_probability_simplex():
    updated = OccupancyEngine.step_backward_euler(_local_state(), _rates(3), 100.0)
    probabilities = np.stack((updated.P0, updated.P1, updated.P2), axis=1)
    assert np.all(np.isfinite(probabilities))
    assert np.all(probabilities >= 0.0)
    np.testing.assert_allclose(probabilities.sum(axis=1), 1.0, rtol=0.0, atol=5e-15)


def test_backward_euler_zero_duration_preserves_state():
    state = _local_state()
    updated = OccupancyEngine.step_backward_euler(state, _rates(3), 0.0)
    np.testing.assert_array_equal(updated.P0, state.P0)
    np.testing.assert_array_equal(updated.P1, state.P1)
    np.testing.assert_array_equal(updated.P2, state.P2)
    assert updated is not state


@pytest.mark.parametrize("dt_s", [-1.0, float("nan"), float("inf")])
def test_backward_euler_rejects_invalid_time_step(dt_s):
    with pytest.raises(ValueError, match="finite and non-negative"):
        OccupancyEngine.step_backward_euler(_local_state(), _rates(3), dt_s)


def test_backward_euler_matches_explicit_small_step_limit():
    state = _local_state()
    rates = _rates(3)
    explicit = OccupancyEngine.step(state, rates, 1.0e-13)
    implicit = OccupancyEngine.step_backward_euler(state, rates, 1.0e-13)
    np.testing.assert_allclose(implicit.P0, explicit.P0, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(implicit.P1, explicit.P1, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(implicit.P2, explicit.P2, rtol=0.0, atol=1e-12)


def test_relax_voltage_default_remains_explicit_euler():
    device = make_v53_reference_device(grid_points=5)
    simulator = Simulator(device)
    state = _charged_state(device, "P1")
    default = simulator.relax_voltage(state, 1.0, dwell_time_s=1e-6, internal_dt_s=1e-6)
    explicit = simulator.relax_voltage(
        state,
        1.0,
        dwell_time_s=1e-6,
        internal_dt_s=1e-6,
        occupancy_integrator="explicit_euler",
    )
    assert default["qfg_C_m2"] == explicit["qfg_C_m2"]
    for lhs, rhs in zip(default["state"].floating_gates, explicit["state"].floating_gates):
        np.testing.assert_array_equal(lhs.P0, rhs.P0)
        np.testing.assert_array_equal(lhs.P1, rhs.P1)
        np.testing.assert_array_equal(lhs.P2, rhs.P2)


def test_relax_voltage_rejects_unknown_integrator():
    device = make_v53_reference_device(grid_points=3)
    with pytest.raises(ValueError, match="occupancy_integrator"):
        Simulator(device).relax_voltage(
            DeviceState.empty_for_device(device),
            0.0,
            dwell_time_s=0.0,
            internal_dt_s=1e-6,
            occupancy_integrator="unknown",
        )


def test_retention_defaults_to_backward_euler():
    assert RetentionConfig().occupancy_integrator == "backward_euler"


def test_retention_config_rejects_unknown_integrator():
    with pytest.raises(ValueError, match="occupancy_integrator"):
        RetentionConfig(occupancy_integrator="unknown").validate()


@pytest.mark.parametrize("kind", ["P1", "P2"])
def test_long_time_retention_has_no_late_vertex_toggling(kind):
    device = make_v53_reference_device(grid_points=5)
    result = Simulator(device).simulate_retention(
        _charged_state(device, kind),
        RetentionConfig(
            gate_voltage_V=0.0,
            total_time_s=100.0,
            initial_dt_s=1e-6,
            maximum_dt_s=100.0,
            output_points=41,
        ),
    )
    fraction = result.total_charge_retention_fraction
    late = fraction[result.time_s >= 1.0]
    assert np.isclose(result.time_s[-1], 100.0)
    assert np.all(np.isfinite(fraction))
    assert late.size >= 2
    assert np.max(np.abs(np.diff(late))) < 1e-8


@pytest.mark.parametrize("kind", ["P1", "P2"])
def test_long_time_retention_stable_under_step_refinement(kind):
    device = make_v53_reference_device(grid_points=5)
    state = _charged_state(device, kind)
    coarse = Simulator(device).simulate_retention(
        state,
        RetentionConfig(
            gate_voltage_V=0.0,
            total_time_s=100.0,
            initial_dt_s=1e-6,
            maximum_dt_s=100.0,
            output_points=41,
        ),
    )
    fine = Simulator(device).simulate_retention(
        state,
        RetentionConfig(
            gate_voltage_V=0.0,
            total_time_s=100.0,
            initial_dt_s=1e-6,
            maximum_dt_s=10.0,
            output_points=41,
        ),
    )
    np.testing.assert_allclose(coarse.time_s, fine.time_s, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(
        coarse.total_charge_retention_fraction,
        fine.total_charge_retention_fraction,
        rtol=1e-8,
        atol=1e-10,
    )
