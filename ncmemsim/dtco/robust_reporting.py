"""Integrity-linked Robust DTCO snapshots and portable report artifacts."""
from __future__ import annotations
import csv
from dataclasses import dataclass
from io import StringIO
import json
from pathlib import Path
from typing import Any
from .._version import __version__
from ..hashing import canonical_hash
from .metrics import _label
from .sampling import SampleManifest
from .sample_analysis import SampleAnalysisResult
from .robust import NominalComparison, RobustParetoResult
from .sweep import _json_snapshot


def _section(value):
    return None if value is None else {"result_hash":value.result_hash,"data":value.to_dict()}


def _check(payload):
    if type(payload) is not dict or set(payload)!={"schema_version","name","ncmemsim_version","metadata","analyses","nominal_comparisons","robust_pareto"} or payload["schema_version"]!="dtco-robust-report-v1":
        raise ValueError("unsupported or incomplete robust report schema")
    _label(payload["name"],"report name");_label(payload["ncmemsim_version"],"package version")
    if type(payload["metadata"]) is not dict or type(payload["analyses"]) is not list or not payload["analyses"]:
        raise ValueError("report requires metadata object and analyses")
    analyses=payload["analyses"]
    if type(payload["nominal_comparisons"]) is not list or len(payload["nominal_comparisons"])!=len(analyses):
        raise ValueError("nominal comparison order/count mismatch")
    def section(value):
        if type(value) is not dict or set(value)!={"result_hash","data"} or canonical_hash(value["data"])!=value["result_hash"]:
            raise ValueError("section integrity mismatch")
        return value["data"]
    try:
        for index,wrapped in enumerate(analyses):
            data=section(wrapped);source=data["source"];study=source["study"]
            if data["schema_version"]!="dtco-sample-analysis-result-v1" or source["schema_version"]!="dtco-propagation-result-v1":
                raise ValueError("unsupported nested analysis schema")
            manifest=SampleManifest.from_json(_json_snapshot(source["manifest"]))
            if canonical_hash(source)!=data["source_result_hash"] or canonical_hash(study)!=source["study_hash"] or canonical_hash(study["nominal"])!=source["nominal_hash"] or study["manifest_hash"]!=manifest.manifest_hash:
                raise ValueError("propagation input identity mismatch")
            if data["analysis_hash"]!=canonical_hash({"schema_version":"dtco-sample-analysis-run-v1","spec":data["spec"],"source_result_hash":data["source_result_hash"],"runtime":data["runtime"]}):
                raise ValueError("sample analysis identity mismatch")
            if len(source["points"])!=manifest.spec.sample_count or len(data["points"])!=manifest.spec.sample_count:
                raise ValueError("samples omitted from report")
            successes=sum(p["status"]=="success" for p in source["points"])
            if source["success_count"]!=successes or source["failure_count"]!=len(source["points"])-successes:
                raise ValueError("propagation counts mismatch")
            names=tuple(v.name for v in manifest.spec.variations)
            for i,(point,assessed) in enumerate(zip(source["points"],data["points"])):
                raw=point["point"]
                expected=[{"name":name,"value":value} for name,value in zip(names,manifest.values[i])]
                if raw["schema_version"]!="dtco-sample-point-v1" or type(raw["index"]) is not int or type(assessed["index"]) is not int or raw["index"]!=i or raw["manifest_hash"]!=manifest.manifest_hash or _json_snapshot(raw["assignments"])!=_json_snapshot(expected) or point["point_hash"]!=canonical_hash(raw) or assessed["index"]!=i or assessed["point_hash"]!=point["point_hash"]:
                    raise ValueError("sample input/order identity mismatch")
            statuses=[p["status"] for p in data["points"]]
            if any(s not in ("feasible","infeasible","failed") for s in statuses):
                raise ValueError("invalid assessment status")
            expected_counts={"total":len(statuses),"assessed":sum(s!="failed" for s in statuses),
                "feasible":statuses.count("feasible"),"infeasible":statuses.count("infeasible"),"failed":statuses.count("failed"),
                "propagation_failed":sum(p["status"]=="failed" and p["failure"]["stage"]=="propagation" for p in data["points"]),
                "extraction_failed":sum(p["status"]=="failed" and p["failure"]["stage"]=="extraction" for p in data["points"])}
            if data["counts"]!=expected_counts or expected_counts["failed"]!=expected_counts["propagation_failed"]+expected_counts["extraction_failed"]:
                raise ValueError("assessment counts mismatch")
            for label,numerator,denominator in (("observed_feasible_fraction_all_attempted",expected_counts["feasible"],expected_counts["total"]),
                ("conditional_feasible_fraction_assessed",expected_counts["feasible"],expected_counts["assessed"]),
                ("failure_fraction_all_attempted",expected_counts["failed"],expected_counts["total"])):
                expected={"value":None if denominator==0 else numerator/denominator,"numerator":numerator,"denominator":denominator}
                if data["fractions"][label]!=expected: raise ValueError("fraction denominator/value mismatch")
            indices=[i for i,s in enumerate(statuses) if s!="failed"]
            metrics=data["spec"]["metrics"]["metrics"]
            if len(data["metric_statistics"])!=len(metrics): raise ValueError("metric statistics omitted")
            for definition,summary in zip(metrics,data["metric_statistics"]):
                if summary["metric_name"]!=definition["name"] or summary["unit"]!=definition["unit"] or summary["denominator"]!=len(indices) or summary["sample_indices"]!=indices:
                    raise ValueError("statistic unit/denominator/source mismatch")
            comparison=payload["nominal_comparisons"][index]
            if comparison is not None:
                c=section(comparison);n=c["nominal_result"]
                if c["source_analysis_hash"]!=wrapped["result_hash"] or c["nominal_hash"]!=source["nominal_hash"] or c["nominal_result_hash"]!=canonical_hash(n) or n["nominal_hash"]!=canonical_hash(n["nominal"]) or n["nominal_hash"]!=source["nominal_hash"] or _json_snapshot(n["evaluation"])!=_json_snapshot(study["evaluation"]) or n["runtime"]!=study["runtime"]:
                    raise ValueError("nominal comparison source mismatch")
        if payload["robust_pareto"] is not None:
            robust=section(payload["robust_pareto"])
            hashes=[a["result_hash"] for a in analyses]
            if [canonical_hash(s) for s in robust["sources"]]!=hashes or [p["source_analysis_hash"] for p in robust["points"]]!=hashes:
                raise ValueError("robust study order/source mismatch")
            if robust["definition_hash"]!=canonical_hash(robust["spec"]) or robust["analysis_hash"]!=canonical_hash({"schema_version":"dtco-robust-pareto-run-v1","spec":robust["spec"],"source_result_hashes":hashes}):
                raise ValueError("robust definition identity mismatch")
    except (KeyError,TypeError,IndexError,AttributeError) as exc:
        raise ValueError("incomplete robust report structure") from exc


