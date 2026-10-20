# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Owned fixed-spectrum pulse trains with explicit dark segments and matched controls."""
from __future__ import annotations
from dataclasses import dataclass as _dataclass
import math as _math
from .multilevel_contracts import (ElectricalSequenceExperiment as _Experiment,
    _Archive, _canonical, _keys, _load, _match, _number)
from .multilevel_execution import (_projection as _electrical_projection, _perform_read,
    _state, ElectricalSequenceResult as _ElectricalResult, run_electrical_sequence as _run_dark)
from .thermal_reporting import _state_payload
from .ensemble.execution import _runtime
from .spectral_context import SpectralSimulationContext as _Context, _capture
from .photo import PhotoTransitionConfig as _Config, PhotoTransitionWeights as _Weights

__all__ = ['OpticalSequenceExperiment', 'OpticalSequenceResult',
           'MatchedOpticalSequenceResult', 'run_optical_sequence', 'run_matched_optical_sequence']


@_dataclass(frozen=True)
class OpticalSequenceExperiment(_Archive):
    """One fixed source at stack entrance; selected physical steps alone receive light.

    The electrical request owns the common waveform, state and dark read policy.
    Its electrical-only schema is retained unchanged, not used to claim dark physics
    for this new optical workflow. Area is the assumed uniform illuminated footprint.
    """
    electrical: _Experiment
    spectral_context: _Context
    illuminated_step_ids: tuple[str, ...]
    capture_efficiency: float
    transition_weights: tuple[float, float, float, float]
    illuminated_area_m2: float

    def __post_init__(self):
        if type(self.electrical) is not _Experiment or type(self.spectral_context) is not _Context:
            raise ValueError('owned electrical request and spectral context required')
        electrical = _Experiment.from_dict(self.electrical.to_dict())
        context = _Context.from_dict(self.spectral_context.to_dict())
        if electrical.context.context_hash != context.resolution.context_hash:
            raise ValueError('optical and electrical resolved contexts differ')
        ids = self.illuminated_step_ids
        if type(ids) is not tuple or not ids or any(type(x) is not str for x in ids) or len(set(ids)) != len(ids):
            raise ValueError('unique immutable illuminated step identities required')
        expected = tuple(s.step_id for s in electrical.sequence.steps if s.step_id in ids)
        if ids != expected or any(s.role == 'idle' and s.step_id in ids for s in electrical.sequence.steps):
            raise ValueError('ordered known non-idle illuminated steps required')
        if type(self.transition_weights) is not tuple or len(self.transition_weights) != 4:
            raise ValueError('immutable r01,r12,r10,r21 weights required')
        weights = tuple(_number(x, 'transition weight', nonnegative=True) for x in self.transition_weights)
        efficiency = _number(self.capture_efficiency, 'capture efficiency', nonnegative=True)
        _capture(_Config(efficiency), _Weights(*weights))
        area = _number(self.illuminated_area_m2, 'uniform illuminated area', positive=True)
        object.__setattr__(self, 'electrical', electrical)
        object.__setattr__(self, 'spectral_context', context)
        object.__setattr__(self, 'capture_efficiency', efficiency)
        object.__setattr__(self, 'transition_weights', weights)
        object.__setattr__(self, 'illuminated_area_m2', area)
        # Reject overflowing requested optical budgets before any solver execution.
        _budget(self, len(electrical.sequence.steps))

    def to_dict(self):
        return {'schema_version': 'optical-sequence-experiment-v1',
                'electrical': self.electrical.to_dict(), 'spectral_context': self.spectral_context.to_dict(),
                'illuminated_step_ids': list(self.illuminated_step_ids),
                'capture_efficiency': self.capture_efficiency, 'transition_weights': list(self.transition_weights),
                'illuminated_area_m2': self.illuminated_area_m2,
                'reference_plane': 'entrance_of_modelled_stack', 'spatial_profile': 'assumed_uniform',
                'source_policy': 'one_fixed_spectrum_only_selected_steps',
                'read_illumination': 'dark', 'experimental_qualification': False}

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ('schema_version', 'electrical', 'spectral_context', 'illuminated_step_ids',
                    'capture_efficiency', 'transition_weights', 'illuminated_area_m2', 'reference_plane',
                    'spatial_profile', 'source_policy', 'read_illumination', 'experimental_qualification'))
        if type(raw['illuminated_step_ids']) is not list or type(raw['transition_weights']) is not list:
            raise ValueError('archived optical identity/weight arrays required')
        obj = cls(_Experiment.from_dict(raw['electrical']), _Context.from_dict(raw['spectral_context']),
                  tuple(raw['illuminated_step_ids']), raw['capture_efficiency'],
                  tuple(raw['transition_weights']), raw['illuminated_area_m2'])
        _match(raw, obj.to_dict())
        return obj


