# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Stored sampling, isolated application, execution and strict archive checks."""
from copy import deepcopy
from dataclasses import replace, asdict
import json

import numpy as np
import pytest

from ncmemsim import DeviceBuilder, DeviceState, PhysicsModel
from ncmemsim.dtco import BindingScope, ParameterBinding
from ncmemsim.ensemble import (
    ConstantDistribution, NormalDistribution, PhysicalDomain, StochasticVariable,
    RNGSpec, EnsembleSpec, SamplingSpec, generate_sample_manifest, MatrixCorrelation,
)
from ncmemsim.ensemble.model_contracts import (
    ModelVariabilitySpec, TrapDensityVariable, TransportModelContext, trap_density_binding,
)
from ncmemsim.ensemble.model_sampling import (
    ModelSamplingSpec, ModelSampleManifest, generate_model_sample_manifest,
)
from ncmemsim.ensemble.model_execution import (
    apply_model_sample_to_context, execute_model_sample_manifest, ModelExecutionResult, AppliedModelRealization,
)
from ncmemsim.ensemble.sampling import EnsembleSample
from ncmemsim.fieldsolver import FieldSolver1D
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.provenance import ParameterProvenance, ParameterStatus
from ncmemsim.program_protocol import ProgramPulseReadProtocol
from ncmemsim.transport import (
    AdvancedTransportSpec, TATLinkAttachment, TrapAssistedTransportSpec, TrapSpecies,
    TrapParameterStatus, AdvancedTransportEngine, TransportEngine, TransportConfig, TransportMechanism,
)


def make(*, distribution=None, enabled=True, mixed=False, count=3, protocol=None):
    device = DeviceBuilder.v2(n_fgs=2, inter_fg_sio2_nm=1)
    trap = TrapSpecies("trap-a", 0.18 * 1.602176634e-19, 0.5, 8e24, 2e-18, 2e14,
                       TrapParameterStatus.ASSUMED, "synthetic L2 test", "test only")
    context = TransportModelContext(AdvancedTransportSpec((TATLinkAttachment(
        "FG1<->FG2", TrapAssistedTransportSpec(enabled, (trap,))),)))
    provenance = ParameterProvenance("synthetic assumed distribution", ParameterStatus.ASSUMED)
    density = TrapDensityVariable("density", trap_density_binding("FG1<->FG2", "trap-a"),
                                  distribution or ConstantDistribution(8e24), PhysicalDomain(lower=0), provenance,
                                  "synthetic only", 8e24)
    variables = [density]
    if mixed:
        variables.append(StochasticVariable("diameter", ParameterBinding(BindingScope.DEVICE, ("layers", "FG1", "nc_diameter_nm")),
                         ConstantDistribution(6), "nm", PhysicalDomain(lower=0, lower_inclusive=False), provenance, "test only"))
    if protocol is not None:
        variables.append(StochasticVariable("voltage", ParameterBinding(BindingScope.OPERATING, ("program", "voltage_V")),
                         ConstantDistribution(6), "V", PhysicalDomain(), provenance, "test only"))
    study = ModelVariabilitySpec.from_device(name="L2", device=device, model_context=context,
                                             variables=tuple(variables), operating_protocol=protocol)
    spec = ModelSamplingSpec(study, RNGSpec(2028), count)
    return device, spec, generate_model_sample_manifest(spec)


def density_evaluator(realization, workflow):
    return {"density": realization.model_context.resolve_density(trap_density_binding("FG1<->FG2", "trap-a"))}


def execute(manifest, device, evaluator=density_evaluator, **kwargs):
    return execute_model_sample_manifest(manifest, device, evaluator, evaluation_id="synthetic-L2",
                                         workflow_context={"purpose": "test only"}, **kwargs)


def stored(spec, rows):
    samples = tuple(EnsembleSample(spec.definition_hash, i, spec.variable_names, tuple(float(x) for x in row))
                    for i, row in enumerate(rows))
    return ModelSampleManifest(spec, samples, generate_model_sample_manifest(spec).runtime)


def test_reproducible_samples_and_strict_roundtrip_without_resampling(monkeypatch):
    device, spec, manifest = make(distribution=NormalDistribution(8e24, 1e24))
    assert generate_model_sample_manifest(spec).to_json() == manifest.to_json()
    monkeypatch.setattr(RNGSpec, "create_generator", lambda self: pytest.fail("reader/executor resampled"))
    restored = ModelSampleManifest.from_json(manifest.to_json())
    assert restored.manifest_hash == manifest.manifest_hash
    assert execute(restored, device).success_count == 3


