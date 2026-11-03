# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Controlled multilayer action references; no interface matching or device execution."""
from __future__ import annotations
import argparse
from decimal import Decimal, localcontext
import json
import math
from pathlib import Path
from ncmemsim.barrier_contracts import (
    BarrierProvenance, BarrierSegment, BarrierProfile, BarrierEvaluationSpec,
    barrier_energy_eV_to_J,
)
from ncmemsim.barrier_evaluation import evaluate_barrier_profile
from ncmemsim.constants import ELECTRON_MASS_KG, HBAR_J_S
from ncmemsim.tunneling import TunnelingConfig, TunnelingEngine
from ncmemsim.transport import tat

ATOL, RTOL, INVARIANT_RTOL = 1e-12, 1e-10, 5e-13
GRIDS = (80, 160, 320, 640, 1280, 2560)


def make_request(label, segments, incident=0.):
    provenance = BarrierProvenance('assumed', 'synthetic S3 numerical study',
        'no measured coefficient', 'isolated electron action only',
        'no interface matching, current supply or experimental qualification')
    rows = [BarrierSegment(str(i), *values, provenance) for i, values in enumerate(segments)]
    profile = BarrierProfile(label, rows, incident, 'one common electron energy zero',
        'left physical boundary', 'left to right', 'along_positive_axis',
        'left contact', 'right contact', 'controlled numerical study',
        'action-only compact approximation, not a device prediction')
    return BarrierEvaluationSpec(profile, ATOL, RTOL, 'predeclared S1 controls')


def decimal_reference(request, electron_mass_kg=ELECTRON_MASS_KG, hbar_J_s=HBAR_J_S):
    """Independent high-precision primitive, not the S2 rationalized algorithm."""
    raw = request.to_dict()['profile']
    with localcontext() as context:
        context.prec = 100
        d = Decimal; total = d(0)
        for row in raw['segments']:
            a = d(row['start_potential_energy_J']) - d(raw['incident_energy_J'])
            b = d(row['end_potential_energy_J']) - d(raw['incident_energy_J'])
            pa, pb = max(a, d(0)), max(b, d(0))
            mean = pa.sqrt() if a == b else d(2)/3*(pb*pb.sqrt()-pa*pa.sqrt())/(b-a)
            total += d(row['length_m'])*(2*d(electron_mass_kg)*d(row['effective_mass_m0'])).sqrt()*mean
        exponent = float(2*total/d(hbar_J_s)); action = float(total)
        if not math.isfinite(exponent) or not math.isfinite(action):
            return dict(status='unavailable', action_J_s=None, wkb_exponent=None,
                        reason='reference_outside_finite_output_range')
        return dict(status='available', action_J_s=action, wkb_exponent=exponent, reason=None)


def comparison(candidate, reference, rtol=RTOL):
    if candidate is None or reference is None:
        return dict(status='unavailable', absolute_error=None, acceptance_limit=None)
    error = abs(candidate-reference); limit = ATOL+rtol*abs(reference)
    return dict(status='matched' if error <= limit else 'mismatched',
                absolute_error=error, acceptance_limit=limit)


def _with_profile(request, raw):
    return BarrierEvaluationSpec(BarrierProfile.from_dict(raw), ATOL, RTOL,
                                 request.to_dict()['reference_scope'])


def split_request(request, parts):
    """Interpolate only within original segments; never smooth an interface jump."""
    if type(parts) is not int or parts < 1:
        raise ValueError('positive integer subdivision count required')
    profile = request.to_dict()['profile']; rows = []
    for source in profile['segments']:
        for index in range(parts):
            row = dict(source); row['segment_id'] = source['segment_id']+'/'+str(index)
            row['length_m'] = source['length_m']/parts
            start, end = source['start_potential_energy_J'], source['end_potential_energy_J']
            row['start_potential_energy_J'] = start if index == 0 else start+(end-start)*(index/parts)
            row['end_potential_energy_J'] = end if index+1 == parts else start+(end-start)*((index+1)/parts)
            rows.append(row)
    profile['segments'] = rows
    return _with_profile(request, profile)


def controlled_profiles():
    return {
        'homogeneous_linear': make_request('homogeneous-linear', [(5e-9, 3e-19, 1e-19, .2)]),
        'mass_step': make_request('mass-step', [(2e-9, 3e-19, 2e-19, .2), (3e-9, 2e-19, 1e-19, .5)]),
        'energy_step': make_request('energy-step', [(2e-9, 3e-19, 2e-19, .2), (3e-9, 5e-19, 1e-19, .2)]),
        'allowed_interval': make_request('allowed-interval', [(2e-9, 3e-19, -1e-19, .2),
            (1e-9, -1e-19, -1e-19, .3), (2e-9, -1e-19, 2e-19, .4)]),
        'zero_action': make_request('zero-action', [(2e-9, -2e-19, 0., .2), (3e-9, -1e-19, -1e-19, .5)]),
        'underflow': make_request('underflow', [(5e-6, 3e-19, 3e-19, .2), (5e-6, 3e-19, 3e-19, .3)]),
        'partial_numeric_failure': make_request('partial-failure', [(1e300, 1., 1., .2), (2e-9, 3e-19, 1e-19, .3)]),
    }


