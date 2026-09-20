# Installation

### Requirements

- Python 3.11 or newer
- NumPy 1.26 or newer
- Python 3.11, 3.12, and 3.13 are tested by the continuous-integration suite

Development dependencies include:

- `pytest`
- `ruff`
- `mypy`
- `build`
- `matplotlib`
- `scipy` (fitting workflows)

`matplotlib` is required by the retained V5.3 legacy regression reference and
is therefore included in the development dependency set rather than the
minimal NCMemSim runtime dependencies.

## Editable installation

From the repository root:

```bash
python -m venv .venv
```

Activate the environment before installing packages. On Windows CMD:

```cmd
.venv\Scripts\activate
```

On Linux/macOS:

```bash
source .venv/bin/activate
```

If a Conda environment is already activated, use that environment instead of
creating a nested venv. Then, from the repository root:

```bash
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

The stable package and citation report `1.0.0`. For reproducible use, record the
exact tag or commit used for installation together with the environment.
Running pytest requires a source checkout and the `[dev]` dependencies; tests
and examples are not an installed-wheel interface.

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
