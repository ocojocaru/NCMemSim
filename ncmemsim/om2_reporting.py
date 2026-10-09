# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""P6A strict reports of assumed OM-2 numerical studies; no experimental claims."""
from dataclasses import dataclass
from pathlib import Path
import csv,hashlib,html,io,json
from .om2_numerics import OM2NumericalStudy,LABELS
from .independent_data import _Archive,_keys,_match,_text,_canonical,_unique,_constant
from .hashing import canonical_hash

__all__=['OM2NumericalReport','build_om2_numerical_report','write_om2_numerical_report','load_om2_numerical_report_bundle']

_LIMITS=(
    'Synthetic assumed OM-2 study, not a reproduction of a measured device.',
    'No admitted measured data, fitting, experimental qualification or statistical uncertainty inference.',
    'Fixed-sequence timestep stability is not a rigorous error bound or full spatial/voltage convergence proof.',
    'Power/capture confounding remains; independent identifiability is not established.',
    'Constant-capacitance crossings are not physical Cfb extraction or a measured LCR capacitance model.',
    'PDF-only protocol/source gaps and substrate photogeneration remain unresolved.',
    'Hashes establish consistency, not measurement authenticity or replayed solver dynamics.',
)


@dataclass(frozen=True)
class OM2NumericalReport(_Archive):
    title: str
    study: OM2NumericalStudy

    def __post_init__(self):
        _text(self.title,'report title')
        if type(self.study) is not OM2NumericalStudy:raise ValueError('typed owned numerical study required')
        object.__setattr__(self,'study',OM2NumericalStudy.from_dict(self.study.to_dict()))

    def to_dict(self):
        return {'schema_version':'om2-numerical-report-v1','title':self.title,
            'study':self.study.to_dict(),'study_hash':self.study.contract_hash,
            'scientific_status':'synthetic_om2_numerical_study','experimental_qualification':False,
            'limitations':list(_LIMITS)}

    @classmethod
    def from_dict(cls,raw):
        _keys(raw,('schema_version','title','study','study_hash','scientific_status','experimental_qualification','limitations'))
        obj=cls(raw['title'],OM2NumericalStudy.from_dict(raw['study']))
        _match(raw,obj.to_dict())
        return obj


def build_om2_numerical_report(title,study):
    return OM2NumericalReport(title,study)


def _csv(header,rows):
    stream=io.StringIO(newline='')
    writer=csv.writer(stream,lineterminator='\n');writer.writerow(header);writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def _cell(value):
    if value is None:return 'undefined'
    return html.escape(str(value)).replace('|','&#124;').replace('\r',' ').replace('\n',' ')


