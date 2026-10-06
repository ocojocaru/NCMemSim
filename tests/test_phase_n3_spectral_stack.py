# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import math
import pytest

from ncmemsim import DeviceBuilder
from ncmemsim.materials import make_ge
from ncmemsim.spectral_sources import SpectralEvidence, TabulatedSpectrum, DiscreteLineSpectrum
from ncmemsim.spectral_absorption import SpectralAbsorptionProfile, evaluate_spectral_absorption
from ncmemsim.spectral_stack import (SpectralStackLayer, SpectralStackPath, SpectralStackResult,
    bind_spectral_stack_path, evaluate_spectral_stack)


@pytest.fixture
def evidence():
    return SpectralEvidence('N3 analytic reference','tests','ASSUMED','m^-1',(),
        'explicit grid','unknown','single-pass diagnostic, not calibrated')


def entry(source,evidence,name,tau,role='floating_gate',thickness=1e-6,treatment='absorbing'):
    p=SpectralAbsorptionProfile(name,source.wavelength_nm,tuple(tau/1e-6 for _ in source.wavelength_nm),
        thickness,1000,2000,evidence)
    return SpectralStackLayer(p,role,treatment)


@pytest.mark.parametrize('kind',['table','lines','relative'])
@pytest.mark.parametrize('count',[1,2,3])
def test_analytic_stack_conservation_and_transmitted_handoff(evidence,kind,count):
    source=(DiscreteLineSpectrum((1550,),(1000,),evidence) if kind=='lines' else
        TabulatedSpectrum((1000,2000),(1,1),evidence,'relative_shape',1000) if kind=='relative' else
        TabulatedSpectrum((1000,2000),(1,1),evidence))
    layers=tuple(entry(source,evidence,f'FG{i}',.2*i) for i in range(1,count+1))
    raw=evaluate_spectral_stack(source,SpectralStackPath(layers,'substrate_to_gate',evidence)).projection
    incident=source.in_band_irradiance_W_m2
    for layer,row in zip(layers,raw['layers']):
        s=row['absorption']['summary'];tau=layer.profile.effective_alpha_m_inv[0]*1e-6
        assert s['incident_irradiance_W_m2']==pytest.approx(incident)
        assert s['absorbed_irradiance_W_m2']==pytest.approx(incident*(-math.expm1(-tau)))
        incident*=math.exp(-tau)
    total_tau=sum(.2*i for i in range(1,count+1))
    assert raw['summary']['transmitted_irradiance_W_m2']==pytest.approx(source.in_band_irradiance_W_m2*math.exp(-total_tau))
    assert raw['summary']['absorbed_photon_flux_m2_s']+raw['summary']['transmitted_photon_flux_m2_s']==pytest.approx(source.photon_flux_m2_s,rel=1e-14)


def test_direction_changes_layer_budgets_but_not_total_linear_transmission(evidence):
    source=DiscreteLineSpectrum((1550,),(1000,),evidence)
    layers=(entry(source,evidence,'A',.2),entry(source,evidence,'B',1))
    path=SpectralStackPath(layers,'substrate_to_gate',evidence)
    a=evaluate_spectral_stack(source,path).projection;b=evaluate_spectral_stack(source,replace(path,direction='gate_to_substrate')).projection
    assert [x['layer_name'] for x in b['layers']]==['B','A']
    assert a['summary']['transmitted_irradiance_W_m2']==pytest.approx(b['summary']['transmitted_irradiance_W_m2'])
    assert a['layers'][0]['absorption']['summary']['absorbed_irradiance_W_m2']>b['layers'][1]['absorption']['summary']['absorbed_irradiance_W_m2']


def test_passive_losses_not_counted_as_nc_photons(evidence):
    source=DiscreteLineSpectrum((1550,),(1000,),evidence)
    layers=(entry(source,evidence,'filter',1,'passive'),entry(source,evidence,'FG1',1))
    raw=evaluate_spectral_stack(source,SpectralStackPath(layers,'substrate_to_gate',evidence)).projection
    assert raw['layers'][0]['nc_absorbed_photon_flux_m2_s'] is None
    assert raw['summary']['passive_absorbed_irradiance_W_m2']==pytest.approx(1000*(1-math.exp(-1)))
    assert raw['summary']['fg_absorbed_irradiance_W_m2']==pytest.approx(1000*math.exp(-1)*(1-math.exp(-1)))


