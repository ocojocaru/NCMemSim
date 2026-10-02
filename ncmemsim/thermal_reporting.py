# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Source-linked thermal reports; restoration never runs workflows or draws samples."""
from __future__ import annotations
import csv
from dataclasses import asdict, dataclass, field, fields
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from .device import Device
from .state import DeviceState, FloatingGateState
from .temperature_context import ThermalContext, _dump, _load, _keys
from .thermal_dtco import ThermalCandidateResolution, resolve_thermal_candidate
from .workflows.application import _device_payload, _restore_device, _restore_protocol
from .dtco.spec import ExperimentSpec, DesignVariable, DesignVariableRole, BindingScope, _device_definition_payload
from .dtco.binding import apply_experiment_design_point
from .dtco.sweep import SweepPoint, SweepPointResult, SweepResult
from .dtco.metrics import analyze_sweep
from .dtco.pareto import analyze_pareto, ParetoAnalysisSpec
from .ensemble._serialization import parameter_binding_from_dict, parameter_provenance_from_dict
from .ensemble.model_contracts import TransportModelContext
from .ensemble.model_dtco import ModelParetoAnalysis
from .ensemble.model_execution import apply_model_sample_to_context
from .ensemble.model_analysis import _metric_spec_from_dict
from .ensemble.execution import _runtime
from .photo import PhotoTransitionConfig
from .retention import RetentionConfig
from .hashing import canonical_hash

__all__ = ['ThermalRunEvidence', 'build_thermal_run_evidence', 'ThermalReportStudy',
           'ThermalReport', 'build_thermal_report', 'write_thermal_report', 'load_thermal_report_bundle']


def _label(value):
    if type(value) is not str or not value or value != value.strip():
        raise ValueError('nonempty label without outer whitespace required')
    return value


def _match(actual, expected):
    if _dump(actual) != _dump(expected):
        raise ValueError('thermal report source, derived content or identity mismatch')


def _qualified(exc):
    return type(exc).__module__+'.'+type(exc).__qualname__


def _state_payload(state, device):
    if type(state) is not DeviceState or set(vars(state)) != {f.name for f in fields(DeviceState)}:
        raise ValueError('unextended initial DeviceState required')
    state.validate(device)
    result=asdict(state)
    for fg,raw in zip(state.floating_gates,result['floating_gates'],strict=True):
        if type(fg) is not FloatingGateState or set(vars(fg)) != {f.name for f in fields(FloatingGateState)}:
            raise ValueError('unextended initial FloatingGateState required')
        if not np.allclose(fg.P0+fg.P1+fg.P2,1,rtol=0,atol=1e-12):
            raise ValueError('initial probability mass must equal one')
        for name in ('P0','P1','P2'): raw[name]=raw[name].tolist()
    _dump(result)
    return result


def _restore_state(raw,device):
    _keys(raw,('floating_gates','time_s','metadata'))
    if type(raw['floating_gates']) is not list or type(raw['metadata']) is not dict or type(raw['time_s']) not in (int,float) or raw['time_s']<0:
        raise ValueError('invalid initial state')
    gates=[]
    for fg in raw['floating_gates']:
        _keys(fg,(f.name for f in fields(FloatingGateState)))
        gates.append(FloatingGateState(**{k:np.asarray(v,dtype=float) if k in ('P0','P1','P2') else v for k,v in fg.items()}))
    state=DeviceState(gates,raw['time_s'],raw['metadata'])
    _match(raw,_state_payload(state,device))
    return state


