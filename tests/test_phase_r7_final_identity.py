# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Published v1.9 release identity and retained published v1.8 attribution."""
from pathlib import Path
import shutil
import pytest
from scripts.validate_v1_9_release_identity import validate,validate_identity
ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def candidate_copy(tmp_path):
    for folder in ('docs','ncmemsim'):
        shutil.copytree(ROOT/folder,tmp_path/folder)
    for name in ('README.md','CHANGELOG.md','CITATION.cff'):
        shutil.copyfile(ROOT/name,tmp_path/name)
    return tmp_path


def test_candidate_identity_and_retained_api():
    result=validate(ROOT)
    assert result['package_version']=='1.9.0' and result['citation_date']=='2026-10-26'
    assert result['latest_published_stable']=='1.9.0' and result['version_specific_doi']=='10.5281/zenodo.23664613'
    assert result['release_published'] and result['api']['retained_published_modules']==140
    assert result['api']['additive_exports']==20 and result['api']['retained_stable_paths']==297


@pytest.mark.parametrize('name,old,new',[
    ('ncmemsim/_version.py','1.9.0','1.8.0'),
    ('CITATION.cff','version: 1.9.0','version: 1.8.0'),
    ('CITATION.cff','2026-10-26','2026-10-23'),
    ('CITATION.cff','23078330','23510004'),
    ('CITATION.cff','Apache-2.0','MIT'),
    ('README.md','**Published v1.9.0 status:**','stale'),
    ('docs/index.md','Latest published stable: `1.9.0`','stale'),
    ('docs/roadmap.md','R7 is complete','R7 pending'),
    ('docs/performance_interoperability.md','Published identity: `1.9.0`','stale'),
    ('docs/v1_9_release_checklist.md','Published identity: `1.9.0`','stale'),
    ('CHANGELOG.md','## 1.9.0 - 2026-10-26','stale')])
def test_partial_identity_rejected(candidate_copy,name,old,new):
    p=candidate_copy/name;text=p.read_text(encoding='utf-8');assert old in text
    p.write_text(text.replace(old,new),encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(candidate_copy)


@pytest.mark.parametrize('doi',['10.5281/zenodo.23510004','10.5281/zenodo.23078330','10.0000/unassigned'])
def test_no_reused_or_invented_version_doi(candidate_copy,doi):
    p=candidate_copy/'CITATION.cff';p.write_text(p.read_text(encoding='utf-8').replace('doi: 10.5281/zenodo.23664613','doi: '+doi),encoding='utf-8')
    with pytest.raises(ValueError,match='DOI'):validate_identity(candidate_copy)


@pytest.mark.parametrize('line',['version: 1.9.0','date-released: 2026-10-26','license: Apache-2.0','identifiers:'])
def test_duplicate_citation_fields(candidate_copy,line):
    p=candidate_copy/'CITATION.cff';p.write_text(p.read_text(encoding='utf-8')+line+'\n',encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(candidate_copy)


def test_duplicate_package_version(candidate_copy):
    p=candidate_copy/'ncmemsim/_version.py';p.write_text(p.read_text(encoding='utf-8')+'__version__="1.9.0"\n',encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(candidate_copy)


def test_retained_snapshot_doi_and_version_not_relabelled():
    root=ROOT/'tests/fixtures/releases/v1_8_0'
    assert '__version__ = "1.8.0"' in (root/'ncmemsim/_version.py').read_text(encoding='utf-8')
    assert 'doi: 10.5281/zenodo.23510004' in (root/'CITATION.cff').read_text(encoding='utf-8')
    assert 'date-released: 2026-10-20' in (root/'CITATION.cff').read_text(encoding='utf-8')
