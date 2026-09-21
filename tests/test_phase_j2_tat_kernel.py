from __future__ import annotations

from dataclasses import FrozenInstanceError
import math
from pathlib import Path

import numpy as np
import pytest

from ncmemsim.transport import (
    TATRateStatus,
    TrapAssistedTransportSpec,
    TrapParameterStatus,
    TrapSpecies,
    build_tat_barrier_profile,
    evaluate_tat_species,
    evaluate_trap_assisted_transport,
    evaluate_trap_assisted_transport_array,
    linear_wkb_transmission,
)
from ncmemsim.transport.tat import (
    ELEMENTARY_CHARGE_C,
    ELECTRON_MASS_KG,
    REDUCED_PLANCK_J_S,
)


ROOT = Path(__file__).resolve().parents[1]


def species(name="oxide-electron-trap", **overrides):
    values = {
        "name": name,
        "energy_depth_J": 1.602176634e-19,
        "position_fraction": 0.4,
        "density_m3": 1.0e23,
        "capture_cross_section_m2": 1.0e-19,
        "attempt_frequency_Hz": 1.0e13,
        "parameter_status": TrapParameterStatus.ASSUMED,
        "source": "synthetic J2 kernel check",
        "applicability": "conditional homogeneous-link rate only",
    }
    values.update(overrides)
    return TrapSpecies(**values)


def enabled(*items):
    return TrapAssistedTransportSpec(enabled=True, species=tuple(items or (species(),)))


def context(**overrides):
    values = {
        "link_length_m": 8.0e-9,
        "electric_field_V_m": 2.0e8,
        "effective_mass_m0": 0.2,
    }
    values.update(overrides)
    return values


def test_flat_linear_wkb_matches_closed_form():
    length, barrier, mass_ratio = 3e-9, 1.2e-19, 0.25
    transmission, exponent = linear_wkb_transmission(length, barrier, barrier, mass_ratio)
    expected = (
        2 * length * math.sqrt(2 * mass_ratio * ELECTRON_MASS_KG * barrier)
        / REDUCED_PLANCK_J_S
    )
    assert exponent == pytest.approx(expected, rel=2e-15)
    assert transmission == pytest.approx(math.exp(-expected), rel=2e-15)


@pytest.mark.parametrize(
    "start,end",
    [(2e-19, 1e-19), (1e-19, 2e-19), (-1e-19, 2e-19), (2e-19, -1e-19), (-2e-19, -1e-19)],
)
def test_linear_wkb_exact_action_matches_independent_quadrature(start, end):
    length, mass_ratio = 6e-9, 0.19
    _, exponent = linear_wkb_transmission(length, start, end, mass_ratio)
    coordinate = np.linspace(0.0, length, 500_001)
    barrier = start + (end - start) * coordinate / length
    integrand = np.sqrt(np.maximum(barrier, 0.0))
    integral = float(np.sum(
        0.5 * (integrand[:-1] + integrand[1:]) * np.diff(coordinate)
    ))
    expected = 2 * math.sqrt(2 * mass_ratio * ELECTRON_MASS_KG) * integral / REDUCED_PLANCK_J_S
    assert exponent == pytest.approx(expected, rel=2e-8, abs=1e-12)


def test_directed_trap_referenced_profile_is_explicit():
    item = species(position_fraction=0.25, energy_depth_J=2e-19)
    profile = build_tat_barrier_profile(item, **context())
    x = 0.25 * context()["link_length_m"]
    assert profile.trap_position_m == x
    assert profile.entry_start_barrier_J == pytest.approx(
        item.energy_depth_J + ELEMENTARY_CHARGE_C * context()["electric_field_V_m"] * x
    )
    assert profile.trap_barrier_J == item.energy_depth_J
    assert profile.exit_end_barrier_J == pytest.approx(
        item.energy_depth_J
        - ELEMENTARY_CHARGE_C * context()["electric_field_V_m"] * (context()["link_length_m"] - x)
    )


def test_component_matches_selected_sequential_rate_equation():
    item = species()
    result = evaluate_tat_species(item, **context())
    expected_active = 1.0 - math.exp(
        -item.density_m3 * item.capture_cross_section_m2 * context()["link_length_m"]
    )
    expected_rate = expected_active * (
        result.entry_rate_Hz * result.exit_rate_Hz
        / (result.entry_rate_Hz + result.exit_rate_Hz)
    )
    assert result.active_probability == pytest.approx(expected_active, rel=2e-15)
    assert result.rate_Hz == pytest.approx(expected_rate, rel=1e-12)
    assert result.status is TATRateStatus.EVALUATED
    assert 0 < result.entry_transmission <= 1
    assert 0 < result.exit_transmission <= 1


