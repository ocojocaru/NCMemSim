from ncmemsim import (
    DeviceBuilder,
    DeviceState,
    Simulator,
    build_reproducibility_manifest,
    validate_simulation,
)


device = DeviceBuilder.v2(3)
simulator = Simulator(device)
output = simulator.relax_voltage(
    DeviceState.empty_for_device(device),
    gate_voltage_V=2.0,
    dwell_time_s=2e-5,
    internal_dt_s=1e-5,
)
report = validate_simulation(device, output["state"], output)
report.raise_for_errors()
manifest = build_reproducibility_manifest(
    device,
    simulation_config={"gate_voltage_V": 2.0, "dwell_time_s": 2e-5},
)
print("validation passed:", report.passed)
print("device hash:", manifest["device_hash"])
print("simulation hash:", manifest["simulation_hash"])
