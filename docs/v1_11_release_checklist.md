# NCMemSim v1.11 release preparation

Phase T7 targets **v1.11.0**. The release adds nine exports across four
module-qualified APIs for finite spherical-well declarations, isolated
evaluation, opt-in Ge optical composition and reporting. The preparation
package identity is v1.10.0. The [Phase T study documentation](finite_confinement.md)
describes the physical assumptions and reproducibility limits.

The compatibility check compares the current package sources against published
v1.10.0 commit `ba1b9ea9563f3786fb4af96215606b103a2925a2`. It checks the
published API review and verifies the exact T module exports. The installed
distribution gate exercises the synthetic T6 report from wheel and sdist
installations. Each environment writes and restores its own bundle because T6
requires exact numerical agreement at restoration.

## Release gates

- [x] Select v1.11.0 for the additive Phase T surface.
- [x] Add source, API and installed distribution checks.
- [ ] Pass CI and Documentation for the preparation commit.
- [ ] Set final package and citation identity, and adapt the historical v1.10
      identity checks to validate their published evidence.
- [ ] Pass CI and Documentation for the final candidate and its merged commit.
- [ ] Publish the annotated tag and verify the release artifacts.
- [ ] Record the version DOI and confirm archival metadata.
