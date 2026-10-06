# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Strict source-linked spectral reports; no optical, workflow or RNG replay."""
from __future__ import annotations
import csv
from dataclasses import dataclass
import hashlib
import io
import json
import math
from pathlib import Path
import numpy as np

from .hashing import canonical_hash
from .spectral_sources import _Archive, _keys, _canonical, _number
from .spectral_context import SpectralSimulationContext, SpectralPulseProtocol, _capture
from .spectral_stack import SpectralStackResult
from .photo import PhotoTransitionConfig, nanocrystal_number_density_m3
from .thermal_reporting import _state_payload, _restore_state, _label, _cell
from .temperature_context import _load
from .ensemble.execution import _runtime

__all__ = ['SpectralRunEvidence','build_spectral_run_evidence','SpectralReportStudy',
           'SpectralReport','build_spectral_report','write_spectral_report','load_spectral_report_bundle']


def _match(actual,expected):
    if _canonical(actual)!=_canonical(expected):raise ValueError('spectral source/observation/projection identity mismatch')


def _charge(state,device,physics):
    q=[]
    for fg,s in zip(device.floating_gates(),state.floating_gates,strict=True):
        x,dx=physics.occupancy.grid(fg)
        density=physics.occupancy.density_profile(fg,x)
        rho=physics.occupancy.charge_density_C_m3(s,density)
        q.append(physics.occupancy.total_charge_C_m2(rho,dx))
    return np.asarray(q)


def _run_summary(raw):
    _keys(raw,('schema_version','context','protocol','capture_efficiency','initial_state','observations','runtime'))
    if raw['schema_version']!='spectral-run-evidence-v1':raise ValueError('unsupported spectral run schema')
    context=SpectralSimulationContext.from_dict(raw['context'])
    protocol=SpectralPulseProtocol.from_dict(raw['protocol'])
    efficiency=_number(raw['capture_efficiency'],'capture efficiency')
    _capture(PhotoTransitionConfig(efficiency),protocol.photo_weights)
    runtime=raw['runtime'];_keys(runtime,('python','python_implementation','numpy','ncmemsim'))
    for value in runtime.values():_label(value)
    device=context.resolution.device;physics=context.resolution.physics
    initial=_restore_state(raw['initial_state'],device)
    o=raw['observations']
    _keys(o,('programmed_state','read_state','delta_vfb_V','qfg_by_fg_C_m2',
             'absorbed_photon_flux_by_fg_m2_s','photo_transition_rate_by_fg_s','absorbed_photon_fluence_by_fg_m2'))
    programmed=_restore_state(o['programmed_state'],device);read=_restore_state(o['read_state'],device)
    duration=protocol.electrical_protocol.programming_time_s
    if programmed.time_s!=initial.time_s+duration or read.time_s!=programmed.time_s:
        raise ValueError('stored pulse/read state times differ from protocol')
    for a,b in zip(programmed.floating_gates,read.floating_gates,strict=True):
        if any(not np.array_equal(getattr(a,k),getattr(b,k)) for k in ('P0','P1','P2')):
            raise ValueError('dark zero-dwell read changed probabilities')
    q=_charge(programmed,device,physics);q0=_charge(initial,device,physics)
    config=context.resolution.simulation_config;voltage=protocol.electrical_protocol.read_voltage_V
    def vfb(charges):
        return physics.electrostatics.evaluate(device,voltage,float(charges.sum()) if len(charges)==1 else charges,
            config.qfix_C_m2,config.qit_C_m2).vfb_V
    rows={x['layer_name']:x for x in context.optical_result.projection['layers']}
    flux=[];rates=[];alphas=[]
    for fg in device.floating_gates():
        s=rows[fg.name]['absorption']['summary'];flux.append(s['absorbed_photon_flux_m2_s'])
        density=nanocrystal_number_density_m3(fg.nc_diameter_nm,fg.nc_volume_fraction)
        rates.append(efficiency*s['average_generation_rate_m3_s']/density if density else 0.)
        profile=next(x.profile for x in context.optical_result.path.layers if x.profile.layer_name==fg.name)
        alphas.append(profile.effective_alpha_m_inv[0] if len(profile.wavelength_nm)==1 else None)
    expected={'delta_vfb_V':vfb(q)-vfb(q0),'qfg_by_fg_C_m2':q.tolist(),
        'absorbed_photon_flux_by_fg_m2_s':flux,'photo_transition_rate_by_fg_s':rates,
        'absorbed_photon_fluence_by_fg_m2':[x*duration for x in flux]}
    for key,value in expected.items():
        if key=='delta_vfb_V':
            if type(o[key]) not in (int,float) or not math.isfinite(o[key]) or not math.isclose(o[key],value,rel_tol=1e-12,abs_tol=1e-14):
                raise ValueError('stored read observable differs from states')
        else:
            if type(o[key]) is not list or len(o[key])!=len(value) or any(type(x) not in (int,float) or not math.isfinite(x) for x in o[key]) or not np.allclose(o[key],value,rtol=1e-12,atol=0):
                raise ValueError('stored optical/charge observations differ from context/states')
    return {'status':'completed','context_hash':context.contract_hash,'protocol_hash':protocol.contract_hash,
        **expected,'scalar_effective_alpha_m_inv_by_fg':alphas,
        'optical_summary':context.optical_result.projection['summary']}


