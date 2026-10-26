# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Owned measurement declarations and deterministic equivalence; no benchmark execution."""
from __future__ import annotations

from fractions import Fraction as _Fraction
from pathlib import PureWindowsPath as _WindowsPath, PurePosixPath as _PosixPath
import hashlib as _hashlib
import json as _json
import math as _math
import re as _re

__all__ = ['PerformanceWorkload', 'MeasurementProtocol', 'PerformanceEnvironment',
           'PerformanceTrial', 'EquivalenceRule', 'EquivalenceContract',
           'compare_scientific_results']


def _text(value, name):
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(name+' must be nonempty trimmed text')
    return value


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(name+' must be an integer in its declared domain')
    return value


def _number(value, name, positive=False):
    if type(value) not in (int,float):
        raise ValueError(name+' must be a finite real number, not boolean')
    if type(value) is float and not _math.isfinite(value):
        raise ValueError(name+' must be finite')
    if value < 0 or (positive and value == 0):
        raise ValueError(name+' must be nonnegative or positive as declared')
    return value


def _seconds(value,name,positive=False):
    _number(value,name,positive)
    try:representable=_math.isfinite(float(value))
    except OverflowError:representable=False
    if not representable:raise ValueError(name+' is outside finite wall-clock range')
    return value


def _choice(value, options, name):
    _text(value,name)
    if value not in options:raise ValueError('unsupported '+name)
    return value


def _digest(value, name, length=64):
    if type(value) is not str or len(value)!=length or any(x not in '0123456789abcdef' for x in value):
        raise ValueError(name+' must be a lowercase digest of the declared length')
    return value


def _canonical(value):
    def walk(v):
        if v is None or type(v) in (str,bool,int):return
        if type(v) is float:
            if not _math.isfinite(v):raise ValueError('nonfinite JSON value')
            return
        if type(v) is list:
            for x in v:walk(x)
            return
        if type(v) is dict and all(type(k) is str for k in v):
            for x in v.values():walk(x)
            return
        raise ValueError('native finite JSON data required; no implicit coercion')
    walk(value)
    return _json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def _unique(pairs):
    out={}
    for key,value in pairs:
        if key in out:raise ValueError('duplicate JSON key')
        out[key]=value
    return out


def _reject(value):raise ValueError('nonfinite JSON constant: '+value)


def _hash(value):return _hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()


class _Owned:
    __slots__=('_serialized',)

    def __setattr__(self,name,value):raise AttributeError('owned performance contract is immutable')

    def __delattr__(self,name):raise AttributeError('owned performance contract is immutable')

    def _store(self,payload):
        if hasattr(self,'_serialized'):raise AttributeError('contract already initialized')
        object.__setattr__(self,'_serialized',_canonical(payload))

    def to_dict(self):return _json.loads(self._serialized)

    def to_json(self):return self._serialized

    @property
    def contract_hash(self):return _hashlib.sha256(self._serialized.encode('utf-8')).hexdigest()

    @classmethod
    def from_json(cls,text):
        if type(text) is not str:raise ValueError('JSON text required')
        return cls.from_dict(_json.loads(text,object_pairs_hook=_unique,parse_constant=_reject))


def _restore(cls,raw,fields,constants):
    if type(raw) is not dict or set(raw)!=set(fields)|set(constants):
        raise ValueError('unknown or missing performance contract fields')
    for name,value in constants.items():
        if _canonical(raw[name])!=_canonical(value):raise ValueError('schema/unit/policy mismatch: '+name)
    obj=cls(**{name:raw[name] for name in fields})
    if obj.to_json()!=_canonical(raw):raise ValueError('inconsistent derived contract fields')
    return obj


