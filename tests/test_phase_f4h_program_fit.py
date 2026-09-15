from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

pytest.importorskip("scipy")

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
from ncmemsim.physics import PhysicsModel
from ncmemsim.program_fit import (
    DeviceProgramTimeFitResult,
    ProgramTimeFitProtocol,
    fit_single_parameter_delta_vfb_vs_programming_time,
    predict_delta_vfb_vs_programming_time,
)
from ncmemsim.reference import (
    make_v53_reference_device,
)
from ncmemsim.simulator import (
    SimulationConfig,
    Simulator,
)
from ncmemsim.state import DeviceState


TRUE_NU0_HZ = 2.0e12
PROGRAM_VOLTAGE_V = 3.0
READ_VOLTAGE_V = 0.0
PROGRAMMING_TIMES_S = np.asarray(
    [1.0e-4, 3.0e-4, 1.0e-3],
    dtype=float,
)


def _base_objects():
    device = make_v53_reference_device(
        grid_points=7,
    )
    physics = PhysicsModel.default()
    config = SimulationConfig(
        dwell_time_s=5.0e-3,
        internal_dt_s=1.0e-5,
    )
    return device, physics, config


def _protocol():
    return ProgramTimeFitProtocol(
        program_voltage_V=PROGRAM_VOLTAGE_V,
        read_voltage_V=READ_VOLTAGE_V,
        program_internal_dt_s=1.0e-5,
    )


def _nu0_spec():
    return DeviceCalibrationSpec(
        parameter_set=FitParameterSet(
            (
                FitParameter(
                    name="nu0_Hz",
                    initial_value=5.0e11,
                    lower_bound=1.0e11,
                    upper_bound=5.0e12,
                    unit="Hz",
                    description=(
                        "Program injection attempt "
                        "frequency."
                    ),
                ),
            )
        ),
        bindings=(
            DeviceFitParameterBinding(
                parameter_name="nu0_Hz",
                target=(
                    DeviceFitTarget
                    .KINETICS_NU0_HZ
                ),
            ),
        ),
        name="synthetic-delta-vfb-time-nu0",
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
    uncertainty=None,
):
    device, physics, config = _base_objects()

    physics.occupancy.config = replace(
        physics.occupancy.config,
        nu0_Hz=TRUE_NU0_HZ,
    )

    prediction = (
        predict_delta_vfb_vs_programming_time(
            Simulator(
                device,
                physics,
                config,
            ),
            PROGRAMMING_TIMES_S,
            _protocol(),
        )
    )

    sigma = None
    if uncertainty is not None:
        sigma = np.full(
            PROGRAMMING_TIMES_S.size,
            uncertainty,
            dtype=float,
        )

    return DeviceObservableDataset(
        independent_variable_name=(
            "programming_time"
        ),
        independent_variable_unit="s",
        independent_values=(
            PROGRAMMING_TIMES_S
        ),
        observable_name="delta_vfb",
        observable_unit="V",
        observed_values=(
            prediction.predicted_delta_vfb_V
        ),
        observed_uncertainty=sigma,
        metadata=ExperimentalDatasetMetadata(
            dataset_id=(
                "synthetic-delta-vfb-vs-time"
            ),
            source=(
                "NCMemSim synthetic F4h2b2 "
                "parameter-recovery data"
            ),
            sample_id="synthetic-v53",
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
        ),
    )


def test_protocol_hash_is_deterministic():
    assert (
        _protocol().protocol_hash()
        == _protocol().protocol_hash()
    )


def test_protocol_hash_changes_with_voltage():
    assert (
        ProgramTimeFitProtocol(
            3.0
        ).protocol_hash()
        != ProgramTimeFitProtocol(
            4.0
        ).protocol_hash()
    )