def _csv(header,rows):
    stream=StringIO(newline="");writer=csv.writer(stream,lineterminator="\n")
    writer.writerow(header);writer.writerows(rows);return stream.getvalue()


@dataclass(frozen=True)
class RobustDTCOReport:
    payload_json: str

    def __post_init__(self):
        payload=json.loads(self.payload_json);_check(payload)
        object.__setattr__(self,"payload_json",_json_snapshot(payload))

    @property
    def report_hash(self): return canonical_hash(json.loads(self.payload_json))

    def to_dict(self): return {**json.loads(self.payload_json),"report_hash":self.report_hash}

    def to_json(self): return _json_snapshot(self.to_dict())

    @classmethod
    def from_json(cls,value):
        def unique(pairs):
            result={}
            for key,item in pairs:
                if key in result: raise ValueError("duplicate report key")
                result[key]=item
            return result
        data=json.loads(value,object_pairs_hook=unique)
        if type(data) is not dict: raise ValueError("report must be an object")
        expected=data.pop("report_hash",None)
        if expected!=canonical_hash(data): raise ValueError("report integrity mismatch")
        return cls(_json_snapshot(data))

    def samples_csv(self):
        rows=[]
        for study_index,wrapped in enumerate(json.loads(self.payload_json)["analyses"]):
            analysis=wrapped["data"]
            for source,point in zip(analysis["source"]["points"],analysis["points"]):
                rows.append((study_index,point["index"],source["point"]["manifest_hash"],point["point_hash"],source["status"],point["status"],
                    _json_snapshot(source["point"]["assignments"]),_json_snapshot(source["output"]),_json_snapshot(point["metrics"]),
                    _json_snapshot(point["constraints"]),_json_snapshot(source["failure"]),_json_snapshot(point["failure"])))
        return _csv(("study_index","sample_index","manifest_hash","point_hash","propagation_status","analysis_status","assignments_json","output_json","metrics_json","constraints_json","propagation_failure_json","analysis_failure_json"),rows)

    def statistics_csv(self):
        rows=[]
        for index,wrapped in enumerate(json.loads(self.payload_json)["analyses"]):
            for s in wrapped["data"]["metric_statistics"]:
                rows.append((index,s["metric_name"],s["unit"],s["denominator"],_json_snapshot(s["sample_indices"]),
                    *(_json_snapshot(s[k]) for k in ("minimum","maximum","mean","standard_deviation")),_json_snapshot(s["quantiles"])))
        return _csv(("study_index","metric_name","unit","denominator","sample_indices_json","minimum","maximum","mean","population_std","quantiles_json"),rows)

    def nominal_csv(self):
        rows=[]
        for index,wrapped in enumerate(json.loads(self.payload_json)["nominal_comparisons"]):
            if wrapped is None: continue
            c=wrapped["data"]
            if not c["metrics"]:
                rows.append((index,c["nominal_hash"],c["status"],"","","null","null",_json_snapshot(c["failure"])))
            for m in c["metrics"]:
                rows.append((index,c["nominal_hash"],c["status"],m["metric_name"],m["unit"],_json_snapshot(m["nominal_value"]),_json_snapshot(m["mean_minus_nominal"]),_json_snapshot(m["difference_undefined_reason"])))
        return _csv(("study_index","nominal_hash","status","metric_name","unit","nominal_value","mean_minus_nominal","failure_or_undefined_reason_json"),rows)

    def robust_csv(self):
        section=json.loads(self.payload_json)["robust_pareto"]
        rows=[] if section is None else [(p["index"],p["nominal_hash"],_json_snapshot(p["rank"]),_json_snapshot(p["objectives"]),_json_snapshot(p["exclusion_reasons"])) for p in section["data"]["points"]]
        return _csv(("study_index","nominal_hash","rank","objectives_json","exclusion_reasons_json"),rows)

    def to_markdown(self):
        payload=json.loads(self.payload_json)
        name=payload["name"].replace("\n"," ").replace("|","\\|")
        lines=[f"# {name}","",f"Report hash: {self.report_hash}","",f"NCMemSim: {payload['ncmemsim_version']}","",
            "| Study | Total | Assessed | Feasible | Infeasible | Failed | Feasible/all | Feasible/assessed | Failed/all |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for i,a in enumerate(payload["analyses"]):
            c=a["data"]["counts"];f=a["data"]["fractions"]
            lines.append(f"| {i} | {c['total']} | {c['assessed']} | {c['feasible']} | {c['infeasible']} | {c['failed']} | {f['observed_feasible_fraction_all_attempted']['value']} | {f['conditional_feasible_fraction_assessed']['value']} | {f['failure_fraction_all_attempted']['value']} |")
        lines += ["","Statistics include all assessed complete cases; failures are not physical infeasibility.",
            "Undefined values are JSON null. Exact manifests, definitions, runtime, responses and failure stages are in manifest.json and CSV artifacts.",
            "Robust eligibility/statistic/unit/direction policies are explicit in the manifest; no guaranteed yield or experimental calibration is implied."]
        if payload["robust_pareto"] is not None:
            lines += ["",f"Robust fronts: {payload['robust_pareto']['data']['fronts']}"]
        return "\n".join(lines)+"\n"


def build_robust_dtco_report(analyses,*,name,nominal_comparisons=None,robust_pareto=None,metadata=None):
    sources=tuple(analyses)
    if not sources or not all(isinstance(s,SampleAnalysisResult) for s in sources): raise TypeError("typed nonempty analyses required")
    comparisons=(None,)*len(sources) if nominal_comparisons is None else tuple(nominal_comparisons)
    if len(comparisons)!=len(sources): raise ValueError("nominal comparison count mismatch")
    for source,c in zip(sources,comparisons):
        if c is not None and (not isinstance(c,NominalComparison) or c.source.result_hash!=source.result_hash):
            raise ValueError("nominal comparison source mismatch")
    if robust_pareto is not None and (not isinstance(robust_pareto,RobustParetoResult) or tuple(s.result_hash for s in robust_pareto.sources)!=tuple(s.result_hash for s in sources)):
        raise ValueError("robust Pareto sources/order mismatch")
    return RobustDTCOReport(_json_snapshot({"schema_version":"dtco-robust-report-v1","name":name,
        "ncmemsim_version":__version__,"metadata":{} if metadata is None else metadata,
        "analyses":[_section(s) for s in sources],"nominal_comparisons":[_section(c) for c in comparisons],
        "robust_pareto":_section(robust_pareto)}))


def write_robust_dtco_report(report,output_dir):
    if not isinstance(report,RobustDTCOReport): raise TypeError("RobustDTCOReport required")
    contents=(("manifest.json",report.to_json()+"\n"),("samples.csv",report.samples_csv()),
        ("statistics.csv",report.statistics_csv()),("nominal.csv",report.nominal_csv()),
        ("robust.csv",report.robust_csv()),("report.md",report.to_markdown()))
    directory=Path(output_dir).resolve();targets=tuple(directory/name for name,_ in contents)
    if any(p.exists() for p in targets): raise FileExistsError("report target already exists")
    directory.mkdir(parents=True,exist_ok=True)
    for target,(_,text) in zip(targets,contents):
        with target.open("x",encoding="utf-8",newline="\n") as stream: stream.write(text)
    return targets


__all__=["RobustDTCOReport","build_robust_dtco_report","write_robust_dtco_report"]
