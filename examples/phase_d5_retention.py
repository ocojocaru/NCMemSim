"""Phase D5: adaptive retention and inter-FG charge redistribution."""
import numpy as np

from ncmemsim import DeviceBuilder, DeviceState, RetentionConfig, Simulator


device = DeviceBuilder.v2(3, inter_fg_sio2_nm=1.5)
simulator = Simulator(device)
state = DeviceState.empty_for_device(device)

# Example programmed state: progressively lower occupation toward substrate.
for fg_state, occupation in zip(state.floating_gates, (0.75, 0.45, 0.20)):
    fg_state.P0[:] = 1.0 - occupation
    fg_state.P1[:] = occupation
    fg_state.P2[:] = 0.0

result = simulator.simulate_retention(
    state,
    RetentionConfig(
        total_time_s=1.0e4,
        initial_dt_s=1.0e-6,
        maximum_dt_s=100.0,
        output_points=61,
    ),
)

print("samples:", result.time_s.size)
print("final time [s]:", result.time_s[-1])
print("initial/final charge [C m^-2]:", result.qfg_C_m2[[0, -1]])
print("final occupation by FG:", result.mean_occupation_by_fg[-1])
print("quasi-equilibrium reached:", result.quasi_equilibrium_reached)
