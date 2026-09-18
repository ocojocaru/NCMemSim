# Robust DTCO — Phase H development

## Status and baseline

H0 starts v0.13.0 at `0.13.0.dev0` from the published v0.12.0 commit
`6da07c5c661a25b2187c13944f9507346c5bc7b0`. The Phase G nominal sweep,
metrics, feasibility, Pareto, grid sensitivity and reporting remain available.
H0 defines the contracts below. H1 adds bounded variation definitions and H2
adds reproducible independent sampling with exact manifests. H3 propagates those
inputs serially through isolated candidates. H4 adds complete-case response
statistics and explicit feasibility/failure accounting. H5 adds linked nominal
comparisons and explicitly defined robust Pareto objectives. H6 adds linked
report snapshots, portable exports and a complete electrical reference. Final
release validation remains H7.

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
| H3 | Implemented: serial isolated propagation with staged failure records |
| H4 | Implemented: response statistics and feasibility/failure accounting |
| H5 | Implemented: linked nominal comparison and explicit robust Pareto objectives |
| H6 | Implemented: linked report bundles and electrical Robust DTCO reference |
| H7 | Implemented: local regression/distribution/documentation gates; remote candidate CI/Documentation pending |

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
manifest as propagation input. H2 itself does not run the simulator, link a nominal device/protocol or compute
feasibility/statistics. H3 adds nominal linking and candidate propagation below.

## H3: propagation through isolated candidates

`propagate_samples(manifest, base_device, evaluator, evaluation_id=...,
evaluation_parameters=..., base_protocol=...)` consumes exact stored values
without sampling again. Device-only studies may omit a protocol; any OPERATING
variation requires a supported nominal protocol. The study snapshots the caller's
device/protocol, checks the nominal baseline and each definition's endpoint
context, then validates every combined candidate using existing Phase G bindings.
Setup/context errors fail before any callback. Binding type/material/layer/optical
restrictions remain unchanged.

Each callback receives `(candidate_device, candidate_protocol, sample_point)`.
Candidates start from fresh copies of the frozen nominal baseline, in manifest
order. Callbacks must create fresh simulator/state objects, return a finite JSON
object and declare their scientific settings in `evaluation_parameters`.
`evaluation_id` identifies callback code/settings conventions; it is not inferred
from the callable. Mutations of candidates cannot contaminate later candidates.
An evaluator's external shared state remains the caller's responsibility.

```python
from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (BindingScope, ParameterBinding, UniformVariation,
    VariationDefinition, VariationKind, VariationProvenance, SamplingSpec,
    sample_variations, propagate_samples)
from ncmemsim.program_protocol import ProgramPulseReadProtocol, run_program_pulse_read
from ncmemsim.simulator import Simulator, SimulationConfig
from dataclasses import asdict

device = DeviceBuilder.v2(n_fgs=1, name="h3-electrical-example")
protocol = ProgramPulseReadProtocol(5.0, 1e-7)
variation = VariationDefinition(
    name="duration",
    binding=ParameterBinding(BindingScope.OPERATING, ("program", "time_s")),
    distribution=UniformVariation(1e-7, 2e-7), unit="s",
    kind=VariationKind.PARAMETER_ESTIMATION,
    provenance=VariationProvenance("Assumed example interval", "Reference protocol"),
)
manifest = sample_variations(SamplingSpec((variation,), seed=2026, sample_count=2))
config = SimulationConfig()

def evaluate(candidate, candidate_protocol, sample_point):
    pulse = run_program_pulse_read(Simulator(candidate, config=config), candidate_protocol)
    return {"delta_vfb_V": pulse.delta_vfb_V, "sample_index": sample_point.index}

result = propagate_samples(
    manifest, device, evaluate, base_protocol=protocol,
    evaluation_id="h3-electrical-example-v1",
    evaluation_parameters={"simulation_config": asdict(config),
                           "physics_model": "PhysicsModel.default",
                           "initial_state": "empty_for_each_candidate"},
)
assert result.success_count == 2 and result.failure_count == 0
assert tuple(p.point.index for p in result.points) == (0, 1)
assert all(p.point.manifest_hash == manifest.manifest_hash for p in result.points)
```

