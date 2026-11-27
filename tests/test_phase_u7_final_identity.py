# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Candidate citation, reviewed version-only change and historical snapshot tests."""
import hashlib
import shutil
import subprocess

import pytest

from scripts.validate_v1_11_release_identity import PUBLISHED_HASHES, SNAPSHOT
from scripts.validate_v1_12_release_identity import ROOT, validate, validate_identity
from scripts.validate_v1_12_preparation import validate_sources


def test_candidate_and_retained_sources():
    result = validate(ROOT)
    assert result['package_version'] == '1.12.0'
    assert not result['release_published'] and result['version_specific_doi'] is None
    assert result['api']['additive_exports'] == 4


@pytest.fixture
def candidate_copy(tmp_path):
    for name in ('ncmemsim/_version.py', 'CITATION.cff', 'README.md', 'CHANGELOG.md',
                 'docs/index.md', 'docs/archival_citation.md', 'docs/v1_12_release_checklist.md'):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, path)
    return tmp_path


@pytest.mark.parametrize('name,old,new', [
    ('ncmemsim/_version.py', '1.12.0', '1.11.0'),
    ('CITATION.cff', 'version: 1.12.0', 'version: 1.11.0'),
    ('CITATION.cff', 'date-released: 2026-11-27', 'date-released: 2026-11-16'),
    ('CITATION.cff', 'license: Apache-2.0', 'license: MIT'),
    ('README.md', '**Final v1.12.0 candidate:**', 'stale'),
    ('docs/index.md', '**Final v1.12.0 candidate:**', 'stale'),
    ('CHANGELOG.md', '## 1.12.0 - 2026-11-27 (unpublished candidate)', 'stale'),
    ('docs/v1_12_release_checklist.md', 'Candidate identity: `1.12.0`', 'stale'),
])
def test_partial_candidate_rejected(candidate_copy, name, old, new):
    path = candidate_copy / name
    source = path.read_text(encoding='utf-8')
    assert old in source
    path.write_text(source.replace(old, new), encoding='utf-8')
    with pytest.raises(ValueError):
        validate_identity(candidate_copy)


@pytest.mark.parametrize('line', [
    'doi: 10.5281/zenodo.24273310', 'doi: 10.5281/zenodo.23078330',
    'doi: 10.0000/unassigned', 'version: 1.12.0', 'date-released: 2026-11-27',
])
def test_stale_or_duplicate_citation_rejected(candidate_copy, line):
    path = candidate_copy / 'CITATION.cff'
    path.write_text(path.read_text(encoding='utf-8') + line + '\n', encoding='utf-8')
    with pytest.raises(ValueError):
        validate_identity(candidate_copy)


def test_snapshot_matches_published_metadata_commit():
    for name, digest in PUBLISHED_HASHES.items():
        original = subprocess.check_output(
            ['git', 'show', '1f6efa1fd4f57a4a404e49b2615fadec8b4f7dd4:' + name], cwd=ROOT)
        assert hashlib.sha256(original).hexdigest() == digest
        assert (ROOT / SNAPSHOT / name).read_text(encoding='utf-8') == original.decode('utf-8')


def test_version_exception_preserves_all_other_source_bytes(tmp_path):
    package = tmp_path / 'ncmemsim'
    package.mkdir()
    original = '# original header\n__version__ = "1.11.0"\n'
    request = {'published_sources': {'ncmemsim/_version.py': hashlib.sha256(original.encode()).hexdigest()},
               'additions': {}}
    path = package / '_version.py'
    path.write_text(original.replace('1.11.0', '1.12.0'), encoding='utf-8')
    validate_sources(tmp_path, request)
    path.write_text(path.read_text(encoding='utf-8') + '# unreviewed change\n', encoding='utf-8')
    with pytest.raises(ValueError, match='source drift'):
        validate_sources(tmp_path, request)
