from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from ncmemsim.device_calibration import (
    DeviceCalibrationSpec,
    DeviceFitParameterBinding,
    DeviceFitTarget,
    apply_device_calibration_parameters,
)
from ncmemsim.device_objectives import interpolate_without_extrapolation
from ncmemsim.experimental import (
    DeviceObservableDataset,
    ExperimentalCondition,
    ExperimentalDatasetMetadata,
)
from ncmemsim.fitting import (
    FitParameter,
    FitParameterSet,
    LeastSquaresConfig,
)
from ncmemsim.physics import PhysicsModel
from ncmemsim.reference import make_v53_reference_device
from ncmemsim.retention import RetentionConfig
from ncmemsim.retention_fit import (
    RetentionFitProtocol,
    fit_single_parameter_retention_fraction,
    predict_retention_fraction,
)
from ncmemsim.simulator import SimulationConfig, Simulator
from ncmemsim.state import DeviceState


TRUE_PHI_ERASE_EV = 2.10
FIT_INITIAL_PHI_ERASE_EV = 2.00
LOWER_BOUND_EV = 1.80
UPPER_BOUND_EV = 2.40

RETENTION_GATE_VOLTAGE_V = -14.0
TOTAL_TIME_S = 3.0e-2
INITIAL_DT_S = 1.0e-7

