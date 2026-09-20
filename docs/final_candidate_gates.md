# Final candidate gates

The v1.0 review gates are approved and the final candidate checks are complete for the release promoted to `main`.

Required final checks:

| Check | Required state | Evidence |
| --- | --- | --- |
| Full local regression | `passed` | `docs/final_candidate_local_regression.md`, `docs/final_candidate_local_regression.json` |
| Strict documentation audit | `passed` | `docs/final_candidate_strict_documentation.md`, `docs/final_candidate_strict_documentation.json`, `scripts/validate_documentation.py` |
| Clean installed distributions | `passed` | `docs/final_candidate_clean_distributions.md`, `docs/final_candidate_clean_distributions.json`, `scripts/validate_clean_distribution_gate.py` |
| Supported runtime CI | `passed` | `docs/final_candidate_remote_evidence.md`, `docs/final_candidate_remote_evidence.json` |
| Remote documentation | `passed` | `docs/final_candidate_remote_evidence.md`, `docs/final_candidate_remote_evidence.json` |

`docs/release_readiness.json` is the machine-readable source of truth. It now records `ready_for_candidate=true` because every approved review gate and every required final candidate check has retained evidence.

Publishing the v1.0.0 tag and GitHub release remains an explicit release action.
No external archival deposit or DOI is required or claimed for this release.
