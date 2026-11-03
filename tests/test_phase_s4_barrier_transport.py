# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Opt-in replacement, context/mapping safety and conservative simulator integration."""
import copy
from dataclasses import replace
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import numpy as np
import pytest
from ncmemsim import DeviceBuilder, DeviceState, PhysicsModel, Simulator
from ncmemsim.simulator import SimulationConfig
from ncmemsim.barrier_transport import (
    BarrierTransportContext, BarrierLinkAttachment, BarrierTransportSpec,
    ProfiledTransportStepResult, BarrierTransportEngine,
)
from ncmemsim.transport import AdvancedTransportEngine

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('s4_reference', ROOT/'examples/phase_s4_barrier_transport_reference.py')
study=importlib.util.module_from_spec(spec);spec.loader.exec_module(study)


@pytest.fixture
def scene(): return study.setup()


def engine(scene, mode='active'):
    return BarrierTransportEngine(scene[2], lambda context: study.make_plan(context, mode), 'synthetic-test-'+mode)


def compare_state(actual, expected):
    for left, right in zip(actual.floating_gates, expected.floating_gates):
        for key in ('P0','P1','P2'): np.testing.assert_array_equal(getattr(left,key),getattr(right,key))
    assert actual.time_s==expected.time_s


def test_no_provider_delegates_disabled_baseline_exactly(scene):
    device, physics, baseline, state, field=scene
    expected, direct=baseline.step(device,state,field,physics.occupancy,1e-6)
    actual, result=BarrierTransportEngine(baseline).step(device,state,field,physics.occupancy,1e-6)
    compare_state(actual,expected)
    assert result.links==direct.links
    np.testing.assert_array_equal(result.net_electron_flux_by_fg_m2_s,direct.net_electron_flux_by_fg_m2_s)


def test_disabled_explicit_plan_is_bit_identical(scene,monkeypatch):
    import ncmemsim.barrier_transport as module
    def forbidden(*args): raise AssertionError('disabled plan evaluated a barrier')
    monkeypatch.setattr(module,'_evaluate_profile',forbidden)
    device,physics,baseline,state,field=scene
    expected,direct=baseline.step(device,state,field,physics.occupancy,1e-6)
    actual,result=engine(scene,'disabled').step(device,state,field,physics.occupancy,1e-6)
    compare_state(actual,expected)
    assert [row.selected for row in result.links]==list(direct.links)
    assert all(row.status in ('disabled','diagnostic_only') for row in result.links)


@pytest.mark.parametrize('index',range(3))
def test_owned_contract_roundtrip_and_isolation(scene,index):
    device,physics,baseline,state,field=scene
    context=engine(scene).capture_context(device,state,field,physics.occupancy)
    plan=study.make_plan(context)
    values=[context,BarrierLinkAttachment.from_dict(plan.to_dict()['attachments'][0]),plan]
    value=values[index]; raw=value.to_dict()
    assert type(value).from_json(value.to_json()).contract_hash==value.contract_hash
    raw['schema_version']='mutated'
    assert value.to_dict()['schema_version']!='mutated'
    with pytest.raises(AttributeError): value._serialized='mutated'
    with pytest.raises(AttributeError): del value._serialized
    with pytest.raises(ValueError): type(value).from_dict(raw)
    with pytest.raises(ValueError): type(value).from_json(value.to_json().replace('{','{"schema_version":"forged",',1))


def test_snapshot_access_has_no_live_arrays_or_material_alias(scene):
    device,physics,baseline,state,field=scene
    context=engine(scene).capture_context(device,state,field,physics.occupancy)
    raw=context.snapshot; raw['state']['floating_gates'][0]['P0'].clear()
    raw['device']['full_declaration']['layers'].clear()
    assert len(state.floating_gates[0].P0)>0 and len(device.layers)>0
    assert len(context.snapshot['device']['layers'])>0


