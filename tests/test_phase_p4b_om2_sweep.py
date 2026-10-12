# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""OM-2 sequence diagnostics; no real experimental qualification."""
from copy import deepcopy
from dataclasses import replace
import json
import numpy as np
import pytest
from examples.phase_p4b_om2_reference import build_om2_experiment, run_reference
from ncmemsim.om2_sweep import OM2SweepProtocol, OM2SweepExperiment, OM2SweepPrediction, run_om2_sweep, _crossing
from ncmemsim.thermal_reporting import _restore_state, _state_payload


@pytest.fixture(scope='module')
def result():
    return run_reference()


def test_sequence_is_continuous_with_light_only_during_holds(result):
    raw=result.to_dict()
    for mode in ('illuminated_writing','matched_dark'):
        events=raw[mode]
        assert len(events)==20
        assert events[0]['kind']=='lower_hold' and events[10]['kind']=='upper_hold'
        for a,b in zip(events,events[1:]):
            assert a['final_state']==b['initial_state']
        for event in events:
            assert event['light_enabled']==(mode=='illuminated_writing' and event['kind'].endswith('hold'))
        assert events[-1]['final_state']['time_s']==pytest.approx(3.8e-7)
    assert raw['illuminated_writing'][0]['initial_state']==raw['matched_dark'][0]['initial_state']
    assert result.summary['experimental_qualification'] is False
    assert result.summary['parameters_fitted'] is False


def test_dark_control_matches_existing_dark_solver(result):
    exp=build_om2_experiment();sim=exp.device_photo.spectral_context.resolution.create_simulator()
    state=_restore_state(json.loads(exp.device_photo.initial_state_json),sim.device)
    for event in result.to_dict()['matched_dark']:
        out=sim.relax_voltage(state,event['gate_voltage_V'],event['duration_s'],exp.protocol.internal_dt_s,occupancy_integrator='backward_euler')
        assert event['final_state']==_state_payload(out['state'],sim.device)
        assert event['capacitance_F_m2']==out['capacitance_F_m2']
        state=out['state']


@pytest.mark.parametrize('kwargs',[{'capture_efficiency':0},{'power_W':0}])
def test_zero_photo_conditions_recover_dark(kwargs):
    raw=run_om2_sweep(build_om2_experiment(**kwargs)).to_dict()
    for a,b in zip(raw['illuminated_writing'],raw['matched_dark']):
        assert a['final_state']==b['final_state']
        assert a['capacitance_F_m2']==b['capacitance_F_m2']


def test_roundtrip_does_not_replay_solver(result,monkeypatch):
    from ncmemsim.spectral_context import SpectralSimulator
    def fail(*a,**k):
        raise AssertionError('solver replayed')
    monkeypatch.setattr(SpectralSimulator,'relax_voltage',fail)
    assert OM2SweepPrediction.from_json(result.to_json())==result
    assert OM2SweepExperiment.from_json(build_om2_experiment().to_json()).contract_hash==build_om2_experiment().contract_hash


@pytest.mark.parametrize('field,value',[
    ('lower_voltage_V',2),('point_dwell_s',0),('internal_dt_s',1),
    ('reference_capacitance_F_m2',float('nan')),('writing_time_s',True),
    ('ascending_voltages_V',(-2.,0.,0.,2.)),('descending_voltages_V',(2.,0.,1.,-2.))])
def test_invalid_protocol_rejected(field,value):
    with pytest.raises(ValueError):
        replace(build_om2_experiment().protocol,**{field:value})


def test_binding_requires_same_hold_duration_and_positive_voltage():
    exp=build_om2_experiment()
    with pytest.raises(ValueError):
        OM2SweepExperiment(exp.device_photo,replace(exp.protocol,writing_time_s=2e-7))


def test_reference_outside_curve_does_not_extrapolate():
    exp=build_om2_experiment()
    result=run_om2_sweep(OM2SweepExperiment(exp.device_photo,replace(exp.protocol,reference_capacitance_F_m2=1e6)))
    assert result.summary['status']=='completed'
    assert result.summary['observable_status']=='not_assessable'
    assert result.summary['light_minus_dark_crossing_window_V'] is None


