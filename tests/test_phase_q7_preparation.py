# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Q7 preparation freezes source/API/archive without claiming release approval."""
from pathlib import Path
import json
import shutil
import pytest
from scripts import validate_v1_8_api_review as gate
from scripts.validate_dtco_distribution import SOURCE_REQUIRED, MULTILEVEL_PROBE
ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def review_copy(tmp_path,monkeypatch):
    for folder in ('docs','ncmemsim','tests/fixtures'):
        shutil.copytree(ROOT/folder,tmp_path/folder)
    for name in ('README.md','CHANGELOG.md','CITATION.cff'):
        shutil.copyfile(ROOT/name,tmp_path/name)
    # The retained gate is exercised against the real checkout below. Negative
    # copies isolate the new gate's checks rather than rerunning that entire gate.
    monkeypatch.setattr(gate,'retained_review',lambda root:{'retained_stable_paths':297,'stable_ensemble_exports':59})
    return tmp_path


def test_preparation_review_and_retained_surface():
    result=gate.validate(ROOT)
    assert result['target_release']=='1.8.0' and result['package_version']=='1.8.0'
    assert result['reviewed_modules']==8 and result['additive_exports']==34
    assert result['archive_case_count']==9 and result['experimental_qualification'] is False
    assert result['retained_stable_paths']==297 and result['stable_ensemble_exports']==59


@pytest.mark.parametrize('fault',['review','source','archive','retained_review','version','checklist','roadmap','scope'])
def test_unreviewed_changes_rejected(review_copy,fault):
    root=review_copy
    if fault=='source':
        p=root/'ncmemsim/multilevel_reporting.py';p.write_text(p.read_text(encoding='utf-8')+'# unreviewed drift\n',encoding='utf-8')
    elif fault=='version':(root/'ncmemsim/_version.py').write_text('__version__="1.7.0"\n',encoding='utf-8')
    elif fault=='checklist':(root/'docs/v1_8_release_checklist.md').write_text('published',encoding='utf-8')
    elif fault=='roadmap':
        p=root/'docs/roadmap.md';p.write_text(p.read_text(encoding='utf-8').replace('Q7 is complete','Q7 incomplete'),encoding='utf-8')
    else:
        filename={'review':'docs/v1_8_api_review.json','archive':gate.ARCHIVE,
                  'retained_review':'docs/v1_7_api_review.json','scope':'docs/v1_8_api_review.json'}[fault]
        p=root/filename;raw=json.loads(p.read_text(encoding='utf-8'))
        if fault=='scope':raw['scientific_limits']=[]
        else:raw['forged']=True
        p.write_text(json.dumps(raw),encoding='utf-8')
    with pytest.raises(ValueError):gate.validate(root)


def test_duplicate_review_keys_rejected(review_copy):
    p=review_copy/'docs/v1_8_api_review.json'
    p.write_text(p.read_text(encoding='utf-8').replace('{','{"status":"forged",',1),encoding='utf-8')
    with pytest.raises(ValueError):gate.validate(review_copy)


def test_export_drift_rejected(monkeypatch):
    from ncmemsim import multilevel_reporting
    monkeypatch.setattr(multilevel_reporting,'__all__',multilevel_reporting.__all__+['MissingExport'])
    with pytest.raises(ValueError):gate.validate(ROOT)


def test_archive_source_versions_and_negative_outcomes_are_not_relabelled():
    from ncmemsim.multilevel_reporting import MultilevelReport
    raw=json.loads((ROOT/gate.ARCHIVE).read_text(encoding='utf-8'))
    report=MultilevelReport.from_dict(raw)
    assert report.to_dict()==raw and '1.7.0' in report.title
    assert set(c.kind for c in report.cases)=={'electrical','separation','updates','paired_updates','optical','matched_optical','retention','ensemble'}
    assert any(x['status']=='failed' for x in report.summary['cases'])
    assert any(x['status']=='not_assessable' for x in report.summary['cases'])
    def runtime_versions(node):
        if type(node) is dict:
            if type(node.get('runtime')) is dict and 'ncmemsim' in node['runtime']:
                yield node['runtime']['ncmemsim']
            for value in node.values():yield from runtime_versions(value)
        elif type(node) is list:
            for value in node:yield from runtime_versions(value)
    assert set(runtime_versions(raw))=={'1.7.0'}


def test_installed_probe_and_ci_source_membership():
    compile(MULTILEVEL_PROBE,'installed-multilevel-probe','exec')
    assert {gate.ARCHIVE,'scripts/validate_v1_8_api_review.py','docs/v1_8_api_review.json',
            'docs/v1_8_release_checklist.md','docs/multilevel_reporting.md'}<=SOURCE_REQUIRED
    assert 'is_relative_to(Path(sys.prefix)' in MULTILEVEL_PROBE
    assert 'coherently rehashed multilevel projection must fail' in MULTILEVEL_PROBE
    assert 'RNGSpec.create_generator=forbidden' in MULTILEVEL_PROBE
    assert 'python scripts/validate_v1_8_api_review.py' in (ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8')
