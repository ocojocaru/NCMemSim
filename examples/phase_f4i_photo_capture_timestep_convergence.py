from __future__ import annotations

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
    fit_single_parameter_photo_capture_efficiency_vs_programming_time,
    predict_electro_optical_delta_vfb_vs_programming_time,
)


TRUE_ETA = 2.0e-7
BASE_ETA = 5.0e-8
PROGRAM_VOLTAGE_V = 2.0
READ_VOLTAGE_V = 0.0
WAVELENGTH_NM = 1550.0
POWER_DENSITY_W_M2 = 1000.0
OBSERVATION_UNCERTAINTY_V = 1.0e-10

PROGRAMMING_TIMES_S = np.asarray(
    [1.0e-4, 3.0e-4, 1.0e-3],
    dtype=float,
)

ETA_SWEEP = (
    0.0,
    1.0e-9,
    5.0e-8,
    1.0e-7,
    2.0e-7,
    5.0e-7,
    1.0e-6,
)

DT_SWEEP_S = (
    1.0e-5,
    5.0e-6,
    2.5e-6,
)


def build_device():
    device = DeviceBuilder.v1(
        n_fgs=1,
        nc_material=[make_gesn(0.08)],
        nc_diameter_nm=[5.0],
        active_fraction=[1.0],
        fg_thickness_nm=[15.0],
    )
    device.floating_gates()[0].grid_points = 7
    return device


def build_protocol(
    internal_dt_s: float,
) -> ElectroOpticalProgramTimeFitProtocol:
    return ElectroOpticalProgramTimeFitProtocol(
        program_voltage_V=PROGRAM_VOLTAGE_V,
        read_voltage_V=READ_VOLTAGE_V,
        program_internal_dt_s=internal_dt_s,
        light_source=LightSource.laser(
            wavelength_nm=WAVELENGTH_NM,
            power_density_W_m2=POWER_DENSITY_W_M2,
        ),
        photo_weights=PhotoTransitionWeights(
            r01=1.0,
            r12=1.0,
            r10=0.0,
            r21=0.0,
        ),
    )


def predict(
    *,
    eta: float,
    internal_dt_s: float,
) -> np.ndarray:
    simulator = Simulator(
        build_device(),
        PhysicsModel.default(),
        SimulationConfig(
            dwell_time_s=5.0e-3,
            internal_dt_s=internal_dt_s,
        ),
    )
    result = (
        predict_electro_optical_delta_vfb_vs_programming_time(
            simulator,
            PROGRAMMING_TIMES_S,
            build_protocol(internal_dt_s),
            photo_config=PhotoTransitionConfig(
                photo_capture_efficiency=eta,
            ),
        )
    )
    return np.asarray(
        result.predicted_delta_vfb_V,
        dtype=float,
    )


