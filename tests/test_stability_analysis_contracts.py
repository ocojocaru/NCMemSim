"""Cross-layer scientific result contracts, without altering numerical models."""
import csv
from io import StringIO
import json
import math

import numpy as np
import pytest

from ncmemsim import DeviceBuilder
from ncmemsim.calibration import CalibrationCriteria, qualify_calibration
from ncmemsim.fit_diagnostics import analyze_fit_uncertainty
from ncmemsim.fitting import (DeterministicFitResult, FitParameter, FitParameterSet,
    LeastSquaresConfig, evaluate_least_squares_objective, run_least_squares_fit)
from ncmemsim.dtco import (BindingScope, ParameterBinding, UniformVariation, VariationDefinition,
    VariationKind, VariationProvenance, SamplingSpec, sample_variations, propagate_samples,
    MetricDefinition, MetricConstraint, MetricAnalysisSpec, ConstraintOperator, ObjectiveDirection,
    SampleAnalysisSpec, analyze_samples, evaluate_nominal, compare_nominal,
    RobustObjective, RobustStatistic, RobustFailurePolicy, RobustParetoSpec,
    analyze_robust_pareto, build_robust_dtco_report, RobustDTCOReport)


@pytest.fixture(scope='module')
def linear_fits():
    pytest.importorskip('scipy')
    x = np.array([1.0, 2.0, 3.0, 4.0])
    observed = np.array([1.0, 2.1, 2.8, 4.2])
    parameters = FitParameterSet((FitParameter('amplitude', 0.8, 0.0, 2.0, 'V'),))
    results = []
    for sigma in (None, 0.2):
        def residuals(values):
            raw = values[0] * x - observed
            return raw if sigma is None else raw / sigma
        fit = run_least_squares_fit(parameters, residuals)
        objective = evaluate_least_squares_objective(observed, fit.fitted_values[0] * x,
            uncertainty=None if sigma is None else np.full(4, sigma))
        results.append((fit, objective, analyze_fit_uncertainty(fit)))
    return tuple(results)


def test_weighted_objective_does_not_change_raw_validation_units(linear_fits):
    raw, weighted = linear_fits
    np.testing.assert_allclose(raw[0].fitted_values, weighted[0].fitted_values, rtol=1e-6)
    assert weighted[1].weighted is True and raw[1].weighted is False
    np.testing.assert_allclose(weighted[1].objective_residuals, weighted[1].residuals / 0.2)
    assert weighted[1].root_mean_square_error == pytest.approx(raw[1].root_mean_square_error)
    assert weighted[1].mean_absolute_error == pytest.approx(raw[1].mean_absolute_error)
    assert weighted[0].cost == pytest.approx(weighted[1].objective_sum_squares / 2)
    assert weighted[0].cost != pytest.approx(weighted[1].residual_sum_squares / 2)


def test_uniform_weight_rescaling_retains_physical_covariance_units(linear_fits):
    raw, weighted = linear_fits
    assert weighted[2].degrees_of_freedom == raw[2].degrees_of_freedom == 3
    assert weighted[2].residual_variance == pytest.approx(raw[2].residual_variance / 0.2**2)
    np.testing.assert_allclose(raw[2].covariance_matrix, weighted[2].covariance_matrix, rtol=1e-5)
    np.testing.assert_allclose(raw[2].standard_errors, weighted[2].standard_errors, rtol=1e-5)
    assert weighted[0].jacobian.shape == (4, 1)
    np.testing.assert_allclose(weighted[0].jacobian[:, 0], np.arange(1, 5) / 0.2, rtol=1e-5)


def test_generic_qualification_uses_raw_rmse_and_never_mutates_fit(linear_fits):
    fit, _, diagnostics = linear_fits[1]
    before = fit.to_dict()
    objective = evaluate_least_squares_objective([0.0, 1.0, 2.0], [0.01, 1.01, 2.01], uncertainty=[0.001]*3)
    qualification = qualify_calibration(fit, diagnostics, fit_dataset_hash='training',
        validation_dataset_hash='holdout', validation_objective=objective,
        criteria=CalibrationCriteria(max_validation_rmse=0.02))
    assert qualification.eligible_for_calibration is True
    assert objective.root_mean_square_error == pytest.approx(0.01)
    assert objective.objective_sum_squares == pytest.approx(300.0)
    assert fit.to_dict() == before
    assert 'scientific_status' not in qualification.to_dict()
    assert 'calibrated_parameter' not in qualification.to_dict()


