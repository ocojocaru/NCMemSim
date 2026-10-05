# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Final v1.4 version/citation/status alignment and historical preparation boundary."""
from pathlib import Path
import shutil
import pytest
from scripts.validate_v1_4_release_identity import validate, validate_identity
from scripts import validate_v1_4_api_review as api

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def final_copy(tmp_path):
    for folder in ('docs', 'ncmemsim', 'tests/fixtures'):
        shutil.copytree(ROOT/folder, tmp_path/folder)
    for name in ('README.md', 'CHANGELOG.md', 'CITATION.cff'):
        shutil.copyfile(ROOT/name, tmp_path/name)
    return tmp_path


def test_published_identity_matches_confirmed_doi():
    result = validate(ROOT)
    assert result['status'] == 'published_identity_consistency_pass'
    assert result['release_version'] == '1.4.0'
    assert result['citation_date'] == '2026-10-02'
    assert result['version_specific_doi'] == '10.5281/zenodo.23102549'
    assert result['concept_doi'] == '10.5281/zenodo.23078330'
    assert result['api']['retained_stable_paths'] == 297


@pytest.mark.parametrize('name,old,new', [
    ('ncmemsim/_version.py','"1.4.0"','"1.4.0.dev0"'),
    ('CITATION.cff','version: 1.4.0','version: 1.3.0'),
    ('CITATION.cff','date-released: 2026-10-02','date-released: 2026-10-01'),
    ('CITATION.cff','value: 10.5281/zenodo.23078330','value: 10.0000/unassigned'),
    ('CITATION.cff','license: Apache-2.0','license: unknown'),
    ('README.md','**Current stable release:** `1.4.0`','release approved'),
    ('README.md','Phase M is complete','Phase M pending'),
    ('CHANGELOG.md','## 1.4.0 — 2026-10-02','## 1.4.0 published'),
    ('docs/index.md','Published stable release: `1.4.0`','stale'),
    ('docs/temperature_properties.md','Published identity: `1.4.0`','stale'),
    ('docs/roadmap.md','published stable release `1.4.0`','stale'),
    ('docs/v1_4_release_checklist.md','Published identity: `1.4.0`','stale'),
])
def test_final_identity_rejects_partial_or_premature_release_updates(final_copy,name,old,new):
    path=final_copy/name;text=path.read_text(encoding='utf-8');assert old in text
    path.write_text(text.replace(old,new),encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(final_copy)


@pytest.mark.parametrize('doi',['10.5281/zenodo.23079171','10.5281/zenodo.23078330','10.0000/unassigned'])
def test_published_identity_rejects_wrong_version_specific_doi(final_copy,doi):
    path=final_copy/'CITATION.cff'
    path.write_text(path.read_text(encoding='utf-8').replace('10.5281/zenodo.23102549',doi),encoding='utf-8')
    with pytest.raises(ValueError,match='v1.4-specific DOI'):validate_identity(final_copy)


def test_explicit_development_snapshot_retains_published_v1_3_citation(final_copy):
    (final_copy/'ncmemsim/_version.py').write_text('__version__="1.4.0.dev0"\n',encoding='utf-8')
    shutil.copyfile(ROOT/'tests/fixtures/releases/v1_3_0/CITATION.cff',final_copy/'CITATION.cff')
    path=final_copy/'README.md'
    text=path.read_text(encoding='utf-8').replace('**Current stable release:** `1.4.0`','**Development version:** `1.4.0.dev0`').replace('**Latest published stable release:**','**Current stable release:**')
    path.write_text(text,encoding='utf-8')
    for name in ('docs/temperature_properties.md','docs/roadmap.md'):
        with (final_copy/name).open('a',encoding='utf-8') as handle:
            handle.write('\nM7 preparation is implemented; release approval remains pending.\n')
    with (final_copy/'docs/v1_4_release_checklist.md').open('a',encoding='utf-8') as handle:
        handle.write('\nStatus: M7 preparation implemented; release approval remains pending.\nNo tag, merge or release publication\n')
    path=final_copy/'README.md'
    path.write_text(path.read_text(encoding='utf-8')+'\n**Current stable release:** `1.3.0`\n',encoding='utf-8')
    result=api.validate(final_copy)
    assert result['package_version']=='1.4.0.dev0' and result['citation_version']=='1.3.0'
    with pytest.raises(ValueError):validate_identity(final_copy)


def test_preparation_ci_is_not_claimed_as_final_candidate_approval():
    text=(ROOT/'docs/v1_4_release_checklist.md').read_text(encoding='utf-8')
    assert 'dc79dd625ead691c9c3c3512ed8eebbb4a641b53' in text
    assert '36993597402' in text and '36993597377' in text
    assert 'not approval of the final candidate' in text
    assert '67e8791a6ec5c3a76fc8f92bcba4da614900f4f5' in text
    assert '37004354221' in text and 'M7 is complete' in text


@pytest.mark.parametrize('fault', ['missing', 'duplicate'])
def test_published_identity_requires_one_version_specific_doi(final_copy, fault):
    path = final_copy/'CITATION.cff'
    text = path.read_text(encoding='utf-8')
    line = 'doi: 10.5281/zenodo.23102549\n'
    text = text.replace(line, '') if fault == 'missing' else text + '\n' + line
    path.write_text(text, encoding='utf-8')
    with pytest.raises(ValueError, match='v1.4-specific DOI'):
        validate_identity(final_copy)
