from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Mapping

from ..base import NanocrystalMaterial
from ..provenance import (
    ParameterProvenance,
    ParameterStatus,
)
from .domain import (
    EvaluationDomainStatus,
    OpticalValidationDomain,
    TRAN_2016_NEAR_EDGE_DOMAIN,
)
from .models import (
    DIRECT_GAP_PROVENANCE,
    direct_gap_gesn_eV,
    photon_energy_eV,
)


TRAN_2016_PARAMETER_SET_NAME = "gesn-near-edge-tran2016-v1"


TRAN_2016_DIRECT_PREFACTOR_PROVENANCE = ParameterProvenance(
    source=(
        "Tran et al., Journal of Applied Physics 119, "
        "103106 (2016)"
    ),
    status=ParameterStatus.LITERATURE_FITTED,
    doi="10.1063/1.4943652",
    notes=(
        "Direct-transition absorption prefactor A fitted by the "
        "publication authors to GeSn absorption coefficients obtained "
        "from spectroscopic ellipsometry through the Johs-Herzinger "
        "optical model. Reported central value: "
        "3.68e6 m^-1 eV^(1/2)."
    ),
    parameter_set=TRAN_2016_PARAMETER_SET_NAME,
    reported_uncertainty=0.86e6,
    uncertainty_unit="m^-1 eV^(1/2)",
)


TRAN_2016_URBACH_ENERGY_PROVENANCE = ParameterProvenance(
    source=(
        "Tran et al., Journal of Applied Physics 119, "
        "103106 (2016)"
    ),
    status=ParameterStatus.LITERATURE_FITTED,
    doi="10.1063/1.4943652",
    notes=(
        "Urbach width fitted by the publication authors from the "
        "near-edge exponential absorption tails. Reported central "
        "value: 10.58 meV with uncertainty 1.06 meV."
    ),
    parameter_set=TRAN_2016_PARAMETER_SET_NAME,
    reported_uncertainty=0.00106,
    uncertainty_unit="eV",
)


NEAR_EDGE_CONTINUITY_PROVENANCE = ParameterProvenance(
    source=(
        "NCMemSim analytical direct/Urbach continuity derivation"
    ),
    status=ParameterStatus.DERIVED,
    doi=None,
    notes=(
        "NCMemSim-derived connection between the Tran Eq. (3) "
        "direct branch and an exponential Urbach branch. The "
        "connection is constructed to enforce exact continuity of "
        "both absorption coefficient and first derivative. It must "
        "not be described as a literal implementation of Tran "
        "Eqs. (6), (7), or (18)."
    ),
    parameter_set=TRAN_2016_PARAMETER_SET_NAME,
)


@dataclass(frozen=True)
class GeSnNearEdgeParameterSet:
    """
    Literature-anchored Ge/GeSn near-edge absorption parameters.

    The numerical absorption parameters are based on Tran et al.
    (2016). The model represents a bulk-like, unstrained,
    room-temperature reference baseline.

    The direct-gap composition relation is intentionally not duplicated
    here. Near-edge models use the existing NCMemSim
    direct_gap_gesn_eV() parameterization.

    The 300 K value is the NCMemSim numerical representation of the
    room-temperature reference condition; it is not a fitted
    temperature parameter from Tran et al.
    """

    name: str = TRAN_2016_PARAMETER_SET_NAME

    direct_prefactor_A: float = 3.68e6
    urbach_energy_eV: float = 0.01058
    temperature_K: float = 300.0

    provenance: Mapping[str, ParameterProvenance] | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Parameter-set name cannot be empty.")

        values = {
            "direct_prefactor_A": self.direct_prefactor_A,
            "urbach_energy_eV": self.urbach_energy_eV,
            "temperature_K": self.temperature_K,
        }

        for name, value in values.items():
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite.")

            if value <= 0:
                raise ValueError(f"{name} must be positive.")


TRAN_2016_NEAR_EDGE_PARAMETERS = GeSnNearEdgeParameterSet(
    provenance={
        "direct_prefactor_A": TRAN_2016_DIRECT_PREFACTOR_PROVENANCE,
        "urbach_energy_eV": TRAN_2016_URBACH_ENERGY_PROVENANCE,
    },
)


@dataclass(frozen=True)
class NearEdgeConnection:
    """
    Exact C1 connection between direct and exponential Urbach branches.

    This connection is derived by NCMemSim while retaining the
    Tran Eq. (3) direct-absorption form:

        alpha_D(E) = A * sqrt(E - Eg) / E

    and an exponential Urbach branch:

        alpha_U(E) = alpha_0 * exp((E - Eg) / Delta_E)

    The connection energy and Urbach prefactor are chosen so that both
    alpha and d(alpha)/dE are continuous.
    """

    direct_gap_eV: float
    connection_offset_eV: float
    connection_energy_eV: float
    urbach_prefactor_m_inv: float


