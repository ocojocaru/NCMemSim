# v1.0 readiness consolidation

The package remains 0.14.0 on prep/v1.0-stability; the published v0.14.0 tag is
unchanged. This consolidation records audited evidence, approved contract and
archival/citation decisions, and final gates still needed. It does not bump the
version, approve all exports or declare a release candidate. The machine-readable matrix is
[release_readiness.json](release_readiness.json), with the final candidate execution plan in
[final_candidate_gates.md](final_candidate_gates.md).

## Approved contract reviews

| Area | Evidence | Approved decision |
|---|---|---|
| Public API | [source inventory](api_inventory.md), [compatibility policy](api_compatibility.md), [stable API candidate](stable_api_proposal.md) | Approve the exact selected imports/signatures, positional constructor guarantees and deprecation policy; do not freeze incidental helpers solely because they appear in the inventory |
| Results | [core contracts](api_results.md), [analysis contracts](api_analysis_results.md), [stable API candidate](stable_api_proposal.md) | Accept axes/units, None/NaN/empty behavior, shallow ownership and existing empty-sweep/input-aliasing semantics as the candidate baseline |
| Archives | [read-schema audit](api_archives.md), seven frozen published-code fixtures, [stable API candidate](stable_api_proposal.md) | Accept strict current-schema readers and retained schema support; coverage is not every historical or optical archive |
| Defaults | [scientific review](scientific_defaults.md), [stable API candidate](stable_api_proposal.md) | Accept existing values, applicability and provenance scope; decide any legacy validation hardening separately |
| Distribution | [distribution review](distribution_contracts.md), [stable API candidate](stable_api_proposal.md) | Accept all-module/source-byte inventory and explicit clean versus inherited-dependency installation modes |
| Scientific scope | [scientific scope](scientific_scope.md), [roadmap](roadmap.md), [calibration scope](calibration.md), [scientific workflows](scientific_workflows.md), [stable API candidate](stable_api_proposal.md) | Approve a stable compact-model simulation/fitting/DTCO software release with explicit ASSUMED/provisional/synthetic FITTED limits and without new experimental-validity claims |
| Archival/citation | [archival and citation plan](archival_citation.md), citation metadata in `CITATION.cff`, [reproducibility](reproducibility.md) | Approve the plan for final source identity, citation metadata and future DOI/deposit verification without inventing a DOI or creating a release |

These audits are complete as local reviews and approved for candidate
preparation. Their tests are evidence for the specific stated behaviors, not
approval of every source-visible field or experimental prediction. Documented
legacy limitations are accepted as candidate behavior; any later incompatible
change needs a separately reviewed migration/major-version decision.

## Scientific and archival decisions

The intended stable release is a compact simulation/fitting/DTCO software API.
It must retain explicit ASSUMED parameters, applicability ranges and synthetic
FITTED references. Software stability does not turn those into experimental
calibration. Existing experimental calibration workflows must be distinguished
from independent experimental validation of a particular device or prediction.
No new measured dataset, blanket predictive-validity claim or DOI is introduced
by this consolidation. See [scientific scope](scientific_scope.md).

The roadmap's software archive, DOI-backed citation and reproducibility-package
requirements remain final-release work. The [archival/citation plan](archival_citation.md)
is approved, but the actual archive/deposit, final citation version and any DOI
must be verified after final source identity and release artifacts exist. Do not
invent a DOI or mark a deposit complete because GitHub publication alone
succeeded.

## Final-candidate checks not yet run for this preparation

1. Full local regression on the final prepared source, including all stability tests.
2. Strict MkDocs and complete documentation audit: links/anchors, API imports,
   runnable electrical/optical examples, version/status claims and source inventory.
3. Default clean wheel/sdist build and installed references, exact audited source
   bytes, reference data and frozen archive readers; inherited dependencies do not
   replace this check.
4. Supported-runtime CI against the exact final prepared commit, with captured
   run identities/results and actual dependency/runtime versions.
5. Documentation Action against that same commit; published Pages must correspond
   to the intended main/release source after integration.

Focused audit passes and historical v0.14.0 release checks do not satisfy these
new final-candidate checks. Do not sum overlapping focused test counts as a full
suite count. If source changes after validation, identify the affected gates and
validate the final source again. Automatic CI and Documentation triggers are configured for `prep/v1.0-stability`
so final candidate pushes validate the prepared source identity. This
configuration does not mark any final check passed.

## Readiness matrix maintenance

Run python -I scripts/validate_release_readiness.py for a read-only check of
structure, required gates, local evidence paths and preparation-version consistency.
A successful check can report ready_for_candidate=false: it means the matrix is
internally consistent and the final gates are still open. The contract,
scientific-scope and archival/citation reviews are approved; remote CI, remote Documentation and full local regression are passed with
recorded evidence, while strict documentation and clean installed distributions
remain not_run.

Approval is a maintainer decision documented with evidence. A passed final check
needs a retained local evidence file with the tested commit/source identity and
result; CI URLs can be recorded inside that file. This script checks references
and state consistency, not the truth of a log, remote status, scientific claims or
external deposits. Do not change state to silence a check.

Before a version change, explicitly review the matrix and its preparation version.
Only after approvals and final checks can ready_for_candidate become true. A final
tag/publication still requires its release procedure and deposit verification.

The next concrete step is final candidate preparation and execution of the final
gates on one source identity.
