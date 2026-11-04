# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""S6 ownership, retained failures, static restoration and deterministic tamper checks."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import pytest
from ncmemsim.barrier_reporting import (
    BarrierStudyReport, write_barrier_study_report, load_barrier_study_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
for name in ('phase_s5_barrier_sensitivity', 'phase_s6_barrier_report'):
    spec = importlib.util.spec_from_file_location(name, ROOT/'examples'/f'{name}.py')
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module)
study = sys.modules['phase_s6_barrier_report']


@pytest.fixture(scope='module')
def report():
    return study.build_report()


def test_complete_accounting_and_owned_roundtrip(report):
    raw = report.to_dict(); s = raw['summary']
    assert s == dict(attempted_count=33, completed_count=32, failed_count=1,
        matched_count=30, mismatched_count=1, unavailable_count=2,
        transmission_underflow_count=1, experimental_qualification=False,
        model_uncertainty_estimated=False)
    assert BarrierStudyReport.from_json(report.to_json()).to_dict() == raw
    raw['cases'][0]['settings']['parameters']['mass_m0'] = 999
    assert report.to_dict()['cases'][0]['settings']['parameters']['mass_m0'] == .2
    with pytest.raises(AttributeError):
        report.extra = True


@pytest.mark.parametrize('field', ['summary','limitations','schema_version'])
def test_report_tamper_rejected(report, field):
    raw = report.to_dict(); raw[field] = None
    with pytest.raises(ValueError):
        BarrierStudyReport.from_dict(raw)


@pytest.mark.parametrize('field', ['result_hash','assessment','result'])
def test_case_tamper_rejected(report, field):
    raw = report.to_dict(); raw['cases'][0][field] = {}
    with pytest.raises(ValueError):
        BarrierStudyReport.from_dict(raw)


def test_duplicate_unknown_nonfinite_json_rejected(report):
    for text in ('{"title":"a","title":"b"}', '{"value":NaN}'):
        with pytest.raises(ValueError):
            BarrierStudyReport.from_json(text)
    raw = report.to_dict(); raw['unknown'] = True
    with pytest.raises(ValueError):
        BarrierStudyReport.from_dict(raw)


def cases(report):
    keys = ('label','result','settings','reference_exponent','reference_description')
    return [{k:r[k] for k in keys} for r in report.to_dict()['cases']]


@pytest.mark.parametrize('reference', [True, -1., float('inf'), float('nan'), '0', 10**400])
def test_invalid_reference_rejected(report, reference):
    rows = cases(report); rows[0]['reference_exponent'] = reference
    with pytest.raises(ValueError):
        BarrierStudyReport('invalid', rows)


def test_empty_duplicate_unknown_cases_rejected(report):
    rows = cases(report)
    for invalid in ([], [rows[0], rows[0]], [{**rows[0], 'extra':1}]):
        with pytest.raises(ValueError):
            BarrierStudyReport('invalid', invalid)


def test_no_device_or_provider_execution_during_restoration(report, monkeypatch):
    import ncmemsim.barrier_transport as transport
    def forbidden(*args, **kwargs):
        raise AssertionError('transport replay')
    monkeypatch.setattr(transport.BarrierTransportEngine, 'step', forbidden)
    monkeypatch.setattr(study, 'build_reference', forbidden)
    assert BarrierStudyReport.from_dict(report.to_dict()).contract_hash == report.contract_hash


def test_deterministic_bundle_and_existing_destination(report, tmp_path):
    a = write_barrier_study_report(report, tmp_path/'a')
    b = write_barrier_study_report(report, tmp_path/'b')
    assert {p.name:p.read_bytes() for p in a.iterdir()} == {p.name:p.read_bytes() for p in b.iterdir()}
    assert load_barrier_study_bundle(a).contract_hash == report.contract_hash
    with pytest.raises(FileExistsError):
        write_barrier_study_report(report, a)


@pytest.mark.parametrize('filename', ['report.json','report.md','cases.csv','segments.csv','bundle.json'])
def test_every_projection_tamper_rejected(report, tmp_path, filename):
    path = write_barrier_study_report(report, tmp_path/'bundle')
    target = path/filename
    if filename == 'report.json':
        raw = json.loads(target.read_text(encoding='utf-8')); raw['summary']['failed_count']=0
        target.write_text(json.dumps(raw), encoding='utf-8')
    else:
        target.write_bytes(target.read_bytes()+b'corrupt')
    with pytest.raises(ValueError):
        load_barrier_study_bundle(path)


@pytest.mark.parametrize('mode', ['extra','missing','directory'])
def test_exact_membership(report, tmp_path, mode):
    path = write_barrier_study_report(report, tmp_path/'bundle')
    if mode == 'extra': (path/'extra').write_text('x')
    else:
        (path/'cases.csv').unlink()
        if mode == 'directory': (path/'cases.csv').mkdir()
    with pytest.raises(ValueError):
        load_barrier_study_bundle(path)


def test_manifest_duplicate_keys_rejected(report, tmp_path):
    path = write_barrier_study_report(report, tmp_path/'bundle')
    (path/'bundle.json').write_text('{"files":{},"files":{}}', encoding='utf-8')
    with pytest.raises(ValueError):
        load_barrier_study_bundle(path)


def test_valid_source_roundoff_preserved(report):
    import math
    from ncmemsim.barrier_evaluation import BarrierEvaluationResult
    rows = cases(report); raw = rows[0]['result']
    # Only the action diagnostic changes; the exponent and exp remain unchanged.
    raw['summary']['action_J_s'] = math.nextafter(raw['summary']['action_J_s'], math.inf)
    BarrierEvaluationResult.from_dict(raw)
    obj = BarrierStudyReport('portable', rows)
    assert BarrierStudyReport.from_json(obj.to_json()).to_dict() == obj.to_dict()


def test_writer_cleans_only_its_created_files(report, tmp_path, monkeypatch):
    original = Path.open
    def failing(path, *args, **kwargs):
        if path.name == 'segments.csv':
            raise OSError('controlled write failure')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', failing)
    target = tmp_path/'bundle'
    with pytest.raises(OSError):
        write_barrier_study_report(report, target)
    assert not target.exists()
