# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Controlled synthetic structural optical/broadband and electro-optical reference."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import argparse,json,math,sys
import numpy as np
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ncmemsim import DeviceBuilder,PhysicsModel,SimulationConfig,DeviceState
from ncmemsim._version import __version__
from ncmemsim.constants import PLANCK_J_S,LIGHT_SPEED_M_S,ELEMENTARY_CHARGE_C
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials import make_ge
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.temperature import GapKind
from ncmemsim.materials.structural import StructuralEvidence,HydrostaticStrainDomain,ConfinementDomain,HydrostaticStrainGapShiftProfile,SphericalConfinementProfile
from ncmemsim.temperature_context import ThermalContext
from ncmemsim.structural_optical_context import StructuralOpticalBinding,StructuralOpticalContext,build_structural_spectral_context,run_structural_spectral_program_pulse_read
from ncmemsim.spectral_sources import TabulatedSpectrum,SpectralEvidence
from ncmemsim.spectral_absorption import SpectralAbsorptionProfile, SpectralAbsorptionResult
from ncmemsim.spectral_stack import SpectralStackLayer
from ncmemsim.spectral_context import SpectralPulseProtocol
from ncmemsim.program_protocol import ProgramPulseReadProtocol
from ncmemsim.photo import PhotoTransitionConfig,PhotoTransitionWeights
from ncmemsim.kinetics import OccupancyEngine
from ncmemsim.tunneling import TunnelingEngine

MODES=('baseline','strain','confinement','composed')
GRIDS=(129,257,513);STEPS=(16,32,64)
POWER_W_M2=1e6;DURATION_S=1e-7;SPECTRAL_RTOL=2e-3;PROBABILITY_ATOL=2e-3;CONTRAST_ATOL_V=1e-5
SCOPE=('Synthetic structural gap/mass/domain and additive-composition assumptions; bulk-Ge compact optics, '
    'transparent passive/matrix layers and constant capture .1. No embedded-NC material/capture qualification, '
    'Coulomb/image/finite-barrier/shear/interference or manufacturing-yield claim. '
    'Combined electrical/optical charge is not attributed wholly to absorbed photons.')
E=StructuralEvidence('O5 diagnostic parameters','explicit O1 synthetic fixture',ParameterStatus.ASSUMED,SCOPE)
SE=SpectralEvidence('O5 flat in-band source','explicit numerical diagnostic','ASSUMED','dimensionless shape',(),
    'declared wavelength grid','unknown',SCOPE)


def structural_context(mode,n=1,diameter_nm=8.,temperature_K=300.,trace=.005):
    if mode not in MODES:raise ValueError('unsupported control mode')
    from examples.phase_m4_ge_temperature_reference import build_context as thermal_template
    template=thermal_template()
    device=DeviceBuilder.v2(n,name='o5-fixed-geometry',nc_material=make_ge(),nc_diameter_nm=diameter_nm,
        nc_volume_fraction=.2,active_fraction=.1,fg_thickness_nm=6)
    for fg in device.floating_gates():fg.grid_points=3
    thermal=ThermalContext.from_nominal(device,PhysicsModel.default(),SimulationConfig(),enabled=True,
        optical_bindings=tuple(replace(template.optical_bindings[0],layer_name=fg.name) for fg in device.floating_gates())).resolve(temperature_K=temperature_K)
    bindings=[]
    if mode!='baseline':
        for fg in thermal.device.floating_gates():
            strain=tuple(HydrostaticStrainGapShiftProfile('o5-'+k.name,fg.name,k,
                HydrostaticStrainDomain('Ge',250,350,-.01,.01,E),slope,E) for k,slope in ((GapKind.GAMMA,-1),(GapKind.L,-.5))) if mode in ('strain','composed') else ()
            confinement=tuple(SphericalConfinementProfile('o5-'+k.name,fg.name,k,'effective_scalar',
                ConfinementDomain('Ge',250,350,2e-9,1e-8,E),mass,.4,E,E,E) for k,mass in ((GapKind.GAMMA,.2),(GapKind.L,.3))) if mode in ('confinement','composed') else ()
            bindings.append(StructuralOpticalBinding(fg.name,strain,confinement,trace))
    return StructuralOpticalContext(thermal,tuple(bindings))


def threshold_union():
    edges=[]
    for t in (300,350):
        for mode in MODES:
            for row in structural_context(mode,temperature_K=t).projection['layers']:
                g=row['targets'][GapKind.GAMMA.value]['resolved_gap_eV'];l=row['targets'][GapKind.L.value]['resolved_gap_eV']
                for energy in (g,l-.027,l+.027):
                    wavelength=PLANCK_J_S*LIGHT_SPEED_M_S*1e9/(energy*ELEMENTARY_CHARGE_C)
                    if 1000<wavelength<2200:edges.append(wavelength)
    return tuple(sorted(set(edges)))


def source(nodes,edges):
    grid=tuple(sorted(set([1000.+1200*i/(nodes-1) for i in range(nodes)]+list(edges))))
    return TabulatedSpectrum(grid,tuple(1. for _ in grid),SE,'relative_shape',POWER_W_M2)


