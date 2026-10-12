# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Assumed OM-2 sequence using existing NC physics; not measured qualification."""
from __future__ import annotations
from dataclasses import dataclass
import json, math
from .independent_data import _Archive, _keys, _number, _text, _canonical, _match
from .device_photo_experiment import DevicePhotoExperiment
from .thermal_reporting import _restore_state, _state_payload
from .photo import PhotoTransitionConfig
from .ensemble.execution import _runtime

__all__ = ['OM2SweepProtocol', 'OM2SweepExperiment', 'OM2SweepPrediction', 'run_om2_sweep']


@dataclass(frozen=True)
class OM2SweepProtocol(_Archive):
    lower_voltage_V: float
    upper_voltage_V: float
    writing_time_s: float
    ascending_voltages_V: tuple[float, ...]
    descending_voltages_V: tuple[float, ...]
    point_dwell_s: float
    internal_dt_s: float
    reference_capacitance_F_m2: float
    sequence_evidence: str

    def __post_init__(self):
        _text(self.sequence_evidence, 'sequence evidence')
        for key in ('lower_voltage_V', 'upper_voltage_V'):
            object.__setattr__(self, key, _number(getattr(self, key), signed=True))
        if self.lower_voltage_V >= self.upper_voltage_V:
            raise ValueError('ordered distinct endpoint voltages required')
        for key in ('writing_time_s', 'point_dwell_s', 'internal_dt_s', 'reference_capacitance_F_m2'):
            value = _number(getattr(self, key))
            if value == 0:
                raise ValueError('positive duration/timestep/reference required')
            object.__setattr__(self, key, value)
        if self.internal_dt_s > min(self.writing_time_s, self.point_dwell_s):
            raise ValueError('timestep must resolve each declared dwell')
        for key, direction in (('ascending_voltages_V', 1), ('descending_voltages_V', -1)):
            values = getattr(self, key)
            if type(values) is not tuple or len(values) < 2:
                raise ValueError('immutable complete voltage grid required')
            values = tuple(_number(x, signed=True) for x in values)
            endpoints = (self.lower_voltage_V, self.upper_voltage_V) if direction == 1 else (self.upper_voltage_V, self.lower_voltage_V)
            if (values[0], values[-1]) != endpoints or any(direction*(b-a) <= 0 for a,b in zip(values,values[1:])):
                raise ValueError('strictly ordered full branch required')
            object.__setattr__(self, key, values)
        total = 2*self.writing_time_s + (len(self.ascending_voltages_V)+len(self.descending_voltages_V))*self.point_dwell_s
        if not math.isfinite(total):
            raise ValueError('representable sequence duration required')

    def to_dict(self):
        raw = {key: getattr(self, key) for key in self.__dataclass_fields__}
        for key in ('ascending_voltages_V', 'descending_voltages_V'):
            raw[key] = list(raw[key])
        return {'schema_version': 'om2-sweep-protocol-v1', **raw,
                'sequence': 'lower_hold/ascending_dark/upper_hold/descending_dark',
                'endpoint_sampling': 'grid includes each endpoint with an additional point dwell after its hold',
                'integrator': 'backward_euler', 'observable': 'signed constant-capacitance crossing window'}

    @classmethod
    def from_dict(cls, raw):
        names = tuple(cls.__dataclass_fields__)
        _keys(raw, ('schema_version', *names, 'sequence', 'endpoint_sampling', 'integrator', 'observable'))
        data = {k: raw[k] for k in names}
        for key in ('ascending_voltages_V', 'descending_voltages_V'):
            if type(data[key]) is not list:
                raise ValueError('archived grid list required')
            data[key] = tuple(data[key])
        obj = cls(**data)
        _match(raw, obj.to_dict())
        return obj


@dataclass(frozen=True)
class OM2SweepExperiment(_Archive):
    device_photo: DevicePhotoExperiment
    protocol: OM2SweepProtocol

    def __post_init__(self):
        if type(self.device_photo) is not DevicePhotoExperiment or type(self.protocol) is not OM2SweepProtocol:
            raise ValueError('typed owned device and sequence required')
        exp = DevicePhotoExperiment.from_dict(self.device_photo.to_dict())
        protocol = OM2SweepProtocol.from_dict(self.protocol.to_dict())
        pulse = exp.protocol.electrical_protocol
        if exp.illumination.exposure_time_s != protocol.writing_time_s or pulse.program_voltage_V != protocol.upper_voltage_V:
            raise ValueError('bound illumination duration/positive writing voltage mismatch')
        object.__setattr__(self, 'device_photo', exp)
        object.__setattr__(self, 'protocol', protocol)

    def to_dict(self):
        return {'schema_version': 'om2-sweep-experiment-v1', 'device_photo': self.device_photo.to_dict(),
                'protocol': self.protocol.to_dict(), 'scientific_status': 'assumed_om2_sequence_diagnostic',
                'experimental_qualification': False, 'substrate_photogeneration_modeled': False}

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ('schema_version', 'device_photo', 'protocol', 'scientific_status',
                    'experimental_qualification', 'substrate_photogeneration_modeled'))
        obj = cls(DevicePhotoExperiment.from_dict(raw['device_photo']), OM2SweepProtocol.from_dict(raw['protocol']))
        _match(raw, obj.to_dict())
        return obj


