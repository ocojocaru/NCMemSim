from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np

from .hashing import canonical_hash


def _validate_optional_text(value: str | None, *, field_name: str) -> None:
    if value is not None and not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


def _readonly_float_array(values: np.ndarray, *, field_name: str) -> np.ndarray:
    array = np.array(values, dtype=float, copy=True)

    if array.ndim != 1:
        raise ValueError(f"{field_name} must be one-dimensional.")

    if not np.all(np.isfinite(array)):
        raise ValueError(f"{field_name} must contain only finite values.")

    array.setflags(write=False)
    return array


@dataclass(frozen=True)
class ExperimentalDatasetMetadata:
    """Metadata required to identify and reproduce an experimental dataset."""

    dataset_id: str
    source: str
    doi: str | None = None
    sample_id: str | None = None
    temperature_K: float | None = None
    temperature_description: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.dataset_id.strip():
            raise ValueError("dataset_id cannot be empty.")

        if not self.source.strip():
            raise ValueError("source cannot be empty.")

        _validate_optional_text(self.doi, field_name="doi")
        _validate_optional_text(self.sample_id, field_name="sample_id")
        _validate_optional_text(
            self.temperature_description,
            field_name="temperature_description",
        )
        _validate_optional_text(self.notes, field_name="notes")

        if self.temperature_K is not None:
            if (
                not math.isfinite(self.temperature_K)
                or self.temperature_K <= 0.0
            ):
                raise ValueError(
                    "temperature_K must be finite and positive."
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "source": self.source,
            "doi": self.doi,
            "sample_id": self.sample_id,
            "temperature_K": self.temperature_K,
            "temperature_description": self.temperature_description,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class OpticalAbsorptionDataset:
    """
    Normalized experimental optical-absorption dataset.

    Internal units are fixed to:

    - wavelength: nm;
    - absorption coefficient: m^-1;
    - absorption uncertainty: m^-1;
    - Sn fraction: dimensionless.

    The dataset stores one GeSn composition per instance. Input arrays are
    copied and made read-only so the normalized dataset cannot be mutated
    accidentally after construction.
    """

    wavelength_nm: np.ndarray
    absorption_coefficient_m_inv: np.ndarray
    sn_fraction: float
    metadata: ExperimentalDatasetMetadata
    absorption_uncertainty_m_inv: np.ndarray | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ExperimentalDatasetMetadata):
            raise TypeError(
                "metadata must be an ExperimentalDatasetMetadata instance."
            )

        if (
            not math.isfinite(self.sn_fraction)
            or not 0.0 <= self.sn_fraction <= 1.0
        ):
            raise ValueError(
                "sn_fraction must be finite and between 0 and 1."
            )

        wavelength_nm = _readonly_float_array(
            self.wavelength_nm,
            field_name="wavelength_nm",
        )
        absorption_coefficient_m_inv = _readonly_float_array(
            self.absorption_coefficient_m_inv,
            field_name="absorption_coefficient_m_inv",
        )

        if wavelength_nm.size < 2:
            raise ValueError(
                "An optical absorption dataset requires at least two points."
            )

        if wavelength_nm.shape != absorption_coefficient_m_inv.shape:
            raise ValueError(
                "wavelength_nm and absorption_coefficient_m_inv "
                "must have the same shape."
            )

        if np.any(wavelength_nm <= 0.0):
            raise ValueError(
                "wavelength_nm values must be strictly positive."
            )

        if np.any(absorption_coefficient_m_inv < 0.0):
            raise ValueError(
                "absorption_coefficient_m_inv values must be non-negative."
            )

        uncertainty: np.ndarray | None = None

        if self.absorption_uncertainty_m_inv is not None:
            uncertainty = _readonly_float_array(
                self.absorption_uncertainty_m_inv,
                field_name="absorption_uncertainty_m_inv",
            )

            if uncertainty.shape != wavelength_nm.shape:
                raise ValueError(
                    "absorption_uncertainty_m_inv must have the same shape "
                    "as wavelength_nm."
                )

            if np.any(uncertainty <= 0.0):
                raise ValueError(
                    "absorption_uncertainty_m_inv values must be "
                    "strictly positive."
                )

        object.__setattr__(self, "wavelength_nm", wavelength_nm)
        object.__setattr__(
            self,
            "absorption_coefficient_m_inv",
            absorption_coefficient_m_inv,
        )
        object.__setattr__(
            self,
            "absorption_uncertainty_m_inv",
            uncertainty,
        )

    @property
    def n_points(self) -> int:
        return int(self.wavelength_nm.size)

    @property
    def has_uncertainty(self) -> bool:
        return self.absorption_uncertainty_m_inv is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "dataset_type": "optical_absorption",
            "metadata": self.metadata.to_dict(),
            "sn_fraction": self.sn_fraction,
            "wavelength_nm": self.wavelength_nm.tolist(),
            "absorption_coefficient_m_inv": (
                self.absorption_coefficient_m_inv.tolist()
            ),
            "absorption_uncertainty_m_inv": (
                None
                if self.absorption_uncertainty_m_inv is None
                else self.absorption_uncertainty_m_inv.tolist()
            ),
        }

    def dataset_hash(self) -> str:
        """Return a deterministic SHA-256 hash of the normalized dataset."""

        return canonical_hash(self.to_dict())


__all__ = [
    "ExperimentalDatasetMetadata",
    "OpticalAbsorptionDataset",
]
