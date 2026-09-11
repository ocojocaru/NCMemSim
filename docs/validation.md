# Validation and reproducibility

## Validation philosophy

NCMemSim separates three ideas that are often conflated:

- **verification:** the code solves the implemented equations consistently;
- **validation:** model outputs are compared with trusted physical or experimental references;
- **regression control:** future code changes preserve an approved numerical baseline unless a documented change is intended.

The v0.10.0 repository has strong verification and regression infrastructure.

Experimental validation remains device- and dataset-dependent and must be demonstrated in the associated scientific study.

## v0.10.0 release validation

The v0.10.0 release extends the validated electrical model with
wavelength-dependent optical absorption and photo-assisted programming.

The automated suite contains **194 tests**, covering Phases A through E6, including:

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

The complete local suite passes on Python 3.13.12.

The official v0.10.0 release has been verified on the supported Python
3.11, 3.12, and 3.13 CI matrix.

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

The current v0.10.0 local validation target is:

```text
194 passed
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