def test_slow_leg_bound_and_active_probability_bounds():
    result = evaluate_tat_species(species(), **context())
    assert 0 <= result.active_probability <= 1
    assert 0 <= result.rate_Hz <= min(result.entry_rate_Hz, result.exit_rate_Hz)
    saturated = evaluate_tat_species(
        species(density_m3=1e300, capture_cross_section_m2=1e100), **context()
    )
    assert saturated.active_probability == 1.0
    assert math.isfinite(saturated.rate_Hz)


def test_zero_density_and_disabled_limits_are_exact_zero():
    zero = evaluate_tat_species(species(density_m3=0.0), **context())
    assert zero.active_probability == zero.rate_Hz == 0.0
    assert zero.status is TATRateStatus.ZERO_DENSITY
    disabled = evaluate_trap_assisted_transport(
        TrapAssistedTransportSpec(species=(species(),)), **context()
    )
    assert disabled.enabled is False
    assert disabled.components == ()
    assert disabled.total_rate_Hz == 0.0
    assert disabled.status is TATRateStatus.DISABLED


def test_exponential_underflow_is_reported_not_raised():
    result = evaluate_tat_species(
        species(energy_depth_J=1e-15),
        **context(link_length_m=1e-6, electric_field_V_m=0.0, effective_mass_m0=1.0),
    )
    assert result.entry_transmission == 0.0
    assert result.exit_transmission == 0.0
    assert result.rate_Hz == 0.0
    assert result.status is TATRateStatus.TRANSMISSION_UNDERFLOW
    assert math.isfinite(result.entry_wkb_exponent)


def test_field_reversal_and_position_mirroring_swap_legs():
    forward = evaluate_tat_species(species(position_fraction=0.3), **context())
    reverse = evaluate_tat_species(
        species(position_fraction=0.7),
        **context(electric_field_V_m=-context()["electric_field_V_m"]),
    )
    assert reverse.entry_wkb_exponent == pytest.approx(forward.exit_wkb_exponent, rel=1e-14)
    assert reverse.exit_wkb_exponent == pytest.approx(forward.entry_wkb_exponent, rel=1e-14)
    assert reverse.rate_Hz == pytest.approx(forward.rate_Hz, rel=1e-14)


def test_multi_species_aggregation_is_observable_and_deterministic():
    spec = enabled(species("a"), species("b", density_m3=2e23, position_fraction=0.6))
    first = evaluate_trap_assisted_transport(spec, **context())
    second = evaluate_trap_assisted_transport(spec, **context())
    assert first == second
    assert first.result_hash == second.result_hash
    assert first.total_rate_Hz == math.fsum(item.rate_Hz for item in first.components)
    assert [item.species_name for item in first.components] == ["a", "b"]
    assert all(len(item.result_hash) == 64 for item in first.components)
    with pytest.raises(FrozenInstanceError):
        first.total_rate_Hz = 0.0


def test_array_entry_point_broadcasts_and_returns_independent_arrays():
    spec = enabled()
    batch = evaluate_trap_assisted_transport_array(
        spec,
        link_length_m=np.array([[6e-9], [8e-9]]),
        electric_field_V_m=np.array([[-2e8, 0.0, 2e8]]),
        effective_mass_m0=0.2,
    )
    assert batch.shape == (2, 3)
    rates = batch.total_rates_Hz
    assert rates.shape == (2, 3)
    expected = evaluate_trap_assisted_transport(
        spec, link_length_m=8e-9, electric_field_V_m=2e8, effective_mass_m0=0.2
    )
    assert rates[1, 2] == expected.total_rate_Hz
    rates[:] = -1
    assert np.all(batch.total_rates_Hz >= 0)
    with pytest.raises(TypeError, match="excluding bool"):
        evaluate_trap_assisted_transport_array(
            spec,
            link_length_m=np.array([True]),
            electric_field_V_m=0.0,
            effective_mass_m0=0.2,
        )


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("link_length_m", 0.0, ValueError),
        ("link_length_m", -1.0, ValueError),
        ("link_length_m", True, TypeError),
        ("electric_field_V_m", float("nan"), ValueError),
        ("effective_mass_m0", 0.0, ValueError),
        ("effective_mass_m0", float("inf"), ValueError),
    ],
)
def test_invalid_context_is_rejected(field, value, error):
    values = context(**{field: value})
    with pytest.raises(error):
        evaluate_trap_assisted_transport(enabled(), **values)


def test_j2_remains_isolated_from_transport_engine():
    engine = (ROOT / "ncmemsim/transport/engine.py").read_text(encoding="utf-8")
    assert "evaluate_trap_assisted" not in engine
    assert "TrapAssistedTransportSpec" not in engine
