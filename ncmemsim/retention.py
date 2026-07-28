from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

import numpy as np

from .state import DeviceState

if TYPE_CHECKING:
    from .simulator import Simulator


@dataclass(frozen=True)
class RetentionConfig:
    """Controls logarithmic-time retention and charge-redistribution runs."""

    gate_voltage_V: float = 0.0
    total_time_s: float = 1.0e4
    initial_dt_s: float = 1.0e-9
    maximum_dt_s: float = 1.0e3
    growth_factor: float = 2.0
    output_points: int = 121
    quasi_equilibrium_tolerance_C_m2_s: float = 1.0e-18
    quasi_equilibrium_steps: int = 4
    stop_at_quasi_equilibrium: bool = False

    def validate(self) -> None:
        if self.total_time_s < 0.0:
            raise ValueError("total_time_s must be non-negative")
        if self.initial_dt_s <= 0.0 or self.maximum_dt_s <= 0.0:
            raise ValueError("Retention time steps must be positive")
        if self.growth_factor <= 1.0:
            raise ValueError("growth_factor must exceed one")
        if self.output_points < 2:
            raise ValueError("output_points must be at least two")
        if self.quasi_equilibrium_tolerance_C_m2_s < 0.0:
            raise ValueError("quasi-equilibrium tolerance cannot be negative")
        if self.quasi_equilibrium_steps < 1:
            raise ValueError("quasi_equilibrium_steps must be positive")


@dataclass
class RetentionResult:
    time_s: np.ndarray
    qfg_C_m2: np.ndarray
    qfg_by_fg_C_m2: np.ndarray
    mean_occupation_by_fg: np.ndarray
    delta_vfb_V: np.ndarray
    delta_vfb_by_fg_V: np.ndarray
    local_field_by_fg_V_m: np.ndarray
    local_potential_by_fg_V: np.ndarray
    inter_fg_flux_by_link_m2_s: np.ndarray
    transport_transmission_by_link: np.ndarray
    transport_link_ids: tuple[str, ...]
    charge_rate_C_m2_s: np.ndarray
    final_state: DeviceState
    quasi_equilibrium_reached: bool
    quasi_equilibrium_time_s: float | None

    @property
    def total_charge_retention_fraction(self) -> np.ndarray:
        q0 = float(self.qfg_C_m2[0])
        if abs(q0) <= np.finfo(float).tiny:
            return np.ones_like(self.qfg_C_m2)
        return self.qfg_C_m2 / q0

    @property
    def charge_loss_fraction(self) -> np.ndarray:
        return 1.0 - self.total_charge_retention_fraction


