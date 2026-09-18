# Scientific workflow integration — Phase I / v0.14.0 development

## Status and baseline

I0 starts `0.14.0.dev0` from published v0.13.0 commit
`c3b1c10824c8296e7900e0b9bd8cbb19d6d75f8f` on
`dev/v0.14.0-scientific-workflows`. Citation metadata remains on v0.13.0.
Existing fitting/calibration, nominal DTCO and Robust DTCO APIs remain available.
I0 supplies scope/contracts and development setup. I1 adds immutable evidence
and identity contracts in `ncmemsim.workflows`; I2 adds fitted application and full
evaluator contexts. Complete references and linked integration reports remain planned.

## Delivery sequence

| Phase | Deliverable | Status |
|---|---|---|
| I0 | Bootstrap, scope and acceptance contracts | Implemented |
| I1 | Immutable workflow evidence and identity contracts | Implemented |
| I2 | Explicit fitted-parameter application and evaluator context adapter | Implemented |
| I3 | Electrical fitting/qualification → nominal/Robust DTCO reference | Next |
| I4 | Electro-optical fitting/qualification → nominal/Robust DTCO reference | Planned |
| I5 | End-to-end provenance, failure and compatibility verification | Planned |
| I6 | Linked workflow evidence report and reproducible exports | Planned |
| I7 | Final version/documentation audit, full CI and clean distributions | Planned |

## Scope

Connect existing Phase F fitting/qualification results to Phase G/H studies
without changing simulator physics, unit contracts, observation semantics or
existing qualification rules. Initial references use small explicitly synthetic
training/held-out datasets so development does not depend on unavailable measured
data. They verify software execution and identity links; experimental validation
requires independently sourced measurements and an applicable model.

The integration layer will preserve dataset/protocol/specification identities,
fitted values, fitting diagnostics, qualification criteria and results, applied
parameter contexts, nominal evaluations, exact sample manifests, sample failures,
response statistics, constraints, robust objectives and full source links. Runtime
provenance is recorded; cross-runtime bitwise reproducibility is not promised.

## Frozen contracts

1. **Evidence and scientific claims.** Keep data origin (synthetic/measured),
   source, applicability and qualification status separately explicit. Optimizer
   convergence, passing synthetic validation criteria or producing a Pareto front
   does not establish experimental device calibration or manufacturing yield.
   Preserve any existing qualification result as evidence without silently
   changing its status; never reinterpret synthetic evidence as measurements.
2. **Application.** Apply supported fitted parameters using existing validated
   application APIs, canonical units and fresh isolated contexts. Record full
   resulting device/material definitions, physics/photo settings, simulation
   configuration and operating protocol. A parameter-application hash alone is
   not a complete simulator identity. Unsupported applications fail explicitly;
   no alias, guessed mapping or implicit conversion is introduced.
3. **Nominal/sample consistency.** Nominal and sampled evaluation use the same
   declared response model, fitted context, configuration and protocol family.
   Each evaluation gets fresh mutable state. Identity mismatches and missing
   evidence fail before execution where possible; staged sample failures remain
   visible and are not relabelled as physical infeasibility.
4. **Uncertainty.** Users supply bounded independent Phase H variation definitions
   with explicit origin/provenance. Fit standard errors or covariance are not
   automatically transformed into probability laws or fabrication variation.
   Parameter-estimation and fabrication assumptions remain distinct. Correlations,
   hierarchical laws and general MODEL-scope sweeps are outside this cycle.
5. **Model-side fitted parameters.** For photo-capture or other supported fitting
   targets applied to model/configuration, snapshot that evaluator context
   explicitly. This does not add MODEL-scope design variables or distributions.
   DEVICE/OPERATING sampling remains within existing Phase H contracts.
6. **Reports.** Link complete source snapshots and identities rather than combine
   unrelated hashes or pass-status labels. Retain all failures, denominators and
   undefined statistics; integrity hashes establish consistency, not signatures
   or physical validation. Report serialization does not reevaluate physics.

## Acceptance by phase

I1 must reject malformed/missing evidence and preserve immutable snapshots,
source identity, data origin and qualification semantics. Public object names
and schema versions are introduced with the implementation review, not assumed
by this planning document.

I2 must demonstrate exact parameter application, isolation of baseline/context,
canonical units and complete evaluator provenance, including model-side settings.
Tests must distinguish full context identity from the narrower application hash.

