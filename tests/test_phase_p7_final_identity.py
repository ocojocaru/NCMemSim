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
    assert result['package_version']=='1.7.0' and result['candidate_date']=='2026-10-12'
    assert result['latest_published_stable']=='1.6.0' and result['version_specific_doi'] is None
    assert result['api']['retained_stable_paths']==297 and result['api']['additive_exports']==29
    assert result['api']['experimental_qualification'] is False


@pytest.mark.parametrize('name,old,new',[
    ('ncmemsim/_version.py','"1.7.0"','"1.6.0"'),
    ('CITATION.cff','version: 1.7.0','version: 1.6.0'),
    ('CITATION.cff','2026-10-12','2026-10-08'),
    ('CITATION.cff','23078330','23235484'),
    ('CITATION.cff','Apache-2.0','MIT'),
    ('README.md','**Final candidate:** `1.7.0`','published v1.7'),
    ('docs/index.md','not yet published','published'),
    ('docs/roadmap.md','experimental qualification remains deferred','experimental qualification complete'),
    ('docs/v1_7_release_checklist.md','release approval remains pending','release approved'),
    ('CHANGELOG.md','(prepared candidate)','(published)')])
def test_partial_or_false_candidate_declarations_rejected(candidate_copy,name,old,new):
    p=candidate_copy/name;s=p.read_text(encoding='utf-8');assert old in s
    p.write_text(s.replace(old,new),encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(candidate_copy)


@pytest.mark.parametrize('doi',['10.5281/zenodo.23235484','10.5281/zenodo.23078330','10.0000/unassigned'])
def test_candidate_cannot_reuse_or_invent_version_doi(candidate_copy,doi):
    p=candidate_copy/'CITATION.cff';p.write_text(p.read_text(encoding='utf-8')+'\ndoi: '+doi+'\n',encoding='utf-8')
    with pytest.raises(ValueError,match='unconfirmed'):validate_identity(candidate_copy)


@pytest.mark.parametrize('name,line',[
    ('CITATION.cff','version: 1.7.0'),
    ('CITATION.cff','date-released: 2026-10-12'),
    ('ncmemsim/_version.py','__version__="1.7.0"')])
def test_duplicate_identity_rejected(candidate_copy,name,line):
    p=candidate_copy/name;p.write_text(p.read_text(encoding='utf-8')+'\n'+line+'\n',encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(candidate_copy)
