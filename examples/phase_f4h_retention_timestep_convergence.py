from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from ncmemsim.device_calibration import (
    DeviceCalibrationSpec,
    DeviceFitParameterBinding,
    DeviceFitTarget,
    apply_device_calibration_parameters,
)
from ncmemsim.device_objectives import interpolate_without_extrapolation
from ncmemsim.fitting import FitParameter, FitParameterSet
from ncmemsim.physics import PhysicsModel
from ncmemsim.reference import make_v53_reference_device
from ncmemsim.retention import RetentionConfig
from ncmemsim.retention_fit import (
    RetentionFitProtocol,
    predict_retention_fraction,
)
from ncmemsim.simulator import SimulationConfig, Simulator
from ncmemsim.state import DeviceState


TRUE_PHI_ERASE_EV = 2.10
RETENTION_GATE_VOLTAGE_V = -14.0
TOTAL_TIME_S = 3.0e-2
INITIAL_DT_S = 1.0e-7

# Keep the output grid fixed and deliberately dense so this audit isolates
# maximum_dt_s rather than mixing timestep and output-grid refinement.
OUTPUT_POINTS = 5001

TIMESTEP_CASES = (
    ("dt3e-6", 3.0e-6),
    ("dt1e-6", 1.0e-6),
    ("dt3e-7", 3.0e-7),
    ("dt1e-7", 1.0e-7),
)

REFERENCE_NAME = "dt1e-7"

PRODUCTION_FIT_TIMES_S = np.asarray(
    [
        1.0e-4,
        3.0e-4,
        1.0e-3,
        3.0e-3,
        1.0e-2,
        3.0e-2,
    ],
    dtype=float,
)

# Focus explicitly on the steep transition, which the original six-point
# production grid samples poorly once the solver is refined.
TRANSITION_PROBE_TIMES_S = np.asarray(
    [
        1.8e-3,
        1.9e-3,
        2.0e-3,
        2.1e-3,
        2.2e-3,
        2.3e-3,
        2.4e-3,
        2.5e-3,
        2.6e-3,
        2.7e-3,
        2.8e-3,
        2.9e-3,
        3.0e-3,
    ],
    dtype=float,
)

CROSSING_LEVELS = (0.99, 0.90, 0.75, 0.50, 0.25, 0.10, 0.05)


def make_base_objects():
    device = make_v53_reference_device(grid_points=7)
    physics = PhysicsModel.default()
    simulation_config = SimulationConfig(
        dwell_time_s=5.0e-3,
        internal_dt_s=1.0e-5,
        qfix_C_m2=0.0,
        qit_C_m2=0.0,
    )
    return device, physics, simulation_config


def make_pure_p2_state(device):
    state = DeviceState.empty_for_device(device)
    for fg_state in state.floating_gates:
        fg_state.P0[:] = 0.0
        fg_state.P1[:] = 0.0
        fg_state.P2[:] = 1.0
    state.validate(device)
    return state


def make_specification() -> DeviceCalibrationSpec:
    parameter = FitParameter(
        name="phi_barrier_erase_eV",
        initial_value=2.0,
        lower_bound=1.80,
        upper_bound=2.40,
        unit="eV",
        description="F4h2c2e timestep-convergence audit parameter.",
    )

    return DeviceCalibrationSpec(
        parameter_set=FitParameterSet((parameter,)),
        bindings=(
            DeviceFitParameterBinding(
                parameter_name="phi_barrier_erase_eV",
                target=DeviceFitTarget.FG_PHI_BARRIER_ERASE_EV,
                fg_index=0,
            ),
        ),
        name="f4h2c2e-timestep-convergence",
        notes=(
            "Controlled pure-P2 accelerated fixed-bias retention benchmark; "
            "numerical audit only."
        ),
    )


def make_protocol(maximum_dt_s: float) -> RetentionFitProtocol:
    return RetentionFitProtocol(
        RetentionConfig(
            gate_voltage_V=RETENTION_GATE_VOLTAGE_V,
            total_time_s=TOTAL_TIME_S,
            initial_dt_s=INITIAL_DT_S,
            maximum_dt_s=maximum_dt_s,
            output_points=OUTPUT_POINTS,
            stop_at_quasi_equilibrium=False,
            occupancy_integrator="backward_euler",
        )
    )


