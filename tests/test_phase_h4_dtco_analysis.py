from dataclasses import replace, FrozenInstanceError
import math
import pytest
from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (BindingScope, ParameterBinding, UniformVariation,
    VariationDefinition, VariationKind, VariationProvenance, SamplingSpec,
    sample_variations, propagate_samples, MetricDefinition, MetricConstraint,
    MetricAnalysisSpec, ConstraintOperator, SampleAnalysisSpec, analyze_samples)
import ncmemsim.dtco.sample_analysis as analysis_module


def source(outputs):
    definition=VariationDefinition("temperature",ParameterBinding(BindingScope.DEVICE,("temperature_K",)),
        UniformVariation(295,305),"K",VariationKind.PARAMETER_ESTIMATION,VariationProvenance("Assumed","Tests"))
    manifest=sample_variations(SamplingSpec((definition,),123,len(outputs)))
    def evaluate(candidate,protocol,point):
        output=outputs[point.index]
        if isinstance(output,Exception): raise output
        return output
    return propagate_samples(manifest,DeviceBuilder.v2(n_fgs=1),evaluate,evaluation_id="h4-test")


def spec(constraint=True,quantiles=(0,0.25,0.5,0.75,1)):
    metrics=(MetricDefinition("response",("response",),"V"),)
    constraints=(MetricConstraint("max","response",ConstraintOperator.LE,2,"V"),) if constraint else ()
    return SampleAnalysisSpec(MetricAnalysisSpec("responses",metrics,constraints),quantiles)


def test_mixed_counts_denominators_and_statistics_include_infeasible():
    result=analyze_samples(source([{"response":1},{"response":3},RuntimeError("failure"),{}]),spec())
    assert (result.total_count,result.assessed_count,result.feasible_count,result.infeasible_count,result.failure_count)==(4,2,1,1,2)
    assert result.observed_feasible_fraction_all_attempted==0.25
    assert result.conditional_feasible_fraction_assessed==0.5
    assert result.failure_fraction_all_attempted==0.5
    data=result.to_dict()
    assert data["counts"]["propagation_failed"]==1 and data["counts"]["extraction_failed"]==1
    assert data["fractions"]["conditional_feasible_fraction_assessed"]=={"value":0.5,"numerator":1,"denominator":2}
    stats=result.metric_statistics[0]
    assert stats["sample_indices"]==[0,1] and stats["denominator"]==2 and stats["unit"]=="V"
    assert (stats["minimum"],stats["maximum"],stats["mean"],stats["standard_deviation"])==(1,3,2,1)
    assert [q["value"] for q in stats["quantiles"]]==[1,1.5,2,2.5,3]
    assert [p.status for p in result.points]==["feasible","infeasible","failed","failed"]
    assert result.points[2].source.failure_stage=="evaluation"


def test_zero_assessed_is_undefined_not_zero_filled():
    result=analyze_samples(source([RuntimeError("bad"),{}]),spec())
    assert result.assessed_count==0 and result.failure_count==2
    assert result.observed_feasible_fraction_all_attempted==0
    assert result.conditional_feasible_fraction_assessed is None
    assert result.failure_fraction_all_attempted==1
    stats=result.metric_statistics[0]
    assert stats["sample_indices"]==[] and stats["denominator"]==0
    assert all(stats[key] is None for key in ["mean","minimum","maximum","standard_deviation"])
    assert all(q["value"] is None for q in stats["quantiles"])
    assert 'null' in result.to_json()


def test_singleton_population_std_and_inclusive_threshold():
    result=analyze_samples(source([{"response":2}]),spec())
    assert result.feasible_count==1
    assert result.metric_statistics[0]["standard_deviation"]==0
    assert all(q["value"]==2 for q in result.metric_statistics[0]["quantiles"])


def test_no_constraints_all_assessed_feasible_and_no_absolute_value():
    result=analyze_samples(source([{"response":-3},{"response":-1}]),spec(False))
    assert result.feasible_count==2
    assert result.metric_statistics[0]["mean"]==-2
    assert result.conditional_feasible_fraction_assessed==1


