# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""P4A device/photo diagnostics with sample-plane delivery and matched dark control."""
from __future__ import annotations
from dataclasses import dataclass
import json,math
import numpy as np
from .independent_data import _Archive,_keys,_canonical,_match,_text,_number,_unique,_constant
from .spectral_sources import SpectralEvidence,DiscreteLineSpectrum
from .spectral_context import SpectralSimulationContext,SpectralPulseProtocol,build_spectral_simulation_context,run_spectral_program_pulse_read,_capture
from .spectral_stack import evaluate_spectral_stack
from .spectral_reporting import _run_summary,_charge
from .thermal_reporting import _state_payload,_restore_state
from .photo import PhotoTransitionConfig
from .state import DeviceState
from .ensemble.execution import _runtime

__all__=['SamplePlaneIllumination','DevicePhotoExperiment','DevicePhotoPrediction',
         'build_device_photo_experiment','predict_device_photo_experiment']


@dataclass(frozen=True)
class SamplePlaneIllumination(_Archive):
    wavelength_nm: float
    sample_power_W: float
    uniform_spot_area_m2: float
    exposure_time_s: float
    evidence: SpectralEvidence
    delivery_statement: str

    def __post_init__(self):
        _text(self.delivery_statement,'sample-plane delivery statement')
        if type(self.evidence) is not SpectralEvidence:raise ValueError('typed optical input evidence required')
        for name in ('wavelength_nm','sample_power_W','uniform_spot_area_m2','exposure_time_s'):
            value=_number(getattr(self,name))
            if name!='sample_power_W' and value==0:raise ValueError('positive wavelength/area/exposure required')
            object.__setattr__(self,name,value)
        object.__setattr__(self,'evidence',SpectralEvidence.from_dict(self.evidence.to_dict()))
        irradiance=self.sample_power_W/self.uniform_spot_area_m2
        if not math.isfinite(irradiance) or (self.sample_power_W>0 and irradiance==0):raise ValueError('representable sample irradiance required')
        if self.sample_power_W>0 and self.source.photon_flux_m2_s==0:raise ValueError('representable photon flux required')
        fluence=self.source.photon_flux_m2_s*self.exposure_time_s
        if not math.isfinite(fluence) or (self.sample_power_W>0 and fluence==0):raise ValueError('representable photon fluence required')

    @property
    def source(self):return DiscreteLineSpectrum((self.wavelength_nm,),(self.sample_power_W/self.uniform_spot_area_m2,),self.evidence)
    @property
    def summary(self):return {'irradiance_W_m2':self.source.in_band_irradiance_W_m2,
        'incident_photon_flux_m2_s':self.source.photon_flux_m2_s,
        'incident_photon_fluence_m2':self.source.photon_flux_m2_s*self.exposure_time_s}
    def to_dict(self):return {'schema_version':'sample-plane-illumination-v1','wavelength_nm':self.wavelength_nm,
        'sample_power_W':self.sample_power_W,'uniform_spot_area_m2':self.uniform_spot_area_m2,'exposure_time_s':self.exposure_time_s,
        'evidence':self.evidence.to_dict(),'delivery_statement':self.delivery_statement,
        'power_reference':'incident_sample_plane_before_modeled_stack','geometry':'normal_incidence_uniform_spot',
        'temporal_profile':'flat_top_during_program_pulse','summary':self.summary}
    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','wavelength_nm','sample_power_W','uniform_spot_area_m2','exposure_time_s','evidence','delivery_statement','power_reference','geometry','temporal_profile','summary'))
        obj=cls(data['wavelength_nm'],data['sample_power_W'],data['uniform_spot_area_m2'],data['exposure_time_s'],SpectralEvidence.from_dict(data['evidence']),data['delivery_statement']);_match(data,obj.to_dict());return obj


