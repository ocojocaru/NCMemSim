# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Declared-order multilevel preparation and static electrical separation analysis."""
from __future__ import annotations
from dataclasses import dataclass as _dataclass
import math as _math

from .multilevel_contracts import (
    ElectricalSequenceExperiment as _Experiment, PulseSequenceEvidence as _Evidence,
    _Archive, _canonical, _keys, _load, _match, _number, _text,
)
from .multilevel_execution import ElectricalSequenceResult as _SequenceResult, run_electrical_sequence as _run_sequence

__all__ = ["MultilevelPreparation", "MultilevelStudyPlan", "MultilevelStudyResult",
           "analyze_multilevel_results", "run_multilevel_study"]


@_dataclass(frozen=True)
class MultilevelPreparation(_Archive):
    """One named independent preparation, selected at its final completed read."""
    level_id: str
    experiment: _Experiment
    readout_half_width_V: float

    def __post_init__(self):
        _text(self.level_id, "level identity")
        if type(self.experiment) is not _Experiment:
            raise ValueError("owned electrical preparation required")
        object.__setattr__(self, "experiment", _Experiment.from_dict(self.experiment.to_dict()))
        object.__setattr__(self, "readout_half_width_V", _number(self.readout_half_width_V, "readout half width", nonnegative=True))

    def to_dict(self):
        return {"schema_version": "multilevel-preparation-v1", "level_id": self.level_id,
                "experiment": self.experiment.to_dict(), "readout_half_width_V": self.readout_half_width_V,
                "selection": "final_read_of_completed_sequence", "readout_unit": "V"}

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ("schema_version", "level_id", "experiment", "readout_half_width_V", "selection", "readout_unit"))
        obj = cls(raw["level_id"], _Experiment.from_dict(raw["experiment"]), raw["readout_half_width_V"])
        _match(raw, obj.to_dict())
        return obj


@_dataclass(frozen=True)
class MultilevelStudyPlan(_Archive):
    """Fixed increasing readout order, common preparation baseline and margin criterion."""
    name: str
    levels: tuple[MultilevelPreparation, ...]
    minimum_margin_V: float
    interval_kind: str
    evidence: _Evidence

    def __post_init__(self):
        _text(self.name, "study name")
        if type(self.levels) is not tuple or len(self.levels) < 2 or any(type(x) is not MultilevelPreparation for x in self.levels):
            raise ValueError("at least two immutable typed level preparations required")
        if len({x.level_id for x in self.levels}) != len(self.levels):
            raise ValueError("duplicate target level identity")
        object.__setattr__(self, "minimum_margin_V", _number(self.minimum_margin_V, "minimum margin", nonnegative=True))
        if type(self.interval_kind) is not str or self.interval_kind not in ("deterministic", "assumed_bounds"):
            raise ValueError("declare deterministic or assumed-bound intervals")
        if self.interval_kind == "deterministic" and any(x.readout_half_width_V != 0 for x in self.levels):
            raise ValueError("deterministic separation requires zero interval widths")
        if type(self.evidence) is not _Evidence:
            raise ValueError("typed margin/interval evidence required")
        first = self.levels[0].experiment
        for level in self.levels:
            exp = level.experiment
            if exp.context.context_hash != first.context.context_hash or exp.sequence.readout.contract_hash != first.sequence.readout.contract_hash:
                raise ValueError("all levels require the exact same physical context and read policy")
            if exp.initial_state_json != first.initial_state_json:
                raise ValueError("independent preparations require the same declared initial state")
            a = None if exp.weight_reference is None else exp.weight_reference.contract_hash
            b = None if first.weight_reference is None else first.weight_reference.contract_hash
            if a != b:
                raise ValueError("level preparations cannot silently change weight references")

    def to_dict(self):
        return {"schema_version": "multilevel-study-plan-v1", "name": self.name,
                "levels": [x.to_dict() for x in self.levels], "minimum_margin_V": self.minimum_margin_V,
                "interval_kind": self.interval_kind, "evidence": self.evidence.to_dict(),
                "order": "declared_increasing_delta_vfb_V", "preparation": "independent_copies_of_common_initial_state",
                "criterion": "signed_margin_positive_and_at_least_minimum",
                "margin_unit": "V", "experimental_qualification": False}

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ("schema_version", "name", "levels", "minimum_margin_V", "interval_kind", "evidence",
                    "order", "preparation", "criterion", "margin_unit", "experimental_qualification"))
        if type(raw["levels"]) is not list:
            raise ValueError("archived level list required")
        obj = cls(raw["name"], tuple(MultilevelPreparation.from_dict(x) for x in raw["levels"]),
                  raw["minimum_margin_V"], raw["interval_kind"], _Evidence.from_dict(raw["evidence"]))
        _match(raw, obj.to_dict())
        return obj


