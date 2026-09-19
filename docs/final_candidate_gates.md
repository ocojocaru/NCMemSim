# Final candidate gates

The v1.0 stability-preparation review gates are approved and the final candidate checks are now complete for the current preparation branch.

Required final checks:

| Check | Required state | Evidence |
| --- | --- | --- |
| Full local regression | `passed` | `docs/final_candidate_local_regression.md`, `docs/final_candidate_local_regression.json` |
| Strict documentation audit | `passed` | `docs/final_candidate_strict_documentation.md`, `docs/final_candidate_strict_documentation.json`, `scripts/validate_documentation.py` |
| Clean installed distributions | `passed` | `docs/final_candidate_clean_distributions.md`, `docs/final_candidate_clean_distributions.json`, `scripts/validate_clean_distribution_gate.py` |
| Supported runtime CI | `passed` | `docs/final_candidate_remote_evidence.md`, `docs/final_candidate_remote_evidence.json` |
| Remote documentation | `passed` | `docs/final_candidate_remote_evidence.md`, `docs/final_candidate_remote_evidence.json` |

`docs/release_readiness.json` is the machine-readable source of truth. It now records `ready_for_candidate=true` because every approved review gate and every required final candidate check has retained evidence.

This preparation state is still not a v1.0 release. Creating the v1.0 tag, publishing the release, deploying final public documentation, and completing any external archival deposit or DOI update remain separate release actions.
