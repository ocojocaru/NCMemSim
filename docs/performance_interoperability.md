# Performance and interoperability - Phase R

## R0 status and baseline

R0 is complete: source audit, exploratory profiling and R1-R7 acceptance sequence.
Baseline is the v1.8 metadata closure commit
`266de0c3e68341b21ba19126bb963b784b9a3480`; the published tag remains on
`03b35f40606dbd84c1cd6d715eb6de6222466b47`.
Version DOI: [10.5281/zenodo.23510004](https://doi.org/10.5281/zenodo.23510004).
The [R0 audit](performance_interoperability_audit.json) records normalized UTF-8/LF
source hashes, exact exploratory inputs/results and measurement limitations.

The next release version is deliberately undecided. Planned development branch:
`dev/phase-r-performance-interop`. No package/citation version is changed by R0.
Acceleration alone is not a reason for a major version; R7 requires a compatibility
rationale. R1-R7 are planned, not implemented or accepted by this document.

No TCAD export or concrete external format is available. The user selected
requirements definition without assuming a simulator vendor. Phase R introduces
no new physical law, device family, fitted parameter or measured qualification.
P4B/P5B/P6B experimental qualification remains deferred.

## Existing baseline and gaps

The legacy `ncmemsim.benchmark` API times a short V2 relaxation for one, two and
three floating gates. It returns the best elapsed time, maximum tracemalloc peak
and last charge observation across repeats; these need not describe one trial.
Tracing changes timing; traced allocation peaks do not establish native NumPy/BLAS
or whole-process resident memory. Keep this API and its historical output intact.
The existing script writes `validation/benchmark_results.json`; R0 did not run
that writer or replace its historical results.

DTCO and manifest executors provide serial references with declared order, owned
contexts and failure accounting. Multilevel pulse steps are state-dependent;
independent preparation/sample/delay work needs different scheduling contracts.
Existing CSV loaders address named experimental observables with typed metadata;
strict scientific bundle restoration is also available. Neither establishes a
generic TCAD file format, observable mapping or co-simulation interface.

## Exploratory profiling on 2026-10-21

One uninstrumented execution was followed by one cProfile execution per case,
in the same Windows process using Python 3.13.12 and source NCMemSim 1.8.0.
Both source and installed-distribution version metadata were 1.8.0. The audit
records NumPy, platform, CPU count, thread environment and profile call tables.
Imports were excluded. There was no warmup/repetition protocol, memory experiment,
parallel/backend comparison or speedup acceptance. These are observations from
one host, not a benchmark campaign.

| Case | Single uninstrumented run (s) | Single cProfile run (s) |
|---|---:|---:|
| legacy_v2_3fg | 0.0193 | 0.0337 |
| q2_electrical_sequence | 1.2150 | 2.0549 |
| q3_level_preparation | 6.0655 | 10.5368 |
| q7_archive_restore | 9.0295 | 21.3285 |

Scopes differ: the legacy case includes simulator/fresh-state construction and
relaxation and selected-output identity hashing on a prebuilt three-FG device;
Q2 executes a prebuilt four-step
experiment; Q3 executes a prebuilt three-level plan; archive restoration validates
a predecoded nine-case report, excluding file I/O and JSON decoding. Cross-row
timing ratios are not speedups. The archive retains its original package-1.7.0
runtime identity. All four plain/profiled pairs retained identical scientific
result hashes, which is a limited instrumentation check, not equivalence of a new
implementation. Cumulative profile entries overlap and must not be summed.

Trajectory profiles include kinetics/rates and trapezoidal WKB costs. Report
restoration shows substantial nested source reconstruction/validation costs.
These observations motivate separate solver and data-handling measurements.
They do not authorize removing validation, reducing grids, changing time steps
or selecting a particular parallel/backend implementation.

## Measurement and equivalence requirements

R1 must define immutable workload identity separately from nondeterministic
performance observations. Capture source commit/import location, package and
distribution metadata versions, Python/NumPy, platform/CPU, native thread settings,
solver/model configuration, grid, time steps, sample manifest and random-stream
identity. Record setup, execution, validation, serialization and I/O scopes.

Use declared warmup and repeated uninstrumented trials with all observations,
median/spread and failed/unavailable trials retained. A candidate default is one
warmup and at least five measured trials, subject to R1 resource-budget review.
Record instrumentation overhead separately. Measure native/process memory with
an explicit method and isolation; do not label tracemalloc peak as total RAM.
Separate transient workspace/storage pressure from simulation memory.

R2 must extend beyond the four exploratory cases: 1-3 FG trajectories, independent
DTCO points, stored DEVICE/MODEL manifests with zero/positive variation and
failures, electrical/optical and thermal contexts, multilevel retention, strict
restoration and bundle export. Use bounded cases with explicit operation counts.
Cross-platform/Python evidence is required; CI wall times are noisy observations,
not an absolute performance pass threshold.

Before accepting R3, preserve full state populations, charge conservation,
signed readout, channels, failure stages and denominators, result ordering and
source identity. Declare observable-specific absolute/relative tolerances and
reference refinement before optimization; preserve negative and unassessable
outcomes. Structural/provenance fields require exact agreement. Scientific input
identity cannot be rewritten to force equal hashes after a changed computation.
Parallel work may cover independent items only; retain manifest index order,
explicit random-stream ownership and immutable state. Include worker startup,
data transfer, validation and export costs in end-to-end comparisons. Require
repeatable benefit on the selected workload without unacceptable memory growth.
No acceleration technology or speedup target is selected by R0.

## Interoperability requirements

R4 starts with a vendor-neutral, versioned data contract. Every imported curve or
profile needs source file digest, source simulator/version, model declarations,
geometry/materials, contacts/bias/temperature, sweep direction/history, initial
state, time/frequency conditions, units and applicability. State coordinate origin,
axis direction, layer order, potential/energy reference and electron-charge sign.
Distinguish total charge from charge per area, signed flat-band shift from an
absolute threshold, and simulated small-signal capacitance from a compact readout.

Require explicit conversion and observable mapping. Preserve original values,
transformation provenance and exclusions; no silent interpolation, smoothing,
sign reversal or unit inference. Missing frequency/area/reference/protocol data
must yield an explicit unavailable comparison, not a fabricated match. Optical
comparisons additionally require sample-plane spectrum/normalization, reflection
and generation assumptions, and which regions contribute to the observable.
Optical transition energies are not interchangeable with tunnelling barriers.

R5 may develop synthetic parser/conversion/comparison references without external
exports, clearly labelled as such. A real TCAD comparison remains conditional on
supplied data and mapping review. No proprietary adapter or external agreement
is claimed. TCAD output is simulated evidence, not measured experimental data.
Full co-simulation, a new PDE solver and larger device families are separate scopes.

## Planned sequence

| Stage | Deliverable | Acceptance |
|---|---|---|
| R0 (complete) | Audit, exploratory profiles, scope and limitations | Baseline/source identity, original results retained; no optimization or TCAD claim |
| R1 | Owned workload/measurement and equivalence contracts | Explicit scopes, repetitions, environment, tolerances and failure policy |
| R2 | Representative serial baseline campaign | Real workloads, bounded resources, trial distributions, numerical references and host provenance |
| R3 | One justified optimization | Repeatable end-to-end benefit with equivalent science, failures, order and resource accounting |
| R4 | Vendor-neutral import/export contracts | Units, coordinates, source identity, applicability and explicit conversion |
| R5 | Controlled optimization/comparison references | Positive/negative/synthetic cases; external applicability conditional on admitted exports |
| R6 | Strict performance/comparison reports | Complete source-linked trials, unavailable outcomes and reproducible projections |
| R7 | Release review | API/archive compatibility, full regression, docs, installed distributions, exact-candidate CI and version rationale |

The immediate next step is R1. R0 changes planning/documentation and enables the
development branch in CI/Documentation. Runtime APIs, defaults, physics, archive
schemas, package identity and citation DOI remain unchanged.
