# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Single-layer spectral absorption; opt-in sampled Beer-Lambert integration."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import math

from .constants import LIGHT_SPEED_M_S, PLANCK_J_S
from .spectral_sources import (SpectralEvidence, TabulatedSpectrum, DiscreteLineSpectrum,
    _Archive, _number, _text, _keys, _canonical, _unique, _constant)

__all__ = ["SpectralAbsorptionProfile", "SpectralAbsorptionResult",
           "evaluate_spectral_absorption", "evaluate_floating_gate_spectrum"]


def _json_object(text):
    if type(text) is not str:
        raise ValueError("stored optical details must be JSON text")
    value = json.loads(text, object_pairs_hook=_unique, parse_constant=_constant)
    if type(value) is not dict:
        raise ValueError("stored optical details must be an object")
    return _canonical(value)


@dataclass(frozen=True)
class SpectralAbsorptionProfile(_Archive):
    """Stored effective alpha samples on the source grid with explicit applicability.

    domain bounds are declared applicability, not independent model qualification.
    node_details_json stores observations/provenance, not a replayable model.
    """
    layer_name: str
    wavelength_nm: tuple[float, ...]
    effective_alpha_m_inv: tuple[float, ...]
    thickness_m: float
    wavelength_min_nm: float
    wavelength_max_nm: float
    evidence: SpectralEvidence
    node_details_json: tuple[str, ...] = ()

    def __post_init__(self):
        _text(self.layer_name, "layer_name")
        if type(self.wavelength_nm) is not tuple or type(self.effective_alpha_m_inv) is not tuple or not self.wavelength_nm or len(self.wavelength_nm) != len(self.effective_alpha_m_inv):
            raise ValueError("matching immutable alpha/wavelength tuples required")
        w = tuple(_number(x, "wavelength", positive=True) for x in self.wavelength_nm)
        a = tuple(_number(x, "effective alpha") for x in self.effective_alpha_m_inv)
        if any(y <= x for x,y in zip(w,w[1:])):
            raise ValueError("profile wavelengths must be strictly increasing")
        object.__setattr__(self,"wavelength_nm",w)
        object.__setattr__(self,"effective_alpha_m_inv",a)
        for name in ("thickness_m","wavelength_min_nm","wavelength_max_nm"):
            object.__setattr__(self,name,_number(getattr(self,name),name,positive=name!='thickness_m'))
        if self.wavelength_max_nm < self.wavelength_min_nm or w[0] < self.wavelength_min_nm or w[-1] > self.wavelength_max_nm:
            raise ValueError("source/profile lies outside the declared wavelength domain")
        if type(self.evidence) is not SpectralEvidence:
            raise ValueError("typed optical applicability evidence required")
        if type(self.node_details_json) is not tuple or (self.node_details_json and len(self.node_details_json)!=len(w)):
            raise ValueError("node details must be an immutable tuple aligned to the grid")
        object.__setattr__(self,"node_details_json",tuple(_json_object(s) for s in self.node_details_json))
        for wavelength,alpha,text in zip(w,a,self.node_details_json):
            row=json.loads(text)
            _keys(row,("model_identity","layer_snapshot","material_snapshot","wavelength_nm","nc_alpha_m_inv",
                       "nc_volume_fraction","effective_alpha_m_inv","channels","direct_gap_eV","indirect_gap_eV","provenance"))
            _text(row['model_identity'],'stored model identity')
            total=_number(row['nc_alpha_m_inv'],'stored NC alpha')
            fraction=_number(row['nc_volume_fraction'],'stored volume fraction')
            if fraction>1 or _number(row['wavelength_nm'],'stored wavelength',positive=True)!=wavelength or _number(row['effective_alpha_m_inv'],'stored effective alpha')!=alpha or total*fraction!=alpha:
                raise ValueError("stored optical node projection differs from profile")
            snapshot=row['layer_snapshot']
            if type(snapshot) is not dict or snapshot.get('name')!=self.layer_name or snapshot.get('nc_volume_fraction')!=fraction or _number(snapshot.get('thickness_nm'),'stored thickness',positive=True)*1e-9!=self.thickness_m:
                raise ValueError("stored layer snapshot differs from profile")
            if type(row['material_snapshot']) is not dict or type(row['provenance']) not in (dict,type(None)):
                raise ValueError("invalid material/provenance snapshot")
            _keys(row['channels'],('alpha_direct_m_inv','alpha_indirect_m_inv','alpha_urbach_m_inv'))
            channels=row['channels'].values()
            for value in channels:
                if value is not None:_number(value,'stored absorption channel')
            if all(v is not None for v in channels) and not math.isclose(math.fsum(channels),total,rel_tol=1e-12,abs_tol=0):
                raise ValueError("stored absorption channel sum differs from total")

    def to_dict(self):
        return {"schema_version":"spectral-absorption-profile-v1", "layer_name":self.layer_name,
            "wavelength_unit":"nm", "alpha_unit":"m^-1", "thickness_unit":"m",
            "wavelength_nm":list(self.wavelength_nm), "effective_alpha_m_inv":list(self.effective_alpha_m_inv),
            "thickness_m":self.thickness_m, "wavelength_min_nm":self.wavelength_min_nm,
            "wavelength_max_nm":self.wavelength_max_nm, "evidence":self.evidence.to_dict(),
            "node_details":[json.loads(s) for s in self.node_details_json]}

    @classmethod
    def from_dict(cls,data):
        _keys(data,("schema_version","layer_name","wavelength_unit","alpha_unit","thickness_unit",
            "wavelength_nm","effective_alpha_m_inv","thickness_m","wavelength_min_nm","wavelength_max_nm","evidence","node_details"))
        if any(type(data[k]) is not list for k in ("wavelength_nm","effective_alpha_m_inv","node_details")):
            raise ValueError("profile archive arrays must be lists")
        obj=cls(data['layer_name'],tuple(data['wavelength_nm']),tuple(data['effective_alpha_m_inv']),data['thickness_m'],
            data['wavelength_min_nm'],data['wavelength_max_nm'],SpectralEvidence.from_dict(data['evidence']),
            tuple(_canonical(s) for s in data['node_details']))
        if obj.to_dict()!=data:
            raise ValueError("unsupported profile schema or units")
        return obj


