from dataclasses import FrozenInstanceError, replace
import json
import random

import pytest

from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (
    BindingScope, ConstraintOperator, DesignVariable, DesignVariableRole,
    ExperimentSpec, MetricAnalysisSpec, MetricConstraint, MetricDefinition,
    ObjectiveDirection, ParameterBinding, ParetoAnalysisResult, ParetoAnalysisSpec,
    ParetoPointResult, analyze_pareto, analyze_sweep, run_cartesian_sweep,
)

MIN = ObjectiveDirection.MINIMIZE
MAX = ObjectiveDirection.MAXIMIZE


def source(vectors, directions=(MIN, MIN), constraints=()):
    device = DeviceBuilder.v2(n_fgs=1)
    variable = DesignVariable(
        "temperature", ParameterBinding(BindingScope.DEVICE, ("temperature_K",)),
        tuple(300 + i for i in range(len(vectors))), DesignVariableRole.MODEL, "K",
    )
    experiment = ExperimentSpec.from_device(name="pareto-source", device=device, variables=(variable,))
    def evaluate(d, p, point):
        vector = vectors[point.index]
        if vector is None:
            raise RuntimeError("source failed")
        return {**{f"x{i}": value for i, value in enumerate(vector)}, "report": point.index}
    sweep = run_cartesian_sweep(experiment, device, evaluate, evaluation_id="g4-test-v1")
    metrics = tuple(MetricDefinition(f"x{i}", (f"x{i}",), "1", direction)
                    for i, direction in enumerate(directions))
    return analyze_sweep(sweep, MetricAnalysisSpec(
        "source-metrics", (*metrics, MetricDefinition("report", ("report",), "1")), constraints,
    ))


@pytest.mark.parametrize("vectors,directions,fronts", [
    ([(1, 1), (2, 2), (3, 3)], (MIN, MIN), ((0,), (1,), (2,))),
    ([(1, 1), (2, 2), (3, 3)], (MAX, MAX), ((2,), (1,), (0,))),
    ([(1, 3), (2, 2), (3, 1)], (MIN, MIN), ((0, 1, 2),)),
    ([(1, 3), (2, 2), (3, 1)], (MIN, MAX), ((0,), (1,), (2,))),
    ([(1, 1), (1, 1), (2, 2)], (MIN, MIN), ((0, 1), (2,))),
    ([(1, 2), (1, 1), (2, 1)], (MIN, MIN), ((1,), (0, 2))),
    ([(5, 5)], (MIN, MAX), ((0,),)),
    ([(0, 0), (0, 0), (0, 0)], (MIN, MAX), ((0, 1, 2),)),
])
def test_exact_dominance_directions_ties_and_all_fronts(vectors, directions, fronts):
    result = analyze_pareto(source(vectors, directions))
    assert result.fronts == fronts
    assert result.pareto_indices == fronts[0]
    for rank, front in enumerate(fronts):
        assert all(result.points[i].rank == rank for i in front)


def test_excluded_points_are_retained_but_cannot_dominate_feasible_points():
    bound = MetricConstraint("minimum", "x0", ConstraintOperator.GE, 1, "1")
    analysis = source([(0, 0), (1, 1), None, ("bad", 0), (2, 2)], constraints=(bound,))
    result = analyze_pareto(analysis)
    assert result.fronts == ((1,), (4,))
    assert result.ranked_count == 2 and result.excluded_count == 3
    assert [p.exclusion_reason for p in result.points] == ["infeasible", None, "failed", "failed", None]
    assert all(result.points[i].rank is None for i in (0, 2, 3))
    assert all(not result.points[i].objective_values for i in (0, 2, 3))
    assert len(result.points) == len(analysis.points)


def test_no_feasible_points_returns_empty_fronts():
    bound = MetricConstraint("impossible", "x0", ConstraintOperator.LE, -100, "1")
    result = analyze_pareto(source([(1, 1), None], constraints=(bound,)))
    assert result.fronts == result.pareto_indices == ()
    assert result.ranked_count == 0 and result.excluded_count == 2


def test_explicit_subset_ignores_other_objectives_and_reporting_metrics():
    analysis = source([(1, 3), (2, 2), (3, 1)])
    all_objectives = analyze_pareto(analysis)
    selected = analyze_pareto(analysis, ParetoAnalysisSpec("x-only", ("x0",)))
    assert all_objectives.fronts == ((0, 1, 2),)
    assert selected.fronts == ((0,), (1,), (2,))
    assert tuple(dict(selected.points[0].objective_values)) == ("x0",)
    assert all_objectives.spec.objective_names == ("x0", "x1")


def test_directionless_unknown_or_empty_objectives_fail_setup():
    analysis = source([(1, 2)])
    for names in (("unknown",), ("report",)):
        with pytest.raises(ValueError):
            analyze_pareto(analysis, ParetoAnalysisSpec("invalid", names))
    with pytest.raises(ValueError, match="at least one"):
        analyze_pareto(source([(1, 2)], (None, None)))
    with pytest.raises(TypeError):
        analyze_pareto(None)
    with pytest.raises(TypeError):
        analyze_pareto(analysis, "invalid")


@pytest.mark.parametrize("kwargs", [
    {"name": ""}, {"name": " spaced"}, {"name": None},
    {"objective_names": ()}, {"objective_names": ("x", "x")},
    {"objective_names": ("",)}, {"objective_names": (" x",)},
    {"objective_names": (1,)}, {"objective_names": "x"},
])
def test_spec_validation(kwargs):
    with pytest.raises((TypeError, ValueError)):
        ParetoAnalysisSpec(**{"name": "pareto", "objective_names": ("x0",), **kwargs})