def _steps(protocol):
    return [('lower_hold', protocol.lower_voltage_V, protocol.writing_time_s)] + [
        ('ascending_dark', v, protocol.point_dwell_s) for v in protocol.ascending_voltages_V] + [
        ('upper_hold', protocol.upper_voltage_V, protocol.writing_time_s)] + [
        ('descending_dark', v, protocol.point_dwell_s) for v in protocol.descending_voltages_V]


def _crossing(events, kind, reference):
    points = [e for e in events if e['kind'] == kind]
    exact = [e['gate_voltage_V'] for e in points if e['capacitance_F_m2'] == reference]
    roots = list(exact)
    for a,b in zip(points, points[1:]):
        ca,cb = a['capacitance_F_m2'],b['capacitance_F_m2']
        if (ca < reference < cb) or (cb < reference < ca):
            roots.append(a['gate_voltage_V'] + (reference-ca)/(cb-ca)*(b['gate_voltage_V']-a['gate_voltage_V']))
    if len(roots) != 1:
        return {'status': 'outside_range' if not roots else 'ambiguous_multiple_crossings', 'voltage_V': None}
    return {'status': 'unique_crossing', 'voltage_V': roots[0]}


def _projection(raw):
    experiment = OM2SweepExperiment.from_dict(raw['experiment'])
    exp, protocol = experiment.device_photo, experiment.protocol
    if raw['experiment_hash'] != experiment.contract_hash:
        raise ValueError('sequence input hash mismatch')
    context = exp.spectral_context
    device = context.resolution.device
    from .spectral_reporting import _charge
    initial = json.loads(exp.initial_state_json)
    sequence = _steps(protocol)
    failure = raw['failure']
    if failure is not None:
        _keys(failure, ('run', 'step_index', 'exception_type', 'message'))
        if failure['run'] not in ('illuminated_writing', 'matched_dark') or type(failure['step_index']) is not int:
            raise ValueError('invalid sequence failure location')
        for key in ('exception_type', 'message'):
            _text(failure[key], key)
    summaries = {}
    for mode in ('illuminated_writing', 'matched_dark'):
        events = raw[mode]
        if type(events) is not list or len(events) > len(sequence):
            raise ValueError('invalid sequence observations')
        expected_count = len(sequence)
        if failure:
            if mode == failure['run']:
                expected_count = failure['step_index']
                if not 0 <= expected_count < len(sequence):
                    raise ValueError('invalid failed step')
            elif mode == 'matched_dark' and failure['run'] == 'illuminated_writing':
                expected_count = 0
        if len(events) != expected_count:
            raise ValueError('missing or extra sequence steps')
        previous = initial
        for index, event in enumerate(events):
            _keys(event, ('kind', 'step_index', 'gate_voltage_V', 'duration_s', 'light_enabled',
                         'initial_state', 'final_state', 'capacitance_F_m2', 'vfb_V', 'qfg_by_fg_C_m2'))
            kind, voltage, duration = sequence[index]
            enabled = mode == 'illuminated_writing' and kind.endswith('hold')
            _match([event['kind'],event['step_index'],event['gate_voltage_V'],event['duration_s'],event['light_enabled']],
                   [kind,index,voltage,duration,enabled])
            _match(event['initial_state'], previous)
            state = _restore_state(event['final_state'], device)
            expected_time = previous['time_s'] + duration
            if not math.isclose(state.time_s, expected_time, rel_tol=1e-12, abs_tol=1e-15):
                raise ValueError('sequence time continuity mismatch')
            q = _charge(state, device, context.resolution.physics)
            stored_q = event['qfg_by_fg_C_m2']
            if type(stored_q) is not list or len(stored_q) != len(q) or any(
                not math.isclose(_number(x, signed=True), float(y), rel_tol=1e-12, abs_tol=1e-20) for x,y in zip(stored_q,q)):
                raise ValueError('stored charge inconsistent with state')
            if _number(event['capacitance_F_m2']) == 0:
                raise ValueError('positive finite stored capacitance required')
            _number(event['vfb_V'], signed=True)
            physics,config = context.resolution.physics,context.resolution.simulation_config
            electro = physics.electrostatics.evaluate(device, voltage, float(q.sum()) if len(q)==1 else q,
                config.qfix_C_m2, config.qit_C_m2)
            for key in ('capacitance_F_m2', 'vfb_V'):
                if not math.isclose(event[key], float(getattr(electro,key)),rel_tol=1e-12,abs_tol=1e-15):
                    raise ValueError('stored electrostatic observable inconsistent with state')
            previous = event['final_state']
        complete = len(events) == len(sequence)
        ascending = _crossing(events, 'ascending_dark', protocol.reference_capacitance_F_m2) if complete else None
        descending = _crossing(events, 'descending_dark', protocol.reference_capacitance_F_m2) if complete else None
        assessable = complete and ascending['status'] == descending['status'] == 'unique_crossing'
        window = descending['voltage_V']-ascending['voltage_V'] if assessable else None
        if window is not None and not math.isfinite(window):
            raise ValueError('unrepresentable crossing window')
        summaries[mode] = {'complete': complete, 'completed_steps': len(events),
            'ascending_crossing': ascending, 'descending_crossing': descending,
            'crossing_window_V': window, 'final_time_s': previous['time_s']}
    a,b = summaries['illuminated_writing']['crossing_window_V'],summaries['matched_dark']['crossing_window_V']
    contrast = a-b if a is not None and b is not None else None
    if contrast is not None and not math.isfinite(contrast):
        raise ValueError('unrepresentable window contrast')
    return {'status': 'sequence_failed' if failure else 'completed',
            'observable_status': 'assessable' if contrast is not None else 'not_assessable',
            'scientific_status': 'assumed_om2_sequence_diagnostic', 'parameters_fitted': False,
            'experimental_qualification': False, 'measurement_definition': 'constant-capacitance crossing; not physical Vfb extraction',
            'reference_capacitance_F_m2': protocol.reference_capacitance_F_m2, **summaries,
            'light_minus_dark_crossing_window_V': contrast}