@dataclass(frozen=True)
class DevicePhotoExperiment(_Archive):
    name: str
    illumination: SamplePlaneIllumination
    spectral_context: SpectralSimulationContext
    protocol: SpectralPulseProtocol
    capture_efficiency: float
    initial_state_json: str
    device_area_m2: float
    initial_preparation_evidence: str
    assumptions: str

    def __post_init__(self):
        for name in ('name','initial_preparation_evidence','assumptions'):_text(getattr(self,name),name)
        if type(self.illumination) is not SamplePlaneIllumination or type(self.spectral_context) is not SpectralSimulationContext or type(self.protocol) is not SpectralPulseProtocol:raise ValueError('typed illumination, owned context and protocol required')
        light=SamplePlaneIllumination.from_dict(self.illumination.to_dict());context=SpectralSimulationContext.from_dict(self.spectral_context.to_dict());protocol=SpectralPulseProtocol.from_dict(self.protocol.to_dict())
        efficiency=_number(self.capture_efficiency);area=_number(self.device_area_m2)
        if area==0 or area>light.uniform_spot_area_m2:raise ValueError('uniform full-device coverage requires positive device area no larger than spot area')
        _capture(PhotoTransitionConfig(efficiency),protocol.photo_weights)
        if protocol.electrical_protocol.program_internal_dt_s is None or protocol.occupancy_integrator!='backward_euler':raise ValueError('P4A requires explicit pulse timestep and backward Euler')
        if light.exposure_time_s!=protocol.electrical_protocol.programming_time_s:raise ValueError('illumination exposure must equal the declared program pulse')
        _match(context.optical_result.source.to_dict(),light.source.to_dict())
        if type(self.initial_state_json) is not str:raise ValueError('explicit initial-state JSON required')
        initial=json.loads(self.initial_state_json,object_pairs_hook=_unique,parse_constant=_constant)
        _restore_state(initial,context.resolution.device)
        object.__setattr__(self,'illumination',light);object.__setattr__(self,'spectral_context',context);object.__setattr__(self,'protocol',protocol)
        object.__setattr__(self,'capture_efficiency',efficiency);object.__setattr__(self,'device_area_m2',area);object.__setattr__(self,'initial_state_json',_canonical(initial))

    def to_dict(self):return {'schema_version':'device-photo-experiment-v1','name':self.name,'illumination':self.illumination.to_dict(),
        'spectral_context':self.spectral_context.to_dict(),'protocol':self.protocol.to_dict(),'capture_efficiency':self.capture_efficiency,
        'initial_state':json.loads(self.initial_state_json),'device_area_m2':self.device_area_m2,'initial_preparation_evidence':self.initial_preparation_evidence,
        'assumptions':self.assumptions,'scientific_status':'synthetic_device_photo_diagnostic',
        'coverage_assumption':'uniform_spot_covers_entire_device','experimental_qualification':False}
    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','name','illumination','spectral_context','protocol','capture_efficiency','initial_state','device_area_m2','initial_preparation_evidence','assumptions','scientific_status','coverage_assumption','experimental_qualification'))
        obj=cls(data['name'],SamplePlaneIllumination.from_dict(data['illumination']),SpectralSimulationContext.from_dict(data['spectral_context']),SpectralPulseProtocol.from_dict(data['protocol']),data['capture_efficiency'],_canonical(data['initial_state']),data['device_area_m2'],data['initial_preparation_evidence'],data['assumptions']);_match(data,obj.to_dict());return obj


def build_device_photo_experiment(name,resolution,illumination: SamplePlaneIllumination,protocol: SpectralPulseProtocol,*,
    capture_efficiency: float,initial_state: DeviceState,device_area_m2: float,initial_preparation_evidence: str,assumptions: str,
    direction: str,passive_layers: tuple,wavelength_min_nm: float,wavelength_max_nm: float,evidence: SpectralEvidence):
    """Bind explicit sample-plane input to existing owned spectral device physics."""
    if type(illumination) is not SamplePlaneIllumination or type(initial_state) is not DeviceState:raise ValueError('typed illumination and explicit initial state required')
    context=build_spectral_simulation_context(resolution,illumination.source,direction=direction,passive_layers=passive_layers,wavelength_min_nm=wavelength_min_nm,wavelength_max_nm=wavelength_max_nm,evidence=evidence)
    return DevicePhotoExperiment(name,illumination,context,protocol,capture_efficiency,_canonical(_state_payload(initial_state,context.resolution.device)),device_area_m2,initial_preparation_evidence,assumptions)