def test_spec_input_sequence_is_snapshotted():
    names = ["x0", "x1"]
    spec = ParetoAnalysisSpec("snapshot", names)
    names.clear()
    assert spec.objective_names == ("x0", "x1")
    with pytest.raises(FrozenInstanceError):
        spec.name = "changed"


def test_exact_integer_precision_and_extreme_values_no_float_conversion():
    huge = 2**60
    result = analyze_pareto(source([(huge + 1, -1e308), (huge, -1e308), (huge, 1e308)]))
    assert result.fronts == ((1,), (0, 2))
    assert type(dict(result.points[0].objective_values)["x0"]) is int
    maximizing = analyze_pareto(source([(-1e308, 1e308), (1e308, 1e308)], (MAX, MAX)))
    assert maximizing.pareto_indices == (1,)


def test_signed_values_are_compared_without_absolute_value_or_tolerance():
    result = analyze_pareto(source([(-2.0, 0), (-1.0, 0)]))
    assert result.fronts == ((0,), (1,))
    near = analyze_pareto(source([(1.0, 1), (1.0 + 1e-14, 1)]))
    assert near.fronts == ((0,), (1,))


def test_hashes_and_exports_are_repeatable_and_source_is_unchanged():
    analysis = source([(1, 2), (2, 1), (3, 3)])
    original = analysis.to_json()
    a = analyze_pareto(analysis)
    b = analyze_pareto(analysis)
    assert a.to_json() == b.to_json()
    assert a.analysis_hash == b.analysis_hash and a.result_hash == b.result_hash
    assert analysis.to_json() == original
    exported = a.to_dict()
    exported["fronts"][0].append(999)
    exported["points"][0]["objectives"]["x0"] = 999
    assert a.fronts == ((0, 1), (2,))
    assert dict(a.points[0].objective_values)["x0"] == 1
    manifest = json.loads(a.to_json())
    assert manifest["source_result_hash"] == analysis.result_hash
    assert manifest["source_analysis"] == analysis.to_dict()
    assert manifest["objectives"][0]["direction"] == "minimize"
    assert manifest["points"][0]["point_hash"] == analysis.points[0].source.point.point_hash


def test_identity_includes_selection_order_direction_and_source_results():
    analysis = source([(1, 2), (2, 1)])
    a = analyze_pareto(analysis)
    reordered = analyze_pareto(analysis, ParetoAnalysisSpec("pareto", ("x1", "x0")))
    assert reordered.fronts == a.fronts
    assert reordered.spec.definition_hash != a.spec.definition_hash
    assert reordered.analysis_hash != a.analysis_hash
    changed_direction = analyze_pareto(source([(1, 2), (2, 1)], (MAX, MIN)))
    changed_source = analyze_pareto(source([(2, 3), (3, 2)]))
    assert changed_direction.analysis_hash != a.analysis_hash
    assert changed_source.analysis_hash != a.analysis_hash


def reference_fronts(vectors, directions):
    # Independent repeated-front extraction; no domination graph or rank propagation.
    remaining = list(range(len(vectors)))
    fronts = []
    while remaining:
        front = []
        for candidate in remaining:
            dominated = False
            for other in remaining:
                comparisons = [
                    (a <= b, a < b) if d is MIN else (a >= b, a > b)
                    for a, b, d in zip(vectors[other], vectors[candidate], directions)
                ]
                if all(pair[0] for pair in comparisons) and any(pair[1] for pair in comparisons):
                    dominated = True
                    break
            if not dominated:
                front.append(candidate)
        fronts.append(tuple(front))
        remaining = [i for i in remaining if i not in front]
    return tuple(fronts)


@pytest.mark.parametrize("seed", range(20))
def test_random_small_grids_match_independent_reference(seed):
    rng = random.Random(seed)
    directions = tuple(rng.choice((MIN, MAX)) for _ in range(rng.randint(1, 4)))
    vectors = [tuple(rng.randint(-3, 3) for _ in directions)
               for _ in range(rng.randint(2, 15))]
    result = analyze_pareto(source(vectors, directions))
    assert result.fronts == reference_fronts(vectors, directions)


def test_permutation_preserves_front_membership_but_respects_new_source_order():
    vectors = [(1, 3), (2, 2), (3, 1), (4, 4)]
    original = analyze_pareto(source(vectors))
    order = (3, 2, 0, 1)
    changed = analyze_pareto(source([vectors[i] for i in order]))
    assert changed.fronts == ((1, 2, 3), (0,))
    assert {order[i] for i in changed.pareto_indices} == set(original.pareto_indices)


def test_public_result_records_reject_incomplete_or_inconsistent_fronts():
    analysis = source([(1, 1), (2, 2)])
    result = analyze_pareto(analysis)
    with pytest.raises(ValueError, match="every source"):
        ParetoAnalysisResult(result.spec, analysis, result.points[:1], result.fronts)
    with pytest.raises(ValueError, match="partition"):
        replace(result, fronts=((0,),))
    with pytest.raises(ValueError):
        replace(result, fronts=((0, 0), (1,)))
    with pytest.raises(ValueError):
        replace(result, fronts=((), (0, 1)))
    with pytest.raises(ValueError, match="order"):
        replace(result, points=tuple(reversed(result.points)))
    with pytest.raises(ValueError):
        ParetoPointResult(analysis.points[0], True, (("x0", 1),))
    with pytest.raises(ValueError):
        ParetoPointResult(analysis.points[0], 0, (("x0", 999),))


def test_failed_points_cannot_be_given_a_rank():
    analysis = source([None, (1, 1)])
    with pytest.raises(ValueError, match="excluded"):
        ParetoPointResult(analysis.points[0], 0)