@dataclass(frozen=True)
class SpectralRunEvidence(_Archive):
    record_json: str

    def __post_init__(self):
        raw=_load(self.record_json);_run_summary(raw)
        object.__setattr__(self,'record_json',_canonical(raw))

    def to_dict(self):return _load(self.record_json)

    @classmethod
    def from_dict(cls,data):return cls(_canonical(data))


def build_spectral_run_evidence(run: dict,*,runtime: dict | None = None):
    """Freeze selected complete-state N4 evidence, without simulation or initial-state inference."""
    _keys(run,('workflow','context','context_hash','protocol','protocol_hash','photo_capture_efficiency',
        'initial_state','program','read','delta_vfb_V','absorbed_photon_fluence_by_fg_m2'))
    if run['workflow']!='spectral-program-pulse-dark-read-v1':raise ValueError('unsupported spectral workflow')
    context=SpectralSimulationContext.from_dict(run['context']);protocol=SpectralPulseProtocol.from_dict(run['protocol'])
    if run['context_hash']!=context.contract_hash or run['protocol_hash']!=protocol.contract_hash:
        raise ValueError('workflow/context identities differ')
    _match(run['program']['spectral_stack'],context.optical_result.to_dict())
    if run['read']['spectral_stack'] is not None:raise ValueError('read must be dark')
    device=context.resolution.device
    raw={'schema_version':'spectral-run-evidence-v1','context':context.to_dict(),'protocol':protocol.to_dict(),
        'capture_efficiency':run['photo_capture_efficiency'],'initial_state':_state_payload(run['initial_state'],device),
        'runtime':_runtime() if runtime is None else runtime,'observations':{
        'programmed_state':_state_payload(run['program']['state'],device),'read_state':_state_payload(run['read']['state'],device),
        'delta_vfb_V':run['delta_vfb_V'],'qfg_by_fg_C_m2':run['program']['qfg_by_fg_C_m2'].tolist(),
        'absorbed_photon_flux_by_fg_m2_s':run['program']['absorbed_photon_flux_by_fg_m2_s'].tolist(),
        'photo_transition_rate_by_fg_s':run['program']['photo_transition_rate_by_fg_s'].tolist(),
        'absorbed_photon_fluence_by_fg_m2':run['absorbed_photon_fluence_by_fg_m2'].tolist()}}
    return SpectralRunEvidence.from_dict(raw)


@dataclass(frozen=True)
class SpectralReportStudy(_Archive):
    name: str
    kind: str
    source_json: str

    def __post_init__(self):
        _label(self.name);source=_load(self.source_json)
        if type(self.kind) is not str:raise ValueError('study kind must be text')
        if self.kind=='stack':SpectralStackResult.from_dict(source)
        elif self.kind=='pulse':SpectralRunEvidence.from_dict(source)
        elif self.kind=='failure':
            _keys(source,('schema_version','request','stage','error_type','message'))
            if source['schema_version']!='spectral-failed-request-v1' or type(source['request']) is not dict:
                raise ValueError('invalid failed-request record')
            for k in ('stage','error_type','message'):_label(source[k])
        else:raise ValueError('unsupported spectral study kind')
        object.__setattr__(self,'source_json',_canonical(source))

    @property
    def summary(self):
        source=_load(self.source_json)
        if self.kind=='stack':return {'status':'completed','optical_summary':SpectralStackResult.from_dict(source).projection['summary']}
        if self.kind=='pulse':return _run_summary(source)
        return {'status':'failed','stage':source['stage'],'error_type':source['error_type'],'message':source['message']}

    def to_dict(self):
        source=_load(self.source_json)
        return {'schema_version':'spectral-report-study-v1','name':self.name,'kind':self.kind,
                'source':source,'source_hash':canonical_hash(source),'summary':self.summary}

    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','name','kind','source','source_hash','summary'))
        obj=cls(data['name'],data['kind'],_canonical(data['source']));_match(data,obj.to_dict());return obj


