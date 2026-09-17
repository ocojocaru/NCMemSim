# Device-Level Calibration and Pulse Protocols

NCMemSim v0.11.0 extends the generic fitting and calibration infrastructure
to electrical and device-level observables while preserving a strict
distinction between numerical fitting and experimental calibration.

The device-level workflows are deliberately conservative. They use controlled
parameter bindings, explicit protocol objects, reproducibility hashes, and
single-parameter reference fits before any broader multi-parameter calibration
is attempted.

## Scope

The implemented device-level calibration layer currently covers:

- controlled mapping from fit parameters to device, kinetics, tunnelling, and
  simulation parameters;
- synthetic single-parameter C–V fitting;
- explicit fixed-voltage program pulses followed by zero-dwell readout;
- synthetic fitting of \(\Delta V_\mathrm{FB}\) versus programming time;
- independent program and erase branches for a pulse-defined memory window.

- illuminated program-pulse prediction with explicit optical conditions;
- single-parameter fitting of `photo_capture_efficiency`;
- shared `photo_capture_efficiency` fitting across multiple wavelength/power conditions;
- local joint-Jacobian uncertainty and identifiability diagnostics.
- independent validation qualification of a multi-condition fitted `photo_capture_efficiency` without refitting;
- auditable calibrated-parameter records and separate `PhotoTransitionConfig` promotion only when all declared criteria pass.

These workflows are infrastructure and validation references. A successful
synthetic recovery result has scientific status `FITTED`, not `CALIBRATED`.

## Controlled parameter bindings

Device-level fit parameters are declared with:

```python
from ncmemsim.device_calibration import (
    DeviceCalibrationSpec,
    DeviceFitParameterBinding,
    DeviceFitTarget,
)
```

A `DeviceCalibrationSpec` combines an ordered `FitParameterSet` with explicit
bindings from parameter names to supported simulator targets.

The binding layer intentionally does not accept arbitrary attribute-path
strings. Supported targets include floating-gate geometry and barriers,
kinetic attempt frequencies, selected tunnelling parameters, and simulation
electrostatic terms.

The current identifiability policy rejects structurally degenerate parameter
pairs such as:

```text
qfix_C_m2 + qit_C_m2
```

and, for the same floating gate:

```text
electrically_active_fraction + nc_volume_fraction
```

because those pairs enter the present model through indistinguishable
combinations for the relevant observables.

The specification also emits warnings for strongly correlated combinations
such as attempt frequency plus barrier height. Warnings are not a substitute
for experimental identifiability analysis.

## Synthetic C–V fitting

The first end-to-end device fitting workflow is exposed from:

```python
from ncmemsim.device_fit import (
    CVCalibrationProtocol,
    DeviceCVFitResult,
    fit_single_parameter_cv_dataset,
)
```

`CVCalibrationProtocol` defines the simulated C–V voltage range and point
count. The reference F4h2a workflow fits exactly one free parameter.

The synthetic validation case recovers `qfix_C_m2` from a C–V curve generated
with a known fixed charge. The fitted result records:

- dataset identity and hash;
- calibration-specification hash;
- protocol hash;
- deterministic least-squares result;
- observable-space objective diagnostics;
- the parameter-application context.

A successful result reports:

```text
scientific_status = FITTED
```

It does not promote the parameter to `CALIBRATED`.

## Two meanings of memory window

NCMemSim now contains two intentionally distinct memory-window concepts.

### Dynamic C–V hysteresis window

`CVResult.memory_window_V` is computed from the forward and backward C–V
sweeps produced by `Simulator.simulate_cv()`.

Conceptually:

```text
forward C–V crossing
backward C–V crossing
        ↓
dynamic C–V hysteresis window
```

The sweep is stateful. Each voltage point uses
`SimulationConfig.dwell_time_s` as the default per-voltage relaxation time,
and the backward sweep starts from the final forward-sweep state.

Therefore `SimulationConfig.dwell_time_s` must not be reinterpreted as a
standalone program-pulse duration.

### Pulse-defined state-separation window

`PairedPulseMemoryResult.memory_window_V` is defined from two independently
prepared states:

\[
\mathrm{MW}_\mathrm{pulse}
=
\Delta V_\mathrm{FB,program}
-
\Delta V_\mathrm{FB,erase}.
\]

Conceptually:

```text
common reference state
    ├─ program pulse → zero-dwell read → ΔVFB_program
    └─ erase pulse   → zero-dwell read → ΔVFB_erase

MW_pulse = ΔVFB_program - ΔVFB_erase
```