FIT_TIMES_S = np.asarray(
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

REFERENCE_MAXIMUM_DT_S = 1.0e-7
REFERENCE_OUTPUT_POINTS = 5001

CANDIDATES = (
    ("A_dt1e-5_out321", 1.0e-5, 321),
    ("B_dt3e-6_out321", 3.0e-6, 321),
    ("C_dt1e-6_out161", 1.0e-6, 161),
    ("D_dt1e-6_out321", 1.0e-6, 321),
    ("E_dt1e-6_out641", 1.0e-6, 641),
)


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


def make_specification(
    *,
    initial_value: float,
) -> DeviceCalibrationSpec:
    parameter = FitParameter(
        name="phi_barrier_erase_eV",
        initial_value=initial_value,
        lower_bound=LOWER_BOUND_EV,
        upper_bound=UPPER_BOUND_EV,
        unit="eV",
        description=(
            "Synthetic effective erase-barrier "
            "practical-grid-selection parameter."
        ),
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
        name="f4h2c2e-practical-fit-grid-selection",
        notes=(
            "Pure-P2, -14 V accelerated fixed-bias synthetic retention "
            "benchmark. FITTED does not imply CALIBRATED."
        ),
    )


def make_protocol(
    *,
    maximum_dt_s: float,
    output_points: int,
) -> RetentionFitProtocol:
    return RetentionFitProtocol(
        RetentionConfig(
            gate_voltage_V=RETENTION_GATE_VOLTAGE_V,
            total_time_s=TOTAL_TIME_S,
            initial_dt_s=INITIAL_DT_S,
            maximum_dt_s=maximum_dt_s,
            output_points=output_points,
            stop_at_quasi_equilibrium=False,
            occupancy_integrator="backward_euler",
        )
    )


def strict_solver() -> LeastSquaresConfig:
    return LeastSquaresConfig(
        ftol=1.0e-12,
        xtol=1.0e-12,
        gtol=1.0e-12,
        max_nfev=200,
    )


def predict_at_phi(
    *,
    phi_erase_eV: float,
    maximum_dt_s: float,
    output_points: int,
) -> dict[str, Any]:
    device, physics, simulation_config = make_base_objects()
    specification = make_specification(
        initial_value=FIT_INITIAL_PHI_ERASE_EV,
    )

    context = apply_device_calibration_parameters(
        device,
        physics,
        simulation_config,
        specification,
        np.asarray([phi_erase_eV], dtype=float),
    )

    initial_state = make_pure_p2_state(context.device)
    protocol = make_protocol(
        maximum_dt_s=maximum_dt_s,
        output_points=output_points,
    )

    start = perf_counter()
    prediction = predict_retention_fraction(
        Simulator(
            context.device,
            context.physics,
            context.simulation_config,
        ),
        protocol,
        initial_state=initial_state,
    )
    runtime_s = perf_counter() - start

    values, interpolation_used = interpolate_without_extrapolation(
        FIT_TIMES_S,
        prediction.time_s,
        prediction.predicted_retention_fraction,
    )

    return {
        "protocol": protocol,
        "prediction": prediction,
        "values": np.asarray(values, dtype=float),
        "runtime_s": float(runtime_s),
        "interpolation_used": bool(interpolation_used),
    }


def make_reference_dataset(
    observed_values: np.ndarray,
) -> DeviceObservableDataset:
    return DeviceObservableDataset(
        independent_variable_name="time",
        independent_variable_unit="s",
        independent_values=FIT_TIMES_S,
        observable_name="total_charge_retention_fraction",
        observable_unit=None,
        observed_values=np.asarray(observed_values, dtype=float),
        metadata=ExperimentalDatasetMetadata(
            dataset_id=(
                "f4h2c2e-high-resolution-reference-retention"
            ),
            source=(
                "NCMemSim synthetic F4h2c2e practical "
                "fit-grid selection audit"
            ),
            sample_id="synthetic-v53",
            temperature_K=300.0,
            notes=(
                "Observed values generated with max_dt=1e-7 s and "
                "output_points=5001. Numerical reference only; "
                "not experimental calibration."
            ),
        ),
        conditions=(
            ExperimentalCondition(
                name="retention_gate_voltage",
                value=RETENTION_GATE_VOLTAGE_V,
                unit="V",
            ),
        ),
    )


def fit_candidate(
    dataset: DeviceObservableDataset,
    *,
    maximum_dt_s: float,
    output_points: int,
):
    device, physics, simulation_config = make_base_objects()
    specification = make_specification(
        initial_value=FIT_INITIAL_PHI_ERASE_EV,
    )
    initial_state = make_pure_p2_state(device)
    protocol = make_protocol(
        maximum_dt_s=maximum_dt_s,
        output_points=output_points,
    )

    start = perf_counter()
    result = fit_single_parameter_retention_fraction(
        dataset,
        base_device=device,
        base_physics=physics,
        base_simulation_config=simulation_config,
        calibration_spec=specification,
        protocol=protocol,
        initial_state=initial_state,
        least_squares_config=strict_solver(),
    )
    runtime_s = perf_counter() - start

    return result, float(runtime_s)


def protocol_dict(
    protocol: RetentionFitProtocol,
) -> dict[str, Any]:
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
    print(
        "Generating high-resolution numerical reference: "
        f"max_dt={REFERENCE_MAXIMUM_DT_S:.1e} s, "
        f"output_points={REFERENCE_OUTPUT_POINTS}"
    )

    reference = predict_at_phi(
        phi_erase_eV=TRUE_PHI_ERASE_EV,
        maximum_dt_s=REFERENCE_MAXIMUM_DT_S,
        output_points=REFERENCE_OUTPUT_POINTS,
    )
    reference_values = reference["values"]
    dataset = make_reference_dataset(reference_values)

    rows: list[dict[str, Any]] = []

    for name, maximum_dt_s, output_points in CANDIDATES:
        print(
            f"Evaluating {name}: "
            f"max_dt={maximum_dt_s:.1e} s, "
            f"output_points={output_points}"
        )

        fixed_phi_prediction = predict_at_phi(
            phi_erase_eV=TRUE_PHI_ERASE_EV,
            maximum_dt_s=maximum_dt_s,
            output_points=output_points,
        )

        discretization_difference = (
            fixed_phi_prediction["values"] - reference_values
        )

        fit_result, fit_runtime_s = fit_candidate(
            dataset,
            maximum_dt_s=maximum_dt_s,
            output_points=output_points,
        )

        fitted_phi = float(
            fit_result.fitted_parameter_values[
                "phi_barrier_erase_eV"
            ]
        )
        bias_eV = fitted_phi - TRUE_PHI_ERASE_EV
        bias_percent = (
            100.0 * bias_eV / TRUE_PHI_ERASE_EV
        )

        active_mask = int(
            np.asarray(
                fit_result.numerical_result.active_mask
            )[0]
        )

        rows.append(
            {
                "name": name,
                "protocol": protocol_dict(
                    fixed_phi_prediction["protocol"]
                ),
                "protocol_hash": (
                    fixed_phi_prediction["protocol"].protocol_hash()
                ),
                "fixed_truth_parameter_prediction": {
                    "values": fixed_phi_prediction["values"].tolist(),
                    "runtime_s": fixed_phi_prediction["runtime_s"],
                    "max_abs_difference_vs_reference": float(
                        np.max(
                            np.abs(discretization_difference)
                        )
                    ),
                    "rmse_difference_vs_reference": float(
                        np.sqrt(
                            np.mean(
                                discretization_difference**2
                            )
                        )
                    ),
                },
                "fit": {
                    "initial_phi_erase_eV": FIT_INITIAL_PHI_ERASE_EV,
                    "fitted_phi_erase_eV": fitted_phi,
                    "absolute_parameter_bias_eV": bias_eV,
                    "relative_parameter_bias_percent": bias_percent,
                    "objective_rmse": float(
                        fit_result.objective.root_mean_square_error
                    ),
                    "success": bool(
                        fit_result.numerical_result.success
                    ),
                    "nfev": int(
                        fit_result.numerical_result.nfev
                    ),
                    "active_mask": active_mask,
                    "runtime_s": fit_runtime_s,
                    "scientific_status": (
                        fit_result.scientific_status
                    ),
                    "dataset_hash": fit_result.dataset_hash,
                    "initial_state_hash": (
                        fit_result.prediction.initial_state_hash
                    ),
                },
            }
        )

    return {
        "schema_version": 1,
        "workflow": (
            "f4h2c2e-practical-retention-fit-grid-selection"
        ),
        "scientific_status": "NUMERICAL_REFINEMENT_AUDIT",
        "scientific_scope": (
            "Select a practical retention-fit discretization by fitting "
            "high-resolution synthetic reference data with cheaper candidate "
            "grids. Numerical audit only; not experimental calibration."
        ),
        "truth": {
            "initial_state": "pure-P2",
            "phi_barrier_erase_eV": TRUE_PHI_ERASE_EV,
            "retention_gate_voltage_V": RETENTION_GATE_VOLTAGE_V,
            "observable": "total_charge_retention_fraction",
            "fit_times_s": FIT_TIMES_S.tolist(),
        },
        "reference": {
            "maximum_dt_s": REFERENCE_MAXIMUM_DT_S,
            "output_points": REFERENCE_OUTPUT_POINTS,
            "retention_fraction_at_fit_times": reference_values.tolist(),
            "prediction_runtime_s": reference["runtime_s"],
            "protocol_hash": reference["protocol"].protocol_hash(),
            "dataset_hash": dataset.dataset_hash(),
        },
        "fit_bounds_eV": [LOWER_BOUND_EV, UPPER_BOUND_EV],
        "fit_initial_phi_erase_eV": FIT_INITIAL_PHI_ERASE_EV,
        "candidate_results": rows,
        "interpretation_policy": {
            "hard_pass_fail_threshold": None,
            "selection_rule": (
                "Prefer the cheapest candidate that shows small and stable "
                "parameter bias relative to finer candidates, acceptable "
                "objective residuals, and no active fit bound."
            ),
            "important": (
                "The high-resolution reference is numerical, not physical "
                "truth. A small cross-grid bias validates this benchmark's "
                "discretization choice, not experimental calibration."
            ),
        },
    }


def print_report(report: dict[str, Any]) -> None:
    print()
    print("F4h2c2e practical retention fit-grid selection")
    print("==============================================")
    print(
        "reference: "
        f"max_dt={report['reference']['maximum_dt_s']:.1e} s, "
        f"output_points={report['reference']['output_points']}"
    )
    print(
        "reference values = "
        + np.array2string(
            np.asarray(
                report["reference"][
                    "retention_fraction_at_fit_times"
                ]
            ),
            precision=12,
            separator=", ",
            max_line_width=200,
        )
    )
    print(
        "reference prediction runtime = "
        f"{report['reference']['prediction_runtime_s']:.3f} s"
    )
    print()

    print("Fixed-phi discretization drift")
    print("------------------------------")
    print(
        f"{'candidate':<20} "
        f"{'max|df|':>14} "
        f"{'RMSE(df)':>14} "
        f"{'pred sec':>10}"
    )
    for row in report["candidate_results"]:
        p = row["fixed_truth_parameter_prediction"]
        print(
            f"{row['name']:<20} "
            f"{p['max_abs_difference_vs_reference']:>14.6e} "
            f"{p['rmse_difference_vs_reference']:>14.6e} "
            f"{p['runtime_s']:>10.3f}"
        )
    print()

    print("Cross-grid fitted parameter bias")
    print("--------------------------------")
    print(
        f"{'candidate':<20} "
        f"{'fit phi [eV]':>16} "
        f"{'bias [eV]':>14} "
        f"{'bias [%]':>12} "
        f"{'fit RMSE':>14} "
        f"{'nfev':>6} "
        f"{'fit sec':>10} "
        f"{'mask':>6} "
        f"{'ok':>5}"
    )
    for row in report["candidate_results"]:
        fit = row["fit"]
        print(
            f"{row['name']:<20} "
            f"{fit['fitted_phi_erase_eV']:>16.12f} "
            f"{fit['absolute_parameter_bias_eV']:>14.6e} "
            f"{fit['relative_parameter_bias_percent']:>12.6e} "
            f"{fit['objective_rmse']:>14.6e} "
            f"{fit['nfev']:>6d} "
            f"{fit['runtime_s']:>10.3f} "
            f"{fit['active_mask']:>6d} "
            f"{str(fit['success']):>5}"
        )
    print()

    print("Interpretation")
    print("--------------")
    print(
        "Select the practical grid from the bias/runtime trade-off; "
        "do not choose solely from same-grid exact recovery."
    )
    print(
        "No hard convergence threshold is imposed in the script."
    )
    print(
        "Scientific status remains numerical audit / FITTED, "
        "never CALIBRATED."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the F4h2c2e practical cross-grid retention "
            "fit-discretization selection audit."
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
