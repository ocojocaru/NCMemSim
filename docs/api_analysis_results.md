# Fitting, qualification and DTCO result contracts

Reviewed on the v0.14.0 code retained by `prep/v1.0-stability`. This page records
existing behavior; no fitting algorithm, simulator default, failure policy or
provenance rule changes. The [source inventory](api_inventory.md) lists exact
fields and source signatures. [Core result contracts](api_results.md) cover the
simulator arrays used below. Historical archive compatibility remains a separate
acceptance gate, not established by matching current JSON keys.

## Objective and numerical fit results

Let M be the number of residual observations and P the ordered parameter count.

| Container / fields | Meaning and unit |
| --- | --- |
| `ObjectiveEvaluation.residuals` | `(M,)`, predicted minus observed, observable unit U |
| `objective_residuals` | `(M,)`, raw residuals when unweighted; residual/uncertainty when weighted, dimensionless |
| `residual_sum_squares`, `root_mean_square_error`, `mean_absolute_error` | raw SSE in U^2; RMSE and MAE in U, even for weighted fits |
| `objective_sum_squares` | SSE of the optimizer-facing residuals; dimensionless only when residual normalization makes it so |
| `coefficient_of_determination` | dimensionless raw-residual R^2; None for constant observed values |
| `DeterministicFitResult.initial_values`, `fitted_values`, `active_mask` | `(P,)` in FitParameterSet order; values in each parameter's declared units; mask -1 lower, 0 free, +1 upper |
| `objective_residuals`, `cost` | optimizer vector `(M,)`; cost = objective SSE/2, not raw RMSE |
| `jacobian` | optional `(M,P)` derivatives of optimizer residuals with respect to physical parameter values; columns follow parameter order |
| `success`, `status`, `message`, `nfev`, `njev`, `optimality` | numerical solver diagnostics; njev/Jacobian may be None; never scientific qualification |

`FitParameter.unit` labels values; the generic numerical layer performs no unit
conversion or universal binding-unit validation. Device/workflow adapters have
additional canonical-unit contracts. Declared uncertainty weights are not
independently authenticated experimental uncertainties, especially in synthetic
examples. Raw RMSE/MAE qualification limits must use observable units, not the
weighted optimizer residual scale.

These generic objective/fit arrays are copied and marked non-writable by default.
Their to_dict methods return lists/dictionaries for serialization; mutating those
returned lists does not mutate the numerical arrays. Write protection is an API
convention, not a security boundary or universal deep immutability.
`run_least_squares_fit` requires the optional fit extra (SciPy); data/result imports
and the source inventory checker do not require loading SciPy.

## Local uncertainty diagnostics

`FitUncertaintyDiagnostics` uses the bound-scaled Jacobian for rank, singular
values and condition number. Returned covariance is in physical parameter
coordinates: covariance entry ij has units U_i * U_j, and standard error i has
units U_i. Correlations, rank flags and condition numbers are dimensionless.

The current degrees_of_freedom is **M minus Jacobian rank**, not always M minus P.
Residual variance is objective SSE / degrees_of_freedom when that denominator is
positive, otherwise None. Covariance/standard_errors/correlation_matrix are all
available together only when full column rank, positive degrees of freedom and
no active parameter bounds hold. Unavailable values are None, not zero matrices
or zero uncertainty. Available arrays have shapes `(P,P)`, `(P,)`, `(P,P)` and are
copied/write-protected by default. Singular values have length min(M,P).

`locally_identifiable` is a local full-column-rank diagnostic, not a proof of
unique global parameters. A rank-deficient condition number is positive infinity.
The plain diagnostic to_dict can therefore contain infinity and is not always a
strict finite-JSON object. I1 evidence has a dedicated reversible tagged encoding
for non-finite diagnostic/qualification numbers. Do not replace infinity by zero
or claim the same encoding applies to arbitrary simulator response payloads.
Covariance is conditional model-based fit uncertainty, not reported measurement
uncertainty or a fabrication-variation distribution.

