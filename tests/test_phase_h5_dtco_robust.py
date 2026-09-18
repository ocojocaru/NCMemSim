from dataclasses import replace, FrozenInstanceError
import json
import math
import pytest
from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (BindingScope, ParameterBinding, UniformVariation, VariationDefinition,
    VariationKind, VariationProvenance, SamplingSpec, sample_variations, propagate_samples,
    MetricDefinition, MetricAnalysisSpec, MetricConstraint, ConstraintOperator, ObjectiveDirection,
    SampleAnalysisSpec, analyze_samples, evaluate_nominal, compare_nominal, RobustStatistic,
    RobustFailurePolicy, RobustObjective, RobustParetoSpec, analyze_robust_pareto)
from ncmemsim.program_protocol import ProgramPulseReadProtocol, run_program_pulse_read
from ncmemsim.simulator import Simulator


def device(): return DeviceBuilder.v2(n_fgs=1,name="h5-reference")


def analysis(values,*,nominal=None,evaluation_id="h5-test",parameters=None,quantiles=(0,0.5,1)):
    variation=VariationDefinition("temperature",ParameterBinding(BindingScope.DEVICE,("temperature_K",)),
        UniformVariation(295,305),"K",VariationKind.PARAMETER_ESTIMATION,VariationProvenance("Assumed","Test"))
    m=sample_variations(SamplingSpec((variation,),123,len(values)))
    def evaluate(candidate,protocol,point):
        value=values[point.index]
        if isinstance(value,Exception): raise value
        if isinstance(value,dict): return value
        return {"response":value}
    source=propagate_samples(m,nominal or device(),evaluate,evaluation_id=evaluation_id,evaluation_parameters=parameters)
    metrics=MetricAnalysisSpec("response",(MetricDefinition("response",("response",),"V"),),
        (MetricConstraint("max","response",ConstraintOperator.LE,4,"V"),))
    return analyze_samples(source,SampleAnalysisSpec(metrics,quantiles))


def objective(name="mean",statistic=RobustStatistic.MEAN,direction=ObjectiveDirection.MAXIMIZE,quantile=None):
    return RobustObjective(name,"response","V",direction,statistic,quantile)


def spec(policy=RobustFailurePolicy.REQUIRE_NO_FAILURES,minimum=1,fraction=0,objectives=None):
    return RobustParetoSpec("robust",objectives or (objective(),),policy,minimum,fraction)


def nominal(value=2,**kwargs):
    return evaluate_nominal(device(),lambda c,p:{"response":value},evaluation_id="h5-test",**kwargs)


def test_nominal_comparison_signed_difference_feasibility_and_links():
    a=analysis([-3,-1]);n=nominal(-1);comparison=compare_nominal(a,n)
    data=comparison.to_dict()
    assert data["status"]=="assessed" and data["nominal_feasible"] is True
    assert data["source_analysis_hash"]==a.result_hash
    metric=data["metrics"][0]
    assert metric["nominal_value"]==-1 and metric["mean_minus_nominal"]==-1
    assert metric["sample_statistics"]["mean"]==-2 and metric["unit"]=="V"
    data["metrics"].clear()
    assert compare_nominal(a,n).result_hash==comparison.result_hash


@pytest.mark.parametrize("mismatch", ["device","material","protocol","id","parameters","runtime"])
def test_nominal_mismatches_rejected(mismatch):
    a=analysis([1,3]);d=device();kwargs={"evaluation_id":"h5-test"}
    if mismatch=="device": d.temperature_K=301.0
    elif mismatch=="material": object.__setattr__(d.floating_gates()[0].nc_material,"phi_barrier_prog_eV",9)
    elif mismatch=="protocol": kwargs["base_protocol"]=ProgramPulseReadProtocol(5,1e-7)
    elif mismatch=="id": kwargs["evaluation_id"]="other"
    elif mismatch=="parameters": kwargs["evaluation_parameters"]={"other":True}
    n=evaluate_nominal(d,lambda c,p:{"response":2},**kwargs)
    if mismatch=="runtime":
        runtime=json.loads(n.runtime_json);runtime["numpy"]="other"
        object.__setattr__(n,"runtime_json",json.dumps(runtime,sort_keys=True,separators=(",",":")))
    with pytest.raises(ValueError): compare_nominal(a,n)


