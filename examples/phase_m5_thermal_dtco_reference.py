# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Conditional thermal DTCO with paired stored density draws, no yield claim."""
from __future__ import annotations
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from examples.phase_l3_tat_density_variability import (build_reference, workflow_settings,
    _electrons, LINK_ID, SPECIES_NAME, NOMINAL_DENSITY_M3, OCCUPATION_ATOL)
from examples.phase_m3_si_temperature_reference import build_context as si_template
from examples.phase_m4_ge_temperature_reference import build_context as optical_template
from ncmemsim import DeviceState, PhysicsModel
from ncmemsim.transport import TransportConfig, TransportEngine, TransportMechanism
from ncmemsim.temperature_context import ThermalContext
from ncmemsim.thermal_dtco import resolve_thermal_candidate
from ncmemsim.dtco import (DesignVariable, DesignVariableRole, ParameterBinding, BindingScope,
    ExperimentSpec, iter_cartesian_points, apply_experiment_design_point, run_cartesian_sweep,
    MetricAnalysisSpec, MetricDefinition, MetricConstraint, ConstraintOperator, ObjectiveDirection,
    analyze_sweep, analyze_pareto)
from ncmemsim.ensemble import (EnsembleScalarDefinition, EnsembleScalarKind, EnsembleConstraint, EnsembleObjective)
from ncmemsim.ensemble.model_contracts import ModelVariabilitySpec, trap_density_binding
from ncmemsim.ensemble.model_sampling import generate_model_sample_manifest
from ncmemsim.ensemble.model_execution import execute_model_sample_manifest, apply_model_sample_to_context
from ncmemsim.ensemble.model_analysis import analyze_model_execution
from ncmemsim.ensemble.model_dtco import ModelDTCOStudy, evaluate_model_eligibility, analyze_model_pareto
from ncmemsim.hashing import canonical_hash

TEMPERATURES_K=(250.,300.,350.,400.)
STEPS=(16,32)
SAMPLE_COUNT=8
SCOPE=('Conditional Si/Ge thermal DTCO with synthetic paired TAT-density draws; '
    'fixed initial electrostatic field and closed inter-FG redistribution, no full '
    'retention, temperature-calibrated TAT law, sampling convergence or manufacturing yield.')


def template_for(device):
    si=si_template(); optical=optical_template().optical_bindings[0]
    physics=PhysicsModel.default()
    physics.transport=TransportEngine(physics.tunneling,TransportConfig(**workflow_settings()['transport_config']))
    return ThermalContext.from_nominal(device,physics,enabled=True,
        semiconductor_mode=si.semiconductor_mode,substrate_gap=si.substrate_gap,
        intrinsic_density=si.intrinsic_density,
        optical_bindings=tuple(replace(optical,layer_name=fg.name) for fg in device.floating_gates()))


def evaluate_candidate(template,device,model,*,steps=16):
    if type(steps) is not int or steps<1:
        raise ValueError('positive integer steps required')
    candidate=resolve_thermal_candidate(template,device,model_context=model)
    sim=candidate.create_simulator()
    sim._require_context()
    physics=sim.physics; engine=physics.transport
    state=DeviceState.empty_for_device(sim.device)
    state.floating_gates[0].P0[:]=0; state.floating_gates[0].P1[:]=1
    profile=physics.electrostatics.evaluate(sim.device,4,np.zeros(sim.device.number_of_fgs())).field_profile
    initial=_electrons(sim.device,physics,state)
    dt=workflow_settings()['total_time_s']/steps
    first=None; clamped=0; residual=0
    for _ in range(steps):
        state,result=engine.step(sim.device,state,profile,physics.occupancy,dt)
        link=next(link for link in result.links if link.link_id==LINK_ID)
        if first is None: first=link
        sites=np.array([engine.baseline._sheet_site_density(physics.occupancy,fg) for fg in sim.device.floating_gates()])
        if np.any(abs(result.net_electron_flux_by_fg_m2_s*dt)>engine.config.max_transfer_fraction_per_step*2*sites):
            clamped+=1
        residual=max(residual,abs(_electrons(sim.device,physics,state)-initial)/initial)
    point=candidate.thermal.optical_model('FG1').evaluate(sim.device.get_layer('FG1').nc_material,1550)
    return {'candidate':candidate.to_dict(),'candidate_hash':candidate.candidate_hash,
        'temperature_K':sim.device.temperature_K,'substrate_gap_eV':physics.electrostatics.semiconductor.bandgap_eV,
        'intrinsic_density_m3':physics.electrostatics.semiconductor.intrinsic_density_m3,
        'vfb0_V':physics.electrostatics.flatband_zero(sim.device),
        'alpha_m_inv':point.absorption_coefficient_m_inv,
        'density_m3':model.resolve_density(trap_density_binding(LINK_ID,SPECIES_NAME)),
        'tat_rate_Hz':first.contribution(TransportMechanism.TRAP_ASSISTED).forward_rate_Hz,
        'conservation':residual,'clamped':clamped,'steps':steps,
        'final_mean_occupation':state.mean_normalized_occupations.tolist()}


