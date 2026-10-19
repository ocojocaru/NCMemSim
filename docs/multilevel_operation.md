# Multilevel and neuromorphic operation - Phase Q

## Q0 status and baseline

Q0 is complete: repository audit, initial scientific scope and Q1-Q7 acceptance
sequence are defined here. Q0 introduces no runtime implementation, public API,
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
| Q1 | Immutable step/sequence, readout and reference-mapping contracts | Explicit units, ownership, ordering, applicability, hashes, strict round trips and rejection of ambiguous definitions; no execution by declaration |
| Q2 | Isolated state-continuing electrical sequence execution | Reproduce single-pulse baseline, correct state/time chain, no input mutation, explicit read semantics and partial-failure retention |
| Q3 | Multilevel preparation and separation analysis | Common read/margin definitions, retained reversed/collapsed/missing levels and controlled electrical reference with timestep checks |
| Q4 | Gradual-update analysis and optical sequence integration | Named linearity/asymmetry definitions, valid normalizers, paired dark control, optical budgets, no conductance substitution and controlled update references |
| Q5 | Retention drift and supported ensemble evaluation | Fixed references, independent delay probes, exact sample/coverage accounting, zero-variation baseline and no noise/yield/endurance inference |
| Q6 | Applied references, strict reports and reproducibility bundles | Electrical/optical normal and negative cases, source-linked states/metrics and no-replay restoration with tamper rejection |
| Q7 | v1.8 additive API/archive review and release gates | Complete regression, strict docs, clean installed wheel/sdist, supported-Python CI and exact-candidate publication/citation checks |

Acceptance is not a promise of a particular number of stable levels or a
favourable update curve. A reproducible negative result remains a valid study
outcome. Implementation must review each new API/result schema at its own stage.

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