def _dark_context(experiment):
    source=experiment.illumination.source
    disabled=DiscreteLineSpectrum(source.wavelength_nm,source.line_irradiance_W_m2,source.evidence,enabled=False)
    return SpectralSimulationContext(experiment.spectral_context.resolution,evaluate_spectral_stack(disabled,experiment.spectral_context.optical_result.path))


def _freeze_run(run,runtime):
    _keys(run,('workflow','context','context_hash','protocol','protocol_hash','photo_capture_efficiency','initial_state','program','read','delta_vfb_V','absorbed_photon_fluence_by_fg_m2'))
    if run['workflow']!='spectral-program-pulse-dark-read-v1':raise ValueError('unsupported device-photo pulse workflow')
    context=SpectralSimulationContext.from_dict(run['context']);protocol=SpectralPulseProtocol.from_dict(run['protocol'])
    if run['context_hash']!=context.contract_hash or run['protocol_hash']!=protocol.contract_hash:raise ValueError('pulse input identity mismatch')
    _match(run['program']['spectral_stack'],context.optical_result.to_dict())
    if run['read']['spectral_stack'] is not None:raise ValueError('read must be dark')
    device=context.resolution.device
    raw={'schema_version':'device-photo-run-evidence-v1','context':context.to_dict(),'protocol':protocol.to_dict(),
        'capture_efficiency':run['photo_capture_efficiency'],'initial_state':_state_payload(run['initial_state'],device),'runtime':runtime,
        'observations':{'programmed_state':_state_payload(run['program']['state'],device),'read_state':_state_payload(run['read']['state'],device),
            'delta_vfb_V':run['delta_vfb_V'],'qfg_by_fg_C_m2':run['program']['qfg_by_fg_C_m2'].tolist(),
            'absorbed_photon_flux_by_fg_m2_s':run['program']['absorbed_photon_flux_by_fg_m2_s'].tolist(),
            'photo_transition_rate_by_fg_s':run['program']['photo_transition_rate_by_fg_s'].tolist(),
            'absorbed_photon_fluence_by_fg_m2':run['absorbed_photon_fluence_by_fg_m2'].tolist()}}
    _run_summary_with_read_audit(raw)
    return raw


def _run_summary_with_read_audit(raw):
    _keys(raw,('schema_version','context','protocol','capture_efficiency','initial_state','observations','runtime'))
    if raw['schema_version']!='device-photo-run-evidence-v1':raise ValueError('unsupported P4A run schema')
    context=SpectralSimulationContext.from_dict(raw['context']);device=context.resolution.device
    programmed=_restore_state(raw['observations']['programmed_state'],device);read=_restore_state(raw['observations']['read_state'],device)
    if programmed.time_s!=read.time_s:raise ValueError('zero-dwell read time changed')
    difference=max(float(np.max(abs(getattr(a,k)-getattr(b,k)))) for a,b in zip(programmed.floating_gates,read.floating_gates,strict=True) for k in ('P0','P1','P2'))
    if difference>1e-12:raise ValueError('zero-dwell probability change exceeds declared roundoff tolerance')
    # Existing N6 projections are reused on a private canonical comparison view.
    # Actual programmed/read arrays remain unmodified and archived above.
    comparison=json.loads(_canonical(raw));comparison['schema_version']='spectral-run-evidence-v1'
    for a,b in zip(comparison['observations']['programmed_state']['floating_gates'],comparison['observations']['read_state']['floating_gates'],strict=True):
        for key in ('P0','P1','P2'):b[key]=a[key]
    result=_run_summary(comparison)
    physics=context.resolution.physics;config=context.resolution.simulation_config
    initial=_restore_state(raw['initial_state'],device)
    voltage=SpectralPulseProtocol.from_dict(raw['protocol']).electrical_protocol.read_voltage_V
    def read_vfb(state):
        charge=_charge(state,device,physics)
        return physics.electrostatics.evaluate(device,voltage,float(charge.sum()) if len(charge)==1 else charge,config.qfix_C_m2,config.qit_C_m2).vfb_V
    actual_delta=read_vfb(read)-read_vfb(initial)
    observed_delta=raw['observations']['delta_vfb_V']
    if not math.isclose(observed_delta,actual_delta,rel_tol=1e-12,abs_tol=1e-14):raise ValueError('actual read-state observable mismatch')
    result['delta_vfb_V']=actual_delta
    return {**result,'read_max_probability_change':difference,'read_probability_tolerance':1e-12}


