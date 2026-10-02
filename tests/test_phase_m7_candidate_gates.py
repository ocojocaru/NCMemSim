# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""M7 review/identity boundaries, immutable archives and remote gate wiring."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import pytest
from scripts import validate_v1_4_api_review as gate
from scripts.validate_dtco_distribution import SOURCE_REQUIRED, THERMAL_PROBE
from ncmemsim.thermal_reporting import ThermalReport

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def candidate_copy(tmp_path):
    for folder in ('docs', 'ncmemsim', 'tests/fixtures'):
        shutil.copytree(ROOT/folder, tmp_path/folder)
    for name in ('README.md', 'CITATION.cff', 'CHANGELOG.md'):
        shutil.copyfile(ROOT/name, tmp_path/name)
    return tmp_path


def test_m7_final_review_retains_published_history():
    result = gate.validate(ROOT)
    assert result['package_version'] == '1.4.0'
    assert result['citation_version'] == '1.4.0'
    assert result['reviewed_modules'] == 4
    assert result['stable_ensemble_exports'] == 59
    assert result['retained_stable_paths'] == 297
    assert result['status'] == 'candidate_contracts_pass_not_release_approval'
    citation = (ROOT/'CITATION.cff').read_text(encoding='utf-8')
    assert not any(line.startswith('doi:') for line in citation.splitlines())
    assert '10.5281/zenodo.23078330' in citation


@pytest.mark.parametrize('fault', ['version', 'citation', 'specific_doi', 'readme', 'review',
    'coefficient', 'audit', 'historical', 'snapshot', 'archive', 'inventory', 'checklist'])
def test_candidate_rejects_unreviewed_identity_scope_or_archival_changes(candidate_copy, fault):
    root = candidate_copy
    if fault == 'version':
        p=root/'ncmemsim/_version.py';p.write_text('__version__="1.4.0.dev0"\n',encoding='utf-8')
    elif fault in ('citation', 'specific_doi'):
        p=root/'CITATION.cff';s=p.read_text(encoding='utf-8')
        s=s.replace('version: 1.4.0','version: 1.3.0') if fault=='citation' else s+'\ndoi: 10.0000/unassigned\n'
        p.write_text(s,encoding='utf-8')
    elif fault == 'readme':
        p=root/'README.md';p.write_text(p.read_text(encoding='utf-8').replace('**Release candidate:** `1.4.0`','stale'),encoding='utf-8')
    elif fault == 'snapshot':
        p=root/'tests/fixtures/releases/v1_3_0/README.md';p.write_text('modified historical identity\n',encoding='utf-8')
    elif fault == 'checklist':
        p=root/'docs/v1_4_release_checklist.md';p.write_text('release approved',encoding='utf-8')
    else:
        name={'review':'docs/v1_4_api_review.json','coefficient':'docs/temperature_coefficients_review.json',
            'audit':'docs/temperature_properties_audit.json','historical':next(iter(gate.HISTORICAL_JSON_SHA256)),
            'archive':'tests/fixtures/archives/v1_4_0_dev/thermal_report.json','inventory':'docs/api_inventory.json'}[fault]
        p=root/name;d=json.loads(p.read_text(encoding='utf-8'));d['unreviewed_change']=True;p.write_text(json.dumps(d),encoding='utf-8')
    with pytest.raises(ValueError):gate.validate(root)


def test_duplicate_review_fields_rejected(candidate_copy):
    path=candidate_copy/'docs/v1_4_api_review.json'
    path.write_text(path.read_text(encoding='utf-8').replace('{','{"status":"forged",',1),encoding='utf-8')
    with pytest.raises(ValueError, match='duplicate'):gate.validate(candidate_copy)


def test_missing_runtime_export_rejected(monkeypatch):
    import ncmemsim.thermal_reporting as module
    monkeypatch.setattr(module,'__all__',module.__all__+['MissingThermalExport'])
    with pytest.raises(ValueError, match='invalid thermal exports'):gate.validate(ROOT)


def test_historical_identity_hashes_tolerate_windows_line_endings(candidate_copy):
    for path in (candidate_copy/'tests/fixtures/releases/v1_3_0').rglob('*'):
        if path.is_file():path.write_bytes(path.read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
    assert gate.validate(candidate_copy)['citation_version']=='1.4.0'


def test_frozen_thermal_archive_preserves_all_failed_attempts():
    path=ROOT/'tests/fixtures/archives/v1_4_0_dev/thermal_report.json'
    raw=json.loads(path.read_text(encoding='utf-8'))
    report=ThermalReport.from_dict(raw)
    assert report.to_dict()==raw
    assert sum(s.to_dict()['summary']['counts']['attempted'] for s in report.studies)==6
    assert sum(s.to_dict()['summary']['counts']['failed'] for s in report.studies)==6
    assert all(r['summary']['mean'] is None for r in report.studies[1].to_dict()['summary']['statistics'])


def test_installed_probe_and_distribution_membership_contract():
    compile(THERMAL_PROBE,'installed-thermal-probe','exec')
    assert {'tests/conftest.py','scripts/validate_v1_4_api_review.py','docs/v1_4_api_review.json',
        'docs/v1_4_release_checklist.md','tests/fixtures/archives/v1_4_0_dev/thermal_report.json',
        'tests/fixtures/releases/v1_3_0/ncmemsim/_version.py'} <= SOURCE_REQUIRED
    assert 'must not run transport/workflows/RNG' in THERMAL_PROBE
    assert 'coherently rehashed projection must fail' in THERMAL_PROBE


def test_remote_gates_cover_exact_candidate_and_python_matrix():
    ci=(ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8')
    docs=(ROOT/'.github/workflows/docs.yml').read_text(encoding='utf-8')
    assert ci.count('python-version: ["3.11", "3.12", "3.13"]')==2
    assert 'python scripts/validate_v1_4_api_review.py' in ci
    assert 'python scripts/validate_api_contract.py' in ci
    assert 'python scripts/validate_dtco_distribution.py' in ci
    assert 'dev/v1.4-temperature-properties' in ci and 'dev/v1.4-temperature-properties' in docs
    assert 'python scripts/validate_documentation.py' in docs
    assert "github.ref == 'refs/heads/main'" in docs


def test_checklist_keeps_publication_and_doi_assignment_pending():
    text=(ROOT/'docs/v1_4_release_checklist.md').read_text(encoding='utf-8')
    assert 'release approval remains pending' in text
    assert 'No tag, merge or release publication' in text
    assert 'Neither is a v1.4 version-specific DOI' in text
    assert 'M7 is not complete' in text
