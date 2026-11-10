# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Opt-in Ge optical gap composition using explicit finite-well pairs."""
from dataclasses import dataclass, replace
import math

from .constants import ELEMENTARY_CHARGE_C
from .materials.finite_confinement import evaluate_finite_confinement
from .materials.finite_confinement_contracts import FiniteConfinementRequest
from .materials.provenance import ParameterProvenance, ParameterStatus
from .materials.structural import _Archive, _keys, _match, _number, _text
from .materials.temperature import GapKind
from .spectral_sources import _canonical
from .structural_optical_context import (
    StructuralOpticalContext,
    _StructuralOpticalModel,
)

__all__ = ['FiniteConfinementOpticalBinding', 'FiniteConfinementOpticalContext']


class _FiniteOpticalModel(_StructuralOpticalModel):
    def evaluate(self, material, wavelength_nm):
        point = super().evaluate(material, wavelength_nm)
        provenance = ParameterProvenance(
            'T4 finite spherical independent-particle optical composition',
            ParameterStatus.ASSUMED, notes=self.row_json, parameter_set=self.context_hash,
        )
        return replace(point, provenance={
            **(point.provenance or {}), 'structural_composition': provenance,
        })


@dataclass(frozen=True)
class FiniteConfinementOpticalBinding(_Archive):
    """Declare one Ge optical transition and the two carrier problems it uses."""

    layer_name: str
    gap_kind: GapKind
    hole_branch: str
    electron: FiniteConfinementRequest
    hole: FiniteConfinementRequest

    def __post_init__(self):
        _text(self.layer_name, 'layer_name')
        _text(self.hole_branch, 'hole_branch')
        if self.gap_kind is not GapKind.GAMMA and self.gap_kind is not GapKind.L:
            raise ValueError('explicit Gamma or L optical transition required')
        for carrier in ('electron', 'hole'):
            request = getattr(self, carrier)
            if type(request) is not FiniteConfinementRequest or request.carrier != carrier:
                raise ValueError(f'explicit {carrier} finite-well request required')
            if request.dot_material != 'Ge':
                raise ValueError('finite optical confinement requires Ge requests')
        for field in ('radius_m', 'temperature_K', 'host_material'):
            if getattr(self.electron, field) != getattr(self.hole, field):
                raise ValueError(f'carrier requests must share {field}')

    def to_dict(self):
        return {
            'schema_version': 'finite-confinement-optical-binding-v1',
            'layer_name': self.layer_name,
            'gap_kind': self.gap_kind.value,
            'hole_branch': self.hole_branch,
            'electron': self.electron.to_dict(),
            'hole': self.hole.to_dict(),
        }

    @classmethod
    def from_dict(cls, data):
        _keys(data, ('schema_version', 'layer_name', 'gap_kind', 'hole_branch', 'electron', 'hole'))
        obj = cls(
            data['layer_name'], GapKind(data['gap_kind']), data['hole_branch'],
            FiniteConfinementRequest.from_dict(data['electron']),
            FiniteConfinementRequest.from_dict(data['hole']),
        )
        _match(data, obj.to_dict())
        return obj


@dataclass(frozen=True)
class FiniteConfinementOpticalContext(_Archive):
    """Replace the confinement contribution at each explicitly selected target."""

    structural_context: StructuralOpticalContext
    bindings: tuple[FiniteConfinementOpticalBinding, ...] = ()

    def __post_init__(self):
        if type(self.structural_context) is not StructuralOpticalContext:
            raise ValueError('typed structural optical owner required')
        if type(self.bindings) is not tuple or any(
            type(binding) is not FiniteConfinementOpticalBinding for binding in self.bindings
        ):
            raise ValueError('typed immutable finite confinement bindings required')
        keys = [(binding.layer_name, binding.gap_kind.value) for binding in self.bindings]
        if len(keys) != len(set(keys)):
            raise ValueError('duplicate finite confinement target')
        object.__setattr__(self, 'bindings', tuple(sorted(
            self.bindings, key=lambda binding: (binding.layer_name, binding.gap_kind.value),
        )))
        self.projection

    @property
    def projection(self):
        """Recompute selected targets from the structural baseline and carrier requests."""
        projection = self.structural_context.projection
        rows = {row['layer_name']: row for row in projection['layers']}
        device = self.structural_context.thermal_resolution.device
        for binding in self.bindings:
            if binding.layer_name not in rows:
                raise ValueError('unknown finite confinement floating gate')
            material = device.get_layer(binding.layer_name).nc_material
            if material.model_name != 'GeModel' or material.sn_fraction != 0:
                raise ValueError('finite optical confinement requires the declared Ge material model')
            row = rows[binding.layer_name]
            if binding.electron.radius_m != row['radius_m_from_device']:
                raise ValueError('finite confinement radius differs from device radius')
            if binding.electron.temperature_K != projection['temperature_K']:
                raise ValueError('finite confinement temperature differs from device temperature')
            electron = evaluate_finite_confinement(binding.electron)
            hole = evaluate_finite_confinement(binding.hole)
            if electron.status != 'bound' or hole.status != 'bound':
                raise ValueError(
                    f'{binding.layer_name}/{binding.gap_kind.value} finite confinement unavailable '
                    f'(electron={electron.status}, hole={hole.status})'
                )
            shift = _number((electron.energy_J + hole.energy_J) / ELEMENTARY_CHARGE_C,
                            'finite kinetic confinement contribution', positive=True)
            target = row['targets'][binding.gap_kind.value]
            try:
                gap = math.fsum((target['thermal_baseline_gap_eV'], target['strain_gap_shift_eV'], shift))
            except OverflowError as exc:
                raise ValueError('combined optical gap is not representable') from exc
            target.update(
                kinetic_confinement_gap_shift_eV=shift,
                resolved_gap_eV=_number(gap, 'combined optical gap', positive=True),
                confinement_result={
                    'model': 'finite_spherical_independent_particle',
                    'hole_branch': binding.hole_branch,
                    'electron': electron.to_dict(),
                    'hole': hole.to_dict(),
                },
            )
            row['applied'] = True
        if self.bindings:
            projection['composition_policy'] = 'thermal-strain-and-selected-confinement-v1'
        return projection

    def to_dict(self):
        return {
            'schema_version': 'finite-confinement-optical-context-v1',
            'structural_context': self.structural_context.to_dict(),
            'bindings': [binding.to_dict() for binding in self.bindings],
            'resolved': self.projection,
        }

    @classmethod
    def from_dict(cls, data):
        _keys(data, ('schema_version', 'structural_context', 'bindings', 'resolved'))
        if type(data['bindings']) is not list:
            raise ValueError('finite confinement binding archive list required')
        obj = cls(
            StructuralOpticalContext.from_dict(data['structural_context']),
            tuple(FiniteConfinementOpticalBinding.from_dict(binding) for binding in data['bindings']),
        )
        _match(data, obj.to_dict())
        return obj

    def optical_model(self, layer_name):
        """Return an evaluator tied to the resolved row and its source identity."""
        model = self.structural_context.optical_model(layer_name)
        if not any(binding.layer_name == layer_name for binding in self.bindings):
            return model
        row = next(row for row in self.projection['layers'] if row['layer_name'] == layer_name)
        return _FiniteOpticalModel(
            model.baseline_model, model.material_json, _canonical(row), self.contract_hash,
        )
