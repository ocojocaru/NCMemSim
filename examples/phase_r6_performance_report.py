# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""R6 strict report: labelled synthetic failures, R5 controls and optional real R2 timing."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
from ncmemsim.performance_contracts import (PerformanceWorkload, MeasurementProtocol,
    PerformanceEnvironment, PerformanceTrial, EquivalenceContract, compare_scientific_results)
from ncmemsim.performance_reporting import (PerformanceCampaignArchive, PerformanceInteroperabilityReport,
    write_performance_interoperability_report, load_performance_interoperability_bundle,
    _campaign_summary, _LIMITS)
from ncmemsim.performance_contracts import _hash
if __package__:
    from .phase_r5_interoperability_reference import build_reference_comparisons
else:
    from phase_r5_interoperability_reference import build_reference_comparisons


def synthetic_campaign_controls():
    """Explicitly invented records for archive gates, never observed benchmark evidence."""
    workload=PerformanceWorkload('synthetic-r6-control','relaxation',
        {'initial_state':[1.,0.], 'law':'prescribed values, no solver execution'},
        ('end_to_end',),'state_chain',1,'Synthetic archive control only')
    environment=PerformanceEnvironment('0'*40,True,'1.8.0',None,
        '/synthetic/ncmemsim/__init__.py','synthetic','synthetic','synthetic-host',
        'synthetic CPU',1,dict.fromkeys(('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS',
        'MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')),'synthetic-archive-control')
    equivalence=EquivalenceContract(workload.contract_hash,(),('',),
        'Prescribed synthetic output; consistency control, not physical accuracy')
    reference={'state':[1.,0.], 'signed_shift_V':-.25}
    records=[]
    for name,mode in [('complete','none'),('native-memory','native_memory'),
                      ('partial-failure','none'),('all-unavailable','none')]:
        protocol=MeasurementProtocol(isolation='fresh_process',instrumentation=mode,
            max_trial_seconds=10.,max_total_seconds=100.)
        unavailable=name=='all-unavailable'
        ref=None if unavailable else reference
        reason={'stage':'campaign_budget','type':'BudgetExhausted','message':'Synthetic unstarted control'}
        raw=dict(schema_version='serial-performance-campaign-v1',workload=workload.to_dict(),
            protocol=protocol.to_dict(),environment=environment.to_dict(),
            source_tree_hash=hashlib.sha256(b'synthetic prescribed source identity, not package bytes').hexdigest(),
            reference=dict(origin='separate_serial_execution',result=ref,
                failure=reason if unavailable else None,lifecycle_seconds=None if unavailable else 1.25),
            equivalence=equivalence.to_dict(),trials=[],
            summary={'campaign_lifecycle_seconds':100.1 if unavailable else 12.},limits=list(_LIMITS))
        for phase,count in [('warmup',1),('measurement',5)]:
            for index in range(count):
                failed=name=='partial-failure' and phase=='measurement' and index==1
                result=None if unavailable else ({'state':[1.,0.],'signed_shift_V':-.5} if failed else reference)
                failure=reason if unavailable else (dict(stage='workload',type='SyntheticFailure',
                    message='Deliberately retained partial output') if failed else None)
                elapsed=None if unavailable else (.5 if failed else 1.+index*.1)
                trial=PerformanceTrial(workload,protocol,environment,phase,index,
                    'unavailable' if unavailable else ('failed' if failed else 'completed'),elapsed,
                    None if result is None else _hash(result),failure,
                    'process_peak_rss' if mode=='native_memory' else 'not_measured',
                    1000000+index*1024 if mode=='native_memory' else None,
                    'Synthetic declared process peak; not a real measurement' if mode=='native_memory' else None)
                raw['trials'].append(dict(trial=trial.to_dict(),result=result,
                    comparison=None if result is None or ref is None else compare_scientific_results(equivalence,workload,ref,result),
                    lifecycle_seconds=None if unavailable else elapsed+.25))
        raw['summary']=_campaign_summary(raw)
        records.append(dict(label='synthetic-'+name,
            archive=PerformanceCampaignArchive(raw,'synthetic_control',
                'All timings, memory, environment and source identity in this case are invented archive controls.')))
    return records


def build_reference_report(*, source_commit=None, source_dirty=True, include_observed=False):
    campaigns=synthetic_campaign_controls()
    if include_observed:
        if source_commit is None:
            raise ValueError('explicit caller-declared Git commit required for observed campaign')
        from ncmemsim import DeviceBuilder
        from ncmemsim.temperature_context import ThermalContext
        from ncmemsim.performance_execution import run_serial_campaign
        workload=PerformanceWorkload('r6-observed-trajectory','relaxation',{'case':'trajectory','payload':{
            'context':ThermalContext.from_nominal(DeviceBuilder.v2(1)).to_dict(),'temperature_K':300.,
            'settings':{'voltage_V':2.,'duration_s':2e-8,'dt_s':1e-8,'initial_p1':[.2]}}},
            ('end_to_end',),'state_chain',1,'Bounded synthetic device; actual fresh-process timing, no calibration')
        raw=run_serial_campaign(workload,MeasurementProtocol(isolation='fresh_process',
            max_trial_seconds=60.,max_total_seconds=240.),source_commit=source_commit,source_dirty=source_dirty)
        campaigns.insert(0,dict(label='observed-serial-timing',archive=PerformanceCampaignArchive(raw,
            'observed_campaign','Actual fresh-process timing on an assumed device. Git commit/dirty flag are caller declarations.')))
    comparisons,_=build_reference_comparisons()
    return PerformanceInteroperabilityReport('R6 performance and interoperability controls',campaigns,
        [dict(label=name,declaration=value) for name,value in comparisons.items()])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='new bundle directory; never overwrite')
    parser.add_argument('--include-observed',action='store_true')
    parser.add_argument('--source-commit',help='required with --include-observed; explicit source Git identity')
    parser.add_argument('--source-clean',action='store_true',help='caller asserts source checkout is clean')
    args=parser.parse_args()
    report=build_reference_report(source_commit=args.source_commit,source_dirty=not args.source_clean,
                                  include_observed=args.include_observed)
    write_performance_interoperability_report(report,args.output)
    restored=load_performance_interoperability_bundle(args.output)
    assert restored.contract_hash==report.contract_hash
    print('R6 strict restoration and deterministic bundle PASS',report.contract_hash)