@dataclass(frozen=True)
class OM2SweepPrediction(_Archive):
    record_json: str

    def __post_init__(self):
        from .independent_data import _unique, _constant
        if type(self.record_json) is not str:
            raise ValueError('strict record JSON required')
        raw = json.loads(self.record_json, object_pairs_hook=_unique, parse_constant=_constant)
        _keys(raw, ('schema_version', 'experiment', 'experiment_hash', 'runtime',
                    'illuminated_writing', 'matched_dark', 'failure', 'summary'))
        if raw['schema_version'] != 'om2-sweep-prediction-v1' or type(raw['runtime']) is not dict:
            raise ValueError('unsupported OM2 record')
        _keys(raw['runtime'],tuple(_runtime()))
        for value in raw['runtime'].values():
            _text(value,'runtime version')
        _match(raw['summary'], _projection(raw))
        object.__setattr__(self, 'record_json', _canonical(raw))

    def to_dict(self):
        return json.loads(self.record_json)

    @property
    def summary(self):
        return self.to_dict()['summary']

    @classmethod
    def from_dict(cls, raw):
        return cls(_canonical(raw))


def run_om2_sweep(experiment: OM2SweepExperiment):
    """Independent matched runs; no resetting within a sequence or optical read."""
    if type(experiment) is not OM2SweepExperiment:
        raise ValueError('owned OM2 experiment required')
    experiment = OM2SweepExperiment.from_dict(experiment.to_dict())
    exp,protocol = experiment.device_photo,experiment.protocol
    context = exp.spectral_context
    raw = {'schema_version': 'om2-sweep-prediction-v1', 'experiment': experiment.to_dict(),
           'experiment_hash': experiment.contract_hash, 'runtime': _runtime(),
           'illuminated_writing': [], 'matched_dark': [], 'failure': None}
    for mode in ('illuminated_writing', 'matched_dark'):
        sim = context.create_simulator()
        state = _restore_state(json.loads(exp.initial_state_json), context.resolution.device)
        for index,(kind,voltage,duration) in enumerate(_steps(protocol)):
            try:
                initial = _state_payload(state,sim.device)
                enabled = mode == 'illuminated_writing' and kind.endswith('hold')
                out = sim.relax_voltage(state,voltage,duration,protocol.internal_dt_s,
                    light_source=context.optical_result.source if enabled else None,
                    photo_config=PhotoTransitionConfig(exp.capture_efficiency) if enabled else None,
                    photo_weights=exp.protocol.photo_weights if enabled else None,
                    occupancy_integrator='backward_euler')
                event = {'kind':kind,'step_index':index,'gate_voltage_V':voltage,'duration_s':duration,
                    'light_enabled':enabled,'initial_state':initial,'final_state':_state_payload(out['state'],sim.device),
                    'capacitance_F_m2':float(out['capacitance_F_m2']),'vfb_V':float(out['vfb_V']),
                    'qfg_by_fg_C_m2':out['qfg_by_fg_C_m2'].tolist()}
                _canonical(event)
                raw[mode].append(event)
                state = out['state']
            except Exception as exc:
                raw['failure']={'run':mode,'step_index':index,'exception_type':type(exc).__module__+'.'+type(exc).__qualname__,
                                'message':str(exc).strip() or type(exc).__name__}
                break
        if raw['failure']:
            break
    raw['summary'] = _projection(raw)
    return OM2SweepPrediction.from_dict(raw)
