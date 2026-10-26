# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Bounded serial baseline campaigns; measurements never imply acceleration."""
from __future__ import annotations

import hashlib as _hashlib
import importlib.metadata as _metadata
import json as _json
import math as _math
import os as _os
from pathlib import Path as _Path
import platform as _platform
import statistics as _statistics
import subprocess as _subprocess
import sys as _sys
import tempfile as _tempfile
import time as _time

from .performance_contracts import (
    PerformanceWorkload as _Workload, MeasurementProtocol as _Protocol,
    PerformanceEnvironment as _Environment, PerformanceTrial as _Trial,
    EquivalenceContract as _Equivalence, compare_scientific_results as _compare,
    _canonical, _hash,
)

__all__ = ['capture_performance_environment', 'run_serial_campaign']
_MAX_BYTES = 16 * 1024 * 1024


def capture_performance_environment(source_commit, source_dirty):
    """Probe the current interpreter; source Git identity remains caller-declared."""
    import numpy as np
    import ncmemsim
    try:
        distribution = _metadata.version('ncmemsim')
    except _metadata.PackageNotFoundError:
        distribution = None
    return _Environment(
        source_commit, source_dirty, ncmemsim.__version__, distribution,
        str(_Path(ncmemsim.__file__).resolve()), _platform.python_version(), np.__version__,
        _platform.platform(), _platform.processor() or _platform.machine() or 'unknown',
        _os.cpu_count(), {k: _os.environ.get(k) for k in (
            'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')},
        'serial-reference',
    )


def _source_digest():
    root = _Path(__file__).resolve().parent
    return _hash({p.relative_to(root).as_posix(): _hashlib.sha256(
        p.read_text(encoding='utf-8').replace('\r\n', '\n').encode('utf-8')).hexdigest()
        for p in sorted(root.rglob('*.py'))})


def _peak_rss():
    if _sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    'PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage',
                    'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage',
                    'PagefileUsage', 'PeakPagefileUsage')]
        data = Counters()
        data.cb = ctypes.sizeof(data)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(data), data.cb):
            raise OSError(ctypes.get_last_error(), 'GetProcessMemoryInfo failed')
        return int(data.PeakWorkingSetSize), 'Windows GetProcessMemoryInfo PeakWorkingSetSize; whole fresh process including imports'
    if _sys.platform.startswith('linux') or _sys.platform == 'darwin':
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        multiplier = 1 if _sys.platform == 'darwin' else 1024
        return int(value * multiplier), 'getrusage(RUSAGE_SELF).ru_maxrss; whole fresh process including imports'
    raise NotImplementedError('native process high-water memory unavailable on this platform')


def _worker(request_file, response_file, storage):
    from .performance_workloads import execute_performance_workload
    request = _json.loads(_Path(request_file).read_text(encoding='utf-8'))
    workload = _Workload.from_dict(request['workload'])
    environment = capture_performance_environment(request['source_commit'], request['source_dirty'])
    response = {'environment': environment.to_dict(), 'source_tree_hash': _source_digest(),
                'status': 'failed', 'result': None, 'elapsed_seconds': None,
                'memory_bytes': None, 'memory_method': None, 'failure': None}
    start = None
    stage = 'instrumentation'
    try:
        if request['instrumentation'] == 'native_memory':
            _peak_rss()  # fail explicitly before the workload if unsupported
        elif request['instrumentation'] != 'none':
            raise NotImplementedError('R2 executes none/native_memory protocols only')
        stage = 'workload'
        start = _time.perf_counter()
        result = execute_performance_workload(workload, _Path(storage))
        response['elapsed_seconds'] = _time.perf_counter() - start
        stage = 'serialization'
        encoded = _canonical(result).encode('utf-8')
        if len(encoded) > _MAX_BYTES:
            raise ValueError('scientific result exceeds the 16 MiB payload limit')
        response['result'] = result
        if request['instrumentation'] == 'native_memory':
            response['memory_bytes'], response['memory_method'] = _peak_rss()
        response['status'] = 'completed'
    except Exception as exc:
        if start is not None and response['elapsed_seconds'] is None:
            response['elapsed_seconds'] = _time.perf_counter() - start
        response['failure'] = {'stage': stage, 'type': type(exc).__name__, 'message': str(exc) or type(exc).__name__}
    _Path(response_file).write_text(_canonical(response), encoding='utf-8')


