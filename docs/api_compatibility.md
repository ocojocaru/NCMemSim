# API compatibility preparation

This policy prepares the v1.0 API using the published v0.14.0 baseline. It does
not declare every importable implementation detail stable. The package version
remains 0.14.0 during this review; the published tag is unchanged.

## Public imports and pending approval

The public API overview lists intended entry points in the root package and
in dedicated materials, optical, dataset, fitting, calibration, DTCO and workflow
modules. Existing documented imports must remain available during preparation.
`__all__` is export evidence, not sufficient approval for a stability guarantee.
A complete approved import/signature manifest remains a v1.0 acceptance gate.
Underscore helpers and incidental imported names receive no new guarantee.

The package module `ncmemsim.experimental` contains public dataset APIs. It is
distinct from the repository's top-level exploratory `experimental/` directory.
The latter is outside the stable package contract.

`ncmemsim.transport` preserves the eight existing type exports and five legacy
submodule aliases (`base`, `link`, `network`, `rates`, `engine`). Its explicit
wildcard list prevents future helper imports from silently extending the API.
These aliases remain importable; no removal is part of this preparation.

## Compatibility rules for the proposed v1.0 contract

For approved APIs, minor releases must retain import paths, accepted documented
keyword arguments and their meanings. New optional arguments must not invalidate
existing calls. Public constructor order needs review before freezing positional
calls; examples should prefer keywords. Incompatible removals require a major
release and a documented migration path. Deprecations require release notes and
at least one preceding minor release with notice; emit DeprecationWarning where
practical for callable use. This is a proposed release policy, not retrospective
assurance that every pre-v1 API has followed it.

Numerical defaults and applicability limits require a separate scientific review.
A default or algorithm change must identify its effect and validation evidence;
a compatible signature alone does not establish compatible scientific behavior.
Software stability never promotes FITTED evidence to experimental calibration.

## Result contract review

Before approval, record units, scalar/array types, shapes, axis ordering and
optional-value behavior for each public result. Do not equate missing values,
None, empty arrays and numerical zero. Mutable NumPy arrays and final states
must not be described as immutable just because their container is frozen.
Ownership and copy guarantees require observed behavior and targeted tests.
Adding result fields must preserve supported construction and reading patterns.
The detailed per-result inventory and ownership review remain open gates.

## Archives and numerical replay

Schema identifiers, required fields and unsupported-schema errors are separate
from the callable contract. Define supported historical read schemas before
v1.0. Migrations must preserve original provenance and distinguish an original
archive from a converted representation. Do not silently reinterpret fields.

Reading an archive without rerunning physics does not guarantee execution in a
new runtime. Existing evaluator runtime checks remain authoritative. Hashes
check integrity and consistency; they do not authenticate scientific claims.
No cross-Python/NumPy bitwise reproducibility guarantee is introduced here.
A retained historical-fixture and schema-migration review remains an open gate.

## Local and final validation

Audit iterations update docs and run focused compatibility checks locally.
No CI/Documentation push trigger is added for the preparation branch. Full
regression, strict documentation, clean distributions and supported-Python
Actions belong to final-version preparation before the release candidate/tag.

## Recorded review baselines

Use the [source API inventory](api_inventory.md) and [result contracts](api_results.md).
`scripts/validate_api_contract.py` checks the recorded source inventory without
importing optional fitting dependencies. Explicit baseline regeneration requires
review of every change and does not by itself approve stability.
