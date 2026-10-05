# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Opt-in spectral source contracts; no absorption or simulator integration."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math

from .constants import LIGHT_SPEED_M_S, PLANCK_J_S

__all__ = ["SpectralEvidence", "TabulatedSpectrum", "DiscreteLineSpectrum"]


def _number(value, name, *, positive=False):
    if type(value) not in (int, float):
        raise ValueError(name + " must be a real number")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(name + " must be finite") from exc
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError(name + " is outside its finite physical bounds")
    return value


def _text(value, name):
    if type(value) is not str or not value.strip():
        raise ValueError(name + " must be nonempty text")


def _keys(data, required):
    if type(data) is not dict or set(data) != set(required):
        raise ValueError("unsupported spectral archive fields")


def _unique(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError("duplicate spectral JSON key")
        data[key] = value
    return data


def _constant(value):
    raise ValueError("nonfinite spectral JSON value: " + value)


def _canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)


class _Archive:
    def to_json(self):
        return _canonical(self.to_dict())

    @property
    def contract_hash(self):
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_json(cls, text):
        if type(text) is not str:
            raise ValueError("spectral archive must be JSON text")
        return cls.from_dict(json.loads(text, object_pairs_hook=_unique, parse_constant=_constant))


@dataclass(frozen=True)
class SpectralEvidence(_Archive):
    """Input provenance; measured source status does not qualify a device model."""
    source: str
    locator: str
    status: str
    original_units: str
    transformations: tuple[str, ...]
    resolution: str
    uncertainty: str
    notes: str
    source_sha256: str | None = None

    def __post_init__(self):
        for name in ("source", "locator", "original_units", "resolution", "uncertainty", "notes"):
            _text(getattr(self, name), name)
        if type(self.status) is not str or self.status not in {"ASSUMED", "MEASURED", "DERIVED", "LITERATURE"}:
            raise ValueError("unsupported spectral provenance status")
        if type(self.transformations) is not tuple:
            raise ValueError("transformations must be an immutable tuple")
        for item in self.transformations:
            _text(item, "transformation")
        if self.source_sha256 is not None:
            if type(self.source_sha256) is not str or len(self.source_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.source_sha256):
                raise ValueError("source_sha256 must be a lowercase SHA-256 digest")

    def to_dict(self):
        return {"schema_version": "spectral-evidence-v1", "source": self.source,
                "locator": self.locator, "status": self.status, "original_units": self.original_units,
                "transformations": list(self.transformations), "resolution": self.resolution,
                "uncertainty": self.uncertainty, "notes": self.notes, "source_sha256": self.source_sha256}

    @classmethod
    def from_dict(cls, data):
        _keys(data, ("schema_version", "source", "locator", "status", "original_units", "transformations", "resolution", "uncertainty", "notes", "source_sha256"))
        if data["schema_version"] != "spectral-evidence-v1" or type(data["transformations"]) is not list:
            raise ValueError("unsupported spectral evidence schema")
        return cls(**{k: tuple(v) if k == "transformations" else v for k, v in data.items() if k != "schema_version"})


def _arrays(owner, value_name, minimum):
    wavelengths = owner.wavelength_nm
    values = getattr(owner, value_name)
    if type(wavelengths) is not tuple or type(values) is not tuple or len(wavelengths) != len(values) or len(values) < minimum:
        raise ValueError("spectral arrays require matching immutable tuples of sufficient length")
    wavelengths = tuple(_number(x, "wavelength_nm", positive=True) for x in wavelengths)
    values = tuple(_number(x, value_name) for x in values)
    if any(b <= a for a, b in zip(wavelengths, wavelengths[1:])):
        raise ValueError("wavelengths must be strictly increasing; no sorting or merging")
    object.__setattr__(owner, "wavelength_nm", wavelengths)
    object.__setattr__(owner, value_name, values)
    if type(owner.evidence) is not SpectralEvidence or type(owner.enabled) is not bool:
        raise ValueError("typed evidence and boolean enabled flag required")


def _sum(values):
    try:
        result = math.fsum(values)
    except (OverflowError, ValueError) as exc:
        raise ValueError("spectral integral is not representable") from exc
    if not math.isfinite(result):
        raise ValueError("spectral integral is not finite")
    return result


def _trapezoid(wavelengths, values):
    # Half each endpoint before adding to avoid unnecessary overflow.
    return _sum((b-a)*(x/2+y/2) for a,b,x,y in zip(wavelengths, wavelengths[1:], values, values[1:]))


