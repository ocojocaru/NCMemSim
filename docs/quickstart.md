# Quick start

## 1. Build a device

```python
from ncmemsim import DeviceBuilder, make_ge, make_gesn

device = DeviceBuilder.v1(
    n_fgs=3,
    nc_material=[make_ge(), make_gesn(0.02), make_gesn(0.10)],
    fg_thickness_nm=[12.0, 15.0, 18.0],
    nc_diameter_nm=[3.0, 5.0, 7.0],
    active_fraction=[0.22, 0.18, 0.12],
)
```

`DeviceBuilder.v1` and `DeviceBuilder.v2` accept scalar values or per-FG sequences for supported floating-gate parameters.

## 2. Create a state

```python
from ncmemsim import DeviceState

state = DeviceState.empty_for_device(device)
```

Each `FloatingGateState` contains probability arrays `P0`, `P1`, and `P2`. The state also records its FG identifier, layer name, and geometric center.

## 3. Relax at a gate voltage

```python
from ncmemsim import SimulationConfig, Simulator

simulator = Simulator(
    device,
    config=SimulationConfig(dwell_time_s=2e-5, internal_dt_s=1e-5),
)
output = simulator.relax_voltage(state, gate_voltage_V=2.0)

print(output["qfg_C_m2"])
print(output["qfg_by_fg_C_m2"])
print(output["delta_vfb_V"])
print(output["mean_occupation_by_fg"])
```

The output dictionary also contains local electrostatic fields, a `FieldProfile`, transport diagnostics, and the updated `DeviceState`.

## 4. Inspect the field profile

```python
profile = output["field_profile"]
print(profile.z_nm)
print(profile.potential_V)
print(profile.electric_field_V_m)
print(profile.local_potentials_by_fg_V)
print(profile.local_fields_by_fg_V_m)
```

## 5. Run retention

```python
from ncmemsim import RetentionConfig

retention = simulator.simulate_retention(
    output["state"],
    RetentionConfig(
        total_time_s=1e4,
        initial_dt_s=1e-6,
        maximum_dt_s=100.0,
        output_points=61,
    ),
)

print(retention.time_s)
print(retention.qfg_C_m2)
print(retention.mean_occupation_by_fg)
print(retention.total_charge_retention_fraction)
```

## 6. Validate and record provenance

```python
from ncmemsim import build_reproducibility_manifest, validate_simulation

report = validate_simulation(device, output["state"], output)
report.raise_for_errors()

manifest = build_reproducibility_manifest(
    device,
    simulation_config={"gate_voltage_V": 2.0},
)
print(manifest["device_hash"])
print(manifest["simulation_hash"])
```

## Executable examples

The `examples/` directory contains phase-oriented scripts:

- `build_devices.py`
- `phase_b_regression.py`
- `phase_c_material_framework.py`
- `phase_d1_multistate.py`
- `phase_d2_electrostatic_coupling.py`
- `phase_d3_local_field_profile.py`
- `phase_d4_inter_fg_transport.py`
- `phase_d5_retention.py`
- `phase_d6_validation.py`
