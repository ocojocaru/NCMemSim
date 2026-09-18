# Robust DTCO — Phase H development

## Status and baseline

H0 starts v0.13.0 at `0.13.0.dev0` from the published v0.12.0 commit
`6da07c5c661a25b2187c13944f9507346c5bc7b0`. The Phase G nominal sweep,
metrics, feasibility, Pareto, grid sensitivity and reporting remain available.
H0 defines the contracts below. H1 adds bounded variation definitions and H2
adds reproducible independent sampling with exact manifests. Sample propagation
and robust analysis remain planned for H3 onward.

Phase H asks how response and feasibility change when supported parameters
vary. It does not introduce new simulator physics or establish experimental
calibration. The package version recorded in runtime provenance can change
result/report hashes; unchanged definitions and regression semantics remain
compatible with Phase G.

## Delivery sequence

| Phase | Deliverable and development status |
| --- | --- |
| H0 | Implemented: scope/contracts and development bootstrap |
| H1 | Implemented: typed bounded definitions, units and provenance |
| H2 | Implemented: reproducible sampling, seed and exact manifest |
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

H2 records distribution definitions, binding order, seed, sample count,
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

Update documentation and changelog alongside each development step, and run
the relevant local checks. Intermediate pushes and pull requests do not start
CI or Documentation Actions. At release candidate, run the full documentation
audit and start Documentation manually; only a manual main build can deploy
Pages. CI runs manually for release-candidate validation and on `v*` release
tags. Package builds and clean installation checks belong to release validation.
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

## H2: reproducible sampling and exact manifests

`SamplingSpec(variations, seed, sample_count, max_draws_per_value=10000)`
requires at least one H1 definition, unique names and bindings, an explicit
nonnegative integer seed smaller than `2**128`, and positive integer sample
count and draw budget. Booleans are rejected as integers. Definition order is
preserved; list inputs are copied into an immutable tuple.

`sample_variations(spec)` uses a local NumPy `Generator(PCG64(seed))` and does
not change global random state. The algorithm is
`numpy-pcg64-scalar-rejection-v1`: scalar float64 draws in sample-major order,
then declared variation order. Uniform values use convex interpolation to avoid
interval-width overflow. Normal values are drawn from the underlying normal and
accepted only when finite and inside the explicit bounds. There is no clipping
or substitution. Independence is a declared assumption, not an inference.

Each value has an explicit attempt budget. Narrow or remote-tail intervals may
exhaust it. `SamplingError` records `sample_index`, `variation_name` and
`attempts`; no partial manifest is returned and no sample disappears.
`KeyboardInterrupt` and `SystemExit` propagate.

```python
from ncmemsim.dtco import (BindingScope, ParameterBinding, UniformVariation,
    TruncatedNormalVariation, VariationDefinition, VariationKind,
    VariationProvenance, SamplingSpec, SampleManifest, sample_variations)

provenance = VariationProvenance(
    source="Assumed intervals for a reproducibility demonstration",
    applicability="Reference electrical protocol, not manufacturing calibration",
)
voltage = VariationDefinition(
    name="program_voltage",
    binding=ParameterBinding(BindingScope.OPERATING, ("program", "voltage_V")),
    distribution=UniformVariation(4.5, 5.5), unit="V",
    kind=VariationKind.PARAMETER_ESTIMATION, provenance=provenance,
)
duration = VariationDefinition(
    name="program_duration",
    binding=ParameterBinding(BindingScope.OPERATING, ("program", "time_s")),
    distribution=TruncatedNormalVariation(0.5e-6, 1.5e-6, 1e-6, 0.1e-6),
    unit="s", kind=VariationKind.PARAMETER_ESTIMATION, provenance=provenance,
)
spec = SamplingSpec((voltage, duration), seed=2026, sample_count=8,
                    max_draws_per_value=10000)
manifest = sample_variations(spec)
assert manifest.to_json() == sample_variations(spec).to_json()
restored = SampleManifest.from_json(manifest.to_json())
assert restored.values == manifest.values
assert restored.manifest_hash == manifest.manifest_hash
assert len(manifest.values) == 8
assert all(4.5 <= row[0] <= 5.5 and 0.5e-6 <= row[1] <= 1.5e-6
           for row in manifest.values)
```

`SampleManifest.values` is an immutable tuple of rows in definition order.
`to_dict()` returns fresh nested data with zero-based contiguous sample indices,
the full specification and provenance, exact values, Python version and
implementation, NumPy/package versions, and specification/manifest hashes.
`to_json()` and `from_json()` preserve those inputs without regenerating draws.
Restoration validates schema, algorithm, indices, shape, bounds and hashes,
and rejects extra/duplicate keys and nonfinite values. Integrity hashes do not
authenticate a manifest or establish physical calibration.

The seed alone is insufficient for cross-runtime reproducibility. Within the
recorded algorithm/runtime, repeated calls reproduce the exact manifest; across
arbitrary NumPy/Python versions bitwise equality is not promised. Use the stored
manifest as propagation input. H2 does not run the simulator, link a nominal
device/protocol or compute feasibility/statistics. Validate definition context
before a study and validate every combined candidate during H3 propagation.
