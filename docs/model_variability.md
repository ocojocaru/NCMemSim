# Model and trap-assisted transport variability

## L0 status and baseline

Planning baseline: published v1.2.0, commit b9d2ff77136217af5b3b5a4b5a4780af5d75d6d5.
Target release: v1.3.0. This document establishes the L0 planning contract;
L1 contracts, L2 isolated execution, L3 controlled density reference, L4 population analysis, L5 variability-aware DTCO and L6 integrity-checked reports are implemented; L7 is pending. No MODEL binding or new runtime API is implemented by L0.
The package remains 1.2.0 until a separate development-cycle bootstrap.

## Scientific objective and first executable scope

Extend Phase K realization to explicitly selected MODEL inputs owned by the
existing advanced transport configuration. The first supported quantity will
be TrapSpecies.density_m3, in m^-3, finite and non-negative, addressed through
an explicit transport-link and trap-species identity. L1 freezes the binding path as
`advanced_transport / attachments / <link_id> / species / <species_name> / density_m3`
with `BindingScope.MODEL`. Exact names, rather than positional indices, identify targets.
Duplicate or ambiguous identities, conflicting assignments and unsupported
model paths must fail explicitly. Arbitrary attribute mutation is excluded.

Trap energy, capture cross section, barrier parameters and attempt frequency
remain later candidates, not promised L1 capabilities. Synthetic density
distributions are assumptions, not experimentally established defect populations.
No new transport equation, atomistic defects, kinetic Monte Carlo, spatial
percolation, fabrication-yield prediction or automatic distribution fitting is
included. Hierarchical uncertainty is a separate future contract.

## Compatibility and ownership

- Preserve the stable v1.2 imports, deterministic behavior, defaults, archive
  readers, DTCO, Robust DTCO and calibration semantics.
- Stochastic model application is explicit and opt-in. Existing MODEL rejection
  stays intact until the reviewed additive implementation is available.
- Reconstruct and validate immutable model configuration for each realization;
  never mutate the nominal device, transport configuration or other samples.
- Preserve direct/TAT mechanism decomposition and existing failure semantics.
- Reuse Phase K distributions, RNG and correlation rules. Do not introduce a
  second sampler or silently resample, clip or discard invalid realizations.
- Constant nominal assignments must recover the nominal workflow within its
  existing exact or declared numerical tolerance. Disabled TAT must preserve
  the existing direct baseline. Zero-density cases follow the existing TAT
  validation rules; they must not be forced through an invalid enabled spec.

## Identity, archives and accounting

Record the nominal and realized transport-configuration identities, ordered
bindings, sample identity, distribution and dependence provenance, model
version and enabled mechanisms. L1 introduces separate versioned definition contracts; L2 must review its
execution/result schema independently. Existing Phase K payloads and
hashes retain their meaning; old archives must not acquire inferred MODEL data.
Round-trip readers must reject unknown fields and unsupported versions under
the existing archival policy.

Configuration failures remain distinct from numerical execution failures,
metric extraction failures and physical infeasibility. Reuse existing failure
stages where their meaning applies; review any additional stage explicitly.
Every attempted realization remains in population counts and report evidence.
Keep simulated_pass_fraction, ensemble_feasibility_fraction and their current
denominators. No manufacturing yield or experimental calibration is claimed.

## Delivery sequence and acceptance

| Step | Deliverable | Acceptance |
|---|---|---|
| L0 | Scope, invariants, ownership and delivery plan | Documented v1.2 baseline; no runtime change |
| L1 | Density binding, typed ownership and identity contracts | Unambiguous link/species addressing; units/domains; round trips; compatibility decision |
| L2 | Isolated model realization and execution integration | Nominal and sibling inputs unchanged; invalid configurations isolated; model hashes retained |
| L3 | Controlled density-variability transport reference | Real solver; nominal/constant/disabled-mechanism limits; direct/TAT diagnostics |
| L4 | Phase K statistics and failure integration | Exact counts/denominators; all-failed and mixed-result cases; no silent exclusions |
| L5 | Variability-aware DTCO reference | Explicit design linkage; eligibility and transparent Pareto objectives |
| L6 | Integrity-checked reports and reproducibility | Nested identities checked; complete attempted population; deterministic rebuilds; no overwrite |
| L7 | Compatibility review and release | Regression, strict docs, clean wheel/sdist, Python 3.11-3.13 CI, exact-commit docs/tag/release checks |

