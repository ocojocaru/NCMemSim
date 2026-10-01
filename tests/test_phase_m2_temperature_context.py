# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Owned runtime inputs, independent controls and recomputed thermal archives."""
from dataclasses import asdict, replace, FrozenInstanceError
import json
import math
import numpy as np
import pytest
from ncmemsim import DeviceBuilder, DeviceState, PhysicsModel, Simulator
from ncmemsim.simulator import SimulationConfig
from ncmemsim.electrostatics import SemiconductorConfig
from ncmemsim.constants import BOLTZMANN_J_K, ELEMENTARY_CHARGE_C
from ncmemsim.optics import LightSource, evaluate_floating_gate_optical_absorption
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.temperature import (
    IntrinsicDensityProfile, CarrierStatisticsDomain, TemperatureDomain,
    ThermalEvidence, profile_from_reviewed_record, reviewed_varshni_coefficients,
)
from ncmemsim.materials.optics.models import CompositeGeSnAbsorptionModel
from ncmemsim.temperature_context import (
    ThermalContext, ResolvedThermalContext, ThermalSimulator, OpticalThermalBinding,
    SemiconductorThermalMode as SMode, OpticalThermalMode as OMode,
)
from ncmemsim.retention import RetentionConfig, RetentionSolver


def make(n=1):
    d = DeviceBuilder.v2(n)
    for fg in d.floating_gates(): fg.grid_points = 3
    d.metadata['nested'] = {'caller': [1, 2]}
    d.get_layer('FG1').metadata['layer'] = {'caller': [3]}
    p = PhysicsModel.default()
    p.electrostatics.semiconductor = replace(SemiconductorConfig(), electron_affinity_eV=4.09, transition_width_V=.25)
    return d, p, SimulationConfig(dwell_time_s=1e-6, internal_dt_s=1e-6, qfix_C_m2=1e-7)


def assumed():
    return ThermalEvidence('Synthetic M2 assumption', 'test', ParameterStatus.ASSUMED, 'Isolation test only')


def profile(index, anchor):
    r = reviewed_varshni_coefficients()[index]
    return profile_from_reviewed_record(r, name='M2-'+r.name,
        domain=TemperatureDomain(r.material,250,350,0,0,assumed()),
        reference_temperature_K=300, reference_gap_eV=anchor, reference_evidence=assumed())


def context(enabled=True, smode=SMode.COUPLED, omode=OMode.COUPLED, n=1):
    d,p,c=make(n); g=profile(0,1.12)
    ni=IntrinsicDensityProfile('M2-ni',g,1e16,assumed(),CarrierStatisticsDomain(1e20,1e24,10,assumed()))
    return ThermalContext.from_nominal(d,p,c,enabled=enabled,semiconductor_mode=smode,
        substrate_gap=g,intrinsic_density=ni,optical_bindings=tuple(
        OpticalThermalBinding(fg.name,omode,profile(1,.7985),profile(2,.664)) for fg in d.floating_gates()))


def run(sim, light=True):
    return sim.relax_voltage(DeviceState.empty_for_device(sim.device),2,
        light_source=LightSource.led(1550,10) if light else None)


def compare(a,b):
    assert set(a)==set(b)
    for name in a:
        if isinstance(a[name],np.ndarray): np.testing.assert_array_equal(a[name],b[name])
        elif isinstance(a[name],float) and math.isnan(a[name]): assert math.isnan(b[name]),name
        elif isinstance(a[name],(int,float,str,type(None))): assert a[name]==b[name],name
    for x,y in zip(a['state'].floating_gates,b['state'].floating_gates):
        for name in ('P0','P1','P2'): np.testing.assert_array_equal(getattr(x,name),getattr(y,name))


@pytest.mark.parametrize('t',[250,300,350,400])
@pytest.mark.parametrize('n',[1,2,3])
def test_disabled_identity(t,n):
    r=context(enabled=False,n=n).resolve(temperature_K=t)
    compare(run(Simulator(r.device,r.physics,r.simulation_config)),run(r.create_simulator()))
    assert r.to_dict()['resolved']['optical'][0]['applied_mode']=='legacy'
    assert r.physics.electrostatics.semiconductor.bandgap_eV==1.12


