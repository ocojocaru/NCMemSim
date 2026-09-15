from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Literal

import numpy as np

from .hashing import canonical_hash
from .simulator import Simulator
from .state import DeviceState


PulseRole = Literal["program", "erase"]


def _readonly_float_array(values) -> np.ndarray:
    array = np.array(values, dtype=float, copy=True)
    if array.ndim != 1:
        raise ValueError("Per-FG result arrays must be one-dimensional.")
    if not np.all(np.isfinite(array)):
        raise ValueError("Per-FG result arrays must contain finite values.")
    array.setflags(write=False)
    return array


@dataclass(frozen=True)
class PairedPulseMemoryProtocol:
    """
    Explicit pulse-defined memory-window protocol.

    Two independent branches start from the same reference state:

        reference -> program pulse -> zero-dwell read
        reference -> erase pulse   -> zero-dwell read

    The pulse-defined signed memory window is

        ΔVFB(programmed) - ΔVFB(erased)

    and is therefore distinct from the dynamic forward/backward hysteresis
    returned by ``Simulator.simulate_cv``.
    """

    program_voltage_V: float
    program_time_s: float
    erase_voltage_V: float
    erase_time_s: float
    read_voltage_V: float = 0.0
    pulse_internal_dt_s: float | None = None

    def __post_init__(self) -> None:
        program_voltage = float(self.program_voltage_V)
        erase_voltage = float(self.erase_voltage_V)
        program_time = float(self.program_time_s)
        erase_time = float(self.erase_time_s)
        read_voltage = float(self.read_voltage_V)

        for field_name, value in {
            "program_voltage_V": program_voltage,
            "erase_voltage_V": erase_voltage,
            "read_voltage_V": read_voltage,
        }.items():
            if not math.isfinite(value):
                raise ValueError(f"{field_name} must be finite.")

        for field_name, value in {
            "program_time_s": program_time,
            "erase_time_s": erase_time,
        }.items():
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(
                    f"{field_name} must be finite and strictly positive."
                )

        if program_voltage == erase_voltage:
            raise ValueError(
                "program_voltage_V and erase_voltage_V must be different."
            )

        pulse_dt = self.pulse_internal_dt_s
        if pulse_dt is not None:
            pulse_dt = float(pulse_dt)
            if not math.isfinite(pulse_dt) or pulse_dt <= 0.0:
                raise ValueError(
                    "pulse_internal_dt_s must be finite and strictly "
                    "positive when supplied."
                )

        object.__setattr__(self, "program_voltage_V", program_voltage)
        object.__setattr__(self, "erase_voltage_V", erase_voltage)
        object.__setattr__(self, "program_time_s", program_time)
        object.__setattr__(self, "erase_time_s", erase_time)
        object.__setattr__(self, "read_voltage_V", read_voltage)
        object.__setattr__(self, "pulse_internal_dt_s", pulse_dt)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "program_voltage_V": self.program_voltage_V,
            "program_time_s": self.program_time_s,
            "erase_voltage_V": self.erase_voltage_V,
            "erase_time_s": self.erase_time_s,
            "read_voltage_V": self.read_voltage_V,
            "pulse_internal_dt_s": self.pulse_internal_dt_s,
            "branch_semantics": (
                "independent-program-and-erase-from-common-reference"
            ),
            "read_dwell_time_s": 0.0,
            "memory_window_definition": (
                "delta_vfb_programmed_minus_delta_vfb_erased"
            ),
        }

    def protocol_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass
class PulseBranchResult:
    """One program or erase branch followed by a zero-dwell read."""

    role: PulseRole
    pulse_voltage_V: float
    pulse_time_s: float
    initial_state: DeviceState
    pulsed_state: DeviceState
    read_state: DeviceState
    delta_vfb_V: float
    delta_vfb_by_fg_V: np.ndarray
    qfg_C_m2: float
    qfg_by_fg_C_m2: np.ndarray
    mean_occupation: float
    mean_occupation_by_fg: np.ndarray

    def __post_init__(self) -> None:
        if self.role not in {"program", "erase"}:
            raise ValueError("role must be 'program' or 'erase'.")

        pulse_voltage = float(self.pulse_voltage_V)
        pulse_time = float(self.pulse_time_s)
        delta_vfb = float(self.delta_vfb_V)
        qfg = float(self.qfg_C_m2)
        mean_occupation = float(self.mean_occupation)

        if not math.isfinite(pulse_voltage):
            raise ValueError("pulse_voltage_V must be finite.")
        if not math.isfinite(pulse_time) or pulse_time <= 0.0:
            raise ValueError(
                "pulse_time_s must be finite and strictly positive."
            )

        for field_name, value in {
            "delta_vfb_V": delta_vfb,
            "qfg_C_m2": qfg,
            "mean_occupation": mean_occupation,
        }.items():
            if not math.isfinite(value):
                raise ValueError(f"{field_name} must be finite.")

        self.pulse_voltage_V = pulse_voltage
        self.pulse_time_s = pulse_time
        self.delta_vfb_V = delta_vfb
        self.qfg_C_m2 = qfg
        self.mean_occupation = mean_occupation
        self.delta_vfb_by_fg_V = _readonly_float_array(
            self.delta_vfb_by_fg_V
        )
        self.qfg_by_fg_C_m2 = _readonly_float_array(
            self.qfg_by_fg_C_m2
        )
        self.mean_occupation_by_fg = _readonly_float_array(
            self.mean_occupation_by_fg
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "pulse_voltage_V": self.pulse_voltage_V,
            "pulse_time_s": self.pulse_time_s,
            "delta_vfb_V": self.delta_vfb_V,
            "delta_vfb_by_fg_V": self.delta_vfb_by_fg_V.tolist(),
            "qfg_C_m2": self.qfg_C_m2,
            "qfg_by_fg_C_m2": self.qfg_by_fg_C_m2.tolist(),
            "mean_occupation": self.mean_occupation,
            "mean_occupation_by_fg": (
                self.mean_occupation_by_fg.tolist()
            ),
            "initial_time_s": float(self.initial_state.time_s),
            "pulsed_time_s": float(self.pulsed_state.time_s),
            "read_time_s": float(self.read_state.time_s),
        }


