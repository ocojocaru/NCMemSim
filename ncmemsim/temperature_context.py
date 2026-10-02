# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Owned isothermal application contexts; existing workflow archives stay separate."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, replace
from enum import Enum
import hashlib
import json

from .device import Device
from .physics import PhysicsModel
from .simulator import SimulationConfig, Simulator
from .optics import evaluate_floating_gate_optical_absorption
from .materials.temperature import (
    AnchoredVarshniProfile, IntrinsicDensityProfile, GapKind,
    _number, _text, _keys, _unique_object, _reject_constant,
)
from .materials.optics.models import (
    GeSnOpticalParameterSet, GeSnAbsorptionParameterSet, CompositeGeSnAbsorptionModel,
    OpticalPoint, direct_gap_gesn_eV, indirect_gap_gesn_eV, photon_energy_eV,
    direct_absorption_m_inv, indirect_absorption_m_inv, urbach_absorption_m_inv,
    ABSORPTION_MODEL_PROVENANCE, ABSORPTION_COEFFICIENT_PROVENANCE,
    PHONON_OCCUPATION_PROVENANCE,
)
from .dtco.sweep import _json_snapshot
from .workflows.application import (
    _device_payload, _restore_device, _physics_payload, _restore_physics,
)

__all__ = ["SemiconductorThermalMode", "OpticalThermalMode", "OpticalThermalBinding",
           "ThermalContext", "ResolvedThermalContext", "ThermalSimulator"]


class SemiconductorThermalMode(str, Enum):
    LEGACY = "legacy"
    GAP_ONLY = "gap_only"
    DENSITY_ONLY = "density_only"
    COUPLED = "coupled"


class OpticalThermalMode(str, Enum):
    LEGACY = "legacy"
    GAPS_ONLY = "gaps_only"
    PHONONS_ONLY = "phonons_only"
    COUPLED = "coupled"


def _dump(value):
    return _json_snapshot(value)


def _load(text):
    if type(text) is not str:
        raise ValueError("thermal context archive must be JSON text")
    result = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    _dump(result)
    return result


def _hash(value):
    return hashlib.sha256(_dump(value).encode("utf-8")).hexdigest()


def _config(value, kind):
    if type(value) is not kind or set(vars(value)) != {f.name for f in fields(kind)}:
        raise ValueError("unextended typed configuration required: " + kind.__name__)
    result = asdict(value)
    _dump(result)
    for key, item in result.items():
        if key != "name":
            _number(item, key)
        else:
            _text(item, key)
    return result


def _restore_config(raw, kind):
    _keys(raw, (f.name for f in fields(kind)))
    try:
        value = kind(**raw)
    except (TypeError, OverflowError) as exc:
        raise ValueError("invalid typed thermal configuration") from exc
    _config(value, kind)
    return value


class _Archive:
    @property
    def context_hash(self) -> str:
        return _hash(self.to_dict())

    def to_json(self) -> str:
        return _dump(self.to_dict())

    @classmethod
    def from_json(cls, text: str):
        return cls.from_dict(_load(text))


