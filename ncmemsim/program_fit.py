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
from .physics import PhysicsModel
from .program_protocol import (
    ProgramPulseReadProtocol,
    ProgramPulseReadResult,
    run_program_pulse_read,
)
from .simulator import SimulationConfig, Simulator
from .state import DeviceState


@dataclass(frozen=True)
class ProgramTimeFitProtocol:
    """
    Common protocol settings for a ΔVFB-versus-programming-time fit.

    The programming times themselves come from the experimental dataset.
    Every time point is simulated from the same initial state; time points are
    not chained cumulatively.
    """

    program_voltage_V: float
    read_voltage_V: float = 0.0
    program_internal_dt_s: float | None = None

    def __post_init__(self) -> None:
        program_voltage = float(self.program_voltage_V)
        read_voltage = float(self.read_voltage_V)

        if not math.isfinite(program_voltage):
            raise ValueError(
                "program_voltage_V must be finite."
            )
        if not math.isfinite(read_voltage):
            raise ValueError(
                "read_voltage_V must be finite."
            )

        program_dt = self.program_internal_dt_s
        if program_dt is not None:
            program_dt = float(program_dt)
            if (
                not math.isfinite(program_dt)
                or program_dt <= 0.0
            ):
                raise ValueError(
                    "program_internal_dt_s must be finite "
                    "and strictly positive when supplied."
                )

        object.__setattr__(
            self,
            "program_voltage_V",
            program_voltage,
        )
        object.__setattr__(
            self,
            "read_voltage_V",
            read_voltage,
        )
        object.__setattr__(
            self,
            "program_internal_dt_s",
            program_dt,
        )

    def pulse_protocol(
        self,
        programming_time_s: float,
    ) -> ProgramPulseReadProtocol:
        return ProgramPulseReadProtocol(
            program_voltage_V=self.program_voltage_V,
            programming_time_s=programming_time_s,
            read_voltage_V=self.read_voltage_V,
            program_internal_dt_s=(
                self.program_internal_dt_s
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "program_voltage_V": self.program_voltage_V,
            "read_voltage_V": self.read_voltage_V,
            "program_internal_dt_s": (
                self.program_internal_dt_s
            ),
            "time_point_semantics": (
                "independent-pulses-from-common-initial-state"
            ),
            "read_semantics": (
                "nondestructive-zero-dwell-electrostatic"
            ),
        }

    def protocol_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass
class ProgramTimePrediction:
    """Predicted ΔVFB values for one parameter vector."""

    programming_times_s: np.ndarray
    predicted_delta_vfb_V: np.ndarray
    pulse_results: tuple[
        ProgramPulseReadResult,
        ...,
    ]

    def __post_init__(self) -> None:
        times = np.array(
            self.programming_times_s,
            dtype=float,
            copy=True,
        )
        predicted = np.array(
            self.predicted_delta_vfb_V,
            dtype=float,
            copy=True,
        )
        pulse_results = tuple(self.pulse_results)

        if times.ndim != 1 or predicted.ndim != 1:
            raise ValueError(
                "programming_times_s and "
                "predicted_delta_vfb_V must be one-dimensional."
            )
        if times.size == 0:
            raise ValueError(
                "Program-time prediction cannot be empty."
            )
        if times.shape != predicted.shape:
            raise ValueError(
                "programming_times_s and predicted_delta_vfb_V "
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
                "predicted_delta_vfb_V must be finite."
            )

        times.setflags(write=False)
        predicted.setflags(write=False)

        self.programming_times_s = times
        self.predicted_delta_vfb_V = predicted
        self.pulse_results = pulse_results


@dataclass
class DeviceProgramTimeFitResult:
    """
    Single-parameter numerical fit to ΔVFB(programming_time).

    ``FITTED`` reports numerical optimization against the identified dataset.
    It does not mean the parameter has passed independent validation or has
    CALIBRATED provenance.
    """

    dataset_id: str
    dataset_hash: str
    calibration_specification_hash: str
    protocol: ProgramTimeFitProtocol
    numerical_result: DeterministicFitResult
    objective: ObjectiveEvaluation
    fitted_context: DeviceCalibrationContext
    prediction: ProgramTimePrediction

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
                "single-parameter-delta-vfb-vs-programming-time-fit"
            ),
            "scientific_status": self.scientific_status,
            "dataset_id": self.dataset_id,
            "dataset_hash": self.dataset_hash,
            "calibration_specification_hash": (
                self.calibration_specification_hash
            ),
            "protocol": self.protocol.to_dict(),
            "protocol_hash": (
                self.protocol.protocol_hash()
            ),
            "parameter_application": (
                self.fitted_context
                .parameter_application_manifest()
            ),
            "programming_times_s": (
                self.prediction
                .programming_times_s.tolist()
            ),
            "predicted_delta_vfb_V": (
                self.prediction
                .predicted_delta_vfb_V.tolist()
            ),
            "numerical_result": (
                self.numerical_result.to_dict()
            ),
            "objective": self.objective.to_dict(),
        }


