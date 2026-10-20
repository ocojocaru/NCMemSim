# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Q4 explicit metric definitions, fixed references, archives and negative cases."""
from dataclasses import replace
from types import SimpleNamespace
import json
import math
import pytest
from examples.phase_q4_gradual_update_reference import build
from ncmemsim.multilevel_contracts import WeightReferenceMapping
from ncmemsim.multilevel_execution import run_electrical_sequence, ElectricalSequenceResult
from ncmemsim.multilevel_updates import (GradualUpdateAnalysis, PairedUpdateAnalysis,
    analyze_gradual_updates, analyze_paired_updates)
import ncmemsim.multilevel_updates as updates


@pytest.fixture(scope='module')
def case():
    a,b,o,r=build()
    return a,b,o,r,run_electrical_sequence(a),run_electrical_sequence(b)


def analyze(case, *, direction='decreasing', minimum=1e-6, source=None, reference=None):
    return analyze_gradual_updates(case[4] if source is None else source, case[3] if reference is None else reference,
        expected_direction=direction, minimum_excursion_V=minimum)


def test_actual_updates_and_no_source_mutation(case):
    before=case[4].to_json(); result=analyze(case);s=result.summary
    assert s['status']=='assessable' and s['complete']
    assert s['observed_update_count']==4 and s['update_coverage_fraction']==1
    assert s['all_steps_identical'] and s['direction_reversal_count']==0
    r=s['read_delta_vfb_V'];n=4
    expected=max(abs((x-r[0])/(r[-1]-r[0])-k/n) for k,x in enumerate(r))
    assert s['linearity_deviation']==expected
    assert s['signed_updates_V']==[b-a for a,b in zip(r,r[1:])]
    assert s['weight_proxy']==[(x+.1)/.1 for x in r]
    assert s['read_times_s']==[0.,1e-7,2e-7,3e-7,4e-7]
    assert case[4].to_json()==before
    assert result.summary['experimental_qualification'] is False
    assert GradualUpdateAnalysis.from_json(result.to_json()).contract_hash==result.contract_hash
    copy=result.summary;copy['weight_proxy'].clear();assert len(result.summary['weight_proxy'])==5


@pytest.mark.parametrize('minimum',[True,False,'1',None,0,-1,float('inf'),float('nan'),10**400])
def test_bad_minimum(case,minimum):
    with pytest.raises(ValueError):analyze(case,minimum=minimum)


@pytest.mark.parametrize('direction',['up','',1,None,True])
def test_bad_direction(case,direction):
    with pytest.raises(ValueError):analyze(case,direction=direction)


def test_insufficient_and_wrong_direction(case):
    assert analyze(case,minimum=1).summary['reason']=='insufficient_dynamic_range'
    assert analyze(case,direction='increasing').summary['reason']=='wrong_or_zero_net_direction'
    negative=analyze(case,direction='increasing',source=case[5])
    assert negative.summary['direction_reversal_count']==4
    paired=analyze_paired_updates(analyze(case),negative)
    assert paired.summary['status']=='not_assessable' and paired.summary['asymmetry'] is None
    assert PairedUpdateAnalysis.from_json(paired.to_json()).contract_hash==paired.contract_hash


def test_reference_bindings_and_no_substitution(case):
    for reference in (replace(case[3],context_hash='0'*64),replace(case[3],readout_hash='0'*64),
                      replace(case[3],name='different fixed reference')):
        with pytest.raises(ValueError):analyze(case,reference=reference)
    with pytest.raises(ValueError):analyze_paired_updates(analyze(case),analyze(case))


def test_short_and_varying_train(case):
    exp=case[0]
    short=replace(exp,sequence=replace(exp.sequence,steps=exp.sequence.steps[:1]))
    s=analyze(case,source=run_electrical_sequence(short)).summary
    assert s['reason']=='fewer_than_two_updates' and s['linearity_deviation'] is None
    steps=tuple(replace(x,duration_s=1.1e-7) if i==1 else x for i,x in enumerate(exp.sequence.steps))
    varying=replace(exp,sequence=replace(exp.sequence,steps=steps))
    assert not analyze(case,source=run_electrical_sequence(varying)).summary['all_steps_identical']


# Isolate the metric arithmetic against known curves while the integration and
# source archive checks are exercised separately with actual model trajectories.
@pytest.mark.parametrize('curve,direction,minimum,expected,reason,reversals',[
    ([0.,1.,2.,3.,4.],'increasing',.1,0.,None,0),
    ([4.,3.,2.,1.,0.],'decreasing',.1,0.,None,0),
    ([0.,1.,1.,1.,2.],'increasing',.1,.25,None,0),
    ([0.,2.,1.,3.,4.],'increasing',.1,.25,None,1),
    ([1.,1.,1.,1.,1.],'increasing',.1,None,'wrong_or_zero_net_direction',0),
    ([0.,.01,.02,.03,.04],'increasing',.1,None,'insufficient_dynamic_range',0),
    ([0.,1.,2.,3.,4.],'increasing',4.,0.,None,0),
])
def test_analytic_metric_oracles(case,monkeypatch,curve,direction,minimum,expected,reason,reversals):
    actual_source=updates._source
    def source(raw):
        result,exp,optical=actual_source(raw)
        return SimpleNamespace(contract_hash=result.contract_hash,
            summary={**result.summary,'read_delta_vfb_V':curve}),exp,optical
    monkeypatch.setattr(updates,'_source',source)
    summary=analyze(case,direction=direction,minimum=minimum).summary
    assert summary['linearity_deviation']==expected and summary['reason']==reason
    assert summary['direction_reversal_count']==reversals
    assert summary['weight_proxy']==[(x+.1)/.1 for x in curve]  # no clipping even far outside endpoints
    assert summary['out_of_reference_read_indices']==[i for i,x in enumerate(curve) if not -.1<=x<=0]


