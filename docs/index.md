![NCMemSim — Nanocrystal Memory Simulation Platform](assets/banner.svg)

# NCMemSim

**NCMemSim** is a modular compact multiphysics platform for distributed
floating-gate nanocrystal memories based on Ge, GeSn, and high-k dielectric
stacks.

NCMemSim v0.12.0 preserves the electrical, retention, optical, electro-optical,
fitting and calibration baseline while adding deterministic design-space
exploration and DTCO. Typed experiment definitions, Cartesian sweeps, explicit
metrics and constraints, Pareto fronts, grid sensitivity and reproducible
reports are covered by dedicated Phase G tests and installed distribution
checks. See [DTCO](dtco.md) for contracts, examples and scientific limits.

The platform supports one to three floating gates, local one-dimensional
electrostatics, compact WKB transport, charge redistribution, retention
simulation, deterministic regression references, reproducibility metadata,
and compact Ge/GeSn optical programming models.

The v0.13.0 development line (`0.13.0.dev0`) starts Phase H.
[Robust DTCO](robust_dtco.md) provides H1 bounded definitions and H2
reproducible independent sampling with exact manifests. H3 propagates the
stored samples through isolated candidates; statistics and robust analysis
remain planned for H4 onward.

## Start here

- New users: [Installation](installation.md) and [Quick start](quickstart.md)
- Researchers: [Scientific scope and assumptions](scientific_scope.md)
- Optical modelling: [Optical programming](optics.md)
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
Optional optical absorption + photo-assisted transitions
        ↓
Conservative inter-FG redistribution
        ↓
C-V, transient, retention, and electro-optical outputs
        ↓
Validation, golden references, benchmarks, manifest
```

## Scientific positioning

NCMemSim is intended for mechanism studies and DTCO, not as a full
multidimensional TCAD replacement.

Its value lies in explicit assumptions, modular physics, transparent per-FG
state variables, deterministic regression testing, and a workflow that can be
calibrated against experiment.

### Current status

The v0.11.0 release adds the Phase F experimental fitting and calibration
layer while retaining the Phase E optical-programming implementation and its
regression baseline.

Phase G / v0.12.0 adds deterministic, reproducible design-space exploration
with explicit variables, units, constraints, metrics and provenance, stable
experiment definitions, multi-objective Pareto analysis, grid sensitivity
and exportable reports. G0–G7 implementation and validation are complete;
v0.12.0 is tagged and published, and the DTCO branch is integrated in `main`.

The Phase D electrical framework includes:

- multi-floating-gate state dynamics;
- electrostatic coupling;
- local field profiles;
- inter-FG transport;
- retention;
- validation;
- golden-reference regression;
- benchmarking;
- reproducibility support.

Phase E adds:

- monochromatic optical sources;
- wavelength-dependent Ge/GeSn optical response;
- direct-Gamma absorption;
- indirect phonon-assisted absorption;
- Urbach-tail absorption;
- Beer-Lambert floating-gate absorption;
- absorbed photon flux and generation;
- photo-assisted 0 -> 1 and 1 -> 2 transitions;
- combined electrical and optical programming;
- optical support in relaxation, voltage sweeps, and C-V simulation;
- SWIR wavelength and programming benchmarks;
- SWIR programming-voltage-reduction validation.

Phase F adds:

- structured experimental optical and device-observable datasets;
- deterministic bounded least-squares fitting;
- local uncertainty and identifiability diagnostics;
- explicit FITTED versus CALIBRATED provenance;
- independent-validation calibration qualification;
- GeSn near-edge real-data fitting with a preserved NOT_CALIBRATED holdout
  result;
- synthetic device-level electrical, retention, and electro-optical recovery
  workflows;
- multi-condition photo-capture fitting and auditable qualification.


Phase G adds canonical binding/unit contracts, deterministic Cartesian sweeps,
metrics and feasibility constraints, Pareto fronts, adjacent-grid sensitivity,
and reproducible report exports.

The v0.12.0 suite contains **1598 tests**, including **507 Phase G cases**.
Full tests and clean installed distribution workflows passed on Python 3.11,
3.12 and 3.13; strict documentation and the tag release workflow also passed.

Regression against the retained V5.3 electrical reference remains part of the
validation suite. The legacy timestep inconsistency identified during v0.9.1
release validation remains corrected and covered by regression testing.

The v0.10.0 optical model is a compact physics model. Absolute optical
absorption amplitudes and photo-capture efficiencies are not yet experimentally
calibrated, and the current implementation does not include effects such as
Franz-Keldysh absorption, Stark shifts, state filling, explicit
strain-dependent absorption, nanocrystal quantum-confinement corrections, or
sequential optical attenuation through multiple floating gates.