def _projection(raw):
    _keys(raw, ("schema_version", "plan", "plan_hash", "results", "summary"))
    if raw["schema_version"] != "multilevel-study-result-v1":
        raise ValueError("unsupported multilevel result schema")
    plan = MultilevelStudyPlan.from_dict(raw["plan"])
    if raw["plan_hash"] != plan.contract_hash:
        raise ValueError("multilevel plan hash mismatch")
    if type(raw["results"]) is not list or len(raw["results"]) != len(plan.levels):
        raise ValueError("every declared level requires a result slot, including missing outcomes")
    rows = []
    for level, record in zip(plan.levels, raw["results"], strict=True):
        value = None
        if record is None:
            status, failure = "missing", None
        else:
            result = _SequenceResult.from_dict(record)
            source = result.to_dict()
            if source["experiment_hash"] != level.experiment.contract_hash:
                raise ValueError("level result belongs to a different preparation")
            status = result.summary["status"]
            failure = source["failure"]
            if status == "completed":
                value = source["steps"][-1]["read"]["delta_vfb_V"]
        rows.append({"level_id": level.level_id, "status": status, "readout_V": value,
                     "readout_half_width_V": level.readout_half_width_V, "failure": failure})
    pairs = []
    for a, b in zip(rows, rows[1:]):
        margin, reason = None, None
        if a["readout_V"] is None or b["readout_V"] is None:
            status, reason = "not_assessable", "missing_or_failed_preparation"
        else:
            computed = (b["readout_V"] - b["readout_half_width_V"]) - (a["readout_V"] + a["readout_half_width_V"])
            if not _math.isfinite(computed):
                status, reason = "not_assessable", "nonrepresentable_margin"
            else:
                margin = computed
                status = "passed" if margin > 0 and margin >= plan.minimum_margin_V else "failed"
        pairs.append({"lower_level_id": a["level_id"], "upper_level_id": b["level_id"],
                      "signed_margin_V": margin, "status": status, "reason": reason})
    passed = sum(x["status"] == "passed" for x in pairs)
    failed = sum(x["status"] == "failed" for x in pairs)
    unassessed = sum(x["status"] == "not_assessable" for x in pairs)
    # A known failed pair remains a failure even when another pair is unavailable.
    status = "failed" if failed else ("not_assessable" if unassessed else "passed")
    return {"status": status, "complete": all(x["status"] == "completed" for x in rows),
            "requested_level_count": len(rows), "completed_level_count": sum(x["status"] == "completed" for x in rows),
            "failed_level_count": sum(x["status"] == "failed" for x in rows),
            "missing_level_count": sum(x["status"] == "missing" for x in rows),
            "requested_pair_count": len(pairs), "passed_pair_count": passed,
            "failed_pair_count": failed, "not_assessable_pair_count": unassessed,
            "pair_assessment_fraction": (passed + failed) / len(pairs),
            "minimum_signed_margin_V": min((x["signed_margin_V"] for x in pairs if x["signed_margin_V"] is not None), default=None),
            "minimum_margin_scope": "assessable_pairs_only", "levels": rows, "adjacent_pairs": pairs,
            "experimental_qualification": False, "capacity_claim": "none", "weights_evaluated": False}


@_dataclass(frozen=True)
class MultilevelStudyResult(_Archive):
    """Original per-level Q2 evidence and strict static multilevel projections."""
    record_json: str

    def __post_init__(self):
        raw = _load(self.record_json)
        summary = _projection(raw)
        _match(raw["summary"], summary)
        object.__setattr__(self, "record_json", _canonical(raw))

    def to_dict(self):
        return _load(self.record_json)

    @property
    def summary(self):
        return self.to_dict()["summary"]

    @classmethod
    def from_dict(cls, raw):
        return cls(_canonical(raw))


def analyze_multilevel_results(plan, results):
    """Analyze exact plan-bound results in declared order; None retains missing evidence."""
    if type(plan) is not MultilevelStudyPlan:
        raise ValueError("typed multilevel plan required")
    if type(results) is not tuple or len(results) != len(plan.levels) or any(x is not None and type(x) is not _SequenceResult for x in results):
        raise ValueError("one typed result or explicit None per declared level required")
    raw = {"schema_version": "multilevel-study-result-v1", "plan": plan.to_dict(), "plan_hash": plan.contract_hash,
           "results": [None if x is None else x.to_dict() for x in results], "summary": None}
    raw["summary"] = _projection(raw)
    return MultilevelStudyResult.from_dict(raw)


def run_multilevel_study(plan):
    """Prepare all declared levels independently, retaining failed Q2 outcomes."""
    if type(plan) is not MultilevelStudyPlan:
        raise ValueError("typed multilevel plan required")
    plan = MultilevelStudyPlan.from_dict(plan.to_dict())
    results = tuple(_run_sequence(level.experiment) for level in plan.levels)
    return analyze_multilevel_results(plan, results)
