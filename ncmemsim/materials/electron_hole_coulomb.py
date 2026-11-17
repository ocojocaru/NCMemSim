# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Isolated first-order direct Coulomb correction for spherical finite wells."""
import math as _math

from numpy.polynomial.legendre import leggauss as _leggauss

from ..barrier_evaluation import _product
from ..constants import ELEMENTARY_CHARGE_C as _Q, EPSILON_0_F_M as _EPS0
from .finite_confinement import evaluate_finite_confinement as _evaluate
from .finite_confinement_contracts import FiniteConfinementRequest as _Request
from .structural import StructuralEvidence as _Evidence, _number

__all__ = ['evaluate_electron_hole_coulomb']

_TAIL_TARGET = 1e-10
_RELATIVE_TARGET = 1e-8


def _interior_integral(x, t):
    z = x * t
    if z < 0.01:
        z2 = z * z
        return t * z2 * (1/3 - z2 * (1/15 - z2 * (2/315 - z2/2835)))
    return 0.5 * t * (1 - _math.sin(2*z)/(2*z))


def _radial(state):
    x, y = state.x, state.y
    interface = _math.sin(x)**2
    normalization = _interior_integral(x, 1.) + interface/(2*y)
    inside = _interior_integral(x, 1.) / normalization
    outside = interface/(2*y) / normalization
    if not _math.isclose(outside, state.outside_probability, rel_tol=1e-10):
        raise ArithmeticError('radial normalization disagrees with carrier result')

    def density_and_cdf(t):
        if t <= 1:
            return _math.sin(x*t)**2 / normalization, _interior_integral(x, t) / normalization
        exponent = -2*y*(t-1)
        return interface * _math.exp(exponent) / normalization, inside - outside * _math.expm1(exponent)

    return density_and_cdf, outside


def _integrate(function, edges, order):
    nodes, weights = _leggauss(order)
    pieces = []
    for lo, hi in zip(edges, edges[1:]):
        half = (hi-lo)*0.5
        midpoint = lo+half
        pieces.append(half * _math.fsum(
            weight * function(midpoint + half * node) for node, weight in zip(nodes, weights)
        ))
    return _math.fsum(pieces)


def _coefficient(electron, hole):
    pe, outside_e = _radial(electron)
    ph, outside_h = _radial(hole)
    # Use both decay scales when subdividing the exterior integration domain.
    cutoffs = [(abs(_math.log(_TAIL_TARGET / 4)) / (2*state.y)) for state in (electron, hole)]
    end = 1 + max(cutoffs)
    if not _math.isfinite(end):
        raise ArithmeticError('exterior domain is not representable')
    edges = sorted({0., 1., end, *(
        1 + span*fraction for span in cutoffs for fraction in (0.01, 0.05, 0.2, 0.5, 1.)
    )})
    tail_bound = (outside_e * _math.exp(-2*electron.y*(end-1))
                  + outside_h * _math.exp(-2*hole.y*(end-1))) / end
    if tail_bound > _TAIL_TARGET:
        raise ArithmeticError('exterior tail exceeds the target')

    def integrand(t):
        if t == 0:
            return 0.
        density_e, cdf_e = pe(t)
        density_h, cdf_h = ph(t)
        return (density_e*cdf_h + density_h*cdf_e) / t

    previous = _integrate(integrand, edges, 16)
    for order in (32, 64, 128):
        current = _integrate(integrand, edges, order)
        change = abs(current - previous)
        if current > 0 and change + tail_bound <= current * _RELATIVE_TARGET:
            return float(current), float(change), tail_bound, order, end
        previous = current
    raise ArithmeticError('quadrature refinement budget exhausted')


def evaluate_electron_hole_coulomb(electron, hole, *, relative_permittivity, screening_evidence):
    """Evaluate a matched electron and hole request under uniform dielectric screening."""
    if type(electron) is not _Request or type(hole) is not _Request:
        raise ValueError('two finite confinement requests required')
    if (electron.carrier, hole.carrier) != ('electron', 'hole') or any(
        getattr(electron, field) != getattr(hole, field)
        for field in ('radius_m', 'temperature_K', 'dot_material', 'host_material')
    ):
        raise ValueError('matched electron and hole requests required')
    permittivity = _number(relative_permittivity, 'relative permittivity', positive=True)
    if type(screening_evidence) is not _Evidence:
        raise ValueError('screening evidence required')
    if screening_evidence.reported_uncertainty is not None and screening_evidence.uncertainty_unit != '1':
        raise ValueError('relative permittivity uncertainty must be dimensionless')
    e_state, h_state = _evaluate(electron), _evaluate(hole)
    result = {
        'schema_version': 'electron-hole-direct-coulomb-v1',
        'relative_permittivity': permittivity,
        'screening_evidence': screening_evidence.to_dict(),
        'electron': e_state.to_dict(), 'hole': h_state.to_dict(),
        'status': 'unavailable', 'reason': 'carrier_state_unavailable',
        'coefficient': None, 'energy_shift_J': None,
        'quadrature_change': None, 'tail_bound': None, 'order': None, 'outer_radius_over_R': None,
    }
    if e_state.status != 'bound' or h_state.status != 'bound':
        return result
    try:
        coefficient, change, tail, order, outer = _coefficient(e_state, h_state)
        energy = -_product((_Q, _Q, coefficient), (4*_math.pi, _EPS0, permittivity, electron.radius_m))
    except ArithmeticError as error:
        return dict(result, status='numerical_failure', reason=str(error))
    return dict(result, status='evaluated', reason=None, coefficient=coefficient, energy_shift_J=energy,
                quadrature_change=change, tail_bound=tail, order=order, outer_radius_over_R=outer)
