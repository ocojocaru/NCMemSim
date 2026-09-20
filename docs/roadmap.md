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

## Current and planned scientific releases

### v0.11.0: Experimental fitting and calibration

The v0.11.0 milestone adds traceable experimental-data handling, parameter fitting, uncertainty and identifiability diagnostics, and explicit calibration qualification.

The v0.11.0 scientific scope is complete and released. The release includes:

- structured experimental optical datasets with source and sample metadata;
- validated CSV import using canonical wavelength and absorption units;
- deterministic least-squares objective evaluation with optional uncertainty weighting;
- explicit fit-parameter bounds and reproducibility hashes;
- optional SciPy-backed deterministic least-squares fitting;
- a GeSn near-edge fitting workflow for the direct prefactor \(A\) and Urbach energy \(\Delta E\);
- model-based local uncertainty estimates, covariance, parameter correlation, rank, and scaled-condition diagnostics;
- a generic calibration-qualification framework with explicit quantitative validation criteria;
- separation of `FITTED` from `CALIBRATED` parameter provenance;
- GeSn-specific promotion from `FITTED` to a new `CALIBRATED` parameter set only when all configured qualification criteria pass;
- a provenance-preserving digitized optical reference dataset from Tran et al. (2016);
- a reproducible real-data fitting and holdout-validation workflow for Tran et al. sample A;
- serialized dataset, parameter-specification, criteria, and qualification hashes.

- generic device-observable datasets and objective adapters for C–V, memory-window, and retention measurements;
- controlled device-calibration parameter bindings with structural degeneracy checks and identifiability warnings;
- a synthetic single-parameter C–V recovery workflow for `qfix_C_m2`;
- explicit fixed-voltage program-pulse and zero-dwell \(\Delta V_\mathrm{FB}\) readout semantics;
- a synthetic single-parameter \(\Delta V_\mathrm{FB}(t_\mathrm{prog})\) recovery workflow for `nu0_Hz`;
- an explicit paired program/erase protocol with independent branches and a pulse-defined memory window;
- a synthetic single-parameter pulse-defined memory-window-versus-programming-time recovery workflow;
- backward-Euler stabilization for long-time retention occupancy integration;
- a synthetic single-parameter retention-fraction-versus-time fitting workflow with caller-supplied initial-state and protocol hashes, physical-time interpolation, and no extrapolation;
- recovery of the effective FG erase barrier in an accelerated fixed-bias retention benchmark;
- numerical-refinement audit of that accelerated retention benchmark, including cross-grid parameter-bias/runtime selection of a practical reproducible example grid;
- explicit separation between dynamic C–V hysteresis windows and pulse-defined state-separation windows.

- explicit electro-optical program-pulse prediction with dark, zero-dwell readout;
- controlled device-level binding of `photo_capture_efficiency`;
- synthetic single-parameter recovery of `photo_capture_efficiency` from illuminated `delta_vfb` versus programming-time data;
- shared-parameter fitting across multiple optical wavelength/power conditions;
- joint local uncertainty and identifiability diagnostics from the full multi-condition Jacobian, including per-condition local sensitivity magnitudes.
- numerical timestep-sensitivity and cross-grid recovery audit for the synthetic photo-capture benchmark, retaining 1e-5 s as the practical example timestep for that benchmark only.
- independent device-level qualification of a fitted `photo_capture_efficiency` against a validation dataset without re-optimizing the fitted parameter;
- auditable `CALIBRATED`/`NOT_CALIBRATED` photo-capture qualification results with training-collection, validation, protocol, criteria, and qualification hashes.

The first real-data reference workflow intentionally does **not** produce a calibrated parameter set. Using the digitized Tran et al. sample-A holdout, the fitted near-edge model gives a validation RMSE of approximately \(4.50\times10^4\ \mathrm{m^{-1}}\), above the predeclared digitization-based qualification threshold of approximately \(1.57\times10^4\ \mathrm{m^{-1}}\). The workflow therefore reports `NOT_CALIBRATED`.

This negative qualification result is preserved as a scientific result rather than weakening the validation threshold.