def test_undefined_r2_fails_only_an_enabled_r2_gate(linear_fits):
    fit, _, diagnostics = linear_fits[0]
    objective = evaluate_least_squares_objective([1.0, 1.0, 1.0], [1.0, 1.0, 1.0])
    assert objective.coefficient_of_determination is None
    for enabled, expected in ((False, True), (True, False)):
        result = qualify_calibration(fit, diagnostics, fit_dataset_hash='training',
            validation_dataset_hash='holdout', validation_objective=objective,
            criteria=CalibrationCriteria(max_validation_rmse=0.1, min_validation_r2=0.9 if enabled else None))
        assert result.eligible_for_calibration is expected


def _declared_fit(jacobian, residuals, active_mask=None):
    columns = np.asarray(jacobian).shape[1]
    params = FitParameterSet(tuple(FitParameter('p' + str(i), 1.0, 0.0, 2.0, 'V') for i in range(columns)))
    return DeterministicFitResult(parameter_set=params, config=LeastSquaresConfig(),
        initial_values=np.ones(columns), fitted_values=np.ones(columns),
        objective_residuals=np.asarray(residuals), success=True, status=1, message='Exact declared Jacobian',
        nfev=1, njev=1, optimality=0.0, active_mask=np.zeros(columns, dtype=int) if active_mask is None else active_mask,
        scipy_version='declared-test-result', jacobian=np.asarray(jacobian, dtype=float))


@pytest.mark.parametrize('case', ['rank_deficient', 'active_bound', 'zero_dof'])
def test_unavailable_covariance_is_not_zero_uncertainty(case):
    if case == 'rank_deficient':
        fit = _declared_fit([[1, 1]]*4, [0.1, -0.1, 0.1, -0.1])
    elif case == 'active_bound':
        fit = _declared_fit([[1], [2], [3]], [0.1, -0.1, 0.1], np.array([1]))
    else:
        fit = _declared_fit([[1]], [0.0])
    d = analyze_fit_uncertainty(fit)
    assert d.covariance_matrix is d.standard_errors is d.correlation_matrix is None
    assert d.parameter_standard_errors is None and d.covariance_available is False
    if case == 'rank_deficient':
        assert d.jacobian_rank == 1 and d.degrees_of_freedom == 3
        assert math.isinf(d.scaled_condition_number)
        with pytest.raises(ValueError):
            json.dumps(d.to_dict(), allow_nan=False)
    elif case == 'active_bound':
        assert d.locally_identifiable is True and d.bound_constrained is True
    else:
        assert d.degrees_of_freedom == 0 and d.residual_variance is None
        assert d.locally_identifiable is True


def test_fit_arrays_and_serialized_lists_have_distinct_ownership(linear_fits):
    fit, objective, diagnostics = linear_fits[0]
    for values in (fit.fitted_values, fit.objective_residuals, fit.jacobian,
            objective.residuals, diagnostics.covariance_matrix, diagnostics.standard_errors):
        assert values.flags.writeable is False
        with pytest.raises(ValueError):
            values.flat[0] = 0.0
    before = fit.to_dict()
    detached = fit.to_dict()
    detached['fitted_values'][0] = 99.0
    detached['jacobian'][0][0] = 99.0
    assert fit.to_dict() == before


def _analysis(outputs):
    definition = VariationDefinition('temperature', ParameterBinding(BindingScope.DEVICE, ('temperature_K',)),
        UniformVariation(295, 305), 'K', VariationKind.PARAMETER_ESTIMATION,
        VariationProvenance('Assumed bounded variation', 'Contract audit'))
    manifest = sample_variations(SamplingSpec((definition,), 17, len(outputs)))
    device = DeviceBuilder.v2(n_fgs=1)
    def callback(candidate, protocol, point):
        output = outputs[point.index]
        if isinstance(output, Exception):
            raise output
        return output
    source = propagate_samples(manifest, device, callback, evaluation_id='analysis-contract-v1')
    metrics = MetricAnalysisSpec('signed response and time',
        (MetricDefinition('signal', ('signal',), 'V'), MetricDefinition('duration', ('duration',), 's')),
        (MetricConstraint('positive signal', 'signal', ConstraintOperator.GE, 0.0, 'V'),))
    return device, analyze_samples(source, SampleAnalysisSpec(metrics, quantiles=(0.5,)))