def invariant_study(profiles):
    rows = []
    for label, source in profiles.items():
        baseline = evaluate_barrier_profile(source).summary['wkb_exponent']
        if baseline is None:
            rows.append(dict(source=label, operation='not_assessed_failed_baseline',
                factor=None, request_hash=source.contract_hash, candidate_exponent=None,
                reference_exponent=None, **comparison(None, None, INVARIANT_RTOL)))
            continue
        candidates = []
        for count in (2, 3, 7, 16):
            candidates.append(('split_each_original_segment', count, split_request(source, count), baseline))
        raw = source.to_dict()['profile']
        reversed_profile = BarrierProfile.from_dict(raw).reversed()
        candidates.append(('same_energy_reversal', None,
            BarrierEvaluationSpec(reversed_profile, ATOL, RTOL, 'same-energy reversal'), baseline))
        for factor in (.25, 4.):
            shifted = source.to_dict()['profile']
            for item in shifted['segments']: item['effective_mass_m0'] *= factor
            candidates.append(('uniform_mass_scaling', factor, _with_profile(source, shifted), baseline*math.sqrt(factor)))
        shifted = source.to_dict()['profile']; offset = 1e-19
        shifted['incident_energy_J'] += offset
        shifted['energy_reference'] = 'common zero shifted by declared 1e-19 J offset'
        for item in shifted['segments']:
            item['start_potential_energy_J'] += offset; item['end_potential_energy_J'] += offset
        candidates.append(('common_energy_zero_shift', offset, _with_profile(source, shifted), baseline))
        for operation, factor, candidate, reference in candidates:
            observed = evaluate_barrier_profile(candidate).summary['wkb_exponent']
            rows.append(dict(source=label, operation=operation, factor=factor,
                request_hash=candidate.contract_hash, candidate_exponent=observed,
                reference_exponent=reference, **comparison(observed, reference, INVARIANT_RTOL)))
    return rows


def published_kernel_study():
    rows = []
    controls = [('rectangle', 5e-9, 0.), ('trapezoid', 5e-9, 1e8),
        ('turning_point', 5e-9, 1e9), ('ascending_linear', 5e-9, -1e8),
        ('near_flat', 5e-9, 1.78e-12/5e-9), ('legacy_floor', 1e-5, 0.)]
    phi, incident, mass = 1.78, .10, .15
    for label, length, field in controls:
        request = make_request(label, [(length, barrier_energy_eV_to_J(phi),
            barrier_energy_eV_to_J(phi-field*length), mass)], barrier_energy_eV_to_J(incident))
        modern = evaluate_barrier_profile(request).summary
        reference = decimal_reference(request)['wkb_exponent']
        endpoint = request.to_dict()['profile']['segments'][0]
        energy = request.to_dict()['profile']['incident_energy_J']
        start, end = endpoint['start_potential_energy_J']-energy, endpoint['end_potential_energy_J']-energy
        t_tat, b_tat = tat.linear_wkb_transmission(length, start, end, mass)
        own_reference = decimal_reference(request, tat.ELECTRON_MASS_KG, tat.REDUCED_PLANCK_J_S)['wkb_exponent']
        samples = []
        for count in GRIDS:
            engine = TunnelingEngine(TunnelingConfig(integration_points=count))
            transmission = engine.trapezoidal_wkb(length, field, phi, incident, mass)
            inferred = -math.log(transmission)
            floor_limited = reference > 700. and inferred >= 700.-1e-10
            samples.append(dict(integration_points=count, transmission=transmission,
                effective_exponent_from_transmission=inferred, floor_limited=floor_limited,
                comparison=({'status':'floor_limited', 'absolute_error':None, 'acceptance_limit':None}
                    if floor_limited else comparison(inferred, reference))))
        rows.append(dict(label=label, inputs=dict(length_m=length, field_V_m=field,
                barrier_eV=phi, injection_energy_eV=incident, effective_mass_m0=mass),
            request=request.to_dict(), modern_summary=modern, decimal_reference_exponent=reference,
            modern_comparison=comparison(modern['wkb_exponent'], reference),
            direct_constants=dict(electron_mass_kg=ELECTRON_MASS_KG, hbar_J_s=HBAR_J_S),
            direct_grid_refinements=samples,
            tat=dict(electron_mass_kg=tat.ELECTRON_MASS_KG, hbar_J_s=tat.REDUCED_PLANCK_J_S,
                transmission=t_tat, exponent=b_tat, own_constant_reference_exponent=own_reference,
                expected_mass_constant_exponent_ratio=math.sqrt(tat.ELECTRON_MASS_KG/ELECTRON_MASS_KG)*HBAR_J_S/tat.REDUCED_PLANCK_J_S,
                raw_difference_from_modern=b_tat-modern['wkb_exponent'],
                own_constant_comparison=comparison(b_tat, own_reference))))
    return rows


