from __future__ import annotations

from dataclasses import dataclass
import math

from .device import Device
from .device_calibration import (
    DeviceCalibrationContext,
    DeviceCalibrationSpec,
    apply_device_calibration_parameters,
)
from .device_objectives import (
    DeviceObjectiveEvaluation,
    evaluate_cv_objective,
)
from .experimental import DeviceObservableDataset
from .fitting import (
    DeterministicFitResult,
    LeastSquaresConfig,
    run_least_squares_fit,
)
from .hashing import canonical_hash
from .physics import PhysicsModel
from .simulator import CVResult, SimulationConfig, Simulator


@dataclass(frozen=True)
class CVCalibrationProtocol:
    """
    Explicit simulator protocol for one C-V calibration workflow.

    ``dwell_time_s`` is intentionally not re-labeled as programming time:
    it remains the per-voltage relaxation time stored in SimulationConfig.
    """

    vmin_V: float = -3.0
    vmax_V: float = 3.0
    points: int = 121

    def __post_init__(self) -> None:
        vmin = float(self.vmin_V)
        vmax = float(self.vmax_V)
        if not math.isfinite(vmin) or not math.isfinite(vmax):
            raise ValueError("vmin_V and vmax_V must be finite.")
        if not vmin < vmax:
            raise ValueError("vmin_V must be strictly less than vmax_V.")
        if isinstance(self.points, bool) or not isinstance(self.points, int):
            raise TypeError("points must be an integer.")
        if self.points < 3:
            raise ValueError("points must be at least three.")
        object.__setattr__(self, "vmin_V", vmin)
        object.__setattr__(self, "vmax_V", vmax)

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "vmin_V": self.vmin_V,
            "vmax_V": self.vmax_V,
            "points": self.points,
        }

    def protocol_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass
class DeviceCVFitResult:
    """
    End-to-end numerical fit of one C-V dataset.

    FITTED means optimized against the identified dataset. It does not imply
    independent validation and does not imply CALIBRATED status.
    """

    dataset_id: str
    dataset_hash: str
    calibration_specification_hash: str
    protocol: CVCalibrationProtocol
    numerical_result: DeterministicFitResult
    objective: DeviceObjectiveEvaluation
    fitted_context: DeviceCalibrationContext
    cv_result: CVResult

    @property
    def fitted_parameter_values(self) -> dict[str, float]:
        return dict(self.fitted_context.parameter_values)

    @property
    def scientific_status(self) -> str:
        return "FITTED"

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "workflow": "single-dataset-cv-fit",
            "scientific_status": self.scientific_status,
            "dataset_id": self.dataset_id,
            "dataset_hash": self.dataset_hash,
            "calibration_specification_hash": self.calibration_specification_hash,
            "protocol": self.protocol.to_dict(),
            "protocol_hash": self.protocol.protocol_hash(),
            "parameter_application": (
                self.fitted_context.parameter_application_manifest()
            ),
            "numerical_result": self.numerical_result.to_dict(),
            "objective": self.objective.to_dict(),
        }


def _require_cv_dataset(dataset: DeviceObservableDataset) -> None:
    if not isinstance(dataset, DeviceObservableDataset):
        raise TypeError("dataset must be a DeviceObservableDataset.")

    if (
        dataset.independent_variable_name != "gate_voltage"
        or dataset.independent_variable_unit != "V"
        or dataset.observable_name != "capacitance"
        or dataset.observable_unit != "F/m^2"
    ):
        raise ValueError(
            "C-V fitting requires a dataset with "
            "gate_voltage [V] -> capacitance [F/m^2]."
        )


def _evaluate_candidate(
    dataset: DeviceObservableDataset,
    *,
    base_device: Device,
    base_physics: PhysicsModel,
    base_simulation_config: SimulationConfig,
    calibration_spec: DeviceCalibrationSpec,
    protocol: CVCalibrationProtocol,
    parameter_values,
) -> tuple[DeviceCalibrationContext, CVResult, DeviceObjectiveEvaluation]:
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

    cv_result = simulator.simulate_cv(
        vmin_V=protocol.vmin_V,
        vmax_V=protocol.vmax_V,
        points=protocol.points,
    )

    objective = evaluate_cv_objective(dataset, cv_result)
    return context, cv_result, objective


def fit_single_parameter_cv_dataset(
    dataset: DeviceObservableDataset,
    *,
    base_device: Device,
    base_physics: PhysicsModel,
    base_simulation_config: SimulationConfig,
    calibration_spec: DeviceCalibrationSpec,
    protocol: CVCalibrationProtocol,
    least_squares_config: LeastSquaresConfig | None = None,
) -> DeviceCVFitResult:
    """
    Fit exactly one device-level parameter to one C-V dataset.

    Every optimizer evaluation is rebuilt from the same baseline objects
    through ``apply_device_calibration_parameters`` so successive evaluations
    cannot accumulate model mutations.
    """

    _require_cv_dataset(dataset)

    if not isinstance(base_device, Device):
        raise TypeError("base_device must be a Device instance.")
    if not isinstance(base_physics, PhysicsModel):
        raise TypeError("base_physics must be a PhysicsModel instance.")
    if not isinstance(base_simulation_config, SimulationConfig):
        raise TypeError(
            "base_simulation_config must be a SimulationConfig instance."
        )
    if not isinstance(calibration_spec, DeviceCalibrationSpec):
        raise TypeError("calibration_spec must be a DeviceCalibrationSpec.")
    if not isinstance(protocol, CVCalibrationProtocol):
        raise TypeError("protocol must be a CVCalibrationProtocol.")

    if calibration_spec.parameter_set.n_parameters != 1:
        raise ValueError(
            "F4h2a single-dataset C-V fitting requires exactly one free parameter."
        )

    # Early compatibility/domain validation at the configured initial value.
    _evaluate_candidate(
        dataset,
        base_device=base_device,
        base_physics=base_physics,
        base_simulation_config=base_simulation_config,
        calibration_spec=calibration_spec,
        protocol=protocol,
        parameter_values=calibration_spec.parameter_set.initial_values,
    )

    def residual_function(parameter_values):
        _, _, evaluation = _evaluate_candidate(
            dataset,
            base_device=base_device,
            base_physics=base_physics,
            base_simulation_config=base_simulation_config,
            calibration_spec=calibration_spec,
            protocol=protocol,
            parameter_values=parameter_values,
        )
        return evaluation.objective.objective_residuals

    numerical_result = run_least_squares_fit(
        calibration_spec.parameter_set,
        residual_function,
        config=least_squares_config,
    )

    fitted_context, cv_result, objective = _evaluate_candidate(
        dataset,
        base_device=base_device,
        base_physics=base_physics,
        base_simulation_config=base_simulation_config,
        calibration_spec=calibration_spec,
        protocol=protocol,
        parameter_values=numerical_result.fitted_values,
    )

    return DeviceCVFitResult(
        dataset_id=dataset.metadata.dataset_id,
        dataset_hash=dataset.dataset_hash(),
        calibration_specification_hash=calibration_spec.specification_hash(),
        protocol=protocol,
        numerical_result=numerical_result,
        objective=objective,
        fitted_context=fitted_context,
        cv_result=cv_result,
    )


__all__ = [
    "CVCalibrationProtocol",
    "DeviceCVFitResult",
    "fit_single_parameter_cv_dataset",
]
