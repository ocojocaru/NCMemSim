from __future__ import annotations

from dataclasses import FrozenInstanceError
import math
from pathlib import Path

import pytest

from ncmemsim.transport import (
    BarrierCorrectionStatus,
    ImageForceBarrierSpec,
    TATRateStatus,
    TrapAssistedTransportSpec,
    TrapParameterStatus,
    TrapSpecies,
    apply_image_force_barrier_correction,
    build_corrected_tat_barrier_profile,
    evaluate_tat_species,
    evaluate_tat_species_with_barrier_correction,
    evaluate_trap_assisted_transport_with_barrier_correction,
    image_force_barrier_lowering_J,
)
from ncmemsim.transport.barrier_corrections import VACUUM_PERMITTIVITY_F_M
from ncmemsim.transport.tat import ELEMENTARY_CHARGE_C


ROOT = Path(__file__).resolve().parents[1]


def species(name="synthetic-j3", **overrides):
    values = dict(
        name=name,
        energy_depth_J=1.602176634e-19,
        position_fraction=0.4,
        density_m3=1.0e23,
        capture_cross_section_m2=1.0e-19,
        attempt_frequency_Hz=1.0e13,
        parameter_status=TrapParameterStatus.ASSUMED,
        source="synthetic J3 barrier-correction check",
        applicability="conditional homogeneous dielectric-link rate only",
    )
    values.update(overrides)
    return TrapSpecies(**values)


def correction(*, enabled=True, **overrides):
    values = dict(
        enabled=enabled,
        relative_permittivity=3.9,
        parameter_status=TrapParameterStatus.LITERATURE,
        source="synthetic effective image-force permittivity",
        applicability="symmetric two-interface compact Schottky lowering",
    )
    values.update(overrides)
    return ImageForceBarrierSpec(**values)


def context(**overrides):
    values = dict(
        link_length_m=8.0e-9,
        electric_field_V_m=2.0e8,
        effective_mass_m0=0.2,
    )
    values.update(overrides)
    return values


def test_classical_lowering_matches_energy_formula_and_field_symmetry():
    field, relative_permittivity = 2.0e8, 3.9
    expected = math.sqrt(
        ELEMENTARY_CHARGE_C**3
        * field
        / (4 * math.pi * VACUUM_PERMITTIVITY_F_M * relative_permittivity)
    )
    forward = image_force_barrier_lowering_J(field, relative_permittivity)
    reverse = image_force_barrier_lowering_J(-field, relative_permittivity)
    assert forward == pytest.approx(expected, rel=2e-15)
    assert reverse == forward
    assert image_force_barrier_lowering_J(0.0, relative_permittivity) == 0.0


def test_enabled_configuration_requires_explicit_provenance():
    with pytest.raises(ValueError, match="source and applicability"):
        ImageForceBarrierSpec(enabled=True, relative_permittivity=3.9)
    with pytest.raises(ValueError, match="strictly positive"):
        correction(relative_permittivity=0.0)
    with pytest.raises(TypeError, match="excluding bool"):
        correction(relative_permittivity=True)
    with pytest.raises(TypeError, match="parameter_status"):
        correction(parameter_status="literature")


def test_disabled_and_zero_field_corrections_are_exact_noops():
    barrier = 2.1e-19
    disabled = apply_image_force_barrier_correction(
        barrier,
        electric_field_V_m=2e8,
        specification=correction(enabled=False),
    )
    assert disabled.unmodified_barrier_J == barrier
    assert disabled.corrected_barrier_J == barrier
    assert disabled.lowering_J == 0.0
    assert disabled.status is BarrierCorrectionStatus.DISABLED

    zero = apply_image_force_barrier_correction(
        barrier,
        electric_field_V_m=0.0,
        specification=correction(),
    )
    assert zero.corrected_barrier_J == barrier
    assert zero.lowering_J == 0.0
    assert zero.status is BarrierCorrectionStatus.ZERO_FIELD


def test_unmodified_profile_is_retained_and_trap_height_is_not_changed():
    item = species()
    result = build_corrected_tat_barrier_profile(item, correction(), **context())
    raw = result.unmodified_profile
    corrected = result.corrected_profile
    lowering = image_force_barrier_lowering_J(
        context()["electric_field_V_m"], correction().relative_permittivity
    )
    assert corrected.entry_start_barrier_J == pytest.approx(
        raw.entry_start_barrier_J - lowering
    )
    assert corrected.exit_end_barrier_J == pytest.approx(
        raw.exit_end_barrier_J - lowering
    )
    assert corrected.trap_barrier_J == raw.trap_barrier_J
    assert result.to_dict()["unmodified_profile"] == raw.to_dict()
    assert result.source_interface.status is BarrierCorrectionStatus.APPLIED


