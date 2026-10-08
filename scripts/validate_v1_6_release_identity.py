# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Published v1.6 identity and author-confirmed DOI consistency."""
from pathlib import Path
from datetime import date
import ast,json,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.validate_v1_2_release_identity import _citation_field
RELEASE_VERSION='1.6.0'
RELEASE_DATE='2026-10-08'
CONCEPT_DOI='10.5281/zenodo.23078330'
VERSION_DOI='10.5281/zenodo.23235484'


def validate_identity(root):
    tree=ast.parse((root/'ncmemsim/_version.py').read_text(encoding='utf-8'))
    versions=[ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='__version__' for t in n.targets)]
    if versions!=[RELEASE_VERSION]:raise ValueError('final package version must be 1.6.0')
    citation=(root/'CITATION.cff').read_text(encoding='utf-8')
    for field in ('version','date-released','license','identifiers'):
        if len(re.findall(r'(?m)^'+re.escape(field)+r'\s*:',citation))!=1:raise ValueError('duplicate or missing citation field: '+field)
    if _citation_field(citation,'version')!=RELEASE_VERSION or _citation_field(citation,'date-released')!=RELEASE_DATE:
        raise ValueError('final citation version/date mismatch')
    date.fromisoformat(RELEASE_DATE)
    if len(re.findall(r'(?m)^doi\s*:',citation))!=1 or _citation_field(citation,'doi')!=VERSION_DOI:
        raise ValueError('v1.6 DOI must match the author-confirmed deposit')
    concept='identifiers:\n  - type: doi\n    value: '+CONCEPT_DOI+'\n    description: "Concept DOI representing all published versions"'
    if concept not in citation or _citation_field(citation,'license')!='Apache-2.0':raise ValueError('Concept DOI/license mismatch')
    markers={'README.md':('**Published v1.6.0 status:**','**Current stable release:** `1.6.0`',VERSION_DOI),
        'CHANGELOG.md':('## 1.6.0 — 2026-10-08',VERSION_DOI),
        'docs/index.md':('Published stable release: `1.6.0`','O7 is complete',VERSION_DOI),
        'docs/archival_citation.md':('published v1.6.0 dated 2026-10-08',VERSION_DOI),
        'docs/roadmap.md':('Published identity: `1.6.0`','O7 is complete',VERSION_DOI),
        'docs/strain_confinement.md':('Published identity: `1.6.0`','O7 is complete',VERSION_DOI),
        'docs/v1_6_release_checklist.md':('Published identity: `1.6.0`','Citation date: `2026-10-08`','O7 is complete',VERSION_DOI,'eebc163ef2f17333d11d62fcbc4135bc0f9a4b1f')}
    for name,values in markers.items():
        if any(x not in (root/name).read_text(encoding='utf-8') for x in values):raise ValueError('inconsistent final candidate declaration: '+name)
    return {'status':'published_identity_consistency_pass','release_version':RELEASE_VERSION,
        'citation_date':RELEASE_DATE,'version_specific_doi':VERSION_DOI,'concept_doi':CONCEPT_DOI}


def validate(root):
    from scripts.validate_v1_6_api_review import validate as review
    return {**validate_identity(root),'api':review(root)}


if __name__=='__main__':print(json.dumps(validate(ROOT),indent=2))
