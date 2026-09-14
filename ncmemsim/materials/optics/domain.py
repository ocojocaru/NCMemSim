from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import math
from typing import Any


class EvaluationDomainStatus(str, Enum):
    """
    Status of a model evaluation relative to its validation domain.

    This status describes where an evaluation is performed. It is
    deliberately separate from ParameterStatus, which describes the
    provenance or scientific status of model parameters.
    """

    WITHIN_VALIDATION_DOMAIN = "within_validation_domain"
    EXTRAPOLATED = "extrapolated"


@dataclass(frozen=True)
class OpticalValidationDomain:
    """
    Experimental or literature validation domain for an optical model.

    The domain records composition and wavelength bounds supported by
    the associated validation source.

    Temperature is currently retained as descriptive metadata rather
    than as a numerical classification interval because the Tran et al.
    dataset is reported at room temperature without establishing a
    calibrated temperature range.
    """

    name: str

    sn_fraction_min: float
    sn_fraction_max: float

    wavelength_min_nm: float
    wavelength_max_nm: float

    temperature_note: str | None = None
    doi: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Domain name cannot be empty.")

        composition_values = (
            self.sn_fraction_min,
            self.sn_fraction_max,
        )

        if not all(math.isfinite(value) for value in composition_values):
            raise ValueError(
                "Sn-fraction domain bounds must be finite."
            )

        if not (
            0.0 <= self.sn_fraction_min <= 1.0
            and 0.0 <= self.sn_fraction_max <= 1.0
        ):
            raise ValueError(
                "Sn-fraction domain bounds must lie between 0 and 1."
            )

        if self.sn_fraction_min > self.sn_fraction_max:
            raise ValueError(
                "sn_fraction_min cannot exceed sn_fraction_max."
            )

        wavelength_values = (
            self.wavelength_min_nm,
            self.wavelength_max_nm,
        )

        if not all(math.isfinite(value) for value in wavelength_values):
            raise ValueError(
                "Wavelength domain bounds must be finite."
            )

        if self.wavelength_min_nm <= 0:
            raise ValueError(
                "wavelength_min_nm must be positive."
            )

        if self.wavelength_max_nm <= 0:
            raise ValueError(
                "wavelength_max_nm must be positive."
            )

        if self.wavelength_min_nm > self.wavelength_max_nm:
            raise ValueError(
                "wavelength_min_nm cannot exceed wavelength_max_nm."
            )

        if (
            self.temperature_note is not None
            and not self.temperature_note.strip()
        ):
            raise ValueError(
                "temperature_note cannot be empty when provided."
            )

        if self.doi is not None and not self.doi.strip():
            raise ValueError(
                "doi cannot be empty when provided."
            )

    def classify(
        self,
        *,
        sn_fraction: float,
        wavelength_nm: float,
    ) -> EvaluationDomainStatus:
        """
        Classify an optical evaluation relative to this domain.

        Physically invalid inputs raise ValueError. Valid physical
        inputs outside the validation bounds are classified as
        extrapolated.
        """

        self._validate_evaluation_inputs(
            sn_fraction=sn_fraction,
            wavelength_nm=wavelength_nm,
        )

        within_composition = (
            self.sn_fraction_min
            <= sn_fraction
            <= self.sn_fraction_max
        )

        within_wavelength = (
            self.wavelength_min_nm
            <= wavelength_nm
            <= self.wavelength_max_nm
        )

        if within_composition and within_wavelength:
            return EvaluationDomainStatus.WITHIN_VALIDATION_DOMAIN

        return EvaluationDomainStatus.EXTRAPOLATED

    def contains(
        self,
        *,
        sn_fraction: float,
        wavelength_nm: float,
    ) -> bool:
        """
        Return True when an evaluation lies inside the validation domain.
        """

        return (
            self.classify(
                sn_fraction=sn_fraction,
                wavelength_nm=wavelength_nm,
            )
            is EvaluationDomainStatus.WITHIN_VALIDATION_DOMAIN
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def _validate_evaluation_inputs(
        *,
        sn_fraction: float,
        wavelength_nm: float,
    ) -> None:
        if not math.isfinite(sn_fraction):
            raise ValueError("sn_fraction must be finite.")

        if not 0.0 <= sn_fraction <= 1.0:
            raise ValueError(
                "sn_fraction must lie between 0 and 1."
            )

        if not math.isfinite(wavelength_nm):
            raise ValueError("wavelength_nm must be finite.")

        if wavelength_nm <= 0:
            raise ValueError("wavelength_nm must be positive.")


TRAN_2016_NEAR_EDGE_DOMAIN = OpticalValidationDomain(
    name="tran-2016-near-edge",
    sn_fraction_min=0.0,
    sn_fraction_max=0.10,
    wavelength_min_nm=1500.0,
    wavelength_max_nm=2500.0,
    temperature_note="room temperature",
    doi="10.1063/1.4943652",
)
