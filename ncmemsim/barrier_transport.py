# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Opt-in snapshot-bound replacement of direct inter-FG transmission only."""
from __future__ import annotations
import copy as _copy
from dataclasses import dataclass as _dataclass, fields as _fields, is_dataclass as _is_dataclass
from enum import Enum as _Enum
import math as _math
import numpy as _np
from .barrier_contracts import BarrierEvaluationSpec as _Request
from .barrier_evaluation import evaluate_barrier_profile as _evaluate_profile, BarrierEvaluationResult as _Evaluation
from .performance_contracts import _Owned, _restore, _text, _digest, _canonical
from .transport.engine import TransportEngine as _Direct
from .transport.rates import LinkTransportResult as _Link, TransportStepResult as _Step
from .kinetics import OccupancyEngine as _Occupancy
from .tunneling import TunnelingEngine as _Tunneling
from .fieldsolver import FieldProfile as _FieldProfile

__all__ = ['BarrierTransportContext', 'BarrierLinkAttachment', 'BarrierTransportSpec',
           'ProfiledLinkTransportResult', 'ProfiledTransportStepResult', 'BarrierTransportEngine']

_SCHEMA = 'ncmemsim-barrier-transport-v1'
_CONTEXT_KEYS = ('device', 'state', 'field_profile', 'network', 'transport_config',
                 'tunneling_config', 'occupancy_config', 'sheet_sites_m2')


def _native(value):
    if isinstance(value, _Enum): return _native(value.value)
    if _is_dataclass(value): return {field.name: _native(getattr(value, field.name)) for field in _fields(value)}
    if isinstance(value, _np.ndarray): return _native(value.tolist())
    if isinstance(value, _np.generic): return _native(value.item())
    if type(value) in (tuple, list): return [_native(item) for item in value]
    if type(value) is dict:
        if any(type(key) is not str for key in value): raise ValueError('text context keys required')
        return {key: _native(item) for key, item in value.items()}
    if value is None or type(value) in (str, bool, int, float):
        _canonical(value)
        return value
    raise ValueError('unsupported context value; no repr coercion')


class BarrierTransportContext(_Owned):
    """Owned current declarations supplied to a provider, without live objects."""
    __slots__ = ()

    def __init__(self, snapshot):
        if type(snapshot) is not dict or set(snapshot) != set(_CONTEXT_KEYS):
            raise ValueError('complete named transport snapshot required')
        self._store(dict(schema_version=_SCHEMA, snapshot=snapshot,
            meaning='current_runtime_declarations_not_authentication'))

    @property
    def snapshot(self): return self.to_dict()['snapshot']

    @classmethod
    def from_dict(cls, raw):
        return _restore(cls, raw, ('snapshot',), dict(schema_version=_SCHEMA,
            meaning='current_runtime_declarations_not_authentication'))


class BarrierLinkAttachment(_Owned):
    """Bind one ordered electron profile to named physical dielectric segments."""
    __slots__ = ()

    def __init__(self, link_id, request, segment_layer_names):
        _text(link_id, 'link_id')
        if isinstance(request, _Request): request = request.to_dict()
        request = _Request.from_dict(request).to_dict()
        if type(segment_layer_names) not in (list, tuple) or len(segment_layer_names) != len(request['profile']['segments']):
            raise ValueError('one physical layer name per profile segment required')
        for name in segment_layer_names: _text(name, 'layer_name')
        self._store(dict(schema_version=_SCHEMA, link_id=link_id, request=request,
            segment_layer_names=list(segment_layer_names), mode='replace_direct_inter_fg'))

    @classmethod
    def from_dict(cls, raw):
        return _restore(cls, raw, ('link_id', 'request', 'segment_layer_names'),
                        dict(schema_version=_SCHEMA, mode='replace_direct_inter_fg'))