`SamplePoint` records manifest identity, zero-based index and ordered exact
assignments; `assignments` returns a fresh mapping. `SamplePointResult` is either
a success with an immutable JSON output snapshot or a failure with stage, error
type and message. Ordinary exceptions at `application`, `evaluation` or
`serialization` become records and execution continues. Every manifest sample
has exactly one result, including failed samples. `KeyboardInterrupt` and
`SystemExit` propagate. No output is silently coerced, clipped or zero-filled.

`PropagationResult` preserves the manifest, full nominal device/material and
protocol definitions, evaluator identity/parameters, propagation runtime and
ordered point results. `nominal_hash` identifies the full baseline, `study_hash`
the declared inputs/execution, and `result_hash` additionally includes outcomes.
`to_dict()` returns fresh data and `to_json()` exports the result; report
restoration is a later phase. Hashes check integrity, not authentication.
A successful callback does not establish physical feasibility. H4 applies
declared metrics/constraints with separate accounting below.

## H4: response statistics and explicit denominators

`analyze_samples(propagation_result, SampleAnalysisSpec(metric_spec, quantiles))`
consumes completed H3 results without reevaluating physics. `metric_spec` is the
existing Phase G `MetricAnalysisSpec`: ordered numeric output paths, exact units
and inclusive named constraints. All metrics must extract successfully for a
sample to be assessed. Missing/nonnumeric/nonfinite outputs or integers that
cannot be represented exactly as finite floats become extraction failures;
partial metrics and constraints are discarded. Phase G extraction is unchanged.

`SampleMetricPointResult.status` is `feasible`, `infeasible` or `failed`.
Assessed samples satisfy or violate the declared constraints; without
constraints, every assessed sample is feasible. A propagation failure retains
its original source stage/type/message and is classified as `propagation`; an
analysis failure is `extraction`. Neither is treated as physical infeasibility.
Every source sample remains present in manifest order.

`SampleAnalysisResult` exposes `total_count`, `assessed_count`, `feasible_count`,
`infeasible_count` and `failure_count`. Total equals assessed plus failed, and
assessed equals feasible plus infeasible. JSON also separates propagation and
extraction failure counts. Three distinct observed fractions have explicit
numerators and denominators:

- `observed_feasible_fraction_all_attempted`: feasible / total;
- `conditional_feasible_fraction_assessed`: feasible / assessed, or `None` when
  assessed is zero;
- `failure_fraction_all_attempted`: failed / total.

With failures, the all-attempted feasible fraction is conservative observed
evidence, not an unbiased estimate of physical feasibility probability. The
conditional fraction describes only assessed samples. No yield guarantee,
confidence interval or automatic probabilistic interpretation is produced.

Metric statistics use all assessed complete cases, including infeasible
samples. Each record includes metric name/unit, denominator and exact source
sample indices. Minimum, maximum, mean, population standard deviation (`ddof=0`)
and quantiles are descriptive response summaries, not fitted distributions.
Quantile probabilities are finite and unique in `[0, 1]`, defaulting to
`(0.05, 0.5, 0.95)`; declared order is preserved and an empty tuple omits quantiles.
The method is fixed: sort observed values, interpolate at `(n-1)*q` using convex
weights (`linear-n-minus-one`). No absolute-value transformation or unit mixing.

With no assessed samples, denominator is zero, indices are empty and all
statistics/quantile values are `None` (JSON `null`). A singleton has population
standard deviation zero. No failed value is zero-filled.

