"""Phase D4 example: inspect the tunnelling network and inter-FG fluxes."""

import numpy as np

from ncmemsim import DeviceBuilder, DeviceState, Simulator


device = DeviceBuilder.v1(3)
simulator = Simulator(device)
state = DeviceState.empty_for_device(device)

# Seed charge in FG1 so that the redistribution diagnostics are non-zero.
state.floating_gates[0].P0[:] = 0.0
state.floating_gates[0].P1[:] = 1.0
state.floating_gates[0].P2[:] = 0.0

result = simulator.relax_voltage(state, gate_voltage_V=2.0, dwell_time_s=1e-4)

print("Transport links:", result["transport_link_ids"])
print("Transmissions:", result["transport_transmission_by_link"])
print("Inter-FG electron fluxes [m^-2 s^-1]:", result["inter_fg_flux_by_link_m2_s"])
print("Net flux per FG [m^-2 s^-1]:", result["transport_net_flux_by_fg_m2_s"])
print("Mean occupations:", result["mean_occupation_by_fg"])