def eta_spec() -> DeviceCalibrationSpec:
    return DeviceCalibrationSpec(
        parameter_set=FitParameterSet(
            (
                FitParameter(
                    name="photo_capture_efficiency",
                    initial_value=BASE_ETA,
                    lower_bound=1.0e-9,
                    upper_bound=1.0e-6,
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
        name="f4i3-cross-grid-photo-capture-audit",
    )


def build_truth_dataset(
    *,
    truth_dt_s: float,
) -> DeviceObservableDataset:
    observed = predict(
        eta=TRUE_ETA,
        internal_dt_s=truth_dt_s,
    )

    return DeviceObservableDataset(
        independent_variable_name="programming_time",
        independent_variable_unit="s",
        independent_values=PROGRAMMING_TIMES_S,
        observable_name="delta_vfb",
        observable_unit="V",
        observed_values=observed,
        observed_uncertainty=np.full(
            PROGRAMMING_TIMES_S.size,
            OBSERVATION_UNCERTAINTY_V,
            dtype=float,
        ),
        metadata=ExperimentalDatasetMetadata(
            dataset_id="synthetic-f4i3-cross-grid-truth",
            source=(
                "NCMemSim synthetic refined-grid truth for "
                "F4i3 numerical audit"
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
                value=WAVELENGTH_NM,
                unit="nm",
            ),
            ExperimentalCondition(
                name="optical_power_density",
                value=POWER_DENSITY_W_M2,
                unit="W/m^2",
            ),
        ),
    )


def run_cross_grid_fit(
    *,
    truth_dt_s: float,
    fit_dt_s: float,
):
    dataset = build_truth_dataset(
        truth_dt_s=truth_dt_s,
    )

    result = (
        fit_single_parameter_photo_capture_efficiency_vs_programming_time(
            dataset,
            base_device=build_device(),
            base_physics=PhysicsModel.default(),
            base_simulation_config=SimulationConfig(
                dwell_time_s=5.0e-3,
                internal_dt_s=fit_dt_s,
            ),
            base_photo_config=PhotoTransitionConfig(
                photo_capture_efficiency=BASE_ETA,
            ),
            calibration_spec=eta_spec(),
            protocol=build_protocol(fit_dt_s),
            least_squares_config=LeastSquaresConfig(
                ftol=1.0e-12,
                xtol=1.0e-12,
                gtol=1.0e-12,
                max_nfev=1000,
            ),
        )
    )
    return dataset, result


def main() -> None:
    print("F4i3 numerical sensitivity audit")
    print("=" * 72)

    practical_dt = DT_SWEEP_S[0]

    print()
    print(f"ETA SWEEP (dt = {practical_dt:.3e} s)")
    print("-" * 72)
    zero_prediction = predict(
        eta=0.0,
        internal_dt_s=practical_dt,
    )

    for eta in ETA_SWEEP:
        values = predict(
            eta=eta,
            internal_dt_s=practical_dt,
        )
        signal = values - zero_prediction
        print(
            f"eta={eta:.3e}  "
            f"dVFB={np.array2string(values, precision=12)}  "
            f"photo_signal={np.array2string(signal, precision=12)}"
        )

    print()
    print(f"TIME-STEP CONVERGENCE (eta = {TRUE_ETA:.3e})")
    print("-" * 72)
    dt_predictions = {
        dt: predict(
            eta=TRUE_ETA,
            internal_dt_s=dt,
        )
        for dt in DT_SWEEP_S
    }
    reference_dt = DT_SWEEP_S[-1]
    reference = dt_predictions[reference_dt]

    for dt in DT_SWEEP_S:
        values = dt_predictions[dt]
        diff = values - reference
        max_abs = float(np.max(np.abs(diff)))
        rmse = float(np.sqrt(np.mean(diff * diff)))
        print(
            f"dt={dt:.3e}  "
            f"dVFB={np.array2string(values, precision=12)}  "
            f"max_abs_vs_{reference_dt:.1e}={max_abs:.12e} V  "
            f"rmse={rmse:.12e} V"
        )

    print()
    print("CROSS-GRID PARAMETER RECOVERY")
    print("-" * 72)
    truth_dt = reference_dt
    fit_dt = practical_dt
    dataset, result = run_cross_grid_fit(
        truth_dt_s=truth_dt,
        fit_dt_s=fit_dt,
    )

    fitted_eta = result.fitted_parameter_values[
        "photo_capture_efficiency"
    ]
    eta_bias = fitted_eta - TRUE_ETA
    relative_bias = eta_bias / TRUE_ETA

    residual = (
        result.prediction.predicted_delta_vfb_V
        - dataset.observed_values
    )
    max_abs_residual = float(
        np.max(np.abs(residual))
    )
    rmse_residual = float(
        np.sqrt(np.mean(residual * residual))
    )

    print(f"truth_dt_s              = {truth_dt:.12e}")
    print(f"fit_dt_s                = {fit_dt:.12e}")
    print(f"true_eta                = {TRUE_ETA:.12e}")
    print(f"fitted_eta              = {fitted_eta:.12e}")
    print(f"eta_bias                = {eta_bias:.12e}")
    print(f"relative_eta_bias       = {relative_bias:.12e}")
    print(f"relative_eta_bias_pct   = {100.0 * relative_bias:.9f}")
    print(f"max_abs_dVFB_residual_V = {max_abs_residual:.12e}")
    print(f"rmse_dVFB_residual_V    = {rmse_residual:.12e}")
    print(f"optimizer_success       = {result.numerical_result.success}")
    print(f"nfev                    = {result.numerical_result.nfev}")
    print(f"scientific_status       = {result.scientific_status}")

    print()
    print(
        "Interpretation: benchmark-specific numerical audit only; "
        "do not convert these values into universal timestep or "
        "calibration thresholds."
    )


if __name__ == "__main__":
    main()
