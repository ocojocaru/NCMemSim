# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Strict static archives of R2 campaigns and R5 comparisons; no solver replay."""
from __future__ import annotations
import csv as _csv
from fractions import Fraction as _Fraction
import hashlib as _hashlib
import html as _html
import io as _io
import json as _json
from pathlib import Path as _Path
from .performance_contracts import (PerformanceWorkload as _Workload,
    MeasurementProtocol as _Protocol, PerformanceEnvironment as _Environment,
    PerformanceTrial as _Trial, EquivalenceContract as _Equivalence,
    compare_scientific_results as _compare, _Owned, _canonical, _hash, _text,
    _digest, _seconds, _unique, _reject)
from .performance_execution import _stats
from .interoperability_comparison import (InteroperabilityComparison as _Comparison,
    compare_interoperability_data as _compare_data)

__all__ = ['PerformanceCampaignArchive', 'PerformanceInteroperabilityReport',
           'write_performance_interoperability_report', 'load_performance_interoperability_bundle']
_LIMITS = [
    'Fresh worker startup/imports and result transfer are in lifecycle time, not workload elapsed time.',
    'Timeout bounds worker launch-to-exit; total budget gates scheduling and bounds each worker by remaining time.',
    'Coordinator comparison/cleanup overhead is recorded but not preemptible; no hard RAM or disk cap.',
    'Native RSS includes the whole fresh process; no workload-only native peak attribution.',
    'Exact repeats are repeatability evidence, not physical accuracy, calibration or speedup.']
_REPORT_LIMITS = [
    'Static consistency checks do not rerun solvers, workers, clocks or environment probes.',
    'Declared source identities, evidence kinds and applicability reviews are not authenticated.',
    'Host/workload/protocol groups remain separate; no pooled timing or speedup acceptance.',
    'Synthetic controls are not observed performance, TCAD agreement or experimental qualification.',
    'R3 paired acceptance artifacts remain historical evidence outside this serial-campaign schema.',
    'Hashes and deterministic projections establish consistency, not authenticity.']


def _keys(raw, names):
    if type(raw) is not dict or set(raw) != set(names):
        raise ValueError('unknown or missing R6 fields')


def _same(actual, expected):
    if _canonical(actual) != _canonical(expected):
        raise ValueError('inconsistent R6 source, summary or projection')


def _failure(value):
    _keys(value, ('stage', 'type', 'message'))
    for item in value.values():
        _text(item, 'failure detail')


def _campaign_summary(raw):
    p = raw['protocol']; trials = raw['trials']; reference = raw['reference']['result']
    measured = [row for row in trials if row['trial']['phase'] == 'measurement']
    accepted = [row for row in measured if row['trial']['status'] == 'completed'
        and not row['trial']['trial_budget_exceeded'] and row['comparison'] is not None
        and row['comparison']['status'] == 'equivalent']
    lifecycle = raw['summary']['campaign_lifecycle_seconds']
    _seconds(lifecycle, 'campaign_lifecycle_seconds')
    exceeded = lifecycle > p['max_total_seconds']
    complete = (not exceeded and reference is not None and len(accepted) == p['measured_count']
        and all(row['trial']['status'] == 'completed' and not row['trial']['trial_budget_exceeded']
                and row['comparison'] is not None and row['comparison']['status'] == 'equivalent'
                for row in trials))
    return dict(complete=complete, declared_measurement_count=p['measured_count'],
        completed_measurement_count=sum(row['trial']['status']=='completed' for row in measured),
        equivalent_measurement_count=len(accepted),
        failed_measurement_count=sum(row['trial']['status']=='failed' for row in measured),
        unavailable_measurement_count=sum(row['trial']['status']=='unavailable' for row in measured),
        completed_observation_statistics=_stats([row['trial']['elapsed_seconds'] for row in measured
                                               if row['trial']['status']=='completed']),
        complete_equivalent_statistics=_stats([row['trial']['elapsed_seconds'] for row in accepted]) if complete else None,
        campaign_lifecycle_seconds=lifecycle, campaign_budget_exceeded=exceeded, speedup_accepted=False)


