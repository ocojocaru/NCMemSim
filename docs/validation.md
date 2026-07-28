# Validation and reproducibility

## Validation philosophy

NCMemSim separates three ideas that are often conflated:

- **verification:** the code solves the implemented equations consistently;
- **validation:** model outputs are compared with trusted physical or experimental references;
- **regression control:** future code changes preserve an approved numerical baseline unless a documented change is intended.

The v0.9.1 repository has strong verification and regression infrastructure. Experimental validation remains device- and dataset-dependent and must be demonstrated in the associated scientific study.

## Test suite

Run all tests with:

```bash
python -m pytest -q
```

The tests cover the project phases from foundation and regression migration through materials, multi-state devices, electrostatic coupling, local fields, transport, retention, and validation utilities.

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

Golden data should only change after a reviewed physical or numerical modification. The reason and expected output difference must be recorded in the changelog or validation report.

## Benchmarks

The benchmark tools report runtime, traced peak memory, and selected physical outputs such as total FG charge.

```bash
python scripts/run_benchmarks.py
```

Performance numbers depend on Python, NumPy, operating system, and hardware. They are primarily intended for regression tracking, not cross-platform absolute ranking.

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

Save the manifest next to every published dataset or figure. A hash establishes identity of serialized inputs; it does not prove that the physical model is correct.

## Existing validation documents

The repository also includes:

- `docs/Validation_Report.md`
- `validation/README.md`
- `validation/benchmark_results.json`
- phase-specific test-result records

These preserve the Phase D6 baseline from which repository polishing proceeds.
