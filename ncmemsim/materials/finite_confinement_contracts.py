# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Declarations for a single-carrier spherical finite well."""
from dataclasses import dataclass as _dataclass

from ..barrier_contracts import barrier_energy_eV_to_J as _energy_eV_to_J
from .structural import StructuralEvidence as _Evidence, _Archive, _keys, _match
from .temperature import _number, _text

__all__ = ['FiniteConfinementRequest', 'confinement_depth_eV_to_J']

_EVIDENCE_UNITS = {
    'radius_evidence': 'm',
    'inside_mass_evidence': 'm0',
    'outside_mass_evidence': 'm0',
    'depth_evidence': 'J',
}
_FIELDS = (
    'carrier', 'dot_material', 'host_material', 'radius_m',
    'inside_mass_m0', 'outside_mass_m0', 'depth_J', 'temperature_K',
    'radius_evidence', 'inside_mass_evidence', 'outside_mass_evidence',
    'depth_evidence', 'applicability',
)


def confinement_depth_eV_to_J(depth_eV):
    """Convert an explicitly nonnegative carrier confinement depth to joules."""
    return _energy_eV_to_J(_number(depth_eV, 'depth_eV', nonnegative=True))


@_dataclass(frozen=True, slots=True)
class FiniteConfinementRequest(_Archive):
    """Own the inputs and provenance for one isolated ground-state calculation."""

    carrier: str
    dot_material: str
    host_material: str
    radius_m: float
    inside_mass_m0: float
    outside_mass_m0: float
    depth_J: float
    temperature_K: float
    radius_evidence: _Evidence
    inside_mass_evidence: _Evidence
    outside_mass_evidence: _Evidence
    depth_evidence: _Evidence
    applicability: _Evidence

    def __post_init__(self):
        _text(self.carrier, 'carrier')
        if self.carrier not in ('electron', 'hole'):
            raise ValueError('carrier must be electron or hole')
        _text(self.dot_material, 'dot_material')
        _text(self.host_material, 'host_material')
        for field in ('radius_m', 'inside_mass_m0', 'outside_mass_m0', 'temperature_K'):
            object.__setattr__(self, field, _number(getattr(self, field), field, positive=True))
        object.__setattr__(self, 'depth_J', _number(self.depth_J, 'depth_J', nonnegative=True))
        for field, unit in _EVIDENCE_UNITS.items():
            evidence = getattr(self, field)
            if type(evidence) is not _Evidence:
                raise ValueError(field + ' requires StructuralEvidence')
            if evidence.reported_uncertainty is not None and evidence.uncertainty_unit != unit:
                raise ValueError(field + ' uncertainty unit mismatch')
        if type(self.applicability) is not _Evidence:
            raise ValueError('applicability requires StructuralEvidence')
        if self.applicability.reported_uncertainty is not None:
            raise ValueError('record uncertainty on the individual input evidence')

    @property
    def numerical_policy(self):
        """Return a fresh copy of the versioned acceptance policy."""
        return {
            'policy_id': 'finite-spherical-ground-state-numerics-v1',
            'threshold_guard': 1e-12,
            'max_x_bracket_width': 1e-12,
            'max_depth_fraction_bracket_width': 1e-12,
            'max_scaled_matching_residual': 1e-11,
            'max_iterations': 256,
        }

    def to_dict(self):
        raw = {field: getattr(self, field) for field in _FIELDS}
        for field in (*_EVIDENCE_UNITS, 'applicability'):
            raw[field] = raw[field].to_dict()
        return dict(
            raw,
            schema_version='finite-spherical-confinement-request-v1',
            energy_reference={'electron': 'dot_conduction_edge', 'hole': 'dot_hole_edge'}[self.carrier],
            geometry='sphere_in_infinite_homogeneous_host',
            angular_momentum=0,
            interface='ben_daniel_duke_full_radial_envelope',
            outcomes=['bound', 'no_bound_state', 'threshold_unresolved', 'numerical_failure'],
            numerical_policy=self.numerical_policy,
        )

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, (*_FIELDS, 'schema_version', 'energy_reference', 'geometry',
                    'angular_momentum', 'interface', 'outcomes', 'numerical_policy'))
        fields = {field: raw[field] for field in _FIELDS}
        for field in (*_EVIDENCE_UNITS, 'applicability'):
            fields[field] = _Evidence.from_dict(fields[field])
        request = cls(**fields)
        _match(raw, request.to_dict())
        return request
