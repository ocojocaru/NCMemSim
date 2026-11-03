# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Isolated positive-segment WKB action; no current or simulator integration."""
from __future__ import annotations

import math as _math
import sys as _sys
from .barrier_contracts import BarrierEvaluationSpec as _Spec
from .constants import ELECTRON_MASS_KG as _M0, HBAR_J_S as _HBAR
from .performance_contracts import _Owned, _canonical

__all__ = ['BarrierEvaluationResult', 'evaluate_barrier_profile']

_METHOD = 'scaled_positive_linear_action_v1'


def _product(numerators, denominators=()):
    """Multiply finite positive factors without intermediate overflow/underflow."""
    mantissa, exponent = 1., 0
    for factors, divide in ((numerators, False), (denominators, True)):
        for factor in factors:
            if not _math.isfinite(factor) or factor <= 0:
                raise ArithmeticError('nonpositive_or_nonfinite_factor')
            part, power = _math.frexp(factor)
            mantissa = mantissa / part if divide else mantissa * part
            exponent += -power if divide else power
            mantissa, adjustment = _math.frexp(mantissa)
            exponent += adjustment
    try:
        result = _math.ldexp(mantissa, exponent)
    except OverflowError as exc:
        raise ArithmeticError('positive_quantity_overflow') from exc
    if not _math.isfinite(result):
        raise ArithmeticError('positive_quantity_overflow')
    if result == 0:
        raise ArithmeticError('positive_quantity_underflow')
    return result


def _attenuation(exponent):
    transmission = _math.exp(-exponent)
    if exponent == 0:
        status = 'zero_forbidden_action'
    elif transmission == 0:
        status = 'transmission_underflow'
    elif transmission < _sys.float_info.min:
        status = 'subnormal_transmission'
    elif transmission == 1:
        status = 'transmission_rounded_to_one'
    else:
        status = 'finite_transmission'
    return dict(wkb_exponent=exponent, log_transmission=-exponent,
                transmission=transmission, attenuation_status=status)


def _segment(raw, incident):
    # These are the represented U-E values, subtracted exactly once. S1 checks
    # their finite domain; no effective field or incident energy is inferred.
    start = float(raw['start_potential_energy_J'] - incident)
    end = float(raw['end_potential_energy_J'] - incident)
    row = dict(segment_id=raw['segment_id'], start_forbidden_energy_J=start,
               end_forbidden_energy_J=end)
    high, low = max(start, end), min(start, end)
    if high <= 0:
        return {**row, 'status': 'completed', 'domain': 'no_forbidden_region',
                'action_J_s': 0., **_attenuation(0.), 'failure': None}
    factors = [float(raw['length_m']), _math.sqrt(2.), _math.sqrt(_M0),
               _math.sqrt(raw['effective_mass_m0']), _math.sqrt(high)]
    divisors = []
    if low >= 0:
        # (a^3-b^3)/(a^2-b^2) is rationalized and scaled by a=sqrt(high).
        # Avoid subtracting nearly equal 3/2 powers in the near-flat limit.
        ratio = _math.sqrt(low) / _math.sqrt(high)
        factors.append((2./3.) * (1. + ratio + ratio*ratio) / (1. + ratio))
        domain = 'fully_forbidden' if low > 0 else 'boundary_turning_point'
    else:
        # The forbidden fraction is high/(high+abs(low)). Keep its factors
        # separate: that ratio may underflow even when the final action does not.
        scale = max(high, -low)
        factors.extend([2./3., high])
        divisors.extend([scale, high/scale + (-low)/scale])
        domain = 'interior_turning_point'
    row['domain'] = domain
    try:
        action = _product(factors, divisors)
        exponent = _product([2., *factors], [_HBAR, *divisors])
    except ArithmeticError as exc:
        return {**row, 'status': 'failed', 'action_J_s': None,
                'wkb_exponent': None, 'log_transmission': None,
                'transmission': None, 'attenuation_status': 'unavailable',
                'failure': str(exc)}
    return {**row, 'status': 'completed', 'action_J_s': action,
            **_attenuation(exponent), 'failure': None}


