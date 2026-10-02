# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Thermal candidate ownership, real transport use and K/L failure denominators."""
from copy import deepcopy
from dataclasses import replace
import math
import numpy as np
import pytest
from examples import phase_m5_thermal_dtco_reference as ref
from ncmemsim import DeviceState, Simulator
from ncmemsim.constants import BOLTZMANN_J_K, ELEMENTARY_CHARGE_C
from ncmemsim.dtco import run_cartesian_sweep, analyze_sweep, analyze_pareto, apply_experiment_design_point, iter_cartesian_points
from ncmemsim.hashing import canonical_hash
from ncmemsim.temperature_context import ThermalContext
from ncmemsim.thermal_dtco import (resolve_thermal_candidate,ThermalCandidateResolution,
    ThermalCandidateError,ThermalDomainError,ThermalModelSimulator)
from ncmemsim.ensemble.model_contracts import TransportModelContext, ModelVariabilitySpec
from ncmemsim.ensemble.model_sampling import generate_model_sample_manifest
from ncmemsim.ensemble.model_execution import execute_model_sample_manifest
from ncmemsim.ensemble.model_analysis import analyze_model_execution
from ncmemsim.ensemble.model_dtco import ModelParetoAnalysis
from ncmemsim.transport import AdvancedTransportEngine, AdvancedTransportSpec
from ncmemsim.optics import LightSource


@pytest.fixture(scope='module')
def evidence():
    return ref.run_reference()


@pytest.fixture
def base():
    device,sampling=ref.build_reference(sample_count=4)
    return device,sampling,ref.template_for(device)


@pytest.mark.parametrize('t',[250.,300.,350.])
def test_candidate_resolves_single_temperature_and_owns_inputs(base,t):
    device,sampling,template=base
    template_hash=template.context_hash
    device.temperature_K=t
    candidate=resolve_thermal_candidate(template,device,model_context=sampling.study.model_context)
    a,b=candidate.create_simulator(),candidate.create_simulator()
    assert isinstance(a,ThermalModelSimulator)
    assert a.device.temperature_K==t
    assert a.physics is not b.physics and a.device is not b.device
    assert a.physics.transport.baseline is not b.physics.transport.baseline
    assert a.physics.transport.tunneling is a.physics.tunneling is a.physics.occupancy.tunneling
    assert a.physics.transport.specification==sampling.study.model_context.advanced_transport
    ni=a.physics.electrostatics.semiconductor.intrinsic_density_m3
    eg=a.physics.electrostatics.semiconductor.bandgap_eV
    expected_phi=BOLTZMANN_J_K*t/ELEMENTARY_CHARGE_C*math.log(a.device.substrate_doping_m3/ni)
    assert a.physics.electrostatics.fermi_potential(a.device)==expected_phi
    assert eg==template.substrate_gap.evaluate(t)
    assert ni==template.intrinsic_density.evaluate(t,substrate_doping_m3=device.substrate_doping_m3)
    device.metadata['caller_mutation']=[1]
    assert 'caller_mutation' not in a.device.metadata
    assert template.context_hash==template_hash
    assert ThermalCandidateResolution.from_json(candidate.to_json()).to_dict()==candidate.to_dict()


@pytest.mark.parametrize('t',[249.,351.,400.])
def test_domain_failure_is_typed_without_clipping(base,t):
    device,sampling,template=base; device.temperature_K=t
    with pytest.raises(ThermalDomainError): resolve_thermal_candidate(template,device)
    assert device.temperature_K==t


def test_no_model_path_and_original_m2_archive_unchanged(base):
    device,sampling,template=base
    plain=resolve_thermal_candidate(template,device)
    assert plain.model_context is None
    assert plain.to_dict()['thermal']['schema_version']=='resolved-thermal-context-v1'
    assert template.to_dict()['schema_version']=='thermal-context-v1'
    with pytest.raises((ValueError,TypeError)):
        sim=plain.create_simulator(); sim.physics.transport=AdvancedTransportEngine(sim.physics.transport,sampling.study.model_context.advanced_transport)
        ThermalContext.from_nominal(sim.device,sim.physics)


