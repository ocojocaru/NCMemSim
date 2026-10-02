# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Equation, applicability and strict archive checks for opt-in thermal contracts."""
from dataclasses import FrozenInstanceError, replace
import copy
import json
import math

import pytest

from ncmemsim.constants import BOLTZMANN_J_K, ELEMENTARY_CHARGE_C
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.temperature import (
    AnchoredVarshniProfile, CarrierStatisticsDomain, GapKind,
    IntrinsicDensityProfile, TemperatureDomain, ThermalEvidence,
    ThermalMaterial, profile_from_reviewed_record, reviewed_varshni_coefficients,
)


def evidence(status=ParameterStatus.ASSUMED):
    return ThermalEvidence('Explicit test assumption', 'test fixture', status,
                           'Numerical domain, not independent calibration')


def gap():
    domain = TemperatureDomain(ThermalMaterial.SILICON, 250, 350, 0, 0, evidence())
    return profile_from_reviewed_record(reviewed_varshni_coefficients()[0],
        name='si-controlled', domain=domain, reference_temperature_K=300,
        reference_gap_eV=1.12, reference_evidence=evidence())


def density():
    return IntrinsicDensityProfile('si-relative', gap(), 1e16, evidence(),
        CarrierStatisticsDomain(1e22, 1e24, 10, evidence()))


@pytest.mark.parametrize('temperature', [250, 275, 300, 325, 350])
def test_gap_matches_independent_equation(temperature):
    profile = gap()
    expected = 1.12 - 7.021e-4 * (temperature**2/(temperature+1108) - 300**2/1408)
    assert profile.evaluate(temperature) == pytest.approx(expected, rel=1e-14)
    assert profile.evaluate_property(temperature).provenance.status is ParameterStatus.DERIVED


def test_exact_anchor_monotonicity_and_constant_control():
    profile = gap()
    assert profile.evaluate(300) == 1.12
    assert profile.evaluate(250) > profile.evaluate(300) > profile.evaluate(350)
    constant = replace(profile, alpha_eV_K=0)
    assert [constant.evaluate(t) for t in (250, 300, 350)] == [1.12]*3
    t, h = 310, 0.01
    derivative = (profile.evaluate(t+h)-profile.evaluate(t-h))/(2*h)
    expected = -profile.alpha_eV_K*t*(t+2*profile.beta_K)/(t+profile.beta_K)**2
    assert derivative == pytest.approx(expected, rel=1e-8)


@pytest.mark.parametrize('temperature', [250, 275, 300, 325, 350])
def test_density_matches_independent_ratio(temperature):
    profile = density()
    kb = BOLTZMANN_J_K/ELEMENTARY_CHARGE_C
    expected = 1e16*(temperature/300)**1.5*math.exp(
        -profile.gap_profile.evaluate(temperature)/(2*kb*temperature) + 1.12/(2*kb*300))
    assert profile.evaluate(temperature, substrate_doping_m3=1e23) == pytest.approx(expected, rel=1e-13)
    assert profile.evaluate(300, substrate_doping_m3=1e23) == 1e16
    assert profile.evaluate_property(temperature, substrate_doping_m3=1e23).unit == 'm^-3'


def test_density_gap_control_and_monotonicity():
    p = density()
    constant = replace(p, gap_profile=replace(p.gap_profile, alpha_eV_K=0))
    assert p.evaluate(350, substrate_doping_m3=1e23) > constant.evaluate(350, substrate_doping_m3=1e23)
    assert p.evaluate(250, substrate_doping_m3=1e23) < p.reference_density_m3 < p.evaluate(350, substrate_doping_m3=1e23)


@pytest.mark.parametrize('bad', [0, -1, float('inf'), float('-inf'), float('nan'), True, '300', None])
def test_invalid_temperature_rejected(bad):
    with pytest.raises(ValueError):
        gap().evaluate(bad)


@pytest.mark.parametrize('temperature', [249.999, 350.001])
def test_no_extrapolation(temperature):
    with pytest.raises(ValueError, match='outside'):
        gap().evaluate(temperature)


@pytest.mark.parametrize('field,bad', [
    ('alpha_eV_K', -1), ('alpha_eV_K', float('nan')), ('beta_K', 0),
    ('beta_K', True), ('reference_gap_eV', 0), ('reference_gap_eV', 0.001),
    ('reference_temperature_K', 249), ('sn_fraction', 0.1), ('name', ''),
    ('gap_kind', GapKind.GAMMA), ('coefficient_evidence', {}),
])
def test_invalid_gap_contracts(field, bad):
    with pytest.raises(ValueError):
        replace(gap(), **{field: bad})


@pytest.mark.parametrize('field,bad', [
    ('min_temperature_K', 0), ('max_temperature_K', 249),
    ('min_sn_fraction', -0.1), ('max_sn_fraction', 1.1),
    ('max_sn_fraction', 0.1), ('strain_state', 'strained'), ('material', 'Si'),
    ('evidence', {}),
])
def test_invalid_domains(field, bad):
    with pytest.raises(ValueError):
        replace(gap().domain, **{field: bad})