@dataclass(frozen=True)
class OpticalThermalBinding(_Archive):
    layer_name: str
    mode: OpticalThermalMode
    gamma_profile: AnchoredVarshniProfile | None = None
    l_profile: AnchoredVarshniProfile | None = None
    optical_parameters: GeSnOpticalParameterSet = field(default_factory=GeSnOpticalParameterSet)
    absorption_parameters: GeSnAbsorptionParameterSet = field(default_factory=GeSnAbsorptionParameterSet)

    def __post_init__(self):
        _text(self.layer_name, "layer_name")
        if type(self.mode) is not OpticalThermalMode:
            raise ValueError("typed optical mode required")
        _config(self.optical_parameters, GeSnOpticalParameterSet)
        _config(self.absorption_parameters, GeSnAbsorptionParameterSet)
        if self.mode is not OpticalThermalMode.LEGACY:
            if self.gamma_profile is None or self.l_profile is None:
                raise ValueError("Gamma and L profiles are both required")
        for profile, target, baseline in (
            (self.gamma_profile, GapKind.GAMMA, direct_gap_gesn_eV),
            (self.l_profile, GapKind.L, indirect_gap_gesn_eV),
        ):
            if profile is not None:
                if type(profile) is not AnchoredVarshniProfile or profile.gap_kind is not target:
                    raise ValueError("incorrect optical valley target")
                if profile.reference_gap_eV != baseline(profile.sn_fraction, self.optical_parameters):
                    raise ValueError("optical profile anchor differs from nominal override")
                if profile.reference_temperature_K != self.optical_parameters.temperature_K:
                    raise ValueError("optical profile and baseline reference temperatures differ")
        if self.gamma_profile is not None and self.l_profile is not None:
            if (self.gamma_profile.sn_fraction != self.l_profile.sn_fraction
                    or self.gamma_profile.domain.material is not self.l_profile.domain.material
                    or self.gamma_profile.reference_temperature_K != self.l_profile.reference_temperature_K):
                raise ValueError("Gamma/L material, composition and reference must agree")
        if self.optical_parameters.temperature_K != self.absorption_parameters.temperature_K:
            raise ValueError("nominal optical gaps and phonons require one reference temperature")

    def to_dict(self) -> dict:
        return {"layer_name": self.layer_name, "mode": self.mode.value,
            "gamma_profile": None if self.gamma_profile is None else self.gamma_profile.to_dict(),
            "l_profile": None if self.l_profile is None else self.l_profile.to_dict(),
            "optical_parameters": asdict(self.optical_parameters),
            "absorption_parameters": asdict(self.absorption_parameters)}

    @classmethod
    def from_dict(cls, data: dict) -> OpticalThermalBinding:
        _keys(data, ("layer_name", "mode", "gamma_profile", "l_profile", "optical_parameters", "absorption_parameters"))
        if type(data["mode"]) is not str:
            raise ValueError("optical mode archive must be a string")
        return cls(data["layer_name"], OpticalThermalMode(data["mode"]),
            None if data["gamma_profile"] is None else AnchoredVarshniProfile.from_dict(data["gamma_profile"]),
            None if data["l_profile"] is None else AnchoredVarshniProfile.from_dict(data["l_profile"]),
            _restore_config(data["optical_parameters"], GeSnOpticalParameterSet),
            _restore_config(data["absorption_parameters"], GeSnAbsorptionParameterSet))


