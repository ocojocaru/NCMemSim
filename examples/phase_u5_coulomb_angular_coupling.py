# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Bound 1p-electron/1p-hole Coulomb channel coupled to total orbital L=0."""
import argparse
import json
import math
from pathlib import Path
import sys
import warnings

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scipy.integrate import IntegrationWarning
from scipy.special import spherical_jn

from examples.phase_u2_coulomb_applicability import run_study as run_u2
from examples.phase_u3_coulomb_spectral_gap import first_excitation
from examples.phase_u4_coulomb_radial_coupling import _envelope, _integral
from ncmemsim.constants import ELEMENTARY_CHARGE_C, EPSILON_0_F_M
from ncmemsim.hashing import canonical_hash


ANGULAR_FACTOR = -1 / math.sqrt(3)


def _p_envelope(x, y, tolerance):
    interface = spherical_jn(1, x)

    def raw(t):
        if t <= 1:
            return t * spherical_jn(1, x*t)
        return interface * math.exp(-y*(t-1)) * (y + 1/t) / (y+1)

    normalization = math.sqrt(_integral(lambda t: raw(t)**2, tolerance=tolerance))
    return lambda t: raw(t)/normalization


def angular_coupling(electron, hole, tolerance=1e-10):
    """Return the signed coefficient for the normalized coupled 1p pair."""
    if electron['status'] != 'bound' or hole['status'] != 'bound':
        return {'status': 'unavailable', 'reason': 'ground_state_unavailable'}
    for field in ('radius_m', 'temperature_K', 'dot_material', 'host_material'):
        if electron['request'][field] != hole['request'][field]:
            raise ValueError('matched carrier geometry and material declarations required')
    excited = [first_excitation(state) for state in (electron, hole)]
    if any(state['channel'] != 'l1_bound' for state in excited):
        return {'status': 'unavailable', 'reason': 'bound_1p_pair_unavailable'}
    transitions = []
    for ground, excitation in zip((electron, hole), excited):
        x = excitation['x']
        y = math.sqrt((ground['rho']-x)*(ground['rho']+x))
        s_wave = _envelope(ground['x'], ground['y'])
        p_wave = _p_envelope(x, y, tolerance)
        transitions.append((s_wave, p_wave))
    (s_e, p_e), (s_h, p_h) = transitions

    def integrand(t):
        if t == 0:
            return 0.
        inner_h = _integral(lambda s: s*s_h(s)*p_h(s), t, tolerance)
        inner_e = _integral(lambda s: s*s_e(s)*p_e(s), t, tolerance)
        return (s_e(t)*p_e(t)*inner_h + s_h(t)*p_h(t)*inner_e) / t**2

    radial = _integral(integrand, tolerance=tolerance)
    gap = math.fsum(excitation['energy_J'] - state['energy_J']
                    for state, excitation in zip((electron, hole), excited))
    return {
        'status': 'evaluated', 'radial_coefficient': radial,
        'angular_factor': ANGULAR_FACTOR, 'signed_coefficient': ANGULAR_FACTOR*radial,
        'excited_states': excited, 'pair_excitation_gap_J': gap,
    }


def run_study():
    source = run_u2()
    rows = []
    for case in source['cases']:
        result = case['result']
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', IntegrationWarning)
                channel = angular_coupling(result['electron'], result['hole'])
                if channel['status'] == 'evaluated':
                    fine = angular_coupling(result['electron'], result['hole'], tolerance=1e-12)
                    change = abs(fine['signed_coefficient'] - channel['signed_coefficient'])
                    if change > 1e-8*abs(fine['signed_coefficient']):
                        raise ArithmeticError('angular channel quadrature refinement failed')
                    channel = dict(fine, refinement_change=change)
                    radius = result['electron']['request']['radius_m']
                    factor = ELEMENTARY_CHARGE_C**2 / (
                        4*math.pi*EPSILON_0_F_M*result['relative_permittivity']*radius
                    )
                    matrix_element = -factor*channel['signed_coefficient']
                    gap = channel['pair_excitation_gap_J']
                    channel.update(
                        matrix_element_J=matrix_element,
                        first_order_amplitude_magnitude=abs(matrix_element/gap),
                        second_order_energy_J=-matrix_element**2/gap,
                    )
        except (ArithmeticError, IntegrationWarning) as error:
            channel = {'status': 'numerical_failure', 'reason': str(error)}
        rows.append({'label': case['label'], 'channel': channel})
    report = {
        'schema_version': 'u5-angular-coulomb-coupling-study-v1',
        'u2_source_hash': source['study_hash'],
        'scope': 'First bound 1p pair coupled to total orbital L=0; equal interface masses and uniform screening.',
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
