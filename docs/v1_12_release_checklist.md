# Phase U7: v1.12 release preparation

Target release: `1.12.0`. Preparation identity was `1.11.0`.
Candidate identity: `1.12.0`, dated 2026-11-27.
Latest published stable is v1.11.0. The candidate is not yet published.

## Scope and compatibility

The additive surface comprises two module-qualified APIs and four exports:
the isolated first-order direct electron–hole Coulomb evaluator and owned
direct-Coulomb reports with bundle writing and restoration. The
[source review](v1_12_api_review.json) pins every published v1.11 package
source to tag commit `77c4c982084383791511eb45fa128974e26b0044` and records
the two new module hashes and explicit exports. Preparation rejects changed,
missing or extra runtime modules. Source text hashes use UTF-8 with LF line endings, so Windows checkout line endings do not change compatibility results. No existing charge or voltage convention changes.

The uniform-screening direct term is a declared-model diagnostic. U2–U5
provide synthetic energy-scale and selected bound-channel studies. They do
not establish complete perturbative convergence, an interacting-pair solution,
experimental calibration or qualified optical integration. Higher channels,
continuum coupling, dielectric mismatch, polarization and exchange remain outside
the model. U4/U5 study files retain separate formats; U6 restores direct results.
Independent experimental P4B/P5B/P6B qualification remains deferred. The legacy stored-charge conversion uses the positive normalized quantity q N_eff m; with m = (P1 + 2 P2)/2 and N_eff counting physical active nanocrystals, the signed electronic density is -2 q N_eff m. The manuscript convention discussion does not change this baseline implementation. A separate electrostatic review and regression are required before interpreting that quantity as physical signed charge or comparing resulting voltages with measurements. The isolated Coulomb evaluator does not use this conversion.

## Gates

- [x] Define the additive target and retain the published package identity.
- [x] Add reviewed source hashes, API membership checks and negative gate tests.
- [x] Add isolated installed-package U6 round-trip, deterministic export and
  coherently rehashed projection-tampering checks to wheel/sdist validation.
- [x] Pass local regression, strict documentation and installed distribution checks.
- [x] Preparation commit `e24cb9b8e745f8b85329e86a932ca4d33a43c53b` passed [CI](https://github.com/ocojocaru/NCMemSim/actions/runs/45841636883) and [Documentation](https://github.com/ocojocaru/NCMemSim/actions/runs/45841671830).
- [x] Declare final candidate identity, scientific scope and current limitations.
- [x] Pass local candidate identity, retained metadata, documentation and installed distribution checks.
- [ ] Commit the candidate and pass CI/Documentation on that exact commit.
- [ ] Pass candidate, PR and main checks before creating the release tag.
- [ ] Verify tag checks, release artifacts and version-specific Zenodo DOI.

Python 3.11, 3.12 and 3.13 distribution environments each create and restore their
own U6 bundle. Exact numerical restoration requires a compatible runtime;
no cross-platform frozen-result equality is claimed.

## Local preparation evidence (2026-11-26)

The complete local suite passed: 5,672 tests. The U1-U7 subset passed all
30 tests. Strict documentation validation checked 79 pages and 14,068 local
references with zero errors. The retained v1.11 identity and source gates passed.
Clean wheel and sdist installations both passed all existing probes and the new
U7 direct-report round-trip, deterministic export and rehashed-tamper rejection
probe; 516 source files were audited. These are local preparation results.
Preparation CI and Documentation subsequently passed on the exact commit recorded above. Candidate checks require their own evidence.


The source compatibility gate permits only the exact `1.11.0` to `1.12.0`
version-literal substitution. All other published source bytes and the U1/U6
module hashes remain pinned. The published v1.11 metadata snapshot is captured
from `1f6efa1fd4f57a4a404e49b2615fadec8b4f7dd4` and independently hash-checked.
Historical v1.11 tests exercise that snapshot, including its original version DOI.
The current candidate citation contains no reused or invented version DOI.

## Local candidate evidence (2026-11-27)

Candidate verification passed 97 selected identity, Coulomb and historical
compatibility tests (22 identity/preparation tests and 75 regression tests).
All retained contract/identity commands from CI passed. Strict documentation
checked 79 pages and 14,087 local references with zero errors. Clean wheel and
sdist installations passed all probes, including U7 in both environments;
526 source files were audited. The 5,672-test full preparation run and its
remote CI evidence above belong to the preparation checkpoint. Candidate
CI/Documentation and the full remote test matrix remain pending commit/push.
