import numpy as np

from ncmemsim import DeviceBuilder, DeviceState, PhysicsModel, Simulator
from ncmemsim.fieldsolver import FieldSolver1D
from ncmemsim.transport import TransportConfig, TransportEngine, TunnelNetwork


def test_network_has_adjacent_fg_and_substrate_links():
    device = DeviceBuilder.v1(3)
    network = TunnelNetwork.from_device(device)
    assert [link.kind for link in network.links] == ["inter_fg", "inter_fg", "substrate"]
    assert network.links[0].left_fg_index == 0
    assert network.links[0].right_fg_index == 1
    assert network.links[1].left_fg_index == 1
    assert network.links[1].right_fg_index == 2
    assert network.links[2].left_fg_index == 2
    assert network.links[2].right_fg_index is None
    assert all(link.length_m > 0 for link in network.links)


def test_single_fg_has_only_substrate_diagnostic_link():
    device = DeviceBuilder.v2(1)
    network = TunnelNetwork.from_device(device)
    assert len(network.links) == 1
    assert network.links[0].kind == "substrate"


def test_inter_fg_step_conserves_total_electron_sheet_density():
    device = DeviceBuilder.v2(2, inter_fg_sio2_nm=1.0)
    physics = PhysicsModel.default()
    physics.transport = TransportEngine(
        physics.tunneling,
        TransportConfig(
            attempt_frequency_Hz=1e13,
            default_barrier_eV=0.25,
            max_transfer_fraction_per_step=0.5,
        ),
    )
    state = DeviceState.empty_for_device(device)
    # Load the gate-side FG and leave the substrate-side FG empty.
    s0 = state.floating_gates[0]
    s0.P0[:] = 0.0
    s0.P1[:] = 1.0
    s0.P2[:] = 0.0
    profile = FieldSolver1D().solve(device, 4.0, np.zeros(2))

    def total_electrons(st):
        total = 0.0
        for fg, fg_state in zip(device.floating_gates(), st.floating_gates):
            x, dx = physics.occupancy.grid(fg)
            n_sheet = np.sum(physics.occupancy.density_profile(fg, x)) * dx
            total += 2.0 * fg_state.mean_normalized_occupation * n_sheet
        return total

    before = total_electrons(state)
    after, result = physics.transport.step(
        device, state, profile, physics.occupancy, 1e-6
    )
    assert np.isclose(total_electrons(after), before, rtol=1e-12, atol=1e-3)
    assert result.inter_fg_fluxes_m2_s.shape == (1,)
    assert after.floating_gates[0].mean_normalized_occupation < state.floating_gates[0].mean_normalized_occupation
    assert after.floating_gates[1].mean_normalized_occupation > state.floating_gates[1].mean_normalized_occupation


def test_transport_step_preserves_probability_normalization():
    device = DeviceBuilder.v1(3, inter_fg_sio2_nm=1.0, inter_fg_hfo2_nm=1.0)
    physics = PhysicsModel.default()
    state = DeviceState.empty_for_device(device)
    state.floating_gates[0].P0[:] = 0.0
    state.floating_gates[0].P1[:] = 0.2
    state.floating_gates[0].P2[:] = 0.8
    profile = FieldSolver1D().solve(device, 3.0, np.zeros(3))
    updated, _ = physics.transport.step(device, state, profile, physics.occupancy, 1e-5)
    updated.validate(device)


def test_simulator_exposes_transport_diagnostics():
    device = DeviceBuilder.v1(3)
    simulator = Simulator(device)
    out = simulator.relax_voltage(DeviceState.empty_for_device(device), 1.0, dwell_time_s=0.0)
    assert len(out["transport_link_results"]) == 3
    assert out["inter_fg_flux_by_link_m2_s"].shape == (2,)
    assert out["transport_transmission_by_link"].shape == (3,)
    assert out["transport_net_flux_by_fg_m2_s"].shape == (3,)


def test_sweep_contains_link_histories():
    device = DeviceBuilder.v2(2)
    result = Simulator(device).run_sweep(np.asarray([-1.0, 0.0, 1.0]))
    assert result.inter_fg_flux_by_link_m2_s.shape == (3, 1)
    assert result.transport_transmission_by_link.shape == (3, 2)
    assert len(result.transport_link_ids) == 2