def _json_bytes(value):
    return (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8')


def _render(report):
    raw=report.to_dict();study=raw['study'];summary=study['summary'];cases=[];checks=[]
    md=['# '+_cell(report.title),'','Scientific status: **synthetic assumed OM-2 numerical study**.',
        'Experimental qualification: **false**. Parameters fitted: **false**.','',
        'Study hash: `'+raw['study_hash']+'`.','',
        '## Cases','',
        '| Case | Execution | Observable | Signed light-minus-dark crossing window (V) |',
        '|---|---|---|---|']
    for name in LABELS:
        result=study['results'][name];s=result['summary'];value=s['light_minus_dark_crossing_window_V']
        md.append('| '+' | '.join(_cell(x) for x in (name,s['status'],s['observable_status'],value))+' |')
        cases.append([name,canonical_hash(result),result['experiment_hash'],s['status'],s['observable_status'],
            '' if value is None else value,'synthetic_om2_numerical_study','false',_canonical(result['failure']),_canonical(result['runtime'])])
    md+=['','## Temporal refinement','',
        '| Pair | Max capacitance change (F/m2) | Window-contrast change (V) | Within example thresholds |',
        '|---|---|---|---|']
    for row in summary['temporal_refinement']:
        md.append('| '+' | '.join(_cell(x) for x in (' / '.join(row['cases']),row['max_capacitance_change_F_m2'],
            row['window_contrast_change_V'],row['within_example_thresholds']))+' |')
        checks.append(['temporal_refinement',row['status'],_canonical(row['cases']),_canonical(row)])
    md+=['','## Local assumed-input sensitivity','',
        '| Input | Central secant (V per input unit) | Input unit |','|---|---|---|']
    for name,row in summary['local_sensitivity'].items():
        md.append('| '+' | '.join(_cell(x) for x in (name,row['central_secant_V_per_input_unit'],row['input_unit']))+' |')
        checks.append(['local_sensitivity:'+name,'assessable' if row['central_secant_V_per_input_unit'] is not None else 'not_assessable',
            _canonical(row['case_pair']),_canonical(row)])
    for name,row in summary['zero_photo_controls'].items():
        checks.append(['zero_photo_control:'+name,'dark_recovery' if row['dark_recovery'] else 'not_recovered',_canonical([name]),_canonical(row)])
    product=summary['power_capture_product_check']
    checks.append(['power_capture_product',product['status'],_canonical(['dt','equal_product']),_canonical(product)])
    md+=['','## Controls and interpretation','',
        'Power/capture product comparison: '+_cell(_canonical(product))+'.',
        'Independent identifiability established: **false**.',
        'Rigorous error bound established: **false**.','',
        'Zero-photo controls: '+_cell(_canonical(summary['zero_photo_controls']))+'.','',
        '## Reference selection','',
        '| Case | Reference C (F/m2) | Observable | Contrast (V) |','|---|---|---|---|']
    for row in summary['reference_selection']:
        md.append('| '+' | '.join(_cell(x) for x in (row['case'],row['reference_capacitance_F_m2'],row['observable_status'],row['contrast_V']))+' |')
        checks.append(['reference_selection',row['observable_status'],_canonical([row['case']]),_canonical(row)])
    md+=['','## Limitations','']+['- '+_cell(x) for x in _LIMITS]+['',
        'Undefined values remain null in JSON and empty in numeric CSV fields.',
        'All source predictions and failures are retained in study.json.','']
    return {'report.json':_json_bytes(raw),'report.md':'\n'.join(md).encode('utf-8'),
        'study.json':_json_bytes(study),
        'cases.csv':_csv(['case','prediction_hash','experiment_hash','execution_status','observable_status','contrast_V',
            'scientific_status','experimental_qualification','failure_json','runtime_json'],cases),
        'checks.csv':_csv(['check','status','source_cases_json','details_json'],checks)}


def _manifest(report,files):
    return {'schema_version':'om2-numerical-report-bundle-v1','report_hash':report.contract_hash,
        'study_hash':report.study.contract_hash,'files':{n:hashlib.sha256(v).hexdigest() for n,v in sorted(files.items())}}


def write_om2_numerical_report(report,destination):
    if type(report) is not OM2NumericalReport:raise ValueError('typed report required')
    report=OM2NumericalReport.from_dict(report.to_dict());files=_render(report)
    files['bundle.json']=_json_bytes(_manifest(report,files))
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False);created=[]
    try:
        for name,value in files.items():
            path=destination/name
            with path.open('xb') as handle:
                created.append(path);handle.write(value)
    except BaseException:
        for path in created:path.unlink()
        if not any(destination.iterdir()):destination.rmdir()
        raise
    return destination


def load_om2_numerical_report_bundle(destination):
    destination=Path(destination)
    if destination.is_symlink() or not destination.is_dir():raise ValueError('ordinary bundle directory required')
    entries=list(destination.iterdir())
    expected={'report.json','report.md','study.json','cases.csv','checks.csv','bundle.json'}
    if {x.name for x in entries}!=expected or any(x.is_symlink() or not x.is_file() for x in entries):
        raise ValueError('invalid report bundle membership')
    report=OM2NumericalReport.from_json((destination/'report.json').read_text(encoding='utf-8'))
    rebuilt=_render(report)
    manifest=json.loads((destination/'bundle.json').read_text(encoding='utf-8'),object_pairs_hook=_unique,parse_constant=_constant)
    _match(manifest,_manifest(report,rebuilt))
    for name,value in rebuilt.items():
        if (destination/name).read_bytes()!=value:raise ValueError('report bundle projection mismatch: '+name)
    return report
