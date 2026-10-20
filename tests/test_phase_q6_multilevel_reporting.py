# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Q6 typed source reports, all result families, static projections and strict bundles."""
from dataclasses import replace, FrozenInstanceError
from pathlib import Path
import csv
import hashlib
import json
import shutil
import numpy as np
import pytest
from examples.phase_q4_gradual_update_reference import build
from examples.phase_q5_retention_ensemble_reference import build_ensemble_plan
from ncmemsim.multilevel_contracts import (ElectricalPulseStep, ElectricalPulseSequence,
    ElectricalSequenceExperiment, PulseSequenceEvidence)
from ncmemsim.multilevel_execution import run_electrical_sequence, ElectricalSequenceResult
from ncmemsim.multilevel_analysis import (MultilevelPreparation, MultilevelStudyPlan,
    run_multilevel_study, analyze_multilevel_results)
from ncmemsim.multilevel_updates import analyze_gradual_updates, analyze_paired_updates
from ncmemsim.multilevel_optical import run_matched_optical_sequence, OpticalSequenceResult
from ncmemsim.multilevel_retention import MultilevelRetentionPlan, run_multilevel_retention, analyze_multilevel_retention
from ncmemsim.multilevel_ensemble import run_multilevel_ensemble
from ncmemsim.multilevel_reporting import (MultilevelReportCase, MultilevelReport,
    build_multilevel_report, write_multilevel_report, load_multilevel_report_bundle)
import ncmemsim.multilevel_reporting as reporting

EVIDENCE=PulseSequenceEvidence('Q6 tests','controlled synthetic fixtures','synthetic','no experimental qualification')


@pytest.fixture(scope='module')
def base():
    a,b,optical,reference=build(internal_dt_s=1e-8)
    steps=a.sequence.steps[:2]
    a=replace(a,sequence=replace(a.sequence,steps=steps))
    state=a.initial_state
    state.metadata={'failure':{'stage':'ordinary user metadata','message':'not an execution failure'}}
    a=ElectricalSequenceExperiment.from_state(a.name,a.context,a.sequence,state,a.weight_reference)
    optical=replace(optical,electrical=a,illuminated_step_ids=tuple(x.step_id for x in steps))
    result=run_electrical_sequence(a)
    negative=analyze_gradual_updates(result,reference,expected_direction='increasing',minimum_excursion_V=1e-6)
    return a,optical,reference,result,negative


@pytest.fixture(scope='module')
def report(base):
    cases=(MultilevelReportCase.from_result('Electrical baseline',base[3],EVIDENCE),
           MultilevelReportCase.from_result('Wrong direction | <script> with\nnewline',base[4],EVIDENCE))
    return build_multilevel_report('Q6 controlled | report',cases,EVIDENCE)


@pytest.fixture(scope='module')
def all_report(base):
    a,optical,reference,result,negative=base
    positive=analyze_gradual_updates(result,reference,expected_direction='decreasing',minimum_excursion_V=1e-6)
    paired=analyze_paired_updates(positive,negative)
    matched=run_matched_optical_sequence(optical)
    levels=[]
    for name,duration in (('L0',2e-8),('L1',1e-8)):
        sequence=ElectricalPulseSequence(name,(ElectricalPulseStep('write','program',6.,duration,1e-9),),a.sequence.readout,EVIDENCE)
        experiment=ElectricalSequenceExperiment.from_state(name,a.context,sequence,a.initial_state)
        levels.append(MultilevelPreparation(name,experiment,0.))
    study=MultilevelStudyPlan('Q6 small study',tuple(levels),1e-10,'deterministic',EVIDENCE)
    prepared=run_multilevel_study(study)
    retention=run_multilevel_retention(MultilevelRetentionPlan(prepared,(0.,1e-8),0.,1e-9,EVIDENCE))
    ensemble=run_multilevel_ensemble(replace(build_ensemble_plan(study,sample_count=1),delays_s=(0.,)))
    sources=(('electrical',result),('separation',prepared),('updates',positive),('paired_updates',paired),
        ('optical',OpticalSequenceResult.from_dict(matched.to_dict()['light'])),('matched_optical',matched),
        ('retention',retention),('ensemble',ensemble))
    return build_multilevel_report('Every Q result family',tuple(
        MultilevelReportCase.from_result(name,value,EVIDENCE) for name,value in sources),EVIDENCE)


