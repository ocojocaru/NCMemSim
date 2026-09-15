from __future__ import annotations

import numpy as np
import pytest

from ncmemsim.device_objectives import (
    DeviceObjectiveEvaluation,
    evaluate_cv_objective,
    evaluate_memory_window_vs_program_voltage_objective,
    evaluate_memory_window_vs_programming_time_objective,
    evaluate_retention_objective,
    interpolate_without_extrapolation,
)
from ncmemsim.experimental import (
    DeviceObservableDataset,
    ExperimentalCondition,
    ExperimentalDatasetMetadata,
)
from ncmemsim.retention import RetentionResult
from ncmemsim.simulator import CVResult, SweepResult


def _metadata(
    dataset_id: str = "device-objective-test",
) -> ExperimentalDatasetMetadata:
    return ExperimentalDatasetMetadata(
        dataset_id=dataset_id,
        source="Synthetic device-objective test data",
        sample_id="sample-device-objective",
        temperature_K=300.0,
    )


def _dataset(
    *,
    x_name: str,
    x_unit: str | None,
    x,
    y_name: str,
    y_unit: str | None,
    y,
    uncertainty=None,
    conditions=(),
    dataset_id: str = "device-objective-test",
) -> DeviceObservableDataset:
    return DeviceObservableDataset(
        independent_variable_name=x_name,
        independent_variable_unit=x_unit,
        independent_values=np.asarray(x, dtype=float),
        observable_name=y_name,
        observable_unit=y_unit,
        observed_values=np.asarray(y, dtype=float),
        observed_uncertainty=(
            None
            if uncertainty is None
            else np.asarray(uncertainty, dtype=float)
        ),
        metadata=_metadata(dataset_id),
        conditions=tuple(conditions),
    )


def _sweep(
    voltages,
    capacitance,
) -> SweepResult:
    voltages = np.asarray(voltages, dtype=float)
    capacitance = np.asarray(capacitance, dtype=float)
    n = voltages.size
    zeros = np.zeros(n, dtype=float)

    return SweepResult(
        voltages_V=voltages,
        capacitance_F_m2=capacitance,
        qfg_C_m2=zeros.copy(),
        vfb_V=zeros.copy(),
        veff_V=zeros.copy(),
        mean_occupation=zeros.copy(),
        field_mean_V_m=zeros.copy(),
        tprog_mean=zeros.copy(),
        terase_mean=zeros.copy(),
        final_state=object(),
    )


def _cv(
    *,
    forward_x=(-1.0, 0.0, 1.0),
    forward_c=(1.0, 2.0, 3.0),
    backward_x=(1.0, 0.0, -1.0),
    backward_c=(4.0, 5.0, 6.0),
    memory_window=1.0,
) -> CVResult:
    return CVResult(
        forward=_sweep(forward_x, forward_c),
        backward=_sweep(backward_x, backward_c),
        memory_window_V=float(memory_window),
        vmid_forward_V=0.0,
        vmid_backward_V=float(memory_window),
    )


def _retention(
    *,
    time=(0.0, 10.0, 100.0),
    qfg=(2.0, 1.8, 1.6),
    delta_vfb=(2.0, 1.8, 1.6),
) -> RetentionResult:
    time = np.asarray(time, dtype=float)
    qfg = np.asarray(qfg, dtype=float)
    delta_vfb = np.asarray(delta_vfb, dtype=float)
    n = time.size

    return RetentionResult(
        time_s=time,
        qfg_C_m2=qfg,
        qfg_by_fg_C_m2=qfg[:, None],
        mean_occupation_by_fg=np.zeros((n, 1)),
        delta_vfb_V=delta_vfb,
        delta_vfb_by_fg_V=delta_vfb[:, None],
        local_field_by_fg_V_m=np.zeros((n, 1)),
        local_potential_by_fg_V=np.zeros((n, 1)),
        inter_fg_flux_by_link_m2_s=np.zeros((n, 0)),
        transport_transmission_by_link=np.zeros((n, 0)),
        transport_link_ids=(),
        charge_rate_C_m2_s=np.zeros(n),
        final_state=object(),
        quasi_equilibrium_reached=False,
        quasi_equilibrium_time_s=None,
    )


