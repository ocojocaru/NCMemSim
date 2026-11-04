# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Final v1.10.0 candidate identity, distinct from a published release."""
from pathlib import Path
import ast
from datetime import date
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts.validate_v1_2_release_identity import _citation_field
VERSION='1.10.0'
CANDIDATE_DATE='2026-11-04'
CONCEPT_DOI='10.5281/zenodo.23078330'


def validate_identity(root):
    root=Path(root)
    tree=ast.parse((root/'ncmemsim/_version.py').read_text(encoding='utf-8'))
    versions=[ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='__version__' for t in n.targets)]
    if versions!=[VERSION]: raise ValueError('single candidate version must be 1.10.0')
    text=(root/'CITATION.cff').read_text(encoding='utf-8')
    for field in ('version','date-released','license','identifiers'):
        if len(re.findall(r'(?m)^'+re.escape(field)+r'\s*:',text))!=1:
            raise ValueError('duplicate or missing citation field: '+field)
    if (_citation_field(text,'version')!=VERSION or
        _citation_field(text,'date-released')!=CANDIDATE_DATE or
        _citation_field(text,'license')!='Apache-2.0'):
        raise ValueError('candidate citation identity mismatch')
    date.fromisoformat(CANDIDATE_DATE)
    concept='identifiers:\n  - type: doi\n    value: '+CONCEPT_DOI+'\n    description: "Concept DOI representing all published versions"'
    if (concept not in text or re.search(r'(?m)^doi\s*:',text) or
        re.findall(r'10\.\d{4,9}/[^\s"\']+',text)!=[CONCEPT_DOI]):
        raise ValueError('candidate has only Concept DOI; version DOI awaits publication')
    markers={
        'README.md':('**Final v1.10.0 candidate:**','**Current stable release:** `1.9.0`','P4B/P5B/P6B'),
        'CHANGELOG.md':('## 1.10.0 - Unreleased','experimental qualification remains deferred'),
        'docs/index.md':('Final candidate: `1.10.0`','Latest published stable: `1.9.0`'),
        'docs/archival_citation.md':('Candidate v1.10.0 citation','version-specific DOI is not assigned'),
        'docs/roadmap.md':('S7 final candidate','v1.10.0'),
        'docs/v1_10_release_checklist.md':('Candidate identity: `1.10.0`','not a published release',
            'Python 3.11, 3.12 and 3.13','P4B/P5B/P6B')}
    for name,words in markers.items():
        if any(word not in (root/name).read_text(encoding='utf-8') for word in words):
            raise ValueError('candidate declaration mismatch: '+name)
    return dict(status='final_candidate_identity_consistency_pass',package_version=VERSION,
        citation_date=CANDIDATE_DATE,latest_published_stable='1.9.0',concept_doi=CONCEPT_DOI,
        version_specific_doi=None,release_published=False,exact_candidate_ci='pending candidate commit/push')


def validate(root):
    from scripts.validate_v1_10_api_review import validate as review
    return {**validate_identity(root),'api':review(root)}


if __name__=='__main__':
    import json
    print(json.dumps(validate(ROOT),indent=2))
