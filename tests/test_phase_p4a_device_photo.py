# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""P4A numerical fixtures only; no experimental device qualification."""
from dataclasses import replace,FrozenInstanceError
from copy import deepcopy
import json,math
import numpy as np
import pytest
from examples.phase_p4a_device_photo_reference import build_experiment,run_reference
from ncmemsim.device_photo_experiment import SamplePlaneIllumination,DevicePhotoExperiment,DevicePhotoPrediction,predict_device_photo_experiment
from ncmemsim.spectral_sources import SpectralEvidence
from ncmemsim.spectral_context import SpectralPulseProtocol
from ncmemsim.program_protocol import ProgramPulseReadProtocol
from ncmemsim.photo import PhotoTransitionWeights
from ncmemsim.thermal_reporting import _restore_state
from ncmemsim.hashing import canonical_hash


@pytest.fixture(scope='module')
def prediction():return run_reference()


def test_sample_plane_power_area_photons_are_explicit():
    from ncmemsim.constants import PLANCK_J_S,LIGHT_SPEED_M_S
    exp=build_experiment();light=exp.illumination
    assert light.summary['irradiance_W_m2']==pytest.approx(1e6)
    expected=1e6*(1550e-9)/(PLANCK_J_S*LIGHT_SPEED_M_S)
    assert light.summary['incident_photon_flux_m2_s']==pytest.approx(expected)
    assert light.summary['incident_photon_fluence_m2']==pytest.approx(expected*1e-7)
    assert SamplePlaneIllumination.from_json(light.to_json())==light
    raw=light.to_dict();raw['power_reference']='nominal_laser'
    with pytest.raises(ValueError):SamplePlaneIllumination.from_dict(raw)


def test_completed_pipeline_and_matched_dark_are_not_calibration(prediction):
    s=prediction.summary
    assert s['status']=='completed' and s['scientific_status']=='synthetic_device_photo_diagnostic'
    assert s['experimental_qualification'] is False and s['parameters_fitted'] is False
    assert s['matched_dark']['absorbed_photon_flux_by_fg_m2_s']==[0.]
    assert s['matched_dark']['photo_transition_rate_by_fg_s']==[0.]
    assert s['illuminated']['average_generation_rate_by_fg_m3_s'][0]>0
    assert s['contrast']['light_minus_dark_delta_vfb_V']!=0
    assert OpticalReadAudit(prediction)<=1e-12
    assert DevicePhotoPrediction.from_json(prediction.to_json())==prediction


def OpticalReadAudit(prediction):
    return max(prediction.summary[k]['read_max_probability_change'] for k in ('illuminated','matched_dark'))


def test_original_program_and_read_states_are_retained(prediction):
    raw=prediction.to_dict()
    for key in ('illuminated_run','dark_run'):
        states=raw[key]['observations'];a=states['programmed_state'];b=states['read_state']
        assert a['time_s']==b['time_s']==raw['experiment']['initial_state']['time_s']+1e-7
        for ga,gb in zip(a['floating_gates'],b['floating_gates'],strict=True):
            for name in ('P0','P1','P2'):assert np.max(abs(np.asarray(ga[name])-np.asarray(gb[name])))<=1e-12


def test_device_area_is_only_total_charge_conversion(prediction):
    area=prediction.to_dict()['experiment']['device_area_m2'];s=prediction.summary
    for key in ('illuminated','matched_dark'):
        assert np.allclose(s[key]['delta_qfg_total_C'],np.asarray(s[key]['delta_qfg_C_m2'])*area,rtol=1e-14,atol=0)
    assert np.allclose(s['contrast']['light_minus_dark_delta_qfg_total_C'],np.asarray(s['contrast']['light_minus_dark_delta_qfg_C_m2'])*area,rtol=1e-14,atol=0)


def test_dark_control_recovers_existing_dark_simulator(prediction):
    exp=build_experiment();context=exp.spectral_context;state=_restore_state(json.loads(exp.initial_state_json),context.resolution.device)
    simulator=context.resolution.create_simulator();p=exp.protocol.electrical_protocol
    program=simulator.relax_voltage(state,p.program_voltage_V,p.programming_time_s,p.program_internal_dt_s,occupancy_integrator='backward_euler')
    stored=prediction.to_dict()['dark_run']['observations']['programmed_state']['floating_gates']
    for expected,actual in zip(program['state'].floating_gates,stored,strict=True):
        for key in ('P0','P1','P2'):assert np.array_equal(getattr(expected,key),actual[key])


@pytest.mark.parametrize('case',['zero_capture','zero_power'])
def test_zero_photo_conditions_recover_dark(case):
    exp=build_experiment(capture_efficiency=0) if case=='zero_capture' else build_experiment(power_W=0)
    s=predict_device_photo_experiment(exp).summary
    assert s['status']=='completed'
    assert abs(s['contrast']['light_minus_dark_delta_vfb_V'])<1e-14
    assert np.allclose(s['contrast']['light_minus_dark_delta_qfg_C_m2'],0,rtol=0,atol=1e-20)


@pytest.mark.parametrize('n',[2,3])
def test_multi_fg_bookkeeping_and_energy_balance(n):
    result=predict_device_photo_experiment(build_experiment(n));s=result.summary
    assert s['status']=='completed'
    assert len(s['illuminated']['delta_qfg_C_m2'])==n
    assert len(s['illuminated']['absorbed_photon_flux_by_fg_m2_s'])==n
    optical=s['illuminated']['optical_summary']
    for suffix in ('irradiance_W_m2','photon_flux_m2_s'):
        assert optical['incident_'+suffix]==pytest.approx(optical['absorbed_'+suffix]+optical['transmitted_'+suffix],rel=1e-12)
    assert DevicePhotoPrediction.from_json(result.to_json())==result


