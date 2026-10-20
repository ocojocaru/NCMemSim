# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Q2 state chains, zero-dwell audits, failure prefixes and static archives."""
from dataclasses import replace
import json
import numpy as np
import pytest
from ncmemsim import DeviceBuilder, DeviceState, Simulator
from ncmemsim.temperature_context import ThermalContext, ThermalSimulator, ResolvedThermalContext
from ncmemsim.multilevel_contracts import (
    PulseSequenceEvidence, ElectricalPulseStep, DarkReadoutPolicy,
    ElectricalPulseSequence, ElectricalSequenceExperiment,
)
from ncmemsim.multilevel_execution import ElectricalSequenceResult, run_electrical_sequence
from ncmemsim.thermal_reporting import _state_payload
from ncmemsim.program_protocol import ProgramPulseReadProtocol, run_program_pulse_read


def build(n_fgs=1):
    device=DeviceBuilder.v2(n_fgs=n_fgs)
    context=ThermalContext.from_nominal(device).resolve()
    source=PulseSequenceEvidence('Q2 tests','test fixture','synthetic','not measured')
    read=DarkReadoutPolicy('common read',0.,source)
    steps=(ElectricalPulseStep('write-1','program',2.,1e-8,1e-10),
           ElectricalPulseStep('idle-1','idle',0.,2e-9,1e-10),
           ElectricalPulseStep('write-2','program',2.,1e-8,1e-10))
    seq=ElectricalPulseSequence('Q2 test sequence',steps,read,source)
    state=DeviceState.empty_for_device(device)
    for gate in state.floating_gates:
        gate.P0[:]=.8;gate.P1[:]=.2
    state.time_s=1e-6
    state.metadata={'nested':{'ids':['preparation']}}
    return ElectricalSequenceExperiment.from_state('Q2 test',context,seq,state)


@pytest.fixture(scope='module')
def experiment():return build()


@pytest.fixture(scope='module')
def result(experiment):return run_electrical_sequence(experiment)


def test_completed_owned_state_chain(experiment,result):
    raw=result.to_dict();s=result.summary
    assert s['status']=='completed'
    assert s['completed_step_count']==s['attempted_step_count']==3
    assert s['completed_read_count']==s['attempted_read_count']==4
    assert s['weight_evaluation']=='not_performed'
    previous=experiment.to_dict()['initial_state']
    for event,step in zip(raw['steps'],experiment.sequence.steps):
        assert event['initial_state']==previous
        assert event['final_state']['time_s']==previous['time_s']+step.duration_s
        assert event['read']['state']['time_s']==event['final_state']['time_s']
        previous=event['final_state']
    assert result.final_state.time_s==s['final_time_s']
    assert s['experimental_qualification'] is False
    assert run_electrical_sequence(experiment).contract_hash==result.contract_hash


@pytest.mark.parametrize('n_fgs',[1,2,3])
def test_exact_explicit_backward_euler_continuation(n_fgs):
    exp=build(n_fgs);res=run_electrical_sequence(exp);raw=res.to_dict()
    assert res.summary['status']=='completed'
    sim=exp.context.create_simulator();state=exp.initial_state
    for event,step in zip(raw['steps'],exp.sequence.steps):
        out=sim.relax_voltage(state,step.gate_voltage_V,step.duration_s,step.internal_dt_s,occupancy_integrator='backward_euler')
        assert _state_payload(out['state'],sim.device)==event['final_state']
        state=out['state']


def test_single_pulse_retained_protocol_at_same_integrator(experiment,monkeypatch):
    # Legacy API has no integrator parameter. Route its explicit entry point to
    # the same BE method solely in this comparator, leaving production defaults intact.
    original=ThermalSimulator.relax_voltage
    def same_integrator(self,*args,**kwargs):
        kwargs['occupancy_integrator']='backward_euler'
        return original(self,*args,**kwargs)
    monkeypatch.setattr(ThermalSimulator,'relax_voltage',same_integrator)
    exp=replace(experiment,sequence=replace(experiment.sequence,steps=experiment.sequence.steps[:1]))
    result=run_electrical_sequence(exp)
    step=exp.sequence.steps[0]
    legacy=run_program_pulse_read(exp.context.create_simulator(),
        ProgramPulseReadProtocol(step.gate_voltage_V,step.duration_s,0.,step.internal_dt_s),initial_state=exp.initial_state)
    assert result.summary['status']=='completed'
    assert result.to_dict()['steps'][0]['read']['delta_vfb_V']==legacy.delta_vfb_V
    assert _state_payload(result.final_state,exp.context.device)==_state_payload(legacy.programmed_state,exp.context.device)


