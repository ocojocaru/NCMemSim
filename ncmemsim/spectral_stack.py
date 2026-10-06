# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Explicit single-pass ordered spectral paths; no reflection or simulator integration."""
from __future__ import annotations
from dataclasses import dataclass
import json
import math

from .spectral_sources import (SpectralEvidence, TabulatedSpectrum, DiscreteLineSpectrum,
    _Archive, _keys, _canonical)
from .spectral_absorption import SpectralAbsorptionProfile, evaluate_spectral_absorption, _json_object

__all__ = ["SpectralStackLayer", "SpectralStackPath", "SpectralStackResult",
           "bind_spectral_stack_path", "evaluate_spectral_stack"]


@dataclass(frozen=True)
class SpectralStackLayer(_Archive):
    profile: SpectralAbsorptionProfile
    role: str
    treatment: str = "absorbing"

    def __post_init__(self):
        if type(self.profile) is not SpectralAbsorptionProfile or type(self.role) is not str or self.role not in {'floating_gate','passive'}:
            raise ValueError('typed profile and explicit floating_gate/passive role required')
        if type(self.treatment) is not str or self.treatment not in {'absorbing','assumed_transparent'}:
            raise ValueError('unsupported layer optical treatment')
        if self.treatment=='assumed_transparent' and (self.role!='passive' or self.profile.evidence.status!='ASSUMED' or any(self.profile.effective_alpha_m_inv)):
            raise ValueError('transparent passive layer requires explicit ASSUMED evidence and zero alpha')
        if self.role=='passive' and self.profile.node_details_json:
            raise ValueError('floating-gate node records cannot describe a passive layer')

    def to_dict(self):
        return {'schema_version':'spectral-stack-layer-v1','profile':self.profile.to_dict(),
                'role':self.role,'treatment':self.treatment}

    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','profile','role','treatment'))
        if data['schema_version']!='spectral-stack-layer-v1':raise ValueError('unsupported layer schema')
        return cls(SpectralAbsorptionProfile.from_dict(data['profile']),data['role'],data['treatment'])


@dataclass(frozen=True)
class SpectralStackPath(_Archive):
    """Layers are stored in substrate-to-gate physical order; direction selects traversal.

    Unbound paths describe only the listed optical layers. Device-bound paths
    require exactly every device layer, with matching roles and thicknesses.
    """
    layers: tuple[SpectralStackLayer, ...]
    direction: str
    evidence: SpectralEvidence
    device_snapshot_json: str | None = None

    def __post_init__(self):
        if type(self.layers) is not tuple or not self.layers or any(type(x) is not SpectralStackLayer for x in self.layers):
            raise ValueError('nonempty immutable optical path required')
        if type(self.direction) is not str or self.direction not in {'substrate_to_gate','gate_to_substrate'}:
            raise ValueError('explicit illumination direction required')
        if type(self.evidence) is not SpectralEvidence:raise ValueError('typed path evidence required')
        names=[x.profile.layer_name for x in self.layers]
        if len(set(names))!=len(names):raise ValueError('duplicate optical layer identity')
        if sum(x.role=='floating_gate' for x in self.layers)>3:raise ValueError('at most three floating gates supported')
        if any(x.profile.wavelength_nm!=self.layers[0].profile.wavelength_nm for x in self.layers):
            raise ValueError('path profiles require a common spectral grid')
        if self.device_snapshot_json is not None:
            object.__setattr__(self,'device_snapshot_json',_json_object(self.device_snapshot_json))
            raw=json.loads(self.device_snapshot_json)
            rows=raw.get('layers')
            if type(rows) is not list or any(type(x) is not dict for x in rows) or [x.get('name') for x in rows]!=names:
                raise ValueError('device path must cover every layer in stored device order')
            for entry,row in zip(self.layers,rows):
                from .spectral_sources import _number
                thickness=_number(row.get('thickness_nm'),'device thickness',positive=True)*1e-9
                role='floating_gate' if row.get('type')=='floating_gate' else 'passive' if row.get('type')=='layer' else None
                if entry.role!=role or entry.profile.thickness_m!=thickness:
                    raise ValueError('optical path role/thickness differs from device')
                for text in entry.profile.node_details_json:
                    if json.loads(text)['layer_snapshot']!=row:
                        raise ValueError('FG profile belongs to a different device layer')

    @property
    def traversal(self):
        return self.layers if self.direction=='substrate_to_gate' else tuple(reversed(self.layers))

    def to_dict(self):
        return {'schema_version':'spectral-stack-path-v1','physical_order':'substrate_to_gate',
            'layers':[x.to_dict() for x in self.layers],'direction':self.direction,
            'evidence':self.evidence.to_dict(),'device_snapshot':json.loads(self.device_snapshot_json) if self.device_snapshot_json is not None else None}

    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','physical_order','layers','direction','evidence','device_snapshot'))
        if data['schema_version']!='spectral-stack-path-v1' or data['physical_order']!='substrate_to_gate' or type(data['layers']) is not list:
            raise ValueError('unsupported path schema/order')
        return cls(tuple(SpectralStackLayer.from_dict(x) for x in data['layers']),data['direction'],
            SpectralEvidence.from_dict(data['evidence']),_canonical(data['device_snapshot']) if data['device_snapshot'] is not None else None)