The first density reference must declare its distribution, seed, sample count,
nominal TAT configuration, protocol, observable, units and numerical tolerances.
Select numerical values from the existing validated J references during L3;
do not invent a process distribution. Audit timestep sensitivity and sample-size
limitations before interpreting tails. Density and capture cross section can
be structurally confounded; a density-only study fixes cross section explicitly
and cannot establish independent experimental identifiability of both.

## Immediate L1 preparation

1. Audit ensemble/realization.py, ensemble execution/specification, transport/
   integration.py, transport/traps.py and DTCO binding contracts.
2. Freeze the smallest density-only binding and model-context serialization.
3. Define focused checks for ambiguous targets, domain and enabled-spec
   validation, input isolation, zero variation, old archives and failure counts.
4. Implement contracts before model execution; keep L2-L6 incremental.

Historical v1.0/v1.1/v1.2 evidence remains historical. Candidate checks must be
rerun on the final v1.3 identity; L0 does not approve a release.

## L1 implemented contracts

The provisional module `ncmemsim.ensemble.model_contracts` provides
`trap_density_binding`, `TrapDensityVariable`, `TransportModelContext` and
`ModelVariabilitySpec`. These module-qualified paths are development contracts;
they are not added to the 59 frozen v1.2 package exports or declared stable by L1.

The new schemas are `trap-density-variable-v1`, `transport-model-context-v1`
and `model-variability-spec-v1`. Strict dictionary readers reconstruct nested
TAT species, specifications and image-force corrections, reject unknown fields
and unsupported versions, and recompute canonical identities from actual data.
Hash properties are derived identities; `from_dict` does not authenticate an
archive or validate an external claimed digest. Transport declaration order is
identity-significant, matching the existing AdvancedTransportSpec contract.

TransportModelContext owns the complete AdvancedTransportSpec attachment map,
including mechanism enablement, equation family, species and barrier-correction
provenance. It is not a complete PhysicsModel or engine configuration. L2 must
link the remaining workflow physics/engine inputs explicitly before execution.
ModelVariabilitySpec binds this context to a complete device-definition hash,
an optional supported operating-protocol identity and an ordered variable list.
It accepts density variables together with existing DEVICE/OPERATING variables,
requires at least one density variable, and rejects unknown targets, duplicate
names/bindings, nominal/context mismatches and invalid physical domains.

Phase K StochasticVariable, EnsembleSpec, samplers and executors remain unchanged
and do not accept the new MODEL definitions. L1 neither draws samples nor applies
densities to a model. No zero-variation solver equivalence is claimed until L2/L3.

```python
from ncmemsim.ensemble.model_contracts import trap_density_binding

binding = trap_density_binding("declared-link-id", "declared-trap-species")
assert binding.path[-1] == "density_m3"
```

L1 tests cover strict nested round trips, physical units/domains, target
resolution, identity sensitivity, immutable source ownership, disabled/zero-density
rules and preserved Phase K rejection/archival boundaries. The current source API
inventory is regenerated for the additive module; historical stable proposals,
release reviews, release evidence and package version remain unchanged.

## L2 isolated realization and execution

The provisional `ncmemsim.ensemble.model_sampling` module adds
`ModelSamplingSpec`, `ModelSampleManifest` and `generate_model_sample_manifest`.
It reuses the unchanged Phase K PCG64 scalar kernels and Gaussian-copula
transforms, including declaration order and draw budgets. New envelopes have
the schemas `model-sampling-spec-v1` and `model-sample-manifest-v1`. Individual
samples retain the existing EnsembleSample scalar format but are bound to the
new sampling-specification hash; they cannot be executed by Phase K APIs.
Stored manifest values are authoritative. Strict dictionary/JSON restoration
validates nested identities and never resamples. Sampling-kernel failures abort
generation with sample index and variable identity; out-of-physical-domain
draws remain stored values and are classified during realization, without
clipping, rejection-resampling or silently dropping attempts.

The provisional `ncmemsim.ensemble.model_execution` module adds
`AppliedModelRealization`, `apply_model_sample_to_context`,
`ModelExecutionPoint`, `ModelExecutionResult` and
`execute_model_sample_manifest`. Every sample receives its own device and
operating-protocol copies and a reconstructed immutable advanced-transport
configuration. All density assignments are applied before enabled-specification
validation, avoiding invalid intermediate states in simultaneous updates.
Device/operating bindings reuse the established application contracts.