@pytest.mark.parametrize('mutation',['temperature','metadata','doping','tunneling','kinetics','baseline','engine','model','extended_spec','config','callback'])
def test_runtime_drift_is_rejected(base,mutation):
    device,sampling,template=base
    simulator=resolve_thermal_candidate(template,device,model_context=sampling.study.model_context).create_simulator()
    if mutation=='temperature': simulator.device.temperature_K=310
    elif mutation=='metadata': simulator.device.metadata['drift']=1
    elif mutation=='doping': simulator.device.substrate_doping_m3*=2
    elif mutation=='tunneling': simulator.physics.tunneling.config=replace(simulator.physics.tunneling.config,integration_points=161)
    elif mutation=='kinetics': simulator.physics.occupancy.config=replace(simulator.physics.occupancy.config,nu0_Hz=123)
    elif mutation=='baseline': simulator.physics.transport.baseline.config=replace(simulator.physics.transport.config,enabled=False)
    elif mutation=='engine': simulator.physics.transport=AdvancedTransportEngine(simulator.physics.transport.baseline,simulator.physics.transport.specification)
    elif mutation=='model': simulator.physics.transport.specification=AdvancedTransportSpec()
    elif mutation=='extended_spec': object.__setattr__(simulator.physics.transport.specification,'runtime_callback',lambda:None)
    elif mutation=='config': simulator.config=replace(simulator.config,qfix_C_m2=1e-5)
    else: simulator.physics.callback=lambda:None
    with pytest.raises(ValueError): simulator.relax_voltage(DeviceState.empty_for_device(simulator.device),4,dwell_time_s=0)


def test_unknown_or_substrate_model_attachments_rejected(base):
    device,sampling,template=base
    attachment=sampling.study.model_context.advanced_transport.attachments[0]
    for name in ('unknown','FG2<->substrate'):
        model=TransportModelContext(AdvancedTransportSpec((replace(attachment,link_id=name),)))
        with pytest.raises(ThermalCandidateError): resolve_thermal_candidate(template,device,model_context=model)


@pytest.mark.parametrize('field',['thermal_hash','model_hash','schema_version','mechanism_failure_policy'])
def test_strict_candidate_identity_rejects_tampering(base,field):
    device,sampling,template=base
    archive=resolve_thermal_candidate(template,device,model_context=sampling.study.model_context).to_dict()
    archive[field]='invalid'
    with pytest.raises(ValueError): ThermalCandidateResolution.from_dict(archive)


def test_reader_rejects_derived_thermal_tampering_and_duplicate_keys(base):
    device,sampling,template=base
    archive=resolve_thermal_candidate(template,device).to_dict()
    archive['thermal']['resolved']['physics']['semiconductor']['bandgap_eV']=1.5
    with pytest.raises(ValueError): ThermalCandidateResolution.from_dict(archive)
    with pytest.raises(ValueError): ThermalCandidateResolution.from_json('{"thermal":1,"thermal":2}')


def test_optional_mechanism_failure_is_not_success(base,monkeypatch):
    import ncmemsim.transport.integration as integration
    def fail(*args,**kwargs): raise ArithmeticError('deliberately unavailable TAT mechanism')
    monkeypatch.setattr(integration,'evaluate_trap_assisted_transport_with_barrier_correction',fail)
    device,sampling,template=base
    simulator=resolve_thermal_candidate(template,device,model_context=sampling.study.model_context).create_simulator()
    with pytest.raises(ArithmeticError,match='optional transport mechanism failed'):
        simulator.relax_voltage(DeviceState.empty_for_device(simulator.device),4,dwell_time_s=0)


def test_reference_temperature_advanced_simulator_recovers_existing_engine(base):
    device,sampling,template=base
    candidate=resolve_thermal_candidate(template,device,model_context=sampling.study.model_context)
    thermal=candidate.create_simulator()
    physics=candidate.thermal.physics
    physics.transport=AdvancedTransportEngine(physics.transport,sampling.study.model_context.advanced_transport)
    original=Simulator(candidate.thermal.device,physics,candidate.thermal.simulation_config)
    outputs=[s.relax_voltage(DeviceState.empty_for_device(s.device),4,dwell_time_s=4e-14,
        internal_dt_s=2.5e-15,light_source=LightSource.led(1550,10)) for s in (thermal,original)]
    for key in ('qfg_C_m2','delta_vfb_V','absorbed_photon_flux_m2_s','photo_transition_rate_s'):
        assert outputs[0][key]==outputs[1][key]
    for a,b in zip(outputs[0]['state'].floating_gates,outputs[1]['state'].floating_gates,strict=True):
        for name in ('P0','P1','P2'): np.testing.assert_array_equal(getattr(a,name),getattr(b,name))


