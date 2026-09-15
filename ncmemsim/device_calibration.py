from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from enum import Enum
import math
from typing import Sequence

import numpy as np

from .device import Device
from .fitting import FitParameterSet
from .hashing import canonical_hash
from .materials.base import NanocrystalMaterial
from .physics import PhysicsModel
from .simulator import SimulationConfig


class DeviceFitTarget(str, Enum):
    """Controlled physical targets for device-level fitting."""

    FG_ELECTRICALLY_ACTIVE_FRACTION = "fg.electrically_active_fraction"
    FG_NC_VOLUME_FRACTION = "fg.nc_volume_fraction"
    FG_NC_DIAMETER_NM = "fg.nc_diameter_nm"
    FG_PHI_BARRIER_PROG_EV = "fg.phi_barrier_prog_eV"
    FG_PHI_BARRIER_ERASE_EV = "fg.phi_barrier_erase_eV"

    KINETICS_NU0_HZ = "kinetics.nu0_Hz"
    KINETICS_NU1_HZ = "kinetics.nu1_Hz"
    KINETICS_NU2_HZ = "kinetics.nu2_Hz"
    KINETICS_CAPACITANCE_EPS_R = "kinetics.capacitance_eps_r"

    TUNNELING_INJECTION_ENERGY_EV = "tunneling.injection_energy_eV"
    TUNNELING_OXIDE_EFFECTIVE_MASS_M0 = "tunneling.oxide_effective_mass_m0"
    TUNNELING_FIELD_COUPLING_FACTOR = "tunneling.field_coupling_factor"
    TUNNELING_ACTIVATION_BETA_V_INV = "tunneling.activation_beta_V_inv"

    SIMULATION_QFIX_C_M2 = "simulation.qfix_C_m2"
    SIMULATION_QIT_C_M2 = "simulation.qit_C_m2"


_FG_TARGETS = frozenset(
    {
        DeviceFitTarget.FG_ELECTRICALLY_ACTIVE_FRACTION,
        DeviceFitTarget.FG_NC_VOLUME_FRACTION,
        DeviceFitTarget.FG_NC_DIAMETER_NM,
        DeviceFitTarget.FG_PHI_BARRIER_PROG_EV,
        DeviceFitTarget.FG_PHI_BARRIER_ERASE_EV,
    }
)

_KINETICS_FIELDS = {
    DeviceFitTarget.KINETICS_NU0_HZ: "nu0_Hz",
    DeviceFitTarget.KINETICS_NU1_HZ: "nu1_Hz",
    DeviceFitTarget.KINETICS_NU2_HZ: "nu2_Hz",
    DeviceFitTarget.KINETICS_CAPACITANCE_EPS_R: "capacitance_eps_r",
}

_TUNNELING_FIELDS = {
    DeviceFitTarget.TUNNELING_INJECTION_ENERGY_EV: "injection_energy_eV",
    DeviceFitTarget.TUNNELING_OXIDE_EFFECTIVE_MASS_M0: "oxide_effective_mass_m0",
    DeviceFitTarget.TUNNELING_FIELD_COUPLING_FACTOR: "field_coupling_factor",
    DeviceFitTarget.TUNNELING_ACTIVATION_BETA_V_INV: "activation_beta_V_inv",
}

_SIMULATION_FIELDS = {
    DeviceFitTarget.SIMULATION_QFIX_C_M2: "qfix_C_m2",
    DeviceFitTarget.SIMULATION_QIT_C_M2: "qit_C_m2",
}

_CANONICAL_UNITS: dict[DeviceFitTarget, str | None] = {
    DeviceFitTarget.FG_ELECTRICALLY_ACTIVE_FRACTION: None,
    DeviceFitTarget.FG_NC_VOLUME_FRACTION: None,
    DeviceFitTarget.FG_NC_DIAMETER_NM: "nm",
    DeviceFitTarget.FG_PHI_BARRIER_PROG_EV: "eV",
    DeviceFitTarget.FG_PHI_BARRIER_ERASE_EV: "eV",
    DeviceFitTarget.KINETICS_NU0_HZ: "Hz",
    DeviceFitTarget.KINETICS_NU1_HZ: "Hz",
    DeviceFitTarget.KINETICS_NU2_HZ: "Hz",
    DeviceFitTarget.KINETICS_CAPACITANCE_EPS_R: None,
    DeviceFitTarget.TUNNELING_INJECTION_ENERGY_EV: "eV",
    DeviceFitTarget.TUNNELING_OXIDE_EFFECTIVE_MASS_M0: "m0",
    DeviceFitTarget.TUNNELING_FIELD_COUPLING_FACTOR: None,
    DeviceFitTarget.TUNNELING_ACTIVATION_BETA_V_INV: "1/V",
    DeviceFitTarget.SIMULATION_QFIX_C_M2: "C/m^2",
    DeviceFitTarget.SIMULATION_QIT_C_M2: "C/m^2",
}