@pytest.mark.parametrize('n',[1,2,3])
def test_exact_reference_optical_and_transient_identity(n):
    r=context(n=n).resolve(temperature_K=300)
    compare(run(Simulator(r.device,r.physics,r.simulation_config)),run(r.create_simulator()))
    m=r.device.get_layer('FG1').nc_material
    assert r.optical_model('FG1').evaluate(m,1550)==CompositeGeSnAbsorptionModel().evaluate(m,1550)


@pytest.mark.parametrize('smode',list(SMode))
@pytest.mark.parametrize('omode',list(OMode))
def test_independent_controls(smode,omode):
    r=context(smode=smode,omode=omode).resolve(temperature_K=350); c=r.context
    s=r.physics.electrostatics.semiconductor
    assert s.bandgap_eV==(c.substrate_gap.evaluate(350) if smode in (SMode.GAP_ONLY,SMode.COUPLED) else 1.12)
    assert s.intrinsic_density_m3==(c.intrinsic_density.evaluate(350,substrate_doping_m3=1e21) if smode in (SMode.DENSITY_ONLY,SMode.COUPLED) else 1e16)
    assert s.electron_affinity_eV==4.09 and s.transition_width_V==.25
    row=r.to_dict()['resolved']['optical'][0]
    assert row['gamma_gap_eV']==(c.optical_bindings[0].gamma_profile.evaluate(350) if omode in (OMode.GAPS_ONLY,OMode.COUPLED) else .7985)
    assert row['phonon_temperature_K']==(350 if omode in (OMode.PHONONS_ONLY,OMode.COUPLED) else 300)
    result=run(r.create_simulator())
    point=evaluate_floating_gate_optical_absorption(LightSource.led(1550,10),r.device.get_layer('FG1'),optical_model=r.optical_model('FG1'))
    assert result['optical_alpha_nc_by_fg_m_inv'][0]==point.nc_absorption_coefficient_m_inv


def test_electrical_expression_and_one_phonon_factor():
    r=context().resolve(temperature_K=350); e,d=r.physics.electrostatics,r.device
    phi=BOLTZMANN_J_K*350/ELEMENTARY_CHARGE_C*math.log(d.substrate_doping_m3/e.semiconductor.intrinsic_density_m3)
    assert e.fermi_potential(d)==phi
    assert e.flatband_zero(d)==d.gate_work_function_eV-(4.09+.5*e.semiconductor.bandgap_eV+phi)
    point=r.optical_model('FG1').evaluate(d.get_layer('FG1').nc_material,1550)
    energy,gap,eph=point.photon_energy_eV,point.indirect_gap_eV,.027
    nph=1/math.expm1(eph*ELEMENTARY_CHARGE_C/(BOLTZMANN_J_K*350))
    assert point.alpha_indirect_m_inv==1e6*(nph*max(energy-gap+eph,0)**2+(nph+1)*max(energy-gap-eph,0)**2)
    assert point.provenance['gamma_gap'].status is ParameterStatus.DERIVED
    b=r.context.optical_bindings[0]; row=r.to_dict()['resolved']['optical'][0]
    for key,value in asdict(b.absorption_parameters).items():
        if key!='temperature_K': assert row['absorption_parameters'][key]==value


def test_emitter_temperature_is_separate():
    r=context().resolve(temperature_K=350)
    source=replace(LightSource.led(1550,10),temperature_K=2800)
    actual=r.create_simulator().relax_voltage(DeviceState.empty_for_device(r.device),2,light_source=source)
    compare(actual,run(r.create_simulator()))


def test_owned_nominal_and_candidates():
    d,p,s=make(); c=ThermalContext.from_nominal(d,p,s); before=c.to_json()
    d.metadata['nested']['caller'].append(9); d.get_layer('FG1').metadata['layer']['caller'].append(9)
    p.electrostatics.semiconductor=replace(p.electrostatics.semiconductor,bandgap_eV=9)
    assert c.to_json()==before
    a,b=c.resolve(temperature_K=250),c.resolve(temperature_K=350)
    owned=a.device; owned.metadata['nested']['caller'].append(7)
    assert a.device.metadata['nested']['caller']==b.device.metadata['nested']['caller']==[1,2]
    physics=a.physics
    assert physics.tunneling is physics.occupancy.tunneling is physics.transport.tunneling
    assert b.physics.tunneling is not physics.tunneling
    assert a.device.get_layer('FG1').nc_material==b.device.get_layer('FG1').nc_material
    projection=a.to_dict(); projection['resolved']['physics']['semiconductor']['bandgap_eV']=100
    assert a.to_dict()['resolved']['physics']['semiconductor']['bandgap_eV']==1.12


