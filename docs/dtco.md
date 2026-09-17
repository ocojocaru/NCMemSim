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

## G3: metrics and feasibility constraints

G3 analyzes a completed `SweepResult` without rerunning simulations. It preserves
every point's order and source identity, including failures.

`MetricDefinition(name, path, unit, direction=None)` names one numeric scalar in
an evaluator's output. A string path segment selects an object key; a nonnegative
integer selects an array index. Paths are explicit, with no attribute traversal,
wildcards, array reduction or implicit conversions. Boolean, string, null,
container and non-finite terminal values are rejected.

Units are explicit and unchanged (`"1"` for dimensionless quantities).
`ObjectiveDirection.MINIMIZE` and `ObjectiveDirection.MAXIMIZE` identify
objectives; `None` defines a reporting or constraint-only metric. Values retain
their original sign and numeric representation. Direction is metadata for later
multi-objective analysis, not a scalar score or a feasibility rule. Compute derived
quantities explicitly in the G2 evaluator and expose them as scalar JSON output.

`MetricConstraint(name, metric_name, operator, threshold, unit)` references an
existing metric by name. Supported operators are `ConstraintOperator.LE` (`<=`)
and `ConstraintOperator.GE` (`>=`). Bounds are inclusive, thresholds are finite
numeric scalars, and constraint units must exactly match the metric unit.
There is no implicit unit conversion, numerical tolerance, penalty, or aggregation
across differently dimensioned constraints. An interval uses two named bounds.
Contradictory bounds are allowed and produce infeasible points.

### Analyzing a program/read sweep

The existing program/read result's `to_dict()` exposes the signed flat-band shift
under `observable/value` and per-floating-gate occupation as an array:

```python
from ncmemsim import DeviceBuilder, Simulator
from ncmemsim.dtco import (
    BindingScope, ConstraintOperator, DesignVariable, DesignVariableRole,
    ExperimentSpec, MetricAnalysisSpec, MetricConstraint, MetricDefinition,
    ObjectiveDirection, ParameterBinding, analyze_sweep, run_cartesian_sweep,
)
from ncmemsim.program_protocol import ProgramPulseReadProtocol, run_program_pulse_read

device = DeviceBuilder.v2(n_fgs=1)
protocol = ProgramPulseReadProtocol(5.0, 1.0e-6)
voltage = DesignVariable(
    name="voltage",
    binding=ParameterBinding(BindingScope.OPERATING, ("program", "voltage_V")),
    values=(5.0, 6.0), role=DesignVariableRole.ELECTRICAL, unit="V",
)
experiment = ExperimentSpec.from_device(
    name="program-study", device=device, variables=(voltage,),
    operating_protocol=protocol,
)

def evaluate(candidate_device, candidate_protocol, point):
    pulse = run_program_pulse_read(Simulator(candidate_device), candidate_protocol)
    return pulse.to_dict()

sweep = run_cartesian_sweep(
    experiment, device, evaluate, base_protocol=protocol,
    evaluation_id="program-read-payload-v1",
    evaluation_parameters={"simulator_configuration": "defaults-v0.12.0.dev0"},
)
metrics = MetricAnalysisSpec(
    name="program-read-feasibility",
    metrics=(
        MetricDefinition("signed_shift", ("observable", "value"), "V",
                         ObjectiveDirection.MAXIMIZE),
        MetricDefinition("occupation", ("mean_occupation",), "1"),
        MetricDefinition("first_fg", ("mean_occupation_by_fg", 0), "1"),
    ),
    constraints=(
        MetricConstraint("occupation_min", "occupation", ConstraintOperator.GE, 0.0, "1"),
        MetricConstraint("occupation_max", "occupation", ConstraintOperator.LE, 1.0, "1"),
    ),
)
analysis = analyze_sweep(sweep, metrics)
print(analysis.feasible_count, analysis.infeasible_count, analysis.failure_count)
manifest_json = analysis.to_json()
```

The signed shift is not automatically converted to a magnitude or a memory window.
Choose a metric and direction appropriate to the observable under study.
Metric units describe the evaluator's numeric payload; G3 cannot infer or verify
physical units from a JSON number alone. The analysis specification checks the
unit contract between each metric and its constraints.

### Point classification and identity

Each `MetricPointResult` has one of three statuses:

- `feasible`: all metrics were extracted and all constraints satisfied;
- `infeasible`: metrics were extracted but at least one bound was violated;
- `failed`: the source sweep point failed, or metric extraction failed.

