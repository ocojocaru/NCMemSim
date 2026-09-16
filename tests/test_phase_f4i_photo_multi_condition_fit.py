from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("scipy")

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
    DevicePhotoMultiConditionFitResult,
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


def _base_objects():
    device = DeviceBuilder.v1(
        n_fgs=1,
        nc_material=[make_gesn(0.08)],
        nc_diameter_nm=[5.0],
        active_fraction=[1.0],
        fg_thickness_nm=[15.0],
    )
    device.floating_gates()[0].grid_points = 7

    physics = PhysicsModel.default()
    config = SimulationConfig(
        dwell_time_s=5.0e-3,
        internal_dt_s=INTERNAL_DT_S,
    )
    photo_config = PhotoTransitionConfig(
        photo_capture_efficiency=BASE_ETA,
    )
    return device, physics, config, photo_config


def _weights(
    *,
    r12: float = 1.0,
) -> PhotoTransitionWeights:
    return PhotoTransitionWeights(
        r01=1.0,
        r12=r12,
        r10=0.0,
        r21=0.0,
    )


def _protocol(
    wavelength_nm: float,
    power_density_W_m2: float,
    *,
    weights: PhotoTransitionWeights | None = None,
) -> ElectroOpticalProgramTimeFitProtocol:
    return ElectroOpticalProgramTimeFitProtocol(
        program_voltage_V=PROGRAM_VOLTAGE_V,
        read_voltage_V=READ_VOLTAGE_V,
        program_internal_dt_s=INTERNAL_DT_S,
        light_source=LightSource.laser(
            wavelength_nm=wavelength_nm,
            power_density_W_m2=power_density_W_m2,
        ),
        photo_weights=(
            _weights()
            if weights is None
            else weights
        ),
    )


def _eta_spec():
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
                "photo_capture_efficiency",
                DeviceFitTarget
                .PHOTO_CAPTURE_EFFICIENCY,
            ),
        ),
        name="synthetic-photo-multi-condition",
    )


def _strict_solver():
    return LeastSquaresConfig(
        ftol=1.0e-12,
        xtol=1.0e-12,
        gtol=1.0e-12,
        max_nfev=1000,
    )


