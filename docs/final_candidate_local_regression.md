# Full local regression evidence

> **Historical evidence/contract:** Version-specific counts, decisions and gates below retain their original scope. They do not describe outstanding v1.10 release work. See [current platform status](platform_status.md).

The v1.0.0 release retains the full local regression gate first recorded on
`prep/v1.0-stability` at commit `6fd4505d7de524caef4ca8361b07c4b5eea0966e`.

Machine-readable evidence is in
[final_candidate_local_regression.json](final_candidate_local_regression.json).

## Required command

```bash
python -m pytest -q --basetemp ..\tmp-stability-full-local-regression-pytest
```

Observed package-preparation result: `2213 passed in 280.07s (0:04:40)`.

The final release verifier reruns the same full pytest command before staging. This gate
does not cover the strict documentation audit or clean installed distribution
validation.
