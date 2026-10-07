# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Separate opt-in structural contracts; no gap evaluation or simulator integration."""
from __future__ import annotations
from dataclasses import dataclass,asdict
import hashlib,json
from .temperature import GapKind,_number,_text
from .provenance import ParameterStatus

__all__=['StructuralEvidence','HydrostaticStrainDomain','ConfinementDomain',
         'HydrostaticGapProfile','SphericalConfinementProfile']


def _keys(data,keys):
    if type(data) is not dict or set(data)!=set(keys):raise ValueError('unsupported structural archive fields')

def _canonical(data):return json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False)

def _unique(items):
    result={}
    for k,v in items:
        if k in result:raise ValueError('duplicate structural JSON key')
        result[k]=v
    return result

def _constant(value):raise ValueError('nonfinite structural JSON value: '+value)

class _Archive:
    def to_json(self):return _canonical(self.to_dict())
    @property
    def contract_hash(self):return hashlib.sha256(self.to_json().encode('utf-8')).hexdigest()
    @classmethod
    def from_json(cls,text):
        if type(text) is not str:raise ValueError('structural JSON text required')
        return cls.from_dict(json.loads(text,object_pairs_hook=_unique,parse_constant=_constant))

def _match(actual,expected):
    if _canonical(actual)!=_canonical(expected):raise ValueError('unsupported structural schema, units or convention')

def _target(value):
    if type(value) is not GapKind or value not in (GapKind.GAMMA,GapKind.L):raise ValueError('Gamma/L optical transition target required')

def _target_raw(value):
    if type(value) is not str:raise ValueError('archived gap kind must be text')
    return GapKind(value)


@dataclass(frozen=True)
class StructuralEvidence(_Archive):
    source: str
    locator: str
    status: ParameterStatus
    notes: str
    doi: str | None = None
    reported_uncertainty: float | None = None
    uncertainty_unit: str | None = None

    def __post_init__(self):
        for name in ('source','locator','notes'):_text(getattr(self,name),name)
        if type(self.status) is not ParameterStatus or self.status is ParameterStatus.CALIBRATED:
            raise ValueError('typed provenance status required; device calibration needs separate qualification')
        if self.doi is not None:_text(self.doi,'doi')
        if (self.reported_uncertainty is None)!=(self.uncertainty_unit is None):raise ValueError('uncertainty value/unit must be supplied together')
        if self.reported_uncertainty is not None:
            object.__setattr__(self,'reported_uncertainty',_number(self.reported_uncertainty,'uncertainty',nonnegative=True))
            _text(self.uncertainty_unit,'uncertainty_unit')

    def to_dict(self):return {'schema_version':'structural-evidence-v1',**asdict(self),'status':self.status.value}
    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','source','locator','status','notes','doi','reported_uncertainty','uncertainty_unit'))
        if type(data['status']) is not str:raise ValueError('archived evidence status must be text')
        obj=cls(data['source'],data['locator'],ParameterStatus(data['status']),data['notes'],data['doi'],data['reported_uncertainty'],data['uncertainty_unit'])
        _match(data,obj.to_dict());return obj


def _domain(owner):
    if type(owner.material) is not str or owner.material!='Ge':raise ValueError('initial structural applicability is Ge only; GeSn requires separate review')
    if type(owner.evidence) is not StructuralEvidence:raise ValueError('typed applicability evidence required')
    for name in ('min_temperature_K','max_temperature_K'):
        object.__setattr__(owner,name,_number(getattr(owner,name),name,positive=True))
    if owner.min_temperature_K>owner.max_temperature_K:raise ValueError('inverted temperature domain')


@dataclass(frozen=True)
class HydrostaticStrainDomain(_Archive):
    material: str
    min_temperature_K: float
    max_temperature_K: float
    min_trace_strain: float
    max_trace_strain: float
    evidence: StructuralEvidence

    def __post_init__(self):
        _domain(self)
        for name in ('min_trace_strain','max_trace_strain'):object.__setattr__(self,name,_number(getattr(self,name),name))
        if not self.min_trace_strain<=0<=self.max_trace_strain:raise ValueError('hydrostatic domain must include the zero-strain anchor')

    def validate_point(self,*,temperature_K,trace_strain):
        t=_number(temperature_K,'temperature',positive=True);strain=_number(trace_strain,'trace strain')
        if not self.min_temperature_K<=t<=self.max_temperature_K or not self.min_trace_strain<=strain<=self.max_trace_strain:
            raise ValueError('point outside hydrostatic applicability domain')

    def to_dict(self):
        return {'schema_version':'hydrostatic-strain-domain-v1',**asdict(self),'evidence':self.evidence.to_dict(),
            'strain_coordinate':'trace_epsilon','strain_unit':'dimensionless','sign_convention':'positive_tensile'}
    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','material','min_temperature_K','max_temperature_K','min_trace_strain','max_trace_strain','evidence','strain_coordinate','strain_unit','sign_convention'))
        obj=cls(data['material'],data['min_temperature_K'],data['max_temperature_K'],data['min_trace_strain'],data['max_trace_strain'],StructuralEvidence.from_dict(data['evidence']))
        _match(data,obj.to_dict());return obj


