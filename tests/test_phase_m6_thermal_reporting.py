# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Nested thermal evidence, source/analysis links and deterministic bundle integrity."""
from copy import deepcopy
from dataclasses import asdict, replace
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
from examples import phase_m5_thermal_dtco_reference as m5
from ncmemsim import DeviceState
from ncmemsim.dtco import (ExperimentSpec,DesignVariable,DesignVariableRole,ParameterBinding,BindingScope,
    run_cartesian_sweep,iter_cartesian_points,apply_experiment_design_point,MetricAnalysisSpec,MetricDefinition,
    MetricConstraint,ConstraintOperator,ObjectiveDirection,analyze_sweep,analyze_pareto)
from ncmemsim.ensemble import EnsembleScalarDefinition,EnsembleScalarKind,EnsembleObjective
from ncmemsim.ensemble.model_contracts import ModelVariabilitySpec
from ncmemsim.ensemble.model_sampling import generate_model_sample_manifest
from ncmemsim.ensemble.model_execution import execute_model_sample_manifest
from ncmemsim.ensemble.model_analysis import analyze_model_execution
from ncmemsim.ensemble.model_dtco import ModelDTCOStudy,evaluate_model_eligibility,analyze_model_pareto
from ncmemsim.temperature_context import _dump
from ncmemsim.thermal_dtco import resolve_thermal_candidate
from ncmemsim.thermal_reporting import (ThermalRunEvidence,build_thermal_run_evidence,ThermalReportStudy,
    ThermalReport,build_thermal_report,write_thermal_report,load_thermal_report_bundle)
from ncmemsim.program_protocol import ProgramPulseReadProtocol,run_program_pulse_read
from ncmemsim.electro_optical_program_protocol import ElectroOpticalProgramPulseReadProtocol,run_electro_optical_program_pulse_read
from ncmemsim.optics import LightSource
from ncmemsim.photo import PhotoTransitionWeights,PhotoTransitionConfig
from ncmemsim.retention import RetentionConfig,RetentionSolver
from ncmemsim.hashing import canonical_hash


def sources(*,all_failed=False,metric_failure=False):
    device,sampling=m5.build_reference(sample_count=2)
    template=m5.template_for(device)
    temperatures=(400.,450.) if all_failed else (300.,400.)
    experiment=ExperimentSpec.from_device(name='synthetic thermal reporting',device=device,variables=(
        DesignVariable('temperature_K',ParameterBinding(BindingScope.DEVICE,('temperature_K',)),temperatures,DesignVariableRole.ELECTRICAL,'K'),))
    settings={'scope':'synthetic reporting test only','thermal_template':template.to_dict(),'nominal_model_context':sampling.study.model_context.to_dict()}
    def output(device,model,value):
        candidate=resolve_thermal_candidate(template,device,model_context=model)
        return {'candidate':candidate.to_dict(),'candidate_hash':candidate.candidate_hash,'x':value}
    def evaluate(device,protocol,point):
        result=output(device,sampling.study.model_context,2)
        if metric_failure:result.pop('x')
        return result
    metric=MetricAnalysisSpec('synthetic x',(MetricDefinition('x',('x',),'1',ObjectiveDirection.MINIMIZE),),
        (MetricConstraint('bound','x',ConstraintOperator.GE,1.5,'1'),))
    sweep=run_cartesian_sweep(experiment,device,evaluate,evaluation_id='M6-synthetic',evaluation_parameters=settings)
    deterministic=analyze_pareto(analyze_sweep(sweep,metric)).to_dict()
    linked=[]
    for point in iter_cartesian_points(experiment):
        design=apply_experiment_design_point(experiment,device,point.assignments)
        study=ModelVariabilitySpec.from_device(name=sampling.study.name,device=design,model_context=sampling.study.model_context,variables=sampling.study.variables)
        manifest=generate_model_sample_manifest(replace(sampling,study=study))
        execution=execute_model_sample_manifest(manifest,design,lambda r,s:output(r.device,r.model_context,r.sample.sample_index+1),
            evaluation_id='M6-synthetic-model',workflow_context={**settings,'dtco_design_point':point.to_dict()})
        population=analyze_model_execution(execution,metric)
        linked.append(evaluate_model_eligibility(ModelDTCOStudy(point,population)))
    objective=EnsembleObjective('mean_x',EnsembleScalarDefinition('mean_x',EnsembleScalarKind.MEAN,'1','x'),ObjectiveDirection.MINIMIZE)
    return deterministic,{'experiment':experiment.to_dict(),'pareto':analyze_model_pareto(linked,(objective,)).to_dict()}