def _workflow(raw):
    _keys(raw,('schema_version','kind','evaluation_id','parameters'))
    _label(raw['evaluation_id'])
    p=raw['parameters']
    if raw['schema_version']!='thermal-workflow-v1' or type(p) is not dict:
        raise ValueError('unsupported thermal workflow')
    kind=raw['kind']
    if kind in ('program_pulse_read','electro_optical_program_pulse_read'):
        _keys(p,('protocol',) if kind=='program_pulse_read' else ('protocol','photo_config'))
        _restore_protocol({'kind':kind,'protocol':p['protocol']})
        if kind=='electro_optical_program_pulse_read':
            _keys(p['photo_config'],('photo_capture_efficiency',))
            if type(p['photo_config']['photo_capture_efficiency']) not in (int,float):raise ValueError('numeric capture efficiency required')
            _match(p['photo_config'],asdict(PhotoTransitionConfig(**p['photo_config'])))
    elif kind=='retention':
        _keys(p,('retention_config',))
        c=p['retention_config'];_keys(c,(f.name for f in fields(RetentionConfig)))
        if type(c['stop_at_quasi_equilibrium']) is not bool or any(type(c[k]) is not int for k in ('output_points','quasi_equilibrium_steps')):
            raise ValueError('invalid retention integer/boolean controls')
        for key,value in c.items():
            if key not in ('stop_at_quasi_equilibrium','occupancy_integrator','output_points','quasi_equilibrium_steps') and type(value) not in (int,float):
                raise ValueError('numeric retention configuration required')
        config=RetentionConfig(**c);config.validate();_match(c,asdict(config))
    elif kind=='fixed_field_redistribution':
        if not {'gate_voltage_V','total_time_s','steps','field_policy'}<=set(p):
            raise ValueError('incomplete fixed-field workflow')
        if type(p['steps']) is not int or p['steps']<1 or type(p['total_time_s']) not in (int,float) or p['total_time_s']<=0:
            raise ValueError('invalid fixed-field time controls')
        if type(p['gate_voltage_V']) not in (int,float): raise ValueError('invalid gate voltage')
        _label(p['field_policy'])
    else: raise ValueError('unsupported thermal workflow kind')
    _dump(raw)
    return raw


def _request(raw):
    _keys(raw,('template','device','model','initial_state'))
    template=ThermalContext.from_dict(raw['template']);device=_restore_device(raw['device'])
    model=None if raw['model'] is None else TransportModelContext.from_dict(raw['model'])
    _restore_state(raw['initial_state'],device)
    return template,device,model


@dataclass(frozen=True)
class ThermalRunEvidence:
    """Completed or failed request; physical observations remain authoritative stored data."""
    record_json: str

    def __post_init__(self):
        raw=_load(self.record_json)
        _keys(raw,('schema_version','request','workflow','runtime','status','resolution','observations','failure','source_hash'))
        if raw['schema_version']!='thermal-run-evidence-v1': raise ValueError('unsupported run evidence')
        template,device,model=_request(raw['request']);_workflow(raw['workflow'])
        if type(raw['runtime']) is not dict or not raw['runtime'] or any(type(v) is not str or not v for v in raw['runtime'].values()):
            raise ValueError('explicit source runtime required')
        resolution=None;error=None
        try: resolution=resolve_thermal_candidate(template,device,model_context=model)
        except (ValueError,TypeError,OverflowError) as exc: error=exc
        if raw['status']=='success':
            if error is not None or type(raw['observations']) is not dict or raw['failure'] is not None:
                raise ValueError('successful run requires valid resolution and complete observations')
            _match(raw['resolution'],resolution.to_dict())
        elif raw['status']=='failed':
            f=raw['failure'];_keys(f,('stage','error_type','message'));_label(f['error_type']);_label(f['message'])
            if raw['observations'] is not None: raise ValueError('failed run cannot contain successful observations')
            if error is not None:
                _match(raw['resolution'],None)
                _match(f,{'stage':'resolution','error_type':_qualified(error),'message':str(error)})
            else:
                if f['stage'] not in ('workflow','serialization'): raise ValueError('failure stage contradicts resolvable request')
                _match(raw['resolution'],resolution.to_dict())
        else: raise ValueError('unsupported run status')
        _match(raw['source_hash'],canonical_hash({k:v for k,v in raw.items() if k!='source_hash'}))
        object.__setattr__(self,'record_json',_dump(raw))

    def to_dict(self) -> dict:
        return _load(self.record_json)

    @property
    def source_hash(self) -> str:
        return self.to_dict()['source_hash']

    def to_json(self) -> str:
        return self.record_json

    @classmethod
    def from_dict(cls, raw: dict) -> ThermalRunEvidence:
        return cls(_dump(raw))

    @classmethod
    def from_json(cls, text: str) -> ThermalRunEvidence:
        return cls(text)


