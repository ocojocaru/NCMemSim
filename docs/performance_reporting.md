# Performance and interchange reports - Phase R6

R6 provides strict static archives of R2 serial performance campaigns and R5
interchange comparisons. R5 CI and Documentation passed on
`0796d4c4f673d09160bbf26dc8d14b10d6d83ce9`. No package/citation version changes.
R3 paired speedup artifacts keep their original historical format and acceptance
review; they are not relabelled as serial campaigns or used to infer a new speedup.

## Owned archives and complete trial accounting

`ncmemsim.performance_reporting` exports `PerformanceCampaignArchive`,
`PerformanceInteroperabilityReport`, `write_performance_interoperability_report`
and `load_performance_interoperability_bundle`.

A `PerformanceCampaignArchive(campaign, evidence_kind, notes)` owns one complete
R2 `serial-performance-campaign-v1` record. `evidence_kind` must explicitly be
`observed_campaign` or `synthetic_control`. These are caller declarations, not
certifications. Synthetic controls can contain invented timings/memory/environment
fields only when labelled and explained as such. An observed timing on an assumed
device is still not a calibrated device prediction or experimental evidence.

Archives retain the workload, protocol, environment, normalized package source
hash, reference origin/result/failure/lifecycle, equivalence declaration, every
warmup and measured trial, full scientific outputs, comparisons and limitations.
They require exactly every declared phase/index in original order. Missing,
duplicate or reordered trials are rejected; failed/unavailable rows cannot simply
be removed to improve a median or denominator.

Restoration strictly reconstructs R1 declarations, checks source/workload/protocol/
environment links and result hashes, recomputes full scientific comparisons and
rebuilds R2 counts, medians/min/max/MAD, complete-equivalent statistics and budget
flags. Completed-observation statistics remain diagnostic when a campaign is
incomplete. Warmup failure prevents completeness even if every measured trial
succeeds. Unstarted trials retain null observations and a reason. Failed launched
trials retain lifecycle, available timings and partial scientific output.

Workload timing cannot exceed its worker lifecycle. The sum of retained worker
lifecycles cannot exceed the campaign interval, allowing only a relative 1e-9
rounding margin with a one-second floor for the interval check. This is an
archive consistency guard, not a physical or measurement tolerance. The original
R2 budget/summary semantics and limitations remain unchanged. Memory observations
require explicit isolated native-memory instrumentation and positive process RSS
for completed native trials; uninstrumented trials cannot invent memory data.

The archive schema is `performance-campaign-archive-v1`. Both archive and report
classes provide `to_dict()`, `to_json()`, strict `from_dict()`/`from_json()` and
`contract_hash`. Unknown fields, duplicate JSON keys, nonfinite values and changed
source/derived projections are rejected. Source commit/dirty flags and evidence
kinds remain declarations. Hashes verify consistency, not authenticity.

## Combined report

`PerformanceInteroperabilityReport(title, campaigns, comparisons)` accepts ordered
labelled lists. Campaign entries contain `label` and a typed/archive-dictionary
`archive`; comparison entries contain `label` and a typed/declaration-dictionary
`declaration` from R5. Labels must be globally unique. A report needs at least one
case; campaign-only and comparison-only reports are supported.

The `performance-interoperability-report-v1` schema owns all original campaign
records and all comparison declarations, regenerated results and hashes. Its
summary keeps each campaign environment, source identity, instrumentation,
reference failure, warmup status counts and original campaign statistics separate.
No host/workload/protocol pooling occurs; `pooled_statistics` remains null and
`speedup_accepted`, `external_agreement` and `experimental_qualification` remain
false. Different native-memory and uninstrumented cases remain separate rows.

R5 residuals, tolerances, source conversions, unavailable reasons, retained/excluded
counts and coverage remain intact. A matched retained subset still does not
establish complete coverage. An unavailable comparison has zero assessed rows,
not zero error. At load time, R5 results are regenerated from the owned sources
and mappings. Changing a claimed result and updating its hash does not bypass
these checks. Changing every source and declaration coherently is a new declared
case, not something a consistency hash can authenticate or forbid.

## Reproducible bundle

The writer creates a **new** directory and refuses to overwrite existing content.
It exports the following UTF-8 files with deterministic LF projections:

| File | Contents |
|---|---|
| `report.json` | Complete owned report, sources, reference/trial results and comparisons |
| `report.md` | Campaign/comparison overview and limitations |
| `campaigns.csv` | Source/environment/protocol identity and per-campaign statistics |
| `trials.csv` | Every warmup/measurement, status, timing, memory, failure and comparison |
| `comparisons.csv` | Positive/negative/unavailable outcomes and coverage accounting |
| `residuals.csv` | Ordered axis/value decisions, quantity/unit and exact rational residual/tolerance fields |
| `bundle.json` | Bundle schema, report hash and exact SHA-256 file inventory |

JSON preserves null; undefined numeric CSV cells stay empty. Rational residual
numerators/denominators remain decimal strings, preserving extreme finite cases.
The bundle schema is `performance-interoperability-bundle-v1`.

The loader requires exactly the expected ordinary files and rejects symlinked
roots/entries, missing/extra files and directories in place of files. It strictly
restores JSON, regenerates all projections and checks the manifest and exact file
bytes. Updating a CSV/Markdown file and its manifest digest still fails. This is
static validation: no worker, clock, environment probe, random draw or scientific
solver is rerun. JSON comparison arithmetic and descriptive statistics are
recomputed; hashes do not prove the original measurements were authentic.

## Reference and verification

The example includes four explicitly synthetic campaigns (complete serial,
separate native-memory, partial failure and all-unavailable) plus the nine R5
synthetic controls. Run from the repository root with a new directory:

```console
python -m examples.phase_r6_performance_report --output r6-controls
```

To add an actual bounded fresh-process timing campaign on an assumed device,
supply the observed source commit explicitly. `--source-clean` is a caller
assertion; omit it for a dirty tree. In the following command, replace `COMMIT_SHA`
with the full 40-character source commit before running it:

```console
python -m examples.phase_r6_performance_report --include-observed --source-commit COMMIT_SHA --output r6-observed
```

Timing observations are nondeterministic; two new measurements can produce
different report hashes. Re-exporting **the same owned report** is byte-identical.
Examples and wheel/sdist probes restore the bundle without simulation replay.
Tests include partial/all-unavailable records, complete trial indices, source/hash
links, changed summaries/comparisons, coherently rehashed file edits, membership,
strict JSON and restoration with workers/environment probing disabled. Retained
historical R2 serial and native campaign records also restore without relabelling
their original environments or source identities.
