import math

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
    analyze_ensemble_execution,
    execute_sample_manifest,
    generate_sample_manifest,
)
from ncmemsim.ensemble.statistics import (
    EnsembleStatisticsSpec,
    _metric_population_summary,
    summarize_ensemble_metrics,
)
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def provenance():
    return ParameterProvenance(
        source="Phase K4b statistics analysis test",
        status=ParameterStatus.ASSUMED,
    )


def metric_analysis(
    values,
    *,
    fail_indices=(),
    missing_metric_indices=(),
    threshold=1000.0,
):
    base = DeviceBuilder.v2(
        n_fgs=1,
        nc_diameter_nm=5.0,
        name="k4b-statistics-analysis-base",
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
        applicability="Phase K4b statistics analysis test",
        nominal_value=5.0,
    )

    ensemble = EnsembleSpec.from_device(
        name="phase-k4b-statistics-analysis",
        device=base,
        variables=(variable,),
    )

    sampling_spec = SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=13579),
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

    fail_indices = set(
        fail_indices
    )

    missing_metric_indices = set(
        missing_metric_indices
    )

    calls = []

    def evaluate(
        candidate,
        protocol,
        realization,
    ):
        index = (
            realization.identity.sample_index
        )

        calls.append(
            index
        )

        if index in fail_indices:
            raise RuntimeError(
                f"controlled failure {index}"
            )

        diameter = float(
            candidate
            .floating_gates()[0]
            .nc_diameter_nm
        )

        if index in missing_metric_indices:
            return {
                "response": diameter,
            }

        return {
            "response": diameter,
            "nested": {
                "value": float(
                    2.0 * diameter
                ),
            },
        }

    execution = execute_sample_manifest(
        manifest,
        base,
        evaluate,
        evaluation_id="k4b-statistics-analysis",
    )

    metric_spec = MetricAnalysisSpec(
        "k4b-statistics-analysis-metrics",
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
                float(threshold),
                "V",
            ),
        ),
    )

    analysis = analyze_ensemble_execution(
        execution,
        metric_spec,
    )

    return analysis, calls


def metric_summary(
    result,
    name,
):
    return next(
        summary
        for summary
        in result.metric_statistics
        if summary.metric_name == name
    )


def test_statistics_analysis_computes_population_summary():
    source, calls = metric_analysis(
        (
            1.0,
            2.0,
            3.0,
            4.0,
        )
    )

    result = summarize_ensemble_metrics(
        source,
        EnsembleStatisticsSpec(
            quantiles=(
                0.0,
                0.25,
                0.5,
                0.75,
                1.0,
            )
        ),
    )

    summary = metric_summary(
        result,
        "response",
    )

    assert summary.denominator == 4
    assert summary.sample_indices == (
        0,
        1,
        2,
        3,
    )

    assert summary.minimum == 1.0
    assert summary.maximum == 4.0
    assert summary.mean == 2.5
    assert summary.variance == 1.25
    assert (
        summary.standard_deviation
        == math.sqrt(1.25)
    )
    assert summary.median == 2.5

    assert summary.quantiles == (
        (0.0, 1.0),
        (0.25, 1.75),
        (0.5, 2.5),
        (0.75, 3.25),
        (1.0, 4.0),
    )

    assert calls == [
        0,
        1,
        2,
        3,
    ]


def test_statistics_analysis_uses_ddof_zero():
    source, _ = metric_analysis(
        (
            2.0,
            4.0,
        )
    )

    result = summarize_ensemble_metrics(
        source,
        EnsembleStatisticsSpec(),
    )

    summary = metric_summary(
        result,
        "response",
    )

    assert summary.mean == 3.0
    assert summary.variance == 1.0
    assert summary.standard_deviation == 1.0