@pytest.mark.parametrize("kind", ["evaluation","serialization","extraction"])
def test_nominal_failures_explicit(kind):
    def callback(c,p):
        if kind=="evaluation": raise RuntimeError("bad")
        if kind=="serialization": return {"response":math.nan}
        return {}
    n=evaluate_nominal(device(),callback,evaluation_id="h5-test")
    data=compare_nominal(analysis([1,3]),n).to_dict()
    assert data["status"]=="failed" and data["failure"]["stage"]==kind
    assert data["metrics"]==[] and data["nominal_feasible"] is None


def test_nominal_no_assessed_and_overflow_difference_are_undefined():
    data=compare_nominal(analysis([{}]),nominal()).to_dict()["metrics"][0]
    assert data["mean_minus_nominal"] is None and data["difference_undefined_reason"]=="no_assessed_samples"
    data=compare_nominal(analysis([1e308]),nominal(-1e308)).to_dict()["metrics"][0]
    assert data["mean_minus_nominal"] is None and data["difference_undefined_reason"]=="arithmetic_overflow"


def test_nominal_isolation_and_output_snapshot():
    d=device();output={"response":1}
    def mutate(candidate,p): candidate.layers.clear();return output
    n=evaluate_nominal(d,mutate,evaluation_id="h5-test");output["response"]=9
    assert len(d.layers)>0 and n.output=={"response":1}
    with pytest.raises(FrozenInstanceError): n.status="failed"


@pytest.mark.parametrize("error", [KeyboardInterrupt,SystemExit])
def test_nominal_interrupts(error):
    def stop(c,p): raise error
    with pytest.raises(error): evaluate_nominal(device(),stop,evaluation_id="h5-test")


def test_pareto_mean_exact_all_fronts_ties_and_source_order():
    sources=(analysis([1,3]),analysis([2,4]),analysis([2,4]),analysis([-3,-1]))
    result=analyze_robust_pareto(sources,spec())
    assert result.fronts==((1,2),(0,),(3,)) and result.pareto_indices==(1,2)
    assert [p["rank"] for p in result.to_dict()["points"]]==[1,0,0,2]
    assert result.result_hash==analyze_robust_pareto(sources,spec()).result_hash
    assert analyze_robust_pareto(sources,spec(objectives=(objective(direction=ObjectiveDirection.MINIMIZE),))).pareto_indices==(3,)


def test_multiobjective_tradeoff_no_weights_or_absolute_value():
    sources=(analysis([0,4]),analysis([1,3]),analysis([1,4]))
    objectives=(objective("maximum",RobustStatistic.MAXIMUM),objective("spread",RobustStatistic.STANDARD_DEVIATION,ObjectiveDirection.MINIMIZE))
    assert analyze_robust_pareto(sources,spec(objectives=objectives)).fronts==((1,2),(0,))


def test_failure_and_assessment_feasible_fraction_eligibility_explicit():
    sources=(analysis([1,RuntimeError("bad")]),analysis([1,3]),analysis([{}]),analysis([9,9]))
    strict=analyze_robust_pareto(sources,spec(minimum=2,fraction=0.5)).to_dict()
    assert strict["fronts"]==[[1]]
    assert strict["points"][0]["exclusion_reasons"]==["insufficient_assessed_samples","failures_disallowed"]
    assert "undefined_objective" in strict["points"][2]["exclusion_reasons"]
    assert strict["points"][3]["exclusion_reasons"]==["feasible_fraction_below_minimum"]
    allow=analyze_robust_pareto(sources,spec(RobustFailurePolicy.ALLOW_ASSESSED_WITH_FAILURES,fraction=0.5))
    assert allow.fronts==((1,),(0,))
    assert allow.to_dict()["points"][0]["objectives"]=={"mean":1}