def metric_spec():
    return MetricAnalysisSpec('M5 conditional numerical and optical assessment',(
        MetricDefinition('alpha',('alpha_m_inv',),'m^-1',ObjectiveDirection.MAXIMIZE),
        MetricDefinition('tat',('tat_rate_Hz',),'Hz',ObjectiveDirection.MINIMIZE),
        MetricDefinition('conservation',('conservation',),'1'),
        MetricDefinition('clamped',('clamped',),'1')),(
        MetricConstraint('illustrative_absorption_min','alpha',ConstraintOperator.GE,1e5,'m^-1'),
        MetricConstraint('conserve','conservation',ConstraintOperator.LE,1e-12,'1'),
        MetricConstraint('no_clamp','clamped',ConstraintOperator.LE,0,'1')))


def run_reference():
    device,sampling=build_reference(sample_count=SAMPLE_COUNT)
    template=template_for(device)
    experiment=ExperimentSpec.from_device(name='M5 DEVICE temperature',device=device,variables=(
        DesignVariable('temperature_K',ParameterBinding(BindingScope.DEVICE,('temperature_K',)),
                       TEMPERATURES_K,DesignVariableRole.ELECTRICAL,'K'),))
    settings={**workflow_settings(),'scope':SCOPE,'thermal_template':template.to_dict(),
        'nominal_model_context':sampling.study.model_context.to_dict(),
        'field_policy':'electrostatic initial field at 4 V, zero charge, resolved Si properties; held fixed',
        'optical_metric':'single FG1 monochromatic absorption at 1550 nm; no illumination or propagation'}
    def deterministic(candidate,protocol,point):
        return evaluate_candidate(template,candidate,sampling.study.model_context)
    sweep=run_cartesian_sweep(experiment,device,deterministic,evaluation_id='m5-thermal-fixed-field-v1',
        evaluation_parameters=settings)
    deterministic_analysis=analyze_sweep(sweep,metric_spec())
    sources=[]; audits=[]; paired=None
    for point in iter_cartesian_points(experiment):
        design=apply_experiment_design_point(experiment,device,point.assignments)
        study=ModelVariabilitySpec.from_device(name=sampling.study.name,device=design,
            model_context=sampling.study.model_context,variables=sampling.study.variables)
        manifest=generate_model_sample_manifest(replace(sampling,study=study))
        values=[s.values for s in manifest.samples]
        if paired is None: paired=values
        elif paired!=values: raise AssertionError('density values must be paired across temperatures')
        def evaluator(realization,context):
            return evaluate_candidate(ThermalContext.from_dict(context['thermal_template']),realization.device,realization.model_context)
        execution=execute_model_sample_manifest(manifest,design,evaluator,
            evaluation_id='m5-paired-thermal-model-v1',workflow_context={**settings,'dtco_design_point':point.to_dict()})
        population=analyze_model_execution(execution,metric_spec())
        coverage=EnsembleScalarDefinition('coverage',EnsembleScalarKind.COVERAGE_FRACTION,'1')
        passed=EnsembleScalarDefinition('passed',EnsembleScalarKind.SIMULATED_PASS_FRACTION,'1')
        sources.append(evaluate_model_eligibility(ModelDTCOStudy(point,population),(
            EnsembleConstraint('complete',coverage,ConstraintOperator.GE,1,'1'),
            EnsembleConstraint('all_pass',passed,ConstraintOperator.GE,1,'1'))))
        if execution.success_count:
            extrema=[min(manifest.samples,key=lambda s:s.values[0]),max(manifest.samples,key=lambda s:s.values[0])]
            models=[study.model_context]+[apply_model_sample_to_context(manifest.sampling_spec,s,design).model_context for s in extrema]
            for model in models:
                coarse=evaluate_candidate(template,design,model,steps=STEPS[0])
                fine=evaluate_candidate(template,design,model,steps=STEPS[1])
                error=max(abs(a-b) for a,b in zip(coarse['final_mean_occupation'],fine['final_mean_occupation'],strict=True))
                if error>OCCUPATION_ATOL or coarse['clamped'] or fine['clamped'] or max(coarse['conservation'],fine['conservation'])>1e-12:
                    raise ArithmeticError('thermal MODEL reference fails numerical audit')
                audits.append({'point_hash':point.point_hash,'density_m3':coarse['density_m3'],
                    'occupation_error_16_vs_32':error,'occupation_atol':OCCUPATION_ATOL})
    objectives=(EnsembleObjective('maximize_mean_alpha',EnsembleScalarDefinition('mean_alpha',EnsembleScalarKind.MEAN,'m^-1','alpha'),ObjectiveDirection.MAXIMIZE),
                EnsembleObjective('minimize_TAT_spread',EnsembleScalarDefinition('sd_tat',EnsembleScalarKind.STANDARD_DEVIATION,'Hz','tat'),ObjectiveDirection.MINIMIZE))
    payload={'schema_version':'m5-thermal-dtco-reference-v1','scope':SCOPE,'experiment':experiment.to_dict(),
        'deterministic':analyze_pareto(deterministic_analysis).to_dict(),
        'model_pareto':analyze_model_pareto(sources,objectives).to_dict(),'paired_density_values':paired,
        'timestep_audit':audits,'limits':['400 K deliberately outside 250-350 K domain; retained as failure',
        'population denominators remain attempted vs assessed under existing K/L rules',
        'illustrative absorption constraint and objectives; no calibrated technology optimization',
        'TAT parameters have no new temperature law; only declared resolved field/property inputs change']}
    return {**payload,'reference_hash':canonical_hash(payload)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('results/m5-thermal-dtco'))
    args=parser.parse_args(); evidence=run_reference()
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'reference.json').write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(evidence['reference_hash'])