@dataclass(frozen=True)
class ThermalContext(_Archive):
    nominal_device_json: str
    nominal_physics_json: str
    simulation_config_json: str
    enabled: bool = False
    semiconductor_mode: SemiconductorThermalMode = SemiconductorThermalMode.LEGACY
    substrate_gap: AnchoredVarshniProfile | None = None
    intrinsic_density: IntrinsicDensityProfile | None = None
    optical_bindings: tuple[OpticalThermalBinding, ...] = ()

    def __post_init__(self):
        if type(self.enabled) is not bool or type(self.semiconductor_mode) is not SemiconductorThermalMode:
            raise ValueError("typed enabled flag and semiconductor mode required")
        device_raw, physics_raw, config_raw = (_load(self.nominal_device_json),
            _load(self.nominal_physics_json), _load(self.simulation_config_json))
        try:
            device = _restore_device(device_raw)
            physics = _restore_physics(physics_raw)
            config = _restore_config(config_raw, SimulationConfig)
        except (KeyError, TypeError, AttributeError, OverflowError) as exc:
            raise ValueError("invalid nominal thermal snapshot") from exc
        for text, raw in ((self.nominal_device_json, device_raw),
                          (self.nominal_physics_json, physics_raw),
                          (self.simulation_config_json, config_raw)):
            if text != _dump(raw):
                raise ValueError("nominal snapshot must use canonical JSON")
        _number(device.temperature_K, "nominal temperature", positive=True)
        _number(device.substrate_doping_m3, "nominal doping", positive=True)
        if config.dwell_time_s < 0 or config.internal_dt_s <= 0:
            raise ValueError("invalid simulation time controls")
        s = physics.electrostatics.semiconductor
        _config(s, type(s))
        gap, density = self.substrate_gap, self.intrinsic_density
        if gap is not None:
            if type(gap) is not AnchoredVarshniProfile or gap.gap_kind is not GapKind.SUBSTRATE:
                raise ValueError("Si substrate profile required")
            if gap.reference_gap_eV != s.bandgap_eV:
                raise ValueError("Si gap anchor differs from nominal override")
        if density is not None:
            if type(density) is not IntrinsicDensityProfile:
                raise ValueError("typed intrinsic density profile required")
            if density.reference_density_m3 != s.intrinsic_density_m3:
                raise ValueError("Si density anchor differs from nominal override")
            if density.gap_profile.reference_gap_eV != s.bandgap_eV:
                raise ValueError("density's coupled gap anchor differs from nominal override")
            if gap is not None and density.gap_profile != gap:
                raise ValueError("density and substrate gap must share the same declared profile")
        if self.semiconductor_mode in (SemiconductorThermalMode.GAP_ONLY, SemiconductorThermalMode.COUPLED) and gap is None:
            raise ValueError("requested semiconductor mode requires a gap profile")
        if self.semiconductor_mode in (SemiconductorThermalMode.DENSITY_ONLY, SemiconductorThermalMode.COUPLED) and density is None:
            raise ValueError("requested semiconductor mode requires a density profile")
        if type(self.optical_bindings) is not tuple or any(type(b) is not OpticalThermalBinding for b in self.optical_bindings):
            raise ValueError("optical bindings must be an immutable typed tuple")
        names = tuple(b.layer_name for b in self.optical_bindings)
        fg_names = {fg.name for fg in device.floating_gates()}
        if len(set(names)) != len(names) or not set(names) <= fg_names:
            raise ValueError("duplicate or unknown optical FG attachment")
        if set(names) != fg_names:
            raise ValueError("declare a binding, including legacy controls, for every FG")
        object.__setattr__(self, "optical_bindings", tuple(sorted(self.optical_bindings, key=lambda b: b.layer_name)))
        references = []
        if gap is not None:
            references.append(gap.reference_temperature_K)
        if density is not None:
            references.append(density.gap_profile.reference_temperature_K)
        for binding in self.optical_bindings:
            material = device.get_layer(binding.layer_name).nc_material
            if binding.mode is not OpticalThermalMode.LEGACY and material.model_name not in {"GeModel", "GeSnModel"}:
                raise ValueError("thermal optical attachment requires a declared Ge/GeSn material model")
            for profile in (binding.gamma_profile, binding.l_profile):
                if profile is not None and profile.sn_fraction != material.sn_fraction:
                    raise ValueError("profile composition differs from attached FG")
            if binding.mode is not OpticalThermalMode.LEGACY:
                references.append(binding.optical_parameters.temperature_K)
        if references and any(t != references[0] for t in references):
            raise ValueError("thermal components must share one reference temperature")

    @classmethod
    def from_nominal(cls, device: Device, physics: PhysicsModel | None = None,
                     config: SimulationConfig | None = None, *, enabled: bool = False,
                     semiconductor_mode: SemiconductorThermalMode = SemiconductorThermalMode.LEGACY,
                     substrate_gap: AnchoredVarshniProfile | None = None,
                     intrinsic_density: IntrinsicDensityProfile | None = None,
                     optical_bindings: tuple[OpticalThermalBinding, ...] = ()) -> ThermalContext:
        if type(device) is not Device or type(optical_bindings) is not tuple:
            raise ValueError("typed nominal Device and immutable optical attachment tuple required")
        device.validate()
        if not optical_bindings:
            optical_bindings = tuple(OpticalThermalBinding(fg.name, OpticalThermalMode.LEGACY)
                                     for fg in device.floating_gates())
        return cls(_dump(_device_payload(device)), _dump(_physics_payload(PhysicsModel.default() if physics is None else physics)),
            _dump(_config(SimulationConfig() if config is None else config, SimulationConfig)), enabled,
            semiconductor_mode, substrate_gap, intrinsic_density, optical_bindings)

    @property
    def nominal_hash(self) -> str:
        return _hash({"device": _load(self.nominal_device_json), "physics": _load(self.nominal_physics_json),
                      "simulation_config": _load(self.simulation_config_json)})

    def resolve(self, *, temperature_K: float | None = None) -> ResolvedThermalContext:
        temperature = _load(self.nominal_device_json)["device"]["temperature_K"] if temperature_K is None else temperature_K
        return ResolvedThermalContext(self, temperature)

    def to_dict(self) -> dict:
        return {"schema_version": "thermal-context-v1", "enabled": self.enabled,
            "semiconductor_mode": self.semiconductor_mode.value,
            "nominal_device": _load(self.nominal_device_json), "nominal_physics": _load(self.nominal_physics_json),
            "simulation_config": _load(self.simulation_config_json),
            "substrate_gap": None if self.substrate_gap is None else self.substrate_gap.to_dict(),
            "intrinsic_density": None if self.intrinsic_density is None else self.intrinsic_density.to_dict(),
            "optical_bindings": [b.to_dict() for b in self.optical_bindings]}

    @classmethod
    def from_dict(cls, data: dict) -> ThermalContext:
        _keys(data, ("schema_version", "enabled", "semiconductor_mode", "nominal_device", "nominal_physics",
                    "simulation_config", "substrate_gap", "intrinsic_density", "optical_bindings"))
        if data["schema_version"] != "thermal-context-v1" or type(data["semiconductor_mode"]) is not str:
            raise ValueError("unsupported thermal context schema or mode")
        if type(data["optical_bindings"]) is not list:
            raise ValueError("optical attachment archive must be a list")
        return cls(_dump(data["nominal_device"]), _dump(data["nominal_physics"]), _dump(data["simulation_config"]),
            data["enabled"], SemiconductorThermalMode(data["semiconductor_mode"]),
            None if data["substrate_gap"] is None else AnchoredVarshniProfile.from_dict(data["substrate_gap"]),
            None if data["intrinsic_density"] is None else IntrinsicDensityProfile.from_dict(data["intrinsic_density"]),
            tuple(OpticalThermalBinding.from_dict(b) for b in data["optical_bindings"]))