def test_nonmonotonic_and_plateau_crossings_are_rejected():
    def events(c):
        return [{'kind':'x','gate_voltage_V':float(i),'capacitance_F_m2':v} for i,v in enumerate(c)]
    assert _crossing(events([0.,2.,0.]),'x',1.)['status']=='ambiguous_multiple_crossings'
    assert _crossing(events([0.,1.,1.,2.]),'x',1.)['status']=='ambiguous_multiple_crossings'
    assert _crossing(events([0.,1.,2.]),'x',1.)['voltage_V']==1.
    assert _crossing(events([2.,0.]),'x',1.)['voltage_V']==.5


@pytest.mark.parametrize('change',['summary','charge','state_chain','time','dark_light','count','hash','extra','capacitance','vfb','runtime'])
def test_archive_tampering_rejected(result,change):
    raw=deepcopy(result.to_dict());event=raw['matched_dark'][1]
    if change=='summary':raw['summary']['experimental_qualification']=True
    if change=='charge':event['qfg_by_fg_C_m2'][0]+=1
    if change=='state_chain':event['initial_state']['time_s']+=1
    if change=='time':event['final_state']['time_s']+=1
    if change=='dark_light':event['light_enabled']=True
    if change=='count':raw['matched_dark'].pop()
    if change=='hash':raw['experiment_hash']='0'*64
    if change=='extra':raw['extra']=None
    if change=='capacitance':event['capacitance_F_m2']*=1.1
    if change=='vfb':event['vfb_V']+=1
    if change=='runtime':raw['runtime']['extra']='unexpected'
    with pytest.raises(ValueError):OM2SweepPrediction.from_dict(raw)


def test_partial_failure_keeps_completed_light_sequence(monkeypatch):
    from ncmemsim.spectral_context import SpectralSimulator
    original=SpectralSimulator.relax_voltage
    calls=[]
    def wrapped(self,*a,**k):
        calls.append(1)
        if len(calls)==23:raise RuntimeError('diagnostic dark failure')
        return original(self,*a,**k)
    monkeypatch.setattr(SpectralSimulator,'relax_voltage',wrapped)
    result=run_reference();raw=result.to_dict()
    assert raw['failure']['run']=='matched_dark' and raw['failure']['step_index']==2
    assert len(raw['illuminated_writing'])==20 and len(raw['matched_dark'])==2
    assert result.summary['light_minus_dark_crossing_window_V'] is None
    assert OM2SweepPrediction.from_json(result.to_json())==result


@pytest.mark.parametrize('n',[2,3])
def test_multi_fg_charge_and_states(n):
    raw=run_om2_sweep(build_om2_experiment(n)).to_dict()
    assert all(len(e['qfg_by_fg_C_m2'])==n for e in raw['matched_dark'])
    assert OM2SweepPrediction.from_dict(raw).summary['status']=='completed'


def test_smaller_integration_step_preserves_protocol_and_produces_close_curves(result):
    exp=build_om2_experiment()
    refined=run_om2_sweep(OM2SweepExperiment(exp.device_photo,replace(exp.protocol,internal_dt_s=exp.protocol.internal_dt_s/2)))
    base=result.to_dict();fine=refined.to_dict()
    for mode in ('illuminated_writing','matched_dark'):
        assert len(base[mode])==len(fine[mode])
        for a,b in zip(base[mode],fine[mode]):
            assert a['duration_s']==b['duration_s']
            assert a['gate_voltage_V']==b['gate_voltage_V']
            assert a['capacitance_F_m2']==pytest.approx(b['capacitance_F_m2'],rel=1e-4)


def test_crossing_window_is_signed_and_not_experimental_vfb(result):
    summary=result.summary
    for mode in ('illuminated_writing','matched_dark'):
        s=summary[mode]
        assert s['crossing_window_V']==s['descending_crossing']['voltage_V']-s['ascending_crossing']['voltage_V']
    assert summary['light_minus_dark_crossing_window_V']==summary['illuminated_writing']['crossing_window_V']-summary['matched_dark']['crossing_window_V']
    assert 'not physical Vfb' in summary['measurement_definition']
