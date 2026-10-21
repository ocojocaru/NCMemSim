# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Registered serial scientific workloads with owned, explicit inputs."""
from __future__ import annotations

import dataclasses as _dataclasses
from enum import Enum as _Enum
import hashlib as _hashlib
import math as _math
from pathlib import Path as _Path

from .performance_contracts import PerformanceWorkload as _Workload, _canonical

__all__ = ['execute_performance_workload']


def _snapshot(value, *, allow_nan=False):
    import numpy as np
    if isinstance(value, _Enum):
        return _snapshot(value.value)
    if _dataclasses.is_dataclass(value):
        return {f.name: _snapshot(getattr(value, f.name)) for f in _dataclasses.fields(value)}
    if isinstance(value, np.ndarray):
        return _snapshot(value.tolist(), allow_nan=allow_nan)
    if isinstance(value, np.generic):
        return _snapshot(value.item(), allow_nan=allow_nan)
    if type(value) in (list, tuple):
        return [_snapshot(x, allow_nan=allow_nan) for x in value]
    if type(value) is dict:
        return {k: _snapshot(v, allow_nan=allow_nan or k in (
            'optical_absorption_fraction_by_fg', 'optical_alpha_nc_by_fg_m_inv',
            'optical_alpha_eff_by_fg_m_inv', 'optical_absorption_fraction')) for k, v in value.items()}
    if type(value) is float and not _math.isfinite(value):
        if _math.isnan(value):
            if allow_nan:
                return {'nonfinite_number': 'nan', 'meaning': 'unavailable optical diagnostic'}
            raise ArithmeticError('NaN scientific output is not a valid baseline')
        return {'nonfinite_number': 'positive_infinity' if value > 0 else 'negative_infinity'}
    _canonical(value)  # reject unsupported leaves, never stringify
    return value


def _trajectory(context, settings):
    from . import DeviceState
    import numpy as np
    if set(settings) != {'initial_p1', 'voltage_V', 'duration_s', 'dt_s'}:
        raise ValueError('unknown or missing trajectory settings')
    if any(type(settings[k]) not in (int, float) or not _math.isfinite(settings[k])
           for k in ('voltage_V', 'duration_s', 'dt_s')):
        raise ValueError('finite nonboolean trajectory settings required')
    if settings['duration_s'] <= 0 or settings['dt_s'] <= 0 or settings['duration_s'] / settings['dt_s'] > 4096:
        raise ValueError('positive bounded duration/time-step count required')
    simulator = context.create_simulator()
    if simulator.device.number_of_fgs() > 3 or any(fg.grid_points > 257 for fg in simulator.device.floating_gates()):
        raise ValueError('R2 controlled trajectory supports at most three FGs and 257 grid points per FG')
    state = DeviceState.empty_for_device(simulator.device)
    initial_p1 = settings['initial_p1']
    if len(initial_p1) != len(state.floating_gates):
        raise ValueError('one declared initial P1 per floating gate required')
    for fg, p1 in zip(state.floating_gates, initial_p1, strict=True):
        if type(p1) not in (int, float) or not _math.isfinite(p1) or not 0 <= p1 <= 1:
            raise ValueError('initial P1 outside [0,1]')
        fg.P0[:] = 1 - p1
        fg.P1[:] = p1
    initial = _snapshot(state)
    output = simulator.relax_voltage(state, settings['voltage_V'], settings['duration_s'], settings['dt_s'])
    final = output['state']
    final.validate()
    mass_error = max(float(np.max(np.abs(fg.P0 + fg.P1 + fg.P2 - 1))) for fg in final.floating_gates)
    return {'context': context.to_dict(), 'initial_state': initial, 'output': _snapshot(output),
            'max_probability_mass_error': mass_error,
            'conservation_scope': 'probability normalization; open device exchanges charge with electrodes'}