def test_full_reference_preserves_failures_pairing_and_denominators(evidence):
    assert evidence['experiment']['variables'][0]['binding']=={'scope':'device','path':['temperature_K']}
    parameters=evidence['deterministic']['source_analysis']['source_sweep']['evaluation']['parameters']
    assert parameters['nominal_model_context']==evidence['model_pareto']['sources'][0]['source']['source']['execution']['nominal']['model']
    assert evidence['deterministic']['ranked_count']==2
    assert [r['source_status'] for r in evidence['deterministic']['points']]==['infeasible','feasible','feasible','failed']
    assert evidence['model_pareto']['attempted_design_count']==4
    assert evidence['model_pareto']['ranked_design_count']==2
    assert len(evidence['paired_density_values'])==8
    draws=[]
    for source in evidence['model_pareto']['sources']:
        population=source['source']; count=population['counts']; fractions=population['fractions']
        assert count['attempted_count']==8
        assert fractions['coverage_fraction']['denominator']==8
        assert fractions['simulated_pass_fraction']['denominator']==8
        execution=population['source']
        draws.append([s['values'] for s in execution['manifest']['samples']])
    assert all(v==draws[0] for v in draws)
    outside=evidence['model_pareto']['sources'][-1]['source']
    assert outside['counts']['execution_failure_count']==8
    assert outside['fractions']['coverage_fraction']['value']==0
    assert outside['fractions']['ensemble_feasibility_fraction']['value'] is None
    assert all(p['error_type'].endswith('ThermalDomainError') for p in outside['points'])
    assert ModelParetoAnalysis.from_dict(evidence['model_pareto']).to_dict()==evidence['model_pareto']
    raw=deepcopy(evidence); digest=raw.pop('reference_hash')
    assert canonical_hash(raw)==digest
    assert max(a['occupation_error_16_vs_32'] for a in evidence['timestep_audit'])<1e-3


def test_domain_metric_failure_and_infeasible_remain_distinct(base):
    device,sampling,template=base
    device.temperature_K=350
    sampling=replace(sampling,study=ModelVariabilitySpec.from_device(
        name=sampling.study.name,device=device,model_context=sampling.study.model_context,variables=sampling.study.variables))
    manifest=generate_model_sample_manifest(sampling)
    def evaluate(realization,settings):
        i=realization.sample.sample_index
        if i==0:
            realization.device.temperature_K=400
            resolve_thermal_candidate(template,realization.device)
        if i==1: return {'alpha_m_inv':1}  # missing other declared metrics
        return {'alpha_m_inv':0 if i==2 else 2e5,'tat_rate_Hz':1,'conservation':0,'clamped':0}
    execution=execute_model_sample_manifest(manifest,device,evaluate,evaluation_id='M5-failure-accounting',workflow_context={'scope':'synthetic failure test'})
    population=analyze_model_execution(execution,ref.metric_spec())
    assert population.counts=={'attempted_count':4,'assessed_count':2,'feasible_count':1,'infeasible_count':1,
        'failed_count':2,'execution_failure_count':1,'metric_failure_count':1}
    assert population.fractions['coverage_fraction']['value']==.5
    assert population.fractions['simulated_pass_fraction']['value']==.25
    assert population.fractions['ensemble_feasibility_fraction']['value']==.5
    points=population.to_dict()['points']
    assert points[0]['error_type'].endswith('ThermalDomainError')
    assert points[1]['failure_category']=='metric-extraction'
    assert points[2]['status']=='infeasible' and points[3]['status']=='feasible'


def test_realized_density_changes_actual_tat_rates_without_changing_thermal_gaps(base):
    device,sampling,template=base
    model=sampling.study.model_context; attachment=model.advanced_transport.attachments[0]
    modified=TransportModelContext(AdvancedTransportSpec((replace(attachment,specification=replace(attachment.specification,
        species=(replace(attachment.specification.species[0],density_m3=ref.NOMINAL_DENSITY_M3*2),))),)))
    a=ref.evaluate_candidate(template,device,model); b=ref.evaluate_candidate(template,device,modified)
    assert b['tat_rate_Hz']==pytest.approx(a['tat_rate_Hz']*2)
    assert a['substrate_gap_eV']==b['substrate_gap_eV']
    assert a['candidate_hash']!=b['candidate_hash']
    assert a['final_mean_occupation']!=b['final_mean_occupation']


@pytest.mark.parametrize('kind',['model','specification','attachment','species'])
def test_extended_model_callbacks_are_not_archived(base,kind):
    device,sampling,template=base
    model=deepcopy(sampling.study.model_context)
    if kind=='model': target=model
    elif kind=='specification': target=model.advanced_transport
    elif kind=='attachment': target=model.advanced_transport.attachments[0]
    else: target=model.advanced_transport.attachments[0].specification.species[0]
    object.__setattr__(target,'runtime_callback',lambda:None)
    with pytest.raises(ThermalCandidateError): resolve_thermal_candidate(template,device,model_context=model)


def test_changed_doping_outside_carrier_domain_fails(base):
    device,sampling,template=base
    device.substrate_doping_m3=1e25
    with pytest.raises(ThermalDomainError): resolve_thermal_candidate(template,device)


def test_mismatched_composition_never_inherits_ge_coefficients(base):
    from ncmemsim.materials import make_gesn
    device,sampling,template=base
    device.get_layer('FG1').nc_material=make_gesn(.05)
    with pytest.raises(ThermalCandidateError): resolve_thermal_candidate(template,device)
