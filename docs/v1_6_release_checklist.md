# v1.6 Phase O7 candidate and release checklist

Status: O7 preparation is implemented; release approval remains pending. O7 is not complete.
Final candidate identity: `1.6.0`; Citation date: `2026-10-08`.
Publication and version-specific DOI remain pending.
Latest published stable: `1.5.0`, with date 2026-10-06 and author-confirmed version DOI `10.5281/zenodo.23189313`.
CITATION.cff now describes the final 1.6.0 candidate without a version-specific DOI; Concept DOI `10.5281/zenodo.23078330` remains separate. No v1.6-specific DOI is assigned before deposit.

## Reviewed scope

O6 implementation: `13b05572567d5124079372f295b39dc6547595e8`.
O6 CI and Documentation passed on this exact commit. Published v1.5 tag:
`53d7c0b9bfa2be5e75aa3a6813c8e33be068843d`; DOI closure source:
`46965a3d7ed86fd64223b587db71500f4a7e7e44`.
Historical identity fixtures are captured from the O6 baseline, retaining published v1.5 declarations. They overlay declarations on current retained contracts; they are not full historical checkouts and do not rewrite tags/assets.

Five structural modules and their explicit qualified exports are reviewed in `v1_6_api_review.json`.
The 297 stable paths, 59 ensemble exports, MODEL, thermal and spectral contracts/archives are retained.
The frozen development archive is an all-failed reporting population, with complete requests and undefined pulse statistics. Installed probes also exercise completed optical/pulse evidence independently. This archive is not the O5 numerical population or a published-v1.6 archive.

Scientific status remains conditional and unqualified. Hydrostatic strain-induced optical transition shifts and kinetic spherical infinite-barrier EMA confinement are separate diagnostics. Coefficients, masses, applicability and additive composition remain ASSUMED; no qualified Ge NC preset, Coulomb/excitonic/shear/finite-barrier correction, transport band-offset correction, calibration or yield claim is introduced. Stored alpha/state observations are authoritative evidence; projection consistency and hashes do not independently validate trajectories or authenticity.

## Required checks

- Full local regression: `python -m pytest -q`.
- Source inventory: `python scripts/validate_api_contract.py`.
- Candidate/retained review: `python scripts/validate_v1_6_api_review.py`.
- Documentation: `python scripts/validate_documentation.py`.
- Installed wheel/sdist: `python scripts/validate_dtco_distribution.py`.
- Offline local `--reuse-dependencies` installs artifacts separately with inherited dependencies; clean dependencies remain a remote CI gate.
- Supported matrix: Python 3.11, 3.12 and 3.13, tests and installed distributions.
- Structural installed probes verify installed import locations, no-replay archive restoration, deterministic bundle export and coherent tamper rejection.

## Verified local preparation evidence

- Full local regression: 4190 passed in 1552.69 seconds on Python 3.13.12.
- Candidate/historical identity gate selection: 52 passed in 65.28 seconds.
- Source inventory: 125 modules and 222 documented import paths; five structural modules and 22 exports reviewed, 297 stable paths and 59 ensemble exports retained.
- Strict documentation: 53 pages, zero errors; 133 complete Python blocks and 482 checked imports.
- Wheel/sdist independently installed as 1.6.0.dev0: workflow, MODEL, thermal, spectral and structural probes passed. 336 source files audited.
- Local distributions inherited dependencies; this does not replace the clean remote matrix.

These results precede the preparation commit. Exact-commit remote CI/Documentation must pass separately; final 1.6.0 candidate and publication checks remain pending.

## Publication sequence still pending

1. Commit/push preparation and verify all six CI jobs plus Documentation.
2. Prepare final 1.6.0 candidate identity, citation date and release gates; rerun affected checks and exact-commit CI.
3. Create/review PR, merge after green checks, verify main.
4. Create annotated v1.6.0 tag on the verified merge commit and wait for release workflow/assets.
5. Confirm published GitHub release and actual Zenodo deposit; record version DOI without moving the tag.
6. Close O7 only after publication, DOI and final metadata CI are verified.

## Final candidate preparation

O7 development preparation passed all six CI jobs and Documentation on `dcee61c47f62659f95e5c6c6bb54d4d14ee3f5c0`. The earlier 4190-test regression covered unchanged runtime contracts at 1.6.0.dev0. Final identity and installed version checks are performed separately; the final commit requires its own full remote CI. Final candidate metadata does not close O7 or claim publication.
