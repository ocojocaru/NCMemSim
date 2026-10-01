# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import Mock

import pytest

from ncmemsim.dtco import ConstraintOperator, SweepPoint
from ncmemsim.dtco.metrics import (
    MetricAnalysisSpec,
    MetricDefinition,
    ObjectiveDirection,
)
from ncmemsim.ensemble.dtco import (
    EnsembleConstraint,
    EnsembleConstraintEvaluation,
    EnsembleDTCOStudy,
    EnsembleEligibilityResult,
    EnsembleObjective,
    EnsembleParetoAnalysisResult,
    EnsembleParetoPointResult,
    EnsembleScalarDefinition,
    EnsembleScalarEvaluation,
    EnsembleScalarKind,
    analyze_ensemble_pareto,
    evaluate_ensemble_constraint,
    evaluate_ensemble_eligibility,
    evaluate_ensemble_scalar,
)
from ncmemsim.ensemble.feasibility import (
    EnsembleFeasibilitySummary,
)
from ncmemsim.ensemble.statistics import (
    EnsemblePopulationStatistics,
    EnsembleStatisticsSpec,
    MetricPopulationSummary,
)


@pytest.fixture(scope="module")
def source():
    result = Mock(spec=EnsembleFeasibilitySummary)
    result.result_hash = "b" * 64
    return result


def point(
    index=0,
    value=1.0,
    experiment_hash="a" * 64,
):
    return SweepPoint(
        experiment_hash,
        index,
        (("x", value),),
    )


def test_study_links_existing_dtco_point_and_k4_result(source):
    design_point = point()
    study = EnsembleDTCOStudy(
        design_point,
        source,
    )

    assert study.design_point is design_point
    assert study.source is source
    assert study.experiment_hash == design_point.experiment_hash
    assert study.point_hash == design_point.point_hash
    assert study.index == design_point.index
    assert study.assignments == {"x": 1.0}
    assert study.source_result_hash == source.result_hash

    payload = study.to_dict()
    assert payload["schema_version"] == "ensemble-dtco-study-v1"
    assert payload["design_point"] == design_point.to_dict()
    assert payload["point_hash"] == design_point.point_hash
    assert payload["source_result_hash"] == source.result_hash


def test_study_assignments_are_not_an_authoritative_duplicate(source):
    study = EnsembleDTCOStudy(
        point(),
        source,
    )

    assignments = study.assignments
    assignments["x"] = 99.0

    assert study.assignments == {"x": 1.0}
    assert study.design_point.assignments == {"x": 1.0}


@pytest.mark.parametrize(
    "design_point",
    [
        None,
        object(),
        "point",
    ],
)
def test_study_rejects_invalid_design_point(
    source,
    design_point,
):
    with pytest.raises(TypeError, match="SweepPoint"):
        EnsembleDTCOStudy(
            design_point,
            source,
        )


@pytest.mark.parametrize(
    "bad_source",
    [
        None,
        object(),
        {},
    ],
)
def test_study_rejects_invalid_source(
    bad_source,
):
    with pytest.raises(
        TypeError,
        match="EnsembleFeasibilitySummary",
    ):
        EnsembleDTCOStudy(
            point(),
            bad_source,
        )


def test_study_hash_is_deterministic_and_sensitive(
    source,
):
    baseline = EnsembleDTCOStudy(
        point(),
        source,
    )
    same = EnsembleDTCOStudy(
        point(),
        source,
    )
    changed_point = EnsembleDTCOStudy(
        point(index=1),
        source,
    )
    alternate_source = Mock(
        spec=EnsembleFeasibilitySummary,
    )
    alternate_source.result_hash = "c" * 64
    changed_source = EnsembleDTCOStudy(
        point(),
        alternate_source,
    )

    assert baseline.study_hash == same.study_hash
    assert baseline.study_hash != changed_point.study_hash
    assert baseline.study_hash != changed_source.study_hash


def test_scalar_kind_contract_is_explicit_and_excludes_variance():
    assert tuple(
        kind.value
        for kind in EnsembleScalarKind
    ) == (
        "mean",
        "standard_deviation",
        "minimum",
        "maximum",
        "median",
        "quantile",
        "coverage_fraction",
        "simulated_pass_fraction",
        "ensemble_feasibility_fraction",
        "failure_fraction",
    )
    assert not hasattr(
        EnsembleScalarKind,
        "VARIANCE",
    )


@pytest.mark.parametrize(
    "kind",
    [
        EnsembleScalarKind.MEAN,
        EnsembleScalarKind.STANDARD_DEVIATION,
        EnsembleScalarKind.MINIMUM,
        EnsembleScalarKind.MAXIMUM,
        EnsembleScalarKind.MEDIAN,
    ],
)
def test_metric_scalar_definition_accepts_declared_unit(
    kind,
):
    definition = EnsembleScalarDefinition(
        name=f"response_{kind.value}",
        kind=kind,
        unit="V",
        metric_name="response",
    )

    assert definition.metric_name == "response"
    assert definition.unit == "V"
    assert definition.quantile is None


