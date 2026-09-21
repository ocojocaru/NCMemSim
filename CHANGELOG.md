# Changelog

All notable changes to NCMemSim are documented in this file.

## Unreleased

### J2 - compact trap-assisted transport kernel

- Implement the J1-selected sequential two-step WKB kernel as isolated scalar
  and broadcast-array entry points, without attaching it to `TransportEngine`.
- Define the exact directed barrier profile relative to the representative trap
  level and expose both leg actions, transmissions, rates, active probability,
  species contributions, aggregate rate and deterministic result hashes.
- Preserve exact disabled and zero-density limits, report transmission
  underflow explicitly, reject invalid numerical contexts, and use stable
  active-probability and slow-leg rate evaluations.
- Verify analytic actions, independent quadrature, field-reversal symmetry,
  slow-leg bounds, broadcast behavior, immutability and v1 API isolation.

### J1 - trap and defect contracts

- Add immutable, strictly validated electron-trap and trap-assisted transport
  specifications with canonical SI units, exact JSON round trips and
  deterministic provenance/configuration hashes.
- Select a compact sequential two-step WKB contract for J2, including the
  representative trap position and an explicit active-trap factor; no new
  transport rate is evaluated or connected to the engine in J1.
- Preserve the approved 204-path v1.0 API baseline while documenting the new
  v1.1 imports as additive APIs rather than retroactive v1.0 guarantees.
- Record primary oxide/Flash TAT literature and distinguish the compact model
  from full multiphonon, percolation and calibrated defect-population models.

### J0 - v1.1.0 advanced transport bootstrap

- Start `1.1.0.dev0` from the published v1.0.0 tag while retaining v1.0.0
  citation metadata as the latest stable release.
- Freeze the approved v1 API, result, archive, scientific-default and
  distribution compatibility boundary for additive Phase J development.
- Define the advanced-transport mechanism boundary, canonical SI units,
  provenance requirements, failure semantics and staged validation ladder.
- Plan J1-J7 delivery for trap/defect contracts, trap-assisted transport,
  optional barrier corrections, network integration, validation, reports and
  final release gates; no new transport physics is implemented in J0.
- Keep automatic CI and Documentation pushes limited to `main`; development
  branches use focused local checks until final-version preparation.

## v1.0.0 — Stable API and release readiness

- Promote the reviewed 204-path API candidate to the first stable NCMemSim release.
- Align package and citation metadata with `1.0.0` and the final release date.
- Retain approved result, archive-reader, scientific-default, distribution and compatibility contracts.
- Record green Python 3.11–3.13 CI, strict documentation, full local regression and clean installed wheel/source-distribution gates.
- Keep the published v0.14.0 archive fixtures as compatibility evidence.
- Publish repository-and-version citation metadata without claiming an unassigned DOI.
- Recorded clean installed wheel/source-distribution evidence and marked the v1.0 stability-preparation candidate ready after all final gates passed.

- Record full local regression final-gate evidence while strict documentation and clean distributions remain open.
- Record remote CI and Documentation final-gate evidence for `prep/v1.0-stability` while keeping local final gates open.
- Configure final candidate gates and CI/Documentation push validation on `prep/v1.0-stability` while keeping every final check `not_run`.
- Approve the v1.0 archival/citation plan while keeping DOI/deposit, final checks and candidate readiness open until final-release evidence exists.

- Approve an exact 204-path stable API candidate surface with source/runtime signatures, retained limitations, generic fitting primitives and explicit scientific scope; archival/citation and final-candidate gates remain open.

- Consolidate v1.0 readiness evidence, pending scope/compatibility decisions and final-candidate gates in a read-only validated matrix.

- Extend distribution gates to all package modules, scientific reference data and frozen archive readers; review runtime/configuration identity limits.

- Review scientific defaults, physical units/signs and scoped parameter provenance; retain existing algorithms and values with compatibility tests.

