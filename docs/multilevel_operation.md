# Multilevel and neuromorphic operation - Phase Q

## Q0 status and baseline

Q0 is complete: repository audit, initial scientific scope and Q1-Q7 acceptance
sequence are defined here. Q1 declaration contracts are now implemented in
`ncmemsim.multilevel_contracts`; Q2 execution and static result archives are now
implemented in `ncmemsim.multilevel_execution`. Q3 preparation and separation
analysis is implemented in `ncmemsim.multilevel_analysis`. Q4 update metrics and
fixed-spectrum optical sequences are implemented in `ncmemsim.multilevel_updates`
and `ncmemsim.multilevel_optical`. Q5 independent dark retention and supported
FG-fraction ensembles are implemented in `ncmemsim.multilevel_retention` and
`ncmemsim.multilevel_ensemble`. Q6 reports and strict bundles are implemented in
`ncmemsim.multilevel_reporting`. Q7 final candidate identity is `1.8.0`; API/archive and installed
package gates are implemented. Exact-candidate CI and publication remain pending. The Q0 audit is retained as
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
span, saturation and direction reversals. Q4 defines the metrics below for
linearity deviation and paired update asymmetry, including index alignment,
normalizers and coverage. A branch with too few reads or insufficient dynamic
range cannot receive a favourable normalized score. Identical repeated pulses
test gradual updates; any varying amplitudes/durations must remain visible.

Q5 retention probes below start from copies of each prepared level and use fixed read
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
| Q3 (complete) | Multilevel preparation and separation analysis | Common read/margin definitions, retained reversed/collapsed/missing levels and controlled electrical reference with timestep checks |
| Q4 (complete) | Gradual-update analysis and optical sequence integration | Named linearity/asymmetry definitions, valid normalizers, paired dark control, optical budgets, no conductance substitution and controlled update references |
| Q5 (complete) | Retention drift and supported ensemble evaluation | Fixed references, independent delay probes, exact sample/coverage accounting, zero-variation baseline and no noise/yield/endurance inference |
| Q6 (complete) | Applied references, strict reports and reproducibility bundles | Electrical/optical normal and negative cases, source-linked states/metrics and no-replay restoration with tamper rejection |
| Q7 (final candidate) | v1.8 additive API/archive review and release gates | Complete regression, strict docs, clean installed wheel/sdist, supported-Python CI and exact-candidate publication/citation checks |

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
are rejected by the Q1 electrical schema; Q4 provides a separate optical workflow below.
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
Q3 adds level separation, Q4 adds weight/update analysis and Q5 adds independent
retention analysis below. Q6 provides strict reports and bundles below.

Tests compare direct sequential backward-Euler stepping for 1-3 FGs, a retained
single-pulse protocol at the same explicitly selected integrator, continuity
under an extra zero-dwell read, and timestep halving at fixed physical waveform.
The controlled test fixture uses `1e-6` absolute bounds on occupation/read-voltage
changes for the refinement comparison. These are example regression thresholds,
not a convergence proof or measured precision. Numerical comparisons do not
change the default explicit integrator of historical single-pulse calls.

## Q3 independent preparation and separation

`ncmemsim.multilevel_analysis` provides `MultilevelPreparation`,
`MultilevelStudyPlan`, `MultilevelStudyResult`, `run_multilevel_study` and
`analyze_multilevel_results`. Each level executes its own Q2 sequence from an
independent copy of the same original initial state. The context, dark read
policy and optional weight reference must match across all levels. Q3 does not
evaluate normalized weights. Only the final read of a completed preparation is
accepted as its level readout; an earlier read cannot replace a failed final read.
Other preparations continue after a level's recorded execution failure.

The plan declares increasing signed `delta_vfb_V` order before analysis. Results
are never sorted to conceal reversals. For adjacent levels, the signed margin is
`(R_upper - h_upper) - (R_lower + h_lower)`, in volts. Passing requires a strictly
positive margin that also meets the declared nonnegative minimum. Equal levels
therefore fail even when the requested minimum is zero. `deterministic` intervals
require zero half-widths; `assumed_bounds` permits explicitly assumed nonnegative
half-widths. Neither choice supplies measured read noise or statistical confidence.

