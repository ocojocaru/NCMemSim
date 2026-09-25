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
    EnsemblePopulationStatistics,
    EnsembleStatisticsSpec,
    MetricPopulationSummary,
)
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def provenance():
    return ParameterProvenance(
        source="Phase K4b statistics contract test",
        status=ParameterStatus.ASSUMED,
    )


def analysis_result(
    values=(5.5, 6.0, 5.25),
    *,
    fail_index=2,
):
    base = DeviceBuilder.v2(
        n_fgs=1,
        nc_diameter_nm=5.0,
        name="k4b-statistics-contract-base",
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
        applicability="Phase K4b statistics contract test",
        nominal_value=5.0,
    )

    ensemble = EnsembleSpec.from_device(
        name="phase-k4b-statistics-contract",
        device=base,
        variables=(variable,),
    )

    sampling_spec = SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=24680),
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
        if (
            fail_index is not None
            and realization.identity.sample_index
            == fail_index
        ):
            raise RuntimeError(
                "controlled K4b source failure"
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
                ),
            },
        }

    execution = execute_sample_manifest(
        manifest,
        base,
        evaluate,
        evaluation_id="k4b-statistics-source",
    )

    metric_spec = MetricAnalysisSpec(
        "k4b-statistics-metrics",
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

    return analyze_ensemble_execution(
        execution,
        metric_spec,
    )


def assessed_membership(source):
    assessed = tuple(
        point
        for point in source.points
        if point.status != "failed"
    )

    return (
        tuple(
            point.source.identity.sample_index
            for point in assessed
        ),
        tuple(
            point.source.identity.realization_id
            for point in assessed
        ),
    )


def valid_summary(
    source,
    *,
    metric_name="response",
    unit="V",
    multiplier=1.0,
):
    sample_indices, realization_ids = (
        assessed_membership(source)
    )

    values = [
        point.metrics[metric_name]
        for point in source.points
        if point.status != "failed"
    ]

    values = [
        float(value * multiplier)
        for value in values
    ]

    minimum = min(values)
    maximum = max(values)
    mean = sum(values) / len(values)

    variance = (
        sum(
            (value - mean) ** 2
            for value in values
        )
        / len(values)
    )

    standard_deviation = (
        variance ** 0.5
    )

    ordered = sorted(values)

    median = (
        ordered[len(ordered) // 2]
        if len(ordered) % 2 == 1
        else (
            ordered[len(ordered) // 2 - 1]
            + ordered[len(ordered) // 2]
        )
        / 2.0
    )

    quantiles = (
        (0.05, float(
            ordered[0]
            + 0.05
            * (len(ordered) - 1)
            * (ordered[-1] - ordered[0])
        )),
        (0.5, float(median)),
        (0.95, float(
            ordered[0]
            + 0.95
            * (len(ordered) - 1)
            * (ordered[-1] - ordered[0])
        )),
    )

    return MetricPopulationSummary(
        metric_name=metric_name,
        unit=unit,
        denominator=len(values),
        sample_indices=sample_indices,
        realization_ids=realization_ids,
        minimum=float(minimum),
        maximum=float(maximum),
        mean=float(mean),
        variance=float(variance),
        standard_deviation=float(
            standard_deviation
        ),
        median=float(median),
        quantiles=quantiles,
    )


def test_statistics_spec_defaults_are_explicit():
    spec = EnsembleStatisticsSpec()

    assert spec.quantiles == (
        0.05,
        0.5,
        0.95,
    )

    assert spec.to_dict() == {
        "schema_version": (
            "ensemble-statistics-spec-v1"
        ),
        "quantiles": [
            0.05,
            0.5,
            0.95,
        ],
        "quantile_method": (
            "linear-n-minus-one"
        ),
        "standard_deviation": (
            "population-ddof-0"
        ),
        "variance": (
            "population-ddof-0"
        ),
        "selection": (
            "all-assessed-complete-cases"
        ),
    }


def test_statistics_spec_normalizes_numeric_quantiles():
    spec = EnsembleStatisticsSpec(
        quantiles=(0, 0.25, 1),
    )

    assert spec.quantiles == (
        0.0,
        0.25,
        1.0,
    )

    assert all(
        type(value) is float
        for value in spec.quantiles
    )


@pytest.mark.parametrize(
    "quantiles",
    [
        (-0.1,),
        (1.1,),
        (float("nan"),),
        (float("inf"),),
        (True,),
        ("0.5",),
    ],
)
def test_statistics_spec_rejects_invalid_quantiles(
    quantiles,
):
    with pytest.raises(
        (TypeError, ValueError),
    ):
        EnsembleStatisticsSpec(
            quantiles=quantiles,
        )


def test_statistics_spec_rejects_duplicate_quantiles():
    with pytest.raises(
        ValueError,
        match="duplicate quantiles",
    ):
        EnsembleStatisticsSpec(
            quantiles=(
                0.5,
                0.50,
            ),
        )


def test_population_summary_accepts_valid_nonempty_contract():
    source = analysis_result()

    summary = valid_summary(
        source,
    )

    assert summary.denominator == 2

    assert summary.sample_indices == (
        0,
        1,
    )

    assert len(
        summary.realization_ids
    ) == 2

    assert summary.minimum == 5.5
    assert summary.maximum == 6.0
    assert summary.mean == 5.75
    assert summary.variance == 0.0625
    assert (
        summary.standard_deviation
        == 0.25
    )
    assert summary.median == 5.75

    assert (
        summary.summary_hash
        == MetricPopulationSummary(
            **{
                "metric_name": (
                    summary.metric_name
                ),
                "unit": summary.unit,
                "denominator": (
                    summary.denominator
                ),
                "sample_indices": (
                    summary.sample_indices
                ),
                "realization_ids": (
                    summary.realization_ids
                ),
                "minimum": summary.minimum,
                "maximum": summary.maximum,
                "mean": summary.mean,
                "variance": summary.variance,
                "standard_deviation": (
                    summary.standard_deviation
                ),
                "median": summary.median,
                "quantiles": (
                    summary.quantiles
                ),
            }
        ).summary_hash
    )


def test_empty_population_summary_requires_none_statistics():
    summary = MetricPopulationSummary(
        metric_name="response",
        unit="V",
        denominator=0,
        sample_indices=(),
        realization_ids=(),
        minimum=None,
        maximum=None,
        mean=None,
        variance=None,
        standard_deviation=None,
        median=None,
        quantiles=(
            (0.05, None),
            (0.5, None),
            (0.95, None),
        ),
    )

    assert summary.denominator == 0

    assert all(
        value is None
        for _, value
        in summary.quantiles
    )


def test_empty_population_summary_rejects_numeric_values():
    with pytest.raises(
        ValueError,
        match="empty summary",
    ):
        MetricPopulationSummary(
            metric_name="response",
            unit="V",
            denominator=0,
            sample_indices=(),
            realization_ids=(),
            minimum=1.0,
            maximum=None,
            mean=None,
            variance=None,
            standard_deviation=None,
            median=None,
            quantiles=(
                (0.5, None),
            ),
        )


def test_nonempty_population_summary_requires_all_values():
    source = analysis_result()

    summary = valid_summary(
        source,
    )

    with pytest.raises(
        ValueError,
        match="nonempty summary",
    ):
        replace(
            summary,
            mean=None,
        )


@pytest.mark.parametrize(
    "change",
    [
        {
            "minimum": 7.0,
            "maximum": 6.0,
        },
        {
            "variance": -1.0,
        },
        {
            "standard_deviation": -1.0,
        },
    ],
)
def test_population_summary_rejects_invalid_scalar_relationships(
    change,
):
    source = analysis_result()

    summary = valid_summary(
        source,
    )

    with pytest.raises(
        ValueError,
    ):
        replace(
            summary,
            **change,
        )


def test_population_summary_membership_matches_denominator():
    source = analysis_result()

    summary = valid_summary(
        source,
    )

    with pytest.raises(
        ValueError,
        match="membership",
    ):
        replace(
            summary,
            denominator=3,
        )


def test_population_summary_rejects_duplicate_membership():
    source = analysis_result()

    summary = valid_summary(
        source,
    )

    with pytest.raises(
        ValueError,
        match="sample_indices must be unique",
    ):
        replace(
            summary,
            sample_indices=(
                0,
                0,
            ),
        )

    with pytest.raises(
        ValueError,
        match="realization_ids must be unique",
    ):
        replace(
            summary,
            realization_ids=(
                summary.realization_ids[0],
                summary.realization_ids[0],
            ),
        )


def test_population_summary_rejects_duplicate_quantile_probability():
    source = analysis_result()

    summary = valid_summary(
        source,
    )

    with pytest.raises(
        ValueError,
        match="duplicate quantile probability",
    ):
        replace(
            summary,
            quantiles=(
                (
                    0.5,
                    5.75,
                ),
                (
                    0.5,
                    5.75,
                ),
            ),
        )


def test_population_statistics_counts_and_coverage():
    source = analysis_result()

    response = valid_summary(
        source,
    )

    nested = valid_summary(
        source,
        metric_name="nested_value",
        unit="1",
    )

    result = EnsemblePopulationStatistics(
        spec=EnsembleStatisticsSpec(),
        source=source,
        metric_statistics=(
            response,
            nested,
        ),
    )

    assert result.attempted_count == 3
    assert result.assessed_count == 2
    assert result.feasible_count == 1
    assert result.infeasible_count == 1
    assert result.failed_count == 1

    assert (
        result.coverage_fraction
        == 2 / 3
    )

    payload = result.to_dict()

    assert payload["coverage_fraction"] == {
        "value": 2 / 3,
        "numerator": 2,
        "denominator": 3,
    }


def test_population_statistics_requires_metric_order():
    source = analysis_result()

    response = valid_summary(
        source,
    )

    nested = valid_summary(
        source,
        metric_name="nested_value",
        unit="1",
    )

    with pytest.raises(
        ValueError,
        match="metric statistics differ",
    ):
        EnsemblePopulationStatistics(
            EnsembleStatisticsSpec(),
            source,
            (
                nested,
                response,
            ),
        )


def test_population_statistics_requires_exact_assessed_membership():
    source = analysis_result()

    response = valid_summary(
        source,
    )

    nested = valid_summary(
        source,
        metric_name="nested_value",
        unit="1",
    )

    wrong = replace(
        response,
        sample_indices=(
            1,
            0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="sample membership",
    ):
        EnsemblePopulationStatistics(
            EnsembleStatisticsSpec(),
            source,
            (
                wrong,
                nested,
            ),
        )


def test_population_statistics_requires_spec_quantiles():
    source = analysis_result()

    response = valid_summary(
        source,
    )

    nested = valid_summary(
        source,
        metric_name="nested_value",
        unit="1",
    )

    wrong = replace(
        response,
        quantiles=(
            (
                0.1,
                5.55,
            ),
            (
                0.5,
                5.75,
            ),
            (
                0.9,
                5.95,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="quantiles differ",
    ):
        EnsemblePopulationStatistics(
            EnsembleStatisticsSpec(),
            source,
            (
                wrong,
                nested,
            ),
        )


def test_population_statistics_hashes_are_deterministic():
    source = analysis_result()

    summaries = (
        valid_summary(
            source,
        ),
        valid_summary(
            source,
            metric_name="nested_value",
            unit="1",
        ),
    )

    first = EnsemblePopulationStatistics(
        EnsembleStatisticsSpec(),
        source,
        summaries,
    )

    second = EnsemblePopulationStatistics(
        EnsembleStatisticsSpec(),
        source,
        summaries,
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


@pytest.mark.parametrize(
    "change, message",
    [
        (
            {"mean": 7.0},
            "mean must lie within",
        ),
        (
            {"median": 7.0},
            "median must lie within",
        ),
        (
            {
                "quantiles": (
                    (0.05, 5.5),
                    (0.5, 7.0),
                    (0.95, 6.0),
                ),
            },
            "quantile values must lie within",
        ),
        (
            {
                "variance": 0.0625,
                "standard_deviation": 0.5,
            },
            "variance and standard deviation",
        ),
    ],
)
def test_population_summary_rejects_inconsistent_statistics(
    change,
    message,
):
    source = analysis_result()

    summary = valid_summary(
        source,
    )

    with pytest.raises(
        ValueError,
        match=message,
    ):
        replace(
            summary,
            **change,
        )
