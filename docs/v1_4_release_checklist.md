# v1.4 Phase M7 candidate and release checklist

Status: M7 preparation implemented; release approval remains pending.
Development package: `1.4.0.dev0`; candidate target: `1.4.0`.
Latest published stable/citation identity: `1.3.0`, dated `2026-10-01`.
Its specific DOI is `10.5281/zenodo.23079171`; Concept DOI is
`10.5281/zenodo.23078330`. Neither is a v1.4 version-specific DOI.

## Contract and scientific review

Implementation source: `8f7e43894fcb3328543741a2090aeb9bc37364ba` (M6).
Baseline release: `v1.3.0`, commit `4319cbc899191bd1cafbd79c4a7df20c1d490d10`.
Four additive thermal modules, Simulator integration and retained stable API
are reviewed in `v1_4_api_review.json`. All 59 stable ensemble exports and the
six MODEL module contracts are retained. Existing archive schemas remain intact.
The new thermal archive is development evidence, not a published-v1.4 archive.
Historical v1.3 snapshots reflect the citation-completed source at M6; the release
tag's original CITATION.cff predates the later DOI update and is not rewritten.

Scientific scope: opt-in anchored Si Eg/ni and bulk-Ge Gamma/L/phonon profiles.
The 250-350 K window is assumed; literature coefficients do not qualify a device.
Controlled Si and Ge references and fixed-field paired-TAT DTCO remain
conditional/synthetic. GeSn thermal laws, broadband propagation, temperature
calibration, process yield and a new TAT temperature law are outside this release.
Reports preserve authoritative observations, domains, failures and undefined
empty-population fractions without workflow/transport/RNG replay. Hashes prove
consistency, not authenticity or independent experimental qualification.

## Preparation checks

- Full regression suite: `python -m pytest -q`.
- Source inventory: `python scripts/validate_api_contract.py`.
- Candidate API/identity: `python scripts/validate_v1_4_api_review.py`.
- Strict documentation: `python scripts/validate_documentation.py`.
- Clean wheel/sdist: `python scripts/validate_dtco_distribution.py`.
- Offline local distribution check may use `--reuse-dependencies`; this mode
  installs NCMemSim separately but inherits dependencies and is not clean CI.
- Python 3.11, 3.12 and 3.13: both test and installed-distribution CI jobs.
- Documentation on the preparation branch and PR; development builds do not
  deploy Pages. All source notices and LICENSE/NOTICE must be packaged.

## Exact-commit evidence and pending publication

Preparation checks do not approve a later commit. Record the full committed SHA
and its CI/Documentation run URLs, with all matrix jobs green. A successful push
alone is not remote evidence. Run status and publication are pending until verified.

1. Commit/push preparation and check all six matrix jobs and Documentation on
   that exact SHA; review the complete branch diff.
2. Prepare final package version `1.4.0`, CITATION.cff version/date, release
   changelog and README/docs status together; retain Concept DOI separately and
   remove the v1.3-specific DOI from the new citation until v1.4 is deposited.
3. Adapt the candidate identity gate for the final state and rerun all local,
   documentation, clean-distribution and remote matrix checks on that final SHA.
4. Create/update the release PR, obtain green exact-head checks and merge using
   the existing workflow; verify the resulting main commit before tagging.
5. Tag `v1.4.0` only after identity and gates agree. Verify tag/main alignment,
   release workflow, wheel/sdist assets, deployed documentation and published release.
6. Record the actual v1.4 Zenodo DOI in citation/docs after deposit confirmation;
   retain previous release identities and rerun checks on the metadata update.

No tag, merge or release publication is performed by this preparation step.
M7 is not complete until the final candidate and publication gates are fulfilled.
