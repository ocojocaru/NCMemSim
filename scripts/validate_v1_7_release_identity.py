# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Prepared v1.7 identity; no publication or version-specific DOI claim."""
from pathlib import Path
from datetime import date
import ast,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.validate_v1_2_release_identity import _citation_field
VERSION='1.7.0'
CANDIDATE_DATE='2026-10-12'
CONCEPT_DOI='10.5281/zenodo.23078330'


def validate_identity(root):
    tree=ast.parse((root/'ncmemsim/_version.py').read_text(encoding='utf-8'))
    versions=[ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='__version__' for t in n.targets)]
    if versions!=[VERSION]:raise ValueError('single final candidate package version must be 1.7.0')
    citation=(root/'CITATION.cff').read_text(encoding='utf-8')
    for field in ('version','date-released','license','identifiers'):
        if len(re.findall(r'(?m)^'+re.escape(field)+r'\s*:',citation))!=1:raise ValueError('duplicate or missing citation field: '+field)
    if _citation_field(citation,'version')!=VERSION or _citation_field(citation,'date-released')!=CANDIDATE_DATE:
        raise ValueError('candidate citation version/date mismatch')
    date.fromisoformat(CANDIDATE_DATE)
    if re.search(r'(?m)^doi\s*:',citation):raise ValueError('candidate must not claim an unconfirmed version-specific DOI')
    concept='identifiers:\n  - type: doi\n    value: '+CONCEPT_DOI+'\n    description: "Concept DOI representing all published versions"'
    if concept not in citation or _citation_field(citation,'license')!='Apache-2.0':raise ValueError('Concept DOI/license mismatch')
    markers={
        'README.md':('**Final candidate:** `1.7.0`','**Current stable release:** `1.6.0`','not yet published','P4B/P5B/P6B'),
        'CHANGELOG.md':('## 1.7.0 - 2026-10-12 (prepared candidate)','experimental qualification remains deferred'),
        'docs/index.md':('Final candidate: `1.7.0`','not yet published','Published stable release: `1.6.0`'),
        'docs/archival_citation.md':('prepared v1.7.0 candidate dated 2026-10-12','No version-specific DOI is assigned to this candidate'),
        'docs/roadmap.md':('P7 final candidate prepared','experimental qualification remains deferred'),
        'docs/independent_calibration.md':('Final candidate identity: `1.7.0`','P4B/P5B/P6B','not yet published'),
        'docs/v1_7_release_checklist.md':('P7 is not complete','Final candidate identity: `1.7.0`','Candidate date: `2026-10-12`','release approval remains pending','P4B/P5B/P6B')}
    for name,values in markers.items():
        if any(x not in (root/name).read_text(encoding='utf-8') for x in values):raise ValueError('candidate declaration mismatch: '+name)
    return {'status':'candidate_identity_pass_not_publication','package_version':VERSION,
        'candidate_date':CANDIDATE_DATE,'latest_published_stable':'1.6.0','version_specific_doi':None,'concept_doi':CONCEPT_DOI}


def validate(root):
    from scripts.validate_v1_7_api_review import validate as review
    return {**validate_identity(root),'api':review(root)}


if __name__=='__main__':
    import json
    print(json.dumps(validate(ROOT),indent=2))