def _require_program_time_delta_vfb_dataset(
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
        or dataset.observable_name != "delta_vfb"
        or dataset.observable_unit != "V"
    ):
        raise ValueError(
            "Program-time fitting requires a dataset with "
            "programming_time [s] -> delta_vfb [V]."
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


def _condition_value(
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


def _validate_protocol_conditions(
    dataset: DeviceObservableDataset,
    protocol: ProgramTimeFitProtocol,
) -> None:
    program_voltage = _condition_value(
        dataset,
        "program_voltage",
    )

    if program_voltage is None:
        raise ValueError(
            "ΔVFB(programming_time) dataset must define "
            "the program_voltage condition."
        )

    if program_voltage.unit != "V":
        raise ValueError(
            "program_voltage condition must use unit 'V'."
        )

    try:
        dataset_program_voltage = float(
            program_voltage.value
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "program_voltage condition must be numeric."
        ) from exc

    if not math.isclose(
        dataset_program_voltage,
        protocol.program_voltage_V,
        rel_tol=0.0,
        abs_tol=1.0e-15,
    ):
        raise ValueError(
            "Protocol program_voltage_V does not match "
            "the dataset program_voltage condition."
        )

    read_voltage = _condition_value(
        dataset,
        "read_voltage",
    )

    if read_voltage is not None:
        if read_voltage.unit != "V":
            raise ValueError(
                "read_voltage condition must use unit 'V'."
            )
        try:
            dataset_read_voltage = float(
                read_voltage.value
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "read_voltage condition must be numeric."
            ) from exc

        if not math.isclose(
            dataset_read_voltage,
            protocol.read_voltage_V,
            rel_tol=0.0,
            abs_tol=1.0e-15,
        ):
            raise ValueError(
                "Protocol read_voltage_V does not match "
                "the dataset read_voltage condition."
            )


def predict_delta_vfb_vs_programming_time(
    simulator: Simulator,
    programming_times_s: Sequence[float]
    | np.ndarray,
    protocol: ProgramTimeFitProtocol,
    *,
    initial_state: DeviceState | None = None,
) -> ProgramTimePrediction:
    """
    Simulate independent program pulses at each requested time.

    Each time point starts from one common initial state. No result from a
    shorter pulse becomes the initial state of a longer pulse.
    """

    if not isinstance(simulator, Simulator):
        raise TypeError(
            "simulator must be a Simulator instance."
        )
    if not isinstance(
        protocol,
        ProgramTimeFitProtocol,
    ):
        raise TypeError(
            "protocol must be a ProgramTimeFitProtocol."
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

    if initial_state is None:
        common_initial = (
            DeviceState.empty_for_device(
                simulator.device
            )
        )
    else:
        if not isinstance(
            initial_state,
            DeviceState,
        ):
            raise TypeError(
                "initial_state must be a DeviceState "
                "or None."
            )
        initial_state.validate(simulator.device)
        common_initial = initial_state.copy()

    common_initial.validate(simulator.device)

    pulse_results = tuple(
        run_program_pulse_read(
            simulator,
            protocol.pulse_protocol(
                float(programming_time_s)
            ),
            initial_state=common_initial,
        )
        for programming_time_s in times
    )

    predicted = np.asarray(
        [
            result.delta_vfb_V
            for result in pulse_results
        ],
        dtype=float,
    )

    return ProgramTimePrediction(
        programming_times_s=times,
        predicted_delta_vfb_V=predicted,
        pulse_results=pulse_results,
    )


def _evaluate_candidate(
    dataset: DeviceObservableDataset,
    *,
    base_device: Device,
    base_physics: PhysicsModel,
    base_simulation_config: SimulationConfig,
    calibration_spec: DeviceCalibrationSpec,
    protocol: ProgramTimeFitProtocol,
    parameter_values,
) -> tuple[
    DeviceCalibrationContext,
    ProgramTimePrediction,
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
        predict_delta_vfb_vs_programming_time(
            simulator,
            dataset.independent_values,
            protocol,
        )
    )

    objective = evaluate_least_squares_objective(
        dataset.observed_values,
        prediction.predicted_delta_vfb_V,
        uncertainty=dataset.observed_uncertainty,
    )

    return context, prediction, objective


def fit_single_parameter_delta_vfb_vs_programming_time(
    dataset: DeviceObservableDataset,
    *,
    base_device: Device,
    base_physics: PhysicsModel,
    base_simulation_config: SimulationConfig,
    calibration_spec: DeviceCalibrationSpec,
    protocol: ProgramTimeFitProtocol,
    least_squares_config: (
        LeastSquaresConfig | None
    ) = None,
) -> DeviceProgramTimeFitResult:
    """
    Fit exactly one device parameter to ΔVFB(programming_time).

    F4h2b2 intentionally remains a single-parameter workflow. This prevents
    the first pulse-kinetic recovery test from conflating attempt-frequency
    and barrier/WKB correlations.
    """

    _require_program_time_delta_vfb_dataset(
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
        ProgramTimeFitProtocol,
    ):
        raise TypeError(
            "protocol must be a ProgramTimeFitProtocol."
        )

    if (
        calibration_spec.parameter_set.n_parameters
        != 1
    ):
        raise ValueError(
            "F4h2b2 program-time fitting requires "
            "exactly one free parameter."
        )

    # Fail early on model/protocol/dataset incompatibility.
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
    )

    return DeviceProgramTimeFitResult(
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
    "DeviceProgramTimeFitResult",
    "ProgramTimeFitProtocol",
    "ProgramTimePrediction",
    "fit_single_parameter_delta_vfb_vs_programming_time",
    "predict_delta_vfb_vs_programming_time",
]