class PerformanceWorkload(_Owned):
    """Scientific inputs are owned separately from host/timing observations."""
    __slots__=()

    def __init__(self,workload_id,workflow_kind,scientific_inputs,scope,
                 dependency_kind,logical_item_count,notes):
        _text(workload_id,'workload_id');_text(notes,'notes')
        _choice(workflow_kind,('relaxation','sequence','level_preparation','retention','sweep','ensemble','restore','export'),'workflow_kind')
        if type(scientific_inputs) is not dict or not scientific_inputs:raise ValueError('nonempty scientific input object required')
        _canonical(scientific_inputs)
        if type(scope) not in (list,tuple) or not scope:raise ValueError('nonempty scope required')
        values=list(scope)
        for value in values:_choice(value,('setup','execution','validation','serialization','io','end_to_end'),'scope')
        if len(values)!=len(set(values)) or ('end_to_end' in values and len(values)!=1):
            raise ValueError('duplicate/ambiguous timing scope')
        _choice(dependency_kind,('state_chain','independent_items','static_restore','static_export'),'dependency_kind')
        if workflow_kind=='sequence' and dependency_kind!='state_chain':raise ValueError('sequence steps are state-dependent')
        if workflow_kind=='restore' and dependency_kind!='static_restore':raise ValueError('restore dependency mismatch')
        if workflow_kind=='export' and dependency_kind!='static_export':raise ValueError('export dependency mismatch')
        _integer(logical_item_count,'logical_item_count',1)
        self._store({'schema_version':'performance-workload-v1','workload_id':workload_id,
            'workflow_kind':workflow_kind,'scientific_inputs':scientific_inputs,'scope':values,
            'dependency_kind':dependency_kind,'logical_item_count':logical_item_count,'notes':notes,
            'scientific_input_hash':_hash({'workflow_kind':workflow_kind,'scientific_inputs':scientific_inputs})})

    @property
    def scientific_inputs(self):return self.to_dict()['scientific_inputs']

    @property
    def scientific_input_hash(self):return self.to_dict()['scientific_input_hash']

    @classmethod
    def from_dict(cls,raw):
        if type(raw) is not dict:raise ValueError('workload object required')
        return _restore(cls,raw,('workload_id','workflow_kind','scientific_inputs','scope','dependency_kind','logical_item_count','notes'),
            {'schema_version':'performance-workload-v1','scientific_input_hash':_hash({'workflow_kind':raw.get('workflow_kind'),'scientific_inputs':raw.get('scientific_inputs')})})


class MeasurementProtocol(_Owned):
    """Bounded declared repeat protocol; constructors do not enforce runtime limits."""
    __slots__=()

    def __init__(self,warmup_count=1,measured_count=5,instrumentation='none',
                 isolation='fresh_state',max_trial_seconds=60.,max_total_seconds=600.):
        _integer(warmup_count,'warmup_count',1);_integer(measured_count,'measured_count',5)
        _choice(instrumentation,('none','cprofile','tracemalloc','native_memory'),'instrumentation')
        _choice(isolation,('fresh_process','fresh_state','static_restore'),'isolation')
        _seconds(max_trial_seconds,'max_trial_seconds',True);_seconds(max_total_seconds,'max_total_seconds',True)
        self._store({'schema_version':'performance-measurement-protocol-v1','warmup_count':warmup_count,
            'measured_count':measured_count,'instrumentation':instrumentation,'isolation':isolation,
            'max_trial_seconds':max_trial_seconds,'max_total_seconds':max_total_seconds,
            'time_unit':'s','clock':'monotonic_wall','budget_policy':'declared_limits_enforced_by_future_executor'})

    @classmethod
    def from_dict(cls,raw):
        return _restore(cls,raw,('warmup_count','measured_count','instrumentation','isolation','max_trial_seconds','max_total_seconds'),
            {'schema_version':'performance-measurement-protocol-v1','time_unit':'s','clock':'monotonic_wall','budget_policy':'declared_limits_enforced_by_future_executor'})