def _run_projection(raw,experiment,context,*,include_totals=True):
    _match(raw['context'],context.to_dict());_match(raw['protocol'],experiment.protocol.to_dict())
    _match(raw['initial_state'],json.loads(experiment.initial_state_json))
    if raw['capture_efficiency']!=experiment.capture_efficiency:raise ValueError('device/photo capture input changed')
    summary=_run_summary_with_read_audit(raw);device=context.resolution.device;physics=context.resolution.physics
    initial=_restore_state(raw['initial_state'],device);programmed=_restore_state(raw['observations']['programmed_state'],device)
    q_initial=_charge(initial,device,physics);q_final=_charge(programmed,device,physics);dq=q_final-q_initial
    total=dq*experiment.device_area_m2 if include_totals else None
    if total is not None and not np.all(np.isfinite(total)):raise ValueError('total charge exceeds finite representation')
    fg_rows={row['layer_name']:row for row in context.optical_result.projection['layers'] if row['role']=='floating_gate'}
    return {'read_max_probability_change':summary['read_max_probability_change'],'read_probability_tolerance':summary['read_probability_tolerance'],'delta_vfb_V':summary['delta_vfb_V'],'initial_qfg_C_m2':q_initial.tolist(),'final_qfg_C_m2':q_final.tolist(),
        'delta_qfg_C_m2':dq.tolist(),'delta_qfg_total_C':None if total is None else total.tolist(),
        'absorbed_photon_flux_by_fg_m2_s':summary['absorbed_photon_flux_by_fg_m2_s'],
        'absorbed_photon_fluence_by_fg_m2':summary['absorbed_photon_fluence_by_fg_m2'],
        'average_generation_rate_by_fg_m3_s':[fg_rows[fg.name]['absorption']['summary']['average_generation_rate_m3_s'] for fg in device.floating_gates()],
        'photo_transition_rate_by_fg_s':summary['photo_transition_rate_by_fg_s'],
        'optical_summary':summary['optical_summary']}


