# Changelog

All notable changes to NCMemSim are documented in this file.

## v0.12.0.dev0 — Design-Space Exploration and DTCO (in development)

Development of v0.12.0 is organized as Phase G. The cycle starts from the
released v0.11.0 electrical, retention, optical, electro-optical, fitting, and
calibration baseline.

### G0 — cycle bootstrap and architecture freeze

- Started the `dev/v0.12.0-dtco` development cycle from the tagged v0.11.0
  release.
- Established `0.12.0.dev0` as the development version.
- Defined the Phase G delivery sequence for deterministic design-space
  exploration, metrics and constraints, Pareto analysis, sensitivity analysis,
  and reproducible DTCO reporting.
- Preserved v0.11.0 scientific and regression semantics as the baseline for
  all Phase G work.
- Kept advanced optimizers outside the initial implementation scope: the first
  sweep engine will be deterministic and grid-based.

### G1a — design-variable and experiment-specification core

- Added a dedicated `ncmemsim.dtco` namespace.
- Added typed semantic parameter bindings for device, operating, and model
  scopes without yet applying mutations.
- Added deterministic design-variable definitions with ordered finite domains,
  units, scientific roles, and optional parameter provenance.
- Added experiment specifications tied to the canonical hash of the exact base
  device definition.
- Added deterministic experiment-definition hashes and Cartesian design-point
  counts in preparation for the G2 sweep engine.
- Kept device mutation, sweep execution, metrics, Pareto analysis, and
  optimization outside the G1a checkpoint.

### G1b — controlled device-binding application

- Added copy-on-write application of device-scope parameter bindings.
- Added strict semantic resolution for supported device and named-layer
  attributes rather than arbitrary attribute traversal.
- Added target-type checks and complete post-application device validation.
- Added atomic multi-binding application while preserving the original base
  device on success and failure paths.
- Added experiment design-point application with exact variable-key matching,
  declared-domain checks, and base-device hash verification.
- Strengthened DTCO base-device identity with complete per-layer material
  definitions so material-parameter changes cannot alias the same hash.
- Kept `spatial_profile` outside the controllable binding allow-list until
  non-uniform profile semantics are explicitly validated.
- Kept nested material mutation plus operating/model-scope application outside
  G1b so composition-dependent and protocol-specific semantics can be added
  explicitly rather than inferred.

### G1c1 — material-aware GeSn composition binding

- Added an explicit floating-gate GeSn `sn_fraction` binding path.
- Rebuilds the complete GeSn nanocrystal material through `make_gesn()` rather
  than mutating a derived material field in place.
- Preserves copy-on-write device semantics and post-application validation.
- Rejects non-GeSn materials, invalid fractions, and non-numeric composition
  values.
- Rejects custom/non-canonical GeSn parameterizations when their original
  parameter-set inputs cannot be reconstructed safely from the material object.
- Added experiment design-point coverage for GeSn composition variables.

### G1c2a — operating-variable binding primitives

- Added immutable bindings for program voltage/time, read voltage, and
  optional program integration timestep.
- Added electro-optical bindings for monochromatic wavelength and incident
  optical power density.
- Reconstructs frozen protocol/light-source dataclasses so their existing
  validation remains authoritative.
- Preserves the v0.11 separation of fitted `photo_capture_efficiency` from
  experimental illumination conditions.
- Defers operating-baseline identity and mixed experiment-point application
  to G1c2b.

### G1c2b — operating-baseline identity and mixed experiment points

- Added optional canonical operating-protocol identity to `ExperimentSpec`.
- Preserved device-only experiment serialization by omitting operating identity
  fields when no operating baseline is supplied.
- Requires an operating baseline whenever an experiment declares
  `BindingScope.OPERATING` variables.
- Added mixed device/operating experiment-point application with exact
  assignment, domain, and baseline-identity checks.
- Keeps `BindingScope.MODEL` application deferred so fitted model parameters
  remain distinct from operating conditions.

### G1d — binding/unit contracts

- Validates exact canonical units for known numeric DEVICE and OPERATING
  bindings at DesignVariable construction, without conversions or aliases.
- Rejects categorical domains for known numeric bindings and categorical
  strings with outer whitespace.
- Leaves MODEL binding contracts deferred and preserves valid serialization,
  hashes, domain order, and existing application validation.
- Adds dedicated contract and compatibility coverage.

### G2 — deterministic structured sweeps

- Adds lazy Cartesian points preserving declared axis/domain order, with
  stable indices and experiment-bound point hashes.
- Adds serial evaluation on independent device/protocol candidates using
  the existing validated G1 binding application.
- Isolates application, evaluation, and serialization failures per point;
  rejects invalid setup before evaluation and propagates process interrupts.
- Records finite JSON output snapshots, complete ordered result manifests,
  explicit evaluator identity/parameters, and sweep/result hashes.