I3/I4 must execute real existing simulator/protocol calls, with declared synthetic
training/held-out data and retained fit/qualification evidence. Fitted parameters
must actually drive predictions. Nominal/sample contexts must be demonstrably
consistent; deliberate failures are separated from physical responses. Any
chosen success/error thresholds require explicit units and applicability.

I5 must check source/context tampering or mismatches, complete-case/failure
accounting, preserved Phase F/G/H contracts and end-to-end electrical/optical
execution. It adds meaningful integration verification, not a second fitting
algorithm or altered scientific defaults.

I6 must restore/export linked evidence without rerunning fits or physics, reject
broken source links, preserve JSON/CSV/Markdown scientific labels and denominators,
and use explicit non-overwrite behavior.

I7 audits all current status/version claims, examples, imports, rendered links and
anchors before the release tag. It runs full pytest, supported-Python CI and
clean wheel/sdist installations with both new references and retained G/H probes.
Built and published source archives must contain the actual audited documentation.

## Development and final-release gates

Update docs and CHANGELOG and run focused local tests at each step. Intermediate
I0–I6 branch pushes/PRs do not launch CI or Documentation. Local checks validate
snippet syntax/public imports and current executable examples without MkDocs.
Package builds, full regression and strict rendered-documentation auditing belong
to final-version preparation. At I7, enable automatic CI and Documentation for
this exact dev branch, including final corrections. No separate release branch
is required. Tags continue to launch CI/Release; Pages deploys only from main.

## Outside this scope

No new quantum, strain, broadband or sequential multilayer optics; no automatic
experimental qualification, calibrated yield prediction, correlated uncertainty,
adaptive optimizer, numerical backend acceleration or physics-default changes.
DOI/archive and stable-API review remain separate v1.0 readiness requirements;
completing this integration cycle alone does not declare v1.0 stability.

## I1 — immutable source evidence

The dedicated `ncmemsim.workflows` surface exposes `DataOrigin`,
`DatasetEvidence`, `WorkflowEvidence`, `capture_dataset_evidence` and
`build_workflow_evidence`. Existing top-level/Phase F/G/H exports are unchanged.

Dataset capture requires an explicit synthetic/measured origin, nonempty source
and applicability without outer whitespace. Origin is a caller declaration,
not inferred from the dataset class/source text and not independently attested.
The dataset hash remains its existing normalized-data identity; evidence hashes
also include origin/source/applicability. Full snapshots are immutable canonical
JSON, with fresh dictionaries returned on inspection and integrity-checked JSON
restoration. Ordinary metadata must be finite strict JSON, without lossy NumPy,
tuple or key coercion.

This standalone example captures a synthetic observable; it performs no fitting
or qualification and makes no experimental claim:

```python
from ncmemsim.experimental import DeviceObservableDataset, ExperimentalDatasetMetadata
from ncmemsim.workflows import DataOrigin, DatasetEvidence, capture_dataset_evidence

dataset = DeviceObservableDataset(
    "programming_time", "s", [1e-7, 2e-7, 3e-7],
    "delta_vfb", "V", [0.01, 0.02, 0.03],
    ExperimentalDatasetMetadata("i1-synthetic", "Declared synthetic fixture"),
)
evidence = capture_dataset_evidence(
    dataset, origin=DataOrigin.SYNTHETIC,
    source="Software contract example", applicability="Synthetic example only",
)
restored = DatasetEvidence.from_json(evidence.to_json())
assert restored.evidence_hash == evidence.evidence_hash
assert restored.dataset_hash == dataset.dataset_hash()
assert restored.origin is DataOrigin.SYNTHETIC
```

`build_workflow_evidence` takes a name, captured training dataset, existing
single-dataset device fit result and its full `DeviceCalibrationSpec`. Initial
supported fit types are `DeviceCVFitResult`, `DeviceProgramTimeFitResult` and
`DevicePhotoProgramTimeFitResult`. Generic/optical-absorption/multi-condition fit
results are not automatically adapted. Standalone optical-absorption dataset
capture is supported. Optional fields are diagnostics, captured validation data,
qualification and strict JSON metadata. Validation data without qualification is
retained, with unknown qualification eligibility.

