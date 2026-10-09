# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""P5A assumed OM-2 numerical study; no measured calibration or uncertainty fit."""
from pathlib import Path
from dataclasses import replace
import argparse,json,sys,math
import numpy as np
if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from examples.phase_p4b_om2_reference import build_om2_experiment
from ncmemsim.om2_sweep import OM2SweepExperiment,OM2SweepPrediction,run_om2_sweep
from ncmemsim.independent_data import _keys,_match,_unique,_constant
from ncmemsim.hashing import canonical_hash


LABELS=('dt','dt_half','dt_quarter','capture_zero','capture_low','capture_high',
        'power_zero','power_low','power_high','equal_product','reference_low','reference_high','reference_outside')


def specification():
    return {'schema_version':'p5a-om2-numerical-spec-v1',
        'input_status':'ASSUMED; PDF-only experimental sources not admitted',
        'cases':list(LABELS),'temporal_refinement_factors':[1,2,4],
        'capture_values':[0.,.09,.1,.11],'sample_power_values_W':[0.,.009,.01,.011],
        'equal_product_case':{'capture_efficiency':.05,'sample_power_W':.02},
        'reference_fractions_of_Ceq':[.7,.8,.9],'outside_reference_F_m2':1e6,
        'numerical_thresholds':{'max_capacitance_step_change_F_m2':1e-8,'max_window_step_change_V':1e-6},
        'threshold_scope':'predeclared example diagnostics; not experimental acceptance or rigorous truncation-error bounds',
        'identifiability_scope':'fixed line spectrum/constant capture product confounding; no statistical inference',
        'scientific_status':'synthetic_om2_numerical_study','experimental_qualification':False}


def build_cases():
    base=build_om2_experiment()
    cases={'dt':base,'dt_half':OM2SweepExperiment(base.device_photo,replace(base.protocol,internal_dt_s=base.protocol.internal_dt_s/2)),
        'dt_quarter':OM2SweepExperiment(base.device_photo,replace(base.protocol,internal_dt_s=base.protocol.internal_dt_s/4))}
    for label,kw in [('capture_zero',{'capture_efficiency':0}),('capture_low',{'capture_efficiency':.09}),
                     ('capture_high',{'capture_efficiency':.11}),('power_zero',{'power_W':0}),
                     ('power_low',{'power_W':.009}),('power_high',{'power_W':.011}),
                     ('equal_product',{'capture_efficiency':.05,'power_W':.02})]:
        cases[label]=build_om2_experiment(**kw)
    for label,fraction in [('reference_low',.7),('reference_high',.9)]:
        cases[label]=OM2SweepExperiment(base.device_photo,replace(base.protocol,reference_capacitance_F_m2=base.protocol.reference_capacitance_F_m2*fraction/.8))
    cases['reference_outside']=OM2SweepExperiment(base.device_photo,replace(base.protocol,reference_capacitance_F_m2=1e6))
    return {k:cases[k] for k in LABELS}


def _difference(a,b):
    av,bv=a.to_dict(),b.to_dict()
    if a.summary['status']!='completed' or b.summary['status']!='completed':
        return {'status':'not_assessable','max_capacitance_change_F_m2':None,'window_contrast_change_V':None}
    diffs=[]
    for mode in ('illuminated_writing','matched_dark'):
        if len(av[mode])!=len(bv[mode]):raise ValueError('different sequence lengths')
        for x,y in zip(av[mode],bv[mode]):
            _match([x['kind'],x['gate_voltage_V'],x['duration_s']],[y['kind'],y['gate_voltage_V'],y['duration_s']])
            diffs.append(abs(x['capacitance_F_m2']-y['capacitance_F_m2']))
    x,y=a.summary['light_minus_dark_crossing_window_V'],b.summary['light_minus_dark_crossing_window_V']
    return {'status':'assessable' if x is not None and y is not None else 'not_assessable',
        'max_capacitance_change_F_m2':max(diffs),'window_contrast_change_V':abs(x-y) if x is not None and y is not None else None}


