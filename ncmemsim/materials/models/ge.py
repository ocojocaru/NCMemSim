from __future__ import annotations
from ..base import NanocrystalMaterial
from ..database import BASE_PROPERTIES, DEFAULT_ASSUMED
from ..provenance import MaterialProperty

def make_ge(*, phi_barrier_prog_eV: float=2.8, phi_barrier_erase_eV: float=2.8, parameter_set: str="default-v1") -> NanocrystalMaterial:
    p=BASE_PROPERTIES["Ge"]
    properties=dict(p)
    properties["phi_barrier_prog_eV"]=MaterialProperty(phi_barrier_prog_eV,"eV",DEFAULT_ASSUMED,"Phi_prog")
    properties["phi_barrier_erase_eV"]=MaterialProperty(phi_barrier_erase_eV,"eV",DEFAULT_ASSUMED,"Phi_erase")
    return NanocrystalMaterial(
        name="Ge", sn_fraction=0.0,
        eps_r_nc=p["eps_r"].value,
        effective_mass_m0=p["effective_mass_m0"].value,
        phi_barrier_prog_eV=phi_barrier_prog_eV,
        phi_barrier_erase_eV=phi_barrier_erase_eV,
        bandgap_eV=p["bandgap_eV"].value,
        electron_affinity_eV=p["electron_affinity_eV"].value,
        metadata={"parameter_status":"provisional/default","parameter_set":parameter_set},
        properties=properties, model_name="GeModel", model_version=parameter_set,
    )
