# Changelog

All notable changes to NCMemSim are documented in this file.

## v0.10.0 — Optical Programming

NCMemSim v0.10.0 introduces wavelength-dependent optical and
photo-assisted programming capabilities for Ge/GeSn nanocrystal
nonvolatile-memory structures.

### Highlights

- Added monochromatic optical-source modelling for LED and laser sources.
- Added photon-energy and incident photon-flux calculations.
- Added compact wavelength-dependent optical models for Ge and GeSn.
- Added direct-Gamma, indirect-L, phonon-assisted, and Urbach-tail
  absorption contributions.
- Added temperature-dependent phonon occupation for indirect absorption.
- Added Beer-Lambert absorption through nanocrystal floating-gate layers.
- Added effective nanocrystal absorption using the NC volume fraction.
- Added absorbed photon flux and volumetric photogeneration diagnostics.
- Added absorbed-photon-rate-per-nanocrystal calculations.
- Added configurable photo-assisted 0->1 and 1->2 charge-state
  transition rates.
- Added electrical + optical transition-rate coupling in the occupancy
  engine.
- Integrated optical programming directly into Simulator.relax_voltage().
- Added optical diagnostics to voltage sweeps and C-V simulations.
- Added SWIR wavelength-sweep validation for Ge and GeSn.
- Added electrical, optical, and electro-optical programming benchmarks.
- Added SWIR-assisted programming-voltage-reduction validation.

### SWIR benchmark

A compact benchmark using GeSn with 8% Sn, 5 nm nanocrystals,
a 15 nm floating-gate layer, 1000 W/m^2 incident optical power density,
and a 1 ms programming interval demonstrates wavelength-dependent
photo-assisted voltage reduction.

For a common target occupation:

| Wavelength | V_dark | V_light | Delta V |
|---:|---:|---:|---:|
| 1300 nm | 3.9124 V | 3.8343 V | 0.078071 V |
| 1550 nm | 3.9124 V | 3.8238 V | 0.088539 V |
| 1700 nm | 3.9124 V | 3.8193 V | 0.093025 V |

The spectral ordering of the voltage reduction follows the calculated
photo-transition rate:

1700 nm > 1550 nm > 1300 nm.

The photo-capture efficiency used for this voltage-reduction benchmark
(1e-10) is a benchmark coupling parameter selected to place the dark and
illuminated programming curves in a common comparison range. It is not
an experimentally calibrated material parameter.

Consequently, the voltage-reduction values demonstrate the behaviour
and internal consistency of the compact model and should not be
interpreted as absolute experimental predictions.

### Optical-model scope

The current optical model is intentionally compact. In particular:

- optical absorption is evaluated independently of gate voltage;
- field-dependent Franz-Keldysh and Stark effects are not yet included;
- state filling is not included;
- strain and nanocrystal quantum-confinement corrections are not
  explicitly included in the compact absorption model;
- the HfO2 matrix is treated as optically transparent in the modelled
  spectral range;
- sequential optical attenuation through multiple floating gates is
  not yet modelled;
- absolute absorption amplitudes and photo-capture efficiencies remain
  provisional unless independently calibrated.

The GeSn direct-gap model uses literature-based composition dependence.
The compact absorption formulation separates direct, indirect
phonon-assisted, and Urbach-tail contributions.

### Validation

v0.10.0 extends the automated validation suite through Phase E6:

- E1 — optical sources
- E2 — optical material response
- E3 — optical absorption
- E4 — photo-assisted transition kinetics
- E5 — simulator, sweep, and C-V integration
- E6 — SWIR spectral and programming benchmarks

Current validation status:

**194 tests passed on Python 3.13.12.**

The existing electrical regression and multistate-memory tests remain
green, preserving compatibility with the validated pre-optical model.

## [0.9.1] - 2026-09-09

### Repository Polish — R1: cleanup

- Added Apache License 2.0, repository ignore rules and editor configuration.
- Centralized version metadata and defined an explicit public package API.
- Removed generated cache artifacts from release packages.

### Repository Polish — R2: professional documentation

- Added a complete README, vision, contribution, conduct and citation files.
- Added MkDocs structure and substantive installation, quick-start, architecture, physics, materials, validation, API, developer and roadmap documentation.

### Repository Polish — R3: GitHub infrastructure

- Added CI, documentation and tagged-release GitHub Actions workflows.
- Added issue templates, pull-request template, Dependabot and CODEOWNERS.

### Repository Polish — R4: scientific documentation

- Added dedicated scope, device-state, electrostatics, transport-retention, reproducibility, workflow and glossary chapters.
- Reorganized documentation around scientific assumptions, validation and reproducible workflows.

