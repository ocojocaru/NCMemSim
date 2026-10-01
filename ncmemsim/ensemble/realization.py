# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Realization identity and sample-domain validation for Phase K."""

from __future__ import annotations

from dataclasses import dataclass
import re
import math
from typing import Any

from ..hashing import canonical_hash
from ._serialization import strict_fields
from .sampling import EnsembleSample, SamplingSpec
from .spec import PhysicalDomain
from ..device import Device
from ..dtco.binding import apply_device_bindings
from ..dtco.operating import (
    OperatingProtocol,
    apply_operating_bindings,
)
from ..dtco.spec import (
    BindingScope,
    ParameterBinding,
    _device_definition_payload,
    _operating_definition_payload,
)


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


@dataclass(frozen=True)
class RealizationAssignment:
    """One ordered stochastic binding applied in a realization."""

    variable_name: str
    binding: ParameterBinding
    unit: str
    value: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.variable_name, str)
            or not self.variable_name
            or self.variable_name
            != self.variable_name.strip()
        ):
            raise ValueError(
                "variable_name must be nonempty normalized text"
            )

        if not isinstance(
            self.binding,
            ParameterBinding,
        ):
            raise TypeError(
                "binding must be ParameterBinding"
            )

        if (
            not isinstance(self.unit, str)
            or not self.unit
            or self.unit != self.unit.strip()
        ):
            raise ValueError(
                "unit must be nonempty normalized text"
            )

        if (
            type(self.value) is not float
            or not math.isfinite(self.value)
        ):
            raise ValueError(
                "realization assignment value must be "
                "a finite Python float"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable_name": self.variable_name,
            "binding": self.binding.to_dict(),
            "binding_id": self.binding.binding_id,
            "unit": self.unit,
            "value": self.value,
        }


@dataclass(frozen=True)
class AppliedRealization:
    """One sample applied to its validated nominal context."""

    identity: RealizationIdentity
    device: Device
    operating_protocol: OperatingProtocol | None
    assignments: tuple[RealizationAssignment, ...]
    realized_device_hash: str
    realized_operating_hash: str | None

    def __post_init__(self) -> None:
        if not isinstance(
            self.identity,
            RealizationIdentity,
        ):
            raise TypeError(
                "identity must be RealizationIdentity"
            )

        if not isinstance(
            self.device,
            Device,
        ):
            raise TypeError(
                "device must be Device"
            )

        assignments = tuple(
            self.assignments
        )

        for assignment in assignments:
            if not isinstance(
                assignment,
                RealizationAssignment,
            ):
                raise TypeError(
                    "assignments must contain "
                    "RealizationAssignment instances"
                )

        if not assignments:
            raise ValueError(
                "applied realization requires assignments"
            )

        _sha256(
            self.realized_device_hash,
            "realized_device_hash",
        )

        _optional_sha256(
            self.realized_operating_hash,
            "realized_operating_hash",
        )

        if (
            self.operating_protocol is None
        ) != (
            self.realized_operating_hash is None
        ):
            raise ValueError(
                "operating protocol and realized operating "
                "hash must be supplied together"
            )

        if (
            self.identity.base_operating_hash is None
        ) != (
            self.operating_protocol is None
        ):
            raise ValueError(
                "realized operating context does not match "
                "realization identity"
            )

        object.__setattr__(
            self,
            "assignments",
            assignments,
        )

    def require_integrity(self) -> None:
        """Verify that realized runtime objects still match their hashes."""

        device_hash = canonical_hash(
            _device_definition_payload(
                self.device
            )
        )

        if (
            device_hash
            != self.realized_device_hash
        ):
            raise ValueError(
                "realized device hash integrity mismatch"
            )

        if self.operating_protocol is None:
            if self.realized_operating_hash is not None:
                raise ValueError(
                    "unexpected realized operating hash"
                )

            return

        operating_hash = canonical_hash(
            _operating_definition_payload(
                self.operating_protocol
            )
        )

        if (
            operating_hash
            != self.realized_operating_hash
        ):
            raise ValueError(
                "realized operating hash integrity mismatch"
            )


def apply_sample_to_context(
    sampling_spec: SamplingSpec,
    sample: EnsembleSample,
    base_device: Device,
    base_operating_protocol: OperatingProtocol | None = None,
) -> AppliedRealization:
    """Apply one validated ensemble sample to its nominal context."""

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

    if not isinstance(
        base_device,
        Device,
    ):
        raise TypeError(
            "base_device must be Device"
        )

    identity = RealizationIdentity.from_sample(
        sampling_spec,
        sample,
    )

    validate_sample_domain(
        sample,
        sampling_spec,
    )

    ensemble_spec = (
        sampling_spec.ensemble_spec
    )

    ensemble_spec.require_matching_device(
        base_device
    )

    if (
        ensemble_spec.base_operating_hash
        is None
    ):
        if base_operating_protocol is not None:
            raise ValueError(
                "ensemble specification has no "
                "operating baseline identity"
            )

    else:
        if base_operating_protocol is None:
            raise ValueError(
                "base_operating_protocol is required "
                "by ensemble specification"
            )

        ensemble_spec.require_matching_operating(
            base_operating_protocol
        )

    assignments: list[
        RealizationAssignment
    ] = []

    device_assignments = []
    operating_assignments = []

    for variable, value in zip(
        ensemble_spec.variables,
        sample.values,
        strict=True,
    ):
        assignment = RealizationAssignment(
            variable_name=variable.name,
            binding=variable.binding,
            unit=variable.unit,
            value=value,
        )

        assignments.append(
            assignment
        )

        if (
            variable.binding.scope
            is BindingScope.DEVICE
        ):
            device_assignments.append(
                (
                    variable.binding,
                    value,
                )
            )

        elif (
            variable.binding.scope
            is BindingScope.OPERATING
        ):
            operating_assignments.append(
                (
                    variable.binding,
                    value,
                )
            )

        else:
            raise ValueError(
                "unsupported realization binding scope"
            )

    realized_device = apply_device_bindings(
        base_device,
        tuple(device_assignments),
    )

    if base_operating_protocol is None:
        realized_operating = None

    else:
        realized_operating = (
            apply_operating_bindings(
                base_operating_protocol,
                tuple(
                    operating_assignments
                ),
            )
        )

    realized_device_hash = canonical_hash(
        _device_definition_payload(
            realized_device
        )
    )

    realized_operating_hash = None

    if realized_operating is not None:
        realized_operating_hash = canonical_hash(
            _operating_definition_payload(
                realized_operating
            )
        )

    result = AppliedRealization(
        identity=identity,
        device=realized_device,
        operating_protocol=(
            realized_operating
        ),
        assignments=tuple(
            assignments
        ),
        realized_device_hash=(
            realized_device_hash
        ),
        realized_operating_hash=(
            realized_operating_hash
        ),
    )

    result.require_integrity()

    return result


__all__ = [
    "REALIZATION_ID_SCHEMA_VERSION",
    "RealizationIdentity",
    "SampleDomainValidationError",
    "validate_sample_domain",
    "AppliedRealization",
    "RealizationAssignment",
    "apply_sample_to_context",
]
