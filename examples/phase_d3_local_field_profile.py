"""Phase-D3 local electric-field and potential-profile example."""

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
profile = result["field_profile"]

print("z nodes [nm]:", profile.z_nm)
print("potential [V]:", profile.potential_V)
print("segment fields [V/m]:", profile.electric_field_V_m)
print("FG local potentials [V]:", profile.local_potentials_by_fg_V)
print("FG local fields [V/m]:", profile.local_fields_by_fg_V_m)
