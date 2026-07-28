from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from .constants import EPSILON_0_F_M, ELEMENTARY_CHARGE_C, BOLTZMANN_J_K
from .coupling import CompactCouplingModel, CouplingModel, CouplingResult
from .fieldsolver import FieldProfile, FieldSolver1D

@dataclass(frozen=True)
class SemiconductorConfig:
    silicon_eps_r: float = 11.7
    intrinsic_density_m3: float = 1.0e16
    electron_affinity_eV: float = 4.05
    bandgap_eV: float = 1.12
    psi_max_V: float = 0.9
    transition_voltage_V: float = 0.65
    transition_width_V: float = 0.22
    accumulation_factor: float = 40.0

@dataclass(frozen=True)
class ElectrostaticsResult:
    cox_F_m2: float
    vfb0_V: float
    qfg_C_m2: float
    vfb_V: float
    veff_V: float
    capacitance_F_m2: float
    qfg_by_fg_C_m2: np.ndarray | None = None
    coupling: CouplingResult | None = None
    local_fields_by_fg_V_m: np.ndarray | None = None
    local_potentials_by_fg_V: np.ndarray | None = None
    field_profile: FieldProfile | None = None

    @property
    def delta_vfb_V(self) -> float:
        if self.coupling is not None:
            return self.coupling.delta_vfb_V
        return self.vfb_V - self.vfb0_V

    @property
    def delta_vfb_by_fg_V(self) -> np.ndarray:
        if self.coupling is None:
            return np.asarray([self.delta_vfb_V], dtype=float)
        return self.coupling.delta_vfb_by_fg_V

class ElectrostaticsEngine:
    def __init__(
        self,
        semiconductor: SemiconductorConfig | None = None,
        coupling_model: CouplingModel | None = None,
        field_solver: FieldSolver1D | None = None,
    ):
        self.semiconductor = semiconductor or SemiconductorConfig()
        self.coupling_model = coupling_model or CompactCouplingModel()
        self.field_solver = field_solver or FieldSolver1D()

    def equivalent_capacitance(self, device) -> float:
        return device.equivalent_dielectric_capacitance_F_m2()

    def fermi_potential(self, device) -> float:
        s=self.semiconductor
        return (BOLTZMANN_J_K*device.temperature_K/ELEMENTARY_CHARGE_C)*math.log(device.substrate_doping_m3/s.intrinsic_density_m3)

    def flatband_zero(self, device, qfix_C_m2: float=0.0, qit_C_m2: float=0.0) -> float:
        cox=self.equivalent_capacitance(device); s=self.semiconductor
        phi_s_eV=s.electron_affinity_eV+0.5*s.bandgap_eV+self.fermi_potential(device)
        return device.gate_work_function_eV-phi_s_eV-(qfix_C_m2+qit_C_m2)/cox

    @staticmethod
    def dynamic_flatband(vfb0_V: float, qfg_C_m2: float, cox_F_m2: float) -> float:
        return vfb0_V-qfg_C_m2/cox_F_m2

    def surface_potential_proxy(self, veff_V):
        s=self.semiconductor
        return s.psi_max_V*0.5*(1.0+np.tanh((np.asarray(veff_V)-s.transition_voltage_V)/s.transition_width_V))

    def semiconductor_capacitance(self, veff_V, cox_F_m2: float, substrate_doping_m3: float):
        s=self.semiconductor; psi=np.maximum(self.surface_potential_proxy(veff_V),1e-6)
        eps_si=s.silicon_eps_r*EPSILON_0_F_M
        wd=np.sqrt(2.0*eps_si*psi/(ELEMENTARY_CHARGE_C*substrate_doping_m3))
        cdep=eps_si/wd; cacc=s.accumulation_factor*cox_F_m2
        wacc=0.5*(1.0-np.tanh((np.asarray(veff_V)-0.0)/0.18))
        return wacc*cacc+(1.0-wacc)*cdep

    def mos_capacitance(self, veff_V, device):
        cox=self.equivalent_capacitance(device)
        cs=self.semiconductor_capacitance(veff_V,cox,device.substrate_doping_m3)
        return cox*cs/(cox+cs)

    @staticmethod
    def _charge_vector(device, qfg_C_m2) -> np.ndarray:
        q = np.asarray(qfg_C_m2, dtype=float)
        if q.ndim == 0:
            if device.number_of_fgs() != 1:
                raise ValueError("Multi-FG electrostatics requires a per-FG charge vector")
            return q.reshape(1)
        if q.ndim != 1 or q.size != device.number_of_fgs():
            raise ValueError("Charge vector must contain one value per floating gate")
        return q

    def evaluate(self, device, gate_voltage_V: float, qfg_C_m2, qfix_C_m2: float=0.0, qit_C_m2: float=0.0) -> ElectrostaticsResult:
        cox=self.equivalent_capacitance(device); vfb0=self.flatband_zero(device,qfix_C_m2,qit_C_m2)
        q_by_fg = self._charge_vector(device, qfg_C_m2)
        coupling = self.coupling_model.evaluate(device, q_by_fg, cox)
        q_total = float(np.sum(q_by_fg))
        vfb = vfb0 + coupling.delta_vfb_V
        veff=gate_voltage_V-vfb
        profile = self.field_solver.solve(device, veff, q_by_fg)
        local_fields = profile.local_fields_by_fg_V_m
        return ElectrostaticsResult(
            cox, vfb0, q_total, vfb, veff,
            float(self.mos_capacitance(veff,device)),
            qfg_by_fg_C_m2=q_by_fg.copy(),
            coupling=coupling,
            local_fields_by_fg_V_m=local_fields,
            local_potentials_by_fg_V=profile.local_potentials_by_fg_V,
            field_profile=profile,
        )

    def voltage_drops(self, device, applied_voltage_V: float) -> dict[str,float]:
        terms=[layer.thickness_nm*1e-9/layer.eps_r for layer in device.layers]
        total=sum(terms)
        return {layer.name: applied_voltage_V*term/total for layer,term in zip(device.layers,terms)}

    def local_fields_V_m(self, device, applied_voltage_V: float) -> dict[str,float]:
        drops=self.voltage_drops(device,applied_voltage_V)
        return {layer.name:drops[layer.name]/(layer.thickness_nm*1e-9) for layer in device.layers}

    def field_profile(self, device, applied_voltage_V: float, qfg_by_fg_C_m2=None) -> FieldProfile:
        return self.field_solver.solve(device, applied_voltage_V, qfg_by_fg_C_m2)

    def local_fields_at_fgs_V_m(self, device, applied_voltage_V: float, qfg_by_fg_C_m2=None) -> np.ndarray:
        return self.field_profile(device, applied_voltage_V, qfg_by_fg_C_m2).local_fields_by_fg_V_m.copy()
