# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""R7 preparation protects published surfaces and original report provenance."""
from pathlib import Path
import json
import shutil
import pytest
from scripts import validate_v1_9_api_review as gate
from scripts.validate_dtco_distribution import SOURCE_REQUIRED, PERFORMANCE_ARCHIVE_PROBE
ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def review_copy(tmp_path,monkeypatch):
    for directory in ('docs','ncmemsim'):
        shutil.copytree(ROOT/directory,tmp_path/directory)
    shutil.copyfile(ROOT/'README.md',tmp_path/'README.md')
    target=tmp_path/gate.ARCHIVE;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/gate.ARCHIVE,target)
    monkeypatch.setattr(gate,'validate_published',lambda root:dict(
        retained_stable_paths=297,stable_ensemble_exports=59,additive_exports=34))
    return tmp_path


def test_preparation_validates_real_retained_contracts():
    result=gate.validate(ROOT)
    assert result['target_release']=='1.9.0' and result['package_version']=='1.8.0'
    assert result['retained_published_modules']==140 and result['reviewed_modules']==6
    assert result['additive_exports']==20 and result['campaign_count']==5 and result['comparison_count']==9
    assert result['final_candidate']=='pending' and not result['experimental_qualification']


@pytest.mark.parametrize('fault',['review','source','archive','surface','retained_review',
    'version','checklist','roadmap','scope'])
def test_unreviewed_preparation_drift_rejected(review_copy,fault):
    root=review_copy
    if fault=='source':
        path=root/'ncmemsim/performance_reporting.py'
        path.write_text(path.read_text(encoding='utf-8')+'# unreviewed source drift\n',encoding='utf-8')
    elif fault=='version':(root/'ncmemsim/_version.py').write_text('__version__="1.9.0"\n',encoding='utf-8')
    elif fault=='checklist':(root/'docs/v1_9_release_checklist.md').write_text('release approved',encoding='utf-8')
    elif fault=='roadmap':
        path=root/'docs/roadmap.md';path.write_text(path.read_text(encoding='utf-8').replace('R7 preparation','R7 closure'),encoding='utf-8')
    else:
        name={'review':'docs/v1_9_api_review.json','archive':gate.ARCHIVE,'surface':gate.SURFACE,
              'retained_review':'docs/v1_8_api_review.json','scope':'docs/v1_9_api_review.json'}[fault]
        path=root/name;raw=json.loads(path.read_text(encoding='utf-8'))
        if fault=='scope':raw['scientific_limits']=[]
        else:raw['unreviewed']=True
        path.write_text(json.dumps(raw),encoding='utf-8')
    with pytest.raises(ValueError):gate.validate(root)


def test_published_surface_cannot_be_silently_reapproved(review_copy):
    path=review_copy/'ncmemsim/benchmark.py'
    path.write_text(path.read_text(encoding='utf-8')+'\ndef unreviewed_public_addition(): pass\n',encoding='utf-8')
    with pytest.raises(ValueError,match='published v1.8 public surface changed'):
        gate.build_review(review_copy)


def test_baseline_hash_blocks_regeneration(review_copy):
    path=review_copy/gate.SURFACE;raw=json.loads(path.read_text(encoding='utf-8'))
    raw['modules'][0]['surface_sha256']='0'*64
    path.write_text(json.dumps(raw),encoding='utf-8')
    with pytest.raises(ValueError,match='baseline drift'):gate.build_review(review_copy)


def test_archive_relabel_cannot_be_reapproved(review_copy):
    path=review_copy/gate.ARCHIVE;raw=json.loads(path.read_text(encoding='utf-8'))
    raw['campaigns'][0]['archive']['campaign']['environment']['source_package_version']='1.9.0'
    path.write_text(json.dumps(raw),encoding='utf-8')
    with pytest.raises(ValueError,match='preparation report drift'):gate.build_review(review_copy)


def test_duplicate_review_keys_rejected(review_copy):
    path=review_copy/'docs/v1_9_api_review.json'
    path.write_text(path.read_text(encoding='utf-8').replace('{','{"status":"forged",',1),encoding='utf-8')
    with pytest.raises(ValueError):gate.validate(review_copy)


def test_additive_runtime_export_drift_rejected(monkeypatch):
    from ncmemsim import performance_reporting
    monkeypatch.setattr(performance_reporting,'__all__',performance_reporting.__all__+['MissingExport'])
    with pytest.raises(ValueError):gate.build_review(ROOT)


def test_frozen_archive_static_restore_retains_sources_and_negatives(monkeypatch):
    import ncmemsim.performance_execution as execution
    def forbidden(*a,**kw):raise AssertionError('frozen archive must not execute or probe')
    monkeypatch.setattr(execution,'_worker',forbidden)
    monkeypatch.setattr(execution,'capture_performance_environment',forbidden)
    report=gate._archive(ROOT);raw=report.to_dict()
    env=raw['campaigns'][0]['archive']['campaign']['environment']
    assert env['source_commit']==gate.CAPTURE_COMMIT and env['source_dirty'] is False
    assert env['source_package_version']=='1.8.0'
    assert all(row['archive']['evidence_kind']=='synthetic_control' for row in raw['campaigns'][1:])
    assert {row['result']['status'] for row in raw['comparisons']}=={'matched','mismatched','unavailable'}
    assert any(row['archive']['campaign']['summary']['failed_measurement_count'] for row in raw['campaigns'])
    assert any(row['archive']['campaign']['summary']['unavailable_measurement_count'] for row in raw['campaigns'])
    assert raw['summary']['pooled_statistics'] is None and not raw['summary']['external_agreement']


def test_installed_archive_probe_and_ci_membership():
    compile(PERFORMANCE_ARCHIVE_PROBE,'installed-r7-probe','exec')
    assert {gate.ARCHIVE,gate.SURFACE,'docs/v1_9_api_review.json',
        'docs/v1_9_release_checklist.md','scripts/validate_v1_9_api_review.py',
        'tests/test_phase_r7_preparation.py'} <= SOURCE_REQUIRED
    assert 'python scripts/validate_v1_9_api_review.py' in (ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert 'execution.capture_performance_environment=forbidden' in PERFORMANCE_ARCHIVE_PROBE
    assert 'coherently rehashed trial projection accepted' in PERFORMANCE_ARCHIVE_PROBE