```python
from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (BindingScope, ParameterBinding, UniformVariation,
    VariationDefinition, VariationKind, VariationProvenance, SamplingSpec,
    sample_variations, propagate_samples, MetricDefinition, MetricConstraint,
    MetricAnalysisSpec, ConstraintOperator, SampleAnalysisSpec, analyze_samples)

variation = VariationDefinition(
    "temperature", ParameterBinding(BindingScope.DEVICE, ("temperature_K",)),
    UniformVariation(295.0, 305.0), "K", VariationKind.PARAMETER_ESTIMATION,
    VariationProvenance("Assumed demonstration interval", "Synthetic accounting example"),
)
manifest = sample_variations(SamplingSpec((variation,), seed=2026, sample_count=4))

def evaluate(candidate, protocol, point):
    # Synthetic outputs illustrate accounting, not a physical response model.
    if point.index == 2:
        raise RuntimeError("Demonstration evaluation failure")
    if point.index == 3:
        return {}  # Deliberately missing the response metric.
    return {"response_V": 1.0 if point.index == 0 else 3.0}

propagation = propagate_samples(
    manifest, DeviceBuilder.v2(n_fgs=1), evaluate,
    evaluation_id="h4-synthetic-accounting-v1",
    evaluation_parameters={"response_model": "synthetic index-based demonstration"},
)
metric_spec = MetricAnalysisSpec(
    "responses", (MetricDefinition("response", ("response_V",), "V"),),
    (MetricConstraint("maximum", "response", ConstraintOperator.LE, 2.0, "V"),),
)
analysis = analyze_samples(propagation, SampleAnalysisSpec(metric_spec, (0.0, 0.5, 1.0)))
assert (analysis.total_count, analysis.assessed_count, analysis.feasible_count,
        analysis.infeasible_count, analysis.failure_count) == (4, 2, 1, 1, 2)
assert analysis.observed_feasible_fraction_all_attempted == 0.25
assert analysis.conditional_feasible_fraction_assessed == 0.5
assert analysis.failure_fraction_all_attempted == 0.5
assert analysis.metric_statistics[0]["sample_indices"] == [0, 1]
assert analysis.metric_statistics[0]["mean"] == 2.0
```

Specifications/results are immutable and exported dictionaries are fresh
snapshots. `analysis_hash` links the metric/statistic definition to the exact
propagation result and snapshotted aggregation runtime/algorithm; `result_hash`
also includes assessed statuses and summaries. `to_json()` exports full inputs
and outcomes. Hashes are integrity links, not signatures or calibration evidence.
H5 adds linked comparisons/objectives below; H6 supplies report bundles.

## H5: nominal comparisons and explicit robust objectives

`evaluate_nominal(device, evaluator, evaluation_id=..., evaluation_parameters=...,
base_protocol=...)` evaluates an isolated nominal copy. Its callback takes
`(device, protocol)` and must use the same scientific response model/settings as
the H3 callback, with fresh simulator/state objects. Setup errors fail early;
ordinary evaluation/serialization errors become `NominalResult` failure records.
Interrupts propagate. Definitions, evaluator settings, runtime and finite JSON
outputs are immutable snapshots.

`compare_nominal(sample_analysis, nominal_result)` rejects any mismatch in full
nominal device/material/protocol identity, evaluator id/parameters or recorded
propagation runtime. Matching ids are caller declarations, not code inspection.
The nominal result must be evaluated with the same scientific settings. Metric
extraction reuses H4's complete-case rules and units. The comparison records
nominal feasibility, all assessed sample summaries and signed `mean_minus_nominal`.
No assessed samples yields an undefined difference (`None`/`null` with reason
`no_assessed_samples`); arithmetic overflow yields `arithmetic_overflow`. Nominal
failures or missing metrics remain explicit, without substituted values.

`RobustObjective(name, metric_name, unit, direction, statistic, quantile=None)`
requires exact source units, explicit `ObjectiveDirection` and `RobustStatistic`.
Available statistics are mean, minimum, maximum, population standard deviation
and quantile. Quantile objectives require a probability already computed in H4;
other statistics reject a quantile argument. There is no automatic sign change,
absolute value, weighting, unit conversion or quantile inference.

`RobustParetoSpec` requires all eligibility settings explicitly:

- `failure_policy`: `REQUIRE_NO_FAILURES` or `ALLOW_ASSESSED_WITH_FAILURES`;
- `minimum_assessed_count`: positive integer;
- `minimum_observed_feasible_fraction`: threshold in `[0,1]` applied to
  feasible / all attempted, not the conditional fraction.

Allowing failures selects statistics over assessed complete cases; it does not
estimate missing responses or turn failures into physical infeasibility. Studies
with undefined objectives are excluded. Excluded studies retain every source
result and ordered reasons, with no rank or objective substitution.

