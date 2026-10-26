# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""R6 static consistency, complete denominators and coherent bundle tamper rejection."""
import copy
import hashlib
import json
from pathlib import Path
import pytest
from examples.phase_r6_performance_report import build_reference_report, synthetic_campaign_controls
from ncmemsim.performance_reporting import (PerformanceCampaignArchive, PerformanceInteroperabilityReport,
    write_performance_interoperability_report, load_performance_interoperability_bundle)
from ncmemsim.performance_contracts import _hash


@pytest.fixture(scope='module')
def report():
    return build_reference_report()


@pytest.fixture
def campaign():
    return synthetic_campaign_controls()[0]['archive']


def refresh_campaign_hashes(raw):
    raw['campaign_hash']=_hash(raw['campaign']);raw['workload_hash']=_hash(raw['campaign']['workload'])


def test_control_denominators_and_nonqualification(report):
    raw=report.to_dict(); summary=raw['summary']
    assert summary['campaign_count']==4 and summary['comparison_count']==9
    assert not summary['speedup_accepted'] and not summary['external_agreement']
    assert summary['pooled_statistics'] is None and not summary['experimental_qualification']
    cases={row['label']:row['archive']['campaign'] for row in raw['campaigns']}
    assert cases['synthetic-complete']['summary']['complete']
    assert cases['synthetic-native-memory']['summary']['complete']
    assert cases['synthetic-native-memory']['protocol']['instrumentation']=='native_memory'
    failed=cases['synthetic-partial-failure']
    assert failed['summary']['completed_measurement_count']==4
    assert failed['summary']['failed_measurement_count']==1
    assert failed['summary']['complete_equivalent_statistics'] is None
    assert failed['trials'][2]['comparison']['status']=='not_equivalent'
    unavailable=cases['synthetic-all-unavailable']
    assert unavailable['summary']['unavailable_measurement_count']==5
    assert unavailable['summary']['completed_observation_statistics'] is None
    assert unavailable['reference']['failure'] and len(unavailable['trials'])==6
    assert all(row['trial']['status']=='unavailable' for row in unavailable['trials'])


def test_roundtrip_static_without_worker_solver_clock_or_environment(monkeypatch,report):
    import ncmemsim.performance_execution as execution
    import ncmemsim.performance_workloads as workloads
    def forbidden(*a,**kw):raise AssertionError('static restoration must not execute or probe')
    monkeypatch.setattr(execution,'_worker',forbidden)
    monkeypatch.setattr(execution,'_invoke',forbidden)
    monkeypatch.setattr(execution,'capture_performance_environment',forbidden)
    monkeypatch.setattr(workloads,'execute_performance_workload',forbidden)
    restored=PerformanceInteroperabilityReport.from_json(report.to_json())
    assert restored.contract_hash==report.contract_hash
    raw=restored.to_dict();raw['campaigns'][0]['archive']['notes']='changed copy'
    assert restored.to_dict()['campaigns'][0]['archive']['notes']!='changed copy'
    with pytest.raises(AttributeError):restored.extra=1


@pytest.mark.parametrize('fault',['missing_trial','duplicate_index','reordered_trials','wrong_environment',
    'wrong_protocol','wrong_workload','result_hash','comparison','median','denominator','budget_flag',
    'false_speedup','limits','source_digest','source_extra','reference_failure','negative_lifecycle',
    'too_short_lifecycle','row_fields','missing_summary_field','invented_memory'])
def test_campaign_tamper_rejected_even_with_refreshed_outer_hashes(campaign,fault):
    raw=campaign.to_dict(); c=raw['campaign'];row=c['trials'][1]
    if fault=='missing_trial':c['trials'].pop()
    elif fault=='duplicate_index':c['trials'][2]=copy.deepcopy(row)
    elif fault=='reordered_trials':c['trials'][1],c['trials'][2]=c['trials'][2],c['trials'][1]
    elif fault=='wrong_environment':row['trial']['environment']['cpu']='another host'
    elif fault=='wrong_protocol':row['trial']['protocol']['max_trial_seconds']=9.
    elif fault=='wrong_workload':row['trial']['workload']['notes']='changed input identity'
    elif fault=='result_hash':row['result']['state']=[0.,1.]
    elif fault=='comparison':row['comparison']['status']='not_equivalent'
    elif fault=='median':c['summary']['completed_observation_statistics']['median_s']=0.
    elif fault=='denominator':c['summary']['completed_measurement_count']=4
    elif fault=='budget_flag':c['summary']['campaign_budget_exceeded']=True
    elif fault=='false_speedup':c['summary']['speedup_accepted']=True
    elif fault=='limits':c['limits']=[]
    elif fault=='source_digest':c['source_tree_hash']='invalid'
    elif fault=='source_extra':c['extra']=1
    elif fault=='reference_failure':c['reference']['failure']={'stage':'x','type':'x','message':'x'}
    elif fault=='negative_lifecycle':row['lifecycle_seconds']=-1
    elif fault=='too_short_lifecycle':c['summary']['campaign_lifecycle_seconds']=1.
    elif fault=='row_fields':row['discarded_failure']=True
    elif fault=='missing_summary_field':del c['summary']['complete']
    else:row['trial'].update(memory_kind='process_peak_rss',memory_bytes=100,memory_method='invented')
    refresh_campaign_hashes(raw)
    with pytest.raises(ValueError):PerformanceCampaignArchive.from_dict(raw)