def summarize(results,spec):
    temporal=[]
    thresholds=spec['numerical_thresholds']
    for first,second in [('dt','dt_half'),('dt_half','dt_quarter')]:
        delta=_difference(results[first],results[second])
        passed=delta['status']=='assessable' and delta['max_capacitance_change_F_m2']<=thresholds['max_capacitance_step_change_F_m2'] and delta['window_contrast_change_V']<=thresholds['max_window_step_change_V']
        temporal.append({'cases':[first,second],**delta,'within_example_thresholds':passed})
    contraction=None
    a,b=temporal
    if a['window_contrast_change_V'] is not None and a['window_contrast_change_V']>0 and b['window_contrast_change_V'] is not None:
        contraction=b['window_contrast_change_V']/a['window_contrast_change_V']
    sensitivities={}
    for name,low,high,step,unit in [('capture','capture_low','capture_high',.02,'dimensionless'),('sample_power','power_low','power_high',.002,'W')]:
        x,y=results[low].summary['light_minus_dark_crossing_window_V'],results[high].summary['light_minus_dark_crossing_window_V']
        slope=(y-x)/step if x is not None and y is not None else None
        if slope is not None and not math.isfinite(slope):raise ValueError('nonfinite local sensitivity')
        sensitivities[name]={'case_pair':[low,high],'central_secant_V_per_input_unit':slope,'input_unit':unit,
            'interpretation':'local assumed-input sensitivity; not standard uncertainty'}
    zero={}
    for name in ('capture_zero','power_zero'):
        d=results[name].to_dict()
        value=None
        if results[name].summary['status']=='completed':
            value=max(abs(x['capacitance_F_m2']-y['capacitance_F_m2']) for x,y in zip(d['illuminated_writing'],d['matched_dark']))
        zero[name]={'max_light_dark_capacitance_difference_F_m2':value,'dark_recovery':value is not None and value<=1e-15}
    equal=_difference(results['dt'],results['equal_product'])
    return {'scientific_status':'synthetic_om2_numerical_study','experimental_qualification':False,'parameters_fitted':False,
        'temporal_refinement':temporal,'window_change_ratio':contraction,'rigorous_error_bound_established':False,
        'local_sensitivity':sensitivities,'zero_photo_controls':zero,
        'power_capture_product_check':equal,'independent_identifiability_established':False,
        'reference_selection':[{'case':k,'reference_capacitance_F_m2':results[k].summary['reference_capacitance_F_m2'],
            'observable_status':results[k].summary['observable_status'],
            'contrast_V':results[k].summary['light_minus_dark_crossing_window_V']} for k in ('reference_low','dt','reference_high','reference_outside')],
        'case_status':{k:results[k].summary['status'] for k in LABELS}}


def restore_study(raw):
    _keys(raw,('schema_version','specification','specification_hash','results','summary'))
    if raw['schema_version']!='p5a-om2-numerical-study-v1':raise ValueError('unsupported study schema')
    _match(raw['specification'],specification())
    if raw['specification_hash']!=canonical_hash(raw['specification']):raise ValueError('specification identity mismatch')
    _keys(raw['results'],LABELS)
    results={k:OM2SweepPrediction.from_dict(raw['results'][k]) for k in LABELS}
    # Rebuild owned inputs only. Do not run occupancy, optical model or RNG.
    base=results['dt'].to_dict()['experiment']
    from copy import deepcopy
    expected={k:deepcopy(base) for k in LABELS}
    for k,factor in [('dt_half',2),('dt_quarter',4)]:
        expected[k]['protocol']['internal_dt_s']=base['protocol']['internal_dt_s']/factor
    for k,value in [('capture_zero',0.),('capture_low',.09),('capture_high',.11),('equal_product',.05)]:
        expected[k]['device_photo']['capture_efficiency']=value
    for k,fraction in [('reference_low',.7),('reference_high',.9)]:
        expected[k]['protocol']['reference_capacitance_F_m2']=base['protocol']['reference_capacitance_F_m2']*fraction/.8
    expected['reference_outside']['protocol']['reference_capacitance_F_m2']=1e6
    # Power changes require linked source/spectral budget changes: inspect exact
    # delivered power and compare all non-optical owned device inputs instead of
    # evaluating absorption again during restore.
    for k,value in [('power_zero',0.),('power_low',.009),('power_high',.011),('equal_product',.02)]:
        actual=results[k].to_dict()['experiment']
        photo=actual['device_photo'];basephoto=base['device_photo']
        if photo['illumination']['sample_power_W']!=value:raise ValueError('wrong power-study case')
        for field in ('protocol','initial_state','device_area_m2','initial_preparation_evidence','assumptions'):
            _match(photo[field],basephoto[field])
        _match(actual['protocol'],base['protocol'])
        _match(photo['spectral_context']['resolution'],basephoto['spectral_context']['resolution'])
        _match(photo['spectral_context']['optical_result']['path'],basephoto['spectral_context']['optical_result']['path'])
        for field in basephoto['illumination']:
            if field not in ('sample_power_W','summary'):
                _match(photo['illumination'][field],basephoto['illumination'][field])
        if photo['capture_efficiency']!=(.05 if k=='equal_product' else .1):raise ValueError('wrong capture for power case')
    for k in LABELS:
        if k not in ('power_zero','power_low','power_high','equal_product'):
            _match(results[k].to_dict()['experiment'],expected[k])
    if base['device_photo']['capture_efficiency']!=.1 or base['device_photo']['illumination']['sample_power_W']!=.01:
        raise ValueError('incorrect nominal sensitivity point')
    _match(raw['summary'],summarize(results,raw['specification']))
    return raw


def run_reference():
    spec=specification()  # freeze declared scope/thresholds before solver calls
    results={k:run_om2_sweep(exp) for k,exp in build_cases().items()}
    return restore_study({'schema_version':'p5a-om2-numerical-study-v1','specification':spec,
        'specification_hash':canonical_hash(spec),'results':{k:v.to_dict() for k,v in results.items()},
        'summary':summarize(results,spec)})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--input',type=Path)
    args=parser.parse_args()
    raw=restore_study(json.loads(args.input.read_text(encoding='utf-8'),object_pairs_hook=_unique,parse_constant=_constant)) if args.input else run_reference()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(raw,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'study_hash':canonical_hash(raw),'summary':raw['summary']}))
