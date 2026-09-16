from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np

from .device import Device
from .device_calibration import (
    DeviceCalibrationContext,
    DeviceCalibrationSpec,
    apply_device_calibration_parameters,
)
from .device_objectives import (
    DeviceObjectiveEvaluation,
    evaluate_retention_objective,
)
from .experimental import DeviceObservableDataset
from .fitting import (
    DeterministicFitResult,
    LeastSquaresConfig,
    ObjectiveEvaluation,
    run_least_squares_fit,
)
from .hashing import canonical_hash
from .physics import PhysicsModel
from .retention import RetentionConfig, RetentionResult
from .simulator import SimulationConfig, Simulator
from .state import DeviceState


RETENTION_FRACTION_OBSERVABLE = "total_charge_retention_fraction"
RETENTION_INITIAL_STATE_SEMANTICS = (
    "caller-supplied-occupation-defined-initial-state"
)
RETENTION_TRAJECTORY_SEMANTICS = (
    "single-continuous-fixed-bias-retention-trajectory"
)
RETENTION_INTERPOLATION_SEMANTICS = (
    "linear-physical-time-no-extrapolation"
)


def _retention_config_dict(config: RetentionConfig) -> dict[str, Any]:
    return {
        "gate_voltage_V": config.gate_voltage_V,
        "total_time_s": config.total_time_s,
        "initial_dt_s": config.initial_dt_s,
        "maximum_dt_s": config.maximum_dt_s,
        "growth_factor": config.growth_factor,
        "output_points": config.output_points,
        "quasi_equilibrium_tolerance_C_m2_s": (
            config.quasi_equilibrium_tolerance_C_m2_s
        ),
        "quasi_equilibrium_steps": config.quasi_equilibrium_steps,
        "stop_at_quasi_equilibrium": config.stop_at_quasi_equilibrium,
        "occupancy_integrator": config.occupancy_integrator,
    }


@dataclass(frozen=True)
class RetentionFitProtocol:
    """
    Fixed-bias protocol for single-parameter retention-fraction fitting.

    The dataset supplies the measurement times. One continuous retention
    trajectory is simulated from a caller-supplied initial ``DeviceState`` and
    interpolated onto the experimental time grid without extrapolation.

    F4h2c2c requires the numerically stable backward-Euler occupancy integrator
    established by F4h2c2a. Early termination at detected quasi-equilibrium is
    disabled because a fitting trajectory must cover the complete declared
    simulation domain.
    """

    retention_config: RetentionConfig

    def __post_init__(self) -> None:
        if not isinstance(self.retention_config, RetentionConfig):
            raise TypeError(
                "retention_config must be a RetentionConfig."
            )

        config = self.retention_config
        config.validate()

        finite_values = {
            "gate_voltage_V": config.gate_voltage_V,
            "total_time_s": config.total_time_s,
            "initial_dt_s": config.initial_dt_s,
            "maximum_dt_s": config.maximum_dt_s,
            "growth_factor": config.growth_factor,
            "quasi_equilibrium_tolerance_C_m2_s": (
                config.quasi_equilibrium_tolerance_C_m2_s
            ),
        }
        for field_name, value in finite_values.items():
            if not math.isfinite(float(value)):
                raise ValueError(f"{field_name} must be finite.")

        if config.total_time_s <= 0.0:
            raise ValueError(
                "Retention fitting requires total_time_s "
                "to be strictly positive."
            )

        if (
            isinstance(config.output_points, bool)
            or not isinstance(config.output_points, int)
        ):
            raise TypeError("output_points must be an integer.")

        if (
            isinstance(config.quasi_equilibrium_steps, bool)
            or not isinstance(config.quasi_equilibrium_steps, int)
        ):
            raise TypeError(
                "quasi_equilibrium_steps must be an integer."
            )

        if not isinstance(config.stop_at_quasi_equilibrium, bool):
            raise TypeError(
                "stop_at_quasi_equilibrium must be a bool."
            )

        if config.stop_at_quasi_equilibrium:
            raise ValueError(
                "Retention fitting requires "
                "stop_at_quasi_equilibrium=False so the simulated "
                "trajectory covers the declared time domain."
            )

        if config.occupancy_integrator != "backward_euler":
            raise ValueError(
                "F4h2c2c retention fitting requires "
                "occupancy_integrator='backward_euler'."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "retention_config": _retention_config_dict(
                self.retention_config
            ),
            "observable": RETENTION_FRACTION_OBSERVABLE,
            "initial_state_semantics": RETENTION_INITIAL_STATE_SEMANTICS,
            "trajectory_semantics": RETENTION_TRAJECTORY_SEMANTICS,
            "interpolation_semantics": RETENTION_INTERPOLATION_SEMANTICS,
            "measurement_time_source": "dataset-independent-variable",
        }

    def protocol_hash(self) -> str:
        return canonical_hash(self.to_dict())