def test_prediction_uses_one_result_per_time_point():
    device, physics, config = _base_objects()

    prediction = (
        predict_delta_vfb_vs_programming_time(
            Simulator(
                device,
                physics,
                config,
            ),
            PROGRAMMING_TIMES_S,
            _protocol(),
        )
    )

    assert (
        prediction.programming_times_s.shape
        == PROGRAMMING_TIMES_S.shape
    )
    assert (
        prediction.predicted_delta_vfb_V.shape
        == PROGRAMMING_TIMES_S.shape
    )
    assert (
        len(prediction.pulse_results)
        == PROGRAMMING_TIMES_S.size
    )


def test_prediction_time_points_are_independent():
    device, physics, config = _base_objects()
    initial = DeviceState.empty_for_device(device)

    prediction = (
        predict_delta_vfb_vs_programming_time(
            Simulator(
                device,
                physics,
                config,
            ),
            PROGRAMMING_TIMES_S,
            _protocol(),
            initial_state=initial,
        )
    )

    for time_s, pulse_result in zip(
        PROGRAMMING_TIMES_S,
        prediction.pulse_results,
    ):
        assert (
            pulse_result.initial_state.time_s
            == pytest.approx(0.0)
        )
        assert (
            pulse_result.programmed_state.time_s
            == pytest.approx(time_s)
        )

    assert initial.time_s == pytest.approx(0.0)


def test_prediction_preserves_dataset_time_order():
    device, physics, config = _base_objects()
    times = np.asarray(
        [1.0e-3, 1.0e-4, 3.0e-4],
        dtype=float,
    )

    prediction = (
        predict_delta_vfb_vs_programming_time(
            Simulator(
                device,
                physics,
                config,
            ),
            times,
            _protocol(),
        )
    )

    assert np.array_equal(
        prediction.programming_times_s,
        times,
    )


def test_fit_recovers_known_nu0():
    device, physics, config = _base_objects()

    result = (
        fit_single_parameter_delta_vfb_vs_programming_time(
            _synthetic_dataset(),
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_nu0_spec(),
            protocol=_protocol(),
            least_squares_config=_strict_solver(),
        )
    )

    assert isinstance(
        result,
        DeviceProgramTimeFitResult,
    )
    assert result.numerical_result.success

    fitted_nu0 = (
        result.fitted_parameter_values[
            "nu0_Hz"
        ]
    )

    assert fitted_nu0 == pytest.approx(
        TRUE_NU0_HZ,
        rel=5.0e-3,
    )

    assert (
        result.objective
        .root_mean_square_error
        < 1.0e-6
    )


def test_fit_uses_uncertainty_weighting():
    device, physics, config = _base_objects()

    result = (
        fit_single_parameter_delta_vfb_vs_programming_time(
            _synthetic_dataset(
                uncertainty=1.0e-4,
            ),
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_nu0_spec(),
            protocol=_protocol(),
            least_squares_config=_strict_solver(),
        )
    )

    assert result.objective.weighted


def test_fit_does_not_mutate_baseline_kinetics():
    device, physics, config = _base_objects()
    original_nu0 = (
        physics.occupancy.config.nu0_Hz
    )

    result = (
        fit_single_parameter_delta_vfb_vs_programming_time(
            _synthetic_dataset(),
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_nu0_spec(),
            protocol=_protocol(),
            least_squares_config=_strict_solver(),
        )
    )

    assert (
        physics.occupancy.config.nu0_Hz
        == pytest.approx(original_nu0)
    )
    assert (
        result.fitted_context
        .physics.occupancy.config.nu0_Hz
        != pytest.approx(original_nu0)
    )


def test_fit_result_is_fitted_not_calibrated():
    device, physics, config = _base_objects()

    result = (
        fit_single_parameter_delta_vfb_vs_programming_time(
            _synthetic_dataset(),
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_nu0_spec(),
            protocol=_protocol(),
            least_squares_config=_strict_solver(),
        )
    )

    assert result.scientific_status == "FITTED"
    assert (
        result.to_dict()[
            "scientific_status"
        ]
        == "FITTED"
    )


