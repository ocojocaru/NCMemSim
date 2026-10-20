# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Q5 manifest identities, zero variation, sample failures and exact denominators."""
from dataclasses import replace, FrozenInstanceError
import pytest
import numpy as np
from examples.phase_q5_retention_ensemble_reference import build_study, build_ensemble_plan
from ncmemsim.multilevel_ensemble import (MultilevelEnsemblePlan, MultilevelEnsembleResult,
    run_multilevel_ensemble, _realized_study, _projection)
from ncmemsim.multilevel_retention import MultilevelRetentionPlan, run_multilevel_retention
from ncmemsim.multilevel_analysis import run_multilevel_study
from ncmemsim.multilevel_contracts import WeightReferenceMapping
from ncmemsim.ensemble import StochasticVariable, EnsembleSpec, SampleManifest, SamplingSpec, generate_sample_manifest
from ncmemsim.dtco import ParameterBinding, BindingScope
from ncmemsim.temperature_context import ResolvedThermalContext, ThermalSimulator
import ncmemsim.multilevel_ensemble as ensemble


@pytest.fixture(scope='module')
def case():
    plan=build_ensemble_plan(build_study())
    return plan,run_multilevel_ensemble(plan)


def with_values(plan,values):
    assert len(values)==len(plan.manifest.samples)
    manifest=replace(plan.manifest,samples=tuple(replace(sample,values=(value,))
        for sample,value in zip(plan.manifest.samples,values,strict=True)))
    return replace(plan,manifest=manifest)


def test_zero_variation_exact_nominal_states_and_identity(case):
    plan,result=case;raw=result.to_dict();s=result.summary
    assert s['requested_sample_count']==s['attempted_sample_count']==s['completed_sample_count']==2
    assert s['partial_sample_count']==s['failed_sample_count']==s['missing_sample_count']==0
    assert s['complete']
    nominal=run_multilevel_retention(MultilevelRetentionPlan(run_multilevel_study(plan.study),plan.delays_s,
        plan.retention_voltage_V,plan.internal_dt_s,plan.evidence))
    for sample,point in zip(plan.manifest.samples,raw['points'],strict=True):
        assert point['sample_id']==sample.sample_id and point['sample_index']==sample.sample_index
        assert point['realized_study']==plan.study.to_dict()
        assert point['result']==nominal.to_dict()
    for delay in s['delays']:
        assert delay['requested_sample_count']==delay['fully_assessed_sample_count']==2
        assert delay['full_assessment_fraction_of_requested']==1
    assert MultilevelEnsemblePlan.from_json(plan.to_json()).contract_hash==plan.contract_hash
    assert MultilevelEnsembleResult.from_json(result.to_json()).contract_hash==result.contract_hash
    with pytest.raises(FrozenInstanceError):plan.delays_s=(0.,)
    copy=result.summary;copy['delays'].clear();assert len(result.summary['delays'])==3


def test_varied_realizations_keep_waveform_grid_margins_and_initial_coordinates(case):
    varied=build_ensemble_plan(case[0].study,varied=True)
    result=run_multilevel_ensemble(varied)
    assert result.summary['completed_sample_count']==2
    source=varied.study
    hashes=[]
    for sample,point in zip(varied.manifest.samples,result.to_dict()['points'],strict=True):
        study=ensemble._Study.from_dict(point['realized_study'])
        context=study.levels[0].experiment.context;hashes.append(context.context_hash)
        assert context.device.floating_gates()[0].electrically_active_fraction==sample.values[0]
        assert study.minimum_margin_V==source.minimum_margin_V
        for realized,original in zip(study.levels,source.levels,strict=True):
            assert realized.readout_half_width_V==original.readout_half_width_V
            assert realized.experiment.sequence.to_dict()==original.experiment.sequence.to_dict()
            assert realized.experiment.initial_state_json==original.experiment.initial_state_json
    assert len(set(hashes))==2


def test_invalid_sample_does_not_disappear_from_denominator(case):
    nominal=case[0].manifest.samples[0].values[0]
    plan=with_values(case[0],(-.1,nominal))
    result=run_multilevel_ensemble(plan);raw=result.to_dict();s=result.summary
    assert s['attempted_sample_count']==2 and s['failed_sample_count']==1 and s['completed_sample_count']==1
    assert raw['points'][0]['failure']['stage']=='realization'
    assert raw['points'][0]['realized_study'] is None and raw['points'][0]['result'] is None
    for delay in s['delays']:
        assert delay['requested_sample_count']==2 and delay['fully_assessed_sample_count']==1
        assert delay['full_assessment_fraction_of_requested']==.5
    assert MultilevelEnsembleResult.from_json(result.to_json()).to_dict()==result.to_dict()


def test_known_collapsed_levels_are_criterion_failure_not_execution_failure(case):
    plan=with_values(case[0],(0.,0.))
    result=run_multilevel_ensemble(plan);s=result.summary
    assert s['completed_sample_count']==2 and s['failed_sample_count']==0
    for delay in s['delays']:
        assert delay['known_failed_sample_count']==2 and delay['passed_sample_count']==0
        assert delay['fully_assessed_sample_count']==2
        assert delay['passed_fraction_of_fully_assessed']==0


