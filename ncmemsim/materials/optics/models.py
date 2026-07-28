from __future__ import annotations
from dataclasses import dataclass
import math
from ..base import NanocrystalMaterial
from ...constants import ELEMENTARY_CHARGE_C, PLANCK_J_S, LIGHT_SPEED_M_S

@dataclass(frozen=True)
class OpticalPoint:
    wavelength_nm: float
    photon_energy_eV: float
    absorption_coefficient_m_inv: float
    refractive_index: float | None = None
    extinction_coefficient: float | None = None

class CompactOpticalMaterialModel:
    """Transparent, calibratable placeholder for Phase G; not a literature fit."""
    def __init__(self, absorption_prefactor_m_inv_eV_sqrt: float=1.0e7):
        if absorption_prefactor_m_inv_eV_sqrt < 0: raise ValueError("Prefactor cannot be negative.")
        self.prefactor=absorption_prefactor_m_inv_eV_sqrt
    def evaluate(self, material: NanocrystalMaterial, wavelength_nm: float) -> OpticalPoint:
        if wavelength_nm <= 0: raise ValueError("wavelength_nm must be positive")
        energy=PLANCK_J_S*LIGHT_SPEED_M_S/(wavelength_nm*1e-9)/ELEMENTARY_CHARGE_C
        eg=max(material.bandgap_eV or 0.0,0.0)
        alpha=self.prefactor*math.sqrt(max(energy-eg,0.0))
        return OpticalPoint(wavelength_nm,energy,alpha)
