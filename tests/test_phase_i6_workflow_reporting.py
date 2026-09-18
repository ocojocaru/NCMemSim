"""Authoritative source links, declared variants and reproducible portable exports."""
from copy import deepcopy
import csv
from io import StringIO
import json
import subprocess
import sys
from pathlib import Path
import pytest
pytest.importorskip('scipy')
from examples import phase_i6_linked_workflow_report as reference
from ncmemsim.workflows import WorkflowReport, write_workflow_report
from ncmemsim.hashing import canonical_hash


@pytest.fixture(scope='module')
def reports():
    return {(optical, failure): reference.build_reference_report(optical=optical, include_failures=failure)
        for optical in (False, True) for failure in (False, True)}


def rehash(raw):
    raw.pop('report_hash', None)
    raw['report_hash'] = canonical_hash(raw)
    return json.dumps(raw)


@pytest.mark.parametrize('optical', [False, True])
@pytest.mark.parametrize('failure', [False, True])
def test_complete_source_links_summary_and_counts(reports, optical, failure):
    report = reports[optical, failure]
    raw = report.to_dict()
    assert WorkflowReport.from_json(report.to_json()).to_dict() == raw
    assert raw['scientific_summary'] == {'scientific_status': 'FITTED', 'fit_data_origin': 'synthetic',
        'validation_data_origin': 'synthetic', 'qualification_eligible': True}
    assert raw['workflow_evidence'] == raw['applied_workflow_evidence']['workflow_evidence']
    assert [v[0]['value'] for v in raw['device_variants']] == [300.0, 325.0]
    for section in raw['robust_report']['analyses']:
        a = section['data']
        assert a['source']['study']['evaluation']['parameters']['applied_workflow_evidence'] == raw['applied_workflow_evidence']
        assert a['counts']['total'] == 4 and a['counts']['failed'] == (3 if failure else 0)
        assert a['fractions']['conditional_feasible_fraction_assessed']['value'] == 1


@pytest.mark.parametrize('optical', [False, True])
@pytest.mark.parametrize('fault', ['source', 'application', 'unit', 'scope', 'value', 'missing_variant', 'status', 'origin', 'qualification', 'qualification_number', 'metadata_source'])
def test_rehashed_invalid_links_and_scientific_promotions_rejected(reports, optical, fault):
    raw = deepcopy(reports[optical, False].to_dict())
    other = reports[not optical, False].to_dict()
    if fault == 'source': raw['workflow_evidence'] = other['workflow_evidence']
    elif fault == 'application': raw['applied_workflow_evidence'] = other['applied_workflow_evidence']
    elif fault == 'missing_variant': raw['device_variants'].pop()
    elif fault in ('unit', 'scope', 'value'):
        if fault == 'scope': raw['device_variants'][0][0]['binding']['scope'] = 'model'
        else: raw['device_variants'][0][0][fault] = 'eV' if fault == 'unit' else 310.0
    elif fault == 'status': raw['scientific_summary']['scientific_status'] = 'CALIBRATED'
    elif fault == 'origin': raw['scientific_summary']['fit_data_origin'] = 'measured'
    elif fault == 'qualification': raw['scientific_summary']['qualification_eligible'] = False
    elif fault == 'qualification_number': raw['scientific_summary']['qualification_eligible'] = 1
    else:
        nested = raw['robust_report']
        nested['metadata']['source_workflow_evidence'] = other['workflow_evidence']
        nested.pop('report_hash'); nested['report_hash'] = canonical_hash(nested)
    with pytest.raises(ValueError): WorkflowReport.from_json(rehash(raw))


def test_corruption_duplicate_keys_nonfinite_and_immutable_inspection(reports):
    report = reports[False, False]
    raw = report.to_dict(); raw['name'] = 'changed'
    with pytest.raises(ValueError): WorkflowReport.from_json(json.dumps(raw))
    with pytest.raises(ValueError): WorkflowReport.from_json(report.to_json().replace('{', '{"name":"duplicate",', 1))
    with pytest.raises(ValueError): WorkflowReport.from_json(report.to_json().replace('300.0', 'NaN', 1))
    assert report.to_dict()['name'] != 'changed'


def test_restore_without_fitting_application_sampling_or_physics(reports, monkeypatch):
    import ncmemsim.workflows.application as application
    def forbidden(*a, **kw): pytest.fail('execution during restoration')
    monkeypatch.setattr(reference, 'build_reference_report', forbidden)
    for name in ('apply_device_calibration_parameters', 'run_program_pulse_read', 'run_electro_optical_program_pulse_read'):
        monkeypatch.setattr(application, name, forbidden)
    for report in reports.values():
        assert WorkflowReport.from_json(report.to_json()).report_hash == report.report_hash


@pytest.mark.parametrize('key', [(False, False), (False, True), (True, False), (True, True)])
def test_exports_preserve_full_sources_hashes_labels_and_denominators(reports, key, tmp_path):
    report = reports[key]; destination = tmp_path / 'export'
    files = write_workflow_report(report, destination)
    assert len(files) == 6
    assert WorkflowReport.from_json((destination / 'manifest.json').read_text(encoding='utf-8')).report_hash == report.report_hash
    for method in ('samples_csv', 'statistics_csv', 'nominal_csv', 'robust_csv'):
        rows = list(csv.DictReader(StringIO(getattr(report, method)())))
        assert rows and all(r['workflow_report_hash'] == report.report_hash for r in rows)
        assert all(r['scientific_status'] == 'FITTED' and r['fit_data_origin'] == 'synthetic' for r in rows)
    samples = list(csv.DictReader(StringIO(report.samples_csv())))
    assert len(samples) == 8
    assert 'failure' in report.to_markdown().lower()
    assert 'synthetic' in report.to_markdown() and 'FITTED' in report.to_markdown()
    before = {p.name: p.read_bytes() for p in files}
    with pytest.raises(FileExistsError): write_workflow_report(report, destination)
    assert before == {p.name: p.read_bytes() for p in files}


def test_collision_preflight_prevents_partial_write(reports, tmp_path):
    (tmp_path / 'robust.csv').write_text('keep', encoding='utf-8')
    with pytest.raises(FileExistsError): write_workflow_report(reports[False, False], tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ['robust.csv']


def test_deterministic_repeat_and_cli_no_default_files(reports, tmp_path):
    assert reference.build_reference_report().report_hash == reports[False, False].report_hash
    result = subprocess.run([sys.executable, str(Path(reference.__file__).resolve())], cwd=tmp_path,
        capture_output=True, text=True, check=True)
    assert 'synthetic; scientific status: FITTED' in result.stdout
    assert not list(tmp_path.iterdir())


def test_public_reporting_import_does_not_load_scipy():
    subprocess.run([sys.executable, '-c', 'import sys; from ncmemsim.workflows import WorkflowReport; assert "scipy" not in sys.modules'], check=True)


def test_future_distribution_probe_and_reference_inventory():
    from scripts.validate_dtco_distribution import REQUIRED, SOURCE_REQUIRED, PROBE
    assert 'ncmemsim/workflows/reporting.py' in REQUIRED
    assert 'examples/phase_i6_linked_workflow_report.py' in SOURCE_REQUIRED
    assert 'linked_workflow_reference.build_reference_report' in PROBE
    compile(PROBE, 'future-installed-probe', 'exec')
