# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Explicit spectral simulator context and illuminated-pulse/dark-read workflow."""
from __future__ import annotations
from dataclasses import dataclass
from types import SimpleNamespace
import math

from .spectral_sources import TabulatedSpectrum, DiscreteLineSpectrum, _Archive, _keys, _canonical, _number
from .spectral_stack import SpectralStackResult
from .temperature_context import ResolvedThermalContext, ThermalSimulator
from .photo import PhotoTransitionConfig, PhotoTransitionWeights
from .program_protocol import ProgramPulseReadProtocol
from .state import DeviceState

__all__ = ["SpectralSimulationContext", "SpectralSimulator", "SpectralPulseProtocol",
           "build_spectral_simulation_context", "run_spectral_program_pulse_read"]


def _capture(config,weights):
    if type(config) is not PhotoTransitionConfig or type(weights) is not PhotoTransitionWeights:
        raise ValueError('explicit typed photo configuration and weights required')
    efficiency=_number(config.photo_capture_efficiency,'capture efficiency')
    strengths=tuple(_number(getattr(weights,name),'photo weight') for name in ('r01','r12','r10','r21'))
    # N4 permits at most one total optical event per absorbed photon per active NC.
    middle=_number(strengths[1]+strengths[2],'combined outgoing photo weight')
    if efficiency>1 or efficiency*max(strengths[0],middle,strengths[3])>1:
        raise ValueError('photo weights/capture exceed the per-photon transition budget')


@dataclass(frozen=True)
class SpectralSimulationContext(_Archive):
    """Pair owned isothermal electrical evidence with a complete spectral device path.

    Stored alpha samples are explicit optical observations, not automatically
    recomputed thermal coefficients. Rebuild optical evidence for new conditions.
    """
    resolution: ResolvedThermalContext
    optical_result: SpectralStackResult

    def __post_init__(self):
        if type(self.resolution) is not ResolvedThermalContext or type(self.optical_result) is not SpectralStackResult:
            raise ValueError('typed thermal resolution and spectral stack result required')
        path=self.optical_result.path
        if path.device_snapshot_json is None or path.device_snapshot_json!=_canonical(self.resolution.device.to_dict()):
            raise ValueError('spectral path must be bound to the exact resolved device')
        self.resolution.to_dict()
        self.optical_result.to_dict()
        for layer in path.layers:
            if layer.role=='floating_gate':
                fg=self.resolution.device.get_layer(layer.profile.layer_name)
                if fg.nc_volume_fraction==0 and any(layer.profile.effective_alpha_m_inv):
                    raise ValueError('nonzero FG absorption requires physical nanocrystals')

    def create_simulator(self):
        return SpectralSimulator(self)

    def to_dict(self):
        return {'schema_version':'spectral-simulation-context-v1','resolution':self.resolution.to_dict(),
                'optical_result':self.optical_result.to_dict()}

    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','resolution','optical_result'))
        if data['schema_version']!='spectral-simulation-context-v1':raise ValueError('unsupported spectral context schema')
        return cls(ResolvedThermalContext.from_dict(data['resolution']),SpectralStackResult.from_dict(data['optical_result']))


class SpectralSimulator(ThermalSimulator):
    """Opt-in spectral path with existing occupancy/transport stepping and dark defaults."""
    def __init__(self, context: SpectralSimulationContext):
        if type(context) is not SpectralSimulationContext:raise ValueError('typed spectral simulation context required')
        self._spectral_context=context
        super().__init__(context.resolution)
        self._spectral_rows={r['layer_name']:r for r in context.optical_result.projection['layers'] if r['role']=='floating_gate'}

    def _evaluate_optical_absorption(self,source,layer):
        row=self._spectral_rows[layer.name]
        s=row['absorption']['summary']
        profile=next(x.profile for x in self._spectral_context.optical_result.path.layers if x.profile.layer_name==layer.name)
        single_line=type(source) is DiscreteLineSpectrum and len(source.wavelength_nm)==1
        eff=profile.effective_alpha_m_inv[0] if single_line else math.nan
        nc=eff/layer.nc_volume_fraction if single_line and layer.nc_volume_fraction else math.nan
        return SimpleNamespace(average_generation_rate_m3_s=s['average_generation_rate_m3_s'],
            absorption_fraction=s['absorbed_photon_flux_m2_s']/s['incident_photon_flux_m2_s'] if s['incident_photon_flux_m2_s'] else 0.0,
            absorbed_photon_flux_m2_s=s['absorbed_photon_flux_m2_s'],
            nc_absorption_coefficient_m_inv=nc,effective_absorption_coefficient_m_inv=eff)

    def relax_voltage(self,state,gate_voltage_V,dwell_time_s=None,internal_dt_s=None,
                      light_source=None,photo_config=None,photo_weights=None,occupancy_integrator='explicit_euler'):
        self._require_context()
        if light_source is not None:
            if type(light_source) not in (TabulatedSpectrum,DiscreteLineSpectrum) or light_source.contract_hash!=self._spectral_context.optical_result.source.contract_hash:
                raise ValueError('source differs from the bound spectral context')
            _capture(photo_config,photo_weights)
        output=super().relax_voltage(state,gate_voltage_V,dwell_time_s,internal_dt_s,
            light_source,photo_config,photo_weights,occupancy_integrator)
        output['spectral_context_hash']=self._spectral_context.contract_hash
        output['spectral_stack']=self._spectral_context.optical_result.to_dict() if light_source is not None else None
        output['optical_diagnostic_semantics']='photon-weighted absorption fraction; broadband scalar alpha undefined'
        return output


