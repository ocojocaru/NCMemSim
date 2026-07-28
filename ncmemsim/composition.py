from .materials.interpolation import bowing as bowing_interpolation, validate_fraction
from .materials.database import BASE_PROPERTIES

def eps_r_gesn(x_sn: float, bowing: float=0.0) -> float:
    return bowing_interpolation(x_sn,BASE_PROPERTIES["Ge"]["eps_r"].value,BASE_PROPERTIES["alpha-Sn"]["eps_r"].value,bowing)
def bandgap_gesn_eV(x_sn: float, bowing: float=2.4) -> float:
    return bowing_interpolation(x_sn,BASE_PROPERTIES["Ge"]["bandgap_eV"].value,BASE_PROPERTIES["alpha-Sn"]["bandgap_eV"].value,bowing)
def effective_mass_gesn_m0(x_sn: float, bowing: float=0.0) -> float:
    return bowing_interpolation(x_sn,BASE_PROPERTIES["Ge"]["effective_mass_m0"].value,BASE_PROPERTIES["alpha-Sn"]["effective_mass_m0"].value,bowing)
def barrier_gesn_eV(x_sn: float,phi_ge_eV: float,phi_sn_eV: float,bowing: float=0.0) -> float:
    return bowing_interpolation(x_sn,phi_ge_eV,phi_sn_eV,bowing)