def bind_spectral_stack_path(device,layers,*,direction: str,evidence: SpectralEvidence):
    """Bind all ordered device layers; no automatic transparent-material assumption."""
    from .device import Device
    from copy import deepcopy
    if type(device) is not Device:raise ValueError('typed device required')
    owned=deepcopy(device);owned.validate()
    return SpectralStackPath(layers,direction,evidence,_canonical(owned.to_dict()))


def _propagate(source,path):
    if type(source) not in (TabulatedSpectrum,DiscreteLineSpectrum) or type(path) is not SpectralStackPath:
        raise ValueError('typed spectral source and optical path required')
    current=source;rows=[]
    for layer in path.traversal:
        result=evaluate_spectral_absorption(current,layer.profile)
        summary=result.summary
        row={'layer_name':layer.profile.layer_name,'role':layer.role,'treatment':layer.treatment,
             'absorption':result.to_dict(),
             'nc_absorbed_photon_flux_m2_s':summary['absorbed_photon_flux_m2_s'] if layer.role=='floating_gate' else None}
        rows.append(row)
        remaining=tuple(summary['transmitted_samples'])
        # Resolved transmitted densities/line powers are absolute: never normalize again.
        current=(TabulatedSpectrum(source.wavelength_nm,remaining,source.evidence) if type(source) is TabulatedSpectrum
                 else DiscreteLineSpectrum(source.wavelength_nm,remaining,source.evidence))
    absorbed_power=math.fsum(x['absorption']['summary']['absorbed_irradiance_W_m2'] for x in rows)
    absorbed_photons=math.fsum(x['absorption']['summary']['absorbed_photon_flux_m2_s'] for x in rows)
    ip=source.in_band_irradiance_W_m2;iph=source.photon_flux_m2_s
    tp=current.in_band_irradiance_W_m2;tph=current.photon_flux_m2_s
    if abs(ip-absorbed_power-tp)>1e-12*ip or abs(iph-absorbed_photons-tph)>1e-12*iph:
        raise ValueError('whole-path spectral balance failed')
    for i,incident in enumerate(rows[0]['absorption']['summary']['incident_samples']):
        absorbed=math.fsum(row['absorption']['summary']['absorbed_samples'][i] for row in rows)
        transmitted=rows[-1]['absorption']['summary']['transmitted_samples'][i]
        if abs(incident-absorbed-transmitted)>1e-12*incident:
            raise ValueError('nodewise optical balance failed')
    def role_total(role,key):
        return math.fsum(x['absorption']['summary'][key] for x in rows if x['role']==role)
    return {'propagation_policy':'ordered-single-pass-beer-lambert-v1','layers':rows,
        'final_source':current.to_dict(),'summary':{
        'incident_irradiance_W_m2':ip,'absorbed_irradiance_W_m2':absorbed_power,'transmitted_irradiance_W_m2':tp,
        'incident_photon_flux_m2_s':iph,'absorbed_photon_flux_m2_s':absorbed_photons,'transmitted_photon_flux_m2_s':tph,
        'fg_absorbed_irradiance_W_m2':role_total('floating_gate','absorbed_irradiance_W_m2'),
        'passive_absorbed_irradiance_W_m2':role_total('passive','absorbed_irradiance_W_m2'),
        'fg_absorbed_photon_flux_m2_s':role_total('floating_gate','absorbed_photon_flux_m2_s'),
        'passive_absorbed_photon_flux_m2_s':role_total('passive','absorbed_photon_flux_m2_s'),
        'power_balance_residual_W_m2':ip-absorbed_power-tp,'photon_balance_residual_m2_s':iph-absorbed_photons-tph}}


@dataclass(frozen=True)
class SpectralStackResult(_Archive):
    source: TabulatedSpectrum | DiscreteLineSpectrum
    path: SpectralStackPath

    def __post_init__(self):
        _propagate(self.source,self.path)

    @property
    def projection(self):
        return _propagate(self.source,self.path)

    def to_dict(self):
        return {'schema_version':'spectral-stack-result-v1','source':self.source.to_dict(),
                'path':self.path.to_dict(),'projection':self.projection}

    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','source','path','projection'))
        if type(data['source']) is not dict:raise ValueError('invalid stack source')
        kind=data['source'].get('schema_version')
        if kind=='tabulated-spectrum-v1':source=TabulatedSpectrum.from_dict(data['source'])
        elif kind=='discrete-line-spectrum-v1':source=DiscreteLineSpectrum.from_dict(data['source'])
        else:raise ValueError('unsupported source schema')
        obj=cls(source,SpectralStackPath.from_dict(data['path']))
        if _canonical(obj.to_dict())!=_canonical(data):raise ValueError('inconsistent stack projection or schema')
        return obj


def evaluate_spectral_stack(source,path):
    return SpectralStackResult(source,path)
