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
from ncmemsim.pulse_memory_fit import (
    DevicePulseMemoryTimeFitResult,
    PULSE_BRANCH_SEMANTICS,
    PULSE_MEMORY_WINDOW_DEFINITION,
    PULSE_READ_SEMANTICS,
    PulseMemoryTimeFitProtocol,
    fit_single_parameter_pulse_memory_window_vs_programming_time,
    predict_pulse_memory_window_vs_programming_time,
)
from ncmemsim.reference import make_v53_reference_device
from ncmemsim.simulator import SimulationConfig, Simulator
from ncmemsim.state import DeviceState


TRUE_NU0_HZ = 2.0e12
PROGRAM_VOLTAGE_V = 3.0
ERASE_VOLTAGE_V = -3.0
ERASE_TIME_S = 1.0e-3
READ_VOLTAGE_V = 0.0
PROGRAMMING_TIMES_S = np.asarray(
    [1.0e-6, 3.0e-6, 1.0e-5, 3.0e-5],
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


def _reference_state(device):
    state = DeviceState.empty_for_device(device)

    for fg_state in state.floating_gates:
        fg_state.P0[:] = 0.5
        fg_state.P1[:] = 0.5
        fg_state.P2[:] = 0.0

    state.validate(device)
    return state


def _protocol():
    return PulseMemoryTimeFitProtocol(
        program_voltage_V=PROGRAM_VOLTAGE_V,
        erase_voltage_V=ERASE_VOLTAGE_V,
        erase_time_s=ERASE_TIME_S,
        read_voltage_V=READ_VOLTAGE_V,
        pulse_internal_dt_s=1.0e-5,
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
                target=DeviceFitTarget.KINETICS_NU0_HZ,
            ),
        ),
        name="synthetic-pulse-memory-time-nu0",
    )


def _strict_solver():
    return LeastSquaresConfig(
        ftol=1.0e-12,
        xtol=1.0e-12,
        gtol=1.0e-12,
        max_nfev=1000,
    )


def _conditions(
    *,
    program_voltage=PROGRAM_VOLTAGE_V,
    erase_voltage=ERASE_VOLTAGE_V,
    erase_time=ERASE_TIME_S,
    read_voltage=READ_VOLTAGE_V,
    definition=PULSE_MEMORY_WINDOW_DEFINITION,
    branch_semantics=PULSE_BRANCH_SEMANTICS,
    read_semantics=PULSE_READ_SEMANTICS,
    include_frequency=False,
):
    conditions = [
        ExperimentalCondition(
            name="program_voltage",
            value=program_voltage,
            unit="V",
        ),
        ExperimentalCondition(
            name="erase_voltage",
            value=erase_voltage,
            unit="V",
        ),
        ExperimentalCondition(
            name="erase_pulse_width",
            value=erase_time,
            unit="s",
        ),
        ExperimentalCondition(
            name="read_voltage",
            value=read_voltage,
            unit="V",
        ),
        ExperimentalCondition(
            name="memory_window_definition",
            value=definition,
        ),
        ExperimentalCondition(
            name="branch_semantics",
            value=branch_semantics,
        ),
        ExperimentalCondition(
            name="read_semantics",
            value=read_semantics,
        ),
    ]

    if include_frequency:
        conditions.append(
            ExperimentalCondition(
                name="measurement_frequency",
                value=1.0e5,
                unit="Hz",
            )
        )

    return tuple(conditions)


