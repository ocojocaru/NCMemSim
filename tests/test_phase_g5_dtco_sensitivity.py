from dataclasses import FrozenInstanceError, replace
import json
import math
import random

import pytest

from ncmemsim import DeviceBuilder, Simulator
from ncmemsim.dtco import (
    BindingScope, ConstraintOperator, DesignVariable, DesignVariableRole,
    ExperimentSpec, MetricAnalysisSpec, MetricConstraint, MetricDefinition,
    ParameterBinding, SensitivityAnalysisResult, SensitivityAnalysisSpec,
    SensitivityEdge, SensitivityEligibility, analyze_sensitivity, analyze_sweep,
    run_cartesian_sweep,
)
from ncmemsim.program_protocol import ProgramPulseReadProtocol, run_program_pulse_read


def source(xs=(300, 325, 350), ys=(4, 6), evaluate=None, constraints=()):
    device = DeviceBuilder.v2(n_fgs=1)
    variables = (
        DesignVariable("x", ParameterBinding(BindingScope.DEVICE, ("temperature_K",)),
                       xs, DesignVariableRole.MODEL, "K"),
        DesignVariable("y", ParameterBinding(BindingScope.DEVICE,
                       ("layers", "FG1", "nc_diameter_nm")),
                       ys, DesignVariableRole.GEOMETRY, "nm"),
    )
    experiment = ExperimentSpec.from_device(name="sensitivity-source", device=device, variables=variables)
    def callback(d, p, point):
        x, y = point.assignments["x"], point.assignments["y"]
        value = evaluate(x, y) if evaluate else 3*x + 2*y
        if value is None:
            raise RuntimeError("point failed")
        return {"response": value, "constant": 7}
    sweep = run_cartesian_sweep(experiment, device, callback, evaluation_id="g5-test-v1")
    return analyze_sweep(sweep, MetricAnalysisSpec("metrics", (
        MetricDefinition("response", ("response",), "V"),
        MetricDefinition("constant", ("constant",), "1"),
    ), constraints))


def spec(axes=("x", "y"), metrics=("response",), eligibility=SensitivityEligibility.ASSESSED):
    return SensitivityAnalysisSpec("sensitivity", axes, metrics, eligibility)


def test_linear_response_secants_units_and_grid_summaries():
    analysis = source()
    result = analyze_sensitivity(analysis, spec())
    assert [e.slope for e in result.edges if e.axis_name == "x"] == [3, 3, 3, 3]
    assert [e.slope for e in result.edges if e.axis_name == "y"] == [2, 2, 2]
    x, y = result.summaries
    assert x["attempted_count"] == x["estimated_count"] == 4
    assert y["attempted_count"] == y["estimated_count"] == 3
    assert x["mean_slope"] == x["mean_absolute_slope"] == x["max_absolute_slope"] == 3
    assert x["axis_unit"] == "K" and x["metric_unit"] == "V"
    assert x["slope_unit"] == "(V)/(K)"
    assert x["coverage_fraction"] == 1 and x["complete"]


def test_unsorted_domains_are_sorted_numerically_without_reordering_source():
    analysis = source(xs=(350, 300, 325))
    original = analysis.to_json()
    result = analyze_sensitivity(analysis, spec(axes=("x",)))
    assert [(e.left_index, e.right_index) for e in result.edges] == [(2, 4), (4, 0), (3, 5), (5, 1)]
    assert [(e.left_value, e.right_value) for e in result.edges] == [(300, 325), (325, 350)] * 2
    assert analysis.to_json() == original


def test_nonlinear_nonuniform_grid_secants_and_equal_edge_weighting():
    result = analyze_sensitivity(source(xs=(6, 1, 3), ys=(4,), evaluate=lambda x, y: x*x),
                                 spec(axes=("x",)))
    assert [e.slope for e in result.edges] == [4, 9]
    assert result.summaries[0]["mean_slope"] == 6.5
    assert result.summaries[0]["max_absolute_slope"] == 9


