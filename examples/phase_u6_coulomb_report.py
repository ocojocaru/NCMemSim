# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Export and restore the U2 direct Coulomb population with a numerical control."""
import argparse
from dataclasses import replace
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.phase_t3_finite_confinement_reference import _baseline
from examples.phase_u2_coulomb_applicability import SCREENING, run_study
from ncmemsim.coulomb_reporting import (
    CoulombStudyReport, load_coulomb_study_bundle, write_coulomb_study_bundle,
)
from ncmemsim.materials.electron_hole_coulomb import evaluate_electron_hole_coulomb


def build_report():
    source = run_study()
    cases = [{
        'label': case['label'], 'result': case['result'],
        'settings': {'source_study': 'U2', 'source_study_hash': source['study_hash']},
    } for case in source['cases']]
    electron = _baseline('electron', 0.2, 0.8)
    hole = replace(electron, carrier='hole')
    failed = evaluate_electron_hole_coulomb(
        electron, hole, relative_permittivity=1e308, screening_evidence=SCREENING,
    )
    if failed['status'] != 'numerical_failure':
        raise AssertionError('expected energy underflow control')
    cases.append({
        'label': 'energy_underflow_control', 'result': failed,
        'settings': {'purpose': 'synthetic numerical range control'},
    })
    return CoulombStudyReport('Synthetic direct Coulomb study', cases)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    destination = write_coulomb_study_bundle(report, args.output)
    restored = load_coulomb_study_bundle(destination)
    print(restored.contract_hash)
