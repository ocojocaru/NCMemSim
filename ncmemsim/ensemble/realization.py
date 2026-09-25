"""Realization identity and sample-domain validation for Phase K."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from ..hashing import canonical_hash
from ._serialization import strict_fields
from .sampling import EnsembleSample, SamplingSpec
from .spec import PhysicalDomain


REALIZATION_ID_SCHEMA_VERSION = "ensemble-realization-id-v1"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256(value: str, label: str) -> str:
    if (
        not isinstance(value, str)
        or not _SHA256_RE.fullmatch(value)
    ):
        raise ValueError(
            f"{label} must be a lowercase SHA-256 hex digest"
        )

    return value


def _optional_sha256(
    value: str | None,
    label: str,
) -> str | None:
    if value is None:
        return None

    return _sha256(value, label)


class SampleDomainValidationError(ValueError):
    """One generated sample value lies outside its physical domain."""

    def __init__(
        self,
        *,
        sampling_spec_hash: str,
        sample_id: str,
        sample_index: int,
        variable_name: str,
        value: float,
        physical_domain: PhysicalDomain,
    ) -> None:
        self.sampling_spec_hash = sampling_spec_hash
        self.sample_id = sample_id
        self.sample_index = sample_index
        self.variable_name = variable_name
        self.value = value
        self.physical_domain = physical_domain

        super().__init__(
            "sample-domain validation failed for "
            f"sample {sample_index} ({sample_id}), "
            f"variable {variable_name!r}: "
            f"value {value!r} lies outside physical domain "
            f"{physical_domain.to_dict()!r}"
        )


def validate_sample_domain(
    sample: EnsembleSample,
    sampling_spec: SamplingSpec,
) -> None:
    """Validate one sample against all declared physical domains."""

    if not isinstance(sample, EnsembleSample):
        raise TypeError(
            "sample must be EnsembleSample"
        )

    if not isinstance(sampling_spec, SamplingSpec):
        raise TypeError(
            "sampling_spec must be SamplingSpec"
        )

    sample.require_matches_spec(
        sampling_spec
    )

    for variable, value in zip(
        sampling_spec.ensemble_spec.variables,
        sample.values,
        strict=True,
    ):
        if not variable.physical_domain.contains(
            value
        ):
            raise SampleDomainValidationError(
                sampling_spec_hash=(
                    sampling_spec.definition_hash
                ),
                sample_id=sample.sample_id,
                sample_index=sample.sample_index,
                variable_name=variable.name,
                value=value,
                physical_domain=(
                    variable.physical_domain
                ),
            )


@dataclass(frozen=True)
class RealizationIdentity:
    """Stable identity of one sample applied to its nominal context."""

    sampling_spec_hash: str
    ensemble_spec_hash: str
    sample_id: str
    sample_hash: str
    sample_index: int
    base_device_hash: str
    base_operating_hash: str | None
    schema_version: str = REALIZATION_ID_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _sha256(
            self.sampling_spec_hash,
            "sampling_spec_hash",
        )
        _sha256(
            self.ensemble_spec_hash,
            "ensemble_spec_hash",
        )
        _sha256(
            self.sample_id,
            "sample_id",
        )
        _sha256(
            self.sample_hash,
            "sample_hash",
        )
        _sha256(
            self.base_device_hash,
            "base_device_hash",
        )
        _optional_sha256(
            self.base_operating_hash,
            "base_operating_hash",
        )

        if (
            isinstance(self.sample_index, bool)
            or not isinstance(
                self.sample_index,
                int,
            )
            or self.sample_index < 0
        ):
            raise ValueError(
                "sample_index must be a nonnegative integer"
            )

        if (
            self.schema_version
            != REALIZATION_ID_SCHEMA_VERSION
        ):
            raise ValueError(
                "unsupported realization identity schema_version"
            )

    @classmethod
    def from_sample(
        cls,
        sampling_spec: SamplingSpec,
        sample: EnsembleSample,
    ) -> "RealizationIdentity":
        if not isinstance(
            sampling_spec,
            SamplingSpec,
        ):
            raise TypeError(
                "sampling_spec must be SamplingSpec"
            )

        if not isinstance(
            sample,
            EnsembleSample,
        ):
            raise TypeError(
                "sample must be EnsembleSample"
            )

        sample.require_matches_spec(
            sampling_spec
        )

        ensemble_spec = (
            sampling_spec.ensemble_spec
        )

        return cls(
            sampling_spec_hash=(
                sampling_spec.definition_hash
            ),
            ensemble_spec_hash=(
                ensemble_spec.definition_hash
            ),
            sample_id=sample.sample_id,
            sample_hash=sample.sample_hash,
            sample_index=sample.sample_index,
            base_device_hash=(
                ensemble_spec.base_device_hash
            ),
            base_operating_hash=(
                ensemble_spec.base_operating_hash
            ),
        )

    def _identity_payload(
        self,
    ) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "sampling_spec_hash": (
                self.sampling_spec_hash
            ),
            "ensemble_spec_hash": (
                self.ensemble_spec_hash
            ),
            "sample_id": self.sample_id,
            "sample_hash": self.sample_hash,
            "sample_index": self.sample_index,
            "base_device_hash": (
                self.base_device_hash
            ),
            "base_operating_hash": (
                self.base_operating_hash
            ),
        }

    @property
    def realization_id(self) -> str:
        return canonical_hash(
            self._identity_payload()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._identity_payload(),
            "realization_id": self.realization_id,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "RealizationIdentity":
        strict_fields(
            data,
            label="realization-identity",
            required={
                "schema_version",
                "sampling_spec_hash",
                "ensemble_spec_hash",
                "sample_id",
                "sample_hash",
                "sample_index",
                "base_device_hash",
                "base_operating_hash",
                "realization_id",
            },
        )

        identity = cls(
            sampling_spec_hash=(
                data["sampling_spec_hash"]
            ),
            ensemble_spec_hash=(
                data["ensemble_spec_hash"]
            ),
            sample_id=data["sample_id"],
            sample_hash=data["sample_hash"],
            sample_index=data["sample_index"],
            base_device_hash=(
                data["base_device_hash"]
            ),
            base_operating_hash=(
                data["base_operating_hash"]
            ),
            schema_version=(
                data["schema_version"]
            ),
        )

        if (
            data["realization_id"]
            != identity.realization_id
        ):
            raise ValueError(
                "realization_id integrity mismatch"
            )

        return identity


__all__ = [
    "REALIZATION_ID_SCHEMA_VERSION",
    "RealizationIdentity",
    "SampleDomainValidationError",
    "validate_sample_domain",
]