def _budget(experiment, count):
    steps = experiment.electrical.sequence.steps[:count]
    exposure = _number(_math.fsum(s.duration_s for s in steps if s.step_id in experiment.illuminated_step_ids),
                       'completed scheduled exposure', nonnegative=True)
    p = experiment.spectral_context.optical_result.projection
    s = p['summary']
    def product(value, scale):
        return _number(value * scale, 'optical budget', nonnegative=True)
    area = experiment.illuminated_area_m2
    irradiance = {key: s[key] for key in ('incident_irradiance_W_m2', 'absorbed_irradiance_W_m2',
        'fg_absorbed_irradiance_W_m2', 'passive_absorbed_irradiance_W_m2', 'transmitted_irradiance_W_m2')}
    power = {key.replace('irradiance_W_m2', 'power_W'): product(value, area) for key, value in irradiance.items()}
    fluence = {key.replace('irradiance_W_m2', 'fluence_J_m2'): product(value, exposure)
               for key, value in irradiance.items()}
    energy = {key.replace('fluence_J_m2', 'energy_J'): product(value, area) for key, value in fluence.items()}
    fg = {row['layer_name']: product(row['absorption']['summary']['absorbed_photon_flux_m2_s'], exposure)
          for row in p['layers'] if row['role'] == 'floating_gate'}
    return {'scheduled_exposure_s': exposure, 'irradiance_W_m2': irradiance,
            'optical_power_W': power, 'optical_fluence_J_m2': fluence, 'optical_energy_J': energy,
            'absorbed_photon_fluence_by_fg_m2': fg,
            'scope': 'completed_physical_steps_only_not_total_programming_energy'}


def _projection(raw):
    _keys(raw, ('schema_version', 'experiment', 'experiment_hash', 'runtime',
                'initial_read', 'steps', 'failure', 'summary'))
    if raw['schema_version'] != 'optical-sequence-result-v1':
        raise ValueError('unsupported optical sequence result schema')
    exp = OpticalSequenceExperiment.from_dict(raw['experiment'])
    if raw['experiment_hash'] != exp.contract_hash:
        raise ValueError('optical sequence source mismatch')
    # Reuse the static state/time/read/failure auditor, never its dark runner or
    # public result schema. That audit does not infer the origin of a trajectory.
    audit = dict(raw, schema_version='electrical-sequence-result-v1',
                 experiment=exp.electrical.to_dict(), experiment_hash=exp.electrical.contract_hash)
    return {**_electrical_projection(audit), 'workflow': 'fixed_spectrum_sequence',
            'optical_budget': _budget(exp, len(raw['steps']))}


@_dataclass(frozen=True)
class OpticalSequenceResult(_Archive):
    """Original optical physical/read trajectory with statically audited projections."""
    record_json: str

    def __post_init__(self):
        raw = _load(self.record_json)
        summary = _projection(raw)
        _match(raw['summary'], summary)
        object.__setattr__(self, 'record_json', _canonical(raw))

    def to_dict(self):
        return _load(self.record_json)

    @property
    def summary(self):
        return self.to_dict()['summary']

    @property
    def final_state(self):
        raw = self.to_dict()
        exp = OpticalSequenceExperiment.from_dict(raw['experiment'])
        state = raw['steps'][-1]['final_state'] if raw['steps'] else raw['experiment']['electrical']['initial_state']
        return _state(state, exp.electrical.context.device)

    @classmethod
    def from_dict(cls, raw):
        return cls(_canonical(raw))


