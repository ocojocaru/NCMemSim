# Stochastic nanocrystal ensembles and device variability

## Status and purpose

This page defines the Phase K development contract for NCMemSim v1.2.0.

Phase K begins from the immutable `v1.1.0` release and extends the stable NCMemSim scientific platform with reproducible stochastic nanocrystal ensembles and device-level variability analysis. The approved v1 public API, the v1.1.0 transport baseline, existing archive readers, deterministic DTCO, Robust DTCO, calibration workflows, and scientific provenance rules remain the compatibility baseline.

Phase K does not replace the deterministic simulator. It introduces an explicitly configured layer that generates parameter realizations, applies them to an existing nominal study, executes the existing NCMemSim workflows, and summarizes the resulting population while preserving every realization's provenance and failure state.

The governing invariant is:

> **Zero-variation invariant:** an ensemble in which every stochastic variation has zero amplitude must reproduce the corresponding nominal NCMemSim v1.1.0 calculation within the exact or declared numerical tolerance of that workflow.

No Phase K feature may silently introduce randomness into an existing deterministic call.

---

## Scientific objective

The objective of Phase K is to represent controlled variability in nanocrystal-memory simulations without conflating numerical sampling with fabricated-device statistics.

A study should be able to define a nominal NCMemSim device or workflow together with explicit distributions for selected physical or effective parameters, generate a reproducible ensemble of realizations, execute the existing electrical, optical, retention, transport, DTCO, or Robust-DTCO workflow for each realization, and report population-level metrics.

Initial use cases include variability in:

- nanocrystal diameter;
- nanocrystal volume fraction;
- electrically active nanocrystal fraction;
- GeSn composition;
- dielectric or floating-gate layer thickness;
- trap density;
- trap energy;
- transport barrier parameters;
- attempt frequency;
- photo-capture efficiency;
- selected operating parameters when explicitly declared as stochastic study variables.

Phase K is intended for compact-model variability studies. A simulated population is not, by itself, a manufacturing population.

The first v1.2.0 implementation therefore uses terms such as:

- `ensemble`;
- `realization`;
- `simulated pass fraction`;
- `ensemble feasibility fraction`;
- `population statistic`.

It must not describe such quantities as measured manufacturing yield unless an independent experimental/process-calibration contract has been established.

---

## K0.1 Scientific scope and non-goals

Phase K shall provide:

1. immutable stochastic-variable specifications;
2. explicit probability-distribution contracts;
3. deterministic seeded ensemble generation;
4. controlled correlations between stochastic variables;
5. reproducible realization identifiers and manifests;
6. application of realizations to existing NCMemSim inputs through explicit bindings;
7. isolated execution and failure accounting for each realization;
8. population statistics and percentile summaries;
9. nominal-versus-ensemble comparison;
10. variability-aware DTCO metrics;
11. integrity-checked serialization and reporting;
12. reproducible scientific reference studies.

The initial v1.2.0 scope explicitly excludes:

- kinetic Monte Carlo of individual electron trajectories;
- atomistic defect generation;
- three-dimensional stochastic percolation;
- spatial point-process placement of individual nanocrystals unless introduced by a later reviewed contract;
- wafer-scale process simulation;
- experimentally inferred manufacturing-yield prediction;
- Bayesian optimization;
- evolutionary optimization;
- machine-learned surrogate models;
- neural-network compact models;
- TCAD co-simulation;
- neuromorphic learning rules;
- automatic inference of probability distributions from experimental populations.

These remain possible later extensions.

---

## K0.2 Frozen v1.1.0 compatibility boundary

Phase K must preserve the stable behavior of NCMemSim v1.1.0.

The following rules are mandatory:

- existing public imports remain valid according to the v1 compatibility policy;
- deterministic workflows remain deterministic;
- existing default parameter values are unchanged unless independently justified outside Phase K;
- stochastic behavior is opt-in only;
- no global random state may alter an existing simulation;
- the direct and advanced transport mechanisms introduced before v1.2.0 retain their equations and defaults;
- existing DTCO and Robust DTCO result semantics remain valid;
- published archive fixtures remain readable;
- historical evidence files retain their historical meaning;
- synthetic ensemble studies must not be promoted to experimental calibration;
- a zero-variation realization must reduce to the underlying nominal configuration;
- a one-member zero-variation ensemble must reproduce its nominal workflow result.

An additive Phase K API may extend the v1 line, but removal or reinterpretation of an approved v1 path is outside the v1.2.0 scope.

---

## K0.3 Ensemble, sample and realization semantics

Phase K uses three distinct concepts.

### Ensemble