- Keeps MODEL application, metrics, constraints, and Pareto analysis deferred.
- Adds ordering, isolation, identity, serialization, electrical/optical, GeSn,
  and real program/read integration tests.

### G3 — metrics and feasibility constraints

- Adds explicit scalar JSON-path metric definitions with units and optional
  minimize/maximize objective direction, preserving signed numeric values.
- Adds named inclusive lower/upper bounds with finite thresholds and exact
  metric/constraint unit contracts.
- Analyzes completed sweeps without rerunning simulation; distinguishes
  feasible, infeasible, source-failed, and extraction-failed points.
- Preserves ordered results, individual bound evaluations, source provenance,
  immutable snapshots, and deterministic analysis/result hashes.
- Keeps G1/G2 serialization unchanged and Pareto ranking deferred to G4.
- Adds dedicated validation, isolation, identity, and real program/read tests.

### G4 — multi-objective / Pareto analysis

- Adds explicit ordered objective selection from directed G3 metrics.
- Adds exact non-dominated sorting across minimize/maximize objectives, with
  zero-based fronts, stable source ordering and retention of tied vectors.
- Ranks feasible points only and retains infeasible/failed points with explicit
  exclusion reasons, preserving all source metrics and failure provenance.
- Preserves signed values and integer precision without weights, tolerances,
  automatic normalization or selection of a single optimum.
- Adds immutable serializable Pareto records and deterministic definition,
  analysis and result hashes without changing G1/G2/G3 serialization.
- Adds independent-reference, tie, exclusion, precision and identity tests.

## v0.11.0 — Experimental Fitting and Calibration

NCMemSim v0.11.0 adds traceable experimental-data handling, deterministic
parameter fitting, uncertainty and identifiability diagnostics, and explicit
calibration qualification while preserving the validated v0.10.0 electrical
and optical simulation baseline.

### Experimental data and deterministic fitting

- Added structured optical and device-observable experimental datasets with
  metadata, conditions, optional uncertainties, deterministic serialization,
  and dataset hashes.
- Added validated optical CSV import with canonical wavelength and absorption
  units.
- Added deterministic least-squares objectives, bounded fit-parameter
  specifications, normalized optimization coordinates, and optional
  SciPy-backed local fitting.
- Added model-based local uncertainty diagnostics including covariance,
  standard errors, parameter correlations, Jacobian rank, scaled singular
  values, and scaled condition number.

### GeSn near-edge fitting and calibration

- Added an opt-in literature-anchored GeSn near-edge reference model and a
  fitting workflow for the direct prefactor and Urbach energy.
- Added explicit FITTED versus CALIBRATED provenance and generic quantitative
  calibration criteria.
- Added independent holdout qualification without re-optimizing fitted
  parameters.
- Added the provenance-preserving digitized Tran et al. (2016) sample-A
  workflow.
- Preserved the scientifically negative real-data result: the declared
  holdout criterion fails, so that workflow reports NOT_CALIBRATED rather
  than weakening the validation threshold.

### Device-level fitting

- Added controlled device-parameter bindings with structural-degeneracy
  checks and identifiability warnings.
- Added synthetic single-parameter fitting workflows for C-V fixed charge,
  fixed-voltage programming-time response, pulse-defined memory window, and
  retention fraction.
- Added an explicit paired program/erase protocol and zero-dwell readout
  semantics.
- Added backward-Euler stabilization for long-time retention occupancy
  integration and numerical refinement audits for the retained synthetic
  benchmarks.

### Electro-optical fitting and photo-capture qualification

- Added device-level binding of `photo_capture_efficiency`.
- Added electro-optical programming-time prediction with illumination during
  programming and dark zero-dwell readout.
- Added single-condition and shared multi-condition
  `photo_capture_efficiency` fitting.
- Added full joint-Jacobian local uncertainty and identifiability diagnostics
  plus per-condition local sensitivity magnitudes.
- Added numerical timestep-sensitivity and cross-grid recovery validation for
  the synthetic photo-capture benchmark.
- Added independent validation qualification of the fitted photo-capture
  efficiency without re-optimization.
- Added auditable CALIBRATED and NOT_CALIBRATED qualification outcomes with
  training-collection, validation, protocol, criteria, and qualification
  hashes.
- Added an explicit synthetic software-validation example that exercises both
  qualification outcomes while making no experimental calibration claim.

### Validation and compatibility

- Expanded the local automated regression suite to **1091 passing tests** at
  the v0.11.0 release-validation checkpoint.
- Preserved the v0.10.0 electrical, retention, optical, and electro-optical
  regression baselines.
- Preserved the distinction between software verification, parameter fitting,
  qualification, and experimental calibration.
- Kept optional global-search initialization and additional independent
  experimental datasets outside the required v0.11.0 scientific scope.

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
