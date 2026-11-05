# Isolated barrier reports and reproducibility bundles - S6

> **Release context:** Included in published NCMemSim v1.10.0. See [current platform status](platform_status.md) for implemented extensions and limits. Earlier phase/version statements identify their original checkpoint or retained default path.

S6 adds three module-qualified exports in `ncmemsim.barrier_reporting`:
`BarrierStudyReport`, `write_barrier_study_report`, `load_barrier_study_bundle`.
Existing package-root and transport exports remain unchanged. The schema archives
isolated S2 evaluations; S4 transport-step histories are not accepted as evaluations.
No simulator/provider callback, field solve or transport update runs on restoration.

## Original sources and strict restoration

A report owns a nonempty ordered list of uniquely labelled cases. Each case holds
the full S2 result, arbitrary native finite JSON settings, an optional finite
nonnegative reference exponent and a required reference description. Settings and
references are caller declarations; the archive does not verify their physical
meaning or infer that they generated the profile. The S2 request remains the
authoritative record of SI energies, incident energy, lengths, masses, orientation,
provenance, approximation, numerical tolerances and applicability limits.

Each result retains its source request/profile hashes, constants, segment actions,
exponents, log transmissions, transmission categories and failures. S2 restoration
checks isolated diagnostics using its existing fixed four-ULP portability budget;
it recomputes the compact segment action, not a device trajectory. Original accepted
floating-point values are preserved. Report restoration reconstructs case hashes,
comparisons and summary counts, rejecting changed projections, missing/unknown
fields, duplicate JSON keys and nonfinite data. Declared source identities and
references are not authenticated, and a coherently rewritten report is a different
declaration, not something a hash can prove fraudulent.

Comparisons use the original request's inclusive exponent tolerance. Exact binary
rational arithmetic avoids overflow in differences and tolerance sums. Exact error
and limit ratios are retained; their optional float projections are null when not
representable. Failed evaluations or absent references produce unavailable
comparisons with explicit reasons. Underflow with finite B/log T remains completed.
Counts include every row; mismatched and unavailable cases are not discarded.
No model uncertainty, current, lifetime, yield or experimental qualification follows.

## Example and exported files

Run `python examples/phase_s6_barrier_report.py --output new-bundle-directory`.
The example carries all 31 S5 rows and two explicitly synthetic archive controls:
one deliberately mismatched reference and one absent reference. Expected counts:
33 attempted, 32 completed, one failed; 30 matches, one mismatch, two unavailable;
one completed transmission-underflow case. The negative reference is an archive
control, not a failure of the S5 numerical acceptance evidence.

The new directory contains exactly `report.json`, `report.md`, `cases.csv`,
`segments.csv` and `bundle.json`. JSON retains full original sources. Markdown is
an escaped summary; CSV retains case settings, comparison details and ordered
segment diagnostics. Undefined numeric CSV cells are empty; JSON retains null.
The manifest binds the report hash and every projection's bytes. Output is
deterministic, without added clock timestamps or destination-dependent data.
Writing refuses an existing destination. Loading rejects extra/missing members,
symlinked members/directories, non-file members, modified projections or a changed
manifest. It validates consistency, not authenticity or an adversarial filesystem.

The [S5 sensitivity study](barrier_sensitivity.md) remains conditional numerical
evidence, and [S4 integration](barrier_transport_integration.md) retains its separate
snapshot/geometry contract. Published package/citation identity is 1.10.0, dated 2026-11-05; S7 is complete.
