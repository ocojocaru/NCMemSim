# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Conditional Si thermal reference; synthetic electrical parameters, no lifetime fit.

Run: python examples/phase_m3_si_temperature_reference.py --output results/m3-si
"""
from __future__ import annotations
import argparse
from dataclasses import asdict, replace
import json
import math
import platform
from pathlib import Path
import numpy as np
from ncmemsim import DeviceBuilder, DeviceState, PhysicsModel, Simulator
from ncmemsim._version import __version__
from ncmemsim.constants import BOLTZMANN_J_K, ELEMENTARY_CHARGE_C
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials import make_ge
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.temperature import (
    ThermalEvidence, ThermalMaterial, TemperatureDomain, CarrierStatisticsDomain,
    IntrinsicDensityProfile, reviewed_varshni_coefficients, profile_from_reviewed_record,
)
from ncmemsim.temperature_context import ThermalContext, SemiconductorThermalMode
from ncmemsim.program_protocol import ProgramPulseReadProtocol, run_program_pulse_read
from ncmemsim.retention import RetentionConfig, RetentionSolver
from ncmemsim.simulator import SimulationConfig

TEMPERATURES_K = (250.0, 300.0, 350.0)
AUDIT_STEPS = (64, 128, 256)
REFERENCE_STEPS = 128
PROGRAM_TIME_S = 5e-7
RETENTION_TIME_S = 1e-3
OCCUPATION_ATOL = 2e-3
PROBABILITY_ATOL = 1e-12
CHARGE_BUDGET_RTOL = 1e-10
PROGRAM_CONTRAST_ATOL_V = 1e-5
SCOPE = ('Conditional isothermal compact-model comparison; synthetic assumed geometry, '
         'barriers and kinetic frequencies. No experimental calibration, universal '
         'retention lifetime, Arrhenius acceleration or manufacturing-yield inference.')


def build_nominal():
    device = DeviceBuilder.v2(1, name='m3-si-substrate-ge-fg',
        nc_material=make_ge(phi_barrier_prog_eV=.65, phi_barrier_erase_eV=.65),
        tunnel_sio2_nm=3, nc_volume_fraction=.2, active_fraction=.1, fg_thickness_nm=6)
    device.floating_gates()[0].grid_points = 7
    device.metadata['scientific_scope'] = SCOPE
    physics = PhysicsModel.default()
    physics.occupancy.config = replace(physics.occupancy.config, nu0_Hz=1e7, nu1_Hz=5e7, nu2_Hz=3e7)
    return device, physics, SimulationConfig()


def build_context(mode=SemiconductorThermalMode.COUPLED, *, enabled=True):
    device, physics, config = build_nominal()
    evidence = ThermalEvidence('Explicit M3 numerical assumption',
        '250-350 K diagnostic window; inherited 300 K semiconductor anchors',
        ParameterStatus.ASSUMED, SCOPE)
    gap = profile_from_reviewed_record(reviewed_varshni_coefficients()[0], name='m3-si-gap',
        domain=TemperatureDomain(ThermalMaterial.SILICON, 250, 350, 0, 0, evidence),
        reference_temperature_K=300, reference_gap_eV=1.12, reference_evidence=evidence)
    ni = IntrinsicDensityProfile('m3-si-ni', gap, 1e16, evidence,
        CarrierStatisticsDomain(1e20, 1e24, 10, evidence))
    return ThermalContext.from_nominal(device, physics, config, enabled=enabled,
        semiconductor_mode=mode, substrate_gap=gap, intrinsic_density=ni)


def _steps(value):
    if type(value) is not int or value < 1:
        raise ValueError('steps must be a positive integer')
    return value


def _probabilities(state):
    fg = state.floating_gates[0]
    return np.stack((fg.P0, fg.P1, fg.P2), axis=1)


def _state_record(state):
    return {'time_s': float(state.time_s), 'probabilities': _probabilities(state).tolist(),
        'max_probability_mass_error': float(np.max(np.abs(_probabilities(state).sum(axis=1)-1))),
        'minimum_probability': float(np.min(_probabilities(state)))}


def protocol(steps=REFERENCE_STEPS):
    return ProgramPulseReadProtocol(3, PROGRAM_TIME_S, 0, PROGRAM_TIME_S/_steps(steps))


def retention_config(steps=REFERENCE_STEPS):
    dt = RETENTION_TIME_S/_steps(steps)
    return RetentionConfig(gate_voltage_V=0, total_time_s=RETENTION_TIME_S,
        initial_dt_s=dt, maximum_dt_s=dt, growth_factor=2, output_points=5,
        occupancy_integrator='backward_euler', stop_at_quasi_equilibrium=False)


def _run(simulator, steps):
    programmed = run_program_pulse_read(simulator, protocol(steps))
    held = RetentionSolver(simulator, retention_config(steps)).run(programmed.programmed_state)
    physics, device = simulator.physics, simulator.device
    fg = device.floating_gates()[0]
    s = physics.electrostatics.semiconductor
    return {'program_protocol': protocol(steps).to_dict(), 'retention_config': asdict(retention_config(steps)),
        'semiconductor': asdict(s), 'fermi_potential_V': physics.electrostatics.fermi_potential(device),
        'flatband_zero_V': physics.electrostatics.flatband_zero(device),
        'gamma_c': physics.occupancy.gamma_c(fg.nc_diameter_nm*1e-9, device.temperature_K),
        'program': {'mean_occupation': programmed.mean_occupation, 'qfg_C_m2': programmed.qfg_C_m2,
            'delta_vfb_V': programmed.delta_vfb_V, 'initial': _state_record(programmed.initial_state),
            'read_max_probability_change': float(np.max(np.abs(_probabilities(programmed.read_state)-_probabilities(programmed.programmed_state)))),
            'final': _state_record(programmed.programmed_state), 'read': _state_record(programmed.read_state)},
        'retention': {'time_s': held.time_s.tolist(), 'qfg_C_m2': held.qfg_C_m2.tolist(),
            'delta_vfb_V': held.delta_vfb_V.tolist(), 'mean_occupation': held.mean_occupation_by_fg[:,0].tolist(),
            'charge_retention_fraction': held.total_charge_retention_fraction.tolist(),
            'final': _state_record(held.final_state)},
        'cox_F_m2': device.equivalent_dielectric_capacitance_F_m2()}


def evaluate_case(context, temperature_K, steps=REFERENCE_STEPS):
    _steps(steps)
    resolution = context.resolve(temperature_K=temperature_K)
    return {'resolution': resolution.to_dict(), 'resolution_hash': resolution.context_hash,
            'observations': _run(resolution.create_simulator(), steps)}


def charge_budget_audit(resolution, steps=REFERENCE_STEPS):
    """Independent discrete reservoir budget, including every occupancy update.

    Program uses pre-step Euler flux; uniform retention uses post-step implicit
    flux with frozen pre-step rates. No closed-system charge conservation is claimed.
    """
    steps = _steps(steps)
    sim = resolution.create_simulator()
    device, physics = sim.device, sim.physics
    fg = device.floating_gates()[0]
    x, dx = physics.occupancy.grid(fg)
    weights = physics.occupancy.density_profile(fg,x)*dx
    index = device.layers.index(fg)
    base = sum(l.thickness_nm*1e-9 for l in device.layers[index+1:]
        if l.role in {'tunnel_dielectric','native_oxide','interlayer_dielectric'})
    state = DeviceState.empty_for_device(device)
    results = []
    for name, voltage, duration, integrator in (('program',3,PROGRAM_TIME_S,'explicit_euler'),
            ('uniform_retention',0,RETENTION_TIME_S,'backward_euler')):
        dt = duration/steps
        initial_charge = ELEMENTARY_CHARGE_C*float(np.dot(weights,state.floating_gates[0].occupation))
        predicted_increments = []
        mass_errors, minima, unclipped_minima = [], [], []
        for _ in range(steps):
            before = _probabilities(state)
            q = ELEMENTARY_CHARGE_C*float(np.dot(weights,state.floating_gates[0].occupation))
            electro = physics.electrostatics.evaluate(device,voltage,q,sim.config.qfix_C_m2,sim.config.qit_C_m2)
            rates = physics.occupancy.rates(fg,x,electro.veff_V,base,device.temperature_K)
            out = sim.relax_voltage(state,voltage,dwell_time_s=dt,internal_dt_s=dt,occupancy_integrator=integrator)
            state = out['state']; after = _probabilities(state)
            p = before if integrator=='explicit_euler' else after
            net_electron_rate = rates.r01*p[:,0] + rates.r12*p[:,1] - rates.r21*p[:,2] - rates.r10*p[:,1]
            # Existing compact charge uses occupation=0.5*(P1+2*P2).
            predicted_increments.append(0.5*ELEMENTARY_CHARGE_C*dt*float(np.dot(weights,net_electron_rate)))
            mass_errors.append(float(np.max(np.abs(after.sum(axis=1)-1))))
            minima.append(float(np.min(after)))
            if integrator=='explicit_euler':
                derivative = np.stack((-rates.r01*before[:,0]+rates.r10*before[:,1],
                    rates.r01*before[:,0]-(rates.r10+rates.r12)*before[:,1]+rates.r21*before[:,2],
                    rates.r12*before[:,1]-rates.r21*before[:,2]),axis=1)
                unclipped_minima.append(float(np.min(before+dt*derivative)))
        final_charge = ELEMENTARY_CHARGE_C*float(np.dot(weights,state.floating_gates[0].occupation))
        integrated = math.fsum(predicted_increments)
        residual = final_charge-initial_charge-integrated
        scale = max(abs(initial_charge),abs(final_charge),abs(integrated),np.finfo(float).tiny)
        results.append({'stage':name,'steps':steps,'integrator':integrator,'initial_qfg_C_m2':initial_charge,
            'final_qfg_C_m2':final_charge,'integrated_substrate_charge_C_m2':integrated,
            'charge_budget_residual_C_m2':residual,'charge_budget_relative_residual':abs(residual)/scale,
            'max_probability_mass_error':max(mass_errors),'minimum_probability':min(minima),
            'minimum_unclipped_euler_probability':min(unclipped_minima) if unclipped_minima else None,
            'final':_state_record(state)})
    return results


def run_reference():
    cases = []
    for temperature in TEMPERATURES_K:
        for mode in SemiconductorThermalMode:
            context = build_context(mode)
            result = evaluate_case(context,temperature)
            audits = {n: result if n==REFERENCE_STEPS else evaluate_case(context,temperature,n) for n in AUDIT_STEPS}
            last, previous = audits[AUDIT_STEPS[-1]]['observations'],audits[AUDIT_STEPS[-2]]['observations']
            errors = {stage:float(np.max(np.abs(np.asarray(last[stage]['final']['probabilities'])-
                np.asarray(previous[stage]['final']['probabilities'])))) for stage in ('program','retention')}
            coarse = {stage:float(np.max(np.abs(np.asarray(audits[64]['observations'][stage]['final']['probabilities'])-
                np.asarray(previous[stage]['final']['probabilities'])))) for stage in ('program','retention')}
            budget = charge_budget_audit(context.resolve(temperature_K=temperature))
            uniform_error = float(np.max(np.abs(np.asarray(budget[-1]['final']['probabilities'])-
                np.asarray(result['observations']['retention']['final']['probabilities']))))
            result.update(temperature_K=temperature, mode=mode.value, charge_budget=budget,
                uniform_retention_vs_solver_max_probability_error=uniform_error,
                timestep_audit={'steps':list(AUDIT_STEPS),'endpoint_only':True,
                    'finest_pair_max_probability_error':errors,'coarser_pair_max_probability_error':coarse,
                    'absolute_probability_tolerance':OCCUPATION_ATOL,
                    'runs':[{'steps':n,'program_delta_vfb_V':audits[n]['observations']['program']['delta_vfb_V'],
                        'program_mean_occupation':audits[n]['observations']['program']['mean_occupation'],
                        'retention_final_mean_occupation':audits[n]['observations']['retention']['mean_occupation'][-1],
                        'retention_output_times_s':audits[n]['observations']['retention']['time_s']} for n in AUDIT_STEPS]})
            cases.append(result)
    for case in cases:
        legacy = next(c for c in cases if c['temperature_K']==case['temperature_K'] and c['mode']=='legacy')
        contrasts = [a['program_delta_vfb_V']-b['program_delta_vfb_V'] for a,b in zip(
            case['timestep_audit']['runs'], legacy['timestep_audit']['runs'], strict=True)]
        case['program_thermal_contrast_audit'] = {'contrast_at_each_step_count_V':contrasts,
            'finest_pair_contrast_error_V':abs(contrasts[-1]-contrasts[-2]),
            'absolute_contrast_tolerance_V':PROGRAM_CONTRAST_ATOL_V}
    disabled = [evaluate_case(build_context(enabled=False),t) for t in TEMPERATURES_K]
    originals = []
    for t in TEMPERATURES_K:
        device,physics,config = build_nominal(); device.temperature_K=t
        originals.append({'temperature_K':t,'observations':_run(Simulator(device,physics,config),REFERENCE_STEPS)})
    result={'schema_version':'m3-si-temperature-reference-v1','scope':SCOPE,'software_version':__version__,
        'runtime':{'python':platform.python_version(),'numpy':np.__version__},
        'case_counts':{'attempted':len(cases),'completed':len(cases),'failed':0},
        'charge_convention':'Legacy normalized occupancy: QFG=q*sum(n_eff*dx*0.5*(P1+2P2)); reservoir flux uses the same half factor.',
        'temperatures_K':list(TEMPERATURES_K),'reference_steps':REFERENCE_STEPS,
        'parameter_status':{'operating_domain':'assumed','geometry_barriers_kinetics':'assumed',
            'thermal_coefficients':'literature_fitted','anchored_values':'derived'},
        'cases':cases,'disabled_controls':disabled,'original_simulator_controls':originals,
        'limits':{'occupation_atol':OCCUPATION_ATOL,'probability_atol':PROBABILITY_ATOL,
            'charge_budget_rtol':CHARGE_BUDGET_RTOL,
            'retention_budget':'Independent uniform-step reservoir audit; RetentionSolver uses clipped output-aligned steps.'}}
    validate_reference(result)
    result['reference_hash']=canonical_hash(result)
    return result


def validate_reference(result):
    """Check numerical acceptance, separate from physical applicability."""
    expected={(t,m.value) for t in TEMPERATURES_K for m in SemiconductorThermalMode}
    rows=[(r['temperature_K'],r['mode']) for r in result['cases']]
    if len(rows)!=len(expected) or set(rows)!=expected:
        raise ValueError('M3 complete diagnostic grid required')
    for case in result['cases']:
        if case['program_thermal_contrast_audit']['finest_pair_contrast_error_V']>PROGRAM_CONTRAST_ATOL_V:
            raise ValueError('M3 paired program contrast acceptance failed')
        if case['observations']['program']['read_max_probability_change']>PROBABILITY_ATOL:
            raise ValueError('M3 nondestructive read acceptance failed')
        if case['uniform_retention_vs_solver_max_probability_error']>OCCUPATION_ATOL:
            raise ValueError('M3 independent retention endpoint acceptance failed')
        for stage, error in case['timestep_audit']['finest_pair_max_probability_error'].items():
            if error>OCCUPATION_ATOL: raise ValueError('M3 timestep acceptance failed: '+stage)
        for row in case['charge_budget']:
            if (row['charge_budget_relative_residual']>CHARGE_BUDGET_RTOL
                    or row['max_probability_mass_error']>PROBABILITY_ATOL or row['minimum_probability']<0
                    or (row['minimum_unclipped_euler_probability'] is not None and row['minimum_unclipped_euler_probability']<0)):
                raise ValueError('M3 reservoir/probability acceptance failed')
    json.dumps(result,allow_nan=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=run_reference();args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'reference.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print('M3 numerical acceptance PASS; conditional scope:',SCOPE)
    print('Reference hash:',result['reference_hash'])


if __name__=='__main__': main()
