"""Cross-workflow provenance and retained Phase F/G/H integration contracts."""
from copy import deepcopy
import json
import pytest
pytest.importorskip('scipy')
from examples import phase_i3_electrical_workflow_reference as electrical
from examples import phase_i4_electro_optical_workflow_reference as optical
from ncmemsim.hashing import canonical_hash
from ncmemsim.workflows import AppliedWorkflowEvidence, WorkflowEvidence, WorkflowEvaluator
from ncmemsim.workflows.application import _restore_device, _restore_protocol
from ncmemsim.dtco import (SampleManifest, propagate_samples, analyze_samples,
    MetricDefinition, MetricAnalysisSpec, SampleAnalysisSpec, evaluate_nominal,
    compare_nominal, RobustDTCOReport)


@pytest.fixture(scope='module')
def reports():
    return {name: {mode: module.build_reference_report(include_failures=mode)
        for mode in (False, True)} for name, module in [('electrical', electrical), ('optical', optical)]}


def captured(report):
    return report.to_dict()['analyses'][0]['data']['source']['study']['evaluation']['parameters']['applied_workflow_evidence']


def evaluator(raw):
    evidence = AppliedWorkflowEvidence.from_json(json.dumps(raw))
    return WorkflowEvaluator(evidence, _restore_device(raw['applied_context']['device']), _restore_protocol(raw['operating']))


def rehash(raw):
    raw.pop('evidence_hash', None)
    raw['evidence_hash'] = canonical_hash(raw)
    return json.dumps(raw)


@pytest.mark.parametrize('name', ['electrical', 'optical'])
@pytest.mark.parametrize('change', ['source_swap', 'fitted_target', 'undeclared_config', 'application_swap'])
def test_real_workflow_context_rejects_rehashed_broken_links(reports, name, change):
    raw = deepcopy(captured(reports[name][False]))
    other = captured(reports['optical' if name == 'electrical' else 'electrical'][False])
    if change == 'source_swap':
        raw['workflow_evidence'] = other['workflow_evidence']
    elif change == 'application_swap':
        raw['parameter_application'] = other['parameter_application']
        raw['parameter_application_hash'] = canonical_hash(raw['parameter_application'])
    elif change == 'undeclared_config':
        raw['applied_context']['simulation_config']['internal_dt_s'] *= 2
        raw['context_hash'] = canonical_hash(raw['applied_context'])
    else:
        target = raw['applied_context']['physics']['kinetics'] if name == 'electrical' else raw['applied_context']['photo_config']
        key = 'nu0_Hz' if name == 'electrical' else 'photo_capture_efficiency'
        target[key] *= 1.1
        raw['context_hash'] = canonical_hash(raw['applied_context'])
    with pytest.raises(ValueError):
        AppliedWorkflowEvidence.from_json(rehash(raw))


@pytest.mark.parametrize('name', ['electrical', 'optical'])
def test_real_sources_reject_swapped_held_out_dataset_even_after_rehash(reports, name):
    source = deepcopy(captured(reports[name][False])['workflow_evidence'])
    source['validation_dataset'] = captured(reports['optical' if name == 'electrical' else 'electrical'][False])['workflow_evidence']['validation_dataset']
    with pytest.raises(ValueError):
        WorkflowEvidence.from_json(rehash(source))


@pytest.mark.parametrize('name', ['electrical', 'optical'])
def test_foreign_runtime_archives_restore_without_permitting_execution(reports, name):
    raw = deepcopy(captured(reports[name][False]))
    raw['runtime']['numpy'] = 'foreign-runtime'
    restored = AppliedWorkflowEvidence.from_json(rehash(raw))
    assert restored.to_dict()['runtime']['numpy'] == 'foreign-runtime'
    adapter = WorkflowEvaluator(restored, _restore_device(raw['applied_context']['device']), _restore_protocol(raw['operating']))
    with pytest.raises(ValueError, match='runtime'):
        adapter.evaluate(adapter.base_device, adapter.base_protocol)