The two branches start from the same reference state. Neither branch is
initialized from the terminal state of the other.

The result also exposes:

```text
memory_window_magnitude_V = abs(memory_window_V)
```

so the signed convention and the absolute state separation remain explicit.

These two memory-window definitions are not interchangeable.

## Explicit program-pulse readout

A single electrical program pulse is represented by:

```python
from ncmemsim.program_protocol import (
    ProgramPulseReadProtocol,
    ProgramPulseReadResult,
    run_program_pulse_read,
)
```

The protocol separates pulse duration from the simulator's default sweep
dwell:

```text
initial state
→ relax_voltage(Vprog, dwell_time_s=tprog)
→ programmed state
→ relax_voltage(Vread, dwell_time_s=0)
→ ΔVFB readout
```

`programming_time_s` is therefore the duration of one fixed-voltage program
pulse.

The read step uses `dwell_time_s=0.0`. It evaluates the programmed state at
the declared read bias without intentional kinetic evolution. The simulator
may still perform zero-time normalization and diagnostic evaluation, so tests
compare populations at floating-point precision rather than requiring
bitwise identity.

The natural observable of this single-state protocol is
`delta_vfb_V`. It is intentionally not called a memory window.

## \(\Delta V_\mathrm{FB}\) versus programming time

The program-time fitting workflow is exposed from:

```python
from ncmemsim.program_fit import (
    DeviceProgramTimeFitResult,
    ProgramTimeFitProtocol,
    ProgramTimePrediction,
    fit_single_parameter_delta_vfb_vs_programming_time,
    predict_delta_vfb_vs_programming_time,
)
```

For a dataset with:

```text
independent variable: programming_time [s]
observable:           delta_vfb [V]
condition:            program_voltage [V]
```

every time point is simulated from the same initial state.

For example:

```text
common initial state
    ├─ 0.1 ms pulse → read ΔVFB
    ├─ 0.3 ms pulse → read ΔVFB
    └─ 1.0 ms pulse → read ΔVFB
```

The 0.3 ms pulse does not start from the 0.1 ms terminal state, and the
1.0 ms pulse does not start from the 0.3 ms terminal state.

The F4h2b2 synthetic reference fit recovers `nu0_Hz` with one free parameter.
This restriction is intentional because `nu0_Hz`, the program barrier, and
several WKB parameters are correlated in the current compact model.

## Paired program/erase protocol

Pulse-defined state separation is available from:

```python
from ncmemsim.paired_pulse_protocol import (
    PairedPulseMemoryProtocol,
    PairedPulseMemoryResult,
    PulseBranchResult,
    run_paired_pulse_memory_protocol,
)
```

A `PairedPulseMemoryProtocol` declares:

```text
program voltage
program time
erase voltage
erase time
read voltage
optional internal pulse timestep
```

Both branches use a zero-dwell read. The serialized result records the
protocol hash, both branch results, the signed pulse-defined memory window,
and its magnitude.

The reference test uses a partially occupied common state so both injection
and emission dynamics are exercised. A completely empty electronic state can
make the erase branch trivial in the present occupancy model.

## Existing device-observable datasets

`DeviceObservableDataset` and `ExperimentalCondition` provide the generic
device-data representation used by the F4g infrastructure:

```python
from ncmemsim.experimental import (
    DeviceObservableDataset,
    ExperimentalCondition,
    ExperimentalDatasetMetadata,
)
```

Current device-observable support includes C–V, memory-window, and retention
data adapters.

The existing memory-window-versus-programming-time objective accepts supplied
C–V results. It must not be silently reinterpreted as the new fixed-voltage
pulse protocol. The two workflows have different experimental semantics.

A future adapter may explicitly connect a pulse-defined memory-window dataset
to `PairedPulseMemoryResult`, but that connection is not implied by the
current API.

## Electro-optical photo-capture fitting

The F4i workflow adds a dedicated electro-optical program-time fitting layer:

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

`ElectroOpticalProgramTimeFitProtocol` fixes the electrical pulse/read
conditions, monochromatic `LightSource`, `PhotoTransitionWeights`, and
occupancy integrator. The device-level `photo_capture_efficiency` is supplied
separately through `PhotoTransitionConfig`; it is not part of the protocol
hash.

For a programming-time dataset, every time point is simulated independently
from the same initial state. Illumination is active during the program pulse
only. Readout is dark and uses zero dwell.

The single-condition workflow fits exactly one free parameter:

```text
DeviceFitTarget.PHOTO_CAPTURE_EFFICIENCY
```

