# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Applied Q6 report: electrical/optical updates, negative separation and retention ensembles."""
from __future__ import annotations
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from examples.phase_q4_gradual_update_reference import run_reference as run_q4, restore as restore_q4
from examples.phase_q5_retention_ensemble_reference import run_reference as run_q5, restore as restore_q5
from ncmemsim.multilevel_contracts import PulseSequenceEvidence, _load
from ncmemsim.multilevel_execution import ElectricalSequenceResult
from ncmemsim.multilevel_analysis import MultilevelStudyPlan, MultilevelStudyResult, analyze_multilevel_results
from ncmemsim.multilevel_updates import GradualUpdateAnalysis, PairedUpdateAnalysis
from ncmemsim.multilevel_optical import OpticalSequenceResult, MatchedOpticalSequenceResult
from ncmemsim.multilevel_retention import MultilevelRetentionResult
from ncmemsim.multilevel_ensemble import MultilevelEnsembleResult
from ncmemsim.multilevel_reporting import (MultilevelReportCase, build_multilevel_report,
    write_multilevel_report, load_multilevel_report_bundle)

EVIDENCE = PulseSequenceEvidence('Q6 controlled applied report', 'Q3-Q5 executable references', 'synthetic',
    'Assumed model inputs and source-specific definitions; negative outcomes retained, no pooled capacity or experimental qualification.')


def build_reference_report(q4=None, q5=None):
    q4 = run_q4() if q4 is None else restore_q4(q4)
    q5 = run_q5() if q5 is None else restore_q5(q5)
    prepared = MultilevelStudyResult.from_dict(q5['nominal_retention']['plan']['prepared'])
    plan = MultilevelStudyPlan.from_dict(prepared.to_dict()['plan'])
    reversed_plan = replace(plan, name='Q6 deliberately reversed level declaration', levels=tuple(reversed(plan.levels)))
    reversed_results = tuple(ElectricalSequenceResult.from_dict(x) for x in reversed(prepared.to_dict()['results']))
    reversed_study = analyze_multilevel_results(reversed_plan, reversed_results)
    sources = (
        ('Electrical loading trajectory', ElectricalSequenceResult.from_dict(q4['electrical_loading']['source'])),
        ('Declared-order level separation', prepared),
        ('Reversed levels - negative control', reversed_study),
        ('Gradual electrical loading', GradualUpdateAnalysis.from_dict(q4['electrical_loading'])),
        ('Wrong-direction branch - undefined metric', GradualUpdateAnalysis.from_dict(q4['electrical_unloading'])),
        ('Paired updates - retained non-assessability', PairedUpdateAnalysis.from_dict(q4['paired_updates'])),
        ('Illuminated loading trajectory', OpticalSequenceResult.from_dict(q4['matched_optical']['light'])),
        ('Matched optical and dark control', MatchedOpticalSequenceResult.from_dict(q4['matched_optical'])),
        ('Independent nominal retention delays', MultilevelRetentionResult.from_dict(q5['nominal_retention'])),
        ('Zero-variation ensemble', MultilevelEnsembleResult.from_dict(q5['zero_variation'])),
        ('Assumed FG-fraction ensemble', MultilevelEnsembleResult.from_dict(q5['varied'])),
    )
    cases = tuple(MultilevelReportCase.from_result(name, result, EVIDENCE) for name, result in sources)
    return build_multilevel_report('NCMemSim multilevel applied studies - Q6', cases, EVIDENCE)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True, help='new bundle directory; never overwritten')
    parser.add_argument('--input-bundle', type=Path, help='restore an existing bundle without simulation')
    parser.add_argument('--q4-input', type=Path, help='reuse a stored Q4 reference instead of executing it')
    parser.add_argument('--q5-input', type=Path, help='reuse a stored Q5 reference instead of executing it')
    args = parser.parse_args()
    if args.input_bundle and (args.q4_input or args.q5_input):
        parser.error('--input-bundle cannot be combined with reference inputs')
    if args.input_bundle:
        report = load_multilevel_report_bundle(args.input_bundle)
    else:
        q4 = None if args.q4_input is None else _load(args.q4_input.read_text(encoding='utf-8'))
        q5 = None if args.q5_input is None else _load(args.q5_input.read_text(encoding='utf-8'))
        report = build_reference_report(q4, q5)
    path = write_multilevel_report(report, args.destination)
    print(json.dumps({'bundle': str(path), 'report_hash': report.contract_hash,
                     'case_count': report.summary['case_count'],
                     'case_status': {x['name']: x['status'] for x in report.summary['cases']}}, allow_nan=False))
