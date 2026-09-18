# v1.0 readiness consolidation

The package remains 0.14.0 on prep/v1.0-stability; the published v0.14.0 tag is
unchanged. This consolidation records audited evidence and decisions still
needed. It does not bump the version, approve all exports or declare a release
candidate. The machine-readable matrix is [release_readiness.json](release_readiness.json).

## Reviewed contracts awaiting approval

| Area | Evidence | Decision still required |
|---|---|---|
| Public API | [source inventory](api_inventory.md), [compatibility policy](api_compatibility.md) | Select exact stable imports/signatures, positional constructor guarantees and deprecation policy; do not freeze incidental helpers solely because they appear in the inventory |
| Results | [core contracts](api_results.md), [analysis contracts](api_analysis_results.md) | Accept axes/units, None/NaN/empty behavior, shallow ownership and existing empty-sweep/input-aliasing semantics, or implement a separately reviewed change |
| Archives | [read-schema audit](api_archives.md), seven frozen published-code fixtures | Accept strict current-schema readers and retained schema support; coverage is not every historical or optical archive |
| Defaults | [scientific review](scientific_defaults.md) | Accept existing values, applicability and provenance scope; decide any legacy validation hardening separately |
| Distribution | [distribution review](distribution_contracts.md) | Accept all-module/source-byte inventory and explicit clean versus inherited-dependency installation modes |

These audits are complete as local reviews. Their tests are evidence for the
specific stated behaviors, not final approval of every source-visible field or
experimental prediction. Documented legacy limitations need an explicit decision;
not every limitation must become a new feature before a stable software release.
If a limitation is unacceptable, make the smallest separately reviewed change and
update its contract/tests before freezing it.

## Scientific and archival decisions

The intended stable release is a compact simulation/fitting/DTCO software API.
It must retain explicit ASSUMED parameters, applicability ranges and synthetic
FITTED references. Software stability does not turn those into experimental
calibration. Existing experimental calibration workflows must be distinguished
from independent experimental validation of a particular device or prediction.
Select the experimental/reference evidence required for the intended scientific
claims; no new measured dataset, blanket predictive-validity claim or DOI is
introduced by this consolidation. See [scientific scope](scientific_scope.md).

The roadmap's software archive, DOI-backed citation and reproducibility-package
requirements remain open. Prepare the archive/deposit/citation plan before the
final release, then verify the deposited final artifact and identifier when
publication makes them available. Do not invent a DOI or mark a deposit complete
because GitHub publication alone succeeded.

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
validate the final source again. Configure automatic CI/Documentation on the
chosen preparation branch only when preparing the final version, following the
agreed workflow; no trigger changes are part of this patch.

## Readiness matrix maintenance

Run python -I scripts/validate_release_readiness.py for a read-only check of
structure, required gates, local evidence paths and preparation-version consistency.
A successful check can report ready_for_candidate=false: it means the matrix is
internally consistent, not that its outstanding decisions have been approved.
The current five contract reviews are reviewed_pending_approval; scientific scope
and archival planning are pending; all five final-candidate checks are not_run.

Approval is a maintainer decision documented with evidence. A passed final check
needs a retained local evidence file with the tested commit/source identity and
result; CI URLs can be recorded inside that file. This script checks references
and state consistency, not the truth of a log, remote status, scientific claims or
external deposits. Do not change state to silence a check.

Before a version change, explicitly review the matrix and its preparation version.
Only after approvals and final checks can ready_for_candidate become true. A final
tag/publication still requires its release procedure and deposit verification.

The next concrete step is resolving the scope/compatibility decisions above;
then prepare the candidate and execute the final gates on one source identity.