@pytest.mark.parametrize('limit',['transparent','zero_thickness','opaque','disabled','dark'])
def test_limits_and_single_layer_n2_identity(evidence,limit):
    source=DiscreteLineSpectrum((1550,),(0 if limit=='dark' else 1000,),evidence,limit!='disabled')
    first=entry(source,evidence,'first',1000 if limit=='opaque' else 0,'passive',
        thickness=0 if limit=='zero_thickness' else 1e-6,treatment='assumed_transparent' if limit=='transparent' else 'absorbing')
    second=entry(source,evidence,'FG1',.2)
    raw=evaluate_spectral_stack(source,SpectralStackPath((first,second),'substrate_to_gate',evidence)).projection
    expected=0 if limit in ('opaque','disabled','dark') else evaluate_spectral_absorption(source,second.profile).summary['absorbed_irradiance_W_m2']
    assert raw['summary']['fg_absorbed_irradiance_W_m2']==pytest.approx(expected)


@pytest.mark.parametrize('fault',['empty','list','duplicate','direction','grid','four_fg','role','treatment','transparent_alpha','transparent_status'])
def test_invalid_paths_fail(evidence,fault):
    source=DiscreteLineSpectrum((1550,),(1000,),evidence);layer=entry(source,evidence,'FG1',.2)
    with pytest.raises(ValueError):
        if fault=='empty':SpectralStackPath((),'substrate_to_gate',evidence)
        elif fault=='list':SpectralStackPath([layer],'substrate_to_gate',evidence)
        elif fault=='duplicate':SpectralStackPath((layer,layer),'substrate_to_gate',evidence)
        elif fault=='direction':SpectralStackPath((layer,),'automatic',evidence)
        elif fault=='grid':SpectralStackPath((layer,replace(layer,profile=replace(layer.profile,layer_name='other',wavelength_nm=(1600,)))),'substrate_to_gate',evidence)
        elif fault=='four_fg':SpectralStackPath(tuple(entry(source,evidence,str(i),.2) for i in range(4)),'substrate_to_gate',evidence)
        elif fault=='role':replace(layer,role='unknown')
        elif fault=='treatment':replace(layer,treatment='implicit')
        elif fault=='transparent_alpha':replace(layer,role='passive',treatment='assumed_transparent')
        else:SpectralStackLayer(replace(layer.profile,effective_alpha_m_inv=(0,),evidence=replace(evidence,status='MEASURED')),'passive','assumed_transparent')


def device_path(source,evidence):
    device=DeviceBuilder.v2(2,nc_material=make_ge())
    layers=tuple(SpectralStackLayer(SpectralAbsorptionProfile(x.name,source.wavelength_nm,
        tuple(1e6 if x.role=='floating_gate' else 0 for _ in source.wavelength_nm),x.thickness_nm*1e-9,1000,2000,evidence),
        'floating_gate' if x.role=='floating_gate' else 'passive', 'absorbing' if x.role=='floating_gate' else 'assumed_transparent') for x in device.layers)
    return device,layers


@pytest.mark.parametrize('fault',['omit','reverse','thickness','role'])
def test_bound_device_path_cannot_skip_or_relabel_layers(evidence,fault):
    source=DiscreteLineSpectrum((1550,),(1000,),evidence);device,layers=device_path(source,evidence)
    if fault=='omit':layers=layers[1:]
    elif fault=='reverse':layers=tuple(reversed(layers))
    elif fault=='thickness':layers=(replace(layers[0],profile=replace(layers[0].profile,thickness_m=1e-9)),)+layers[1:]
    else:layers=(replace(layers[0],role='floating_gate',treatment='absorbing'),)+layers[1:]
    with pytest.raises(ValueError):bind_spectral_stack_path(device,layers,direction='gate_to_substrate',evidence=evidence)


