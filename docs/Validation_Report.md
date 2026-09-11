# NCMemSim v0.10.0 Verification and Validation Report

## Scope

Version 0.10.0 extends the verified Phase A-D6 electrical framework with the
Phase E optical-programming model.

The verification scope includes:

- numerical regression against the retained V5.3 electrical reference;
- physics-consistency checks;
- benchmark instrumentation;
- reproducibility manifests;
- optical source handling;
- Ge/GeSn wavelength-dependent optical response;
- floating-gate photon absorption;
- photo-assisted charge-state kinetics;
- electro-optical programming;
- SWIR wavelength and voltage-reduction benchmarks.

This report establishes software verification and internal model consistency.
It does not constitute experimental validation of a specific fabricated memory
device.

## Automated regression status

The complete v0.10.0 local test suite contains **194 tests** covering Phases A
through E6.

The release validation suite passes locally with:

```text
Python 3.13.12
pytest 9.1.1
194 passed
```

The v0.10.0 release was also verified by continuous integration on the
supported Python 3.11, 3.12, and 3.13 matrix.

## Verified invariants

The regression and validation suite checks that:

- floating-gate probabilities are finite, bounded, and normalized;
- dielectric thicknesses and relative permittivities are physically admissible;
- nanocrystal barriers and effective masses are positive;
- one-dimensional potential profiles are finite and use a strictly increasing
  grid;
- internal floating-gate redistribution is charge conservative within
  numerical tolerance;
- deterministic one-, two-, and three-FG reference cases match approved golden
  data;
- optical absorption coefficients and photon rates are non-negative;
- electrical and photo-assisted transition rates combine consistently;
- dark simulations preserve zero photo-transition contribution;
- electro-optical programming preserves probability normalization;
- wavelength-dependent SWIR behaviour is spectrally consistent with the
  implemented compact model.

## Electrical regression baseline

The Phase B regression suite compares the modular NCMemSim implementation with
the retained V5.3 reference implementation for:

- electrostatics;
- WKB tunnelling;
- occupancy kinetics;
- single-voltage relaxation;
- compact C-V sweeps.

### V5.3 reference timestep correction

During v0.9.1 release validation, a timestep inconsistency was identified in
the retained V5.3 reference implementation.

When the requested dwell time was shorter than the legacy internal timestep,
the implementation forced a single integration step but advanced the state
using the larger internal timestep.

For example, with a requested dwell time of `2e-5 s` and a legacy internal
timestep of `2e-4 s`, the retained reference advanced the state by `2e-4 s`.
In the low-occupation regime this produced an approximately tenfold difference
in floating-gate charge relative to evolution over the requested dwell
interval.

The retained reference was corrected to use:

```text
actual_dt = dwell_time / nsteps
```

This guarantees that the total integrated interval equals the requested dwell
time.

The modular NCMemSim timestep implementation already used this behaviour and
did not require the corresponding correction.

### V5.3 parameter alignment

Regression validation also requires explicit use of the retained V5.3
parameter set.

The regression configuration aligns:

- attempt frequency;
- bias-activation coefficient;
- field coupling;
- tunnelling barriers.

After parameter alignment and the retained-reference timestep correction, the
Phase B regression path remains green in v0.10.0.

## Phase E optical verification

### E1 - Optical sources

Verification covers:

- monochromatic LED and laser source validation;
- photon energy;
- photon flux;
- enabled and disabled source semantics.

### E2 - Ge/GeSn optical material response

Verification covers:

- direct Gamma-gap composition dependence;
- indirect L-gap composition dependence;
- temperature-dependent phonon occupation;
- direct absorption;
- indirect phonon-assisted absorption;
- Urbach-tail absorption.

The direct-gap parameterization is literature based. The indirect compact model
is literature informed.

Absolute absorption prefactors remain provisional compact-model parameters.

### E3 - Floating-gate optical absorption

Verification covers:

- Beer-Lambert absorption;
- effective absorption using nanocrystal volume fraction;
- absorbed photon flux;
- transmitted photon flux;
- volumetric generation rate;
- floating-gate optical diagnostics.

The present model assumes the HfO2 matrix is optically transparent and does not
include explicit scattering or effective-medium electrodynamics.

### E4 - Photo-assisted kinetics

Verification covers:

- nanocrystal number density;
- absorbed photon rate per nanocrystal;
- photo-transition arrays;
- photo-assisted loading;
- electrical plus optical rate coupling;
- electro-optical programming.

The default compact photo-loading model supports:

- 0 -> 1;
- 1 -> 2.

Photo-assisted detrapping is disabled by default.

Photo-capture efficiency remains a provisional model parameter unless
experimentally calibrated.

### E5 - Simulator integration

Optical programming is integrated into:

