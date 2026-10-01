# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Numerical population semantics and recomputed MODEL archival integrity."""
import pytest

from ncmemsim.dtco import MetricAnalysisSpec, MetricDefinition, MetricConstraint, ConstraintOperator
from ncmemsim.ensemble import EnsembleStatisticsSpec, NominalMetricReference
from ncmemsim.ensemble.model_analysis import ModelPopulationAnalysis, analyze_model_execution
from ncmemsim.ensemble.model_execution import ModelExecutionResult, execute_model_sample_manifest
from ncmemsim.ensemble.model_sampling import generate_model_sample_manifest
from ncmemsim.hashing import canonical_hash
from test_phase_l2_model_execution import make, stored


def execution(outputs, *, failing=()):
    device, spec, _ = make(count=len(outputs))
    def evaluator(realization, workflow):
        index = realization.sample.sample_index
        if index in failing:
            raise ArithmeticError("controlled workflow failure")
        return outputs[index]
    return execute_model_sample_manifest(generate_model_sample_manifest(spec), device, evaluator,
                                         evaluation_id="L4-tests", workflow_context={"scope": "synthetic"})


def metrics(two=False, constraints=True):
    definitions = [MetricDefinition("x", ("x",), "Hz")]
    if two:
        definitions.append(MetricDefinition("y", ("y",), "V"))
    bounds = (MetricConstraint("upper", "x", ConstraintOperator.LE, 3, "Hz"),) if constraints else ()
    return MetricAnalysisSpec("L4", tuple(definitions), bounds)


def test_known_population_complete_cases_include_infeasible_points():
    source = execution([{"x": 1}, {"x": 3}, {"x": 5}, {"x": 7}])
    analysis = analyze_model_execution(source, metrics(), statistics_spec=EnsembleStatisticsSpec((0, 0.25, 0.5, 1)),
                                        nominal_references=(NominalMetricReference("x", "Hz", 2),))
    result = analysis.to_dict()
    assert result["counts"] == {"attempted_count": 4, "assessed_count": 4, "feasible_count": 2,
        "infeasible_count": 2, "failed_count": 0, "execution_failure_count": 0, "metric_failure_count": 0}
    summary = result["statistics"][0]
    assert summary["mean"] == 4
    assert summary["variance"] == 5  # Population variance, not sample variance.
    assert summary["standard_deviation"] == pytest.approx(5 ** 0.5)
    assert summary["median"] == 4
    assert summary["minimum"] == 1 and summary["maximum"] == 7
    assert [q["value"] for q in summary["quantiles"]] == [1, 2.5, 4, 7]
    assert summary["denominator"] == 4 and summary["sample_indices"] == [0, 1, 2, 3]
    assert result["fractions"]["simulated_pass_fraction"] == {"numerator": 2, "denominator": 4, "value": 0.5}
    assert result["nominal_comparisons"][0]["mean_delta"] == 2
    assert result["nominal_comparisons"][0]["median_delta"] == 2


def test_mixed_failures_have_exact_denominators_and_original_provenance():
    source = execution([{"x": 1, "y": 2}, {"x": 5, "y": 4}, {"x": 3}, {}], failing=(3,))
    original = source.to_json()
    analysis = analyze_model_execution(source, metrics(two=True))
    data = analysis.to_dict()
    assert analysis.counts["attempted_count"] == 4
    assert analysis.counts["assessed_count"] == 2
    assert analysis.counts["feasible_count"] == analysis.counts["infeasible_count"] == 1
    assert analysis.counts["execution_failure_count"] == analysis.counts["metric_failure_count"] == 1
    assert data["failure_stage_counts"] == {"metric-extraction": 1, "workflow": 1}
    assert data["points"][2]["metric_values"] == []  # No partial metric set leaks into statistics.
    assert [s["sample_indices"] for s in data["statistics"]] == [[0, 1], [0, 1]]
    fractions = analysis.fractions
    assert fractions["coverage_fraction"]["value"] == 0.5
    assert fractions["simulated_pass_fraction"]["value"] == 0.25
    assert fractions["ensemble_feasibility_fraction"]["value"] == 0.5
    assert fractions["failure_fraction"]["value"] == 0.5
    for key in ("failure_stage", "failure_category", "error_type", "error_message"):
        assert data["points"][3][key] == source.points[3].to_dict()[key]
    assert source.to_json() == original


