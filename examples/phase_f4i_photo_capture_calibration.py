from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from ncmemsim import DeviceBuilder, PhysicsModel, SimulationConfig, Simulator, make_gesn
from ncmemsim.calibration import CalibrationCriteria
from ncmemsim.device_calibration import DeviceCalibrationSpec, DeviceFitParameterBinding, DeviceFitTarget
from ncmemsim.experimental import DeviceObservableDataset, ExperimentalCondition, ExperimentalDatasetMetadata
from ncmemsim.fitting import FitParameter, FitParameterSet, LeastSquaresConfig
from ncmemsim.optics import LightSource
from ncmemsim.photo import PhotoTransitionConfig, PhotoTransitionWeights
from ncmemsim.photo_calibration import qualify_photo_capture_efficiency_fit
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
PROGRAMMING_TIMES_S = np.asarray([1.0e-4, 3.0e-4, 1.0e-3], dtype=float)
TRAINING_CONDITIONS = ((1550.0, 500.0), (1550.0, 1000.0), (1300.0, 1000.0))
VALIDATION_CONDITION = (1450.0, 750.0)


def build_base_objects():
    device = DeviceBuilder.v1(
        n_fgs=1,
        nc_material=[make_gesn(0.08)],
        nc_diameter_nm=[5.0],
        active_fraction=[1.0],
        fg_thickness_nm=[15.0],
    )
    device.floating_gates()[0].grid_points = 7
    return (
        device,
        PhysicsModel.default(),
        SimulationConfig(dwell_time_s=5.0e-3, internal_dt_s=INTERNAL_DT_S),
        PhotoTransitionConfig(photo_capture_efficiency=BASE_ETA),
    )


def build_protocol(wavelength_nm: float, power_density_W_m2: float):
    return ElectroOpticalProgramTimeFitProtocol(
        program_voltage_V=PROGRAM_VOLTAGE_V,
        read_voltage_V=READ_VOLTAGE_V,
        program_internal_dt_s=INTERNAL_DT_S,
        light_source=LightSource.laser(
            wavelength_nm=wavelength_nm,
            power_density_W_m2=power_density_W_m2,
        ),
        photo_weights=PhotoTransitionWeights(r01=1.0, r12=1.0, r10=0.0, r21=0.0),
    )


def build_synthetic_dataset(*, wavelength_nm: float, power_density_W_m2: float, dataset_id: str, observed_scale: float = 1.0):
    device, physics, simulation_config, _ = build_base_objects()
    protocol = build_protocol(wavelength_nm, power_density_W_m2)
    prediction = predict_electro_optical_delta_vfb_vs_programming_time(
        Simulator(device, physics, simulation_config),
        PROGRAMMING_TIMES_S,
        protocol,
        photo_config=PhotoTransitionConfig(photo_capture_efficiency=TRUE_ETA),
    )
    return DeviceObservableDataset(
        independent_variable_name='programming_time',
        independent_variable_unit='s',
        independent_values=PROGRAMMING_TIMES_S,
        observable_name='delta_vfb',
        observable_unit='V',
        observed_values=observed_scale * prediction.predicted_delta_vfb_V,
        observed_uncertainty=np.full(PROGRAMMING_TIMES_S.size, OBSERVATION_UNCERTAINTY_V, dtype=float),
        metadata=ExperimentalDatasetMetadata(
            dataset_id=dataset_id,
            source='NCMemSim synthetic F4i5 software-validation example; not an experimental calibration dataset',
            sample_id='synthetic-gesn-photo',
            temperature_K=300.0,
        ),
        conditions=(
            ExperimentalCondition(name='program_voltage', value=PROGRAM_VOLTAGE_V, unit='V'),
            ExperimentalCondition(name='read_voltage', value=READ_VOLTAGE_V, unit='V'),
            ExperimentalCondition(name='wavelength', value=wavelength_nm, unit='nm'),
            ExperimentalCondition(name='optical_power_density', value=power_density_W_m2, unit='W/m^2'),
        ),
    )


def build_calibration_spec():
    return DeviceCalibrationSpec(
        parameter_set=FitParameterSet((FitParameter(name='photo_capture_efficiency', initial_value=BASE_ETA, lower_bound=1.0e-9, upper_bound=1.0e-6),)),
        bindings=(DeviceFitParameterBinding(parameter_name='photo_capture_efficiency', target=DeviceFitTarget.PHOTO_CAPTURE_EFFICIENCY),),
        name='f4i5-photo-capture-calibration-example',
    )