@dataclass(frozen=True)
class ConfinementDomain(_Archive):
    material: str
    min_temperature_K: float
    max_temperature_K: float
    min_radius_m: float
    max_radius_m: float
    evidence: StructuralEvidence

    def __post_init__(self):
        _domain(self)
        for name in ('min_radius_m','max_radius_m'):object.__setattr__(self,name,_number(getattr(self,name),name,positive=True))
        if self.min_radius_m>self.max_radius_m:raise ValueError('inverted radius domain')

    def validate_point(self,*,temperature_K,radius_m):
        t=_number(temperature_K,'temperature',positive=True);radius=_number(radius_m,'radius',positive=True)
        if not self.min_temperature_K<=t<=self.max_temperature_K or not self.min_radius_m<=radius<=self.max_radius_m:
            raise ValueError('point outside confinement applicability domain')

    def to_dict(self):return {'schema_version':'confinement-domain-v1',**asdict(self),'evidence':self.evidence.to_dict(),'size_coordinate':'radius','size_unit':'m'}
    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','material','min_temperature_K','max_temperature_K','min_radius_m','max_radius_m','evidence','size_coordinate','size_unit'))
        obj=cls(data['material'],data['min_temperature_K'],data['max_temperature_K'],data['min_radius_m'],data['max_radius_m'],StructuralEvidence.from_dict(data['evidence']))
        _match(data,obj.to_dict());return obj


@dataclass(frozen=True)
class HydrostaticGapProfile(_Archive):
    name: str
    layer_name: str
    gap_kind: GapKind
    domain: HydrostaticStrainDomain
    gap_coefficient_eV_per_trace: float
    coefficient_evidence: StructuralEvidence

    def __post_init__(self):
        _text(self.name,'name');_text(self.layer_name,'layer_name');_target(self.gap_kind)
        if type(self.domain) is not HydrostaticStrainDomain or type(self.coefficient_evidence) is not StructuralEvidence:raise ValueError('typed hydrostatic domain/coefficient evidence required')
        object.__setattr__(self,'gap_coefficient_eV_per_trace',_number(self.gap_coefficient_eV_per_trace,'gap coefficient'))
        if self.coefficient_evidence.reported_uncertainty is not None and self.coefficient_evidence.uncertainty_unit!='eV_per_unit_trace':raise ValueError('coefficient uncertainty unit mismatch')

    def to_dict(self):
        return {'schema_version':'hydrostatic-gap-profile-v1','name':self.name,'layer_name':self.layer_name,'gap_kind':self.gap_kind.value,
            'domain':self.domain.to_dict(),'gap_coefficient_eV_per_trace':self.gap_coefficient_eV_per_trace,
            'coefficient_evidence':self.coefficient_evidence.to_dict(),'coefficient_unit':'eV_per_unit_trace',
            'coefficient_semantics':'optical_transition_gap_derivative','law_id':'hydrostatic-linear-gap-v1'}
    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','name','layer_name','gap_kind','domain','gap_coefficient_eV_per_trace','coefficient_evidence','coefficient_unit','coefficient_semantics','law_id'))
        obj=cls(data['name'],data['layer_name'],_target_raw(data['gap_kind']),HydrostaticStrainDomain.from_dict(data['domain']),
            data['gap_coefficient_eV_per_trace'],StructuralEvidence.from_dict(data['coefficient_evidence']))
        _match(data,obj.to_dict());return obj


@dataclass(frozen=True)
class SphericalConfinementProfile(_Archive):
    name: str
    layer_name: str
    gap_kind: GapKind
    hole_branch: str
    domain: ConfinementDomain
    electron_mass_m0: float
    hole_mass_m0: float
    electron_mass_evidence: StructuralEvidence
    hole_mass_evidence: StructuralEvidence
    approximation_evidence: StructuralEvidence

    def __post_init__(self):
        _text(self.name,'name');_text(self.layer_name,'layer_name');_target(self.gap_kind)
        if type(self.hole_branch) is not str or self.hole_branch not in {'heavy_hole','light_hole','effective_scalar'}:raise ValueError('explicit hole branch/equivalent scalar mass required')
        if type(self.domain) is not ConfinementDomain:raise ValueError('typed radius applicability domain required')
        for name in ('electron_mass_m0','hole_mass_m0'):object.__setattr__(self,name,_number(getattr(self,name),name,positive=True))
        for name in ('electron_mass_evidence','hole_mass_evidence','approximation_evidence'):
            e=getattr(self,name)
            if type(e) is not StructuralEvidence:raise ValueError('typed mass/approximation evidence required')
            if name!='approximation_evidence' and e.reported_uncertainty is not None and e.uncertainty_unit!='m0':raise ValueError('mass uncertainty unit mismatch')

    def to_dict(self):
        return {'schema_version':'spherical-confinement-profile-v1','name':self.name,'layer_name':self.layer_name,'gap_kind':self.gap_kind.value,
            'hole_branch':self.hole_branch,'domain':self.domain.to_dict(),'electron_mass_m0':self.electron_mass_m0,'hole_mass_m0':self.hole_mass_m0,
            'electron_mass_evidence':self.electron_mass_evidence.to_dict(),'hole_mass_evidence':self.hole_mass_evidence.to_dict(),
            'approximation_evidence':self.approximation_evidence.to_dict(),'mass_unit':'m0','geometry':'spherical',
            'barrier_model':'infinite','mass_basis':'isotropic_equivalent','interaction_terms':'kinetic_only',
            'law_id':'spherical-infinite-barrier-ema-kinetic-v1'}
    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','name','layer_name','gap_kind','hole_branch','domain','electron_mass_m0','hole_mass_m0',
            'electron_mass_evidence','hole_mass_evidence','approximation_evidence','mass_unit','geometry','barrier_model','mass_basis','interaction_terms','law_id'))
        obj=cls(data['name'],data['layer_name'],_target_raw(data['gap_kind']),data['hole_branch'],ConfinementDomain.from_dict(data['domain']),
            data['electron_mass_m0'],data['hole_mass_m0'],StructuralEvidence.from_dict(data['electron_mass_evidence']),
            StructuralEvidence.from_dict(data['hole_mass_evidence']),StructuralEvidence.from_dict(data['approximation_evidence']))
        _match(data,obj.to_dict());return obj
