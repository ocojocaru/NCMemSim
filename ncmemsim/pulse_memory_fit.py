from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Sequence

import numpy as np

from .device import Device
from .device_calibration import (
    DeviceCalibrationContext,
    DeviceCalibrationSpec,
    apply_device_calibration_parameters,
)
from .experimental import DeviceObservableDataset
from .fitting import (
    DeterministicFitResult,
    LeastSquaresConfig,
    ObjectiveEvaluation,
    evaluate_least_squares_objective,
    run_least_squares_fit,
)
from .hashing import canonical_hash
from .paired_pulse_protocol import (
    PairedPulseMemoryProtocol,
    PairedPulseMemoryResult,
    run_paired_pulse_memory_protocol,
)
from .physics import PhysicsModel
from .simulator import SimulationConfig, Simulator
from .state import DeviceState


PULSE_MEMORY_WINDOW_DEFINITION = (
    "delta_vfb_programmed_minus_delta_vfb_erased"
)
PULSE_BRANCH_SEMANTICS = (
    "independent-program-and-erase-from-common-reference"
)
PULSE_READ_SEMANTICS = (
    "nondestructive-zero-dwell-electrostatic"
)


@dataclass(frozen=True)
class PulseMemoryTimeFitProtocol:
    """
    Common settings for pulse-defined memory-window versus program-time fits.

    The programming times come from the dataset.  Every data point starts from
    one common reference state, and the program and erase branches for that
    point are themselves independent.
    """

    program_voltage_V: float
    erase_voltage_V: float
    erase_time_s: float
    read_voltage_V: float = 0.0
    pulse_internal_dt_s: float | None = None

    def __post_init__(self) -> None:
        program_voltage = float(self.program_voltage_V)
        erase_voltage = float(self.erase_voltage_V)
        erase_time = float(self.erase_time_s)
        read_voltage = float(self.read_voltage_V)

        for field_name, value in {
            "program_voltage_V": program_voltage,
            "erase_voltage_V": erase_voltage,
            "read_voltage_V": read_voltage,
        }.items():
            if not math.isfinite(value):
                raise ValueError(f"{field_name} must be finite.")

        if program_voltage == erase_voltage:
            raise ValueError(
                "program_voltage_V and erase_voltage_V must be different."
            )

        if not math.isfinite(erase_time) or erase_time <= 0.0:
            raise ValueError(
                "erase_time_s must be finite and strictly positive."
            )

        pulse_dt = self.pulse_internal_dt_s
        if pulse_dt is not None:
            pulse_dt = float(pulse_dt)
            if not math.isfinite(pulse_dt) or pulse_dt <= 0.0:
                raise ValueError(
                    "pulse_internal_dt_s must be finite and strictly "
                    "positive when supplied."
                )

        object.__setattr__(
            self,
            "program_voltage_V",
            program_voltage,
        )
        object.__setattr__(
            self,
            "erase_voltage_V",
            erase_voltage,
        )
        object.__setattr__(
            self,
            "erase_time_s",
            erase_time,
        )
        object.__setattr__(
            self,
            "read_voltage_V",
            read_voltage,
        )
        object.__setattr__(
            self,
            "pulse_internal_dt_s",
            pulse_dt,
        )

    def paired_protocol(
        self,
        programming_time_s: float,
    ) -> PairedPulseMemoryProtocol:
        return PairedPulseMemoryProtocol(
            program_voltage_V=self.program_voltage_V,
            program_time_s=programming_time_s,
            erase_voltage_V=self.erase_voltage_V,
            erase_time_s=self.erase_time_s,
            read_voltage_V=self.read_voltage_V,
            pulse_internal_dt_s=self.pulse_internal_dt_s,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "program_voltage_V": self.program_voltage_V,
            "erase_voltage_V": self.erase_voltage_V,
            "erase_time_s": self.erase_time_s,
            "read_voltage_V": self.read_voltage_V,
            "pulse_internal_dt_s": self.pulse_internal_dt_s,
            "programming_time_source": "dataset-independent-variable",
            "memory_window_definition": PULSE_MEMORY_WINDOW_DEFINITION,
            "branch_semantics": PULSE_BRANCH_SEMANTICS,
            "read_semantics": PULSE_READ_SEMANTICS,
            "time_point_semantics": (
                "independent-paired-pulses-from-common-reference"
            ),
        }

    def protocol_hash(self) -> str:
        return canonical_hash(self.to_dict())


