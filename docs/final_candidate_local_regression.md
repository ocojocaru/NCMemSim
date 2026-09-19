# Full local regression evidence

The package remains `0.14.0` on `prep/v1.0-stability`. This page records the full local
regression gate for commit `6fd4505d7de524caef4ca8361b07c4b5eea0966e`.

Machine-readable evidence is in
[final_candidate_local_regression.json](final_candidate_local_regression.json).

## Required command

```bash
python -m pytest -q --basetemp ..\tmp-stability-full-local-regression-pytest
```

Observed package-preparation result: `2213 passed in 280.07s (0:04:40)`.

The verify script reruns the same full pytest command before staging. This gate
does not cover the strict documentation audit or clean installed distribution
validation.
