# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Multilayer references distinguish action accuracy, model conventions and grid error."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import pytest
from scipy.integrate import quad
from ncmemsim.barrier_contracts import BarrierProfile, BarrierEvaluationSpec
from ncmemsim.barrier_evaluation import BarrierEvaluationResult, evaluate_barrier_profile
from ncmemsim.constants import ELECTRON_MASS_KG, HBAR_J_S

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('s3_reference', ROOT/'examples/phase_s3_multilayer_reference.py')
study = importlib.util.module_from_spec(spec); spec.loader.exec_module(study)


@pytest.fixture(scope='module')
def report():
    return study.build_reference()


@pytest.mark.parametrize('name', ['homogeneous_linear', 'mass_step', 'energy_step',
    'allowed_interval', 'zero_action', 'underflow'])
def test_independent_multilayer_references(report, name):
    case = report['profiles'][name]
    assert case['result']['summary']['status'] == 'completed'
    assert case['comparison']['status'] == 'matched'
    assert BarrierEvaluationResult.from_dict(case['result']).to_dict() == case['result']
    assert not case['result']['interface_matching']


def test_mass_and_energy_steps_are_independent_controls(report):
    mass = report['profiles']['mass_step']['request']['profile']['segments']
    energy = report['profiles']['energy_step']['request']['profile']['segments']
    assert mass[0]['end_potential_energy_J'] == mass[1]['start_potential_energy_J']
    assert mass[0]['effective_mass_m0'] != mass[1]['effective_mass_m0']
    assert energy[0]['end_potential_energy_J'] != energy[1]['start_potential_energy_J']
    assert energy[0]['effective_mass_m0'] == energy[1]['effective_mass_m0']


def test_allowed_interval_does_not_become_resonance_model(report):
    case = report['profiles']['allowed_interval']['result']
    assert case['segments'][1]['domain'] == 'no_forbidden_region'
    assert case['segments'][1]['wkb_exponent'] == 0.
    assert case['summary']['wkb_exponent'] == math.fsum(x['wkb_exponent'] for x in case['segments'])
    assert not report['summary']['published_kernel_equivalence_claim']


@pytest.mark.parametrize('label', ['homogeneous_linear', 'mass_step', 'energy_step',
    'allowed_interval', 'zero_action', 'underflow'])
@pytest.mark.parametrize('parts', [2, 3, 7, 16])
def test_segment_splitting_retains_action_and_interfaces(label, parts):
    source = study.controlled_profiles()[label]
    split = study.split_request(source, parts)
    original = source.to_dict()['profile']['segments']; divided = split.to_dict()['profile']['segments']
    assert len(divided) == len(original)*parts
    for i, row in enumerate(original):
        group = divided[i*parts:(i+1)*parts]
        assert group[0]['start_potential_energy_J'] == row['start_potential_energy_J']
        assert group[-1]['end_potential_energy_J'] == row['end_potential_energy_J']
        assert math.fsum(x['length_m'] for x in group) == pytest.approx(row['length_m'], rel=2e-15, abs=0)
        assert all(x['effective_mass_m0'] == row['effective_mass_m0'] for x in group)
        assert all(x['end_potential_energy_J'] == y['start_potential_energy_J'] for x, y in zip(group, group[1:]))
    expected = evaluate_barrier_profile(source).summary['wkb_exponent']
    observed = evaluate_barrier_profile(split).summary['wkb_exponent']
    assert study.comparison(observed, expected, study.INVARIANT_RTOL)['status'] == 'matched'


@pytest.mark.parametrize('parts', [0, -1, True, 1.5, '2'])
def test_invalid_subdivision_declaration(parts):
    with pytest.raises(ValueError): study.split_request(study.controlled_profiles()['mass_step'], parts)


def test_all_invariants_and_failed_baseline_accounting(report):
    assert report['summary']['invariant_counts'] == {'matched':48, 'mismatched':0, 'unavailable':1}
    missing = [row for row in report['invariants'] if row['status']=='unavailable']
    assert missing[0]['source'] == 'partial_numeric_failure'
    failed = report['profiles']['partial_numeric_failure']
    assert failed['result']['summary']['failed_segment_count'] == 1
    assert failed['result']['summary']['completed_segment_count'] == 1
    assert failed['decimal_reference']['status'] == 'unavailable'
    assert failed['comparison']['status'] == 'unavailable'


@pytest.mark.parametrize('label', ['mass_step', 'energy_step', 'allowed_interval', 'underflow'])
def test_reversal_is_same_landscape_and_energy(label):
    source = study.controlled_profiles()[label]
    original = BarrierProfile.from_dict(source.to_dict()['profile'])
    reverse = original.reversed()
    assert reverse.reversed().to_json() == original.to_json()
    request = BarrierEvaluationSpec(reverse, study.ATOL, study.RTOL, 'same-energy control')
    expected = evaluate_barrier_profile(source).summary['wkb_exponent']
    observed = evaluate_barrier_profile(request).summary['wkb_exponent']
    assert study.comparison(observed, expected, study.INVARIANT_RTOL)['status']=='matched'