An `ensemble` is the complete statistical experiment definition.

It contains, at minimum:

- the ensemble size;
- random-generation specification;
- stochastic-variable definitions;
- distribution parameters;
- correlation specification where present;
- binding targets;
- nominal-context identifier;
- ordering rules;
- provenance;
- serialization schema;
- integrity hash.

An ensemble specification does not itself contain simulator outputs.

### Sample

A `sample` is one deterministic draw from the ensemble sampling contract before it is applied to a nominal NCMemSim configuration.

A sample records:

- its stable index;
- sample identifier;
- generated values;
- canonical units;
- the stochastic-variable identities from which the values originated;
- generator/seed provenance;
- a deterministic hash.

Sampling and device construction remain conceptually separate.

### Realization

A `realization` is the fully instantiated NCMemSim study obtained by applying one sample to the declared nominal context through explicit bindings.

A realization records enough provenance to answer:

- which nominal configuration was used;
- which sample was applied;
- which values changed;
- which values remained nominal;
- which bindings were executed;
- whether construction succeeded;
- which exact realized configuration was executed.

A failed realization is still part of the ensemble accounting.

---

## K0.4 Stochastic-variable and distribution ownership

Every stochastic variable must have an explicit owner and binding target.

A variable specification must eventually define at least:

- stable variable name;
- target binding;
- canonical unit;
- distribution type;
- distribution parameters;
- allowed physical domain;
- nominal value or nominal-value source;
- provenance/status;
- applicability statement.

The initial serializable distribution family implemented in K1 is:

- constant;
- normal;
- truncated normal;
- uniform;
- log-normal;
- finite discrete.

Distribution semantics must be mathematical and explicit. For example, a log-normal contract must state whether supplied parameters describe the underlying normal distribution or the physical-space mean and spread.

No public low-level distribution contract may rely on undocumented library defaults.

Arbitrary user callbacks are outside the initial serializable K1 distribution contract.

### Sample-domain policy

A mathematically valid distribution and the physical domain of the bound
parameter are separate contracts.

A generated value outside the declared physical domain is an invalid sample
value for that realization. The initial Phase K implementation must not
silently clip, cap, reflect, replace, or resample such a value.

If a study requires every generated value to remain inside a physical domain,
the study must use a distribution whose support is explicitly bounded for that
purpose, such as a truncated-normal or uniform distribution.

Any future rejection/resampling policy must be explicit in the ensemble
specification because it changes the effective sampled distribution and the
reproducibility contract.

Out-of-domain samples retain their sample identity and remain part of attempted
ensemble accounting. They fail before simulator execution with an explicit
sample-domain-validation failure.

---

## K0.5 Canonical units

Phase K inherits the canonical unit of an existing stable NCMemSim binding
whenever that binding is reused.

The stochastic layer must not redefine an existing binding's unit merely to
enforce a separate SI convention. This preserves the v1 compatibility
boundary and prevents a second incompatible parameter-binding system.

For the existing executable DTCO bindings, the Phase K units therefore include:

| Quantity | Stable binding unit |
|---|---:|
| gate work function | eV |
| substrate doping | m^-3 |
| temperature | K |
| layer thickness | nm |
| nanocrystal diameter | nm |
| nanocrystal volume fraction | 1 |
| electrically active fraction | 1 |
| GeSn Sn fraction | 1 |
| program/read voltage | V |
| programming time | s |
| internal timestep | s |
| optical wavelength | nm |
| optical power density | W/m^2 |

For a parameter that does not yet have a stable executable binding, its unit
must be fixed explicitly when that binding is introduced. Such new bindings
should follow the unit contract of the underlying NCMemSim physics model; for
example, the existing advanced-transport contracts use joules for trap and
barrier energies.

A stochastic distribution and its physical-domain bounds use the same unit as
the variable's binding.

Convenience units may only be introduced through named conversion helpers.

There shall be no implicit nm/m, eV/J, cm^-3/m^-3, percentage/fraction, or
wavelength-unit conversion in a low-level stochastic contract. A value is
interpreted only in the explicit unit recorded by its binding and stochastic
variable definition.

A distribution parameter such as arithmetic standard deviation has the same
physical unit as its corresponding variable unless its mathematical definition
explicitly makes it dimensionless.

---

## K0.6 Randomness and reproducibility contract

Randomness in Phase K must be local, explicit and reproducible.

The following rules apply:

- every stochastic ensemble has an explicit seed or an explicitly recorded generated seed;
- no Phase K implementation may depend on Python's process-global random state;
- no existing NCMemSim deterministic workflow may consume Phase K random numbers implicitly;
- the random-number generator family/algorithm must be recorded;
- sample ordering must be deterministic;
- stochastic-variable ordering must be deterministic;
- the ensemble manifest must contain enough information to reconstruct or verify the generated sample table;
- generated sample values must have a deterministic canonical representation and integrity hash;
- rerunning the same supported sampling contract with the same inputs must reproduce the same ordered sample table;
- changing only reporting order must not alter generated values.

The first implementation should use one explicitly selected NumPy `Generator`/bit-generator contract rather than an unspecified library default. The selected algorithm becomes part of the K2 reproducibility contract.

For long-term archival reproducibility, the generated canonical sample values and their hash are the authoritative evidence. Reproduction must therefore not depend solely on a seed if a future numerical-library implementation changes.

---

## K0.7 Correlation contract

Phase K distinguishes independent sampling from explicitly correlated sampling.

Independence is the default.

Correlation may only be introduced by an explicit correlation specification that identifies:

- the participating stochastic variables;
- their stable ordering;
- the correlation representation;
- validation rules;
- provenance;
- deterministic hash.

The initial K2 target is a matrix-based correlation contract for compatible continuous variables.

The initial matrix-based implementation uses a Gaussian-copula
representation. Matrix entries therefore represent Pearson correlation
coefficients between latent standard-normal variables, not necessarily
Pearson correlations between the resulting physical-space stochastic
parameters.

For affine normal marginals, latent and physical-space Pearson correlation
coincide. For non-normal marginals such as uniform, log-normal or truncated
normal distributions, they generally do not. Reports must preserve this
distinction and must not label the latent matrix as an experimentally measured
physical-space correlation matrix unless independent evidence supports that
interpretation.

The initial executable correlated-sampling contract is limited to compatible
continuous marginals. Constant and finite-discrete distributions are excluded
from the first Gaussian-copula implementation.

A correlation matrix must be:

- square;
- finite;
- symmetric within declared numerical tolerance;
- unit diagonal;
- dimensionally associated with the declared variable order;
- valid for the selected transformation/sampling method.

The initial K2 implementation additionally requires every matrix entry to lie
within [-1, 1] and the matrix to be positive semidefinite within the declared
numerical tolerance. Invalid matrices are rejected; they are never silently
projected, clipped or repaired.

Invalid correlation definitions must fail before ensemble execution.

Correlation is a statistical modelling assumption unless supported by experimental evidence. Reports must preserve that distinction.

Phase K will not silently infer correlations from the nominal model or from parameter names.

---

## K0.8 Device-realization and binding contract

Phase K must reuse existing NCMemSim construction and workflow APIs rather than implement a second simulator.

A realization is formed by:

1. copying or reconstructing the nominal immutable study context according to its existing contract;
2. applying the sample through reviewed parameter bindings;
3. validating the resulting physical/configuration state;
4. executing the existing workflow;
5. recording the realized inputs and outputs.

The same parameter must not be changed through two ambiguous bindings within one realization.

Structural invalidity must be detected explicitly.

Bindings should reuse existing DTCO binding semantics where their ownership and units already match. Phase K must not create a parallel incompatible naming system for the same parameter.

Parameters that do not yet have a stable executable binding remain outside executable ensemble scope until that binding is explicitly defined and tested.

---

## K0.9 Statistical metric semantics

Population statistics are computed from clearly defined sets of realizations.

At minimum, K4 is expected to support appropriate combinations of:

- attempted count;
- successful count;
- failed count;
- feasible count;
- infeasible count;
- mean;
- standard deviation;
- variance;
- minimum;
- maximum;
- median;
- requested quantiles/percentiles;
- nominal comparison;
- coverage fraction.

Every statistical result must state its denominator.

Failures must not silently disappear from a statistic.

A metric summary must distinguish, as applicable:

- all attempted realizations;
- successfully evaluated realizations;
- feasible realizations;
- infeasible realizations;
- failed realizations.

Quantile conventions must be fixed by contract and tested before K4 is considered complete.

No confidence interval may be reported unless its statistical meaning and method are explicitly implemented and documented.

---

## K0.10 Simulated pass fraction and yield boundary

Phase K may evaluate declared pass/fail criteria across an ensemble.

For example:

- memory window greater than or equal to a declared threshold;
- retention loss below a declared threshold;
- programming voltage below a declared threshold;
- combined feasibility constraints.

The resulting quantity may be called:

- `simulated_pass_fraction`; or
- `ensemble_feasibility_fraction`.

Its denominator must be explicit.

A failed simulation is not automatically equivalent to a physically failing device unless the study explicitly defines such a rule. Numerical/model failures therefore remain separately counted by default.