def build_thermal_run_evidence(template: ThermalContext, device: Device, *, workflow: dict,
                               observations: dict | None = None, failure: dict | None = None,
                               model_context: TransportModelContext | None = None,
                               initial_state: DeviceState | None = None, runtime: dict | None = None) -> ThermalRunEvidence:
    """Freeze a declared completed workflow, or preserve a failed resolution/request.

    This records evidence; it does not run the workflow or infer its initial state.
    None explicitly selects an empty initial DeviceState, which is archived fully.
    """
    if type(template) is not ThermalContext or type(device) is not Device:
        raise ValueError('typed thermal template and device required')
    request={'template':template.to_dict(),'device':_device_payload(device),
        'model':None if model_context is None else model_context.to_dict(),
        'initial_state':_state_payload(DeviceState.empty_for_device(device) if initial_state is None else initial_state,device)}
    resolution=None
    try: resolution=resolve_thermal_candidate(template,device,model_context=model_context)
    except (ValueError,TypeError,OverflowError) as exc:
        if observations is not None or failure is not None: raise ValueError('resolution failure cannot accept completed or unrelated evidence') from exc
        failure={'stage':'resolution','error_type':_qualified(exc),'message':str(exc)}
    payload={'schema_version':'thermal-run-evidence-v1','request':request,'workflow':workflow,
        'runtime':_runtime() if runtime is None else runtime,'status':'failed' if failure is not None else 'success',
        'resolution':None if resolution is None else resolution.to_dict(),
        'observations':observations,'failure':failure}
    return ThermalRunEvidence.from_dict({**payload,'source_hash':canonical_hash(payload)})


def _experiment(raw):
    if type(raw) is not dict or set(raw)-{'schema_version','name','base_device_hash','base_device_name','variables','description'}:
        raise ValueError('M6 thermal DTCO supports explicitly declared DEVICE-only experiments')
    variables=[]
    if type(raw['variables']) is not list: raise ValueError('experiment variables must be a list')
    for value in raw['variables']:
        if set(value)-{'name','binding','values','role','unit','provenance'}: raise ValueError('unknown variable fields')
        binding=parameter_binding_from_dict(value['binding'])
        if binding.scope is not BindingScope.DEVICE: raise ValueError('thermal DTCO report v1 requires DEVICE-only design axes')
        variables.append(DesignVariable(value['name'],binding,tuple(value['values']),DesignVariableRole(value['role']),value['unit'],
            None if 'provenance' not in value else parameter_provenance_from_dict(value['provenance'])))
    result=ExperimentSpec(raw['name'],raw['base_device_hash'],tuple(variables),raw.get('base_device_name'),raw.get('description'),raw['schema_version'])
    _match(raw,result.to_dict())
    return result


def _point(raw):
    _keys(raw,('schema_version','experiment_hash','index','assignments'))
    if type(raw['assignments']) is not list: raise ValueError('point assignments must be a list')
    for a in raw['assignments']: _keys(a,('name','value'))
    result=SweepPoint(raw['experiment_hash'],raw['index'],tuple((a['name'],a['value']) for a in raw['assignments']))
    _match(raw,result.to_dict())
    return result


