# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Q4 source linkage, light scheduling, matched dark controls and budgets."""
from dataclasses import replace, FrozenInstanceError
import numpy as np
import pytest
from examples.phase_q4_gradual_update_reference import build, restore
from ncmemsim.multilevel_contracts import ElectricalPulseStep
from ncmemsim.multilevel_execution import run_electrical_sequence
from ncmemsim.multilevel_optical import (OpticalSequenceExperiment, OpticalSequenceResult,
    MatchedOpticalSequenceResult, run_optical_sequence, run_matched_optical_sequence)
from ncmemsim.multilevel_updates import analyze_gradual_updates
from ncmemsim.spectral_context import SpectralSimulator, SpectralPulseProtocol, run_spectral_program_pulse_read
from ncmemsim.photo import PhotoTransitionConfig, PhotoTransitionWeights
from ncmemsim.program_protocol import ProgramPulseReadProtocol


@pytest.fixture(scope='module')
def case():
    a,b,o,r=build()
    return a,b,o,r,run_matched_optical_sequence(o)


def probabilities(state):
    return np.array([[fg.P0,fg.P1,fg.P2] for fg in state.floating_gates])


def test_matched_source_ownership_and_budget(case):
    optical=case[2];result=case[4];raw=result.to_dict()
    assert raw['dark']['experiment']==raw['light']['experiment']['electrical']
    assert raw['dark']['experiment']['initial_state']==raw['light']['experiment']['electrical']['initial_state']
    assert result.summary['matched_read_count']==5 and result.summary['matched_read_fraction']==1
    assert result.summary['light_minus_dark_delta_vfb_V'][0]==0
    assert result.summary['light_minus_dark_delta_vfb_V'][-1]<0
    light=OpticalSequenceResult.from_dict(raw['light'])
    b=light.summary['optical_budget'];assert b['scheduled_exposure_s']==4e-7
    assert b['optical_power_W']['incident_power_W']==pytest.approx(.01)
    assert b['optical_energy_J']['incident_energy_J']==pytest.approx(4e-9)
    f=b['optical_fluence_J_m2']
    assert f['incident_fluence_J_m2']==pytest.approx(f['absorbed_fluence_J_m2']+f['transmitted_fluence_J_m2'])
    assert f['absorbed_fluence_J_m2']==pytest.approx(f['fg_absorbed_fluence_J_m2']+f['passive_absorbed_fluence_J_m2'])
    for row in optical.spectral_context.optical_result.projection['layers']:
        if row['role']=='floating_gate':
            assert b['absorbed_photon_fluence_by_fg_m2'][row['layer_name']]==pytest.approx(
                row['absorption']['summary']['absorbed_photon_flux_m2_s']*4e-7)
    assert MatchedOpticalSequenceResult.from_json(result.to_json()).contract_hash==result.contract_hash
    assert OpticalSequenceResult.from_json(light.to_json()).contract_hash==light.contract_hash
    assert OpticalSequenceExperiment.from_json(optical.to_json()).contract_hash==optical.contract_hash
    with pytest.raises(FrozenInstanceError):optical.capture_efficiency=.5
    copy=result.to_dict();copy['light']['steps'].clear();assert len(result.to_dict()['light']['steps'])==4


@pytest.mark.parametrize('n_fgs',[1,2,3])
def test_direct_continuation_and_retained_single_pulse(n_fgs):
    electrical,_,optical,_=build(n_fgs)
    result=run_optical_sequence(optical);assert result.summary['status']=='completed'
    sim=optical.spectral_context.create_simulator();state=electrical.initial_state
    for index,step in enumerate(electrical.sequence.steps):
        out=sim.relax_voltage(state,step.gate_voltage_V,step.duration_s,step.internal_dt_s,
            optical.spectral_context.optical_result.source,PhotoTransitionConfig(.1),
            PhotoTransitionWeights(),occupancy_integrator='backward_euler')
        state=out['state']
        archived=result.to_dict()['steps'][index]['final_state']
        np.testing.assert_array_equal(probabilities(state),probabilities(
            __import__('ncmemsim.multilevel_execution',fromlist=['_state'])._state(archived,electrical.context.device)))
    step=electrical.sequence.steps[0]
    protocol=SpectralPulseProtocol(ProgramPulseReadProtocol(step.gate_voltage_V,step.duration_s,0.,step.internal_dt_s),
                                   PhotoTransitionWeights())
    retained=run_spectral_program_pulse_read(optical.spectral_context,protocol,
        photo_config=PhotoTransitionConfig(.1),initial_state=electrical.initial_state)
    np.testing.assert_array_equal(probabilities(retained['program']['state']),np.array([
        [fg['P0'],fg['P1'],fg['P2']] for fg in result.to_dict()['steps'][0]['final_state']['floating_gates']]))


