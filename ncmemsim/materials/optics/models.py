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
    Parameter set for the compact Ge/GeSn direct-edge optical model.

    Values are provisional until replaced by a documented literature
    parameterization or experimental calibration.
    """

    name: str = "gesn-optical-provisional-v1"

    ge_direct_gap_eV: float = 0.80
    alpha_sn_direct_gap_eV: float = -0.41
    direct_gap_bowing_eV: float = 2.9

    absorption_prefactor_m_inv_eV_sqrt: float = 1.0e7
    broadening_eV: float = 0.0

    def __post_init__(self) -> None:
        if self.absorption_prefactor_m_inv_eV_sqrt < 0:
            raise ValueError("Absorption prefactor cannot be negative.")

        if self.direct_gap_bowing_eV < 0:
            raise ValueError("direct_gap_bowing_eV cannot be negative.")

        if self.broadening_eV < 0:
            raise ValueError("broadening_eV cannot be negative.")


OPTICAL_PROVISIONAL = ParameterProvenance(
    source="NCMemSim provisional compact Ge/GeSn optical model",
    status=ParameterStatus.ASSUMED,
    notes=(
        "Architecture parameter set for Phase E. "
        "Replace with literature-derived or calibrated parameters "
        "before quantitative publication."
    ),
    parameter_set="gesn-optical-provisional-v1",
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

        provenance = ParameterProvenance(
            source=OPTICAL_PROVISIONAL.source,
            status=OPTICAL_PROVISIONAL.status,
            notes=OPTICAL_PROVISIONAL.notes,
            parameter_set=self.parameters.name,
        )

        return MaterialProperty(
            value=gap,
            unit="eV",
            provenance=provenance,
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