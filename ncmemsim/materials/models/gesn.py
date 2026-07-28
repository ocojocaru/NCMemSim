from __future__ import annotations
from dataclasses import dataclass
from ..base import NanocrystalMaterial
from ..database import BASE_PROPERTIES, DEFAULT_ASSUMED
from ..interpolation import bowing, validate_fraction
from ..provenance import MaterialProperty

@dataclass(frozen=True)
class GeSnParameterSet:
    name: str = "default-v1"
    eps_bowing: float = 0.0
    bandgap_bowing_eV: float = 2.4
    affinity_bowing_eV: float = 0.0
    mass_bowing_m0: float = 0.0
    barrier_bowing_eV: float = 0.0
    phi_ge_prog_eV: float = 2.8
    phi_sn_prog_eV: float = 2.0
    phi_ge_erase_eV: float = 2.8
    phi_sn_erase_eV: float = 2.0

class GeSnModel:
    def __init__(self, composition: float, parameter_set: GeSnParameterSet | None=None):
        self.x=validate_fraction(composition)
        self.parameter_set=parameter_set or GeSnParameterSet()

    def _interp(self, key: str, bow: float=0.0) -> float:
        return bowing(self.x,BASE_PROPERTIES["Ge"][key].value,BASE_PROPERTIES["alpha-Sn"][key].value,bow)

    def build(self) -> NanocrystalMaterial:
        ps=self.parameter_set
        eps=self._interp("eps_r",ps.eps_bowing)
        eg=self._interp("bandgap_eV",ps.bandgap_bowing_eV)
        chi=self._interp("electron_affinity_eV",ps.affinity_bowing_eV)
        mass=self._interp("effective_mass_m0",ps.mass_bowing_m0)
        pprog=bowing(self.x,ps.phi_ge_prog_eV,ps.phi_sn_prog_eV,ps.barrier_bowing_eV)
        perase=bowing(self.x,ps.phi_ge_erase_eV,ps.phi_sn_erase_eV,ps.barrier_bowing_eV)
        props={
            "eps_r":MaterialProperty(eps,"1",DEFAULT_ASSUMED,"epsilon_r"),
            "bandgap_eV":MaterialProperty(eg,"eV",DEFAULT_ASSUMED,"E_g"),
            "electron_affinity_eV":MaterialProperty(chi,"eV",DEFAULT_ASSUMED,"chi"),
            "effective_mass_m0":MaterialProperty(mass,"m0",DEFAULT_ASSUMED,"m_e^*"),
            "phi_barrier_prog_eV":MaterialProperty(pprog,"eV",DEFAULT_ASSUMED,"Phi_prog"),
            "phi_barrier_erase_eV":MaterialProperty(perase,"eV",DEFAULT_ASSUMED,"Phi_erase"),
        }
        return NanocrystalMaterial(
            name=f"GeSn_{100*self.x:.1f}atpctSn", sn_fraction=self.x,
            eps_r_nc=eps,effective_mass_m0=mass,
            phi_barrier_prog_eV=pprog,phi_barrier_erase_eV=perase,
            bandgap_eV=eg,electron_affinity_eV=chi,
            metadata={"parameter_status":"provisional composition interpolation","parameter_set":ps.name},
            properties=props,model_name="GeSnModel",model_version=ps.name,
        )

def make_gesn(sn_fraction: float, **kwargs) -> NanocrystalMaterial:
    field_names=set(GeSnParameterSet.__dataclass_fields__)
    ps_kwargs={k:v for k,v in kwargs.items() if k in field_names}
    unknown=set(kwargs)-field_names
    if unknown:
        raise TypeError(f"Unknown GeSn parameter(s): {sorted(unknown)}")
    return GeSnModel(sn_fraction,GeSnParameterSet(**ps_kwargs)).build()