def simulate_case(maximum_dt_s: float) -> dict[str, Any]:
    device, physics, simulation_config = make_base_objects()
    specification = make_specification()

    context = apply_device_calibration_parameters(
        device,
        physics,
        simulation_config,
        specification,
        np.asarray([TRUE_PHI_ERASE_EV], dtype=float),
    )

    state = make_pure_p2_state(context.device)
    protocol = make_protocol(maximum_dt_s)

    prediction = predict_retention_fraction(
        Simulator(
            context.device,
            context.physics,
            context.simulation_config,
        ),
        protocol,
        initial_state=state,
    )

    production_values, production_interp = interpolate_without_extrapolation(
        PRODUCTION_FIT_TIMES_S,
        prediction.time_s,
        prediction.predicted_retention_fraction,
    )
    transition_values, transition_interp = interpolate_without_extrapolation(
        TRANSITION_PROBE_TIMES_S,
        prediction.time_s,
        prediction.predicted_retention_fraction,
    )

    return {
        "protocol": protocol,
        "prediction": prediction,
        "production_values": np.asarray(production_values, dtype=float),
        "transition_values": np.asarray(transition_values, dtype=float),
        "production_interpolation_used": bool(production_interp),
        "transition_interpolation_used": bool(transition_interp),
    }


def crossing_time_s(
    time_s: np.ndarray,
    fraction: np.ndarray,
    level: float,
) -> float | None:
    t = np.asarray(time_s, dtype=float)
    y = np.asarray(fraction, dtype=float)

    indices = np.flatnonzero(y <= level)
    if indices.size == 0:
        return None

    i = int(indices[0])
    if i == 0:
        return float(t[0])

    t0 = float(t[i - 1])
    t1 = float(t[i])
    y0 = float(y[i - 1])
    y1 = float(y[i])

    if y1 == y0:
        return t1

    w = (level - y0) / (y1 - y0)
    return float(t0 + w * (t1 - t0))


def protocol_dict(protocol: RetentionFitProtocol) -> dict[str, Any]:
    c = protocol.retention_config
    return {
        "gate_voltage_V": c.gate_voltage_V,
        "total_time_s": c.total_time_s,
        "initial_dt_s": c.initial_dt_s,
        "maximum_dt_s": c.maximum_dt_s,
        "growth_factor": c.growth_factor,
        "output_points": c.output_points,
        "occupancy_integrator": c.occupancy_integrator,
        "stop_at_quasi_equilibrium": c.stop_at_quasi_equilibrium,
    }


def run_audit() -> dict[str, Any]:
    simulations: dict[str, dict[str, Any]] = {}

    for name, maximum_dt_s in TIMESTEP_CASES:
        print(
            f"Running {name}: max_dt={maximum_dt_s:.1e} s, "
            f"output_points={OUTPUT_POINTS}"
        )
        simulations[name] = simulate_case(maximum_dt_s)

    reference = simulations[REFERENCE_NAME]

    rows: list[dict[str, Any]] = []

    for name, maximum_dt_s in TIMESTEP_CASES:
        simulation = simulations[name]
        prediction = simulation["prediction"]

        production_diff = (
            simulation["production_values"] - reference["production_values"]
        )
        transition_diff = (
            simulation["transition_values"] - reference["transition_values"]
        )

        crossings: dict[str, float | None] = {}
        for level in CROSSING_LEVELS:
            crossings[f"{level:.2f}"] = crossing_time_s(
                prediction.time_s,
                prediction.predicted_retention_fraction,
                level,
            )

        rows.append(
            {
                "name": name,
                "maximum_dt_s": maximum_dt_s,
                "protocol": protocol_dict(simulation["protocol"]),
                "protocol_hash": simulation["protocol"].protocol_hash(),
                "production_fit_values": simulation["production_values"].tolist(),
                "transition_probe_values": simulation["transition_values"].tolist(),
                "production_max_abs_difference_vs_reference": float(
                    np.max(np.abs(production_diff))
                ),
                "production_rmse_difference_vs_reference": float(
                    np.sqrt(np.mean(production_diff**2))
                ),
                "transition_max_abs_difference_vs_reference": float(
                    np.max(np.abs(transition_diff))
                ),
                "transition_rmse_difference_vs_reference": float(
                    np.sqrt(np.mean(transition_diff**2))
                ),
                "crossing_times_s": crossings,
            }
        )

    # Successive crossing-time changes are more informative than pointwise
    # vertical differences for this very steep transition.
    successive = []
    for index in range(1, len(rows)):
        previous = rows[index - 1]
        current = rows[index]

        changes = {}
        for level in CROSSING_LEVELS:
            key = f"{level:.2f}"
            t_prev = previous["crossing_times_s"][key]
            t_curr = current["crossing_times_s"][key]
            if t_prev is None or t_curr is None:
                changes[key] = None
            else:
                changes[key] = {
                    "absolute_change_s": float(t_curr - t_prev),
                    "relative_change": float((t_curr - t_prev) / t_curr),
                    "relative_change_percent": float(
                        100.0 * (t_curr - t_prev) / t_curr
                    ),
                }

        successive.append(
            {
                "from_case": previous["name"],
                "to_case": current["name"],
                "crossing_time_changes": changes,
            }
        )

    return {
        "schema_version": 1,
        "workflow": "f4h2c2e-retention-timestep-convergence-audit",
        "scientific_status": "NUMERICAL_REFINEMENT_AUDIT",
        "scientific_scope": (
            "Maximum-timestep convergence audit with a fixed dense output "
            "grid for the pure-P2, -14 V synthetic retention benchmark."
        ),
        "truth": {
            "phi_barrier_erase_eV": TRUE_PHI_ERASE_EV,
            "retention_gate_voltage_V": RETENTION_GATE_VOLTAGE_V,
            "initial_state": "pure-P2",
        },
        "fixed_output_points": OUTPUT_POINTS,
        "production_fit_times_s": PRODUCTION_FIT_TIMES_S.tolist(),
        "transition_probe_times_s": TRANSITION_PROBE_TIMES_S.tolist(),
        "reference_case": REFERENCE_NAME,
        "case_results": rows,
        "successive_crossing_time_changes": successive,
        "interpretation_policy": {
            "hard_pass_fail_threshold": None,
            "note": (
                "No arbitrary convergence threshold is imposed. The primary "
                "diagnostic is stabilization of transition crossing times as "
                "maximum_dt_s is reduced while output_points is held fixed."
            ),
            "steep_transition_note": (
                "Large vertical differences at fixed time can result from a "
                "small horizontal shift of a steep transition; crossing-time "
                "stability is therefore reported explicitly."
            ),
        },
    }


