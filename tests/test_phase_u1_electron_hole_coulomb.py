# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Independent nested quadrature and analytic limits for U1."""
from dataclasses import replace
import json
import math

import pytest
from scipy.integrate import quad
from scipy.special import sici

from ncmemsim.materials.electron_hole_coulomb import evaluate_electron_hole_coulomb
from test_phase_t2_finite_confinement import _request


def _evaluate(electron, hole, epsilon=12):
    return evaluate_electron_hole_coulomb(
        electron, hole, relative_permittivity=epsilon,
        screening_evidence=electron.applicability,
    )


def _reference(electron, hole):
    def radial(state):
        x, y = state['x'], state['y']

        def weight(t):
            if t <= 1:
                return math.sin(x*t)**2
            return math.sin(x)**2 * math.exp(-2*y*(t-1))

        normalizer = quad(weight, 0, 1, epsabs=1e-12)[0] + quad(weight, 1, math.inf, epsabs=1e-12)[0]
        return lambda t: weight(t)/normalizer

    def triangle(outer, inner):
        def integrand(t):
            boundary = min(t, 1.)
            integral = quad(inner, 0, boundary, epsabs=1e-13)[0]
            if t > 1:
                integral += quad(inner, 1, t, epsabs=1e-13)[0]
            return outer(t) * integral / t

        return quad(integrand, 0, 1, epsabs=1e-12)[0] + quad(integrand, 1, math.inf, epsabs=1e-12)[0]

    pe, ph = radial(electron), radial(hole)
    return triangle(pe, ph) + triangle(ph, pe)


@pytest.mark.parametrize('beta_e,rho_e,beta_h,rho_h', [
    (1., 4., 1., 4.),
    (.25, 4., 2., 3.),
    (1., 1.6, 1., 1.7),
])
def test_reference_population(beta_e, rho_e, beta_h, rho_h):
    electron = _request(beta_e, rho_e)
    hole = replace(_request(beta_h, rho_h), carrier='hole')
    result = _evaluate(electron, hole)
    assert result['status'] == 'evaluated', result['reason']
    assert result['coefficient'] == pytest.approx(_reference(result['electron'], result['hole']), rel=1e-8, abs=0)
    assert result['tail_bound'] < 1e-10
    assert result['energy_shift_J'] < 0
    swapped = _evaluate(replace(hole, carrier='electron'), replace(electron, carrier='hole'))
    assert swapped['coefficient'] == pytest.approx(result['coefficient'], rel=1e-14)
    json.dumps(result, allow_nan=False)


def test_hard_wall_limit_and_scaling():
    electron = _request(1., 1e5)
    hole = replace(electron, carrier='hole')
    result = _evaluate(electron, hole)
    expected = 2 - (sici(2*math.pi)[0] - 0.5*sici(4*math.pi)[0])/math.pi
    assert result['coefficient'] == pytest.approx(expected, rel=2e-5)
    doubled = _evaluate(*(replace(r, radius_m=2*r.radius_m, depth_J=r.depth_J/4) for r in (electron, hole)))
    assert doubled['energy_shift_J'] == pytest.approx(result['energy_shift_J']/2, rel=1e-12, abs=0)
    screened = _evaluate(electron, hole, epsilon=24)
    assert screened['energy_shift_J'] == pytest.approx(result['energy_shift_J']/2, rel=1e-12, abs=0)


def test_unavailable_and_invalid_inputs():
    electron = _request(1., 4.)
    hole = replace(electron, carrier='hole', depth_J=0.)
    result = _evaluate(electron, hole)
    assert result['status'] == 'unavailable'
    assert result['hole']['status'] == 'no_bound_state'
    assert result['energy_shift_J'] is None
    with pytest.raises(ValueError, match='matched'):
        _evaluate(electron, replace(hole, radius_m=4e-9))
    with pytest.raises(ValueError, match='permittivity'):
        _evaluate(electron, hole, epsilon=0)