def test_all_failed_keeps_counts_null_statistics_and_nominal_identity():
    source = execution([{}, {}], failing=(1,))
    result = analyze_model_execution(source, metrics(), nominal_references=(NominalMetricReference("x", "Hz", 2),)).to_dict()
    assert result["counts"]["assessed_count"] == 0 and result["counts"]["failed_count"] == 2
    summary = result["statistics"][0]
    assert summary["denominator"] == 0 and summary["sample_indices"] == []
    for key in ("mean", "median", "variance", "standard_deviation", "minimum", "maximum"):
        assert summary[key] is None
    assert all(q["value"] is None for q in summary["quantiles"])
    assert result["fractions"]["simulated_pass_fraction"]["value"] == 0
    assert result["fractions"]["failure_fraction"]["value"] == 1
    assert result["fractions"]["ensemble_feasibility_fraction"] == {"numerator": 0, "denominator": 0, "value": None}
    assert result["nominal_comparisons"][0]["nominal_value"] == 2
    assert result["nominal_comparisons"][0]["mean_delta"] is None


def test_single_member_empty_quantiles_and_unconstrained_feasibility():
    result = analyze_model_execution(execution([{"x": 2}]), metrics(constraints=False),
                                     statistics_spec=EnsembleStatisticsSpec(())).to_dict()
    summary = result["statistics"][0]
    assert summary["variance"] == summary["standard_deviation"] == 0
    assert summary["quantiles"] == []
    assert result["nominal_comparisons"] == []
    assert result["counts"]["feasible_count"] == 1


@pytest.mark.parametrize("bad", [True, "category", [1], {"value": 1}, 10 ** 400, 2 ** 53 + 1])
def test_invalid_scalar_or_inexact_integer_is_metric_failure(bad):
    result = analyze_model_execution(execution([{"x": bad}, {"x": 2}]), metrics())
    assert result.counts["metric_failure_count"] == 1
    assert result.counts["assessed_count"] == 1


def test_existing_execution_failures_are_not_reinterpreted_as_infeasibility():
    device, spec, _ = make(count=3)
    manifest = stored(spec, [(-1,), (0,), (8e24,)])
    source = execute_model_sample_manifest(manifest, device, lambda r, w: {"x": 9},
                                          evaluation_id="failures", workflow_context={"purpose": "synthetic"})
    result = analyze_model_execution(source, metrics()).to_dict()
    assert result["counts"]["failed_count"] == 2
    assert result["counts"]["infeasible_count"] == 1
    assert result["failure_stage_counts"] == {"realization-construction": 1, "sample-domain-validation": 1}


def test_array_metrics_and_ge_constraint():
    spec = MetricAnalysisSpec("array", (MetricDefinition("v", ("array", 0), "V"),),
                              (MetricConstraint("minimum", "v", ConstraintOperator.GE, 2, "V"),))
    result = analyze_model_execution(execution([{"array": [1]}, {"array": [2]}, {"array": []}]), spec)
    assert result.counts["feasible_count"] == 1 and result.counts["infeasible_count"] == 1
    assert result.counts["metric_failure_count"] == 1


@pytest.mark.parametrize("references", [
    (NominalMetricReference("x", "V", 2),), (NominalMetricReference("unknown", "Hz", 2),),
    (NominalMetricReference("x", "Hz", 2), NominalMetricReference("x", "Hz", 3)), (object(),),
])
def test_invalid_nominal_references_rejected(references):
    with pytest.raises((ValueError, TypeError)):
        analyze_model_execution(execution([{"x": 1}]), metrics(), nominal_references=references)


