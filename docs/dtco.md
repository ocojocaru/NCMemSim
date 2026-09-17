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


## G1c1: material-aware GeSn composition binding

GeSn composition is not applied by mutating `sn_fraction` directly on the
material object. The material is rebuilt through the existing `make_gesn()`
factory so composition-dependent dielectric, band-gap, affinity, effective-mass,
and program/erase barrier values remain internally consistent.

The supported semantic path is:

```text
("layers", "<FG name>", "nc_material", "sn_fraction")
```

G1c1 intentionally accepts only a canonical default `GeSnModel` material. A
custom GeSn parameterization is rejected because the current immutable
`NanocrystalMaterial` retains the derived material properties but not enough
information to reconstruct every original `GeSnParameterSet` input when the Sn
fraction changes. Silently falling back to the default parameter set would
destroy provenance and change the scientific model.

The original base device remains unchanged because material-aware composition
application uses the same copy-on-write path as the other device bindings.


## G1c2a: operating-variable binding primitives

G1c2a adds immutable operating-condition bindings for the existing electrical
and electro-optical pulse protocols. Bindings reconstruct frozen dataclasses
with `dataclasses.replace()` so the established protocol and light-source
validators remain authoritative.

Stable operating paths are:

```text
("program", "voltage_V")
("program", "time_s")
("program", "internal_dt_s")
("read", "voltage_V")
("optical", "wavelength_nm")
("optical", "power_density_W_m2")
```

The electrical paths apply both to `ProgramPulseReadProtocol` and to the
nested electrical protocol in `ElectroOpticalProgramPulseReadProtocol`.
Optical paths require the electro-optical protocol; wavelength variation is
restricted to LED and laser sources.

`photo_capture_efficiency` is deliberately not exposed as an operating
condition. The v0.11 semantics keep it separate from illumination conditions
because it is a fitted device/model parameter supplied at execution time.
Experiment-level operating-baseline identity and mixed device/operating point
application are deferred to G1c2b.


## G1c2b: operating-baseline identity and mixed experiment points

`ExperimentSpec.from_device()` can now optionally record an operating baseline
through `operating_protocol=`. The baseline identity hashes a canonical payload
containing both the supported protocol kind and its complete `to_dict()`
representation.

The operating identity is optional for device-only studies. When it is absent,
the new operating fields are omitted from `ExperimentSpec.to_dict()`, preserving
the existing device-only experiment serialization and experiment hashes.
Experiments containing `BindingScope.OPERATING` variables, however, must record
an operating baseline so that the experiment definition is complete.

`apply_experiment_point()` validates both the base-device and base-operating
identities, requires an exact assignment for every declared variable, checks
each value against its declared domain, and then applies device and operating
bindings through their existing copy-on-write/immutable mechanisms.

`BindingScope.MODEL` remains outside G1c2b. In particular,
`photo_capture_efficiency` is still treated as a fitted model/device parameter,
not as an experimental illumination condition.

## G1d: binding/unit contracts

Known numeric DEVICE and OPERATING bindings require their exact canonical unit
when constructing a `DesignVariable`. No aliases or unit conversions are applied,
and categorical domains for these bindings are rejected immediately.

| Scope | Path | Unit |
| --- | --- | --- |
| DEVICE | `gate_work_function_eV` | `eV` |
| DEVICE | `substrate_doping_m3` | `m^-3` |
| DEVICE | `temperature_K` | `K` |
| DEVICE | `layers/<name>/thickness_nm` | `nm` |
| DEVICE | `layers/<name>/nc_diameter_nm` | `nm` |
| DEVICE | `layers/<name>/nc_volume_fraction` | `1` |
| DEVICE | `layers/<name>/electrically_active_fraction` | `1` |
| DEVICE | `layers/<name>/grid_points` | `1` |
| DEVICE | `layers/<name>/nc_material/sn_fraction` | `1` |
| OPERATING | `program/voltage_V` | `V` |
| OPERATING | `program/time_s` | `s` |
| OPERATING | `program/internal_dt_s` | `s` |
| OPERATING | `read/voltage_V` | `V` |
| OPERATING | `optical/wavelength_nm` | `nm` |
| OPERATING | `optical/power_density_W_m2` | `W/m^2` |

Layer names are resolved during application; declaring a contract does not
enable additional target fields or bypass device, material, or protocol validation.
Unknown paths retain their declarative G1 behavior. MODEL bindings have no binding
unit or numeric-domain contracts yet; the general domain validation still applies.

All categorical strings must have no outer whitespace; internal whitespace is
preserved. Valid variable serialization, domain order, and definition hashes are
unchanged.