def test_statistics_analysis_single_member_population():
    source, _ = metric_analysis(
        (7.25,)
    )

    result = summarize_ensemble_metrics(
        source,
        EnsembleStatisticsSpec(
            quantiles=(
                0.0,
                0.5,
                1.0,
            )
        ),
    )

    summary = metric_summary(
        result,
        "response",
    )

    assert summary.denominator == 1
    assert summary.minimum == 7.25
    assert summary.maximum == 7.25
    assert summary.mean == 7.25
    assert summary.variance == 0.0
    assert summary.standard_deviation == 0.0
    assert summary.median == 7.25

    assert summary.quantiles == (
        (0.0, 7.25),
        (0.5, 7.25),
        (1.0, 7.25),
    )


def test_statistics_analysis_odd_member_median():
    source, _ = metric_analysis(
        (
            9.0,
            1.0,
            5.0,
        )
    )

    result = summarize_ensemble_metrics(
        source,
        EnsembleStatisticsSpec(),
    )

    summary = metric_summary(
        result,
        "response",
    )

    assert summary.median == 5.0


def test_statistics_analysis_quantiles_use_linear_n_minus_one():
    source, _ = metric_analysis(
        (
            10.0,
            20.0,
            30.0,
            40.0,
            50.0,
        )
    )

    result = summarize_ensemble_metrics(
        source,
        EnsembleStatisticsSpec(
            quantiles=(
                0.1,
                0.6,
                0.9,
            )
        ),
    )

    summary = metric_summary(
        result,
        "response",
    )

    assert summary.quantiles == (
        (0.1, 14.0),
        (0.6, 34.0),
        (0.9, 46.0),
    )


def test_statistics_analysis_excludes_failed_points_but_preserves_coverage():
    source, _ = metric_analysis(
        (
            1.0,
            100.0,
            3.0,
            200.0,
        ),
        fail_indices=(
            1,
            3,
        ),
    )

    result = summarize_ensemble_metrics(
        source,
        EnsembleStatisticsSpec(),
    )

    summary = metric_summary(
        result,
        "response",
    )

    assert result.attempted_count == 4
    assert result.assessed_count == 2
    assert result.failed_count == 2

    assert (
        result.coverage_fraction
        == 0.5
    )

    assert summary.denominator == 2
    assert summary.sample_indices == (
        0,
        2,
    )

    assert summary.minimum == 1.0
    assert summary.maximum == 3.0
    assert summary.mean == 2.0
    assert summary.variance == 1.0


def test_statistics_analysis_includes_feasible_and_infeasible_points():
    source, _ = metric_analysis(
        (
            1.0,
            2.0,
            3.0,
        ),
        threshold=1.5,
    )

    result = summarize_ensemble_metrics(
        source,
        EnsembleStatisticsSpec(),
    )

    summary = metric_summary(
        result,
        "response",
    )

    assert result.feasible_count == 1
    assert result.infeasible_count == 2
    assert result.assessed_count == 3

    assert summary.denominator == 3
    assert summary.sample_indices == (
        0,
        1,
        2,
    )

    assert summary.mean == 2.0


def test_statistics_analysis_preserves_declared_metric_order():
    source, _ = metric_analysis(
        (
            1.0,
            2.0,
        )
    )

    result = summarize_ensemble_metrics(
        source,
        EnsembleStatisticsSpec(),
    )

    assert tuple(
        summary.metric_name
        for summary
        in result.metric_statistics
    ) == (
        "response",
        "nested_value",
    )

    nested = metric_summary(
        result,
        "nested_value",
    )

    assert nested.minimum == 2.0
    assert nested.maximum == 4.0
    assert nested.mean == 3.0
    assert nested.variance == 1.0


def test_statistics_analysis_all_failed_produces_empty_summaries():
    source, _ = metric_analysis(
        (
            1.0,
            2.0,
            3.0,
        ),
        fail_indices=(
            0,
            1,
            2,
        ),
    )

    result = summarize_ensemble_metrics(
        source,
        EnsembleStatisticsSpec(
            quantiles=(
                0.1,
                0.5,
                0.9,
            )
        ),
    )

    assert result.attempted_count == 3
    assert result.assessed_count == 0
    assert result.failed_count == 3
    assert result.coverage_fraction == 0.0

    for summary in result.metric_statistics:
        assert summary.denominator == 0
        assert summary.sample_indices == ()
        assert summary.realization_ids == ()

        assert summary.minimum is None
        assert summary.maximum is None
        assert summary.mean is None
        assert summary.variance is None
        assert (
            summary.standard_deviation
            is None
        )
        assert summary.median is None

        assert summary.quantiles == (
            (0.1, None),
            (0.5, None),
            (0.9, None),
        )


