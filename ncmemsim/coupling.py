from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CouplingResult:
    """Compact electrostatic coupling of distributed FG sheet charges.

    ``sensitivity_factors`` are dimensionless centroid weighting factors.
    ``coefficients_m2_F`` convert sheet charge (C/m²) to voltage.  Their
    product with the charge vector gives each FG contribution to the flat-band
    shift.  The matrix is diagonal in D2; a full mutual-capacitance model can
    later implement the same interface without changing the simulator.
    """

    qfg_by_fg_C_m2: np.ndarray
    sensitivity_factors: np.ndarray
    coefficients_m2_F: np.ndarray
    delta_vfb_by_fg_V: np.ndarray
    delta_vfb_V: float
    matrix_m2_F: np.ndarray


class CouplingModel:
    """Interface for floating-gate electrostatic coupling models."""

    def sensitivity_factors(self, device) -> np.ndarray:  # pragma: no cover - interface
        raise NotImplementedError

    def evaluate(self, device, qfg_by_fg_C_m2, cox_F_m2: float) -> CouplingResult:  # pragma: no cover - interface
        raise NotImplementedError


class CompactCouplingModel(CouplingModel):
    """Centroid-weighted compact model for one to three floating gates.

    For multiple FGs, a sheet charge is weighted by its electrical depth from
    the gate towards the substrate.  A charge close to the gate therefore has
    a weaker control-voltage effect than one close to the substrate.

    For a single FG, ``legacy_single_fg=True`` deliberately returns a factor of
    one, preserving the validated Phase-B relation exactly::

        delta_VFB = -QFG / Cox
    """

    def __init__(self, *, legacy_single_fg: bool = True):
        self.legacy_single_fg = bool(legacy_single_fg)

    @staticmethod
    def _electrical_centroid_depths_m_over_epsr(device) -> np.ndarray:
        depths: list[float] = []
        running = 0.0
        fg_names = {fg.name for fg in device.floating_gates()}
        for layer in device.layers:
            term = layer.thickness_nm * 1e-9 / layer.eps_r
            if layer.name in fg_names:
                depths.append(running + 0.5 * term)
            running += term
        return np.asarray(depths, dtype=float)

    def sensitivity_factors(self, device) -> np.ndarray:
        n_fgs = device.number_of_fgs()
        if n_fgs < 1:
            raise ValueError("At least one floating gate is required")
        if n_fgs == 1 and self.legacy_single_fg:
            return np.ones(1, dtype=float)
        total = sum(layer.thickness_nm * 1e-9 / layer.eps_r for layer in device.layers)
        if total <= 0:
            raise ValueError("Device electrical thickness must be positive")
        beta = self._electrical_centroid_depths_m_over_epsr(device) / total
        return np.clip(beta, 0.0, 1.0)

    def evaluate(self, device, qfg_by_fg_C_m2, cox_F_m2: float) -> CouplingResult:
        q = np.asarray(qfg_by_fg_C_m2, dtype=float)
        if q.ndim != 1 or q.size != device.number_of_fgs():
            raise ValueError("Charge vector must contain one value per floating gate")
        if np.any(~np.isfinite(q)):
            raise ValueError("Floating-gate charges must be finite")
        if cox_F_m2 <= 0:
            raise ValueError("cox_F_m2 must be positive")
        beta = self.sensitivity_factors(device)
        coeff = beta / cox_F_m2
        delta_by_fg = -coeff * q
        matrix = np.diag(coeff)
        return CouplingResult(
            qfg_by_fg_C_m2=q.copy(),
            sensitivity_factors=beta,
            coefficients_m2_F=coeff,
            delta_vfb_by_fg_V=delta_by_fg,
            delta_vfb_V=float(np.sum(delta_by_fg)),
            matrix_m2_F=matrix,
        )
