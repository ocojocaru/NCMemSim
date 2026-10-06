# v1.4 Phase M7 candidate and release checklist

Status: M7 complete; v1.4.0 published.
Published identity: `1.4.0`; citation date: `2026-10-02`.
Version-specific DOI: [10.5281/zenodo.23102549](https://doi.org/10.5281/zenodo.23102549) (confirmed by the project author).
Concept DOI: `10.5281/zenodo.23078330`, retained separately.

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

## Final candidate checks

- Full regression suite: `python -m pytest -q`.
- Source inventory: `python scripts/validate_api_contract.py`.
- Candidate API: `python scripts/validate_v1_4_api_review.py`.
- Final identity: `python scripts/validate_v1_4_release_identity.py`.
- Strict documentation: `python scripts/validate_documentation.py`.
- Clean wheel/sdist: `python scripts/validate_dtco_distribution.py`.
- Offline local distribution check may use `--reuse-dependencies`; this mode
  installs NCMemSim separately but inherits dependencies and is not clean CI.
- Python 3.11, 3.12 and 3.13: both test and installed-distribution CI jobs.
- Documentation on the preparation branch and PR; development builds do not
  deploy Pages. All source notices and LICENSE/NOTICE must be packaged.

## Verified preparation evidence

Preparation commit: `dc79dd625ead691c9c3c3512ed8eebbb4a641b53`.
[CI](https://github.com/ocojocaru/NCMemSim/actions/runs/36993597402) passed all six
Python 3.11-3.13 test/distribution jobs;
[Documentation](https://github.com/ocojocaru/NCMemSim/actions/runs/36993597377) passed.
These are verified preparation results, not approval of the final candidate.

## Verified final publication evidence

Final branch/PR head: `b5f308e822e6909df82bb6047047b1856d3f64d3`.
PR [#7](https://github.com/ocojocaru/NCMemSim/pull/7) merged after
[CI](https://github.com/ocojocaru/NCMemSim/actions/runs/37001550220) and
[Documentation](https://github.com/ocojocaru/NCMemSim/actions/runs/37001550360) passed.
Release commit: `67e8791a6ec5c3a76fc8f92bcba4da614900f4f5`.
Main [CI](https://github.com/ocojocaru/NCMemSim/actions/runs/37002876523) and
[Documentation](https://github.com/ocojocaru/NCMemSim/actions/runs/37002876274) passed.
The annotated `v1.4.0` tag points to this release commit.
Tag [CI](https://github.com/ocojocaru/NCMemSim/actions/runs/37004354378) passed all
six Python 3.11, 3.12 and 3.13 test/distribution jobs.
[Release](https://github.com/ocojocaru/NCMemSim/actions/runs/37004354221) passed.
[GitHub Release](https://github.com/ocojocaru/NCMemSim/releases/tag/v1.4.0)
was published on 2026-10-02 at 12:15:51 UTC, without draft/prerelease flags.

| Asset | SHA-256 |
|---|---|
| `ncmemsim-1.4.0-py3-none-any.whl` | `405be8418ea82e27eb147bb4df6fe5f8e4323b2fe926646db7049183f34ac997` |
| `ncmemsim-1.4.0.tar.gz` | `094cf7f347ae3ec2bed956374f53c51524157593d247e77e461fe099418a54dd` |

The project author supplied the v1.4.0 DOI after publication. The Zenodo page
could not be independently accessed by the automated verification session.
The original tag and release assets remain unchanged. The subsequent citation
metadata commit may put main ahead of the release tag; its CI is a separate check.
M7 is complete. Metadata validation checks internal consistency; it does not
query GitHub or independently prove archive authenticity.
