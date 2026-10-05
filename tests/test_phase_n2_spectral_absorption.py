# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Independent Beer-Lambert limits, spectral convergence and source-linked readers."""
from copy import deepcopy
from dataclasses import replace
import math
from types import SimpleNamespace
import pytest

from ncmemsim import DeviceBuilder
from ncmemsim.constants import LIGHT_SPEED_M_S, PLANCK_J_S
from ncmemsim.materials import make_ge
from ncmemsim.materials.optics.models import CompositeGeSnAbsorptionModel
from ncmemsim.optics import LightSource, evaluate_floating_gate_optical_absorption
from ncmemsim.spectral_sources import SpectralEvidence, TabulatedSpectrum, DiscreteLineSpectrum
from ncmemsim.spectral_absorption import (SpectralAbsorptionProfile, SpectralAbsorptionResult,
    evaluate_spectral_absorption, evaluate_floating_gate_spectrum)


@pytest.fixture
def evidence():
    return SpectralEvidence('analytical reference','N2 test','ASSUMED','m^-1',(),
        'explicit test grid','unknown','diagnostic applicability, not qualification')


def profile(source,evidence,alpha=1e6,thickness=1e-6):
    return SpectralAbsorptionProfile('FG1',source.wavelength_nm,tuple(alpha for _ in source.wavelength_nm),
        thickness,1000,2000,evidence)


@pytest.mark.parametrize('cls,args',[(TabulatedSpectrum,((1000,2000),(1,1))),
    (DiscreteLineSpectrum,((1550,),(1000,)))])
def test_constant_alpha_power_photon_and_generation_analytic(evidence,cls,args):
    source=cls(*args,evidence); result=evaluate_spectral_absorption(source,profile(source,evidence))
    s=result.summary; f=1-math.exp(-1)
    assert s['absorbed_irradiance_W_m2']==pytest.approx(source.in_band_irradiance_W_m2*f)
    assert s['absorbed_photon_flux_m2_s']==pytest.approx(source.photon_flux_m2_s*f)
    assert s['transmitted_irradiance_W_m2']==pytest.approx(source.in_band_irradiance_W_m2*math.exp(-1))
    assert s['average_generation_rate_m3_s']==pytest.approx(s['absorbed_photon_flux_m2_s']/1e-6)
    assert s['absorbed_photon_flux_m2_s']+s['transmitted_photon_flux_m2_s']==pytest.approx(s['incident_photon_flux_m2_s'],rel=1e-14)


@pytest.mark.parametrize('alpha,thickness',[(0,1e-6),(1e6,0),(1e300,1e300)])
def test_transparent_zero_thickness_and_opaque_limits(evidence,alpha,thickness):
    source=DiscreteLineSpectrum((1550,),(1000,),evidence)
    result=evaluate_spectral_absorption(source,profile(source,evidence,alpha,thickness)).summary
    expected=1000 if alpha and thickness else 0
    assert result['absorbed_irradiance_W_m2']==expected
    assert result['transmitted_irradiance_W_m2']==1000-expected


def test_thin_layer_absorption_and_opaque_transmission_are_not_cancelled(evidence):
    source=DiscreteLineSpectrum((1550,),(1,),evidence)
    thin=evaluate_spectral_absorption(source,profile(source,evidence,1,1e-20)).summary
    assert thin['absorbed_irradiance_W_m2']==pytest.approx(1e-20,rel=1e-15,abs=0)
    thick=evaluate_spectral_absorption(source,profile(source,evidence,40,1)).summary
    assert thick['transmitted_irradiance_W_m2']==pytest.approx(math.exp(-40),rel=1e-15,abs=0)


@pytest.mark.parametrize('disabled',[False,True])
def test_dark_and_disabled_inputs_have_zero_balances(evidence,disabled):
    source=TabulatedSpectrum((1000,2000),(1,1) if disabled else (0,0),evidence,enabled=not disabled)
    result=evaluate_spectral_absorption(source,profile(source,evidence)).summary
    for key in ('incident_irradiance_W_m2','absorbed_irradiance_W_m2','transmitted_photon_flux_m2_s',
                'average_generation_rate_m3_s','power_balance_residual_W_m2','photon_balance_residual_m2_s'):
        assert result[key]==0


