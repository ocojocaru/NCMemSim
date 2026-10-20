# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Q3 fixed-source preparation, signed margins, negative outcomes and archives."""
from dataclasses import FrozenInstanceError, replace
import json
import numpy as np
import pytest
from examples.phase_q3_multilevel_reference import build_plan
from ncmemsim.multilevel_contracts import ElectricalSequenceExperiment, WeightReferenceMapping
from ncmemsim.multilevel_execution import ElectricalSequenceResult
from ncmemsim.multilevel_analysis import (
    MultilevelPreparation, MultilevelStudyPlan, MultilevelStudyResult,
    analyze_multilevel_results, run_multilevel_study,
)
from ncmemsim.temperature_context import ThermalSimulator, ResolvedThermalContext


@pytest.fixture(scope='module')
def plan():return build_plan()


@pytest.fixture(scope='module')
def result(plan):return run_multilevel_study(plan)


@pytest.fixture(scope='module')
def results(result):return tuple(ElectricalSequenceResult.from_dict(x) for x in result.to_dict()['results'])


def test_independent_preparation_and_common_readout(plan,result):
    assert result.summary['status']=='passed'
    assert result.summary['completed_level_count']==3
    assert result.summary['passed_pair_count']==2
    assert result.summary['minimum_signed_margin_V']>.004
    assert not result.summary['experimental_qualification']
    for level,run in zip(plan.levels,result.to_dict()['results']):
        assert run['experiment']['initial_state']==plan.levels[0].experiment.to_dict()['initial_state']
        assert run['steps'][0]['initial_state']==run['experiment']['initial_state']
        assert run['experiment_hash']==level.experiment.contract_hash


@pytest.mark.parametrize('index',range(3))
def test_strict_roundtrip_and_owned_projections(plan,result,index):
    obj=(plan.levels[0],plan,result)[index]
    assert type(obj).from_json(obj.to_json()).contract_hash==obj.contract_hash
    with pytest.raises(FrozenInstanceError):obj.extra=True
    raw=obj.to_dict();raw['schema_version']='changed'
    assert obj.to_dict()['schema_version']!='changed'


@pytest.mark.parametrize('index',range(3))
@pytest.mark.parametrize('mutation',['version','missing','extra','duplicate','nonfinite'])
def test_archive_boundaries(plan,result,index,mutation):
    obj=(plan.levels[0],plan,result)[index];raw=obj.to_dict()
    if mutation=='version':raw['schema_version']='future'
    elif mutation=='missing':raw.pop('schema_version')
    elif mutation=='extra':raw['bad']=0
    if mutation=='duplicate':text=obj.to_json()[:-1]+',"schema_version":"duplicate"}'
    elif mutation=='nonfinite':text=obj.to_json()[:-1]+',"bad":NaN}'
    else:text=json.dumps(raw)
    with pytest.raises(ValueError):type(obj).from_json(text)


@pytest.mark.parametrize('value',[True,'1',None,-1,float('inf'),float('nan'),10**400])
def test_invalid_margin_and_width(plan,value):
    with pytest.raises(ValueError):replace(plan,minimum_margin_V=value)
    with pytest.raises(ValueError):replace(plan.levels[0],readout_half_width_V=value)


@pytest.mark.parametrize('levels',[(),[],(None,),('a','b')])
def test_nonempty_typed_levels(plan,levels):
    with pytest.raises(ValueError):replace(plan,levels=levels)


def test_duplicate_ids_and_interval_semantics(plan):
    with pytest.raises(ValueError):replace(plan,levels=(plan.levels[0],plan.levels[0]))
    with pytest.raises(ValueError):replace(plan,interval_kind='measured_sigma')
    with pytest.raises(ValueError):replace(plan,levels=(replace(plan.levels[0],readout_half_width_V=.001),*plan.levels[1:]))
    with pytest.raises(ValueError):replace(plan,evidence=None)


@pytest.mark.parametrize('change',['readout','context','initial_state','weight_reference'])
def test_common_condition_binding(plan,change):
    level=plan.levels[1];exp=level.experiment
    if change=='readout':
        exp=replace(exp,sequence=replace(exp.sequence,readout=replace(exp.sequence.readout,read_voltage_V=.1)))
    elif change=='context':
        exp=replace(exp,context=exp.context.context.resolve(temperature_K=301))
    elif change=='initial_state':
        state=exp.initial_state;state.time_s=1
        exp=ElectricalSequenceExperiment.from_state(exp.name,exp.context,exp.sequence,state)
    else:
        ref=WeightReferenceMapping('pair',exp.context.context_hash,exp.sequence.readout.contract_hash,
            -.1,.1,.01,'low','high','this context',exp.sequence.evidence)
        exp=replace(exp,weight_reference=ref)
    with pytest.raises(ValueError):replace(plan,levels=(plan.levels[0],replace(level,experiment=exp),plan.levels[2]))


def test_reversal_not_resorted(plan,results):
    reversed_plan=replace(plan,levels=tuple(reversed(plan.levels)))
    res=analyze_multilevel_results(reversed_plan,tuple(reversed(results)))
    assert res.summary['status']=='failed'
    assert res.summary['failed_pair_count']==2
    assert all(x['signed_margin_V']<0 for x in res.summary['adjacent_pairs'])
    assert [x['level_id'] for x in res.summary['levels']]==['L2','L1','L0']