@pytest.mark.parametrize('field,value',[('uniform_spot_area_m2',0),('uniform_spot_area_m2',True),('sample_power_W',-.01),('sample_power_W',float('nan')),('exposure_time_s',0),('wavelength_nm',0)])
def test_invalid_delivery_rejected(field,value):
    light=build_experiment().illumination
    with pytest.raises(ValueError):replace(light,**{field:value})


@pytest.mark.parametrize('fault',['area','exposure','source','capture','timestep','integrator','initial'])
def test_incomplete_or_inconsistent_experiment_rejected(fault):
    exp=build_experiment()
    with pytest.raises(ValueError):
        if fault=='area':replace(exp,device_area_m2=1e-7)
        elif fault=='exposure':replace(exp,illumination=replace(exp.illumination,exposure_time_s=2e-7))
        elif fault=='source':replace(exp,illumination=replace(exp.illumination,sample_power_W=.02))
        elif fault=='capture':replace(exp,capture_efficiency=2.)
        elif fault=='timestep':replace(exp,protocol=SpectralPulseProtocol(ProgramPulseReadProtocol(2,1e-7,0),PhotoTransitionWeights()))
        elif fault=='integrator':replace(exp,protocol=replace(exp.protocol,occupancy_integrator='explicit_euler'))
        else:replace(exp,initial_state_json='{}')


def test_failed_dark_control_keeps_completed_light_evidence(monkeypatch):
    import ncmemsim.device_photo_experiment as module
    exp=build_experiment();run=module.run_spectral_program_pulse_read;calls=[]
    def conditional(context,*args,**kwargs):
        calls.append(context.optical_result.source.enabled)
        if not context.optical_result.source.enabled:raise RuntimeError('injected dark control failure')
        return run(context,*args,**kwargs)
    monkeypatch.setattr(module,'run_spectral_program_pulse_read',conditional)
    result=module.predict_device_photo_experiment(exp)
    assert result.summary['status']=='prediction_failed'
    assert result.to_dict()['illuminated_run'] is not None and result.to_dict()['dark_run'] is None
    assert result.to_dict()['failure']['stage']=='matched_dark_control'
    assert result.summary['contrast'] is None
    assert DevicePhotoPrediction.from_json(result.to_json())==result


@pytest.mark.parametrize('fault',['summary','state','read','power','area','flux','runtime','dark_light','extra'])
def test_source_or_projection_tampering_rejected(prediction,fault):
    raw=deepcopy(prediction.to_dict())
    if fault=='summary':raw['summary']['experimental_qualification']=True
    elif fault=='state':raw['illuminated_run']['observations']['programmed_state']['floating_gates'][0]['P0'][0]=.5
    elif fault=='read':raw['dark_run']['observations']['read_state']['time_s']+=1
    elif fault=='power':raw['experiment']['illumination']['sample_power_W']*=2
    elif fault=='area':raw['experiment']['device_area_m2']*=2
    elif fault=='flux':raw['illuminated_run']['observations']['absorbed_photon_flux_by_fg_m2_s'][0]*=2
    elif fault=='runtime':raw['runtime']['unreviewed']='yes'
    elif fault=='dark_light':raw['dark_run']['context']=raw['illuminated_run']['context']
    else:raw['unreviewed']=True
    with pytest.raises(ValueError):DevicePhotoPrediction.from_dict(raw)


def test_restore_without_optical_simulator_or_rng_replay(prediction,monkeypatch):
    from ncmemsim.simulator import Simulator
    from ncmemsim.materials.optics.models import CompositeGeSnAbsorptionModel
    def forbidden(*args,**kwargs):raise AssertionError('no replay')
    monkeypatch.setattr(Simulator,'relax_voltage',forbidden)
    monkeypatch.setattr(CompositeGeSnAbsorptionModel,'evaluate',forbidden)
    monkeypatch.setattr(np.random,'default_rng',forbidden)
    assert DevicePhotoPrediction.from_json(prediction.to_json())==prediction


def test_strict_json_and_owned_initial_state(prediction):
    with pytest.raises(ValueError):DevicePhotoPrediction.from_json(prediction.to_json().replace('{','{"summary":null,',1))
    with pytest.raises(ValueError):DevicePhotoPrediction.from_json(prediction.to_json().replace('300.0','NaN',1))
    exp=build_experiment()
    with pytest.raises(FrozenInstanceError):exp.capture_efficiency=.2
    raw=exp.to_dict();raw['initial_state']['floating_gates'][0]['P0'][0]=0
    assert exp.to_dict()['initial_state']['floating_gates'][0]['P0'][0]==1


def test_read_state_change_above_roundoff_is_rejected(prediction):
    raw=deepcopy(prediction.to_dict());gate=raw['dark_run']['observations']['read_state']['floating_gates'][0]
    gate['P0'][0]-=1e-6;gate['P1'][0]+=1e-6
    with pytest.raises(ValueError,match='roundoff tolerance'):DevicePhotoPrediction.from_dict(raw)


def test_sample_plane_conversion_rejects_positive_power_rounded_to_zero():
    light=build_experiment().illumination
    with pytest.raises(ValueError):replace(light,sample_power_W=5e-324,uniform_spot_area_m2=1e308)
