# NCMemSim Vision

## Mission

NCMemSim exists to make the physics, assumptions, and numerical consequences of nanocrystal-memory design explicit, reproducible, and extensible. Its mission is to connect device architecture, material composition, charge-state kinetics, electrostatics, transport, retention, and eventually optical excitation within one transparent research framework.

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

Future releases will represent light sources, wavelength-dependent absorption, photocarrier generation, and coupled electro-optical programming. Target sources include monochromatic lasers and LEDs, broadband incandescent or xenon-like sources, and solar-spectrum presets.

### Experimental fitting

The fitting layer will connect simulated C–V, memory-window, programming, and retention observables with experimental data. Parameter bounds, identifiability, uncertainty, and provenance will be treated as first-class outputs rather than hidden optimizer details.

### Design-space exploration

The DTCO layer will explore variables such as dielectric thickness, FG count, NC size, GeSn composition, active fraction, barrier parameters, programming waveform, and optical wavelength. The goal is to identify Pareto fronts rather than a single opaque optimum.

### Neuromorphic and in-memory operation

Multi-level charge states, gradual programming, retention, optical sensitivity, and coupled FG dynamics may support future studies of synaptic weight update, non-linearity, state symmetry, endurance proxies, and multispectral memory functions.

### Advanced physics

Candidate extensions include improved barrier shapes, self-consistent carrier statistics, trap-assisted transport, image-force effects, quantum confinement, Coulomb charging, temperature-dependent material properties, stochastic NC distributions, and uncertainty propagation.

## Software trajectory

- **v0.9.x:** stabilize repository, documentation, testing, and public interfaces;
- **v0.10:** optical programming foundation;
- **v0.11:** experimental fitting and uncertainty-aware calibration;
- **v0.12:** automated design-space exploration and DTCO;
- **v1.0:** stable scientific API, validated workflows, archived release, and DOI;
- **v2.x:** advanced physics, larger device families, and optional high-performance backends.

## Definition of success

NCMemSim succeeds when another researcher can reproduce a published simulation, inspect each modelling assumption, replace one physical submodel without breaking unrelated components, compare simulation to experiment, and report the exact software and parameter provenance used.
