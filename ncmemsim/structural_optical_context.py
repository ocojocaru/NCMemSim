# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Owned opt-in structural optical composition with thermal and spectral contexts."""
from __future__ import annotations
from dataclasses import dataclass,replace
import json,math
from .temperature_context import ResolvedThermalContext
from .materials.structural import (HydrostaticStrainGapShiftProfile,SphericalConfinementProfile,
    StructuralEvidence,_Archive,_keys,_match,_number,_text)
from .materials.structural_strain import evaluate_hydrostatic_strain_gap_shift
from .materials.structural_confinement import evaluate_spherical_kinetic_confinement_gap_shift
from .materials.temperature import GapKind
from .materials.provenance import ParameterStatus,ParameterProvenance
from .materials.optics.models import (OpticalPoint,GeSnAbsorptionParameterSet,photon_energy_eV,
    direct_absorption_m_inv,indirect_absorption_m_inv,urbach_absorption_m_inv,
    ABSORPTION_MODEL_PROVENANCE,ABSORPTION_COEFFICIENT_PROVENANCE,PHONON_OCCUPATION_PROVENANCE)
from .spectral_sources import TabulatedSpectrum,DiscreteLineSpectrum,_canonical
from .spectral_context import SpectralSimulationContext,SpectralSimulator
from .spectral_stack import SpectralStackLayer,bind_spectral_stack_path,evaluate_spectral_stack
from .spectral_absorption import evaluate_floating_gate_spectrum

__all__=['StructuralOpticalBinding','StructuralOpticalContext','StructuralSpectralContext',
    'StructuralSpectralSimulator','build_structural_spectral_context','run_structural_spectral_program_pulse_read']


@dataclass(frozen=True)
class StructuralOpticalBinding(_Archive):
    layer_name: str
    strain_profiles: tuple[HydrostaticStrainGapShiftProfile, ...]
    confinement_profiles: tuple[SphericalConfinementProfile, ...]
    trace_strain: float
    enabled: bool = True

    def __post_init__(self):
        _text(self.layer_name,'layer_name')
        object.__setattr__(self,'trace_strain',_number(self.trace_strain,'trace strain'))
        if type(self.enabled) is not bool:raise ValueError('boolean structural mode required')
        for name,kind in (('strain_profiles',HydrostaticStrainGapShiftProfile),('confinement_profiles',SphericalConfinementProfile)):
            profiles=getattr(self,name)
            if type(profiles) is not tuple or any(type(p) is not kind for p in profiles):raise ValueError('immutable typed structural profile tuples required')
            if len({p.gap_kind for p in profiles})!=len(profiles):raise ValueError('duplicate target within a structural mechanism')
            if any(p.layer_name!=self.layer_name for p in profiles):raise ValueError('profile attached to a different FG')
            object.__setattr__(self,name,tuple(sorted(profiles,key=lambda p:p.gap_kind.value)))
        if self.enabled and not (self.strain_profiles or self.confinement_profiles):raise ValueError('enabled structural binding requires a mechanism')

    def to_dict(self):return {'schema_version':'structural-optical-binding-v1','layer_name':self.layer_name,
        'strain_profiles':[p.to_dict() for p in self.strain_profiles],'confinement_profiles':[p.to_dict() for p in self.confinement_profiles],
        'trace_strain':self.trace_strain,'enabled':self.enabled}
    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','layer_name','strain_profiles','confinement_profiles','trace_strain','enabled'))
        if any(type(data[k]) is not list for k in ('strain_profiles','confinement_profiles')):raise ValueError('profile archive lists required')
        obj=cls(data['layer_name'],tuple(HydrostaticStrainGapShiftProfile.from_dict(p) for p in data['strain_profiles']),
            tuple(SphericalConfinementProfile.from_dict(p) for p in data['confinement_profiles']),data['trace_strain'],data['enabled'])
        _match(data,obj.to_dict());return obj


