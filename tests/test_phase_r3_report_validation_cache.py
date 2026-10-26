# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""R3 exact source reuse, bounded lifetime and unchanged rejection semantics."""
import copy
from dataclasses import replace
import json
from pathlib import Path

import pytest
import ncmemsim.multilevel_reporting as reporting
from ncmemsim.multilevel_contracts import PulseSequenceEvidence

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def probe(monkeypatch):
    calls = []
    class Validated:
        def __init__(self, raw):
            self.raw = raw
        def to_json(self):
            return json.dumps(self.raw, sort_keys=True, separators=(',', ':'), allow_nan=False)
    class Validator:
        @classmethod
        def from_dict(cls, raw):
            calls.append(copy.deepcopy(raw))
            if raw.get('invalid'):
                raise ValueError('invalid probe source')
            return Validated(raw)
    monkeypatch.setitem(reporting._TYPES, 'probe', Validator)
    assert reporting._SOURCE_VALIDATION_CACHE.get() is None
    yield calls, Validator
    assert reporting._SOURCE_VALIDATION_CACHE.get() is None


def test_exact_immutable_snapshot_reused_only_inside_scope(probe):
    calls, _ = probe
    raw = '{"value":[1,2],"source":"a"}'
    with reporting._source_validation_scope():
        first = reporting._validated_source_json('probe', raw)
        second = reporting._validated_source_json('probe', raw)
        assert first == second and len(calls) == 1
        altered_copy = json.loads(first)
        altered_copy['value'].clear()
        assert json.loads(reporting._validated_source_json('probe', raw))['value'] == [1, 2]
        assert len(calls) == 1
    reporting._validated_source_json('probe', raw)
    assert len(calls) == 2
    with reporting._source_validation_scope():
        reporting._validated_source_json('probe', raw)
    assert len(calls) == 3


def test_changed_source_and_changed_validator_are_cache_misses(probe, monkeypatch):
    calls, _ = probe
    with reporting._source_validation_scope():
        reporting._validated_source_json('probe', '{"value":1}')
        reporting._validated_source_json('probe', '{"value":2}')
        assert len(calls) == 2
        class Rejecting:
            @classmethod
            def from_dict(cls, raw):
                raise ValueError('new validator must run')
        monkeypatch.setitem(reporting._TYPES, 'probe', Rejecting)
        with pytest.raises(ValueError, match='new validator'):
            reporting._validated_source_json('probe', '{"value":1}')


@pytest.mark.parametrize('raw', ['{"invalid":true}', '{"x":NaN}', '{"x":1,"x":2}', '[]', None])
def test_invalid_sources_are_never_cached_and_scope_resets(probe, raw):
    with pytest.raises((ValueError, AttributeError)):
        with reporting._source_validation_scope():
            reporting._validated_source_json('probe', raw)
    assert reporting._SOURCE_VALIDATION_CACHE.get() is None


def test_exception_does_not_poison_next_operation(probe):
    calls, _ = probe
    with pytest.raises(ValueError):
        with reporting._source_validation_scope():
            reporting._validated_source_json('probe', '{"value":1}')
            raise ValueError('later report validation fails')
    with reporting._source_validation_scope():
        reporting._validated_source_json('probe', '{"value":1}')
    assert len(calls) == 2


@pytest.mark.parametrize('limit', [0, 1, 32])
def test_small_memory_budget_falls_back_to_full_validation(probe, monkeypatch, limit):
    calls, _ = probe
    monkeypatch.setattr(reporting, '_SOURCE_CACHE_MAX_BYTES', limit)
    with reporting._source_validation_scope():
        first = reporting._validated_source_json('probe', '{"value":[1,2]}')
        assert reporting._validated_source_json('probe', '{"value":[1,2]}') == first
        assert len(calls) == 2
        assert not reporting._SOURCE_VALIDATION_CACHE.get()['values']


def test_entry_bound_and_nested_scope(probe, monkeypatch):
    calls, _ = probe
    monkeypatch.setattr(reporting, '_SOURCE_CACHE_MAX_ENTRIES', 1)
    with reporting._source_validation_scope():
        original = reporting._SOURCE_VALIDATION_CACHE.get()
        reporting._validated_source_json('probe', '{"value":1}')
        with reporting._source_validation_scope():
            assert reporting._SOURCE_VALIDATION_CACHE.get() is original
            reporting._validated_source_json('probe', '{"value":1}')
            reporting._validated_source_json('probe', '{"value":2}')
            reporting._validated_source_json('probe', '{"value":2}')
        assert len(original['values']) == 1 and len(calls) == 3


def test_contexts_do_not_share_validation_results(probe):
    from contextvars import Context
    calls, _ = probe
    def operation():
        with reporting._source_validation_scope():
            reporting._validated_source_json('probe', '{"value":1}')
            reporting._validated_source_json('probe', '{"value":1}')
    with reporting._source_validation_scope():
        reporting._validated_source_json('probe', '{"value":1}')
        Context().run(operation)
        reporting._validated_source_json('probe', '{"value":1}')
    assert len(calls) == 2


@pytest.fixture(scope='module')
def small_raw():
    raw = json.loads((ROOT/'tests/fixtures/archives/v1_8_preparation/multilevel_report.json').read_text(encoding='utf-8'))
    case = next(x for x in raw['cases'] if x['kind'] == 'electrical')
    result = reporting.MultilevelReport('R3 small source reference',
        (reporting.MultilevelReportCase.from_dict(case),), PulseSequenceEvidence.from_dict(raw['evidence']))
    return result.to_dict()


