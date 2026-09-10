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
    ELEMENTARY_CHARGE_C,
    LIGHT_SPEED_M_S,
    PLANCK_J_S,
)


@dataclass(frozen=True)
class OpticalPoint:
    wavelength_nm: float
    photon_energy_eV: float
    absorption_coefficient_m_inv: float
    direct_gap_eV: float | None = None
    refractive_index: float | None = None
    extinction_coefficient: float | None = None


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
        "GeSn L-valley indirect-gap parameterization "
        "for unstrained bulk material at 300 K"
    ),
    status=ParameterStatus.LITERATURE,
    notes=(
        "Eg_L(Ge)=0.664 eV, "
        "Eg_L(alpha-Sn)=0.092 eV, "
        "b_L=0.89 eV. "
        "The literature reports significant variation in L-valley "
        "bowing; this parameter set is therefore explicitly versioned. "
        "Strain and temperature corrections are not included."
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
    name: str = "gesn-absorption-compact-v1"

    urbach_energy_eV: float = 0.012
    urbach_alpha_edge_m_inv: float = 1.0e5

    indirect_prefactor_m_inv_eV2: float = 1.0e6
    acoustic_phonon_energy_eV: float = 0.027

    direct_prefactor_m_inv_eV_sqrt: float = 1.0e7

    def __post_init__(self) -> None:
        if self.urbach_energy_eV <= 0:
            raise ValueError("urbach_energy_eV must be positive.")

        if self.urbach_alpha_edge_m_inv < 0:
            raise ValueError("urbach_alpha_edge_m_inv cannot be negative.")

        if self.indirect_prefactor_m_inv_eV2 < 0:
            raise ValueError("indirect_prefactor_m_inv_eV2 cannot be negative.")

        if self.acoustic_phonon_energy_eV < 0:
            raise ValueError("acoustic_phonon_energy_eV cannot be negative.")

        if self.direct_prefactor_m_inv_eV_sqrt < 0:
            raise ValueError("direct_prefactor_m_inv_eV_sqrt cannot be negative.")
            
def urbach_absorption_m_inv(
    photon_energy_eV: float,
    edge_eV: float,
    parameters: GeSnAbsorptionParameterSet,
) -> float:
    if photon_energy_eV >= edge_eV:
        return 0.0

    return (
        parameters.urbach_alpha_edge_m_inv
        * math.exp(
            (photon_energy_eV - edge_eV)
            / parameters.urbach_energy_eV
        )
    )
    
def indirect_absorption_m_inv(
    photon_energy_eV: float,
    indirect_gap_eV: float,
    parameters: GeSnAbsorptionParameterSet,
) -> float:
    eph = parameters.acoustic_phonon_energy_eV
    ap = parameters.indirect_prefactor_m_inv_eV2

    absorption = 0.0

    term_abs = photon_energy_eV - indirect_gap_eV + eph
    if term_abs > 0:
        absorption += ap * term_abs**2

    term_emit = photon_energy_eV - indirect_gap_eV - eph
    if term_emit > 0:
        absorption += ap * term_emit**2

    return absorption
    
def direct_absorption_m_inv(
    photon_energy_eV: float,
    direct_gap_eV: float,
    parameters: GeSnAbsorptionParameterSet,
) -> float:
    excess = photon_energy_eV - direct_gap_eV

    if excess <= 0:
        return 0.0

    return (
        parameters.direct_prefactor_m_inv_eV_sqrt
        * math.sqrt(excess)
    )
    
class CompositeGeSnAbsorptionModel:
    """
    Compact Ge/GeSn absorption model with explicit direct,
    indirect, and Urbach-tail contributions.

    The decomposition follows the physical structure used in
    GeSn optical-property literature, while numerical prefactors
    remain provisional/calibratable.
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

        direct_gap = direct_gap_gesn_eV(
            material.sn_fraction,
            self.optical_parameters,
        )

        # Temporary approximation until an independent L-gap
        # parameterization is introduced.
        indirect_gap = material.bandgap_eV

        alpha_direct = direct_absorption_m_inv(
            energy,
            direct_gap,
            self.absorption_parameters,
        )

        alpha_indirect = 0.0
        if indirect_gap is not None:
            alpha_indirect = indirect_absorption_m_inv(
                energy,
                indirect_gap,
                self.absorption_parameters,
            )

        alpha_urbach = urbach_absorption_m_inv(
            energy,
            direct_gap,
            self.absorption_parameters,
        )

        return OpticalPoint(
            wavelength_nm=wavelength_nm,
            photon_energy_eV=energy,
            absorption_coefficient_m_inv=(
                alpha_direct
                + alpha_indirect
                + alpha_urbach
            ),
            direct_gap_eV=direct_gap,
        )
        