## Device and optical fitting families

| Public result family | Response/context contract |
| --- | --- |
| `DeviceCVFitResult` | DeviceObjectiveEvaluation on dataset voltage order; capacitance F/m^2; retains CVResult and explicit fitted context |
| `DeviceProgramTimeFitResult` / `ProgramTimePrediction` | positive programming times `(M,)` in s, signed predicted_delta_vfb_V `(M,)`, one independent pulse result per time |
| `DevicePulseMemoryTimeFitResult` / `PulseMemoryTimePrediction` | times in s, pulse-defined memory window in V, paired pulse results and reference-state manifest; distinct from dynamic C-V hysteresis |
| `DeviceRetentionFractionFitResult` / `RetentionFractionPrediction` | time in s, dimensionless retention fraction on observation order, physical-time interpolation without extrapolation, retained initial-state manifest |
| `DevicePhotoProgramTimeFitResult` / `ElectroOpticalProgramTimePrediction` | illuminated pulse and dark zero-dwell read; signed shift V, times s; fitted photo_config distinct from operating light settings |
| `DevicePhotoMultiConditionFitResult` | ordered dataset IDs/hashes/protocols/objectives/predictions; shared ordered parameter vector, stacked optimizer residuals and joint Jacobian; uncertainty diagnostics from the full fit |
| `GeSnNearEdgeFitResult` | predicted_absorption_m_inv `(M,)` in 1/m; fitted material parameter set/provenance plus numerical result, objective and local diagnostics |

DeviceObjectiveEvaluation.predicted_values follows the experimental observation
order after the adapter's supported interpolation. Its unmodeled_condition_names
records preserved conditions not represented by this simulation (for example
measurement frequency); it does not mean those conditions were simulated.
Prediction arrays in the listed prediction containers are copied and marked
non-writable; nested pulse/retention/CV states and fitted contexts can remain
mutable. Several device fit wrappers themselves are mutable dataclasses. Do not
apply the generic fit array protection to every nested object or promise a
standalone source-complete archive for every to_dict representation.

Device/material fit wrappers describe FITTED provenance. Generic numerical
success alone does not assign FITTED or CALIBRATED status. Fit wrappers retain
available dataset/specification/protocol/application identities; this is not
proof of an independent validation experiment. Absolute sign and observable
semantics must not be silently converted to magnitude during reporting.

## Qualification and provenance

`CalibrationQualification.eligible_for_calibration` is all configured
criterion_results.passed; failed_criteria preserves criterion order. Each
CalibrationCriterionResult retains observed_value, comparison, threshold and
optional notes. A None optional criterion threshold disables that criterion,
not a zero threshold. Criteria require at least one quantitative validation gate.
RMSE/MAE checks use raw units; R^2 and scaled condition limits are dimensionless.
An undefined R^2 cannot pass an enabled R^2 minimum.

Generic qualify_calibration does not mutate fitted parameters, material registry
or provenance. It retains fit/validation dataset hashes, criteria hash, validation
objective and diagnostics. Distinct dataset hashes are a configured identity
check, not proof of independent acquisition. The generic qualification object
does not store a complete numerical-fit hash; only available links are asserted.

Domain-specific GeSnNearEdgeCalibrationResult and DevicePhotoCalibrationResult
return CALIBRATED/NOT_CALIBRATED according to their configured qualification.
Failed qualification remains a result with calibrated_parameter_set or the
photo calibrated_parameter/calibrated_photo_config absent (None), not silently
promoted. Passing creates a new calibrated record/configuration rather than
mutating the original fit. Model-derived standard errors remain diagnostics;
they are not copied into reported experimental uncertainty. Domain scope,
source provenance and validation evidence still govern scientific applicability.

