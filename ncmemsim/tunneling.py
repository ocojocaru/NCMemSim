from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from .constants import ELEMENTARY_CHARGE_C, HBAR_J_S, ELECTRON_MASS_KG

@dataclass(frozen=True)
class TunnelingConfig:
    injection_energy_eV: float = 0.10
    oxide_effective_mass_m0: float = 0.15
    integration_points: int = 160
    field_coupling_factor: float = 0.80
    activation_beta_V_inv: float = 0.8

class TunnelingEngine:
    def __init__(self, config: TunnelingConfig | None=None): self.config=config or TunnelingConfig()

    def field_from_effective_voltage(self, veff_V: float, path_length_m: float) -> float:
        return self.config.field_coupling_factor*abs(veff_V)/max(path_length_m,1e-12)

    def trapezoidal_wkb(self, length_m: float, field_V_m: float, barrier_eV: float, injection_energy_eV: float|None=None, effective_mass_m0: float|None=None) -> float:
        if length_m<=0: return 1.0
        e=self.config.injection_energy_eV if injection_energy_eV is None else injection_energy_eV
        mrel=self.config.oxide_effective_mass_m0 if effective_mass_m0 is None else effective_mass_m0
        s=np.linspace(0.0,length_m,self.config.integration_points)
        u=np.maximum(barrier_eV-field_V_m*s-e,0.0)
        if np.all(u<=0): return 1.0
        kappa=np.sqrt(2.0*(mrel*ELECTRON_MASS_KG)*(u*ELEMENTARY_CHARGE_C))/HBAR_J_S
        action=np.trapezoid(kappa,s)
        return float(np.exp(max(-2.0*action,-700.0)))

    def positive_activation(self, veff_V: float) -> float:
        return 1.0/(1.0+math.exp(-self.config.activation_beta_V_inv*veff_V))

    def negative_activation(self, veff_V: float) -> float:
        return 1.0/(1.0+math.exp(self.config.activation_beta_V_inv*veff_V))
