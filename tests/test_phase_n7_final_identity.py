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
    assert r['version_specific_doi'] is None and r['api']['retained_stable_paths']==297

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
    ('README.md','**Release candidate:** `1.5.0`','stale'),
    ('docs/index.md','Final release candidate: `1.5.0`','stale'),
    ('docs/broadband_optics.md','Final candidate identity: `1.5.0`','stale'),
    ('docs/roadmap.md','final candidate identity `1.5.0`','stale'),
    ('docs/v1_5_release_checklist.md','Final candidate identity: `1.5.0`','stale'),
    ('CHANGELOG.md','## 1.5.0 — 2026-10-06 (release candidate; publication pending)','stale'),
])
def test_partial_identity_rejected(final_copy,name,old,new):
    p=final_copy/name;s=p.read_text(encoding='utf-8');assert old in s
    p.write_text(s.replace(old,new),encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(final_copy)

@pytest.mark.parametrize('doi',['10.5281/zenodo.23102549','10.5281/zenodo.23078330','10.0000/unassigned'])
def test_no_unconfirmed_specific_doi(final_copy,doi):
    with (final_copy/'CITATION.cff').open('a',encoding='utf-8') as f:f.write('\ndoi: '+doi+'\n')
    with pytest.raises(ValueError,match='actual deposit'):validate_identity(final_copy)