def test_public_restore_exact_output_and_each_distinct_source_validated(small_raw, monkeypatch):
    original = reporting._TYPES['electrical']
    calls = []
    class Counting:
        @classmethod
        def from_dict(cls, raw):
            calls.append(1)
            return original.from_dict(raw)
    monkeypatch.setitem(reporting._TYPES, 'electrical', Counting)
    raw = copy.deepcopy(small_raw)
    restored = reporting.MultilevelReport.from_dict(raw)
    assert restored.to_dict() == small_raw and len(calls) == 1
    assert reporting._SOURCE_VALIDATION_CACHE.get() is None
    raw['cases'][0]['source']['summary']['status'] = 'forged'
    with pytest.raises(ValueError):
        reporting.MultilevelReport.from_dict(raw)
    assert len(calls) == 2
    assert reporting._SOURCE_VALIDATION_CACHE.get() is None
    assert restored.to_dict() == small_raw


@pytest.mark.parametrize('fault', ['source_hash', 'source', 'case_evidence', 'summary', 'extra', 'nonfinite', 'duplicate'])
def test_tampered_report_rejected_even_after_valid_restore(small_raw, fault):
    reporting.MultilevelReport.from_dict(small_raw)
    raw = copy.deepcopy(small_raw)
    if fault == 'source_hash':
        raw['cases'][0]['source_hash'] = '0'*64
    elif fault == 'source':
        raw['cases'][0]['source']['summary']['status'] = 'forged'
    elif fault == 'case_evidence':
        raw['cases'][0]['evidence']['forged'] = True
    elif fault == 'summary':
        raw['summary']['case_count'] = 999
    elif fault == 'extra':
        raw['extra'] = True
    elif fault == 'nonfinite':
        raw['cases'][0]['source']['forged'] = float('nan')
    else:
        text = json.dumps(raw).replace('{', '{"title":"forged",', 1)
        with pytest.raises(ValueError):
            reporting.MultilevelReport.from_json(text)
        return
    with pytest.raises(ValueError):
        reporting.MultilevelReport.from_dict(raw)
    assert reporting._SOURCE_VALIDATION_CACHE.get() is None


def test_cache_disabled_has_identical_bundle_bytes_and_negative_projection_gate(small_raw, monkeypatch, tmp_path):
    cached = reporting.MultilevelReport.from_dict(small_raw)
    reporting.write_multilevel_report(cached, tmp_path/'cached')
    monkeypatch.setattr(reporting, '_SOURCE_CACHE_MAX_BYTES', 0)
    uncached = reporting.MultilevelReport.from_dict(small_raw)
    assert cached.to_json() == uncached.to_json() and cached.contract_hash == uncached.contract_hash
    reporting.write_multilevel_report(uncached, tmp_path/'uncached')
    for path in (tmp_path/'cached').iterdir():
        assert path.read_bytes() == (tmp_path/'uncached'/path.name).read_bytes()
    monkeypatch.setattr(reporting, '_SOURCE_CACHE_MAX_BYTES', 2*1024*1024)
    assert reporting.load_multilevel_report_bundle(tmp_path/'cached').to_dict() == small_raw
    (tmp_path/'cached'/'metrics.csv').write_text('forged', encoding='utf-8')
    with pytest.raises(ValueError):
        reporting.load_multilevel_report_bundle(tmp_path/'cached')


def _paired_rows():
    rows=[]
    for mode in ('none','native_memory'):
        for phase,count in (('warmup',1),('measurement',5)):
            for index in range(count):
                for variant in ('baseline','candidate'):
                    rows.append({'mode':mode,'phase':phase,'index':index,'variant':variant,
                        'status':'completed','comparison':{'status':'equivalent'},
                        'lifecycle_seconds':11. if variant=='baseline' else 6.,
                        'trial':{'elapsed_seconds':10. if variant=='baseline' else 5.,
                            'trial_budget_exceeded':False,
                            'memory_kind':'process_peak_rss' if mode=='native_memory' else 'not_measured',
                            'memory_bytes':100_000_000 if mode=='native_memory' else None}})
    return rows


def test_paired_gate_accepts_complete_exact_gain_with_memory_accounting():
    from scripts.compare_report_restoration import _summarize, GATES
    summary=_summarize(_paired_rows(),GATES)
    assert summary['accepted'] and summary['median_workload_speedup']==2
    assert len(summary['paired_workload_speedups'])==5
    assert summary['median_native_peak_bytes']['candidate']==100_000_000


@pytest.mark.parametrize('fault',['missing','duplicate','science','warmup_failure','no_gain',
    'one_slower_pair','memory_growth','zero_time','lifecycle_regression'])
def test_paired_gate_rejects_incomplete_or_unacceptable_evidence(fault):
    from scripts.compare_report_restoration import _summarize, GATES
    rows=_paired_rows()
    if fault=='missing':rows.pop()
    elif fault=='duplicate':rows[-1]=copy.deepcopy(rows[-2])
    elif fault=='science':rows[-1]['comparison']['status']='not_equivalent'
    elif fault=='warmup_failure':rows[0]['status']='failed'
    elif fault=='no_gain':
        for row in rows:
            if row['variant']=='candidate':row['trial']['elapsed_seconds']=10.
    elif fault=='one_slower_pair':rows[3]['trial']['elapsed_seconds']=11.
    elif fault=='memory_growth':
        for row in rows:
            if row['variant']=='candidate' and row['mode']=='native_memory':
                row['trial']['memory_bytes']=150_000_000
    elif fault=='zero_time':rows[3]['trial']['elapsed_seconds']=0.
    else:
        for row in rows:
            if row['variant']=='candidate':row['lifecycle_seconds']=20.
    assert not _summarize(rows,GATES)['accepted']
