# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Owned thermal candidate resolution for existing DEVICE and MODEL DTCO paths."""
from __future__ import annotations
from copy import copy
from dataclasses import dataclass, fields
from .device import Device
from .physics import PhysicsModel
from .simulator import Simulator, SimulationConfig
from .temperature_context import (ThermalContext, ResolvedThermalContext, ThermalSimulator,
    _dump, _load, _config, _keys)
from .workflows.application import _device_payload, _physics_payload, _restore_physics
from .ensemble.model_contracts import TransportModelContext
from .transport.integration import AdvancedTransportEngine, MechanismEvaluationStatus, AdvancedTransportSpec, TATLinkAttachment
from .transport.traps import TrapAssistedTransportSpec, TrapSpecies
from .transport.barrier_corrections import ImageForceBarrierSpec
from .hashing import canonical_hash

__all__ = ['ThermalCandidateError', 'ThermalDomainError', 'ThermalCandidateResolution',
           'ThermalModelSimulator', 'resolve_thermal_candidate']


class ThermalCandidateError(ValueError):
    """Candidate/context/model compatibility failed before scientific execution."""


class ThermalDomainError(ThermalCandidateError):
    """Candidate cannot be resolved inside the declared thermal applicability."""


def _owned_model(model):
    if type(model) is not TransportModelContext:
        raise ThermalCandidateError('unextended TransportModelContext required')
    def exact(value, kind):
        if type(value) is not kind or set(vars(value)) != {f.name for f in fields(kind)}:
            raise ThermalCandidateError('unextended '+kind.__name__+' required')
    exact(model, TransportModelContext)
    exact(model.advanced_transport, AdvancedTransportSpec)
    for attachment in model.advanced_transport.attachments:
        exact(attachment, TATLinkAttachment)
        exact(attachment.specification, TrapAssistedTransportSpec)
        exact(attachment.barrier_correction, ImageForceBarrierSpec)
        for species in attachment.specification.species:
            exact(species, TrapSpecies)
    restored = TransportModelContext.from_dict(model.to_dict())
    if _dump(restored.to_dict()) != _dump(model.to_dict()):
        raise ThermalCandidateError('noncanonical transport model context')
    return restored


class _CheckedTransport(AdvancedTransportEngine):
    def evaluate(self, device, state, field_profile, occupancy_engine):
        result = super().evaluate(device, state, field_profile, occupancy_engine)
        failures = [c for link in result.links for c in link.contributions
                    if c.status is MechanismEvaluationStatus.FAILED]
        if failures:
            raise ArithmeticError('optional transport mechanism failed: '+failures[0].failure.message)
        return result


