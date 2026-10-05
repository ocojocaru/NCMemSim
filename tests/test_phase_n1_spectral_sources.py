# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Analytical source integrals, immutable provenance and strict archive boundaries."""
from dataclasses import FrozenInstanceError, replace
import json
import math
import pytest

from ncmemsim.constants import LIGHT_SPEED_M_S, PLANCK_J_S
from ncmemsim.optics import LightSource
from ncmemsim.spectral_sources import SpectralEvidence, TabulatedSpectrum, DiscreteLineSpectrum


@pytest.fixture
def evidence():
    return SpectralEvidence("synthetic reference", "analytic test", "ASSUMED", "W m^-2 nm^-1", (), "ideal table", "unknown", "not calibrated")


def test_constant_density_has_analytic_power_and_photon_integrals(evidence):
    s = TabulatedSpectrum((1000, 2000), (2, 2), evidence)
    assert s.in_band_irradiance_W_m2 == 2000
    assert s.photon_flux_m2_s == pytest.approx(2*1.5e6*1e-9/(PLANCK_J_S*LIGHT_SPEED_M_S))


def test_linear_density_photon_moment_and_grid_refinement(evidence):
    coarse = TabulatedSpectrum((1000, 2000), (0, 2), evidence)
    refined = TabulatedSpectrum((1000, 1500, 2000), (0, 1, 2), evidence)
    expected = (5e6/3)*1e-9/(PLANCK_J_S*LIGHT_SPEED_M_S)
    assert coarse.in_band_irradiance_W_m2 == 1000
    assert coarse.photon_flux_m2_s == pytest.approx(expected)
    assert refined.photon_flux_m2_s == pytest.approx(expected)
    # Trapezoid on lambda*S at endpoints would yield 2e6, not 5e6/3.
    assert not math.isclose(coarse.photon_flux_m2_s, 2e6*1e-9/(PLANCK_J_S*LIGHT_SPEED_M_S), rel_tol=.01)


def test_relative_shape_preserves_input_and_records_normalization(evidence):
    s = TabulatedSpectrum((1000, 2000), (1, 3), evidence, "relative_shape", 100)
    assert s.values == (1, 3)
    assert s.normalization_factor == .05
    assert s.in_band_irradiance_W_m2 == pytest.approx(100)
    assert s.to_dict()["value_unit"] == "dimensionless"
    with pytest.raises(FrozenInstanceError):
        s.enabled = False


def test_line_limit_matches_legacy_photon_flux(evidence):
    source = LightSource.laser(1550, 1000)
    line = DiscreteLineSpectrum((1550,), (1000,), evidence)
    assert line.in_band_irradiance_W_m2 == 1000
    assert line.photon_flux_m2_s == pytest.approx(source.photon_flux_m2_s, rel=1e-15)


def test_multiple_lines_integrate_each_energy_separately(evidence):
    s = DiscreteLineSpectrum((1000, 2000), (1, 3), evidence)
    assert s.photon_flux_m2_s == pytest.approx(7e-6/(PLANCK_J_S*LIGHT_SPEED_M_S))


@pytest.mark.parametrize('cls,args', [(TabulatedSpectrum,((1000,2000),(0,0))), (DiscreteLineSpectrum,((1550,),(0,)))])
def test_dark_and_disabled_sources(evidence,cls,args):
    s = cls(*args,evidence)
    assert s.photon_flux_m2_s == s.in_band_irradiance_W_m2 == 0
    bright = cls(args[0],tuple(2 for _ in args[1]),evidence,enabled=False)
    assert bright.photon_flux_m2_s == bright.in_band_irradiance_W_m2 == 0
    assert bright.to_dict()["enabled"] is False


@pytest.mark.parametrize('w,v', [((1000,), (1,)), ((2000,1000),(1,1)), ((1000,1000),(1,1)),
    ((0,1000),(1,1)), ((1000,float('inf')),(1,1)), ((True,1000),(1,1)),
    ((1000,2000),(-1,1)), ((1000,2000),(float('nan'),1)), ((1000,2000),(True,1)),
    ((1000,2000),(1,)), ([1000,2000],(1,1)), ((1000,2000),[1,1])])
def test_invalid_table_rejected(evidence,w,v):
    with pytest.raises(ValueError):TabulatedSpectrum(w,v,evidence)


@pytest.mark.parametrize('kwargs', [{"target_irradiance_W_m2":100}, {"input_kind":"relative_shape"},
    {"input_kind":"frequency_density"}, {"enabled":1}, {"input_kind":"relative_shape","target_irradiance_W_m2":-1}])
def test_ambiguous_normalization_and_flags_rejected(evidence,kwargs):
    with pytest.raises(ValueError):TabulatedSpectrum((1000,2000),(1,1),evidence,**kwargs)


