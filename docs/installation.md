# Installation

## Requirements

- Python 3.11 or newer
- NumPy 1.26 or newer
- `pytest`, `ruff`, and `mypy` for development

## Editable installation

From the repository root:

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e .
```

Install development dependencies with:

```bash
python -m pip install -e ".[dev]"
```

## Verify the installation

```bash
python -c "import ncmemsim; print(ncmemsim.__version__)"
python -m pytest -q
```

The expected package version for this release is `0.9.1`.

## Documentation tools

MkDocs dependencies are intentionally not part of the runtime package:

```bash
python -m pip install mkdocs mkdocs-material
mkdocs serve
```

Open the local address printed by MkDocs. A strict static build can be checked with:

```bash
mkdocs build --strict
```

## Source-checkout execution

Examples are intended to run from an installed editable checkout. Some historical examples also add the repository root to `sys.path` so they can be executed directly.