- Audit typed JSON archive readers and retain seven published-v0.14.0 reference fixtures with integrity and compatibility tests.

- Audit fitting/qualification and DTCO result semantics: raw versus weighted
  residuals, physical covariance units, unavailable diagnostics, failure
  denominators, exact eligibility and provenance boundaries.
- Add cross-layer contract checks without changing library algorithms/defaults.

- Record complete package source/export/documented-import inventory with source
  signatures, public methods and declared fields; add a read-only drift check.
- Document and verify core result units, FG/link/grid axes, dark NaN/zero
  diagnostics, state-copy limits and legacy empty-sweep/input-aliasing behavior.
- Preserve physics/defaults; final approval of all result/schema contracts remains
  separate from this observed baseline.

- Make transport exports explicit while preserving all v0.14.0 wildcard names.
- Add API compatibility preparation policy and focused legacy import checks.
- Correct the API overview to reflect implemented I6 linked workflow reports.
- Preserve package version, scientific defaults and published release tag.

## v0.14.0 — Scientific workflow integration

### I7 — final-version preparation and release gates

- Align package/citation and current documentation with 0.14.0; retain historical
  release evidence and explicit synthetic/FITTED applicability limits.
- Audit strict MkDocs, rendered links, source references and executable I1–I6
  examples; full suite contains 2000 tests, including 192 Phase I cases.
- Validate clean wheel/sdist installations with actual electrical/optical fits,
  linked archives and exports, and audited source-archive bytes.
- Enable CI/Documentation on push to the exact active dev branch, including
  final corrections; remote supported-Python gates follow push before tagging.
- Documentation installs its optional fit dependency for executed examples.
  Preparation does not create a tag, publish assets or establish experimental
  calibration. Remote results must refer to the final prepared commit.


### I6 — linked workflow reports and portable exports

- Add immutable WorkflowReport and typed builder/writer linking full workflow,
  applied context and ordered Robust DTCO studies with explicit DEVICE variants.
- Validate source, evaluator, operating/runtime and declared device links;
  derive scientific status/origins/qualification without provenance promotion.
- Restore archives without fitting/physics and export six non-overwriting
  JSON/CSV/Markdown artifacts retaining source hashes and failure denominators.
- Add electrical/optical normal/error reporting reference and dedicated tests;
  update docs and future installed probe. Existing F/G/H APIs/physics unchanged.


### I5 — cross-workflow integration verification

- Verify real electrical/electro-optical source, fitted application and held-out
  identity links against swaps and recalculated-hash context corruption.
- Verify runtime archive/execution distinction, nominal mismatch rejection,
  all-failed complete-case denominators and unchanged sources in error demos.
- Restore all four linked reference archives with execution entry points disabled.
- Preserve Phase F/G/H API, physics and synthetic/FITTED scientific semantics;
  update development documentation and retain final-version package/Actions gates.



### Phase I4 — synthetic electro-optical workflow reference

- Connect existing photo-capture fitting, diagnostics and held-out synthetic
  qualification to explicit fitted application and actual nominal/Robust DTCO.
- Retain illumination and fitted photo configuration separately, source identity
  links, common exact duration/power manifest and explicit failure accounting.
- Add dedicated parameter recovery, execution, isolation, archive/export and
  optical contract tests; extend the future installed probe/source inventory.
- Update development documentation. No physics/default/API changes or claims
  of experimental calibration/manufacturing yield; package/Actions gates remain
  final-version preparation work.

### I0 — bootstrap and scope/contracts

- Start from published v0.13.0 commit `c3b1c10824c8296e7900e0b9bd8cbb19d6d75f8f`.
- Set the package development version to `0.14.0.dev0`; retain v0.13.0 citation metadata.
- Define I1–I7 evidence, parameter-application, electrical/electro-optical workflow,
  integration report and final-validation deliverables without claiming implementation.