Archives retain the plan, full source-linked Q2 results, raw level observations,
failures and missing slots. Summaries distinguish completed, failed and missing
preparations, passed/failed/unassessed pairs and pair-assessment coverage. A known
failed pair makes the overall criterion fail even if other pairs are unassessed.
Otherwise incomplete assessment is `not_assessable`. Minimum margin covers only
assessable pairs. Nonrepresentable margin arithmetic remains unassessed rather
than being serialized as infinity. Completion of preparations is reported
separately from assessability or passing the separation criterion.

Strict restoration checks schemas, hashes, result-to-preparation correspondence
and recomputed static summaries without rerunning integration or an RNG. Hashes
check integrity; they do not authenticate experimental evidence.

### Controlled electrical reference

`examples/phase_q3_multilevel_reference.py` uses one default V2 FG, a common empty
initial state and dark zero-dwell reads at 0 V. Three independent +6 V preparations
last 1 microsecond, 0.5 microseconds and 0.1 microseconds, with 1 ns internal steps.
The longest pulse is declared first because electron accumulation gives a more
negative signed readout in this context. The deterministic minimum margin is
explicitly set to 1 mV, with zero interval half-widths.

```bash
python examples/phase_q3_multilevel_reference.py --output q3-result.json
python examples/phase_q3_multilevel_reference.py --input q3-result.json --output q3-restored.json
```

The controlled run gives approximately -10.1681, -5.04555 and -1.00328 mV.
Adjacent signed margins are approximately 5.12256 and 4.04227 mV; both pass the
declared criterion. These are synthetic model results, not experimentally
resolved levels, storage capacity, manufacturing yield or conductance states.
Tests halve the internal timestep at the same physical waveform and compare
readouts with a declared `1e-5 V` absolute regression tolerance. This fixture check
is not a general convergence proof or experimental uncertainty estimate.
Reversed, collapsed, overlapping, missing and failed preparations are tested
explicitly, including restoration without solver execution.

## Q4 gradual updates and fixed-spectrum optical sequences

### Fixed-reference update analysis

`ncmemsim.multilevel_updates` exports `GradualUpdateAnalysis`,
`PairedUpdateAnalysis`, `analyze_gradual_updates` and `analyze_paired_updates`.
Analysis accepts a Q2 electrical result or a Q4 optical result, the exact fixed
Q1 `WeightReferenceMapping`, an expected signed-readout direction (`increasing`
or `decreasing`) and a strictly positive `minimum_excursion_V`. Context and dark
read policy must match the reference; an experiment's declared reference cannot
be replaced by another one during analysis. Reference endpoints are supplied
with evidence and applicability, not inferred from the observed trajectory.

All accepted reads remain in physical order. Weights use
`w_k = (R_k - R_low)/(R_high - R_low)` without clipping, per-branch min/max
rescaling or sign changes. Out-of-reference read indices are explicit. Raw
signed updates are `R_(k+1)-R_k`, in V; signed weight updates use the same fixed
reference span. Read times are absolute physical times in seconds. Requested,
completed and observed pulse counts distinguish non-idle pulses from idle
segments; update coverage counts all declared segment boundaries, including
idle segments. Varying waveforms and illumination schedules remain visible,
with an explicit `all_steps_identical` flag.

For N segment updates, **endpoint-interpolated pulse-index linearity deviation** is
`max_k abs((R_k-R_0)/(R_N-R_0) - k/N)`, for k=0 through N. It is dimensionless,
normalized by the branch endpoint excursion, not the fixed reference span.
The complete branch needs at least two updates, a net excursion in the declared
direction, absolute excursion at least `minimum_excursion_V` and representable
normalization. Otherwise the score is null with a reason. Raw observations and
partial coverage are retained. Opposite-to-declared-direction updates are counted
as `direction_reversal_count`; this is not a count of sign changes between two
successive updates. Exact-zero updates are counted separately and do not by
themselves prove physical saturation. A nonmonotonic branch can retain a defined
linearity deviation and its visible opposite-direction count.

**Paired pulse-index magnitude asymmetry** is
`sum_k abs(abs(delta_w_first_k)-abs(delta_w_second_k)) /
 sum_k (abs(delta_w_first_k)+abs(delta_w_second_k))`.
