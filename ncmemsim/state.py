from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class FloatingGateState:
    """Occupation state of one floating-gate layer.

    ``fg_id``, ``layer_name`` and ``z_center_nm`` are structural metadata.  They
    do not enter the Phase-D1 rate equations, but make every state traceable to
    its physical layer and prepare the local-field/optical engines of later
    Phase-D sprints.
    """

    P0: np.ndarray
    P1: np.ndarray
    P2: np.ndarray
    fg_id: int | None = None
    layer_name: str | None = None
    z_center_nm: float | None = None
    local_field_V_m: float | None = None
    local_potential_V: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def empty(
        cls,
        grid_points: int,
        *,
        fg_id: int | None = None,
        layer_name: str | None = None,
        z_center_nm: float | None = None,
    ) -> "FloatingGateState":
        if grid_points < 2:
            raise ValueError("grid_points must be at least two")
        return cls(
            np.ones(grid_points),
            np.zeros(grid_points),
            np.zeros(grid_points),
            fg_id=fg_id,
            layer_name=layer_name,
            z_center_nm=z_center_nm,
        )

    def copy(self) -> "FloatingGateState":
        return FloatingGateState(
            self.P0.copy(),
            self.P1.copy(),
            self.P2.copy(),
            fg_id=self.fg_id,
            layer_name=self.layer_name,
            z_center_nm=self.z_center_nm,
            local_field_V_m=self.local_field_V_m,
            local_potential_V=self.local_potential_V,
            metadata=dict(self.metadata),
        )

    def validate(self, atol: float = 1e-12) -> None:
        if not (self.P0.shape == self.P1.shape == self.P2.shape):
            raise ValueError("P0, P1 and P2 must have identical shapes")
        if self.P0.ndim != 1:
            raise ValueError("Floating-gate probabilities must be one-dimensional")
        if np.any(~np.isfinite(self.P0)) or np.any(~np.isfinite(self.P1)) or np.any(~np.isfinite(self.P2)):
            raise ValueError("Probabilities must be finite")
        if np.any(self.P0 < 0) or np.any(self.P1 < 0) or np.any(self.P2 < 0):
            raise ValueError("Probabilities cannot be negative")
        if not np.allclose(self.P0 + self.P1 + self.P2, 1.0, atol=atol):
            raise ValueError("P0 + P1 + P2 must equal one")
        if self.fg_id is not None and self.fg_id < 0:
            raise ValueError("fg_id cannot be negative")

    @property
    def occupation(self) -> np.ndarray:
        return 0.5 * (self.P1 + 2.0 * self.P2)

    @property
    def mean_normalized_occupation(self) -> float:
        return float(np.mean(self.occupation))


@dataclass
class DeviceState:
    """Complete state of a device with one or more independent FG states."""

    floating_gates: list[FloatingGateState]
    time_s: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def empty_for_device(cls, device) -> "DeviceState":
        positions = device.layer_positions_nm()
        states: list[FloatingGateState] = []
        for fg_id, fg in enumerate(device.floating_gates()):
            z0_nm, z1_nm = positions[fg.name]
            states.append(
                FloatingGateState.empty(
                    fg.grid_points,
                    fg_id=fg_id,
                    layer_name=fg.name,
                    z_center_nm=0.5 * (z0_nm + z1_nm),
                )
            )
        return cls(states)

    def copy(self) -> "DeviceState":
        return DeviceState(
            [state.copy() for state in self.floating_gates],
            time_s=self.time_s,
            metadata=dict(self.metadata),
        )

    def validate(self, device=None) -> None:
        if not self.floating_gates:
            raise ValueError("DeviceState must contain at least one floating gate")
        if device is not None and len(self.floating_gates) != device.number_of_fgs():
            raise ValueError("State/device floating-gate count mismatch")
        for index, state in enumerate(self.floating_gates):
            state.validate()
            if device is not None:
                fg = device.floating_gates()[index]
                if state.P0.size != fg.grid_points:
                    raise ValueError(f"Grid-size mismatch for {fg.name}")
                if state.fg_id is not None and state.fg_id != index:
                    raise ValueError(f"Floating-gate ID mismatch for {fg.name}")
                if state.layer_name is not None and state.layer_name != fg.name:
                    raise ValueError(f"Layer-name mismatch for {fg.name}")

    def for_layer(self, layer_name: str) -> FloatingGateState:
        for state in self.floating_gates:
            if state.layer_name == layer_name:
                return state
        raise KeyError(layer_name)

    @property
    def mean_normalized_occupations(self) -> np.ndarray:
        return np.asarray([s.mean_normalized_occupation for s in self.floating_gates], dtype=float)
