# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Published identity, historical declarations and confirmed DOI guards."""
from pathlib import Path
import shutil
import pytest
from scripts.validate_v1_8_release_identity import validate,validate_identity
ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def candidate_copy(published_v1_8_copy):
    return published_v1_8_copy


def test_final_candidate_and_retained_identity(published_v1_8_copy):
    result=validate(published_v1_8_copy)
    assert result['package_version']=='1.8.0' and result['citation_date']=='2026-10-20'
    assert result['latest_published_stable']=='1.8.0'
    assert result['version_specific_doi']=='10.5281/zenodo.23510004'
    assert result['api']['reviewed_modules']==8 and result['api']['additive_exports']==34
    assert result['api']['retained_stable_paths']==297 and result['api']['experimental_qualification'] is False


@pytest.mark.parametrize('name,old,new',[
    ('ncmemsim/_version.py','1.8.0','1.7.0'),
    ('CITATION.cff','version: 1.8.0','version: 1.7.0'),
    ('CITATION.cff','2026-10-20','2026-10-12'),
    ('CITATION.cff','23078330','23316663'),
    ('CITATION.cff','Apache-2.0','MIT'),
    ('README.md','**Published v1.8.0 status:**','stale'),
    ('docs/index.md','Published stable release: `1.8.0`','stale'),
    ('docs/roadmap.md','Q7 is complete','stale'),
    ('docs/multilevel_operation.md','published identity is `1.8.0`','stale'),
    ('docs/v1_8_release_checklist.md','Latest published stable: `1.8.0`','stale'),
    ('CHANGELOG.md','## 1.8.0 - 2026-10-20','stale')])
def test_partial_identity_rejected(candidate_copy,name,old,new):
    p=candidate_copy/name
    s=p.read_text(encoding='utf-8');assert old in s
    p.write_text(s.replace(old,new),encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(candidate_copy)


@pytest.mark.parametrize('doi',['10.5281/zenodo.23316663','10.5281/zenodo.23078330','10.0000/unassigned'])
def test_no_reused_concept_or_invented_version_doi(candidate_copy,doi):
    p=candidate_copy/'CITATION.cff'
    p.write_text(p.read_text(encoding='utf-8').replace('10.5281/zenodo.23510004',doi),encoding='utf-8')
    with pytest.raises(ValueError,match='confirmed'):validate_identity(candidate_copy)


@pytest.mark.parametrize('line',['version: 1.8.0','date-released: 2026-10-20','license: Apache-2.0','identifiers:'])
def test_duplicate_citation_fields_rejected(candidate_copy,line):
    p=candidate_copy/'CITATION.cff'
    p.write_text(p.read_text(encoding='utf-8')+line+'\n',encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(candidate_copy)


def test_duplicate_package_version_rejected(candidate_copy):
    p=candidate_copy/'ncmemsim/_version.py'
    p.write_text(p.read_text(encoding='utf-8')+'\n__version__="1.8.0"\n',encoding='utf-8')
    with pytest.raises(ValueError):validate_identity(candidate_copy)


@pytest.mark.parametrize('fault',['missing','duplicate'])
def test_one_confirmed_version_doi_required(candidate_copy,fault):
    p=candidate_copy/'CITATION.cff'
    s=p.read_text(encoding='utf-8');line='doi: 10.5281/zenodo.23510004\n'
    s=s.replace(line,'') if fault=='missing' else s+line
    p.write_text(s,encoding='utf-8')
    with pytest.raises(ValueError,match='confirmed'):validate_identity(candidate_copy)