The terms `manufacturing yield`, `process yield`, or equivalent experimental production claims are prohibited for an uncalibrated synthetic Phase K population.

---

## K0.11 Failure accounting

Failure isolation is required at every stage.

At minimum, later implementation must distinguish:

1. ensemble-specification failure;
2. distribution-validation failure;
3. correlation-validation failure;
4. sample-generation failure;
5. sample-domain-validation failure;
6. binding failure;
7. realization-construction failure;
8. simulator/workflow failure;
9. metric-extraction failure;
10. report/export failure.

One failed realization must not invalidate unrelated realizations unless the caller explicitly selects fail-fast behavior.

A failure result must retain:

- sample/realization identity;
- failure stage;
- stable failure category;
- relevant diagnostic message;
- available provenance;
- attempted-count membership.

A disabled stochastic variable, a zero-amplitude stochastic variable, and a failed stochastic variable are three different states and must not be conflated.

---

## K0.12 Provenance, serialization and integrity

Phase K evidence must allow a population result to be traced back to its statistical and physical assumptions.

Later contracts must preserve, as applicable:

- NCMemSim version;
- nominal-context hash;
- ensemble-specification hash;
- variable specifications;
- distribution parameters;
- correlation specification;
- generator algorithm;
- seed;
- ordered sample table or authoritative sample-table hash;
- realization bindings;
- successful and failed realization identities;
- workflow/result hashes;
- metric definitions;
- report schema version.

Serialization must use strict finite values where JSON requires them.

Unknown fields, duplicate semantic identifiers, incompatible schema versions, non-finite stochastic parameters, and integrity-hash mismatches must fail explicitly.

A regenerated ensemble whose sample-table hash differs from its archived authoritative hash must not be presented as the same ensemble evidence.

---

## K0.13 DTCO and Robust-DTCO integration boundary

Phase K must compose with the existing design-space architecture rather than replace it.

Deterministic DTCO continues to answer:

> How does the nominal model behave across a declared design space?

Robust DTCO continues to answer questions defined by its existing bounded-variation contract.

Phase K adds explicit stochastic-population evaluation with probability-distribution semantics and reproducible population draws.

Variability-aware DTCO may expose metrics such as:

- lower-percentile memory window;
- upper-percentile retention loss;
- median programming voltage;
- simulated failure fraction;
- ensemble feasibility fraction.

Example future objectives include:

- maximize `P05(memory_window)`;
- minimize `P95(retention_loss)`;
- minimize nominal or population programming voltage.

Pareto analysis remains transparent. Phase K must not collapse multiple stochastic objectives into an undocumented scalar optimum.

Existing Robust-DTCO semantics must not be silently redefined as stochastic ensemble semantics. Any bridge between the two systems must be explicit.

---

## K0.14 Validation ladder

Phase K development follows a layered validation strategy.

### Contract-level tests

Verify:

- immutable specifications;
- units;
- finite-value rules;
- bounds;
- distribution semantics;
- serialization;
- hashing;
- equality/ordering where part of the public contract.

### Analytic distribution tests

Where possible, verify generated or transformed values against analytically controlled cases and exact limiting behavior.

### Reproducibility tests

Verify:

- same contract + same seed -> same ordered sample table;
- stable sample identifiers;
- stable hashes;
- serialization round trips;
- zero-variation identity.

### Correlation tests

Verify:

- independent limit;
- matrix validation;
- deterministic transformed draws;
- declared ordering;
- controlled synthetic correlation cases.

### Realization tests

Verify:

- correct parameter application;
- unchanged nominal values outside the declared bindings;
- physical-domain validation;
- one-sample failure isolation.

### Simulator integration tests

Verify representative:

- electrical programming;
- electro-optical programming;
- retention;
- advanced transport;
- DTCO execution.

### Statistical-result tests

Verify counts, denominators, quantiles, failure treatment, feasibility fractions and nominal comparison on small exactly controlled datasets.

### End-to-end scientific references

At least three reference studies are planned:

1. nanocrystal-diameter variability;
2. trap/disorder variability using the v1.1 transport framework;
3. multi-parameter variability-aware DTCO.

### Release validation

The final K7 release gate must include:

- v1 API/result compatibility review;
- complete regression suite;
- strict documentation audit;
- deterministic ensemble reproducibility checks;
- clean wheel and source-distribution validation;
- supported Python CI;
- exact-commit branch validation;
- exact-commit `main` validation;
- tag CI;
- automated GitHub Release validation.

---

## Planned Phase K delivery sequence

### K0 — Scope and architecture freeze

