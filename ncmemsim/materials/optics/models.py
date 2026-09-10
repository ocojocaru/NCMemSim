from __future__ import annotations

from dataclasses import dataclass
import math

from ..base import NanocrystalMaterial
from ..interpolation import validate_fraction
from ..provenance import (
    MaterialProperty,
    ParameterProvenance,
    ParameterStatus,
)

from ...constants import (
    BOLTZMANN_J_K,
    ELEMENTARY_CHARGE_C,
    LIGHT_SPEED_M_S,
    PLANCK_J_S,
)

from typing import Mapping

@dataclass(frozen=True)
class OpticalPoint:
    wavelength_nm: float
    photon_energy_eV: float
    absorption_coefficient_m_inv: float

    direct_gap_eV: float | None = None
    indirect_gap_eV: float | None = None

    alpha_direct_m_inv: float | None = None
    alpha_indirect_m_inv: float | None = None
    alpha_urbach_m_inv: float | None = None

    refractive_index: float | None = None
    extinction_coefficient: float | None = None
    
    provenance: Mapping[str, ParameterProvenance] | None = None


@dataclass(frozen=True)
class GeSnOpticalParameterSet:
    """
    Literature-derived compact Ge/GeSn optical parameter set.

    The Gamma- and L-valley parameterizations represent unstrained
    bulk Ge1-xSnx at 300 K.

    Strain and explicit temperature dependence are not included.
    """

    name: str = "gesn-optical-300K-v1"

    temperature_K: float = 300.0

    # Direct Gamma valley
    ge_direct_gap_eV: float = 0.7985
    alpha_sn_direct_gap_eV: float = -0.413
    direct_gap_bowing_eV: float = 2.89

    # Indirect L valley
    ge_indirect_gap_eV: float = 0.664
    alpha_sn_indirect_gap_eV: float = 0.092
    indirect_gap_bowing_eV: float = 0.89

    absorption_prefactor_m_inv_eV_sqrt: float = 1.0e7
    broadening_eV: float = 0.0

    def __post_init__(self) -> None:
        if self.temperature_K <= 0:
            raise ValueError("temperature_K must be positive.")

        if self.absorption_prefactor_m_inv_eV_sqrt < 0:
            raise ValueError("Absorption prefactor cannot be negative.")

        if self.direct_gap_bowing_eV < 0:
            raise ValueError("direct_gap_bowing_eV cannot be negative.")

        if self.indirect_gap_bowing_eV < 0:
            raise ValueError("indirect_gap_bowing_eV cannot be negative.")

        if self.broadening_eV < 0:
            raise ValueError("broadening_eV cannot be negative.")


DIRECT_GAP_PROVENANCE = ParameterProvenance(
    source=(
        "GeSn direct-gap parameterization at 300 K; "
        "Ge and alpha-Sn endpoints with composition bowing"
    ),
    status=ParameterStatus.LITERATURE,
    doi="10.1039/D2NR07107J",
    notes=(
        "Unstrained bulk Ge1-xSnx direct Gamma gap at 300 K. "
        "Eg_Gamma(Ge)=0.7985 eV, "
        "Eg_Gamma(alpha-Sn)=-0.413 eV, "
        "b_Gamma=2.89 eV. "
        "Strain and temperature corrections are not included."
    ),
    parameter_set="gesn-optical-300K-v1",
)

INDIRECT_GAP_PROVENANCE = ParameterProvenance(
    source=(
        "Compiled GeSn L-valley literature parameterization: "
        "Eg_L(Ge)=0.664 eV, Eg_L(alpha-Sn)=0.092 eV, "
        "b_L=0.89 eV"
    ),
    status=ParameterStatus.LITERATURE,
    doi=None,
    notes=(
        "Room-temperature unstrained compact parameterization. "
        "The L-valley bowing is not universal; reported literature "
        "values vary substantially with model, strain and experiment. "
        "This parameter set is explicitly versioned."
    ),
    parameter_set="gesn-optical-300K-v1",
)

