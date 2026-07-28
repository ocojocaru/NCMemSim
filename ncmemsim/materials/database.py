from __future__ import annotations
from .provenance import MaterialProperty, ParameterProvenance, ParameterStatus

# Phase C intentionally uses explicit provisional defaults where no verified source
# has yet been entered. No literature reference is fabricated.
DEFAULT_ASSUMED = ParameterProvenance(
    source="NCMemSim provisional parameter set",
    status=ParameterStatus.ASSUMED,
    notes="Replace or calibrate before quantitative publication.",
    parameter_set="default-v1",
)

BASE_PROPERTIES = {
    "Ge": {
        "eps_r": MaterialProperty(16.0,"1",DEFAULT_ASSUMED,"epsilon_r"),
        "bandgap_eV": MaterialProperty(0.66,"eV",DEFAULT_ASSUMED,"E_g"),
        "electron_affinity_eV": MaterialProperty(4.00,"eV",DEFAULT_ASSUMED,"chi"),
        "effective_mass_m0": MaterialProperty(0.12,"m0",DEFAULT_ASSUMED,"m_e^*"),
    },
    "alpha-Sn": {
        "eps_r": MaterialProperty(24.0,"1",DEFAULT_ASSUMED,"epsilon_r"),
        "bandgap_eV": MaterialProperty(-0.41,"eV",DEFAULT_ASSUMED,"E_g"),
        "electron_affinity_eV": MaterialProperty(4.18,"eV",DEFAULT_ASSUMED,"chi"),
        "effective_mass_m0": MaterialProperty(0.03,"m0",DEFAULT_ASSUMED,"m_e^*"),
    },
    "Si": {
        "eps_r": MaterialProperty(11.7,"1",DEFAULT_ASSUMED,"epsilon_r"),
        "bandgap_eV": MaterialProperty(1.12,"eV",DEFAULT_ASSUMED,"E_g"),
        "electron_affinity_eV": MaterialProperty(4.05,"eV",DEFAULT_ASSUMED,"chi"),
    },
    "SiO2": {
        "eps_r": MaterialProperty(3.9,"1",DEFAULT_ASSUMED,"epsilon_r"),
        "bandgap_eV": MaterialProperty(8.9,"eV",DEFAULT_ASSUMED,"E_g"),
        "electron_affinity_eV": MaterialProperty(0.95,"eV",DEFAULT_ASSUMED,"chi"),
    },
    "HfO2": {
        "eps_r": MaterialProperty(25.0,"1",DEFAULT_ASSUMED,"epsilon_r"),
        "bandgap_eV": MaterialProperty(5.7,"eV",DEFAULT_ASSUMED,"E_g"),
        "electron_affinity_eV": MaterialProperty(2.0,"eV",DEFAULT_ASSUMED,"chi"),
    },
}

def get_base_property(material: str, property_name: str) -> MaterialProperty:
    try:
        return BASE_PROPERTIES[material][property_name]
    except KeyError as exc:
        raise KeyError(f"Unknown material/property: {material}/{property_name}") from exc
