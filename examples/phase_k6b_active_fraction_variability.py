"""Phase K6b electrically-active-fraction variability reference study.

This is a controlled synthetic ensemble reference for floating-gate
electrically-active-fraction disorder. It is not a measured process
distribution, not a trap-density model, and not a manufacturing-yield
prediction.

Run as:
    python -m examples.phase_k6b_active_fraction_variability --output-dir <path>
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from io import StringIO
import json
from pathlib import Path
import platform

import numpy as np

from ncmemsim import DeviceBuilder
from ncmemsim._version import __version__
from ncmemsim.dtco import (
    BindingScope,
    ConstraintOperator,
    MetricAnalysisSpec,
    MetricConstraint,
    MetricDefinition,
    ObjectiveDirection,
    ParameterBinding,
    SweepPoint,
)
from ncmemsim.ensemble import (
    EnsembleDTCOStudy,
    EnsembleReport,
    EnsembleReportStudy,
    EnsembleSpec,
    EnsembleStatisticsSpec,
    NormalDistribution,
    NominalMetricReference,
    PhysicalDomain,
    RNGSpec,
    SamplingSpec,
    StochasticVariable,
    analyze_ensemble_execution,
    build_ensemble_report,
    evaluate_ensemble_eligibility,
    execute_sample_manifest,
    generate_sample_manifest,
    summarize_ensemble_feasibility,
    summarize_ensemble_metrics,
    write_ensemble_report,
)
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)
from ncmemsim.program_protocol import (
    ProgramPulseReadProtocol,
    run_program_pulse_read,
)
from ncmemsim.simulator import SimulationConfig, Simulator


REFERENCE_SEED = 2027
REFERENCE_SAMPLE_COUNT = 6
NOMINAL_ACTIVE_FRACTION = 0.22
ACTIVE_FRACTION_STANDARD_DEVIATION = 0.03


def _provenance() -> ParameterProvenance:
    return ParameterProvenance(
        source=(
            "Phase K6b controlled reference assumption; "
            "not an experimentally measured active-fraction distribution"
        ),
        status=ParameterStatus.ASSUMED,
    )


def _design_point(
    *,
    nominal_active_fraction: float,
) -> SweepPoint:
    definition = {
        "schema_version": "phase-k6b-reference-design-v1",
        "name": "k6b-active-fraction-reference",
        "nominal_electrically_active_fraction": nominal_active_fraction,
        "role": "single nominal design anchor for ensemble reporting",
    }
    return SweepPoint(
        canonical_hash(definition),
        0,
        (
            (
                "nominal_electrically_active_fraction",
                float(nominal_active_fraction),
            ),
        ),
    )


def build_reference_report(
    *,
    sample_count: int = REFERENCE_SAMPLE_COUNT,
    seed: int = REFERENCE_SEED,
) -> EnsembleReport:
    """Build the deterministic K6b active-fraction reference report."""

    if type(sample_count) is not int or sample_count <= 0:
        raise ValueError("sample_count must be a positive integer")
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")

    device = DeviceBuilder.v2(
        n_fgs=1,
        active_fraction=NOMINAL_ACTIVE_FRACTION,
        name="k6b-active-fraction-reference",
    )
    protocol = ProgramPulseReadProtocol(
        5.0,
        1.0e-6,
    )
    config = SimulationConfig()

    variable = StochasticVariable(
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
        provenance=_provenance(),
        applicability=(
            "Controlled single-parameter electrically-active-fraction "
            "variability reference for one-FG electrical program/read"
        ),
        nominal_value=NOMINAL_ACTIVE_FRACTION,
    )

    ensemble = EnsembleSpec.from_device(
        name="phase-k6b-active-fraction-variability",
        device=device,
        variables=(variable,),
        operating_protocol=protocol,
    )
    sampling_spec = SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=seed),
        sample_count=sample_count,
    )
    manifest = generate_sample_manifest(
        sampling_spec
    )

    evaluation_parameters = {
        "simulation_config": asdict(config),
        "physics_model": "PhysicsModel.default",
        "ncmemsim_version": __version__,
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "initial_state": "empty_for_each_realization",
        "uncertainty_basis": (
            "assumed normal electrically-active-fraction distribution; "
            "not experimentally calibrated"
        ),
        "nominal_electrically_active_fraction": NOMINAL_ACTIVE_FRACTION,
        "active_fraction_standard_deviation": (
            ACTIVE_FRACTION_STANDARD_DEVIATION
        ),
        "tat_scope": (
            "does not vary TrapSpecies or TAT trap density; "
            "Phase-K MODEL bindings remain unsupported"
        ),
    }

    def physics(candidate, candidate_protocol):
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
        payload["electrically_active_fraction"] = float(
            candidate.floating_gates()[0].electrically_active_fraction
        )
        return payload

    def evaluate(
        candidate,
        candidate_protocol,
        realization,
    ):
        return physics(
            candidate,
            candidate_protocol,
        )

    execution = execute_sample_manifest(
        manifest,
        device,
        evaluate,
        base_operating_protocol=protocol,
        evaluation_id=(
            "phase-k6b-active-fraction-program-read-reference-v1"
        ),
        evaluation_parameters=evaluation_parameters,
    )

    metric_spec = MetricAnalysisSpec(
        name="k6b-active-fraction-reference-metrics",
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
                "active_fraction",
                ("electrically_active_fraction",),
                "1",
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

    metric_analysis = analyze_ensemble_execution(
        execution,
        metric_spec,
    )
    statistics = summarize_ensemble_metrics(
        metric_analysis,
        EnsembleStatisticsSpec(),
    )

    nominal_payload = physics(
        device,
        protocol,
    )
    nominal_references = (
        NominalMetricReference(
            "shift_magnitude",
            "V",
            float(nominal_payload["shift_magnitude_V"]),
        ),
        NominalMetricReference(
            "occupation",
            "1",
            float(nominal_payload["mean_occupation"]),
        ),
        NominalMetricReference(
            "active_fraction",
            "1",
            NOMINAL_ACTIVE_FRACTION,
        ),
    )
    feasibility = summarize_ensemble_feasibility(
        statistics,
        nominal_references=nominal_references,
    )

    study = EnsembleDTCOStudy(
        design_point=_design_point(
            nominal_active_fraction=NOMINAL_ACTIVE_FRACTION,
        ),
        source=feasibility,
    )
    eligibility = evaluate_ensemble_eligibility(
        study,
        (),
    )

    report_study = EnsembleReportStudy(
        execution=execution,
        metric_analysis=metric_analysis,
        population_statistics=statistics,
        feasibility=feasibility,
        study=study,
        eligibility=eligibility,
    )

    return build_ensemble_report(
        (report_study,),
        name="Electrically-active-fraction variability reference",
        metadata={
            "workflow": (
                "phase-k6b-active-fraction-variability-v1"
            ),
            "reference_type": (
                "controlled-single-parameter-ensemble"
            ),
            "variable": "FG1.electrically_active_fraction",
            "unit": "1",
            "nominal_value": NOMINAL_ACTIVE_FRACTION,
            "distribution": {
                "kind": "normal",
                "mean": NOMINAL_ACTIVE_FRACTION,
                "standard_deviation": (
                    ACTIVE_FRACTION_STANDARD_DEVIATION
                ),
            },
            "physical_domain": {
                "lower": 0.0,
                "upper": 1.0,
                "lower_inclusive": True,
                "upper_inclusive": True,
            },
            "seed": seed,
            "sample_count": sample_count,
            "scope": (
                "single-program electrical response; "
                "not a memory-window prediction"
            ),
            "interpretation": (
                "synthetic assumed electrically-active-fraction disorder; "
                "not measured process statistics, not TAT trap density, "
                "and not manufacturing yield"
            ),
            "feasibility_definition": (
                "occupation and active-fraction bounds only; "
                "simulated pass fraction is not a manufacturing-yield estimate"
            ),
            "tat_limitation": (
                "TrapSpecies density_m3 is a MODEL/TAT parameter and is "
                "not varied by this reference because Phase-K MODEL "
                "bindings remain explicitly unsupported"
            ),
            "common_random_numbers": (
                "not applicable: single design point"
            ),
        },
    )


def plot_reference(
    report: EnsembleReport,
    output_dir: str | Path,
) -> tuple[Path, Path]:
    """Write optional PNG/SVG active-fraction response plots."""

    if not isinstance(report, EnsembleReport):
        raise TypeError("report must be an EnsembleReport")

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    directory = Path(output_dir).resolve()
    targets = (
        directory / "active-fraction-shift.png",
        directory / "active-fraction-shift.svg",
    )
    for target in targets:
        if target.exists():
            raise FileExistsError(
                f"plot target already exists: {target}"
            )

    rows = list(
        csv.DictReader(
            StringIO(
                report.samples_csv()
            )
        )
    )
    points = []
    for row in rows:
        if row["metric_status"] == "failed":
            continue
        metrics = json.loads(
            row["metrics_json"]
        )
        points.append(
            (
                float(metrics["active_fraction"]),
                float(metrics["shift_magnitude"]),
            )
        )

    fig, ax = plt.subplots(
        figsize=(6.4, 4.2),
        layout="constrained",
    )
    try:
        if points:
            ax.scatter(
                [item[0] for item in points],
                [item[1] for item in points],
                s=38,
            )
        ax.axvline(
            NOMINAL_ACTIVE_FRACTION,
            linestyle="--",
            linewidth=1.0,
            label="Nominal active fraction",
        )
        ax.set(
            xlabel="Electrically active fraction (1)",
            ylabel="Program-induced |ΔVFB| (V)",
        )
        ax.grid(alpha=0.2)
        ax.legend(frameon=False)
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        fig.savefig(
            targets[0],
            dpi=300,
        )
        with plt.rc_context(
            {"svg.hashsalt": report.report_hash}
        ):
            fig.savefig(
                targets[1],
                metadata={"Date": None},
            )
    finally:
        plt.close(fig)

    return targets


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
    )
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
    parser.add_argument(
        "--plots",
        action="store_true",
        help="requires optional matplotlib",
    )
    args = parser.parse_args()

    if args.plots:
        for name in (
            "active-fraction-shift.png",
            "active-fraction-shift.svg",
        ):
            if (
                args.output_dir / name
            ).exists():
                parser.error(
                    f"plot target already exists: {name}"
                )

    report = build_reference_report(
        sample_count=args.sample_count,
        seed=args.seed,
    )
    paths = write_ensemble_report(
        report,
        args.output_dir,
    )
    if args.plots:
        paths += plot_reference(
            report,
            args.output_dir,
        )

    for path in paths:
        print(path)
    print("report_hash:", report.report_hash)


if __name__ == "__main__":
    main()
