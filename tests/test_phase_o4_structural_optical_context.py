# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import math,json
import numpy as np
import pytest
from ncmemsim import DeviceBuilder,PhysicsModel,SimulationConfig,DeviceState
from ncmemsim.materials import make_ge,make_gesn
from ncmemsim.materials.temperature import GapKind
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.structural import StructuralEvidence,HydrostaticStrainDomain,ConfinementDomain,HydrostaticStrainGapShiftProfile,SphericalConfinementProfile
from ncmemsim.temperature_context import ThermalContext
from ncmemsim.spectral_sources import DiscreteLineSpectrum,TabulatedSpectrum,SpectralEvidence
from ncmemsim.spectral_absorption import SpectralAbsorptionProfile
from ncmemsim.spectral_stack import SpectralStackLayer
from ncmemsim.spectral_context import build_spectral_simulation_context
from ncmemsim.structural_optical_context import StructuralOpticalBinding,StructuralOpticalContext,StructuralSpectralContext,build_structural_spectral_context
from ncmemsim.photo import PhotoTransitionConfig,PhotoTransitionWeights

E=StructuralEvidence('synthetic O4','tests',ParameterStatus.ASSUMED,'not qualified coupled Ge model')
SE=SpectralEvidence('synthetic O4 source','tests','ASSUMED','canonical units',(),'explicit nodes','unknown','not calibrated')

def resolution(n=1,*,diameter=8,material=None):
    d=DeviceBuilder.v2(n,nc_material=make_ge() if material is None else material,nc_diameter_nm=diameter,fg_thickness_nm=6,nc_volume_fraction=.2)
    for fg in d.floating_gates():fg.grid_points=3
    return ThermalContext.from_nominal(d,PhysicsModel.default(),SimulationConfig()).resolve(temperature_K=300)

def binding(name='FG1',*,strain=True,confinement=True,enabled=True,trace=.001):
    strains=tuple(HydrostaticStrainGapShiftProfile('strain-'+k.name,name,k,HydrostaticStrainDomain('Ge',300,300,-.01,.01,E),-1,E) for k in (GapKind.GAMMA,GapKind.L)) if strain else ()
    sizes=tuple(SphericalConfinementProfile('size-'+k.name,name,k,'effective_scalar',ConfinementDomain('Ge',300,300,2e-9,1e-8,E),.2,.4,E,E,E) for k in (GapKind.GAMMA,GapKind.L)) if confinement else ()
    return StructuralOpticalBinding(name,strains,sizes,trace,enabled)

def passive(r,source):
    return tuple(SpectralStackLayer(SpectralAbsorptionProfile(x.name,source.wavelength_nm,tuple(0 for _ in source.wavelength_nm),x.thickness_nm*1e-9,1500,2000,SE),'passive','assumed_transparent') for x in r.device.layers if x.role!='floating_gate')

def spectral(c,source):
    return build_structural_spectral_context(c,source,direction='gate_to_substrate',passive_layers=passive(c.thermal_resolution,source),wavelength_min_nm=1500,wavelength_max_nm=2000,evidence=SE)

@pytest.mark.parametrize('mode',['strain','confinement','both'])
def test_separate_contributions_on_same_thermal_baseline(mode):
    r=resolution();b=binding(strain=mode!='confinement',confinement=mode!='strain');c=StructuralOpticalContext(r,(b,))
    for row in c.projection['layers']:
        assert row['radius_m_from_device']==4e-9
        for target in row['targets'].values():
            assert target['resolved_gap_eV']==math.fsum((target['thermal_baseline_gap_eV'],target['strain_gap_shift_eV'],target['kinetic_confinement_gap_shift_eV']))
            if mode!='confinement':assert target['strain_gap_shift_eV']==-.001
            if mode!='strain':assert target['confinement_result']['unconfined_gap_eV']==target['thermal_baseline_gap_eV']
    assert StructuralOpticalContext.from_json(c.to_json())==c

def test_disabled_and_zero_strain_preserve_legacy_optical_numbers():
    r=resolution(material=make_gesn(.08));c=StructuralOpticalContext(r,(binding(enabled=False,trace=.5),))
    fg=r.device.get_layer('FG1')
    assert c.optical_model('FG1').evaluate(fg.nc_material,1550)==r.optical_model('FG1').evaluate(fg.nc_material,1550)
    r=resolution();c=StructuralOpticalContext(r,(binding(confinement=False,trace=0),));fg=r.device.get_layer('FG1')
    a=c.optical_model('FG1').evaluate(fg.nc_material,1550);b=r.optical_model('FG1').evaluate(fg.nc_material,1550)
    assert (a.absorption_coefficient_m_inv,a.direct_gap_eV,a.indirect_gap_eV)==(b.absorption_coefficient_m_inv,b.direct_gap_eV,b.indirect_gap_eV)

