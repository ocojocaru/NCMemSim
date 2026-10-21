# v1.8 Q7 release preparation checklist

Status: Q7 is complete; release and Zenodo archival verified.
Published identity: `1.8.0`; citation date: `2026-10-20`.
Latest published stable: `1.8.0`. Version DOI: 10.5281/zenodo.23510004.
Experimental P4B/P5B/P6B qualification remains deferred.

## Approved scope and frozen surface

Q1-Q6 add owned electrical sequences, declared-order multilevel separation,
fixed-reference gradual-update metrics, explicit fixed-spectrum optical steps
and matched dark controls, bounded dark retention/FG-fraction ensemble adapters,
and strict source-linked reports. Eight additive module-qualified modules and
34 exports are reviewed in `v1_8_api_review.json`. Retain the 297 stable paths,
59 ensemble exports and published 1.7/structural/MODEL/thermal/spectral archives.
No new independent measured dataset or calibrated parameter is admitted.

Weight proxies are not conductance or circuit MAC. Assumed separation, short
retention probes and synthetic ensembles establish no universal capacity,
lifetime, endurance, read/cycle noise or manufacturing yield. Q5 accepts Q3
electrical preparations and only FG electrically-active/NC-volume fractions;
nominal-context weight mappings are not rebound. Case counts are not independent
statistical samples. Optical budgets are not total programming energy.

## Preparation archive

`tests/fixtures/archives/v1_8_preparation/multilevel_report.json` contains nine
compact synthetic cases covering all eight result families, including reversed
levels and undefined paired metrics. It was captured with package identity
1.7.0 before v1.8 identity work. It is not fabricated as a published or development
1.8 archive. Original observations, states, context/source hashes and runtime
versions remain authoritative and are not rewritten on restore.

## Required local and remote checks

- Q7 review/source/archive consistency, retained v1.7 review and scientific limits.
- Full local regression and strict documentation/example audit.
- Wheel and sdist built from this source, separately installed outside the checkout;
  every package module must import from the new environment, including the eight
  multilevel modules. Audit required source-release files against source contents.
- Installed probes restore frozen sources without solver integration, material
  absorption sampling or RNG generation; reexport all seven bundle files
  byte-identically and reject coherently rehashed CSV projection changes.
- Supported clean remote matrix: Python 3.11, 3.12 and 3.13, tests and distributions.
- Local `--reuse-dependencies` is inherited-dependency evidence only; it does not
  replace clean remote installation checks on the exact committed source.

## Local preparation evidence (2026-10-20)

- Python 3.13.12: 13 dedicated Q7 tests passed.
- API consistency: 140 modules and 262 documented import paths; Q7 reviews eight
  additive modules/34 exports and retains 297 stable paths/59 ensemble exports.
- Documentation: 61 rendered pages, 10,676 local references, zero errors;
  141 complete Python blocks and 526 imports checked.
- Wheel and sdist separately built/installed: all retained and multilevel probes
  passed; 394 source files audited. Local dependency mode was `inherited`.
- Nine-case preparation archive contract hash:
  `0279307ed825eb00c9b94d2b3fb70ec4edb64e359c8f7dea9c1cca39e3d65880`.
- Full 4,855-test regression attempted: 4,842 passed in 2,523.82 s; 3 failures
  and 10 setup errors were all `OSError: [Errno 28] No space left on device`.
  After clearing old pytest scratch files, both affected files were rerun:
  63 passed in 28.48 s, covering all 13 affected tests. No unresolved test failure
  remains; this is full-suite coverage plus an environmental retry, not one
  uninterrupted green run. Clean exact-commit CI remains required.
- The preparation commit subsequently passed CI/Documentation; see the final
  candidate checkpoint below for the current identity and pending gates.

## Publication sequence - completed (2026-10-21)

1. Preparation ef3db53 and final candidate d2049a3 passed CI/Documentation,
   including Python 3.11, 3.12 and 3.13 test and clean-distribution jobs.
2. PR #11 passed checks and merged into main at
   `03b35f40606dbd84c1cd6d715eb6de6222466b47`; main CI/Documentation passed.
3. Annotated tag v1.8.0 points to that exact commit; tag CI and Release passed.
4. Published assets: ncmemsim-1.8.0-py3-none-any.whl (429790 bytes;
   SHA-256 79fdcfcefaeeb7a1393124d833761ca6b67cc9a6aa2008c8d1905b0833fa62d0)
   and ncmemsim-1.8.0.tar.gz (2216520 bytes;
   SHA-256 ca793332baf5d415bd489c439ed57808a7f08b5a1e7d049b76326b2dcbc6f7a8).
5. Zenodo record 23510004 identifies v1.8.0, publication date 2026-10-20 and
   the GitHub tag; version DOI is 10.5281/zenodo.23510004. Concept DOI stays separate.

Publication closes Q7 release gates, not experimental P4B/P5B/P6B qualification.
The following candidate checkpoint is historical evidence, superseded by the
verified release above. Metadata closure does not move tags or replace assets.

## Final candidate checkpoint (2026-10-20)

Preparation commit `ef3db539489f523241a2aada4183deb3a29158c5` has successful CI
and Documentation. Candidate source and CITATION.cff now use 1.8.0; the latest
published stable release remains 1.7.0. The 1.7 publication metadata and workflows
are frozen in `tests/fixtures/releases/v1_7_0`; retained gates check those
declarations with the current retained runtime contracts. The nine-case
preparation archive remains package 1.7.0 and is not relabelled.

Candidate local verification (Python 3.13.12):

- Full 4,875-test suite: 4,873 passed in 2,793.99 s; two Q7 review-consistency
  tests failed because the process had loaded the policy text before its final
  review update. This was a stale loaded validator, not a runtime physics change.
- Fresh process on the final sources: all 64 candidate/Q7/retained-v1.7 tests
  passed in 223.65 s, including both affected tests. No unresolved failure remains.
  Evidence is full-suite coverage plus this fresh retry, not a single uninterrupted
  green full-suite run; exact-final-candidate clean remote CI remains required.
- API/identity validators passed; 297 stable paths and 59 ensemble exports retained.
- Strict documentation audit passed: 61 pages, 141 complete Python blocks and
  526 imports. Wheel and sdist separately installed with inherited dependencies:
  all retained/multilevel probes passed; 406 required source files audited.
- All 11 declaration snapshots match preparation commit ef3db53 after normalizing
  text line endings. They capture declarations at that checkpoint, not an entire
  checkout of the published v1.7 tag.

Its exact new commit still requires
Python 3.11, 3.12 and 3.13 CI/Documentation, followed by PR/main/tag/publication.
The actual version-specific DOI is recorded after publication; no previous
version DOI or Concept DOI is substituted for it.
