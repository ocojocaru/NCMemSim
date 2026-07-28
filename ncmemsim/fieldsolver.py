from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .constants import EPSILON_0_F_M


@dataclass(frozen=True)
class FieldProfile:
    """One-dimensional electrostatic profile through the complete stack.

    The coordinate starts at the gate-side surface (``z=0``) and increases
    towards the semiconductor. Electric fields are piecewise constant inside
    each dielectric segment. Floating-gate charge is represented by a sheet at
    the centroid of each FG layer, so the displacement field can jump there.
    """

    z_nm: np.ndarray
    potential_V: np.ndarray
    electric_field_V_m: np.ndarray
    segment_layer_names: tuple[str, ...]
    local_fields_by_fg_V_m: np.ndarray
    local_potentials_by_fg_V: np.ndarray
    gate_side_displacement_C_m2: float

    @property
    def total_voltage_V(self) -> float:
        return float(self.potential_V[-1] - self.potential_V[0])

    def field_at_nm(self, z_nm: float) -> float:
        z = float(z_nm)
        if z < self.z_nm[0] or z > self.z_nm[-1]:
            raise ValueError("z_nm lies outside the device stack")
        if z == self.z_nm[-1]:
            return float(self.electric_field_V_m[-1])
        idx = int(np.searchsorted(self.z_nm[1:], z, side="right"))
        return float(self.electric_field_V_m[idx])

    def potential_at_nm(self, z_nm: float) -> float:
        z = float(z_nm)
        if z < self.z_nm[0] or z > self.z_nm[-1]:
            raise ValueError("z_nm lies outside the device stack")
        return float(np.interp(z, self.z_nm, self.potential_V))


class FieldSolver1D:
    """Piecewise-constant displacement-field solver for planar NC memories."""

    @staticmethod
    def _charge_vector(device, qfg_by_fg_C_m2=None) -> np.ndarray:
        n_fgs = device.number_of_fgs()
        if qfg_by_fg_C_m2 is None:
            return np.zeros(n_fgs, dtype=float)
        q = np.asarray(qfg_by_fg_C_m2, dtype=float)
        if q.shape != (n_fgs,):
            raise ValueError("Charge vector must contain one value per floating gate")
        if np.any(~np.isfinite(q)):
            raise ValueError("Floating-gate charges must be finite")
        return q

    def solve(self, device, applied_voltage_V: float, qfg_by_fg_C_m2=None) -> FieldProfile:
        q = self._charge_vector(device, qfg_by_fg_C_m2)
        fgs = device.floating_gates()
        fg_index_by_name = {fg.name: i for i, fg in enumerate(fgs)}

        # Each tuple is (thickness_m, eps_r, layer_name, charge sheet after segment).
        segments: list[tuple[float, float, str, int | None]] = []
        for layer in device.layers:
            thickness_m = layer.thickness_nm * 1e-9
            if layer.name in fg_index_by_name:
                idx = fg_index_by_name[layer.name]
                segments.append((0.5 * thickness_m, layer.eps_r, layer.name, idx))
                segments.append((0.5 * thickness_m, layer.eps_r, layer.name, None))
            else:
                segments.append((thickness_m, layer.eps_r, layer.name, None))

        denominator = sum(t / (EPSILON_0_F_M * eps_r) for t, eps_r, _, _ in segments)
        if denominator <= 0.0:
            raise ValueError("Device stack has zero electrical thickness")

        cumulative_q = 0.0
        charge_voltage = 0.0
        for thickness_m, eps_r, _, sheet_after in segments:
            charge_voltage += cumulative_q * thickness_m / (EPSILON_0_F_M * eps_r)
            if sheet_after is not None:
                cumulative_q += q[sheet_after]
        d_gate = (float(applied_voltage_V) - charge_voltage) / denominator

        z_nodes_m = [0.0]
        potentials = [0.0]
        fields: list[float] = []
        names: list[str] = []
        local_fields = np.zeros(len(fgs), dtype=float)
        local_potentials = np.zeros(len(fgs), dtype=float)
        cumulative_q = 0.0

        for thickness_m, eps_r, layer_name, sheet_after in segments:
            field_before = (d_gate + cumulative_q) / (EPSILON_0_F_M * eps_r)
            fields.append(float(field_before))
            names.append(layer_name)
            z_nodes_m.append(z_nodes_m[-1] + thickness_m)
            potentials.append(potentials[-1] + field_before * thickness_m)
            if sheet_after is not None:
                local_potentials[sheet_after] = potentials[-1]
                field_after = (d_gate + cumulative_q + q[sheet_after]) / (EPSILON_0_F_M * eps_r)
                local_fields[sheet_after] = 0.5 * (field_before + field_after)
                cumulative_q += q[sheet_after]

        return FieldProfile(
            z_nm=np.asarray(z_nodes_m, dtype=float) * 1e9,
            potential_V=np.asarray(potentials, dtype=float),
            electric_field_V_m=np.asarray(fields, dtype=float),
            segment_layer_names=tuple(names),
            local_fields_by_fg_V_m=local_fields,
            local_potentials_by_fg_V=local_potentials,
            gate_side_displacement_C_m2=float(d_gate),
        )