def test_interactions_hold_other_axes_fixed_and_global_summary_covers_contexts():
    result = analyze_sensitivity(source(xs=(1, 2, 3), evaluate=lambda x, y: x*y), spec())
    assert [e.slope for e in result.edges if e.axis_name == "x"] == [4, 4, 6, 6]
    assert [e.slope for e in result.edges if e.axis_name == "y"] == [1, 2, 3]
    assert result.summaries[0]["mean_slope"] == 5
    assert result.summaries[1]["mean_slope"] == 2


def test_failed_neighbor_is_excluded_without_bridging():
    analysis = source(evaluate=lambda x, y: None if x == 325 else x)
    result = analyze_sensitivity(analysis, spec(axes=("x",)))
    assert len(result.edges) == 4
    assert all(e.status == "excluded" and e.slope is None for e in result.edges)
    summary = result.summaries[0]
    assert summary["excluded_count"] == 4 and summary["estimated_count"] == 0
    assert summary["coverage_fraction"] == 0
    assert summary["mean_slope"] is None and not summary["complete"]
    assert result.edges[0].reason == "right:failed"


def test_extraction_failed_neighbor_is_excluded():
    result = analyze_sensitivity(source(evaluate=lambda x, y: "bad" if x == 325 else x),
                                 spec(axes=("x",)))
    assert all(e.status == "excluded" for e in result.edges)
    assert result.source_analysis.points[2].failure_stage == "extraction"


def test_eligibility_explicitly_controls_infeasible_endpoints():
    bound = MetricConstraint("upper", "response", ConstraintOperator.LE, 325, "V")
    analysis = source(evaluate=lambda x, y: x, constraints=(bound,))
    assessed = analyze_sensitivity(analysis, spec(axes=("x",)))
    feasible = analyze_sensitivity(analysis, spec(
        axes=("x",), eligibility=SensitivityEligibility.FEASIBLE_ONLY))
    assert assessed.summaries[0]["estimated_count"] == 4
    assert feasible.summaries[0]["estimated_count"] == 2
    assert feasible.summaries[0]["excluded_count"] == 2
    assert feasible.summaries[0]["coverage_fraction"] == 0.5
    assert any(e.reason == "right:infeasible" for e in feasible.edges)
    assert assessed.analysis_hash != feasible.analysis_hash


def test_singleton_axis_has_no_estimates_and_null_coverage():
    result = analyze_sensitivity(source(xs=(300,)), spec(axes=("x",)))
    assert result.edges == ()
    summary = result.summaries[0]
    assert summary["attempted_count"] == 0 and summary["mean_slope"] is None
    assert summary["coverage_fraction"] is None and not summary["complete"]


def test_constant_metric_and_negative_response_preserve_sign():
    result = analyze_sensitivity(source(evaluate=lambda x, y: -x),
                                 spec(axes=("x",), metrics=("response", "constant")))
    assert [e.slope for e in result.edges] == [-1]*4 + [0]*4
    signed, constant = result.summaries
    assert signed["mean_slope"] == -1 and signed["mean_absolute_slope"] == 1
    assert constant["mean_slope"] == constant["max_absolute_slope"] == 0


def test_arithmetic_overflow_is_recorded_and_other_contexts_continue():
    analysis = source(xs=(300, 325), evaluate=lambda x, y:
                      (-1e308 if x == 300 else 1e308) if y == 4 else x)
    result = analyze_sensitivity(analysis, spec(axes=("x",)))
    assert [e.status for e in result.edges] == ["failed", "estimated"]
    assert result.edges[0].error_type == "builtins.ValueError"
    assert result.edges[0].slope is None
    assert result.summaries[0]["failure_count"] == 1
    json.loads(result.to_json())


def test_large_integer_metric_differences_are_computed_before_float_division():
    origin = 2**60
    result = analyze_sensitivity(source(xs=(300, 301), evaluate=lambda x, y: origin + x),
                                 spec(axes=("x",)))
    assert all(e.slope == 1 for e in result.edges)