def _initial_state_manifest(
    state: DeviceState,
    device: Device,
) -> dict[str, Any]:
    """
    Serialize the occupation-defined initial state used by retention fitting.

    Local electrostatic diagnostic fields are intentionally excluded because
    the simulator recomputes them self-consistently at the retention bias.
    """

    state.validate(device)

    floating_gates = []
    for fg_state in state.floating_gates:
        floating_gates.append(
            {
                "fg_id": fg_state.fg_id,
                "layer_name": fg_state.layer_name,
                "z_center_nm": fg_state.z_center_nm,
                "P0": np.asarray(fg_state.P0, dtype=float).tolist(),
                "P1": np.asarray(fg_state.P1, dtype=float).tolist(),
                "P2": np.asarray(fg_state.P2, dtype=float).tolist(),
            }
        )

    return {
        "schema_version": 1,
        "semantics": RETENTION_INITIAL_STATE_SEMANTICS,
        "diagnostic_fields_included": False,
        "time_s": float(state.time_s),
        "floating_gates": floating_gates,
    }


@dataclass
class RetentionFractionPrediction:
    """One simulated fixed-bias retention-fraction trajectory."""

    time_s: np.ndarray
    predicted_retention_fraction: np.ndarray
    retention_result: RetentionResult
    initial_state_manifest: dict[str, Any]

    def __post_init__(self) -> None:
        times = np.array(self.time_s, dtype=float, copy=True)
        predicted = np.array(
            self.predicted_retention_fraction,
            dtype=float,
            copy=True,
        )
        manifest = dict(self.initial_state_manifest)

        if not isinstance(self.retention_result, RetentionResult):
            raise TypeError(
                "retention_result must be a RetentionResult."
            )

        if times.ndim != 1 or predicted.ndim != 1:
            raise ValueError(
                "time_s and predicted_retention_fraction "
                "must be one-dimensional."
            )
        if times.size < 2:
            raise ValueError(
                "Retention prediction must contain at least "
                "two time points."
            )
        if times.shape != predicted.shape:
            raise ValueError(
                "time_s and predicted_retention_fraction "
                "must have matching shapes."
            )
        if not np.all(np.isfinite(times)):
            raise ValueError(
                "time_s must contain only finite values."
            )
        if np.any(times < 0.0):
            raise ValueError("time_s must be non-negative.")
        if not np.all(np.diff(times) > 0.0):
            raise ValueError(
                "time_s must be strictly increasing."
            )
        if not np.all(np.isfinite(predicted)):
            raise ValueError(
                "predicted_retention_fraction must contain "
                "only finite values."
            )

        times.setflags(write=False)
        predicted.setflags(write=False)

        self.time_s = times
        self.predicted_retention_fraction = predicted
        self.initial_state_manifest = manifest

    @property
    def initial_state_hash(self) -> str:
        return canonical_hash(self.initial_state_manifest)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "observable": RETENTION_FRACTION_OBSERVABLE,
            "time_s": self.time_s.tolist(),
            "predicted_retention_fraction": (
                self.predicted_retention_fraction.tolist()
            ),
            "initial_state": self.initial_state_manifest,
            "initial_state_hash": self.initial_state_hash,
        }


