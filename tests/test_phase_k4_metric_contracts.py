# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

from dataclasses import replace

import pytest

from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (
    BindingScope,
    ConstraintOperator,
    MetricAnalysisSpec,
    MetricConstraint,
    MetricDefinition,
    ParameterBinding,
)
from ncmemsim.dtco.metrics import (
    ConstraintEvaluation,
)
from ncmemsim.ensemble import (
    EnsembleSample,
    EnsembleSpec,
    NormalDistribution,
    PhysicalDomain,
    RNGSpec,
    SampleManifest,
    SamplingSpec,
    StochasticVariable,
    execute_sample_manifest,
    generate_sample_manifest,
)
from ncmemsim.ensemble.metrics import (
    EnsembleMetricAnalysisResult,
    EnsembleMetricPointResult,
)
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def provenance():
    return ParameterProvenance(
        source="Phase K4 metric contract test",
        status=ParameterStatus.ASSUMED,
    )


def source_result(
    values=(5.5, 6.0),
    *,
    fail_index=None,
):
    base = DeviceBuilder.v2(
        n_fgs=1,
        nc_diameter_nm=5.0,
        name="k4-metric-contract-base",
    )

    variable = StochasticVariable(
        name="diameter",
        binding=ParameterBinding(
            BindingScope.DEVICE,
            (
                "layers",
                "FG1",
                "nc_diameter_nm",
            ),
        ),
        distribution=NormalDistribution(
            mean=5.0,
            standard_deviation=0.5,
        ),
        unit="nm",
        physical_domain=PhysicalDomain(
            lower=0.0,
            lower_inclusive=False,
        ),
        provenance=provenance(),
        applicability="Phase K4 metric contract test",
        nominal_value=5.0,
    )

    ensemble = EnsembleSpec.from_device(
        name="phase-k4-metric-contract",
        device=base,
        variables=(variable,),
    )

    sampling_spec = SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=12345),
        sample_count=len(values),
    )

    runtime = generate_sample_manifest(
        sampling_spec
    ).runtime

    samples = tuple(
        EnsembleSample.from_values(
            sampling_spec,
            index,
            (float(value),),
        )
        for index, value
        in enumerate(values)
    )

    manifest = SampleManifest(
        sampling_spec=sampling_spec,
        samples=samples,
        runtime=runtime,
    )

    def evaluate(
        candidate,
        protocol,
        realization,
    ):
        if (
            fail_index is not None
            and realization.identity.sample_index
            == fail_index
        ):
            raise RuntimeError(
                "controlled K3 workflow failure"
            )

        diameter = (
            candidate
            .floating_gates()[0]
            .nc_diameter_nm
        )

        return {
            "response": float(diameter),
            "nested": {
                "value": float(
                    2.0 * diameter
                )
            },
        }

    return execute_sample_manifest(
        manifest,
        base,
        evaluate,
        evaluation_id="k4-contract-source",
    )


def metric_spec():
    metrics = (
        MetricDefinition(
            "response",
            ("response",),
            "V",
        ),
        MetricDefinition(
            "nested_value",
            (
                "nested",
                "value",
            ),
            "1",
        ),
    )

    constraints = (
        MetricConstraint(
            "response_max",
            "response",
            ConstraintOperator.LE,
            5.75,
            "V",
        ),
    )

    return MetricAnalysisSpec(
        "k4-contract-metrics",
        metrics,
        constraints,
    )


def assessed_point(
    source,
    *,
    response,
    nested_value,
):
    constraint = ConstraintEvaluation(
        metric_spec().constraints[0],
        response,
    )

    status = (
        "feasible"
        if constraint.satisfied
        else "infeasible"
    )

    return EnsembleMetricPointResult(
        source=source,
        status=status,
        metric_values=(
            (
                "response",
                float(response),
            ),
            (
                "nested_value",
                float(nested_value),
            ),
        ),
        constraints=(constraint,),
    )


