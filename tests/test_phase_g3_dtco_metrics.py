from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
import math

import pytest

from ncmemsim import DeviceBuilder, Simulator
from ncmemsim.dtco import (
    BindingScope, ConstraintEvaluation, ConstraintOperator, DesignVariable,
    DesignVariableRole, ExperimentSpec, MetricAnalysisResult, MetricAnalysisSpec,
    MetricConstraint, MetricDefinition, MetricPointResult, ObjectiveDirection,
    analyze_sweep, run_cartesian_sweep,
    ParameterBinding,
)
from ncmemsim.hashing import canonical_hash
from ncmemsim.program_protocol import ProgramPulseReadProtocol, run_program_pulse_read


def sweep(evaluator=None, temperatures=(300.0, 325.0, 350.0)):
    device = DeviceBuilder.v2(n_fgs=1)
    variable = DesignVariable(
        "temperature", ParameterBinding(BindingScope.DEVICE, ("temperature_K",)),
        temperatures, DesignVariableRole.MODEL, "K",
    )
    spec = ExperimentSpec.from_device(name="g3-source", device=device, variables=(variable,))
    return run_cartesian_sweep(
        spec, device, evaluator or (lambda d, p, point: {"value": d.temperature_K}),
        evaluation_id="g3-test-v1",
    )


def metric(**kwargs):
    return MetricDefinition(**{
        "name": "temperature", "path": ("value",), "unit": "K",
        "direction": ObjectiveDirection.MINIMIZE, **kwargs,
    })


def constraint(name="upper", operator=ConstraintOperator.LE, threshold=325.0, **kwargs):
    return MetricConstraint(**{
        "name": name, "metric_name": "temperature", "operator": operator,
        "threshold": threshold, "unit": "K", **kwargs,
    })


def analysis(*, metrics=None, constraints=()):
    return MetricAnalysisSpec("test-analysis", metrics or (metric(),), constraints)


def test_inclusive_constraints_and_distinct_feasibility_states():
    source = sweep(temperatures=(-1.0, 300.0, 325.0, 350.0))
    spec = analysis(constraints=(
        constraint("lower", ConstraintOperator.GE, 300.0), constraint(),
    ))
    result = analyze_sweep(source, spec)
    assert [p.status for p in result.points] == ["failed", "feasible", "feasible", "infeasible"]
    assert (result.feasible_count, result.infeasible_count, result.failure_count) == (2, 1, 1)
    assert result.points[0].failure_stage == "sweep"
    assert result.points[0].error_type == source.points[0].error_type
    assert result.points[0].error_message == source.points[0].error_message
    assert [c.satisfied for c in result.points[3].constraints] == [True, False]
    assert result.points[3].metrics == {"temperature": 350.0}
    assert result.points[3].constraints[1].value == 350.0


def test_extraction_failure_is_isolated_and_no_partial_metrics_escape():
    source = sweep(lambda d, p, point: {"value": d.temperature_K,
                                      "extra": None if point.index == 0 else 2})
    spec = analysis(metrics=(metric(), metric(name="extra", path=("extra",), unit="1")))
    result = analyze_sweep(source, spec)
    assert result.points[0].status == "failed"
    assert result.points[0].failure_stage == "extraction"
    assert result.points[0].metric_values == ()
    assert result.points[1].metrics == {"temperature": 325.0, "extra": 2}


@pytest.mark.parametrize("value", [True, False, "12", None, [], {}, [1], {"nested": 1}])
def test_nonnumeric_metrics_are_failed_not_infeasible(value):
    source = sweep(lambda d, p, point: {"value": value if point.index == 0 else 325.0})
    result = analyze_sweep(source, analysis(constraints=(constraint(),)))
    assert result.points[0].status == "failed"
    assert result.points[0].error_type == "builtins.TypeError"
    assert result.points[1].status == "feasible"


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_direct_metric_extraction_rejects_nonfinite_numbers(value):
    with pytest.raises(ValueError, match="finite"):
        metric().extract({"value": value})


def test_nested_dictionary_and_array_scalar_paths():
    source = sweep(lambda *args: {"observable": {"value": 2}, "per_fg": [1, 3.0]})
    spec = analysis(metrics=(
        metric(name="observable", path=("observable", "value"), unit="V",
               direction=ObjectiveDirection.MAXIMIZE),
        metric(name="second_fg", path=("per_fg", 1), unit="1", direction=None),
    ))
    result = analyze_sweep(source, spec)
    assert result.points[0].metric_values == (("observable", 2), ("second_fg", 3.0))
    assert result.feasible_count == 3
    assert result.spec.metrics[0].direction is ObjectiveDirection.MAXIMIZE


