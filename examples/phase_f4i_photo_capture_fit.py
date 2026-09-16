from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from ncmemsim import (
    DeviceBuilder,
    PhysicsModel,
    SimulationConfig,
    Simulator,
    make_gesn,
)
from ncmemsim.device_calibration import (
    DeviceCalibrationSpec,
    DeviceFitParameterBinding,
    DeviceFitTarget,
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
from ncmemsim.optics import LightSource
from ncmemsim.photo import (
    PhotoTransitionConfig,
    PhotoTransitionWeights,
)
from ncmemsim.photo_program_fit import (
    ElectroOpticalProgramTimeFitProtocol,
    fit_single_parameter_photo_capture_efficiency_multi_condition,
    predict_electro_optical_delta_vfb_vs_programming_time,
)


TRUE_ETA = 2.0e-7
BASE_ETA = 5.0e-8
PROGRAM_VOLTAGE_V = 2.0
READ_VOLTAGE_V = 0.0
INTERNAL_DT_S = 1.0e-5
OBSERVATION_UNCERTAINTY_V = 1.0e-10

PROGRAMMING_TIMES_S = np.asarray(
    [1.0e-4, 3.0e-4, 1.0e-3],
    dtype=float,
)

OPTICAL_CONDITIONS = (
    (1550.0, 500.0),
    (1550.0, 1000.0),
    (1300.0, 1000.0),
)


def build_base_objects():
    device = DeviceBuilder.v1(
        n_fgs=1,
        nc_material=[make_gesn(0.08)],
        nc_diameter_nm=[5.0],
        active_fraction=[1.0],
        fg_thickness_nm=[15.0],
    )
    device.floating_gates()[0].grid_points = 7

    physics = PhysicsModel.default()
    simulation_config = SimulationConfig(
        dwell_time_s=5.0e-3,
        internal_dt_s=INTERNAL_DT_S,
    )
    photo_config = PhotoTransitionConfig(
        photo_capture_efficiency=BASE_ETA,
    )
    return device, physics, simulation_config, photo_config


def build_protocol(
    wavelength_nm: float,
    power_density_W_m2: float,
) -> ElectroOpticalProgramTimeFitProtocol:
    return ElectroOpticalProgramTimeFitProtocol(
        program_voltage_V=PROGRAM_VOLTAGE_V,
        read_voltage_V=READ_VOLTAGE_V,
        program_internal_dt_s=INTERNAL_DT_S,
        light_source=LightSource.laser(
            wavelength_nm=wavelength_nm,
            power_density_W_m2=power_density_W_m2,
        ),
        photo_weights=PhotoTransitionWeights(
            r01=1.0,
            r12=1.0,
            r10=0.0,
            r21=0.0,
        ),
    )


def build_synthetic_dataset(
    *,
    wavelength_nm: float,
    power_density_W_m2: float,
    dataset_id: str,
) -> DeviceObservableDataset:
    device, physics, simulation_config, _ = build_base_objects()
    protocol = build_protocol(
        wavelength_nm,
        power_density_W_m2,
    )

    prediction = (
        predict_electro_optical_delta_vfb_vs_programming_time(
            Simulator(
                device,
                physics,
                simulation_config,
            ),
            PROGRAMMING_TIMES_S,
            protocol,
            photo_config=PhotoTransitionConfig(
                photo_capture_efficiency=TRUE_ETA,
            ),
        )
    )

    return DeviceObservableDataset(
        independent_variable_name="programming_time",
        independent_variable_unit="s",
        independent_values=PROGRAMMING_TIMES_S,
        observable_name="delta_vfb",
        observable_unit="V",
        observed_values=prediction.predicted_delta_vfb_V,
        observed_uncertainty=np.full(
            PROGRAMMING_TIMES_S.size,
            OBSERVATION_UNCERTAINTY_V,
            dtype=float,
        ),
        metadata=ExperimentalDatasetMetadata(
            dataset_id=dataset_id,
            source=(
                "NCMemSim synthetic F4i4 multi-condition "
                "photo-capture example"
            ),
            sample_id="synthetic-gesn-photo",
            temperature_K=300.0,
        ),
        conditions=(
            ExperimentalCondition(
                name="program_voltage",
                value=PROGRAM_VOLTAGE_V,
                unit="V",
            ),
            ExperimentalCondition(
                name="read_voltage",
                value=READ_VOLTAGE_V,
                unit="V",
            ),
            ExperimentalCondition(
                name="wavelength",
                value=wavelength_nm,
                unit="nm",
            ),
            ExperimentalCondition(
                name="optical_power_density",
                value=power_density_W_m2,
                unit="W/m^2",
            ),
        ),
    )


def build_calibration_spec() -> DeviceCalibrationSpec:
    return DeviceCalibrationSpec(
        parameter_set=FitParameterSet(
            (
                FitParameter(
                    name="photo_capture_efficiency",
                    initial_value=BASE_ETA,
                    lower_bound=1.0e-9,
                    upper_bound=1.0e-6,
                    description=(
                        "Effective absorbed-photon to useful "
                        "occupancy-transition probability."
                    ),
                ),
            )
        ),
        bindings=(
            DeviceFitParameterBinding(
                parameter_name="photo_capture_efficiency",
                target=(
                    DeviceFitTarget.PHOTO_CAPTURE_EFFICIENCY
                ),
            ),
        ),
        name="f4i4-photo-capture-multi-condition-example",
    )


def run_example():
    datasets = tuple(
        build_synthetic_dataset(
            wavelength_nm=wavelength_nm,
            power_density_W_m2=power_density_W_m2,
            dataset_id=f"synthetic-photo-condition-{index}",
        )
        for index, (
            wavelength_nm,
            power_density_W_m2,
        ) in enumerate(
            OPTICAL_CONDITIONS,
            start=1,
        )
    )
    protocols = tuple(
        build_protocol(
            wavelength_nm,
            power_density_W_m2,
        )
        for wavelength_nm, power_density_W_m2
        in OPTICAL_CONDITIONS
    )

    (
        base_device,
        base_physics,
        base_simulation_config,
        base_photo_config,
    ) = build_base_objects()

    result = (
        fit_single_parameter_photo_capture_efficiency_multi_condition(
            datasets,
            protocols,
            base_device=base_device,
            base_physics=base_physics,
            base_simulation_config=base_simulation_config,
            base_photo_config=base_photo_config,
            calibration_spec=build_calibration_spec(),
            least_squares_config=LeastSquaresConfig(
                ftol=1.0e-12,
                xtol=1.0e-12,
                gtol=1.0e-12,
                max_nfev=1000,
            ),
        )
    )

    fitted_eta = result.fitted_parameter_values[
        "photo_capture_efficiency"
    ]
    diagnostics = result.uncertainty_diagnostics

    summary = {
        "workflow": (
            "synthetic shared photo-capture-efficiency "
            "multi-condition recovery"
        ),
        "scientific_status": result.scientific_status,
        "true_photo_capture_efficiency": TRUE_ETA,
        "initial_photo_capture_efficiency": BASE_ETA,
        "fitted_photo_capture_efficiency": fitted_eta,
        "relative_parameter_error": (
            (fitted_eta - TRUE_ETA) / TRUE_ETA
        ),
        "n_conditions": result.n_conditions,
        "n_observations": result.n_observations,
        "locally_identifiable": (
            diagnostics.locally_identifiable
        ),
        "identifiability_scope": (
            "local-linearized-conditional-on-fixed-optical-model"
        ),
        "jacobian_rank": diagnostics.jacobian_rank,
        "scaled_condition_number": (
            diagnostics.scaled_condition_number
        ),
        "covariance_available": (
            diagnostics.covariance_available
        ),
        "parameter_standard_errors": (
            diagnostics.parameter_standard_errors
        ),
        "condition_scaled_jacobian_l2_norms": list(
            result.condition_scaled_jacobian_l2_norms
        ),
        "joint_root_mean_square_error_V": (
            result.joint_root_mean_square_error_V
        ),
        "scientific_conclusion": "FITTED_NOT_CALIBRATED",
    }

    return result, summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the F4i4 synthetic multi-condition "
            "photo-capture fitting example."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Optional JSON output path containing the compact "
            "summary and full serialized fit result."
        ),
    )
    args = parser.parse_args()

    result, summary = run_example()

    print("NCMemSim F4i4 photo-capture multi-condition example")
    print("--------------------------------------------------")
    print(f"scientific status: {summary['scientific_status']}")
    print(
        "true eta_photo:      "
        f"{summary['true_photo_capture_efficiency']:.12e}"
    )
    print(
        "fitted eta_photo:    "
        f"{summary['fitted_photo_capture_efficiency']:.12e}"
    )
    print(
        "relative error:      "
        f"{summary['relative_parameter_error']:.6e}"
    )
    print(
        "local identifiable:  "
        f"{summary['locally_identifiable']}"
    )
    print(
        "jacobian rank:       "
        f"{summary['jacobian_rank']}"
    )
    print(
        "scaled cond. number: "
        f"{summary['scaled_condition_number']:.6g}"
    )
    print(
        "condition sensitivities: "
        f"{summary['condition_scaled_jacobian_l2_norms']}"
    )
    print(
        "scientific conclusion: "
        f"{summary['scientific_conclusion']}"
    )

    if args.output is not None:
        payload = {
            "summary": summary,
            "fit_result": result.to_dict(),
        }
        args.output.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            )
            + "\\n",
            encoding="utf-8",
        )
        print(f"wrote: {args.output}")


if __name__ == "__main__":
    main()