The synthetic device-level recovery workflows, including pulse-memory and retention fitting, demonstrate deterministic parameter recovery only. They report `FITTED`, not `CALIBRATED`, and do not substitute for independent experimental device validation.

The v0.11.0 release-engineering cycle is complete: package/distribution validation,
supported-Python CI, tagged release verification, and release assets all passed.

Post-v0.11.0 extensions may include:

- optional global-search initialization before deterministic local fitting;
- additional independent experimental validation datasets.

Candidate fitted parameters for later workflows may include:

- electrically active nanocrystal fraction;
- nanocrystal diameter or effective size parameters;
- program and erase barriers;
- attempt frequencies;
- field-coupling parameters;
- effective electrostatic parameters;
- optical absorption amplitudes;
- photo-capture efficiency;
- photo-transition weights.

Calibration procedures must distinguish fitted effective parameters from independently measured material properties. Material-absorption data must not be used to infer device-specific photo-capture efficiency without a corresponding device observable.

### v0.12.0: Design-space exploration and DTCO

**Status: released as `v0.12.0`, integrated in `main`.**

The G7 baseline passed full regression tests and clean installed distribution
workflows on Python 3.11–3.13, plus strict documentation. The package version
is `0.12.0`; stable-version/main CI, tag publication and documentation
deployment have passed.

Phase G is organized as:

- **G0 — cycle bootstrap / architecture freeze:** development version,
  scope, invariants, delivery sequence, and release baseline;
- **G1 — design variables and experiment specifications:** typed variables,
  domains, units, parameter bindings, deterministic experiment definitions,
  and provenance;
- **G2 — deterministic structured sweeps:** Cartesian/grid exploration,
  stable point ordering, failure isolation, reproducible hashing, and
  serializable results;
- **G3 — metrics and feasibility constraints:** explicit metric extraction,
  objective direction, constraint evaluation, and infeasible-point handling;
- **G4 — multi-objective / Pareto analysis:** non-dominated sorting and
  transparent trade-off surfaces without a single opaque optimum;
- **G5 — sensitivity analysis:** adjacent-grid secants and coverage
  summaries with explicit units (not probabilistic global sensitivity);
- **G6 — reproducible DTCO reports and reference examples:** exportable
  experiment/result manifests, publication-ready summaries, and end-to-end
  examples;
- **G7 — v0.12.0 release validation:** regression preservation, supported
  Python CI, documentation, distribution validation, and tagged release.

Implemented v0.12.0 capabilities include:

- structured deterministic parameter sweeps;
- reproducible experiment definitions;
- geometry and material design variables;
- electrical and optical operating variables;
- explicit feasibility constraints;
- multi-objective metrics;
- Pareto analysis;
- sensitivity analysis;
- reproducible DTCO reports.

The first implementation intentionally prioritizes deterministic grid-based
exploration. Latin-hypercube sampling, Bayesian optimization, evolutionary
optimization, and other adaptive/global optimizers are not prerequisites for
the initial Phase G architecture.