def _robust_spec(policy):
    return RobustParetoSpec('explicit empirical mean',
        (RobustObjective('mean signal', 'signal', 'V', ObjectiveDirection.MAXIMIZE, RobustStatistic.MEAN),),
        policy, 1, 0.0)


def test_complete_case_denominators_survive_robust_report_and_roundtrip():
    outputs = [{'signal':4, 'duration':0.1}, {'signal':-2, 'duration':0.3},
        {'signal':100}, RuntimeError('evaluation failure'), {'signal':np.array([1.0]), 'duration':0.1},
        {'signal':True, 'duration':0.1}, {'signal':math.nan, 'duration':0.1}]
    _, result = _analysis(outputs)
    assert (result.total_count, result.assessed_count, result.feasible_count, result.infeasible_count, result.failure_count) == (7, 2, 1, 1, 5)
    assert result.observed_feasible_fraction_all_attempted == pytest.approx(1/7)
    assert result.conditional_feasible_fraction_assessed == 0.5
    data = result.to_dict()
    assert data['counts']['propagation_failed'] == 3 and data['counts']['extraction_failed'] == 2
    assert [s['sample_indices'] for s in result.metric_statistics] == [[0, 1], [0, 1]]
    assert result.metric_statistics[0]['mean'] == 1.0 and result.metric_statistics[0]['standard_deviation'] == 3.0
    assert result.metric_statistics[1]['mean'] == pytest.approx(0.2)
    allowed = analyze_robust_pareto((result,), _robust_spec(RobustFailurePolicy.ALLOW_ASSESSED_WITH_FAILURES))
    denied = analyze_robust_pareto((result,), _robust_spec(RobustFailurePolicy.REQUIRE_NO_FAILURES))
    assert allowed.pareto_indices == (0,) and denied.pareto_indices == ()
    assert denied.to_dict()['points'][0]['rank'] is None
    report = build_robust_dtco_report((result,), name='cross-layer contract', robust_pareto=allowed)
    restored = RobustDTCOReport.from_json(report.to_json())
    assert restored.report_hash == report.report_hash
    assert restored.to_dict()['analyses'][0]['data']['fractions'] == data['fractions']
    rows = list(csv.DictReader(StringIO(restored.samples_csv())))
    assert len(rows) == 7
    assert [row['analysis_status'] for row in rows].count('failed') == 5


def test_all_failed_undefined_values_remain_null_through_nominal_and_csv():
    device, result = _analysis([RuntimeError('failure'), {'signal':1}])
    nominal = evaluate_nominal(device, lambda candidate, protocol: {'signal':2.0, 'duration':0.1}, evaluation_id='analysis-contract-v1')
    comparison = compare_nominal(result, nominal)
    data = comparison.to_dict()
    assert data['status'] == 'assessed' and data['nominal_feasible'] is True
    assert all(m['mean_minus_nominal'] is None and m['difference_undefined_reason'] == 'no_assessed_samples' for m in data['metrics'])
    assert result.conditional_feasible_fraction_assessed is None
    front = analyze_robust_pareto((result,), _robust_spec(RobustFailurePolicy.ALLOW_ASSESSED_WITH_FAILURES))
    assert front.pareto_indices == () and 'undefined_objective' in front.to_dict()['points'][0]['exclusion_reasons']
    report = build_robust_dtco_report((result,), name='undefined contract', nominal_comparisons=(comparison,), robust_pareto=front)
    statistics = list(csv.DictReader(StringIO(report.statistics_csv())))
    assert all(row['mean'] == 'null' and row['population_std'] == 'null' and row['denominator'] == '0' for row in statistics)
    robust = list(csv.DictReader(StringIO(report.robust_csv())))
    assert robust[0]['rank'] == 'null'
    restored = RobustDTCOReport.from_json(report.to_json())
    assert restored.to_dict()['analyses'][0]['data']['fractions']['conditional_feasible_fraction_assessed']['value'] is None
