# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Synthetic equal-power broadband/multispectral reference; no experimental qualification."""
from __future__ import annotations
import argparse
from dataclasses import replace
import json
import math
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from ncmemsim import DeviceBuilder,PhysicsModel,SimulationConfig,DeviceState
from ncmemsim._version import __version__
from ncmemsim.constants import PLANCK_J_S,LIGHT_SPEED_M_S,ELEMENTARY_CHARGE_C
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials import make_ge
from ncmemsim.photo import PhotoTransitionConfig,PhotoTransitionWeights
from ncmemsim.program_protocol import ProgramPulseReadProtocol
from ncmemsim.spectral_sources import SpectralEvidence,TabulatedSpectrum,DiscreteLineSpectrum
from ncmemsim.spectral_absorption import SpectralAbsorptionProfile
from ncmemsim.spectral_stack import SpectralStackLayer
from ncmemsim.spectral_context import build_spectral_simulation_context,SpectralSimulationContext,SpectralPulseProtocol,run_spectral_program_pulse_read
from ncmemsim.temperature_context import ThermalContext

GRIDS=(65,129,257)
STEPS=(16,32,64)
POWER_W_M2=1e6
DURATION_S=1e-7
SPECTRAL_RTOL=1e-3
PROBABILITY_ATOL=2e-3
READ_VFB_ATOL_V=1e-5
SCOPE=('Synthetic equal in-band power sources, bulk-Ge compact absorption, assumed passive/matrix optics, '
    'constant capture efficiency .1 and isothermal devices. No measured spectrum, calibrated device, '
    'wavelength-dependent capture, reflection/interference, confinement or yield claim. '
    'Combined electrical/optical charge is not attributed wholly to photons.')
EVIDENCE=SpectralEvidence('N5 synthetic diagnostic','examples/phase_n5_broadband_reference.py','ASSUMED',
    'canonical source/profile units',(),'declared numerical grids','unknown',SCOPE)


def build_resolution(n=1):
    device=DeviceBuilder.v2(n,name=f'n5-{n}fg',nc_material=make_ge(),nc_volume_fraction=.2,active_fraction=.1,fg_thickness_nm=6)
    for fg in device.floating_gates():fg.grid_points=3
    return ThermalContext.from_nominal(device,PhysicsModel.default(),SimulationConfig()).resolve(temperature_K=300)


def make_source(kind,nodes=257,*,enabled=True):
    if kind=='mono':return DiscreteLineSpectrum((1550.,),(POWER_W_M2,),EVIDENCE,enabled)
    if kind=='multispectral':return DiscreteLineSpectrum((1550.,1850.),(POWER_W_M2/2,POWER_W_M2/2),EVIDENCE,enabled)
    if kind!='broadband':raise ValueError('unsupported reference source')
    edges=[PLANCK_J_S*LIGHT_SPEED_M_S*1e9/(gap*ELEMENTARY_CHARGE_C) for gap in (.7985,.664-.027,.664+.027)]
    wavelengths=tuple(sorted(set([1500.+500*i/(nodes-1) for i in range(nodes)]+[x for x in edges if 1500<x<2000])))
    return TabulatedSpectrum(wavelengths,tuple(1. for _ in wavelengths),EVIDENCE,'relative_shape',POWER_W_M2,enabled)


def build_context(resolution,source,*,passive_loss=False,direction='gate_to_substrate',omit=False):
    passive=[]
    for layer in resolution.device.layers:
        if layer.role=='floating_gate':continue
        alpha=1e6 if passive_loss else 0.
        profile=SpectralAbsorptionProfile(layer.name,source.wavelength_nm,tuple(alpha for _ in source.wavelength_nm),
            layer.thickness_nm*1e-9,1500.,2000.,EVIDENCE)
        passive.append(SpectralStackLayer(profile,'passive','absorbing' if passive_loss else 'assumed_transparent'))
    return build_spectral_simulation_context(resolution,source,direction=direction,passive_layers=tuple(passive[1:] if omit else passive),
        wavelength_min_nm=1500.,wavelength_max_nm=2000.,evidence=EVIDENCE)


def probabilities(state):
    return np.stack([np.stack((fg.P0,fg.P1,fg.P2),axis=1) for fg in state.floating_gates])