No constraints means every successful extraction is feasible. An infeasible point
retains its metrics and all individual bound evaluations (actual value, threshold,
operator, unit and satisfied flag). A failed point is not classified as infeasible
and exposes no partial metrics or partial constraint results.

Source failures retain their exception details and receive analysis failure stage
`sweep`; the complete source manifest preserves the original G2 failure stage.
Missing keys, wrong container types, out-of-range indices and invalid scalar values
receive stage `extraction`. Other points continue to be analyzed.

`MetricAnalysisSpec` rejects empty metrics, duplicate names, unknown constraint
references and mismatched units before analysis. Definitions and result records are
immutable; exported dictionaries and JSON are snapshots independent of callers.

The result manifest includes the complete source sweep, source sweep/result hashes,
ordered metric/constraint definitions, point classifications and counts.
`definition_hash` identifies the ordered analysis specification.
`analysis_hash` links that definition to the exact source result hash.
`result_hash` additionally identifies the full analysis result.
Changing paths, units, objective directions, bounds or source results changes the
corresponding identity. G1/G2 serialization and hashes remain unchanged.

The analysis retains the source sweep and all classifications in memory.
It does not remove failed or infeasible points, select an optimum, or compute
Pareto fronts; non-dominated sorting belongs to G4.

## G4: multi-objective / Pareto analysis

`analyze_pareto(metric_analysis, spec=None)` performs deterministic non-dominated
sorting over the feasible points of a completed G3 analysis. It does not rerun
simulation or change G1/G2/G3 serialization.

A point dominates another if it is no worse on every selected objective and
strictly better on at least one. Each metric's declared `ObjectiveDirection`
determines the comparison. Values retain their sign, unit and integer precision;
there are no weights, absolute-value transforms, numerical tolerances or combined
scores. Equal objective vectors do not dominate one another, so all duplicate
vectors are retained.

`ParetoAnalysisSpec(name, objective_names)` selects an ordered subset of directed
G3 metrics. Unknown names, duplicate names, empty selections and directionless
reporting metrics are rejected. If no specification is provided, all directed
metrics are selected in G3 declaration order. At least one objective is required.

### Example: response versus pulse duration

This example evaluates the existing program/read protocol and compares the signed
flat-band shift with the pulse duration. The chosen shift direction is illustrative;
choose the observable and direction appropriate to the physical study.

```python
from ncmemsim import DeviceBuilder, Simulator
from ncmemsim.dtco import (
    BindingScope, DesignVariable, DesignVariableRole, ExperimentSpec,
    MetricAnalysisSpec, MetricDefinition, ObjectiveDirection, ParameterBinding,
    ParetoAnalysisSpec, analyze_pareto, analyze_sweep, run_cartesian_sweep,
)
from ncmemsim.program_protocol import ProgramPulseReadProtocol, run_program_pulse_read

device = DeviceBuilder.v2(n_fgs=1)
protocol = ProgramPulseReadProtocol(5.0, 1.0e-6)
duration = DesignVariable(
    name="duration",
    binding=ParameterBinding(BindingScope.OPERATING, ("program", "time_s")),
    values=(1.0e-6, 2.0e-6), role=DesignVariableRole.ELECTRICAL, unit="s",
)
experiment = ExperimentSpec.from_device(
    name="response-duration", device=device, variables=(duration,),
    operating_protocol=protocol,
)

def evaluate(candidate_device, candidate_protocol, point):
    return run_program_pulse_read(Simulator(candidate_device), candidate_protocol).to_dict()

sweep = run_cartesian_sweep(
    experiment, device, evaluate, base_protocol=protocol,
    evaluation_id="program-read-pareto-example-v1",
    evaluation_parameters={"simulator_configuration": "defaults-v0.12.0.dev0"},
)
analysis = analyze_sweep(sweep, MetricAnalysisSpec(
    name="response-duration-metrics",
    metrics=(
        MetricDefinition("signed_shift", ("observable", "value"), "V",
                         ObjectiveDirection.MAXIMIZE),
        MetricDefinition("duration", ("protocol", "programming_time_s"), "s",
                         ObjectiveDirection.MINIMIZE),
    ),
))
pareto = analyze_pareto(
    analysis, ParetoAnalysisSpec("response-duration-fronts", ("signed_shift", "duration")),
)
print(pareto.pareto_indices)
print(pareto.fronts)
manifest_json = pareto.to_json()
```

The objectives may have different units because each is compared independently.
Constraint-only and reporting metrics affect neither dominance nor ranking unless
they are explicitly directed and selected; G3 constraints still govern eligibility.