@pytest.mark.parametrize("path", [
    ("missing",), ("value", "child"), ("value", 0), ("array", 9), ("array", "key"),
])
def test_missing_wrong_container_and_out_of_range_paths_are_isolated(path):
    source = sweep(lambda *args: {"value": 1, "array": [2]})
    result = analyze_sweep(source, analysis(metrics=(metric(path=path),)))
    assert result.failure_count == 3
    assert all(p.failure_stage == "extraction" for p in result.points)


def test_numeric_dictionary_keys_are_not_implicitly_array_indices():
    definition = metric(path=("dictionary", "0"))
    assert definition.extract({"dictionary": {"0": 9}}) == 9
    with pytest.raises(TypeError, match="array"):
        metric(path=("dictionary", 0)).extract({"dictionary": {"0": 9}})


@pytest.mark.parametrize("kwargs", [
    {"name": ""}, {"name": " space"}, {"unit": ""}, {"unit": None},
    {"unit": " V"}, {"path": ()}, {"path": ("",)}, {"path": (" key",)},
    {"path": (True,)}, {"path": (-1,)}, {"path": (1.0,)},
])
def test_metric_definition_rejects_invalid_labels_units_and_paths(kwargs):
    with pytest.raises((ValueError, TypeError)):
        metric(**kwargs)


@pytest.mark.parametrize("path", ["value", b"value"])
def test_metric_path_rejects_bare_string(path):
    with pytest.raises(TypeError):
        metric(path=path)


def test_metric_path_is_snapshotted_and_direction_requires_enum():
    path = ["value"]
    definition = metric(path=path)
    path.append("changed")
    assert definition.path == ("value",)
    with pytest.raises(TypeError, match="direction"):
        metric(direction="minimize")
    assert metric(direction=None).to_dict()["direction"] is None


@pytest.mark.parametrize("kwargs", [
    {"name": ""}, {"metric_name": " spaced"}, {"unit": "K "},
    {"threshold": True}, {"threshold": "1"}, {"threshold": None},
    {"threshold": math.nan}, {"threshold": math.inf}, {"operator": "<="},
])
def test_constraint_definition_rejects_invalid_fields(kwargs):
    with pytest.raises((ValueError, TypeError)):
        constraint(**kwargs)


def test_analysis_setup_validation_and_matching_units():
    with pytest.raises(ValueError, match="at least"):
        MetricAnalysisSpec("empty", ())
    with pytest.raises(ValueError, match="metric names"):
        analysis(metrics=(metric(), metric()))
    with pytest.raises(ValueError, match="constraint names"):
        analysis(constraints=(constraint(), constraint()))
    with pytest.raises(ValueError, match="unknown"):
        analysis(constraints=(constraint(metric_name="missing"),))
    with pytest.raises(ValueError, match="unit differs"):
        analysis(constraints=(constraint(unit="k"),))
    with pytest.raises(TypeError):
        MetricAnalysisSpec("wrong", ("invalid",))
    with pytest.raises(TypeError):
        analysis(constraints=("invalid",))


def test_interval_with_contradictory_bounds_is_infeasible_not_setup_failure():
    spec = analysis(constraints=(
        constraint("lower", ConstraintOperator.GE, 400.0),
        constraint("upper", ConstraintOperator.LE, 100.0),
    ))
    result = analyze_sweep(sweep(), spec)
    assert result.infeasible_count == 3
    assert result.failure_count == 0


def test_no_constraints_treats_successful_extraction_as_feasible():
    result = analyze_sweep(sweep(), analysis())
    assert result.feasible_count == 3
    assert all(not p.constraints for p in result.points)


def test_analysis_does_not_mutate_or_rerun_source_and_exports_are_independent():
    called = []
    source = sweep(lambda d, p, point: called.append(point.index) or {"value": d.temperature_K})
    original = source.to_json()
    spec = analysis(constraints=(constraint(),))
    result = analyze_sweep(source, spec)
    assert called == [0, 1, 2]
    assert source.to_json() == original
    manifest = result.to_dict()
    manifest["points"][0]["metrics"]["temperature"] = -100
    manifest["source_sweep"]["points"][0]["output"]["value"] = -100
    assert result.points[0].metrics["temperature"] == 300
    assert source.to_json() == original
    with pytest.raises(FrozenInstanceError):
        spec.name = "changed"
    with pytest.raises(FrozenInstanceError):
        result.points[0].status = "changed"