def _validate_campaign(raw):
    _keys(raw, ('schema_version','workload','protocol','environment','source_tree_hash',
                'reference','equivalence','trials','summary','limits'))
    if raw['schema_version'] != 'serial-performance-campaign-v1':
        raise ValueError('unsupported performance campaign schema')
    _canonical(raw)
    workload = _Workload.from_dict(raw['workload']); protocol = _Protocol.from_dict(raw['protocol'])
    environment = _Environment.from_dict(raw['environment']); p = protocol.to_dict()
    if p['isolation'] != 'fresh_process' or p['instrumentation'] not in ('none','native_memory'):
        raise ValueError('R6 serial archive requires the R2 supported execution protocol')
    _digest(raw['source_tree_hash'], 'source_tree_hash')
    equivalence = _Equivalence.from_dict(raw['equivalence'])
    if equivalence.to_dict()['workload_hash'] != workload.contract_hash:
        raise ValueError('equivalence/workload mismatch')
    ref = raw['reference']; _keys(ref, ('origin','result','failure','lifecycle_seconds'))
    if ref['origin'] not in ('caller_supplied','separate_serial_execution'):
        raise ValueError('unsupported reference origin')
    if ref['result'] is not None and type(ref['result']) is not dict:
        raise ValueError('scientific reference object required')
    if ref['failure'] is not None:
        _failure(ref['failure'])
    if ref['result'] is not None and ref['failure'] is not None:
        raise ValueError('successful reference cannot carry a failure')
    if ref['origin'] == 'caller_supplied':
        if ref['result'] is None or ref['failure'] is not None or ref['lifecycle_seconds'] is not None:
            raise ValueError('invalid caller-supplied reference observations')
    elif ref['result'] is None and ref['failure'] is None:
        raise ValueError('missing reference must retain failure or unavailable reason')
    if ref['origin']=='separate_serial_execution' and ref['result'] is not None and ref['lifecycle_seconds'] is None:
        raise ValueError('separate successful reference requires lifecycle observation')
    if ref['lifecycle_seconds'] is not None:
        _seconds(ref['lifecycle_seconds'], 'reference lifecycle')
    trials = raw['trials']
    if type(trials) is not list:
        raise ValueError('ordered complete trial list required')
    expected = [('warmup',i) for i in range(p['warmup_count'])] + [('measurement',i) for i in range(p['measured_count'])]
    if len(trials) != len(expected):
        raise ValueError('missing or extra declared trial index')
    for row, position in zip(trials, expected):
        _keys(row, ('trial','result','comparison','lifecycle_seconds'))
        trial = _Trial.from_dict(row['trial']); t = trial.to_dict()
        if (t['phase'], t['index']) != position:
            raise ValueError('duplicate, missing or reordered trial index')
        for name in ('workload','protocol','environment'):
            _same(t[name], raw[name])
        if row['result'] is not None and type(row['result']) is not dict:
            raise ValueError('scientific result object required')
        _same(t['result_hash'], None if row['result'] is None else _hash(row['result']))
        if t['status']=='completed' and row['result'] is None:
            raise ValueError('completed trial missing scientific result')
        if t['status']=='unavailable':
            if row['lifecycle_seconds'] is not None:
                raise ValueError('unstarted trial cannot invent lifecycle timing')
        else:
            if row['lifecycle_seconds'] is None:
                raise ValueError('launched trial requires lifecycle observation')
            _seconds(row['lifecycle_seconds'], 'trial lifecycle')
            if t['elapsed_seconds'] is not None and row['lifecycle_seconds'] < t['elapsed_seconds']:
                raise ValueError('workload timing cannot exceed launch-to-response timing')
        if p['instrumentation']=='none' and t['memory_kind']!='not_measured':
            raise ValueError('uninstrumented timing cannot invent native memory')
        if p['instrumentation']=='native_memory' and t['status']=='completed':
            if t['memory_kind']!='process_peak_rss' or t['memory_bytes']<=0:
                raise ValueError('completed native-memory trial needs positive whole-process RSS')
        derived = (None if row['result'] is None or ref['result'] is None else
                   _compare(equivalence, workload, ref['result'], row['result']))
        _same(row['comparison'], derived)
    _keys(raw['summary'], ('complete','declared_measurement_count','completed_measurement_count',
        'equivalent_measurement_count','failed_measurement_count','unavailable_measurement_count',
        'completed_observation_statistics','complete_equivalent_statistics','campaign_lifecycle_seconds',
        'campaign_budget_exceeded','speedup_accepted'))
    summary = _campaign_summary(raw)
    _same(raw['summary'], summary); _same(raw['limits'], _LIMITS)
    # Lifecycle endpoints may have tiny float rounding; this is not a scientific tolerance.
    times = [ref['lifecycle_seconds']] + [row['lifecycle_seconds'] for row in trials]
    total = sum((_Fraction(t) for t in times if t is not None), _Fraction(0))
    observed = _Fraction(summary['campaign_lifecycle_seconds'])
    if total > observed + _Fraction(1e-9)*max(1,abs(observed)):
        raise ValueError('campaign lifecycle smaller than retained worker lifecycles')
    return raw