def _output(raw, expected):
    if type(raw) is not dict or 'candidate' not in raw or 'candidate_hash' not in raw:
        raise ValueError('successful thermal DTCO output requires linked M5 candidate')
    candidate=ThermalCandidateResolution.from_dict(raw['candidate'])
    _match(candidate.to_dict(),expected.to_dict());_match(raw['candidate_hash'],candidate.candidate_hash)
    s=candidate.thermal.physics.electrostatics.semiconductor
    for key,value in (('temperature_K',candidate.thermal.temperature_K),('substrate_gap_eV',s.bandgap_eV),('intrinsic_density_m3',s.intrinsic_density_m3)):
        if key in raw: _match(raw[key],value)
    if 'density_m3' in raw:
        densities=[s.density_m3 for a in candidate.model_context.advanced_transport.attachments for s in a.specification.species] if candidate.model_context is not None else []
        if len(densities)!=1: raise ValueError('single density observable requires a single declared trap species')
        _match(raw['density_m3'],densities[0])


def _resolution_for(template,device,model,status,error_type):
    try: result=resolve_thermal_candidate(template,device,model_context=model)
    except (TypeError,ValueError,OverflowError) as exc:
        if status!='failed' or error_type!=_qualified(exc): raise ValueError('thermal request/failure identity mismatch') from exc
        return None
    if status=='failed' and error_type is not None and error_type.startswith('ncmemsim.thermal_dtco.'):
        raise ValueError('thermal domain/compatibility failure contradicts valid request')
    return result


def _attempt(template,device,model,resolution,*,index,status,workflow,metrics=None,failure=None,design=None):
    return {'index':index,'design':design,'status':status,'temperature_K':device.temperature_K,
        'template_hash':template.context_hash,'candidate_hash':None if resolution is None else resolution.candidate_hash,
        'model_hash':None if model is None else model.context_hash,'workflow_hash':canonical_hash(workflow),
        'profiles':{'substrate_gap':None if template.substrate_gap is None else template.substrate_gap.to_dict(),
            'intrinsic_density':None if template.intrinsic_density is None else template.intrinsic_density.to_dict(),
            'optical_bindings':[b.to_dict() for b in template.optical_bindings]},
        'resolved_properties':None if resolution is None else {k:resolution.thermal.to_dict()['resolved'][k] for k in ('physics','optical')},
        'metrics':metrics,'failure':failure}


def _deterministic(raw):
    analysis=raw['source_analysis'];sweep_raw=analysis['source_sweep']
    parameters=sweep_raw['evaluation']['parameters']
    template=ThermalContext.from_dict(parameters['thermal_template'])
    base=_restore_device(_load(template.nominal_device_json));experiment=_experiment(sweep_raw['experiment']);experiment.require_matching_device(base)
    model=TransportModelContext.from_dict(parameters['nominal_model_context'])
    points=[];resolutions=[];devices=[]
    for source in sweep_raw['points']:
        point=_point(source['point']);failure=source['failure']
        parsed=SweepPointResult(point,source['status'],None if source['output'] is None else _dump(source['output']),
            None if failure is None else failure['stage'],None if failure is None else failure['type'],None if failure is None else failure['message'])
        _match(source,parsed.to_dict());points.append(parsed)
        device=apply_experiment_design_point(experiment,base,point.assignments)
        resolution=_resolution_for(template,device,model,source['status'],parsed.error_type)
        if source['status']=='success': _output(source['output'],resolution)
        devices.append(device);resolutions.append(resolution)
    sweep=SweepResult(_dump(experiment.to_dict()),_dump(sweep_raw['evaluation']),tuple(points));_match(sweep_raw,sweep.to_dict())
    metrics=analyze_sweep(sweep,_metric_spec_from_dict(analysis['spec']));_match(analysis,metrics.to_dict())
    spec=raw['spec'];pareto=analyze_pareto(metrics,ParetoAnalysisSpec(spec['name'],tuple(spec['objective_names'])));_match(raw,pareto.to_dict())
    attempts=[_attempt(template,d,model,r,index=i,status=p.status,workflow=sweep_raw['evaluation'],metrics=dict(p.metric_values),
        failure=None if p.status!='failed' else (points[i].to_dict()['failure'] if points[i].status=='failed' else {'stage':p.failure_stage,'type':p.error_type,'message':p.error_message}),design=points[i].point.to_dict()) for i,(d,r,p) in enumerate(zip(devices,resolutions,metrics.points,strict=True))]
    return {'counts':{'attempted':len(points),'completed':sweep.success_count,'assessed':len(points)-metrics.failure_count,
        'feasible':metrics.feasible_count,'infeasible':metrics.infeasible_count,'failed':metrics.failure_count},
        'attempts':attempts,'statistics':[],'designs':pareto.to_dict()['points']}


