# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest

from ncmemsim import DeviceBuilder,DeviceState,PhysicsModel,SimulationConfig,Simulator
from ncmemsim.materials import make_ge
from ncmemsim.optics import LightSource
from ncmemsim.photo import PhotoTransitionConfig,PhotoTransitionWeights,nanocrystal_number_density_m3
from ncmemsim.program_protocol import ProgramPulseReadProtocol
from ncmemsim.spectral_sources import SpectralEvidence,TabulatedSpectrum,DiscreteLineSpectrum
from ncmemsim.spectral_absorption import SpectralAbsorptionProfile
from ncmemsim.spectral_stack import SpectralStackLayer
from ncmemsim.temperature_context import ThermalContext
from ncmemsim.spectral_context import (SpectralSimulationContext,SpectralSimulator,SpectralPulseProtocol,
    build_spectral_simulation_context,run_spectral_program_pulse_read)


E=SpectralEvidence('N4 synthetic reference','tests','ASSUMED','m^-1',(),
    'declared grid','unknown','constant capture, diagnostic applicability')


def context(n=1,*,table=False,disabled=False,resolution=None,passive_alpha=0):
    if resolution is None:
        device=DeviceBuilder.v2(n,nc_material=make_ge(),nc_volume_fraction=.2,active_fraction=1)
        for fg in device.floating_gates():fg.grid_points=3
        resolution=ThermalContext.from_nominal(device,PhysicsModel.default(),SimulationConfig()).resolve(temperature_K=300)
    source=TabulatedSpectrum((1500,1750,2000),(1000,2000,1000),E,enabled=not disabled) if table else DiscreteLineSpectrum((1550,),(1e6,),E,not disabled)
    passive=tuple(SpectralStackLayer(SpectralAbsorptionProfile(x.name,source.wavelength_nm,
        tuple(passive_alpha for _ in source.wavelength_nm),x.thickness_nm*1e-9,1500,2000,E),'passive',
        'absorbing' if passive_alpha else 'assumed_transparent') for x in resolution.device.layers if x.role!='floating_gate')
    return build_spectral_simulation_context(resolution,source,direction='gate_to_substrate',passive_layers=passive,
        wavelength_min_nm=1500,wavelength_max_nm=2000,evidence=E)


def states_equal(a,b):
    return all(np.array_equal(getattr(x,k),getattr(y,k)) for x,y in zip(a.floating_gates,b.floating_gates) for k in ('P0','P1','P2'))


@pytest.mark.parametrize('n',[1,2,3])
def test_dark_identity_with_legacy_simulator(n):
    c=context(n);s=c.create_simulator();initial=DeviceState.empty_for_device(s.device)
    reference=Simulator(c.resolution.device,c.resolution.physics,c.resolution.simulation_config).relax_voltage(initial,0,1e-8,1e-9)
    actual=s.relax_voltage(initial,0,1e-8,1e-9)
    assert states_equal(reference['state'],actual['state']) and reference['qfg_C_m2']==actual['qfg_C_m2']
    assert actual['spectral_stack'] is None


def test_one_line_one_fg_preserves_legacy_pulse_states_and_rates():
    c=context();s=c.create_simulator();initial=DeviceState.empty_for_device(s.device)
    args={'photo_config':PhotoTransitionConfig(.1),'photo_weights':PhotoTransitionWeights(),'occupancy_integrator':'backward_euler'}
    spectral=s.relax_voltage(initial,0,1e-8,1e-9,c.optical_result.source,**args)
    legacy=c.resolution.create_simulator().relax_voltage(initial,0,1e-8,1e-9,LightSource.laser(1550,1e6),**args)
    assert spectral['photo_transition_rate_by_fg_s']==pytest.approx(legacy['photo_transition_rate_by_fg_s'],rel=1e-14)
    for a,b in zip(spectral['state'].floating_gates,legacy['state'].floating_gates):
        for key in ('P0','P1','P2'):np.testing.assert_allclose(getattr(a,key),getattr(b,key),rtol=1e-13,atol=1e-16)