def test_fit_result_serializes_reproducibility_ids():
    device, physics, config = _base_objects()
    dataset = _synthetic_dataset()
    spec = _nu0_spec()
    protocol = _protocol()

    result = (
        fit_single_parameter_delta_vfb_vs_programming_time(
            dataset,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
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
        payload[
            "calibration_specification_hash"
        ]
        == spec.specification_hash()
    )
    assert (
        payload["protocol_hash"]
        == protocol.protocol_hash()
    )


def test_fit_rejects_wrong_observable_semantics():
    dataset = _synthetic_dataset()

    bad = DeviceObservableDataset(
        independent_variable_name=(
            "programming_time"
        ),
        independent_variable_unit="s",
        independent_values=(
            dataset.independent_values
        ),
        observable_name="memory_window",
        observable_unit="V",
        observed_values=(
            dataset.observed_values
        ),
        metadata=dataset.metadata,
        conditions=dataset.conditions,
    )

    device, physics, config = _base_objects()

    with pytest.raises(
        ValueError,
        match="delta_vfb",
    ):
        fit_single_parameter_delta_vfb_vs_programming_time(
            bad,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_nu0_spec(),
            protocol=_protocol(),
        )


def test_fit_requires_program_voltage_condition():
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
        observable_name=(
            dataset.observable_name
        ),
        observable_unit=(
            dataset.observable_unit
        ),
        observed_values=(
            dataset.observed_values
        ),
        metadata=dataset.metadata,
        conditions=(),
    )

    device, physics, config = _base_objects()

    with pytest.raises(
        ValueError,
        match="program_voltage",
    ):
        fit_single_parameter_delta_vfb_vs_programming_time(
            bad,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_nu0_spec(),
            protocol=_protocol(),
        )


def test_fit_rejects_program_voltage_mismatch():
    device, physics, config = _base_objects()

    with pytest.raises(
        ValueError,
        match="does not match",
    ):
        fit_single_parameter_delta_vfb_vs_programming_time(
            _synthetic_dataset(),
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_nu0_spec(),
            protocol=ProgramTimeFitProtocol(
                program_voltage_V=4.0,
                read_voltage_V=READ_VOLTAGE_V,
                program_internal_dt_s=1.0e-5,
            ),
        )


def test_fit_rejects_read_voltage_mismatch_when_condition_present():
    device, physics, config = _base_objects()

    with pytest.raises(
        ValueError,
        match="read_voltage_V",
    ):
        fit_single_parameter_delta_vfb_vs_programming_time(
            _synthetic_dataset(),
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_nu0_spec(),
            protocol=ProgramTimeFitProtocol(
                program_voltage_V=PROGRAM_VOLTAGE_V,
                read_voltage_V=1.0,
                program_internal_dt_s=1.0e-5,
            ),
        )


def test_fit_rejects_multi_parameter_spec():
    device, physics, config = _base_objects()

    spec = DeviceCalibrationSpec(
        parameter_set=FitParameterSet(
            (
                FitParameter(
                    name="nu0_Hz",
                    initial_value=5.0e11,
                    lower_bound=1.0e11,
                    upper_bound=5.0e12,
                ),
                FitParameter(
                    name="barrier",
                    initial_value=2.8,
                    lower_bound=1.5,
                    upper_bound=4.0,
                ),
            )
        ),
        bindings=(
            DeviceFitParameterBinding(
                "nu0_Hz",
                DeviceFitTarget.KINETICS_NU0_HZ,
            ),
            DeviceFitParameterBinding(
                "barrier",
                DeviceFitTarget.FG_PHI_BARRIER_PROG_EV,
                fg_index=0,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="exactly one free parameter",
    ):
        fit_single_parameter_delta_vfb_vs_programming_time(
            _synthetic_dataset(),
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=spec,
            protocol=_protocol(),
        )


@pytest.mark.parametrize(
    "times",
    [
        [0.0, 1.0e-3],
        [-1.0e-4, 1.0e-3],
        [float("nan"), 1.0e-3],
    ],
)
def test_prediction_rejects_invalid_times(
    times,
):
    device, physics, config = _base_objects()

    with pytest.raises(ValueError):
        predict_delta_vfb_vs_programming_time(
            Simulator(
                device,
                physics,
                config,
            ),
            times,
            _protocol(),
        )
