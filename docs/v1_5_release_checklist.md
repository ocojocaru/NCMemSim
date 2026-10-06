# v1.5 Phase N7 candidate and release checklist

Status: N7 preparation implemented; release approval remains pending.
Final candidate identity: `1.5.0`; citation date: `2026-10-06`.
CITATION.cff now describes the final candidate without a version-specific DOI.
Published v1.4.0 retains date 2026-10-02 and DOI
`10.5281/zenodo.23102549`; Concept DOI `10.5281/zenodo.23078330` is separate.
No v1.5 version-specific DOI is assigned before its actual deposit.

## Review scope

Implementation source: `23cf78cd8088658c9eb95a56f46fa30d04c83b14` (N6).
Baseline v1.4 tag commit: `67e8791a6ec5c3a76fc8f92bcba4da614900f4f5`.
Published v1.4 citation metadata source: `7bf9096de2148201ab301376ce1baac786a06e08`.
Historical identity snapshots use that citation-completed source, not the original
tag citation; published tags and assets are not rewritten. Tests overlay these
identity declarations while exercising the retained contracts in the current source;
the snapshot directory is not a complete historical source checkout.

Five additive spectral modules, 24 qualified exports and complete source hashes
are reviewed in `v1_5_api_review.json`. The 297 stable paths, 59 ensemble exports,
MODEL and thermal module contracts and existing archives are retained.
The frozen archive retains two failed requests with undefined pulse statistics.
Completed stack/pulse evidence is created and restored independently by installed
probes. Neither population is the N5 eleven-attempt reference or a published-v1.5 archive.

Scientific limits: normal-incidence single-pass Beer-Lambert; transparent matrix
and explicit passive treatments; constant spectral capture. Synthetic sources,
numerical convergence and static report consistency do not qualify a device,
calibration, yield, coherent optics or independently verified solver trajectories.

## Local and installed checks

- Full regression: `python -m pytest -q`.
- Source inventory: `python scripts/validate_api_contract.py`.
- Candidate review: `python scripts/validate_v1_5_api_review.py`.
- Strict documentation: `python scripts/validate_documentation.py`.
- Wheel/sdist: `python scripts/validate_dtco_distribution.py`.
- Offline local `--reuse-dependencies` installs artifacts separately but inherits
  dependencies; clean dependency environments remain a remote CI gate.
- Supported matrix: Python 3.11, 3.12 and 3.13, tests and installed distributions.
- Spectral installed probes restore the archive without solver/optical/RNG replay,
  reject coherent projection tampering and export byte-identical bundles.

## Verified local preparation evidence

- Full local regression: 3958 passed in 959.04 seconds on Python 3.13.12.
- Source/API review: 120 modules, 203 documented imports, 297 retained stable paths,
  59 ensemble exports, five spectral modules and 24 qualified exports.
- Strict documentation: 51 pages, 8970 local references, zero errors; 128 complete
  Python blocks and 442 imports, with executable examples passing.
- Wheel and sdist independently installed as 1.5.0.dev0; legacy DTCO/workflow,
  MODEL, thermal and spectral probes passed, including no-replay restoration,
  deterministic exports and coherent tamper rejection. 308 source files audited.
- Local distribution mode inherited dependencies; this is not the clean remote matrix.

These local results precede the preparation commit. Exact-commit remote CI,
final candidate identity, main/tag/release and deposit checks remain pending.

## Remote evidence and publication sequence

N6 implementation CI passed on `23cf78cd8088658c9eb95a56f46fa30d04c83b14`:
[CI](https://github.com/ocojocaru/NCMemSim/actions/runs/37436138000) and
[Documentation](https://github.com/ocojocaru/NCMemSim/actions/runs/37436138156).
These results do not approve the later preparation/final candidate commit.

1. Commit/push preparation and verify all six matrix jobs and Documentation on its exact SHA.
2. Prepare final package/citation/date/changelog/README/docs identity together; keep
   the Concept DOI separate and wait for the actual v1.5 deposit for its specific DOI.
3. Validate final identity, full tests/docs/distributions and remote exact-head checks.
4. Create/review the release PR, verify the merge commit on main, then tag v1.5.0.
5. Verify tag/main identity, Release, assets, deployed docs and actual publication.
6. Record the author-confirmed v1.5 DOI after deposit and verify metadata-update CI.

N7 is not complete until final candidate and publication gates are fulfilled.
No merge, tag or release publication is performed by this preparation step.

Preparation CI passed on fdf491c7574dbb0470b36fcab050b90fe29dc697: CI 37441323800 and Documentation 37441323423. These results do not approve the later final candidate; its exact-commit checks remain pending.


## Verified local final-candidate evidence

Final package/citation: 1.5.0, candidate date 2026-10-06; specific DOI pending.
Full suite: 3972 passed in 948.42 seconds on Python 3.13.12.
Final identity/API gates passed; retained paths 297, ensemble exports 59,
five spectral modules and 24 exports unchanged.
Strict documentation: 51 pages, 8972 local references, zero errors; 128 Python
blocks and 442 imports checked with executable examples passing.
Wheel/sdist independently installed as 1.5.0; all legacy/MODEL/thermal/spectral
probes passed, 309 source files audited. Local dependencies were inherited;
clean supported-Python remote gates remain pending for the final committed SHA.
These results do not assert PR/main/tag/publication approval. N7 is not complete.
