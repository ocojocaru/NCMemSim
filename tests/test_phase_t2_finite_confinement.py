# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Predeclared threshold controls and independent radial eigenvalue checks."""
from dataclasses import replace
from decimal import Decimal, localcontext
import json
import math

import numpy as np
import pytest
from scipy.linalg import eigh_tridiagonal

from ncmemsim.constants import ELECTRON_MASS_KG, HBAR_J_S, PLANCK_J_S
from ncmemsim.materials.finite_confinement import evaluate_finite_confinement
from ncmemsim.materials.finite_confinement_contracts import FiniteConfinementRequest
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.structural import StructuralEvidence

_PI = Decimal('3.1415926535897932384626433832795028841971693993751058209749445923078164')


def _sine(x):
    term = total = x
    for n in range(1, 85):
        term *= -(x*x)/((2*n)*(2*n+1))
        total += term
    return total


def _cosine(x):
    return _sine(_PI/2 - x)


def _reference_root(function, high):
    low = Decimal(0)
    for _ in range(190):
        midpoint = (low + high)/2
        if function(midpoint) > 0:
            low = midpoint
        else:
            high = midpoint
    return (low + high)/2


def _threshold(beta):
    with localcontext() as context:
        context.prec = 65
        if beta == 1:
            return float(_PI/2)
        return float(_reference_root(
            lambda x: x*_cosine(x)/_sine(x) + Decimal(beta)-1, _PI,
        ))


def _request(beta, rho):
    evidence = StructuralEvidence('T2 synthetic control', 'dimensionless control grid',
                                  ParameterStatus.ASSUMED, 'Explicit illustrative dot and host')
    radius, inside_mass = 2e-9, .2
    depth = (rho*HBAR_J_S/radius)**2/(2*ELECTRON_MASS_KG*inside_mass)
    return FiniteConfinementRequest(
        'electron', 'synthetic dot', 'synthetic host', radius, inside_mass,
        inside_mass/beta, depth, 300., evidence, evidence, evidence, evidence, evidence,
    )


def _reference(request):
    """Decimal logarithmic-derivative matching and separately normalized tail."""
    with localcontext() as context:
        context.prec = 65
        inside = Decimal(request.inside_mass_m0)
        outside = Decimal(request.outside_mass_m0)
        rho = (Decimal(request.radius_m)
               * (2*Decimal(ELECTRON_MASS_KG)*inside*Decimal(request.depth_J)).sqrt()
               / Decimal(HBAR_J_S))
        beta = inside/outside

        def mismatch(x):
            y = ((rho*rho-x*x)/beta).sqrt()
            inside_derivative = (x*_cosine(x)/_sine(x)-1)/inside
            outside_derivative = (-y-1)/outside
            return inside_derivative-outside_derivative

        x = _reference_root(mismatch, min(_PI, rho))
        y = ((rho*rho-x*x)/beta).sqrt()
        outer = _sine(x)**2/(2*y)
        inner = Decimal('.5')-_sine(2*x)/(4*x)
        return float((x/rho)**2), float(outer/(inner+outer))


@pytest.mark.parametrize('beta', [.1, 1., 10.])
@pytest.mark.parametrize('relative_depth_scale,status', [
    (.5, 'no_bound_state'), (1-1e-6, 'no_bound_state'),
    (1., 'threshold_unresolved'), (1+1e-6, 'bound'), (2., 'bound'), (100., 'bound'),
])
def test_predeclared_grid(beta, relative_depth_scale, status):
    request = _request(beta, _threshold(beta)*relative_depth_scale)
    result = evaluate_finite_confinement(request)
    assert result.status == status, result.to_dict()
    raw = json.loads(json.dumps(result.to_dict(), allow_nan=False))
    assert raw['request_hash'] == request.contract_hash
    if status != 'bound':
        assert raw['energy_J'] is None and raw['outside_probability'] is None
        assert raw['reason']
        return
    expected_energy, expected_outside = _reference(request)
    assert result.energy_J/request.depth_J == pytest.approx(expected_energy, abs=1e-9, rel=0)
    assert result.outside_probability == pytest.approx(expected_outside, abs=1e-8, rel=0)
    assert result.inside_probability + result.outside_probability == pytest.approx(1., abs=1e-10, rel=0)
    assert 0 < result.energy_J < request.depth_J
    assert result.x_bracket[0] <= result.x <= result.x_bracket[1]
    assert result.x_bracket[1]-result.x_bracket[0] <= 1e-12
    assert result.depth_fraction_bracket[1]-result.depth_fraction_bracket[0] <= 1e-12
    assert abs(result.scaled_matching_residual) <= 1e-11


