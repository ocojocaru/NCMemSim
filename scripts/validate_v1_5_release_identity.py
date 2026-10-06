# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Final v1.5 candidate identity consistency; not publication approval."""
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.validate_v1_4_api_review import _version
from scripts.validate_v1_2_release_identity import _citation_field

def validate_identity(root):
    if _version(root)!='1.5.0':raise ValueError('final package version must be 1.5.0')
    citation=(root/'CITATION.cff').read_text(encoding='utf-8')
    if _citation_field(citation,'version')!='1.5.0' or _citation_field(citation,'date-released')!='2026-10-06':raise ValueError('final citation version/date mismatch')
    if re.search(r'(?m)^doi\s*:',citation):raise ValueError('v1.5 DOI requires actual deposit confirmation')
    if _citation_field(citation,'license')!='Apache-2.0' or 'value: 10.5281/zenodo.23078330' not in citation:raise ValueError('Concept DOI/license mismatch')
    markers={'README.md':('**Release candidate:** `1.5.0`','**Current stable release:** `1.4.0`'),
        'CHANGELOG.md':('## 1.5.0 — 2026-10-06 (release candidate; publication pending)',),
        'docs/index.md':('Final release candidate: `1.5.0`',),
        'docs/broadband_optics.md':('Final candidate identity: `1.5.0`','release approval remains pending'),
        'docs/roadmap.md':('final candidate identity `1.5.0`','release approval remains pending'),
        'docs/v1_5_release_checklist.md':('Final candidate identity: `1.5.0`','N7 is not complete')}
    for name,required in markers.items():
        text=(root/name).read_text(encoding='utf-8')
        if any(x not in text for x in required):raise ValueError('inconsistent final candidate declaration: '+name)
    return {'status':'final_candidate_identity_pass_not_release_approval','release_version':'1.5.0','citation_date':'2026-10-06','version_specific_doi':None}

def validate(root):
    from scripts.validate_v1_5_api_review import validate as review
    return {**validate_identity(root),'api':review(root)}

if __name__=='__main__':print(json.dumps(validate(ROOT),indent=2))