def test_quantile_scalar_normalizes_probability():
    definition = EnsembleScalarDefinition(
        name="response_p05",
        kind=EnsembleScalarKind.QUANTILE,
        unit="V",
        metric_name="response",
        quantile=0.05,
    )

    assert definition.quantile == 0.05
    assert type(definition.quantile) is float


@pytest.mark.parametrize(
    "quantile",
    [
        None,
        True,
        "0.5",
        -0.01,
        1.01,
        float("nan"),
        float("inf"),
    ],
)
def test_quantile_scalar_rejects_invalid_probability(
    quantile,
):
    with pytest.raises(
        ValueError,
        match="finite probability",
    ):
        EnsembleScalarDefinition(
            name="response_quantile",
            kind=EnsembleScalarKind.QUANTILE,
            unit="V",
            metric_name="response",
            quantile=quantile,
        )


def test_nonquantile_metric_rejects_quantile_probability():
    with pytest.raises(
        ValueError,
        match="only valid for QUANTILE",
    ):
        EnsembleScalarDefinition(
            name="response_mean",
            kind=EnsembleScalarKind.MEAN,
            unit="V",
            metric_name="response",
            quantile=0.5,
        )


@pytest.mark.parametrize(
    "kind",
    [
        EnsembleScalarKind.MEAN,
        EnsembleScalarKind.QUANTILE,
    ],
)
def test_metric_scalar_requires_metric_name(
    kind,
):
    kwargs = (
        {"quantile": 0.5}
        if kind is EnsembleScalarKind.QUANTILE
        else {}
    )

    with pytest.raises(
        ValueError,
        match="requires metric_name",
    ):
        EnsembleScalarDefinition(
            name="metric_scalar",
            kind=kind,
            unit="V",
            **kwargs,
        )


@pytest.mark.parametrize(
    "kind",
    [
        EnsembleScalarKind.COVERAGE_FRACTION,
        EnsembleScalarKind.SIMULATED_PASS_FRACTION,
        EnsembleScalarKind.ENSEMBLE_FEASIBILITY_FRACTION,
        EnsembleScalarKind.FAILURE_FRACTION,
    ],
)
def test_fraction_scalar_is_explicitly_dimensionless(
    kind,
):
    definition = EnsembleScalarDefinition(
        name=kind.value,
        kind=kind,
        unit="1",
    )

    assert definition.metric_name is None
    assert definition.quantile is None
    assert definition.unit == "1"


@pytest.mark.parametrize(
    "kwargs,match",
    [
        (
            {"metric_name": "response"},
            "cannot declare metric_name",
        ),
        (
            {"quantile": 0.5},
            "cannot declare quantile",
        ),
        (
            {"unit": "V"},
            "requires unit '1'",
        ),
    ],
)
def test_fraction_scalar_rejects_metric_quantile_or_unit(
    kwargs,
    match,
):
    values = {
        "name": "failure_fraction",
        "kind": EnsembleScalarKind.FAILURE_FRACTION,
        "unit": "1",
    }
    values.update(kwargs)

    with pytest.raises(
        ValueError,
        match=match,
    ):
        EnsembleScalarDefinition(**values)


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "name": "",
            "kind": EnsembleScalarKind.MEAN,
            "unit": "V",
            "metric_name": "response",
        },
        {
            "name": " mean",
            "kind": EnsembleScalarKind.MEAN,
            "unit": "V",
            "metric_name": "response",
        },
        {
            "name": "mean",
            "kind": EnsembleScalarKind.MEAN,
            "unit": "",
            "metric_name": "response",
        },
        {
            "name": "mean",
            "kind": EnsembleScalarKind.MEAN,
            "unit": "V",
            "metric_name": " response",
        },
    ],
)
def test_scalar_definition_rejects_invalid_labels(
    kwargs,
):
    with pytest.raises(ValueError):
        EnsembleScalarDefinition(**kwargs)


def test_scalar_definition_requires_typed_kind():
    with pytest.raises(
        TypeError,
        match="EnsembleScalarKind",
    ):
        EnsembleScalarDefinition(
            name="response_mean",
            kind="mean",
            unit="V",
            metric_name="response",
        )


def test_scalar_definition_serialization_and_hash_are_deterministic():
    first = EnsembleScalarDefinition(
        name="response_p95",
        kind=EnsembleScalarKind.QUANTILE,
        unit="V",
        metric_name="response",
        quantile=0.95,
    )
    same = EnsembleScalarDefinition(
        name="response_p95",
        kind=EnsembleScalarKind.QUANTILE,
        unit="V",
        metric_name="response",
        quantile=0.95,
    )
    changed = EnsembleScalarDefinition(
        name="response_p50",
        kind=EnsembleScalarKind.QUANTILE,
        unit="V",
        metric_name="response",
        quantile=0.5,
    )

    assert first.to_dict() == {
        "schema_version": "ensemble-scalar-definition-v1",
        "name": "response_p95",
        "kind": "quantile",
        "metric_name": "response",
        "unit": "V",
        "quantile": 0.95,
    }
    assert first.definition_hash == same.definition_hash
    assert first.definition_hash != changed.definition_hash