def _invoke(workload, protocol, environment, timeout, directory):
    request = directory / 'request.json'
    response = directory / 'response.json'
    request.write_text(_canonical({'workload': workload.to_dict(),
        'source_commit': environment.to_dict()['source_commit'],
        'source_dirty': environment.to_dict()['source_dirty'],
        'instrumentation': protocol.to_dict()['instrumentation']}), encoding='utf-8')
    root = str(_Path(__file__).resolve().parent.parent)
    bootstrap = ('import sys;sys.path.insert(0,sys.argv[1]);'
                 'from ncmemsim.performance_execution import _worker;_worker(*sys.argv[2:])')
    # Output is redirected to files: a noisy worker cannot grow coordinator RAM.
    with (directory / 'stdout.log').open('wb') as stdout, (directory / 'stderr.log').open('wb') as stderr:
        _subprocess.run([_sys.executable, '-I', '-c', bootstrap, root, str(request),
                         str(response), str(directory / 'artifact')], cwd=directory,
                        stdout=stdout, stderr=stderr, timeout=timeout, check=True)
    if response.stat().st_size > 2 * _MAX_BYTES:
        raise ValueError('worker response exceeds resource limit')
    raw = _json.loads(response.read_text(encoding='utf-8'))
    _canonical(raw)
    actual = _Environment.from_dict(raw['environment'])
    if actual.to_dict() != environment.to_dict() or raw['source_tree_hash'] != _source_digest():
        raise ValueError('worker import/environment/source identity differs from coordinator')
    return raw


def _stats(values):
    if not values:
        return None
    median = _statistics.median(values)
    return {'count': len(values), 'median_s': median, 'min_s': min(values), 'max_s': max(values),
            'median_absolute_deviation_s': _statistics.median(abs(x - median) for x in values)}