- Preserve Phase F/G/H APIs, units, qualification semantics and simulator physics.
- Require explicit data origin, full device/model/configuration provenance and
  independent assumed variation definitions; no automatic experimental-calibration
  claim, manufacturing yield or fit-covariance conversion.
- Keep local focused tests/docs updates per step; defer full CI, strict Documentation
  builds and clean package checks to final-version preparation on the same dev branch.

### I1 — immutable scientific workflow evidence

- Add a dedicated `ncmemsim.workflows` API for declared dataset origin/provenance,
  immutable dataset and linked workflow evidence snapshots.
- Link existing single-dataset C-V/electrical/photo-program fits to full calibration
  specifications, applied fitted values, optional diagnostics and qualification.
- Preserve FITTED status, explicit eligibility/unknown qualification, synthetic versus
  measured declarations and unavailable/non-finite diagnostic values without promotion.
- Validate source identities and strict JSON restoration without refitting/requalification;
  keep full evaluator-context application and end-to-end references for I2–I6.
- Add real synthetic C-V fit/qualification linkage, mismatch, mutation, restoration,
  scientific-label and rank-diagnostic tests; extend required distribution inventory.

### I2 — explicit fitted application and complete evaluator context

- Add `AppliedWorkflowEvidence`, `WorkflowEvaluator` and `apply_workflow_parameters`
  in the dedicated workflows API; preserve Phase F/G/H and top-level interfaces.
- Apply exact ordered fitted values through existing APIs, with exact canonical
  fitting-unit checks in the adapter and no alias or implicit conversion.
- Capture baseline/applied full devices, materials/layer metadata, core physics,
  shared tunneling, simulation/photo settings, fixed optical defaults, operating
  protocol, sources and application runtime; distinguish full and application hashes.
- Create fresh simulators/state for electrical or electro-optical nominal/sample
  callbacks, passing fitted photo efficiency explicitly at execution.
- Verify strict archival restoration and declared application deltas without running
  fits/physics; reject custom incomplete contexts, model/family drift and mismatches.
- Add genuine fit/application, target compatibility, isolation, context identity,
  restoration and Phase H nominal/sample/failure tests; update docs/source inventory.

### I3 — synthetic electrical fitting/qualification to nominal/Robust DTCO

- Add a runnable electrical reference linking real program-time fitting,
  held-out synthetic qualification, I1/I2 source/context evidence and fresh
  nominal/sample simulator calls, without changing physics or existing APIs.
- Reuse one explicit fitted context across two DEVICE temperature variants and
  one exact manifest; retain full nominal definitions and evaluator/source links.
- Declare synthetic data/noise/weights, RMSE threshold in V, assumed independent
  variations, metric units, occupation-only constraints and robust objectives/policy.
- Preserve FITTED status and separate synthetic eligibility; add declared software
  failures with all-attempted/assessed denominators using existing Phase H reports.
- Test actual fitted predictions, source identities, sampling reuse, direct
  captured-context recomputation, failure accounting, restoration and non-overwrite exports.
- Register the reference in source inventory and future installed probes using
  the existing optional fit extra; defer actual clean builds/installs to I7.

## v0.13.0 — Robust DTCO

Release preparation sets package/citation metadata to `0.13.0` (2026-09-18).
Phase H adds bounded independent variation contracts, exact reproducible sample
manifests, isolated propagation, response statistics, explicit feasibility/failure
accounting, linked nominal comparisons, robust Pareto objectives and report bundles.
Existing physics and Phase G APIs remain compatible. Variation assumptions do
not establish experimentally calibrated manufacturing yield.

The candidate `b5d8374e1a386e00a442b37839784134ae6e6209` passed all six
manual CI test/distribution jobs on Python 3.11–3.13 and manual Documentation.
Local verification passed 1808 tests, strict rendered-documentation auditing and
clean wheel/sdist workflows. Final publication follows review of this release
metadata change; no release tag is created by preparation.