def evaluation_study(
    *,
    denominator=3,
    ensemble_feasibility_fraction=2.0 / 3.0,
):
    empty = denominator == 0
    summary = MetricPopulationSummary(
        metric_name="response",
        unit="V",
        denominator=denominator,
        sample_indices=() if empty else (0, 1, 2),
        realization_ids=() if empty else ("r0", "r1", "r2"),
        minimum=None if empty else 1.0,
        maximum=None if empty else 3.0,
        mean=None if empty else 2.0,
        variance=None if empty else 1.0,
        standard_deviation=None if empty else 1.0,
        median=None if empty else 2.0,
        quantiles=(
            (0.05, None if empty else 1.1),
            (0.5, None if empty else 2.0),
            (0.95, None if empty else 2.9),
        ),
    )

    statistics = Mock(spec=EnsemblePopulationStatistics)
    statistics.metric_statistics = (summary,)
    statistics.coverage_fraction = 0.0 if empty else 0.75

    source = Mock(spec=EnsembleFeasibilitySummary)
    source.source = statistics
    source.simulated_pass_fraction = 0.0 if empty else 0.5
    source.ensemble_feasibility_fraction = ensemble_feasibility_fraction
    source.failure_fraction = 1.0 if empty else 0.25
    source.result_hash = "d" * 64

    return EnsembleDTCOStudy(point(), source)


def metric_definition(kind, *, quantile=None, unit="V", metric_name="response"):
    return EnsembleScalarDefinition(
        name=f"test_{kind.value}",
        kind=kind,
        unit=unit,
        metric_name=metric_name,
        quantile=quantile,
    )


@pytest.mark.parametrize(
    "kind,expected",
    [
        (EnsembleScalarKind.MEAN, 2.0),
        (EnsembleScalarKind.STANDARD_DEVIATION, 1.0),
        (EnsembleScalarKind.MINIMUM, 1.0),
        (EnsembleScalarKind.MAXIMUM, 3.0),
        (EnsembleScalarKind.MEDIAN, 2.0),
    ],
)
def test_evaluate_metric_scalar_reads_k4_summary(kind, expected):
    result = evaluate_ensemble_scalar(
        evaluation_study(),
        metric_definition(kind),
    )
    assert result.status == "defined"
    assert result.value == expected
    assert type(result.value) is float


def test_evaluate_quantile_requires_existing_k4_probability():
    study = evaluation_study()
    result = evaluate_ensemble_scalar(
        study,
        metric_definition(
            EnsembleScalarKind.QUANTILE,
            quantile=0.95,
        ),
    )
    assert result.value == 2.9

    with pytest.raises(ValueError, match="not declared"):
        evaluate_ensemble_scalar(
            study,
            metric_definition(
                EnsembleScalarKind.QUANTILE,
                quantile=0.25,
            ),
        )


def test_evaluate_metric_rejects_absent_metric_and_unit_mismatch():
    study = evaluation_study()

    with pytest.raises(ValueError, match="absent from source statistics"):
        evaluate_ensemble_scalar(
            study,
            metric_definition(
                EnsembleScalarKind.MEAN,
                metric_name="missing",
            ),
        )

    with pytest.raises(ValueError, match="uses unit"):
        evaluate_ensemble_scalar(
            study,
            metric_definition(
                EnsembleScalarKind.MEAN,
                unit="mV",
            ),
        )


@pytest.mark.parametrize(
    "kind,expected",
    [
        (EnsembleScalarKind.COVERAGE_FRACTION, 0.75),
        (EnsembleScalarKind.SIMULATED_PASS_FRACTION, 0.5),
        (EnsembleScalarKind.ENSEMBLE_FEASIBILITY_FRACTION, 2.0 / 3.0),
        (EnsembleScalarKind.FAILURE_FRACTION, 0.25),
    ],
)
def test_evaluate_fraction_scalar_reads_k4_value(kind, expected):
    result = evaluate_ensemble_scalar(
        evaluation_study(),
        EnsembleScalarDefinition(
            name=kind.value,
            kind=kind,
            unit="1",
        ),
    )
    assert result.status == "defined"
    assert result.value == expected
    assert type(result.value) is float


@pytest.mark.parametrize(
    "definition",
    [
        metric_definition(EnsembleScalarKind.MEAN),
        metric_definition(
            EnsembleScalarKind.QUANTILE,
            quantile=0.95,
        ),
    ],
)
def test_empty_metric_population_is_undefined(definition):
    result = evaluate_ensemble_scalar(
        evaluation_study(
            denominator=0,
            ensemble_feasibility_fraction=None,
        ),
        definition,
    )
    assert result.status == "undefined"
    assert result.value is None


