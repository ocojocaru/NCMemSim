from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .network import TunnelNetwork
from .rates import LinkTransportResult, TransportStepResult


@dataclass(frozen=True)
class TransportConfig:
    enabled: bool = True
    attempt_frequency_Hz: float = 1.0e9
    default_barrier_eV: float = 1.78
    effective_mass_m0: float = 0.15
    direction_beta_V_inv: float = 8.0
    max_transfer_fraction_per_step: float = 0.10
    include_substrate_diagnostics: bool = True


class TransportEngine:
    """Conservative nearest-neighbour electron redistribution between FGs.

    The pre-existing substrate/FG kinetics remain responsible for injection and
    emission. D4 adds inter-FG exchange and exposes the substrate path as a
    diagnostic network link, avoiding double counting of substrate transport.
    """

    def __init__(self, tunneling_engine, config: TransportConfig | None = None):
        self.tunneling = tunneling_engine
        self.config = config or TransportConfig()

    def build_network(self, device) -> TunnelNetwork:
        return TunnelNetwork.from_device(
            device,
            barrier_eV=self.config.default_barrier_eV,
            effective_mass_m0=self.config.effective_mass_m0,
            include_substrate_link=self.config.include_substrate_diagnostics,
        )

    @staticmethod
    def _sheet_site_density(occupancy_engine, fg) -> float:
        x_m, dx_m = occupancy_engine.grid(fg)
        density = occupancy_engine.density_profile(fg, x_m)
        return float(np.sum(density) * dx_m)

    @staticmethod
    def _set_mean_occupation(state, target_m: float):
        """Move P0<->P1<->P2 while preserving normalization and bounds."""
        target = float(np.clip(target_m, 0.0, 1.0))
        current = state.mean_normalized_occupation
        delta_e = 2.0 * (target - current)  # electrons per NC
        p0, p1, p2 = state.P0.copy(), state.P1.copy(), state.P2.copy()
        if abs(delta_e) < 1e-18:
            return state.copy()
        if delta_e > 0.0:
            # Add electrons: first P0->P1, then P1->P2.
            need = delta_e
            cap01 = float(np.mean(p0))
            move01 = min(need, cap01)
            if cap01 > 0.0:
                frac = move01 / cap01
                moved = frac * p0
                p0 -= moved
                p1 += moved
            need -= move01
            cap12 = float(np.mean(p1))
            move12 = min(need, cap12)
            if cap12 > 0.0:
                frac = move12 / cap12
                moved = frac * p1
                p1 -= moved
                p2 += moved
        else:
            # Remove electrons: first P2->P1, then P1->P0.
            need = -delta_e
            cap21 = float(np.mean(p2))
            move21 = min(need, cap21)
            if cap21 > 0.0:
                frac = move21 / cap21
                moved = frac * p2
                p2 -= moved
                p1 += moved
            need -= move21
            cap10 = float(np.mean(p1))
            move10 = min(need, cap10)
            if cap10 > 0.0:
                frac = move10 / cap10
                moved = frac * p1
                p1 -= moved
                p0 += moved
        total = p0 + p1 + p2
        p0, p1, p2 = p0 / total, p1 / total, p2 / total
        out = state.copy()
        out.P0, out.P1, out.P2 = p0, p1, p2
        return out

    def evaluate(self, device, state, field_profile, occupancy_engine) -> TransportStepResult:
        network = self.build_network(device)
        fgs = device.floating_gates()
        n_fgs = len(fgs)
        sheet_sites = np.asarray(
            [self._sheet_site_density(occupancy_engine, fg) for fg in fgs], dtype=float
        )
        occupations = state.mean_normalized_occupations
        electron_sheet = 2.0 * occupations * sheet_sites
        capacity_sheet = 2.0 * sheet_sites
        net = np.zeros(n_fgs, dtype=float)
        results: list[LinkTransportResult] = []

        local_v = field_profile.local_potentials_by_fg_V
        for link in network.links:
            li, ri = link.left_fg_index, link.right_fg_index
            if link.kind == "inter_fg":
                dv = float(local_v[ri] - local_v[li])
                field = dv / link.length_m
                transmission = self.tunneling.trapezoidal_wkb(
                    link.length_m,
                    abs(field),
                    link.barrier_eV,
                    effective_mass_m0=link.effective_mass_m0,
                )
                forward_bias = 1.0 / (1.0 + math.exp(-self.config.direction_beta_V_inv * dv))
                backward_bias = 1.0 - forward_bias
                kf = self.config.attempt_frequency_Hz * transmission * forward_bias
                kb = self.config.attempt_frequency_Hz * transmission * backward_bias
                available_left = electron_sheet[li]
                empty_right = capacity_sheet[ri] - electron_sheet[ri]
                available_right = electron_sheet[ri]
                empty_left = capacity_sheet[li] - electron_sheet[li]
                forward_flux = kf * min(available_left, empty_right)
                backward_flux = kb * min(available_right, empty_left)
                flux = forward_flux - backward_flux  # positive left -> right
                net[li] -= flux
                net[ri] += flux
            else:
                # Diagnostic only; substrate injection is already handled by OccupancyEngine.
                li = link.left_fg_index
                substrate_v = field_profile.total_voltage_V
                dv = float(substrate_v - local_v[li])
                field = dv / link.length_m
                transmission = self.tunneling.trapezoidal_wkb(
                    link.length_m,
                    abs(field),
                    link.barrier_eV,
                    effective_mass_m0=link.effective_mass_m0,
                )
                forward_bias = 1.0 / (1.0 + math.exp(-self.config.direction_beta_V_inv * dv))
                kf = self.config.attempt_frequency_Hz * transmission * forward_bias
                kb = self.config.attempt_frequency_Hz * transmission * (1.0 - forward_bias)
                flux = 0.0
            results.append(
                LinkTransportResult(
                    link_id=link.link_id,
                    kind=link.kind,
                    field_V_m=float(field),
                    potential_difference_V=float(dv),
                    transmission=float(transmission),
                    forward_rate_Hz=float(kf),
                    backward_rate_Hz=float(kb),
                    net_electron_flux_m2_s=float(flux),
                    left_fg_index=link.left_fg_index,
                    right_fg_index=link.right_fg_index,
                )
            )
        return TransportStepResult(tuple(results), net)

    def step(self, device, state, field_profile, occupancy_engine, dt_s: float):
        result = self.evaluate(device, state, field_profile, occupancy_engine)
        if not self.config.enabled or device.number_of_fgs() < 2 or dt_s <= 0.0:
            return state.copy(), result

        fgs = device.floating_gates()
        sheet_sites = np.asarray(
            [self._sheet_site_density(occupancy_engine, fg) for fg in fgs], dtype=float
        )
        current_e = 2.0 * state.mean_normalized_occupations * sheet_sites
        delta_e = result.net_electron_flux_by_fg_m2_s * dt_s
        max_delta = self.config.max_transfer_fraction_per_step * 2.0 * sheet_sites
        delta_e = np.clip(delta_e, -max_delta, max_delta)

        # Independent per-node clipping can otherwise create or destroy charge
        # when neighbouring FG layers have different sheet-site densities.
        # Rebalance positive and negative transfers to the same conservative
        # amount before applying occupancy bounds.
        positive = float(np.sum(delta_e[delta_e > 0.0]))
        negative = float(-np.sum(delta_e[delta_e < 0.0]))
        transferable = min(positive, negative)
        if positive > 0.0:
            delta_e[delta_e > 0.0] *= transferable / positive
        if negative > 0.0:
            delta_e[delta_e < 0.0] *= transferable / negative

        lower = -current_e
        upper = 2.0 * sheet_sites - current_e
        delta_e = np.minimum(np.maximum(delta_e, lower), upper)
        # Bounds may introduce a small imbalance; remove it proportionally from
        # nodes that still have room in the compensating direction.
        imbalance = float(np.sum(delta_e))
        if abs(imbalance) > 0.0:
            if imbalance > 0.0:
                candidates = delta_e > lower
                room = delta_e[candidates] - lower[candidates]
                if room.size and float(np.sum(room)) > 0.0:
                    delta_e[candidates] -= imbalance * room / float(np.sum(room))
            else:
                candidates = delta_e < upper
                room = upper[candidates] - delta_e[candidates]
                if room.size and float(np.sum(room)) > 0.0:
                    delta_e[candidates] += (-imbalance) * room / float(np.sum(room))
        target_e = np.clip(current_e + delta_e, 0.0, 2.0 * sheet_sites)

        out = state.copy()
        out.floating_gates = [
            self._set_mean_occupation(fg_state, target_e[i] / (2.0 * sheet_sites[i]))
            for i, fg_state in enumerate(state.floating_gates)
        ]
        return out, result
