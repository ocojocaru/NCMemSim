# Archive schema compatibility preparation

This review remains on package version 0.14.0. It records reader contracts and
retained fixtures; it does not declare a v1.0 compatibility guarantee yet.

## Portable reader surface

The reviewed typed JSON readers are DTCOReport (dtco-report-v1),
RobustDTCOReport (dtco-robust-report-v1), WorkflowReport
(scientific-workflow-report-v1), DatasetEvidence
(workflow-dataset-evidence-v1), WorkflowEvidence
(scientific-workflow-evidence-v1), AppliedWorkflowEvidence
(applied-workflow-evidence-v1), and SampleManifest (integer schema 1).
These are distinct envelopes. Other to_dict outputs, including numerical fit
results, are not automatically standalone restorable archives.

Readers preserve archived values, ordered samples, failure records, units,
scientific labels and provenance. Restoring an archive does not fit parameters,
run physics or draw samples again. Runtime provenance is retained from the
archive; it is not replaced with the current machine's versions. Current
runtime results need not reproduce historical numerical values exactly.

JSON is authoritative. Reformatting JSON object keys or whitespace preserves
content identity. Array order remains meaningful. Duplicate keys, nonfinite
JSON constants, corrupted envelope hashes, unknown envelope fields, missing
schema identifiers and unsupported schema versions are rejected. This strict
policy does not provide forward reading of arbitrary added fields. Nested
checks are reader-specific: a valid outer hash is not sufficient, but these
checks are not a proof of every possible scientific assertion or a signature.
See [result semantics](api_analysis_results.md) for undefined values and CSV.

## Retained published-tag fixtures

Seven UTF-8 JSON fixtures in tests/fixtures/archives/v0_14_0 were generated once
from the published v0.14.0 commit
f210f3fcf1e8d48806b0f9a94e564abc0aaabfc9 using the G6, H6 and I6 reference
builders with deliberate failures. Four standalone nested evidence/manifest
fixtures were extracted from those generated reports. All fitting evidence is
synthetic and FITTED; it is not experimental calibration.

These are published-code fixtures created for this audit, not files claimed to
have been downloaded from a user's historical run or GitHub release asset.
Their archived runtime describes the generation environment. inventory.json
records the source tag/commit, schema labels and SHA-256 of each exact file.
Tests never regenerate the expected archives. Preserve these bytes in future
changes; add new fixtures instead of overwriting history or updating hashes to
silence a compatibility failure. Explicit migration, if needed, must preserve
the old fixture and test the old reader/migration separately.

Tests check exact file digests, lossless typed read/write/read, detached
inspection dictionaries, whitespace independence, invalid envelopes even
with recomputed hashes, failure counts, nested source links and restoration in
a fresh process without SciPy or numerical execution. Existing semantic
corruption tests continue to cover nested links and scientific promotions.
The fixtures are retained in source distributions, not installed wheel data.

## Remaining v1.0 decisions

A future incompatible envelope must use a new schema identifier and an explicit
migration/read policy. No silent scientific promotion, unit conversion,
resampling or dropping failed samples is acceptable. This is the proposed
maintenance policy; final v1.0 approval remains a release gate.

Coverage currently includes electrical workflow reports with failures, not
all historical package versions, optical workflow archive fixtures or every
domain dataset serialization. Existing optical reader tests remain relevant.
Reader integrity checks are consistency checks, not authentication. New nested
validation requirements must be evaluated against these retained archives.
Full supported-runtime CI, source-distribution byte checks and documentation
builds remain final-version preparation gates.
