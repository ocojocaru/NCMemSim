# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Check the v1.11.0 package, citation and publication declarations."""
import ast
import argparse
import hashlib
import json
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
PUBLICATION_DATE = '2026-11-16'
VERSION_DOI = '10.5281/zenodo.24273310'


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
    date.fromisoformat(PUBLICATION_DATE)
    for field, expected in (
        ('doi', VERSION_DOI), ('version', VERSION), ('date-released', PUBLICATION_DATE), ('license', 'Apache-2.0'),
    ):
        if _citation_field(citation, field) != expected or len(re.findall(rf'(?m)^{field}\s*:', citation)) != 1:
            raise ValueError(f'published citation mismatch: {field}')
    concept = 'identifiers:\n  - type: doi\n    value: ' + CONCEPT_DOI + '\n'
    if (concept not in citation or len(re.findall(r'(?m)^identifiers\s*:', citation)) != 1
        or re.findall(r'10\.\d{4,9}/[^\s"\']+', citation) != [VERSION_DOI, CONCEPT_DOI]):
        raise ValueError('published citation requires version and Concept DOIs')
    for name, marker in (
        ('CHANGELOG.md', f'## {VERSION} - {PUBLICATION_DATE}'),
        ('README.md', '**Published v1.11.0 status:**'),
        ('docs/index.md', '**Published v1.11.0 status:**'),
        ('docs/archival_citation.md', '## Published v1.11.0 citation'),
        ('docs/v1_11_release_checklist.md', f'Published identity: `{VERSION}`, dated {PUBLICATION_DATE}.'),
    ):
        if marker not in (root / name).read_text(encoding='utf-8'):
            raise ValueError(f'published declaration mismatch: {name}')


SNAPSHOT = 'tests/fixtures/releases/v1_11_0'
PUBLISHED_HASHES = {'ncmemsim/_version.py': '416a31bef6bf2426b38539df350fca523404e4a339d88e4fa1d692b41f2b9905', 'CITATION.cff': '3452143c0a03aa2de3b0dfd985ac93b7df8f59f195354b477677757f2637695b', 'CHANGELOG.md': '4a3dccd7809262f423f0e17e6dbdc1c0c76a3637c82dbe8b7bac2399fa119026', 'README.md': 'cf534fc5b16535e30e8ab2bb707f696f33256d6deb035097c53ff2fe1e95c4de', 'docs/index.md': 'ed073eb3d1cb8547ff59c0e4b0f4fead448da349acbb94165a8b7ea286686b2f', 'docs/archival_citation.md': 'b5c222710d8d20739316c6172f0cdfdd9eda556cb5b27eeda166e45f21b0f325', 'docs/v1_11_release_checklist.md': '98013b2c52032bd742dd5985624caa8fa65bf1b885a06fc9adfeed4b498ef232'}


def validate_retained(root=ROOT):
    snapshot = Path(root) / SNAPSHOT
    declaration = json.loads((snapshot / 'snapshot.json').read_text(encoding='utf-8'))
    if declaration != {'capture_commit': '1f6efa1fd4f57a4a404e49b2615fadec8b4f7dd4', 'files': PUBLISHED_HASHES}:
        raise ValueError('published v1.11 snapshot declaration drift')
    for name, digest in PUBLISHED_HASHES.items():
        source = (snapshot / name).read_text(encoding='utf-8')
        if hashlib.sha256(source.encode('utf-8')).hexdigest() != digest:
            raise ValueError('published v1.11 snapshot drift: ' + name)
    validate_identity(snapshot)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retained', action='store_true')
    args = parser.parse_args()
    if args.retained:
        validate_retained()
    else:
        validate_identity(ROOT)
    print('v1.11.0 published identity PASS')