def _evaluate(request):
    profile = request['profile']
    rows = [_segment(row, profile['incident_energy_J']) for row in profile['segments']]
    failed = sum(row['status'] == 'failed' for row in rows)
    summary = dict(status='failed' if failed else 'completed',
        attempted_segment_count=len(rows), completed_segment_count=len(rows)-failed,
        failed_segment_count=failed, action_J_s=None, wkb_exponent=None,
        log_transmission=None, transmission=None, attenuation_status='unavailable',
        failure='segment_numeric_range_failure' if failed else None)
    if not failed:
        try:
            action = _math.fsum(row['action_J_s'] for row in rows)
            exponent = _math.fsum(row['wkb_exponent'] for row in rows)
            if not _math.isfinite(action) or not _math.isfinite(exponent):
                raise OverflowError
            summary.update(action_J_s=action, **_attenuation(exponent))
        except OverflowError:
            summary.update(status='failed', failure='aggregate_overflow')
    return dict(schema_version='ncmemsim-barrier-evaluation-v1', request=request,
        request_hash=_Spec.from_dict(request).contract_hash,
        profile_hash=_profile_hash(profile), method=_METHOD,
        constants=dict(electron_mass_kg=_M0, hbar_J_s=_HBAR),
        segments=rows, summary=summary, evaluated=True,
        approximation='positive_segment_action_only',
        restoration_policy='four_ulp_action_exponent_and_exp_at_stored_exponent',
        interface_matching=False,
        simulator_attachment=False, experimental_qualification=False)


def _profile_hash(raw):
    from .barrier_contracts import BarrierProfile
    return BarrierProfile.from_dict(raw).contract_hash


class BarrierEvaluationResult(_Owned):
    """Owned computed result, including source request and numerical failure rows.

    Restoration checks the isolated action with an explicit four-ULP roundoff
    budget and retains accepted original values. This is not device replay.
    """
    __slots__ = ()

    def __init__(self, request):
        if isinstance(request, _Spec):
            request = request.to_dict()
        request = _Spec.from_dict(request).to_dict()
        self._store(_evaluate(request))

    @property
    def summary(self):
        return self.to_dict()['summary']

    @property
    def segments(self):
        return self.to_dict()['segments']

    @classmethod
    def from_dict(cls, raw):
        if type(raw) is not dict or 'request' not in raw:
            raise ValueError('source-linked barrier result object required')
        result = cls(raw['request'])
        expected = result.to_dict()
        # Compare exp at the stored exponent: a one-ULP exponent difference can
        # cause far more than one ULP in a small transmission. Request tolerances
        # never relax archive checks; the small portability budget is fixed.
        try:
            if len(raw['segments']) != len(expected['segments']):
                raise ValueError('segment count mismatch')
            pairs = list(zip(expected['segments'], raw['segments']))
            pairs.append((expected['summary'], raw['summary']))
            for current, original in pairs:
                if current['wkb_exponent'] is None:
                    continue
                if not _near(current['action_J_s'], original['action_J_s']):
                    raise ValueError('action outside roundoff budget')
                if not _near(current['wkb_exponent'], original['wkb_exponent']):
                    raise ValueError('exponent outside roundoff budget')
                attenuation = _attenuation(original['wkb_exponent'])
                if not _near(attenuation['transmission'], original['transmission']):
                    raise ValueError('transmission outside roundoff budget')
                if attenuation['transmission'] == 1 and original['transmission'] != 1:
                    raise ValueError('unit transmission rounding identity mismatch')
                if (type(original['log_transmission']) is not float or
                    original['log_transmission'] != -original['wkb_exponent'] or
                    original['attenuation_status'] != attenuation['attenuation_status']):
                    raise ValueError('attenuation identity mismatch')
                for key in ('action_J_s', 'wkb_exponent', 'log_transmission',
                            'transmission', 'attenuation_status'):
                    current[key] = original[key]
        except (KeyError, TypeError, OverflowError) as exc:
            raise ValueError('malformed barrier diagnostics') from exc
        if _canonical(expected) != _canonical(raw):
            raise ValueError('barrier result/source/diagnostic mismatch')
        restored = cls.__new__(cls)
        restored._store(raw)
        return restored


def _near(expected, original):
    if type(original) is not float or not _math.isfinite(original) or original < 0:
        return False
    if expected == 0 or original == 0:
        return original == expected
    return abs(expected-original) <= 4*max(_math.ulp(expected), _math.ulp(original))


def evaluate_barrier_profile(request):
    """Evaluate an S1 request only; failed numerical segments remain explicit."""
    return BarrierEvaluationResult(request)
