from __future__ import annotations

from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from ncmemsim import DeviceBuilder, DeviceState, PhysicsModel, Simulator
from ncmemsim.fieldsolver import FieldSolver1D
from ncmemsim.transport import (
    AdvancedTransportEngine,
    AdvancedTransportSpec,
    ImageForceBarrierSpec,
    MechanismEvaluationStatus,
    TATLinkAttachment,
    TransportConfig,
    TransportEngine,
    TransportMechanism,
    TrapAssistedTransportSpec,
    TrapParameterStatus,
    TrapSpecies,
)
import ncmemsim.transport.integration as integration_module


def trap(name="j4-synthetic"):
    return TrapSpecies(
        name=name,
        energy_depth_J=0.18 * 1.602176634e-19,
        position_fraction=0.5,
        density_m3=8.0e24,
        capture_cross_section_m2=2.0e-18,
        attempt_frequency_Hz=2.0e14,
        parameter_status=TrapParameterStatus.ASSUMED,
        source="synthetic J4 integration test",
        applicability="mechanism-accounting test only",
    )


def attachment(link_id, *, enabled=True, correction=None):
    specification = TrapAssistedTransportSpec(
        enabled=enabled,
        species=(trap(),) if enabled else (),
    )
    return TATLinkAttachment(
        link_id,
        specification,
        correction or ImageForceBarrierSpec(),
    )


def context(number_of_fgs=3):
    device = DeviceBuilder.v2(number_of_fgs, inter_fg_sio2_nm=1.0)
    physics = PhysicsModel.default()
    baseline = TransportEngine(
        physics.tunneling,
        TransportConfig(
            attempt_frequency_Hz=1.0e13,
            default_barrier_eV=0.25,
            max_transfer_fraction_per_step=0.5,
        ),
    )
    state = DeviceState.empty_for_device(device)
    state.floating_gates[0].P0[:] = 0.0
    state.floating_gates[0].P1[:] = 1.0
    state.floating_gates[0].P2[:] = 0.0
    profile = FieldSolver1D().solve(device, 4.0, np.zeros(number_of_fgs))
    return device, physics, baseline, state, profile


def total_electrons(device, occupancy, state):
    total = 0.0
    for fg, fg_state in zip(device.floating_gates(), state.floating_gates):
        x, dx = occupancy.grid(fg)
        sheet = float(np.sum(occupancy.density_profile(fg, x)) * dx)
        total += 2.0 * fg_state.mean_normalized_occupation * sheet
    return total


def test_attachment_contract_is_immutable_unique_and_hashed():
    item = attachment("fg1<->fg2")
    spec = AdvancedTransportSpec((item,))
    assert len(spec.configuration_hash) == 64
    assert spec.to_dict()["attachments"][0]["link_id"] == "fg1<->fg2"
    with pytest.raises(FrozenInstanceError):
        item.link_id = "changed"
    with pytest.raises(ValueError, match="at most one"):
        AdvancedTransportSpec((item, item))
    with pytest.raises(ValueError, match="link_id"):
        attachment(" bad ")


def test_empty_composite_preserves_direct_values_and_marks_not_attached():
    device, physics, baseline, state, profile = context(2)
    direct = baseline.evaluate(device, state, profile, physics.occupancy)
    composite = AdvancedTransportEngine(baseline).evaluate(
        device, state, profile, physics.occupancy
    )
    np.testing.assert_array_equal(
        composite.net_electron_flux_by_fg_m2_s,
        direct.net_electron_flux_by_fg_m2_s,
    )
    assert composite.baseline is not direct
    for actual, expected in zip(composite.links, direct.links):
        assert actual.baseline == expected
        assert actual.total_forward_rate_Hz == expected.forward_rate_Hz
        assert actual.total_backward_rate_Hz == expected.backward_rate_Hz
        assert actual.total_net_electron_flux_m2_s == expected.net_electron_flux_m2_s
        assert actual.contribution(TransportMechanism.TRAP_ASSISTED).status is MechanismEvaluationStatus.NOT_ATTACHED


def test_empty_composite_step_matches_baseline_state_exactly():
    device, physics, baseline, state, profile = context(2)
    expected_state, expected_result = baseline.step(
        device, state, profile, physics.occupancy, 1.0e-6
    )
    actual_state, actual_result = AdvancedTransportEngine(baseline).step(
        device, state, profile, physics.occupancy, 1.0e-6
    )
    np.testing.assert_array_equal(
        actual_result.net_electron_flux_by_fg_m2_s,
        expected_result.net_electron_flux_by_fg_m2_s,
    )
    for actual, expected in zip(
        actual_state.floating_gates, expected_state.floating_gates
    ):
        np.testing.assert_array_equal(actual.P0, expected.P0)
        np.testing.assert_array_equal(actual.P1, expected.P1)
        np.testing.assert_array_equal(actual.P2, expected.P2)


