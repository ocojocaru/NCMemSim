# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import shutil
import pytest
from scripts.validate_v1_5_release_identity import validate,validate_identity
ROOT=Path(__file__).resolve().parents[1]

def test_final_identity_and_retained_contracts():
    r=validate(ROOT)
    assert r['release_version']=='1.5.0' and r['citation_date']=='2026-10-06'
    assert r['version_specific_doi']=='10.5281/zenodo.23189313' and r['api']['retained_stable_paths']==297

@pytest.fixture
def final_copy(tmp_path):
    for folder in ('docs','ncmemsim'):shutil.copytree(ROOT/folder,tmp_path/folder)
    for name in ('README.md','CHANGELOG.md','CITATION.cff'):shutil.copyfile(ROOT/name,tmp_path/name)
    return tmp_path

@pytest.mark.parametrize('name,old,new',[
    ('ncmemsim/_version.py','"1.5.0"','"1.5.0.dev0"'),
    ('CITATION.cff','version: 1.5.0','version: 1.4.0'),
    ('CITATION.cff','2026-10-06','2026-10-02'),
    ('CITATION.cff','23078330','00000000'),
    ('README.md','**Published v1.5.0 status:**','stale'),
    ('docs/index.md','Published stable release: `1.5.0`','stale'),
    ('docs/broadband_optics.md','Published identity: `1.5.0`','stale'),
    ('docs/roadmap.md','published stable release `1.5.0`','stale'),
    ('docs/v1_5_release_checklist.md','Published identity: `1.5.0`','stale'),
    ('CHANGELOG.md','## 1.5.0 — 2026-10-06','stale'),
])
def test_partial_identity_rejected(final_copy,name,old,new):
    p=final_copy/name;s=p.read_text(encoding='utf-8');assert old in s
    p.write_text(s.replace(old,new),encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(final_copy)

@pytest.mark.parametrize('doi',['10.5281/zenodo.23102549','10.5281/zenodo.23078330','10.0000/unassigned'])
def test_no_unconfirmed_specific_doi(final_copy,doi):
    p=final_copy/'CITATION.cff';p.write_text(p.read_text(encoding='utf-8').replace('10.5281/zenodo.23189313',doi),encoding='utf-8')
    with pytest.raises(ValueError,match='author-confirmed'):validate_identity(final_copy)


@pytest.mark.parametrize('fault',['missing','duplicate'])
def test_published_identity_requires_one_specific_doi(final_copy,fault):
    p=final_copy/'CITATION.cff';s=p.read_text(encoding='utf-8');line='doi: 10.5281/zenodo.23189313\n'
    s=s.replace(line,'') if fault=='missing' else s+'\n'+line
    p.write_text(s,encoding='utf-8')
    with pytest.raises(ValueError,match='author-confirmed'):validate_identity(final_copy)
