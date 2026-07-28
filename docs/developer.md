# Developer guide

## Repository layout

```text
ncmemsim/      Python package
materials/     material models and provenance framework
transport/     node/link transport engine
examples/      executable scientific examples
configs/       serialized device examples
scripts/       golden, benchmark, and reproduction utilities
tests/         unit and regression tests
validation/    validation assets
docs/          MkDocs documentation
experimental/  explicitly non-stable work
```

The `materials/` and `transport/` directories referenced above are package subdirectories under `ncmemsim/`.

## Adding a new physical feature

1. Define the physical scope, equations, units, and assumptions.
2. Add or extend an explicit configuration dataclass.
3. Implement the kernel in the narrowest appropriate module.
4. Add unit tests for limiting cases and invalid inputs.
5. Integrate through `Simulator` only after the kernel is independently testable.
6. Add end-to-end regression coverage.
7. Update documentation, public exports, changelog, and reproducibility metadata.

## Numerical conventions

- Use NumPy arrays for vector state variables.
- Preserve probability normalization to documented tolerance.
- Treat clipping as a physical/numerical decision, not a cosmetic fix.
- Keep inter-FG transfer conservative.
- Make timestep choices explicit in configuration.
- Avoid results that depend on dictionary insertion order or uncontrolled randomness.

## Extending the public API

A public class or function should:

- have a clear docstring;
- use explicit units in parameter or field names where practical;
- have typed arguments and returns;
- be exported in `ncmemsim/__init__.py` and `__all__`;
- be documented in `docs/api.md`;
- include tests that import it from the package root.

## Tests and regression data

Run focused tests while developing, then the full suite:

```bash
python -m pytest tests/test_phase_d4_transport.py -q
python -m pytest -q
```

Do not regenerate golden references automatically during normal tests. Golden generation is an explicit maintainer operation.

## Documentation

Keep user-facing pages conceptual and executable. Avoid documenting planned functionality as available. Build locally with:

```bash
mkdocs build --strict
```

## Experimental code

Code in `experimental/` is not part of the stable API and may be incomplete. Promotion into `ncmemsim/` requires tests, documentation, and a defined compatibility policy.
