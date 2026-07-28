# First GitHub release: NCMemSim v0.9.1

These commands assume the extracted project directory is the current working directory and that an empty GitHub repository named `NCMemSim` has already been created.

## 1. Set the final repository owner

Replace the placeholder in both files before the first commit:

```text
CITATION.cff
mkdocs.yml
```

Change:

```text
REPLACE-WITH-OWNER
```

to the exact GitHub account or organization name that owns the repository.

## 2. Run the local release gate

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall -q ncmemsim
python -m pip wheel . --no-deps --wheel-dir dist
```

For documentation validation:

```bash
python -m pip install mkdocs mkdocs-material
mkdocs build --strict
```

Expected automated test result for this archive:

```text
63 passed
```

## 3. Initialize Git and create the first commit

```bash
git init
git branch -M main
git add .
git status
git commit -m "Release NCMemSim v0.9.1"
```

## 4. Connect and push the GitHub repository

Use the repository URL displayed by GitHub:

```bash
git remote add origin https://github.com/<OWNER>/NCMemSim.git
git push -u origin main
```

Check the **Actions** tab and resolve any CI or documentation failure before tagging the release.

## 5. Enable GitHub Pages

In **Settings → Pages**, select **GitHub Actions** as the build and deployment source. Push a documentation-only change only if a fresh documentation deployment is needed.

## 6. Tag and publish v0.9.1

After all checks on `main` are green:

```bash
git tag -a v0.9.1 -m "NCMemSim v0.9.1"
git push origin v0.9.1
```

The tag starts `.github/workflows/release.yml`, which builds the wheel and source distribution and creates a GitHub release with those artifacts.

## 7. Post-release verification

Confirm that:

- the release page displays `v0.9.1`;
- wheel and source archives are attached;
- `CITATION.cff` is recognized by GitHub;
- the documentation site loads correctly;
- the repository license is detected as Apache-2.0;
- a clean clone passes `python -m pytest -q`.

Do not delete the Phase D6 golden-reference file named for `v0.9.0`; it records the validated numerical baseline from that scientific release.
