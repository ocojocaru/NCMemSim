# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""R5 controlled residuals, source binding, missing conditions and negative outcomes."""
import copy
from fractions import Fraction
import hashlib
import json
import pytest
from examples.phase_r5_interoperability_reference import build_reference_comparisons, run_reference
from ncmemsim.interoperability import InteroperabilityDataset, ObservableMapping
from ncmemsim.interoperability_comparison import InteroperabilityComparison, compare_interoperability_data


@pytest.fixture
def base():
    return build_reference_comparisons()[0]['unit_axis_area_match']


def changed(base, **updates):
    raw = base.to_dict(); raw.update(updates)
    return InteroperabilityComparison.from_dict(raw)


def rebind(raw, label):
    digest=InteroperabilityDataset.from_dict(raw[label]).contract_hash
    for suffix in ('axis','values'):
        raw['mappings'][label+'_'+suffix]['dataset_hash']=digest


def test_reference_controls_and_genuine_upstream_digests():
    evidence=run_reference()
    assert len(evidence['results'])==9
    assert not evidence['external_agreement'] and not evidence['experimental_qualification']
    for digest,text in evidence['upstream_sources'].items():
        assert hashlib.sha256(text.encode()).hexdigest()==digest
        assert json.loads(text)['columns']
    for result in evidence['results'].values():
        assert not result['external_agreement'] and not result['experimental_qualification']
        for label in ('reference','candidate'):
            data=result['declaration'][label]
            upstream=json.loads(evidence['upstream_sources'][data['source']['file_sha256']])
            assert data['metadata']==upstream['metadata'] and data['columns']==upstream['columns']
    mismatch=evidence['results']['negative_value_mismatch']
    assert mismatch['assessed_count']==3 and mismatch['mismatched_count']==1
    residual=mismatch['value_comparison'][-1]['residual']
    assert Fraction(int(residual['numerator']),int(residual['denominator']))==1


def test_roundtrip_ownership_and_source_binding(base):
    restored=InteroperabilityComparison.from_json(base.to_json())
    assert restored.contract_hash==base.contract_hash
    assert compare_interoperability_data(restored)==compare_interoperability_data(base)
    raw=base.to_dict(); raw['candidate']['columns'][1]['values'][1]=123
    assert base.to_dict()['candidate']['columns'][1]['values'][1]==2e-12
    with pytest.raises(ValueError): InteroperabilityComparison.from_dict(raw)
    with pytest.raises(AttributeError): base.extra=True
    with pytest.raises(AttributeError): del base._serialized
    result=compare_interoperability_data(base)
    result['declaration']['target_metadata']['coordinates']['origin']='changed'
    assert base.to_dict()['target_metadata']['coordinates']['origin']!='changed'


@pytest.mark.parametrize('fault', ['extra','missing','schema','duplicate_json','nonfinite_json'])
def test_strict_reader_rejects_unreviewed_declarations(base,fault):
    raw=base.to_dict()
    if fault=='extra':raw['other']=1
    elif fault=='missing':del raw['atol']
    elif fault=='schema':raw['schema_version']='future'
    elif fault=='duplicate_json':
        with pytest.raises(ValueError): InteroperabilityComparison.from_json('{"a":1,"a":2}')
        return
    else:
        with pytest.raises(ValueError): InteroperabilityComparison.from_json('{"a":NaN}')
        return
    with pytest.raises(ValueError): InteroperabilityComparison.from_dict(raw)


@pytest.mark.parametrize('key', ['axis_atol','axis_rtol','atol','rtol'])
@pytest.mark.parametrize('value', [-1,True,float('nan'),float('inf')])
def test_tolerances_are_explicit_finite_nonnegative(base,key,value):
    with pytest.raises(ValueError): changed(base,**{key:value})


@pytest.mark.parametrize('fault',['missing_mapping','wrong_dataset','wrong_column','axis_is_signal',
    'different_target_unit','different_target_quantity','missing_review','empty_review','invalid_target_metadata'])
def test_incompatible_or_unreviewed_plan_fails(base,fault):
    raw=base.to_dict()
    if fault=='missing_mapping':del raw['mappings']['reference_axis']
    elif fault=='wrong_dataset':raw['mappings']['candidate_values']['dataset_hash']='0'*64
    elif fault=='wrong_column':raw['mappings']['candidate_values']['column']='absent'
    elif fault=='axis_is_signal':raw['mappings']['candidate_axis']['column']='signal'
    elif fault=='different_target_unit':raw['mappings']['candidate_axis']['target_unit']='nm'
    elif fault=='different_target_quantity':
        raw['mappings']['candidate_values'].update(target_quantity='current_per_area',target_unit='A/m^2')
    elif fault=='missing_review':del raw['applicability_review']['reference']
    elif fault=='empty_review':raw['applicability_review']['candidate']=''
    else:raw['target_metadata']['coordinates']={'origin':'zero'}
    with pytest.raises(ValueError): InteroperabilityComparison.from_dict(raw)