def test_zero_assessed_feasibility_is_undefined_but_other_fractions_are_defined():
    study = evaluation_study(
        denominator=0,
        ensemble_feasibility_fraction=None,
    )

    feasibility = evaluate_ensemble_scalar(
        study,
        EnsembleScalarDefinition(
            name="ensemble_feasibility_fraction",
            kind=EnsembleScalarKind.ENSEMBLE_FEASIBILITY_FRACTION,
            unit="1",
        ),
    )
    assert feasibility.status == "undefined"
    assert feasibility.value is None

    for kind, expected in (
        (EnsembleScalarKind.COVERAGE_FRACTION, 0.0),
        (EnsembleScalarKind.SIMULATED_PASS_FRACTION, 0.0),
        (EnsembleScalarKind.FAILURE_FRACTION, 1.0),
    ):
        result = evaluate_ensemble_scalar(
            study,
            EnsembleScalarDefinition(
                name=kind.value,
                kind=kind,
                unit="1",
            ),
        )
        assert result.status == "defined"
        assert result.value == expected


@pytest.mark.parametrize(
    "status,value",
    [
        ("invalid", None),
        ("defined", None),
        ("defined", 1),
        ("defined", float("nan")),
        ("undefined", 1.0),
    ],
)
def test_scalar_evaluation_rejects_invalid_state(status, value):
    with pytest.raises((TypeError, ValueError)):
        EnsembleScalarEvaluation(
            study=evaluation_study(),
            definition=metric_definition(EnsembleScalarKind.MEAN),
            status=status,
            value=value,
        )


def test_scalar_evaluation_serialization_and_hash_are_deterministic():
    study = evaluation_study()
    definition = metric_definition(EnsembleScalarKind.MEAN)
    first = evaluate_ensemble_scalar(study, definition)
    same = evaluate_ensemble_scalar(study, definition)
    payload = first.to_dict()

    assert payload["schema_version"] == "ensemble-scalar-evaluation-v1"
    assert payload["study_hash"] == study.study_hash
    assert payload["definition"] == definition.to_dict()
    assert payload["definition_hash"] == definition.definition_hash
    assert payload["status"] == "defined"
    assert payload["value"] == 2.0
    assert first.evaluation_hash == same.evaluation_hash


def constraint_definition(
    *,
    name="response_max",
    scalar=None,
    operator=ConstraintOperator.LE,
    threshold=2.0,
    unit="V",
):
    if scalar is None:
        scalar = metric_definition(
            EnsembleScalarKind.MEAN,
        )
    return EnsembleConstraint(
        name=name,
        scalar=scalar,
        operator=operator,
        threshold=threshold,
        unit=unit,
    )


@pytest.mark.parametrize(
    "operator,threshold,expected",
    [
        (ConstraintOperator.LE, 2.0, "satisfied"),
        (ConstraintOperator.LE, 1.999, "violated"),
        (ConstraintOperator.GE, 2.0, "satisfied"),
        (ConstraintOperator.GE, 2.001, "violated"),
    ],
)
def test_constraint_evaluation_uses_inclusive_dtco_operator(
    operator,
    threshold,
    expected,
):
    result = evaluate_ensemble_constraint(
        evaluation_study(),
        constraint_definition(
            operator=operator,
            threshold=threshold,
        ),
    )
    assert result.status == expected
    assert result.scalar_evaluation.status == "defined"
    assert result.scalar_evaluation.value == 2.0


def test_constraint_evaluation_preserves_undefined_as_unevaluable():
    result = evaluate_ensemble_constraint(
        evaluation_study(
            denominator=0,
            ensemble_feasibility_fraction=None,
        ),
        constraint_definition(),
    )
    assert result.status == "unevaluable"
    assert result.scalar_evaluation.status == "undefined"
    assert result.scalar_evaluation.value is None


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"name": ""}, ValueError),
        ({"scalar": object()}, TypeError),
        ({"operator": "<="}, TypeError),
        ({"threshold": True}, TypeError),
        ({"threshold": float("nan")}, ValueError),
        ({"unit": "mV"}, ValueError),
    ],
)
def test_constraint_definition_rejects_invalid_contract(kwargs, error):
    base = {
        "name": "response_max",
        "scalar": metric_definition(
            EnsembleScalarKind.MEAN,
        ),
        "operator": ConstraintOperator.LE,
        "threshold": 2.0,
        "unit": "V",
    }
    base.update(kwargs)
    with pytest.raises(error):
        EnsembleConstraint(**base)


def test_constraint_definition_serialization_and_hash_are_deterministic():
    first = constraint_definition()
    same = constraint_definition()
    changed = constraint_definition(
        threshold=2.5,
    )
    payload = first.to_dict()

    assert payload["schema_version"] == "ensemble-constraint-v1"
    assert payload["name"] == "response_max"
    assert payload["scalar"] == first.scalar.to_dict()
    assert payload["scalar_definition_hash"] == (
        first.scalar.definition_hash
    )
    assert payload["operator"] == "<="
    assert payload["threshold"] == 2.0
    assert payload["unit"] == "V"
    assert first.definition_hash == same.definition_hash
    assert first.definition_hash != changed.definition_hash


