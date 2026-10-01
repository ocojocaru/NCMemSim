# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Explicit MODEL population linkage, eligibility and exact Pareto projection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..dtco.metrics import ConstraintOperator, ObjectiveDirection
from ..dtco.sweep import SweepPoint
from ..hashing import canonical_hash
from .dtco import EnsembleScalarDefinition, EnsembleScalarKind, EnsembleConstraint, EnsembleObjective
from .model_analysis import ModelPopulationAnalysis
from .model_sampling import _snapshot, _strict_json


@dataclass(frozen=True)
class ModelDTCOStudy:
    """One design linked to its explicitly annotated MODEL execution."""
    design_point: SweepPoint
    source: ModelPopulationAnalysis

    def __post_init__(self) -> None:
        if not isinstance(self.design_point, SweepPoint) or not isinstance(self.source, ModelPopulationAnalysis):
            raise TypeError("MODEL DTCO requires SweepPoint and ModelPopulationAnalysis")
        workflow = _strict_json(self.source.source.execution_json)["workflow_context"]
        if _snapshot(workflow.get("dtco_design_point")) != _snapshot(self.design_point.to_dict()):
            raise ValueError("design point differs from declared execution linkage")

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": "model-dtco-study-v1", "design_point": self.design_point.to_dict(),
                "point_hash": self.design_point.point_hash, "source_analysis_hash": self.source.analysis_hash,
                "source": self.source.to_dict()}

    @property
    def study_hash(self) -> str:
        return canonical_hash(self.to_dict())


def evaluate_model_scalar(study: ModelDTCOStudy, definition: EnsembleScalarDefinition) -> dict[str, Any]:
    """Project an existing K scalar contract with source denominator evidence."""
    if not isinstance(study, ModelDTCOStudy) or not isinstance(definition, EnsembleScalarDefinition):
        raise TypeError("invalid MODEL study/scalar definition")
    data = study.source.to_dict()
    kind = definition.kind.value
    if definition.metric_name is None:
        summary = data["fractions"][kind]
        value, denominator = summary["value"], summary["denominator"]
    else:
        matches = [s for s in data["statistics"] if s["metric_name"] == definition.metric_name]
        if len(matches) != 1 or matches[0]["unit"] != definition.unit:
            raise ValueError("scalar metric absent or unit mismatch")
        summary = matches[0]
        denominator = summary["denominator"]
        if definition.kind is EnsembleScalarKind.QUANTILE:
            matches = [q for q in summary["quantiles"] if q["probability"] == definition.quantile]
            if len(matches) != 1:
                raise ValueError("quantile was not declared in source statistics")
            value = matches[0]["value"]
        else:
            value = summary[kind]
    return {"definition": definition.to_dict(), "status": "undefined" if value is None else "defined",
            "value": value, "denominator": denominator, "source_analysis_hash": study.source.analysis_hash}


@dataclass(frozen=True)
class ModelEligibilityResult:
    study: ModelDTCOStudy
    constraints: tuple[EnsembleConstraint, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.study, ModelDTCOStudy):
            raise TypeError("study must be ModelDTCOStudy")
        object.__setattr__(self, "constraints", tuple(self.constraints))
        if any(not isinstance(c, EnsembleConstraint) for c in self.constraints):
            raise TypeError("constraints must contain EnsembleConstraint")
        if len({c.name for c in self.constraints}) != len(self.constraints):
            raise ValueError("duplicate constraint names")
        self.to_dict()

    def to_dict(self) -> dict[str, Any]:
        evaluations = []
        for constraint in self.constraints:
            scalar = evaluate_model_scalar(self.study, constraint.scalar)
            value = scalar["value"]
            satisfied = None if value is None else (
                value <= constraint.threshold if constraint.operator is ConstraintOperator.LE else value >= constraint.threshold)
            evaluations.append({"constraint": constraint.to_dict(), "scalar": scalar,
                "status": "unevaluable" if satisfied is None else "satisfied" if satisfied else "violated"})
        status = ("unevaluable" if any(e["status"] == "unevaluable" for e in evaluations) else
                  "ineligible" if any(e["status"] == "violated" for e in evaluations) else "eligible")
        return {"schema_version": "model-dtco-eligibility-v1", "study_hash": self.study.study_hash,
                "status": status, "evaluations": evaluations}

    @property
    def status(self) -> str:
        return self.to_dict()["status"]