@pytest.mark.parametrize('fault',['extra','missing','enabled_bool','duplicate_link','disabled_attachments','wrong_policy'])
def test_plan_semantic_validation(scene,fault):
    device,physics,baseline,state,field=scene
    context=engine(scene).capture_context(device,state,field,physics.occupancy)
    raw=study.make_plan(context).to_dict()
    if fault=='extra':raw['extra']=1
    elif fault=='missing':del raw['context_hash']
    elif fault=='enabled_bool':raw['enabled']=1
    elif fault=='duplicate_link':raw['attachments'].append(raw['attachments'][0])
    elif fault=='disabled_attachments':raw['enabled']=False
    else:raw['failure_policy']='fallback_to_legacy'
    with pytest.raises(ValueError):BarrierTransportSpec.from_dict(raw)


@pytest.mark.parametrize('fault',['unknown_link','contacts','origin','axis','direction','layer','length','missing_layer_map'])
def test_mapping_errors_rejected_without_state_advance(scene,fault):
    device,physics,baseline,state,field=scene; before=copy.deepcopy(state)
    def provider(context):
        raw=study.make_plan(context).to_dict(); item=raw['attachments'][0]
        profile=item['request']['profile']
        if fault=='unknown_link':item['link_id']='unknown'
        elif fault=='contacts':profile['source_contact']='other node'
        elif fault=='origin':profile['axis_origin']='other origin'
        elif fault=='axis':profile['positive_axis_direction']='right to left'
        elif fault=='direction':profile['traversal_direction']='against_positive_axis'
        elif fault=='layer':item['segment_layer_names'][0]='unknown dielectric'
        elif fault=='length':profile['segments'][0]['length_m']*=2
        else:item['segment_layer_names']=[]
        return BarrierTransportSpec.from_dict(raw)
    with pytest.raises(ValueError):BarrierTransportEngine(baseline,provider,'bad-mapping').step(device,state,field,physics.occupancy,1e-6)
    compare_state(state,before)


def test_substrate_cannot_be_attached(scene):
    device,physics,baseline,state,field=scene
    def provider(context):
        raw=study.make_plan(context).to_dict(); substrate=context.snapshot['network']['links'][-1]
        raw['attachments'][0]['link_id']=substrate['link_id']
        return BarrierTransportSpec.from_dict(raw)
    with pytest.raises(ValueError,match='substrate'):BarrierTransportEngine(baseline,provider,'no-substrate').evaluate(device,state,field,physics.occupancy)


@pytest.mark.parametrize('change',['state','time','field','temperature','material','config'])
def test_stale_context_detects_all_runtime_changes(scene,change):
    device,physics,baseline,state,field=scene
    wrapper=engine(scene)
    plan=study.make_plan(wrapper.capture_context(device,state,field,physics.occupancy))
    fixed=BarrierTransportEngine(baseline,lambda context:plan,'stale-control')
    if change=='state':state.floating_gates[0].P1[:]=.5;state.floating_gates[0].P0[:]=.5
    elif change=='time':state.time_s+=1
    elif change=='field':field.potential_V[-1]+=.1
    elif change=='temperature':device.temperature_K+=1
    elif change=='material':
        fg=device.floating_gates()[0]
        fg.matrix_material=replace(fg.matrix_material,eps_r=fg.matrix_material.eps_r+1)
    else:baseline.config=replace(baseline.config,attempt_frequency_Hz=1e12)
    with pytest.raises(ValueError,match='stale'):fixed.evaluate(device,state,field,physics.occupancy)


def test_mutating_snapshot_copy_does_not_affect_live_inputs(scene):
    device,physics,baseline,state,field=scene; original=copy.deepcopy(state)
    def provider(context):
        raw=context.snapshot;raw['state']['floating_gates'][0]['P1'].clear()
        return study.make_plan(context)
    BarrierTransportEngine(baseline,provider,'copy-only').evaluate(device,state,field,physics.occupancy)
    compare_state(state,original)