def test_interpolation_exact_ascending_grid_uses_no_interpolation():
    predicted, used = interpolate_without_extrapolation(
        [0.0, 1.0, 2.0],
        [0.0, 1.0, 2.0],
        [10.0, 20.0, 30.0],
    )

    assert np.allclose(predicted, [10.0, 20.0, 30.0])
    assert used is False
    assert predicted.flags.writeable is False


def test_interpolation_exact_descending_grid_uses_no_interpolation():
    predicted, used = interpolate_without_extrapolation(
        [2.0, 1.0, 0.0],
        [2.0, 1.0, 0.0],
        [30.0, 20.0, 10.0],
    )

    assert np.allclose(predicted, [30.0, 20.0, 10.0])
    assert used is False


def test_interpolation_preserves_experimental_order():
    predicted, used = interpolate_without_extrapolation(
        [1.5, 0.5],
        [0.0, 1.0, 2.0],
        [0.0, 10.0, 20.0],
    )

    assert np.allclose(predicted, [15.0, 5.0])
    assert used is True


@pytest.mark.parametrize(
    "query",
    [
        [-0.1, 1.0],
        [1.0, 2.1],
    ],
)
def test_interpolation_rejects_extrapolation(query):
    with pytest.raises(
        ValueError,
        match="extrapolation is not allowed",
    ):
        interpolate_without_extrapolation(
            query,
            [0.0, 1.0, 2.0],
            [0.0, 10.0, 20.0],
        )


@pytest.mark.parametrize(
    "simulation_x",
    [
        [0.0, 1.0, 0.5],
        [0.0, 1.0, 1.0],
    ],
)
def test_interpolation_requires_strictly_monotonic_simulation_grid(
    simulation_x,
):
    with pytest.raises(
        ValueError,
        match="strictly monotonic",
    ):
        interpolate_without_extrapolation(
            [0.25, 0.75],
            simulation_x,
            [0.0, 10.0, 20.0],
        )


def test_cv_objective_selects_forward_branch():
    dataset = _dataset(
        x_name="gate_voltage",
        x_unit="V",
        x=[-1.0, 0.0, 1.0],
        y_name="capacitance",
        y_unit="F/m^2",
        y=[1.1, 1.9, 3.2],
        conditions=(
            ExperimentalCondition(
                name="sweep_direction",
                value="forward",
            ),
        ),
    )

    evaluation = evaluate_cv_objective(
        dataset,
        _cv(),
    )

    assert isinstance(
        evaluation,
        DeviceObjectiveEvaluation,
    )
    assert np.allclose(
        evaluation.predicted_values,
        [1.0, 2.0, 3.0],
    )
    assert np.allclose(
        evaluation.objective.residuals,
        [-0.1, 0.1, -0.2],
    )
    assert evaluation.interpolation_used is False


def test_cv_objective_selects_backward_branch_and_interpolates():
    dataset = _dataset(
        x_name="gate_voltage",
        x_unit="V",
        x=[0.5, -0.5],
        y_name="capacitance",
        y_unit="F/m^2",
        y=[4.6, 5.4],
        conditions=(
            ExperimentalCondition(
                name="sweep_direction",
                value="backward",
            ),
        ),
    )

    evaluation = evaluate_cv_objective(
        dataset,
        _cv(),
    )

    assert np.allclose(
        evaluation.predicted_values,
        [4.5, 5.5],
    )
    assert evaluation.interpolation_used is True


def test_cv_objective_uses_dataset_uncertainty():
    dataset = _dataset(
        x_name="gate_voltage",
        x_unit="V",
        x=[-1.0, 1.0],
        y_name="capacitance",
        y_unit="F/m^2",
        y=[0.5, 2.0],
        uncertainty=[0.5, 0.5],
        conditions=(
            ExperimentalCondition(
                name="sweep_direction",
                value="forward",
            ),
        ),
    )

    evaluation = evaluate_cv_objective(
        dataset,
        _cv(),
    )

    assert np.allclose(
        evaluation.objective.residuals,
        [0.5, 1.0],
    )
    assert np.allclose(
        evaluation.objective.objective_residuals,
        [1.0, 2.0],
    )