def evaluate_model_eligibility(study: ModelDTCOStudy, constraints=()) -> ModelEligibilityResult:
    """Evaluate explicit inclusive bounds; undefined takes precedence."""
    return ModelEligibilityResult(study, tuple(constraints))


@dataclass(frozen=True)
class ModelParetoAnalysis:
    sources: tuple[ModelEligibilityResult, ...]
    objectives: tuple[EnsembleObjective, ...]
    name: str = "model-pareto"

    def __post_init__(self) -> None:
        object.__setattr__(self, "sources", tuple(self.sources))
        object.__setattr__(self, "objectives", tuple(self.objectives))
        if not isinstance(self.name, str) or not self.name or self.name != self.name.strip():
            raise ValueError("invalid Pareto name")
        if any(not isinstance(s, ModelEligibilityResult) for s in self.sources):
            raise TypeError("sources must contain ModelEligibilityResult")
        if not self.objectives or any(not isinstance(o, EnsembleObjective) for o in self.objectives):
            raise ValueError("nonempty EnsembleObjective sequence required")
        if len({o.name for o in self.objectives}) != len(self.objectives):
            raise ValueError("duplicate objective names")
        if len({s.study.design_point.point_hash for s in self.sources}) != len(self.sources):
            raise ValueError("duplicate design points")
        if len({(s.study.design_point.experiment_hash, s.study.design_point.index) for s in self.sources}) != len(self.sources):
            raise ValueError("duplicate experiment/index identities")
        if len({s.study.design_point.experiment_hash for s in self.sources}) > 1:
            raise ValueError("mixed design experiment identities")
        # Prevent unlike populations/assessment definitions being silently ranked.
        signatures = {(s.study.source.metric_spec.definition_hash, s.study.source.statistics_spec.definition_hash,
                       _strict_json(s.study.source.source.execution_json)["evaluation_id"],
                       _snapshot([c.to_dict() for c in s.constraints])) for s in self.sources}
        if len(signatures) > 1:
            raise ValueError("incompatible metric/statistics/workflow/eligibility definitions")
        self._derived()

    def _derived(self) -> dict[str, Any]:
        points, values = [], {}
        for index, source in enumerate(self.sources):
            projections = [evaluate_model_scalar(source.study, o.scalar) for o in self.objectives]
            reason = source.status if source.status != "eligible" else (
                "undefined-objective" if any(p["value"] is None for p in projections) else None)
            points.append({"source_index": index, "point_hash": source.study.design_point.point_hash,
                "study_hash": source.study.study_hash, "eligibility": source.to_dict(),
                "objective_values": [{"name": o.name, **p} for o, p in zip(self.objectives, projections, strict=True)],
                "exclusion_reason": reason, "rank": None})
            if reason is None:
                values[index] = tuple(p["value"] for p in projections)
        def dominates(left, right):
            comparisons = [(a < b, a <= b) if o.direction is ObjectiveDirection.MINIMIZE else (a > b, a >= b)
                           for a, b, o in zip(values[left], values[right], self.objectives, strict=True)]
            return all(c[1] for c in comparisons) and any(c[0] for c in comparisons)
        remaining = list(values)
        fronts = []
        while remaining:
            front = [i for i in remaining if not any(dominates(j, i) for j in remaining if j != i)]
            for i in front:
                points[i]["rank"] = len(fronts)
            fronts.append(front)
            remaining = [i for i in remaining if i not in front]
        return {"points": points, "fronts": fronts, "attempted_design_count": len(points),
                "ranked_design_count": len(values), "excluded_design_count": len(points)-len(values)}

    def to_dict(self) -> dict[str, Any]:
        payload = {"schema_version": "model-dtco-pareto-v1", "name": self.name,
                   "sources": [s.study.to_dict() for s in self.sources],
                   "objectives": [o.to_dict() for o in self.objectives], **self._derived()}
        return {**payload, "analysis_hash": canonical_hash(payload)}


def analyze_model_pareto(sources, objectives, *, name="model-pareto") -> ModelParetoAnalysis:
    """Rank eligible, defined designs with exact dominance and stable tie order."""
    return ModelParetoAnalysis(tuple(sources), tuple(objectives), name)


__all__ = ["ModelDTCOStudy", "ModelEligibilityResult", "ModelParetoAnalysis", "evaluate_model_scalar",
           "evaluate_model_eligibility", "analyze_model_pareto"]
