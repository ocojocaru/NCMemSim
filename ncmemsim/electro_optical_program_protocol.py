from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np

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
class ElectroOpticalProgramPulseReadProtocol:
    """
    Reproducible illuminated program pulse followed by a dark zero-dwell read.

    The electrical pulse/read definition is reused directly from
    ``ProgramPulseReadProtocol``. Illumination is active only during the
    programming pulse. The read operation is always dark and has zero dwell
    time, so the programmed occupation state is sampled electrostatically
    without additional photo-assisted or electrical kinetic evolution.

    ``photo_capture_efficiency`` is deliberately not part of this protocol.
    It is supplied at execution time through ``PhotoTransitionConfig`` so a
    fitted device parameter remains separate from experimental illumination
    conditions.
    """

    electrical_protocol: ProgramPulseReadProtocol
    light_source: LightSource
    photo_weights: PhotoTransitionWeights
    occupancy_integrator: str = "explicit_euler"

    def __post_init__(self) -> None:
        if not isinstance(
            self.electrical_protocol,
            ProgramPulseReadProtocol,
        ):
            raise TypeError(
                "electrical_protocol must be a ProgramPulseReadProtocol."
            )
        if not isinstance(self.light_source, LightSource):
            raise TypeError(
                "light_source must be a LightSource."
            )
        if not isinstance(
            self.photo_weights,
            PhotoTransitionWeights,
        ):
            raise TypeError(
                "photo_weights must be a PhotoTransitionWeights."
            )

        source = self.light_source
        if not source.enabled:
            raise ValueError(
                "Electro-optical programming requires an enabled light source."
            )

        power = float(source.power_density_W_m2)
        if not math.isfinite(power) or power <= 0.0:
            raise ValueError(
                "light_source.power_density_W_m2 must be finite "
                "and strictly positive."
            )

        for field_name in (
            "temperature_K",
            "wavelength_nm",
            "wavelength_min_nm",
            "wavelength_max_nm",
        ):
            raw_value = getattr(source, field_name)
            if raw_value is None:
                continue
            value = float(raw_value)
            if not math.isfinite(value):
                raise ValueError(
                    f"light_source.{field_name} must be finite when supplied."
                )

        weights = _photo_weights_dict(self.photo_weights)
        for name, value in weights.items():
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(
                    f"photo_weights.{name} must be finite and non-negative."
                )

        if not any(value > 0.0 for value in weights.values()):
            raise ValueError(
                "At least one photo-transition weight must be positive."
            )

        if self.occupancy_integrator not in {
            "explicit_euler",
            "backward_euler",
        }:
            raise ValueError(
                "occupancy_integrator must be 'explicit_euler' "
                "or 'backward_euler'."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "workflow": (
                "electro-optical-program-pulse-nondestructive-dark-read"
            ),
            "electrical_protocol": self.electrical_protocol.to_dict(),
            "light_source": self.light_source.to_dict(),
            "photo_transition_weights": _photo_weights_dict(
                self.photo_weights
            ),
            "occupancy_integrator": self.occupancy_integrator,
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
class ElectroOpticalProgramPulseReadResult:
    """
    Result of one illuminated program pulse followed by a dark zero-dwell read.

    Program-pulse optical diagnostics are retained so a fitted device
    observable can be traced to the absorbed-photon and photo-transition
    rates used by the simulator.
    """

    protocol: ElectroOpticalProgramPulseReadProtocol
    photo_config: PhotoTransitionConfig
    initial_state: DeviceState
    programmed_state: DeviceState
    read_state: DeviceState
    delta_vfb_V: float
    delta_vfb_by_fg_V: np.ndarray
    qfg_C_m2: float
    qfg_by_fg_C_m2: np.ndarray
    mean_occupation: float
    mean_occupation_by_fg: np.ndarray
    absorbed_photon_flux_m2_s: float
    absorbed_photon_flux_by_fg_m2_s: np.ndarray
    photo_transition_rate_s: float
    photo_transition_rate_by_fg_s: np.ndarray

    def __post_init__(self) -> None:
        if not isinstance(
            self.protocol,
            ElectroOpticalProgramPulseReadProtocol,
        ):
            raise TypeError(
                "protocol must be an ElectroOpticalProgramPulseReadProtocol."
            )
        if not isinstance(
            self.photo_config,
            PhotoTransitionConfig,
        ):
            raise TypeError(
                "photo_config must be a PhotoTransitionConfig."
            )

        scalar_values = {
            "delta_vfb_V": float(self.delta_vfb_V),
            "qfg_C_m2": float(self.qfg_C_m2),
            "mean_occupation": float(self.mean_occupation),
            "absorbed_photon_flux_m2_s": float(
                self.absorbed_photon_flux_m2_s
            ),
            "photo_transition_rate_s": float(
                self.photo_transition_rate_s
            ),
        }

        for field_name, value in scalar_values.items():
            if not math.isfinite(value):
                raise ValueError(
                    f"{field_name} must be finite."
                )

        if scalar_values["absorbed_photon_flux_m2_s"] < 0.0:
            raise ValueError(
                "absorbed_photon_flux_m2_s cannot be negative."
            )
        if scalar_values["photo_transition_rate_s"] < 0.0:
            raise ValueError(
                "photo_transition_rate_s cannot be negative."
            )

        self.delta_vfb_V = scalar_values["delta_vfb_V"]
        self.qfg_C_m2 = scalar_values["qfg_C_m2"]
        self.mean_occupation = scalar_values["mean_occupation"]
        self.absorbed_photon_flux_m2_s = scalar_values[
            "absorbed_photon_flux_m2_s"
        ]
        self.photo_transition_rate_s = scalar_values[
            "photo_transition_rate_s"
        ]

        self.delta_vfb_by_fg_V = _readonly_float_array(
            self.delta_vfb_by_fg_V
        )
        self.qfg_by_fg_C_m2 = _readonly_float_array(
            self.qfg_by_fg_C_m2
        )
        self.mean_occupation_by_fg = _readonly_float_array(
            self.mean_occupation_by_fg
        )
        self.absorbed_photon_flux_by_fg_m2_s = _readonly_float_array(
            self.absorbed_photon_flux_by_fg_m2_s
        )
        self.photo_transition_rate_by_fg_s = _readonly_float_array(
            self.photo_transition_rate_by_fg_s
        )

        if np.any(self.absorbed_photon_flux_by_fg_m2_s < 0.0):
            raise ValueError(
                "absorbed_photon_flux_by_fg_m2_s cannot contain "
                "negative values."
            )
        if np.any(self.photo_transition_rate_by_fg_s < 0.0):
            raise ValueError(
                "photo_transition_rate_by_fg_s cannot contain "
                "negative values."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "workflow": (
                "electro-optical-program-pulse-nondestructive-dark-read"
            ),
            "protocol": self.protocol.to_dict(),
            "protocol_hash": self.protocol.protocol_hash(),
            "photo_transition_config": {
                "photo_capture_efficiency": (
                    self.photo_config.photo_capture_efficiency
                ),
            },
            "observable": {
                "name": "delta_vfb",
                "unit": "V",
                "value": self.delta_vfb_V,
            },
            "qfg_C_m2": self.qfg_C_m2,
            "qfg_by_fg_C_m2": self.qfg_by_fg_C_m2.tolist(),
            "mean_occupation": self.mean_occupation,
            "mean_occupation_by_fg": (
                self.mean_occupation_by_fg.tolist()
            ),
            "absorbed_photon_flux_m2_s": (
                self.absorbed_photon_flux_m2_s
            ),
            "absorbed_photon_flux_by_fg_m2_s": (
                self.absorbed_photon_flux_by_fg_m2_s.tolist()
            ),
            "photo_transition_rate_s": self.photo_transition_rate_s,
            "photo_transition_rate_by_fg_s": (
                self.photo_transition_rate_by_fg_s.tolist()
            ),
            "initial_time_s": float(self.initial_state.time_s),
            "programmed_time_s": float(
                self.programmed_state.time_s
            ),
            "read_time_s": float(self.read_state.time_s),
        }


def run_electro_optical_program_pulse_read(
    simulator: Simulator,
    protocol: ElectroOpticalProgramPulseReadProtocol,
    *,
    photo_config: PhotoTransitionConfig,
    initial_state: DeviceState | None = None,
) -> ElectroOpticalProgramPulseReadResult:
    """
    Apply one illuminated program pulse and perform a dark zero-dwell read.

    ``photo_config`` is explicit and is not embedded in the protocol because
    its ``photo_capture_efficiency`` may be the device parameter being fitted.
    """

    if not isinstance(simulator, Simulator):
        raise TypeError(
            "simulator must be a Simulator instance."
        )
    if not isinstance(
        protocol,
        ElectroOpticalProgramPulseReadProtocol,
    ):
        raise TypeError(
            "protocol must be an ElectroOpticalProgramPulseReadProtocol."
        )
    if not isinstance(photo_config, PhotoTransitionConfig):
        raise TypeError(
            "photo_config must be a PhotoTransitionConfig."
        )

    if initial_state is None:
        start = DeviceState.empty_for_device(
            simulator.device
        )
    else:
        if not isinstance(initial_state, DeviceState):
            raise TypeError(
                "initial_state must be a DeviceState or None."
            )
        initial_state.validate(simulator.device)
        start = initial_state.copy()

    start.validate(simulator.device)
    initial_snapshot = start.copy()

    electrical = protocol.electrical_protocol

    program_output = simulator.relax_voltage(
        start,
        gate_voltage_V=electrical.program_voltage_V,
        dwell_time_s=electrical.programming_time_s,
        internal_dt_s=electrical.program_internal_dt_s,
        light_source=protocol.light_source,
        photo_config=photo_config,
        photo_weights=protocol.photo_weights,
        occupancy_integrator=protocol.occupancy_integrator,
    )

    programmed_state = program_output["state"].copy()
    programmed_state.validate(simulator.device)

    # The read is deliberately dark. No light source, photo configuration,
    # or photo weights are passed to the simulator.
    read_output = simulator.relax_voltage(
        programmed_state,
        gate_voltage_V=electrical.read_voltage_V,
        dwell_time_s=0.0,
        internal_dt_s=electrical.program_internal_dt_s,
        occupancy_integrator=protocol.occupancy_integrator,
    )

    read_state = read_output["state"].copy()
    read_state.validate(simulator.device)

    return ElectroOpticalProgramPulseReadResult(
        protocol=protocol,
        photo_config=photo_config,
        initial_state=initial_snapshot,
        programmed_state=programmed_state,
        read_state=read_state,
        delta_vfb_V=float(read_output["delta_vfb_V"]),
        delta_vfb_by_fg_V=np.asarray(
            read_output["delta_vfb_by_fg_V"],
            dtype=float,
        ),
        qfg_C_m2=float(read_output["qfg_C_m2"]),
        qfg_by_fg_C_m2=np.asarray(
            read_output["qfg_by_fg_C_m2"],
            dtype=float,
        ),
        mean_occupation=float(read_output["mean_occupation"]),
        mean_occupation_by_fg=np.asarray(
            read_output["mean_occupation_by_fg"],
            dtype=float,
        ),
        absorbed_photon_flux_m2_s=float(
            program_output["absorbed_photon_flux_m2_s"]
        ),
        absorbed_photon_flux_by_fg_m2_s=np.asarray(
            program_output[
                "absorbed_photon_flux_by_fg_m2_s"
            ],
            dtype=float,
        ),
        photo_transition_rate_s=float(
            program_output["photo_transition_rate_s"]
        ),
        photo_transition_rate_by_fg_s=np.asarray(
            program_output["photo_transition_rate_by_fg_s"],
            dtype=float,
        ),
    )


__all__ = [
    "ElectroOpticalProgramPulseReadProtocol",
    "ElectroOpticalProgramPulseReadResult",
    "run_electro_optical_program_pulse_read",
]
