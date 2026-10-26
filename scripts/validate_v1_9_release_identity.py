# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Published v1.9.0 identity and confirmed Zenodo archival."""
from pathlib import Path
import ast
from datetime import date
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.validate_v1_2_release_identity import _citation_field
VERSION='1.9.0'
CANDIDATE_DATE='2026-10-26'
VERSION_DOI='10.5281/zenodo.23664613'
CONCEPT_DOI='10.5281/zenodo.23078330'


def validate_identity(root):
    root=Path(root)
    tree=ast.parse((root/'ncmemsim/_version.py').read_text(encoding='utf-8'))
    values=[ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign)
        and any(isinstance(target,ast.Name) and target.id=='__version__' for target in node.targets)]
    if values!=[VERSION]:raise ValueError('single final candidate version must be 1.9.0')
    citation=(root/'CITATION.cff').read_text(encoding='utf-8')
    for field in ('version','date-released','license','identifiers','doi'):
        if len(re.findall(r'(?m)^'+re.escape(field)+r'\s*:',citation))!=1:
            raise ValueError('duplicate or missing citation field: '+field)
    if _citation_field(citation,'version')!=VERSION or _citation_field(citation,'date-released')!=CANDIDATE_DATE:
        raise ValueError('candidate citation version/date mismatch')
    date.fromisoformat(CANDIDATE_DATE)
    if _citation_field(citation,'license')!='Apache-2.0':raise ValueError('candidate license mismatch')
    concept='identifiers:\n  - type: doi\n    value: '+CONCEPT_DOI+'\n    description: "Concept DOI representing all published versions"'
    if concept not in citation or _citation_field(citation,'doi')!=VERSION_DOI:
        raise ValueError('confirmed version DOI and separate Concept DOI required')
    if re.findall(r'10\.\d{4,9}/[^\s"\']+',citation)!=[VERSION_DOI,CONCEPT_DOI]:
        raise ValueError('only the confirmed version DOI and Concept DOI belong in this citation')
    markers={
        'README.md':('**Published v1.9.0 status:**','**Current stable release:** `1.9.0`','P4B/P5B/P6B',VERSION_DOI),
        'CHANGELOG.md':('## 1.9.0 - 2026-10-26','experimental qualification remains deferred'),
        'docs/index.md':('Latest published stable: `1.9.0`','R7 is complete',VERSION_DOI),
        'docs/archival_citation.md':('Published v1.9.0 citation',VERSION_DOI),
        'docs/roadmap.md':('R7 is complete','v1.9.0','experimental qualification remains deferred'),
        'docs/performance_interoperability.md':('Published identity: `1.9.0`','R7',VERSION_DOI),
        'docs/v1_9_release_checklist.md':('Published identity: `1.9.0`','Citation date: `2026-10-26`',
            'Latest published stable: `1.9.0`','Python 3.11, 3.12 and 3.13','P4B/P5B/P6B')}
    for name,words in markers.items():
        text=(root/name).read_text(encoding='utf-8')
        if any(word not in text for word in words):raise ValueError('candidate declaration mismatch: '+name)
    if 'not yet published' in (root/'docs/roadmap.md').read_text(encoding='utf-8'):
        raise ValueError('published release must not retain unpublished roadmap status')
    return dict(status='published_identity_consistency_pass',package_version=VERSION,
        citation_date=CANDIDATE_DATE,latest_published_stable='1.9.0',concept_doi=CONCEPT_DOI,
        version_specific_doi=VERSION_DOI,release_published=True,exact_candidate_ci='success')


def validate(root):
    from scripts.validate_v1_9_api_review import validate as review
    return {**validate_identity(root),'api':review(root)}


if __name__=='__main__':
    import json
    print(json.dumps(validate(ROOT),indent=2))