class PerformanceCampaignArchive(_Owned):
    """Own and statically validate one complete indexed serial campaign, including failures."""
    __slots__ = ()

    def __init__(self, campaign, evidence_kind, notes):
        if evidence_kind not in ('observed_campaign','synthetic_control'):
            raise ValueError('explicit observed/synthetic evidence kind required')
        _text(notes, 'campaign evidence notes')
        campaign = _json.loads(_canonical(campaign)); _validate_campaign(campaign)
        self._store(dict(schema_version='performance-campaign-archive-v1', campaign=campaign,
            evidence_kind=evidence_kind, notes=notes, campaign_hash=_hash(campaign),
            workload_hash=_hash(campaign['workload'])))

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ('schema_version','campaign','evidence_kind','notes','campaign_hash','workload_hash'))
        obj = cls(raw['campaign'], raw['evidence_kind'], raw['notes'])
        _same(raw, obj.to_dict()); return obj


class PerformanceInteroperabilityReport(_Owned):
    """Retain labelled campaigns and comparisons without pooling hosts or inferring agreement."""
    __slots__ = ()

    def __init__(self, title, campaigns, comparisons):
        _text(title, 'report title')
        if type(campaigns) not in (list,tuple) or type(comparisons) not in (list,tuple):
            raise ValueError('ordered labelled case lists required')
        if not campaigns and not comparisons:
            raise ValueError('nonempty report required')
        sources = []; predictions = []; seen = set()
        for row in campaigns:
            _keys(row, ('label','archive')); _text(row['label'], 'campaign label')
            if row['label'] in seen:raise ValueError('duplicate report label')
            seen.add(row['label'])
            value = row['archive']
            archive = PerformanceCampaignArchive.from_dict(value.to_dict() if isinstance(value,PerformanceCampaignArchive) else value)
            sources.append(dict(label=row['label'], archive=archive.to_dict(), archive_hash=archive.contract_hash))
        for row in comparisons:
            _keys(row, ('label','declaration')); _text(row['label'], 'comparison label')
            if row['label'] in seen:raise ValueError('duplicate report label')
            seen.add(row['label'])
            value = row['declaration']
            declaration = _Comparison.from_dict(value.to_dict() if isinstance(value,_Comparison) else value)
            result = _compare_data(declaration)
            predictions.append(dict(label=row['label'], declaration=declaration.to_dict(),
                comparison_hash=declaration.contract_hash, result=result, result_hash=_hash(result)))
        summary = dict(campaign_count=len(sources), comparison_count=len(predictions),
            campaigns=[dict(label=row['label'], evidence_kind=row['archive']['evidence_kind'],
                archive_hash=row['archive_hash'], workload_hash=row['archive']['workload_hash'],
                source_tree_hash=row['archive']['campaign']['source_tree_hash'],
                environment=row['archive']['campaign']['environment'],
                instrumentation=row['archive']['campaign']['protocol']['instrumentation'],
                warmup_status_counts={status:sum(trial['trial']['phase']=='warmup' and trial['trial']['status']==status
                    for trial in row['archive']['campaign']['trials']) for status in ('completed','failed','unavailable')},
                reference_origin=row['archive']['campaign']['reference']['origin'],
                reference_failure=row['archive']['campaign']['reference']['failure'],
                summary=row['archive']['campaign']['summary']) for row in sources],
            comparisons=[dict(label=row['label'], comparison_hash=row['comparison_hash'],
                status=row['result']['status'], assessed_count=row['result']['assessed_count'],
                matched_count=row['result']['matched_count'], mismatched_count=row['result']['mismatched_count'],
                full_coverage=row['result']['full_coverage'], assessed_fraction=row['result']['assessed_fraction'],
                reasons=row['result']['reasons'], coverage=row['result']['coverage']) for row in predictions],
            pooled_statistics=None, speedup_accepted=False, external_agreement=False,
            experimental_qualification=False)
        self._store(dict(schema_version='performance-interoperability-report-v1', title=title,
            campaigns=sources, comparisons=predictions, summary=summary, limitations=_REPORT_LIMITS))

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ('schema_version','title','campaigns','comparisons','summary','limitations'))
        if type(raw['campaigns']) is not list or type(raw['comparisons']) is not list:
            raise ValueError('ordered report cases required')
        for row in raw['campaigns']:_keys(row, ('label','archive','archive_hash'))
        for row in raw['comparisons']:_keys(row, ('label','declaration','comparison_hash','result','result_hash'))
        obj = cls(raw['title'], [dict(label=row['label'],archive=row['archive']) for row in raw['campaigns']],
                  [dict(label=row['label'],declaration=row['declaration']) for row in raw['comparisons']])
        _same(raw, obj.to_dict()); return obj


