# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Phase K6b nanocrystal-diameter variability reference study.

This is a controlled synthetic ensemble reference, not a measured process
distribution and not a manufacturing-yield prediction.

Run as:
    python -m examples.phase_k6b_nc_diameter_variability --output-dir <path>
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


REFERENCE_SEED = 2026
REFERENCE_SAMPLE_COUNT = 6
NOMINAL_DIAMETER_NM = 5.0
DIAMETER_STANDARD_DEVIATION_NM = 0.35


def _provenance() -> ParameterProvenance:
    return ParameterProvenance(
        source=(
            "Phase K6b controlled reference assumption; "
            "not an experimentally measured diameter distribution"
        ),
        status=ParameterStatus.ASSUMED,
    )


def _design_point(
    *,
    nominal_diameter_nm: float,
) -> SweepPoint:
    definition = {
        "schema_version": "phase-k6b-reference-design-v1",
        "name": "k6b-nc-diameter-reference",
        "nominal_nc_diameter_nm": nominal_diameter_nm,
        "role": "single nominal design anchor for ensemble reporting",
    }
    return SweepPoint(
        canonical_hash(definition),
        0,
        (("nominal_nc_diameter_nm", float(nominal_diameter_nm)),),
    )


def build_reference_report(
    *,
    sample_count: int = REFERENCE_SAMPLE_COUNT,
    seed: int = REFERENCE_SEED,
) -> EnsembleReport:
    """Build the deterministic K6b NC-diameter reference report."""

    if type(sample_count) is not int or sample_count <= 0:
        raise ValueError("sample_count must be a positive integer")
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")

    device = DeviceBuilder.v2(
        n_fgs=1,
        nc_diameter_nm=NOMINAL_DIAMETER_NM,
        name="k6b-nc-diameter-reference",
    )
    protocol = ProgramPulseReadProtocol(
        5.0,
        1.0e-6,
    )
    config = SimulationConfig()

    variable = StochasticVariable(
        name="diameter",
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
        provenance=_provenance(),
        applicability=(
            "Controlled single-parameter variability reference "
            "for one-FG electrical program/read"
        ),
        nominal_value=NOMINAL_DIAMETER_NM,
    )

    ensemble = EnsembleSpec.from_device(
        name="phase-k6b-nc-diameter-variability",
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
            "assumed normal NC-diameter distribution; "
            "not experimentally calibrated"
        ),
        "nominal_nc_diameter_nm": NOMINAL_DIAMETER_NM,
        "diameter_standard_deviation_nm": (
            DIAMETER_STANDARD_DEVIATION_NM
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
        payload["nc_diameter_nm"] = float(
            candidate.floating_gates()[0].nc_diameter_nm
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
            "phase-k6b-nc-diameter-program-read-reference-v1"
        ),
        evaluation_parameters=evaluation_parameters,
    )

    metric_spec = MetricAnalysisSpec(
        name="k6b-nc-diameter-reference-metrics",
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
            "nc_diameter",
            "nm",
            NOMINAL_DIAMETER_NM,
        ),
    )
    feasibility = summarize_ensemble_feasibility(
        statistics,
        nominal_references=nominal_references,
    )

    study = EnsembleDTCOStudy(
        design_point=_design_point(
            nominal_diameter_nm=NOMINAL_DIAMETER_NM,
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
        name="Nanocrystal-diameter variability reference",
        metadata={
            "workflow": (
                "phase-k6b-nc-diameter-variability-v1"
            ),
            "reference_type": (
                "controlled-single-parameter-ensemble"
            ),
            "variable": "FG1.nc_diameter_nm",
            "unit": "nm",
            "nominal_value": NOMINAL_DIAMETER_NM,
            "distribution": {
                "kind": "normal",
                "mean_nm": NOMINAL_DIAMETER_NM,
                "standard_deviation_nm": (
                    DIAMETER_STANDARD_DEVIATION_NM
                ),
            },
            "seed": seed,
            "sample_count": sample_count,
            "scope": (
                "single-program electrical response; "
                "not a memory-window prediction"
            ),
            "interpretation": (
                "synthetic assumed NC-diameter variability; "
                "not measured process statistics and not "
                "manufacturing yield"
            ),
            "feasibility_definition": (
                "occupation bounds only; simulated pass fraction "
                "is not a manufacturing-yield estimate"
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
    """Write optional PNG/SVG diameter-response plots outside report identity."""

    if not isinstance(report, EnsembleReport):
        raise TypeError("report must be an EnsembleReport")

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    directory = Path(output_dir).resolve()
    targets = (
        directory / "diameter-shift.png",
        directory / "diameter-shift.svg",
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
                float(metrics["nc_diameter"]),
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
            NOMINAL_DIAMETER_NM,
            linestyle="--",
            linewidth=1.0,
            label="Nominal diameter",
        )
        ax.set(
            xlabel="Nanocrystal diameter (nm)",
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
            "diameter-shift.png",
            "diameter-shift.svg",
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
