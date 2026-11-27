# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Verify the unpublished v1.12 candidate and retained published identity."""
import ast
from datetime import date
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_v1_2_release_identity import _citation_field
from scripts.validate_v1_11_release_identity import validate_retained
from scripts.validate_v1_12_preparation import validate as validate_sources

VERSION = '1.12.0'
CANDIDATE_DATE = '2026-11-27'
CONCEPT_DOI = '10.5281/zenodo.23078330'


def validate_identity(root):
    root = Path(root)
    tree = ast.parse((root / 'ncmemsim/_version.py').read_text(encoding='utf-8'))
    versions = [ast.literal_eval(n.value) for n in tree.body
                if isinstance(n, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == '__version__' for t in n.targets)]
    if versions != [VERSION]:
        raise ValueError('candidate package version mismatch')
    citation = (root / 'CITATION.cff').read_text(encoding='utf-8')
    date.fromisoformat(CANDIDATE_DATE)
    for field, expected in (('version', VERSION), ('date-released', CANDIDATE_DATE), ('license', 'Apache-2.0')):
        if (_citation_field(citation, field) != expected
                or len(re.findall(rf'(?m)^{field}\s*:', citation)) != 1):
            raise ValueError('candidate citation mismatch: ' + field)
    if re.search(r'(?m)^doi\s*:', citation):
        raise ValueError('unpublished candidate must not declare a version DOI')
    identifiers = 'identifiers:\n  - type: doi\n    value: ' + CONCEPT_DOI + '\n'
    if (identifiers not in citation or len(re.findall(r'(?m)^identifiers\s*:', citation)) != 1
            or re.findall(r'10\.\d{4,9}/[^\s"\']+', citation) != [CONCEPT_DOI]):
        raise ValueError('candidate requires the separate Concept DOI only')
    for name, marker in (
        ('README.md', '**Final v1.12.0 candidate:**'),
        ('docs/index.md', '**Final v1.12.0 candidate:**'),
        ('CHANGELOG.md', '## 1.12.0 - 2026-11-27 (unpublished candidate)'),
        ('docs/archival_citation.md', '## Unpublished v1.12.0 candidate citation'),
        ('docs/v1_12_release_checklist.md', 'Candidate identity: `1.12.0`, dated 2026-11-27.'),
    ):
        if marker not in (root / name).read_text(encoding='utf-8'):
            raise ValueError('candidate declaration mismatch: ' + name)
    return {'package_version': VERSION, 'release_published': False, 'version_specific_doi': None}


def validate(root=ROOT):
    validate_retained(root)
    return {**validate_identity(root), 'api': validate_sources(root)}


if __name__ == '__main__':
    print('v1.12.0 candidate identity PASS:', validate())
