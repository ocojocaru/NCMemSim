# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Inert Phase L1 MODEL contracts, separate from Phase K v1 archives.

No sampler, realization or transport execution is introduced here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..device import Device
from ..dtco.spec import (
    BindingScope, ParameterBinding, _device_definition_payload,
    _operating_definition_payload,
)
from ..hashing import canonical_hash
from ..materials.provenance import ParameterProvenance, ParameterStatus
from ..transport.barrier_corrections import ImageForceBarrierSpec
from ..transport.integration import AdvancedTransportSpec, TATLinkAttachment
from ..transport.traps import TrapAssistedTransportSpec, TrapParameterStatus
from ._serialization import (
    parameter_binding_from_dict, parameter_provenance_from_dict, strict_fields,
)
from .distributions import distribution_from_dict
from .spec import PhysicalDomain, StochasticVariable, _DISTRIBUTION_TYPES, _number, _text


def trap_density_binding(link_id: str, species_name: str) -> ParameterBinding:
    """Address density by exact attachment link and species names, never index."""
    _text(link_id, "link_id")
    _text(species_name, "species_name")
    return ParameterBinding(
        BindingScope.MODEL,
        ("advanced_transport", "attachments", link_id, "species", species_name, "density_m3"),
    )


def _density_target(binding: ParameterBinding) -> tuple[str, str]:
    if not isinstance(binding, ParameterBinding):
        raise TypeError("binding must be ParameterBinding")
    path = binding.path
    if (binding.scope is not BindingScope.MODEL or len(path) != 6
            or path[:2] != ("advanced_transport", "attachments")
            or path[3] != "species" or path[5] != "density_m3"):
        raise ValueError("L1 supports only explicit advanced-transport trap-density bindings")
    return path[2], path[4]


def _schema(data: dict[str, Any], fields: set[str], version: str) -> None:
    strict_fields(data, label=version, required=fields | {"schema_version"})
    if type(data["schema_version"]) is not str or data["schema_version"] != version:
        raise ValueError("unsupported MODEL contract schema_version")


def _advanced_from_dict(data: dict[str, Any]) -> AdvancedTransportSpec:
    strict_fields(data, label="advanced-transport", required={"schema_version", "attachments"})
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("unsupported advanced-transport schema")
    if type(data["attachments"]) is not list:
        raise TypeError("attachments must be a list")
    attachments = []
    for item in data["attachments"]:
        strict_fields(item, label="TAT attachment", required={"link_id", "specification", "barrier_correction"})
        spec = item["specification"]
        strict_fields(spec, label="TAT specification", required={"schema_version", "enabled", "model", "species"})
        if type(spec["schema_version"]) is not int or spec["schema_version"] != 1:
            raise ValueError("unsupported TAT specification schema")
        if type(spec["species"]) is not list:
            raise TypeError("species must be a list")
        for species in spec["species"]:
            if type(species) is not dict or type(species.get("schema_version")) is not int:
                raise ValueError("unsupported trap-species schema")
        correction = item["barrier_correction"]
        strict_fields(correction, label="image-force correction", required={
            "schema_version", "enabled", "relative_permittivity", "parameter_status", "source", "applicability",
        })
        if type(correction["schema_version"]) is not int or correction["schema_version"] != 1:
            raise ValueError("unsupported image-force schema")
        attachments.append(TATLinkAttachment(
            link_id=item["link_id"],
            specification=TrapAssistedTransportSpec.from_dict(spec),
            barrier_correction=ImageForceBarrierSpec(
                enabled=correction["enabled"],
                relative_permittivity=correction["relative_permittivity"],
                parameter_status=TrapParameterStatus(correction["parameter_status"]),
                source=correction["source"], applicability=correction["applicability"],
            ),
        ))
    return AdvancedTransportSpec(tuple(attachments))


