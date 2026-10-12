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
from ncmemsim.om2_numerics import LABELS, specification, summarize, restore_study


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