def test_provider_side_effect_is_detected(scene):
    device,physics,baseline,state,field=scene
    def provider(context):
        state.time_s+=1
        return study.make_plan(context)
    with pytest.raises(ValueError,match='side-effect free'):BarrierTransportEngine(baseline,provider,'unsupported-side-effect').evaluate(device,state,field,physics.occupancy)


def test_replacement_is_not_added_to_legacy_rates(scene):
    device,physics,baseline,state,field=scene
    result=engine(scene).evaluate(device,state,field,physics.occupancy)
    for row in result.links:
        if row.kind=='substrate':assert row.selected==row.baseline;continue
        assert row.status=='profile_replaced'
        bias=1/(1+math.exp(-baseline.config.direction_beta_V_inv*row.potential_difference_V))
        assert row.forward_rate_Hz==baseline.config.attempt_frequency_Hz*row.evaluation.summary['transmission']*bias
        assert row.forward_rate_Hz!=row.baseline.forward_rate_Hz+baseline.config.attempt_frequency_Hz*row.transmission*bias
    expected=np.zeros(3)
    for row in result.links:
        if row.kind=='inter_fg':expected[row.left_fg_index]-=row.net_electron_flux_m2_s;expected[row.right_fg_index]+=row.net_electron_flux_m2_s
    np.testing.assert_array_equal(result.net_electron_flux_by_fg_m2_s,expected)
    assert not result.net_electron_flux_by_fg_m2_s.flags.writeable


def test_only_selected_link_changes_and_substrate_remains_diagnostic(scene):
    device,physics,baseline,state,field=scene
    def provider(context):
        raw=study.make_plan(context).to_dict();raw['attachments']=raw['attachments'][:1]
        return BarrierTransportSpec.from_dict(raw)
    result=BarrierTransportEngine(baseline,provider,'one-link').evaluate(device,state,field,physics.occupancy)
    assert result.links[0].status=='profile_replaced'
    assert result.links[1].status=='not_attached' and result.links[1].selected==result.links[1].baseline
    assert result.links[-1].status=='diagnostic_only' and result.links[-1].net_electron_flux_m2_s==0


def test_failed_profile_zeroes_only_its_selected_flux_without_fallback(scene):
    device,physics,baseline,state,field=scene
    result=engine(scene,'partial_failure').evaluate(device,state,field,physics.occupancy)
    first=result.links[0]
    assert first.status=='failed' and first.evaluation.summary['status']=='failed'
    assert first.forward_rate_Hz==first.backward_rate_Hz==first.net_electron_flux_m2_s==0
    assert first.baseline.net_electron_flux_m2_s!=0
    assert result.links[1].status=='profile_replaced' and result.links[1].net_electron_flux_m2_s!=0


def test_transmission_underflow_is_completed_zero_flux_not_failure(scene):
    device,physics,baseline,state,field=scene
    updated,result=engine(scene,'underflow').step(device,state,field,physics.occupancy,1e-6)
    compare_state(updated,state)
    for row in result.links[:-1]:
        assert row.status=='profile_replaced' and row.transmission==0
        assert row.evaluation.summary['attenuation_status']=='transmission_underflow'


@pytest.mark.parametrize('mode',['active','partial_failure','underflow'])
@pytest.mark.parametrize('dt',[0.,1e-12,1e-6,1.])
def test_conservation_normalization_and_source_state_ownership(scene,mode,dt):
    device,physics,baseline,state,field=scene
    device.floating_gates()[0].electrically_active_fraction*=.3
    device.floating_gates()[1].electrically_active_fraction*=.7
    state.metadata={'nested':{'label':'original'}}
    before=copy.deepcopy(state); total=study.electron_sheet(device,physics.occupancy,state)
    updated,result=engine(scene,mode).step(device,state,field,physics.occupancy,dt)
    updated.validate(device);compare_state(state,before)
    actual=study.electron_sheet(device,physics.occupancy,updated)
    assert abs(actual-total)<=1e-12*max(abs(total),1.)
    updated.metadata['nested']['label']='changed'
    assert state.metadata['nested']['label']=='original'