def _validate_positive_finite(
    value: float,
    name: str,
) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")

    if value <= 0:
        raise ValueError(f"{name} must be positive.")


def derive_near_edge_connection(
    direct_gap_eV: float,
    parameters: GeSnNearEdgeParameterSet | None = None,
) -> NearEdgeConnection:
    """
    Derive the exact direct/Urbach C1 connection.

    Matching logarithmic derivatives gives:

        1 / (2 yc) - 1 / (Eg + yc) = 1 / Delta_E

    where yc is the connection offset above the direct gap.

    The positive quadratic root is evaluated using an algebraically
    equivalent form that avoids subtractive cancellation when
    Delta_E << Eg.
    """

    _validate_positive_finite(
        direct_gap_eV,
        "direct_gap_eV",
    )

    params = parameters or TRAN_2016_NEAR_EDGE_PARAMETERS

    delta_eV = params.urbach_energy_eV
    prefactor_A = params.direct_prefactor_A

    base = 2.0 * direct_gap_eV + delta_eV

    discriminant_sqrt = math.sqrt(
        base * base
        + 8.0 * delta_eV * direct_gap_eV
    )

    connection_offset_eV = (
        2.0
        * delta_eV
        * direct_gap_eV
        / (discriminant_sqrt + base)
    )

    connection_energy_eV = (
        direct_gap_eV + connection_offset_eV
    )

    urbach_prefactor_m_inv = (
        prefactor_A
        * math.sqrt(connection_offset_eV)
        / connection_energy_eV
        * math.exp(
            -connection_offset_eV / delta_eV
        )
    )

    return NearEdgeConnection(
        direct_gap_eV=direct_gap_eV,
        connection_offset_eV=connection_offset_eV,
        connection_energy_eV=connection_energy_eV,
        urbach_prefactor_m_inv=urbach_prefactor_m_inv,
    )


def near_edge_direct_absorption_m_inv(
    photon_energy_eV: float,
    direct_gap_eV: float,
    parameters: GeSnNearEdgeParameterSet | None = None,
) -> float:
    """
    Evaluate the Tran Eq. (3) direct-absorption branch.

        alpha_D(E) =
            A * sqrt(E - Eg) / E

    The direct contribution is zero at and below the direct gap.
    """

    _validate_positive_finite(
        photon_energy_eV,
        "photon_energy_eV",
    )
    _validate_positive_finite(
        direct_gap_eV,
        "direct_gap_eV",
    )

    if photon_energy_eV <= direct_gap_eV:
        return 0.0

    params = parameters or TRAN_2016_NEAR_EDGE_PARAMETERS

    return (
        params.direct_prefactor_A
        * math.sqrt(photon_energy_eV - direct_gap_eV)
        / photon_energy_eV
    )


def near_edge_urbach_absorption_m_inv(
    photon_energy_eV: float,
    direct_gap_eV: float,
    parameters: GeSnNearEdgeParameterSet | None = None,
) -> float:
    """
    Evaluate the NCMemSim continuity-consistent Urbach branch.

        alpha_U(E) =
            alpha_0 * exp((E - Eg) / Delta_E)

    alpha_0 is not copied from the literal Tran Eq. (7). It is derived
    from the exact C1 connection to the Tran Eq. (3) direct branch.
    """

    _validate_positive_finite(
        photon_energy_eV,
        "photon_energy_eV",
    )
    _validate_positive_finite(
        direct_gap_eV,
        "direct_gap_eV",
    )

    params = parameters or TRAN_2016_NEAR_EDGE_PARAMETERS

    connection = derive_near_edge_connection(
        direct_gap_eV=direct_gap_eV,
        parameters=params,
    )

    return (
        connection.urbach_prefactor_m_inv
        * math.exp(
            (photon_energy_eV - direct_gap_eV)
            / params.urbach_energy_eV
        )
    )


class NearEdgeBranch(str, Enum):
    """
    Active branch of the piecewise near-edge reference model.
    """

    URBACH = "urbach"
    DIRECT = "direct"