@dataclass(frozen=True)
class DeviceFitParameterBinding:
    """
    Bind one ordered FitParameter to one controlled physical target.

    ``fg_index`` is required only for floating-gate targets and follows
    ``Device.floating_gates()`` ordering.
    """

    parameter_name: str
    target: DeviceFitTarget
    fg_index: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.parameter_name, str):
            raise TypeError("parameter_name must be a string.")

        name = self.parameter_name.strip()
        if not name:
            raise ValueError("parameter_name cannot be empty.")

        if not isinstance(self.target, DeviceFitTarget):
            try:
                target = DeviceFitTarget(self.target)
            except (TypeError, ValueError) as exc:
                raise TypeError("target must be a DeviceFitTarget.") from exc
            object.__setattr__(self, "target", target)

        if self.target in _FG_TARGETS:
            if isinstance(self.fg_index, bool) or not isinstance(self.fg_index, int):
                raise TypeError(
                    "fg_index must be an integer for floating-gate targets."
                )
            if self.fg_index < 0:
                raise ValueError("fg_index must be non-negative.")
        elif self.fg_index is not None:
            raise ValueError("fg_index is only valid for floating-gate targets.")

        object.__setattr__(self, "parameter_name", name)

    @property
    def canonical_unit(self) -> str | None:
        return _CANONICAL_UNITS[self.target]

    @property
    def target_key(self) -> str:
        if self.target in _FG_TARGETS:
            suffix = self.target.value.removeprefix("fg.")
            return f"fg[{self.fg_index}].{suffix}"
        return self.target.value

    def to_dict(self) -> dict:
        out = {
            "parameter_name": self.parameter_name,
            "target": self.target.value,
            "canonical_unit": self.canonical_unit,
        }
        if self.fg_index is not None:
            out["fg_index"] = self.fg_index
        return out


def _targets(
    bindings: tuple[DeviceFitParameterBinding, ...],
) -> set[DeviceFitTarget]:
    return {binding.target for binding in bindings}


def _for_fg(
    bindings: tuple[DeviceFitParameterBinding, ...],
    fg_index: int,
) -> tuple[DeviceFitParameterBinding, ...]:
    return tuple(binding for binding in bindings if binding.fg_index == fg_index)


