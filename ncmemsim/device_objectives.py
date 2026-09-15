from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np

from .experimental import (
    DeviceObservableDataset,
    ExperimentalCondition,
)
from .fitting import (
    ObjectiveEvaluation,
    evaluate_least_squares_objective,
)
from .retention import RetentionResult
from .simulator import CVResult


@dataclass(frozen=True)
class DeviceObjectiveEvaluation:
    """
    Reproducible comparison between one experimental device dataset and
    simulator predictions evaluated on the experimental grid.

    ``predicted_values`` follows the ordering of the experimental dataset.
    ``objective`` is the generic NCMemSim least-squares evaluation, including
    uncertainty weighting when the dataset provides pointwise uncertainty.

    ``unmodeled_condition_names`` records experimental conditions preserved in
    the dataset but not represented by the simulator output used by this
    adapter. For example, measurement frequency is metadata for the current
    quasi-static device model rather than a simulated degree of freedom.
    """

    dataset_id: str
    dataset_hash: str
    independent_variable_name: str
    observable_name: str
    predicted_values: np.ndarray
    objective: ObjectiveEvaluation
    simulation_point_count: int
    interpolation_used: bool
    unmodeled_condition_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        predicted = np.asarray(
            self.predicted_values,
            dtype=float,
        )

        if predicted.ndim != 1:
            raise ValueError(
                "predicted_values must be one-dimensional."
            )
        if not np.all(np.isfinite(predicted)):
            raise ValueError(
                "predicted_values must contain only finite values."
            )
        if self.simulation_point_count < 2:
            raise ValueError(
                "simulation_point_count must be at least two."
            )

        predicted = np.array(
            predicted,
            dtype=float,
            copy=True,
        )
        predicted.setflags(write=False)

        object.__setattr__(
            self,
            "predicted_values",
            predicted,
        )
        object.__setattr__(
            self,
            "unmodeled_condition_names",
            tuple(sorted(self.unmodeled_condition_names)),
        )

    def to_dict(self) -> dict:
        return {
            "dataset_id": self.dataset_id,
            "dataset_hash": self.dataset_hash,
            "independent_variable_name": (
                self.independent_variable_name
            ),
            "observable_name": self.observable_name,
            "predicted_values": self.predicted_values.tolist(),
            "objective": self.objective.to_dict(),
            "simulation_point_count": self.simulation_point_count,
            "interpolation_used": self.interpolation_used,
            "unmodeled_condition_names": list(
                self.unmodeled_condition_names
            ),
        }


def _require_device_dataset(
    dataset: DeviceObservableDataset,
) -> None:
    if not isinstance(
        dataset,
        DeviceObservableDataset,
    ):
        raise TypeError(
            "dataset must be a DeviceObservableDataset instance."
        )


def _require_schema(
    dataset: DeviceObservableDataset,
    *,
    independent_variable_name: str,
    independent_variable_unit: str | None,
    observable_name: str,
    observable_unit: str | None,
) -> None:
    _require_device_dataset(dataset)

    if (
        dataset.independent_variable_name
        != independent_variable_name
    ):
        raise ValueError(
            "Unsupported independent variable. "
            f"Expected {independent_variable_name!r}, got "
            f"{dataset.independent_variable_name!r}."
        )

    if (
        dataset.independent_variable_unit
        != independent_variable_unit
    ):
        raise ValueError(
            "Unsupported independent-variable unit. "
            f"Expected {independent_variable_unit!r}, got "
            f"{dataset.independent_variable_unit!r}."
        )

    if dataset.observable_name != observable_name:
        raise ValueError(
            "Unsupported observable. "
            f"Expected {observable_name!r}, got "
            f"{dataset.observable_name!r}."
        )

    if dataset.observable_unit != observable_unit:
        raise ValueError(
            "Unsupported observable unit. "
            f"Expected {observable_unit!r}, got "
            f"{dataset.observable_unit!r}."
        )


def _condition(
    dataset: DeviceObservableDataset,
    name: str,
) -> ExperimentalCondition:
    matches = tuple(
        condition
        for condition in dataset.conditions
        if condition.name == name
    )

    if len(matches) != 1:
        raise ValueError(
            f"Dataset must contain exactly one {name!r} condition."
        )

    return matches[0]