@dataclass(frozen=True)
class NearEdgeOpticalPoint:
    """
    Result of one GeSn near-edge reference-model evaluation.

    The absorption coefficient is the value of exactly one active
    branch: direct or Urbach. No independent indirect-absorption
    contribution is included in this reference model.
    """

    wavelength_nm: float
    photon_energy_eV: float
    absorption_coefficient_m_inv: float

    direct_gap_eV: float
    connection_energy_eV: float

    branch: NearEdgeBranch
    domain_status: EvaluationDomainStatus

    provenance: Mapping[str, ParameterProvenance]


def _near_edge_parameter_provenance(
    parameters: GeSnNearEdgeParameterSet,
    key: str,
) -> ParameterProvenance:
    """
    Return explicit parameter provenance.

    Custom parameter sets without provenance remain usable, but their
    numerical values must not silently inherit the Tran literature
    classification.
    """

    if (
        parameters.provenance is not None
        and key in parameters.provenance
    ):
        return parameters.provenance[key]

    return ParameterProvenance(
        source=(
            "User-supplied GeSn near-edge parameter without "
            "explicit provenance"
        ),
        status=ParameterStatus.ASSUMED,
        notes=(
            "No explicit provenance was supplied with this custom "
            "near-edge parameter set."
        ),
        parameter_set=parameters.name,
    )


class GeSnNearEdgeReferenceModel:
    """
    Bulk-like, unstrained Ge/GeSn near-edge optical reference model.

    The model combines:

    - the existing NCMemSim direct-gap composition relation;
    - the Tran et al. direct-absorption functional form;
    - the Tran literature-fitted direct prefactor;
    - the Tran literature-fitted Urbach width;
    - the NCMemSim-derived exact C1 direct/Urbach connection.

    The result is piecewise:

        E < Ec:
            Urbach branch

        E >= Ec:
            direct branch

    No independent indirect-absorption term is included.

    The default validation domain is the near-edge domain audited from
    Tran et al. (2016). Evaluations outside that domain are permitted
    when physically valid but are marked as extrapolated.
    """

    def __init__(
        self,
        parameters: GeSnNearEdgeParameterSet | None = None,
        validation_domain: OpticalValidationDomain | None = None,
    ) -> None:
        self.parameters = (
            parameters or TRAN_2016_NEAR_EDGE_PARAMETERS
        )
        self.validation_domain = (
            validation_domain or TRAN_2016_NEAR_EDGE_DOMAIN
        )

    def evaluate(
        self,
        material: NanocrystalMaterial,
        wavelength_nm: float,
    ) -> NearEdgeOpticalPoint:
        domain_status = self.validation_domain.classify(
            sn_fraction=material.sn_fraction,
            wavelength_nm=wavelength_nm,
        )

        energy_eV = photon_energy_eV(wavelength_nm)

        direct_gap_eV = direct_gap_gesn_eV(
            material.sn_fraction,
        )

        connection = derive_near_edge_connection(
            direct_gap_eV=direct_gap_eV,
            parameters=self.parameters,
        )

        if energy_eV >= connection.connection_energy_eV:
            branch = NearEdgeBranch.DIRECT

            alpha_m_inv = near_edge_direct_absorption_m_inv(
                photon_energy_eV=energy_eV,
                direct_gap_eV=direct_gap_eV,
                parameters=self.parameters,
            )
        else:
            branch = NearEdgeBranch.URBACH

            alpha_m_inv = near_edge_urbach_absorption_m_inv(
                photon_energy_eV=energy_eV,
                direct_gap_eV=direct_gap_eV,
                parameters=self.parameters,
            )

        provenance = {
            "direct_gap": DIRECT_GAP_PROVENANCE,
            "direct_prefactor_A": _near_edge_parameter_provenance(
                self.parameters,
                "direct_prefactor_A",
            ),
            "urbach_energy_eV": _near_edge_parameter_provenance(
                self.parameters,
                "urbach_energy_eV",
            ),
            "continuity": ParameterProvenance(
                source=NEAR_EDGE_CONTINUITY_PROVENANCE.source,
                status=NEAR_EDGE_CONTINUITY_PROVENANCE.status,
                doi=NEAR_EDGE_CONTINUITY_PROVENANCE.doi,
                notes=NEAR_EDGE_CONTINUITY_PROVENANCE.notes,
                parameter_set=self.parameters.name,
            ),
        }

        return NearEdgeOpticalPoint(
            wavelength_nm=wavelength_nm,
            photon_energy_eV=energy_eV,
            absorption_coefficient_m_inv=alpha_m_inv,
            direct_gap_eV=direct_gap_eV,
            connection_energy_eV=(
                connection.connection_energy_eV
            ),
            branch=branch,
            domain_status=domain_status,
            provenance=provenance,
        )