def test_three_grid_convergence_against_independent_continuum_integrals(evidence):
    errors=[]
    exact_power=1000/math.e
    exact_photons=(-.5e6+3e6/math.e)*1e-9/(PLANCK_J_S*LIGHT_SPEED_M_S)
    for n in (33,65,129):
        w=tuple(1000+1000*i/(n-1) for i in range(n))
        source=TabulatedSpectrum(w,tuple(1 for _ in w),evidence)
        p=SpectralAbsorptionProfile('analytic',w,tuple((x-1000)*1000 for x in w),1e-6,1000,2000,evidence)
        result=evaluate_spectral_absorption(source,p).summary
        errors.append((abs(result['absorbed_irradiance_W_m2']/exact_power-1),
            abs(result['absorbed_photon_flux_m2_s']/exact_photons-1)))
    assert errors[2][0]<errors[1][0]<errors[0][0]
    assert errors[2][1]<errors[1][1]<errors[0][1]
    assert max(errors[-1])<1e-5


@pytest.mark.parametrize('fault', ['negative','nan','bool','length','order','domain','thickness','details','evidence'])
def test_invalid_profile_and_domain_rejected(evidence,fault):
    source=DiscreteLineSpectrum((1550,),(1000,),evidence);p=profile(source,evidence)
    mutations={'negative':{'effective_alpha_m_inv':(-1,)},'nan':{'effective_alpha_m_inv':(float('nan'),)},
        'bool':{'effective_alpha_m_inv':(True,)},'length':{'effective_alpha_m_inv':()},
        'order':{'wavelength_nm':(1550,1550),'effective_alpha_m_inv':(1,1)},
        'domain':{'wavelength_min_nm':1600},'thickness':{'thickness_m':-1},
        'details':{'node_details_json':('{"x":NaN}',)},'evidence':{'evidence':None}}
    with pytest.raises(ValueError):replace(p,**mutations[fault])


def test_grid_mismatch_rejected_without_interpolation(evidence):
    source=DiscreteLineSpectrum((1550,),(1000,),evidence)
    with pytest.raises(ValueError):evaluate_spectral_absorption(source,replace(profile(source,evidence),wavelength_nm=(1600,)))


@pytest.fixture
def fg():
    return DeviceBuilder.v2(1,nc_material=make_ge(),nc_volume_fraction=.2,fg_thickness_nm=6).floating_gates()[0]


def evaluate(source,fg,evidence,model=None):
    return evaluate_floating_gate_spectrum(source,fg,optical_model=model or CompositeGeSnAbsorptionModel(),
        model_identity='explicit compact model test',wavelength_min_nm=1500,wavelength_max_nm=2000,evidence=evidence)


def test_single_line_recovers_legacy_fg_evaluator_and_keeps_input_owned(evidence,fg):
    source=DiscreteLineSpectrum((1550,),(1000,),evidence);before=deepcopy(fg.to_dict())
    result=evaluate(source,fg,evidence)
    legacy=evaluate_floating_gate_optical_absorption(LightSource.laser(1550,1000),fg)
    assert result.summary['absorbed_photon_flux_m2_s']==pytest.approx(legacy.absorbed_photon_flux_m2_s,rel=1e-14)
    assert result.summary['average_generation_rate_m3_s']==pytest.approx(legacy.average_generation_rate_m3_s,rel=1e-14)
    assert result.profile.effective_alpha_m_inv[0]==legacy.effective_absorption_coefficient_m_inv
    details=result.profile.to_dict()['node_details'][0]
    assert sum(details['channels'].values())==pytest.approx(details['nc_alpha_m_inv'])
    assert details['provenance'] and details['layer_snapshot']==before
    assert fg.to_dict()==before


def test_domain_failure_precedes_even_disabled_model_evaluation(evidence,fg):
    class Forbidden:
        def evaluate(self,*args):raise AssertionError('must not invoke outside domain')
    source=DiscreteLineSpectrum((1499,),(1000,),evidence,False)
    with pytest.raises(ValueError,match='domain'):evaluate(source,fg,evidence,Forbidden())


@pytest.mark.parametrize('fault',['negative','wrong_wavelength','inconsistent_channels','failure'])
def test_model_failures_are_explicit_and_wavelength_linked(evidence,fg,fault):
    class Model:
        def evaluate(self,material,w):
            if fault=='failure':raise ValueError('unsupported composition')
            return SimpleNamespace(wavelength_nm=w+1 if fault=='wrong_wavelength' else w,
                absorption_coefficient_m_inv=-1 if fault=='negative' else 1,
                alpha_direct_m_inv=1,alpha_indirect_m_inv=1,alpha_urbach_m_inv=1)
    with pytest.raises(ValueError,match='1550 nm'):evaluate(DiscreteLineSpectrum((1550,),(1000,),evidence),fg,evidence,Model())