@pytest.mark.parametrize('enabled,capture',[(False,.1),(True,0.)])
def test_disabled_or_zero_capture_matches_dark(enabled,capture):
    _,_,optical,_=build(enabled=enabled,capture=capture)
    paired=run_matched_optical_sequence(optical)
    assert paired.summary['light_minus_dark_delta_vfb_V']==pytest.approx([0.]*5,abs=1e-12)
    if not enabled:
        assert paired.to_dict()['light']['summary']['optical_budget']['optical_energy_J']['incident_energy_J']==0
    else:
        assert paired.to_dict()['light']['summary']['optical_budget']['optical_energy_J']['incident_energy_J']>0


def test_dark_idle_and_unscheduled_steps_do_not_inherit_light(case,monkeypatch):
    optical=case[2];e=optical.electrical
    idle=ElectricalPulseStep('idle','idle',0.,1e-8,1e-9)
    sequence=replace(e.sequence,steps=(e.sequence.steps[0],idle,*e.sequence.steps[1:]))
    request=replace(optical,electrical=replace(e,sequence=sequence),illuminated_step_ids=(e.sequence.steps[0].step_id,))
    seen=[];original=SpectralSimulator.relax_voltage
    def track(self,*args,**kwargs):
        seen.append((kwargs.get('dwell_time_s',args[2] if len(args)>2 else None),kwargs.get('light_source')))
        return original(self,*args,**kwargs)
    monkeypatch.setattr(SpectralSimulator,'relax_voltage',track)
    result=run_optical_sequence(request)
    assert result.summary['status']=='completed'
    assert sum(source is not None for _,source in seen)==1
    assert all(source is None for dwell,source in seen if dwell==0)
    assert result.summary['optical_budget']['scheduled_exposure_s']==1e-7
    assert result.summary['completed_step_count']==5
    analysis=analyze_gradual_updates(result,case[3],expected_direction='decreasing',minimum_excursion_V=1e-6)
    assert not analysis.summary['all_steps_identical'] and analysis.summary['observed_update_count']==5


@pytest.mark.parametrize('field,value',[
    ('capture_efficiency',True),('capture_efficiency',float('nan')),('capture_efficiency',1.1),
    ('capture_efficiency',-1),('illuminated_area_m2',0),('illuminated_area_m2',True),
    ('illuminated_area_m2',float('inf')),('illuminated_area_m2',1e308),
    ('transition_weights',[1.,1.,0.,0.]),('transition_weights',(1.,True,0.,0.)),
    ('transition_weights',(1.,float('inf'),0.,0.)),('transition_weights',(20.,20.,20.,20.)),
    ('illuminated_step_ids',()),('illuminated_step_ids',('absent',)),
    ('illuminated_step_ids',('loading-0','loading-0')),('illuminated_step_ids',['loading-0']),
    ('illuminated_step_ids',('loading-1','loading-0')),
])
def test_bad_optical_declarations(case,field,value):
    with pytest.raises(ValueError):replace(case[2],**{field:value})


def test_wrong_context_and_illuminated_idle_rejected(case):
    optical=case[2]
    from ncmemsim.temperature_context import ThermalContext
    different=ThermalContext.from_nominal(optical.electrical.context.device).resolve(temperature_K=301)
    with pytest.raises(ValueError):replace(optical,spectral_context=replace(optical.spectral_context,resolution=different))
    e=optical.electrical;idle=ElectricalPulseStep('idle','idle',0.,1e-7,1e-9)
    e=replace(e,sequence=replace(e.sequence,steps=(idle,)))
    with pytest.raises(ValueError):replace(optical,electrical=e,illuminated_step_ids=('idle',))


@pytest.mark.parametrize('stage',['setup','initial_read','step','read'])
def test_failure_prefix_and_completed_optical_budget(case,monkeypatch,stage):
    optical=case[2]
    original=SpectralSimulator.relax_voltage
    if stage=='setup':
        from ncmemsim.spectral_context import SpectralSimulationContext
        def fail(*args,**kwargs):raise RuntimeError('injected setup failure')
        monkeypatch.setattr(SpectralSimulationContext,'create_simulator',fail)
    else:
        reads=0
        def fail(self,*args,**kwargs):
            nonlocal reads
            dwell=kwargs.get('dwell_time_s',args[2] if len(args)>2 else None)
            if dwell==0:reads+=1
            if (stage=='initial_read' and reads==1) or (stage=='step' and dwell>0) or (stage=='read' and reads==2):
                raise RuntimeError('injected '+stage+' failure')
            return original(self,*args,**kwargs)
        monkeypatch.setattr(SpectralSimulator,'relax_voltage',fail)
    result=run_optical_sequence(optical);raw=result.to_dict()
    assert raw['failure']['stage']==stage and result.summary['status']=='failed'
    count=int(stage=='read')
    assert result.summary['completed_step_count']==count
    assert result.summary['optical_budget']['scheduled_exposure_s']==count*1e-7
    assert result.final_state.time_s==count*1e-7
    assert OpticalSequenceResult.from_json(result.to_json()).contract_hash==result.contract_hash
    analysis=analyze_gradual_updates(result,case[3],expected_direction='decreasing',minimum_excursion_V=1e-6)
    assert analysis.summary['reason']=='incomplete_sequence' and analysis.summary['linearity_deviation'] is None


