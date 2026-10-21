# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""R1 ownership, measurement boundaries and independent numerical-equivalence guards."""
import copy
import json
import pytest
from ncmemsim.performance_contracts import (
    PerformanceWorkload,MeasurementProtocol,PerformanceEnvironment,PerformanceTrial,
    EquivalenceRule,EquivalenceContract,compare_scientific_results,
)


@pytest.fixture
def declarations():
    w=PerformanceWorkload('fixture','sequence',{'device':{'layers':[1,2]},'solver':{'dt_s':1e-9},'initial':[1,0,0]},
        ('execution','validation'),'state_chain',2,'synthetic declared inputs; no benchmark execution')
    p=MeasurementProtocol()
    e=PerformanceEnvironment('a'*40,False,'1.8.0',None,'/synthetic/package/__init__.py','3.13','2.3','synthetic OS','declared CPU',
        None,{k:None for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')},'serial-reference')
    rule=EquivalenceRule('/observations/population','state_population','1',1e-12,1e-8)
    contract=EquivalenceContract(w.contract_hash,(rule,),('/context',),'synthetic reference; tolerances declared for tests only')
    trial=PerformanceTrial(w,p,e,'measurement',0,'completed',.2,'b'*64)
    return w,p,e,rule,contract,trial


@pytest.mark.parametrize('index',range(6))
def test_owned_roundtrip_frozen_and_no_implicit_execution(declarations,index):
    value=declarations[index]
    restored=type(value).from_json(value.to_json())
    assert restored.to_dict()==value.to_dict() and restored.contract_hash==value.contract_hash
    for name in ('extra','_serialized'):
        with pytest.raises(AttributeError):setattr(value,name,'mutated')
    with pytest.raises(AttributeError):del value._serialized
    raw=value.to_dict();raw['schema_version']='caller mutation'
    assert value.to_dict()['schema_version']!='caller mutation'
    with pytest.raises(AttributeError):value._store({})


def test_input_and_nested_access_are_independently_owned():
    data={'grid':[1,2]};scope=['execution']
    w=PerformanceWorkload('owned','relaxation',data,scope,'state_chain',1,'synthetic')
    digest=w.contract_hash;data['grid'].append(3);scope.append('io')
    access=w.scientific_inputs;access['grid'].clear()
    assert w.contract_hash==digest and w.scientific_inputs=={'grid':[1,2]}
    other=PerformanceWorkload('different scope','relaxation',{'grid':[1,2]},('execution','io'),'state_chain',1,'synthetic')
    assert other.scientific_input_hash==w.scientific_input_hash and other.contract_hash!=w.contract_hash


@pytest.mark.parametrize('index',range(6))
@pytest.mark.parametrize('fault',['extra','schema','duplicate','nonfinite'])
def test_strict_archive_and_duplicate_key_rejection(declarations,index,fault):
    obj=declarations[index];raw=obj.to_dict()
    if fault=='duplicate':
        text=obj.to_json().replace('{','{"schema_version":"forged",',1)
        with pytest.raises(ValueError):type(obj).from_json(text)
        return
    if fault=='extra':raw['extra']=True
    elif fault=='schema':raw['schema_version']='unsupported'
    else:raw['extra']=float('nan')
    with pytest.raises(ValueError):type(obj).from_dict(raw)


@pytest.mark.parametrize('value',[True,-1,float('inf'),float('nan'),'5'])
def test_invalid_repeat_counts(value):
    with pytest.raises(ValueError):MeasurementProtocol(measured_count=value)


@pytest.mark.parametrize('kwargs',[{'warmup_count':0},{'measured_count':4},{'max_trial_seconds':0},
    {'max_total_seconds':float('inf')},{'instrumentation':'magic'},{'isolation':'shared_mutable'}])
def test_protocol_boundaries(kwargs):
    with pytest.raises(ValueError):MeasurementProtocol(**kwargs)


@pytest.mark.parametrize('scope',[[],['execution','execution'],['end_to_end','execution'],['unknown']])
def test_ambiguous_scopes_rejected(scope):
    with pytest.raises(ValueError):PerformanceWorkload('bad','sequence',{'x':1},scope,'state_chain',1,'synthetic')


@pytest.mark.parametrize('bad',[{}, {'x':float('nan')},{'x':(1,2)},{1:'wrong key'}])
def test_non_json_or_empty_inputs_rejected(bad):
    with pytest.raises(ValueError):PerformanceWorkload('bad','sequence',bad,['execution'],'state_chain',1,'synthetic')


def test_state_chain_cannot_be_declared_independent():
    with pytest.raises(ValueError):PerformanceWorkload('bad','sequence',{'x':1},['execution'],'independent_items',2,'synthetic')


@pytest.mark.parametrize('kind',['completed','failed','unavailable','warmup','profiled'])
def test_trial_observation_and_nonacceptance_projection(declarations,kind):
    w,p,e,*_=declarations
    phase='warmup' if kind=='warmup' else 'measurement'
    status=kind if kind in ('failed','unavailable') else 'completed'
    elapsed=None if status=='unavailable' else .2
    digest=None if status=='unavailable' else 'b'*64
    reason=None if status=='completed' else {'stage':'worker','type':'Unavailable' if status=='unavailable' else 'Error','message':'explicit reason'}
    if kind=='profiled':p=MeasurementProtocol(instrumentation='cprofile')
    trial=PerformanceTrial(w,p,e,phase,0,status,elapsed,digest,reason)
    assert trial.to_dict()['uninstrumented_measurement']==(kind=='completed')
    assert PerformanceTrial.from_json(trial.to_json()).to_dict()==trial.to_dict()


@pytest.mark.parametrize('kwargs',[{'elapsed_seconds':None},{'result_hash':None},{'elapsed_seconds':True},
    {'elapsed_seconds':float('inf')},{'index':5},{'index':True},{'phase':'unknown'},{'status':'failed'},
    {'status':'unavailable','failure':{'stage':'host','type':'Unavailable','message':'missing'}}])
def test_invalid_trial_combinations(declarations,kwargs):
    w,p,e,*_=declarations
    args=dict(workload=w,protocol=p,environment=e,phase='measurement',index=0,status='completed',elapsed_seconds=.2,result_hash='b'*64)
    args.update(kwargs)
    with pytest.raises(ValueError):PerformanceTrial(**args)


def test_budget_exceedance_is_retained_not_silently_dropped(declarations):
    w,p,e,*_=declarations
    trial=PerformanceTrial(w,p,e,'measurement',0,'completed',61.,'b'*64)
    assert trial.to_dict()['trial_budget_exceeded'] is True


def test_memory_kinds_and_method_isolation(declarations):
    w,p,e,*_=declarations
    with pytest.raises(ValueError):PerformanceTrial(w,p,e,'measurement',0,'completed',1.,'b'*64,memory_kind='process_peak_rss',memory_bytes=1,memory_method='OS high-water')
    for instrument,isolation,kind in [('tracemalloc','fresh_state','traced_allocations'),('native_memory','fresh_process','process_peak_rss')]:
        protocol=MeasurementProtocol(instrumentation=instrument,isolation=isolation)
        trial=PerformanceTrial(w,protocol,e,'measurement',0,'completed',1.,'b'*64,memory_kind=kind,memory_bytes=12,memory_method='declared synthetic observation')
        assert trial.to_dict()['memory_unit']=='byte' and not trial.to_dict()['uninstrumented_measurement']
        assert PerformanceTrial.from_json(trial.to_json()).contract_hash==trial.contract_hash
    with pytest.raises(ValueError):PerformanceTrial(w,p,e,'measurement',0,'completed',1.,'b'*64,memory_bytes=0)


@pytest.mark.parametrize('field,value',[('uninstrumented_measurement',False),('memory_unit','MB'),('time_unit','ms'),('trial_budget_exceeded',True)])
def test_trial_projection_tampering_rejected(declarations,field,value):
    raw=declarations[-1].to_dict();raw[field]=value
    with pytest.raises(ValueError):PerformanceTrial.from_dict(raw)


@pytest.mark.parametrize('field,value',[('source_commit','A'*40),('source_dirty',1),('thread_settings',{}),('logical_cpu_count',0),('python_version',''),('imported_package_path','relative/package')])
def test_environment_requires_explicit_typed_provenance(declarations,field,value):
    raw=declarations[2].to_dict();raw[field]=value
    with pytest.raises(ValueError):PerformanceEnvironment.from_dict(raw)


def result(population):return {'context':{'source_hash':'c'*64},'observations':{'population':population},'status':'completed'}


def test_numeric_tolerance_and_undeclared_exact_values(declarations):
    w,_,_,rule,contract,_=declarations
    assert compare_scientific_results(contract,w,result([.2,.8]),result([.2+1e-10,.8]))['status']=='equivalent'
    failed=compare_scientific_results(contract,w,result([.2,.8]),result([.3,.8]))
    assert failed['status']=='not_equivalent' and failed['differences'][0]['path']=='/observations/population/0'
    candidate=result([.2,.8]);candidate['context']['source_hash']='d'*64
    assert compare_scientific_results(contract,w,result([.2,.8]),candidate)['status']=='not_equivalent'
    candidate=result([.2,.8]);candidate['status']='failed'
    assert compare_scientific_results(contract,w,result([.2,.8]),candidate)['status']=='not_equivalent'


@pytest.mark.parametrize('other',[[[.2,.8]],[.2],[True,.8],['0.2',.8]])
def test_array_shape_order_and_numeric_types_are_preserved(declarations,other):
    w,_,_,_,contract,_=declarations
    assert compare_scientific_results(contract,w,result([.2,.8]),result(other))['status']=='not_equivalent'


def test_missing_empty_and_known_negative_evidence(declarations):
    w,_,_,_,contract,_=declarations
    a=result([]);b=result([])
    assert compare_scientific_results(contract,w,a,b)['status']=='not_assessable'
    a={'context':{'source_hash':'c'*64}};b=copy.deepcopy(a)
    assert compare_scientific_results(contract,w,a,b)['status']=='not_assessable'
    b['context']['source_hash']='d'*64
    out=compare_scientific_results(contract,w,a,b)
    assert out['status']=='not_equivalent' and out['missing_paths']


@pytest.mark.parametrize('value',[float('nan'),float('inf'),{'not':'numeric'}])
def test_invalid_scientific_json_is_not_coerced(declarations,value):
    w,_,_,_,contract,_=declarations
    if type(value) is dict:
        assert compare_scientific_results(contract,w,result([.2]),result(value))['status']=='not_equivalent'
    else:
        with pytest.raises(ValueError):compare_scientific_results(contract,w,result([.2]),result(value))


def test_exact_rational_comparison_avoids_overflow_and_integer_rounding(declarations):
    w=declarations[0]
    zero=EquivalenceContract(w.contract_hash,(EquivalenceRule('/x','charge','C',0,0),),('/context',),'synthetic exact oracle')
    a={'context':'fixed','x':2**53};b={'context':'fixed','x':2**53+1}
    assert compare_scientific_results(zero,w,a,b)['status']=='not_equivalent'
    huge=EquivalenceContract(w.contract_hash,(EquivalenceRule('/x','readout','V',0,1),),('/context',),'synthetic overflow guard')
    assert compare_scientific_results(huge,w,{'context':'fixed','x':1e308},{'context':'fixed','x':-1e308})['status']=='not_equivalent'
    relative=EquivalenceContract(w.contract_hash,(EquivalenceRule('/x','readout','V',1,0),),('/context',),'synthetic threshold')
    assert compare_scientific_results(relative,w,{'context':'fixed','x':0},{'context':'fixed','x':1})['status']=='equivalent'


@pytest.mark.parametrize('path',['','bad','/bad~','/bad~2'])
def test_invalid_json_pointers(path):
    with pytest.raises(ValueError):EquivalenceRule(path,'readout','V',0,0)


def test_provenance_overlap_and_ambiguous_rules_rejected(declarations):
    w=declarations[0];rule=EquivalenceRule('/x','readout','V',0,0)
    with pytest.raises(ValueError):EquivalenceContract(w.contract_hash,(rule,),('/x',),'synthetic')
    with pytest.raises(ValueError):EquivalenceContract(w.contract_hash,(rule,rule),('/context',),'synthetic')
    with pytest.raises(ValueError):EquivalenceContract(w.contract_hash,(),('/context','/context/x'),'synthetic')
    with pytest.raises(ValueError):EquivalenceContract(w.contract_hash,(),(),'synthetic')


def test_escaped_paths_and_workload_binding(declarations):
    w=declarations[0];rule=EquivalenceRule('/x~1y/~0value','charge','C',0,0)
    contract=EquivalenceContract(w.contract_hash,(rule,),('/context',),'synthetic')
    data={'context':'fixed','x/y':{'~value':1}}
    assert compare_scientific_results(contract,w,data,data)['status']=='equivalent'
    other=PerformanceWorkload('other','restore',{'source':'different'},('validation',),'static_restore',1,'synthetic')
    with pytest.raises(ValueError):compare_scientific_results(contract,other,data,data)


def test_unavailable_numeric_values_do_not_hide_known_provenance_failure(declarations):
    w,_,_,_,contract,_=declarations
    a=result(None);b=result(None)
    assert compare_scientific_results(contract,w,a,b)['status']=='not_assessable'
    b['context']['source_hash']='d'*64
    out=compare_scientific_results(contract,w,a,b)
    assert out['status']=='not_equivalent' and out['unavailable_numeric_paths']


def test_wall_clock_range_and_subnormal_numeric_oracle(declarations):
    with pytest.raises(ValueError):MeasurementProtocol(max_trial_seconds=1<<5000)
    w=declarations[0]
    contract=EquivalenceContract(w.contract_hash,(EquivalenceRule('/x','charge','C',5e-324,0),),('/context',),'synthetic subnormal test')
    assert compare_scientific_results(contract,w,{'context':'fixed','x':0.0},{'context':'fixed','x':1e-323})['status']=='not_equivalent'


def test_scientific_comparison_inputs_are_not_mutated(declarations):
    w,_,_,_,contract,_=declarations
    a=result([.2,.8]);b=copy.deepcopy(a);original=copy.deepcopy(a)
    out=compare_scientific_results(contract,w,a,b)
    assert out['status']=='equivalent' and a==b==original
    out['differences'].append({'path':'/context','reason':'caller mutation'})
    assert compare_scientific_results(contract,w,a,b)['differences']==[]


def test_changed_memory_and_result_source_identity_are_not_rebound(declarations):
    w,p,e,*_=declarations
    raw=PerformanceTrial(w,p,e,'measurement',0,'completed',.2,'b'*64).to_dict()
    raw['workload']['scientific_inputs']['solver']['dt_s']=2e-9
    with pytest.raises(ValueError):PerformanceTrial.from_dict(raw)


def test_exact_object_keys_and_array_order(declarations):
    w=declarations[0]
    contract=EquivalenceContract(w.contract_hash,(),('/context',),'exact-only synthetic archive comparison')
    a={'context':'fixed','rows':[1,2],'other':1}
    assert compare_scientific_results(contract,w,a,{'other':1,'rows':[1,2],'context':'fixed'})['status']=='equivalent'
    b=copy.deepcopy(a);b['rows'].reverse()
    assert compare_scientific_results(contract,w,a,b)['status']=='not_equivalent'
    b=copy.deepcopy(a);b['extra']=None
    assert compare_scientific_results(contract,w,a,b)['status']=='not_equivalent'