@pytest.fixture(scope='module')
def source_data():return sources()


def make_report(source_data):
    deterministic,model=source_data
    return build_thermal_report('M6 | source-linked',(
        ThermalReportStudy('deterministic','deterministic_dtco',_dump(deterministic)),
        ThermalReportStudy('population','model_dtco',_dump(model))),limitations=('synthetic only','no calibration or yield'))


@pytest.fixture(scope='module')
def report(source_data):return make_report(source_data)


def rehash(raw,key):raw[key]=canonical_hash({k:v for k,v in raw.items() if k!=key})


def test_report_roundtrip_and_ownership(report):
    assert ThermalReport.from_json(report.to_json()).to_json()==report.to_json()
    raw=report.to_dict();raw['studies'][0]['summary']['counts']['attempted']=999
    assert report.to_dict()['studies'][0]['summary']['counts']['attempted']==2
    assert report.to_dict()['scientific_status']=='conditional-unqualified-simulation'


def test_complete_case_and_failed_domain_accounting(report):
    raw=report.to_dict();a,b=[s['summary']['counts'] for s in raw['studies']]
    assert a=={'attempted':2,'completed':1,'assessed':1,'feasible':1,'infeasible':0,'failed':1}
    assert b=={'attempted':4,'completed':2,'assessed':2,'feasible':1,'infeasible':1,'failed':2}
    rows=raw['studies'][1]['summary']['attempts']
    assert [r['status'] for r in rows]==['infeasible','feasible','failed','failed']
    assert all(r['candidate_hash'] is None for r in rows[-2:])
    assert all(r['failure']['error_type'].endswith('ThermalDomainError') for r in rows[-2:])
    assert raw['studies'][1]['summary']['statistics'][-1]['summary']['denominator']==0
    assert raw['studies'][1]['summary']['statistics'][-1]['summary']['mean'] is None


def test_all_failed_report_preserves_attempts_and_undefined_statistics():
    report=make_report(sources(all_failed=True));restored=ThermalReport.from_json(report.to_json())
    assert all(s.to_dict()['summary']['counts']['completed']==0 for s in restored.studies)
    assert restored.studies[1].to_dict()['summary']['counts']['failed']==4
    assert restored.studies[1].to_dict()['summary']['statistics'][0]['summary']['mean'] is None


def test_metric_failure_kept_separate_from_domain_failure():
    deterministic,_=sources(metric_failure=True)
    study=ThermalReportStudy('metric failures','deterministic_dtco',_dump(deterministic))
    rows=study.to_dict()['summary']['attempts']
    assert study.to_dict()['summary']['counts']['completed']==1
    assert study.to_dict()['summary']['counts']['assessed']==0
    assert rows[0]['failure']['stage']=='extraction'
    assert rows[1]['failure']['type'].endswith('ThermalDomainError')


@pytest.mark.parametrize('mutate',[
    lambda d:d.update(schema_version='unknown'),lambda d:d.update(extra=1),
    lambda d:d.update(scientific_status='calibrated'),lambda d:d.update(restoration_policy='rerun'),
    lambda d:d['studies'][0]['summary']['counts'].update(assessed=99),
    lambda d:d['studies'][1]['summary']['attempts'].pop(),
    lambda d:d['studies'][1]['summary']['statistics'][0]['summary'].update(denominator=99),
    lambda d:d['studies'][0].update(source_hash='0'*64),
    lambda d:d['studies'][0]['source']['points'][0].update(rank=99),
    lambda d:d['studies'][1]['source']['pareto']['sources'][0]['source']['fractions']['coverage_fraction'].update(denominator=99),
    lambda d:d['studies'][1]['source']['pareto']['points'][0].update(rank=99),
    lambda d:d['studies'][0]['source']['source_analysis']['source_sweep']['points'][0]['output'].update(candidate_hash='0'*64),
    lambda d:d['studies'][0]['source']['source_analysis']['source_sweep']['evaluation']['parameters']['thermal_template'].update(enabled=False),
])
def test_rehashed_nested_report_tampering_rejected(report,mutate):
    raw=report.to_dict();mutate(raw);rehash(raw,'report_hash')
    with pytest.raises((ValueError,TypeError)):ThermalReport.from_dict(raw)


def test_fully_rehashed_deterministic_constraints_are_recomputed(source_data):
    deterministic,_=deepcopy(source_data)
    deterministic['source_analysis']['points'][0]['status']='infeasible'
    # The source output is unchanged: no hash refresh may replace recomputation.
    with pytest.raises(ValueError):ThermalReportStudy('x','deterministic_dtco',_dump(deterministic))


