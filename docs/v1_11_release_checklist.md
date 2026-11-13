# NCMemSim v1.11 release preparation

Phase T7 targets **v1.11.0**. The release adds nine exports across four
module-qualified APIs for finite spherical-well declarations, isolated
evaluation, opt-in Ge optical composition and reporting. The preparation
package identity was v1.10.0. Candidate identity: `1.11.0`, dated 2026-11-11. The [Phase T study documentation](finite_confinement.md)
describes the physical assumptions and reproducibility limits.

The compatibility check compares the current package sources against published
v1.10.0 commit `ba1b9ea9563f3786fb4af96215606b103a2925a2`. It checks the
published API review, the exact T module exports and the candidate version literal. The installed
distribution gate exercises the synthetic T6 report from wheel and sdist
installations. Each environment writes and restores its own bundle because T6
requires exact numerical agreement at restoration.

## Release gates

- [x] Select v1.11.0 for the additive Phase T surface.
- [x] Add source, API and installed distribution checks.
- [x] Preparation commit `7c85672` passed [CI](https://github.com/ocojocaru/NCMemSim/actions/runs/42930232461) and [Documentation](https://github.com/ocojocaru/NCMemSim/actions/runs/42930232422).
- [x] Set candidate identity and verify the historical v1.10 identity against the published metadata snapshot.
- [ ] Pass CI and Documentation for the final candidate and its merged commit.
- [ ] Publish the annotated tag and verify the release artifacts.
- [ ] Record the version DOI and confirm archival metadata.
