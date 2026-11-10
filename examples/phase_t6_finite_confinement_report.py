# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Export and restore a synthetic finite-confinement study bundle."""
import argparse
from dataclasses import replace
import math
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.phase_t3_finite_confinement_reference import _baseline, run_reference
from ncmemsim.constants import ELECTRON_MASS_KG, HBAR_J_S
from ncmemsim.finite_confinement_reporting import (
    FiniteConfinementStudyReport, load_finite_confinement_study_bundle,
    write_finite_confinement_study_bundle,
)
from ncmemsim.materials.finite_confinement import evaluate_finite_confinement


def build_report():
    """Use an analytic equal-mass control and the complete T3 pair population."""
    request = _baseline('electron', 0.2, 0.8)
    x = 3 * math.pi / 4
    energy = (HBAR_J_S * x / request.radius_m)**2 / (2 * ELECTRON_MASS_KG * request.inside_mass_m0)
    request = replace(request, depth_J=2 * energy)
    cases = [{
        'label': 'equal-mass analytic control',
        'results': [evaluate_finite_confinement(request).to_dict()],
        'settings': {'study': 'T6 analytic control'},
        'references': [{
            'description': 'Equal masses, x = y = 3*pi/4; E = V0/2',
            'energy_J': energy, 'absolute_tolerance_J': energy * 1e-10,
        }],
    }]
    for index, pair in enumerate(run_reference()['pairs'], 1):
        cases.append({
            'label': f'T3 matched-radius pair {index}',
            'results': [pair[carrier]['finite'] for carrier in ('electron', 'hole')],
            'settings': {
                'study': 'T3 finite/infinite comparison',
                'radius_m': pair['radius_m'],
                'infinite_kinetic_sum_J': pair['infinite_kinetic_sum_J'],
            },
            'references': [None, None],
        })
    return FiniteConfinementStudyReport('Synthetic finite-well reference study', cases)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = build_report()
    destination = write_finite_confinement_study_bundle(report, args.output)
    print(load_finite_confinement_study_bundle(destination).contract_hash)