def test_successful_candidate_cannot_be_swapped_between_temperatures(source_data):
    deterministic,_=deepcopy(source_data)
    output=deterministic['source_analysis']['source_sweep']['points'][0]['output']
    candidate=output['candidate'];candidate['thermal']['temperature_K']=350
    with pytest.raises(ValueError):ThermalReportStudy('swapped','deterministic_dtco',_dump(deterministic))


def run_fixture(kind='program_pulse_read',*,failed=False):
    from examples.phase_m3_si_temperature_reference import build_context
    template=build_context();device=template.resolve().device
    protocol=ProgramPulseReadProtocol(3,1e-8,0,1e-9)
    initial=DeviceState.empty_for_device(device)
    if kind=='program_pulse_read':parameters={'protocol':protocol.to_dict()}
    elif kind=='electro_optical_program_pulse_read':
        protocol=ElectroOpticalProgramPulseReadProtocol(protocol,LightSource.led(1550,10),PhotoTransitionWeights())
        parameters={'protocol':protocol.to_dict(),'photo_config':asdict(PhotoTransitionConfig())}
    else:parameters={'retention_config':asdict(RetentionConfig(total_time_s=1e-8,initial_dt_s=1e-9,maximum_dt_s=1e-8,output_points=3))}
    workflow={'schema_version':'thermal-workflow-v1','kind':kind,'evaluation_id':'M6-actual-'+kind,'parameters':parameters}
    if failed:
        device.temperature_K=400
        return build_thermal_run_evidence(template,device,workflow=workflow)
    sim=resolve_thermal_candidate(template,device).create_simulator()
    if kind=='program_pulse_read':observations=run_program_pulse_read(sim,protocol,initial_state=initial).to_dict()
    elif kind=='electro_optical_program_pulse_read':observations=run_electro_optical_program_pulse_read(sim,protocol,photo_config=PhotoTransitionConfig(),initial_state=initial).to_dict()
    else:
        result=RetentionSolver(sim,RetentionConfig(**parameters['retention_config'])).run(initial)
        observations={'time_s':result.time_s.tolist(),'qfg_C_m2':result.qfg_C_m2.tolist(),'delta_vfb_V':result.delta_vfb_V.tolist()}
    return build_thermal_run_evidence(template,device,workflow=workflow,observations=observations,initial_state=initial)


@pytest.mark.parametrize('kind',['program_pulse_read','electro_optical_program_pulse_read','retention'])
def test_declared_protocols_initial_states_and_real_observations_roundtrip(kind):
    run=run_fixture(kind);assert ThermalRunEvidence.from_json(run.to_json()).to_dict()==run.to_dict()
    study=ThermalReportStudy(kind,'run',run.to_json())
    assert study.to_dict()['summary']['counts']['completed']==1
    assert run.to_dict()['request']['initial_state']['floating_gates'][0]['P0']==[1.]*7


def test_failed_run_keeps_full_request_and_domain():
    run=run_fixture(failed=True);raw=run.to_dict()
    assert raw['status']=='failed' and raw['observations'] is None and raw['resolution'] is None
    assert raw['request']['device']['device']['temperature_K']==400
    assert raw['failure']['error_type'].endswith('ThermalDomainError')
    assert ThermalRunEvidence.from_dict(raw).to_dict()==raw


@pytest.mark.parametrize('mutate',[
    lambda d:d['resolution'].update(candidate_hash='bad'),
    lambda d:d['resolution']['thermal']['resolved']['physics']['semiconductor'].update(bandgap_eV=9),
    lambda d:d['workflow']['parameters']['protocol'].update(read_dwell_time_s=1),
    lambda d:d['request']['device']['device'].update(temperature_K=400),
    lambda d:d['request']['initial_state']['floating_gates'][0].update(P0=[.5]*7),
    lambda d:d['workflow']['parameters'].update(unknown=1),
    lambda d:d.update(runtime={}),lambda d:d.update(observations=[]),
])
def test_rehashed_run_tampering_rejected(mutate):
    raw=run_fixture().to_dict();mutate(raw);rehash(raw,'source_hash')
    with pytest.raises((ValueError,TypeError)):ThermalRunEvidence.from_dict(raw)


def test_json_duplicates_nonfinite_missing_unknown_rejected(report):
    with pytest.raises(ValueError):ThermalReport.from_json(report.to_json().replace('{','{"name":"forged",',1))
    with pytest.raises(ValueError):ThermalReport.from_json('{"name":NaN}')
    for key in ('studies','report_hash'):
        raw=report.to_dict();raw.pop(key)
        with pytest.raises(ValueError):ThermalReport.from_dict(raw)