@pytest.mark.parametrize('name', ['electrical', 'optical'])
def test_all_failed_and_partial_metric_cases_keep_all_attempted_denominator(reports, name):
    report = reports[name][False].to_dict()
    adapter = evaluator(captured(reports[name][False]))
    manifest = SampleManifest.from_json(json.dumps(report['analyses'][0]['data']['source']['manifest']))
    common = dict(evaluation_id=adapter.evaluation_id, evaluation_parameters=adapter.evaluation_parameters, base_protocol=adapter.base_protocol)
    metrics = SampleAnalysisSpec(MetricAnalysisSpec('i5-complete-responses', (
        MetricDefinition('shift', ('delta_vfb_V',), 'V'),
        MetricDefinition('occupation', ('mean_occupation',), '1'))))
    def incomplete(device, protocol, point):
        # One available metric must not enter complete-case response statistics.
        return {'delta_vfb_V': 0.0}
    result = analyze_samples(propagate_samples(manifest, adapter.base_device, incomplete, **common), metrics)
    data = result.to_dict()
    assert data['counts'] == {'total': 4, 'assessed': 0, 'feasible': 0, 'infeasible': 0, 'failed': 4,
        'extraction_failed': 4, 'propagation_failed': 0}
    assert data['fractions']['observed_feasible_fraction_all_attempted'] == {'value': 0.0, 'numerator': 0, 'denominator': 4}
    assert data['fractions']['conditional_feasible_fraction_assessed'] == {'value': None, 'numerator': 0, 'denominator': 0}
    assert data['fractions']['failure_fraction_all_attempted']['value'] == 1.0
    assert all(p['failure']['stage'] == 'extraction' for p in data['points'])
    assert all(s['sample_indices'] == [] and s['mean'] is None for s in data['metric_statistics'])
    nominal = evaluate_nominal(adapter.base_device, adapter.evaluate, **common)
    comparison = compare_nominal(result, nominal).to_dict()
    assert comparison['nominal_result']['output']['delta_vfb_V'] == adapter.evaluate(adapter.base_device, adapter.base_protocol)['delta_vfb_V']


@pytest.mark.parametrize('name', ['electrical', 'optical'])
@pytest.mark.parametrize('mismatch', ['device', 'evaluation'])
def test_nominal_comparison_rejects_unrelated_device_or_evaluator(reports, name, mismatch):
    adapter = evaluator(captured(reports[name][False]))
    raw = reports[name][False].to_dict()
    manifest = SampleManifest.from_json(json.dumps(raw['analyses'][0]['data']['source']['manifest']))
    common = dict(evaluation_id=adapter.evaluation_id, evaluation_parameters=adapter.evaluation_parameters, base_protocol=adapter.base_protocol)
    source = propagate_samples(manifest, adapter.base_device, adapter.evaluate, **common)
    analysis = analyze_samples(source, SampleAnalysisSpec(MetricAnalysisSpec('i5-shift', (MetricDefinition('shift', ('delta_vfb_V',), 'V'),))))
    candidate = adapter.base_device
    if mismatch == 'device': candidate.temperature_K = 325.0
    else: common['evaluation_id'] += '-unrelated'
    nominal = evaluate_nominal(candidate, adapter.evaluate, **common)
    with pytest.raises(ValueError): compare_nominal(analysis, nominal)


@pytest.mark.parametrize('name', ['electrical', 'optical'])
def test_error_demo_preserves_fit_application_manifest_and_nominal_outputs(reports, name):
    normal, failure = [reports[name][mode].to_dict() for mode in (False, True)]
    assert normal['metadata']['source_workflow_evidence'] == failure['metadata']['source_workflow_evidence']
    assert captured(reports[name][False]) == captured(reports[name][True])
    for i in range(2):
        a, b = [r['analyses'][i]['data'] for r in (normal, failure)]
        assert a['source']['manifest'] == b['source']['manifest']
        assert normal['nominal_comparisons'][i]['data']['nominal_result']['output'] == failure['nominal_comparisons'][i]['data']['nominal_result']['output']
        assert b['counts']['failed'] == 3 and b['counts']['infeasible'] == 0
        assert b['fractions']['failure_fraction_all_attempted']['value'] == .75
        assert all(p['status'] == 'failed' for p in b['points'][1:])


def test_electrical_and_optical_evidence_have_distinct_full_context_identity(reports):
    a, b = [AppliedWorkflowEvidence.from_json(json.dumps(captured(reports[name][False]))) for name in ('electrical', 'optical')]
    assert a.evidence_hash != b.evidence_hash and a.context_hash != b.context_hash
    assert a.to_dict()['applied_context']['photo_config'] is None
    assert b.to_dict()['applied_context']['photo_config'] is not None
    assert a.to_dict()['operating']['kind'] != b.to_dict()['operating']['kind']
    assert a.scientific_status == b.scientific_status == 'FITTED'


def test_all_archives_restore_with_execution_entry_points_disabled(reports, monkeypatch):
    import ncmemsim.workflows.application as app
    def forbidden(*args, **kwargs): pytest.fail('execution during archival restoration')
    for module in (electrical, optical):
        for name in ('build_workflow_sources', 'apply_workflow_parameters', 'propagate_samples'):
            monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(app, 'apply_device_calibration_parameters', forbidden)
    monkeypatch.setattr(app, 'run_program_pulse_read', forbidden)
    monkeypatch.setattr(app, 'run_electro_optical_program_pulse_read', forbidden)
    for pair in reports.values():
        for report in pair.values():
            assert RobustDTCOReport.from_json(report.to_json()).report_hash == report.report_hash
            raw = captured(report)
            applied = AppliedWorkflowEvidence.from_json(json.dumps(raw))
            assert applied.to_dict() == raw
            source = WorkflowEvidence.from_json(json.dumps(raw['workflow_evidence']))
            assert source.qualification_eligible is True and source.scientific_status == 'FITTED'
