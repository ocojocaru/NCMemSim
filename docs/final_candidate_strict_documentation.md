# Strict documentation audit evidence

> **Historical evidence/contract:** Version-specific counts, decisions and gates below retain their original scope. They do not describe outstanding v1.10 release work. See [current platform status](platform_status.md).

The v1.0.0 release retains the strict documentation audit gate first recorded
on `prep/v1.0-stability` for commit
`95405f4b6188c6609d3c1b38b609e7627ded2beb`.

Machine-readable evidence is in
[final_candidate_strict_documentation.json](final_candidate_strict_documentation.json).

## Command

```bash
python scripts/validate_documentation.py
```

Observed result: MkDocs strict build passed, 42 rendered pages were checked,
7070 local references had no missing targets or anchors, 116 Python
documentation blocks parsed, 338 public imports resolved, and the DTCO, robust
DTCO and scientific workflow examples executed.

This gate does not cover clean installed wheel/source distribution validation.
