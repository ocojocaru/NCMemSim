# Archival and Citation Policy

This page records the approved archival and citation policy for v1.0.0. The
versioned GitHub release provides the exact source identity and distributable
artifacts. No DOI or external archival deposit is currently claimed.

The machine-readable policy is
[archival_citation.json](archival_citation.json).

## Approved policy

The first stable release cites and archives the exact final source identity used
for release. Before the tag is published, the project must retain evidence for:

- the exact final commit, tag and package version;
- the versioned GitHub source archive and built distributions;
- the final `CITATION.cff` contents;
- full local regression;
- strict documentation audit;
- clean installed wheel and source distributions;
- supported-runtime CI;
- remote documentation publication.

If an external archive service later assigns a DOI, it can be added to
`CITATION.cff` and the release documentation only after the identifier is visible
and verified. Until then, citation instructions refer to the repository, exact
software version and release identity. A DOI must never be invented or copied
from an unrelated publication.

## v1.0.0 citation state

Citation metadata is aligned with version `1.0.0`. The repository code URL is
`https://github.com/ocojocaru/NCMemSim`. `CITATION.cff` does not claim a DOI
because no external service has assigned one. Repository URL, exact version and
release identity form the current software citation.

## Explicit non-claims

Archival policy does not establish experimental calibration, manufactured
yield, all-device predictive validity or a publication claim. Those remain
governed by the approved scientific scope and retained source evidence.

The readiness matrix marks `archival_citation` as approved and
`ready_for_candidate=true` because every required final candidate check passed.
An optional future DOI deposit is independent of the v1.0.0 release gate.