def _reference_state_manifest(
    state: DeviceState,
    device: Device,
) -> dict[str, Any]:
    """
    Serialize the occupation-defined reference state used by the fit.

    Local electrostatic field/potential diagnostics are intentionally excluded:
    they are recomputed by the simulator at each pulse/read bias.  The
    reference identity is therefore the occupation state, its structural
    floating-gate identifiers, and its time coordinate.
    """

    state.validate(device)

    floating_gates = []
    for fg_state in state.floating_gates:
        floating_gates.append(
            {
                "fg_id": fg_state.fg_id,
                "layer_name": fg_state.layer_name,
                "z_center_nm": fg_state.z_center_nm,
                "P0": np.asarray(
                    fg_state.P0,
                    dtype=float,
                ).tolist(),
                "P1": np.asarray(
                    fg_state.P1,
                    dtype=float,
                ).tolist(),
                "P2": np.asarray(
                    fg_state.P2,
                    dtype=float,
                ).tolist(),
            }
        )

    return {
        "schema_version": 1,
        "semantics": "occupation-defined-common-reference-state",
        "diagnostic_fields_included": False,
        "time_s": float(state.time_s),
        "floating_gates": floating_gates,
    }


@dataclass
class PulseMemoryTimePrediction:
    """Predicted signed pulse-defined memory windows."""

    programming_times_s: np.ndarray
    predicted_memory_window_V: np.ndarray
    pulse_results: tuple[
        PairedPulseMemoryResult,
        ...,
    ]
    reference_state_manifest: dict[str, Any]

    def __post_init__(self) -> None:
        times = np.array(
            self.programming_times_s,
            dtype=float,
            copy=True,
        )
        predicted = np.array(
            self.predicted_memory_window_V,
            dtype=float,
            copy=True,
        )
        pulse_results = tuple(self.pulse_results)
        reference_manifest = dict(
            self.reference_state_manifest
        )

        if times.ndim != 1 or predicted.ndim != 1:
            raise ValueError(
                "programming_times_s and predicted_memory_window_V "
                "must be one-dimensional."
            )
        if times.size == 0:
            raise ValueError(
                "Pulse-memory prediction cannot be empty."
            )
        if times.shape != predicted.shape:
            raise ValueError(
                "programming_times_s and predicted_memory_window_V "
                "must have the same shape."
            )
        if len(pulse_results) != times.size:
            raise ValueError(
                "pulse_results must contain one result per time point."
            )
        if (
            not np.all(np.isfinite(times))
            or np.any(times <= 0.0)
        ):
            raise ValueError(
                "programming_times_s must be finite and "
                "strictly positive."
            )
        if not np.all(np.isfinite(predicted)):
            raise ValueError(
                "predicted_memory_window_V must be finite."
            )

        for pulse_result in pulse_results:
            if not isinstance(
                pulse_result,
                PairedPulseMemoryResult,
            ):
                raise TypeError(
                    "pulse_results must contain "
                    "PairedPulseMemoryResult instances."
                )

        times.setflags(write=False)
        predicted.setflags(write=False)

        self.programming_times_s = times
        self.predicted_memory_window_V = predicted
        self.pulse_results = pulse_results
        self.reference_state_manifest = reference_manifest

    @property
    def reference_state_hash(self) -> str:
        return canonical_hash(
            self.reference_state_manifest
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "memory_window_definition": PULSE_MEMORY_WINDOW_DEFINITION,
            "programming_times_s": self.programming_times_s.tolist(),
            "predicted_memory_window_V": (
                self.predicted_memory_window_V.tolist()
            ),
            "reference_state": self.reference_state_manifest,
            "reference_state_hash": self.reference_state_hash,
            "pulse_results": [
                result.to_dict()
                for result in self.pulse_results
            ],
        }