def test_no_eligible_studies_retained_with_empty_fronts():
    result=analyze_robust_pareto((analysis([{}]),),spec())
    assert result.fronts==() and result.pareto_indices==()
    assert result.to_dict()["points"][0]["rank"] is None


def test_quantile_selection_exact_and_noncomputed_rejected():
    o=objective("median",RobustStatistic.QUANTILE,quantile=0.5)
    result=analyze_robust_pareto((analysis([1,3]),),spec(objectives=(o,)))
    assert result.to_dict()["points"][0]["objectives"]=={"median":2}
    with pytest.raises(ValueError): analyze_robust_pareto((analysis([1,3]),),spec(objectives=(replace(o,quantile=0.25),)))


@pytest.mark.parametrize("change", ["unit","metric","definitions","evaluator","parameters"])
def test_incomparable_studies_or_objectives_rejected(change):
    a=analysis([1,3]);sources=(a,);s=spec()
    if change=="unit": s=spec(objectives=(replace(objective(),unit="s"),))
    elif change=="metric": s=spec(objectives=(replace(objective(),metric_name="unknown"),))
    elif change=="definitions": sources=(a,analysis([1,3],quantiles=(0.5,)))
    elif change=="evaluator": sources=(a,analysis([1,3],evaluation_id="different"))
    elif change=="parameters": sources=(a,analysis([1,3],parameters={"different":True}))
    with pytest.raises(ValueError): analyze_robust_pareto(sources,s)


@pytest.mark.parametrize("q", [None,True,-1,2,math.inf,math.nan])
def test_invalid_quantile_objective(q):
    with pytest.raises(ValueError): objective(statistic=RobustStatistic.QUANTILE,quantile=q)


def test_typed_policy_statistic_direction_and_bounds():
    with pytest.raises(ValueError): objective(quantile=0.5)
    with pytest.raises(TypeError): replace(objective(),direction="maximize")
    with pytest.raises(TypeError): replace(objective(),statistic="mean")
    with pytest.raises(TypeError): replace(spec(),failure_policy="allow")
    for count in [0,True,1.5]:
        with pytest.raises(ValueError): spec(minimum=count)
    for fraction in [-1,2,True,math.nan]:
        with pytest.raises(ValueError): spec(fraction=fraction)
    with pytest.raises(ValueError): spec(objectives=(objective(),objective()))
    with pytest.raises(ValueError): analyze_robust_pareto((),spec())


def test_real_nominal_and_sampled_program_read_use_same_model():
    from ncmemsim.dtco import propagate_samples,analyze_samples
    d=device();p=ProgramPulseReadProtocol(5,1e-7)
    variation=VariationDefinition("duration",ParameterBinding(BindingScope.OPERATING,("program","time_s")),
        UniformVariation(1e-7,2e-7),"s",VariationKind.PARAMETER_ESTIMATION,VariationProvenance("Assumed","Protocol"))
    m=sample_variations(SamplingSpec((variation,),123,2))
    def physics(c,p): return {"response":run_program_pulse_read(Simulator(c),p).delta_vfb_V}
    source=propagate_samples(m,d,lambda c,p,point:physics(c,p),evaluation_id="physics-v1",base_protocol=p)
    metric_spec=SampleAnalysisSpec(MetricAnalysisSpec("response",(MetricDefinition("response",("response",),"V"),)))
    a=analyze_samples(source,metric_spec)
    n=evaluate_nominal(d,physics,evaluation_id="physics-v1",base_protocol=p)
    assert compare_nominal(a,n).to_dict()["status"]=="assessed"
