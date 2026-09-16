from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Sequence

import numpy as np

from .device import Device
from .device_calibration import (
    DeviceCalibrationContext,
    DeviceCalibrationSpec,
    DeviceFitTarget,
    apply_device_calibration_parameters,
)
from .electro_optical_program_protocol import (
    ElectroOpticalProgramPulseReadProtocol,
    ElectroOpticalProgramPulseReadResult,
    run_electro_optical_program_pulse_read,
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
from .optics import LightSource
from .photo import PhotoTransitionConfig, PhotoTransitionWeights
from .physics import PhysicsModel
from .program_protocol import ProgramPulseReadProtocol
from .simulator import SimulationConfig, Simulator
from .state import DeviceState


def _readonly_float_array(values) -> np.ndarray:
    array = np.array(values, dtype=float, copy=True)
    array.setflags(write=False)
    return array


def _photo_weights_dict(
    weights: PhotoTransitionWeights,
) -> dict[str, float]:
    return {
        "r01": float(weights.r01),
        "r12": float(weights.r12),
        "r10": float(weights.r10),
        "r21": float(weights.r21),
    }


@dataclass(frozen=True)
class ElectroOpticalProgramTimeFitProtocol:
    """
    Time-series protocol for illuminated program-pulse delta-VFB prediction.

    Programming times are supplied by the caller or dataset. Every time point
    is simulated independently from one common initial state. Illumination is
    active only during each program pulse; the read is dark and zero-dwell.

    ``photo_capture_efficiency`` is not part of this protocol. It is supplied
    separately through ``PhotoTransitionConfig`` so the fitted device
    parameter remains distinct from the experimental optical conditions.
    """

    program_voltage_V: float
    light_source: LightSource
    photo_weights: PhotoTransitionWeights
    read_voltage_V: float = 0.0
    program_internal_dt_s: float | None = None
    occupancy_integrator: str = "explicit_euler"

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
            if not math.isfinite(program_dt) or program_dt <= 0.0:
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

        # Delegate optical-source, transition-weight, and integrator validation
        # to the public F4i2 pulse protocol instead of duplicating those rules.
        self.pulse_protocol(1.0)

    def pulse_protocol(
        self,
        programming_time_s: float,
    ) -> ElectroOpticalProgramPulseReadProtocol:
        electrical = ProgramPulseReadProtocol(
            program_voltage_V=self.program_voltage_V,
            programming_time_s=programming_time_s,
            read_voltage_V=self.read_voltage_V,
            program_internal_dt_s=self.program_internal_dt_s,
        )
        return ElectroOpticalProgramPulseReadProtocol(
            electrical_protocol=electrical,
            light_source=self.light_source,
            photo_weights=self.photo_weights,
            occupancy_integrator=self.occupancy_integrator,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "workflow": (
                "electro-optical-delta-vfb-vs-programming-time"
            ),
            "program_voltage_V": self.program_voltage_V,
            "read_voltage_V": self.read_voltage_V,
            "program_internal_dt_s": self.program_internal_dt_s,
            "light_source": self.light_source.to_dict(),
            "photo_transition_weights": _photo_weights_dict(
                self.photo_weights
            ),
            "occupancy_integrator": self.occupancy_integrator,
            "time_point_semantics": (
                "independent-pulses-from-common-initial-state"
            ),
            "illumination_semantics": "program-pulse-only",
            "read_illumination": "dark",
            "read_dwell_time_s": 0.0,
            "photo_capture_efficiency_semantics": (
                "supplied-at-execution-not-part-of-protocol"
            ),
        }

    def protocol_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass
class ElectroOpticalProgramTimePrediction:
    """Predicted illuminated delta-VFB values on a programming-time grid."""

    programming_times_s: np.ndarray
    predicted_delta_vfb_V: np.ndarray
    pulse_results: tuple[
        ElectroOpticalProgramPulseReadResult,
        ...,
    ]

    def __post_init__(self) -> None:
        times = _readonly_float_array(
            self.programming_times_s
        )
        predicted = _readonly_float_array(
            self.predicted_delta_vfb_V
        )
        pulse_results = tuple(self.pulse_results)

        if times.ndim != 1 or predicted.ndim != 1:
            raise ValueError(
                "programming_times_s and predicted_delta_vfb_V "
                "must be one-dimensional."
            )
        if times.size == 0:
            raise ValueError(
                "Electro-optical program-time prediction cannot be empty."
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
                "programming_times_s must contain finite, "
                "strictly positive values."
            )
        if not np.all(np.isfinite(predicted)):
            raise ValueError(
                "predicted_delta_vfb_V must contain only finite values."
            )
        if any(
            not isinstance(
                result,
                ElectroOpticalProgramPulseReadResult,
            )
            for result in pulse_results
        ):
            raise TypeError(
                "pulse_results must contain only "
                "ElectroOpticalProgramPulseReadResult instances."
            )

        self.programming_times_s = times
        self.predicted_delta_vfb_V = predicted
        self.pulse_results = pulse_results


def predict_electro_optical_delta_vfb_vs_programming_time(
    simulator: Simulator,
    programming_times_s: Sequence[float] | np.ndarray,
    protocol: ElectroOpticalProgramTimeFitProtocol,
    *,
    photo_config: PhotoTransitionConfig,
    initial_state: DeviceState | None = None,
) -> ElectroOpticalProgramTimePrediction:
    """
    Predict illuminated delta-VFB for independent programming-time points.

    Every point starts from the same initial state. ``photo_config`` is explicit
    because ``photo_capture_efficiency`` may be the device parameter varied by
    the fitting layer introduced after this prediction adapter.
    """

    if not isinstance(simulator, Simulator):
        raise TypeError(
            "simulator must be a Simulator instance."
        )
    if not isinstance(
        protocol,
        ElectroOpticalProgramTimeFitProtocol,
    ):
        raise TypeError(
            "protocol must be an "
            "ElectroOpticalProgramTimeFitProtocol."
        )
    if not isinstance(photo_config, PhotoTransitionConfig):
        raise TypeError(
            "photo_config must be a PhotoTransitionConfig."
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
        common_initial = DeviceState.empty_for_device(
            simulator.device
        )
    else:
        if not isinstance(initial_state, DeviceState):
            raise TypeError(
                "initial_state must be a DeviceState or None."
            )
        initial_state.validate(simulator.device)
        common_initial = initial_state.copy()

    common_initial.validate(simulator.device)

    pulse_results = tuple(
        run_electro_optical_program_pulse_read(
            simulator,
            protocol.pulse_protocol(
                float(programming_time_s)
            ),
            photo_config=photo_config,
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

    return ElectroOpticalProgramTimePrediction(
        programming_times_s=times,
        predicted_delta_vfb_V=predicted,
        pulse_results=pulse_results,
    )




@dataclass
class DevicePhotoProgramTimeFitResult:
    """
    Single-parameter numerical fit of photo-capture efficiency to illuminated
    delta-VFB(programming_time) data.

    ``FITTED`` reports numerical optimization against the identified dataset.
    It does not imply independent experimental validation or CALIBRATED
    provenance.
    """

    dataset_id: str
    dataset_hash: str
    calibration_specification_hash: str
    protocol: ElectroOpticalProgramTimeFitProtocol
    numerical_result: DeterministicFitResult
    objective: ObjectiveEvaluation
    fitted_context: DeviceCalibrationContext
    prediction: ElectroOpticalProgramTimePrediction

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
        if self.fitted_context.photo_config is None:
            raise ValueError(
                "Photo-program fit result requires a fitted photo_config."
            )

        return {
            "schema_version": 1,
            "workflow": (
                "single-parameter-photo-capture-efficiency-"
                "vs-programming-time-fit"
            ),
            "scientific_status": self.scientific_status,
            "dataset_id": self.dataset_id,
            "dataset_hash": self.dataset_hash,
            "calibration_specification_hash": (
                self.calibration_specification_hash
            ),
            "protocol": self.protocol.to_dict(),
            "protocol_hash": self.protocol.protocol_hash(),
            "parameter_application": (
                self.fitted_context
                .parameter_application_manifest()
            ),
            "fitted_photo_transition_config": {
                "photo_capture_efficiency": (
                    self.fitted_context
                    .photo_config
                    .photo_capture_efficiency
                ),
            },
            "programming_times_s": (
                self.prediction.programming_times_s.tolist()
            ),
            "predicted_delta_vfb_V": (
                self.prediction.predicted_delta_vfb_V.tolist()
            ),
            "numerical_result": (
                self.numerical_result.to_dict()
            ),
            "objective": self.objective.to_dict(),
        }


def _condition_value(
    dataset: DeviceObservableDataset,
    name: str,
):
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


def _require_numeric_condition(
    dataset: DeviceObservableDataset,
    *,
    name: str,
    expected_unit: str,
    actual_value: float,
    actual_value_name: str,
) -> None:
    condition = _condition_value(dataset, name)

    if condition.unit != expected_unit:
        raise ValueError(
            f"Condition {name!r} must use unit "
            f"{expected_unit!r}."
        )

    if isinstance(condition.value, bool):
        raise ValueError(
            f"Condition {name!r} must contain a numeric value."
        )

    try:
        expected = float(condition.value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Condition {name!r} must contain a numeric value."
        ) from exc

    actual = float(actual_value)

    if not math.isfinite(expected) or not math.isfinite(actual):
        raise ValueError(
            f"Condition {name!r} and {actual_value_name} "
            "must both be finite."
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


def _require_photo_program_time_dataset(
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
            "Photo-capture fitting requires a dataset with "
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


def _validate_photo_protocol_conditions(
    dataset: DeviceObservableDataset,
    protocol: ElectroOpticalProgramTimeFitProtocol,
) -> None:
    wavelength_nm = protocol.light_source.wavelength_nm
    if wavelength_nm is None:
        raise ValueError(
            "Photo-capture fitting currently requires "
            "a monochromatic light source with wavelength_nm."
        )

    _require_numeric_condition(
        dataset,
        name="program_voltage",
        expected_unit="V",
        actual_value=protocol.program_voltage_V,
        actual_value_name="protocol.program_voltage_V",
    )
    _require_numeric_condition(
        dataset,
        name="read_voltage",
        expected_unit="V",
        actual_value=protocol.read_voltage_V,
        actual_value_name="protocol.read_voltage_V",
    )
    _require_numeric_condition(
        dataset,
        name="wavelength",
        expected_unit="nm",
        actual_value=float(wavelength_nm),
        actual_value_name="protocol.light_source.wavelength_nm",
    )
    _require_numeric_condition(
        dataset,
        name="optical_power_density",
        expected_unit="W/m^2",
        actual_value=(
            protocol.light_source.power_density_W_m2
        ),
        actual_value_name=(
            "protocol.light_source.power_density_W_m2"
        ),
    )


def _evaluate_photo_candidate(
    dataset: DeviceObservableDataset,
    *,
    base_device: Device,
    base_physics: PhysicsModel,
    base_simulation_config: SimulationConfig,
    base_photo_config: PhotoTransitionConfig,
    calibration_spec: DeviceCalibrationSpec,
    protocol: ElectroOpticalProgramTimeFitProtocol,
    parameter_values,
) -> tuple[
    DeviceCalibrationContext,
    ElectroOpticalProgramTimePrediction,
    ObjectiveEvaluation,
]:
    context = apply_device_calibration_parameters(
        base_device,
        base_physics,
        base_simulation_config,
        calibration_spec,
        parameter_values,
        base_photo_config=base_photo_config,
    )

    if context.photo_config is None:
        raise ValueError(
            "Photo-capture fitting requires a photo_config "
            "after parameter application."
        )

    simulator = Simulator(
        context.device,
        context.physics,
        context.simulation_config,
    )

    prediction = (
        predict_electro_optical_delta_vfb_vs_programming_time(
            simulator,
            dataset.independent_values,
            protocol,
            photo_config=context.photo_config,
        )
    )

    objective = evaluate_least_squares_objective(
        dataset.observed_values,
        prediction.predicted_delta_vfb_V,
        uncertainty=dataset.observed_uncertainty,
    )

    return context, prediction, objective


def fit_single_parameter_photo_capture_efficiency_vs_programming_time(
    dataset: DeviceObservableDataset,
    *,
    base_device: Device,
    base_physics: PhysicsModel,
    base_simulation_config: SimulationConfig,
    base_photo_config: PhotoTransitionConfig,
    calibration_spec: DeviceCalibrationSpec,
    protocol: ElectroOpticalProgramTimeFitProtocol,
    least_squares_config: LeastSquaresConfig | None = None,
) -> DevicePhotoProgramTimeFitResult:
    """
    Fit exactly one photo-capture-efficiency parameter to illuminated
    delta-VFB(programming_time) data.

    F4i3b is intentionally limited to one free parameter and to the
    ``PHOTO_CAPTURE_EFFICIENCY`` device target. Wavelength, optical power,
    pulse voltage, read voltage, transition weights, and numerical integration
    remain fixed protocol conditions.

    The result is numerical ``FITTED`` provenance only. It is not a
    ``CALIBRATED`` device parameter without independent validation.
    """

    _require_photo_program_time_dataset(
        dataset
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
        base_photo_config,
        PhotoTransitionConfig,
    ):
        raise TypeError(
            "base_photo_config must be a "
            "PhotoTransitionConfig instance."
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
        ElectroOpticalProgramTimeFitProtocol,
    ):
        raise TypeError(
            "protocol must be an "
            "ElectroOpticalProgramTimeFitProtocol."
        )

    _validate_photo_protocol_conditions(
        dataset,
        protocol,
    )

    if (
        calibration_spec.parameter_set.n_parameters
        != 1
    ):
        raise ValueError(
            "F4i3b photo-capture fitting requires "
            "exactly one free parameter."
        )

    binding = calibration_spec.bindings[0]
    if (
        binding.target
        != DeviceFitTarget.PHOTO_CAPTURE_EFFICIENCY
    ):
        raise ValueError(
            "F4i3b photo-capture fitting requires the "
            "single free parameter to target "
            "DeviceFitTarget.PHOTO_CAPTURE_EFFICIENCY."
        )

    # Fail early on model/protocol/dataset incompatibility.
    _evaluate_photo_candidate(
        dataset,
        base_device=base_device,
        base_physics=base_physics,
        base_simulation_config=(
            base_simulation_config
        ),
        base_photo_config=base_photo_config,
        calibration_spec=calibration_spec,
        protocol=protocol,
        parameter_values=(
            calibration_spec
            .parameter_set.initial_values
        ),
    )

    def residual_function(parameter_values):
        _, _, objective = _evaluate_photo_candidate(
            dataset,
            base_device=base_device,
            base_physics=base_physics,
            base_simulation_config=(
                base_simulation_config
            ),
            base_photo_config=base_photo_config,
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
    ) = _evaluate_photo_candidate(
        dataset,
        base_device=base_device,
        base_physics=base_physics,
        base_simulation_config=(
            base_simulation_config
        ),
        base_photo_config=base_photo_config,
        calibration_spec=calibration_spec,
        protocol=protocol,
        parameter_values=(
            numerical_result.fitted_values
        ),
    )

    return DevicePhotoProgramTimeFitResult(
        dataset_id=dataset.metadata.dataset_id,
        dataset_hash=dataset.dataset_hash(),
        calibration_specification_hash=(
            calibration_spec.specification_hash()
        ),
        protocol=protocol,
        numerical_result=numerical_result,
        objective=objective,
        fitted_context=fitted_context,
        prediction=prediction,
    )



def _multi_condition_nonoptical_manifest(
    protocol: ElectroOpticalProgramTimeFitProtocol,
) -> dict[str, Any]:
    return {
        "program_voltage_V": protocol.program_voltage_V,
        "read_voltage_V": protocol.read_voltage_V,
        "program_internal_dt_s": (
            protocol.program_internal_dt_s
        ),
        "photo_transition_weights": _photo_weights_dict(
            protocol.photo_weights
        ),
        "occupancy_integrator": protocol.occupancy_integrator,
    }


def _validate_photo_multi_condition_pairs(
    datasets: Sequence[DeviceObservableDataset],
    protocols: Sequence[
        ElectroOpticalProgramTimeFitProtocol
    ],
) -> tuple[
    tuple[DeviceObservableDataset, ...],
    tuple[ElectroOpticalProgramTimeFitProtocol, ...],
]:
    dataset_tuple = tuple(datasets)
    protocol_tuple = tuple(protocols)

    if len(dataset_tuple) < 2:
        raise ValueError(
            "Multi-condition photo-capture fitting requires "
            "at least two datasets."
        )
    if len(dataset_tuple) != len(protocol_tuple):
        raise ValueError(
            "datasets and protocols must contain the same "
            "number of entries."
        )

    for dataset, protocol in zip(
        dataset_tuple,
        protocol_tuple,
    ):
        _require_photo_program_time_dataset(dataset)
        if not isinstance(
            protocol,
            ElectroOpticalProgramTimeFitProtocol,
        ):
            raise TypeError(
                "protocols must contain only "
                "ElectroOpticalProgramTimeFitProtocol instances."
            )
        _validate_photo_protocol_conditions(
            dataset,
            protocol,
        )

    dataset_hashes = tuple(
        dataset.dataset_hash()
        for dataset in dataset_tuple
    )
    if len(set(dataset_hashes)) != len(dataset_hashes):
        raise ValueError(
            "Multi-condition fitting rejects duplicate datasets "
            "to avoid accidental repeated weighting."
        )

    weighting_modes = tuple(
        dataset.observed_uncertainty is not None
        for dataset in dataset_tuple
    )
    if len(set(weighting_modes)) != 1:
        raise ValueError(
            "All multi-condition datasets must either provide "
            "pointwise uncertainty or all omit it."
        )

    reference_nonoptical_hash = canonical_hash(
        _multi_condition_nonoptical_manifest(
            protocol_tuple[0]
        )
    )
    for protocol in protocol_tuple[1:]:
        current_hash = canonical_hash(
            _multi_condition_nonoptical_manifest(
                protocol
            )
        )
        if current_hash != reference_nonoptical_hash:
            raise ValueError(
                "F4i4a varies optical source conditions only; "
                "program/read voltages, program timestep, "
                "photo-transition weights, and occupancy "
                "integrator must remain identical across "
                "multi-condition protocols."
            )

    optical_conditions = tuple(
        (
            float(protocol.light_source.wavelength_nm),
            float(
                protocol.light_source
                .power_density_W_m2
            ),
        )
        for protocol in protocol_tuple
    )
    if len(set(optical_conditions)) < 2:
        raise ValueError(
            "Multi-condition fitting requires at least two "
            "distinct (wavelength_nm, power_density_W_m2) "
            "optical conditions."
        )

    return dataset_tuple, protocol_tuple


@dataclass
class DevicePhotoMultiConditionFitResult:
    """
    Shared single-parameter photo-capture fit across multiple optical
    conditions.

    The same fitted device-level ``photo_capture_efficiency`` is applied to
    every condition. Per-condition objectives remain explicit, while the
    optimizer sees their concatenated residual vector.

    This is numerical ``FITTED`` provenance only. Multi-condition consistency
    improves the identifiability test but does not itself establish
    ``CALIBRATED`` provenance.
    """

    dataset_ids: tuple[str, ...]
    dataset_hashes: tuple[str, ...]
    protocols: tuple[
        ElectroOpticalProgramTimeFitProtocol,
        ...,
    ]
    calibration_specification_hash: str
    numerical_result: DeterministicFitResult
    objectives: tuple[ObjectiveEvaluation, ...]
    fitted_context: DeviceCalibrationContext
    predictions: tuple[
        ElectroOpticalProgramTimePrediction,
        ...,
    ]

    def __post_init__(self) -> None:
        dataset_ids = tuple(self.dataset_ids)
        dataset_hashes = tuple(self.dataset_hashes)
        protocols = tuple(self.protocols)
        objectives = tuple(self.objectives)
        predictions = tuple(self.predictions)

        n_conditions = len(dataset_ids)
        if n_conditions < 2:
            raise ValueError(
                "Multi-condition fit results require at least "
                "two conditions."
            )
        if not (
            len(dataset_hashes)
            == len(protocols)
            == len(objectives)
            == len(predictions)
            == n_conditions
        ):
            raise ValueError(
                "Multi-condition result fields must have "
                "matching condition counts."
            )

        if any(
            not isinstance(
                protocol,
                ElectroOpticalProgramTimeFitProtocol,
            )
            for protocol in protocols
        ):
            raise TypeError(
                "protocols must contain only "
                "ElectroOpticalProgramTimeFitProtocol instances."
            )
        if any(
            not isinstance(
                objective,
                ObjectiveEvaluation,
            )
            for objective in objectives
        ):
            raise TypeError(
                "objectives must contain only "
                "ObjectiveEvaluation instances."
            )
        if any(
            not isinstance(
                prediction,
                ElectroOpticalProgramTimePrediction,
            )
            for prediction in predictions
        ):
            raise TypeError(
                "predictions must contain only "
                "ElectroOpticalProgramTimePrediction instances."
            )

        self.dataset_ids = dataset_ids
        self.dataset_hashes = dataset_hashes
        self.protocols = protocols
        self.objectives = objectives
        self.predictions = predictions

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

    @property
    def n_conditions(self) -> int:
        return len(self.dataset_ids)

    @property
    def n_observations(self) -> int:
        return int(
            sum(
                objective.n_points
                for objective in self.objectives
            )
        )

    @property
    def weighted(self) -> bool:
        return all(
            objective.weighted
            for objective in self.objectives
        )

    @property
    def joint_objective_residuals(
        self,
    ) -> np.ndarray:
        residuals = np.concatenate(
            [
                objective.objective_residuals
                for objective in self.objectives
            ]
        ).astype(float, copy=True)
        residuals.setflags(write=False)
        return residuals

    @property
    def joint_raw_residuals_V(
        self,
    ) -> np.ndarray:
        residuals = np.concatenate(
            [
                objective.residuals
                for objective in self.objectives
            ]
        ).astype(float, copy=True)
        residuals.setflags(write=False)
        return residuals

    @property
    def joint_objective_sum_squares(self) -> float:
        residuals = self.joint_objective_residuals
        return float(np.dot(residuals, residuals))

    @property
    def joint_root_mean_square_error_V(self) -> float:
        residuals = self.joint_raw_residuals_V
        return float(
            np.sqrt(
                np.dot(residuals, residuals)
                / residuals.size
            )
        )

    def to_dict(self) -> dict[str, Any]:
        if self.fitted_context.photo_config is None:
            raise ValueError(
                "Multi-condition photo fit requires a fitted "
                "photo_config."
            )

        conditions = []
        for (
            dataset_id,
            dataset_hash,
            protocol,
            objective,
            prediction,
        ) in zip(
            self.dataset_ids,
            self.dataset_hashes,
            self.protocols,
            self.objectives,
            self.predictions,
        ):
            conditions.append(
                {
                    "dataset_id": dataset_id,
                    "dataset_hash": dataset_hash,
                    "protocol": protocol.to_dict(),
                    "protocol_hash": (
                        protocol.protocol_hash()
                    ),
                    "programming_times_s": (
                        prediction
                        .programming_times_s
                        .tolist()
                    ),
                    "predicted_delta_vfb_V": (
                        prediction
                        .predicted_delta_vfb_V
                        .tolist()
                    ),
                    "objective": objective.to_dict(),
                }
            )

        return {
            "schema_version": 1,
            "workflow": (
                "shared-photo-capture-efficiency-"
                "multi-optical-condition-fit"
            ),
            "scientific_status": self.scientific_status,
            "n_conditions": self.n_conditions,
            "n_observations": self.n_observations,
            "weighted": self.weighted,
            "calibration_specification_hash": (
                self.calibration_specification_hash
            ),
            "parameter_application": (
                self.fitted_context
                .parameter_application_manifest()
            ),
            "fitted_photo_transition_config": {
                "photo_capture_efficiency": (
                    self.fitted_context
                    .photo_config
                    .photo_capture_efficiency
                ),
            },
            "joint_objective_sum_squares": (
                self.joint_objective_sum_squares
            ),
            "joint_root_mean_square_error_V": (
                self.joint_root_mean_square_error_V
            ),
            "joint_objective_residuals": (
                self.joint_objective_residuals.tolist()
            ),
            "numerical_result": (
                self.numerical_result.to_dict()
            ),
            "conditions": conditions,
        }


def _evaluate_photo_multi_condition_candidate(
    datasets: tuple[DeviceObservableDataset, ...],
    protocols: tuple[
        ElectroOpticalProgramTimeFitProtocol,
        ...,
    ],
    *,
    base_device: Device,
    base_physics: PhysicsModel,
    base_simulation_config: SimulationConfig,
    base_photo_config: PhotoTransitionConfig,
    calibration_spec: DeviceCalibrationSpec,
    parameter_values,
) -> tuple[
    DeviceCalibrationContext,
    tuple[ElectroOpticalProgramTimePrediction, ...],
    tuple[ObjectiveEvaluation, ...],
    np.ndarray,
]:
    context = apply_device_calibration_parameters(
        base_device,
        base_physics,
        base_simulation_config,
        calibration_spec,
        parameter_values,
        base_photo_config=base_photo_config,
    )

    if context.photo_config is None:
        raise ValueError(
            "Multi-condition photo fitting requires a "
            "photo_config after parameter application."
        )

    predictions: list[
        ElectroOpticalProgramTimePrediction
    ] = []
    objectives: list[ObjectiveEvaluation] = []

    for dataset, protocol in zip(
        datasets,
        protocols,
    ):
        prediction = (
            predict_electro_optical_delta_vfb_vs_programming_time(
                Simulator(
                    context.device,
                    context.physics,
                    context.simulation_config,
                ),
                dataset.independent_values,
                protocol,
                photo_config=context.photo_config,
            )
        )
        objective = evaluate_least_squares_objective(
            dataset.observed_values,
            prediction.predicted_delta_vfb_V,
            uncertainty=dataset.observed_uncertainty,
        )
        predictions.append(prediction)
        objectives.append(objective)

    objective_tuple = tuple(objectives)
    joint_residuals = np.concatenate(
        [
            objective.objective_residuals
            for objective in objective_tuple
        ]
    ).astype(float, copy=True)

    return (
        context,
        tuple(predictions),
        objective_tuple,
        joint_residuals,
    )


def fit_single_parameter_photo_capture_efficiency_multi_condition(
    datasets: Sequence[DeviceObservableDataset],
    protocols: Sequence[
        ElectroOpticalProgramTimeFitProtocol
    ],
    *,
    base_device: Device,
    base_physics: PhysicsModel,
    base_simulation_config: SimulationConfig,
    base_photo_config: PhotoTransitionConfig,
    calibration_spec: DeviceCalibrationSpec,
    least_squares_config: LeastSquaresConfig | None = None,
) -> DevicePhotoMultiConditionFitResult:
    """
    Fit one shared photo-capture-efficiency parameter across multiple optical
    conditions.

    F4i4a deliberately varies only wavelength and/or incident optical power.
    Electrical pulse/read settings, photo-transition weights, numerical
    integration, and the fitted device parameter are shared across all
    conditions.

    The optimizer receives the concatenation of each condition's residual
    vector. Datasets must use a consistent weighting mode: either all provide
    pointwise uncertainty or all omit it.

    The result is ``FITTED`` only. Identifiability diagnostics are attached in
    the subsequent F4i4b checkpoint.
    """

    dataset_tuple, protocol_tuple = (
        _validate_photo_multi_condition_pairs(
            datasets,
            protocols,
        )
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
        base_photo_config,
        PhotoTransitionConfig,
    ):
        raise TypeError(
            "base_photo_config must be a "
            "PhotoTransitionConfig instance."
        )
    if not isinstance(
        calibration_spec,
        DeviceCalibrationSpec,
    ):
        raise TypeError(
            "calibration_spec must be a "
            "DeviceCalibrationSpec."
        )

    if (
        calibration_spec.parameter_set.n_parameters
        != 1
    ):
        raise ValueError(
            "F4i4a multi-condition photo fitting requires "
            "exactly one free parameter."
        )

    binding = calibration_spec.bindings[0]
    if (
        binding.target
        != DeviceFitTarget.PHOTO_CAPTURE_EFFICIENCY
    ):
        raise ValueError(
            "F4i4a multi-condition photo fitting requires "
            "the single free parameter to target "
            "DeviceFitTarget.PHOTO_CAPTURE_EFFICIENCY."
        )

    # Fail early before entering the optimizer.
    _evaluate_photo_multi_condition_candidate(
        dataset_tuple,
        protocol_tuple,
        base_device=base_device,
        base_physics=base_physics,
        base_simulation_config=(
            base_simulation_config
        ),
        base_photo_config=base_photo_config,
        calibration_spec=calibration_spec,
        parameter_values=(
            calibration_spec
            .parameter_set.initial_values
        ),
    )

    def residual_function(parameter_values):
        _, _, _, joint_residuals = (
            _evaluate_photo_multi_condition_candidate(
                dataset_tuple,
                protocol_tuple,
                base_device=base_device,
                base_physics=base_physics,
                base_simulation_config=(
                    base_simulation_config
                ),
                base_photo_config=base_photo_config,
                calibration_spec=calibration_spec,
                parameter_values=parameter_values,
            )
        )
        return joint_residuals

    numerical_result = run_least_squares_fit(
        calibration_spec.parameter_set,
        residual_function,
        config=least_squares_config,
    )

    (
        fitted_context,
        predictions,
        objectives,
        _,
    ) = _evaluate_photo_multi_condition_candidate(
        dataset_tuple,
        protocol_tuple,
        base_device=base_device,
        base_physics=base_physics,
        base_simulation_config=(
            base_simulation_config
        ),
        base_photo_config=base_photo_config,
        calibration_spec=calibration_spec,
        parameter_values=(
            numerical_result.fitted_values
        ),
    )

    return DevicePhotoMultiConditionFitResult(
        dataset_ids=tuple(
            dataset.metadata.dataset_id
            for dataset in dataset_tuple
        ),
        dataset_hashes=tuple(
            dataset.dataset_hash()
            for dataset in dataset_tuple
        ),
        protocols=protocol_tuple,
        calibration_specification_hash=(
            calibration_spec.specification_hash()
        ),
        numerical_result=numerical_result,
        objectives=objectives,
        fitted_context=fitted_context,
        predictions=predictions,
    )

__all__ = [
    "DevicePhotoMultiConditionFitResult",
    "DevicePhotoProgramTimeFitResult",
    "ElectroOpticalProgramTimeFitProtocol",
    "ElectroOpticalProgramTimePrediction",
    "fit_single_parameter_photo_capture_efficiency_multi_condition",
    "fit_single_parameter_photo_capture_efficiency_vs_programming_time",
    "predict_electro_optical_delta_vfb_vs_programming_time",
]