@dataclass(frozen=True)
class ResolvedThermalContext(_Archive):
    context: ThermalContext
    temperature_K: float

    def __post_init__(self):
        if type(self.context) is not ThermalContext:
            raise ValueError("typed nominal thermal context required")
        object.__setattr__(self, "temperature_K", _number(self.temperature_K, "temperature_K", positive=True))
        self._projection()

    def _projection(self):
        c, t = self.context, self.temperature_K
        device = _load(c.nominal_device_json)
        device["device"]["temperature_K"] = t
        physics = _load(c.nominal_physics_json)
        s = physics["semiconductor"]
        if c.enabled:
            if c.semiconductor_mode in (SemiconductorThermalMode.GAP_ONLY, SemiconductorThermalMode.COUPLED):
                s["bandgap_eV"] = c.substrate_gap.evaluate(t)
            if c.semiconductor_mode in (SemiconductorThermalMode.DENSITY_ONLY, SemiconductorThermalMode.COUPLED):
                s["intrinsic_density_m3"] = c.intrinsic_density.evaluate(t,
                    substrate_doping_m3=device["device"]["substrate_doping_m3"])
        optical = []
        for binding in c.optical_bindings:
            x = _restore_device(device).get_layer(binding.layer_name).nc_material.sn_fraction
            gamma = direct_gap_gesn_eV(x, binding.optical_parameters)
            l_gap = indirect_gap_gesn_eV(x, binding.optical_parameters)
            phonon_t = binding.absorption_parameters.temperature_K
            mode = binding.mode if c.enabled else OpticalThermalMode.LEGACY
            if mode is not OpticalThermalMode.LEGACY:
                evaluated_gamma = binding.gamma_profile.evaluate(t, sn_fraction=x)
                evaluated_l = binding.l_profile.evaluate(t, sn_fraction=x)
                if mode in (OpticalThermalMode.GAPS_ONLY, OpticalThermalMode.COUPLED):
                    gamma, l_gap = evaluated_gamma, evaluated_l
            if mode in (OpticalThermalMode.PHONONS_ONLY, OpticalThermalMode.COUPLED):
                phonon_t = t
            optical.append({"layer_name": binding.layer_name, "applied_mode": mode.value,
                "sn_fraction": x, "gamma_gap_eV": gamma, "l_gap_eV": l_gap,
                "phonon_temperature_K": phonon_t,
                "optical_parameters": asdict(binding.optical_parameters),
                "absorption_parameters": asdict(replace(binding.absorption_parameters, temperature_K=phonon_t))})
        return {"device": device, "physics": physics,
                "simulation_config": _load(c.simulation_config_json), "optical": optical}

    @property
    def device(self) -> Device:
        return _restore_device(self._projection()["device"])

    @property
    def physics(self) -> PhysicsModel:
        return _restore_physics(self._projection()["physics"])

    @property
    def simulation_config(self) -> SimulationConfig:
        return _restore_config(self._projection()["simulation_config"], SimulationConfig)

    def create_simulator(self) -> ThermalSimulator:
        return ThermalSimulator(self)

    def optical_model(self, layer_name: str):
        """Return an independently owned evaluator for an explicitly bound FG."""
        for binding, row in zip(self.context.optical_bindings, self._projection()["optical"], strict=True):
            if binding.layer_name == layer_name:
                row["device_temperature_K"] = self.temperature_K
                return _ResolvedOpticalModel(binding, _dump(row))
        raise ValueError("no optical binding for this layer")

    def to_dict(self) -> dict:
        return {"schema_version": "resolved-thermal-context-v1", "context": self.context.to_dict(),
                "source_context_hash": self.context.context_hash, "nominal_hash": self.context.nominal_hash,
                "temperature_K": self.temperature_K, "resolved": self._projection()}

    @classmethod
    def from_dict(cls, data: dict) -> ResolvedThermalContext:
        _keys(data, ("schema_version", "context", "source_context_hash", "nominal_hash", "temperature_K", "resolved"))
        if data["schema_version"] != "resolved-thermal-context-v1":
            raise ValueError("unsupported resolved thermal context schema")
        result = ThermalContext.from_dict(data["context"]).resolve(temperature_K=data["temperature_K"])
        if _dump(data) != result.to_json():
            raise ValueError("thermal context hashes or recomputed resolution differ")
        return result


