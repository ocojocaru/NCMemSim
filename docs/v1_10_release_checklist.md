# v1.10 S7 preparation checklist

Status: S7 final candidate; not a published release.
Target release: `1.10.0`. Candidate identity: `1.10.0`.
Candidate date: `2026-11-04`. Preparation identity was `1.9.0`.
Latest published stable remains v1.9.0, DOI 10.5281/zenodo.23664613.
Concept DOI remains 10.5281/zenodo.23078330. No v1.10 DOI is assigned here.
Experimental P4B/P5B/P6B qualification remains deferred.

## Compatibility and version rationale

The proposed minor release adds four module-qualified APIs with 16 exports:
five profile/provenance contracts, two isolated evaluation exports, six explicit
transport-integration exports and three isolated-report exports. All 146 published
v1.9 module sources, public surfaces and defaults remain unchanged except the explicitly reviewed package-version literal. The independent
v1.9 source/surface fence runs before the S review is generated, so regenerating
the new review cannot silently accept changes to published runtime sources.
No major-version break is identified. Version 1.10 follows 1.9; it is not version 2.0.
New S exports are reviewed additions, not retroactive changes to historical stable
API declarations or archives.

The [API review](v1_10_api_review.json) records normalized source hashes, source
contracts and runtime exports. The preparation validator checks the complete current
inventory, retained v1.9 review, additive S surface and frozen report.

## Frozen regression evidence

`tests/fixtures/archives/v1_10_preparation/barrier_report.json` was captured from
clean S6 commit `8264b7e69ff1985716c226c466640b57c2ed96ac` with package identity 1.9.0.
That is capture provenance recorded in the review, not a claim of device measurement
or a field inside the isolated report schema. The report contains 33 synthetic rows:
32 completed evaluations and one numerical failure; 30 matched, one deliberately
mismatched and two unavailable comparisons; one completed transmission-underflow
case. The original SI requests, provenance, tolerances and failure reasons remain.
The archive is pinned by semantic hash and must not be regenerated or relabelled as
a v1.10 observation. Installed wheel and sdist probes restore and deterministically
reexport it, reject tampering and prohibit simulator/provider execution. Isolated
S2 action consistency checks remain part of restoration.

## Scientific scope

- Piecewise-linear electron action diagnostics; no coherent interface matching,
  resonances, current supply statistics or full TCAD comparison.
- Explicit S4 direct inter-FG replacements only, with current context and physical
  layer/length/contact/orientation checks; no substrate injection replacement.
- No automatic field-to-barrier law, TAT/image-force composition or inferred optical
  band-offset law. S3 negative and unavailable legacy/reference evidence is retained.
- S6 archives isolated action results, not S4 transport histories. Sensitivity is
  conditional on declared parameters, not physical uncertainty, yield or lifetime.
- No new admitted experimental data or device qualification.

## Remaining publication gates

- [x] Select additive minor target v1.10.0 and define compatibility rationale.
- [x] Capture original clean S6 archive and pin all negative/unavailable outcomes.
- [x] Add API, source, archive and installed-distribution preparation gates.
- Local focused-test, documentation and wheel/sdist results are recorded separately in the preparation validation evidence.
- [x] Preparation commit 74ce5e9: CI 41828989008 and Documentation 41828989014 succeeded.
- [ ] Require full test and clean distribution matrices on Python 3.11, 3.12 and 3.13.
- [x] Prepare final identity, preserving published v1.9 declarations in historical fixtures.
- [ ] Commit/push final candidate and require its exact-commit CI and Documentation success.
- [ ] Review PR; merge and verify the exact main commit.
- [ ] Create immutable annotated v1.10.0 tag only after main CI succeeds.
- [ ] Verify tag CI, Release artifacts and the independently assigned version DOI.
- [ ] Record confirmed DOI and close S7 with separate metadata-follow-up CI.

The historical R3 performance job stays pinned to its original experiment and is
not a Phase S speedup claim. No tag, merge, release or DOI publication is performed
by this preparation step. Local validation evidence lives outside the repository;
the checkbox for exact-commit remote results remains pending until that commit exists.