## G2: deterministic structured sweeps

G2 exposes lazy Cartesian enumeration through `iter_cartesian_points(spec)`
and serial execution through `run_cartesian_sweep()`. Variable order and each
domain's declared order are preserved; the last declared axis varies fastest.
Point indices start at zero. Enumeration does not apply bindings, so declarative
MODEL and categorical axes can be inspected even though MODEL execution remains
deferred.

Each `SweepPoint` records its experiment hash, index, ordered assignments and
canonical point hash. The point's `assignments` property returns a fresh dictionary.
Enumeration is lazy and does not materialize the Cartesian product.

### Executing a study

The evaluator receives `(candidate_device, candidate_protocol, point)` and returns
a dictionary containing finite JSON values: string keys, dictionaries, lists,
strings, integers, finite floats, booleans and null. Convert scientific arrays
explicitly with `.tolist()`; arbitrary objects are not stringified.

```python
from ncmemsim import DeviceBuilder, Simulator
from ncmemsim.dtco import (
    BindingScope, DesignVariable, DesignVariableRole, ExperimentSpec,
    ParameterBinding, run_cartesian_sweep,
)
from ncmemsim.program_protocol import (
    ProgramPulseReadProtocol, run_program_pulse_read,
)

device = DeviceBuilder.v2(n_fgs=1)
protocol = ProgramPulseReadProtocol(5.0, 1.0e-6)
voltage = DesignVariable(
    name="program_voltage",
    binding=ParameterBinding(BindingScope.OPERATING, ("program", "voltage_V")),
    values=(5.0, 6.0),
    role=DesignVariableRole.ELECTRICAL,
    unit="V",
)
spec = ExperimentSpec.from_device(
    name="program-voltage-study",
    device=device,
    variables=(voltage,),
    operating_protocol=protocol,
)

def evaluate(candidate_device, candidate_protocol, point):
    simulator = Simulator(candidate_device)
    pulse = run_program_pulse_read(simulator, candidate_protocol)
    return {"delta_vfb_V": pulse.delta_vfb_V}

sweep = run_cartesian_sweep(
    spec, device, evaluate,
    base_protocol=protocol,
    evaluation_id="program-pulse-read-defaults-v1",
    evaluation_parameters={"simulator_configuration": "defaults-v0.12.0.dev0"},
)
print(sweep.success_count, sweep.failure_count)
print(sweep.sweep_hash, sweep.result_hash)
manifest_json = sweep.to_json()
```

For device-only studies without a recorded operating identity, omit
`base_protocol`; the evaluator receives `None` as its protocol. To evaluate even a
device-only study under a fixed protocol, record that protocol in the experiment.
A protocol supplied without a recorded identity is rejected.

The engine snapshots the baseline and evaluation definition before evaluation.
Every candidate is independently reconstructed using the existing G1 application
functions. Candidate mutation by an evaluator cannot contaminate later points.
Evaluators must construct fresh simulators and state for each point and avoid
sharing mutable simulation state through a closure or global variable.

### Failures and result identity

Setup errors (baseline mismatch, missing/unrecorded operating identity, MODEL
execution, invalid evaluator or evaluation definition) raise before evaluation.
Ordinary point exceptions are recorded with status `failed`, stage
(`application`, `evaluation`, or `serialization`), fully qualified exception
type and message. Subsequent points continue, including when every point fails.
`KeyboardInterrupt` and `SystemExit` propagate.

Success outputs are immutable JSON snapshots internally; exported dictionaries
are fresh copies. `SweepResult.points` contains one record per declared Cartesian
point, including failures, in the same deterministic order. The complete
experiment definition, evaluation identity/parameters, assignments, point hashes,
outputs, failures and counts are available in `to_dict()` and `to_json()`.

`evaluation_id` identifies the evaluator implementation/version.
`evaluation_parameters` must declare all execution settings affecting the
scientific result, including simulator configuration, fitted parameters and
initial-state policy. The engine cannot infer callback code or hidden closure
state. Update the identity when evaluator semantics change.

`sweep_hash` identifies the experiment, evaluator definition, ordering and serial
execution policy. `result_hash` additionally hashes all outputs and failures.
Identical definitions and deterministic evaluators produce repeatable manifests;
the engine does not guarantee numerical equivalence across solver/library
versions. Failure messages containing external paths or other changing text can
also change the result hash.

Execution retains the full result manifest in memory. Large studies can consume
the lazy point iterator with a caller-managed workflow instead. Parallel workers,
caching/resume, metric definitions, feasibility and Pareto analysis are outside
G2; metrics and constraints belong to G3.