def _model_evaluator(realization, settings):
    from . import DeviceState, PhysicsModel
    from .fieldsolver import FieldSolver1D
    from .transport import AdvancedTransportEngine, TransportEngine, TransportConfig
    from .tunneling import TunnelingConfig
    from .kinetics import KineticsConfig
    import numpy as np
    if realization.sample.sample_index in settings['fail_sample_indices']:
        raise ArithmeticError('declared synthetic workflow failure; not a physical result')
    if type(settings['steps']) is not int or not 1 <= settings['steps'] <= 64:
        raise ValueError('R2 model step count must be between 1 and 64')
    physics = PhysicsModel.default()
    physics.tunneling.config = TunnelingConfig(**settings['tunneling_config'])
    physics.occupancy.config = KineticsConfig(**settings['occupancy_config'])
    baseline = TransportEngine(physics.tunneling, TransportConfig(**settings['transport_config']))
    engine = AdvancedTransportEngine(baseline, realization.model_context.advanced_transport)
    device = realization.device
    profile = FieldSolver1D().solve(device, settings['gate_voltage_V'], np.zeros(device.number_of_fgs()))
    state = DeviceState.empty_for_device(device)
    state.floating_gates[0].P0[:] = 0
    state.floating_gates[0].P1[:] = 1
    initial = _snapshot(state)
    sites = np.array([baseline._sheet_site_density(physics.occupancy, fg) for fg in device.floating_gates()])
    def electrons(current):
        return float(np.sum(2 * sites * current.mean_normalized_occupations))
    initial_electrons = electrons(state)
    error = 0.0
    channels = []
    for _ in range(settings['steps']):
        state, result = engine.step(device, state, profile, physics.occupancy,
                                    settings['total_time_s'] / settings['steps'])
        state.validate()
        channels.append(_snapshot(result))
        error = max(error, abs(electrons(state) - initial_electrons) / initial_electrons)
    if error > settings['conservation_rtol']:
        raise ArithmeticError('closed redistribution electron conservation failed')
    return {'initial_state': initial, 'final_state': _snapshot(state), 'steps': channels,
            'initial_electron_sheet_m2': initial_electrons, 'final_electron_sheet_m2': electrons(state),
            'max_relative_conservation_error': error}


