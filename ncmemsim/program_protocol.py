from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np

from .hashing import canonical_hash
from .simulator import Simulator
from .state import DeviceState


def _readonly_float_array(values) -> np.ndarray:
    array = np.array(values, dtype=float, copy=True)
    array.setflags(write=False)
    return array


@dataclass(frozen=True)
class ProgramPulseReadProtocol:
    """
    Explicit electrical program-pulse plus nondestructive read protocol.

    ``programming_time_s`` is the duration of one fixed-voltage program pulse.
    It is passed directly to ``Simulator.relax_voltage`` and is therefore
    distinct from ``SimulationConfig.dwell_time_s``, which remains the
    simulator's default per-voltage relaxation time.

    The read operation is forced to zero dwell time so the programmed
    occupation state is evaluated electrostatically without further kinetic
    evolution.
    """

    program_voltage_V: float
    programming_time_s: float
    read_voltage_V: float = 0.0
    program_internal_dt_s: float | None = None

    def __post_init__(self) -> None:
        program_voltage = float(self.program_voltage_V)
        programming_time = float(self.programming_time_s)
        read_voltage = float(self.read_voltage_V)

        if not math.isfinite(program_voltage):
            raise ValueError(
                "program_voltage_V must be finite."
            )
        if (
            not math.isfinite(programming_time)
            or programming_time <= 0.0
        ):
            raise ValueError(
                "programming_time_s must be finite and "
                "strictly positive."
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
            "programming_time_s",
            programming_time,
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "program_voltage_V": self.program_voltage_V,
            "programming_time_s": self.programming_time_s,
            "read_voltage_V": self.read_voltage_V,
            "program_internal_dt_s": (
                self.program_internal_dt_s
            ),
            "read_dwell_time_s": 0.0,
            "read_semantics": (
                "nondestructive-zero-dwell-electrostatic"
            ),
        }

    def protocol_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass
class ProgramPulseReadResult:
    """
    Result of one electrical program pulse followed by a zero-dwell read.

    The primary observable is ``delta_vfb_V``. This is intentionally not
    called a memory window: a single programmed state does not by itself
    define the separation between programmed and erased/reference states.
    """

    protocol: ProgramPulseReadProtocol
    initial_state: DeviceState
    programmed_state: DeviceState
    read_state: DeviceState
    delta_vfb_V: float
    delta_vfb_by_fg_V: np.ndarray
    qfg_C_m2: float
    qfg_by_fg_C_m2: np.ndarray
    mean_occupation: float
    mean_occupation_by_fg: np.ndarray

    def __post_init__(self) -> None:
        delta_vfb = float(self.delta_vfb_V)
        qfg = float(self.qfg_C_m2)
        mean_occupation = float(self.mean_occupation)

        for field_name, value in {
            "delta_vfb_V": delta_vfb,
            "qfg_C_m2": qfg,
            "mean_occupation": mean_occupation,
        }.items():
            if not math.isfinite(value):
                raise ValueError(
                    f"{field_name} must be finite."
                )

        self.delta_vfb_V = delta_vfb
        self.qfg_C_m2 = qfg
        self.mean_occupation = mean_occupation
        self.delta_vfb_by_fg_V = (
            _readonly_float_array(
                self.delta_vfb_by_fg_V
            )
        )
        self.qfg_by_fg_C_m2 = (
            _readonly_float_array(
                self.qfg_by_fg_C_m2
            )
        )
        self.mean_occupation_by_fg = (
            _readonly_float_array(
                self.mean_occupation_by_fg
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "workflow": (
                "electrical-program-pulse-nondestructive-read"
            ),
            "protocol": self.protocol.to_dict(),
            "protocol_hash": self.protocol.protocol_hash(),
            "observable": {
                "name": "delta_vfb",
                "unit": "V",
                "value": self.delta_vfb_V,
            },
            "qfg_C_m2": self.qfg_C_m2,
            "qfg_by_fg_C_m2": (
                self.qfg_by_fg_C_m2.tolist()
            ),
            "mean_occupation": self.mean_occupation,
            "mean_occupation_by_fg": (
                self.mean_occupation_by_fg.tolist()
            ),
            "initial_time_s": (
                float(self.initial_state.time_s)
            ),
            "programmed_time_s": (
                float(self.programmed_state.time_s)
            ),
            "read_time_s": (
                float(self.read_state.time_s)
            ),
        }


def run_program_pulse_read(
    simulator: Simulator,
    protocol: ProgramPulseReadProtocol,
    *,
    initial_state: DeviceState | None = None,
) -> ProgramPulseReadResult:
    """
    Apply one fixed-voltage program pulse and read ``delta_vfb`` at zero dwell.

    Each call is independent unless an explicit ``initial_state`` is supplied.
    The supplied state is copied by ``Simulator.relax_voltage`` and is not
    mutated by this workflow.
    """

    if not isinstance(simulator, Simulator):
        raise TypeError(
            "simulator must be a Simulator instance."
        )
    if not isinstance(
        protocol,
        ProgramPulseReadProtocol,
    ):
        raise TypeError(
            "protocol must be a ProgramPulseReadProtocol."
        )

    if initial_state is None:
        start = DeviceState.empty_for_device(
            simulator.device
        )
    else:
        if not isinstance(initial_state, DeviceState):
            raise TypeError(
                "initial_state must be a DeviceState "
                "or None."
            )
        initial_state.validate(simulator.device)
        start = initial_state.copy()

    start.validate(simulator.device)
    initial_snapshot = start.copy()

    program_output = simulator.relax_voltage(
        start,
        gate_voltage_V=(
            protocol.program_voltage_V
        ),
        dwell_time_s=(
            protocol.programming_time_s
        ),
        internal_dt_s=(
            protocol.program_internal_dt_s
        ),
    )

    programmed_state = (
        program_output["state"].copy()
    )
    programmed_state.validate(simulator.device)

    # A zero-dwell read evaluates the programmed state without
    # advancing the occupation dynamics.
    read_output = simulator.relax_voltage(
        programmed_state,
        gate_voltage_V=protocol.read_voltage_V,
        dwell_time_s=0.0,
        internal_dt_s=(
            protocol.program_internal_dt_s
        ),
    )

    read_state = read_output["state"].copy()
    read_state.validate(simulator.device)

    return ProgramPulseReadResult(
        protocol=protocol,
        initial_state=initial_snapshot,
        programmed_state=programmed_state,
        read_state=read_state,
        delta_vfb_V=float(
            read_output["delta_vfb_V"]
        ),
        delta_vfb_by_fg_V=np.asarray(
            read_output["delta_vfb_by_fg_V"],
            dtype=float,
        ),
        qfg_C_m2=float(
            read_output["qfg_C_m2"]
        ),
        qfg_by_fg_C_m2=np.asarray(
            read_output["qfg_by_fg_C_m2"],
            dtype=float,
        ),
        mean_occupation=float(
            read_output["mean_occupation"]
        ),
        mean_occupation_by_fg=np.asarray(
            read_output[
                "mean_occupation_by_fg"
            ],
            dtype=float,
        ),
    )


__all__ = [
    "ProgramPulseReadProtocol",
    "ProgramPulseReadResult",
    "run_program_pulse_read",
]