def _synthetic_dataset(
    wavelength_nm: float,
    power_density_W_m2: float,
    *,
    dataset_suffix: str,
    uncertainty: bool = True,
) -> DeviceObservableDataset:
    device, physics, config, _ = _base_objects()
    protocol = _protocol(
        wavelength_nm,
        power_density_W_m2,
    )

    prediction = (
        predict_electro_optical_delta_vfb_vs_programming_time(
            Simulator(
                device,
                physics,
                config,
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
        observed_values=(
            prediction.predicted_delta_vfb_V
        ),
        observed_uncertainty=(
            np.full(
                PROGRAMMING_TIMES_S.size,
                OBSERVATION_UNCERTAINTY_V,
                dtype=float,
            )
            if uncertainty
            else None
        ),
        metadata=ExperimentalDatasetMetadata(
            dataset_id=(
                "synthetic-photo-multi-"
                f"{dataset_suffix}"
            ),
            source=(
                "NCMemSim synthetic F4i4a "
                "multi-condition data"
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


@pytest.fixture(scope="module")
def prepared_conditions():
    datasets = tuple(
        _synthetic_dataset(
            wavelength_nm,
            power_density,
            dataset_suffix=f"condition-{index}",
        )
        for index, (
            wavelength_nm,
            power_density,
        ) in enumerate(
            OPTICAL_CONDITIONS,
            start=1,
        )
    )
    protocols = tuple(
        _protocol(
            wavelength_nm,
            power_density,
        )
        for wavelength_nm, power_density
        in OPTICAL_CONDITIONS
    )
    return datasets, protocols


@pytest.fixture(scope="module")
def joint_fit_bundle(prepared_conditions):
    datasets, protocols = prepared_conditions
    device, physics, config, photo_config = (
        _base_objects()
    )
    spec = _eta_spec()

    result = (
        fit_single_parameter_photo_capture_efficiency_multi_condition(
            datasets,
            protocols,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            base_photo_config=photo_config,
            calibration_spec=spec,
            least_squares_config=_strict_solver(),
        )
    )

    return (
        result,
        datasets,
        protocols,
        spec,
        photo_config,
    )


def test_joint_fit_recovers_shared_photo_capture_efficiency(
    joint_fit_bundle,
):
    result = joint_fit_bundle[0]

    assert isinstance(
        result,
        DevicePhotoMultiConditionFitResult,
    )
    assert result.numerical_result.success
    assert (
        result.fitted_parameter_values[
            "photo_capture_efficiency"
        ]
        == pytest.approx(
            TRUE_ETA,
            rel=5.0e-3,
        )
    )
    assert (
        result.joint_root_mean_square_error_V
        < 1.0e-9
    )


def test_joint_fit_concatenates_all_condition_residuals(
    joint_fit_bundle,
):
    result = joint_fit_bundle[0]

    expected_points = (
        len(OPTICAL_CONDITIONS)
        * PROGRAMMING_TIMES_S.size
    )

    assert result.n_conditions == len(
        OPTICAL_CONDITIONS
    )
    assert result.n_observations == expected_points
    assert (
        result.numerical_result
        .objective_residuals.size
        == expected_points
    )
    assert (
        result.joint_objective_residuals.size
        == expected_points
    )


def test_joint_fit_preserves_per_condition_weighting(
    joint_fit_bundle,
):
    result = joint_fit_bundle[0]

    assert result.weighted
    assert all(
        objective.weighted
        for objective in result.objectives
    )


def test_joint_fit_does_not_mutate_base_photo_config(
    joint_fit_bundle,
):
    result = joint_fit_bundle[0]
    photo_config = joint_fit_bundle[4]

    assert (
        photo_config.photo_capture_efficiency
        == pytest.approx(BASE_ETA)
    )
    assert result.fitted_context.photo_config is not None
    assert (
        result.fitted_context.photo_config
        .photo_capture_efficiency
        == pytest.approx(
            result.fitted_parameter_values[
                "photo_capture_efficiency"
            ]
        )
    )


def test_joint_fit_is_fitted_not_calibrated(
    joint_fit_bundle,
):
    result = joint_fit_bundle[0]

    assert result.scientific_status == "FITTED"
    assert (
        result.to_dict()["scientific_status"]
        == "FITTED"
    )


def test_joint_fit_serializes_dataset_and_protocol_hashes(
    joint_fit_bundle,
):
    result, datasets, protocols, spec, _ = (
        joint_fit_bundle
    )
    payload = result.to_dict()

    assert (
        payload["calibration_specification_hash"]
        == spec.specification_hash()
    )
    assert len(payload["conditions"]) == len(
        datasets
    )

    for entry, dataset, protocol in zip(
        payload["conditions"],
        datasets,
        protocols,
    ):
        assert (
            entry["dataset_hash"]
            == dataset.dataset_hash()
        )
        assert (
            entry["protocol_hash"]
            == protocol.protocol_hash()
        )


def test_joint_fit_requires_at_least_two_conditions(
    prepared_conditions,
):
    datasets, protocols = prepared_conditions
    device, physics, config, photo_config = (
        _base_objects()
    )

    with pytest.raises(
        ValueError,
        match="at least two datasets",
    ):
        fit_single_parameter_photo_capture_efficiency_multi_condition(
            datasets[:1],
            protocols[:1],
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            base_photo_config=photo_config,
            calibration_spec=_eta_spec(),
        )


def test_joint_fit_rejects_dataset_protocol_count_mismatch(
    prepared_conditions,
):
    datasets, protocols = prepared_conditions
    device, physics, config, photo_config = (
        _base_objects()
    )

    with pytest.raises(
        ValueError,
        match="same number",
    ):
        fit_single_parameter_photo_capture_efficiency_multi_condition(
            datasets,
            protocols[:2],
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            base_photo_config=photo_config,
            calibration_spec=_eta_spec(),
        )


def test_joint_fit_requires_distinct_optical_conditions():
    first = _synthetic_dataset(
        1550.0,
        1000.0,
        dataset_suffix="duplicate-a",
    )
    second = _synthetic_dataset(
        1550.0,
        1000.0,
        dataset_suffix="duplicate-b",
    )
    protocol = _protocol(
        1550.0,
        1000.0,
    )
    device, physics, config, photo_config = (
        _base_objects()
    )

    with pytest.raises(
        ValueError,
        match="distinct",
    ):
        fit_single_parameter_photo_capture_efficiency_multi_condition(
            (first, second),
            (protocol, protocol),
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            base_photo_config=photo_config,
            calibration_spec=_eta_spec(),
        )


def test_joint_fit_rejects_nonoptical_protocol_changes(
    prepared_conditions,
):
    datasets, protocols = prepared_conditions
    changed = ElectroOpticalProgramTimeFitProtocol(
        program_voltage_V=PROGRAM_VOLTAGE_V,
        read_voltage_V=READ_VOLTAGE_V,
        program_internal_dt_s=INTERNAL_DT_S,
        light_source=protocols[1].light_source,
        photo_weights=_weights(r12=0.5),
    )
    device, physics, config, photo_config = (
        _base_objects()
    )

    with pytest.raises(
        ValueError,
        match="varies optical source conditions only",
    ):
        fit_single_parameter_photo_capture_efficiency_multi_condition(
            datasets,
            (
                protocols[0],
                changed,
                protocols[2],
            ),
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            base_photo_config=photo_config,
            calibration_spec=_eta_spec(),
        )


def test_joint_fit_rejects_mixed_weighting_modes(
    prepared_conditions,
):
    datasets, protocols = prepared_conditions
    unweighted = DeviceObservableDataset(
        independent_variable_name=(
            datasets[1].independent_variable_name
        ),
        independent_variable_unit=(
            datasets[1].independent_variable_unit
        ),
        independent_values=(
            datasets[1].independent_values
        ),
        observable_name=datasets[1].observable_name,
        observable_unit=datasets[1].observable_unit,
        observed_values=datasets[1].observed_values,
        observed_uncertainty=None,
        metadata=datasets[1].metadata,
        conditions=datasets[1].conditions,
    )

    device, physics, config, photo_config = (
        _base_objects()
    )

    with pytest.raises(
        ValueError,
        match="either provide",
    ):
        fit_single_parameter_photo_capture_efficiency_multi_condition(
            (
                datasets[0],
                unweighted,
                datasets[2],
            ),
            protocols,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            base_photo_config=photo_config,
            calibration_spec=_eta_spec(),
        )