def run_optical_sequence(experiment):
    """Continue physical states; light is explicit per step, every read is dark."""
    if type(experiment) is not OpticalSequenceExperiment:
        raise ValueError('owned optical sequence experiment required')
    exp = OpticalSequenceExperiment.from_dict(experiment.to_dict())
    electrical = exp.electrical
    raw = {'schema_version': 'optical-sequence-result-v1', 'experiment': exp.to_dict(),
           'experiment_hash': exp.contract_hash, 'runtime': _runtime(),
           'initial_read': None, 'steps': [], 'failure': None, 'summary': None}
    stage, index = 'setup', None
    try:
        simulator = exp.spectral_context.create_simulator()
        stage = 'initial_read'
        current = _load(electrical.initial_state_json)
        raw['initial_read'] = _perform_read(simulator, current, electrical)
        for index, step in enumerate(electrical.sequence.steps):
            stage = 'step'
            lit = step.step_id in exp.illuminated_step_ids
            out = simulator.relax_voltage(_state(current, simulator.device), step.gate_voltage_V,
                dwell_time_s=step.duration_s, internal_dt_s=step.internal_dt_s,
                light_source=exp.spectral_context.optical_result.source if lit else None,
                photo_config=_Config(exp.capture_efficiency) if lit else None,
                photo_weights=_Weights(*exp.transition_weights) if lit else None,
                occupancy_integrator='backward_euler')
            simulator._require_context()
            final = _state_payload(out['state'], simulator.device)
            _state(final, simulator.device)
            if final['time_s'] != current['time_s'] + step.duration_s:
                raise ValueError('solver returned inconsistent physical clock')
            event = {'step_index': index, 'step_id': step.step_id, 'initial_state': current,
                     'final_state': final, 'read': None}
            raw['steps'].append(event)
            current = final
            stage = 'read'
            event['read'] = _perform_read(simulator, current, electrical)
    except Exception as exc:
        raw['failure'] = {'stage': stage, 'step_index': index,
            'exception_type': type(exc).__module__ + '.' + type(exc).__qualname__,
            'message': str(exc).strip() or type(exc).__name__}
    raw['summary'] = _projection(raw)
    return OpticalSequenceResult.from_dict(raw)


def _paired_projection(raw):
    _keys(raw, ('schema_version', 'light', 'dark', 'summary'))
    if raw['schema_version'] != 'matched-optical-sequence-result-v1':
        raise ValueError('unsupported matched optical sequence schema')
    light = OpticalSequenceResult.from_dict(raw['light'])
    dark = _ElectricalResult.from_dict(raw['dark'])
    exp = OpticalSequenceExperiment.from_dict(raw['light']['experiment'])
    _match(exp.electrical.to_dict(), raw['dark']['experiment'])
    a, b = light.summary, dark.summary
    count = min(a['completed_read_count'], b['completed_read_count'])
    contrasts = [_number(x-y, 'matched read contrast') for x, y in
                 zip(a['read_delta_vfb_V'][:count], b['read_delta_vfb_V'][:count], strict=True)]
    return {'light_status': a['status'], 'dark_status': b['status'],
            'matched_read_count': count, 'requested_read_count': a['requested_read_count'],
            'matched_read_fraction': count/a['requested_read_count'],
            'light_minus_dark_delta_vfb_V': contrasts,
            'contrast_alignment': 'same_zero_based_read_index_and_physical_time',
            'experimental_qualification': False}


@_dataclass(frozen=True)
class MatchedOpticalSequenceResult(_Archive):
    """Independent light/dark copies of one physical request, including failures."""
    record_json: str

    def __post_init__(self):
        raw = _load(self.record_json)
        summary = _paired_projection(raw)
        _match(raw['summary'], summary)
        object.__setattr__(self, 'record_json', _canonical(raw))

    def to_dict(self):
        return _load(self.record_json)

    @property
    def summary(self):
        return self.to_dict()['summary']

    @classmethod
    def from_dict(cls, raw):
        return cls(_canonical(raw))


def run_matched_optical_sequence(experiment):
    if type(experiment) is not OpticalSequenceExperiment:
        raise ValueError('owned optical sequence experiment required')
    light = run_optical_sequence(experiment)
    dark = _run_dark(experiment.electrical)
    raw = {'schema_version': 'matched-optical-sequence-result-v1',
           'light': light.to_dict(), 'dark': dark.to_dict(), 'summary': None}
    raw['summary'] = _paired_projection(raw)
    return MatchedOpticalSequenceResult.from_dict(raw)