def _model(raw):
    _keys(raw,('experiment','pareto'));experiment=_experiment(raw['experiment'])
    pareto=ModelParetoAnalysis.from_dict(raw['pareto']);attempts=[];statistics=[]
    counts={key:0 for key in ('attempted','completed','assessed','feasible','infeasible','failed')}
    for source in pareto.sources:
        point=source.study.design_point;population=source.study.source;execution=population.source
        _match(point.experiment_hash,experiment.experiment_hash)
        settings=_load(execution.execution_json)['workflow_context'];template=ThermalContext.from_dict(settings['thermal_template'])
        base=_restore_device(_load(template.nominal_device_json));experiment.require_matching_device(base)
        design=apply_experiment_design_point(experiment,base,point.assignments)
        _match(_device_definition_payload(design),_load(execution.execution_json)['nominal']['device'])
        _match(settings['nominal_model_context'],execution.manifest.sampling_spec.study.model_context.to_dict())
        assessments=population.to_dict()['points']
        for sample,record,assessment in zip(execution.manifest.samples,execution.points,assessments,strict=True):
            original=record.to_dict();realization=None
            try: realization=apply_model_sample_to_context(execution.manifest.sampling_spec,sample,design)
            except (TypeError,ValueError) as exc:
                if original['status']!='failed' or original['context'] is not None: raise ValueError('invalid failed MODEL realization') from exc
            if realization is None:
                device=design;model=execution.manifest.sampling_spec.study.model_context;resolution=None
            else:
                _match(original['context'],realization.context_payload())
                device=realization.device;model=realization.model_context
                resolution=_resolution_for(template,device,model,original['status'],original['error_type'])
                if original['status']=='success': _output(original['output'],resolution)
            attempts.append(_attempt(template,device,model,resolution,index=sample.sample_index,status=assessment['status'],workflow=settings,
                metrics=dict(assessment['metric_values']),failure=None if assessment['status']!='failed' else {k:assessment[k] for k in ('failure_stage','failure_category','error_type','error_message')},design=point.to_dict()))
        c=population.counts
        for key,field_name in (('attempted','attempted_count'),('assessed','assessed_count'),('feasible','feasible_count'),('infeasible','infeasible_count'),('failed','failed_count')):counts[key]+=c[field_name]
        counts['completed']+=execution.success_count
        for s in population.to_dict()['statistics']:
            statistics.append({'design':point.to_dict(),'summary':s,'fractions':population.fractions})
    return {'counts':counts,'attempts':attempts,'statistics':statistics,'designs':pareto.to_dict()['points']}


