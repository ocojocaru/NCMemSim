# Reproducibility, validation, and benchmarking

## Reproducibility manifest

`build_reproducibility_manifest()` creates a structured record of the software and simulation environment. The schema includes:

- NCMemSim version;
- Git commit when available;
- Python, NumPy, platform, and runtime information;
- deterministic hashes of device and simulation configurations;
- random seed;
- material-model identifiers.

A published dataset or figure should store this manifest together with the input configuration and output data.

## Validation reports

The validation API returns `ValidationReport` objects containing structured `ValidationIssue` entries. Dedicated checks cover:

- probability normalization;
- device and material consistency;
- field-profile consistency;
- internal charge conservation;
- complete simulation outputs.

Validation is intentionally separate from execution: a simulation can be inspected and diagnosed without converting every warning into an exception.

## Golden references

`build_golden_suite()` creates deterministic reference cases for:

- a one-FG V2 stack;
- a two-FG V2 stack;
- a three-FG V2 stack;
- a short retention trajectory.

`compare_golden()` detects numerical drift against stored references. Golden cases are regression anchors, not experimental validation.

The historical file name `phase_d6_v0.9.0.json` identifies the Phase D6 numerical baseline and is intentionally preserved in v0.9.1.

## Benchmarks

`benchmark_case()` and `run_benchmark_suite()` report runtime, traced peak memory, and representative output quantities such as total FG charge. Benchmarks support regression monitoring but should not be treated as portable absolute performance guarantees across machines.

## Recommended evidence hierarchy

A defensible scientific result should distinguish four levels:

1. **code correctness:** unit tests and invariants;
2. **numerical regression:** golden references;
3. **physical consistency:** limits, trends, and conservation checks;
4. **experimental validity:** comparison with measured C–V, transient, spectral, or retention data.

The current repository provides the first three foundations. Experimental validation remains device- and dataset-specific.

## Reproducing repository checks

From the repository root:

```bash
python -m pytest
python scripts/generate_golden.py
python scripts/run_benchmarks.py
```

Generated artifacts should be reviewed before replacing an accepted golden reference. A changed reference is evidence of changed behaviour, not automatically evidence of an improvement.