def test_semantic_substitution_not_hidden_as_missing_data(base):
    raw=base.to_dict()
    # Valid dimensions on both target declarations cannot turn charge into current.
    for side in ('reference','candidate'):
        raw['mappings'][side+'_values'].update(target_quantity='current_per_area',target_unit='A/m^2')
    plan=InteroperabilityComparison.from_dict(raw)
    with pytest.raises(ValueError): compare_interoperability_data(plan)


@pytest.mark.parametrize('location',['reference','candidate','target_metadata'])
def test_missing_common_condition_stays_unavailable(base,location):
    raw=base.to_dict()
    if location=='target_metadata':raw[location]['initial_state']=None
    else:
        raw[location]['metadata']['initial_state']=None
        rebind(raw,location)
    result=compare_interoperability_data(InteroperabilityComparison.from_dict(raw))
    assert result['status']=='unavailable' and result['assessed_count']==0
    assert result['value_comparison']==[] and result['reasons']


def test_subset_match_does_not_claim_full_coverage():
    cases,_=build_reference_comparisons()
    result=compare_interoperability_data(cases['matched_retained_subset'])
    assert result['status']=='matched' and not result['full_coverage']
    assert result['scope']=='retained_rows_only' and result['assessed_fraction']==2/3
    assert [row['index'] for row in result['value_comparison']]==[0,2]
    for coverage in result['coverage'].values():
        assert coverage['excluded_count']==1 and coverage['original_count']==3
    result=compare_interoperability_data(cases['different_exclusion_masks'])
    assert result['status']=='unavailable' and result['assessed_count']==0


def test_grid_mismatch_is_not_silently_sorted_or_interpolated():
    cases,_=build_reference_comparisons()
    result=compare_interoperability_data(cases['ordered_grid_mismatch'])
    assert result['status']=='unavailable' and result['value_comparison']==[]
    assert any(not row['within_tolerance'] for row in result['axis_comparison'])


def test_signed_residual_and_boundary_tolerances(base):
    raw=base.to_dict()
    for side in ('reference','candidate'):
        raw[side]['columns'][1].update(quantity='charge_per_area',unit='C/m^2',values=[0.,1.,2.])
        raw['mappings'][side+'_values']['area_operation']='none'
        rebind(raw,side)
    raw['candidate']['columns'][1]['values']=[0.,.5,2.5]; rebind(raw,'candidate')
    raw.update(atol=.5,rtol=0.)
    result=compare_interoperability_data(InteroperabilityComparison.from_dict(raw))
    assert result['status']=='matched'
    assert result['value_comparison'][1]['residual']=={'numerator':'-1','denominator':'2'}
    raw['atol']=.499
    assert compare_interoperability_data(InteroperabilityComparison.from_dict(raw))['mismatched_count']==2


def test_extreme_residual_does_not_overflow_into_false_match(base):
    raw=base.to_dict()
    for side,number in [('reference',-1e308),('candidate',1e308)]:
        raw[side]['columns'][1].update(quantity='charge_per_area',unit='C/m^2',values=[number]*3)
        raw['mappings'][side+'_values']['area_operation']='none'; rebind(raw,side)
    raw.update(atol=0.,rtol=0.)
    result=compare_interoperability_data(InteroperabilityComparison.from_dict(raw))
    assert result['status']=='mismatched' and result['mismatched_count']==3
    json.dumps(result,allow_nan=False)


def test_all_excluded_and_different_lengths_are_unavailable(base):
    raw=base.to_dict()
    for side in ('reference','candidate'):
        raw[side]['exclusions']=[{'index':i,'reason':'synthetic complete exclusion'} for i in range(3)]
        rebind(raw,side)
    assert compare_interoperability_data(InteroperabilityComparison.from_dict(raw))['status']=='unavailable'
    raw=base.to_dict()
    for column in raw['candidate']['columns']:column['values'].pop()
    rebind(raw,'candidate')
    assert compare_interoperability_data(InteroperabilityComparison.from_dict(raw))['status']=='unavailable'