class PerformanceEnvironment(_Owned):
    """Explicit caller-declared environment; no probing, certification or execution."""
    __slots__=()

    def __init__(self,source_commit,source_dirty,source_package_version,distribution_version,
                 imported_package_path,python_version,numpy_version,platform,cpu,
                 logical_cpu_count,thread_settings,backend_id):
        _digest(source_commit,'source_commit',40)
        if type(source_dirty) is not bool:raise ValueError('source_dirty must be boolean')
        for name,value in (('source_package_version',source_package_version),('imported_package_path',imported_package_path),
            ('python_version',python_version),('numpy_version',numpy_version),('platform',platform),('cpu',cpu),('backend_id',backend_id)):_text(value,name)
        if not (_WindowsPath(imported_package_path).is_absolute() or _PosixPath(imported_package_path).is_absolute()):raise ValueError('absolute declared import path required')
        if distribution_version is not None:_text(distribution_version,'distribution_version')
        if logical_cpu_count is not None:_integer(logical_cpu_count,'logical_cpu_count',1)
        if type(thread_settings) is not dict or not {'OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'}<=set(thread_settings):raise ValueError('explicit thread environment settings or unknown values required')
        for key,value in thread_settings.items():
            _text(key,'thread setting')
            if value is not None:_text(value,'thread setting value')
        self._store({'schema_version':'performance-environment-v1','source_commit':source_commit,
            'source_dirty':source_dirty,'source_package_version':source_package_version,'distribution_version':distribution_version,
            'imported_package_path':imported_package_path,'python_version':python_version,'numpy_version':numpy_version,
            'platform':platform,'cpu':cpu,'logical_cpu_count':logical_cpu_count,'thread_settings':thread_settings,'backend_id':backend_id})

    @classmethod
    def from_dict(cls,raw):
        return _restore(cls,raw,('source_commit','source_dirty','source_package_version','distribution_version','imported_package_path',
            'python_version','numpy_version','platform','cpu','logical_cpu_count','thread_settings','backend_id'),{'schema_version':'performance-environment-v1'})


class PerformanceTrial(_Owned):
    """One observed or unavailable trial; failed timings are never accepted measurements."""
    __slots__=()

    def __init__(self,workload,protocol,environment,phase,index,status,elapsed_seconds,
                 result_hash=None,failure=None,memory_kind='not_measured',memory_bytes=None,memory_method=None):
        for obj,cls in ((workload,PerformanceWorkload),(protocol,MeasurementProtocol),(environment,PerformanceEnvironment)):
            if type(obj) is not cls:raise ValueError('typed owned trial declarations required')
        _choice(phase,('warmup','measurement'),'phase');_integer(index,'index')
        p=protocol.to_dict()
        if index>=p['warmup_count' if phase=='warmup' else 'measured_count']:raise ValueError('trial index outside phase')
        _choice(status,('completed','failed','unavailable'),'status')
        if elapsed_seconds is not None:_seconds(elapsed_seconds,'elapsed_seconds')
        if result_hash is not None:_digest(result_hash,'result_hash')
        if status=='completed':
            if elapsed_seconds is None or result_hash is None or failure is not None:raise ValueError('completed trial requires timing/result and no failure')
        else:
            if type(failure) is not dict or set(failure)!= {'stage','type','message'}:raise ValueError('explicit failure/unavailable reason required')
            for value in failure.values():_text(value,'failure detail')
        if status=='unavailable' and (elapsed_seconds is not None or result_hash is not None):raise ValueError('unavailable trial cannot invent observations')
        _choice(memory_kind,('not_measured','traced_allocations','process_peak_rss'),'memory_kind')
        if memory_kind=='not_measured':
            if memory_bytes is not None or memory_method is not None:raise ValueError('unmeasured memory must remain absent')
        else:
            _integer(memory_bytes,'memory_bytes');_text(memory_method,'memory_method')
            if status=='unavailable':raise ValueError('unavailable trial cannot invent memory')
            if memory_kind=='traced_allocations' and p['instrumentation']!='tracemalloc':raise ValueError('traced allocation method mismatch')
            if memory_kind=='process_peak_rss' and (p['isolation']!='fresh_process' or p['instrumentation']!='native_memory'):
                raise ValueError('process high-water memory requires isolated native-memory trial')
        self._store({'schema_version':'performance-trial-v1','workload':workload.to_dict(),'protocol':p,'environment':environment.to_dict(),
            'phase':phase,'index':index,'status':status,'elapsed_seconds':elapsed_seconds,'result_hash':result_hash,'failure':failure,
            'memory_kind':memory_kind,'memory_bytes':memory_bytes,'memory_method':memory_method,'time_unit':'s','memory_unit':'byte',
            'trial_budget_exceeded':elapsed_seconds is not None and elapsed_seconds>p['max_trial_seconds'],
            'uninstrumented_measurement':status=='completed' and phase=='measurement' and p['instrumentation']=='none'})

    @classmethod
    def from_dict(cls,raw):
        if type(raw) is not dict:raise ValueError('trial object required')
        expected={'schema_version','workload','protocol','environment','phase','index','status','elapsed_seconds','result_hash','failure',
                  'memory_kind','memory_bytes','memory_method','time_unit','memory_unit','trial_budget_exceeded','uninstrumented_measurement'}
        if set(raw)!=expected:raise ValueError('unknown or missing trial fields')
        obj=cls(PerformanceWorkload.from_dict(raw['workload']),MeasurementProtocol.from_dict(raw['protocol']),PerformanceEnvironment.from_dict(raw['environment']),
            **{k:raw[k] for k in ('phase','index','status','elapsed_seconds','result_hash','failure','memory_kind','memory_bytes','memory_method')})
        if obj.to_json()!=_canonical(raw):raise ValueError('inconsistent trial units/projection')
        return obj


