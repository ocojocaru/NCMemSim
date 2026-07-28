import numpy as np

from ncmemsim import DeviceBuilder, DeviceState, RetentionConfig, Simulator
from ncmemsim.kinetics import KineticsConfig, OccupancyEngine
from ncmemsim.transport import TransportConfig, TransportEngine


def loaded_state(device, occupations):
    state = DeviceState.empty_for_device(device)
    for fg_state, m in zip(state.floating_gates, occupations):
        fg_state.P0[:] = 1.0 - m
        fg_state.P1[:] = m
        fg_state.P2[:] = 0.0
    return state


def test_retention_result_shapes_and_final_time():
    device = DeviceBuilder.v2(2)
    result = Simulator(device).simulate_retention(
        loaded_state(device, (0.5, 0.2)),
        RetentionConfig(total_time_s=1e-5, initial_dt_s=1e-7, maximum_dt_s=1e-6, output_points=9),
    )
    assert np.isclose(result.time_s[0], 0.0)
    assert np.isclose(result.time_s[-1], 1e-5)
    assert result.qfg_by_fg_C_m2.shape == (result.time_s.size, 2)
    assert result.mean_occupation_by_fg.shape == (result.time_s.size, 2)
    assert result.delta_vfb_by_fg_V.shape == (result.time_s.size, 2)
    assert result.local_field_by_fg_V_m.shape == (result.time_s.size, 2)
    assert result.inter_fg_flux_by_link_m2_s.shape[0] == result.time_s.size
    result.final_state.validate(device)


def test_disabled_transport_preserves_internal_distribution_at_zero_bias_short_run():
    device = DeviceBuilder.v2(2)
    sim = Simulator(device)
    sim.physics.transport = TransportEngine(sim.physics.tunneling, TransportConfig(enabled=False))
    state = loaded_state(device, (0.7, 0.1))
    result = sim.simulate_retention(
        state,
        RetentionConfig(total_time_s=1e-12, initial_dt_s=1e-13, maximum_dt_s=1e-12, output_points=5),
    )
    assert np.allclose(result.mean_occupation_by_fg[-1], result.mean_occupation_by_fg[0], rtol=0, atol=1e-10)


def test_inter_fg_redistribution_conserves_total_charge_when_substrate_kinetics_negligible():
    device = DeviceBuilder.v2(2, inter_fg_sio2_nm=1.0)
    sim = Simulator(device)
    sim.physics.transport = TransportEngine(
        sim.physics.tunneling,
        TransportConfig(attempt_frequency_Hz=1e13, default_barrier_eV=0.25, max_transfer_fraction_per_step=0.2),
    )
    sim.physics.occupancy = OccupancyEngine(
        sim.physics.tunneling,
        KineticsConfig(nu0_Hz=0.0, nu1_Hz=0.0, nu2_Hz=0.0),
    )
    state = loaded_state(device, (0.9, 0.0))
    result = sim.simulate_retention(
        state,
        RetentionConfig(total_time_s=1e-7, initial_dt_s=1e-9, maximum_dt_s=1e-8, output_points=11),
    )
    assert result.mean_occupation_by_fg[-1, 0] < result.mean_occupation_by_fg[0, 0]
    assert result.mean_occupation_by_fg[-1, 1] > result.mean_occupation_by_fg[0, 1]
    assert np.isclose(result.qfg_C_m2[-1], result.qfg_C_m2[0], rtol=5e-4, atol=1e-12)


def test_retention_fraction_and_loss_are_complementary():
    device = DeviceBuilder.v1(1)
    result = Simulator(device).simulate_retention(
        loaded_state(device, (0.4,)),
        RetentionConfig(total_time_s=1e-8, initial_dt_s=1e-9, maximum_dt_s=1e-8, output_points=5),
    )
    assert np.allclose(result.total_charge_retention_fraction + result.charge_loss_fraction, 1.0)


def test_quasi_equilibrium_detection_can_stop_early():
    device = DeviceBuilder.v1(1)
    sim = Simulator(device)
    sim.physics.occupancy = OccupancyEngine(
        sim.physics.tunneling,
        KineticsConfig(nu0_Hz=0.0, nu1_Hz=0.0, nu2_Hz=0.0),
    )
    sim.physics.transport = TransportEngine(sim.physics.tunneling, TransportConfig(enabled=False))
    result = sim.simulate_retention(
        DeviceState.empty_for_device(device),
        RetentionConfig(
            total_time_s=1.0,
            initial_dt_s=1e-6,
            maximum_dt_s=1e-2,
            output_points=30,
            quasi_equilibrium_tolerance_C_m2_s=1e-30,
            quasi_equilibrium_steps=2,
            stop_at_quasi_equilibrium=True,
        ),
    )
    assert result.quasi_equilibrium_reached
    assert result.quasi_equilibrium_time_s is not None
    assert result.time_s[-1] < 1.0