@pytest.mark.parametrize('fault',['unknown','duplicate','profile_layer','target','material','strain_domain','radius_domain','temperature_domain'])
def test_invalid_attachments_and_applicability_fail(fault):
    with pytest.raises(ValueError):
        if fault=='unknown':StructuralOpticalContext(resolution(),(binding('other'),))
        elif fault=='duplicate':StructuralOpticalContext(resolution(),(binding(),binding()))
        elif fault=='profile_layer':replace(binding(),layer_name='FG2')
        elif fault=='target':replace(binding(),strain_profiles=(binding().strain_profiles[0],binding().strain_profiles[0]))
        elif fault=='material':StructuralOpticalContext(resolution(material=make_gesn(.08)),(binding(),))
        elif fault=='strain_domain':StructuralOpticalContext(resolution(),(binding(trace=.1),))
        elif fault=='radius_domain':StructuralOpticalContext(resolution(diameter=2),(binding(),))
        else:StructuralOpticalContext(replace(resolution(),temperature_K=350),(binding(),))

def test_device_radius_is_rebuilt_and_owned_inputs_not_mutated():
    r=resolution();before=deepcopy(r.to_dict());c=StructuralOpticalContext(r,(binding(),))
    smaller=StructuralOpticalContext(resolution(diameter=4),(binding(),))
    a=c.projection['layers'][0]['targets'][GapKind.GAMMA.value];b=smaller.projection['layers'][0]['targets'][GapKind.GAMMA.value]
    assert b['kinetic_confinement_gap_shift_eV']==pytest.approx(a['kinetic_confinement_gap_shift_eV']*4)
    fg=r.device.get_layer('FG1');model=c.optical_model('FG1');model.evaluate(fg.nc_material,1550)
    assert r.to_dict()==before
    with pytest.raises(ValueError):model.evaluate(replace(fg.nc_material,phi_barrier_prog_eV=99),1550)

def test_thermal_coupled_baseline_applied_once_and_phonons_preserved():
    from examples.phase_m4_ge_temperature_reference import build_context
    r=build_context().resolve(temperature_K=350)
    b=binding(strain=True,confinement=False)
    b=replace(b,strain_profiles=tuple(replace(p,domain=replace(p.domain,min_temperature_K=250,max_temperature_K=350)) for p in b.strain_profiles))
    c=StructuralOpticalContext(r,(b,));row=c.projection['layers'][0]
    thermal=r.to_dict()['resolved']['optical'][0]
    assert row['targets'][GapKind.GAMMA.value]['thermal_baseline_gap_eV']==thermal['gamma_gap_eV']
    assert row['thermal_optical_row']['absorption_parameters']['temperature_K']==350

@pytest.mark.parametrize('n',[1,2,3])
def test_spectral_sampling_and_simulator_map_owned_structural_gaps(n):
    r=resolution(n);c=StructuralOpticalContext(r,tuple(binding(fg.name) for fg in r.device.floating_gates()))
    source=TabulatedSpectrum((1500,1750,2000),(1,2,1),SE);wrapped=spectral(c,source)
    assert StructuralSpectralContext.from_json(wrapped.to_json())==wrapped
    simulator=wrapped.create_simulator();initial=DeviceState.empty_for_device(simulator.device)
    out=simulator.relax_voltage(initial,0,0,light_source=source,photo_config=PhotoTransitionConfig(.1),photo_weights=PhotoTransitionWeights())
    assert out['structural_context_hash']==c.contract_hash
    assert np.sum(out['absorbed_photon_flux_by_fg_m2_s'])==pytest.approx(wrapped.spectral_context.optical_result.projection['summary']['fg_absorbed_photon_flux_m2_s'])
    assert np.all(out['photo_transition_rate_by_fg_s']>=0)

def test_disabled_spectral_optics_recover_existing_n_context_values():
    r=resolution();c=StructuralOpticalContext(r,());source=DiscreteLineSpectrum((1550,),(1000,),SE)
    a=spectral(c,source).spectral_context.optical_result.projection
    b=build_spectral_simulation_context(r,source,direction='gate_to_substrate',passive_layers=passive(r,source),wavelength_min_nm=1500,wavelength_max_nm=2000,evidence=SE).optical_result.projection
    assert a['summary']==b['summary']
    assert [x['absorption']['summary'] for x in a['layers']]==[x['absorption']['summary'] for x in b['layers']]

def test_stale_spectral_context_and_changed_geometry_rejected():
    r=resolution();c=StructuralOpticalContext(r,(binding(),));source=DiscreteLineSpectrum((1550,),(1000,),SE);wrapped=spectral(c,source)
    changed=StructuralOpticalContext(r,(binding(trace=.002),))
    with pytest.raises(ValueError):StructuralSpectralContext(changed,wrapped.spectral_context)
    with pytest.raises(ValueError):StructuralSpectralContext(StructuralOpticalContext(resolution(diameter=6),(binding(),)),wrapped.spectral_context)

