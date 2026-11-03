# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Independent high-precision limits and quadrature for the isolated WKB kernel."""
import copy
from decimal import Decimal, localcontext
import math
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest
from scipy.integrate import quad
from ncmemsim.barrier_contracts import (
    BarrierProvenance, BarrierSegment, BarrierProfile, BarrierEvaluationSpec,
)
from ncmemsim.barrier_evaluation import BarrierEvaluationResult, evaluate_barrier_profile
from ncmemsim.constants import ELECTRON_MASS_KG, HBAR_J_S


def request(start=3e-19, end=1e-19, length=5e-9, mass=.2, incident=0., more=()):
    provenance = BarrierProvenance('assumed', 'synthetic numerical control',
        'no measured parameter', 'isolated action', 'no interface matching')
    segments = [BarrierSegment('a', length, start, end, mass, provenance)]
    for i, values in enumerate(more):
        segments.append(BarrierSegment(str(i), *values, provenance))
    profile = BarrierProfile('numerical-control', segments, incident,
        'common electron energy zero', 'left boundary', 'left to right',
        'along_positive_axis', 'left', 'right', 'analytic test controls',
        'no current or experimental qualification')
    return BarrierEvaluationSpec(profile, 1e-12, 1e-10, 'predeclared S1 controls')


def decimal_reference(spec):
    """Independent 100-digit primitive, including exact represented input energies."""
    with localcontext() as ctx:
        ctx.prec = 100
        d = lambda value: Decimal(value)
        raw = spec.to_dict()['profile']; total = Decimal(0)
        for row in raw['segments']:
            a = d(row['start_potential_energy_J']) - d(raw['incident_energy_J'])
            b = d(row['end_potential_energy_J']) - d(raw['incident_energy_J'])
            left, right = max(a, Decimal(0)), max(b, Decimal(0))
            if a == b:
                integral = left.sqrt()
            else:
                integral = Decimal(2)/3 * (right*right.sqrt()-left*left.sqrt()) / (b-a)
            total += d(row['length_m']) * (2*d(ELECTRON_MASS_KG)*d(row['effective_mass_m0'])).sqrt() * integral
        return float(total), float(2*total/d(HBAR_J_S))


def check_reference(spec):
    result = evaluate_barrier_profile(spec)
    action, exponent = decimal_reference(spec)
    summary = result.summary
    assert summary['status'] == 'completed'
    assert abs(summary['wkb_exponent']-exponent) <= 1e-12+1e-10*abs(exponent)
    assert summary['action_J_s'] == pytest.approx(action, rel=1e-12, abs=0)
    assert summary['log_transmission'] == -summary['wkb_exponent']
    assert summary['transmission'] == math.exp(summary['log_transmission'])
    return result


@pytest.mark.parametrize('a', [-3., -1., 0., 1., 3.])
@pytest.mark.parametrize('b', [-3., -1., 0., 1., 3.])
def test_all_endpoint_sign_and_turning_limits(a, b):
    check_reference(request(a*1e-19, b*1e-19))


@pytest.mark.parametrize('target', [1e-12, .1, 1., 700., 740., 745., 746., 10000.])
def test_rectangular_action_across_transmission_ranges(target):
    mass = .2; height = 3e-19
    per_metre = 2*math.sqrt(2*ELECTRON_MASS_KG*mass*height)/HBAR_J_S
    result = check_reference(request(height, height, target/per_metre, mass))
    assert result.summary['wkb_exponent'] == pytest.approx(target, rel=1e-14)


@pytest.mark.parametrize('relative_delta', [-1e-12, -1e-15, -1e-16, 0., 1e-16, 1e-15, 1e-12])
@pytest.mark.parametrize('target', [.1, 100., 10000.])
def test_near_flat_limit_does_not_subtract_nearly_equal_powers(relative_delta, target):
    height = 3e-19
    per_metre = 2*math.sqrt(2*ELECTRON_MASS_KG*.2*height)/HBAR_J_S
    check_reference(request(height, height*(1+relative_delta), target/per_metre))


