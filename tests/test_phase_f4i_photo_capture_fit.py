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
    DevicePhotoProgramTimeFitResult,
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
INTERNAL_DT_S = 1.0e-5
OBSERVATION_UNCERTAINTY_V = 1.0e-10
PROGRAMMING_TIMES_S = np.asarray(
    [1.0e-4, 3.0e-4, 1.0e-3],
    dtype=float,
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


def _protocol(
    *,
    wavelength_nm: float = WAVELENGTH_NM,
    power_density_W_m2: float = POWER_DENSITY_W_M2,
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


def _eta_spec():
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
                    DeviceFitTarget
                    .PHOTO_CAPTURE_EFFICIENCY
                ),
            ),
        ),
        name="synthetic-photo-capture-recovery",
    )


def _strict_solver():
    return LeastSquaresConfig(
        ftol=1.0e-12,
        xtol=1.0e-12,
        gtol=1.0e-12,
        max_nfev=1000,
    )


def _synthetic_dataset(
    *,
    wavelength_nm: float = WAVELENGTH_NM,
    power_density_W_m2: float = POWER_DENSITY_W_M2,
):
    device, physics, config, _ = _base_objects()
    protocol = _protocol(
        wavelength_nm=wavelength_nm,
        power_density_W_m2=power_density_W_m2,
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
        observed_uncertainty=np.full(
            PROGRAMMING_TIMES_S.size,
            OBSERVATION_UNCERTAINTY_V,
            dtype=float,
        ),
        metadata=ExperimentalDatasetMetadata(
            dataset_id=(
                "synthetic-photo-delta-vfb-vs-time"
            ),
            source=(
                "NCMemSim synthetic F4i3b "
                "photo-capture recovery data"
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


def _run_fit(
    dataset=None,
    protocol=None,
    spec=None,
):
    device, physics, config, photo_config = (
        _base_objects()
    )

    result = (
        fit_single_parameter_photo_capture_efficiency_vs_programming_time(
            (
                _synthetic_dataset()
                if dataset is None
                else dataset
            ),
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            base_photo_config=photo_config,
            calibration_spec=(
                _eta_spec()
                if spec is None
                else spec
            ),
            protocol=(
                _protocol()
                if protocol is None
                else protocol
            ),
            least_squares_config=_strict_solver(),
        )
    )

    return result, photo_config


def test_fit_recovers_known_photo_capture_efficiency():
    result, _ = _run_fit()

    assert isinstance(
        result,
        DevicePhotoProgramTimeFitResult,
    )
    assert result.numerical_result.success

    fitted_eta = (
        result.fitted_parameter_values[
            "photo_capture_efficiency"
        ]
    )

    assert fitted_eta == pytest.approx(
        TRUE_ETA,
        rel=5.0e-3,
    )
    assert (
        result.objective.root_mean_square_error
        < 1.0e-9
    )


def test_fit_uses_uncertainty_weighting():
    result, _ = _run_fit()

    assert result.objective.weighted


def test_fit_does_not_mutate_base_photo_config():
    result, photo_config = _run_fit()

    assert (
        photo_config.photo_capture_efficiency
        == pytest.approx(BASE_ETA)
    )
    assert result.fitted_context.photo_config is not None
    assert (
        result.fitted_context.photo_config
        .photo_capture_efficiency
        != pytest.approx(BASE_ETA)
    )


def test_fit_result_is_fitted_not_calibrated():
    result, _ = _run_fit()

    assert result.scientific_status == "FITTED"
    assert (
        result.to_dict()["scientific_status"]
        == "FITTED"
    )
    assert "CALIBRATED" not in result.to_dict().values()


def test_fit_result_serializes_reproducibility_ids():
    dataset = _synthetic_dataset()
    spec = _eta_spec()
    protocol = _protocol()

    device, physics, config, photo_config = (
        _base_objects()
    )

    result = (
        fit_single_parameter_photo_capture_efficiency_vs_programming_time(
            dataset,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            base_photo_config=photo_config,
            calibration_spec=spec,
            protocol=protocol,
            least_squares_config=_strict_solver(),
        )
    )

    payload = result.to_dict()

    assert (
        payload["dataset_hash"]
        == dataset.dataset_hash()
    )
    assert (
        payload["calibration_specification_hash"]
        == spec.specification_hash()
    )
    assert (
        payload["protocol_hash"]
        == protocol.protocol_hash()
    )
    assert (
        payload["fitted_photo_transition_config"][
            "photo_capture_efficiency"
        ]
        == pytest.approx(
            result.fitted_parameter_values[
                "photo_capture_efficiency"
            ]
        )
    )


def test_fit_rejects_wavelength_mismatch():
    with pytest.raises(
        ValueError,
        match="wavelength",
    ):
        _run_fit(
            protocol=_protocol(
                wavelength_nm=1300.0,
            )
        )


def test_fit_rejects_optical_power_mismatch():
    with pytest.raises(
        ValueError,
        match="optical_power_density",
    ):
        _run_fit(
            protocol=_protocol(
                power_density_W_m2=500.0,
            )
        )


def test_fit_rejects_wrong_observable_semantics():
    dataset = _synthetic_dataset()

    bad = DeviceObservableDataset(
        independent_variable_name=(
            dataset.independent_variable_name
        ),
        independent_variable_unit=(
            dataset.independent_variable_unit
        ),
        independent_values=(
            dataset.independent_values
        ),
        observable_name="memory_window",
        observable_unit="V",
        observed_values=(
            dataset.observed_values
        ),
        observed_uncertainty=(
            dataset.observed_uncertainty
        ),
        metadata=dataset.metadata,
        conditions=dataset.conditions,
    )

    with pytest.raises(
        ValueError,
        match="delta_vfb",
    ):
        _run_fit(dataset=bad)


def test_fit_requires_all_optical_conditions():
    dataset = _synthetic_dataset()

    bad = DeviceObservableDataset(
        independent_variable_name=(
            dataset.independent_variable_name
        ),
        independent_variable_unit=(
            dataset.independent_variable_unit
        ),
        independent_values=(
            dataset.independent_values
        ),
        observable_name=dataset.observable_name,
        observable_unit=dataset.observable_unit,
        observed_values=dataset.observed_values,
        observed_uncertainty=(
            dataset.observed_uncertainty
        ),
        metadata=dataset.metadata,
        conditions=tuple(
            condition
            for condition in dataset.conditions
            if condition.name != "wavelength"
        ),
    )

    with pytest.raises(
        ValueError,
        match="wavelength",
    ):
        _run_fit(dataset=bad)


def test_fit_rejects_non_photo_single_parameter_target():
    parameter = FitParameter(
        name="qfix_C_m2",
        initial_value=0.0,
        lower_bound=-1.0e-3,
        upper_bound=1.0e-3,
        unit="C/m^2",
    )
    spec = DeviceCalibrationSpec(
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
    )

    with pytest.raises(
        ValueError,
        match="PHOTO_CAPTURE_EFFICIENCY",
    ):
        _run_fit(spec=spec)


def test_fit_rejects_multi_parameter_spec():
    spec = DeviceCalibrationSpec(
        parameter_set=FitParameterSet(
            (
                FitParameter(
                    name="photo_capture_efficiency",
                    initial_value=BASE_ETA,
                    lower_bound=1.0e-9,
                    upper_bound=1.0e-6,
                ),
                FitParameter(
                    name="qfix_C_m2",
                    initial_value=0.0,
                    lower_bound=-1.0e-3,
                    upper_bound=1.0e-3,
                    unit="C/m^2",
                ),
            )
        ),
        bindings=(
            DeviceFitParameterBinding(
                "photo_capture_efficiency",
                DeviceFitTarget
                .PHOTO_CAPTURE_EFFICIENCY,
            ),
            DeviceFitParameterBinding(
                "qfix_C_m2",
                DeviceFitTarget
                .SIMULATION_QFIX_C_M2,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="exactly one free parameter",
    ):
        _run_fit(spec=spec)