def test_constraint_evaluation_rejects_status_inconsistent_with_scalar():
    study = evaluation_study()
    constraint = constraint_definition()
    scalar = evaluate_ensemble_scalar(
        study,
        constraint.scalar,
    )
    with pytest.raises(
        ValueError,
        match="status differs",
    ):
        EnsembleConstraintEvaluation(
            constraint=constraint,
            scalar_evaluation=scalar,
            status="violated",
        )


def test_constraint_evaluation_serialization_and_hash_are_deterministic():
    study = evaluation_study()
    constraint = constraint_definition()
    first = evaluate_ensemble_constraint(
        study,
        constraint,
    )
    same = evaluate_ensemble_constraint(
        study,
        constraint,
    )
    payload = first.to_dict()

    assert payload["schema_version"] == (
        "ensemble-constraint-evaluation-v1"
    )
    assert payload["study_hash"] == study.study_hash
    assert payload["constraint"] == constraint.to_dict()
    assert payload["constraint_hash"] == (
        constraint.definition_hash
    )
    assert payload["scalar_evaluation_hash"] == (
        first.scalar_evaluation.evaluation_hash
    )
    assert payload["status"] == "satisfied"
    assert payload["value"] == 2.0
    assert first.evaluation_hash == same.evaluation_hash


def test_eligibility_is_eligible_when_all_constraints_are_satisfied():
    study = evaluation_study()
    constraints = (
        constraint_definition(
            name="mean_max",
            operator=ConstraintOperator.LE,
            threshold=2.0,
        ),
        constraint_definition(
            name="mean_min",
            operator=ConstraintOperator.GE,
            threshold=1.5,
        ),
    )
    result = evaluate_ensemble_eligibility(
        study,
        constraints,
    )

    assert result.status == "eligible"
    assert tuple(
        evaluation.status
        for evaluation in result.evaluations
    ) == ("satisfied", "satisfied")


def test_eligibility_is_ineligible_when_any_constraint_is_violated():
    study = evaluation_study()
    result = evaluate_ensemble_eligibility(
        study,
        (
            constraint_definition(
                name="mean_ok",
                threshold=2.0,
            ),
            constraint_definition(
                name="mean_too_low_max",
                threshold=1.5,
            ),
        ),
    )

    assert result.status == "ineligible"
    assert tuple(
        evaluation.status
        for evaluation in result.evaluations
    ) == ("satisfied", "violated")


def test_unevaluable_precedes_violated_at_study_level():
    study = evaluation_study(
        denominator=0,
        ensemble_feasibility_fraction=None,
    )
    undefined_scalar = EnsembleScalarDefinition(
        name="assessed_feasibility",
        kind=(
            EnsembleScalarKind
            .ENSEMBLE_FEASIBILITY_FRACTION
        ),
        unit="1",
    )
    coverage_scalar = EnsembleScalarDefinition(
        name="coverage",
        kind=EnsembleScalarKind.COVERAGE_FRACTION,
        unit="1",
    )
    result = evaluate_ensemble_eligibility(
        study,
        (
            EnsembleConstraint(
                name="coverage_min",
                scalar=coverage_scalar,
                operator=ConstraintOperator.GE,
                threshold=0.5,
                unit="1",
            ),
            EnsembleConstraint(
                name="assessed_feasibility_min",
                scalar=undefined_scalar,
                operator=ConstraintOperator.GE,
                threshold=0.5,
                unit="1",
            ),
        ),
    )

    assert tuple(
        evaluation.status
        for evaluation in result.evaluations
    ) == ("violated", "unevaluable")
    assert result.status == "unevaluable"


def test_eligibility_rejects_duplicate_constraint_names():
    study = evaluation_study()
    first = constraint_definition(
        name="duplicate",
        threshold=2.0,
    )
    second = constraint_definition(
        name="duplicate",
        threshold=2.5,
    )
    with pytest.raises(
        ValueError,
        match="constraint names must be unique",
    ):
        evaluate_ensemble_eligibility(
            study,
            (first, second),
        )


def test_eligibility_serialization_and_hash_are_deterministic():
    study = evaluation_study()
    constraints = (
        constraint_definition(
            name="mean_max",
            threshold=2.0,
        ),
        constraint_definition(
            name="mean_min",
            operator=ConstraintOperator.GE,
            threshold=1.0,
        ),
    )
    first = evaluate_ensemble_eligibility(
        study,
        constraints,
    )
    same = evaluate_ensemble_eligibility(
        study,
        constraints,
    )
    payload = first.to_dict()

    assert payload["schema_version"] == (
        "ensemble-eligibility-result-v1"
    )
    assert payload["study_hash"] == study.study_hash
    assert payload["status"] == "eligible"
    assert len(payload["evaluations"]) == 2
    assert first.result_hash == same.result_hash