@pytest.mark.parametrize('a,b', [(3e-19, 1e-19), (1e-19, 3e-19),
    (3e-19, -1e-19), (-1e-19, 3e-19), (0., 3e-19),
    (3e-19, 0.), (3e-19, 3e-19*(1+1e-14))])
def test_independent_refined_gauss_kronrod_quadrature(a, b):
    spec = request(a, b); scale = max(abs(a), abs(b))
    points = [a/(a-b)] if a*b < 0 else None
    integrand = lambda x: math.sqrt(max(((1-x)*a+x*b)/scale, 0.))
    estimates = []
    for eps in (1e-9, 1e-12):
        value, error = quad(integrand, 0., 1., epsabs=eps, epsrel=eps,
                            points=points, limit=200)
        estimates.append(value)
        assert error >= 0
    assert abs(estimates[1]-estimates[0]) < 1e-10
    reference = 2*5e-9*math.sqrt(2*ELECTRON_MASS_KG*.2*scale)/HBAR_J_S*estimates[-1]
    actual = evaluate_barrier_profile(spec).summary['wkb_exponent']
    assert abs(actual-reference) <= 1e-12+1e-10*abs(reference)


def test_incident_energy_subtracted_exactly_once():
    spec = request(4e-19, 2e-19, incident=1e-19)
    result = check_reference(spec)
    row = result.segments[0]
    assert row['start_forbidden_energy_J'] == 4e-19-1e-19
    assert row['end_forbidden_energy_J'] == 2e-19-1e-19
    equivalent = evaluate_barrier_profile(request(4e-19-1e-19, 2e-19-1e-19))
    assert result.summary == equivalent.summary


def test_segment_sum_heterogeneous_mass_and_interface_values_are_retained():
    spec = request(more=[(2e-9, 5e-19, 2e-19, .5)])
    result = check_reference(spec)
    assert result.summary['wkb_exponent'] == math.fsum(row['wkb_exponent'] for row in result.segments)
    assert result.segments[0]['end_forbidden_energy_J'] == 1e-19
    assert result.segments[1]['start_forbidden_energy_J'] == 5e-19
    assert len(result.segments) == 2


def test_same_energy_reversal_and_linear_splitting_smoke():
    spec = request()
    profile = spec.to_dict()['profile']
    from ncmemsim.barrier_contracts import BarrierProfile
    reversed_spec = BarrierEvaluationSpec(BarrierProfile.from_dict(profile).reversed(),
        1e-12, 5e-13, 'same-energy reversal')
    expected = evaluate_barrier_profile(spec).summary['wkb_exponent']
    actual = evaluate_barrier_profile(reversed_spec).summary['wkb_exponent']
    assert abs(actual-expected) <= 1e-12+5e-13*abs(expected)
    split = request(3e-19, 2e-19, 2.5e-9,
                    more=[(2.5e-9, 2e-19, 1e-19, .2)])
    actual = evaluate_barrier_profile(split).summary['wkb_exponent']
    assert abs(actual-expected) <= 1e-12+5e-13*abs(expected)


@pytest.mark.parametrize('start,end,length,mass', [
    (1e308, 1e308, 1e-300, 1e308),
    (1e100, 1e100, 1e200, 5e-324),
    (1e-200, -1e200, 1e300, 1e300),
])
def test_scaled_products_avoid_intermediate_range_loss(start, end, length, mass):
    check_reference(request(start, end, length, mass))


@pytest.mark.parametrize('length,reason', [(1e300, 'positive_quantity_overflow'),
                                         (5e-324, 'positive_quantity_underflow')])
def test_numeric_range_failures_preserve_other_segments(length, reason):
    spec = request(1., 1., length, more=[(1e-9, 3e-19, 1e-19, .2)])
    result = evaluate_barrier_profile(spec)
    assert result.summary['status'] == 'failed'
    assert result.summary['failed_segment_count'] == 1
    assert result.summary['completed_segment_count'] == 1
    assert result.summary['wkb_exponent'] is None
    assert result.segments[0]['failure'] == reason
    assert result.segments[1]['status'] == 'completed'
    assert result.to_dict()['request_hash'] == spec.contract_hash
    assert BarrierEvaluationResult.from_json(result.to_json()).to_json() == result.to_json()


