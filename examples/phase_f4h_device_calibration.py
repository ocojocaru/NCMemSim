from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from ncmemsim.device_calibration import (
    DeviceCalibrationSpec,
    DeviceFitParameterBinding,
    DeviceFitTarget,
    apply_device_calibration_parameters,
)
from ncmemsim.device_fit import (
    CVCalibrationProtocol,
    fit_single_parameter_cv_dataset,
)
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
from ncmemsim.paired_pulse_protocol import (
    PairedPulseMemoryProtocol,
    run_paired_pulse_memory_protocol,
)
from ncmemsim.physics import PhysicsModel
from ncmemsim.program_fit import (
    ProgramTimeFitProtocol,
    fit_single_parameter_delta_vfb_vs_programming_time,
    predict_delta_vfb_vs_programming_time,
)
from ncmemsim.reference import make_v53_reference_device
from ncmemsim.retention import RetentionConfig
from ncmemsim.retention_fit import (
    RetentionFitProtocol,
    fit_single_parameter_retention_fraction,
    predict_retention_fraction,
)
from ncmemsim.simulator import SimulationConfig, Simulator
from ncmemsim.state import DeviceState


TRUE_QFIX_C_M2 = 1.2e-3
TRUE_NU0_HZ = 2.0e12
TRUE_PHI_ERASE_EV = 2.10
RETENTION_GATE_VOLTAGE_V = -14.0
RETENTION_TIMES_S = np.asarray(
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


def strict_solver() -> LeastSquaresConfig:
    return LeastSquaresConfig(
        ftol=1.0e-12,
        xtol=1.0e-12,
        gtol=1.0e-12,
        max_nfev=1000,
    )


def make_base_objects(*, dwell_time_s: float):
    return (
        make_v53_reference_device(grid_points=7),
        PhysicsModel.default(),
        SimulationConfig(
            dwell_time_s=dwell_time_s,
            internal_dt_s=1.0e-5,
            qfix_C_m2=0.0,
            qit_C_m2=0.0,
        ),
    )


def run_cv_recovery():
    device, physics, config = make_base_objects(
        dwell_time_s=0.0
    )
    protocol = CVCalibrationProtocol(
        vmin_V=-2.0,
        vmax_V=2.0,
        points=31,
    )

    truth_config = replace(
        config,
        qfix_C_m2=TRUE_QFIX_C_M2,
    )
    truth_cv = Simulator(
        device,
        physics,
        truth_config,
    ).simulate_cv(
        vmin_V=protocol.vmin_V,
        vmax_V=protocol.vmax_V,
        points=protocol.points,
    )

    dataset = DeviceObservableDataset(
        independent_variable_name="gate_voltage",
        independent_variable_unit="V",
        independent_values=np.asarray(
            truth_cv.forward.voltages_V,
            dtype=float,
        ),
        observable_name="capacitance",
        observable_unit="F/m^2",
        observed_values=np.asarray(
            truth_cv.forward.capacitance_F_m2,
            dtype=float,
        ),
        metadata=ExperimentalDatasetMetadata(
            dataset_id="example-synthetic-cv-qfix",
            source="NCMemSim synthetic F4h device-calibration example",
            sample_id="synthetic-v53",
            temperature_K=300.0,
        ),
        conditions=(
            ExperimentalCondition(
                name="sweep_direction",
                value="forward",
            ),
        ),
    )

    parameter = FitParameter(
        name="qfix_C_m2",
        initial_value=0.0,
        lower_bound=-3.0e-3,
        upper_bound=3.0e-3,
        unit="C/m^2",
        description="Synthetic fixed-charge recovery parameter.",
    )
    specification = DeviceCalibrationSpec(
        parameter_set=FitParameterSet(
            (parameter,)
        ),
        bindings=(
            DeviceFitParameterBinding(
                parameter_name="qfix_C_m2",
                target=(
                    DeviceFitTarget
                    .SIMULATION_QFIX_C_M2
                ),
            ),
        ),
        name="example-cv-qfix-recovery",
    )

    return fit_single_parameter_cv_dataset(
        dataset,
        base_device=device,
        base_physics=physics,
        base_simulation_config=config,
        calibration_spec=specification,
        protocol=protocol,
        least_squares_config=strict_solver(),
    )


def run_program_time_recovery():
    times_s = np.asarray(
        [1.0e-4, 3.0e-4, 1.0e-3],
        dtype=float,
    )
    protocol = ProgramTimeFitProtocol(
        program_voltage_V=3.0,
        read_voltage_V=0.0,
        program_internal_dt_s=1.0e-5,
    )

    truth_device, truth_physics, truth_config = (
        make_base_objects(dwell_time_s=5.0e-3)
    )
    truth_physics.occupancy.config = replace(
        truth_physics.occupancy.config,
        nu0_Hz=TRUE_NU0_HZ,
    )

    truth_prediction = (
        predict_delta_vfb_vs_programming_time(
            Simulator(
                truth_device,
                truth_physics,
                truth_config,
            ),
            times_s,
            protocol,
        )
    )

    dataset = DeviceObservableDataset(
        independent_variable_name="programming_time",
        independent_variable_unit="s",
        independent_values=times_s,
        observable_name="delta_vfb",
        observable_unit="V",
        observed_values=(
            truth_prediction.predicted_delta_vfb_V
        ),
        metadata=ExperimentalDatasetMetadata(
            dataset_id="example-synthetic-delta-vfb-time",
            source="NCMemSim synthetic F4h device-calibration example",
            sample_id="synthetic-v53",
            temperature_K=300.0,
        ),
        conditions=(
            ExperimentalCondition(
                name="program_voltage",
                value=3.0,
                unit="V",
            ),
            ExperimentalCondition(
                name="read_voltage",
                value=0.0,
                unit="V",
            ),
        ),
    )

    parameter = FitParameter(
        name="nu0_Hz",
        initial_value=5.0e11,
        lower_bound=1.0e11,
        upper_bound=5.0e12,
        unit="Hz",
        description=(
            "Synthetic program-injection attempt-frequency "
            "recovery parameter."
        ),
    )
    specification = DeviceCalibrationSpec(
        parameter_set=FitParameterSet(
            (parameter,)
        ),
        bindings=(
            DeviceFitParameterBinding(
                parameter_name="nu0_Hz",
                target=DeviceFitTarget.KINETICS_NU0_HZ,
            ),
        ),
        name="example-delta-vfb-time-nu0-recovery",
    )

    device, physics, config = make_base_objects(
        dwell_time_s=5.0e-3
    )

    return (
        fit_single_parameter_delta_vfb_vs_programming_time(
            dataset,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=specification,
            protocol=protocol,
            least_squares_config=strict_solver(),
        )
    )


def make_partially_occupied_reference(device):
    state = DeviceState.empty_for_device(device)

    for fg_state in state.floating_gates:
        fg_state.P0[:] = 0.5
        fg_state.P1[:] = 0.5
        fg_state.P2[:] = 0.0

    state.validate(device)
    return state


def run_paired_pulse_window():
    device, physics, config = make_base_objects(
        dwell_time_s=5.0e-3
    )
    simulator = Simulator(
        device,
        physics,
        config,
    )
    reference = make_partially_occupied_reference(
        device
    )
    protocol = PairedPulseMemoryProtocol(
        program_voltage_V=3.0,
        program_time_s=1.0e-3,
        erase_voltage_V=-3.0,
        erase_time_s=1.0e-3,
        read_voltage_V=0.0,
        pulse_internal_dt_s=1.0e-5,
    )

    return run_paired_pulse_memory_protocol(
        simulator,
        protocol,
        reference_state=reference,
    )



def make_pure_p2_state(device):
    """Return the controlled synthetic retention initial condition."""

    state = DeviceState.empty_for_device(device)

    for fg_state in state.floating_gates:
        fg_state.P0[:] = 0.0
        fg_state.P1[:] = 0.0
        fg_state.P2[:] = 1.0

    state.validate(device)
    return state


def retention_protocol() -> RetentionFitProtocol:
    return RetentionFitProtocol(
        RetentionConfig(
            gate_voltage_V=RETENTION_GATE_VOLTAGE_V,
            total_time_s=3.0e-2,
            initial_dt_s=1.0e-7,
            maximum_dt_s=1.0e-3,
            output_points=81,
            occupancy_integrator="backward_euler",
        )
    )


def erase_barrier_specification(
    *,
    initial_value: float,
) -> DeviceCalibrationSpec:
    parameter = FitParameter(
        name="phi_barrier_erase_eV",
        initial_value=initial_value,
        lower_bound=1.80,
        upper_bound=2.40,
        unit="eV",
        description=(
            "Synthetic effective erase-barrier recovery parameter."
        ),
    )

    return DeviceCalibrationSpec(
        parameter_set=FitParameterSet((parameter,)),
        bindings=(
            DeviceFitParameterBinding(
                parameter_name="phi_barrier_erase_eV",
                target=(
                    DeviceFitTarget.FG_PHI_BARRIER_ERASE_EV
                ),
                fg_index=0,
            ),
        ),
        name="example-retention-erase-barrier-recovery",
        notes=(
            "Single-parameter synthetic fixed-bias retention benchmark; "
            "the fitted barrier remains an effective parameter."
        ),
    )


def run_retention_recovery():
    protocol = retention_protocol()

    truth_device, truth_physics, truth_config = (
        make_base_objects(dwell_time_s=5.0e-3)
    )

    truth_specification = erase_barrier_specification(
        initial_value=1.90,
    )
    truth_context = apply_device_calibration_parameters(
        truth_device,
        truth_physics,
        truth_config,
        truth_specification,
        np.asarray([TRUE_PHI_ERASE_EV], dtype=float),
    )

    truth_initial_state = make_pure_p2_state(
        truth_context.device
    )
    truth_prediction = predict_retention_fraction(
        Simulator(
            truth_context.device,
            truth_context.physics,
            truth_context.simulation_config,
        ),
        protocol,
        initial_state=truth_initial_state,
    )

    observed = np.interp(
        RETENTION_TIMES_S,
        truth_prediction.time_s,
        truth_prediction.predicted_retention_fraction,
    )

    dataset = DeviceObservableDataset(
        independent_variable_name="time",
        independent_variable_unit="s",
        independent_values=RETENTION_TIMES_S,
        observable_name="total_charge_retention_fraction",
        observable_unit=None,
        observed_values=observed,
        metadata=ExperimentalDatasetMetadata(
            dataset_id="example-synthetic-retention-erase-barrier",
            source=(
                "NCMemSim synthetic F4h2c2 retention-fitting example"
            ),
            sample_id="synthetic-v53",
            temperature_K=300.0,
            notes=(
                "Controlled accelerated fixed-bias synthetic benchmark; "
                "not an experimental zero-bias retention dataset."
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

    device, physics, config = make_base_objects(
        dwell_time_s=5.0e-3
    )
    initial_state = make_pure_p2_state(device)

    return fit_single_parameter_retention_fraction(
        dataset,
        base_device=device,
        base_physics=physics,
        base_simulation_config=config,
        calibration_spec=erase_barrier_specification(
            initial_value=1.90,
        ),
        protocol=protocol,
        initial_state=initial_state,
        least_squares_config=strict_solver(),
    )

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the NCMemSim F4h synthetic device-level "
            "calibration and pulse-protocol example."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output path.",
    )
    args = parser.parse_args()

    cv_result = run_cv_recovery()
    time_result = run_program_time_recovery()
    paired_result = run_paired_pulse_window()
    retention_result = run_retention_recovery()

    fitted_qfix = (
        cv_result.fitted_parameter_values["qfix_C_m2"]
    )
    fitted_nu0 = (
        time_result.fitted_parameter_values["nu0_Hz"]
    )
    fitted_phi_erase = (
        retention_result.fitted_parameter_values[
            "phi_barrier_erase_eV"
        ]
    )

    print("F4h synthetic device-level workflows")
    print("------------------------------------")
    print(
        "C-V qfix recovery: "
        f"truth={TRUE_QFIX_C_M2:.6e} C/m^2, "
        f"fit={fitted_qfix:.6e} C/m^2, "
        f"status={cv_result.scientific_status}"
    )
    print(
        "Delta-VFB(tprog) nu0 recovery: "
        f"truth={TRUE_NU0_HZ:.6e} Hz, "
        f"fit={fitted_nu0:.6e} Hz, "
        f"status={time_result.scientific_status}"
    )
    print(
        "Paired pulse memory window: "
        f"signed={paired_result.memory_window_V:.6e} V, "
        "magnitude="
        f"{paired_result.memory_window_magnitude_V:.6e} V"
    )
    print(
        "Retention phi_erase recovery: "
        f"truth={TRUE_PHI_ERASE_EV:.6f} eV, "
        f"fit={fitted_phi_erase:.6f} eV, "
        f"Vret={RETENTION_GATE_VOLTAGE_V:.1f} V, "
        f"status={retention_result.scientific_status}"
    )
    print(
        "Scientific conclusion: synthetic parameter recovery "
        "demonstrated; no experimental CALIBRATED claim."
    )

    payload = {
        "schema_version": 1,
        "workflow": "phase-f4h-device-calibration-example",
        "scientific_scope": (
            "synthetic validation and protocol semantics"
        ),
        "scientific_conclusion": "FITTED_NOT_CALIBRATED",
        "cv_qfix_truth_C_m2": TRUE_QFIX_C_M2,
        "program_time_nu0_truth_Hz": TRUE_NU0_HZ,
        "retention_phi_erase_truth_eV": TRUE_PHI_ERASE_EV,
        "retention_gate_voltage_V": RETENTION_GATE_VOLTAGE_V,
        "cv_fit": cv_result.to_dict(),
        "program_time_fit": time_result.to_dict(),
        "paired_pulse_memory": paired_result.to_dict(),
        "retention_fit": retention_result.to_dict(),
    }

    if args.output is not None:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