@dataclass(frozen=True)
class StructuralOpticalContext(_Archive):
    thermal_resolution: ResolvedThermalContext
    bindings: tuple[StructuralOpticalBinding, ...]

    def __post_init__(self):
        if type(self.thermal_resolution) is not ResolvedThermalContext or type(self.bindings) is not tuple or any(type(b) is not StructuralOpticalBinding for b in self.bindings):raise ValueError('typed resolved thermal owner and binding tuple required')
        names=[b.layer_name for b in self.bindings]
        if len(set(names))!=len(names):raise ValueError('duplicate structural FG attachment')
        if not set(names)<={fg.name for fg in self.thermal_resolution.device.floating_gates()}:raise ValueError('unknown structural FG attachment')
        object.__setattr__(self,'bindings',tuple(sorted(self.bindings,key=lambda b:b.layer_name)))
        self.projection

    @property
    def projection(self):
        resolution=self.thermal_resolution;device=resolution.device;rows=[]
        attached={b.layer_name:b for b in self.bindings}
        baselines=resolution.to_dict()['resolved']['optical']
        for baseline in baselines:
            fg=device.get_layer(baseline['layer_name']);b=attached.get(fg.name);active=b is not None and b.enabled
            if active and (fg.nc_material.sn_fraction!=0 or fg.nc_material.model_name!='GeModel'):raise ValueError('enabled structural optical composition requires the declared Ge material model')
            radius=fg.nc_diameter_nm*.5e-9
            targets={}
            for kind,key in ((GapKind.GAMMA,'gamma_gap_eV'),(GapKind.L,'l_gap_eV')):
                gap=baseline[key];strain=None;confinement=None
                if active:
                    _number(gap,'thermal optical baseline gap',positive=True)
                    evidence=StructuralEvidence('Resolved M optical baseline',resolution.context_hash+'/'+fg.name+'/'+kind.value,
                        ParameterStatus.DERIVED,'Gap already resolved at the sole device temperature; no second thermal correction')
                    p=next((p for p in b.strain_profiles if p.gap_kind is kind),None)
                    if p is not None:strain=evaluate_hydrostatic_strain_gap_shift(p,unstrained_gap_eV=gap,unstrained_gap_evidence=evidence,
                        temperature_K=resolution.temperature_K,trace_strain=b.trace_strain).to_dict()
                    p=next((p for p in b.confinement_profiles if p.gap_kind is kind),None)
                    if p is not None:confinement=evaluate_spherical_kinetic_confinement_gap_shift(p,unconfined_gap_eV=gap,
                        unconfined_gap_evidence=evidence,temperature_K=resolution.temperature_K,radius_m=radius).to_dict()
                ds=0. if strain is None else strain['gap_shift_eV'];dc=0. if confinement is None else confinement['kinetic_gap_shift_eV']
                try:total=gap if ds==dc==0 else math.fsum((gap,ds,dc))
                except OverflowError as exc:raise ValueError('combined optical gap is not representable') from exc
                if active:_number(total,'combined optical gap',positive=True)
                targets[kind.value]={'thermal_baseline_gap_eV':gap,'strain_gap_shift_eV':ds,'kinetic_confinement_gap_shift_eV':dc,
                    'resolved_gap_eV':total,'strain_result':strain,'confinement_result':confinement}
            rows.append({'layer_name':fg.name,'applied':active,'radius_m_from_device':radius,'targets':targets,'thermal_optical_row':baseline})
        return {'composition_policy':'thermal-baseline-plus-independent-structural-shifts-assumed-v1','temperature_K':resolution.temperature_K,'layers':rows}

    def to_dict(self):return {'schema_version':'structural-optical-context-v1','thermal_resolution':self.thermal_resolution.to_dict(),
        'bindings':[b.to_dict() for b in self.bindings],'resolved':self.projection}
    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','thermal_resolution','bindings','resolved'))
        if type(data['bindings']) is not list:raise ValueError('binding archive list required')
        obj=cls(ResolvedThermalContext.from_dict(data['thermal_resolution']),tuple(StructuralOpticalBinding.from_dict(b) for b in data['bindings']))
        _match(data,obj.to_dict());return obj

    def optical_model(self,layer_name):
        rows={r['layer_name']:r for r in self.projection['layers']}
        if layer_name not in rows:raise ValueError('unknown FG optical evaluator')
        return _StructuralOpticalModel(self.thermal_resolution.optical_model(layer_name),
            _canonical(self.thermal_resolution.device.get_layer(layer_name).nc_material.to_dict()),_canonical(rows[layer_name]),self.contract_hash)