The multi-condition workflow fits the same parameter simultaneously against
two or more datasets. F4i4 deliberately allows the optical source wavelength
and/or incident optical power density to vary while keeping the electrical
program/read conditions, transition weights, numerical integration settings,
and device parameterization fixed. The optimizer receives the concatenation
of all per-condition objective residuals.

The multi-condition result attaches the generic
`FitUncertaintyDiagnostics` computed from the full joint Jacobian. It records
the local Jacobian rank, bound-scaled singular values, scaled condition
number, covariance and standard error when available, and a
`locally_identifiable` flag. It also exposes
`condition_scaled_jacobian_l2_norms`, which reports the local sensitivity
magnitude contributed by each optical condition.

For the current single-free-parameter workflow, a nonzero full-rank
one-column Jacobian has a scaled condition number of one. That numerical fact
must not be interpreted as strong evidence of global identifiability.
`locally_identifiable=True` means only that the local linearized joint
Jacobian has full column rank under the fixed optical model.

In particular, the F4i4 result does not by itself separate
`photo_capture_efficiency` from systematic errors or uncertainty in incident
optical power, absorption amplitudes, nanocrystal density, or
photo-transition weights. Those quantities are fixed in this workflow.

All F4i3/F4i4 synthetic recovery results remain:

```text
scientific_status = FITTED
```

They are not promoted to `CALIBRATED`. Independent device-observable
validation and explicit calibration qualification are required for that
promotion.

## Photo-capture numerical sensitivity audit

The F4i3 single-parameter synthetic recovery was followed by a dedicated
timestep-sensitivity and cross-grid audit before device-level calibration
qualification.

The reference benchmark uses:

```text
wavelength                  1550 nm
incident optical power      1000 W/m^2
programming times           0.1, 0.3, 1.0 ms
true photo-capture eta      2e-7
practical timestep          1e-5 s
refined reference timestep  2.5e-6 s
```

An eta sweep from zero through `1e-6` showed a monotonic, essentially linear
photo-induced `delta_vfb` response over this benchmark range. At `eta=0`, the
remaining `delta_vfb` was at numerical-zero scale, approximately `1e-21 V`.

For `eta=2e-7`, timestep refinement from `1e-5 s` to `5e-6 s` and
`2.5e-6 s` changed the predicted programming-time curve only at floating-point
roundoff scale. Relative to the `2.5e-6 s` reference, the `1e-5 s` prediction
had:

```text
maximum absolute delta_vfb difference  2.12e-21 V
RMSE                                    1.23e-21 V
```

A cross-grid fit generated synthetic truth at `2.5e-6 s` and fitted it with
the practical `1e-5 s` grid. It recovered:

```text
true eta                    2.000000000000e-7
fitted eta                  2.000000000000e-7
relative eta bias           1.32e-16
delta_vfb RMSE              1.37e-22 V
optimizer evaluations       7
scientific status           FITTED
```

These values justify `1e-5 s` as a practical reproducible timestep for this
specific synthetic benchmark. They do **not** establish a universal optical
programming timestep, a universal numerical tolerance, or experimental
calibration accuracy. The near-machine-precision agreement also reflects the
low-signal, nearly linear regime exercised by this benchmark and must not be
generalized to stronger optical loading or different pulse regimes without a
new convergence audit.

The reproducible audit is:

```text
examples/phase_f4i_photo_capture_timestep_convergence.py
```

Run it with:

```bash
python examples/phase_f4i_photo_capture_timestep_convergence.py
```

## Independent photo-capture calibration qualification

F4i5 adds a device-level qualification adapter:

```python
from ncmemsim.photo_calibration import (
    CalibratedPhotoCaptureEfficiency,
    DevicePhotoCalibrationResult,
    qualify_photo_capture_efficiency_fit,
)
```

The adapter accepts an already completed
`DevicePhotoMultiConditionFitResult`, a validation
`DeviceObservableDataset`, a matching
`ElectroOpticalProgramTimeFitProtocol`, and explicit
`CalibrationCriteria`.

The fitted `photo_capture_efficiency` is used **unchanged** on the validation
dataset. The qualification path performs no parameter re-optimization.

The validation protocol may change optical wavelength and/or incident optical
power, but it must preserve the non-optical training protocol: program/read
voltages, program timestep, photo-transition weights, and occupancy
integrator.

Because F4i4 training uses multiple datasets, F4i5 stores a deterministic hash
of the ordered training-dataset hash collection. When distinct validation is
required, the validation dataset hash must also differ from **every**
individual training dataset hash. A validation dataset that reuses any
training dataset therefore fails the `distinct_validation_dataset` criterion.

