"""Electrical synthetic source -> qualification -> actual nominal/sample execution."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import pytest
pytest.importorskip('scipy')
from examples import phase_i3_electrical_workflow_reference as reference
from ncmemsim.workflows import WorkflowEvidence, AppliedWorkflowEvidence, WorkflowEvaluator
from ncmemsim.dtco import RobustDTCOReport, SampleManifest, write_robust_dtco_report


@pytest.fixture(scope='module')
def reports():
    return {mode: reference.build_reference_report(include_failures=mode) for mode in (False, True)}


def application(report, index=0):
    raw = report.to_dict()
    study = raw['analyses'][index]['data']['source']['study']
    return AppliedWorkflowEvidence.from_json(json.dumps(study['evaluation']['parameters']['applied_workflow_evidence']))


def test_actual_parameter_recovery_and_separate_synthetic_qualification(reports):
    raw = reports[False].to_dict()
    evidence = WorkflowEvidence.from_json(json.dumps(raw['metadata']['source_workflow_evidence']))
    source = evidence.to_dict()
    value = source['fit_result']['data']['numerical_result']['fitted_parameters']['nu0_Hz']
    assert value == pytest.approx(reference.TRUE_NU0_HZ, rel=1e-3)
    assert value != 5e11
    assert evidence.qualification_eligible is True
    assert evidence.scientific_status == 'FITTED'
    for key in ('fit_dataset', 'validation_dataset'):
        assert source[key]['origin'] == 'synthetic'
        assert 'no independent' in source[key]['applicability']
    train = source['fit_dataset']['dataset']['independent_variable']['values']
    held = source['validation_dataset']['dataset']['independent_variable']['values']
    assert set(train).isdisjoint(held)
    qualification = source['qualification']['data']
    assert qualification['fit_dataset_hash'] != qualification['validation_dataset_hash']
    assert qualification['criteria']['max_validation_rmse'] == reference.MAX_VALIDATION_RMSE_V
    assert qualification['validation_objective']['root_mean_square_error'] <= reference.MAX_VALIDATION_RMSE_V
    assert source['metadata']['validation_threshold_unit'] == 'V'


def test_source_application_study_and_nominal_links_are_complete(reports):
    raw = reports[False].to_dict()
    metadata = raw['metadata']
    contexts = []
    for index, analysis in enumerate(raw['analyses']):
        a = analysis['data']
        study = a['source']['study']
        applied = application(reports[False], index)
        source = applied.to_dict()
        assert applied.evidence_hash == metadata['applied_workflow_evidence_hash']
        assert source['workflow_evidence'] == metadata['source_workflow_evidence']
        assert source['applied_context']['physics']['kinetics']['nu0_Hz'] == source['parameter_application']['parameter_values']['nu0_Hz']
        assert source['baseline_context']['physics']['kinetics']['nu0_Hz'] == 1e12
        assert study['nominal']['device']['device']['temperature_K'] == metadata['design_temperatures_K'][index]
        comparison = raw['nominal_comparisons'][index]['data']
        assert comparison['source_analysis_hash'] == analysis['result_hash']
        assert comparison['nominal_result']['nominal_hash'] == a['source']['nominal_hash']
        assert comparison['nominal_result']['evaluation'] == study['evaluation']
        assert comparison['status'] == 'assessed'
        contexts.append(study['evaluation'])
    assert contexts[0] == contexts[1]


def test_same_exact_manifest_inputs_order_and_units_for_both_designs(reports):
    raw = reports[False].to_dict()
    sources = [a['data']['source'] for a in raw['analyses']]
    assert sources[0]['manifest'] == sources[1]['manifest']
    restored = SampleManifest.from_json(json.dumps(sources[0]['manifest']))
    assert restored.manifest_hash == raw['metadata']['same_exact_manifest_reused']
    assert restored.spec.seed == 2026 and restored.spec.sample_count == 4
    assert [v.unit for v in restored.spec.variations] == ['s', 'eV']
    assert all(v.binding.scope.value != 'model' for v in restored.spec.variations)
    assert all('not inferred' in v.provenance.source for v in restored.spec.variations)
    assert sources[0]['points'][0]['point'] == sources[1]['points'][0]['point']
    assert [p['point']['index'] for p in sources[0]['points']] == [0, 1, 2, 3]


def test_nominal_prediction_actually_uses_fitted_kinetics(reports):
    from ncmemsim.workflows.application import _restore_device, _restore_protocol
    from ncmemsim.program_protocol import run_program_pulse_read
    raw = reports[False].to_dict()
    applied = application(reports[False])
    initial = applied.to_dict()
    evaluator = WorkflowEvaluator(applied, _restore_device(initial['applied_context']['device']),
        _restore_protocol(initial['operating']))
    simulator = evaluator.fresh_simulator()
    expected = evaluator.evaluate(evaluator.base_device, evaluator.base_protocol)
    output = raw['nominal_comparisons'][0]['data']['nominal_result']['output']
    assert output['delta_vfb_V'] == expected['delta_vfb_V']
    assert output['mean_occupation'] == expected['mean_occupation']
    assert output['shift_magnitude_V'] == abs(output['delta_vfb_V'])
    assert output['duration_s'] == evaluator.base_protocol.programming_time_s
    simulator.physics.occupancy.config = replace(simulator.physics.occupancy.config, nu0_Hz=1e12)
    baseline = run_program_pulse_read(simulator, evaluator.base_protocol)
    assert abs(baseline.delta_vfb_V - output['delta_vfb_V']) > 1e-9


def test_nominal_and_every_assessed_sample_can_be_recomputed_from_captured_context(reports):
    from ncmemsim.workflows.application import _restore_device, _restore_protocol
    from ncmemsim.dtco import apply_device_binding, apply_operating_binding
    report = reports[False].to_dict()
    for index, analysis in enumerate(report['analyses']):
        source = analysis['data']['source']
        applied = application(reports[False], index)
        context = applied.to_dict()
        evaluator = WorkflowEvaluator(applied, _restore_device(context['applied_context']['device']), _restore_protocol(context['operating']))
        # Phase H has its own retained device identity, without I2 layer metadata.
        nominal = evaluator.base_device
        nominal.temperature_K = report['metadata']['design_temperatures_K'][index]
        manifest = SampleManifest.from_json(json.dumps(source['manifest']))
        before = deepcopy(nominal.to_dict())
        for values, point in zip(manifest.values, source['points']):
            device, protocol = deepcopy(nominal), evaluator.base_protocol
            for variation, value in zip(manifest.spec.variations, values):
                if variation.binding.scope.value == 'device':
                    device = apply_device_binding(device, variation.binding, value)
                else:
                    protocol = apply_operating_binding(protocol, variation.binding, value)
            actual = evaluator.evaluate(device, protocol)
            assert actual['delta_vfb_V'] == point['output']['delta_vfb_V']
            assert actual['mean_occupation'] == point['output']['mean_occupation']
        assert nominal.to_dict() == before


@pytest.mark.parametrize('mode', [False, True])
def test_failure_counts_denominators_and_robust_policy_are_explicit(reports, mode):
    report = reports[mode].to_dict()
    for analysis in report['analyses']:
        data = analysis['data']
        assert data['counts']['total'] == 4
        assert data['counts']['assessed'] == (1 if mode else 4)
        assert data['counts']['failed'] == (3 if mode else 0)
        assert data['counts']['infeasible'] == 0
        assert data['fractions']['observed_feasible_fraction_all_attempted']['denominator'] == 4
        assert data['fractions']['observed_feasible_fraction_all_attempted']['value'] == (.25 if mode else 1.)
        assert data['fractions']['conditional_feasible_fraction_assessed']['value'] == 1.
        assert all(s['sample_indices'] == ([0] if mode else [0, 1, 2, 3]) for s in data['metric_statistics'])
        if mode:
            assert data['source']['points'][1]['failure']['stage'] == 'evaluation'
            assert data['source']['points'][3]['failure']['stage'] == 'serialization'
            assert data['points'][2]['failure']['stage'] == 'extraction'
            assert all(p['status'] == 'failed' for p in data['points'][1:])
    policy = report['robust_pareto']['data']['spec']
    assert policy['minimum_assessed_count'] == (1 if mode else 4)
    assert policy['minimum_observed_feasible_fraction'] == (0. if mode else 1.)
    assert all(c['data']['status'] == 'assessed' for c in report['nominal_comparisons'])


def test_repeated_execution_and_archive_restore_need_no_refit(reports, monkeypatch):
    normal = reports[False]
    assert reference.build_reference_report().report_hash == normal.report_hash
    def forbidden(*a, **kw): pytest.fail('execution during restoration')
    monkeypatch.setattr(reference, 'build_workflow_sources', forbidden)
    monkeypatch.setattr(reference, 'apply_workflow_parameters', forbidden)
    monkeypatch.setattr(reference, 'propagate_samples', forbidden)
    restored = RobustDTCOReport.from_json(normal.to_json())
    assert restored.to_dict() == normal.to_dict()
    for mode in (False, True):
        AppliedWorkflowEvidence.from_json(application(reports[mode]).to_json())


@pytest.mark.parametrize('mode', [False, True])
def test_existing_exports_retain_complete_evidence_and_nonoverwrite(reports, mode, tmp_path):
    destination = tmp_path / 'exports'
    paths = write_robust_dtco_report(reports[mode], destination)
    assert len(paths) == 6
    restored = RobustDTCOReport.from_json((destination / 'manifest.json').read_text(encoding='utf-8'))
    assert restored.report_hash == reports[mode].report_hash
    assert restored.to_dict()['metadata']['scientific_status'] == 'FITTED'
    assert restored.to_dict()['metadata']['data_origin'] == 'synthetic'
    with pytest.raises(FileExistsError): write_robust_dtco_report(reports[mode], destination)


def test_cli_runs_outside_source_cwd_and_discloses_synthetic_claims(tmp_path):
    path = Path(reference.__file__).resolve()
    result = subprocess.run([sys.executable, str(path)], cwd=tmp_path, capture_output=True, text=True, check=True)
    assert 'Data origin: synthetic; scientific status: FITTED' in result.stdout
    assert 'software verification only' in result.stdout
    assert not list(tmp_path.iterdir())


def test_source_inventory_and_future_installed_probe_include_reference():
    from scripts.validate_dtco_distribution import SOURCE_REQUIRED, PROBE
    assert 'examples/phase_i3_electrical_workflow_reference.py' in SOURCE_REQUIRED
    assert 'electrical_workflow_reference.build_reference_report' in PROBE
    # Syntax/inventory checks only: real builds and installed execution are I7.
    compile(PROBE, 'future-installed-probe', 'exec')


def test_failure_demo_is_not_a_truthy_implicit_flag():
    with pytest.raises(TypeError): reference.build_reference_report(include_failures='yes')
