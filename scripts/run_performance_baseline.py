# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Run the Phase R2 bounded serial baseline; never replace historical benchmark data."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ncmemsim import DeviceBuilder
from ncmemsim.performance_contracts import PerformanceWorkload, MeasurementProtocol
from ncmemsim.performance_execution import run_serial_campaign
from ncmemsim.temperature_context import ThermalContext


def build_workloads():
    """Construct owned inputs once; all samples are stored before measurement."""
    from examples.phase_q2_electrical_sequence_reference import build_experiment
    from examples.phase_q3_multilevel_reference import build_plan
    from examples.phase_q4_gradual_update_reference import build as optical_experiment
    from examples.phase_m3_si_temperature_reference import build_context as thermal_context
    from examples.phase_l3_tat_density_variability import build_reference, workflow_settings
    from ncmemsim.multilevel_analysis import run_multilevel_study
    from ncmemsim.multilevel_retention import MultilevelRetentionPlan
    from ncmemsim.multilevel_contracts import PulseSequenceEvidence
    from ncmemsim.ensemble import (ConstantDistribution, UniformDistribution, StochasticVariable,
        PhysicalDomain, EnsembleSpec, RNGSpec, SamplingSpec, generate_sample_manifest)
    from ncmemsim.dtco import ParameterBinding, BindingScope
    from ncmemsim.materials.provenance import ParameterProvenance, ParameterStatus
    from ncmemsim.ensemble.model_sampling import generate_model_sample_manifest

    cases = []
    def add(name, case, kind, dependency, count, payload):
        cases.append(PerformanceWorkload(name, kind, {'case': case, 'payload': payload},
            ('end_to_end',), dependency, count,
            'R2 bounded synthetic compact-model reference; no physical calibration or speedup claim'))

    def settings(n):
        return {'voltage_V': 2., 'duration_s': 2e-5, 'dt_s': 1e-5, 'initial_p1': [.2] * n}
    for n in (1, 2, 3):
        context = ThermalContext.from_nominal(DeviceBuilder.v2(n))
        add(f'trajectory-{n}fg', 'trajectory', 'relaxation', 'state_chain', 1,
            {'context': context.to_dict(), 'temperature_K': 300., 'settings': settings(n)})
    nominal = ThermalContext.from_nominal(DeviceBuilder.v2(1))
    add('independent-dtco', 'dtco', 'sweep', 'independent_items', 2,
        {'context': nominal.to_dict(), 'binding_path': ['layers', 'tunnel_sio2', 'thickness_nm'],
         'values_nm': [3., 3.2], 'settings': settings(1)})
    for varied in (False, True):
        nominal_fraction = nominal.resolve().device.floating_gates()[0].electrically_active_fraction
        distribution = (UniformDistribution(.8 * nominal_fraction, nominal_fraction) if varied
                        else ConstantDistribution(nominal_fraction))
        variable = StochasticVariable('active_fraction', ParameterBinding(BindingScope.DEVICE,
            ('layers', 'FG1', 'electrically_active_fraction')), distribution, '1', PhysicalDomain(lower=0., upper=1.),
            ParameterProvenance('R2 synthetic fraction assumption', ParameterStatus.ASSUMED),
            'Stored two-sample diagnostic; not a yield estimate', nominal_value=nominal_fraction)
        spec = EnsembleSpec.from_device(name='R2 device '+str(varied), device=nominal.resolve().device, variables=(variable,))
        manifest = generate_sample_manifest(SamplingSpec(spec, RNGSpec(seed=2102), 2))
        add('device-'+('varied' if varied else 'zero'), 'device_manifest', 'ensemble', 'independent_items', 2,
            {'context': nominal.to_dict(), 'manifest': manifest.to_dict(), 'settings': settings(1),
             'fail_sample_indices': [1] if varied else []})
    for constant in (True, False):
        device, spec = build_reference(constant=constant, sample_count=2)
        for fg in device.floating_gates():
            fg.grid_points = 3
        # Geometry/grid identity changes require reconstructing the owned study.
        from ncmemsim.ensemble.model_contracts import ModelVariabilitySpec
        study = ModelVariabilitySpec.from_device(name=spec.study.name, device=device,
            model_context=spec.study.model_context, variables=spec.study.variables)
        manifest = generate_model_sample_manifest(replace(spec, study=study))
        settings_model = {**workflow_settings(4), 'fail_sample_indices': [] if constant else [1]}
        add('model-'+('zero' if constant else 'varied'), 'model_manifest', 'ensemble', 'independent_items', 2,
            {'context': ThermalContext.from_nominal(device).to_dict(),
             'manifest': manifest.to_dict(), 'settings': settings_model})
    experiment = build_experiment(internal_dt_s=1e-9)
    add('electrical-sequence', 'sequence', 'sequence', 'state_chain', 4,
        {'experiment': experiment.to_dict()})
    _, _, optical, _ = optical_experiment(internal_dt_s=1e-8)
    add('matched-optical', 'optical', 'sequence', 'state_chain', 8,
        {'experiment': optical.to_dict()})
    for temperature in (250., 350.):
        add(f'thermal-{temperature:g}K', 'thermal', 'relaxation', 'state_chain', 1,
            {'context': thermal_context().to_dict(), 'temperature_K': temperature,
             'settings': {'voltage_V': 3., 'duration_s': 5e-7, 'dt_s': 5e-8, 'initial_p1': [0.]}})
    prepared = run_multilevel_study(build_plan(internal_dt_s=1e-8))
    evidence = PulseSequenceEvidence('R2 short retention probe', 'Q3 numerical preparation', 'synthetic',
        'Independent dark delay probes; no retention lifetime or physical calibration')
    retention = MultilevelRetentionPlan(prepared, (0., 1e-7), 0., 1e-8, evidence)
    add('multilevel-retention', 'retention', 'retention', 'independent_items', 6, {'plan': retention.to_dict()})
    archive = ROOT / 'tests/fixtures/archives/v1_8_preparation/multilevel_report.json'
    raw = json.loads(archive.read_text(encoding='utf-8'))
    for case in ('restore', 'export'):
        add('strict-'+case, case, case, 'static_'+case, len(raw['cases']), {'report': raw})
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='new evidence directory; never overwritten')
    parser.add_argument('--case', action='append', dest='cases', help='explicit workload ID, repeatable')
    parser.add_argument('--skip-refinement', action='store_true', help='omit untimed dt/dt/2 diagnostic; selection recorded')
    parser.add_argument('--native-memory', action='store_true', help='separate RSS campaign, not uninstrumented timing')
    parser.add_argument('--max-trial-seconds', type=float, default=120.)
    parser.add_argument('--max-total-seconds', type=float, default=900., help='per-workload scheduling budget including reference')
    args = parser.parse_args()
    protocol = MeasurementProtocol(isolation='fresh_process', instrumentation='native_memory' if args.native_memory else 'none',
        max_trial_seconds=args.max_trial_seconds, max_total_seconds=args.max_total_seconds)
    workloads = build_workloads()
    available = {w.to_dict()['workload_id'] for w in workloads}
    if args.cases and (len(set(args.cases)) != len(args.cases) or set(args.cases) - available):
        parser.error('case names must be unique supported workload IDs: '+', '.join(sorted(available)))
    if args.cases:
        workloads = [w for w in workloads if w.to_dict()['workload_id'] in args.cases]
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip())
    args.output.mkdir(parents=True, exist_ok=False)
    refinement = []
    if not args.skip_refinement:
        from copy import deepcopy
        from ncmemsim.performance_workloads import execute_performance_workload
        for workload in workloads:
            if workload.scientific_inputs['case'] not in ('trajectory', 'thermal'):
                continue
            inputs = deepcopy(workload.scientific_inputs)
            inputs['payload']['settings']['dt_s'] /= 2
            fine = PerformanceWorkload(workload.to_dict()['workload_id']+'-dt-half',
                workload.to_dict()['workflow_kind'], inputs, ('end_to_end',), 'state_chain', 1,
                'Untimed paired dt diagnostic; changed inputs retained, not an exact-solution bound')
            coarse_output = execute_performance_workload(workload, args.output/'unused-coarse')['scientific_result']
            fine_output = execute_performance_workload(fine, args.output/'unused-fine')['scientific_result']
            populations = lambda result: [v for fg in result['output']['state']['floating_gates']
                for key in ('P0', 'P1', 'P2') for v in fg[key]]
            refinement.append({'case': workload.to_dict()['workload_id'],
                'coarse_workload': workload.to_dict(), 'fine_workload': fine.to_dict(),
                'coarse_result': coarse_output, 'fine_result': fine_output,
                'max_population_absolute_difference': max(abs(a-b) for a,b in zip(
                    populations(coarse_output), populations(fine_output), strict=True)),
                'signed_vfb_absolute_difference_V': abs(coarse_output['output']['vfb_V']-fine_output['output']['vfb_V']),
                'interpretation': 'Paired dt/dt/2 diagnostic only; not an accuracy bound or proof of convergence'})
    (args.output/'refinement.json').write_text(json.dumps({'performed': not args.skip_refinement,
        'cases': refinement}, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    summaries = []
    for workload in workloads:
        name = workload.to_dict()['workload_id']
        result = run_serial_campaign(workload, protocol, source_commit=commit, source_dirty=dirty)
        data = json.dumps(result, indent=2, allow_nan=False).encode('utf-8') + b'\n'
        (args.output / (name+'.json')).write_bytes(data)
        row = {'case': name, 'workload_hash': workload.contract_hash, 'file_sha256': hashlib.sha256(data).hexdigest(),
               'source_tree_hash': result['source_tree_hash'], 'environment': result['environment'],
               'summary': result['summary']}
        summaries.append(row)
        print(name, json.dumps(result['summary']), flush=True)
    summary = {'schema_version': 'r2-serial-suite-index-v1', 'source_commit': commit, 'source_dirty': dirty,
        'protocol': protocol.to_dict(), 'cases': summaries,
        'limits': ['Current-host observations; no cross-host speedup or absolute CI timing threshold.',
                   'Fresh-process serial repeatability; existing scientific validation/refinement evidence remains required.',
                   'DEVICE/MODEL varied cases deliberately retain a declared failed sample; matching that negative result is not success of the sample.',
                   'Prepared multilevel inputs and stored manifests are built once outside campaign timing.',
                   'Historical benchmark_results.json and R0 profiling evidence are never overwritten.']}
    summary['refinement_performed'] = not args.skip_refinement
    (args.output / 'index.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    if not all(row['summary']['complete'] for row in summaries):
        raise SystemExit('Incomplete or non-equivalent campaign; all evidence retained')


if __name__ == '__main__':
    main()