def _radial_grid_energy(beta, rho, cells_per_radius, outer_radius):
    """Cell-centred spherical flux balance in r/R with a distant zero envelope."""
    spacing = 1./cells_per_radius
    faces = np.arange(outer_radius*cells_per_radius+1)*spacing
    volumes = np.diff(faces**3)/3
    coefficients = np.where(faces[1:-1] < 1., 1., beta)
    coefficients[cells_per_radius-1] = 2*beta/(1+beta)
    conductance = coefficients*faces[1:-1]**2/spacing
    diagonal = np.r_[0., conductance] + np.r_[conductance, 0.]
    diagonal[-1] += 2*beta*faces[-1]**2/spacing
    diagonal /= volumes
    diagonal[cells_per_radius:] += rho**2
    off_diagonal = -conductance/np.sqrt(volumes[1:]*volumes[:-1])
    eigenvalue = eigh_tridiagonal(diagonal, off_diagonal, eigvals_only=True,
                                 select='i', select_range=(0, 0))[0]
    return eigenvalue/rho**2


@pytest.mark.parametrize('beta', [.25, 1.])
def test_independent_radial_grid_and_domain_refinement(beta):
    rho = 4.
    request = _request(beta, rho)
    result = evaluate_finite_confinement(request)
    expected = result.energy_J/request.depth_J
    grid = [_radial_grid_energy(beta, rho, n, 6) for n in (40, 80, 160, 320)]
    errors = [abs(value-expected) for value in grid]
    assert all(current < previous for previous, current in zip(errors, errors[1:]))
    enlarged = _radial_grid_energy(beta, rho, 320, 9)
    assert abs(enlarged-grid[-1]) < 1e-8
    assert abs(enlarged-expected) < 2e-5
    inside_derivative = result.x*math.cos(result.x)/math.sin(result.x)-1
    outside_derivative = beta*(-result.y-1)
    assert inside_derivative == pytest.approx(outside_derivative, rel=1e-9)



def test_large_barrier_recovers_published_infinite_well_limit():
    request = _request(1., 1e5)
    result = evaluate_finite_confinement(request)
    infinite = PLANCK_J_S**2/(8*ELECTRON_MASS_KG*request.inside_mass_m0*request.radius_m**2)
    assert result.status == 'bound'
    assert 0 < result.energy_J < infinite
    assert result.energy_J/infinite == pytest.approx(1., abs=3e-5, rel=0)


def test_zero_depth_and_unrepresentable_binding_are_distinct():
    request = _request(1., math.pi/2*(1+1e-9))
    assert evaluate_finite_confinement(request).status == 'threshold_unresolved'
    empty = evaluate_finite_confinement(replace(request, depth_J=0.))
    assert (empty.status, empty.reason, empty.energy_J) == ('no_bound_state', 'zero_depth', None)


@pytest.mark.parametrize('changes', [
    {'inside_mass_m0': 1e308, 'outside_mass_m0': 5e-324},
    {'inside_mass_m0': 5e-324, 'outside_mass_m0': 1e308},
    {'radius_m': 5e-324, 'depth_J': 5e-324},
])
def test_unrepresentable_dimensionless_inputs_are_failures(changes):
    result = evaluate_finite_confinement(replace(_request(1., 4.), **changes))
    assert result.status == 'numerical_failure'
    assert result.reason and result.energy_J is None
    json.dumps(result.to_dict(), allow_nan=False)
