from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("scipy")

from ncmemsim.device_calibration import (
    DeviceCalibrationSpec,
    DeviceFitParameterBinding,
    DeviceFitTarget,
    apply_device_calibration_parameters,
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
from ncmemsim.reference import make_v53_reference_device
from ncmemsim.retention import RetentionConfig
from ncmemsim.retention_fit import (
    DeviceRetentionFractionFitResult,
    RETENTION_FRACTION_OBSERVABLE,
    RETENTION_INITIAL_STATE_SEMANTICS,
    RETENTION_INTERPOLATION_SEMANTICS,
    RETENTION_TRAJECTORY_SEMANTICS,
    RetentionFitProtocol,
    fit_single_parameter_retention_fraction,
    predict_retention_fraction,
)
from ncmemsim.simulator import SimulationConfig, Simulator
from ncmemsim.state import DeviceState


TRUE_PHI_ERASE_EV = 2.10
RETENTION_GATE_VOLTAGE_V = -14.0
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


def _base_objects():
    device = make_v53_reference_device(grid_points=7)
    physics = PhysicsModel.default()
    config = SimulationConfig(
        dwell_time_s=5.0e-3,
        internal_dt_s=1.0e-5,
    )
    return device, physics, config


def _pure_p2_state(device):
    state = DeviceState.empty_for_device(device)
    for fg_state in state.floating_gates:
        fg_state.P0[:] = 0.0
        fg_state.P1[:] = 0.0
        fg_state.P2[:] = 1.0
    state.validate(device)
    return state


def _protocol(
    *,
    gate_voltage=RETENTION_GATE_VOLTAGE_V,
    total_time=3.0e-2,
    stop_at_quasi_equilibrium=False,
    occupancy_integrator="backward_euler",
):
    return RetentionFitProtocol(
        RetentionConfig(
            gate_voltage_V=gate_voltage,
            total_time_s=total_time,
            initial_dt_s=1.0e-7,
            maximum_dt_s=1.0e-3,
            output_points=81,
            stop_at_quasi_equilibrium=stop_at_quasi_equilibrium,
            occupancy_integrator=occupancy_integrator,
        )
    )


def _erase_barrier_spec(*, initial_value=1.90):
    return DeviceCalibrationSpec(
        parameter_set=FitParameterSet(
            (
                FitParameter(
                    name="phi_barrier_erase_eV",
                    initial_value=initial_value,
                    lower_bound=1.80,
                    upper_bound=2.40,
                    unit="eV",
                    description=(
                        "Synthetic effective erase-barrier "
                        "recovery parameter."
                    ),
                ),
            )
        ),
        bindings=(
            DeviceFitParameterBinding(
                parameter_name="phi_barrier_erase_eV",
                target=DeviceFitTarget.FG_PHI_BARRIER_ERASE_EV,
                fg_index=0,
            ),
        ),
        name="synthetic-retention-erase-barrier",
    )


def _strict_solver():
    return LeastSquaresConfig(
        ftol=1.0e-12,
        xtol=1.0e-12,
        gtol=1.0e-12,
        max_nfev=200,
    )


def _conditions(
    *,
    gate_voltage=RETENTION_GATE_VOLTAGE_V,
    include_frequency=False,
):
    conditions = [
        ExperimentalCondition(
            name="retention_gate_voltage",
            value=gate_voltage,
            unit="V",
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


def _truth_prediction():
    device, physics, config = _base_objects()
    truth_context = apply_device_calibration_parameters(
        device,
        physics,
        config,
        _erase_barrier_spec(),
        np.asarray([TRUE_PHI_ERASE_EV], dtype=float),
    )
    initial_state = _pure_p2_state(truth_context.device)
    return predict_retention_fraction(
        Simulator(
            truth_context.device,
            truth_context.physics,
            truth_context.simulation_config,
        ),
        _protocol(),
        initial_state=initial_state,
    )


def _synthetic_dataset(
    *,
    uncertainty=None,
    conditions=None,
    times=None,
):
    prediction = _truth_prediction()
    dataset_times = (
        FIT_TIMES_S
        if times is None
        else np.asarray(times, dtype=float)
    )
    observed = np.interp(
        dataset_times,
        prediction.time_s,
        prediction.predicted_retention_fraction,
    )

    sigma = None
    if uncertainty is not None:
        sigma = np.full(
            dataset_times.size,
            uncertainty,
            dtype=float,
        )

    return DeviceObservableDataset(
        independent_variable_name="time",
        independent_variable_unit="s",
        independent_values=dataset_times,
        observable_name=RETENTION_FRACTION_OBSERVABLE,
        observable_unit=None,
        observed_values=observed,
        observed_uncertainty=sigma,
        metadata=ExperimentalDatasetMetadata(
            dataset_id="synthetic-retention-fraction-vs-time",
            source=(
                "NCMemSim synthetic F4h2c2c "
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


def _fit(dataset=None, *, initial_value=1.90):
    device, physics, config = _base_objects()
    return fit_single_parameter_retention_fraction(
        _synthetic_dataset() if dataset is None else dataset,
        base_device=device,
        base_physics=physics,
        base_simulation_config=config,
        calibration_spec=_erase_barrier_spec(
            initial_value=initial_value
        ),
        protocol=_protocol(),
        initial_state=_pure_p2_state(device),
        least_squares_config=_strict_solver(),
    )


def test_protocol_hash_is_deterministic():
    assert _protocol().protocol_hash() == _protocol().protocol_hash()


def test_protocol_hash_changes_with_gate_voltage():
    assert (
        _protocol().protocol_hash()
        != _protocol(gate_voltage=-13.0).protocol_hash()
    )


def test_protocol_serializes_retention_semantics():
    payload = _protocol().to_dict()
    assert payload["observable"] == RETENTION_FRACTION_OBSERVABLE
    assert (
        payload["initial_state_semantics"]
        == RETENTION_INITIAL_STATE_SEMANTICS
    )
    assert (
        payload["trajectory_semantics"]
        == RETENTION_TRAJECTORY_SEMANTICS
    )
    assert (
        payload["interpolation_semantics"]
        == RETENTION_INTERPOLATION_SEMANTICS
    )


def test_protocol_requires_backward_euler():
    with pytest.raises(ValueError, match="backward_euler"):
        _protocol(occupancy_integrator="explicit_euler")


def test_protocol_rejects_early_quasi_equilibrium_stop():
    with pytest.raises(
        ValueError,
        match="stop_at_quasi_equilibrium=False",
    ):
        _protocol(stop_at_quasi_equilibrium=True)


def test_prediction_requires_caller_supplied_initial_state():
    device, physics, config = _base_objects()
    with pytest.raises(TypeError, match="initial_state"):
        predict_retention_fraction(
            Simulator(device, physics, config),
            _protocol(),
            initial_state=None,
        )


def test_prediction_does_not_mutate_initial_state():
    device, physics, config = _base_objects()
    initial_state = _pure_p2_state(device)
    before = initial_state.copy()

    prediction = predict_retention_fraction(
        Simulator(device, physics, config),
        _protocol(),
        initial_state=initial_state,
    )

    assert prediction.time_s[0] == pytest.approx(0.0)
    assert prediction.time_s[-1] == pytest.approx(
        _protocol().retention_config.total_time_s
    )

    for lhs, rhs in zip(
        initial_state.floating_gates,
        before.floating_gates,
    ):
        assert np.array_equal(lhs.P0, rhs.P0)
        assert np.array_equal(lhs.P1, rhs.P1)
        assert np.array_equal(lhs.P2, rhs.P2)


def test_prediction_arrays_are_read_only():
    device, physics, config = _base_objects()
    prediction = predict_retention_fraction(
        Simulator(device, physics, config),
        _protocol(),
        initial_state=_pure_p2_state(device),
    )
    assert not prediction.time_s.flags.writeable
    assert not prediction.predicted_retention_fraction.flags.writeable


def test_initial_state_hash_is_deterministic_and_sensitive():
    device, physics, config = _base_objects()
    simulator = Simulator(device, physics, config)

    state_a = _pure_p2_state(device)
    state_b = _pure_p2_state(device)

    prediction_a = predict_retention_fraction(
        simulator,
        _protocol(),
        initial_state=state_a,
    )
    prediction_b = predict_retention_fraction(
        simulator,
        _protocol(),
        initial_state=state_b,
    )
    assert (
        prediction_a.initial_state_hash
        == prediction_b.initial_state_hash
    )

    state_b.floating_gates[0].P0[:] = 0.0
    state_b.floating_gates[0].P1[:] = 0.1
    state_b.floating_gates[0].P2[:] = 0.9
    state_b.validate(device)

    prediction_c = predict_retention_fraction(
        simulator,
        _protocol(),
        initial_state=state_b,
    )
    assert (
        prediction_a.initial_state_hash
        != prediction_c.initial_state_hash
    )


@pytest.mark.parametrize(
    "initial_value",
    [1.90, 2.00, 2.20, 2.30],
)
def test_fit_recovers_known_erase_barrier(initial_value):
    result = _fit(initial_value=initial_value)

    assert isinstance(
        result,
        DeviceRetentionFractionFitResult,
    )
    assert result.numerical_result.success

    fitted = result.fitted_parameter_values[
        "phi_barrier_erase_eV"
    ]
    assert fitted == pytest.approx(
        TRUE_PHI_ERASE_EV,
        rel=1.0e-8,
        abs=1.0e-10,
    )
    assert result.objective.root_mean_square_error < 1.0e-10
    assert int(result.numerical_result.active_mask[0]) == 0


def test_fit_uses_uncertainty_weighting():
    result = _fit(
        _synthetic_dataset(uncertainty=1.0e-4)
    )
    assert result.objective.weighted


def test_fit_does_not_mutate_baseline_material_or_initial_state():
    device, physics, config = _base_objects()
    initial_state = _pure_p2_state(device)
    before = initial_state.copy()

    original_barrier = (
        device.floating_gates()[0]
        .nc_material.phi_barrier_erase_eV
    )

    result = fit_single_parameter_retention_fraction(
        _synthetic_dataset(),
        base_device=device,
        base_physics=physics,
        base_simulation_config=config,
        calibration_spec=_erase_barrier_spec(),
        protocol=_protocol(),
        initial_state=initial_state,
        least_squares_config=_strict_solver(),
    )

    assert (
        device.floating_gates()[0]
        .nc_material.phi_barrier_erase_eV
        == pytest.approx(original_barrier)
    )
    assert (
        result.fitted_context.device
        .floating_gates()[0]
        .nc_material.phi_barrier_erase_eV
        == pytest.approx(TRUE_PHI_ERASE_EV)
    )

    fitted_material = (
        result.fitted_context.device
        .floating_gates()[0]
        .nc_material
    )
    if "phi_barrier_erase_eV" in fitted_material.properties:
        assert (
            fitted_material.properties[
                "phi_barrier_erase_eV"
            ].value
            == pytest.approx(TRUE_PHI_ERASE_EV)
        )

    for lhs, rhs in zip(
        initial_state.floating_gates,
        before.floating_gates,
    ):
        assert np.array_equal(lhs.P0, rhs.P0)
        assert np.array_equal(lhs.P1, rhs.P1)
        assert np.array_equal(lhs.P2, rhs.P2)


def test_fit_result_is_fitted_not_calibrated():
    result = _fit()
    assert result.scientific_status == "FITTED"
    assert result.to_dict()["scientific_status"] == "FITTED"


def test_fit_result_serializes_hashes_and_retention_semantics():
    device, physics, config = _base_objects()
    dataset = _synthetic_dataset()
    spec = _erase_barrier_spec()
    protocol = _protocol()
    initial_state = _pure_p2_state(device)

    result = fit_single_parameter_retention_fraction(
        dataset,
        base_device=device,
        base_physics=physics,
        base_simulation_config=config,
        calibration_spec=spec,
        protocol=protocol,
        initial_state=initial_state,
        least_squares_config=_strict_solver(),
    )

    payload = result.to_dict()
    assert payload["dataset_hash"] == dataset.dataset_hash()
    assert (
        payload["calibration_specification_hash"]
        == spec.specification_hash()
    )
    assert payload["protocol_hash"] == protocol.protocol_hash()
    assert payload["observable"] == RETENTION_FRACTION_OBSERVABLE
    assert (
        payload["initial_state_hash"]
        == result.prediction.initial_state_hash
    )
    assert (
        payload["protocol"]["trajectory_semantics"]
        == RETENTION_TRAJECTORY_SEMANTICS
    )
    assert (
        payload["protocol"]["interpolation_semantics"]
        == RETENTION_INTERPOLATION_SEMANTICS
    )


def test_fit_rejects_wrong_observable_semantics():
    dataset = _synthetic_dataset()
    bad = DeviceObservableDataset(
        independent_variable_name="time",
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
        match="total_charge_retention_fraction",
    ):
        fit_single_parameter_retention_fraction(
            bad,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_erase_barrier_spec(),
            protocol=_protocol(),
            initial_state=_pure_p2_state(device),
        )


def test_fit_requires_retention_gate_voltage_condition():
    dataset = _synthetic_dataset(conditions=())
    device, physics, config = _base_objects()

    with pytest.raises(
        ValueError,
        match="retention_gate_voltage",
    ):
        fit_single_parameter_retention_fraction(
            dataset,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_erase_barrier_spec(),
            protocol=_protocol(),
            initial_state=_pure_p2_state(device),
        )


def test_fit_rejects_retention_gate_voltage_mismatch():
    dataset = _synthetic_dataset(
        conditions=_conditions(gate_voltage=-13.0)
    )
    device, physics, config = _base_objects()

    with pytest.raises(
        ValueError,
        match="retention_gate_voltage",
    ):
        fit_single_parameter_retention_fraction(
            dataset,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_erase_barrier_spec(),
            protocol=_protocol(),
            initial_state=_pure_p2_state(device),
        )


def test_fit_rejects_unmodeled_dataset_conditions():
    dataset = _synthetic_dataset(
        conditions=_conditions(include_frequency=True)
    )
    device, physics, config = _base_objects()

    with pytest.raises(
        ValueError,
        match="measurement_frequency",
    ):
        fit_single_parameter_retention_fraction(
            dataset,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_erase_barrier_spec(),
            protocol=_protocol(),
            initial_state=_pure_p2_state(device),
        )


def test_fit_rejects_multi_parameter_spec():
    device, physics, config = _base_objects()
    spec = DeviceCalibrationSpec(
        parameter_set=FitParameterSet(
            (
                FitParameter(
                    name="erase_barrier",
                    initial_value=1.9,
                    lower_bound=1.8,
                    upper_bound=2.4,
                ),
                FitParameter(
                    name="nu1_Hz",
                    initial_value=1.0e10,
                    lower_bound=1.0e9,
                    upper_bound=1.0e11,
                ),
            )
        ),
        bindings=(
            DeviceFitParameterBinding(
                "erase_barrier",
                DeviceFitTarget.FG_PHI_BARRIER_ERASE_EV,
                fg_index=0,
            ),
            DeviceFitParameterBinding(
                "nu1_Hz",
                DeviceFitTarget.KINETICS_NU1_HZ,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="exactly one free parameter",
    ):
        fit_single_parameter_retention_fraction(
            _synthetic_dataset(),
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=spec,
            protocol=_protocol(),
            initial_state=_pure_p2_state(device),
        )


def test_fit_rejects_extrapolation_beyond_protocol_domain():
    dataset = _synthetic_dataset(
        times=np.asarray(
            [1.0e-4, 3.0e-2, 4.0e-2],
            dtype=float,
        ),
    )
    device, physics, config = _base_objects()

    with pytest.raises(
        ValueError,
        match="extrapolation is not allowed",
    ):
        fit_single_parameter_retention_fraction(
            dataset,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_erase_barrier_spec(),
            protocol=_protocol(total_time=3.0e-2),
            initial_state=_pure_p2_state(device),
        )