def test_cv_measurement_frequency_is_reported_as_unmodeled():
    dataset = _dataset(
        x_name="gate_voltage",
        x_unit="V",
        x=[-1.0, 1.0],
        y_name="capacitance",
        y_unit="F/m^2",
        y=[1.0, 3.0],
        conditions=(
            ExperimentalCondition(
                name="sweep_direction",
                value="forward",
            ),
            ExperimentalCondition(
                name="measurement_frequency",
                value=1.0e6,
                unit="Hz",
            ),
        ),
    )

    evaluation = evaluate_cv_objective(
        dataset,
        _cv(),
    )

    assert evaluation.unmodeled_condition_names == (
        "measurement_frequency",
    )


@pytest.mark.parametrize(
    ("x_name", "x_unit", "y_name", "y_unit"),
    [
        ("voltage", "V", "capacitance", "F/m^2"),
        ("gate_voltage", "mV", "capacitance", "F/m^2"),
        ("gate_voltage", "V", "conductance", "F/m^2"),
        ("gate_voltage", "V", "capacitance", "F"),
    ],
)
def test_cv_objective_rejects_wrong_schema(
    x_name,
    x_unit,
    y_name,
    y_unit,
):
    dataset = _dataset(
        x_name=x_name,
        x_unit=x_unit,
        x=[-1.0, 1.0],
        y_name=y_name,
        y_unit=y_unit,
        y=[1.0, 3.0],
        conditions=(
            ExperimentalCondition(
                name="sweep_direction",
                value="forward",
            ),
        ),
    )

    with pytest.raises(ValueError):
        evaluate_cv_objective(
            dataset,
            _cv(),
        )


def test_cv_objective_requires_direction_condition():
    dataset = _dataset(
        x_name="gate_voltage",
        x_unit="V",
        x=[-1.0, 1.0],
        y_name="capacitance",
        y_unit="F/m^2",
        y=[1.0, 3.0],
    )

    with pytest.raises(
        ValueError,
        match="sweep_direction",
    ):
        evaluate_cv_objective(
            dataset,
            _cv(),
        )


def test_cv_objective_requires_cv_result():
    dataset = _dataset(
        x_name="gate_voltage",
        x_unit="V",
        x=[-1.0, 1.0],
        y_name="capacitance",
        y_unit="F/m^2",
        y=[1.0, 3.0],
        conditions=(
            ExperimentalCondition(
                name="sweep_direction",
                value="forward",
            ),
        ),
    )

    with pytest.raises(TypeError, match="CVResult"):
        evaluate_cv_objective(
            dataset,
            object(),
        )


def test_memory_window_vs_program_voltage_objective():
    dataset = _dataset(
        x_name="program_voltage",
        x_unit="V",
        x=[2.5, 3.5],
        y_name="memory_window",
        y_unit="V",
        y=[0.7, 1.7],
        conditions=(
            ExperimentalCondition(
                name="program_pulse_width",
                value=1.0e-3,
                unit="s",
            ),
        ),
    )

    evaluation = (
        evaluate_memory_window_vs_program_voltage_objective(
            dataset,
            program_voltages_V=[2.0, 3.0, 4.0],
            cv_results=[
                _cv(memory_window=0.2),
                _cv(memory_window=1.0),
                _cv(memory_window=2.0),
            ],
            program_pulse_width_s=1.0e-3,
        )
    )

    assert np.allclose(
        evaluation.predicted_values,
        [0.6, 1.5],
    )
    assert evaluation.interpolation_used is True


