# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Standalone optical transition-gap shifts induced by hydrostatic strain."""
from __future__ import annotations
from dataclasses import dataclass
from .structural import (HydrostaticStrainGapShiftProfile,StructuralEvidence,_Archive,
                         _keys,_match,_number)

__all__=['HydrostaticStrainGapShiftResult','evaluate_hydrostatic_strain_gap_shift']


def _shift(profile,trace):
    coefficient=profile.gap_deformation_potential_eV_per_trace
    if coefficient==0 or trace==0:return 0.0
    shift=_number(coefficient*trace,'hydrostatic strain-induced gap shift')
    if shift==0:raise ValueError('nonzero gap shift underflows the numerical representation')
    return shift


@dataclass(frozen=True)
class HydrostaticStrainGapShiftResult(_Archive):
    """Explicit unstrained baseline and signed shift; no band-offset inference.

    The supplied unstrained gap is at temperature_K. This evaluator does not
    calculate its thermal dependence or bind an actual device/material layer.
    """
    profile: HydrostaticStrainGapShiftProfile
    unstrained_gap_eV: float
    unstrained_gap_evidence: StructuralEvidence
    temperature_K: float
    trace_strain: float

    def __post_init__(self):
        if type(self.profile) is not HydrostaticStrainGapShiftProfile or type(self.unstrained_gap_evidence) is not StructuralEvidence:
            raise ValueError('typed profile and unstrained-gap evidence required')
        for name in ('unstrained_gap_eV','temperature_K','trace_strain'):
            object.__setattr__(self,name,_number(getattr(self,name),name,positive=name!='trace_strain'))
        if self.unstrained_gap_evidence.reported_uncertainty is not None and self.unstrained_gap_evidence.uncertainty_unit!='eV':
            raise ValueError('unstrained-gap uncertainty must use eV')
        self.profile.domain.validate_point(temperature_K=self.temperature_K,trace_strain=self.trace_strain)
        _number(self.unstrained_gap_eV+self.gap_shift_eV,'shifted optical transition gap',positive=True)

    @property
    def gap_shift_eV(self):return _shift(self.profile,self.trace_strain)

    @property
    def shifted_gap_eV(self):
        return self.unstrained_gap_eV if self.gap_shift_eV==0 else self.unstrained_gap_eV+self.gap_shift_eV

    def to_dict(self):
        return {'schema_version':'hydrostatic-strain-gap-shift-result-v1',
            'profile':self.profile.to_dict(),'profile_hash':self.profile.contract_hash,
            'unstrained_gap_eV':self.unstrained_gap_eV,'unstrained_gap_evidence':self.unstrained_gap_evidence.to_dict(),
            'temperature_K':self.temperature_K,'trace_strain':self.trace_strain,'energy_unit':'eV',
            'strain_coordinate':'trace_epsilon','strain_unit':'dimensionless','sign_convention':'positive_tensile',
            'gap_shift_eV':self.gap_shift_eV,'shifted_gap_eV':self.shifted_gap_eV}

    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','profile','profile_hash','unstrained_gap_eV','unstrained_gap_evidence',
            'temperature_K','trace_strain','energy_unit','strain_coordinate','strain_unit','sign_convention',
            'gap_shift_eV','shifted_gap_eV'))
        obj=cls(HydrostaticStrainGapShiftProfile.from_dict(data['profile']),data['unstrained_gap_eV'],
            StructuralEvidence.from_dict(data['unstrained_gap_evidence']),data['temperature_K'],data['trace_strain'])
        _match(data,obj.to_dict());return obj


def evaluate_hydrostatic_strain_gap_shift(profile: HydrostaticStrainGapShiftProfile,*,unstrained_gap_eV: float,
                                         unstrained_gap_evidence: StructuralEvidence,temperature_K: float,
                                         trace_strain: float) -> HydrostaticStrainGapShiftResult:
    """Evaluate delta Eg = gap deformation potential * Tr(epsilon), without mutation."""
    return HydrostaticStrainGapShiftResult(profile,unstrained_gap_eV,unstrained_gap_evidence,temperature_K,trace_strain)