def test_scalar_stream_matches_existing_phase_k_kernels():
    _, spec, manifest = make(distribution=NormalDistribution(8e24, 1e24), count=20)
    pv = ParameterProvenance("synthetic", ParameterStatus.ASSUMED)
    k_variable = StochasticVariable("density", ParameterBinding(BindingScope.DEVICE, ("substrate_doping_m3",)),
                                    spec.study.variables[0].distribution, "m^-3",
                                    PhysicalDomain(lower=0, lower_inclusive=False), pv, "test only")
    k = SamplingSpec(EnsembleSpec("K", "a" * 64, (k_variable,)), spec.rng, spec.sample_count)
    legacy = generate_sample_manifest(k)
    assert [s.values for s in legacy.samples] == [s.values for s in manifest.samples]
    assert legacy.samples[0].sample_id != manifest.samples[0].sample_id


def test_correlated_stream_uses_same_phase_k_copula():
    _, spec, _ = make(distribution=NormalDistribution(8e24, 1e24), mixed=True, count=10)
    diameter = replace(spec.study.variables[1], distribution=NormalDistribution(5, 0.2))
    study = replace(spec.study, variables=(spec.study.variables[0], diameter))
    correlation = MatrixCorrelation(variable_names=("density", "diameter"), matrix=((1.0, 0.4), (0.4, 1.0)), provenance=diameter.provenance, applicability="synthetic test")
    model_spec = replace(spec, study=study, dependence=correlation)
    manifest = generate_model_sample_manifest(model_spec)
    k_density = StochasticVariable("density", ParameterBinding(BindingScope.DEVICE, ("substrate_doping_m3",)),
                                    study.variables[0].distribution, "m^-3", PhysicalDomain(lower=0, lower_inclusive=False),
                                    diameter.provenance, "test only")
    k = SamplingSpec(EnsembleSpec("K", "a" * 64, (k_density, diameter)), spec.rng, 10, dependence=correlation)
    assert [s.values for s in generate_sample_manifest(k).samples] == [s.values for s in manifest.samples]


def test_constant_nominal_preserves_context_identity_and_inputs():
    device, spec, manifest = make()
    before = deepcopy(device.to_dict())
    realization = apply_model_sample_to_context(spec, manifest.samples[0], device)
    assert realization.model_context.context_hash == spec.study.model_context.context_hash
    assert realization.device is not device
    assert realization.model_context is not spec.study.model_context
    realization.device.get_layer("FG1").nc_diameter_nm = 9
    assert device.to_dict() == before


def test_mixed_device_and_operating_bindings_are_isolated():
    protocol = ProgramPulseReadProtocol(program_voltage_V=5, programming_time_s=1e-5)
    device, spec, manifest = make(mixed=True, protocol=protocol)
    applied = apply_model_sample_to_context(spec, manifest.samples[0], device, protocol)
    assert applied.device.get_layer("FG1").nc_diameter_nm == 6
    assert device.get_layer("FG1").nc_diameter_nm != 6
    assert applied.operating_protocol.program_voltage_V == 6
    assert protocol.program_voltage_V == 5
    assert execute(manifest, device, base_operating_protocol=protocol).success_count == 3


def test_domain_invalid_model_and_workflow_failures_do_not_stop_siblings():
    device, spec, _ = make(count=4)
    manifest = stored(spec, [(-1,), (0,), (7e24,), (9e24,)])
    def evaluator(realization, workflow):
        if realization.sample.sample_index == 2:
            raise ArithmeticError("controlled solver failure")
        return density_evaluator(realization, workflow)
    result = execute(manifest, device, evaluator)
    assert (result.success_count, result.failure_count) == (1, 3)
    assert [p.failure_stage for p in result.points] == ["sample-domain-validation", "realization-construction", "workflow", None]
    assert len(result.to_dict()["points"]) == 4
    assert all(p.to_dict()["assignments"] for p in result.points)


def test_all_failed_is_preserved_and_serialization_failure_is_distinct():
    device, spec, _ = make(count=2)
    result = execute(stored(spec, [(-1,), (0,)]), device)
    assert (result.success_count, result.failure_count) == (0, 2)
    bad = execute(generate_model_sample_manifest(spec), device, lambda r, w: {"nonfinite": float("nan")})
    assert all(p.failure_stage == "serialization" for p in bad.points)
    assert ModelExecutionResult.from_json(bad.to_json()).result_hash == bad.result_hash


def test_workflow_mutation_cannot_change_nominal_siblings_or_recorded_context():
    device, spec, manifest = make(mixed=True)
    before = deepcopy(device.to_dict())
    expected_context = apply_model_sample_to_context(spec, manifest.samples[0], device).context_payload()
    seen = []
    def evaluator(realization, workflow):
        seen.append((realization.device.get_layer("FG1").nc_diameter_nm, workflow["purpose"]))
        realization.device.get_layer("FG1").nc_diameter_nm = 99
        workflow["purpose"] = "changed"
        return {"ok": True}
    result = execute(manifest, device, evaluator)
    assert seen == [(6, "test only")] * 3
    assert device.to_dict() == before
    assert all(p.to_dict()["context"] == expected_context for p in result.points)
    assert ModelExecutionResult.from_dict(result.to_dict()).result_hash == result.result_hash


