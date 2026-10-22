# Controlled interchange comparisons - Phase R5

R5 adds source-bound comparisons and nine synthetic reference cases on top of the
[R4 interchange contract](interoperability.md). CI and Documentation passed for
R4 commit `6e7514bf0ed54f26bc94857faaba563626ad92b0`. The R3 optimization and its
accepted historical comparison remain unchanged. R5 introduces no solver
optimization, fitted coefficient or real TCAD/experimental qualification.

## Declaration and scope

`ncmemsim.interoperability_comparison` exports `InteroperabilityComparison` and
`compare_interoperability_data`. The owned declaration embeds both original
R4 datasets, four dataset-hash-bound mappings, common target metadata, a separate
applicability review for each source and four explicit nonnegative finite
tolerances: `axis_atol`, `axis_rtol`, `atol`, `rtol`. No default tolerances are
inferred from values or units. Absolute tolerances use the corresponding mapped
target unit; relative tolerances are dimensionless. Zero is allowed.

Mapping keys are exactly `reference_axis`, `reference_values`, `candidate_axis`
and `candidate_values`. Each side uses distinct source columns for axis and
observable. Both sides must explicitly map to the same target quantity/unit for
each role. Supported axes are position, time and gate voltage. R4 retains the
semantic distinctions between flat-band shifts and threshold voltages, compact
readout and small-signal capacitance, optical transition and tunnelling energies.
A malformed or semantically invalid transformation raises an error; it cannot
become an apparently valid unavailable or matched comparison.

The target metadata follow the R4 schema. They declare the common coordinates,
references, geometry/protocol/applicability assumptions under which the analyst
wants to compare the arrays. Each source review must explain why that source is
applicable and how the explicit mapping relates it to those conditions. These
texts are declarations for review, not automatic proof that devices/protocols
are physically equivalent. Original source metadata are never rewritten to force
agreement. Unknown applicable source or target conditions yield `unavailable`.

The declaration provides strict `to_dict()`, `to_json()`, `from_dict()`,
`from_json()` and `contract_hash` with schema
`ncmemsim-interoperability-comparison-v1`. Imports reject unknown/missing fields,
changed schemas, duplicate JSON keys and nonfinite data. Reusing a mapping after
changing its source dataset is rejected until it is explicitly rebound/reviewed.

## Alignment, residuals and coverage

The comparison first performs all four explicit R4 conversions, retaining their
originals, mappings, hashes, exclusions and missing-condition outcomes. Both
original row counts and retained row-index masks must agree. There is no silent
intersection of masks, point sorting, nearest-neighbour pairing, interpolation,
smoothing or refitting. Converted coordinates are compared in acquisition order.
A coordinate outside the declared axis tolerance yields an unavailable value
comparison; coordinate diagnostics remain visible.

For reference value `r` and candidate value `c`, the declared test is:

`abs(c - r) <= atol + rtol * abs(r)`

The same reference-relative formula applies to axes with their own tolerances.
The boundary is inclusive. Python integer/float values are compared using exact
rational arithmetic on their stored numeric representations, after the R4 unit
conversions. This avoids overflow in residual/tolerance arithmetic; it does not
remove floating-point rounding in the original data or conversions.
Signed residual is `candidate - reference`. Per-row signed/absolute residuals,
limits and maximum absolute residual are exported as numerator/denominator
**decimal strings** so extreme finite input values cannot overflow JSON floats.
Reference/candidate numeric values remain available alongside each decision.

Results have these statuses:

| Status | Meaning |
|---|---|
| `matched` | Every assessed retained row satisfies its observable tolerance |
| `mismatched` | At least one assessed row violates its observable tolerance; all negative results remain |
| `unavailable` | Missing applicable conditions, no retained rows, different row masks/counts or incompatible grids prevent assessment |

Every result preserves the complete declaration and conversions, named reasons,
per-source original/retained/excluded counts and exclusion reasons, axis/value
rows and assessed/matched/mismatched counts. `scope="retained_rows_only"`,
`full_coverage` and `assessed_fraction` distinguish a subset match from complete
coverage. `full_coverage` describes absence of exclusions, not successful
assessment. Unavailable comparisons have zero assessed rows, not zero error.
These are fresh JSON-compatible projections; strict report/bundle restoration
is provided by [R6 reports](performance_reporting.md). Neither `experimental_qualification` nor `external_agreement`
is set true by this comparison.

## Reproducible synthetic controls

Run from the repository root, choosing a new output filename:

```console
python -m examples.phase_r5_interoperability_reference --output r5-controls.json
```

The example refuses to overwrite an existing output file. It retains the exact
synthetic upstream JSON texts and their verified SHA-256 digests. Every dataset
and comparison declaration passes through the strict JSON interchange readers.
The prescribed linear profiles are software controls; they are not device/PDE
predictions or an independent physical validation oracle.

| Case | Expected result |
|---|---|
| nm to m, explicit axis reversal, total charge divided by source area | Matched |
| Deliberately changed charge-density point | Mismatched, one negative row |
| Missing source area for total/per-area conversion | Unavailable |
| Missing source frequency for small-signal capacitance | Unavailable |
| Reordered source grid | Unavailable; no automatic sorting |
| Different exclusion masks | Unavailable; no silent intersection |
| Identical exclusions on both sides | Matched retained subset, 2/3 coverage |
| Missing common coordinate declaration | Unavailable |
| Small perturbation inside declared tolerance | Matched |

The tests additionally exercise source binding, ownership, strict readers,
semantic substitution rejection, invalid tolerances, exact tolerance boundaries,
negative signed residuals, all-row exclusion, different lengths and residuals
larger than the finite float range. Separately installed wheel and sdist probes
run all nine example controls outside the source checkout. R1-R4 regression,
API/archive identity and documentation gates remain active. Real TCAD comparisons
still require source files and reviewed observable/protocol mappings; P4B/P5B/P6B
experimental qualification remains deferred. Package/citation identity stays 1.8.0.
