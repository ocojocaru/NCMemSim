# Public API overview

The public import surface for NCMemSim v0.14.0 is defined primarily in
`ncmemsim/__init__.py`, with optical material models exposed from
`ncmemsim.materials.optics`.

Experimental-data, fitting, diagnostic, and calibration APIs are exposed
from their dedicated v0.11.0 modules.

The following groups summarize the principal public objects.
Compatibility preparation and remaining v1.0 gates are described in
[API compatibility preparation](api_compatibility.md).

## Version

- `__version__`

## Device and materials

- `Device`
- `DeviceBuilder`
- `Layer`
- `FloatingGateLayer`
- `Material`
- `NanocrystalMaterial`
- `SILICON`, `SIO2`, `HFO2`
- `make_ge`, `make_gesn`
- `make_v53_reference_device`

## State

- `DeviceState`
- `FloatingGateState`

## Simulation

- `Simulator`
- `SimulationConfig`
- `SweepResult`
- `CVResult`
- `PhysicsModel`

`Simulator.relax_voltage()` supports dark, optical, and electro-optical
programming through the optional arguments:

- `light_source`
- `photo_config`
- `photo_weights`

The same optical configuration can be propagated through voltage sweeps
and compact C-V simulations.

## Electrostatics and fields

- `ElectrostaticsEngine`
- `ElectrostaticsResult`
- `SemiconductorConfig`
- `CouplingModel`
- `CompactCouplingModel`
- `CouplingResult`
- `FieldSolver1D`
- `FieldProfile`

## Kinetics and tunnelling

- `KineticsConfig`
- `OccupancyEngine`
- `RateArrays`
- `TunnelingConfig`
- `TunnelingEngine`

Electrical and optical transition-rate arrays are combined additively by
the occupancy engine.

## Optical sources

- `LightSource`

`LightSource` represents monochromatic LED and laser sources and provides
derived photon quantities including:

- photon energy in joules;
- photon energy in electron-volts;
- incident photon flux.

Example:

```python
from ncmemsim.optics import LightSource

source = LightSource.laser(
    wavelength_nm=1550.0,
    power_density_W_m2=1000.0,
)
```

## Optical material models

The public optical material API is available from
`ncmemsim.materials.optics`.

Principal objects include:

- `OpticalPoint`
- `GeSnOpticalParameterSet`
- `GeSnAbsorptionParameterSet`
- `CompactOpticalMaterialModel`
- `CompositeGeSnAbsorptionModel`
- `GeSnNearEdgeParameterSet`
- `GeSnNearEdgeReferenceModel`
- `NearEdgeBranch`
- `NearEdgeOpticalPoint`
- `OpticalValidationDomain`
- `EvaluationDomainStatus`
- `TRAN_2016_NEAR_EDGE_PARAMETERS`
- `TRAN_2016_NEAR_EDGE_DOMAIN`
- `photon_energy_eV`
- `direct_gap_gesn_eV`
- `indirect_gap_gesn_eV`
- `phonon_occupation`

The compact Ge/GeSn optical model provides separate direct-Gamma,
indirect phonon-assisted, and Urbach-tail absorption contributions.

Example:

```python
from ncmemsim.materials.optics import CompositeGeSnAbsorptionModel

model = CompositeGeSnAbsorptionModel()
point = model.evaluate(material, wavelength_nm=1550.0)
```

### GeSn near-edge reference model

NCMemSim v0.11.0 also provides an opt-in, literature-anchored
near-edge reference model for bulk-like, unstrained Ge/GeSn:

```python
from ncmemsim.materials.optics import GeSnNearEdgeReferenceModel

model = GeSnNearEdgeReferenceModel()
point = model.evaluate(material, wavelength_nm=2000.0)

print(point.absorption_coefficient_m_inv)
print(point.branch.value)
print(point.domain_status.value)
```

The model uses the Tran et al. literature-fitted direct prefactor and
Urbach width together with an NCMemSim-derived C1 connection between
the direct and Urbach branches.

It does not replace the existing compact v0.10.0 optical model and is
not selected automatically by the existing optical-programming
workflow.

See [GeSn near-edge reference](near_edge_reference.md) for the full
scientific scope, provenance, equations, validation domain, fitting
workflow, and limitations.