Changed densities are recorded as ASSUMED assigned values in the realized trap
species, retaining the original source plus a realization marker; distribution
provenance remains in the full study. They do not inherit nominal CALIBRATED
status. An unchanged density preserves nominal provenance and configuration
identity, including the zero-variation invariant. Disabled TAT remains disabled;
an enabled configuration without any positive-density species fails existing
validation instead of silently disabling the mechanism.

Execution requires a named evaluator and a nonempty JSON `workflow_context`
declaring the physics, engine configuration, solver settings, initial-state and
protocol inputs used by that evaluator. The callback receives the realized
inputs and an independent copy of those settings for every attempt, and must
construct its solver using the realized transport configuration. Arbitrary
callback closure state cannot be inferred or certified by the orchestrator;
reference studies must make their complete settings explicit. The execution
identity includes these settings, the nominal device/protocol/model, manifest
identity and runtime. Per-realization identities include execution and exact
sample/content identities. Input context is snapshotted before callback execution,
so callback mutation cannot rewrite the recorded input or affect another sample.

Every attempted sample has one ordered point with declared assignments, status
and either output or failure details. Stages are sample-domain-validation,
binding, realization-construction, workflow and serialization, retaining the
established categories. Baseline mismatch and malformed execution definitions
are study-level errors before callbacks run; realized enabled-specification
errors are isolated realization-construction failures. Optional-mechanism
failures returned by the existing transport engine remain mechanism diagnostics;
L2 does not reinterpret them as physical infeasibility or process yield.

The new schemas `model-execution-v1`, `model-realization-id-v1`,
`model-execution-point-v1` and `model-execution-result-v1` preserve nominal and
realized model evidence separately. Strict readers verify manifest/point linkage,
ordered assignments, realized model reconstruction, context hashes, counts and
result identity; JSON readers reject duplicate keys and non-finite constants.
Hashes detect content inconsistency and are not signatures or authentication.
The archives preserve device/protocol input snapshots; full result reporting
and reproducibility bundles remain L6; L4 reuses Phase K statistics rather than an implicit
conversion into an existing K result type.

Focused validation covers deterministic scalar/copula equivalence to Phase K,
authoritative restoration, mixed bindings, simultaneous updates, nominal and
callback isolation, invalid domains, all-failed populations, configuration/
binding/workflow/serialization failures, archive tampering and calibration
boundaries. A real two-FG transport test checks nominal equality with TAT enabled
and disabled, unchanged direct contribution and density-sensitive TAT rates.
These are integration checks, not the completed scientific L3 reference or a
claim of statistical tail convergence. Package version stays 1.2.0 until an
explicit development-identity bootstrap, and frozen v1 release evidence stays
unchanged.

## L3 controlled TAT-density reference

`examples/phase_l3_tat_density_variability.py` implements the first density-only
scientific reference. It reuses the J5 two-FG stack with 1 nm inter-FG SiO2 and
the J5 assumed trap parameters: 0.18 eV conduction-band depth, midpoint position,
8e22 m^-3 nominal volume density, 2e-20 m^2 capture cross section and 2e11 Hz
attempt frequency. The explicit image-force correction uses relative
permittivity 3.9. The direct transport configuration uses attempt frequency
1e13 Hz, 0.25 eV barrier and a 0.05 per-step transfer cap. These are controlled
reference numbers, not calibrated defect properties or process statistics.

The stochastic density distribution is lognormal with **median** 8e22 m^-3
and geometric standard deviation 1.25; the median is not the arithmetic mean.
Sixteen realizations use PCG64 seed 2029 and physical domain density >= 0.
Capture cross section, trap energy, position, attempt frequency, device,
image-force configuration and electrical settings remain fixed.

The primary observable is the initial forward TAT rate in Hz. Initial direct
and total forward rates and signed inter-FG fluxes are also retained. The
secondary numerical exercise is closed inter-FG redistribution at fixed gate
voltage 4 V: FG1 starts in P1=1 and FG2 in P0=1, and a FieldSolver1D profile
constructed with zero supplied sheet charges is held fixed. This does not run
substrate injection/emission kinetics or refresh electrostatics self-consistently,
and must not be described as a full device-retention prediction.

