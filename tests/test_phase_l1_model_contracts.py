# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Phase L1 addressing, archival identity and compatibility boundaries."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json

import pytest

from ncmemsim import DeviceBuilder
from ncmemsim.dtco import BindingScope, ParameterBinding
from ncmemsim.ensemble import ConstantDistribution, EnsembleSpec, PhysicalDomain, StochasticVariable
from ncmemsim.ensemble.model_contracts import (
    ModelVariabilitySpec, TransportModelContext, TrapDensityVariable, trap_density_binding,
)
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.provenance import ParameterProvenance, ParameterStatus
from ncmemsim.transport import (
    AdvancedTransportSpec, ImageForceBarrierSpec, TATLinkAttachment,
    TrapAssistedTransportSpec, TrapParameterStatus, TrapSpecies,
)


def context(density=8e24, *, enabled=True, link="gate_to_FG1", source="synthetic L1 test"):
    species = TrapSpecies("trap-a", 0.18 * 1.602176634e-19, 0.5, density, 2e-18,
                          2e14, TrapParameterStatus.ASSUMED, source, "contract tests only")
    return TransportModelContext(AdvancedTransportSpec((TATLinkAttachment(
        link, TrapAssistedTransportSpec(enabled, (species,)),
        ImageForceBarrierSpec(True, 3.9, TrapParameterStatus.ASSUMED, source, "test only"),
    ),)))


def variable(**kwargs):
    values = dict(name="density", binding=trap_density_binding("gate_to_FG1", "trap-a"),
                  distribution=ConstantDistribution(8e24), physical_domain=PhysicalDomain(lower=0),
                  provenance=ParameterProvenance("explicit assumed population", ParameterStatus.ASSUMED),
                  applicability="synthetic test only", nominal_value=8e24)
    values.update(kwargs)
    return TrapDensityVariable(**values)


def device_variable():
    return StochasticVariable("diameter", ParameterBinding(BindingScope.DEVICE, ("layers", "FG1", "nc_diameter_nm")),
                              ConstantDistribution(5), "nm", PhysicalDomain(lower=0, lower_inclusive=False),
                              ParameterProvenance("synthetic", ParameterStatus.ASSUMED), "test only")


def study(**kwargs):
    values = dict(name="l1-test", base_device_hash="a" * 64, model_context=context(), variables=(variable(),))
    values.update(kwargs)
    return ModelVariabilitySpec(**values)


def test_binding_identity_uses_exact_link_and_species():
    assert context().resolve_density(variable().binding) == 8e24
    assert variable().binding.scope is BindingScope.MODEL
    assert trap_density_binding("gate_to_FG1", "trap-a").binding_id != trap_density_binding("gate_to_FG1", "trap-b").binding_id


@pytest.mark.parametrize("link,species", [("", "a"), (" link", "a"), ("x", "a "), ("x", "")])
def test_reject_empty_or_padded_identifiers(link, species):
    with pytest.raises(ValueError):
        trap_density_binding(link, species)


@pytest.mark.parametrize("path", [("density_m3",), ("advanced_transport", "attachments", "x", "species", "a", "energy_depth_J")])
def test_reject_arbitrary_model_paths(path):
    with pytest.raises(ValueError):
        variable(binding=ParameterBinding(BindingScope.MODEL, path))


@pytest.mark.parametrize("link,species", [("missing-link", "trap-a"), ("gate_to_FG1", "missing-species")])
def test_reject_unknown_targets(link, species):
    with pytest.raises(ValueError):
        study(variables=(variable(binding=trap_density_binding(link, species)),))


@pytest.mark.parametrize("override", [
    {"unit": "cm^-3"}, {"physical_domain": PhysicalDomain()},
    {"physical_domain": PhysicalDomain(lower=-1)}, {"nominal_value": -1},
    {"nominal_value": float("nan")}, {"nominal_value": float("inf")},
    {"nominal_value": True}, {"distribution": object()}, {"provenance": object()},
    {"binding": ParameterBinding(BindingScope.DEVICE, ("density_m3",))},
])
def test_variable_validation(override):
    with pytest.raises((ValueError, TypeError)):
        variable(**override)


def test_declared_nominal_must_match_configuration_and_domain():
    with pytest.raises(ValueError, match="differs"):
        study(variables=(variable(nominal_value=7e24),))
    with pytest.raises(ValueError, match="outside"):
        study(variables=(variable(nominal_value=None, physical_domain=PhysicalDomain(lower=9e24)),))


def test_zero_density_is_valid_for_disabled_tat_only_when_existing_rules_allow():
    ctx = context(0, enabled=False)
    spec = study(model_context=ctx, variables=(variable(nominal_value=0, distribution=ConstantDistribution(0)),))
    assert spec.model_context.resolve_density(variable().binding) == 0
    with pytest.raises(ValueError, match="positive-density"):
        context(0, enabled=True)