@dataclass(frozen=True)
class ThermalReportStudy:
    """Stored run or DEVICE-only thermal DTCO evidence with rebuilt projections."""
    name: str
    kind: str
    source_json: str
    _summary_json: str = field(init=False,repr=False,compare=False)

    def __post_init__(self):
        _label(self.name);source=_load(self.source_json)
        try:
            if self.kind=='run':
                run=ThermalRunEvidence.from_dict(source);raw=run.to_dict();template,device,model=_request(raw['request'])
                resolution=None if raw['resolution'] is None else ThermalCandidateResolution.from_dict(raw['resolution'])
                summary={'counts':{'attempted':1,'completed':int(raw['status']=='success'),'assessed':None,'feasible':None,'infeasible':None,'failed':int(raw['status']=='failed')},
                    'attempts':[_attempt(template,device,model,resolution,index=0,status=raw['status'],workflow=raw['workflow'],failure=raw['failure'])],
                    'statistics':[],'designs':[]}
            elif self.kind=='deterministic_dtco':summary=_deterministic(source)
            elif self.kind=='model_dtco':summary=_model(source)
            else:raise ValueError('unsupported thermal report study kind')
        except (KeyError,IndexError,AttributeError,TypeError) as exc:
            raise ValueError('incomplete or invalid thermal report source') from exc
        object.__setattr__(self,'source_json',_dump(source));object.__setattr__(self,'_summary_json',_dump(summary))

    def to_dict(self) -> dict:
        return {'schema_version':'thermal-report-study-v1','name':self.name,'kind':self.kind,'source':_load(self.source_json),
            'source_hash':canonical_hash(_load(self.source_json)),'summary':_load(self._summary_json)}

    @classmethod
    def from_dict(cls,raw: dict) -> ThermalReportStudy:
        _keys(raw,('schema_version','name','kind','source','source_hash','summary'))
        result=cls(raw['name'],raw['kind'],_dump(raw['source']));_match(raw,result.to_dict());return result


@dataclass(frozen=True)
class ThermalReport:
    """Immutable authoritative sources, conditional status and complete failure accounting."""
    name: str
    studies: tuple[ThermalReportStudy, ...]
    limitations: tuple[str, ...]
    evidence_json: str = '{}'

    def __post_init__(self):
        _label(self.name)
        if type(self.studies) is not tuple or not self.studies or any(type(s) is not ThermalReportStudy for s in self.studies):
            raise ValueError('nonempty immutable typed thermal study tuple required')
        if len({s.name for s in self.studies})!=len(self.studies):raise ValueError('duplicate thermal study names')
        if type(self.limitations) is not tuple or not self.limitations:raise ValueError('explicit scientific limitations required')
        for text in self.limitations:_label(text)
        evidence=_load(self.evidence_json)
        if type(evidence) is not dict:raise ValueError('evidence must be an object')
        object.__setattr__(self,'evidence_json',_dump(evidence))

    def to_dict(self) -> dict:
        payload={'schema_version':'thermal-report-v1','name':self.name,'scientific_status':'conditional-unqualified-simulation',
            'restoration_policy':'stored observations authoritative; resolve inputs and rebuild analysis; no workflow/RNG replay',
            'studies':[s.to_dict() for s in self.studies],'limitations':list(self.limitations),'evidence':_load(self.evidence_json)}
        return {**payload,'report_hash':canonical_hash(payload)}

    @property
    def report_hash(self) -> str:
        return self.to_dict()['report_hash']

    def to_json(self) -> str:
        return _dump(self.to_dict())

    @classmethod
    def from_dict(cls,raw: dict) -> ThermalReport:
        _keys(raw,('schema_version','name','scientific_status','restoration_policy','studies','limitations','evidence','report_hash'))
        if type(raw['studies']) is not list or type(raw['limitations']) is not list:raise ValueError('study/limitation lists required')
        result=cls(raw['name'],tuple(ThermalReportStudy.from_dict(s) for s in raw['studies']),tuple(raw['limitations']),_dump(raw['evidence']))
        _match(raw,result.to_dict());return result

    @classmethod
    def from_json(cls,text: str) -> ThermalReport:
        return cls.from_dict(_load(text))


def build_thermal_report(name: str, studies, *, limitations, evidence=None) -> ThermalReport:
    """Build only from stored typed sources; no simulation or sampling."""
    return ThermalReport(name,tuple(studies),tuple(limitations),_dump({} if evidence is None else evidence))


def _csv(headers,rows):
    stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n');writer.writerow(headers);writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def _cell(value):
    return str(value).replace('\\','\\\\').replace('|','\\|').replace('\r',' ').replace('\n',' ')