@pytest.mark.parametrize('n',[1,2,3])
def test_broadband_rates_map_each_sequential_fg_flux(n):
    c=context(n,table=True,passive_alpha=1e6);s=c.create_simulator();initial=DeviceState.empty_for_device(s.device)
    out=s.relax_voltage(initial,0,0,light_source=c.optical_result.source,photo_config=PhotoTransitionConfig(.1),photo_weights=PhotoTransitionWeights())
    rows={r['layer_name']:r for r in c.optical_result.projection['layers']}
    for i,fg in enumerate(s.device.floating_gates()):
        generation=rows[fg.name]['absorption']['summary']['average_generation_rate_m3_s']
        density=nanocrystal_number_density_m3(fg.nc_diameter_nm,fg.nc_volume_fraction)
        assert out['photo_transition_rate_by_fg_s'][i]==pytest.approx(.1*generation/density)
        assert out['absorbed_photon_flux_by_fg_m2_s'][i]==rows[fg.name]['nc_absorbed_photon_flux_m2_s']
    assert np.all(np.isnan(out['optical_alpha_eff_by_fg_m_inv']))
    assert np.sum(out['absorbed_photon_flux_by_fg_m2_s'])==pytest.approx(c.optical_result.projection['summary']['fg_absorbed_photon_flux_m2_s'])


def test_pulse_workflow_dark_read_and_input_ownership():
    c=context(2,table=True);initial=DeviceState.empty_for_device(c.resolution.device);before=initial.copy()
    p=SpectralPulseProtocol(ProgramPulseReadProtocol(0,1e-8,0,1e-9),PhotoTransitionWeights())
    run=run_spectral_program_pulse_read(c,p,photo_config=PhotoTransitionConfig(.1),initial_state=initial)
    assert states_equal(initial,before) and states_equal(run['program']['state'],run['read']['state'])
    assert run['read']['spectral_stack'] is None
    assert np.all(run['read']['photo_transition_rate_by_fg_s']==0)
    np.testing.assert_allclose(run['absorbed_photon_fluence_by_fg_m2'],run['program']['absorbed_photon_flux_by_fg_m2_s']*1e-8)


def test_disabled_source_recovers_dark_occupancy():
    c=context(table=True,disabled=True);s=c.create_simulator();state=DeviceState.empty_for_device(s.device)
    a=s.relax_voltage(state,0,1e-8,1e-9)
    b=s.relax_voltage(state,0,1e-8,1e-9,c.optical_result.source,PhotoTransitionConfig(.1),PhotoTransitionWeights())
    assert states_equal(a['state'],b['state'])


@pytest.mark.parametrize('fault',['device','config','source','weights','budget','no_config'])
def test_drift_ambiguous_sources_and_unphysical_capture_rejected(fault):
    c=context();s=c.create_simulator();state=DeviceState.empty_for_device(s.device)
    source=c.optical_result.source;cfg=PhotoTransitionConfig(.1);weights=PhotoTransitionWeights()
    if fault=='device':s.device.temperature_K=301
    elif fault=='config':s.config=SimulationConfig(qfix_C_m2=1)
    elif fault=='source':source=replace(source,line_irradiance_W_m2=(1,))
    elif fault=='weights':weights=PhotoTransitionWeights(r01=float('inf'))
    elif fault=='budget':cfg=PhotoTransitionConfig(1);weights=PhotoTransitionWeights(r12=1,r10=1)
    else:cfg=None
    with pytest.raises(ValueError):s.relax_voltage(state,0,0,light_source=source,photo_config=cfg,photo_weights=weights)


def test_context_requires_complete_path_for_exact_device():
    c=context();other=context(2)
    with pytest.raises(ValueError):SpectralSimulationContext(other.resolution,c.optical_result)
    with pytest.raises(ValueError):SpectralSimulationContext(c.resolution,replace(c.optical_result,path=replace(c.optical_result.path,device_snapshot_json=None)))


def test_strict_context_and_protocol_roundtrip_without_solver(monkeypatch):
    c=context(table=True);p=SpectralPulseProtocol(ProgramPulseReadProtocol(0,1e-8,0,1e-9),PhotoTransitionWeights())
    def forbidden(*args,**kwargs):raise AssertionError('no solver replay')
    monkeypatch.setattr(Simulator,'relax_voltage',forbidden)
    assert SpectralSimulationContext.from_json(c.to_json())==c
    assert SpectralPulseProtocol.from_json(p.to_json())==p


