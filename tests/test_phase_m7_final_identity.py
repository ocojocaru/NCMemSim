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


def test_final_identity_is_aligned_without_publication_approval():
    result = validate(ROOT)
    assert result['status'] == 'final_candidate_identity_pass_not_release_approval'
    assert result['release_version'] == '1.4.0'
    assert result['citation_date'] == '2026-10-02'
    assert result['version_specific_doi'] is None
    assert result['concept_doi'] == '10.5281/zenodo.23078330'
    assert result['api']['retained_stable_paths'] == 297


@pytest.mark.parametrize('name,old,new', [
    ('ncmemsim/_version.py','"1.4.0"','"1.4.0.dev0"'),
    ('CITATION.cff','version: 1.4.0','version: 1.3.0'),
    ('CITATION.cff','date-released: 2026-10-02','date-released: 2026-10-01'),
    ('CITATION.cff','value: 10.5281/zenodo.23078330','value: 10.0000/unassigned'),
    ('CITATION.cff','license: Apache-2.0','license: unknown'),
    ('README.md','**Release candidate:** `1.4.0`','release approved'),
    ('README.md','**Latest published stable release:** `1.3.0`','**Current stable release:** `1.4.0`'),
    ('CHANGELOG.md','## 1.4.0 — 2026-10-02 (release candidate; publication pending)','## 1.4.0 published'),
    ('docs/index.md','Final release candidate: `1.4.0`','Published stable release: `1.4.0`'),
    ('docs/temperature_properties.md','Final candidate identity: `1.4.0`','stale'),
    ('docs/roadmap.md','final candidate identity `1.4.0`','stale'),
    ('docs/v1_4_release_checklist.md','Final candidate identity: `1.4.0`','stale'),
])
def test_final_identity_rejects_partial_or_premature_release_updates(final_copy,name,old,new):
    path=final_copy/name;text=path.read_text(encoding='utf-8');assert old in text
    path.write_text(text.replace(old,new),encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(final_copy)


@pytest.mark.parametrize('doi',['10.5281/zenodo.23079171','10.5281/zenodo.23078330','10.0000/unassigned'])
def test_final_candidate_rejects_any_unconfirmed_top_level_doi(final_copy,doi):
    path=final_copy/'CITATION.cff'
    path.write_text(path.read_text(encoding='utf-8')+'\ndoi: '+doi+'\n',encoding='utf-8')
    with pytest.raises(ValueError,match='v1.4-specific DOI'):validate_identity(final_copy)


def test_explicit_development_snapshot_retains_published_v1_3_citation(final_copy):
    (final_copy/'ncmemsim/_version.py').write_text('__version__="1.4.0.dev0"\n',encoding='utf-8')
    shutil.copyfile(ROOT/'tests/fixtures/releases/v1_3_0/CITATION.cff',final_copy/'CITATION.cff')
    path=final_copy/'README.md'
    text=path.read_text(encoding='utf-8').replace('**Release candidate:** `1.4.0`','**Development version:** `1.4.0.dev0`').replace('**Latest published stable release:**','**Current stable release:**')
    path.write_text(text,encoding='utf-8')
    result=api.validate(final_copy)
    assert result['package_version']=='1.4.0.dev0' and result['citation_version']=='1.3.0'
    with pytest.raises(ValueError):validate_identity(final_copy)


def test_preparation_ci_is_not_claimed_as_final_candidate_approval():
    text=(ROOT/'docs/v1_4_release_checklist.md').read_text(encoding='utf-8')
    assert 'dc79dd625ead691c9c3c3512ed8eebbb4a641b53' in text
    assert '36993597402' in text and '36993597377' in text
    assert 'not approval of the final candidate' in text
    assert 'exact' in text and 'M7 is not complete' in text
