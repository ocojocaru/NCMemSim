import csv
from dataclasses import FrozenInstanceError
import importlib.util
from io import StringIO
import json
from pathlib import Path
import pytest
from ncmemsim.dtco import RobustDTCOReport, write_robust_dtco_report, build_robust_dtco_report
from ncmemsim.hashing import canonical_hash


def reference(failures=False):
    path=Path(__file__).resolve().parents[1]/"examples/phase_h6_robust_dtco_reference.py"
    spec=importlib.util.spec_from_file_location("h6_reference",path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.build_reference_report(include_failures=failures)


@pytest.fixture(scope="module")
def report(): return reference()


@pytest.fixture(scope="module")
def failed_report(): return reference(True)


def test_real_reference_repeat_roundtrip_and_exact_samples(report):
    assert report.to_json()==reference().to_json()
    restored=RobustDTCOReport.from_json(report.to_json())
    assert restored.report_hash==report.report_hash
    payload=restored.to_dict()
    assert len(payload["analyses"])==2
    for section in payload["analyses"]:
        assert section["data"]["counts"]=={"total":4,"assessed":4,"feasible":4,"infeasible":0,"failed":0,"propagation_failed":0,"extraction_failed":0}
        assert len(section["data"]["source"]["manifest"]["samples"])==4
    assert all(c["data"]["status"]=="assessed" for c in payload["nominal_comparisons"])
    assert len(payload["robust_pareto"]["data"]["points"])==2


def test_failure_reference_keeps_all_stages_and_denominators(failed_report):
    payload=failed_report.to_dict()
    for section in payload["analyses"]:
        data=section["data"]
        assert data["counts"]["total"]==4 and data["counts"]["assessed"]==1 and data["counts"]["failed"]==3
        assert data["counts"]["propagation_failed"]==2 and data["counts"]["extraction_failed"]==1
        assert data["source"]["points"][1]["failure"]["stage"]=="evaluation"
        assert data["source"]["points"][3]["failure"]["stage"]=="serialization"
        assert data["points"][2]["failure"]["stage"]=="extraction"
        assert data["fractions"]["observed_feasible_fraction_all_attempted"]["value"]==0.25
        assert data["fractions"]["conditional_feasible_fraction_assessed"]["value"]==1
    assert RobustDTCOReport.from_json(failed_report.to_json()).report_hash==failed_report.report_hash


@pytest.mark.parametrize("kind", ["outer","analysis","source","manifest","nominal","robust","missing","duplicate"])
def test_tampering_rejected_even_if_outer_hash_refreshed(report,kind):
    raw=report.to_dict()
    if kind=="outer": raw["report_hash"]="0"*64
    elif kind=="analysis": raw["analyses"][0]["data"]["counts"]["total"]+=1
    elif kind=="source": raw["analyses"][0]["data"]["source"]["points"][0]["output"]["signed_shift_V"]+=1
    elif kind=="manifest": raw["analyses"][0]["data"]["source"]["manifest"]["samples"][0]["values"][0]=99
    elif kind=="nominal": raw["nominal_comparisons"][0]["data"]["nominal_hash"]="0"*64
    elif kind=="robust": raw["robust_pareto"]["data"]["points"].reverse()
    elif kind=="missing": raw["nominal_comparisons"].pop()
    if kind not in ("outer","duplicate"):
        raw["report_hash"]=canonical_hash({k:v for k,v in raw.items() if k!="report_hash"})
    text=json.dumps(raw)
    if kind=="duplicate": text=text.replace('"name":','"name": "duplicate", "name":',1)
    with pytest.raises(ValueError): RobustDTCOReport.from_json(text)


def test_counts_and_fraction_consistency_rejected_with_section_rehashed(report):
    for key in ["counts","fractions"]:
        raw=report.to_dict();section=raw["analyses"][0]
        if key=="counts": section["data"]["counts"]["total"]=99
        else: section["data"]["fractions"]["conditional_feasible_fraction_assessed"]["denominator"]=99
        section["result_hash"]=canonical_hash(section["data"])
        raw["report_hash"]=canonical_hash({k:v for k,v in raw.items() if k!="report_hash"})
        with pytest.raises(ValueError): RobustDTCOReport.from_json(json.dumps(raw))


def test_csv_rows_include_every_failure_and_units(failed_report):
    samples=list(csv.DictReader(StringIO(failed_report.samples_csv())))
    assert len(samples)==8
    assert sum(r["analysis_status"]=="failed" for r in samples)==6
    assert all(r["assignments_json"] and r["propagation_failure_json"] for r in samples)
    stats=list(csv.DictReader(StringIO(failed_report.statistics_csv())))
    assert len(stats)==6 and {r["unit"] for r in stats}=={"V","s","1"}
    assert all(r["denominator"]=="1" and json.loads(r["sample_indices_json"])==[0] for r in stats)
    assert len(list(csv.DictReader(StringIO(failed_report.nominal_csv()))))==6
    assert len(list(csv.DictReader(StringIO(failed_report.robust_csv()))))==2


def test_export_six_utf8_artifacts_restores_and_never_overwrites(tmp_path,report):
    paths=write_robust_dtco_report(report,tmp_path/"report")
    assert {p.name for p in paths}=={"manifest.json","samples.csv","statistics.csv","nominal.csv","robust.csv","report.md"}
    assert RobustDTCOReport.from_json(paths[0].read_text(encoding="utf-8")).report_hash==report.report_hash
    before={p.name:p.read_bytes() for p in paths}
    with pytest.raises(FileExistsError): write_robust_dtco_report(report,tmp_path/"report")
    assert before=={p.name:p.read_bytes() for p in paths}
    assert report.report_hash in (tmp_path/"report/report.md").read_text(encoding="utf-8")


def test_snapshot_immutable_and_metadata_validation(report):
    data=report.to_dict();data["analyses"].clear()
    assert len(report.to_dict()["analyses"])==2
    with pytest.raises(FrozenInstanceError): report.payload_json="{}"
    raw=report.to_dict();raw["metadata"]["invalid"]=float("nan")
    with pytest.raises(ValueError): RobustDTCOReport(json.dumps({k:v for k,v in raw.items() if k!="report_hash"}))
    with pytest.raises(ValueError): RobustDTCOReport.from_json('[]')


def test_builder_rejects_wrong_input_types():
    with pytest.raises(TypeError): build_robust_dtco_report([],name="empty")
    with pytest.raises(TypeError): build_robust_dtco_report([{}],name="bad")


def typed_study(name="a",failed=False):
    from ncmemsim import DeviceBuilder
    from ncmemsim.dtco import (BindingScope,ParameterBinding,UniformVariation,VariationDefinition,
        VariationKind,VariationProvenance,SamplingSpec,sample_variations,propagate_samples,
        MetricDefinition,MetricAnalysisSpec,SampleAnalysisSpec,analyze_samples,evaluate_nominal,compare_nominal)
    d=DeviceBuilder.v2(n_fgs=1,name=name)
    v=VariationDefinition("t",ParameterBinding(BindingScope.DEVICE,("temperature_K",)),UniformVariation(295,305),
        "K",VariationKind.PARAMETER_ESTIMATION,VariationProvenance("Assumed","Test"))
    m=sample_variations(SamplingSpec((v,),123,1))
    def callback(c,p):
        if failed: raise RuntimeError("failed test response")
        return {"temperature":c.temperature_K}
    propagated=propagate_samples(m,d,lambda c,p,point:callback(c,p),evaluation_id="report-test")
    a=analyze_samples(propagated,SampleAnalysisSpec(MetricAnalysisSpec("temperature",(MetricDefinition("t",("temperature",),"K"),))))
    n=evaluate_nominal(d,callback,evaluation_id="report-test")
    return a,compare_nominal(a,n)


def test_optional_sections_and_source_mismatch_rejection():
    from ncmemsim.dtco import (RobustObjective,RobustStatistic,ObjectiveDirection,RobustFailurePolicy,RobustParetoSpec,analyze_robust_pareto)
    a,c=typed_study("a");b,d=typed_study("b")
    optional=build_robust_dtco_report((a,),name="optional")
    assert optional.to_dict()["nominal_comparisons"]==[None]
    assert len(list(csv.DictReader(StringIO(optional.nominal_csv()))))==0
    assert len(list(csv.DictReader(StringIO(optional.robust_csv()))))==0
    with pytest.raises(ValueError): build_robust_dtco_report((a,),name="mismatch",nominal_comparisons=(d,))
    with pytest.raises(ValueError): build_robust_dtco_report((a,),name="count",nominal_comparisons=())
    spec=RobustParetoSpec("front",(RobustObjective("mean","t","K",ObjectiveDirection.MINIMIZE,RobustStatistic.MEAN),),RobustFailurePolicy.REQUIRE_NO_FAILURES,1,1)
    robust=analyze_robust_pareto((a,b),spec)
    with pytest.raises(ValueError): build_robust_dtco_report((b,a),name="reordered",robust_pareto=robust)


def test_zero_assessed_and_nominal_failure_exports_remain_explicit():
    a,c=typed_study(failed=True)
    report=build_robust_dtco_report((a,),name="all failures",nominal_comparisons=(c,))
    stats=list(csv.DictReader(StringIO(report.statistics_csv())))[0]
    assert stats["denominator"]=="0" and stats["mean"]=="null" and stats["sample_indices_json"]=="[]"
    row=list(csv.DictReader(StringIO(report.nominal_csv())))[0]
    assert row["status"]=="failed" and json.loads(row["failure_or_undefined_reason_json"])["stage"]=="evaluation"
    assert RobustDTCOReport.from_json(report.to_json()).report_hash==report.report_hash
