"""Minimal executable example for the Phase-D1 multi-state API."""

from pathlib import Path
import sys

# Permit direct execution from a source checkout without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ncmemsim import DeviceBuilder, DeviceState, SimulationConfig, Simulator, make_ge, make_gesn

device = DeviceBuilder.v1(
    n_fgs=3,
    nc_material=[make_ge(), make_gesn(0.02), make_gesn(0.10)],
    nc_diameter_nm=[3.0, 5.0, 7.0],
    active_fraction=[0.22, 0.18, 0.12],
)
state = DeviceState.empty_for_device(device)
simulator = Simulator(
    device,
    config=SimulationConfig(dwell_time_s=2e-5, internal_dt_s=1e-5),
)
result = simulator.relax_voltage(state, gate_voltage_V=2.0)

print("Total QFG [C/m²]:", result["qfg_C_m2"])
for fg_state, charge, occupation in zip(
    result["state"].floating_gates,
    result["qfg_by_fg_C_m2"],
    result["mean_occupation_by_fg"],
):
    print(
        fg_state.fg_id,
        fg_state.layer_name,
        fg_state.z_center_nm,
        charge,
        occupation,
    )
