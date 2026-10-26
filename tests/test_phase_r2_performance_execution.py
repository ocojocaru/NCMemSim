# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""R2 process isolation, budgets, complete denominators and scientific baselines."""
import copy
import json
from pathlib import Path
import subprocess

import pytest

from ncmemsim import DeviceBuilder
from ncmemsim.temperature_context import ThermalContext
from ncmemsim.performance_contracts import PerformanceWorkload, MeasurementProtocol, PerformanceTrial
import ncmemsim.performance_execution as execution
from ncmemsim.performance_workloads import execute_performance_workload, _snapshot


@pytest.fixture
def workload():
    return PerformanceWorkload('test-relaxation', 'relaxation', {'case': 'trajectory', 'payload': {
        'context': ThermalContext.from_nominal(DeviceBuilder.v2(1)).to_dict(), 'temperature_K': 300.,
        'settings': {'voltage_V': 2., 'duration_s': 2e-8, 'dt_s': 1e-8, 'initial_p1': [.2]}}},
        ('end_to_end',), 'state_chain', 1, 'Synthetic test trajectory with full scientific output')


@pytest.fixture
def protocol():
    return MeasurementProtocol(isolation='fresh_process', max_trial_seconds=30., max_total_seconds=180.)


def campaign(workload, protocol, **kwargs):
    return execution.run_serial_campaign(workload, protocol, source_commit='a'*40, source_dirty=True, **kwargs)


def fake_response(result):
    return {'environment': {}, 'source_tree_hash': '', 'status': 'completed', 'result': copy.deepcopy(result),
            'elapsed_seconds': .25, 'memory_bytes': None, 'memory_method': None, 'failure': None}


def test_fresh_process_full_payload_repeatability(workload, protocol):
    before = workload.to_json()
    result = campaign(workload, protocol)
    assert result['summary']['complete']
    assert result['summary']['equivalent_measurement_count'] == 5
    assert len(result['trials']) == 6
    assert result['reference']['origin'] == 'separate_serial_execution'
    assert result['environment']['source_commit'] == 'a'*40
    assert Path(result['environment']['imported_package_path']).is_absolute()
    assert result['source_tree_hash'] == execution._source_digest()
    assert result['summary']['complete_equivalent_statistics']['count'] == 5
    for row in result['trials']:
        assert row['comparison']['status'] == 'equivalent'
        assert row['lifecycle_seconds'] >= row['trial']['elapsed_seconds'] >= 0
        assert PerformanceTrial.from_dict(row['trial']).to_dict() == row['trial']
        scientific = row['result']['scientific_result']
        assert scientific['output']['state']['floating_gates'][0]['P0']
        assert scientific['output']['transport_network']['links']
        assert scientific['max_probability_mass_error'] < 1e-12
    assert workload.to_json() == before
    assert not result['summary']['speedup_accepted']


def test_separate_native_memory_protocol(workload):
    protocol = MeasurementProtocol(isolation='fresh_process', instrumentation='native_memory',
        max_trial_seconds=30., max_total_seconds=180.)
    result = campaign(workload, protocol)
    import sys
    if sys.platform in ('win32', 'darwin') or sys.platform.startswith('linux'):
        assert result['summary']['complete'], result['reference']['failure']
    elif not result['summary']['complete']:
        assert result['reference']['failure'] is not None
        return  # unsupported OS remains a retained failure, never invented RAM
    for row in result['trials']:
        trial = row['trial']
        assert trial['memory_kind'] == 'process_peak_rss'
        assert trial['memory_bytes'] > 0 and 'whole fresh process' in trial['memory_method']
        assert not trial['uninstrumented_measurement']


def test_timeout_retains_every_declared_index(monkeypatch, workload, protocol):
    def timeout(*args):
        raise subprocess.TimeoutExpired('worker', .01)
    monkeypatch.setattr(execution, '_invoke', timeout)
    result = campaign(workload, protocol)
    assert result['reference']['failure']['type'] == 'TimeoutExpired'
    assert [(x['trial']['phase'], x['trial']['index']) for x in result['trials']] == [
        ('warmup', 0), *[('measurement', i) for i in range(5)]]
    assert result['summary']['failed_measurement_count'] == 5
    assert result['summary']['complete_equivalent_statistics'] is None
    assert all(x['trial']['result_hash'] is None for x in result['trials'])