@dataclass
class DeviceRetentionFractionFitResult:
    """
    Single-parameter fit to total charge retention fraction versus time.

    ``FITTED`` denotes numerical optimization against the identified dataset.
    It does not imply independent validation or ``CALIBRATED`` provenance.
    """

    dataset_id: str
    dataset_hash: str
    calibration_specification_hash: str
    protocol: RetentionFitProtocol
    numerical_result: DeterministicFitResult
    device_objective: DeviceObjectiveEvaluation
    fitted_context: DeviceCalibrationContext
    prediction: RetentionFractionPrediction

    @property
    def objective(self) -> ObjectiveEvaluation:
        return self.device_objective.objective

    @property
    def fitted_parameter_values(self) -> dict[str, float]:
        return dict(self.fitted_context.parameter_values)

    @property
    def scientific_status(self) -> str:
        return "FITTED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "workflow": "single-parameter-retention-fraction-vs-time-fit",
            "scientific_status": self.scientific_status,
            "dataset_id": self.dataset_id,
            "dataset_hash": self.dataset_hash,
            "calibration_specification_hash": (
                self.calibration_specification_hash
            ),
            "protocol": self.protocol.to_dict(),
            "protocol_hash": self.protocol.protocol_hash(),
            "observable": RETENTION_FRACTION_OBSERVABLE,
            "initial_state_hash": self.prediction.initial_state_hash,
            "initial_state": self.prediction.initial_state_manifest,
            "parameter_application": (
                self.fitted_context.parameter_application_manifest()
            ),
            "simulation_time_s": self.prediction.time_s.tolist(),
            "simulated_retention_fraction": (
                self.prediction.predicted_retention_fraction.tolist()
            ),
            "predicted_values_on_dataset_grid": (
                self.device_objective.predicted_values.tolist()
            ),
            "numerical_result": self.numerical_result.to_dict(),
            "device_objective": self.device_objective.to_dict(),
            "objective": self.objective.to_dict(),
        }


def _require_retention_fraction_dataset(
    dataset: DeviceObservableDataset,
) -> None:
    if not isinstance(dataset, DeviceObservableDataset):
        raise TypeError(
            "dataset must be a DeviceObservableDataset."
        )

    if (
        dataset.independent_variable_name != "time"
        or dataset.independent_variable_unit != "s"
        or dataset.observable_name != RETENTION_FRACTION_OBSERVABLE
        or dataset.observable_unit is not None
    ):
        raise ValueError(
            "Retention-fraction fitting requires a dataset "
            "with time [s] -> "
            "total_charge_retention_fraction [dimensionless]."
        )

    times = np.asarray(dataset.independent_values, dtype=float)
    if not np.all(np.isfinite(times)) or np.any(times < 0.0):
        raise ValueError(
            "Retention dataset times must be finite and "
            "non-negative."
        )


def _reject_unmodeled_conditions(
    evaluation: DeviceObjectiveEvaluation,
) -> None:
    if evaluation.unmodeled_condition_names:
        names = ", ".join(evaluation.unmodeled_condition_names)
        raise ValueError(
            "Retention fitting does not model dataset "
            f"condition(s): {names}."
        )


def predict_retention_fraction(
    simulator: Simulator,
    protocol: RetentionFitProtocol,
    *,
    initial_state: DeviceState,
) -> RetentionFractionPrediction:
    """
    Simulate one continuous retention trajectory from a supplied initial state.

    The caller's state is never mutated.
    """

    if not isinstance(simulator, Simulator):
        raise TypeError(
            "simulator must be a Simulator instance."
        )
    if not isinstance(protocol, RetentionFitProtocol):
        raise TypeError(
            "protocol must be a RetentionFitProtocol."
        )
    if not isinstance(initial_state, DeviceState):
        raise TypeError(
            "initial_state must be a DeviceState."
        )

    initial_state.validate(simulator.device)
    state = initial_state.copy()
    state.validate(simulator.device)

    manifest = _initial_state_manifest(
        state,
        simulator.device,
    )

    result = simulator.simulate_retention(
        state,
        protocol.retention_config,
    )

    return RetentionFractionPrediction(
        time_s=result.time_s,
        predicted_retention_fraction=(
            result.total_charge_retention_fraction
        ),
        retention_result=result,
        initial_state_manifest=manifest,
    )


