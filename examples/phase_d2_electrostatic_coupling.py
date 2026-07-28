"""Minimal Phase-D2 electrostatic-coupling example."""

from ncmemsim import DeviceBuilder, DeviceState, SimulationConfig, Simulator, make_ge, make_gesn


device = DeviceBuilder.v1(
    n_fgs=3,
    nc_material=[make_ge(), make_gesn(0.02), make_gesn(0.10)],
    fg_thickness_nm=[12.0, 15.0, 18.0],
)
simulator = Simulator(
    device,
    config=SimulationConfig(dwell_time_s=1e-5, internal_dt_s=1e-5),
)
result = simulator.relax_voltage(DeviceState.empty_for_device(device), 2.0)

print("Sensitivity factors:", result["coupling_sensitivity_factors"])
print("Charge by FG [C/m2]:", result["qfg_by_fg_C_m2"])
print("Delta VFB by FG [V]:", result["delta_vfb_by_fg_V"])
print("Total Delta VFB [V]:", result["delta_vfb_V"])
print("Local fields [V/m]:", result["electrostatic_local_field_by_fg_V_m"])
