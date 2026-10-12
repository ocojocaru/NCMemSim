# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Published v1.7 identity and author-confirmed version DOI consistency."""
from pathlib import Path
from datetime import date
import ast,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.validate_v1_2_release_identity import _citation_field
VERSION='1.7.0'
RELEASE_DATE='2026-10-12'
CONCEPT_DOI='10.5281/zenodo.23078330'
VERSION_DOI='10.5281/zenodo.23316663'


def validate_identity(root):
    tree=ast.parse((root/'ncmemsim/_version.py').read_text(encoding='utf-8'))
    versions=[ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='__version__' for t in n.targets)]
    if versions!=[VERSION]:raise ValueError('single published package version must be 1.7.0')
    citation=(root/'CITATION.cff').read_text(encoding='utf-8')
    for field in ('version','date-released','license','identifiers'):
        if len(re.findall(r'(?m)^'+re.escape(field)+r'\s*:',citation))!=1:raise ValueError('duplicate or missing citation field: '+field)
    if _citation_field(citation,'version')!=VERSION or _citation_field(citation,'date-released')!=RELEASE_DATE:
        raise ValueError('published citation version/date mismatch')
    date.fromisoformat(RELEASE_DATE)
    if len(re.findall(r'(?m)^doi\s*:',citation))!=1 or _citation_field(citation,'doi')!=VERSION_DOI:
        raise ValueError('v1.7 DOI must match the author-confirmed deposit')
    concept='identifiers:\n  - type: doi\n    value: '+CONCEPT_DOI+'\n    description: "Concept DOI representing all published versions"'
    if concept not in citation or _citation_field(citation,'license')!='Apache-2.0':raise ValueError('Concept DOI/license mismatch')
    markers={
        'README.md':('**Published v1.7.0 status:**','**Current stable release:** `1.7.0`',VERSION_DOI,'P4B/P5B/P6B'),
        'CHANGELOG.md':('## 1.7.0 - 2026-10-12','experimental qualification remains deferred',VERSION_DOI),
        'docs/index.md':('Published stable release: `1.7.0`','P7 is complete',VERSION_DOI),
        'docs/archival_citation.md':('published v1.7.0 dated 2026-10-12',VERSION_DOI),
        'docs/roadmap.md':('P7 is complete','experimental qualification remains deferred',VERSION_DOI),
        'docs/independent_calibration.md':('Published identity: `1.7.0`','P4B/P5B/P6B',VERSION_DOI),
        'docs/v1_7_release_checklist.md':('P7 is complete','Published identity: `1.7.0`','Citation date: `2026-10-12`',VERSION_DOI,'cf640a37cf474c0cec17c756fabae9be5acab685','P4B/P5B/P6B')}
    for name,values in markers.items():
        if any(x not in (root/name).read_text(encoding='utf-8') for x in values):raise ValueError('published declaration mismatch: '+name)
    return {'status':'published_identity_consistency_pass','package_version':VERSION,
        'citation_date':RELEASE_DATE,'latest_published_stable':'1.7.0','version_specific_doi':VERSION_DOI,'concept_doi':CONCEPT_DOI}


def validate(root):
    from scripts.validate_v1_7_api_review import validate as review
    return {**validate_identity(root),'api':review(root)}


if __name__=='__main__':
    import json
    print(json.dumps(validate(ROOT),indent=2))
