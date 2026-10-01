# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Validate final candidate identity without asserting publication or remote approval."""
from __future__ import annotations
import ast
from datetime import date
import json
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.validate_v1_3_api_review import validate as validate_api
from scripts.validate_v1_2_release_identity import _citation_field

ROOT = Path(__file__).resolve().parents[1]


def validate(root: Path) -> dict:
    tree = ast.parse((root / 'ncmemsim/_version.py').read_text(encoding='utf-8'))
    versions = [ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '__version__' for t in node.targets)]
    if versions != ['1.3.0']:
        raise ValueError('final candidate package version must be 1.3.0')
    citation = (root / 'CITATION.cff').read_text(encoding='utf-8')
    if _citation_field(citation, 'version') != '1.3.0':
        raise ValueError('citation version does not match final candidate')
    released = _citation_field(citation, 'date-released')
    if released != '2026-10-01':
        raise ValueError('candidate citation date differs from reviewed release date')
    date.fromisoformat(released)
    published = '**Current stable release:** `1.3.0`' in (root / 'README.md').read_text(encoding='utf-8')
    dois = re.findall(r'(?m)^doi\s*:\s*(\S+)\s*$', citation)
    if published and dois != ['10.5281/zenodo.23079171']:
        raise ValueError('version-specific DOI must match the author-confirmed v1.3.0 deposit')
    if not published and dois:
        raise ValueError('version-specific DOI requires verification of the v1.3.0 deposit; the Concept DOI belongs in identifiers')
    required = {
        'README.md': ('**Release candidate:** `1.3.0`', '**Latest published stable release:** `1.2.0`'),
        'CHANGELOG.md': ('## 1.3.0 \u2014 2026-10-01 (release candidate; publication pending)',),
        'docs/index.md': ('`1.3.0` release candidate',),
        'docs/model_variability.md': ('final candidate identity 1.3.0',),
        'docs/v1_3_release_checklist.md': ('Final candidate identity: `1.3.0`', 'final release approval is pending'),
    }
    if published:
        required = {
            'README.md': ('**Current stable release:** `1.3.0`',),
            'CHANGELOG.md': ('## 1.3.0 \u2014 2026-10-01',),
            'docs/index.md': ('current stable release `1.3.0`',),
            'docs/model_variability.md': ('L7 is complete',),
            'docs/v1_3_release_checklist.md': ('Status: L7 complete', '4319cbc899191bd1cafbd79c4a7df20c1d490d10'),
        }
    for name, markers in required.items():
        text = (root / name).read_text(encoding='utf-8')
        if any(marker not in text for marker in markers):
            raise ValueError('inconsistent final candidate declaration: ' + name)
    review = validate_api(root)
    return {'status': 'published_release_identity_pass' if published else 'final_candidate_identity_pass_not_release_approval',
            'release_version': '1.3.0', 'citation_date': released, 'api': review}


if __name__ == '__main__':
    # Direct script execution needs the repository on sys.path.
    print(json.dumps(validate(ROOT), indent=2))
