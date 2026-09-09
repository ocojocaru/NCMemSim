![NCMemSim — Nanocrystal Memory Simulation Platform](assets/banner.svg)

# NCMemSim

**NCMemSim** is a modular compact multiphysics platform for distributed floating-gate nanocrystal memories based on Ge, GeSn, and high-κ dielectric stacks.

The current v0.9.1 scientific kernel supports one to three floating gates, local one-dimensional electrostatics, compact WKB transport, charge redistribution, retention simulation, deterministic regression references, and reproducibility metadata.

## Start here

- New users: [Installation](installation.md) and [Quick start](quickstart.md)
- Researchers: [Scientific scope and assumptions](scientific_scope.md)
- Model developers: [Software architecture](architecture.md) and [Developer guide](developer.md)
- Reproducibility: [Validation](validation.md) and [Reproducibility and benchmarking](reproducibility.md)

## Model map

```text
Device and materials
        ↓
State initialization: P0, P1, P2 for each FG
        ↓
Electrostatics and local field profile
        ↓
Occupancy kinetics + WKB transport
        ↓
Conservative inter-FG redistribution
        ↓
C–V, transient, and retention outputs
        ↓
Validation, golden references, benchmarks, manifest
```

## Scientific positioning

NCMemSim is intended for mechanism studies and DTCO, not as a full multidimensional TCAD replacement. Its value lies in explicit assumptions, modular physics, transparent per-FG state variables, deterministic regression testing, and a workflow that can be calibrated against experiment.

### Current status

NCMemSim v0.9.1 is the current validated release.

The Phase D physics framework is complete and includes multi-floating-gate
state dynamics, electrostatic coupling, local field profiles, inter-FG
transport, retention, validation, golden-reference regression, benchmarking,
and reproducibility support.

The v0.9.1 release also completes repository, documentation, CI, and release
engineering. The full automated test suite contains 63 tests and is validated
on Python 3.11, 3.12, and 3.13.

Regression against the legacy V5.3 reference implementation is included in the
validation suite. During release validation, a legacy timestep inconsistency
for dwell times shorter than the internal timestep was identified and corrected
in the retained V5.3 reference implementation.

Optical programming, experimental parameter fitting, automated design-space
exploration, and advanced quantum corrections remain planned development areas.