@pytest.mark.parametrize('target',['temperature','doping','material','physics','config','metadata'])
def test_runtime_drift(target):
    sim=context().resolve(temperature_K=350).create_simulator()
    if target=='temperature': sim.device.temperature_K=300
    if target=='doping': sim.device.substrate_doping_m3=1e22
    if target=='material': sim.device.get_layer('FG1').nc_material=replace(sim.device.get_layer('FG1').nc_material,sn_fraction=.1)
    if target=='physics': sim.physics.electrostatics.semiconductor=replace(sim.physics.electrostatics.semiconductor,bandgap_eV=1.12)
    if target=='config': sim.config=replace(sim.config,qfix_C_m2=0)
    if target=='metadata': sim.device.metadata['new']='changed'
    with pytest.raises(ValueError,match='changed'): run(sim)


def test_retention_shared_context():
    r=context().resolve(temperature_K=350); sim=r.create_simulator()
    result=RetentionSolver(sim,RetentionConfig(total_time_s=1e-6,initial_dt_s=1e-6,maximum_dt_s=1e-6,output_points=2)).run(DeviceState.empty_for_device(sim.device))
    assert np.all(np.isfinite(result.qfg_C_m2))
    assert sim.device.temperature_K==350
    assert sim.physics.electrostatics.semiconductor.bandgap_eV==r.context.substrate_gap.evaluate(350)


@pytest.mark.parametrize('bad',[True,'350',0,-1,float('inf'),float('nan'),249,351])
def test_invalid_active_temperature(bad):
    with pytest.raises(ValueError): context().resolve(temperature_K=bad)


@pytest.mark.parametrize('mode',[OMode.GAPS_ONLY,OMode.PHONONS_ONLY,OMode.COUPLED])
def test_every_optical_control_enforces_domain(mode):
    with pytest.raises(ValueError): context(smode=SMode.LEGACY,omode=mode).resolve(temperature_K=400)


@pytest.mark.parametrize('field,bad',[('enabled',1),('semiconductor_mode','coupled'),('substrate_gap',None),('intrinsic_density',None),('optical_bindings',[]),('substrate_gap',profile(1,.7985))])
def test_invalid_context(field,bad):
    with pytest.raises(ValueError): replace(context(),**{field:bad})


def test_targets_anchors_references_and_attachments():
    c=context(); b=c.optical_bindings[0]
    for change in ({'gamma_profile':profile(2,.664)},{'l_profile':None},{'gamma_profile':replace(b.gamma_profile,reference_gap_eV=.8)}, {'absorption_parameters':replace(b.absorption_parameters,temperature_K=350)}):
        with pytest.raises(ValueError): replace(b,**change)
    with pytest.raises(ValueError): replace(c,optical_bindings=(b,b))
    with pytest.raises(ValueError): replace(c,optical_bindings=(replace(b,layer_name='missing'),))
    with pytest.raises(ValueError): replace(context(n=2),optical_bindings=(b,))
    g=replace(c.substrate_gap,reference_temperature_K=310)
    with pytest.raises(ValueError,match='reference'): replace(c,substrate_gap=g,intrinsic_density=replace(c.intrinsic_density,gap_profile=g))
    with pytest.raises(ValueError): c.resolve().optical_model('missing')


@pytest.mark.parametrize('factory',[lambda:context(),lambda:context().resolve(temperature_K=350)])
def test_strict_roundtrip_and_frozen_hash(factory):
    value=factory(); restored=type(value).from_json(value.to_json())
    assert restored==value and restored.context_hash==value.context_hash
    with pytest.raises(FrozenInstanceError): value.temperature_K=100


@pytest.mark.parametrize('target',['source_hash','nominal_hash','gap','ni','temperature','phonon','barrier','extra','nested_extra','schema'])
def test_resolution_tampering(target):
    data=context().resolve(temperature_K=350).to_dict()
    if target=='source_hash': data['source_context_hash']='0'*64
    if target=='nominal_hash': data['nominal_hash']='0'*64
    if target=='gap': data['resolved']['physics']['semiconductor']['bandgap_eV']=1.12
    if target=='ni': data['resolved']['physics']['semiconductor']['intrinsic_density_m3']=1e16
    if target=='temperature': data['temperature_K']=340
    if target=='phonon': data['resolved']['optical'][0]['phonon_temperature_K']=300
    if target=='barrier': data['resolved']['device']['layer_material_definitions'][1]['nc_material']['phi_barrier_prog_eV']=9
    if target=='extra': data['extra']=1
    if target=='nested_extra': data['resolved']['optical'][0]['extra']=1
    if target=='schema': data['schema_version']='future'
    with pytest.raises(ValueError): ResolvedThermalContext.from_dict(data)


