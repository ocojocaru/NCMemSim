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
from ncmemsim.ensemble import (
    EnsembleSample,
    EnsembleSpec,
    EnsembleStatisticsSpec,
    NormalDistribution,
    PhysicalDomain,
    RNGSpec,
    SampleManifest,
    SamplingSpec,
    StochasticVariable,
    analyze_ensemble_execution,
    execute_sample_manifest,
    generate_sample_manifest,
    summarize_ensemble_metrics,
)
from ncmemsim.ensemble.feasibility import (
    EnsembleFeasibilitySummary,
    NominalMetricComparison,
    NominalMetricReference,
    summarize_ensemble_feasibility,
)
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def provenance():
    return ParameterProvenance(
        source="Phase K4c feasibility contract test",
        status=ParameterStatus.ASSUMED,
    )


def population_statistics(
    values=(1.0, 2.0, 3.0),
    *,
    fail_indices=(),
    threshold=1.5,
):
    base = DeviceBuilder.v2(
        n_fgs=1,
        nc_diameter_nm=5.0,
        name="k4c-feasibility-contract-base",
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
        applicability="Phase K4c feasibility contract test",
        nominal_value=5.0,
    )

    ensemble = EnsembleSpec.from_device(
        name="phase-k4c-feasibility-contract",
        device=base,
        variables=(variable,),
    )

    sampling_spec = SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=86420),
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

    def evaluate(
        candidate,
        protocol,
        realization,
    ):
        index = (
            realization.identity.sample_index
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
        evaluation_id="k4c-feasibility-contract",
    )

    metric_spec = MetricAnalysisSpec(
        "k4c-feasibility-metrics",
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

    return summarize_ensemble_metrics(
        analysis,
        EnsembleStatisticsSpec(),
    )


def reference(
    metric_name="response",
    unit="V",
    nominal_value=1.5,
):
    return NominalMetricReference(
        metric_name=metric_name,
        unit=unit,
        nominal_value=nominal_value,
    )


def comparison(
    source,
    ref,
):
    summary = next(
        item
        for item
        in source.metric_statistics
        if item.metric_name
        == ref.metric_name
    )

    if summary.denominator == 0:
        return NominalMetricComparison(
            reference=ref,
            denominator=0,
            population_mean=None,
            population_median=None,
            mean_delta=None,
            median_delta=None,
        )

    return NominalMetricComparison(
        reference=ref,
        denominator=summary.denominator,
        population_mean=summary.mean,
        population_median=summary.median,
        mean_delta=float(
            summary.mean
            - ref.nominal_value
        ),
        median_delta=float(
            summary.median
            - ref.nominal_value
        ),
    )


def valid_result(
    source=None,
):
    if source is None:
        source = population_statistics()

    refs = (
        reference(
            "response",
            "V",
            1.5,
        ),
        reference(
            "nested_value",
            "1",
            3.0,
        ),
    )

    comparisons = tuple(
        comparison(
            source,
            ref,
        )
        for ref in refs
    )

    return EnsembleFeasibilitySummary(
        source=source,
        nominal_references=refs,
        comparisons=comparisons,
    )


def test_nominal_reference_accepts_finite_value():
    ref = NominalMetricReference(
        metric_name="response",
        unit="V",
        nominal_value=2,
    )

    assert ref.nominal_value == 2.0
    assert type(ref.nominal_value) is float

    assert (
        ref.reference_hash
        == NominalMetricReference(
            "response",
            "V",
            2.0,
        ).reference_hash
    )


@pytest.mark.parametrize(
    "value",
    [
        True,
        "1.0",
        float("nan"),
        float("inf"),
        9007199254740993,
    ],
)
def test_nominal_reference_rejects_invalid_values(
    value,
):
    with pytest.raises(
        (TypeError, ValueError),
    ):
        NominalMetricReference(
            "response",
            "V",
            value,
        )


def test_nominal_comparison_accepts_complete_values():
    ref = reference()

    item = NominalMetricComparison(
        reference=ref,
        denominator=2,
        population_mean=2.0,
        population_median=2.5,
        mean_delta=0.5,
        median_delta=1.0,
    )

    assert item.denominator == 2
    assert item.mean_delta == 0.5
    assert item.median_delta == 1.0


def test_nominal_comparison_zero_denominator_requires_none():
    ref = reference()

    item = NominalMetricComparison(
        reference=ref,
        denominator=0,
        population_mean=None,
        population_median=None,
        mean_delta=None,
        median_delta=None,
    )

    assert item.denominator == 0

    with pytest.raises(
        ValueError,
        match="zero-denominator",
    ):
        replace(
            item,
            population_mean=1.0,
        )


def test_nominal_comparison_nonzero_requires_complete_values():
    ref = reference()

    with pytest.raises(
        ValueError,
        match="nonzero-denominator",
    ):
        NominalMetricComparison(
            reference=ref,
            denominator=1,
            population_mean=2.0,
            population_median=2.0,
            mean_delta=None,
            median_delta=0.5,
        )


def test_nominal_comparison_requires_exact_deltas():
    ref = reference()

    with pytest.raises(
        ValueError,
        match="mean_delta differs",
    ):
        NominalMetricComparison(
            reference=ref,
            denominator=1,
            population_mean=2.0,
            population_median=2.0,
            mean_delta=0.6,
            median_delta=0.5,
        )

    with pytest.raises(
        ValueError,
        match="median_delta differs",
    ):
        NominalMetricComparison(
            reference=ref,
            denominator=1,
            population_mean=2.0,
            population_median=2.0,
            mean_delta=0.5,
            median_delta=0.6,
        )


def test_feasibility_summary_counts_and_fractions():
    result = valid_result()

    assert result.attempted_count == 3
    assert result.assessed_count == 3
    assert result.feasible_count == 1
    assert result.infeasible_count == 2
    assert result.failed_count == 0

    assert (
        result.simulated_pass_fraction
        == 1 / 3
    )

    assert (
        result.ensemble_feasibility_fraction
        == 1 / 3
    )

    assert result.failure_fraction == 0.0


def test_feasibility_summary_keeps_failures_distinct():
    source = population_statistics(
        (
            1.0,
            2.0,
            3.0,
            4.0,
        ),
        fail_indices=(
            3,
        ),
        threshold=1.5,
    )

    result = valid_result(
        source,
    )

    assert result.attempted_count == 4
    assert result.assessed_count == 3
    assert result.feasible_count == 1
    assert result.infeasible_count == 2
    assert result.failed_count == 1

    assert (
        result.simulated_pass_fraction
        == 0.25
    )

    assert (
        result.ensemble_feasibility_fraction
        == 1 / 3
    )

    assert result.failure_fraction == 0.25


def test_feasibility_summary_all_failed_has_none_assessed_fraction():
    source = population_statistics(
        (
            1.0,
            2.0,
        ),
        fail_indices=(
            0,
            1,
        ),
    )

    refs = (
        reference(
            "response",
            "V",
            1.5,
        ),
    )

    result = EnsembleFeasibilitySummary(
        source=source,
        nominal_references=refs,
        comparisons=(
            comparison(
                source,
                refs[0],
            ),
        ),
    )

    assert result.attempted_count == 2
    assert result.assessed_count == 0
    assert result.feasible_count == 0
    assert result.infeasible_count == 0
    assert result.failed_count == 2

    assert result.simulated_pass_fraction == 0.0
    assert (
        result.ensemble_feasibility_fraction
        is None
    )
    assert result.failure_fraction == 1.0


def test_feasibility_summary_rejects_duplicate_references():
    source = population_statistics()

    ref = reference()

    with pytest.raises(
        ValueError,
        match="must be unique",
    ):
        EnsembleFeasibilitySummary(
            source=source,
            nominal_references=(
                ref,
                ref,
            ),
            comparisons=(
                comparison(
                    source,
                    ref,
                ),
                comparison(
                    source,
                    ref,
                ),
            ),
        )


def test_feasibility_summary_rejects_unknown_metric_reference():
    source = population_statistics()

    ref = reference(
        "unknown",
        "V",
        1.0,
    )

    comparison_item = NominalMetricComparison(
        reference=ref,
        denominator=3,
        population_mean=2.0,
        population_median=2.0,
        mean_delta=1.0,
        median_delta=1.0,
    )

    with pytest.raises(
        ValueError,
        match="absent from source",
    ):
        EnsembleFeasibilitySummary(
            source=source,
            nominal_references=(
                ref,
            ),
            comparisons=(
                comparison_item,
            ),
        )


def test_feasibility_summary_rejects_unit_mismatch():
    source = population_statistics()

    ref = reference(
        "response",
        "A",
        1.5,
    )

    comparison_item = NominalMetricComparison(
        reference=ref,
        denominator=3,
        population_mean=2.0,
        population_median=2.0,
        mean_delta=0.5,
        median_delta=0.5,
    )

    with pytest.raises(
        ValueError,
        match="unit differs",
    ):
        EnsembleFeasibilitySummary(
            source=source,
            nominal_references=(
                ref,
            ),
            comparisons=(
                comparison_item,
            ),
        )


def test_feasibility_summary_requires_reference_order():
    source = population_statistics()

    first = reference(
        "response",
        "V",
        1.5,
    )

    second = reference(
        "nested_value",
        "1",
        3.0,
    )

    with pytest.raises(
        ValueError,
        match="reference order",
    ):
        EnsembleFeasibilitySummary(
            source=source,
            nominal_references=(
                first,
                second,
            ),
            comparisons=(
                comparison(
                    source,
                    second,
                ),
                comparison(
                    source,
                    first,
                ),
            ),
        )


def test_feasibility_summary_requires_source_values():
    source = population_statistics()

    ref = reference()

    valid = comparison(
        source,
        ref,
    )

    wrong = replace(
        valid,
        population_mean=2.5,
        mean_delta=1.0,
    )

    with pytest.raises(
        ValueError,
        match="population mean differs",
    ):
        EnsembleFeasibilitySummary(
            source=source,
            nominal_references=(
                ref,
            ),
            comparisons=(
                wrong,
            ),
        )


def test_feasibility_summary_records_runtime_provenance():
    result = valid_result()

    runtime = result.runtime

    assert set(runtime) == {
        "python",
        "python_implementation",
        "ncmemsim",
        "algorithm",
    }

    assert (
        runtime["algorithm"]
        == "phase-k-feasibility-nominal-comparison-v1"
    )


def test_feasibility_summary_serialization_has_explicit_denominators():
    result = valid_result()

    payload = result.to_dict()

    assert payload[
        "simulated_pass_fraction"
    ] == {
        "value": 1 / 3,
        "numerator": 1,
        "denominator": 3,
    }

    assert payload[
        "ensemble_feasibility_fraction"
    ] == {
        "value": 1 / 3,
        "numerator": 1,
        "denominator": 3,
    }

    assert payload[
        "failure_fraction"
    ] == {
        "value": 0.0,
        "numerator": 0,
        "denominator": 3,
    }


def test_feasibility_summary_hashes_are_deterministic():
    source = population_statistics()

    first = valid_result(
        source,
    )

    second = valid_result(
        source,
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


def test_feasibility_summary_requires_matching_comparison_count():
    source = population_statistics()

    first = reference(
        "response",
        "V",
        1.5,
    )

    second = reference(
        "nested_value",
        "1",
        3.0,
    )

    with pytest.raises(
        ValueError,
        match="comparisons must match",
    ):
        EnsembleFeasibilitySummary(
            source=source,
            nominal_references=(
                first,
                second,
            ),
            comparisons=(
                comparison(
                    source,
                    first,
                ),
            ),
        )


def test_feasibility_summary_requires_source_denominator():
    source = population_statistics()

    ref = reference()

    valid = comparison(
        source,
        ref,
    )

    wrong = replace(
        valid,
        denominator=2,
    )

    with pytest.raises(
        ValueError,
        match="denominator differs",
    ):
        EnsembleFeasibilitySummary(
            source=source,
            nominal_references=(
                ref,
            ),
            comparisons=(
                wrong,
            ),
        )


def test_feasibility_summary_requires_source_median():
    source = population_statistics()

    ref = reference()

    valid = comparison(
        source,
        ref,
    )

    wrong = replace(
        valid,
        population_median=2.5,
        median_delta=1.0,
    )

    with pytest.raises(
        ValueError,
        match="population median differs",
    ):
        EnsembleFeasibilitySummary(
            source=source,
            nominal_references=(
                ref,
            ),
            comparisons=(
                wrong,
            ),
        )


def test_summarize_feasibility_without_nominal_references():
    source = population_statistics()

    result = summarize_ensemble_feasibility(
        source,
    )

    assert result.source is source
    assert result.nominal_references == ()
    assert result.comparisons == ()

    assert result.attempted_count == 3
    assert result.assessed_count == 3
    assert result.feasible_count == 1
    assert result.infeasible_count == 2
    assert result.failed_count == 0

    assert (
        result.simulated_pass_fraction
        == 1 / 3
    )

    assert (
        result.ensemble_feasibility_fraction
        == 1 / 3
    )

    assert result.failure_fraction == 0.0


def test_summarize_feasibility_builds_nominal_comparisons():
    source = population_statistics()

    refs = (
        reference(
            "response",
            "V",
            1.5,
        ),
        reference(
            "nested_value",
            "1",
            3.0,
        ),
    )

    result = summarize_ensemble_feasibility(
        source,
        refs,
    )

    assert result.nominal_references == refs
    assert len(result.comparisons) == 2

    response = result.comparisons[0]

    assert response.reference == refs[0]
    assert response.denominator == 3
    assert response.population_mean == 2.0
    assert response.population_median == 2.0
    assert response.mean_delta == 0.5
    assert response.median_delta == 0.5

    nested = result.comparisons[1]

    assert nested.reference == refs[1]
    assert nested.denominator == 3
    assert nested.population_mean == 4.0
    assert nested.population_median == 4.0
    assert nested.mean_delta == 1.0
    assert nested.median_delta == 1.0


def test_summarize_feasibility_all_failed_has_empty_comparison_values():
    source = population_statistics(
        (
            1.0,
            2.0,
        ),
        fail_indices=(
            0,
            1,
        ),
    )

    ref = reference(
        "response",
        "V",
        1.5,
    )

    result = summarize_ensemble_feasibility(
        source,
        (
            ref,
        ),
    )

    item = result.comparisons[0]

    assert item.denominator == 0
    assert item.population_mean is None
    assert item.population_median is None
    assert item.mean_delta is None
    assert item.median_delta is None

    assert result.simulated_pass_fraction == 0.0
    assert (
        result.ensemble_feasibility_fraction
        is None
    )
    assert result.failure_fraction == 1.0


def test_summarize_feasibility_rejects_unknown_metric():
    source = population_statistics()

    ref = reference(
        "unknown",
        "V",
        1.0,
    )

    with pytest.raises(
        ValueError,
        match="absent from source",
    ):
        summarize_ensemble_feasibility(
            source,
            (
                ref,
            ),
        )


def test_summarize_feasibility_rejects_unit_mismatch():
    source = population_statistics()

    ref = reference(
        "response",
        "A",
        1.5,
    )

    with pytest.raises(
        ValueError,
        match="unit differs",
    ):
        summarize_ensemble_feasibility(
            source,
            (
                ref,
            ),
        )


def test_summarize_feasibility_rejects_duplicate_references():
    source = population_statistics()

    ref = reference()

    with pytest.raises(
        ValueError,
        match="must be unique",
    ):
        summarize_ensemble_feasibility(
            source,
            (
                ref,
                ref,
            ),
        )


def test_summarize_feasibility_rejects_invalid_source():
    with pytest.raises(
        TypeError,
        match="source must be",
    ):
        summarize_ensemble_feasibility(
            object(),
        )


@pytest.mark.parametrize(
    "refs",
    [
        "response",
        b"response",
        (
            object(),
        ),
    ],
)
def test_summarize_feasibility_rejects_invalid_references(
    refs,
):
    source = population_statistics()

    with pytest.raises(
        TypeError,
        match="nominal_references",
    ):
        summarize_ensemble_feasibility(
            source,
            refs,
        )


def test_summarize_feasibility_does_not_mutate_source():
    source = population_statistics()

    before_payload = source.to_dict()
    before_hash = source.result_hash

    summarize_ensemble_feasibility(
        source,
        (
            reference(),
        ),
    )

    assert source.to_dict() == before_payload
    assert source.result_hash == before_hash


def test_summarize_feasibility_is_deterministic():
    source = population_statistics()

    refs = (
        reference(
            "response",
            "V",
            1.5,
        ),
        reference(
            "nested_value",
            "1",
            3.0,
        ),
    )

    first = summarize_ensemble_feasibility(
        source,
        refs,
    )

    second = summarize_ensemble_feasibility(
        source,
        refs,
    )

    assert first.to_dict() == second.to_dict()
    assert first.analysis_hash == second.analysis_hash
    assert first.result_hash == second.result_hash


def test_summarize_feasibility_fails_closed_on_nonfinite_delta():
    source = population_statistics()

    response = source.metric_statistics[0]

    extreme = replace(
        response,
        minimum=1e308,
        maximum=1e308,
        mean=1e308,
        variance=0.0,
        standard_deviation=0.0,
        median=1e308,
        quantiles=tuple(
            (
                probability,
                1e308,
            )
            for probability, _
            in response.quantiles
        ),
    )

    altered_source = replace(
        source,
        metric_statistics=(
            extreme,
            source.metric_statistics[1],
        ),
    )

    ref = reference(
        "response",
        "V",
        -1e308,
    )

    with pytest.raises(
        ValueError,
        match="mean_delta is not finitely representable",
    ):
        summarize_ensemble_feasibility(
            altered_source,
            (
                ref,
            ),
        )
