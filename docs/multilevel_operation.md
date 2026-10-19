# Multilevel and neuromorphic operation - Phase Q

## Q0 status and baseline

Q0 is complete: repository audit, initial scientific scope and Q1-Q7 acceptance
sequence are defined here. Q1 declaration contracts are now implemented in
`ncmemsim.multilevel_contracts`; Q2 execution and static result archives are now
implemented in `ncmemsim.multilevel_execution`. Q3-Q7 remain pending. The Q0 audit is retained as
its historical planning snapshot, not updated to imply Q1 existed at Q0.
Q0 introduced no runtime implementation, public API,
material law, calibrated parameter or new device family.

Baseline: published v1.7.0, tag commit
`cf640a37cf474c0cec17c756fabae9be5acab685`, followed by DOI closure at
`7056b579428f86647f48edeb9365feef4a47d8d0`.
Version DOI: [10.5281/zenodo.23316663](https://doi.org/10.5281/zenodo.23316663).
Target: v1.8.0, subject to Q7 acceptance. Package and citation identity remain
published v1.7.0 during Q0. The [machine-readable audit](multilevel_operation_audit.json)
records the inspected source identities and decisions as of 2026-10-19.

Phase P experimental P4B/P5B/P6B qualification remains deferred. Q can develop
software and synthetic reference studies without closing those experimental gates.

## Scientific objective

Study how explicit electrical and electro-optical pulse sequences produce
several distinguishable read states, gradual updates and retention drift in the
existing one-to-three-FG Ge/GeSn compact device family. Preserve the full charge
state and the history needed to reproduce each readout.

The first neuromorphic output is a **readout-derived normalized weight proxy**.
It does not establish a channel conductance, measured synaptic response or an
in-memory computation demonstration. A current/channel mapping, array circuit,
learning algorithm or physical degradation model requires a separate contract.

## Audit of reusable components

| Source | Existing capability | Q decision |
|---|---|---|
| `ncmemsim/state.py` | Per-FG P0/P1/P2 arrays, normalized occupation and device time | Retain the full state; a scalar readout cannot uniquely identify charge distribution |
| `ncmemsim/simulator.py` | `relax_voltage`, sequential sweep, compact electrostatic readout and optional photo rates | Reuse existing physics through explicit owned contexts; do not change legacy stepping defaults |
| `ncmemsim/program_protocol.py` | One program pulse followed by a declared read | Preserve the single-pulse API; add a separate general sequence contract |
| `ncmemsim/paired_pulse_protocol.py` | Independent program and erase branches from one reference state | Do not reinterpret independent branches as a state-continuing pulse train |
| `ncmemsim/om2_sweep.py` | State-continuing endpoint holds and dark sweeps, strict partial-result records | Reuse ownership/accounting principles; preserve the specific OM-2 sequence and archive semantics |
| `ncmemsim/device_photo_experiment.py` | Explicit sample-plane input, matched dark control, retained read states | Preserve illumination evidence and zero-dwell read roundoff handling |
| `ncmemsim/spectral_context.py` | Owned spectrum/device path and illuminated-pulse/dark-read execution | Optical sequence steps need exact source/context linkage and exposure duration |
| `ncmemsim/temperature_context.py`, `ncmemsim/structural_optical_context.py` | Explicit thermal/structural context ownership | Keep material resolution explicit and fixed for the first sequence reference |
| `ncmemsim/retention.py` | Biased/zero-bias state evolution and retention outputs | Reuse state evolution; record actual elapsed time and any early stop |
| `ncmemsim/ensemble/execution.py`, `ncmemsim/ensemble/model_execution.py` | Isolated realization and failure accounting | Extend only supported bindings; separate between-device variation from pulse-to-pulse randomness |
| `ncmemsim/om2_numerics.py`, `ncmemsim/om2_reporting.py` | Immutable study records and strict reproducibility bundles | Reuse validation patterns, not a new meaning for existing OM-2 schemas |
| `docs/independent_calibration.md` | Admission and independent-validation requirements | Preserve FITTED/CALIBRATED distinctions; synthetic pulse results admit no measured dataset |

This is a source audit, not a fresh numerical convergence study or a certification
of each inherited model's experimental accuracy.

## First implementation boundary

### Sequence and state ownership

An owned sequence must bind one device/physics context, explicit initial state,
ordered step identities and read policy. Steps declare finite gate voltage in V,
duration in s, integration control, role and illumination status. Positive-duration
write/erase/idle steps are distinct from zero-dwell read events. A role label does
not guarantee the sign of the update. Reject ambiguous units, invalid durations,
non-finite inputs, duplicate identities and unsupported context combinations.

The first implementation uses finite, explicit open-loop piecewise-constant
sequences and the existing backward-Euler occupancy integrator, selected
explicitly. Program-and-verify feedback and arbitrary continuous waveforms are
later candidates. No hidden reset, clipping, state renormalization, resampling or
parameter fitting may make a requested trajectory appear successful.

Within a trajectory, each completed physical step continues from the previous
final state and advances the device clock by the declared duration. Independent
target preparations, matched-dark controls and ensemble realizations receive
their own copies. Store initial, post-step and read states with their identities.
A nondestructive zero-dwell read must have declared numerical tolerances and
preserve original stored states; the inherited ULP-scale normalization issue must
not become an undocumented state edit. Finite-dwell read disturbance is outside
the first Q reference and cannot be labelled nondestructive.

For optical steps, the exact spectrum, reference plane, power/area, capture
settings and exposure duration belong to the sequence evidence. Idle and dark
read steps must not inherit light implicitly. Reuse existing thermal and optical
applicability checks. No new substrate photogeneration or GeSn coefficient law is
introduced. Temperature and structural context stay fixed within the first train.

### Readout and weight proxy

The first scalar readout is the simulator's signed compact `delta_vfb_V`, in V,
at one declared dark, zero-dwell read condition. Retain per-FG charge and
occupation as physical diagnostics. Do not substitute a C-V branch-crossing
window, threshold voltage or measured instrument response for this observable.

An optional dimensionless proxy uses declared finite reference readouts:
`w = (R - R_low) / (R_high - R_low)`, with `R_high > R_low`.
Reference identity, preparation, units and applicability must accompany the
mapping. Do not choose new minima/maxima independently for each trajectory,
retention time or ensemble member. Out-of-range weights remain visible and are
not clipped to [0, 1]. A collapsed or unqualified reference interval makes the
proxy not assessable, rather than zero. The proxy is not a conductance in siemens.

Potentiation/depression refer only to declared increases/decreases in this proxy.
Pulse polarity, electron charge, `delta_vfb_V` and proxy direction must be mapped
explicitly before applying those labels. Retain wrong-direction and nonmonotonic
updates as outcomes. Do not sort a trajectory or reverse signs to improve it.

### Multilevel separation and update diagnostics

Declare target level identities, their order, preparation histories, common
read condition, minimum readout margin in V and optional readout interval widths
before analysis. Distinct deterministic readouts alone do not establish a
noise-limited memory capacity. With explicit interval half-widths `h_i`, the
adjacent signed margin is `(R_(i+1) - h_(i+1)) - (R_i + h_i)` in declared order.
Use zero widths only for a stated deterministic diagnostic. Assumed intervals,
numerical tolerances and measured statistical uncertainty remain different inputs.
Crossed levels or insufficient margins fail the criterion; missing observations
are not assessable. Never invent read noise from timestep differences.

Preserve raw signed updates `R_(k+1) - R_k`, pulse counts, elapsed time, reference
span, saturation and direction reversals. Q4 will freeze explicit definitions for
linearity deviation and paired update asymmetry, including index alignment,
normalizers and coverage. A branch with too few reads or insufficient dynamic
range cannot receive a favourable normalized score. Identical repeated pulses
test gradual updates; any varying amplitudes/durations must remain visible.

Q5 retention probes start from copies of each prepared level and use fixed read
references and margins. Report signed drift, level crossings and covered times;
do not simulate successive independent delays by inadvertently accumulating them.
Ensemble summaries retain attempted, completed, metric-assessable and failed
counts, exact denominator policy and sample identities. A deterministic solver
repeated on identical inputs does not represent cycle-to-cycle stochastic noise.

## Scientific exclusions

- No channel-current/conductance model, resistor crossbar, circuit-level MAC,
  network training, STDP rule or application-accuracy claim.
- No fatigue, trap creation, irreversible damage, breakdown, measured endurance
  or lifetime prediction. A completed update-cycle count is an operating-history
  count only, not a physical endurance estimate.
- No automatic energy-per-update calculation from FG charge changes. Device
  terminal work, leakage and delivered optical energy need explicit accounting;
  absorbed optical energy alone is not total programming energy.
- No new manufacturing-yield, independent calibration, read-noise or universal
  effective-number-of-bits claim from synthetic state separation.
- No new physics, silent changes to optical/transport defaults, arbitrary MODEL
  mutation, or reinterpretation of existing published archives.

## Delivery sequence and acceptance

| Step | Planned deliverable | Acceptance |
|---|---|---|
| Q0 (complete) | Audit, scientific boundary, terminology and staged plan | Source-linked planning only; published v1.7 identity and P experimental deferrals retained |
| Q1 (complete) | Immutable step/sequence, readout and reference-mapping contracts | Explicit units, ownership, ordering, applicability, hashes, strict round trips and rejection of ambiguous definitions; no execution by declaration |
| Q2 (complete) | Isolated state-continuing electrical sequence execution | Reproduce single-pulse baseline, correct state/time chain, no input mutation, explicit read semantics and partial-failure retention |
| Q3 | Multilevel preparation and separation analysis | Common read/margin definitions, retained reversed/collapsed/missing levels and controlled electrical reference with timestep checks |
| Q4 | Gradual-update analysis and optical sequence integration | Named linearity/asymmetry definitions, valid normalizers, paired dark control, optical budgets, no conductance substitution and controlled update references |
| Q5 | Retention drift and supported ensemble evaluation | Fixed references, independent delay probes, exact sample/coverage accounting, zero-variation baseline and no noise/yield/endurance inference |
| Q6 | Applied references, strict reports and reproducibility bundles | Electrical/optical normal and negative cases, source-linked states/metrics and no-replay restoration with tamper rejection |
| Q7 | v1.8 additive API/archive review and release gates | Complete regression, strict docs, clean installed wheel/sdist, supported-Python CI and exact-candidate publication/citation checks |

Acceptance is not a promise of a particular number of stable levels or a
favourable update curve. A reproducible negative result remains a valid study
outcome. Implementation must review each new API/result schema at its own stage.

## Q1 electrical declaration contracts

Q1 adds six module-qualified types, without changing top-level v1 exports:

| Contract | Meaning |
|---|---|
| `PulseSequenceEvidence` | Source, locator, declaration kind and notes; experimental qualification remains false even for a measured-source declaration |
| `ElectricalPulseStep` | Identified program/erase/idle constant-voltage segment, positive duration and resolving timestep, explicitly dark and backward Euler |
| `DarkReadoutPolicy` | One common signed `delta_vfb_V` read condition, zero dwell, initial/after-step sampling and retained original states |
| `WeightReferenceMapping` | Fixed ordered readout reference pair, explicit minimum span, preparation/applicability evidence and exact context/readout hashes |
| `ElectricalPulseSequence` | Nonempty immutable ordered step tuple, unique IDs, fixed readout, total duration and read-count projections |
| `ElectricalSequenceExperiment` | Owned resolved thermal/electrical context, sequence, copied initial-state JSON and optional matching reference declaration |

Q1 is **declarative**. There is no runner, read execution or normalization method.
`from_state` captures a request, not a simulated result. Q2 supplies a separate
runner and result type for physical execution and read audits. Optical steps, source switching and finite-dwell reads
are rejected by the Q1 electrical schema; optical integration remains for Q4.
The `program`/`erase` role labels do not guarantee update direction.

Numeric inputs reject booleans, text and non-finite values. A segment timestep
must not exceed its duration, integration subdivision counts must be finite, and
sequence duration/absolute initial time must permit representable clock advances.
Archived schemas, fields, units, read policies and derived counts/durations are
checked strictly. Duplicate JSON keys, non-finite metadata and mismatched source
hashes are rejected. Each `to_dict` or `initial_state` access returns independent
data. Mutating caller-owned states, nested metadata or returned dictionaries does
not change the captured experiment. Hashes establish consistency, not source
authenticity or experimental validation.

The reference interval must be finite, ordered and at least `minimum_span_V` wide.
Invalid reference declarations raise an input error in Q1. A later result with
missing/insufficient readout evidence will instead be not assessable. No weights
are clipped and no inferred per-trajectory extrema replace the fixed references.
The minimum span is a declared numerical/study threshold, not a measured error.

The static read policy records a probability audit with absolute tolerance
`1e-12` and zero relative tolerance, retaining original states. This numerical
mass/read audit is neither experimental read noise nor a license to change the
stored preparation. It does not turn a finite-dwell read into a nondestructive one.

### Executable declaration example

```python
from ncmemsim import DeviceBuilder, DeviceState
from ncmemsim.temperature_context import ThermalContext
from ncmemsim.multilevel_contracts import (
    PulseSequenceEvidence, ElectricalPulseStep, DarkReadoutPolicy,
    WeightReferenceMapping, ElectricalPulseSequence, ElectricalSequenceExperiment,
)

device = DeviceBuilder.v2(n_fgs=1)
context = ThermalContext.from_nominal(device).resolve()
evidence = PulseSequenceEvidence(
    "Q1 synthetic declaration", "documentation example", "synthetic",
    "Assumed pulse and read references; no measured calibration.",
)
readout = DarkReadoutPolicy("common-dark-read", 0.0, evidence)
sequence = ElectricalPulseSequence(
    "two writes and an idle",
    (
        ElectricalPulseStep("write-1", "program", 2.0, 1e-7, 1e-9),
        ElectricalPulseStep("idle-1", "idle", 0.0, 2e-8, 1e-9),
        ElectricalPulseStep("write-2", "program", 2.0, 1e-7, 1e-9),
    ),
    readout, evidence,
)
references = WeightReferenceMapping(
    "assumed reference pair", context.context_hash, readout.contract_hash,
    -0.2, 0.3, 0.01, "declared low preparation", "declared high preparation",
    "This resolved device and common read condition only", evidence,
)
experiment = ElectricalSequenceExperiment.from_state(
    "Q1 owned request", context, sequence, DeviceState.empty_for_device(device),
    references,
)
restored = ElectricalSequenceExperiment.from_json(experiment.to_json())
assert restored.contract_hash == experiment.contract_hash
assert sequence.to_dict()["read_count_if_complete"] == 4
assert experiment.to_dict()["experimental_qualification"] is False
```

Static material/context resolution and state validation can occur when capturing
or restoring a request. They do not advance occupancy, run a retention workflow,
evaluate optical absorption or draw random samples. Existing optical/structural
adapters are not accepted as this electrical experiment's context by duck typing.

## Q2 isolated electrical execution

`ncmemsim.multilevel_execution` exports `run_electrical_sequence` and
`ElectricalSequenceResult`. The runner accepts only an owned Q1
`ElectricalSequenceExperiment`, creates its own simulator and executes each
dark constant-voltage step with its explicit timestep and backward-Euler
integrator. Existing simulator and single/paired-pulse defaults are unchanged.

An initial dark read precedes the first physical step. Each subsequent read
has zero dwell and uses the one declared read voltage. The full original
physical state continues to the next step; an audited read's returned state
never silently replaces that physical state. Store the physical and returned
read states separately, including their original arrays and metadata. Per-FG
charges, occupations and signed compact `delta_vfb_V` refer to the stored read
state. This is not a C-V crossing window or a voltage difference from the
initial read. The initial read provides the preparation's own readout.

Read verification checks exact time and state identity/metadata, maximum
probability-coordinate change against Q1's `1e-12` absolute tolerance, and
static charge/electrostatic observables recomputed from the read state. Local
fields/potentials can change because read voltage differs from writing voltage.
Observable reconstruction uses relative tolerance `1e-12` and absolute tolerance
`1e-20 C/m2` for per-FG charge or `1e-14` in the stored voltage/dimensionless
coordinate. These are archive consistency tolerances, not read noise or an
experimental error budget. No stored state or readout is clipped or rewritten.

### Failures and partial results

Invalid request declarations raise before execution. Runtime failures instead
produce a result retaining accepted earlier observations and a failure record
with stage, step index, exception type and message. The first failure stops the
sequence. Stages are `setup`, `initial_read`, `step` and post-step `read`.

A successful physical step remains in the archive if its subsequent read fails.
Its `read` is null, and `final_state` still returns that completed physical state.
A failed/unauditable read has no accepted read observation. A solver exception
inside a step exposes no claimed final state for that unfinished step. Separate
requested, attempted and completed step/read counts make both cases visible.
Setup or initial-read failure retains the declared initial physical state.
Elapsed physical time follows accepted physical states, not read count.

Result restoration checks schema, source hash, runtime declarations, ordered
prefix, state/time chain, original read-state audits, failure location and summary.
It rebuilds static projections without running occupancy integration, optical
absorption, retention or an RNG. Integrity hashes do not authenticate a laboratory
measurement or independently prove that an archived trajectory was executed.

### Controlled executable reference

`examples/phase_q2_electrical_sequence_reference.py` starts a one-FG V2 device
from explicitly assumed P0=0.8, P1=0.2, P2=0. It declares +2 V writing for
1e-8 s, a 0 V idle for 2e-9 s, another +2 V writing segment for 1e-8 s and
a -2 V erase segment for 1e-8 s. Each step uses 1e-10 s internal timestep.
All five reads are dark at 0 V with zero dwell. Role names are declarations,
not guarantees of a particular sign or magnitude of charge update.

```bash
python examples/phase_q2_electrical_sequence_reference.py --output q2-result.json
python examples/phase_q2_electrical_sequence_reference.py --input q2-result.json --output q2-restored.json
```

The result archive includes the source request, original physical/read states,
runtime versions, counts, raw readouts and retained failures. It does not compute
normalized weights, level separation, update linearity or experimental capacity.
Those analyses belong to Q3-Q5. Strict report bundles remain a Q6 deliverable.

Tests compare direct sequential backward-Euler stepping for 1-3 FGs, a retained
single-pulse protocol at the same explicitly selected integrator, continuity
under an extra zero-dwell read, and timestep halving at fixed physical waveform.
The controlled test fixture uses `1e-6` absolute bounds on occupation/read-voltage
changes for the refinement comparison. These are example regression thresholds,
not a convergence proof or measured precision. Numerical comparisons do not
change the default explicit integrator of historical single-pulse calls.

## Compatibility and validation ladder

Keep the existing v1 APIs, source provenance, numerical defaults, deterministic
calls, historical readers and exact archived observations. Use additive,
module-qualified Q interfaces rather than changing the meaning of paired-pulse,
OM-2, retention, ensemble or DTCO contracts.

Start with identity and invalid-input checks, then one-pulse equivalence,
state/time continuity and zero-duration read audits. Add timestep refinement at
fixed physical waveform, probability/charge accounting, matched dark/zero-photo
controls, saturation/reversal/collapsed-reference cases and deliberate failures.
Do not substitute timestep refinement for experimental uncertainty or model
validation. Any numerical tolerance must state its units and purpose.

Each result retains device/context/sequence hashes, original initial state,
completed step evidence, selected observable and mapping, failures and unassessed
metrics, runtime versions and provenance. Restore derived static summaries
without rerunning occupancy integration, optics, fitting or an RNG. Distinguish
invalid input, execution failure, insufficient coverage and a scientifically
failed criterion. Experimental qualification remains governed by Phase P.