### Fronts, exclusions and reproducibility

Ranks start at zero. Front zero contains all non-dominated feasible points.
Removing it exposes front one, and so on until every feasible point has a rank.
Front members appear in original source order, including ties. This order carries
no preference between members of the same front.

`ParetoAnalysisResult.points` retains every G3 point in source order.
Feasible points retain the selected objective values and integer rank.
Infeasible or failed points have `rank=None`, no ranking objective vector, and
an explicit exclusion reason; their metrics, constraint evaluations and errors
remain available through the complete source analysis in the result manifest.

`fronts` is a tuple of tuples of source point indices.
`pareto_indices` is front zero, or an empty tuple if no feasible points exist.
The manifest includes the specification, selected metric definitions and
directions, source analysis/result hash, complete source analysis, all point
records, fronts, ranked count and excluded count.

`definition_hash` identifies the selection and exact ranking policy.
`analysis_hash` links the specification to the exact G3 result.
`result_hash` identifies the full Pareto result. Changing objective selection,
selection order, direction or source results changes the corresponding identity.
Exports are independent JSON snapshots; analysis does not mutate its source.

The algorithm uses O(N² M) comparisons and up to O(N²) memory for N feasible
points and M objectives. Large studies should account for this cost.
G4 exposes trade-off fronts and does not select a single optimum.
Sensitivity analysis is deferred to G5.

## G5: sensitivity analysis of structured grids

`analyze_sensitivity(metric_analysis, spec=None)` computes local finite-interval
secants and grid-wide summaries over a completed G3 analysis, without rerunning
simulation or changing G1–G4 serialization.

`SensitivityAnalysisSpec(name, axis_names, metric_names, eligibility)` selects
numeric design-variable axes and G3 metrics in explicit order. Directionless
reporting metrics are supported: sensitivity uses raw signed response values,
independent of optimization direction. Unknown names, duplicate/empty selections
and selected categorical axes are rejected.

Without a specification, all numeric axes and all G3 metrics are selected in
declaration order. At least one numeric axis and one metric are required.
Singleton axes are allowed and have no intervals to estimate. Other axes can
remain categorical background contexts; they are held fixed.

### Local estimates

For each selected axis, its declared values are sorted in ascending numeric order.
For each fixed combination of the other axes, adjacent values define a secant:

```text
slope = (metric_at_right - metric_at_left) / (axis_right - axis_left)
```

The remaining coordinates are identical at both endpoints. Original source point
indices, axis values and metric identities are retained, and the source order is
unchanged. Output order is selected axis, selected metric, other-axis contexts in
declared Cartesian order, then ascending adjacent axis intervals.

Integer differences are computed before division; slopes are floating-point
estimates. Unit metadata is the explicit ratio `(metric_unit)/(axis_unit)`,
without conversion, normalization, absolute-value transformation or implicit
unit simplification. Secants on discrete axes are finite-step response changes,
not a claim of an infinitesimal derivative.

`SensitivityEligibility.ASSESSED` (default) includes both feasible and infeasible
G3 points with successfully extracted metrics. `FEASIBLE_ONLY` includes only
feasible points. Both endpoints must qualify. Source/extraction failures and
infeasible endpoints under feasible-only analysis exclude the interval.

Missing or excluded neighbors are never bridged. Every declared adjacent interval
has a record: `estimated`, `excluded`, or `failed` for non-finite/overflowing
arithmetic. Exclusions identify the endpoint and G3 status; arithmetic failures
retain their type and message. No invalid slope is silently replaced with zero.

### Example: program-duration sensitivity

