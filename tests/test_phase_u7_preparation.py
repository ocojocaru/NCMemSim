# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Retained source membership and tamper rejection for the U7 gate."""
import hashlib
import json
from pathlib import Path

import pytest

from scripts.validate_v1_12_preparation import validate, validate_sources


def test_review_matches_current_sources():
    result = validate()
    assert result['additive_modules'] == 2
    assert result['additive_exports'] == 4


def test_review_pins_published_baseline():
    import subprocess
    root = Path(__file__).resolve().parents[1]
    review = json.loads((root / 'docs/v1_12_api_review.json').read_text(encoding='utf-8'))
    baseline = review['baseline_commit']
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', baseline,
                                     '--', 'ncmemsim'], cwd=root, text=True).splitlines()
    expected = {p: hashlib.sha256(subprocess.check_output(
        ['git', 'show', baseline + ':' + p], cwd=root)).hexdigest()
        for p in paths if p.endswith('.py')}
    assert review['published_sources'] == expected


def test_source_changes_and_extra_modules_rejected(tmp_path):
    package = tmp_path / 'ncmemsim'
    package.mkdir()
    source = package / 'original.py'
    source.write_bytes(b'original = True\n')
    review = {'published_sources': {'ncmemsim/original.py': hashlib.sha256(source.read_bytes()).hexdigest()},
              'additions': {}}
    assert validate_sources(tmp_path, review)['retained_modules'] == 1
    source.write_bytes(b'original = False\n')
    with pytest.raises(ValueError, match='source drift'):
        validate_sources(tmp_path, review)
    source.write_bytes(b'original = True\n')
    (package / 'extra.py').write_bytes(b'')
    with pytest.raises(ValueError, match='membership'):
        validate_sources(tmp_path, review)