def test_memory_window_program_voltage_checks_fixed_pulse_width():
    dataset = _dataset(
        x_name="program_voltage",
        x_unit="V",
        x=[2.0, 4.0],
        y_name="memory_window",
        y_unit="V",
        y=[0.2, 2.0],
        conditions=(
            ExperimentalCondition(
                name="program_pulse_width",
                value=1.0e-3,
                unit="s",
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="does not match",
    ):
        evaluate_memory_window_vs_program_voltage_objective(
            dataset,
            program_voltages_V=[2.0, 4.0],
            cv_results=[
                _cv(memory_window=0.2),
                _cv(memory_window=2.0),
            ],
            program_pulse_width_s=2.0e-3,
        )


def test_memory_window_vs_programming_time_objective():
    dataset = _dataset(
        x_name="programming_time",
        x_unit="s",
        x=[2.0e-3, 5.0e-3],
        y_name="memory_window",
        y_unit="V",
        y=[0.7, 1.2],
        conditions=(
            ExperimentalCondition(
                name="program_voltage",
                value=4.0,
                unit="V",
            ),
        ),
    )

    evaluation = (
        evaluate_memory_window_vs_programming_time_objective(
            dataset,
            programming_times_s=[
                1.0e-3,
                3.0e-3,
                1.0e-2,
            ],
            cv_results=[
                _cv(memory_window=0.4),
                _cv(memory_window=0.8),
                _cv(memory_window=1.5),
            ],
            program_voltage_V=4.0,
        )
    )

    assert evaluation.predicted_values.shape == (2,)
    assert evaluation.interpolation_used is True


@pytest.mark.parametrize(
    "times",
    [
        [0.0, 1.0e-3],
        [-1.0e-3, 1.0e-3],
        [float("nan"), 1.0e-3],
    ],
)
def test_memory_window_programming_time_requires_positive_simulation_times(
    times,
):
    dataset = _dataset(
        x_name="programming_time",
        x_unit="s",
        x=[1.0e-3, 2.0e-3],
        y_name="memory_window",
        y_unit="V",
        y=[0.5, 0.7],
        conditions=(
            ExperimentalCondition(
                name="program_voltage",
                value=4.0,
                unit="V",
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="strictly positive",
    ):
        evaluate_memory_window_vs_programming_time_objective(
            dataset,
            programming_times_s=times,
            cv_results=[
                _cv(memory_window=0.5),
                _cv(memory_window=0.7),
            ],
            program_voltage_V=4.0,
        )


def test_memory_window_series_requires_matching_lengths():
    dataset = _dataset(
        x_name="program_voltage",
        x_unit="V",
        x=[2.0, 3.0],
        y_name="memory_window",
        y_unit="V",
        y=[0.2, 1.0],
        conditions=(
            ExperimentalCondition(
                name="program_pulse_width",
                value=1.0e-3,
                unit="s",
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="matching lengths",
    ):
        evaluate_memory_window_vs_program_voltage_objective(
            dataset,
            program_voltages_V=[2.0, 3.0, 4.0],
            cv_results=[
                _cv(memory_window=0.2),
                _cv(memory_window=1.0),
            ],
            program_pulse_width_s=1.0e-3,
        )


def test_memory_window_series_requires_cv_results():
    dataset = _dataset(
        x_name="program_voltage",
        x_unit="V",
        x=[2.0, 3.0],
        y_name="memory_window",
        y_unit="V",
        y=[0.2, 1.0],
        conditions=(
            ExperimentalCondition(
                name="program_pulse_width",
                value=1.0e-3,
                unit="s",
            ),
        ),
    )

    with pytest.raises(TypeError, match="CVResult"):
        evaluate_memory_window_vs_program_voltage_objective(
            dataset,
            program_voltages_V=[2.0, 3.0],
            cv_results=[
                _cv(memory_window=0.2),
                object(),
            ],
            program_pulse_width_s=1.0e-3,
        )


def test_retention_delta_vfb_objective():
    dataset = _dataset(
        x_name="time",
        x_unit="s",
        x=[0.0, 50.0, 100.0],
        y_name="delta_vfb",
        y_unit="V",
        y=[2.0, 1.65, 1.55],
        conditions=(
            ExperimentalCondition(
                name="retention_gate_voltage",
                value=0.0,
                unit="V",
            ),
        ),
    )

    evaluation = evaluate_retention_objective(
        dataset,
        _retention(),
        retention_gate_voltage_V=0.0,
    )

    assert np.allclose(
        evaluation.predicted_values,
        [2.0, 1.7111111111111112, 1.6],
    )
    assert np.allclose(
        evaluation.objective.residuals,
        [0.0, 0.061111111111111116, 0.05],
    )


def test_retention_charge_fraction_uses_result_property():
    dataset = _dataset(
        x_name="time",
        x_unit="s",
        x=[0.0, 10.0, 100.0],
        y_name="total_charge_retention_fraction",
        y_unit=None,
        y=[1.0, 0.91, 0.79],
        conditions=(
            ExperimentalCondition(
                name="retention_gate_voltage",
                value=0.0,
                unit="V",
            ),
        ),
    )

    evaluation = evaluate_retention_objective(
        dataset,
        _retention(
            qfg=[2.0, 1.8, 1.6],
        ),
        retention_gate_voltage_V=0.0,
    )

    assert np.allclose(
        evaluation.predicted_values,
        [1.0, 0.9, 0.8],
    )


def test_retention_checks_gate_voltage_condition():
    dataset = _dataset(
        x_name="time",
        x_unit="s",
        x=[0.0, 100.0],
        y_name="delta_vfb",
        y_unit="V",
        y=[2.0, 1.6],
        conditions=(
            ExperimentalCondition(
                name="retention_gate_voltage",
                value=0.0,
                unit="V",
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="does not match",
    ):
        evaluate_retention_objective(
            dataset,
            _retention(),
            retention_gate_voltage_V=1.0,
        )


def test_retention_frequency_is_reported_as_unmodeled():
    dataset = _dataset(
        x_name="time",
        x_unit="s",
        x=[0.0, 100.0],
        y_name="delta_vfb",
        y_unit="V",
        y=[2.0, 1.6],
        conditions=(
            ExperimentalCondition(
                name="retention_gate_voltage",
                value=0.0,
                unit="V",
            ),
            ExperimentalCondition(
                name="measurement_frequency",
                value=1.0e6,
                unit="Hz",
            ),
        ),
    )

    evaluation = evaluate_retention_objective(
        dataset,
        _retention(),
        retention_gate_voltage_V=0.0,
    )

    assert evaluation.unmodeled_condition_names == (
        "measurement_frequency",
    )


@pytest.mark.parametrize(
    ("observable", "unit"),
    [
        ("charge_loss_fraction", None),
        ("delta_vfb", "mV"),
        ("total_charge_retention_fraction", "1"),
    ],
)
def test_retention_rejects_unsupported_observable_or_unit(
    observable,
    unit,
):
    dataset = _dataset(
        x_name="time",
        x_unit="s",
        x=[0.0, 100.0],
        y_name=observable,
        y_unit=unit,
        y=[1.0, 0.8],
        conditions=(
            ExperimentalCondition(
                name="retention_gate_voltage",
                value=0.0,
                unit="V",
            ),
        ),
    )

    with pytest.raises(ValueError):
        evaluate_retention_objective(
            dataset,
            _retention(),
            retention_gate_voltage_V=0.0,
        )


def test_retention_rejects_extrapolation():
    dataset = _dataset(
        x_name="time",
        x_unit="s",
        x=[0.0, 200.0],
        y_name="delta_vfb",
        y_unit="V",
        y=[2.0, 1.4],
        conditions=(
            ExperimentalCondition(
                name="retention_gate_voltage",
                value=0.0,
                unit="V",
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="extrapolation is not allowed",
    ):
        evaluate_retention_objective(
            dataset,
            _retention(),
            retention_gate_voltage_V=0.0,
        )


def test_device_objective_to_dict_is_reproducible():
    dataset = _dataset(
        x_name="gate_voltage",
        x_unit="V",
        x=[-1.0, 1.0],
        y_name="capacitance",
        y_unit="F/m^2",
        y=[1.0, 3.0],
        conditions=(
            ExperimentalCondition(
                name="sweep_direction",
                value="forward",
            ),
        ),
        dataset_id="cv-repro",
    )

    evaluation = evaluate_cv_objective(
        dataset,
        _cv(),
    )
    payload = evaluation.to_dict()

    assert payload["dataset_id"] == "cv-repro"
    assert payload["dataset_hash"] == dataset.dataset_hash()
    assert payload["independent_variable_name"] == "gate_voltage"
    assert payload["observable_name"] == "capacitance"
    assert payload["predicted_values"] == [1.0, 3.0]
    assert payload["simulation_point_count"] == 3
    assert payload["interpolation_used"] is True
    assert payload["unmodeled_condition_names"] == []
    assert "objective" in payload


def test_device_objective_prediction_array_is_read_only():
    dataset = _dataset(
        x_name="gate_voltage",
        x_unit="V",
        x=[-1.0, 1.0],
        y_name="capacitance",
        y_unit="F/m^2",
        y=[1.0, 3.0],
        conditions=(
            ExperimentalCondition(
                name="sweep_direction",
                value="forward",
            ),
        ),
    )

    evaluation = evaluate_cv_objective(
        dataset,
        _cv(),
    )

    with pytest.raises(ValueError):
        evaluation.predicted_values[0] = 99.0