def test_feasible_and_infeasible_point_contracts():
    source = source_result()

    feasible = assessed_point(
        source.points[0],
        response=5.5,
        nested_value=11.0,
    )

    infeasible = assessed_point(
        source.points[1],
        response=6.0,
        nested_value=12.0,
    )

    assert feasible.status == "feasible"
    assert infeasible.status == "infeasible"

    assert feasible.metrics == {
        "response": 5.5,
        "nested_value": 11.0,
    }

    assert feasible.failure_stage is None
    assert feasible.failure_category is None


def test_failed_source_preserves_exact_k3_failure():
    source = source_result(
        fail_index=0,
    )

    original = source.points[0]

    point = EnsembleMetricPointResult(
        source=original,
        status="failed",
        failure_stage=(
            original.failure_stage
        ),
        failure_category=(
            original.failure_category
        ),
        error_type=original.error_type,
        error_message=(
            original.error_message
        ),
    )

    assert point.failure_stage == "workflow"

    assert (
        point.failure_category
        == "workflow-execution"
    )

    assert (
        point.to_dict()["failure"]
        == {
            "stage": (
                original.failure_stage
            ),
            "category": (
                original.failure_category
            ),
            "type": original.error_type,
            "message": (
                original.error_message
            ),
        }
    )


def test_propagated_failure_cannot_be_reclassified():
    source = source_result(
        fail_index=0,
    )

    original = source.points[0]

    with pytest.raises(
        ValueError,
        match="preserve K3 failure details",
    ):
        EnsembleMetricPointResult(
            source=original,
            status="failed",
            failure_stage=(
                original.failure_stage
            ),
            failure_category=(
                "metric-extraction"
            ),
            error_type=original.error_type,
            error_message=(
                original.error_message
            ),
        )


def test_metric_extraction_failure_contract():
    source = source_result()

    point = EnsembleMetricPointResult(
        source=source.points[0],
        status="failed",
        failure_stage="metric-extraction",
        failure_category="metric-extraction",
        error_type="builtins.ValueError",
        error_message="missing metric",
    )

    assert point.metric_values == ()
    assert point.constraints == ()

    with pytest.raises(
        ValueError,
        match="partial metrics",
    ):
        replace(
            point,
            metric_values=(
                (
                    "response",
                    5.5,
                ),
            ),
        )


def test_metric_extraction_failure_requires_stable_category():
    source = source_result()

    with pytest.raises(
        ValueError,
        match="metric-extraction",
    ):
        EnsembleMetricPointResult(
            source=source.points[0],
            status="failed",
            failure_stage="metric-extraction",
            failure_category="wrong",
            error_type="builtins.ValueError",
            error_message="bad metric",
        )


@pytest.mark.parametrize(
    "metric_values",
    [
        (
            (
                "response",
                5,
            ),
        ),
        (
            (
                "response",
                float("nan"),
            ),
        ),
        (
            (
                "response",
                float("inf"),
            ),
        ),
    ],
)
def test_assessed_metrics_require_finite_exact_python_floats(
    metric_values,
):
    source = source_result(
        values=(5.5,),
    )

    with pytest.raises(
        (TypeError, ValueError),
    ):
        EnsembleMetricPointResult(
            source=source.points[0],
            status="feasible",
            metric_values=metric_values,
        )


def test_assessed_metric_names_must_be_unique():
    source = source_result(
        values=(5.5,),
    )

    with pytest.raises(
        ValueError,
        match="unique",
    ):
        EnsembleMetricPointResult(
            source=source.points[0],
            status="feasible",
            metric_values=(
                (
                    "response",
                    5.5,
                ),
                (
                    "response",
                    6.0,
                ),
            ),
        )


def test_status_must_match_constraint_evaluation():
    source = source_result(
        values=(6.0,),
    )

    constraint = ConstraintEvaluation(
        metric_spec().constraints[0],
        6.0,
    )

    assert not constraint.satisfied

    with pytest.raises(
        ValueError,
        match="status differs",
    ):
        EnsembleMetricPointResult(
            source=source.points[0],
            status="feasible",
            metric_values=(
                (
                    "response",
                    6.0,
                ),
                (
                    "nested_value",
                    12.0,
                ),
            ),
            constraints=(constraint,),
        )


