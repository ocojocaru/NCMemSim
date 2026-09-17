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