`analyze_robust_pareto(analyses, spec)` requires common metric/constraint/quantile
definitions, evaluator id/settings and recorded propagation/aggregation runtimes.
Nominal designs, sample counts, seeds and declared variation laws may differ;
their exact manifests/provenance remain visible, and comparability of these study
assumptions is the caller's responsibility. Ranking compares explicit vectors
exactly: no worse in all objectives and strictly better in at least one. Equal
vectors are all retained. All fronts preserve declared study order, with zero-based
ranks. An entirely excluded set has empty fronts. Sorting is O(N²M) time and
O(N²) worst-case memory for N eligible studies and M objectives.

```python
from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (BindingScope, ParameterBinding, UniformVariation,
    VariationDefinition, VariationKind, VariationProvenance, SamplingSpec,
    sample_variations, propagate_samples, MetricDefinition, MetricAnalysisSpec,
    SampleAnalysisSpec, analyze_samples, evaluate_nominal, compare_nominal,
    ObjectiveDirection, RobustStatistic, RobustFailurePolicy, RobustObjective,
    RobustParetoSpec, analyze_robust_pareto)

variation = VariationDefinition(
    "temperature", ParameterBinding(BindingScope.DEVICE, ("temperature_K",)),
    UniformVariation(295.0, 305.0), "K", VariationKind.PARAMETER_ESTIMATION,
    VariationProvenance("Assumed example interval", "Synthetic linear response example"),
)
manifest = sample_variations(SamplingSpec((variation,), seed=2026, sample_count=4))
metric_spec = SampleAnalysisSpec(MetricAnalysisSpec(
    "response", (MetricDefinition("response", ("response_V",), "V"),),
))
parameters = {"response_model": "synthetic linear example", "temperature_slope_V_K": 0.01}

def response(candidate, protocol):
    # Demonstration model, not experimental calibration or simulator physics.
    return {"response_V": candidate.gate_work_function_eV
            + parameters["temperature_slope_V_K"] * (candidate.temperature_K - 300.0)}

designs = [DeviceBuilder.v2(n_fgs=1, name="h5-design-a"),
           DeviceBuilder.v2(n_fgs=1, name="h5-design-b")]
designs[1].gate_work_function_eV = 4.9
analyses = []
for design in designs:
    propagation = propagate_samples(
        manifest, design, lambda c, p, point: response(c, p),
        evaluation_id="h5-linear-example-v1", evaluation_parameters=parameters,
    )
    analyses.append(analyze_samples(propagation, metric_spec))
nominal = evaluate_nominal(
    designs[0], response, evaluation_id="h5-linear-example-v1",
    evaluation_parameters=parameters,
)
comparison = compare_nominal(analyses[0], nominal)
assert comparison.to_dict()["status"] == "assessed"
robust_spec = RobustParetoSpec(
    "lower-quantile-response",
    (RobustObjective("q05", "response", "V", ObjectiveDirection.MAXIMIZE,
                     RobustStatistic.QUANTILE, quantile=0.05),),
    failure_policy=RobustFailurePolicy.REQUIRE_NO_FAILURES,
    minimum_assessed_count=4, minimum_observed_feasible_fraction=1.0,
)
fronts = analyze_robust_pareto(analyses, robust_spec)
assert fronts.pareto_indices == (1,)
assert len(fronts.to_dict()["points"]) == 2
```

`NominalComparison` and `RobustParetoResult` export fresh dictionaries/JSON and
integrity hashes linking their source results. Robust ranking is a separate
analysis, not a nominal simulator output, calibrated optimum or guaranteed yield.
Scientific eligibility and failure handling are always visible in the spec.
H6 supplies reproducible report bundles and an electrical reference below.

## H6: reproducible reports and electrical reference

`build_robust_dtco_report(analyses, name=..., nominal_comparisons=...,
robust_pareto=..., metadata=...)` snapshots ordered H4 analyses and optional
H5 comparisons/fronts into `RobustDTCOReport`. Comparisons must have the same
source analysis at each position; robust fronts must reference the exact ordered
analyses. Missing nominal comparisons are explicit `None` entries, not silently
matched by name. Empty input or mismatched source/order/count is rejected.

