# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Opt-in, reference-anchored thermal contracts; no simulator integration or presets."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math

from ..constants import BOLTZMANN_J_K, ELEMENTARY_CHARGE_C
from .provenance import MaterialProperty, ParameterProvenance, ParameterStatus

__all__ = ["ThermalMaterial", "GapKind", "ThermalEvidence", "TemperatureDomain",
           "CarrierStatisticsDomain", "AnchoredVarshniProfile", "IntrinsicDensityProfile",
           "VarshniCoefficientRecord", "reviewed_varshni_coefficients", "profile_from_reviewed_record"]


class ThermalMaterial(str, Enum):
    SILICON = "Si"
    GERMANIUM = "Ge"
    GERMANIUM_TIN = "GeSn"


class GapKind(str, Enum):
    SUBSTRATE = "substrate_electronic_gap"
    GAMMA = "optical_gamma_gap"
    L = "optical_l_gap"


def _number(value, name, *, positive=False, nonnegative=False):
    if type(value) not in (int, float):
        raise ValueError(name + " must be a real number, not a boolean or string")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(name + " must be finite") from exc
    if not math.isfinite(result) or (positive and result <= 0) or (nonnegative and result < 0):
        raise ValueError(name + " must be finite and within its physical bounds")
    return result


def _text(value, name):
    if type(value) is not str or not value.strip():
        raise ValueError(name + " must be nonempty text")
    return value


def _keys(data, keys):
    if type(data) is not dict or set(data) != set(keys):
        raise ValueError("unsupported thermal archive fields")


def _enum(kind, value):
    if type(value) is not str:
        raise ValueError("thermal enum archive values must be strings")
    return kind(value)


def _normalize(owner, names, **bounds):
    for name in names:
        object.__setattr__(owner, name, _number(getattr(owner, name), name, **bounds))


def _canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate thermal JSON key: " + key)
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("nonfinite thermal JSON value: " + value)


class _Archive:
    @property
    def contract_hash(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict()).encode("utf-8")).hexdigest()

    def to_json(self) -> str:
        return _canonical(self.to_dict())

    @classmethod
    def from_json(cls, text: str):
        if type(text) is not str:
            raise ValueError("thermal archive must be JSON text")
        return cls.from_dict(json.loads(text, object_pairs_hook=_unique_object,
                                        parse_constant=_reject_constant))


@dataclass(frozen=True)
class ThermalEvidence(_Archive):
    source: str
    locator: str
    status: ParameterStatus
    notes: str
    doi: str | None = None

    def __post_init__(self):
        for name in ("source", "locator", "notes"):
            _text(getattr(self, name), name)
        if type(self.status) is not ParameterStatus or self.status not in {
            ParameterStatus.ASSUMED, ParameterStatus.DERIVED,
            ParameterStatus.LITERATURE, ParameterStatus.LITERATURE_FITTED,
        }:
            raise ValueError("unsupported thermal evidence status; calibration requires a separate contract")
        if self.doi is not None:
            _text(self.doi, "doi")

    def to_dict(self) -> dict:
        return {"source": self.source, "locator": self.locator, "status": self.status.value,
                "notes": self.notes, "doi": self.doi}

    @classmethod
    def from_dict(cls, data: dict) -> ThermalEvidence:
        _keys(data, ("source", "locator", "status", "notes", "doi"))
        return cls(data["source"], data["locator"], _enum(ParameterStatus, data["status"]),
                   data["notes"], data["doi"])