def _require_string_condition(
    dataset: DeviceObservableDataset,
    *,
    name: str,
    expected_values: tuple[str, ...],
) -> str:
    condition = _condition(dataset, name)

    if condition.unit is not None:
        raise ValueError(
            f"Condition {name!r} must be unitless."
        )

    value = condition.value

    if not isinstance(value, str):
        raise ValueError(
            f"Condition {name!r} must contain a string value."
        )

    if value not in expected_values:
        raise ValueError(
            f"Unsupported {name!r} value {value!r}. "
            f"Expected one of {expected_values!r}."
        )

    return value


def _require_numeric_condition(
    dataset: DeviceObservableDataset,
    *,
    name: str,
    expected_unit: str,
    actual_value: float,
    actual_value_name: str,
) -> None:
    condition = _condition(dataset, name)

    if condition.unit != expected_unit:
        raise ValueError(
            f"Condition {name!r} must use unit "
            f"{expected_unit!r}."
        )

    if isinstance(condition.value, bool) or not isinstance(
        condition.value,
        (int, float),
    ):
        raise ValueError(
            f"Condition {name!r} must contain a numeric value."
        )

    expected = float(condition.value)
    actual = float(actual_value)

    if not math.isfinite(actual):
        raise ValueError(
            f"{actual_value_name} must be finite."
        )

    tolerance = (
        1.0e-12
        * max(1.0, abs(expected), abs(actual))
    )

    if not math.isclose(
        expected,
        actual,
        rel_tol=1.0e-12,
        abs_tol=tolerance,
    ):
        raise ValueError(
            f"Dataset condition {name!r}={expected!r} "
            f"does not match {actual_value_name}={actual!r}."
        )


def _unmodeled_conditions(
    dataset: DeviceObservableDataset,
    *,
    consumed: set[str],
) -> tuple[str, ...]:
    return tuple(
        condition.name
        for condition in dataset.conditions
        if condition.name not in consumed
    )


def _as_simulation_series(
    independent_values: np.ndarray | Sequence[float],
    observable_values: np.ndarray | Sequence[float],
) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(
        independent_values,
        dtype=float,
    )
    y = np.asarray(
        observable_values,
        dtype=float,
    )

    if x.ndim != 1 or y.ndim != 1:
        raise ValueError(
            "Simulation independent and observable arrays "
            "must be one-dimensional."
        )

    if x.size < 2:
        raise ValueError(
            "Simulation series must contain at least two points."
        )

    if x.shape != y.shape:
        raise ValueError(
            "Simulation independent and observable arrays "
            "must have matching shapes."
        )

    if not np.all(np.isfinite(x)):
        raise ValueError(
            "Simulation independent values must be finite."
        )

    if not np.all(np.isfinite(y)):
        raise ValueError(
            "Simulation observable values must be finite."
        )

    dx = np.diff(x)

    if np.all(dx > 0.0):
        return (
            np.array(x, dtype=float, copy=True),
            np.array(y, dtype=float, copy=True),
        )

    if np.all(dx < 0.0):
        return (
            np.array(x[::-1], dtype=float, copy=True),
            np.array(y[::-1], dtype=float, copy=True),
        )

    raise ValueError(
        "Simulation independent values must be strictly "
        "monotonic for interpolation."
    )


def interpolate_without_extrapolation(
    experimental_x: np.ndarray | Sequence[float],
    simulation_x: np.ndarray | Sequence[float],
    simulation_y: np.ndarray | Sequence[float],
) -> tuple[np.ndarray, bool]:
    """
    Interpolate a simulator series onto an experimental grid.

    The simulation grid may be strictly increasing or strictly decreasing.
    Experimental ordering is preserved. Extrapolation is never performed.
    A tiny floating-point tolerance is accepted at the simulation-domain
    boundaries and clipped back to the exact boundary value.

    Returns ``(predicted_values, interpolation_used)``.
    """

    query = np.asarray(
        experimental_x,
        dtype=float,
    )

    if query.ndim != 1:
        raise ValueError(
            "experimental_x must be one-dimensional."
        )

    if query.size < 2:
        raise ValueError(
            "experimental_x must contain at least two points."
        )

    if not np.all(np.isfinite(query)):
        raise ValueError(
            "experimental_x must contain only finite values."
        )

    x, y = _as_simulation_series(
        simulation_x,
        simulation_y,
    )

    lower = float(x[0])
    upper = float(x[-1])
    tolerance = (
        64.0
        * np.finfo(float).eps
        * max(1.0, abs(lower), abs(upper))
    )

    if np.any(query < lower - tolerance) or np.any(
        query > upper + tolerance
    ):
        raise ValueError(
            "Experimental grid extends outside the "
            "simulation domain; extrapolation is not allowed."
        )

    clipped_query = np.clip(
        query,
        lower,
        upper,
    )

    predicted = np.interp(
        clipped_query,
        x,
        y,
    )
    predicted = np.array(
        predicted,
        dtype=float,
        copy=True,
    )
    predicted.setflags(write=False)

    original_x = np.asarray(
        simulation_x,
        dtype=float,
    )
    same_grid = (
        query.shape == original_x.shape
        and np.allclose(
            query,
            original_x,
            rtol=0.0,
            atol=tolerance,
        )
    )

    return predicted, not same_grid


