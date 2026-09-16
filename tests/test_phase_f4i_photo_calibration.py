from __future__ import annotations

import copy

import numpy as np
import pytest

pytest.importorskip("scipy.optimize")

from ncmemsim import (
    DeviceBuilder,
    PhysicsModel,
    SimulationConfig,
    Simulator,
    make_gesn,
)
from ncmemsim.calibration import CalibrationCriteria
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
from ncmemsim.photo_calibration import (
    CalibratedPhotoCaptureEfficiency,
    DevicePhotoCalibrationResult,
    qualify_photo_capture_efficiency_fit,
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
UNCERTAINTY_V = 1.0e-10

PROGRAMMING_TIMES_S = np.asarray(
    [1.0e-4, 3.0e-4, 1.0e-3],
    dtype=float,
)

TRAINING_CONDITIONS = (
    (1550.0, 500.0),
    (1550.0, 1000.0),
    (1300.0, 1000.0),
)

VALIDATION_CONDITION = (1450.0, 750.0)


def _base_objects():
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
        SimulationConfig(
            dwell_time_s=5.0e-3,
            internal_dt_s=INTERNAL_DT_S,
        ),
        PhotoTransitionConfig(
            photo_capture_efficiency=BASE_ETA,
        ),
    )


def _protocol(
    wavelength_nm: float,
    power_density_W_m2: float,
    *,
    program_voltage_V: float = PROGRAM_VOLTAGE_V,
):
    return ElectroOpticalProgramTimeFitProtocol(
        program_voltage_V=program_voltage_V,
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


def _dataset(
    wavelength_nm: float,
    power_density_W_m2: float,
    *,
    dataset_id: str,
    scale: float = 1.0,
    program_voltage_V: float = PROGRAM_VOLTAGE_V,
):
    device, physics, config, _ = _base_objects()
    protocol = _protocol(
        wavelength_nm,
        power_density_W_m2,
        program_voltage_V=program_voltage_V,
    )
    prediction = (
        predict_electro_optical_delta_vfb_vs_programming_time(
            Simulator(device, physics, config),
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
        observed_values=(
            scale
            * prediction.predicted_delta_vfb_V
        ),
        observed_uncertainty=np.full(
            PROGRAMMING_TIMES_S.size,
            UNCERTAINTY_V,
            dtype=float,
        ),
        metadata=ExperimentalDatasetMetadata(
            dataset_id=dataset_id,
            source="NCMemSim synthetic F4i5 validation fixture",
            sample_id="synthetic-gesn-photo",
            temperature_K=300.0,
        ),
        conditions=(
            ExperimentalCondition(
                name="program_voltage",
                value=program_voltage_V,
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


def _calibration_spec():
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
                parameter_name=(
                    "photo_capture_efficiency"
                ),
                target=(
                    DeviceFitTarget
                    .PHOTO_CAPTURE_EFFICIENCY
                ),
            ),
        ),
        name="f4i5-photo-capture-training-fit",
    )


def _criteria():
    return CalibrationCriteria(
        max_validation_rmse=1.0e-10,
        max_scaled_condition_number=1.01,
    )


@pytest.fixture(scope="module")
def training_bundle():
    datasets = tuple(
        _dataset(
            wavelength_nm,
            power_density_W_m2,
            dataset_id=f"f4i5-training-{index}",
        )
        for index, (
            wavelength_nm,
            power_density_W_m2,
        ) in enumerate(
            TRAINING_CONDITIONS,
            start=1,
        )
    )
    protocols = tuple(
        _protocol(
            wavelength_nm,
            power_density_W_m2,
        )
        for wavelength_nm, power_density_W_m2
        in TRAINING_CONDITIONS
    )

    device, physics, config, photo = _base_objects()
    fit_result = (
        fit_single_parameter_photo_capture_efficiency_multi_condition(
            datasets,
            protocols,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            base_photo_config=photo,
            calibration_spec=_calibration_spec(),
            least_squares_config=LeastSquaresConfig(
                ftol=1.0e-12,
                xtol=1.0e-12,
                gtol=1.0e-12,
                max_nfev=1000,
            ),
        )
    )

    return fit_result, datasets, protocols


def test_independent_validation_can_promote_fitted_eta(
    training_bundle,
):
    fit_result = training_bundle[0]
    wavelength_nm, power_density_W_m2 = (
        VALIDATION_CONDITION
    )
    validation = _dataset(
        wavelength_nm,
        power_density_W_m2,
        dataset_id="f4i5-independent-validation",
    )
    protocol = _protocol(
        wavelength_nm,
        power_density_W_m2,
    )

    result = qualify_photo_capture_efficiency_fit(
        fit_result,
        validation,
        protocol,
        criteria=_criteria(),
    )

    assert isinstance(
        result,
        DevicePhotoCalibrationResult,
    )
    assert result.calibrated is True
    assert result.scientific_status == "CALIBRATED"
    assert result.failed_criteria == ()
    assert isinstance(
        result.calibrated_parameter,
        CalibratedPhotoCaptureEfficiency,
    )
    assert result.calibrated_photo_config is not None
    assert (
        result.calibrated_parameter.status
        == "CALIBRATED"
    )
    assert (
        result.calibrated_parameter.target
        is DeviceFitTarget.PHOTO_CAPTURE_EFFICIENCY
    )
    assert (
        result.calibrated_parameter.value
        == pytest.approx(TRUE_ETA, rel=5.0e-3)
    )
    assert (
        result.calibrated_photo_config
        .photo_capture_efficiency
        == result.calibrated_parameter.value
    )


def test_validation_uses_fitted_eta_without_refitting(
    training_bundle,
):
    fit_result = training_bundle[0]
    wavelength_nm, power_density_W_m2 = (
        VALIDATION_CONDITION
    )
    validation = _dataset(
        wavelength_nm,
        power_density_W_m2,
        dataset_id="f4i5-no-refit-validation",
    )
    protocol = _protocol(
        wavelength_nm,
        power_density_W_m2,
    )

    fitted_before = copy.deepcopy(
        fit_result.fitted_parameter_values
    )
    nfev_before = fit_result.numerical_result.nfev

    result = qualify_photo_capture_efficiency_fit(
        fit_result,
        validation,
        protocol,
        criteria=_criteria(),
    )

    assert fit_result.fitted_parameter_values == fitted_before
    assert fit_result.numerical_result.nfev == nfev_before
    assert result.calibrated_parameter is not None
    assert (
        result.calibrated_parameter.value
        == fit_result.fitted_parameter_values[
            "photo_capture_efficiency"
        ]
    )
    assert np.allclose(
        result.prediction.predicted_delta_vfb_V,
        validation.observed_values,
        rtol=1.0e-10,
        atol=1.0e-15,
    )


def test_reusing_any_training_dataset_fails_distinctness(
    training_bundle,
):
    fit_result, datasets, protocols = training_bundle

    result = qualify_photo_capture_efficiency_fit(
        fit_result,
        datasets[0],
        protocols[0],
        criteria=_criteria(),
    )

    assert result.calibrated is False
    assert result.scientific_status == "NOT_CALIBRATED"
    assert "distinct_validation_dataset" in (
        result.failed_criteria
    )
    assert result.calibrated_parameter is None
    assert result.calibrated_photo_config is None


def test_incompatible_validation_data_fail_rmse_without_promotion(
    training_bundle,
):
    fit_result = training_bundle[0]
    wavelength_nm, power_density_W_m2 = (
        VALIDATION_CONDITION
    )
    validation = _dataset(
        wavelength_nm,
        power_density_W_m2,
        dataset_id="f4i5-incompatible-validation",
        scale=1.20,
    )

    result = qualify_photo_capture_efficiency_fit(
        fit_result,
        validation,
        _protocol(
            wavelength_nm,
            power_density_W_m2,
        ),
        criteria=_criteria(),
    )

    assert result.calibrated is False
    assert result.scientific_status == "NOT_CALIBRATED"
    assert "validation_rmse" in result.failed_criteria
    assert (
        result.qualification.validation_objective
        .root_mean_square_error
        > _criteria().max_validation_rmse
    )
    assert result.calibrated_parameter is None
    assert result.calibrated_photo_config is None


def test_validation_preserves_training_nonoptical_protocol(
    training_bundle,
):
    fit_result = training_bundle[0]
    wavelength_nm, power_density_W_m2 = (
        VALIDATION_CONDITION
    )
    validation = _dataset(
        wavelength_nm,
        power_density_W_m2,
        dataset_id="f4i5-voltage-mismatch",
        program_voltage_V=2.5,
    )

    with pytest.raises(
        ValueError,
        match="may vary optical source conditions only",
    ):
        qualify_photo_capture_efficiency_fit(
            fit_result,
            validation,
            _protocol(
                wavelength_nm,
                power_density_W_m2,
                program_voltage_V=2.5,
            ),
            criteria=_criteria(),
        )


def test_calibration_result_is_auditable_and_hashed(
    training_bundle,
):
    fit_result = training_bundle[0]
    wavelength_nm, power_density_W_m2 = (
        VALIDATION_CONDITION
    )
    validation = _dataset(
        wavelength_nm,
        power_density_W_m2,
        dataset_id="f4i5-serialization-validation",
    )
    protocol = _protocol(
        wavelength_nm,
        power_density_W_m2,
    )

    result = qualify_photo_capture_efficiency_fit(
        fit_result,
        validation,
        protocol,
        criteria=_criteria(),
    )
    payload = result.to_dict()

    assert payload["schema_version"] == 1
    assert (
        payload["calibration_type"]
        == "device_photo_capture_efficiency"
    )
    assert payload["scientific_status"] == "CALIBRATED"
    assert payload["calibrated"] is True
    assert payload["training_dataset_hashes"] == list(
        fit_result.dataset_hashes
    )
    assert (
        payload["training_dataset_collection_hash"]
        == result.training_dataset_collection_hash
    )
    assert (
        payload["validation_dataset_hash"]
        == validation.dataset_hash()
    )
    assert (
        payload["validation_protocol_hash"]
        == protocol.protocol_hash()
    )
    assert (
        payload["qualification_hash"]
        == result.qualification.qualification_hash()
    )
    assert (
        payload["calibrated_parameter"]["status"]
        == "CALIBRATED"
    )
    assert (
        payload["calibrated_parameter"][
            "reported_uncertainty"
        ]
        is None
    )


def test_original_fitted_context_is_not_mutated(
    training_bundle,
):
    fit_result = training_bundle[0]
    original_eta = (
        fit_result.fitted_context.photo_config
        .photo_capture_efficiency
    )
    original_values = dict(
        fit_result.fitted_context.parameter_values
    )

    wavelength_nm, power_density_W_m2 = (
        VALIDATION_CONDITION
    )
    qualify_photo_capture_efficiency_fit(
        fit_result,
        _dataset(
            wavelength_nm,
            power_density_W_m2,
            dataset_id="f4i5-nonmutation-validation",
        ),
        _protocol(
            wavelength_nm,
            power_density_W_m2,
        ),
        criteria=_criteria(),
    )

    assert (
        fit_result.fitted_context.photo_config
        .photo_capture_efficiency
        == original_eta
    )
    assert (
        fit_result.fitted_context.parameter_values
        == original_values
    )
