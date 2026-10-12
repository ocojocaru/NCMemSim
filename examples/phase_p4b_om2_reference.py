# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Short assumed OM-2 sequence; not a reproduction of Palade2018."""
from pathlib import Path
import argparse, json, sys
if __package__ in (None, ''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from examples.phase_p4a_device_photo_reference import build_experiment
from ncmemsim.om2_sweep import OM2SweepProtocol, OM2SweepExperiment, OM2SweepPrediction, run_om2_sweep


def build_om2_experiment(n=1, *, capture_efficiency=.1, power_W=.01):
    exp=build_experiment(n,power_W=power_W,capture_efficiency=capture_efficiency)
    steps=8
    ascending=tuple(-2+4*i/steps for i in range(steps+1))
    reference=.8*exp.spectral_context.resolution.physics.electrostatics.equivalent_capacitance(exp.spectral_context.resolution.device)
    protocol=OM2SweepProtocol(-2.,2.,1e-7,ascending,tuple(reversed(ascending)),
        1e-8,1e-8/4,reference,
        'Assumed negative hold, ascending dark sweep, positive hold, descending dark sweep; endpoints included. '
        '1550 nm line, short numerical durations, common reference .8*Ceq; not published lamp, timing or Cfb.')
    return OM2SweepExperiment(exp,protocol)


def run_reference():
    return run_om2_sweep(build_om2_experiment())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--input',type=Path)
    args=parser.parse_args()
    result=OM2SweepPrediction.from_json(args.input.read_text(encoding='utf-8')) if args.input else run_reference()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result.to_dict(),indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'prediction_hash':result.contract_hash,'summary':result.summary}))