def _pointer(value):
    if type(value) is not str or (value and not value.startswith('/')):raise ValueError('JSON pointer required')
    if _re.search(r'~(?![01])',value):raise ValueError('invalid JSON pointer escape')
    return tuple(part.replace('~1','/').replace('~0','~') for part in value.split('/')[1:]) if value else ()


def _overlap(a,b):return a[:len(b)]==b or b[:len(a)]==a


class EquivalenceRule(_Owned):
    """A scalar/array tolerance on an explicit observable, never implicit unit conversion."""
    __slots__=()

    def __init__(self,path,quantity,unit,atol,rtol):
        _pointer(path);_text(quantity,'quantity');_text(unit,'unit')
        if not path:raise ValueError('numeric rule must select an observable below the object root')
        _number(atol,'atol');_number(rtol,'rtol')
        self._store({'schema_version':'performance-equivalence-rule-v1','path':path,'quantity':quantity,'unit':unit,'atol':atol,'rtol':rtol,
            'formula':'abs(candidate-reference)<=atol+rtol*abs(reference)','array_policy':'same_order_and_shape_all_numeric_leaves'})

    @classmethod
    def from_dict(cls,raw):
        return _restore(cls,raw,('path','quantity','unit','atol','rtol'),{'schema_version':'performance-equivalence-rule-v1',
            'formula':'abs(candidate-reference)<=atol+rtol*abs(reference)','array_policy':'same_order_and_shape_all_numeric_leaves'})


class EquivalenceContract(_Owned):
    """Everything is exact except declared numeric paths; provenance paths must exist."""
    __slots__=()

    def __init__(self,workload_hash,rules,exact_paths,reference_evidence):
        _digest(workload_hash,'workload_hash');_text(reference_evidence,'reference_evidence')
        if type(rules) not in (list,tuple) or any(type(x) is not EquivalenceRule for x in rules):raise ValueError('typed equivalence rules required')
        if type(exact_paths) not in (list,tuple) or not exact_paths:raise ValueError('explicit provenance/structural paths required')
        numeric=[_pointer(x.to_dict()['path']) for x in rules];exact=[_pointer(x) for x in exact_paths]
        if any(_overlap(a,b) for i,a in enumerate(numeric) for b in numeric[i+1:]):raise ValueError('overlapping numeric rules')
        if any(_overlap(a,b) for i,a in enumerate(exact) for b in exact[i+1:]):raise ValueError('duplicate/redundant exact paths')
        if any(_overlap(a,b) for a in numeric for b in exact):raise ValueError('numeric rules cannot weaken exact provenance')
        self._store({'schema_version':'performance-equivalence-contract-v1','workload_hash':workload_hash,'rules':[x.to_dict() for x in rules],
            'exact_paths':list(exact_paths),'reference_evidence':reference_evidence,'undeclared_fields':'exact','structure':'exact_object_keys_and_array_order_shape'})

    @classmethod
    def from_dict(cls,raw):
        if type(raw) is not dict:raise ValueError('equivalence contract required')
        expected={'schema_version','workload_hash','rules','exact_paths','reference_evidence','undeclared_fields','structure'}
        if set(raw)!=expected or type(raw['rules']) is not list:raise ValueError('invalid equivalence contract fields')
        obj=cls(raw['workload_hash'],tuple(EquivalenceRule.from_dict(x) for x in raw['rules']),raw['exact_paths'],raw['reference_evidence'])
        if obj.to_json()!=_canonical(raw):raise ValueError('inconsistent equivalence contract policy')
        return obj