def _build_evaluation(
    dataset: DeviceObservableDataset,
    *,
    simulation_x: np.ndarray | Sequence[float],
    simulation_y: np.ndarray | Sequence[float],
    consumed_conditions: set[str],
) -> DeviceObjectiveEvaluation:
    predicted, interpolation_used = (
        interpolate_without_extrapolation(
            dataset.independent_values,
            simulation_x,
            simulation_y,
        )
    )

    objective = evaluate_least_squares_objective(
        observed=dataset.observed_values,
        predicted=predicted,
        uncertainty=dataset.observed_uncertainty,
    )

    return DeviceObjectiveEvaluation(
        dataset_id=dataset.metadata.dataset_id,
        dataset_hash=dataset.dataset_hash(),
        independent_variable_name=(
            dataset.independent_variable_name
        ),
        observable_name=dataset.observable_name,
        predicted_values=predicted,
        objective=objective,
        simulation_point_count=len(
            np.asarray(simulation_x)
        ),
        interpolation_used=interpolation_used,
        unmodeled_condition_names=(
            _unmodeled_conditions(
                dataset,
                consumed=consumed_conditions,
            )
        ),
    )


def evaluate_cv_objective(
    dataset: DeviceObservableDataset,
    result: CVResult,
) -> DeviceObjectiveEvaluation:
    """
    Compare one experimental C-V sweep against a ``CVResult``.

    The dataset's ``sweep_direction`` condition selects ``result.forward`` or
    ``result.backward``. Capacitance is interpolated onto the experimental
    gate-voltage grid without extrapolation.
    """

    _require_schema(
        dataset,
        independent_variable_name="gate_voltage",
        independent_variable_unit="V",
        observable_name="capacitance",
        observable_unit="F/m^2",
    )

    if not isinstance(result, CVResult):
        raise TypeError(
            "result must be a CVResult instance."
        )

    direction = _require_string_condition(
        dataset,
        name="sweep_direction",
        expected_values=("forward", "backward"),
    )

    sweep = (
        result.forward
        if direction == "forward"
        else result.backward
    )

    return _build_evaluation(
        dataset,
        simulation_x=sweep.voltages_V,
        simulation_y=sweep.capacitance_F_m2,
        consumed_conditions={"sweep_direction"},
    )


def evaluate_memory_window_vs_program_voltage_objective(
    dataset: DeviceObservableDataset,
    *,
    program_voltages_V: np.ndarray | Sequence[float],
    cv_results: Sequence[CVResult],
    program_pulse_width_s: float,
) -> DeviceObjectiveEvaluation:
    """
    Compare memory-window versus program-voltage data against CV results.

    Each element of ``cv_results`` must correspond to the same-position
    program voltage in ``program_voltages_V``. The fixed program-pulse width
    is checked against the dataset condition before the objective is built.
    """

    _require_schema(
        dataset,
        independent_variable_name="program_voltage",
        independent_variable_unit="V",
        observable_name="memory_window",
        observable_unit="V",
    )

    _require_numeric_condition(
        dataset,
        name="program_pulse_width",
        expected_unit="s",
        actual_value=program_pulse_width_s,
        actual_value_name="program_pulse_width_s",
    )

    results = tuple(cv_results)

    if len(results) < 2:
        raise ValueError(
            "cv_results must contain at least two CVResult objects."
        )

    if any(
        not isinstance(result, CVResult)
        for result in results
    ):
        raise TypeError(
            "Every element of cv_results must be a CVResult."
        )

    if len(program_voltages_V) != len(results):
        raise ValueError(
            "program_voltages_V and cv_results must "
            "have matching lengths."
        )

    memory_windows = np.asarray(
        [
            result.memory_window_V
            for result in results
        ],
        dtype=float,
    )

    return _build_evaluation(
        dataset,
        simulation_x=program_voltages_V,
        simulation_y=memory_windows,
        consumed_conditions={"program_pulse_width"},
    )


