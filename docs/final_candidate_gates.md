# Final Candidate Gates

This page defines the final v1.0 candidate gate plan. The package remains
`0.14.0` on `prep/v1.0-stability`; this preparation step configures the gates
but does not run or pass them.

The machine-readable gate plan is
[final_candidate_gates.json](final_candidate_gates.json).

## Required Gates

The candidate can become ready only after all five final checks pass on one
exact final source identity:

1. Full local regression.
2. Strict documentation audit and MkDocs strict build.
3. Clean installed wheel and source distribution validation.
4. Supported-runtime CI on GitHub Actions.
5. Documentation workflow on GitHub Actions.

Each passed check needs retained evidence that records the tested commit,
command or workflow identity, runtime, result and any relevant artifact paths or
URLs. Focused audit checks from earlier preparation steps are useful evidence
for review but do not replace these final checks.

## Workflow Configuration

During final preparation, CI and Documentation run automatically on pushes to
`prep/v1.0-stability`. CI also runs on version tags. Documentation still deploys
Pages only from `main`, so development pushes can validate documentation without
publishing it.

This branch-trigger configuration is part of final candidate preparation. It can
be narrowed again after v1.0 if a different development workflow is preferred.

## Current State

All review gates are approved. The five final candidate checks remain `not_run`,
and `ready_for_candidate` remains `false`. This is intentional until the final
source identity is chosen and every final gate has recorded evidence.

## Remote evidence status

The remote CI and Documentation gates are recorded in
[remote final candidate gate evidence](final_candidate_remote_evidence.md).
The remaining local gates stay open until they are executed on the exact final
source identity.

## Local regression evidence

The full local regression gate is recorded in
[full local regression evidence](final_candidate_local_regression.md).
Strict documentation and clean installed distributions remain open until they are
executed on the exact final source identity.
