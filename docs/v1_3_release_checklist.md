# v1.3 Phase L7 candidate and release checklist

Status: L7 preparation is implemented; final release approval is pending.
Final candidate identity: `1.3.0`, citation date `2026-10-01`. Latest published stable release: `v1.2.0`.
Historical v1.0/v1.1/v1.2 JSON evidence retains its published meaning; CITATION.cff
now describes the final candidate source and is not proof of publication.

Preparation commit `3054c8e65d5b046b180debbaffdc7b2d2b1e2138` passed
[CI](https://github.com/ocojocaru/NCMemSim/actions/runs/36832977786)
(all six test/distribution jobs on Python 3.11-3.13) and
[Documentation](https://github.com/ocojocaru/NCMemSim/actions/runs/36832977839).
These results do not approve the later final candidate commit.

The additive MODEL API review is `v1_3_api_review.json`, validated by
`python scripts/validate_v1_3_api_review.py`. It reviews six module-qualified
MODEL modules and preserves the 59 stable ensemble exports. Source signatures
and result contracts are reviewed against the v1.2 baseline; this is candidate
contract review, not release approval. L1-L6 tests cover MODEL schemas, nested
readers, source linkage, execution isolation, scientific references and reports.

## Candidate checks

- Full regression suite: `python -m pytest -q`.
- Source API inventory and v1.3 candidate review validators.
- Documentation audit plus strict MkDocs build.
- Clean wheel and sdist installation probes, including stored MODEL report
  restoration, failure accounting and deterministic re-export.
- CI and documentation workflows on `dev/v1.3-model-variability` and pull
  requests to main. Python 3.11, 3.12 and 3.13 are required for tests and
  distribution jobs. Development docs builds do not deploy Pages.
- Source notices and LICENSE/NOTICE in distributions; MkDocs constrained below 2.

## Exact-commit remote evidence

After committing and pushing the preparation changes, record the full SHA and
verify every CI matrix job and the Documentation workflow succeeds for that SHA.
A local pass on Windows/Python does not stand in for the remote Python matrix.
Do not infer a successful GitHub run from a successful push. Do not mark L7
complete while these remote results or final release checks remain pending.

## Final release sequence

1. Review the complete branch diff and obtain green candidate checks on its SHA.
2. Prepare the final `1.3.0` identity, release changelog, README/docs declarations
   and CITATION.cff version/date together. Keep historical JSON evidence intact.
3. Rerun complete local/distribution/documentation checks and the Python matrix
   on that exact final release commit; development-commit checks are insufficient.
4. Merge according to the repository workflow, then verify checks on the resulting
   main commit. Record that identity before tagging.
5. Create the `v1.3.0` tag only when package/citation/docs identity and gates agree.
   Verify tag, main commit, release assets, release workflow and deployed docs
   refer to the intended final source. Publication is a separate final action.

No tag, merge or release publication is performed by this preparation step.
