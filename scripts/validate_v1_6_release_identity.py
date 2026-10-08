# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Final v1.6 candidate identity consistency; publication/DOI remain pending."""
from pathlib import Path
from datetime import date
import ast,json,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.validate_v1_2_release_identity import _citation_field
RELEASE_VERSION='1.6.0'
RELEASE_DATE='2026-10-08'
CONCEPT_DOI='10.5281/zenodo.23078330'


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
    if re.search(r'(?m)^doi\s*:',citation):raise ValueError('no v1.6-specific DOI before the actual deposit')
    concept='identifiers:\n  - type: doi\n    value: '+CONCEPT_DOI+'\n    description: "Concept DOI representing all published versions"'
    if concept not in citation or _citation_field(citation,'license')!='Apache-2.0':raise ValueError('Concept DOI/license mismatch')
    markers={'README.md':('**Final candidate version:** `1.6.0`','publication and version-specific DOI pending','**Current stable release:** `1.5.0`'),
        'CHANGELOG.md':('## 1.6.0 — 2026-10-08 (final candidate; publication pending)',),
        'docs/index.md':('Final v1.6.0 candidate: `1.6.0`','publication and version-specific DOI pending'),
        'docs/archival_citation.md':('final v1.6.0 candidate dated 2026-10-08','No v1.6-specific DOI is assigned'),
        'docs/roadmap.md':('Final candidate identity: `1.6.0`','O7 is not complete'),
        'docs/strain_confinement.md':('Final candidate identity: `1.6.0`','publication and version-specific DOI pending'),
        'docs/v1_6_release_checklist.md':('Final candidate identity: `1.6.0`','Citation date: `2026-10-08`','O7 is not complete','dcee61c47f62659f95e5c6c6bb54d4d14ee3f5c0')}
    for name,values in markers.items():
        if any(x not in (root/name).read_text(encoding='utf-8') for x in values):raise ValueError('inconsistent final candidate declaration: '+name)
    return {'status':'final_candidate_identity_pass_not_publication','release_version':RELEASE_VERSION,
        'citation_date':RELEASE_DATE,'version_specific_doi':None,'concept_doi':CONCEPT_DOI}


def validate(root):
    from scripts.validate_v1_6_api_review import validate as review
    return {**validate_identity(root),'api':review(root)}


if __name__=='__main__':print(json.dumps(validate(ROOT),indent=2))