@pytest.mark.parametrize('label', ['rectangle', 'trapezoid', 'turning_point', 'ascending_linear', 'near_flat', 'legacy_floor'])
def test_both_published_kernels_use_explicit_matching_inputs(report, label):
    row = next(x for x in report['published_kernel_comparisons'] if x['label']==label)
    assert row['modern_comparison']['status']=='matched'
    assert [r['integration_points'] for r in row['direct_grid_refinements']] == list(study.GRIDS)
    assert 160 in study.GRIDS
    assert row['tat']['electron_mass_kg'] != row['direct_constants']['electron_mass_kg']
    own_ref = study.decimal_reference(BarrierEvaluationSpec.from_dict(row['request']),
        row['tat']['electron_mass_kg'], row['tat']['hbar_J_s'])['wkb_exponent']
    assert own_ref == row['tat']['own_constant_reference_exponent']
    predicted_ratio = math.sqrt(row['tat']['electron_mass_kg']/row['direct_constants']['electron_mass_kg'])
    assert row['tat']['expected_mass_constant_exponent_ratio'] == predicted_ratio


def test_published_negative_evidence_is_retained(report):
    near_flat = next(x for x in report['published_kernel_comparisons'] if x['label']=='near_flat')
    assert near_flat['tat']['own_constant_comparison']['status']=='mismatched'
    assert near_flat['tat']['own_constant_comparison']['absolute_error'] > near_flat['tat']['own_constant_comparison']['acceptance_limit']
    assert report['summary']['published_tat_numeric_mismatches'] == ['near_flat']
    floor = next(x for x in report['published_kernel_comparisons'] if x['label']=='legacy_floor')
    assert floor['modern_summary']['transmission']==0.
    assert all(x['transmission']>0 and x['comparison']['status']=='floor_limited' for x in floor['direct_grid_refinements'])


@pytest.mark.parametrize('label', ['trapezoid', 'turning_point', 'ascending_linear'])
def test_legacy_grid_refinement_is_observed_without_tolerance_redefinition(report, label):
    row = next(x for x in report['published_kernel_comparisons'] if x['label']==label)
    samples = row['direct_grid_refinements']
    assert samples[-1]['comparison']['absolute_error'] < samples[0]['comparison']['absolute_error']
    for sample in samples:
        comparison = study.comparison(sample['effective_exponent_from_transmission'], row['decimal_reference_exponent'])
        assert sample['comparison'] == comparison


def test_smooth_profile_refinement_is_separate_from_segment_integration(report):
    smooth = report['smooth_profile_refinement']
    assert smooth['refinement_observed']
    levels = smooth['levels']
    assert all(row['piecewise_linear_comparison']['status']=='matched' for row in levels)
    assert all(right['absolute_error'] < left['absolute_error'] for left, right in zip(levels, levels[1:]))
    assert smooth['last_level_meets_s1_tolerance'] is False
    assert levels[-1]['comparison_to_smooth_reference']['status']=='mismatched'
    integral, error = quad(lambda x: math.sqrt(1+smooth['curvature']*x*x), 0., 1., epsabs=1e-12, epsrel=1e-12)
    independent = 2*smooth['length_m']*math.sqrt(2*ELECTRON_MASS_KG*smooth['effective_mass_m0']*smooth['height_J'])/HBAR_J_S*integral
    assert study.comparison(independent, smooth['reference_exponent'])['status']=='matched'


def test_study_never_runs_device_dynamics(monkeypatch):
    from ncmemsim.simulator import Simulator
    def forbidden(*args, **kwargs): raise AssertionError('S3 is an isolated reference study')
    monkeypatch.setattr(Simulator, 'relax_voltage', forbidden)
    raw = study.build_reference()
    assert not raw['simulator_attachment'] and not raw['experimental_qualification']
    json.dumps(raw, allow_nan=False)


def test_review_is_source_pinned_and_preserves_negative_evidence():
    review = json.loads((ROOT/'docs/barrier_multilayer_review.json').read_text(encoding='utf-8'))
    for path, digest in review['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_text(encoding='utf-8').encode()).hexdigest()==digest
    raw = review['study']
    assert raw['summary']['failed_profiles']==1
    assert raw['summary']['invariant_counts']['unavailable']==1
    assert raw['summary']['published_tat_numeric_mismatches']==['near_flat']
    # Historical observations may differ by roundoff across hosts. Reassess
    # numeric comparisons; do not require byte-identical host math outputs.
    for case in raw['profiles'].values():
        current = evaluate_barrier_profile(BarrierEvaluationSpec.from_dict(case['request']))
        reference = case['decimal_reference']['wkb_exponent']
        assert study.comparison(current.summary['wkb_exponent'], reference)['status']==case['comparison']['status']


def test_study_does_not_loosen_predeclared_s1_tolerances():
    review = json.loads((ROOT/'docs/barrier_parameters_review.json').read_text(encoding='utf-8'))
    controls = review['numerical_acceptance']['analytic_controls']
    invariants = review['numerical_acceptance']['splitting_reversal_controls']
    assert study.ATOL == controls['atol'] == invariants['atol'] == 1e-12
    assert study.RTOL == controls['rtol'] == 1e-10
    assert study.INVARIANT_RTOL == invariants['rtol'] == 5e-13