def test_aggregate_overflow_is_not_a_partial_sum():
    result = evaluate_barrier_profile(request(1., 1., 6e288, 1.,
        more=[(6e288, 1., 1., 1.)]))
    assert all(row['status'] == 'completed' for row in result.segments)
    assert result.summary['status'] == 'failed'
    assert result.summary['failure'] == 'aggregate_overflow'
    assert result.summary['wkb_exponent'] is None


def test_zero_action_underflow_and_subnormal_are_distinct():
    assert evaluate_barrier_profile(request(-1., 0.)).summary['attenuation_status'] == 'zero_forbidden_action'
    factor = 2*math.sqrt(2*ELECTRON_MASS_KG*.2*3e-19)/HBAR_J_S
    underflow = evaluate_barrier_profile(request(length=10000/factor, end=3e-19))
    assert underflow.summary['attenuation_status'] == 'transmission_underflow'
    assert underflow.summary['transmission'] == 0
    assert math.isfinite(underflow.summary['log_transmission'])
    subnormal = evaluate_barrier_profile(request(length=740/factor, end=3e-19))
    assert subnormal.summary['attenuation_status'] == 'subnormal_transmission'
    tiny = evaluate_barrier_profile(request(length=1e-30, end=3e-19))
    assert tiny.summary['attenuation_status'] == 'transmission_rounded_to_one'
    assert tiny.summary['wkb_exponent'] > 0


@pytest.mark.parametrize('fault', ['extra', 'missing', 'schema', 'request_hash', 'profile_hash',
    'method', 'constant', 'row', 'summary', 'failure', 'attachment', 'qualification'])
def test_result_reconstruction_rejects_changed_source_or_diagnostics(fault):
    raw = evaluate_barrier_profile(request()).to_dict()
    if fault == 'extra': raw['extra'] = 1
    elif fault == 'missing': del raw['segments']
    elif fault == 'schema': raw['schema_version'] = 'future'
    elif fault in ('request_hash', 'profile_hash'): raw[fault] = 'a'*64
    elif fault == 'method': raw['method'] = 'other'
    elif fault == 'constant': raw['constants']['hbar_J_s'] *= 2
    elif fault == 'row': raw['segments'][0]['wkb_exponent'] *= 2
    elif fault == 'summary': raw['summary']['transmission'] = 1.
    elif fault == 'failure': raw['segments'][0]['failure'] = 'forged'
    elif fault == 'attachment': raw['simulator_attachment'] = True
    else: raw['experimental_qualification'] = True
    with pytest.raises(ValueError): BarrierEvaluationResult.from_dict(raw)


def test_result_ownership_roundtrip_and_strict_json():
    result = evaluate_barrier_profile(request())
    restored = BarrierEvaluationResult.from_json(result.to_json())
    assert result.contract_hash == restored.contract_hash
    raw = result.summary; raw['status'] = 'forged'
    rows = result.segments; rows.clear()
    assert result.summary['status'] == 'completed' and len(result.segments) == 1
    with pytest.raises(AttributeError): result._serialized = 'forged'
    with pytest.raises(AttributeError): del result._serialized
    with pytest.raises(ValueError): BarrierEvaluationResult.from_json(result.to_json().replace('{', '{"method":"forged",', 1))
    with pytest.raises(ValueError): BarrierEvaluationResult.from_json('{"request":NaN}')


def test_kernel_never_calls_existing_transport_or_simulator(monkeypatch):
    from ncmemsim.tunneling import TunnelingEngine
    import ncmemsim.transport.tat as tat
    from ncmemsim.simulator import Simulator
    def forbidden(*args, **kwargs): raise AssertionError('isolated S2 evaluator')
    monkeypatch.setattr(TunnelingEngine, 'trapezoidal_wkb', forbidden)
    monkeypatch.setattr(tat, 'linear_wkb_transmission', forbidden)
    monkeypatch.setattr(Simulator, 'relax_voltage', forbidden)
    result = evaluate_barrier_profile(request())
    assert not result.to_dict()['simulator_attachment']
    assert BarrierEvaluationResult.from_json(result.to_json()).contract_hash == result.contract_hash