@pytest.mark.parametrize('value',[-1,True,math.nan,math.inf,'1'])
def test_enabled_step_rejects_invalid_time(scene,value):
    device,physics,baseline,state,field=scene
    with pytest.raises(ValueError):engine(scene).step(device,state,field,physics.occupancy,value)


def test_advanced_tat_and_nested_wrappers_rejected(scene):
    baseline=scene[2]
    for unsupported in (AdvancedTransportEngine(baseline),BarrierTransportEngine(baseline)):
        with pytest.raises(ValueError):BarrierTransportEngine(unsupported)
    with pytest.raises(ValueError):BarrierTransportEngine(baseline,provider='not callable',provider_id='bad')
    with pytest.raises(ValueError):BarrierTransportEngine(baseline,lambda context:None)


def test_multi_dielectric_layer_order_is_checked():
    device,physics,baseline,state,field=study.setup()
    device=DeviceBuilder.v1(3,inter_fg_sio2_nm=1.,inter_fg_hfo2_nm=2.)
    state=DeviceState.empty_for_device(device)
    field=__import__('ncmemsim.fieldsolver',fromlist=['FieldSolver1D']).FieldSolver1D().solve(device,0.,np.zeros(3))
    accepted=BarrierTransportEngine(baseline,study.make_plan,'multi-layer').evaluate(device,state,field,physics.occupancy)
    assert accepted.links[0].status=='profile_replaced'
    assert len(accepted.links[0].evaluation.to_dict()['request']['profile']['segments'])==2
    def subdivided(context):
        raw=study.make_plan(context).to_dict();item=raw['attachments'][0]
        original=item['request']['profile']['segments'];rows=[];names=[]
        for row,name in zip(original,item['segment_layer_names']):
            left=copy.deepcopy(row);right=copy.deepcopy(row)
            middle=(row['start_potential_energy_J']+row['end_potential_energy_J'])/2
            left['length_m']/=2;right['length_m']/=2
            left['segment_id']+='/a';right['segment_id']+='/b'
            left['end_potential_energy_J']=middle;right['start_potential_energy_J']=middle
            rows.extend([left,right]);names.extend([name,name])
        item['request']['profile']['segments']=rows;item['segment_layer_names']=names
        return BarrierTransportSpec.from_dict(raw)
    accepted=BarrierTransportEngine(baseline,subdivided,'subdivided-layers').evaluate(device,state,field,physics.occupancy)
    assert accepted.links[0].status=='profile_replaced'
    assert len(accepted.links[0].evaluation.to_dict()['request']['profile']['segments'])==4
    def provider(context):
        raw=study.make_plan(context).to_dict()
        raw['attachments'][0]['segment_layer_names'].reverse()
        return BarrierTransportSpec.from_dict(raw)
    with pytest.raises(ValueError,match='layer mapping'):BarrierTransportEngine(baseline,provider,'wrong-order').evaluate(device,state,field,physics.occupancy)


def test_simulator_requests_fresh_plans_with_existing_injection_unchanged(scene):
    device,physics,baseline,state,field=scene
    seen=[]
    def provider(context):
        seen.append(context.contract_hash)
        return study.make_plan(context)
    physics.transport=BarrierTransportEngine(baseline,provider,'fresh-simulator-plan')
    original_tunneling=physics.occupancy.tunneling
    simulator=Simulator(device,physics,SimulationConfig(internal_dt_s=1e-9))
    result=simulator.relax_voltage(state,.1,dwell_time_s=3e-9)
    result['state'].validate(device)
    assert len(seen)>=3 and len(set(seen))>1
    assert physics.occupancy.tunneling is original_tunneling
    assert all(row.status=='profile_replaced' for row in result['transport_link_results'] if row.kind=='inter_fg')
    assert all(row.context.contract_hash==seen[-1] and row.provider_id=='fresh-simulator-plan'
               for row in result['transport_link_results'])


