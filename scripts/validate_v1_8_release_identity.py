# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Published v1.8 identity and verified Zenodo version DOI consistency."""
from pathlib import Path
import ast
import re
import sys
from datetime import date

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.validate_v1_2_release_identity import _citation_field

VERSION='1.8.0'
CANDIDATE_DATE='2026-10-20'
CONCEPT_DOI='10.5281/zenodo.23078330'
VERSION_DOI='10.5281/zenodo.23510004'


def validate_identity(root):
    tree=ast.parse((root/'ncmemsim/_version.py').read_text(encoding='utf-8'))
    versions=[ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='__version__' for t in n.targets)]
    if versions!=[VERSION]:raise ValueError('single prepared package version must be 1.8.0')
    citation=(root/'CITATION.cff').read_text(encoding='utf-8')
    for field in ('version','date-released','license','identifiers'):
        if len(re.findall(r'(?m)^'+re.escape(field)+r'\s*:',citation))!=1:
            raise ValueError('duplicate or missing citation field: '+field)
    if _citation_field(citation,'version')!=VERSION or _citation_field(citation,'date-released')!=CANDIDATE_DATE:
        raise ValueError('candidate citation version/date mismatch')
    date.fromisoformat(CANDIDATE_DATE)
    if len(re.findall(r'(?m)^doi\s*:',citation))!=1 or _citation_field(citation,'doi')!=VERSION_DOI:
        raise ValueError('published version DOI must match the confirmed Zenodo record')
    concept='identifiers:\n  - type: doi\n    value: '+CONCEPT_DOI+'\n    description: "Concept DOI representing all published versions"'
    if concept not in citation or _citation_field(citation,'license')!='Apache-2.0':
        raise ValueError('Concept DOI/license mismatch')
    if citation.count(CONCEPT_DOI)!=1 or re.findall(r'10\.\d{4,9}/[^\s"\']+',citation)!=[VERSION_DOI,CONCEPT_DOI]:
        raise ValueError('only confirmed version and separate Concept DOI belong in the published citation')
    markers={
        'README.md':('**Published v1.8.0 status:**','**Current stable release:** `1.8.0`',VERSION_DOI,'P4B/P5B/P6B'),
        'CHANGELOG.md':('## 1.8.0 - 2026-10-20','experimental qualification remains deferred',VERSION_DOI),
        'docs/index.md':('Published stable release: `1.8.0`','Q7 is complete',VERSION_DOI),
        'docs/archival_citation.md':('published v1.8.0 dated 2026-10-20',VERSION_DOI),
        'docs/roadmap.md':('Q7 is complete','experimental',VERSION_DOI),
        'docs/multilevel_operation.md':('Q7 is complete','published identity is `1.8.0`',VERSION_DOI),
        'docs/v1_8_release_checklist.md':('Published identity: `1.8.0`','Latest published stable: `1.8.0`','Q7 is complete','P4B/P5B/P6B',VERSION_DOI,'03b35f40606dbd84c1cd6d715eb6de6222466b47')}
    for name,values in markers.items():
        if any(value not in (root/name).read_text(encoding='utf-8') for value in values):
            raise ValueError('candidate declaration mismatch: '+name)
    return {'status':'published_identity_consistency_pass','package_version':VERSION,
        'citation_date':CANDIDATE_DATE,'latest_published_stable':'1.8.0',
        'version_specific_doi':VERSION_DOI,'concept_doi':CONCEPT_DOI}


def validate(root):
    from scripts.validate_v1_8_api_review import validate as review
    return {**validate_identity(root),'api':review(root)}


if __name__=='__main__':
    import json
    print(json.dumps(validate(ROOT),indent=2))