@dataclass(frozen=True)
class TabulatedSpectrum(_Archive):
    """Piecewise-linear wavelength density or explicitly normalized relative shape.

    Absolute values are W m^-2 nm^-1. Relative values are dimensionless;
    normalization preserves the original shape and records the target power.
    Photon integration is exact for each linear-density segment.
    """
    wavelength_nm: tuple[float, ...]
    values: tuple[float, ...]
    evidence: SpectralEvidence
    input_kind: str = "absolute_irradiance"
    target_irradiance_W_m2: float | None = None
    enabled: bool = True

    def __post_init__(self):
        _arrays(self, "values", 2)
        if type(self.input_kind) is not str or self.input_kind not in {"absolute_irradiance", "relative_shape"}:
            raise ValueError("unsupported spectral input kind")
        if self.input_kind == "absolute_irradiance":
            if self.target_irradiance_W_m2 is not None:
                raise ValueError("absolute measurements cannot be silently renormalized")
        else:
            object.__setattr__(self, "target_irradiance_W_m2", _number(self.target_irradiance_W_m2, "target_irradiance_W_m2"))
            if self.shape_integral == 0:
                raise ValueError("a zero-integral relative shape cannot be normalized")
        _number(self.normalization_factor, "normalization_factor")
        for value in self.irradiance_density_W_m2_nm:
            _number(value, "resolved density")
        _number(self.in_band_irradiance_W_m2, "in-band irradiance")
        _number(self.photon_flux_m2_s, "photon flux")

    @property
    def shape_integral(self):
        return _trapezoid(self.wavelength_nm, self.values)

    @property
    def normalization_factor(self):
        return 1.0 if self.input_kind == "absolute_irradiance" else self.target_irradiance_W_m2/self.shape_integral

    @property
    def irradiance_density_W_m2_nm(self):
        scale = self.normalization_factor if self.enabled else 0.0
        return tuple(value*scale for value in self.values)

    @property
    def in_band_irradiance_W_m2(self):
        return _trapezoid(self.wavelength_nm, self.irradiance_density_W_m2_nm)

    @property
    def photon_flux_m2_s(self):
        # Integral of lambda*S(lambda) for the declared linear S interpolant.
        values = self.irradiance_density_W_m2_nm
        moment = _sum((b-a)*(a*(x/3+y/6)+b*(x/6+y/3))
                      for a,b,x,y in zip(self.wavelength_nm, self.wavelength_nm[1:], values, values[1:]))
        return moment*1e-9/(PLANCK_J_S*LIGHT_SPEED_M_S)

    def to_dict(self):
        return {"schema_version": "tabulated-spectrum-v1", "wavelength_unit": "nm",
                "value_unit": "W m^-2 nm^-1" if self.input_kind == "absolute_irradiance" else "dimensionless",
                "integration_policy": "piecewise-linear-density-exact-moments-v1",
                "wavelength_nm": list(self.wavelength_nm), "values": list(self.values),
                "evidence": self.evidence.to_dict(), "input_kind": self.input_kind,
                "target_irradiance_W_m2": self.target_irradiance_W_m2, "enabled": self.enabled}

    @classmethod
    def from_dict(cls, data):
        _keys(data, ("schema_version", "wavelength_unit", "value_unit", "integration_policy", "wavelength_nm", "values", "evidence", "input_kind", "target_irradiance_W_m2", "enabled"))
        if type(data["wavelength_nm"]) is not list or type(data["values"]) is not list:
            raise ValueError("spectral archive arrays must be lists")
        obj = cls(tuple(data["wavelength_nm"]), tuple(data["values"]), SpectralEvidence.from_dict(data["evidence"]), data["input_kind"], data["target_irradiance_W_m2"], data["enabled"])
        if obj.to_dict() != data:
            raise ValueError("unsupported spectral schema, units or integration policy")
        return obj


@dataclass(frozen=True)
class DiscreteLineSpectrum(_Archive):
    """Resolved optical lines with integrated W m^-2 per line, not densities."""
    wavelength_nm: tuple[float, ...]
    line_irradiance_W_m2: tuple[float, ...]
    evidence: SpectralEvidence
    enabled: bool = True

    def __post_init__(self):
        _arrays(self, "line_irradiance_W_m2", 1)
        _number(self.in_band_irradiance_W_m2, "line irradiance")
        _number(self.photon_flux_m2_s, "line photon flux")

    @property
    def in_band_irradiance_W_m2(self):
        return _sum(self.line_irradiance_W_m2) if self.enabled else 0.0

    @property
    def photon_flux_m2_s(self):
        if not self.enabled:
            return 0.0
        return _sum(p*(w*1e-9)/(PLANCK_J_S*LIGHT_SPEED_M_S) for w,p in zip(self.wavelength_nm, self.line_irradiance_W_m2))

    def to_dict(self):
        return {"schema_version": "discrete-line-spectrum-v1", "wavelength_unit": "nm",
                "value_unit": "W m^-2", "wavelength_nm": list(self.wavelength_nm),
                "line_irradiance_W_m2": list(self.line_irradiance_W_m2),
                "evidence": self.evidence.to_dict(), "enabled": self.enabled}

    @classmethod
    def from_dict(cls, data):
        _keys(data, ("schema_version", "wavelength_unit", "value_unit", "wavelength_nm", "line_irradiance_W_m2", "evidence", "enabled"))
        if type(data["wavelength_nm"]) is not list or type(data["line_irradiance_W_m2"]) is not list:
            raise ValueError("line archive arrays must be lists")
        obj = cls(tuple(data["wavelength_nm"]), tuple(data["line_irradiance_W_m2"]), SpectralEvidence.from_dict(data["evidence"]), data["enabled"])
        if obj.to_dict() != data:
            raise ValueError("unsupported line schema or units")
        return obj