def build_spectral_simulation_context(resolution,source,*,direction: str,passive_layers: tuple,
                                     wavelength_min_nm: float,wavelength_max_nm: float,evidence):
    """Sample the resolution's owned FG models and explicitly supplied passive profiles."""
    from .spectral_stack import SpectralStackLayer,bind_spectral_stack_path,evaluate_spectral_stack
    from .spectral_absorption import evaluate_floating_gate_spectrum
    if type(resolution) is not ResolvedThermalContext or type(passive_layers) is not tuple:
        raise ValueError('typed resolution and immutable passive layer tuple required')
    if any(type(x) is not SpectralStackLayer or x.role!='passive' for x in passive_layers):
        raise ValueError('explicit passive optical entries required')
    device=resolution.device
    names=[x.profile.layer_name for x in passive_layers]
    expected={x.name for x in device.layers if x.role!='floating_gate'}
    if len(names)!=len(set(names)) or set(names)!=expected:
        raise ValueError('every passive device layer must be supplied exactly once')
    passive={x.profile.layer_name:x for x in passive_layers}
    layers=[]
    for layer in device.layers:
        if layer.role!='floating_gate':layers.append(passive[layer.name]);continue
        result=evaluate_floating_gate_spectrum(source,layer,optical_model=resolution.optical_model(layer.name),
            model_identity=resolution.context_hash+'/'+layer.name,wavelength_min_nm=wavelength_min_nm,
            wavelength_max_nm=wavelength_max_nm,evidence=evidence)
        layers.append(SpectralStackLayer(result.profile,'floating_gate'))
    path=bind_spectral_stack_path(device,tuple(layers),direction=direction,evidence=evidence)
    return SpectralSimulationContext(resolution,evaluate_spectral_stack(source,path))


@dataclass(frozen=True)
class SpectralPulseProtocol(_Archive):
    electrical_protocol: ProgramPulseReadProtocol
    photo_weights: PhotoTransitionWeights
    occupancy_integrator: str = 'backward_euler'

    def __post_init__(self):
        if type(self.electrical_protocol) is not ProgramPulseReadProtocol or type(self.photo_weights) is not PhotoTransitionWeights:
            raise ValueError('typed electrical protocol and photo weights required')
        _capture(PhotoTransitionConfig(0),self.photo_weights)
        if type(self.occupancy_integrator) is not str or self.occupancy_integrator not in {'explicit_euler','backward_euler'}:
            raise ValueError('unsupported occupancy integrator')

    def to_dict(self):
        return {'schema_version':'spectral-pulse-protocol-v1','electrical_protocol':self.electrical_protocol.to_dict(),
            'photo_weights':{name:getattr(self.photo_weights,name) for name in ('r01','r12','r10','r21')},
            'occupancy_integrator':self.occupancy_integrator,'read_semantics':'dark-zero-dwell'}

    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','electrical_protocol','photo_weights','occupancy_integrator','read_semantics'))
        e=data['electrical_protocol']
        _keys(e,('schema_version','program_voltage_V','programming_time_s','read_voltage_V','program_internal_dt_s','read_dwell_time_s','read_semantics'))
        _keys(data['photo_weights'],('r01','r12','r10','r21'))
        obj=cls(ProgramPulseReadProtocol(e['program_voltage_V'],e['programming_time_s'],e['read_voltage_V'],e['program_internal_dt_s']),
            PhotoTransitionWeights(**data['photo_weights']),data['occupancy_integrator'])
        if _canonical(obj.to_dict())!=_canonical(data):raise ValueError('inconsistent spectral protocol/read semantics')
        return obj


def run_spectral_program_pulse_read(context: SpectralSimulationContext, protocol: SpectralPulseProtocol,
                                   *,photo_config: PhotoTransitionConfig,initial_state: DeviceState | None = None):
    """Illuminated pulse then zero-dwell dark read; raw run evidence for future N6 reports."""
    if type(context) is not SpectralSimulationContext or type(protocol) is not SpectralPulseProtocol:
        raise ValueError('typed context and protocol required')
    _capture(photo_config,protocol.photo_weights)
    simulator=context.create_simulator()
    if initial_state is not None and type(initial_state) is not DeviceState:raise ValueError('typed initial state required')
    start=DeviceState.empty_for_device(simulator.device) if initial_state is None else initial_state.copy()
    start.validate(simulator.device)
    e=protocol.electrical_protocol
    reference=simulator.relax_voltage(start,e.read_voltage_V,0,light_source=None)
    program=simulator.relax_voltage(start,e.program_voltage_V,e.programming_time_s,e.program_internal_dt_s,
        context.optical_result.source,photo_config,protocol.photo_weights,protocol.occupancy_integrator)
    read=simulator.relax_voltage(program['state'],e.read_voltage_V,0,light_source=None)
    return {'workflow':'spectral-program-pulse-dark-read-v1','context':context.to_dict(),
        'context_hash':context.contract_hash,'protocol':protocol.to_dict(),'protocol_hash':protocol.contract_hash,
        'photo_capture_efficiency':photo_config.photo_capture_efficiency,'initial_state':start.copy(),
        'program':program,'read':read,'delta_vfb_V':read['vfb_V']-reference['vfb_V'],
        'absorbed_photon_fluence_by_fg_m2':program['absorbed_photon_flux_by_fg_m2_s']*e.programming_time_s}