```python
from ncmemsim import DeviceBuilder, Simulator
from ncmemsim.dtco import (
    BindingScope, DesignVariable, DesignVariableRole, ExperimentSpec,
    MetricAnalysisSpec, MetricDefinition, ParameterBinding,
    SensitivityAnalysisSpec, SensitivityEligibility,
    analyze_sensitivity, analyze_sweep, run_cartesian_sweep,
)
from ncmemsim.program_protocol import ProgramPulseReadProtocol, run_program_pulse_read

device = DeviceBuilder.v2(n_fgs=1)
protocol = ProgramPulseReadProtocol(5.0, 1.0e-6)
duration = DesignVariable(
    name="duration",
    binding=ParameterBinding(BindingScope.OPERATING, ("program", "time_s")),
    values=(1.0e-6, 2.0e-6, 3.0e-6),
    role=DesignVariableRole.ELECTRICAL, unit="s",
)
experiment = ExperimentSpec.from_device(
    name="duration-sensitivity", device=device, variables=(duration,),
    operating_protocol=protocol,
)

def evaluate(candidate_device, candidate_protocol, point):
    return run_program_pulse_read(Simulator(candidate_device), candidate_protocol).to_dict()

sweep = run_cartesian_sweep(
    experiment, device, evaluate, base_protocol=protocol,
    evaluation_id="program-read-sensitivity-example-v1",
    evaluation_parameters={"simulator_configuration": "defaults-v0.12.0.dev0"},
)
analysis = analyze_sweep(sweep, MetricAnalysisSpec(
    name="shift-metrics",
    metrics=(MetricDefinition("signed_shift", ("observable", "value"), "V"),),
))
sensitivity = analyze_sensitivity(analysis, SensitivityAnalysisSpec(
    name="duration-secants", axis_names=("duration",),
    metric_names=("signed_shift",),
    eligibility=SensitivityEligibility.ASSESSED,
))
print(sensitivity.summaries)
manifest_json = sensitivity.to_json()
```

### Grid-wide summaries, coverage and identity

Each axis/metric pair has its own summary: attempted, estimated, excluded and
arithmetic-failed interval counts; coverage fraction; complete flag; mean signed
slope; mean absolute slope; and maximum absolute slope.

Every valid grid edge has equal weight. These statistics summarize sampled
finite-interval slopes over the whole grid, including changes with background
context; they are not Sobol indices, variance decomposition, probability-weighted
sensitivities or a ranking across differently dimensioned axes. Nonuniform
sampling changes these summaries. Signed means can cancel; the absolute-slope
statistics remain available separately.

Excluded and failed intervals are omitted from statistics but remain in the
denominator of coverage. With no valid estimates, statistics are null.
A singleton axis has zero attempted intervals, null coverage, and complete=false.
Partial coverage is never presented as complete.

Definitions and edge records are immutable; summary dictionaries and exported
manifests are fresh snapshots. The manifest includes selected axes/units, metric
definitions, eligibility/method policy, all edge records and coverage summaries,
plus the complete G3 source analysis and its result hash.

`definition_hash` identifies the ordered specification and method policy.
`analysis_hash` links it to the exact source result, and `result_hash` identifies
the full sensitivity result. Changing selection, eligibility, domains, metrics or
source results changes the corresponding identity.

Analysis retains the source and all interval records in memory. G5 does not infer
a continuous response surface, impute missing points or fit an optimizer.
Reproducible reports and reference workflows are deferred to G6.

## G6: reproducible report bundles and reference workflow

`build_dtco_report(metric_analysis, pareto=None, sensitivity=None, ...)` combines
a G3 analysis with optional G4/G5 results from the exact same source analysis.
Mismatched source hashes are rejected before report construction.

`DTCOReport` is an immutable canonical JSON snapshot. Its manifest contains the
complete G3 analysis and G2 sweep once. Pareto and sensitivity sections reference
that analysis without duplicating it; their original result hashes remain
verifiable by restoring the shared `source_analysis` field.

The manifest records the report name, NCMemSim version, caller-declared metadata,
component/result hashes, complete experiment/evaluator definitions, source outputs,
assignments, units, constraint evaluations, exclusions, failures and coverage.
No wall-clock timestamp, output path or generated filename enters report identity.

### Report API

```python
from ncmemsim.dtco import DTCOReport, build_dtco_report, write_dtco_report

# analysis, pareto and sensitivity are the completed G3/G4/G5 results.
report = build_dtco_report(
    analysis, name="My DTCO study", pareto=pareto, sensitivity=sensitivity,
    metadata={"study_id": "study-v1"},
)
manifest_json = report.to_json()
verified = DTCOReport.from_json(manifest_json)
assert verified.report_hash == report.report_hash
paths = write_dtco_report(report, "results/my-dtco-study")
```

`from_json()` rejects duplicate keys, unsupported schemas, stale report/component
hashes and inconsistent source/definition/point identity links. This checks
manifest integrity and consistency; it is not a digital signature or independent
validation of the scientific model. A self-consistent manifest can be authored
by any caller.

`write_dtco_report()` writes four UTF-8 files and refuses existing target filenames
before writing. Other files in the directory are preserved. In case of an
unexpected I/O interruption, the directory can contain a partial bundle; no
transactional directory replacement is claimed.

