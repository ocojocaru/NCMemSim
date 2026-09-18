# Robust DTCO — Phase H development

## Status and baseline

H0 starts v0.13.0 at `0.13.0.dev0` from the published v0.12.0 commit
`6da07c5c661a25b2187c13944f9507346c5bc7b0`. The Phase G nominal sweep,
metrics, feasibility, Pareto, grid sensitivity and reporting remain available.
H0 defines the contracts below. H1 adds bounded variation definitions; sampling
and robust analysis remain planned.

Phase H asks how response and feasibility change when supported parameters
vary. It does not introduce new simulator physics or establish experimental
calibration. The package version recorded in runtime provenance can change
result/report hashes; unchanged definitions and regression semantics remain
compatible with Phase G.

## Delivery sequence

| Phase | Planned deliverable |
| --- | --- |
| H0 | Scope/contracts, development version and documentation workflow policy |
| H1 | Typed bounded variation definitions, units and provenance |
| H2 | Reproducible sampling, explicit seed and sample manifest |
| H3 | Sample propagation through supported binding/evaluator contracts |
| H4 | Response statistics and explicit feasibility/failure accounting |
| H5 | Nominal/robust comparisons and explicitly defined robust objectives |
| H6 | Reproducible reports and an end-to-end reference |
| H7 | Regression/CI/distribution validation and documentation audit before tag |

## Variation semantics

The initial contract uses independent continuous numeric DEVICE and OPERATING
bindings already supported by Phase G, with their exact canonical units.
Integer fields such as `grid_points`, categorical variables, MODEL execution,
FG-count changes and arbitrary model-parameter traversal are excluded initially.
Every sampled candidate must still pass the existing physical/device/protocol
validation; a distribution is not permission to bypass a binding contract.

Each definition must distinguish fabrication variation from parameter-estimation
uncertainty and record its source/provenance and applicability range. A declared
distribution describes the study's assumption, not an inferred measured fact.
Fitting covariance is not automatically a manufacturing distribution, and
independent marginal sampling is not justified merely by fit standard errors.

H1 validates exact units, finite numeric parameters, ordered finite bounds,
and valid distribution parameters before execution. Initial distribution
families are bounded uniform and normal truncated to explicit finite bounds.
Normal parameters describe the underlying normal law before truncation; they
are not the actual moments of the truncated distribution. No clipping, silent
unit conversion, missing-bound defaults or automatic distribution inference.

Supported geometric/composition fractions must retain their existing valid
ranges. Whether an interval is admissible is checked against binding semantics,
not just mathematical distribution validity. Dependence/correlation, discrete
laws, joint posterior sampling and sensitivity-based probability inference
remain outside the first implementation.

## Sampling identity and execution

H2 must record distribution definitions, binding order, seed, sample count,
algorithm identifier/version and relevant library/runtime versions. The exact
sample manifest, not the seed alone, establishes the input to propagation.
Reproducibility is defined within a recorded algorithm/runtime; bitwise equality
across arbitrary NumPy/Python versions is not assumed.

Sampling must draw from the specified bounded law, without clipping values to
limits. The algorithm, precision, any rejection policy and any exhaustion limit
must be explicit. A failed draw cannot silently disappear or be substituted.
Candidates start from isolated nominal device/protocol copies. Evaluation is
serial initially, preserving sample indices, input identities and failure stages.
KeyboardInterrupt/SystemExit must continue to propagate.

## Statistics and failure accounting

Keep total, assessed, feasible, infeasible and failed sample counts separately.
A numerical or application failure is not automatically physically infeasible.
Metric statistics use successfully assessed samples only, state their denominator
and have explicit undefined behavior when no samples are assessed. Quantile
method, units and sample identities must be recorded; no silent zero filling.

Report the observed feasible fraction of all attempted samples and the
conditional feasible fraction among assessed samples with distinct names and
denominators. If failures exist, the former is conservative observed evidence,
not an unbiased physical feasibility probability. The failure fraction is
reported alongside both. Any uncertainty interval or probabilistic claim must
name its statistical assumptions and estimator; finite sampling gives an
estimate rather than guaranteed yield.

## Robust comparisons and reporting

H5 must define a robust objective explicitly before Pareto sorting, including
metric, units, direction, statistic/quantile and eligibility/failure policy.
No automatic absolute-value transformation, weighting or mixing of incompatible
units. A nominal point and its sampled study must share explicit identity links;
robust results cannot be presented as a nominal simulator output.

H6 reports preserve nominal and sampled definitions, sample payloads, response
statistics, constraints, failures and provenance. Integrity hashes are not
digital signatures or evidence of physical calibration. Initial robust analysis
is not a Sobol variance decomposition or Bayesian optimization.

## Release and documentation gates

Before a release tag: audit all current-version/status claims, examples, imports,
links/anchors and scientific limits; build strictly; inspect the built source
archive for the audited Markdown/assets and compare their actual contents.
Run full scientific regression, supported-Python CI and clean installed wheel
and source checks for code/packaging changes. Version, tag, source archive and
published assets must agree before closing the release.

Documentation-only commits run Documentation, not full CI. Development and PR
builds validate strictly but do not replace the published main Pages site.
Generated `site/` is not the source of truth and is not regenerated for commits.

## H1: bounded variation definitions

`UniformVariation(lower, upper)` requires finite, strictly ordered bounds.
`TruncatedNormalVariation(lower, upper, mean, standard_deviation)` additionally
requires a finite mean and strictly positive finite standard deviation. Its mean
may lie outside the bounds: these parameters describe the underlying normal.
No values are drawn, clipped, converted or inferred in H1.

```python
from ncmemsim.dtco import (BindingScope, ParameterBinding, UniformVariation,
    VariationDefinition, VariationKind, VariationProvenance)

variation = VariationDefinition(
    name="temperature",
    binding=ParameterBinding(BindingScope.DEVICE, ("temperature_K",)),
    distribution=UniformVariation(290.0, 310.0),
    unit="K",
    kind=VariationKind.PARAMETER_ESTIMATION,
    provenance=VariationProvenance(
        source="Assumed study interval, not experimental calibration",
        applicability="Nominal reference device near room temperature",
    ),
)
assert variation.to_dict()["distribution"]["family"] == "uniform"
assert len(variation.definition_hash) == 64
```

Call `variation.validate_context(device, protocol)` before a study to check both
endpoints using existing Phase G bindings on isolated copies. DEVICE variations
do not require a protocol; OPERATING variations do. A layer name, material model
and optical protocol must actually support the requested binding. This is a
context check, not execution, a joint-range proof or a guarantee of convergence.
Future propagation must validate every combined candidate.

The definition hash covers the schema, name, binding, distribution, exact unit,
kind and provenance. It does not identify a nominal device, protocol or sample
manifest; those links belong to later phases. Returned dictionaries are fresh
copies. Definitions and provenance are immutable. No MODEL contract is added to
Phase G: MODEL and integer bindings are simply outside this new H1 API.
