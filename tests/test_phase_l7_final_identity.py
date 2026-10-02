# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import shutil
import pytest
from scripts.validate_v1_3_release_identity import validate

ROOT = Path(__file__).resolve().parents[1]


def test_final_candidate_identity_is_aligned_without_release_approval(published_v1_3_copy):
    result = validate(published_v1_3_copy)
    assert result['release_version'] == '1.3.0'
    assert result['status'] == 'published_release_identity_pass'


@pytest.mark.parametrize('name,old,new', [
    ('ncmemsim/_version.py', '"1.3.0"', '"1.3.0.dev0"'),
    ('CITATION.cff', 'version: 1.3.0', 'version: 1.2.0'),
    ('CITATION.cff', 'date-released: 2026-10-01', 'date-released: 2026-09-30'),
    ('README.md', '**Current stable release:** `1.3.0`', '**Current stable release:** `1.2.0`'),
    ('CHANGELOG.md', '## 1.3.0 — 2026-10-01', '## 1.2.0 — 2026-10-01'),
])
def test_final_identity_rejects_partial_release_updates(published_v1_3_copy, name, old, new):
    tmp_path = published_v1_3_copy
    path = tmp_path / name
    text = path.read_text(encoding='utf-8')
    assert old in text
    path.write_text(text.replace(old, new), encoding='utf-8')
    with pytest.raises(ValueError):
        validate(tmp_path)


def test_v1_2_archive_doi_cannot_be_assigned_to_v1_3_candidate(published_v1_3_copy):
    tmp_path = published_v1_3_copy
    citation = tmp_path / 'CITATION.cff'
    citation.write_text(citation.read_text(encoding='utf-8') + '\ndoi: 10.5281/zenodo.23078331\n', encoding='utf-8')
    with pytest.raises(ValueError, match='version-specific DOI'):
        validate(tmp_path)