class BarrierTransportSpec(_Owned):
    """An explicit plan for exactly one captured context; disabled by default."""
    __slots__ = ()

    def __init__(self, context_hash, attachments=(), enabled=False):
        _digest(context_hash, 'context_hash')
        if type(enabled) is not bool: raise ValueError('enabled must be bool')
        if type(attachments) not in (list, tuple): raise ValueError('ordered attachments required')
        rows = [BarrierLinkAttachment.from_dict(item.to_dict() if isinstance(item, BarrierLinkAttachment) else item).to_dict() for item in attachments]
        ids = [item['link_id'] for item in rows]
        if len(set(ids)) != len(ids): raise ValueError('at most one direct replacement per link')
        if not enabled and rows: raise ValueError('disabled plan must have no attachments')
        self._store(dict(schema_version=_SCHEMA, context_hash=context_hash,
            attachments=rows, enabled=enabled, failure_policy='zero_selected_flux_no_fallback',
            direction_policy='same_energy_action_with_legacy_directional_rate_factors',
            field_policy='explicit_current_snapshot_profile_no_automatic_tilt',
            additional_mechanisms='unsupported'))

    @classmethod
    def from_dict(cls, raw):
        return _restore(cls, raw, ('context_hash', 'attachments', 'enabled'),
            dict(schema_version=_SCHEMA, failure_policy='zero_selected_flux_no_fallback',
                direction_policy='same_energy_action_with_legacy_directional_rate_factors',
                field_policy='explicit_current_snapshot_profile_no_automatic_tilt',
                additional_mechanisms='unsupported'))


@_dataclass(frozen=True)
class ProfiledLinkTransportResult:
    baseline: _Link
    selected: _Link
    status: str
    context: BarrierTransportContext
    provider_id: str
    specification_hash: str
    attachment_hash: str | None = None
    evaluation: object | None = None
    failure: str | None = None

    def __post_init__(self):
        if not isinstance(self.context, BarrierTransportContext): raise ValueError('owned link context required')
        _text(self.provider_id, 'provider_id')
        _digest(self.specification_hash, 'specification_hash')
        if type(self.baseline) is not _Link or type(self.selected) is not _Link:
            raise ValueError('plain direct link records required')
        for key in ('link_id', 'kind', 'field_V_m', 'potential_difference_V', 'left_fg_index', 'right_fg_index'):
            if getattr(self.baseline, key) != getattr(self.selected, key):
                raise ValueError('selected link identity/field cannot change')
        for row in (self.baseline, self.selected):
            for key in ('transmission', 'forward_rate_Hz', 'backward_rate_Hz', 'net_electron_flux_m2_s'):
                if not _math.isfinite(getattr(row, key)): raise ValueError('finite link diagnostics required')
            if not 0 <= row.transmission <= 1 or min(row.forward_rate_Hz, row.backward_rate_Hz) < 0:
                raise ValueError('link transmission/rates outside domain')
        if self.status not in ('disabled', 'not_attached', 'diagnostic_only', 'profile_replaced', 'failed'):
            raise ValueError('unknown profile selection status')
        if self.status in ('profile_replaced', 'failed'):
            _digest(self.attachment_hash, 'attachment_hash')
            if not isinstance(self.evaluation, _Evaluation): raise ValueError('source-linked action evaluation required')
            if self.status == 'failed':
                _text(self.failure, 'failure')
                if any(getattr(self.selected, key) != 0 for key in ('transmission', 'forward_rate_Hz', 'backward_rate_Hz', 'net_electron_flux_m2_s')):
                    raise ValueError('failed replacement must have zero selected contribution')
            elif (self.failure is not None or self.evaluation.summary['status'] != 'completed' or
                  self.selected.transmission != self.evaluation.summary['transmission']):
                raise ValueError('completed replacement must retain its evaluated transmission')
        elif self.attachment_hash is not None or self.evaluation is not None or self.failure is not None:
            raise ValueError('inactive links cannot carry profile results')
        elif self.selected != self.baseline:
            raise ValueError('inactive link must retain the baseline exactly')

    @property
    def link_id(self): return self.selected.link_id
    @property
    def kind(self): return self.selected.kind
    @property
    def field_V_m(self): return self.selected.field_V_m
    @property
    def potential_difference_V(self): return self.selected.potential_difference_V
    @property
    def transmission(self): return self.selected.transmission
    @property
    def forward_rate_Hz(self): return self.selected.forward_rate_Hz
    @property
    def backward_rate_Hz(self): return self.selected.backward_rate_Hz
    @property
    def net_electron_flux_m2_s(self): return self.selected.net_electron_flux_m2_s
    @property
    def left_fg_index(self): return self.selected.left_fg_index
    @property
    def right_fg_index(self): return self.selected.right_fg_index

    def to_dict(self):
        return dict(baseline=_native(self.baseline), selected=_native(self.selected),
            context=self.context.to_dict(), provider_id=self.provider_id,
            specification_hash=self.specification_hash,
            status=self.status, attachment_hash=self.attachment_hash,
            evaluation=None if self.evaluation is None else self.evaluation.to_dict(), failure=self.failure)


