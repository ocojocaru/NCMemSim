# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Single-carrier 2s Coulomb couplings in the synthetic equal-mass U2 wells."""
import argparse
import json
import math
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scipy.integrate import quad
from scipy.optimize import brentq

from examples.phase_u2_coulomb_applicability import run_study as run_u2
from ncmemsim.constants import ELEMENTARY_CHARGE_C, EPSILON_0_F_M
from ncmemsim.hashing import canonical_hash


def _envelope(x, y):
    norm = math.sqrt(0.5 - math.sin(2*x)/(4*x) + math.sin(x)**2/(2*y))

    def value(t):
        return (math.sin(x*t) if t <= 1 else math.sin(x)*math.exp(-y*(t-1))) / norm

    return value


def _integral(function, upper=math.inf, tolerance=1e-10):
    inside = quad(function, 0, min(upper, 1.), epsabs=tolerance, epsrel=tolerance)[0]
    if upper > 1:
        inside += quad(function, 1, upper, epsabs=tolerance, epsrel=tolerance)[0]
    return inside


def radial_coupling(excited_carrier, spectator, tolerance=1e-10):
    """Compute a signed 1s-to-2s matrix element with the spectator in 1s."""
    if excited_carrier['status'] != 'bound' or spectator['status'] != 'bound':
        return {'status': 'unavailable', 'reason': 'ground_state_unavailable'}
    request = excited_carrier['request']
    if request['inside_mass_m0'] != request['outside_mass_m0']:
        raise ValueError('equal interface masses required')
    rho = excited_carrier['rho']
    if rho <= 1.5*math.pi:
        return {'status': 'unavailable', 'reason': 'no_bound_2s_state'}

    def matching(x):
        return x*math.cos(x) + math.sqrt((rho-x)*(rho+x))*math.sin(x)

    x = brentq(matching, 1.5*math.pi, min(rho, 2*math.pi), xtol=1e-13)
    y = math.sqrt((rho-x)*(rho+x))
    ground = _envelope(excited_carrier['x'], excited_carrier['y'])
    excited = _envelope(x, y)
    other = _envelope(spectator['x'], spectator['y'])

    def transition(t):
        return ground(t)*excited(t)

    def density(t):
        return other(t)**2

    def integrand(t):
        if t == 0:
            return 0.
        return (transition(t)*_integral(density, t, tolerance)
                + density(t)*_integral(transition, t, tolerance)) / t

    return {
        'status': 'evaluated', 'signed_coefficient': _integral(integrand, tolerance=tolerance),
        'overlap': _integral(transition, tolerance=tolerance),
        'excited_energy_J': request['depth_J']*(x/rho)**2,
        'excitation_gap_J': request['depth_J']*(x/rho)**2 - excited_carrier['energy_J'],
    }


def run_study():
    source = run_u2()
    rows = []
    for case in source['cases']:
        result = case['result']
        channels = {}
        for carrier, spectator in (('electron', 'hole'), ('hole', 'electron')):
            channel = radial_coupling(result[carrier], result[spectator])
            if channel['status'] == 'evaluated':
                fine = radial_coupling(result[carrier], result[spectator], tolerance=1e-12)
                channel['refinement_change'] = abs(channel['signed_coefficient'] - fine['signed_coefficient'])
                channel['signed_coefficient'] = fine['signed_coefficient']
                radius = result[carrier]['request']['radius_m']
                factor = ELEMENTARY_CHARGE_C**2 / (4*math.pi*EPSILON_0_F_M*result['relative_permittivity']*radius)
                matrix_element = -factor*channel['signed_coefficient']
                channel['matrix_element_J'] = matrix_element
                channel['first_order_amplitude_magnitude'] = abs(matrix_element/channel['excitation_gap_J'])
                channel['second_order_energy_J'] = -matrix_element**2/channel['excitation_gap_J']
            channels[carrier] = channel
        rows.append({'label': case['label'], 'channels': channels})
    report = {
        'schema_version': 'u4-radial-coulomb-coupling-study-v1',
        'u2_source_hash': source['study_hash'],
        'scope': 'Single-carrier bound 2s channels with the other carrier in 1s; equal interface masses.',
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