def _projection(source,profile):
    if type(source) not in (TabulatedSpectrum,DiscreteLineSpectrum) or type(profile) is not SpectralAbsorptionProfile:
        raise ValueError("typed source and absorption profile required")
    if source.wavelength_nm!=profile.wavelength_nm:
        raise ValueError("source and profile wavelength grids differ; no implicit interpolation")
    fractions=tuple(-math.expm1(-a*profile.thickness_m) for a in profile.effective_alpha_m_inv)
    # exp, rather than 1-fraction, retains transmission near the opaque limit.
    transmissions=tuple(math.exp(-a*profile.thickness_m) for a in profile.effective_alpha_m_inv)
    if type(source) is TabulatedSpectrum:
        incoming=source.irradiance_density_W_m2_nm
        def integral(values):
            s=TabulatedSpectrum(source.wavelength_nm,values,source.evidence)
            return s.in_band_irradiance_W_m2,s.photon_flux_m2_s
        unit="W m^-2 nm^-1"
    else:
        incoming=source.line_irradiance_W_m2 if source.enabled else tuple(0.0 for _ in source.wavelength_nm)
        def integral(values):
            s=DiscreteLineSpectrum(source.wavelength_nm,values,source.evidence)
            return s.in_band_irradiance_W_m2,s.photon_flux_m2_s
        unit="W m^-2 per line"
    absorbed=tuple(s*f for s,f in zip(incoming,fractions))
    transmitted=tuple(s*t for s,t in zip(incoming,transmissions))
    ip,iph=integral(incoming);ap,aph=integral(absorbed);tp,tph=integral(transmitted)
    power_residual=ip-ap-tp;photon_residual=iph-aph-tph
    if abs(power_residual)>1e-12*ip or abs(photon_residual)>1e-12*iph:
        raise ValueError("spectral power/photon balance failed")
    return {"integration_policy":"sampled-beer-lambert-linear-density-exact-moments-v1",
        "sample_value_unit":unit,"incident_samples":list(incoming),"absorbed_samples":list(absorbed),
        "transmitted_samples":list(transmitted),"absorption_fraction_samples":list(fractions),
        "transmission_fraction_samples":list(transmissions),
        "incident_irradiance_W_m2":ip,"absorbed_irradiance_W_m2":ap,"transmitted_irradiance_W_m2":tp,
        "incident_photon_flux_m2_s":iph,"absorbed_photon_flux_m2_s":aph,"transmitted_photon_flux_m2_s":tph,
        "power_balance_residual_W_m2":power_residual,"photon_balance_residual_m2_s":photon_residual,
        "average_generation_rate_m3_s":aph/profile.thickness_m if profile.thickness_m>0 else 0.0}


