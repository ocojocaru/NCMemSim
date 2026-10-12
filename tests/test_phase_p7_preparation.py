# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""P7 candidate contracts; no publication or measured-calibration approval."""
from pathlib import Path
import json,shutil
import pytest
from scripts import validate_v1_7_api_review as gate
from scripts.validate_dtco_distribution import SOURCE_REQUIRED,INDEPENDENT_PROBE
ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def review_copy(tmp_path):
    for folder in ('docs','ncmemsim','tests/fixtures','data'):
        shutil.copytree(ROOT/folder,tmp_path/folder)
    for name in ('README.md','CHANGELOG.md','CITATION.cff'):
        shutil.copyfile(ROOT/name,tmp_path/name)
    return tmp_path


def test_candidate_review_retains_history_and_deferred_experiments():
    result=gate.validate(ROOT)
    assert result['package_version']=='1.7.0' and result['target_release']=='1.7.0'
    assert result['retained_stable_paths']==297 and result['stable_ensemble_exports']==59
    assert result['reviewed_modules']==7 and result['additive_exports']==29
    assert result['experimental_qualification'] is False


@pytest.mark.parametrize('fault',['review','source','archive','retained_review','data_review','version','checklist','roadmap'])
def test_unreviewed_scope_and_sources_rejected(review_copy,fault):
    root=review_copy
    if fault=='source':
        p=root/'ncmemsim/om2_reporting.py';p.write_text(p.read_text(encoding='utf-8')+'# drift\n',encoding='utf-8')
    elif fault=='version':(root/'ncmemsim/_version.py').write_text('__version__="1.6.0"\n',encoding='utf-8')
    elif fault=='checklist':(root/'docs/v1_7_release_checklist.md').write_text('P7 complete',encoding='utf-8')
    elif fault=='roadmap':
        p=root/'docs/roadmap.md';p.write_text(p.read_text(encoding='utf-8').replace('experimental qualification remains deferred','experimentally calibrated'),encoding='utf-8')
    else:
        names={'review':'docs/v1_7_api_review.json','archive':gate.ARCHIVE,
            'retained_review':'docs/v1_6_api_review.json','data_review':'docs/independent_data_review.json'}
        p=root/names[fault];d=json.loads(p.read_text(encoding='utf-8'));d['forged']=True;p.write_text(json.dumps(d),encoding='utf-8')
    with pytest.raises(ValueError):gate.validate(root)


def test_duplicate_review_keys_rejected(review_copy):
    p=review_copy/'docs/v1_7_api_review.json';p.write_text(p.read_text(encoding='utf-8').replace('{','{"status":"forged",',1),encoding='utf-8')
    with pytest.raises(ValueError):gate.validate(review_copy)


def test_export_drift_rejected(monkeypatch):
    from ncmemsim import om2_reporting
    monkeypatch.setattr(om2_reporting,'__all__',om2_reporting.__all__+['NonexistentExport'])
    with pytest.raises(ValueError):gate.validate(ROOT)


def test_installed_probe_and_ci_source_gate():
    compile(INDEPENDENT_PROBE,'installed-independent-probe','exec')
    assert {'scripts/validate_v1_7_api_review.py','docs/v1_7_api_review.json',gate.ARCHIVE}<=SOURCE_REQUIRED
    assert 'is_relative_to(Path(sys.prefix)' in INDEPENDENT_PROBE
    assert 'coherently rehashed projection must fail' in INDEPENDENT_PROBE
    assert 'python scripts/validate_v1_7_api_review.py' in (ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8')