Define scientific scope, compatibility boundary, terminology, units, stochastic ownership, reproducibility, correlation, realization, statistics, failure, provenance, DTCO integration and validation contracts.

No stochastic simulator execution is introduced in K0.

### K1 — Stochastic variable and distribution contracts (complete)

Implemented immutable serializable variable and distribution specifications with canonical units, physical domains, provenance and deterministic hashes.

Implemented initial distributions:

- constant;
- normal;
- truncated normal;
- uniform;
- log-normal;
- finite discrete.

K1 also establishes strict round-trip deserialization for distribution,
physical-domain, stochastic-variable and ensemble-specification contracts,
including reconstruction of existing parameter-binding and provenance
identities without modifying the v1 contracts.

K1 does not execute simulator ensembles.

### K2 — Reproducible ensemble generation and correlations (complete)

K2 implements deterministic seeded ensemble sampling with an explicit local
NumPy `Generator`/PCG64 contract, stable sample identities, authoritative
sample manifests and sample-table hashes, strict archival serialization, and
deterministic sample-major/declared-variable-order generation.

Independent scalar sampling uses an explicitly versioned algorithm rather than
NumPy distribution helpers. Correlated sampling uses the Gaussian-copula
contract defined above, with latent standard-normal Pearson correlations,
deterministic sequential PSD factorization, explicit marginal transforms, and
no silent matrix repair.

The executable Gaussian-copula path supports compatible normal, truncated
normal, uniform and log-normal marginals. Constant and finite-discrete
variables may remain in the same ensemble when they are outside the correlated
subset.

Deterministic statistical validation confirms the expected physical-space
Pearson behavior for affine normal marginals and the Gaussian-copula Spearman
relation for nonlinear monotonic marginals. The latent correlation matrix is
not reinterpreted as a physical-space Pearson matrix for nonlinear marginals.

The generated canonical sample table and its integrity hash remain the
authoritative archival evidence; seed-only regeneration is not treated as
sufficient long-term evidence.

### K3 — Ensemble realization and simulation execution (complete)

Apply samples through reviewed bindings to nominal contexts and execute existing NCMemSim workflows with realization-local failure isolation.

No duplicate simulator physics is introduced.

K3 is complete. The implemented contracts provide:

- sample-domain validation and stable realization identity before application;
- realization construction through the existing reviewed device and operating binding helpers;
- exact manifest-order serial execution without resampling;
- realized device and operating context snapshots with integrity hashes;
- isolated failures for sample-domain validation, binding application, realization construction, workflow execution and output serialization;
- stable failure stage/category pairs while preserving realization identity and attempted-sample membership.

Aggregate population statistics, feasibility accounting, nominal comparisons, percentiles and simulated pass fractions begin in K4 rather than K3.

### K4 — Statistical device and reliability metrics

Add population summaries, percentiles, nominal comparisons, explicit denominators, feasibility accounting and simulated pass fractions.

K4 is implemented in three ordered subphases:

**Status: K4 complete; K5 next.**

- **K4a - per-realization metric assessment (complete):** extract declared scalar metrics from successful K3 outputs without rerunning physics, apply declared constraints, preserve complete-case semantics, propagate K3 failures unchanged, and distinguish metric-extraction failures explicitly;
- **K4b - population statistics (complete):** report attempted, assessed, feasible, infeasible and failed counts with explicit denominators; compute complete-case population mean, variance, standard deviation, minimum, maximum, median and requested quantiles using population `ddof=0` and linear `(n - 1) q` interpolation; report coverage as assessed count divided by attempted count;

K4b uses an ensemble-specific statistics contract over the immutable K4a result. Requested quantiles are finite unique probabilities in `[0, 1]`. Metric summaries use all assessed complete cases only and record their denominator, sample indices and realization identities. Population variance and standard deviation use `ddof=0`; quantiles use linear `(n - 1) q` interpolation. When no realization is assessed, scalar summary values and quantile values are `None` with denominator zero. Failed realizations remain in attempted and failed counts and are never silently removed from coverage accounting. K4b does not compute nominal comparisons or feasibility/pass fractions; those remain K4c.

The implemented K4b API provides `EnsembleStatisticsSpec`, `MetricPopulationSummary`, `EnsemblePopulationStatistics` and `summarize_ensemble_metrics()`. Statistics are derived from the immutable K4a result without rerunning physics, include runtime/algorithm provenance, preserve declared metric and realization ordering, fail closed on non-finite derived statistics, and treat both propagated K3 failures and K4a metric-extraction failures as failed attempted realizations rather than assessed complete cases.
- **K4c - nominal comparison and feasibility fractions (complete):** compare ensemble metrics with declared nominal references and report explicit all-attempted and assessed-only feasibility fractions while keeping numerical/model failures distinct from physical pass/fail outcomes.