def test_analysis_requires_every_source_point_in_order():
    source = source_result()

    points = (
        assessed_point(
            source.points[0],
            response=5.5,
            nested_value=11.0,
        ),
        assessed_point(
            source.points[1],
            response=6.0,
            nested_value=12.0,
        ),
    )

    result = EnsembleMetricAnalysisResult(
        metric_spec(),
        source,
        points,
    )

    assert result.points == points

    with pytest.raises(
        ValueError,
        match="every source realization",
    ):
        replace(
            result,
            points=result.points[:-1],
        )

    with pytest.raises(
        ValueError,
        match="order or source differs",
    ):
        replace(
            result,
            points=tuple(
                reversed(
                    result.points
                )
            ),
        )


def test_analysis_enforces_metric_and_constraint_definition_order():
    source = source_result(
        values=(5.5,),
    )

    point = assessed_point(
        source.points[0],
        response=5.5,
        nested_value=11.0,
    )

    result = EnsembleMetricAnalysisResult(
        metric_spec(),
        source,
        (point,),
    )

    with pytest.raises(
        ValueError,
        match="metric order differs",
    ):
        replace(
            result,
            points=(
                replace(
                    point,
                    metric_values=tuple(
                        reversed(
                            point.metric_values
                        )
                    ),
                ),
            ),
        )


def test_analysis_hash_and_result_hash_are_deterministic():
    source = source_result(
        values=(5.5,),
    )

    point = assessed_point(
        source.points[0],
        response=5.5,
        nested_value=11.0,
    )

    first = EnsembleMetricAnalysisResult(
        metric_spec(),
        source,
        (point,),
    )

    second = EnsembleMetricAnalysisResult(
        metric_spec(),
        source,
        (point,),
    )

    assert (
        first.analysis_hash
        == second.analysis_hash
    )

    assert (
        first.result_hash
        == second.result_hash
    )

    assert (
        first.to_dict()
        == second.to_dict()
    )


def test_constraint_values_require_finite_python_floats():
    source = source_result(
        values=(5.5,),
    )

    constraint = ConstraintEvaluation(
        metric_spec().constraints[0],
        5,
    )

    with pytest.raises(
        ValueError,
        match="constraint values",
    ):
        EnsembleMetricPointResult(
            source=source.points[0],
            status="feasible",
            metric_values=(
                (
                    "response",
                    5.0,
                ),
                (
                    "nested_value",
                    10.0,
                ),
            ),
            constraints=(constraint,),
        )


def test_analysis_rejects_constraint_definition_mismatch():
    source = source_result(
        values=(5.5,),
    )

    point = assessed_point(
        source.points[0],
        response=5.5,
        nested_value=11.0,
    )

    result = EnsembleMetricAnalysisResult(
        metric_spec(),
        source,
        (point,),
    )

    wrong_constraint = MetricConstraint(
        "different_constraint",
        "response",
        ConstraintOperator.LE,
        5.75,
        "V",
    )

    wrong_point = replace(
        point,
        constraints=(
            ConstraintEvaluation(
                wrong_constraint,
                5.5,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="constraint definitions differ",
    ):
        replace(
            result,
            points=(wrong_point,),
        )


def test_analysis_rejects_constraint_value_mismatch():
    source = source_result(
        values=(5.5,),
    )

    point = assessed_point(
        source.points[0],
        response=5.5,
        nested_value=11.0,
    )

    result = EnsembleMetricAnalysisResult(
        metric_spec(),
        source,
        (point,),
    )

    wrong_point = replace(
        point,
        constraints=(
            ConstraintEvaluation(
                metric_spec().constraints[0],
                5.0,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="constraint value differs",
    ):
        replace(
            result,
            points=(wrong_point,),
        )