@dataclass
class DevicePulseMemoryTimeFitResult:
    """
    Single-parameter fit to pulse-defined memory_window(programming_time).

    ``FITTED`` denotes numerical optimization against the identified dataset.
    It does not imply independent validation or CALIBRATED provenance.
    """

    dataset_id: str
    dataset_hash: str
    calibration_specification_hash: str
    protocol: PulseMemoryTimeFitProtocol
    numerical_result: DeterministicFitResult
    objective: ObjectiveEvaluation
    fitted_context: DeviceCalibrationContext
    prediction: PulseMemoryTimePrediction

    @property
    def fitted_parameter_values(
        self,
    ) -> dict[str, float]:
        return dict(
            self.fitted_context.parameter_values
        )

    @property
    def scientific_status(self) -> str:
        return "FITTED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "workflow": (
                "single-parameter-pulse-memory-window-vs-programming-time-fit"
            ),
            "scientific_status": self.scientific_status,
            "dataset_id": self.dataset_id,
            "dataset_hash": self.dataset_hash,
            "calibration_specification_hash": (
                self.calibration_specification_hash
            ),
            "protocol": self.protocol.to_dict(),
            "protocol_hash": self.protocol.protocol_hash(),
            "memory_window_definition": PULSE_MEMORY_WINDOW_DEFINITION,
            "branch_semantics": PULSE_BRANCH_SEMANTICS,
            "read_semantics": PULSE_READ_SEMANTICS,
            "reference_state_hash": (
                self.prediction.reference_state_hash
            ),
            "reference_state": (
                self.prediction.reference_state_manifest
            ),
            "parameter_application": (
                self.fitted_context
                .parameter_application_manifest()
            ),
            "programming_times_s": (
                self.prediction.programming_times_s.tolist()
            ),
            "predicted_memory_window_V": (
                self.prediction
                .predicted_memory_window_V.tolist()
            ),
            "numerical_result": (
                self.numerical_result.to_dict()
            ),
            "objective": self.objective.to_dict(),
        }


def _require_pulse_memory_time_dataset(
    dataset: DeviceObservableDataset,
) -> None:
    if not isinstance(
        dataset,
        DeviceObservableDataset,
    ):
        raise TypeError(
            "dataset must be a DeviceObservableDataset."
        )

    if (
        dataset.independent_variable_name
        != "programming_time"
        or dataset.independent_variable_unit != "s"
        or dataset.observable_name != "memory_window"
        or dataset.observable_unit != "V"
    ):
        raise ValueError(
            "Pulse-memory fitting requires a dataset with "
            "programming_time [s] -> memory_window [V]."
        )

    times = np.asarray(
        dataset.independent_values,
        dtype=float,
    )
    if np.any(times <= 0.0):
        raise ValueError(
            "Programming-time dataset values must be "
            "strictly positive."
        )


def _condition(
    dataset: DeviceObservableDataset,
    name: str,
):
    matches = tuple(
        condition
        for condition in dataset.conditions
        if condition.name == name
    )

    if len(matches) > 1:
        raise ValueError(
            f"Dataset contains duplicate condition {name!r}."
        )

    return None if not matches else matches[0]


def _numeric_condition_value(
    dataset: DeviceObservableDataset,
    name: str,
    *,
    unit: str,
) -> float:
    condition = _condition(dataset, name)

    if condition is None:
        raise ValueError(
            f"Pulse-defined memory-window dataset must define "
            f"the {name} condition."
        )

    if condition.unit != unit:
        raise ValueError(
            f"{name} condition must use unit {unit!r}."
        )

    try:
        value = float(condition.value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{name} condition must be numeric."
        ) from exc

    if not math.isfinite(value):
        raise ValueError(
            f"{name} condition must be finite."
        )

    return value


def _text_condition_value(
    dataset: DeviceObservableDataset,
    name: str,
) -> str:
    condition = _condition(dataset, name)

    if condition is None:
        raise ValueError(
            f"Pulse-defined memory-window dataset must define "
            f"the {name} condition."
        )

    if condition.unit is not None:
        raise ValueError(
            f"{name} condition must not declare a unit."
        )

    if not isinstance(condition.value, str):
        raise ValueError(
            f"{name} condition must be text."
        )

    value = condition.value.strip()
    if not value:
        raise ValueError(
            f"{name} condition cannot be empty."
        )

    return value


def _require_close(
    *,
    observed: float,
    expected: float,
    field_name: str,
) -> None:
    if not math.isclose(
        observed,
        expected,
        rel_tol=0.0,
        abs_tol=1.0e-15,
    ):
        raise ValueError(
            f"Protocol {field_name} does not match "
            f"the dataset {field_name.removesuffix('_V').removesuffix('_s')} "
            "condition."
        )