Supported executable bindings include device work function, substrate doping,
temperature, named-layer thickness/NC diameter/volume and active fractions,
grid points, canonical GeSn composition, program voltage/time/internal step,
read voltage, optical wavelength and optical power density. The exact paths
and units are listed in [DTCO binding contracts](dtco.md#g1d-bindingunit-contracts).

Changing FG count, arbitrary tunnelling barriers and arbitrary programming
waveforms is not an executable DTCO binding in v0.12.0. MODEL scope remains
declarative; advanced optimizers and categorical sweep execution require
future semantic contracts.

The DTCO layer should expose trade-offs rather than return a single opaque optimum.

### v0.13.0: Robust DTCO

**Status: H0–H7 complete; package version `0.13.0`.**

Phase H adds independent bounded parameter variations and uncertainty
propagation on the preserved deterministic Phase G workflow. See
[Robust DTCO scope and contracts](robust_dtco.md) for the delivery sequence,
failure accounting, reproducibility rules and scientific limits. H1 supplies
bounded definitions and H2 supplies independent sampling with exact manifests.
H3 adds serial propagation with isolated candidates and staged failure records.
H4 adds assessed response statistics with explicit denominators and separate
feasible/infeasible/failure counts. H5 adds linked nominal comparisons and explicit
robust objectives/fronts. H6 adds linked report bundles and an electrical reference
with deliberate failure accounting. H7 candidate validation passed local regression, manual supported-Python CI,
strict documentation auditing and clean wheel/sdist installations.

### v0.14.0: Scientific workflow integration

**Status: v0.14.0 published; I0–I7 completed and promoted into v1.0.0.**

Local full regression, strict documentation and clean distributions are final
gates. CI/Documentation run after push on the prepared dev branch; tag/publication
follow successful remote checks on that exact commit.

Link existing fitting/calibration evidence and explicitly applied parameter
contexts to nominal and Robust DTCO. Deliver electrical and electro-optical
references, complete source/context provenance, staged failure verification and
linked integration reports without changing simulator physics or promoting
synthetic evidence to experimental-calibration claims. See
[Scientific workflow integration](scientific_workflows.md) for I0–I7 acceptance
contracts and final-release gates. Local focused tests/docs updates run at each
step; full CI, strict Documentation and clean distributions run at final-version
preparation on the same dev branch. The later v1.0 stability review approved
the public API, compatibility scope, scientific defaults, distribution contract
and final release gates.

### v1.0.0: First stable scientific release

**Status: released as `v1.0.0`; all required local and remote gates passed.**

The release includes:

- stable and documented public API;
- complete reference documentation;
- reviewed scientific defaults and provenance;
- validated end-to-end electrical and electro-optical examples;
- experimental calibration workflows;
- exact versioned GitHub source and distribution archives;
- repository-and-version software citation, with no DOI claimed until one is assigned;
- publication-quality reproducibility package.

### v1.1.0: Advanced transport physics

**Status: J1 contracts complete; package version `1.1.0.dev0`.**

Phase J begins from the immutable v1.0.0 tag and preserves the approved v1
public API and scientific baseline. J1 adds inert trap contracts and selects
the compact J2 equation. It does not yet change transport equations or defaults.

The planned sequence is:

- **J0 - scope and architecture freeze:** compatibility boundary, mechanism
  decomposition, canonical units, provenance, failures and validation ladder;
- **J1 - trap and defect contracts (complete):** immutable specifications, selected TAT
  equation, energy/field/carrier conventions and serialization;
- **J2 - trap-assisted transport kernel:** opt-in rates, component diagnostics,
  analytic limits and numerical-range validation;
- **J3 - image-force and barrier corrections:** explicit opt-in corrections
  with unmodified-barrier diagnostics; this stage may be deferred if the
  scientific contract is not sufficiently supported;
- **J4 - transport-network integration:** explicit link attachment,
  per-mechanism accounting, state isolation and failure propagation;
- **J5 - scientific validation and sensitivity:** controlled references,
  parameter sensitivity, identifiability limits and DTCO integration;
- **J6 - reproducible examples and reports:** normal/failure references,
  mechanism-resolved exports and interpretation limits;
- **J7 - v1.1.0 release gates:** full regression, strict documentation, clean
  distributions and supported-runtime remote validation.

See [Advanced transport physics](advanced_transport.md) for the governing J0
contracts. New mechanisms remain disabled by default and synthetic examples do
not establish experimental defect calibration.

## Post-v0.10 optical extensions

Several optical effects are intentionally outside the current compact model and may be introduced in later revisions:

- further experimental calibration of wavelength-dependent absorption using independent datasets;
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
- correlated and hierarchical uncertainty propagation beyond Phase H;
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

## Stability preparation from published v0.14.0

Local API/result/archive/default/distribution reviews and the archival/citation
policy are recorded in the [v1.0 readiness consolidation](release_readiness.md).
The stable API, scientific scope and citation policy are approved, and the full
regression, strict documentation, clean-distribution and remote Actions gates
all passed. The preparation branch was promoted to `main` for v1.0.0.
