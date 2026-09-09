# NCMemSim v0.9.1 release checklist

This checklist is the release gate for the first public NCMemSim repository and the `v0.9.1` tag.

## Source and version

- [x] Package version is defined once in `ncmemsim/_version.py`.
- [x] `pyproject.toml` reads the package version dynamically.
- [x] `CITATION.cff` declares version `0.9.1` and Apache-2.0 licensing.
- [x] The changelog contains the cumulative Phase D and Repository Polish history.
- [x] Generated caches and local build outputs are excluded from the release archive.

## Scientific validation

- [x] The complete automated test suite passes locally: **63 passed**.
- [x] Golden references for Phase D6 are retained unchanged.
- [x] Validation and reproducibility documentation is included.
- [x] Benchmark and golden-reference scripts are included.

## Documentation and community files

- [x] README, installation, quick-start, physics, architecture, materials, validation, API, developer and roadmap documentation are present.
- [x] Apache License 2.0 is present.
- [x] `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, issue templates and pull-request template are present.
- [x] Branding assets and reusable scientific diagrams are present.
- [x] MkDocs configuration and documentation workflow are present.

## GitHub release gate

Complete these items after creating the GitHub repository:

- [x] Final GitHub owner `ocojocaru` is configured in repository metadata and MkDocs.
- [x] Confirm the default branch is `main`.
- [ ] Push the repository and verify the CI and documentation workflows.
- [ ] Configure GitHub Pages to use **GitHub Actions**.
- [ ] Create and push the annotated tag `v0.9.1`.
- [ ] Verify the release workflow creates wheel and source-distribution assets.
- [ ] Review the generated GitHub release notes before publication.
- [ ] Optionally connect the repository to Zenodo only after the public repository metadata is final.

The release must not be tagged while any required item above is unresolved.
