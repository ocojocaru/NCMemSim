# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Export or restore an assumed OM-2 numerical report; no measured qualification."""
from pathlib import Path
import argparse,json,sys
if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from examples.phase_p5a_om2_numerical_study import run_reference
from ncmemsim.om2_numerics import OM2NumericalStudy
from ncmemsim.om2_reporting import build_om2_numerical_report,write_om2_numerical_report,load_om2_numerical_report_bundle


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    source=parser.add_mutually_exclusive_group()
    source.add_argument('--study',type=Path)
    source.add_argument('--input',type=Path)
    args=parser.parse_args()
    if args.input:
        report=load_om2_numerical_report_bundle(args.input)
    else:
        study=OM2NumericalStudy.from_json(args.study.read_text(encoding='utf-8')) if args.study else OM2NumericalStudy.from_dict(run_reference())
        report=build_om2_numerical_report('P6A assumed OM-2 numerical study',study)
    write_om2_numerical_report(report,args.output)
    print(json.dumps({'report_hash':report.contract_hash,'study_hash':report.study.contract_hash,'experimental_qualification':False}))
