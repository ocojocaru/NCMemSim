# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Spectral review, retained history, immutable archives and preparation boundaries."""
from pathlib import Path
import json
import shutil
import pytest
from scripts import validate_v1_5_api_review as gate
from scripts.validate_dtco_distribution import SOURCE_REQUIRED,SPECTRAL_PROBE
from ncmemsim.spectral_reporting import SpectralReport

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def candidate_copy(tmp_path):
    for folder in ('docs','ncmemsim','tests/fixtures'):shutil.copytree(ROOT/folder,tmp_path/folder)
    for name in ('README.md','CHANGELOG.md','CITATION.cff'):shutil.copyfile(ROOT/name,tmp_path/name)
    return tmp_path


def test_preparation_identity_and_retained_contracts():
    result=gate.validate(ROOT)
    assert result=={'status':'candidate_contracts_pass_not_release_approval','package_version':'1.5.0.dev0',
        'citation_version':'1.4.0','latest_published_stable':'1.4.0','retained_stable_paths':297,
        'stable_ensemble_exports':59,'reviewed_modules':5,'spectral_exports':24}


@pytest.mark.parametrize('fault',['version','citation','readme','review','source','archive','snapshot','audit','thermal','model','checklist','inventory'])
def test_unreviewed_or_partial_preparation_rejected(candidate_copy,fault):
    root=candidate_copy
    if fault=='version':
        p=root/'ncmemsim/_version.py';p.write_text('__version__="1.5.0"\n',encoding='utf-8')
    elif fault=='citation':
        p=root/'CITATION.cff';p.write_text(p.read_text(encoding='utf-8').replace('23102549','99999999'),encoding='utf-8')
    elif fault=='readme':
        p=root/'README.md';p.write_text('release approved',encoding='utf-8')
    elif fault=='source':
        with (root/'ncmemsim/spectral_reporting.py').open('a',encoding='utf-8') as handle:handle.write('\n# unreviewed implementation change\n')
    elif fault=='snapshot':
        p=root/'tests/fixtures/releases/v1_4_0/CITATION.cff';p.write_text('changed historical citation',encoding='utf-8')
    elif fault=='checklist':
        p=root/'docs/v1_5_release_checklist.md';p.write_text('release approved',encoding='utf-8')
    else:
        names={'review':'docs/v1_5_api_review.json','archive':'tests/fixtures/archives/v1_5_0_dev/spectral_report.json',
            'audit':'docs/broadband_optics_audit.json','thermal':'docs/v1_4_api_review.json','model':'docs/v1_3_api_review.json',
            'inventory':'docs/api_inventory.json'}
        p=root/names[fault];raw=json.loads(p.read_text(encoding='utf-8'));raw['unreviewed']=True;p.write_text(json.dumps(raw),encoding='utf-8')
    with pytest.raises(ValueError):gate.validate(root)


def test_duplicate_review_keys_rejected(candidate_copy):
    p=candidate_copy/'docs/v1_5_api_review.json';p.write_text(p.read_text(encoding='utf-8').replace('{','{"status":"forged",',1),encoding='utf-8')
    with pytest.raises(ValueError,match='duplicate'):gate.validate(candidate_copy)


def test_missing_runtime_export_rejected(monkeypatch):
    import ncmemsim.spectral_reporting as module
    monkeypatch.setattr(module,'__all__',module.__all__+['MissingSpectralExport'])
    with pytest.raises(ValueError,match='invalid spectral exports'):gate.validate(ROOT)


def test_frozen_development_archive_and_no_publication_claim():
    raw=json.loads((ROOT/'tests/fixtures/archives/v1_5_0_dev/spectral_report.json').read_text(encoding='utf-8'))
    report=SpectralReport.from_dict(raw)
    assert report.to_dict()==raw
    assert report.summary['counts']=={'attempted':2,'completed':0,'failed':2}
    assert report.summary['pulse_delta_vfb_V']['mean'] is None
    assert report.to_dict()['evidence']['runtime']['ncmemsim']=='1.5.0.dev0'
    text=(ROOT/'docs/v1_5_release_checklist.md').read_text(encoding='utf-8')
    assert 'N7 is not complete' in text and 'release approval remains pending' in text
    assert '23cf78cd8088658c9eb95a56f46fa30d04c83b14' in text


def test_distribution_probe_and_source_membership():
    compile(SPECTRAL_PROBE,'installed-spectral-probe','exec')
    assert {'scripts/validate_v1_5_api_review.py','docs/v1_5_api_review.json','docs/v1_5_release_checklist.md',
        'tests/fixtures/archives/v1_5_0_dev/spectral_report.json','tests/fixtures/releases/v1_4_0/CITATION.cff'}<=SOURCE_REQUIRED
    assert 'coherently rehashed projection must fail' in SPECTRAL_PROBE
    assert 'is_relative_to(Path(sys.prefix)' in SPECTRAL_PROBE


def test_ci_runs_current_review_and_supported_python_matrix():
    ci=(ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert 'python scripts/validate_v1_5_api_review.py' in ci
    assert 'python scripts/validate_api_contract.py' in ci
    assert ci.count('python-version: ["3.11", "3.12", "3.13"]')==2
    assert 'dev/v1.5-broadband-optics' in ci


def test_snapshot_hashes_tolerate_windows_line_endings(candidate_copy):
    for name in gate.SNAPSHOTS:
        p=candidate_copy/'tests/fixtures/releases/v1_4_0'/name
        p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
    assert gate.validate(candidate_copy)['citation_version']=='1.4.0'