def fit_training_conditions():
    datasets = tuple(
        build_synthetic_dataset(wavelength_nm=wavelength_nm, power_density_W_m2=power_density_W_m2, dataset_id=f'f4i5-training-{index}')
        for index, (wavelength_nm, power_density_W_m2) in enumerate(TRAINING_CONDITIONS, start=1)
    )
    protocols = tuple(build_protocol(wavelength_nm, power_density_W_m2) for wavelength_nm, power_density_W_m2 in TRAINING_CONDITIONS)
    device, physics, config, photo = build_base_objects()
    return fit_single_parameter_photo_capture_efficiency_multi_condition(
        datasets,
        protocols,
        base_device=device,
        base_physics=physics,
        base_simulation_config=config,
        base_photo_config=photo,
        calibration_spec=build_calibration_spec(),
        least_squares_config=LeastSquaresConfig(ftol=1.0e-12, xtol=1.0e-12, gtol=1.0e-12, max_nfev=1000),
    )


def qualification_criteria():
    return CalibrationCriteria(max_validation_rmse=1.0e-10, max_scaled_condition_number=1.01)


def run_example():
    fit_result = fit_training_conditions()
    wavelength_nm, power_density_W_m2 = VALIDATION_CONDITION
    protocol = build_protocol(wavelength_nm, power_density_W_m2)
    compatible = build_synthetic_dataset(wavelength_nm=wavelength_nm, power_density_W_m2=power_density_W_m2, dataset_id='f4i5-compatible-validation')
    incompatible = build_synthetic_dataset(wavelength_nm=wavelength_nm, power_density_W_m2=power_density_W_m2, dataset_id='f4i5-incompatible-validation', observed_scale=1.20)
    passing = qualify_photo_capture_efficiency_fit(fit_result, compatible, protocol, criteria=qualification_criteria())
    failing = qualify_photo_capture_efficiency_fit(fit_result, incompatible, protocol, criteria=qualification_criteria())
    fitted_eta = fit_result.fitted_parameter_values['photo_capture_efficiency']
    summary = {
        'workflow_scope': 'SYNTHETIC_SOFTWARE_VALIDATION',
        'experimental_calibration_claim': False,
        'training_scientific_status': fit_result.scientific_status,
        'true_photo_capture_efficiency': TRUE_ETA,
        'fitted_photo_capture_efficiency': fitted_eta,
        'compatible_validation': {
            'scientific_status': passing.scientific_status,
            'calibrated': passing.calibrated,
            'validation_rmse_V': passing.qualification.validation_objective.root_mean_square_error,
            'failed_criteria': list(passing.failed_criteria),
        },
        'incompatible_validation': {
            'scientific_status': failing.scientific_status,
            'calibrated': failing.calibrated,
            'validation_rmse_V': failing.qualification.validation_objective.root_mean_square_error,
            'failed_criteria': list(failing.failed_criteria),
        },
        'interpretation': 'These synthetic cases validate the software qualification mechanism. They do not establish an experimentally calibrated physical eta_photo value.',
    }
    return fit_result, passing, failing, summary


def main() -> None:
    parser = argparse.ArgumentParser(description='Run the F4i5 synthetic photo-capture calibration qualification example.')
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args()
    fit_result, passing, failing, summary = run_example()
    print('NCMemSim F4i5 photo-capture calibration qualification')
    print('-----------------------------------------------------')
    print(f"workflow scope:        {summary['workflow_scope']}")
    print(f"training status:       {summary['training_scientific_status']}")
    print(f"fitted eta_photo:      {summary['fitted_photo_capture_efficiency']:.12e}")
    print()
    print('compatible synthetic validation')
    print(f"  status:              {summary['compatible_validation']['scientific_status']}")
    print(f"  RMSE [V]:            {summary['compatible_validation']['validation_rmse_V']:.12e}")
    print(f"  failed criteria:     {summary['compatible_validation']['failed_criteria']}")
    print()
    print('incompatible synthetic validation')
    print(f"  status:              {summary['incompatible_validation']['scientific_status']}")
    print(f"  RMSE [V]:            {summary['incompatible_validation']['validation_rmse_V']:.12e}")
    print(f"  failed criteria:     {summary['incompatible_validation']['failed_criteria']}")
    print()
    print(f"experimental calibration claim: {summary['experimental_calibration_claim']}")
    print(summary['interpretation'])
    if args.output is not None:
        payload = {
            'summary': summary,
            'training_fit': fit_result.to_dict(),
            'compatible_qualification': passing.to_dict(),
            'incompatible_qualification': failing.to_dict(),
        }
        args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        print(f'wrote: {args.output}')


if __name__ == '__main__':
    main()
