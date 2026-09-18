# Validation and reproducibility

## Validation philosophy

NCMemSim separates three ideas that are often conflated:

- **verification:** the code solves the implemented equations consistently;
- **validation:** model outputs are compared with trusted physical or experimental references;
- **regression control:** future code changes preserve an approved numerical baseline unless a documented change is intended.

The v0.10.0 repository has strong verification and regression infrastructure.

Experimental validation remains device- and dataset-dependent and must be demonstrated in the associated scientific study.

## v0.13.0 Robust DTCO validation

The candidate `b5d8374e1a386e00a442b37839784134ae6e6209` passed
**1808 local tests**, including **717 Phase G/H DTCO cases**. Strict MkDocs
and rendered-link auditing covered 27 pages and 4747 local references without
errors; 111 Python snippets and 301 public imports were checked, with current
G/H examples executed. Clean wheel/sdist installations exercise both nominal
and Robust DTCO references, deliberate failures, repeatable hashes, restoration
and exports. Source-release verification compares 67 audited source files.

All six supported-Python candidate test/distribution jobs passed on Python
3.11, 3.12 and 3.13 in [CI](https://github.com/ocojocaru/NCMemSim/actions/runs/35317323748).
The [Documentation audit](https://github.com/ocojocaru/NCMemSim/actions/runs/35317328574)
passed; deployment was skipped on the dev branch. These remote results belong
to the stated candidate commit. Final version/citation/documentation preparation
is checked locally again before publication; preparation itself creates no tag.

## v0.12.0 DTCO release validation

The complete verification suite contains **1598 tests**, including **507**
Phase G cases. G7 commit `cdbb785be24a99170e2fa08c6682fb1e342edf6d` passed
full tests and clean installed wheel/source workflows on Python 3.11, 3.12
and 3.13, plus strict documentation in CI. Stable-version commit
`cc8999b1373f7c3282c2352562635ed9a48ad50a` also passed branch/main CI,
the `v0.12.0` tag release workflow and documentation deployment. The release
contains the wheel and source distribution. See the
[v0.12.0 release](https://github.com/ocojocaru/NCMemSim/releases/tag/v0.12.0).

DTCO verification covers canonical bindings/units, copy-on-write candidates,
Cartesian ordering and failure isolation, finite metric extraction, inclusive
constraints, mixed-direction Pareto sorting, adjacent-grid sensitivity,
manifest integrity, report exports and the real reference workflow.

This is software verification and regression evidence, not a claim of
independent device-specific physical calibration. Tag/version matching and
installed distribution checks gate the existing GitHub release workflow.

## v0.11.0 release validation

The v0.11.0 release preserves the validated electrical and optical model while adding experimental-data, fitting, uncertainty, identifiability, and calibration-qualification workflows.

The automated suite contains **1091 tests**, covering the retained Phases A through E6 baseline and the v0.11.0 Phase F workflows, including:

- foundation and device construction;
- V5.3 electrical regression;
- materials;
- multi-state floating gates;
- electrostatic coupling;
- local electric fields;
- transport;
- retention;
- validation utilities;
- optical sources;
- Ge/GeSn optical response;
- Beer-Lambert absorption;
- photo-assisted transition kinetics;
- electrical + optical rate coupling;
- simulator optical integration;
- optical voltage sweeps;
- optical C-V support;
- SWIR wavelength sweeps;
- SWIR programming benchmarks;
- SWIR voltage-reduction benchmarks.

The complete v0.11.0 release suite passes locally on Python 3.13.

The repository CI matrix passes on Python 3.11, 3.12, and 3.13 for the v0.11.0 release.

## Electrical regression

The Phase B regression suite explicitly compares the modular implementation against the retained V5.3 reference for:

- electrostatics;
- WKB tunnelling;
- occupancy kinetics;
- single-voltage relaxation;
- compact C-V sweeps.

During the v0.9.1 validation cycle, a timestep inconsistency was identified in the retained V5.3 reference implementation.

When the requested dwell time was shorter than the legacy internal timestep, the legacy code forced one integration step but advanced the state using the larger internal timestep.

The retained reference was corrected to use:

`actual_dt = dwell_time / nsteps`

so that the integrated interval exactly matches the requested dwell time.

This remains documented as a legacy-reference bug fix rather than a change to the validated modular NCMemSim timestep implementation.

## Optical validation

Phase E validates the optical-programming implementation in six stages.

### E1 - Optical sources

Checks include:

- monochromatic source validation;
- photon energy;
- photon flux;
- enabled and disabled source behaviour.

### E2 - Optical material response

Checks include:

- direct Ge/GeSn optical gap;
- indirect optical gap;
- temperature-dependent phonon occupation;
- direct absorption;
- indirect phonon-assisted absorption;
- Urbach-tail absorption;
- spectral behaviour across Ge and GeSn compositions.

### E3 - Optical absorption

Checks include:

- Beer-Lambert absorption;
- effective nanocrystal absorption;
- absorbed and transmitted photon flux;
- floating-gate optical evaluation;
- average optical generation rate.

### E4 - Photo-assisted kinetics

Checks include:

- absorbed photon rate per nanocrystal;
- photo-transition rate arrays;
- photo-assisted charge loading;
- electrical + optical rate addition;
- electro-optical programming;
- voltage-reduction behaviour.

### E5 - Simulator integration

Checks include:

- `Simulator.relax_voltage()` optical programming;
- optical diagnostics;
- voltage-sweep integration;
- C-V integration;
- dark-source and disabled-source semantics;
- multi-floating-gate diagnostics.

### E6 - SWIR benchmarks

Phase E6 checks:

- wavelength-dependent SWIR absorption;
- Ge versus GeSn spectral response;
- positive and finite photo-assisted programming;
- probability normalization;
- spectral ordering of photo-transition rates;
- voltage reduction under illumination.

The current quantitative voltage-reduction benchmark uses:

- GeSn composition: 8% Sn;
- nanocrystal diameter: 5 nm;
- floating-gate thickness: 15 nm;
- optical power density: 1000 W/m^2;
- programming interval: 1 ms;
- benchmark photo-capture efficiency: 1e-10.

For a common target occupation:

| Wavelength | Vdark | Vlight | Delta V |
|---:|---:|---:|---:|
| 1300 nm | 3.9124 V | 3.8343 V | 0.078071 V |
| 1550 nm | 3.9124 V | 3.8238 V | 0.088539 V |
| 1700 nm | 3.9124 V | 3.8193 V | 0.093025 V |

The spectral ordering is:

```text
1700 nm > 1550 nm > 1300 nm
```

for both the photo-transition rate and the voltage reduction in this benchmark.

The `photo_capture_efficiency = 1e-10` value used for this benchmark is a comparison parameter selected to place dark and illuminated programming curves in a common occupation range.

It is **not** an experimentally calibrated material parameter.

Accordingly, the reported voltage-reduction values demonstrate internal model behaviour and consistency rather than absolute experimental prediction.

## Test suite

Run all tests with:

```bash
python -m pytest
```

The current v0.13.0 local verification target is:

```text
1808 passed
```

## Physics checks

`validate_simulation` combines checks including:

- probability normalization and bounds;
- consistency between a `DeviceState` and the device geometry;
- validity of the field profile;
- internal charge conservation for redistribution;
- structural consistency of simulation outputs.

Example:

```python
from ncmemsim import validate_simulation

report = validate_simulation(device, output["state"], output)
report.raise_for_errors()
```

A `ValidationReport` distinguishes issues and can be used in automated workflows.

## Golden references

The golden suite contains deterministic cases for:

- a V2 one-FG device;
- a V2 two-FG device;
- a V2 three-FG device;
- a short retention trajectory.

Generate the suite with:

```bash
python scripts/generate_golden.py
```

Golden data should only change after a reviewed physical or numerical modification.

The reason and expected output difference must be recorded in the changelog or validation report.

## Benchmarks

The benchmark tools report runtime, traced peak memory, and selected physical outputs such as total FG charge.

```bash
python scripts/run_benchmarks.py
```

Performance numbers depend on Python, NumPy, operating system, and hardware.

They are primarily intended for regression tracking, not cross-platform absolute ranking.

## Reproducibility manifest

`build_reproducibility_manifest` records information such as:

- NCMemSim version;
- git commit when available;
- Python, NumPy, runtime, and platform;
- device hash;
- simulation hash;
- random seed;
- material models;
- caller-supplied metadata.

Save the manifest next to every published dataset or figure.

A hash establishes identity of serialized inputs; it does not prove that the physical model is correct.

## Existing validation documents

The repository also includes:

- `docs/Validation_Report.md`
- `validation/README.md`
- `validation/benchmark_results.json`
- phase-specific test-result records

These preserve the validated electrical baseline and the Phase E optical extension used by v0.10.0.