The manifest preserves full variation definitions/provenance, exact sampled
values, baseline device/material/protocol definitions, evaluator/settings/runtime,
responses, metric constraints/statistics, nominal comparisons, robust eligibility
and every failure stage. Integrity hashes link sections and the complete report.
`to_dict()` returns fresh data; the report itself is an immutable JSON snapshot.
`from_json()` checks report/section hashes, source links, exact sample indices and
assignments, assessment counts, denominators and statistic units/source indices.
It rejects duplicate JSON keys and nonfinite values and does not regenerate
samples, rerun physics or require the original runtime to be installed. These
checks establish payload consistency, not signatures or scientific calibration.

`write_robust_dtco_report(report, output_dir)` writes six UTF-8 artifacts:

- `manifest.json`: full exact report and integrity hash;
- `samples.csv`: all study/sample indices, assignments, responses, constraints
  and propagation/analysis failures;
- `statistics.csv`: metric units, denominators, source indices, descriptive
  summaries and quantiles;
- `nominal.csv`: nominal values/differences or explicit nominal failure records;
- `robust.csv`: study identities, ranks, objectives and exclusion reasons;
- `report.md`: counts, observed fractions, fronts and scientific interpretation.

Undefined numeric CSV cells use the literal JSON `null`; structured cells are
JSON. Optional absent sections produce header-only CSV files. Existing target
files cause an error before writing; export never overwrites them. This is not
a transactional database: an I/O failure can leave a partial new bundle.

```python
from tempfile import TemporaryDirectory
from pathlib import Path
from examples.phase_h6_robust_dtco_reference import build_reference_report
from ncmemsim.dtco import RobustDTCOReport, write_robust_dtco_report

report = build_reference_report()
restored = RobustDTCOReport.from_json(report.to_json())
assert restored.report_hash == report.report_hash
with TemporaryDirectory(prefix="robust-dtco-example-") as temporary:
    paths = write_robust_dtco_report(restored, Path(temporary) / "report")
    assert len(paths) == 6
    assert RobustDTCOReport.from_json(paths[0].read_text(encoding="utf-8")).report_hash == report.report_hash
```

The source example `examples/phase_h6_robust_dtco_reference.py` evaluates two
nominal temperatures, using one exact four-sample manifest with independent
assumed duration/work-function marginals. Each electrical program/read call
creates a fresh simulator/state. Nominal and sampled evaluations declare the
same response model/configuration and use signed shift, duration and occupation
metrics. The robust objectives maximize the lower signed-shift quantile and
minimize mean duration; no absolute-value interpretation is inferred.

From the repository root, export to separate new directories:

```text
python examples/phase_h6_robust_dtco_reference.py --output-dir results/h6-reference
python examples/phase_h6_robust_dtco_reference.py --include-failures --output-dir results/h6-failures
```

The normal reference has two studies with four assessed samples each. Failure
mode deliberately injects evaluation, missing-metric and serialization failures,
leaving one assessed and three failed samples per study. Failure injection and
its explicit eligibility policy are declared in provenance/settings; it does not
claim those errors were physical simulator predictions. This mode permits
assessed-with-failures objectives and reports the failure fraction alongside
all-attempted and conditional assessed feasibility fractions. Nominal evaluations
remain physical program/read calls. The study is an assumed uncertainty example,
not an experimentally calibrated manufacturing-yield estimate.

Full scientific regression, supported-Python CI, strict documentation audit,
source-content and installed-distribution validation remain the H7 release gate.

## H7 — release-candidate validation

Run `python scripts/validate_documentation.py` from the checkout to build
strictly in a temporary directory, check rendered local links/anchors and README
references, validate Python snippets/public imports and execute G/H examples.
The historical software design specification remains an explicitly historical
document, excluded from executable snippet validation.

Run `python scripts/validate_dtco_distribution.py` for clean wheel/sdist
installations outside the checkout. Both installed electrical references exercise
normal and deliberate failure cases, repeatable hashes, snapshot restoration and
CSV exports. Every Robust DTCO module must resolve inside the fresh environment.
The built source archive is compared byte for byte with audited source modules,
documentation, assets and reference/build entry points. `--reuse-dependencies`
is an offline convenience and does not satisfy the clean-install release gate.

Full pytest and manual CI across supported Python versions, followed by manual
Documentation on the exact candidate commit, are required before release. Branch
pushes do not trigger these workflows. H7 does not create a release tag or bump
the development version; remote gates remain pending until the candidate is
committed and pushed after local review.