def _json_bytes(raw):
    return (_json.dumps(raw,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8')


def _csv_bytes(header, rows):
    stream = _io.StringIO(newline=''); writer = _csv.writer(stream,lineterminator='\n')
    writer.writerow(header); writer.writerows(rows); return stream.getvalue().encode('utf-8')


def _cell(value):
    return _html.escape(str(value)).replace('|','&#124;').replace('\r',' ').replace('\n',' ')


def _render(report):
    raw = report.to_dict(); campaigns=[]; trials=[]; comparisons=[]; residuals=[]
    markdown = ['# '+_cell(raw['title']), '', 'Experimental qualification: **false**. External agreement: **false**.',
        'No pooled timing statistics or speedup acceptance.', '', '## Campaigns', '',
        '| Case | Evidence | Instrumentation | Complete | Failed measurements | Unavailable measurements |',
        '|---|---|---|---|---|---|']
    for entry in raw['campaigns']:
        label=entry['label']; archive=entry['archive']; c=archive['campaign']; s=c['summary']
        campaigns.append([label,entry['archive_hash'],archive['evidence_kind'],archive['campaign_hash'],
            archive['workload_hash'],c['source_tree_hash'],_canonical(c['environment']),_canonical(c['protocol']),_canonical(s)])
        markdown.append('| '+' | '.join(_cell(x) for x in (label,archive['evidence_kind'],c['protocol']['instrumentation'],
            s['complete'],s['failed_measurement_count'],s['unavailable_measurement_count']))+' |')
        for row in c['trials']:
            t=row['trial']; trials.append([label,t['phase'],t['index'],t['status'],
                '' if t['elapsed_seconds'] is None else t['elapsed_seconds'],
                '' if row['lifecycle_seconds'] is None else row['lifecycle_seconds'],t['memory_kind'],
                '' if t['memory_bytes'] is None else t['memory_bytes'],t['memory_method'] or '',t['result_hash'] or '',
                _canonical(t['failure']),_canonical(row['comparison'])])
    markdown += ['', '## Comparisons', '', '| Case | Status | Assessed | Mismatched | Full coverage |', '|---|---|---|---|---|']
    for entry in raw['comparisons']:
        label=entry['label']; result=entry['result']
        comparisons.append([label,entry['comparison_hash'],entry['result_hash'],result['status'],
            result['assessed_count'],result['matched_count'],result['mismatched_count'],result['full_coverage'],
            result['assessed_fraction'],_canonical(result['reasons']),_canonical(result['coverage'])])
        markdown.append('| '+' | '.join(_cell(x) for x in (label,result['status'],result['assessed_count'],
            result['mismatched_count'],result['full_coverage']))+' |')
        for role in ('axis','value'):
            for row in result[role+'_comparison']:
                rule=entry['declaration']['mappings']['reference_'+('axis' if role=='axis' else 'values')]
                residuals.append([label,role,rule['target_quantity'],rule['target_unit'],row['index'],row['reference'],row['candidate'],
                    _canonical(row['residual']),_canonical(row['absolute_residual']),
                    _canonical(row['tolerance']),row['within_tolerance']])
    markdown += ['', '## Limitations', '']+['- '+_cell(item) for item in _REPORT_LIMITS]+['',
        'All original sources, trials, failed/unavailable outcomes and mappings remain in report.json.',
        'Undefined numeric cells remain empty in CSV; JSON retains null.','']
    return {'report.json':_json_bytes(raw),'report.md':'\n'.join(markdown).encode('utf-8'),
        'campaigns.csv':_csv_bytes(['label','archive_hash','evidence_kind','campaign_hash','workload_hash','source_tree_hash',
            'environment_json','protocol_json','summary_json'],campaigns),
        'trials.csv':_csv_bytes(['label','phase','index','status','elapsed_s','lifecycle_s','memory_kind','memory_bytes',
            'memory_method','result_hash','failure_json','comparison_json'],trials),
        'comparisons.csv':_csv_bytes(['label','comparison_hash','result_hash','status','assessed','matched','mismatched',
            'full_coverage','assessed_fraction','reasons_json','coverage_json'],comparisons),
        'residuals.csv':_csv_bytes(['label','role','quantity','unit','index','reference','candidate','residual_rational_json',
            'absolute_residual_rational_json','tolerance_rational_json','within_tolerance'],residuals)}


def _manifest(report, files):
    return dict(schema_version='performance-interoperability-bundle-v1',report_hash=report.contract_hash,
                files={name:_hashlib.sha256(value).hexdigest() for name,value in sorted(files.items())})


def write_performance_interoperability_report(report, destination):
    if type(report) is not PerformanceInteroperabilityReport:
        raise ValueError('typed report required')
    report=PerformanceInteroperabilityReport.from_dict(report.to_dict()); files=_render(report)
    files['bundle.json']=_json_bytes(_manifest(report,files))
    destination=_Path(destination); destination.mkdir(parents=True,exist_ok=False); created=[]
    try:
        for name,value in files.items():
            path=destination/name
            with path.open('xb') as stream:
                created.append(path);stream.write(value)
    except BaseException:
        for path in created:path.unlink()
        if not any(destination.iterdir()):destination.rmdir()
        raise
    return destination


def load_performance_interoperability_bundle(destination):
    destination=_Path(destination)
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError('ordinary bundle directory required')
    entries=list(destination.iterdir())
    names={'report.json','report.md','campaigns.csv','trials.csv','comparisons.csv','residuals.csv','bundle.json'}
    if {entry.name for entry in entries}!=names or any(entry.is_symlink() or not entry.is_file() for entry in entries):
        raise ValueError('invalid bundle membership')
    report=PerformanceInteroperabilityReport.from_json((destination/'report.json').read_text(encoding='utf-8'))
    files=_render(report)
    manifest=_json.loads((destination/'bundle.json').read_text(encoding='utf-8'),object_pairs_hook=_unique,parse_constant=_reject)
    _same(manifest,_manifest(report,files))
    for name,value in files.items():
        if (destination/name).read_bytes()!=value:
            raise ValueError('bundle projection mismatch: '+name)
    return report
