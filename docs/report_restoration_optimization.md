# Report restoration optimization - Phase R3

## Selection and R2 evidence

The [R3 review](report_restoration_optimization_review.json) records the decision,
predeclared acceptance conditions and the reviewed R2 artifacts. CI run
`39588960817` passed on exact commit
`6034231ffe34c374c42a43f9ac89a1a4acd7316c`: all 15 serial cases and both native-memory
cases completed on Ubuntu/Windows, Python 3.11/3.13. Artifact index and case-file
SHA-256 links were checked; the source trees were clean. Restore medians ranged
from 6.12 to 9.17 seconds and export medians from 12.23 to 18.14 seconds across
these distinct hosts. They are not pooled or interpreted as Python/OS speedups.

R3 selects one internal optimization in `ncmemsim.multilevel_reporting`.
`MultilevelReport.from_dict` first restores each typed report case, then constructs
the owned report whose constructor restores cases again. The identical immutable
source JSON therefore undergoes repeated nested reconstruction. Every separate
report operation must still validate its sources; changing data must still fail
or be independently validated.

## Scoped reuse and preserved validation

Only the canonical string returned by a successful source validation is reused.
The key contains the actual validator method and exact source text, not a digest
alone. A changed validator, kind or text is a miss. Exceptions never insert a
value. No mutable result object or caller dictionary is retained or returned from
the cache. Source JSON remains owned; case/source hashes and all outer/case/report
schema, evidence, summary and projection checks still execute normally.

A private ContextVar limits reuse to one public report restoration. The scope
is reset in `finally`, including after late validation failures; separate contexts
and later public operations start without cached source validations. Nested scope
calls reuse their enclosing operation. The cache admits at most 16 entries and a
2 MiB budget for retained text/key objects as measured by `sys.getsizeof`.
Dictionary/context/validator overhead is additional and bounded by the entry count;
this is not a hard process-RAM limit. Larger inputs transparently use full validation.
There is no process-global cross-call result cache, solver replay, new dependency,
parallel worker backend or change to physics/defaults/public signatures/archive schemas.

The retained [v1.8 API review](v1_8_api_review.json) records the post-release
compatibility amendment and the original R2 module digest. Published tag/release
identity and the frozen package-1.7.0 multilevel archive are unchanged. The review
tracks current compatible source; it does not relabel the published tag's bytes.

## Paired acceptance protocol

`scripts/compare_report_restoration.py` extracts the committed R2 baseline through
read-only `git archive`, without switching branches or changing Git state. It
verifies identical package-file membership and that `multilevel_reporting.py` is
the only changed runtime source. The original frozen archive bytes must match.
The R2 restore/export workload identities and measurement scopes are retained.

Fresh baseline and candidate processes are alternated AB/BA by pair index. Each
workload/instrumentation has one warmup pair and five measured pairs. The first
baseline warmup supplies the exact full scientific reference; every subsequent
baseline/candidate observation, including native-memory runs and warmups, must
match it. Bundle filenames, sizes and SHA-256 digests are part of the export
scientific result. No tolerance is relaxed and failed/incomplete observations
cannot be dropped to obtain acceptance. Raw responses and observation files
remain available for each declared pair; partial evidence survives CLI failure.

Predeclared local acceptance requires all exact comparisons, every measured pair
faster, at least 1.10 median workload speedup, improvement in median launch-to-response
time, and native median growth no larger than `max(4 MiB, 10% of baseline peak)`.
These are workload-specific relative gates, not an absolute wall-time threshold
or a universal performance promise. Native memory uses the same whole-process
method as R2 and is measured in separate instrumented runs. The 2 MiB private cache
budget does not replace the observed process-memory gate.

The worker launch-to-exit limit is 150 seconds; the full paired scheduling budget
is 1800 seconds by default. Git archive extraction and setup precede this budget.
Remaining time bounds each worker, while coordinator comparison and I/O overhead
are not preemptible. All 24 declared observations per case (two variants, two
instrument modes, one warmup and five measurements) are required. Source/import
paths, versions, thread settings and normalized source-tree digests are captured;
the baseline archive and dirty candidate remain separately identified.

```console
python scripts/compare_report_restoration.py --output results/r3-paired
```

The destination must be new. Run comparisons separately from heavy tests/builds;
ordinary host activity is not controlled and observations remain single-host data.
The baseline source archive has no installed project metadata of its own, so
distribution metadata may differ from source-package metadata; actual imports,
Python and NumPy are recorded separately. Only the declared unchanged dependency
interpreter and runtime source delta support this comparison.

## Gates and scope

Tests cover source/validator changes, cache bounds and lifetime, independent contexts,
invalid/duplicate/nonfinite JSON, source hash and report projection tampering,
identical cached/uncached bundle bytes, and rejected incomplete/no-gain/memory-growth
comparisons. Existing Q6/Q7 static archive, failure and deterministic export gates
remain required, together with installed wheel/sdist and documentation checks.

Dedicated CI jobs compare the committed R2 sources with the exact candidate on
Ubuntu/Windows and Python 3.11/3.13, retaining paired artifacts even on failure.
CI acceptance is distinct from local acceptance of a dirty working tree. R3
introduces no calibrated parameter, experimental qualification or TCAD agreement;
P4B/P5B/P6B remain deferred. R4 vendor-neutral import/export is the next planned stage
after review of the exact-commit R3 evidence.


## Local paired results

All 48 observations (40 measured, eight warmups) completed with exact full
scientific results. The two selected workloads passed every predeclared gate.

| Workload | Baseline median (s) | Candidate median (s) | Workload speedup | Baseline / candidate native median (MiB) |
|---|---:|---:|---:|---:|
| strict-restore | 9.384 | 4.925 | 1.91x | 67.84 / 67.68 |
| strict-export | 18.902 | 9.916 | 1.91x | 74.98 / 73.96 |

Every measured uninstrumented pair improved. Launch-to-response median also
improved and native process peaks remained within the predeclared allowance.
The candidate was a dirty working tree on the R2 commit, identified by its exact
normalized runtime source digest; these are local observations, not an exact-
commit CI result or a universal acceleration factor. The current source delta is
one runtime module. Any later runtime membership or dependency change requires
review of this isolated comparison experiment rather than automatically relaxing
its source-delta gate. The separate R2 full-workload campaign remains active.