def test_partial_retention_is_not_completed_sample(case,monkeypatch):
    original=ThermalSimulator.relax_voltage
    def fail(self,*args,**kwargs):
        if kwargs.get('dwell_time_s')==2e-7:raise RuntimeError('intentional retention failure')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(ThermalSimulator,'relax_voltage',fail)
    result=run_multilevel_ensemble(case[0]);s=result.summary
    assert s['partial_sample_count']==2 and s['completed_sample_count']==0 and s['failed_sample_count']==0
    assert s['delays'][0]['fully_assessed_sample_count']==2
    assert s['delays'][-1]['fully_assessed_sample_count']==0
    assert s['delays'][-1]['passed_fraction_of_fully_assessed'] is None
    assert all(p['result']['summary']['failed_probe_count']==3 for p in result.to_dict()['points'])


def test_workflow_failure_is_retained_and_later_sample_runs(case,monkeypatch):
    original=ensemble._prepare;calls=0
    def fail(study):
        nonlocal calls
        calls+=1
        if calls==1:raise RuntimeError('intentional preparation wrapper failure')
        return original(study)
    monkeypatch.setattr(ensemble,'_prepare',fail)
    result=run_multilevel_ensemble(case[0])
    assert result.summary['failed_sample_count']==1 and result.summary['completed_sample_count']==1
    assert result.to_dict()['points'][0]['failure']['stage']=='workflow'
    assert result.to_dict()['points'][0]['realized_study']==case[0].study.to_dict()


def test_missing_manifest_slot_keeps_full_requested_count(case):
    raw=case[1].to_dict();raw['points'][0]=None
    raw['summary']=_projection(raw)
    result=MultilevelEnsembleResult.from_dict(raw)
    assert result.summary['missing_sample_count']==1 and result.summary['attempted_sample_count']==1
    assert result.summary['requested_sample_count']==2
    assert all(x['full_assessment_fraction_of_requested']==.5 for x in result.summary['delays'])


def test_unsupported_binding_and_reference_rebinding_rejected():
    from ncmemsim.ensemble import PhysicalDomain
    plan=build_ensemble_plan(build_study())
    variable=plan.manifest.sampling_spec.ensemble_spec.variables[0]
    # This is a valid legacy diameter declaration; the Q5 adapter, rather than
    # the upstream physical-domain contract, must reject its unsupported scope.
    v=replace(variable,binding=ParameterBinding(BindingScope.DEVICE,('layers','FG1','nc_diameter_nm')),
              unit='nm',nominal_value=None,physical_domain=PhysicalDomain(lower=0.,lower_inclusive=False))
    e=EnsembleSpec.from_device(name='unsupported Q5',device=plan.study.levels[0].experiment.context.device,variables=(v,))
    manifest=generate_sample_manifest(replace(plan.manifest.sampling_spec,ensemble_spec=e))
    with pytest.raises(ValueError,match='only existing FG'):
        replace(plan,manifest=manifest)
    exp=plan.study.levels[0].experiment
    reference=WeightReferenceMapping('nominal fixed window',exp.context.context_hash,exp.sequence.readout.contract_hash,
        -.02,0.,.001,'assumed low','assumed high','nominal only',plan.evidence)
    study=replace(plan.study,levels=tuple(replace(level,experiment=replace(level.experiment,weight_reference=reference))
                                         for level in plan.study.levels))
    with pytest.raises(ValueError):replace(plan,study=study)


def test_nc_volume_fraction_binding_is_supported(case):
    plan=case[0];spec=plan.manifest.sampling_spec.ensemble_spec;variable=spec.variables[0]
    device=plan.study.levels[0].experiment.context.device
    value=device.floating_gates()[0].nc_volume_fraction
    from ncmemsim.ensemble import ConstantDistribution
    v=replace(variable,binding=ParameterBinding(BindingScope.DEVICE,('layers','FG1','nc_volume_fraction')),
              distribution=ConstantDistribution(value),nominal_value=value)
    e=EnsembleSpec.from_device(name='Q5 volume baseline',device=device,variables=(v,))
    manifest=generate_sample_manifest(replace(plan.manifest.sampling_spec,ensemble_spec=e))
    bound=replace(plan,manifest=manifest)
    assert _realized_study(bound,manifest.samples[0]).to_dict()==plan.study.to_dict()


@pytest.mark.parametrize('kind',['order','sample_id','plan_hash','status','summary','realized_context','reference_policy'])
def test_tamper_rejected(case,kind):
    raw=case[1].to_dict()
    if kind=='order':raw['points'].reverse()
    elif kind=='sample_id':raw['points'][0]['sample_id']='forged'
    elif kind=='plan_hash':raw['plan_hash']='0'*64
    elif kind=='status':raw['points'][0]['status']='partial'
    elif kind=='summary':raw['summary']['completed_sample_count']=0
    elif kind=='reference_policy':raw['plan']['reference_policy']='per-sample rescaling'
    else:raw['points'][0]['realized_study']['minimum_margin_V']=0.
    with pytest.raises(ValueError):MultilevelEnsembleResult.from_dict(raw)


def test_restoration_does_not_resample_or_integrate(case,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('resampling or integration')
    monkeypatch.setattr(ResolvedThermalContext,'create_simulator',forbidden)
    monkeypatch.setattr(ThermalSimulator,'relax_voltage',forbidden)
    monkeypatch.setattr(np.random,'default_rng',forbidden)
    from ncmemsim.ensemble import RNGSpec
    monkeypatch.setattr(RNGSpec,'create_generator',forbidden)
    import ncmemsim.ensemble.sampling as sampling
    monkeypatch.setattr(sampling,'generate_sample_manifest',forbidden)
    assert MultilevelEnsembleResult.from_json(case[1].to_json()).to_dict()==case[1].to_dict()
    with pytest.raises(ValueError):MultilevelEnsembleResult.from_json('{"x":1,"x":2}')
    with pytest.raises(ValueError):MultilevelEnsemblePlan.from_json('{"x":Infinity}')
