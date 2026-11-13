# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Check the v1.11.0 package, citation and candidate declarations."""
import ast
from datetime import date
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_v1_2_release_identity import _citation_field
from scripts.validate_v1_10_release_identity import CONCEPT_DOI

VERSION = '1.11.0'
CANDIDATE_DATE = '2026-11-11'


def validate_identity(root):
    root = Path(root)
    tree = ast.parse((root / 'ncmemsim/_version.py').read_text(encoding='utf-8'))
    versions = [
        ast.literal_eval(node.value) for node in tree.body
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == '__version__' for target in node.targets
        )
    ]
    if versions != [VERSION]:
        raise ValueError('expected one v1.11.0 package version')
    citation = (root / 'CITATION.cff').read_text(encoding='utf-8')
    date.fromisoformat(CANDIDATE_DATE)
    for field, expected in (
        ('version', VERSION), ('date-released', CANDIDATE_DATE), ('license', 'Apache-2.0'),
    ):
        if _citation_field(citation, field) != expected or len(re.findall(rf'(?m)^{field}\s*:', citation)) != 1:
            raise ValueError(f'candidate citation mismatch: {field}')
    concept = 'identifiers:\n  - type: doi\n    value: ' + CONCEPT_DOI + '\n'
    if (concept not in citation or len(re.findall(r'(?m)^identifiers\s*:', citation)) != 1
        or re.search(r'(?m)^doi\s*:', citation)
        or re.findall(r'10\.\d{4,9}/[^\s"\']+', citation) != [CONCEPT_DOI]):
        raise ValueError('candidate citation requires the Concept DOI alone')
    for name, marker in (
        ('CHANGELOG.md', f'## {VERSION} - {CANDIDATE_DATE}'),
        ('README.md', '**v1.11.0 release candidate**'),
        ('docs/index.md', '**v1.11.0 release candidate**'),
        ('docs/archival_citation.md', '## v1.11.0 candidate citation'),
        ('docs/v1_11_release_checklist.md', f'Candidate identity: `{VERSION}`, dated {CANDIDATE_DATE}.'),
    ):
        if marker not in (root / name).read_text(encoding='utf-8'):
            raise ValueError(f'candidate declaration mismatch: {name}')


if __name__ == '__main__':
    validate_identity(ROOT)
    print('v1.11.0 candidate identity PASS')