def test_collapsed_readouts_and_zero_minimum_still_fail(plan,results):
    second=replace(plan.levels[0],level_id='duplicate-response')
    collapsed=replace(plan,levels=(plan.levels[0],second),minimum_margin_V=0)
    res=analyze_multilevel_results(collapsed,(results[0],results[0]))
    assert res.summary['status']=='failed'
    assert res.summary['minimum_signed_margin_V']==0


def test_threshold_boundary_and_assumed_overlap(plan,results):
    base=analyze_multilevel_results(plan,results)
    threshold=base.summary['minimum_signed_margin_V']
    assert analyze_multilevel_results(replace(plan,minimum_margin_V=threshold),results).summary['status']=='passed'
    assert analyze_multilevel_results(replace(plan,minimum_margin_V=threshold+.001),results).summary['status']=='failed'
    overlap=replace(plan,interval_kind='assumed_bounds',levels=tuple(replace(x,readout_half_width_V=.01) for x in plan.levels))
    res=analyze_multilevel_results(overlap,results)
    assert res.summary['status']=='failed'
    assert res.summary['failed_pair_count']==2


def test_missing_slots_and_known_failure_priority(plan,results):
    missing=analyze_multilevel_results(plan,(results[0],None,results[2]))
    assert missing.summary['status']=='not_assessable'
    assert missing.summary['missing_level_count']==1
    assert missing.summary['not_assessable_pair_count']==2
    assert missing.summary['minimum_signed_margin_V'] is None
    four=replace(plan,levels=(plan.levels[0],replace(plan.levels[0],level_id='collapsed'),*plan.levels[1:]))
    res=analyze_multilevel_results(four,(results[0],results[0],results[1],None))
    assert res.summary['status']=='failed' and not res.summary['complete']
    assert res.summary['failed_pair_count']==1 and res.summary['not_assessable_pair_count']==1
    assert res.summary['pair_assessment_fraction']==2/3


def test_failed_preparation_does_not_stop_other_levels(plan,monkeypatch):
    original=ThermalSimulator.relax_voltage
    def intercepted(self,*args,**kwargs):
        if kwargs.get('dwell_time_s')==5e-7:raise RuntimeError('deliberate middle-level failure')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(ThermalSimulator,'relax_voltage',intercepted)
    res=run_multilevel_study(plan)
    assert res.summary['completed_level_count']==2
    assert res.summary['failed_level_count']==1
    assert res.summary['status']=='not_assessable'
    assert res.summary['levels'][1]['readout_V'] is None
    assert res.summary['levels'][1]['failure']['stage']=='step'
    assert res.to_dict()['results'][1]['initial_read'] is not None
    assert MultilevelStudyResult.from_json(res.to_json()).contract_hash==res.contract_hash


def test_numeric_overflow_retained_as_unassessable(plan,results):
    wide=replace(plan,interval_kind='assumed_bounds',levels=tuple(replace(x,readout_half_width_V=1e308) for x in plan.levels))
    res=analyze_multilevel_results(wide,results)
    assert res.summary['status']=='not_assessable' and res.summary['complete']
    assert all(x['reason']=='nonrepresentable_margin' for x in res.summary['adjacent_pairs'])


def test_wrong_source_order_counts_and_tampering(plan,result,results):
    with pytest.raises(ValueError):analyze_multilevel_results(plan,tuple(reversed(results)))
    for bad in ([],tuple(results[:1]),(1,None,None)):
        with pytest.raises(ValueError):analyze_multilevel_results(plan,bad)
    for mutation in ('hash','margin','counts','drop','source'):
        raw=result.to_dict()
        if mutation=='hash':raw['plan_hash']='0'*64
        elif mutation=='margin':raw['summary']['adjacent_pairs'][0]['signed_margin_V']=1
        elif mutation=='counts':raw['summary']['completed_level_count']=0
        elif mutation=='drop':raw['results'].pop()
        elif mutation=='source':raw['results'][0]['experiment_hash']='0'*64
        with pytest.raises(ValueError):MultilevelStudyResult.from_dict(raw)


def test_restore_and_analysis_do_not_replay(plan,result,results,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('replay forbidden')
    monkeypatch.setattr(ResolvedThermalContext,'create_simulator',forbidden)
    monkeypatch.setattr(ThermalSimulator,'relax_voltage',forbidden)
    monkeypatch.setattr(np.random,'default_rng',forbidden)
    assert MultilevelStudyResult.from_json(result.to_json()).contract_hash==result.contract_hash
    assert analyze_multilevel_results(plan,results).contract_hash==result.contract_hash


def test_fixed_waveform_timestep_halving(plan,result):
    fine=run_multilevel_study(build_plan(internal_dt_s=5e-10))
    assert fine.summary['status']=='passed'
    a=[x['readout_V'] for x in result.summary['levels']]
    b=[x['readout_V'] for x in fine.summary['levels']]
    np.testing.assert_allclose(a,b,rtol=0,atol=1e-5)
    assert all(run['summary']['completed_step_count']==1 for run in fine.to_dict()['results'])
