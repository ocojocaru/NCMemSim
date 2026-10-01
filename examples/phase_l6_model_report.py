# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Rebuild a complete L6 report from stored L5 evidence without rerunning physics."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ncmemsim.hashing import canonical_hash
from ncmemsim.ensemble.model_sampling import _strict_json
from ncmemsim.ensemble.model_dtco import ModelParetoAnalysis
from ncmemsim.ensemble.model_reporting import ModelReportStudy, build_model_report, write_model_report, load_model_report_bundle


def report_from_reference(evidence):
    """Verify the stored L5 envelope and restore all linked MODEL results."""
    required = {"schema_version", "experiment", "pareto", "timestep_audit", "limits", "reference_hash"}
    if type(evidence) is not dict or set(evidence) != required or evidence["schema_version"] != "l5-model-dtco-reference-v1":
        raise ValueError("unsupported L5 reference envelope")
    if evidence["reference_hash"] != canonical_hash({k:v for k,v in evidence.items() if k != "reference_hash"}):
        raise ValueError("L5 reference hash mismatch")
    pareto = ModelParetoAnalysis.from_dict(evidence["pareto"])
    if any(s.study.design_point.experiment_hash != canonical_hash(evidence["experiment"]) for s in pareto.sources):
        raise ValueError("L5 experiment linkage mismatch")
    return build_model_report("L6 stored MODEL DTCO report", tuple(
        ModelReportStudy("design-"+str(s.study.design_point.index), s.study.source, s) for s in pareto.sources),
        pareto=pareto, limitations=evidence["limits"], evidence={
            "reference_hash": evidence["reference_hash"], "experiment": evidence["experiment"],
            "timestep_audit": evidence["timestep_audit"],
            "restoration_policy": "stored samples and outputs authoritative; no resampling or physics rerun"})


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,required=True,help="Existing L5 reference.json")
    parser.add_argument("--output",type=Path,required=True,help="New report directory")
    args=parser.parse_args()
    report=report_from_reference(_strict_json(args.input.read_text(encoding="utf-8")))
    write_model_report(report,args.output)
    restored=load_model_report_bundle(args.output)
    print(json.dumps({"report_hash":restored.report_hash,"studies":len(restored.studies),
        "attempts":sum(s.population.counts["attempted_count"] for s in restored.studies)},indent=2))
