# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Compare direct Coulomb energy with continuum separation in synthetic wells."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.phase_t3_finite_confinement_reference import _baseline
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.electron_hole_coulomb import evaluate_electron_hole_coulomb
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.structural import StructuralEvidence


SCREENING = StructuralEvidence(
    'U2 synthetic screening', 'controlled uniform dielectric comparison',
    ParameterStatus.ASSUMED, 'Illustrative dimensionless values for a diagnostic study',
)
CASES = (
    ('baseline', 4e-9, 0.15, 12.),
    ('smaller_radius', 2e-9, 0.15, 12.),
    ('shallower_hole', 4e-9, 0.02, 12.),
    ('weaker_screening', 4e-9, 0.15, 6.),
    ('unbound_hole', 4e-9, 0., 12.),
)


def run_study():
    """Return the isolated results and a one-sided perturbation diagnostic."""
    rows = []
    for label, radius, hole_depth, epsilon in CASES:
        electron = replace(_baseline('electron', 0.2, 0.8), radius_m=radius)
        hole = replace(_baseline('hole', 0.4, hole_depth), radius_m=radius)
        result = evaluate_electron_hole_coulomb(
            electron, hole, relative_permittivity=epsilon, screening_evidence=SCREENING,
        )
        distances = ratio = None
        assessment = 'unavailable'
        if result['status'] == 'evaluated':
            distances = {
                carrier: result[carrier]['request']['depth_J'] - result[carrier]['energy_J']
                for carrier in ('electron', 'hole')
            }
            ratio = abs(result['energy_shift_J']) / min(distances.values())
            assessment = 'shift_reaches_continuum_scale' if ratio >= 1 else 'inconclusive'
        rows.append({
            'label': label, 'result': result, 'continuum_separation_J': distances,
            'shift_to_min_continuum_separation': ratio, 'assessment': assessment,
        })
    report = {
        'schema_version': 'u2-coulomb-applicability-study-v1',
        'scope': 'Synthetic isolated wells with uniform screening. First-order direct diagonal energy only.',
        'cases': rows,
    }
    report['study_hash'] = canonical_hash(report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run_study()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(report['study_hash'])