def test_eligibility_result_rejects_invalid_status():
    with pytest.raises(
        ValueError,
        match="status must be eligible",
    ):
        EnsembleEligibilityResult(
            study=evaluation_study(),
            evaluations=(),
            status="invalid",
        )



def pareto_study(
    *,
    index=0,
    mean=2.0,
    denominator=3,
    metric_path=("response",),
    metric_direction=None,
    statistics_quantiles=(0.05, 0.5, 0.95),
    coverage_fraction=0.75,
    simulated_pass_fraction=0.5,
    ensemble_feasibility_fraction=2.0 / 3.0,
    failure_fraction=0.25,
):
    empty = denominator == 0
    quantiles = tuple(
        (
            probability,
            None if empty else float(mean),
        )
        for probability in statistics_quantiles
    )
    summary = MetricPopulationSummary(
        metric_name="response",
        unit="V",
        denominator=denominator,
        sample_indices=() if empty else (0, 1, 2),
        realization_ids=() if empty else ("r0", "r1", "r2"),
        minimum=None if empty else float(mean - 1.0),
        maximum=None if empty else float(mean + 1.0),
        mean=None if empty else float(mean),
        variance=None if empty else 1.0,
        standard_deviation=None if empty else 1.0,
        median=None if empty else float(mean),
        quantiles=quantiles,
    )

    metric = MetricDefinition(
        name="response",
        path=metric_path,
        unit="V",
        direction=metric_direction,
    )
    metric_analysis = Mock()
    metric_analysis.spec = MetricAnalysisSpec(
        name="pareto-source",
        metrics=(metric,),
    )

    statistics = Mock(spec=EnsemblePopulationStatistics)
    statistics.spec = EnsembleStatisticsSpec(
        quantiles=statistics_quantiles,
    )
    statistics.source = metric_analysis
    statistics.metric_statistics = (summary,)
    statistics.coverage_fraction = coverage_fraction

    source = Mock(spec=EnsembleFeasibilitySummary)
    source.source = statistics
    source.simulated_pass_fraction = simulated_pass_fraction
    source.ensemble_feasibility_fraction = (
        ensemble_feasibility_fraction
    )
    source.failure_fraction = failure_fraction
    source.result_hash = f"{index + 1:064x}"

    return EnsembleDTCOStudy(
        point(
            index=index,
            value=float(index + 1),
        ),
        source,
    )


def pareto_objective(
    kind=EnsembleScalarKind.MEAN,
    *,
    name="response_mean",
    direction=ObjectiveDirection.MINIMIZE,
    quantile=None,
):
    if kind in (
        EnsembleScalarKind.COVERAGE_FRACTION,
        EnsembleScalarKind.SIMULATED_PASS_FRACTION,
        EnsembleScalarKind.ENSEMBLE_FEASIBILITY_FRACTION,
        EnsembleScalarKind.FAILURE_FRACTION,
    ):
        scalar = EnsembleScalarDefinition(
            name=f"test_{kind.value}",
            kind=kind,
            unit="1",
        )
    else:
        scalar = metric_definition(
            kind,
            quantile=quantile,
        )
    return EnsembleObjective(
        name=name,
        scalar=scalar,
        direction=direction,
    )


def eligible_result(study):
    return evaluate_ensemble_eligibility(
        study,
        (),
    )


def ineligible_result(study):
    return evaluate_ensemble_eligibility(
        study,
        (
            EnsembleConstraint(
                name="mean_too_high",
                scalar=metric_definition(
                    EnsembleScalarKind.MEAN,
                ),
                operator=ConstraintOperator.LE,
                threshold=-1.0,
                unit="V",
            ),
        ),
    )


def unevaluable_result(study):
    scalar = EnsembleScalarDefinition(
        name="assessed_feasibility",
        kind=(
            EnsembleScalarKind
            .ENSEMBLE_FEASIBILITY_FRACTION
        ),
        unit="1",
    )
    return evaluate_ensemble_eligibility(
        study,
        (
            EnsembleConstraint(
                name="assessed_feasibility_min",
                scalar=scalar,
                operator=ConstraintOperator.GE,
                threshold=0.5,
                unit="1",
            ),
        ),
    )


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"name": ""}, ValueError),
        ({"scalar": object()}, TypeError),
        ({"direction": "minimize"}, TypeError),
    ],
)
def test_pareto_objective_rejects_invalid_contract(kwargs, error):
    base = {
        "name": "response_mean",
        "scalar": metric_definition(
            EnsembleScalarKind.MEAN,
        ),
        "direction": ObjectiveDirection.MINIMIZE,
    }
    base.update(kwargs)
    with pytest.raises(error):
        EnsembleObjective(**base)