@dataclass(frozen=True)
class TemperatureDomain(_Archive):
    material: ThermalMaterial
    min_temperature_K: float
    max_temperature_K: float
    min_sn_fraction: float
    max_sn_fraction: float
    evidence: ThermalEvidence
    strain_state: str = "unstrained"

    def __post_init__(self):
        if type(self.material) is not ThermalMaterial or type(self.evidence) is not ThermalEvidence:
            raise ValueError("typed material and applicability evidence required")
        _normalize(self, ("min_temperature_K", "max_temperature_K"), positive=True)
        _normalize(self, ("min_sn_fraction", "max_sn_fraction"), nonnegative=True)
        if self.min_temperature_K > self.max_temperature_K:
            raise ValueError("inverted temperature domain")
        if not 0 <= self.min_sn_fraction <= self.max_sn_fraction <= 1:
            raise ValueError("invalid composition domain")
        if self.material is not ThermalMaterial.GERMANIUM_TIN and (self.min_sn_fraction != 0 or self.max_sn_fraction != 0):
            raise ValueError("Si and Ge domains require zero Sn fraction")
        if self.material is ThermalMaterial.GERMANIUM_TIN and self.min_sn_fraction <= 0:
            raise ValueError("GeSn requires an explicit positive Sn composition domain")
        if self.strain_state != "unstrained":
            raise ValueError("strain-dependent thermal profiles are outside Phase M")

    def check(self, temperature_K: float, sn_fraction: float) -> float:
        temperature = _number(temperature_K, "temperature_K", positive=True)
        composition = _number(sn_fraction, "sn_fraction", nonnegative=True)
        if not self.min_temperature_K <= temperature <= self.max_temperature_K:
            raise ValueError("temperature outside declared applicability domain")
        if not self.min_sn_fraction <= composition <= self.max_sn_fraction:
            raise ValueError("composition outside declared applicability domain")
        return temperature

    def to_dict(self) -> dict:
        return {"material": self.material.value, "min_temperature_K": self.min_temperature_K,
                "max_temperature_K": self.max_temperature_K, "min_sn_fraction": self.min_sn_fraction,
                "max_sn_fraction": self.max_sn_fraction, "strain_state": self.strain_state,
                "evidence": self.evidence.to_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> TemperatureDomain:
        _keys(data, ("material", "min_temperature_K", "max_temperature_K", "min_sn_fraction",
                     "max_sn_fraction", "strain_state", "evidence"))
        return cls(_enum(ThermalMaterial, data["material"]), data["min_temperature_K"],
                   data["max_temperature_K"], data["min_sn_fraction"], data["max_sn_fraction"],
                   ThermalEvidence.from_dict(data["evidence"]), data["strain_state"])


@dataclass(frozen=True)
class CarrierStatisticsDomain(_Archive):
    min_doping_m3: float
    max_doping_m3: float
    minimum_doping_to_intrinsic_ratio: float
    evidence: ThermalEvidence
    assumption: str = "constant_dos_mass_non_degenerate_fully_ionized"

    def __post_init__(self):
        _normalize(self, ("min_doping_m3", "max_doping_m3", "minimum_doping_to_intrinsic_ratio"), positive=True)
        if self.min_doping_m3 > self.max_doping_m3 or self.minimum_doping_to_intrinsic_ratio <= 1:
            raise ValueError("invalid carrier statistics domain")
        if type(self.evidence) is not ThermalEvidence:
            raise ValueError("carrier statistics evidence required")
        if self.assumption != "constant_dos_mass_non_degenerate_fully_ionized":
            raise ValueError("unsupported carrier statistics approximation")

    def check(self, doping_m3: float, intrinsic_density_m3: float) -> None:
        doping = _number(doping_m3, "substrate_doping_m3", positive=True)
        density = _number(intrinsic_density_m3, "intrinsic_density_m3", positive=True)
        if not self.min_doping_m3 <= doping <= self.max_doping_m3:
            raise ValueError("doping outside declared applicability domain")
        # Division preserves inclusive ratio boundaries; an infinite ratio passes.
        if doping / density < self.minimum_doping_to_intrinsic_ratio:
            raise ValueError("doping/intrinsic ratio violates declared extrinsic approximation")

    def to_dict(self) -> dict:
        return {"min_doping_m3": self.min_doping_m3, "max_doping_m3": self.max_doping_m3,
                "minimum_doping_to_intrinsic_ratio": self.minimum_doping_to_intrinsic_ratio,
                "assumption": self.assumption, "evidence": self.evidence.to_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> CarrierStatisticsDomain:
        _keys(data, ("min_doping_m3", "max_doping_m3", "minimum_doping_to_intrinsic_ratio", "assumption", "evidence"))
        return cls(data["min_doping_m3"], data["max_doping_m3"], data["minimum_doping_to_intrinsic_ratio"],
                   ThermalEvidence.from_dict(data["evidence"]), data["assumption"])


def _fraction(first, second):
    total = first + second
    if math.isfinite(total):
        return first / total
    ratio = first / second
    return ratio / (1.0 + ratio)


@dataclass(frozen=True)
class AnchoredVarshniProfile(_Archive):
    name: str
    gap_kind: GapKind
    domain: TemperatureDomain
    sn_fraction: float
    reference_temperature_K: float
    reference_gap_eV: float
    alpha_eV_K: float
    beta_K: float
    coefficient_evidence: ThermalEvidence
    reference_evidence: ThermalEvidence

    def __post_init__(self):
        _text(self.name, "name")
        if type(self.gap_kind) is not GapKind or type(self.domain) is not TemperatureDomain:
            raise ValueError("typed gap target and domain required")
        if any(type(e) is not ThermalEvidence for e in (self.coefficient_evidence, self.reference_evidence)):
            raise ValueError("typed coefficient/reference evidence required")
        _normalize(self, ("reference_temperature_K", "reference_gap_eV", "beta_K"), positive=True)
        _normalize(self, ("sn_fraction", "alpha_eV_K"), nonnegative=True)
        if (self.gap_kind is GapKind.SUBSTRATE) != (self.domain.material is ThermalMaterial.SILICON):
            raise ValueError("substrate gap belongs to Si; optical Gamma/L gaps belong to Ge/GeSn")
        self.domain.check(self.reference_temperature_K, self.sn_fraction)
        for temperature in (self.domain.min_temperature_K, self.domain.max_temperature_K):
            self.evaluate(temperature)

    def evaluate(self, temperature_K: float, *, sn_fraction: float | None = None) -> float:
        composition = self.sn_fraction if sn_fraction is None else _number(sn_fraction, "sn_fraction", nonnegative=True)
        temperature = self.domain.check(temperature_K, composition)
        if composition != self.sn_fraction:
            raise ValueError("gap anchor belongs to one declared composition; provide a separate profile")
        if temperature == self.reference_temperature_K:
            return self.reference_gap_eV
        # Algebraically factor f(T)-f(Tref) to avoid cancellation and T**2 overflow.
        delta = (temperature - self.reference_temperature_K) * (
            _fraction(temperature, self.beta_K)
            + _fraction(self.beta_K, temperature) * _fraction(self.reference_temperature_K, self.beta_K))
        value = self.reference_gap_eV - self.alpha_eV_K * delta
        return _number(value, "evaluated_gap_eV", positive=True)

    def evaluate_property(self, temperature_K: float, *, sn_fraction: float | None = None) -> MaterialProperty:
        value = self.evaluate(temperature_K, sn_fraction=sn_fraction)
        evidence = ParameterProvenance(source="Reference-anchored Varshni evaluation", status=ParameterStatus.DERIVED,
            parameter_set=self.name, doi=self.coefficient_evidence.doi,
            notes="Contract " + self.contract_hash + "; coefficient, anchor and applicability evidence remain separate.")
        return MaterialProperty(value, "eV", evidence, self.gap_kind.value)

    def to_dict(self) -> dict:
        return {"schema_version": "anchored-varshni-v1", "unit": "eV", "name": self.name,
                "gap_kind": self.gap_kind.value, "domain": self.domain.to_dict(), "sn_fraction": self.sn_fraction,
                "reference_temperature_K": self.reference_temperature_K, "reference_gap_eV": self.reference_gap_eV,
                "alpha_eV_K": self.alpha_eV_K, "beta_K": self.beta_K,
                "coefficient_evidence": self.coefficient_evidence.to_dict(), "reference_evidence": self.reference_evidence.to_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> AnchoredVarshniProfile:
        _keys(data, ("schema_version", "unit", "name", "gap_kind", "domain", "sn_fraction", "reference_temperature_K",
                     "reference_gap_eV", "alpha_eV_K", "beta_K", "coefficient_evidence", "reference_evidence"))
        if data["schema_version"] != "anchored-varshni-v1" or data["unit"] != "eV":
            raise ValueError("unsupported gap schema or unit")
        return cls(data["name"], _enum(GapKind, data["gap_kind"]), TemperatureDomain.from_dict(data["domain"]),
                   data["sn_fraction"], data["reference_temperature_K"], data["reference_gap_eV"], data["alpha_eV_K"],
                   data["beta_K"], ThermalEvidence.from_dict(data["coefficient_evidence"]), ThermalEvidence.from_dict(data["reference_evidence"]))


@dataclass(frozen=True)
class IntrinsicDensityProfile(_Archive):
    name: str
    gap_profile: AnchoredVarshniProfile
    reference_density_m3: float
    reference_evidence: ThermalEvidence
    statistics_domain: CarrierStatisticsDomain

    def __post_init__(self):
        _text(self.name, "name")
        _normalize(self, ("reference_density_m3",), positive=True)
        if type(self.gap_profile) is not AnchoredVarshniProfile or self.gap_profile.gap_kind is not GapKind.SUBSTRATE:
            raise ValueError("intrinsic density requires a Si substrate gap profile")
        if type(self.reference_evidence) is not ThermalEvidence or type(self.statistics_domain) is not CarrierStatisticsDomain:
            raise ValueError("typed density/statistics evidence required")
        # Validate the entire declared temperature/doping rectangle at its worst endpoints.
        for temperature in (self.gap_profile.domain.min_temperature_K, self.gap_profile.reference_temperature_K,
                            self.gap_profile.domain.max_temperature_K):
            self.evaluate(temperature, substrate_doping_m3=self.statistics_domain.min_doping_m3)

    def evaluate(self, temperature_K: float, *, substrate_doping_m3: float) -> float:
        gap = self.gap_profile.evaluate(temperature_K)
        temperature = _number(temperature_K, "temperature_K", positive=True)
        reference = self.gap_profile.reference_temperature_K
        if temperature == reference:
            density = self.reference_density_m3
        else:
            kb_eV_K = BOLTZMANN_J_K / ELEMENTARY_CHARGE_C
            log_density = (math.log(self.reference_density_m3) + 1.5 * (math.log(temperature) - math.log(reference))
                           - (gap / temperature - self.gap_profile.reference_gap_eV / reference) / (2.0 * kb_eV_K))
            try:
                density = math.exp(log_density)
            except OverflowError as exc:
                raise ValueError("intrinsic density overflow; no clipping is allowed") from exc
            density = _number(density, "evaluated_intrinsic_density_m3", positive=True)
        self.statistics_domain.check(substrate_doping_m3, density)
        return density

    def evaluate_property(self, temperature_K: float, *, substrate_doping_m3: float) -> MaterialProperty:
        value = self.evaluate(temperature_K, substrate_doping_m3=substrate_doping_m3)
        provenance = ParameterProvenance(source="Gap-coupled relative intrinsic-density approximation",
            status=ParameterStatus.DERIVED, parameter_set=self.name,
            notes="Contract " + self.contract_hash + "; inherited density anchor and declared carrier-statistics assumptions.")
        return MaterialProperty(value, "m^-3", provenance, "n_i")

    def to_dict(self) -> dict:
        return {"schema_version": "relative-intrinsic-density-v1", "unit": "m^-3", "name": self.name,
                "gap_profile": self.gap_profile.to_dict(), "reference_density_m3": self.reference_density_m3,
                "reference_evidence": self.reference_evidence.to_dict(), "statistics_domain": self.statistics_domain.to_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> IntrinsicDensityProfile:
        _keys(data, ("schema_version", "unit", "name", "gap_profile", "reference_density_m3", "reference_evidence", "statistics_domain"))
        if data["schema_version"] != "relative-intrinsic-density-v1" or data["unit"] != "m^-3":
            raise ValueError("unsupported density schema or unit")
        return cls(data["name"], AnchoredVarshniProfile.from_dict(data["gap_profile"]), data["reference_density_m3"],
                   ThermalEvidence.from_dict(data["reference_evidence"]), CarrierStatisticsDomain.from_dict(data["statistics_domain"]))


@dataclass(frozen=True)
class VarshniCoefficientRecord:
    name: str
    material: ThermalMaterial
    gap_kind: GapKind
    zero_temperature_gap_eV: float
    alpha_eV_K: float
    beta_K: float
    evidence: ThermalEvidence

    def __post_init__(self):
        _text(self.name, "name")
        _normalize(self, ("zero_temperature_gap_eV", "beta_K"), positive=True)
        _normalize(self, ("alpha_eV_K",), nonnegative=True)
        if type(self.material) is not ThermalMaterial or type(self.gap_kind) is not GapKind or type(self.evidence) is not ThermalEvidence:
            raise ValueError("typed coefficient record fields required")
        if self.material is ThermalMaterial.GERMANIUM_TIN or ((self.material is ThermalMaterial.SILICON) != (self.gap_kind is GapKind.SUBSTRATE)):
            raise ValueError("reviewed coefficient records are restricted to Si and bulk Ge")


def reviewed_varshni_coefficients() -> tuple[VarshniCoefficientRecord, ...]:
    """Transcribe Table I only; this function does not create material presets or certify ranges."""
    rows = (("varshni1967-si", ThermalMaterial.SILICON, GapKind.SUBSTRATE, 1.1557, 7.021e-4, 1108.0),
            ("varshni1967-ge-gamma", ThermalMaterial.GERMANIUM, GapKind.GAMMA, 0.8893, 6.042e-4, 398.0),
            ("varshni1967-ge-l", ThermalMaterial.GERMANIUM, GapKind.L, 0.7412, 4.561e-4, 210.0))
    evidence = ThermalEvidence("Y. P. Varshni, Physica 34 (1967), 149-154", "Table I, p. 152; equation (1), p. 149",
        ParameterStatus.LITERATURE_FITTED, "Table I fit; Si uses the exciton-subtracted gap convention. No operating domain is certified by this record.",
        "10.1016/0031-8914(67)90062-6")
    return tuple(VarshniCoefficientRecord(*row, evidence) for row in rows)


def profile_from_reviewed_record(record: VarshniCoefficientRecord, *, name: str, domain: TemperatureDomain,
                                reference_temperature_K: float, reference_gap_eV: float,
                                reference_evidence: ThermalEvidence) -> AnchoredVarshniProfile:
    """Apply reviewed coefficients to an explicitly inherited anchor and an ASSUMED operating domain."""
    if type(record) is not VarshniCoefficientRecord or record not in reviewed_varshni_coefficients():
        raise ValueError("coefficient record is not one of the reviewed Table I transcriptions")
    if type(domain) is not TemperatureDomain or domain.material is not record.material:
        raise ValueError("coefficient material and domain differ")
    if domain.evidence.status is not ParameterStatus.ASSUMED:
        raise ValueError("Table I coefficients do not certify a temperature range; declare the operating domain ASSUMED")
    return AnchoredVarshniProfile(name, record.gap_kind, domain, 0.0, reference_temperature_K,
                                 reference_gap_eV, record.alpha_eV_K, record.beta_K, record.evidence, reference_evidence)
