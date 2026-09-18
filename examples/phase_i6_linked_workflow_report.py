"""Linked electrical/electro-optical synthetic evidence reports; optional fit extra.

No files are written unless --output-dir is explicitly supplied.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

root = Path(__file__).resolve().parents[1]
if (root / 'ncmemsim').is_dir(): sys.path.insert(0, str(root))
from ncmemsim.workflows import (WorkflowEvidence, AppliedWorkflowEvidence,
    build_workflow_report, write_workflow_report)
from ncmemsim.dtco import ParameterBinding, BindingScope


def build_reference_report(*, optical=False, include_failures=False):
    if type(optical) is not bool or type(include_failures) is not bool:
        raise TypeError('reference mode flags must be boolean')
    filename = 'phase_i4_electro_optical_workflow_reference.py' if optical else 'phase_i3_electrical_workflow_reference.py'
    spec = importlib.util.spec_from_file_location('workflow_reference', Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    robust = module.build_reference_report(include_failures=include_failures)
    raw = robust.to_dict()
    applied = AppliedWorkflowEvidence.from_json(json.dumps(raw['analyses'][0]['data']['source']['study']['evaluation']['parameters']['applied_workflow_evidence']))
    evidence = WorkflowEvidence.from_json(json.dumps(raw['metadata']['source_workflow_evidence']))
    variants = [((ParameterBinding(BindingScope.DEVICE, ('temperature_K',)), temperature),)
        for temperature in raw['metadata']['design_temperatures_K']]
    return build_workflow_report(evidence, applied, robust,
        name='I6 synthetic ' + ('electro-optical' if optical else 'electrical') + ' linked workflow',
        device_variants=variants, metadata={'scope': 'Synthetic software verification only',
            'qualification_scope': '300 K fixture only; 325 K is exploratory',
            'reference': 'I4' if optical else 'I3', 'failure_demo': include_failures})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--optical', action='store_true')
    parser.add_argument('--include-failures', action='store_true')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    report = build_reference_report(optical=args.optical, include_failures=args.include_failures)
    print('Data origin: synthetic; scientific status: FITTED; software verification only')
    print('Linked workflow report hash:', report.report_hash)
    if args.output_dir:
        for path in write_workflow_report(report, args.output_dir): print(path)


if __name__ == '__main__': main()
