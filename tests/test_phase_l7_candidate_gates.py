# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Candidate contracts, historical boundaries and remote-gate wiring."""
from pathlib import Path
import json
import shutil
import pytest
from scripts import validate_v1_3_api_review as gate
from scripts.validate_dtco_distribution import MODEL_PROBE, SOURCE_REQUIRED

ROOT=Path(__file__).resolve().parents[1]


def test_v1_3_candidate_review_and_retained_stable_exports():
    result=gate.validate(ROOT)
    assert result['package_version'] in ('1.3.0.dev0','1.3.0')
    assert result['reviewed_modules']==6
    assert result['stable_ensemble_exports']==59
    assert result['status']=='candidate_contracts_pass_not_release_approval'


@pytest.mark.parametrize('fault',['version','surface','historical','citation'])
def test_candidate_rejects_identity_review_or_historical_mutation(tmp_path,monkeypatch,fault):
    shutil.copytree(ROOT/'docs',tmp_path/'docs')
    shutil.copytree(ROOT/'ncmemsim',tmp_path/'ncmemsim')
    shutil.copyfile(ROOT/'README.md',tmp_path/'README.md')
    shutil.copyfile(ROOT/'CITATION.cff',tmp_path/'CITATION.cff')
    if fault=='version':monkeypatch.setattr(gate,'__version__','1.2.0')
    elif fault=='surface':
        p=tmp_path/'docs/v1_3_api_review.json';d=json.loads(p.read_text());d['additive_module_qualified_surface']=[];p.write_text(json.dumps(d))
    elif fault=='historical':
        p=tmp_path/next(iter(gate.HISTORICAL_JSON_SHA256));p.write_text('{}')
    else:(tmp_path/'CITATION.cff').write_text('version: 0.0.0\n')
    with pytest.raises(ValueError):gate.validate(tmp_path)


def test_model_distribution_probe_and_fixture_are_packaged():
    compile(MODEL_PROBE,'model-installed-probe','exec')
    assert {'NOTICE','scripts/validate_v1_3_api_review.py','docs/v1_3_api_review.json','docs/v1_3_release_checklist.md'}<=SOURCE_REQUIRED
    from ncmemsim.ensemble.model_reporting import ModelReport
    data=(ROOT/'tests/fixtures/archives/v1_3_0_dev/model_report.json').read_text(encoding='utf-8')
    report=ModelReport.from_json(data)
    assert sum(s.population.counts['attempted_count'] for s in report.studies)==4
    assert sum(s.population.counts['failed_count'] for s in report.studies)==4


def test_candidate_checklist_does_not_claim_release_approval():
    text=(ROOT/'docs/v1_3_release_checklist.md').read_text(encoding='utf-8')
    assert 'Status: L7 complete' in text
    assert 'Historical preparation checklist' in text
    assert 'exact final release commit' in text
    assert 'No tag, merge or release publication' in text