Total redistribution time is 4e-14 s. The declared practical grid has 16 steps
(dt=2.5e-15 s). A refinement audit uses 4, 8, 16 and 32 steps at the nominal,
minimum sampled and maximum sampled density, comparing final occupations to
the 32-step reference. Predeclared acceptance is maximum absolute occupation
delta <= 1e-3 for the selected grid, no selected-grid transfer-cap activation,
and maximum relative electron-conservation error <= 1e-12. The finite refined
grid is a comparison reference, not an exact-solution error bound.

Controls retain an independently constructed nominal solve, a one-member
constant-density ensemble and sixteen disabled-TAT realizations with exactly
paired physical density values. All solver attempts must succeed; an optional
mechanism FAILED diagnostic is explicitly raised as a workflow failure rather
than silently accepting an incomplete mechanism result. Zero variation matches
the nominal output exactly, direct transport remains unchanged, and disabled
TAT produces zero TAT rates. Sampled density changes the initial TAT rate
monotonically; the dilute reference is approximately linear in density.

In the validated reference, the nominal forward direct rate is about
8.545e12 Hz and the forward TAT rate is about 1.033e5 Hz. The selected-grid
occupation difference from the finer grid is about 6.61e-4. The observed
sampled occupation span is smaller than this refinement difference; no
numerically resolved dynamic population spread is claimed. Density variability
is demonstrated through the mechanism-resolved initial rate, while the dynamic
run verifies integration and conservation. Sixteen samples do not establish
converged tails, and density/capture-cross-section confounding prevents this
density-only study from establishing independent experimental identifiability.

Run the reference from an environment with the package available:

```shell
python examples/phase_l3_tat_density_variability.py --output results/l3-density
```

The new directory contains `reference.json`, including full manifest/execution
evidence, controls, refinement outputs, units, settings, interpretation limits
and a derived reference hash. Existing targets are never overwritten. This is
a reference evidence file, not the complete L6 report bundle; generic population
statistics and failure/feasibility analysis are provided by L4 below. Focused tests check the
J5 parameter baseline, repeatability, strict nested L2 restoration, nominal and
disabled limits, monotonic rate response, conservation, numerical acceptance,
deliberate workflow failure and no-overwrite export behavior.


## L4 population analysis and failure accounting

The provisional module `ncmemsim.ensemble.model_analysis` provides
`analyze_model_execution` and `ModelPopulationAnalysis`. Analysis consumes a
stored `ModelExecutionResult`; it does not draw samples or rerun physics.
It reuses Phase K metric, constraint, statistics and nominal-reference contracts
and the population-statistics kernel without converting MODEL archives into K
archives. Existing package exports and historical release contracts stay intact.

Every attempted realization retains its identity. Execution failures preserve
the original stage, category and error. Missing, nonnumeric, nonfinite or inexact
integer metrics become metric-extraction failures. A realization is assessed
only when every requested metric is valid; partial metric sets are excluded
from every summary. Assessed realizations are feasible or infeasible according
to all declared constraints, including equality at the threshold. Without
constraints, every assessed realization is feasible.

Statistics include **all assessed complete cases**, including infeasible ones.
Each metric retains its denominator and ordered source realization/sample IDs.
Mean, minimum, maximum, median, population variance and standard deviation use
Phase K semantics (ddof=0); quantiles use linear interpolation at (n-1)*p.
A singleton has zero variance. An empty assessed population has denominator
zero and null statistics, including quantiles. Aggregate overflow is rejected.

Counts distinguish attempted, assessed, feasible, infeasible, execution failures
and metric failures. Failure stages are counted explicitly. Each fraction stores
its numerator and denominator:

| Fraction | Numerator | Denominator |
| --- | --- | --- |
| Coverage | Assessed | Attempted |
| Simulated pass | Feasible | Attempted |
| Ensemble feasibility | Feasible | Assessed |
| Failure | All failures | Attempted |

A zero denominator produces null, never a fabricated success fraction.
Nominal comparisons require explicit metric/unit-matched
`NominalMetricReference` values; the first realization is never inferred as
nominal. Mean and median deltas retain the assessed denominator. Neither these
fractions nor descriptive population variance establishes measured process
yield, sampling uncertainty, calibration or converged tails.

