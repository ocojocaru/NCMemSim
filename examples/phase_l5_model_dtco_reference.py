# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Controlled MODEL variability DTCO reference; no calibrated process-yield claim."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

# Support direct execution from the repository as well as namespace imports.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.phase_l3_tat_density_variability import (
    build_reference, workflow_settings, evaluate_reference, _evaluate_context, OCCUPATION_ATOL,
)
from ncmemsim.dtco import (DesignVariable, DesignVariableRole, ParameterBinding, BindingScope,
    ExperimentSpec, iter_cartesian_points, apply_experiment_design_point, MetricAnalysisSpec,
    MetricDefinition, MetricConstraint, ConstraintOperator, ObjectiveDirection)
from ncmemsim.ensemble import (EnsembleScalarDefinition, EnsembleScalarKind, EnsembleConstraint,
    EnsembleObjective, NominalMetricReference)
from ncmemsim.ensemble.model_contracts import ModelVariabilitySpec
from ncmemsim.ensemble.model_sampling import generate_model_sample_manifest
from ncmemsim.ensemble.model_execution import execute_model_sample_manifest
from ncmemsim.ensemble.model_analysis import analyze_model_execution
from ncmemsim.ensemble.model_dtco import ModelDTCOStudy, evaluate_model_eligibility, analyze_model_pareto
from ncmemsim.hashing import canonical_hash


def run_reference():
    """Apply real geometry designs, use paired density draws and audit timestep."""
    device, base_sampling = build_reference()
    experiment = ExperimentSpec.from_device(name="l5-inter-FG-thickness", device=device, variables=(
        DesignVariable("inter_fg_nm", ParameterBinding(BindingScope.DEVICE, ("layers", "inter_fg1_sio2", "thickness_nm")),
                       (1.0, 1.1, 1.2), DesignVariableRole.GEOMETRY, "nm"),))
    metrics = MetricAnalysisSpec("L5 controlled transport", (
        MetricDefinition("tat_rate", ("initial_tat_rate_Hz",), "Hz"),
        MetricDefinition("conservation", ("max_relative_conservation_error",), "1"),
        MetricDefinition("clamped", ("clamped_steps",), "1")), (
        MetricConstraint("conservation", "conservation", ConstraintOperator.LE, 1e-12, "1"),
        MetricConstraint("no_clamp", "clamped", ConstraintOperator.LE, 0, "1")))
    coverage = EnsembleScalarDefinition("coverage", EnsembleScalarKind.COVERAGE_FRACTION, "1")
    passed = EnsembleScalarDefinition("pass", EnsembleScalarKind.SIMULATED_PASS_FRACTION, "1")
    constraints = (EnsembleConstraint("full_coverage", coverage, ConstraintOperator.GE, 1, "1"),
                   EnsembleConstraint("all_numerical_checks", passed, ConstraintOperator.GE, 1, "1"))
    objectives = (
        EnsembleObjective("maximize_mean_TAT", EnsembleScalarDefinition("mean_TAT", EnsembleScalarKind.MEAN,
                          "Hz", "tat_rate"), ObjectiveDirection.MAXIMIZE),
        EnsembleObjective("minimize_TAT_spread", EnsembleScalarDefinition("sd_TAT", EnsembleScalarKind.STANDARD_DEVIATION,
                          "Hz", "tat_rate"), ObjectiveDirection.MINIMIZE))
    sources, audit, paired_values = [], [], None
    for point in iter_cartesian_points(experiment):
        candidate = apply_experiment_design_point(experiment, device, point.assignments)
        study = ModelVariabilitySpec.from_device(name=base_sampling.study.name, device=candidate,
            model_context=base_sampling.study.model_context, variables=base_sampling.study.variables)
        manifest = generate_model_sample_manifest(replace(base_sampling, study=study))
        values = [s.values for s in manifest.samples]
        if paired_values is None:
            paired_values = values
        elif values != paired_values:
            raise AssertionError("density draws must be paired across designs")
        settings = workflow_settings()
        settings["dtco_design_point"] = point.to_dict()
        execution = execute_model_sample_manifest(manifest, candidate, evaluate_reference,
            evaluation_id="l5-paired-density-geometry-v1", workflow_context=settings)
        nominal = _evaluate_context(candidate, study.model_context, settings)
        # Audit nominal and sampled extremes, not an inferred ensemble nominal.
        from ncmemsim.ensemble.model_execution import apply_model_sample_to_context
        density_samples = [min(manifest.samples, key=lambda s: s.values[0]), max(manifest.samples, key=lambda s: s.values[0])]
        contexts = [study.model_context] + [apply_model_sample_to_context(manifest.sampling_spec, s, candidate).model_context
                                           for s in density_samples]
        deltas = []
        for context in contexts:
            coarse = _evaluate_context(candidate, context, settings)
            fine = _evaluate_context(candidate, context, {**settings, "steps": 32})
            delta = max(abs(a-b) for a,b in zip(coarse["final_mean_occupation_by_fg"],fine["final_mean_occupation_by_fg"],strict=True))
            if delta > OCCUPATION_ATOL or coarse["clamped_steps"]:
                raise AssertionError("candidate grid fails numerical audit")
            deltas.append(delta)
        audit.append({"point_hash": point.point_hash, "occupation_deltas_16_vs_32": deltas,
                      "occupation_atol": OCCUPATION_ATOL})
        population = analyze_model_execution(execution, metrics,
            nominal_references=(NominalMetricReference("tat_rate", "Hz", nominal["initial_tat_rate_Hz"]),))
        sources.append(evaluate_model_eligibility(ModelDTCOStudy(point, population), constraints))
    result = analyze_model_pareto(sources, objectives, name="L5 paired-density thickness tradeoff")
    payload = {"schema_version": "l5-model-dtco-reference-v1", "experiment": experiment.to_dict(),
               "pareto": result.to_dict(), "timestep_audit": audit,
               "limits": ["synthetic assumed lognormal density; not measured or calibrated",
                          "16 paired draws do not establish tail convergence or sampling uncertainty",
                          "maximize mean TAT and minimize spread are illustrative declared objectives",
                          "fixed-field closed inter-FG redistribution is not full device retention",
                          "occupation spread is not claimed numerically resolved",
                          "finite 16/32-step comparison is not an exact-solution error bound"]}
    return {**payload, "reference_hash": canonical_hash(payload)}


def write_reference(destination, evidence):
    payload = {k:v for k,v in evidence.items() if k != "reference_hash"}
    if evidence.get("reference_hash") != canonical_hash(payload):
        raise ValueError("reference hash mismatch")
    serialized = json.dumps(evidence, indent=2, allow_nan=False)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    (destination/"reference.json").write_text(serialized+"\n",encoding="utf-8")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    evidence=run_reference()
    if args.output:
        write_reference(args.output,evidence)
    print(json.dumps({"reference_hash":evidence["reference_hash"],"fronts":evidence["pareto"]["fronts"],
                      "ranked_design_count":evidence["pareto"]["ranked_design_count"]},indent=2))
