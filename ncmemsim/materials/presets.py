from .base import Material
from .database import BASE_PROPERTIES

def _bulk(name: str) -> Material:
    p=BASE_PROPERTIES[name]
    return Material(
        name=name,eps_r=p["eps_r"].value,
        electron_affinity_eV=p.get("electron_affinity_eV").value if p.get("electron_affinity_eV") else None,
        bandgap_eV=p.get("bandgap_eV").value if p.get("bandgap_eV") else None,
        electron_effective_mass_m0=p.get("effective_mass_m0").value if p.get("effective_mass_m0") else None,
        metadata={"parameter_set":"default-v1"},properties=p,
    )
HFO2=_bulk("HfO2")
SIO2=_bulk("SiO2")
SILICON=_bulk("Si")