ABSORPTION_PREFACTOR_PROVENANCE = ParameterProvenance(
    source="NCMemSim compact direct-edge absorption approximation",
    status=ParameterStatus.ASSUMED,
    notes=(
        "The compact sqrt(E-Eg) prefactor is not a literature-exact "
        "GeSn absorption model. It must be calibrated or replaced "
        "before quantitative optical predictions."
    ),
    parameter_set="gesn-optical-300K-v1",
)

ABSORPTION_MODEL_PROVENANCE = ParameterProvenance(
    source=(
        "Tran et al., Journal of Applied Physics 119, "
        "103106 (2016)"
    ),
    status=ParameterStatus.LITERATURE,
    doi="10.1063/1.4943652",
    notes=(
        "Supports decomposition of GeSn absorption into "
        "direct-gap, indirect-gap and Urbach-tail contributions. "
        "Experimental domain: Ge1-xSnx with x=0-0.10, "
        "1500-2500 nm, room temperature."
    ),
    parameter_set="gesn-absorption-compact-v1",
)

ABSORPTION_COEFFICIENT_PROVENANCE = ParameterProvenance(
    source="NCMemSim provisional GeSn absorption amplitudes",
    status=ParameterStatus.ASSUMED,
    notes=(
        "Numerical direct, indirect and Urbach amplitudes are "
        "provisional. Do not use for quantitative publication "
        "before calibration against experimental absorption data."
    ),
    parameter_set="gesn-absorption-compact-v1",
)

PHONON_OCCUPATION_PROVENANCE = ParameterProvenance(
    source="Bose-Einstein phonon occupation",
    status=ParameterStatus.LITERATURE,
    notes=(
        "Thermal phonon occupation uses the Bose-Einstein "
        "distribution. The phonon energy and indirect absorption "
        "amplitude remain model parameters."
    ),
    parameter_set="gesn-absorption-compact-v1",
)

def photon_energy_eV(wavelength_nm: float) -> float:
    if wavelength_nm <= 0:
        raise ValueError("wavelength_nm must be positive.")

    return (
        PLANCK_J_S
        * LIGHT_SPEED_M_S
        / (wavelength_nm * 1e-9)
        / ELEMENTARY_CHARGE_C
    )


def direct_gap_gesn_eV(
    sn_fraction: float,
    parameters: GeSnOpticalParameterSet | None = None,
) -> float:
    ps = parameters or GeSnOpticalParameterSet()
    x = validate_fraction(sn_fraction)

    return (
        (1.0 - x) * ps.ge_direct_gap_eV
        + x * ps.alpha_sn_direct_gap_eV
        - ps.direct_gap_bowing_eV * x * (1.0 - x)
    )
    
def indirect_gap_gesn_eV(
    sn_fraction: float,
    parameters: GeSnOpticalParameterSet | None = None,
) -> float:
    ps = parameters or GeSnOpticalParameterSet()
    x = validate_fraction(sn_fraction)

    return (
        (1.0 - x) * ps.ge_indirect_gap_eV
        + x * ps.alpha_sn_indirect_gap_eV
        - ps.indirect_gap_bowing_eV * x * (1.0 - x)
    )


