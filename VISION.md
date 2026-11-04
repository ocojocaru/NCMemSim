# NCMemSim Vision

## Mission

NCMemSim exists to make the physics, assumptions, and numerical consequences of nanocrystal-memory design explicit, reproducible, and extensible. Its mission is to connect device architecture, material composition, charge-state kinetics, electrostatics, transport, retention, and optical excitation within one transparent research framework.

## Scientific vision

The long-term goal is a DTCO platform for emerging nanocrystal-based non-volatile memories. Instead of treating geometry, materials, and operating conditions as independent afterthoughts, NCMemSim is intended to study their coupled influence on memory window, programming conditions, retention, state separability, and device reliability.

The primary device class is a Ge/GeSn nanocrystal floating-gate stack embedded in SiO2/HfO2 dielectrics. The software architecture is intentionally general enough to support additional nanocrystal materials, barrier models, and excitation mechanisms without rewriting the entire simulator.

## Guiding principles

1. **Physics before convenience.** Every feature should state its assumptions, units, validity range, and limitations.
2. **Reproducibility by default.** A result should be traceable to a device definition, simulation configuration, software version, material provenance, and deterministic reference where applicable.
3. **Modular growth.** Electrostatics, transport, kinetics, optics, fitting, and optimization should remain independently testable.
4. **Conservative evolution.** New models should not silently change validated baselines; regression references and release notes must reveal numerical changes.
5. **Research transparency.** NCMemSim is not presented as a full TCAD replacement. Compact approximations must be labelled as such.

## Research directions

### Optical programming

NCMemSim v0.10.0 establishes the optical-programming foundation with monochromatic light sources, wavelength-dependent Ge/GeSn absorption, absorbed-photon calculations, photo-assisted charge-state transitions, and coupled electro-optical programming.

The current implementation is intentionally compact. Published v1.5 delivers broadband/sequential multi-FG optics and v1.6 delivers opt-in strain and kinetic confinement diagnostics. Remaining work includes independent experimental calibration, measured-spectrum admission, field-dependent optical response and propagation beyond the current single-pass approximation.

### Experimental fitting

The fitting layer will connect simulated C–V, memory-window, programming, and retention observables with experimental data. Parameter bounds, identifiability, uncertainty, and provenance will be treated as first-class outputs rather than hidden optimizer details.

### Design-space exploration

The DTCO layer will explore variables such as dielectric thickness, FG count, NC size, GeSn composition, active fraction, barrier parameters, programming waveform, and optical wavelength. The goal is to identify Pareto fronts rather than a single opaque optimum.

### Neuromorphic and in-memory operation

Published v1.8 provides explicit electrical/matched optical pulse sequences,
multilevel readout separation, gradual updates and bounded retention diagnostics
using existing compact physics. The completed Phase Q
[scope and acceptance sequence](docs/multilevel_operation.md) retains scientific
limits. The first
neuromorphic quantity is a normalized readout-derived weight proxy, with an
explicit mapping from signed flat-band shift. Conductance/current, circuit-level
in-memory computation and physical degradation need separate models. Repeated
update counts do not establish endurance or lifetime.

### Advanced physics

Trap-assisted transport, an opt-in image-force correction and stochastic
ensembles are delivered in v1.1-v1.2. Opt-in Ge optical strain and kinetic confinement diagnostics are delivered in v1.6.
Remaining candidates include improved
barrier shapes, self-consistent carrier statistics, interacting/finite-barrier confinement,
improved charging/interaction models and hierarchical uncertainty. Opt-in anchored temperature
properties are delivered in v1.4.

## Software trajectory

- **v0.9.x:** stabilize repository, documentation, testing, and public interfaces;
- **v0.10:** optical programming foundation;
- **v0.11:** experimental fitting and uncertainty-aware calibration;
- **v0.12:** automated design-space exploration and DTCO;
- **v1.0:** stable scientific API, validated workflows and versioned releases;
  DOI/external deposit only when independently assigned;
- **v1.1-v1.2:** released advanced transport and stochastic ensembles;
- **v1.3:** released explicit MODEL/TAT variability and strict reproducibility bundles;
- **v1.4:** released temperature-dependent properties and strict thermal reports;
- **v1.5:** released broadband/sequential multi-FG optics and strict spectral reports;
- **v1.6:** released hydrostatic strain-induced optical shifts, kinetic confinement diagnostics and strict structural reports;
- **v1.7:** published calibration infrastructure and synthetic numerical diagnostics;
  independent experimental P4B/P5B/P6B qualification remains deferred;
- **v1.8:** published multilevel/neuromorphic diagnostics and strict reports;
  Q7 release and Zenodo archival complete, with experimental P4B/P5B/P6B deferred;
- **v1.9:** published scoped report-restoration optimization, serial performance
  measurements, vendor-neutral interchange/comparisons and strict reports; R7 complete;
- **Phase S / v1.10 target:** S1-S6 explicit electron barrier profiles, isolated
  action evaluation, opt-in direct inter-FG integration and strict isolated reports
  are implemented; S7 compatibility and release preparation is in progress;
  see [Phase S planning](docs/barrier_transport.md);
- **Later (indicative):** broader structural physics, neuromorphic
  workflows, acceleration and higher-fidelity interoperability; see
  [roadmap](docs/roadmap.md). Major-version changes require a compatibility rationale.

## Definition of success

NCMemSim succeeds when another researcher can reproduce a published simulation, inspect each modelling assumption, replace one physical submodel without breaking unrelated components, compare simulation to experiment, and report the exact software and parameter provenance used.

Published v1.9.0 is a minor additive release with retained published module surfaces
and archive semantics. Release and Zenodo archival are complete. Phase S must
justify any next-version decision from compatibility evidence, not from a feature
label alone. S0 introduces no runtime or parameter changes.