def pulse(context,steps,*,efficiency=.1,dark=False):
    protocol=SpectralPulseProtocol(ProgramPulseReadProtocol(2.,DURATION_S,0.,DURATION_S/steps),PhotoTransitionWeights())
    if dark:
        simulator=context.create_simulator();initial=DeviceState.empty_for_device(simulator.device)
        program=simulator.relax_voltage(initial,2.,DURATION_S,DURATION_S/steps,occupancy_integrator='backward_euler')
        read=simulator.relax_voltage(program['state'],0.,0.)
    else:
        run=run_spectral_program_pulse_read(context,protocol,photo_config=PhotoTransitionConfig(efficiency))
        program=run['program'];read=run['read']
    p=probabilities(program['state']);r=probabilities(read['state'])
    return {'steps':steps,'protocol':protocol.to_dict(),'capture_efficiency':efficiency,'dark':dark,
        'probabilities':p.tolist(),'read_vfb_V':float(read['vfb_V']),'qfg_by_fg_C_m2':program['qfg_by_fg_C_m2'].tolist(),
        'absorbed_photon_flux_by_fg_m2_s':program['absorbed_photon_flux_by_fg_m2_s'].tolist(),
        'photo_transition_rate_by_fg_s':program['photo_transition_rate_by_fg_s'].tolist(),
        'read_max_probability_change':float(np.max(abs(p-r))),
        'maximum_probability_mass_error':float(np.max(abs(p.sum(axis=2)-1))),
        'minimum_probability':float(p.min())}


def run_reference():
    cases=[];controls=[]
    for n in (1,2,3):
        resolution=build_resolution(n)
        for kind in ('mono','multispectral','broadband'):
            context=build_context(resolution,make_source(kind))
            optical=[]
            for grid in GRIDS if kind=='broadband' else (None,):
                c=build_context(resolution,make_source(kind,grid or 257))
                optical.append({'base_grid_nodes':grid,'actual_nodes':len(c.optical_result.source.wavelength_nm),
                    'summary':c.optical_result.projection['summary']})
            runs=[]
            for steps in STEPS:
                light=pulse(context,steps);dark=pulse(context,steps,dark=True)
                runs.append({'light':light,'dark':dark,'photo_contrast_V':light['read_vfb_V']-dark['read_vfb_V']})
            cases.append({'n_fgs':n,'source_kind':kind,'context':context.to_dict(),'context_hash':context.contract_hash,
                'spectral_grid_audit':optical,'programs':runs})
        context=build_context(resolution,make_source('broadband'))
        zero=pulse(context,64,efficiency=0);dark=pulse(context,64,dark=True)
        disabled=pulse(build_context(resolution,make_source('broadband',enabled=False)),64)
        lossy=build_context(resolution,make_source('broadband'),passive_loss=True)
        controls.append({'n_fgs':n,'zero_capture':zero,'dark':dark,'disabled':disabled,
            'passive_loss_summary':lossy.optical_result.projection['summary'],
            'transparent_summary':context.optical_result.projection['summary']})
    from examples.phase_m4_ge_temperature_reference import build_context as thermal_context
    thermal=[]
    for t in (300.,350.):
        resolution=thermal_context().resolve(temperature_K=t)
        context=build_context(resolution,make_source('broadband'))
        thermal.append({'device_temperature_K':t,'source':context.optical_result.source.to_dict(),
            'resolved_context':resolution.to_dict(),'optical_summary':context.optical_result.projection['summary']})
    failures=[]
    for name in ('unsupported_domain','incomplete_path'):
        try:
            source=DiscreteLineSpectrum((1499.,),(POWER_W_M2,),EVIDENCE) if name=='unsupported_domain' else make_source('mono')
            build_context(build_resolution(),source,omit=name=='incomplete_path')
        except ValueError as exc:failures.append({'case':name,'status':'failed','error_type':'ValueError','message':str(exc)})
        else:raise AssertionError('deliberate failure did not fail')
    result={'schema_version':'n5-broadband-reference-v1','software_version':__version__,'scope':SCOPE,
        'implementation_baseline':'80c8327d9e6d8bf748c883b744b64fe682b5c7e8',
        'identity_note':'N5 development reference; package version is retained until N7, not published-v1.4 runtime evidence',
        'assumptions':{'source':'ASSUMED','capture':'ASSUMED','passive_optics':'ASSUMED','material_amplitudes':'ASSUMED'},
        'acceptance':{'spectral_rtol':SPECTRAL_RTOL,'probability_atol':PROBABILITY_ATOL,'read_vfb_atol_V':READ_VFB_ATOL_V},
        'cases':cases,'controls':controls,'thermal_source_controls':thermal,'failures':failures,
        'case_counts':{'attempted':11,'completed':9,'failed':2}}
    result['reference_hash']=canonical_hash(result)
    validate_reference(result)
    return result