@pytest.mark.parametrize('factor,expected',[(1.,0.),(2.,1/3),(10.,9/11)])
def test_analytic_paired_magnitude_definition(case,monkeypatch,factor,expected):
    actual_source=updates._source
    def source(raw):
        result,exp,optical=actual_source(raw)
        curve=([0.,1.,2.,3.,4.] if exp.name=='loading' else [4.*factor,3.*factor,2.*factor,factor,0.])
        return SimpleNamespace(contract_hash=result.contract_hash,
            summary={**result.summary,'read_delta_vfb_V':curve}),exp,optical
    monkeypatch.setattr(updates,'_source',source)
    a=analyze(case,direction='increasing')
    b=analyze(case,direction='decreasing',source=case[5])
    s=analyze_paired_updates(a,b).summary
    assert s['status']=='assessable' and s['asymmetry']==pytest.approx(expected)
    assert s['alignment']=='same_segment_index_no_reverse_or_state_matching'


def test_partial_prefix_never_favourable_score(case,monkeypatch):
    from ncmemsim.temperature_context import ThermalSimulator
    original=ThermalSimulator.relax_voltage
    calls=0
    def fail(self,*args,**kwargs):
        nonlocal calls
        if kwargs.get('dwell_time_s',0)>0:
            calls+=1
            if calls==3:raise RuntimeError('intentional third physical step failure')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(ThermalSimulator,'relax_voltage',fail)
    source=run_electrical_sequence(case[0]);s=analyze(case,source=source).summary
    assert s['reason']=='incomplete_sequence' and s['observed_update_count']==2
    assert s['update_coverage_fraction']==.5 and s['linearity_deviation'] is None
    assert len(s['weight_proxy'])==3
    assert source.to_dict()['failure']['stage']=='step'


@pytest.mark.parametrize('field',['summary','source_hash','reference','expected_direction','minimum_excursion_V'])
def test_tamper_rejected(case,field):
    raw=analyze(case).to_dict()
    if field=='summary':raw[field]['linearity_deviation']=0.
    elif field=='source_hash':raw[field]='0'*64
    elif field=='reference':raw[field]['formula']='clip(R)'
    elif field=='expected_direction':raw[field]='increasing'
    else:raw[field]=10.
    with pytest.raises(ValueError):GradualUpdateAnalysis.from_dict(raw)


def test_strict_schema_and_duplicate_json(case):
    analysis=analyze(case);raw=analysis.to_dict();raw['extra']=0
    with pytest.raises(ValueError):GradualUpdateAnalysis.from_dict(raw)
    with pytest.raises(ValueError):GradualUpdateAnalysis.from_json('{"x":1,"x":2}')
    with pytest.raises(ValueError):GradualUpdateAnalysis.from_json('{"x":NaN}')
    with pytest.raises(ValueError):analyze_gradual_updates(None,case[3],expected_direction='increasing',minimum_excursion_V=1)


def test_no_solver_or_rng_on_restoration(case,monkeypatch):
    from ncmemsim.temperature_context import ResolvedThermalContext, ThermalSimulator
    import numpy as np
    a=analyze(case)
    b=analyze(case,direction='increasing',source=case[5])
    pair=analyze_paired_updates(a,b)
    def forbidden(*args,**kwargs):raise AssertionError('workflow or random replay')
    monkeypatch.setattr(ResolvedThermalContext,'create_simulator',forbidden)
    monkeypatch.setattr(ThermalSimulator,'relax_voltage',forbidden)
    monkeypatch.setattr(np.random,'default_rng',forbidden)
    assert GradualUpdateAnalysis.from_json(a.to_json()).to_dict()==a.to_dict()
    assert PairedUpdateAnalysis.from_json(pair.to_json()).to_dict()==pair.to_dict()


def test_nonrepresentable_weight_is_explicitly_unassessable(case,monkeypatch):
    actual_source=updates._source
    def source(raw):
        result,exp,optical=actual_source(raw)
        return SimpleNamespace(contract_hash=result.contract_hash,
            summary={**result.summary,'read_delta_vfb_V':[0.,1e308,1e308,1e308,1e308]}),exp,optical
    monkeypatch.setattr(updates,'_source',source)
    s=analyze(case,direction='increasing').summary
    assert s['reason']=='nonrepresentable_normalization' and s['linearity_deviation'] is None
    assert s['weight_proxy'][1] is None and s['signed_weight_updates'][0] is None


def test_paired_duration_mismatch_remains_unassessable(case):
    exp=case[1]
    steps=tuple(replace(s,duration_s=2e-7) for s in exp.sequence.steps)
    changed=replace(exp,sequence=replace(exp.sequence,steps=steps))
    second=analyze(case,direction='increasing',source=run_electrical_sequence(changed))
    paired=analyze_paired_updates(analyze(case),second)
    assert paired.summary['reason']=='unmatched_segment_count_duration_or_timestep'
    assert paired.summary['asymmetry'] is None and paired.summary['matched_update_count']==0
    raw=paired.to_dict();raw['summary']['asymmetry']=0.
    with pytest.raises(ValueError):PairedUpdateAnalysis.from_dict(raw)
