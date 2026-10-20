# Multilevel reports and bundles - Phase Q6

## Scope and scientific status

Q6 packages already typed Q2-Q5 evidence into a reviewable report. It introduces
no new physical law, fitted parameter, admitted dataset, experimental qualification,
conductance model or lifetime prediction. Published package/citation identity
remains v1.7.0 until Q7 release work. The full Phase Q scope and exclusions are
in [Multilevel and neuromorphic operation](multilevel_operation.md).

Cases retain their own contexts, read policies, reference windows, metric definitions,
assumed intervals, source hashes and exact denominators. There is no cross-case
pooling, automatic ranking, sign change, clipping or per-case reference rescaling.
A failed criterion and a failed execution retain their different source meanings.
Cases can reuse underlying trajectories (for example, a raw electrical result and
its update analysis). Report case counts and CSV row counts are not independent
experimental or statistical sample counts.

## Typed cases and strict archives

`ncmemsim.multilevel_reporting` exports five module-qualified interfaces:

| Interface | Meaning |
|---|---|
| `MultilevelReportCase` | Named, owned source result and explicit `PulseSequenceEvidence` |
| `MultilevelReport` | Ordered nonempty immutable tuple of uniquely named cases, report evidence and fixed limitations |
| `build_multilevel_report` | Build the typed report without simulation |
| `write_multilevel_report` | Create a new local bundle directory; never overwrite existing content |
| `load_multilevel_report_bundle` | Restore source evidence and check every regenerated view and hash |

A case created with `MultilevelReportCase.from_result` accepts exactly one of:

| Kind | Existing result type |
|---|---|
| `electrical` | `ElectricalSequenceResult` |
| `separation` | `MultilevelStudyResult` |
| `updates` | `GradualUpdateAnalysis` |
| `paired_updates` | `PairedUpdateAnalysis` |
| `optical` | `OpticalSequenceResult` |
| `matched_optical` | `MatchedOpticalSequenceResult` |
| `retention` | `MultilevelRetentionResult` |
| `ensemble` | `MultilevelEnsembleResult` |

Schemas are `multilevel-report-case-v1`, `multilevel-report-v1` and
`multilevel-report-bundle-v1`. Unknown fields/kinds/versions, duplicate JSON keys,
non-finite numbers, changed qualification/limitations and inconsistent summaries
or source hashes are rejected. All archived source data is validated through its
own existing strict reader; declarations are not accepted as executed results.
Every access to an exposed JSON dictionary returns a separate owned projection.

The report's scientific status is `conditional_unqualified_compact_model_studies`,
with `experimental_qualification=false`. Evidence labels describe declarations;
they do not admit measured data, authenticate experiments or qualify a model.

## Files, units and source linkage

A bundle has exactly seven ordinary files:

| File | Content |
|---|---|
| `report.json` | Authoritative report with complete original sources, requests, physical/read states, failures and source summaries |
| `report.md` | Human-readable case statuses, selected diagnostics, source hashes and interpretation limits |
| `cases.csv` | Case identity, kind, source hash, source-specific status and evidence |
| `observations.csv` | Scalar readout/weight/drift views, level/step/sample identity, selected times, status and source JSON pointers |
| `metrics.csv` | Every scalar source-summary value as typed JSON, with unit labels where defined |
| `failures.csv` | Actual typed workflow failures and their source pointers; unrelated user metadata named `failure` is not an execution failure |
| `bundle.json` | Report/source identities and SHA-256 digests of the six content files |

`source_path` is a JSON pointer **inside that case's source record**, identified by
`case` and `source_hash`; it is not a path into the report root or a filesystem
path. Full sources remain in `report.json` even if a scalar CSV does not repeat
every array element. Q4 paired branches, light/dark controls, Q5 delays and
manifest sample IDs remain explicit. CSVs do not invent observations for physical
steps that never completed.

