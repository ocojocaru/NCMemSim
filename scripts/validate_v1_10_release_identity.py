# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Published v1.10.0 identity and confirmed Zenodo archival."""
from pathlib import Path
import ast
from hashlib import sha256
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
PUBLISHED_SNAPSHOT = Path('tests/fixtures/releases/v1_10_0')
# Published metadata closure 46ec695aba82978e1bb115bb5647f7fed69f0898.
PUBLISHED_HASHES = {
    'ncmemsim/_version.py': '5902c282291346a2803f1bc91def6815eb435bf161baa51454a2a099e9e4f497',
    'CITATION.cff': '9660901b99d4bfda732b00631be50f42afd29b4c816348de13473dc7b6f75976',
    'README.md': 'ee41ad207cf551c4be88dd7b59192a5c3d2519daa883eb6b85bad90fdf7cfed3',
    'CHANGELOG.md': '5a04a8dde6233cdd177080ac983e54e971c4bd1c3dd95712d75c47a5f7c9cf04',
    'docs/index.md': 'b965a6807281d163bde442c391865d14f377fff68c73b82a81b56df151c6f3c9',
    'docs/archival_citation.md': 'fc8ba55cff99700fb35f3aa06669e943f2b607baefb64bd29a24f3d71a7de5e1',
    'docs/roadmap.md': '333cf6a24ddbbe5ce4775a391fbc97ea1831d670c501919c34e786661c8c6ff0',
    'docs/v1_10_release_checklist.md': '6e6a95e816084ff135f791e175c9e4787b2abd37c006ed885e961f6a60fdc440',
}


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
    snapshot = Path(root) / PUBLISHED_SNAPSHOT
    for name, expected in PUBLISHED_HASHES.items():
        content = (snapshot / name).read_text(encoding='utf-8')
        if sha256(content.encode('utf-8')).hexdigest() != expected:
            raise ValueError('published v1.10 snapshot drift: ' + name)
    return {**validate_identity(snapshot), 'api': review(root)}


if __name__=='__main__':
    import json
    print(json.dumps(validate(ROOT),indent=2))