```python
from ncmemsim.dtco import MetricAnalysisSpec, MetricDefinition
from ncmemsim.ensemble import NominalMetricReference
from ncmemsim.ensemble.model_analysis import analyze_model_execution
from ncmemsim.ensemble.model_execution import ModelExecutionResult
from examples.phase_l3_tat_density_variability import run_reference

evidence = run_reference()
source = ModelExecutionResult.from_dict(evidence["execution"])
metrics = MetricAnalysisSpec(
    "L3 initial TAT rate", (MetricDefinition("tat_rate", ("initial_tat_rate_Hz",), "Hz"),)
)
analysis = analyze_model_execution(
    source, metrics,
    nominal_references=(NominalMetricReference(
        "tat_rate", "Hz", evidence["nominal"]["initial_tat_rate_Hz"]
    ),),
)
assert analysis.counts["assessed_count"] == 16
assert analysis.to_dict()["statistics"][0]["denominator"] == 16
```

The separately versioned `model-population-analysis-v1` envelope includes the
full execution source, definitions, runtime, identities and derived results.
Restoration verifies the nested source and recomputes all analysis values;
changing counts, denominators, statistics or assessment records is rejected
even if the outer hash is recomputed. Strict JSON rejects duplicate keys and
nonfinite constants. This is an analysis archive; complete report bundles and
export orchestration remain L6. The L3 finding that occupation spread is below
the refinement difference is unchanged. L5 implements explicitly linked variability-aware DTCO objectives and eligibility
below; L6 report bundles are implemented and L7 release gates are next.


## L5 explicitly linked MODEL DTCO

The provisional `ncmemsim.ensemble.model_dtco` module links a `SweepPoint` to
its `ModelPopulationAnalysis` through `ModelDTCOStudy`. The execution must
already declare the exact point dictionary in `workflow_context["dtco_design_point"]`;
a missing or different declaration is rejected. This is an explicit execution
link, not an automatic design applier: evaluators remain responsible for applying
the declared design. The real reference uses the existing device-binding applier
and verifies candidate geometry and baseline hashes.

`evaluate_model_scalar` reuses `EnsembleScalarDefinition` and
`EnsembleScalarKind`: mean, population standard deviation, extrema, median,
previously declared quantiles, coverage, simulated pass, ensemble feasibility
and failure fractions. Every projection preserves its source denominator and
analysis identity. Missing metric/unit or undeclared quantile is an error;
zero-assessed statistics remain undefined, not zero.

`evaluate_model_eligibility` reuses `EnsembleConstraint`. Inclusive bounds return
eligible, ineligible or unevaluable, with unevaluable taking precedence over
violations. No automatic coverage or failure policy is invented: callers must
declare it. An unconstrained study is eligible, but undefined objectives still
exclude it from ranking.

`analyze_model_pareto` reuses `EnsembleObjective` with explicit minimization or
maximization. Only eligible studies with defined objective values are ranked.
Every supplied design is retained with objective projections, eligibility,
exclusion reason and rank. Exact dominance requires no-worse values on every
objective and a strict improvement on at least one; ties share a front in source
order. No tolerances, weighting or hidden scalarization are introduced.
Duplicate points/experiment-index identities, mixed experiments and inconsistent
metric, statistics, evaluator or eligibility definitions are rejected. Full
source/model/distribution/workflow provenance is retained; identical definitions
do not themselves establish experimental comparability or measured uncertainty.
Existing Phase K DTCO types and stable package exports remain unchanged.

Run the real synthetic reference:

```shell
python examples/phase_l5_model_dtco_reference.py --output results/l5-model-dtco
```

It applies inter-FG SiO2 thickness designs 1.0, 1.1 and 1.2 nm to cloned J5/L3
devices using the deterministic DTCO binding applier. Each design executes 16
paired density values from the L3 assumed lognormal distribution, PCG64 seed
2029. Device identity is rebuilt per candidate; trap energy, capture cross
section, image-force correction and workflow settings remain as in L3.
Independent nominal solves provide explicit TAT-rate references. A 16/32-step
comparison at nominal and sampled density extremes requires occupation delta
<= 1e-3 and no selected-grid transfer-cap activation for every candidate.
Electron-conservation and no-clamp metrics use thresholds 1e-12 and zero;
DTCO eligibility explicitly requires full coverage and simulated pass fraction
one. The two illustrative objectives maximize mean initial TAT rate and minimize
its population standard deviation. They describe a declared synthetic tradeoff,
not a recommendation for a calibrated memory-device optimum.

All three designs belong to the first front in the validated reference. The
export retains experiment, complete MODEL populations, eligibility, objectives,
fronts, source identities, numerical audit and scientific limitations; existing
targets are never overwritten. The L6 reader and bundle builder below restore this reference export without
rerunning the simulation. Sixteen paired realizations do not
establish converged tails or sampling uncertainty. Dynamic occupation spread is
not claimed resolved; fixed-field redistribution is not full device retention.