def _evaluate_candidate(
    dataset: DeviceObservableDataset,
    *,
    base_device: Device,
    base_physics: PhysicsModel,
    base_simulation_config: SimulationConfig,
    calibration_spec: DeviceCalibrationSpec,
    protocol: RetentionFitProtocol,
    parameter_values,
    initial_state: DeviceState,
) -> tuple[
    DeviceCalibrationContext,
    RetentionFractionPrediction,
    DeviceObjectiveEvaluation,
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

    prediction = predict_retention_fraction(
        simulator,
        protocol,
        initial_state=initial_state,
    )

    device_objective = evaluate_retention_objective(
        dataset,
        prediction.retention_result,
        retention_gate_voltage_V=(
            protocol.retention_config.gate_voltage_V
        ),
    )
    _reject_unmodeled_conditions(device_objective)

    return context, prediction, device_objective


def fit_single_parameter_retention_fraction(
    dataset: DeviceObservableDataset,
    *,
    base_device: Device,
    base_physics: PhysicsModel,
    base_simulation_config: SimulationConfig,
    calibration_spec: DeviceCalibrationSpec,
    protocol: RetentionFitProtocol,
    initial_state: DeviceState,
    least_squares_config: LeastSquaresConfig | None = None,
) -> DeviceRetentionFractionFitResult:
    """
    Fit exactly one device parameter to charge-retention fraction versus time.

    F4h2c2c intentionally remains single-parameter. The fitted observable is
    ``RetentionResult.total_charge_retention_fraction`` from one continuous
    fixed-bias trajectory. The F4g retention objective adapter performs
    physical-time interpolation and rejects extrapolation.
    """

    _require_retention_fraction_dataset(dataset)

    if not isinstance(base_device, Device):
        raise TypeError(
            "base_device must be a Device instance."
        )
    if not isinstance(base_physics, PhysicsModel):
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
            "calibration_spec must be a DeviceCalibrationSpec."
        )
    if not isinstance(protocol, RetentionFitProtocol):
        raise TypeError(
            "protocol must be a RetentionFitProtocol."
        )
    if not isinstance(initial_state, DeviceState):
        raise TypeError(
            "initial_state must be a DeviceState."
        )

    if calibration_spec.parameter_set.n_parameters != 1:
        raise ValueError(
            "F4h2c2c retention fitting requires "
            "exactly one free parameter."
        )

    base_device.validate()
    initial_state.validate(base_device)

    # Preflight validates the full simulator path, the retention-gate
    # condition, unsupported conditions and the no-extrapolation rule before
    # the optimizer is entered.
    _evaluate_candidate(
        dataset,
        base_device=base_device,
        base_physics=base_physics,
        base_simulation_config=base_simulation_config,
        calibration_spec=calibration_spec,
        protocol=protocol,
        parameter_values=calibration_spec.parameter_set.initial_values,
        initial_state=initial_state,
    )

    def residual_function(parameter_values):
        _, _, device_objective = _evaluate_candidate(
            dataset,
            base_device=base_device,
            base_physics=base_physics,
            base_simulation_config=base_simulation_config,
            calibration_spec=calibration_spec,
            protocol=protocol,
            parameter_values=parameter_values,
            initial_state=initial_state,
        )
        return device_objective.objective.objective_residuals

    numerical_result = run_least_squares_fit(
        calibration_spec.parameter_set,
        residual_function,
        config=least_squares_config,
    )

    (
        fitted_context,
        prediction,
        device_objective,
    ) = _evaluate_candidate(
        dataset,
        base_device=base_device,
        base_physics=base_physics,
        base_simulation_config=base_simulation_config,
        calibration_spec=calibration_spec,
        protocol=protocol,
        parameter_values=numerical_result.fitted_values,
        initial_state=initial_state,
    )

    return DeviceRetentionFractionFitResult(
        dataset_id=dataset.metadata.dataset_id,
        dataset_hash=dataset.dataset_hash(),
        calibration_specification_hash=(
            calibration_spec.specification_hash()
        ),
        protocol=protocol,
        numerical_result=numerical_result,
        device_objective=device_objective,
        fitted_context=fitted_context,
        prediction=prediction,
    )


__all__ = [
    "DeviceRetentionFractionFitResult",
    "RETENTION_FRACTION_OBSERVABLE",
    "RETENTION_INITIAL_STATE_SEMANTICS",
    "RETENTION_INTERPOLATION_SEMANTICS",
    "RETENTION_TRAJECTORY_SEMANTICS",
    "RetentionFitProtocol",
    "RetentionFractionPrediction",
    "fit_single_parameter_retention_fraction",
    "predict_retention_fraction",
]