def test_hashes_are_repeatable_and_include_source_direction_unit_and_bounds():
    source = sweep()
    spec = analysis(constraints=(constraint(),))
    a = analyze_sweep(source, spec)
    b = analyze_sweep(source, spec)
    assert a.to_json() == b.to_json()
    assert a.analysis_hash == b.analysis_hash
    assert a.result_hash == b.result_hash
    assert spec.definition_hash == canonical_hash(spec.to_dict())
    changed_direction = analysis(metrics=(metric(direction=ObjectiveDirection.MAXIMIZE),),
                                 constraints=(constraint(),))
    assert changed_direction.definition_hash != spec.definition_hash
    assert analyze_sweep(source, changed_direction).analysis_hash != a.analysis_hash
    assert analyze_sweep(source, analysis(constraints=(constraint(threshold=350),))).analysis_hash != a.analysis_hash
    changed_source = sweep(lambda *args: {"value": 300})
    assert changed_source.sweep_hash == source.sweep_hash
    assert analyze_sweep(changed_source, spec).analysis_hash != a.analysis_hash
    assert metric(unit="1").definition_hash != metric().definition_hash
    assert metric(path=("other",)).definition_hash != metric().definition_hash


def test_analysis_metric_and_constraint_order_is_preserved():
    source = sweep(lambda *args: {"value": 300, "other": 1})
    spec = analysis(
        metrics=(metric(name="other", path=("other",), unit="1"), metric()),
        constraints=(constraint("second"), constraint("first", ConstraintOperator.GE, 300)),
    )
    result = analyze_sweep(source, spec)
    assert [p.source.point.index for p in result.points] == [0, 1, 2]
    assert tuple(result.points[0].metrics) == ("other", "temperature")
    assert [c.constraint.name for c in result.points[0].constraints] == ["second", "first"]


def test_counts_provenance_and_serializable_complete_manifest():
    source = sweep()
    spec = analysis(constraints=(constraint(),))
    result = analyze_sweep(source, spec)
    manifest = json.loads(result.to_json())
    assert manifest["source_result_hash"] == source.result_hash
    assert manifest["source_sweep_hash"] == source.sweep_hash
    assert manifest["source_sweep"] == source.to_dict()
    assert sum(manifest[k] for k in ("feasible_count", "infeasible_count", "failure_count")) == 3
    assert manifest["points"][0]["point_hash"] == source.points[0].point.point_hash


def test_invalid_analysis_result_records_are_rejected():
    source = sweep()
    spec = analysis(constraints=(constraint(),))
    result = analyze_sweep(source, spec)
    with pytest.raises(ValueError, match="every"):
        MetricAnalysisResult(spec, source, result.points[:1])
    with pytest.raises(ValueError, match="order"):
        MetricAnalysisResult(spec, source, tuple(reversed(result.points)))
    with pytest.raises(ValueError, match="status"):
        replace(result.points[0], status="infeasible")
    wrong_values = replace(result.points[0], metric_values=(("unknown", 300),))
    with pytest.raises(ValueError, match="metrics differ"):
        MetricAnalysisResult(spec, source, (wrong_values, *result.points[1:]))
    with pytest.raises(ValueError, match="partial"):
        MetricPointResult(source.points[0], "failed", (("temperature", 300),),
                          failure_stage="extraction", error_type="builtins.ValueError", error_message="bad")
    with pytest.raises(ValueError, match="failure stage"):
        MetricPointResult(source.points[0], "failed", failure_stage="sweep",
                          error_type="builtins.ValueError", error_message="bad")


def test_invalid_analysis_inputs_are_setup_errors():
    with pytest.raises(TypeError):
        analyze_sweep(None, analysis())
    with pytest.raises(TypeError):
        analyze_sweep(sweep(), None)


def test_constraints_compare_large_values_without_subtraction_overflow():
    upper = MetricConstraint("upper", "x", ConstraintOperator.LE, -1e308, "1")
    lower = MetricConstraint("lower", "x", ConstraintOperator.GE, 1e308, "1")
    assert not ConstraintEvaluation(upper, 1e308).satisfied
    assert not ConstraintEvaluation(lower, -1e308).satisfied


