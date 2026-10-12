# v1.7 P7 release preparation checklist

Status: P7 is not complete. This is a pre-identity review checkpoint.
Target release: 1.7.0. Package/citation remain published 1.6.0; no release approval.

## Approved release scope

Calibration infrastructure, declared-data admission/leakage/uncertainty contracts,
owned optical training and holdout adapters, assumed device/photo OM-2 diagnostics,
P5A numerical checks and P6A reproducibility reports. Experimental P4B/P5B/P6B
remain deferred: no new independent measured dataset or calibrated parameter is
admitted. Published figures are candidates, not newly qualified measurements.
No substrate photogeneration or measured C-V/LCR model is introduced.

Seven additive modules and their explicit qualified exports are reviewed in
v1_7_api_review.json. Retain the 297 stable paths, 59 ensemble exports and all
published structural/MODEL/thermal/spectral/archive contracts. The frozen P6A
report is preparation evidence captured while package identity was 1.6.0;
it is not fabricated as a 1.7 development or published-release archive.

## Required checks

- Source/API review and retained v1.6/P1 gates.
- Full local regression and strict documentation/example audit.
- Independently installed wheel and sdist, including source-file content audit.
- Installed P7 probes restore the frozen study/report and reexport deterministic
  bundles, reject coherently rehashed projection tampering and verify installed
  import locations without solver, optical-model or RNG replay.
- Supported remote matrix: Python 3.11, 3.12 and 3.13, tests and distributions.
- Offline local --reuse-dependencies is inherited-dependency evidence only;
  it does not replace clean remote installation checks.

## Remaining release steps

1. Commit/push this checkpoint and verify exact-commit CI/Documentation.
2. Prepare the development/final candidate identity with retained v1.6 citation
   snapshots and historical gates. Verify changed identity and installed version.
3. Review final scope/API/results; only then create PR and merge after green checks.
4. Verify main, create an annotated tag on the verified commit and verify release
   workflow/assets. No existing published tag or asset is moved/replaced.
5. Record the actual v1.7 version-specific DOI only after the Zenodo deposit;
   Concept DOI remains separate. Never reuse the v1.6 DOI as a v1.7 DOI.

Local preparation results are recorded after checks finish. This checklist alone
does not approve publication or close the experimental calibration milestone.

## Verified local pre-identity evidence

- Full regression: 4463 passed in 1919.92 s on Python 3.13.12.
- Focused preparation gates: 12 passed.
- Documentation: 58 pages, 10092 references, zero errors; 139 Python blocks
  and 511 imports checked; historical executable examples passed.
- API review: seven modules, 29 exports, 297 stable paths and 59 ensemble exports retained.
- Wheel and sdist separately installed as 1.6.0: all workflow/MODEL/thermal/
  spectral/structural and new independent/numerical probes passed;
  362 source files audited. Dependencies were inherited locally.

These results precede the preparation commit. Exact-commit remote CI/Documentation,
candidate identity, publication and actual v1.7 DOI remain pending. They do not
close experimental P4B/P5B/P6B or approve release publication.
