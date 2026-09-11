# Roadmap

## Completed foundation

### v0.1.0–v0.3.0: Phases A–C

- modular package foundation;
- migration of the validated compact model;
- material registry, Ge/GeSn models, provenance, band alignment, and optical foundations.

### v0.4.0–v0.9.0: Phase D

- independent multi-FG state representation;
- compact electrostatic coupling;
- local one-dimensional fields;
- explicit tunnel-network transport;
- adaptive retention and charge redistribution;
- scientific validation pack, golden references, benchmarks, and reproducibility manifests.

### v0.9.1: Release validation and repository polish

- R1: repository cleanup, Apache-2.0, centralized version, public API cleanup;
- R2: professional project and scientific documentation;
- R3: GitHub collaboration and CI infrastructure;
- R4: expanded scientific manual and publication-ready assets;
- R5–R6: branding, reproducibility, and release engineering;
- complete 63-test release-validation suite;
- V5.3 regression alignment and correction of the legacy timestep inconsistency;
- continuous-integration validation on Python 3.11, 3.12, and 3.13;
- verified wheel and source-distribution build and clean wheel installation.

### v0.10.0: Optical programming

Phase E establishes the first integrated optical and electro-optical programming capability in NCMemSim.

Implemented capabilities include:

- monochromatic optical source modelling;
- photon-energy and incident photon-flux calculations;
- wavelength-dependent Ge/GeSn optical response;
- separate direct-Gamma, indirect phonon-assisted, and Urbach-tail absorption contributions;
- temperature-dependent phonon occupation for indirect absorption;
- Beer–Lambert absorption through nanocrystal floating-gate layers;
- effective absorption using nanocrystal volume fraction;
- absorbed photon flux and volumetric generation diagnostics;
- absorbed photon rate per nanocrystal;
- configurable photo-assisted charge-state transition rates;
- additive coupling of electrical and optical transition rates;
- electrical-only, optical-only, and electro-optical programming modes;
- optical diagnostics in voltage relaxation, sweeps, and C–V simulation;
- SWIR wavelength-sweep validation;
- SWIR electro-optical programming benchmarks;
- programming-voltage-reduction validation;
- preservation of the validated Phase D electrical regression baseline.

The v0.10.0 validation suite contains 194 tests and covers Phases A through E6.

The optical implementation is intentionally compact. Absolute absorption amplitudes and photo-capture efficiencies remain provisional unless independently calibrated.

## Planned scientific releases

### v0.11.0: Experimental fitting and calibration

The next scientific milestone is experimental calibration of the compact electrical and optical models.

Planned capabilities include:

- import of experimental C–V, memory-window, programming, retention, and optical-response data;
- objective functions and parameter bounds;
- deterministic fitting workflows;
- optional global-search initialization;
- fitting of electrical and optical model parameters;
- uncertainty-aware calibration;
- parameter-correlation and identifiability diagnostics;
- residual analysis and goodness-of-fit metrics;
- calibrated material and device parameter provenance;
- reproducible storage of fitted configurations and metadata.

Candidate fitted parameters may include:

- electrically active nanocrystal fraction;
- nanocrystal diameter or effective size parameters;
- program and erase barriers;
- attempt frequencies;
- field-coupling parameters;
- effective electrostatic parameters;
- optical absorption amplitudes;
- photo-capture efficiency;
- photo-transition weights.

Calibration procedures must distinguish fitted effective parameters from independently measured material properties.

### v0.12.0: Design-space exploration and DTCO

Planned capabilities include:

- structured parameter sweeps;
- reproducible experiment definitions;
- geometry and material design variables;
- electrical and optical operating variables;
- multi-objective metrics;
- Pareto analysis;
- sensitivity analysis;
- reproducible DTCO reports.

Candidate design variables include:

- dielectric thicknesses;
- floating-gate count;
- nanocrystal diameter;
- nanocrystal volume fraction;
- electrically active fraction;
- GeSn composition;
- tunnelling-barrier parameters;
- programming waveform;
- optical wavelength;
- optical power density.

The DTCO layer should expose trade-offs rather than return a single opaque optimum.

### v1.0.0: First stable scientific release

Target requirements include:

- stable and documented public API;
- complete reference documentation;
- reviewed scientific defaults and provenance;
- validated end-to-end electrical and electro-optical examples;
- experimental calibration workflows;
- archived software release;
- DOI-backed software citation;
- publication-quality reproducibility package.

## Post-v0.10 optical extensions

Several optical effects are intentionally outside the current compact model and may be introduced in later revisions:

- experimental calibration of wavelength-dependent absorption;
- experimentally calibrated photo-capture efficiencies;
- broadband and measured optical spectra;
- strain-dependent direct and indirect band gaps;
- nanocrystal quantum-confinement corrections;
- field-dependent absorption, including Franz–Keldysh or related effects;
- Stark shifts;
- state filling;
- improved matrix and effective-medium optical response;
- sequential optical attenuation through multiple floating gates;
- wavelength-dependent optical propagation through complete device stacks.

These extensions should preserve the current high-level optical programming API where practical.

## Longer-term research

Potential post-v1.0 extensions include:

- trap-assisted transport;
- defect-mediated transport;
- image-force effects;
- improved barrier models;
- self-consistent carrier statistics;
- stochastic nanocrystal ensembles;
- temperature-dependent electrical and optical material properties;
- uncertainty propagation;
- neuromorphic and in-memory programming metrics;
- multispectral memory operation;
- larger device families;
- accelerated numerical backends;
- optional integration with higher-fidelity TCAD workflows.

## Roadmap principles

Future development should continue to follow four project rules:

1. validated electrical and optical baselines must not change silently;
2. new model parameters must include units, provenance, calibration status, and applicability range;
3. new physics must include focused unit tests and end-to-end validation;
4. compact-model predictions must be clearly distinguished from experimentally calibrated results.