def execute_performance_workload(workload, storage):
    """Execute a registered case serially; callers decide and measure its scope.

    R2 cases use end_to_end: owned input restoration, fresh state, computation and
    scientific projection; dependency imports on first use are included. Export
    also includes file writing/reading. Worker startup and outer JSON transfer are
    excluded here and separately retained by the campaign lifecycle observation.
    """
    if type(workload) is not _Workload or workload.to_dict()['scope'] != ['end_to_end']:
        raise ValueError('R2 registered cases require end_to_end scope')
    source = workload.scientific_inputs
    if set(source) != {'case', 'payload'} or type(source['payload']) is not dict:
        raise ValueError('registered case and explicit payload required')
    case, payload = source['case'], source['payload']
    fields = {
        'trajectory': {'context', 'temperature_K', 'settings'},
        'thermal': {'context', 'temperature_K', 'settings'},
        'sequence': {'experiment'}, 'optical': {'experiment'},
        'dtco': {'context', 'binding_path', 'values_nm', 'settings'},
        'device_manifest': {'context', 'manifest', 'settings', 'fail_sample_indices'},
        'model_manifest': {'context', 'manifest', 'settings'},
        'retention': {'plan'}, 'restore': {'report'}, 'export': {'report'},
    }
    if case not in fields or set(payload) != fields[case]:
        raise ValueError('unknown or missing registered case payload fields')
    count = (len(payload['manifest']['samples']) if case in ('device_manifest', 'model_manifest') else
             len(payload['values_nm']) if case == 'dtco' else
             len(payload['report']['cases']) if case in ('restore', 'export') else
             len(payload['experiment']['sequence']['steps']) if case == 'sequence' else
             2 * len(payload['experiment']['electrical']['sequence']['steps']) if case == 'optical' else
             len(payload['plan']['delays_s']) * len(payload['plan']['prepared']['plan']['levels']) if case == 'retention' else 1)
    if workload.to_dict()['logical_item_count'] != count or not 1 <= count <= 64:
        raise ValueError('registered logical item count mismatch or resource limit')
    expected = {'trajectory': ('relaxation', 'state_chain'), 'thermal': ('relaxation', 'state_chain'),
                'sequence': ('sequence', 'state_chain'), 'optical': ('sequence', 'state_chain'),
                'dtco': ('sweep', 'independent_items'), 'device_manifest': ('ensemble', 'independent_items'),
                'model_manifest': ('ensemble', 'independent_items'), 'retention': ('retention', 'independent_items'),
                'restore': ('restore', 'static_restore'), 'export': ('export', 'static_export')}
    if case not in expected:
        raise ValueError('unsupported registered scientific case')
    if (workload.to_dict()['workflow_kind'], workload.to_dict()['dependency_kind']) != expected[case]:
        raise ValueError('registered workload kind/dependency mismatch')
    from .temperature_context import ThermalContext
    if case in ('trajectory', 'thermal'):
        context = ThermalContext.from_dict(payload['context']).resolve(temperature_K=payload['temperature_K'])
        result = _trajectory(context, payload['settings'])
    elif case == 'sequence':
        from .multilevel_contracts import ElectricalSequenceExperiment
        from .multilevel_execution import run_electrical_sequence
        experiment = ElectricalSequenceExperiment.from_dict(payload['experiment'])
        result = run_electrical_sequence(experiment).to_dict()
    elif case == 'optical':
        from .multilevel_optical import OpticalSequenceExperiment, run_matched_optical_sequence
        experiment = OpticalSequenceExperiment.from_dict(payload['experiment'])
        result = run_matched_optical_sequence(experiment).to_dict()
    elif case == 'retention':
        from .multilevel_retention import MultilevelRetentionPlan, run_multilevel_retention
        result = run_multilevel_retention(MultilevelRetentionPlan.from_dict(payload['plan'])).to_dict()
    elif case == 'dtco':
        from .dtco import (ExperimentSpec, DesignVariable, DesignVariableRole, ParameterBinding,
                           BindingScope, run_cartesian_sweep)
        device = ThermalContext.from_dict(payload['context']).resolve().device
        spec = ExperimentSpec.from_device(name='R2 serial independent geometry points', device=device, variables=(
            DesignVariable('tunnel_nm', ParameterBinding(BindingScope.DEVICE, tuple(payload['binding_path'])),
                           tuple(payload['values_nm']), DesignVariableRole.GEOMETRY, 'nm'),))
        def evaluate(candidate, protocol, point):
            context = ThermalContext.from_nominal(candidate).resolve()
            return _trajectory(context, payload['settings'])
        result = run_cartesian_sweep(spec, device, evaluate, evaluation_id='r2-full-state-trajectory-v1',
                                    evaluation_parameters=payload['settings']).to_dict()
    elif case == 'device_manifest':
        from .ensemble import SampleManifest, execute_sample_manifest
        context = ThermalContext.from_dict(payload['context'])
        manifest = SampleManifest.from_dict(payload['manifest'])
        def evaluate(device, protocol, realization):
            if realization.identity.sample_index in payload['fail_sample_indices']:
                raise ArithmeticError('declared synthetic workflow failure; not a physical result')
            return _trajectory(ThermalContext.from_nominal(device).resolve(), payload['settings'])
        result = execute_sample_manifest(manifest, context.resolve().device, evaluate,
            evaluation_id='r2-device-manifest-full-state-v1', evaluation_parameters={
                'settings': payload['settings'], 'fail_sample_indices': payload['fail_sample_indices']}).to_dict()
    elif case == 'model_manifest':
        from .ensemble.model_sampling import ModelSampleManifest
        from .ensemble.model_execution import execute_model_sample_manifest
        manifest = ModelSampleManifest.from_dict(payload['manifest'])
        device = ThermalContext.from_dict(payload['context']).resolve().device
        result = execute_model_sample_manifest(manifest, device, _model_evaluator,
            evaluation_id='r2-fixed-field-full-state-model-v1', workflow_context=payload['settings']).to_dict()
    else:
        from .multilevel_reporting import MultilevelReport, write_multilevel_report
        report = MultilevelReport.from_dict(payload['report'])
        result = {'report': report.to_dict()}
        if case == 'export':
            destination = _Path(storage)
            write_multilevel_report(report, destination)
            result['files'] = {p.name: {'bytes': p.stat().st_size,
                                      'sha256': _hashlib.sha256(p.read_bytes()).hexdigest()}
                               for p in sorted(destination.iterdir()) if p.is_file()}
    result = _snapshot(result)
    _canonical(result)
    return {'case': case, 'declared_inputs': source, 'scientific_result': result}