@dataclass
class PairedPulseMemoryResult:
    """Program/erase state separation measured as a pulse-defined window."""

    protocol: PairedPulseMemoryProtocol
    reference_state: DeviceState
    program: PulseBranchResult
    erase: PulseBranchResult

    @property
    def memory_window_V(self) -> float:
        return float(
            self.program.delta_vfb_V
            - self.erase.delta_vfb_V
        )

    @property
    def memory_window_magnitude_V(self) -> float:
        return abs(self.memory_window_V)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "workflow": "paired-program-erase-pulse-memory-window",
            "protocol": self.protocol.to_dict(),
            "protocol_hash": self.protocol.protocol_hash(),
            "memory_window_V": self.memory_window_V,
            "memory_window_magnitude_V": self.memory_window_magnitude_V,
            "memory_window_definition": (
                "delta_vfb_programmed_minus_delta_vfb_erased"
            ),
            "program": self.program.to_dict(),
            "erase": self.erase.to_dict(),
            "reference_time_s": float(self.reference_state.time_s),
        }


def _run_branch(
    simulator: Simulator,
    *,
    role: PulseRole,
    reference_state: DeviceState,
    pulse_voltage_V: float,
    pulse_time_s: float,
    read_voltage_V: float,
    pulse_internal_dt_s: float | None,
) -> PulseBranchResult:
    initial_snapshot = reference_state.copy()

    pulse_output = simulator.relax_voltage(
        reference_state,
        gate_voltage_V=pulse_voltage_V,
        dwell_time_s=pulse_time_s,
        internal_dt_s=pulse_internal_dt_s,
    )

    pulsed_state = pulse_output["state"].copy()
    pulsed_state.validate(simulator.device)

    read_output = simulator.relax_voltage(
        pulsed_state,
        gate_voltage_V=read_voltage_V,
        dwell_time_s=0.0,
        internal_dt_s=pulse_internal_dt_s,
    )

    read_state = read_output["state"].copy()
    read_state.validate(simulator.device)

    return PulseBranchResult(
        role=role,
        pulse_voltage_V=pulse_voltage_V,
        pulse_time_s=pulse_time_s,
        initial_state=initial_snapshot,
        pulsed_state=pulsed_state,
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
    )


def run_paired_pulse_memory_protocol(
    simulator: Simulator,
    protocol: PairedPulseMemoryProtocol,
    *,
    reference_state: DeviceState | None = None,
) -> PairedPulseMemoryResult:
    """
    Generate programmed and erased states from one common reference state.

    The two branches are independent. Neither branch is initialized from the
    terminal state of the other, and the caller-supplied reference state is
    never mutated.
    """

    if not isinstance(simulator, Simulator):
        raise TypeError("simulator must be a Simulator instance.")
    if not isinstance(protocol, PairedPulseMemoryProtocol):
        raise TypeError(
            "protocol must be a PairedPulseMemoryProtocol."
        )

    if reference_state is None:
        reference = DeviceState.empty_for_device(simulator.device)
    else:
        if not isinstance(reference_state, DeviceState):
            raise TypeError(
                "reference_state must be a DeviceState or None."
            )
        reference_state.validate(simulator.device)
        reference = reference_state.copy()

    reference.validate(simulator.device)
    reference_snapshot = reference.copy()

    program = _run_branch(
        simulator,
        role="program",
        reference_state=reference,
        pulse_voltage_V=protocol.program_voltage_V,
        pulse_time_s=protocol.program_time_s,
        read_voltage_V=protocol.read_voltage_V,
        pulse_internal_dt_s=protocol.pulse_internal_dt_s,
    )

    erase = _run_branch(
        simulator,
        role="erase",
        reference_state=reference,
        pulse_voltage_V=protocol.erase_voltage_V,
        pulse_time_s=protocol.erase_time_s,
        read_voltage_V=protocol.read_voltage_V,
        pulse_internal_dt_s=protocol.pulse_internal_dt_s,
    )

    return PairedPulseMemoryResult(
        protocol=protocol,
        reference_state=reference_snapshot,
        program=program,
        erase=erase,
    )


__all__ = [
    "PairedPulseMemoryProtocol",
    "PairedPulseMemoryResult",
    "PulseBranchResult",
    "run_paired_pulse_memory_protocol",
]