Readouts and signed drift use V. `delta_vfb_V` and
`light_minus_dark_delta_vfb_V` are different observables, explicitly labelled.
Weights and normalized metrics are dimensionless proxies, not conductance.
Time columns distinguish selected absolute device times from requested retention
delays; blank absolute-time cells are not inferred timestamps. Covered physical
times and failure prefixes remain in the full sources and `metrics.csv`.

Blank numeric observation cells are undefined. A real zero remains numeric zero.
`metrics.csv` stores JSON `null`, booleans, strings and numbers explicitly in
`value_json`; it never replaces null with a favourable score. Its `source_path`
resolves to the exact value in the original summary. Units include V, s, J, W,
J/m2, W/m2, m-2, dimensionless values and counts where encoded by the source field.
Blank unit labels denote nonnumeric or source-defined fields, not an inferred
physical dimension. Markdown numbers are a readable projection; source JSON
retains the original observations without rounding or state rewriting.

Reports retain requested/attempted/completed/failed/missing counts and the original
assessability definitions. They do not infer manufacturing yield from passing
fractions, read noise from timestep checks, conductance from weight proxies or
retention lifetime from a few delay probes. Optical energy remains optical
accounting, not total programming energy.

## Export an existing result

The function below accepts an already executed, typed Q2-Q5 result. It only
validates and exports evidence; it does not execute a source workflow.

```python
from ncmemsim.multilevel_contracts import PulseSequenceEvidence
from ncmemsim.multilevel_reporting import (
    MultilevelReportCase, MultilevelReport, build_multilevel_report,
    write_multilevel_report, load_multilevel_report_bundle,
)


def export_existing_result(result, destination):
    evidence = PulseSequenceEvidence(
        "Declared study source", "existing result record", "synthetic",
        "Conditional compact-model result; no experimental qualification.",
    )
    case = MultilevelReportCase.from_result("Existing study", result, evidence)
    report = build_multilevel_report("Multilevel evidence", (case,), evidence)
    assert isinstance(report, MultilevelReport)
    write_multilevel_report(report, destination)
    restored = load_multilevel_report_bundle(destination)
    assert restored.contract_hash == report.contract_hash
    return restored
```

The destination must be a new directory. Source integrity checks and view
rendering finish before creation; interrupted writes remove only files created
by that write and remove its directory only when empty. Existing directories and
files are preserved.

Loading rejects a linked root, linked/non-file members, missing/extra names,
modified report data, wrong manifests and CSV/Markdown content differing from
regenerated views. Replacing a modified CSV's digest in the manifest does not
bypass source-projection comparison. A fully self-consistent new report has a
new identity; hashes are integrity checks, not authentication.

Static restoration may resolve stored device bindings and check inherited spectral
balances from archived profiles. It does not integrate occupancies, sample new
material absorption, fit parameters or invoke RNG generation. Re-exporting a
restored report produces byte-identical content under the same serialization
contract. Historical Q2-Q5 and published report schemas are unchanged.

## Applied normal and negative reference

`examples/phase_q6_multilevel_report.py` produces eleven cases from the existing
Q4 and Q5 references. It includes declared-order separation and a deliberately
reversed declaration using the same source predictions, with no new solver run
for the reversed case. The Q4 wrong-direction branch remains not assessable,
and its paired asymmetry remains null. Q5 zero-variation and assumed between-device
fraction results keep their manifest and endpoint denominators.

```bash
python examples/phase_q6_multilevel_report.py --destination q6-report
python examples/phase_q6_multilevel_report.py --input-bundle q6-report --destination q6-restored
```

The first command executes source workflows if stored reference inputs are not
supplied. To package previously saved, validated Q4/Q5 reference JSON instead:

```bash
python examples/phase_q6_multilevel_report.py --q4-input q4-reference.json --q5-input q5-reference.json --destination q6-from-sources
```

`--input-bundle` restores an existing report without source workflow execution;
it cannot be combined with the reference-input options. Each command creates a
new destination. The references remain synthetic diagnostics, not a demonstration
of experimentally qualified synaptic operation or application accuracy.