def test_only_explicit_inter_fg_link_receives_tat_and_totals_are_auditable():
    device, physics, baseline, state, profile = context(3)
    link_ids = [item.link_id for item in baseline.build_network(device).links]
    engine = AdvancedTransportEngine(
        baseline,
        AdvancedTransportSpec((attachment(link_ids[0]),)),
    )
    result = engine.evaluate(device, state, profile, physics.occupancy)
    first = result.links[0]
    direct = first.contribution(TransportMechanism.DIRECT_TUNNELLING)
    tat = first.contribution(TransportMechanism.TRAP_ASSISTED)
    assert tat.status is MechanismEvaluationStatus.EVALUATED
    assert tat.evaluation is not None and tat.evaluation.total_rate_Hz > 0.0
    assert first.total_forward_rate_Hz == pytest.approx(direct.forward_rate_Hz + tat.forward_rate_Hz)
    assert first.total_backward_rate_Hz == pytest.approx(direct.backward_rate_Hz + tat.backward_rate_Hz)
    assert first.total_net_electron_flux_m2_s == pytest.approx(
        direct.net_electron_flux_m2_s + tat.net_electron_flux_m2_s
    )
    assert result.links[1].contribution(TransportMechanism.TRAP_ASSISTED).status is MechanismEvaluationStatus.NOT_ATTACHED
    assert result.links[-1].contribution(TransportMechanism.TRAP_ASSISTED).status is MechanismEvaluationStatus.NOT_ATTACHED
    assert float(np.sum(result.net_electron_flux_by_fg_m2_s)) == pytest.approx(0.0, abs=1.0)


def test_disabled_attachment_is_explicit_and_has_zero_contribution():
    device, physics, baseline, state, profile = context(2)
    link_id = baseline.build_network(device).links[0].link_id
    result = AdvancedTransportEngine(
        baseline, AdvancedTransportSpec((attachment(link_id, enabled=False),))
    ).evaluate(device, state, profile, physics.occupancy)
    item = result.links[0].contribution(TransportMechanism.TRAP_ASSISTED)
    assert item.status is MechanismEvaluationStatus.DISABLED
    assert item.forward_rate_Hz == item.backward_rate_Hz == item.net_electron_flux_m2_s == 0.0


def test_unknown_link_is_a_configuration_error_before_optional_evaluation():
    device, physics, baseline, state, profile = context(2)
    engine = AdvancedTransportEngine(
        baseline, AdvancedTransportSpec((attachment("missing<->link"),))
    )
    with pytest.raises(ValueError, match="unknown links"):
        engine.evaluate(device, state, profile, physics.occupancy)


