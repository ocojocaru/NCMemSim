# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Final unpublished v1.9.0 candidate identity; version DOI awaits actual archival."""
from pathlib import Path
import ast
from datetime import date
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.validate_v1_2_release_identity import _citation_field
VERSION='1.9.0'
CANDIDATE_DATE='2026-10-23'
CONCEPT_DOI='10.5281/zenodo.23078330'


def validate_identity(root):
    root=Path(root)
    tree=ast.parse((root/'ncmemsim/_version.py').read_text(encoding='utf-8'))
    values=[ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign)
        and any(isinstance(target,ast.Name) and target.id=='__version__' for target in node.targets)]
    if values!=[VERSION]:raise ValueError('single final candidate version must be 1.9.0')
    citation=(root/'CITATION.cff').read_text(encoding='utf-8')
    for field in ('version','date-released','license','identifiers'):
        if len(re.findall(r'(?m)^'+re.escape(field)+r'\s*:',citation))!=1:
            raise ValueError('duplicate or missing citation field: '+field)
    if _citation_field(citation,'version')!=VERSION or _citation_field(citation,'date-released')!=CANDIDATE_DATE:
        raise ValueError('candidate citation version/date mismatch')
    date.fromisoformat(CANDIDATE_DATE)
    if _citation_field(citation,'license')!='Apache-2.0':raise ValueError('candidate license mismatch')
    concept='identifiers:\n  - type: doi\n    value: '+CONCEPT_DOI+'\n    description: "Concept DOI representing all published versions"'
    if concept not in citation or re.search(r'(?m)^doi\s*:',citation):
        raise ValueError('version-specific DOI awaits confirmed v1.9 archival; retain separate Concept DOI only')
    if re.findall(r'10\.\d{4,9}/[^\s"\']+',citation)!=[CONCEPT_DOI]:
        raise ValueError('only the confirmed Concept DOI belongs in this unpublished candidate citation')
    markers={
        'README.md':('**Final v1.9.0 candidate:**','**Current stable release:** `1.8.0`','P4B/P5B/P6B','not yet published'),
        'CHANGELOG.md':('## 1.9.0 - 2026-10-23 (unpublished candidate)','experimental qualification remains deferred'),
        'docs/index.md':('Final candidate: `1.9.0`','Latest published stable: `1.8.0`','not yet published'),
        'docs/archival_citation.md':('Final v1.9.0 candidate','version-specific DOI remains pending'),
        'docs/roadmap.md':('R7 final candidate','v1.9.0','experimental qualification remains deferred'),
        'docs/performance_interoperability.md':('Final candidate identity: `1.9.0`','R7','not yet published'),
        'docs/v1_9_release_checklist.md':('Final candidate identity: `1.9.0`','Citation date: `2026-10-23`',
            'Latest published stable: `1.8.0`','Python 3.11, 3.12 and 3.13','P4B/P5B/P6B')}
    for name,words in markers.items():
        text=(root/name).read_text(encoding='utf-8')
        if any(word not in text for word in words):raise ValueError('candidate declaration mismatch: '+name)
    if 'R7 is complete' in (root/'docs/roadmap.md').read_text(encoding='utf-8'):
        raise ValueError('candidate must not claim completed release/archival')
    return dict(status='final_candidate_identity_consistency_pass',package_version=VERSION,
        citation_date=CANDIDATE_DATE,latest_published_stable='1.8.0',concept_doi=CONCEPT_DOI,
        version_specific_doi=None,release_published=False,exact_candidate_ci='pending after push')


def validate(root):
    from scripts.validate_v1_9_api_review import validate as review
    return {**validate_identity(root),'api':review(root)}


if __name__=='__main__':
    import json
    print(json.dumps(validate(ROOT),indent=2))
