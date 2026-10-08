# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Structural candidate gates, retained identities and archive/distribution boundaries."""
from pathlib import Path
import json
import shutil
import pytest
from scripts import validate_v1_6_api_review as gate
from scripts.validate_dtco_distribution import SOURCE_REQUIRED,STRUCTURAL_PROBE
from ncmemsim.structural_reporting import StructuralReport
ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def candidate_copy(tmp_path):
    for folder in ('docs','ncmemsim','tests/fixtures'):shutil.copytree(ROOT/folder,tmp_path/folder)
    for name in ('README.md','CHANGELOG.md','CITATION.cff'):shutil.copyfile(ROOT/name,tmp_path/name)
    return tmp_path


def test_candidate_identity_and_retained_contracts():
    assert gate.validate(ROOT)=={'status':'candidate_contracts_pass_not_release_approval',
        'package_version':'1.6.0','citation_version':'1.6.0','latest_published_stable':'1.5.0',
        'retained_stable_paths':297,'stable_ensemble_exports':59,'reviewed_modules':5,'structural_exports':22}


@pytest.mark.parametrize('fault',['version','citation','readme','review','source','archive','snapshot','audit','parameters','spectral','checklist','inventory'])
def test_unreviewed_preparation_rejected(candidate_copy,fault):
    root=candidate_copy
    if fault=='version':(root/'ncmemsim/_version.py').write_text('__version__="1.5.0"\n',encoding='utf-8')
    elif fault=='citation':
        p=root/'CITATION.cff';p.write_text(p.read_text(encoding='utf-8').replace('version: 1.6.0','version: 1.5.0'),encoding='utf-8')
    elif fault=='readme':(root/'README.md').write_text('published v1.6',encoding='utf-8')
    elif fault=='source':
        p=root/'ncmemsim/structural_reporting.py';p.write_text(p.read_text(encoding='utf-8')+'# unreviewed\n',encoding='utf-8')
    elif fault=='snapshot':(root/'tests/fixtures/releases/v1_5_0/CITATION.cff').write_text('altered history',encoding='utf-8')
    elif fault=='checklist':(root/'docs/v1_6_release_checklist.md').write_text('release approved',encoding='utf-8')
    else:
        names={'review':'docs/v1_6_api_review.json','archive':'tests/fixtures/archives/v1_6_0_dev/structural_report.json',
            'audit':'docs/strain_confinement_audit.json','parameters':'docs/structural_parameters_review.json',
            'spectral':'docs/v1_5_api_review.json','inventory':'docs/api_inventory.json'}
        p=root/names[fault];raw=json.loads(p.read_text(encoding='utf-8'));raw['unreviewed']=True;p.write_text(json.dumps(raw),encoding='utf-8')
    with pytest.raises(ValueError):gate.validate(root)


def test_duplicate_review_keys_rejected(candidate_copy):
    p=candidate_copy/'docs/v1_6_api_review.json';p.write_text(p.read_text(encoding='utf-8').replace('{','{"status":"forged",',1),encoding='utf-8')
    with pytest.raises(ValueError,match='duplicate'):gate.validate(candidate_copy)


def test_missing_runtime_export_rejected(monkeypatch):
    import ncmemsim.structural_reporting as module
    monkeypatch.setattr(module,'__all__',module.__all__+['MissingStructuralExport'])
    with pytest.raises(ValueError,match='invalid structural exports'):gate.validate(ROOT)


def test_development_archive_does_not_claim_publication():
    raw=json.loads((ROOT/'tests/fixtures/archives/v1_6_0_dev/structural_report.json').read_text(encoding='utf-8'))
    report=StructuralReport.from_dict(raw)
    assert report.to_dict()==raw
    assert report.summary['counts']=={'attempted':2,'completed':0,'failed':2}
    assert report.summary['pulse_delta_vfb_V']['mean'] is None
    assert raw['evidence']['runtime']['ncmemsim']=='1.6.0.dev0'
    assert 'O7 is not complete' in (ROOT/'docs/v1_6_release_checklist.md').read_text(encoding='utf-8')


def test_installed_probe_and_source_requirements():
    compile(STRUCTURAL_PROBE,'structural-installed-probe','exec')
    assert {'scripts/validate_v1_6_api_review.py','docs/v1_6_api_review.json',
        'docs/v1_6_release_checklist.md','tests/fixtures/archives/v1_6_0_dev/structural_report.json',
        'tests/fixtures/releases/v1_5_0/CITATION.cff'}<=SOURCE_REQUIRED
    assert 'coherently rehashed projection must fail' in STRUCTURAL_PROBE
    assert 'is_relative_to(Path(sys.prefix)' in STRUCTURAL_PROBE
    ci=(ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert 'python scripts/validate_v1_6_api_review.py' in ci
    assert ci.count('python-version: ["3.11", "3.12", "3.13"]')==2