def rows(path,name):
    with (path/name).open(encoding='utf-8',newline='') as stream:return list(csv.DictReader(stream))


def resolve(source,pointer):
    value=source
    for item in pointer.split('/')[1:]:
        item=item.replace('~1','/').replace('~0','~')
        value=value[int(item)] if type(value) is list else value[item]
    return value


def test_owned_strict_roundtrip_and_hashes(report):
    assert MultilevelReport.from_json(report.to_json()).contract_hash==report.contract_hash
    assert report.summary['case_count']==2 and report.summary['experimental_qualification'] is False
    for case in report.cases:
        assert MultilevelReportCase.from_json(case.to_json()).source_hash==case.source_hash
        assert case.source_hash==hashlib.sha256(case.source_json.encode('utf-8')).hexdigest()
    raw=report.to_dict();raw['cases'][0]['source']['steps'].clear()
    assert len(report.cases[0].source['steps'])==2
    with pytest.raises(FrozenInstanceError):report.title='changed'


def test_all_eight_families_keep_exact_sources_and_units(all_report,tmp_path):
    path=write_multilevel_report(all_report,tmp_path/'all')
    restored=load_multilevel_report_bundle(path)
    assert restored.to_dict()==all_report.to_dict()
    assert set(x.kind for x in restored.cases)==set(reporting._TYPES)
    assert {x.name for x in path.iterdir()}==reporting._FILES
    observations=rows(path,'observations.csv');metrics=rows(path,'metrics.csv')
    byname={x.name:x for x in restored.cases}
    for row in observations:
        case=byname[row['case']]
        assert row['source_hash']==case.source_hash
        resolve(case.source,row['source_path'])
    for row in metrics:
        assert json.loads(row['value_json'])==resolve(byname[row['case']].source,row['source_path'])
    assert any(x['role']=='contrast' and x['observable']=='light_minus_dark_delta_vfb_V' for x in observations)
    assert any(x['sample_id'] for x in observations if x['kind']=='ensemble')
    assert any(x['unit']=='m^-2' for x in metrics if 'absorbed_photon_fluence_by_fg_m2' in x['source_path'])
    assert any(x['unit']=='V' for x in metrics if 'read_delta_vfb_V' in x['source_path'])
    assert any(x['unit']=='1' for x in metrics if 'signed_weight_updates' in x['source_path'])


def test_nulls_negative_cases_metadata_and_no_false_failures(report,tmp_path):
    path=write_multilevel_report(report,tmp_path/'negative')
    assert rows(path,'failures.csv')==[]  # metadata key "failure" is not a runtime failure
    cases=rows(path,'cases.csv');assert cases[1]['source_status']=='not_assessable'
    metrics=rows(path,'metrics.csv')
    deviation=next(x for x in metrics if x['case']==report.cases[1].name and x['source_path']=='/summary/linearity_deviation')
    assert deviation['value_json']=='null' and deviation['unit']=='1'
    text=(path/'report.md').read_text(encoding='utf-8')
    assert 'undefined' in text and 'Experimental qualification: **false**' in text
    assert '&lt;script&gt;' in text and '&#124;' in text and '<script>' not in text
    assert all(x['experimental_qualification']=='false' for x in cases)


@pytest.mark.parametrize('field',['schema','kind','source_hash','summary','qualification','limits','extra'])
def test_report_tamper_rejected(report,field):
    raw=report.to_dict()
    if field=='schema':raw['schema_version']='unknown'
    elif field=='kind':raw['cases'][0]['kind']='updates'
    elif field=='source_hash':raw['cases'][0]['source_hash']='0'*64
    elif field=='summary':raw['summary']['case_count']=0
    elif field=='qualification':raw['experimental_qualification']=True
    elif field=='limits':raw['limitations']=[]
    else:raw['extra']=0
    with pytest.raises(ValueError):MultilevelReport.from_dict(raw)