### H0 — bootstrap and contract freeze

- Start Phase H from the published v0.12.0 baseline, preserving its physics,
  DTCO APIs, canonical experiment definitions and scientific regressions.
- Set the development version to `0.13.0.dev0`; keep citation metadata tied
  to the latest published v0.12.0 release.
- Define independent bounded variation and uncertainty contracts, reproducible
  sampling, failure accounting and robust reporting goals without yet adding
  execution APIs or claiming experimental calibration.
- Separate Documentation from full CI for documentation-only changes; validate
  development/PR documentation without deploying it over main Pages.
- Require documentation and source-archive content audits before release tags.

### H1 — bounded variation contracts (0.13.0.dev0)

- Add immutable uniform and truncated-normal definitions with finite explicit bounds.
- Enforce continuous DEVICE/OPERATING bindings, exact canonical units and physical ranges.
- Require variation kind, source and applicability; add nominal endpoint validation and identity hashes.
- Subsequent H2/H3 complete sampling and propagation; Phase G APIs remain unchanged.

### H2 — reproducible independent sampling

- Add explicit seed/count/attempt-budget specifications with unique ordered bindings.
- Sample bounded uniform and truncated-normal laws using local PCG64 scalar draws;
  reject out-of-bounds draws and report exhaustion without clipping or partial output.
- Preserve exact immutable manifests, definitions/provenance, algorithm/runtime
  identity and hashes; restore JSON without regenerating inputs.
- Add dedicated deterministic, statistical, integrity and exhaustion tests.
- Keep documentation current at each step; run Documentation manually at release
  candidate and CI manually or on release tags, without intermediate push/PR Actions.
- Retain propagation and robust statistics as future phases.

### H3 — isolated sample propagation

- Consume exact H2 manifest values without resampling and preserve every sample index.
- Snapshot full nominal device/material/protocol definitions and evaluator settings;
  link nominal, manifest, study and result identities with runtime provenance.
- Validate setup/endpoint context and every combined candidate using Phase G bindings.
- Evaluate serially on isolated copies; snapshot finite JSON outputs and record
  application/evaluation/serialization failures without dropping samples.
- Preserve interrupts and require fresh simulator/state objects in each callback.
- Add dedicated isolation, identity, failure, validation and real program/read tests,
  plus current API documentation and an executable electrical example.
- Leave metrics, feasibility and robust statistics for H4 onward.

### H4 — response statistics and feasibility accounting

- Reuse Phase G metric/unit/constraint definitions on exact H3 results without reevaluation.
- Assess complete metric cases; keep propagation/extraction failures distinct from infeasibility.
- Report total/assessed/feasible/infeasible/failed counts and observed fractions
  with explicit numerators, denominators and undefined zero-assessed behavior.
- Summarize all assessed responses with units/source indices, mean, range,
  population standard deviation and explicitly defined linear quantiles.
- Preserve immutable definitions/results and aggregation identity; reject lossy
  integer-to-float extraction instead of silently changing constraint outcomes.
- Add dedicated statistical/accounting/identity tests and an executable example.
- Leave robust objectives/comparisons and reports for H5/H6.

### H5 — linked nominal comparisons and robust objectives

- Evaluate isolated nominal baselines and compare them with H4 only when full
  device/material/protocol, evaluator/settings and propagation runtime match.
- Preserve nominal failures, feasibility, signed mean differences and explicit
  undefined reasons for missing assessed responses or arithmetic overflow.
- Define robust objectives with exact metric units, direction and statistic/quantile;
  require explicit failure policy, assessed-count and observed-feasibility eligibility.
- Sort eligible studies into exact Pareto fronts, retaining ties and all excluded
  source studies with reasons; reject incomparable definitions/evaluators/runtimes.
- Add linked comparison, eligibility, statistical selection and real program/read
  tests, plus executable examples and updated development status.
- H6/H7 complete reproducible report bundles and release-candidate validation.