@dataclass(frozen=True)
class SpectralReport(_Archive):
    name: str
    studies: tuple[SpectralReportStudy, ...]
    limitations: tuple[str, ...]
    evidence_json: str = '{}'

    def __post_init__(self):
        _label(self.name)
        if type(self.studies) is not tuple or not self.studies or any(type(x) is not SpectralReportStudy for x in self.studies):raise ValueError('nonempty immutable studies required')
        if len({x.name for x in self.studies})!=len(self.studies):raise ValueError('duplicate study names')
        if type(self.limitations) is not tuple or not self.limitations:raise ValueError('explicit scientific limitations required')
        for x in self.limitations:_label(x)
        evidence=_load(self.evidence_json)
        if type(evidence) is not dict:raise ValueError('report evidence must be an object')
        object.__setattr__(self,'evidence_json',_canonical(evidence))

    @property
    def summary(self):
        summaries=[s.summary for s in self.studies];failed=sum(s['status']=='failed' for s in summaries)
        values=[s['delta_vfb_V'] for s in summaries if 'delta_vfb_V' in s]
        return {'counts':{'attempted':len(summaries),'completed':len(summaries)-failed,'failed':failed},
            'completed_fraction':(len(summaries)-failed)/len(summaries),
            'pulse_delta_vfb_V':{'estimated_count':len(values),'mean':math.fsum(values)/len(values) if values else None,
                'denominator':'completed pulse studies'}}

    def to_dict(self):
        raw={'schema_version':'spectral-report-v1','name':self.name,'scientific_status':'conditional-unqualified-simulation',
            'restoration_policy':'stored states/observations authoritative; rebuild projections; no optical/workflow/RNG replay',
            'studies':[x.to_dict() for x in self.studies],'limitations':list(self.limitations),
            'evidence':_load(self.evidence_json),'summary':self.summary}
        return {**raw,'report_hash':canonical_hash(raw)}

    @property
    def report_hash(self):return self.to_dict()['report_hash']

    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','name','scientific_status','restoration_policy','studies','limitations','evidence','summary','report_hash'))
        if type(data['studies']) is not list or type(data['limitations']) is not list:raise ValueError('study/limitation lists required')
        obj=cls(data['name'],tuple(SpectralReportStudy.from_dict(x) for x in data['studies']),tuple(data['limitations']),_canonical(data['evidence']))
        _match(data,obj.to_dict());return obj


def build_spectral_report(name,studies,*,limitations,evidence=None):
    return SpectralReport(name,tuple(studies),tuple(limitations),_canonical({} if evidence is None else evidence))


def _csv(headers,rows):
    stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n');writer.writerow(headers);writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def _render(report):
    data=report.to_dict();attempts=[];layers=[];sources=[]
    md=['# '+_cell(report.name),'','Report hash: `'+report.report_hash+'`','',
        'Conditional spectral simulation evidence; no experimental device or capture qualification.','',
        '| Study | Kind | Status |','| --- | --- | --- |']
    for study in data['studies']:
        summary=study['summary'];source=study['source'];digest=study['source_hash']
        md.append('| '+' | '.join(_cell(x) for x in (study['name'],study['kind'],summary['status']))+' |')
        attempts.append([study['name'],study['kind'],digest,summary['status'],_canonical(summary)])
        sources.append([study['name'],digest,_canonical(source)])
        stack=source if study['kind']=='stack' else source['context']['optical_result'] if study['kind']=='pulse' else None
        if stack is not None:
            for index,row in enumerate(stack['projection']['layers']):
                layers.append([study['name'],digest,index,row['layer_name'],row['role'],row['treatment'],_canonical(row['absorption']['summary'])])
    md+=['','## Interpretation limits','']+['- '+_cell(x) for x in report.limitations]+['',
        'Null means undefined. JSON retains complete sources; CSV/Markdown are rebuilt projections.',
        'Hashes verify consistency, not authenticity or replayed solver trajectories.','']
    return {'report.json':(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8'),
        'report.md':'\n'.join(md).encode('utf-8'),
        'attempts.csv':_csv(['study','kind','source_hash','status','summary_json'],attempts),
        'layers.csv':_csv(['study','source_hash','traversal_index','layer','role','treatment','summary_json'],layers),
        'sources.csv':_csv(['study','source_hash','source_json'],sources)}


def _manifest(report,files):
    return {'schema_version':'spectral-report-bundle-v1','report_hash':report.report_hash,
        'files':{name:hashlib.sha256(value).hexdigest() for name,value in sorted(files.items())}}


def write_spectral_report(report,destination):
    if type(report) is not SpectralReport:raise ValueError('typed spectral report required')
    report=SpectralReport.from_dict(report.to_dict());files=_render(report)
    files['bundle.json']=(json.dumps(_manifest(report,files),indent=2,sort_keys=True)+'\n').encode('utf-8')
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False);created=[]
    try:
        for name,value in files.items():
            path=destination/name
            with path.open('xb') as handle:created.append(path);handle.write(value)
    except BaseException:
        for path in created:path.unlink()
        if not any(destination.iterdir()):destination.rmdir()
        raise
    return destination


def load_spectral_report_bundle(destination):
    destination=Path(destination)
    if destination.is_symlink() or not destination.is_dir():raise ValueError('ordinary bundle directory required')
    expected={'report.json','report.md','attempts.csv','layers.csv','sources.csv','bundle.json'}
    entries=list(destination.iterdir())
    if {x.name for x in entries}!=expected or any(x.is_symlink() or not x.is_file() for x in entries):raise ValueError('invalid bundle membership')
    report=SpectralReport.from_json((destination/'report.json').read_text(encoding='utf-8'));rebuilt=_render(report)
    _match(_load((destination/'bundle.json').read_text(encoding='utf-8')),_manifest(report,rebuilt))
    for name,value in rebuilt.items():
        if (destination/name).read_bytes()!=value:raise ValueError('bundle projection/content mismatch: '+name)
    return report