def test_disabled_correction_reproduces_j2_component_exactly():
    item = species()
    raw = evaluate_tat_species(item, **context())
    corrected = evaluate_tat_species_with_barrier_correction(
        item, correction(enabled=False), **context()
    )
    profile = corrected.barrier_diagnostics.corrected_profile
    assert profile == raw.barrier_profile
    for field in (
        "entry_wkb_exponent",
        "exit_wkb_exponent",
        "entry_transmission",
        "exit_transmission",
        "entry_rate_Hz",
        "exit_rate_Hz",
        "active_probability",
        "rate_Hz",
        "status",
    ):
        assert getattr(corrected, field) == getattr(raw, field)


def test_enabled_correction_lowers_actions_and_does_not_reduce_rate():
    item = species()
    raw = evaluate_tat_species(item, **context())
    corrected = evaluate_tat_species_with_barrier_correction(
        item, correction(), **context()
    )
    assert corrected.entry_wkb_exponent < raw.entry_wkb_exponent
    assert corrected.exit_wkb_exponent < raw.exit_wkb_exponent
    assert corrected.entry_transmission > raw.entry_transmission
    assert corrected.exit_transmission > raw.exit_transmission
    assert corrected.rate_Hz >= raw.rate_Hz
    assert corrected.status is TATRateStatus.EVALUATED


def test_field_reversal_and_position_mirroring_swap_corrected_legs():
    forward = evaluate_tat_species_with_barrier_correction(
        species(position_fraction=0.3), correction(), **context()
    )
    reverse = evaluate_tat_species_with_barrier_correction(
        species(position_fraction=0.7),
        correction(),
        **context(electric_field_V_m=-2e8),
    )
    assert reverse.entry_wkb_exponent == pytest.approx(
        forward.exit_wkb_exponent, rel=1e-14
    )
    assert reverse.exit_wkb_exponent == pytest.approx(
        forward.entry_wkb_exponent, rel=1e-14
    )
    assert reverse.rate_Hz == pytest.approx(forward.rate_Hz, rel=1e-14)


def test_barrier_suppression_is_explicit_and_numerically_bounded():
    result = apply_image_force_barrier_correction(
        1e-22,
        electric_field_V_m=1e9,
        specification=correction(relative_permittivity=1.0),
    )
    assert result.corrected_barrier_J < 0.0
    assert result.status is BarrierCorrectionStatus.BARRIER_SUPPRESSED
    component = evaluate_tat_species_with_barrier_correction(
        species(energy_depth_J=1e-22),
        correction(relative_permittivity=1.0),
        **context(electric_field_V_m=1e9),
    )
    assert math.isfinite(component.rate_Hz)
    assert 0.0 <= component.entry_transmission <= 1.0
    assert 0.0 <= component.exit_transmission <= 1.0


def test_mechanism_aggregation_is_deterministic_and_hashes_configuration():
    tat = TrapAssistedTransportSpec(
        enabled=True,
        species=(species("a"), species("b", position_fraction=0.6)),
    )
    image = correction()
    first = evaluate_trap_assisted_transport_with_barrier_correction(
        tat, image, **context()
    )
    second = evaluate_trap_assisted_transport_with_barrier_correction(
        tat, image, **context()
    )
    assert first == second
    assert first.result_hash == second.result_hash
    assert first.tat_configuration_hash == tat.configuration_hash
    assert first.correction_configuration_hash == image.configuration_hash
    assert first.total_rate_Hz == math.fsum(item.rate_Hz for item in first.components)
    with pytest.raises(FrozenInstanceError):
        first.total_rate_Hz = 0.0


def test_disabled_tat_is_exact_zero_even_when_correction_is_enabled():
    result = evaluate_trap_assisted_transport_with_barrier_correction(
        TrapAssistedTransportSpec(), correction(), **context()
    )
    assert result.enabled is False
    assert result.components == ()
    assert result.total_rate_Hz == 0.0
    assert result.status is TATRateStatus.DISABLED


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("electric_field_V_m", float("nan"), ValueError),
        ("electric_field_V_m", True, TypeError),
        ("unmodified_barrier_J", float("inf"), ValueError),
    ],
)
def test_invalid_correction_inputs_are_rejected(field, value, error):
    values = dict(
        unmodified_barrier_J=1e-19,
        electric_field_V_m=2e8,
        specification=correction(),
    )
    values[field] = value
    with pytest.raises(error):
        apply_image_force_barrier_correction(**values)


def test_j3_remains_isolated_from_transport_engine():
    engine = (ROOT / "ncmemsim/transport/engine.py").read_text(encoding="utf-8")
    assert "barrier_correction" not in engine
    assert "ImageForceBarrierSpec" not in engine