### H6 — reproducible Robust DTCO reports and reference

- Snapshot full ordered sample analyses, exact manifests, nominal comparisons
  and robust fronts into integrity-linked immutable report JSON.
- Validate section hashes, source/order links, counts, denominators and statistic
  source identities on restoration without sampling or reevaluating physics.
- Export six non-overwriting UTF-8 JSON/CSV/Markdown artifacts preserving failures,
  undefined values, exact units, objectives and explicit eligibility policies.
- Add a real electrical program/read reference with two nominal temperatures,
  independent assumed variation marginals and deliberate failure-accounting mode.
- Add reporting/restoration/export tests and executable current documentation.
- H7 completes regression, CI/documentation and distribution gates.

### H7 release-candidate validation
- Audit rendered documentation links/anchors, examples and public imports before release.
- Validate every Robust DTCO module and both reference workflows in clean wheel/sdist installations.
- Compare built source-release documentation, assets and required modules with audited checkout bytes.
- Keep CI and Documentation manual during development; remote candidate gates precede publication.

## v0.12.0 — Design-Space Exploration and DTCO

Phase G adds deterministic Cartesian design-space exploration, canonical
binding/unit contracts, explicit metrics and feasibility constraints,
multi-objective Pareto fronts, adjacent-grid sensitivity and reproducible
DTCO reports on the preserved v0.11.0 simulation and calibration baseline.

Release preparation sets the package and citation version to `0.12.0`.
The G7 baseline passed all seven CI jobs on Python 3.11–3.13, including
installed wheel/source workflows and strict documentation. The tag workflow
checks version agreement, regressions and installed distributions before
publication. Creating a tag and publishing release assets are separate steps.

Advanced optimizers and MODEL-scope binding application remain outside the
implemented scope. Grid sensitivity is not a probabilistic Sobol analysis;
software verification does not establish device-specific physical calibration.

### G7 — release validation and distribution checks

- Added wheel and source distribution archive checks and separate installed
  DTCO reference workflows outside the source checkout.
- Verify deterministic reports, manifest restoration, candidate failures and
  CSV exports from each installed distribution.
- Extended CI to the DTCO branch with clean distribution checks on Python
  3.11–3.13 and strict documentation builds.
- Gate tag publication on installed distribution validation; preserve the
  development version and existing scientific behavior.

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

### G5 — sensitivity analysis

- Adds explicit numeric-axis/metric selection and assessed/feasible-only
  eligibility over completed G3 analyses without rerunning simulations.
- Computes adjacent numeric secants while holding all other axes fixed,
  preserving source indices and excluding missing neighbors without bridging.
- Records local slope estimates, endpoint exclusions and arithmetic failures,
  with physical metric/axis unit metadata and unchanged signed responses.
- Adds equal-valid-edge grid-wide signed/absolute slope summaries with
  attempted/estimated/excluded/failed counts and explicit coverage.
- Adds immutable serializable records, complete source provenance and
  deterministic definition/analysis/result hashes without changing G1–G4.
- Adds analytic nonuniform-grid, interaction, isolation, precision and
  real program/read integration coverage.

### G6 — reproducible DTCO reports and reference examples

- Adds immutable report manifests linking exact G2/G3 sources with optional
  Pareto/sensitivity results, rejecting mismatched analyses.
- Adds canonical report hashes and integrity-checked JSON import, with shared
  source data and verifiable component/definition/point identity chains.
- Exports all points and sensitivity intervals to UTF-8 CSV plus complete
  Markdown summaries, refusing existing report targets before writing.
- Adds an executable electrical reference workflow with explicit configuration,
  initial-state policy, runtime versions, derived observables and failure demo.
- Adds optional 300-dpi PNG/vector SVG trade-off figures without a base plotting
  dependency or changes to G1–G5 hashes and simulation semantics.
- Adds integrity, precision, export, source-isolation and reference-workflow tests.

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