def _validate_protocol_conditions(
    dataset: DeviceObservableDataset,
    protocol: PulseMemoryTimeFitProtocol,
) -> None:
    _require_close(
        observed=_numeric_condition_value(
            dataset,
            "program_voltage",
            unit="V",
        ),
        expected=protocol.program_voltage_V,
        field_name="program_voltage_V",
    )
    _require_close(
        observed=_numeric_condition_value(
            dataset,
            "erase_voltage",
            unit="V",
        ),
        expected=protocol.erase_voltage_V,
        field_name="erase_voltage_V",
    )
    _require_close(
        observed=_numeric_condition_value(
            dataset,
            "erase_pulse_width",
            unit="s",
        ),
        expected=protocol.erase_time_s,
        field_name="erase_time_s",
    )
    _require_close(
        observed=_numeric_condition_value(
            dataset,
            "read_voltage",
            unit="V",
        ),
        expected=protocol.read_voltage_V,
        field_name="read_voltage_V",
    )

    definition = _text_condition_value(
        dataset,
        "memory_window_definition",
    )
    if definition != PULSE_MEMORY_WINDOW_DEFINITION:
        raise ValueError(
            "memory_window_definition condition does not identify "
            "the pulse-defined signed memory window."
        )

    branch_semantics = _text_condition_value(
        dataset,
        "branch_semantics",
    )
    if branch_semantics != PULSE_BRANCH_SEMANTICS:
        raise ValueError(
            "branch_semantics condition does not identify independent "
            "program/erase branches from a common reference state."
        )

    read_semantics = _text_condition_value(
        dataset,
        "read_semantics",
    )
    if read_semantics != PULSE_READ_SEMANTICS:
        raise ValueError(
            "read_semantics condition does not identify the "
            "zero-dwell electrostatic read."
        )

    if _condition(
        dataset,
        "measurement_frequency",
    ) is not None:
        raise ValueError(
            "measurement_frequency is not modeled by the "
            "zero-dwell pulse-memory fitting workflow."
        )


def predict_pulse_memory_window_vs_programming_time(
    simulator: Simulator,
    programming_times_s: Sequence[float]
    | np.ndarray,
    protocol: PulseMemoryTimeFitProtocol,
    *,
    reference_state: DeviceState | None = None,
) -> PulseMemoryTimePrediction:
    """
    Simulate pulse-defined signed memory windows at independent program times.

    Every point uses the same common reference state.  Within each point,
    program and erase branches are independent, following
    ``PairedPulseMemoryProtocol``.
    """

    if not isinstance(simulator, Simulator):
        raise TypeError(
            "simulator must be a Simulator instance."
        )
    if not isinstance(
        protocol,
        PulseMemoryTimeFitProtocol,
    ):
        raise TypeError(
            "protocol must be a PulseMemoryTimeFitProtocol."
        )

    times = np.array(
        programming_times_s,
        dtype=float,
        copy=True,
    )

    if times.ndim != 1 or times.size == 0:
        raise ValueError(
            "programming_times_s must be a non-empty "
            "one-dimensional array."
        )
    if (
        not np.all(np.isfinite(times))
        or np.any(times <= 0.0)
    ):
        raise ValueError(
            "programming_times_s must contain finite, "
            "strictly positive values."
        )

    if reference_state is None:
        common_reference = (
            DeviceState.empty_for_device(
                simulator.device
            )
        )
    else:
        if not isinstance(
            reference_state,
            DeviceState,
        ):
            raise TypeError(
                "reference_state must be a DeviceState "
                "or None."
            )
        reference_state.validate(
            simulator.device
        )
        common_reference = reference_state.copy()

    common_reference.validate(
        simulator.device
    )

    reference_manifest = (
        _reference_state_manifest(
            common_reference,
            simulator.device,
        )
    )

    pulse_results = tuple(
        run_paired_pulse_memory_protocol(
            simulator,
            protocol.paired_protocol(
                float(programming_time_s)
            ),
            reference_state=common_reference,
        )
        for programming_time_s in times
    )

    predicted = np.asarray(
        [
            result.memory_window_V
            for result in pulse_results
        ],
        dtype=float,
    )

    return PulseMemoryTimePrediction(
        programming_times_s=times,
        predicted_memory_window_V=predicted,
        pulse_results=pulse_results,
        reference_state_manifest=reference_manifest,
    )


def _evaluate_candidate(
    dataset: DeviceObservableDataset,
    *,
    base_device: Device,
    base_physics: PhysicsModel,
    base_simulation_config: SimulationConfig,
    calibration_spec: DeviceCalibrationSpec,
    protocol: PulseMemoryTimeFitProtocol,
    parameter_values,
    reference_state: DeviceState | None,
) -> tuple[
    DeviceCalibrationContext,
    PulseMemoryTimePrediction,
    ObjectiveEvaluation,
]:
    context = apply_device_calibration_parameters(
        base_device,
        base_physics,
        base_simulation_config,
        calibration_spec,
        parameter_values,
    )

    simulator = Simulator(
        context.device,
        context.physics,
        context.simulation_config,
    )

    prediction = (
        predict_pulse_memory_window_vs_programming_time(
            simulator,
            dataset.independent_values,
            protocol,
            reference_state=reference_state,
        )
    )

    objective = evaluate_least_squares_objective(
        dataset.observed_values,
        prediction.predicted_memory_window_V,
        uncertainty=dataset.observed_uncertainty,
    )

    return context, prediction, objective