Branches require the same fixed reference, physical context/read policy, opposite
declared directions and matching segment counts, durations and timesteps. Two
optical branches additionally share the exact spectral path/source, capture,
transition weights and assumed illuminated area. Alignment is by the same
segment index, with no reversed indexing or inferred state matching. Independent
branches may have different initial states and voltages; full requests retain
those differences. This is not a state-matched hysteresis metric or a fit.
Both branches must be assessable and contain no opposite-direction updates.
Undefined/misaligned branches retain coverage and a null score, never a favourable
zero. For defined scores, zero means equal paired update magnitudes, and values
approaching one indicate increasing magnitude mismatch under this definition.

### Explicit optical execution and dark controls

`ncmemsim.multilevel_optical` exports `OpticalSequenceExperiment`,
`OpticalSequenceResult`, `MatchedOpticalSequenceResult`, `run_optical_sequence`
and `run_matched_optical_sequence`. An optical request combines an owned Q1
electrical waveform/initial state/read policy with an exactly matching resolved
`SpectralSimulationContext`. It adds ordered non-idle illuminated step identities,
capture efficiency, immutable weights in `(r01,r12,r10,r21)` order and a positive
uniform illuminated area in m2. This first adapter uses **one fixed spectrum**;
source switching, finite-dwell reads and changing material contexts are outside
its scope. Q1/Q2 electrical schemas and their dark execution are unchanged.

The spectral source's irradiance is defined at the entrance of the modelled
stack, using its declared traversal direction. All passive-layer assumptions and
FG absorption profiles remain in the context. Existing N4 capture/outgoing-event
constraints are enforced. Selected physical steps alone receive this source;
idle, unselected steps and every zero-dwell read are explicitly dark. Each step
uses backward Euler and continues the original physical state, not a returned
read state. Source, initial-state, clock, read and failure-prefix checks retain
the Q2 audit semantics through the new, separately named optical result schema.

The matched runner creates independent light and dark copies of the exact same
electrical request. The dark branch still runs if the light branch records a
failure. Contrasts are light minus dark signed readout at the same read index
and physical time. Matched read counts/fractions expose missing comparisons.
Disabled sources and zero capture are separate controls: zero capture can still
have delivered and absorbed optical energy.

Budgets retain irradiance in W/m2, optical power in W for the assumed uniform
area, exposure in seconds, fluence in J/m2, energy in J and absorbed photon
fluence per FG in m-2. Incident, total absorbed, FG absorbed, passive absorbed
and transmitted components are distinguished. These budgets cover only completed
physical steps, including a step whose subsequent read fails. A failed physical
step contributes no claimed completed exposure. Scheduled exposure can be nonzero
with a disabled source, while its power/fluence are zero. This is delivered/
absorbed optical accounting, not total electrical-plus-optical programming energy
or an inferred energy per update from FG charge.

Strict archives retain requests, original states and read observations, failures,
metric definitions and derived counts/budgets. Restoration recomputes static
state/read projections and inherited spectral consistency checks from stored
profiles. It does not rerun occupancy integration, resample material absorption,
fit parameters or draw random samples. Integrity hashes do not authenticate
measurements or prove a trajectory was physically executed. Q6 provides strict report/bundle exports below.

### Controlled reference and negative outcome

`examples/phase_q4_gradual_update_reference.py` uses one V2 Ge FG, assumed
transparent passive layers, four 100 ns constant-voltage segments with 1 ns
internal steps and dark zero-dwell reads at 0 V. The fixed reference interval
is explicitly assumed to be [-0.1,0] V, with a 1 microvolt minimum branch
excursion. It is not a measured or newly calibrated reference.

```bash
python examples/phase_q4_gradual_update_reference.py --output q4-reference.json
python examples/phase_q4_gradual_update_reference.py --input q4-reference.json --output q4-restored.json
```

The +6 V branch starts empty and gives about -0.259216 mV net signed update,
with linearity deviation about `5.79e-5` under the definition above. The -6 V
branch starts at assumed P0=0.8, P1=0.2 and gives a small negative excursion,
contrary to its declared increasing-readout direction. That negative outcome is
retained: its linearity and the paired asymmetry are **not assessable**. Pulse
role or polarity is not silently reinterpreted as successful potentiation/erase.

The illuminated +6 V branch uses a synthetic 1550 nm line at 1e6 W/m2, capture
0.1, loading weights `(1,1,0,0)` and assumed uniform area 1e-8 m2. Four exposures
give 400 ns scheduled exposure, 0.01 W incident optical power and 4 nJ incident
optical energy. The net signed update is about -1.735945 mV, with final matched
light-minus-dark contrast about -1.476728 mV. It is not valid to attribute all
combined electrical/optical charge to photons. These conditional model outputs
are neither measured synaptic conductance nor experimental qualification.