## Experimental optical datasets

Experimental optical absorption datasets are represented by:

```python
from ncmemsim.experimental import (
    ExperimentalDatasetMetadata,
    OpticalAbsorptionDataset,
)
```

`OpticalAbsorptionDataset` stores canonical:

- wavelength in nm;
- absorption coefficient in \(\mathrm{m^{-1}}\);
- Sn fraction;
- source and sample metadata;
- optional pointwise absorption uncertainty in \(\mathrm{m^{-1}}\).

CSV import is available from:

```python
from ncmemsim.io import load_optical_absorption_csv
```

The validated optical CSV schema is:

```text
wavelength_nm,absorption_coefficient_m_inv,absorption_uncertainty_m_inv
```

The uncertainty column is optional when the source dataset has no
declared pointwise uncertainty.

## Generic fitting

The fitting layer is available from `ncmemsim.fitting`.

Principal objects include:

- `FitParameter`
- `FitParameterSet`
- `LeastSquaresConfig`
- `DeterministicFitResult`
- `evaluate_least_squares_objective`
- `run_least_squares_fit`

The deterministic runner uses normalized parameter coordinates internally
while reporting fitted values and stored Jacobians in physical parameter
coordinates.

SciPy is an optional fitting dependency rather than a mandatory runtime
dependency for the base package.

## Fit uncertainty and identifiability

Local fit diagnostics are available from:

```python
from ncmemsim.fit_diagnostics import (
    FitUncertaintyDiagnostics,
    analyze_fit_uncertainty,
)
```

Diagnostics include:

- Jacobian rank;
- bound-scaled singular values;
- scaled condition number;
- covariance matrix when available;
- parameter standard errors;
- parameter correlation;
- active-bound count;
- a local-identifiability flag.

`locally_identifiable=True` means that the local Jacobian has full
column rank. It is not a claim of global identifiability.

The reported standard errors are model-based linearized fit estimates.
They are not source-reported experimental uncertainties.

## Calibration qualification

The generic calibration API is available from:

```python
from ncmemsim.calibration import (
    CalibrationCriteria,
    CalibrationCriterionResult,
    CalibrationQualification,
    qualify_calibration,
)
```

`CalibrationCriteria` can configure:

- maximum validation RMSE;
- maximum validation MAE;
- minimum validation \(R^2\);
- maximum scaled condition number;
- whether a distinct validation-dataset hash is required;
- whether local identifiability is required;
- whether covariance availability is required.

At least one quantitative validation threshold is required.

A successful optimizer result alone never creates `CALIBRATED`
provenance.

## GeSn near-edge fitting and calibration

The GeSn-specific public API is exposed from
`ncmemsim.materials.optics`:

```python
from ncmemsim.materials.optics import (
    GESN_NEAR_EDGE_FIT_PARAMETER_NAMES,
    GeSnNearEdgeCalibrationResult,
    GeSnNearEdgeFitResult,
    fit_gesn_near_edge_absorption,
    predict_gesn_near_edge_absorption_m_inv,
    qualify_gesn_near_edge_fit,
)
```

The first adapter fits exactly the direct prefactor and Urbach energy
while keeping the direct-gap relation fixed.

A successful fit creates a separate near-edge parameter set whose fitted
parameters have `FITTED` provenance.

`qualify_gesn_near_edge_fit()` evaluates a declared validation dataset
without re-optimizing the fitted parameters. If every configured
criterion passes, it creates a **new** parameter set with `CALIBRATED`
provenance. If qualification fails, the result remains auditable but no
calibrated parameter set is created.

See [Experimental fitting and calibration](calibration.md) for the
reference workflow and scientific interpretation.


## Device-observable datasets

Generic device-level experimental data are represented by:

```python
from ncmemsim.experimental import (
    DeviceObservableDataset,
    ExperimentalCondition,
    ExperimentalDatasetMetadata,
)
```

The device-observable layer supports explicit independent-variable and
observable names/units, optional uncertainty, experimental conditions, stable
serialization, and deterministic dataset hashes.

Current F4g adapters cover C–V, memory-window, and retention observables.

## Device calibration bindings

Controlled device-parameter application is available from:

```python
from ncmemsim.device_calibration import (
    DeviceCalibrationContext,
    DeviceCalibrationSpec,
    DeviceFitParameterBinding,
    DeviceFitTarget,
    apply_device_calibration_parameters,
)
```

`DeviceCalibrationSpec` maps an ordered `FitParameterSet` to supported
device, kinetics, tunnelling, or simulation targets.

The binding layer rejects structurally degenerate parameter combinations such
as simultaneous `qfix_C_m2` and `qit_C_m2` fitting, and simultaneous active
fraction plus nanocrystal volume fraction for the same floating gate.

Applying a parameter vector creates a cloned calibration context. It does not
assign `CALIBRATED` provenance.

## Device-level fitting

The first C–V fit adapter is exposed from:

```python
from ncmemsim.device_fit import (
    CVCalibrationProtocol,
    DeviceCVFitResult,
    fit_single_parameter_cv_dataset,
)
```

The F4h2a reference workflow intentionally fits exactly one parameter.

Program-time fitting is exposed from:

```python
from ncmemsim.program_fit import (
    DeviceProgramTimeFitResult,
    ProgramTimeFitProtocol,
    ProgramTimePrediction,
    fit_single_parameter_delta_vfb_vs_programming_time,
    predict_delta_vfb_vs_programming_time,
)
```

The F4h2b2 reference workflow fits one parameter to
\(\Delta V_\mathrm{FB}\) versus fixed-voltage programming time. Every
programming-time point starts from the same initial state.

Successful results report `scientific_status == "FITTED"`.


Retention-fraction fitting is exposed from:

```python
from ncmemsim.retention_fit import (
    DeviceRetentionFractionFitResult,
    RetentionFitProtocol,
    RetentionFractionPrediction,
    fit_single_parameter_retention_fraction,
    predict_retention_fraction,
)
```

The F4h2c2 workflow fits exactly one parameter to
`total_charge_retention_fraction` versus time from a caller-supplied initial
`DeviceState`. It uses the standard `RetentionResult` plus the F4g
`evaluate_retention_objective()` adapter, performs linear interpolation in
physical time, and rejects extrapolation. The protocol requires the
backward-Euler occupancy integrator and a complete declared simulation domain.

`RetentionFractionPrediction` records the continuous simulated trajectory and
an occupation-defined initial-state manifest/hash. `DeviceRetentionFractionFitResult`
records the dataset hash, calibration-specification hash, protocol hash,
parameter-application manifest, fitted numerical result, and objective.

A successful retention fit reports `scientific_status == "FITTED"`; it does
not assign `CALIBRATED` provenance.

### Electro-optical photo-capture fitting

Electro-optical programming-time prediction and fitting are exposed from:

```python
from ncmemsim.photo_program_fit import (
    DevicePhotoMultiConditionFitResult,
    DevicePhotoProgramTimeFitResult,
    ElectroOpticalProgramTimeFitProtocol,
    ElectroOpticalProgramTimePrediction,
    fit_single_parameter_photo_capture_efficiency_multi_condition,
    fit_single_parameter_photo_capture_efficiency_vs_programming_time,
    predict_electro_optical_delta_vfb_vs_programming_time,
)
```

The protocol fixes the electrical pulse/read conditions and optical source
conditions. `photo_capture_efficiency` is supplied separately through
`PhotoTransitionConfig` so the fitted device parameter is not embedded in the
protocol hash.

The single-condition adapter fits one
`DeviceFitTarget.PHOTO_CAPTURE_EFFICIENCY` to illuminated
`delta_vfb`-versus-programming-time data.

The multi-condition adapter fits one shared value across two or more distinct
wavelength/power conditions. Its residual vector is the concatenation of the
per-condition objective residuals. The result includes
`FitUncertaintyDiagnostics` evaluated on the full joint Jacobian and
per-condition bound-scaled Jacobian L2 norms.

`locally_identifiable=True` is a local linearized rank statement conditional
on the fixed optical model. It is not a claim of global identifiability.
For the present one-parameter workflow, a full-rank one-column Jacobian has
scaled condition number one, so that value must not be over-interpreted.

Successful single- and multi-condition photo-capture fits report `FITTED`,
not `CALIBRATED`.

