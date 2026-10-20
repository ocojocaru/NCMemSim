# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Q5 independent retention delays, fixed margins/references and failure coverage."""
from dataclasses import replace, FrozenInstanceError
import pytest
import numpy as np
from examples.phase_q5_retention_ensemble_reference import build_study, EVIDENCE
from ncmemsim.multilevel_contracts import WeightReferenceMapping
from ncmemsim.multilevel_analysis import run_multilevel_study, analyze_multilevel_results
from ncmemsim.multilevel_execution import ElectricalSequenceResult
from ncmemsim.multilevel_retention import (MultilevelRetentionPlan, MultilevelRetentionResult,
    run_multilevel_retention, analyze_multilevel_retention, _separation)
from ncmemsim.temperature_context import ThermalSimulator, ResolvedThermalContext


@pytest.fixture(scope='module')
def case():
    study=build_study();prepared=run_multilevel_study(study)
    first=study.levels[0].experiment
    reference=WeightReferenceMapping('test fixed reference',first.context.context_hash,
        first.sequence.readout.contract_hash,-.02,0.,.001,'assumed low','assumed high','this test context',EVIDENCE)
    plan=MultilevelRetentionPlan(prepared,(0.,1e-7,2e-7),0.,1e-8,EVIDENCE,reference)
    return study,prepared,plan,run_multilevel_retention(plan)


def test_independent_delay_origin_fixed_reference_and_accounting(case):
    study,prepared,plan,result=case;raw=result.to_dict();s=result.summary
    assert s['complete'] and s['requested_observation_count']==s['completed_observation_count']==9
    assert s['requested_probe_count']==s['eligible_probe_count']==s['attempted_probe_count']==s['completed_probe_count']==6
    assert s['failed_probe_count']==s['missing_probe_count']==0
    for j,delay in enumerate(plan.delays_s):
        for i,row in enumerate(s['delays'][j]['levels']):
            baseline=prepared.to_dict()['results'][i]
            assert row['actual_elapsed_s']==pytest.approx(delay,abs=1e-20)
            assert row['weight_proxy']==pytest.approx((row['readout_V']+.02)/.02)
            assert row['signed_drift_V']==row['readout_V']-baseline['steps'][-1]['read']['delta_vfb_V']
            if j==0:
                assert raw['probes'][j][i] is None and row['signed_drift_V']==0
            else:
                probe=raw['probes'][j][i]
                assert probe['experiment']['initial_state']==baseline['steps'][-1]['final_state']
                assert probe['experiment']['sequence']['steps'][0]['duration_s']==delay
                assert probe['steps'][0]['final_state']['time_s']==baseline['steps'][-1]['final_state']['time_s']+delay
                assert probe['experiment']['sequence']['readout']==study.levels[i].experiment.sequence.readout.to_dict()
    assert s['delays'][0]['separation']['minimum_signed_margin_V']==prepared.summary['minimum_signed_margin_V']
    assert MultilevelRetentionResult.from_json(result.to_json()).contract_hash==result.contract_hash
    assert MultilevelRetentionPlan.from_json(plan.to_json()).contract_hash==plan.contract_hash
    with pytest.raises(FrozenInstanceError):plan.internal_dt_s=1
    copy=result.summary;copy['delays'].clear();assert len(result.summary['delays'])==3


def test_direct_existing_dark_stepping(case):
    study,prepared,plan,result=case
    for i,level in enumerate(study.levels):
        baseline=ElectricalSequenceResult.from_dict(prepared.to_dict()['results'][i])
        for j,delay in enumerate(plan.delays_s[1:],1):
            sim=level.experiment.context.create_simulator()
            direct=sim.relax_voltage(baseline.final_state,0.,delay,plan.internal_dt_s,
                light_source=None,occupancy_integrator='backward_euler')['state']
            archived=ElectricalSequenceResult.from_dict(result.to_dict()['probes'][j][i]).final_state
            for a,b in zip(direct.floating_gates,archived.floating_gates,strict=True):
                np.testing.assert_array_equal(a.P0,b.P0);np.testing.assert_array_equal(a.P1,b.P1)
                np.testing.assert_array_equal(a.P2,b.P2)


@pytest.mark.parametrize('field,value',[
    ('delays_s',()),('delays_s',[0.,1e-7]),('delays_s',(1e-7,)),
    ('delays_s',(0.,0.)),('delays_s',(0.,2e-7,1e-7)),('delays_s',(0.,-1.)),
    ('delays_s',(False,1e-7)),('delays_s',(0.,float('inf'))),
    ('delays_s',(0.,float('nan'))),('delays_s',(0.,'1')),
    ('internal_dt_s',0),('internal_dt_s',True),('internal_dt_s',float('inf')),
    ('internal_dt_s',1e-6),('retention_voltage_V',True),('retention_voltage_V',float('nan')),
])
def test_invalid_schedule(case,field,value):
    with pytest.raises(ValueError):replace(case[2],**{field:value})


def test_wrong_reference_and_unrepresentable_clock(case):
    with pytest.raises(ValueError):replace(case[2],reference=replace(case[2].reference,context_hash='0'*64))
    with pytest.raises(ValueError):replace(case[2],delays_s=(0.,1e-300),internal_dt_s=1e-301)