def test_duplicate_names_and_targets_are_rejected():
    for variables in [(variable(), replace(variable(), name="other")), (variable(), variable())]:
        with pytest.raises(ValueError, match="unique"):
            study(variables=variables)


def test_existing_transport_contracts_reject_ambiguous_link_and_species():
    attachment = context().advanced_transport.attachments[0]
    with pytest.raises(ValueError):
        AdvancedTransportSpec((attachment, attachment))
    with pytest.raises(ValueError):
        TrapAssistedTransportSpec(True, attachment.specification.species * 2)


def test_json_roundtrip_and_independent_payload_ownership():
    original = study(variables=(variable(), device_variable()))
    payload = original.to_dict()
    restored = ModelVariabilitySpec.from_dict(json.loads(json.dumps(payload)))
    assert restored == original
    assert restored.definition_hash == original.definition_hash
    payload["model_context"]["advanced_transport"]["attachments"][0]["specification"]["species"][0]["density_m3"] = 9e24
    assert original.model_context.resolve_density(variable().binding) == 8e24
    with pytest.raises(ValueError, match="differs"):
        ModelVariabilitySpec.from_dict(payload)
    payload["variables"][0]["nominal_value"] = 9e24
    assert ModelVariabilitySpec.from_dict(payload).definition_hash != original.definition_hash
    with pytest.raises(FrozenInstanceError):
        original.name = "changed"


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(extra=1), lambda d: d.pop("model_context"),
    lambda d: d.update(schema_version="model-variability-spec-v2"),
    lambda d: d["model_context"].update(extra=1),
    lambda d: d["model_context"]["advanced_transport"].update(schema_version=True),
    lambda d: d["model_context"]["advanced_transport"]["attachments"][0].update(extra=1),
    lambda d: d["model_context"]["advanced_transport"]["attachments"][0]["barrier_correction"].update(extra=1),
    lambda d: d["model_context"]["advanced_transport"]["attachments"][0]["barrier_correction"].update(schema_version=2),
    lambda d: d["model_context"]["advanced_transport"]["attachments"][0]["specification"].update(schema_version=True),
    lambda d: d["model_context"]["advanced_transport"]["attachments"][0]["specification"]["species"][0].update(schema_version=True),
    lambda d: d["variables"][0].update(extra=1),
    lambda d: d["variables"][0].update(schema_version="trap-density-variable-v2"),
])
def test_nested_archives_fail_closed(mutate):
    payload = deepcopy(study().to_dict())
    mutate(payload)
    with pytest.raises((ValueError, TypeError)):
        ModelVariabilitySpec.from_dict(payload)


def test_identity_includes_density_provenance_mechanisms_and_correction():
    base = context()
    assert base.context_hash != context(source="different provenance").context_hash
    assert base.context_hash != context(enabled=False).context_hash
    a = base.advanced_transport.attachments[0]
    changed = TransportModelContext(AdvancedTransportSpec((replace(a, barrier_correction=ImageForceBarrierSpec()),)))
    assert changed.context_hash != base.context_hash
    assert variable().definition_hash != replace(variable(), distribution=ConstantDistribution(7e24)).definition_hash


def test_v1_k_variable_and_archives_still_reject_model_contracts():
    with pytest.raises(ValueError, match="DEVICE/OPERATING"):
        StochasticVariable("density", variable().binding, ConstantDistribution(8e24), "m^-3",
                           PhysicalDomain(lower=0), variable().provenance, "test only")
    with pytest.raises(ValueError):
        EnsembleSpec.from_dict(study().to_dict())
    k = EnsembleSpec("legacy", "a" * 64, (device_variable(),))
    payload = k.to_dict()
    assert EnsembleSpec.from_dict(payload).definition_hash == canonical_hash(payload)
    assert "model_context" not in payload
    with pytest.raises(TypeError):
        EnsembleSpec("legacy", "a" * 64, (variable(),))


def test_factory_uses_complete_device_identity_and_mixed_variables():
    dev = DeviceBuilder.v2(n_fgs=1)
    base = ModelVariabilitySpec.from_device(name="test", device=dev, model_context=context(), variables=(variable(), device_variable()))
    altered = deepcopy(dev)
    altered.gate_work_function_eV += 0.1
    other = ModelVariabilitySpec.from_device(name="test", device=altered, model_context=context(), variables=(variable(), device_variable()))
    assert base.definition_hash != other.definition_hash


@pytest.mark.parametrize("kwargs", [
    {"base_device_hash": "invalid"}, {"base_operating_hash": "b" * 64},
    {"base_operating_kind": "program_pulse_read"},
    {"base_operating_hash": "b" * 64, "base_operating_kind": "unsupported"},
    {"variables": ()}, {"variables": (device_variable(),)},
    {"model_context": object()},
])
def test_spec_validation(kwargs):
    with pytest.raises((ValueError, TypeError)):
        study(**kwargs)