def spectral(context,light):
    passive=tuple(SpectralStackLayer(SpectralAbsorptionProfile(x.name,light.wavelength_nm,
        tuple(0. for _ in light.wavelength_nm),x.thickness_nm*1e-9,1000,2200,SE),'passive','assumed_transparent')
        for x in context.thermal_resolution.device.layers if x.role!='floating_gate')
    return build_structural_spectral_context(context,light,direction='gate_to_substrate',passive_layers=passive,
        wavelength_min_nm=1000,wavelength_max_nm=2200,evidence=SE)


def pulse(context,steps,*,efficiency=.1,dark=False):
    protocol=SpectralPulseProtocol(ProgramPulseReadProtocol(2,DURATION_S,0,DURATION_S/steps),PhotoTransitionWeights())
    if dark:
        simulator=context.create_simulator();initial=DeviceState.empty_for_device(simulator.device)
        program=simulator.relax_voltage(initial,2,DURATION_S,DURATION_S/steps,occupancy_integrator='backward_euler')
        read=simulator.relax_voltage(program['state'],0,0)
    else:
        run=run_structural_spectral_program_pulse_read(context,protocol,photo_config=PhotoTransitionConfig(efficiency))['spectral_run']
        program=run['program'];read=run['read']
    def p(state):return np.stack([np.stack((x.P0,x.P1,x.P2),axis=1) for x in state.floating_gates])
    probabilities=p(program['state']);read_probabilities=p(read['state'])
    return {'steps':steps,'protocol':protocol.to_dict(),'capture_efficiency':efficiency,'dark':dark,
        'probabilities':probabilities.tolist(),'read_vfb_V':float(read['vfb_V']),
        'qfg_by_fg_C_m2':program['qfg_by_fg_C_m2'].tolist(),
        'absorbed_photon_flux_by_fg_m2_s':program['absorbed_photon_flux_by_fg_m2_s'].tolist(),
        'photo_transition_rate_by_fg_s':program['photo_transition_rate_by_fg_s'].tolist(),
        'minimum_probability':float(probabilities.min()),'probability_mass_error':float(np.max(abs(probabilities.sum(axis=2)-1))),
        'read_probability_change':float(np.max(abs(probabilities-read_probabilities)))}


def run_reference():
    edges=threshold_union();cases=[]
    for mode in MODES:
        owner=structural_context(mode);audit=[];final=None
        for grid in GRIDS:
            context=spectral(owner,source(grid,edges))
            audit.append({'base_nodes':grid,'actual_nodes':len(context.spectral_context.optical_result.source.wavelength_nm),
                'summary':context.spectral_context.optical_result.projection['summary']})
            final=context
        programs=[]
        for steps in STEPS:
            light=pulse(final,steps);dark=pulse(final,steps,dark=True)
            programs.append({'light':light,'dark':dark,'photo_contrast_V':light['read_vfb_V']-dark['read_vfb_V']})
        cases.append({'mode':mode,'structural_context':owner.to_dict(),'structural_context_hash':owner.contract_hash,
            'source':final.spectral_context.optical_result.source.to_dict(),'spectral_context_hash':final.contract_hash,
            'spectral_audit':audit,'optical_layers':final.spectral_context.optical_result.projection['layers'],
            'programs':programs})
    controls=[];light=source(GRIDS[-1],edges)
    for n in (2,3):
        owner=structural_context('composed',n);context=spectral(owner,light)
        controls.append({'kind':'multiple_fg','n_fgs':n,'structural_context':owner.to_dict(),
            'optical_summary':context.spectral_context.optical_result.projection['summary'],'pulse':pulse(context,64)})
    for diameter in (4.,8.):
        owner=structural_context('composed',diameter_nm=diameter);context=spectral(owner,light)
        fg=owner.thermal_resolution.device.get_layer('FG1');kinetics=OccupancyEngine(TunnelingEngine())
        controls.append({'kind':'diameter','diameter_nm':diameter,'structural_context':owner.to_dict(),
            'physical_nc_density_m3':kinetics.nanocrystal_density(diameter*1e-9,fg.nc_volume_fraction),
            'charging_energy_J':kinetics.charging_energy_J(diameter*1e-9),'pulse':pulse(context,64)})
    for t in (300.,350.):
        owner=structural_context('composed',temperature_K=t);context=spectral(owner,light)
        controls.append({'kind':'temperature','temperature_K':t,'source':light.to_dict(),'structural_context':owner.to_dict(),
            'optical_summary':context.spectral_context.optical_result.projection['summary']})
    context=spectral(structural_context('composed'),light)
    controls.append({'kind':'zero_capture','zero_capture':pulse(context,64,efficiency=0),'dark':pulse(context,64,dark=True)})
    failures=[]
    for name,params in (('strain_domain',{'trace':.02}),('radius_domain',{'diameter_nm':2}),('temperature_domain',{'temperature_K':400})):
        try:structural_context('composed',**params)
        except ValueError as exc:failures.append({'case':name,'request':{'mode':'composed',**params},'status':'failed','error_type':'ValueError','message':str(exc)})
        else:raise AssertionError('expected negative control')
    raw={'schema_version':'o5-structural-reference-v1','software_version':__version__,
        'implementation_baseline':'cf7aed6b637567f34040c7049d1e2fa9b0e03a60','scope':SCOPE,
        'acceptance':{'spectral_rtol':SPECTRAL_RTOL,'probability_atol':PROBABILITY_ATOL,'contrast_atol_V':CONTRAST_ATOL_V},
        'source_support_nm':[1000,2200],'threshold_union_nm':list(edges),'cases':cases,'controls':controls,'failures':failures,
        'case_counts':{'attempted':7,'completed':4,'failed':3},'population_note':'four fixed-geometry mechanism cases plus three failures; auxiliary controls/refinements are not additional population members'}
    raw['reference_hash']=canonical_hash(raw);validate_reference(raw);return raw


