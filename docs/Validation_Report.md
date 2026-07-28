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
