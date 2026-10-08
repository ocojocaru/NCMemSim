# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Create a small O6 report or restore a stored report without simulation."""
from pathlib import Path
import argparse
import json
import sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from examples.phase_o5_structural_reference import structural_context, spectral, source, SCOPE
from ncmemsim.spectral_sources import _canonical
from ncmemsim.spectral_context import SpectralPulseProtocol
from ncmemsim.structural_optical_context import run_structural_spectral_program_pulse_read
from ncmemsim.program_protocol import ProgramPulseReadProtocol
from ncmemsim.photo import PhotoTransitionConfig, PhotoTransitionWeights
from ncmemsim.structural_reporting import (StructuralReport, StructuralReportStudy,
    build_structural_run_evidence, build_structural_report, write_structural_report, load_structural_report_bundle)


def run_reference():
    owner=structural_context('composed');light=source(5,())
    context=spectral(owner,light)
    protocol=SpectralPulseProtocol(ProgramPulseReadProtocol(2,1e-7,0,1e-7/8),PhotoTransitionWeights())
    run=run_structural_spectral_program_pulse_read(context,protocol,photo_config=PhotoTransitionConfig(.1))
    frozen=build_structural_run_evidence(run)
    studies=[StructuralReportStudy('composed optical path','optical',context.to_json()),
        StructuralReportStudy('composed illuminated pulse','pulse',frozen.to_json())]
    for name,request in (('strain outside domain',{'trace':.02}),('radius outside domain',{'diameter_nm':2.})):
        try:structural_context('composed',**request)
        except ValueError as exc:
            failure={'schema_version':'structural-failed-request-v1',
                'request':{'baseline_context':owner.to_dict(),'source':light.to_dict(),
                    'mode':'composed','requested_override':request},
                'stage':'structural resolution','error_type':'builtins.ValueError','message':str(exc)}
            studies.append(StructuralReportStudy(name,'failure',_canonical(failure)))
        else:raise AssertionError('expected failed request')
    return build_structural_report('O6 conditional structural evidence',studies,
        limitations=(SCOPE,'Stored states/alpha observations are authoritative; consistency hashes do not establish authenticity or independently validate a trajectory.',
            'Five spectral nodes and eight time steps demonstrate reporting only; use O5 for numerical refinement evidence.'),
        evidence={'implementation_baseline':'9e82212f75c4d7370865c43aa1a5f1f4383260ed',
            'reference_role':'new O6 report demonstration, not the O5 convergence population',
            'population':'each optical/pulse/failure study is one report attempt'})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--input',type=Path)
    args=parser.parse_args()
    report=StructuralReport.from_json(args.input.read_text(encoding='utf-8')) if args.input else run_reference()
    write_structural_report(report,args.output)
    restored=load_structural_report_bundle(args.output)
    print(json.dumps({'report_hash':restored.report_hash,'summary':restored.summary}))
