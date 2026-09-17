"""Reference electrical DTCO workflow; run as python -m examples.phase_g6_dtco_reference."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
import platform

import numpy as np

from ncmemsim import DeviceBuilder
from ncmemsim._version import __version__
from ncmemsim.dtco import (
    BindingScope, ConstraintOperator, DesignVariable, DesignVariableRole,
    DTCOReport, ExperimentSpec, MetricAnalysisSpec, MetricConstraint,
    MetricDefinition, ObjectiveDirection, ParameterBinding, analyze_pareto,
    analyze_sensitivity, analyze_sweep, build_dtco_report, run_cartesian_sweep,
    write_dtco_report,
)
from ncmemsim.program_protocol import ProgramPulseReadProtocol, run_program_pulse_read
from ncmemsim.simulator import SimulationConfig, Simulator


def build_reference_report(*, include_invalid_point: bool = False) -> DTCOReport:
    device = DeviceBuilder.v2(n_fgs=1, name="g6-electrical-reference")
    protocol = ProgramPulseReadProtocol(5.0, 1e-6)
    durations = (1e-6, 2e-6, -1e-6) if include_invalid_point else (1e-6, 2e-6)
    variables = (
        DesignVariable("temperature", ParameterBinding(BindingScope.DEVICE, ("temperature_K",)),
                       (300.0, 325.0), DesignVariableRole.MODEL, "K"),
        DesignVariable("duration", ParameterBinding(BindingScope.OPERATING, ("program", "time_s")),
                       durations, DesignVariableRole.ELECTRICAL, "s"),
    )
    experiment = ExperimentSpec.from_device(
        name="g6-program-response-duration", device=device,
        variables=variables, operating_protocol=protocol,
    )
    config = SimulationConfig()
    def evaluate(candidate, candidate_protocol, point):
        pulse = run_program_pulse_read(Simulator(candidate, config=config), candidate_protocol)
        payload = pulse.to_dict()
        payload["shift_magnitude_V"] = abs(pulse.delta_vfb_V)
        return payload
    sweep = run_cartesian_sweep(
        experiment, device, evaluate, base_protocol=protocol,
        evaluation_id="g6-electrical-program-read-reference-v1",
        evaluation_parameters={
            "simulation_config": asdict(config), "physics_model": "PhysicsModel.default",
            "ncmemsim_version": __version__, "python_version": platform.python_version(),
            "numpy_version": np.__version__, "initial_state": "empty_for_candidate",
            "derived_shift": "abs(delta_vfb_V)",
        },
    )
    analysis = analyze_sweep(sweep, MetricAnalysisSpec(
        name="g6-response-duration-metrics",
        metrics=(
            MetricDefinition("shift_magnitude", ("shift_magnitude_V",), "V", ObjectiveDirection.MAXIMIZE),
            MetricDefinition("duration", ("protocol", "programming_time_s"), "s", ObjectiveDirection.MINIMIZE),
            MetricDefinition("occupation", ("mean_occupation",), "1"),
        ),
        constraints=(
            MetricConstraint("occupation_min", "occupation", ConstraintOperator.GE, 0.0, "1"),
            MetricConstraint("occupation_max", "occupation", ConstraintOperator.LE, 1.0, "1"),
        ),
    ))
    return build_dtco_report(
        analysis, name="Electrical program/read DTCO reference",
        pareto=analyze_pareto(analysis), sensitivity=analyze_sensitivity(analysis),
        metadata={
            "workflow": "phase_g6_dtco_reference-v1",
            "scope": "single-program shift magnitude, not a memory window or calibrated prediction",
            "invalid_point_demo": include_invalid_point,
        },
    )


def plot_reference(report: DTCOReport, output_dir: str | Path) -> tuple[Path, Path]:
    """Optional publication-resolution PNG and vector SVG; plotting is not hashed."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    directory = Path(output_dir).resolve()
    targets = (directory / "response-duration.png", directory / "response-duration.svg")
    for target in targets:
        if target.exists():
            raise FileExistsError(f"plot target already exists: {target}")
    manifest = report.to_dict()
    points = manifest["metric_analysis"]["data"]["points"]
    eligible = [p for p in points if p["status"] != "failed"]
    front = set(manifest["pareto"]["data"]["pareto_indices"])
    fig, ax = plt.subplots(figsize=(6.4, 4.2), layout="constrained")
    try:
        for status, color in (("feasible", "#176b87"), ("infeasible", "#777777")):
            subset = [p for p in eligible if p["status"] == status]
            if subset:
                ax.scatter([p["metrics"]["duration"] for p in subset],
                           [p["metrics"]["shift_magnitude"] for p in subset],
                           c=color, label=status.capitalize(), s=38)
        selected = [p for p in eligible if p["index"] in front]
        if selected:
            ax.scatter([p["metrics"]["duration"] for p in selected],
                       [p["metrics"]["shift_magnitude"] for p in selected],
                       facecolors="none", edgecolors="#c45532", linewidths=1.5,
                       s=110, label="Pareto front")
        for point in eligible:
            ax.annotate(str(point["index"]),
                        (point["metrics"]["duration"], point["metrics"]["shift_magnitude"]),
                        xytext=(5, 5), textcoords="offset points", fontsize=8)
        ax.set(xlabel="Program pulse duration (s)", ylabel="Program-induced |ΔVFB| (V)")
        ax.grid(alpha=0.2)
        if eligible:
            ax.legend(frameon=False)
        directory.mkdir(parents=True, exist_ok=True)
        fig.savefig(targets[0], dpi=300)
        with plt.rc_context({"svg.hashsalt": report.report_hash}):
            fig.savefig(targets[1], metadata={"Date": None})
    finally:
        plt.close(fig)
    return targets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--include-invalid-point", action="store_true")
    parser.add_argument("--plots", action="store_true", help="requires optional matplotlib")
    args = parser.parse_args()
    if args.plots:
        for name in ("response-duration.png", "response-duration.svg"):
            if (args.output_dir / name).exists():
                parser.error(f"plot target already exists: {name}")
    report = build_reference_report(include_invalid_point=args.include_invalid_point)
    paths = write_dtco_report(report, args.output_dir)
    if args.plots:
        paths += plot_reference(report, args.output_dir)
    for path in paths:
        print(path)
    print("report_hash:", report.report_hash)


if __name__ == "__main__":
    main()
