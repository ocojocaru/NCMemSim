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
    analyze_ensemble_execution,
)
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def provenance():
    return ParameterProvenance(
        source="Phase K4 metric analysis test",
        status=ParameterStatus.ASSUMED,
    )


def source_result(
    values=(5.5, 6.0),
    *,
    fail_index=None,
    evaluator_calls=None,
):
    base = DeviceBuilder.v2(
        n_fgs=1,
        nc_diameter_nm=5.0,
        name="k4-metric-analysis-base",
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
        applicability="Phase K4 metric analysis test",
        nominal_value=5.0,
    )

    ensemble = EnsembleSpec.from_device(
        name="phase-k4-metric-analysis",
        device=base,
        variables=(variable,),
    )

    sampling_spec = SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=54321),
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
        for index, value in enumerate(values)
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
        if evaluator_calls is not None:
            evaluator_calls.append(
                realization.identity.sample_index
            )

        if (
            fail_index is not None
            and realization.identity.sample_index
            == fail_index
        ):
            raise RuntimeError(
                "controlled K3 failure"
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
                    diameter * 2.0
                ),
            },
            "integer_exact": 4,
            "integer_lossy": 9007199254740993,
        }

    return execute_sample_manifest(
        manifest,
        base,
        evaluate,
        evaluation_id="k4-analysis-source",
    )


def metric_spec():
    return MetricAnalysisSpec(
        "k4-analysis",
        (
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
        ),
        (
            MetricConstraint(
                "response_max",
                "response",
                ConstraintOperator.LE,
                5.75,
                "V",
            ),
        ),
    )


def test_analyze_extracts_metrics_and_constraints():
    source = source_result()

    result = analyze_ensemble_execution(
        source,
        metric_spec(),
    )

    assert tuple(
        point.status
        for point in result.points
    ) == (
        "feasible",
        "infeasible",
    )

    assert result.points[0].metrics == {
        "response": 5.5,
        "nested_value": 11.0,
    }

    assert result.points[1].metrics == {
        "response": 6.0,
        "nested_value": 12.0,
    }

    assert (
        result.points[0]
        .constraints[0]
        .value
        == 5.5
    )

    assert (
        result.points[1]
        .constraints[0]
        .value
        == 6.0
    )


def test_analyze_supports_no_constraints():
    source = source_result(
        values=(6.0,),
    )

    spec = MetricAnalysisSpec(
        "no-constraints",
        (
            MetricDefinition(
                "response",
                ("response",),
                "V",
            ),
        ),
    )

    result = analyze_ensemble_execution(
        source,
        spec,
    )

    assert result.points[0].status == "feasible"
    assert result.points[0].constraints == ()


def test_analyze_propagates_k3_failure_unchanged():
    source = source_result(
        fail_index=0,
    )

    original = source.points[0]

    result = analyze_ensemble_execution(
        source,
        metric_spec(),
    )

    propagated = result.points[0]

    assert propagated.status == "failed"

    assert (
        propagated.failure_stage
        == original.failure_stage
    )

    assert (
        propagated.failure_category
        == original.failure_category
    )

    assert (
        propagated.error_type
        == original.error_type
    )

    assert (
        propagated.error_message
        == original.error_message
    )

    assert result.points[1].status == "infeasible"


def test_missing_metric_becomes_metric_extraction_failure():
    source = source_result(
        values=(5.5,),
    )

    spec = MetricAnalysisSpec(
        "missing-metric",
        (
            MetricDefinition(
                "missing",
                ("does_not_exist",),
                "1",
            ),
        ),
    )

    result = analyze_ensemble_execution(
        source,
        spec,
    )

    point = result.points[0]

    assert point.status == "failed"

    assert (
        point.failure_stage
        == "metric-extraction"
    )

    assert (
        point.failure_category
        == "metric-extraction"
    )

    assert point.metric_values == ()
    assert point.constraints == ()

    assert (
        point.error_type
        == "builtins.ValueError"
    )


def test_exact_integer_metric_is_normalized_to_float():
    source = source_result(
        values=(5.5,),
    )

    spec = MetricAnalysisSpec(
        "exact-integer",
        (
            MetricDefinition(
                "integer_exact",
                ("integer_exact",),
                "1",
            ),
        ),
    )

    result = analyze_ensemble_execution(
        source,
        spec,
    )

    point = result.points[0]

    assert point.status == "feasible"

    assert (
        point.metrics["integer_exact"]
        == 4.0
    )

    assert (
        type(
            point.metrics["integer_exact"]
        )
        is float
    )


def test_lossy_integer_metric_fails_closed():
    source = source_result(
        values=(5.5,),
    )

    spec = MetricAnalysisSpec(
        "lossy-integer",
        (
            MetricDefinition(
                "integer_lossy",
                ("integer_lossy",),
                "1",
            ),
        ),
    )

    result = analyze_ensemble_execution(
        source,
        spec,
    )

    point = result.points[0]

    assert point.status == "failed"

    assert (
        point.failure_stage
        == "metric-extraction"
    )

    assert (
        point.failure_category
        == "metric-extraction"
    )

    assert (
        "exactly representable"
        in point.error_message
    )


def test_analysis_does_not_rerun_evaluator():
    calls = []

    source = source_result(
        evaluator_calls=calls,
    )

    assert calls == [0, 1]

    analyze_ensemble_execution(
        source,
        metric_spec(),
    )

    assert calls == [0, 1]


def test_analysis_does_not_modify_source():
    source = source_result()

    before_dict = source.to_dict()
    before_hash = source.result_hash

    analyze_ensemble_execution(
        source,
        metric_spec(),
    )

    assert source.to_dict() == before_dict
    assert source.result_hash == before_hash


def test_analysis_is_deterministic():
    source = source_result()

    first = analyze_ensemble_execution(
        source,
        metric_spec(),
    )

    second = analyze_ensemble_execution(
        source,
        metric_spec(),
    )

    assert (
        first.analysis_hash
        == second.analysis_hash
    )

    assert (
        first.result_hash
        == second.result_hash
    )

    assert first.to_dict() == second.to_dict()


@pytest.mark.parametrize(
    "interrupt",
    [
        KeyboardInterrupt,
        SystemExit,
    ],
)
def test_interrupts_propagate(
    monkeypatch,
    interrupt,
):
    source = source_result(
        values=(5.5,),
    )

    spec = MetricAnalysisSpec(
        "interrupt-test",
        (
            MetricDefinition(
                "response",
                ("response",),
                "V",
            ),
        ),
    )

    def raise_interrupt(
        self,
        output,
    ):
        raise interrupt()

    monkeypatch.setattr(
        MetricDefinition,
        "extract",
        raise_interrupt,
    )

    with pytest.raises(interrupt):
        analyze_ensemble_execution(
            source,
            spec,
        )


def test_partial_metric_extraction_fails_complete_case():
    source = source_result(
        values=(5.5,),
    )

    spec = MetricAnalysisSpec(
        "partial-extraction",
        (
            MetricDefinition(
                "response",
                ("response",),
                "V",
            ),
            MetricDefinition(
                "missing",
                ("does_not_exist",),
                "1",
            ),
        ),
    )

    result = analyze_ensemble_execution(
        source,
        spec,
    )

    point = result.points[0]

    assert point.status == "failed"

    assert (
        point.failure_stage
        == "metric-extraction"
    )

    assert (
        point.failure_category
        == "metric-extraction"
    )

    assert point.metric_values == ()
    assert point.constraints == ()