class CompactOpticalMaterialModel:
    """
    Compact, calibratable Ge/GeSn direct-edge absorption model.

    This Phase-E model provides a transparent optical-programming
    interface. It is not a full dielectric-function or k·p model.
    """

    def __init__(
        self,
        parameters: GeSnOpticalParameterSet | None = None,
    ):
        self.parameters = parameters or GeSnOpticalParameterSet()

    def direct_gap_property(
        self,
        material: NanocrystalMaterial,
    ) -> MaterialProperty:
        gap = direct_gap_gesn_eV(
            material.sn_fraction,
            self.parameters,
        )

        return MaterialProperty(
            value=gap,
            unit="eV",
            provenance=ParameterProvenance(
                source=DIRECT_GAP_PROVENANCE.source,
                status=DIRECT_GAP_PROVENANCE.status,
                doi=DIRECT_GAP_PROVENANCE.doi,
                notes=DIRECT_GAP_PROVENANCE.notes,
                parameter_set=self.parameters.name,
            ),
            symbol="E_g^Gamma",
        )
        
    def indirect_gap_property(
        self,
        material: NanocrystalMaterial,
    ) -> MaterialProperty:
        gap = indirect_gap_gesn_eV(
            material.sn_fraction,
            self.parameters,
        )

        return MaterialProperty(
            value=gap,
            unit="eV",
            provenance=ParameterProvenance(
                source=INDIRECT_GAP_PROVENANCE.source,
                status=INDIRECT_GAP_PROVENANCE.status,
                doi=INDIRECT_GAP_PROVENANCE.doi,
                notes=INDIRECT_GAP_PROVENANCE.notes,
                parameter_set=self.parameters.name,
            ),
            symbol="E_g^L",
        )

    def evaluate(
        self,
        material: NanocrystalMaterial,
        wavelength_nm: float,
    ) -> OpticalPoint:
        energy_eV = photon_energy_eV(wavelength_nm)

        gap_property = self.direct_gap_property(material)
        direct_gap_eV = gap_property.value

        excess_eV = (
            energy_eV
            - direct_gap_eV
            + self.parameters.broadening_eV
        )

        alpha = (
            self.parameters.absorption_prefactor_m_inv_eV_sqrt
            * math.sqrt(max(excess_eV, 0.0))
        )

        return OpticalPoint(
            wavelength_nm=wavelength_nm,
            photon_energy_eV=energy_eV,
            absorption_coefficient_m_inv=alpha,
            direct_gap_eV=direct_gap_eV,
        )
        
@dataclass(frozen=True)
class GeSnAbsorptionParameterSet:
    """
    Compact Ge/GeSn absorption parameter set.

    Functional forms follow the direct, indirect and Urbach
    decomposition used for Ge/GeSn optical absorption.

    Numerical amplitudes and broadening parameters remain
    provisional until experimentally calibrated.
    """

    name: str = "gesn-absorption-compact-v1"

    direct_prefactor_A: float = 1.0e7

    indirect_prefactor_A: float = 1.0e6
    phonon_energy_eV: float = 0.027

    urbach_energy_eV: float = 0.012
    urbach_edge_alpha_m_inv: float = 1.0e5
    
    temperature_K: float = 300.0

    def __post_init__(self) -> None:
        values = (
            self.direct_prefactor_A,
            self.indirect_prefactor_A,
            self.phonon_energy_eV,
            self.urbach_energy_eV,
            self.urbach_edge_alpha_m_inv,
            self.temperature_K,
        )

        if min(values) < 0:
            raise ValueError(
                "Absorption-model parameters cannot be negative."
            )

        if self.urbach_energy_eV <= 0:
            raise ValueError("urbach_energy_eV must be positive.")
            
        if self.temperature_K <= 0:
            raise ValueError("temperature_K must be positive.")

        if self.phonon_energy_eV <= 0:
            raise ValueError("phonon_energy_eV must be positive.")
            
def urbach_absorption_m_inv(
    photon_energy_eV: float,
    direct_gap_eV: float,
    parameters: GeSnAbsorptionParameterSet,
) -> float:
    if photon_energy_eV <= 0:
        raise ValueError("photon_energy_eV must be positive.")

    if photon_energy_eV >= direct_gap_eV:
        return 0.0

    return (
        parameters.urbach_edge_alpha_m_inv
        * math.exp(
            (photon_energy_eV - direct_gap_eV)
            / parameters.urbach_energy_eV
        )
    )
    