@pytest.mark.parametrize('fault',['resolved_gap','contribution','policy','extra','schema'])
def test_context_reader_rebuilds_contributions_and_rejects_tampering(fault):
    c=StructuralOpticalContext(resolution(),(binding(),));raw=c.to_dict()
    if fault=='resolved_gap':raw['resolved']['layers'][0]['targets'][GapKind.GAMMA.value]['resolved_gap_eV']+=.1
    elif fault=='contribution':raw['resolved']['layers'][0]['targets'][GapKind.L.value]['strain_gap_shift_eV']*=2
    elif fault=='policy':raw['resolved']['composition_policy']='qualified_coupled_model'
    elif fault=='extra':raw['barrier_override']=1
    else:raw['schema_version']='unknown'
    with pytest.raises(ValueError):StructuralOpticalContext.from_dict(raw)

def test_restoration_recomputes_gaps_but_never_resamples_optics(monkeypatch):
    c=StructuralOpticalContext(resolution(),(binding(),));wrapped=spectral(c,DiscreteLineSpectrum((1550,),(1000,),SE));raw=wrapped.to_json()
    import ncmemsim.structural_optical_context as module
    def forbidden(*args,**kwargs):raise AssertionError('no optical replay')
    monkeypatch.setattr(module._StructuralOpticalModel,'evaluate',forbidden)
    assert StructuralSpectralContext.from_json(raw)==wrapped


def test_absorption_channels_are_recomputed_from_structural_gaps():
    from ncmemsim.constants import BOLTZMANN_J_K,ELEMENTARY_CHARGE_C
    r=resolution();c=StructuralOpticalContext(r,(binding(),));fg=r.device.get_layer('FG1')
    point=c.optical_model('FG1').evaluate(fg.nc_material,1500)
    base=r.optical_model('FG1').evaluate(fg.nc_material,1500)
    energy=point.photon_energy_eV;gamma=point.direct_gap_eV;l_gap=point.indirect_gap_eV
    occupation=1/math.expm1(.027*ELEMENTARY_CHARGE_C/(BOLTZMANN_J_K*300))
    expected_direct=1e7*math.sqrt(max(energy-gamma,0))/energy
    expected_indirect=1e6*(occupation*max(energy-l_gap+.027,0)**2+(occupation+1)*max(energy-l_gap-.027,0)**2)
    expected_tail=1e5*math.exp((energy-gamma)/.012) if energy<gamma else 0
    assert point.alpha_direct_m_inv==pytest.approx(expected_direct)
    assert point.alpha_indirect_m_inv==pytest.approx(expected_indirect)
    assert point.alpha_urbach_m_inv==pytest.approx(expected_tail)
    assert point.absorption_coefficient_m_inv!=base.absorption_coefficient_m_inv
    assert 'structural_composition' in point.provenance


def test_disabled_pulse_preserves_n4_probabilities_and_caller_state():
    r=resolution();c=StructuralOpticalContext(r,());source=DiscreteLineSpectrum((1550,),(1000,),SE)
    wrapped=spectral(c,source);old=build_spectral_simulation_context(r,source,direction='gate_to_substrate',passive_layers=passive(r,source),wavelength_min_nm=1500,wavelength_max_nm=2000,evidence=SE)
    initial=DeviceState.empty_for_device(r.device);before=initial.copy()
    args={'light_source':source,'photo_config':PhotoTransitionConfig(.1),'photo_weights':PhotoTransitionWeights(),'occupancy_integrator':'backward_euler'}
    a=wrapped.create_simulator().relax_voltage(initial,0,1e-8,1e-9,**args)
    b=old.create_simulator().relax_voltage(initial,0,1e-8,1e-9,**args)
    for key in ('P0','P1','P2'):
        np.testing.assert_array_equal(getattr(a['state'].floating_gates[0],key),getattr(b['state'].floating_gates[0],key))
        np.testing.assert_array_equal(getattr(initial.floating_gates[0],key),getattr(before.floating_gates[0],key))
    assert a['qfg_C_m2']==b['qfg_C_m2']


def test_simulator_rejects_electrical_context_drift():
    c=StructuralOpticalContext(resolution(),(binding(),));wrapped=spectral(c,DiscreteLineSpectrum((1550,),(1000,),SE));simulator=wrapped.create_simulator()
    initial=DeviceState.empty_for_device(simulator.device);simulator.device.temperature_K=301
    with pytest.raises(ValueError):simulator.relax_voltage(initial,0,0)


def test_pulse_wrapper_retains_structural_owner_and_dark_read():
    from ncmemsim.structural_optical_context import run_structural_spectral_program_pulse_read
    from ncmemsim.spectral_context import SpectralPulseProtocol
    from ncmemsim.program_protocol import ProgramPulseReadProtocol
    c=StructuralOpticalContext(resolution(),(binding(),));wrapped=spectral(c,DiscreteLineSpectrum((1550,),(1000,),SE))
    protocol=SpectralPulseProtocol(ProgramPulseReadProtocol(0,1e-8,0,1e-9),PhotoTransitionWeights())
    out=run_structural_spectral_program_pulse_read(wrapped,protocol,photo_config=PhotoTransitionConfig(.1))
    assert out['context_hash']==wrapped.contract_hash and out['structural_context_hash']==c.contract_hash
    assert out['spectral_run']['read']['spectral_stack'] is None
    assert StructuralSpectralContext.from_dict(out['context'])==wrapped