def test_adapter_copies_mutating_model_and_material(evidence,fg):
    class Model:
        calls=0
        def evaluate(self,material,w):
            self.calls+=1
            material.metadata['owned mutation']=True
            return SimpleNamespace(wavelength_nm=w,absorption_coefficient_m_inv=1)
    model=Model();before=deepcopy(fg.to_dict());metadata=deepcopy(fg.nc_material.metadata)
    evaluate(DiscreteLineSpectrum((1550,),(1000,),evidence),fg,evidence,model)
    assert model.calls==0 and fg.to_dict()==before and fg.nc_material.metadata==metadata


def test_strict_roundtrip_rebuilds_projection_without_optical_replay(evidence,fg,monkeypatch):
    result=evaluate(TabulatedSpectrum((1500,1750,2000),(1,2,1),evidence),fg,evidence)
    def forbidden(*args):raise AssertionError('reader must not evaluate optics')
    monkeypatch.setattr(CompositeGeSnAbsorptionModel,'evaluate',forbidden)
    restored=SpectralAbsorptionResult.from_json(result.to_json())
    assert restored==result and restored.contract_hash==result.contract_hash


@pytest.mark.parametrize('fault',['summary','profile_alpha','units','nested_source','extra','schema'])
def test_inconsistent_or_unknown_archives_rejected(evidence,fault):
    source=DiscreteLineSpectrum((1550,),(1000,),evidence)
    raw=evaluate_spectral_absorption(source,profile(source,evidence)).to_dict()
    if fault=='summary':raw['summary']['absorbed_irradiance_W_m2']+=1
    elif fault=='profile_alpha':raw['profile']['effective_alpha_m_inv'][0]*=2
    elif fault=='units':raw['profile']['alpha_unit']='cm^-1'
    elif fault=='nested_source':raw['source']['unreviewed']=True
    elif fault=='extra':raw['extra']=True
    else:raw['schema_version']='unknown'
    with pytest.raises(ValueError):SpectralAbsorptionResult.from_dict(raw)


@pytest.mark.parametrize('fault',['effective_alpha','channel','layer','wavelength'])
def test_node_details_must_match_profile_and_layer(evidence,fg,fault):
    raw=evaluate(DiscreteLineSpectrum((1550,),(1000,),evidence),fg,evidence).to_dict()
    row=raw['profile']['node_details'][0]
    if fault=='effective_alpha':row['effective_alpha_m_inv']*=2
    elif fault=='channel':row['channels']['alpha_direct_m_inv']+=100
    elif fault=='layer':row['layer_snapshot']['name']='other FG'
    else:row['wavelength_nm']=1600
    with pytest.raises(ValueError):SpectralAbsorptionResult.from_dict(raw)


def test_resolved_thermal_model_composes_without_new_temperature_owner(evidence):
    from examples.phase_m4_ge_temperature_reference import build_context
    resolution=build_context().resolve(temperature_K=350)
    fg=resolution.device.get_layer('FG1')
    source=DiscreteLineSpectrum((1550,),(1000,),evidence)
    result=evaluate(source,fg,evidence,resolution.optical_model('FG1'))
    legacy=evaluate_floating_gate_optical_absorption(LightSource.laser(1550,1000),fg,
        optical_model=resolution.optical_model('FG1'))
    assert result.summary['absorbed_photon_flux_m2_s']==pytest.approx(legacy.absorbed_photon_flux_m2_s,rel=1e-14)
    assert result.profile.to_dict()['node_details'][0]['direct_gap_eV']==legacy.direct_gap_eV


def test_compact_ge_three_grids_include_known_threshold_nodes(evidence,fg):
    from ncmemsim.constants import ELEMENTARY_CHARGE_C
    edges=tuple(PLANCK_J_S*LIGHT_SPEED_M_S*1e9/(gap*ELEMENTARY_CHARGE_C)
                for gap in (.7985,.664-.027,.664+.027))
    totals=[]
    for n in (65,129,257):
        w=tuple(sorted(set([1500+500*i/(n-1) for i in range(n)]+[x for x in edges if 1500<x<2000])))
        source=TabulatedSpectrum(w,tuple(1 for _ in w),evidence)
        summary=evaluate(source,fg,evidence).summary
        totals.append((summary['absorbed_irradiance_W_m2'],summary['absorbed_photon_flux_m2_s']))
    for j in (0,1):
        coarse=abs(totals[1][j]-totals[0][j])/totals[2][j]
        fine=abs(totals[2][j]-totals[1][j])/totals[2][j]
        assert fine<coarse and fine<1e-3
