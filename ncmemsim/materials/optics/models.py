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

    The direct-gap parameterization represents unstrained bulk
    Ge1-xSnx at 300 K. The compact absorption prefactor remains
    calibratable and is not itself a literature-exact absorption model.
    """

    name: str = "gesn-optical-300K-v1"

    temperature_K: float = 300.0

    ge_direct_gap_eV: float = 0.7985
    alpha_sn_direct_gap_eV: float = -0.413
    direct_gap_bowing_eV: float = 2.89

    absorption_prefactor_m_inv_eV_sqrt: float = 1.0e7
    broadening_eV: float = 0.0

    def __post_init__(self) -> None:
        if self.temperature_K <= 0:
            raise ValueError("temperature_K must be positive.")

        if self.absorption_prefactor_m_inv_eV_sqrt < 0:
            raise ValueError("Absorption prefactor cannot be negative.")

        if self.direct_gap_bowing_eV < 0:
            raise ValueError("direct_gap_bowing_eV cannot be negative.")

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