def test_total_budget_marks_unstarted_trials_unavailable(monkeypatch, workload, protocol):
    ticks = iter([0., 0., 1000.] + [1001.] * 100)
    monkeypatch.setattr(execution._time, 'monotonic', lambda: next(ticks))
    calls = []
    def worker(*args):
        calls.append(args)
        return fake_response({'state': [1., 0.], 'source': 'reference'})
    monkeypatch.setattr(execution, '_invoke', worker)
    result = campaign(workload, protocol)
    assert len(calls) == 1  # reference launched while budget existed
    assert result['summary']['unavailable_measurement_count'] == 5
    assert all(x['trial']['failure']['stage'] == 'campaign_budget' for x in result['trials'])
    assert not result['summary']['complete']


def test_changed_science_is_retained_not_averaged_away(monkeypatch, workload, protocol):
    results = iter([{'source': 'fixed', 'state': [1., 0.]}] * 3 +
                   [{'source': 'fixed', 'state': [.9, .1]}] +
                   [{'source': 'fixed', 'state': [1., 0.]}] * 3)
    monkeypatch.setattr(execution, '_invoke', lambda *args: fake_response(next(results)))
    result = campaign(workload, protocol)
    assert result['summary']['completed_measurement_count'] == 5
    assert result['summary']['equivalent_measurement_count'] == 4
    assert result['summary']['completed_observation_statistics']['count'] == 5
    assert result['summary']['complete_equivalent_statistics'] is None
    assert result['trials'][2]['comparison']['status'] == 'not_equivalent'
    assert result['trials'][2]['result']['state'] == [.9, .1]


def test_worker_failure_preserves_partial_scientific_result(monkeypatch, workload, protocol):
    def fail(*args):
        result = fake_response({'state': [1., 0.]})
        result['status'] = 'failed'
        result['failure'] = {'stage': 'serialization', 'type': 'ValueError', 'message': 'synthetic failure'}
        return result
    monkeypatch.setattr(execution, '_invoke', fail)
    result = campaign(workload, protocol)
    assert not result['summary']['complete']
    assert result['trials'][0]['result'] == {'state': [1., 0.]}
    assert result['trials'][0]['trial']['result_hash'] is not None


def test_caller_reference_binding_and_ownership(monkeypatch, workload, protocol):
    from ncmemsim.performance_contracts import EquivalenceContract, EquivalenceRule
    reference = {'source': 'fixed', 'value': 1.}
    rules = EquivalenceContract(workload.contract_hash,
        (EquivalenceRule('/value', 'synthetic scalar', '1', .01, 0),), ('/source',), 'Synthetic test tolerance')
    monkeypatch.setattr(execution, '_invoke', lambda *args: fake_response({'source': 'fixed', 'value': 1.001}))
    result = campaign(workload, protocol, reference=reference, equivalence=rules)
    reference['source'] = 'caller mutation'
    assert result['summary']['complete']
    assert result['reference']['result']['source'] == 'fixed'
    assert result['reference']['origin'] == 'caller_supplied'
    assert result['reference']['lifecycle_seconds'] is None


def test_invalid_reference_or_isolation(workload, protocol):
    with pytest.raises(ValueError):
        campaign(workload, MeasurementProtocol())
    with pytest.raises(ValueError):
        campaign(workload, protocol, reference={})


def test_real_short_timeout_and_cleanup(workload, tmp_path, monkeypatch):
    monkeypatch.setattr(execution._tempfile, 'tempdir', str(tmp_path))
    result = campaign(workload, MeasurementProtocol(isolation='fresh_process',
        max_trial_seconds=.0001, max_total_seconds=.1))
    assert not result['summary']['complete']
    assert result['reference']['failure'] is not None
    assert not list(tmp_path.iterdir())


def test_snapshot_preserves_unavailable_optics_but_rejects_nan_state():
    import numpy as np
    result = _snapshot({'optical_alpha_nc_by_fg_m_inv': np.array([float('nan')])})
    assert result['optical_alpha_nc_by_fg_m_inv'][0]['meaning'] == 'unavailable optical diagnostic'
    assert _snapshot(float('inf')) == {'nonfinite_number': 'positive_infinity'}
    with pytest.raises(ArithmeticError):
        _snapshot({'P0': [float('nan')]})
    with pytest.raises(ValueError):
        _snapshot(object())


@pytest.fixture(scope='module')
def representative_workloads():
    from scripts.run_performance_baseline import build_workloads
    return {w.to_dict()['workload_id']: w for w in build_workloads()}


def test_suite_covers_required_families(representative_workloads):
    assert len(representative_workloads) == 15
    assert set(w.scientific_inputs['case'] for w in representative_workloads.values()) == {
        'trajectory', 'dtco', 'device_manifest', 'model_manifest', 'sequence', 'optical',
        'thermal', 'retention', 'restore', 'export'}
    assert all(w.to_dict()['scope'] == ['end_to_end'] for w in representative_workloads.values())