Tests cover explicit 1-3 FG state continuation against direct spectral stepping
and the retained single-pulse workflow, paired dark/disabled/zero-capture controls,
light scheduling, optical balances, injected failures and strict archive tamper
rejection. Analytic curve tests separately verify linear, nonlinear, collapsed,
reversed and unequal-magnitude definitions. Halving the optical reference timestep
at the same physical waveform uses an absolute `1e-5 V` readout regression bound;
this is a fixture tolerance, not measured noise or a general convergence proof.

## Q5 independent dark retention and supported ensembles

### Retention plan and original-state ownership

`ncmemsim.multilevel_retention` exports `MultilevelRetentionPlan`,
`MultilevelRetentionResult`, `run_multilevel_retention` and
`analyze_multilevel_retention`. This first adapter accepts source-linked Q3
electrical prepared-level results, a strictly increasing immutable delay tuple
starting at zero, a fixed dark retention voltage, explicit backward-Euler
timestep, evidence and an optional fixed Q1 `WeightReferenceMapping`. Optical
preparations, finite-dwell reads and changing material contexts are outside this
adapter; Q4 optical workflows retain their separate meaning.

Every positive delay starts from a fresh copy of **that level's original prepared
physical state**. A 200 ns probe does not start from the end of the 100 ns probe.
The delay origin is the end of each level's own preparation, not a common absolute
device age; different preparation durations remain in the source. Zero delay
reuses the already audited original preparation read and performs no integration.
Each positive-delay probe is an explicit Q2 dark constant-bias hold and a dark
zero-dwell endpoint read, retaining the original physical and read states.

The read policy, level order, minimum margin and interval half-widths remain those
of the original Q3 study. Signed drift is `R_level(delay)-R_level(0)`, in V.
If requested, weights use the same fixed reference span at all delays, without
clipping or new min/max normalization. Reference context/read identity must match;
an existing preparation reference cannot be replaced. A null normalized value
means unavailable or nonrepresentable normalization, not zero drift or a stable
state. The normalization status and raw readout remain explicit.

At each requested delay, adjacent margins use the original Q3 formula and order.
`crossed_pair_count` counts negative adjacent **raw readout gaps at that sampled
delay**. Interval overlap, equal readouts and an insufficient positive margin can
fail separation without such a crossing. No event time is interpolated between
probes. A known failed pair remains failed even if another pair is unassessed.
Minimum reported margins cover only assessable pairs.

### Missing and failed evidence

A failed or missing preparation has no invented retention endpoint. Its requested
observations remain unavailable, with preparation failure evidence retained.
Every eligible probe has its own result slot; explicit missing slots are supported
by the static analyzer. A failed probe keeps its Q2 prefix and actual elapsed
physical time but supplies no accepted readout at the requested endpoint. Later
independent delays and levels continue. In particular, a completed physical hold
with a failed subsequent read is still an unobserved endpoint.

Counts distinguish all requested observations (including zero-delay reads),
completed observations, unavailable preparations, all requested positive probes,
eligible probes, attempted/completed/failed probes and missing probe slots.
Observation coverage uses all declared level-delay combinations as denominator.
These are sampled-time coverage diagnostics, not a retention lifetime or a claim
that separation holds throughout every interval between probes.

### Manifest-bound between-device variation

`ncmemsim.multilevel_ensemble` exports `MultilevelEnsemblePlan`,
`MultilevelEnsembleResult` and `run_multilevel_ensemble`. The runner consumes an
already generated Phase K `SampleManifest`, retaining its seed/sampling contract,
original values, sample IDs, order and provenance. It uses existing sample-domain
validation and device-binding application; it never draws new samples during
execution or restoration.

The first supported bindings are existing DEVICE paths
`('layers', FG_name, 'electrically_active_fraction')` and
`('layers', FG_name, 'nc_volume_fraction')`. These preserve the probability grid.
Each realization starts from its own owned device/context and the same declared
initial probability coordinates; it independently prepares the complete Q3 level
study and performs the declared retention probes. Thermal laws/settings are retained
from the nominal context. An exact zero-variation realization preserves the original
context identity, states, readouts and margins.