K4c uses explicit declared nominal metric references; nominal values are never inferred from the ensemble population. The all-attempted `simulated_pass_fraction` is feasible count divided by attempted count. The assessed-only `ensemble_feasibility_fraction` is feasible count divided by assessed count and is `None` when no realization is assessed. `failure_fraction` is failed count divided by attempted count. Failed realizations remain distinct from physically infeasible realizations and are not automatically counted as physical failures. For each declared nominal metric reference, K4c reports the nominal value together with complete-case population mean and median deltas relative to that nominal value; when the assessed denominator is zero, nominal-comparison deltas are `None`. Manufacturing-yield terminology remains prohibited for uncalibrated synthetic ensembles.

The implemented K4c API provides `NominalMetricReference`, `NominalMetricComparison`, `EnsembleFeasibilitySummary` and `summarize_ensemble_feasibility()`. It consumes immutable K4b population statistics without rerunning physics, preserves explicit declared nominal references and their units, reports all fractions with explicit numerators and denominators, records runtime/algorithm provenance, fails closed on non-finite nominal deltas, and permits feasibility accounting without nominal references rather than inferring them from the ensemble.

For K4, `attempted_count` is the number of K3 realization execution points. `assessed_count` is the number of realizations with complete successfully extracted metric sets and therefore equals `feasible_count + infeasible_count`. `failed_count` includes both propagated K3 execution failures and K4 metric-extraction failures. No failed realization is silently removed from denominator accounting.

Manufacturing-yield claims remain outside scope.

K4 is complete: per-realization assessment, complete-case population statistics, explicit failure accounting, nominal comparisons and feasibility fractions are now implemented as separate ordered analysis layers over immutable upstream results.

### K5 — Variability-aware DTCO

Expose ensemble-derived objectives and constraints to the existing transparent Pareto/DTCO framework while keeping deterministic DTCO and Robust DTCO semantics distinct.

**Status: K5 complete; K6 next.**

K5 composes with the existing DTCO design-space architecture but defines a distinct Phase-K analysis layer. Each K5 study links one explicit existing DTCO design-point identity and assignments to one immutable `EnsembleFeasibilitySummary`; design identity must not be inferred from device hashes or ensemble names. K5 never resamples, reruns K3/K4 physics, mutates source results, or converts a Phase-K ensemble result into a Robust-DTCO result.

K5 is implemented in three ordered subphases:

- **K5a - ensemble-derived scalar definitions and DTCO study linkage - COMPLETE:** define typed scalar selectors over immutable K4 results and explicit links to existing DTCO design points;

K5a scalar evaluation is a read-only projection of one immutable `EnsembleFeasibilitySummary`; it does not resample, rerun physics, recompute K4 statistics, or infer a different DTCO identity. A scalar evaluation is either `defined`, with one finite Python-float value, or `undefined`, with `value=None`. Undefined is an evaluability state and must not be interpreted as physical infeasibility.

For metric-derived selectors, the declared metric name and unit must match the K4 population summary exactly. Mean, standard deviation, minimum, maximum, and median are read directly from the corresponding `MetricPopulationSummary`. Quantiles may only select probabilities already declared and computed by the source `EnsembleStatisticsSpec`; K5 must not interpolate or otherwise synthesize undeclared quantiles. A present metric summary with zero denominator therefore evaluates as undefined, while an absent metric, unit mismatch, or undeclared quantile is a contract error rather than an undefined value.

The population-level fractions are read directly from K4: `coverage_fraction` from K4b, and `simulated_pass_fraction`, `ensemble_feasibility_fraction`, and `failure_fraction` from K4c. `ensemble_feasibility_fraction` is undefined when no realizations were assessed; the other declared fractions remain defined according to their K4 denominators. K5a does not introduce objective direction, constraints, Pareto eligibility, Robust-DTCO failure policy, or manufacturing-yield semantics.

K5a is implemented by `EnsembleDTCOStudy`, `EnsembleScalarKind`, `EnsembleScalarDefinition`, `EnsembleScalarEvaluation` and `evaluate_ensemble_scalar`. The implementation links directly to the existing DTCO `SweepPoint`, preserves source K4 identity through `EnsembleFeasibilitySummary`, serializes deterministic study/definition/evaluation identities, and is exported through the public `ncmemsim.ensemble` API. K5a was completed in commits `c4562c4`, `4c5c545`, `fbdceb3` and `aef9ff7`; the extended Phase K2-K5 gate completed with 432 passing tests.
- **K5b - population-level constraints and eligibility - COMPLETE:** evaluate declared ensemble-derived constraints with explicit units and distinguish constraint infeasibility from undefined or unavailable source quantities;

