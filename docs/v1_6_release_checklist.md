# v1.6 Phase O7 candidate and release checklist

Status: O7 is complete; v1.6.0 is published.
Published identity: `1.6.0`; Citation date: `2026-10-08`.
Author-confirmed version-specific DOI: [10.5281/zenodo.23235484](https://doi.org/10.5281/zenodo.23235484).
Previous published stable: `1.5.0`, with date 2026-10-06 and author-confirmed version DOI `10.5281/zenodo.23189313`.
CITATION.cff records the published 1.6.0 identity and its author-confirmed DOI; Concept DOI `10.5281/zenodo.23078330` remains separate. The version-specific DOI was added only after the author confirmed the actual deposit.

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

These results preceded the preparation commit; final-candidate and publication checks were pending at that checkpoint. Their verified completion is recorded below.

## Publication sequence (completed)

1. Commit/push preparation and verify all six CI jobs plus Documentation.
2. Prepare final 1.6.0 candidate identity, citation date and release gates; rerun affected checks and exact-commit CI.
3. Create/review PR, merge after green checks, verify main.
4. Create annotated v1.6.0 tag on the verified merge commit and wait for release workflow/assets.
5. Confirm published GitHub release and actual Zenodo deposit; record version DOI without moving the tag.
6. Close O7 only after publication, DOI and final metadata CI are verified.

## Final candidate preparation

O7 development preparation passed all six CI jobs and Documentation on `dcee61c47f62659f95e5c6c6bb54d4d14ee3f5c0`. The earlier 4190-test regression covered unchanged runtime contracts at 1.6.0.dev0. Final identity and installed version checks passed separately; the final candidate, PR, main and tag received their own successful CI checks. That candidate metadata did not itself close O7 or claim publication.


## Verified publication and DOI closure

PR #9 merged at `eebc163ef2f17333d11d62fcbc4135bc0f9a4b1f`; all six main CI jobs and Documentation passed.
The annotated v1.6.0 tag targets that same commit. All six tag CI jobs and the Release workflow passed.
GitHub Release was published on 2026-10-08 at 09:40:38 UTC, publicly and without prerelease/draft flags,
with ncmemsim-1.6.0-py3-none-any.whl and ncmemsim-1.6.0.tar.gz.
The author confirmed version DOI 10.5281/zenodo.23235484; automated Zenodo access was unavailable.

Evidence: [main CI](https://github.com/ocojocaru/NCMemSim/actions/runs/37753775648),
[main Documentation](https://github.com/ocojocaru/NCMemSim/actions/runs/37753775796),
[tag CI](https://github.com/ocojocaru/NCMemSim/actions/runs/37756345556),
[Release workflow](https://github.com/ocojocaru/NCMemSim/actions/runs/37756345779),
[GitHub Release](https://github.com/ocojocaru/NCMemSim/releases/tag/v1.6.0),
[version DOI](https://doi.org/10.5281/zenodo.23235484).

This post-publication metadata commit does not move the tag or replace assets. Exact metadata-commit CI remains a separate check after commit/push.