def test_reviewed_coefficients_and_bulk_ge_anchor():
    records = reviewed_varshni_coefficients()
    assert [(r.zero_temperature_gap_eV, r.alpha_eV_K, r.beta_K) for r in records] == [
        (1.1557, 7.021e-4, 1108), (0.8893, 6.042e-4, 398), (0.7412, 4.561e-4, 210)]
    for record, anchor in zip(records[1:], (0.7985, 0.664)):
        p = profile_from_reviewed_record(record, name=record.name,
            domain=TemperatureDomain(ThermalMaterial.GERMANIUM, 250, 350, 0, 0, evidence()),
            reference_temperature_K=300, reference_gap_eV=anchor, reference_evidence=evidence())
        assert p.evaluate(300) == anchor
        assert p.coefficient_evidence.status is ParameterStatus.LITERATURE_FITTED
        with pytest.raises(ValueError):
            replace(density(), gap_profile=p)
    with pytest.raises(ValueError, match='reviewed'):
        profile_from_reviewed_record(replace(records[0], alpha_eV_K=0.000473),
            name='unreviewed', domain=gap().domain, reference_temperature_K=300,
            reference_gap_eV=1.12, reference_evidence=evidence())
    with pytest.raises(ValueError, match='ASSUMED'):
        profile_from_reviewed_record(records[0], name='unqualified',
            domain=replace(gap().domain, evidence=evidence(ParameterStatus.LITERATURE)),
            reference_temperature_K=300, reference_gap_eV=1.12, reference_evidence=evidence())


def test_explicit_gesn_contract_does_not_invent_composition_law():
    domain = TemperatureDomain(ThermalMaterial.GERMANIUM_TIN, 250, 350, .05, .15, evidence())
    p = AnchoredVarshniProfile('conditional-gesn', GapKind.GAMMA, domain, .1,
        300, .5, .0004, 300, evidence(), evidence())
    assert p.evaluate(300, sn_fraction=.1) == .5
    with pytest.raises(ValueError, match='one declared composition'):
        p.evaluate(300, sn_fraction=.11)
    with pytest.raises(ValueError):
        profile_from_reviewed_record(reviewed_varshni_coefficients()[1],
            name='invalid-ge-copy', domain=domain, reference_temperature_K=300,
            reference_gap_eV=.5, reference_evidence=evidence())


@pytest.mark.parametrize('factory', [gap, density])
def test_owned_archive_roundtrip_hash_and_frozen_state(factory):
    p = factory()
    assert type(p).from_json(p.to_json()) == p
    assert type(p).from_dict(p.to_dict()).contract_hash == p.contract_hash
    snapshot = p.to_dict()
    snapshot['name'] = 'tampered copy'
    assert p.to_dict()['name'] != snapshot['name']
    with pytest.raises(FrozenInstanceError):
        p.name = 'mutated'
    assert replace(p, name='new-name').contract_hash != p.contract_hash


@pytest.mark.parametrize('factory', [gap, density])
@pytest.mark.parametrize('mode', ['extra', 'missing', 'unit', 'schema', 'boolean', 'nested'])
def test_strict_archives(factory, mode):
    p = factory()
    data = copy.deepcopy(p.to_dict())
    if mode == 'extra': data['unknown'] = 1
    if mode == 'missing': del data['name']
    if mode == 'unit': data['unit'] = 'joules'
    if mode == 'schema': data['schema_version'] = 'future-v99'
    if mode == 'boolean': data['reference_gap_eV' if factory is gap else 'reference_density_m3'] = True
    if mode == 'nested':
        target = data['domain'] if factory is gap else data['gap_profile']['domain']
        target['evidence']['status'] = 'calibrated'
    with pytest.raises(ValueError):
        type(p).from_dict(data)


@pytest.mark.parametrize('text', ['{"name":1,"name":2}', '{"name":NaN}', '[]', '{}'])
def test_invalid_json(text):
    with pytest.raises(ValueError):
        AnchoredVarshniProfile.from_json(text)


@pytest.mark.parametrize('bad', [0, -1, True, float('inf'), float('nan'), '1e23', 1e21, 1e25])
def test_doping_rejected(bad):
    with pytest.raises(ValueError):
        density().evaluate(300, substrate_doping_m3=bad)


def test_carrier_boundaries_and_invalid_rectangles():
    stats = CarrierStatisticsDomain(100, 1000, 10, evidence())
    stats.check(100, 10)
    stats.check(1000, 100)
    stats.check(1000, 1e-320)
    with pytest.raises(ValueError): stats.check(100, 10.0001)
    with pytest.raises(ValueError): replace(stats, assumption='degenerate')
    with pytest.raises(ValueError): replace(stats, max_doping_m3=99)
    with pytest.raises(ValueError): replace(stats, minimum_doping_to_intrinsic_ratio=1)
    with pytest.raises(ValueError): replace(density(), statistics_domain=stats)


def test_underflow_overflow_are_not_clipped():
    tiny = replace(gap(), domain=replace(gap().domain, min_temperature_K=1), alpha_eV_K=0)
    with pytest.raises(ValueError): replace(density(), gap_profile=tiny)
    single = replace(gap(), domain=replace(gap().domain, min_temperature_K=300, max_temperature_K=300))
    extreme = IntrinsicDensityProfile('extreme', single, 1e307, evidence(),
        CarrierStatisticsDomain(1e308, 1e308, 2, evidence()))
    broad = replace(single, domain=replace(single.domain, max_temperature_K=350))
    with pytest.raises(ValueError, match='overflow'):
        replace(extreme, gap_profile=broad)


def test_no_implicit_public_alias():
    import ncmemsim.materials as materials
    assert not hasattr(materials, 'AnchoredVarshniProfile')