def smooth_profile_study():
    length, height, mass, curvature = 5e-9, 2e-19, .2, 3.
    with localcontext() as context:
        context.prec = 100; d = Decimal
        c = d(curvature); root = c.sqrt()
        mean = ((1+c).sqrt()+(root+(1+c).sqrt()).ln()/root)/2
        reference = float(2*d(length)*(2*d(ELECTRON_MASS_KG)*d(mass)*d(height)).sqrt()*mean/d(HBAR_J_S))
    levels = []
    for count in (1, 2, 4, 8, 16, 32, 64):
        segments = [(length/count, height*(1+curvature*(i/count)**2),
            height*(1+curvature*((i+1)/count)**2), mass) for i in range(count)]
        request = make_request('sampled-quadratic-'+str(count), segments)
        exponent = evaluate_barrier_profile(request).summary['wkb_exponent']
        linear_reference = decimal_reference(request)['wkb_exponent']
        levels.append(dict(segment_count=count, request_hash=request.contract_hash,
            observed_exponent=exponent, absolute_error=abs(exponent-reference),
            piecewise_linear_decimal_reference_exponent=linear_reference,
            piecewise_linear_comparison=comparison(exponent, linear_reference),
            comparison_to_smooth_reference=comparison(exponent, reference)))
    return dict(law='U(s)-E = height_J * (1 + curvature * (s/length_m)^2)',
        length_m=length, height_J=height, effective_mass_m0=mass, curvature=curvature,
        reference_method='100-digit Decimal quadratic integral with logarithmic/asinh primitive',
        reference_exponent=reference, levels=levels,
        refinement_observed=levels[-1]['absolute_error'] < levels[0]['absolute_error'],
        last_level_meets_s1_tolerance=levels[-1]['comparison_to_smooth_reference']['status']=='matched',
        meaning='Profile approximation error, not an error in integrating each linear segment.')


def build_reference():
    sources = controlled_profiles(); profiles = {}
    for label, request in sources.items():
        result = evaluate_barrier_profile(request); reference = decimal_reference(request)
        profiles[label] = dict(request=request.to_dict(), result=result.to_dict(),
            decimal_reference=reference,
            comparison=comparison(result.summary['wkb_exponent'], reference['wkb_exponent']))
    invariants = invariant_study(sources); published = published_kernel_study(); smooth = smooth_profile_study()
    return dict(schema_version='phase-s3-multilayer-reference-v1',
        evidence_kind='synthetic_numerical_study',
        tolerances=dict(exponent_atol=ATOL, exponent_rtol=RTOL, invariant_rtol=INVARIANT_RTOL),
        profiles=profiles, invariants=invariants, published_kernel_comparisons=published,
        smooth_profile_refinement=smooth,
        summary=dict(profile_count=len(profiles), completed_profiles=sum(v['result']['summary']['status']=='completed' for v in profiles.values()),
            failed_profiles=sum(v['result']['summary']['status']=='failed' for v in profiles.values()),
            invariant_counts={status:sum(row['status']==status for row in invariants) for status in ('matched','mismatched','unavailable')},
            published_tat_numeric_mismatches=[row['label'] for row in published if row['tat']['own_constant_comparison']['status']=='mismatched'],
            legacy_floor_cases=[row['label'] for row in published if any(x['floor_limited'] for x in row['direct_grid_refinements'])],
            published_kernel_equivalence_claim=False, experimental_qualification=False),
        simulator_attachment=False, experimental_qualification=False,
        limitations=['All material values are assumed synthetic controls.',
            'Action sums do not model coherent interface matching or well resonances.',
            'Reversal is at the same incident energy; it is not reverse-bias current.',
            'Published kernels and their constants are unchanged; mismatches remain evidence.',
            'Refining a sampled nonlinear profile changes its approximation, unlike splitting an existing linear segment.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(); text = json.dumps(build_reference(), indent=2, allow_nan=False)+'\n'
    if args.output is None: print(text, end='')
    else:
        with args.output.open('x', encoding='utf-8', newline='\n') as stream: stream.write(text)


if __name__ == '__main__': main()