def test_overflow_of_statistics_and_nominal_delta_fails_closed():
    with pytest.raises((ValueError, OverflowError)):
        analyze_model_execution(execution([{"x": -1e308}, {"x": 1e308}]), metrics())
    with pytest.raises(ValueError, match="delta must be finite"):
        analyze_model_execution(execution([{"x": 1e308}]), metrics(),
                                nominal_references=(NominalMetricReference("x", "Hz", -1e308),))


def test_analysis_and_restoration_do_not_execute_physics_or_draw_samples(monkeypatch):
    import ncmemsim.ensemble.model_sampling as sampling
    import ncmemsim.ensemble.model_execution as executing
    source = execution([{"x": 1}, {"x": 3}])
    monkeypatch.setattr(sampling, "generate_model_sample_manifest", lambda *a: pytest.fail("resampling"))
    monkeypatch.setattr(executing, "execute_model_sample_manifest", lambda *a: pytest.fail("rerunning physics"))
    result = analyze_model_execution(source, metrics())
    assert ModelPopulationAnalysis.from_json(result.to_json()).analysis_hash == result.analysis_hash
    assert analyze_model_execution(source, metrics()).to_json() == result.to_json()


@pytest.mark.parametrize("mutate", [
    lambda d: d["counts"].update(assessed_count=99),
    lambda d: d["counts"].update(feasible_count=True),
    lambda d: d["fractions"]["coverage_fraction"].update(denominator=99),
    lambda d: d["statistics"][0].update(mean=99),
    lambda d: d["statistics"][0].update(variance=99),
    lambda d: d["statistics"][0]["quantiles"][0].update(value=99),
    lambda d: d["points"][0]["metric_values"][0].__setitem__(1, 99),
    lambda d: d["points"].reverse(), lambda d: d["failure_stage_counts"].update(workflow=99),
    lambda d: d["statistics_spec"].update(variance="sample-ddof-1"),
    lambda d: d.update(source_hash="0" * 64), lambda d: d.update(metric_spec_hash="0" * 64),
    lambda d: d.update(extra=1), lambda d: d.update(schema_version="unknown"),
])
def test_forged_derived_content_is_rejected_even_with_rehashed_outer_archive(mutate):
    data = analyze_model_execution(execution([{"x": 1}, {"x": 3}]), metrics()).to_dict()
    mutate(data)
    data["analysis_hash"] = canonical_hash({k: v for k, v in data.items() if k != "analysis_hash"})
    with pytest.raises((ValueError, TypeError)):
        ModelPopulationAnalysis.from_dict(data)


def test_snapshot_ownership_and_duplicate_json_keys():
    analysis = analyze_model_execution(execution([{"x": 1}]), metrics())
    original = analysis.to_json()
    data = analysis.to_dict()
    data["counts"]["feasible_count"] = 99
    assert analysis.to_json() == original
    with pytest.raises(ValueError, match="duplicate"):
        ModelPopulationAnalysis.from_json(original.replace('{', '{"schema_version":"forged",', 1))


def test_l3_real_reference_analysis_preserves_scientific_limits():
    from examples.phase_l3_tat_density_variability import run_reference
    evidence = run_reference()
    source = ModelExecutionResult.from_dict(evidence["execution"])
    spec = MetricAnalysisSpec("L3 rates", (MetricDefinition("tat_rate", ("initial_tat_rate_Hz",), "Hz"),))
    result = analyze_model_execution(source, spec,
        nominal_references=(NominalMetricReference("tat_rate", "Hz", evidence["nominal"]["initial_tat_rate_Hz"]),))
    assert result.counts["assessed_count"] == 16
    assert result.to_dict()["statistics"][0]["denominator"] == 16
    assert evidence["interpretation"]["dynamic_population_precision_claim"] is False
