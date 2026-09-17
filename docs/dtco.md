# Design-space exploration and DTCO

## Phase G scope

NCMemSim v0.12.0 introduces a deterministic design-space exploration layer on
top of the validated v0.11.0 simulation, fitting, and calibration baseline.

The DTCO layer is designed to expose explicit trade-offs. It does not define a
single opaque optimum and does not alter the scientific provenance of
underlying model parameters.

## G1a: specification core

The first Phase G checkpoint defines experiment identity before any sweep
execution is implemented.

`ParameterBinding` identifies a target by a top-level scope and semantic path
segments. The current scopes are `device`, `operating`, and `model`.

A binding is declarative in G1a. Resolution and application of a binding to a
copied device or operating configuration are intentionally deferred to a later
G1 checkpoint.

`DesignVariable` defines a stable name, one binding, an explicitly ordered
finite domain, scientific role, explicit unit for numeric variables (`1` for
dimensionless values), and optional `ParameterProvenance`.

The declared value order is significant because it will define deterministic
sweep-axis ordering in G2.

`ExperimentSpec` records the experiment name, canonical hash of the exact base
device, optional base-device name, ordered design-variable definitions,
optional description, schema version, and deterministic experiment hash.

## Example

```python
from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (
    BindingScope,
    DesignVariable,
    DesignVariableRole,
    ExperimentSpec,
    ParameterBinding,
)

device = DeviceBuilder.v2(n_fgs=1)

diameter = DesignVariable(
    name="fg1_nc_diameter",
    binding=ParameterBinding(
        scope=BindingScope.DEVICE,
        path=("layers", "FG1", "nc_diameter_nm"),
    ),
    values=(4.0, 5.0, 6.0),
    role=DesignVariableRole.GEOMETRY,
    unit="nm",
)

spec = ExperimentSpec.from_device(
    name="diameter-study",
    device=device,
    variables=(diameter,),
)

print(spec.base_device_hash)
print(spec.experiment_hash)
print(spec.design_point_count)
```

G1a does **not** yet modify the device, generate Cartesian design points, run
simulations, compute objectives, or perform Pareto analysis.


## G1b: controlled device-binding application

G1b adds mutation semantics for **device-scope bindings only**. Application is
copy-on-write: the supplied base device is validated, one deep copy is created,
bindings are resolved through a strict allow-list, target types are checked,
all assignments are applied to the copy, and the complete candidate device is
validated before it is returned.

The base device is never modified, including when binding resolution or
post-application validation fails.

Supported G1b bindings include top-level `gate_work_function_eV`,
`substrate_doping_m3`, and `temperature_K`; `thickness_nm` for named layers;
and for floating-gate layers: `thickness_nm`, `nc_diameter_nm`,
`nc_volume_fraction`, `electrically_active_fraction`, and `grid_points`.

The DTCO base-device hash includes the complete material definitions attached
to every layer in addition to the established `Device.to_dict()` payload.
This prevents physically distinct material models from aliasing the same
experiment identity when their names or composition labels are unchanged.

`spatial_profile` is intentionally not bindable in G1b because non-uniform
profile semantics are not yet explicitly validated by the current model.

Nested material mutation is intentionally not supported in G1b. GeSn
composition must later use a material-aware replacement/factory path so that
composition-dependent material properties remain internally consistent.

`apply_experiment_design_point()` additionally requires the supplied base
device to match the recorded base-device hash, assignment keys to match the
experiment variables exactly, every value to belong to its declared domain,
and all variables to use `BindingScope.DEVICE`.