def test_original_sweep_failure_details_survive_analysis_manifest():
    def fail(*args):
        raise RuntimeError("simulation failed")
    source = sweep(fail)
    result = analyze_sweep(source, analysis())
    assert result.failure_count == 3
    assert result.infeasible_count == 0
    manifest = json.loads(result.to_json())
    assert manifest["source_sweep"]["points"][0]["failure"]["stage"] == "evaluation"
    assert manifest["points"][0]["failure"]["stage"] == "sweep"


def test_real_program_read_metrics_use_existing_result_payload():
    device = DeviceBuilder.v2(n_fgs=1)
    protocol = ProgramPulseReadProtocol(5.0, 1e-9)
    variable = DesignVariable(
        "temperature", ParameterBinding(BindingScope.DEVICE, ("temperature_K",)),
        (300.0,), DesignVariableRole.MODEL, "K",
    )
    experiment = ExperimentSpec.from_device(name="real-g3", device=device,
                                           variables=(variable,), operating_protocol=protocol)
    source = run_cartesian_sweep(
        experiment, device,
        lambda d, p, point: run_program_pulse_read(Simulator(d), p).to_dict(),
        base_protocol=protocol, evaluation_id="program-read-defaults-v1",
    )
    spec = MetricAnalysisSpec("program-read-metrics", (
        MetricDefinition("shift", ("observable", "value"), "V", ObjectiveDirection.MAXIMIZE),
        MetricDefinition("occupation", ("mean_occupation",), "1"),
        MetricDefinition("first_fg", ("mean_occupation_by_fg", 0), "1"),
    ), (
        MetricConstraint("occupation_nonnegative", "occupation", ConstraintOperator.GE, 0, "1"),
        MetricConstraint("occupation_bounded", "occupation", ConstraintOperator.LE, 1, "1"),
    ))
    result = analyze_sweep(source, spec)
    assert result.feasible_count == 1
    assert result.points[0].metrics["shift"] == source.points[0].output["observable"]["value"]
    assert result.points[0].metrics["occupation"] == pytest.approx(result.points[0].metrics["first_fg"])


def test_objective_direction_does_not_flip_values_or_change_feasibility():
    source = sweep(lambda *args: {"value": -2.0})
    bound = constraint(threshold=-1.0)
    minimizing = analyze_sweep(source, analysis(constraints=(bound,)))
    maximizing = analyze_sweep(
        source, analysis(metrics=(metric(direction=ObjectiveDirection.MAXIMIZE),),
                         constraints=(bound,)),
    )
    assert minimizing.feasible_count == maximizing.feasible_count == 3
    assert minimizing.points[0].metrics == maximizing.points[0].metrics == {"temperature": -2.0}


def test_integer_metrics_and_thresholds_preserve_precision_above_float_range():
    exact = 2**60 + 1
    source = sweep(lambda *args: {"value": exact})
    bound = constraint(threshold=exact - 1)
    result = analyze_sweep(source, analysis(constraints=(bound,)))
    assert result.infeasible_count == 3
    assert result.points[0].metrics["temperature"] == exact
    assert type(result.points[0].metrics["temperature"]) is int
    assert json.loads(result.to_json())["points"][0]["metrics"]["temperature"] == exact


def test_definitions_snapshot_input_sequences_and_order_affects_identity():
    definitions = [metric(), metric(name="other", path=("value",), unit="1")]
    bounds = [constraint()]
    spec = MetricAnalysisSpec("snapshot", definitions, bounds)
    definitions.clear()
    bounds.clear()
    assert len(spec.metrics) == 2 and len(spec.constraints) == 1
    reordered = replace(spec, metrics=tuple(reversed(spec.metrics)))
    assert reordered.definition_hash != spec.definition_hash


def test_failed_analysis_and_feasibility_records_require_consistent_fields():
    source = sweep()
    with pytest.raises(ValueError):
        MetricPointResult(source.points[0], "feasible", (("temperature", 300),),
                          failure_stage="extraction")
    with pytest.raises(ValueError):
        MetricPointResult(source.points[0], "failed", failure_stage="extraction",
                          error_type=None, error_message="bad")
    with pytest.raises(ValueError):
        MetricPointResult(source.points[0], "unknown")
    with pytest.raises(TypeError):
        ConstraintEvaluation("invalid", 1)
    with pytest.raises(TypeError):
        ConstraintEvaluation(constraint(), True)
