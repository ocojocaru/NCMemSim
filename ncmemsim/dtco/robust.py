"""Explicit robust objectives, linked nominal comparisons and exact Pareto fronts."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
import json
import math
import platform
import numpy as np
from .._version import __version__
from typing import Any, Callable
from ..device import Device
from ..hashing import canonical_hash
from .metrics import ObjectiveDirection, ConstraintEvaluation, _label
from .operating import OperatingProtocol
from .spec import _device_definition_payload, _operating_definition_payload
from .sample_analysis import SampleAnalysisResult, _finite_float
from .sweep import _json_snapshot


@dataclass(frozen=True)
class NominalResult:
    nominal_json: str
    evaluation_json: str
    status: str
    output_json: str | None = None
    failure_stage: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    runtime_json: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "runtime_json", _json_snapshot({"python": platform.python_version(),
            "python_implementation": platform.python_implementation(), "numpy": np.__version__, "ncmemsim": __version__}))
        for field in ("nominal_json", "evaluation_json"):
            value = json.loads(getattr(self, field))
            if type(value) is not dict:
                raise TypeError("nominal/evaluation definitions require JSON objects")
            object.__setattr__(self, field, _json_snapshot(value))
        nominal = json.loads(self.nominal_json)
        if set(nominal) != {"device", "operating"} or type(nominal["device"]) is not dict:
            raise ValueError("invalid nominal definition")
        evaluation = json.loads(self.evaluation_json)
        _label(evaluation.get("id"), "evaluation id")
        if set(evaluation) != {"id", "parameters"} or type(evaluation["parameters"]) is not dict:
            raise ValueError("invalid evaluation definition")
        if self.status == "success":
            if any(v is not None for v in (self.failure_stage, self.error_type, self.error_message)):
                raise ValueError("successful nominal cannot expose failure details")
            output = json.loads(self.output_json) if self.output_json is not None else None
            if type(output) is not dict:
                raise TypeError("successful nominal output must be a JSON object")
            object.__setattr__(self, "output_json", _json_snapshot(output))
        elif self.status == "failed":
            if self.output_json is not None or self.failure_stage not in ("evaluation", "serialization"):
                raise ValueError("invalid nominal failure")
            _label(self.error_type, "error type")
            if not isinstance(self.error_message, str):
                raise TypeError("failure requires an error message")
        else:
            raise ValueError("nominal status must be success/failed")

    @property
    def nominal_hash(self) -> str:
        return canonical_hash(json.loads(self.nominal_json))

    @property
    def output(self) -> dict[str, Any] | None:
        return None if self.output_json is None else json.loads(self.output_json)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": "dtco-nominal-result-v1", "nominal": json.loads(self.nominal_json),
                "nominal_hash": self.nominal_hash, "evaluation": json.loads(self.evaluation_json),
                "runtime": json.loads(self.runtime_json), "status": self.status, "output": self.output,
                "failure": None if self.status == "success" else {"stage": self.failure_stage,
                    "type": self.error_type, "message": self.error_message}}

    @property
    def result_hash(self) -> str:
        return canonical_hash(self.to_dict())


def evaluate_nominal(base_device: Device, evaluator: Callable, *, evaluation_id: str,
                     evaluation_parameters: dict[str, Any] | None = None,
                     base_protocol: OperatingProtocol | None = None) -> NominalResult:
    """Evaluate one isolated baseline; callback receives (device, protocol).

    Declare the same evaluator id/parameters as propagation for comparison.
    The caller must use the same scientific response model and fresh state.
    """
    if not isinstance(base_device, Device) or not callable(evaluator):
        raise TypeError("nominal evaluation requires a device and callable")
    _label(evaluation_id, "evaluation id")
    parameters = {} if evaluation_parameters is None else evaluation_parameters
    if type(parameters) is not dict:
        raise TypeError("evaluation parameters must be a JSON object")
    evaluation = _json_snapshot({"id": evaluation_id, "parameters": parameters})
    device, protocol = deepcopy(base_device), deepcopy(base_protocol)
    device.validate()
    nominal = _json_snapshot({"device": _device_definition_payload(device),
        "operating": None if protocol is None else _operating_definition_payload(protocol)})
    stage = "evaluation"
    try:
        output = evaluator(device, protocol)
        stage = "serialization"
        if type(output) is not dict:
            raise TypeError("nominal evaluator must return a finite JSON object")
        return NominalResult(nominal, evaluation, "success", output_json=_json_snapshot(output))
    except Exception as exc:
        return NominalResult(nominal, evaluation, "failed", failure_stage=stage,
            error_type=f"{type(exc).__module__}.{type(exc).__qualname__}", error_message=str(exc))


@dataclass(frozen=True)
class NominalComparison:
    source: SampleAnalysisResult
    nominal: NominalResult

    def __post_init__(self) -> None:
        if not isinstance(self.source, SampleAnalysisResult) or not isinstance(self.nominal, NominalResult):
            raise TypeError("comparison requires sample analysis and nominal result")
        study = json.loads(self.source.source.study_json)
        if self.nominal.nominal_hash != self.source.source.nominal_hash:
            raise ValueError("nominal baseline differs from sampled study")
        if self.nominal.evaluation_json != _json_snapshot(study["evaluation"]):
            raise ValueError("nominal evaluator identity/settings differ from sampled study")
        if self.nominal.runtime_json != _json_snapshot(study["runtime"]):
            raise ValueError("nominal runtime differs from sampled study")

    def to_dict(self) -> dict[str, Any]:
        failure = None
        metrics = []
        status = "assessed"
        nominal_feasible = None
        if self.nominal.status == "failed":
            status = "failed"
            failure = self.nominal.to_dict()["failure"]
        else:
            try:
                values = {m.name: _finite_float(m.extract(self.nominal.output)) for m in self.source.spec.metrics.metrics}
            except (ValueError, TypeError, OverflowError) as exc:
                status = "failed"
                failure = {"stage": "extraction", "type": f"{type(exc).__module__}.{type(exc).__qualname__}", "message": str(exc)}
            else:
                nominal_feasible = all(ConstraintEvaluation(c, values[c.metric_name]).satisfied for c in self.source.spec.metrics.constraints)
                for summary in self.source.metric_statistics:
                    nominal_value = values[summary["metric_name"]]
                    mean = summary["mean"]
                    delta = None if mean is None else mean - nominal_value
                    reason = "no_assessed_samples" if mean is None else None
                    if delta is not None and not math.isfinite(delta):
                        delta, reason = None, "arithmetic_overflow"
                    metrics.append({"metric_name": summary["metric_name"], "unit": summary["unit"],
                        "nominal_value": nominal_value, "sample_statistics": summary,
                        "mean_minus_nominal": delta, "difference_undefined_reason": reason})
        return {"schema_version": "dtco-nominal-comparison-v1", "source_analysis_hash": self.source.result_hash,
                "nominal_hash": self.nominal.nominal_hash, "nominal_result_hash": self.nominal.result_hash,
                "nominal_result": self.nominal.to_dict(), "status": status,
                "nominal_feasible": nominal_feasible, "metrics": metrics, "failure": failure}

    def to_json(self) -> str:
        return _json_snapshot(self.to_dict())

    @property
    def result_hash(self) -> str:
        return canonical_hash(self.to_dict())


def compare_nominal(source: SampleAnalysisResult, nominal: NominalResult) -> NominalComparison:
    return NominalComparison(source, nominal)


class RobustStatistic(str, Enum):
    MEAN = "mean"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    STANDARD_DEVIATION = "standard_deviation"
    QUANTILE = "quantile"


class RobustFailurePolicy(str, Enum):
    REQUIRE_NO_FAILURES = "require_no_failures"
    ALLOW_ASSESSED_WITH_FAILURES = "allow_assessed_with_failures"


@dataclass(frozen=True)
class RobustObjective:
    name: str
    metric_name: str
    unit: str
    direction: ObjectiveDirection
    statistic: RobustStatistic
    quantile: float | None = None

    def __post_init__(self) -> None:
        for label, value in (("objective name",self.name),("metric name",self.metric_name),("unit",self.unit)):
            _label(value,label)
        if not isinstance(self.direction,ObjectiveDirection) or not isinstance(self.statistic,RobustStatistic):
            raise TypeError("objective requires typed direction/statistic")
        if self.statistic is RobustStatistic.QUANTILE:
            if type(self.quantile) not in (int,float) or not 0 <= self.quantile <= 1 or not math.isfinite(self.quantile):
                raise ValueError("quantile objective requires a finite probability in [0,1]")
            object.__setattr__(self,"quantile",float(self.quantile))
        elif self.quantile is not None:
            raise ValueError("quantile probability is only valid for QUANTILE")

    def to_dict(self) -> dict[str,Any]:
        return {"name":self.name,"metric_name":self.metric_name,"unit":self.unit,
                "direction":self.direction.value,"statistic":self.statistic.value,"quantile":self.quantile}


@dataclass(frozen=True)
class RobustParetoSpec:
    name: str
    objectives: tuple[RobustObjective,...]
    failure_policy: RobustFailurePolicy
    minimum_assessed_count: int
    minimum_observed_feasible_fraction: float

    def __post_init__(self) -> None:
        _label(self.name,"robust analysis name")
        items=tuple(self.objectives)
        if not items or not all(isinstance(o,RobustObjective) for o in items):
            raise ValueError("robust objectives must be typed and nonempty")
        if len({o.name for o in items}) != len(items):
            raise ValueError("duplicate objective names")
        object.__setattr__(self,"objectives",items)
        if not isinstance(self.failure_policy,RobustFailurePolicy):
            raise TypeError("explicit RobustFailurePolicy required")
        if type(self.minimum_assessed_count) is not int or self.minimum_assessed_count < 1:
            raise ValueError("minimum assessed count must be a positive integer")
        fraction=self.minimum_observed_feasible_fraction
        if type(fraction) not in (int,float) or not 0 <= fraction <= 1 or not math.isfinite(fraction):
            raise ValueError("minimum observed feasible fraction must lie in [0,1]")
        object.__setattr__(self,"minimum_observed_feasible_fraction",float(fraction))

    def to_dict(self) -> dict[str,Any]:
        return {"schema_version":"dtco-robust-pareto-v1","name":self.name,
                "objectives":[o.to_dict() for o in self.objectives],"failure_policy":self.failure_policy.value,
                "minimum_assessed_count":self.minimum_assessed_count,
                "minimum_observed_feasible_fraction":self.minimum_observed_feasible_fraction,
                "dominance":"exact-no-worse-all-strictly-better-one","ties":"retain-all",
                "ordering":"declared-study-order","rank_base":0}

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


def _prepare(sources: tuple[SampleAnalysisResult,...],spec: RobustParetoSpec):
    if not sources or not all(isinstance(s,SampleAnalysisResult) for s in sources):
        raise ValueError("robust Pareto requires nonempty sample analyses")
    if any(s.spec.definition_hash != sources[0].spec.definition_hash for s in sources[1:]):
        raise ValueError("studies must share metric/constraint/statistic definitions")
    baseline=json.loads(sources[0].source.study_json)
    for source in sources[1:]:
        study=json.loads(source.source.study_json)
        if _json_snapshot(study["evaluation"]) != _json_snapshot(baseline["evaluation"]) or study["runtime"] != baseline["runtime"] or source.runtime_json != sources[0].runtime_json:
            raise ValueError("studies must share evaluator/settings and recorded runtimes")
    definitions={m.name:m for m in sources[0].spec.metrics.metrics}
    for objective in spec.objectives:
        if objective.metric_name not in definitions or objective.unit != definitions[objective.metric_name].unit:
            raise ValueError("objective metric/unit differs from source definitions")
        if objective.statistic is RobustStatistic.QUANTILE and objective.quantile not in sources[0].spec.quantiles:
            raise ValueError("requested objective quantile was not computed")
    records=[]
    for source in sources:
        reasons=[]
        if source.assessed_count < spec.minimum_assessed_count: reasons.append("insufficient_assessed_samples")
        if spec.failure_policy is RobustFailurePolicy.REQUIRE_NO_FAILURES and source.failure_count: reasons.append("failures_disallowed")
        if source.observed_feasible_fraction_all_attempted < spec.minimum_observed_feasible_fraction: reasons.append("feasible_fraction_below_minimum")
        summaries={s["metric_name"]:s for s in source.metric_statistics}
        values=[]
        for objective in spec.objectives:
            summary=summaries[objective.metric_name]
            value=next(q["value"] for q in summary["quantiles"] if q["probability"]==objective.quantile) if objective.statistic is RobustStatistic.QUANTILE else summary[objective.statistic.value]
            if value is None and "undefined_objective" not in reasons: reasons.append("undefined_objective")
            values.append((objective.name,value))
        records.append((tuple(reasons),() if reasons else tuple(values)))
    return tuple(records)


def _fronts(records,spec):
    remaining=[i for i,(reasons,_) in enumerate(records) if not reasons]
    def dominates(a,b):
        better=False
        for objective,(_,left),(_,right) in zip(spec.objectives,records[a][1],records[b][1]):
            if objective.direction is ObjectiveDirection.MINIMIZE:
                if left > right: return False
                better=better or left < right
            else:
                if left < right: return False
                better=better or left > right
        return better
    successors={i:[] for i in remaining}
    incoming={i:0 for i in remaining}
    for position,left in enumerate(remaining):
        for right in remaining[position+1:]:
            if dominates(left,right):
                successors[left].append(right);incoming[right]+=1
            elif dominates(right,left):
                successors[right].append(left);incoming[left]+=1
    current=[i for i in remaining if incoming[i]==0]
    fronts=[]
    while current:
        front=tuple(sorted(current))
        fronts.append(front)
        following=[]
        for index in front:
            for target in successors[index]:
                incoming[target]-=1
                if incoming[target]==0: following.append(target)
        current=following
    return tuple(fronts)


@dataclass(frozen=True)
class RobustParetoResult:
    spec: RobustParetoSpec
    sources: tuple[SampleAnalysisResult,...]

    def __post_init__(self) -> None:
        if not isinstance(self.spec,RobustParetoSpec): raise TypeError("spec must be RobustParetoSpec")
        object.__setattr__(self,"sources",tuple(self.sources))
        _prepare(self.sources,self.spec)

    @property
    def fronts(self) -> tuple[tuple[int,...],...]:
        return _fronts(_prepare(self.sources,self.spec),self.spec)

    @property
    def pareto_indices(self) -> tuple[int,...]:
        return self.fronts[0] if self.fronts else ()

    @property
    def analysis_hash(self) -> str:
        return canonical_hash({"schema_version":"dtco-robust-pareto-run-v1",
            "spec":self.spec.to_dict(),"source_result_hashes":[s.result_hash for s in self.sources]})

    def to_dict(self) -> dict[str,Any]:
        records=_prepare(self.sources,self.spec)
        fronts=_fronts(records,self.spec)
        ranks={index:rank for rank,front in enumerate(fronts) for index in front}
        return {"schema_version":"dtco-robust-pareto-result-v1","spec":self.spec.to_dict(),
            "definition_hash":self.spec.definition_hash,"analysis_hash":self.analysis_hash,
            "sources":[s.to_dict() for s in self.sources],"fronts":[list(f) for f in fronts],
            "points":[{"index":i,"source_analysis_hash":s.result_hash,"nominal_hash":s.source.nominal_hash,
                "rank":ranks.get(i),"objectives":dict(records[i][1]),"exclusion_reasons":list(records[i][0])}
                for i,s in enumerate(self.sources)]}

    def to_json(self) -> str:
        return _json_snapshot(self.to_dict())

    @property
    def result_hash(self) -> str:
        return canonical_hash(self.to_dict())


def analyze_robust_pareto(sources, spec: RobustParetoSpec) -> RobustParetoResult:
    return RobustParetoResult(spec,tuple(sources))


__all__=["NominalResult","NominalComparison","evaluate_nominal","compare_nominal",
    "RobustStatistic","RobustFailurePolicy","RobustObjective","RobustParetoSpec",
    "RobustParetoResult","analyze_robust_pareto"]