def indirect_absorption_m_inv(
    photon_energy_eV: float,
    indirect_gap_eV: float,
    parameters: GeSnAbsorptionParameterSet,
) -> float:
    if photon_energy_eV <= 0:
        raise ValueError("photon_energy_eV must be positive.")

    eph = parameters.phonon_energy_eV

    n_ph = phonon_occupation(
        eph,
        parameters.temperature_K,
    )

    phonon_absorption = max(
        photon_energy_eV - indirect_gap_eV + eph,
        0.0,
    )

    phonon_emission = max(
        photon_energy_eV - indirect_gap_eV - eph,
        0.0,
    )

    return parameters.indirect_prefactor_A * (
        n_ph * phonon_absorption**2
        + (n_ph + 1.0) * phonon_emission**2
    )
    
def direct_absorption_m_inv(
    photon_energy_eV: float,
    direct_gap_eV: float,
    parameters: GeSnAbsorptionParameterSet,
) -> float:
    if photon_energy_eV <= 0:
        raise ValueError("photon_energy_eV must be positive.")

    excess = photon_energy_eV - direct_gap_eV

    if excess <= 0:
        return 0.0

    return (
        parameters.direct_prefactor_A
        * math.sqrt(excess)
        / photon_energy_eV
    )
    
class CompositeGeSnAbsorptionModel:
    """
    Compact Ge/GeSn absorption model.

    Band-edge energies are literature-derived.
    Absorption amplitudes are provisional/calibratable.
    """

    def __init__(
        self,
        optical_parameters: GeSnOpticalParameterSet | None = None,
        absorption_parameters: GeSnAbsorptionParameterSet | None = None,
    ):
        self.optical_parameters = (
            optical_parameters or GeSnOpticalParameterSet()
        )
        self.absorption_parameters = (
            absorption_parameters or GeSnAbsorptionParameterSet()
        )

    def evaluate(
        self,
        material: NanocrystalMaterial,
        wavelength_nm: float,
    ) -> OpticalPoint:
        energy = photon_energy_eV(wavelength_nm)

        eg_gamma = direct_gap_gesn_eV(
            material.sn_fraction,
            self.optical_parameters,
        )

        eg_l = indirect_gap_gesn_eV(
            material.sn_fraction,
            self.optical_parameters,
        )

        alpha_direct = direct_absorption_m_inv(
            energy,
            eg_gamma,
            self.absorption_parameters,
        )

        alpha_indirect = indirect_absorption_m_inv(
            energy,
            eg_l,
            self.absorption_parameters,
        )

        alpha_urbach = urbach_absorption_m_inv(
            energy,
            eg_gamma,
            self.absorption_parameters,
        )

        alpha_total = (
            alpha_direct
            + alpha_indirect
            + alpha_urbach
        )
        

        return OpticalPoint(
            wavelength_nm=wavelength_nm,
            photon_energy_eV=energy,
            absorption_coefficient_m_inv=alpha_total,
            direct_gap_eV=eg_gamma,
            indirect_gap_eV=eg_l,
            alpha_direct_m_inv=alpha_direct,
            alpha_indirect_m_inv=alpha_indirect,
            alpha_urbach_m_inv=alpha_urbach,
            provenance={
                "model_form": ABSORPTION_MODEL_PROVENANCE,
                "coefficients": ABSORPTION_COEFFICIENT_PROVENANCE,
                "phonon_occupation": PHONON_OCCUPATION_PROVENANCE,
            },
        )
        
def phonon_occupation(
    phonon_energy_eV: float,
    temperature_K: float,
) -> float:
    """
    Bose-Einstein occupation number for a phonon mode.
    """
    if phonon_energy_eV <= 0:
        raise ValueError("phonon_energy_eV must be positive.")

    if temperature_K <= 0:
        raise ValueError("temperature_K must be positive.")

    exponent = (
        phonon_energy_eV
        * ELEMENTARY_CHARGE_C
        / (BOLTZMANN_J_K * temperature_K)
    )

    return 1.0 / math.expm1(exponent)