@_dataclass(frozen=True)
class ProfiledTransportStepResult:
    baseline: _Step
    context: BarrierTransportContext
    specification: BarrierTransportSpec
    provider_id: str
    links: tuple[ProfiledLinkTransportResult, ...]
    net_electron_flux_by_fg_m2_s: _np.ndarray

    def __post_init__(self):
        if not isinstance(self.context, BarrierTransportContext) or not isinstance(self.specification, BarrierTransportSpec):
            raise ValueError('owned context and specification required')
        if self.specification.to_dict()['context_hash'] != self.context.contract_hash:
            raise ValueError('step context/specification mismatch')
        _text(self.provider_id, 'provider_id')
        if type(self.links) is not tuple or any(not isinstance(row, ProfiledLinkTransportResult) for row in self.links):
            raise ValueError('ordered profiled links required')
        if tuple(row.link_id for row in self.links) != tuple(row.link_id for row in self.baseline.links):
            raise ValueError('profiled link order must retain baseline order')
        if any(row.context.contract_hash != self.context.contract_hash or
               row.provider_id != self.provider_id or row.specification_hash != self.specification.contract_hash
               for row in self.links): raise ValueError('link source declarations must match the step context')
        values = _np.asarray(self.net_electron_flux_by_fg_m2_s, dtype=float).copy()
        if values.shape != (len(self.context.snapshot['sheet_sites_m2']),) or not _np.all(_np.isfinite(values)):
            raise ValueError('finite selected flux vector with one value per FG required')
        expected = _np.zeros_like(values)
        for row in self.links:
            if row.kind == 'inter_fg':
                expected[row.left_fg_index] -= row.net_electron_flux_m2_s
                expected[row.right_fg_index] += row.net_electron_flux_m2_s
        if not _np.array_equal(values, expected): raise ValueError('net vector must match selected link fluxes')
        values.setflags(write=False)
        original = _np.asarray(self.baseline.net_electron_flux_by_fg_m2_s, dtype=float).copy()
        original.setflags(write=False)
        object.__setattr__(self, 'net_electron_flux_by_fg_m2_s', values)
        object.__setattr__(self, 'baseline', _Step(tuple(self.baseline.links), original))

    @property
    def inter_fg_fluxes_m2_s(self):
        return _np.asarray([row.net_electron_flux_m2_s for row in self.links if row.kind == 'inter_fg'], dtype=float)

    def to_dict(self):
        return dict(schema_version=_SCHEMA, context=self.context.to_dict(),
            specification=self.specification.to_dict(), provider_id=self.provider_id,
            baseline=dict(links=[_native(row) for row in self.baseline.links],
                net_electron_flux_by_fg_m2_s=self.baseline.net_electron_flux_by_fg_m2_s.tolist()),
            links=[row.to_dict() for row in self.links],
            net_electron_flux_by_fg_m2_s=self.net_electron_flux_by_fg_m2_s.tolist(),
            experimental_qualification=False)


class _SelectedFluxEngine(_Direct):
    """Reuse the published conservative update without duplicating its algorithm."""
    def __init__(self, baseline, result):
        super().__init__(baseline.tunneling, baseline.config)
        self._result = result

    def evaluate(self, device, state, field_profile, occupancy_engine): return self._result