Passing all configured criteria creates:

```text
CalibratedPhotoCaptureEfficiency
status = CALIBRATED
```

plus a separate `PhotoTransitionConfig` containing the qualified
`photo_capture_efficiency`. Failed qualification remains fully auditable and
returns:

```text
scientific_status = NOT_CALIBRATED
```

with no calibrated parameter record and no promoted photo configuration.

The qualification record includes the training-dataset collection hash,
validation-dataset hash, validation-protocol hash, criteria hash through the
generic qualification object, and qualification hash. Model-based fit
uncertainty remains in the fit/qualification diagnostics and is not copied
into source-reported experimental uncertainty.

### What hash distinctness does and does not establish

Dataset-hash distinctness is a reproducibility and data-reuse safeguard. It
shows that the validation dataset is not identical to any training dataset as
serialized by NCMemSim.

It does **not** by itself establish experimental independence. For a physical
calibration claim, independence must also be supported by the dataset
provenance and experimental design, for example by a held-out device,
measurement run, sample, or other declared validation split appropriate to
the experiment.

### Synthetic software-validation example

The F4i5 reference example deliberately contains two synthetic validation
cases:

```text
compatible synthetic validation   -> CALIBRATED
incompatible synthetic validation -> NOT_CALIBRATED
```

The first verifies the positive software promotion path. The second perturbs
the synthetic validation observable so the declared RMSE criterion fails,
demonstrating that qualification is blocked rather than silently weakening
the threshold.

These statuses are **software-validation outcomes relative to synthetic input
datasets and declared criteria**. They do not establish that the physical
value of `photo_capture_efficiency` is experimentally calibrated.

## Reproducible device-level example

The consolidated electrical/device reference example is:

```text
examples/phase_f4h_device_calibration.py
```

It demonstrates three separate workflows:

```text
1. synthetic C–V recovery of qfix_C_m2
2. synthetic ΔVFB(tprog) recovery of nu0_Hz
3. paired program/erase pulse-defined memory window
```

Run it with:

```bash
python examples/phase_f4h_device_calibration.py
```

or serialize the results with:

```bash
python examples/phase_f4h_device_calibration.py \
    --output device_calibration_result.json
```

The example is self-generated synthetic validation. It demonstrates numerical
recovery and protocol semantics, not experimental calibration.

The electro-optical F4i reference example is:

```text
examples/phase_f4i_photo_capture_fit.py
```

Run it with:

```bash
python examples/phase_f4i_photo_capture_fit.py
```

or serialize the full joint fit and compact summary with:

```bash
python examples/phase_f4i_photo_capture_fit.py \
    --output photo_capture_fit_result.json
```

It generates three synthetic optical conditions with one common
`photo_capture_efficiency`, performs a shared fit, and reports the joint local
identifiability diagnostics. Its scientific conclusion is
`FITTED_NOT_CALIBRATED`.

The F4i5 qualification reference example is:

```text
examples/phase_f4i_photo_capture_calibration.py
```

Run it with:

```bash
python examples/phase_f4i_photo_capture_calibration.py
```

or serialize the training fit and both qualification outcomes with:

```bash
python examples/phase_f4i_photo_capture_calibration.py \
    --output photo_capture_calibration_result.json
```

It reports one compatible synthetic validation case that exercises the
`CALIBRATED` promotion path and one incompatible synthetic validation case
that remains `NOT_CALIBRATED`. The example labels itself
`SYNTHETIC_SOFTWARE_VALIDATION` and explicitly makes no experimental
calibration claim.

## Current limitations

The photo-capture workflow now provides explicit post-fit qualification
against a validation dataset, but NCMemSim does not yet bundle an independent
experimental device dataset that establishes an experimentally calibrated
`photo_capture_efficiency`. The F4i5 synthetic example validates the software
qualification mechanism only.

Program or erase barriers, attempt frequencies, fixed charge, interface
charge, and other device parameters likewise remain without independent
experimental device calibration in the bundled reference workflows.

The paired pulse protocol is currently a simulation protocol, not a complete
end-to-end fit adapter.

The current photo-capture multi-condition workflow holds optical-model
quantities such as absorption amplitudes and transition weights fixed. Its
local identifiability diagnostics therefore do not establish global
identifiability against those nuisance quantities.

Independent experimental validation and explicit calibration qualification
remain necessary before a fitted device parameter can be described as
experimentally calibrated.
