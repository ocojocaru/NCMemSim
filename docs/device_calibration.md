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

## Reproducible device-level example

The consolidated reference example is:

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

## Current limitations

The device-level workflows do not yet establish calibrated values for
photo-capture efficiency, program or erase barriers, attempt frequencies,
fixed charge, interface charge, or other device parameters against independent
experimental device datasets.

The paired pulse protocol is currently a simulation protocol, not a complete
end-to-end fit adapter.

Retention already has experimental-data and objective infrastructure, but a
dedicated end-to-end retention fitting workflow is still future work.

Independent experimental validation and explicit calibration qualification
remain necessary before a fitted device parameter can be described as
experimentally calibrated.
