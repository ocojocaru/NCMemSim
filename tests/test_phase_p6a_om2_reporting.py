# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Strict synthetic-study reports/bundles, not measured qualification."""
from copy import deepcopy
from pathlib import Path
import csv,hashlib,json
import pytest
from examples.phase_p5a_om2_numerical_study import run_reference
from ncmemsim.om2_numerics import OM2NumericalStudy,LABELS,summarize,specification
from ncmemsim.om2_sweep import OM2SweepPrediction,_projection
from ncmemsim.om2_reporting import OM2NumericalReport,build_om2_numerical_report,write_om2_numerical_report,load_om2_numerical_report_bundle


@pytest.fixture(scope='module')
def report():
    return build_om2_numerical_report('P6A numerical report',OM2NumericalStudy.from_dict(run_reference()))


def test_owned_report_roundtrip(report):
    assert OM2NumericalReport.from_json(report.to_json())==report
    assert OM2NumericalStudy.from_json(report.study.to_json())==report.study
    raw=report.to_dict();raw['study']['summary']['experimental_qualification']=True
    assert report.to_dict()['study']['summary']['experimental_qualification'] is False
    assert report.to_dict()['limitations']


def test_bundle_exports_all_outcomes_and_nulls(report,tmp_path):
    path=write_om2_numerical_report(report,tmp_path/'report')
    assert {x.name for x in path.iterdir()}=={'report.json','report.md','study.json','cases.csv','checks.csv','bundle.json'}
    assert load_om2_numerical_report_bundle(path)==report
    cases=list(csv.DictReader((path/'cases.csv').open(encoding='utf-8',newline='')))
    assert len(cases)==13
    outside=next(x for x in cases if x['case']=='reference_outside')
    assert outside['contrast_V']=='' and outside['observable_status']=='not_assessable'
    assert all(x['experimental_qualification']=='false' for x in cases)
    text=(path/'report.md').read_text(encoding='utf-8')
    assert 'undefined' in text and 'Experimental qualification: **false**' in text
    assert 'Independent identifiability established: **false**' in text


def test_restore_and_export_no_solver_optics_or_rng(report,tmp_path,monkeypatch):
    from ncmemsim.spectral_context import SpectralSimulator
    from ncmemsim.materials.optics.near_edge import GeSnNearEdgeReferenceModel
    import numpy as np
    def fail(*a,**k):raise AssertionError('unexpected replay')
    monkeypatch.setattr(SpectralSimulator,'relax_voltage',fail)
    monkeypatch.setattr(GeSnNearEdgeReferenceModel,'evaluate',fail)
    monkeypatch.setattr(np.random,'default_rng',fail)
    p=write_om2_numerical_report(report,tmp_path/'first')
    loaded=load_om2_numerical_report_bundle(p)
    q=write_om2_numerical_report(loaded,tmp_path/'second')
    assert all(x.read_bytes()==(q/x.name).read_bytes() for x in p.iterdir())


@pytest.mark.parametrize('file',['report.json','study.json','report.md','cases.csv','checks.csv','bundle.json'])
def test_bundle_tampering_rejected(report,tmp_path,file):
    p=write_om2_numerical_report(report,tmp_path/'tampered')
    with (p/file).open('ab') as stream:stream.write(b'corruption\n')
    with pytest.raises(ValueError):load_om2_numerical_report_bundle(p)


def test_resealing_modified_csv_does_not_bypass_projection_check(report,tmp_path):
    p=write_om2_numerical_report(report,tmp_path/'resealed')
    target=p/'cases.csv';target.write_bytes(target.read_bytes().replace(b'not_assessable',b'assessable'))
    manifest=json.loads((p/'bundle.json').read_text(encoding='utf-8'))
    manifest['files']['cases.csv']=hashlib.sha256(target.read_bytes()).hexdigest()
    (p/'bundle.json').write_text(json.dumps(manifest),encoding='utf-8')
    with pytest.raises(ValueError):load_om2_numerical_report_bundle(p)


def test_existing_directory_never_overwritten(report,tmp_path):
    p=tmp_path/'existing';p.mkdir();(p/'keep.txt').write_text('preserved',encoding='utf-8')
    with pytest.raises(FileExistsError):write_om2_numerical_report(report,p)
    assert (p/'keep.txt').read_text()=='preserved' and len(list(p.iterdir()))==1


@pytest.mark.parametrize('kind',['missing','extra','directory'])
def test_membership_is_exact(report,tmp_path,kind):
    p=write_om2_numerical_report(report,tmp_path/'member')
    if kind=='missing':(p/'study.json').unlink()
    if kind=='extra':(p/'extra.txt').write_text('extra')
    if kind=='directory':(p/'study.json').unlink();(p/'study.json').mkdir()
    with pytest.raises(ValueError):load_om2_numerical_report_bundle(p)


@pytest.mark.parametrize('change',['qualified','limits','hash','schema'])
def test_report_source_and_scope_cannot_be_promoted(report,change):
    raw=deepcopy(report.to_dict())
    if change=='qualified':raw['experimental_qualification']=True
    if change=='limits':raw['limitations']=[]
    if change=='hash':raw['study_hash']='0'*64
    if change=='schema':raw['schema_version']='unknown'
    with pytest.raises(ValueError):OM2NumericalReport.from_dict(raw)


def test_failed_study_case_remains_in_report(report,tmp_path):
    raw=deepcopy(report.study.to_dict());failed=raw['results']['dt_half']
    failed['illuminated_writing']=failed['illuminated_writing'][:2];failed['matched_dark']=[]
    failed['failure']={'run':'illuminated_writing','step_index':2,'exception_type':'builtins.RuntimeError','message':'retained diagnostic failure'}
    failed['summary']=_projection(failed)
    results={k:OM2SweepPrediction.from_dict(raw['results'][k]) for k in LABELS}
    raw['summary']=summarize(results,specification())
    failed_report=build_om2_numerical_report('Failed numerical case',OM2NumericalStudy.from_dict(raw))
    p=write_om2_numerical_report(failed_report,tmp_path/'failure')
    loaded=load_om2_numerical_report_bundle(p)
    assert loaded.study.summary['case_status']['dt_half']=='sequence_failed'
    assert 'retained diagnostic failure' in (p/'cases.csv').read_text(encoding='utf-8')


def test_failed_write_cleans_only_new_bundle(report,tmp_path,monkeypatch):
    original=Path.open
    def broken(self,*a,**k):
        if self.name=='checks.csv' and a and a[0]=='xb':raise OSError('diagnostic write failure')
        return original(self,*a,**k)
    monkeypatch.setattr(Path,'open',broken)
    destination=tmp_path/'partial'
    with pytest.raises(OSError):write_om2_numerical_report(report,destination)
    assert not destination.exists()