def test_simultaneous_density_changes_validate_final_configuration_only():
    device, spec, _ = make(count=1)
    attachment = spec.study.model_context.advanced_transport.attachments[0]
    first = attachment.specification.species[0]
    second = replace(first, name="trap-b", density_m3=0)
    ctx = TransportModelContext(AdvancedTransportSpec((replace(attachment,
        specification=replace(attachment.specification, species=(first, second))),)))
    v1 = replace(spec.study.variables[0], distribution=ConstantDistribution(0))
    v2 = replace(v1, name="second", binding=trap_density_binding("FG1<->FG2", "trap-b"),
                 nominal_value=0, distribution=ConstantDistribution(8e24))
    spec = replace(spec, study=replace(spec.study, model_context=ctx, variables=(v1, v2)))
    sample = generate_model_sample_manifest(spec).samples[0]
    applied = apply_model_sample_to_context(spec, sample, device)
    species = applied.model_context.advanced_transport.attachments[0].specification.species
    assert [s.density_m3 for s in species] == [0, 8e24]
    assert [s.density_m3 for s in attachment.specification.species] == [8e24]


def test_unknown_device_binding_is_counted_as_binding_failure():
    device, spec, _ = make(mixed=True, count=2)
    missing = replace(spec.study.variables[1], binding=ParameterBinding(BindingScope.DEVICE,
                                                                       ("layers", "missing", "nc_diameter_nm")))
    spec = replace(spec, study=replace(spec.study, variables=(spec.study.variables[0], missing)))
    result = execute(generate_model_sample_manifest(spec), device)
    assert result.failure_count == 2
    assert all(p.failure_stage == "binding" for p in result.points)


def test_generation_failure_has_sample_and_variable_identity(monkeypatch):
    from ncmemsim.ensemble.sampling import SamplingError, SampleGenerationError
    import ncmemsim.ensemble.model_sampling as module
    _, spec, _ = make()
    def fail(*args, **kwargs):
        raise SamplingError("normal", "controlled generation failure")
    monkeypatch.setattr(module, "sample_distribution", fail)
    with pytest.raises(SampleGenerationError) as error:
        generate_model_sample_manifest(spec)
    assert error.value.sample_index == 0
    assert error.value.variable_name == "density"


def test_model_sampling_and_workflow_settings_change_identity():
    device, spec, manifest = make()
    other_spec = replace(spec, rng=RNGSpec(2029))
    other = generate_model_sample_manifest(other_spec)
    assert other.manifest_hash != manifest.manifest_hash
    assert other.samples[0].sample_id != manifest.samples[0].sample_id
    result = execute(manifest, device)
    changed = execute_model_sample_manifest(manifest, device, density_evaluator, evaluation_id="synthetic-L2",
                                            workflow_context={"purpose": "different test settings"})
    assert result.result_hash != changed.result_hash
    assert result.points[0].to_dict()["realization_id"] != changed.points[0].to_dict()["realization_id"]


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(extra=1), lambda d: d.update(schema_version="unknown"),
    lambda d: d["sampling_spec"].update(study_hash="0" * 64),
    lambda d: d["sampling_spec"].update(scalar_sampling_algorithm="different"),
    lambda d: d["samples"][0]["values"].__setitem__(0, 1.0),
    lambda d: d["samples"].reverse(), lambda d: d["runtime"].update(extra="unknown"),
])
def test_manifest_tampering_is_rejected(mutation):
    _, _, manifest = make()
    data = manifest.to_dict()
    mutation(data)
    with pytest.raises((ValueError, TypeError)):
        ModelSampleManifest.from_dict(data)


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(success_count=99), lambda d: d.update(failure_count=True),
    lambda d: d["points"].reverse(), lambda d: d["points"][0].update(realization_id="0" * 64),
    lambda d: d["points"][0].update(context_hash="0" * 64),
    lambda d: d["points"][0]["assignments"][0].update(value=1.0),
    lambda d: d["execution"].update(manifest_hash="0" * 64),
    lambda d: d["points"][0].update(extra=1),
])
def test_result_tampering_rejected_even_with_recomputed_outer_hash(mutation):
    device, _, manifest = make()
    data = execute(manifest, device).to_dict()
    mutation(data)
    data["result_hash"] = canonical_hash({k: v for k, v in data.items() if k != "result_hash"})
    with pytest.raises((ValueError, TypeError)):
        ModelExecutionResult.from_dict(data)