The factory checks training identity, calibration/parameter specification,
protocol hash, solver configuration, applied versus numerical fitted values and
provided diagnostics against existing `analyze_fit_uncertainty` on that numerical
fit. Qualification additionally requires linked validation data with matching
variable/observable names and units, supplied diagnostics, dataset/criteria links
and consistent criterion accounting. This checks identifiable source contracts;
it does not attest historical fitting execution or measurement independence from
hashes alone. Existing qualification objects do not contain a numerical-fit hash;
the envelope adds a fit source identity but cannot prove provenance absent from
the original source. Full applied simulator/evaluator context is supplied separately
by I2, rather than retroactively added to I1 sources. No fit, simulator or
qualification is rerun by capture.

The resulting `scientific_status` remains `FITTED` exactly as in supported fit
results. `qualification_eligible` is `None` without qualification, otherwise the
original boolean; eligibility never assigns `CALIBRATED` provenance. Synthetic
passing/failed qualification evidence stays explicitly synthetic. Rank-deficient
or unavailable diagnostics preserve `None` and tagged non-finite values such as
`{"_workflow_float":"positive_infinity"}` in diagnostic/qualification sections;
finite metadata/dataset/fit requirements remain unchanged. Source hashes use the
existing canonical source representation, while exported JSON uses explicit tags.

Workflow evidence snapshots include source schemas/hashes, full fit/specification,
optional diagnostics/qualification, declared dataset provenance, metadata and
Python/implementation/NumPy/package runtime. `to_json`/`from_json` verifies envelope,
source hashes and cross-source links; restoration does not refit, recompute
uncertainty or requalify, and preserves the captured runtime. Hashes establish
consistency, not authenticity, signatures or physical validation. Repeatability
is within a fixed runtime; cross-runtime bitwise equality is not guaranteed.

## I2 — application and evaluator adapter

`apply_workflow_parameters` accepts `WorkflowEvidence`, its exact
`DeviceCalibrationSpec`, explicit baseline device/physics/simulation/photo
configuration, an electrical or electro-optical program-pulse/read protocol and
an `evaluation_id`. It reads the ordered numerical fitted values from evidence
and applies them through `apply_device_calibration_parameters`; values, mappings
and units are never guessed or converted. Canonical fitting units must match
`DeviceFitParameterBinding.canonical_unit` exactly, including `None` for
dimensionless Phase F parameters. This new adapter check leaves existing Phase F
application APIs unchanged. Qualification eligibility and data origin remain
separate evidence, with `FITTED` status retained.

The declared baseline is recorded, not attested as the original fitting simulator:
I1 fit sources do not identify that full historical context. Reapplying to a
different baseline is an explicit new application with a different context
identity. Baselines are copied; full applied device/material definitions, layer
metadata, semiconductor/coupling/field-solver settings, shared tunneling, kinetics,
transport, simulation config, photo settings and fixed compact optical-model
defaults are captured. Source evidence, operating protocol/light/weights/integrator,
response model and current application runtime are linked in `AppliedWorkflowEvidence`.

`parameter_application_hash` remains the existing narrower specification/value
identity. `context_hash` covers the full applied device/model/configuration;
`evidence_hash` additionally covers baseline, sources, operating protocol,
response model/evaluator id and runtime. Changes to materials or unfitted model
settings alter full context identity even when the application hash is unchanged.
JSON restoration verifies envelope/source hashes, domain representations, fitted
targets and the exact declared baseline-to-applied delta without applying
parameters, refitting, qualifying or running physics. Runtime snapshots are
preserved, including foreign runtimes; execution requires the captured application
runtime and fixed optical defaults to match the current executable runtime.
Integrity hashes are not signatures or historical execution attestations.

The returned `WorkflowEvaluator` supplies copied `base_device`, `base_protocol`
and `evaluation_parameters`, its `evaluation_id`, immutable `evidence`, and
`fresh_simulator()`. Core physics is reconstructed from captured settings for
each simulator, retaining shared tunneling within that fresh object graph.
`evaluate(device, protocol, point=None)` accepts both two-argument nominal and
three-argument G2/H3 callbacks. It runs the existing electrical or electro-optical
pulse/read function from an empty state and returns `delta_vfb_V` in V and
`mean_occupation` dimensionlessly. Fitted photo efficiency is passed explicitly
at execution, not inserted into the operating protocol. Optical execution requires
explicit photo settings; photo fitting targets in a dark electrical evaluator are
rejected. Model-side parameters do not add MODEL-scope variations.

