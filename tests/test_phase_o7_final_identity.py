# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Published identity, confirmed DOI and retained development evidence."""
from pathlib import Path
import shutil
import pytest
from scripts.validate_v1_6_release_identity import validate,validate_identity
ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def final_copy(tmp_path):
    for folder in ('docs','ncmemsim'):shutil.copytree(ROOT/folder,tmp_path/folder)
    for name in ('README.md','CHANGELOG.md','CITATION.cff'):shutil.copyfile(ROOT/name,tmp_path/name)
    return tmp_path


def test_final_identity_and_retained_contracts():
    result=validate(ROOT)
    assert result['release_version']=='1.6.0' and result['citation_date']=='2026-10-08'
    assert result['version_specific_doi']=='10.5281/zenodo.23235484'
    assert result['api']['retained_stable_paths']==297 and result['api']['structural_exports']==22


@pytest.mark.parametrize('name,old,new',[
    ('ncmemsim/_version.py','"1.6.0"','"1.6.0.dev0"'),
    ('CITATION.cff','version: 1.6.0','version: 1.5.0'),
    ('CITATION.cff','2026-10-08','2026-10-06'),
    ('CITATION.cff','23078330','00000000'),
    ('CITATION.cff','Apache-2.0','MIT'),
    ('README.md','**Published v1.6.0 status:**','**Development version:**'),
    ('README.md','**Current stable release:** `1.6.0`','stale'),
    ('docs/index.md','Published stable release: `1.6.0`','stale'),
    ('docs/archival_citation.md','published v1.6.0 dated 2026-10-08','stale'),
    ('docs/roadmap.md','Published identity: `1.6.0`','stale'),
    ('docs/strain_confinement.md','Published identity: `1.6.0`','stale'),
    ('docs/v1_6_release_checklist.md','Citation date: `2026-10-08`','stale'),
    ('CHANGELOG.md','## 1.6.0 — 2026-10-08','published'),
])
def test_partial_identity_rejected(final_copy,name,old,new):
    p=final_copy/name;s=p.read_text(encoding='utf-8');assert old in s
    p.write_text(s.replace(old,new),encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(final_copy)


@pytest.mark.parametrize('doi',['10.5281/zenodo.23189313','10.5281/zenodo.23078330','10.0000/unassigned'])
def test_no_unassigned_or_previous_release_doi(final_copy,doi):
    p=final_copy/'CITATION.cff';p.write_text(p.read_text(encoding='utf-8').replace('10.5281/zenodo.23235484',doi),encoding='utf-8')
    with pytest.raises(ValueError,match='author-confirmed'):validate_identity(final_copy)


def test_duplicate_package_version_rejected(final_copy):
    p=final_copy/'ncmemsim/_version.py';p.write_text(p.read_text(encoding='utf-8')+'\n__version__="1.6.0"\n',encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(final_copy)


def test_duplicate_citation_field_rejected(final_copy):
    p=final_copy/'CITATION.cff';p.write_text(p.read_text(encoding='utf-8')+'\nversion: 1.6.0\n',encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(final_copy)


@pytest.mark.parametrize('fault',['missing','duplicate'])
def test_one_confirmed_version_doi_required(final_copy,fault):
    p=final_copy/'CITATION.cff';s=p.read_text(encoding='utf-8');line='doi: 10.5281/zenodo.23235484\n'
    s=s.replace(line,'') if fault=='missing' else s+'\n'+line
    p.write_text(s,encoding='utf-8')
    with pytest.raises(ValueError,match='author-confirmed'):validate_identity(final_copy)