def _identifiability_warnings(
    bindings: tuple[DeviceFitParameterBinding, ...],
) -> tuple[str, ...]:
    warnings: list[str] = []
    targets = _targets(bindings)

    if (
        DeviceFitTarget.KINETICS_NU0_HZ in targets
        and any(
            b.target == DeviceFitTarget.FG_PHI_BARRIER_PROG_EV
            for b in bindings
        )
    ):
        warnings.append(
            "nu0_Hz and program barrier are strongly correlated through "
            "the product of attempt frequency and tunneling transmission; "
            "use joint or multi-condition data before interpreting them independently."
        )

    if (
        targets.intersection(
            {
                DeviceFitTarget.KINETICS_NU1_HZ,
                DeviceFitTarget.KINETICS_NU2_HZ,
            }
        )
        and any(
            b.target == DeviceFitTarget.FG_PHI_BARRIER_ERASE_EV
            for b in bindings
        )
    ):
        warnings.append(
            "erase attempt frequency and erase barrier are strongly correlated "
            "through escape-rate products; use joint or multi-condition data "
            "before interpreting them independently."
        )

    if (
        targets.intersection(
            {
                DeviceFitTarget.TUNNELING_INJECTION_ENERGY_EV,
                DeviceFitTarget.TUNNELING_OXIDE_EFFECTIVE_MASS_M0,
                DeviceFitTarget.TUNNELING_FIELD_COUPLING_FACTOR,
            }
        )
        and any(
            b.target
            in {
                DeviceFitTarget.FG_PHI_BARRIER_PROG_EV,
                DeviceFitTarget.FG_PHI_BARRIER_ERASE_EV,
            }
            for b in bindings
        )
    ):
        warnings.append(
            "WKB barrier, injection energy, oxide effective mass, and field "
            "coupling can be highly correlated; independent constraints are recommended."
        )

    fg_indices = sorted(
        {b.fg_index for b in bindings if b.fg_index is not None}
    )
    for fg_index in fg_indices:
        fg_targets = {b.target for b in _for_fg(bindings, fg_index)}
        if (
            DeviceFitTarget.FG_NC_DIAMETER_NM in fg_targets
            and fg_targets.intersection(
                {
                    DeviceFitTarget.FG_ELECTRICALLY_ACTIVE_FRACTION,
                    DeviceFitTarget.FG_NC_VOLUME_FRACTION,
                }
            )
        ):
            warnings.append(
                f"FG {fg_index}: nanocrystal diameter is correlated with "
                "effective NC density because density scales with inverse NC volume; "
                "use independent size information where possible."
            )

    if len(bindings) > 3:
        warnings.append(
            "More than three device-level parameters are free; local "
            "identifiability diagnostics and multi-dataset validation are strongly recommended."
        )

    return tuple(sorted(warnings))


@dataclass(frozen=True)
class DeviceCalibrationSpec:
    """
    Deterministic optimizer-to-physics binding specification.

    This class defines what may be varied. It does not run fitting and does
    not assign FITTED or CALIBRATED provenance.

    Exact structural degeneracies in the current model are rejected:
    qfix/qit enter electrostatics only through their sum, and active fraction /
    NC volume fraction enter the current effective NC density as a product.
    """

    parameter_set: FitParameterSet
    bindings: tuple[DeviceFitParameterBinding, ...]
    name: str = "device-calibration-v1"
    notes: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.parameter_set, FitParameterSet):
            raise TypeError("parameter_set must be a FitParameterSet.")

        bindings = tuple(self.bindings)
        if len(bindings) != self.parameter_set.n_parameters:
            raise ValueError(
                "bindings must contain exactly one entry per FitParameter."
            )
        if not all(isinstance(b, DeviceFitParameterBinding) for b in bindings):
            raise TypeError(
                "bindings must contain only DeviceFitParameterBinding instances."
            )

        if tuple(b.parameter_name for b in bindings) != self.parameter_set.names:
            raise ValueError(
                "Binding parameter names and order must exactly match FitParameterSet.names."
            )

        keys = tuple(b.target_key for b in bindings)
        if len(keys) != len(set(keys)):
            raise ValueError("Each physical fit target may be bound only once.")

        if not isinstance(self.name, str):
            raise TypeError("name must be a string.")
        name = self.name.strip()
        if not name:
            raise ValueError("name cannot be empty.")

        notes = self.notes
        if notes is not None:
            if not isinstance(notes, str):
                raise TypeError("notes must be a string or None.")
            notes = notes.strip()
            if not notes:
                raise ValueError("notes cannot be empty when supplied.")

        targets = _targets(bindings)
        if {
            DeviceFitTarget.SIMULATION_QFIX_C_M2,
            DeviceFitTarget.SIMULATION_QIT_C_M2,
        }.issubset(targets):
            raise ValueError(
                "qfix_C_m2 and qit_C_m2 are structurally non-identifiable "
                "in the current electrostatic model because flat-band voltage "
                "depends on their sum. Fit at most one."
            )

        for fg_index in {
            b.fg_index for b in bindings if b.fg_index is not None
        }:
            fg_targets = {b.target for b in _for_fg(bindings, fg_index)}
            if {
                DeviceFitTarget.FG_ELECTRICALLY_ACTIVE_FRACTION,
                DeviceFitTarget.FG_NC_VOLUME_FRACTION,
            }.issubset(fg_targets):
                raise ValueError(
                    "electrically_active_fraction and nc_volume_fraction are "
                    "structurally non-identifiable when both are free for "
                    f"FG {fg_index}; current effective NC density depends on their product."
                )

        object.__setattr__(self, "bindings", bindings)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "notes", notes)

    @property
    def identifiability_warnings(self) -> tuple[str, ...]:
        return _identifiability_warnings(self.bindings)

    def to_dict(self) -> dict:
        out = {
            "schema_version": 1,
            "name": self.name,
            "parameter_set": self.parameter_set.to_dict(),
            "bindings": [b.to_dict() for b in self.bindings],
            "identifiability_warnings": list(self.identifiability_warnings),
        }
        if self.notes is not None:
            out["notes"] = self.notes
        return out

    def specification_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass
class DeviceCalibrationContext:
    """
    Isolated device/physics/config objects after one parameter application.

    ``parameter_application_hash`` identifies only the binding specification
    plus applied values. It is intentionally not a complete simulator
    reproducibility hash.
    """

    device: Device
    physics: PhysicsModel
    simulation_config: SimulationConfig
    specification_hash: str
    parameter_values: dict[str, float]
    identifiability_warnings: tuple[str, ...]

    def parameter_application_manifest(self) -> dict:
        return {
            "schema_version": 1,
            "specification_hash": self.specification_hash,
            "parameter_values": dict(self.parameter_values),
            "identifiability_warnings": list(self.identifiability_warnings),
        }

    def parameter_application_hash(self) -> str:
        return canonical_hash(self.parameter_application_manifest())


def _validate_physics_sharing(physics: PhysicsModel) -> None:
    if physics.occupancy.tunneling is not physics.tunneling:
        raise ValueError(
            "PhysicsModel must share the same TunnelingEngine between "
            "physics.tunneling and occupancy.tunneling for device calibration."
        )

    transport_tunneling = getattr(
        physics.transport,
        "tunneling",
        physics.tunneling,
    )
    if transport_tunneling is not physics.tunneling:
        raise ValueError(
            "PhysicsModel must share the same TunnelingEngine between "
            "physics.tunneling and transport.tunneling for device calibration."
        )


def _validate_target_value(
    binding: DeviceFitParameterBinding,
    value: float,
) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{binding.parameter_name} must be finite.")

    target = binding.target

    if target in {
        DeviceFitTarget.FG_ELECTRICALLY_ACTIVE_FRACTION,
        DeviceFitTarget.FG_NC_VOLUME_FRACTION,
    }:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{target.value} must lie in [0, 1].")
        return

    positive_targets = {
        DeviceFitTarget.FG_NC_DIAMETER_NM,
        DeviceFitTarget.FG_PHI_BARRIER_PROG_EV,
        DeviceFitTarget.FG_PHI_BARRIER_ERASE_EV,
        DeviceFitTarget.KINETICS_NU0_HZ,
        DeviceFitTarget.KINETICS_NU1_HZ,
        DeviceFitTarget.KINETICS_NU2_HZ,
        DeviceFitTarget.KINETICS_CAPACITANCE_EPS_R,
        DeviceFitTarget.TUNNELING_OXIDE_EFFECTIVE_MASS_M0,
        DeviceFitTarget.TUNNELING_FIELD_COUPLING_FACTOR,
        DeviceFitTarget.TUNNELING_ACTIVATION_BETA_V_INV,
    }
    if target in positive_targets and value <= 0.0:
        raise ValueError(f"{target.value} must be strictly positive.")

    if (
        target == DeviceFitTarget.TUNNELING_INJECTION_ENERGY_EV
        and value < 0.0
    ):
        raise ValueError(
            "tunneling.injection_energy_eV must be non-negative."
        )


def _replace_material_property_value(
    material: NanocrystalMaterial,
    *,
    field_name: str,
    property_key: str,
    value: float,
) -> NanocrystalMaterial:
    properties = dict(material.properties)
    if property_key in properties:
        properties[property_key] = replace(
            properties[property_key],
            value=value,
        )
    return replace(
        material,
        **{field_name: value, "properties": properties},
    )


def _fg_for_binding(
    device: Device,
    binding: DeviceFitParameterBinding,
):
    floating_gates = device.floating_gates()
    assert binding.fg_index is not None
    if binding.fg_index >= len(floating_gates):
        raise ValueError(
            f"Binding {binding.parameter_name!r} targets FG index "
            f"{binding.fg_index}, but the device contains "
            f"{len(floating_gates)} floating gate(s)."
        )
    return floating_gates[binding.fg_index]