Pulse voltages/durations/timesteps, dark read policy, level order, interval widths,
minimum separation and retention schedule are fixed across samples. Geometry/grid,
OPERATING and MODEL bindings and optical-source variation are rejected by this
adapter. It also rejects nominal-context weight-reference declarations rather
than silently rebinding them to changed device contexts. Ensemble comparisons
therefore use physical readout/drift/margin in V; fixed-reference normalization
is available in the nominal retention adapter above. This is an explicit scope
boundary, not an automatic per-sample calibration.

Requested samples always mean the **entire manifest**. Results distinguish
attempted, completed, partial, failed and missing samples. A workflow with missing
or failed endpoints is partial; a constructed study with fully observed but
collapsed/reversed levels is a completed execution with a failed separation
criterion. Domain/binding/construction and unexpected workflow failures remain
source-linked isolated failures; later samples continue.

For each delay, summaries retain all sample identities, fully assessed sample
counts (every adjacent pair assessable), passed counts, known failed counts and
not-fully-assessed counts. A known failed partial sample can also be not fully
assessed; these two counters are deliberately not mutually exclusive. Fractions
state their denominator: all requested samples or fully assessed samples. With
no fully assessed sample the latter fraction is null. Passing fractions are
conditional results under the declared distribution, **not manufacturing yield**.
Repeated deterministic histories at identical parameters do not model cycle noise,
read noise, endurance or irreversible degradation.

### Archives and controlled reference

Both adapters retain complete source requests/results and strict summaries.
Restoration validates source hashes, delay/level/sample order, original prepared
state linkage, supported realization bindings and recomputed static projections.
Static device binding/context resolution may run; occupancy integration and RNG
sampling do not. Hashes establish consistency, not experimental authenticity or
proof of replayed trajectories. Q6 provides strict report/bundle exports below.

```bash
python examples/phase_q5_retention_ensemble_reference.py --output q5-reference.json
python examples/phase_q5_retention_ensemble_reference.py --input q5-reference.json --output q5-restored.json
```

The reference uses the Q3 three-level electrical preparation with 10 ns internal
steps, dark 0 V holds at independent delays 0, 100 and 200 ns, and 10 ns retention
steps. The nominal-only proxy interval [-20,0] mV is explicitly assumed and fixed.
Two zero-variation realizations use the nominal FG1 electrically active fraction.
Two further realizations use an assumed uniform distribution from 80% to 100% of
that nominal fraction, with explicit seed 1805. These short synthetic probes test
software semantics; they do not demonstrate a device retention specification.

Tests verify direct dark-step equivalence, independent delay origins, zero-delay
identity, fixed normalization, missing/failed endpoints, order inversions, interval
overlap and strict tamper rejection. Ensemble tests retain zero-variation identity,
manifest order, varied realized contexts, invalid samples, partial workflows and
exact denominators. Static restoration is checked with integration and RNG disabled.

## Q6 applied reports and reproducibility bundles

`ncmemsim.multilevel_reporting` adds typed, ordered reports over the eight Q2-Q5
result families. It retains source-specific definitions, contexts and denominators;
it does not pool different studies into a capacity, yield or performance score.
See [Multilevel reports and bundles](multilevel_reporting.md) for schemas,
file meanings, source pointers, static restoration and executable usage.

The applied reference combines electrical loading, declared-order separation,
deliberately reversed levels, gradual updates, a wrong-direction branch and its
undefined paired metric, fixed-spectrum optical loading with matched dark control,
independent nominal retention, zero-variation and assumed-fraction ensembles.
All eleven cases retain their original full source records and hashes. Negative,
partial and undefined results are not removed to improve the report.

```bash
python examples/phase_q6_multilevel_report.py --destination q6-report
python examples/phase_q6_multilevel_report.py --input-bundle q6-report --destination q6-restored
```

Reporting and loading use existing static result readers; they do not rerun
occupancy integration or generate new samples. Source generation in the first
command does execute the declared Q4/Q5 reference workflows. Optional stored
reference inputs are described in the reporting guide. Bundle tests compare
re-exported bytes and reject altered source evidence, CSV/Markdown projections,
manifest hashes and unexpected directory members. Q7 preparation gates and remaining release steps are recorded in
[v1.8 release checklist](v1_8_release_checklist.md).

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