def test_zero_only_reuses_baseline_without_solver(case,monkeypatch):
    plan=replace(case[2],delays_s=(0.,))
    def forbidden(*args,**kwargs):raise AssertionError('zero delay must not integrate')
    monkeypatch.setattr(ResolvedThermalContext,'create_simulator',forbidden)
    result=run_multilevel_retention(plan)
    assert result.summary['complete'] and result.summary['attempted_probe_count']==0
    assert result.summary['completed_observation_count']==3


def test_failed_hold_does_not_stop_other_delays(case,monkeypatch):
    original=ThermalSimulator.relax_voltage
    def fail(self,*args,**kwargs):
        if kwargs.get('dwell_time_s')==1e-7:raise RuntimeError('intentional short probe failure')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(ThermalSimulator,'relax_voltage',fail)
    result=run_multilevel_retention(case[2]);s=result.summary
    assert s['failed_probe_count']==3 and s['completed_probe_count']==3
    assert s['completed_observation_count']==6 and s['observation_coverage_fraction']==2/3
    assert s['delays'][1]['separation']['status']=='not_assessable'
    assert all(x['actual_elapsed_s']==0 and x['readout_V'] is None for x in s['delays'][1]['levels'])
    assert all(x['status']=='completed' for x in s['delays'][2]['levels'])
    assert MultilevelRetentionResult.from_json(result.to_json()).to_dict()==result.to_dict()


def test_missing_probe_and_unavailable_preparation(case):
    raw=case[3].to_dict()
    rows=tuple(tuple(None if x is None else ElectricalSequenceResult.from_dict(x) for x in row) for row in raw['probes'])
    missing=(rows[0],(None,*rows[1][1:]),rows[2])
    result=analyze_multilevel_retention(case[2],missing)
    assert result.summary['missing_probe_count']==1 and result.summary['attempted_probe_count']==5
    assert result.summary['delays'][1]['levels'][0]['status']=='missing_probe'
    original=case[1].to_dict()['results']
    prepared=analyze_multilevel_results(case[0],tuple(None if i==1 else ElectricalSequenceResult.from_dict(x)
                                                     for i,x in enumerate(original)))
    plan=replace(case[2],prepared=prepared)
    result=run_multilevel_retention(plan)
    assert result.summary['unavailable_preparation_observation_count']==3
    assert result.summary['eligible_probe_count']==4 and result.summary['completed_observation_count']==6
    assert result.summary['delays'][0]['separation']['status']=='not_assessable'


@pytest.mark.parametrize('values,status,crossings',[
    ((0.,.002,.004),'passed',0),((0.,0.,.004),'failed',0),
    ((.003,.002,.004),'failed',1),((0.,None,.004),'not_assessable',0),
    ((.003,.002,None),'failed',1),
])
def test_declared_order_crossings_collapse_and_missing(case,values,status,crossings):
    rows=[{'level_id':x.level_id,'readout_V':value} for x,value in zip(case[0].levels,values,strict=True)]
    result=_separation(rows,case[0])
    assert result['status']==status and result['crossed_pair_count']==crossings


def test_fixed_assumed_intervals_and_nonrepresentable_margin(case):
    study=replace(case[0],interval_kind='assumed_bounds',levels=tuple(
        replace(x,readout_half_width_V=.01) for x in case[0].levels))
    rows=[{'level_id':x.level_id,'readout_V':i*.002} for i,x in enumerate(study.levels)]
    assert _separation(rows,study)['status']=='failed'
    study=replace(study,levels=tuple(replace(x,readout_half_width_V=1e308) for x in study.levels))
    assert _separation(rows,study)['status']=='not_assessable'


@pytest.mark.parametrize('kind',['source','clock','summary','order'])
def test_tamper_rejected(case,kind):
    raw=case[3].to_dict()
    if kind=='source':raw['plan_hash']='0'*64
    elif kind=='clock':raw['probes'][1][0]['steps'][0]['final_state']['time_s']+=1e-7
    elif kind=='summary':raw['summary']['completed_probe_count']=0
    else:raw['probes'][1].reverse()
    with pytest.raises(ValueError):MultilevelRetentionResult.from_dict(raw)


def test_static_restore_without_integration_or_rng(case,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('replayed solver or RNG')
    monkeypatch.setattr(ResolvedThermalContext,'create_simulator',forbidden)
    monkeypatch.setattr(ThermalSimulator,'relax_voltage',forbidden)
    monkeypatch.setattr(np.random,'default_rng',forbidden)
    assert MultilevelRetentionResult.from_json(case[3].to_json()).to_dict()==case[3].to_dict()
    with pytest.raises(ValueError):MultilevelRetentionResult.from_json('{"x":1,"x":2}')
    with pytest.raises(ValueError):MultilevelRetentionPlan.from_json('{"x":NaN}')


def test_schedule_rejects_nonrepresentable_subdivision_without_prepared_evidence():
    from ncmemsim.multilevel_retention import _schedule
    with pytest.raises(ValueError):_schedule((0.,1e100),0.,1e-300)
