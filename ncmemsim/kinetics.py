from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from .constants import EPSILON_0_F_M,ELEMENTARY_CHARGE_C,BOLTZMANN_J_K
from .state import FloatingGateState

@dataclass(frozen=True)
class KineticsConfig:
    nu0_Hz: float=1.0e12
    nu1_Hz: float=1.0e10
    nu2_Hz: float=3.0e9
    capacitance_eps_r: float=8.0
    density_profile: str='front_loaded'

@dataclass(frozen=True)
class RateArrays:
    r01: np.ndarray; r12: np.ndarray; r21: np.ndarray; r10: np.ndarray
    tprog: np.ndarray; terase: np.ndarray; field_V_m: np.ndarray

class OccupancyEngine:
    def __init__(self, tunneling_engine, config: KineticsConfig|None=None):
        self.tunneling=tunneling_engine; self.config=config or KineticsConfig()

    @staticmethod
    def nanocrystal_volume(diameter_m): return math.pi*diameter_m**3/6.0
    def nanocrystal_density(self, diameter_m, volume_fraction): return volume_fraction/self.nanocrystal_volume(diameter_m)
    def effective_density(self, diameter_m, volume_fraction, active_fraction): return active_fraction*self.nanocrystal_density(diameter_m,volume_fraction)
    def nc_capacitance(self, diameter_m): return 4.0*math.pi*EPSILON_0_F_M*self.config.capacitance_eps_r*(0.5*diameter_m)
    def charging_energy_J(self, diameter_m): return ELEMENTARY_CHARGE_C**2/(2.0*self.nc_capacitance(diameter_m))
    def gamma_c(self, diameter_m, temperature_K): return self.charging_energy_J(diameter_m)/(BOLTZMANN_J_K*temperature_K)

    @staticmethod
    def grid(fg):
        t=fg.thickness_nm*1e-9; n=fg.grid_points
        return np.linspace(0.5*t/n,t-0.5*t/n,n),t/n

    def density_profile(self, fg, x_m):
        n0=self.effective_density(fg.nc_diameter_nm*1e-9,fg.nc_volume_fraction,fg.electrically_active_fraction)
        profile=fg.spatial_profile or self.config.density_profile
        if profile=='uniform': return np.full_like(x_m,n0,dtype=float)
        if profile=='front_loaded':
            lam=0.30*fg.thickness_nm*1e-9; weights=np.exp(-x_m/lam); weights/=np.mean(weights); return n0*weights
        raise ValueError(f'Unknown density profile: {profile}')

    def rates(self, fg, x_m, veff_V: float, tunnel_base_distance_m: float, temperature_K: float, field_V_m: float | None = None) -> RateArrays:
        diameter=fg.nc_diameter_nm*1e-9
        base=max(tunnel_base_distance_m,0.0)
        path_for_field=max(base,1e-12)
        field=(self.tunneling.field_from_effective_voltage(veff_V,path_for_field)
               if field_V_m is None else abs(float(field_V_m)))
        arrays=[np.zeros_like(x_m) for _ in range(7)]
        r01,r12,r21,r10,tp,te,fv=arrays
        fp=self.tunneling.positive_activation(veff_V); fm=self.tunneling.negative_activation(veff_V)
        gamma=self.gamma_c(diameter,temperature_K)
        for i,x in enumerate(x_m):
            L=base+x
            tp[i]=self.tunneling.trapezoidal_wkb(L,field,fg.nc_material.phi_barrier_prog_eV)
            te[i]=self.tunneling.trapezoidal_wkb(L,field,fg.nc_material.phi_barrier_erase_eV)
            r01[i]=self.config.nu0_Hz*tp[i]*fp
            r12[i]=r01[i]*math.exp(-gamma)
            r21[i]=self.config.nu1_Hz*te[i]*fm
            r10[i]=self.config.nu2_Hz*te[i]*fm
            fv[i]=field
        return RateArrays(r01,r12,r21,r10,tp,te,fv)

    @staticmethod
    def step(state: FloatingGateState, rates: RateArrays, dt_s: float) -> FloatingGateState:
        p0,p1,p2=state.P0,state.P1,state.P2
        d0=-rates.r01*p0+rates.r10*p1
        d1=rates.r01*p0-(rates.r10+rates.r12)*p1+rates.r21*p2
        d2=rates.r12*p1-rates.r21*p2
        p0n=np.maximum(p0+d0*dt_s,0.0); p1n=np.maximum(p1+d1*dt_s,0.0); p2n=np.maximum(p2+d2*dt_s,0.0)
        total=p0n+p1n+p2n; total=np.where(total<=0,1.0,total)
        return FloatingGateState(
            p0n / total,
            p1n / total,
            p2n / total,
            fg_id=state.fg_id,
            layer_name=state.layer_name,
            z_center_nm=state.z_center_nm,
            metadata=dict(state.metadata),
        )

    @staticmethod
    def charge_density_C_m3(state, density_m3): return ELEMENTARY_CHARGE_C*density_m3*state.occupation
    @staticmethod
    def total_charge_C_m2(rho_C_m3, dx_m): return float(np.sum(rho_C_m3)*dx_m)
