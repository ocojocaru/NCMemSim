# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Validate the reviewed v1.4 final identity for the published release."""
from __future__ import annotations
import ast
from datetime import date
import json
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.validate_v1_2_release_identity import _citation_field

RELEASE_VERSION = '1.4.0'
RELEASE_DATE = '2026-10-02'
CONCEPT_DOI = '10.5281/zenodo.23078330'
VERSION_DOI = '10.5281/zenodo.23102549'


def validate_identity(root: Path) -> dict:
    tree = ast.parse((root/'ncmemsim/_version.py').read_text(encoding='utf-8'))
    versions = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == '__version__' for t in n.targets)]
    if versions != [RELEASE_VERSION]:
        raise ValueError('final candidate package version must be 1.4.0')
    citation = (root/'CITATION.cff').read_text(encoding='utf-8')
    if _citation_field(citation, 'version') != RELEASE_VERSION:
        raise ValueError('final candidate citation version mismatch')
    released = _citation_field(citation, 'date-released')
    if released != RELEASE_DATE:
        raise ValueError('candidate citation date differs from reviewed release date')
    date.fromisoformat(released)
    if len(re.findall(r'(?m)^doi\s*:', citation)) != 1 or _citation_field(citation, 'doi') != VERSION_DOI:
        raise ValueError('v1.4-specific DOI must match the author-confirmed deposit')
    expected = 'identifiers:\n  - type: doi\n    value: '+CONCEPT_DOI+'\n    description: "Concept DOI representing all published versions"'
    if expected not in citation or _citation_field(citation, 'license') != 'Apache-2.0':
        raise ValueError('candidate must retain separate Concept DOI and Apache-2.0 license')
    markers = {
        'README.md': ('**Current stable release:** `1.4.0`', 'Phase M is complete'),
        'CHANGELOG.md': ('## 1.4.0 — 2026-10-02',),
        'docs/index.md': ('Published stable release: `1.4.0`', VERSION_DOI),
        'docs/temperature_properties.md': ('Published identity: `1.4.0`', 'M7 is complete', VERSION_DOI),
        'docs/roadmap.md': ('published stable release `1.4.0`', 'M7 is complete', VERSION_DOI),
        'docs/v1_4_release_checklist.md': ('Published identity: `1.4.0`', 'M7 is complete', VERSION_DOI, '67e8791a6ec5c3a76fc8f92bcba4da614900f4f5'),
    }
    for name, required in markers.items():
        text = (root/name).read_text(encoding='utf-8')
        if any(marker not in text for marker in required):
            raise ValueError('inconsistent final candidate declaration: '+name)
    return {'status': 'published_identity_consistency_pass',
            'release_version': RELEASE_VERSION, 'citation_date': released,
            'version_specific_doi': VERSION_DOI, 'concept_doi': CONCEPT_DOI}


def validate(root: Path) -> dict:
    identity = validate_identity(root)
    from scripts.validate_v1_4_api_review import validate as validate_api
    return {**identity, 'api': validate_api(root)}


if __name__ == '__main__':
    print(json.dumps(validate(ROOT), indent=2))