@pytest.mark.parametrize('target',['missing','extra','nested_missing','nested_extra','numeric_bool','profile','bindings'])
def test_nominal_archive_errors(target):
    data=context().to_dict()
    if target=='missing': del data['simulation_config']
    if target=='extra': data['extra']=1
    if target=='nested_missing': del data['nominal_device']['device']['layers'][0]['role']
    if target=='nested_extra': data['nominal_device']['device']['layers'][0]['extra']=1
    if target=='numeric_bool': data['simulation_config']['internal_dt_s']=True
    if target=='profile': data['substrate_gap']['domain']['max_temperature_K']='350'
    if target=='bindings': data['optical_bindings'][0]['optical_parameters']['unknown']=1
    with pytest.raises(ValueError): ThermalContext.from_dict(data)


@pytest.mark.parametrize('text',['{"enabled":true,"enabled":false}','{"temperature":NaN}','[]','{}'])
def test_invalid_json(text):
    with pytest.raises(ValueError): ThermalContext.from_json(text)


def test_legacy_without_profiles_and_custom_runtime_rejection():
    c=ThermalContext.from_nominal(*make(),enabled=True); r=c.resolve(temperature_K=400)
    compare(run(r.create_simulator()),run(Simulator(r.device,r.physics,r.simulation_config)))
    with pytest.raises(ValueError): replace(c,nominal_device_json=json.dumps(json.loads(c.nominal_device_json),indent=2))
    class ExtendedPhysics(PhysicsModel): pass
    d,p,s=make()
    with pytest.raises(TypeError): ThermalContext.from_nominal(d,ExtendedPhysics(**vars(p)),s)
    with pytest.raises(ValueError): ThermalSimulator('not a resolution')


def test_hashes_cover_controls_and_temperature():
    c=context()
    assert c.context_hash!=replace(c,enabled=False).context_hash
    assert c.nominal_hash==replace(c,enabled=False).nominal_hash
    assert c.resolve(temperature_K=300).context_hash!=c.resolve(temperature_K=350).context_hash
    assert c.context_hash!=replace(c,semiconductor_mode=SMode.GAP_ONLY).context_hash


def test_custom_nominal_overrides_recover_exactly():
    from ncmemsim.materials.optics.models import GeSnOpticalParameterSet, GeSnAbsorptionParameterSet
    d,p,s=make(); p.electrostatics.semiconductor=replace(p.electrostatics.semiconductor,bandgap_eV=1.13,intrinsic_density_m3=2e16)
    gap=profile(0,1.13)
    ni=IntrinsicDensityProfile('custom-ni',gap,2e16,assumed(),CarrierStatisticsDomain(1e20,1e24,10,assumed()))
    optical=replace(GeSnOpticalParameterSet(),ge_direct_gap_eV=.81,ge_indirect_gap_eV=.67)
    absorption=replace(GeSnAbsorptionParameterSet(),direct_prefactor_A=8e6,indirect_prefactor_A=3e5,urbach_energy_eV=.014)
    binding=OpticalThermalBinding('FG1',OMode.COUPLED,profile(1,.81),profile(2,.67),optical,absorption)
    c=ThermalContext.from_nominal(d,p,s,enabled=True,semiconductor_mode=SMode.COUPLED,substrate_gap=gap,intrinsic_density=ni,optical_bindings=(binding,))
    r=c.resolve(temperature_K=300)
    assert r.physics.electrostatics.semiconductor==p.electrostatics.semiconductor
    m=d.get_layer('FG1').nc_material
    assert r.optical_model('FG1').evaluate(m,1600)==CompositeGeSnAbsorptionModel(optical,absorption).evaluate(m,1600)
    assert ResolvedThermalContext.from_json(r.to_json()).to_json()==r.to_json()