def test_input_and_returned_projection_isolation(experiment,result):
    before=experiment.to_json();raw=result.to_dict();state=result.final_state
    state.metadata['nested']['ids'].append('mutation')
    state.floating_gates[0].P0[:]=0
    raw['steps'][0]['initial_state']['metadata']['nested']['ids'].clear()
    assert experiment.to_json()==before
    assert result.final_state.metadata['nested']['ids']==['preparation']
    assert np.all(result.final_state.floating_gates[0].P0>0)


@pytest.mark.parametrize('stage',['setup','initial_read','step','read'])
def test_failures_preserve_physical_prefix(experiment,monkeypatch,stage):
    original=ThermalSimulator.relax_voltage
    counts={'read':0,'step':0}
    def intercepted(self,*args,**kwargs):
        kind='read' if kwargs.get('dwell_time_s')==0 else 'step'
        counts[kind]+=1
        if ((stage=='initial_read' and kind=='read' and counts[kind]==1) or
            (stage=='read' and kind=='read' and counts[kind]==2) or
            (stage=='step' and kind=='step' and counts[kind]==2)):
            raise RuntimeError('injected '+stage+' failure')
        return original(self,*args,**kwargs)
    if stage=='setup':
        def fail(self):raise RuntimeError('injected setup failure')
        monkeypatch.setattr(ResolvedThermalContext,'create_simulator',fail)
    else:monkeypatch.setattr(ThermalSimulator,'relax_voltage',intercepted)
    res=run_electrical_sequence(experiment);raw=res.to_dict()
    assert res.summary['status']=='failed' and raw['failure']['stage']==stage
    expected=0 if stage in ('setup','initial_read') else 1
    assert res.summary['completed_step_count']==expected
    if stage=='read':
        assert raw['steps'][-1]['read'] is None
        assert res.final_state.time_s==raw['steps'][-1]['final_state']['time_s']
    assert ElectricalSequenceResult.from_json(res.to_json()).contract_hash==res.contract_hash


@pytest.mark.parametrize('change',['roundoff','physical_change','clock_change'])
def test_read_audit_and_original_continuation(experiment,monkeypatch,change):
    original=ThermalSimulator.relax_voltage
    def intercepted(self,*args,**kwargs):
        out=original(self,*args,**kwargs)
        if kwargs.get('dwell_time_s')==0:
            state=out['state'];g=state.floating_gates[0]
            if change=='clock_change':state.time_s+=1e-9
            else:
                amount=1e-16 if change=='roundoff' else 1e-6
                g.P0[0]-=amount;g.P1[0]+=amount
        return out
    monkeypatch.setattr(ThermalSimulator,'relax_voltage',intercepted)
    result=run_electrical_sequence(experiment)
    if change!='roundoff':
        assert result.summary['status']=='failed'
        assert result.to_dict()['failure']['stage']=='initial_read'
    else:
        assert result.summary['status']=='completed'
        raw=result.to_dict()
        assert raw['initial_read']['max_probability_change']>0
        assert raw['steps'][0]['initial_state']==experiment.to_dict()['initial_state']
        assert raw['initial_read']['state']['floating_gates'][0]['P0']!=raw['steps'][0]['initial_state']['floating_gates'][0]['P0']


@pytest.mark.parametrize('mutation',['summary','source','chain','clock','index','missing_read','read_source','read_value','vector','version','extra','failure','runtime'])
def test_tampered_archives_rejected(result,mutation):
    raw=result.to_dict()
    if mutation=='summary':raw['summary']['completed_step_count']=0
    elif mutation=='source':raw['experiment_hash']='0'*64
    elif mutation=='chain':raw['steps'][1]['initial_state']['metadata']={}
    elif mutation=='clock':raw['steps'][0]['final_state']['time_s']+=1
    elif mutation=='index':raw['steps'][0]['step_index']=True
    elif mutation=='missing_read':raw['steps'][0]['read']=None
    elif mutation=='read_source':raw['initial_read']['source_state_hash']='0'*64
    elif mutation=='read_value':raw['initial_read']['delta_vfb_V']+=.01
    elif mutation=='vector':raw['initial_read']['qfg_by_fg_C_m2']=[]
    elif mutation=='version':raw['schema_version']='future'
    elif mutation=='extra':raw['extra']=1
    elif mutation=='failure':raw['failure']={'stage':'read','step_index':1,'exception_type':'RuntimeError','message':'forged'}
    elif mutation=='runtime':raw['runtime']['python']=None
    with pytest.raises(ValueError):ElectricalSequenceResult.from_dict(raw)


