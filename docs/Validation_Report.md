# NCMemSim v0.9.0 Verification and Validation Report

## Scope

Phase D6 establishes automated numerical regression, physics-consistency checks, benchmark instrumentation, and reproducibility manifests for the Phase A-D5 physics stack.

## Verified invariants

- Floating-gate probabilities are finite, bounded, and normalized.
- Dielectric thicknesses and relative permittivities are physically admissible.
- Nanocrystal barriers and effective masses are positive.
- One-dimensional potential profiles are finite and use a strictly increasing grid.
- Internal floating-gate redistribution is charge conservative within numerical tolerance.
- Deterministic one-, two-, and three-FG reference cases match versioned golden data.

## Golden cases

The release includes compact deterministic outputs for V2 devices with one, two, and three floating gates plus a short three-FG retention trajectory. Tests compare all recorded values using explicit relative and absolute tolerances.

## Reproducibility

Every manifest records the software version, timestamp, Python and NumPy versions, platform, optional Git commit, complete device description, material models, canonical device hash, simulation configuration, and simulation hash.

## Limitations

The golden suite verifies software stability; it is not a substitute for experimental validation. Experimental reference datasets are intentionally not bundled. Performance thresholds are not enforced in CI because shared runners have variable load; benchmark values are recorded for trend analysis.

## v0.9.1 release-validation addendum

Version 0.9.1 preserves the Phase D6 v0.9.0 golden-reference baseline and
extends verification to the final repository and release configuration.

### Automated regression status

The complete v0.9.1 automated test suite contains **63 tests** covering
Phases A through D6. The suite passes locally on Python 3.13 and in GitHub
Actions on Python 3.11, 3.12, and 3.13.

The Phase B regression suite additionally compares the modular NCMemSim
implementation with the retained V5.3 reference implementation, including
electrostatics, WKB tunnelling, occupancy kinetics, single-voltage relaxation,
and compact C–V sweeps.

### V5.3 reference correction

Release validation identified a timestep inconsistency in the retained V5.3
reference implementation. When the requested dwell time was shorter than the
legacy internal timestep, the implementation forced a single integration step
but advanced the state using the larger internal timestep.

For example, with a requested dwell time of `2e-5 s` and a legacy internal
timestep of `2e-4 s`, the reference implementation advanced the state by
`2e-4 s`. In the low-occupation regime this produced an approximately tenfold
difference in floating-gate charge relative to evolution over the requested
dwell interval.

The retained reference implementation was corrected to compute the number of
steps and then use

`actual_dt = dwell_time / nsteps`

for probability evolution. This guarantees that the total integrated interval
equals the requested dwell time.

The modular NCMemSim timestep implementation already used this behavior and
did not require the corresponding correction.

### V5.3 parameter alignment

Regression validation also requires the V5.3 reference parameter set to be
specified explicitly. The regression configuration uses the legacy attempt
frequency, bias-activation coefficient, field coupling, and tunnelling-barrier
values rather than relying on the independent defaults of the modular model.

After reference-parameter alignment and correction of the legacy timestep
behavior, all Phase B regression tests pass.

### Release packaging

The v0.9.1 source distribution and platform-independent wheel build
successfully. The wheel was also installed and imported from an isolated
virtual environment, where `ncmemsim.__version__` reported `0.9.1`.

These checks establish software verification, regression consistency, and
release reproducibility. They do not constitute experimental validation of a
specific fabricated memory device.