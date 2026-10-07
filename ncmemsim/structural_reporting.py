# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Strict structural reports with complete sources; no optical, solver or RNG replay."""
from __future__ import annotations
import csv
from dataclasses import dataclass
import hashlib
import io
import json
import math
from pathlib import Path

from .hashing import canonical_hash
from .spectral_sources import _Archive, _keys, _canonical
from .structural_optical_context import StructuralSpectralContext
from .spectral_reporting import SpectralRunEvidence, build_spectral_run_evidence, _run_summary as _spectral_run_summary
from .thermal_reporting import _label, _cell
from .temperature_context import _load

__all__ = ['StructuralRunEvidence','build_structural_run_evidence','StructuralReportStudy',
           'StructuralReport','build_structural_report','write_structural_report','load_structural_report_bundle']


def _match(actual,expected):
    if _canonical(actual)!=_canonical(expected):raise ValueError('structural source/observation/projection identity mismatch')


def _run_summary(raw):
    _keys(raw,('schema_version','context','spectral_run'))
    if raw['schema_version']!='structural-run-evidence-v1':raise ValueError('unsupported structural run schema')
    context=StructuralSpectralContext.from_dict(raw['context'])
    evidence=SpectralRunEvidence.from_dict(raw['spectral_run'])
    _match(evidence.to_dict()['context'],context.spectral_context.to_dict())
    return {**_spectral_run_summary(evidence.to_dict()),
        'structural_context_hash':context.structural_context.contract_hash,
        'structural_projection':context.structural_context.projection}


@dataclass(frozen=True)
class StructuralRunEvidence(_Archive):
    record_json: str

    def __post_init__(self):
        raw=_load(self.record_json);_run_summary(raw)
        object.__setattr__(self,'record_json',_canonical(raw))

    def to_dict(self):return _load(self.record_json)

    @classmethod
    def from_dict(cls,data):return cls(_canonical(data))


def build_structural_run_evidence(run: dict,*,runtime: dict | None = None):
    """Freeze the O4 wrapper and complete N run; never infer missing initial states."""
    _keys(run,('workflow','context','context_hash','structural_context_hash','spectral_run'))
    if run['workflow']!='structural-spectral-program-pulse-dark-read-v1':raise ValueError('unsupported structural workflow')
    context=StructuralSpectralContext.from_dict(run['context'])
    if run['context_hash']!=context.contract_hash or run['structural_context_hash']!=context.structural_context.contract_hash:
        raise ValueError('structural workflow/context identities differ')
    evidence=build_spectral_run_evidence(run['spectral_run'],runtime=runtime)
    return StructuralRunEvidence.from_dict({'schema_version':'structural-run-evidence-v1',
        'context':context.to_dict(),'spectral_run':evidence.to_dict()})


@dataclass(frozen=True)
class StructuralReportStudy(_Archive):
    name: str
    kind: str
    source_json: str

    def __post_init__(self):
        _label(self.name);source=_load(self.source_json)
        if type(self.kind) is not str:raise ValueError('study kind must be text')
        if self.kind=='optical':StructuralSpectralContext.from_dict(source)
        elif self.kind=='pulse':StructuralRunEvidence.from_dict(source)
        elif self.kind=='failure':
            _keys(source,('schema_version','request','stage','error_type','message'))
            if source['schema_version']!='structural-failed-request-v1' or type(source['request']) is not dict:
                raise ValueError('invalid failed-request record')
            for k in ('stage','error_type','message'):_label(source[k])
        else:raise ValueError('unsupported structural study kind')
        object.__setattr__(self,'source_json',_canonical(source))

    @property
    def summary(self):
        source=_load(self.source_json)
        if self.kind=='optical':
            context=StructuralSpectralContext.from_dict(source)
            return {'status':'completed','optical_summary':context.spectral_context.optical_result.projection['summary'],
                'structural_context_hash':context.structural_context.contract_hash,
                'structural_projection':context.structural_context.projection}
        if self.kind=='pulse':return _run_summary(source)
        return {'status':'failed','stage':source['stage'],'error_type':source['error_type'],'message':source['message']}

    def to_dict(self):
        source=_load(self.source_json)
        return {'schema_version':'structural-report-study-v1','name':self.name,'kind':self.kind,
                'source':source,'source_hash':canonical_hash(source),'summary':self.summary}

    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','name','kind','source','source_hash','summary'))
        obj=cls(data['name'],data['kind'],_canonical(data['source']));_match(data,obj.to_dict());return obj