def test_restoration_no_solver_optics_rng(result,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('replay forbidden')
    monkeypatch.setattr(ThermalSimulator,'relax_voltage',forbidden)
    monkeypatch.setattr(ResolvedThermalContext,'create_simulator',forbidden)
    monkeypatch.setattr(np.random,'default_rng',forbidden)
    restored=ElectricalSequenceResult.from_json(result.to_json())
    assert restored.contract_hash==result.contract_hash


def test_dark_execution_never_evaluates_optics(experiment,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('optical path forbidden')
    monkeypatch.setattr(Simulator,'_evaluate_optical_absorption',forbidden)
    assert run_electrical_sequence(experiment).summary['status']=='completed'


def test_json_boundary_and_bad_requests(result):
    with pytest.raises(ValueError):run_electrical_sequence(object())
    for text in ('{}',result.to_json()[:-1]+',"extra":NaN}',result.to_json()[:-1]+',"summary":{}}'):
        with pytest.raises(ValueError):ElectricalSequenceResult.from_json(text)


def test_read_frequency_does_not_reset_or_alter_physical_chain(experiment):
    first=experiment.sequence.steps[0]
    one=replace(experiment,sequence=replace(experiment.sequence,steps=(replace(first,duration_s=2e-8),)))
    two=replace(experiment,sequence=replace(experiment.sequence,steps=(first,replace(first,step_id='second'))))
    a,b=run_electrical_sequence(one),run_electrical_sequence(two)
    assert a.summary['status']==b.summary['status']=='completed'
    for x,y in zip(a.final_state.floating_gates,b.final_state.floating_gates):
        for key in ('P0','P1','P2'):
            np.testing.assert_allclose(getattr(x,key),getattr(y,key),rtol=0,atol=1e-12)


def test_timestep_refinement_at_fixed_waveform(experiment):
    refined=replace(experiment,sequence=replace(experiment.sequence,steps=tuple(
        replace(step,internal_dt_s=step.internal_dt_s/2) for step in experiment.sequence.steps)))
    a,b=run_electrical_sequence(experiment),run_electrical_sequence(refined)
    assert a.summary['status']==b.summary['status']=='completed'
    assert a.summary['final_time_s']==b.summary['final_time_s']
    # Synthetic regression tolerances for this fixture, not measurement errors.
    np.testing.assert_allclose(a.summary['read_delta_vfb_V'],b.summary['read_delta_vfb_V'],rtol=0,atol=1e-6)
    for x,y in zip(a.final_state.floating_gates,b.final_state.floating_gates):
        for key in ('P0','P1','P2'):
            np.testing.assert_allclose(getattr(x,key),getattr(y,key),rtol=0,atol=1e-6)


def test_failed_final_read_preserves_every_physical_step(experiment,monkeypatch):
    original=ThermalSimulator.relax_voltage
    calls=0
    def intercepted(self,*args,**kwargs):
        nonlocal calls
        if kwargs.get('dwell_time_s')==0:
            calls+=1
            if calls==len(experiment.sequence.steps)+1:raise RuntimeError('last read failure')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(ThermalSimulator,'relax_voltage',intercepted)
    result=run_electrical_sequence(experiment)
    assert result.summary['status']=='failed'
    assert result.summary['completed_step_count']==len(experiment.sequence.steps)
    assert result.summary['completed_read_count']==len(experiment.sequence.steps)
    assert result.to_dict()['failure']['step_index']==len(experiment.sequence.steps)-1


def test_solver_cannot_mutate_captured_metadata(experiment,monkeypatch):
    original=ThermalSimulator.relax_voltage
    before=experiment.to_json()
    def intercepted(self,state,*args,**kwargs):
        state.metadata['nested']['ids'].append('injected caller-state mutation')
        raise RuntimeError('deliberate mutation then failure')
    monkeypatch.setattr(ThermalSimulator,'relax_voltage',intercepted)
    result=run_electrical_sequence(experiment)
    assert result.summary['status']=='failed'
    assert experiment.to_json()==before
    assert result.final_state.metadata['nested']['ids']==['preparation']