def test_pareto_objective_serialization_and_hash_are_deterministic():
    first = pareto_objective()
    same = pareto_objective()
    changed = pareto_objective(
        direction=ObjectiveDirection.MAXIMIZE,
    )
    payload = first.to_dict()

    assert payload["schema_version"] == "ensemble-objective-v1"
    assert payload["name"] == "response_mean"
    assert payload["scalar"] == first.scalar.to_dict()
    assert payload["scalar_definition_hash"] == (
        first.scalar.definition_hash
    )
    assert payload["direction"] == "minimize"
    assert first.definition_hash == same.definition_hash
    assert first.definition_hash != changed.definition_hash


def test_pareto_minimize_builds_all_fronts_from_rank_zero():
    sources = tuple(
        eligible_result(
            pareto_study(
                index=index,
                mean=mean,
            )
        )
        for index, mean in enumerate((1.0, 2.0, 3.0))
    )
    result = analyze_ensemble_pareto(
        sources,
        (pareto_objective(),),
    )

    assert result.fronts == ((0,), (1,), (2,))
    assert tuple(
        point.rank for point in result.points
    ) == (0, 1, 2)
    assert result.pareto_indices == (0,)
    assert result.ranked_count == 3
    assert result.excluded_count == 0


def test_pareto_maximize_reverses_exact_dominance_direction():
    sources = tuple(
        eligible_result(
            pareto_study(
                index=index,
                mean=mean,
            )
        )
        for index, mean in enumerate((1.0, 2.0, 3.0))
    )
    result = analyze_ensemble_pareto(
        sources,
        (
            pareto_objective(
                direction=ObjectiveDirection.MAXIMIZE,
            ),
        ),
    )

    assert result.fronts == ((2,), (1,), (0,))
    assert tuple(
        point.rank for point in result.points
    ) == (2, 1, 0)


def test_pareto_retains_equal_objective_vectors_as_ties():
    sources = tuple(
        eligible_result(
            pareto_study(
                index=index,
                mean=mean,
            )
        )
        for index, mean in enumerate((1.0, 1.0, 2.0))
    )
    result = analyze_ensemble_pareto(
        sources,
        (pareto_objective(),),
    )

    assert result.fronts == ((0, 1), (2,))
    assert result.pareto_indices == (0, 1)
    assert tuple(
        point.rank for point in result.points
    ) == (0, 0, 1)


def test_pareto_exact_multiobjective_tradeoff_retains_nondominated_points():
    studies = (
        pareto_study(
            index=0,
            mean=1.0,
            failure_fraction=0.4,
        ),
        pareto_study(
            index=1,
            mean=2.0,
            failure_fraction=0.1,
        ),
        pareto_study(
            index=2,
            mean=3.0,
            failure_fraction=0.5,
        ),
    )
    sources = tuple(
        eligible_result(study)
        for study in studies
    )
    result = analyze_ensemble_pareto(
        sources,
        (
            pareto_objective(),
            pareto_objective(
                EnsembleScalarKind.FAILURE_FRACTION,
                name="failure_fraction",
                direction=ObjectiveDirection.MINIMIZE,
            ),
        ),
    )

    assert result.fronts == ((0, 1), (2,))
    assert result.pareto_indices == (0, 1)


def test_pareto_preserves_distinct_exclusion_reasons():
    ranked = eligible_result(
        pareto_study(
            index=0,
            mean=1.0,
        )
    )
    constraint_ineligible = ineligible_result(
        pareto_study(
            index=1,
            mean=2.0,
        )
    )
    constraint_unevaluable = unevaluable_result(
        pareto_study(
            index=2,
            denominator=0,
            ensemble_feasibility_fraction=None,
        )
    )
    objective_unevaluable = eligible_result(
        pareto_study(
            index=3,
            denominator=0,
            ensemble_feasibility_fraction=None,
        )
    )

    result = analyze_ensemble_pareto(
        (
            ranked,
            constraint_ineligible,
            constraint_unevaluable,
            objective_unevaluable,
        ),
        (pareto_objective(),),
    )

    assert tuple(
        point.exclusion_reason
        for point in result.points
    ) == (
        None,
        "constraint-ineligible",
        "constraint-unevaluable",
        "objective-unevaluable",
    )
    assert tuple(
        point.rank for point in result.points
    ) == (0, None, None, None)
    assert result.fronts == ((0,),)
    assert result.ranked_count == 1
    assert result.excluded_count == 3


def test_pareto_rejects_incompatible_selected_metric_definitions():
    sources = (
        eligible_result(
            pareto_study(
                index=0,
                metric_path=("response",),
            )
        ),
        eligible_result(
            pareto_study(
                index=1,
                metric_path=("other_response",),
            )
        ),
    )

    with pytest.raises(
        ValueError,
        match="incompatible source definitions",
    ):
        analyze_ensemble_pareto(
            sources,
            (pareto_objective(),),
        )