def test_declarations_and_nonfinite_json_rejected(report):
    for cases in ((),list(report.cases),(report.cases[0],report.cases[0]),(object(),)):
        with pytest.raises(ValueError):build_multilevel_report('invalid cases',cases,EVIDENCE)
    with pytest.raises(ValueError):MultilevelReportCase.from_result('unknown',object(),EVIDENCE)
    with pytest.raises(ValueError):MultilevelReportCase('name','unknown','{}',EVIDENCE)
    with pytest.raises(ValueError):MultilevelReport.from_json('{"x":1,"x":2}')
    with pytest.raises(ValueError):MultilevelReport.from_json('{"x":NaN}')
    raw=report.cases[0].to_dict();raw['source']['steps'][0]['read']['delta_vfb_V']+=1
    with pytest.raises(ValueError):MultilevelReportCase.from_dict(raw)


@pytest.mark.parametrize('filename',sorted(reporting._FILES))
def test_modified_bundle_file_rejected(report,tmp_path,filename):
    path=write_multilevel_report(report,tmp_path/'tamper')
    with (path/filename).open('ab') as stream:stream.write(b'\nmodified\n')
    with pytest.raises(ValueError):load_multilevel_report_bundle(path)


def test_resealed_csv_still_requires_source_projection(report,tmp_path):
    path=write_multilevel_report(report,tmp_path/'resealed')
    target=path/'cases.csv';target.write_bytes(target.read_bytes().replace(b'not_assessable',b'assessable'))
    manifest=json.loads((path/'bundle.json').read_text(encoding='utf-8'))
    manifest['files']['cases.csv']=hashlib.sha256(target.read_bytes()).hexdigest()
    (path/'bundle.json').write_text(json.dumps(manifest),encoding='utf-8')
    with pytest.raises(ValueError):load_multilevel_report_bundle(path)


@pytest.mark.parametrize('kind',['missing','extra','directory'])
def test_exact_membership(report,tmp_path,kind):
    path=write_multilevel_report(report,tmp_path/'member')
    if kind=='missing':(path/'metrics.csv').unlink()
    elif kind=='extra':(path/'extra.txt').write_text('extra',encoding='utf-8')
    else:(path/'metrics.csv').unlink();(path/'metrics.csv').mkdir()
    with pytest.raises(ValueError):load_multilevel_report_bundle(path)


def test_duplicate_manifest_json_keys_rejected(report,tmp_path):
    path=write_multilevel_report(report,tmp_path/'duplicate')
    manifest=(path/'bundle.json').read_text(encoding='utf-8')
    (path/'bundle.json').write_text('{"report_hash":"forged",'+manifest.lstrip()[1:],encoding='utf-8')
    with pytest.raises(ValueError):load_multilevel_report_bundle(path)


def test_no_overwrite_and_failed_write_cleanup(report,tmp_path,monkeypatch):
    keep=tmp_path/'existing';keep.mkdir();(keep/'keep.txt').write_text('preserved',encoding='utf-8')
    with pytest.raises(FileExistsError):write_multilevel_report(report,keep)
    assert (keep/'keep.txt').read_text()=='preserved'
    original=Path.open
    def broken(self,*args,**kwargs):
        if self.name=='metrics.csv' and args and args[0]=='xb':raise OSError('injected write failure')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,'open',broken)
    target=tmp_path/'partial'
    with pytest.raises(OSError):write_multilevel_report(report,target)
    assert not target.exists() and (keep/'keep.txt').read_text()=='preserved'


def test_runtime_failure_and_missing_preparation_remain_visible(base,tmp_path,monkeypatch):
    from ncmemsim.temperature_context import ThermalSimulator
    original=ThermalSimulator.relax_voltage
    def fail(self,*args,**kwargs):
        if kwargs.get('dwell_time_s',0)>0:raise RuntimeError('controlled Q6 physical step failure')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(ThermalSimulator,'relax_voltage',fail)
    failed=run_electrical_sequence(base[0])
    report=build_multilevel_report('failed execution',
        (MultilevelReportCase.from_result('failed',failed,EVIDENCE),),EVIDENCE)
    path=write_multilevel_report(report,tmp_path/'failed')
    failures=rows(path,'failures.csv')
    assert len(failures)==1 and failures[0]['stage']=='step'
    assert 'controlled Q6 physical step failure' in failures[0]['message']
    assert load_multilevel_report_bundle(path).cases[0].source['failure']==failed.to_dict()['failure']
    assert rows(path,'cases.csv')[0]['source_status']=='failed'
    assert len(rows(path,'observations.csv'))==1  # accepted initial read, no invented endpoint