def _synthetic_dataset(
    *,
    uncertainty=None,
    conditions=None,
):
    truth_device, truth_physics, truth_config = (
        _base_objects()
    )
    truth_reference = _reference_state(
        truth_device
    )

    truth_physics.occupancy.config = replace(
        truth_physics.occupancy.config,
        nu0_Hz=TRUE_NU0_HZ,
    )

    prediction = (
        predict_pulse_memory_window_vs_programming_time(
            Simulator(
                truth_device,
                truth_physics,
                truth_config,
            ),
            PROGRAMMING_TIMES_S,
            _protocol(),
            reference_state=truth_reference,
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
        independent_variable_name="programming_time",
        independent_variable_unit="s",
        independent_values=PROGRAMMING_TIMES_S,
        observable_name="memory_window",
        observable_unit="V",
        observed_values=(
            prediction.predicted_memory_window_V
        ),
        observed_uncertainty=sigma,
        metadata=ExperimentalDatasetMetadata(
            dataset_id=(
                "synthetic-pulse-memory-vs-program-time"
            ),
            source=(
                "NCMemSim synthetic F4h2c1 "
                "parameter-recovery data"
            ),
            sample_id="synthetic-v53",
            temperature_K=300.0,
        ),
        conditions=(
            _conditions()
            if conditions is None
            else conditions
        ),
    )


def _fit(dataset=None):
    device, physics, config = _base_objects()
    reference = _reference_state(device)

    return (
        fit_single_parameter_pulse_memory_window_vs_programming_time(
            _synthetic_dataset()
            if dataset is None
            else dataset,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_nu0_spec(),
            protocol=_protocol(),
            reference_state=reference,
            least_squares_config=_strict_solver(),
        )
    )


def test_protocol_hash_is_deterministic():
    assert (
        _protocol().protocol_hash()
        == _protocol().protocol_hash()
    )


def test_protocol_hash_changes_with_erase_time():
    assert (
        _protocol().protocol_hash()
        != PulseMemoryTimeFitProtocol(
            program_voltage_V=PROGRAM_VOLTAGE_V,
            erase_voltage_V=ERASE_VOLTAGE_V,
            erase_time_s=2.0e-3,
            read_voltage_V=READ_VOLTAGE_V,
            pulse_internal_dt_s=1.0e-5,
        ).protocol_hash()
    )


def test_protocol_requires_distinct_program_and_erase_voltage():
    with pytest.raises(
        ValueError,
        match="must be different",
    ):
        PulseMemoryTimeFitProtocol(
            program_voltage_V=2.0,
            erase_voltage_V=2.0,
            erase_time_s=1.0e-3,
        )


def test_prediction_uses_one_paired_result_per_time_point():
    device, physics, config = _base_objects()
    reference = _reference_state(device)

    prediction = (
        predict_pulse_memory_window_vs_programming_time(
            Simulator(
                device,
                physics,
                config,
            ),
            PROGRAMMING_TIMES_S,
            _protocol(),
            reference_state=reference,
        )
    )

    assert (
        prediction.programming_times_s.shape
        == PROGRAMMING_TIMES_S.shape
    )
    assert (
        prediction.predicted_memory_window_V.shape
        == PROGRAMMING_TIMES_S.shape
    )
    assert (
        len(prediction.pulse_results)
        == PROGRAMMING_TIMES_S.size
    )
    assert not (
        prediction.predicted_memory_window_V.flags.writeable
    )


def test_prediction_preserves_requested_time_order():
    device, physics, config = _base_objects()
    reference = _reference_state(device)
    times = np.asarray(
        [1.0e-3, 1.0e-4, 3.0e-4],
        dtype=float,
    )

    prediction = (
        predict_pulse_memory_window_vs_programming_time(
            Simulator(
                device,
                physics,
                config,
            ),
            times,
            _protocol(),
            reference_state=reference,
        )
    )

    assert np.array_equal(
        prediction.programming_times_s,
        times,
    )


def test_prediction_time_points_share_common_reference():
    device, physics, config = _base_objects()
    reference = _reference_state(device)
    before = reference.copy()

    prediction = (
        predict_pulse_memory_window_vs_programming_time(
            Simulator(
                device,
                physics,
                config,
            ),
            PROGRAMMING_TIMES_S,
            _protocol(),
            reference_state=reference,
        )
    )

    for time_s, paired_result in zip(
        PROGRAMMING_TIMES_S,
        prediction.pulse_results,
    ):
        assert (
            paired_result.program.initial_state.time_s
            == pytest.approx(reference.time_s)
        )
        assert (
            paired_result.erase.initial_state.time_s
            == pytest.approx(reference.time_s)
        )
        assert (
            paired_result.program.pulsed_state.time_s
            == pytest.approx(
                reference.time_s + time_s
            )
        )
        assert (
            paired_result.erase.pulsed_state.time_s
            == pytest.approx(
                reference.time_s + ERASE_TIME_S
            )
        )

    assert reference.time_s == before.time_s
    for lhs, rhs in zip(
        reference.floating_gates,
        before.floating_gates,
    ):
        assert np.array_equal(lhs.P0, rhs.P0)
        assert np.array_equal(lhs.P1, rhs.P1)
        assert np.array_equal(lhs.P2, rhs.P2)


def test_prediction_is_directly_from_paired_memory_window():
    device, physics, config = _base_objects()
    reference = _reference_state(device)

    prediction = (
        predict_pulse_memory_window_vs_programming_time(
            Simulator(
                device,
                physics,
                config,
            ),
            PROGRAMMING_TIMES_S,
            _protocol(),
            reference_state=reference,
        )
    )

    expected = np.asarray(
        [
            result.memory_window_V
            for result in prediction.pulse_results
        ],
        dtype=float,
    )

    assert np.array_equal(
        prediction.predicted_memory_window_V,
        expected,
    )


def test_reference_state_hash_is_deterministic_and_sensitive():
    device, physics, config = _base_objects()
    simulator = Simulator(device, physics, config)
    reference_a = _reference_state(device)
    reference_b = _reference_state(device)

    prediction_a = (
        predict_pulse_memory_window_vs_programming_time(
            simulator,
            PROGRAMMING_TIMES_S,
            _protocol(),
            reference_state=reference_a,
        )
    )
    prediction_b = (
        predict_pulse_memory_window_vs_programming_time(
            simulator,
            PROGRAMMING_TIMES_S,
            _protocol(),
            reference_state=reference_b,
        )
    )

    assert (
        prediction_a.reference_state_hash
        == prediction_b.reference_state_hash
    )

    reference_b.floating_gates[0].P0[:] = 0.6
    reference_b.floating_gates[0].P1[:] = 0.4
    reference_b.floating_gates[0].P2[:] = 0.0
    reference_b.validate(device)

    prediction_c = (
        predict_pulse_memory_window_vs_programming_time(
            simulator,
            PROGRAMMING_TIMES_S,
            _protocol(),
            reference_state=reference_b,
        )
    )

    assert (
        prediction_a.reference_state_hash
        != prediction_c.reference_state_hash
    )


def test_fit_recovers_known_nu0():
    result = _fit()

    assert isinstance(
        result,
        DevicePulseMemoryTimeFitResult,
    )
    assert result.numerical_result.success

    fitted_nu0 = (
        result.fitted_parameter_values["nu0_Hz"]
    )

    assert fitted_nu0 == pytest.approx(
        TRUE_NU0_HZ,
        rel=5.0e-3,
    )
    assert (
        result.objective.root_mean_square_error
        < 1.0e-6
    )


def test_fit_uses_uncertainty_weighting():
    result = _fit(
        _synthetic_dataset(
            uncertainty=1.0e-4,
        )
    )

    assert result.objective.weighted


def test_fit_does_not_mutate_baseline_kinetics_or_reference():
    device, physics, config = _base_objects()
    reference = _reference_state(device)
    reference_before = reference.copy()
    original_nu0 = physics.occupancy.config.nu0_Hz

    result = (
        fit_single_parameter_pulse_memory_window_vs_programming_time(
            _synthetic_dataset(),
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_nu0_spec(),
            protocol=_protocol(),
            reference_state=reference,
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

    for lhs, rhs in zip(
        reference.floating_gates,
        reference_before.floating_gates,
    ):
        assert np.array_equal(lhs.P0, rhs.P0)
        assert np.array_equal(lhs.P1, rhs.P1)
        assert np.array_equal(lhs.P2, rhs.P2)


def test_fit_result_is_fitted_not_calibrated():
    result = _fit()

    assert result.scientific_status == "FITTED"
    assert (
        result.to_dict()["scientific_status"]
        == "FITTED"
    )


def test_fit_result_serializes_pulse_semantics_and_hashes():
    device, physics, config = _base_objects()
    reference = _reference_state(device)
    dataset = _synthetic_dataset()
    spec = _nu0_spec()
    protocol = _protocol()

    result = (
        fit_single_parameter_pulse_memory_window_vs_programming_time(
            dataset,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=spec,
            protocol=protocol,
            reference_state=reference,
            least_squares_config=_strict_solver(),
        )
    )

    payload = result.to_dict()

    assert payload["dataset_hash"] == dataset.dataset_hash()
    assert (
        payload["calibration_specification_hash"]
        == spec.specification_hash()
    )
    assert (
        payload["protocol_hash"]
        == protocol.protocol_hash()
    )
    assert (
        payload["memory_window_definition"]
        == PULSE_MEMORY_WINDOW_DEFINITION
    )
    assert (
        payload["branch_semantics"]
        == PULSE_BRANCH_SEMANTICS
    )
    assert (
        payload["read_semantics"]
        == PULSE_READ_SEMANTICS
    )
    assert (
        payload["reference_state_hash"]
        == result.prediction.reference_state_hash
    )


def test_fit_rejects_wrong_observable_semantics():
    dataset = _synthetic_dataset()

    bad = DeviceObservableDataset(
        independent_variable_name="programming_time",
        independent_variable_unit="s",
        independent_values=dataset.independent_values,
        observable_name="delta_vfb",
        observable_unit="V",
        observed_values=dataset.observed_values,
        metadata=dataset.metadata,
        conditions=dataset.conditions,
    )

    device, physics, config = _base_objects()

    with pytest.raises(
        ValueError,
        match="memory_window",
    ):
        fit_single_parameter_pulse_memory_window_vs_programming_time(
            bad,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_nu0_spec(),
            protocol=_protocol(),
            reference_state=_reference_state(device),
        )


@pytest.mark.parametrize(
    "missing_name",
    [
        "program_voltage",
        "erase_voltage",
        "erase_pulse_width",
        "read_voltage",
        "memory_window_definition",
        "branch_semantics",
        "read_semantics",
    ],
)
def test_fit_requires_explicit_pulse_conditions(
    missing_name,
):
    conditions = tuple(
        condition
        for condition in _conditions()
        if condition.name != missing_name
    )
    dataset = _synthetic_dataset(
        conditions=conditions,
    )
    device, physics, config = _base_objects()

    with pytest.raises(
        ValueError,
        match=missing_name,
    ):
        fit_single_parameter_pulse_memory_window_vs_programming_time(
            dataset,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_nu0_spec(),
            protocol=_protocol(),
            reference_state=_reference_state(device),
        )


@pytest.mark.parametrize(
    ("conditions", "match"),
    [
        (
            _conditions(program_voltage=4.0),
            "program_voltage_V",
        ),
        (
            _conditions(erase_voltage=-4.0),
            "erase_voltage_V",
        ),
        (
            _conditions(erase_time=2.0e-3),
            "erase_time_s",
        ),
        (
            _conditions(read_voltage=1.0),
            "read_voltage_V",
        ),
    ],
)
def test_fit_rejects_protocol_condition_mismatch(
    conditions,
    match,
):
    dataset = _synthetic_dataset(
        conditions=conditions,
    )
    device, physics, config = _base_objects()

    with pytest.raises(
        ValueError,
        match=match,
    ):
        fit_single_parameter_pulse_memory_window_vs_programming_time(
            dataset,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_nu0_spec(),
            protocol=_protocol(),
            reference_state=_reference_state(device),
        )


def test_fit_rejects_wrong_memory_window_definition():
    dataset = _synthetic_dataset(
        conditions=_conditions(
            definition="cv_forward_minus_backward",
        )
    )
    device, physics, config = _base_objects()

    with pytest.raises(
        ValueError,
        match="pulse-defined",
    ):
        fit_single_parameter_pulse_memory_window_vs_programming_time(
            dataset,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_nu0_spec(),
            protocol=_protocol(),
            reference_state=_reference_state(device),
        )


def test_fit_rejects_wrong_branch_semantics():
    dataset = _synthetic_dataset(
        conditions=_conditions(
            branch_semantics="sequential-program-then-erase",
        )
    )
    device, physics, config = _base_objects()

    with pytest.raises(
        ValueError,
        match="independent",
    ):
        fit_single_parameter_pulse_memory_window_vs_programming_time(
            dataset,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_nu0_spec(),
            protocol=_protocol(),
            reference_state=_reference_state(device),
        )


def test_fit_rejects_measurement_frequency_as_unmodeled():
    dataset = _synthetic_dataset(
        conditions=_conditions(
            include_frequency=True,
        )
    )
    device, physics, config = _base_objects()

    with pytest.raises(
        ValueError,
        match="measurement_frequency",
    ):
        fit_single_parameter_pulse_memory_window_vs_programming_time(
            dataset,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_nu0_spec(),
            protocol=_protocol(),
            reference_state=_reference_state(device),
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
        fit_single_parameter_pulse_memory_window_vs_programming_time(
            _synthetic_dataset(),
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=spec,
            protocol=_protocol(),
            reference_state=_reference_state(device),
        )


@pytest.mark.parametrize(
    "times",
    [
        [0.0, 1.0e-3],
        [-1.0e-4, 1.0e-3],
        [float("nan"), 1.0e-3],
    ],
)
def test_prediction_rejects_invalid_times(times):
    device, physics, config = _base_objects()

    with pytest.raises(ValueError):
        predict_pulse_memory_window_vs_programming_time(
            Simulator(
                device,
                physics,
                config,
            ),
            times,
            _protocol(),
            reference_state=_reference_state(device),
        )