def run_serial_campaign(workload, protocol, *, source_commit, source_dirty,
                        reference=None, equivalence=None):
    """Run one bounded case in fresh processes, retaining all declared indices.

    Default comparison is exact serial repeatability against a separate reference
    execution, not an independent physical accuracy or optimization acceptance gate.
    Optional caller-supplied reference and rules must be provided together.
    """
    if type(workload) is not _Workload or type(protocol) is not _Protocol:
        raise ValueError('typed workload and measurement protocol required')
    if len(workload.to_json().encode('utf-8')) > _MAX_BYTES:
        raise ValueError('workload exceeds the 16 MiB payload limit')
    p = protocol.to_dict()
    if p['instrumentation'] not in ('none', 'native_memory'):
        raise ValueError('R2 supports separate none/native_memory protocols only')
    if p['isolation'] != 'fresh_process':
        raise ValueError('R2 requires fresh_process isolation')
    if (reference is None) != (equivalence is None):
        raise ValueError('reference and equivalence must be supplied together')
    if reference is not None:
        if type(equivalence) is not _Equivalence:
            raise ValueError('typed equivalence required')
        reference_text = _canonical(reference)
        if len(reference_text.encode('utf-8')) > _MAX_BYTES:
            raise ValueError('reference exceeds the 16 MiB payload limit')
        reference = _json.loads(reference_text)
        _compare(equivalence, workload, reference, reference)
    else:
        equivalence = _Equivalence(workload.contract_hash, (), ('',),
            'Separate serial reference execution; exact full-payload repeatability, not a refinement/accuracy proof')
    environment = capture_performance_environment(source_commit, source_dirty)
    source_hash = _source_digest()
    start = _time.monotonic()
    trials = []
    reference_record = {'origin': 'caller_supplied' if reference is not None else 'separate_serial_execution',
                        'result': reference, 'failure': None, 'lifecycle_seconds': None}

    def invoke(directory):
        remaining = p['max_total_seconds'] - (_time.monotonic() - start)
        if remaining <= 0:
            return None, {'stage': 'campaign_budget', 'type': 'BudgetExhausted',
                          'message': 'No remaining scheduling budget; workload was not started'}, None
        began = _time.monotonic()
        try:
            raw = _invoke(workload, protocol, environment,
                          min(p['max_trial_seconds'], remaining), directory)
            return raw, None, _time.monotonic() - began
        except Exception as exc:
            return None, {'stage': 'worker', 'type': type(exc).__name__,
                          'message': ('fresh-process launch-to-exit timeout' if isinstance(exc, _subprocess.TimeoutExpired)
                                      else str(exc) or type(exc).__name__)}, _time.monotonic() - began

    with _tempfile.TemporaryDirectory(prefix='ncmemsim-r2-') as temporary:
        root = _Path(temporary)
        if reference is None:
            directory = root / 'reference'
            directory.mkdir()
            raw, failure, lifecycle = invoke(directory)
            reference_record.update(lifecycle_seconds=lifecycle,
                failure=failure if raw is None else raw['failure'],
                result=None if raw is None or raw['status'] != 'completed' else raw['result'])
            reference = reference_record['result']
        for phase, count in (('warmup', p['warmup_count']), ('measurement', p['measured_count'])):
            for index in range(count):
                directory = root / f'{phase}-{index}'
                directory.mkdir()
                raw, failure, lifecycle = invoke(directory)
                result = None if raw is None else raw['result']
                status = ('unavailable' if lifecycle is None else 'failed') if raw is None else raw['status']
                trial = _Trial(workload, protocol, environment, phase, index, status,
                    None if raw is None else raw['elapsed_seconds'],
                    None if result is None else _hash(result), failure if raw is None else raw['failure'],
                    'process_peak_rss' if raw is not None and raw['memory_bytes'] is not None else 'not_measured',
                    None if raw is None else raw['memory_bytes'], None if raw is None else raw['memory_method'])
                comparison = (None if result is None or reference is None else
                              _compare(equivalence, workload, reference, result))
                trials.append({'trial': trial.to_dict(), 'result': result, 'comparison': comparison,
                               'lifecycle_seconds': lifecycle})
    measured = [x for x in trials if x['trial']['phase'] == 'measurement']
    accepted = [x for x in measured if x['trial']['status'] == 'completed'
                and not x['trial']['trial_budget_exceeded'] and x['comparison'] is not None
                and x['comparison']['status'] == 'equivalent']
    lifecycle_seconds = _time.monotonic() - start
    campaign_budget_exceeded = lifecycle_seconds > p['max_total_seconds']
    complete = (not campaign_budget_exceeded and reference is not None and len(accepted) == p['measured_count']
                and all(x['trial']['status'] == 'completed' and not x['trial']['trial_budget_exceeded']
                        and x['comparison'] is not None
                        and x['comparison']['status'] == 'equivalent' for x in trials))
    return {'schema_version': 'serial-performance-campaign-v1', 'workload': workload.to_dict(),
        'protocol': p, 'environment': environment.to_dict(), 'source_tree_hash': source_hash,
        'reference': reference_record, 'equivalence': equivalence.to_dict(), 'trials': trials,
        'summary': {'complete': complete, 'declared_measurement_count': p['measured_count'],
            'completed_measurement_count': sum(x['trial']['status'] == 'completed' for x in measured),
            'equivalent_measurement_count': len(accepted),
            'failed_measurement_count': sum(x['trial']['status'] == 'failed' for x in measured),
            'unavailable_measurement_count': sum(x['trial']['status'] == 'unavailable' for x in measured),
            'completed_observation_statistics': _stats([x['trial']['elapsed_seconds'] for x in measured
                                                       if x['trial']['status'] == 'completed']),
            'complete_equivalent_statistics': _stats([x['trial']['elapsed_seconds'] for x in accepted]) if complete else None,
            'campaign_lifecycle_seconds': lifecycle_seconds,
            'campaign_budget_exceeded': campaign_budget_exceeded,
            'speedup_accepted': False},
        'limits': ['Fresh worker startup/imports and result transfer are in lifecycle time, not workload elapsed time.',
                   'Timeout bounds worker launch-to-exit; total budget gates scheduling and bounds each worker by remaining time.',
                   'Coordinator comparison/cleanup overhead is recorded but not preemptible; no hard RAM or disk cap.',
                   'Native RSS includes the whole fresh process; no workload-only native peak attribution.',
                   'Exact repeats are repeatability evidence, not physical accuracy, calibration or speedup.']}
