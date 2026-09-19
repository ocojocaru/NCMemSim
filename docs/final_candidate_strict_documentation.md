# Strict documentation audit evidence

The package remains `0.14.0` on `prep/v1.0-stability`. This page records the
strict documentation audit gate for commit
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
