# v1.0 release readiness

> **Historical evidence/contract:** Version-specific counts, decisions and gates below retain their original scope. They do not describe outstanding v1.10 release work. See [current platform status](platform_status.md).

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

The candidate readiness flag is therefore `ready_for_candidate=true` for the v1.0.0 release state promoted to `main`.

This means the repository has retained evidence for the v1.0.0 release. The
release tag and GitHub assets remain explicit publication actions. No DOI or
external deposit is claimed; one may be added later if independently assigned.