def validate_reference(result):
    json.dumps(result,allow_nan=False)
    raw=deepcopy_reference(result);digest=raw.pop('reference_hash')
    if canonical_hash(raw)!=digest:raise ValueError('reference integrity mismatch')
    if result['case_counts']!={'attempted':11,'completed':9,'failed':2} or result['acceptance']!={'spectral_rtol':SPECTRAL_RTOL,'probability_atol':PROBABILITY_ATOL,'read_vfb_atol_V':READ_VFB_ATOL_V}:
        raise ValueError('attempted population or acceptance criteria changed')
    if {(x['n_fgs'],x['source_kind']) for x in result['cases']}!={(n,k) for n in (1,2,3) for k in ('mono','multispectral','broadband')} or len(result['cases'])!=9:
        raise ValueError('incomplete case matrix')
    for case in result['cases']:
        context=SpectralSimulationContext.from_dict(case['context'])
        if context.contract_hash!=case['context_hash']:raise ValueError('context identity mismatch')
        if abs(context.optical_result.source.in_band_irradiance_W_m2/POWER_W_M2-1)>1e-14:raise ValueError('source normalization mismatch')
        audit=case['spectral_grid_audit']
        if case['source_kind']=='broadband':
            if [x['base_grid_nodes'] for x in audit]!=list(GRIDS):raise ValueError('incomplete spectral refinement')
            for key in ('fg_absorbed_irradiance_W_m2','fg_absorbed_photon_flux_m2_s'):
                fine=abs(audit[-1]['summary'][key]-audit[-2]['summary'][key])/audit[-1]['summary'][key]
                coarse=abs(audit[-2]['summary'][key]-audit[-3]['summary'][key])/audit[-1]['summary'][key]
                if fine>SPECTRAL_RTOL or fine>coarse+1e-14:raise ValueError('spectral refinement failed')
        if [x['light']['steps'] for x in case['programs']]!=list(STEPS):raise ValueError('incomplete temporal refinement')
        a,b=case['programs'][-2:]
        if np.max(abs(np.asarray(a['light']['probabilities'])-np.asarray(b['light']['probabilities'])))>PROBABILITY_ATOL or abs(a['photo_contrast_V']-b['photo_contrast_V'])>READ_VFB_ATOL_V:
            raise ValueError('pulse refinement failed')
        for program in case['programs']:
            for run in (program['light'],program['dark']):
                if run['minimum_probability']<0 or run['maximum_probability_mass_error']>1e-12 or run['read_max_probability_change']>1e-12:raise ValueError('probability/read audit failed')
                p=np.asarray(run['probabilities'])
                if p.shape!=(case['n_fgs'],3,3) or not np.all(np.isfinite(p)) or p.min()<0 or np.max(abs(p.sum(axis=2)-1))>1e-12:
                    raise ValueError('invalid stored probabilities')
    if len(result['controls'])!=3 or {x['n_fgs'] for x in result['controls']}!={1,2,3}:raise ValueError('control matrix incomplete')
    for control in result['controls']:
        for run in (control['zero_capture'],control['disabled']):
            if run['probabilities']!=control['dark']['probabilities'] or run['read_vfb_V']!=control['dark']['read_vfb_V']:raise ValueError('dark/zero-capture compatibility failed')
        if control['passive_loss_summary']['fg_absorbed_photon_flux_m2_s']>=control['transparent_summary']['fg_absorbed_photon_flux_m2_s']:raise ValueError('passive-loss control failed')
    if len(result['failures'])!=2 or {x['case'] for x in result['failures']}!={'unsupported_domain','incomplete_path'}:raise ValueError('failure population incomplete')
    if result['thermal_source_controls'][0]['source']!=result['thermal_source_controls'][1]['source']:raise ValueError('source/device temperature separation failed')


def deepcopy_reference(result):
    return json.loads(json.dumps(result,allow_nan=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=run_reference();args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'case_counts':result['case_counts'],'reference_hash':result['reference_hash']}))


if __name__=='__main__':main()
