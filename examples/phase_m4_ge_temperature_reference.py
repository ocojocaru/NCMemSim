# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Conditional bulk-Ge thermal optics; no multi-temperature absorption calibration."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np
from ncmemsim import DeviceBuilder, PhysicsModel, Simulator
from ncmemsim._version import __version__
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials import make_ge, make_gesn
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.temperature import (ThermalEvidence, TemperatureDomain,
    reviewed_varshni_coefficients, profile_from_reviewed_record)
from ncmemsim.materials.optics.near_edge import GeSnNearEdgeReferenceModel
from ncmemsim.optics import LightSource, evaluate_floating_gate_optical_absorption
from ncmemsim.photo import PhotoTransitionConfig, PhotoTransitionWeights
from ncmemsim.program_protocol import ProgramPulseReadProtocol, run_program_pulse_read
from ncmemsim.electro_optical_program_protocol import (
    ElectroOpticalProgramPulseReadProtocol, run_electro_optical_program_pulse_read)
from ncmemsim.simulator import SimulationConfig
from ncmemsim.temperature_context import ThermalContext, OpticalThermalBinding, OpticalThermalMode

TEMPERATURES_K = (250., 300., 350.)
WAVELENGTHS_NM = (1450., 1500., 1550., 1600., 1700., 1800., 1850., 1900., 2000., 2200.)
PROGRAM_WAVELENGTHS_NM = (1550., 1850.)
STEPS = (32, 64, 128)
POWER_W_M2 = 1e6
DURATION_S = 1e-6
CAPTURE_EFFICIENCY = .1
PROBABILITY_ATOL = 2e-3
CONTRAST_ATOL_V = 1e-5
SCOPE = ('Conditional unstrained bulk-Ge gap laws applied to a compact nanocrystal layer; '
    'synthetic geometry, illumination and capture efficiency. Absorption amplitudes, '
    'Urbach tail, phonon energy and barriers held constant. No experimental thermal '
    'absorption calibration, confinement, broadband propagation or GeSn thermal qualification.')


def build_context(mode=OpticalThermalMode.COUPLED, *, enabled=True):
    device = DeviceBuilder.v2(1, name='m4-bulk-ge-optical-reference', nc_material=make_ge(),
        nc_volume_fraction=.2, active_fraction=.1, fg_thickness_nm=6)
    device.floating_gates()[0].grid_points = 3
    device.metadata['scientific_scope'] = SCOPE
    evidence = ThermalEvidence('Explicit M4 numerical assumption',
        '250-350 K diagnostic window; inherited 300 K bulk-Ge anchors', ParameterStatus.ASSUMED, SCOPE)
    def profile(index, anchor):
        record = reviewed_varshni_coefficients()[index]
        return profile_from_reviewed_record(record, name='m4-'+record.name,
            domain=TemperatureDomain(record.material,250,350,0,0,evidence),
            reference_temperature_K=300, reference_gap_eV=anchor, reference_evidence=evidence)
    binding = OpticalThermalBinding('FG1',mode,profile(1,.7985),profile(2,.664))
    return ThermalContext.from_nominal(device,PhysicsModel.default(),SimulationConfig(),
        enabled=enabled,optical_bindings=(binding,))


def optical_record(resolution, wavelength):
    point = evaluate_floating_gate_optical_absorption(LightSource.led(wavelength,POWER_W_M2),
        resolution.device.get_layer('FG1'),optical_model=resolution.optical_model('FG1'))
    result = {key:value for key,value in asdict(point).items() if key!='provenance'}
    incident = point.incident_photon_flux_m2_s
    result['photon_budget_relative_error'] = abs(incident-point.absorbed_photon_flux_m2_s-
        point.transmitted_photon_flux_m2_s)/incident
    return result


def probabilities(state):
    fg=state.floating_gates[0]
    return np.stack((fg.P0,fg.P1,fg.P2),axis=1)


def program_record(resolution, wavelength, steps, *, original=False, efficiency=CAPTURE_EFFICIENCY):
    if type(steps) is not int or steps<1:
        raise ValueError('steps must be a positive integer')
    def simulator():
        return Simulator(resolution.device,resolution.physics,resolution.simulation_config) if original else resolution.create_simulator()
    electrical=ProgramPulseReadProtocol(3,DURATION_S,0,DURATION_S/steps)
    protocol=ElectroOpticalProgramPulseReadProtocol(electrical,LightSource.led(wavelength,POWER_W_M2),PhotoTransitionWeights())
    config=PhotoTransitionConfig(efficiency)
    light=run_electro_optical_program_pulse_read(simulator(),protocol,photo_config=config)
    dark=run_program_pulse_read(simulator(),electrical)
    p=probabilities(light.programmed_state)
    return {'steps':steps,'protocol':protocol.to_dict(),'photo_config':asdict(config),
        'delta_vfb_V':light.delta_vfb_V,'dark_delta_vfb_V':dark.delta_vfb_V,
        'photo_contrast_V':light.delta_vfb_V-dark.delta_vfb_V,
        'qfg_C_m2':light.qfg_C_m2,'mean_occupation':light.mean_occupation,
        'absorbed_photon_flux_m2_s':light.absorbed_photon_flux_m2_s,
        'photo_transition_rate_s':light.photo_transition_rate_s,
        'probabilities':p.tolist(),'read_max_probability_change':float(np.max(abs(p-probabilities(light.read_state)))),
        'max_probability_mass_error':float(np.max(abs(p.sum(axis=1)-1))),
        'minimum_probability':float(p.min())}