@dataclass(frozen=True)
class _StructuralOpticalModel:
    baseline_model: object
    material_json: str
    row_json: str
    context_hash: str

    def evaluate(self,material,wavelength_nm):
        if _canonical(material.to_dict())!=self.material_json:raise ValueError('optical material differs from its owned structural context')
        row=json.loads(self.row_json)
        if not row['applied']:return self.baseline_model.evaluate(material,wavelength_nm)
        gamma=row['targets'][GapKind.GAMMA.value]['resolved_gap_eV'];l_gap=row['targets'][GapKind.L.value]['resolved_gap_eV']
        base=row['thermal_optical_row']
        provenance=ParameterProvenance('O4 additive optical gap composition',ParameterStatus.ASSUMED,
            notes=self.row_json,parameter_set=self.context_hash)
        if gamma==base['gamma_gap_eV'] and l_gap==base['l_gap_eV']:
            point=self.baseline_model.evaluate(material,wavelength_nm)
            return replace(point,provenance={**(point.provenance or {}),'structural_composition':provenance})
        wavelength=_number(wavelength_nm,'wavelength',positive=True);energy=_number(photon_energy_eV(wavelength),'photon energy',positive=True)
        parameters=GeSnAbsorptionParameterSet(**base['absorption_parameters'])
        try:
            direct=direct_absorption_m_inv(energy,gamma,parameters);indirect=indirect_absorption_m_inv(energy,l_gap,parameters);urbach=urbach_absorption_m_inv(energy,gamma,parameters)
        except (OverflowError,ZeroDivisionError) as exc:raise ValueError('structural optical absorption is not representable') from exc
        for name,value in (('direct',direct),('indirect',indirect),('Urbach',urbach)):_number(value,name+' absorption',nonnegative=True)
        total=_number(direct+indirect+urbach,'total absorption',nonnegative=True)
        return OpticalPoint(wavelength,energy,total,direct_gap_eV=gamma,indirect_gap_eV=l_gap,
            alpha_direct_m_inv=direct,alpha_indirect_m_inv=indirect,alpha_urbach_m_inv=urbach,
            provenance={'model_form':ABSORPTION_MODEL_PROVENANCE,'coefficients':ABSORPTION_COEFFICIENT_PROVENANCE,
                'phonon_occupation':PHONON_OCCUPATION_PROVENANCE,'structural_composition':provenance})


@dataclass(frozen=True)
class StructuralSpectralContext(_Archive):
    structural_context: StructuralOpticalContext
    spectral_context: SpectralSimulationContext

    def __post_init__(self):
        if type(self.structural_context) is not StructuralOpticalContext or type(self.spectral_context) is not SpectralSimulationContext:raise ValueError('typed structural and spectral contexts required')
        _match(self.structural_context.thermal_resolution.to_dict(),self.spectral_context.resolution.to_dict())
        rows={r['layer_name']:r for r in self.structural_context.projection['layers']}
        for layer in self.spectral_context.optical_result.path.layers:
            if layer.role!='floating_gate':continue
            if len(layer.profile.node_details_json)!=len(layer.profile.wavelength_nm):raise ValueError('complete FG samples and structural identities required')
            for text in layer.profile.node_details_json:
                node=json.loads(text);row=rows[layer.profile.layer_name]
                expected_id=self.structural_context.contract_hash+'/'+layer.profile.layer_name
                if node['model_identity']!=expected_id or node['direct_gap_eV']!=row['targets'][GapKind.GAMMA.value]['resolved_gap_eV'] or node['indirect_gap_eV']!=row['targets'][GapKind.L.value]['resolved_gap_eV']:
                    raise ValueError('stale spectral samples or gap/context identities')

    def to_dict(self):return {'schema_version':'structural-spectral-context-v1','structural_context':self.structural_context.to_dict(),'spectral_context':self.spectral_context.to_dict()}
    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','structural_context','spectral_context'))
        obj=cls(StructuralOpticalContext.from_dict(data['structural_context']),SpectralSimulationContext.from_dict(data['spectral_context']))
        _match(data,obj.to_dict());return obj
    def create_simulator(self):return StructuralSpectralSimulator(self)