def evaluate_memory_window_vs_programming_time_objective(
    dataset: DeviceObservableDataset,
    *,
    programming_times_s: np.ndarray | Sequence[float],
    cv_results: Sequence[CVResult],
    program_voltage_V: float,
) -> DeviceObjectiveEvaluation:
    """
    Compare memory-window versus programming-time data against CV results.

    Each element of ``cv_results`` must correspond to the same-position
    programming time in ``programming_times_s``. Programming times must be
    strictly positive. The fixed program voltage is checked against the
    dataset condition.
    """

    _require_schema(
        dataset,
        independent_variable_name="programming_time",
        independent_variable_unit="s",
        observable_name="memory_window",
        observable_unit="V",
    )

    _require_numeric_condition(
        dataset,
        name="program_voltage",
        expected_unit="V",
        actual_value=program_voltage_V,
        actual_value_name="program_voltage_V",
    )

    times = np.asarray(
        programming_times_s,
        dtype=float,
    )

    if np.any(~np.isfinite(times)) or np.any(times <= 0.0):
        raise ValueError(
            "programming_times_s must contain only "
            "finite, strictly positive values."
        )

    results = tuple(cv_results)

    if len(results) < 2:
        raise ValueError(
            "cv_results must contain at least two CVResult objects."
        )

    if any(
        not isinstance(result, CVResult)
        for result in results
    ):
        raise TypeError(
            "Every element of cv_results must be a CVResult."
        )

    if len(times) != len(results):
        raise ValueError(
            "programming_times_s and cv_results must "
            "have matching lengths."
        )

    memory_windows = np.asarray(
        [
            result.memory_window_V
            for result in results
        ],
        dtype=float,
    )

    return _build_evaluation(
        dataset,
        simulation_x=times,
        simulation_y=memory_windows,
        consumed_conditions={"program_voltage"},
    )


def evaluate_retention_objective(
    dataset: DeviceObservableDataset,
    result: RetentionResult,
    *,
    retention_gate_voltage_V: float,
) -> DeviceObjectiveEvaluation:
    """
    Compare retention data against a ``RetentionResult``.

    Supported observables are ``delta_vfb`` and
    ``total_charge_retention_fraction``. The supplied retention gate voltage
    is checked against the dataset condition because ``RetentionResult`` does
    not itself store the ``RetentionConfig`` used to generate it.
    """

    _require_device_dataset(dataset)

    if (
        dataset.independent_variable_name != "time"
        or dataset.independent_variable_unit != "s"
    ):
        raise ValueError(
            "Retention datasets must use 'time' in seconds "
            "as the independent variable."
        )

    if not isinstance(result, RetentionResult):
        raise TypeError(
            "result must be a RetentionResult instance."
        )

    _require_numeric_condition(
        dataset,
        name="retention_gate_voltage",
        expected_unit="V",
        actual_value=retention_gate_voltage_V,
        actual_value_name="retention_gate_voltage_V",
    )

    if dataset.observable_name == "delta_vfb":
        if dataset.observable_unit != "V":
            raise ValueError(
                "delta_vfb datasets must use observable unit 'V'."
            )
        simulation_y = result.delta_vfb_V

    elif (
        dataset.observable_name
        == "total_charge_retention_fraction"
    ):
        if dataset.observable_unit is not None:
            raise ValueError(
                "total_charge_retention_fraction must be "
                "dimensionless."
            )
        simulation_y = (
            result.total_charge_retention_fraction
        )

    else:
        raise ValueError(
            "Unsupported retention observable "
            f"{dataset.observable_name!r}."
        )

    return _build_evaluation(
        dataset,
        simulation_x=result.time_s,
        simulation_y=simulation_y,
        consumed_conditions={"retention_gate_voltage"},
    )


__all__ = [
    "DeviceObjectiveEvaluation",
    "evaluate_cv_objective",
    "evaluate_memory_window_vs_program_voltage_objective",
    "evaluate_memory_window_vs_programming_time_objective",
    "evaluate_retention_objective",
    "interpolate_without_extrapolation",
]