def test_missing_retention_and_source_denominators_exported(all_report,tmp_path):
    case=next(x for x in all_report.cases if x.kind=='retention')
    raw=case.source
    plan=MultilevelRetentionPlan.from_dict(raw['plan'])
    probes=tuple(tuple(None if x is None else ElectricalSequenceResult.from_dict(x) for x in row) for row in raw['probes'])
    missing=analyze_multilevel_retention(plan,(probes[0],(None,*probes[1][1:])))
    report=build_multilevel_report('partial retention',
        (MultilevelReportCase.from_result('missing probe',missing,EVIDENCE),),EVIDENCE)
    path=write_multilevel_report(report,tmp_path/'missing')
    observation=next(x for x in rows(path,'observations.csv') if x['status']=='missing_probe')
    assert observation['readout_V']==observation['signed_drift_V']==''
    metrics={x['source_path']:json.loads(x['value_json']) for x in rows(path,'metrics.csv')}
    assert metrics['/summary/missing_probe_count']==1
    assert metrics['/summary/requested_observation_count']==4
    assert metrics['/summary/completed_observation_count']==3


def test_restore_reexport_all_types_without_solver_material_sampling_or_rng(all_report,tmp_path,monkeypatch):
    from ncmemsim.temperature_context import ResolvedThermalContext, ThermalSimulator
    from ncmemsim.spectral_context import SpectralSimulator
    from ncmemsim.ensemble import RNGSpec
    import ncmemsim.spectral_absorption as absorption
    def forbidden(*args,**kwargs):raise AssertionError('unexpected workflow/RNG/material sampling')
    monkeypatch.setattr(ResolvedThermalContext,'create_simulator',forbidden)
    monkeypatch.setattr(ThermalSimulator,'relax_voltage',forbidden)
    monkeypatch.setattr(SpectralSimulator,'relax_voltage',forbidden)
    monkeypatch.setattr(absorption,'evaluate_floating_gate_spectrum',forbidden)
    monkeypatch.setattr(RNGSpec,'create_generator',forbidden)
    monkeypatch.setattr(np.random,'default_rng',forbidden)
    first=write_multilevel_report(all_report,tmp_path/'first')
    loaded=load_multilevel_report_bundle(first)
    second=write_multilevel_report(loaded,tmp_path/'second')
    assert all(x.read_bytes()==(second/x.name).read_bytes() for x in first.iterdir())


@pytest.mark.parametrize('family',['separation','ensemble'])
def test_missing_source_slots_remain_rows_not_zero_predictions(all_report,tmp_path,family):
    source=next(x.source for x in all_report.cases if x.kind==family)
    if family=='separation':
        plan=MultilevelStudyPlan.from_dict(source['plan'])
        result=analyze_multilevel_results(plan,(None,ElectricalSequenceResult.from_dict(source['results'][1])))
    else:
        from ncmemsim.multilevel_ensemble import MultilevelEnsembleResult, _projection
        source['points'][0]=None
        source['summary']=_projection(source)
        result=MultilevelEnsembleResult.from_dict(source)
    report=build_multilevel_report('Missing evidence is not zero',
        (MultilevelReportCase.from_result('missing '+family,result,EVIDENCE),),EVIDENCE)
    path=write_multilevel_report(report,tmp_path/family)
    missing=[x for x in rows(path,'observations.csv') if x['status']=='missing']
    assert len(missing)==1 and missing[0]['readout_V']==''
    metrics={x['source_path']:json.loads(x['value_json']) for x in rows(path,'metrics.csv')}
    if family=='separation':
        assert metrics['/summary/missing_level_count']==1
        assert metrics['/summary/requested_level_count']==2
    else:
        assert metrics['/summary/missing_sample_count']==1
        assert metrics['/summary/requested_sample_count']==1
        assert metrics['/summary/attempted_sample_count']==0
