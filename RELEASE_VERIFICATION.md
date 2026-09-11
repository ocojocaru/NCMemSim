# NCMemSim v0.9.1 release verification

> **Historical document:** This file records the v0.9.1 release process and is retained for project provenance. It does not describe the current NCMemSim release. See `README.md` and `CHANGELOG.md` for the current release status.

Verification was run on the cumulative R1–R6 release candidate packaged from the uploaded R5 archive.

## Passed checks

- **Automated tests:** `63 passed`.
- **Package import:** `ncmemsim.__version__ == "0.9.1"`.
- **Python compilation:** `python -m compileall -q ncmemsim` completed successfully.
- **Package metadata:** `pyproject.toml` parsed successfully.
- **Package discovery:** restricted explicitly to `ncmemsim*`, preventing accidental inclusion of repository data directories.
- **Wheel build:** `ncmemsim-0.9.1-py3-none-any.whl` built successfully with the installed build environment using `--no-build-isolation`.
- **YAML validation:** MkDocs, CFF, Dependabot, issue configuration and all GitHub workflow files parsed successfully.
- **SVG validation:** all 14 SVG assets in `assets/` and `docs/assets/` parsed successfully.
- **Repository hygiene:** Python caches, pytest caches and generated build directories were removed before packaging.

## Environment-limited checks

- A build using an isolated PEP 517 environment could not be completed locally because the execution environment could not retrieve `setuptools>=68`. The non-isolated wheel build succeeded, and the tagged GitHub release workflow installs current build requirements on GitHub-hosted runners.
- `mkdocs build --strict` was not executed locally because MkDocs was not installed in the offline packaging environment. The MkDocs configuration parsed successfully, and the GitHub Pages workflow installs MkDocs and runs a strict build.

## Intentional placeholder

The final GitHub owner `ocojocaru` is configured in `CITATION.cff`, `mkdocs.yml`, and `pyproject.toml`.