def format_array(values: np.ndarray) -> str:
    return np.array2string(
        np.asarray(values, dtype=float),
        precision=12,
        separator=", ",
        max_line_width=220,
    )


def format_time(value: float | None) -> str:
    if value is None:
        return "not reached"
    return f"{value:.9e}"


def print_report(report: dict[str, Any]) -> None:
    print()
    print("F4h2c2e fixed-output timestep convergence audit")
    print("==============================================")
    print(f"truth phi_erase = {TRUE_PHI_ERASE_EV:.12f} eV")
    print(f"Vret = {RETENTION_GATE_VOLTAGE_V:.6f} V")
    print(f"fixed output_points = {OUTPUT_POINTS}")
    print(f"reference case = {REFERENCE_NAME}")
    print()

    print("Production fit-time values")
    print("--------------------------")
    for row in report["case_results"]:
        print(
            f"{row['name']:<8} max_dt={row['maximum_dt_s']:.1e} | "
            f"{format_array(np.asarray(row['production_fit_values']))}"
        )
    print()

    print("Transition crossing times")
    print("-------------------------")
    header = f"{'case':<8}"
    for level in CROSSING_LEVELS:
        header += f"  f={level:.2f}".rjust(17)
    print(header)

    for row in report["case_results"]:
        line = f"{row['name']:<8}"
        for level in CROSSING_LEVELS:
            line += format_time(
                row["crossing_times_s"][f"{level:.2f}"]
            ).rjust(17)
        print(line)
    print()

    print("Successive crossing-time changes")
    print("--------------------------------")
    for change in report["successive_crossing_time_changes"]:
        print(
            f"{change['from_case']} -> {change['to_case']}"
        )
        for level in CROSSING_LEVELS:
            key = f"{level:.2f}"
            item = change["crossing_time_changes"][key]
            if item is None:
                print(f"  f={level:.2f}: unavailable")
            else:
                print(
                    f"  f={level:.2f}: "
                    f"delta_t={item['absolute_change_s']:+.6e} s, "
                    f"relative={item['relative_change_percent']:+.6e}%"
                )
    print()

    print("Pointwise drift versus dt1e-7")
    print("-----------------------------")
    print(
        f"{'case':<8} {'prod max|df|':>14} {'prod RMSE':>14} "
        f"{'trans max|df|':>15} {'trans RMSE':>14}"
    )
    for row in report["case_results"]:
        print(
            f"{row['name']:<8} "
            f"{row['production_max_abs_difference_vs_reference']:>14.6e} "
            f"{row['production_rmse_difference_vs_reference']:>14.6e} "
            f"{row['transition_max_abs_difference_vs_reference']:>15.6e} "
            f"{row['transition_rmse_difference_vs_reference']:>14.6e}"
        )
    print()

    print("Interpretation")
    print("--------------")
    print(
        "This run holds output_points fixed at 5001, so changes are driven "
        "primarily by maximum_dt_s rather than output-grid refinement."
    )
    print(
        "For the steep retention transition, crossing-time stabilization is "
        "the primary convergence diagnostic."
    )
    print(
        "No CALIBRATED claim is made; this is a numerical audit only."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the F4h2c2e fixed-output maximum-timestep convergence audit."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output path.",
    )
    args = parser.parse_args()

    report = run_audit()
    print_report(report)

    if args.output is not None:
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print()
        print(f"Wrote {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