def test_thermal_model_factory_retains_resolved_temperature():
    from examples.phase_m4_ge_temperature_reference import build_context
    resolution=build_context().resolve(temperature_K=350)
    c=context(resolution=resolution)
    assert c.resolution.temperature_K==350
    row=next(x for x in c.optical_result.path.layers if x.role=='floating_gate').profile.to_dict()['node_details'][0]
    point=resolution.optical_model('FG1').evaluate(resolution.device.get_layer('FG1').nc_material,1550)
    assert row['direct_gap_eV']==point.direct_gap_eV


@pytest.mark.parametrize('fault',['context_schema','protocol_read','protocol_weights','passive_omission'])
def test_invalid_context_protocol_or_factory_rejected(fault):
    c=context();p=SpectralPulseProtocol(ProgramPulseReadProtocol(0,1e-8),PhotoTransitionWeights())
    with pytest.raises(ValueError):
        if fault=='context_schema':
            raw=c.to_dict();raw['schema_version']='unknown';SpectralSimulationContext.from_dict(raw)
        elif fault=='protocol_read':
            raw=p.to_dict();raw['read_semantics']='illuminated';SpectralPulseProtocol.from_dict(raw)
        elif fault=='protocol_weights':
            raw=p.to_dict();raw['photo_weights']['extra']=1;SpectralPulseProtocol.from_dict(raw)
        else:build_spectral_simulation_context(c.resolution,c.optical_result.source,direction='gate_to_substrate',passive_layers=(),wavelength_min_nm=1500,wavelength_max_nm=2000,evidence=E)


def test_isolated_photo_pulse_converges_and_respects_charge_photon_budget(monkeypatch):
    import math
    from ncmemsim.constants import ELEMENTARY_CHARGE_C
    from ncmemsim.kinetics import OccupancyEngine,RateArrays
    def zero_electrical_rates(self,fg,x,*args,**kwargs):
        return RateArrays(*(np.zeros_like(x) for _ in range(7)))
    monkeypatch.setattr(OccupancyEngine,'rates',zero_electrical_rates)
    c=context(table=True);errors=[];duration=1e-6
    for steps in (32,64,128):
        p=SpectralPulseProtocol(ProgramPulseReadProtocol(0,duration,0,duration/steps),PhotoTransitionWeights())
        run=run_spectral_program_pulse_read(c,p,photo_config=PhotoTransitionConfig(.1))
        state=run['program']['state'].floating_gates[0]
        x=run['program']['photo_transition_rate_by_fg_s'][0]*duration
        expected=np.array([math.exp(-x),x*math.exp(-x),1-(1+x)*math.exp(-x)])
        actual=np.stack((state.P0,state.P1,state.P2),axis=1)
        errors.append(float(np.max(np.abs(actual-expected))))
        np.testing.assert_allclose(actual.sum(axis=1),1,rtol=0,atol=1e-14)
        assert actual.min()>=0
        stored_electrons=abs(run['program']['qfg_C_m2'])/ELEMENTARY_CHARGE_C
        assert stored_electrons <= .1*run['absorbed_photon_fluence_by_fg_m2'][0]*(1+1e-12)
    assert errors[2]<errors[1]<errors[0] and errors[-1]<2e-3


def test_changed_thermal_resolution_requires_new_optical_context():
    c=context()
    changed=replace(c.resolution,temperature_K=301)
    with pytest.raises(ValueError,match='exact resolved device'):SpectralSimulationContext(changed,c.optical_result)


def test_tampered_context_projection_rejected():
    c=context();raw=c.to_dict()
    raw['optical_result']['projection']['summary']['fg_absorbed_photon_flux_m2_s']*=2
    with pytest.raises(ValueError):SpectralSimulationContext.from_dict(raw)


def test_unrepresentable_combined_photo_weights_rejected():
    with pytest.raises(ValueError):SpectralPulseProtocol(ProgramPulseReadProtocol(0,1e-8),PhotoTransitionWeights(r12=1e308,r10=1e308))


def test_legacy_light_source_is_not_silently_accepted_by_spectral_adapter():
    c=context();s=c.create_simulator()
    with pytest.raises(ValueError):s.relax_voltage(DeviceState.empty_for_device(s.device),0,0,
        light_source=LightSource.laser(1550,1e6),photo_config=PhotoTransitionConfig(.1),photo_weights=PhotoTransitionWeights())
