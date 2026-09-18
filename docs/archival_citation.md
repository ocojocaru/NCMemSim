# Archival and Citation Plan

This page records the approved archival and citation plan for v1.0
preparation. The package remains `0.14.0` on `prep/v1.0-stability`; this step
does not create a v1.0 tag, publish a release, deposit an archive or assign a
DOI.

The machine-readable plan is [archival_citation.json](archival_citation.json).

## Approved Plan

The first stable release should cite and archive the exact final source identity
used for release. Before a candidate can be called ready, the project must retain
evidence for:

- the exact final commit/tag and package version;
- the source archive or external software deposit generated from that commit;
- the final `CITATION.cff` contents;
- full local regression;
- strict documentation audit;
- clean installed wheel and source distributions;
- supported-runtime CI;
- remote documentation publication.

If an external archive service assigns a DOI, the DOI can be added to
`CITATION.cff` and to release documentation only after the identifier is visible
and verified. Until then, citation instructions must refer to the repository,
the exact software version and the final source identity. A DOI must never be
invented or copied from an unrelated publication.

## Retained Current State

Current citation metadata remains for version `0.14.0`. The repository code URL
is `https://github.com/ocojocaru/NCMemSim`. The current `CITATION.cff` does not
claim a DOI, and this is intentional during stability preparation.

The v1.0 release can later update the citation file to version `1.0.0` and the
actual release date as part of final candidate preparation. That update must be
reviewed together with the final source identity and archive/deposit evidence.

## Explicit Non-Claims

Archival planning does not establish experimental calibration, manufactured
yield, all-device predictive validity or a publication claim. Those remain
governed by the approved scientific scope and the retained source evidence.

Archival planning also does not satisfy final release checks. The readiness
matrix can mark `archival_citation` as approved because the plan is approved,
while `ready_for_candidate` remains false until all final candidate checks pass.
