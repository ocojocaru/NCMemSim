# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Resolve the first excitation scale for the equal-mass U2 controls."""
import argparse
import json
import math
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scipy.optimize import brentq
from scipy.special import spherical_jn

from examples.phase_u2_coulomb_applicability import run_study as run_u2
from ncmemsim.hashing import canonical_hash


def first_excitation(state):
    """Return the energy above the well bottom and the spectral channel."""
    if state['status'] != 'bound':
        return None
    request = state['request']
    if request['inside_mass_m0'] != request['outside_mass_m0']:
        raise ValueError('equal inside and outside masses required')
    rho = state['rho']
    if rho <= math.pi:
        return {'channel': 'continuum_threshold', 'energy_J': request['depth_J']}

    def matching(x):
        y = math.sqrt((rho - x) * (rho + x))
        return math.sin(x) + y * (y / (1 + y)) * spherical_jn(1, x)

    # First zero of j_1, the infinite-barrier limit for this channel.
    hard_wall = brentq(lambda x: spherical_jn(1, x), math.pi, 1.5 * math.pi)
    x = brentq(matching, math.pi, min(rho, hard_wall), xtol=1e-13)
    energy = request['depth_J'] * (x / rho)**2
    return {'channel': 'l1_bound', 'energy_J': energy, 'x': x}


def _radial_excitation_energy(state):
    rho = state['rho']
    depth = state['request']['depth_J']
    if rho <= 1.5 * math.pi:
        return depth

    def matching(x):
        return x * math.cos(x) - math.sqrt((rho-x)*(rho+x)) * abs(math.sin(x))

    x = brentq(matching, 1.5 * math.pi, min(rho, 2 * math.pi), xtol=1e-13)
    return depth * (x / rho)**2


def run_study():
    """Compare U2 energy shifts with the resolved unperturbed pair gap."""
    source = run_u2()
    rows = []
    for case in source['cases']:
        result = case['result']
        excitations = {carrier: first_excitation(result[carrier]) for carrier in ('electron', 'hole')}
        gap = ratio = scalar_gap = scalar_ratio = None
        if all(excitation is not None for excitation in excitations.values()):
            gaps = [excitation['energy_J'] - result[carrier]['energy_J']
                    for carrier, excitation in excitations.items()]
            gap = min(gaps)
            # A central interaction preserves total orbital angular momentum.
            # Within total L=0 both carriers have the same individual l.
            scalar_gap = min(
                sum(gaps),
                *(_radial_excitation_energy(result[carrier]) - result[carrier]['energy_J']
                  for carrier in excitations),
            )
            if result['energy_shift_J'] is not None:
                ratio = abs(result['energy_shift_J']) / gap
                scalar_ratio = abs(result['energy_shift_J']) / scalar_gap
        rows.append({
            'label': case['label'], 'first_excitations': excitations,
            'pair_spectral_gap_J': gap, 'shift_to_pair_spectral_gap': ratio,
            'total_L0_gap_J': scalar_gap, 'shift_to_total_L0_gap': scalar_ratio,
            'shift_to_min_continuum_separation': case['shift_to_min_continuum_separation'],
        })
    report = {
        'schema_version': 'u3-coulomb-spectral-gap-study-v1',
        'u2_source_hash': source['study_hash'],
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