@dataclass(frozen=True)
class StructuralReport(_Archive):
    name: str
    studies: tuple[StructuralReportStudy, ...]
    limitations: tuple[str, ...]
    evidence_json: str = '{}'

    def __post_init__(self):
        _label(self.name)
        if type(self.studies) is not tuple or not self.studies or any(type(x) is not StructuralReportStudy for x in self.studies):raise ValueError('nonempty immutable studies required')
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
        raw={'schema_version':'structural-report-v1','name':self.name,'scientific_status':'conditional-unqualified-simulation',
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
        obj=cls(data['name'],tuple(StructuralReportStudy.from_dict(x) for x in data['studies']),tuple(data['limitations']),_canonical(data['evidence']))
        _match(data,obj.to_dict());return obj


def build_structural_report(name,studies,*,limitations,evidence=None):
    return StructuralReport(name,tuple(studies),tuple(limitations),_canonical({} if evidence is None else evidence))


def _csv(headers,rows):
    stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n');writer.writerow(headers);writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def _render(report):
    data=report.to_dict();attempts=[];layers=[];sources=[];structural=[]
    md=['# '+_cell(report.name),'','Report hash: `'+report.report_hash+'`','',
        'Conditional structural optical simulation evidence; no material/device/capture qualification.','',
        '| Study | Kind | Status |','| --- | --- | --- |']
    for study in data['studies']:
        summary=study['summary'];source=study['source'];digest=study['source_hash']
        md.append('| '+' | '.join(_cell(x) for x in (study['name'],study['kind'],summary['status']))+' |')
        attempts.append([study['name'],study['kind'],digest,summary['status'],_canonical(summary)])
        sources.append([study['name'],digest,_canonical(source)])
        context=source if study['kind']=='optical' else source['context'] if study['kind']=='pulse' else None
        stack=context['spectral_context']['optical_result'] if context is not None else None
        if context is not None:
            for row in summary['structural_projection']['layers']:
                for target,value in row['targets'].items():
                    structural.append([study['name'],digest,row['layer_name'],target,row['radius_m_from_device'],
                        value['thermal_baseline_gap_eV'],value['strain_gap_shift_eV'],value['kinetic_confinement_gap_shift_eV'],value['resolved_gap_eV']])
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
        'structural.csv':_csv(['study','source_hash','layer','gap_target','radius_m','thermal_baseline_gap_eV','strain_gap_shift_eV','kinetic_confinement_gap_shift_eV','resolved_gap_eV'],structural),
        'sources.csv':_csv(['study','source_hash','source_json'],sources)}


def _manifest(report,files):
    return {'schema_version':'structural-report-bundle-v1','report_hash':report.report_hash,
        'files':{name:hashlib.sha256(value).hexdigest() for name,value in sorted(files.items())}}


def write_structural_report(report,destination):
    if type(report) is not StructuralReport:raise ValueError('typed structural report required')
    report=StructuralReport.from_dict(report.to_dict());files=_render(report)
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


def load_structural_report_bundle(destination):
    destination=Path(destination)
    if destination.is_symlink() or not destination.is_dir():raise ValueError('ordinary bundle directory required')
    expected={'report.json','report.md','attempts.csv','layers.csv','sources.csv','structural.csv','bundle.json'}
    entries=list(destination.iterdir())
    if {x.name for x in entries}!=expected or any(x.is_symlink() or not x.is_file() for x in entries):raise ValueError('invalid bundle membership')
    report=StructuralReport.from_json((destination/'report.json').read_text(encoding='utf-8'));rebuilt=_render(report)
    _match(_load((destination/'bundle.json').read_text(encoding='utf-8')),_manifest(report,rebuilt))
    for name,value in rebuilt.items():
        if (destination/name).read_bytes()!=value:raise ValueError('bundle projection/content mismatch: '+name)
    return report