def test_bound_device_roundtrip_and_caller_ownership(evidence):
    source=TabulatedSpectrum((1000,1500,2000),(1,2,1),evidence)
    device,layers=device_path(source,evidence);before=deepcopy(device.to_dict())
    path=bind_spectral_stack_path(device,layers,direction='gate_to_substrate',evidence=evidence)
    result=evaluate_spectral_stack(source,path)
    assert SpectralStackResult.from_json(result.to_json())==result
    assert device.to_dict()==before
    device.name='caller mutation'
    assert 'caller mutation' not in result.to_json()


@pytest.mark.parametrize('fault',['handoff','total','role','direction','passive','extra'])
def test_strict_reader_recomputes_every_layer_and_total(evidence,fault):
    source=DiscreteLineSpectrum((1550,),(1000,),evidence)
    path=SpectralStackPath((entry(source,evidence,'A',.2),entry(source,evidence,'B',.5)),'substrate_to_gate',evidence)
    raw=evaluate_spectral_stack(source,path).to_dict()
    if fault=='handoff':raw['projection']['layers'][1]['absorption']['summary']['incident_irradiance_W_m2']=1000
    elif fault=='total':raw['projection']['summary']['absorbed_irradiance_W_m2']+=1
    elif fault=='role':raw['path']['layers'][0]['role']='passive'
    elif fault=='direction':raw['path']['direction']='gate_to_substrate'
    elif fault=='passive':raw['projection']['summary']['passive_absorbed_photon_flux_m2_s']=1
    else:raw['extra']=True
    with pytest.raises(ValueError):SpectralStackResult.from_dict(raw)


def test_restore_does_not_call_optical_models(evidence,monkeypatch):
    from ncmemsim.materials.optics.models import CompositeGeSnAbsorptionModel
    source=DiscreteLineSpectrum((1550,),(1000,),evidence)
    raw=evaluate_spectral_stack(source,SpectralStackPath((entry(source,evidence,'A',.2),),'substrate_to_gate',evidence)).to_json()
    def forbidden(*args):raise AssertionError('no optical replay')
    monkeypatch.setattr(CompositeGeSnAbsorptionModel,'evaluate',forbidden)
    assert SpectralStackResult.from_json(raw).source==source


def test_three_grid_stack_convergence_against_continuum_budgets(evidence):
    from ncmemsim.constants import PLANCK_J_S,LIGHT_SPEED_M_S
    exact_power=1000/math.e
    exact_photons=(-.5e6+3e6/math.e)*1e-9/(PLANCK_J_S*LIGHT_SPEED_M_S)
    errors=[]
    for n in (33,65,129):
        w=tuple(1000+1000*i/(n-1) for i in range(n))
        source=TabulatedSpectrum(w,tuple(1 for _ in w),evidence)
        layers=tuple(SpectralStackLayer(SpectralAbsorptionProfile(name,w,
            tuple((x-1000)*500 for x in w),1e-6,1000,2000,evidence),role)
            for name,role in [('filter','passive'),('FG1','floating_gate')])
        summary=evaluate_spectral_stack(source,SpectralStackPath(layers,'substrate_to_gate',evidence)).projection['summary']
        errors.append((abs(summary['absorbed_irradiance_W_m2']/exact_power-1),
            abs(summary['absorbed_photon_flux_m2_s']/exact_photons-1)))
    for j in (0,1):assert errors[2][j]<errors[1][j]<errors[0][j]
    assert max(errors[-1])<1e-5


def test_path_without_device_binding_does_not_claim_device_coverage(evidence):
    source=DiscreteLineSpectrum((1550,),(1000,),evidence)
    path=SpectralStackPath((entry(source,evidence,'explicit subset',.2),),'substrate_to_gate',evidence)
    assert path.to_dict()['device_snapshot'] is None
    with pytest.raises(ValueError):evaluate_spectral_stack(replace(source,wavelength_nm=(1600,)),path)


def test_bound_path_rejects_extra_nonlayer_snapshot_record(evidence):
    import json
    source=DiscreteLineSpectrum((1550,),(1000,),evidence);device,layers=device_path(source,evidence)
    raw=device.to_dict();raw['layers'].append(None)
    with pytest.raises(ValueError):SpectralStackPath(layers,'gate_to_substrate',evidence,json.dumps(raw))
