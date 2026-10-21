# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Paired fresh-process R3 comparison against a read-only Git archive baseline."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ncmemsim.performance_contracts import (PerformanceWorkload, MeasurementProtocol,
    PerformanceEnvironment, PerformanceTrial, EquivalenceContract, compare_scientific_results)

BASELINE = '6034231ffe34c374c42a43f9ac89a1a4acd7316c'
GATES = {'minimum_median_workload_speedup': 1.10, 'require_every_measured_pair_faster': True,
         'maximum_median_native_growth_fraction': .10, 'absolute_native_allowance_bytes': 4*1024*1024,
         'science': 'exact full finite scientific payload and deterministic bundle file hashes',
         'repetitions': 'one warmup then five measured pairs per instrumentation and workload',
         'ordering': 'alternate baseline/candidate and candidate/baseline by pair index',
         'acceptance_scope': 'observed same-host workloads only; remote CI acceptance remains separate'}


def _json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _source_hash(root):
    payload = {p.relative_to(root/'ncmemsim').as_posix(): hashlib.sha256(
        p.read_text(encoding='utf-8').replace('\r\n','\n').encode('utf-8')).hexdigest()
        for p in sorted((root/'ncmemsim').rglob('*.py'))}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()


def _archive_baseline(output, commit):
    archive = output/'baseline.tar'
    with archive.open('wb') as stream:
        subprocess.run(['git','archive','--format=tar',commit],cwd=ROOT,stdout=stream,check=True)
    destination = output/'baseline-source'
    destination.mkdir()
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            path = (destination/member.name).resolve()
            if not path.is_relative_to(destination.resolve()) or not (member.isfile() or member.isdir()):
                raise ValueError('baseline archive contains an unsupported path/member')
            if member.isdir():
                path.mkdir(parents=True,exist_ok=True)
            else:
                path.parent.mkdir(parents=True,exist_ok=True)
                with source.extractfile(member) as stream:
                    path.write_bytes(stream.read())
    return destination


def _trial(root, workload, protocol, commit, dirty, phase, index, directory):
    directory.mkdir(parents=True)
    request, response = directory/'request.json', directory/'response.json'
    request.write_text(json.dumps({'workload':workload.to_dict(),'source_commit':commit,
        'source_dirty':dirty,'instrumentation':protocol.to_dict()['instrumentation']}),encoding='utf-8')
    start = time.monotonic()
    failure = None
    raw = None
    try:
        bootstrap = ('import sys;sys.path.insert(0,sys.argv[1]);'
            'from ncmemsim.performance_execution import _worker;_worker(*sys.argv[2:])')
        with (directory/'stdout.log').open('wb') as stdout, (directory/'stderr.log').open('wb') as stderr:
            subprocess.run([sys.executable,'-I','-c',bootstrap,str(root),str(request),str(response),
                str(directory/'artifact')],cwd=directory,stdout=stdout,stderr=stderr,
                timeout=protocol.to_dict()['max_trial_seconds'],check=True)
        if response.stat().st_size > 32*1024*1024:
            raise ValueError('worker response exceeds 32 MiB limit')
        raw = _json(response)
        environment = PerformanceEnvironment.from_dict(raw['environment'])
        if Path(environment.to_dict()['imported_package_path']).resolve() != (root/'ncmemsim/__init__.py').resolve():
            raise ValueError('worker imported a different checkout')
        if raw['source_tree_hash'] != _source_hash(root):
            raise ValueError('worker source digest changed during measurement')
    except Exception as exc:
        failure = {'stage':'worker','type':type(exc).__name__,'message':str(exc) or type(exc).__name__}
    lifecycle = time.monotonic()-start
    return {'status':'failed' if failure is not None or raw is None else raw['status'], 'raw':raw,
            'failure':failure if raw is None else raw['failure'],
            'phase':phase,'index':index,'lifecycle_seconds':lifecycle}


