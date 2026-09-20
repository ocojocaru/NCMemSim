# Distribution and reproducibility contract review

This audit was performed from the v0.14.0 baseline and is retained as the
v1.0.0 distribution contract. It changes release-validation tooling and
documentation, not simulation algorithms.

## Source and installed-package inventories

The distribution gate now requires every existing ncmemsim Python source module,
not just the DTCO/workflow subset: currently 84 files. The checkout inventory is
the comparator. Wheel presence is checked before installation; exact installed
execution is still required at final-version preparation. Presence alone is not
a byte comparison of every wheel file or a guarantee of dependency compatibility.

Source distributions must retain LICENSE, pyproject.toml, citation, build entry
points, audited documentation/assets, reference examples and frozen archive
fixtures. Byte comparison also discovers all current files under docs, assets,
data/reference, examples and tests/fixtures/archives, excluding caches/bytecode.
Missing, altered, duplicate and non-regular expected source members fail the
gate. No archive extraction is performed by these checks.

MANIFEST.in now explicitly grafts data/reference. This retains the Tran2016
CSV/JSON records and their README, which are repository scientific reference
inputs and provenance evidence. They are source-distribution content, not wheel
package data. Frozen fixtures retain LF endings and their exact SHA-256 digests.
The source-content gate detects unintended bytes, not the scientific correctness
or authenticity of a declared reference dataset.

## Installation isolation is a final gate

The default validator creates fresh environments, installs declared dependencies,
builds sdist and a wheel from that sdist, then installs each artifact separately.
The probe runs outside the checkout with Python -I, checks import origins in the
installation environment, and runs actual electrical/optical fitting, application,
DTCO and linked-report references. Copied reference examples are execution inputs;
package modules must come from the installed artifact.

The installed probe now also reads all seven frozen published-v0.14.0 archive
fixtures and verifies their SHA-256/content without regenerating expected values.
Fixture copies are source reference inputs, not wheel data. Existing installed
report/fit checks remain. --reuse-dependencies is a distinct offline mode which
inherits dependencies; it is not equivalent to a clean installation.

During audit iterations we test the validators with small synthetic archive
containers and execute the frozen-reader probe locally. We do not build wheels,
install packages, run Actions or claim clean-install success for this new commit.
Full installed validation remains a final-version preparation gate on supported
Python environments; the current CI matrix is 3.11, 3.12 and 3.13.
Dependency/runtime versions remain part of the evidence: broad dependency bounds
are not a lock file or proof of reproducibility on every permitted future version.

## Runtime and configuration identity boundaries

The legacy build_reproducibility_manifest emits schema 2, creation timestamp,
software version, Git commit when available, Python/platform/NumPy versions,
device/configuration hashes, material models and optional seed/metadata.
Its default physics_model is the historical string PhaseD6, not an automatic
serialization of every configured engine. Capture actual settings explicitly.
software_version prefers installed distribution metadata when present. GITHUB_SHA
is accepted as declared CI provenance; Git fallback uses the caller's working
directory and may be unavailable. These fields are not verified signatures.

The legacy simulation_hash covers device summary, physics_model label and supplied
configuration. It does not include every recorded runtime, seed or extra field.
Equal hashes therefore do not prove identical complete runtime/physics inputs.
created_utc prevents treating the entire legacy manifest as a deterministic result.
Material records are deduplicated by name/model_version; do not use that alone
to distinguish different custom values under the same identity.

The legacy manifest holds shallow references to supplied configuration/metadata;
subsequent mutation can leave recorded hashes inconsistent with the dictionary.
Serialize/copy it at capture time and avoid modifying source objects afterwards.
This audit documents and tests that behavior without silently changing schema or
copy semantics. It is distinct from immutable typed workflow/archive evidence.
See [scientific defaults](scientific_defaults.md),
[archive compatibility](api_archives.md) and
[fitting/DTCO result contracts](api_analysis_results.md).

G/H/I archives retain their own definition/run/runtime/source hashes and explicit
failure denominators. Reading archived evidence preserves the recorded runtime;
it does not rerun physics or assert matching results across arbitrary platforms.
A seed by itself is insufficient: law, bounds, algorithm, sample count, settings,
ordered stored samples and runtime must be retained. Successful synthetic fitting
and matching hashes remain separate from experimental calibration.

## Remaining final-version gates

Approve the intended stable read/default contracts, perform full local tests,
strict documentation/link/example audit and clean wheel/sdist execution, then
verify supported-runtime CI and documentation for the final prepared commit.
No published tags or version metadata are changed by this audit. Release
artifact hashes/commit identity and dependency/runtime records should accompany
the final result; this patch does not establish experimental predictive validity.