I2 supports the unextended built-in device/layer/material/core-physics classes,
`CompactCouplingModel` and `FieldSolver1D`; custom engine subclasses, extra
instance state or broken tunneling sharing fail rather than receive incomplete
identities. Optical execution requires an LED/laser protocol and uses the existing
fixed `CompositeGeSnAbsorptionModel` defaults, recorded explicitly; arbitrary
custom absorption models are not adapted. DEVICE candidates and existing
OPERATING wavelength/power/electrical variations are accepted. Photo weights,
integrator and optical source family must stay fixed. Explicit DEVICE variations
may override a device-side fitted target; Phase G/H records them as variations.
Returned templates are copies, private template drift fails before execution,
and staged Phase H failures remain visible.

This standalone synthetic C-V example demonstrates application and isolated
evaluation, without claiming parameter recovery, qualification or experimental
calibration. Complete electrical and optical references remain I3/I4 work:

```python
from dataclasses import replace
from ncmemsim.reference import make_v53_reference_device
from ncmemsim.physics import PhysicsModel
from ncmemsim.simulator import SimulationConfig, Simulator
from ncmemsim.device_fit import CVCalibrationProtocol, fit_single_parameter_cv_dataset
from ncmemsim.device_calibration import DeviceCalibrationSpec, DeviceFitParameterBinding, DeviceFitTarget
from ncmemsim.fitting import FitParameter, FitParameterSet
from ncmemsim.experimental import DeviceObservableDataset, ExperimentalDatasetMetadata, ExperimentalCondition
from ncmemsim.program_protocol import ProgramPulseReadProtocol
from ncmemsim.workflows import (
    DataOrigin, AppliedWorkflowEvidence, capture_dataset_evidence,
    build_workflow_evidence, apply_workflow_parameters,
)

device = make_v53_reference_device(grid_points=7)
physics = PhysicsModel.default()
config = SimulationConfig(dwell_time_s=0.0)
protocol = CVCalibrationProtocol(-2.0, 2.0, 7)
generated = Simulator(device, physics, replace(config, qfix_C_m2=0.001)).simulate_cv(
    vmin_V=-2.0, vmax_V=2.0, points=7,
).forward
dataset = DeviceObservableDataset(
    "gate_voltage", "V", generated.voltages_V, "capacitance", "F/m^2",
    generated.capacitance_F_m2,
    ExperimentalDatasetMetadata("i2-synthetic-cv", "Generated software example"),
    conditions=(ExperimentalCondition("sweep_direction", "forward"),),
)
spec = DeviceCalibrationSpec(
    FitParameterSet((FitParameter("qfix", 0.0, -0.005, 0.005, unit="C/m^2"),)),
    (DeviceFitParameterBinding("qfix", DeviceFitTarget.SIMULATION_QFIX_C_M2),),
)
fit = fit_single_parameter_cv_dataset(dataset, base_device=device, base_physics=physics,
    base_simulation_config=config, calibration_spec=spec, protocol=protocol)
captured = capture_dataset_evidence(dataset, origin=DataOrigin.SYNTHETIC,
    source="Generated C-V example", applicability="Software verification only")
workflow = build_workflow_evidence(name="I2 application example", fit_dataset=captured,
    fit_result=fit, calibration_spec=spec)
adapter = apply_workflow_parameters(workflow, calibration_spec=spec,
    base_device=device, base_physics=physics, base_simulation_config=config,
    base_protocol=ProgramPulseReadProtocol(3.0, 1e-7, program_internal_dt_s=1e-7),
    evaluation_id="i2-example-delta-vfb")
output = adapter.evaluate(adapter.base_device, adapter.base_protocol)
assert output == adapter.evaluate(adapter.base_device, adapter.base_protocol)
assert adapter.fresh_simulator().config.qfix_C_m2 == fit.fitted_parameter_values["qfix"]
assert AppliedWorkflowEvidence.from_json(adapter.evidence.to_json()).evidence_hash == adapter.evidence.evidence_hash
assert workflow.qualification_eligible is None
```

For nominal and sampled studies, pass `adapter.evaluate` as the callback and the
same `adapter.evaluation_id`, `adapter.evaluation_parameters`, `adapter.base_device`
and `adapter.base_protocol` to existing Phase H functions. Supply variation
laws/provenance independently; no fitted covariance or diagnostics are converted
into fabrication assumptions. Integration tests exercise genuine fits for C-V
and photo efficiency, every retained non-photo application target, nominal/sample
consistency, isolation, model-setting identity changes and staged failures.
Insensitive zero-dwell target fits check application compatibility, not
identifiability or physical parameter recovery.