@dataclass(frozen=True)
class TransportModelContext:
    """Owned advanced-transport configuration, not a complete PhysicsModel.

    Full device/protocol identity belongs to ModelVariabilitySpec. Engine knobs
    and broader physics inputs must be recorded by the L2 workflow context.
    Attachment and species declaration order remains identity-significant.
    """

    advanced_transport: AdvancedTransportSpec

    def __post_init__(self) -> None:
        if not isinstance(self.advanced_transport, AdvancedTransportSpec):
            raise TypeError("advanced_transport must be AdvancedTransportSpec")

    def resolve_density(self, binding: ParameterBinding) -> float:
        link_id, species_name = _density_target(binding)
        attachment = next((a for a in self.advanced_transport.attachments if a.link_id == link_id), None)
        if attachment is None:
            raise ValueError(f"unknown MODEL attachment link: {link_id!r}")
        species = next((s for s in attachment.specification.species if s.name == species_name), None)
        if species is None:
            raise ValueError(f"unknown MODEL trap species: {species_name!r}")
        return species.density_m3

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": "transport-model-context-v1",
                "advanced_transport": self.advanced_transport.to_dict()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TransportModelContext:
        _schema(data, {"advanced_transport"}, "transport-model-context-v1")
        return cls(_advanced_from_dict(data["advanced_transport"]))

    @property
    def context_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class TrapDensityVariable:
    """Density-only MODEL variable; distribution provenance is explicit."""

    name: str
    binding: ParameterBinding
    distribution: Any
    physical_domain: PhysicalDomain
    provenance: ParameterProvenance
    applicability: str
    nominal_value: float | None = None
    unit: str = "m^-3"

    def __post_init__(self) -> None:
        _text(self.name, "name")
        _text(self.applicability, "applicability")
        _density_target(self.binding)
        if not isinstance(self.distribution, _DISTRIBUTION_TYPES):
            raise TypeError("distribution must be a supported Phase K distribution")
        if not isinstance(self.physical_domain, PhysicalDomain):
            raise TypeError("physical_domain must be PhysicalDomain")
        if self.physical_domain.lower is None or self.physical_domain.lower < 0:
            raise ValueError("density domain requires an explicit nonnegative lower bound")
        if self.unit != "m^-3":
            raise ValueError("density canonical unit must be m^-3")
        if not isinstance(self.provenance, ParameterProvenance):
            raise TypeError("provenance must be ParameterProvenance")
        if not isinstance(self.provenance.status, ParameterStatus):
            raise TypeError("provenance status must be ParameterStatus")
        _text(self.provenance.source, "provenance.source")
        if self.nominal_value is not None:
            value = _number(self.nominal_value, "nominal_value")
            if not self.physical_domain.contains(value):
                raise ValueError("nominal_value must lie inside density physical_domain")
            object.__setattr__(self, "nominal_value", value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": "trap-density-variable-v1", "name": self.name,
                "binding": self.binding.to_dict(), "distribution": self.distribution.to_dict(),
                "physical_domain": self.physical_domain.to_dict(), "provenance": self.provenance.to_dict(),
                "applicability": self.applicability, "nominal_value": self.nominal_value, "unit": self.unit}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrapDensityVariable:
        _schema(data, {"name", "binding", "distribution", "physical_domain", "provenance",
                       "applicability", "nominal_value", "unit"}, "trap-density-variable-v1")
        return cls(name=data["name"], binding=parameter_binding_from_dict(data["binding"]),
                   distribution=distribution_from_dict(data["distribution"]),
                   physical_domain=PhysicalDomain.from_dict(data["physical_domain"]),
                   provenance=parameter_provenance_from_dict(data["provenance"]),
                   applicability=data["applicability"], nominal_value=data["nominal_value"], unit=data["unit"])

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class ModelVariabilitySpec:
    """New inert identity envelope; Phase K sampling/execution does not accept it."""

    name: str
    base_device_hash: str
    model_context: TransportModelContext
    variables: tuple[TrapDensityVariable | StochasticVariable, ...]
    base_operating_hash: str | None = None
    base_operating_kind: str | None = None

    def __post_init__(self) -> None:
        from .specification import _SHA256_RE
        _text(self.name, "name")
        if not isinstance(self.base_device_hash, str) or not _SHA256_RE.fullmatch(self.base_device_hash):
            raise ValueError("base_device_hash must be a lowercase SHA-256 digest")
        if not isinstance(self.model_context, TransportModelContext):
            raise TypeError("model_context must be TransportModelContext")
        object.__setattr__(self, "variables", tuple(self.variables))
        if not self.variables or not any(isinstance(v, TrapDensityVariable) for v in self.variables):
            raise ValueError("MODEL studies require at least one TrapDensityVariable")
        if any(not isinstance(v, (TrapDensityVariable, StochasticVariable)) for v in self.variables):
            raise TypeError("unsupported MODEL study variable")
        names = [v.name for v in self.variables]
        bindings = [v.binding.binding_id for v in self.variables]
        if len(names) != len(set(names)) or len(bindings) != len(set(bindings)):
            raise ValueError("variable names and binding targets must be unique")
        if (self.base_operating_hash is None) != (self.base_operating_kind is None):
            raise ValueError("operating hash and kind must be supplied together")
        if self.base_operating_hash is not None:
            if not isinstance(self.base_operating_hash, str) or not _SHA256_RE.fullmatch(self.base_operating_hash):
                raise ValueError("base_operating_hash must be a lowercase SHA-256 digest")
            if self.base_operating_kind not in {"program_pulse_read", "electro_optical_program_pulse_read"}:
                raise ValueError("unsupported operating kind")
        for variable in self.variables:
            if isinstance(variable, TrapDensityVariable):
                nominal = self.model_context.resolve_density(variable.binding)
                if not variable.physical_domain.contains(nominal):
                    raise ValueError("nominal model density lies outside variable domain")
                if variable.nominal_value is not None and variable.nominal_value != nominal:
                    raise ValueError("declared nominal density differs from model context")
            elif variable.binding.scope is BindingScope.OPERATING and self.base_operating_hash is None:
                raise ValueError("operating variables require an operating baseline identity")

    @classmethod
    def from_device(cls, *, name: str, device: Device, model_context: TransportModelContext,
                    variables: tuple[TrapDensityVariable | StochasticVariable, ...],
                    operating_protocol: Any | None = None) -> ModelVariabilitySpec:
        device.validate()
        payload = None if operating_protocol is None else _operating_definition_payload(operating_protocol)
        return cls(name, canonical_hash(_device_definition_payload(device)), model_context, variables,
                   None if payload is None else canonical_hash(payload),
                   None if payload is None else payload["kind"])

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": "model-variability-spec-v1", "name": self.name,
                "base_device_hash": self.base_device_hash, "model_context": self.model_context.to_dict(),
                "variables": [v.to_dict() for v in self.variables],
                "base_operating_hash": self.base_operating_hash, "base_operating_kind": self.base_operating_kind}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelVariabilitySpec:
        _schema(data, {"name", "base_device_hash", "model_context", "variables",
                       "base_operating_hash", "base_operating_kind"}, "model-variability-spec-v1")
        if type(data["variables"]) is not list:
            raise TypeError("variables must be a list")
        variables = []
        for item in data["variables"]:
            if type(item) is not dict:
                raise TypeError("variable must be a dict")
            reader = TrapDensityVariable if item.get("schema_version") == "trap-density-variable-v1" else StochasticVariable
            variables.append(reader.from_dict(item))
        return cls(data["name"], data["base_device_hash"],
                   TransportModelContext.from_dict(data["model_context"]), tuple(variables),
                   data["base_operating_hash"], data["base_operating_kind"])

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


__all__ = ["trap_density_binding", "TransportModelContext", "TrapDensityVariable", "ModelVariabilitySpec"]