class BarrierTransportEngine:
    """Explicit drop-in wrapper; a provider receives an owned snapshot per call.

    Providers are ordinary trusted Python callables, not serialized executable
    policies. Their identifiers are declarations. No automatic material/bias law
    is inferred; profiles must be supplied at the exact current snapshot.
    """
    def __init__(self, baseline, provider=None, provider_id=None):
        if type(baseline) is not _Direct or type(baseline.tunneling) is not _Tunneling:
            raise ValueError('plain published direct transport required; no nested TAT/correction wrappers')
        if provider is not None:
            if not callable(provider): raise ValueError('provider must be callable')
            _text(provider_id, 'provider_id')
        elif provider_id is not None: raise ValueError('provider_id requires a provider')
        self.baseline, self.provider, self.provider_id = baseline, provider, provider_id

    @property
    def config(self): return self.baseline.config
    @property
    def tunneling(self): return self.baseline.tunneling
    def build_network(self, device): return self.baseline.build_network(device)

    def capture_context(self, device, state, field_profile, occupancy_engine):
        if type(occupancy_engine) is not _Occupancy or type(occupancy_engine.tunneling) is not _Tunneling:
            raise ValueError('plain occupancy/tunneling engines required')
        if type(field_profile) is not _FieldProfile: raise ValueError('plain FieldProfile required')
        device.validate()
        state.validate(device)
        # The public device summary omits some material fields. Bind full
        # dataclass declarations too, so a changed permittivity/barrier cannot
        # reuse a plan merely because material names stayed the same.
        declared_device = dict(device.to_dict(), full_declaration=_native(device))
        snapshot = _native(dict(device=declared_device, state=state,
            field_profile=field_profile, network=self.build_network(device),
            transport_config=self.config, tunneling_config=self.tunneling.config,
            occupancy_config=dict(kinetics=occupancy_engine.config,
                                  tunneling=occupancy_engine.tunneling.config),
            sheet_sites_m2=[self.baseline._sheet_site_density(occupancy_engine, fg) for fg in device.floating_gates()]))
        if any(value <= 0 for value in snapshot['sheet_sites_m2']): raise ValueError('positive sheet-site densities required')
        for key in ('attempt_frequency_Hz', 'direction_beta_V_inv', 'max_transfer_fraction_per_step'):
            value = snapshot['transport_config'][key]
            if type(value) not in (int, float) or value < 0: raise ValueError('nonnegative direct transport controls required')
        if snapshot['transport_config']['max_transfer_fraction_per_step'] > 1: raise ValueError('transfer fraction exceeds one')
        return BarrierTransportContext(snapshot)

    @staticmethod
    def _validate_attachment(item, context):
        raw = item.to_dict(); snapshot = context.snapshot
        links = {row['link_id']: row for row in snapshot['network']['links']}
        if raw['link_id'] not in links: raise ValueError('unknown attachment link')
        link = links[raw['link_id']]
        if link['kind'] != 'inter_fg': raise ValueError('substrate attachment is outside S4; injection remains in occupancy kinetics')
        profile = raw['request']['profile']
        if (profile['source_contact'] != link['left_node_id'] or
            profile['destination_contact'] != link['right_node_id'] or
            profile['axis_origin'] != link['left_node_id'] or
            profile['positive_axis_direction'] != 'network_left_to_right' or
            profile['traversal_direction'] != 'along_positive_axis'):
            raise ValueError('profile orientation/contact declarations do not match the network link')
        groups = []
        for name in raw['segment_layer_names']:
            if not groups or groups[-1] != name: groups.append(name)
        if groups != link['dielectric_layers']: raise ValueError('ordered physical layer mapping mismatch')
        physical = {row['name']: row['thickness_nm']*1e-9 for row in snapshot['device']['layers']}
        for name in groups:
            length = _math.fsum(row['length_m'] for row, label in zip(profile['segments'], raw['segment_layer_names']) if label == name)
            if not _math.isclose(length, physical[name], rel_tol=1e-12, abs_tol=0.):
                raise ValueError('profile segment lengths do not match the physical dielectric layer')
        total = _math.fsum(row['length_m'] for row in profile['segments'])
        if not _math.isclose(total, link['length_m'], rel_tol=1e-12, abs_tol=0.):
            raise ValueError('profile total length does not match transport link')

    def evaluate(self, device, state, field_profile, occupancy_engine):
        if self.provider is None:
            return self.baseline.evaluate(device, state, field_profile, occupancy_engine)
        context = self.capture_context(device, state, field_profile, occupancy_engine)
        plan = self.provider(context)
        if not isinstance(plan, BarrierTransportSpec): raise ValueError('provider must return an owned BarrierTransportSpec')
        plan = BarrierTransportSpec.from_dict(plan.to_dict())
        if plan.to_dict()['context_hash'] != context.contract_hash: raise ValueError('stale or foreign transport context')
        if self.capture_context(device, state, field_profile, occupancy_engine).contract_hash != context.contract_hash:
            raise ValueError('provider changed live runtime inputs; providers must be side-effect free')
        attachments = {row['link_id']: BarrierLinkAttachment.from_dict(row) for row in plan.to_dict()['attachments']}
        for item in attachments.values(): self._validate_attachment(item, context)
        direct = self.baseline.evaluate(device, state, field_profile, occupancy_engine)
        selected = []; net = _np.zeros(device.number_of_fgs(), dtype=float)
        sites = _np.asarray(context.snapshot['sheet_sites_m2'], dtype=float)
        electrons = 2*state.mean_normalized_occupations*sites
        capacity = 2*sites
        for base in direct.links:
            if any(not _math.isfinite(value) for value in (base.transmission, base.forward_rate_Hz,
                   base.backward_rate_Hz, base.net_electron_flux_m2_s)):
                raise ArithmeticError('finite direct baseline diagnostics required')
            item = attachments.get(base.link_id)
            evaluation = None; failure = None; replacement = base
            status = 'diagnostic_only' if base.kind == 'substrate' else ('disabled' if not plan.to_dict()['enabled'] else 'not_attached')
            if item is not None:
                evaluation = _evaluate_profile(item.to_dict()['request'])
                status = 'profile_replaced'
                if evaluation.summary['status'] != 'completed':
                    failure = evaluation.summary['failure']; status = 'failed'
                    transmission = kf = kb = flux = 0.
                else:
                    transmission = evaluation.summary['transmission']
                    bias = 1./(1.+_math.exp(-self.config.direction_beta_V_inv*base.potential_difference_V))
                    kf = self.config.attempt_frequency_Hz*transmission*bias
                    kb = self.config.attempt_frequency_Hz*transmission*(1.-bias)
                    li, ri = base.left_fg_index, base.right_fg_index
                    flux = (kf*min(float(electrons[li]), float(capacity[ri]-electrons[ri]))-
                            kb*min(float(electrons[ri]), float(capacity[li]-electrons[li])))
                    if not all(_math.isfinite(value) for value in (kf, kb, flux)):
                        failure = 'profile_directional_rate_or_flux_nonfinite'; status = 'failed'
                        transmission = kf = kb = flux = 0.
                replacement = _Link(base.link_id, base.kind, base.field_V_m,
                    base.potential_difference_V, transmission, kf, kb, float(flux), base.left_fg_index, base.right_fg_index)
            if base.kind == 'inter_fg':
                left = float(net[base.left_fg_index])-replacement.net_electron_flux_m2_s
                right = float(net[base.right_fg_index])+replacement.net_electron_flux_m2_s
                if not _math.isfinite(left) or not _math.isfinite(right):
                    raise ArithmeticError('aggregate selected flux outside finite range; no state update')
                net[base.left_fg_index], net[base.right_fg_index] = left, right
            selected.append(ProfiledLinkTransportResult(base, replacement, status,
                context, self.provider_id, plan.contract_hash,
                None if item is None else item.contract_hash, evaluation, failure))
        return ProfiledTransportStepResult(direct, context, plan, self.provider_id, tuple(selected), net)

    def step(self, device, state, field_profile, occupancy_engine, dt_s):
        if self.provider is None:
            return self.baseline.step(device, state, field_profile, occupancy_engine, dt_s)
        if type(dt_s) not in (int, float) or not _math.isfinite(dt_s) or dt_s < 0:
            raise ValueError('finite nonnegative timestep required')
        result = self.evaluate(device, state, field_profile, occupancy_engine)
        # A disabled explicit plan delegates the entire published update exactly.
        if not result.specification.to_dict()['enabled']:
            updated, _ = self.baseline.step(device, state, field_profile, occupancy_engine, dt_s)
            return updated, result
        updated, _ = _SelectedFluxEngine(self.baseline, result).step(
            device, _copy.deepcopy(state), field_profile, occupancy_engine, dt_s)
        return updated, result
