# Contributing to NCMemSim

Thank you for contributing to NCMemSim. This is scientific software: a change is acceptable only when its physical meaning, numerical behaviour, and reproducibility impact are clear.

## Development setup

```bash
git clone <repository-url>
cd NCMemSim
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest -q
```

Python 3.11, 3.12, and 3.13 are the supported development and CI targets for the current release series.

## Branches and pull requests

Create a focused branch from the current development branch. Suggested prefixes:

- `feature/` for new functionality;
- `fix/` for defects;
- `docs/` for documentation-only changes;
- `refactor/` for behaviour-preserving restructuring;
- `validation/` for golden data, tests, and scientific checks.

A pull request should explain:

- the problem and motivation;
- the physics or API affected;
- assumptions and units;
- numerical or compatibility impact;
- tests and validation added;
- documentation and changelog updates.

## Coding expectations

- Use SI units internally unless a public parameter explicitly states another unit in its name.
- Add type annotations to new public functions and data structures.
- Prefer dataclasses and explicit configuration objects over unstructured dictionaries for stable APIs.
- Keep physics kernels deterministic unless stochastic behaviour is the stated feature.
- Avoid hidden global state.
- Do not silently clip, renormalize, or repair invalid physical states without documenting the behaviour.
- Keep public exports in `ncmemsim/__init__.py` deliberate and update `__all__` when necessary.

## Scientific requirements

A new or modified physical model must include:

1. governing equations or algorithmic definition;
2. parameter definitions and units;
3. assumptions and applicability range;
4. provenance for material or empirical parameters;
5. limiting-case or regression tests;
6. comparison with an existing baseline when behaviour changes;
7. explicit calibration status for empirical or phenomenological parameters;
8. spectral or operating-range limitations when the model is wavelength-, field-, or temperature-dependent.

For a model that is not yet experimentally validated, documentation must say so directly.

## Testing

Run:

```bash
python -m pytest -q
```

New features should include focused unit tests and, when they affect end-to-end outputs, a regression or golden-reference update. A golden-reference change must not be committed merely to make a failing test pass; explain the physical or numerical reason for the changed baseline.

## Documentation

Update the most relevant page in `docs/`. Public API changes require corresponding changes in `docs/api.md`, examples, and `CHANGELOG.md`. Use equations, units, and terminology consistently with the implementation.

Build the documentation locally with:

```bash
python -m pip install mkdocs mkdocs-material
mkdocs build --strict
```

## Versioning and changelog

NCMemSim follows semantic versioning as closely as practical for research software:

- patch releases: corrections, polish, and backward-compatible documentation;
- minor releases: new backward-compatible scientific capabilities;
- major releases: stable scientific milestones or intentional breaking changes.

Record user-visible changes in `CHANGELOG.md` under an `Unreleased` section or the target release.

## Commit messages

Use concise imperative messages, for example:

```text
Add charge-conservation regression test
Document WKB barrier assumptions
Fix FG transfer clipping imbalance
```

## Code of conduct and licensing

Participation is governed by `CODE_OF_CONDUCT.md`. By contributing, you agree that your contribution is licensed under Apache-2.0.