I1/I2 workflow evidence keeps FITTED and qualification eligibility separately.
A synthetic held-out dataset can pass declared criteria without establishing
experimental calibration or automatic CALIBRATED promotion in that workflow.

## Deterministic DTCO and robust sampling

`ncmemsim.dtco.SweepResult` is the ordered Cartesian result, distinct from the
root `ncmemsim.SweepResult` containing simulator NumPy histories. G results retain
every point and H results every manifest sample. Outputs are finite JSON objects;
access returns reconstructed dictionaries, not live simulator arrays.

| Stage | Recorded failure meaning |
| --- | --- |
| G sweep / H propagation | application, evaluation or serialization failure; no successful output for that point |
| G/H metric analysis | upstream failure or extraction failure; no partial metrics/constraints on a failed case |
| assessed analysis point | feasible or infeasible according to inclusive unit-matched constraints; not a computational failure |
| nominal evaluation/comparison | evaluation/serialization failure, or extraction failure during comparison |
| sensitivity edge | estimated, excluded due to point eligibility, or failed arithmetic; undefined slope is None |

Metric paths accept finite builtin numeric scalars, not booleans/categories.
G can preserve arbitrary finite integer scalars; H statistics additionally
require finite exact float representation. Both keep declared signs and units;
constraints and objectives do not perform automatic conversions.

For H let A be total attempted samples, S assessed complete cases, F feasible,
J infeasible and E failed. Then A = S + E and S = F + J. Fractions are:

- observed feasibility = F/A;
- conditional feasibility = F/S, None when S=0;
- failure fraction = E/A.

A is positive because SamplingSpec requires positive sample count. All-assessed
metric summaries include infeasible complete cases, not failed cases or partial
available metrics. Every metric uses the same assessed sample indices and
denominator S. Standard deviation is population ddof=0; quantiles use linear
interpolation at `(S-1)*q`, preserving requested quantile order. Empty summaries
have None min/max/mean/std/quantile values and denominator 0. A singleton has
population std 0. These empirical fractions are not guaranteed process yield.

G Pareto uses feasible points only, exact dominance, retained ties, source order
and zero-based ranks. Excluded ranks are None, not rank zero. Sensitivity uses
adjacent numeric-grid secants in metric-unit/axis-unit with explicit eligibility
and coverage; it is not a probabilistic/global Sobol analysis.

H robust objectives require an explicit statistic/unit/direction and failure
policy, assessed-count minimum and observed-feasibility minimum. Eligible study
statistics still use all assessed cases. Excluded studies retain reasons and
rank=None with no objective values; admitting assessed studies with failures
does not erase failed samples. Comparisons require common metric/statistic
contracts, evaluator settings and recorded runtimes; nominal device variants
may differ. Nominal comparison requires an exactly matching declared baseline.
Undefined mean-minus-nominal retains a reason (no_assessed_samples or overflow).

## Reports, JSON and CSV

G/H/I report wrappers retain canonical JSON and validate supported nested links
and hashes. Integrity/consistency checks are not authenticity, independent
measurement validation or guaranteed future runtime replay. Free metadata cannot
replace typed evidence. Restoring a supported report does not rerun physics,
optimization, sampling or qualification.

JSON is authoritative for value types and undefined values. CSV conventions are
column-specific: H6 statistics values serialize unavailable numbers as literal
`null`, and the H6 robust CSV uses `null` for an excluded rank. Embedded JSON columns
retain their JSON encodings. Never parse every blank/null as numeric zero.
Writers avoid replacing existing targets but do not promise a transactional
multi-file write under all filesystem failures.

## Audit status and remaining gates

The fields/signatures baseline plus this semantic review cover the existing
fitting/qualification and G/H result families without changing library behavior.
I1–I6 source/context/report contracts remain in the scientific workflow manual.
This does not freeze every pre-v1 API. Remaining gates are approved supported
paths, decisions on documented legacy edge cases, retained historical read-schema
fixtures/migration policy, scientific-default review and final release validation.
