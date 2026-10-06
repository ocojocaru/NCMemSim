# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Build a small N6 pulse/stack/failure bundle; alternatively restore a stored report."""
from pathlib import Path
import argparse
import json
import sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from examples.phase_n5_broadband_reference import build_resolution,make_source,build_context,SCOPE
from ncmemsim.spectral_sources import _canonical
from ncmemsim.spectral_context import SpectralPulseProtocol,run_spectral_program_pulse_read
from ncmemsim.program_protocol import ProgramPulseReadProtocol
from ncmemsim.photo import PhotoTransitionConfig,PhotoTransitionWeights
from ncmemsim.spectral_reporting import (SpectralReport,SpectralReportStudy,build_spectral_run_evidence,
    build_spectral_report,write_spectral_report,load_spectral_report_bundle)


def run_reference():
    context=build_context(build_resolution(),make_source('broadband',65))
    protocol=SpectralPulseProtocol(ProgramPulseReadProtocol(2,1e-7,0,1e-7/32),PhotoTransitionWeights())
    run=run_spectral_program_pulse_read(context,protocol,photo_config=PhotoTransitionConfig(.1))
    evidence=build_spectral_run_evidence(run)
    studies=[SpectralReportStudy('ordered optical path','stack',context.optical_result.to_json()),
        SpectralReportStudy('broadband illuminated pulse','pulse',evidence.to_json())]
    for name in ('unsupported_domain','incomplete_path'):
        try:
            source=make_source('mono')
            if name=='unsupported_domain':
                from dataclasses import replace
                source=replace(source,wavelength_nm=(1499.,))
            build_context(build_resolution(),source,omit=name=='incomplete_path')
        except ValueError as exc:
            failure={'schema_version':'spectral-failed-request-v1',
                'request':{'source':source.to_dict(),'device_resolution':build_resolution().to_dict(),
                    'declared_domain_nm':[1500,2000],'omit_first_passive_layer':name=='incomplete_path'},
                'stage':'input/path resolution','error_type':'builtins.ValueError','message':str(exc)}
            studies.append(SpectralReportStudy(name,'failure',_canonical(failure)))
        else:raise AssertionError('expected failed request')
    return build_spectral_report('N6 conditional spectral evidence',studies,
        limitations=(SCOPE,'Stored states are authoritative; restoration is consistency checking, not solver replay or authenticity.'),
        evidence={'implementation_baseline':'f7673c597e799e093daea09c3d14d8c35ba2c723',
            'reference_role':'new N6 development execution, not the nine-case N5 population',
            'report_population':'each optical/pulse/failure study counts as one report attempt'})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--input',type=Path);args=parser.parse_args()
    report=SpectralReport.from_json(args.input.read_text(encoding='utf-8')) if args.input else run_reference()
    write_spectral_report(report,args.output);restored=load_spectral_report_bundle(args.output)
    print(json.dumps({'report_hash':restored.report_hash,'summary':restored.summary}))