class StructuralSpectralSimulator(SpectralSimulator):
    def __init__(self,context: StructuralSpectralContext):
        if type(context) is not StructuralSpectralContext:raise ValueError('typed structural/spectral owner required')
        self._structural_context=context
        super().__init__(context.spectral_context)
    def relax_voltage(self,state,gate_voltage_V,dwell_time_s=None,internal_dt_s=None,light_source=None,
                      photo_config=None,photo_weights=None,occupancy_integrator='explicit_euler'):
        result=super().relax_voltage(state,gate_voltage_V,dwell_time_s,internal_dt_s,light_source,photo_config,photo_weights,occupancy_integrator)
        result['structural_context_hash']=self._structural_context.structural_context.contract_hash
        result['structural_optical_context']=self._structural_context.structural_context.to_dict()
        return result


def build_structural_spectral_context(context,source,*,direction: str,passive_layers: tuple,
                                     wavelength_min_nm: float,wavelength_max_nm: float,evidence):
    if type(context) is not StructuralOpticalContext or type(source) not in (TabulatedSpectrum,DiscreteLineSpectrum) or type(passive_layers) is not tuple:
        raise ValueError('typed structural context/source and passive tuple required')
    if any(type(p) is not SpectralStackLayer or p.role!='passive' for p in passive_layers):raise ValueError('explicit passive entries required')
    device=context.thermal_resolution.device;names=[p.profile.layer_name for p in passive_layers]
    if len(set(names))!=len(names) or set(names)!={x.name for x in device.layers if x.role!='floating_gate'}:raise ValueError('every passive layer must be supplied exactly once')
    passive={p.profile.layer_name:p for p in passive_layers};layers=[]
    for layer in device.layers:
        if layer.role!='floating_gate':layers.append(passive[layer.name]);continue
        point=evaluate_floating_gate_spectrum(source,layer,optical_model=context.optical_model(layer.name),
            model_identity=context.contract_hash+'/'+layer.name,wavelength_min_nm=wavelength_min_nm,wavelength_max_nm=wavelength_max_nm,evidence=evidence)
        layers.append(SpectralStackLayer(point.profile,'floating_gate'))
    path=bind_spectral_stack_path(device,tuple(layers),direction=direction,evidence=evidence)
    spectral=SpectralSimulationContext(context.thermal_resolution,evaluate_spectral_stack(source,path))
    return StructuralSpectralContext(context,spectral)


def run_structural_spectral_program_pulse_read(context: StructuralSpectralContext,protocol,*,photo_config,initial_state=None):
    """Retain the complete structural owner around the unchanged N4 pulse workflow."""
    from .spectral_context import run_spectral_program_pulse_read
    if type(context) is not StructuralSpectralContext:raise ValueError('typed structural/spectral context required')
    run=run_spectral_program_pulse_read(context.spectral_context,protocol,photo_config=photo_config,initial_state=initial_state)
    return {'workflow':'structural-spectral-program-pulse-dark-read-v1','context':context.to_dict(),
        'context_hash':context.contract_hash,'structural_context_hash':context.structural_context.contract_hash,'spectral_run':run}