def near_edge_reference_limits():
    # This separate model remains a room-temperature reference, never the thermal evaluator.
    model=GeSnNearEdgeReferenceModel()
    rows=[]
    for x,w in ((0.,1550.),(.05,2000.),(.1,2500.),(.15,2000.),(.05,1400.)):
        point=model.evaluate(make_gesn(x),w)
        rows.append({'sn_fraction':x,'wavelength_nm':w,'temperature_K':300.,
            'absorption_coefficient_m_inv':point.absorption_coefficient_m_inv,
            'domain_status':point.domain_status.value})
    return rows


def run_reference():
    cases=[]
    for t in TEMPERATURES_K:
        for mode in OpticalThermalMode:
            context=build_context(mode)
            resolution=context.resolve(temperature_K=t)
            programs=[]
            for w in PROGRAM_WAVELENGTHS_NM:
                runs=[program_record(resolution,w,n) for n in STEPS]
                programs.append({'wavelength_nm':w,'runs':runs,
                    'finest_probability_error':float(np.max(abs(np.asarray(runs[-1]['probabilities'])-np.asarray(runs[-2]['probabilities'])))),
                    'finest_photo_contrast_error_V':abs(runs[-1]['photo_contrast_V']-runs[-2]['photo_contrast_V'])})
            cases.append({'temperature_K':t,'mode':mode.value,'context':context.to_dict(),
                'resolved_context':resolution.to_dict(),'resolution_hash':resolution.context_hash,
                'optical':[optical_record(resolution,w) for w in WAVELENGTHS_NM],'programs':programs})
    controls=[]
    for t in TEMPERATURES_K:
        disabled=build_context(enabled=False).resolve(temperature_K=t)
        legacy=build_context(OpticalThermalMode.LEGACY).resolve(temperature_K=t)
        controls.append({'temperature_K':t,
            'disabled':program_record(disabled,1550,64),
            'legacy':program_record(legacy,1550,64),
            'original':program_record(legacy,1550,64,original=True),
            'zero_capture':program_record(build_context().resolve(temperature_K=t),1550,64,efficiency=0)})
    result={'schema':'m4-ge-temperature-reference-v1','software_version':__version__,'scope':SCOPE,
        'case_counts':{'attempted':12,'completed':12,'failed':0},'cases':cases,'controls':controls,
        'near_edge_300K_reference':near_edge_reference_limits(),
        'limits':{'probability_atol':PROBABILITY_ATOL,'photo_contrast_atol_V':CONTRAST_ATOL_V,
            'photon_budget_relative_error':1e-12},
        'statuses':{'temperature_window':'ASSUMED','gap_coefficients':'LITERATURE_FITTED',
            'anchored_gap_values':'DERIVED','thermal_absorption':'DERIVED','capture_efficiency':'ASSUMED'}}
    validate_reference(result)
    result['reference_hash']=canonical_hash(result)
    return result


def validate_reference(result):
    json.dumps(result,allow_nan=False)
    expected={(t,m.value) for t in TEMPERATURES_K for m in OpticalThermalMode}
    if len(result['cases'])!=12 or {(r['temperature_K'],r['mode']) for r in result['cases']}!=expected:
        raise ValueError('incomplete or duplicated thermal case grid')
    for case in result['cases']:
        if [r['wavelength_nm'] for r in case['optical']]!=list(WAVELENGTHS_NM):
            raise ValueError('incomplete wavelength audit')
        for row in case['optical']:
            incident=row['incident_photon_flux_m2_s']
            residual=abs(incident-row['absorbed_photon_flux_m2_s']-row['transmitted_photon_flux_m2_s'])/incident if incident>0 else float('inf')
            if residual>1e-12 or row['photon_budget_relative_error']>1e-12 or not 0<=row['absorption_fraction']<=1:
                raise ValueError('photon accounting failed')
        if [r['wavelength_nm'] for r in case['programs']]!=list(PROGRAM_WAVELENGTHS_NM):
            raise ValueError('incomplete programming audit')
        for program in case['programs']:
            runs=program['runs']
            probability_error=float(np.max(abs(np.asarray(runs[-1]['probabilities'])-np.asarray(runs[-2]['probabilities']))))
            contrast_error=abs(runs[-1]['photo_contrast_V']-runs[-2]['photo_contrast_V'])
            if probability_error>PROBABILITY_ATOL or contrast_error>CONTRAST_ATOL_V or program['finest_probability_error']>PROBABILITY_ATOL or program['finest_photo_contrast_error_V']>CONTRAST_ATOL_V:
                raise ValueError('program refinement failed')
            if [r['steps'] for r in program['runs']]!=list(STEPS):
                raise ValueError('incomplete step refinement')
            for row in program['runs']:
                if row['read_max_probability_change']>1e-12 or row['max_probability_mass_error']>1e-12 or row['minimum_probability']<0:
                    raise ValueError('probability/read audit failed')
    if len(result['controls'])!=3 or {r['temperature_K'] for r in result['controls']}!=set(TEMPERATURES_K):
        raise ValueError('incomplete legacy control grid')
    for control in result['controls']:
        if control['disabled']!=control['legacy'] or control['legacy']!=control['original']:
            raise ValueError('legacy compatibility failed')
        if abs(control['zero_capture']['photo_contrast_V'])>1e-14:
            raise ValueError('zero capture control failed')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('results/m4-ge'))
    args=parser.parse_args()
    result=run_reference()
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'reference.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(SCOPE)
    print(result['reference_hash'])


if __name__=='__main__':
    main()