def _summarize(rows, gates):
    measured = [r for r in rows if r['phase']=='measurement']
    groups = {mode:{variant:[r for r in measured if r['mode']==mode and r['variant']==variant]
        for variant in ('baseline','candidate')} for mode in ('none','native_memory')}
    expected={(mode,phase,i,variant) for mode in ('none','native_memory')
        for phase,count in (('warmup',1),('measurement',5)) for i in range(count)
        for variant in ('baseline','candidate')}
    complete_indices = len(rows)==len(expected) and {
        (r['mode'],r['phase'],r['index'],r['variant']) for r in rows}==expected
    summary = {'all_completed_and_exact':complete_indices and all(r.get('comparison',{}).get('status')=='equivalent'
        and r['status']=='completed' and not r.get('trial',{}).get('trial_budget_exceeded',True)
        and r['trial']['elapsed_seconds']>0
        and (r['mode']!='native_memory' or (r['trial']['memory_kind']=='process_peak_rss'
             and r['trial']['memory_bytes'] is not None and r['trial']['memory_bytes']>0)) for r in rows)}
    if not summary['all_completed_and_exact']:
        summary['accepted'] = False
        return summary
    timings = {}
    for mode, variants in groups.items():
        timings[mode] = {}
        for variant, observations in variants.items():
            values = [r['trial']['elapsed_seconds'] for r in observations]
            lifecycles = [r['lifecycle_seconds'] for r in observations]
            timings[mode][variant] = {'count':len(values),'median_s':statistics.median(values),
                'min_s':min(values),'max_s':max(values),
                'median_absolute_deviation_s':statistics.median(abs(v-statistics.median(values)) for v in values),
                'median_launch_to_response_s':statistics.median(lifecycles)}
    baseline = groups['none']['baseline']; candidate = groups['none']['candidate']
    ratios = [baseline[i]['trial']['elapsed_seconds']/candidate[i]['trial']['elapsed_seconds'] for i in range(5)]
    median_ratio = timings['none']['baseline']['median_s']/timings['none']['candidate']['median_s']
    memory = {v:statistics.median(r['trial']['memory_bytes'] for r in groups['native_memory'][v])
              for v in ('baseline','candidate')}
    memory_allowed = memory['baseline']+max(gates['absolute_native_allowance_bytes'],
        memory['baseline']*gates['maximum_median_native_growth_fraction'])
    lifecycle_gain = timings['none']['baseline']['median_launch_to_response_s']/timings['none']['candidate']['median_launch_to_response_s']
    summary.update({'workload_timings':timings,'paired_workload_speedups':ratios,'median_workload_speedup':median_ratio,
        'median_launch_to_response_speedup':lifecycle_gain,'median_native_peak_bytes':memory,
        'native_memory_accepted':memory['candidate']<=memory_allowed,
        'accepted':median_ratio>=gates['minimum_median_workload_speedup'] and all(r>1 for r in ratios)
            and memory['candidate']<=memory_allowed and lifecycle_gain>1})
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='new directory; never overwrite')
    parser.add_argument('--baseline-commit',default=BASELINE)
    parser.add_argument('--max-trial-seconds',type=float,default=150.)
    parser.add_argument('--max-campaign-seconds',type=float,default=1800.)
    args=parser.parse_args()
    protocol = MeasurementProtocol(isolation='fresh_process',max_trial_seconds=args.max_trial_seconds,
                                   max_total_seconds=args.max_campaign_seconds)
    candidate_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    baseline_commit=subprocess.check_output(['git','rev-parse',args.baseline_commit+'^{commit}'],cwd=ROOT,text=True).strip()
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'acceptance.json').write_text(json.dumps(GATES,indent=2)+'\n',encoding='utf-8')
    baseline_root=_archive_baseline(args.output,baseline_commit)
    roots={'baseline':baseline_root,'candidate':ROOT}
    source_hashes={key:_source_hash(value) for key,value in roots.items()}
    source_files={key:{p.relative_to(value/'ncmemsim').as_posix():
        p.read_text(encoding='utf-8').replace('\r\n','\n')
        for p in (value/'ncmemsim').rglob('*.py')} for key,value in roots.items()}
    if set(source_files['baseline'])!=set(source_files['candidate']):
        raise ValueError('R3 comparison requires unchanged package file membership')
    changed=[name for name in source_files['baseline']
             if source_files['baseline'][name]!=source_files['candidate'][name]]
    if changed!=['multilevel_reporting.py']:
        raise ValueError('R3 comparison must isolate the one reviewed runtime optimization: '+str(changed))
    archive_path='tests/fixtures/archives/v1_8_preparation/multilevel_report.json'
    assert (baseline_root/archive_path).read_bytes()==(ROOT/archive_path).read_bytes()
    raw=_json(ROOT/archive_path)
    workloads=[PerformanceWorkload('strict-'+case,case,{'case':case,'payload':{'report':raw}},
        ('end_to_end',),'static_'+case,len(raw['cases']),
        'R2 bounded synthetic compact-model reference; no physical calibration or speedup claim') for case in ('restore','export')]
    start=time.monotonic()
    cases=[]
    for workload in workloads:
        name=workload.to_dict()['workload_id']; rows=[]; reference=None
        contract=EquivalenceContract(workload.contract_hash,(),('',),
            'Exact complete baseline-commit serial output; archive sources and bundle hashes unchanged')
        for mode in ('none','native_memory'):
            current=MeasurementProtocol(isolation='fresh_process',instrumentation=mode,
                max_trial_seconds=args.max_trial_seconds,max_total_seconds=args.max_campaign_seconds)
            for phase,count in (('warmup',1),('measurement',5)):
                for index in range(count):
                    order=('baseline','candidate') if index%2==0 else ('candidate','baseline')
                    for variant in order:
                        if time.monotonic()-start >= args.max_campaign_seconds:
                            raise TimeoutError('R3 campaign budget exhausted; completed trial files retained')
                        remaining=args.max_campaign_seconds-(time.monotonic()-start)
                        bounded=MeasurementProtocol(isolation='fresh_process',instrumentation=mode,
                            max_trial_seconds=min(args.max_trial_seconds,remaining),max_total_seconds=args.max_campaign_seconds)
                        directory=args.output/name/mode/f'{phase}-{index}-{variant}'
                        row=_trial(roots[variant],workload,bounded,
                            baseline_commit if variant=='baseline' else candidate_commit,
                            False if variant=='baseline' else dirty,phase,index,directory)
                        row.update(mode=mode,variant=variant)
                        result=None if row['raw'] is None else row['raw']['result']
                        if reference is None and variant=='baseline' and result is not None and row['status']=='completed':
                            reference=result
                        if result is not None and reference is not None:
                            row['comparison']=compare_scientific_results(contract,workload,reference,result)
                        if row['raw'] is not None:
                            response=row['raw']; env=PerformanceEnvironment.from_dict(response['environment'])
                            trial=PerformanceTrial(workload,current,env,phase,index,row['status'],response['elapsed_seconds'],
                                None if result is None else hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                                row['failure'],'process_peak_rss' if response['memory_bytes'] is not None else 'not_measured',
                                response['memory_bytes'],response['memory_method'])
                            row['trial']=trial.to_dict()
                        # Raw scientific evidence is in response.json, never pooled or discarded.
                        row.pop('raw')
                        row['response_file']=str((directory/'response.json').relative_to(args.output))
                        (directory/'observation.json').write_text(json.dumps(row,indent=2,allow_nan=False)+'\n',encoding='utf-8')
                        rows.append(row)
                        print(name,mode,phase,index,variant,row['status'],flush=True)
        summary=_summarize(rows,GATES)
        case={'workload':workload.to_dict(),'workload_hash':workload.contract_hash,'equivalence':contract.to_dict(),
              'observations':rows,'summary':summary}
        (args.output/(name+'.json')).write_text(json.dumps(case,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        cases.append(case)
        print(name,json.dumps(summary),flush=True)
    index={'schema_version':'r3-paired-report-comparison-v1','baseline_commit':baseline_commit,
        'candidate_commit':candidate_commit,'candidate_dirty':dirty,'source_tree_hashes':source_hashes,
        'acceptance':GATES,'cases':[{'case':c['workload']['workload_id'],'summary':c['summary']} for c in cases],
        'accepted':all(c['summary']['accepted'] for c in cases),
        'limits':['Single-host alternating fresh-process observations, not a universal speedup.',
                  'Native memory runs separate from uninstrumented timings; whole-process peaks include imports.',
                  'Workload and lifecycle scopes match R2; baseline files come from a read-only Git archive.',
                  'Candidate dirty state is retained; exact-commit cross-platform evidence follows push.']}
    (args.output/'index.json').write_text(json.dumps(index,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    if not index['accepted']:
        raise SystemExit('R3 acceptance failed; all paired evidence retained')


if __name__=='__main__':
    main()