def _apply_binding(
    device: Device,
    physics: PhysicsModel,
    simulation_config: SimulationConfig,
    binding: DeviceFitParameterBinding,
    value: float,
) -> SimulationConfig:
    _validate_target_value(binding, value)
    target = binding.target

    if target in _FG_TARGETS:
        fg = _fg_for_binding(device, binding)

        if target == DeviceFitTarget.FG_ELECTRICALLY_ACTIVE_FRACTION:
            fg.electrically_active_fraction = value
        elif target == DeviceFitTarget.FG_NC_VOLUME_FRACTION:
            fg.nc_volume_fraction = value
        elif target == DeviceFitTarget.FG_NC_DIAMETER_NM:
            fg.nc_diameter_nm = value
        elif target == DeviceFitTarget.FG_PHI_BARRIER_PROG_EV:
            fg.nc_material = _replace_material_property_value(
                fg.nc_material,
                field_name="phi_barrier_prog_eV",
                property_key="phi_barrier_prog_eV",
                value=value,
            )
        elif target == DeviceFitTarget.FG_PHI_BARRIER_ERASE_EV:
            fg.nc_material = _replace_material_property_value(
                fg.nc_material,
                field_name="phi_barrier_erase_eV",
                property_key="phi_barrier_erase_eV",
                value=value,
            )
        return simulation_config

    if target in _KINETICS_FIELDS:
        physics.occupancy.config = replace(
            physics.occupancy.config,
            **{_KINETICS_FIELDS[target]: value},
        )
        return simulation_config

    if target in _TUNNELING_FIELDS:
        # Keep the cloned TunnelingEngine object itself so the canonical
        # shared reference held by occupancy/transport remains intact.
        physics.tunneling.config = replace(
            physics.tunneling.config,
            **{_TUNNELING_FIELDS[target]: value},
        )
        return simulation_config

    if target in _SIMULATION_FIELDS:
        return replace(
            simulation_config,
            **{_SIMULATION_FIELDS[target]: value},
        )

    raise AssertionError(f"Unhandled device fit target: {target!r}")


def apply_device_calibration_parameters(
    base_device: Device,
    base_physics: PhysicsModel,
    base_simulation_config: SimulationConfig,
    spec: DeviceCalibrationSpec,
    values: np.ndarray | Sequence[float],
) -> DeviceCalibrationContext:
    """
    Apply one bounded parameter vector to isolated deep-copied model objects.

    The three baseline objects are copied together so aliasing inside the
    object graph is preserved. Baselines are never mutated.

    This function only applies parameters. It does not run a simulator,
    evaluate an objective, or assign FITTED/CALIBRATED provenance.
    """

    if not isinstance(base_device, Device):
        raise TypeError("base_device must be a Device instance.")
    if not isinstance(base_physics, PhysicsModel):
        raise TypeError("base_physics must be a PhysicsModel instance.")
    if not isinstance(base_simulation_config, SimulationConfig):
        raise TypeError(
            "base_simulation_config must be a SimulationConfig instance."
        )
    if not isinstance(spec, DeviceCalibrationSpec):
        raise TypeError("spec must be a DeviceCalibrationSpec.")

    base_device.validate()
    _validate_physics_sharing(base_physics)
    vector = spec.parameter_set.validate_values(values)

    device, physics, simulation_config = deepcopy(
        (base_device, base_physics, base_simulation_config)
    )
    _validate_physics_sharing(physics)

    for binding, raw_value in zip(spec.bindings, vector):
        simulation_config = _apply_binding(
            device,
            physics,
            simulation_config,
            binding,
            float(raw_value),
        )

    device.validate()
    _validate_physics_sharing(physics)

    return DeviceCalibrationContext(
        device=device,
        physics=physics,
        simulation_config=simulation_config,
        specification_hash=spec.specification_hash(),
        parameter_values=spec.parameter_set.values_to_dict(vector),
        identifiability_warnings=spec.identifiability_warnings,
    )


__all__ = [
    "DeviceCalibrationContext",
    "DeviceCalibrationSpec",
    "DeviceFitParameterBinding",
    "DeviceFitTarget",
    "apply_device_calibration_parameters",
]
