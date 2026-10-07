# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Kinetic optical-gap shifts for a spherical infinite-barrier EMA diagnostic."""
from __future__ import annotations
from dataclasses import dataclass
import math
from ..constants import PLANCK_J_S,ELECTRON_MASS_KG,ELEMENTARY_CHARGE_C
from .structural import SphericalConfinementProfile,StructuralEvidence,_Archive,_number,_keys,_match

__all__=['SphericalKineticConfinementGapShiftResult','evaluate_spherical_kinetic_confinement_gap_shift']


def _energy_eV(mass_m0,radius_m):
    # pi^2*hbar^2/(2*m*R^2) = h^2/(8*m*R^2). Relative masses use m0.
    coefficient=PLANCK_J_S**2/(8*ELECTRON_MASS_KG*ELEMENTARY_CHARGE_C)
    c,ec=math.frexp(coefficient);m,em=math.frexp(mass_m0);r,er=math.frexp(radius_m)
    try:value=math.ldexp(c/(m*r*r),ec-em-2*er)
    except OverflowError as exc:raise ValueError('individual confinement energy overflows the numerical representation') from exc
    value=_number(value,'individual kinetic confinement energy',positive=True)
    return value


@dataclass(frozen=True)
class SphericalKineticConfinementGapShiftResult(_Archive):
    """Explicit electron/hole kinetic contributions; no interaction or barrier inference."""
    profile: SphericalConfinementProfile
    unconfined_gap_eV: float
    unconfined_gap_evidence: StructuralEvidence
    temperature_K: float
    radius_m: float

    def __post_init__(self):
        if type(self.profile) is not SphericalConfinementProfile or type(self.unconfined_gap_evidence) is not StructuralEvidence:
            raise ValueError('typed confinement profile and unconfined-gap evidence required')
        for name in ('unconfined_gap_eV','temperature_K','radius_m'):
            object.__setattr__(self,name,_number(getattr(self,name),name,positive=True))
        if self.unconfined_gap_evidence.reported_uncertainty is not None and self.unconfined_gap_evidence.uncertainty_unit!='eV':raise ValueError('unconfined-gap uncertainty must use eV')
        self.profile.domain.validate_point(temperature_K=self.temperature_K,radius_m=self.radius_m)
        _number(self.confined_gap_eV,'confined optical transition gap',positive=True)

    @property
    def electron_confinement_energy_eV(self):return _energy_eV(self.profile.electron_mass_m0,self.radius_m)
    @property
    def hole_confinement_energy_eV(self):return _energy_eV(self.profile.hole_mass_m0,self.radius_m)
    @property
    def kinetic_gap_shift_eV(self):
        try:value=math.fsum((self.electron_confinement_energy_eV,self.hole_confinement_energy_eV))
        except OverflowError as exc:raise ValueError('total kinetic confinement shift is not representable') from exc
        return _number(value,'total kinetic gap shift',positive=True)
    @property
    def confined_gap_eV(self):return self.unconfined_gap_eV+self.kinetic_gap_shift_eV

    def to_dict(self):
        return {'schema_version':'spherical-kinetic-confinement-gap-shift-result-v1','profile':self.profile.to_dict(),
            'profile_hash':self.profile.contract_hash,'unconfined_gap_eV':self.unconfined_gap_eV,
            'unconfined_gap_evidence':self.unconfined_gap_evidence.to_dict(),'temperature_K':self.temperature_K,'radius_m':self.radius_m,
            'size_coordinate':'radius','size_unit':'m','mass_unit':'m0','energy_unit':'eV',
            'constants':{'planck_J_s':PLANCK_J_S,'electron_mass_kg':ELECTRON_MASS_KG,'elementary_charge_C':ELEMENTARY_CHARGE_C},
            'electron_confinement_energy_eV':self.electron_confinement_energy_eV,'hole_confinement_energy_eV':self.hole_confinement_energy_eV,
            'kinetic_gap_shift_eV':self.kinetic_gap_shift_eV,'confined_gap_eV':self.confined_gap_eV}

    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','profile','profile_hash','unconfined_gap_eV','unconfined_gap_evidence','temperature_K','radius_m',
            'size_coordinate','size_unit','mass_unit','energy_unit','constants','electron_confinement_energy_eV',
            'hole_confinement_energy_eV','kinetic_gap_shift_eV','confined_gap_eV'))
        obj=cls(SphericalConfinementProfile.from_dict(data['profile']),data['unconfined_gap_eV'],
            StructuralEvidence.from_dict(data['unconfined_gap_evidence']),data['temperature_K'],data['radius_m'])
        _match(data,obj.to_dict());return obj


def evaluate_spherical_kinetic_confinement_gap_shift(profile: SphericalConfinementProfile,*,unconfined_gap_eV: float,
    unconfined_gap_evidence: StructuralEvidence,temperature_K: float,radius_m: float) -> SphericalKineticConfinementGapShiftResult:
    """Evaluate only kinetic confinement; radius and masses are explicit, never inferred."""
    return SphericalKineticConfinementGapShiftResult(profile,unconfined_gap_eV,unconfined_gap_evidence,temperature_K,radius_m)