def test_zero_relative_shape_rejected_even_when_disabled(evidence):
    with pytest.raises(ValueError):TabulatedSpectrum((1000,2000),(0,0),evidence,"relative_shape",100,False)
    assert TabulatedSpectrum((1000,2000),(1,1),evidence,"relative_shape",0).photon_flux_m2_s == 0


@pytest.mark.parametrize('kwargs', [{"status":"CALIBRATED"}, {"transformations":[]}, {"source_sha256":"bad"}, {"uncertainty":""}])
def test_provenance_cannot_imply_device_qualification(evidence,kwargs):
    with pytest.raises(ValueError):replace(evidence,**kwargs)


@pytest.mark.parametrize('cls,args',[(TabulatedSpectrum,((1000,2000),(1,2))), (DiscreteLineSpectrum,((1550,),(1000,)))])
def test_roundtrip_and_identity_include_evidence(evidence,cls,args):
    s = cls(*args,evidence)
    assert cls.from_json(s.to_json()) == s
    assert cls.from_dict(s.to_dict()).contract_hash == s.contract_hash
    other=cls(*args,replace(evidence,notes="different assumption"))
    assert other.contract_hash != s.contract_hash
    data=s.to_dict();data["evidence"]["notes"]="caller mutation"
    assert s.evidence.notes == "not calibrated"


@pytest.mark.parametrize('fault',["unit","schema","policy","extra","nested","bool","density-list"])
def test_strict_archive_rejects_semantic_changes(evidence,fault):
    data=TabulatedSpectrum((1000,2000),(1,2),evidence).to_dict()
    if fault=='unit':data['wavelength_unit']='Hz'
    elif fault=='schema':data['schema_version']='unknown'
    elif fault=='policy':data['integration_policy']='silent extrapolation'
    elif fault=='extra':data['unreviewed']=True
    elif fault=='nested':data['evidence']['unreviewed']=True
    elif fault=='bool':data['enabled']=1
    else:data['values']=(1,2)
    with pytest.raises(ValueError):TabulatedSpectrum.from_dict(data)


def test_duplicate_and_nonfinite_json_rejected(evidence):
    text=TabulatedSpectrum((1000,2000),(1,2),evidence).to_json()
    with pytest.raises(ValueError,match='duplicate'):TabulatedSpectrum.from_json(text.replace('{','{"enabled":true,',1))
    with pytest.raises(ValueError,match='nonfinite'):TabulatedSpectrum.from_json(text.replace('[1.0,2.0]','[NaN,2.0]'))


def test_integral_overflow_rejected(evidence):
    with pytest.raises(ValueError):TabulatedSpectrum((1,1e308),(1e308,1e308),evidence)
    with pytest.raises(ValueError):DiscreteLineSpectrum((1000,2000),(1e308,1e308),evidence)


@pytest.mark.parametrize('w,p', [((),()), ((1000,1000),(1,2)), ((1000,),(-1,)),
    ((1000,),(float('inf'),)), ((1000,),(True,)), ((0,),(1,))])
def test_line_inputs_reject_nonphysical_or_ambiguous_values(evidence,w,p):
    with pytest.raises(ValueError):DiscreteLineSpectrum(w,p,evidence)


@pytest.mark.parametrize('field,value', [('schema_version','tabulated-spectrum-v1'),
    ('value_unit','W m^-2 nm^-1'), ('wavelength_unit','eV')])
def test_lines_cannot_be_restored_as_density_or_other_coordinate(evidence,field,value):
    data=DiscreteLineSpectrum((1550,),(1000,),evidence).to_dict()
    data[field]=value
    with pytest.raises(ValueError):DiscreteLineSpectrum.from_dict(data)


def test_measured_source_retains_digest_uncertainty_and_transformations(evidence):
    measured=replace(evidence,status='MEASURED',source_sha256='a'*64,
        transformations=('convert mW cm^-2 nm^-1 to W m^-2 nm^-1',),
        uncertainty='instrument estimate 2 percent')
    source=TabulatedSpectrum((1000,2000),(1,2),measured)
    restored=TabulatedSpectrum.from_json(source.to_json())
    assert restored.evidence == measured
    assert restored.values == (1,2)


def test_relative_shape_scale_changes_identity_but_not_resolved_flux(evidence):
    a=TabulatedSpectrum((1000,2000),(1,2),evidence,'relative_shape',100)
    b=TabulatedSpectrum((1000,2000),(2,4),evidence,'relative_shape',100)
    assert a.photon_flux_m2_s == pytest.approx(b.photon_flux_m2_s)
    assert a.contract_hash != b.contract_hash
    assert TabulatedSpectrum.from_json(a.to_json()) == a