@pytest.mark.parametrize('name,successes,failures', [
    ('independent-dtco', 2, 0), ('device-zero', 2, 0), ('device-varied', 1, 1),
    ('model-zero', 2, 0), ('model-varied', 1, 1)])
def test_real_manifest_order_and_negative_outcomes(representative_workloads, name, successes, failures, tmp_path):
    workload = representative_workloads[name]
    before = workload.to_json()
    result = execute_performance_workload(workload, tmp_path/'unused')['scientific_result']
    assert result['success_count'] == successes and result['failure_count'] == failures
    assert len(result['points']) == workload.to_dict()['logical_item_count']
    if failures:
        assert result['points'][1]['status'] == 'failed'
    if 'model' in name:
        first = result['points'][0]['output']
        assert first['max_relative_conservation_error'] < 1e-12
        assert first['steps'] and first['final_state']['floating_gates']
    assert workload.to_json() == before


def test_workload_must_not_relabel_sequence_independent(workload, tmp_path):
    bad = PerformanceWorkload('wrong', 'restore', workload.scientific_inputs, ('end_to_end',),
                              'static_restore', 1, 'mismatch test')
    with pytest.raises(ValueError):
        execute_performance_workload(bad, tmp_path/'unused')


@pytest.mark.parametrize('fault', ['count', 'extra_payload', 'extra_settings', 'too_many_steps', 'boolean_population'])
def test_workload_resource_and_input_guards(workload, tmp_path, fault):
    raw = workload.to_dict()
    inputs = workload.scientific_inputs
    count = 1
    if fault == 'count':
        count = 2
    elif fault == 'extra_payload':
        inputs['payload']['ignored'] = 'must not be ignored'
    elif fault == 'extra_settings':
        inputs['payload']['settings']['ignored'] = 1
    elif fault == 'too_many_steps':
        inputs['payload']['settings']['dt_s'] = 1e-30
    else:
        inputs['payload']['settings']['initial_p1'] = [True]
    altered = PerformanceWorkload('guard', 'relaxation', inputs, ('end_to_end',), 'state_chain', count, 'guard')
    with pytest.raises(ValueError):
        execute_performance_workload(altered, tmp_path/'unused')


def test_unsupported_instrumentation_rejected_before_launch(workload):
    with pytest.raises(ValueError, match='none/native_memory'):
        campaign(workload, MeasurementProtocol(isolation='fresh_process', instrumentation='cprofile'))


def test_worker_identity_mismatch_is_not_accepted(monkeypatch, workload, protocol, tmp_path):
    environment = execution.capture_performance_environment('a'*40, True)
    def run(command, **kwargs):
        raw = fake_response({'state': [1., 0.]})
        raw['environment'] = environment.to_dict()
        raw['environment']['python_version'] = 'wrong-interpreter'
        raw['source_tree_hash'] = execution._source_digest()
        Path(command[-2]).write_text(json.dumps(raw), encoding='utf-8')
    monkeypatch.setattr(execution._subprocess, 'run', run)
    with pytest.raises(ValueError, match='identity'):
        execution._invoke(workload, protocol, environment, 5., tmp_path)


def test_warmup_over_budget_prevents_complete_baseline(monkeypatch, workload, protocol):
    count = 0
    def run(*args):
        nonlocal count
        count += 1
        result = fake_response({'source': 'same', 'state': [1., 0.]})
        if count == 2:
            result['elapsed_seconds'] = 31.
        return result
    monkeypatch.setattr(execution, '_invoke', run)
    result = campaign(workload, protocol)
    assert result['summary']['equivalent_measurement_count'] == 5
    assert result['trials'][0]['trial']['trial_budget_exceeded']
    assert not result['summary']['complete']


def test_stored_manifests_do_not_resample(monkeypatch, representative_workloads, tmp_path):
    import ncmemsim.ensemble.sampling as sampling
    import ncmemsim.ensemble.model_sampling as model_sampling
    def no_draw(*args, **kwargs):
        raise AssertionError('stored execution must not generate a new manifest')
    monkeypatch.setattr(sampling, 'generate_sample_manifest', no_draw)
    monkeypatch.setattr(model_sampling, 'generate_model_sample_manifest', no_draw)
    for name in ('device-zero', 'device-varied', 'model-zero', 'model-varied'):
        result = execute_performance_workload(representative_workloads[name], tmp_path/'unused')
        assert len(result['scientific_result']['points']) == 2
