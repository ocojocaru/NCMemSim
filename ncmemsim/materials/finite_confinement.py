# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Isolated l=0 ground state of the declared spherical finite well."""
from dataclasses import dataclass as _dataclass, fields as _fields
import math as _math

from ..barrier_evaluation import _product
from ..constants import ELECTRON_MASS_KG as _M0, HBAR_J_S as _HBAR
from .finite_confinement_contracts import FiniteConfinementRequest as _Request

__all__ = ['FiniteConfinementResult', 'evaluate_finite_confinement']


@_dataclass(frozen=True, slots=True)
class FiniteConfinementResult:
    """Ground-state diagnostics and a reference to the original request."""

    request: _Request
    status: str
    reason: str | None = None
    rho: float | None = None
    beta: float | None = None
    threshold_residual: float | None = None
    x_bracket: tuple[float, float] | None = None
    depth_fraction_bracket: tuple[float, float] | None = None
    iterations: int = 0
    x: float | None = None
    y: float | None = None
    scaled_matching_residual: float | None = None
    energy_J: float | None = None
    penetration_depth_m: float | None = None
    inside_probability: float | None = None
    outside_probability: float | None = None

    def to_dict(self):
        raw = {field.name: getattr(self, field.name) for field in _fields(self)}
        raw['request'] = self.request.to_dict()
        for key in ('x_bracket', 'depth_fraction_bracket'):
            if raw[key] is not None:
                raw[key] = list(raw[key])
        return dict(
            raw,
            schema_version='finite-spherical-confinement-result-v1',
            request_hash=self.request.contract_hash,
            constants={'hbar_J_s': _HBAR, 'electron_mass_kg': _M0},
        )


def _matching(x, scaled_tail, scaled_mass, inverse_scale):
    sinc = _math.sin(x) / x if x else 1.
    if x < 1e-3:
        squared = x*x
        difference = squared*(-1/3 + squared*(1/30 - squared/840))
    else:
        difference = _math.cos(x) - sinc
    return difference*inverse_scale + (scaled_mass + scaled_tail)*sinc


def _probabilities(x, y):
    if x < 1e-3:
        squared = x*x
        inner = squared*(1/3 + squared*(-1/15 + squared*2/315))
    else:
        inner = .5*(1 - _math.sin(2*x)/(2*x))
    outer = _product((_math.sin(x), _math.sin(x)), (2., y))
    scale = max(inner, outer)
    inside_weight, outside_weight = inner/scale, outer/scale
    total = inside_weight + outside_weight
    inside, outside = inside_weight/total, outside_weight/total
    if not (inside > 0 and outside > 0):
        raise ArithmeticError('probability_underflow')
    return inside, outside


def evaluate_finite_confinement(request):
    """Evaluate a typed T1 request with its archived numerical policy."""
    if type(request) is not _Request:
        raise ValueError('FiniteConfinementRequest required')
    if request.depth_J == 0:
        return FiniteConfinementResult(request, 'no_bound_state', 'zero_depth')
    policy = request.numerical_policy
    diagnostics = {}
    try:
        beta = _product((request.inside_mass_m0,), (request.outside_mass_m0,))
        rho = _product((request.radius_m, _math.sqrt(2.), _math.sqrt(_M0),
                        _math.sqrt(request.inside_mass_m0), _math.sqrt(request.depth_J)),
                       (_HBAR,))
        diagnostics.update(beta=beta, rho=rho)
        root_beta = _math.sqrt(beta)
        tail_scale = _product((root_beta, rho))
        scale = max(1., beta, tail_scale)
        shallow = rho < _math.pi
        if shallow:
            endpoint = _matching(rho, 0., beta/scale, 1/scale)
            diagnostics['threshold_residual'] = endpoint
            guard = policy['threshold_guard']
            if endpoint > guard:
                return FiniteConfinementResult(request, 'no_bound_state', 'below_threshold',
                                               **diagnostics)
            if endpoint >= -guard:
                return FiniteConfinementResult(request, 'threshold_unresolved', 'threshold_guard',
                                               **diagnostics)

        # The bracket coordinate increases with energy. For shallow wells it is
        # convenient to bisect the exterior decay fraction in reverse order.
        # This resolves the tail when the interior wave number rounds to rho.
        lower, upper = (1., 0.) if shallow else (0., _math.pi)

        def coordinates(value):
            if shallow:
                fraction = (1 - value)*(1 + value)
                return rho*_math.sqrt(fraction), fraction, value
            ratio = value/rho
            return value, ratio*ratio, _math.sqrt((1 - ratio)*(1 + ratio))

        for iteration in range(1, policy['max_iterations'] + 1):
            middle = lower + (upper - lower)*.5
            x, fraction, decay_fraction = coordinates(middle)
            residual = _matching(x, (tail_scale/scale)*decay_fraction,
                                 beta/scale, 1/scale)
            low_x, low_fraction, _ = coordinates(lower)
            high_x, high_fraction, _ = coordinates(upper)
            diagnostics.update(iterations=iteration, x_bracket=(low_x, high_x),
                               depth_fraction_bracket=(low_fraction, high_fraction),
                               scaled_matching_residual=residual)
            if (high_x - low_x <= policy['max_x_bracket_width']
                and high_fraction - low_fraction <= policy['max_depth_fraction_bracket_width']
                and abs(residual) <= policy['max_scaled_matching_residual']):
                if not (0 < x < min(_math.pi, rho) and 0 < fraction < 1
                        and decay_fraction > 0):
                    status = 'threshold_unresolved' if shallow and x == rho else 'numerical_failure'
                    return FiniteConfinementResult(request, status,
                                                   'interior_energy_unrepresentable', **diagnostics)
                energy = _product((request.depth_J, fraction))
                if energy >= request.depth_J:
                    return FiniteConfinementResult(request, 'threshold_unresolved',
                                                   'interior_energy_unrepresentable', **diagnostics)
                y = _product((rho, decay_fraction), (root_beta,))
                penetration = _product((request.radius_m,), (y,))
                inside, outside = _probabilities(x, y)
                return FiniteConfinementResult(
                    request, 'bound', x=x, y=y, energy_J=energy,
                    penetration_depth_m=penetration, inside_probability=inside,
                    outside_probability=outside, **diagnostics,
                )
            if middle == lower or middle == upper:
                return FiniteConfinementResult(request, 'numerical_failure', 'bracket_stagnated',
                                               **diagnostics)
            if residual > 0:
                lower = middle
            else:
                upper = middle
        return FiniteConfinementResult(request, 'numerical_failure', 'iteration_budget',
                                       **diagnostics)
    except ArithmeticError as error:
        return FiniteConfinementResult(request, 'numerical_failure', str(error), **diagnostics)