class RetentionSolver:
    """Adaptive logarithmic-time wrapper around the coupled transient solver.

    Every accepted step recomputes electrostatics, local fields, substrate
    kinetics and inter-FG transport through :meth:`Simulator.relax_voltage`.
    Output is sampled on a logarithmic time grid, while the internal step grows
    geometrically and is clipped to land exactly on requested sample times.
    """

    def __init__(self, simulator: "Simulator", config: RetentionConfig | None = None):
        self.simulator = simulator
        self.config = config or RetentionConfig()
        self.config.validate()

    def _output_times(self) -> np.ndarray:
        c = self.config
        if c.total_time_s == 0.0:
            return np.asarray([0.0], dtype=float)
        first = min(c.initial_dt_s, c.total_time_s)
        positive = np.geomspace(first, c.total_time_s, c.output_points - 1)
        return np.unique(np.concatenate(([0.0], positive))).astype(float)

    @staticmethod
    def _snapshot(out: dict) -> dict:
        return {
            "qfg_C_m2": float(out["qfg_C_m2"]),
            "qfg_by_fg_C_m2": np.asarray(out["qfg_by_fg_C_m2"], dtype=float).copy(),
            "mean_occupation_by_fg": np.asarray(out["mean_occupation_by_fg"], dtype=float).copy(),
            "delta_vfb_V": float(out["delta_vfb_V"]),
            "delta_vfb_by_fg_V": np.asarray(out["delta_vfb_by_fg_V"], dtype=float).copy(),
            "local_field_by_fg_V_m": np.asarray(out["electrostatic_local_field_by_fg_V_m"], dtype=float).copy(),
            "local_potential_by_fg_V": np.asarray(out["electrostatic_local_potential_by_fg_V"], dtype=float).copy(),
            "inter_fg_flux_by_link_m2_s": np.asarray(out["inter_fg_flux_by_link_m2_s"], dtype=float).copy(),
            "transport_transmission_by_link": np.asarray(out["transport_transmission_by_link"], dtype=float).copy(),
            "transport_link_ids": tuple(out["transport_link_ids"]),
        }

    def run(self, initial_state: DeviceState | None = None) -> RetentionResult:
        c = self.config
        state = initial_state.copy() if initial_state is not None else DeviceState.empty_for_device(self.simulator.device)
        state.validate(self.simulator.device)

        # A zero-duration call gives a fully self-consistent initial snapshot.
        initial = self.simulator.relax_voltage(
            state,
            c.gate_voltage_V,
            dwell_time_s=0.0,
            internal_dt_s=c.initial_dt_s,
        )
        state = initial["state"]
        snapshots = [self._snapshot(initial)]
        times = [0.0]
        charge_rates = [0.0]
        requested = self._output_times()
        next_output = 1
        time_s = 0.0
        dt_s = min(c.initial_dt_s, c.maximum_dt_s)
        stable_count = 0
        quasi_time = None
        previous_q = float(initial["qfg_C_m2"])

        while time_s < c.total_time_s and next_output < requested.size:
            target = float(requested[next_output])
            step = min(dt_s, target - time_s, c.total_time_s - time_s)
            if step <= 0.0:
                next_output += 1
                continue
            out = self.simulator.relax_voltage(
                state,
                c.gate_voltage_V,
                dwell_time_s=step,
                internal_dt_s=step,
            )
            state = out["state"]
            current_q = float(out["qfg_C_m2"])
            rate = abs(current_q - previous_q) / step
            previous_q = current_q
            time_s += step

            if rate <= c.quasi_equilibrium_tolerance_C_m2_s:
                stable_count += 1
            else:
                stable_count = 0
            if stable_count >= c.quasi_equilibrium_steps and quasi_time is None:
                quasi_time = time_s

            if math.isclose(time_s, target, rel_tol=1e-12, abs_tol=max(1e-18, 1e-12 * target)):
                snapshots.append(self._snapshot(out))
                times.append(time_s)
                charge_rates.append(rate)
                next_output += 1
                if c.stop_at_quasi_equilibrium and quasi_time is not None:
                    break
            dt_s = min(dt_s * c.growth_factor, c.maximum_dt_s)

        def stack(key: str) -> np.ndarray:
            return np.asarray([snap[key] for snap in snapshots], dtype=float)

        return RetentionResult(
            time_s=np.asarray(times, dtype=float),
            qfg_C_m2=stack("qfg_C_m2"),
            qfg_by_fg_C_m2=stack("qfg_by_fg_C_m2"),
            mean_occupation_by_fg=stack("mean_occupation_by_fg"),
            delta_vfb_V=stack("delta_vfb_V"),
            delta_vfb_by_fg_V=stack("delta_vfb_by_fg_V"),
            local_field_by_fg_V_m=stack("local_field_by_fg_V_m"),
            local_potential_by_fg_V=stack("local_potential_by_fg_V"),
            inter_fg_flux_by_link_m2_s=stack("inter_fg_flux_by_link_m2_s"),
            transport_transmission_by_link=stack("transport_transmission_by_link"),
            transport_link_ids=snapshots[-1]["transport_link_ids"],
            charge_rate_C_m2_s=np.asarray(charge_rates, dtype=float),
            final_state=state,
            quasi_equilibrium_reached=quasi_time is not None,
            quasi_equilibrium_time_s=quasi_time,
        )
