# Performance and interoperability - Phase R

## R0 status and baseline

R0 is complete: source audit, exploratory profiling and R1-R7 acceptance sequence.
Baseline is the v1.8 metadata closure commit
`266de0c3e68341b21ba19126bb963b784b9a3480`; the published tag remains on
`03b35f40606dbd84c1cd6d715eb6de6222466b47`.
Version DOI: [10.5281/zenodo.23510004](https://doi.org/10.5281/zenodo.23510004).
The [R0 audit](performance_interoperability_audit.json) records normalized UTF-8/LF
source hashes, exact exploratory inputs/results and measurement limitations.

R7 preparation targets **v1.9.0**, with additive APIs and unchanged published
module surfaces; see the [release checklist](v1_9_release_checklist.md). Development
branch: `dev/phase-r-performance-interop`. Current package/citation identity stays
1.8.0 until the separately verified final candidate. R1/R2 are implemented and the exact R2 commit passed cross-platform CI.
R3 passed exact-commit CI and Documentation on `8c63a0a`. R4 implements owned
vendor-neutral interchange and explicit conversion, with exact-commit CI passed
on `6e7514b`. R5 controlled comparisons passed CI on `0796d4c`. R6 adds strict static serial-
campaign/comparison reports and reproducible bundles. R7 API/archive preparation
is implemented; exact new-commit CI and final-candidate/release closure remain pending.

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
| R1 (complete) | Owned workload/measurement and equivalence contracts | Explicit scopes, repetitions, environment, tolerances and failure policy |
| R2 (cross-platform evidence reviewed) | Representative serial baseline campaign | Real workloads, bounded resources, trial distributions, numerical references and host provenance |
| R3 (complete; exact-commit CI passed) | One justified optimization | Repeatable end-to-end benefit with equivalent science, failures, order and resource accounting |
| R4 (implemented) | Vendor-neutral import/export contracts | Units, coordinates, source identity, applicability and explicit conversion |
| R5 (implemented) | Controlled optimization/comparison references | Positive/negative/synthetic cases; external applicability conditional on admitted exports |
| R6 (implemented) | Strict performance/comparison reports | Complete source-linked trials, unavailable outcomes and reproducible projections |
| R7 (preparation implemented; release pending) | Release review | API/archive compatibility, full regression, docs, installed distributions, exact-candidate CI and version rationale |

R2 measurements and exact-commit CI evidence have been reviewed. The selected
R3 optimization and paired acceptance protocol are recorded in the
[report restoration review](report_restoration_optimization.md). R1 adds contracts without changing existing runtime APIs,
physics, defaults, published archive schemas, package identity or citation DOI.


## R1 owned contracts and numerical equivalence

`ncmemsim.performance_contracts` exports seven additive names:

| Contract/API | Responsibility |
|---|---|
| `PerformanceWorkload` | Owned scientific inputs, logical item count, scope and dependency declaration |
| `MeasurementProtocol` | At least one warmup and five measurements; instrumentation, isolation and time budgets |
| `PerformanceEnvironment` | Declared source/import/version, Python/NumPy, CPU/platform, backend and thread settings |
| `PerformanceTrial` | One indexed warmup/measurement, status, elapsed seconds, result hash and explicit memory method |
| `EquivalenceRule` | JSON Pointer, quantity, unit and absolute/relative tolerance for a scalar or numeric array |
| `EquivalenceContract` | Workload identity, numeric rules, mandatory exact paths and reference evidence |
| `compare_scientific_results` | Deterministic whole-payload comparison and source/result hashes |

The six contract classes own canonical finite native-JSON snapshots. `to_dict()`
returns a fresh copy; `to_json()` and `contract_hash` identify the declaration.
`from_dict()`/`from_json()` reconstruct strictly, rejecting unknown fields, changed
derived fields, duplicate JSON keys and nonfinite values. Constructors perform no
simulation, timing, environment probing or external process execution.

Scientific inputs must explicitly include the device/model/solver, grid/time steps,
initial state, protocol, manifests and random streams relevant to the workload.
The contract cannot discover omitted inputs or hidden callback state.
`scientific_input_hash` binds workflow kind and those inputs; the complete contract
hash additionally binds scope, dependency, count, label and notes. Comparisons bind
the complete workload hash. Source identity must never be rewritten to force a match.

Scope selects setup, execution, validation, serialization and/or I/O, or the single
`end_to_end` scope. Sequence steps require `state_chain`; independent work must be
declared explicitly. R1 validates declarations, not scheduling independence.
Environment metadata are caller declarations, not certification of actual imports
or host settings. Import paths must be absolute. Unknown CPU count, distribution
version or thread settings remain `None`; unknown thread limits do not mean one.
Declare `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` and
`NUMEXPR_NUM_THREADS` explicitly, with further relevant settings when applicable.

R1 does not run or aggregate a campaign. R2 must capture the environment, enforce
the declared per-trial/total budgets, ensure complete unique trial indices and
retain all warmups, repetitions and failures before computing median/spread.
Completed trials need elapsed seconds and a result digest. Failed trials retain
available partial observations and a stage/type/message reason; unavailable trials
cannot invent measurements. `trial_budget_exceeded` retains over-budget observations.
`uninstrumented_measurement` describes a completed uninstrumented measured trial;
it does not establish numerical equivalence, resource acceptance or a speedup.

Memory is `not_measured`, `traced_allocations` (tracemalloc) or `process_peak_rss`
(native-memory instrumentation in a fresh process), with integer bytes and an
explicit method. These quantities are not interchangeable. Instrumented timing
belongs to a separate protocol from uninstrumented timing.

### Synthetic comparison example

The following tolerance is a test-only illustration, not a recommended physical
accuracy threshold or a measured benchmark. Real references need justified
observable-specific tolerances and refinement evidence before optimization.

```python
from ncmemsim.performance_contracts import (
    PerformanceWorkload, MeasurementProtocol, EquivalenceRule,
    EquivalenceContract, compare_scientific_results,
)

workload = PerformanceWorkload(
    "synthetic-readout", "sequence",
    {"device": "synthetic", "dt_s": 1e-9, "initial_population": [1.0, 0.0]},
    ("execution",), "state_chain", 2, "Contract example; no solver execution",
)
protocol = MeasurementProtocol()  # declares one warmup and five measurements
rule = EquivalenceRule("/observations/delta_vfb", "signed_flat_band_shift", "V", 1e-9, 1e-6)
contract = EquivalenceContract(
    workload.contract_hash, (rule,), ("/context",),
    "Synthetic test-only tolerance; no experimental or refinement claim",
)
reference = {"context": {"source": "synthetic", "order": [0, 1]},
             "observations": {"delta_vfb": [0.1, -0.2]}}
candidate = {"context": {"source": "synthetic", "order": [0, 1]},
             "observations": {"delta_vfb": [0.10000001, -0.2]}}
assert compare_scientific_results(contract, workload, reference, candidate)["status"] == "equivalent"
candidate["context"]["source"] = "changed"
assert compare_scientific_results(contract, workload, reference, candidate)["status"] == "not_equivalent"
candidate["context"]["source"] = "synthetic"
candidate["observations"]["delta_vfb"] = None
assert compare_scientific_results(contract, workload, reference, candidate)["status"] == "not_assessable"
```

The comparison applies `abs(candidate-reference) <= atol + rtol*abs(reference)`
using exact rational arithmetic on supplied finite numbers, avoiding overflow,
subnormal loss and large-integer rounding in the oracle. It performs no unit
conversion, interpolation or resampling. Numeric arrays require identical shape
and order; all other fields require exact values and types. Object key order is
irrelevant. JSON Pointer escapes are supported; overlapping exact/numeric rules
are rejected. Mandatory paths must exist; null or empty numeric observations are
unassessable. A known mismatch takes precedence over unavailable observations,
which remain listed in the result.

Callers must supply the complete scientific payload: state populations, charge
conservation diagnostics, signed readouts, channels, order, failure stages and
denominators, and source metadata. A match of a selected scalar cannot establish
equivalence of omitted physics or state. Hashes identify supplied data and do not
prove authenticity or calibration. Run the oracle outside the timed region unless
validation is explicitly part of the scope. Existing scientific archives and the
R0 exploratory evidence remain unchanged; R6 will address campaign reports.


## R2 bounded serial baseline campaigns

`ncmemsim.performance_execution` adds `capture_performance_environment` and
`run_serial_campaign`; `ncmemsim.performance_workloads` adds
`execute_performance_workload`. These are additive APIs; legacy benchmark outputs,
solver defaults, scientific archives and the published 1.8.0 identity are retained.

The source-tree driver `scripts/run_performance_baseline.py` builds the following
15 owned workloads. Scientific inputs include complete context/solver declarations,
protocols and states, stored manifests and requested failure indices, or embedded
archival sources. Each descriptor has a checked logical item count.

| Workloads | Declared logical items per execution | Scope |
|---|---:|---|
| V2 trajectories with 1, 2 and 3 floating gates | 1 trajectory each | Full final populations, electrostatic/charge/readout and channel outputs |
| Independent geometry DTCO | 2 ordered design points | Fresh candidate state and full trajectory per point |
| DEVICE zero/positive variation | 2 stored samples each | Zero control succeeds; varied case retains one deliberately failed workflow sample |
| MODEL zero/positive density variation | 2 stored samples each | Closed fixed-field inter-FG transport with full states, step channels and electron-conservation diagnostics |
| Electrical sequence | 4 dependent steps | Fresh owned experiment and dark readout |
| Matched optical/dark sequence | 8 dependent steps across two controls | Fixed source and common electrical history |
| Coupled thermal trajectories at 250/350 K | 1 trajectory each | Anchored Si thermal material context |
| Independent multilevel retention | 6 level/delay probes | Three stored preparations, two independent delays |
| Strict archive restoration / bundle export | 9 archived cases each | Static nested validation; export also writes and hashes bundle files |

The DEVICE/MODEL realizations remain serial and manifest-ordered. Sampling happens
once while preparing inputs, never inside timed execution. Prepared multilevel
states are also constructed before the campaign. The stored archive retains its
original package-1.7.0 runtime identity. No historical identity is relabelled.
Assumed distributions and injected failures are numerical controls, not physical
failure rates, process yield or experimental calibration.

The registered scope is `end_to_end` within the worker: restoring owned input,
fresh state, computation, scientific projection and final finite snapshot checks.
Lazy workload dependency imports are included. Worker/interpreter startup,
environment/source capture, outer result serialization/transfer and coordinator
comparison are outside workload elapsed time. Launch-to-response lifecycle time
is retained separately for each trial; campaign lifecycle also includes cleanup.
These scopes differ from R0 and must not be used to infer speedups against its
single-run profiles.

Every campaign uses fresh processes: a separate serial reference, one warmup and
five measured repetitions by default. This is a cold-process baseline; the warmup
does not establish resident solver/cache warmup in subsequent fresh processes.
The default equivalence contract compares the entire finite scientific tree
exactly against the separate serial reference. It establishes same-host serial
repeatability, not an independent accuracy proof. A caller may instead supply an
owned reference and an R1 `EquivalenceContract` together; inputs and rules must
match the workload. R3 still requires justified tolerances/refinement and review
of the complete scientific outputs before accepting a changed implementation.

The driver additionally retains paired `dt`/`dt/2` results for the three nominal
and two thermal trajectories, outside performance timing. Changed workload inputs,
full results, maximum population difference and signed flat-band voltage
difference are preserved in `refinement.json`. A two-resolution difference is
not an exact-solution error bound or proof of convergence. Existing applied
scientific validation remains necessary. `--skip-refinement` explicitly records
omission; it is used for separate memory-only observation campaigns.

The default per-worker launch-to-exit limit is 120 seconds; the per-workload total
scheduling budget is 900 seconds including the reference. Every worker is bounded
by the lesser of its limit and remaining total budget. Timeout kills/reaps the
worker. Unstarted remaining indices become `unavailable`; launched failures and
timeouts remain `failed`. Complete-equivalent statistics require every declared
warmup and measurement to complete and match, with no observed budget overrun.
Completed-observation median/min/max/MAD are separately retained even when the
campaign is incomplete; these diagnostics do not become an accepted baseline.
Coordinator comparison/serialization/cleanup cannot be preempted by this timer;
observed campaign overshoot is reported and prevents complete status. Limits are
not hard RAM/disk caps. Payloads are bounded at 16 MiB and controlled trajectories
at three FGs, 257 spatial points per FG and 4096 time steps; declared logical items
are bounded at 64 and MODEL transport steps at 64. Worker logs use files rather
than unbounded coordinator capture.

Only `none` and `native_memory` instrumentation execute in R2, always with
`fresh_process` isolation. Native-memory observations use Windows
`PeakWorkingSetSize` or platform-scaled `getrusage().ru_maxrss`. They include
imports and the whole process, not only the solver or NumPy workspace. Unsupported
measurement methods remain explicit failures. These instrumented observations
are separate from uninstrumented timings. No tracemalloc-to-native-memory
conversion, hard memory cap or comparison of different trials as one trial occurs.

Environment capture records actual import path, source and distribution metadata
versions separately, Python/NumPy, OS/CPU and thread settings. The Git commit/dirty
flag is supplied by the caller (the source driver probes Git); the worker checks
its environment and normalized package-source tree digest against the coordinator.
Dirty source observations remain explicitly dirty and are not relabelled as an
exact clean commit. Hashes demonstrate consistency, not execution authenticity.

Disabled optical diagnostics sometimes use NaN in the existing solver. The R2
scientific projection preserves these named unavailable optical fields as tagged
objects; it never converts them to zero. Infinite values retain their signed
nonfinite tag. NaN in physical states or other outputs fails the workload. State
normalization and closed MODEL electron-conservation checks remain active.

Run the driver with a new output directory, for example:

```console
python scripts/run_performance_baseline.py --output results/r2-serial
python scripts/run_performance_baseline.py --output results/r2-memory --native-memory --skip-refinement --case trajectory-3fg --case strict-restore
```

Each case JSON contains the separate reference, every trial and scientific result,
equivalence outcomes, environment and complete/incomplete summary. `index.json`
links case files by SHA-256; `refinement.json` retains untimed diagnostics. Output
directories are never overwritten. This is baseline evidence, not the strict R6
campaign reporting/archive schema, and no speedup is accepted by these APIs.

CI collects the full serial suite and the two separate native-memory cases on
Ubuntu/Windows with Python 3.11/3.13, retaining artifacts even on failures. It gates
completion and scientific repeatability, without an absolute timing threshold.
Cross-host numerical/timing differences require review; host-specific timings
are not pooled. Remote evidence remains pending until this change is pushed and
the new jobs finish. Installed wheel/sdist gates separately execute a small fresh-
process baseline outside the checkout. Local distribution validation may reuse
dependencies; remote distribution jobs use clean environments.


### Local R2 evidence

The [local baseline audit](performance_baseline_audit.json) records 15 separate
serial references, 15 warmups and 75 measured trials, plus two separate native-
memory references, two warmups and ten native-memory measurements. All declared
trials completed and matched their full serial reference. Both native-memory
references also matched the corresponding uninstrumented scientific results.
Five paired time-step diagnostics retain population/readout differences without
claiming convergence. Raw case files remain in the workspace evidence directories,
linked by SHA-256 in the audit. The observed source tree was dirty on the R1
commit and is identified by its normalized package digest; it is not an exact-
commit clean CI result. These are single-host observations. Remote CI evidence
for the committed R2 change remains required before selecting R3.


## R4 owned simulated-data interchange

The [R4 contract](interoperability.md) specifies strict JSON import/export,
original-value ownership, source digests, conditions, semantic quantity distinctions,
explicit units/sign/reference/area conversions and unavailable outcomes. No external
TCAD export is available. R5 [controlled comparisons](interoperability_comparison.md)
add explicit alignment, tolerances and nine synthetic references. The recurring
R3 measurement is frozen at accepted commit `8c63a0a`; it is historical evidence,
while current tests, distributions and serial workload gates use the current tree.


## R5 controlled comparison references

The [R5 comparison contract and controls](interoperability_comparison.md) bind both
original sources and four mappings, common condition/applicability declarations
and axis/observable tolerances. Row masks, acquisition order, negative residuals
and unavailable outcomes remain visible. A subset match cannot imply complete
coverage. The nine synthetic cases are software controls, not real TCAD agreement
or experimental qualification. R3 optimization evidence remains historical and
unchanged; R6 [strict reports and bundles](performance_reporting.md) preserve
serial-campaign accounting and all comparison outcomes.


## R6 strict archives and reproducible reports

The [R6 report contract](performance_reporting.md) restores complete indexed R2
serial campaigns and R5 comparisons without worker/solver/environment replay.
All source identities, warmups, negative and unavailable results, statistics and
coverage are retained and statically checked. Timing/native-memory and host
groups stay separate. New-directory JSON/Markdown/CSV bundles verify regenerated
projections even against coherently rehashed edits. Synthetic controls remain
labelled; R3 paired artifacts retain their historical format and acceptance.


## R7 preparation and target v1.9.0

The [R7 release checklist](v1_9_release_checklist.md) records the minor-version
rationale, six additive modules/20 exports, independently pinned compatibility
for 140 published v1.8 modules and the five-campaign/nine-comparison frozen
preparation report. The source/review/archive and installed-distribution gates
are implemented. R6 exact-source CI is recorded separately from new preparation,
final-candidate, PR/main/tag and archival evidence still to be obtained.