### Photo-capture calibration qualification

Independent device-level qualification of the F4i4 multi-condition fit is
exposed from:

```python
from ncmemsim.photo_calibration import (
    CalibratedPhotoCaptureEfficiency,
    DevicePhotoCalibrationResult,
    qualify_photo_capture_efficiency_fit,
)
```

`qualify_photo_capture_efficiency_fit()` evaluates a declared validation
`DeviceObservableDataset` using the already fitted
`photo_capture_efficiency`. It does not re-optimize the parameter on
validation data.

The validation protocol may vary optical wavelength and/or incident optical
power while preserving the non-optical training protocol. Qualification uses
the generic `CalibrationCriteria` and `CalibrationQualification`
infrastructure.

For the multi-condition training fit, the adapter records a deterministic
hash of the ordered training-dataset hash collection and separately verifies
that a required validation dataset hash is not equal to any individual
training dataset hash.

A successful qualification returns a
`CalibratedPhotoCaptureEfficiency` record with status `CALIBRATED` and a
separate promoted `PhotoTransitionConfig`. Failed qualification returns an
auditable `DevicePhotoCalibrationResult` with
`scientific_status == "NOT_CALIBRATED"` and no promoted parameter/config.

Dataset-hash distinctness is a data-reuse check, not proof of experimental
independence. Experimental calibration claims additionally require suitable
dataset provenance and experimental validation design.

## Explicit electrical pulse protocols

A single program pulse followed by nondestructive readout is represented by:

```python
from ncmemsim.program_protocol import (
    ProgramPulseReadProtocol,
    ProgramPulseReadResult,
    run_program_pulse_read,
)
```

The read step uses zero dwell. `programming_time_s` is the explicit
fixed-voltage pulse duration and is distinct from
`SimulationConfig.dwell_time_s`, which remains the simulator's default
per-voltage relaxation time.

Paired program/erase state preparation is available from:

```python
from ncmemsim.paired_pulse_protocol import (
    PairedPulseMemoryProtocol,
    PairedPulseMemoryResult,
    PulseBranchResult,
    run_paired_pulse_memory_protocol,
)
```

Its signed pulse-defined memory window is:

\[
\Delta V_\mathrm{FB,program}
-
\Delta V_\mathrm{FB,erase}.
\]

This is a state-separation observable and is distinct from
`CVResult.memory_window_V`, which is the dynamic forward/backward C–V
hysteresis window.

See [Device-level calibration and pulse protocols](device_calibration.md) for
the complete semantics and reproducible example.

## Optical absorption

The optical layer model provides:

- Beer-Lambert absorption;
- nanocrystal-volume-fraction effective absorption;
- absorbed photon flux;
- transmitted photon flux;
- average volumetric generation rate;
- floating-gate optical diagnostics.

The principal floating-gate evaluation path is exposed through:

- `evaluate_floating_gate_optical_absorption`

A floating-gate optical result includes quantities such as:

- incident photon flux;
- absorbed photon flux;
- transmitted photon flux;
- nanocrystal absorption coefficient;
- effective absorption coefficient;
- direct, indirect, and Urbach contributions;
- direct and indirect optical gaps.

## Photo-assisted transitions

Photo-assisted charge-state kinetics are configured with:

- `PhotoTransitionConfig`
- `PhotoTransitionWeights`
- `PhotoTransitionRates`
- `PhotoTransitionEvaluation`

The default compact photo-loading model supports:

- 0 -> 1
- 1 -> 2

Photo-assisted detrapping is disabled by default.

Example:

```python
from ncmemsim.photo import PhotoTransitionConfig

photo = PhotoTransitionConfig(
    photo_capture_efficiency=1.0e-7,
)
```

The default photo-capture efficiency is a provisional compact-model
parameter and should not be treated as experimentally calibrated unless
explicitly replaced by a calibrated value.

## Optical simulator diagnostics

When optical programming is enabled, `Simulator.relax_voltage()` exposes
diagnostics including:

- `optical_absorption_fraction`
- `absorbed_photon_flux_m2_s`
- `photo_transition_rate_s`
- `optical_absorption_fraction_by_fg`
- `absorbed_photon_flux_by_fg_m2_s`
- `absorbed_photon_rate_per_nc_by_fg_s`
- `photo_transition_rate_by_fg_s`
- `optical_alpha_nc_by_fg_m_inv`
- `optical_alpha_eff_by_fg_m_inv`

For dark simulations, optical flux and photo-transition rates are zero.

For disabled optical sources, photon flux and photo-transition rates are
zero while wavelength-dependent material properties can remain defined.

## Transport

- `NodeKind`
- `TransportNode`
- `TunnelLink`
- `TunnelNetwork`
- `TransportConfig`
- `TransportEngine`
- `LinkTransportResult`
- `TransportStepResult`

## Retention

- `RetentionConfig`
- `RetentionSolver`
- `RetentionResult`

The v0.11.0 retention-fitting API is provided by the dedicated
`ncmemsim.retention_fit` module rather than the v0.10.0 top-level import
surface. See the device-level fitting section above for the fit protocol,
prediction, and result objects.

## Validation and reproducibility

- `ValidationIssue`
- `ValidationReport`
- `validate_probabilities`
- `validate_device_physics`
- `validate_field_profile`
- `validate_internal_charge_conservation`
- `validate_simulation`
- `build_reproducibility_manifest`

The v0.11.0 fitting/calibration layer also records deterministic dataset,
parameter-specification, solver-configuration, criteria, and
qualification hashes where applicable.

## Golden references and benchmarks

- `build_golden_suite`
- `compare_golden`
- `write_golden_suite`
- `BenchmarkRecord`
- `benchmark_case`
- `run_benchmark_suite`
- `write_benchmark_report`

## Design-space exploration and DTCO (v0.12.0)

Import the dedicated public namespace `ncmemsim.dtco`, rather than assuming
DTCO symbols are re-exported from `ncmemsim`:

- specification: `ParameterBinding`, `DesignVariable`, `ExperimentSpec`;
- execution: `iter_cartesian_points`, `run_cartesian_sweep`;
- metrics/constraints: `MetricDefinition`, `MetricConstraint`,
  `MetricAnalysisSpec`, `analyze_sweep`;
- Pareto: `ParetoAnalysisSpec`, `analyze_pareto`;
- grid sensitivity: `SensitivityAnalysisSpec`, `analyze_sensitivity`;
- reports: `DTCOReport`, `build_dtco_report`, `write_dtco_report`.

See [DTCO](dtco.md) for enums, result types, exact units, evaluator contracts,
complete examples and limitations. Candidate application is copy-on-write;
unsupported MODEL bindings cannot execute. Pareto sorting uses explicit
min/max directions, and sensitivity uses adjacent-grid secants with coverage.
Report restoration checks canonical payload integrity, not authentication.

## Robust DTCO definitions, sampling, propagation and objectives (v0.13.0)

Import from `ncmemsim.dtco`:

- variation laws: `UniformVariation`, `TruncatedNormalVariation`;
- definitions and provenance: `VariationDefinition`, `VariationKind`,
  `VariationProvenance`;
- reproducible sampling: `SamplingSpec`, `sample_variations`;
- exact inputs and restoration: `SampleManifest`;
- explicit bounded-draw exhaustion: `SamplingError`;
- isolated propagation: `propagate_samples`, `SamplePoint`, `SamplePointResult`,
  `PropagationResult`;
- assessed metrics/statistics: `SampleAnalysisSpec`, `SampleMetricPointResult`,
  `SampleAnalysisResult`, `analyze_samples`;
- linked nominal comparison: `NominalResult`, `evaluate_nominal`,
  `NominalComparison`, `compare_nominal`;
- explicit robust objectives/fronts: `RobustStatistic`, `RobustFailurePolicy`,
  `RobustObjective`, `RobustParetoSpec`, `RobustParetoResult`, `analyze_robust_pareto`;
- reproducible bundles: `RobustDTCOReport`, `build_robust_dtco_report`,
  `write_robust_dtco_report`.