### Repository Polish — R5: assets and branding

- Added logo, banner and reusable SVG diagrams for device stacks, software architecture, transport and scientific workflow.
- Integrated visual assets into README and MkDocs documentation.

### Repository Polish — R6: release engineering

- Added the release gate, first-publication procedure and security policy.
- Finalized executable CI, GitHub Pages and tagged-release workflows.
- Added tag/version verification and automated wheel/source-distribution release assets.
- Expanded GitHub issue and pull-request templates for scientific-software traceability.
- Consolidated the cumulative R1–R6 project into the final `v0.9.1` release.

## 0.4.0 — Phase D1

- Removed the one-FG-only simulator guard.
- Added traceable FG IDs, physical layer names, and centre coordinates to states.
- Added strict state/device and grid-size validation.
- Added independent transient evolution for 1–3 floating gates.
- Added per-FG charge, occupation, field, and transmission outputs.
- Added two-dimensional per-FG sweep histories.
- Preserved the legacy scalar API and one-FG numerical regression.
- Added seven Phase-D1 tests; complete suite: 34 passed.

## 0.3.0 — Phase C

- Replaced the flat material module with a scalable material package.
- Added parameter provenance, units, and status tracking.
- Added versioned Ge and GeSn models and a registry.
- Added configurable interpolation and bowing parameters.
- Added band-alignment and compact optical-material interfaces.
- Added reproducibility manifests and the Developer Guide.
- Preserved Phase B public imports and regression behavior.

## 6.0.0-alpha2 — Phase B

- Migrated v5.3 electrostatics into `ElectrostaticsEngine`.
- Migrated trapezoidal WKB into `TunnelingEngine`.
- Migrated distributed P0/P1/P2 kinetics into `OccupancyEngine`.
- Added `PhysicsModel`, `DeviceState`, and a modular one-FG `Simulator`.
- Added a v5.3 reference device with effective FG permittivity 18 and original barriers.
- Added regression tests for capacitance, flat-band voltage, charging energy, WKB, probability stepping, one-voltage relaxation, and a compact C–V sweep.

## 0.5.0 - Phase D2

- Added `CouplingModel`, `CompactCouplingModel`, and `CouplingResult`.
- Added centroid-based electrostatic sensitivity factors for 2/3-FG devices.
- Preserved the validated one-FG relation `Delta VFB = -QFG/Cox` exactly.
- Added per-FG flat-band-shift contributions and a diagonal D2 coupling matrix.
- Added a 1-D displacement-field solver with floating-gate sheet charges.
- Connected local per-FG fields to multi-FG WKB rate calculations.
- Extended transient and sweep results with D2 coupling diagnostics.

## 0.6.0 — Phase D3

- Added `FieldSolver1D` and immutable `FieldProfile`.
- Added complete one-dimensional potential and electric-field profiles.
- Added local potential and local field values at every floating-gate centroid.
- Added sheet-charge displacement jumps at FG centroids.
- Integrated field profiles into `ElectrostaticsResult`, simulator outputs, sweep outputs and `FloatingGateState`.
- Preserved the validated one-FG kinetic path and all Phase A–D2 regression tests.

## 0.7.0 - Phase D4

- Added a graph-like transport layer with `TransportNode`, `TunnelLink`, and `TunnelNetwork`.
- Added nearest-neighbour FG↔FG WKB transport with conservative electron redistribution.
- Added substrate↔nearest-FG diagnostic links without double-counting the existing substrate kinetics.
- Added per-link transmission, directional rates, fields, potential differences, and electron fluxes.
- Integrated transport into transient relaxation and voltage-sweep results.
- Added Phase D4 example and regression tests.

## 0.8.0 - Phase D5

- Added `RetentionConfig`, `RetentionSolver`, and `RetentionResult`.
- Added adaptive geometrically growing time steps with logarithmic output sampling.
- Recomputed electrostatics, local fields, substrate kinetics, and inter-FG transport at every retention step.
- Added per-FG charge, occupation, local field, flat-band drift, and transport histories.
- Added automatic quasi-equilibrium detection and optional early termination.
- Added charge-retention and charge-loss convenience properties.
- Added Phase D5 example and regression tests.

## 0.9.0 - Phase D6

- Added deterministic golden regression cases for one-, two-, and three-FG devices and retention.
- Added physics-consistency validation APIs for states, materials, fields, and charge conservation.
- Added reproducibility schema v2 with runtime metadata and canonical SHA-256 hashes.
- Added benchmark instrumentation for execution time and peak traced memory.
- Added a Scientific Validation Pack, validation report, scripts, and GitHub Actions workflow.