- `Simulator.relax_voltage()`;
- voltage sweeps;
- compact C-V simulation.

Diagnostics include per-floating-gate and scalar values for:

- optical absorption fraction;
- absorbed photon flux;
- absorbed photon rate per nanocrystal;
- photo-transition rate;
- nanocrystal absorption coefficient;
- effective floating-gate absorption coefficient.

For a fixed source and material in v0.10.0, the optical absorption properties
are voltage independent.

## Phase E6 SWIR validation

### Wavelength sweep

The SWIR validation checks wavelength-dependent behaviour over Ge and GeSn
compositions.

For the compact direct-gap model, approximate direct-gap cutoff wavelengths
are:

| Material | Approximate direct-gap cutoff |
|---|---:|
| Ge | 1553 nm |
| GeSn 4% | 1940 nm |
| GeSn 8% | 2536 nm |
| GeSn 12% | 3564 nm |

These values describe the implemented compact model and are not independent
experimental measurements.

The 12% Sn case extends beyond the 0-10% Sn composition range of the principal
room-temperature absorption dataset used for model guidance and should be
treated as extrapolative.

### SWIR programming benchmark

The programming benchmark verifies that:

- dark simulations have zero photo-assisted contribution;
- SWIR illumination produces measurable photo-assisted loading;
- electro-optical programming exceeds electrical-only programming under the
  benchmark conditions;
- spectral photo-rate ordering is reflected in occupation changes;
- probability normalization is preserved.

### Quantitative voltage-reduction benchmark

The v0.10.0 benchmark uses:

- GeSn composition: 8% Sn;
- nanocrystal diameter: 5 nm;
- floating-gate thickness: 15 nm;
- optical power density: 1000 W/m^2;
- programming interval: 1 ms;
- voltage range: 0 to 4 V;
- voltage step: 0.25 V;
- benchmark photo-capture efficiency: `1e-10`.

A single common target occupation is used for the dark and all illuminated
curves.

| Wavelength | Photo rate (s^-1) | Vdark (V) | Vlight (V) | Delta V (V) |
|---:|---:|---:|---:|---:|
| 1300 nm | 3.092040e-07 | 3.9124 | 3.8343 | 0.078071 |
| 1550 nm | 3.506618e-07 | 3.9124 | 3.8238 | 0.088539 |
| 1700 nm | 3.684289e-07 | 3.9124 | 3.8193 | 0.093025 |

The spectral ranking is:

```text
1700 nm > 1550 nm > 1300 nm
```

for both photo-transition rate and voltage reduction in this benchmark.

The value `photo_capture_efficiency = 1e-10` is a benchmark-only coupling
parameter selected to place dark and illuminated curves in a common occupation
range.

It is **not experimentally calibrated**.

Therefore the reported voltage reductions demonstrate compact-model behaviour,
spectral consistency, and software verification rather than absolute
experimental predictive accuracy.

## Golden cases

The release preserves deterministic outputs for V2 devices with:

- one floating gate;
- two floating gates;
- three floating gates;
- a short three-FG retention trajectory.

Tests compare recorded values using explicit relative and absolute tolerances.

Golden data should only change after a reviewed physical or numerical model
change.

## Reproducibility

Reproducibility manifests record information including:

- software version;
- timestamp;
- Python and NumPy versions;
- runtime platform;
- optional Git commit;
- complete device description;
- material models;
- canonical device hash;
- simulation configuration;
- simulation hash.

A hash establishes identity of serialized model inputs; it does not establish
physical correctness.

## Known model limitations

The v0.10.0 optical model does not yet include:

- voltage-dependent optical absorption;
- Franz-Keldysh absorption;
- Stark shifts;
- state filling;
- explicit strain-dependent absorption;
- nanocrystal quantum-confinement corrections;
- sequential optical attenuation through multiple floating gates;
- experimentally calibrated absolute absorption amplitudes;
- experimentally calibrated photo-capture efficiencies.

The compact model is intended for mechanism studies, controlled comparison,
and DTCO workflows.

## Release conclusion

NCMemSim v0.10.0 satisfies the release verification target:

```text
194 passed
```

The documentation builds successfully with strict MkDocs checking, and the
supported Python 3.11, 3.12, and 3.13 continuous-integration matrix passes.

The official `v0.10.0` tag corresponds to the released Phase E
optical-programming implementation. The release workflow completed
successfully and produced both wheel and source-distribution artifacts.

The published documentation includes the v0.10.0 optical-programming model,
API, assumptions, limitations, validation results, and SWIR benchmark
documentation.

Accordingly, v0.10.0 is the verified release baseline for subsequent NCMemSim
development.

The verification reported here establishes software correctness relative to
the implemented equations, regression baselines, and internal physical
consistency checks. It does not imply experimental calibration of the absolute
optical response or programming-voltage reduction.