@dataclass(frozen=True)
class ThermalCandidateResolution:
    """Separate M5 envelope; original M2 and K/L archive schemas stay unchanged."""
    thermal: ResolvedThermalContext
    model_context: TransportModelContext | None = None

    def __post_init__(self):
        if type(self.thermal) is not ResolvedThermalContext:
            raise ThermalCandidateError('typed thermal resolution required')
        # Eagerly validate domain/projections, even when the model is absent.
        self.thermal.to_dict()
        if self.model_context is not None:
            model = _owned_model(self.model_context)
            physics = self.thermal.physics
            network = physics.transport.build_network(self.thermal.device)
            inter_fg = {link.link_id for link in network.links if link.kind == 'inter_fg'}
            if any(a.link_id not in inter_fg for a in model.advanced_transport.attachments):
                raise ThermalCandidateError('MODEL attachments must target existing inter-FG links')
            object.__setattr__(self, 'model_context', model)

    @property
    def candidate_hash(self) -> str:
        return canonical_hash(self.to_dict())

    def to_dict(self) -> dict:
        return {'schema_version': 'thermal-dtco-candidate-v1', 'thermal': self.thermal.to_dict(),
            'thermal_hash': self.thermal.context_hash,
            'model': None if self.model_context is None else self.model_context.to_dict(),
            'model_hash': None if self.model_context is None else self.model_context.context_hash,
            'mechanism_failure_policy': 'raise-no-partial-success'}

    def to_json(self) -> str:
        return _dump(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> ThermalCandidateResolution:
        _keys(data, ('schema_version','thermal','thermal_hash','model','model_hash','mechanism_failure_policy'))
        result = cls(ResolvedThermalContext.from_dict(data['thermal']),
            None if data['model'] is None else TransportModelContext.from_dict(data['model']))
        if _dump(data) != _dump(result.to_dict()):
            raise ThermalCandidateError('thermal candidate identity or derived content mismatch')
        return result

    @classmethod
    def from_json(cls, text: str) -> ThermalCandidateResolution:
        return cls.from_dict(_load(text))

    def create_simulator(self) -> ThermalSimulator:
        if self.model_context is None:
            return self.thermal.create_simulator()
        return ThermalModelSimulator(self)


class ThermalModelSimulator(ThermalSimulator):
    """Resolved thermal physics plus owned explicit MODEL transport attachments."""
    def __init__(self, candidate: ThermalCandidateResolution):
        if type(candidate) is not ThermalCandidateResolution or candidate.model_context is None:
            raise ThermalCandidateError('MODEL thermal candidate required')
        # Restore before using it, excluding arbitrary runtime engine callbacks.
        candidate = ThermalCandidateResolution.from_dict(candidate.to_dict())
        self._candidate = candidate
        self._resolution = candidate.thermal
        physics = candidate.thermal.physics
        physics.transport = _CheckedTransport(physics.transport, candidate.model_context.advanced_transport)
        Simulator.__init__(self, candidate.thermal.device, physics, candidate.thermal.simulation_config)
        self._require_context()

    def _require_context(self):
        engine = self.physics.transport
        if type(self.physics) is not PhysicsModel or type(engine) is not _CheckedTransport or set(vars(engine)) != {'baseline','specification'}:
            raise ThermalCandidateError('thermal MODEL engine implementation changed')
        # The exact core validator still checks every engine and shared tunneling.
        core = copy(self.physics)
        core.transport = engine.baseline
        try:
            actual = {'device': _device_payload(self.device), 'physics': _physics_payload(core),
                      'simulation_config': _config(self.config, SimulationConfig)}
        except (TypeError, ValueError, AttributeError) as exc:
            raise ThermalCandidateError('thermal MODEL core implementation changed') from exc
        expected = self._resolution._projection()
        if _dump(actual) != _dump({k:expected[k] for k in actual}):
            raise ThermalCandidateError('thermal MODEL inputs changed; resolve a new candidate')
        actual_model = _owned_model(TransportModelContext(engine.specification))
        if _dump(actual_model.to_dict()) != _dump(self._candidate.model_context.to_dict()):
            raise ThermalCandidateError('MODEL attachment configuration changed')


def resolve_thermal_candidate(template: ThermalContext, device: Device, *,
                              model_context: TransportModelContext | None = None) -> ThermalCandidateResolution:
    """Rebase nominal DEVICE inputs, then resolve their single temperature owner.

    The template supplies unchanged reference physics/configuration and profiles.
    Composition/doping incompatibility is rejected, never patched or extrapolated.
    Ordinary exceptions remain failures in the existing sweep/MODEL executors.
    """
    if type(template) is not ThermalContext or type(device) is not Device:
        raise ThermalCandidateError('unextended thermal template and candidate Device required')
    try:
        thermal = ThermalContext.from_nominal(device, _restore_physics(_load(template.nominal_physics_json)),
            SimulationConfig(**_load(template.simulation_config_json)), enabled=template.enabled,
            semiconductor_mode=template.semiconductor_mode, substrate_gap=template.substrate_gap,
            intrinsic_density=template.intrinsic_density, optical_bindings=template.optical_bindings)
    except (TypeError, ValueError, KeyError) as exc:
        raise ThermalCandidateError(str(exc)) from exc
    try:
        resolved = thermal.resolve(temperature_K=device.temperature_K)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ThermalDomainError(str(exc)) from exc
    return ThermalCandidateResolution(resolved, model_context)
