# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Independent scaling, domain boundaries and complete sensitivity accounting."""
import importlib.util
import math
from pathlib import Path
import pytest
from ncmemsim.barrier_evaluation import BarrierEvaluationResult

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('s5', ROOT/'examples/phase_s5_barrier_sensitivity.py')
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


@pytest.fixture(scope='module')
def report():
    return study.build_reference()


@pytest.mark.parametrize('axis', list(study.AXES))
def test_one_factor_changes_only_selected_parameter(report, axis):
    for row in report['sweeps'][axis]:
        assert {k: v for k, v in row['parameters'].items() if k != axis} == {
            k: v for k, v in study.BASE.items() if k != axis}
        assert row['comparison'] == 'matched'


@pytest.mark.parametrize('axis,power', [('length_m', 1.), ('mass_m0', .5)])
def test_analytic_scaling(report, axis, power):
    base = report['baseline']['result']['summary']['wkb_exponent']
    for row in report['sweeps'][axis]:
        expected = base*(row['parameters'][axis]/study.BASE[axis])**power
        assert row['result']['summary']['wkb_exponent'] == pytest.approx(expected, rel=5e-13, abs=1e-12)


@pytest.mark.parametrize('axis,direction', [('length_m', 1), ('potential_eV', 1),
                                         ('mass_m0', 1), ('incident_eV', -1)])
def test_monotonic_action_and_opposite_transmission(report, axis, direction):
    values = [row['result']['summary'] for row in report['sweeps'][axis]]
    assert all(direction*(b['wkb_exponent']-a['wkb_exponent']) >= 0 for a, b in zip(values, values[1:]))
    assert all(direction*(b['transmission']-a['transmission']) <= 0 for a, b in zip(values, values[1:]))


def test_threshold_and_above_barrier_are_explicit_zero_action(report):
    for row in report['sweeps']['incident_eV'][-2:]:
        assert row['result']['summary']['wkb_exponent'] == 0
        assert row['result']['summary']['transmission'] == 1
        assert row['result']['summary']['attenuation_status'] == 'zero_forbidden_action'


def test_joint_design_matches_independent_decimal_reference(report):
    assert len(report['design']) == 9
    for row in report['design']:
        assert row['comparison'] == 'matched'
        assert row['absolute_error'] <= row['acceptance_limit']


def test_splitting_same_profile_is_not_new_physical_evidence(report):
    base = report['baseline']['result']['summary']['wkb_exponent']
    for row in report['subdivision_controls']:
        assert row['comparison'] == 'matched'
        assert row['result']['summary']['wkb_exponent'] == pytest.approx(base, rel=5e-13, abs=1e-12)
    assert not report['model_uncertainty_estimated']
    assert not report['experimental_qualification']


def test_underflow_and_failure_are_separate_retained_outcomes(report):
    underflow, failure = report['controls']
    assert underflow['result']['summary']['status'] == 'completed'
    assert underflow['result']['summary']['transmission'] == 0
    assert math.isfinite(underflow['result']['summary']['log_transmission'])
    assert underflow['comparison'] == 'matched'
    assert failure['result']['summary']['status'] == 'failed'
    assert failure['result']['summary']['transmission'] is None
    assert failure['comparison'] == 'unavailable'
    assert failure['reference_exponent'] is None
    assert report['counts'] == dict(attempted=31, completed=30, failed=1,
                                   matched=30, mismatched=0, unavailable=1)


def test_all_original_source_results_restore(report):
    rows = [report['baseline']]+report['design']+report['controls']+report['subdivision_controls']
    rows += [row for group in report['sweeps'].values() for row in group]
    for row in rows:
        assert BarrierEvaluationResult.from_dict(row['result']).to_dict() == row['result']


@pytest.mark.parametrize('parts', [0, -1, True, 1.5])
def test_bad_subdivision_rejected(parts):
    with pytest.raises(ValueError):
        study.request(study.BASE, parts)