def test_optional_failure_is_local_and_preserves_direct_and_neighbor(monkeypatch):
    device, physics, baseline, state, profile = context(3)
    link_ids = [item.link_id for item in baseline.build_network(device).links if item.kind == "inter_fg"]
    original = integration_module.evaluate_trap_assisted_transport_with_barrier_correction
    calls = 0

    def fail_first(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ArithmeticError("synthetic link-local failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(
        integration_module,
        "evaluate_trap_assisted_transport_with_barrier_correction",
        fail_first,
    )
    result = AdvancedTransportEngine(
        baseline,
        AdvancedTransportSpec(tuple(attachment(link_id) for link_id in link_ids)),
    ).evaluate(device, state, profile, physics.occupancy)
    failed = result.links[0].contribution(TransportMechanism.TRAP_ASSISTED)
    neighbor = result.links[1].contribution(TransportMechanism.TRAP_ASSISTED)
    assert failed.status is MechanismEvaluationStatus.FAILED
    assert failed.failure.exception_type == "ArithmeticError"
    assert failed.failure.message == "synthetic link-local failure"
    assert failed.net_electron_flux_m2_s == 0.0
    assert result.links[0].total_net_electron_flux_m2_s == result.links[0].baseline.net_electron_flux_m2_s
    assert neighbor.status is MechanismEvaluationStatus.EVALUATED
    assert neighbor.failure is None


def test_nonfinite_optional_flux_is_isolated_before_net_vector_mutation():
    device, physics, baseline, state, profile = context(2)
    link_id = next(
        item.link_id
        for item in baseline.build_network(device).links
        if item.kind == "inter_fg"
    )
    extreme = TrapSpecies(
        name="j4-nonfinite-flux-injection",
        energy_depth_J=1.0e-30,
        position_fraction=0.5,
        density_m3=8.0e22,
        capture_cross_section_m2=2.0e-20,
        attempt_frequency_Hz=1.0e308,
        parameter_status=TrapParameterStatus.ASSUMED,
        source="deliberate finite overflow-injection regression fixture",
        applicability="optional-mechanism failure isolation only; not physical",
    )
    specification = TrapAssistedTransportSpec(
        enabled=True,
        species=(extreme,),
    )
    result = AdvancedTransportEngine(
        baseline,
        AdvancedTransportSpec(
            (
                TATLinkAttachment(
                    link_id,
                    specification,
                    ImageForceBarrierSpec(
                        enabled=True,
                        relative_permittivity=3.9,
                        parameter_status=TrapParameterStatus.ASSUMED,
                        source="synthetic J4 overflow-isolation fixture",
                        applicability="failure-isolation regression only",
                    ),
                ),
            )
        ),
    ).evaluate(device, state, profile, physics.occupancy)

    link = next(item for item in result.links if item.link_id == link_id)
    direct = link.contribution(TransportMechanism.DIRECT_TUNNELLING)
    tat = link.contribution(TransportMechanism.TRAP_ASSISTED)

    assert tat.status is MechanismEvaluationStatus.FAILED
    assert tat.failure is not None
    assert tat.failure.exception_type == "ArithmeticError"
    assert "non-finite optional mechanism flux" in tat.failure.message
    assert tat.forward_rate_Hz == 0.0
    assert tat.backward_rate_Hz == 0.0
    assert tat.net_electron_flux_m2_s == 0.0
    assert link.total_forward_rate_Hz == direct.forward_rate_Hz
    assert link.total_backward_rate_Hz == direct.backward_rate_Hz
    assert link.total_net_electron_flux_m2_s == direct.net_electron_flux_m2_s
    assert np.all(np.isfinite(result.net_electron_flux_by_fg_m2_s))
    np.testing.assert_array_equal(
        result.net_electron_flux_by_fg_m2_s,
        result.baseline.net_electron_flux_by_fg_m2_s,
    )


def test_substrate_attachment_is_diagnostic_only_and_never_changes_state_flux():
    device, physics, baseline, state, profile = context(2)
    substrate = next(item for item in baseline.build_network(device).links if item.kind == "substrate")
    result = AdvancedTransportEngine(
        baseline, AdvancedTransportSpec((attachment(substrate.link_id),))
    ).evaluate(device, state, profile, physics.occupancy)
    item = next(link for link in result.links if link.link_id == substrate.link_id)
    tat = item.contribution(TransportMechanism.TRAP_ASSISTED)
    assert tat.status is MechanismEvaluationStatus.DIAGNOSTIC_ONLY
    assert tat.evaluation is not None
    assert tat.net_electron_flux_m2_s == 0.0
    np.testing.assert_array_equal(
        result.net_electron_flux_by_fg_m2_s,
        result.baseline.net_electron_flux_by_fg_m2_s,
    )


def test_composite_step_is_conservative_and_does_not_mutate_input_state():
    device, physics, baseline, state, profile = context(2)
    before_state = state.copy()
    before_total = total_electrons(device, physics.occupancy, state)
    link_id = next(item.link_id for item in baseline.build_network(device).links if item.kind == "inter_fg")
    updated, result = AdvancedTransportEngine(
        baseline, AdvancedTransportSpec((attachment(link_id),))
    ).step(device, state, profile, physics.occupancy, 1.0e-6)
    state.validate(device)
    updated.validate(device)
    for actual, expected in zip(state.floating_gates, before_state.floating_gates):
        np.testing.assert_array_equal(actual.P0, expected.P0)
        np.testing.assert_array_equal(actual.P1, expected.P1)
        np.testing.assert_array_equal(actual.P2, expected.P2)
    assert total_electrons(device, physics.occupancy, updated) == pytest.approx(
        before_total, rel=1.0e-12, abs=1.0
    )
    assert result.links[0].total_net_electron_flux_m2_s != result.links[0].baseline.net_electron_flux_m2_s


def test_composite_engine_remains_simulator_compatible_when_explicitly_installed():
    device, physics, baseline, state, _ = context(2)
    link_id = next(item.link_id for item in baseline.build_network(device).links if item.kind == "inter_fg")
    physics.transport = AdvancedTransportEngine(
        baseline, AdvancedTransportSpec((attachment(link_id),))
    )
    out = Simulator(device, physics).relax_voltage(state, 1.0, dwell_time_s=0.0)
    assert out["transport_link_ids"][0] == link_id
    assert out["inter_fg_flux_by_link_m2_s"].shape == (1,)
    assert len(out["transport_link_results"][0].contributions) == 2