def fit_single_parameter_pulse_memory_window_vs_programming_time(
    dataset: DeviceObservableDataset,
    *,
    base_device: Device,
    base_physics: PhysicsModel,
    base_simulation_config: SimulationConfig,
    calibration_spec: DeviceCalibrationSpec,
    protocol: PulseMemoryTimeFitProtocol,
    reference_state: DeviceState | None = None,
    least_squares_config: (
        LeastSquaresConfig | None
    ) = None,
) -> DevicePulseMemoryTimeFitResult:
    """
    Fit exactly one device parameter to a pulse-defined MW(programming_time).

    F4h2c1 intentionally remains single-parameter.  The workflow uses the
    signed state separation produced directly by ``PairedPulseMemoryResult``;
    it does not reinterpret ``CVResult.memory_window_V``.
    """

    _require_pulse_memory_time_dataset(
        dataset
    )
    _validate_protocol_conditions(
        dataset,
        protocol,
    )

    if not isinstance(base_device, Device):
        raise TypeError(
            "base_device must be a Device instance."
        )
    if not isinstance(
        base_physics,
        PhysicsModel,
    ):
        raise TypeError(
            "base_physics must be a PhysicsModel instance."
        )
    if not isinstance(
        base_simulation_config,
        SimulationConfig,
    ):
        raise TypeError(
            "base_simulation_config must be a "
            "SimulationConfig instance."
        )
    if not isinstance(
        calibration_spec,
        DeviceCalibrationSpec,
    ):
        raise TypeError(
            "calibration_spec must be a "
            "DeviceCalibrationSpec."
        )
    if not isinstance(
        protocol,
        PulseMemoryTimeFitProtocol,
    ):
        raise TypeError(
            "protocol must be a "
            "PulseMemoryTimeFitProtocol."
        )

    if (
        calibration_spec.parameter_set.n_parameters
        != 1
    ):
        raise ValueError(
            "F4h2c1 pulse-memory fitting requires "
            "exactly one free parameter."
        )

    if reference_state is not None:
        if not isinstance(
            reference_state,
            DeviceState,
        ):
            raise TypeError(
                "reference_state must be a DeviceState "
                "or None."
            )
        reference_state.validate(base_device)

    _evaluate_candidate(
        dataset,
        base_device=base_device,
        base_physics=base_physics,
        base_simulation_config=(
            base_simulation_config
        ),
        calibration_spec=calibration_spec,
        protocol=protocol,
        parameter_values=(
            calibration_spec
            .parameter_set.initial_values
        ),
        reference_state=reference_state,
    )

    def residual_function(parameter_values):
        _, _, objective = _evaluate_candidate(
            dataset,
            base_device=base_device,
            base_physics=base_physics,
            base_simulation_config=(
                base_simulation_config
            ),
            calibration_spec=calibration_spec,
            protocol=protocol,
            parameter_values=parameter_values,
            reference_state=reference_state,
        )
        return objective.objective_residuals

    numerical_result = run_least_squares_fit(
        calibration_spec.parameter_set,
        residual_function,
        config=least_squares_config,
    )

    (
        fitted_context,
        prediction,
        objective,
    ) = _evaluate_candidate(
        dataset,
        base_device=base_device,
        base_physics=base_physics,
        base_simulation_config=(
            base_simulation_config
        ),
        calibration_spec=calibration_spec,
        protocol=protocol,
        parameter_values=(
            numerical_result.fitted_values
        ),
        reference_state=reference_state,
    )

    return DevicePulseMemoryTimeFitResult(
        dataset_id=dataset.metadata.dataset_id,
        dataset_hash=dataset.dataset_hash(),
        calibration_specification_hash=(
            calibration_spec
            .specification_hash()
        ),
        protocol=protocol,
        numerical_result=numerical_result,
        objective=objective,
        fitted_context=fitted_context,
        prediction=prediction,
    )


__all__ = [
    "DevicePulseMemoryTimeFitResult",
    "PULSE_BRANCH_SEMANTICS",
    "PULSE_MEMORY_WINDOW_DEFINITION",
    "PULSE_READ_SEMANTICS",
    "PulseMemoryTimeFitProtocol",
    "PulseMemoryTimePrediction",
    "fit_single_parameter_pulse_memory_window_vs_programming_time",
    "predict_pulse_memory_window_vs_programming_time",
]