def compare_scientific_results(contract,workload,reference,candidate):
    """Compare full finite JSON scientific trees, using exact-rational tolerance arithmetic.

    No solver, clock, sampling, unit conversion or environment probing is performed.
    Result hashes establish observed identity, not execution authenticity or calibration.
    """
    if type(contract) is not EquivalenceContract or type(workload) is not PerformanceWorkload:raise ValueError('typed comparison declarations required')
    c=contract.to_dict()
    if c['workload_hash']!=workload.contract_hash:raise ValueError('comparison workload mismatch')
    if type(reference) is not dict or type(candidate) is not dict:raise ValueError('scientific result objects required')
    # Snapshot ownership and reject nonfinite/coercible values before comparison.
    reference=_json.loads(_canonical(reference));candidate=_json.loads(_canonical(candidate))
    rules={_pointer(x['path']):x for x in c['rules']}
    def exists(node,path):
        for part in path:
            if type(node) is dict and part in node:node=node[part]
            elif type(node) is list and part.isascii() and part.isdigit() and str(int(part))==part and int(part)<len(node):node=node[int(part)]
            else:return False
        return True
    missing=[p for p in [*c['exact_paths'],*(x['path'] for x in c['rules'])]
             if not exists(reference,_pointer(p)) or not exists(candidate,_pointer(p))]
    result={'schema_version':'performance-equivalence-result-v1','contract_hash':contract.contract_hash,'workload_hash':workload.contract_hash,
        'reference_hash':_hash(reference),'candidate_hash':_hash(candidate),'status':'not_assessable' if missing else 'equivalent',
        'missing_paths':missing,'unavailable_numeric_paths':[],'differences':[],'numeric_leaf_count':0}
    def pointer(path):return ''.join('/'+x.replace('~','~0').replace('/','~1') for x in path)
    def diff(path,reason):result['differences'].append({'path':pointer(path),'reason':reason})
    def numeric(a,b,path,rule):
        if a is None or b is None:result['unavailable_numeric_paths'].append(pointer(path));return
        if type(a) is list and type(b) is list:
            if not a and not b:result['unavailable_numeric_paths'].append(pointer(path));return
            if len(a)!=len(b):diff(path,'array_shape');return
            for i,(x,y) in enumerate(zip(a,b)):numeric(x,y,path+(str(i),),rule)
        elif type(a) in (int,float) and type(b) in (int,float):
            result['numeric_leaf_count']+=1
            if abs(_Fraction(b)-_Fraction(a))>_Fraction(rule['atol'])+_Fraction(rule['rtol'])*abs(_Fraction(a)):
                diff(path,'numeric_tolerance')
        else:diff(path,'non_numeric_or_array_shape')
    def walk(a,b,path):
        if path in rules:numeric(a,b,path,rules[path]);return
        if type(a) is dict and type(b) is dict:
            if set(a)!=set(b):diff(path,'object_keys');return
            for key in sorted(a):walk(a[key],b[key],path+(key,))
        elif type(a) is list and type(b) is list:
            if len(a)!=len(b):diff(path,'array_shape');return
            for i,(x,y) in enumerate(zip(a,b)):walk(x,y,path+(str(i),))
        elif _canonical(a)!=_canonical(b):diff(path,'exact_value_or_type')
    walk(reference,candidate,())
    if result['differences']:result['status']='not_equivalent'
    elif result['unavailable_numeric_paths'] or missing:result['status']='not_assessable'
    return result
