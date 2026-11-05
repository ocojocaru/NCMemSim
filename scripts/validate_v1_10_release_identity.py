# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Published v1.10.0 identity and confirmed Zenodo archival."""
from pathlib import Path
import ast
from datetime import date
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts.validate_v1_2_release_identity import _citation_field
VERSION='1.10.0'
CANDIDATE_DATE='2026-11-05'
VERSION_DOI='10.5281/zenodo.23973765'
CONCEPT_DOI='10.5281/zenodo.23078330'


def validate_identity(root):
    root=Path(root)
    tree=ast.parse((root/'ncmemsim/_version.py').read_text(encoding='utf-8'))
    versions=[ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='__version__' for t in n.targets)]
    if versions!=[VERSION]: raise ValueError('single candidate version must be 1.10.0')
    text=(root/'CITATION.cff').read_text(encoding='utf-8')
    for field in ('version','date-released','license','identifiers','doi'):
        if len(re.findall(r'(?m)^'+re.escape(field)+r'\s*:',text))!=1:
            raise ValueError('duplicate or missing citation field: '+field)
    if (_citation_field(text,'version')!=VERSION or
        _citation_field(text,'date-released')!=CANDIDATE_DATE or
        _citation_field(text,'license')!='Apache-2.0'):
        raise ValueError('candidate citation identity mismatch')
    date.fromisoformat(CANDIDATE_DATE)
    concept='identifiers:\n  - type: doi\n    value: '+CONCEPT_DOI+'\n    description: "Concept DOI representing all published versions"'
    if (concept not in text or _citation_field(text,'doi')!=VERSION_DOI or
        re.findall(r'10\.\d{4,9}/[^\s"\']+',text)!=[VERSION_DOI,CONCEPT_DOI]):
        raise ValueError('confirmed version DOI and separate Concept DOI required')
    markers={
        'README.md':('**Published v1.10.0 status:**','**Current stable release:** `1.10.0`','P4B/P5B/P6B'),
        'CHANGELOG.md':('## 1.10.0 - 2026-11-05','experimental qualification remains deferred'),
        'docs/index.md':('Latest published stable: `1.10.0`','S7 is complete'),
        'docs/archival_citation.md':('Published v1.10.0 citation',VERSION_DOI),
        'docs/roadmap.md':('S7 is complete','v1.10.0'),
        'docs/v1_10_release_checklist.md':('Published identity: `1.10.0`','S7 is complete',
            'Python 3.11, 3.12 and 3.13','P4B/P5B/P6B')}
    for name,words in markers.items():
        if any(word not in (root/name).read_text(encoding='utf-8') for word in words):
            raise ValueError('candidate declaration mismatch: '+name)
    return dict(status='published_identity_consistency_pass',package_version=VERSION,
        citation_date=CANDIDATE_DATE,latest_published_stable='1.10.0',concept_doi=CONCEPT_DOI,
        version_specific_doi=VERSION_DOI,release_published=True,exact_candidate_ci='success',
        metadata_followup_ci='pending metadata commit/push')


def validate(root):
    from scripts.validate_v1_10_api_review import validate as review
    return {**validate_identity(root),'api':review(root)}


if __name__=='__main__':
    import json
    print(json.dumps(validate(ROOT),indent=2))