def test_reference_review_is_source_pinned_and_failures_remain_explicit():
    review=json.loads((ROOT/'docs/barrier_transport_integration_review.json').read_text(encoding='utf-8'))
    for path,digest in review['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_text(encoding='utf-8').encode()).hexdigest()==digest
    rows=study.build_reference()['cases']
    assert [row['status'] for row in rows['partial_failure']['result']['links']]==['failed','profile_replaced','diagnostic_only']
    for case in rows.values():
        assert abs(case['conservation_error_m2'])<=1e-12*case['before_electron_sheet_m2']
    assert not review['experimental_qualification']


def test_bad_provider_return_and_non_native_context_rejected(scene):
    device,physics,baseline,state,field=scene
    with pytest.raises(ValueError,match='owned BarrierTransportSpec'):
        BarrierTransportEngine(baseline,lambda context:{},'bad-return').evaluate(device,state,field,physics.occupancy)
    state.metadata['unsupported']=object()
    with pytest.raises(ValueError,match='unsupported context'):
        engine(scene).evaluate(device,state,field,physics.occupancy)


def test_zero_sheet_density_is_an_explicit_context_domain_error(scene):
    device,physics,baseline,state,field=scene
    device.floating_gates()[0].electrically_active_fraction=0.
    with pytest.raises(ValueError,match='positive sheet'):
        engine(scene).evaluate(device,state,field,physics.occupancy)


def test_overflow_in_selected_flux_is_retained_without_nonfinite_output(scene):
    device,physics,baseline,state,field=scene
    baseline.config=replace(baseline.config,attempt_frequency_Hz=1e300,default_barrier_eV=1000.)
    result=engine(scene).evaluate(device,state,field,physics.occupancy)
    assert all(row.status=='failed' for row in result.links if row.kind=='inter_fg')
    assert all(row.failure=='profile_directional_rate_or_flux_nonfinite' for row in result.links if row.kind=='inter_fg')
    assert all(row.evaluation.summary['status']=='completed' for row in result.links if row.kind=='inter_fg')
    json.dumps(result.to_dict(),allow_nan=False)


def test_nonfinite_snapshot_is_rejected_before_provider(scene):
    device,physics,baseline,state,field=scene
    field.potential_V[0]=math.nan
    with pytest.raises(ValueError,match='nonfinite'):
        engine(scene).evaluate(device,state,field,physics.occupancy)


def test_single_fg_simulator_keeps_injection_in_existing_occupancy_engine():
    device=DeviceBuilder.v2(1); state=DeviceState.empty_for_device(device)
    original=PhysicsModel.default(); profiled=PhysicsModel.default()
    profiled.transport=BarrierTransportEngine(profiled.transport,study.make_plan,'single-FG-no-profile')
    config=SimulationConfig(internal_dt_s=1e-9)
    first=Simulator(device,original,config).relax_voltage(state,.1,dwell_time_s=2e-9)
    second=Simulator(device,profiled,config).relax_voltage(state,.1,dwell_time_s=2e-9)
    compare_state(first['state'],second['state'])
    assert first['qfg_C_m2']==second['qfg_C_m2']
    assert all(row.status=='diagnostic_only' and row.net_electron_flux_m2_s==0 for row in second['transport_link_results'])


def test_global_transport_disable_still_prevents_state_update(scene):
    device,physics,baseline,state,field=scene
    baseline.config=replace(baseline.config,enabled=False)
    updated,result=engine(scene).step(device,state,field,physics.occupancy,1.)
    compare_state(updated,state)
    assert any(row.status=='profile_replaced' for row in result.links)
    assert not result.context.snapshot['transport_config']['enabled']