@pytest.mark.parametrize("kwargs", [
    {"name": ""}, {"name": " spaced"}, {"axis_names": ()},
    {"axis_names": ("x", "x")}, {"axis_names": ("",)}, {"axis_names": "x"},
    {"metric_names": ()}, {"metric_names": ("response", "response")},
    {"metric_names": (" response",)}, {"eligibility": "assessed"},
])
def test_spec_validation(kwargs):
    with pytest.raises((ValueError, TypeError)):
        SensitivityAnalysisSpec(**{"name": "test", "axis_names": ("x",),
                                   "metric_names": ("response",), **kwargs})


def test_unknown_axis_metric_and_invalid_input_fail_setup():
    analysis = source()
    with pytest.raises(ValueError, match="unknown sensitivity axis"):
        analyze_sensitivity(analysis, spec(axes=("unknown",)))
    with pytest.raises(ValueError, match="unknown sensitivity metric"):
        analyze_sensitivity(analysis, spec(metrics=("unknown",)))
    with pytest.raises(TypeError):
        analyze_sensitivity(None)
    with pytest.raises(TypeError):
        analyze_sensitivity(analysis, "invalid")


def test_default_selects_numeric_axes_and_all_metrics():
    result = analyze_sensitivity(source())
    assert result.spec.axis_names == ("x", "y")
    assert result.spec.metric_names == ("response", "constant")


def test_categorical_axes_rejected_but_categorical_background_contexts_supported():
    device = DeviceBuilder.v2(n_fgs=1)
    variables = (
        DesignVariable("category", ParameterBinding(BindingScope.DEVICE, ("unknown",)),
                       ("low", "high"), DesignVariableRole.MODEL),
        DesignVariable("x", ParameterBinding(BindingScope.DEVICE, ("temperature_K",)),
                       (300, 325), DesignVariableRole.MODEL, "K"),
    )
    experiment = ExperimentSpec.from_device(name="categorical", device=device, variables=variables)
    sweep = run_cartesian_sweep(experiment, device, lambda *args: {"response": 1}, evaluation_id="test")
    analysis = analyze_sweep(sweep, MetricAnalysisSpec("metrics", (
        MetricDefinition("response", ("response",), "1"),
    )))
    with pytest.raises(TypeError, match="numeric"):
        analyze_sensitivity(analysis, spec(axes=("category",)))
    result = analyze_sensitivity(analysis)
    assert result.spec.axis_names == ("x",)
    assert len(result.edges) == 2 and all(e.status == "excluded" for e in result.edges)


def test_identity_snapshots_counts_and_complete_source_provenance():
    analysis = source()
    original = analysis.to_json()
    a, b = analyze_sensitivity(analysis, spec()), analyze_sensitivity(analysis, spec())
    assert a.to_json() == b.to_json() and a.result_hash == b.result_hash
    assert a.analysis_hash == b.analysis_hash
    assert analysis.to_json() == original
    assert analyze_sensitivity(analysis, spec(axes=("y", "x"))).analysis_hash != a.analysis_hash
    assert analyze_sensitivity(source(evaluate=lambda x, y: x), spec()).analysis_hash != a.analysis_hash
    exported = a.to_dict()
    exported["summaries"][0]["mean_slope"] = 999
    exported["axes"][0]["values"].append(999)
    assert a.summaries[0]["mean_slope"] == 3 and analysis.to_json() == original
    manifest = json.loads(a.to_json())
    assert manifest["source_result_hash"] == analysis.result_hash
    assert manifest["source_analysis"] == analysis.to_dict()


def test_input_sequences_and_result_edges_are_immutable():
    axes, metrics = ["x"], ["response"]
    definition = SensitivityAnalysisSpec("snapshot", axes, metrics)
    axes.clear()
    metrics.clear()
    assert definition.axis_names == ("x",)
    result = analyze_sensitivity(source(), definition)
    with pytest.raises(FrozenInstanceError):
        result.edges[0].slope = 100


