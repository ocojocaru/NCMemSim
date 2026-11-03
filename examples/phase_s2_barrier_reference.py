# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Controlled isolated barriers, including underflow and a retained numeric failure."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from ncmemsim.barrier_contracts import (
    BarrierProvenance, BarrierSegment, BarrierProfile, BarrierEvaluationSpec,
)
from ncmemsim.barrier_evaluation import evaluate_barrier_profile


def build_reference():
    provenance = BarrierProvenance('assumed', 'synthetic S2 reference',
        'analytic numerical controls, no measurement', 'isolated WKB action',
        'no scattering matching, supply function or current')
    cases = {}
    controls = [('rectangle', 3e-19, 3e-19, 5e-9),
        ('linear', 3e-19, 1e-19, 5e-9),
        ('turning_point', 3e-19, -1e-19, 5e-9),
        ('zero_action', -1e-19, 0., 5e-9),
        ('transmission_underflow', 3e-19, 3e-19, 1e-5),
        ('numeric_failure', 1., 1., 1e300)]
    for label, start, end, length in controls:
        segment = BarrierSegment(label, length, start, end, .2, provenance)
        profile = BarrierProfile(label, [segment], 0., 'common synthetic energy zero',
            'source boundary', 'source to destination', 'along_positive_axis',
            'source', 'destination', 'isolated numerical control',
            'no physical calibration or experimental qualification')
        request = BarrierEvaluationSpec(profile, 1e-12, 1e-10, 'S1 predeclared analytic controls')
        cases[label] = evaluate_barrier_profile(request).to_dict()
    return dict(schema_version='phase-s2-controlled-reference-v1',
        evidence_kind='synthetic_numerical_controls', cases=cases,
        simulator_attachment=False, experimental_qualification=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    text = json.dumps(build_reference(), indent=2, allow_nan=False)+'\n'
    if args.output is None:
        print(text, end='')
    else:
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(text)


if __name__ == '__main__':
    main()