The shared Phase K linear-quantile kernel also preserves equal interpolation
endpoints exactly. This avoids floating-point roundoff outside the range of a
constant population without changing the quantile definition or archive schemas.
Focused tests cover this correction, scalar units/denominators, undefined values,
strict design linkage, inclusivity, eligibility precedence, exclusions, exact
fronts and ties, actual candidate geometry, paired sampling and export safeguards.


## L6 authoritative MODEL reports and reproducibility bundles

`ModelDTCOStudy.from_dict`, `ModelEligibilityResult.from_dict` and
`ModelParetoAnalysis.from_dict/from_json` restore L5 payloads strictly. They
restore nested L4/L2 sources and rebuild scalar projections, constraint results,
exclusion reasons, counts, ranks and front ordering. Unknown fields/versions,
source/design mismatches and derived tampering are rejected even if the outer
hash is recalculated. Existing L5 schemas are retained; existing Phase K readers
and stable exports do not acquire MODEL data.

The provisional `ncmemsim.ensemble.model_reporting` module provides
`ModelReportStudy`, `ModelReport`, `build_model_report`, `write_model_report` and
`load_model_report_bundle`. A study retains its complete population and optional
DTCO eligibility. A report can contain standalone populations, all-failed or
mixed populations, and a linked Pareto analysis. If present, Pareto sources must
match the ordered DTCO report studies exactly; excluded designs remain present.
Names are unique, source/population identities match, and JSON snapshots own
supplemental evidence without mutable caller dictionaries.

The authoritative `model-report-v1` JSON retains all attempted samples and
assignments, nominal/realized contexts, model/distribution/dependence definitions,
workflow settings, runtime, outputs, metrics, failure stages, exact denominators,
nominal references and design/objective identities. Supplemental evidence can
retain experiment definitions, numerical audits and interpretation limits.
Supplemental declarations are archived under the report hash; their physical
claims are not independently recomputed by the reader. Hashes and consistency
checks do not replace provenance or experimental calibration.

A new export directory contains six deterministic UTF-8 files:

| File | Contents |
| --- | --- |
| `report.json` | Authoritative report and all nested source evidence |
| `report.md` | Population counts, DTCO eligibility/exclusions/ranks, interpretation limits |
| `attempts.csv` | Every attempt, assignments, metric values, constraints and failure details |
| `statistics.csv` | Metric units, cohort IDs, denominators, population statistics, fractions and nominal comparisons |
| `designs.csv` | Every Pareto design, assignments, eligibility, exclusions, ranks and objective projections |
| `bundle.json` | Bundle schema, report identity and SHA-256 digests of the five content files |

`write_model_report` validates before writing and refuses an existing target,
including an empty directory or existing file. Exclusive creation protects
individual output files. A failed write removes only files created by that
export. No report creation timestamp or automatic runtime refresh is inserted;
original execution provenance stays authoritative.

`load_model_report_bundle` accepts only the exact ordinary-file set, verifies
manifest identity and restores strict JSON, then regenerates every content file
and compares its bytes. Rehashed altered CSV or Markdown projections are still
rejected. Missing/extra files, symlinks and traversal-like manifest entries are
rejected. Restoring and re-exporting a valid report yields identical content
and bundle bytes without sample generation or workflow execution. Zero-assessed
statistics retain zero denominators and null values; CSV leaves those undefined
scalar cells empty rather than substituting zero.

The runnable reference consumes an existing L5 archive:

```shell
python examples/phase_l6_model_report.py --input results/l5-model-dtco/reference.json --output results/l6-model-report
```

It verifies the L5 reference identity and experiment linkage, restores all three
designs and 48 attempts, and carries the timestep audit and scientific limits
into the bundle. It does not rerun L3/L5 physics. The assumed distribution,
finite-sample tail limitations, unresolved dynamic occupation spread and
fixed-field retention limitation remain unchanged.

Focused tests cover nested restoration, rehashed derived tampering, exact
report/Pareto linkage, duplicate/nonfinite JSON, all-failed and mixed accounting,
deterministic exports, rehashed projection tampering, bundle structure,
no-overwrite behavior, interrupted-write cleanup and restoration without physics
or sampling. L7 remains the compatibility, clean-distribution, supported-Python
CI and exact-commit release gate; L6 alone does not approve v1.3.0 release.