def validate_reference(raw):
    if raw['reference_hash']!=canonical_hash({k:v for k,v in raw.items() if k!='reference_hash'}):raise ValueError('reference identity mismatch')
    if raw['case_counts']!={'attempted':7,'completed':4,'failed':3} or len(raw['cases'])!=4 or {c['mode'] for c in raw['cases']}!=set(MODES):raise ValueError('case population incomplete')
    if raw['acceptance']!={'spectral_rtol':SPECTRAL_RTOL,'probability_atol':PROBABILITY_ATOL,'contrast_atol_V':CONTRAST_ATOL_V}:raise ValueError('acceptance criteria changed')
    sources=[];devices=[]
    for case in raw['cases']:
        owner=StructuralOpticalContext.from_dict(case['structural_context'])
        if owner.contract_hash!=case['structural_context_hash']:raise ValueError('structural source identity mismatch')
        devices.append(owner.thermal_resolution.device.to_dict());sources.append(TabulatedSpectrum.from_dict(case['source']).to_dict())
        for layer in case['optical_layers']:
            SpectralAbsorptionResult.from_dict(layer['absorption'])
        audit=case['spectral_audit']
        if [r['base_nodes'] for r in audit]!=list(GRIDS):raise ValueError('incomplete spectral refinement')
        for row in audit:
            summary=row['summary']
            for suffix in ('irradiance_W_m2','photon_flux_m2_s'):
                incident=summary['incident_'+suffix]
                if abs(incident-summary['absorbed_'+suffix]-summary['transmitted_'+suffix])>1e-12*incident:raise ValueError('whole-path balance failed')
        for key in ('fg_absorbed_irradiance_W_m2','fg_absorbed_photon_flux_m2_s'):
            values=[a['summary'][key] for a in audit]
            fine=abs(values[-1]-values[-2])/values[-1];coarse=abs(values[-2]-values[-3])/values[-1]
            if fine>SPECTRAL_RTOL or fine>coarse+1e-14:raise ValueError('spectral refinement failed')
        programs=case['programs']
        if [p['light']['steps'] for p in programs]!=list(STEPS):raise ValueError('incomplete temporal refinement')
        a,b=programs[-2:]
        if np.max(abs(np.asarray(a['light']['probabilities'])-np.asarray(b['light']['probabilities'])))>PROBABILITY_ATOL or abs(a['photo_contrast_V']-b['photo_contrast_V'])>CONTRAST_ATOL_V:raise ValueError('pulse refinement failed')
        for program in programs:
            for p in (program['light'],program['dark']):
                probs=np.asarray(p['probabilities'])
                if probs.shape!=(1,3,3) or not np.all(np.isfinite(probs)) or probs.min()<0 or np.max(abs(probs.sum(axis=2)-1))>1e-12 or p['read_probability_change']>1e-12:raise ValueError('probability/read audit failed')
    if any(s!=sources[0] for s in sources) or any(d!=devices[0] for d in devices):raise ValueError('mechanism cases must retain fixed source and geometry')
    if len(raw['failures'])!=3 or {f['case'] for f in raw['failures']}!={'strain_domain','radius_domain','temperature_domain'}:raise ValueError('failure population incomplete')
    expected=[('multiple_fg',2),('multiple_fg',3),('diameter',4.),('diameter',8.),('temperature',300.),('temperature',350.),('zero_capture',None)]
    actual=[(c['kind'],c.get('n_fgs',c.get('diameter_nm',c.get('temperature_K')))) for c in raw['controls']]
    if actual!=expected:raise ValueError('auxiliary controls incomplete')
    for control in raw['controls']:
        if 'structural_context' in control:StructuralOpticalContext.from_dict(control['structural_context'])
        if control['kind']=='zero_capture' and (control['zero_capture']['probabilities']!=control['dark']['probabilities'] or control['zero_capture']['read_vfb_V']!=control['dark']['read_vfb_V']):raise ValueError('zero capture control failed')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    raw=run_reference();args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(raw,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'case_counts':raw['case_counts'],'reference_hash':raw['reference_hash']}))