def test_pareto_ignores_unselected_extra_quantiles_when_selected_one_matches():
    sources = (
        eligible_result(
            pareto_study(
                index=0,
                mean=1.0,
                statistics_quantiles=(0.05, 0.5, 0.95),
            )
        ),
        eligible_result(
            pareto_study(
                index=1,
                mean=2.0,
                statistics_quantiles=(0.5,),
            )
        ),
    )

    result = analyze_ensemble_pareto(
        sources,
        (
            pareto_objective(
                EnsembleScalarKind.QUANTILE,
                name="response_q50",
                quantile=0.5,
            ),
        ),
    )

    assert result.fronts == ((0,), (1,))


def test_pareto_rejects_quantile_not_computed_by_one_eligible_source():
    sources = (
        eligible_result(
            pareto_study(
                index=0,
                statistics_quantiles=(0.05, 0.5, 0.95),
            )
        ),
        eligible_result(
            pareto_study(
                index=1,
                statistics_quantiles=(0.05, 0.95),
            )
        ),
    )

    with pytest.raises(
        ValueError,
        match="quantile was not computed",
    ):
        analyze_ensemble_pareto(
            sources,
            (
                pareto_objective(
                    EnsembleScalarKind.QUANTILE,
                    name="response_q50",
                    quantile=0.5,
                ),
            ),
        )


def test_pareto_incompatible_excluded_source_does_not_block_comparison():
    eligible = eligible_result(
        pareto_study(
            index=0,
            metric_path=("response",),
        )
    )
    excluded = ineligible_result(
        pareto_study(
            index=1,
            metric_path=("other_response",),
        )
    )

    result = analyze_ensemble_pareto(
        (eligible, excluded),
        (pareto_objective(),),
    )

    assert result.fronts == ((0,),)
    assert result.points[1].exclusion_reason == (
        "constraint-ineligible"
    )


def test_pareto_result_serialization_and_hash_are_deterministic():
    sources = (
        eligible_result(
            pareto_study(
                index=0,
                mean=1.0,
            )
        ),
        eligible_result(
            pareto_study(
                index=1,
                mean=2.0,
            )
        ),
    )
    objectives = (pareto_objective(),)
    first = analyze_ensemble_pareto(
        sources,
        objectives,
        name="variability-pareto",
    )
    same = analyze_ensemble_pareto(
        sources,
        objectives,
        name="variability-pareto",
    )
    payload = first.to_dict()

    assert payload["schema_version"] == (
        "ensemble-pareto-result-v1"
    )
    assert payload["analysis_hash"] == first.analysis_hash
    assert payload["definition_hash"] == first.definition_hash
    assert payload["source_result_hashes"] == [
        source.result_hash for source in sources
    ]
    assert payload["fronts"] == [[0], [1]]
    assert payload["pareto_indices"] == [0]
    assert payload["ranked_count"] == 2
    assert payload["excluded_count"] == 0
    assert first.analysis_hash == same.analysis_hash
    assert first.result_hash == same.result_hash


def test_pareto_result_rejects_objective_values_inconsistent_with_source():
    source = eligible_result(
        pareto_study(
            index=0,
            mean=1.0,
        )
    )
    objective = pareto_objective()
    valid = analyze_ensemble_pareto(
        (source,),
        (objective,),
    )
    bad_point = EnsembleParetoPointResult(
        source=source,
        rank=0,
        objective_values=(
            ("response_mean", 999.0),
        ),
    )

    with pytest.raises(
        ValueError,
        match="point objectives differ",
    ):
        EnsembleParetoAnalysisResult(
            name="pareto",
            objectives=(objective,),
            source_results=(source,),
            points=(bad_point,),
            fronts=valid.fronts,
        )


def test_pareto_result_rejects_rank_inconsistent_with_front():
    source = eligible_result(
        pareto_study(
            index=0,
            mean=1.0,
        )
    )
    objective = pareto_objective()
    valid = analyze_ensemble_pareto(
        (source,),
        (objective,),
    )
    bad_point = EnsembleParetoPointResult(
        source=source,
        rank=1,
        objective_values=valid.points[0].objective_values,
    )

    with pytest.raises(
        ValueError,
        match="front membership or point rank differs",
    ):
        EnsembleParetoAnalysisResult(
            name="pareto",
            objectives=(objective,),
            source_results=(source,),
            points=(bad_point,),
            fronts=((0,),),
        )


def test_pareto_analysis_rejects_invalid_source_before_compatibility_access():
    with pytest.raises(
        TypeError,
        match="source_results must contain",
    ):
        analyze_ensemble_pareto(
            (object(),),
            (pareto_objective(),),
        )


def test_pareto_analysis_requires_unique_nonempty_objectives():
    source = eligible_result(
        pareto_study(
            index=0,
        )
    )

    with pytest.raises(
        ValueError,
        match="at least one objective",
    ):
        analyze_ensemble_pareto(
            (source,),
            (),
        )

    duplicate = pareto_objective()
    with pytest.raises(
        ValueError,
        match="objective names must be unique",
    ):
        analyze_ensemble_pareto(
            (source,),
            (duplicate, duplicate),
        )
