# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Angular projection, radial normalization and U5 negative controls."""
from dataclasses import replace
import json
import math

import pytest
from scipy.integrate import quad
from scipy.special import spherical_jn, spherical_kn

from examples import phase_u5_coulomb_angular_coupling as study
from examples.phase_u3_coulomb_spectral_gap import first_excitation
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.finite_confinement import evaluate_finite_confinement
from test_phase_t2_finite_confinement import _request


@pytest.mark.parametrize('r,s', [(0.3, 0.8), (1.2, 0.6), (2., 2.)])
def test_angular_projection_against_direct_cosine_integral(r, s):
    actual = -math.sqrt(3)/2 * quad(
        lambda cosine: cosine/math.sqrt(r*r+s*s-2*r*s*cosine),
        -1, 1, epsabs=1e-11,
    )[0]
    expected = study.ANGULAR_FACTOR*min(r, s)/max(r, s)**2
    assert actual == pytest.approx(expected, rel=1e-10)


def test_normalized_exterior_matches_modified_spherical_bessel():
    state = evaluate_finite_confinement(_request(1., 6.)).to_dict()
    excitation = first_excitation(state)
    x = excitation['x']
    y = math.sqrt((state['rho']-x)*(state['rho']+x))
    envelope = study._p_envelope(x, y, 1e-12)
    assert study._integral(lambda t: envelope(t)**2, tolerance=1e-12) == pytest.approx(1, abs=1e-11)
    for t in (1.1, 2., 4.):
        expected = t*spherical_kn(1, y*t)/spherical_kn(1, y)
        assert envelope(t)/envelope(1) == pytest.approx(expected, rel=1e-12)
    assert envelope(0.5)/envelope(1) == pytest.approx(
        0.5*spherical_jn(1, x*0.5)/spherical_jn(1, x),
    )


def test_exchange_symmetry():
    electron = evaluate_finite_confinement(_request(1., 6.)).to_dict()
    hole = evaluate_finite_confinement(replace(_request(1., 4.), carrier='hole')).to_dict()
    first = study.angular_coupling(electron, hole)
    second = study.angular_coupling(hole, electron)
    assert first['signed_coefficient'] == pytest.approx(second['signed_coefficient'], rel=1e-12)
    assert first['pair_excitation_gap_J'] == second['pair_excitation_gap_J']


def test_population_scaling_and_integrity():
    report = study.run_study()
    rows = {row['label']: row['channel'] for row in report['cases']}
    base, screened = rows['baseline'], rows['weaker_screening']
    assert base['status'] == screened['status'] == 'evaluated'
    assert base['refinement_change'] < 1e-8*abs(base['signed_coefficient'])
    assert base['second_order_energy_J'] < 0
    assert screened['first_order_amplitude_magnitude'] == pytest.approx(2*base['first_order_amplitude_magnitude'])
    assert screened['second_order_energy_J'] == pytest.approx(4*base['second_order_energy_J'], rel=1e-10, abs=0)
    for name in ('smaller_radius', 'shallower_hole'):
        assert rows[name] == {'status': 'unavailable', 'reason': 'bound_1p_pair_unavailable'}
    assert rows['unbound_hole'] == {'status': 'unavailable', 'reason': 'ground_state_unavailable'}
    assert json.loads(json.dumps(report, allow_nan=False)) == report
    assert report['study_hash'] == canonical_hash({k: v for k, v in report.items() if k != 'study_hash'})


def test_integration_failure_is_retained(monkeypatch):
    def fail(*args, **kwargs):
        raise ArithmeticError('test integration failure')
    monkeypatch.setattr(study, 'angular_coupling', fail)
    assert all(
        row['channel'] == {'status': 'numerical_failure', 'reason': 'test integration failure'}
        for row in study.run_study()['cases']
    )
