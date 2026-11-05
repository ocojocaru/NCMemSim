# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""S7 source fence, additive review and immutable negative archive controls."""
from pathlib import Path
import copy
import pytest
from scripts import validate_v1_10_api_review as gate
from scripts.validate_dtco_distribution import SOURCE_REQUIRED, BARRIER_ARCHIVE_PROBE
ROOT=Path(__file__).resolve().parents[1]


def test_real_preparation_gate():
    result=gate.validate(ROOT)
    assert result['target_release']=='1.10.0' and result['package_version']=='1.10.0'
    assert result['retained_published_modules']==146
    assert result['reviewed_modules']==4 and result['additive_exports']==16
    assert result['final_candidate']
    assert gate.build_review(ROOT)['preparation_archive']['capture_package_version']=='1.9.0'


@pytest.mark.parametrize('field', ['publication','scientific_limits','version_rationale','preparation_archive'])
def test_review_drift_rejected(monkeypatch,field):
    original=gate._json
    def altered(path):
        raw=original(path)
        if Path(path)==ROOT/gate.REVIEW:
            raw[field]=None
        return raw
    monkeypatch.setattr(gate,'_json',altered)
    with pytest.raises(ValueError,match='review/source drift'):
        gate.validate(ROOT)


def test_frozen_archive_cannot_be_relabelled(monkeypatch):
    original=gate._json
    def altered(path):
        raw=original(path)
        if Path(path)==ROOT/gate.ARCHIVE:
            raw['title']='Rewritten evidence'
        return raw
    monkeypatch.setattr(gate,'_json',altered)
    with pytest.raises(ValueError,match='archive drift'):
        gate._archive(ROOT)


def test_runtime_export_drift_rejected(monkeypatch):
    import ncmemsim.barrier_reporting as module
    monkeypatch.setattr(module,'__all__',module.__all__+['UnreviewedExport'])
    with pytest.raises(ValueError,match='export mismatch'):
        gate.build_review(ROOT)


def test_published_source_fence_cannot_be_reapproved(tmp_path):
    # The existing independent fence must run even when generating a new S review.
    import shutil
    shutil.copytree(ROOT/'ncmemsim',tmp_path/'ncmemsim')
    shutil.copytree(ROOT/'docs',tmp_path/'docs')
    shutil.copytree(ROOT/'tests/fixtures',tmp_path/'tests/fixtures')
    shutil.copyfile(ROOT/'README.md',tmp_path/'README.md')
    path=tmp_path/'ncmemsim/tunneling.py'
    path.write_text(path.read_text(encoding='utf-8')+'\n# unreviewed published drift\n',encoding='utf-8')
    with pytest.raises(ValueError,match='published v1.9 source changed'):
        gate.build_review(tmp_path)


def test_frozen_restore_does_not_call_provider_or_step(monkeypatch):
    from ncmemsim.barrier_transport import BarrierTransportEngine
    def forbidden(*args,**kwargs): raise AssertionError('device replay')
    monkeypatch.setattr(BarrierTransportEngine,'step',forbidden)
    report=gate._archive(ROOT)
    assert report.to_dict()['summary']==gate.EXPECTED_SUMMARY


def test_distribution_and_ci_membership():
    compile(BARRIER_ARCHIVE_PROBE,'installed-s7','exec')
    assert {gate.ARCHIVE,gate.REVIEW,'docs/v1_10_release_checklist.md',
            'scripts/validate_v1_10_api_review.py','tests/test_phase_s7_preparation.py'} <= SOURCE_REQUIRED
    assert 'python scripts/validate_v1_10_api_review.py' in (ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8')


def test_regenerated_inventory_cannot_approve_unknown_module(monkeypatch):
    original=gate.build_inventory
    def altered(root):
        raw=original(root)
        raw['modules'].append(dict(raw['modules'][0],module='ncmemsim.unreviewed'))
        return raw
    monkeypatch.setattr(gate,'build_inventory',altered)
    with pytest.raises(ValueError,match='unreviewed additive module set'):
        gate.build_review(ROOT)
