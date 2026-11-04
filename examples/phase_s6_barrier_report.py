# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""S6 source-linked isolated barrier report with all S5 rows and negative controls."""
from __future__ import annotations
import argparse
from pathlib import Path
from ncmemsim.barrier_reporting import (
    BarrierStudyReport, write_barrier_study_report, load_barrier_study_bundle,
)
if __package__:
    from .phase_s5_barrier_sensitivity import build_reference
else:
    from phase_s5_barrier_sensitivity import build_reference


def build_report():
    study = build_reference()
    rows = [study['baseline']]+[r for group in study['sweeps'].values() for r in group]
    rows += study['design']+study['controls']+study['subdivision_controls']
    cases = [dict(label=str(i)+':'+row['label'], result=row['result'],
        settings=dict(parameters=row['parameters'], subdivision_count=row['subdivision_count'],
                      evidence_kind=study['evidence_kind']),
        reference_exponent=row['reference_exponent'],
        reference_description='S5 100-digit rectangular reference with declared SI inputs; synthetic')
        for i, row in enumerate(rows)]
    # Explicit archive controls for a negative comparison and a missing reference.
    for label, reference in [('negative-reference-control', 0.), ('missing-reference-control', None)]:
        cases.append(dict(label=label, result=study['baseline']['result'],
            settings=dict(evidence_kind='synthetic_archive_control'), reference_exponent=reference,
            reference_description='Deliberately mismatched or absent reference; not physical evidence'))
    return BarrierStudyReport('Controlled barrier action study', cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(); report = build_report()
    if args.output is None:
        print(report.to_json())
    else:
        write_barrier_study_report(report, args.output)
        restored = load_barrier_study_bundle(args.output)
        assert restored.contract_hash == report.contract_hash
        print(report.contract_hash)


if __name__ == '__main__':
    main()