def test_tolerances_are_request_metadata_not_a_claim_of_measured_accuracy():
    spec = request(); raw = spec.to_dict()
    raw['exponent_atol'] = 1e-20; raw['exponent_rtol'] = 1e-20
    changed = evaluate_barrier_profile(raw)
    original = evaluate_barrier_profile(spec)
    assert changed.summary == original.summary
    assert changed.contract_hash != original.contract_hash
    assert not changed.to_dict()['experimental_qualification']


def test_portable_roundoff_budget_preserves_original_bytes():
    result = evaluate_barrier_profile(request())
    raw = result.to_dict()
    for row in [*raw['segments'], raw['summary']]:
        row['action_J_s'] = math.nextafter(row['action_J_s'], math.inf)
        row['wkb_exponent'] = math.nextafter(row['wkb_exponent'], math.inf)
        row['log_transmission'] = -row['wkb_exponent']
        row['transmission'] = math.exp(row['log_transmission'])
    restored = BarrierEvaluationResult.from_dict(raw)
    assert restored.to_dict() == raw
    assert restored.contract_hash != result.contract_hash
    assert BarrierEvaluationResult.from_json(restored.to_json()).contract_hash == restored.contract_hash


@pytest.mark.parametrize('fault', ['outside_budget', 'negative_action', 'negative_exponent',
    'zero_action_changed', 'unit_transmission_changed', 'bool', 'nonfinite'])
def test_roundoff_policy_does_not_relax_scientific_semantics(fault):
    raw = evaluate_barrier_profile(request(-1., -1.) if fault == 'zero_action_changed'
                                   else request()).to_dict()
    row = raw['segments'][0]
    if fault == 'outside_budget':
        for _ in range(16): row['wkb_exponent'] = math.nextafter(row['wkb_exponent'], math.inf)
        row['log_transmission'] = -row['wkb_exponent']
        row['transmission'] = math.exp(row['log_transmission'])
    elif fault == 'negative_action': row['action_J_s'] *= -1
    elif fault == 'negative_exponent': row['wkb_exponent'] *= -1
    elif fault == 'zero_action_changed': row['action_J_s'] = 5e-324
    elif fault == 'unit_transmission_changed': row['transmission'] = 1.
    elif fault == 'bool': row['action_J_s'] = True
    else: row['action_J_s'] = math.nan
    with pytest.raises(ValueError): BarrierEvaluationResult.from_dict(raw)


def test_review_is_source_pinned_and_controls_meet_predeclared_limits():
    root = Path(__file__).resolve().parents[1]
    review = json.loads((root/'docs/barrier_kernel_review.json').read_text(encoding='utf-8'))
    for path, digest in review['source_sha256'].items():
        assert hashlib.sha256((root/path).read_text(encoding='utf-8').encode()).hexdigest() == digest
    controls = review['analytic_controls'] + review['quadrature_controls']
    assert len(controls) == 22
    for row in controls:
        spec = BarrierEvaluationSpec.from_dict(row['request'])
        actual = evaluate_barrier_profile(spec).summary['wkb_exponent']
        reference = row['reference_exponent']
        assert abs(actual-reference) <= 1e-12+1e-10*abs(reference)
        assert row['passed'] and row['absolute_error'] <= row['acceptance_limit']


def test_reference_preserves_negative_outcome_without_experimental_claim():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('s2_reference', root/'examples/phase_s2_barrier_reference.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    raw = module.build_reference()
    assert len(raw['cases']) == 6 and raw['experimental_qualification'] is False
    assert raw['cases']['numeric_failure']['summary']['status'] == 'failed'
    assert raw['cases']['transmission_underflow']['summary']['attenuation_status'] == 'transmission_underflow'
    for result in raw['cases'].values():
        assert BarrierEvaluationResult.from_dict(result).to_dict() == result
