# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Final candidate identity, unpublished DOI policy and retained v1.9 source fence."""
from pathlib import Path
import shutil
import pytest
from scripts.validate_v1_10_release_identity import PUBLISHED_SNAPSHOT, validate, validate_identity
from scripts import validate_v1_9_api_review as historical
ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def candidate_copy(tmp_path):
    shutil.copytree(ROOT / PUBLISHED_SNAPSHOT, tmp_path, dirs_exist_ok=True)
    return tmp_path


def test_final_identity_and_current_review():
    result=validate(ROOT)
    assert result['package_version']=='1.10.0' and result['citation_date']=='2026-11-05'
    assert result['release_published'] and result['version_specific_doi']=='10.5281/zenodo.23973765'
    assert result['latest_published_stable']=='1.10.0'
    assert result['api']['retained_published_modules']==146 and result['api']['additive_exports']==16


@pytest.mark.parametrize('name,old,new',[
    ('ncmemsim/_version.py','1.10.0','1.9.0'),
    ('CITATION.cff','version: 1.10.0','version: 1.9.0'),
    ('CITATION.cff','date-released: 2026-11-05','date-released: 2026-10-26'),
    ('CITATION.cff','23078330','23664613'),
    ('CITATION.cff','license: Apache-2.0','license: MIT'),
    ('README.md','**Published v1.10.0 status:**','stale'),
    ('docs/index.md','Latest published stable: `1.10.0`','stale'),
    ('docs/v1_10_release_checklist.md','Published identity: `1.10.0`','stale'),
    ('CHANGELOG.md','## 1.10.0 - 2026-11-05','stale')])
def test_partial_identity_rejected(candidate_copy,name,old,new):
    path=candidate_copy/name;text=path.read_text(encoding='utf-8');assert old in text
    path.write_text(text.replace(old,new),encoding='utf-8')
    with pytest.raises(ValueError): validate_identity(candidate_copy)


@pytest.mark.parametrize('doi',['10.5281/zenodo.23664613','10.5281/zenodo.23078330','10.0000/unassigned'])
def test_candidate_must_not_reuse_or_invent_version_doi(candidate_copy,doi):
    path=candidate_copy/'CITATION.cff'
    path.write_text(path.read_text(encoding='utf-8').replace('doi: 10.5281/zenodo.23973765','doi: '+doi),encoding='utf-8')
    with pytest.raises(ValueError,match='DOI'): validate_identity(candidate_copy)


@pytest.mark.parametrize('line',['version: 1.10.0','date-released: 2026-11-05','identifiers:','license: Apache-2.0'])
def test_duplicate_citation_fields_rejected(candidate_copy,line):
    path=candidate_copy/'CITATION.cff'
    path.write_text(path.read_text(encoding='utf-8')+line+'\n',encoding='utf-8')
    with pytest.raises(ValueError): validate_identity(candidate_copy)


def test_duplicate_package_version_rejected(candidate_copy):
    path=candidate_copy/'ncmemsim/_version.py'
    path.write_text(path.read_text(encoding='utf-8')+'__version__="1.10.0"\n',encoding='utf-8')
    with pytest.raises(ValueError): validate_identity(candidate_copy)


@pytest.mark.parametrize('fault',['version_source','snapshot'])
def test_historical_view_cannot_hide_extra_source_or_snapshot_changes(tmp_path,fault):
    target=tmp_path/'tests/fixtures/releases/v1_9_0'
    shutil.copytree(ROOT/'tests/fixtures/releases/v1_9_0',target)
    (tmp_path/'ncmemsim').mkdir()
    shutil.copyfile(ROOT/'ncmemsim/_version.py',tmp_path/'ncmemsim/_version.py')
    path=tmp_path/'ncmemsim/_version.py' if fault=='version_source' else target/'README.md'
    path.write_text(path.read_text(encoding='utf-8')+'\n# unreviewed change\n',encoding='utf-8')
    with pytest.raises(ValueError,match='version source|snapshot drift'):
        with historical._published_view(tmp_path):
            raise AssertionError('unreviewed source accepted')