def test_statistics_analysis_does_not_rerun_source_evaluator():
    source, calls = metric_analysis(
        (
            1.0,
            2.0,
            3.0,
        )
    )

    before = list(
        calls
    )

    summarize_ensemble_metrics(
        source,
        EnsembleStatisticsSpec(),
    )

    assert calls == before


def test_statistics_analysis_does_not_mutate_source():
    source, _ = metric_analysis(
        (
            1.0,
            2.0,
            3.0,
        )
    )

    before_hash = (
        source.result_hash
    )

    before_payload = (
        source.to_dict()
    )

    summarize_ensemble_metrics(
        source,
        EnsembleStatisticsSpec(),
    )

    assert (
        source.result_hash
        == before_hash
    )

    assert (
        source.to_dict()
        == before_payload
    )


def test_statistics_analysis_is_deterministic():
    source, _ = metric_analysis(
        (
            1.0,
            2.0,
            3.0,
            4.0,
        )
    )

    spec = EnsembleStatisticsSpec(
        quantiles=(
            0.1,
            0.5,
            0.9,
        )
    )

    first = summarize_ensemble_metrics(
        source,
        spec,
    )

    second = summarize_ensemble_metrics(
        source,
        spec,
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


def test_statistics_analysis_rejects_wrong_types():
    source, _ = metric_analysis(
        (
            1.0,
            2.0,
        )
    )

    with pytest.raises(
        TypeError,
        match="source must be",
    ):
        summarize_ensemble_metrics(
            object(),
            EnsembleStatisticsSpec(),
        )

    with pytest.raises(
        TypeError,
        match="spec must be",
    ):
        summarize_ensemble_metrics(
            source,
            object(),
        )


def test_statistics_analysis_even_median_avoids_overflow():
    summary = _metric_population_summary(
        metric_name="large_metric",
        unit="1",
        values=[
            1.0e308,
            1.0e308,
        ],
        sample_indices=(
            0,
            1,
        ),
        realization_ids=(
            "realization-0",
            "realization-1",
        ),
        probabilities=(
            0.5,
        ),
    )

    assert math.isfinite(
        summary.median
    )

    assert (
        summary.median
        == 1.0e308
    )

    assert summary.quantiles == (
        (
            0.5,
            1.0e308,
        ),
    )


def test_statistics_analysis_fails_closed_on_nonfinite_variance():
    with pytest.raises(
        ValueError,
        match="variance must be finite",
    ):
        _metric_population_summary(
            metric_name="wide_metric",
            unit="1",
            values=[
                -1.0e200,
                1.0e200,
            ],
            sample_indices=(
                0,
                1,
            ),
            realization_ids=(
                "realization-0",
                "realization-1",
            ),
            probabilities=(
                0.5,
            ),
        )


def test_statistics_analysis_excludes_metric_extraction_failures():
    source, _ = metric_analysis(
        (
            1.0,
            2.0,
            3.0,
        ),
        missing_metric_indices=(
            1,
        ),
    )

    assert (
        source.points[1].status
        == "failed"
    )

    assert (
        source.points[1].failure_stage
        == "metric-extraction"
    )

    result = summarize_ensemble_metrics(
        source,
        EnsembleStatisticsSpec(),
    )

    response = metric_summary(
        result,
        "response",
    )

    nested = metric_summary(
        result,
        "nested_value",
    )

    assert result.attempted_count == 3
    assert result.assessed_count == 2
    assert result.failed_count == 1
    assert result.coverage_fraction == 2 / 3

    assert response.denominator == 2
    assert response.sample_indices == (
        0,
        2,
    )
    assert response.mean == 2.0

    assert nested.denominator == 2
    assert nested.sample_indices == (
        0,
        2,
    )
    assert nested.mean == 4.0