@pytest.mark.parametrize("seed", range(12))
def test_random_nonuniform_linear_grids_match_analytic_slopes(seed):
    rng = random.Random(seed)
    xs = rng.sample(range(280, 350), 4)
    ys = rng.sample(range(3, 10), 3)
    a, b = rng.randint(-5, 5), rng.randint(-5, 5)
    result = analyze_sensitivity(source(xs=xs, ys=ys, evaluate=lambda x, y: a*x + b*y), spec())
    assert all(e.slope == (a if e.axis_name == "x" else b) for e in result.edges)
    assert result.summaries[0]["attempted_count"] == 9
    assert result.summaries[1]["attempted_count"] == 8


def test_public_result_validation_requires_every_edge_and_correct_geometry():
    result = analyze_sensitivity(source(), spec())
    with pytest.raises(ValueError, match="every adjacent"):
        replace(result, edges=result.edges[:-1])
    with pytest.raises(ValueError, match="geometry"):
        replace(result, edges=tuple(reversed(result.edges)))
    with pytest.raises(ValueError, match="eligibility"):
        wrong = replace(result.edges[0], status="excluded", slope=None, reason="left:failed")
        replace(result, edges=(wrong, *result.edges[1:]))
    with pytest.raises(ValueError):
        SensitivityEdge("x", "response", 0, 1, 300, 325, "estimated", math.inf)
    with pytest.raises(ValueError):
        SensitivityEdge("x", "response", 0, 1, 325, 300, "estimated", 1)
    with pytest.raises(TypeError):
        SensitivityAnalysisResult("invalid", result.source_analysis, result.edges)


def test_real_program_read_duration_secant_matches_independent_difference():
    device = DeviceBuilder.v2(n_fgs=1)
    protocol = ProgramPulseReadProtocol(5.0, 1e-9)
    variable = DesignVariable(
        "duration", ParameterBinding(BindingScope.OPERATING, ("program", "time_s")),
        (1e-9, 2e-9), DesignVariableRole.ELECTRICAL, "s",
    )
    experiment = ExperimentSpec.from_device(name="real-sensitivity", device=device,
                                           variables=(variable,), operating_protocol=protocol)
    sweep = run_cartesian_sweep(experiment, device,
        lambda d, p, point: run_program_pulse_read(Simulator(d), p).to_dict(),
        evaluation_id="program-read-defaults-v1", base_protocol=protocol)
    analysis = analyze_sweep(sweep, MetricAnalysisSpec("metrics", (
        MetricDefinition("shift", ("observable", "value"), "V"),
    )))
    result = analyze_sensitivity(analysis)
    expected = (analysis.points[1].metrics["shift"] - analysis.points[0].metrics["shift"]) / 1e-9
    assert result.edges[0].slope == pytest.approx(expected)
    assert result.summaries[0]["slope_unit"] == "(V)/(s)"


def test_signed_slope_cancellation_keeps_absolute_statistics_visible():
    result = analyze_sensitivity(source(xs=(1, 2, 3), ys=(4,),
                                       evaluate=lambda x, y: (x - 2)**2), spec(axes=("x",)))
    assert [e.slope for e in result.edges] == [-1, 1]
    assert result.summaries[0]["mean_slope"] == 0
    assert result.summaries[0]["mean_absolute_slope"] == 1


def test_large_finite_slopes_have_finite_scaled_means():
    result = analyze_sensitivity(source(xs=(300, 301, 302), ys=(4,),
                                       evaluate=lambda x, y: (x - 301)*1e308), spec(axes=("x",)))
    summary = result.summaries[0]
    assert summary["estimated_count"] == 2
    assert summary["mean_slope"] == summary["mean_absolute_slope"] == 1e308
    json.loads(result.to_json())