K5b reuses the existing DTCO `ConstraintOperator` exactly: only inclusive `<=` and `>=` comparisons are supported. K5b does not reuse deterministic-DTCO `MetricConstraint` or `ConstraintEvaluation`, because those contracts require an available numeric metric value and cannot represent an undefined ensemble-derived scalar. No unit conversion is performed: every K5 constraint declares a unit that must match its selected `EnsembleScalarDefinition` exactly, and every threshold is a finite numeric scalar with booleans rejected.

Each K5 constraint evaluation has exactly one status: `satisfied`, `violated`, or `unevaluable`. A defined scalar is compared directly with the declared inclusive operator and threshold. An undefined scalar produces `unevaluable`; it must never be converted to a violated constraint or interpreted as physical infeasibility. Missing scalar definitions, mismatched units, or structurally incompatible definitions are contract errors rather than unevaluable numerical outcomes.

Study-level K5b eligibility has exactly three states: `eligible`, `ineligible`, or `unevaluable`. If any selected constraint is unevaluable, the study is unevaluable for that eligibility analysis. Otherwise, any violated constraint makes the study ineligible, and only a complete set of satisfied constraints makes it eligible. This precedence preserves incomplete evaluability instead of silently collapsing it into constraint infeasibility. K5b performs no resampling, physics execution, K4 recomputation, objective ranking, Pareto dominance, or Robust-DTCO failure-policy inference.

K5b is implemented by `EnsembleConstraint`, `EnsembleConstraintEvaluation`, `EnsembleEligibilityResult`, `evaluate_ensemble_constraint` and `evaluate_ensemble_eligibility`. Constraint definitions reuse the existing inclusive DTCO `ConstraintOperator`, preserve ordered evaluations and explicit source-study identity, and serialize deterministic definition, evaluation and result hashes. The implementation was completed in commits `e3dc2ce` and `6fe433b`, following the K5b contract freeze in `0fff53b`; the extended Phase K2-K5 gate completed with 452 passing tests.
- **K5c - transparent Pareto analysis - COMPLETE:** rank only eligible K5 studies using the existing `ObjectiveDirection` semantics and exact no-worse-all/strictly-better-one dominance rule, retaining ties and source order without weights, tolerances or hidden scalarization.

K5c objectives are explicit and typed. Each objective declares a unique name, one existing `EnsembleScalarDefinition`, and one existing DTCO `ObjectiveDirection`; objective direction is never inferred from the scalar kind. At least one objective is required. K5c introduces no weights, tolerances, normalization, utility function or hidden scalarization, and it does not inherit Robust-DTCO objective or failure-policy contracts.

K5c consumes an ordered collection of K5b eligibility results and retains every source study in the Pareto result. Only studies whose K5b status is `eligible` and whose selected objective scalars are all defined are ranked. A K5b `ineligible` study remains excluded as constraint-ineligible. A K5b `unevaluable` study remains excluded as constraint-unevaluable. If a K5b-eligible study has an undefined selected objective scalar, it is excluded as objective-unevaluable rather than reclassified as physically infeasible. Missing metrics, unit mismatches, undeclared quantiles or otherwise incompatible scalar definitions remain contract errors rather than exclusion states.

Dominance follows the existing deterministic DTCO rule exactly: one study dominates another only when it is no worse on every selected objective and strictly better on at least one, using exact comparisons and the declared `ObjectiveDirection`. Equal objective vectors do not dominate one another. All non-dominated ties are retained. Pareto fronts and point records preserve input study order, ranks start at zero, and excluded studies carry no rank or objective vector used for dominance.

K5c result identity is deterministic from the ordered source eligibility-result identities and the explicit ordered objective definitions. The result preserves every source study and its K5b result identity, records explicit exclusion reasons, exposes all Pareto fronts and the rank-zero Pareto set, and never reruns sampling, physics, K4 statistics or K5b eligibility.

K5c is implemented by `EnsembleObjective`, `EnsembleParetoPointResult`, `EnsembleParetoAnalysisResult` and `analyze_ensemble_pareto`. The implementation reuses the existing DTCO `ObjectiveDirection`, preserves exact no-worse-all/strictly-better-one dominance and source ordering, retains equal objective vectors as ties, distinguishes `constraint-ineligible`, `constraint-unevaluable` and `objective-unevaluable` exclusions, and validates compatibility of the selected metric and population-statistics definitions before comparison. K5c was frozen in commit `9e67aad`, implemented and tested in `9154171`, and exported through the public `ncmemsim.ensemble` API in `7ca8e69`; the extended Phase K2-K5 gate completed with 470 passing tests.

