from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Sequence

import numpy as np

from .electro_optical_program_protocol import (
    ElectroOpticalProgramPulseReadProtocol,
    ElectroOpticalProgramPulseReadResult,
    run_electro_optical_program_pulse_read,
)
from .hashing import canonical_hash
from .optics import LightSource
from .photo import PhotoTransitionConfig, PhotoTransitionWeights
from .program_protocol import ProgramPulseReadProtocol
from .simulator import Simulator
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


__all__ = [
    "ElectroOpticalProgramTimeFitProtocol",
    "ElectroOpticalProgramTimePrediction",
    "predict_electro_optical_delta_vfb_vs_programming_time",
]