def test_restoration_and_export_do_not_simulate_or_sample(report,tmp_path,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('restoration must not replay science/RNG')
    from ncmemsim.simulator import Simulator
    from ncmemsim.transport.integration import AdvancedTransportEngine
    import ncmemsim.ensemble.model_sampling as sampling
    monkeypatch.setattr(Simulator,'relax_voltage',forbidden)
    monkeypatch.setattr(AdvancedTransportEngine,'step',forbidden)
    monkeypatch.setattr(sampling,'generate_model_sample_manifest',forbidden)
    monkeypatch.setattr(np.random,'default_rng',forbidden)
    restored=ThermalReport.from_json(report.to_json())
    destination=write_thermal_report(restored,tmp_path/'no-replay')
    assert load_thermal_report_bundle(destination).report_hash==report.report_hash


def test_deterministic_exports_and_complete_csv(report,tmp_path):
    paths=[write_thermal_report(report,tmp_path/name) for name in ('first','second')]
    assert {p.name:p.read_bytes() for p in paths[0].iterdir()}=={p.name:p.read_bytes() for p in paths[1].iterdir()}
    with (paths[0]/'attempts.csv').open(newline='',encoding='utf-8') as handle:rows=list(csv.DictReader(handle))
    assert len(rows)==6 and sum(r['status']=='failed' for r in rows)==3
    assert all(json.loads(r['profiles_json'])['substrate_gap'] is not None for r in rows)
    assert '| M6 \\| source-linked' not in (paths[0]/'report.md').read_text()  # title safely escaped
    with pytest.raises(FileExistsError):write_thermal_report(report,paths[0])


@pytest.mark.parametrize('filename',['report.json','report.md','attempts.csv','statistics.csv','designs.csv','bundle.json'])
def test_bundle_byte_tampering_rejected(report,tmp_path,filename):
    path=write_thermal_report(report,tmp_path/'bundle')
    with (path/filename).open('ab') as handle:handle.write(b'\nforged')
    with pytest.raises((ValueError,TypeError)):load_thermal_report_bundle(path)


def test_coherently_rehashed_projection_and_extra_file_rejected(report,tmp_path):
    path=write_thermal_report(report,tmp_path/'projection')
    (path/'report.md').write_text('forged but rehashed',encoding='utf-8')
    manifest=json.loads((path/'bundle.json').read_text());manifest['files']['report.md']=hashlib.sha256((path/'report.md').read_bytes()).hexdigest()
    (path/'bundle.json').write_text(json.dumps(manifest),encoding='utf-8')
    with pytest.raises(ValueError):load_thermal_report_bundle(path)
    other=write_thermal_report(report,tmp_path/'extra');(other/'unexpected.txt').write_text('x')
    with pytest.raises(ValueError):load_thermal_report_bundle(other)


def test_invalid_export_validated_before_creating_destination(report,tmp_path):
    forged=deepcopy(report);object.__setattr__(forged.studies[0],'_summary_json','{}')
    with pytest.raises(ValueError):write_thermal_report(forged,tmp_path/'must-not-exist')
    assert not (tmp_path/'must-not-exist').exists()


@pytest.mark.parametrize('variant',['missing','directory','symlink_flag'])
def test_missing_nonregular_and_linked_bundle_members_rejected(report,tmp_path,monkeypatch,variant):
    path=write_thermal_report(report,tmp_path/'invalid-member')
    member=path/'attempts.csv'
    if variant=='missing':member.unlink()
    elif variant=='directory':member.unlink();member.mkdir()
    else:
        original=Path.is_symlink
        monkeypatch.setattr(Path,'is_symlink',lambda p:True if p==member else original(p))
    with pytest.raises(ValueError):load_thermal_report_bundle(path)


def test_partial_export_rolls_back_only_created_files(report,tmp_path,monkeypatch):
    original=Path.open
    destination=tmp_path/'interrupted'
    def interrupt(path,*args,**kwargs):
        if path==destination/'statistics.csv' and args and args[0]=='xb':raise OSError('controlled write failure')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',interrupt)
    with pytest.raises(OSError):write_thermal_report(report,destination)
    assert not destination.exists()


def test_all_failed_bundle_roundtrip(tmp_path):
    report=make_report(sources(all_failed=True))
    path=write_thermal_report(report,tmp_path/'all-failed')
    restored=load_thermal_report_bundle(path)
    assert restored.to_json()==report.to_json()
    with (path/'attempts.csv').open(newline='',encoding='utf-8') as handle:rows=list(csv.DictReader(handle))
    assert len(rows)==6 and all(r['status']=='failed' for r in rows)