H1/H2 support independent continuous DEVICE/OPERATING bindings with canonical
units. H2 records the exact manifest, seed, algorithm, order and runtime; it
does not execute physics. H3 links the full nominal baseline and evaluator to
serial isolated execution with staged failure records. H4 assesses complete-case
metrics/constraints and descriptive statistics with explicit sample identities
and denominators. H5 adds identity-checked nominal comparisons and explicitly
defined robust Pareto objectives with eligibility/failure policies. H6 snapshots
these linked inputs/outcomes into integrity-checked JSON/CSV/Markdown bundles
and supplies an electrical reference. See
[Robust DTCO](robust_dtco.md) for the complete example, rejection policy,
manifest integrity checks and reproducibility limits.

## Compatibility note

Before v1.0, internal module paths and some result-dictionary details may
evolve.

Code intended to survive minor releases should prefer the documented
public imports, documented result objects, and stable simulator entry
points.

## Scientific workflow evidence (v0.14.0)

The dedicated `ncmemsim.workflows` surface captures dataset origin/provenance and
immutable evidence linking existing fits, specifications and optional qualification.
It preserves FITTED and qualification eligibility separately; no provenance is
promoted. See [Scientific workflow integration](scientific_workflows.md#i1-immutable-source-evidence)
for supported source types, identity checks, runtime and scientific limits.

```python
from ncmemsim.workflows import (
    DataOrigin, DatasetEvidence, WorkflowEvidence,
    capture_dataset_evidence, build_workflow_evidence,
    AppliedWorkflowEvidence, WorkflowEvaluator, apply_workflow_parameters,
)
```

`apply_workflow_parameters` returns a `WorkflowEvaluator`, using explicit baseline
device/physics/simulation/photo settings, a matching calibration specification,
captured workflow evidence, a program-pulse/read protocol and `evaluation_id`.
It checks exact canonical fitting units and applies the recorded ordered values
through existing Phase F APIs. `evidence` captures both baseline/applied contexts,
full materials, core physics, optical defaults, protocol and source/runtime links.
`base_device`, `base_protocol` and `evaluation_parameters` return copies;
`fresh_simulator` returns an independent simulator. `evaluate` accepts nominal/G2
or H3 callback arguments and reports `delta_vfb_V` (V) and `mean_occupation` (1).
Use the same `evaluation_id`/`evaluation_parameters` in nominal and sampled studies.
See [I2 application and evaluator adapter](scientific_workflows.md#i2-application-and-evaluator-adapter)
for the supported core implementation, model-side/photo requirements and limits.

The runnable `examples/phase_i3_electrical_workflow_reference.py` connects existing
program-time fitting/qualification, I1/I2 source/application evidence and nominal/
sampled Phase H evaluation with explicit synthetic data. It uses the existing
`RobustDTCOReport` and exports; linked workflow reports and exports are supplied by I6.
See [I3 electrical reference](scientific_workflows.md#i3-synthetic-electrical-workflow-reference)
for units, synthetic qualification threshold, assumed variations and failure mode.


The runnable `examples/phase_i4_electro_optical_workflow_reference.py` uses the
existing photo-capture fitting API and I2 adapter with explicit
`base_photo_config`. Fitted efficiency stays separate from protocol wavelength
and power. Actual nominal/sample responses use the captured photo configuration.
See [I4 electro-optical reference](scientific_workflows.md#i4-synthetic-electro-optical-workflow-reference)
for synthetic qualification limits, exact manifest and failure policies.


I5 adds cross-workflow integration verification without new public API. Existing
`WorkflowEvidence`, `AppliedWorkflowEvidence`, evaluator, nominal comparison and
sample-analysis contracts reject broken links and incompatible execution contexts.
See [I5 integration verification](scientific_workflows.md#i5-cross-workflow-integration-verification)
for recalculated-hash checks, complete-case denominators and archive semantics.


### Linked scientific workflow reports

```python
from ncmemsim.workflows import WorkflowReport, build_workflow_report, write_workflow_report
```

The builder requires typed source/application/Robust DTCO evidence and explicit
ordered `device_variants`, each an iterable of `(DEVICE ParameterBinding, value)`
assignments. Empty assignments declare the unchanged applied device.
`WorkflowReport.from_json` validates hashes and source/context/variant links
without refitting or physics. The writer produces six non-overwriting portable
artifacts. See [I6 report contract](scientific_workflows.md#i6-linked-workflow-report-and-portable-exports).
