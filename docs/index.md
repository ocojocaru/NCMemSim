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

## Current status

Phase D is closed at v0.9.0, and repository-polish work is collected in v0.9.1. Optical programming, experimental fitting, automated design-space exploration, and advanced quantum corrections remain future development phases.
