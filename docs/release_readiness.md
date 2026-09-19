# v1.0 release readiness

This page records the machine-readable readiness state in `docs/release_readiness.json`.

All v1.0 stability-preparation review gates are approved:

- API surface
- result semantics
- archive read policy
- scientific defaults
- distribution contract
- scientific scope
- archival and citation plan

All final candidate checks are now passed:

- full local regression
- strict documentation audit
- clean installed distributions
- supported runtime CI
- remote documentation

The candidate readiness flag is therefore `ready_for_candidate=true` for the current `prep/v1.0-stability` preparation branch state.

This means the branch has retained evidence for v1.0 candidate preparation. It does not create a v1.0 tag, GitHub release, DOI, archival deposit or final public documentation deployment by itself. Those remain final release actions after the candidate branch is merged or otherwise promoted.