def _projection(raw):
    _keys(raw,('schema_version','experiment','experiment_hash','runtime','illuminated_run','dark_run','failure'))
    if raw['schema_version']!='device-photo-prediction-v1':raise ValueError('unsupported device-photo prediction schema')
    experiment=DevicePhotoExperiment.from_dict(raw['experiment'])
    if raw['experiment_hash']!=experiment.contract_hash:raise ValueError('device-photo input identity mismatch')
    _keys(raw['runtime'],('python','python_implementation','numpy','ncmemsim'))
    for value in raw['runtime'].values():_text(value,'runtime version')
    light=None;dark=None
    totals=not (raw['failure'] is not None and raw['failure'].get('stage')=='derived_observables')
    if raw['illuminated_run'] is not None:
        evidence=raw['illuminated_run'];_match(evidence['runtime'],raw['runtime'])
        light=_run_projection(evidence,experiment,experiment.spectral_context,include_totals=totals)
    if raw['dark_run'] is not None:
        if light is None:raise ValueError('dark control cannot precede missing illuminated evidence')
        evidence=raw['dark_run'];_match(evidence['runtime'],raw['runtime'])
        dark=_run_projection(evidence,experiment,_dark_context(experiment),include_totals=totals)
        if any(x!=0 for x in dark['absorbed_photon_flux_by_fg_m2_s']+dark['photo_transition_rate_by_fg_s']):raise ValueError('dark control has optical generation')
    if raw['failure'] is not None:
        _keys(raw['failure'],('stage','error_type','message'))
        for value in raw['failure'].values():_text(value,'prediction failure detail')
        if dark is not None and raw['failure']['stage']!='derived_observables':raise ValueError('completed control cannot be labelled failed')
        contrast=None;status='prediction_failed'
    else:
        if light is None or dark is None:raise ValueError('complete illuminated and dark evidence required')
        dq=np.asarray(light['delta_qfg_C_m2'])-np.asarray(dark['delta_qfg_C_m2'])
        contrast={'light_minus_dark_delta_vfb_V':light['delta_vfb_V']-dark['delta_vfb_V'],
            'light_minus_dark_delta_qfg_C_m2':dq.tolist(),'light_minus_dark_delta_qfg_total_C':(dq*experiment.device_area_m2).tolist()}
        status='completed'
    return {'status':status,'scientific_status':'synthetic_device_photo_diagnostic','experimental_qualification':False,
        'parameters_fitted':False,'initial_preparation_evidence':experiment.initial_preparation_evidence,
        'sample_plane_input':experiment.illumination.summary,'illuminated':light,'matched_dark':dark,'contrast':contrast,
        'charge_sign_policy':'existing occupancy/electrostatic convention; light-minus-dark is a response contrast, not photon storage yield'}


@dataclass(frozen=True)
class DevicePhotoPrediction(_Archive):
    record_json: str
    def __post_init__(self):
        raw=json.loads(self.record_json,object_pairs_hook=_unique,parse_constant=_constant)
        summary=raw.pop('summary',None);expected=_projection(raw)
        if summary is not None:_match(summary,expected)
        _canonical(expected)
        object.__setattr__(self,'record_json',_canonical(raw))
    @property
    def summary(self):return _projection(json.loads(self.record_json))
    def to_dict(self):return {**json.loads(self.record_json),'summary':self.summary}
    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','experiment','experiment_hash','runtime','illuminated_run','dark_run','failure','summary'))
        obj=cls(_canonical(data));_match(data,obj.to_dict());return obj


def predict_device_photo_experiment(experiment: DevicePhotoExperiment):
    """Run fixed inputs in light and matched dark; no fitting or qualification."""
    if type(experiment) is not DevicePhotoExperiment:raise ValueError('typed device-photo experiment required')
    experiment=DevicePhotoExperiment.from_dict(experiment.to_dict());runtime=_runtime()
    raw={'schema_version':'device-photo-prediction-v1','experiment':experiment.to_dict(),'experiment_hash':experiment.contract_hash,
        'runtime':runtime,'illuminated_run':None,'dark_run':None,'failure':None}
    stage='illuminated_program'
    try:
        for key,context in (('illuminated_run',experiment.spectral_context),('dark_run',_dark_context(experiment))):
            if key=='dark_run':stage='matched_dark_control'
            initial=_restore_state(json.loads(experiment.initial_state_json),context.resolution.device)
            run=run_spectral_program_pulse_read(context,experiment.protocol,photo_config=PhotoTransitionConfig(experiment.capture_efficiency),initial_state=initial)
            raw[key]=_freeze_run(run,runtime)
        stage='derived_observables'
        return DevicePhotoPrediction(_canonical(raw))
    except (ValueError,RuntimeError,OverflowError,FloatingPointError,np.linalg.LinAlgError) as error:
        raw['failure']={'stage':stage,'error_type':type(error).__name__,'message':str(error) or type(error).__name__}
        return DevicePhotoPrediction(_canonical(raw))