| Artifact | Contents |
| --- | --- |
| `manifest.json` | Canonical manifest and report hash |
| `points.csv` | Every source point, status, optional Pareto rank and JSON payload columns |
| `sensitivity.csv` | Every interval, endpoint indices/values, estimate or exclusion/error, slope unit |
| `report.md` | Metric/constraint definitions, counts, fronts, all classifications and coverage summaries |

The point CSV uses fixed column names and JSON fields for assignments, metrics,
constraints and failures. JSON preserves numeric payload precision and explicit
names without ambiguous dynamic CSV headers. Units and evaluator settings remain
in the manifest and Markdown definitions. A blank rank denotes either exclusion
or an omitted Pareto component; the status and manifest distinguish these cases.
When sensitivity is absent, its CSV contains the header only.

Markdown reports retain all point classifications and all sensitivity summaries.
They do not promote an infeasible point or select a single optimum.
Report payloads remain exact; spreadsheet applications may apply their own
numeric interpretation if CSV JSON fields are manually expanded.

### Executable reference example

From the repository root, with the package installed or the checkout importable:

```text
python -m examples.phase_g6_dtco_reference --output-dir results/g6-reference
```

The example sweeps temperature and program duration on the existing electrical
program/read workflow, starting from a fresh empty state per candidate. It records
the complete `SimulationConfig`, default physics identity, NCMemSim/Python/NumPy
versions and derived-observable policy in the evaluator definition.

It explicitly derives `abs(delta_vfb_V)` as a single-program shift magnitude,
maximizes that response and minimizes pulse duration. Occupation bounds determine
feasibility. This is an illustrative electrical reference, not a memory-window
definition, a calibrated prediction or evidence of a universal design optimum.

An intentional invalid-duration demonstration exercises failures and partial
sensitivity coverage:

```text
python -m examples.phase_g6_dtco_reference --output-dir results/g6-failure-demo --include-invalid-point
```

For publication-resolution PNG (300 dpi) and vector SVG output, add `--plots`.
This optional path requires Matplotlib from the existing development dependencies;
the base reporting API adds no plotting dependency.

```text
python -m examples.phase_g6_dtco_reference --output-dir results/g6-reference-plots --plots
```

The figure plots assessed points and outlines front-zero members, with source point
indices as labels. Failed points remain in the bundle and have no plotted response.
No line implies a continuous response curve. Figure files are presentation
artifacts outside the report hash; rendering depends on the plotting environment.
SVG dates are omitted and identifier salts follow report identity.

Use a new output directory for repeat exports, or remove the previous files
explicitly. Identical source results and declared metadata yield the same report
hash in the same recorded execution environment. If callback semantics or
scientific settings change, update the G2 evaluator identity/parameters.

G6 packages completed results and examples. It does not modify simulation
semantics, run an optimizer or bypass G3/G4 eligibility.
## G7: release validation and distribution checks

CI now validates the DTCO development branch and main on Python 3.11, 3.12,
and 3.13. Full regression tests remain in the existing matrix. A separate
matrix builds wheel and source distributions and installs each in its own
virtual environment. Strict documentation builds also gate CI.

Run the distribution check from the repository root:

```console
python scripts/validate_dtco_distribution.py
```

The default check downloads build tools/dependencies as needed and creates
clean environments. Build tools are installed in a separate clean builder;
source installation uses freshly installed setuptools/wheel. On Windows Conda,
a temporary startup file registers the interpreter's runtime DLL directory
for stdlib extensions such as `pyexpat` and `ssl`; it does not expose host
Python packages. This file stays inside temporary environments. It checks all DTCO modules in each archive, proves imports
come from the installed package outside the checkout, and runs the real G6
reference with and without failed candidates. It checks repeatable hashes,
manifest round trips, CSV row counts and all four exported files. Examples
remain repository assets; the reference is copied separately into the probe.

For a local offline check with existing NumPy/build tools:

```console
python scripts/validate_dtco_distribution.py --reuse-dependencies
```

This mode inherits dependencies from the invoking interpreter. NCMemSim itself
must still load from the newly installed distribution. It does not substitute
for clean dependency resolution in CI. Temporary builds, environments and
reports are removed automatically. Hash equality is checked within each
runtime, not across Python/NumPy versions recorded in the manifest.

The tag release workflow validates installed distributions before publication.
G7 adds release gates; it does not change `0.12.0.dev0`, create a tag, publish
artifacts, or establish scientific calibration. Python 3.11/3.12 execution is
confirmed by CI, not by a local run on Python 3.13.
