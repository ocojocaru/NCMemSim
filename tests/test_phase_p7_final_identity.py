# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""v1.7 prepared identity and DOI/scope boundaries, not publication approval."""
from pathlib import Path
import shutil
import pytest
from scripts.validate_v1_7_release_identity import validate,validate_identity
ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def candidate_copy(tmp_path):
    for folder in ('docs','ncmemsim','tests/fixtures','data'):
        shutil.copytree(ROOT/folder,tmp_path/folder)
    for name in ('README.md','CHANGELOG.md','CITATION.cff'):
        shutil.copyfile(ROOT/name,tmp_path/name)
    return tmp_path


def test_candidate_and_retained_v16_identity():
    result=validate(ROOT)
    assert result['package_version']=='1.7.0' and result['citation_date']=='2026-10-12'
    assert result['latest_published_stable']=='1.7.0' and result['version_specific_doi']=='10.5281/zenodo.23316663'
    assert result['api']['retained_stable_paths']==297 and result['api']['additive_exports']==29
    assert result['api']['experimental_qualification'] is False


@pytest.mark.parametrize('name,old,new',[
    ('ncmemsim/_version.py','"1.7.0"','"1.6.0"'),
    ('CITATION.cff','version: 1.7.0','version: 1.6.0'),
    ('CITATION.cff','2026-10-12','2026-10-08'),
    ('CITATION.cff','23078330','23235484'),
    ('CITATION.cff','Apache-2.0','MIT'),
    ('README.md','**Published v1.7.0 status:**','stale'),
    ('docs/index.md','Published stable release: `1.7.0`','stale'),
    ('docs/roadmap.md','experimental qualification remains deferred','experimental qualification complete'),
    ('docs/v1_7_release_checklist.md','P7 is complete','P7 incomplete'),
    ('CHANGELOG.md','## 1.7.0 - 2026-10-12','stale')])
def test_partial_or_false_candidate_declarations_rejected(candidate_copy,name,old,new):
    p=candidate_copy/name;s=p.read_text(encoding='utf-8');assert old in s
    p.write_text(s.replace(old,new),encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(candidate_copy)


@pytest.mark.parametrize('doi',['10.5281/zenodo.23235484','10.5281/zenodo.23078330','10.0000/unassigned'])
def test_published_version_cannot_reuse_or_invent_doi(candidate_copy,doi):
    p=candidate_copy/'CITATION.cff';p.write_text(p.read_text(encoding='utf-8').replace('10.5281/zenodo.23316663',doi),encoding='utf-8')
    with pytest.raises(ValueError,match='author-confirmed'):validate_identity(candidate_copy)


@pytest.mark.parametrize('name,line',[
    ('CITATION.cff','version: 1.7.0'),
    ('CITATION.cff','date-released: 2026-10-12'),
    ('ncmemsim/_version.py','__version__="1.7.0"')])
def test_duplicate_identity_rejected(candidate_copy,name,line):
    p=candidate_copy/name;p.write_text(p.read_text(encoding='utf-8')+'\n'+line+'\n',encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(candidate_copy)


@pytest.mark.parametrize('fault',['missing','duplicate'])
def test_one_confirmed_doi_required(candidate_copy,fault):
    p=candidate_copy/'CITATION.cff';s=p.read_text(encoding='utf-8');line='doi: 10.5281/zenodo.23316663\n'
    s=s.replace(line,'') if fault=='missing' else s+'\n'+line
    p.write_text(s,encoding='utf-8')
    with pytest.raises(ValueError,match='author-confirmed'):validate_identity(candidate_copy)