def test_gesn_requires_its_own_composition_qualified_profiles():
    from ncmemsim.materials.models.gesn import GeSnModel
    from ncmemsim.materials.temperature import AnchoredVarshniProfile, ThermalMaterial, GapKind
    from ncmemsim.materials.optics.models import direct_gap_gesn_eV,indirect_gap_gesn_eV
    d,p,s=make(); material=GeSnModel(.1).build(); d.get_layer('FG1').nc_material=material
    domain=TemperatureDomain(ThermalMaterial.GERMANIUM_TIN,250,350,.1,.1,assumed())
    gamma=AnchoredVarshniProfile('synthetic-gesn-Gamma',GapKind.GAMMA,domain,.1,300,direct_gap_gesn_eV(.1),.0003,300,assumed(),assumed())
    l_gap=AnchoredVarshniProfile('synthetic-gesn-L',GapKind.L,domain,.1,300,indirect_gap_gesn_eV(.1),.0002,250,assumed(),assumed())
    binding=OpticalThermalBinding('FG1',OMode.COUPLED,gamma,l_gap)
    c=ThermalContext.from_nominal(d,p,s,enabled=True,optical_bindings=(binding,))
    r=c.resolve(temperature_K=350)
    point=r.optical_model('FG1').evaluate(material,1600)
    assert point.direct_gap_eV==gamma.evaluate(350,sn_fraction=.1)
    assert point.indirect_gap_eV==l_gap.evaluate(350,sn_fraction=.1)
    assert r.device.get_layer('FG1').nc_material==material
    with pytest.raises(ValueError):
        ThermalContext.from_nominal(d,p,s,enabled=True,optical_bindings=context().optical_bindings)
    with pytest.raises(ValueError): r.optical_model('FG1').evaluate(replace(material,sn_fraction=.11),1600)


def test_heterogeneous_attachments_resolve_independently():
    c=context(n=2); one,two=c.optical_bindings
    c=replace(c,optical_bindings=(replace(two,mode=OMode.PHONONS_ONLY),one))
    assert c.optical_bindings[0].layer_name=='FG1'
    r=c.resolve(temperature_K=350); rows=r.to_dict()['resolved']['optical']
    assert rows[0]['gamma_gap_eV']<.7985 and rows[1]['gamma_gap_eV']==.7985
    assert rows[0]['phonon_temperature_K']==rows[1]['phonon_temperature_K']==350
    sim=r.create_simulator(); result=run(sim)
    assert result['optical_alpha_nc_by_fg_m_inv'][0]!=result['optical_alpha_nc_by_fg_m_inv'][1]


def test_dark_simulation_and_occupancy_use_device_temperature_once():
    r=context(smode=SMode.LEGACY,omode=OMode.LEGACY).resolve(temperature_K=350)
    compare(run(r.create_simulator(),light=False),run(Simulator(r.device,r.physics,r.simulation_config),light=False))
    state=DeviceState.empty_for_device(r.device)
    sim=r.create_simulator()
    first=sim.relax_voltage(state,2,occupancy_integrator='backward_euler')
    second=sim.relax_voltage(state,2,occupancy_integrator='backward_euler')
    compare(first,second)
    assert np.all(state.floating_gates[0].P0==1)


def test_material_scope_and_doping_domain_not_silently_widened():
    c=context(); data=c.to_dict()
    data['nominal_device']['device']['substrate_doping_m3']=1e19
    changed=ThermalContext.from_dict(data)
    with pytest.raises(ValueError,match='doping'): changed.resolve(temperature_K=350)
    data=c.to_dict()
    data['nominal_device']['layer_material_definitions'][1]['nc_material']['model_name']='OtherCompound'
    with pytest.raises(ValueError,match='Ge/GeSn'): ThermalContext.from_dict(data)


@pytest.mark.parametrize('wavelength',[True,'1550',0,-1,float('nan'),float('inf'),1e-320,1e-200])
def test_nonrepresentable_optical_inputs(wavelength):
    r=context().resolve(temperature_K=350)
    with pytest.raises(ValueError): r.optical_model('FG1').evaluate(r.device.get_layer('FG1').nc_material,wavelength)


@pytest.mark.parametrize('field,bad',[('optical_bindings',[]),('device',False),('physics',False),('config',False)])
def test_factory_rejects_untyped_false_values(field,bad):
    d,p,s=make(); kwargs={'device':d,'physics':p,'config':s}
    kwargs[field]=bad
    with pytest.raises((ValueError,TypeError)): ThermalContext.from_nominal(**kwargs)