def test_half_timestep_same_waveform(case):
    _,_,fine,_=build(internal_dt_s=5e-10)
    fine_result=run_optical_sequence(fine)
    assert fine_result.summary['status']=='completed'
    np.testing.assert_allclose(fine_result.summary['read_delta_vfb_V'],
        case[4].to_dict()['light']['summary']['read_delta_vfb_V'],rtol=0,atol=1e-5)
    assert fine_result.summary['optical_budget']==case[4].to_dict()['light']['summary']['optical_budget']


@pytest.mark.parametrize('kind',['experiment','result','matched'])
def test_schema_tamper_and_duplicate_keys(case,kind):
    cls,obj={'experiment':(OpticalSequenceExperiment,case[2]),
        'result':(OpticalSequenceResult,OpticalSequenceResult.from_dict(case[4].to_dict()['light'])),
        'matched':(MatchedOpticalSequenceResult,case[4])}[kind]
    raw=obj.to_dict();raw['unexpected']=1
    with pytest.raises(ValueError):cls.from_dict(raw)
    with pytest.raises(ValueError):cls.from_json('{"x":1,"x":2}')
    with pytest.raises(ValueError):cls.from_json('{"x":Infinity}')
    raw=obj.to_dict()
    if kind=='experiment':raw['reference_plane']='lamp'
    elif kind=='result':raw['summary']['optical_budget']['optical_energy_J']['incident_energy_J']*=2
    else:raw['summary']['light_minus_dark_delta_vfb_V'][-1]=0
    with pytest.raises(ValueError):cls.from_dict(raw)


def test_matched_dark_request_must_be_identical(case):
    raw=case[4].to_dict()
    wrong=replace(case[0],name='different matched request')
    raw['dark']=run_electrical_sequence(wrong).to_dict()
    with pytest.raises(ValueError):MatchedOpticalSequenceResult.from_dict(raw)


def test_no_integration_or_material_sampling_on_restore(case,monkeypatch):
    from ncmemsim.temperature_context import ResolvedThermalContext
    import ncmemsim.spectral_absorption as absorption
    def forbidden(*args,**kwargs):raise AssertionError('workflow replay')
    monkeypatch.setattr(SpectralSimulator,'relax_voltage',forbidden)
    monkeypatch.setattr(ResolvedThermalContext,'create_simulator',forbidden)
    monkeypatch.setattr(absorption,'evaluate_floating_gate_spectrum',forbidden)
    monkeypatch.setattr(np.random,'default_rng',forbidden)
    assert MatchedOpticalSequenceResult.from_json(case[4].to_json()).to_dict()==case[4].to_dict()


def test_light_failure_does_not_stop_matched_dark_control(case,monkeypatch):
    original=SpectralSimulator.relax_voltage
    physical=0
    def fail(self,*args,**kwargs):
        nonlocal physical
        if kwargs.get('dwell_time_s',0)>0:
            physical+=1
            if physical==3:raise RuntimeError('third light step intentionally failed')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(SpectralSimulator,'relax_voltage',fail)
    result=run_matched_optical_sequence(case[2]);s=result.summary
    assert s['light_status']=='failed' and s['dark_status']=='completed'
    assert s['matched_read_count']==3 and s['matched_read_fraction']==.6
    assert result.to_dict()['light']['summary']['optical_budget']['scheduled_exposure_s']==2e-7
    assert MatchedOpticalSequenceResult.from_json(result.to_json()).contract_hash==result.contract_hash


def test_failed_read_retains_original_physical_state(case,monkeypatch):
    original=SpectralSimulator.relax_voltage
    reads=0
    def disturb(self,*args,**kwargs):
        nonlocal reads
        out=original(self,*args,**kwargs)
        if kwargs.get('dwell_time_s',args[2] if len(args)>2 else None)==0:
            reads+=1
            if reads==2:
                gate=out['state'].floating_gates[0]
                gate.P0[:]-=.01;gate.P1[:]+=.01
        return out
    monkeypatch.setattr(SpectralSimulator,'relax_voltage',disturb)
    result=run_optical_sequence(case[2]);raw=result.to_dict()
    assert raw['failure']['stage']=='read' and raw['steps'][0]['read'] is None
    assert raw['steps'][0]['final_state']==case[4].to_dict()['light']['steps'][0]['final_state']
    assert result.summary['completed_read_count']==1


def test_source_change_and_read_observation_tamper_rejected(case):
    raw=case[4].to_dict()['light'];raw['experiment']['spectral_context']['optical_result']['source']['line_irradiance_W_m2'][0]*=2
    with pytest.raises(ValueError):OpticalSequenceResult.from_dict(raw)
    raw=case[4].to_dict()['light'];raw['steps'][0]['read']['delta_vfb_V']+=.01
    with pytest.raises(ValueError):OpticalSequenceResult.from_dict(raw)
