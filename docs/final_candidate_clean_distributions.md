# Clean installed distribution evidence

This final candidate gate records clean installed-distribution validation for the v1.0 stability-preparation branch.

- Source branch: `prep/v1.0-stability`
- Tested commit: `03ad3915f2161f5e94cf88c5942a1b836ef30c7b`
- Final package version: `1.0.0`
- Gate status: `passed`

The validation builds both the wheel and source distribution, checks the artifact inventories with the retained distribution validator policy, installs each artifact into a separate virtual environment outside the source checkout, and runs representative installed-package probes.

The local gate intentionally uses available local dependencies instead of downloading dependencies during final preparation. This keeps the check offline and reproducible in the development environment. Supported-runtime distribution jobs were already recorded as passed in remote CI for Python 3.11, 3.12 and 3.13.

The installed probe verifies:

- package import identity resolves from the installed environment, not the source checkout;
- representative DTCO, robust DTCO and scientific workflow public imports are available from the installed package;
- release-readiness and stable-API proposal validators execute from the source tree against the final evidence state;
- frozen published v0.14.0 archive fixture readers round-trip through the installed package;
- source distribution content matches the audited source files byte-for-byte through `scripts.validate_dtco_distribution`.

This step marks `clean_installed_distributions` as passed and makes `ready_for_candidate=true` because all approved review gates and final candidate checks now have retained evidence. The final release verifier rebuilds the `1.0.0` wheel and source archive before tagging. No DOI or external archival deposit is claimed.