@pytest.mark.parametrize('fault',['report_summary','comparison_result','comparison_hash','archive_hash',
    'false_qualification','missing_campaign','extra','schema','duplicate_label'])
def test_report_tamper_rejected(report,fault):
    raw=report.to_dict()
    if fault=='report_summary':raw['summary']['campaign_count']=100
    elif fault=='comparison_result':
        raw['comparisons'][1]['result']['status']='matched'
        raw['comparisons'][1]['result_hash']=_hash(raw['comparisons'][1]['result'])
    elif fault=='comparison_hash':raw['comparisons'][0]['comparison_hash']='a'*64
    elif fault=='archive_hash':raw['campaigns'][0]['archive_hash']='b'*64
    elif fault=='false_qualification':raw['summary']['experimental_qualification']=True
    elif fault=='missing_campaign':raw['campaigns'].pop()
    elif fault=='extra':raw['extra']=1
    elif fault=='schema':raw['schema_version']='unsupported'
    else:raw['campaigns'][1]['label']=raw['campaigns'][0]['label']
    with pytest.raises(ValueError):PerformanceInteroperabilityReport.from_dict(raw)


@pytest.mark.parametrize('text',['{"x":1,"x":2}','{"x":NaN}','{"x":Infinity}'])
@pytest.mark.parametrize('cls',[PerformanceCampaignArchive,PerformanceInteroperabilityReport])
def test_duplicate_keys_and_nonfinite_json_rejected(cls,text):
    with pytest.raises(ValueError):cls.from_json(text)


def test_deterministic_bundle_and_no_overwrite(tmp_path,report):
    left=write_performance_interoperability_report(report,tmp_path/'left')
    right=write_performance_interoperability_report(report,tmp_path/'right')
    assert {p.name:p.read_bytes() for p in left.iterdir()}=={p.name:p.read_bytes() for p in right.iterdir()}
    assert load_performance_interoperability_bundle(left).contract_hash==report.contract_hash
    with pytest.raises(FileExistsError):write_performance_interoperability_report(report,left)
    csv=(left/'trials.csv').read_text(encoding='utf-8')
    assert 'unavailable' in csv and 'failed' in csv and 'warmup' in csv
    assert (left/'comparisons.csv').read_text().count('unavailable')>=1


@pytest.mark.parametrize('name',['report.md','campaigns.csv','trials.csv','comparisons.csv','residuals.csv'])
def test_coherently_rehashed_projection_is_still_rejected(tmp_path,report,name):
    destination=write_performance_interoperability_report(report,tmp_path/'tamper')
    target=destination/name;target.write_bytes(target.read_bytes()+b'changed\n')
    manifest=json.loads((destination/'bundle.json').read_text())
    manifest['files'][name]=hashlib.sha256(target.read_bytes()).hexdigest()
    (destination/'bundle.json').write_text(json.dumps(manifest),encoding='utf-8')
    with pytest.raises(ValueError):load_performance_interoperability_bundle(destination)


@pytest.mark.parametrize('fault',['missing','extra','directory','manifest_duplicate_key'])
def test_invalid_bundle_membership_and_manifest(tmp_path,report,fault):
    destination=write_performance_interoperability_report(report,tmp_path/'bad')
    if fault=='missing':(destination/'residuals.csv').unlink()
    elif fault=='extra':(destination/'extra.txt').write_text('extra')
    elif fault=='directory':
        (destination/'trials.csv').unlink();(destination/'trials.csv').mkdir()
    else:(destination/'bundle.json').write_text('{"x":1,"x":2}')
    with pytest.raises(ValueError):load_performance_interoperability_bundle(destination)


def test_observed_campaign_roundtrip_requires_no_faked_record():
    report=build_reference_report(source_commit='a'*40,source_dirty=True,include_observed=True)
    raw=report.to_dict(); case=raw['campaigns'][0]['archive']
    assert case['evidence_kind']=='observed_campaign' and case['campaign']['summary']['complete']
    assert case['campaign']['environment']['source_commit']=='a'*40
    assert case['campaign']['source_tree_hash']!='0'*64
    assert PerformanceInteroperabilityReport.from_json(report.to_json()).contract_hash==report.contract_hash