def _render(report):
    data=report.to_dict();attempts=[];stats=[];designs=[]
    md=['# '+_cell(report.name),'','Report hash: `'+report.report_hash+'`','','Conditional simulation evidence; no temperature calibration or manufacturing-yield qualification.','',
        '| Study | Attempted | Completed | Assessed | Feasible | Infeasible | Failed |','| --- | --- | --- | --- | --- | --- | --- |']
    for study in data['studies']:
        summary=study['summary'];counts=summary['counts']
        md.append('| '+' | '.join([_cell(study['name'])]+['' if counts[k] is None else str(counts[k]) for k in ('attempted','completed','assessed','feasible','infeasible','failed')])+' |')
        for r in summary['attempts']:
            attempts.append([study['name'],study['kind'],study['source_hash'],r['index'],r['temperature_K'],r['status'],r['template_hash'],r['candidate_hash'],r['model_hash'],r['workflow_hash'],
                _dump(r['profiles']),_dump(r['resolved_properties']),_dump(r['design']),_dump(r['metrics']),_dump(r['failure'])])
        for r in summary['statistics']:
            s=r['summary'];stats.append([study['name'],study['source_hash'],_dump(r['design']),s['metric_name'],s['unit'],s['denominator'],s['mean'],s['standard_deviation'],_dump(s['quantiles']),_dump(r['fractions'])])
        for r in summary['designs']:designs.append([study['name'],study['source_hash'],_dump(r)])
    md+=['','## Interpretation limits','']+['- '+_cell(text) for text in report.limitations]+['',
        'JSON retains source requests, profiles, protocols/settings, runtime, observations and failures. CSV and Markdown are rebuilt projections.',
        'Integrity checks establish consistency, not authenticity or independent physical validation.','']
    return {'report.json':(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8'),
        'report.md':'\n'.join(md).encode('utf-8'),
        'attempts.csv':_csv(['study','kind','source_hash','index','temperature_K','status','template_hash','candidate_hash','model_hash','workflow_hash','profiles_json','resolved_properties_json','design_json','metrics_json','failure_json'],attempts),
        'statistics.csv':_csv(['study','source_hash','design_json','metric','unit','denominator','mean','standard_deviation','quantiles_json','fractions_json'],stats),
        'designs.csv':_csv(['study','source_hash','pareto_point_json'],designs)}


def _manifest(report,files):
    return {'schema_version':'thermal-report-bundle-v1','report_hash':report.report_hash,
        'files':{name:hashlib.sha256(content).hexdigest() for name,content in sorted(files.items())}}


def write_thermal_report(report: ThermalReport,destination: str | Path) -> Path:
    """Validate before creating a new destination; never overwrite a bundle."""
    if type(report) is not ThermalReport:raise ValueError('typed thermal report required')
    report=ThermalReport.from_dict(report.to_dict());files=_render(report)
    files['bundle.json']=(json.dumps(_manifest(report,files),indent=2,sort_keys=True)+'\n').encode('utf-8')
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False);created=[]
    try:
        for name,content in files.items():
            path=destination/name
            with path.open('xb') as handle:created.append(path);handle.write(content)
    except BaseException:
        for path in created:path.unlink()
        if not any(destination.iterdir()):destination.rmdir()
        raise
    return destination


def load_thermal_report_bundle(destination: str | Path) -> ThermalReport:
    """Verify exact membership/bytes and restore all nested sources and projections."""
    destination=Path(destination)
    if destination.is_symlink() or not destination.is_dir():raise ValueError('ordinary bundle directory required')
    expected={'report.json','report.md','attempts.csv','statistics.csv','designs.csv','bundle.json'}
    entries=list(destination.iterdir())
    if {p.name for p in entries}!=expected or any(p.is_symlink() or not p.is_file() for p in entries):raise ValueError('missing, extra or nonregular bundle member')
    manifest=_load((destination/'bundle.json').read_text(encoding='utf-8'))
    report=ThermalReport.from_json((destination/'report.json').read_text(encoding='utf-8'));rebuilt=_render(report)
    _match(manifest,_manifest(report,rebuilt))
    for name,content in rebuilt.items():
        if (destination/name).read_bytes()!=content:raise ValueError('bundle projection/content mismatch: '+name)
    return report