@dataclass(frozen=True)
class SpectralAbsorptionResult(_Archive):
    """Source-linked derived evidence; restoration rebuilds integrals, not optics."""
    source: TabulatedSpectrum | DiscreteLineSpectrum
    profile: SpectralAbsorptionProfile

    def __post_init__(self):
        projection=_projection(self.source,self.profile)
        _number(projection['average_generation_rate_m3_s'],"generation rate")

    @property
    def summary(self):
        return _projection(self.source,self.profile)

    def to_dict(self):
        return {"schema_version":"spectral-absorption-result-v1","source":self.source.to_dict(),
                "profile":self.profile.to_dict(),"summary":self.summary}

    @classmethod
    def from_dict(cls,data):
        _keys(data,("schema_version","source","profile","summary"))
        if type(data['source']) is not dict:
            raise ValueError("source archive must be an object")
        kind=data['source'].get('schema_version')
        if kind=='tabulated-spectrum-v1':source=TabulatedSpectrum.from_dict(data['source'])
        elif kind=='discrete-line-spectrum-v1':source=DiscreteLineSpectrum.from_dict(data['source'])
        else:raise ValueError("unsupported source schema")
        obj=cls(source,SpectralAbsorptionProfile.from_dict(data['profile']))
        if _canonical(obj.to_dict())!=_canonical(data):
            raise ValueError("inconsistent spectral absorption projection")
        return obj


def evaluate_spectral_absorption(source,profile):
    """Evaluate stored effective alpha samples without an optical model or solver."""
    return SpectralAbsorptionResult(source,profile)


def evaluate_floating_gate_spectrum(source,layer,*,optical_model,model_identity: str,
                                    wavelength_min_nm: float,wavelength_max_nm: float,
                                    evidence: SpectralEvidence):
    """Sample an explicit owned model, retaining point and layer provenance.

    Bounds/evidence are an explicit applicability declaration. No model domain
    is inferred from finite output or source coverage. No model is selected silently.
    """
    from .layers import FloatingGateLayer
    if type(source) not in (TabulatedSpectrum,DiscreteLineSpectrum) or type(layer) is not FloatingGateLayer:
        raise ValueError("typed spectral source and floating-gate layer required")
    _text(model_identity,"model_identity")
    # Validate coverage before invoking a model, including dark/disabled sources.
    SpectralAbsorptionProfile(layer.name,source.wavelength_nm,tuple(0.0 for _ in source.wavelength_nm),
        0.0,wavelength_min_nm,wavelength_max_nm,evidence)
    owned_layer=deepcopy(layer);owned_model=deepcopy(optical_model)
    owned_layer.validate()
    fraction=_number(owned_layer.nc_volume_fraction,"NC volume fraction")
    if fraction>1:raise ValueError("NC volume fraction must be at most one")
    thickness=_number(owned_layer.thickness_nm,"FG thickness",positive=True)*1e-9
    layer_snapshot=owned_layer.to_dict()
    alpha=[];details=[]
    for wavelength in source.wavelength_nm:
        try:
            point=owned_model.evaluate(deepcopy(owned_layer.nc_material),wavelength)
            if _number(point.wavelength_nm,"model wavelength",positive=True)!=wavelength:
                raise ValueError("model returned a different wavelength")
            total=_number(point.absorption_coefficient_m_inv,"NC absorption")
            channels={name:getattr(point,name,None) for name in ('alpha_direct_m_inv','alpha_indirect_m_inv','alpha_urbach_m_inv')}
            for value in channels.values():
                if value is not None:_number(value,"absorption channel")
            if all(v is not None for v in channels.values()) and not math.isclose(math.fsum(channels.values()),total,rel_tol=1e-12,abs_tol=0):
                raise ValueError("absorption channel sum differs from total")
            provenance=getattr(point,'provenance',None)
            record={"model_identity":model_identity,"layer_snapshot":layer_snapshot,"wavelength_nm":wavelength,
                "material_snapshot":owned_layer.nc_material.to_dict(),
                "nc_alpha_m_inv":total,"nc_volume_fraction":fraction,"effective_alpha_m_inv":total*fraction,
                "channels":channels,"direct_gap_eV":getattr(point,'direct_gap_eV',None),
                "indirect_gap_eV":getattr(point,'indirect_gap_eV',None),
                "provenance":{k:v.to_dict() for k,v in provenance.items()} if provenance is not None else None}
            details.append(_canonical(record));alpha.append(total*fraction)
        except (ValueError,OverflowError,TypeError,AttributeError) as exc:
            raise ValueError(f"optical evaluation failed at {wavelength:g} nm: {exc}") from exc
    profile=SpectralAbsorptionProfile(owned_layer.name,source.wavelength_nm,tuple(alpha),thickness,
        wavelength_min_nm,wavelength_max_nm,evidence,tuple(details))
    return evaluate_spectral_absorption(source,profile)