@dataclass(frozen=True)
class _ResolvedOpticalModel:
    binding: OpticalThermalBinding
    projection_json: str

    def evaluate(self, material, wavelength_nm):
        try:
            return self._evaluate(material, wavelength_nm)
        except (OverflowError, ZeroDivisionError) as exc:
            raise ValueError("nonrepresentable thermal optical evaluation; no clipping is allowed") from exc

    def _evaluate(self, material, wavelength_nm):
        row = _load(self.projection_json)
        if material.sn_fraction != row["sn_fraction"]:
            raise ValueError("optical model attached to a different composition")
        _number(wavelength_nm, "wavelength_nm", positive=True)
        energy = _number(photon_energy_eV(wavelength_nm), "photon_energy_eV", positive=True)
        parameters = _restore_config(row["absorption_parameters"], GeSnAbsorptionParameterSet)
        if (row["gamma_gap_eV"] == direct_gap_gesn_eV(material.sn_fraction, self.binding.optical_parameters)
                and row["l_gap_eV"] == indirect_gap_gesn_eV(material.sn_fraction, self.binding.optical_parameters)):
            point = CompositeGeSnAbsorptionModel(self.binding.optical_parameters, parameters).evaluate(material, wavelength_nm)
            for name in ("absorption_coefficient_m_inv", "alpha_direct_m_inv", "alpha_indirect_m_inv", "alpha_urbach_m_inv"):
                _number(getattr(point, name), name, nonnegative=True)
            return point
        gamma, l_gap = row["gamma_gap_eV"], row["l_gap_eV"]
        direct = direct_absorption_m_inv(energy, gamma, parameters)
        indirect = indirect_absorption_m_inv(energy, l_gap, parameters)
        urbach = urbach_absorption_m_inv(energy, gamma, parameters)
        for name, value in (("direct absorption", direct), ("indirect absorption", indirect), ("Urbach absorption", urbach)):
            _number(value, name, nonnegative=True)
        total = _number(direct + indirect + urbach, "total absorption", nonnegative=True)
        return OpticalPoint(wavelength_nm, energy, total,
            direct_gap_eV=gamma, indirect_gap_eV=l_gap, alpha_direct_m_inv=direct,
            alpha_indirect_m_inv=indirect, alpha_urbach_m_inv=urbach,
            provenance={"model_form": ABSORPTION_MODEL_PROVENANCE,
                "coefficients": ABSORPTION_COEFFICIENT_PROVENANCE,
                "phonon_occupation": PHONON_OCCUPATION_PROVENANCE,
                "gamma_gap": self.binding.gamma_profile.evaluate_property(
                    row["device_temperature_K"], sn_fraction=material.sn_fraction).provenance,
                "l_gap": self.binding.l_profile.evaluate_property(
                    row["device_temperature_K"], sn_fraction=material.sn_fraction).provenance})


class ThermalSimulator(Simulator):
    """An owned simulator that rejects drift from its declared isothermal context."""

    def __init__(self, resolution: ResolvedThermalContext):
        if type(resolution) is not ResolvedThermalContext:
            raise ValueError("typed resolved thermal context required")
        self._resolution = resolution
        super().__init__(resolution.device, resolution.physics, resolution.simulation_config)

    def _require_context(self):
        expected = self._resolution._projection()
        actual = {"device": _device_payload(self.device), "physics": _physics_payload(self.physics),
                  "simulation_config": _config(self.config, SimulationConfig)}
        if _dump(actual) != _dump({k: expected[k] for k in actual}):
            raise ValueError("thermal simulator inputs changed; resolve a new owned context")

    def _evaluate_optical_absorption(self, source, layer):
        self._require_context()
        bindings = {b.layer_name: b for b in self._resolution.context.optical_bindings}
        if layer.name not in bindings:
            return super()._evaluate_optical_absorption(source, layer)
        return evaluate_floating_gate_optical_absorption(source, layer,
            optical_model=self._resolution.optical_model(layer.name))

    def relax_voltage(self, state, gate_voltage_V, dwell_time_s=None, internal_dt_s=None,
                      light_source=None, photo_config=None, photo_weights=None,
                      occupancy_integrator="explicit_euler"):
        self._require_context()
        return super().relax_voltage(state, gate_voltage_V, dwell_time_s, internal_dt_s,
            light_source, photo_config, photo_weights, occupancy_integrator)
