"""Electrical Robust DTCO reference; assumed uncertainty, not calibrated yield."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from pathlib import Path
import sys
import numpy as np
if (Path(__file__).resolve().parents[1]/"ncmemsim").is_dir():
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (BindingScope, ParameterBinding, TruncatedNormalVariation, UniformVariation,
    VariationDefinition, VariationKind, VariationProvenance, SamplingSpec, sample_variations,
    propagate_samples, MetricDefinition, MetricAnalysisSpec, MetricConstraint, ConstraintOperator,
    SampleAnalysisSpec, analyze_samples, evaluate_nominal, compare_nominal, ObjectiveDirection,
    RobustStatistic, RobustFailurePolicy, RobustObjective, RobustParetoSpec, analyze_robust_pareto,
    RobustDTCOReport, build_robust_dtco_report, write_robust_dtco_report)
from ncmemsim.program_protocol import ProgramPulseReadProtocol, run_program_pulse_read
from ncmemsim.simulator import SimulationConfig, Simulator


def build_reference_report(*,include_failures: bool=False) -> RobustDTCOReport:
    provenance=VariationProvenance("Assumed reference intervals, not measured variation",
        "Electrical reference devices near room temperature")
    variations=(VariationDefinition("duration",ParameterBinding(BindingScope.OPERATING,("program","time_s")),
        TruncatedNormalVariation(1e-7,2e-7,1.5e-7,1e-8),"s",VariationKind.PARAMETER_ESTIMATION,provenance),
        VariationDefinition("work_function",ParameterBinding(BindingScope.DEVICE,("gate_work_function_eV",)),
        UniformVariation(4.7,4.9),"eV",VariationKind.PARAMETER_ESTIMATION,provenance))
    manifest=sample_variations(SamplingSpec(variations,seed=2026,sample_count=4,max_draws_per_value=10000))
    devices=[DeviceBuilder.v2(n_fgs=1,name="h6-temperature-300"),DeviceBuilder.v2(n_fgs=1,name="h6-temperature-325")]
    devices[1].temperature_K=325.0
    protocol=ProgramPulseReadProtocol(5.0,1.5e-7)
    config=SimulationConfig()
    parameters={"simulation_config":asdict(config),"physics_model":"PhysicsModel.default",
        "initial_state":"empty_for_each_candidate","failure_demo":include_failures,
        "failure_injection":"sample 1 evaluation, sample 2 missing metrics, sample 3 non-JSON output" if include_failures else "none"}
    def physics(candidate,p):
        pulse=run_program_pulse_read(Simulator(candidate,config=config),p)
        return {"signed_shift_V":pulse.delta_vfb_V,"duration_s":p.programming_time_s,
                "mean_occupation":pulse.mean_occupation}
    def evaluate(candidate,p,point):
        if include_failures:
            if point.index==1: raise RuntimeError("Deliberate H6 evaluation failure")
            if point.index==2: return {}
            if point.index==3: return {"unsupported":np.array([1.0])}
        return physics(candidate,p)
    metric_spec=SampleAnalysisSpec(MetricAnalysisSpec("reference-responses",
        (MetricDefinition("signed_shift",("signed_shift_V",),"V"),MetricDefinition("duration",("duration_s",),"s"),
         MetricDefinition("occupation",("mean_occupation",),"1")),
        (MetricConstraint("occupation_min","occupation",ConstraintOperator.GE,0,"1"),
         MetricConstraint("occupation_max","occupation",ConstraintOperator.LE,1,"1"))))
    analyses=[];comparisons=[]
    for device in devices:
        propagated=propagate_samples(manifest,device,evaluate,evaluation_id="h6-electrical-reference-v1",
            evaluation_parameters=parameters,base_protocol=protocol)
        analysis=analyze_samples(propagated,metric_spec);analyses.append(analysis)
        nominal=evaluate_nominal(device,physics,evaluation_id="h6-electrical-reference-v1",
            evaluation_parameters=parameters,base_protocol=protocol)
        comparisons.append(compare_nominal(analysis,nominal))
    robust=analyze_robust_pareto(analyses,RobustParetoSpec("reference-robust-fronts",
        (RobustObjective("lower_signed_shift","signed_shift","V",ObjectiveDirection.MAXIMIZE,RobustStatistic.QUANTILE,0.05),
         RobustObjective("mean_duration","duration","s",ObjectiveDirection.MINIMIZE,RobustStatistic.MEAN)),
        RobustFailurePolicy.ALLOW_ASSESSED_WITH_FAILURES if include_failures else RobustFailurePolicy.REQUIRE_NO_FAILURES,
        minimum_assessed_count=1 if include_failures else 4,minimum_observed_feasible_fraction=0.0 if include_failures else 1.0))
    return build_robust_dtco_report(analyses,name="Electrical Robust DTCO reference",nominal_comparisons=comparisons,
        robust_pareto=robust,metadata={"workflow":"phase-h6-electrical-v1","failure_demo":include_failures,
            "scope":"single-program signed shift, not calibrated manufacturing yield",
            "cross_study_sampling":"same exact manifest reused for both nominal temperatures"})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-failures",action="store_true")
    parser.add_argument("--output-dir",type=Path)
    args=parser.parse_args();report=build_reference_report(include_failures=args.include_failures)
    print("Report hash:",report.report_hash)
    if args.output_dir:
        for path in write_robust_dtco_report(report,args.output_dir): print(path)

if __name__=="__main__": main()