def test_realized_density_tampering_rejected_even_with_rehashed_context():
    device, _, manifest = make()
    data = execute(manifest, device).to_dict()
    point = data["points"][0]
    point["context"]["model"]["advanced_transport"]["attachments"][0]["specification"]["species"][0]["density_m3"] = 9e24
    point["context_hash"] = canonical_hash(point["context"])
    data["result_hash"] = canonical_hash({k: v for k, v in data.items() if k != "result_hash"})
    with pytest.raises(ValueError, match="configuration differs"):
        ModelExecutionResult.from_dict(data)


def test_duplicate_json_keys_rejected():
    _, _, manifest = make()
    with pytest.raises(ValueError, match="duplicate"):
        ModelSampleManifest.from_json(manifest.to_json().replace('{', '{"schema_version":"fake",', 1))


def test_nominal_mismatch_aborts_before_workflow_and_cross_sample_is_rejected():
    device, spec, manifest = make()
    altered = deepcopy(device)
    altered.gate_work_function_eV += 0.1
    with pytest.raises(ValueError, match="baseline"):
        execute(manifest, altered, lambda *args: pytest.fail("must not run"))
    other_spec = replace(spec, rng=RNGSpec(1))
    with pytest.raises(ValueError, match="does not belong"):
        apply_model_sample_to_context(other_spec, manifest.samples[0], device)
    with pytest.raises(ValueError, match="workflow_context"):
        execute_model_sample_manifest(manifest, device, density_evaluator, evaluation_id="test", workflow_context={})


def test_no_accidental_calibration_inheritance_for_changed_density():
    device, spec, _ = make(count=1)
    attachment = spec.study.model_context.advanced_transport.attachments[0]
    calibrated = replace(attachment.specification.species[0], parameter_status=TrapParameterStatus.CALIBRATED)
    context = TransportModelContext(AdvancedTransportSpec((replace(attachment, specification=replace(attachment.specification, species=(calibrated,))),)))
    spec = replace(spec, study=replace(spec.study, model_context=context))
    manifest = stored(spec, [(9e24,)])
    applied = apply_model_sample_to_context(spec, manifest.samples[0], device)
    assert applied.model_context.advanced_transport.attachments[0].specification.species[0].parameter_status is TrapParameterStatus.ASSUMED
    assert context.advanced_transport.attachments[0].specification.species[0].parameter_status is TrapParameterStatus.CALIBRATED


@pytest.mark.parametrize("enabled", [True, False])
def test_real_transport_zero_variation_matches_nominal_and_preserves_direct_component(enabled):
    device, spec, manifest = make(enabled=enabled, count=2)
    config = TransportConfig(attempt_frequency_Hz=1e13, default_barrier_eV=0.25, max_transfer_fraction_per_step=0.5)
    settings = {"transport_config": asdict(config), "voltage_V": 4.0,
                "physics": "PhysicsModel.default", "field_solver": "FieldSolver1D",
                "state": "FG1 P1=1; other FGs empty"}
    def solve(realization, workflow):
        physics = PhysicsModel.default()
        base = TransportEngine(physics.tunneling, TransportConfig(**workflow["transport_config"]))
        state = DeviceState.empty_for_device(realization.device)
        state.floating_gates[0].P0[:] = 0
        state.floating_gates[0].P1[:] = 1
        profile = FieldSolver1D().solve(realization.device, workflow["voltage_V"], np.zeros(2))
        result = AdvancedTransportEngine(base, realization.model_context.advanced_transport).evaluate(
            realization.device, state, profile, physics.occupancy)
        link = next(x for x in result.links if x.link_id == "FG1<->FG2")
        return {"forward": link.forward_rate_Hz, "direct": link.contribution(TransportMechanism.DIRECT_TUNNELLING).forward_rate_Hz,
                "tat": link.contribution(TransportMechanism.TRAP_ASSISTED).forward_rate_Hz}
    nominal = solve(AppliedModelRealization(manifest.samples[0], deepcopy(device), None, spec.study.model_context, ()), settings)
    result = execute_model_sample_manifest(manifest, device, solve, evaluation_id="real-transport-test", workflow_context=settings)
    assert result.success_count == 2
    assert all(p.to_dict()["output"] == nominal for p in result.points)
    varied = stored(spec, [(4e24,), (12e24,)])
    alternate = execute_model_sample_manifest(varied, device, solve, evaluation_id="real-transport-test", workflow_context=settings)
    values = [p.to_dict()["output"] for p in alternate.points]
    assert all(v["direct"] == nominal["direct"] for v in values)
    if enabled:
        assert values[0]["tat"] != values[1]["tat"]
    else:
        assert all(v["tat"] == 0 for v in values)
