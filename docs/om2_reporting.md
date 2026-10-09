# P6A OM-2 numerical reports and bundles

P6A reports the assumed OM-2 numerical study implemented in P5A. P6B remains
the measured-study report/bundle stage, conditional on admitted experimental
evidence. P4B/P5B experimental gates remain open. The user approved this split;
the available experimental sources are the supplied PDFs only. Package/citation
remain published v1.6.0.

## Owned source and report contracts

`ncmemsim.om2_numerics.OM2NumericalStudy` owns the complete strict P5A study
archive. The P5A example delegates its specification, projections and restoration
to that library module; its callable names and archive format are retained.
It contains all thirteen named predictions, numerical specification/thresholds,
source identities, runtime, states, failed cases and non-assessable observables.
This contract does not fit parameters or authenticate measured data.

`ncmemsim.om2_reporting` adds `OM2NumericalReport`,
`build_om2_numerical_report`, `write_om2_numerical_report` and
`load_om2_numerical_report_bundle`. A report owns a study and title, pins the
study hash and retains mandatory scientific limitations. A source, summary,
schema, scope or hash mismatch is rejected; callers cannot remove limitations
or promote the archive into experimental qualification.

```python
from ncmemsim.om2_numerics import OM2NumericalStudy
from ncmemsim.om2_reporting import (
    OM2NumericalReport, build_om2_numerical_report,
    write_om2_numerical_report, load_om2_numerical_report_bundle,
)
```

## Six-file bundle

| File | Purpose |
|---|---|
| report.json | Owned typed report, complete study, source hash and mandatory scope |
| study.json | Complete original study and thirteen prediction archives |
| report.md | Human-readable cases, timestep checks, sensitivities, controls and limitations |
| cases.csv | Thirteen source-linked outcomes, signed contrast, failures and runtime |
| checks.csv | Refinement, sensitivity, zero-photo, product and reference-selection projections |
| bundle.json | Schema, report/study hashes and SHA-256 of the five content files |

The writer requires a new destination directory and never overwrites an existing
bundle. It uses exclusive file creation; a failed write removes only the files
and directory it just created. The reader requires exact ordinary-file membership,
rejects symlink entries and rebuilds all projections from the typed JSON source.
It compares the manifest and exact rebuilt bytes, so recalculating a hash after
changing a CSV/Markdown projection does not make the altered projection valid.
Equivalent restored reports export byte-identical bundles.

Undefined numeric outputs remain null in JSON, empty in CSV and explicitly
undefined in Markdown; they are never replaced with zero. The outside-reference
case remains completed but not assessable. A failed numerical case retains its
partial prediction/failure, does not become a passed refinement check and is
reported alongside successful cases.

## No dynamics replay and interpretation limits

Restoration checks source/step/charge/static electrostatic projections and
rebuilds numerical comparisons. It does not run occupancy integration, evaluate
an optical model, fit parameters or replay random generators. Stored trajectories
are authoritative retained observations, not authenticated or recomputed dynamics.
Hashes are integrity links, not a certification of an experiment.

All report forms retain the synthetic diagnostic status and absence of
experimental qualification. Local parameter probes are not measurement standard
uncertainties or confidence intervals. Product confounding remains visible;
no independent identifiability is inferred. Fixed-grid timestep stability is not
a rigorous error bound, complete discretization study or measured-device accuracy.
The constant-capacitance crossing is not physical Cfb/LCR extraction. Substrate
photo-response and PDF-only source/protocol gaps remain outside the model scope.

## Example

```bash
python examples/phase_p6a_om2_report.py --study om2-study.json --output om2-report
python examples/phase_p6a_om2_report.py --input om2-report --output restored-om2-report
```

The first command restores an existing P5A study and exports the report; it does
not simulate. Omitting both --study and --input explicitly runs the assumed P5A
reference before export. --study and --input are mutually exclusive, and output
must be a new directory. The second command verifies and reexports the bundle
without occupancy/optical/RNG replay. P6A supplies reproducibility infrastructure;
it does not close P6B, P4B/P5B or the independent experimental calibration milestone.