Initial K5 scalar selectors may expose complete-case metric `mean`, `standard_deviation`, `minimum`, `maximum`, `median` and a quantile whose probability was explicitly computed by K4b, together with `coverage_fraction`, `simulated_pass_fraction`, `ensemble_feasibility_fraction` and `failure_fraction`. Metric-derived selectors inherit the declared metric unit; fraction selectors use unit `1`. K4b population variance remains reportable but is not initially eligible as a K5 objective or constraint because squared-unit semantics are not yet defined.

K5 objective and constraint definitions must be explicit and typed. Objective direction reuses the existing DTCO `ObjectiveDirection`; constraint comparison reuses the existing `ConstraintOperator`. No Robust-DTCO failure policy is inherited. If a user wants numerical/model failure to affect design eligibility, `failure_fraction` must be declared explicitly as a K5 constraint. An undefined selected quantity, including an assessed-only fraction when `assessed_count == 0` or a population statistic with denominator zero, makes that K5 study unevaluable for the affected analysis rather than physically infeasible.

Studies compared in one K5 analysis must use compatible declared metric and population-statistics definitions for every selected quantity. K5 preserves every source study and its source-result identity, records explicit exclusion reasons, and includes ordered source hashes and analysis definitions in deterministic result identity. Manufacturing-yield terminology remains prohibited for uncalibrated synthetic ensembles.

### K6 — Scientific reference studies and reproducible reports

**Status: K6 architecture defined; K6a next.**

Provide controlled end-to-end examples, integrity-checked ensemble manifests, population summaries, failure accounting, plots/exports and interpretation limits.

K6 is divided into three ordered subphases:

- **K6a - ensemble reporting and integrity bundle:** define an immutable Phase-K report snapshot with canonical JSON identity, exact source-result linkage, integrity validation, portable CSV/Markdown artifacts, round-trip reconstruction and tamper detection. Writers must refuse existing target files before writing. Optional plots remain outside the report hash.
- **K6b - controlled single-parameter reference studies:** provide reproducible nanocrystal-diameter and trap/disorder variability studies using explicit stochastic specifications, fixed local RNG identity, preserved sample manifests, complete failure accounting and explicit scientific interpretation limits.
- **K6c - multi-parameter ensemble DTCO reference:** provide an end-to-end variability-aware DTCO study linking explicit DTCO design points to immutable ensemble results, reusing the same exact manifest where cross-design comparison requires common stochastic draws, applying K5 eligibility and transparent Pareto analysis, and exporting the complete integrity-checked report bundle.

K6 reporting follows the established deterministic and Robust-DTCO reference conventions: repeated construction from identical inputs must reproduce the same report identity; every attempted realization and failure stage must remain represented; nested source identities must be validated rather than trusted from the outer hash alone; CSV artifacts must preserve units, denominators and exact JSON payloads; report snapshots are immutable; and report writers never overwrite existing targets. Plot files, when requested, are derived presentation artifacts and are not included in the canonical report hash.

The planned scientific references are:

- nanocrystal-diameter variability;
- trap/disorder variability;
- multi-parameter ensemble DTCO.

### K7 — v1.2.0 compatibility review and release gates

Review additive public APIs and result contracts, run the full local and remote release-validation ladder, finalize release identity, validate the exact final commit, create tag `v1.2.0`, and publish validated distributions.

---

## Scientific interpretation limits

Phase K samples mathematical distributions assigned to compact-model parameters.

It does not establish that:

- the selected distribution is the true fabrication distribution;
- the selected correlation structure represents a fabrication process;
- the ensemble size corresponds to an experimental population;
- every model parameter has a directly measurable microscopic interpretation;
- simulated pass fractions equal manufacturing yield;
- synthetic variability constitutes experimental calibration.

Where distributions are based on literature, fitted data, measured device populations, or explicit assumptions, that provenance must remain visible in the ensemble evidence and reports.

These limits are part of the scientific result, not optional documentation.

---

## Architecture principle

The intended dependency direction is:

```text
Materials / Device / Transport / Optics
                  |
                  v
             Simulator
                  |
          +-------+-------+
          |               |
        DTCO           Ensemble
          |               |
          +-------+-------+
                  |
                  v
        Variability-aware DTCO
```

The ensemble layer orchestrates existing scientific models. It does not become an alternative physics implementation.

Phase K therefore adds population semantics around the stable simulator while preserving the v1.1.0 scientific baseline.