@pytest.mark.parametrize("value", [True,"1",None,[],{},2**53+1,10**1000])
def test_invalid_or_lossy_metric_is_extraction_failure(value):
    result=analyze_samples(source([{"response":value}]),spec())
    assert result.failure_count==1 and result.points[0].failure_stage=="extraction"
    assert result.points[0].metrics=={} and result.points[0].constraints==()


@pytest.mark.parametrize("quantiles", [(True,),(-0.1,),(1.1,),(math.nan,),(math.inf,),('0.5',),(0.5,0.5)])
def test_invalid_quantiles(quantiles):
    with pytest.raises(ValueError): spec(quantiles=quantiles)


def test_declared_quantile_order_and_empty_selection():
    result=analyze_samples(source([{"response":1},{"response":3}]),spec(quantiles=(1,0,0.5)))
    assert [q["value"] for q in result.metric_statistics[0]["quantiles"]]==[3,1,2]
    assert analyze_samples(result.source,spec(quantiles=())).metric_statistics[0]["quantiles"]==[]


def test_all_metrics_complete_case_and_units_stay_distinct():
    definitions=MetricAnalysisSpec("mixed",(MetricDefinition("response",("response",),"V"),MetricDefinition("duration",("duration",),"s")))
    result=analyze_samples(source([{"response":1,"duration":0.1},{"response":2}]),SampleAnalysisSpec(definitions))
    assert result.assessed_count==1 and result.failure_count==1
    assert result.points[1].metric_values==()
    assert [s["unit"] for s in result.metric_statistics]==["V","s"]
    assert all(s["sample_indices"]==[0] for s in result.metric_statistics)
    with pytest.raises(ValueError): MetricAnalysisSpec("bad",definitions.metrics,
        (MetricConstraint("c","response",ConstraintOperator.LE,2,"s"),))


def test_nested_array_metric_and_ge_constraint():
    definitions=MetricAnalysisSpec("nested",(MetricDefinition("value",("nested",0),"1"),),
        (MetricConstraint("min","value",ConstraintOperator.GE,0,"1"),))
    result=analyze_samples(source([{"nested":[0]},{"nested":[-1]}]),SampleAnalysisSpec(definitions))
    assert result.feasible_count==1 and result.infeasible_count==1


def test_wide_finite_values_no_overflow_in_mean_std_quantiles():
    result=analyze_samples(source([{"response":-1e308},{"response":1e308}]),spec(False))
    stats=result.metric_statistics[0]
    assert stats["mean"]==0 and stats["standard_deviation"]==1e308
    assert [q["value"] for q in stats["quantiles"]]==[-1e308,-5e307,0,5e307,1e308]


def test_source_is_unchanged_repeat_and_snapshot_immutability():
    original=source([{"response":1},{"response":3}]);before=original.to_json()
    a=analyze_samples(original,spec());b=analyze_samples(original,spec())
    assert original.to_json()==before and a.result_hash==b.result_hash
    payload=a.to_dict();payload["metric_statistics"][0]["sample_indices"].clear()
    assert a.metric_statistics[0]["sample_indices"]==[0,1]
    with pytest.raises(FrozenInstanceError): a.points=()
    with pytest.raises(ValueError): replace(a,points=tuple(reversed(a.points)))
    with pytest.raises(ValueError): replace(a,points=a.points[:-1])
    assert a.analysis_hash!=analyze_samples(original,spec(quantiles=(0.5,))).analysis_hash


def test_runtime_identity_is_snapshotted(monkeypatch):
    a=analyze_samples(source([{"response":1}]),spec());before=a.analysis_hash
    monkeypatch.setattr(analysis_module.platform,"python_version",lambda:"changed")
    assert a.analysis_hash==before


def test_interrupts_during_extraction_propagate(monkeypatch):
    def stop(*args): raise KeyboardInterrupt
    original=source([{"response":1}]);monkeypatch.setattr(MetricDefinition,"extract",stop)
    with pytest.raises(KeyboardInterrupt): analyze_samples(original,spec())


def test_all_infeasible_still_assessed_and_summarized():
    result=analyze_samples(source([{"response":3},{"response":5}]),spec())
    assert result.assessed_count==2 and result.infeasible_count==2 and result.failure_count==0
    assert result.observed_feasible_fraction_all_attempted==0
    assert result.conditional_feasible_fraction_assessed==0
    assert result.metric_statistics[0]["mean"]==4
