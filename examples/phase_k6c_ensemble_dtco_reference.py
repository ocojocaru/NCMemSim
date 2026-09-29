"""Phase K6c multi-parameter ensemble DTCO reference study.

This reference combines a deterministic tunnel-thickness/program-voltage
design space with paired stochastic nanocrystal-diameter and
electrically-active-fraction realizations.

The stochastic distributions are controlled assumptions inherited from the
K6b references. They are not measured process distributions and simulated
pass fractions are not manufacturing-yield estimates.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import platform

import numpy as np

from ncmemsim import DeviceBuilder
from ncmemsim._version import __version__
from ncmemsim.dtco import (
    AppliedExperimentPoint,
    BindingScope,
    ConstraintOperator,
    DesignVariable,
    DesignVariableRole,
    ExperimentSpec,
    MetricAnalysisSpec,
    MetricConstraint,
    MetricDefinition,
    ObjectiveDirection,
    ParameterBinding,
    SweepPoint,
    apply_experiment_point,
    iter_cartesian_points,
)
from ncmemsim.ensemble import (
    EnsembleExecutionResult,
    EnsembleFeasibilitySummary,
    EnsembleMetricAnalysisResult,
    EnsemblePopulationStatistics,
    EnsembleSpec,
    EnsembleStatisticsSpec,
    NominalMetricReference,
    NormalDistribution,
    PhysicalDomain,
    RNGSpec,
    SampleManifest,
    SamplingSpec,
    StochasticVariable,
    analyze_ensemble_execution,
    execute_sample_manifest,
    generate_sample_manifest,
    summarize_ensemble_feasibility,
    summarize_ensemble_metrics,
)
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)
from ncmemsim.program_protocol import (
    ProgramPulseReadProtocol,
    run_program_pulse_read,
)
from ncmemsim.simulator import SimulationConfig, Simulator


TUNNEL_THICKNESS_VALUES_NM = (6.0, 8.0, 10.0)
PROGRAM_VOLTAGE_VALUES_V = (4.0, 5.0, 6.0)

NOMINAL_TUNNEL_THICKNESS_NM = 8.0
NOMINAL_PROGRAM_VOLTAGE_V = 5.0
PROGRAMMING_TIME_S = 1.0e-6

NOMINAL_DIAMETER_NM = 5.0
DIAMETER_STANDARD_DEVIATION_NM = 0.35
NOMINAL_ACTIVE_FRACTION = 0.22
ACTIVE_FRACTION_STANDARD_DEVIATION = 0.03

REFERENCE_SEED = 2028
REFERENCE_SAMPLE_COUNT = 6

REFERENCE_EXPERIMENT_NAME = "phase-k6c-ensemble-dtco-reference"
REFERENCE_ENSEMBLE_NAME = "phase-k6c-paired-variability"


@dataclass(frozen=True)
class ReferenceEnsembleCase:
    """One DTCO point with its applied baseline and paired sample manifest."""

    point: SweepPoint
    applied: AppliedExperimentPoint
    manifest: SampleManifest


@dataclass(frozen=True)
class ReferenceExecutionCase:
    """One K6c ensemble case with its complete K3 execution result."""

    ensemble_case: ReferenceEnsembleCase
    execution: EnsembleExecutionResult


@dataclass(frozen=True)
class ReferenceAnalysisCase:
    """One K6c design point with its immutable K4a-K4c analysis chain."""

    execution_case: ReferenceExecutionCase
    metric_analysis: EnsembleMetricAnalysisResult
    population_statistics: EnsemblePopulationStatistics
    feasibility: EnsembleFeasibilitySummary


def _diameter_provenance() -> ParameterProvenance:
    return ParameterProvenance(
        source=(
            "Phase K6c controlled reference assumption inherited from K6b; "
            "not an experimentally measured diameter distribution"
        ),
        status=ParameterStatus.ASSUMED,
    )


def _active_fraction_provenance() -> ParameterProvenance:
    return ParameterProvenance(
        source=(
            "Phase K6c controlled reference assumption inherited from K6b; "
            "not an experimentally measured active-fraction distribution"
        ),
        status=ParameterStatus.ASSUMED,
    )


def _stochastic_variables() -> tuple[StochasticVariable, StochasticVariable]:
    """Return the frozen ordered K6c stochastic-variable definitions."""

    return (
        StochasticVariable(
            name="nc_diameter",
            binding=ParameterBinding(
                BindingScope.DEVICE,
                (
                    "layers",
                    "FG1",
                    "nc_diameter_nm",
                ),
            ),
            distribution=NormalDistribution(
                mean=NOMINAL_DIAMETER_NM,
                standard_deviation=DIAMETER_STANDARD_DEVIATION_NM,
            ),
            unit="nm",
            physical_domain=PhysicalDomain(
                lower=0.0,
                lower_inclusive=False,
            ),
            provenance=_diameter_provenance(),
            applicability=(
                "Controlled paired variability reference for one-FG "
                "electrical program/read DTCO"
            ),
            nominal_value=NOMINAL_DIAMETER_NM,
        ),
        StochasticVariable(
            name="active_fraction",
            binding=ParameterBinding(
                BindingScope.DEVICE,
                (
                    "layers",
                    "FG1",
                    "electrically_active_fraction",
                ),
            ),
            distribution=NormalDistribution(
                mean=NOMINAL_ACTIVE_FRACTION,
                standard_deviation=ACTIVE_FRACTION_STANDARD_DEVIATION,
            ),
            unit="1",
            physical_domain=PhysicalDomain(
                lower=0.0,
                upper=1.0,
                lower_inclusive=True,
                upper_inclusive=True,
            ),
            provenance=_active_fraction_provenance(),
            applicability=(
                "Controlled paired electrically-active-fraction disorder "
                "reference; not TAT trap-density variation"
            ),
            nominal_value=NOMINAL_ACTIVE_FRACTION,
        ),
    )


def build_reference_experiment():
    """Return the K6c base device, operating protocol and DTCO experiment."""

    device = DeviceBuilder.v2(
        n_fgs=1,
        name="k6c-ensemble-dtco-reference",
    )
    protocol = ProgramPulseReadProtocol(
        NOMINAL_PROGRAM_VOLTAGE_V,
        PROGRAMMING_TIME_S,
    )

    variables = (
        DesignVariable(
            name="tunnel_thickness_nm",
            binding=ParameterBinding(
                BindingScope.DEVICE,
                (
                    "layers",
                    "tunnel_sio2",
                    "thickness_nm",
                ),
            ),
            values=TUNNEL_THICKNESS_VALUES_NM,
            role=DesignVariableRole.GEOMETRY,
            unit="nm",
        ),
        DesignVariable(
            name="program_voltage_V",
            binding=ParameterBinding(
                BindingScope.OPERATING,
                (
                    "program",
                    "voltage_V",
                ),
            ),
            values=PROGRAM_VOLTAGE_VALUES_V,
            role=DesignVariableRole.ELECTRICAL,
            unit="V",
        ),
    )

    experiment = ExperimentSpec.from_device(
        name=REFERENCE_EXPERIMENT_NAME,
        device=device,
        variables=variables,
        description=(
            "Phase K6c controlled variability-aware DTCO reference: "
            "tunnel thickness versus program voltage."
        ),
        operating_protocol=protocol,
    )

    return device, protocol, experiment


def build_reference_design_points(
    experiment: ExperimentSpec,
) -> tuple[SweepPoint, ...]:
    """Return all nine canonical DTCO points in declared Cartesian order."""

    if not isinstance(experiment, ExperimentSpec):
        raise TypeError("experiment must be an ExperimentSpec")

    return tuple(iter_cartesian_points(experiment))


def build_reference_design_space():
    """Return base device, protocol, experiment and its ordered design points."""

    device, protocol, experiment = build_reference_experiment()
    points = build_reference_design_points(experiment)
    return device, protocol, experiment, points


def build_reference_ensemble_cases(
    *,
    sample_count: int = REFERENCE_SAMPLE_COUNT,
    seed: int = REFERENCE_SEED,
) -> tuple[ReferenceEnsembleCase, ...]:
    """Build distinct per-design manifests with deterministic paired draws."""

    if type(sample_count) is not int or sample_count <= 0:
        raise ValueError("sample_count must be a positive integer")
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")

    device, protocol, experiment, points = build_reference_design_space()
    stochastic_variables = _stochastic_variables()

    cases: list[ReferenceEnsembleCase] = []

    for point in points:
        applied = apply_experiment_point(
            experiment,
            device,
            protocol,
            point.assignments,
        )

        ensemble = EnsembleSpec.from_device(
            name=REFERENCE_ENSEMBLE_NAME,
            device=applied.device,
            variables=stochastic_variables,
            description=(
                "Phase K6c paired NC-diameter and electrically-active-fraction "
                "variability at one DTCO design point."
            ),
            operating_protocol=applied.operating_protocol,
        )

        sampling_spec = SamplingSpec(
            ensemble_spec=ensemble,
            rng=RNGSpec(seed=seed),
            sample_count=sample_count,
        )
        manifest = generate_sample_manifest(sampling_spec)

        cases.append(
            ReferenceEnsembleCase(
                point=point,
                applied=applied,
                manifest=manifest,
            )
        )

    return tuple(cases)



def build_reference_executions(
    *,
    sample_count: int = REFERENCE_SAMPLE_COUNT,
    seed: int = REFERENCE_SEED,
) -> tuple[ReferenceExecutionCase, ...]:
    """Execute all paired K6c realizations with the real program/read solver."""

    cases = build_reference_ensemble_cases(
        sample_count=sample_count,
        seed=seed,
    )
    config = SimulationConfig()
    executions: list[ReferenceExecutionCase] = []

    for case in cases:
        point = case.point
        applied = case.applied

        evaluation_parameters = {
            "simulation_config": asdict(config),
            "physics_model": "PhysicsModel.default",
            "ncmemsim_version": __version__,
            "python_version": platform.python_version(),
            "numpy_version": np.__version__,
            "initial_state": "empty_for_each_realization",
            "uncertainty_basis": (
                "assumed independent normal NC-diameter and "
                "electrically-active-fraction distributions; "
                "not experimentally calibrated"
            ),
            "nominal_nc_diameter_nm": NOMINAL_DIAMETER_NM,
            "diameter_standard_deviation_nm": (
                DIAMETER_STANDARD_DEVIATION_NM
            ),
            "nominal_active_fraction": NOMINAL_ACTIVE_FRACTION,
            "active_fraction_standard_deviation": (
                ACTIVE_FRACTION_STANDARD_DEVIATION
            ),
            "stochastic_dependence": "independent",
            "sample_count": sample_count,
            "rng_seed": seed,
            "cross_design_pairing": (
                "distinct point-bound manifests with identical physical "
                "draws at equal sample_index"
            ),
            "design_point_index": point.index,
            "tunnel_thickness_nm": float(
                point.assignments["tunnel_thickness_nm"]
            ),
            "program_voltage_V": float(
                point.assignments["program_voltage_V"]
            ),
        }

        def evaluate(
            candidate,
            candidate_protocol,
            realization,
        ):
            pulse = run_program_pulse_read(
                Simulator(
                    candidate,
                    config=config,
                ),
                candidate_protocol,
            )
            payload = pulse.to_dict()
            payload["shift_magnitude_V"] = abs(
                pulse.delta_vfb_V
            )
            payload["nc_diameter_nm"] = float(
                candidate.floating_gates()[0].nc_diameter_nm
            )
            payload["electrically_active_fraction"] = float(
                candidate.floating_gates()[0].electrically_active_fraction
            )
            payload["program_voltage_V"] = float(
                candidate_protocol.program_voltage_V
            )
            payload["tunnel_thickness_nm"] = float(
                candidate.get_layer("tunnel_sio2").thickness_nm
            )
            return payload

        execution = execute_sample_manifest(
            case.manifest,
            applied.device,
            evaluate,
            base_operating_protocol=applied.operating_protocol,
            evaluation_id=(
                "phase-k6c-ensemble-dtco-program-read-reference-v1"
            ),
            evaluation_parameters=evaluation_parameters,
        )

        executions.append(
            ReferenceExecutionCase(
                ensemble_case=case,
                execution=execution,
            )
        )

    return tuple(executions)


def _metric_analysis_spec() -> MetricAnalysisSpec:
    """Return the frozen six-metric K6c K4 analysis contract."""

    return MetricAnalysisSpec(
        name="phase-k6c-ensemble-dtco-reference-metrics",
        metrics=(
            MetricDefinition(
                "shift_magnitude",
                ("shift_magnitude_V",),
                "V",
                ObjectiveDirection.MAXIMIZE,
            ),
            MetricDefinition(
                "occupation",
                ("mean_occupation",),
                "1",
            ),
            MetricDefinition(
                "nc_diameter",
                ("nc_diameter_nm",),
                "nm",
            ),
            MetricDefinition(
                "active_fraction",
                ("electrically_active_fraction",),
                "1",
            ),
            MetricDefinition(
                "program_voltage",
                ("program_voltage_V",),
                "V",
            ),
            MetricDefinition(
                "tunnel_thickness",
                ("tunnel_thickness_nm",),
                "nm",
            ),
        ),
        constraints=(
            MetricConstraint(
                "occupation_min",
                "occupation",
                ConstraintOperator.GE,
                0.0,
                "1",
            ),
            MetricConstraint(
                "occupation_max",
                "occupation",
                ConstraintOperator.LE,
                1.0,
                "1",
            ),
            MetricConstraint(
                "active_fraction_min",
                "active_fraction",
                ConstraintOperator.GE,
                0.0,
                "1",
            ),
            MetricConstraint(
                "active_fraction_max",
                "active_fraction",
                ConstraintOperator.LE,
                1.0,
                "1",
            ),
        ),
    )


def _nominal_payload(
    execution_case: ReferenceExecutionCase,
    config: SimulationConfig,
) -> dict[str, object]:
    """Evaluate the point-specific nominal device without stochastic variation."""

    case = execution_case.ensemble_case
    candidate = case.applied.device
    candidate_protocol = case.applied.operating_protocol

    pulse = run_program_pulse_read(
        Simulator(
            candidate,
            config=config,
        ),
        candidate_protocol,
    )
    payload = pulse.to_dict()
    payload["shift_magnitude_V"] = abs(
        pulse.delta_vfb_V
    )
    payload["nc_diameter_nm"] = float(
        candidate.floating_gates()[0].nc_diameter_nm
    )
    payload["electrically_active_fraction"] = float(
        candidate.floating_gates()[0].electrically_active_fraction
    )
    payload["program_voltage_V"] = float(
        candidate_protocol.program_voltage_V
    )
    payload["tunnel_thickness_nm"] = float(
        candidate.get_layer("tunnel_sio2").thickness_nm
    )
    return payload


def build_reference_analyses(
    *,
    sample_count: int = REFERENCE_SAMPLE_COUNT,
    seed: int = REFERENCE_SEED,
) -> tuple[ReferenceAnalysisCase, ...]:
    """Build the complete K4a-K4c chain for all nine K6c design points."""

    execution_cases = build_reference_executions(
        sample_count=sample_count,
        seed=seed,
    )
    metric_spec = _metric_analysis_spec()
    statistics_spec = EnsembleStatisticsSpec()
    config = SimulationConfig()

    analyses: list[ReferenceAnalysisCase] = []

    for execution_case in execution_cases:
        metric_analysis = analyze_ensemble_execution(
            execution_case.execution,
            metric_spec,
        )
        statistics = summarize_ensemble_metrics(
            metric_analysis,
            statistics_spec,
        )

        nominal = _nominal_payload(
            execution_case,
            config,
        )
        nominal_references = (
            NominalMetricReference(
                "shift_magnitude",
                "V",
                float(nominal["shift_magnitude_V"]),
            ),
            NominalMetricReference(
                "occupation",
                "1",
                float(nominal["mean_occupation"]),
            ),
            NominalMetricReference(
                "nc_diameter",
                "nm",
                NOMINAL_DIAMETER_NM,
            ),
            NominalMetricReference(
                "active_fraction",
                "1",
                NOMINAL_ACTIVE_FRACTION,
            ),
            NominalMetricReference(
                "program_voltage",
                "V",
                float(nominal["program_voltage_V"]),
            ),
            NominalMetricReference(
                "tunnel_thickness",
                "nm",
                float(nominal["tunnel_thickness_nm"]),
            ),
        )
        feasibility = summarize_ensemble_feasibility(
            statistics,
            nominal_references=nominal_references,
        )

        analyses.append(
            ReferenceAnalysisCase(
                execution_case=execution_case,
                metric_analysis=metric_analysis,
                population_statistics=statistics,
                feasibility=feasibility,
            )
        )

    return tuple(analyses)

def main() -> None:
    """Run the complete K6c K4 reference and print point/population summaries."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample-count",
        type=int,
        default=REFERENCE_SAMPLE_COUNT,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=REFERENCE_SEED,
    )
    args = parser.parse_args()

    _, _, experiment, _ = build_reference_design_space()
    analysis_cases = build_reference_analyses(
        sample_count=args.sample_count,
        seed=args.seed,
    )

    attempted = sum(
        item.feasibility.attempted_count
        for item in analysis_cases
    )
    assessed = sum(
        item.feasibility.assessed_count
        for item in analysis_cases
    )
    feasible = sum(
        item.feasibility.feasible_count
        for item in analysis_cases
    )
    infeasible = sum(
        item.feasibility.infeasible_count
        for item in analysis_cases
    )
    failed = sum(
        item.feasibility.failed_count
        for item in analysis_cases
    )

    print("experiment_hash:", experiment.experiment_hash)
    print("design_point_count:", experiment.design_point_count)
    print("sample_count:", args.sample_count)
    print("seed:", args.seed)

    for item in analysis_cases:
        case = item.execution_case.ensemble_case
        feasibility = item.feasibility
        print(
            case.point.index,
            case.point.assignments,
            "manifest_hash=",
            case.manifest.manifest_hash,
            "assessed=",
            feasibility.assessed_count,
            "feasible=",
            feasibility.feasible_count,
            "failed=",
            feasibility.failed_count,
            "simulated_pass_fraction=",
            feasibility.simulated_pass_fraction,
        )

    print("attempted:", attempted)
    print("assessed:", assessed)
    print("feasible:", feasible)
    print("infeasible:", infeasible)
    print("failed:", failed)


if __name__ == "__main__":
    main()
